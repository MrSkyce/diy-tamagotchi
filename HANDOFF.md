# Handoff — Tamagotchi ESP32-C3

## Résumé de reprise

Prototype de Tamagotchi DIY destiné à un enfant, basé sur un ESP32-C3 AYWHP
au format proche du SuperMini. Le firmware actif est un projet PlatformIO en
Arduino C++. Le sketch `TamagotchiESP32C3.ino` est uniquement une référence
historique V0.3.

État de référence au 5 septembre 2026 :

- branche `main` synchronisée avec `origin/main` ;
- dernier jalon versionné : `050a692 feat: add ST7789 color display support` ;
- firmware affiché : `v0.6` ; schéma de sauvegarde NVS : `6` ;
- OLED 128×64 et TFT IPS ST7789 240×240 actifs simultanément ;
- interface, boutons, buzzer, persistance, cycle de vie et deep sleep validés
  sur la carte réelle ;
- SPI mode 3 testé progressivement de 100 kHz à 32 MHz ; 32 MHz validé sans
  artefact sur deux écrans du même modèle ;
- dernier correctif téléversé : cache des jauges TFT pour ne les redessiner
  que lorsqu'une valeur change. La compilation et le téléversement sont
  validés ; demander une confirmation visuelle explicite si ce point devient
  un critère de release.

## Matériel actuel

### Microcontrôleur

- AYWHP ESP32-C3, format proche ESP32-C3 SuperMini ;
- cible PlatformIO : `esp32-c3-devkitm-1` ;
- configuration Arduino équivalente validée : `ESP32C3 Dev Module` ;
- USB CDC à 115200 bauds ; port observé sous Linux : `/dev/ttyACM0` ;
- identifiant USB observé : `303A:1001`.

### OLED de contrôle

- OLED SSD1306 128×64 bicolore, adresse I²C `0x3C` ;
- bande physique jaune approximativement sur `y=0..15`, zone bleue sur
  `y=16..63` ;
- bibliothèque : Adafruit SSD1306, avec Adafruit GFX ;
- reste la source du framebuffer monochrome et l'affichage de contrôle.

### TFT IPS

- module 1,3 pouce 240×240, contrôleur ST7789, marquage observé
  `Y-PS1.30-V2.0` ;
- deux exemplaires du même modèle ont été essayés ; le comportement est
  identique ;
- broches du module : `GND VCC SCL SDA RES DC BLK` ;
- `SCL` et `SDA` désignent ici l'horloge et les données SPI, pas l'I²C ;
- aucune broche `CS` exposée : le contrôleur est sélectionné en permanence ;
- aucune broche `MISO` : liaison en écriture seule ;
- `VCC` et `BLK` actuellement reliés au 3,3 V ;
- écran monté à l'envers sur la breadboard ; `setRotation(0)` fournit
  l'orientation visuelle souhaitée.

### Pinout validé

| Fonction | GPIO | Notes |
|---|---:|---|
| OLED SDA | 0 | I²C |
| OLED SCL | 1 | I²C |
| Bouton gauche | 21 | `INPUT_PULLUP`, bouton vers GND |
| Bouton OK | 3 | `INPUT_PULLUP`, réveil deep sleep |
| Bouton droite | 10 | `INPUT_PULLUP`, bouton vers GND |
| Buzzer passif | 5 | déplacé depuis GPIO4 pour libérer SCLK |
| TFT SCLK / SCL | 4 | SPI matériel |
| TFT MOSI / SDA | 6 | SPI matériel, écriture seule |
| TFT DC | 7 | sélection commande/données |
| TFT RESET / RES | 20 | reset actif à LOW |
| TFT CS | — | non exposé par le module |
| TFT MISO | — | désactivé |

Vue de dessus de la carte, USB-C vers le haut, la première broche de la rangée
gauche est GPIO5. Ne pas revenir à l'ancien schéma erroné utilisant GPIO5
comme SCLK : le câblage matériel validé est bien SCLK GPIO4 et MOSI GPIO6.

## Paramètres ST7789 validés

Configuration fonctionnelle :

```text
interface       SPI matériel
mode            SPI_MODE3
fréquence       32 MHz
ordre           MSB first
format pixels   RGB565, COLMOD 0x55
inversion IPS   active, INVON 0x21
taille          240 × 240
orientation     Adafruit rotation 0
offset          offset Adafruit natif de 80 lignes dans cette orientation
CS              absent
MISO            absent
```

Le diagnostic a établi les points suivants :

1. Le rétroéclairage noir ne prouvait que l'alimentation de `VCC`/`BLK`, pas
   la communication avec le ST7789.
