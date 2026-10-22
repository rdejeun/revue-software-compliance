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
INTERLIGNE = 1.3   # interligne des paragraphes
TAILLES = [10.0, 9.8, 9.6, 9.4, 9.2, 9.0, 8.8, 8.6, 8.5]   # corps des paragraphes (pt), du plus grand au plus petit
MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
MOISC = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.']
NAVY, ACC, BRIQUE = '#0f2a4a', '#c2410c', '#9a3412'
VERSION = 'journal-34'   # à changer quand la mise en page change (invalide le cache)


RENVOI = re.compile(r'\s*\((?:voir|cf\.)\s+(?:aussi\s+)?(?:le|les)\s+(?:N°|numéros?)\s*[\d\s,et]+\)', re.I)   # « (voir le N° 1) »


VERSION_0 = re.compile(r'(?<![\d.])(\d+\.\d+)\.0(?!\d|\.\d)')   # « 0.76.0 » -> « 0.76 »


MARQUE = re.compile(r'\b(?:[A-Za-z]*[a-z][A-Z][A-Za-z]*|[A-Z]{2,}[a-z]+[A-Za-z]*)\b')   # GitHub, OpenSSF, OVHcloud…


def sans_cesure(h):
    """Noms de marque à capitale intérieure (GitHub, LibreOffice, OVHcloud) : jamais coupés en fin de ligne."""
    return ''.join(x if x.startswith('<') else MARQUE.sub(r'<span class="nh">\g<0></span>', x) for x in re.split(r'(<[^>]+>)', h))


def T(s): return sans_cesure(E(typo(VERSION_0.sub(r'\1', RENVOI.sub('', s or '')))))
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
    srcs, out, labs = [], [], []
    for x in segs:
        if x.get('href') and x.get('type') != 'projet':
            lab = x['t'][2:] if x['t'].startswith('↗\u00a0') else x['t']
            srcs.append((lab, x['href'], officiel(x['href']), x.get('type') == 'editeur')); out.append(f'\x00{len(labs)}\x02'); labs.append(lab)
        else:
            out.append(('\x01' if x.get('type') == 'projet' else '') + x.get('t', ''))
    t = ''.join(out)
    S_ = r'\x00\d+\x02'
    t = re.sub(r'\s*\(\s*' + S_ + r'(?:\s*[,;]\s*' + S_ + r')*\s*\)', '', t)   # « (Source1, Source2) »
    t = re.sub(r'[,;]?\s*' + S_ + r'(?=\s*(?:[,;.)]|$|\x00))', '', t)   # sources en fin de phrase
    t = re.sub(r'\x00(\d+)\x02', lambda m: labs[int(m[1])], t)   # lien au milieu d'une phrase (« par le règlement … du 15 octobre ») : son texte reste
    t = t.replace('\x01', '').strip()
    if t and t[-1] not in '.!?…': t += '.'
    t = re.sub(r'\s+\.$', '.', t)
    return t, srcs


def accroche(t):
    """Texte de l'élément, sans début en gras : le titre de l'article joue déjà ce rôle (rappels compris)."""
    return T(t)


FACULTATIF = re.compile(r'\{\{([123])\|(.*?)\}\}', re.S)   # portion facultative du champ « papier » : {{n|…}}, 3 coupée en premier


def papier(sm, iid, incl, tout=False):
    """Paragraphes du champ « papier » (README, § 6) : portions facultatives gardées selon le calage."""
    out = []
    for par in re.split(r'\n\s*\n', sm['papier'].strip()):
        par = FACULTATIF.sub(lambda m: m[2] if tout or (f'papier{m[1]}', iid) in incl else '', par)
        par = re.sub(r'\s{2,}', ' ', par).strip()
        if par: out.append(par)
    return out


def morceaux(it, incl, une=False):
    """Article en morceaux successifs : titre et texte, puis chaque paragraphe retenu (champ « papier » s'il existe,
    sinon paragraphes de la synthèse)."""
    t, _ = corps(it['segs'])
    sm = it.get('sum') or {}
    tit = sm.get('titre')
    m = [(f'<h3 class="hl">{T(tit)}</h3>' if tit and not une else '') + f'<p class="txt">{accroche(t)}</p>']
    if sm.get('papier'):
        if une or ('papier', it['id']) in incl: m += [f'<p class="sp">{T(x)}</p>' for x in papier(sm, it['id'], incl, une)]
        return m
    for k in ('contexte', 'essentiel', 'impact_avere', 'impact_potentiel'):
        if sm.get(k) and (une or (k, it['id']) in incl): m.append(f'<p class="sp">{T(sm[k])}</p>')
    return m


def article(it, incl, une=False):
    return f'<article class="art{" une" if une else ""}" id="art-{it["id"]}">' + ''.join(morceaux(it, incl, une)) + '</article>'


def rappels(rs, incl, moins=0):
    """Encadré « En bref » (rappels) : une seule colonne, jamais coupé (break-inside: avoid) ; moins : brèves omises
    (les dernières), quand l'encadré est trop haut pour le texte de sa rubrique (corriger())."""
    if not rs: return ''
    li = []
    rid = f'rap-{rs[0]["id"]}'
    for r in rs[:max(1, len(rs) - moins)]:
        t, _ = corps(r['segs'])
        res = (r.get('sum') or {}).get('essentiel')
        li.append(f'<li><p>{accroche(t)}</p>' + (f'<p class="rap-s">{T(res)}</p>' if res and ('essentiel', r['id']) in incl else '') + '</li>')
    return f'<aside class="rap" id="{rid}"><p class="rap-t">En bref</p><ul>{"".join(li)}</ul></aside>'


def demi(mo):
    """Mois abrégé centré : une demi-espace (espace fine) devant compense le point final."""
    return ' ' + mo if mo.endswith('.') else mo


def pastille(date, annee=None):
    """« 20 octobre 2026 » -> cadre arrondi « 20 / OCT. » ; « Novembre 2026 » -> « NOV. / 2026 »."""
    t = date.lower()
    m = re.search(r'(' + '|'.join(MOIS) + r')\s+(\d{4})', t)
    j = re.match(r'(1er|\d{1,2})(?:\s+au\s+(\d{1,2}))?', t)
    if m and j and (annee is None or m[2] == annee):
        jour = j[1] + (f'–{j[2]}' if j[2] else '')
        return f'<div class="ag-cal"><span class="j">{T(jour)}</span><span class="m">{demi(MOISC[MOIS.index(m[1])])}</span></div>'
    if m: return f'<div class="ag-cal mois"><span class="j">{demi(MOISC[MOIS.index(m[1])])}</span><span class="m">{m[2]}</span></div>'
    return f'<div class="ag-cal mois"><span class="j">{T(date[:6])}</span></div>'


def redondant(quoi, detail):
    """L'accroche d'une échéance (« quoi ») est redondante quand le détail en reprend la plupart des mots
    (« Application complète du CRA » / « Application complète du CRA ; selon l'ENISA… ») : on ne garde que le détail."""
    w = lambda s: {x.lower() for x in re.findall(r'\w{4,}', s or '')}
    q = w(quoi)
    return not q or len(q & w(detail)) >= .5 * len(q)


def entree_agenda(e, annee):
    if e.get('detail') and redondant(e['quoi'], e['detail']): txt = f'<p class="ag-q">{T(e["detail"])}</p>'
    else: txt = f'<p class="ag-q">{T(e["quoi"])}</p>' + (f'<p class="ag-x">{T(e["detail"])}</p>' if e.get('detail') else '')
    return (f'<div class="ag-e" id="ag-{e["id"]}"><div class="ag-dt">{pastille(e["date"], annee)}</div><div>'
            f'<p class="ag-th">{T(e["theme"])}</p>{txt}</div></div>')


