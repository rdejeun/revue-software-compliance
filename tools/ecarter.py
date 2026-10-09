#!/usr/bin/env python3
"""Écarte d'une édition les informations dont la vérification est douteuse : affirmation « non confirmée » de claims.json
ou extrait introuvable dans sa source (page lue). La revue n'est jamais bloquée pour cela (README, § 3 et § 7).

Usage : python3 tools/ecarter.py [AAAA-MM-JJ] [--appliquer]
  sans --appliquer : liste seulement ce qui serait écarté (aucun fichier modifié)
  --appliquer      : retire les éléments de blocks.json (puce, paragraphe « Défense », ligne d'agenda), leurs affirmations de
                     claims.json, les rubriques devenues vides ; écrit le journal veille/ecartes/AAAA-MM-JJ.md
Un élément est retrouvé par le champ facultatif « ref » de l'affirmation (début du texte de l'élément), à défaut par l'adresse
de la source (si une seule puce la cite). Une affirmation qu'on ne peut pas rattacher à un élément, ou une page illisible
(PDF, accès refusé), est signalée sans rien retirer. Une édition déjà envoyée (envoi.json) n'est jamais modifiée. Code de sortie : 0 (toujours, sauf erreur de lecture des fichiers)."""
import datetime, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import validate as V


def plat(segs):
    return V.norme(re.sub(r'\*\{[a-z]{2,3}\}|\*|==', '', ''.join(s.get('t', '') for s in segs)))


def liens(segs):
    return {norm_url(s['href']) for s in segs if s.get('href')}


def norm_url(u):
    return (u or '').split('#')[0].rstrip('/').lower()


def elements(blocks, meta):
    """Liste des éléments retirables : {kind, b, j, texte, urls}."""
    out = []; refs = meta.get('agenda_refs') or []
    for bi, b in enumerate(blocks):
        if b['k'] == 'ul':
            for j, it in enumerate(b['items']): out.append({'kind': 'ul', 'b': bi, 'j': j, 'texte': plat(it), 'urls': liens(it)})
        elif b['k'] == 'p' and b.get('attrs') is not None:
            out.append({'kind': 'p', 'b': bi, 'j': 0, 'texte': plat(b['i']), 'urls': liens(b['i'])})
        elif b['k'] == 'table' and 'Date' in ''.join(x['t'] for x in b['rows'][0][0]):
            for j, r in enumerate(b['rows'][1:]):
                u = liens(r[1]) | ({norm_url(refs[j])} if j < len(refs) and refs[j] else set())
                out.append({'kind': 'agenda', 'b': bi, 'j': j, 'texte': plat(r[0] + [{'t': ' '}] + r[1]), 'urls': u})
    return out


def rattacher(c, els):
    """Élément concerné par l'affirmation c : un seul candidat, sinon None."""
    if c.get('ou') == 'podcast': return None
    ref = V.norme(c.get('ref') or '')
    if ref:
        cand = [e for e in els if e['texte'].startswith(ref) or ref in e['texte'][:220]]
        return cand[0] if len(cand) == 1 else None
    u = norm_url(c.get('url'))
    cand = [e for e in els if u and u in e['urls']]
    if len(cand) > 1 and c.get('ou') == 'article': cand = [e for e in cand if e['kind'] in ('ul', 'p')]   # la même source peut être citée par la puce et par l'agenda
    if len(cand) > 1 and c.get('ou') == 'agenda': cand = [e for e in cand if e['kind'] == 'agenda']
    return cand[0] if len(cand) == 1 else None


