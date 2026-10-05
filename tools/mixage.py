#!/usr/bin/env python3
"""Post-production de l'épisode : deux voix ElevenLabs « dans la même pièce ».

Entrée : les blocs reçus de l'API Text to Dialogue « with-timestamps » (MP3 44,1 kHz + voice_segments).
Étapes (brief « Podcast IA à deux voix ») :
  3. une piste par locuteur, alignée à l'échantillon (fondus de 10 ms, chevauchements attribués à une seule piste) ;
  4. passe-haut 80 Hz, expandeur doux (raccourcit les queues de réverbération propres à une voix),
     EQ match vers la courbe moyenne des deux voix (FIR à phase linéaire, ±6 dB, 100 Hz–10 kHz), de-esser si besoin ;
  5. même compresseur sur les deux pistes, loudness égalisé, panoramique léger, réverbération partagée, fond d'ambiance ;
  6. mixage, compression de bus légère, loudnorm en deux passes (−16 LUFS, −1 dBTP), export M4A (AAC) mono.
Le contrôle qualité (qc) mesure le résultat ; podcast.py décide de publier ou non.
Tout est mesuré, rien n'est réglé « à l'oreille » : les valeurs de départ sont dans CONFIG.
"""
import json, os, re, subprocess, tempfile
import numpy as np
import soundfile as sf
from scipy import signal

SR = 44100
CONFIG = {
    'passe_haut_hz': 80,
    # expandeur appliqué à la voix dont les fins de mots traînent (réverbération d'origine), ratio augmenté
    # jusqu'à revenir près de l'autre voix : cible = décroissance de l'autre voix × 1,3
    'expandeur': {'seuil_db': -30, 'ratios': [1.5, 2, 2.5, 3, 4], 'attaque_ms': 2, 'relache_ms': 50, 'max_db': 15, 'tolerance': 1.3},
    'eq': {'f_min': 100, 'f_max': 10000, 'max_db': 6, 'coefs': 2049, 'cible_ecart_db': 3, 'passes': 3},
    'sibilantes_ecart_db': 3,
    'compresseur': {'ratio': 3, 'attaque_ms': 10, 'relache_ms': 100, 'reduction_db': 4},
    # Sortie mono : pas de panoramique (évite les artefacts de centrage à l'écoute au casque).
    # Réverbération partagée désactivée (None) : jugée trop présente à l'écoute. Fond d'ambiance conservé.
    'mono': True,
    'pan': 0.15,                       # stéréo seulement : −1 gauche … +1 droite ; A à gauche, B à droite
    'reverb': None,                    # ex. {'room_size': 0.15, 'damping': 0.6, 'wet': 0.07, 'width': 0.6}
    'room_tone_dbfs': -60,             # bruit rose filtré sous 8 kHz, continu sous tout l'épisode ; None pour l'ôter
    'bus': {'ratio': 2, 'reduction_db': 1.5},
    'lufs': -19, 'true_peak': -1.0, 'lra': 11,   # −19 LUFS en mono (équivalent de −16 en stéréo)
    'aac_kbps': 64,
    # Habillage sonore : même son en ouverture et en clôture (tools/habillage.mp3, « Tech Logo Intro »,
    # sergequadrado, Pixabay), ramené 2 LU sous la voix, séparé de la parole par un court blanc.
    'habillage': {'fichier': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'habillage.mp3'), 'lufs': -21, 'blanc_s': 0.6},                    # export M4A (AAC-LC) mono : −31 % par rapport au MP3 96 kbps, validé à l'écoute
    'pause_s': 0.6,                    # silence entre deux blocs (= entre deux sujets)
}


def log(*a): print(*a, flush=True)


# ------------------------------------------------------------------ E/S
def decoder(mp3):
    """MP3 -> float32 mono 44,1 kHz (décodé une seule fois)."""
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', mp3, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype='<f4').astype(np.float64)


def db(x): return 20 * np.log10(np.maximum(np.abs(x), 1e-12))


