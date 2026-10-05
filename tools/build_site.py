#!/usr/bin/env python3
"""Construit le site complet et les e-mails à partir de content/.

Usage : python3 tools/build_site.py

Pour chaque édition content/AAAA-MM-JJ/ (blocks.json, meta.json) :
  build/AAAA-MM-JJ/revue-email.html  e-mail HTML
  build/AAAA-MM-JJ/revue-email.txt   partie texte de l'e-mail
  build/AAAA-MM-JJ/items.json        éléments rendus (pour les dossiers)
  _site/AAAA-MM-JJ/index.html        édition web (adresse permanente)
  _site/AAAA-MM-JJ/index.md          version Markdown (lecture par les LLM)
Et pour le site :
  _site/index.html, _site/index.md   dernière édition
  _site/archives/                    sommaire des éditions
  _site/dossiers/ et dossiers/<thème>/  pages Dossier (thèmes de tools/themes.json)
  _site/feed.xml                     flux RSS
  _site/llms.txt                     index pour les LLM
"""
import datetime, html, json, os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, 'tools')
CONTENT = os.path.join(ROOT, 'content')
SITE = os.path.join(ROOT, '_site')
BUILD = os.path.join(ROOT, 'build')
URL = 'https://revue.dejeun.es'
SANS = "'Segoe UI',Arial,sans-serif"; SERIF = "Georgia,serif"
E = lambda s: html.escape(str(s), quote=True)
TY = lambda s: str(s).replace("'", '’')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from podcast import titre_episode   # « Épisode n : … »
POD_TITRE = 'Software Compliance, le podcast'
# Visuels des flux : <image> RSS 2.0 (144 px de large au plus) et couverture du podcast (carrée, 1400 px au moins)
IMAGES_FLUX = ('flux.jpg', 'flux-144.png', 'podcast.jpg')
_T = os.path.dirname(os.path.abspath(__file__))
IMG_FLUX = ('<image><url>https://revue.dejeun.es/assets/flux-144.png</url><title>Software Compliance</title><link>https://revue.dejeun.es/</link><width>144</width><height>144</height></image>'
            if os.path.isfile(os.path.join(_T, 'flux-144.png')) else '')
IMG_POD = ('<image><url>https://revue.dejeun.es/assets/podcast.jpg</url><title>Software Compliance, le podcast</title><link>https://revue.dejeun.es/</link></image><itunes:image href="https://revue.dejeun.es/assets/podcast.jpg"/>'
           if os.path.isfile(os.path.join(_T, 'podcast.jpg')) else '')
POD_DESC = 'Chaque semaine, Julie et Guillaume passent en revue l’essentiel de l’actualité sur la conformité logicielle des produits pour l’industrie de la défense.'
MOISC = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.']
def fdate_court(iso):
    p = iso.split('-'); m = MOISC[int(p[1]) - 1]
    if len(p) == 2: return f'{m} {p[0]}'
    d = int(p[2]); return f'{"1er" if d == 1 else d} {m} {p[0]}'
MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']


def fdate_long(iso):
    p = iso.split('-'); m = MOIS[int(p[1]) - 1]
    if len(p) == 2: return f'{m} {p[0]}'
    d = int(p[2]); return f'{"1er" if d == 1 else d} {m} {p[0]}'


def episode(d):
    """Métadonnées de l'épisode audio de l'édition d (tools/podcast.py), ou None."""
    c = os.path.join(CONTENT, d)
    f = next((x for x in ('episode.m4a', 'episode.mp3') if os.path.isfile(os.path.join(c, x))), None)   # M4A ; MP3 (anciens épisodes)
    if f and os.path.isfile(os.path.join(c, 'episode.json')):
        return {**json.load(open(os.path.join(c, 'episode.json'), encoding='utf-8')), 'fichier': f, 'octets': os.path.getsize(os.path.join(c, f))}
    return None


