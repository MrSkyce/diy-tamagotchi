# Proposition — animations et cinq mascottes

Date : 8 septembre 2026. Statut : proposition rédigée ; cinq modèles V1 validés
par l'utilisateur (« les 5 nouveaux modèles sont validés »).
Cette phase ne modifie ni le firmware, ni les 33 BMP validés, ni la W25Q64.

## Diagnostic fondé sur le projet actuel

Sources relues : README, HANDOFF, GRAPHICS_PLAN, ANIMATION_GUIDELINES,
ASSET_STORAGE, main.cpp, tft_asset_store et le générateur BMP/RLE.
Le HANDOFF décrit la v0.7, schéma NVS 7, TFT seul 240×240. Le catalogue
actuel confirme 33 sprites et une image de 212 482 octets. Une ancienne ligne
de GRAPHICS_PLAN mentionne encore CS=-1 : le HANDOFF actuel fait autorité,
avec CS TFT GPIO9 et CS flash GPIO2.

Le mouvement actuel est A / A relevée / B relevée / B, à 180 ms par phase.
Il ne contient donc que deux poses dessinées. La position évolue séparément
toutes les 120 ms et le clignement utilise une image fermée pendant 140 ms,
toutes les 3,5 secondes. Les expressions de maladie, faim et tristesse sont
statiques et prioritaires dans currentTftHomeDragonFrame(). Augmenter seulement
la fréquence répéterait les mêmes poses et ne corrigerait pas les appuis.

## Direction graphique proposée

Conserver intégralement les keyframes du dragon. Dessiner ses intermédiaires
par parties, avec onion skin : jambes, bras, ailes et queue ; réparer chaque
raccord sur la grille. Verrouiller tête, yeux/reflets, cornes, ventre, palette
et épaisseur du contour hors animation explicite de l'élément concerné.
Pas de fondu, morphing, lissage ou rotation interpolée.

Pour les nouvelles espèces : même grosse tête, petit corps, grands yeux
brillants cyan, contour bleu nuit, aplats saturés et ventre clair. Leur couleur
dominante change, mais la construction des yeux et le langage des contours
doivent rester cohérents avec le dragon. Chaque palette sera figée après
validation du design, puis réutilisée pour toutes ses frames.

Les cinq BMP de mascots-v1/bmp sont les poses neutres validées par l'utilisateur.
Leurs empreintes et palettes sont figées dans mascots-v1/APPROVAL.json.
Ce ne sont pas encore des séquences animées ni des assets testés sur le TFT. Les sources IA
sont archivées dans source et les prompts dans PROMPTS.md. La conversion
de revue utilise un échantillonnage sans interpolation à 112×112, un fond
magenta normalisé et une palette de 24 couleurs maximum, sans dithering.
Cette conversion ne remplace pas une retouche pixel par pixel.

Inspection V1 : famille visuelle reconnaissable, cinq espèces/couleurs présentes.
La revue initiale avait relevé des détails parasites sur le chat et une tête
plus basse pour la salamandre. L'utilisateur a ensuite validé les cinq modèles :
conserver désormais leurs proportions, palettes et expressions. Toute correction
technique de détourage doit préserver ces références, sans redessiner les modèles.
Le contrôle des BMP relève aussi 23 à 67 pixels par image correspondant au
détecteur de nuances magenta du générateur. Une inspection du détourage est
requise ; pour la salamandre violette, distinguer sa palette de peau des franges
avant suppression. Une simulation en lecture seule du normaliseur existant laisse
11 pixels intérieurs #9819BD que le contrôle générique rejetterait. Le manifeste
de validation conserve leurs coordonnées. Ne pas supprimer indistinctement cette
couleur lors de l'intégration. Le fond majoritaire est bien magenta pur, mais le
contrat technique de transparence doit être adapté avant promotion en production.

## Catalogue d'animations cible par mascotte

