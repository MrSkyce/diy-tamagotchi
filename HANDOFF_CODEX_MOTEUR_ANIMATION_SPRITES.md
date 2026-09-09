# Handoff Codex — Générateur d’animations pixel art du Tamagotchi

> Source documentaire du futur moteur, intégrée au dépôt le 9 septembre 2026.
> Ce document décrit le travail à réaliser, pas une implémentation existante.
> Les [six références graphiques](design/README.md) sont conservées ; les anciens
> essais de marche ont été retirés. Le firmware v0.7 reste le socle embarqué.
>
> Pour l'intégration, les [contraintes graphiques](ANIMATION_GUIDELINES.md) et le
> [format de stockage actuel](ASSET_STORAGE.md) complètent ce cadrage : sprites
> 112×112, écran 240×240, RGB565 little-endian compressé en RLE sur W25Q64.
> Les exemples de configuration et d'export ci-dessous sont indicatifs.

## 1. Contexte

Le projet est un Tamagotchi développé autour d’un **ESP32-C3 SuperMini** et d’un écran couleur de type **ST7789**. Il comporte **six mascottes**, chacune disposant ou devant disposer d’un concept art en pixel art.

Le besoin porte sur la production de cycles de marche cohérents pour ces six mascottes.

Le générateur d’animations est exclusivement un **outil de développement hors ligne**. Il ne sera jamais exécuté sur l’ESP32. Le firmware embarqué ne doit contenir que les bitmaps finaux validés et la logique minimale nécessaire pour les afficher successivement.

## 2. Objectif

Concevoir un outil déterministe capable de produire les différentes frames d’un cycle de marche à partir :

- des concept arts pixel art des six mascottes ;
- de parties mobiles préparées sous forme de calques ou de poses alternatives ;
- d’une grammaire de marche commune ;
- d’une configuration propre à la morphologie de chaque mascotte ;
- de quelques corrections ou exceptions artistiques explicites.

Le résultat attendu est un pipeline reproductible : à entrées et configuration identiques, les bitmaps générés doivent être strictement identiques.

Le but n’est pas de générer artistiquement de nouvelles images au moyen d’un modèle probabiliste. Il s’agit de mapper des assets maîtrisés sur des poses et des trajectoires déterministes.

## 3. Principes structurants

1. **Aucun moteur procédural sur l’ESP32** : toutes les frames sont précalculées dans l’environnement de développement.
2. **Pixel perfect** : coordonnées entières, palette contrôlée et aucun filtrage ou anticrénelage.
3. **Assets maîtres non destructifs** : le générateur ne modifie jamais les sources.
4. **Séparation identité/mouvement** : l’apparence appartient aux assets de la mascotte ; le rythme et la mécanique de marche appartiennent aux profils d’animation.
5. **Transformations limitées** : privilégier les translations et les substitutions de poses aux rotations ou déformations automatiques.
6. **Validation humaine obligatoire** : les images générées sont des candidates ; seules les frames approuvées sont exportées vers le firmware.
7. **Exceptions déclaratives** : les adaptations d’une mascotte ou d’une frame doivent être décrites dans sa configuration plutôt que codées en dur dans le moteur.

## 4. Périmètre de la première version

La V1 doit prendre en charge :

- une animation latérale de marche vers la droite ;
- un cycle de **six frames** ;
- la marche vers la gauche obtenue par miroir horizontal ;
- des sprites de dimensions fixes et configurables ;
- des PNG avec transparence comme assets de développement ;
- des calques ordonnés et des poses alternatives ;
- des déplacements sur des coordonnées entières ;
- la génération des frames PNG ;
- la génération d’une sprite sheet et d’un GIF de prévisualisation ;
- des contrôles automatiques simples ;
- l’export des frames approuvées dans un format utilisable par le firmware.

Ne pas inclure initialement :

