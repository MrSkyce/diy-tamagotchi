# Plan graphique — TFT IPS couleur

## Objectif

Le ZJY154S0800TG01 240×240 est l'unique écran du Tamagotchi. Toute l'interface,
le boot, l'œuf, le dragon et les transitions sont rendus nativement en couleur,
sans framebuffer intermédiaire.

## Architecture actuelle

- contrôleur ST7789 via Adafruit GFX, SPI mode 3 à 32 MHz ;
- `rotation(0)`, inversion IPS active et offset Adafruit natif de 80 lignes ;
- broche CS du module reliée à GND, donc `CS = -1` dans le pilote ;
- compositions 240×240 dédiées pour HOME, les six actions, STATUS, boot,
  œuf, éclosion et pré-veille ;
- jauges à cinq cases pleines ou vides ;
- rafraîchissement partiel du HOME et des animations pour éviter le
  clignotement.

## Contrat des assets

- `assets/tft/*.bmp` est l'unique source graphique ;
- 33 BMP couleur 112×112 couvrent tous les états du dragon et de l'œuf ;
- formats acceptés : BMP non compressé 8 ou 24 bits ;
- le magenta pur `#FF00FF` représente la transparence ;
- le générateur normalise en transparence les seules franges magenta reliées
  au fond et refuse toute nuance de matte résiduelle ;
- une keyframe graphique correspond à un fichier explicitement nommé ; les
  paires sont rendues en quatre phases sans créer de dessin intermédiaire ;
- `dragon_medicine_01` reprend les yeux canoniques de `dragon_idle1` ;
- `tools/generate_tft_assets.py` produit un catalogue léger et une image RGB565
  compressée RLE destinée à la W25Q64 ;
- la génération refuse un dragon hors de la plage normalisée de 5 000 à 7 300
  pixels visibles ou un écart de surface supérieur à 12 % entre deux frames
  d'une même animation ; elle refuse aussi un décalage de ligne de sol supérieur
  à 3 pixels dans une famille animée ;
- le header généré est reproductible et ne doit pas être modifié à la main.

```text
assets/tft/*.bmp
↓ tools/generate_tft_assets.py
catalogue C++ + image RLE
↓ asset-flash-programmer
W25Q64
↓ cache RAM 112×112
ST7789
```

## Couverture

- HOME : marche gauche/droite, idle, clignement, faim, tristesse, maladie et
  fatigue ;
- FOOD, PLAY, MEDICINE, CLEAN et SLEEP : animations couleur dédiées ;
- SLEEP : acceptation, refus et pose de sommeil profond ;
- boot : quatre rotations d'œuf, deux fissures et éclosion ;
- stade œuf : cycle continu des quatre rotations, chaleur, actions bloquées et
  naissance animée sur les trois étapes de fissuration ;
- STATUS : six jauges segmentées, stade et âge.

## Performance et énergie

- ne jamais effacer tout l'écran dans une boucle d'animation périodique ;
- sur HOME, ne redessiner que la jauge, la case de menu ou le sprite modifié ;
- charger une frame depuis la W25Q64 dans le cache RGB565 unique, puis la
  transférer ligne par ligne vers le TFT ;
- rendre les paires en quatre phases de 180 ms avec un rebond maximal de 1 px,
  sans interpolation de couleur ni modification des keyframes validées ;
- ne pas allouer de framebuffer couleur plein écran de 115 200 octets ;
- le contrôleur TFT est désactivé avant le deep sleep et BLK GPIO10 est
  maintenu à LOW.

## État de validation

- les 33 assets couleur et leurs animations ont été validés par l'utilisateur
  sur la dalle réelle, puis depuis la W25Q64 le 6 septembre 2026 ;
- l'échelle, les lignes de sol, les yeux de `NO MEDICINE`, les couleurs et les
  découpes sont validés ;
- HOME, les jauges à cinq segments et la navigation partielle sont validés sans
  clignotement ;
- le générateur et les environnements PlatformIO compilent ;
- le firmware normal lisant les sprites externes a été téléversé et validé ;
- les 33 CRC passent, avec 35,5 ms au pire pour charger une frame à 8 MHz ;
- le deep sleep, l'extinction BLK et le réveil GPIO3 sont validés.

Version validée au 7 septembre 2026 : le générateur nettoie 1 325 pixels de
frange magenta répartis sur 17 assets et l'application utilise les quatre phases
à 180 ms. Les essais de keyframes intermédiaires ont tous été rejetés après
inspection agrandie dès qu'ils altéraient les contours ou la structure. Les
builds applicatif, programmateur et test de stockage passent. L'image W25Q64 est
programmée et ses 33 CRC passent. Les contours, le rythme, les actions,
l'absence de rognage et de scintillement ont été validés par l'utilisateur sur
le TFT réel.

## Contraintes matérielles

- l'écran est physiquement retourné sur le prototype ;
- le TFT et la W25Q64 partagent le bus avec leurs CS GPIO9 et GPIO2 distincts.

Le format externe, les CRC, la procédure de programmation et la capacité pour
de futures frames sont détaillés dans `ASSET_STORAGE.md`.
