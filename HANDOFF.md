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
  couleur et leurs animations normalisées ont été validés sur le TFT réel ;
- câblage final TFT/W25Q64/PCF8523 et extinction BLK en deep sleep validés.

Instantané au 6 septembre 2026 : le câblage d'extension et son support logiciel
ont été validés sur le prototype réel. Les changements correspondants sont
encore dans le worktree et ne doivent être commités qu'après instruction.

## Matériel

### Microcontrôleur

- AYWHP ESP32-C3, format proche ESP32-C3 SuperMini ;
- cible PlatformIO : `esp32-c3-devkitm-1` ;
- USB CDC à 115200 bauds ; port observé : `/dev/ttyACM0` ;
- identifiant USB observé : `303A:1001`.

### TFT IPS

- ZJY154S0800TG01, 1,54 pouce, ST7789, 240×240 ;
- SPI matériel mode 3 à 32 MHz pour l'affichage ;
- `SCL` = SCLK GPIO4, `SDA` = MOSI GPIO6 ;
- DC GPIO7, CS GPIO9 avec pull-up 10 kΩ ;
- RESET autonome par réseau RC 10 kΩ/100 nF, `RST = -1` dans Adafruit ;
- VCC 3,3 V, BLK piloté directement par GPIO10 ;
- écran retourné physiquement : `setRotation(0)`, inversion active et offset
  Adafruit natif de 80 lignes.

### Autres broches

| Fonction | GPIO | Notes |
|---|---:|---|
| RTC SDA | 0 | PCF8523, pull-up sur le breakout |
| RTC SCL | 1 | PCF8523, pull-up sur le breakout |
| Flash CS | 2 | W25Q64, pull-up externe 10 kΩ |
| Bouton gauche | 21 | `INPUT_PULLUP`, bouton vers GND |
| Bouton OK | 3 | `INPUT_PULLUP`, réveil deep sleep |
| Bouton droite | 8 | `INPUT_PULLUP`, bouton vers GND ; LED bleue active à LOW |
| Buzzer passif | 5 | GPIO4 réservé au SCLK |
| TFT SCLK | 4 | SPI matériel |
| TFT MOSI | 6 | SPI matériel |
| TFT DC | 7 | commande/données |
| TFT CS | 9 | actif à LOW, pull-up externe 10 kΩ |
| TFT BLK | 10 | HIGH allumé, LOW éteint et maintenu en deep sleep |
| Flash MISO | 20 | W25Q64 DO/IO1 |

Le TFT et la W25Q64 partagent SCLK GPIO4 et MOSI GPIO6. La flash utilise
GPIO2 comme CS. Son identifiant JEDEC lu sans écriture est `EF 40 17`.
Le PCF8523 répond à `0x68` ; sans CR1220, son oscillateur est arrêté.

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
CS              GPIO9
MISO            GPIO20, utilisé par la W25Q64
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
- `HARDWARE_EXPANSION_PLAN.md` : câblage cible exhaustif depuis zéro ;
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

- flash : 91,7 %, soit 1 202 584 octets sur 1 310 720 ;
- RAM statique : 4,8 %, soit 15 720 octets sur 327 680.

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
- BLK GPIO10 maintenu à LOW pendant le deep sleep ;
- réveil par OK, GPIO3 à LOW.

Le cycle complet a été validé sur le prototype. Une cible
`tamagotchi-30s-test` conserve l'application complète avec un délai de
30 secondes pour les essais ; la cible normale conserve 10 minutes.

## Extension matérielle validée

Le câblage exhaustif est spécifié dans `HARDWARE_EXPANSION_PLAN.md` :

- W25Q64 2,7–3,6 V sur le bus SPI partagé, CS GPIO2 et MISO GPIO20 ;
- TFT CS déplacé de GND vers GPIO9 ;
- TFT RESET autonome avec 10 kΩ vers 3,3 V et 100 nF vers GND, sans GPIO ;
- BLK relié directement à GPIO10 grâce au S8050 intégré au module, HIGH = allumé
  et LOW = éteint ;
- bouton droit déplacé de GPIO10 vers GPIO8 ;
- RTC Adafruit PCF8523 sur SDA GPIO0 et SCL GPIO1, adresse `0x68` ;
- `SQW` non connecté pour la première intégration.

État au 6 septembre 2026 : affichage, boutons, buzzer, RTC, lecture JEDEC,
absence de scintillement, extinction BLK et réveil OK validés sur la carte. La
flash externe n'a subi aucune écriture ni aucun effacement. Aucun système de
fichiers n'est encore choisi. La conservation RTC reste à tester après ajout
d'une pile CR1220.

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
| `hardware-expansion-test` | câblage, RTC et JEDEC en lecture seule |
| `deep-sleep-test` | extinction BLK et réveil OK après 5 secondes |
| `tamagotchi-30s-test` | application complète, veille après 30 secondes |

Tous utilisent le pinout de `include/config.h`. Les diagnostics autonomes sont
exclus du firmware applicatif normal.

## Validation de clôture

| Contrôle | État au 6 septembre 2026 |
|---|---|
| Génération des 33 BMP vers `generated_tft_assets.h` | validée |
| Compilation du firmware normal | validée, flash 91,7 %, RAM 4,8 % |
| Compilation des huit environnements PlatformIO | validée après le dernier essai matériel |
| Téléversement sur `/dev/ttyACM0` et vérification du hash | validé |
| HOME, jauges à cinq segments et navigation sans clignotement | validés sur le TFT |
| 33 assets, couleurs, échelle, ancrages et animations | validés par l'utilisateur sur le TFT |
| `NO MEDICINE`, taille et yeux canoniques | validé dans le lot graphique |
| PCF8523 à `0x68`, sans pile et oscillateur arrêté | validé sur le matériel |
| W25Q64 JEDEC `EF 40 17`, sans écriture/effacement | validée sur le matériel |
| TFT, boutons et buzzer avec le câblage final | validés sur le matériel |
| `git diff --check` | validé |
| Veille réelle, BLK et LED bleue éteints, réveil GPIO3 | validés avec la cible applicative 30 s |

Commandes de reprise dans l'environnement Codex :

```bash
rtk /home/skyce/.platformio/penv/bin/pio run
rtk /home/skyce/.platformio/penv/bin/pio run -e esp32-c3-devkitm-1 -e tamagotchi-30s-test -e st7789-test -e gpio-test -e raw-st7789-test -e hardware-st7789-test -e hardware-expansion-test -e deep-sleep-test
rtk /home/skyce/.platformio/penv/bin/pio run -t upload --upload-port /dev/ttyACM0
rtk git diff --check
rtk git status --short --branch
```

Avant commit, recompiler toutes les cibles puis, sur instruction explicite
seulement, ajouter, commiter et pousser l'ensemble de l'intégration.

La disparition de `/dev/ttyACM0` après deep sleep est normale. Un appui sur OK
réveille la carte.

## Contraintes

- ne pas modifier le pinout sans vérifier le câblage réel ;
- conserver SPI mode 3, 32 MHz, inversion et offset validés ;
- préserver les timers et le lecteur audio non bloquants ;
- incrémenter ensemble version firmware et version NVS seulement lors d'une
  évolution incompatible du format sauvegardé ;
- préserver les CS distincts GPIO9 (TFT) et GPIO2 (W25Q64) sur le bus partagé ;
- valider l'UI sur l'appareil réel avant commit.
