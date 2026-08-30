# Handoff — Tamagotchi ESP32-C3

## Contexte

Projet de Tamagotchi DIY destiné à un enfant, basé sur un **ESP32-C3 AYWHP** (format proche ESP32-C3 SuperMini), avec un écran OLED 128×64 bicolore, trois boutons et un buzzer passif.

Le prototype matériel est **fonctionnel et validé** :
- OLED OK
- boutons OK
- buzzer OK
- navigation OK
- moteur de stats OK
- animation idle/clignement OK
- boot animation œuf → naissance OK

Le code actuel reste volontairement monolithique dans un seul `.ino` afin de rester facile à flasher depuis Arduino IDE. La reprise dans Codex doit d'abord **préserver le comportement actuel**, puis refactorer par petites étapes.

## Matériel actuel

### Microcontrôleur
- **AYWHP ESP32-C3**
- Configuration Arduino testée : `ESP32C3 Dev Module`
- USB CDC fonctionnel à 115200 bauds

### OLED
- 128×64, I²C
- adresse : `0x3C`
- dalle bicolore : environ 16 premières lignes jaunes, reste bleu
- bibliothèque testée : `Adafruit SSD1306`

### Pinout validé

| Fonction | GPIO |
|---|---:|
| OLED SDA | 0 |
| OLED SCL | 1 |
| Bouton A / gauche | 21 |
| Bouton B / OK | 3 |
| Bouton C / droite | 10 |
| Buzzer passif | 4 |

Les boutons sont câblés **GPIO → bouton → GND** avec `INPUT_PULLUP`.

## Bibliothèques Arduino nécessaires

- `Adafruit GFX Library`
- `Adafruit SSD1306`
- `Wire`

## Fonctionnalités déjà implémentées

### Boot
- œuf animé
- oscillation gauche/droite
- fissure
- apparition du dragon
- mélodie de naissance

### UI
Menu principal :
- `FOOD`
- `PLAY`
- `STAT`

Contrôles :
- A = précédent
- B = valider
- C = suivant

### Moteur du pet

```cpp
struct Pet {
  int hunger;
  int happiness;
  int health;
  unsigned long birthTime;
};
```

Stats 0..100.

Comportement actuel :
- hunger baisse périodiquement
- happiness baisse périodiquement
- health baisse si hunger ou happiness sont critiques
- FOOD augmente hunger
- PLAY augmente happiness et consomme un peu de hunger
- STAT affiche hunger, happiness, health, age

Timings de développement volontairement courts :
- hunger : 10 s
- happiness : 15 s
- health : 12 s

### Animation
- deux frames idle
- blink automatique
- sprite triste si stat critique
- léger mouvement horizontal

### Machine à états

```cpp
enum ScreenState {
  SCREEN_MAIN,
  SCREEN_FOOD,
  SCREEN_PLAY,
  SCREEN_STATUS
};
```

Loop actuelle :

```cpp
void loop() {
  updateSimulation();
  updateScreenState();
  updateCreatureAnimation();
  handleButtons();
  delay(5);
}
```

## Direction artistique

Le personnage doit être un **petit dragon mignon de type mascotte arcade**, inspiré de l'esprit des petits dragons de jeux de puzzle rétro, sans copier un personnage existant.

Le projet est passé aux **sprites bitmap 24×24** car le dessin procédural donnait un rendu trop inquiétant.

Sprites existants :
- `dragon_idle1`
- `dragon_idle2`
- `dragon_blink`
- `dragon_sad`

Ils sont provisoires et peuvent être redessinés.

Direction souhaitée :
- grosse tête
- petit corps
- grands yeux doux
- silhouette ronde
- petites cornes
- petite queue / crête
- très lisible en monochrome

## Points faibles connus

### Code monolithique
Refactor recommandé après baseline compilable :

```text
src/
  main.cpp
  pet.cpp
  ui.cpp
  input.cpp
  audio.cpp
include/
  config.h
  pet.h
  ui.h
  input.h
  audio.h
  sprites.h
```

### `delay()` encore présents
Les sons et le boot utilisent encore des `delay()`.
Objectif futur : séquenceur audio et animations non bloquants.