def agenda(ev, annee=None, coupe=None):
    """Agenda sur deux colonnes (tableau) : les dates ev[:coupe] à gauche, les suivantes à droite ; coupe choisie par
    coupe_agenda() pour équilibrer la hauteur des deux colonnes."""
    if not ev: return ''
    s = -(-len(ev) // 2) if coupe is None else coupe
    col = lambda xs: ''.join(entree_agenda(e, annee) for e in xs)
    return ('<h2 class="rub" id="r-agenda"><span>Agenda</span> Dates à surveiller</h2>'
            f'<table class="ag"><tr><td class="ag-1">{col(ev[:s])}</td><td class="ag-2">{col(ev[s:])}</td></tr></table>')


def court(de):
    """Définition courte d'un sigle pour le lexique imprimé : son développement (avant « : »), sinon le début de sa
    première phrase (avant « ; », puis avant « qui », « pour » ou une virgule quand elle est longue)."""
    de = sans_ital(de).strip()
    if ' : ' in de[:120]: return de.split(' : ', 1)[0].rstrip('.')
    de = re.split(r'(?<=[a-zé\)])\.\s', de, maxsplit=1)[0].split(' ; ')[0].rstrip('.')
    if len(de) > 70:
        m = re.search(r'.{25,}?(?=,\s| qui | pour | dont )', de)
        if m: de = m[0]
    return de


def sigles(texte_html):
    """Sigles du glossaire cités dans le texte : [(sigle, définition courte, nombre de citations)] ; pour une entrée
    nommée en toutes lettres mais repérée par son sigle (« CRA » : Cyber Resilience Act), le sigle et son nom."""
    plain = re.sub(r'<[^>]+>', ' ', texte_html)
    vus, h = set(), []
    sig = lambda x: re.fullmatch(r'[A-Z][A-Z0-9-]{1,9}', x)
    for rx, lab, de, _u in G:
        if not sig(rx): continue   # sigles seulement (CRA, SBOM, ECJU…)
        nom, dfn = (lab, court(de)) if sig(lab) else (rx, re.sub(r'\s*\(' + rx + r'\)', '', lab))   # « Norme européenne (EN) »
        if re.search(r'\b' + rx + r'\b', dfn) and not sig(lab): dfn = court(de)   # « Licence OTN » : sa définition
        if nom in vus: continue
        n = len(re.findall(r'(?<![\w-])(' + rx + r')(?![\w])', plain))
        if n: vus.add(nom); h.append((nom, dfn, n))
    return h


def lexique(ed):
    """Lexique des sigles cités, en appoint (README, § 18) : placé au bas d'une page qui resterait blanche, avec les
    ed['lex_n'] sigles les plus cités (tous par défaut), dans l'ordre alphabétique, définition courte."""
    h = ed.get('sigles') or []
    n = ed.get('lex_n')
    if n is not None: h = sorted(h, key=lambda x: (-x[2], x[0]))[:n]
    h = sorted(h, key=lambda x: x[0].lower())
    if not h: return ''
    return (f'<h2 class="rub" id="r-lexique"{air(ed, "r-lexique", 3.6)}><span>Lexique</span> Sigles cités</h2><div class="cols lex" id="clex">'
            + ''.join(f'<p class="lx"><b>{T(lab)}</b> {T(de)}</p>' for lab, de, _n in h) + '</div>')


def qr(url):
    try:
        import qrcode, qrcode.image.svg
        img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=0)
        b = io.BytesIO(); img.save(b)
        svg = b.getvalue().replace(b'fill="#000000"', b'fill="#7d6c47"')   # couleur des titres de l'agenda
        return f'<img class="qr" src="data:image/svg+xml;base64,{base64.b64encode(svg).decode()}" alt="">'
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