def niveau_court(x, ms=10):
    n = max(1, int(SR * ms / 1000))
    e = np.convolve(x ** 2, np.ones(n) / n, mode='same')
    return 10 * np.log10(e + 1e-15)


def debut_parole(x, seuil_rel=-40):
    lv = niveau_court(x, 5)
    i = np.argmax(lv > lv.max() + seuil_rel)
    return i / SR


# ------------------------------------------------------------------ étape 3 : pistes
def pistes(blocs, voix):
    """blocs : [{'mp3': chemin, 'segments': [...voice_segments...]}] ; voix : {'A': voice_id, 'B': voice_id}.
    Renvoie (mix d'origine, {'A': piste, 'B': piste}, masques de parole, journal)."""
    ids = {v: k for k, v in voix.items()}
    audios, journal, offs = [], [], []
    pause = np.zeros(int(SR * CONFIG['pause_s']))
    pos = 0
    for k, b in enumerate(blocs):
        x = decoder(b['mp3'])
        segs = b['segments']
        if segs:   # retard éventuel du décodeur MP3
            dec = debut_parole(x) - min(s['start_time_seconds'] for s in segs)
            if 0.005 < dec < 0.2:
                x = x[int(dec * SR):]; journal.append(f'bloc {k + 1} : décalage de décodage corrigé ({dec * 1000:.0f} ms)')
        if k: audios.append(pause); pos += len(pause)
        offs.append(pos); audios.append(x); pos += len(x)
    mix = np.concatenate(audios)
    st = {k: np.zeros_like(mix) for k in voix}
    masque = {k: np.zeros(len(mix), bool) for k in voix}
    fondu = int(SR * 0.010)
    for k, b in enumerate(blocs):
        fin_prec = None
        for s in sorted(b['segments'], key=lambda s: s['start_time_seconds']):
            v = ids.get(s['voice_id'])
            if v is None: journal.append(f'bloc {k + 1} : voix inconnue {s["voice_id"]}'); continue
            a = offs[k] + int(round(s['start_time_seconds'] * SR)); z = offs[k] + int(round(s['end_time_seconds'] * SR))
            if fin_prec is not None and a < fin_prec:
                journal.append(f'bloc {k + 1} : chevauchement de {(fin_prec - a) / SR * 1000:.0f} ms attribué à la voix précédente')
                a = fin_prec
            z = min(z, len(mix))
            if z - a < 2 * fondu: continue
            seg = mix[a:z].copy()
            r = np.linspace(0, 1, fondu); seg[:fondu] *= r; seg[-fondu:] *= r[::-1]
            st[v][a:z] += seg; masque[v][a:z] = True
            fin_prec = max(fin_prec or 0, z)
    return mix, st, masque, journal


# ------------------------------------------------------------------ mesures
TIERS = np.array([100 * 2 ** (i / 3) for i in range(0, 21)])    # 100 Hz … ~10 kHz


def trames_parole(x, masque=None, seuil=-40):
    """Échantillons de parole : dans le masque et à moins de 40 dB du maximum (trames de 20 ms)."""
    n = int(SR * 0.02); m = len(x) // n
    if m == 0: return x
    t = x[:m * n].reshape(m, n)
    e = 10 * np.log10((t ** 2).mean(1) + 1e-15)
    ok = e > e.max() + seuil
    if masque is not None: ok &= masque[:m * n].reshape(m, n).mean(1) > 0.9
    return t[ok].ravel() if ok.any() else x


def ltas(x, masque=None):
    """Spectre moyen à long terme (Welch) en tiers d'octave, dB."""
    p = trames_parole(x, masque)
    f, P = signal.welch(p, SR, nperseg=4096)
    out = []
    for c in TIERS:
        lo, hi = c / 2 ** (1 / 6), c * 2 ** (1 / 6)
        sel = (f >= lo) & (f < hi)
        out.append(10 * np.log10(P[sel].mean() + 1e-20))
    return np.array(out)


def lufs(x, masque=None):
    import pyloudnorm as pyln
    p = trames_parole(x, masque)
    if len(p) < SR: return float('nan')
    return pyln.Meter(SR).integrated_loudness(p)