- l’interpolation subpixel ;
- les transformations affines libres ;
- le rigging complexe par maillage ;
- l’inbetweening par IA ;
- l’animation procédurale exécutée sur l’ESP32 ;
- les animations autres que la marche, sauf préparation de l’architecture pour les ajouter plus tard.

## 5. Architecture cible du pipeline

```text
Concept art et calques PNG
          +
Configuration de la mascotte
          +
Profil morphologique et cycle de marche
          |
          v
Générateur Python déterministe
          |
          +--> Frames PNG générées
          +--> Sprite sheet de contrôle
          +--> GIF de prévisualisation
          +--> Rapport de validation
          |
          v
Validation et éventuelles retouches humaines
          |
          v
Assets approuvés
          |
          v
Conversion RGB565 / format firmware
          |
          v
Bitmaps intégrés au projet ESP32
```

## 6. Arborescence proposée

```text
sprite-tool/
├── README.md
├── pyproject.toml
├── src/
│   └── sprite_animator/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── model.py
│       ├── renderer.py
│       ├── validators.py
│       ├── preview.py
│       └── exporters/
│           ├── png.py
│           └── rgb565.py
├── profiles/
│   ├── quadruped.yaml
│   ├── biped.yaml
│   └── atypical.yaml
├── mascots/
│   ├── mascot_01/
│   │   ├── mascot.yaml
│   │   ├── layers/
│   │   ├── poses/
│   │   ├── patches/
│   │   └── masks/
│   └── ...
├── generated/
│   └── <mascot>/<animation>/
├── approved/
│   └── <mascot>/<animation>/
├── firmware-export/
│   └── <mascot>/<animation>/
└── tests/
    ├── fixtures/
    ├── golden/
    └── test_*.py
```

Les noms définitifs des six mascottes remplaceront `mascot_01`, etc.

## 7. Modèle graphique d’une mascotte

Le concept art de chaque mascotte doit être découpé manuellement en parties cohérentes. Exemple pour un quadrupède :

- pattes éloignées ;
- queue ou appendices arrière ;
- corps ;
- tête ;
- pattes proches ;
- yeux et détails de premier plan ;
- patch final de contour ou de raccord.

Chaque partie est un bitmap PNG transparent. Elle possède :

- un identifiant stable ;
- une position de référence ;
- éventuellement un parent ;
- un point d’ancrage entier ;
- un ordre d’affichage ;
- une ou plusieurs poses discrètes.

Pour les petits membres, fournir de préférence trois poses dessinées :

```text
poses/front_leg_near/
├── forward.png
├── neutral.png
└── backward.png
```

Cette substitution de poses produira un meilleur pixel art qu’une rotation arbitraire d’un bitmap minuscule.

## 8. Grammaire commune de marche

Le cycle commun fournit une timeline normalisée en six frames. Exemple de base :

| Frame | Membres proches | Membres éloignés | Corps |
|---:|---|---|---|
| 0 | vers l’avant | vers l’arrière | hauteur normale |
| 1 | appui avant | retour | descend de 1 px |
| 2 | neutres | neutres | point bas |
| 3 | vers l’arrière | vers l’avant | hauteur normale |
| 4 | retour | appui avant | descend de 1 px |
| 5 | neutres | neutres | remonte |

Exemple de profil abstrait :

```yaml
id: quadruped
animation: walk
frames: 6
duration_ms: 120

timeline:
  body_y: [0, 1, 1, 0, 1, 1]
  head_y: [0, 0, 1, 0, 0, 1]
  near_leg_pose: [forward, forward, neutral, backward, backward, neutral]
  far_leg_pose: [backward, backward, neutral, forward, forward, neutral]
  tail_y: [0, -1, -1, 0, 1, 1]
```

Le profil décrit le mouvement générique. Il ne doit faire aucune référence directe à une mascotte donnée.

## 9. Configuration d’une mascotte

Exemple indicatif :

