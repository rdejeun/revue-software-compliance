#!/usr/bin/env python3
"""Version imprimable d'une édition : quatre pages A4 mises en page à la manière d'un journal (colonnes, titres,
folios, en-têtes courants), puis imposition sur une feuille A3 recto-verso pliée en deux (README, § 18).

Contenu : chapô de l'édition, chaque nouveauté (titre de sa synthèse, texte, puis Résumé, Impact et Contexte en
paragraphes sans intertitre), les rappels (texte court), l'agenda, et, si la place le permet, le résumé des rappels,
le détail de l'agenda et un lexique des sigles ; puis le colophon. Ni fiche Statut/Fonctions, ni ligne de sources,
ni « À vérifier ».
Calage sur exactement quatre pages : corps des paragraphes de 8,5 pt au moins (rappels, agenda et lexique : 8 pt au
moins) ; l'élément d'ajustement est la profondeur du contenu, ajoutée bloc par bloc par ordre d'importance (README, § 18).

Usage : python3 tools/journal.py [AAAA-MM-JJ …]   (défaut : dernière édition)
Écrit build/AAAA-MM-JJ/revue-AAAA-MM-JJ.pdf (A4, 4 pages) et revue-AAAA-MM-JJ-a3.pdf (A3 imposé : recto 4|1, verso 2|3).
Dépendances : weasyprint, pypdf ; qrcode (facultatif, code QR du colophon).
"""
import base64, datetime, glob, hashlib, html, io, json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS, CONTENT, BUILD = os.path.join(ROOT, 'tools'), os.path.join(ROOT, 'content'), os.path.join(ROOT, 'build')
FONTS = os.path.join(TOOLS, 'vendor', 'fonts')
sys.path.insert(0, TOOLS)
_cwd = os.getcwd()
_ed = sorted(glob.glob(os.path.join(CONTENT, '*', 'blocks.json')))
if _ed: os.chdir(os.path.dirname(_ed[0]))   # commun.py lit blocks.json du dossier courant à l'import (fonctions pures ici)
from commun import typo, E, sans_ital   # noqa: E402
os.chdir(_cwd)
from glossary import G   # noqa: E402
from officiel import officiel   # noqa: E402

PAGES = 4   # une feuille A3 pliée
CORPS_MIN, PETIT_MIN = 8.5, 8.0   # corps minimal des paragraphes ; des rappels, de l'agenda et du lexique
TAILLES = [10.0, 9.8, 9.6, 9.4, 9.2, 9.0, 8.8, 8.6, 8.5]   # corps des paragraphes (pt), du plus grand au plus petit
MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
MOISC = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.']
NAVY, ACC, BRIQUE = '#0f2a4a', '#c2410c', '#9a3412'
VERSION = 'journal-16'   # à changer quand la mise en page change (invalide le cache)


RENVOI = re.compile(r'\s*\((?:voir|cf\.)\s+(?:aussi\s+)?(?:le|les)\s+(?:N°|numéros?)\s*[\d\s,et]+\)', re.I)   # « (voir le N° 1) »


def T(s): return E(typo(RENVOI.sub('', s or '')))
def texte(segs): return ''.join(x.get('t', '') for x in segs)


def fdate(iso, annee=True):
    if not iso: return ''
    p = iso.split('-'); m = MOISC[int(p[1]) - 1]
    if len(p) == 2: return f'{m}\u00a0{p[0]}'
    d = int(p[2]); s = f'{"1er" if d == 1 else d}\u00a0{m}'
    return s + (f'\u00a0{p[0]}' if annee else '')


# ---------------------------------------------------------------- lecture de l'édition

def lire(d):
    b = json.load(open(os.path.join(CONTENT, d, 'blocks.json'), encoding='utf-8'))
    meta = json.load(open(os.path.join(CONTENT, d, 'meta.json'), encoding='utf-8'))
    ed = {'meta': meta, 'chapo': '', 'rubriques': [], 'agenda': []}
    cur = None
    for i, x in enumerate(b):
        k = x['k']
        if k == 'h1': continue
        if k == 'h2':
            t = texte(x['i']); lab, _, tit = t.partition(' : ')
            cur = {'titre': t, 'label': lab.strip(), 'sous': tit.strip(), 'chapo': '', 'items': [], 'rappels': [], 'agenda': lab.strip().startswith('Agenda')}
            ed['rubriques'].append(cur); continue
        if k == 'p':
            t = texte(x['i']).strip(' ·\u00a0')
            if not t: continue
            if cur is None:
                if not ed['chapo']: ed['chapo'] = t
                continue
            if not x.get('attrs') and not cur['chapo'] and not cur['items']:
                cur['chapo'] = t; continue
            a = x.get('attrs') or {}
            (cur['rappels'] if a.get('rappel') else cur['items']).append({'id': f'e{i}', 'segs': x['i'], 'a': a, 'sum': x.get('sum')})
        elif k == 'ul':
            for j, (it, a, s) in enumerate(zip(x['items'], x.get('attrs') or [{}] * len(x['items']), x.get('sum') or [None] * len(x['items']))):
                (cur['rappels'] if (a or {}).get('rappel') else cur['items']).append({'id': f'e{i}.{j}', 'segs': it, 'a': a or {}, 'sum': s})
        elif k == 'table':
            det = x.get('detail') or []
            for j, r in enumerate(x['rows'][1:]):
                cel = [texte(c) if isinstance(c, list) else str(c) for c in r]
                ed['agenda'].append({'id': f'a{j}', 'date': cel[0], 'quoi': cel[1], 'theme': cel[2] if len(cel) > 2 else '',
                                     'detail': det[j] if j < len(det) else None})
    ed['rubriques'] = [r for r in ed['rubriques'] if not r['agenda'] and (r['items'] or r['rappels'])]
    return ed


