# Références graphiques des six mascottes

Ce dossier conserve les modèles de référence pour le futur générateur d'animations.
Les expérimentations de marche ont été retirées le 9 septembre 2026 ; elles
restent récupérables dans l'historique Git. Aucun nouveau clip n'est approuvé.

| Mascotte | BMP de référence |
|---|---|
| Dragon | [dragon_idle1.bmp](../assets/tft/dragon_idle1.bmp) |
| Chat Bleu | [blue_cat_idle_01_candidate.bmp](mascots-v1/bmp/blue_cat_idle_01_candidate.bmp) |
| Chien Rouge | [red_dog_idle_01_candidate.bmp](mascots-v1/bmp/red_dog_idle_01_candidate.bmp) |
| Souris Verte | [green_mouse_idle_01_candidate.bmp](mascots-v1/bmp/green_mouse_idle_01_candidate.bmp) |
| Oiseau Jaune | [yellow_bird_idle_01_candidate.bmp](mascots-v1/bmp/yellow_bird_idle_01_candidate.bmp) |
| Salamandre Violette | [purple_salamander_idle_01_candidate.bmp](mascots-v1/bmp/purple_salamander_idle_01_candidate.bmp) |

Le dragon est celui du firmware v0.7, dont les 33 BMP restent dans `assets/tft/`.
Les cinq autres modèles sont approuvés depuis le 8 septembre 2026 :
[preuve, empreintes et palettes](mascots-v1/APPROVAL.json).
Le suffixe historique `_candidate` ne remet pas cette approbation en question.

La [revue des six modèles](mascots-v1/review.html), la planche, les sources PNG,
les aperçus et les prompts sont conservés dans `mascots-v1/`.
Les BMP sont des références aplaties ; les calques et poses du futur moteur
restent à préparer. Le nettoyage de transparence des cinq nouvelles mascottes
reste à traiter sur des dérivés, en préservant les références approuvées.

Le [cadrage du moteur](../HANDOFF_CODEX_MOTEUR_ANIMATION_SPRITES.md) définit le
prochain chantier : générateur déterministe hors ligne, première marche à six
frames et export après validation. Les [contraintes graphiques](../ANIMATION_GUIDELINES.md)
et le [format de stockage](../ASSET_STORAGE.md) décrivent le contrat existant.
