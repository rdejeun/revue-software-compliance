#!/usr/bin/env python3
"""Épisode audio de la revue : content/AAAA-MM-JJ/podcast.json -> episode.m4a (+ episode.json).

Usage :
  python3 tools/podcast.py --check [AAAA-MM-JJ]   contrôle le script (sans appel réseau)
  python3 tools/podcast.py [AAAA-MM-JJ]           produit l'épisode (par défaut : dernière édition)
  python3 tools/podcast.py --dry-run [...]        chaîne complète sans appel à ElevenLabs (voix synthétiques)
  python3 tools/podcast.py --force [...]          régénère même si l'épisode est à jour

Synthèse vocale : API ElevenLabs « Text to Dialogue » (plusieurs voix dans une même requête).
Variables : ELEVENLABS_API_KEY (clé), ELEVENLABS_VOICE_FEMALE et ELEVENLABS_VOICE_MALE (identifiants
des voix de Julie, voix A, et de Guillaume, voix B), ELEVENLABS_MODEL (facultatif, défaut eleven_v4 ; « eleven_v3 » pour revenir en arrière).
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
SANS_CONTINUITE = {'eleven_v3', 'eleven_v4'}   # v4 : par prudence, non documenté pour le dialogue
MODELE = os.environ.get('ELEVENLABS_MODEL') or 'eleven_v4'   # v4 : essai du 5 octobre 2026 concluant (dialogue en français)
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
def titre_episode(n,titre):
    """« Épisode 1 : le CRA en marche… » à partir du titre de podcast.json, sans « N° 1 – » ni « Revue Software Compliance, numéro 1 : »"""
    t=re.sub(r'^\s*(?:N°\s*\d+\s*[-–—:]\s*)?(?:Revue\s+(?:de\s+presse\s+)?Software\s+Compliance\s*,?\s*(?:numéro|n°)\s*[\w-]+\s*[:–—-]\s*)?','',titre or '',flags=re.I)
    return f'Épisode {n} : {t.strip()}'


def numero(d):
    """numéro de l'édition (meta.json), ou None"""
    try: return json.load(open(os.path.join(CONTENT, d, 'meta.json'), encoding='utf-8')).get('n')
    except (OSError, ValueError): return None


def charger(d, chemin=None):
    p = chemin or os.path.join(CONTENT, d, 'podcast.json')
    if not os.path.isfile(p): return None, None
    raw = open(p, 'rb').read()
    pod = json.loads(raw.decode('utf-8'))
    pod = preparer(pod)
    return pod, hashlib.sha256(raw).hexdigest()


def preparer(pod):
    # {"sujet": "…", "court": "…"} : marque de changement de sujet (non lue) ; « court » : libellé du signet dans le
    # lecteur (facultatif, sinon le début du sujet avant « : »). Chaque réplique reçoit le numéro de son sujet.
    reps, n, noms, courts = [], 0, [], []
    for r in pod.get('repliques') or []:
        if 'sujet' in r and 't' not in r:
            if reps or noms: n += 1
            noms.append(r['sujet']); courts.append(r.get('court') or r['sujet'].split(' : ')[0]); continue
        reps.append({**r, '_s': n})
    pod['repliques'], pod['_sujets'], pod['_courts'] = reps, noms, courts
    return pod


# Balises audio d'Eleven v3 autorisées (jouées, pas lues). Toute autre balise est refusée.
BALISES = {'curious', 'thoughtful', 'surprised', 'chuckles', 'sighs', 'exhales'}
# Quota : chaque type de balise au plus une fois par épisode, et seulement à dessein pédagogique
# (par exemple, une respiration au milieu d'une longue explication).
HESITATIONS_MAX = 3                # « euh », « hum »… écrits dans le texte (avertissement au-delà)
RX_HESITATION = re.compile(r"(?<![\w-])(?:euh|heu|hum|hmm)(?![\w-])", re.I)


_UNITES = ['zéro', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf', 'dix', 'onze', 'douze', 'treize',
           'quatorze', 'quinze', 'seize', 'dix-sept', 'dix-huit', 'dix-neuf']
