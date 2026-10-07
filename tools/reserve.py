#!/usr/bin/env python3
"""Réserve d'articles (README, § 5) : retrait automatique des articles mis en réserve depuis plus de 21 jours.

Lancé par la routine au début de chaque numéro (README, § 7, étape 1), avant la lecture de la réserve. Les articles
retirés quittent veille/reserve.json et sont consignés dans veille/reserve-retraits.md (date, sujet, ancienneté), que le
journal de veille reprend.

  python3 tools/reserve.py 2026-10-13      # date de l'édition en préparation (défaut : aujourd'hui)
"""
import datetime, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESERVE = os.path.join(ROOT, 'veille', 'reserve.json')
RETRAITS = os.path.join(ROOT, 'veille', 'reserve-retraits.md')
MAX_JOURS = 21


def main():
    d = datetime.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime.date.today()
    res = json.load(open(RESERVE, encoding='utf-8')) if os.path.isfile(RESERVE) else []
    garde, retire = [], []
    for r in res:
        try: j = (d - datetime.date.fromisoformat(r['mis_en_reserve'])).days
        except (KeyError, ValueError): j = MAX_JOURS + 1   # date absente ou illisible : retiré
        (retire if j > MAX_JOURS else garde).append((j, r))
    if retire:
        json.dump([r for _, r in garde], open(RESERVE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        neuf = not os.path.isfile(RETRAITS)
        with open(RETRAITS, 'a', encoding='utf-8') as f:
            if neuf: f.write('# Articles retirés de la réserve (plus de 21 jours)\n\n| Retiré le | Sujet | Rubrique | Mis en réserve | Jours |\n|---|---|---|---|---|\n')
            for j, r in retire:
                f.write(f"| {d.isoformat()} | {r.get('sujet', '?')} | {r.get('rubrique', '')} | {r.get('mis_en_reserve', '?')} | {j} |\n")
    print(f'Réserve au {d.isoformat()} : {len(garde)} article(s) gardé(s), {len(retire)} retiré(s) (plus de {MAX_JOURS} jours).')
    for j, r in retire: print(f"  retiré : {r.get('sujet', '?')} ({j} jours)")


if __name__ == '__main__':
    main()
