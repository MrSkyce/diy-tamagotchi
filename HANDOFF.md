# Handoff — Tamagotchi ESP32-C3

## État de reprise

Le firmware actif est un projet PlatformIO Arduino C++ pour ESP32-C3. Le seul
affichage géré est désormais le TFT IPS ZJY154S0800TG01 240×240. La chaîne
graphique historique 1-bit et la dépendance SSD1306 ont été retirées.

- firmware : `v0.6` ; schéma NVS : `6` ;
- veille automatique après 10 minutes sans interaction ;
- HOME, navigation partielle et jauges à cinq segments validés visuellement
  après la migration finale ;
- 33 BMP couleur couvrent tous les sprites et animations ;
- boot, œuf, éclosion, HOME, FOOD, PLAY, MEDICINE, CLEAN, SLEEP, STATUS et
  pré-veille sont rendus nativement sur le TFT ;
- compilation et téléversement de la migration complète validés ; les 33 assets
  couleur et leurs animations normalisées ont été validés sur le TFT réel.

Instantané au 5 septembre 2026 : la migration TFT couleur est terminée et
validée, mais elle n'est pas encore commitée. La branche `main` et
`origin/main` pointent encore sur `ee51f16`; le worktree contient l'intégralité
de la migration. Ne pas nettoyer ni restaurer ces changements. La prochaine
action Git est à effectuer uniquement sur demande explicite.

### Diff attendu avant commit

Les suppressions massives visibles dans `git status` sont intentionnelles :

- ancien sketch racine `TamagotchiESP32C3.ino` ;
- anciens BMP monochromes dans `assets/boot/`, `assets/sprites/` et
  `assets/sprites_24x24_backup/` ;
- anciens headers `include/generated_sprites.h` et `include/sprites.h` ;
- anciens outils `draft_boot_eggs.py`, `draft_dragon_sprites.py`,
  `generate_sprites.py` et `scale_sprites.py`.

Ils sont remplacés par `assets/tft/`, `tools/generate_tft_assets.py` et
`include/generated_tft_assets.h`. Ces trois chemins sont encore non suivis tant
que la migration n'a pas été ajoutée à Git ; ne pas oublier de les inclure lors
du futur `git add -A`.

## Matériel

### Microcontrôleur

- AYWHP ESP32-C3, format proche ESP32-C3 SuperMini ;
- cible PlatformIO : `esp32-c3-devkitm-1` ;
- USB CDC à 115200 bauds ; port observé : `/dev/ttyACM0` ;
- identifiant USB observé : `303A:1001`.

### TFT IPS

- ZJY154S0800TG01, 1,54 pouce, ST7789, 240×240 ;
- SPI matériel mode 3 à 32 MHz, écriture seule ;
- `SCL` = SCLK GPIO4, `SDA` = MOSI GPIO6 ;
- DC GPIO7, RESET GPIO20 ;
- CS actif à LOW relié à GND, donc `CS = -1` dans Adafruit ;
- VCC et BLK reliés au 3,3 V ;
- écran retourné physiquement : `setRotation(0)`, inversion active et offset
  Adafruit natif de 80 lignes.

### Autres broches

| Fonction | GPIO | Notes |
|---|---:|---|
| Libre | 0 | ancien SDA, écran physiquement déconnecté |
| Libre | 1 | ancien SCL, écran physiquement déconnecté |
| Bouton gauche | 21 | `INPUT_PULLUP`, bouton vers GND |
| Bouton OK | 3 | `INPUT_PULLUP`, réveil deep sleep |
| Bouton droite | 10 | `INPUT_PULLUP`, bouton vers GND |
| Buzzer passif | 5 | GPIO4 réservé au SCLK |
| TFT SCLK | 4 | SPI matériel |
| TFT MOSI | 6 | SPI matériel |
| TFT DC | 7 | commande/données |
| TFT RESET | 20 | actif à LOW |
| TFT CS | GND | sélection permanente |