_DIZAINES = {2: 'vingt', 3: 'trente', 4: 'quarante', 5: 'cinquante', 6: 'soixante', 8: 'quatre-vingt'}


def en_lettres(n):
    """1 -> « un », 21 -> « vingt-et-un », 80 -> « quatre-vingts » (de 0 à 999, pour le numéro d'édition)"""
    if n < 20: return _UNITES[n]
    if n < 100:
        d, u = divmod(n, 10)
        if d in (7, 9): d, u = d - 1, u + 10
        base = _DIZAINES[d]
        if u == 0: return base + ('s' if d == 8 else '')
        return base + ('-et-' if u in (1, 11) and d != 8 else '-') + _UNITES[u]
    c, r = divmod(n, 100)
    tete = 'cent' if c == 1 else _UNITES[c] + '-cent' + ('s' if r == 0 else '')
    return tete + ('' if r == 0 else '-' + en_lettres(r))


RX_NUMERO = re.compile(r"\b(?:numéro|N°)\s*(\d+|[a-zé-]+)", re.I)


def controler(pod, n=None):
    err, warn = [], []
    if n is not None:   # le numéro annoncé doit être celui de l'édition (meta.json)
        for ou, t in [('titre', pod.get('titre') or ''), ('description', pod.get('description') or '')] + \
                     [(f'réplique {i + 1}', r.get('t') or '') for i, r in enumerate(pod.get('repliques') or [])]:
            for m in RX_NUMERO.finditer(t):
                v = m.group(1).lower()
                if v.isdigit(): ok = int(v) == n
                elif v.replace('-', '') in {en_lettres(k).replace('-', '') for k in range(1000)}: ok = v.replace('-', '') == en_lettres(n).replace('-', '')
                else: continue   # « numéro de plaque », « un nouveau numéro »…
                if not ok: err.append(f'{ou} : « {m.group(0)} » ne correspond pas au numéro de l’édition ({n})')
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
        t = r.get('t') or ''
        for b in re.findall(r'\[([^\]]*)\]', t):
            if b not in BALISES: err.append(f'réplique {i + 1} : balise [{b}] non autorisée (autorisées : {", ".join(sorted(BALISES))})')
        if re.search(r'[{}<>*_#]|https?://', re.sub(r'\[[^\]]*\]', '', t)) or t.count('[') != t.count(']'): err.append(f'réplique {i + 1} : lien ou mise en forme à retirer (texte lu à voix haute)')
        m_ = re.search(r'\b(avérée?s?|potentiel(?:le)?s?)\b', t, re.I)
        if m_: err.append(f'réplique {i + 1} : « {m_.group(1)} » à éviter : dire l’impact naturellement (indicatif pour ce qui est déjà acquis, conditionnel pour ce qui pourrait arriver), sans l’étiqueter')
    from collections import Counter
    for b, n in Counter(x for r in reps for x in re.findall(r'\[([^\]]*)\]', r.get('t') or '')).items():
        if n > 1: err.append(f'balise [{b}] utilisée {n} fois : une seule fois par épisode, à dessein pédagogique')
    hes = sum(len(RX_HESITATION.findall(r.get('t') or '')) for r in reps)
    if hes > HESITATIONS_MAX: warn.append(f'{hes} hésitations écrites (« euh », « hum ») : {HESITATIONS_MAX} au plus par épisode')
    mots = sum(len(re.sub(r'\[[^\]]*\]', '', r.get('t') or '').split()) for r in reps)
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


def chapitres(pod, chunks, blocs, offs_s, intro_s):
    """Début de chaque sujet dans l'épisode (signets du lecteur) : première réplique du sujet, d'après les
    horodatages d'ElevenLabs (dialogue_input_index), le début de son bloc dans la voix et la durée de l'habillage."""
    noms, courts, vus, ch = pod.get('_sujets') or [], pod.get('_courts') or [], set(), []
    for k, (c, b) in enumerate(zip(chunks, blocs)):
        for i, r in enumerate(c):
            s = r.get('_s')
            if s is None or s in vus or s >= len(noms): continue
            vus.add(s)
            t = [x['start_time_seconds'] for x in b['segments'] if x.get('dialogue_input_index') == i]
            ch.append({'titre': noms[s], 'court': courts[s] if s < len(courts) else noms[s], 'debut_s': 0.0 if not ch else round(intro_s + offs_s[k] + (min(t) if t else 0), 1)})
    return ch