def corps(segs):
    """Texte d'un élément sans ses sources de fin : (html, [(libellé, url, officielle, éditeur)])."""
    srcs, out = [], []
    for x in segs:
        if x.get('href') and x.get('type') != 'projet':
            lab = x['t'][2:] if x['t'].startswith('↗\u00a0') else x['t']
            srcs.append((lab, x['href'], officiel(x['href']), x.get('type') == 'editeur')); out.append('\x00')
        else:
            out.append(('\x01' if x.get('type') == 'projet' else '') + x.get('t', ''))
    t = ''.join(out)
    t = re.sub(r'\s*\(\s*\x00(?:\s*[,;]\s*\x00)*\s*\)', '', t)   # « (Source1, Source2) »
    t = re.sub(r'[,;]?\s*\x00', '', t).replace('\x01', '').strip()
    if t and t[-1] not in '.!?…': t += '.'
    t = re.sub(r'\s+\.$', '.', t)
    return t, srcs


def accroche(t):
    """« Accroche : texte » -> accroche en gras sans empattement (comme la version web)."""
    m = re.match(r'^([^:]{1,90}?)\s:\s(.*)$', t, re.S)
    if not m: return T(t)
    return f'<b class="acc">{T(m[1])}</b>\u00a0: {T(m[2])}'


def synthese(it, incl, tout=False):
    """Paragraphes de la synthèse retenus par le calage, dans l'ordre de lecture : Contexte, Résumé, Impact."""
    sm, h = it.get('sum') or {}, []
    for k in ('contexte', 'essentiel', 'impact_avere', 'impact_potentiel'):
        if sm.get(k) and (tout or (k, it['id']) in incl): h.append(f'<p>{T(sm[k])}</p>')
    return '<div class="syn">' + ''.join(h) + '</div>' if h else ''


def morceaux(it, incl, une=False):
    """Article en morceaux successifs : titre et texte, puis chaque paragraphe retenu de la synthèse."""
    t, _ = corps(it['segs'])
    sm = it.get('sum') or {}
    tit = sm.get('titre')
    m = [(f'<h3 class="hl">{T(tit)}</h3>' if tit and not une else '') + f'<p class="txt">{accroche(t)}</p>']
    for k in ('contexte', 'essentiel', 'impact_avere', 'impact_potentiel'):
        if sm.get(k) and (une or (k, it['id']) in incl): m.append(f'<p class="sp">{T(sm[k])}</p>')
    return m


def article(it, incl, une=False):
    return f'<article class="art{" une" if une else ""}">' + ''.join(morceaux(it, incl, une)) + '</article>'


def unites(r, incl):
    """Contenu d'une rubrique en unités (morceaux d'articles, encadré « En bref ») : [(n° d'article ou None, html)]."""
    u = [(j, x) for j, it in enumerate(r['items']) for x in morceaux(it, incl)]
    rb = rappels(r['rappels'], incl)
    return u + ([(None, rb)] if rb else [])


def assembler(us):
    """Recompose des unités : les morceaux consécutifs d'un même article dans un seul <article>."""
    h, cur, ouvert = [], None, False
    for j, x in us:
        if j is None or j != cur:
            if ouvert: h.append('</article>'); ouvert = False
            if j is not None: h.append('<article class="art">'); ouvert = True
            cur = j
        h.append(x)
    if ouvert: h.append('</article>')
    return ''.join(h)


def rappels(rs, incl):
    if not rs: return ''
    li = []
    for r in rs:
        t, _ = corps(r['segs'])
        res = (r.get('sum') or {}).get('essentiel')   # résumé d'un rappel : bloc facultatif
        li.append(f'<li><p>{accroche(t)}</p>' + (f'<p class="rap-s">{T(res)}</p>' if res and ('essentiel', r['id']) in incl else '') + '</li>')
    return '<aside class="rap"><p class="rap-t">En bref</p><ul>' + ''.join(li) + '</ul></aside>'


def pastille(date, annee=None):
    """« 20 octobre 2026 » -> cadre arrondi « 20 / OCT. » ; « Novembre 2026 » -> « NOV. / 2026 »."""
    t = date.lower()
    m = re.search(r'(' + '|'.join(MOIS) + r')\s+(\d{4})', t)
    j = re.match(r'(1er|\d{1,2})(?:\s+au\s+(\d{1,2}))?', t)
    if m and j and (annee is None or m[2] == annee):
        jour = j[1] + (f'–{j[2]}' if j[2] else '')
        return f'<div class="ag-cal"><span class="j">{T(jour)}</span><span class="m">{MOISC[MOIS.index(m[1])]}</span></div>'
    if m: return f'<div class="ag-cal mois"><span class="j">{MOISC[MOIS.index(m[1])]}</span><span class="m">{m[2]}</span></div>'
    return f'<div class="ag-cal mois"><span class="j">{T(date[:6])}</span></div>'


def agenda(ev, incl, annee=None):
    if not ev: return ''
    h = []
    for e in ev:
        det = f'<p class="ag-x">{T(e["detail"])}</p>' if e.get('detail') and ('detail', e['id']) in incl else ''
        h.append(f'<div class="ag-e"><div class="ag-dt">{pastille(e["date"], annee)}</div><div>'
                 f'<p class="ag-th">{T(e["theme"])}</p><p class="ag-q">{T(e["quoi"])}</p>{det}</div></div>')
    return '<h2 class="rub" id="r-agenda" data-rub="Agenda"><span>Agenda</span> Dates à surveiller</h2><div class="ag">' + ''.join(h) + '</div>'


