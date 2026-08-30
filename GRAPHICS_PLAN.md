# Plan graphique — sprites BMP et OLED bicolore

## Objectif

Donner au dragon une silhouette originale plus lisible et expressive, sans
reprendre les personnages Tamagotchi. L'interface utilise la bande jaune et le
dragon bénéficie de toute la zone bleue.

| Zone physique OLED | Coordonnées | Usage prévu |
|---|---:|---|
| Jaune | `y = 0..15` | Menu compact FD / PL / MD / CL / SL / ST |
| Bleue | `y = 16..63` | Dragon, animations et messages contextuels |

La zone bleue mesure 128×48 px. Les premiers sprites viseront 32×32 px, mais
le convertisseur acceptera toute image qui tient dans 128×48 px.

## Contrat des assets

- Tous les assets source sont des BMP non compressés, en noir et blanc.
- Un pixel clair est affiché sur l'OLED ; un pixel sombre est transparent.
- Les BMP sont versionnés dans `assets/sprites/` et restent la source de vérité.
- Un GIF n'est pas utilisé : chaque frame d'animation est un BMP nommé
  explicitement, par exemple `dragon_idle_01.bmp` et `dragon_idle_02.bmp`.

## Chaîne de précompilation

```text
assets/sprites/*.bmp
        ↓ tools/generate_sprites.py
include/generated_sprites.h
        ↓ PlatformIO
firmware ESP32-C3
```

Le script Python n'aura aucune dépendance externe : il lira le format BMP
non compressé, validera dimensions et palette, puis produira des tableaux
`PROGMEM` compatibles avec `Adafruit_SSD1306::drawBitmap()`. Le header généré
reste versionné : son diff rend visible le résultat de toute modification
graphique dans une revue Git.

## Incrément d'implémentation

1. **Fait —** déplacer le menu principal dans la bande jaune et réserver la
   zone bleue au contenu ; préserver les trois boutons et les écrans
   FOOD/PLAY/STAT.
2. **Fait —** ajouter le répertoire d'assets, le convertisseur pré-build
   PlatformIO et migrer les sprites existants ; compiler pour vérifier la
   génération reproductible.
3. **Fait —** tester le cadrage 40×40 avec les BMP migrés, puis redessiner
   les sprites avec des silhouettes originales et détourées : idle, blink,
   happy, hungry, sad, sick et sleeping.
4. **Fait —** ajouter et revoir sur l'OLED réelle les frames de marche du
   dragon (deux poses par direction) et les quatre poses de rotation de l'œuf :
   contraste, centrage, lisibilité à distance et fluidité.

Le dragon 40×40 se promène entre les marges de la zone bleue, avec un
déplacement d'un pixel toutes les 120 ms. Les frames `dragon_walk_left_01/02`
et `dragon_walk_right_01/02` alternent les pattes selon son sens de marche.
Chaque entrée du menu jaune est limitée à deux lettres (`FD`, `PL`, `MD`,
`CL`, `SL`, `ST`) ; sur l'écran principal, son nom complet est centré une
seconde dans la première ligne bleue. Le dragon commence donc à `y = 24`.

Les messages d'action sont placés dans les marges latérales bleues afin que le
dragon conserve la même ligne de sol sur l'écran principal, FOOD et PLAY.
Pendant FOOD, deux frames BMP font frotter ses pattes sur son ventre ; pendant
PLAY, le dragon joyeux saute entre `y = 20` et `y = 16`, sans empiéter sur le
menu jaune.

L'œuf de démarrage est également précompilé depuis `assets/boot/`. Ses quatre
frames de rotation le font rouler vers la bordure droite avant de se fissurer ;
trois frames de casse ouvrent ensuite la coque avec des éclats, accompagnés
d'un bref effet sonore. Un réveil deep sleep saute cette animation et joue une
courte mélodie de retour.
5. Documenter l'export des BMP et la convention de nommage dans le README.

## Validation

- La génération échoue clairement pour un BMP compressé, coloré ou trop grand.
- `pio run` régénère le header lorsque l'asset change.
- Les sprites sont vérifiés sur la dalle bicolore réelle, pas uniquement dans
  un éditeur d'image.
- Aucun asset issu d'une franchise existante n'est intégré au firmware.