def css(fs, meta, ed=None):
    ed = ed or {}
    ess_pt, colo_pt = ed.get('ess_pt', 11.0), ed.get('colo_pt', 7.6)
    pied = f'Software Compliance – {meta["date"]}'
    petit = max(PETIT_MIN, round(fs - .5, 2))   # rappels, agenda, lexique
    ag = petit + ed.get('tw', {}).get('ag', (0,))[0]   # agenda : jusqu'à 0,75 pt de plus, pour égaler la hauteur de la dernière rubrique
    titre = round(1.36 * fs, 2)   # titres d'article : fixes, même quand le corps d'une rubrique est ajusté
    entete = os.path.join(TOOLS, 'en-tete.webp')
    return polices() + f'''
@page {{ size:A4; margin:11mm 9.5mm 13mm 9.5mm }}
@page :right {{ @bottom-left {{ content:"{pied}"; font:400 7.5pt {SANS}; color:#6b7280; vertical-align:top; padding-top:2mm }}
               @bottom-right {{ content:counter(page); font:700 9pt {SANS}; color:{NAVY}; vertical-align:top; padding-top:1.6mm }} }}
@page :left {{ @bottom-left {{ content:counter(page); font:700 9pt {SANS}; color:{NAVY}; vertical-align:top; padding-top:1.6mm }}
              @bottom-right {{ content:"{pied}"; font:400 7.5pt {SANS}; color:#6b7280; vertical-align:top; padding-top:2mm }} }}
@page :first {{ margin-top:11mm; @bottom-left {{ content:none }} @bottom-right {{ content:none }} }}
html {{ font-family:{SERIF}; font-size:{fs}pt; line-height:{INTERLIGNE}; color:#1b1f27; hyphens:auto; -webkit-hyphens:auto; orphans:2; widows:2 }}
body {{ margin:0 }}
p {{ margin:0 }}
i {{ font-style:italic }}
sup {{ font-size:70%; line-height:0 }}
.kw {{ color:{BRIQUE} }} .nh {{ hyphens:manual }}
/* manchette : dessin d'en-tête du site (graphe, certificats, circuits) estompé en haut à droite */
.mast {{ position:relative; text-align:center; padding-bottom:9mm }}
.mast::before {{ content:""; position:absolute; right:-9.5mm; top:-11mm; width:120mm; height:42mm; background:url('file://{entete}') no-repeat right top / auto 100%; opacity:.7 }}
.mast > * {{ position:relative }}
.mast .ey {{ font:600 7.7pt {SANS}; letter-spacing:.3em; text-transform:uppercase; color:{ACC}; margin-bottom:.6mm }}
.mast h1 {{ margin:0; font:400 38pt/1 {SERIF}; color:{NAVY}; letter-spacing:-.01em }}
.mast h1 i {{ color:{ACC} }} .mast h1 span {{ font:600 36pt/1 {SANS}; letter-spacing:-.03em }}
.mast .st {{ margin-top:2mm; font:italic 9.5pt {SERIF}; color:#374151 }}
/* bandeau « onglet » : le numéro et la date dans un onglet, le reste sur un filet */
.band {{ display:flex; justify-content:space-between; align-items:flex-end; border-bottom:.8pt solid {NAVY}; color:{NAVY}; font:600 8.75pt/1.25 {SANS}; letter-spacing:.04em; margin-bottom:4.5mm }}
.band .n {{ background:{NAVY}; color:#fff; padding:.6mm 3mm .5mm 2.4mm }} .band .r {{ padding-bottom:.6mm }}
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
.une-k {{ font:700 7.5pt {SANS}; letter-spacing:.18em; text-transform:uppercase; color:{ACC}; margin-bottom:1mm }}
.une-c {{ font:11pt/1.35 {SERIF}; color:#374151; margin-bottom:2.5mm; hyphens:manual }}
/* colonnes */
.cols {{ column-count:4; column-gap:4mm; column-rule:.4pt solid #d8d2c6; text-align:justify }}
.une-cols {{ column-count:3; column-gap:4mm; column-rule:.4pt solid #d8d2c6; text-align:justify; padding-bottom:1mm }}
.cols2 {{ column-count:2; column-gap:4mm; column-rule:.4pt solid #d8d2c6; text-align:justify }}
h2.rub {{ break-after:avoid; margin:3.6mm 0 2mm; padding-top:1.4mm; border-top:1.6pt solid {NAVY}; font:700 13pt/1.15 {SERIF}; color:{NAVY}; text-align:left; hyphens:manual }}
h2.rub span {{ display:inline-block; margin-right:2mm; padding:.4mm 1.6mm; background:{ACC}; color:#fff; font:700 7.2pt/1.3 {SANS}; letter-spacing:.14em; text-transform:uppercase; vertical-align:2pt }}
.rub-c {{ break-after:avoid; font:italic 9.6pt/1.32 {SERIF}; color:#4b5563; margin:-.6mm 0 2.4mm; text-align:left; hyphens:manual }}
.art {{ margin:0 0 2.4mm; padding-bottom:2mm; border-bottom:.4pt solid #d8d2c6 }}
.art:last-of-type {{ border-bottom:0; padding-bottom:0 }}
.une-cols .art {{ margin:0 0 2mm; padding:0; border:0 }}   /* sans filet ni marge basse : sinon WeasyPrint ne répartit pas la Une sur trois colonnes */
h3.hl {{ margin:0 0 1.2mm; font:700 {titre}pt/1.14 {SANS}; color:{NAVY}; text-align:left; hyphens:manual; break-after:avoid }}
.txt {{ margin-bottom:.8mm }}
p.sp {{ margin:0 0 .6mm; text-indent:1em }}
/* « En bref » : encadré d'une colonne, jamais coupé */
.rap {{ break-inside:avoid; margin:0 0 2mm; padding:1.6mm 2mm 1.2mm; border-top:.8pt solid {ACC}; background:#faf6ef; font-size:{petit}pt; line-height:1.27; text-align:left; hyphens:auto }}
.rap-t {{ font:700 .82em {SANS}; letter-spacing:.18em; text-transform:uppercase; color:{ACC}; margin-bottom:.8mm }}
.rap ul {{ margin:0; padding:0; list-style:none }} .rap li {{ margin:0 0 1.1mm }} .rap li:last-child {{ margin-bottom:0 }}
.rap li + li {{ padding-top:1.1mm; border-top:.4pt solid #e6dccb }}
.rap-s {{ margin-top:.4mm; color:#374151 }}
/* bas de la dernière page : à gauche l'agenda, à droite la dernière rubrique puis le crédit, calé en bas de page */
.bas {{ display:table; width:100%; table-layout:fixed; break-inside:avoid }}
.bas > div {{ display:table-cell; vertical-align:top }}
.bas .bas-g {{ padding-right:2mm; border-right:.4pt solid #d8d2c6 }}
.bas .bas-d {{ padding-left:2mm }}
.bas h2.rub {{ margin:0 0 2mm }}
table.ag {{ width:100%; table-layout:fixed; border-collapse:collapse }}
table.ag td {{ vertical-align:top; padding:0 }} table.ag td.ag-1 {{ padding-right:2mm; border-right:.4pt solid #d8d2c6 }} table.ag td.ag-2 {{ padding-left:2mm }}
.ag-e {{ display:table; width:100%; margin-bottom:1.8mm; text-align:left }}
.ag-e > div {{ display:table-cell; vertical-align:top }}
.ag-e > .ag-dt {{ width:9.4mm; padding-right:2mm }}
.ag-cal {{ width:9.4mm; height:9.4mm; box-sizing:border-box; border:1pt solid {ACC}; border-radius:2mm; text-align:center; padding-top:1.3mm; color:{NAVY} }}
.ag-cal .j {{ display:block; font:700 11.5pt/1 {SANS} }}
.ag-cal .m {{ display:block; font:600 5.8pt/1.2 {SANS}; letter-spacing:.05em; text-transform:uppercase; color:{ACC}; margin-top:.4mm }}
.ag-cal.mois {{ padding-top:2mm }} .ag-cal.mois .j {{ font-size:7.6pt; letter-spacing:.03em; text-transform:uppercase }}
.ag-th {{ font:700 {round(6.8 * ag / petit, 2)}pt/1.2 {SANS}; letter-spacing:.1em; text-transform:uppercase; color:#7d6c47; margin-bottom:.4mm; hyphens:manual }}
.ag-q {{ font-size:{ag}pt; line-height:1.25 }} .ag-x {{ font-size:{ag}pt; color:#4b5563; line-height:1.25; margin-top:.3mm }}
/* lexique et colophon */
.lex {{ font-size:{petit}pt; line-height:1.26; text-align:left; hyphens:auto }}
.lex p.lx {{ margin:0 0 .7mm; padding-left:1.2em; text-indent:-1.2em }} .lex p.lx b {{ font:700 .95em {SANS}; color:{NAVY} }}
.colo {{ display:table; width:100%; table-layout:fixed; margin-top:3mm }}
.colo-qr {{ display:table-cell; width:22mm; vertical-align:bottom }} .colo-qr .qr {{ display:block; width:22mm; height:22mm }}
.colo-t {{ display:table-cell; vertical-align:bottom; padding-right:3mm; font:400 {colo_pt}pt/1.3 {SANS}; color:#4b5563; text-align:right; hyphens:manual }}
.colo-t .mq {{ font:400 1.9em/1 {SERIF}; color:{NAVY}; margin-bottom:.25em }} .colo-t .mq i {{ color:{ACC} }} .colo-t .mq span {{ font:600 .95em/1 {SANS} }} .nw {{ white-space:nowrap }}
'''


def une_autres(ed):
    rubs = ed['rubriques']
    une = rubs[0] if rubs and rubs[0]['label'].lower().startswith('à la une') else None
    return une, (rubs[1:] if une else rubs)


def reglage(ed, k, fs):
    """Réglages d'une rubrique (k : rang, ou 'une') : (interligne, corps en pt, nombre de colonnes)."""
    nc0 = 3 if k == 'une' else (2 if k == ed.get('dern') else 4)
    lh, f, nc = (tuple(ed.get('tw', {}).get(k, ())) + (INTERLIGNE, fs, nc0)[len(ed.get('tw', {}).get(k, ())):])
    return lh, f, nc


def style_rub(ed, k, fs):
    lh, f, nc = reglage(ed, k, fs)
    st = ([f'line-height:{lh}'] if lh != INTERLIGNE else []) + ([f'font-size:{f}pt'] if f != fs else []) \
        + ([f'column-count:{nc}'] if nc != reglage({}, k, fs)[2] and k != ed.get('dern') else [])
    return f' style="{";".join(st)}"' if st else ''


def air(ed, cle, base_mm):
    """Blanc vertical réparti (justification verticale d'une page, voir finaliser()) : marge haute augmentée."""
    x = ed.get('air', {}).get(cle, 0)
    return f' style="margin-top:{base_mm * PX_MM + x:.2f}px"' if x > 0 else ''


def contenu_rub(ed, k, r, incl):
    """Articles et encadré « En bref » d'une rubrique : l'encadré en fin de rubrique, ou en tête (réglage « bd » : la
    colonne de l'encadré est alors la première, et c'est la dernière colonne de texte qui finit plus court)."""
    arts = ''.join(article(it, incl) for it in r['items']); rb = rappels(r['rappels'], incl, dict(ed.get('tw', {}).get('m', ())).get(k, 0))
    return rb + arts if k in ed.get('tw', {}).get('bd', ()) else arts + rb


def titre_rub(k, r, ed=None):
    sous = r['sous'][:1].upper() + r['sous'][1:]
    return (f'<h2 class="rub" id="r{k}"{air(ed or {}, f"r{k}", 3.6)}><span>{T(r["label"])}</span>{T(sous)}</h2>'
            + (f'<p class="rub-c">{T(r["chapo"])}</p>' if r['chapo'] else ''))