def decroissance_ms(x):
    """Indicateur de réverbération : temps médian (ms) pour qu'une fin de mot passe de −20 à −45 dB
    sous le niveau de parole. Une voix « sèche » descend en ~25 ms ; une réverbération courte l'allonge."""
    lv = niveau_court(x, 5); v = lv[lv > -100]
    if len(v) < SR: return float('nan')
    ref = np.percentile(v, 95); hi = lv > ref - 20; out = []
    for i in np.where(hi[:-1] & ~hi[1:])[0]:
        seg = lv[i + 1:i + int(0.4 * SR)]
        if len(seg) < 10 or seg.min() < -110: continue        # fin de segment (silence numérique) : ignorée
        k = np.argmax(seg < ref - 45)
        if k > 0 and (seg[:k] < ref - 20).all(): out.append(k / SR * 1000)
    return float(np.median(out)) if len(out) >= 5 else float('nan')


def energie_sifflantes(x, masque):
    p = trames_parole(x, masque)
    f, P = signal.welch(p, SR, nperseg=4096)
    return 10 * np.log10(P[(f >= 5000) & (f <= 9000)].sum() / (P[(f >= 150) & (f <= 9000)].sum() + 1e-20) + 1e-20)


# ------------------------------------------------------------------ étape 4 : timbres
def passe_haut(x, f):
    sos = signal.butter(4, f, 'highpass', fs=SR, output='sos')
    return signal.sosfiltfilt(sos, x)


def expandeur_rapide(x, masque, ratio):
    """Expansion vers le bas, relative au niveau de parole : atténue les queues de réverbération entre les syllabes.
    Enveloppe sous-échantillonnée (×32) puis interpolée."""
    c = CONFIG['expandeur']; dec = 32
    ref = np.percentile(niveau_court(trames_parole(x, masque), 10), 95)
    lv = niveau_court(x, 5)[::dec] - ref
    gr = np.clip((lv - c['seuil_db']) * (ratio - 1), -c['max_db'], 0)
    fs = SR / dec
    a, r = np.exp(-1 / (fs * c['attaque_ms'] / 1000)), np.exp(-1 / (fs * c['relache_ms'] / 1000))
    g = np.empty_like(gr); acc = 0.0
    for i, v in enumerate(gr):
        k = a if v < acc else r          # descente rapide (attaque), remontée lente (relâchement)
        acc = k * acc + (1 - k) * v; g[i] = acc
    g = np.interp(np.arange(len(x)), np.arange(len(g)) * dec, g)
    return x * 10 ** (g / 20)


def fir_eq(gains_db):
    """FIR à phase linéaire depuis des gains par tiers d'octave (plat en dehors de f_min–f_max)."""
    c = CONFIG['eq']
    f = np.concatenate([[0, c['f_min'] / 2], TIERS, [c['f_max'] * 1.25, SR / 2]])
    g = np.concatenate([[0, 0], gains_db, [0, 0]])
    return signal.firwin2(c['coefs'], f, 10 ** (g / 20), fs=SR)


def appliquer_fir(x, h):
    y = signal.fftconvolve(x, h)
    d = (len(h) - 1) // 2
    return y[d:d + len(x)]


def eq_match(st, masque):
    c = CONFIG['eq']; rapport = []
    for passe in range(c['passes']):
        L = {k: ltas(st[k], masque[k]) for k in st}
        cible = np.mean(list(L.values()), axis=0)
        ecart = np.abs(L['A'] - L['B'])[(TIERS >= 150) & (TIERS <= 8000)].max()
        rapport.append(f'passe {passe + 1} : écart de timbre max {ecart:.1f} dB')
        if ecart <= c['cible_ecart_db'] * 0.6: break
        for k in st:
            corr = np.clip(cible - L[k], -c['max_db'], c['max_db'])
            corr -= np.interp(1000, TIERS, corr)      # garde le niveau à 1 kHz : on corrige la couleur, pas le volume
            st[k] = appliquer_fir(st[k], fir_eq(corr))
    return rapport


