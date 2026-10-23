#!/usr/bin/env python3
"""Version imprimable d'une édition : quatre pages A4 composées comme un journal, puis imposées sur une feuille A3
recto-verso pliée en deux (README, § 18).

Composition (moteur maison, WeasyPrint pour les mesures et le rendu) : chaque paragraphe est mesuré ligne à ligne à la
largeur d'une colonne ; les colonnes sont composées par le programme, chacune positionnée sur la page avec sa hauteur
exacte : toutes les rubriques sur quatre colonnes (la Une sur trois), colonnes de même hauteur, encadré « En bref » en
fin de rubrique, calé en bas de sa dernière colonne, même marge basse sur toutes les pages ; dernière page : agenda ancré
en bas à gauche (deux colonnes égales), crédit en bas à droite, glossaire en dernier, qui enveloppe l'agenda. Une
recherche en faisceau choisit, rubrique par rubrique, corps (8,5 à 8,8 pt), interligne (1,30 à 1,40), portions
facultatives et brèves (d'abord celles que l'agenda répète), et l'étendue du glossaire.

Usage : python3 tools/journal.py [AAAA-MM-JJ …]   (défaut : dernière édition)
        python3 tools/journal.py --jauge [AAAA-MM-JJ]   (rédaction : texte à ajouter aux champs « papier » pour remplir les pages)
Écrit build/AAAA-MM-JJ/revue-AAAA-MM-JJ.pdf (A4, 4 pages) et revue-AAAA-MM-JJ-a3.pdf (A3 imposé : recto 4|1, verso 2|3).
Dépendances : weasyprint, pypdf ; qrcode (code QR du crédit).
"""
import base64, glob, hashlib, html, json, math, os, re, shutil, sys

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
VERSION = 'journal-39'   # à changer quand la mise en page change (invalide le cache)


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


def papier(sm, iid, incl, tout=False, niv=3):
    """Paragraphes du champ « papier » (README, § 6) : portions facultatives gardées selon le calage (tout : toutes
    celles de niveau niv ou moins, pour la Une)."""
    out = []
    for par in re.split(r'\n\s*\n', sm['papier'].strip()):
        par = FACULTATIF.sub(lambda m: m[2] if (tout and int(m[1]) <= niv) or (f'papier{m[1]}', iid) in incl else '', par)
        par = re.sub(r'\s{2,}', ' ', par).strip()
        if par: out.append(par)
    return out


def morceaux(it, incl, une=False, une_niv=3):
    """Article en morceaux successifs : titre et texte, puis chaque paragraphe retenu (champ « papier » s'il existe,
    sinon paragraphes de la synthèse)."""
    t, _ = corps(it['segs'])
    sm = it.get('sum') or {}
    tit = sm.get('titre')
    m = [(f'<h3 class="hl">{T(tit)}</h3>' if tit and not une else '') + f'<p class="txt">{accroche(t)}</p>']
    if sm.get('papier'):
        if une or ('papier', it['id']) in incl: m += [f'<p class="sp">{T(x)}</p>' for x in papier(sm, it['id'], incl, une, une_niv)]
        return m
    for k in ('contexte', 'essentiel', 'impact_avere', 'impact_potentiel'):
        if sm.get(k) and (une or (k, it['id']) in incl): m.append(f'<p class="sp">{T(sm[k])}</p>')
    return m


def titre_breve(h):
    """Brève : son titre (le texte avant le premier deux-points) en sans-serif semi-gras."""
    m = re.search('\u00a0:', h)
    if not m or m.start() > 90 or h[:m.start()].count('<') != h[:m.start()].count('>'): return h
    return f'<span class="rap-k">{h[:m.start()]}</span>{h[m.start():]}'


def rappels_html(rs, incl):
    """Encadré « En bref » (rappels retenus) : une seule colonne, en fin de rubrique, jamais coupé."""
    if not rs: return ''
    li = []
    for r in rs:
        t, _ = corps(r['segs'])
        res = (r.get('sum') or {}).get('essentiel')
        li.append(f'<li><p>{titre_breve(accroche(t))}</p>' + (f'<p class="rap-s">{T(res)}</p>' if res and ('essentiel', r['id']) in incl else '') + '</li>')
    return f'<aside class="rap" id="rap-{rs[0]["id"]}"><p class="rap-t">En bref</p><ul>{"".join(li)}</ul></aside>'


MOTS = re.compile(r'\w{4,}')


def doublon_agenda(r, agenda):
    """Brève qui répète une échéance de l'agenda (même texte de loi « 2024/2853 », ou même date et mêmes mots) :
    elle peut être omise de l'encadré imprimé, l'agenda la donne déjà."""
    t = corps(r['segs'])[0].lower()
    lois = set(re.findall(r'\b\d{4}/\d{3,4}\b', t))
    dates = {(j, m) for j, m in re.findall(r'\b(1er|\d{1,2})\s+(' + '|'.join(MOIS) + r')\b', t)}
    mots = set(MOTS.findall(t))
    for e in agenda:
        s = ' '.join([e['date'], e['quoi'], e.get('detail') or '']).lower()
        if lois & set(re.findall(r'\b\d{4}/\d{3,4}\b', s)): return True
        ds = {(j, m) for j, m in re.findall(r'\b(1er|\d{1,2})\s+(' + '|'.join(MOIS) + r')\b', s)}
        if dates & ds and mots and len(mots & set(MOTS.findall(s))) >= .3 * len(mots): return True
    return False


def ordre_omission(rs, agenda):
    """Ordre dans lequel des brèves peuvent être omises : d'abord celles que l'agenda répète, puis les dernières ;
    deux brèves au moins restent. Renvoie (indices dans l'ordre d'omission, nombre de doublons)."""
    dup = [i for i, r in enumerate(rs) if doublon_agenda(r, agenda)]
    reste = [i for i in reversed(range(len(rs))) if i not in dup]
    return dup + reste, len(dup)


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


def entree_agenda(e, annee, pt, marge=0.0, extra=0.0):
    """Une échéance : case de date, catégorie en titre (coupée entre les mots seulement), puis le détail s'il existe
    (l'accroche, redondante, est omise), sinon l'accroche."""
    txt = e.get('detail') or e['quoi']
    return (f'<div class="ag-e" id="ag-{e["id"]}" style="margin-top:{marge:.2f}px"><div class="ag-dt">{pastille(e["date"], annee)}</div><div>'
            f'<p class="ag-th" style="font-size:{round(6.8 * pt / 8, 2)}pt">{T(e["theme"])}</p><p class="ag-q" style="font-size:{pt}pt;line-height:{1.25 * pt * 96 / 72 + extra:.3f}px">{T(txt)}</p></div></div>')


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


def texte_anterieur(d):
    """Texte de toutes les éditions antérieures à d (éléments et synthèses), pour savoir si un terme y figurait déjà."""
    out = []
    def walk(x):
        if isinstance(x, str): out.append(x)
        elif isinstance(x, dict):
            for k, v in x.items():
                if k not in ('href', 'type', 'k', 'attrs'): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    for p_ in sorted(glob.glob(os.path.join(CONTENT, '*', 'blocks.json'))):
        if os.path.basename(os.path.dirname(p_)) < d: walk(json.load(open(p_, encoding='utf-8')))
    return ' '.join(out)


def sigles(texte_html, avant=''):
    """Sigles et termes du glossaire cités dans le texte : [(nom, définition courte, nombre de citations, définition
    complète, nouveau)] ; nouveau : le terme n'apparaissait dans aucune édition antérieure (avant : leur texte). Pour une
    entrée nommée en toutes lettres mais repérée par son sigle (« CRA » : Cyber Resilience Act), le sigle et son nom."""
    plain = re.sub(r'<[^>]+>', ' ', texte_html)
    neuf = lambda rx: not re.search(r'(?<![\w-])(' + rx + r')(?![\w])', avant)
    vus, h = set(), []
    sig = lambda x: re.fullmatch(r'[A-Z][A-Z0-9-]{1,9}', x)
    for rx, lab, de, _u in G:
        if not sig(rx):   # terme nommé en toutes lettres (outil, organisation, texte)
            n = len(re.findall(r'(?<![\w-])(' + rx + r')(?![\w])', plain))
            if n and lab not in vus: vus.add(lab); h.append((lab, court(de), n, sans_ital(de).strip(), neuf(rx)))
            continue
        nom, dfn = (lab, court(de)) if sig(lab) else (rx, re.sub(r'\s*\(' + rx + r'\)', '', lab))   # « Norme européenne (EN) »
        if re.search(r'\b' + rx + r'\b', dfn) and not sig(lab): dfn = court(de)   # « Licence OTN » : sa définition
        if nom in vus: continue
        n = len(re.findall(r'(?<![\w-])(' + rx + r')(?![\w])', plain))
        long_ = sans_ital(de).strip()
        if not sig(lab) and not long_.lower().startswith(dfn.lower()[:12]): long_ = f'{dfn}. {long_}'
        if n: vus.add(nom); h.append((nom, dfn, n, long_, neuf(rx)))
    return h


def qr(url):
    """Code QR de l'édition en ligne : les trois « oreilles » (repères de position) en orange, le reste en bleu nuit."""
    try:
        import qrcode
        q = qrcode.QRCode(border=0, error_correction=qrcode.constants.ERROR_CORRECT_M); q.add_data(url); q.make(fit=True)
        mat = q.get_matrix(); n = len(mat)
        oreille = lambda y, x: (y < 7 and x < 7) or (y < 7 and x >= n - 7) or (y >= n - 7 and x < 7)
        chemins = {True: [], False: []}
        for y, ligne in enumerate(mat):
            for x, v in enumerate(ligne):
                if v: chemins[oreille(y, x)].append(f'M{x} {y}h1v1h-1z')
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" shape-rendering="crispEdges">'
               f'<path fill="{NAVY}" d="{"".join(chemins[False])}"/><path fill="{ACC}" d="{"".join(chemins[True])}"/></svg>')
        return f'<img class="qr" src="data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}" alt="">'
    except Exception:
        return ''


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



# ---------------------------------------------------------------- géométrie (px CSS, 96 par pouce)

MM, PT = 96 / 25.4, 96 / 72
LARG, HAUT = 191 * MM, 273 * MM   # boîte de contenu de la page A4 (marges 11, 9,5, 13, 9,5 mm)
GOUT = 4 * MM
W4 = (LARG - 3 * GOUT) / 4   # colonne du journal (quatre colonnes)
W3 = (LARG - 2 * GOUT) / 3   # colonne de la Une (trois colonnes)
W2 = 2 * W4 + GOUT           # deux colonnes : agenda, crédit
TITRE_PT = 11.6              # titres d'article
CREDIT_PT = 7.0   # crédit (taille fixe : cinq lignes à côté du code QR)
# pied de page « Software Compliance – date » (7,5 pt) sur la ligne de base du folio (9 pt, 0,6 mm sous le haut de la marge)
PIED_PAD = .6 * 72 / 25.4 + 1.024 * (9 - 7.5)
MAST_BAS = 9 * 96 / 25.4 - 12 * 96 / 72   # blanc sous la manchette, au-dessus du bandeau (remonté deux fois de 6 pt)
# crédit abaissé (décalage relatif, sans effet sur la composition) pour que sa dernière ligne ait la même ligne de base que
# le folio : bas du contenu à 284 mm, folio en tête de la marge (285 mm) + 0,6 mm, Source Sans 3 (ascendante 1,024 em,
# descendante 0,4 em), crédit en interligne 1,3
DECAL_CREDIT = 1.6 * 96 / 25.4 + (1.024 * 9 + .4 * CREDIT_PT + (1.3 - 1.424) / 2 * CREDIT_PT) * 96 / 72
MONO_H = 21 * 96 / 25.4      # monogramme de la manchette
MONO_X = 2.17 * 96 / 25.4               # décalage à droite : sa marge au bord gauche de la feuille égale sa marge au bord haut
FS_LIST = (8.5, 8.6, 8.7, 8.8)                  # corps des paragraphes, réglé par rubrique
LH_LIST = (1.30, 1.32, 1.34, 1.36, 1.38)  # interligne de base, réglé par rubrique
LH_MAX = 1.40   # interligne maximal, justification verticale comprise
REGLAGE_LIBRE = int(os.environ.get("JOURNAL_LIBRE", "1"))   # 1 : corps et interligne réglés rubrique par rubrique
AG_PT = (8.0, 8.25, 8.5, 8.75, 9.0, 9.25)      # corps de l'agenda
ECART = {'ill': 1.6 * MM, 'titre': 0.0, 'par': 0.0, 'art': 4.4 * MM, 'bref': 2 * MM, 'lex': .8 * MM}   # blancs avant un élément (voir blanc())
EXTENSIBLE = {'par', 'art', 'bref', 'lex'}       # blancs que la justification verticale peut agrandir
G_APRES_UNE = 3 * 96 / 25.4   # blanc supplémentaire entre la Une et la rubrique suivante (filet de rubrique moins serré)
G_RUB, G_CHAPO, G_BAS, G_AG = 4.2 * MM, 2.6 * MM, 4.2 * MM, 1.8 * MM
MIN_QUEUE = 4   # lignes au moins d'une fin de rubrique en tête de page
MIN_TETE = 6    # lignes au moins d’un début de rubrique en bas de page


