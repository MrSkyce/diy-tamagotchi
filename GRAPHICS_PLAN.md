# Plan graphique — OLED bicolore et TFT IPS couleur

## Objectif

Donner au dragon une silhouette originale plus lisible et expressive, sans
reprendre les personnages Tamagotchi. L'OLED reste l'affichage de contrôle et
la source de la scène monochrome historique. Le TFT ST7789 240×240 fournit
désormais une présentation couleur et doit évoluer vers une interface native.

## État graphique actuel

### OLED SSD1306

L'interface OLED 128×64 est complète et validée sur la dalle bicolore :

| Zone physique OLED | Coordonnées | Usage prévu |
|---|---:|---|
| Jaune | `y = 0..15` | Menu compact FD / PL / MD / CL / SL / ST |
| Bleue | `y = 16..63` | Dragon, animations et messages contextuels |

La zone bleue mesure 128×48 px. Les premiers sprites viseront 32×32 px, mais
le convertisseur acceptera toute image qui tient dans 128×48 px.

### TFT ST7789

Le TFT utilise Adafruit GFX/ST7789 en SPI mode 3 à 32 MHz. L'écran est monté à
l'envers sur la breadboard ; `rotation(0)` et l'offset Adafruit natif de 80
lignes donnent l'orientation et le cadrage validés.

Le rendu actuel est hybride :

- bandeau supérieur natif 240×32, coloré selon l'écran courant ;
- version et titre dessinés directement avec Adafruit GFX ;
- scène OLED 128×64 agrandie et colorisée dans une zone 224×112 ;
- quatre jauges TFT natives dans la partie basse ;
- stade de vie affiché en pied d'écran ;
- fond sombre commun et couleur d'accent dépendant de l'action.

La scène centrale reste monochrome à la source. Un pixel OLED éteint devient
noir et un pixel allumé prend la couleur d'accent. Les 240×240 pixels sont
utilisés pour la composition générale, mais pas encore pour des sprites natifs
haute définition.

Le rafraîchissement ne doit jamais effacer tout l'écran à chaque animation :
la première implémentation avec `fillScreen()` périodique produisait un fort
clignotement IPS. L'écran complet n'est nettoyé qu'une fois ; la zone centrale
est remplacée directement et les jauges sont mises en cache jusqu'à ce que
leur valeur change.

## Contrat des assets

- Tous les assets source sont des BMP non compressés, en noir et blanc.
- Un pixel clair est affiché sur l'OLED ; un pixel sombre est transparent.
- Les BMP sont versionnés dans `assets/sprites/` et restent la source de vérité.
- Un GIF n'est pas utilisé : chaque frame d'animation est un BMP nommé
  explicitement, par exemple `dragon_idle_01.bmp` et `dragon_idle_02.bmp`.

## Chaîne de précompilation

```text
assets/sprites/*.bmp
        ↓ tools/generate_sprites.py
include/generated_sprites.h
        ↓ PlatformIO
firmware ESP32-C3
```

Le script Python n'aura aucune dépendance externe : il lira le format BMP
non compressé, validera dimensions et palette, puis produira des tableaux
`PROGMEM` compatibles avec `Adafruit_SSD1306::drawBitmap()`. Le header généré
reste versionné : son diff rend visible le résultat de toute modification
graphique dans une revue Git.

## Incréments OLED réalisés

1. **Fait —** déplacer le menu principal dans la bande jaune et réserver la
   zone bleue au contenu ; préserver les trois boutons et les écrans
   FOOD/PLAY/STAT.
2. **Fait —** ajouter le répertoire d'assets, le convertisseur pré-build
   PlatformIO et migrer les sprites existants ; compiler pour vérifier la
   génération reproductible.
3. **Fait —** tester le cadrage 40×40 avec les BMP migrés, puis redessiner
   les sprites avec des silhouettes originales et détourées : idle, blink,
   happy, hungry, sad, sick et sleeping.
4. **Fait —** ajouter et revoir sur l'OLED réelle les frames de marche du
   dragon (deux poses par direction) et les quatre poses de rotation de l'œuf :
   contraste, centrage, lisibilité à distance et fluidité.

Le dragon 40×40 se promène entre les marges de la zone bleue, avec un
déplacement d'un pixel toutes les 120 ms. Les frames `dragon_walk_left_01/02`
et `dragon_walk_right_01/02` alternent les pattes selon son sens de marche.
Chaque entrée du menu jaune est limitée à deux lettres (`FD`, `PL`, `MD`,
`CL`, `SL`, `ST`) ; sur l'écran principal, son nom complet est centré une
seconde dans la première ligne bleue. Le dragon commence donc à `y = 24`.

