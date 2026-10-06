#!/usr/bin/env python3
"""Contrôle une édition avant publication et envoi.

Usage : python3 tools/validate.py [AAAA-MM-JJ] [--no-links]
  (par défaut : la dernière édition de content/ ; --no-links : sans vérification des liens)
À lancer après tools/build_site.py (lit build/AAAA-MM-JJ/).
Code de sortie 1 si une erreur bloquante est trouvée. Le rapport est écrit sur la sortie standard
et, dans GitHub Actions, dans le résumé de l'exécution.
"""
import concurrent.futures, datetime, html, json, os, re, socket, sys, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT, BUILD, TOOLS = (os.path.join(ROOT, x) for x in ('content', 'build', 'tools'))
JOURS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
ORIGINE = datetime.date(2026, 10, 5)   # lundi de la semaine du N° 1 (remise à zéro du 5 octobre 2026)
ERR, WARN = [], []
AGENDA_MAX = 8   # dates présentées dans l'agenda


def words(s): return len(re.findall(r"\w+(?:[’'-]\w+)*", re.sub(r'\*\{[a-z]{2,3}\}', '', s or '')))   # sans balise de langue de l'italique


def segs_ok(segs, where):
    if not isinstance(segs, list) or not segs:
        ERR.append(f'{where} : liste de segments vide ou invalide'); return False
    for s in segs:
        if not isinstance(s, dict) or not isinstance(s.get('t'), str):
            ERR.append(f'{where} : segment invalide {str(s)[:60]}'); return False
        if 'href' in s and not re.match(r'https?://', s['href'] or ''):
            ERR.append(f'{where} : lien invalide « {s.get("href")} »')
    return True


RESEAU_DEPUIS = '2026-10-09'   # « Connexion réseau » et « Modèle de licence » obligatoires pour les outils et services à partir de cette édition
RESEAU_VALEURS = ('Déconnecté', 'Connecté', 'Non documenté')
LICENCE_VALEURS = ('Open source', 'Commercial', 'Mixte', 'Gratuit', 'Non documenté')


def check_reseau(sm, where, d):
    """Outils et services : la synthèse porte « reseau » et « licence » (README, § 6)."""
    if not sm or d < RESEAU_DEPUIS: return
    r = sm.get('reseau') or ''
    if not r: ERR.append(f'{where} : synthèse sans « reseau » (connexion réseau de l’outil ou du service, README § 6)')
    elif not r.startswith(RESEAU_VALEURS): WARN.append(f'{where} : « reseau » doit commencer par « Déconnecté », « Connecté » ou « Non documenté »')
    l = sm.get('licence') or ''
    if not l: ERR.append(f'{where} : synthèse sans « licence » (modèle de licence de l’outil ou du service, README § 6)')
    elif not l.startswith(LICENCE_VALEURS): WARN.append(f'{where} : « licence » doit commencer par « Open source », « Commercial », « Mixte », « Gratuit » ou « Non documenté »')


def check_sum(sm, where):
    if sm is None: return
    if not isinstance(sm, dict): ERR.append(f'{where} : synthèse invalide'); return
    for k in ('titre', 'statut', 'fonctions', 'essentiel', 'contexte'):
        if not sm.get(k): ERR.append(f'{where} : synthèse sans « {k} »')
    if not (sm.get('impact_avere') or sm.get('impact_potentiel')): ERR.append(f'{where} : synthèse sans impact')
    av = sm.get('a_verifier') or []
    if not 2 <= len(av) <= 3: WARN.append(f'{where} : « À vérifier » contient {len(av)} question(s) (2 ou 3 attendues)')
    n = sum(words(sm.get(k)) for k in ('essentiel', 'contexte', 'impact_avere', 'impact_potentiel')) + sum(words(q) for q in av)
    if words(sm.get('essentiel')) > 120: WARN.append(f'{where} : résumé de {words(sm.get("essentiel"))} mots (120 au plus)')
    if not 140 <= n <= 275: WARN.append(f'{where} : synthèse de {n} mots (170 à 245 visés)')


