# Handoff — Tamagotchi ESP32-C3

## État de reprise

Audit courant : `sprite-tool/INTEGRATION_AUDIT.md`. 199 tests passent, dont le
vrai décodeur embarqué sur 129 images ; défaut de cache INVALID corrigé.
`sprite-anim generate-rigged destination --root sprite-tool` reconstruit les
96 PNG des six marches et vérifie l'égalité aux lots approuvés, sans les remplacer.
Les illustrations d'autres états sont hors V1 marche selon le handoff ; restent
les essais sur carte. La validation stricte des variantes est implémentée : les
20 configurations V1–V4 restent acceptées, les 96 PNG approuvés sont reproduits
à l'identique. Compilation de la variante 30 secondes revérifiée le 10 septembre.

Choix utilisateur confirmé : mascotte choisie à la création, puis persistée.
Le registre commun `include/mascot_walks.h` est utilisé par HOME pour les six espèces ;
la cible `mascot-walk-test` permet de parcourir les six marches sans sauvegarde
(gauche/droite : espèce, OK : pause). Compilation réussie, 169 tests hôte passent.
Migration v7 vers v8, choix à la création et protection du démarrage implémentés
(dragon conservé pour v7) : 172 tests passent ; jeu principal et variante 30s
compilent. HOME utilise l'espèce sauvegardée ; les états non illustrés gardent
provisoirement sa pose immobile. Voir `sprite-tool/CREATION_SELECTION.md`.
Aucun téléversement ; ne pas revenir au
firmware v0.7 après migration v8 sans procédure de restauration.

Inflexion animation choisie le 9 septembre 2026 : les cycles rigides ci-dessous
sont jugés non convaincants et écartés comme direction artistique. On construit
désormais un mannequin articulé à huit poses avant l'habillage pixel art.
Premier jalon : [étude du dragon sans détails](sprite-tool/MOTION_STUDY.md),
dont la marche est désormais approuvée par l'utilisateur (« marche parfaite »).
La référence d'habillage V3 et le cycle corrigé sont approuvés (« top », puis
« oui, validé. »). Le [cycle habillé](sprite-tool/RIGGED_WALK.md) est intégré au
lecteur HOME : huit poses à 120 ms, 3 pixels par pose, sans rebond ajouté.
Les 16 BMP du dragon et les 80 BMP des cinq marches V4 validées s'ajoutent aux
33 anciens conservés : catalogue de 129 images, image W25Q64 de 476646 octets.
Les 80 nouveaux BMP sont liés aux lots approuvés par `assets/tft/mascot_walks_approval.json`.
Le lecteur HOME utilise la mascotte choisie à la création ; les autres états
gardent sa pose immobile en attendant une phase artistique distincte.
Les quatre cibles jeu/30s/programmeur/test stockage compilent ;
aucun téléversement ni essai TFT effectué. Le handoff
animation contient la décision prioritaire. Les six références restent intactes.

Nettoyage du 9 septembre 2026 : les expérimentations de marche, leur lecteur,
leurs tests et leur diagnostic ont été retirés du dépôt de travail. Le socle
conserve le firmware v0.7, ses 33 assets de production et les dix environnements
PlatformIO historiques. Aucun téléversement n'a été effectué pendant ce nettoyage.

