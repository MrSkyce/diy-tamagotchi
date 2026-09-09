# Jalon 2 — première marche à quatre poses

**REJETÉE par l'utilisateur** : impression de pattes qui s'allongent plutôt
qu'une marche. Les contrôles techniques ci-dessous ne constituent pas une
validation du mouvement. Conserver cette version comme historique, ne pas
l'intégrer ni la téléverser. La révision courante est `../walk-left-v2/`.

État au 8 septembre 2026 : BMP et GIF candidats préparés, lecteur de séquences
et firmware de diagnostic compilés. Validation visuelle de cette nouvelle
séquence attendue avant essai sur le TFT. Les cinq modèles précédemment validés
ne sont pas remis en question et leurs BMP restent identiques.

## Revue du mouvement

- [GIF sombre ×4](walk-dark-4x.gif), [cyan ×4](walk-cyan-4x.gif), [vert ×4](walk-green-4x.gif).
- [Planche sombre ×4](sheet-dark-4x.png) et [planche taille native](sheet-dark-1x.png).
- Versions `walk-*-1x.gif` : lecture à la taille native 112×112.
- `bmp/` : quatre BMP RGB 24 bits, transparence magenta pure.

| Pose | Base | Retouche | Durée | Décalage Y |
|---|---|---|---:|---:|
| 01 Contact | historique A | aucune retouche du dessin | 140 ms | 0 |
| 02 Amortissement | A | patte avant fléchie, appui plus plat ; griffes reprises de A | 140 ms | 0 |
| 03 Passage | historique B | aucune retouche du dessin | 140 ms | −1 px |
| 04 Élévation | B | pied avant replié sous le tibia ; griffes reprises de B | 140 ms | 0 |

Cycle : 560 ms, contre 720 ms pour les quatre phases anciennes. Il y a bien
quatre dessins distincts, pas quatre translations de deux images. La retouche
reste volontairement limitée à la patte avant pour vérifier cette méthode avant
de multiplier les mouvements. La variété du visage et des cinq espèces relève
des jalons suivants ; elle n'est pas livrée dans cette séquence.

Les sources A/B dans `assets/tft/` sont inchangées et verrouillées par SHA-256.
Les copies de revue emploient le même nettoyage de fond que le rendu actuel
(134 pixels pour A, 62 pour B), puis des polygones entiers et des blocs de
griffes sélectionnés à la main. Ni génération IA, ni morphing, ni interpolation.
La zone de retouche est limitée à x=30..68, y=92..109 ; les lignes 0..91 et
les aplats clairs du bas du ventre sont vérifiés à l'identique. Les différences
de visage déjà présentes entre A et B sont conservées, sans nouvelle interprétation.

La pose B descend nativement jusqu'à y=108, contre y=105 pour A. Son décalage
d'affichage −1 aligne la séquence sans redessiner les références. L'écart de sol
**affiché** est de 2 px ; les BMP natifs conservent un écart de 3 px. Une intégration
future doit donc conserver les offsets de `validation.json`, dans le contrôle
d'ancrage comme dans le rendu ; supprimer cet offset invaliderait ce résultat.

## Vérifications réalisées

- 4 images 112×112 non compressées, 24 bits ; palettes propres à A/B préservées.
- 215 pixels retouchés pour l'amortissement, 238 pour l'élévation.
- Surfaces visibles 5 930..6 002 pixels : ratio maximal 1,0122, inférieur à 1,06.
- Aucun nouveau pixel opaque isolé ni trou transparent d'un pixel dans les retouches.
  Les vérifications comparent aux sources et ne prétendent pas corriger leurs détails hérités.
- Aucune nuance magenta résiduelle ; round-trip RLE et CRC des quatre images vérifiés.
- 6 GIF, chacun contenant exactement 4 frames de 140 ms ; couleurs RGB et offsets
  comparés aux BMP sans quantification approximative ni lissage.
- Tests C++11 du lecteur avec ASan/UBSan : durées variables, limites exactes,
  boucle, lecture unique, reprise, sélection identique, débordement millis,
  longs retards, lecteurs indépendants, clips invalides.
- 11 environnements PlatformIO compilés : les 10 existants et `animation-preview`.
- Catalogue normal et blob W25Q64 inchangés : 33 assets, 212 482 octets.
- Aucun téléversement, aucune mesure TFT réelle, aucun commit.

## Reproduction locale

Depuis la racine du projet (Pillow installé dans `/usr/bin/python3`) :

```sh
rtk proxy /usr/bin/python3 -B design/walk-left-v1/build.py
rtk proxy /usr/bin/python3 -B design/walk-left-v1/verify.py
rtk proxy g++ -std=c++11 -Wall -Wextra -Werror -pedantic -fsanitize=undefined,address -Iinclude tests/animation_player_test.cpp -o /tmp/tama-animation-player-test
rtk proxy env ASAN_OPTIONS=detect_leaks=0 /tmp/tama-animation-player-test
rtk /home/skyce/.platformio/penv/bin/pio run -e animation-preview
```

LeakSanitizer est désactivé car il ne fonctionne pas sous le ptrace de cet
environnement ; AddressSanitizer et UndefinedBehaviorSanitizer restent actifs.
Le lecteur n'alloue pas de mémoire dynamique.

## Diagnostic préparé pour le TFT

`animation-preview` utilise le pinout et les paramètres SPI du prototype validé.
Les quatre images viennent de la flash **interne** de ce diagnostic ; le CS de
la W25Q64 reste inactif. Aucune initialisation NVS/RTC, aucun effacement de la
W25Q64, aucune sauvegarde de jeu. Le firmware normal exclut cette source.

- Gauche : fond sombre, cyan, vert.
- OK : pause/reprise ; la reprise redémarre le cycle en pose 1.
- Droite : mélodie activée/désactivée pendant l'animation.
- Série : numéro de pose, compteur de dessins, durée du transfert/composition
  du sprite et maximum observé. Ce diagnostic ne mesure pas le chargement W25Q64.

Après validation du GIF, l'essai matériel utilisera ce firmware temporaire :

```sh
rtk /home/skyce/.platformio/penv/bin/pio run -e animation-preview -t upload --upload-port /dev/ttyACM0
```

Puis restaurer l'application normale sans reprogrammer ses assets externes :

```sh
rtk /home/skyce/.platformio/penv/bin/pio run -e esp32-c3-devkitm-1 -t upload --upload-port /dev/ttyACM0
```

Le test doit confirmer appuis lisibles, continuité de la boucle, contours et
griffes propres, absence de rognage/scintillement et boutons/audio réactifs.
L'intégration dans HOME et le catalogue W25Q64 viendra après cette validation.
