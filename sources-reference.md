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

## Licences : intégration et redistribution dans un produit

Au-delà de la GPL et des licences « source available » : obligations des licences permissives à la redistribution (avis de copyright, texte de licence, fichier NOTICE, brevets), logiciels commerciaux redistribués sous licence OEM ou embarquée, pools de brevets des codecs, audits de licences et contentieux de redistribution. Flux marqués « relevé » : relevés automatiquement (`tools/sources.json`).

| Source | Adresse | À surveiller | Nature |
|---|---|---|---|
| OSADL, listes d'obligations par licence | https://www.osadl.org/OSADL-Open-Source-License-Checklists.oss-compliance-lists.0.html | Obligations à la redistribution licence par licence (MIT, BSD, Apache-2.0…), table copyleft, matrice de compatibilité (JSON) | Consortium industriel de l'embarqué |
| Apache Software Foundation, LICENSE et NOTICE | https://infra.apache.org/licensing-howto.html · https://www.apache.org/legal/ | Contenu des fichiers LICENSE et NOTICE, dépendances regroupées | Primaire |
| REUSE (FSFE) | https://reuse.software/ | Spécification des avis de copyright par fichier ; versions de l'outil (relevé) | Organisme |
| Liste des licences SPDX | https://spdx.org/licenses/ | Nouveaux identifiants, exceptions, licences retirées (relevé) | Primaire (ISO/IEC 5962) |
| ScanCode LicenseDB et ClearlyDefined | https://scancode-licensedb.aboutcode.org/ · https://clearlydefined.io/about | Catégories de licences et données de licence des composants utilisées par les outils de SCA | Référentiels ouverts |
| Linux Foundation, pratiques de licence | https://www.linuxfoundation.org/licensebestpractices | Guides, OSPO, Civil Infrastructure Platform (relevé, filtré) | Organisme |
| SFC, conformité copyleft | https://sfconservancy.org/copyleft-compliance/ | Produits embarqués (téléviseurs, imprimantes 3D), code source correspondant (relevé : actualités et blog) | Organisme |
| FSFE | https://fsfe.org/news/news.en.html | REUSE, politique européenne, droit d'auteur du code généré par IA (relevé) | Organisme |
| Commission, EUPL et Open Source Observatory (OSOR) | https://interoperable-europe.ec.europa.eu/collection/eupl · https://interoperable-europe.ec.europa.eu/collection/open-source-observatory-osor | Compatibilité des licences, EUPL, politique open source de l'UE (relevé) | Primaire |
| Microsoft, Windows IoT Enterprise | https://learn.microsoft.com/en-us/windows/iot/iot-enterprise/commercialization/licensing | Licence OEM par appareil, distributeurs agréés, calendrier LTSC | Primaire |
| Microsoft, conditions des produits | https://www.microsoft.com/licensing/terms/ | Modifications mensuelles des conditions d'utilisation | Primaire |
| Oracle, Java SE et audits | https://www.oracle.com/java/technologies/javase/jdk-faqs.html · https://www.oracle.com/corporate/license-management-services/ | Licences NFTC et OTN, abonnement, embarquement ; règles d'audit | Primaire |
| The Qt Company, licences | https://www.qt.io/development/qt-framework/qt-licensing | Licences de distribution par appareil, LGPL ou commercial (relevé, filtré) | Primaire |
| QNX, contrats de licence | https://www.qnx.com/legal/licensing/ | Licences de distribution (runtime), contrats par version | Primaire |
| Via Licensing Alliance et Access Advance | https://www.via-la.com/licensing-programs/ · https://accessadvance.com/licensing-programs/ | Redevances des codecs (AVC, HEVC, VVC, AAC, projet AV1/AV2) dues pour les appareils (relevé) | Pools de brevets |
| ITAM Review | https://itassetmanagement.net/ | Audits Oracle, Microsoft, Broadcom (relevé, filtré) | Presse spécialisée |
| CIGREF, CNLL, Numeum, April, inno³ | https://www.cigref.fr/ · https://cnll.fr/news/ · https://numeum.fr/ · https://www.april.org/ · https://inno3.fr/ | Relations avec les éditeurs et audits (CIGREF), CRA et open source (CNLL, relevé), affaires de licence libre en France (April) | Organismes français |

**Jurisprudence**

| Source | Adresse | À surveiller | Nature |
|---|---|---|---|
| Judilibre (Cour de cassation) | https://www.courdecassation.fr/recherche-judilibre | Contrefaçon de logiciel, licences, art. L. 122-6 CPI (cours d'appel comprises) | Primaire |
| CJUE, directive 2009/24/CE | https://curia.europa.eu/ | Questions préjudicielles (références : UsedSoft C-128/11, IT Development C-666/18, Top System C-13/20) | Primaire |
| Legalis | https://www.legalis.net/ | Décisions françaises du numérique, contrefaçon de logiciel (relevé, filtré) | Base spécialisée |
| ifrOSS | https://www.ifross.org/ | Décisions allemandes sur la GPL, l'AGPL et le copyleft (relevé) | Institut juridique |
| Copyleft Currents (Heather Meeker) | https://heathermeeker.com/ | Contentieux américains : licences, attribution, IA (relevé) | Avocate spécialisée |
| Kluwer Copyright Blog, The IPKat | https://legalblogs.wolterskluwer.com/copyright-blog/ · https://ipkitten.blogspot.com/ | Droit d'auteur européen, logiciels et licences (relevé, filtré) | Universitaires et praticiens |

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
- licences dans un produit : « obligations licence MIT BSD Apache distribution binaire », « fichier NOTICE Apache conformité », `"NOTICE file" Apache-2.0 redistribution binary`, `attribution notices embedded firmware open source` ;
- licences commerciales embarquées et audits : `"Windows IoT" licensing OEM`, `Oracle Java audit`, « audit de licences éditeur », `codec patent pool AV1 OR HEVC OR VVC royalty devices` ;
- contentieux : « contrefaçon de logiciel licence arrêt cour d'appel », « non-respect licence logiciel libre », `GPL OR LGPL OR AGPL lawsuit embedded device`, `Landgericht GPL Urteil`, `CJEU "Directive 2009/24" judgment` ;
- un audit des sujets connexes est fait une fois par mois (README, § 14).

## Presse et analyses (interprétation, jamais seule source d'un fait juridique)

LWN.net, The Record, Industrial Cyber, BleepingComputer (attaques de la chaîne d'approvisionnement), lettres d'information des cabinets d'avocats spécialisés (contrôle des exportations, sanctions, CRA).

Presse française : Next, LeMagIT, Le Monde Informatique, Silicon.fr, JDN, CIO-Online, L'Usine Digitale, Solutions Numériques, IT Social, Global Security Mag. Elles relaient surtout les annonces d'éditeurs et les attaques : utiles pour repérer un sujet, jamais seule source d'un fait.