def page_html(ed, fs, incl, haut_seul=False):
    """incl : blocs facultatifs retenus (voir blocs()) ; réglages lus dans ed : tw (interligne et corps par rubrique),
    ag_coupe (partage de l'agenda), espace (blanc avant le bas de la dernière page, pour le caler en bas), gap_d (blanc
    entre la dernière rubrique et le crédit). haut_seul : manchette, bandeau, essentiel et sommaire seulement (mesure)."""
    avec_lexique = ('lexique', '') in incl
    m = ed['meta']; d = m['date_iso']
    une, autres = une_autres(ed)
    som = []
    toc = [x for x in m.get('toc', []) if not x.lower().startswith(('à la une', 'agenda'))]
    for k, r in enumerate(autres):   # libellés courts du sommaire de l'édition (meta.json, toc) quand ils correspondent
        som.append(f'<a href="#r{k}">{T(toc[k] if len(toc) == len(autres) else r["label"])}</a>')
        if avec_lexique and ed.get('lex_apres') == k: som.append('<a href="#r-lexique">Lexique</a>')
    if avec_lexique and ed.get('lex_apres') is None: som.append('<a href="#r-lexique">Lexique</a>')
    if ed['agenda']: som.append('<a href="#r-agenda">Agenda</a>')
    h = [f'<header class="mast"><div class="ey">Revue de presse hebdomadaire</div><h1><i>Software</i> <span>Compliance</span></h1>'
         f'<div class="st">L’essentiel de la conformité des logiciels embarqués dans les produits de défense</div></header>'
         f'<div class="band"><span class="n">N° {m["n"]} – {T(m.get("date_long", m["date"]))}</span><span class="r">Revue de presse hebdomadaire, tous les mardis</span></div>'
         f'<div class="top"><div class="ess"><div class="ess-in"><p class="l">{T(ed["chapo"])}</p></div></div><div class="gout"></div>'
         f'<div class="som"><div class="som-in"><div class="k">Dans ce numéro</div>{"".join(som)}</div></div></div>']
    if haut_seul:
        return f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><style>{css(fs, m, ed)}</style></head><body>{"".join(h)}</body></html>'
    if une:
        tu = une['sous'] or une['label']
        h.append(f'<div class="une-k" id="une-k"{air(ed, "une-k", 0)}>À la une</div><h2 class="une-h">{T(tu[:1].upper() + tu[1:])}</h2>')
        if une['chapo']: h.append(f'<p class="une-c">{T(une["chapo"])}</p>')
        h.append(f'<div class="une-cols" id="cu"{style_rub(ed, "une", fs)}>'
                 + ''.join(article(it, incl, une=(j == 0)) for j, it in enumerate(une['items'])) + rappels(une['rappels'], incl) + '</div>')
    dern = len(autres) - 1 if autres and ed['agenda'] else None   # dernière rubrique : entière, à droite de l'agenda
    for k, r in enumerate(autres):
        if k == dern: break
        h.append(titre_rub(k, r, ed) + f'<div class="cols" id="c{k}"{style_rub(ed, k, fs)}>'
                 + contenu_rub(ed, k, r, incl) + '</div>')
        if avec_lexique and ed.get('lex_apres') == k: h.append(lexique(ed))
    droite = ''
    if dern is not None:
        r = autres[dern]
        droite = (f'<div id="dern">{titre_rub(dern, r)}<div class="cols2" id="c{dern}"{style_rub(ed, dern, fs)}>'
                  + contenu_rub(ed, dern, r, incl) + '</div></div>')
    if avec_lexique and ed.get('lex_apres') is None: h.append(lexique(ed))
    if ed.get('espace', 0) > 0: h.append(f'<div style="height:{ed["espace"]:.2f}px"></div>')
    if ed.get('gap_d', 0) > 0: droite += f'<div style="height:{ed["gap_d"]:.2f}px"></div>'
    droite += credit(ed)
    h.append(f'<div class="bas" id="bas"><div class="bas-g" id="bas-g">{agenda(ed["agenda"], d[:4], ed.get("ag_coupe"))}</div>'
             f'<div class="bas-d" id="bas-d">{droite}</div></div>')
    return (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Software Compliance – N° {m["n"]} – {html.escape(m["date"])}</title>'
            f'<style>{css(fs, m, ed)}</style></head><body>{"".join(h)}</body></html>')


def credit(ed):
    m = ed['meta']; d = m['date_iso']
    url = f'{m.get("site", "https://revue.dejeun.es/").rstrip("/")}/{d}/'
    return (f'<div class="colo" id="colo"><div class="colo-t" id="colo-t">'
            f'<div class="mq"><i>Software</i> <span>Compliance</span></div>'
            f'<p>Revue de presse hebdomadaire, N° {m["n"]} du {T(m["date"])}. Rédigée par une intelligence artificielle '
            f'({T(m.get("redaction", "Anthropic Claude"))}) à partir des sources citées ; des erreurs sont possibles. '
            f'Édition en ligne, liens et sources : {html.escape(url)} · <span class="nw">© {d[:4]} Rodolphe Dejeunes</span> · CC BY 4.0</p></div>'
            f'<div class="colo-qr">{qr(url)}</div></div>')


# ---------------------------------------------------------------- rendu et mesures

_FC = []


def rendre(ed, fs, incl):
    from weasyprint import HTML
    from weasyprint.text.fonts import FontConfiguration
    if not _FC: _FC.append(FontConfiguration())   # polices chargées une fois pour tous les rendus (−20 % de temps)
    return HTML(string=page_html(ed, fs, incl), base_url=ROOT).render(font_config=_FC[0])


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
    pts = [x / 4 for x in range(56, 35, -1)]   # 14 → 9 pt, par quart de point ; recherche dichotomique
    lo, hi, best = 0, len(pts) - 1, 9.0
    while lo <= hi:
        mid = (lo + hi) // 2; e, s_ = mesure(pts[mid])
        if e + pad <= s_: best, hi = pts[mid], mid - 1
        else: lo = mid + 1
    ed['ess_pt'] = best
    return best


def taille_credit(ed):
    """Plus grand corps du crédit (de 9 à 5 pt) dont le texte (titre et paragraphe) ne dépasse pas la hauteur du code QR."""
    from weasyprint import HTML
    m = ed['meta']; qr_px = 22 * 96 / 25.4
    def tient(pt):
        ed['colo_pt'] = pt
        h = (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><style>{css(CORPS_MIN, m, ed)}</style></head>'
             f'<body><div class="bas"><div class="bas-g"></div><div class="bas-d">{credit(ed)}</div></div></body></html>')
        pg = HTML(string=h, base_url=ROOT).render().pages[0]
        t = boite(pg, lambda el: el.get('id') == 'colo-t')
        return sum(c.margin_height() for c in t.children) <= qr_px
    pts = [x / 4 for x in range(36, 19, -1)]   # 9 → 5 pt ; recherche dichotomique
    lo, hi, best = 0, len(pts) - 1, 5.0
    while lo <= hi:
        mid = (lo + hi) // 2
        if tient(pts[mid]): best, hi = pts[mid], mid - 1
        else: lo = mid + 1
    ed['colo_pt'] = best
    return best


def coupe_agenda(ed, fs):
    """Partage de l'agenda entre ses deux colonnes qui équilibre leurs hauteurs (mesure de chaque date à la largeur
    d'une colonne) ; à égalité, la colonne de gauche la plus longue."""
    from weasyprint import HTML
    ev = ed['agenda']
    if len(ev) < 2: return len(ev)
    m = ed['meta']
    h = (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><style>{css(fs, m, ed)}</style></head><body>'
         f'<div class="bas"><div class="bas-g">{agenda(ev, m["date_iso"][:4])}</div><div class="bas-d"></div></div></body></html>')
    pg = HTML(string=h, base_url=ROOT).render().pages[0]
    hs = [boite(pg, lambda el, i=e['id']: el.get('id') == f'ag-{i}').margin_height() for e in ev]
    return min(range(1, len(ev)), key=lambda s: (max(sum(hs[:s]), sum(hs[s:])), -s))


PX_MM = 96 / 25.4


def bas_libre(pg):
    """Blanc (px) sous la dernière ligne d'une page."""
    pb = pg._page_box; bas = pb.content_box_y()
    def walk(b):
        nonlocal bas
        for c in getattr(b, 'children', []):
            if type(c).__name__ == 'MarginBox': continue
            if type(c).__name__ in ('LineBox', 'InlineReplacedBox', 'BlockReplacedBox'): bas = max(bas, c.position_y + c.height)
            walk(c)
    walk(pb)
    return pb.content_box_y() + pb.height - bas


