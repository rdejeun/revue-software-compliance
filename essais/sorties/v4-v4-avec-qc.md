# Contrôle qualité de l'épisode

Résultat : **publiable**

| Critère | Mesure | Seuil | Résultat |
|---|---|---|---|
| Loudness intégré du master (bloquant) | -18.9 LUFS | -19 ± 1.0 | ok |
| True peak (bloquant) | -2.3 dBTP | ≤ -1.0 | ok |
| Écart de loudness A/B | 0.00 LU | ≤ 1.0 | ok |
| Écart de timbre A/B (150 Hz–8 kHz) | 13.1 → 1.5 dB | ≤ 3.0 | ok |
| Réverbération propre à une voix (fins de mots −20 → −45 dB) | A nan → nan ms, B 21 → 21 ms | écart ≤ 50 % (+5 ms) | ok |
| Durée (bloquant) | 62.3 s (blocs : 62.4 s) | écart < 1.0 s | ok |
| Clics | 0 saut(s) anormal(aux) | aucun | ok |
| Fidélité au script (faster-whisper) (bloquant) | 2.0 % de mots différents sur 200 | ≤ 15 % | ok |

## Journal

- bloc 1 : décalage de décodage corrigé (83 ms)
- passe 1 : écart de timbre max 13.0 dB
- passe 2 : écart de timbre max 7.9 dB
- passe 3 : écart de timbre max 5.8 dB
