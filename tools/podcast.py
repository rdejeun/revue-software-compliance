#!/usr/bin/env python3
"""Épisode audio de la revue : content/AAAA-MM-JJ/podcast.json -> episode.mp3 (+ episode.json).

Usage :
  python3 tools/podcast.py --check [AAAA-MM-JJ]   contrôle le script (sans appel réseau)
  python3 tools/podcast.py [AAAA-MM-JJ]           produit l'épisode (par défaut : dernière édition)
  python3 tools/podcast.py --dry-run [...]        chaîne complète sans appel à ElevenLabs (voix synthétiques)
  python3 tools/podcast.py --force [...]          régénère même si l'épisode est à jour

Synthèse vocale : API ElevenLabs « Text to Dialogue » (plusieurs voix dans une même requête).
Variables : ELEVENLABS_API_KEY (clé), ELEVENLABS_VOICE_FEMALE et ELEVENLABS_VOICE_MALE (identifiants
des voix de Julie, voix A, et de Guillaume, voix B), ELEVENLABS_MODEL (facultatif, défaut ci-dessous).
Prononciation : tools/prononciation.json est recopié à chaque production dans le dictionnaire de
prononciation ElevenLabs « Software Compliance » (règles alias), passé ensuite à chaque requête.
Si le dictionnaire est inaccessible (droits de la clé), les remplacements sont faits localement.
Post-production (tools/mixage.py) : une piste par voix, timbres appariés, réverbération propre à une voix
atténuée, espace commun, master −16 LUFS ; contrôle qualité bloquant (loudness, true peak, durée, fidélité au
script par faster-whisper). Budget : pas d'épisode si le solde ElevenLabs ne couvre pas le script + 20 %.
Fichiers de travail : build/podcast/AAAA-MM-JJ/ (raw/, stems/, out/, qc_report.md), publiés en artefact par Actions.
L'épisode n'est régénéré que si podcast.json a changé (empreinte dans episode.json) : pas de
double facturation quand le workflow est relancé.
Ne bloque jamais la revue : sans clé ou sans podcast.json, le script s'arrête proprement (code 0).
"""
import base64, datetime, hashlib, io, json, os, re, shutil, subprocess, sys, tempfile, time, wave
import urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, 'content')
LEXIQUE = os.path.join(ROOT, 'tools', 'prononciation.json')
API = 'https://api.elevenlabs.io'
ENDPOINT = API + '/v1/text-to-dialogue/with-timestamps'   # audio + voice_segments (une piste par voix)
FORMAT = 'mp3_44100_128'         # seul format 44,1 kHz inclus dans l'abonnement Starter
SEED = int(os.environ.get('PODCAST_SEED') or 20261004)   # même tirage pour tous les blocs : voix homogènes
MARGE = 1.2                      # solde exigé : caractères du script + 20 %
DICT_NOM = 'Software Compliance'
# Modèles qui refusent previous_request_ids (erreur 400) : chaque requête est alors indépendante.
SANS_CONTINUITE = {'eleven_v3'}
MODELE = os.environ.get('ELEVENLABS_MODEL') or 'eleven_v3'
CHUNK_MAX = 1700                 # caractères par requête (limite de l'API : 2 000)
PAUSE = 0.6                      # secondes de silence entre deux requêtes (= entre deux sujets)

# Voix : identifiants ElevenLabs lus dans l'environnement ; un podcast.json peut les remplacer
# par une clé "voix" ({"A": {"voice": "…"}}).
VOIX = {
    'A': {'nom': 'Julie', 'voice': os.environ.get('ELEVENLABS_VOICE_FEMALE', '').strip()},
    'B': {'nom': 'Guillaume', 'voice': os.environ.get('ELEVENLABS_VOICE_MALE', '').strip()},
}
MOTS_MIN, MOTS_MAX = 900, 1800   # ≈ 6 à 12 minutes
# Mode essai (variable PODCAST_MAX_CHARS, ex. 450 ≈ 30 s) : seules les premières répliques, jusqu'à
# ce nombre de caractères, sont synthétisées. Pour limiter le coût pendant la mise au point.
MAX_CHARS = int(os.environ.get('PODCAST_MAX_CHARS') or 0)


