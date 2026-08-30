# Tamagotchi ESP32-C3

Prototype de Tamagotchi DIY basé sur ESP32-C3, OLED 128×64, trois boutons et buzzer passif.
Le firmware affiche actuellement la version `v0.6` dans le coin supérieur droit
des écrans de transition.

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
- `assets/sprites/` : source de vérité des sprites BMP noir et blanc.
- `tools/generate_sprites.py` : précompile les BMP en tableaux `PROGMEM`.
- `include/generated_sprites.h` : bitmaps générés, utilisés par `sprites.h`.
- `GRAPHICS_PLAN.md` : plan de migration vers des assets BMP précompilés.
- `TamagotchiESP32C3.ino` : référence Arduino V0.3, conservée pour comparaison.
- `HANDOFF.md` : contexte et roadmap.

## Pinout

- SDA : GPIO0
- SCL : GPIO1
- A / Left : GPIO21
- B / OK : GPIO3
- C / Right : GPIO10
- Buzzer : GPIO4

L'écran OLED utilise l'adresse I²C `0x3C`. Les boutons sont câblés entre le
GPIO et GND et utilisent les résistances de tirage internes (`INPUT_PULLUP`).
Chaque appui est validé après 35 ms stables afin d'éliminer les rebonds
mécaniques, sans bloquer la boucle principale.

Le menu jaune compact expose `FD`, `PL`, `MD`, `CL`, `SL` et `ST`. Le nom
complet de l'action sélectionnée s'affiche une seconde dans la première ligne
bleue. Le dragon exprime aussi la fatigue, la faim, la tristesse et la maladie.

## Actions et stats

- `FD` / FOOD : nourrit le dragon ; son trait d'appétit ajuste le gain.
- `PL` / PLAY : améliore le bonheur, mais augmente la fatigue et fait perdre
  5 points d'hygiène.
- `MD` / MEDICINE : soigne lorsque les HP sont bas.
- `CL` / CLEAN : restaure l'hygiène ; une hygiène critique pénalise les HP.
- `SL` / SLEEP : demande une sieste. Un dragon têtu peut répondre `ONE MORE!`.
- `ST` / STATUS : affiche Food, Happy, HP, Clean, Fatigue et âge.

À partir de 80 de fatigue, le dragon perd un point de bonheur à chaque cycle
de 15 s et un HP à chaque cycle de santé de 12 s, jusqu'à ce qu'il dorme.

## Persistance

Les stats, l'âge, l'hygiène, la fatigue, le stade de vie et les trois traits de personnalité
sont sauvegardés dans la mémoire NVS interne de l'ESP32. Le schéma NVS `6`
correspond exactement au firmware `v0.6` : une sauvegarde d'une autre version
est volontairement ignorée et un nouveau dragon est créé. Elle est regroupée
après les actions et actualisée périodiquement pour limiter l'usure de la flash.

## Veille profonde (test)

Après 60 secondes sans appui, le prototype sauvegarde le dragon, affiche
`SLEEP`, éteint l'OLED et entre en deep sleep. Le bouton OK (GPIO3) réveille la
carte. Cette durée courte sert aux tests ; elle sera ajustée pour l'usage sur
batterie.

## Cycle de vie

Le dragon commence dans un œuf : sélectionnez `FD` avec gauche/droite puis appuyez
trois fois sur `OK` pour le réchauffer et le faire éclore. Il devient ensuite bébé, jeune après cinq minutes, puis adulte
quinze minutes plus tard. Ces délais courts sont destinés à la validation sur le
prototype. Durant le stade œuf, les autres actions indiquent de le réchauffer ;
pour un bébé, `FD` et `PL` sont affichés comme `MILK` et `CUDDLE`.

Maintenez les boutons gauche et droite simultanément pendant cinq secondes pour
effacer la sauvegarde NVS et recréer un nouvel œuf.

### Sprites BMP

Les sprites sont des BMP 1-bit non compressés, tous de même dimension et au
plus 128×48 px. Un pixel clair est affiché sur l'OLED ; un pixel sombre est
transparent. Chaque frame d'animation est un fichier distinct, par exemple
`dragon_idle1.bmp` et `dragon_idle2.bmp`. PlatformIO régénère automatiquement
`include/generated_sprites.h` avant chaque compilation.

Les assets de démarrage suivent le même principe dans `assets/boot/` : les
frames d'œuf sont des BMP 24×24, indépendants des sprites dragon 40×40.
