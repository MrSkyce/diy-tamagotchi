# Dragon habillé sur le rig approuvé — cycle candidat

La marche du mannequin est approuvée (« marche parfaite »), et l'habillage V3
est retenu comme référence graphique (« top »). Ces validations sont enregistrées
séparément dans `mascots/dragon/MOTION_APPROVAL.json` et `ART_APPROVAL.json`.
**Le cycle habillé corrigé et sa taille sont approuvés : « oui, validé. ».**
Le lot est figé sous `approved/dragon_rigged/walk` et ses 16 BMP ont été promus
avec empreintes sous `assets/tft/rigged_walk_approval.json` à la racine du dépôt.

## Aperçus à examiner

- [Cycle sur place ×4](generated/dragon_rigged/walk/right/walk-4x.gif).
- [Déplacement sur sol gradué](prepared-skins/dragon-v3/travel.gif), trois cycles
  puis retour au départ : ce retour est un montage de l'aperçu.
- [Comparaison mannequin/habillage](prepared-skins/dragon-v3/comparison.png),
  poses 0–3 puis 4–7, mannequin au-dessus de chaque rangée habillée.
- [Cycle miroir à gauche](generated/dragon_rigged/walk/left/walk-4x.gif).

## Construction contrôlée

Correction de découpe après revue : le masque de queue retenait 11 pixels brun
foncé de la patte arrière présente dans la référence V3. Le masque suit désormais
le contour sombre sans ces pixels. Le test de régression vérifie leur exclusion
et la conservation du contour. Aucun autre pixel du calque de queue, aucune
articulation et aucun pixel de la référence approuvée ne sont modifiés. La
préparation antérieure `dragon-v2` reste disponible pour comparaison.

Une tentative de planche complète via imagegen a été écartée : la jambe proche
restait porteuse presque partout, malgré le guide des huit poses. Elle ne sert
donc pas d'entrée au moteur. Le prompt est conservé dans
`mascots/dragon/art-candidates/PROMPT-walk-sheet-rejected.md`.

Le compilateur `sprite_animator.skin` utilise à la place :

1. Le PNG V3 intact, verrouillé par SHA-256, préparé une seule fois à 112×112
   au plus proche voisin et ramené à une palette explicite de 17 couleurs.
2. Des sélections polygonales explicites de tête, aile et queue dans `skin.json`.
   Ces éléments ne changent plus de dessin entre les poses : ils suivent uniquement
   la translation entière du bassin. Le fond bleu est retiré selon une plage RGB
   propre à cette source. Ce n'est pas un détourage universel.
3. Les articulations exactes du rig approuvé, pour dessiner les segments de jambes
   et bras. Pas de translation de pattes rigides ni de générations indépendantes
   des huit visages. La patte arrière est plus sombre ; les griffes sont dessinées
   dans chaque calque de pied, à partir de sa cheville, jamais dans la queue.
4. Un torse et des contours de membres rasterisés, ordonnés explicitement avec
   les autres calques. Ces nouveaux dessins sont des candidats à la revue artistique.

La réduction de la référence, la palette, le torse et les membres ne sont pas
approuvés par héritage. Le rendu est volontairement plus simple que le grand PNG
V3 : la fidélité et la lisibilité native restent à juger. Le rig approuvé n'est
pas modifié pour s'adapter au dessin. Les dimensions, durées et appuis sont
112×112, huit poses de 120 ms, sol y=104, déplacement de 3 pixels/pose.

## Reproduction

Depuis la racine du dépôt, choisir une nouvelle destination pour chaque préparation :

```sh
rtk proxy sprite-tool/.venv/bin/python -m sprite_animator.skin sprite-tool/mascots/dragon/skin.json sprite-tool/prepared-skins/dragon-v4
rtk proxy sprite-tool/.venv/bin/sprite-anim generate sprite-tool/prepared-skins/dragon-v4/mascot.yaml --root sprite-tool --force
```

`--force` remplace uniquement le candidat généré, en conservant l'ancien dossier
dans une sauvegarde sœur `.walk.previous-*`. La préparation refuse tout écrasement.
La recette `skin.json`, les références approuvées et les fichiers du rig ne sont
jamais modifiés. `preparation.json` contient les empreintes des entrées, celles des
fichiers préparés et les coordonnées des poses. Le modèle préparé utilise les huit
poses PNG comme assets maîtrisés du compilateur commun.

## Intégration et preuves

L'[intégration firmware](FIRMWARE_INTEGRATION.md) accepte maintenant ce cycle
explicitement approuvé, sans modifier les seuils des anciens assets. Le lecteur
synchronise les huit poses et le déplacement ; l'essai matériel reste à faire.

Le pipeline commun accepte désormais six **ou** huit poses : chargement, validation
des longueurs de pistes, déphasage et overrides, composition, manifestes, GIF,
approbation, RGB565, masque, BMP et en-têtes C++. Les fichiers des deux directions
doivent correspondre exactement au nombre déclaré. La compatibilité des exemples
historiques reste vérifiée par 24 empreintes golden.

Les tests couvrent la géométrie approuvée inchangée, les griffes aux chevilles,
la tête stable, le sol, la palette, l'alpha, la reproductibilité, les fichiers de
frame 7, les durées GIF et les exports à huit frames sur une fixture synthétique
temporaire. Le dragon corrigé est désormais approuvé/exporté et intégré au lecteur
firmware ; les six références originales restent inchangées. La validation sur
ST7789 et la déclinaison aux autres morphologies restent à réaliser.