def lexique(html_txt):
    plain = re.sub(r'<[^>]+>', ' ', html_txt)
    vus, h = set(), []
    for rx, lab, de, _u in G:
        if lab in vus or not re.fullmatch(r'[A-Z][A-Z0-9-]{1,9}', rx): continue   # sigles seulement (CRA, SBOM, ECJU…)
        if re.search(r'(?<![\w-])(' + rx.replace(' ', '[ \u00a0]') + r')(?![\w])', plain):
            vus.add(lab); h.append((lab, de))
    h.sort(key=lambda x: x[0].lower())
    if not h: return ''
    return ('<h2 class="rub" id="r-lexique" data-rub="Lexique"><span>Lexique</span> Sigles cités</h2><div class="cols lex"><dl>'
            + ''.join(f'<dt>{T(lab)}</dt><dd>{T(sans_ital(de))}</dd>' for lab, de in h) + '</dl></div>')


def qr(url):
    try:
        import qrcode, qrcode.image.svg
        img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=0)
        b = io.BytesIO(); img.save(b)
        return f'<img class="qr" src="data:image/svg+xml;base64,{base64.b64encode(b.getvalue()).decode()}" alt="">'
    except Exception:
        return ''


# ---------------------------------------------------------------- page

def polices():
    css = []
    for fam, dossier, styles in (('Gelasio', 'gelasio', ('400-normal', '400-italic', '700-normal', '700-italic')),
                                 ('Source Sans 3', 'source-sans-3', ('400-normal', '400-italic', '600-normal', '700-normal'))):
        for st in styles:
            w, s = st.split('-')
            for sub, suff in (('latin', ''), ('latin-ext', ' Ext')):
                f = os.path.join(FONTS, dossier, f'{dossier}-{sub}-{st}.woff2')
                css.append(f"@font-face{{font-family:'{fam}{suff}';font-weight:{w};font-style:{s};src:url('file://{f}') format('woff2')}}")
    return '\n'.join(css)


SERIF = "'Gelasio','Gelasio Ext',Georgia,serif"
SANS = "'Source Sans 3','Source Sans 3 Ext','Segoe UI',Arial,sans-serif"


