#!/usr/bin/env python3
"""Épisode audio de la revue : content/AAAA-MM-JJ/podcast.json -> episode.mp3 (+ episode.json).

Usage :
  python3 tools/podcast.py --check [AAAA-MM-JJ]   contrôle le script (sans appel réseau)
  python3 tools/podcast.py [AAAA-MM-JJ]           produit l'épisode (par défaut : dernière édition)
  python3 tools/podcast.py --dry-run [...]        chaîne complète sans appel à Gemini (audio muet)
  python3 tools/podcast.py --force [...]          régénère même si l'épisode est à jour

Synthèse vocale : API Gemini (deux voix dans une même requête). Clé : variable GEMINI_API_KEY.
Modèle : variable GEMINI_TTS_MODEL (défaut ci-dessous). Assemblage et encodage MP3 : ffmpeg.
L'épisode n'est régénéré que si podcast.json a changé (empreinte dans episode.json) : pas de
double facturation quand le workflow est relancé.
Ne bloque jamais la revue : sans clé ou sans podcast.json, le script s'arrête proprement (code 0).
"""
import base64, datetime, hashlib, io, json, os, re, shutil, subprocess, sys, tempfile, time, wave
import urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, 'content')
LEXIQUE = os.path.join(ROOT, 'tools', 'prononciation.json')
ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/interactions'
MODELE = os.environ.get('GEMINI_TTS_MODEL') or 'gemini-3.8-flash-tts'
RATE = 24000                     # Hz, mono, 16 bits : format de sortie de Gemini TTS
CHUNK_MAX = 1800                 # caractères par requête (≈ 1 min 30 d'audio)
PAUSE = 0.45                     # secondes de silence entre deux requêtes

# Voix par défaut ; un podcast.json peut les remplacer par une clé "voix".
VOIX = {
    'A': {'nom': 'Claire', 'voice': 'Aoede', 'style': 'en français de France, curieuse et détendue, ton de conversation naturel'},
    'B': {'nom': 'Thomas', 'voice': 'Charon', 'style': 'en français de France, posé et pédagogue, chaleureux, sans emphase'},
}
MOTS_MIN, MOTS_MAX = 900, 1800   # ≈ 6 à 12 minutes


def editions():
    return sorted(d for d in os.listdir(CONTENT) if re.fullmatch(r'\d{4}-\d{2}-\d{2}', d))


def log(*a): print(*a, flush=True)


# ------------------------------------------------------------------ contrôle
def charger(d):
    p = os.path.join(CONTENT, d, 'podcast.json')
    if not os.path.isfile(p): return None, None
    raw = open(p, 'rb').read()
    return json.loads(raw.decode('utf-8')), hashlib.sha256(raw).hexdigest()


def controler(pod):
    err, warn = [], []
    voix = {**VOIX, **(pod.get('voix') or {})}
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
    if reps and 'synthèse' not in (reps[0].get('t') or '').lower():
        err.append('la première réplique doit annoncer des voix de synthèse')
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


