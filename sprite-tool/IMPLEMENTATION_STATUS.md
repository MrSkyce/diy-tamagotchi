# État d'implémentation — 9 septembre 2026

## Inflexion retenue

Les cycles rigides sont jugés non convaincants par l'utilisateur. Ils ne sont plus
des candidats à promouvoir : le tableau historique ci-dessous décrit des capacités
techniques, pas la direction graphique actuelle. La nouvelle étape est le
[mannequin articulé de dragon à huit poses](MOTION_STUDY.md), sans habillage.
Son module isolé résout les articulations et produit des volumes colorés, une
superposition du squelette et un déplacement sur sol gradué. Le rig bipède est
désormais chargé depuis un YAML strict, avec contrôles géométriques avant génération.
Marche du mannequin approuvée par l'utilisateur (« marche parfaite »), avec rig
et aperçus figés par empreinte. La référence d'habillage V3 est également approuvée.
Un [cycle habillé candidat](RIGGED_WALK.md) utilise la tête/aile/queue préparées
depuis V3 et des membres rasterisés sur les articulations exactes. Le pipeline
commun accepte désormais six ou huit frames, exports compris (tests synthétiques).
Les tests couvrent notamment l'exclusion des 11 pixels de patte arrière qui contaminaient
la découpe de queue. Les 24 empreintes golden historiques restent inchangées.
Le cycle habillé corrigé et sa taille sont approuvés (« oui, validé. »).
Ses 16 BMP et les 80 BMP des cinq autres marches V4 validées sont intégrés,
sans modifier les 33 anciens : catalogue de 129 images, W25Q64 de 476646 octets.
Les quatre cibles jeu/30s/programmeur/test stockage compilent. Le lecteur HOME
à huit poses synchronisées utilise encore le dragon.
La règle de surface spécifique et les empreintes concernent uniquement ce cycle ;
les autres règles graphiques restent inchangées. Voir l'[intégration firmware](FIRMWARE_INTEGRATION.md).
Programmation et validation ST7789 non réalisées : aucun port ESP32 détecté.
Les autres morphologies sont validées et exportées. Leur sélection et la couverture
des états dans le jeu restent à intégrer ; l'objectif global n'est pas terminé.

## Capacités du compilateur historique à six poses

L'objectif reste le moteur décrit dans le handoff, jusqu'aux vrais assets et à
leur vérification sur ST7789. La disponibilité de la CLI ne suffit pas à déclarer
la V1 complète.

| Exigence du handoff | Preuve actuelle | État |
|---|---|---|
| Générateur Python hors ligne, sans changement du firmware | `src/sprite_animator/`, diff du firmware vide | Implémenté |
| YAML validé, erreurs explicites, identifiants uniques | Schémas JSON, `config.py`, tests de configuration | Implémenté |
| Calques ordonnés, ancres parent/enfant, poses et offsets | `renderer.py`, assertions de pixels, tests de pivots/phase | Implémenté |
| Coordonnées entières, alpha binaire, palette sans interpolation | Schémas et validation PNG, cas d'erreur | Implémenté |
| Masques, patches, miroir gauche | Tests masques et comparaison pixel à pixel | Implémenté |
| Marche six étapes, profils indépendants de l'espèce | Profils bipède/quadrupède sur fixtures, profil rigide réutilisé sur six modèles réels | Implémenté ; mouvement réel candidat |
| PNG, planches, GIF à cadence nominale, trois boucles | Tests des pixels et durées du GIF | Implémenté |
| Contrôles de sol, cadre, palette et avertissements visuels | `renderer.py`, `validators.py`, rapport JSON | Implémenté |
| Séparation generated/approved/export, pas d'approbation implicite | `pipeline.py`, tests d'intégrité/non-écrasement | Implémenté |
| Export RGB565, ordre configurable, clé ou masque, métadonnées | Tests d'octets connus et headers C++ compilés | Implémenté |
| Compatibilité avec les formats du projet | Test BMP112 → lecteur existant → round-trip RLE | Vérifiée sur hôte |
| Golden tests et répétabilité des fichiers | 24 empreintes de fixtures ; deux générations complètes des six modèles réels comparées | Vérifiée sur hôte |
| CLI complète et exemple documenté | `cli.py`, `README.md`, commandes exécutées | Implémenté |
| Noms, dimensions, palettes des six références | Tests lisant les références réelles, aucune mutation | Relevés et compatibles |
| Génération batch de six mascottes | 72 PNG sur les six références réelles, manifestes et aperçus comparés octet par octet | Vérifiée sur candidats réels |
| Calques et poses d'une vraie mascotte pilote | Huit sélections, un patch et un cycle rigide à six frames ; identité/sol vérifiés | Candidat à revoir, poses alternatives absentes |
| Deuxième morphologie réelle | Oiseau jaune avec deux ailes/deux pattes, même moteur ; modèle frontal conservé | Structure éprouvée, mouvement/vue latérale non approuvés |
| Six animations visuellement approuvées | Aucun lot réel approuvé | À réaliser |
| Intégration firmware et affichage ST7789, Flash et temps de rendu | Aucun export de production intégré ; aucun port USB ESP32 observé | À réaliser sur matériel |

## Décisions conservées

- Les six modèles approuvés et les 33 BMP de production restent inchangés.
- Les exemples géométriques ne constituent pas une approbation graphique et ne
  sont pas copiés dans les assets embarqués.
- Aucun besoin de profil atypique n'est encore établi : les profils bipède et
  quadrupède servent aux fixtures, et le profil rigide commun aux candidats réels.
- La préparation des vrais assets est décrite dans `ASSET_PREPARATION.md`.
- Le premier cycle du dragon est documenté dans `mascots/dragon/README.md` ; il
  n'est pas approuvé. Ses tests de pixels et d'appui ne prouvent pas sa qualité artistique.
- Le format BMP d'export est le pont vers la chaîne W25Q64 existante. L'export
  brut ou C++ ne remplace pas l'image RLE `TAMASPR` du jeu.

Les fixtures synthétiques autorisent le premier incrément prévu au §21 du handoff.
Les tests des six candidats réels complètent ce premier incrément et vérifient
la conservation des références, des couleurs intérieures et des zones identitaires,
les lignes de sol et la continuité des composants. Ils ne valident pas les critères
artistiques et matériels du §18. Les poses alternatives dessinées, la revue humaine,
la lisibilité latérale et les essais ST7789 restent nécessaires à la V1 complète.
