"""Pied de page commun (édition web, e-mail, pages annexes) et page des mentions légales."""
import html

EDITEUR = 'Rodolphe Dejeunes'
ATTRIBUTION = 'Software Compliance · revue.dejeun.es'
LICENCE_URL = 'https://creativecommons.org/licenses/by/4.0/deed.fr'
SITE = 'https://revue.dejeun.es'


def pied(redaction, annee, absolu=False, lien='color:#7a808d;'):
    """Version courte : IA, droits, licence CC BY 4.0, contenus tiers, lien vers les mentions légales.
    absolu=True pour l'e-mail (liens complets)."""
    ml = (SITE if absolu else '') + '/mentions-legales/'
    return (f'Rédigé par une intelligence artificielle ({html.escape(redaction)}) à partir des sources citées ; des erreurs sont possibles. '
            f'©\u00a0{annee} {EDITEUR} — Contenu original sous licence <a href="{LICENCE_URL}" style="{lien}">CC BY 4.0</a> : '
            f'réutilisation libre avec mention «\u00a0{ATTRIBUTION}\u00a0». Les contenus cités restent la propriété de leurs auteurs. '
            f'<a href="{ml}" style="{lien}">Mentions légales</a>')


SANS_ = "'Segoe UI',Arial,sans-serif"
CSS_PIED = ('@media(max-width:660px){td.pd-c{display:block!important;width:100%!important;text-align:left!important;padding:0 0 10px!important}'
            'td.pd-c.pd-n{padding-bottom:4px!important}}')


def pied_bloc(redaction, annee, absolu=False):
    """Pied de page (variante A) : monogramme et « Revue de presse hebdomadaire », navigation à droite ; filet fin ;
    une ligne de mentions (©, licence, rédaction par IA) et le lien vers les mentions légales. Tableaux et styles en
    ligne, pour l'e-mail (Outlook compris) ; petit écran : les cellules s'empilent (CSS_PIED). absolu=True : liens complets."""
    b = SITE if absolu else ''
    lk = 'color:#4b5563;text-decoration:none;border-bottom:1px dotted #9ca3af;'
    nav = ' &nbsp;&nbsp; '.join(f'<a href="{b}{u}" style="{lk}">{t}</a>' for t, u in (
        ('Archives', '/archives/'), ('Dossiers', '/dossiers/'), ('Fil RSS', '/feed.xml'), ('Podcast', '/#ecouter')))
    fin = 'color:#8a8f98;text-decoration:none;border-bottom:1px dotted #b8bcc4;'
    T = '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"'
    return (f'{T} style="margin:44px 0 0;border-top:2px solid #0f2a4a;"><tr><td style="padding:0;">'
            # ligne 1 : identité, navigation
            f'{T}><tr><td class="pd-c pd-n" valign="middle" style="padding:16px 0 12px;font:13px/20px {SANS_};color:#4b5563;white-space:nowrap;">'
            f'<img src="{b}/apple-touch-icon.png" width="28" height="28" alt="SC" style="display:inline-block;vertical-align:middle;width:28px;height:28px;border:0;border-radius:5px;margin:0 10px 0 0;">'
            f'<span style="vertical-align:middle;">Revue de presse hebdomadaire</span></td>'
            f'<td class="pd-c" align="right" valign="middle" style="padding:16px 0 12px 12px;font:13px/20px {SANS_};text-align:right;white-space:nowrap;">{nav}</td></tr></table>'
            # filet fin, puis ligne 2 : mentions et lien vers les mentions légales
            f'{T} style="border-top:1px solid #e5e1d8;"><tr><td class="pd-c" valign="top" style="padding:10px 0 0;font:350 12px/18px {SANS_};color:#8a8f98;">'
            f'©\u00a0{annee} {EDITEUR} · <a href="{LICENCE_URL}" style="{fin}">CC\u00a0BY\u00a04.0</a> · Rédigé par IA à partir des sources citées</td>'
            f'<td class="pd-c" align="right" valign="top" style="padding:10px 0 0 12px;font:350 12px/18px {SANS_};text-align:right;white-space:nowrap;">'
            f'<a href="{b}/mentions-legales/" style="{fin}">Mentions légales</a></td></tr></table>'
            '</td></tr></table>')