def css(meta, ed):
    ess_pt, colo_pt = ed.get('ess_pt', 11.0), ed.get('colo_pt', 7.6)
    pied = f'Software Compliance – {meta["date"]}'
    entete = os.path.join(TOOLS, 'en-tete.webp')
    return polices() + f'''
@page {{ size:A4; margin:11mm 9.5mm 12mm 9.5mm }}   /* contenu composé sur 273 mm : 1 mm de garde sous la dernière ligne */
@page :right {{ @bottom-left {{ content:"{pied}"; font:400 7.5pt {SANS}; color:#6b7280; vertical-align:top; padding-top:{PIED_PAD:.2f}pt }}
               @bottom-right {{ content:counter(page); font:700 9pt {SANS}; color:{NAVY}; vertical-align:top; padding-top:.6mm }} }}
@page :left {{ @bottom-left {{ content:counter(page); font:700 9pt {SANS}; color:{NAVY}; vertical-align:top; padding-top:.6mm }}
              @bottom-right {{ content:"{pied}"; font:400 7.5pt {SANS}; color:#6b7280; vertical-align:top; padding-top:{PIED_PAD:.2f}pt }} }}
@page :first {{ @bottom-left {{ content:none }} @bottom-right {{ content:none }} }}
@page derniere {{ @bottom-right {{ content:none }} }}   /* dernière page : le crédit dit déjà le titre et la date ; folio seul */
.pg.dern {{ page:derniere }}
html {{ font-family:{SERIF}; font-size:8.5pt; line-height:1.3; color:#1b1f27; hyphens:auto; -webkit-hyphens:auto; orphans:1; widows:1 }}
body {{ margin:0 }}
p, h1, h2, h3, ul {{ margin:0 }}
i {{ font-style:italic }}
sup {{ font-size:70%; line-height:0 }}
.kw {{ color:{BRIQUE} }} .nh {{ hyphens:manual }}
.pg {{ position:relative; height:{HAUT - .5:.2f}px; break-after:page; overflow:visible }} .pg:last-child {{ break-after:auto }}
.abs {{ position:absolute }}
/* manchette : dessin d'en-tête du site (graphe, certificats, circuits) estompé en haut à droite, à 4 mm du coin de la
   feuille (marges des imprimantes), sous le titre et sous le bandeau */
.mast {{ position:relative; text-align:center; padding-bottom:{MAST_BAS:.2f}px }}   /* bandeau remonté de 12 pt */
.mast::before {{ content:""; position:absolute; right:-5.5mm; top:-7mm; width:114mm; height:36.1mm; background:url('file://{entete}') no-repeat right top / auto 100%; opacity:.7; z-index:0 }}
.mast > * {{ position:relative; z-index:1 }}
.mast .ey {{ font:600 7.7pt {SANS}; letter-spacing:.3em; text-transform:uppercase; color:{ACC}; margin-bottom:.6mm }}
.mast h1 {{ margin:0; font:400 38pt/1 {SERIF}; color:{NAVY}; letter-spacing:-.01em }}
.mast .mono {{ position:absolute; left:{MONO_X:.2f}px; top:{(38 * PT - MONO_H) / 2:.2f}px; height:{MONO_H:.2f}px; width:auto; opacity:.14 }}   /* monogramme « SC », sans fond, estompé, centré sur la ligne du titre */
.mast h1 i {{ color:{ACC} }} .mast h1 span {{ font:600 36pt/1 {SANS}; letter-spacing:-.03em }}
.mast .st {{ margin-top:2mm; font:italic 9.5pt {SERIF}; color:#374151 }}
/* bandeau « onglet » */
.band {{ position:relative; z-index:1; display:flex; justify-content:space-between; align-items:flex-end; border-bottom:.8pt solid {NAVY}; color:{NAVY}; font:600 8.75pt/1.25 {SANS}; letter-spacing:.04em; margin-bottom:4.5mm }}
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
.une-k {{ font:700 8.2pt {SANS}; letter-spacing:.18em; text-transform:uppercase; color:{ACC}; margin-bottom:1mm }}
.une-c {{ font:11pt/1.35 {SERIF}; color:#374151; padding-bottom:2.6mm; hyphens:manual }}
/* titres de rubrique */
h2.rub {{ padding-top:1.4mm; border-top:1.6pt solid {NAVY}; font:700 13pt/1.15 {SERIF}; color:{NAVY}; text-align:left; hyphens:manual }}
h2.rub span {{ display:inline-block; margin-right:2mm; padding:.4mm 1.6mm; background:{ACC}; color:#fff; font:700 7.9pt/1.3 {SANS}; letter-spacing:.14em; text-transform:uppercase; vertical-align:2pt }}
.rub-c {{ font:italic 9.6pt/1.32 {SERIF}; color:#4b5563; margin-top:1.4mm; text-align:left; hyphens:manual }}
/* colonnes */
.col {{ text-align:justify }}
.col > * {{ margin:0 }}
.regle {{ position:absolute; width:0; border-left:.4pt solid #d8d2c6 }}
h3.hl {{ font:700 {TITRE_PT}pt/1.14 {SANS}; color:{NAVY}; text-align:left; hyphens:manual }}
p.sp {{ text-indent:1em }} p.cont {{ text-indent:0 }} p.coupe {{ text-align-last:justify }}
.filet {{ border-top:.4pt solid #d8d2c6 }}
/* « En bref » : encadré d'une colonne, en fin de rubrique */
.rap {{ padding:1.6mm 2mm 1.2mm; border-top:.8pt solid {ACC}; background:#faf6ef; font-size:{PETIT_MIN}pt; line-height:1.27; text-align:left; hyphens:auto }}
.rap-t {{ font:700 .82em {SANS}; letter-spacing:.18em; text-transform:uppercase; color:{ACC}; margin-bottom:.8mm }}
.rap ul {{ padding:0; list-style:none }} .rap li {{ margin:0 0 1.1mm }} .rap li:last-child {{ margin-bottom:0 }}
.rap li + li {{ padding-top:1.1mm; border-top:.4pt solid #e6dccb }}
.rap-s {{ margin-top:.4mm; color:#374151 }}
.rap-k {{ font-family:{SANS}; font-weight:600; font-size:1.02em; color:{NAVY} }}
/* agenda */
.ag-e {{ display:table; width:100%; text-align:left }}
.ag-e > div {{ display:table-cell; vertical-align:top }}
.ag-e > .ag-dt {{ width:9.4mm; padding-right:2mm }}
.ag-cal {{ width:9.4mm; height:9.4mm; box-sizing:border-box; border:1pt solid {ACC}; border-radius:2mm; text-align:center; padding-top:1.3mm; color:{NAVY} }}
.ag-cal .j {{ display:block; font:700 11.5pt/1 {SANS} }}
.ag-cal .m {{ display:block; font:600 5.8pt/1.2 {SANS}; letter-spacing:.05em; text-transform:uppercase; color:{ACC}; margin-top:.4mm }}
.ag-cal.mois {{ padding-top:2mm }} .ag-cal.mois .j {{ font-size:7.6pt; letter-spacing:.03em; text-transform:uppercase }}
.ag-th {{ font-weight:700; font-family:{SANS}; line-height:1.2; letter-spacing:.1em; text-transform:uppercase; color:#7d6c47; margin-bottom:.4mm; hyphens:manual }}
.ag-q {{ line-height:1.25 }}
/* lexique */
.lx {{ font-size:{PETIT_MIN}pt; line-height:1.32; text-align:left }} .lx b {{ font:700 .95em {SANS}; color:{NAVY} }}
/* illustration : dessin de presse au trait, sous le titre, sur la colonne */
.ill {{ margin:0; width:100%; overflow:hidden; display:flex; align-items:center; justify-content:center }} .ill img {{ display:block; object-fit:contain }}
/* crédit */
.colo {{ display:table; width:100%; table-layout:fixed; position:relative; top:{DECAL_CREDIT:.2f}px }}
.colo-qr {{ display:table-cell; width:22mm; vertical-align:bottom }} .colo-qr .qr {{ display:block; width:22mm; height:22mm }}
.colo-t {{ display:table-cell; vertical-align:bottom; padding-right:3mm; font:400 {colo_pt}pt/1.3 {SANS}; color:#4b5563; text-align:right; hyphens:manual; white-space:nowrap }}
.colo-t a {{ color:inherit; text-decoration:none }}
.colo-t .mq {{ font:400 1.9em/1 {SERIF}; color:{NAVY}; margin-bottom:.25em }} .colo-t .mq i {{ color:{ACC} }} .colo-t .mq span {{ font:600 .95em/1 {SANS} }} .nw {{ white-space:nowrap }}
'''


def une_autres(ed):
    rubs = ed['rubriques']
    une = rubs[0] if rubs and rubs[0]['label'].lower().startswith('à la une') else None
    return une, (rubs[1:] if une else rubs)


def haut_html(ed):
    """Haut de la page 1 : manchette, bandeau, « L'essentiel » et sommaire, en-tête de la Une."""
    m = ed['meta']; une, autres = une_autres(ed)
    toc = [x for x in m.get('toc', []) if not x.lower().startswith(('à la une', 'agenda'))]
    som = [f'<a href="#r{k}">{T(toc[k] if len(toc) == len(autres) else r["label"])}</a>' for k, r in enumerate(autres)]
    if ed.get('sigles'): som.append('<a href="#r-lexique">Glossaire</a>')
    if ed['agenda']: som.append('<a href="#r-agenda">Agenda</a>')
    mono = os.path.join(TOOLS, 'monogramme.png')
    h = (f'<header class="mast"><div class="ey">Revue de presse hebdomadaire</div>'
         f'<div class="tl"><img class="mono" src="file://{mono}" alt=""><h1><i>Software</i> <span>Compliance</span></h1></div>'
         f'<div class="st">L’essentiel de la conformité des logiciels embarqués dans les produits de défense</div></header>'
         f'<div class="band"><span class="n">N° {m["n"]} – {T(m.get("date_long", m["date"]))}</span><span class="r">Revue de presse hebdomadaire, tous les mardis</span></div>'
         f'<div class="top"><div class="ess"><div class="ess-in"><p class="l">{T(ed["chapo"])}</p></div></div><div class="gout"></div>'
         f'<div class="som"><div class="som-in"><div class="k">Dans ce numéro</div>{"".join(som)}</div></div></div>')
    if une:
        tu = une['sous'] or une['label']
        h += f'<div class="une-k">À la une</div><h2 class="une-h">{T(tu[:1].upper() + tu[1:])}</h2>'
        if une['chapo']: h += f'<p class="une-c">{T(une["chapo"])}</p>'
    return h


def titre_html(k, r):
    sous = r['sous'][:1].upper() + r['sous'][1:]
    return (f'<h2 class="rub" id="r{k}"><span>{T(r["label"])}</span>{T(sous)}</h2>'
            + (f'<p class="rub-c">{T(r["chapo"])}</p>' if r['chapo'] else ''))


def credit(ed):
    """Crédit, en cinq lignes, à gauche du code QR de l'édition en ligne."""
    m = ed['meta']; d = m['date_iso']
    url = f'{m.get("site", "https://revue.dejeun.es/").rstrip("/")}/{d}/'
    redac = re.sub(r'^Anthropic\s+', '', m.get('redaction', 'Claude'))
    return (f'<div class="colo" id="colo"><div class="colo-t" id="colo-t">'
            f'<div class="mq"><i>Software</i> <span>Compliance</span></div>'
            f'<p>Revue de presse hebdomadaire, N°\u00a0{m["n"]} du {T(m["date"])}.<br>'
            f'Rédigée par une intelligence artificielle ({T(redac)}),<br>'
            f'peut comporter des erreurs\u00a0: pensez à croiser vos sources.<br>'
            f'Édition en ligne avec sources\u00a0: <a href="{html.escape(url)}">{html.escape(re.sub(r"^https?://", "", url).rstrip("/"))}</a><br>'
            f'©\u00a0{d[:4]} Rodolphe\u00a0Dejeunes, publié sous licence CC\u00a0BY\u00a04.0.</p></div>'
            f'<div class="colo-qr">{qr(url)}</div></div>')