def css(fs, meta, ess_pt=11.0, colo_pt=7.6):
    pied = f'Software Compliance – {meta["date"]}'
    petit = max(PETIT_MIN, round(fs - .5, 2))   # rappels, agenda, lexique
    return polices() + f'''
@page {{ size:A4; margin:11mm 9.5mm 13mm 9.5mm }}
@page :right {{ @bottom-left {{ content:"{pied}"; font:400 7.5pt {SANS}; color:#6b7280; vertical-align:top; padding-top:2mm }}
               @bottom-right {{ content:counter(page); font:700 9pt {SANS}; color:{NAVY}; vertical-align:top; padding-top:1.6mm }} }}
@page :left {{ @bottom-left {{ content:counter(page); font:700 9pt {SANS}; color:{NAVY}; vertical-align:top; padding-top:1.6mm }}
              @bottom-right {{ content:"{pied}"; font:400 7.5pt {SANS}; color:#6b7280; vertical-align:top; padding-top:2mm }} }}
@page :first {{ margin-top:16mm; @bottom-left {{ content:none }} @bottom-right {{ content:none }} }}
html {{ font-family:{SERIF}; font-size:{fs}pt; line-height:1.25; color:#1b1f27; hyphens:auto; -webkit-hyphens:auto }}
body {{ margin:0 }}
p {{ margin:0 }}
i {{ font-style:italic }}
sup {{ font-size:70%; line-height:0 }}
.kw {{ color:{BRIQUE} }}
/* manchette */
.mast {{ text-align:center; border-bottom:2.2pt solid {NAVY}; padding-bottom:4mm; margin-bottom:.6mm }}
.mast .ey {{ font:600 7pt {SANS}; letter-spacing:.3em; text-transform:uppercase; color:{ACC}; margin-bottom:.6mm }}
.mast h1 {{ margin:0; font:400 38pt/1 {SERIF}; color:{NAVY}; letter-spacing:-.01em }}
.mast h1 i {{ color:{ACC} }} .mast h1 span {{ font:600 36pt/1 {SANS}; letter-spacing:-.03em }}
.mast .st {{ margin-top:2mm; font:italic 9.5pt {SERIF}; color:#374151 }}
.band {{ display:table; width:100%; border-bottom:.6pt solid {NAVY}; padding:1.1mm 0; font:600 7.6pt {SANS}; color:{NAVY}; letter-spacing:.04em; margin-bottom:4.5mm }}
.band span {{ display:table-cell }} .band .r {{ text-align:right }}
/* essentiel et sommaire */
.top {{ display:table; width:100%; margin-bottom:3.5mm }}
.top > div {{ display:table-cell; vertical-align:top }}
.ess {{ border:1.2pt solid {ACC}; padding:2.4mm 3.2mm 2.6mm; vertical-align:middle !important }}
.ess p.l {{ font:italic {ess_pt}pt/1.3 {SERIF}; color:{ACC}; text-align:left; hyphens:manual }}
.gout {{ width:5mm }}
.som {{ width:52mm; border-left:.6pt solid #c9c2b4; padding-left:4mm }}
.som .k {{ font:700 7.5pt {SANS}; letter-spacing:.18em; text-transform:uppercase; color:{NAVY}; margin-bottom:1mm }}
.som a {{ display:block; color:#1f2937; text-decoration:none; font:400 8.2pt/1.45 {SANS} }}
.som a::after {{ content:leader(".") target-counter(attr(href), page); color:{ACC}; font-weight:600 }}
/* Une */
.une-h {{ margin:0 0 1.2mm; font:700 24pt/1.08 {SERIF}; color:{NAVY}; letter-spacing:-.01em; hyphens:manual }}
.une-k {{ font:700 7.5pt {SANS}; letter-spacing:.18em; text-transform:uppercase; color:{ACC}; margin-bottom:1mm; string-set:rub "À la une" }}
.une-c {{ font:11pt/1.35 {SERIF}; color:#374151; margin-bottom:2.5mm; hyphens:manual }}
/* colonnes */
.cols {{ column-count:4; column-gap:4mm; column-rule:.4pt solid #d8d2c6; text-align:justify }}
.une-cols {{ column-count:3; column-gap:4mm; column-rule:.4pt solid #d8d2c6; text-align:justify; padding-bottom:1mm }}
h2.rub {{ string-set:rub attr(data-rub); break-after:avoid; margin:3.6mm 0 2mm; padding-top:1.4mm; border-top:1.6pt solid {NAVY}; font:700 13pt/1.15 {SERIF}; color:{NAVY}; text-align:left; hyphens:manual }}
h2.rub span {{ display:inline-block; margin-right:2mm; padding:.4mm 1.6mm; background:{ACC}; color:#fff; font:700 7.2pt/1.3 {SANS}; letter-spacing:.14em; text-transform:uppercase; vertical-align:2pt }}
.rub-c {{ break-after:avoid; font:italic 9.6pt/1.32 {SERIF}; color:#4b5563; margin:-.6mm 0 2.4mm; text-align:left; hyphens:manual }}
.art, .rap {{ string-set:rub attr(data-rub) }}
.art {{ margin:0 0 2.4mm; padding-bottom:2mm; border-bottom:.4pt solid #d8d2c6 }}
.art:last-of-type {{ border-bottom:0 }}
.une-cols .art {{ margin:0 0 2mm; padding:0; border:0 }}   /* sans filet ni marge basse : sinon WeasyPrint ne répartit pas la Une sur trois colonnes */
h3.hl {{ margin:0 0 1.2mm; font:700 1.36em/1.14 {SANS}; color:{NAVY}; text-align:left; hyphens:manual; break-after:avoid }}
.txt {{ margin-bottom:.8mm }}
b.acc {{ font:700 .97em {SANS}; color:{NAVY} }}
.syn p, p.sp {{ margin:0 0 .6mm; text-indent:1em }}
.rap {{ margin:0 0 3mm; padding:1.6mm 2mm 1.2mm; border-top:.8pt solid {ACC}; background:#faf6ef; font-size:{petit}pt; line-height:1.27; text-align:left; hyphens:auto }}
.rap-t {{ font:700 .82em {SANS}; letter-spacing:.18em; text-transform:uppercase; color:{ACC}; margin-bottom:.8mm }}
.rap ul {{ margin:0; padding:0; list-style:none }} .rap li {{ margin:0 0 1mm }}
.rap-s {{ margin-top:.4mm; color:#374151 }}
/* bas de la dernière page : à gauche, fin de la dernière rubrique (deux colonnes) puis crédit ; à droite, agenda */
.bas {{ display:table; width:100%; table-layout:fixed; break-inside:avoid }}
.bas > div {{ display:table-cell; vertical-align:top }}
.bas .bas-g {{ padding-right:2mm; border-right:.4pt solid #d8d2c6 }}
.bas .bas-d {{ padding-left:2mm; vertical-align:bottom }}
.bas h2.rub {{ margin:0 0 2mm }}
.cols2 .rap {{ display:inline-block; width:100%; box-sizing:border-box }}   /* encadré non sécable dans la suite à gauche de l'agenda */
.cols2 {{ column-count:2; column-gap:4mm; column-rule:.4pt solid #d8d2c6; text-align:justify; margin-bottom:2.4mm }}
.ag {{ column-count:2; column-gap:4mm; column-rule:.4pt solid #d8d2c6 }}
.ag-e {{ display:table; width:100%; margin-bottom:1.8mm; break-inside:avoid; text-align:left }}
.ag-e > div {{ display:table-cell; vertical-align:top }}
.ag-e > .ag-dt {{ width:9.4mm; padding-right:2mm }}
.ag-cal {{ width:9.4mm; height:9.4mm; box-sizing:border-box; border:1pt solid {ACC}; border-radius:2mm; text-align:center; padding-top:1.3mm; color:{NAVY} }}
.ag-cal .j {{ display:block; font:700 11.5pt/1 {SANS} }}
.ag-cal .m {{ display:block; font:600 5.8pt/1.2 {SANS}; letter-spacing:.05em; text-transform:uppercase; color:{ACC}; margin-top:.4mm }}
.ag-cal.mois {{ padding-top:2mm }} .ag-cal.mois .j {{ font-size:7.6pt; letter-spacing:.03em; text-transform:uppercase }}
.ag-th {{ font:700 6.8pt/1.2 {SANS}; letter-spacing:.1em; text-transform:uppercase; color:#7d6c47; margin-bottom:.4mm }}
.ag-q {{ font-size:{petit}pt; line-height:1.25 }} .ag-x {{ font-size:{petit}pt; color:#4b5563; line-height:1.25; margin-top:.3mm }}
/* lexique et colophon */
.lex dl {{ margin:0; font-size:{petit}pt; line-height:1.26; text-align:left }}
.lex dt {{ font:700 .95em {SANS}; color:{NAVY}; margin-top:.8mm; break-after:avoid }} .lex dd {{ margin:0 }}
.colo {{ display:table; width:100%; table-layout:fixed }}
.colo-qr {{ display:table-cell; width:22mm; vertical-align:bottom }} .colo-qr .qr {{ display:block; width:22mm; height:22mm }}
.colo-t {{ display:table-cell; vertical-align:bottom; padding-left:3mm; font:400 {colo_pt}pt/1.3 {SANS}; color:#4b5563; text-align:left; hyphens:manual }}
.colo-t .mq {{ font:400 1.9em/1 {SERIF}; color:{NAVY}; margin-bottom:.25em }} .colo-t .mq i {{ color:{ACC} }} .colo-t .mq span {{ font:600 .95em/1 {SANS} }}
'''