def produire(d, dry=False, force=False):
    pod, sha = charger(d)
    if pod is None: bilan('notice', f'{d} : pas de podcast.json, rien à faire.'); return False
    err, warn, mots = controler(pod, numero(d))
    sha = hashlib.sha256((sha + json.dumps(regles(), sort_keys=True, ensure_ascii=False) + MODELE).encode('utf-8')).hexdigest()  # lexique et modèle comptent aussi
    # un extrait n'est jamais pris pour l'épisode complet ; un plafond qui ne coupe rien ne compte pas
    # (changer PODCAST_MAX_CHARS ne refait pas un épisode déjà complet)
    coupe = len(extrait(pod['repliques'])) < len(pod['repliques'])
    if coupe: sha += f':essai-{MAX_CHARS}'
    for w in warn: log(f'{d} : avertissement : {w}')
    if err: raise SystemExit(f'{d} : script invalide :\n- ' + '\n- '.join(err))
    dossier = os.path.join(CONTENT, d)
    mp3, info = os.path.join(dossier, 'episode.m4a'), os.path.join(dossier, 'episode.json')
    if not force and not dry and os.path.isfile(mp3) and os.path.isfile(info):
        avant = json.load(open(info, encoding='utf-8'))
        complet = avant.get('repliques') == len(pod['repliques'])   # l'épisode existant contient toutes les répliques
        if avant.get('sha_script') == sha or (not coupe and complet and str(avant.get('sha_script', '')).split(':essai-')[0] == sha):
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
    if coupe:
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
    sortie = os.path.join(travail, 'out', 'episode.m4a')
    M = mixage.produire(blocs, ids_voix, sortie, travail, {'titre': pod['titre'], 'date': d, 'n': ''}, sortie_brute=os.path.join(travail, 'out', 'episode_sans_traitement.m4a'))
    ok, ecarts, resume = mixage.qc(M, sortie, ' '.join(r['t'] for r in reps), travail)
    duree = M['duree_blocs_s'] + M.get('habillage_s', 0)
    meta = {'duree_s': round(duree), 'octets': os.path.getsize(sortie), 'mots': mots, 'modele': 'essai à blanc' if dry else MODELE, 'seed': SEED,
            'voix': {k: {'nom': v['nom'], 'voice': v.get('voice', '')} for k, v in voix.items()},
            'genere_le': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'sha_script': sha, 'extrait': coupe, 'repliques': len(reps),
            'prononciation': 'aucune (essai à blanc)' if dry else ('dictionnaire ElevenLabs ' + loc['version_id'] if loc else 'remplacements locaux'),
            'qc': resume, 'requetes': len(chunks), 'chapitres': chapitres(pod, chunks, blocs, M['offs_s'], M.get('intro_s', 0))}
    if dry:
        log(f'{d} : essai à blanc terminé : {sortie} ({duree / 60:.1f} min), contrôle {"réussi" if ok else "en écart"} ; rapport : {travail}/qc_report.md. Aucun fichier écrit dans content/.')
        return False
    if not ok:
        bilan('error', f'{d} : épisode produit mais non publié, contrôle qualité en écart : ' + ' ; '.join(ecarts) + '. Détail dans l’artefact « podcast » de l’exécution.')
        return False
    for e in ecarts: bilan('warning', f'{d} : contrôle qualité, écart non bloquant : {e}')
    shutil.copyfile(sortie, mp3); meta['octets'] = os.path.getsize(mp3); meta['fichier'] = 'episode.m4a'
    ancien = os.path.join(dossier, 'episode.mp3')
    if os.path.isfile(ancien): os.remove(ancien)   # ancien format, remplacé
    json.dump(meta, open(info, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    bilan('notice', f'{d} : {"extrait d’essai" if coupe else "épisode"} produit : {meta["duree_s"] // 60} min {meta["duree_s"] % 60:02d} s, {meta["octets"]} octets.')
    return True


def essai(chemin):
    """Essai d'écoute : plusieurs versions d'un même court dialogue (ex. sans / avec balises audio), produites par
    la chaîne complète dans essais/sorties/<nom>-<version>.m4a (+ rapport). Ne touche à aucune édition."""
    E = json.load(open(chemin, encoding='utf-8')); nom = os.path.splitext(os.path.basename(chemin))[0]
    cle = os.environ.get('ELEVENLABS_API_KEY', '').strip()
    if not cle: raise SystemExit('ELEVENLABS_API_KEY absente')
    voix = dict(VOIX)
    if any(not v.get('voice') for v in voix.values()): raise SystemExit('identifiants de voix manquants')
    sorties = os.path.join(ROOT, 'essais', 'sorties')
    versions = {k: preparer({'titre': E.get('titre', nom), 'description': 'essai', 'repliques': v}) for k, v in E['versions'].items()
                if not os.path.isfile(os.path.join(sorties, f'{nom}-{k}.m4a'))}   # déjà produite : pas refacturée
    if not versions: log(f'essai {nom} : toutes les versions existent déjà'); return
    for k, pod in versions.items():
        err, warn, _ = controler(pod)
        for w in warn: log(f'essai {k} : avertissement : {w}')
        if err: raise SystemExit(f'essai {k} : ' + ' ; '.join(err))
    lexl = lexique()
    besoin = int(sum(len(dire(r['t'], lexl)) for p in versions.values() for r in p['repliques']) * MARGE)
    reste, raz = solde(cle)
    if reste < besoin: bilan('warning', f'essai : solde insuffisant ({reste} restants, {besoin} nécessaires)'); return
    log(f'essai : solde {reste} caractères, besoin {besoin} : ok')
    loc = dictionnaire(cle); lex = [] if loc else lexl
    import mixage
    os.makedirs(sorties, exist_ok=True)
    global MODELE
    defaut = MODELE
    for k, pod in versions.items():
        MODELE = (E.get('modeles') or {}).get(k) or defaut      # modèle propre à une version (ex. eleven_v4)
        log(f'essai {nom} ({k}) : modèle {MODELE}')
        travail = os.path.join(ROOT, 'build', 'essais', nom, k); shutil.rmtree(travail, ignore_errors=True); os.makedirs(os.path.join(travail, 'raw'))
        blocs, ids = [], []
        for i, c in enumerate(decouper(pod['repliques']), 1):
            base = os.path.join(travail, 'raw', f'chunk_{i:02d}')
            segs, rid = requete(c, voix, lex, cle, ids, loc, base)
            if rid: ids.append(rid)
            blocs.append({'mp3': base + '.mp3', 'segments': segs})
        out = os.path.join(sorties, f'{nom}-{k}.m4a')
        M = mixage.produire(blocs, {kk: vv['voice'] for kk, vv in voix.items()}, out, travail, {'titre': f'Essai {nom} ({k})', 'date': '2026', 'n': ''},
                            sortie_brute=os.path.join(sorties, f'{nom}-{k}-sans-traitement.m4a') if E.get('sans_traitement') else None)
        ok, ecarts, resume = mixage.qc(M, out, ' '.join(r['t'] for r in pod['repliques']), travail)
        shutil.copyfile(os.path.join(travail, 'qc_report.md'), os.path.join(sorties, f'{nom}-{k}-qc.md'))
        bilan('notice', f'essai {nom} ({k}, {MODELE}) : {M["duree_blocs_s"]:.0f} s ; contrôle {"ok" if ok else "en écart : " + " ; ".join(ecarts)}')


def main():
    a = sys.argv[1:]
    flags = {x for x in a if x.startswith('--')}
    if '--essai' in flags:
        for f in [x for x in a if not x.startswith('--')]: essai(f)
        return
    eds = [x for x in a if not x.startswith('--')] or editions()[-1:]
    if '--check' in flags:
        ko = False
        for d in eds:
            pod, _ = charger(d)
            if pod is None: print(f'{d} : pas de podcast.json'); continue
            err, warn, mots = controler(pod, numero(d))
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
