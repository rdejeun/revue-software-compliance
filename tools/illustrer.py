#!/usr/bin/env python3
"""Illustrations de la version imprimable (README, § 18) : à partir des briefs de content/AAAA-MM-JJ/illustrations.json,
demande à Recraft (API, clé RECRAFT_API_KEY) des dessins de presse au trait, vectoriels, dans les deux couleurs de la
charte, et les dépose dans veille/illustrations/AAAA-MM-JJ/ (SVG brut, SVG ramené à la charte, fiche JSON).

Usage : python3 tools/illustrer.py AAAA-MM-JJ [--candidats N] [--seulement id,id] [--modele recraftv3_vector] [--style "Line art"]
        python3 tools/illustrer.py --retenir AAAA-MM-JJ ID FICHIER   (dessin retenu : recadré sur son contenu, légendes du
        brief ajoutées en vectoriel, copié dans content/AAAA-MM-JJ/illustrations/ID.svg, champ « fichier » renseigné)
        python3 tools/illustrer.py --grille FICHIER.svg   (aperçu PNG quadrillé au dixième, pour placer une légende)
Coût : 0,08 $ par image vectorielle (V3) ; le script affiche le total demandé et refuse au-delà de --budget (défaut 1,50 $).
S'exécute dans le workflow « Illustrations » (la session de rédaction ne peut pas joindre l'API)."""
import argparse, hashlib, json, os, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
API = 'https://external.api.recraft.ai/v1/images/generations'
NAVY, ACC = (15, 42, 74), (194, 65, 12)   # charte : bleu nuit, orange brique (journal.py)
PRIX = {'recraftv4_styles_vector': .05, 'recraftv4_1_vector': .08, 'recraftv3_vector': .08, 'recraftv3_raster': .04, 'recraftv4_vector': .08, 'recraftv4_styles_vector': .05, 'recraftv2_vector': .044}
STYLE = ('Editorial press cartoon, clean confident ink line drawing, flat, no shading, no gradients. Exactly two spot colors: '
         'dark navy blue lines and fills, with a few orange accents, on a plain white background. Any logo, emblem or public figure '
         'named in the scene is redrawn in the same simple line style and two colors, instantly recognizable. '
         'Bold thick outlines (line width about one hundredth of the image width), few large simple shapes, no small details, '
         'no fine patterns or hatching, no tiny objects. It tells a simple story: a plausible everyday situation in which the '
         'characters act naturally and the two or three elements interact as they would in real life (no symbolic juxtaposition '
         'of unrelated objects). The scene spreads across the whole width of the frame, characters large, no empty margins, '
         'no background decor, readable at 4 cm wide. Scene: ')
SANS_TEXTE = ' No text, no letters.'
NEGATIF = 'watermark, photo, realistic, gradient, shading, 3d, many colors, frame, border, background scenery, abstract shapes'
REFERENCES = sorted(os.path.relpath(f, ROOT) for f in __import__('glob').glob(os.path.join(HERE, 'illustrations-references', '*.png')))   # style de la revue (dessins retenus)
TAILLES = {'1:1': '1024x1024', '4:3': '1365x1024', '3:2': '1536x1024'}   # format du brief (carré par défaut)


def lire_briefs(d):
    p = os.path.join(ROOT, 'content', d, 'illustrations.json')
    return json.load(open(p, encoding='utf-8')), p


def references_data(refs):
    """Dessins de référence (chemins du dépôt, PNG) en URL de données, pour le style des modèles V4 Styles."""
    import base64
    return ['data:image/png;base64,' + base64.b64encode(open(os.path.join(ROOT, r), 'rb').read()).decode() for r in refs]