def doc_html(ed, corps_html, titre=''):
    return (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>{html.escape(titre)}</title>'
            f'<style>{css(ed["meta"], ed)}</style></head><body>{corps_html}</body></html>')


# ---------------------------------------------------------------- rendu WeasyPrint et boîtes

_FC = []


def rendu(h):
    from weasyprint import HTML
    from weasyprint.text.fonts import FontConfiguration
    if not _FC: _FC.append(FontConfiguration())
    return HTML(string=h, base_url=ROOT).render(font_config=_FC[0])


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
    def mesure(pt):
        ed['ess_pt'] = pt
        pg = rendu(doc_html(ed, f'<div style="width:{LARG:.2f}px">{haut_html(ed)}</div>')).pages[0]
        cls = lambda c: (lambda el: c in (el.get('class') or '').split())
        return boite(pg, cls('ess-in')).margin_height(), boite(pg, cls('som-in')).margin_height()
    pad = (2.4 + 2.6) * MM + 2 * 1.2 * PT
    pts = [x / 4 for x in range(56, 35, -1)]
    lo, hi, best = 0, len(pts) - 1, 9.0
    while lo <= hi:
        mid = (lo + hi) // 2; e, s_ = mesure(pts[mid])
        if e + pad <= s_: best, hi = pts[mid], mid - 1
        else: lo = mid + 1
    ed['ess_pt'] = best


def taille_credit(ed):
    """Plus grand corps du crédit (de 9 à 5 pt) dont le texte ne dépasse pas la hauteur du code QR."""
    qr_px = 22 * MM
    def tient(pt):
        ed['colo_pt'] = pt
        pg = rendu(doc_html(ed, f'<div style="width:{W2:.2f}px">{credit(ed)}</div>')).pages[0]
        t = boite(pg, lambda el: el.get('id') == 'colo-t')
        return sum(c.margin_height() for c in t.children) <= qr_px
    pts = [x / 4 for x in range(36, 19, -1)]
    lo, hi, best = 0, len(pts) - 1, 5.0
    while lo <= hi:
        mid = (lo + hi) // 2
        if tient(pts[mid]): best, hi = pts[mid], mid - 1
        else: lo = mid + 1
    ed['colo_pt'] = best


# ---------------------------------------------------------------- découpe des paragraphes ligne à ligne

JETON = re.compile(r'<[^>]+>|&[#\w]+;|[^<&]', re.S)


def car(t): return html.unescape(t) if t.startswith('&') else t


def debuts_lignes(inner, textes):
    """Jetons du HTML d'un paragraphe et, pour chaque ligne mesurée, l'indice du jeton où elle commence, plus un
    drapeau « mot coupé en fin de ligne ». None si le texte mesuré ne correspond pas au source."""
    toks = JETON.findall(inner)
    vis = [(i, car(t)) for i, t in enumerate(toks) if not t.startswith('<') and not car(t).isspace()]
    debuts, coupes, k = [], [], 0
    for t in textes:
        s = ''.join(c for c in t if not c.isspace())
        coupe = s.endswith('‐') and not (k + len(s) - 1 < len(vis) and vis[k + len(s) - 1][1] == '‐')
        if coupe: s = s[:-1]
        if ''.join(c for _, c in vis[k:k + len(s)]) != s: return None
        debuts.append(vis[k][0] if k < len(vis) else len(toks)); coupes.append(coupe)
        k += len(s)
    if k != len(vis): return None
    return toks, debuts, coupes


def morceau(toks, a, b):
    """HTML des jetons [a, b), balises ouvertes avant a rouvertes, balises restées ouvertes refermées."""
    pile = []
    for t in toks[:a]:
        if t.startswith('</'):
            if pile: pile.pop()
        elif t.startswith('<') and not t.endswith('/>'): pile.append(t)
    out, p2 = ''.join(pile), list(pile)
    for t in toks[a:b]:
        out += t
        if t.startswith('</'):
            if p2: p2.pop()
        elif t.startswith('<') and not t.endswith('/>'): p2.append(t)
    return out + ''.join('</' + re.match(r'<(\w+)', t)[1] + '>' for t in reversed(p2))


# ---------------------------------------------------------------- mesures

def variantes(ed):
    """Blocs facultatifs de chaque nouveauté, dans l'ordre de priorité (socle, puis portions 1, 2, 3) : la variante v
    retient les v premiers."""
    out = {}
    for b in blocs(ed):
        out.setdefault(b[1], []).append(b)
    return out


def mesurer(ed):
    """Mesure tout ce qui se compose : pour chaque corps (8,5 à 8,8 pt), les lignes de chaque paragraphe de chaque
    variante de chaque article (largeur d'une colonne) ; titres d'article, encadrés (chaque nombre de brèves),
    titres de rubrique, entrées du lexique, agenda (chaque corps), crédit, haut de la page 1. Cinq rendus en tout."""
    une, autres = une_autres(ed)
    var = variantes(ed)
    M = {'p': {}, 't': {}, 'b': {}, 'h': {}, 'x': {}, 'ag': {}, 'agh': 0, 'colo': 0, 'haut': 0}
    def art_units(it, w_une):
        vs = var.get(it['id'], [])
        for v in range(len(vs) + 1):
            incl = set(vs[:v])
            for j, x in enumerate(morceaux(it, incl, une=w_une)):
                yield v, j, x
    # 1. articles, par corps
    for fs in FS_LIST:
        parts = []
        for r, w in ([(une, W3)] if une else []) + [(r, W4) for r in autres]:
            for it in r['items']:
                est_une = r is une and it is une['items'][0]
                gen = ([(v, j, x) for v in range(3) for j, x in enumerate(morceaux(it, set(), une=True, une_niv=3 - v))]   # la Une : portions 3, puis 2, coupables
                       if est_une else art_units(it, False))
                html_u = []
                for v, j, x in gen:
                    for n_, sub in enumerate(re.findall(r'<h3 class="hl">.*?</h3>|<p class="[^"]*">.*?</p>', x, re.S)):
                        html_u.append(sub.replace('>', f' data-m="{it["id"]}|{v}|{j}|{n_}">', 1))
                parts.append(f'<div class="col" style="width:{w:.3f}px; font-size:{fs}pt; line-height:1.3">{"".join(html_u)}</div>')
        doc = rendu(doc_html(ed, '<style>@page{size:300mm 20000mm; margin:0}</style>' + ''.join(parts)))
        for pg in doc.pages:
            for b in boites(pg):
                el = getattr(b, 'element', None)
                if el is None or not el.get('data-m') or type(b).__name__ in ('LineBox', 'TextBox', 'InlineBox'): continue
                key = el.get('data-m')
                if el.tag == 'h3':
                    M['t'][key] = (b.margin_height(), max(1, len([x for x in boites_de(b) if type(x).__name__ == 'LineBox']))); continue
                lignes = [x for x in boites_de(b) if type(x).__name__ == 'LineBox']
                textes = [''.join(t.text for t in boites_de(l) if type(t).__name__ == 'TextBox') for l in lignes]
                M['p'][(fs, key)] = textes
    # 2. le reste (indépendant du corps des paragraphes)
    parts = []
    for k, r in ([('une', une)] if une else []) + list(enumerate(autres)):
        w = W3 if k == 'une' else W4
        ordre, _nd = ordre_omission(r['rappels'], ed['agenda'])
        for d in range(len(r['rappels'])):
            garde = [x for i, x in enumerate(r['rappels']) if i not in ordre[:d]]
            parts.append(f'<div style="width:{w:.3f}px">' + rappels_html(garde, set()).replace('<aside class="rap"', f'<aside class="rap" data-b="{k}|{d}"', 1) + '</div>')
        if k != 'une': parts.append(f'<div data-h="{k}" style="width:{LARG:.3f}px">{titre_html(k, r)}</div>')
    parts.append(f'<div data-h="lex" style="width:{LARG:.3f}px"><h2 class="rub" id="r-lexique"><span>Glossaire</span> Sigles et termes cités</h2></div>')
    for i, (lab, de, _n, lg, _neuf) in enumerate(ed.get('sigles') or []):
        parts.append(f'<div style="width:{W4:.3f}px"><p class="lx" data-x="c{i}"><b>{T(lab)}</b> {T(de)}</p></div>')
        parts.append(f'<div style="width:{W4:.3f}px"><p class="lx" data-x="l{i}"><b>{T(lab)}</b> {T(lg)}</p></div>')
    for pt in AG_PT:
        for e in ed['agenda']:
            parts.append(f'<div style="width:{W4:.3f}px">' + entree_agenda(e, ed['meta']['date_iso'][:4], pt).replace('class="ag-e"', f'class="ag-e" data-a="{pt}|{e["id"]}"', 1) + '</div>')
    parts.append(f'<div data-agh="1" style="width:{W2:.3f}px"><h2 class="rub"><span>Agenda</span> Dates à surveiller</h2></div>')
    parts.append(f'<div data-colo="1" style="width:{W2:.3f}px">{credit(ed)}</div>')
    parts.append(f'<div data-haut="1" style="width:{LARG:.3f}px">{haut_html(ed)}</div>')
    doc = rendu(doc_html(ed, '<style>@page{size:300mm 20000mm; margin:0}</style>' + ''.join(parts)))
    for pg in doc.pages:
        for b in boites(pg):
            el = getattr(b, 'element', None)
            if el is None or type(b).__name__ in ('LineBox', 'TextBox', 'InlineBox'): continue
            if el.get('data-b'): M['b'].setdefault(el.get('data-b'), b.margin_height())
            elif el.get('data-h'): M['h'].setdefault(el.get('data-h'), b.margin_height())
            elif el.get('data-x'): M['x'].setdefault(el.get('data-x'), b.margin_height())
            elif el.get('data-a'):
                M['ag'].setdefault(el.get('data-a'), b.margin_height())
                q = next((x for x in boites_de(b) if getattr(x, 'element', None) is not None and 'ag-q' in (x.element.get('class') or '') and type(x).__name__ == 'BlockBox'), None)
                M.setdefault('agl', {})[el.get('data-a')] = len([x for x in boites_de(q) if type(x).__name__ == 'LineBox']) if q else 1
            elif el.get('data-agh'): M['agh'] = M['agh'] or b.margin_height()
            elif el.get('data-colo'): M['colo'] = M['colo'] or b.margin_height()
            elif el.get('data-haut'): M['haut'] = M['haut'] or b.margin_height()
    return M


def boites_de(b):
    yield b
    for c in getattr(b, 'children', []): yield from boites_de(c)


# ---------------------------------------------------------------- unités de composition

class ListeU(list):
    """Unités d'un bloc, avec le corps (pt) de son texte : il borne l'interligne de la justification verticale."""
    fs = 8.5


class Unite:
    """Élément d'une colonne : titre d'article ('t'), paragraphe ('p', sécable ligne à ligne), encadré ('b'), entrée
    du lexique ('x') ou illustration ('i', sous le titre, carrée sur la largeur de la colonne, calée sur la grille). ecart : nature du blanc qui le précède ; filet : filet de séparation d'articles dans ce blanc."""
    __slots__ = ('kind', 'html', 'cls', 'n', 'h', 'ecart', 'filet', 'toks', 'debuts', 'coupes', 'suite')

    def __init__(self, kind, html_='', cls='', n=0, h=0.0, ecart='par', filet=False, toks=None, debuts=None, coupes=None, suite=False):
        self.kind, self.html, self.cls, self.n, self.h, self.ecart, self.filet = kind, html_, cls, n, h, ecart, filet
        self.toks, self.debuts, self.coupes, self.suite = toks, debuts, coupes, suite


_CACHE_U = {}


