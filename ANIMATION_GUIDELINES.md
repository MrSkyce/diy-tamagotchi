# Guide de création des animations TFT

## Objectif

Ajouter de vraies frames intermédiaires sans modifier l'identité graphique du
dragon. Les BMP déjà validés restent les keyframes de référence et ne doivent
jamais être remplacés par une réinterprétation automatique.

Le rendu actuellement validé utilise quatre phases de 180 ms à partir de deux
keyframes : `A → A relevée de 1 px → B relevée de 1 px → B`. Cette solution
améliore le rythme sans redessiner le personnage. L'étape suivante consiste à
remplacer progressivement ces phases de rebond par de vraies poses
intermédiaires, animation par animation.

## Méthodes à ne pas utiliser directement

Les essais suivants n'ont pas atteint la qualité requise et ne doivent pas
produire d'assets définitifs sans retouche manuelle complète :

- génération d'un sprite entier par IA : elle modifie la morphologie, la pose,
  les yeux, la silhouette ou la palette malgré des références strictes ;
- fondu ou morphing classique : il crée des doubles contours, du flou et des
  couleurs intermédiaires étrangères à la palette ;
- déplacement automatique des pixels vers la couleur voisine : il produit des
  trous, des pixels isolés et parfois des cornes ou membres en double ;
- simple redimensionnement ou rotation : ils déforment la grille de pixel art.

Une image générée peut servir de suggestion de mouvement hors production, mais
jamais de sprite final ni de base remplaçant le dragon validé.

## Méthode recommandée

### 1. Travailler une seule animation à la fois

Commencer par `dragon_walk_left`. Ne généraliser la méthode qu'après validation
de cette séquence dans un GIF agrandi puis sur le TFT réel.

### 2. Verrouiller les éléments identitaires

Avant toute modification, identifier les zones qui doivent rester inchangées :

- forme et position des yeux, pupilles et reflets ;
- bouche et expression, sauf si l'action exige explicitement leur mouvement ;
- cornes, crête, museau et joues ;
- contour général de la tête ;
- dessin et couleurs du ventre ;
- épaisseur du contour sombre ;
- palette de couleurs ;
- échelle globale et ligne de sol.

### 3. Décomposer le mouvement

Traiter séparément les parties mobiles :

- bras ;
- jambes et appuis ;
- ailes ;
- queue ;
- accessoire propre à l'action.

Le torse et la tête restent fixes autant que possible. Les raccords entre une
partie déplacée et le corps sont réparés manuellement pixel par pixel.

### 4. Dessiner avec onion skin

Utiliser Aseprite ou LibreSprite avec les keyframes A et B dans deux calques ou
deux frames voisines :

1. activer l'onion skin de A et B ;
2. dupliquer A pour créer la frame intermédiaire ;
3. déplacer ou redessiner uniquement les membres concernés ;
4. placer chaque articulation entre ses positions dans A et B ;
5. nettoyer les raccords et la silhouette à l'échelle 1:1 ;
6. contrôler aussi le résultat avec un zoom entier, sans interpolation.

Le fond du BMP reste en magenta pur `#FF00FF`. Le générateur supprimera les
éventuelles nuances de matte reliées au fond dans l'image W25Q64 dérivée, mais
le fichier source doit déjà être aussi propre que possible.

## Nombre de frames et cadences cibles

| Animation | Cible | Cadence initiale |
|---|---:|---:|
| marche gauche/droite | 4 vraies frames | 120 à 150 ms |
| FOOD, PLAY, MEDICINE, CLEAN | 3 frames | 160 à 200 ms |
| refus de sommeil, fatigue | 3 frames | 200 à 250 ms |
| idle ou respiration | 3 frames | 250 à 350 ms |
| clignement | transition courte | 80 à 120 ms |

Pour une animation à trois images, jouer `A → M → B → M`. Pour la marche à
quatre images, employer les poses classiques :

1. contact ;
2. amortissement ;
3. passage ;
4. élévation.

La mesure actuelle à 8 MHz est de 36,451 ms au pire pour charger une keyframe
depuis la W25Q64. Les cadences proposées conservent donc une marge suffisante.

## Convention de fichiers

Ne jamais écraser les keyframes validées pendant un essai. Créer d'abord des
fichiers frères clairement identifiés, par exemple :

```text
dragon_walk_left_01.bmp
dragon_walk_left_02_candidate.bmp
dragon_walk_left_03_candidate.bmp
dragon_walk_left_04.bmp
```

Après validation, retirer le suffixe `_candidate`, fixer l'ordre de lecture et
mettre à jour `ANIMATION_GROUPS` dans `tools/generate_tft_assets.py`.

La marche droite peut être dérivée de la marche gauche par miroir uniquement si
les keyframes droite existantes confirment que les détails sont réellement
symétriques. Les yeux, reflets, ailes et éclairages doivent être comparés avant
d'accepter ce raccourci.

## Contrôles automatiques minimaux

Chaque nouvelle frame doit satisfaire les règles suivantes :

- canvas exact de 112×112 px ;
- format BMP non compressé 8 ou 24 bits ;
- palette limitée aux couleurs des keyframes de la famille ;
- aucune nuance magenta visible après normalisation ;
- surface visible dans une tolérance de 6 % au sein de la séquence ;
- ligne de sol dans une tolérance de 2 px ;
- positions des yeux, cornes et centre du ventre contrôlées par des points
  d'ancrage ;
- absence de pixel opaque isolé et de trou d'un pixel dans les aplats ;
- round-trip RLE et CRC valides.

La tolérance globale actuelle du générateur reste plus large pour accepter les
assets historiques. Les nouvelles animations doivent employer les contraintes
plus strictes ci-dessus.

## Contrôle visuel obligatoire

Préparer pour chaque séquence :

- un contact sheet `A / intermédiaire(s) / B` agrandi par facteur entier ;
- un GIF en boucle à la cadence cible ;
- une version sur fond cyan, vert et sombre pour révéler les franges ;
- une comparaison avec les keyframes originales à l'échelle 1:1.

Rejeter immédiatement une frame si elle présente un des défauts suivants :

- taille ou silhouette différente sans justification par le mouvement ;
- œil, reflet, corne, crête, aile ou ventre redessiné ;
- expression ambiguë entre deux actions ;
- double contour ou membre fantôme ;
- pixel isolé, trou dans un aplat ou raccord cassé ;
- nouvelle couleur injustifiée ;
- variation verticale donnant l'impression que le dragon change de taille.

## Validation sur le prototype

La validation finale suit toujours cet ordre :

1. générer et compiler l'image W25Q64 ;
2. programmer avec `asset-flash-programmer` ;
3. confirmer `ASSET FLASH OK` ;
4. lancer `asset-storage-test` et valider tous les CRC ;
5. réinstaller le firmware normal ;
6. contrôler la fluidité, les contours, les expressions, le rognage et le
   scintillement sur le TFT réel ;
7. ne committer qu'après confirmation visuelle explicite.

Le nombre de frames et la cadence doivent rester ajustables après ce test : une
animation techniquement correcte mais peu lisible ou trop rapide n'est pas
considérée comme terminée.