def demander_v4(cle, prompt, modele, n, refs, taille='1024x1024'):
    """Recraft V4 Styles : le style est donné par des dessins de référence déjà retenus (meilleure tenue du brief que le
    style « Line art » de V3, qui laisse tomber les actions des personnages)."""
    corps = {'prompt': prompt, 'model': modele, 'n': n, 'size': taille, 'response_format': 'url',
             'style_reference_urls': references_data(refs), 'style_match': 'precise',
             'controls': {'colors': [{'rgb': list(NAVY), 'weight': .75}, {'rgb': list(ACC), 'weight': .25}],
                          'background_color': {'rgb': [255, 255, 255]}}}
    req = urllib.request.Request(API, data=json.dumps(corps).encode(), method='POST',
                                 headers={'Authorization': f'Bearer {cle}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as r: return json.loads(r.read())


def demander(cle, prompt, modele, style, n, graine=None, taille='1024x1024', texte=False):
    corps = {'prompt': prompt[:1000], 'model': modele, 'style': style, 'n': n, 'size': taille, 'response_format': 'url',
             'negative_prompt': NEGATIF + ('' if texte else ', text, letters, words'),
             'controls': {'colors': [{'rgb': list(NAVY), 'weight': .75}, {'rgb': list(ACC), 'weight': .25}],
                          'background_color': {'rgb': [255, 255, 255]}, 'artistic_level': 2, 'no_text': not texte}}
    if graine is not None: corps['random_seed'] = graine
    req = urllib.request.Request(API, data=json.dumps(corps).encode(), method='POST',
                                 headers={'Authorization': f'Bearer {cle}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=180) as r: return json.loads(r.read())


def telecharger(url):
    with urllib.request.urlopen(url, timeout=120) as r: return r.read()


def couleur_proche(hexa):
    """Ramène une couleur à la charte : blanc, bleu nuit ou orange (les teintes chaudes vont à l'orange, le très clair au blanc)."""
    m = re.match(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', hexa)
    if m: r, g, b = map(int, m.groups())
    else:
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
        if not (v.startswith('#') or v.startswith('rgb')): return m.group(0)
        return f'{m.group(1)}{couleur_proche(v)}{m.group(3)}'
    svg = re.sub(r'((?:fill|stroke)=")([^"]*)(")', rempl, svg)
    svg = re.sub(r'((?:fill|stroke)\s*:\s*)([^;"}]*)([;"}])', rempl, svg)
    return svg


def apercu(svg):
    """Aperçus PNG du SVG pour la relecture : 512 px, et 180 px (le dessin imprimé sur une colonne de 45 mm)."""
    try:
        import cairosvg
        cairosvg.svg2png(url=svg, write_to=svg[:-4] + '.png', output_width=512)
        cairosvg.svg2png(url=svg, write_to=svg[:-4] + '-45mm.png', output_width=180)
    except Exception as e:   # noqa
        print(f'aperçu impossible ({os.path.basename(svg)}) : {e}', file=sys.stderr)


FONTE = os.path.join(HERE, 'vendor', 'fonts', 'amatic-sc', 'amatic-sc-latin-700-normal.woff2')   # manuscrite étroite (OFL)
_FUT = {}


def fut_fonte():
    """Épaisseur du fût de la police, en fraction du corps (mesurée sur un « H » rendu)."""
    if 'f' not in _FUT:
        import cairosvg, io, numpy as np
        from PIL import Image
        from scipy import ndimage
        corps = 400
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600"><rect width="600" height="600" fill="white"/>'
               + texte_chemin('H', 300, 300, corps, epaisseur=0) + '</svg>')
        a = np.array(Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('L')) < 128
        d = ndimage.distance_transform_edt(a); v = d[(ndimage.maximum_filter(d, 3) == d) & a & (d > 1)]
        _FUT['f'] = float(np.median(v) * 2 / corps) if len(v) else .08
    return _FUT['f']


def trait_dessin(svg_txt):
    """Épaisseur médiane du trait du dessin, en unités du viewBox."""
    import cairosvg, io, numpy as np
    from PIL import Image
    from scipy import ndimage
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', svg_txt)[1].split()]
    W = 1000
    img = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg_txt.encode(), output_width=W))).convert('RGBA')
    fond = Image.new('RGB', img.size, 'white'); fond.paste(img, mask=img.split()[3])
    a = np.array(fond.convert('L')) < 200
    d = ndimage.distance_transform_edt(a); v = d[(ndimage.maximum_filter(d, 3) == d) & a & (d > 1)]
    return float(np.median(v) * 2 / W * vb[2]) if len(v) else .008 * vb[2]


def encre_texte(texte):
    """(chemins, boîte de l'encre xmin, ymin, xmax, ymax en unités de la police, upm) du texte composé."""
    from fontTools.ttLib import TTFont
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.boundsPen import BoundsPen
    f = TTFont(FONTE); gs = f.getGlyphSet(); cmap = f.getBestCmap(); upm = f['head'].unitsPerEm
    x, chemins, bb = 0, [], None
    for ch in texte:
        g = cmap.get(ord(ch))
        if g is None: x += upm * .3; continue
        pen = SVGPathPen(gs); gs[g].draw(pen); bp = BoundsPen(gs); gs[g].draw(bp)
        if bp.bounds:
            b = (bp.bounds[0] + x, bp.bounds[1], bp.bounds[2] + x, bp.bounds[3])
            bb = b if bb is None else (min(bb[0], b[0]), min(bb[1], b[1]), max(bb[2], b[2]), max(bb[3], b[3]))
        chemins.append(f'<path transform="translate({x} 0)" d="{pen.getCommands()}"/>'); x += gs[g].width
    return chemins, bb, upm


def texte_zone(texte, zone, vb, angle=0.0, couleur='#0f2a4a', epaisseur=None, remplissage=(.82, .72)):
    """Texte centré **sur son encre** dans une zone [x0, y0, x1, y1] (fraction du dessin, repère de la zone tourné de
    « angle » autour de son centre), au plus grand corps qui tienne dans remplissage (largeur, hauteur) de la zone."""
    chemins, bb, upm = encre_texte(texte)
    zx0, zy0, zx1, zy1 = vb[0] + zone[0] * vb[2], vb[1] + zone[1] * vb[3], vb[0] + zone[2] * vb[2], vb[1] + zone[3] * vb[3]
    cx, cy = (zx0 + zx1) / 2, (zy0 + zy1) / 2
    w, h = (bb[2] - bb[0]), (bb[3] - bb[1])
    k = min(remplissage[0] * (zx1 - zx0) / w, remplissage[1] * (zy1 - zy0) / h)
    sup = max(0.0, min(epaisseur or 0, .085 * upm * k) - fut_fonte() * upm * k) if epaisseur else 0.0   # épaisseur du trait du dessin, sans empâter un petit texte
    tr = f' stroke="{couleur}" stroke-width="{sup / k:.1f}" stroke-linejoin="round"' if sup > 0 else ''
    mx, my = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2   # centre de l'encre (repère de la police, y vers le haut)
    return (f'<g fill="{couleur}"{tr} transform="translate({cx:.1f} {cy:.1f}) rotate({angle}) scale({k:.5f} {-k:.5f}) translate({-mx:.1f} {-my:.1f})">'
            + ''.join(chemins) + '</g>')


def zone_libre(svg_txt, point, angle=0.0, W=1200):
    """Zone libre autour d'un point (fraction du dessin) : la surface blanche qui le contient (remplissage par
    diffusion, dans le repère tourné de « angle »), son centre optique (centre du plateau de la distance aux traits) et
    son étendue en largeur et en hauteur à ce centre. Renvoie (cx, cy, largeur, hauteur) en unités du viewBox."""
    import cairosvg, io, math, numpy as np
    from PIL import Image
    from scipy import ndimage
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', svg_txt)[1].split()]
    H = int(W * vb[3] / vb[2])
    img = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg_txt.encode(), output_width=W, output_height=H))).convert('RGBA')
    fond = Image.new('RGB', img.size, 'white'); fond.paste(img, mask=img.split()[3])
    g = fond.convert('L')
    px, py = point[0] * W, point[1] * H
    if angle:   # on redresse : le texte sera horizontal dans ce repère
        g = g.rotate(angle, center=(W / 2, H / 2), fillcolor=255, resample=Image.BILINEAR)
        a = math.radians(angle); dx, dy = px - W / 2, py - H / 2
        px, py = W / 2 + dx * math.cos(a) + dy * math.sin(a), H / 2 - dx * math.sin(a) + dy * math.cos(a)
    blanc = np.array(g) > 200
    lab, _ = ndimage.label(blanc)
    region = lab == lab[int(py), int(px)]
    d = ndimage.distance_transform_edt(region)
    plateau = d >= .85 * d[region].max()
    ys, xs = np.nonzero(plateau)
    cy_, cx_ = ys.mean(), xs.mean()
    row = region[int(cy_)]; col = region[:, int(cx_)]
    x0 = int(cx_); x1 = int(cx_)
    while x0 > 0 and row[x0 - 1]: x0 -= 1
    while x1 < W - 1 and row[x1 + 1]: x1 += 1
    y0 = int(cy_); y1 = int(cy_)
    while y0 > 0 and col[y0 - 1]: y0 -= 1
    while y1 < len(col) - 1 and col[y1 + 1]: y1 += 1
    cx_, cy_ = (x0 + x1) / 2, (y0 + y1) / 2   # centre de l'étendue, au plateau
    if angle:   # retour au repère du dessin
        a = math.radians(angle); dx, dy = cx_ - W / 2, cy_ - H / 2
        cx_, cy_ = W / 2 + dx * math.cos(a) - dy * math.sin(a), H / 2 + dx * math.sin(a) + dy * math.cos(a)
    k = vb[2] / W
    return vb[0] + cx_ * k, vb[1] + cy_ * k, (x1 - x0) * k, (y1 - y0) * k


