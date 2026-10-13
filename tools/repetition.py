#!/usr/bin/env python3
"""Répétition générale d'une édition, sans publication ni envoi, et sans aucun appel facturé à ElevenLabs (README, § 7 et § 9).

Usage :
  python3 tools/repetition.py [AAAA-MM-JJ]          répète l'édition (par défaut : la dernière) et écrit
                                                     veille/repetition/AAAA-MM-JJ.json et .md
  python3 tools/repetition.py --etat [AAAA-MM-JJ]   état de l'édition pour les routines (JSON) : répétition, figeage, épisode

La répétition exécute, dans les conditions de la publication (workflow « Répétition », sur le serveur qui lit GitHub) :
  1. tools/build_site.py ;
  2. tools/validate.py complet (liens et citations compris) ;
  3. tools/ecarter.py en aperçu (ce qui serait écarté, sujets du podcast touchés) ;
  4. tools/podcast.py --check ;
  5. tools/podcast.py --dry-run (toute la chaîne audio avec des voix synthétiques locales : aucun appel à ElevenLabs) ;
  6. tools/podcast.py --solde (lecture du solde ElevenLabs : gratuite).
Verdict « verte » si 2 et 4 réussissent, si 3 ne relève aucune affirmation en échec et si 5 réussit (le solde est signalé à part).
Le figeage du script (tools/podcast.py --figer) n'est possible qu'après une répétition verte. Code de sortie : 0 (le verdict est
dans le rapport et, dans GitHub Actions, dans la sortie « verdict »)."""
import datetime, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
CONTENT = os.path.join(ROOT, 'content')
sys.path.insert(0, HERE)


def editions():
    return sorted(x for x in os.listdir(CONTENT) if re.fullmatch(r'\d{4}-\d{2}-\d{2}', x))


def lancer(*cmd, timeout=1800):
    """-> (code, sortie fusionnée) ; la sortie est aussi recopiée dans le journal."""
    print(f'$ {" ".join(cmd)}', flush=True)
    try:
        r = subprocess.run([sys.executable, *cmd], cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or '') + (r.stderr or '')
        code = r.returncode
    except subprocess.TimeoutExpired as e:
        out, code = f'délai dépassé ({timeout} s)\n' + str(e.stdout or ''), 124
    print(out[-6000:], flush=True)
    return code, out


def commit():
    r = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True)
    return os.environ.get('GITHUB_SHA') or r.stdout.strip()


def repeter(d):
    import podcast as P
    t0 = datetime.datetime.now(datetime.timezone.utc)
    R = {'date': d, 'commit': commit(), 'le': t0.strftime('%Y-%m-%dT%H:%M:%SZ'), 'verdict': 'rouge', 'motifs': []}
    R['script'], R['sources'] = P.empreintes(d)

    code, _ = lancer('tools/build_site.py')
    if code: R['motifs'].append('construction du site en échec')

    code, out = lancer('tools/validate.py', d) if not code else (1, '')
    erreurs = re.findall(r'^- (.+)$', out.split('### Erreurs bloquantes', 1)[1].split('### Avertissements', 1)[0], re.M) if '### Erreurs bloquantes' in out else []
    avert = re.findall(r'^- (.+)$', out.split('### Avertissements', 1)[1], re.M) if '### Avertissements' in out else []
    R['controle'] = {'code': code, 'erreurs': erreurs, 'avertissements': avert}
    if code: R['motifs'].append(f'contrôle bloquant en échec ({len(erreurs)} erreur(s))')

    jf = os.path.join(ROOT, 'build', 'repetition', d + '-ecarter.json')
    code, _ = lancer('tools/ecarter.py', d, f'--json={jf}')
    try: E = json.load(open(jf, encoding='utf-8'))
    except (OSError, ValueError): E = {'echecs': None}
    R['ecarter'] = E
    if code or E.get('echecs') is None: R['motifs'].append('aperçu des informations à écarter impossible')
    elif E['echecs']: R['motifs'].append(f'{E["echecs"]} affirmation(s) en échec (extrait introuvable ou non confirmée) : {len(E.get("elements") or [])} élément(s) seraient écartés')

    if os.path.isfile(os.path.join(CONTENT, d, 'podcast.json')):
        code, out = lancer('tools/podcast.py', '--check', d)
        R['podcast'] = {'code': code, 'sortie': out.strip()[-2000:]}
        if code: R['motifs'].append('script du podcast invalide (podcast.py --check)')
        code, out = lancer('tools/podcast.py', '--dry-run', d, timeout=2400)
        m = re.search(r'contrôle (réussi|en écart)', out)
        R['essai_audio'] = {'code': code, 'controle': m.group(1) if m else None, 'sortie': out.strip()[-2000:]}
        if code: R['motifs'].append('chaîne audio en échec à blanc (podcast.py --dry-run) : voir le journal')
        code, out = lancer('tools/podcast.py', '--solde', d)
        try: R['solde'] = json.loads(out.strip().splitlines()[-1])
        except (ValueError, IndexError): R['solde'] = {'suffisant': None, 'raison': 'lecture impossible'}
    else:
        R['podcast'] = None; R['motifs'].append('pas de podcast.json')

    R['verdict'] = 'verte' if not R['motifs'] else 'rouge'
    R['duree_s'] = round((datetime.datetime.now(datetime.timezone.utc) - t0).total_seconds())
    ecrire(d, R)
    return R


