#!/usr/bin/env python3
"""Conservation des preuves (README, § 3) : archive dans la Wayback Machine (Internet Archive, « Save Page Now »)
chaque source officielle citée par une édition, et chaque source de claims.json, puis note l'adresse de la copie et la
date dans content/AAAA-MM-JJ/archives.json. Non bloquant : une source non archivée (service indisponible, refus) est
retentée à la publication suivante.

  python3 tools/archiver.py                 # dernière édition
  python3 tools/archiver.py 2026-10-09 --max 40
"""
import argparse, datetime, json, os, re, sys, time, urllib.error, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from officiel import officiel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = 'Mozilla/5.0 (revue Software Compliance ; conservation des sources)'


def liens(d):
    """Sources à archiver : liens officiels de blocks.json et toutes les sources de claims.json."""
    c = os.path.join(ROOT, 'content', d); out = []
    def parcours(x):
        if isinstance(x, dict):
            if x.get('href') and officiel(x['href']): out.append(x['href'])
            for v in x.values(): parcours(v)
        elif isinstance(x, list):
            for v in x: parcours(v)
    parcours(json.load(open(os.path.join(c, 'blocks.json'), encoding='utf-8')))
    f = os.path.join(c, 'claims.json')
    if os.path.isfile(f): out += [a['url'] for a in json.load(open(f, encoding='utf-8')) if a.get('url')]
    return list(dict.fromkeys(u for u in out if u.startswith('http')))


def archiver(u):
    req = urllib.request.Request('https://web.archive.org/save/' + u, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        loc = r.headers.get('Content-Location') or ''
        fin = r.geturl()
    if loc.startswith('/web/'): return 'https://web.archive.org' + loc
    if re.match(r'https://web\.archive\.org/web/\d+', fin): return fin
    raise ValueError('adresse de la copie absente de la réponse')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('edition', nargs='?', help='AAAA-MM-JJ (défaut : dernière édition)')
    ap.add_argument('--max', type=int, default=60, help='nombre maximal de sources archivées par exécution')
    a = ap.parse_args()
    eds = sorted(x for x in os.listdir(os.path.join(ROOT, 'content')) if re.fullmatch(r'\d{4}-\d{2}-\d{2}', x))
    if not eds: print('Aucune édition.'); return
    d = a.edition or eds[-1]
    f = os.path.join(ROOT, 'content', d, 'archives.json')
    fait = json.load(open(f, encoding='utf-8')) if os.path.isfile(f) else {}
    a_faire = [u for u in liens(d) if u not in fait][:a.max]
    ok = ko = 0
    for u in a_faire:
        try:
            fait[u] = {'archive': archiver(u), 'le': datetime.date.today().isoformat()}; ok += 1
        except (urllib.error.URLError, OSError, ValueError) as e:
            ko += 1; print(f'non archivé : {u} ({type(e).__name__})', file=sys.stderr)
            if ko >= 3 and ok == 0: print('Service indisponible : arrêt, nouvel essai à la prochaine publication.', file=sys.stderr); break
        time.sleep(6)   # Save Page Now limite le débit des requêtes anonymes
        json.dump(fait, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{d} : {ok} source(s) archivée(s), {ko} en échec, {len(fait)} au total.')


if __name__ == '__main__':
    main()
