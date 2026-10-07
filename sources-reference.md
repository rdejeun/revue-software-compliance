# Sources de référence

Les sources à flux sont relevées automatiquement chaque jeudi soir (`tools/sources.json`, relevé dans `veille/collecte/`, README § 3) ; les autres sont à consulter chaque semaine, avant la recherche générale. Elles priment sur la presse et les blogs : quand une information en découle, citer la source primaire.

## Union européenne

| Source | Adresse | À surveiller |
|---|---|---|
| EUR-Lex et Journal officiel de l'UE | https://eur-lex.europa.eu/ | Règlements, actes délégués et d'exécution, rectificatifs |
| Commission, Cyber Resilience Act | https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act | Guidance, actes à venir, FAQ |
| ENISA | https://www.enisa.europa.eu/news | Plateforme unique de déclaration, rapports SBOM, schéma EUCC |
| Commission, industrie de défense (DG DEFIS) | https://defence-industry-space.ec.europa.eu/ | SAFE, EDIP, FED, Omnibus V |
| Conseil de l'UE, communiqués | https://www.consilium.europa.eu/en/press/press-releases/ | Paquets de sanctions, accords provisoires |
| Commission, commerce : biens à double usage | https://policy.trade.ec.europa.eu/help-exporters-and-importers/exporting-dual-use-items_en | Liste dual-use, lignes directrices |
| Carte des sanctions de l'UE | https://www.sanctionsmap.eu/ | Régimes et listes |
| CJUE | https://curia.europa.eu/ | Arrêts sur les sanctions, la responsabilité, la propriété intellectuelle |
| CEN-CENELEC (JTC 13) | https://www.cencenelec.eu/ | Normes harmonisées du CRA |
| ETSI | https://www.etsi.org/newsroom | EN 303 645, EN 18031, normes CRA |
| ENISA, base européenne des vulnérabilités (EUVD) | https://euvd.enisa.europa.eu/ | Vulnérabilités exploitées (relevé automatique), notion clé de la déclaration CRA |
| BSI (Allemagne), directive technique TR-03183 | https://www.bsi.bund.de/EN/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/Technische-Richtlinien/TR-nach-Thema-sortiert/tr03183/TR-03183_node.html | Exigences du CRA pour les fabricants, SBOM (partie 2) : référence très citée en Europe |
| Arrangement de Wassenaar | https://www.wassenaar.org/ | Plénière de décembre et listes de contrôle, reprises ensuite dans l'annexe I du règlement dual-use |

## France

| Source | Adresse | À surveiller |
|---|---|---|
| Légifrance (JORF) | https://www.legifrance.gouv.fr/ | Lois, décrets, arrêtés (NIS2, export, SREN) |
| ANSSI | https://cyber.gouv.fr/actualites | Référentiels, qualifications (SecNumCloud), transposition NIS2 |
| CERT-FR (ANSSI) | https://www.cert.ssi.gouv.fr/ | Panoramas de la cybermenace (annuels), alertes et rapports sur les attaques par la chaîne d'approvisionnement |
| SGDSN | https://www.sgdsn.gouv.fr/ | Contrôle des exportations de matériels de guerre (CIEEMG) |
| Ministère des Armées, DGA | https://www.defense.gouv.fr/dga | Contrôle des exportations, SIGALE |
| DG Trésor, sanctions économiques | https://www.tresor.economie.gouv.fr/services-aux-entreprises/sanctions-economiques | Gels d'avoirs, mesures nationales |
| Assemblée nationale et Sénat | https://www.assemblee-nationale.fr/ · https://www.senat.fr/ | Examen des projets de loi (loi Résilience) |

## États-Unis et Royaume-Uni

| Source | Adresse | À surveiller |
|---|---|---|
| Federal Register | https://www.federalregister.gov/ | Règles finales EAR, ITAR, DFARS |
| BIS (EAR) | https://www.bis.gov/ | Entity List, règle des affiliés, contrôles logiciels |
| OFAC, actions récentes | https://ofac.treasury.gov/recent-actions | Désignations, licences générales |
| DDTC (ITAR) | https://www.pmddtc.state.gov/ | Exemptions, modifications de l'USML |
| DoD CIO, CMMC | https://dodcio.defense.gov/CMMC/ | Calendrier des phases |
| CISA | https://www.cisa.gov/sbom | Éléments minimaux du SBOM, Secure by Design |
| CISA, catalogue KEV | https://www.cisa.gov/known-exploited-vulnerabilities-catalog | Vulnérabilités activement exploitées (relevé automatique) : composants tiers des produits |
| NIST, NVD | https://nvd.nist.gov/ | Base de vulnérabilités, SSDF |
| ECJU (Royaume-Uni) | https://www.gov.uk/government/organisations/export-control-joint-unit | Contrôle des exportations britannique : avis aux exportateurs, listes, licences (relevé automatique) |
| OFSI (Royaume-Uni) | https://www.gov.uk/government/organisations/office-of-financial-sanctions-implementation | Sanctions britanniques |

