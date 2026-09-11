# Déclinaison des cinq autres mascottes

## État au 2026-09-09

Mise à jour intégration après validation : les 80 BMP des cinq V4 ont été exportés
et ajoutés à `assets/tft/`, avec `mascot_walks_approval.json`. Le catalogue commun
contient 129 images et son image Flash mesure 476646 octets. Les 168 tests passent,
dont comparaison exacte des pixels aux PNG approuvés et round-trip RLE ; quatre
cibles PlatformIO compilent. Aucun téléversement. Le lecteur HOME utilise encore
le dragon ; sélection et couverture des états des autres mascottes restent à intégrer.
Les mentions d'absence d'export ci-dessous décrivent les étapes de revue antérieures.

La direction des cinq profils a été validée par l'utilisateur (« oui »). Cette portée est enregistrée dans `OTHER_MASCOTS_DIRECTION_APPROVAL.json`, avec les empreintes des images. Elle ne vaut pas validation des futurs cycles ou export firmware. Les six références originales et la marche validée du dragon sont conservées.

Les cinq cycles V4 sont **validés par l'utilisateur** (« validé »), avec les gros pieds cartoon et les chevilles corrigées : huit poses, 112 × 112, 120 ms par pose, dans les deux directions. Les copies figées et leurs empreintes vérifiées sont dans `approved/<espèce>_rigged_feet_v4/walk/`, avec un `approval.json` par mascotte. Les six références originales et le dragon sont inchangés ; aucun export ou changement du firmware à cette étape.

## Aperçus animés

- **V4, raccord des chevilles corrigé, version validée** : [droite](reviews/mascot-walks-v4/walk-right.gif), [gauche](reviews/mascot-walks-v4/walk-left.gif). Le nettoyage rectangulaire préalable au dessin du pied V3 coupait le tibia lorsqu'il arrivait en biais près du point haut. La V4 restaure sa partie colorée et son contour dans la zone de raccord, sans changer la semelle, les articulations ni le rythme. Gros pieds cartoon conservés ; dragon inchangé. Paramètre `continuous_ankle` dans les configurations `variant-skin-v4.json`. V1–V3 conservées, approbation utilisateur enregistrée séparément, aucun export firmware.
- **V3 cartoon, avant correction des chevilles** : [droite](reviews/mascot-walks-v3/walk-right.gif), [gauche](reviews/mascot-walks-v3/walk-left.gif). Suite au retour « pieds trop petits ! ambiance cartoons, gros pieds », pieds volontairement surdimensionnés, arrondis, avec volumes propres aux espèces. Articulations, rythme, appuis et dragon inchangés ; seuls les pixels autour des chevilles changent. Configurations `variant-skin-v3.json`, préparations `<espèce>-v3`, cycles `<espèce>_rigged_feet_v3`. Pas d'export firmware ni d'approbation automatique. V1 et V2 conservées.
- Version pieds affinés : [droite](reviews/mascot-walks-v2/walk-right.gif), [gauche](reviews/mascot-walks-v2/walk-left.gif).
- Cette V2 conserve les poses et les appuis de la V1. Seul le dessin terminal des pieds change : petites pattes chat/chien, souris plus fine, doigts suggérés salamandre/oiseau. Le dragon est inchangé. Retouche demandée après le retour « les cycles me semblent OK. les pieds sont un peu grossiers ? », puis accord « oui ».
- Les V1 restent disponibles ci-dessous. La V2 est candidate, sans approbation artistique finale ni export firmware. Configurations `variant-skin-v2.json`, préparations `prepared-skins/<espèce>-v2/`, cycles `generated/<espèce>_rigged_feet_v2/walk/`.

- [Comparatif vers la droite](reviews/mascot-walks-v1/walk-right.gif)
- [Comparatif vers la gauche](reviews/mascot-walks-v1/walk-left.gif)

Ordre : chat / chien, souris / oiseau, salamandre / dragon validé. Les GIF comparent trois cycles avec déplacement ; le retour à la position initiale est une remise en boucle de l'aperçu.

Les aperçus individuels sont dans `generated/<espèce>_rigged/walk/{right,left}/walk-4x.gif`. Les pièces et diagnostics sont dans `prepared-skins/<espèce>-v1/`. Les paramètres reproductibles sont dans `mascots/<espèce>/variant-skin-v1.json`.

### Adaptations effectuées