def editions():
    return sorted(d for d in os.listdir(CONTENT) if re.fullmatch(r'\d{4}-\d{2}-\d{2}', d) and os.path.isfile(os.path.join(CONTENT, d, 'blocks.json')))


def load(d):
    c = os.path.join(CONTENT, d)
    return json.load(open(os.path.join(c, 'blocks.json'), encoding='utf-8')), json.load(open(os.path.join(c, 'meta.json'), encoding='utf-8'))


def run_gen(d):
    out = os.path.join(BUILD, d); os.makedirs(out, exist_ok=True)
    env = dict(os.environ, PYTHONPATH=TOOLS)
    r = subprocess.run([sys.executable, os.path.join(TOOLS, 'gen.py'), out], cwd=os.path.join(CONTENT, d), env=env, capture_output=True, text=True)
    sys.stdout.write(''.join(f'[{d}] {l}\n' for l in r.stdout.strip().splitlines()))
    if r.stderr.strip(): sys.stderr.write(''.join(f'[{d}] {l}\n' for l in r.stderr.strip().splitlines()))
    if r.returncode: sys.exit(f'Échec de la génération de {d}')
    open(os.path.join(out, 'gen.log'), 'w').write(r.stdout + r.stderr)
    return out


# ---------------------------------------------------------------- Markdown
def seg_md(segs):
    o = ''
    for s in segs:
        o += f'[{TY(s["t"])}]({s["href"]})' if s.get('href') else TY(s['t'])
    return re.sub(r'\s+', ' ', o).strip()


def seg_txt(segs):
    o = ''
    for s in segs:
        o += f'{TY(s["t"])} <{s["href"]}>' if s.get('href') else TY(s['t'])
    return re.sub(r'\s+', ' ', o).strip()


def sum_md(sm, ind='  '):
    L = []
    if sm.get('titre'): L.append(f'{ind}- **Synthèse : {TY(sm["titre"])}**')
    for k, lab in (('statut', 'Statut'), ('fonctions', 'Fonctions concernées'), ('contexte', 'Contexte'), ('essentiel', 'Résumé')):
        if sm.get(k): L.append(f'{ind}  - {lab} : {TY(sm[k])}')
    imp = ' '.join(TY(sm[k]) for k in ('impact_avere', 'impact_potentiel') if sm.get(k))
    if imp: L.append(f'{ind}  - Impact : {imp}')
    for q in sm.get('a_verifier') or []: L.append(f'{ind}  - À vérifier : {TY(q)}')
    return L