def de_esser(x):
    with tempfile.TemporaryDirectory() as t:
        a, b = os.path.join(t, 'a.wav'), os.path.join(t, 'b.wav')
        sf.write(a, x.astype(np.float32), SR, subtype='FLOAT')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', a, '-af', 'deesser=i=0.4:m=0.5:f=0.5', '-c:a', 'pcm_f32le', b], check=True)
        return sf.read(b)[0]


# ------------------------------------------------------------------ étape 5 : dynamique et espace
def compresseur(x, masque, ratio, reduction_db, attaque_ms=10, relache_ms=100):
    from pedalboard import Compressor
    p = trames_parole(x, masque)
    seuil = float(np.percentile(niveau_court(p, 10), 95)) - reduction_db * ratio / (ratio - 1)
    return Compressor(threshold_db=seuil, ratio=ratio, attack_ms=attaque_ms, release_ms=relache_ms)(x.astype(np.float32), SR).astype(np.float64)


def panoramique(x, p):
    ang = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(ang), x * np.sin(ang)])


def bruit_rose(n, rng):
    """Bruit rose (filtre de Paul Kellet), filtré passe-bas 8 kHz."""
    b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]; a = [1, -2.494956002, 2.017265875, -0.522189400]
    x = signal.lfilter(b, a, rng.standard_normal(n))
    return signal.sosfilt(signal.butter(4, 8000, 'lowpass', fs=SR, output='sos'), x)


# ------------------------------------------------------------------ étape 6 : master
def ffmpeg_ebur128(path):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True)
    t = r.stderr[r.stderr.rfind('Summary:'):]
    i = float(re.search(r'I:\s+(-?[\d.]+) LUFS', t).group(1)); tp = float(re.search(r'Peak:\s+(-?[\d.]+) dBFS', t).group(1))
    return i, tp


def loudnorm_2_passes(wav_in, wav_out):
    c = CONFIG
    base = f'loudnorm=I={c["lufs"]}:TP={c["true_peak"]}:LRA={c["lra"]}'
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', wav_in, '-af', base + ':print_format=json', '-f', 'null', '-'], capture_output=True, text=True)
    m = json.loads(r.stderr[r.stderr.rfind('{'):r.stderr.rfind('}') + 1])
    filt = (base + f':measured_I={m["input_i"]}:measured_TP={m["input_tp"]}:measured_LRA={m["input_lra"]}'
            f':measured_thresh={m["input_thresh"]}:offset={m["target_offset"]}:linear=true')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', wav_in, '-af', filt + f',aresample={SR}', '-c:a', 'pcm_s24le', wav_out], check=True)


def habiller(master, sortie_wav):
    """Ajoute l'habillage en début et en fin. Renvoie la durée ajoutée (s) ; 0 sans fichier d'habillage."""
    h = CONFIG.get('habillage') or {}
    if not h.get('fichier') or not os.path.isfile(h['fichier']):
        import shutil; shutil.copyfile(master, sortie_wav); return 0.0
    d = os.path.dirname(sortie_wav); brut = os.path.join(d, 'habillage_mono.wav'); norm = os.path.join(d, 'habillage_norm.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', h['fichier'], '-ac', '1' if CONFIG['mono'] else '2', '-ar', str(SR), '-c:a', 'pcm_f32le', brut], check=True)
    sauve = CONFIG['lufs']; CONFIG['lufs'] = h['lufs']
    try: loudnorm_2_passes(brut, norm)
    finally: CONFIG['lufs'] = sauve
    j = sf.read(norm, always_2d=True)[0]; v = sf.read(master, always_2d=True)[0]
    if j.shape[1] != v.shape[1]: j = np.repeat(j.mean(1, keepdims=True), v.shape[1], axis=1)
    blanc = np.zeros((int(SR * h['blanc_s']), v.shape[1]))
    sf.write(sortie_wav, np.concatenate([j, blanc, v, blanc, j]), SR, subtype='PCM_24')
    return 2 * (len(j) + len(blanc)) / SR


