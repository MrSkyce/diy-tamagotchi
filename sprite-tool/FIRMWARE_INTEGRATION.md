# Intégration firmware du cycle approuvé

Le cycle habillé corrigé et sa taille ont été validés par l'utilisateur :
**« oui, validé. »** La preuve du lot est dans
`approved/dragon_rigged/walk/approval.json` ; les empreintes des 16 BMP promus sont
dans `../assets/tft/rigged_walk_approval.json`.

L'intégration logicielle du dragon est réalisée : huit frames par direction,
120 ms par pose, 3 pixels écran par pose, sans rebond supplémentaire. Les 33
anciens BMP restent intacts ; 16 nouveaux BMP `dragon_rigged_walk_*` portent le
catalogue initial à 49 images. Les cinq marches V4 sont maintenant validées et
leurs 80 BMP exportés sont ajoutés : **129 images**, **476646 octets** pour
l'image W25Q64. `assets/tft/mascot_walks_approval.json` lie chaque BMP à son
empreinte et chaque espèce à son manifeste approuvé. Le générateur contrôle les
80 empreintes, les groupes complets de huit poses, le sol à 104 et la capacité Flash.
Les tests comparent chaque pixel exporté au PNG approuvé, puis au décodage RLE.
Le lecteur HOME utilise maintenant l'espèce choisie à la création et sauvegardée.
Les cinq autres espèces utilisent provisoirement une pose immobile de leur propre
cycle pour les états non illustrés ; cette couverture graphique reste à compléter.
Le tampon décompressé reste de 25088 octets.

Le firmware principal a compilé : RAM 40896/327680 octets, Flash
355308/1310720 octets. Aucun téléversement ni essai TFT n'a encore été effectué.
Les cibles `tamagotchi-30s-test`, `asset-flash-programmer` et `asset-storage-test`
compilent également avec le catalogue 129. Les 24 empreintes
golden historiques sont conservées.

## Contrôle reproductible, sans export ni approbation

Vérification du catalogue 129 : **168 tests passent**, dont trois tests de promotion
des cinq espèces (pixels approuvés, intégrité, groupes complets et capacité W25Q64).
Les quatre compilations ont réussi ; le programmeur d'assets occupe 737870 octets
de Flash programme, sous la limite de 1310720 octets.

```sh
rtk proxy sprite-tool/.venv/bin/python -m sprite_animator.production_check sprite-tool/generated/dragon_rigged/walk --repo .
```

Le contrôle charge les assets de production et simule en mémoire l'ajout des
huit poses par direction. Il appelle le véritable validateur de
`tools/generate_tft_assets.py`, sans exécuter sa fonction d'écriture. Un rejet de
validation produit un code de sortie 2. Aucun BMP ou en-tête n'est écrit.

Résultat après promotion du cycle validé :

- Les 16 frames passent le round-trip du codec de production.
- Surface visible : 2306–2378 pixels par frame. Une règle limitée aux noms des
  seize images approuvées contrôle cette plage ; la règle 5000–7300 des autres
  dragons n'a pas changé. La génération vérifie également les SHA-256 des BMP
  contre l'approbation et les groupes de huit frames complets.
- Le validateur de production accepte désormais le catalogue. Le CRC, les
  identifiants et l'image W25Q64 ont été régénérés ensemble. Il faudra programmer
  la Flash externe et le firmware correspondant de façon cohérente.

## Lecteur intégré

`include/mascot_walks.h` centralise les tableaux explicites des six espèces,
soit 96 identifiants testés en C++ natif contre les BMP du catalogue.
`src/main.cpp` appelle ce registre pour l'espèce choisie. `tftAnimatedPair`, ses 180 ms et son rebond restent utilisés uniquement
pour les anciennes animations. La marche a sa propre horloge `WalkCycle` dans
`include/walk_cycle.h`, compilée aussi dans les tests natifs C++.

