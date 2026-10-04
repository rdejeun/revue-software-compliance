#!/usr/bin/env python3
"""Envoie l'e-mail de l'édition par l'API Resend (appelé par GitHub Actions après la mise en ligne).

Usage : python3 tools/send.py --mode auto|brouillon|aucun [AAAA-MM-JJ] [--wait]
  auto      : envoi aux destinataires (MAIL_TO), une seule fois par édition (content/<date>/envoi.json),
              jamais pour une édition de démonstration ni pour une édition de plus de 3 jours
  brouillon : envoi de relecture à DRAFT_TO, objet préfixé « [Brouillon] », sans enregistrement
  aucun     : pas d'envoi
  --wait    : attend que la page web de l'édition soit en ligne (6 minutes au plus)
Variables d'environnement : RESEND_API_KEY (secret), MAIL_TO, DRAFT_TO, MAIL_FROM (facultatif).
Écrit sent=1 dans GITHUB_OUTPUT quand un envoi définitif a eu lieu (jamais en mode brouillon).
"""
import datetime, json, os, re, sys, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT, BUILD = os.path.join(ROOT, 'content'), os.path.join(ROOT, 'build')
FROM = os.environ.get('MAIL_FROM') or 'Software Compliance <no-reply@s2c2.dejeun.es>'
UNSUB = '<mailto:unsubscribe@dejeun.es>'


def out(k, v):
    if os.environ.get('GITHUB_OUTPUT'): open(os.environ['GITHUB_OUTPUT'], 'a').write(f'{k}={v}\n')


def wait_online(url, n):
    for _ in range(36):
        try:
            with urllib.request.urlopen(urllib.request.Request(url + f'?v={int(time.time())}', headers={'User-Agent': 'revue-sc'}), timeout=20) as r:
                if r.status == 200 and f'N°&nbsp;{n} ' in r.read().decode('utf-8', 'replace'):
                    print(f'Page en ligne : {url}'); return True
        except Exception:
            pass
        time.sleep(10)
    print(f'ATTENTION : {url} ne répond pas encore ; envoi quand même', file=sys.stderr)
    return False


def main():
    a = sys.argv[1:]
    mode = a[a.index('--mode') + 1] if '--mode' in a else 'auto'
    pos = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] != '--mode')]
    eds = sorted(x for x in os.listdir(CONTENT) if re.fullmatch(r'\d{4}-\d{2}-\d{2}', x))
    d = pos[0] if pos else eds[-1]
    meta = json.load(open(os.path.join(CONTENT, d, 'meta.json'), encoding='utf-8'))
    rec = os.path.join(CONTENT, d, 'envoi.json')
    out('sent', '0')
    if mode == 'aucun': print('Mode « aucun » : pas d’envoi.'); return
    if mode == 'auto':
        age = (datetime.date.today() - datetime.date.fromisoformat(d)).days
        if meta.get('demo'): print('Édition de démonstration : pas d’envoi.'); return
        if os.path.exists(rec): print(f'Édition {d} déjà envoyée ({json.load(open(rec)).get("id")}) : pas de nouvel envoi.'); return
        if not -1 <= age <= 3: print(f'Édition {d} datée de {age} jours : pas d’envoi automatique.'); return
        to = os.environ.get('MAIL_TO', '')
    elif mode == 'brouillon':
        to = os.environ.get('DRAFT_TO', '')
    else:
        sys.exit(f'Mode inconnu : {mode}')
    to = [x.strip() for x in to.split(',') if x.strip()]
    key = os.environ.get('RESEND_API_KEY')
    if not to or not key: sys.exit('Destinataires (MAIL_TO / DRAFT_TO) ou clé RESEND_API_KEY manquants : envoi impossible.')
    if '--wait' in a: wait_online(f'https://revue.dejeun.es/{d}/', meta['n'])
    b = os.path.join(BUILD, d)
    subject = f'Software Compliance – N° {meta["n"]} – {meta["date"]}'
    if mode == 'brouillon': subject = '[Brouillon] ' + subject
    payload = {'from': FROM, 'to': to, 'subject': subject,
               'html': open(os.path.join(b, 'revue-email.html'), encoding='utf-8').read(),
               'text': open(os.path.join(b, 'revue-email.txt'), encoding='utf-8').read(),
               'headers': {'List-Unsubscribe': UNSUB}}
    idem = f'revue-{d}' if mode == 'auto' else f'brouillon-{d}-{os.environ.get("GITHUB_RUN_ID", int(time.time()))}'
    req = urllib.request.Request('https://api.resend.com/emails', data=json.dumps(payload).encode(), method='POST',
                                 headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json', 'Idempotency-Key': idem, 'User-Agent': 'revue-sc'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r: res = json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f'Resend a refusé l’envoi ({e.code}) : {e.read().decode()[:300]}')
    print(f'Envoyé ({mode}) : id {res.get("id")} · {len(to)} destinataire(s) · « {subject} »')
    if mode == 'auto':
        json.dump({'id': res.get('id'), 'envoye_le': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'), 'objet': subject}, open(rec, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        out('sent', '1')


if __name__ == '__main__':
    main()