def rub_courante(h, lab):
    """Chaque article et chaque encadré porte sa rubrique : l'en-tête courant affiche celle du premier de la page."""
    a = f' data-rub="{html.escape(lab, True)}"'
    return h.replace('<article class="art', f'<article{a} class="art').replace('<aside class="rap"', f'<aside{a} class="rap"')


def page_html(ed, fs, incl, espace=0.0, haut_seul=False):
    """incl : blocs facultatifs retenus par le calage (voir blocs()) ; espace : blanc (px) inséré avant le bas de la
    dernière page pour le caler en bas ; haut_seul : manchette, bandeau, essentiel et sommaire seulement (mesure)."""
    avec_lexique = ('lexique', '') in incl
    m = ed['meta']; d = m['date_iso']
    url = f'{m.get("site", "https://revue.dejeun.es/").rstrip("/")}/{d}/'
    rubs = ed['rubriques']
    une = rubs[0] if rubs and rubs[0]['label'].lower().startswith('à la une') else None
    autres = rubs[1:] if une else rubs
    som = []
    toc = [x for x in m.get('toc', []) if not x.lower().startswith(('à la une', 'agenda'))]
    for k, r in enumerate(autres):   # libellés courts du sommaire de l'édition (meta.json, toc) quand ils correspondent
        som.append(f'<a href="#r{k}">{T(toc[k] if len(toc) == len(autres) else r["label"])}</a>')
    if ed['agenda']: som.append('<a href="#r-agenda">Agenda</a>')
    if avec_lexique: som.append('<a href="#r-lexique">Lexique</a>')
    h = [f'<header class="mast"><div class="ey">Revue de presse hebdomadaire</div><h1><i>Software</i> <span>Compliance</span></h1>'
         f'<div class="st">L’essentiel de la conformité des logiciels embarqués dans les produits de défense</div></header>'
         f'<div class="band"><span>N°\u00a0{m["n"]} – {T(m.get("date_long", m["date"]))}</span><span class="r">Revue de presse hebdomadaire, tous les mardis</span></div>'
         f'<div class="top"><div class="ess"><div class="ess-in"><p class="l">{T(ed["chapo"])}</p></div></div><div class="gout"></div>'
         f'<div class="som"><div class="som-in"><div class="k">Dans ce numéro</div>{"".join(som)}</div></div></div>']
    if haut_seul:
        return f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><style>{css(fs, m, ed.get("ess_pt", 11.0), ed.get("colo_pt", 7.6))}</style></head><body>{"".join(h)}</body></html>'
    if une:
        tu = une['sous'] or une['label']
        h.append(f'<div class="une-k">À la une</div><h2 class="une-h">{T(tu[:1].upper() + tu[1:])}</h2>')
        if une['chapo']: h.append(f'<p class="une-c">{T(une["chapo"])}</p>')
        corps_une = ''.join(article(it, incl, une=(j == 0)) for j, it in enumerate(une['items']))
        h.append(f'<div class="une-cols">{rub_courante(corps_une + rappels(une["rappels"], incl), "À la une")}</div>')
    split = ed.get('k_split', 0)   # unités de la dernière rubrique placées à gauche de l'agenda, au-dessus du crédit
    reste_b = []
    for k, r in enumerate(autres):   # une rubrique = un titre sur toute la largeur + son propre bloc de colonnes
        if k == len(autres) - 1 and avec_lexique: h.append(lexique(''.join(h)))   # lexique avant la dernière rubrique
        sous = r['sous'][:1].upper() + r['sous'][1:]
        h.append(f'<h2 class="rub" id="r{k}" data-rub="{html.escape(r["label"], True)}"><span>{T(r["label"])}</span>{T(sous)}</h2>')
        if r['chapo']: h.append(f'<p class="rub-c">{T(r["chapo"])}</p>')
        us = unites(r, incl)
        if k == len(autres) - 1 and split:
            split = min(split, len(us)); us, reste_b = us[:len(us) - split], us[len(us) - split:]
        if us: h.append('<div class="cols">' + rub_courante(assembler(us), r['label']) + '</div>')
    if espace > 0: h.append(f'<div style="height:{espace:.2f}px"></div>')
    gauche = ''
    if reste_b:   # suite de la dernière rubrique : hauteur fixée par caler_fin(), colonne par colonne
        st = f' style="height:{ed["h_suite"]:.2f}px;column-fill:auto"' if ed.get('h_suite') else ''
        gauche += f'<div class="cols2" id="suite"{st}>{rub_courante(assembler(reste_b), autres[-1]["label"])}</div>'
    if ed.get('gap_g'): gauche += f'<div style="height:{ed["gap_g"]:.2f}px"></div>'
    gauche += credit(ed)
    h.append(f'<div class="bas" id="bas"><div class="bas-g">{gauche}</div>'
             f'<div class="bas-d" id="bas-d">{agenda(ed["agenda"], incl, d[:4])}</div></div>')
    return (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Software Compliance – N° {m["n"]} – {html.escape(m["date"])}</title>'
            f'<style>{css(fs, m, ed.get("ess_pt", 11.0), ed.get("colo_pt", 7.6))}</style></head><body>{"".join(h)}</body></html>')


def credit(ed):
    m = ed['meta']; d = m['date_iso']
    url = f'{m.get("site", "https://revue.dejeun.es/").rstrip("/")}/{d}/'
    return (f'<div class="colo" id="colo"><div class="colo-qr">{qr(url)}</div><div class="colo-t" id="colo-t">'
            f'<div class="mq"><i>Software</i> <span>Compliance</span></div>'
            f'<p>Revue de presse hebdomadaire, N°\u00a0{m["n"]} du {T(m["date"])}. Rédigée par une intelligence artificielle '
            f'({T(m.get("redaction", "Anthropic Claude"))}) à partir des sources citées ; des erreurs sont possibles. '
            f'Édition en ligne, liens et sources : {html.escape(url)} · © {d[:4]} Rodolphe Dejeunes · CC BY 4.0</p></div></div>')


