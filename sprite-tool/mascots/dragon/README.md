# Dragon pilote — première intégration au moteur

Statut : **cycle de diagnostic candidat, revue visuelle attendue**. Aucun export
approuvé, aucun changement du jeu, aucun téléversement. Ce cycle réutilise des
pièces rigides ; les poses dessinées alternatives restent à préparer si la revue
montre que les translations seules ne suffisent pas à rendre la marche crédible.

## Reproduire

Depuis la racine du dépôt :

```sh
rtk proxy sprite-tool/.venv/bin/sprite-anim prepare-layers sprite-tool/mascots/dragon/preparation.yaml --root sprite-tool --force
rtk proxy sprite-tool/.venv/bin/python sprite-tool/mascots/dragon/build_patches.py
rtk proxy sprite-tool/.venv/bin/sprite-anim generate sprite-tool/mascots/dragon/mascot.yaml --root sprite-tool --force
```

`--force` est explicite et conserve les résultats précédents dans des dossiers
frères cachés. Le script de patch refuse de remplacer une retouche différente.

## Aperçus

- [Cycle droite ×4](../../generated/dragon/walk/right/walk-4x.gif)
- [Planche droite ×4](../../generated/dragon/walk/right/sheet-4x.png)
- [Cycle gauche ×4](../../generated/dragon/walk/left/walk-4x.gif)
- [Calques séparés](../../prepared-layers/dragon/layers.png)
- [Rapport](../../generated/dragon/walk/validation.json)

## Construction et preuves

La source est `assets/tft/dragon_walk_right_01.bmp`, conservée sans changement,
avec une copie RGBA de travail dans `references/dragon/`. Son SHA-256 est
verrouillé dans `preparation.yaml`.

Les sélections de tête, pattes, bras, queue et ailes sont déclarées en polygones
entiers ; le corps reçoit les pixels restants. La liste `clear_pixels` reproduit
exactement les 57 pixels de frange magenta que retire déjà le codec de production
sur cette keyframe. Elle ne touche que les dérivés. Les huit calques recomposent
pixel pour pixel la référence ainsi nettoyée.

Le petit patch sous le ventre décrit dans `build_patches.py` fournit une surface
masquée dans la pose de référence, mais exposée par le déplacement des pattes.
Il utilise trois couleurs déjà présentes et des coordonnées entières ; c'est
une correction candidate explicite, pas un nouveau dessin de la mascotte.

Le profil générique `rigid_walk.yaml` translate les pattes sans les redimensionner.
Les trois phases d'appui d'une patte alternent avec celles de l'autre. Les bras
accompagnent la patte opposée. Tête, corps, ailes et queue restent fixes.
Six poses de 120 ms forment un cycle de 720 ms ; la direction gauche est un miroir
précalculé. Les silhouettes des membres ne sont ni interpolées ni déformées.

Les tests vérifient la conservation de la zone identitaire supérieure, la ligne
de sol y=104, six poses distinctes, une surface variant de moins de 6 % et l'absence
de composants isolés. Avec un déplacement global de 2 px vers la droite par pose,
les coordonnées théoriques du pied porteur sont fixes pendant ses trois phases
d'appui. Le GIF est sur place : cette propriété ne remplace pas la revue visuelle.

## Revue attendue

Examiner la lecture des appuis, la transition de boucle, le raccord du bassin,
la rigidité éventuelle des pattes et les reflets après miroir. Le rapport sans
erreur ne constitue pas une approbation du mouvement. Toute correction doit
passer par les calques, poses ou patches avant une nouvelle génération.