def texte_point(texte, svg_txt, point, angle=0.0, couleur='#0f2a4a', epaisseur=None, remplissage=(.8, .72)):
    """Texte centré sur son encre dans la zone libre qui contient le point (zone_libre()), au plus grand corps qui tienne."""
    cx, cy, w, h = zone_libre(svg_txt, point, angle)
    chemins, bb, upm = encre_texte(texte)
    k = min(remplissage[0] * w / (bb[2] - bb[0]), remplissage[1] * h / (bb[3] - bb[1]))
    sup = max(0.0, min(epaisseur or 0, .085 * upm * k) - fut_fonte() * upm * k) if epaisseur else 0.0   # épaisseur du trait du dessin, sans empâter un petit texte
    tr = f' stroke="{couleur}" stroke-width="{sup / k:.1f}" stroke-linejoin="round"' if sup > 0 else ''
    mx, my = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    return (f'<g fill="{couleur}"{tr} transform="translate({cx:.1f} {cy:.1f}) rotate({angle}) scale({k:.5f} {-k:.5f}) translate({-mx:.1f} {-my:.1f})">'
            + ''.join(chemins) + '</g>')


def texte_chemin(texte, cx, cy, taille, angle=0.0, couleur='#0f2a4a', epaisseur=None):
    """Texte en contours vectoriels (Amatic SC gras, manuscrite étroite), centré en (cx, cy), corps « taille » (unités
    du SVG) ; épaisseur : épaisseur de trait visée (celle du dessin), obtenue en épaississant le contour."""
    from fontTools.ttLib import TTFont
    from fontTools.pens.svgPathPen import SVGPathPen
    f = TTFont(FONTE); gs = f.getGlyphSet(); cmap = f.getBestCmap(); upm = f['head'].unitsPerEm
    x, chemins = 0, []
    for ch in texte:
        g = cmap.get(ord(ch))
        if g is None: x += upm * .3; continue
        pen = SVGPathPen(gs); gs[g].draw(pen)
        chemins.append(f'<path transform="translate({x} 0)" d="{pen.getCommands()}"/>'); x += gs[g].width
    k = taille / upm; cap = getattr(f['OS/2'], 'sCapHeight', 0) or upm * .66
    sup = max(0.0, (epaisseur or 0) - fut_fonte() * taille) if epaisseur else 0.0   # épaississement (unités du SVG)
    tr = f' stroke="{couleur}" stroke-width="{sup / k:.1f}" stroke-linejoin="round"' if sup > 0 else ''
    return (f'<g fill="{couleur}"{tr} transform="translate({cx} {cy}) rotate({angle}) scale({k} {-k}) translate({-x / 2} {-cap / 2})">'
            + ''.join(chemins) + '</g>')


