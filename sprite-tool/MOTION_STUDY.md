# Inflexion : mannequin articulé, puis habillage

**Marche validée par l'utilisateur le 9 septembre 2026 : « marche parfaite ».**
La [preuve d'approbation](mascots/dragon/MOTION_APPROVAL.json) fixe les empreintes
du rig et des aperçus conservés dans `mascots/dragon/motion-reference/`.
Elle concerne le mouvement seul, pas l'habillage ou son intégration firmware.
La [référence d'habillage V3](mascots/dragon/art-candidates/skin-keypose-v3.png)
est également approuvée (« top »). Le [cycle habillé corrigé](RIGGED_WALK.md)
et sa taille sont ensuite approuvés (« oui, validé. ») et intégrés au firmware.

Direction choisie le 9 septembre 2026. Les cycles par translations rigides sont
écartés comme direction artistique ; ils restent disponibles comme diagnostics
techniques. Les anciennes références approuvées restent intactes ; le nouveau
cycle approuvé a ses propres assets de production.

## Premier jalon : étude de mouvement du dragon

```sh
rtk proxy sprite-tool/.venv/bin/python -m sprite_animator.mannequin sprite-tool/generated/dragon-mannequin-v1
```

La même étude peut être générée depuis le rig versionné, dans une nouvelle destination :

```sh
rtk proxy sprite-tool/.venv/bin/python -m sprite_animator.mannequin sprite-tool/generated/dragon-mannequin-declarative-v1 --rig sprite-tool/mascots/dragon/mannequin.yaml
```

Le YAML complet décrit les longueurs, la position du bassin, les volumes relatifs
au bassin, les huit offsets des pieds, les levées, le rebond et la cadence.
Les champs inconnus, manquants ou dupliqués sont refusés, ainsi que les cibles
inaccessibles, les appuis glissants et le débordement du mannequin hors du cadre.
Le JSON produit conserve tous les paramètres effectifs et les articulations résolues.

La destination doit être nouvelle : pas d'écrasement. Pour une itération, choisir
un nouveau suffixe. Le prototype est isolé du compilateur historique à six poses
et ne dispose d'aucune voie d'approbation/export firmware.

- [Mannequin sur place](generated/dragon-mannequin-v1/walk.gif).
- [Articulations superposées](generated/dragon-mannequin-v1/skeleton.gif).
- [Déplacement sur sol gradué](generated/dragon-mannequin-v1/travel.gif).
- [Huit poses, lecture de gauche à droite puis seconde ligne](generated/dragon-mannequin-v1/sheet.png).
- [Géométrie et paramètres](generated/dragon-mannequin-v1/motion.json).

Orange : membres proches ; bleu : membres éloignés ; vert : torse ; beige : tête ;
violet : aile ; vert sombre : queue. Ce mannequin est une hypothèse de volumes
latéraux, **pas un nouveau dessin de dragon validé**. Aucun pixel des références
ou du tutoriel n'est utilisé. Il n'a volontairement ni visage ni détails.

Huit poses de 120 ms ; cuisse et tibia de 12 pixels ; déplacement de 3 pixels
par pose. Chaque jambe porte pendant quatre poses, puis se replie pendant quatre
poses. La résolution à deux os interdit l'allongement pour atteindre une cible
inaccessible. Les pieds ont une empreinte constante et plate : le déroulé des
orteils n'est pas encore travaillé. Les bras accompagnent la jambe opposée.
La tête et le torse suivent le bassin ; queue et aile n'ont pas encore de mouvement
secondaire. Les proportions sont réglables dans `mascots/dragon/mannequin.yaml`.
Ce format reste un mannequin bipède à huit poses ; il n'est pas encore une grammaire
universelle pour toutes les morphologies. Les épaisseurs de tracé et l'ordre des
volumes restent propres au dessinateur de diagnostic.

Le GIF de déplacement montre trois cycles puis revient au départ : cette remise
à zéro est un montage d'aperçu, pas une discontinuité du cycle de marche.

## Revue avant habillage

1. Les appuis sont-ils lisibles, sans glissement dans l'aperçu en déplacement ?
2. La flexion, le rebond et le rythme évoquent-ils une marche crédible pour un
   petit dragon, plutôt qu'une marche humaine simplement raccourcie ?
3. Les volumes tête/ventre/pattes conviennent-ils à l'identité visée ?
4. Le croisement des jambes reste-t-il lisible à la taille native de 112×112 ?

Les tests vérifient les longueurs avant arrondi, une erreur raster bornée à √2 px,
les appuis dans le repère du sol y compris à la jonction des cycles, l'alternance,
les huit poses distinctes et la reproductibilité des fichiers. Ils ne valident
pas ces quatre critères artistiques. Statut : **marche approuvée par l'utilisateur**.
Les métadonnées des sorties d'origine restent inchangées pour conserver leurs
empreintes ; `MOTION_APPROVAL.json` porte la décision ultérieure.

Prochaine étape : vérifier le cycle intégré sur ST7789, puis décliner les autres
morphologies. Le pipeline commun a été adapté aux huit frames.
La déclinaison aux cinq autres mascottes et l'intégration TFT viennent ensuite.