def extrait(reps):
    """Premières répliques tenant dans MAX_CHARS (au moins une) ; toutes si MAX_CHARS vaut 0."""
    if not MAX_CHARS: return reps
    out, n = [], 0
    for r in reps:
        if out and n + len(r['t']) > MAX_CHARS: break
        out.append(r); n += len(r['t'])
    return out


def editions():
    return sorted(d for d in os.listdir(CONTENT) if re.fullmatch(r'\d{4}-\d{2}-\d{2}', d))


def log(*a): print(*a, flush=True)


def bilan(niveau, msg):
    """Message affiché aussi en annotation dans GitHub Actions (visible sans ouvrir le journal)."""
    log(msg)
    if os.environ.get('GITHUB_ACTIONS'): print(f'::{niveau} title=Épisode audio::{msg}', flush=True)


# ------------------------------------------------------------------ contrôle
def charger(d):
    p = os.path.join(CONTENT, d, 'podcast.json')
    if not os.path.isfile(p): return None, None
    raw = open(p, 'rb').read()
    pod = json.loads(raw.decode('utf-8'))
    # {"sujet": "…"} : marque de changement de sujet (non lue). Chaque réplique reçoit le numéro de son sujet.
    reps, n, noms = [], 0, []
    for r in pod.get('repliques') or []:
        if 'sujet' in r and 't' not in r:
            if reps or noms: n += 1
            noms.append(r['sujet']); continue
        reps.append({**r, '_s': n})
    pod['repliques'], pod['_sujets'] = reps, noms
    return pod, hashlib.sha256(raw).hexdigest()


def controler(pod):
    err, warn = [], []
    voix = {k: {**VOIX.get(k, {}), **v} for k, v in {**VOIX, **(pod.get('voix') or {})}.items()}
    for k in ('titre', 'description'):
        if not str(pod.get(k) or '').strip(): err.append(f'champ « {k} » manquant')
    reps = pod.get('repliques') or []
    if len(reps) < 6: err.append('moins de 6 répliques')
    for i, r in enumerate(reps):
        if r.get('v') not in voix: err.append(f'réplique {i + 1} : voix « {r.get("v")} » inconnue')
        if not str(r.get('t') or '').strip(): err.append(f'réplique {i + 1} : texte vide')
        if len(r.get('t') or '') > 900: warn.append(f'réplique {i + 1} : très longue ({len(r["t"])} caractères), à couper')
        if i and r.get('v') == reps[i - 1].get('v'): warn.append(f'réplique {i + 1} : même voix que la précédente')
        if re.search(r'[\[\]{}<>*_#]|https?://', r.get('t') or ''): err.append(f'réplique {i + 1} : balise, lien ou mise en forme à retirer (texte lu à voix haute)')
    mots = sum(len((r.get('t') or '').split()) for r in reps)
    noms = pod.get('_sujets') or []
    if not noms: warn.append('aucun marqueur {"sujet": …} : les coupures entre requêtes ne suivront pas les sujets')
    for k, nom in enumerate(noms):
        t = sum(len(r['t']) for r in reps if r.get('_s') == k)
        if t > CHUNK_MAX: warn.append(f'sujet « {nom} » : {t} caractères, au-delà de {CHUNK_MAX} ; il sera coupé avant une question (mieux : le scinder en deux sujets)')
    if not MOTS_MIN <= mots <= MOTS_MAX: warn.append(f'{mots} mots : hors de la plage visée ({MOTS_MIN}-{MOTS_MAX})')
    return err, warn, mots


