# Tamagotchi ESP32-C3

Prototype de Tamagotchi DIY basé sur ESP32-C3, OLED 128×64, trois boutons et buzzer passif.

## V0.4 : projet PlatformIO

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
- `include/sprites.h` : sprites 24×24 du dragon.
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

Le dragon exprime son état : joyeux après une action, affamé quand `Food` est
critique, triste quand `Happy` est critique et malade quand `HP` est critique.

## Persistance

Les stats et l'âge du dragon sont sauvegardés dans la mémoire NVS interne de
l'ESP32. La sauvegarde est versionnée et vérifiée avant restauration. Elle est
regroupée après les actions et actualisée périodiquement pour limiter l'usure
de la flash. Le temps hors alimentation n'est pas encore compté : cette étape
sera traitée avec le deep sleep et une source de temps adaptée.

## Veille profonde (test)

Après 30 secondes sans appui, le prototype sauvegarde le dragon, affiche
`SLEEP`, éteint l'OLED et entre en deep sleep. Le bouton OK (GPIO3) réveille la
carte. Cette durée courte sert aux tests ; elle sera ajustée pour l'usage sur
batterie.

## Prochain incrément graphique

Le menu sera déplacé dans la bande jaune (`y = 0..15`) afin de réserver la
zone bleue 128×48 au dragon. Les futurs sprites seront des BMP noir et blanc
précompilés en tableaux `PROGMEM`. Voir [GRAPHICS_PLAN.md](GRAPHICS_PLAN.md).
