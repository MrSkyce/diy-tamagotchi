# Préparer les véritables mascottes

Les références sont recensées dans [design/README.md](../design/README.md).
Leur approbation couvre l'identité graphique, pas des animations encore absentes.
Les modèles neutres sont frontaux ; la marche latérale du dragon possède déjà
des keyframes de production. Les sources initiales n'étaient pas fournies en
calques ; des sélections explicites et des cycles rigides candidats sont maintenant
disponibles pour les [six modèles](mascots/README.md).

## Pilote

Le dragon est le pilote logique : les deux keyframes droites existantes fournissent
un contexte latéral dans `assets/tft/dragon_walk_right_01.bmp` et `_02.bmp`.
Le découpage initial prend `dragon_walk_right_01.bmp` comme référence, via sa copie
RGBA exacte dans `references/dragon/walk_right_01.png`. Les huit calques initiaux
sont produits par `prepare-layers` selon `mascots/dragon/preparation.yaml` ; leur
recomposition reproduit la source après le nettoyage explicite de 57 pixels de
frange, identique à celui du firmware. Un premier cycle à pièces rigides et un
patch sous le ventre sont disponibles : [dragon/README.md](mascots/dragon/README.md).
Les limites anatomiques de ces sélections et le mouvement restent à revoir, et
les poses alternatives restent à préparer selon les retouches nécessaires.
Ce contrôle de conservation ne prouve pas la qualité du rig.

La tête et les traits identitaires doivent être figés sur cette référence ;
alterner deux dessins complets ne démontre pas la qualité du nouveau moteur.

Préparer dans `mascots/dragon/` une copie de travail, sans écraser les BMP :

1. Définir une palette RGBA et un fond transparent binaire ; distinguer les franges
   du fond des véritables couleurs de l'intérieur.
2. Séparer tête, tronc, queue, bras et pattes proches/éloignées. Placer les régions
   cachées et les raccords dans des calques/patches explicites.
3. Dessiner au moins les poses avant, neutre et arrière des membres, dans des
   canevas de même taille avec un pivot fixe. Préserver leurs longueurs apparentes.
4. Définir les ancres entières et associer les membres aux pistes du profil bipède.
5. Composer six poses ; inspecter contact, appui et retour de la jambe libre,
   puis la transition dernière/première et le miroir gauche.
6. Corriger les poses ou overrides, pas les références approuvées ; approuver
   seulement le lot visuellement retenu.

Une pose de retour dessinée peut remplacer `neutral` pour améliorer la levée du
pied. Le format permet d'autres noms de poses ; il impose seulement six étapes.
Le moteur ne prétend pas déduire les appuis d'une silhouette aplatie.

## Deuxième morphologie et six modèles

L'oiseau jaune éprouve une deuxième structure réelle : corps/visage, deux ailes
et deux petites pattes. Les quatre autres modèles ont aussi leurs calques et
candidats. Leur pose frontale ne suffit pas à déduire automatiquement un profil
latéral approuvé : cette présentation reste à revoir. Le profil quadrupède est fourni
et testé sur une fixture, sans attribuer arbitrairement cette démarche à une espèce.

La palette violette de la salamandre requiert une attention particulière : les
11 pixels intérieurs `#9819BD` signalés dans `APPROVAL.json` sont des pixels à
préserver. Les masques alpha du moteur ne reposent pas sur une détection de teinte
magenta ; le détourage explicite permet de conserver cette couleur.

## Intégration ultérieure

Les décisions déjà établies sont 112×112, ST7789 240×240, Adafruit, RGB565
little-endian/RLE, W25Q64 et miroir précalculé. Restent à valider sur les vrais
assets : poses latérales et calques, cadence finale, éventuelles exceptions de sol
et correction de détourage propre à chaque espèce.

Après approbation, exporter les BMP dans un répertoire séparé, étendre le catalogue
et les groupes du générateur embarqué, mesurer la taille RLE, puis tester couleurs,
fluidité, boutons/audio et temps de rendu sur le TFT réel. Une image correcte sur
l'ordinateur ne prouve ni la cadence SPI ni l'absence de scintillement.