def to_md(blocks, meta, text=False):
    """Markdown complet (synthèses comprises) ; text=True : partie texte de l'e-mail (sans synthèses)."""
    S = seg_txt if text else seg_md
    L = [f'# Software Compliance — N° {meta["n"]} — {meta["date"]}', '']
    if text:
        L += [f'Version enrichie (synthèses) : {URL}/{meta["date_iso"]}/']
        if episode(meta['date_iso']): L += [f'Écouter l’épisode audio : {URL}/{meta["date_iso"]}/#ecouter']
        L += ['']
    sec, rap, first = '', [], True

    def line(segs, a, sm):
        d = (a or {}).get('date')
        t = '- ' + S(segs) + (f' — {fdate_long(d)}' if d else '')
        return [t] + ([] if text or not sm else sum_md(sm))

    def flush():
        if rap:
            L.extend(['', '### Rappels', ''])
            for x in rap: L.extend(line(*x))
            rap.clear()
    for b in blocks:
        k = b['k']
        if k == 'h2':
            flush()
            sec = ''.join(x['t'] for x in b['i']).strip()
            if sec.startswith(('Audit', 'Sources')): break
            L += ['', f'## {TY(sec)}', '']
        elif k == 'p':
            raw = ''.join(x['t'] for x in b['i']).strip(' ·')
            if not raw or sec.startswith('Agenda') or raw.startswith('Cette section ne retient'): continue
            if first:
                first = False; L += [f'> {S(b["i"])}', '']; continue
            a = b.get('attrs') or {}
            if a.get('rappel'): rap.append((b['i'], a, b.get('sum'))); continue
            if b.get('sum') or a: L.extend(line(b['i'], a, b.get('sum')))
            else: L += [S(b['i']), '']
        elif k == 'ul':
            sums = b.get('sum') or []; ats = b.get('attrs') or []
            for j, it in enumerate(b['items']):
                a = (ats[j] if j < len(ats) else None) or {}; sm = sums[j] if j < len(sums) else None
                if a.get('rappel'): rap.append((it, a, sm))
                else: L.extend(line(it, a, sm))
            L.append('')
        elif k == 'table' and 'Date' in ''.join(x['t'] for x in b['rows'][0][0]):
            sums = b.get('sum') or []
            refs = meta.get('agenda_refs') or []
            for j, r in enumerate(b['rows'][1:]):
                u = ''.join(x.get('href', '') for x in r[1]) or (refs[j] if j < len(refs) else '')
                txt = TY(''.join(x['t'] for x in r[1]))
                lien = (f' <{u}>' if text else f' ([référence]({u}))') if u else ''
                L.append(f'- **{TY("".join(x["t"] for x in r[0]))}** — {txt} ({TY("".join(x["t"] for x in r[2]))}){lien}')
                sm = sums[j] if j < len(sums) else None
                if sm and not text: L.extend(sum_md(sm))
            L.append('')
    flush()
    L += ['', '---', f'Édition web : {URL}/{meta["date_iso"]}/' + ('' if text else f' · Archives : {URL}/archives/ · Dossiers : {URL}/dossiers/ · RSS : {URL}/feed.xml')]
    out = '\n'.join(L)
    return re.sub(r'\n{3,}', '\n\n', out).strip() + '\n'


