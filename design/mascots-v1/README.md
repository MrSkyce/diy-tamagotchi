# Mascottes V1 — modèles validés

Le 8 septembre 2026, l'utilisateur a confirmé : « les 5 nouveaux modèles sont
validés ». Les silhouettes, couleurs et expressions de ces cinq modèles sont
désormais les références graphiques à conserver. Voir `APPROVAL.json` pour les
fichiers exacts, leurs SHA-256, leurs palettes et le diagnostic de détourage.
Les noms `_candidate` sont conservés pour ne pas casser les liens déjà partagés ;
ils ne signifient plus que le choix des modèles est en attente.

Lire [la proposition](../ANIMATION_PROPOSAL.md) avant toute intégration.
La revue interactive `review.html` affiche les pixels exacts des six BMP,
avec zoom 1×/2× et fonds magenta/cyan/vert/sombre. Elle ne change pas les fichiers
sources et ne masque aucune frange : seul #FF00FF est remplacé à l'affichage.
`embed_review_data.py` actualise les données embarquées depuis les BMP.
La planche contact-sheet.png présente, de gauche à droite :

- ligne 1 : dragon existant de référence, Chat Bleu, Chien Rouge ;
- ligne 2 : Souris Verte, Oiseau Jaune, Salamandre Violette.

Les cinq fichiers de bmp/ sont des BMP RGB 24 bits non compressés de 112×112.
Ils restent hors assets/tft/ pour ne pas être embarqués par les builds actuels.
source/ conserve les générations originales ; preview/ contient les BMP agrandis
×4 sans interpolation. PROMPTS.md conserve les prompts exacts et l'outil utilisé.

Conversion effectuée avec ImageMagick 6, pour chaque identifiant de mascotte :

```sh
rtk proxy convert source/blue_cat.png -sample 112x112! -fuzz 8% -fill '#FF00FF' -opaque '#FF00FF' +dither -colors 24 -type TrueColor BMP3:bmp/blue_cat_idle_01_candidate.bmp
rtk proxy convert bmp/blue_cat_idle_01_candidate.bmp -scale 448x448 preview/blue_cat.png
```

Depuis la racine du projet, contrôle reproductible en lecture seule :

```sh
rtk proxy python3 -B design/mascots-v1/verify.py
```

validation.json contient les dimensions, format, palette, surface, rectangle,
nuances magenta suspectes, taille RLE, CRC RGB565 et SHA-256 de chaque BMP.
Les cinq round-trips RLE passent. Cela vérifie le format et la conversion,
pas le rendu TFT. Le choix artistique est validé par l'utilisateur. Le nettoyage
technique de la transparence reste à traiter dans la chaîne d'intégration,
en préservant les BMP de référence et leurs pixels intérieurs.

Le normaliseur existant enlèverait respectivement 34, 23, 60, 28 et 56 pixels
reliés au fond pour le chat, le chien, la souris, l'oiseau et la salamandre.
Il laisse 11 pixels violets intérieurs de la salamandre, de couleur #9819BD,
que le contrôle générique de matte rejetterait. Ne pas les supprimer en bloc :
adapter la validation au masque de transparence et à la palette de l'espèce.
Les coordonnées sont conservées dans `APPROVAL.json`.

L'aperçu interactif reste l'archive de la revue V1 et affiche encore le libellé
« candidats V1 ». La présente validation s'applique exactement à ses cinq BMP.
Prochaine phase : intégration et animations suivant la proposition ; la validation
des modèles ne vaut pas validation de frames futures ni preuve sur le TFT réel.