```yaml
schema_version: 1
id: dragon
canvas:
  width: 48
  height: 48
  ground_y: 41
  transparent: true

palette:
  mode: indexed
  file: palette.png

animation_profiles:
  walk: quadruped

layers:
  - id: rear_leg_far
    source: layers/rear_leg_far.png
    anchor: [14, 29]
    z_index: 10
    poses_dir: poses/rear_leg_far

  - id: front_leg_far
    source: layers/front_leg_far.png
    anchor: [29, 29]
    z_index: 20
    poses_dir: poses/front_leg_far

  - id: body
    source: layers/body.png
    anchor: [22, 22]
    z_index: 30

  - id: head
    source: layers/head.png
    anchor: [34, 17]
    parent: body
    z_index: 40

  - id: rear_leg_near
    source: layers/rear_leg_near.png
    anchor: [15, 30]
    z_index: 50
    poses_dir: poses/rear_leg_near

  - id: front_leg_near
    source: layers/front_leg_near.png
    anchor: [30, 30]
    z_index: 60
    poses_dir: poses/front_leg_near

  - id: outline_patch
    source: patches/body_outline.png
    anchor: [22, 22]
    z_index: 100

parameters:
  body_bob_scale: 1
  stride_scale: 1
  head_delay_frames: 1
  mirror_left: true

overrides:
  walk:
    frame_1:
      head:
        offset: [0, 1]
    frame_4:
      outline_patch:
        offset: [0, 0]
```

Ce schéma est une proposition. Il doit être stabilisé pendant le prototype et validé par un schéma formel, idéalement JSON Schema.

## 10. Algorithme de rendu

Pour chaque mascotte et chaque frame :

1. Charger et valider le profil d’animation.
2. Charger et valider la configuration de la mascotte.
3. Créer un canevas transparent aux dimensions attendues.
4. Trier les parties par `z_index`.
5. Pour chaque partie :
   - sélectionner la pose demandée par la timeline ;
   - calculer la position à partir de l’ancre, du parent et des offsets ;
   - appliquer uniquement des coordonnées entières ;
   - appliquer les overrides de la frame ;
   - composer le bitmap sans interpolation.
6. Appliquer les masques ou patches de raccord déclarés.
7. Vérifier le cadre, la palette, la transparence et la ligne de sol.
8. Exporter la frame PNG.
9. Calculer une empreinte du fichier afin de permettre les tests de non-régression.

Les opérations autorisées en V1 sont :

- translation entière ;
- miroir horizontal ;
- sélection d’une pose alternative ;
- composition alpha sans lissage ;
- application d’un masque binaire ;
- ajout d’un patch de pixels.

Toute rotation éventuelle doit être limitée à des angles explicitement autorisés et désactivée par défaut.

## 11. Validation automatique

Le pipeline doit produire un rapport d’erreurs et d’avertissements. Contrôles minimum :

- dimensions identiques pour toutes les frames d’une animation ;
- nombre de frames conforme au profil ;
- pixels contenus dans le canevas ;
- respect de la palette autorisée ;
- absence d’anticrénelage ou de couleurs imprévues ;
- présence de tous les calques et de toutes les poses référencées ;
- absence d’identifiants dupliqués ;
- stabilité de la ligne de sol ;
- cohérence de la transparence ;
- bouclage visuel vérifiable entre les frames 5 et 0 ;
- taille estimée de l’export firmware.

Les détecteurs plus subjectifs — pixels isolés, membre visuellement déconnecté, raccord imparfait — doivent générer des avertissements, pas modifier automatiquement le dessin.

## 12. Prévisualisation et validation humaine

Chaque génération doit produire :

- les six PNG individuels ;
- une sprite sheet horizontale avec repères facultatifs ;
- un GIF animé à la cadence nominale ;
- si possible, un aperçu agrandi en nearest-neighbor ;
- un rapport texte ou JSON de validation.

Les frames générées ne sont pas automatiquement considérées comme livrables. Le workflow attendu est :