# ------------------------------------------------------------------ texte lu
def regles():
    try: L = json.load(open(LEXIQUE, encoding='utf-8'))
    except FileNotFoundError: return {}
    return {k: v for k, v in L.items() if not k.startswith('_')}


def lexique():
    """Remplacements locaux (repli quand le dictionnaire ElevenLabs n'est pas utilisable)."""
    return [(re.compile(r'(?<![\w-])' + re.escape(k) + r'(?![\w-])'), v) for k, v in regles().items()]


def appel(methode, chemin, cle, corps=None):
    req = urllib.request.Request(API + chemin, method=methode, data=json.dumps(corps).encode('utf-8') if corps is not None else None,
                                 headers={'xi-api-key': cle, 'Content-Type': 'application/json', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r: return json.load(r)


def dictionnaire(cle):
    """Recopie le lexique dans le dictionnaire ElevenLabs ; renvoie son localisateur, ou None (repli local)."""
    R = [{'string_to_replace': k, 'type': 'alias', 'alias': v} for k, v in regles().items()]
    if not R: return None
    try:
        liste = appel('GET', '/v1/pronunciation-dictionaries?page_size=100', cle).get('pronunciation_dictionaries') or []
        d = next((x for x in liste if x.get('name') == DICT_NOM), None)
        if d: rep_ = appel('POST', f'/v1/pronunciation-dictionaries/{d["id"]}/set-rules', cle, {'rules': R})
        else: rep_ = appel('POST', '/v1/pronunciation-dictionaries/add-from-rules', cle,
                           {'name': DICT_NOM, 'description': 'Podcast Software Compliance : copie de tools/prononciation.json (dépôt revue-software-compliance)', 'rules': R})
        log(f'  dictionnaire « {DICT_NOM} » : {len(R)} règle(s), version {rep_["version_id"]}')
        return {'pronunciation_dictionary_id': rep_['id'], 'version_id': rep_['version_id']}
    except (urllib.error.URLError, KeyError, ValueError) as e:
        code = getattr(e, 'code', '')
        detail = e.read().decode('utf-8', 'replace')[:200] if hasattr(e, 'read') else str(e)
        bilan('warning', f'Dictionnaire de prononciation ElevenLabs inaccessible ({code} {detail}) : remplacements faits localement. Vérifier que la clé a le droit « Pronunciation Dictionaries » en écriture.')
        return None


def dire(t, lex):
    t = t.replace('’', "'").replace(' ', ' ')
    for rx, v in lex: t = rx.sub(v, t)
    return t


def taille(rs): return sum(len(r['t']) for r in rs)


def scinder(rs):
    """Sujet trop long pour une requête : coupe en parts égales, juste avant une question de Julie (voix A)."""
    parts = -(-taille(rs) // CHUNK_MAX)
    cible, out, cur = taille(rs) / parts, [], []
    for r in rs:
        if cur and r['v'] == 'A' and len(out) < parts - 1 and taille(cur) >= cible * 0.8:
            out.append(cur); cur = []
        cur.append(r)
    out.append(cur)
    return out


def decouper(reps):
    """Une requête par sujet ({"sujet": …} dans le script) : les coupures tombent sur les changements de sujet.
    Des sujets courts consécutifs partagent une requête ; un sujet trop long est scindé avant une question."""
    sujets = {}
    for r in reps: sujets.setdefault(r.get('_s', 0), []).append(r)
    blocs = [b for rs in sujets.values() for b in (scinder(rs) if taille(rs) > CHUNK_MAX else [rs])]
    out = []
    for b in blocs:
        if out and taille(out[-1]) + taille(b) <= CHUNK_MAX: out[-1] = out[-1] + b
        else: out.append(b)
    return out


# ------------------------------------------------------------------ ElevenLabs
def requete(chunk, voix, lex, cle, precedents, loc, base):
    """Une requête Text to Dialogue « with-timestamps ». Écrit base.mp3 (audio reçu) et base.json (réponse sans
    l'audio). Renvoie (segments de voix, identifiant de requête)."""
    inputs = [{'text': dire(r['t'], lex), 'voice_id': voix[r['v']]['voice']} for r in chunk]
    n = sum(len(x['text']) for x in inputs)
    if n > 2000: raise SystemExit(f'Requête de {n} caractères : au-delà de la limite de 2 000 (réduire CHUNK_MAX)')
    body = {'inputs': inputs, 'model_id': MODELE, 'language_code': 'fr', 'seed': SEED}
    if precedents and MODELE not in SANS_CONTINUITE: body['previous_request_ids'] = precedents[-3:]
    if loc: body['pronunciation_dictionary_locators'] = [loc]
    data = json.dumps(body).encode('utf-8')
    for essai in range(1, 6):
        req = urllib.request.Request(f'{ENDPOINT}?output_format={FORMAT}', data=data, method='POST',
                                     headers={'xi-api-key': cle, 'Content-Type': 'application/json', 'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                rep_ = json.load(r); rid = r.headers.get('request-id') or r.headers.get('x-request-id')
            if not rep_.get('audio_base64'): raise SystemExit('Réponse d\'ElevenLabs sans audio : ' + json.dumps(rep_)[:600])
            open(base + '.mp3', 'wb').write(base64.b64decode(rep_.pop('audio_base64')))
            json.dump({**rep_, 'request_id': rid, 'inputs': inputs}, open(base + '.json', 'w', encoding='utf-8'), ensure_ascii=False)
            return rep_.get('voice_segments') or [], rid
        except urllib.error.HTTPError as e:
            detail = e.read().decode('utf-8', 'replace')[:600]
            if e.code in (429, 500, 502, 503, 504) and essai < 3:
                log(f'  HTTP {e.code}, nouvel essai dans {10 * essai} s'); time.sleep(10 * essai); continue
            raise SystemExit(f'ElevenLabs a refusé la requête (HTTP {e.code}) : {detail}')
        except (urllib.error.URLError, TimeoutError) as e:
            if essai < 3: log(f'  {e}, nouvel essai dans {10 * essai} s'); time.sleep(10 * essai); continue
            raise SystemExit(f'ElevenLabs injoignable : {e}')


def solde(cle):
    """Caractères restants sur la période d'abonnement en cours, et date de remise à zéro."""
    a = appel('GET', '/v1/user/subscription', cle)
    reste = int(a['character_limit']) - int(a['character_count'])
    raz = a.get('next_character_count_reset_unix')
    return reste, (datetime.datetime.fromtimestamp(raz, datetime.timezone.utc).strftime('%d/%m/%Y') if raz else 'inconnue')


def synthetique(chunk, voix, base):
    """--dry-run : « voix » de synthèse (bruit filtré modulé), A plus brillante et réverbérée, B sèche,
    au format de l'API (MP3 + voice_segments). Exerce toute la post-production sans appel réseau."""
    import numpy as np
    from scipy import signal as sg
    sr, rng, x, segs, t = 44100, np.random.default_rng(len(chunk)), [], [], 0.0
    for r in chunk:
        d = max(0.6, len(r['t']) / 15); n = int(sr * d)
        bas, haut = (300, 6000) if r['v'] == 'A' else (120, 3500)
        y = sg.sosfilt(sg.butter(4, [bas, haut], 'bandpass', fs=sr, output='sos'), rng.standard_normal(n))
        env = (np.sin(np.arange(n) / sr * 2 * np.pi * 4) > -0.2).astype(float)
        y *= np.convolve(env, np.ones(200) / 200, 'same')
        if r['v'] == 'A': y = y + 0.3 * sg.lfilter([1], [1, -0.995], y) / 30
        y *= 0.1 / (np.sqrt((y ** 2).mean()) + 1e-9)
        segs.append({'voice_id': voix[r['v']]['voice'] or r['v'], 'start_time_seconds': t, 'end_time_seconds': t + d})
        x += [y, np.zeros(int(sr * 0.3))]; t += d + 0.3
    a = np.concatenate(x).astype('<f4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(sr), '-ac', '1', '-i', '-', '-b:a', '128k', base + '.mp3'], input=a.tobytes(), check=True)
    return segs


def produire(d, dry=False, force=False):
    pod, sha = charger(d)
    if pod is None: bilan('notice', f'{d} : pas de podcast.json, rien à faire.'); return False
    err, warn, mots = controler(pod)
    sha = hashlib.sha256((sha + json.dumps(regles(), sort_keys=True, ensure_ascii=False)).encode('utf-8')).hexdigest()  # le lexique compte aussi
    if MAX_CHARS: sha += f':essai-{MAX_CHARS}'   # un extrait n'est jamais pris pour l'épisode complet
    for w in warn: log(f'{d} : avertissement : {w}')
    if err: raise SystemExit(f'{d} : script invalide :\n- ' + '\n- '.join(err))
    dossier = os.path.join(CONTENT, d)
    mp3, info = os.path.join(dossier, 'episode.mp3'), os.path.join(dossier, 'episode.json')
    if not force and not dry and os.path.isfile(mp3) and os.path.isfile(info):
        if json.load(open(info, encoding='utf-8')).get('sha_script') == sha:
            bilan('notice', f'{d} : épisode déjà à jour, rien à refaire.'); return False
    cle = os.environ.get('ELEVENLABS_API_KEY', '').strip()
    if not dry and not cle: bilan('warning', f'{d} : secret ELEVENLABS_API_KEY absent, épisode non produit.'); return False
    if not shutil.which('ffmpeg'): raise SystemExit('ffmpeg introuvable')
    voix = {k: {**VOIX.get(k, {}), **v} for k, v in {**VOIX, **(pod.get('voix') or {})}.items()}
    manque = [v['nom'] for v in voix.values() if not v.get('voice')]
    if manque and not dry: bilan('warning', f'{d} : identifiant de voix manquant pour {", ".join(manque)} (variables ELEVENLABS_VOICE_FEMALE / ELEVENLABS_VOICE_MALE), épisode non produit.'); return False
    reps = extrait(pod['repliques'])
    if not dry:   # règle de budget : une semaine où le solde ne couvre pas le script (+20 %) ne produit pas de podcast
        besoin = int(sum(len(dire(r['t'], lexique())) for r in reps) * MARGE)
        try: reste, raz = solde(cle)
        except (urllib.error.URLError, KeyError, ValueError) as e:
            bilan('warning', f'{d} : solde ElevenLabs illisible ({getattr(e, "code", "")} {type(e).__name__}) : épisode non produit par prudence. Vérifier que la clé a le droit « User » en lecture.'); return False
        if reste < besoin:
            bilan('warning', f'{d} : solde ElevenLabs insuffisant ({reste} caractères restants, {besoin} nécessaires avec la marge) : pas d’épisode cette semaine. Remise à zéro le {raz}.'); return False
        log(f'{d} : solde ElevenLabs {reste} caractères, besoin {besoin} (marge comprise) : ok')
    loc = None if dry else dictionnaire(cle)
    lex = [] if loc else lexique()
    if MAX_CHARS:
        mots = sum(len(r['t'].split()) for r in reps)
        log(f'{d} : MODE ESSAI (PODCAST_MAX_CHARS={MAX_CHARS}) : {len(reps)} réplique(s) sur {len(pod["repliques"])}, {sum(len(r["t"]) for r in reps)} caractères')
    chunks = decouper(reps)
    log(f'{d} : {len(reps)} répliques, {mots} mots, {len(chunks)} requête(s) {"(essai à blanc)" if dry else "à " + MODELE}')
    travail = os.path.join(ROOT, 'build', 'podcast', d); shutil.rmtree(travail, ignore_errors=True); os.makedirs(os.path.join(travail, 'raw'))
    blocs, ids = [], []
    for i, c in enumerate(chunks, 1):
        sujets = ', '.join(dict.fromkeys(pod['_sujets'][r['_s']] for r in c if pod['_sujets']))
        log(f'  requête {i}/{len(chunks)} ({sum(len(r["t"]) for r in c)} caractères){" : " + sujets if sujets else ""}')
        base = os.path.join(travail, 'raw', f'chunk_{i:02d}')
        if dry: segs = synthetique(c, voix, base)
        else:
            segs, rid = requete(c, voix, lex, cle, ids, loc, base)
            if rid: ids.append(rid)
        blocs.append({'mp3': base + '.mp3', 'segments': segs})
    import mixage
    ids_voix = {k: (v.get('voice') or k) for k, v in voix.items()}
    sortie = os.path.join(travail, 'out', 'episode.mp3')
    M = mixage.produire(blocs, ids_voix, sortie, travail, {'titre': pod['titre'], 'date': d, 'n': ''})
    ok, ecarts, resume = mixage.qc(M, sortie, ' '.join(r['t'] for r in reps), travail)
    duree = M['duree_blocs_s']
    meta = {'duree_s': round(duree), 'octets': os.path.getsize(sortie), 'mots': mots, 'modele': 'essai à blanc' if dry else MODELE, 'seed': SEED,
            'voix': {k: {'nom': v['nom'], 'voice': v.get('voice', '')} for k, v in voix.items()},
            'genere_le': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'sha_script': sha, 'extrait': bool(MAX_CHARS), 'repliques': len(reps),
            'prononciation': 'aucune (essai à blanc)' if dry else ('dictionnaire ElevenLabs ' + loc['version_id'] if loc else 'remplacements locaux'),
            'qc': resume, 'requetes': len(chunks)}
    if dry:
        log(f'{d} : essai à blanc terminé : {sortie} ({duree / 60:.1f} min), contrôle {"réussi" if ok else "en écart"} ; rapport : {travail}/qc_report.md. Aucun fichier écrit dans content/.')
        return False
    if not ok:
        bilan('error', f'{d} : épisode produit mais non publié, contrôle qualité en écart : ' + ' ; '.join(ecarts) + '. Détail dans l’artefact « podcast » de l’exécution.')
        return False
    for e in ecarts: bilan('warning', f'{d} : contrôle qualité, écart non bloquant : {e}')
    shutil.copyfile(sortie, mp3); meta['octets'] = os.path.getsize(mp3)
    json.dump(meta, open(info, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    bilan('notice', f'{d} : {"extrait d’essai" if MAX_CHARS else "épisode"} produit : {meta["duree_s"] // 60} min {meta["duree_s"] % 60:02d} s, {meta["octets"]} octets.')
    return True


def main():
    a = sys.argv[1:]
    flags = {x for x in a if x.startswith('--')}
    eds = [x for x in a if not x.startswith('--')] or editions()[-1:]
    if '--check' in flags:
        ko = False
        for d in eds:
            pod, _ = charger(d)
            if pod is None: print(f'{d} : pas de podcast.json'); continue
            err, warn, mots = controler(pod)
            print(f'{d} : {len(pod.get("repliques") or [])} répliques, {mots} mots (≈ {mots / 150:.0f} min)')
            for w in warn: print('  avertissement :', w)
            for e in err: print('  ERREUR :', e)
            ko |= bool(err)
        sys.exit(1 if ko else 0)
    nouveau = False
    for d in eds:
        nouveau |= produire(d, dry='--dry-run' in flags, force='--force' in flags)
    if os.environ.get('GITHUB_OUTPUT'):
        open(os.environ['GITHUB_OUTPUT'], 'a').write(f'new={"1" if nouveau else "0"}\n')


if __name__ == '__main__':
    try: main()
    except SystemExit as e:
        if e.code not in (None, 0) and not isinstance(e.code, int): bilan('error', str(e))
        raise
