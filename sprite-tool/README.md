# Générateur d'animations pixel art

**Direction retenue le 9 septembre 2026 : mannequin articulé, puis habillage.**
Les cycles rigides sont écartés comme direction artistique. Le premier jalon est
une [étude de mouvement à huit poses](MOTION_STUDY.md), séparée du compilateur
historique décrit ci-dessous. Sa marche et la référence graphique V3 sont
approuvées ; le [cycle habillé corrigé](RIGGED_WALK.md) et sa taille sont également
validés. Les 16 frames sont intégrées au firmware, compilé mais pas encore testé
sur la carte. Les cinq autres marches V4 sont elles aussi approuvées, exportées
et intégrées ; le choix à la création et sa sauvegarde v8 sont implémentés.

## Reconstruire les six marches actuelles

```sh
rtk proxy sprite-tool/.venv/bin/sprite-anim generate-rigged /private/tmp/tama-walk-review --root sprite-tool
```

La destination doit être nouvelle. `rigged-walks.json` sélectionne le dragon
et les cinq V4. La commande refait les pièces, les 96 PNG et les aperçus, puis
compare les fichiers PNG octet par octet aux lots approuvés. Elle refuse toute
différence et produit `verification.json` ; aucune approbation ni export de
production n'est créé. `generate-all` reste réservé aux configurations historiques
et aux fixtures décrites ci-dessous, pas aux marches actuelles.

Outil Python hors ligne : compose des PNG en six ou huit poses de marche vers la droite,
précalcule le miroir gauche et produit les aperçus avant approbation et export.
Le [handoff](../HANDOFF_CODEX_MOTEUR_ANIMATION_SPRITES.md) reste le cadrage du moteur.
Les références graphiques restent intactes ; l'intégration du cycle dragon au
firmware est décrite dans [FIRMWARE_INTEGRATION.md](FIRMWARE_INTEGRATION.md).

## Installation et première génération

Depuis la racine du dépôt, avec Python 3.12 ou plus récent :

```sh
rtk proxy python3 -m venv sprite-tool/.venv
rtk proxy sprite-tool/.venv/bin/python -m pip install -r sprite-tool/requirements-dev.lock
rtk proxy sprite-tool/.venv/bin/python -m pip install -e 'sprite-tool[dev]'
rtk proxy sprite-tool/.venv/bin/sprite-anim generate sprite-tool/examples/mascots/demo_biped/mascot.yaml --root sprite-tool
```

La génération crée `generated/demo_biped/walk/` : six PNG, une planche, une
planche agrandie ×4, des GIF ×1/×4 pour chaque direction, `validation.json` et
`manifest.json`. Chaque GIF encode trois cycles et se répète indéfiniment.
Une pose consécutive identique peut être fusionnée par l'encodeur GIF ; la durée
totale reste exactement trois cycles. Les six PNG ne sont jamais fusionnés.

Les deux exemples versionnés sont **des fixtures géométriques**, bipède et
quadrupède, pour tester les mécanismes. Ils ne constituent ni de nouveaux modèles
de mascottes ni une validation artistique de leur démarche. La répétition de
certaines poses est volontaire et signalée dans le rapport.

Pour générer les deux exemples ensemble :

```sh
rtk proxy sprite-tool/.venv/bin/sprite-anim generate-all --root sprite-tool/examples
```

Pour créer un espace d'essai indépendant :

```sh
rtk proxy sprite-tool/.venv/bin/sprite-anim init-demo /private/tmp/sprite-demo
rtk proxy sprite-tool/.venv/bin/sprite-anim generate-all --root /private/tmp/sprite-demo
```

La destination d'`init-demo` doit être inexistante. Aucun des chemins ci-dessus
n'est une commande de programmation de la carte.

## Commandes

Les commandes acceptent `--root` après leur nom ; par défaut, la racine est le
répertoire courant. Les chemins des configurations sont relatifs au répertoire
courant, tandis que ceux des assets et profils sont relatifs au fichier YAML.
La V1 accepte uniquement `--animation walk`.

| Commande | Effet |
|---|---|
| `validate chemin/mascot.yaml` | Charge, compose et contrôle en mémoire ; n'écrit rien |
| `generate chemin/mascot.yaml` | Écrit une animation candidate |
| `generate-all` | Prévalide puis génère tous les `mascots/*/mascot.yaml` |
| `generate-rigged destination` | Reconstruit les six marches actuelles et vérifie les 96 PNG approuvés |
| `approve identifiant --reviewed-by nom` | Copie la génération examinée dans `approved/` et fige son empreinte |
| `export identifiant --format rgb565` | Exporte exclusivement l'animation approuvée |
| `test-golden` | Compare les pixels des deux fixtures aux empreintes versionnées |
| `init-demo destination` | Crée deux fixtures dans un nouveau répertoire |
| `prepare-references --repo chemin` | Prépare les copies RGBA exactes des six modèles et des deux keyframes droites du dragon |
| `prepare-layers chemin/preparation.yaml` | Exécute un découpage manuel déclaré en polygones et vérifie la recomposition exacte |

