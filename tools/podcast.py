#!/usr/bin/env python3
"""Épisode audio de la revue : content/AAAA-MM-JJ/podcast.json -> episode.mp3 (+ episode.json).

Usage :
  python3 tools/podcast.py --check [AAAA-MM-JJ]   contrôle le script (sans appel réseau)
  python3 tools/podcast.py [AAAA-MM-JJ]           produit l'épisode (par défaut : dernière édition)
  python3 tools/podcast.py --dry-run [...]        chaîne complète sans appel à ElevenLabs (audio muet)
  python3 tools/podcast.py --force [...]          régénère même si l'épisode est à jour

Synthèse vocale : API ElevenLabs « Text to Dialogue » (plusieurs voix dans une même requête).
Variables : ELEVENLABS_API_KEY (clé), ELEVENLABS_VOICE_A et ELEVENLABS_VOICE_B (identifiants des
voix de Claire et de Thomas), ELEVENLABS_MODEL (facultatif, défaut ci-dessous).
Assemblage et encodage MP3 : ffmpeg.
L'épisode n'est régénéré que si podcast.json a changé (empreinte dans episode.json) : pas de
double facturation quand le workflow est relancé.
Ne bloque jamais la revue : sans clé ou sans podcast.json, le script s'arrête proprement (code 0).
"""
import datetime, hashlib, io, json, os, re, shutil, subprocess, sys, tempfile, time, wave
import urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, 'content')
LEXIQUE = os.path.join(ROOT, 'tools', 'prononciation.json')
ENDPOINT = 'https://api.elevenlabs.io/v1/text-to-dialogue'
MODELE = os.environ.get('ELEVENLABS_MODEL') or 'eleven_v3'
RATE = 24000                     # Hz, mono, 16 bits : sortie demandée (output_format=pcm_24000)
CHUNK_MAX = 1700                 # caractères par requête (limite de l'API : 2 000)
PAUSE = 0.35                     # secondes de silence entre deux requêtes

