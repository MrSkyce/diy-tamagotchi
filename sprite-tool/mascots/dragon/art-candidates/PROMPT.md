# Habillage candidat — pose 00

Outil : imagegen intégré, via le skill imagegen. Statut : proposition graphique
non approuvée ; ce PNG haute résolution n'est pas un sprite intégrable.

Entrées : dragon de référence (identité graphique) et pose 00 du mannequin validé
(contrainte de pose). Les chemins relatifs à sprite-tool sont `references/dragon/walk_right_01.png`
et `mascots/dragon/motion-reference/frame_00.png`.

## Prompt envoyé

Use case: sketch-to-render. Asset type: one candidate pixel-art key pose for a Tamagotchi dragon, not a final animation. Image 1 is the existing approved dragon identity and pixel-art reference. Image 2 is the EDIT TARGET: the approved motion mannequin frame 00, right-facing side view. Dress the mannequin with the dragon identity from Image 1. Preserve Image 2's composition, pose, body placement, head volume, hip, knee, ankle and arm positions, and foot contacts; do not copy Image 1's frontal pose. Keep the mannequin's small torso and articulated short limbs. Apply orange dragon skin, pale yellow belly, bright blue eye visible in profile, yellow horns, small orange/yellow bat wing and tapering orange tail. Head remains in the mannequin head volume, muzzle faces right; horns may extend just above the volume. Near foot planted at the same position and rear foot slightly lifted at the same position. Use sparse, clean, genuine low-resolution pixel art with crisp square pixel clusters and dark outline, few flat shading colors, no smooth gradients, no high-resolution illustration disguised as pixel art. Square canvas, keep exact relative placement of Image 2's figure and its empty margins, as an enlarged 112 by 112 logical pixel grid. Retain flat navy background #182238 and the ground line of Image 2 so alignment is inspectable. Only one complete character and one pose, no captions, no grid, no extra figures, no watermark. Do not output the original mannequin colors or white skeleton. Prioritize skeletal alignment over adding detail.

## Revue technique

La proposition reprend les couleurs et les signes distinctifs du dragon, mais
ne constitue pas une preuve de respect des articulations. La ligne de sol et
les volumes ne coïncident pas exactement avec la grille source ; le fond est
texturé et les pixels ne sont pas une grille native 112×112 exploitable telle quelle.
Elle ne doit donc pas remplacer la pose validée ni être simplement découpée en
sprite de production. Étape suivante : préparer l'habillage en éléments/poses
sur les masques du rig figé, avec comparaison des appuis et validation artistique.