1. génération dans `generated/` ;
2. inspection de la sprite sheet et du GIF ;
3. correction de la configuration, ajout d’une pose ou d’un patch si nécessaire ;
4. nouvelle génération ;
5. copie explicite des frames retenues vers `approved/` ;
6. export firmware depuis `approved/` uniquement.

Ne jamais écraser automatiquement les retouches ou assets présents dans `approved/`.

## 13. Export vers le firmware

La cible probable est un écran ST7789 en couleur. Prévoir au minimum un export :

- RGB565 ;
- ordre des octets configurable ;
- tableau C/C++ ou fichier binaire ;
- transparence par couleur clé ou masque 1 bit configurable ;
- métadonnées : largeur, hauteur, nombre de frames et durée d’une frame.

Structure C++ indicative :

```cpp
struct AnimationFrames {
    const uint16_t* const* frames;
    uint8_t frameCount;
    uint16_t frameDurationMs;
    uint8_t width;
    uint8_t height;
};
```

Le firmware reste responsable uniquement de :

- sélectionner la mascotte et l’animation ;
- choisir la frame d’après le temps écoulé ;
- dessiner le bitmap ;
- gérer la position globale du sprite à l’écran.

La V1 peut précalculer les directions droite et gauche afin d’éviter tout traitement de miroir sur l’ESP32. Une option permettra ensuite d’arbitrer entre consommation Flash et traitement à l’exécution.

## 14. Technologie recommandée

- **Python 3.12+** ;
- **Pillow** pour les opérations bitmap ;
- **PyYAML** ou `ruamel.yaml` pour les configurations ;
- **Pydantic** ou dataclasses avec validation pour le modèle de données ;
- **Typer** pour la CLI, si utile ;
- **pytest** pour les tests ;
- **Ruff** pour le lint et le formatage ;
- JSON Schema exporté ou maintenu pour documenter les fichiers YAML.

Éviter une interface graphique dans le premier incrément. La CLI, les fichiers YAML et les aperçus générés suffisent pour valider le modèle.

## 15. Interface en ligne de commande proposée

```bash
# Valider un profil et une mascotte
sprite-anim validate mascots/dragon/mascot.yaml

# Générer le cycle de marche
sprite-anim generate mascots/dragon/mascot.yaml --animation walk

# Générer toutes les mascottes
sprite-anim generate-all --animation walk

# Approuver explicitement une génération
sprite-anim approve dragon --animation walk

# Exporter les assets approuvés pour le firmware
sprite-anim export dragon --animation walk --format rgb565

# Vérifier que les sorties restent identiques aux références
sprite-anim test-golden
```

La commande `approve` doit refuser d’écraser des assets existants sans option explicite.

## 16. Tests attendus

### Tests unitaires

- chargement et validation YAML ;
- tri des calques ;
- résolution des ancres parent/enfant ;
- sélection des poses ;
- application des offsets par frame ;
- miroir horizontal ;
- validation de palette ;
- conversion RGB888 vers RGB565 ;
- sérialisation C/C++.

### Golden tests

À partir d’un jeu minimal d’assets de test, générer des frames dont l’empreinte ou les pixels sont comparés à des sorties de référence versionnées.

### Test de boucle

Produire automatiquement un GIF répétant le cycle au moins trois fois afin de repérer les ruptures entre la dernière et la première frame.

### Tests d’intégration

- génération complète d’une mascotte ;
- génération complète des six mascottes ;
- export firmware depuis `approved/` ;
- refus d’exporter une animation incomplète ou non validée.

## 17. Plan d’implémentation recommandé

### Étape 1 — Spike sur une mascotte pilote

- choisir la mascotte ayant la morphologie et les assets les plus simples ;
- préparer ses calques et trois poses par patte ;
- coder le compositeur PNG ;
- produire six frames, une sprite sheet et un GIF ;
- vérifier visuellement que le résultat est crédible.

### Étape 2 — Deuxième morphologie

- sélectionner une mascotte structurellement différente ;
- tenter de réutiliser le même profil ou créer un second profil ;
- identifier ce qui doit être générique et ce qui doit être configurable ;
- stabiliser le schéma YAML.