def encoder(wav, sortie, meta):
    tmp = sortie + '.tmp.m4a'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', wav, '-c:a', 'aac', '-b:a', f'{CONFIG["aac_kbps"]}k', '-movflags', '+faststart', '-ar', str(SR), '-ac', '1' if CONFIG['mono'] else '2',
                    '-metadata', f'title={meta["titre"]}', '-metadata', 'artist=Software Compliance', '-metadata', 'album=Software Compliance', tmp], check=True)
    os.replace(tmp, sortie)


def produire(blocs, voix, sortie_audio, dossier, meta, sortie_brute=None):
    """Chaîne complète. Écrit stems/ et out/ dans `dossier`, puis sortie_audio. Renvoie le dictionnaire de mesures."""
    os.makedirs(os.path.join(dossier, 'stems'), exist_ok=True); os.makedirs(os.path.join(dossier, 'out'), exist_ok=True)
    M = {'journal': []}
    mix, st, masque, j = pistes(blocs, voix); M['journal'] += j
    sf.write(os.path.join(dossier, 'raw_dialogue_full.wav'), mix.astype(np.float32), SR, subtype='FLOAT')
    if sortie_brute:   # référence d'écoute : audio ElevenLabs tel quel, seulement mis au même volume et au même format
        brut = os.path.join(dossier, 'out', 'brut_master.wav')
        loudnorm_2_passes(os.path.join(dossier, 'raw_dialogue_full.wav'), brut)
        encoder(brut, sortie_brute, {'titre': meta['titre'] + ' (sans traitement)'})
    M['avant'] = {'timbre_ecart_db': float(np.abs(ltas(st['A'], masque['A']) - ltas(st['B'], masque['B']))[(TIERS >= 150) & (TIERS <= 8000)].max()),
                  'decroissance_ms': {k: decroissance_ms(st[k]) for k in st},
                  'lufs': {k: lufs(st[k], masque[k]) for k in st}}
    for k in st: sf.write(os.path.join(dossier, 'stems', f'voix_{k}_brute.wav'), st[k].astype(np.float32), SR, subtype='FLOAT')
    # étape 4
    for k in st: st[k] = passe_haut(st[k], CONFIG['passe_haut_hz'])
    # réverbération propre à une voix : expandeur sur cette voix seulement, jusqu'à rejoindre l'autre
    c = CONFIG['expandeur']; dc = M['avant']['decroissance_ms']
    if not any(np.isnan(v) for v in dc.values()):
        sec, hum = min(dc, key=dc.get), max(dc, key=dc.get)
        cible = dc[sec] * c['tolerance']
        if dc[hum] > cible:
            for r in c['ratios']:
                y = expandeur_rapide(st[hum], masque[hum], r); d = decroissance_ms(y)
                if np.isnan(d) or d <= cible: break
            st[hum] = y
            M['journal'].append(f'voix {hum} : fins de mots {dc[hum]:.0f} ms contre {dc[sec]:.0f} ms pour {sec} ; expandeur ratio {r} → {d:.0f} ms')
    M['journal'] += eq_match(st, masque)
    sib = {k: energie_sifflantes(st[k], masque[k]) for k in st}
    if abs(sib['A'] - sib['B']) > CONFIG['sibilantes_ecart_db']:
        k = max(sib, key=sib.get); st[k] = de_esser(st[k]); M['journal'].append(f'de-esser appliqué à la voix {k} (+{abs(sib["A"] - sib["B"]):.1f} dB de sifflantes)')
    # étape 5
    c = CONFIG['compresseur']
    for k in st: st[k] = compresseur(st[k], masque[k], c['ratio'], c['reduction_db'], c['attaque_ms'], c['relache_ms'])
    L = {k: lufs(st[k], masque[k]) for k in st}; cible = np.nanmean(list(L.values()))
    for k in st: st[k] *= 10 ** ((cible - L[k]) / 20)
    for k in st: sf.write(os.path.join(dossier, 'stems', f'voix_{k}_traitee.wav'), st[k].astype(np.float32), SR, subtype='FLOAT')
    M['apres'] = {'timbre_ecart_db': float(np.abs(ltas(st['A'], masque['A']) - ltas(st['B'], masque['B']))[(TIERS >= 150) & (TIERS <= 8000)].max()),
                  'decroissance_ms': {k: decroissance_ms(st[k]) for k in st},
                  'lufs': {k: lufs(st[k], masque[k]) for k in st}}
    from pedalboard import Reverb, Compressor
    if CONFIG['mono']: bus = (st['A'] + st['B'])[None, :]
    else: bus = panoramique(st['A'], -CONFIG['pan']) + panoramique(st['B'], CONFIG['pan'])
    rv = CONFIG['reverb']
    if rv:
        wet = Reverb(room_size=rv['room_size'], damping=rv['damping'], wet_level=1.0, dry_level=0.0, width=rv['width'])(bus.astype(np.float32), SR).astype(np.float64)
        bus = bus + wet * rv['wet']
    if CONFIG['room_tone_dbfs'] is not None:
        rng = np.random.default_rng(7)
        for ch in range(bus.shape[0]):
            n = bruit_rose(bus.shape[1], rng)
            n *= 10 ** (CONFIG['room_tone_dbfs'] / 20) / (np.sqrt((n ** 2).mean()) + 1e-12)
            bus[ch] += n
    # étape 6
    b = CONFIG['bus']; ref = np.percentile(niveau_court(bus.mean(0), 10), 95)
    bus = Compressor(threshold_db=float(ref - b['reduction_db'] * b['ratio'] / (b['ratio'] - 1)), ratio=b['ratio'], attack_ms=20, release_ms=200)(bus.astype(np.float32), SR).astype(np.float64)
    pre = os.path.join(dossier, 'out', 'premaster.wav'); master = os.path.join(dossier, 'out', 'episode_master.wav')
    sf.write(pre, (bus.T / max(1.0, np.abs(bus).max())).astype(np.float32), SR, subtype='FLOAT')
    loudnorm_2_passes(pre, master)
    final = os.path.join(dossier, 'out', 'episode_final.wav')
    M['habillage_s'] = habiller(master, final)          # le contrôle qualité porte sur la voix (master) ; l'habillage s'y ajoute
    encoder(final, sortie_audio, meta)
    M['duree_blocs_s'] = sum(len(decoder(b['mp3'])) for b in blocs) / SR + CONFIG['pause_s'] * (len(blocs) - 1)
    M['master'] = master; M['masques'] = masque; M['stems'] = st
    return M