2. Les exemples en SPI mode 0 laissaient l'écran noir. Le mode 3 est requis
   par ce lot de dalles.
3. Sans `INVON`, le vert apparaissait magenta et le rouge cyan/bleu : les
   couleurs affichées étaient complémentaires.
4. Avec le pilote brut et `MADCTL=0`, la fenêtre valide était `0..239` sans
   offset. Un départ à la ligne 80 faisait commencer le remplissage au tiers.
5. Avec Adafruit `setRotation(0)`, l'image est tournée de 180 degrés et
   l'offset interne de 80 lignes appliqué par la bibliothèque est nécessaire.
   Le forcer à zéro décale toute l'image d'un tiers vers le bas.
6. Le bit-banging à environ 100 kHz a permis de prouver le protocole. Le SPI
   matériel a ensuite été validé à 1, 4, 8, 16 puis 32 MHz.
7. Les transferts octet par octet ajoutaient un fort surcoût. Les essais par
   blocs de ligne ont confirmé que le bus pouvait approcher son débit attendu.

## Architecture logicielle actuelle

### Dépendances du firmware normal

- framework Arduino ESP32 ;
- Adafruit GFX Library ;
- Adafruit SSD1306 ;
- Adafruit ST7735 and ST7789 Library ;
- `Wire`, `SPI` et `Preferences` fournis par le framework.

Adafruit ST7789 v1.11.0 initialise le SPI matériel à 32 MHz par défaut. Le
firmware appelle explicitement `init(240, 240, SPI_MODE3)`, conserve
`rotation(0)`, active l'inversion et fixe les transferts suivants à 32 MHz.

### Fichiers principaux

- `src/main.cpp` : simulation, états d'écran, entrées, audio, OLED et TFT ;
- `src/persistence.cpp` : sérialisation et validation NVS ;
- `include/config.h` : pinout, versions et temporisations ;
- `assets/sprites/*.bmp` et `assets/boot/*.bmp` : sources graphiques 1-bit ;
- `tools/generate_sprites.py` : génération du header `PROGMEM` ;
- `include/generated_sprites.h` : résultat généré et versionné ;
- `platformio.ini` : firmware normal et quatre environnements de diagnostic.

### Rendu des deux écrans

Les fonctions historiques dessinent toujours l'interface 128×64 dans le
framebuffer SSD1306. `presentDisplay()` :

1. envoie ce framebuffer à l'OLED ;
2. appelle le rendu TFT Adafruit ;
3. affiche un bandeau couleur natif selon l'écran courant ;
4. colorise et agrandit la scène monochrome dans une zone centrale 224×112 ;
5. dessine quatre jauges TFT natives et le stade de vie dans la partie basse.

L'interface TFT est donc hybride : le cadre, les couleurs et les jauges sont
natifs 240×240, mais la scène centrale reste dérivée du framebuffer OLED. Ce
n'est pas encore une interface entièrement indépendante en 240×240.

### Prévention du clignotement TFT

- l'écran complet n'est effacé qu'à la première image ;
- les trames suivantes remplacent directement la zone centrale ;
- les jauges mémorisent leurs dernières valeurs et ne sont redessinées que
  lorsqu'une statistique change ;
- le stade de vie n'est redessiné que lors d'une évolution.

La première version effaçait les 240×240 pixels à chaque animation, ce qui
provoquait un clignotement très visible. Ne pas réintroduire de
`fillScreen()` dans le chemin de rafraîchissement périodique.

### Occupation mesurée

Dernière compilation du firmware normal :

- flash : environ 24,7 %, soit 323 108 octets sur 1 310 720 ;
- RAM statique : environ 4,8 %, soit 15 752 octets sur 327 680.

Ces chiffres n'incluent pas la mémoire dynamique maximale utilisée en cours
d'exécution. Le framebuffer couleur complet 240×240×16 bits demanderait
115 200 octets ; il n'est pas alloué actuellement.

## Environnements PlatformIO de diagnostic

Les sources de test sont exclues du firmware normal par `build_src_filter`.

| Environnement | Source | Usage |
|---|---|---|
| `esp32-c3-devkitm-1` | application normale | Tamagotchi OLED + TFT |
| `gpio-test` | `src/gpio_test.cpp` | contrôle statique/cyclique des broches |
| `raw-st7789-test` | `src/raw_st7789_test.cpp` | pilote brut bit-bang mode 3 lent |
| `hardware-st7789-test` | `src/hardware_st7789_test.cpp` | SPI matériel brut, transferts par blocs |
| `st7789-test` | `src/st7789_test.cpp` | Adafruit, texte multicolore, mode 3 |

Commandes usuelles :