# ---------------------------------------------------------------- rendu, calage et imposition

def rendre(ed, fs, incl, espace=0.0):
    from weasyprint import HTML
    return HTML(string=page_html(ed, fs, incl, espace), base_url=ROOT).render()


def boites(page):
    def walk(b):
        yield b
        for c in getattr(b, 'children', []): yield from walk(c)
    return walk(page._page_box)


def boite(page, pred):
    for b in boites(page):
        el = getattr(b, 'element', None)
        if el is not None and pred(el) and type(b).__name__ not in ('LineBox', 'TextBox', 'InlineBox'): return b
    return None


def taille_essentiel(ed):
    """Plus grand corps de « L'essentiel » (de 14 à 9 pt) dont le cadre ne dépasse pas la hauteur du sommaire."""
    from weasyprint import HTML
    def mesure(pt):
        ed['ess_pt'] = pt
        pg = HTML(string=page_html(ed, CORPS_MIN, set(), haut_seul=True), base_url=ROOT).render().pages[0]
        cls = lambda c: (lambda el: c in (el.get('class') or '').split())
        return boite(pg, cls('ess-in')).margin_height(), boite(pg, cls('som-in')).margin_height()
    pad = (2.4 + 2.6) * 96 / 25.4 + 2 * 1.2 * 4 / 3   # marges intérieures et bordure du cadre (px)
    best = 9.0
    for pt in [x / 4 for x in range(56, 35, -1)]:   # 14 → 9 pt, par quart de point
        e, s_ = mesure(pt)
        if e + pad <= s_: best = pt; break
    ed['ess_pt'] = best
    return best


def taille_credit(ed):
    """Plus grand corps du crédit (de 9 à 5 pt) dont le texte (titre et paragraphe) ne dépasse pas la hauteur du code QR."""
    from weasyprint import HTML
    m = ed['meta']; qr_px = 22 * 96 / 25.4
    best = 5.0
    for pt in [x / 4 for x in range(36, 19, -1)]:   # 9 → 5 pt
        ed['colo_pt'] = pt
        h = (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><style>{css(CORPS_MIN, m, ed.get("ess_pt", 11.0), pt)}</style></head>'
             f'<body><div class="bas"><div class="bas-g">{credit(ed)}</div><div class="bas-d"></div></div></body></html>')
        pg = HTML(string=h, base_url=ROOT).render().pages[0]
        t = boite(pg, lambda el: el.get('id') == 'colo-t')
        if sum(c.margin_height() for c in t.children) <= qr_px: best = pt; break
    ed['colo_pt'] = best
    return best


def caler_fin(ed, fs, incl, cible):
    """Bas de la dernière page : à droite l'agenda ; à gauche, sur la même hauteur, le crédit calé en bas et, au-dessus,
    la fin de la dernière rubrique sur deux colonnes de hauteur fixe remplies l'une après l'autre (le plus grand nombre
    d'unités qui y tient) : la rubrique court sur quatre colonnes, puis « enveloppe » l'agenda jusqu'au crédit.
    Renvoie le document ou None."""
    rubs = ed['rubriques']
    une = rubs[0] if rubs and rubs[0]['label'].lower().startswith('à la une') else None
    autres = rubs[1:] if une else rubs
    par_id = lambda pg, i: boite(pg, lambda el: el.get('id') == i)
    ed['k_split'] = 0; ed['h_suite'] = None; ed['gap_g'] = 0
    doc = rendre(ed, fs, incl)
    pg = doc.pages[-1]; colo, bd = par_id(pg, 'colo'), par_id(pg, 'bas-d')
    if colo is None or bd is None: return doc
    h_ag = sum(c.margin_height() for c in bd.children); h_colo = colo.margin_height()
    h_box = h_ag - h_colo - 2.4 * 96 / 25.4
    n = len(unites(autres[-1], incl)) if autres else 0
    if h_box < 15 * 96 / 25.4 or not n:   # agenda trop court : blanc au-dessus du crédit
        ed['gap_g'] = max(0.0, h_ag - h_colo)
        return rendre(ed, fs, incl)
    ed['h_suite'] = h_box

    def essai(k):
        ed['k_split'] = k
        d = rendre(ed, fs, incl)
        if len(d.pages) > cible: return None
        su = par_id(d.pages[-1], 'suite')
        cols = [c for c in (su.children if su is not None else []) if c.margin_height() > 0]
        return d if su is not None and len(cols) <= 2 else None

    lo, hi, best = 1, n, None
    while lo <= hi:   # plus grand nombre d'unités qui tient dans les deux colonnes de gauche
        mid = (lo + hi) // 2; d = essai(mid)
        if d is not None: best, lo = (mid, d), mid + 1
        else: hi = mid - 1
    if best is None:
        ed['k_split'] = 0; ed['h_suite'] = None; ed['gap_g'] = max(0.0, h_ag - h_colo)
        return rendre(ed, fs, incl)
    ed['k_split'] = best[0]
    for _ in range(3):   # le bas occupe toute la hauteur restante : les deux colonnes de gauche s'allongent d'autant
        d = best[1]; pg = d.pages[-1]; pb = pg._page_box; bas = par_id(pg, 'bas')
        dispo = pb.content_box_y() + pb.height - bas.position_y - 1
        h_new = dispo - h_colo - 2.4 * 96 / 25.4
        if h_new <= ed['h_suite'] + 2: break
        ed['h_suite'] = h_new
        lo, hi, b2 = best[0], n, None
        while lo <= hi:
            mid = (lo + hi) // 2; d = essai(mid)
            if d is not None: b2, lo = (mid, d), mid + 1
            else: hi = mid - 1
        if b2 is None: ed['h_suite'] -= 4; ed['k_split'] = best[0]; best = (best[0], rendre(ed, fs, incl)); break
        best = b2; ed['k_split'] = best[0]
    return best[1]