def fond_contenu(b):
    """Bas (px) du dernier contenu (ligne, image) d'une boîte."""
    bas = None
    def walk(x):
        nonlocal bas
        for c in getattr(x, 'children', []):
            if type(c).__name__ in ('LineBox', 'InlineReplacedBox', 'BlockReplacedBox'):
                bas = c.position_y + c.height if bas is None else max(bas, c.position_y + c.height)
            else: walk(c)
    walk(b)
    if type(b).__name__ == 'BlockBox' and getattr(b, 'element', None) is not None and b.element.tag == 'aside':
        bas = b.position_y + b.margin_height()
    return bas


def colonnes(b):
    """Colonnes d'un fragment de bloc multicolonne : [(x, haut, bas du contenu)] de gauche à droite (les boîtes de
    colonne ont toute la hauteur du fragment : on mesure le bas de leur contenu)."""
    out = []
    for c in getattr(b, 'children', []):
        kids = [g for g in getattr(c, 'children', [])]
        fond = max((g.position_y + g.margin_height() for g in kids), default=c.position_y)
        out.append((round(c.position_x), c.position_y, fond))
    return sorted(out)


def boites_de(b):
    yield b
    for c in getattr(b, 'children', []): yield from boites_de(c)


def analyser(doc, ed, fs):
    """Défauts de mise en page, du plus grave au plus léger : {'score', 'defauts': [(poids, texte, rubriques)], mesures}.
    Une rubrique (k) qui passe d'une page à la suivante ne doit y laisser ni moins de 5 lignes (« queue », en tête de
    page), ni moins de 3 lignes sous son titre (« tête », en bas de page) ; un « En bref » n'est jamais coupé ni seul de
    sa rubrique sur une page ; aucune colonne vide ou creusée au milieu d'une rubrique ; pas de blanc au bas des pages ;
    dernière page : bas calé en bas de page sans blanc au-dessus, agenda et dernière rubrique de même hauteur."""
    une, autres = une_autres(ed)
    pt = 96 / 72
    D = []
    n = len(doc.pages)
    if n != ed['cible']: D.append((1e6, f'{n} pages au lieu de {ed["cible"]}', [], ed['cible'] - 1))
    frag, page_de = {}, {}   # id -> [(page, boîte)] (boîte extérieure de chaque page)
    for p, pg in enumerate(doc.pages):
        vus = set()
        for b in boites(pg):
            el = getattr(b, 'element', None)
            if el is None or type(b).__name__ in ('LineBox', 'TextBox', 'InlineBox'): continue
            i = el.get('id') or ''
            if not i or i in vus: continue
            if re.fullmatch(r'c\d+|cu|r\d+|rap-.*|bas|bas-g|bas-d|dern|colo|r-agenda|r-lexique|clex|art-.*', i):
                vus.add(i); frag.setdefault(i, []).append((p, b)); page_de.setdefault(i, p)
    cles = (['une'] if une else []) + list(range(len(autres)))
    cid = lambda k: 'cu' if k == 'une' else f'c{k}'
    sur_page = {}   # page -> rubriques présentes
    for k in cles:
        for p, _ in frag.get(cid(k), []): sur_page.setdefault(p, []).append(k)
    for k in cles:
        fr = frag.get(cid(k), [])
        if not fr: continue
        lh, f, nb = reglage(ed, k, fs); ligne = lh * f * pt
        nom = 'la Une' if k == 'une' else f'« {autres[k]["label"]} »'
        prec = [j for j in sur_page.get(fr[-1][0] - 1, []) if j != k] if len(fr) > 1 else []
        if len(fr) > 1:
            p0, b0 = fr[0]; p1, b1 = fr[-1]
            nl = round(b1.height / ligne, 1)
            if nl < 5: D.append((1000 + 50 * (5 - nl), f'{nom} : {nl:g} ligne(s) seule(s) en tête de la page {p1 + 1}', [k] + prec[::-1], p1))
            nl0 = round(b0.height / ligne, 1)
            if nl0 < 3: D.append((800, f'{nom} : {nl0:g} ligne(s) sous son titre en bas de la page {p0 + 1}', [k] + [j for j in sur_page.get(p0, []) if j != k][::-1], p0))
            arts = [i for i, l in frag.items() if i.startswith('art-') and any(q == p1 for q, _ in l)]
            r = (une if k == 'une' else autres[k])
            ids = {f'art-{it["id"]}' for it in r['items']}
            if not ids & set(arts) and r['rappels']: D.append((1200, f'{nom} : « En bref » seul en tête de la page {p1 + 1}', [k] + prec[::-1], p1))
        for p, b in fr:   # colonnes vides ou creusées
            cs = colonnes(b)
            if not cs: continue
            haut = b.position_y + b.height
            if len(cs) < nb and ((p, b) != fr[-1] or b.height > 4 * ligne):
                D.append((700 * (nb - len(cs)), f'{nom} : {nb - len(cs)} colonne(s) vide(s) page {p + 1}', [k] + [j for j in sur_page.get(p, []) if j != k][::-1], p))
            if (p, b) == fr[-1] and len(cs) == nb and b.height > 8 * ligne:   # dernière colonne : pas plus qu'à moitié vide
                vide = haut - cs[-1][2]
                if vide > .65 * b.height and vide > 20 * PX_MM:   # dernière colonne remplie au tiers au moins
                    D.append((150 + vide / 2, f'{nom} : dernière colonne vide aux {100 * vide / b.height:.0f} % page {p + 1}', [k], p))
            for x, y0, y1 in cs[:-1]:
                creux = haut - y1
                if creux > 2.5 * ligne: D.append((300 + creux, f'{nom} : colonne creusée de {creux / PX_MM:.0f} mm page {p + 1}', [k], p))
    if len({p for p, _ in frag.get('clex', [])}) > 1: D.append((1500, 'lexique coupé d\'une page à l\'autre', [], frag['clex'][0][0]))
    for i, l in frag.items():
        if i.startswith('rap-') and len({p for p, _ in l}) > 1: D.append((1200, f'« En bref » {i} coupé', [], min(p for p, _ in l)))
    mes = {'air': {}}
    for p in range(n):   # blanc au bas des pages : réparti au-dessus des titres de la page (AIR_MAX chacun), le reste est un défaut
        haut_p = doc.pages[p]._page_box.content_box_y()
        ecarts = [i for i, l in frag.items() if re.fullmatch(r'r\d+|r-lexique|une-k', i) and i != f'r{ed.get("dern")}'
                  and l[0][0] == p and l[0][1].position_y > haut_p + 5 * PX_MM]   # titres de la page (hors haut de page et bas de la dernière page)
        if p == n - 1:   # dernière page : le blanc au-dessus du bas s'y répartit aussi (voir plus bas)
            mes['air'][p] = ecarts; continue
        bl = bas_libre(doc.pages[p]) / PX_MM
        if bl > 3:
            pris = min(bl - 2, AIR_MAX * len(ecarts)); reste = bl - pris
            mes['air'][p] = (pris * PX_MM, ecarts)
            fin = [k for k in sur_page.get(p, []) if not any(q > p for q, _ in frag.get(cid(k), []))]
            deb = [k for k in sur_page.get(p + 1, []) if page_de.get(cid(k)) == p + 1]
            D.append((2 * pris + (20 * (reste - 3) if reste > 3 else 0), f'blanc de {bl:.0f} mm au bas de la page {p + 1}'
                      + (f' ({pris:.0f} mm répartis au-dessus des titres)' if pris > 0 else ''), fin[::-1] + deb, p))
    pg = doc.pages[-1]; pb = pg._page_box
    bas = boite(pg, lambda el: el.get('id') == 'bas')
    if bas is not None and n == ed['cible']:
        g, dr, colo, de = (boite(pg, lambda el, i=i: el.get('id') == i) for i in ('bas-g', 'bas-d', 'colo', 'dern'))
        h_g = sum(c.margin_height() for c in g.children)
        h_dern = de.margin_height() if de is not None else 0
        h_d = h_dern + colo.margin_height()
        espace = pb.content_box_y() + pb.height - (bas.position_y + bas.margin_height())
        mes.update(h_g=h_g, h_d=h_d, espace=espace)
        e_mm = espace / PX_MM
        dern_p = [k for k in sur_page.get(n - 1, [])]
        if e_mm > 2.5: D.append((15 * (e_mm - 2.5), f'blanc de {e_mm:.0f} mm au-dessus du bas de la dernière page', dern_p[::-1], n - 1))
        ec = (h_g - h_d) / PX_MM   # agenda plus haut que la dernière rubrique et le crédit : blanc au-dessus du crédit
        eb = (h_dern - h_g) / PX_MM   # agenda plus court que la dernière rubrique : blanc sous l'agenda (à côté du crédit, il ne compte pas)
        dk = ed.get('dern')
        if ec > 8: D.append((8 * (ec - 8), f'blanc de {ec:.0f} mm entre la dernière rubrique et le crédit', ([dk] if dk is not None else []) + dern_p[::-1], n - 1))
        if eb > 3: D.append((12 * (eb - 3), f'blanc de {eb:.0f} mm sous l\'agenda', ([dk] if dk is not None else []) + dern_p[::-1], n - 1))
    elif n == ed['cible']: D.append((1e5, 'bas de la dernière page absent', [], n - 1))
    D.sort(key=lambda x: -x[0])
    fins = {k: max(p for p, _ in frag[cid(k)]) for k in cles if frag.get(cid(k))}   # page où finit chaque rubrique
    return {'score': sum(x[0] for x in D), 'defauts': D, 'mesures': mes, 'fins': fins}