def unites_rub(ed, M, k, r, fs, prof, omis, ecartes=(), pos_une=0):
    """Unités d'une rubrique (k : rang ou 'une') au corps fs ; prof : portions facultatives retirées à chaque article
    (0 : toutes retenues) ; omis : brèves omises de l'encadré (ordre_omission())."""
    cle = (k, fs, prof, omis, ecartes, pos_une)
    if cle in _CACHE_U: return _CACHE_U[cle]
    une, _ = une_autres(ed)
    var = variantes(ed)
    us = ListeU(); us.fs = fs
    for j, it in enumerate(r['items']):
        est_une = k == 'une' and j == 0
        v = min(prof, 2) if est_une else max(min(1, len(var.get(it['id'], []))), len(var.get(it['id'], [])) - prof)
        incl = set() if est_une else set(var.get(it['id'], [])[:v])
        prev_t, premier = False, True
        ill = (ed.get('illustrations') or {}).get(it['id'])
        ill_une = None
        if est_une and ill and it['id'] not in ecartes:   # la Une n'a pas de titre d'article dans ses colonnes : le dessin ouvre la première,
            # ou vient après le paragraphe pos_une (meilleure répartition sur la page)
            ill_une = Unite('i', f'<figure class="ill"><img src="file://{html.escape(ill[0])}" alt="{html.escape(ill[1])}"></figure>', h=W3, n=int(round(ill[2] * 1000)), ecart='titre')
            if pos_une == 0: us.append(ill_une); ill_une = None
        for jj, x in enumerate(morceaux(it, incl, une=est_une, une_niv=3 - v if est_une else 3)):
            for n_, sub in enumerate(re.findall(r'<h3 class="hl">.*?</h3>|<p class="[^"]*">.*?</p>', x, re.S)):
                key = f'{it["id"]}|{v}|{jj}|{n_}'
                ecart = 'art' if (premier and j > 0) else ('titre' if prev_t else 'par')
                filet = premier and j > 0
                premier = False
                if sub.startswith('<h3'):
                    us.append(Unite('t', sub, h=M['t'][key][0], n=M['t'][key][1], ecart=ecart, filet=filet)); prev_t = True
                    ill = (ed.get('illustrations') or {}).get(it['id'])
                    if ill and jj == 0 and it['id'] not in ecartes:   # dessin de presse sous le titre (ou entre deux paragraphes), sur la colonne (README, § 18)
                        us.append(Unite('i', f'<figure class="ill"><img src="file://{html.escape(ill[0])}" alt="{html.escape(ill[1])}"></figure>',
                                        h=W3 if k == 'une' else W4, n=int(round(ill[2] * 1000)), ecart='ill'))
                    continue
                cls, inner = re.match(r'<p class="([^"]*)">(.*)</p>$', sub, re.S).groups()
                textes = M['p'][(fs, key)]
                dl = debuts_lignes(inner, textes)
                if dl is None: print(f'  ! découpe impossible ({key}) : paragraphe insécable', file=sys.stderr)
                us.append(Unite('p', inner, cls, n=len(textes), ecart=ecart, filet=filet, toks=dl and dl[0], debuts=dl and dl[1], coupes=dl and dl[2]))
                prev_t = False
                if ill_une is not None and sum(1 for u_ in us if u_.kind == 'p') == pos_une: us.append(ill_une); ill_une = None
    if r['rappels']:
        d = len(omis)
        hb = M['b'].get(f'{k}|{d}')
        if hb is not None:
            garde = [x for i, x in enumerate(r['rappels']) if i not in omis]
            us.append(Unite('b', rappels_html(garde, set()), h=hb, ecart='bref'))
    _CACHE_U[cle] = us
    return us


def unites_lex(ed, M, n, longs=0):
    """Entrées du glossaire : n termes, d'abord ceux qui apparaissent pour la première fois dans ce numéro, puis les
    plus cités ; présentés dans l'ordre alphabétique ; les « longs » premiers avec leur définition complète, les autres
    avec leur développement ou une définition courte."""
    sg = sorted(enumerate(ed.get('sigles') or []), key=lambda x: (not x[1][4], -x[1][2], x[1][0]))[:n]
    lg = {i for i, _x in sg[:longs]}
    garde = sorted(sg, key=lambda x: x[1][0].lower())
    us = ListeU(Unite('x', f'<p class="lx"><b>{T(x[0])}</b> {T(x[3] if i in lg else x[1])}</p>', h=M['x'][f'{"l" if i in lg else "c"}{i}'], ecart='lex') for i, x in garde)
    us.fs = PETIT_MIN
    return us


# ---------------------------------------------------------------- composition des colonnes

G_TITRE = 1.2 * MM   # blanc minimal sous un titre d'article


def lignes_titre(u, lh_px):
    """Nombre de lignes de texte qu'occupent un titre d'article et son blanc : l'entier le plus proche, l'interligne
    du titre s'ajustant (0,98 à 1,30) ; sinon l'entier supérieur."""
    k = round((u.h + G_TITRE) / lh_px)
    lt = (k * lh_px - G_TITRE) / max(u.n, 1) / (TITRE_PT * PT)
    return k if .98 <= lt <= 1.30 else math.ceil((u.h + G_TITRE) / lh_px - 1e-6)


def blanc(u, lh_px):
    """Blanc avant une unité : aucun entre paragraphes (alinéa seul, comme dans la presse), une ligne entre deux
    articles (filet au milieu) ; le blanc sous un titre est compris dans sa hauteur, calée sur la grille des lignes."""
    if u.ecart == 'art': return lh_px
    if u.ecart in ('par', 'titre'): return 0.0
    return ECART[u.ecart]


G_ILL = 2.8 * MM        # blanc sous une illustration
G_ILL_HAUT = 2.8 * MM   # blanc au-dessus d'une illustration placée entre deux paragraphes
# (sous son titre, le dessin prend 1,6 mm de blanc au-dessus, ECART['ill'], qui s'ajoute au blanc du titre, 1,2 mm au moins)
ILL_HMAX = 48 * MM       # hauteur maximale d'un dessin
ILL_HMAX_UNE = 46 * MM   # hauteur maximale du dessin de la Une (colonne plus large, page 1 chargée)
ILL_RETRECI = .85       # un dessin peut perdre jusqu'à 15 % de sa largeur pour tomber sur la grille plutôt que laisser du blanc


def dims_ill(u, lh_px):
    """(hauteur sur la grille, hauteur et largeur du dessin) : le dessin occupe la largeur de la colonne (u.h), rapport
    u.n / 1000 ; s'il dépasse la ligne d'un peu, il rétrécit (ILL_RETRECI au plus) plutôt que d'ajouter une ligne blanche."""
    w = u.h
    h = w * u.n / 1000
    hmax = ILL_HMAX_UNE if u.h > W4 + 1 else ILL_HMAX
    if h > hmax: w, h = w * hmax / h, hmax   # un dessin haut (ou celui de la Une) ne dépasse pas sa hauteur maximale
    k = math.floor((h + G_ILL) / lh_px + 1e-6)
    if k * lh_px - G_ILL >= ILL_RETRECI * h and k >= 2: return k * lh_px, k * lh_px - G_ILL, w * (k * lh_px - G_ILL) / h
    k = math.ceil((h + G_ILL) / lh_px - 1e-6)
    return k * lh_px, h, w


def hauteur_u(u, lh_px, a=0, b=None):
    if u.kind == 'p': return ((u.n if b is None else b) - a) * lh_px
    if u.kind == 't': return lignes_titre(u, lh_px) * lh_px   # titre et son blanc : un nombre entier de lignes du texte
    if u.kind == 'i':
        if b == -1: return 0.0   # dessin écarté faute de place dans son article
        return dims_ill(u, lh_px)[0]   # dessin sur la largeur de la colonne (h), rapport n/1000, et son blanc, sur la grille
    return u.h