Un résultat valide est écrit en JSON sur stdout (code 0). Une erreur est écrite
en JSON sur stderr (code 2). Les erreurs d'usage d'argparse utilisent son aide
texte et le code 2. Les avertissements du validateur ne modifient jamais les pixels.

Par défaut, les destinations existantes sont refusées. `--force` autorise leur
remplacement ; l'ancien dossier reste récupérable dans un frère
`.walk.previous-<identifiant>`. Cela concerne aussi les approbations et exports.
Un verrou protège chaque destination pendant l'écriture. En cas d'erreur avant
publication, le dossier partiel est supprimé et l'ancien résultat conservé.
Les liens symboliques de sortie et les sorties contenant une entrée sont refusés.
Un batch prévalide toutes ses configurations, mais sa publication se fait par
mascotte : une panne d'I/O peut laisser les premières mascottes terminées.

## Préparer une mascotte

Les [six modèles approuvés](../design/README.md) sont des BMP aplatis de 112×112.
Le moteur exige des PNG RGBA à alpha binaire (0 ou 255). Préparer des **dérivés** :
corps, tête, membres proches/éloignés, appendices, poses alternatives et patches.
Les régions cachées que révèle un mouvement doivent être dessinées explicitement.
Le moteur ne les invente pas et ne déforme pas automatiquement les membres.

Les copies de travail sont disponibles dans `references/`. La commande suivante
permet de les reconstruire dans un nouvel espace de travail (ou avec `--force`
pour remplacer explicitement une copie existante en conservant sa précédente version) :

```sh
rtk proxy sprite-tool/.venv/bin/sprite-anim prepare-references --repo . --root /private/tmp/sprite-reference-work
rtk proxy sprite-tool/.venv/bin/sprite-anim prepare-layers sprite-tool/mascots/dragon/preparation.yaml --root sprite-tool
```

Le [premier cycle du dragon](mascots/dragon/README.md) utilise déjà ces calques
dans le moteur, avec des pièces rigides et un patch explicite sous le ventre.
Cet essai historique est écarté ; il ne faut pas le confondre avec le cycle sur rig approuvé.

Les [six modèles réels](mascots/README.md) disposent maintenant de candidats à
pièces rigides, dont l'oiseau jaune avec une structure de calques différente.
`generate-all --root sprite-tool --force` les génère ensemble : 72 PNG avec
leurs GIF et rapports. Les poses neutres frontales sont conservées ; les animations
restent à revoir et ne constituent pas des vues latérales approuvées.

Le découpage initial du dragon est décrit en coordonnées entières dans
`mascots/dragon/preparation.yaml`. Les sélections revendiquent les pixels dans
l'ordre déclaré ; `body` reçoit les pixels restants. Les huit calques recomposent
exactement la keyframe après retrait explicite de 57 pixels de frange déjà
normalisés par le codec de production, avec chaque pixel opaque restant présent
une seule fois. Les sources restent inchangées. Le résultat dans
`prepared-layers/dragon/` est **à revoir anatomiquement** ; le `mascot.yaml` du
pilote utilise le profil de diagnostic `rigid_walk.yaml`, sans poses redessinées.

Utiliser les palettes propres à chaque espèce. Pour la salamandre, conserver
les violets intérieurs ; le magenta de fond ne doit pas être confondu avec sa peau.
Le contrat de préparation complet figure dans [ASSET_PREPARATION.md](ASSET_PREPARATION.md).

Les schémas formels sont livrés dans `src/sprite_animator/schemas/`. Le YAML est
strict : champs inconnus, clés dupliquées, coordonnées fractionnaires, parents
cycliques, pistes et poses manquantes sont refusés. Aucune rotation n'est exposée.

### Profil de mouvement

Un profil contient six étapes pour chaque piste abstraite. `duration_ms` est
commun aux six poses, multiple de 10 ms (résolution du GIF). `profiles/biped.yaml`
et `profiles/quadruped.yaml` montrent les deux vocabulaires. Aucun profil ne contient
un nom de mascotte ni un chemin d'image.

```yaml
schema_version: 1
id: simple_walk
animation: walk
frames: 6
duration_ms: 120
tracks:
  near_leg:
    - {pose: forward}
    - {pose: forward}
    - {pose: neutral}
    - {pose: backward}
    - {pose: backward}
    - {pose: neutral}
```

### Calques, ancres et exceptions

Voir les YAML exécutables dans `examples/mascots/`. Pour chaque calque :

- `source` fournit la pose `default` ; `poses` associe des noms à des PNG de mêmes dimensions.
- `anchor` est une position dans le canevas pour une racine, ou relative à l'ancre
  résolue du parent. `pivot`, par défaut `[0, 0]`, est un point local dans le PNG.
