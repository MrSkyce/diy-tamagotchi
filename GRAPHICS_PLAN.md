# Plan graphique — sprites BMP et OLED bicolore

## Objectif

Donner au dragon une silhouette originale plus lisible et expressive, sans
reprendre les personnages Tamagotchi. L'interface utilise la bande jaune et le
dragon bénéficie de toute la zone bleue.

| Zone physique OLED | Coordonnées | Usage prévu |
|---|---:|---|
| Jaune | `y = 0..15` | Menu FOOD / PLAY / STAT et sélection |
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

1. Déplacer le menu principal dans la bande jaune et réserver la zone bleue au
   contenu ; préserver les trois boutons et les écrans FOOD/PLAY/STAT.
2. Ajouter le répertoire d'assets, le convertisseur pré-build PlatformIO et un
   BMP de test ; compiler pour vérifier la génération reproductible.
3. Remplacer les bitmaps codés à la main par des BMP originaux : idle, blink,
   happy, hungry, sad, sick et sleeping.
4. Ajouter les frames d'animation supplémentaires seulement après revue sur
   l'OLED réelle : contraste, centrage, lisibilité à distance et fluidité.
5. Documenter l'export des BMP et la convention de nommage dans le README.

## Validation

- La génération échoue clairement pour un BMP compressé, coloré ou trop grand.
- `pio run` régénère le header lorsque l'asset change.
- Les sprites sont vérifiés sur la dalle bicolore réelle, pas uniquement dans
  un éditeur d'image.
- Aucun asset issu d'une franchise existante n'est intégré au firmware.