### Étape 3 — Industrialisation légère

- ajouter validation, CLI, rapports et golden tests ;
- documenter la préparation des calques ;
- garantir la reproductibilité des sorties ;
- ajouter l’export RGB565.

### Étape 4 — Généralisation aux six mascottes

- intégrer les quatre mascottes restantes ;
- créer le minimum de profils morphologiques nécessaires ;
- traiter les exceptions par poses, patches ou configuration ;
- mesurer la taille totale des bitmaps.

### Étape 5 — Intégration firmware

- brancher les assets exportés dans le projet ESP32-C3 ;
- vérifier l’ordre des couleurs et des octets sur le ST7789 ;
- mesurer la Flash utilisée et le temps d’affichage ;
- ajuster le format ou la transparence si nécessaire.

## 18. Critères d’acceptation de la V1

La V1 est acceptée lorsque :

- une commande unique génère le cycle de marche de la mascotte pilote ;
- le cycle contient exactement six frames et boucle sans rupture majeure ;
- aucune opération n’introduit d’anticrénelage ;
- deux exécutions avec les mêmes entrées produisent des fichiers identiques ;
- les sorties PNG, sprite sheet et GIF sont générées ;
- les erreurs d’asset ou de configuration sont explicites ;
- les assets approuvés peuvent être exportés en RGB565 ;
- l’export est affichable correctement sur le ST7789 ;
- le modèle a été éprouvé avec au moins une deuxième mascotte de morphologie différente.

## 19. Points à confirmer avant ou pendant le spike

Ne pas inventer ces informations. Les demander ou les relever dans le projet existant :

- noms et concept arts des six mascottes ;
- dimensions exactes des sprites à l’écran ;
- résolution exacte du ou des écrans ST7789 retenus ;
- palette globale ou palette propre à chaque mascotte ;
- couleur et mécanisme de transparence utilisés par le firmware ;
- bibliothèque graphique ESP32 actuellement utilisée ;
- ordre RGB/BGR et ordre des octets attendus ;
- emplacement futur des bitmaps : firmware, partition Flash ou stockage externe ;
- nombre d’animations prévues à terme ;
- capacité à utiliser le miroir au runtime ou nécessité de précalculer les deux directions ;
- existence d’assets sources déjà séparés en calques.

Ces inconnues ne doivent pas bloquer la création du compositeur PNG : utiliser des valeurs configurables et un jeu d’assets de test.

## 20. Consignes à Codex

1. Inspecter d’abord le dépôt et ses éventuelles instructions `AGENTS.md`.
2. Identifier la stack, l’arborescence et le format d’assets déjà en place avant d’ajouter des dépendances.
3. Ne pas modifier le firmware lors du premier spike, sauf demande explicite.
4. Construire le générateur par petits incréments testables.
5. Ne pas inventer la morphologie ou les noms des six mascottes en l’absence des assets.
6. Maintenir toutes les coordonnées et transformations en nombres entiers.
7. Bannir tout redimensionnement avec interpolation autre que nearest-neighbor.
8. Ne jamais écraser les assets sources ou approuvés sans option explicite.
9. Fournir une commande reproductible, des tests et un exemple minimal documenté.
10. Signaler toute hypothèse qui affecte le format embarqué avant de figer l’exporteur.

## 21. Livrables attendus du premier incrément

- squelette du projet Python ;
- schéma de configuration initial ;
- profil de marche six frames ;
- compositeur de calques et de poses ;
- une mascotte de démonstration ou un fixture synthétique ;
- génération PNG, sprite sheet et GIF ;
- validations fondamentales ;
- tests unitaires et golden test ;
- README avec installation et commandes ;
- liste des décisions à prendre pour intégrer les véritables mascottes.

Le premier incrément doit démontrer la viabilité de l’approche, pas chercher à produire immédiatement toutes les animations définitives.
