# Oiseau jaune — deuxième structure réelle

Le candidat utilise cinq calques extraits du modèle neutre approuvé : corps et
visage communs, deux ailes et deux pattes. Il réutilise `rigid_walk.yaml`, sans
changement du code du moteur ni de la référence graphique.

La préparation enlève explicitement 28 pixels de frange reliés au fond sur un
dérivé, conformément au normaliseur existant. La recomposition est exacte après
ce nettoyage. Les pattes et ailes sont translatées sur des coordonnées entières ;
aucune pose cachée ni vue latérale n'est inventée. Le visage reste frontal.

- [Cycle droite](../../generated/yellow_bird/walk/right/walk-4x.gif)
- [Cycle gauche](../../generated/yellow_bird/walk/left/walk-4x.gif)
- [Planche](../../generated/yellow_bird/walk/right/sheet-4x.png)
- [Calques](../../prepared-layers/yellow_bird/layers.png)

Six images distinctes, sol y=100 et absence de composants isolés sont vérifiés
sur hôte. Les appuis, raccords et la boucle restent à valider visuellement.
Ce candidat n'est pas approuvé et n'est pas intégré au firmware.
