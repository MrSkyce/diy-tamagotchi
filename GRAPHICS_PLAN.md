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
- une frame d'animation correspond à un fichier explicitement nommé ;
- `dragon_medicine_01` reprend les yeux canoniques de `dragon_idle1` ;
- `tools/generate_tft_assets.py` produit les pixels RGB565 et un masque 1 bit
  dans `include/generated_tft_assets.h` ;
- la génération refuse un dragon hors de la plage normalisée de 5 000 à 7 300
  pixels visibles ou un écart de surface supérieur à 12 % entre deux frames
  d'une même animation ; elle refuse aussi un décalage de ligne de sol supérieur
  à 2 pixels dans une famille animée ;
- le header généré est reproductible et ne doit pas être modifié à la main.

```text
assets/tft/*.bmp
        ↓ tools/generate_tft_assets.py
include/generated_tft_assets.h
        ↓ PlatformIO
firmware ESP32-C3
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
- transférer les sprites ligne par ligne en RGB565 ;
- ne pas allouer de framebuffer couleur plein écran de 115 200 octets ;
- le contrôleur TFT est désactivé avant le deep sleep ; `BLK` reste toutefois
  alimenté tant qu'il est câblé directement au 3,3 V.

## État de validation

- les 33 assets couleur et leurs animations ont été validés par l'utilisateur
  sur la dalle réelle le 5 septembre 2026 ;
- l'échelle, les lignes de sol, les yeux de `NO MEDICINE`, les couleurs et les
  découpes sont validés ;
- HOME, les jauges à cinq segments et la navigation partielle sont validés sans
  clignotement ;
- le générateur et les cinq environnements PlatformIO compilent ;
- le firmware normal a été téléversé sur `/dev/ttyACM0` avec hash vérifié ;
- seule la veille réelle après 10 minutes et le réveil GPIO3 restent à
  revalider avant une release matérielle ; ce point ne remet pas en cause la
  validation du lot graphique.

## Contraintes matérielles

- le CS relié à GND monopolise le bus SPI ;
- l'absence de MISO impose un diagnostic visuel ;
- l'écran est physiquement retourné sur le prototype ;
- la W25Q64 ne doit pas partager ce bus sans rendre le CS du TFT pilotable.
