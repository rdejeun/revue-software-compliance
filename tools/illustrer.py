#!/usr/bin/env python3
"""Illustrations de la version imprimable (README, § 18) : à partir des briefs de content/AAAA-MM-JJ/illustrations.json,
demande à Recraft (API, clé RECRAFT_API_KEY) des dessins de presse au trait, vectoriels, dans les deux couleurs de la
charte, et les dépose dans veille/illustrations/AAAA-MM-JJ/ (SVG brut, SVG ramené à la charte, fiche JSON).

Usage : python3 tools/illustrer.py AAAA-MM-JJ [--candidats N] [--seulement id,id] [--modele recraftv3_vector] [--style "Line art"]
Coût : 0,08 $ par image vectorielle (V3) ; le script affiche le total demandé et refuse au-delà de --budget (défaut 1,50 $).
S'exécute dans le workflow « Illustrations » (la session de rédaction ne peut pas joindre l'API)."""
import argparse, json, os, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
API = 'https://external.api.recraft.ai/v1/images/generations'
NAVY, ACC = (15, 42, 74), (194, 65, 12)   # charte : bleu nuit, orange brique (journal.py)
PRIX = {'recraftv3_vector': .08, 'recraftv3_raster': .04, 'recraftv4_vector': .08, 'recraftv4_styles_vector': .05, 'recraftv2_vector': .044}
STYLE = ('Editorial press cartoon, clean confident ink line drawing, flat, no shading, no gradients. Exactly two spot colors: '
         'dark navy blue lines and fills, with a few orange accents, on a plain white background. No text, no letters, no logos, '
         'no brand marks, no real people. One simple scene, readable at 4 cm wide, generous white space. Scene: ')
NEGATIF = 'text, letters, words, logo, watermark, photo, realistic, gradient, shading, 3d, many colors, frame, border'


def lire_briefs(d):
    p = os.path.join(ROOT, 'content', d, 'illustrations.json')
    return json.load(open(p, encoding='utf-8')), p


def demander(cle, prompt, modele, style, n, graine=None):
    corps = {'prompt': prompt[:1000], 'model': modele, 'style': style, 'n': n, 'size': '1024x1024', 'response_format': 'url',
             'negative_prompt': NEGATIF,
             'controls': {'colors': [{'rgb': list(NAVY), 'weight': .75}, {'rgb': list(ACC), 'weight': .25}],
                          'background_color': {'rgb': [255, 255, 255]}, 'artistic_level': 2, 'no_text': True}}
    if graine is not None: corps['random_seed'] = graine
    req = urllib.request.Request(API, data=json.dumps(corps).encode(), method='POST',
                                 headers={'Authorization': f'Bearer {cle}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=180) as r: return json.loads(r.read())


def telecharger(url):
    with urllib.request.urlopen(url, timeout=120) as r: return r.read()


def couleur_proche(hexa):
    """Ramène une couleur à la charte : blanc, bleu nuit ou orange (les teintes chaudes vont à l'orange, le très clair au blanc)."""
    h = hexa.lstrip('#')
    if len(h) == 3: h = ''.join(c * 2 for c in h)
    try: r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError: return hexa
    lum = (.299 * r + .587 * g + .114 * b) / 255
    if lum > .88: return '#ffffff'
    if r > g + 25 and r > b + 25: return '#c2410c'
    return '#0f2a4a'


def charte(svg):
    """SVG ramené aux couleurs de la charte (attributs fill/stroke et styles en ligne) ; les noms de couleurs usuels aussi."""
    noms = {'black': '#000000', 'white': '#ffffff', 'red': '#ff0000', 'orange': '#ffa500', 'blue': '#0000ff', 'navy': '#000080'}
    def rempl(m):
        v = m.group(2).strip().lower()
        if v in ('none', 'transparent', 'currentcolor') or v.startswith('url('): return m.group(0)
        v = noms.get(v, v)
        if not v.startswith('#'): return m.group(0)
        return f'{m.group(1)}{couleur_proche(v)}{m.group(3)}'
    svg = re.sub(r'((?:fill|stroke)=")([^"]*)(")', rempl, svg)
    svg = re.sub(r'((?:fill|stroke)\s*:\s*)([^;"}]*)([;"}])', rempl, svg)
    return svg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('date'); ap.add_argument('--candidats', type=int, default=1); ap.add_argument('--seulement', default='')
    ap.add_argument('--modele', default='recraftv3_vector'); ap.add_argument('--style', default='Line art')
    ap.add_argument('--budget', type=float, default=1.5); ap.add_argument('--simuler', action='store_true')
    a = ap.parse_args()
    cle = os.environ.get('RECRAFT_API_KEY')
    briefs, _ = lire_briefs(a.date)
    seuls = {x for x in a.seulement.split(',') if x}
    briefs = [b for b in briefs if not seuls or b['id'] in seuls]
    total = len(briefs) * a.candidats * PRIX.get(a.modele, .08)
    print(f'{len(briefs)} brief(s) × {a.candidats} candidat(s), modèle {a.modele}, style « {a.style} » : {total:.2f} $', file=sys.stderr)
    if total > a.budget: sys.exit(f'au-delà du budget de {a.budget:.2f} $ : rien demandé')
    if a.simuler: return
    if not cle: sys.exit('RECRAFT_API_KEY absente')
    sortie = os.path.join(ROOT, 'veille', 'illustrations', a.date); os.makedirs(sortie, exist_ok=True)
    fiche_p = os.path.join(sortie, 'illustrations.json')
    fiche = json.load(open(fiche_p, encoding='utf-8')) if os.path.exists(fiche_p) else []
    deja = {f['fichier'] for f in fiche}
    for b in briefs:
        prompt = STYLE + b['brief']
        try: rep = demander(cle, prompt, a.modele, a.style, a.candidats, b.get('graine'))
        except Exception as e:   # noqa
            print(f'{b["id"]} : échec {e}', file=sys.stderr); continue
        k0 = sum(1 for f in fiche if f['id'] == b['id'])
        for k, img in enumerate(rep.get('data', []), k0 + 1):
            ext = 'svg' if 'vector' in a.modele else 'png'
            nom = f'{b["id"]}-{k}.{ext}'
            while nom in deja: k += 1; nom = f'{b["id"]}-{k}.{ext}'
            data = telecharger(img['url'])
            open(os.path.join(sortie, nom), 'wb').write(data)
            if ext == 'svg':
                open(os.path.join(sortie, nom.replace('.svg', '-charte.svg')), 'w', encoding='utf-8').write(charte(data.decode('utf-8', 'replace')))
            fiche.append({'id': b['id'], 'fichier': nom, 'modele': a.modele, 'style': a.style, 'image_id': img.get('image_id'),
                          'date': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'credits': rep.get('credits')})
            deja.add(nom)
            print(f'{b["id"]} : {nom}', file=sys.stderr)
        time.sleep(1)
    json.dump(fiche, open(fiche_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
