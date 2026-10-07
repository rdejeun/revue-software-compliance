# Veille : relevés et journaux

Ce dossier n'est pas publié sur le site et ne déclenche pas la publication. Le dépôt est public : rien de confidentiel.

- `collecte/AAAA-MM-JJ.md` : relevé automatique des sources à flux, produit le mardi vers 3 h 30 (heure de Paris), avant la routine, par le workflow « Relevé des sources de veille » (`tools/collecte.py`, sources de `tools/sources.json`) pour l'édition du jour (README, § 3).
- `journal/AAAA-MM-JJ.md` : journal de veille de l'édition, écrit par la routine (README, § 7, étape 9), selon ce modèle :

```markdown
# Journal de veille — édition du AAAA-MM-JJ

## Requêtes
| Requête | Langue | Éléments retenus |
|---|---|---|

## Sources consultées
| Source | Relevé ou consultation | Éléments retenus |
|---|---|---|

## Éléments écartés
| Sujet | Lien | Motif (règle d'or, hors période, source insuffisante, doublon…) |
|---|---|---|

## Audit de couverture
| Dossier (themes.json) | Nouveauté, rappel ou rien | Pourquoi |
|---|---|---|

## Vérification
Affirmations : n ; confirmées : n ; corrigées : n ; retirées : n. Extraits retrouvés automatiquement : n ; à vérifier à la main : n.
```

- `reserve.json` : articles reportés au numéro suivant faute de place (budget de lecture de 10 minutes, README, § 5), selon ce format :

```json
[{"sujet": "…", "mis_en_reserve": "AAAA-MM-JJ", "rubrique": "Licences", "cote": [2, 1, 3], "fiabilite": "A",
  "item": [segments de blocks.json], "attrs": {…}, "sum": {synthèse}, "motif": "budget de lecture"}]
```

- `reserve-retraits.md` : articles retirés automatiquement de la réserve après 21 jours (`tools/reserve.py`, lancé en début de numéro).

La revue mensuelle (README, § 14) compte, sur ces journaux, les requêtes sans élément retenu, les sources jamais citées et les dossiers sans nouveauté.
