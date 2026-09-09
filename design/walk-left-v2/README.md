# Marche V2 — alternance des appuis, huit poses

Statut : révision candidate après rejet de V1 (« les pattes s'allongent »).
Aucun téléversement. Les contrôles mécaniques ne remplacent pas la revue visuelle.

## Aperçus à examiner

- [Traversée sur sol gradué ×2](walk-travel-2x.gif) : contrôler que le pied
  porteur reste en place pendant que le corps avance. Trois cycles, puis retour
  au début de la traversée.
- [Cycle sur place ×4](walk-dark-4x.gif) ; [cyan](walk-cyan-4x.gif) ; [vert](walk-green-4x.gif).
- [Les huit poses](sheet-dark-3x.png).
- [Articulations en mouvement](rig-4x.gif) et [planche des articulations](rig-sheet-3x.png).
  Orange = membres proches, bleu = membres éloignés, blanc = torse/bassin.
- `bmp/` contient huit BMP RGB 24 bits 112×112, sans compression, fond #FF00FF.

## Ce qui corrige V1

V1 redessinait surtout la patte avant sous un torse fixe : le pied changeait
de forme sans alternance cohérente des appuis. Ses tests de palette et de
surface ne permettaient pas de prouver une marche.

La référence de mouvement fournie est
[SLYNYRD, Pixelblog 50 — Human Walk Cycle](https://www.slynyrd.com/blog/2024/5/24/pixelblog-50-human-walk-cycle).
Le tutoriel distingue contact, appui, passage et avancée de la jambe libre,
puis inverse les rôles des membres sur la seconde moitié du cycle. Il utilise
un mannequin pour construire le mouvement avant les détails et montre le
balancement opposé des bras. Aucun pixel des illustrations du tutoriel n'est
repris dans les assets du projet.

Adaptation au dragon, avec ses proportions courtes plutôt que celles d'un humain :

- huit poses de 120 ms, cycle de 960 ms ;
- cuisse et tibia de 10 px chacun, bras et avant-bras de 8 px chacun dans
  le squelette ; aucune mise à l'échelle des membres ;
- résolution des angles de genou/coude pour atteindre les pieds/mains ;
- deux pattes déphasées d'un demi-cycle ; une patte porte pendant que l'autre
  se replie et avance, avec une levée maximale de 7 px ;
- sole au sol y=106 durant l'appui et progression de 4,5 px par pose dans
  la traversée ;
- mouvement vertical du corps : 0, +1, −1, −2 px, répété pour le second pas ;
- bras qui accompagnent la jambe opposée ;
- pieds de taille constante : griffes proches issues du sprite original,
  patte éloignée plus petite, redessinée une seule fois avec une sole plate.
  Le déroulé talon/pointe humain est simplifié pour ces petites pattes.

## Conservation graphique

Une seule référence : `assets/tft/dragon_walk_left_01.bmp`, inchangée et
verrouillée par SHA-256. Le visage, les yeux, les cornes et les ailes restent
pixel pour pixel identiques à cette référence, avec uniquement la translation
verticale entière du corps. Plus d'alternance entre les visages A et B.

Le tronc et la queue sont extraits de la référence ; les membres sont reconstruits
sur les articulations. La racine de la queue et deux raccords d'un pixel sont
retouchés explicitement. Les mains et les griffes proches sont des blocs de
pixels sélectionnés dans la référence. Le script n'utilise ni flou, ni morphing,
ni nouvelles couleurs. Les cinq modèles de mascottes validés restent inchangés.

## Preuves et limites

`validation.json` décrit les articulations de chaque pose ; `checks.json`
contient les résultats des contrôles indépendants :

- longueur de chaque segment constante avant arrondi ; erreur des segments
  rasterisés bornée à √2 px par l'arrondi des deux articulations ;
- dérive théorique de l'appui nulle en coordonnées du sol ; dérive rasterisée
  de 1 px maximum, due à la progression fractionnaire arrondie ;
- au moins une patte porte à chaque pose ;
- tête identique à la référence après compensation du rebond ;
- palettes, taille, absence de pixels opaques isolés/trous transparents d'un
  pixel, round-trip RLE, empreintes et GIF vérifiés ;
- huit images distinctes, sols fixes et faible variation de surface visible.

Le diagnostic `animation-preview` compile avec les huit images ; il conserve
les boutons gauche=fond, OK=pause/reprise, droite=audio. Les images y sont
embarquées en flash interne, sans écriture de NVS ou de W25Q64. Cette compilation
ne prouve pas encore la lisibilité ou la fluidité sur l'écran réel.

## Reproduire

```sh
rtk proxy /usr/bin/python3 -B design/walk-left-v2/build.py
rtk proxy /usr/bin/python3 -B design/walk-left-v2/verify.py
rtk /home/skyce/.platformio/penv/bin/pio run -e animation-preview
```

Le firmware normal et son catalogue de 33 sprites restent inchangés. La V1
est conservée comme essai rejeté ; seule cette V2 alimente le diagnostic.
L'essai TFT et la promotion vers les assets du jeu attendent la validation
visuelle du nouveau mouvement.
