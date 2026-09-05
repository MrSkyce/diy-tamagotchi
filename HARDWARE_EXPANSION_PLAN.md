# Extension matérielle — W25Q64, RTC et rétroéclairage

## État

Proposition validée pour le câblage, le 5 septembre 2026. Le montage et le
firmware de diagnostic ne sont pas encore validés. Le firmware `v0.6` du commit
`2875ae6` utilise encore GPIO20 comme sortie RESET du TFT, considère son CS
relié à GND et ne pilote pas BLK.

Ne pas alimenter le montage cible avec `DO/MISO` du W25Q64 relié à GPIO20 tant
que le firmware n'a pas été adapté. Pendant la première phase de câblage,
laisser cette liaison ouverte.

## Pinout cible

| GPIO ESP32-C3 | Fonction cible | État requis au démarrage |
|---:|---|---|
| 0 | RTC PCF8523 SDA | pull-up 10 kΩ présent sur le breakout |
| 1 | RTC PCF8523 SCL | pull-up 10 kΩ présent sur le breakout |
| 2 | W25Q64 CS | pull-up externe 10 kΩ, inactif à HIGH |
| 3 | bouton OK et réveil actuel | `INPUT_PULLUP` |
| 4 | SPI SCLK partagé TFT/W25Q64 | horloge mode 3 pour le TFT |
| 5 | buzzer passif | inchangé |
| 6 | SPI MOSI partagé TFT/W25Q64 | données vers les deux périphériques |
| 7 | TFT DC | inchangé |
| 8 | commande BLK via transistor PNP BC327 | pull-up 100 kΩ, rétroéclairage éteint |
| 9 | TFT CS | pull-up externe 10 kΩ, inactif à HIGH |
| 10 | bouton droite | `INPUT_PULLUP` |
| 20 | SPI MISO du W25Q64 | entrée, liaison différée |
| 21 | bouton gauche | `INPUT_PULLUP` |
| 18, 19 | USB natif | ne pas utiliser |

GPIO2, GPIO8 et GPIO9 sont des broches de strapping. Le montage impose un état
HIGH au démarrage sur les deux CS et sur la base de commande BLK. Les
résistances indiquées doivent être installées avant la première mise sous
tension.

Le RESET du TFT quitte GPIO20 et est relié au signal EN/RST de la carte. Ainsi,
le TFT et l'ESP32-C3 sont réinitialisés ensemble et GPIO20 devient disponible
pour MISO.

## W25Q64 2,7–3,6 V

| W25Q64 | Connexion |
|---|---|
| VCC | 3,3 V |
| GND | GND commun |
| CLK | GPIO4 |
| DI / IO0 | GPIO6, MOSI |
| DO / IO1 | GPIO20, MISO — laisser ouvert avant le firmware adapté |
| CS | GPIO2 avec pull-up 10 kΩ vers 3,3 V |
| WP / IO2 | pull-up 10 kΩ vers 3,3 V |
| HOLD ou RESET / IO3 | pull-up 10 kΩ vers 3,3 V |

Ajouter un condensateur céramique de 100 nF entre VCC et GND, au plus près du
module. Vérifier si les résistances sont déjà présentes sur le breakout avant
d'en ajouter en parallèle.

## TFT ZJY154S0800TG01

- retirer CS de GND et le relier à GPIO9 ;
- ajouter un pull-up 10 kΩ entre CS et 3,3 V ;
- conserver SCLK GPIO4, MOSI GPIO6 et DC GPIO7 ;
- déconnecter RESET de GPIO20 et le relier à EN/RST ;
- retirer la liaison directe entre BLK et 3,3 V ;
- conserver VCC à 3,3 V et GND commun.

## Commande de BLK

Ne pas alimenter BLK directement depuis GPIO8. Utiliser un transistor PNP
BC327 en commutation haute :

```text
3,3 V ─── émetteur BC327
              collecteur ─── BLK TFT
GPIO8 ── 1 kΩ ─ base
3,3 V ─ 100 kΩ ─┘
```

- GPIO8 HIGH ou haute impédance : rétroéclairage éteint ;
- GPIO8 LOW : rétroéclairage allumé ;
- le pull-up entre base et émetteur maintient BLK éteint pendant le reset et le
  deep sleep ;
- vérifier le brochage du BC327 utilisé avant soudure. Le brochage courant en
  boîtier TO-92 est C-B-E, face plate vers soi et pattes vers le bas, mais il
  peut varier selon le fabricant.

## RTC Adafruit PCF8523

| PCF8523 | Connexion |
|---|---|
| VCC | 3,3 V |
| GND | GND commun |
| SDA | GPIO0 |
| SCL | GPIO1 |
| SQW | non connecté pour la première intégration |

Le breakout possède déjà des pull-ups de 10 kΩ sur SDA et SCL. Son adresse I2C
fixe est `0x68`. Installer une pile CR1220 avant les essais. La première
intégration utilisera `RTClib` et ne modifiera l'heure que sur commande
explicite, afin de ne pas la réinitialiser à chaque démarrage.

## Ordre de câblage sûr

1. Débrancher USB, alimentation et batterie principale.
2. Installer les pull-ups des CS et le circuit BC327 de BLK.
3. Déplacer CS, RESET et BLK du TFT.
4. Câbler le PCF8523 et sa pile CR1220.
5. Câbler VCC, GND, CLK, DI, CS, WP et HOLD du W25Q64.
6. Laisser `DO/MISO → GPIO20` ouvert.
7. Vérifier l'absence de court-circuit entre 3,3 V et GND et contrôler chaque
   liaison au multimètre.
8. Adapter et téléverser le firmware de diagnostic.
9. Hors tension, connecter enfin DO/MISO à GPIO20, puis lire l'identifiant
   JEDEC sans aucune écriture ni effacement.

## Prochaine étape logicielle

- déclarer TFT CS GPIO9, flash CS GPIO2, BLK GPIO8, MISO GPIO20 et I2C GPIO0/1 ;
- mettre les deux CS à HIGH avant l'initialisation du bus SPI ;
- initialiser le ST7789 avec `CS = 9` et `RST = -1` ;
- partager le bus avec des transactions SPI indépendantes ;
- détecter le W25Q64 par son identifiant JEDEC, en lecture seule ;
- détecter le PCF8523 à l'adresse `0x68` et lire l'heure ;
- vérifier l'extinction réelle de BLK avant de modifier la logique de veille ;
- ne choisir un système de fichiers qu'après ces validations électriques.

## Critères de validation

- démarrage normal et mode de téléchargement USB toujours accessibles ;
- TFT identique à la version validée, sans conflit SPI ni clignotement ;
- identifiant JEDEC stable sur plusieurs redémarrages ;
- date PCF8523 conservée après coupure grâce à la CR1220 ;
- BLK complètement éteint pendant le deep sleep ;
- boutons, buzzer et réveil GPIO3 inchangés.