def remplir(us, pos, hauteurs, lh_px):
    """Remplit des colonnes de hauteurs données à partir de pos = (unité, ligne). Règles : jamais moins de deux lignes
    d'un paragraphe en bas ou en haut de colonne ; un titre d'article garde au moins deux lignes de son texte ; un
    encadré ou une entrée ne se coupe pas. Renvoie (colonnes, pos final, tout placé) ; colonne = ([(i, a, b, blanc)], hauteur)."""
    i, l = pos
    cols = []
    att = None   # dessin en attente : il n'a pas tenu sous son titre, il se placera entre deux paragraphes de son article
    def tient_ill(j, y, H, parts):
        """Le dessin j tient-il ici, suivi de deux lignes du paragraphe suivant (ou de la suite de l'article) ?"""
        g = G_ILL_HAUT if parts else 0.0
        return y + g + hauteur_u(us[j], lh_px) + 2 * lh_px <= H + .01
    for H in hauteurs:
        y, parts = 0.0, []
        if att is not None and l == 0 and i < len(us) and us[i].kind == 'p':   # en tête de colonne, entre deux paragraphes
            if tient_ill(att, y, H, parts): parts.append((att, 0, None, 0.0)); y += hauteur_u(us[att], lh_px); att = None
        while i < len(us):
            u = us[i]
            g = blanc(u, lh_px) if parts else 0.0
            if att is not None and u.kind != 'p':   # fin de l'article sans place pour son dessin : écarté (coût dans penalite_col)
                parts.append((att, 0, -1, 0.0)); att = None
            if u.kind == 'p' and u.toks is not None:
                reste = u.n - l
                place = int((H - y - g + .01) // lh_px) if H - y - g > 0 else 0
                if place >= reste:
                    parts.append((i, l, u.n, g)); y += g + reste * lh_px; i += 1; l = 0
                    if att is not None and i < len(us) and us[i].kind == 'p' and tient_ill(att, y, H, parts):   # entre deux paragraphes
                        ga = G_ILL_HAUT; parts.append((att, 0, None, ga)); y += ga + hauteur_u(us[att], lh_px); att = None
                    continue
                k = min(place, reste - 2)
                if k >= 2:
                    parts.append((i, l, l + k, g)); y += g + k * lh_px; l += k
                break
            h = hauteur_u(u, lh_px)
            if u.kind == 't':
                suiv = us[i + 1] if i + 1 < len(us) else None
                if suiv is not None and suiv.kind == 'i': suiv = us[i + 2] if i + 2 < len(us) else None
                h_suiv = min(2, suiv.n) * lh_px if suiv is not None and suiv.kind == 'p' else 0
                if y + g + h + h_suiv > H + .01: break
            elif u.kind == 'i':
                if y + g + h + 2 * lh_px > H + .01 or att is not None:   # pas la place sous le titre : le dessin attend
                    att = i; i += 1; continue
            elif y + g + h > H + .01: break
            parts.append((i, 0, u.n if u.kind == 'p' else None, g)); y += g + h; i += 1; l = 0
        if parts and us[parts[-1][0]].kind == 't' and parts[-1][0] == i - 1 and l == 0 and i < len(us):   # titre seul en bas de colonne
            t = parts.pop(); i = t[0]; y -= t[3] + hauteur_u(us[t[0]], lh_px)
        cols.append((parts, y))
        if not parts and i < len(us): return cols, (i, l), False
    if att is not None and i >= len(us) and cols: cols[-1][0].append((att, 0, -1, 0.0))   # jamais placé
    return cols, (i, l), i >= len(us)


def equilibrer(us, n, lh_px, pos=(0, 0)):
    """Plus petite hauteur commune de n colonnes qui reçoit toute la suite à partir de pos (colonnes équilibrées)."""
    tot = sum(blanc(u, lh_px) + hauteur_u(u, lh_px, pos[1] if i == pos[0] else 0) for i, u in enumerate(us) if i >= pos[0])
    lo = max([u.h for u in us[pos[0]:] if u.kind != 'p'] + [2 * lh_px, tot / n - lh_px])
    hi = tot + lh_px
    best = None
    for _ in range(40):
        if hi - lo < .3: break
        mid = (lo + hi) / 2
        cols, p2, ok = remplir(us, pos, [mid] * n, lh_px)
        if ok: best, hi = (mid, cols), mid
        else: lo = mid
    if best is None:
        cols, p2, ok = remplir(us, pos, [hi] * n, lh_px)
        best = (hi, cols) if ok else (None, None)
    if best[0] is not None:   # la plus petite hauteur n'est pas toujours la mieux répartie : on essaie jusqu'à une ligne de plus
        def cout(H, cols):
            if any(not p_ for p_, _y in cols) or len(cols) < n: return None
            return sum(penalite_col(us, p_, H, y_, lh_px)[0] for p_, y_ in cols) + 2 * (H - best[0]) / MM
        cb = cout(*best)
        for j in range(1, 5):
            H = best[0] + j * lh_px / 4
            cols, p2, ok = remplir(us, pos, [H] * n, lh_px)
            if not ok: continue
            c = cout(H, cols)
            if c is not None and (cb is None or c < cb - .5): best, cb = (H, cols), c
    return best


def bref_bas(us, parts):
    """La colonne finit par l'encadré « En bref », précédé de texte : il se cale en bas de colonne."""
    return len(parts) > 1 and us[parts[-1][0]].kind == 'b'


def ecart_col(us, parts):
    """Nombre de blancs extensibles et de lignes d'une colonne (le blanc avant un « En bref » calé en bas à part)."""
    g = sum(1 for k, (i, a, b, e) in enumerate(parts) if k > 0 and us[i].ecart in EXTENSIBLE and us[i].kind != 'b')
    nl = sum((b - a) for i, a, b, e in parts if us[i].kind == 'p')
    return g, nl


G_SOUPLE, F_SOUPLE, B_SOUPLE = .6 * MM, .3 * MM, 3 * MM   # justification verticale : par blanc, par ligne, au-dessus d'un « En bref »


def fmax(us, lh_px):
    """Interligne qu'on peut ajouter par ligne sans dépasser 1,40 (ni F_SOUPLE)."""
    return max(0.0, min(F_SOUPLE, LH_MAX * getattr(us, 'fs', 8.5) * PT - lh_px))


def repartir(s, g, nl, fm):
    """Répartit un reste s (px) d'une colonne : d'abord ses blancs (G_SOUPLE chacun), puis ses interlignes (fm par
    ligne, sans dépasser l'interligne 1,40), puis de nouveau ses blancs, en dernier ressort ses interlignes.
    Renvoie (ajout par blanc, ajout par ligne)."""
    if s <= 0: return 0.0, 0.0
    e = min(G_SOUPLE, s / g) if g else 0.0
    r = s - e * g
    f = min(fm, r / nl) if nl else 0.0
    r -= f * nl
    if r > 0:
        if g: e += r / g
        elif nl: f += r / nl
    return e, f


ILL_SOUPLE = .8 * MM   # blanc qu'un dessin peut prendre autour de lui (centré) pour justifier sa colonne


def absorbe_ill(us, parts, s):
    """Part du reste s d'une colonne que prennent ses dessins (ILL_SOUPLE chacun, centré autour du dessin) : (par dessin, reste)."""
    n = sum(1 for i, a, b, e in parts if us[i].kind == 'i' and b != -1)
    if not n or s <= 0: return 0.0, s
    a = min(ILL_SOUPLE, s / n)
    return a, s - a * n


def partage_col(us, parts, s, lh_px):
    """(blanc au-dessus de l'« En bref » calé en bas, ajout par blanc, ajout par ligne) pour un reste s."""
    b = min(s, B_SOUPLE) if bref_bas(us, parts) else 0.0
    g, nl = ecart_col(us, parts)
    e, f = repartir(s - b, g, nl, fmax(us, lh_px))
    if bref_bas(us, parts) and not g and not nl: b = s
    return b, e, f


def penalite_col(us, parts, H, y, lh_px):
    """Coût d'une colonne de hauteur cible H remplie sur y : le reste est réparti (partage_col()) ; il se voit
    au-delà de 0,6 mm par blanc, de l'interligne 1,40, ou de 3 mm au-dessus d'un « En bref »."""
    s = H - y
    ec = COUT_ILL * sum(1 for i_, a_, b_, e_ in parts if us[i_].kind == 'i' and b_ == -1)   # dessins écartés
    ai, s2 = absorbe_ill(us, parts, s)
    if ai: ec += .6 * (s - s2) / MM; s = s2   # le blanc autour d'un dessin se voit peu
    if s < .5: return ec, s
    g, nl = ecart_col(us, parts)
    if not g and not nl and not bref_bas(us, parts): return ec + 40 * s / MM, s
    b, e, f = partage_col(us, parts, s, lh_px)
    fm = fmax(us, lh_px)
    if us[0].kind == 'x' and g:   # glossaire : le blanc entre les entrées peut s'ouvrir jusqu'à 2 mm sans se voir
        return ec + .4 * s / MM + (30 * (e / MM - 2) * g if e > 2 * MM else 0), s
    pen = ec + .8 * s / MM + .3 * b / MM + (40 * (b / MM - 3) if b > B_SOUPLE + .5 else 0)
    pen += (30 * (e / MM - .6) * g if e > G_SOUPLE else 0) + (300 * (f - fm) / MM * nl if f > fm + .01 else 0)
    return pen, s


# ---------------------------------------------------------------- composition des pages (recherche en faisceau)

def options_rub(ed, k, r):
    """Réglages possibles d'une rubrique : (corps, interligne, portions retirées, brèves omises, dessins écartés)."""
    var = variantes(ed)
    pmax = max([len(var.get(it['id'], [])) - 1 for it in r['items']] + [0])
    ordre, nd = ordre_omission(r['rappels'], ed['agenda']) if r['rappels'] else ([], 0)
    oms = [()]
    if nd: oms.append(tuple(ordre[:nd]))
    for x in (1, 2):   # brèves omises au-delà des doublons de l'agenda (coûteux) ; une au moins reste
        if r['rappels'] and len(r['rappels']) - nd - x >= 1: oms.append(tuple(ordre[:nd + x]))
    ills = [it['id'] for it in r['items'] if it['id'] in (ed.get('illustrations') or {})]
    ecs = [()] + [tuple(ills[-x:]) for x in range(1, len(ills) + 1)]   # dessins écartés, les derniers de la rubrique d'abord
    return [(fs, lh, pr, om, ec) for fs in FS_LIST for lh in LH_LIST for pr in range(min(pmax, 3) + 1) for om in oms for ec in ecs]


def cout_option(ed, k, r, opt, prec):
    """Préférences : contenu complet (portion retirée : 8 par article ; brève répétée par l'agenda omise : 6, autre : 400, plus qu'une composition moins régulière mais sans défaut), corps
    ample (1 par 0,1 pt sous 8,8), régularité d'une rubrique à l'autre."""
    fs, lh, pr, om, ec = opt
    ordre, nd = ordre_omission(r['rappels'], ed['agenda']) if r['rappels'] else ([], 0)
    c = COUT_PORTION * pr * len(r['items']) + sum(6 if j < nd else COUT_BREVE for j in range(len(om))) + COUT_ILL * len(ec) + 10 * (FS_LIST[-1] - fs) + 10 * abs(lh - 1.34)
    if prec: c += 15 * abs(fs - prec[0]) + 60 * abs(lh - prec[1])
    return c


def geometrie_bas(ed, M, ag_pt):
    """Bas de la dernière page : agenda (deux colonnes, ancré en bas à gauche) et crédit (en bas à droite). Le partage
    des dates égale au mieux les deux colonnes ; l'écart restant se rattrape d'abord par le blanc entre les dates
    (resserré d'1 mm au plus dans la plus longue, élargi de 2,5 mm au plus dans la plus courte), puis par l'interligne
    de la plus courte. Renvoie (hauteur de l'agenda, partage, blanc ajouté entre deux dates de la colonne courte,
    interligne ajouté (px), colonne la plus courte, hauteur du crédit, blanc retiré dans la longue)."""
    ev = ed['agenda']
    if not ev: return 0.0, 0, 0.0, 0.0, 0, M['colo'], 0.0
    hs = [M['ag'][f'{ag_pt}|{e["id"]}'] for e in ev]
    nl = [M['agl'][f'{ag_pt}|{e["id"]}'] for e in ev]
    best = None
    for s in range(1, len(ev)):
        c1 = sum(hs[:s]) + G_AG * (s - 1); c2 = sum(hs[s:]) + G_AG * (len(ev) - s - 1)
        court_ = 1 if c1 < c2 else 2
        ng_c = (s - 1) if court_ == 1 else (len(ev) - s - 1)
        ng_l = (len(ev) - s - 1) if court_ == 1 else (s - 1)
        lignes = sum(nl[:s]) if court_ == 1 else sum(nl[s:])
        d = abs(c1 - c2)
        rl = min(1.0 * MM, d / 2 / ng_l) if ng_l else 0.0
        d2 = d - rl * ng_l
        eg = min(2.5 * MM, d2 / ng_c) if ng_c else 0.0
        ex = (d2 - eg * ng_c) / max(lignes, 1)
        cle = (round(ex, 2), eg + rl)
        if best is None or cle < best[0]: best = (cle, s, max(c1, c2) - rl * ng_l, court_, eg, ex, rl)
    _, s, hc, court_, eg, ex, rl = best
    return M['agh'] + 2 * MM + hc, s, eg, ex, court_, M['colo'], rl


class Etat:
    """État de la recherche : page et hauteur atteintes, coût, plan (liste chaînée d'éléments placés), défauts."""
    __slots__ = ('p', 'y', 'cout', 'plan', 'defauts', 'prec', 'lex', 'geo', 'choix')

    def __init__(self, p, y, cout, plan, defauts, prec, lex, geo, choix):
        self.p, self.y, self.cout, self.plan, self.defauts, self.prec, self.lex, self.geo, self.choix = p, y, cout, plan, defauts, prec, lex, geo, choix


def positions_ill(plan):
    """Dessins placés : [(page, colonne, ordonnée du centre, sous son titre)] d'après le plan."""
    out = []
    for it in liste(plan):
        if it[0] != 'cols': continue
        _, p, y0, specs, cols, us, fs, lh_px, wrap = it
        for (x, w, H), (parts, _y) in zip(specs, cols):
            y = 0.0
            for k, (i, a, b, g) in enumerate(parts):
                h = hauteur_u(us[i], lh_px, a, b)
                if us[i].kind == 'i' and b != -1:
                    sous_titre = k == 0 and p == 0 and y0 < 200 * MM or (k > 0 and us[parts[k - 1][0]].kind == 't')
                    out.append((p, int(round(x / (W4 + GOUT))) + (4 if p == 2 else 0), y0 + y + (g if k else 0) + h / 2, sous_titre))
                y += (g if k else 0) + h
    return out


def cout_repartition(plan):
    """Répartition des dessins (README, § 18) : deux dessins d'une même page ne partagent ni la colonne ni la bande
    horizontale ; la double page 2-3 se lit comme un seul espace (huit colonnes) : ses dessins s'étagent du haut en bas ;
    deux dessins au plus par page, trois sur la double page ; un dessin hors de son titre coûte un peu."""
    ps = positions_ill(plan)
    c = sum(8 for x in ps if not x[3])
    for a in range(len(ps)):
        for b in range(a + 1, len(ps)):
            (p1, c1, y1, _), (p2, c2, y2, _) = ps[a], ps[b]
            proche = abs(y1 - y2) < 70 * MM
            if p1 == p2:
                if c1 == c2: c += 120
                if proche: c += 50
                if abs(c1 - c2) == 1 and proche: c += 20
            elif {p1, p2} == {1, 2}:
                if proche: c += 40
                if abs(c1 - c2) == 1 and proche: c += 20
    par_page = {}
    for x in ps: par_page[x[0]] = par_page.get(x[0], 0) + 1
    c += sum(80 * max(0, n - 2) for n in par_page.values())
    c += 100 * max(0, par_page.get(1, 0) + par_page.get(2, 0) - 3)
    return c


def liste(ch):
    out = []
    while ch: ch, x = ch; out.append(x)
    return out[::-1]


def cout_cols(us, cols, cibles, nom, p, D, lh_px):
    """Coût de colonnes remplies (cols) pour des hauteurs cibles ; défauts visibles notés dans D. Une colonne vide
    rend la composition impossible (None)."""
    c = 0.0
    if len(cols) < len(cibles) or any(not parts for parts, _y in cols): return None
    for (parts, y), H in zip(cols, cibles):
        pen, s = penalite_col(us, parts, H, y, lh_px)
        c += pen
        if s > .5:
            b, e, f = partage_col(us, parts, s, lh_px)
            if e > (2.2 if us[0].kind == 'x' else 1.5) * MM or f > fmax(us, lh_px) + .08 * MM or b > B_SOUPLE + .5 * MM:   # au-delà, la justification verticale se voit
                D.append(f'{nom} : colonne justifiée de {s / MM:.1f} mm (page {p + 1})')
    return c


_CACHE_EQ = {}


def placer(ed, M, st, bloc, cible):
    """Place un bloc (rubrique, lexique) à partir de l'état st ; renvoie le nouvel état, ou None si c'est impossible.
    bloc : dict(cle, nom, us, lh_px, fs, th (hauteur du titre), titre (élément du plan), wrap)."""
    us, lh_px, geo = bloc['us'], bloc['lh_px'], st.geo
    p, y, cout, plan, D = st.p, st.y, st.cout, st.plan, []
    pos, titre_fait = (0, 0), False
    while True:
        if p >= cible: return None
        dern_p = p == cible - 1
        if bloc.get('derniere') and not titre_fait and not dern_p:   # le glossaire ne commence jamais avant la dernière page :
            if p < cible - 2: return None                                # le bas de la page précédente s'aère (aerer())
            W = HAUT - y
            if W > .5:
                plan, dc = aerer(plan, p, W, D)
                if dc is None: return None
                cout += dc
            p, y = p + 1, 0.0
            continue
        lim = geo['L'] if dern_p else HAUT
        y0 = y + (G_RUB if y > 1 else 0) + bloc['th'] + G_CHAPO if not titre_fait else y
        if dern_p and bloc['wrap']:
            Lh, Rh = geo['L'] - y0, geo['R'] - y0
            if Lh < 4 * lh_px and bloc.get('droite') and not titre_fait:
                # glossaire réduit au minimum : les articles descendent jusqu'à l'agenda sur les quatre colonnes (le reste
                # de la page s'aère, aerer()) ; le glossaire tient dans les deux colonnes de droite, à hauteur de l'agenda
                W = geo['L'] - y
                if W < -.5: return None
                if W > .5:
                    plan, dc = aerer(plan, p, W, D)
                    if dc is None: return None
                    cout += dc
                top = HAUT - geo['hag']
                yg = top + M['agh'] + 2 * MM
                Rg = geo['R'] - yg
                if Rg < 4 * lh_px: return None
                cols, pos2, ok = remplir(us, pos, [Rg, Rg], lh_px)
                if not ok or any(not c[0] for c in cols): return None
                cc = cout_cols(us, cols, [Rg, Rg], bloc['nom'], p, D, lh_px)
                if cc is None: return None
                cout += cc
                plan = (plan, ('titre', p, top, bloc['titre'], W2 + GOUT, W2))
                plan = (plan, ('cols', p, yg, [(2 * (W4 + GOUT), W4, Rg), (3 * (W4 + GOUT), W4, Rg)], cols, us, bloc['fs'], lh_px, 'droite'))
                return Etat(p, HAUT, cout, plan, D and (st.defauts, D) or st.defauts, st.prec, st.lex, geo, st.choix)
            if Lh < 4 * lh_px: return None
            cols, pos2, ok = remplir(us, pos, [Lh, Lh, Rh, Rh], lh_px)
            if not ok or any(not c[0] for c in cols): return None
            cc = cout_cols(us, cols, [Lh, Lh, Rh, Rh], bloc['nom'], p, D, lh_px)
            if cc is None: return None
            cout += cc
            if not titre_fait: plan = (plan, ('titre', p, y0 - bloc['th'] - G_CHAPO, bloc['titre']))
            plan = (plan, ('cols', p, y0, [(0, W4, Lh), (W4 + GOUT, W4, Lh), (2 * (W4 + GOUT), W4, Rh), (3 * (W4 + GOUT), W4, Rh)], cols, us, bloc['fs'], lh_px, True))
            return Etat(p, HAUT, cout, plan, D and (st.defauts, D) or st.defauts, st.prec, st.lex, geo, st.choix)
        ck = (bloc['cle'], pos)
        if ck not in _CACHE_EQ: _CACHE_EQ[ck] = equilibrer(us, 4, lh_px, pos)
        H, colsb = _CACHE_EQ[ck]
        if H is not None and y0 + H <= lim + .01:
            cc = cout_cols(us, colsb, [H] * 4, bloc['nom'], p, D, lh_px)
            if cc is None: return None
            cout += cc
            if titre_fait and H < MIN_QUEUE * lh_px:
                cout += 400; D.append(f'{bloc["nom"]} : fin de rubrique de {H / lh_px:.0f} ligne(s) en tête de la page {p + 1}')
            if not titre_fait: plan = (plan, ('titre', p, y0 - bloc['th'] - G_CHAPO, bloc['titre']))
            plan = (plan, ('cols', p, y0, [(c * (W4 + GOUT), W4, H) for c in range(4)], colsb, us, bloc['fs'], lh_px, False))
            return Etat(p, y0 + H, cout, plan, D and (st.defauts, D) or st.defauts, st.prec, st.lex, geo, st.choix)
        if dern_p or bloc.get('entier'): return None   # au-dessus de l'agenda, tout doit tenir ; le lexique ne se coupe pas
        A = lim - y0
        cols, pos2, ok = remplir(us, pos, [A] * 4, lh_px) if A >= MIN_TETE * lh_px else ([], pos, False)
        if not cols or ok or any(not c[0] for c in cols):
            if titre_fait: return None
            # la rubrique ne peut pas commencer ici : le blanc du bas de la page se répartit au-dessus des titres de la
            # page (AIR_MAX chacun), puis dans les colonnes du dernier bloc, qui finit alors au bas de la page
            W = HAUT - y
            if W > .5:
                plan, dc = aerer(plan, p, W, D)
                if dc is None: return None
                cout += dc
            p, y = p + 1, 0.0
            continue
        dy = 0.0
        if not titre_fait and y > 1:   # début de rubrique en bas de page : colonnes plus courtes (d'une demi-ligne à une
            # ligne et demie) si elles s'égalent mieux ; le reste passe au-dessus du titre
            best = None
            for j_ in range(4):
                T_ = A - j_ * lh_px / 2
                c_, p_, ok_ = remplir(us, pos, [T_] * 4, lh_px) if T_ >= MIN_TETE * lh_px else ([], pos, True)
                if not c_ or ok_ or any(not x[0] for x in c_): continue
                d_ = min(AIR_MAX, A - max(x[1] for x in c_))
                cc_ = cout_cols(us, c_, [A - d_] * 4, '', p, [], lh_px)
                if cc_ is None: continue
                if best is None or cc_ + 1.5 * d_ / MM < best[0]: best = (cc_ + 1.5 * d_ / MM, c_, p_, d_)
            if best: _, cols, pos2, dy = best
        cc = cout_cols(us, cols, [A - dy] * 4, bloc['nom'], p, D, lh_px)
        if cc is None: return None
        reste_l = sum((us[i].n - (pos2[1] if i == pos2[0] else 0)) for i in range(pos2[0], len(us)) if us[i].kind == 'p')
        if reste_l < MIN_QUEUE * 2 and len(us) - pos2[0] < 8: return None   # la page suivante ne commence pas par un encadré seul ou quelques lignes
        cout += cc + 1.5 * dy / MM
        if not titre_fait: plan = (plan, ('titre', p, y0 + dy - bloc['th'] - G_CHAPO, bloc['titre']))
        plan = (plan, ('cols', p, y0 + dy, [(c * (W4 + GOUT), W4, A - dy) for c in range(4)], cols, us, bloc['fs'], lh_px, False))
        titre_fait, pos, p, y = True, pos2, p + 1, 0.0


COUT_BREVE = float(os.environ.get('JOURNAL_COUT_BREVE', '400'))   # coût d'une brève omise (hors doublons de l'agenda)
COUT_ILL = float(os.environ.get('JOURNAL_COUT_ILL', '150'))   # coût d'un dessin écarté
COUT_PORTION = float(os.environ.get('JOURNAL_COUT_PORTION', '8'))   # coût d'un niveau de portions facultatives retiré, par article
AIR_MAX = 6 * MM   # blanc ajouté au plus au-dessus d'un titre (justification verticale d'une page)
AIR_HAUT = 14 * MM  # blanc ajouté au plus sous le bandeau et dans l’en-tête de la Une (trois blancs ; manchette et bandeau fixes)


def aerer(plan, p, W, D):
    """Justification verticale de la page p, dont le bas reste blanc sur W : le blanc se répartit d'abord au-dessus des
    titres de rubrique de la page (sauf en haut de page) et, en page 1, au-dessus de la Une, puis dans les blancs des
    colonnes du dernier bloc. Renvoie (plan, coût) ; coût None si la page ne peut pas être remplie."""
    items, ch = [], plan
    while ch and ch[1][1] == p and ch[1][0] in ('titre', 'cols', 'haut'):
        items.append(ch[1]); ch = ch[0]
    items.reverse()
    if not items or items[-1][0] != 'cols': return plan, 30 * W / MM
    gaps = [n for n, it in enumerate(items) if (it[0] == 'titre' and it[2] > 1) or (it[0] == 'cols' and n > 0 and items[n - 1][0] == 'haut')]
    ah = min(AIR_HAUT, W) if items[0][0] == 'haut' else 0.0   # page 1 : d'abord les blancs de la manchette et de l'en-tête de la Une
    W -= ah
    a = min(AIR_MAX, W / len(gaps)) if gaps else 0.0
    cout, off, out = .5 * ah / MM + 1.5 * a / MM * len(gaps), ah, []
    for n, it in enumerate(items):
        if n in gaps: off += a
        if it[0] == 'titre': out.append(('titre', it[1], it[2] + off, it[3]))
        elif it[0] == 'cols': out.append(it[:2] + (it[2] + off,) + it[3:])
        elif it[0] == 'haut': out.append(('haut', 0, ah))
        else: out.append(it)
    reste = W - a * len(gaps)
    der = out[-1]
    if reste > .5:
        _, pp, yy, specs, cc, uu, ff, ll, wr = der
        specs2 = [(x, w, h + reste) for x, w, h in specs]
        d0 = cout_cols(uu, cc, [h for _, _, h in specs], '', pp, [], ll) or 0
        d1 = cout_cols(uu, cc, [h for _, _, h in specs2], f'page {pp + 1}', pp, D, ll)
        if d1 is None: return plan, None
        cout += d1 - d0
        out[-1] = ('cols', pp, yy, specs2, cc, uu, ff, ll, wr)
    for it in out: ch = (ch, it)
    return ch, cout


def bloc_rub(ed, M, k, r, opt):
    fs, lh, pr, om, ec = opt
    us = unites_rub(ed, M, k, r, fs, pr, om, ec)
    return {'cle': ('r', k, opt), 'nom': f'« {r["label"]} »', 'us': us, 'lh_px': lh * fs * PT, 'fs': fs,
            'th': M['h'][str(k)], 'titre': ('rub', k), 'wrap': False}


_CACHE_LU = {}


def bloc_lex(ed, M, n, longs=0):
    if (n, longs) not in _CACHE_LU: _CACHE_LU[(n, longs)] = unites_lex(ed, M, n, longs)
    us = _CACHE_LU[(n, longs)]
    return {'cle': ('lex', n, longs), 'nom': 'Lexique', 'us': us, 'lh_px': 1.32 * PETIT_MIN * PT, 'fs': PETIT_MIN,
            'th': M['h']['lex'], 'titre': ('lex',), 'wrap': False}


def chercher(ed, M, cible=PAGES, largeur=200, lex_libre=False, complet=False):
    """Recherche en faisceau, rubrique par rubrique, des réglages qui composent le journal sans défaut : Une, puis
    chaque rubrique (corps, interligne, portions facultatives, brèves omises), lexique en appoint, corps de l'agenda."""
    une, autres = une_autres(ed)
    K = len(autres)
    # bornes de hauteur (pleine largeur) de chaque rubrique et du lexique, pour estimer si la place restante peut être remplie
    bornes = []
    for k, r in enumerate(autres):
        hs, tous = [], []
        for opt in options_rub(ed, k, r):
            b = bloc_rub(ed, M, k, r, opt); ck = (b['cle'], (0, 0))
            if ck not in _CACHE_EQ: _CACHE_EQ[ck] = equilibrer(b['us'], 4, b['lh_px'])
            H, cols = _CACHE_EQ[ck]
            if H is None: continue
            cc = cout_cols(b['us'], cols, [H] * 4, '', 0, [], b['lh_px'])
            if cc is not None: tous.append((cc, G_RUB + b['th'] + G_CHAPO + H))
            if cc is not None and cc < 25: hs.append(G_RUB + b['th'] + G_CHAPO + H)   # réglages sans colonne creusée
        if not hs and tous: hs = [h for c, h in tous if c <= min(tous)[0] + 25]
        bornes.append((min(hs), max(hs)) if hs else (0.0, 0.0))
    lmax = 0.0
    if ed.get('sigles'):
        for mode in (len(ed['sigles']), 0):
            b = bloc_lex(ed, M, len(ed['sigles']), mode)
            H = equilibrer(b['us'], 4, b['lh_px'])[0] or 0
            lmax = max(lmax, G_RUB + M['h']['lex'] + G_CHAPO + H)
    def estime(st, k):
        """Écart (mm, pondéré) entre la place qui reste et ce que les rubriques k+1… (et le lexique) peuvent occuper."""
        z = .5 * (st.geo['hag'] + G_BAS) + .5 * (M['colo'] + G_BAS)
        cap = (cible - 1 - st.p) * HAUT + (HAUT - st.y) - z
        lo = sum(b[0] for b in bornes[k + 1:]); hi = sum(b[1] for b in bornes[k + 1:]) + (0 if st.lex else lmax)
        return 20 * max(0.0, cap - hi) / MM + 20 * max(0.0, lo - cap) / MM
    etats = []
    for ag in AG_PT:
        hag, s, eg, ex, court_, hcol, rl = geometrie_bas(ed, M, ag)
        geo = {'ag': ag, 'L': HAUT - hag - G_BAS, 'R': HAUT - hcol - G_BAS, 's': s, 'eg': eg, 'ex': ex, 'court': court_, 'hag': hag, 'rl': rl}
        c_ag = 4 * (AG_PT[-1] - ag) + 400 * max(0.0, ex / MM - .06) + 3 * (eg + rl) / MM
        Dg = [f'agenda : interligne augmenté de {ex / MM:.2f} mm dans une colonne pour l\'égaler à l\'autre'] if ex > .1 * MM else []
        for fs in FS_LIST:
            for lh in LH_LIST:
                # la Une : son dessin ouvre la première colonne ou vient après le paragraphe pos_une (répartition sur la page)
                for pos_une, pr_une in [(a_, b_) for a_ in ((0, 1, 2, 3, 4, 5) if une and une['items'][0]['id'] in (ed.get('illustrations') or {}) else (0,)) for b_ in (0, 1, 2)]:
                    plan = (None, ('haut', 0, 0.0))
                    y, cout, D = M['haut'], c_ag + 10 * (FS_LIST[-1] - fs) + COUT_PORTION * pr_une, list(Dg)
                    if une:
                        us = unites_rub(ed, M, 'une', une, fs, pr_une, (), (), pos_une)
                        if pos_une and not any(u_.kind == 'i' for u_ in us): continue
                        lh_px = lh * fs * PT
                        ck = (('une', fs, pos_une, pr_une), (0, 0))
                        if ck not in _CACHE_EQ: _CACHE_EQ[ck] = equilibrer(us, 3, lh_px)
                        H, cols = _CACHE_EQ[ck]
                        if H is None or y + H > HAUT: continue
                        cc = cout_cols(us, cols, [H] * 3, 'la Une', 0, D, lh_px)
                        if cc is None: continue
                        cout += cc
                        plan = (plan, ('cols', 0, y, [(c * (W3 + GOUT), W3, H) for c in range(3)], cols, us, fs, lh_px, False))
                        y += H + G_APRES_UNE
                    etats.append(Etat(0, y, cout + cout_repartition(plan), plan, (None, D) if D else None, (fs, lh), False, geo, (('une', fs, lh, pos_une, pr_une), ('ag', ag))))
    lex_fin = bool(ed.get('sigles'))   # le lexique, en dernier, enveloppe l'agenda ; sans lexique, la dernière rubrique
    def elaguer(xs, k):
        meilleurs = {}
        rang = lambda s_: s_.cout + (estime(s_, k) if k < K - 1 or lex_fin else 0)
        for s_ in sorted(xs, key=rang):
            cle = (s_.p, round(s_.y / MM))
            if len(meilleurs.setdefault(cle, [])) < 2: meilleurs[cle].append(s_)
        return sorted((x for v in meilleurs.values() for x in v), key=rang)[:largeur]
    for k, r in enumerate(autres):
        nouv = []
        opts = options_rub(ed, k, r)
        if complet: opts = [o for o in opts if o[2] == 0 and not o[4] and len(o[3]) <= ordre_omission(r['rappels'], ed['agenda'])[1]]   # contenu complet (jauge)
        if os.environ.get('JOURNAL_SANS_OMISSION'): opts = [o for o in opts if len(o[3]) <= ordre_omission(r['rappels'], ed['agenda'])[1]]
        for st in etats:
            for opt in opts:
                if REGLAGE_LIBRE == 0 and (opt[0] != st.prec[0] or abs(opt[1] - st.prec[1]) > .041): continue   # même corps partout ; interligne voisin de la rubrique précédente
                b = bloc_rub(ed, M, k, r, opt)
                b['wrap'] = k == K - 1 and not lex_fin
                st2 = placer(ed, M, st, b, cible)
                if st2 is None: continue
                st2.cout += cout_option(ed, k, r, opt, st.prec)
                if opt[4] != () or any(it_['id'] in (ed.get('illustrations') or {}) for it_ in r['items']): st2.cout += cout_repartition(st2.plan) - cout_repartition(st.plan)
                st2.prec, st2.choix = (opt[0], opt[1]), st.choix + ((k,) + opt,)
                nouv.append(st2)
        if k == K - 1 and not lex_fin: nouv = [s_ for s_ in nouv if s_.p == cible - 1]
        etats = elaguer(nouv, k)
        if os.environ.get('JOURNAL_TRACE'):
            print(f'  rubrique {k} : {len(nouv)} états, {len(etats)} gardés' + (f' ; meilleur p{etats[0].p + 1} y={etats[0].y / MM:.0f} mm coût {etats[0].cout:.0f}' if etats else ''), file=sys.stderr)
        if not etats: return None
    if lex_fin:
        nouv = []
        N = len(ed['sigles'])
        def essai(st, n, longs):
            b = bloc_lex(ed, M, n, longs); b['wrap'] = True; b['derniere'] = not lex_libre; b['droite'] = True
            st3 = placer(ed, M, st, b, cible)
            if st3 is None or st3.p != cible - 1: return None
            st3.cout += .5 * (N - n) + .1 * (n - longs)
            st3.choix = st.choix + (('glossaire', n, longs),)
            return st3
        # le glossaire est l'appoint : il perd ses termes les moins utiles (anciens, peu cités) plutôt que les articles
        # leurs portions ou les brèves ; pour chaque nombre de termes, le plus grand nombre de définitions complètes qui
        # tient (recherche dichotomique), et les deux suivants
        for st in etats:
            trouves = 0
            for n in range(N, min(N, 8) - 1, -1):
                if trouves >= 4: break
                if essai(st, n, 0) is None: continue
                lo, hi = 0, n
                while lo < hi:
                    mi = (lo + hi + 1) // 2
                    if essai(st, n, mi) is None: hi = mi - 1
                    else: lo = mi
                for longs in range(lo, max(-1, lo - 3), -1):
                    st3 = essai(st, n, longs)
                    if st3 is not None: nouv.append(st3)
                trouves += 1
        if os.environ.get('JOURNAL_TRACE'): print(f'  lexique : {len(nouv)} états', file=sys.stderr)
        if not nouv: return None
        etats = nouv
    best = min(etats, key=lambda s_: s_.cout)
    plan = liste(best.plan) + [('agenda', cible - 1), ('credit', cible - 1)]
    return best, plan


# ---------------------------------------------------------------- rendu du plan

def html_colonne(us, parts, H, lh_px):
    used = 0.0
    for k, (i, a, b, g) in enumerate(parts):
        used += (g if k else 0) + hauteur_u(us[i], lh_px, a, b if b is not None else None)
    s = max(0.0, H - used)
    ai, s = absorbe_ill(us, parts, s)
    sb, ext, feather = partage_col(us, parts, s, lh_px)
    out = []
    for k, (i, a, b, g) in enumerate(parts):
        u = us[i]
        mt = 0.0 if k == 0 else g + (sb if u.kind == 'b' else (ext if u.ecart in EXTENSIBLE else 0))
        filet = u.filet and k > 0 and (u.kind != 'p' or a == 0)
        st = f'margin-top:{mt / 2:.2f}px;padding-top:{mt / 2:.2f}px' if filet else f'margin-top:{mt:.2f}px'
        fc = ' filet' if filet else ''
        if u.kind == 'p':
            if u.toks is None or (a == 0 and b == u.n): inner = u.html
            else:
                inner = morceau(u.toks, u.debuts[a], u.debuts[b] if b < u.n else len(u.toks)).strip()
                if b < u.n and u.coupes[b - 1]: inner += '‐'
            cls = u.cls + (' cont' if a > 0 else '') + (' coupe' if b < u.n else '') + fc
            if feather: st += f';line-height:{lh_px + feather:.3f}px'
            out.append(f'<p class="{cls}" data-n="{b - a}" style="{st}">{inner}</p>')
        elif u.kind == 't':   # interligne du titre ajusté pour que titre et blanc tombent sur la grille des lignes
            lt = (hauteur_u(u, lh_px) - G_TITRE) / max(u.n, 1)
            lt = min(lt, 1.30 * TITRE_PT * PT)
            pb = hauteur_u(u, lh_px) - lt * u.n
            out.append(u.html.replace('<h3 class="hl"', f'<h3 class="hl{fc}" style="{st};line-height:{lt:.3f}px;padding-bottom:{pb:.2f}px"', 1))
        elif u.kind == 'b': out.append(u.html.replace('<aside class="rap"', f'<aside class="rap{fc}" style="{st}"', 1))
        elif u.kind == 'i' and b == -1: continue
        elif u.kind == 'i':
            H_, hi, wi = dims_ill(u, lh_px)
            out.append(u.html.replace('<figure class="ill"', f'<figure class="ill" style="{st};height:{H_ - G_ILL + ai:.2f}px;margin-bottom:{G_ILL:.2f}px"', 1)
                       .replace('<img ', f'<img style="width:{wi:.2f}px;height:{hi:.2f}px" ', 1))
        else: out.append(u.html.replace('<p class="lx"', f'<p class="lx{fc}" style="{st}"', 1))
    return ''.join(out)


def html_plan(ed, M, plan, geo, cible):
    une, autres = une_autres(ed)
    pages = [[] for _ in range(cible)]
    ncol = 0
    for it in plan:
        kind, p = it[0], it[1]
        if kind == 'haut':
            q = (it[2] if len(it) > 2 else 0) / 3   # air réparti dans les trois blancs sous le bandeau (la manchette et le bandeau restent fixes)
            st = (f'<style>.band{{margin-bottom:{4.5 * MM + q:.2f}px}} .top{{margin-bottom:{3.5 * MM + q:.2f}px}}'
                  f' .une-c{{padding-bottom:{2.6 * MM + q:.2f}px}}</style>') if q else ''
            pages[0].append(f'{st}<div class="abs" style="top:0;left:0;width:{LARG:.2f}px">{haut_html(ed)}</div>')
        elif kind == 'titre':
            _, p, y, t = it[:4]
            x, w = it[4:6] if len(it) > 4 else (0, LARG)
            h = titre_html(t[1], autres[t[1]]) if t[0] == 'rub' else '<h2 class="rub" id="r-lexique"><span>Glossaire</span> Sigles et termes cités</h2>'
            pages[p].append(f'<div class="abs" style="top:{y:.2f}px;left:{x:.2f}px;width:{w:.2f}px">{h}</div>')
        elif kind == 'cols':
            _, p, y0, specs, cols, us, fs, lh_px, wrap = it
            if wrap == 'droite':   # glossaire réduit : filet entre l'agenda et le glossaire, jusqu'au bas de la page
                pages[p].append(f'<div class="regle" style="top:{y0:.2f}px;left:{specs[0][0] - GOUT / 2:.2f}px;height:{HAUT - y0:.2f}px"></div>')
                wrap = False
            for c, ((x, w, H), (parts, _y)) in enumerate(zip(specs, cols)):
                ncol += 1
                pages[p].append(f'<div class="abs col" id="col-{ncol}" data-h="{H:.2f}" style="top:{y0:.2f}px;left:{x:.2f}px;width:{w:.2f}px;height:{H:.2f}px;'
                                f'font-size:{fs}pt;line-height:{lh_px:.3f}px">{html_colonne(us, parts, H, lh_px)}</div>')
                if c and parts and cols[c - 1][0]:
                    hr = max(H, specs[c - 1][2])
                    if wrap and c == 2: hr = HAUT - y0
                    if wrap and c == 1: hr = min(H, specs[0][2])
                    pages[p].append(f'<div class="regle" style="top:{y0:.2f}px;left:{x - GOUT / 2:.2f}px;height:{hr:.2f}px"></div>')
        elif kind == 'agenda' and ed['agenda']:
            ev, ag, s = ed['agenda'], geo['ag'], geo['s']
            top = HAUT - geo['hag']
            an = ed['meta']['date_iso'][:4]
            def colonne(xs, court_):
                eg, ex = (geo['eg'], geo['ex']) if court_ else (-geo.get('rl', 0.0), 0.0)
                return ''.join(entree_agenda(e, an, ag, 0 if i == 0 else G_AG + eg, ex) for i, e in enumerate(xs))
            ex1, ex2 = geo['court'] == 1, geo['court'] == 2
            yc = top + M['agh'] + 2 * MM
            pages[p].append(f'<div class="abs" style="top:{top:.2f}px;left:0;width:{W2:.2f}px"><h2 class="rub" id="r-agenda"><span>Agenda</span> Dates à surveiller</h2></div>'
                            f'<div class="abs" id="ag-1" style="top:{yc:.2f}px;left:0;width:{W4:.2f}px">{colonne(ev[:s], ex1)}</div>'
                            f'<div class="abs" id="ag-2" style="top:{yc:.2f}px;left:{W4 + GOUT:.2f}px;width:{W4:.2f}px">{colonne(ev[s:], ex2)}</div>'
                            f'<div class="regle" style="top:{yc:.2f}px;left:{W4 + GOUT / 2:.2f}px;height:{HAUT - yc:.2f}px"></div>')
        elif kind == 'credit':
            pages[p].append(f'<div class="abs" style="top:{HAUT - M["colo"]:.2f}px;left:{W2 + GOUT:.2f}px;width:{W2:.2f}px">{credit(ed)}</div>')
    m = ed['meta']
    return doc_html(ed, ''.join(f'<section class="pg{" dern" if n == len(pages) - 1 else ""}">{"".join(x)}</section>' for n, x in enumerate(pages)), f'Software Compliance – N° {m["n"]} – {m["date"]}')


def verifier(doc, cible):
    """Contrôle du rendu : nombre de pages ; chaque colonne finit à sa hauteur cible, au pixel près (rien ne déborde,
    rien ne manque) ; les deux colonnes de l'agenda finissent ensemble, en bas de page."""
    D = []
    if len(doc.pages) != cible: D.append(f'{len(doc.pages)} pages au lieu de {cible}')
    for n, pg in enumerate(doc.pages):
        fonds_ag = []
        for b in boites(pg):
            el = getattr(b, 'element', None)
            if el is None or type(b).__name__ != 'BlockBox': continue
            i = el.get('id') or ''
            if i.startswith('col-') and el.get('data-h'):
                kids = list(b.children)
                if not kids: continue
                fond = max(c.position_y + c.margin_height() for c in kids)
                if abs(fond - (b.position_y + float(el.get('data-h')))) > 1.5:
                    D.append(f'page {n + 1} : une colonne finit à {(fond - b.position_y - float(el.get("data-h"))) / MM:+.1f} mm de sa hauteur')
            elif i in ('ag-1', 'ag-2'):
                fonds_ag.append(b.position_y + b.margin_height())
        if len(fonds_ag) == 2:
            pb = pg._page_box
            if abs(fonds_ag[0] - fonds_ag[1]) > 1.5: D.append(f'agenda : colonnes décalées de {abs(fonds_ag[0] - fonds_ag[1]) / MM:.1f} mm')
            if abs(max(fonds_ag) - (pb.content_box_y() + HAUT)) > 2: D.append(f'agenda à {(pb.content_box_y() + HAUT - max(fonds_ag)) / MM:.1f} mm du bas de page')
    return D


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
              os.path.join(TOOLS, 'commun.py'), os.path.join(TOOLS, 'glossary.py'), os.path.join(TOOLS, 'en-tete.webp'),
              os.path.join(TOOLS, 'monogramme.png')]:
        hsh.update(open(f, 'rb').read())
    pi = os.path.join(CONTENT, d, 'illustrations.json')
    if os.path.exists(pi):
        hsh.update(open(pi, 'rb').read())
        for f in sorted(glob.glob(os.path.join(CONTENT, d, 'illustrations', '*'))): hsh.update(open(f, 'rb').read())
    return hsh.hexdigest()[:16]



