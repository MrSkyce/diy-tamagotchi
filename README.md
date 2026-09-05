# Tamagotchi ESP32-C3

Prototype de Tamagotchi DIY basé sur ESP32-C3, TFT IPS ZJY154S0800TG01
1,54 pouce (ST7789, 240×240), trois boutons et buzzer passif.

## V0.6 : firmware actuel

Le projet PlatformIO est compilable pour `esp32-c3-devkitm-1`, l'équivalent
PlatformIO retenu pour la configuration Arduino validée `ESP32C3 Dev Module`.

```bash
pio run
pio run --target upload
pio device monitor --baud 115200
```

PlatformIO télécharge automatiquement le framework Arduino ESP32 et les
bibliothèques Adafruit déclarées dans `platformio.ini`.

### Structure

- `src/main.cpp` : comportement applicatif actuel.
- `include/config.h` : pinout et configuration écran.
- `assets/tft/` : unique source de vérité des sprites BMP couleur.
- `tools/generate_tft_assets.py` : génère les pixels RGB565 et masques TFT.
- `include/generated_tft_assets.h` : assets TFT couleur générés.
- `GRAPHICS_PLAN.md` : contrat graphique et couverture des écrans.
- `HARDWARE_EXPANSION_PLAN.md` : câblage cible W25Q64, PCF8523 et BLK.
- `HANDOFF.md` : contexte et roadmap.

### Écran IPS ST7789

Le firmware affiche une interface native colorée 240×240 sur le ST7789 avec
Adafruit GFX. Le module actuel est un ZJY154S0800TG01 de 1,54 pouce. Sa broche
`CS`, active à LOW, est reliée
à GND ; le pilote utilise donc `-1` comme broche CS. Il est validé en SPI
matériel mode 3 à 32 MHz,
avec l'inversion IPS active et l'offset Adafruit de 80 lignes correspondant à
l'orientation retournée du montage. Les jauges TFT ne sont redessinées que
lorsque leur valeur change afin d'éviter le clignotement.

HOME, FOOD, PLAY, MEDICINE, CLEAN, SLEEP, STATUS, le boot, le stade œuf,
l'éclosion et l'annonce de mise en veille ont tous leur composition TFT native.
Le HOME réunit six indicateurs à cinq segments, un décor couleur, un sprite
112×112 et six icônes d'action. Aucun framebuffer d'écran intermédiaire n'est
alloué.

Des environnements PlatformIO autonomes conservent les diagnostics GPIO,
SPI brut, SPI matériel et Adafruit sans les inclure dans le firmware normal.

```bash
pio run -e gpio-test
pio run -e raw-st7789-test
pio run -e hardware-st7789-test
pio run -e st7789-test
```

Ces diagnostics utilisent tous le pinout central de `include/config.h`.
`gpio-test` ne pilote que SCLK, MOSI, DC et RESET ; il ne touche ni aux GPIO0/1
libérés ni au GPIO5 réservé au buzzer.

Le diagnostic matériel a établi que le mode 0 laisse cette dalle noire, que
`INVON` est nécessaire pour obtenir les couleurs attendues et que l'offset
dépend de l'orientation : zéro avec le pilote brut en `MADCTL=0`, mais 80 avec
Adafruit en rotation 0. Ne pas transposer un offset d'un pilote à l'autre.

## Pinout

- GPIO0 : libre, ancien SDA de l'écran retiré
- GPIO1 : libre, ancien SCL de l'écran retiré
- A / Left : GPIO21
- B / OK : GPIO3
- C / Right : GPIO10
- Buzzer : GPIO5
- TFT SCK : GPIO4
- TFT MOSI / SDA : GPIO6
- TFT DC : GPIO7
- TFT RESET : GPIO20
- TFT CS : GND (sélection permanente)
- TFT VCC et BLK : 3,3 V

Les boutons sont câblés entre le GPIO et GND et utilisent les résistances de
tirage internes (`INPUT_PULLUP`).
Chaque appui est validé après 35 ms stables afin d'éliminer les rebonds
mécaniques, sans bloquer la boucle principale.

Le TFT dont `CS` est relié à GND ne peut pas partager simplement son bus avec
la mémoire W25Q64 : celle-ci reste volontairement non câblée. Sans `MISO`, le firmware ne
peut pas lire les registres du contrôleur. Enfin, `BLK` étant relié directement
au 3,3 V, le rétroéclairage reste alimenté même lorsque le contrôleur TFT est
désactivé avant le deep sleep.

### Extension matérielle en cours de câblage

