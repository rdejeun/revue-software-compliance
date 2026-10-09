#!/usr/bin/env python3
"""Envoie l'e-mail de l'édition par l'API Resend (appelé par GitHub Actions après la mise en ligne).

Usage : python3 tools/send.py --mode auto|brouillon|diffusion|aucun [AAAA-MM-JJ] [--wait]
  auto      : envoi aux abonnés, une seule fois par édition (content/<date>/envoi.json), jamais pour une
              édition de démonstration ni pour une édition de plus de 3 jours. Avec RESEND_SEGMENT_ID : diffusion
              (Broadcast) au segment Resend, avec le lien de désabonnement de Resend ; sinon copie cachée à MAIL_TO
  diffusion : crée la diffusion dans Resend SANS l'envoyer (à relire et à tester depuis le tableau de bord), sans enregistrement
  brouillon : envoi de relecture à DRAFT_TO, objet préfixé « [Brouillon] », sans enregistrement
  aucun     : pas d'envoi
  --wait    : attend que la page web de l'édition soit en ligne (6 minutes au plus)
Variables d'environnement : RESEND_API_KEY (secret), RESEND_SEGMENT_ID, DRAFT_TO, MAIL_FROM (facultatif) ; MAIL_TO et MAIL_VISIBLE seulement sans segment.
Écrit sent=1 dans GITHUB_OUTPUT quand un envoi définitif a eu lieu (jamais en mode brouillon).
"""
import datetime, hashlib, json, os, re, sys, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT, BUILD = os.path.join(ROOT, 'content'), os.path.join(ROOT, 'build')
FROM = os.environ.get('MAIL_FROM') or 'Software Compliance <no-reply@s2c2.dejeun.es>'
UNSUB = '<mailto:unsubscribe@dejeun.es>'
# Envoi aux abonnés : destinataires en copie cachée (aucun ne voit les autres) ; le champ « À » porte l'adresse
# MAIL_VISIBLE, à défaut celle de l'expéditeur. Le brouillon (DRAFT_TO) reste adressé directement.
VISIBLE = os.environ.get('MAIL_VISIBLE') or FROM
BCC_MAX = 50   # limite de Resend par message (envoi sans segment)
SEGMENT = os.environ.get('RESEND_SEGMENT_ID', '').strip()
# lien de désabonnement géré par Resend (diffusions) : le segment ne reçoit que les contacts abonnés
PIED_DESABO = ('<div style="margin:0;padding:18px 16px 28px;text-align:center;font:12px/18px \'Segoe UI\',Arial,sans-serif;color:#6b7280;">'
               'Vous recevez cette revue parce que votre adresse est inscrite à la liste de diffusion. '
               '<a href="{{{RESEND_UNSUBSCRIBE_URL}}}" style="color:#6b7280;">Se désabonner</a></div>')


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
    if not pos and not eds: print('Aucune édition : pas d’envoi.'); out('sent', '0'); return
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
        to = '' if SEGMENT else os.environ.get('MAIL_TO', '')
    elif mode == 'brouillon':
        to = os.environ.get('DRAFT_TO', '')
    elif mode == 'diffusion':
        to = ''
    else:
        sys.exit(f'Mode inconnu : {mode}')
    to = [x.strip() for x in to.split(',') if x.strip()]
    key = os.environ.get('RESEND_API_KEY')
    diffusion = mode in ('auto', 'diffusion') and bool(SEGMENT)
    if mode == 'diffusion' and not SEGMENT: sys.exit('Mode « diffusion » : RESEND_SEGMENT_ID manquant.')
    if not key or (not to and not diffusion): sys.exit('Destinataires (RESEND_SEGMENT_ID / MAIL_TO / DRAFT_TO) ou clé RESEND_API_KEY manquants : envoi impossible.')
    if '--wait' in a: wait_online(f'https://revue.dejeun.es/{d}/', meta['n'])
    b = os.path.join(BUILD, d)
    subject = f'📰 Revue de presse – {meta["date"]}'   # meta « date » : « 9 octobre 2026 »
    if mode == 'brouillon': subject = '[Brouillon] ' + subject
    if mode == 'auto' and not diffusion and len(to) > BCC_MAX: sys.exit(f'{len(to)} destinataires : au-delà de {BCC_MAX}, Resend refuse la copie cachée (passer à un envoi par lots)')
    if diffusion:
        html_ = open(os.path.join(b, 'revue-email.html'), encoding='utf-8').read()
        html_ = html_.replace('</body>', PIED_DESABO + '</body>', 1) if '</body>' in html_ else html_ + PIED_DESABO
        texte = open(os.path.join(b, 'revue-email.txt'), encoding='utf-8').read().rstrip() + '\n\nSe désabonner : {{{RESEND_UNSUBSCRIBE_URL}}}\n'
        payload = {'segment_id': SEGMENT, 'from': FROM, 'subject': subject, 'name': f'Revue {d} (N° {meta["n"]})', 'html': html_, 'text': texte, 'send': mode == 'auto'}
        req = urllib.request.Request('https://api.resend.com/broadcasts', data=json.dumps(payload).encode(), method='POST',
                                     headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json', 'User-Agent': 'revue-sc'})
        try:
            with urllib.request.urlopen(req, timeout=60) as r: res = json.loads(r.read())
        except urllib.error.HTTPError as e:
            sys.exit(f'Resend a refusé la diffusion ({e.code}) : {e.read().decode()[:300]}')
        print(f'Diffusion {"envoyée" if mode == "auto" else "créée sans envoi"} : id {res.get("id")} · segment {SEGMENT} · « {subject} »')
        if mode == 'auto':
            json.dump({'id': res.get('id'), 'envoye_le': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'), 'objet': subject, 'diffusion': True, 'segment': SEGMENT}, open(rec, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            out('sent', '1')
        return
    dest = {'to': [VISIBLE], 'bcc': to} if mode == 'auto' else {'to': to}
    payload = {'from': FROM, **dest, 'subject': subject,
               'html': open(os.path.join(b, 'revue-email.html'), encoding='utf-8').read(),
               'text': open(os.path.join(b, 'revue-email.txt'), encoding='utf-8').read(),
               'headers': {'List-Unsubscribe': UNSUB}}
    # empreinte du contenu : un nouvel essai identique est dédoublonné par Resend, un contenu corrigé repart
    emp = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]
    idem = f'revue-{d}-n{meta["n"]}-{emp}' if mode == 'auto' else f'brouillon-{d}-{os.environ.get("GITHUB_RUN_ID", int(time.time()))}'
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