```bash
/home/skyce/.platformio/penv/bin/pio run -e esp32-c3-devkitm-1
/home/skyce/.platformio/penv/bin/pio run -e esp32-c3-devkitm-1 \
  --target upload --upload-port /dev/ttyACM0
/home/skyce/.platformio/penv/bin/pio run -e st7789-test \
  --target upload --upload-port /dev/ttyACM0
```

Après un banc autonome, retéléverser explicitement l'environnement normal :
un test remplace entièrement le firmware présent sur la carte.

## Fonctionnalités du Tamagotchi

### Navigation

Menu principal :

- `FD` / FOOD ;
- `PL` / PLAY ;
- `MD` / MEDICINE ;
- `CL` / CLEAN ;
- `SL` / SLEEP ;
- `ST` / STATUS.

Contrôles : gauche = précédent, OK = valider, droite = suivant. Le debounce
accepte un changement après 35 ms de niveau stable.

### Cycle de vie

États persistés : `EGG`, `BABY`, `YOUNG`, `ADULT`.

- un nouveau dragon commence dans un œuf ;
- sélectionner `FD` et appuyer trois fois sur OK pour le réchauffer ;
- l'œuf éclot en bébé ;
- le bébé devient jeune après 5 minutes ;
- le jeune devient adulte après 15 minutes supplémentaires ;
- ces durées sont volontairement courtes pour le prototype ;
- au stade œuf, les autres actions demandent de réchauffer l'œuf ;
- au stade bébé, FOOD et PLAY sont présentés comme `MILK` et `CUDDLE`.