MOTS_ARTICLE = 220   # longueur maximale d'un article imprimé (texte de l'élément et champ « papier »), README § 6, règle 7


def mesure_glossaire(M, plan):
    """Hauteur pleine largeur (px) qu'occupe le glossaire dans un plan composé, titre compris."""
    h = 0.0
    for it in plan:
        if it[0] == 'cols' and it[5] and it[5][0].kind == 'x': h += sum(x[2] for x in it[3]) / 4
        elif it[0] == 'titre' and it[3][0] == 'lex': h += M['h']['lex'] + G_CHAPO
    return h


def preparer(d):
    ed = lire(d)
    ed['sigles'] = sigles(''.join(x for r in ed['rubriques'] for it in r['items'] for x in morceaux(it, set(blocs(ed))))
                          + ''.join(corps(x['segs'])[0] for r in ed['rubriques'] for x in r['rappels']), texte_anterieur(d))
    taille_essentiel(ed); ed['colo_pt'] = CREDIT_PT
    ed['illustrations'] = illustrations(d)
    return ed


def illustrations(d):
    """Dessins retenus (content/d/illustrations.json, champ « fichier » renseigné) : {id d'élément: (chemin, alt)}."""
    p = os.path.join(CONTENT, d, 'illustrations.json')
    if not os.path.exists(p) or os.environ.get('JOURNAL_SANS_ILLUSTRATION'): return {}
    out = {}
    for x in json.load(open(p, encoding='utf-8')):
        f = x.get('fichier')
        if f and os.path.exists(os.path.join(CONTENT, d, f)): out[x['id']] = (os.path.join(CONTENT, d, f), x.get('alt', ''), ratio_svg(os.path.join(CONTENT, d, f)))
    return out


