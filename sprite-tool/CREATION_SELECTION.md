# Choix de mascotte à la création

Décision utilisateur : « Choix à la création ».

## Contrat retenu

- Le choix fait partie de la création d'un nouveau compagnon, pas d'un menu de changement permanent.
- Son identité est conservée dans la sauvegarde.
- Une sauvegarde existante v7 garde le dragon et ses statistiques, son âge et son horodatage RTC ; ne pas la supprimer pour proposer un choix.
- Les six références et les marches approuvées restent les sources graphiques.

## État d'implémentation

Le registre `include/mascot_walks.h` fournit les 96 références de frames,
avec des identifiants d'espèce distincts des indices du catalogue Flash.
Le lecteur HOME appelle ce registre pour l'espèce sauvegardée. Les six marches utilisent
la même horloge `WalkCycle` ; aucune génération de pixels sur l'ESP32.

La migration de sauvegarde est implémentée : v7 (40 octets) vers v8 (44 octets),
encodage little-endian explicite, identité dans le même bloc NVS que les stats.
La lecture d'un v7 valide restitue le dragon et tous les champs historiques ;
la prochaine sauvegarde écrit v8. Le codec rejette les identifiants invalides,
versions inconnues, sommes erronées et enregistrements incomplets sans modifier
la structure de sortie. Le firmware porte désormais le numéro v0.8.

Tests C++ natifs : disposition v7 historique et checksum indépendant, migration
sans perte, six identités, corruption de chaque octet, troncatures, aller-retour
déterministe. L'adaptateur NVS réel est également compilé contre un faux
Preferences pour tester lectures sans écriture, échec d'ouverture/d'écriture,
réinitialisation et conservation de l'ancien bloc. Ce faux ne simule pas une
coupure électrique physique.

L'écran de choix est implémenté : gauche/droite parcourent les six espèces,
OK confirme. Aucune sauvegarde du compagnon ni simulation avant confirmation.
L'âge et les horloges de décroissance démarrent à la confirmation ; un échec
d'écriture reste sur le choix avec une invitation à réessayer par OK, sans
boucle de nouvelles écritures. Une confirmation exige que les assets soient prêts.
Les sauvegardes restaurées ne repassent pas par le choix.

`readPetSave` distingue Loaded/Missing/Invalid/Unavailable via les erreurs NVS
réelles : seuls un namespace ou une clé absents ouvrent la création. Un blob
invalide, une erreur d'ouverture ou une lecture incomplète ouvrent SAVE PROTECTED,
sans simulation ni sauvegarde automatique. OK redémarre pour réessayer ; le
raccourci historique L+R cinq secondes reste la réinitialisation explicite.
La lecture NVS est en mode strictement lecture seule, sans création de namespace.

Le gestionnaire réel du choix est compilé en C++ natif avec services matériels
simulés : navigation circulaire, attente sans écriture, assets absents, échec
d'écriture puis confirmation, remise à zéro des horloges et mode protégé sont
testés. Ce test ne prouve pas le dessin TFT, le debounce matériel ou une coupure
électrique ; ces vérifications restent à faire sur carte.
Ne pas confondre sélection de diagnostic et création d'un compagnon.

Attention : un ancien firmware v0.7 ne sait pas lire v8 et son parcours historique
pourrait réinitialiser le compagnon. Ne pas revenir à v0.7 après migration sans
procédure explicite de sauvegarde/restauration. Aucun flash de v0.8 effectué.

## États graphiques à résoudre

Les cinq autres espèces possèdent des marches approuvées, mais pas encore les
poses food/play/medicine/clean/sleep/sick/hungry/sad/blink/happy du dragon.
Le parcours utilise désormais une pose immobile de l'espèce choisie pour ces
états, actions, accueil et sommeil : il ne remplace plus la mascotte par un dragon.
Les effets des actions et leurs textes restent actifs. Ce fallback annoncé est
temporaire, pas une couverture artistique complète ni une nouvelle animation
approuvée. Il reste à produire et valider les illustrations spécifiques des états.