def boite_contenu(svg_txt, marge=.02):
    """Boîte (unités du viewBox) de ce qui n'est pas blanc dans le dessin, marge comprise."""
    import cairosvg, io
    from PIL import Image
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', svg_txt)[1].split()]
    W = 800; img = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg_txt.encode(), output_width=W, output_height=int(W * vb[3] / vb[2]))))
    fond = Image.new('RGB', img.size, 'white'); fond.paste(img.convert('RGBA'), mask=img.convert('RGBA').split()[3])
    gris = fond.convert('L').point(lambda v: 255 if v < 235 else 0)
    bb = gris.getbbox() or (0, 0, img.width, img.height)
    sx = vb[2] / img.width; sy = vb[3] / img.height
    x0, y0, x1, y1 = vb[0] + bb[0] * sx, vb[1] + bb[1] * sy, vb[0] + bb[2] * sx, vb[1] + bb[3] * sy
    m = marge * max(x1 - x0, y1 - y0)
    return max(vb[0], x0 - m), max(vb[1], y0 - m), min(vb[0] + vb[2], x1 + m), min(vb[1] + vb[3], y1 + m)


def retenir(d, ident, fichier):
    """Dessin retenu : légendes du brief (champ « legendes » : texte, x, y en fraction du dessin, taille en fraction de sa
    largeur, angle, couleur navy|orange) ajoutées en contours vectoriels, dans une manuscrite étroite à l'épaisseur du
    trait du dessin ; marges blanches haute et basse retirées (la largeur, et donc l'équilibre horizontal, reste
    intacte) ; copie dans content/ et champ « fichier » renseigné. Aucun recadrage latéral, aucun masque : un dessin
    qu'il faudrait couper se redemande (README, § 18)."""
    briefs, p = lire_briefs(d)
    b = next(x for x in briefs if x['id'] == ident)
    src = fichier if os.path.exists(fichier) else os.path.join(ROOT, 'veille', 'illustrations', d, fichier)
    svg = charte(open(src, encoding='utf-8').read())   # couleurs exactes de la charte
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', svg)[1].split()]
    ep = trait_dessin(svg)
    ajout = ''
    for L in b.get('legendes') or []:
        coul = '#c2410c' if L.get('couleur') == 'orange' else ('#ffffff' if L.get('couleur') == 'blanc' else '#0f2a4a')
        if 'point' in L: ajout += texte_point(L['texte'], svg, L['point'], L.get('angle', 0), coul, ep, tuple(L.get('remplissage', (.8, .72))))
        elif 'zone' in L: ajout += texte_zone(L['texte'], L['zone'], vb, L.get('angle', 0), coul, ep, tuple(L.get('remplissage', (.82, .72))))
        else: ajout += texte_chemin(L['texte'], vb[0] + L['x'] * vb[2], vb[1] + L['y'] * vb[3], L.get('taille', .1) * vb[2], L.get('angle', 0), coul, ep)
    svg = svg.replace('</svg>', ajout + '</svg>')
    x0, y0, x1, y1 = boite_contenu(svg, marge=0)
    utile = (x1 - x0) / vb[2]   # largeur occupée par le dessin : un sujet étroit dans un cadre large laisse du vide sur les côtés
    if utile < .85: print(f'  ! {ident} : le dessin n\'occupe que {utile:.0%} de la largeur (vide sur les côtés) : à redemander', file=sys.stderr)
    x0, x1 = vb[0], vb[0] + vb[2]   # largeur intacte
    svg = re.sub(r'viewBox="[^"]+"', f'viewBox="{x0:.1f} {y0:.1f} {x1 - x0:.1f} {y1 - y0:.1f}"', svg, count=1)
    svg = re.sub(r'(<svg[^>]*?)\swidth="[^"]*"', r'\1', svg, count=1)
    svg = re.sub(r'(<svg[^>]*?)\sheight="[^"]*"', r'\1', svg, count=1)
    svg = re.sub(r'preserveAspectRatio="[^"]*"', 'preserveAspectRatio="xMidYMid meet"', svg, count=1)
    svg = svg.replace('<svg ', f'<svg width="{x1 - x0:.0f}" height="{y1 - y0:.0f}" ', 1)
    os.makedirs(os.path.join(ROOT, 'content', d, 'illustrations'), exist_ok=True)
    dest = os.path.join('illustrations', f'{ident}.svg')
    open(os.path.join(ROOT, 'content', d, dest), 'w', encoding='utf-8').write(svg)
    b['fichier'] = dest; b['source'] = os.path.basename(src)
    for k in ('recadrage',): b.pop(k, None)
    json.dump(briefs, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1); open(p, 'a').write('\n')
    apercu(os.path.join(ROOT, 'content', d, dest))
    print(f'{ident} : {dest} ({x1 - x0:.0f} × {y1 - y0:.0f}, rapport {(y1 - y0) / (x1 - x0):.2f} ; trait {ep / vb[2] * 100:.2f} % de la largeur ; largeur occupée {utile:.0%})', file=sys.stderr)