### Debounce minimal
La détection de front fonctionne, mais il n'y a pas de vrai debounce temporisé.

### Pas de persistance
Reset = nouveau Tamagotchi.
Prévoir NVS / `Preferences` plus tard.

### Pas de temps réel hors alimentation
L'âge et les timers reposent sur `millis()`.
Prévoir deep sleep + calcul du temps écoulé au réveil, éventuellement RTC externe si nécessaire.

### Gestion énergétique à faire
Matériel prévu : LiPo ~500 mAh.
Objectifs : extinction OLED, deep sleep, réveil bouton/timer, faible consommation.

## Roadmap suggérée

### Prochain incrément — actions de soin

Le menu compact peut accueillir six entrées, chacune limitée à deux lettres
dans la bande jaune et explicitée dans la première ligne bleue. L'objectif est
de conserver les actions existantes puis d'ajouter progressivement :

1. `FD` / **FOOD** : nourrir le dragon (déjà disponible).
2. `PL` / **PLAY** : jouer avec lui (déjà disponible).
3. `MD` / **MEDICINE** : soigner une santé dégradée, avec un retour si le
   médicament n'est pas nécessaire.
4. `CL` / **CLEAN** : ajouter une jauge d'hygiène, la faire décroître et la
   restaurer par le nettoyage.
5. `SL` / **SLEEP** : offrir un repos au dragon, distinct de la veille
   profonde technique de la carte.
6. `ST` / **STATUS** : consulter les jauges, y compris l'hygiène.

Chaque nouvelle action doit recevoir une animation BMP, un effet sonore, une
durée d'affichage lisible et une vérification sur l'OLED réelle. Le cycle de
vie œuf → adulte viendra ensuite faire évoluer cette liste selon l'âge.

1. **V0.4 refactor sans changement fonctionnel**
   - PlatformIO ou Arduino CLI
   - `platformio.ini`
   - `src/main.cpp`
   - pinout dans `config.h`
   - sprites dans `sprites.h`
   - README de build
2. Debounce propre / abstraction boutons
3. Audio non bloquant
4. **Incrément graphique BMP (prochain)**
   - déplacer le menu dans la bande jaune pour libérer la zone bleue 128×48
   - établir `assets/sprites/*.bmp` comme source de vérité des sprites
   - précompiler les BMP en tableaux `PROGMEM` avec un script sans dépendance
   - redessiner un dragon original : idle, blink, happy, hungry, sad, sick,
     sleeping
   - suivre le détail dans `GRAPHICS_PLAN.md`
5. Moteur Tamagotchi plus riche : cleanliness, fatigue, weight, évolution
6. Cycle de vie : œuf → bébé → jeune → adulte
   - Le jeu pourra commencer à l'état œuf : il ne se nourrit pas encore, mais
     doit être réchauffé par une interaction dédiée.
   - Les interactions disponibles pourront évoluer avec l'âge du dragon.
7. Persistance NVS versionnée
8. Deep sleep + temps écoulé
9. Batterie / indicateur / économie d'énergie
10. PCB custom et boîtier imprimé 3D
11. Explorer le Bluetooth de l'ESP32 pour permettre à deux dragons proches
    d'échanger ou de « discuter ».

## Contraintes de reprise

1. **Ne pas casser le pinout validé.**
2. Garder l'adresse OLED `0x3C` configurable.
3. Garder Adafruit SSD1306 tant qu'il n'y a pas de raison forte de changer.
4. Préserver le comportement actuel avant toute extension.
5. Éviter les abstractions lourdes et dépendances inutiles.
6. Favoriser machines à états et timers non bloquants.
7. Garder les sprites modifiables indépendamment du moteur.
8. Préparer l'architecture à NVS et deep sleep.

## Premier objectif recommandé pour Codex

Créer une **V0.4 refactorée sans changement fonctionnel** :
- convertir en projet PlatformIO
- compiler pour ESP32-C3
- extraire config et sprites
- conserver boot, boutons, menu, sons, stats, animation
- ajouter README et commandes de build/flash

Une fois cette baseline compilable validée, évoluer incrémentalement.

## Source de référence

`TamagotchiESP32C3.ino` correspond au dernier état logiciel préparé à partir du prototype fonctionnel validé.