- Pattes et bras rasterisés depuis les articulations, sans les doigts clairs hérités du dragon.
- Quatre espèces : articulations et cadence de la marche du dragon ; palettes et masques spécifiques.
- Oiseau : cuisse/tibia de 8 pixels au lieu de 12, hanche à 88 au lieu de 80, ailes fixes et absence de bras mammaliens. Les huit phases et le déplacement de 3 pixels par pose sont conservés ; ces proportions sont incluses dans la validation visuelle de la V4.
- Têtes, queues et ailes sont des pièces fixes, uniquement translatées avec le mouvement vertical du bassin. Pas encore de mouvement secondaire des oreilles ou queues.
- Contrôles automatisés : appuis, palette, alpha, huit images distinctes, miroir gauche/droite, pièces stables, reproductibilité et absence d'approbation implicite.

### Vérification de cette étape

- V4 chevilles : **165 tests passent**. Test de continuité colorée genou–cheville–pied sur les huit poses, deux jambes et cinq espèces ; modifications limitées au raccord et semelles V3 identiques. Les cinq planches ont été inspectées, Ruff ciblé et `git diff --check` conformes.
- V3 cartoon : **150 tests passent**. Comparaison aux poses V1, changements limités à la zone des pieds, volumes supérieurs à ceux de la V2 rejetée, appuis/palette/miroir/reproductibilité vérifiés. Cinq planches de poses et comparatif inspectés ; Ruff ciblé et `git diff --check` conformes.
- Retouche pieds V2 : **135 tests passent**. Les nouveaux tests comparent les poses aux enregistrements V1, vérifient la diminution de surface des pieds et l'identité de tous les pixels hors de leur zone. Les fichiers V1 restent reproductibles. Ruff ciblé et `git diff --check` conformes ; les cinq planches V2 ont été inspectées.
- Suite complète : `120 passed in 17.44s` (dont 10 nouveaux tests des variantes).
- Ruff : nouveaux fichiers `variants.py` et `test_variants.py` conformes. Le contrôle global signale 14 erreurs de classement d'imports dans des tests préexistants, laissées inchangées.
- `git diff --check` : conforme.
- Inspection des cinq planches de huit poses et de la planche comparative ; pas de vérification sur écran TFT, carte indisponible.

## Images et prompts

- blue_cat : [profil](mascots/blue_cat/art-candidates/profile-v1.png), [prompt exact](mascots/blue_cat/art-candidates/PROMPT-profile-v1.md).
- red_dog : [profil](mascots/red_dog/art-candidates/profile-v1.png), [prompt exact](mascots/red_dog/art-candidates/PROMPT-profile-v1.md).
- green_mouse : [profil](mascots/green_mouse/art-candidates/profile-v1.png), [prompt exact](mascots/green_mouse/art-candidates/PROMPT-profile-v1.md).
- yellow_bird : [profil](mascots/yellow_bird/art-candidates/profile-v1.png), [prompt exact](mascots/yellow_bird/art-candidates/PROMPT-profile-v1.md).
- purple_salamander : [profil](mascots/purple_salamander/art-candidates/profile-v1.png), [prompt exact](mascots/purple_salamander/art-candidates/PROMPT-profile-v1.md).

## Revue visuelle initiale

- Cohérence de style et silhouettes globalement lisibles ; les queues sont distinctes des pieds dans ces poses statiques. Cela ne prouve pas l'absence de chevauchement dans un futur cycle.
- Chat : rayures et doigts clairs ajoutés par le générateur ; à confronter au modèle neutre et à simplifier avant intégration.
- Chien : extension crème sur le front et bout de queue clair proposés sans validation ; doigts très découpés à adoucir.
- Souris : oreilles rondes et queue fine conservées ; les doigts clairs et le corps plus long restent à revoir.
- Oiseau : ailes et pieds aviens conservés, mais tête et corps plus séparés que sur le modèle neutre. Un rig à pattes plus courtes sera nécessaire.
- Salamandre : taches et queue épaisse conservées, aucun ajout de cornes/ailes ; les doigts clairs et le contour queue/patte arrière demandent une attention particulière lors du découpage.
- Ces images haute résolution ne sont pas des assets 112 × 112 prêts à exporter : palette, grille de pixels, transparence et dimensions restent à normaliser après sélection artistique.

## Suite après cette première animation

Les six mascottes disposent maintenant d'un cycle de marche validé (dragon antérieur et cinq V4). Prochaine étape : export des cinq cycles puis intégration de la sélection des mascottes et vérification TFT lorsque la carte sera disponible. Aucun export ni flash effectué lors de l'enregistrement de cette validation.