Le pinout cible pour partager le bus SPI avec un W25Q64 3,3 V, ajouter un RTC
Adafruit PCF8523 et couper réellement BLK est décrit dans
`HARDWARE_EXPANSION_PLAN.md`. Ce pinout n'est pas encore actif dans le firmware :
GPIO20 reste pour l'instant une sortie RESET du TFT. Ne pas connecter le MISO
du W25Q64 à GPIO20 avant le téléversement du firmware adapté.

Le plan cible utilise GPIO0/1 pour le PCF8523, GPIO2 pour le CS du W25Q64,
GPIO8 pour BLK via un transistor PNP BC327, GPIO9 pour le CS du TFT et GPIO20
pour MISO. Le RESET du TFT sera relié à EN/RST. `SQW` du PCF8523 reste
déconnecté lors de la première intégration.

La barre inférieure du HOME expose six icônes : FOOD, PLAY, MEDICINE, CLEAN,
SLEEP et STATUS. L'icône sélectionnée est mise en évidence et le nom complet de
l'action apparaît dans l'en-tête de son écran. Le dragon exprime aussi la
fatigue, la faim, la tristesse et la maladie.

## Actions et stats

- `FD` / FOOD : nourrit le dragon ; son trait d'appétit ajuste le gain.
- `PL` / PLAY : améliore le bonheur, mais augmente la fatigue et fait perdre
  5 points d'hygiène.
- `MD` / MEDICINE : soigne lorsque les HP sont bas.
- `CL` / CLEAN : restaure l'hygiène ; une hygiène critique pénalise les HP.
- `SL` / SLEEP : demande une sieste. Un dragon têtu peut répondre `ONE MORE!`.
- `ST` / STATUS : affiche Food, Happy, HP, Clean, Rest, progression et âge.

À partir de 80 de fatigue, le dragon perd un point de bonheur à chaque cycle
de 15 s et un HP à chaque cycle de santé de 12 s, jusqu'à ce qu'il dorme.

## Persistance

Les stats, l'âge, l'hygiène, la fatigue, le stade de vie et les trois traits de personnalité
sont sauvegardés dans la mémoire NVS interne de l'ESP32. Le schéma NVS `6`
correspond exactement au firmware `v0.6` : une sauvegarde d'une autre version
est volontairement ignorée et un nouveau dragon est créé. Elle est regroupée
après les actions et actualisée périodiquement pour limiter l'usure de la flash.

## Veille profonde (test)

Après 10 minutes sans appui, le prototype sauvegarde le dragon, affiche
`GOOD NIGHT`, éteint le contrôleur TFT, puis entre en deep sleep. Le
bouton OK (GPIO3) réveille la carte. Le rétroéclairage reste alimenté tant que
`BLK` est relié directement au 3,3 V.

## Cycle de vie

Le dragon commence dans un œuf : sélectionnez `FD` avec gauche/droite puis appuyez
trois fois sur `OK` pour le réchauffer et le faire éclore. Il devient ensuite bébé, jeune après cinq minutes, puis adulte
quinze minutes plus tard. Ces délais courts sont destinés à la validation sur le
prototype. Durant le stade œuf, les autres actions indiquent de le réchauffer ;
pour un bébé, `FD` et `PL` sont affichés comme `MILK` et `CUDDLE`.

Maintenez les boutons gauche et droite simultanément pendant cinq secondes pour
effacer la sauvegarde NVS et recréer un nouvel œuf.

### Assets couleur TFT

Les sources TFT sont des BMP couleur non compressés placés dans `assets/tft/`.
Le magenta pur `#FF00FF` représente la transparence. Le générateur
`tools/generate_tft_assets.py` accepte les BMP 8 ou 24 bits, convertit chaque
pixel en RGB565 et produit un masque de transparence 1 bit dans
`include/generated_tft_assets.h`. Les 33 assets mesurent 112×112 px. Ils
couvrent toutes les expressions et actions du dragon, ses quatre frames de
marche, le sommeil, les quatre rotations de l'œuf et ses trois étapes
d'éclosion. Les rotations animent l'œuf au repos ; les trois fissures sont
jouées successivement lors du troisième réchauffement.

Le générateur contrôle aussi l'échelle : chaque dragon doit rester dans une
plage de surface visible commune et deux frames d'une même animation ne peuvent
pas différer de plus de 12 %. La ligne de sol de deux frames ne peut pas non
plus varier de plus de 2 pixels. La compilation échoue si ce contrat est violé.

Les 33 assets et leurs animations ont été validés sur le TFT réel le
5 septembre 2026, notamment l'échelle, les ancrages et les yeux canoniques de
`dragon_medicine_01`.
