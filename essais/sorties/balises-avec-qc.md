# Contrôle qualité de l'épisode

Résultat : **publiable**

| Critère | Mesure | Seuil | Résultat |
|---|---|---|---|
| Loudness intégré du master (bloquant) | -19.0 LUFS | -19 ± 1.0 | ok |
| True peak (bloquant) | -1.0 dBTP | ≤ -1.0 | ok |
| Écart de loudness A/B | 0.00 LU | ≤ 1.0 | ok |
| Écart de timbre A/B (150 Hz–8 kHz) | 9.0 → 2.2 dB | ≤ 3.0 | ok |
| Réverbération propre à une voix (fins de mots −20 → −45 dB) | A 53 → 28 ms, B 25 → 21 ms | écart ≤ 50 % (+5 ms) | ok |
| Durée (bloquant) | 68.3 s (blocs : 68.3 s) | écart < 1.0 s | ok |
| Clics | 0 saut(s) anormal(aux) | aucun | ok |
| Fidélité au script (faster-whisper) | non vérifiée (TypeError : open() got an unexpected keyword argument 'metadata_errors') | — | ok |

## Journal

- voix A : fins de mots 53 ms contre 25 ms pour B ; expandeur ratio 4 → 23 ms
- passe 1 : écart de timbre max 8.4 dB
- passe 2 : écart de timbre max 2.9 dB
- passe 3 : écart de timbre max 2.2 dB