def caler_bas(ed, fs, incl, doc):
    """Insère un blanc pour que le bloc du bas (crédit et agenda) touche le bas de la dernière page."""
    pg = doc.pages[-1]
    b = boite(pg, lambda el: el.get('id') == 'bas')
    if b is None: return doc, 0.0
    pb = pg._page_box
    reste = pb.content_box_y() + pb.height - (b.position_y + b.margin_height()) - 1
    if reste <= 2: return doc, 0.0
    n = len(doc.pages)
    for esp in (reste, reste - 6, reste - 14):
        d2 = rendre(ed, fs, incl, esp)
        if len(d2.pages) == n: return d2, esp
    return doc, 0.0


def blocs(ed):
    """Blocs facultatifs, du plus important au moins important : ajoutés dans cet ordre jusqu'à remplir les pages.
    Nouveautés (hors Une, toujours complète) triées par cote décroissante (impact × urgence × certitude) :
    d'abord leur Résumé, puis Impact (acquis, puis possible), puis Contexte ; ensuite le détail de l'agenda,
    le résumé des rappels (ordre des rubriques), enfin le lexique."""
    rubs = ed['rubriques']
    une = rubs[0] if rubs and rubs[0]['label'].lower().startswith('à la une') else None
    nouv = [it for r in rubs if r is not une for it in r['items'] if it.get('sum')]
    if une: nouv += [it for it in une['items'][1:] if it.get('sum')]
    cote = lambda it: -(lambda c: c[0] * c[1] * c[2] if len(c) == 3 else 0)(it['a'].get('cote') or [])
    nouv = sorted(nouv, key=cote)   # tri stable : à cote égale, ordre de l'édition
    b = [(k, it['id']) for k in ('essentiel', 'impact_avere', 'impact_potentiel', 'contexte') for it in nouv if (it['sum'] or {}).get(k)]
    b += [('detail', e['id']) for e in ed['agenda'] if e.get('detail')]
    b += [('essentiel', it['id']) for r in rubs for it in r['rappels'] if (it.get('sum') or {}).get('essentiel')]
    return b + [('lexique', '')]


def remplissage(doc):
    """Part de la hauteur utile de la dernière page occupée par le contenu (0 à 1)."""
    pb = doc.pages[-1]._page_box
    haut = pb.content_box_y(); bas = haut
    def parcourir(bx):
        nonlocal bas
        for c in getattr(bx, 'children', []):
            if type(c).__name__ == 'MarginBox': continue
            if getattr(c, 'height', None) is not None and getattr(c, 'position_y', None) is not None:
                if type(c).__name__ in ('LineBox', 'ImageBox', 'InlineReplacedBox', 'BlockReplacedBox'): bas = max(bas, c.position_y + c.height)
            parcourir(c)
    parcourir(pb)
    return min(1.0, (bas - haut) / pb.height)