# ---------------------------------------------------------------- calage

def blocs(ed):
    """Blocs facultatifs, du plus important au moins important : ajoutés dans cet ordre jusqu'à remplir les pages.
    Nouveautés (hors Une, toujours complète) triées par cote décroissante (impact × urgence × certitude) :
    d'abord leur Résumé (ou le texte de base de leur champ « papier »), puis Impact acquis (ou portions facultatives de
    niveau 1), Impact possible (niveau 2), Contexte (niveau 3)."""
    une, _ = une_autres(ed)
    rubs = ed['rubriques']
    nouv = [it for r in rubs if r is not une for it in r['items'] if it.get('sum')]
    if une: nouv += [it for it in une['items'][1:] if it.get('sum')]
    cote = lambda it: -(lambda c: c[0] * c[1] * c[2] if len(c) == 3 else 0)(it['a'].get('cote') or [])
    nouv = sorted(nouv, key=cote)   # tri stable : à cote égale, ordre de l'édition
    pap = lambda it: bool((it['sum'] or {}).get('papier'))
    niv = lambda it, n: '{{' + str(n) + '|' in it['sum']['papier']
    b = [('papier', it['id']) if pap(it) else ('essentiel', it['id']) for it in nouv if pap(it) or it['sum'].get('essentiel')]
    for n, k in ((1, 'impact_avere'), (2, 'impact_potentiel'), (3, 'contexte')):   # champ « papier » : portions 1, puis 2, puis 3
        b += [(f'papier{n}', it['id']) if pap(it) else (k, it['id']) for it in nouv if (pap(it) and niv(it, n)) or (not pap(it) and it['sum'].get(k))]
    return b   # pas de résumé des rappels : les encadrés « En bref », insécables, restent courts ; le lexique, sous l'agenda, est un appoint (corriger())


def remplissage(doc):
    """Part de la hauteur utile de la dernière page occupée par le contenu (0 à 1)."""
    pb = doc.pages[-1]._page_box
    return min(1.0, 1 - bas_libre(doc.pages[-1]) / pb.height)


