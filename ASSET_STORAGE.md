# Stockage des sprites sur W25Q64

## Architecture

Les BMP de `assets/tft/` restent l'unique source graphique modifiable. Avant
chaque compilation applicative ou du programmateur, `tools/generate_tft_assets.py` :

1. normalise en transparence les franges magenta reliées au fond et refuse
   toute nuance de matte résiduelle ;
2. valide les dimensions, l'échelle et la ligne de sol des animations ;
3. convertit les couleurs en RGB565 little-endian et conserve `#FF00FF` comme
   couleur réservée à la transparence ;
4. compresse chaque image avec le RLE décrit ci-dessous ;
5. génère le petit catalogue C++ `include/generated_tft_assets.h` ;
6. génère l'image de programmation dans
   `include/generated_tft_asset_blob.h`.

Le firmware normal n'inclut pas le blob. Il ne conserve en flash interne que
les identifiants et les constantes du catalogue. Les données compressées sont
lues depuis la W25Q64 dans un cache RAM unique de 112×112 pixels RGB565, soit
25 088 octets. Le nombre d'images peut donc augmenter sans augmenter ce cache.

## Format binaire version 1

Toutes les valeurs multioctets sont little-endian.

### En-tête de 24 octets

| Champ | Taille | Valeur ou rôle |
|---|---:|---|
| magic | 8 | `TAMASPR\0` |
| version | 2 | `1` |
| asset count | 2 | nombre d'entrées |
| catalog CRC32 | 4 | ordre et noms des BMP |
| image size | 4 | taille totale utilisée sur la W25Q64 |
| body CRC32 | 4 | table et données compressées |

### Entrée de catalogue de 16 octets

Chaque entrée contient l'offset absolu, la taille compressée, le CRC32 des
pixels RGB565 décompressés, la largeur et la hauteur. L'ordre alphabétique des
noms de fichiers définit les valeurs de `TftAssetId`.

### Compression RLE RGB565

Le flux alterne des paquets de 1 à 128 pixels :

- bit 7 à 0 : paquet littéral, suivi de `n` pixels RGB565 ;
- bit 7 à 1 : répétition, suivie d'un seul pixel RGB565 répété `n` fois ;
- dans les deux cas, `n = (octet & 0x7F) + 1`.

Ce RLE est retenu à la place de zlib car il se décode sans allocation, avec un
code court et une consommation déterministe. Sur les 33 sprites actuels,
827 904 octets RGB565 deviennent une image complète de 212 482 octets, table
comprise, soit 25,7 %. À complexité graphique comparable, les 8 Mio permettent
environ 1 290 images. Une compression plus complexe n'est donc pas nécessaire
à ce stade.

## Programmation par USB

Le programmateur est un firmware temporaire. Il vérifie le JEDEC `EF 40 17`,
compare d'abord l'image déjà présente pour éviter une réécriture inutile,
efface uniquement les secteurs occupés, programme par pages de 256 octets puis
compare chaque octet relu.

```bash
rtk /home/skyce/.platformio/penv/bin/pio run \
  -e asset-flash-programmer -t upload --upload-port /dev/ttyACM0
```

Attendre `ASSETS READY` sur le TFT et `ASSET FLASH OK` sur le port série, puis
réinstaller l'application :

```bash
rtk /home/skyce/.platformio/penv/bin/pio run \
  -e tamagotchi-30s-test -t upload --upload-port /dev/ttyACM0
```

Pour la version normale, remplacer l'environnement par
`esp32-c3-devkitm-1`.

## Ajout de frames

Ajouter les BMP 112×112 dans `assets/tft/`, étendre les groupes de validation
si nécessaire, puis compiler le programmateur. Après programmation réussie de
la W25Q64, compiler et téléverser l'application issue de la même révision. Le
CRC du catalogue empêche une application et une image d'assets dont la liste
ou l'ordre diffèrent de fonctionner silencieusement ensemble ; le CRC de
chaque image protège aussi son décodage.

La fréquence d'animation reste indépendante du format de stockage. Les paires
actuelles sont rendues en quatre phases de 180 ms avec un rebond de 1 px, sans
nouvelle keyframe ni interpolation graphique. Le cache unique charge une
nouvelle keyframe à la demande et réutilise la keyframe courante pour les
phases de rebond et les déplacements. Si une animation future descend largement
sous 100 ms par phase, mesurer d'abord le temps de chargement réel avant
d'envisager un second cache ou une prélecture.

Mesure sur le prototype à 8 MHz le 6 septembre 2026 : les 33 CRC sont validés
en 1,03 s, avec 35,5 ms pour la keyframe la plus lente. La cadence actuelle de
180 ms par phase dispose donc d'une marge importante ; une animation à 100 ms
reste plausible avant même toute optimisation du lecteur SPI.

Nouvelle mesure après nettoyage des contours, le 7 septembre 2026 : image
exacte de 212 482 octets et catalogue `84E4793D` confirmés par le programmateur,
33/33 CRC validés en 1,069 s, avec 36,451 ms au pire.