def ratio_svg(f):
    """Hauteur / largeur d'un dessin (viewBox, sinon width et height du SVG ; 1 à défaut)."""
    try:
        tete = open(f, encoding='utf-8', errors='replace').read(4000)
        m = re.search(r'viewBox="\s*[\d.\-]+\s+[\d.\-]+\s+([\d.]+)\s+([\d.]+)', tete)
        if not m: m = re.search(r'width="([\d.]+)(?:px)?"\s+height="([\d.]+)', tete)
        if m and float(m[1]) > 0: return float(m[2]) / float(m[1])
    except OSError: pass
    return 1.0


def plan_articles(ed, plan):
    """Où tombent les articles : [(page, bande, titre)], bande haut / milieu / bas de la page (Une comprise)."""
    out, vus = [], set()
    une, _ = une_autres(ed)
    if une: out.append((0, 'haut', une['items'][0]['sum']['titre'] if une['items'][0].get('sum') else 'la Une')); vus.add('une')
    for it in liste(plan):
        if it[0] != 'cols': continue
        _, p, y0, specs, cols, us, fs, lh_px, wrap = it
        for (x, w, H), (parts, _y) in zip(specs, cols):
            y = 0.0
            for k, (i, a, b, g) in enumerate(parts):
                if us[i].kind == 't':
                    t = re.sub(r'<[^>]+>', '', us[i].html).strip()
                    if t not in vus:
                        vus.add(t); yy = y0 + y
                        out.append((p, 'haut' if yy < HAUT / 3 else ('milieu' if yy < 2 * HAUT / 3 else 'bas'), html.unescape(t)))
                y += (g if k else 0) + hauteur_u(us[i], lh_px, a, b)
    return sorted(out, key=lambda x: (x[0], ['haut', 'milieu', 'bas'].index(x[1])))