- `track` sélectionne une piste ; `phase` avance sa lecture de 0 à 5 poses.
- `offset_scale` multiplie les déplacements entiers de la piste, axe par axe.
- `mirror: true` retourne localement le PNG et son pivot. Le parent transmet
  seulement sa translation ; ni ses pixels ni son miroir ne sont hérités.
- `mask` désigne un PNG opaque noir/blanc de mêmes dimensions : noir retire le
  pixel, blanc conserve son alpha. Un patch est un calque avec un `z_index` élevé.

La position finale est `ancre parent + anchor + déplacement piste × offset_scale
+ déplacement override − pivot`. Les overrides de `frame_0` à `frame_5` ajoutent
un déplacement et/ou remplacent la pose. Les enfants suivent les déplacements
du parent. Le dessin est trié par `(z_index, id)`, indépendamment de l'ordre YAML.

```yaml
overrides:
  walk:
    frame_1:
      head: {offset: [0, -1]}
      near_leg: {pose: neutral}
```

La ligne de sol désigne le dernier pixel opaque de la frame. `ground_tolerance`
vaut zéro par défaut. Cette mesure ne prouve pas à elle seule que les pieds portent.
Les contrôles de composants isolés, de poses répétées et de différence entre la
dernière et la première image donnent des avertissements à examiner visuellement.

## Approbation et export

Après inspection des six poses et de la boucle dans les deux directions :

```sh
rtk proxy sprite-tool/.venv/bin/sprite-anim approve demo_biped --root sprite-tool --reviewed-by votre-nom
rtk proxy sprite-tool/.venv/bin/sprite-anim export demo_biped --root sprite-tool --format rgb565
```

L'approbation atteste la revue de ce lot exact ; elle n'est jamais automatique à
la génération. Toute modification d'un fichier approuvé invalide son export.
Pour retoucher, modifier les calques/poses sources, régénérer et revoir le nouveau
lot. Les empreintes protègent contre les modifications accidentelles, pas contre
une falsification volontaire de tous les fichiers et manifestes.

Trois exports sont disponibles dans `firmware-export/<id>/walk/` :

- `rgb565` : `right.rgb565` et `left.rgb565`, six frames contiguës, ordre lignes
  puis colonnes ; `--byte-order little|big`, little par défaut.
- `cpp` : tableaux d'octets dans deux headers C++, dimensions, nombre de frames,
  durée, clé et présence de masque. Ce sont des flux d'octets, pas des tableaux
  `uint16_t` directement utilisables avec `drawRGBBitmap`.
- `bmp` : douze BMP RGB24 compatibles avec le lecteur du projet. Requiert
  112×112 et la transparence par clé magenta. Les fichiers restent hors de
  `assets/tft/` jusqu'à une intégration dédiée.

`--transparency key|mask` sélectionne la clé RGB (par défaut `#FF00FF`) ou un masque
1 bit. Le masque suit l'ordre des pixels, bit de poids fort en premier, avec
bourrage à l'octet à la fin de **chaque frame**. Une collision de couleur opaque
avec la clé **après conversion RGB565** est refusée. Les métadonnées JSON donnent
le format exact, les tailles et les empreintes.

L'export brut n'est pas une image W25Q64 `TAMASPR`. La voie d'intégration existante
est BMP approuvés → catalogue/contrôles du projet → RLE W25Q64. Les familles
d'animation et leurs règles devront être ajoutées lors de l'intégration ; le moteur
ne réécrit pas le catalogue du jeu ni sa sauvegarde NVS.

## Tests et limites de validation

Depuis `sprite-tool/` :

```sh
rtk proxy .venv/bin/pytest -q
rtk proxy .venv/bin/ruff check --config pyproject.toml src tests
rtk proxy .venv/bin/sprite-anim test-golden
```

Les tests couvrent la composition, les erreurs d'assets/configuration, les masques,
les approbations, l'intégrité, la reproductibilité de tous les fichiers générés,
les pixels et la durée des GIF, les octets RGB565 connus et la compilation des
headers avec un compilateur C++ hôte. Des contrôles lisent aussi les six références
réelles et le codec BMP/RLE existant, sans les modifier.

Un batch teste aussi les six candidats réels : recomposition des références,
palettes, pixels violets intérieurs, zones identitaires, sol et répétabilité des
sorties. Ces tests ne constituent pas une approbation des six marches.
Les golden tests portent sur les deux fixtures examinées. Une migration
de Pillow doit être revue ; `requirements-dev.lock` fixe les versions vérifiées.

Les marches actuelles sont revues et intégrées. Les configurations des variantes
sont maintenant validées strictement avant génération (champs, types, rig,
palette et source), sans changement des 96 PNG approuvés. Restent les
mesures/essais sur ST7789 et la persistance sous coupure sur carte.
Voir [l'audit d'intégration](INTEGRATION_AUDIT.md). Les contrôles hôtes ne
constituent pas une validation matérielle.
