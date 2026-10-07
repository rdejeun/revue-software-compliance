#!/usr/bin/env python3
"""Relevé systématique des sources de référence (README, § 7, étape 2).

Pour chaque source de tools/sources.json, liste les publications parues depuis la date donnée (par défaut, la
dernière édition de content/), avec titre, date et lien. Le relevé est une liste de candidats : l'agent les trie
(règle d'or), puis complète par la recherche générale. Une source qui ne répond pas est signalée « à consulter
manuellement », comme les sources sans flux.

  python3 tools/collecte.py                       # relevé depuis la dernière édition, sur la sortie standard
  python3 tools/collecte.py --depuis 2026-10-02 --sortie veille/collecte/2026-10-09.md
"""
import argparse, datetime, email.utils, json, os, re, sys, urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = 'Mozilla/5.0 (revue Software Compliance ; veille)'


def lire(url, n=30):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*'})
    with urllib.request.urlopen(req, timeout=n) as r:
        return r.read()


def jour(s):
    """Date d'un élément (RSS, Atom, ISO) -> datetime.date, ou None."""
    if not s: return None
    s = s.strip()
    try: return email.utils.parsedate_to_datetime(s).date()
    except (TypeError, ValueError): pass
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', s)
    return datetime.date(int(m[1]), int(m[2]), int(m[3])) if m else None


def flux(data):
    """Éléments d'un flux RSS 2.0 ou Atom : [(date, titre, lien)]."""
    racine = ET.fromstring(data); out = []
    for it in racine.iter():
        tag = it.tag.split('}')[-1]
        if tag not in ('item', 'entry'): continue
        def f(*noms):
            for c in it:
                if c.tag.split('}')[-1] in noms: return c
        t, d = f('title'), f('pubDate', 'published', 'updated', 'date')
        l = f('link'); lien = (l.get('href') or (l.text or '')).strip() if l is not None else ''
        out.append((jour(d.text if d is not None else ''), (t.text or '').strip() if t is not None else '', lien))
    return out


def releve(src, depuis):
    t, data = src['type'], lire(src['url'])
    if t in ('rss', 'github'): el = flux(data)
    elif t == 'federalregister':
        el = [(jour(d.get('publication_date')), f"{d.get('type', '')} : {d.get('title', '')}", d.get('html_url', '')) for d in json.loads(data).get('results', [])]
    elif t == 'kev':
        el = [(jour(v.get('dateAdded')), f"{v.get('cveID')} — {v.get('vendorProject')} {v.get('product')} : {v.get('vulnerabilityName')}",
               f"https://nvd.nist.gov/vuln/detail/{v.get('cveID')}") for v in json.loads(data).get('vulnerabilities', [])]
    elif t == 'euvd':
        d = json.loads(data); d = d.get('items', d) if isinstance(d, dict) else d
        el = [(jour(v.get('exploitedSince') or v.get('datePublished')), f"{v.get('id')} — {(v.get('description') or '')[:140]}",
               f"https://euvd.enisa.europa.eu/vulnerability/{v.get('id')}") for v in d]
    else: raise ValueError(f'type inconnu : {t}')
    filtre = re.compile(src['filtre'], re.I) if src.get('filtre') else None
    exclure = re.compile(src['exclure']) if src.get('exclure') else None
    return sorted([e for e in el if e[0] and e[0] >= depuis and (not filtre or filtre.search(e[1])) and not (exclure and exclure.search(e[2]))], reverse=True)


def derniere_edition():
    c = os.path.join(ROOT, 'content')
    eds = sorted(d for d in os.listdir(c) if re.fullmatch(r'\d{4}-\d{2}-\d{2}', d)) if os.path.isdir(c) else []
    return datetime.date.fromisoformat(eds[-1]) if eds else None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--depuis', help='AAAA-MM-JJ (défaut : date de la dernière édition, sinon il y a 7 jours)')
    ap.add_argument('--sortie', help='fichier Markdown (défaut : sortie standard)')
    a = ap.parse_args()
    depuis = datetime.date.fromisoformat(a.depuis) if a.depuis else (derniere_edition() or datetime.date.today() - datetime.timedelta(days=7))
    cfg = json.load(open(os.path.join(ROOT, 'tools', 'sources.json'), encoding='utf-8'))
    L = [f'# Relevé des sources de référence depuis le {depuis.isoformat()}', '',
         f'Produit le {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC par `tools/collecte.py`. Candidats à trier (règle d’or) ; '
         'les sources sans flux restent à consulter (fin du relevé).', '']
    echecs, total = [], 0
    for src in cfg['sources']:
        try: el = releve(src, depuis)
        except Exception as e:
            echecs.append(f"{src['nom']} ({type(e).__name__} : {str(e)[:80]})"); continue
        total += len(el)
        L += [f"## {src['nom']} ({len(el)})", '']
        L += [f'- {d.isoformat()} · [{t}]({u})' for d, t, u in el] or ['- Rien de nouveau.']
        L.append('')
    L += ['## À consulter manuellement', ''] + [f'- {e}' for e in echecs] + [f'- {m}' for m in cfg.get('manuelles', [])]
    txt = '\n'.join(L) + '\n'
    if a.sortie:
        os.makedirs(os.path.dirname(os.path.abspath(a.sortie)), exist_ok=True)
        open(a.sortie, 'w', encoding='utf-8').write(txt)
        print(f'{a.sortie} : {total} élément(s), {len(echecs)} source(s) en échec', file=sys.stderr)
    else: sys.stdout.write(txt)


if __name__ == '__main__':
    main()