def caler(ed, indice=None):
    """Exactement PAGES pages, corps des paragraphes ≥ CORPS_MIN : si tout le contenu tient au corps minimal, plus grand
    corps qui le fait tenir ; sinon, au corps minimal, le plus grand nombre de blocs facultatifs (blocs()) qui tient.
    Une édition dont le contenu obligatoire dépasse PAGES pages au corps minimal passe à 8 pages (puis 12).
    indice : nombre de blocs d'un calage précédent, pour resserrer la recherche (gain de temps)."""
    bl = blocs(ed); n = len(bl)
    if indice is not None and 0 < indice < n:   # recherche resserrée autour du calage précédent
        a, b = max(0, indice - 6), min(n, indice + 6)
        if len(rendre(ed, CORPS_MIN, set(bl[:a])).pages) <= PAGES and len(rendre(ed, CORPS_MIN, set(bl[:b])).pages) > PAGES:
            lo, hi, best = a + 1, b - 1, (CORPS_MIN, set(bl[:a]), None, PAGES)
            while lo <= hi:
                mid = (lo + hi) // 2; incl = set(bl[:mid]); doc = rendre(ed, CORPS_MIN, incl)
                if len(doc.pages) <= PAGES: best, lo = (CORPS_MIN, incl, doc, PAGES), mid + 1
                else: hi = mid - 1
            if best[2] is None: best = (CORPS_MIN, best[1], rendre(ed, CORPS_MIN, best[1]), PAGES)
            return best
    for cible in (PAGES, 2 * PAGES, 3 * PAGES):
        if len(rendre(ed, CORPS_MIN, set()).pages) > cible: continue
        tout = set(bl)
        if len(rendre(ed, CORPS_MIN, tout).pages) <= cible:   # tout tient : on grossit le corps
            lo, hi, best = 0, len(TAILLES) - 1, None
            while lo <= hi:
                mid = (lo + hi) // 2; doc = rendre(ed, TAILLES[mid], tout)
                if len(doc.pages) <= cible: best, hi = (TAILLES[mid], tout, doc, cible), mid - 1
                else: lo = mid + 1
            return best
        lo, hi, best = 0, n, None   # au corps minimal, plus grand préfixe de blocs qui tient
        while lo <= hi:
            mid = (lo + hi) // 2; incl = set(bl[:mid]); doc = rendre(ed, CORPS_MIN, incl)
            if len(doc.pages) <= cible: best, lo = (CORPS_MIN, incl, doc, cible), mid + 1
            else: hi = mid - 1
        return best
    doc = rendre(ed, CORPS_MIN, set())
    return CORPS_MIN, set(), doc, -(-len(doc.pages) // 4) * 4


def imposer(a4, a3):
    """Imposition en cahier sur feuilles A3 paysage recto-verso, pliées au milieu et emboîtées : pour 4 pages,
    recto 4 | 1 et verso 2 | 3 ; pour 8 pages, feuille extérieure 8 | 1 et 2 | 7, feuille intérieure 6 | 3 et 4 | 5."""
    from pypdf import PdfReader, PdfWriter, PageObject, Transformation
    r = PdfReader(a4); p = list(r.pages)
    n = -(-len(p) // 4) * 4
    p += [None] * (n - len(p))   # pages blanches en fin de cahier si besoin
    w, h = float(r.pages[0].mediabox.width), float(r.pages[0].mediabox.height)
    out = PdfWriter()
    for f_ in range(n // 4):
        for g, dr in ((n - 2 * f_, 1 + 2 * f_), (2 + 2 * f_, n - 1 - 2 * f_)):   # numéros de page (1 = première)
            f = PageObject.create_blank_page(width=2 * w, height=h)
            if p[g - 1] is not None: f.merge_transformed_page(p[g - 1], Transformation().translate(0, 0))
            if p[dr - 1] is not None: f.merge_transformed_page(p[dr - 1], Transformation().translate(w, 0))
            out.add_page(f)
    out.add_metadata({'/Title': str((r.metadata or {}).get('/Title', 'Software Compliance')) + ' (A3 imposé)'})
    with open(a3, 'wb') as fh: out.write(fh)


def complet(h, pdf):
    """Garde-fou : WeasyPrint peut perdre du texte dans certains blocs de colonnes ; le PDF doit contenir le colophon
    et au moins 97 % des mots du HTML (les césures et l'en-tête courant en ajoutent), sinon il n'est pas publié."""
    from pypdf import PdfReader
    t = ' '.join(p.extract_text() or '' for p in PdfReader(pdf).pages)
    src = html.unescape(re.sub(r'<[^>]+>', ' ', re.sub(r'<style.*?</style>', ' ', h, flags=re.S)))
    n_pdf, n_src = len(t.split()), len(src.split())
    if 'CC BY 4.0' not in t or n_pdf < 0.97 * n_src:
        os.remove(pdf)
        raise RuntimeError(f'texte incomplet dans le PDF ({n_pdf} mots pour {n_src} dans la page)')


def empreinte(d):
    hsh = hashlib.sha256(VERSION.encode())
    for f in [os.path.join(CONTENT, d, 'blocks.json'), os.path.join(CONTENT, d, 'meta.json'), __file__,
              os.path.join(TOOLS, 'commun.py'), os.path.join(TOOLS, 'glossary.py')]:
        hsh.update(open(f, 'rb').read())
    return hsh.hexdigest()[:16]


def produire(d, sortie=None):
    """Produit les deux PDF de l'édition d dans sortie (défaut build/d) ; cache dans build/pdf-cache. Renvoie un résumé."""
    sortie = sortie or os.path.join(BUILD, d)
    os.makedirs(sortie, exist_ok=True)
    cache = os.path.join(BUILD, 'pdf-cache'); os.makedirs(cache, exist_ok=True)
    e = empreinte(d)
    a4, a3 = os.path.join(sortie, f'revue-{d}.pdf'), os.path.join(sortie, f'revue-{d}-a3.pdf')
    c4, c3, cj = (os.path.join(cache, f'{d}-{e}{s}') for s in ('.pdf', '-a3.pdf', '.json'))
    if os.path.exists(c4) and os.path.exists(c3) and os.path.exists(cj):
        shutil.copy(c4, a4); shutil.copy(c3, a3); return json.load(open(cj))
    ed = lire(d)
    taille_essentiel(ed); taille_credit(ed)
    ed['k_split'] = 0; ed['gap_g'] = 0; ed['h_suite'] = None
    meilleur, prec, fs_prec = None, None, None
    for _ in range(4):   # calage du contenu, puis de la fin de la dernière rubrique à gauche de l'agenda, et ainsi de suite
        fs, incl, doc, cible = caler(ed, len(prec) if prec is not None and fs_prec == CORPS_MIN else None)
        fs_prec = fs
        d2 = caler_fin(ed, fs, incl, cible)
        if d2 is not None and len(d2.pages) == cible and (meilleur is None or (len(incl), fs) > (len(meilleur[1]), meilleur[0])):
            meilleur = (fs, incl, d2, cible, {k: ed[k] for k in ('k_split', 'h_suite', 'gap_g')})
        if incl == prec: break
        prec = incl
    if meilleur:
        fs, incl, doc, cible, etat = meilleur; ed.update(etat)
    doc, esp = caler_bas(ed, fs, incl, doc)
    doc.write_pdf(a4)
    complet(page_html(ed, fs, incl, esp), a4)
    print(f"  suite à gauche de l'agenda : {ed['k_split']} unité(s) ; essentiel {ed['ess_pt']} pt ; crédit {ed['colo_pt']} pt", file=sys.stderr)
    imposer(a4, a3)
    bl = blocs(ed)
    info = {'edition': d, 'pages': len(doc.pages), 'cahier': cible, 'corps_pt': fs, 'blocs': f'{len(incl)}/{len(bl)}',
            'remplissage': round(remplissage(doc), 2), 'lexique': ('lexique', '') in incl}
    shutil.copy(a4, c4); shutil.copy(a3, c3); json.dump(info, open(cj, 'w'))
    return info


def main():
    eds = sys.argv[1:] or sorted(x for x in os.listdir(CONTENT) if re.fullmatch(r'\d{4}-\d{2}-\d{2}', x))[-1:]
    for d in eds:
        i = produire(d)
        print(f"{d} : {i['pages']} pages (cahier de {i['cahier']}), corps {i['corps_pt']} pt, blocs facultatifs {i['blocs']}, "
              f"dernière page remplie à {round(100 * i['remplissage'])} %")


if __name__ == '__main__':
    main()
