# Habillage V2 — séparation jambe arrière / queue

Demande utilisateur : la jambe arrière se confond avec la queue ; renforcer le détourage.
Édition avec imagegen intégré, skill imagegen. Source : `skin-keypose-v1.png`.
Résultat : `skin-keypose-v2.png`. V1 conservée, mouvement approuvé inchangé.
Un premier essai trop subtil a été écarté. La variante retenue renforce le contour
sombre au croisement et assombrit la jambe arrière. Proposition non approuvée,
toujours à recaler sur la grille native avant intégration.

## Prompt final

Use case: precise-object-edit. Edit the attached original dragon image. The prior subtle contour approach is insufficient: make the lifted REAR LEG visibly distinct from the TAIL with a clear dark internal contour. In this 1254x1254 composition, the confusing overlap is approximately x440–610,y885–1005: the little hanging yellow claw belongs to the rear foot, not the tail. Draw an unmistakable continuous stair-stepped very dark purple dividing line about one existing outline block thick (roughly 12–16 image pixels) from the hip near (606,897), diagonally down-left through (546,928) toward (476,948). Below this boundary, shade the bent rear leg a darker burnt orange than the bright orange tail above it, keeping the existing hanging yellow claw at (488,985). The tail must continue leftward above this boundary, the rear foot below it. Do not move the foot or tail, do not add any limb or claw. This localized occlusion edge must be clearly readable at thumbnail size. Preserve all other pixels as closely as possible: head, face, horns, wing, torso, foreground arm and leg, ground line, background, framing and pixel-art style. No global restyling.