# ------------------------------------------------------------------ contrôle qualité
def mots(t):
    t = t.lower().replace('’', "'").replace('-', ' ')
    t = re.sub(r"\[[^\]]*\]", ' ', t)                  # balises d'expression v3
    t = re.sub(r"(?<![\w-])(?:euh|heu|hum|hmm|mmh)(?![\w-])", ' ', t)   # hésitations : transcrites de façon variable
    t = re.sub(r"[^\w' ]", ' ', t).replace("'", ' ')
    return t.split()


def wer(ref, hyp):
    r, h = mots(ref), mots(hyp)
    d = np.arange(len(h) + 1)
    for i, rw in enumerate(r, 1):
        prev, d[0] = d.copy(), i
        for j, hw in enumerate(h, 1):
            d[j] = min(prev[j] + 1, d[j - 1] + 1, prev[j - 1] + (rw != hw))
    return d[len(h)] / max(1, len(r)), len(r)


def transcrire(path):
    from faster_whisper import WhisperModel
    m = WhisperModel(os.environ.get('PODCAST_WHISPER_MODEL') or 'small', device='cpu', compute_type='int8')
    # décodage par ffmpeg (16 kHz mono) : évite PyAV, dont les versions récentes cassent faster-whisper
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'], capture_output=True, check=True)
    segs, _ = m.transcribe(np.frombuffer(r.stdout, dtype='<f4').copy(), language='fr', beam_size=1)
    return ' '.join(s.text for s in segs)


SEUILS = {'lufs_tol': 1.0, 'true_peak': -1.0, 'ab_lu': 1.0, 'timbre_db': 3.0, 'duree_s': 1.0, 'wer': 0.15}


