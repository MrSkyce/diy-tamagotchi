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
- `TamagotchiESP32C3.ino` : référence Arduino V0.3, conservée pour comparaison.
- `HANDOFF.md` : contexte et roadmap.

## Pinout

- SDA : GPIO0
- SCL : GPIO1
- A / Left : GPIO21
- B / OK : GPIO20
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