| Séquence | Dessins cibles | Durée par pose | Intention |
|---|---:|---|---|
| Respiration | 3 | 250–350 ms | torse et épaules, tête stable |
| Clignement | 2 supplémentaires | 80–120 ms | demi-fermé, fermé, demi-fermé, retour |
| Marche gauche | 8 | 120 ms | contact, appui, passage, avancée puis alternance des jambes |
| Marche droite | 8 | 120 ms | même cycle complet ; miroir seulement si éclairage cohérent |
| Joie, faim, tristesse, maladie | 2 par émotion | 220–350 ms | expression lisible et petit geste approprié |
| Fatigue | 3 | 200–250 ms | paupières, bâillement, relâchement |
| FOOD, PLAY, MEDICINE, CLEAN | 3 par action | 160–200 ms | anticipation, action, récupération |
| Sommeil accepté | 3 | 200–300 ms | installation progressive |
| Refus du sommeil | 3 | 200–250 ms | refus expressif, retour au repos |
| Sommeil profond | 3 | 350–500 ms | respiration lente, yeux fermés |
| Geste propre à l'espèce | 3 | 180–300 ms | variété occasionnelle au repos |

Total cible révisé après rejet de la marche V1 : 56 dessins par mascotte,
soit 336 pour six espèces, plus les 7 assets d'œuf partagés = 343 entrées.
Les keyframes compatibles sont réutilisées
dans ce total ; leur conservation en archive ne dépend pas de leur présence
dans le catalogue final. La marche à huit poses doit encore être validée
visuellement ; le nombre de frames ne suffit pas à prouver la qualité du mouvement.

Gestes proposés : dragon qui déploie légèrement ses ailes ; chat qui remue
une oreille et la queue ; chien qui frétille ; souris qui renifle ; oiseau
qui replie/déplie ses ailes ; salamandre dont la queue ondule. Déclencher une
variation de repos toutes les 6–12 secondes environ, sans répéter immédiatement
la même et sans interrompre une action ou un état critique.

## Implémentation firmware après validation des designs

1. Ajouter un lecteur de séquences piloté par millis(), avec pour chaque pose
   assetId, durée, déplacement entier et événement éventuel. Décrire les boucles,
   aller-retours et séquences jouées une fois dans des tables constantes. Remplacer
   progressivement tftAnimatedPair et le compteur global modulo 4. Les animations
   ne doivent ni bloquer les boutons/audio/RTC ni déterminer les effets des soins.
2. Séparer l'état de simulation, l'expression et le clip visible. Garder les
   priorités des états critiques et du sommeil ; réinitialiser la séquence lors
   d'un changement d'état. Revenir au repos en fin d'action. Face animée au sein
   de chaque clip par BMP complet pour garder le cache et le compositeur simples.
3. Synchroniser déplacement et appuis : avancer de quelques pixels entiers par
   phase, avec vitesse moyenne stable, ralentir puis tourner au bord. Ne pas
   ajouter un rebond global à des poses qui contiennent déjà l'amortissement.
4. Ajouter MascotId stable (dragon/chat/chien/souris/oiseau/salamandre) et une
   table MascotDefinition qui associe chaque état à son clip. Ne jamais persister
   TftAssetId, dont l'ordre change avec les noms du catalogue. Proposer un choix
   d'espèce à la création d'une nouvelle partie ; ne pas le changer pendant la vie.
   Les règles de jeu et l'œuf restent communs dans cette première extension.
5. Persister MascotId dans PetSaveData seulement lors de cette seconde phase.
   Le schéma actuel n'a pas ce champ : prévoir une nouvelle version NVS/firmware
   cohérente et expliciter l'effet sur la sauvegarde existante avant déploiement.
   L'ajout de frames seul ne justifie pas un changement de schéma NVS.
6. Étendre le générateur avec un manifeste explicite des espèces et séquences,
   durées et ancrages ; vérifier couverture et références. Les seuils de surface
   absolus du dragon ne s'appliquent pas aveuglément à l'oiseau ou à la souris.
   Définir une référence de taille par espèce et contrôler la stabilité par clip.

## Stockage et fluidité

