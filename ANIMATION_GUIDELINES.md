# Contraintes graphiques pour le futur moteur d'animation

Le périmètre et le plan du générateur hors ligne sont définis dans
[le cadrage du moteur](HANDOFF_CODEX_MOTEUR_ANIMATION_SPRITES.md).
Ce document conserve les contraintes du projet existant ; les anciens essais
de marche et leurs objectifs de cadence ont été retirés.

## Références à préserver

Les [six mascottes](design/README.md) constituent les références graphiques.
Conserver leurs proportions, palettes, expressions et détails identitaires :
yeux, reflets, contours, cornes et autres attributs propres à chaque espèce.
Les sources et les assets approuvés ne doivent pas être écrasés par une génération.
Une approbation du modèle ne vaut pas approbation de ses futures animations.

## Socle embarqué actuel

- Écran ST7789 240×240 ; sprites BMP non compressés 8 ou 24 bits de 112×112.
- Transparence réservée au magenta pur `#FF00FF`.
- Conversion RGB565 little-endian et compression RLE sur W25Q64.
- Cache RAM d'une frame : 25 088 octets, sans framebuffer permanent d'écran.
- Les animations v0.7 à deux keyframes utilisent quatre phases de 180 ms,
  avec un rebond de 1 px. Elles restent en place jusqu'à une intégration dédiée.

Voir [ASSET_STORAGE.md](ASSET_STORAGE.md) pour le format et la programmation.
Les exemples de dimensions et d'export du cadrage ne remplacent pas ce contrat.

## Génération et validation

Préparer les calques et poses sans modifier les références. Composer avec des
coordonnées entières, sans lissage, morphing ni couleurs intermédiaires.
Les transformations et exceptions artistiques doivent être explicites.
Les sorties candidates restent hors de `assets/tft/` jusqu'à leur approbation.

Contrôler dimensions, palette, transparence, ancrages, ligne de sol, raccords
et reproductibilité. Les tolérances de surface doivent être adaptées à chaque
mascotte et au mouvement ; les seuils historiques du dragon ne sont pas universels.
Le détecteur de franges magenta ne doit pas supprimer la peau violette de la
salamandre : ses 11 pixels intérieurs signalés sont documentés dans
`design/mascots-v1/APPROVAL.json`.

Produire une planche et un GIF, inspectés à l'échelle réelle et en zoom entier
sur plusieurs fonds. Vérifier les appuis, la continuité de boucle et la stabilité
de l'identité graphique. Les contrôles automatiques ne prouvent pas la qualité
visuelle du mouvement.

L'export des frames approuvées doit vérifier le round-trip RLE, les CRC et la
capacité de stockage. L'intégration ultérieure demande une mesure du chargement
et du rendu avec boutons et audio actifs, puis une validation sur le TFT réel.
La mesure historique de 36,451 ms concerne le chargement d'une keyframe à 8 MHz,
pas le temps total d'affichage d'un futur clip.