# ---------------------------------------------------------------- pages annexes
CSS = f'''body{{margin:0;background:#ecebe6 url(/assets/fond.webp) repeat;background-size:512px 512px;color:#1f2937;font:16px/24px {SERIF}}}
.c{{max-width:720px;margin:24px auto;background:#fff;border-top:6px solid #c2410c;padding:38px 52px 44px;box-sizing:border-box}}
.e{{font:600 12px/16px {SANS};letter-spacing:.16em;text-transform:uppercase;color:#c2410c}}
h1{{margin:8px 0 14px;font:700 46px/52px {SERIF};color:#0f2a4a;letter-spacing:-.01em;text-wrap:balance}} h1 i{{font-weight:400;color:#c2410c}} h1 span{{font:500 44px/52px {SANS};letter-spacing:-.025em}} h1.dos{{font-size:44px;line-height:50px}} h1.dos span{{font-size:42px;line-height:50px}}
.pied{{margin:44px 0 0;padding:16px 0 0;border-top:2px solid #0f2a4a;font:12px/19px {SANS};color:#6b7280}}
.sub{{margin:0 0 24px;padding-bottom:14px;border-bottom:2px solid #0f2a4a;font:13px/20px {SANS};color:#6b7280}} .sub a{{color:#6b7280}}
h2{{margin:32px 0 12px;font:600 20px/28px {SANS};color:#0f2a4a}} .r{{width:30px;height:3px;background:#c2410c;margin:32px 0 10px}} .r+h2{{margin-top:0}}
ul.l{{list-style:none;margin:0;padding:0}} ul.l>li{{border-bottom:1px solid #e5e1d8}}
ul.l a.b{{display:block;padding:14px 4px;color:#1f2937;text-decoration:none}} ul.l a.b:hover,ul.l a.b:focus-visible{{background:#faf7f0;outline:none}}
.m{{display:block;font:600 13px/20px {SANS};color:#c2410c}} .x{{display:block;margin-top:2px}} .n{{font:13px/20px {SANS};color:#6b7280}}
nav.d{{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 8px}} nav.d a{{font:600 12px/18px {SANS};color:#7d6c47;border:1px solid #d9cfb6;border-radius:11px;padding:1px 10px;text-decoration:none}} nav.d a.on,nav.d a:hover{{background:#c2410c;border-color:#c2410c;color:#fff}}
dl.st{{display:grid;grid-template-columns:max-content 1fr;gap:4px 16px;margin:0;padding:12px 16px;background:#f7f4ee;font:13px/19px {SANS};color:#374151}} dl.st dt{{color:#7d6c47;font-weight:600}} dl.st dd{{margin:0;min-width:0}}
ul.tl{{list-style:none;margin:0 0 0 16px;padding:0 0 0 14px;border-left:2px solid #e3ddd0}} ul.tl li{{position:relative;display:grid;grid-template-columns:112px 1fr;margin:0 0 10px;padding-left:16px;font-size:15px;line-height:22px}}
ul.tl li.sy-it{{margin-left:-6px;padding:2px 6px 2px 22px;border-radius:6px}} ul.tl li.sy-it::before{{left:-15px;top:9px}}
ul.it li.sy-it{{margin:0 -8px;padding:10px 8px 12px;border-radius:6px}} ul.it li.sy-it:hover{{border-bottom-color:transparent}}
ul.tl li::before{{content:"";position:absolute;left:-21px;top:7px;width:8px;height:8px;background:#c2410c;border:2px solid #fff}} ul.tl li.v::before{{background:#fff;border-color:#c2410c}}
.dt{{display:block;font:600 13px/22px {SANS};color:#c2410c}}
ul.it{{list-style:none;margin:0;padding:0}} ul.it li{{padding:10px 0 12px;border-bottom:1px solid #eee9de}}
.sec{{display:block;font:600 11px/16px {SANS};letter-spacing:.1em;text-transform:uppercase;color:#8a8f98;margin:0 0 3px}}
.ed{{font:600 12px/16px {SANS};letter-spacing:.14em;text-transform:uppercase;color:#0f2a4a;margin:24px 0 4px}}
a.s{{color:#6b7280;font:13px {SANS};text-decoration:none;border-bottom:1px dotted #9ca3af}} a.s.so{{font-weight:600}}
a.t{{border-bottom:1px dotted #1f4e8c;color:#1f4e8c;text-decoration:none;position:relative;cursor:help}}
a.t:hover::after,a.t:focus::after{{content:attr(data-tip);position:absolute;left:0;top:1.7em;z-index:9;width:min(290px,70vw);background:#0f2a4a;color:#fff;font:400 13px/1.45 {SANS};padding:9px 11px;border-radius:6px}}
a.more{{color:#c2410c;font:600 13px {SANS};text-decoration:none;white-space:nowrap}}
.demo{{font:600 11px/16px {SANS};color:#8a8f98;letter-spacing:.06em;text-transform:uppercase}}
@media(max-width:660px){{.c{{margin:0;padding:24px 18px 30px}} h1{{font-size:36px;line-height:42px}} h1 span{{font-size:34px;line-height:42px}} dl.st{{grid-template-columns:1fr;gap:0}} dl.st dd{{margin-bottom:6px}}}}'''


REDACTION = 'Anthropic Claude Opus 5.5'   # remplacé par la valeur « redaction » de la dernière édition


def titre(nom, spec=None):
    """Titre façon page principale. spec (« titre » dans themes.json) : « partie en italique|suite »,
    coupé entre deux blocs de sens ; sans spec, tout le nom en sans-serif."""
    if spec and '|' in spec:
        a, b = spec.split('|', 1)
        return f'<i>{E(a)}</i> <span>{E(b)}</span>'
    return f'<span>{E(spec or nom)}</span>'


SYN = {}   # styles, script et pastille de la fenêtre « En savoir plus » (gen.py, syn.json de la dernière édition)