GPIO0 et GPIO1 ne sont plus initialisés ni utilisés par le firmware. Ils sont
disponibles pour une extension future, sous réserve de valider le nouveau
câblage sur la carte réelle.

## Paramètres ST7789 validés

```text
interface       SPI matériel
mode            SPI_MODE3
fréquence       32 MHz
format pixels   RGB565
inversion IPS   active
taille          240 × 240
orientation     Adafruit rotation 0
offset          offset Adafruit natif de 80 lignes
CS              relié à GND
MISO            absent
```

Le mode 0 laisse cette dalle noire. Sans inversion, les couleurs apparaissent
complémentaires. Avec le pilote Adafruit en rotation 0, ne pas forcer l'offset
à zéro : cela décale l'image d'un tiers vers le bas.

## Architecture logicielle

### Dépendances normales

- framework Arduino ESP32 ;
- Adafruit GFX Library ;
- Adafruit ST7735 and ST7789 Library ;
- `SPI` et `Preferences` fournis par le framework.

### Fichiers principaux

- `src/main.cpp` : simulation, écrans TFT, boutons et audio ;
- `src/persistence.cpp` : sérialisation NVS ;
- `include/config.h` : pinout, versions et temporisations ;
- `assets/tft/*.bmp` : source graphique couleur unique ;
- `tools/generate_tft_assets.py` : BMP vers RGB565 et masque ;
- `include/generated_tft_assets.h` : header généré et versionné ;
- `HARDWARE_EXPANSION_PLAN.md` : futur pinout W25Q64, PCF8523 et BLK ;
- `platformio.ini` : firmware et environnements de diagnostic.

`presentDisplay()` appelle directement le compositeur TFT. Il n'existe plus de
framebuffer secondaire, de conversion à l'exécution ni de rendu hybride.

### Prévention du clignotement

- sur HOME, une navigation ne redessine que les deux cases concernées ;
- une variation de statistique ne redessine que sa zone 40×32 ;
- les animations remplacent directement la zone du sprite ;
- ne pas remettre `fillScreen()` dans un chemin périodique.

### Occupation mesurée

Compilation avec 33 sprites TFT couleur et sans bibliothèque SSD1306 :

- flash : 90,4 %, soit 1 184 310 octets sur 1 310 720 ;
- RAM statique : 4,7 %, soit 15 464 octets sur 327 680.

Il n'y a pas de framebuffer 240×240 permanent, qui demanderait 115 200 octets.

## Fonctionnalités

Menu : FOOD, PLAY, MEDICINE, CLEAN, SLEEP et STATUS. Gauche/droite déplacent
la sélection ; OK valide. Le debounce est non bloquant, après 35 ms stables.

Le dragon commence dans un œuf. Trois validations de FOOD le réchauffent et
le font éclore. Il devient jeune après 5 minutes puis adulte 15 minutes plus
tard. Ces durées sont volontairement courtes pour le prototype.

Les cinq statistiques restent bornées à 0..100. Les traits d'appétit, de jeu
et d'entêtement sont persistés dans NVS avec le stade, la chaleur et l'âge.
Maintenir gauche et droite cinq secondes efface la sauvegarde.

## Deep sleep

- déclenchement après 10 minutes sans interaction ;
- écran GOOD NIGHT pendant 1 seconde ;
- sauvegarde NVS immédiate ;
- contrôleur TFT désactivé avec `enableDisplay(false)` ;
- réveil par OK, GPIO3 à LOW.

`BLK` reste alimenté au 3,3 V. Pour une vraie économie d'énergie, le piloter
via un GPIO adapté et éventuellement un transistor.

## Extension matérielle en préparation

Le câblage cible est spécifié dans `HARDWARE_EXPANSION_PLAN.md`. Il ajoute :

- W25Q64 2,7–3,6 V sur le bus SPI partagé, CS GPIO2 et MISO GPIO20 ;
- TFT CS déplacé de GND vers GPIO9 ;
- TFT RESET déplacé de GPIO20 vers EN/RST ;
- commande BLK par GPIO8 via transistor PNP BC327, active à LOW ;
- RTC Adafruit PCF8523 sur SDA GPIO0 et SCL GPIO1, adresse `0x68` ;
- `SQW` non connecté pour la première intégration.

