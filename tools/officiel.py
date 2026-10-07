"""Sources officielles (journaux officiels, autorités, organismes de normalisation) : liens mis en relief par le
générateur, sources primaires exigées par le contrôle (README, § 3) et archivées (tools/archiver.py)."""
from urllib.parse import urlparse

OFFICIEL = ('europa.eu', 'federalregister.gov', 'ecfr.gov', 'govinfo.gov', 'bis.gov', 'bis.doc.gov', 'treasury.gov', 'state.gov',
            'cisa.gov', 'nist.gov', 'defense.gov', 'gouv.fr', 'assemblee-nationale.fr', 'senat.fr', 'gov.uk', 'iso.org', 'etsi.org',
            'cencenelec.eu', 'bsi.bund.de', 'wassenaar.org', 'curia.europa.eu', 'legifrance.gouv.fr')


def officiel(u):
    h = (urlparse(u).hostname or '').lower()
    return any(h == d or h.endswith('.' + d) for d in OFFICIEL)
