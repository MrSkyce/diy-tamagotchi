# Audit de l'intégration — 10 septembre 2026

Périmètre : handoff sections 4, 11–18, décision prioritaire des huit poses,
six marches approuvées et choix à la création demandé par l'utilisateur.
Ce document ne constitue pas une déclaration de fin.

Vérification du 10 septembre : 199 tests hôte passent (50,80 s), Ruff est propre
sur les modules modifiés et leurs nouveaux tests, `git diff --check` est propre.
La cible `tamagotchi-30s-test` compile : RAM 40896 octets, Flash 357258 octets.
Aucun téléversement effectué.

| Exigence | Preuve actuelle | Limite / suite |
|---|---|---|
| Sources conservées, six identités | Références, approbations et tests de références | Pas de nouvel art approuvé par héritage |
| Marche sur squelette, deux morphologies au moins | Dragon + cinq V4, oiseau à segments courts, tests de poses et chevilles | Validation TFT encore absente |
| Reproduction identique | `generate-rigged`, reconstruction des 96 PNG comparés aux lots approuvés | Échec explicite si un pixel/fichier diffère |
| PNG, sheet, GIF trois cycles, rapports | `pipeline`, `preview`, manifestes des six lots | `generate-all` historique ne sélectionne pas les nouveaux rigs |
| Configuration stricte, erreurs explicites | JSON Schema du compositeur et des variantes, validation commune des rigs, tests négatifs | Les 20 configurations historiques V1–V4 restent acceptées ; aucune approbation héritée |
| Approbation sans écrasement implicite | Six lots `approved`, empreintes, tests transaction/export | Aucun commit/push demandé dans l'étape actuelle |
| RGB565, endian, clé/masque, métadonnées | Exporteurs, tests C++ et codec | RGB/BGR et ordre réel sur TFT à observer |
| Flash et décodeur embarqué | 129 BMP / 476646 octets ; vrai `tft_asset_store.cpp` testé sur toutes les images | Test hôte remplace le bus SPI, pas le décodeur ; temps matériel non prouvé |
| Lecteur temps/position, six espèces | `WalkCycle`, registre 96 IDs, HOME et mode `mascot-walk-test` compilés | Mesurer charge TFT et vérifier visuellement tous les changements |
| Choix à la création et persistance | Gestionnaire réel testé avec services simulés ; codec v7/v8 et adaptateur NVS testés | Coupure physique, réveil et écran de choix à vérifier sur carte |

## Validation des configurations de variantes

`variant_config.py` refuse les champs inconnus, doublons JSON, nombres non finis,
coordonnées non entières ou hors canevas, rigs invalides, couleurs hors palette,
styles de pieds inconnus, chemins sortants ou symboliques et sources modifiées.
La source doit être un PNG opaque non animé, au plus 4096 pixels par dimension.
Ces contrôles précèdent la transaction de génération. Les paramètres complets du
rig passent par le même contrôle strict que le mannequin YAML.

La reconstruction `rebuilds/approved-walks-strict-config` a réussi : 96 PNG
identiques octet pour octet aux lots approuvés, sans remplacement des références,
ni nouvel export de production. Les tests de reconstruction couvrent également
ce contrat lors de chaque suite complète.

## Correction du lecteur Flash issue de l'audit

L'identifiant INVALID était initialement égal au marqueur de cache vide ; `load`
renvoyait donc true avant initialisation. Un `begin` en échec gardait aussi un
pointeur Flash utilisable. Correction : publication du pointeur seulement après
validation de l'en-tête, contrôle de validité avant le cache, nettoyage du message
d'erreur lors d'un succès de cache. Tests : 129 décodages exacts, tampon stable,
zéro lecture sur cache valide, INVALID, échec de réinitialisation, erreurs d'offset,
taille/dimension, troncature, CRC et reprise après erreur.

## Limite du périmètre artistique

La section 4 du handoff exclut explicitement les animations autres que la marche
de la première version. Les illustrations food/play/sleep/etc. des cinq espèces
sont donc une phase ultérieure, pas un critère ajouté à la fin de ce moteur.
Le fallback immobile identitaire actuel reste annoncé : il n'est pas une nouvelle
animation d'état approuvée. Il faudra valider séparément toute extension artistique.

## Portes matérielles non franchies

Carte indisponible pendant le déplacement de l'utilisateur. Aucun téléversement
effectué. À vérifier : programmation cohérente des assets et du firmware, ordre
des couleurs/octets, contours/chevilles/sol, temps de chargement et d'affichage
par rapport aux 120 ms, choix et persistance sous coupure/reprise. Les exécutables
hôte et les compilations ESP32 ne remplacent aucune de ces preuves.
