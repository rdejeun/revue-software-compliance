# Image de fond de l'en-tête : prompt pour Gemini

Emplacement : en-tête de la version web, de la barre orange jusqu'au filet bleu marine.
Zone mesurée : 720 × 165 px sur ordinateur (rapport 4,36:1).
Texte présent :
- le titre « Software Compliance », à gauche, jusqu'à 64 % de la largeur ;
- la ligne « N° · date · Archives · Dossiers », en bas à gauche ;
- « Lecture ≈ 15 min », en bas à droite, dans les 22 % inférieurs.

Zone libre pour l'illustration : le quart supérieur droit, soit 65 à 100 % de la largeur et 0 à 75 % de la hauteur.

Générer en 21:9 (format le plus large proposé), puis recadrer au rapport 4,36:1 en gardant la bande du haut (environ 53 % de la hauteur) : les motifs, limités aux 38 % supérieurs de l'image générée, occupent alors les 71 % supérieurs de l'en-tête. Exporter en WebP, 2 880 × 660 px, et déposer le fichier sous `tools/en-tete.webp` : le site l'utilise automatiquement.

## Prompt (en anglais, plus fiable pour le modèle d'image)

```
Wide horizontal banner background, 21:9, for the masthead of a professional newsletter about software compliance (software bills of materials, open-source licences, cybersecurity regulation, export controls). Purely abstract, editorial, understated, like a faint watermark printed on fine paper.

BACKGROUND: perfectly flat pure white (#FFFFFF) across the entire image, no texture, no vignette, no gradient on the background itself. The image will sit behind dark text, so the left two thirds must stay completely empty and white.

COMPOSITION (strict geometric constraint):
- All illustration elements are confined to the upper-right corner: horizontally between 65% and 100% of the width, vertically between 0% and 38% of the height (the top edge and right edge may crop elements).
- Density is highest at the very top-right corner and fades smoothly to nothing toward the left and toward the bottom, following a soft diagonal falloff; nothing at all left of 60% of the width or below 42% of the height.
- Everything below 42% of the height must be empty white: text will be placed there.

MOTIFS (abstract line art, thin uniform strokes of 1 to 1.5 px at final size, geometric and precise, no fills except very light flat tints):
- a dependency graph: small circular nodes connected by straight and orthogonal lines, branching like a tree, suggesting a software bill of materials;
- fragments of a printed-circuit / data-trace pattern with right-angle paths and small via dots;
- a few stacked, slightly offset rectangular sheets with short horizontal hairlines suggesting lines of code or a checklist, one of them with a small check-mark;
- a partial outline of a shield or of a seal/rosette, cropped by the top edge, suggesting conformity and assurance;
- a sparse grid of small dots or a faint isometric grid behind the elements to tie them together.
Elements overlap gently in transparent layers; no element is dominant; the overall feeling is calm, precise, institutional.

PALETTE (watermark-level contrast, every stroke very light):
- burnt orange #C2410C at 12 to 18% opacity (accents: a few nodes, the check-mark, one trace);
- deep navy #0F2A4A at 8 to 12% opacity (most lines);
- muted blue #1F4E8C at 8% opacity (grid, secondary lines);
- warm sand #E3D6C3 and #F7F4EE as very light flat tints inside one or two shapes.
No other colours. No pure black. Maximum contrast against white must stay low enough for small dark text to remain perfectly readable on top.

STRICTLY AVOID: any text, letters, numbers, code syntax that can be read, logos, brand marks, flags, national symbols, weapons, military vehicles, padlocks, people, hands, faces, photographs, 3D rendering, glossy effects, glows, lens flares, neon, drop shadows, gradients on the background, dark areas, borders or frames.

Style references: Swiss editorial design, technical blueprint line drawing, banknote guilloche watermark subtlety, flat vector illustration.
```

## Variante si le premier résultat est trop chargé

Ajouter à la fin du prompt :

```
Make it even sparser: about half as many elements, larger empty spaces between them, and reduce all opacities by a further third.
```
