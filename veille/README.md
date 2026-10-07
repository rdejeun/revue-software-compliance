# Veille : relevés et journaux

Ce dossier n'est pas publié sur le site et ne déclenche pas la publication. Le dépôt est public : rien de confidentiel.

- `collecte/AAAA-MM-JJ.md` : relevé automatique des sources à flux, produit le jeudi soir par le workflow « Relevé des sources de veille » (`tools/collecte.py`, sources de `tools/sources.json`) pour l'édition du vendredi (README, § 3).
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

La revue mensuelle (README, § 14) compte, sur ces journaux, les requêtes sans élément retenu, les sources jamais citées et les dossiers sans nouveauté.
