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
- persistance NVS v3 rétrocompatible OK
- deep sleep sur inactivité et réveil OK
- animations et six actions de soin OK

Le firmware courant est un projet PlatformIO : `src/main.cpp` porte la boucle
de jeu et `src/persistence.cpp` isole la sauvegarde NVS. Le sketch `.ino` est
uniquement conservé comme référence historique.

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
- `FD` / FOOD
- `PL` / PLAY
- `MD` / MEDICINE
- `CL` / CLEAN
- `SL` / SLEEP
- `ST` / STATUS

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
  int cleanliness;
  int fatigue;
  uint8_t appetite;
  uint8_t playfulness;
  uint8_t stubbornness;
  unsigned long birthTime;
};
```

Stats 0..100.

Comportement actuel :
- hunger, happiness, cleanliness et fatigue baissent ou montent périodiquement
- health baisse si hunger, happiness ou cleanliness sont critiques
- FOOD, PLAY, MEDICINE, CLEAN et SLEEP ont des animations et sons dédiés
- les traits appétit, joueur et têtu modulent les besoins et le sommeil
- STATUS affiche les six jauges utiles et l'âge

Timings de développement volontairement courts :
- hunger : 10 s
- happiness : 15 s
- health : 12 s
- cleanliness : 20 s
- fatigue : 15 s

### Animation
- marche animée dans les deux sens, blink et expressions d'état
- FOOD, PLAY, MEDICINE, CLEAN, SLEEP et refus de sommeil animés
- œuf roulant, éclatement en trois frames et mélodie de naissance

### Machine à états

```cpp
enum ScreenState {
  SCREEN_MAIN,
  SCREEN_FOOD,
  SCREEN_PLAY,
  SCREEN_MEDICINE,
  SCREEN_CLEAN,
  SCREEN_REST,
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

Le projet utilise des sprites BMP 1-bit : dragon détouré en **40×40** et œuf
de démarrage en **24×24**. Ils sont précompilés en tableaux `PROGMEM`.

Les BMP source dans `assets/sprites/` restent la source de vérité ; le script
`tools/generate_sprites.py` régénère le header à chaque build.

Direction souhaitée :
- grosse tête
- petit corps
- grands yeux doux
- silhouette ronde
- petites cornes
- petite queue / crête
- très lisible en monochrome

## Points faibles connus

### Architecture à faire évoluer
Le noyau est volontairement compact (`main.cpp` et `persistence.cpp`). Un
refactor en modules ne devient utile que lorsque le cycle de vie ajoute une
complexité réelle :

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

### Boucle non bloquante
Les sons, l'œuf, les animations et les délais d'écran utilisent déjà des
machines à états et des timers. Préserver cette propriété dans les futurs
évolutions.

### Boutons
Le debounce temporisé est validé. Les nouvelles interactions doivent conserver
la navigation A / OK / C actuelle.

### Persistance et temps réel
La NVS v3 sauvegarde les stats et les traits. Le temps hors alimentation n'est
pas encore décompté : c'est le principal manque avant un sommeil long réaliste.

### Pas de temps réel hors alimentation
L'âge et les timers reposent sur `millis()`.
Prévoir deep sleep + calcul du temps écoulé au réveil, éventuellement RTC externe si nécessaire.

### Gestion énergétique à faire
Matériel prévu : LiPo ~500 mAh.
Objectifs : extinction OLED, deep sleep, réveil bouton/timer, faible consommation.

## État et roadmap

**Fait et validé sur la carte :** refactor PlatformIO, debounce, audio
non bloquant, sprites BMP, animation de naissance, persistance NVS v3,
deep sleep, six actions et personnalité légère.

1. **Prochain incrément — cycle de vie.** Œuf → bébé → jeune → adulte ; l'œuf
   est réchauffé, puis les actions se transforment selon l'âge.
2. **Temps réel hors alimentation.** Mesurer le temps de sommeil pour que
   l'âge, la fatigue et les besoins continuent d'évoluer en deep sleep.
3. **Équilibrage.** Revoir les seuils, les gains et les traits après usage
   réel avec l'enfant.
4. **Énergie.** Ajouter la LiPo, son indicateur et ajuster l'inactivité.
5. **Social.** Explorer le Bluetooth de l'ESP32 pour permettre à deux dragons
   proches d'échanger ou de « discuter ».
6. **Matériel final.** PCB et boîtier imprimé 3D.

## Contraintes de reprise

1. **Ne pas casser le pinout validé.**
2. Garder l'adresse OLED `0x3C` configurable.
3. Garder Adafruit SSD1306 tant qu'il n'y a pas de raison forte de changer.
4. Préserver le comportement actuel avant toute extension.
5. Éviter les abstractions lourdes et dépendances inutiles.
6. Favoriser machines à états et timers non bloquants.
7. Garder les sprites modifiables indépendamment du moteur.
8. Conserver la compatibilité des sauvegardes NVS lors de chaque évolution.

## Source de référence

`TamagotchiESP32C3.ino` est une référence Arduino V0.3 historique ; le code
actif et validé est le projet PlatformIO.