État au 5 septembre 2026 : documentation prête, câblage en cours, aucun support
logiciel encore ajouté. Le firmware actuel ne doit pas être utilisé avec MISO
relié à GPIO20, car cette broche est encore configurée comme RESET du TFT.

## Assets graphiques

- 33 BMP 112×112 dans `assets/tft/` ;
- magenta `#FF00FF` = transparence ;
- formats BMP non compressés 8 ou 24 bits ;
- pixels RGB565 et masques 1-bit précompilés dans `PROGMEM` ;
- génération automatique avant chaque build ;
- contrôle automatique de l'échelle : 5 000 à 7 300 pixels visibles par
  dragon, ratio maximal de 1,12 et écart de ligne de sol maximal de 2 pixels
  dans chaque famille animée.

Le lot couvre idle, clignement, émotions, fatigue, marche dans les deux sens,
FOOD, PLAY, MEDICINE, CLEAN, sommeil accepté/refusé/profond, rotation de l'œuf,
fissures et éclosion.

## Diagnostics PlatformIO

| Environnement | Usage |
|---|---|
| `esp32-c3-devkitm-1` | application normale |
| `gpio-test` | contrôle des broches |
| `raw-st7789-test` | pilote brut bit-bang mode 3 |
| `hardware-st7789-test` | SPI matériel brut |
| `st7789-test` | Adafruit et couleurs |

Tous utilisent le pinout de `include/config.h`. `gpio-test` couvre uniquement
SCLK, MOSI, DC et RESET ; GPIO0/1 restent libres et GPIO5 reste réservé au
buzzer.

## Validation de clôture

| Contrôle | État au 5 septembre 2026 |
|---|---|
| Génération des 33 BMP vers `generated_tft_assets.h` | validée |
| Compilation du firmware normal | validée, flash 90,4 %, RAM 4,7 % |
| Compilation des cinq environnements PlatformIO | validée |
| Téléversement sur `/dev/ttyACM0` et vérification du hash | validé |
| HOME, jauges à cinq segments et navigation sans clignotement | validés sur le TFT |
| 33 assets, couleurs, échelle, ancrages et animations | validés par l'utilisateur sur le TFT |
| `NO MEDICINE`, taille et yeux canoniques | validé dans le lot graphique |
| Absence de SSD1306, OLED et initialisation I2C dans le code actif | validée par recherche |
| `git diff --check` | validé |
| Veille réelle après 10 minutes et réveil GPIO3 avec cette migration | à revalider avant une release matérielle |

Commandes de reprise dans l'environnement Codex :

```bash
rtk /home/skyce/.platformio/penv/bin/pio run
rtk /home/skyce/.platformio/penv/bin/pio run -e esp32-c3-devkitm-1 -e st7789-test -e gpio-test -e raw-st7789-test -e hardware-st7789-test
rtk /home/skyce/.platformio/penv/bin/pio run -t upload --upload-port /dev/ttyACM0
rtk git diff --check
rtk git status --short --branch
```

Si aucune autre retouche n'est demandée, revalider la veille à 10 minutes puis,
sur instruction explicite seulement, ajouter, commiter et pousser l'ensemble de
la migration.

La disparition de `/dev/ttyACM0` après deep sleep est normale. Un appui sur OK
réveille la carte.

## Contraintes

- ne pas modifier le pinout sans vérifier le câblage réel ;
- conserver SPI mode 3, 32 MHz, inversion et offset validés ;
- préserver les timers et le lecteur audio non bloquants ;
- incrémenter ensemble version firmware et version NVS seulement lors d'une
  évolution incompatible du format sauvegardé ;
- le TFT avec CS à GND ne peut pas partager simplement le bus avec la W25Q64 ;
- valider l'UI sur l'appareil réel avant commit.