def ecrire(d, R):
    dos = os.path.join(ROOT, 'veille', 'repetition'); os.makedirs(dos, exist_ok=True)
    json.dump(R, open(os.path.join(dos, d + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    E = R.get('ecarter') or {}
    L = [f'# Répétition de l’édition du {d}', '', f'Commit {R["commit"][:7]}, {R["le"]} ({R.get("duree_s", 0)} s) : **répétition {R["verdict"]}**.', '']
    if R['motifs']: L += ['## À corriger avant le figeage', ''] + [f'- {m}' for m in R['motifs']] + ['']
    if (R.get('controle') or {}).get('erreurs'): L += ['## Erreurs bloquantes du contrôle', ''] + [f'- {e}' for e in R['controle']['erreurs']] + ['']
    if E.get('elements'):
        L += ['## Éléments qui seraient écartés', '']
        for e in E['elements']:
            L.append(f'- **{e["texte"][:140]}…** ({e["kind"]})')
            L += [f'  - affirmation {a["n"]} ({a["raison"]}, {a["ou"]}) : « {str(a["affirmation"])[:110]} » — {a["url"]}' for a in e['affirmations']]
        L.append('')
    if E.get('sans_element'):
        L += ['## Affirmations en échec non rattachées à un élément (podcast compris)', ''] + [f'- affirmation {a["n"]} ({a["raison"]}, {a["ou"]}) : « {str(a["affirmation"])[:110]} » — {a["url"]}' for a in E['sans_element']] + ['']
    if E.get('sujets_podcast'): L += ['## Sujets du podcast à réécrire', ''] + [f'- {s}' for s in E['sujets_podcast']] + ['']
    S = R.get('solde') or {}
    if S: L += ['## Solde ElevenLabs (lecture seule)', '', f'- besoin du script (marge comprise) : {S.get("besoin")} caractères ; reste : {S.get("reste")} ; '
                + ('suffisant' if S.get('suffisant') else 'INSUFFISANT' if S.get('suffisant') is False else f'non lu ({S.get("raison")})') + (f' ; remise à zéro le {S["raz"]}' if S.get('raz') else ''), '']
    A = R.get('essai_audio') or {}
    if A: L += ['## Chaîne audio à blanc', '', f'- code {A.get("code")}, contrôle qualité (voix synthétiques, indicatif) : {A.get("controle")}', '']
    if (R.get('controle') or {}).get('avertissements'): L += ['## Avertissements du contrôle', ''] + [f'- {w}' for w in R['controle']['avertissements'][:40]] + ['']
    if E.get('illisibles'): L += ['## Pages non vérifiables automatiquement', ''] + [f'- affirmation {x["affirmation"]} ({x["raison"]}) : {x["url"]}' for x in E['illisibles'][:40]] + ['']
    txt = '\n'.join(L) + '\n'
    open(os.path.join(dos, d + '.md'), 'w', encoding='utf-8').write(txt)
    print(txt)
    if os.environ.get('GITHUB_STEP_SUMMARY'): open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8').write(txt)
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as o:
            o.write(f'verdict={R["verdict"]}\n'); o.write(f'resume={("; ".join(R["motifs"]) or "rien à corriger")[:130]}\n')


def etat(d):
    """État de l'édition pour les routines B et C : répétition, figeage, épisode, essais ; « pret » si la branche peut être fusionnée."""
    import podcast as P
    E = {'date': d, 'repetition': None, 'repetition_a_jour': False, 'fige': None, 'episode': None, 'essais': len(P.essais_lire(d)),
         'productions_max': P.PRODUCTIONS_MAX, 'pret_a_figer': False, 'pret_a_publier': False}
    f = os.path.join(ROOT, 'veille', 'repetition', d + '.json')
    if os.path.isfile(f):
        R = json.load(open(f, encoding='utf-8')); E['repetition'] = R.get('verdict'); E['commit_repetition'] = R.get('commit'); E['motifs'] = R.get('motifs')
        excl = [f':(exclude)content/{d}/podcast.fige.json', f':(exclude)content/{d}/episode.*']
        same = lambda *a: subprocess.run(['git', 'diff', '--quiet', *a, '--', 'content', 'tools', *excl], cwd=ROOT).returncode == 0
        E['repetition_a_jour'] = bool(R.get('commit')) and same(R['commit']) and same('HEAD')
    ok, F = P.fige_valide(d)
    E['fige'] = 'valide' if ok else F
    info = os.path.join(CONTENT, d, 'episode.json')
    if os.path.isfile(info) and os.path.isfile(os.path.join(CONTENT, d, 'episode.m4a')):
        M = json.load(open(info, encoding='utf-8'))
        E['episode'] = 'à jour' if ok and M.get('figeage') == F.get('commit_repetition', '')[:12] else 'ancien (figeage différent)'
    E['pret_a_figer'] = E['repetition'] == 'verte' and E['repetition_a_jour']
    E['pret_a_publier'] = E['pret_a_figer'] and E['episode'] == 'à jour'
    print(json.dumps(E, ensure_ascii=False, indent=1))


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    d = a[0] if a else editions()[-1]
    if '--etat' in sys.argv: etat(d); return
    R = repeter(d)
    print(f'Répétition {R["verdict"]} pour {d} ({R["commit"][:7]}).')


if __name__ == '__main__':
    main()