### État du pet

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
  LifeStage lifeStage;
  uint8_t warmth;
  unsigned long birthTime;
  unsigned long stageStartedAgeMs;
};
```

Toutes les statistiques sont bornées à `0..100`. Les traits de personnalité
sont bornés à `0..2` et générés aléatoirement pour un nouveau dragon.

Temporisations de développement :

| Évolution | Intervalle |
|---|---:|
| faim | -1 toutes les 10 s |
| bonheur | -1 toutes les 15 s |
| santé | contrôle toutes les 12 s |
| propreté | -1 toutes les 20 s |
| fatigue | +1 toutes les 15 s |

La santé baisse lorsque faim, bonheur, propreté ou fatigue deviennent
critiques. À partir de 80 de fatigue, le bonheur et la santé reçoivent une
pénalité supplémentaire à leurs cycles respectifs.

### Actions

- FOOD rétablit la faim selon le trait d'appétit ;
- PLAY augmente le bonheur et la fatigue, retire 3 de faim et 5 de propreté ;
- MEDICINE soigne de 25 lorsque la santé est inférieure à 70 ;
- CLEAN ajoute 40 de propreté ;
- SLEEP est accepté selon la fatigue et le trait têtu, puis retire 50 de
  fatigue, ajoute 3 de bonheur et retire 1 de faim ;
- STATUS affiche les statistiques, le stade, l'âge et la version.

Toutes les actions ont des sons et animations dédiés. Le lecteur audio est
non bloquant et permet d'enchaîner un son principal puis un son d'action.

### Reset du dragon

Maintenir gauche et droite simultanément pendant 5 secondes efface la clé NVS
du pet et redémarre la carte. Le menu principal reste complet au retour sur le
nouvel œuf ; `FD` permet de le réchauffer.

## Persistance NVS

- namespace : `tamagotchi` ; clé : `pet` ;
- magic : `0x54414D41` (`TAMA`) ;
- version stricte : `FIRMWARE_SAVE_VERSION = 6` ;
- contenu : cinq stats, trois traits, stade, chaleur, âge et âge au début du
  stade ;
- checksum calculé sur tous les champs ;
- taille, magic, version, plages et checksum sont validés avant restauration ;
- le blob complet est lu avec `Preferences::getBytes()` ;
- aucune migration des anciennes versions : une sauvegarde incompatible est
  ignorée et un nouveau dragon est créé ;
- écriture différée de 3 secondes après modification ;
- checkpoint périodique toutes les 5 minutes.

L'âge sauvegardé repose sur `millis()`. Le temps passé hors alimentation ou en
deep sleep n'est pas ajouté. Le compteur 32 bits reboucle après environ
49,7 jours : c'est une limite connue.

## Deep sleep

- déclenchement après 60 secondes sans interaction ;
- écran de pré-veille affiché pendant 1 seconde ;
- sauvegarde immédiate du pet ;
- OLED mis hors affichage ;
- contrôleur TFT désactivé avec Adafruit `enableDisplay(false)` ;
- réveil par bouton OK, GPIO3 à LOW ;
- au réveil, l'animation longue de naissance est ignorée et un son de retour
  est joué.

Limite énergétique importante : `BLK` est relié au 3,3 V. La dalle devient
noire mais son rétroéclairage reste alimenté pendant le deep sleep. Pour une
veille réellement basse consommation, piloter `BLK` via un GPIO adapté et,
si nécessaire, un transistor.

## Assets graphiques

- sprites dragon : BMP 1-bit 40×40 ;
- œuf : BMP 1-bit 24×24 ;
- sources de vérité : `assets/sprites/` et `assets/boot/` ;
- conversion automatique avant chaque build ;
- 31 assets BMP observés lors des dernières compilations ;
- le header généré reste versionné pour rendre les changements auditables.

Préserver les BMP comme format collaboratif source. Ne pas éditer uniquement
`generated_sprites.h`, car il sera régénéré au prochain build.

## Limites et décisions matérielles

### Bus SPI non partageable simplement

Le TFT n'a pas de `CS` et écoute en permanence. La mémoire W25Q64 8 Mo reçue
est volontairement mise de côté. Elle ne doit pas être ajoutée sur le même bus
SPI sans solution matérielle ou architecturale, sous peine d'envoyer les
transactions de la flash au TFT.

Options futures :

- écran équivalent avec broche CS exposée ;
- bus logiciel séparé pour la mémoire ;
- autre contrôleur/brochage SPI si disponible et validé sur l'ESP32-C3 ;
- modification matérielle permettant de contrôler le CS interne du TFT.

### Liaison TFT en écriture seule

Sans MISO, le firmware ne peut pas lire l'identifiant, le statut ou la mémoire
graphique du ST7789. Le diagnostic doit rester visuel ou utiliser un analyseur
logique externe.

### Broches restantes

GPIO4 est réservé à SCLK, GPIO5 au buzzer, GPIO6 à MOSI, GPIO7 à DC et GPIO20
au reset TFT. Toute nouvelle fonction matérielle doit commencer par un audit
du pinout et des broches de strapping/démarrage.

### BLE

Aucun module BLE n'est présent dans le firmware. Les expérimentations de debug
BLE ont été retirées en raison de leur coût flash. L'idée d'identifier les
téléphones voisins a également été retirée du suivi : elle nécessiterait une
application émettrice ou une balise et n'est pas dans la roadmap active.

## Validation et commandes de clôture

Avant un commit firmware :

1. compiler l'environnement normal ;
2. téléverser sur `/dev/ttyACM0` ;
3. vérifier OLED et TFT réels ;
4. vérifier navigation, buzzer GPIO5 et boutons ;
5. attendre 60 secondes et vérifier le deep sleep/réveil si la gestion
   d'énergie a changé ;
6. exécuter `git diff --check` ;
7. ne versionner les photos ou fichiers locaux que sur demande explicite.

La disparition temporaire de `/dev/ttyACM0` après deep sleep est normale. Un
appui sur OK réveille la carte et rétablit le port USB.

## Roadmap actuelle

1. **UI TFT réellement native.** Remplacer progressivement la scène centrale
   dérivée du framebuffer OLED par une composition 240×240 dédiée, en couleur,
   écran par écran.
2. **Rétroéclairage.** Piloter `BLK` pour supprimer la consommation du TFT en
   deep sleep et permettre éventuellement une variation de luminosité.
3. **Temps réel hors alimentation.** Choisir entre réveils temporisés, horloge
   logicielle avec référence persistée ou RTC externe ; mettre à jour âge et
   besoins au réveil.
4. **Mémoire externe.** Résoudre d'abord l'absence de CS du TFT avant de câbler
   la W25Q64.
5. **Équilibrage.** Ajuster les durées, gains et seuils après usage réel.
6. **Énergie et mécanique.** Ajouter LiPo, indicateur de batterie, PCB et
   boîtier imprimé 3D.

## Contraintes de reprise

1. Considérer ce document et le code au commit courant avant toute ancienne
   mémoire de conversation.
2. Ne pas modifier le pinout sans vérifier le câblage physique.
3. Conserver SPI mode 3 et 32 MHz tant qu'un test matériel ne justifie pas un
   changement.
4. En Adafruit rotation 0, conserver l'offset natif de 80 lignes ; ne pas
   appliquer aveuglément l'offset zéro du pilote brut.
5. Ne pas remettre un `fillScreen()` dans chaque trame TFT.
6. Préserver les machines à états et les timers non bloquants.
7. Incrémenter ensemble version firmware et version NVS lors d'une évolution
   incompatible du format sauvegardé.
8. Garder les BMP source comme référence graphique.
9. Ne pas supposer que la W25Q64 peut partager le bus actuel.
10. Valider les changements UI et matériels sur l'appareil réel avant commit.