Les six références de mascottes sont recensées dans `design/README.md` : dragon
de production et cinq modèles approuvés dans `design/mascots-v1/APPROVAL.json`.
Leurs images, sources, aperçus et preuves d'approbation sont conservés.
Le générateur déterministe hors ligne décrit dans
`HANDOFF_CODEX_MOTEUR_ANIMATION_SPRITES.md` est en cours dans `sprite-tool/`.
La composition entière, les profils à six étapes, la CLI, les prévisualisations,
l'approbation et les exports sont implémentés avec deux fixtures géométriques.
Voir `sprite-tool/README.md` pour les commandes et `sprite-tool/ASSET_PREPARATION.md`
pour le travail restant sur les vrais modèles. Un premier cycle de diagnostic du
dragon utilise huit calques issus d'une keyframe de production, un patch explicite
et des translations rigides. Les cinq autres modèles disposent aussi de calques
et de cycles rigides candidats ; la génération des six produit 72 PNG et ses
sorties sont comparées octet par octet dans les tests. Les raccords de queue
exposés sont traités par des patches explicites. Voir `sprite-tool/mascots/README.md`.
Les poses alternatives dessinées, la validation artistique des mouvements/vues
latérales des cinq autres mascottes restent à réaliser. Ce diagnostic rigide n'est
pas la direction retenue : le dragon sur rig est désormais approuvé et intégré
au firmware (voir l'état en tête du document), mais pas encore vérifié sur TFT.
Les validations matérielles ci-dessous concernent la v0.7, pas ce futur moteur.

Le firmware actif est un projet PlatformIO Arduino C++ pour ESP32-C3. Le seul
affichage géré est désormais le TFT IPS ZJY154S0800TG01 240×240. La chaîne
graphique historique 1-bit et la dépendance SSD1306 ont été retirées.

- firmware : `v0.7` ; schéma NVS : `7` ;
- veille automatique après 10 minutes sans interaction ;
- HOME, navigation partielle et jauges à cinq segments validés visuellement
  après la migration finale ;
- 33 BMP couleur couvrent tous les sprites et animations ;
- boot, œuf, éclosion, HOME, FOOD, PLAY, MEDICINE, CLEAN, SLEEP, STATUS et
  pré-veille sont rendus nativement sur le TFT ;
- compilation et téléversement de la migration complète validés ; les 33 assets
  couleur et leurs animations normalisées ont été validés sur le TFT réel ;
- câblage final TFT/W25Q64/PCF8523 et extinction BLK en deep sleep validés.
- support RTC implémenté : initialisation conditionnelle, âge hors tension,
  rattrapage des stats plafonné à 24 h et heure visible dans STATUS ; RTC et
  rattrapage deep sleep validés sur la carte réelle.

Les pixels des sprites sont stockés sur la W25Q64 dans un format RLE. L'image,
le diagnostic des 33 CRC, leur défilement et toutes les animations dans
l'application normale ont été validés sur le prototype réel.

Instantané au 7 septembre 2026 : la v0.7 RTC est téléversée sur le prototype en
configuration normale avec veille à 10 minutes. Le PCF8523 a été initialisé une
fois depuis l'heure de compilation, puis préservé au redémarrage. Le diagnostic
a observé l'oscillateur actif, les secondes croissantes et un réveil GPIO avec
32 secondes réappliquées à l'âge et aux stats. Après coupure USB complète, le
diagnostic a retrouvé l'heure préservée à `22:38:27`, puis `TICK OK` jusqu'à
`22:38:40`. Le firmware normal à 10 minutes a ensuite été restauré.

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
Le PCF8523 répond à `0x68` et la pile CR1220 est désormais installée.

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
- Adafruit RTClib ;
- `SPI` et `Preferences` fournis par le framework.

### Fichiers principaux

- `src/main.cpp` : simulation, écrans TFT, boutons et audio ;
- `src/persistence.cpp` : sérialisation NVS ;
- `src/rtc_clock.cpp` : initialisation et lecture robuste du PCF8523 ;
- `include/config.h` : pinout, versions et temporisations ;
- `assets/tft/*.bmp` : source graphique couleur unique ;
- `tools/generate_tft_assets.py` : BMP vers image W25Q64 RLE RGB565 ;
- `include/generated_tft_assets.h` : catalogue léger généré et versionné ;
- `include/generated_tft_asset_blob.h` : image compressée du programmateur ;
- `src/external_flash.cpp` : lecture, effacement et programmation W25Q64 ;
- `src/tft_asset_store.cpp` : validation, décodage et cache d'une frame ;
- `ASSET_STORAGE.md` : format et procédure de mise à jour des assets ;
- `ANIMATION_GUIDELINES.md` : contraintes graphiques du futur moteur ;
- `HANDOFF_CODEX_MOTEUR_ANIMATION_SPRITES.md` : source documentaire et plan du générateur hors ligne ;
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

Compilation applicative avec les pixels des 33 sprites retirés de la flash
interne et un cache RAM RGB565 de 25 088 octets :

- flash : 27,1 %, soit 355 234 octets sur 1 310 720 ;
- RAM statique : 12,5 %, soit 40 888 octets sur 327 680.

Il n'y a pas de framebuffer 240×240 permanent, qui demanderait 115 200 octets.

## Fonctionnalités

Menu : FOOD, PLAY, MEDICINE, CLEAN, SLEEP et STATUS. Gauche/droite déplacent
la sélection ; OK valide. Le debounce est non bloquant, après 35 ms stables.

Le dragon commence dans un œuf. Trois validations de FOOD le réchauffent et
le font éclore. Il devient jeune après 5 minutes puis adulte 15 minutes plus
tard. Ces durées sont volontairement courtes pour le prototype.

Les cinq statistiques restent bornées à 0..100. Les traits d'appétit, de jeu
et d'entêtement sont persistés dans NVS avec le stade, la chaleur, l'âge 64 bits
et l'ancre Unix du RTC.
Maintenir gauche et droite cinq secondes efface la sauvegarde.

Le temps écoulé pendant une veille ou une coupure est ajouté à l'âge au prochain
démarrage. Les mêmes règles de simulation sont rejouées chronologiquement, avec
un plafond de 24 h pour les jauges seulement. Un écart RTC supérieur à 366 jours,
une horloge reculée ou une horloge qui vient d'être réinitialisée est rejeté.

## Deep sleep

- déclenchement après 10 minutes sans interaction ;
- écran GOOD NIGHT pendant 1 seconde ;
- sauvegarde NVS immédiate ;
- contrôleur TFT désactivé avec `enableDisplay(false)` ;
- BLK GPIO10 maintenu à LOW pendant le deep sleep ;
- réveil par OK, GPIO3 à LOW.

Le cycle complet a été validé sur le prototype. Une cible
`tamagotchi-30s-test` conserve l'application complète avec un délai de
30 secondes pour les essais ; elle attend aussi 10 secondes avant le journal
de démarrage afin que le moniteur USB récupère les preuves RTC. La cible normale
conserve 10 minutes et ne reçoit pas ce délai de diagnostic. La cible de test
répète en plus toutes les 5 secondes un résumé `RTC SUMMARY` avec cause de
réveil, temps hors ligne, âge et heure, afin que la preuve reste récupérable
même si Linux renumérote le port USB après un deep sleep.

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
flash externe contient maintenant l'image RLE des sprites dans ses premiers
214 128 octets. Aucun système de fichiers n'est encore choisi. La pile CR1220
est installée. Le rattrapage après deep sleep, la conservation de l'heure après
coupure USB complète et l'affichage de l'heure dans STATUS sont validés sur le
prototype réel.

## Assets graphiques

- 33 BMP 112×112 dans `assets/tft/` ;
- magenta `#FF00FF` = transparence ;
- formats BMP non compressés 8 ou 24 bits ;
- pixels RGB565 compressés en RLE sur W25Q64 ;
- cache unique de 112×112 pixels en RAM, indépendant du nombre de frames ;
- génération automatique avant chaque build ;
- contrôle automatique de l'échelle : 5 000 à 7 300 pixels visibles par
  dragon, ratio maximal de 1,12 et écart de ligne de sol maximal de 3 pixels
  dans chaque famille animée.

Version graphique validée au 7 septembre 2026 : le générateur convertit en
transparence 1 325 pixels de frange magenta reliés au fond sur 17 assets et
refuse toute nuance de matte résiduelle. Les paires de keyframes sont rendues en
quatre phases de 180 ms avec un rebond de 1 px, sans redessiner le dragon. Les
dix environnements PlatformIO compilent. L'image de 212 482 octets est
programmée, son catalogue `84E4793D` est confirmé et ses 33 CRC passent en
1,069 s, avec 36,451 ms au pire.
Les contours, le nouveau rythme, toutes les actions, l'absence de rognage et de
scintillement sont validés par l'utilisateur sur le TFT réel.

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
| `hardware-expansion-test` | câblage, RTC horodaté et JEDEC SPI en lecture seule |
| `deep-sleep-test` | extinction BLK et réveil OK après 5 secondes |
| `tamagotchi-30s-test` | application complète, veille après 30 secondes |
| `asset-flash-programmer` | écrit et vérifie l'image RLE sur la W25Q64 |
| `asset-storage-test` | valide les 33 CRC, mesure les lectures et fait défiler les sprites |

Tous utilisent le pinout de `include/config.h`. Les diagnostics autonomes sont
exclus du firmware applicatif normal.

## Validation de clôture

| Contrôle | État au 7 septembre 2026 |
|---|---|
| Génération RLE des 33 BMP | validée, 214 128 octets, round-trip vérifié |
| Compilation du firmware normal externe | validée, 355 234 octets flash et 40 888 octets RAM |
| Compilation des dix environnements PlatformIO | validée avec la v0.7 RTC |
| Téléversement sur `/dev/ttyACM0` et vérification du hash | validé |
| HOME, jauges à cinq segments et navigation sans clignotement | validés sur le TFT |
| 33 assets, couleurs, échelle, ancrages et animations | validés par l'utilisateur sur le TFT |
| `NO MEDICINE`, taille et yeux canoniques | validé dans le lot graphique |
| PCF8523 à `0x68`, oscillateur et secondes | validés sur le matériel, `TICK OK` |
| Compilation v0.7 normale, veille 30 s et diagnostic RTC | validée statiquement et téléversée |
| Réveil GPIO et rattrapage après deep sleep | validés : `wake=7`, `elapsed=32 s` |
| Conservation RTC après coupure USB complète | validée, `TIME PRESERVED` et `TICK OK` |
| Heure dans STATUS | validée visuellement par l'utilisateur |
| W25Q64 JEDEC `EF 40 17` | validée sur le matériel |
| TFT, boutons et buzzer avec le câblage final | validés sur le matériel |
| `git diff --check` | validé |
| Veille réelle, BLK et LED bleue éteints, réveil GPIO3 | validés avec la cible applicative 30 s |
| Programmation et vérification de l'image RLE sur W25Q64 | validée, 214 128 octets, catalogue `84E4793D` |
| Lecture et CRC des 33 sprites depuis W25Q64 | validés, 1,03 s au total, maximum 35,5 ms |
| Défilement des 33 sprites depuis W25Q64 | validé visuellement sans corruption ni scintillement |
| Animations de l'application normale lues depuis W25Q64 | validées visuellement par l'utilisateur |

Commandes de reprise dans l'environnement Codex :

```bash
rtk /home/skyce/.platformio/penv/bin/pio run
rtk /home/skyce/.platformio/penv/bin/pio run -e esp32-c3-devkitm-1 -e tamagotchi-30s-test -e asset-flash-programmer -e asset-storage-test -e st7789-test -e gpio-test -e raw-st7789-test -e hardware-st7789-test -e hardware-expansion-test -e deep-sleep-test
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