def grille(f):
    """Aperçu PNG quadrillé au dixième, pour placer une légende (coordonnées en fraction du dessin)."""
    import cairosvg, io
    from PIL import Image, ImageDraw
    img = Image.open(io.BytesIO(cairosvg.svg2png(url=f, output_width=800))).convert('RGB')
    dr = ImageDraw.Draw(img)
    for k in range(1, 20):
        c = (0, 170, 0) if k % 2 == 0 else (170, 230, 170)
        dr.line([(img.width * k / 20, 0), (img.width * k / 20, img.height)], fill=c); dr.line([(0, img.height * k / 20), (img.width, img.height * k / 20)], fill=c)
        if k % 2 == 0: dr.text((img.width * k / 20 + 2, 2), f'.{k // 2}', fill=(0, 140, 0)); dr.text((2, img.height * k / 20 + 2), f'.{k // 2}', fill=(0, 140, 0))
    out = f[:-4] + '-grille.png'; img.save(out); print(out)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--retenir': return retenir(*sys.argv[2:5])
    if len(sys.argv) > 1 and sys.argv[1] == '--grille': return grille(sys.argv[2])
    ap = argparse.ArgumentParser()
    ap.add_argument('date'); ap.add_argument('--candidats', type=int, default=1); ap.add_argument('--seulement', default='')
    ap.add_argument('--modele', default='recraftv4_styles_vector'); ap.add_argument('--style', default='Line art')
    ap.add_argument('--budget', type=float, default=1.5); ap.add_argument('--simuler', action='store_true')
    a = ap.parse_args()
    cle = os.environ.get('RECRAFT_API_KEY')
    briefs, _ = lire_briefs(a.date)
    seuls = {x for x in a.seulement.split(',') if x}
    briefs = [b for b in briefs if not seuls or b['id'] in seuls]
    sortie = os.path.join(ROOT, 'veille', 'illustrations', a.date); os.makedirs(sortie, exist_ok=True)
    fiche_p = os.path.join(sortie, 'illustrations.json')
    fiche = json.load(open(fiche_p, encoding='utf-8')) if os.path.exists(fiche_p) else []
    deja = {f['fichier'] for f in fiche}
    emp = lambda b: hashlib.sha256((b['brief'] + b.get('format', '1:1') + str(bool(b.get('texte'))) + (b.get('modele') or '') + ','.join(b.get('references') or [])).encode()).hexdigest()[:12]
    nb = lambda b: max(a.candidats, int(b.get('candidats', 1)))   # candidats par brief (champ « candidats » du brief, sinon --candidats)
    briefs = [b for b in briefs if sum(1 for f in fiche if f['id'] == b['id'] and f.get('brief') == emp(b)) < nb(b)]   # ce brief déjà servi : rien à redemander
    total = sum(nb(b) * PRIX.get(b.get('modele') or a.modele, .08) for b in briefs)
    if total > a.budget: sys.exit(f'au-delà du budget de {a.budget:.2f} $ : rien demandé')
    print(f'{len(briefs)} brief(s) à servir : {total:.2f} $', file=sys.stderr)
    if a.simuler: print('  ' + ', '.join(f"{b['id']} × {nb(b)}" for b in briefs), file=sys.stderr); return
    if not cle: sys.exit('RECRAFT_API_KEY absente')
    for b in briefs:
        texte = bool(b.get('texte'))   # un mot court ou un sigle, écrit dans le brief, éclaire parfois le dessin (README, § 18)
        prompt = STYLE + b['brief'] + ('' if texte else SANS_TEXTE)   # message, repère et action sont dans le brief (README, § 18)
        modele = b.get('modele') or a.modele
        refs = b.get('references') or (REFERENCES if modele.startswith('recraftv4_styles') else None)
        try:
            if refs and modele.startswith('recraftv4'): rep = demander_v4(cle, prompt, modele, nb(b), refs, b.get('format', '1:1'))   # V4 : taille en rapport
            else: rep = demander(cle, prompt, modele, a.style, nb(b), b.get('graine'), TAILLES.get(b.get('format', '1:1'), '1024x1024'), texte)
        except Exception as e:   # noqa
            corps_err = e.read().decode('utf-8', 'replace')[:500] if hasattr(e, 'read') else ''
            print(f'{b["id"]} : échec {e} {corps_err}', file=sys.stderr); continue
        k0 = sum(1 for f in fiche if f['id'] == b['id'])
        for k, img in enumerate(rep.get('data', []), k0 + 1):
            ext = 'svg' if 'vector' in a.modele else 'png'
            nom = f'{b["id"]}-{k}.{ext}'
            while nom in deja: k += 1; nom = f'{b["id"]}-{k}.{ext}'
            data = telecharger(img['url'])
            open(os.path.join(sortie, nom), 'wb').write(data)
            if ext == 'svg':
                open(os.path.join(sortie, nom.replace('.svg', '-charte.svg')), 'w', encoding='utf-8').write(charte(data.decode('utf-8', 'replace')))
                apercu(os.path.join(sortie, nom))
            fiche.append({'id': b['id'], 'fichier': nom, 'brief': emp(b), 'modele': modele, 'style': a.style, 'image_id': img.get('image_id'),
                          'date': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'credits': rep.get('credits')})
            deja.add(nom)
            print(f'{b["id"]} : {nom}', file=sys.stderr)
        time.sleep(1)
    json.dump(fiche, open(fiche_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