def check_attrs(a, where, themes, need_date=True):
    if a is None: return
    if not isinstance(a, dict): ERR.append(f'{where} : attributs invalides'); return
    d = a.get('date')
    if d and not re.fullmatch(r'\d{4}-\d{2}(-\d{2})?', d): ERR.append(f'{where} : date « {d} » au mauvais format (AAAA-MM-JJ ou AAAA-MM)')
    if need_date and not d: WARN.append(f'{where} : élément sans date')
    for t in a.get('themes') or []:
        if t not in themes: ERR.append(f'{where} : thème inconnu « {t} » (voir tools/themes.json)')
    if not a.get('themes'): WARN.append(f'{where} : élément sans thème (absent des dossiers)')


def check_cles(blocks):
    """Mots-clés de lecture rapide (==…==, README § 4) : au plus un par article, aucun dans les rappels ni les débuts
    en gras ; dans une rubrique d'au moins trois articles, pas plus d'un article sur deux ; au plus un par synthèse."""
    sec, n, m = '', 0, 0
    def bilan():
        if n >= 3 and m * 2 > n: WARN.append(f'Rubrique « {sec} » : {m} articles sur {n} ont un mot-clé (un sur deux au plus)')
    for x in blocks:
        if x['k'] == 'h2':
            bilan(); sec, n, m = ''.join(z['t'] for z in x['i']), 0, 0; continue
        for sm in (x.get('sum') if isinstance(x.get('sum'), list) else [x.get('sum')]):   # synthèses : un passage au plus, dans le texte
            if not sm: continue
            hors = [k for k in ('titre', 'statut', 'fonctions', 'reseau', 'licence') if '==' in str(sm.get(k) or '')] + (['a_verifier'] if '==' in json.dumps(sm.get('a_verifier') or [], ensure_ascii=False) else [])
            if hors: WARN.append(f'Synthèse « {str(sm.get("titre"))[:50]} » : mot-clé hors du texte ({", ".join(hors)}), à retirer')
            k = sum(str(sm.get(c) or '').count('==') // 2 for c in ('contexte', 'essentiel', 'impact_avere', 'impact_potentiel'))
            if k > 1: WARN.append(f'Synthèse « {str(sm.get("titre"))[:50]} » : {k} mots-clés (un au plus)')
        if x['k'] == 'ul':
            at = x.get('attrs') or [{}] * len(x['items']); its = [(it, (at[i] or {}).get('rappel')) for i, it in enumerate(x['items'])]
        elif x['k'] == 'p' and x.get('attrs'): its = [(x['i'], x['attrs'].get('rappel'))]
        else: continue
        for it, rap in its:
            t = ''.join(z['t'] for z in it if not z.get('href')); k = t.count('==') // 2
            if rap:
                if k: WARN.append(f'Rubrique « {sec} » : mot-clé dans un rappel, à retirer : « {t[:60]}… »')
                continue
            n += 1; m += bool(k)
            if k > 1: WARN.append(f'Rubrique « {sec} » : {k} mots-clés dans un article (un au plus) : « {t[:60]}… »')
            if k and re.match(r'^[^:]{0,90}==', t.split(' : ')[0] + ' : ') : WARN.append(f'Mot-clé dans le début en gras : « {t[:60]}… »')
    bilan()


def check_content(d, blocks, meta, themes):
    check_cles(blocks)
    def chaines(x):
        if isinstance(x, str): yield x
        elif isinstance(x, dict): yield from (c for v in x.values() for c in chaines(v))
        elif isinstance(x, list): yield from (c for v in x for c in chaines(v))
    for c in chaines(blocks):   # italique *…* (README, § 4) : astérisques appariés
        if c.count('==') % 2: ERR.append(f'Mot-clé non refermé (== isolé) : « {c[:80]}… »')
        if c.count('*') % 2: ERR.append(f'Italique non refermée (astérisque isolé) : « {c[:80]}… »')
        for x in re.findall(r'(?<![*}])\b[A-Z]{2,}[A-Za-z0-9-]*\s\(([A-Z][a-z][\w-]*(?:\s(?:[A-Z][\w-]*|of|and|in|on|for|by|the|to))+)\)', c):   # README, § 4
            WARN.append(f'Développé anglais de sigle à mettre en italique (*{{en}}…*) : « {x} »')
        for x in re.findall(r'«\s([A-Z][^»]*?\s(?:on|over|for|by|of|in)\s[^»]*?)\s»', c):
            WARN.append(f'Nom étranger avec mots de liaison entre guillemets : en italique, sans guillemets (*{{en}}…*) : « {x} »')
        m = re.match(r'^([^:]{1,90}?)\s:', c)   # début en gras : la date de l'élément figure déjà en fin de ligne (README, § 12)
        if m and re.search(r'\((?:\d{1,2}(?:er)?\s)?(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s\d{4}\)', m.group(1)):
            WARN.append(f'Date entre parenthèses dans le début en gras (déjà affichée en fin d’élément) : « {m.group(1)} »')
    for k in ('n', 'date_iso', 'date_long', 'date', 'toc', 'site'):
        if k not in meta: ERR.append(f'meta.json : clé « {k} » manquante')
    if meta.get('date_iso') != d: ERR.append(f'meta.json : date_iso « {meta.get("date_iso")} » différente du dossier « {d} »')
    try:
        dt = datetime.date.fromisoformat(d)
        n = (dt - ORIGINE).days // 7 + 1
        if not meta.get('demo') and meta.get('n') != n: ERR.append(f'meta.json : n = {meta.get("n")}, attendu {n} pour le {d}')
        attendu = f'{JOURS[dt.weekday()]} {dt.day if dt.day > 1 else "1er"} {MOIS[dt.month - 1]} {dt.year}'
        if meta.get('date_long') != attendu: ERR.append(f'meta.json : date_long « {meta.get("date_long")} », attendu « {attendu} »')
    except ValueError:
        ERR.append(f'Nom de dossier « {d} » invalide')
    nsec = 0; sec = ''; nitems = nsum = 0; rap = {}; nb = {}   # nb : éléments par rubrique
    for i, b in enumerate(blocks):
        k = b.get('k'); w = f'bloc {i} ({k})'
        if k not in ('h1', 'h2', 'p', 'ul', 'table'): ERR.append(f'{w} : type inconnu'); continue
        if k in ('h1', 'h2', 'p'):
            if not segs_ok(b.get('i'), w): continue
        if k == 'h2':
            sec = ''.join(x['t'] for x in b['i']).strip(); nsec += 1; rap.setdefault(sec, 0); nb.setdefault(sec, 0)
            if sec.startswith(('Audit', 'Sources')): ERR.append(f'{w} : la section « {sec} » est interne et ne doit pas figurer dans le dépôt public')
        elif k == 'p' and b.get('attrs') is not None:
            check_attrs(b['attrs'], w, themes, need_date=False); check_sum(b.get('sum'), w)
            if (b['attrs'] or {}).get('rappel'): rap[sec] = rap.get(sec, 0) + 1
            nitems += 1; nsum += bool(b.get('sum')); nb[sec] = nb.get(sec, 0) + 1
        elif k == 'ul':
            its = b.get('items') or []
            if not its: ERR.append(f'{w} : liste vide')
            for name in ('sum', 'attrs'):
                if name in b and len(b[name]) != len(its): ERR.append(f'{w} : « {name} » contient {len(b[name])} entrées pour {len(its)} puces')
            for j, it in enumerate(its):
                ww = f'{w}, puce {j + 1} ({sec.split(" : ")[0]})'
                segs_ok(it, ww)
                a = (b.get('attrs') or [None] * len(its))[j] if j < len(b.get('attrs') or []) else None
                sm = (b.get('sum') or [None] * len(its))[j] if j < len(b.get('sum') or []) else None
                check_attrs(a or {}, ww, themes); check_sum(sm, ww)
                if sec.startswith('Outils'): check_reseau(sm, ww, d)
                nitems += 1; nsum += bool(sm); nb[sec] = nb.get(sec, 0) + 1
                if a and a.get('rappel'): rap[sec] = rap.get(sec, 0) + 1
                if a and a.get('rappel') and words(''.join(x['t'] for x in it if not x.get('href'))) > 30:
                    WARN.append(f'{ww} : rappel de plus de 30 mots (deux colonnes : rester court)')
        elif k == 'table':
            rows = b.get('rows') or []
            if not rows or len(rows[0]) != 3: ERR.append(f'{w} : l’agenda doit avoir 3 colonnes (Date, Échéance, Thème)'); continue
            n = len(rows) - 1
            if n > AGENDA_MAX: ERR.append(f'Agenda : {n} dates, {AGENDA_MAX} au plus (ne garder que les plus importantes)')
            for name in ('sum', 'attrs', 'detail'):
                if name in b and len(b[name]) != n: ERR.append(f'{w} : « {name} » contient {len(b[name])} entrées pour {n} lignes')
            refs = meta.get('agenda_refs') or []
            for j, r in enumerate(rows[1:]):
                ww = f'agenda, ligne {j + 1}'
                dd = ''.join(x['t'] for x in r[0]).strip()
                if not re.fullmatch(r'(?:(\d+)(?: au (\d+))? )?(\w+) (\d{4})', dd) or dd.split()[-2].lower() not in MOIS:
                    ERR.append(f'{ww} : date « {dd} » non reconnue')
                if not any(x.get('href') for x in r[1]) and not (j < len(refs) and refs[j]): ERR.append(f'{ww} : pas de page de référence')
                sm = (b.get('sum') or [None] * n)[j]
                check_sum(sm, ww); nitems += 1; nsum += bool(sm)
                check_attrs((b.get('attrs') or [{}] * n)[j] or {}, ww, themes, need_date=False)
    if nsec < 4: ERR.append(f'Édition incomplète : {nsec} section(s)')
    if len(meta.get('toc') or []) != nsec: ERR.append(f'meta.json : « toc » compte {len(meta.get("toc") or [])} libellé(s) pour {nsec} section(s)')
    vides = [s_ for s_, n_ in nb.items() if n_ == 0 and not s_.startswith(('Agenda', 'Audit', 'Sources'))]
    for s_ in vides:   # ni nouveauté ni rappel encore ouvert : la rubrique n'est pas affichée (README, § 5)
        ERR.append(f'Rubrique « {s_.split(" : ")[0]} » sans aucun élément : la retirer (titre, chapô et libellé de « toc »)')
    for s_, n_ in rap.items():   # au moins 2 rappels par rubrique affichée (hors Agenda)
        if s_ not in vides and not s_.startswith(('Agenda', 'Audit', 'Sources')) and n_ < 2:
            ERR.append(f'Rubrique « {s_.split(" : ")[0]} » : {n_} rappel(s), au moins 2 attendus')
        elif s_ not in vides and not s_.startswith(('Agenda', 'Audit', 'Sources')) and n_ % 2:
            WARN.append(f'Rubrique « {s_.split(" : ")[0]} » : {n_} rappels ; un nombre pair équilibre les deux colonnes')
    if nitems and nsum < nitems: WARN.append(f'{nitems - nsum} élément(s) sans synthèse sur {nitems}')
    return nitems


def visible(h):
    h = re.sub(r'<(script|style)\b.*?</\1>', ' ', h, flags=re.S)
    h = re.sub(r'<div class="sy-d"[^>]*hidden>', ' ', h)
    return html.unescape(re.sub(r'<[^>]+>', ' ', h))


def check_outputs(d):
    out = os.path.join(BUILD, d)
    em = open(os.path.join(out, 'revue-email.html'), encoding='utf-8').read()
    web = open(os.path.join(out, 'revue-web.html'), encoding='utf-8').read()
    size = len(em.encode())
    if size > 100000: ERR.append(f'E-mail de {size} octets : au-delà de 100 000, Gmail le coupe')
    log = open(os.path.join(out, 'gen.log'), encoding='utf-8').read()
    for l in log.splitlines():
        if 'sigles sans définition' in l: ERR.append(l.strip())
        elif l.startswith(('ATTENTION', 'Note')): WARN.append(l.strip())
    for name, h in (('e-mail', em), ('web', web)):
        v = visible(h)
        for bad in ('None', 'undefined', 'null', 'NaN', '[]', '{}', '[ ]', '@@'):
            if re.search(r'(?<![\w@])' + re.escape(bad) + r'(?![\w])', v): ERR.append(f'Version {name} : « {bad} » apparaît dans le texte')
    return size, em, web


UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'


def probe(u):
    for meth in ('HEAD', 'GET'):
        try:
            req = urllib.request.Request(u, method=meth, headers={'User-Agent': UA, 'Accept': 'text/html,application/pdf,*/*', 'Accept-Language': 'fr,en'})
            with urllib.request.urlopen(req, timeout=25) as r: return r.status, ''
        except urllib.error.HTTPError as e:
            if meth == 'HEAD' and e.code in (403, 405, 404, 400, 429, 500, 501, 503): continue
            return e.code, ''
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as e:
            reason = getattr(e, 'reason', e)
            if meth == 'HEAD': continue
            return None, str(reason)[:80]
    return None, 'sans réponse'


def check_links(web):
    urls = sorted({html.unescape(u) for u in re.findall(r'href="(https?://[^"]+)"', web)} - {'https://revue.dejeun.es/'})
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        res = dict(zip(urls, ex.map(probe, urls)))
    for u, (code, why) in res.items():
        if code in (404, 410): ERR.append(f'Lien mort ({code}) : {u}')
        elif code is None and ('Name or service not known' in why or 'nodename nor servname' in why or 'getaddrinfo' in why):
            ERR.append(f'Lien vers un domaine inexistant : {u}')
        elif code is None or code >= 400: WARN.append(f'Lien non vérifiable ({code or why}) : {u}')
    return len(urls)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    eds = sorted(x for x in os.listdir(CONTENT) if re.fullmatch(r'\d{4}-\d{2}-\d{2}', x))
    if not args and not eds: print('Aucune édition à contrôler.'); sys.exit(0)
    d = args[0] if args else eds[-1]
    blocks = json.load(open(os.path.join(CONTENT, d, 'blocks.json'), encoding='utf-8'))
    meta = json.load(open(os.path.join(CONTENT, d, 'meta.json'), encoding='utf-8'))
    themes = json.load(open(os.path.join(TOOLS, 'themes.json'), encoding='utf-8'))
    nitems = check_content(d, blocks, meta, themes)
    if os.path.isfile(os.path.join(CONTENT, d, 'podcast.json')):
        sys.path.insert(0, TOOLS); import podcast
        pod, _ = podcast.charger(d)
        perr, _, _ = podcast.controler(pod, meta.get('n'))
        ERR.extend(f'podcast.json : {e}' for e in perr)
    size, em, web = check_outputs(d)
    nl = check_links(web) if '--no-links' not in sys.argv else 0
    rep = [f'## Contrôle de l’édition {d} (N° {meta.get("n")}{", démonstration" if meta.get("demo") else ""})', '',
           f'{nitems} éléments · e-mail de {size} octets · {nl} liens vérifiés' + (' (vérification des liens désactivée)' if '--no-links' in sys.argv else ''), '']
    rep += [f'### Erreurs bloquantes ({len(ERR)})', ''] + [f'- {e}' for e in ERR] + ([''] if ERR else ['Aucune.', ''])
    rep += [f'### Avertissements ({len(WARN)})', ''] + [f'- {w}' for w in WARN] + ([] if WARN else ['Aucun.'])
    txt = '\n'.join(rep) + '\n'
    print(txt)
    if os.environ.get('GITHUB_STEP_SUMMARY'): open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8').write(txt)
    if os.environ.get('GITHUB_ACTIONS'):   # annotations visibles dans l'interface et par l'API
        for e in ERR: print(f'::error title=Contrôle de l’édition {d}::{e}')
        for w in WARN[:20]: print(f'::warning title=Contrôle de l’édition {d}::{w}')
    open(os.path.join(BUILD, d, 'controle.md'), 'w', encoding='utf-8').write(txt)
    sys.exit(1 if ERR else 0)


if __name__ == '__main__':
    main()