def retirer(blocks, meta, a_retirer):
    """Retire les éléments (indices décroissants par bloc), puis les listes vides et les rubriques sans élément."""
    for e in sorted(a_retirer, key=lambda e: (e['b'], e['j']), reverse=True):
        b = blocks[e['b']]
        if e['kind'] == 'ul':
            for k in ('items', 'attrs', 'sum'):
                if k in b and e['j'] < len(b[k]): del b[k][e['j']]
        elif e['kind'] == 'p': b['_x'] = True
        else:
            del b['rows'][e['j'] + 1]
            for k in ('attrs', 'sum', 'detail'):
                if k in b and e['j'] < len(b[k]): del b[k][e['j']]
            if meta.get('agenda_refs') and e['j'] < len(meta['agenda_refs']): del meta['agenda_refs'][e['j']]
    blocks[:] = [b for b in blocks if not b.get('_x') and not (b['k'] == 'ul' and not b['items']) and not (b['k'] == 'table' and len(b['rows']) <= 1)]
    # rubriques sans élément : titre, chapô et libellé du sommaire retirés (README, § 5)
    sec = [i for i, b in enumerate(blocks) if b['k'] == 'h2']; supprimer = []; toc_a_retirer = []
    for n, i in enumerate(sec):
        fin = sec[n + 1] if n + 1 < len(sec) else len(blocks)
        corps = blocks[i + 1:fin]
        if not any(x['k'] in ('ul', 'table') or (x['k'] == 'p' and x.get('attrs') is not None) for x in corps):
            supprimer += list(range(i, fin)); toc_a_retirer.append(n)
    if supprimer:
        blocks[:] = [b for i, b in enumerate(blocks) if i not in set(supprimer)]
        if meta.get('toc'): meta['toc'] = [t for n, t in enumerate(meta['toc']) if n not in toc_a_retirer]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    content = os.path.join(ROOT, 'content')
    eds = sorted(x for x in os.listdir(content) if re.fullmatch(r'\d{4}-\d{2}-\d{2}', x))
    if not eds: print('Aucune édition.'); return
    d = args[0] if args else eds[-1]; appliquer = '--appliquer' in sys.argv
    dossier = os.path.join(content, d)
    if '--appliquer' in sys.argv and os.path.isfile(os.path.join(dossier, 'envoi.json')):
        print(f'{d} : édition déjà envoyée (envoi.json) : on ne la modifie jamais ; aperçu seulement.'); appliquer = False
    fb, fc, fm = (os.path.join(dossier, x) for x in ('blocks.json', 'claims.json', 'meta.json'))
    if not os.path.isfile(fc): print(f'{d} : pas de claims.json, rien à écarter.'); return
    blocks = json.load(open(fb, encoding='utf-8')); claims = json.load(open(fc, encoding='utf-8')); meta = json.load(open(fm, encoding='utf-8'))
    # affirmations en échec : non confirmées, ou extrait introuvable dans une page lue
    echecs = {i: 'non confirmée' for i, c in enumerate(claims, 1) if c.get('verifie') and c['verifie'] != 'confirmé'}
    ok = None
    if '--sans-reseau' not in sys.argv:
        ok, absents, illisibles = V.analyser_citations(claims)
        for i, raison in absents: echecs.setdefault(i, raison)
    else: illisibles = []
    els = elements(blocks, meta)
    par_element = {}; sans_element = []
    for i, raison in sorted(echecs.items()):
        e = rattacher(claims[i - 1], els)
        if e is None: sans_element.append((i, raison))
        else: par_element.setdefault((e['kind'], e['b'], e['j']), (e, [])) [1].append((i, raison))
    lignes = [f'# Informations écartées — édition du {d}', '', f'Contrôle du {datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")} : {len(echecs)} affirmation(s) en échec'
              + (f', {ok} extrait(s) retrouvé(s)' if ok is not None else '') + f', {len(illisibles)} page(s) non vérifiable(s) automatiquement.', '']
    if par_element:
        lignes += ['## Éléments retirés de l\'édition' if appliquer else '## Éléments qui seraient retirés (aperçu, rien n\'est modifié)', '']
        for (e, fails) in par_element.values():
            lignes.append(f'- **{e["texte"][:140]}…** ({e["kind"]})')
            for i, raison in fails: lignes.append(f'  - affirmation {i} ({raison}) : « {str(claims[i - 1].get("affirmation"))[:110]} » — {claims[i - 1].get("url")}')
        lignes.append('')
    if sans_element:
        lignes += ['## Affirmations en échec non rattachées à un élément (rien n\'est retiré : à examiner)', '']
        for i, raison in sans_element: lignes.append(f'- affirmation {i} ({raison}, {claims[i - 1].get("ou")}) : « {str(claims[i - 1].get("affirmation"))[:110]} » — {claims[i - 1].get("url")}')
        lignes.append('')
    pod = [i for i, c in enumerate(claims, 1) if c.get('ou') == 'podcast' and any(norm_url(c.get('url')) in e['urls'] for (e, _) in par_element.values())]
    if pod and par_element: lignes += ['## Podcast à relire', '', 'Des affirmations du podcast citent la source d\'un élément écarté : relire `podcast.json` (aucun fait absent de l\'édition).', '']
    if illisibles: lignes += ['## Pages non vérifiables automatiquement (PDF, accès refusé…)', ''] + [f'- affirmation {i} ({why}) : {claims[i - 1].get("url")}' for i, why in illisibles[:40]] + ['']
    txt = '\n'.join(lignes) + '\n'
    print(txt)
    if os.environ.get('GITHUB_STEP_SUMMARY'): open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8').write(txt)
    if os.environ.get('GITHUB_ACTIONS'):
        for (e, fails) in par_element.values(): print(f'::warning title=Information écartée ({d})::{e["texte"][:100]}')
        for i, raison in sans_element[:10]: print(f'::warning title=Vérification douteuse ({d})::affirmation {i} ({raison}) non rattachée à un élément')
    if not appliquer or not par_element:
        return
    cles = set(par_element)
    ids = {i for (_, fails) in par_element.values() for i, _ in fails}
    # affirmations des éléments retirés : retirées aussi (celles en échec, et les autres affirmations rattachées au même élément)
    for i, c in enumerate(claims, 1):
        e = rattacher(c, els)
        if e is not None and (e['kind'], e['b'], e['j']) in cles: ids.add(i)
    claims = [c for i, c in enumerate(claims, 1) if i not in ids]
    retirer(blocks, meta, [e for (e, _) in par_element.values()])
    json.dump(blocks, open(fb, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(meta, open(fm, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(claims, open(fc, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as o:
            o.write('ecartes=1\n')
            if pod: o.write('podcast_a_relire=1\n')   # le podcast cite la source d'un élément écarté : épisode non produit cette fois
    os.makedirs(os.path.join(ROOT, 'veille', 'ecartes'), exist_ok=True)
    open(os.path.join(ROOT, 'veille', 'ecartes', d + '.md'), 'w', encoding='utf-8').write(txt)
    print(f'{len(par_element)} élément(s) écarté(s) de l\'édition {d}.')


if __name__ == '__main__':
    main()