# ------------------------------------------------------------------ Gemini
def requete(chunk, voix, lex, cle):
    body = {
        'model': MODELE,
        'input': [{'type': 'user_input', 'content': [
            {'type': 'text', 'text': dire(r['t'], lex),
             'annotations': [{'type': 'speech_metadata', 'speaker': voix[r['v']]['nom'], 'style': voix[r['v']]['style']}]}
            for r in chunk]}],
        'response_format': {'type': 'audio'},
        'generation_config': {'speech_config': {'mode': 'conversational', 'speakers': [
            {'speaker': v['nom'], 'voice': v['voice']} for v in voix.values()]}},
    }
    data = json.dumps(body).encode('utf-8')
    for essai in range(1, 6):
        req = urllib.request.Request(ENDPOINT, data=data, method='POST',
                                     headers={'x-goog-api-key': cle, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return extraire(json.load(r))
        except urllib.error.HTTPError as e:
            detail = e.read().decode('utf-8', 'replace')[:600]
            if e.code in (429, 500, 502, 503, 504) and essai < 5:
                log(f'  HTTP {e.code}, nouvel essai dans {10 * essai} s'); time.sleep(10 * essai); continue
            raise SystemExit(f'Gemini a refusé la requête (HTTP {e.code}) : {detail}')
        except (urllib.error.URLError, TimeoutError) as e:
            if essai < 5: log(f'  {e}, nouvel essai dans {10 * essai} s'); time.sleep(10 * essai); continue
            raise SystemExit(f'Gemini injoignable : {e}')


def extraire(rep):
    """Renvoie l'audio (octets PCM 16 bits mono) de la dernière sortie audio de la réponse."""
    trouves = []
    def parcourir(x):
        if isinstance(x, dict):
            if x.get('type') == 'audio' and isinstance(x.get('data'), str): trouves.append(x)
            for v in x.values(): parcourir(v)
        elif isinstance(x, list):
            for v in x: parcourir(v)
    parcourir(rep)
    if not trouves: raise SystemExit('Réponse de Gemini sans audio : ' + json.dumps(rep)[:600])
    brut = base64.b64decode(trouves[-1]['data'])
    if brut[:4] == b'RIFF':
        with wave.open(io.BytesIO(brut)) as w:
            if w.getnchannels() != 1 or w.getsampwidth() != 2: raise SystemExit('Format WAV inattendu')
            if w.getframerate() != RATE: raise SystemExit(f'Fréquence inattendue : {w.getframerate()} Hz')
            return w.readframes(w.getnframes())
    return brut  # L16 brut, 24 kHz mono


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
    if pod is None: log(f'{d} : pas de podcast.json, rien à faire.'); return False
    err, warn, mots = controler(pod)
    for w in warn: log(f'{d} : avertissement : {w}')
    if err: raise SystemExit(f'{d} : script invalide :\n- ' + '\n- '.join(err))
    dossier = os.path.join(CONTENT, d)
    mp3, info = os.path.join(dossier, 'episode.mp3'), os.path.join(dossier, 'episode.json')
    if not force and not dry and os.path.isfile(mp3) and os.path.isfile(info):
        if json.load(open(info, encoding='utf-8')).get('sha_script') == sha:
            log(f'{d} : épisode déjà à jour.'); return False
    cle = os.environ.get('GEMINI_API_KEY', '').strip()
    if not dry and not cle: log(f'{d} : GEMINI_API_KEY absente, épisode non produit.'); return False
    if not shutil.which('ffmpeg'): raise SystemExit('ffmpeg introuvable')
    voix = {**VOIX, **(pod.get('voix') or {})}
    lex = lexique()
    chunks = decouper(pod['repliques'])
    log(f'{d} : {len(pod["repliques"])} répliques, {mots} mots, {len(chunks)} requête(s) {"(essai à blanc)" if dry else "à " + MODELE}')
    morceaux = []
    for i, c in enumerate(chunks, 1):
        log(f'  requête {i}/{len(chunks)} ({sum(len(r["t"]) for r in c)} caractères)')
        morceaux.append(muet(c) if dry else requete(c, voix, lex, cle))
    sortie = os.path.join(tempfile.gettempdir(), f'episode-{d}.mp3') if dry else mp3
    duree = assembler(morceaux, sortie, {'titre': pod['titre'], 'date': d})
    meta = {'duree_s': round(duree), 'octets': os.path.getsize(sortie), 'mots': mots, 'modele': 'essai à blanc' if dry else MODELE,
            'voix': {k: {'nom': v['nom'], 'voice': v['voice']} for k, v in voix.items()},
            'genere_le': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'sha_script': sha}
    if dry:
        log(f'{d} : essai à blanc réussi : {sortie} ({meta["octets"]} octets, {duree / 60:.1f} min). Aucun fichier écrit dans content/.')
        return False
    json.dump(meta, open(info, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    log(f'{d} : épisode produit : {meta["duree_s"] // 60} min {meta["duree_s"] % 60:02d} s, {meta["octets"]} octets.')
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
    main()