Les messages d'action sont placés dans les marges latérales bleues afin que le
dragon conserve la même ligne de sol sur l'écran principal, FOOD et PLAY.
Pendant FOOD, deux frames BMP font frotter ses pattes sur son ventre ; pendant
PLAY, le dragon joyeux saute entre `y = 20` et `y = 16`, sans empiéter sur le
menu jaune.

L'œuf de démarrage est également précompilé depuis `assets/boot/`. Ses quatre
frames de rotation le font rouler vers la bordure droite avant de se fissurer ;
trois frames de casse ouvrent ensuite la coque avec des éclats, accompagnés
d'un bref effet sonore. Un réveil deep sleep saute cette animation et joue une
courte mélodie de retour.
5. Documenter l'export des BMP et la convention de nommage dans le README.

## Migration TFT couleur

### Palier 1 — fait et validé

- valider câblage, reset et alimentation sur deux dalles ;
- identifier SPI mode 3, `INVON` et les règles d'offset ;
- valider le SPI matériel à 1, 4, 8, 16 puis 32 MHz ;
- tester Adafruit ST7789 avec texte multicolore ;
- conserver OLED et TFT actifs simultanément ;
- ajouter bandeau, scène colorisée et jauges natives ;
- supprimer le clignotement global ;
- mettre en cache les jauges inchangées.

### Palier 2 — prochaine étape

Créer une vraie composition TFT indépendante, écran par écran, sans supprimer
l'OLED tant que la nouvelle interface n'est pas complètement validée :

1. définir grille, marges, palette et typographie 240×240 ;
2. refaire d'abord HOME et STATUS nativement ;
3. ajouter les écrans FOOD, PLAY, MEDICINE, CLEAN et SLEEP ;
4. migrer boot, œuf, éclosion et transitions ;
5. comparer chaque écran avec l'OLED et valider sur la dalle réelle ;
6. retirer la dépendance au framebuffer OLED uniquement lorsque toutes les
   fonctions sont couvertes.

### Palier 3 — assets couleur

- choisir un format source éditable et reproductible ;
- conserver les BMP 1-bit actuels tant que les nouveaux sprites ne sont pas
  validés ;
- préférer RGB565 précompilé ou palette indexée pour limiter la flash ;
- éviter un framebuffer plein écran permanent de 115 200 octets sans mesure
  préalable de la RAM dynamique ;
- prévoir transparence, variantes d'expression et animations sans dupliquer
  inutilement les pixels ;
- mesurer flash, RAM et temps de transfert à chaque famille d'assets.

### Palier 4 — performance et énergie

- mettre à jour uniquement les régions modifiées ;
- regrouper les transferts SPI et éviter les écritures pixel par pixel ;
- évaluer double buffering partiel ou DMA seulement si nécessaire ;
- piloter `BLK` pour extinction réelle et variation de luminosité ;
- conserver une fréquence de référence de 32 MHz, déjà validée matériellement.

## Validation

- La génération échoue clairement pour un BMP compressé, coloré ou trop grand.
- `pio run` régénère le header lorsque l'asset change.
- Les sprites sont vérifiés sur la dalle bicolore réelle, pas uniquement dans
  un éditeur d'image.
- Aucun asset issu d'une franchise existante n'est intégré au firmware.
- Les bords du TFT doivent être cadrés sans décalage vertical en rotation 0.
- Le TFT ne doit présenter ni bandes, ni pixels parasites, ni clignotement
  pendant les animations et la navigation.
- Les couleurs de test rouge, vert, bleu, cyan, magenta et jaune doivent être
  correctes avec l'inversion IPS active.
- Toute migration d'écran doit préserver les informations et actions visibles
  sur l'OLED jusqu'à validation fonctionnelle équivalente.

## Contraintes matérielles affectant le graphisme

- le TFT ne possède pas de CS et monopolise son bus SPI ;
- le TFT ne possède pas de MISO : aucun diagnostic par lecture de registre ;
- `BLK` est relié au 3,3 V et reste éclairé en deep sleep ;
- l'écran est physiquement retourné sur le prototype ;
- la W25Q64 ne doit pas être ajoutée au même bus sans solution de sélection
  distincte.