# Voix : identifiants ElevenLabs lus dans l'environnement ; un podcast.json peut les remplacer
# par une clé "voix" ({"A": {"voice": "…"}}).
VOIX = {
    'A': {'nom': 'Claire', 'voice': os.environ.get('ELEVENLABS_VOICE_A', '').strip()},
    'B': {'nom': 'Thomas', 'voice': os.environ.get('ELEVENLABS_VOICE_B', '').strip()},
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
    return json.loads(raw.decode('utf-8')), hashlib.sha256(raw).hexdigest()


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
    if not MOTS_MIN <= mots <= MOTS_MAX: warn.append(f'{mots} mots : hors de la plage visée ({MOTS_MIN}-{MOTS_MAX})')
    return err, warn, mots


# ------------------------------------------------------------------ texte lu
def lexique():
    try: L = json.load(open(LEXIQUE, encoding='utf-8'))
    except FileNotFoundError: return []
    return [(re.compile(r'(?<![\w-])' + k + r'(?![\w-])'), v) for k, v in L.items() if not k.startswith('_')]


def dire(t, lex):
    t = t.replace('’', "'").replace(' ', ' ')
    for rx, v in lex: t = rx.sub(v, t)
    return t


def decouper(reps):
    """Regroupe les répliques en requêtes de taille raisonnable, sans couper une réplique."""
    out, cur, n = [], [], 0
    for r in reps:
        if cur and n + len(r['t']) > CHUNK_MAX:
            out.append(cur); cur, n = [], 0
        cur.append(r); n += len(r['t'])
    if cur: out.append(cur)
    return out


# ------------------------------------------------------------------ ElevenLabs
def requete(chunk, voix, lex, cle, precedents):
    """Une requête Text to Dialogue ; renvoie (audio PCM 16 bits mono 24 kHz, identifiant de requête)."""
    inputs = [{'text': dire(r['t'], lex), 'voice_id': voix[r['v']]['voice']} for r in chunk]
    n = sum(len(x['text']) for x in inputs)
    if n > 2000: raise SystemExit(f'Requête de {n} caractères : au-delà de la limite de 2 000 (réduire CHUNK_MAX)')
    body = {'inputs': inputs, 'model_id': MODELE, 'language_code': 'fr'}
    if precedents: body['previous_request_ids'] = precedents[-3:]
    data = json.dumps(body).encode('utf-8')
    for essai in range(1, 6):
        req = urllib.request.Request(ENDPOINT + '?output_format=pcm_24000', data=data, method='POST',
                                     headers={'xi-api-key': cle, 'Content-Type': 'application/json', 'Accept': 'audio/*'})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                pcm = r.read()
                if (r.headers.get('Content-Type') or '').startswith('application/json'):
                    raise SystemExit('Réponse d\'ElevenLabs sans audio : ' + pcm[:600].decode('utf-8', 'replace'))
                if pcm[:4] == b'RIFF':
                    with wave.open(io.BytesIO(pcm)) as w: pcm = w.readframes(w.getnframes())
                if len(pcm) % 2: pcm = pcm[:-1]
                return pcm, r.headers.get('request-id') or r.headers.get('x-request-id')
        except urllib.error.HTTPError as e:
            detail = e.read().decode('utf-8', 'replace')[:600]
            if e.code in (429, 500, 502, 503, 504) and essai < 5:
                log(f'  HTTP {e.code}, nouvel essai dans {10 * essai} s'); time.sleep(10 * essai); continue
            raise SystemExit(f'ElevenLabs a refusé la requête (HTTP {e.code}) : {detail}')
        except (urllib.error.URLError, TimeoutError) as e:
            if essai < 5: log(f'  {e}, nouvel essai dans {10 * essai} s'); time.sleep(10 * essai); continue
            raise SystemExit(f'ElevenLabs injoignable : {e}')


def muet(chunk):
    """--dry-run : silence de durée réaliste (≈ 15 caractères lus par seconde), aucun appel réseau."""
    n = sum(len(r['t']) for r in chunk)
    return b"\x00\x00" * int(RATE * n / 15)


# ------------------------------------------------------------------ assemblage
def assembler(morceaux, mp3, meta):
    silence = b'\x00\x00' * int(RATE * PAUSE)
    pcm = silence.join(morceaux)
    with tempfile.TemporaryDirectory() as t:
        wav = os.path.join(t, 'episode.wav')
        with wave.open(wav, 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(pcm)
        tmp = mp3 + '.tmp.mp3'
        cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', wav,
               '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', '-ar', '44100', '-ac', '1', '-c:a', 'libmp3lame', '-b:a', '64k',
               '-metadata', f'title={meta["titre"]}', '-metadata', 'artist=Software Compliance',
               '-metadata', f'album=Software Compliance', '-metadata', f'date={meta["date"][:4]}',
               '-metadata', 'comment=Voix de synthèse', '-id3v2_version', '3', tmp]
        subprocess.run(cmd, check=True)
        os.replace(tmp, mp3)
    return len(pcm) / 2 / RATE


def produire(d, dry=False, force=False):
    pod, sha = charger(d)
    if pod is None: bilan('notice', f'{d} : pas de podcast.json, rien à faire.'); return False
    err, warn, mots = controler(pod)
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
    if manque and not dry: bilan('warning', f'{d} : identifiant de voix manquant pour {", ".join(manque)} (ELEVENLABS_VOICE_A / _B), épisode non produit.'); return False
    lex = lexique()
    reps = extrait(pod['repliques'])
    if MAX_CHARS:
        mots = sum(len(r['t'].split()) for r in reps)
        log(f'{d} : MODE ESSAI (PODCAST_MAX_CHARS={MAX_CHARS}) : {len(reps)} réplique(s) sur {len(pod["repliques"])}, {sum(len(r["t"]) for r in reps)} caractères')
    chunks = decouper(reps)
    log(f'{d} : {len(reps)} répliques, {mots} mots, {len(chunks)} requête(s) {"(essai à blanc)" if dry else "à " + MODELE}')
    morceaux, ids = [], []
    for i, c in enumerate(chunks, 1):
        log(f'  requête {i}/{len(chunks)} ({sum(len(r["t"]) for r in c)} caractères)')
        if dry: morceaux.append(muet(c)); continue
        pcm, rid = requete(c, voix, lex, cle, ids)
        morceaux.append(pcm)
        if rid: ids.append(rid)
    sortie = os.path.join(tempfile.gettempdir(), f'episode-{d}.mp3') if dry else mp3
    duree = assembler(morceaux, sortie, {'titre': pod['titre'], 'date': d})
    meta = {'duree_s': round(duree), 'octets': os.path.getsize(sortie), 'mots': mots, 'modele': 'essai à blanc' if dry else MODELE,
            'voix': {k: {'nom': v['nom'], 'voice': v.get('voice', '')} for k, v in voix.items()},
            'genere_le': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'sha_script': sha, 'extrait': bool(MAX_CHARS), 'repliques': len(reps)}
    if dry:
        log(f'{d} : essai à blanc réussi : {sortie} ({meta["octets"]} octets, {duree / 60:.1f} min). Aucun fichier écrit dans content/.')
        return False
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