Position écran et indice de pose avancent ensemble : ±3 pixels et une pose toutes
les 120 ms. La position reste dans 4..124 ; le retournement comporte un battement
immobile, puis le dragon repart. Lors d'une pause ou d'un retour HOME, l'horloge
redémarre en pose 0 sans rattrapage brutal. Un retard de boucle avance au maximum
d'une pose et de 3 pixels, ce qui ralentit l'animation plutôt que de téléporter
le personnage. Le débordement de millis est couvert par un test natif.

La marche et le déplacement sont suspendus hors HOME, pour l'œuf et pendant les
états sick/hungry/sad/tired/blink/happy prioritaires. La persistance passe désormais
à v8 pour l'identité, avec lecture compatible v7 ; voir les limites de démarrage
et de retour arrière dans [le parcours de création](CREATION_SELECTION.md).

`TftAssetStore` conserve une seule frame décompressée : le tampon reste de
112×112×2 = 25088 octets. La charge réelle de lecture Flash/décodage/affichage
doit être mesurée sur ST7789 ; les tests hôte ne constituent pas cette preuve.

## Portes restantes

1. Programmation cohérente firmware/assets et validation TFT du dragon.
2. Validation sur carte du choix à la création, sauvegarde/restauration v8,
   migration v7, erreur de lecture et coupure avant/après confirmation.

Hors V1 marche (section 4 du handoff) : illustrations spécifiques des autres états
pour les cinq espèces. Le fallback identitaire immobile est annoncé ; aucune
nouvelle pose d'état n'est considérée approuvée. Voir [l'audit](INTEGRATION_AUDIT.md).

Décision utilisateur : [choix à la création](CREATION_SELECTION.md), identité
persistante, sauvegardes v7 conservées comme dragon. Parcours implémenté,
compilation jeu et variante 30s réussie, sans essai TFT ni téléversement.

## Mode de test des six marches

Compilation `mascot-walk-test` réussie : RAM 39212/327680 octets, Flash programme
290024/1310720 octets. Le test de stockage historique compile aussi. La suite hôte
compte désormais **169 tests passants**, dont le registre des 96 frames compilé
en C++ natif. Aucun essai sur carte ni téléversement.

La cible `mascot-walk-test` réutilise le test de CRC de tous les assets, puis
lit les six cycles via le registre commun et l'horloge `WalkCycle`.
Gauche/droite changent de mascotte ; OK met en pause ou reprend. Le changement
d'espèce redémarre au centre. Il n'y a ni chargement ni écriture de sauvegarde.
Le test de stockage historique garde son défilement automatique des 129 images.

```sh
rtk proxy env PLATFORMIO_CORE_DIR=/Users/gdevinzelles/Projects/diy-tamagotchi/.pio-core sprite-tool/.venv/bin/pio run -e mascot-walk-test
```

Après programmation cohérente de la Flash et du firmware de test, vérifier sur
chacune des six espèces les deux sens, toutes les poses, les chevilles, les queues,
les appuis et l'absence de traînées. Les lignes série `WALK` donnent l'espèce,
le sens, la pose, x, `load_us` et `total_us`. Comparer le temps total réel au budget
de 120000 µs par pose ; les compilations et tests hôte ne prouvent pas ce budget.
Le tampon de frame reste unique ; la ligne d'affichage du test occupe 480 octets.

PlatformIO 6.2.0 est installé dans `sprite-tool/.venv`. Le cache matériel est
local au projet, sous `.pio-core/` (ignoré par Git). Résolution de compilation :
espressif32 7.1.2 et framework Arduino 4.20017.260907+sha.dcc1105b.

```sh
rtk proxy env PLATFORMIO_CORE_DIR=/Users/gdevinzelles/Projects/diy-tamagotchi/.pio-core sprite-tool/.venv/bin/pio run -e esp32-c3-devkitm-1
```

Aucun port série ESP32 n'est actuellement visible (seulement Bluetooth,
GalaxyBudsFE et debug-console). Ne pas téléverser sur ces ports. Rebrancher la
carte et vérifier son port avant de lancer le programmeur d'assets, puis le jeu.