def courriel():
    """Adresse lisible à l'écran mais pas dans le code de la page : caractères écrits à l'envers et remis
    à l'endroit par le sens d'écriture CSS, avec un leurre invisible ; pas de lien mailto."""
    a, b = 'revue', 'dejeun.es'
    return (f'<span class="eml" aria-label="{a} arobase {b.replace(".", " point ")}">{b[::-1]}'
            f'<span class="lr" aria-hidden="true">{"moc.elpmaxe"}</span>@{a[::-1]}</span>')


CSS_COURRIEL = '.eml{unicode-bidi:bidi-override;direction:rtl;white-space:nowrap}.eml .lr{display:none}'


def mentions(redaction, annee):
    """Corps de la page /mentions-legales/."""
    li = lambda t: f'<p>{t}</p>'
    return ''.join([
        '<div class="r"></div><h2>Éditeur et directeur de la publication</h2>',
        li(f'{EDITEUR} — contact : {courriel()}'),
        '<div class="r"></div><h2>Hébergement</h2>',
        li('GitHub, Inc. (service GitHub Pages), 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, États-Unis — <a href="https://github.com">github.com</a>.'),
        '<div class="r"></div><h2>Rédaction</h2>',
        li(f'Les éditions, synthèses et scripts du podcast sont rédigés par une intelligence artificielle ({html.escape(redaction)}) à partir des sources citées, '
           'selon une procédure de vérification des faits décrite dans le dépôt du projet. Des erreurs sont possibles : se reporter aux sources avant toute décision. '
           'La revue ne constitue pas un conseil juridique.'),
        '<div class="r"></div><h2>Propriété intellectuelle et licence</h2>',
        li(f'© {annee} {EDITEUR}. Sauf mention contraire, le contenu original de Software Compliance (synthèses, sélection et organisation des informations) '
           f'est mis à disposition, dans la mesure où des droits existent, selon les termes de la licence '
           f'<a href="{LICENCE_URL}">Creative Commons Attribution 4.0 International (CC BY 4.0)</a>. Vous pouvez le copier, le diffuser et l’adapter, '
           f'y compris à des fins commerciales, à condition de citer « {ATTRIBUTION} », d’indiquer la licence et de signaler toute modification.'),
        li('Les contenus de tiers cités ou résumés (articles, rapports, textes officiels, marques, logos) restent la propriété de leurs auteurs et ne sont pas '
           'couverts par cette licence ; les courtes citations sont reproduites au titre de l’article L. 122-5, 3°, du Code de la propriété intellectuelle.'),
        '<div class="r"></div><h2>Podcast</h2>',
        li('Voix de synthèse (Julie et Guillaume) générées avec <a href="https://elevenlabs.io">ElevenLabs</a>, dans le cadre d’une offre payante qui inclut '
           'une licence d’usage commercial ; la mention est faite par transparence sur l’usage de voix artificielles.'),
        li('Habillage sonore : « Tech Logo Intro », de sergequadrado, publié sur Pixabay sous la '
           '<a href="https://pixabay.com/service/license-summary/">licence de contenu Pixabay</a>.'),
        '<div class="r"></div><h2>Visuels</h2>',
        li('Monogramme « SC » (icône du site, flux RSS et couverture du podcast) : image générée avec ChatGPT (OpenAI). Illustration de l’en-tête : image générée avec Gemini (Google).'),
        '<div class="r"></div><h2>Données personnelles</h2>',
        li('Le site ne dépose pas de cookie et ne mesure pas l’audience. Les adresses des destinataires de la lettre servent uniquement à son envoi, '
           'confié au prestataire Resend. Pour toute demande (accès, rectification, désinscription), écrire à l’adresse de contact ci-dessus.'),
    ])