## Standards, communautés et licences

| Source | Adresse | À surveiller |
|---|---|---|
| OpenSSF | https://openssf.org/blog/ | SLSA, sécurité des registres, préparation au CRA |
| CycloneDX | https://cyclonedx.org/news/ | Versions de la spécification |
| SPDX | https://spdx.dev/ | Versions de la spécification |
| OpenChain | https://openchainproject.org/news | ISO/IEC 5230 et 18974 |
| ISA/IEC 62443 | https://www.isa.org/standards-and-publications/isa-standards/isa-iec-62443-series-of-standards | Cybersécurité des systèmes industriels : exigences de développement sécurisé (62443-4-1), pertinentes pour les équipements |
| Eclipse ORC | https://orcwg.org/ | Travaux sur la conformité réglementaire open source |
| OSI | https://opensource.org/blog | Licences approuvées |
| Software Freedom Conservancy | https://sfconservancy.org/news/ | Contentieux GPL |
| OSV et GitHub Advisory Database | https://osv.dev/ · https://github.com/advisories | Bases de vulnérabilités des composants |

## Outils et services de conformité (installables ou en ligne)

| Source | Adresse | À surveiller |
|---|---|---|
| Versions des outils open source | https://github.com/anchore/syft/releases · https://github.com/anchore/grype/releases · https://github.com/aquasecurity/trivy/releases · https://github.com/google/osv-scanner/releases · https://github.com/DependencyTrack/dependency-track/releases · https://github.com/oss-review-toolkit/ort/releases · https://github.com/aboutcode-org/scancode-toolkit/releases | Versions, formats SBOM pris en charge, bases de données |
| BIS, chiffrement | https://www.bis.gov/ | Autoclassement et rapports annuels du chiffrement (5A002, 5D002, 740.17), outils SNAP-R |
| ANSSI, cryptologie | https://cyber.gouv.fr/ | Déclarations et autorisations de moyens de cryptologie (démarches en ligne) |
| Commission, biens à double usage | https://policy.trade.ec.europa.eu/help-exporters-and-importers/exporting-dual-use-items_en | Outils d'aide au classement, lignes directrices (logiciel, IA, cybersurveillance) |
| Office européen des brevets (OEB) | https://www.epo.org/ | Espacenet, services en ligne, brevets logiciels et IA |
| EUIPO et OMPI | https://www.euipo.europa.eu/ · https://www.wipo.int/ | Outils en ligne de propriété intellectuelle |
| INPI | https://www.inpi.fr/ | Services en ligne, brevets et logiciels |

## Requêtes de veille (chaque semaine, en français et en anglais)

- « Software Composition Analysis », « SBOM tool », « open source license compliance tool » ;
- en français, toutes les formes en usage, car la presse titre souvent avec l'une et rédige avec l'autre : « chaîne d'approvisionnement logicielle », « supply chain logicielle », « attaque supply chain », « attaque de la chaîne d'approvisionnement » (UE, ENISA, éditeurs) et « attaque par la chaîne d'approvisionnement » (ANSSI) ; pour le SBOM : « nomenclature logicielle » (ANSSI, presse) et « nomenclature des logiciels » (version française du CRA) ; « chaîne d'approvisionnement numérique » pour les textes européens ;
- « export control classification software », « ECCN classification tool », « classement export logiciel », « dual-use classification AI » ;
- « encryption classification 5D002 », « mass market encryption », « moyens de cryptologie déclaration » ;
- « AI model export control », « geospatial imagery deep learning export control », « 0D521 » ;
- « patent search AI tool », « freedom to operate software », « code provenance copyright tool », « snippet matching open source » ;
- un audit des sujets connexes est fait une fois par mois (README, § 14).

## Presse et analyses (interprétation, jamais seule source d'un fait juridique)

LWN.net, The Record, Industrial Cyber, BleepingComputer (attaques de la chaîne d'approvisionnement), lettres d'information des cabinets d'avocats spécialisés (contrôle des exportations, sanctions, CRA).

Presse française : Next, LeMagIT, Le Monde Informatique, Silicon.fr, JDN, CIO-Online, L'Usine Digitale, Solutions Numériques, IT Social, Global Security Mag. Elles relaient surtout les annonces d'éditeurs et les attaques : utiles pour repérer un sujet, jamais seule source d'un fait.