def page(title, eyebrow, h1, sub, body, cls='', syn=''):
    """syn : contenus des fenêtres « En savoir plus » de la page (la fenêtre et ses scripts ne sont ajoutés que s'il y en a)"""
    css = CSS + ('\n' + SYN.get('css', '') if syn else '')
    fin = (syn + SYN.get('js', '') + SYN.get('pill', '')) if syn else ''
    return f'''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><meta name="color-scheme" content="light"><title>{E(title)}</title><link rel="alternate" type="application/rss+xml" title="Software Compliance" href="/feed.xml"><style>{css}</style></head>
<body><main class="c"><div class="e">{eyebrow}</div><h1{f' class="{cls}"' if cls else ''}>{h1}</h1><p class="sub">{sub}</p>{body}<p class="pied">Ce document a été rédigé par une intelligence artificielle ({E(REDACTION)}). Des erreurs sont possibles.</p></main>{fin}</body></html>'''


def write(path, txt):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write(txt)


def main():
    if os.path.isdir(SITE): shutil.rmtree(SITE)
    os.makedirs(SITE)
    eds = editions()
    if not eds:   # aucune édition (remise à zéro) : site d'attente, archives et flux vides
        attente = 'La première édition paraîtra un vendredi matin. Les archives, les dossiers et les flux se rempliront à partir de là.'
        write(os.path.join(SITE, 'index.html'), page('Software Compliance', 'Revue de presse hebdomadaire', '<i>Software</i> <span>Compliance</span>', 'Première édition à paraître', f'<p>{attente}</p>'))
        write(os.path.join(SITE, 'archives', 'index.html'), page('Archives · Software Compliance', 'Revue de presse hebdomadaire', '<i>Software</i> <span>Compliance</span>', 'Archives · aucune édition · <a href="/">Accueil</a>', '<ul class="l"></ul>'))
        write(os.path.join(SITE, 'dossiers', 'index.html'), page('Dossiers · Software Compliance', 'Revue de presse hebdomadaire', 'Dossiers', 'Aucun dossier pour l’instant · <a href="/">Accueil</a>', ''))
        vide = lambda t, d, x='': f'<?xml version="1.0" encoding="utf-8"?>\n<rss version="2.0"{x}><channel><title>{t}</title><link>{URL}/</link><description>{d}</description><language>fr</language></channel></rss>\n'
        write(os.path.join(SITE, 'feed.xml'), vide('Software Compliance', 'Revue de presse hebdomadaire sur la conformité logicielle des produits, pour l’industrie de défense.'))
        write(os.path.join(SITE, 'podcast.xml'), vide(E(POD_TITRE), E(POD_DESC), ' xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"'))
        write(os.path.join(SITE, 'llms.txt'), '# Software Compliance\n\n> Revue de presse hebdomadaire sur la conformité logicielle des produits pour l’industrie de défense.\n\n## Éditions\n\n- Première édition à paraître.\n')
        write(os.path.join(SITE, 'CNAME'), 'revue.dejeun.es\n')
        print('Aucune édition : site d’attente construit'); return
    infos = []
    for d in eds:
        blocks, meta = load(d)
        out = run_gen(d)
        write(os.path.join(SITE, d, 'index.html'), open(os.path.join(out, 'revue-web.html'), encoding='utf-8').read())
        md = to_md(blocks, meta)
        write(os.path.join(SITE, d, 'index.md'), md)
        ep = episode(d)
        if ep: shutil.copyfile(os.path.join(CONTENT, d, ep['fichier']), os.path.join(SITE, d, ep['fichier']))
        write(os.path.join(out, 'revue-email.txt'), to_md(blocks, meta, text=True))
        lede = next((TY(''.join(x['t'] for x in b['i']).strip(' ·')) for b in blocks if b['k'] == 'p' and ''.join(x['t'] for x in b['i']).strip(' ·')), '')
        infos.append({'d': d, 'meta': meta, 'lede': lede, 'items': json.load(open(os.path.join(out, 'items.json'), encoding='utf-8')), 'md': md})
        if os.path.isfile(os.path.join(out, 'syn.json')): SYN.update(json.load(open(os.path.join(out, 'syn.json'), encoding='utf-8')))
    last = infos[-1]
    global REDACTION
    REDACTION = last['meta'].get('redaction') or REDACTION
    web = open(os.path.join(SITE, last['d'], 'index.html'), encoding='utf-8').read()
    write(os.path.join(SITE, 'index.html'), web.replace('<meta charset="utf-8">', f'<meta charset="utf-8"><link rel="canonical" href="/{last["d"]}/">', 1))
    write(os.path.join(SITE, 'index.md'), last['md'])

    # archives
    rows = ''.join(f'<li><a class="b" href="/{i["d"]}/"><span class="m">N° {i["meta"]["n"]} · {E(i["meta"]["date_long"])}{" · démonstration" if i["meta"].get("demo") else ""}</span><span class="x">{E(i["lede"])}</span></a></li>' for i in reversed(infos))
    n = len(infos)
    write(os.path.join(SITE, 'archives', 'index.html'), page('Archives · Software Compliance', 'Revue de presse hebdomadaire', '<i>Software</i> <span>Compliance</span>',
          f'Archives · {n} édition{"s" if n > 1 else ""} · <a href="/">Dernière édition</a> · <a href="/dossiers/">Dossiers</a> · <a href="/feed.xml">RSS</a>', f'<ul class="l">{rows}</ul>'))

    # dossiers
    themes = json.load(open(os.path.join(TOOLS, 'themes.json'), encoding='utf-8'))
    today = datetime.date.today().isoformat()
    by = {k: [] for k in themes}
    for i in infos:
        for it in i['items']:
            for t in it.get('themes') or []:
                if t in by: by[t].append((i, it))
    nav = lambda cur: '<nav class="d">' + ''.join(f'<a{" class=on" if k == cur else ""} href="/dossiers/{k}/">{E(v["court"])}</a>' for k, v in themes.items() if by[k] or v.get('chronologie')) + '</nav>'
    idx = []
    for k, v in themes.items():
        its = by[k]
        if not its and not v.get('chronologie'): continue
        maj = max((i['meta']['date'] for i, _ in its), key=lambda x: x, default='')
        dmaj = max((i['d'] for i, _ in its), default='')
        idx.append(f'<li><a class="b" href="/dossiers/{k}/"><span class="m">{E(v["nom"])}</span><span class="x">{E(TY(v.get("reference", "")))}</span><span class="n">{len(its)} information{"s" if len(its) > 1 else ""}{" · mis à jour le " + fdate_long(dmaj) if dmaj else ""}</span></a></li>')
        body = nav(k)
        st = [(lab, v.get(f)) for f, lab in (('statut', 'Statut'), ('fonctions', 'Fonctions concernées'), ('defense', 'Défense')) if v.get(f)]
        if st:
            body += '<div class="r"></div><h2>État du dossier</h2><dl class="st">' + ''.join(f'<dt>{lab}</dt><dd>{E(TY(x))}</dd>' for lab, x in st) + '</dl>'
        syn = {}   # fenêtres « En savoir plus » de la page : identifiant unique (date de l'édition + sid) -> contenu
        def sid_de(i, it):
            if not (it.get('sid') and it.get('syn')): return None
            u = f'{i["d"]}-{it["sid"]}'; syn[u] = it['syn']; return u
        par_date = {}   # événement de chronologie couvert par une synthèse : même date qu'un élément publié du dossier
        for i, it in sorted(its, key=lambda x: x[0]['d'], reverse=True):
            if it.get('date') and it.get('syn'): par_date.setdefault(it['date'], (i, it))
        if v.get('chronologie'):
            li = []
            for c in sorted(v['chronologie'], key=lambda c: c['date']):
                u = sid_de(*par_date[c['date']]) if c['date'] in par_date else None
                cl = ' '.join(x for x in ('v' if c['date'] > today else '', 'sy-it' if u else '') if x)
                att = f' class="{cl}"' if cl else ''
                if u: att += f' data-syn="{u}"'
                li.append(f'<li{att}><span class="dt">{E(c.get("libelle") or fdate_court(c["date"]))}</span><span>{E(TY(c["texte"]))}{" " + SYN.get("synb", "").format(u) if u else ""}</span></li>')
            body += '<div class="r"></div><h2>Chronologie</h2><ul class="tl">' + ''.join(li) + '</ul>'
        if its:
            body += '<div class="r"></div><h2>Informations publiées</h2>'
            cur = None
            for i, it in sorted(its, key=lambda x: x[0]['d'], reverse=True):
                if i['d'] != cur:
                    if cur: body += '</ul>'
                    cur = i['d']
                    body += f'<p class="ed">N° {i["meta"]["n"]} · {E(i["meta"]["date"])}{" <span class=demo>· démonstration</span>" if i["meta"].get("demo") else ""}</p><ul class="it">'
                lab = 'Agenda · ' + it.get('label', '') if it['kind'] == 'agenda' else it['sec'].split(' : ')[0] + (' · rappel' if it.get('rappel') else '')
                u = sid_de(i, it)
                if u and SYN.get('synb'): body += f'<li class="sy-it" data-syn="{u}"><span class="sec">{E(lab)}</span>{it["html"]} {SYN["synb"].format(u)}</li>'
                else:
                    more = f' <a class="more" href="/{i["d"]}/#{it["sid"]}">En savoir plus ↗</a>' if it.get('sid') else ''
                    body += f'<li><span class="sec">{E(lab)}</span>{it["html"]}{more}</li>'
            body += '</ul>'
        write(os.path.join(SITE, 'dossiers', k, 'index.html'), page(f'{v["nom"]} · Dossiers · Software Compliance', 'Dossier', titre(v['nom'], v.get('titre')),
              f'{E(TY(v.get("reference", "")))}<br>{len(its)} information{"s" if len(its) > 1 else ""} · <a href="/dossiers/">Tous les dossiers</a> · <a href="/">Dernière édition</a>', body, cls='dos',
              syn=''.join(f'<div class="sy-d" id="d-{u}" hidden>{h}</div>' for u, h in syn.items())))
    write(os.path.join(SITE, 'dossiers', 'index.html'), page('Dossiers · Software Compliance', 'Revue de presse hebdomadaire', titre('Dossiers'),
          'Tout ce que la revue a publié, thème par thème · <a href="/">Dernière édition</a> · <a href="/archives/">Archives</a>', f'<ul class="l">{"".join(idx)}</ul>'))

    # RSS (hors démonstration)
    pub = [i for i in infos if not i['meta'].get('demo')]
    def rfc(d): return datetime.datetime.strptime(d, '%Y-%m-%d').replace(hour=5, minute=30).strftime('%a, %d %b %Y %H:%M:%S +0000')
    items = ''.join(f'''<item><title>{E(f"N° {i['meta']['n']} — {i['meta']['date']}")}</title><link>{URL}/{i['d']}/</link><guid isPermaLink="true">{URL}/{i['d']}/</guid><pubDate>{rfc(i['d'])}</pubDate><description>{E(i['lede'])}</description></item>''' for i in reversed(pub))
    write(os.path.join(SITE, 'feed.xml'), f'''<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>Software Compliance</title><link>{URL}/</link><atom:link href="{URL}/feed.xml" rel="self" type="application/rss+xml"/><description>Revue de presse hebdomadaire sur la conformité logicielle des produits, pour l’industrie de défense.</description><language>fr</language>{IMG_FLUX}{items}</channel></rss>
''')

    # flux du podcast (hors démonstration)
    eps = [(i, episode(i['d'])) for i in pub if episode(i['d'])]
    def duree(s): return f'{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}'
    def pod(i):
        p = json.load(open(os.path.join(CONTENT, i['d'], 'podcast.json'), encoding='utf-8'))
        return p['titre'], p['description']
    pitems = ''.join(f'''<item><title>{E(TY(titre_episode(i['meta']['n'], pod(i)[0])))}</title><link>{URL}/{i['d']}/#ecouter</link><guid isPermaLink="false">{URL}/{i['d']}/episode</guid><pubDate>{rfc(i['d'])}</pubDate><description>{E(TY(pod(i)[1]))}</description><enclosure url="{URL}/{i['d']}/{ep['fichier']}" length="{ep['octets']}" type="{'audio/mp4' if ep['fichier'].endswith('.m4a') else 'audio/mpeg'}"/><itunes:duration>{duree(ep['duree_s'])}</itunes:duration><itunes:episode>{i['meta']['n']}</itunes:episode><itunes:explicit>false</itunes:explicit></item>''' for i, ep in reversed(eps))
    write(os.path.join(SITE, 'podcast.xml'), f'''<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"><channel><title>{E(POD_TITRE)}</title><link>{URL}/</link><atom:link href="{URL}/podcast.xml" rel="self" type="application/rss+xml"/><description>{E(POD_DESC)}</description>{IMG_POD}<language>fr</language><itunes:author>Software Compliance</itunes:author><itunes:explicit>false</itunes:explicit><itunes:category text="Technology"/><itunes:type>episodic</itunes:type>{pitems}</channel></rss>
''')

    # llms.txt (hors démonstration)
    L = ['# Software Compliance', '', '> Revue de presse hebdomadaire, en français, sur la maîtrise de la conformité logicielle des produits fabriqués par un industriel de la défense : Cyber Resilience Act, SBOM, analyse de composition logicielle, licences open source, contrôle des exportations et sanctions appliqués au logiciel.', '',
         'Chaque édition existe en Markdown (synthèses comprises) à l’adresse /AAAA-MM-JJ/index.md. Les sources sont citées en lien pour chaque information.', '', '## Éditions', '']
    L += [f'- [N° {i["meta"]["n"]} — {i["meta"]["date"]}]({URL}/{i["d"]}/index.md): {i["lede"]}' for i in reversed(pub)] or ['- Première édition à paraître.']
    L += ['', '## Dossiers thématiques', ''] + [f'- [{v["nom"]}]({URL}/dossiers/{k}/): {TY(v.get("reference", ""))}' for k, v in themes.items() if by[k]]
    write(os.path.join(SITE, 'llms.txt'), '\n'.join(L) + '\n')

    if os.path.isfile(os.path.join(TOOLS, 'fond.webp')):   # fond de page répété
        os.makedirs(os.path.join(SITE, 'assets'), exist_ok=True); shutil.copyfile(os.path.join(TOOLS, 'fond.webp'), os.path.join(SITE, 'assets', 'fond.webp'))
    for x in ('webp', 'png', 'jpg'):   # image d'en-tête facultative (tools/en-tete.*)
        f = os.path.join(TOOLS, f'en-tete.{x}')
        if os.path.isfile(f): os.makedirs(os.path.join(SITE, 'assets'), exist_ok=True); shutil.copyfile(f, os.path.join(SITE, 'assets', f'en-tete.{x}'))
    for f in IMAGES_FLUX:   # visuels des flux RSS (tools/flux.jpg, flux-144.png, podcast.jpg)
        if os.path.isfile(os.path.join(TOOLS, f)): os.makedirs(os.path.join(SITE, 'assets'), exist_ok=True); shutil.copyfile(os.path.join(TOOLS, f), os.path.join(SITE, 'assets', f))
    write(os.path.join(SITE, 'CNAME'), 'revue.dejeun.es\n')
    write(os.path.join(SITE, '.nojekyll'), '')
    print(f'Site construit : {len(infos)} édition(s), {len(idx)} dossier(s) -> {SITE}')


if __name__ == '__main__':
    main()