def caler(ed):
    """Exactement PAGES pages, corps des paragraphes ≥ CORPS_MIN : si tout le contenu tient au corps minimal, plus grand
    corps qui le fait tenir ; sinon, au corps minimal, le plus grand nombre de blocs facultatifs (blocs()) qui tient.
    Une édition dont le contenu obligatoire dépasse PAGES pages au corps minimal passe à 8 pages (puis 12)."""
    bl = blocs(ed); n = len(bl)
    for cible in (PAGES, 2 * PAGES, 3 * PAGES):
        ed['cible'] = cible
        if len(rendre(ed, CORPS_MIN, set()).pages) > cible: continue
        tout = set(bl)
        if len(rendre(ed, CORPS_MIN, tout).pages) <= cible:   # tout tient : on grossit le corps
            lo, hi, best = 0, len(TAILLES) - 1, CORPS_MIN
            while lo <= hi:
                mid = (lo + hi) // 2
                if len(rendre(ed, TAILLES[mid], tout).pages) <= cible: best, hi = TAILLES[mid], mid - 1
                else: lo = mid + 1
            return (CORPS_MIN if best <= FS_MAX else best), tout   # jusqu'à 8,8 pt, le corps se règle par rubrique (corriger())
        lo, hi, best = 0, n, set()   # au corps minimal, plus grand préfixe de blocs qui tient
        while lo <= hi:
            mid = (lo + hi) // 2; incl = set(bl[:mid])
            if len(rendre(ed, CORPS_MIN, incl).pages) <= cible: best, lo = incl, mid + 1
            else: hi = mid - 1
        return CORPS_MIN, best
    ed['cible'] = -(-len(rendre(ed, CORPS_MIN, set()).pages) // 4) * 4
    return CORPS_MIN, set()


AIR_MAX = 7   # mm de blanc ajoutés au plus au-dessus d'un titre de rubrique (justification verticale)
LH_MAX, FS_MAX, FS_PAS = 1.40, 8.8, 0.1   # ajustements imperceptibles : interligne jusqu'à 1,40, corps jusqu'à 8,8 pt
LIMITE = int(os.environ.get('JOURNAL_LIMITE', '480'))   # secondes consacrées à la correction des défauts


def cle_etat(incl, tw):
    return frozenset(incl), tuple(sorted(tw.items(), key=str))


def _evaluer(arg):
    """Rendu et analyse d'un état (blocs, réglages) : exécuté dans un processus fils (les documents ne se transmettent pas).
    Coût : défauts (analyser()), moins 0,8 par bloc facultatif retenu, plus de petites pénalités pour chaque écart
    d'interligne, de corps ou de nombre de colonnes (à défaut égal, la mise en page la plus régulière)."""
    ed, fs, incl, tw = arg
    ed = dict(ed, tw=tw, espace=0, gap_d=0)
    doc = rendre(ed, fs, set(incl))
    a = analyser(doc, ed, fs)
    ecarts = 8 * tw.get('ag', (0,))[0] + 3 * len(tw.get('bd', ())) + 60 * sum(n for _k, n in tw.get('m', ()))   # brève omise : coûteux
    fsm = max(fs, FS_MAX)
    for k in cles_rub(ed):   # à défaut égal, le corps et l'interligne les plus amples (lisibilité) et la grille de base
        lh, f, nc = reglage(ed, k, fs)
        ecarts += 30 * (LH_MAX - lh) + 30 * (fsm - f) + (8 if nc != reglage({'dern': ed.get('dern')}, k, fs)[2] else 0)
    a['ecarts'] = ecarts
    return a['score'] - 0.8 * len(incl) + ecarts, a


def cles_rub(ed):
    une, autres = une_autres(ed)
    return (['une'] if une else []) + list(range(len(autres)))


def mouvements(ed, fs, incl, tw, a, bl):
    """États voisins pour corriger les deux défauts les plus graves : pour chaque rubrique en cause, interligne
    (1,30 à 1,40) et corps (jusqu'à 8,8 pt) ajustés, trois ou quatre colonnes, un ou deux blocs facultatifs ajoutés ou
    retirés (selon l'ordre d'importance) ; corps de l'agenda."""
    une, autres = une_autres(ed)
    rub_de = {}
    for k, r in ([('une', une)] if une else []) + list(enumerate(autres)):
        for it in r['items']: rub_de[it['id']] = k
    out, vus = [], {cle_etat(incl, tw)}
    def ajouter(c):
        if cle_etat(*c) not in vus: vus.add(cle_etat(*c)); out.append(c)
    rubs = []
    for _p, _t, ks, _pg in a['defauts'][:2]:
        for k in ks:
            if k not in rubs: rubs.append(k)
    if any('dernière page' in t or 'agenda' in t or 'crédit' in t for _p, t, _, _pg in a['defauts'][:3]):   # corps de l'agenda
        g = tw.get('ag', (0,))[0]
        for g2 in (g - .25, g + .25):
            if -1e-9 <= g2 <= .75 + 1e-9: ajouter((incl, {**{k: v for k, v in tw.items() if k != 'ag'}, **({'ag': (g2,)} if g2 > 1e-9 else {})}))
    for k in rubs[:3]:
        lh, f, nc = reglage(dict(ed, tw=tw), k, fs)
        def avec(lh2=lh, f2=f, nc2=nc):
            t = dict(tw); t[k] = (round(lh2, 2), round(f2, 2), nc2)
            if t[k] == reglage({'dern': ed.get('dern')}, k, fs): t.pop(k)
            return t
        if lh + .02 <= LH_MAX + 1e-9: ajouter((incl, avec(lh2=lh + .02)))
        if lh + .05 <= LH_MAX + 1e-9: ajouter((incl, avec(lh2=lh + .05)))
        if lh - .02 >= INTERLIGNE - 1e-9: ajouter((incl, avec(lh2=lh - .02)))
        if f + FS_PAS <= max(fs, FS_MAX) + 1e-9: ajouter((incl, avec(f2=f + FS_PAS)))
        if f - FS_PAS >= fs - 1e-9: ajouter((incl, avec(f2=f - FS_PAS)))
        if k != 'une' and k != ed.get('dern'): ajouter((incl, avec(nc2=3 if nc == 4 else 4)))
        nb_r = len((une if k == 'une' else autres[k])['rappels'])
        m = dict(tw.get('m', ()))
        if k != 'une' and nb_r - m.get(k, 0) > 2:   # une brève de moins (deux au moins restent)
            m2 = dict(m); m2[k] = m.get(k, 0) + 1
            ajouter((incl, {**{x: v for x, v in tw.items() if x != 'm'}, 'm': tuple(sorted(m2.items()))}))
        if k != 'une':   # encadré « En bref » en tête ou en fin de rubrique
            bd = set(tw.get('bd', ())) ^ {k}
            ajouter((incl, {**{x: v for x, v in tw.items() if x != 'bd'}, **({'bd': tuple(sorted(bd))} if bd else {})}))
        a_ajouter = [b for b in bl if rub_de.get(b[1]) == k and b not in incl]
        a_retirer = [b for b in bl if rub_de.get(b[1]) == k and b in incl]
        if a_ajouter: ajouter((incl | {a_ajouter[0]}, tw))
        if len(a_ajouter) > 1: ajouter((incl | set(a_ajouter[:2]), tw))
        if a_retirer: ajouter((incl - {a_retirer[-1]}, tw))
        if len(a_retirer) > 1: ajouter((incl - set(a_retirer[-2:]), tw))
    return out


def combler(base, fs, incl, tw, s, a, carte):
    """Blanc qui subsiste au bas d'une page (la rubrique suivante ne peut pas y commencer) : le lexique des sigles s'y
    place, réduit aux sigles les plus cités pour tenir dans le blanc (README, § 18)."""
    pages = [(d[0], d[3]) for d in a['defauts'] if d[1].startswith('blanc de') and 'au bas de la page' in d[1] and d[0] >= 40]
    if not pages or not base.get('sigles'): return incl, base, s, a
    p = max(pages)[1]
    fins = a['fins']; ks = [k for k in fins if k != 'une' and fins[k] == p]
    if not ks: return incl, base, s, a
    k = max(ks)
    lx = ('lexique', '')
    ns = list(range(len(base["sigles"]), 3, -1))
    essais = [(dict(base, lex_apres=k, lex_n=n), n) for n in ns]
    res = carte(_evaluer, [(b, fs, frozenset(incl | {lx}), tw) for b, _n in essais])
    j = min(range(len(res)), key=lambda i: res[i][0])
    if res[j][0] < s - 20:
        print(f'  lexique au bas de la page {p + 1} ({essais[j][1]} sigles) : score {res[j][0]:.0f}', file=sys.stderr, flush=True)
        return incl | {lx}, essais[j][0], res[j][0], res[j][1]
    return incl, base, s, a


def corriger(ed, fs, incl):
    """Correction des défauts (analyser()) : d'abord une construction rubrique par rubrique, dans l'ordre de lecture
    (pour chacune, interligne et corps serrés, moyens ou amples, trois ou quatre colonnes, « En bref » en fin ou en tête ;
    on garde le réglage qui donne le moins de défauts jusqu'à la page où elle finit, les rubriques suivantes restant au
    repos, serrées, pour ne pas fermer de possibilité), puis une recherche locale : tant que des défauts subsistent (et dans la limite de temps), l'état voisin
    le meilleur (mouvements()) remplace l'état courant s'il en diminue le coût. Les rendus se font en parallèle."""
    import multiprocessing as mp, time
    t0 = time.time()
    bl = blocs(ed)
    base = {k: v for k, v in ed.items() if k not in ('tw',)}
    try: pool = mp.get_context('spawn').Pool(min(4, os.cpu_count() or 1)) if (os.cpu_count() or 1) > 1 else None   # « fork » se bloque (polices)
    except Exception: pool = None
    carte = (lambda f, xs: pool.map(f, xs)) if pool else (lambda f, xs: [f(x) for x in xs])
    hist = []
    try:
        ks = cles_rub(ed)
        dern = ed.get('dern')
        defaut = lambda k: reglage({'dern': dern}, k, fs)
        fsm = max(fs, FS_MAX)
        niveaux = sorted({(INTERLIGNE, fs), (1.35, round(min(fs + .15, fsm), 2)), (LH_MAX, fsm)})
        tw = {}
        for k in [k for k in ks if k != dern]:   # construction rubrique par rubrique, dans l'ordre de lecture
            opts = []
            for lh, f in niveaux:
                for nc in ([defaut(k)[2]] if k == 'une' else [4, 3]):
                    for deb in ([False] if k == 'une' else [False, True]):
                        t = {x: v for x, v in tw.items() if x != 'bd'}
                        if (lh, f, nc) != defaut(k): t[k] = (lh, f, nc)
                        bd = set(tw.get('bd', ())) | ({k} if deb else set())
                        if bd: t['bd'] = tuple(sorted(bd))
                        opts.append(t)
            res = carte(_evaluer, [(base, fs, frozenset(incl), t) for t in opts])
            P = max(a_['fins'].get(k, 0) for _, a_ in res)   # pages jusqu'à la fin de la rubrique : les suivantes, au repos, ne comptent pas encore
            part = [sum(d[0] for d in a_['defauts'] if d[3] <= P) + a_['ecarts'] for _, a_ in res]
            j_ = min(range(len(res)), key=lambda i: part[i])
            tw = opts[j_]; s, a = res[j_]
            print(f'  [{time.time() - t0:.0f} s] rubrique {k} : {tw.get(k, "repos")}{" encadré en tête" if k in tw.get("bd", ()) else ""} ; '
                  f'jusqu\'à la page {P + 1} : {"; ".join(d[1] for d in a["defauts"] if d[3] <= P) or "aucun défaut"}', file=sys.stderr, flush=True)
        if not [k for k in ks if k != dern]: s, a = _evaluer((base, fs, frozenset(incl), tw))
        incl, base, s, a = combler(base, fs, incl, tw, s, a, carte)
        hist.append((round(s, 1), [d[1] for d in a['defauts']]))
        print(f'  [{time.time() - t0:.0f} s, construction] score {s:.0f} : {"; ".join(d[1] for d in a["defauts"][:3])}', file=sys.stderr, flush=True)
        while a['defauts'] and time.time() - t0 < LIMITE:
            cands = mouvements(ed, fs, incl, tw, a, bl)
            if not cands: break
            res = carte(_evaluer, [(base, fs, frozenset(c[0]), c[1]) for c in cands])
            j = min(range(len(res)), key=lambda i: res[i][0])
            if res[j][0] >= s - .5: break
            s, a = res[j]; incl, tw = set(cands[j][0]), cands[j][1]
            hist.append((round(s, 1), [d[1] for d in a['defauts']]))
            print(f'  [{time.time() - t0:.0f} s, {len(cands)} essais] score {s:.0f} : {"; ".join(d[1] for d in a["defauts"][:3])}', file=sys.stderr, flush=True)
    finally:
        if pool: pool.close(); pool.join()
    return incl, tw, a, hist, base


def finaliser(ed, fs, incl, a):
    """Bas de la dernière page calé en bas : blanc avant le bas, et blanc entre la dernière rubrique et le crédit
    pour coller le crédit au bas de la page."""
    mes = a.get('mesures') or {}
    ed['gap_d'] = max(0.0, mes.get('h_g', 0) - mes.get('h_d', 0) - 1)
    esp = max(0.0, mes.get('espace', 0) - 1.5)
    ed['air'] = {}
    for p, v in (mes.get('air') or {}).items():
        if isinstance(v, list):   # dernière page : blanc au-dessus du bas partagé entre ses titres et le bas
            parts = len(v) + 1; x = min(esp / parts, AIR_MAX * PX_MM)
            for i in v: ed['air'][i] = x
            esp -= x * len(v)
        else:
            pris, ecarts = v
            for i in ecarts: ed['air'][i] = pris / len(ecarts)
    ed['espace'] = esp
    for f in (1, .8, .5, 0):   # garde-fou : rien ne doit changer de page
        ed['air'] = {i: x * f for i, x in ed['air'].items()}; ed['espace'] = esp * (f if f < 1 else 1)
        doc = rendre(ed, fs, incl)
        if len(doc.pages) == ed['cible'] and analyser(doc, dict(ed, espace=0, air={}), fs)['score'] <= a['score'] + 50: return doc
    return doc


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
    et au moins 97 % des mots du HTML (les césures en ajoutent), sinon il n'est pas publié."""
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
              os.path.join(TOOLS, 'commun.py'), os.path.join(TOOLS, 'glossary.py'), os.path.join(TOOLS, 'en-tete.webp')]:
        hsh.update(open(f, 'rb').read())
    return hsh.hexdigest()[:16]


