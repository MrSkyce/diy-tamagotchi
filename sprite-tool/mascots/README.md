# Six mascottes — intégration candidate au moteur

Les six références approuvées disposent désormais de sélections de calques et
d'un `mascot.yaml` exécutable. Le même profil `rigid_walk.yaml` est utilisé pour
éprouver la réutilisation du moteur sur des images et des structures différentes.
Les images de référence restent inchangées.

Ces cycles sont **des candidats de diagnostic à pièces rigides**, pas six marches
artistiquement approuvées. Les cinq nouveaux modèles conservent leur présentation
frontale. Leur déplacement vers la droite et leur miroir ne constituent pas une
validation de vues anatomiques latérales. Des poses alternatives dessinées et des
raccords restent nécessaires selon la revue.

| Modèle | Structure | Aperçu droite |
|---|---|---|
| Dragon | Tête, corps, bras, pattes, ailes, queue et patch de bassin | [GIF](../generated/dragon/walk/right/walk-4x.gif) |
| Oiseau jaune | Corps/visage, deux ailes, deux pattes | [GIF](../generated/yellow_bird/walk/right/walk-4x.gif) |
| Chat bleu | Corps/visage, deux pattes, queue et raccord | [GIF](../generated/blue_cat/walk/right/walk-4x.gif) |
| Chien rouge | Corps/visage, deux pattes, queue et raccord | [GIF](../generated/red_dog/walk/right/walk-4x.gif) |
| Souris verte | Corps/visage, deux pattes, queue et raccord | [GIF](../generated/green_mouse/walk/right/walk-4x.gif) |
| Salamandre violette | Corps/visage, deux pattes, queue et raccord | [GIF](../generated/purple_salamander/walk/right/walk-4x.gif) |

Les termes `near_leg` et `far_leg` sont des rôles de piste/profondeur du rendu,
pas une déclaration que tous ces modèles possèdent une anatomie bipède. Aucune
patte cachée n'a été inventée à partir des dessins frontaux.

## Reproduction

Depuis la racine du dépôt, après installation de la CLI :

```sh
rtk proxy sprite-tool/.venv/bin/sprite-anim generate-all --root sprite-tool --force
```

Cela génère 72 PNG : six étapes × deux directions × six modèles, avec les planches,
GIF et rapports correspondants. `--force` conserve les versions précédentes dans
des dossiers cachés, ignorés par Git. Aucun lot n'est approuvé par cette commande.

Pour reconstruire les calques d'un modèle, utiliser `prepare-layers` avec son
`preparation.yaml`. Les polygones sont des sélections manuelles déclarées.
Les listes `clear_pixels` reproduisent les seuls pixels de frange connectés au fond
identifiés par le codec existant. Les 11 pixels violets intérieurs de la salamandre
sont explicitement testés et préservés. Les calques recomposent exactement chaque
référence après ce nettoyage sur dérivé.

## Limites de la revue actuelle

Les visages sont fixes, les silhouettes des membres ne sont pas redimensionnées,
les lignes de sol sont constantes et les six étapes sont distinctes. Deux
générations complètes sont comparées octet par octet dans les tests.

Le dragon et l'oiseau n'ont pas de composants isolés dans le rapport. Le chat,
le chien, la souris et la salamandre avaient une rupture de raccord de queue
dans certaines étapes. Les surfaces cachées correspondantes sont maintenant
dessinées explicitement dans `build_tail_patches.py`, avec les palettes existantes,
puis placées derrière les pattes. Les six cycles ne présentent plus de composants
isolés ; cette propriété est vérifiée dans les tests. Ces patches restent des
retouches candidates, et l'absence d'avertissement ne prouve pas la qualité du
mouvement ni de sa boucle.

La revue humaine des appuis, du bassin et de la boucle reste en attente, puis
viendront l'export des seuls lots approuvés et les mesures sur le ST7789 réel.
