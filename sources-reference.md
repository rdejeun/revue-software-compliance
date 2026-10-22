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

## Sources internationales (README, § 3, règle 9)

Organismes multilatéraux, pays partenaires de la France à l'export de défense et presse internationale : leurs informations de conformité entrent dans la revue selon la règle d'or, pondérées par la densité de l'actualité (README, § 3). Adresses lues le 22 ou le 23 octobre 2026.

### Organismes internationaux

Ce sont des sources primaires multilatérales. Les listes adoptées par les régimes de contrôle sont reprises ensuite dans l'annexe I du règlement dual-use de l'UE et dans les listes nationales des pays partenaires (SCOMET indien, liste des EAU, ordonnance de Singapour, notification coréenne…). L'Arrangement de Wassenaar figure déjà dans la section « Union européenne ».

| Source | Adresse | À surveiller |
|---|---|---|
| Arrangement de Wassenaar, listes de contrôle (en) | https://www.wassenaar.org/control-lists/ | Liste en vigueur (WA-LIST (25) 1 Corr., plénière de décembre 2025), résumé des modifications (catégorie 5 partie 2 : chiffrement, logiciels d'intrusion) |
| Traité sur le commerce des armes, secrétariat (en, fr, es) | https://www.thearmstradetreaty.org/ | Conférences des États parties (CSP12 : 24-28 août 2026), rapports annuels nationaux, guides de mise en œuvre |
| Conseil de sécurité de l'ONU, régimes de sanctions (en, fr) | https://main.un.org/securitycouncil/en/sanctions/information | Quinze comités actifs (dont la Corée du Nord, résolution 1718, et le Yémen, 2140), programme de travail mensuel |
| Conseil de sécurité de l'ONU, liste récapitulative (en, fr) | https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list | Date de mise à jour, téléchargements XML, PDF et HTML pour le filtrage des tiers (pas de flux, alerte par courriel) |
| ONU, comptes rendus et communiqués (en) (flux) | https://press.un.org/en/content/security-council | Désignations et radiations par les comités des sanctions, réunions du comité 1540 (non-prolifération) |
| MTCR, annexe des équipements, logiciels et technologies (en) | https://www.mtcr.info/en/mtcr-annex | Version de l'annexe (mise à jour du 25 avril 2024), manuel de l'annexe : logiciels de guidage et de navigation des drones et missiles |
| Groupe des fournisseurs nucléaires (NSG) (en) | http://nuclearsuppliersgroup.org/index.php/en | Directives INFCIRC/254 (parties 1 et 2), mises à jour de la liste de la partie 2 (juillet 2025), bonnes pratiques sur les transferts intangibles de technologie (adresse en http : le site d'origine nsg-online.org y redirige) |
| Groupe d'Australie (en) | https://www.dfat.gov.au/publications/minisite/theaustraliagroupnet/site/en/index.html | Déclarations de plénière, listes communes (le logiciel y figure dans les rubriques des équipements chimiques et biologiques) |
| OTAN, agence NCIA (en) | https://www.ncia.nato.int/ | Annonces aux industriels (NATO Edge, conférences), cybersécurité des systèmes de l'Alliance |
| OTAN, NCIA : achats (en) | https://www.ncia.nato.int/business/procurement | Politique d'achat de l'OTAN (NPP, en vigueur pour les procédures lancées après le 22 juillet 2025), avis d'opportunité (NPO), plateforme Neo |
| ISO/IEC JTC 1 (en) | https://jtc1info.org/ | Lettre trimestrielle, nouvelles normes des technologies de l'information (dont l'IA, SC 42) |
| ISO/IEC JTC 1/SC 27 (en) | https://www.iso.org/committee/45306.html | Programme de travail : ISO/IEC 27001, 15408 (critères communs), 27090 (sécurité de l'IA), cryptographie (WG 2), évaluation (WG 3) |
| UIT-T, commission d'études 17 (sécurité) (en, fr) | https://www.itu.int/en/ITU-T/studygroups/2025-2028/17/Pages/default.aspx | Réunions (Genève, 18-29 janvier 2027), recommandations de la série X approuvées, programmation sécurisée |
| Critères communs, portail de l'accord CCRA (en) | https://www.commoncriteriaportal.org/index.cfm | Profils de protection collaboratifs (cPP), produits certifiés, transition vers CC:2022 : reconnaissance des certificats hors de l'UE (Japon, Corée, Inde, Singapour, Australie) |
| G7, groupe de travail sur la cybersécurité (en, fr ; présidence française en 2026) | https://cyber.gouv.fr/en/international-cooperation-and-actions/the-g7-cybersecurity-working-group/ | Déclaration du 27 mai 2026, document « SBOM for AI », migration post-quantique, sécurité dès la conception |
| OCDE, observatoire de l'IA (OECD.AI) (en) (flux) | https://oecd.ai/en/ | Cadre de rapport du processus d'Hiroshima (HAIP), interopérabilité avec l'AI Act, suivi des incidents d'IA (AIM) |
| IEC, Commission électrotechnique internationale (en, fr) | https://www.iec.ch/homepage | Actualités et « IEC Just Published » ; la page du TC 65 (série IEC 62443) n'a pas pu être lue (voir la fin) |