def produire(d, sortie=None):
    """Produit les deux PDF de l'édition d dans sortie (défaut build/d) ; cache dans build/pdf-cache. Renvoie un résumé ;
    sa clé « defauts » liste les défauts de mise en page qui subsistent (la page de l'édition ne propose alors pas le PDF)."""
    sortie = sortie or os.path.join(BUILD, d)
    os.makedirs(sortie, exist_ok=True)
    cache = os.path.join(BUILD, 'pdf-cache'); os.makedirs(cache, exist_ok=True)
    e = empreinte(d)
    a4, a3 = os.path.join(sortie, f'revue-{d}.pdf'), os.path.join(sortie, f'revue-{d}-a3.pdf')
    c4, c3, cj = (os.path.join(cache, f'{d}-{e}{s}') for s in ('.pdf', '-a3.pdf', '.json'))
    if os.path.exists(c4) and os.path.exists(c3) and os.path.exists(cj):
        shutil.copy(c4, a4); shutil.copy(c3, a3); return json.load(open(cj))
    v = os.path.join(ROOT, 'veille', 'imprimable', d)   # version déjà produite (répétition, ou production locale) et versée au dépôt
    vj, v4 = os.path.join(v, 'imprimable.json'), os.path.join(v, f'revue-{d}.pdf')
    if os.path.exists(vj) and os.path.exists(v4) and json.load(open(vj, encoding='utf-8')).get('empreinte') == e:
        shutil.copy(v4, a4); imposer(a4, a3)
        shutil.copy(a4, c4); shutil.copy(a3, c3); shutil.copy(vj, cj)
        return json.load(open(vj, encoding='utf-8'))
    import time
    t0 = time.time()
    ed = lire(d)
    _, autres = une_autres(ed)
    ed['dern'] = len(autres) - 1 if autres and ed['agenda'] else None
    taille_essentiel(ed); taille_credit(ed)
    ed['ag_coupe'] = coupe_agenda(ed, CORPS_MIN)
    fs, incl = caler(ed)
    if fs != CORPS_MIN: ed['ag_coupe'] = coupe_agenda(ed, fs)
    t1 = time.time()
    ed['sigles'] = sigles(page_html(ed, fs, set(blocs(ed))))
    incl, tw, a, hist, base = corriger(ed, fs, incl)
    ed.update({k: base[k] for k in ('lex_apres', 'lex_n') if k in base})
    ed['tw'] = tw
    c2 = coupe_agenda(ed, fs)   # partage de l'agenda recalculé à son corps définitif
    if c2 != ed['ag_coupe']:
        ed['ag_coupe'] = c2; a = analyser(rendre(dict(ed, espace=0, gap_d=0), fs, incl), dict(ed, espace=0, gap_d=0), fs)
    doc = finaliser(ed, fs, incl, a)
    fin = analyser(doc, dict(ed, espace=0), fs)   # contrôle du document définitif
    doc.write_pdf(a4)
    complet(page_html(ed, fs, incl), a4)
    imposer(a4, a3)
    bl = blocs(ed)
    defauts = [t for p, t, _, _pg in fin['defauts'] if p >= 50]   # défauts francs ; les blancs de moins de quelques mm sont tolérés
    for s_, ds in hist: print(f'  score {s_} : {"; ".join(ds[:4]) or "aucun défaut"}', file=sys.stderr)
    print(f'  calage {t1 - t0:.0f} s, corrections {time.time() - t1:.0f} s ; réglages {tw} ; espace {ed["espace"] / PX_MM:.1f} mm, '
          f'crédit décalé de {ed["gap_d"] / PX_MM:.1f} mm ; essentiel {ed["ess_pt"]} pt ; crédit {ed["colo_pt"]} pt', file=sys.stderr)
    info = {'edition': d, 'pages': len(doc.pages), 'cahier': ed['cible'], 'corps_pt': fs, 'blocs': f'{len(set(incl) & set(bl))}/{len(bl)}',
            'remplissage': round(remplissage(doc), 2), 'lexique': ('lexique', '') in incl, 'defauts': defauts,
            'etat': {'incl': sorted(map(list, incl)), 'reglages': {str(k): v for k, v in tw.items()}, 'ag_coupe': ed['ag_coupe'],
                     'espace_mm': round(ed['espace'] / PX_MM, 1), 'gap_d_mm': round(ed['gap_d'] / PX_MM, 1),
                     'ess_pt': ed['ess_pt'], 'colo_pt': ed['colo_pt'], 'lex_apres': ed.get('lex_apres'), 'lex_n': ed.get('lex_n')}, 'empreinte': e}
    shutil.copy(a4, c4); shutil.copy(a3, c3); json.dump(info, open(cj, 'w'), ensure_ascii=False)
    os.makedirs(v, exist_ok=True); shutil.copy(a4, v4); json.dump(info, open(vj, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return info


def main():
    eds = sys.argv[1:] or sorted(x for x in os.listdir(CONTENT) if re.fullmatch(r'\d{4}-\d{2}-\d{2}', x))[-1:]
    for d in eds:
        i = produire(d)
        print(f"{d} : {i['pages']} pages (cahier de {i['cahier']}), corps {i['corps_pt']} pt, blocs facultatifs {i['blocs']}, "
              f"dernière page remplie à {round(100 * i['remplissage'])} % ; défauts : {'; '.join(i.get('defauts') or []) or 'aucun'}")


if __name__ == '__main__':
    main()