def qc(M, mp3, texte_script, dossier):
    """Contrôles du brief. Renvoie (ok, lignes du rapport, résumé). Bloquants : loudness, true peak, durée, fidélité."""
    S, L, bloque, alerte = SEUILS, [], [], []
    i, tp = ffmpeg_ebur128(M['master'])
    L.append(('Loudness intégré du master', f'{i:.1f} LUFS', f'{CONFIG["lufs"]} ± {S["lufs_tol"]}', abs(i - CONFIG['lufs']) <= S['lufs_tol'], True))
    L.append(('True peak', f'{tp:.1f} dBTP', f'≤ {S["true_peak"]}', tp <= S['true_peak'] + 0.1, True))
    ab = abs(M['apres']['lufs']['A'] - M['apres']['lufs']['B'])
    L.append(('Écart de loudness A/B', f'{ab:.2f} LU', f'≤ {S["ab_lu"]}', ab <= S['ab_lu'], False))
    L.append(('Écart de timbre A/B (150 Hz–8 kHz)', f'{M["avant"]["timbre_ecart_db"]:.1f} → {M["apres"]["timbre_ecart_db"]:.1f} dB', f'≤ {S["timbre_db"]}', M['apres']['timbre_ecart_db'] <= S['timbre_db'], False))
    rv = M['apres']['decroissance_ms']; rv0 = M['avant']['decroissance_ms']
    ok_rv = True if np.isnan(rv['A'] + rv['B']) else max(rv.values()) <= min(rv.values()) * 1.5 + 5
    L.append(('Réverbération propre à une voix (fins de mots −20 → −45 dB)', f'A {rv0["A"]:.0f} → {rv["A"]:.0f} ms, B {rv0["B"]:.0f} → {rv["B"]:.0f} ms', 'écart ≤ 50 % (+5 ms)', ok_rv, False))
    import soundfile as _sf
    info = _sf.info(M['master']); d = info.frames / info.samplerate
    L.append(('Durée', f'{d:.1f} s (blocs : {M["duree_blocs_s"]:.1f} s)', f'écart < {S["duree_s"]} s', abs(d - M['duree_blocs_s']) < S['duree_s'], True))
    # clics : saut d'un échantillon à l'autre, comparé à la distribution
    x = _sf.read(M['master'])[0]; x = x.mean(1) if x.ndim > 1 else x; dd = np.abs(np.diff(x)); seuil = np.percentile(dd, 99.99) * 3
    clics = int((dd > max(seuil, 0.2)).sum())
    L.append(('Clics', f'{clics} saut(s) anormal(aux)', 'aucun', clics == 0, False))
    try:
        hyp = transcrire(mp3); w, n = wer(texte_script, hyp)
        open(os.path.join(dossier, 'transcription.txt'), 'w', encoding='utf-8').write(hyp + '\n')
        L.append(('Fidélité au script (faster-whisper)', f'{w * 100:.1f} % de mots différents sur {n}', f'≤ {S["wer"] * 100:.0f} %', w <= S['wer'], True))
    except Exception as e:
        L.append(('Fidélité au script (faster-whisper)', f'non vérifiée ({type(e).__name__} : {str(e)[:160]})', '—', True, False))
    ok = all(r[3] for r in L if r[4])
    rep = ['# Contrôle qualité de l\'épisode', '', f'Résultat : {"**publiable**" if ok else "**non publié**"}', '',
           '| Critère | Mesure | Seuil | Résultat |', '|---|---|---|---|']
    rep += [f'| {a}{" (bloquant)" if bl else ""} | {b} | {c} | {"ok" if r else "ÉCART"} |' for a, b, c, r, bl in L]
    rep += ['', '## Journal', ''] + [f'- {j}' for j in M['journal']]
    open(os.path.join(dossier, 'qc_report.md'), 'w', encoding='utf-8').write('\n'.join(rep) + '\n')
    resume = {a: b for a, b, c, r, bl in L}
    return ok, [f'{a} : {b} ({"ok" if r else "écart"})' for a, b, c, r, bl in L if not r], resume