Conserver W25Q64, RGB565 RLE et le cache unique de 25 088 octets. Pas de plein
framebuffer et pas d'effacement intégral périodique. Recomposer la réunion de
l'ancien et du nouveau rectangle du personnage sur le fond HOME, y compris
queue, déplacement et rebond, puis transférer les zones nécessaires.

À la moyenne actuelle (212 482 / 33), 343 entrées représenteraient environ
2,21 Mo : estimation, pas une mesure du futur lot. Un encodage entièrement
littéral maximal de 25 186 octets par frame donne 8 644 310 octets avec la table,
au-delà des 8 Mio externes. Mesurer l'image RLE réelle et refuser explicitement
une image dépassant la capacité avant programmation. Vérifier aussi la partition interne du
programmateur : son blob complet est inclus dans le firmware de programmation,
contrairement à l'application. Un gros lot pourra imposer un programmateur par
lots ou un flux USB vers la W25Q64 ; ne pas supposer que le blob grandit sans limite.

La lecture/décompression/CRC la plus lente documentée est de 36,451 ms à 8 MHz.
Elle ne comprend pas une preuve du temps total de rendu des futurs assets.
Mesurer chargement + composition + transfert TFT, médiane/p95/maximum, avec
audio et boutons actifs. Viser un maximum inférieur à 70 % de la durée minimale
de pose retenue. En cas de dépassement, optimiser les lectures SPI puis adapter
la cadence ; envisager un second cache uniquement sur preuve du besoin.
En cas de retard, borner le rattrapage, éviter les rafales de frames et conserver
la cohérence des événements de gameplay indépendamment des images sautées.

## Livraison par jalons

1. Revue des cinq designs neutres avec le dragon : validée par l'utilisateur
   le 8 septembre 2026. Les BMP de référence restent dans design/.
2. Après choix des designs, retouches finales et marche gauche du dragon à
   huit poses : planche, GIF à vitesse cible, vue 1:1 et zoom entier, fonds
   cyan/vert/sombre. Validation de cette séquence avant déclinaison du catalogue.
3. Pilotage par tables pour le dragon seul, puis expressions et actions ;
   comparaison sur le TFT réel avec une mélodie et navigation pendant l'animation.
4. Décliner les cinq espèces validées, ajouter sélection/persistance, vérifier
   la couverture de tous les états et les limites du programmateur.

Contrôles de chaque nouveau clip : BMP 112×112 non compressé 8/24 bits,
magenta exact, palette verrouillée, surface ±6 %, sol ±2 px, ancrages identitaires,
absence de trous/pixels isolés/membres fantômes, round-trip RLE et CRC. Exceptions
de saut ou d'ailes ouvertes documentées par clip plutôt que seuils globaux relâchés.
Compiler les dix environnements. Ensuite seulement : programmer l'image,
confirmer ASSET FLASH OK, vérifier tous les CRC dans asset-storage-test,
restaurer l'application, contrôler les six espèces et la veille sur le TFT.
Commit uniquement après validation visuelle et instruction explicite.

## État de cette livraison

Proposition rédigée et cinq BMP de référence validés. Depuis le passage au jalon
suivant, la marche gauche V1 a été rejetée par l'utilisateur : impression de
pattes qui s'allongent. La V2 dans `walk-left-v2/` reconstruit les deux jambes
en huit poses à longueurs constantes et inclut une vue des articulations et
une traversée sur sol gradué. Le diagnostic `animation-preview` cible cette V2.
Les dix cibles normales avaient compilé au jalon précédent et restent inchangées.
Voir `walk-left-v2/README.md`. Aucun téléversement ni validation matérielle de
cette nouvelle séquence n'a encore été réalisé.
La validation des cinq modèles par l'utilisateur est acquise. Le préalable de
choix des modèles est levé ; le premier clip attend sa propre validation visuelle.
Les clips suivants et l'intégration dans HOME restent à réaliser. Aucune
validation matérielle n'est déduite de l'accord sur les cinq modèles.