### Pays partenaires de la France à l'export de défense

**Comment les pays ont été retenus.** Trois sources officielles ont été lues :
- le *Rapport au Parlement 2026 sur les exportations d'armement de la France* (année 2025, https://www.vie-publique.fr/files/rapport/pdf/304339_0.pdf) : partenariats stratégiques de défense « avec des pays comme l'Inde, les Émirats arabes unis, l'Indonésie ou le Brésil » (p. 22) ; principales commandes de 2025 : Inde, Indonésie, Grèce, Maroc, Croatie, Slovénie, Danemark, Belgique… L'annexe 14, « Principaux clients sur la période 2016-2025 », n'est pas lisible dans la version texte du PDF ;
- le *Rapport au Parlement 2025* (année 2024, https://www.vie-publique.fr/files/rapport/pdf/300296.pdf) et la fiche du SIPRI *Trends in International Arms Transfers, 2025* (mars 2026, https://www.sipri.org/sites/default/files/2026-03/fs_2603_at_2025.pdf) : de 2021 à 2025, l'Inde reçoit 24 % des exportations françaises d'armement majeur, l'Égypte 11 % et la Grèce 10 %. La fiche précédente (https://www.sipri.org/sites/default/files/2025-03/fs_2503_at_2024_0.pdf) donne pour 2020-2024 l'Inde (28 %), le Qatar (9,7 %) et la Grèce (8,3 %) ;
- le compte rendu de l'audition des ministres du 24 février 2026 (https://www.assemblee-nationale.fr/dyn/opendata/CRCANR5L17S2026PO59047N044.html).

La Grèce, la Croatie, les Pays-Bas, la Belgique, le Danemark, l'Estonie et les autres clients européens appliquent le droit de l'UE : ils sont couverts par la section « Union européenne ». L'Ukraine, premier importateur mondial d'armes en 2021-2025 selon le rapport 2026, n'a pas de sous-section : le site de son service de contrôle des exportations (dsek.gov.ua) n'a pas pu être lu. Singapour, la Corée du Sud et l'Australie ne sont pas établis comme clients majeurs par ces sources (le rapport 2026 présente même la Corée en concurrente). Leurs autorités publient pourtant des références très suivies (labels IoT, listes de contrôle, sécurité des produits) : elles figurent dans la sous-section « Autres autorités de référence » ci-dessous.

#### Inde

Partenaire : premier destinataire des armes françaises en 2021-2025 (SIPRI, 24 %) ; partenariat stratégique et commande de 26 Rafale Marine en 2025 (rapport au Parlement 2026).

| Source | Adresse | À surveiller |
|---|---|---|
| DGFT, liste SCOMET (en) | https://www.dgft.gov.in/CP/?opt=scomet | Versions de la liste des biens à double usage et militaires (dernière : 23 septembre 2025) ; la catégorie 8 couvre les télécommunications et la sécurité de l'information |
| DGFT, notifications (en) | https://www.dgft.gov.in/CP/?opt=notification | « SCOMET Updates » annuels, autorisations générales (dont la catégorie 8A5), politique d'exportation |
| Journal officiel de l'Inde (eGazette) (en, hi) | https://egazette.gov.in/ | Notifications extraordinaires : textes du DGFT, du ministère de la Défense, du MeitY (CERT-In, protection des données) |
| CERT-In (en) | https://www.cert-in.org.in/ | Directives (section 70B), *Technical Guidelines on SBOM, QBOM & CBOM, AIBOM and HBOM* (version 2.0 du 9 juillet 2025), avis ; lecture partielle (page dynamique) |
| Département de la production de défense (DDP) (en) | https://www.ddpmod.gov.in/ | Autonomie de l'industrie de défense, iDEX ; le DDP délivre aussi les licences d'exportation de la catégorie 6 (munitions) de la SCOMET depuis 2024. Page d'accueil peu actualisée |
| SRIJAN, portail d'indigénisation (en) | https://srijandefence.gov.in/ | Produits importés par les entreprises publiques de défense et les états-majors, ouverts à la fabrication locale (contenu indien) |

#### Émirats arabes unis

Partenaire : partenariat stratégique de défense (rapport au Parlement 2026, p. 22) ; 700 M€ de nouvelles commandes en 2024 (audition du 24 février 2026).

| Source | Adresse | À surveiller |
|---|---|---|
| Executive Office for Control & Non-Proliferation (EOCN) (en, ar) | https://www.uaeiec.gov.ae/en-us/ | Liste de contrôle des EAU, biens stratégiques, sanctions financières ciblées, décret-loi fédéral n° 43 de 2021 et résolution n° 97 de 2024 |
| TDRA, régulateur des télécommunications et du numérique (en, ar) | https://tdra.gov.ae/en | Homologation des équipements, réglementation des TIC, services de cybersécurité |
| Conseil Tawazun (ar, en) | https://www.tawazun.gov.ae/ | Achats de défense, développement et localisation de l'industrie (« توطين الصناعة »), IA industrielle |
| UAE Legislation, portail législatif fédéral (en, ar) | https://uaelegislation.gov.ae/en | Lois fédérales et résolutions du Cabinet (contrôle des exportations, cybersécurité, IA) |

#### Qatar

Partenaire : deuxième destinataire des armes françaises en 2020-2024 (SIPRI, 9,7 %).

| Source | Adresse | À surveiller |
|---|---|---|
| Qatar News Agency (QNA), agence officielle (en, ar) (flux) | https://www.qna.org.qa/en | Communiqués de l'agence nationale de cybersécurité (NCSA : certification NIA, adhésion à ISASecure pour l'IEC 62443), de Barzan et du ministère de la Défense, accords avec la France |
| Al Meezan, portail juridique (ar, en) | https://www.almeezan.qa/ | Lois et décrets (contrôle des armes, cybersécurité, protection des données) ; lecture partielle (page dynamique) |

#### Arabie saoudite

Partenaire : citée parmi les destinataires des licences françaises lors de l'audition du 24 février 2026 ; le rapport au Parlement 2026 (p. 15) la cite, après les EAU, parmi les pays qui développent leur propre industrie de défense.

| Source | Adresse | À surveiller |
|---|---|---|
| Autorité nationale de cybersécurité (NCA), documents réglementaires (en, ar) | https://nca.gov.sa/en/regulatory-documents/ | Contrôles ECC, CCC, OTCC (systèmes industriels), contrôles des systèmes critiques, normes cryptographiques nationales (NCS), lignes directrices IoT |
| NCA, actualités (en, ar) | https://nca.gov.sa/en/news/ | Nouveaux contrôles, enregistrement des prestataires, rapports |
| GAMI, autorité des industries militaires (en, ar) | https://www.gami.gov.sa/en | Objectif de 50 % de dépenses militaires localisées d'ici 2030 (40,74 % en 2024), licences de fabrication et d'exportation de produits militaires |
| Umm al-Qura, journal officiel (ar) | https://uqn.gov.sa/ | Lois et décisions du Conseil des ministres (le flux uqn.gov.sa/rss est annoncé, mais n'a pas pu être lu) |
| CST, régulateur des communications, de l'espace et des technologies (en, ar) | https://www.cst.gov.sa/en | Réglementation IoT, cloud, homologation ; lecture partielle |

#### Égypte

Partenaire : deuxième destinataire des armes françaises en 2021-2025 (SIPRI, 11 %).

| Source | Adresse | À surveiller |
|---|---|---|
| NTRA, régulateur des télécommunications (en, ar) | https://www.tra.gov.eg/en/ | Homologation des équipements (type approval), EG-CERT, consultations publiques |

Les autres sites officiels égyptiens (EG-CERT, ministère de la Production militaire, AOI, MCIT) refusent la lecture automatique : voir la fin.

#### Indonésie

Partenaire : partenariat stratégique ; commande de deux sous-marins Scorpène Evolved en 2025 (rapport au Parlement 2026) ; dernière tranche de 18 Rafale entrée en vigueur en 2024 (rapport 2025).

| Source | Adresse | À surveiller |
|---|---|---|
| Ministère de la Défense (Kemhan) (id) (flux) | https://www.kemhan.go.id/ | Accords industriels, politique d'acquisition |
| KKIP, comité de politique de l'industrie de défense (id) (flux) | https://kkip.go.id/ | Autonomie de l'industrie de défense, contenu local et compensations (offsets), appariements d'entreprises |
| Base des règlements (peraturan.go.id) (id) | https://peraturan.go.id/ | Journal officiel (Lembaran Negara, Berita Negara), projets de règlements (cybersécurité, BSSN, contenu local TKDN) |

#### Brésil

Partenaire : partenariat stratégique de défense (rapport au Parlement 2026, p. 22).

| Source | Adresse | À surveiller |
|---|---|---|
| Ministère de la Défense (pt) (flux) | https://www.gov.br/defesa/pt-br | Base industrielle de défense, projets stratégiques (PPED), cyberdéfense (exercice Guardião Cibernético) |
| Anatel, régulateur des télécommunications (pt) | https://www.gov.br/anatel/pt-br | Exigences de cybersécurité pour la certification des équipements, consultations publiques (une partie du contenu a été retirée en période électorale à partir du 4 juillet 2026) |
| GSI, cabinet de sécurité institutionnelle (pt) | https://www.gov.br/gsi/pt-br | Stratégie nationale de cybersécurité (E-Ciber), résolutions du comité CNCiber, CTIR.Gov |

#### Serbie

Partenaire : commande de 12 Rafale entrée en vigueur en 2024 (rapport au Parlement 2025) ; 2,7 Md€ d'échanges d'armement cités lors de l'audition du 24 février 2026.

| Source | Adresse | À surveiller |
|---|---|---|
| RATEL, régulateur des communications électroniques (en, sr) | https://www.ratel.rs/en | Cybersécurité (portail des incidents de sécurité), homologation des équipements |
| SRB-CERT, CERT national (sr) | https://www.cert.rs/ | Recommandations et alertes (loi sur la sécurité de l'information) |
| Système d'information juridique (sr) | https://www.pravno-informacioni-sistem.rs/ | Journal officiel : loi sur l'exportation et l'importation de biens à double usage, alignement sur l'UE ; lecture partielle |

#### Maroc

Partenaire : commande d'hélicoptères Caracal en 2025 (rapport au Parlement 2026).

| Source | Adresse | À surveiller |
|---|---|---|
| Ministère de l'Industrie et du Commerce (fr, ar) | https://www.mcinet.gov.ma/ | Commerce extérieur : licences d'exportation des biens à double usage ; écosystème aéronautique et de défense |
| Arrêté n° 2529-24 relatif aux licences d'exportation des biens à double usage (fr) | https://www.mcinet.gov.ma/sites/default/files/inline-files/Arr%C3%AAt%C3%A9%20relatif%20aux%20licences_0.pdf | Texte de référence (BO n° 7350 du 7 novembre 2024) : demandes, transferts de technologie, assistance technique |
| SGG, Bulletin officiel (fr, ar) | https://www.sgg.gov.ma/BulletinOfficiel.aspx | Lois et décrets (biens à double usage, industrie de défense, cybersécurité) ; lecture partielle (tableaux vides dans la version lue) |

#### Japon

Partenaire : accord franco-japonais relatif au transfert d'équipements et de technologies de défense, signé à Tokyo le 13 mars 2015 (projet de loi n° 536 du Sénat, 2015-2016, https://www.senat.fr/leg/pjl15-536.html) ; le Japon n'est pas un client majeur, mais c'est un régime d'exportation et de labels de référence.

| Source | Adresse | À surveiller |
|---|---|---|
| METI, contrôle des exportations de sécurité (ja) | https://www.meti.go.jp/policy/anpo/ | Révisions du décret sur le contrôle du commerce d'exportation et de ses circulaires (dernière : 30 janvier 2026), questions-réponses |
| METI, Security Export Control (en) | https://www.meti.go.jp/policy/anpo/englishpage.html | Liste des utilisateurs finaux (End User List), guides en anglais |
| IPA, label JC-STAR (ja) | https://www.ipa.go.jp/security/jc-star/ | Label de sécurité IoT, niveaux ★1 à ★4, exigences ★3, reconnaissance mutuelle avec le CLS de Singapour et le PSTI britannique |
| Bureau national de la cybersécurité (NCO, ex-NISC) (ja) | https://www.cyber.go.jp/ | Politique nationale (cyberdéfense active), communiqués |
| ATLA, agence des acquisitions de défense (en, ja) | https://www.mod.go.jp/atla/en/ | Appels d'offres, manuel de sécurité industrielle de défense, transferts d'équipements |

#### Autres autorités de référence (hors partenaires établis)

| Source | Adresse | À surveiller |
|---|---|---|
| Singapour, douanes : contrôle des biens stratégiques (en) | https://www.customs.gov.sg/businesses/strategic-goods-control/overview/ | Ordonnance Strategic Goods (Control) Order 2026 (en vigueur le 1er décembre 2026), transferts intangibles de technologie, manuel du Strategic Trade Scheme |
| Singapour, CSA : label CLS (en) | https://www.csa.gov.sg/our-programmes/certification-and-labelling-schemes/cybersecurity-labelling-scheme/ | Niveaux 1 à 4, reconnaissances mutuelles (Finlande, Allemagne, Corée, Royaume-Uni, Connectivity Standards Alliance) |
| Singapour, CSA : communiqués (en) | https://www.csa.gov.sg/news-events/press-releases/ | Calendrier de migration post-quantique (14 octobre 2026), sécurité de l'IA agentique, accords bilatéraux |
| Corée du Sud, Yestrade (MOTIE et KOSTI) (ko) | https://www.yestrade.go.kr/ | Notification sur l'exportation et l'importation de biens stratégiques (38e modification, en vigueur le 1er septembre 2026), autoclassement |
| Corée du Sud, ITSCC : certification Critères communs (ko) | https://itscc.kr/ | Produits certifiés, profils de protection, procédures d'évaluation (révision du 7 avril 2026), sécurité de la chaîne d'approvisionnement des TIC |
| Corée du Sud, DAPA : acquisitions de défense (en) | https://www.dapa.go.kr/dapa_en/main.do | Compensations (offsets), procédures d'acquisition, appels d'offres étrangers (d2b.go.kr) |
| Corée du Sud, KISA (en) | https://www.kisa.or.kr/EN | Gestion nationale des vulnérabilités, certification IoT (CIC) ; lecture partielle |
| Australie, ASD ACSC (en) | https://www.cyber.gov.au/ | Guides de sécurité dès la conception et SBOM cosignés avec la CISA, alertes |

### Presse internationale

Ces titres servent au repérage. Ils ne sont jamais la seule source d'un fait juridique : remonter au texte officiel du pays, cité dans les sections ci-dessus. Seuls figurent les titres dont la page d'accueil a été lue.

| Source | Adresse | À surveiller |
|---|---|---|
| Breaking Defense (en) (flux) | https://breakingdefense.com/ | Achats de défense, ITAR, chaînes d'approvisionnement, logiciel embarqué |
| Defense News, rubrique Global (en) (flux) | https://www.defensenews.com/ | Contrats internationaux, contrôle des exportations américain vu par l'industrie |
| Shephard (en) | https://www.shephardmedia.com/ | Programmes terre, air et mer, exigences des clients du Golfe et d'Asie |
| Naval News (en) (flux) | https://www.navalnews.com/ | Programmes navals (Inde, Indonésie, Golfe), intégration des systèmes de combat |
| Janes (en) | https://www.janes.com/ | Renseignement de défense ; le site est surtout commercial et la rubrique d'actualités refuse la lecture automatique |
| WorldECR (en) | https://www.worldecr.com/ | Revue spécialisée du contrôle des exportations et des sanctions, toutes juridictions (son flux n'est pas tenu à jour) |
| Nikkei Asia (en) | https://asia.nikkei.com/ | Contrôle des exportations japonais et asiatique, semi-conducteurs, investissements |
| Asia Times (en) (flux) | https://asiatimes.com/ | Géopolitique des technologies en Asie, sanctions |
| The Japan Times (en) | https://www.japantimes.co.jp/ | Politique de défense et d'exportation du Japon |
| Korea JoongAng Daily (en) | https://www.koreajoongangdaily.com/ | Industrie de défense coréenne, cybersécurité |
| The Korea Times (en) | https://www.koreatimes.co.kr/ | Exportations de défense coréennes, incidents de cybersécurité |
| Business Standard (en) | https://www.business-standard.com/ | Défense et commerce extérieur indiens (SCOMET, licences) |
| The National (en) | https://www.thenationalnews.com/ | Économie et défense des EAU, EDGE, investissements |
| Gulf News (en) | https://gulfnews.com/ | Réglementation et économie des EAU |
| Arab News (en) (flux) | https://www.arabnews.com/ | Arabie saoudite : GAMI, NCA, Vision 2030 |
| The Peninsula (en) | https://thepeninsulaqatar.com/ | Qatar : NCSA, défense, accords |
| Gulf Times (en) | https://www.gulf-times.com/ | Qatar : défense (pacte Badr), dialogue stratégique avec la France |
| Ahram Online (en) | https://english.ahram.org.eg/ | Égypte : politique industrielle et de défense |
| The Jakarta Post (en) | https://www.thejakartapost.com/ | Indonésie : défense, cybersécurité, politique industrielle |
| Tecnodefesa (pt) | https://tecnodefesa.com.br/ | Brésil : industrie et programmes de défense |
| Médias24 (fr) | https://medias24.com/ | Maroc : industrie de défense, cybersécurité, lois de finances |

Titres connus mais non lus (sites bloqués pour l'outil de lecture, à vérifier dans un navigateur avant de les ajouter) : The Economic Times et The Hindu BusinessLine (Inde), Yonhap (Corée), The Straits Times (Singapour), Valor Econômico et Defesa Aérea & Naval (Brésil).

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

### Requêtes internationales

- régimes multilatéraux : `Wassenaar OR MTCR OR "Australia Group" OR "Nuclear Suppliers Group" plenary 2026 control list software`, `"Security Council" sanctions committee designation cyber OR software` ;
- listes nationales alignées sur Wassenaar : `SCOMET update software OR technology DGFT notification`, `"Strategic Goods (Control) Order" Singapore amendment`, `"UAE Control List" OR "Executive Office for Control and Non-Proliferation"` ;
- japonais : 「輸出貿易管理令 改正 ソフトウェア」, 「外為法 技術提供 役務取引 見直し」, 「JC-STAR 相互承認」 ;
- coréen : 「전략물자 수출입고시 개정」, 「방위사업청 사이버보안 위험관리 K-RMF」, 「소프트웨어 공급망 보안 SBOM 가이드라인」 ;
- arabe : 「الهيئة الوطنية للأمن السيبراني ضوابط جديدة」 (NCA saoudienne), 「الهيئة العامة للصناعات العسكرية المحتوى المحلي」 (GAMI), 「مجلس الأمن السيبراني الإمارات معيار」 (Conseil de cybersécurité des EAU) ;
- indonésien : 「BSSN sertifikasi keamanan siber produk」, 「TKDN alutsista perangkat lunak offset」 ;
- portugais : 「controle de exportação bens sensíveis software MCTI」, 「Anatel requisitos de segurança cibernética equipamentos」, 「Base Industrial de Defesa conteúdo nacional software」 ;
- serbe : 「izvoz robe dvostruke namene softver dozvola」 ;
- contenu local et ITAR-free : `"indigenous content" OR "local content" defence software "source code" India OR Saudi OR UAE OR Indonesia`, `"ITAR-free" Gulf OR India OR Asia defence export`, `"Defence Acquisition Procedure 2026" software OR IP` ;
- SBOM et sécurité des produits hors UE et États-Unis : `SBOM guidelines CERT-In OR "Cyber Security Agency of Singapore" OR NCA OR JPCERT OR KISA`, `"cybersecurity labelling" mutual recognition CLS OR "JC-STAR" OR KISA` ;
- certification : `"Common Criteria" CCRA OR cPP 2026 certificate recognition`, `IEC 62443 certification ISASecure national scheme` ;
- cadres internationaux de l'IA et de la cybersécurité : `"G7 Cybersecurity Working Group" SBOM OR "post-quantum"`, `"Hiroshima AI Process" reporting framework`.

## Presse et analyses (interprétation, jamais seule source d'un fait juridique)

LWN.net, The Record, Industrial Cyber, BleepingComputer (attaques de la chaîne d'approvisionnement), lettres d'information des cabinets d'avocats spécialisés (contrôle des exportations, sanctions, CRA).

Presse française : Next, LeMagIT, Le Monde Informatique, Silicon.fr, JDN, CIO-Online, L'Usine Digitale, Solutions Numériques, IT Social, Global Security Mag. Elles relaient surtout les annonces d'éditeurs et les attaques : utiles pour repérer un sujet, jamais seule source d'un fait.

## Sources internationales à vérifier manuellement

La lecture automatique a échoué : robots.txt l'interdit, le site renvoie une erreur ou affiche un test anti-robot.
- Organismes : IEC TC 65 (https://www.iec.ch/dyn/www/f?p=103:7:::::FSP_ORG_ID:1250, https://www.iec.ch/tc65), IECEE (certification IEC 62443), rubrique des rapports annuels du Traité sur le commerce des armes, actualités de l'OTAN (nato.int : site en reconstruction, pas de flux exploitable).
- Inde : ministère de la Défense (mod.gov.in, procédure d'acquisition DAP 2026), portail des exportations de défense (defenceexim.gov.in), MeitY (meity.gov.in), page des lignes directrices du CERT-In.
- EAU : Conseil de cybersécurité (csc.gov.ae), pages internes de l'EOCN.
- Qatar : NCSA (ncsa.gov.qa, page dynamique), Barzan Holdings.
- Arabie saoudite : flux d'Umm al-Qura (uqn.gov.sa/rss), autorité du contenu local et des achats publics (lcgpa.gov.sa), agence de presse SPA (page dynamique).
- Égypte : EG-CERT (egcert.eg), ministère de la Production militaire (momp.gov.eg), AOI (aoi.gov.eg), MCIT (mcit.gov.eg).
- Indonésie : BSSN (bssn.go.id), TKDN (tkdn.kemenperin.go.id).
- Brésil : MCTI, bens sensíveis (test anti-robot), Diário Oficial da União (in.gov.br), Anatel cybersécurité (page interne), SEPROD (ministère de la Défense).
- Serbie : ministère du Commerce intérieur et extérieur (mtt.gov.rs, contrôle des exportations).
- Maroc : DGSSI (dgssi.gov.ma), base juridique Adala (adala.justice.gov.ma).
- Ukraine : service national de contrôle des exportations (dsek.gov.ua).
- Australie : Defence Export Controls (defence.gov.au), flux de l'ACSC.
- EAU, presse officielle : WAM (page dynamique).