def conseil_dessins(ed, plan):
    """Articles à illustrer (README, § 18) : la Une et un autre en page 1, trois sur la double page 2-3 étagés du haut en
    bas, un ou deux en page 4."""
    print('Place des articles (pour choisir les dessins : Une + 1 en page 1, 3 sur la double page 2-3 étagés haut / milieu / bas, 1 ou 2 en page 4) :')
    for p, bande, t in plan_articles(ed, plan): print(f'  p. {p + 1}, {bande} : {t}')


def jauge(d):
    """Jauge de rédaction (README, § 6, règle 9) : compose l'édition avec tout son contenu (aucune portion facultative
    coupée, aucune brève omise sinon celles que l'agenda répète), le glossaire libre de commencer avant la dernière
    page. Si elle tient, la hauteur du glossaire au-delà de son minimum (deux colonnes de droite, à hauteur de l'agenda) dit
    combien de texte ajouter (de préférence en nouveautés) ; sinon, l'édition déborde, et la jauge dit ce que la composition doit couper."""
    ed = preparer(d); M = mesurer(ed)
    res = chercher(ed, M, PAGES, lex_libre=True, complet=True)
    if res:
        best, plan = res
        conseil_dessins(ed, plan)
        g = mesure_glossaire(M, plan)
        geo = best.geo   # cible : le glossaire réduit au minimum, dans les deux colonnes de droite, à hauteur de l'agenda
        cible_g = M['h']['lex'] + G_CHAPO + (geo['R'] - (HAUT - geo['hag'] + M['agh'] + 2 * MM)) / 2
        ligne = 8.8 * 1.34 * PT
        manque = max(0.0, g - cible_g) * 4 / ligne   # lignes de colonne
        print(f'{d} : tout le contenu tient ; glossaire de {g / MM:.0f} mm (pleine largeur), minimum {cible_g / MM:.0f} mm (deux colonnes de droite, à hauteur de l\'agenda).')
        if manque < 8: print('Remplissage atteint : rien à ajouter.')
        else: print(f'Place libre : environ {manque:.0f} lignes de colonne, soit {manque * 6.5:.0f} mots, ou {manque * 6.5 / 200:.1f} article(s) de 200 mots. '
                    f'Ajouter de préférence des nouveautés (réserve, recherche élargie, § 3) plutôt que d\'allonger les articles au-delà de '
                    f'{MOTS_ARTICLE} mots ; jamais de répétition.')
        return
    res = chercher(ed, M, PAGES, lex_libre=True)
    if not res:
        print(f'{d} : l\'édition ne tient pas en {PAGES} pages, même réduite : raccourcir le socle des champs « papier ».'); return
    conseil_dessins(ed, res[1])
    une, autres = une_autres(ed); var = variantes(ed)
    mots = lambda t: len(re.findall(r"\w+(?:[’'-]\w+)*", t))
    coupe, details = 0, []
    for c in res[0].choix:
        if not isinstance(c[0], int): continue
        k, fs, lh, pr, om, ec = c; r = autres[k]
        for it in r['items']:
            v = var.get(it['id'], []); garde = max(min(1, len(v)), len(v) - pr)
            for (nom, _) in v[garde:]:
                n = int(nom[-1]) if nom[-1].isdigit() else 0
                w = sum(mots(x) for x in re.findall(r'\{\{' + str(n) + r'\|(.*?)\}\}', it['sum'].get('papier', ''), re.S)) if n else 0
                if w: coupe += w; details.append(f'{it["sum"]["titre"][:50]} : niveau {n}, {w} mots')
        ordre, nd = ordre_omission(r['rappels'], ed['agenda']) if r['rappels'] else ([], 0)
        for j in om[nd:]: details.append(f'brève omise ({r["label"]}) : « {accroche(corps(r["rappels"][j]["segs"])[0])[:60]}… »')
        for x in ec: details.append(f'dessin écarté ({r["label"]}) : {x}')
    print(f'{d} : l\'édition déborde : pour tenir en {PAGES} pages, la composition coupe {coupe} mots de portions facultatives.')
    for x in details: print('  - ' + x)
    print('Rien à ajouter. Ces portions sont coupées à l\'impression (elles restent possibles) ; si une brève est omise, '
          f'raccourcir les champs « papier » d\'environ {coupe // 2} mots (portions de niveau 3 d\'abord).')


def produire(d, sortie=None):
    """Produit les deux PDF de l'édition d dans sortie (défaut build/d) ; cache dans build/pdf-cache. Renvoie un résumé ;
    sa clé « defauts » liste les défauts de mise en page qui subsistent (la page de l'édition ne propose alors pas le PDF)."""
    import time
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
    t0 = time.time()
    ed = preparer(d)
    M = mesurer(ed)
    t1 = time.time()
    res, cible = None, PAGES
    for cible in (PAGES, 2 * PAGES, 3 * PAGES):
        res = chercher(ed, M, cible)
        if res: break
    if not res: raise RuntimeError('aucune composition possible')
    best, plan = res
    h = html_plan(ed, M, plan, best.geo, cible)
    doc = rendu(h)
    tous = list(dict.fromkeys(x for lot in liste(best.defauts) for x in lot)) + verifier(doc, cible)
    def mineur(t):   # justification verticale de moins d'une ligne : remarque, pas défaut
        m = re.search(r'colonne justifiée de ([\d.]+) mm', t)
        return bool(m and float(m[1]) <= 6) or t.startswith('agenda : interligne')
    defauts, remarques = [t for t in tous if not mineur(t)], [t for t in tous if mineur(t)]
    doc.write_pdf(a4)
    complet(h, a4)
    imposer(a4, a3)
    choix = [list(map(str, c)) for c in best.choix]
    print(f'  mesures {t1 - t0:.0f} s, composition {time.time() - t1:.0f} s, coût {best.cout:.0f} ; réglages {best.choix}', file=sys.stderr)
    info = {'edition': d, 'pages': len(doc.pages), 'cahier': cible, 'blocs': f'{sum(len(variantes(ed).get(it["id"], [])) for r in ed["rubriques"] for it in r["items"])}',
            'remplissage': 1.0, 'defauts': defauts, 'remarques': remarques, 'glossaire_mm': round(mesure_glossaire(M, plan) / MM), 'etat': {'choix': choix, 'cout': round(best.cout, 1), 'ess_pt': ed['ess_pt'], 'colo_pt': ed['colo_pt']}, 'empreinte': e}
    shutil.copy(a4, c4); shutil.copy(a3, c3); json.dump(info, open(cj, 'w'), ensure_ascii=False)
    os.makedirs(v, exist_ok=True); shutil.copy(a4, v4); json.dump(info, open(vj, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return info


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    eds = args or sorted(x for x in os.listdir(CONTENT) if re.fullmatch(r'\d{4}-\d{2}-\d{2}', x))[-1:]
    if '--jauge' in sys.argv:
        for d in eds: jauge(d)
        return
    for d in eds:
        i = produire(d)
        print(f"{d} : {i['pages']} pages (cahier de {i['cahier']}) ; défauts : {'; '.join(i.get('defauts') or []) or 'aucun'} ; remarques : {'; '.join(i.get('remarques') or []) or 'aucune'}")


if __name__ == '__main__':
    main()
