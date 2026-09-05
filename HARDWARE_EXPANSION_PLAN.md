# Câblage complet — ESP32-C3 Super Mini, TFT, W25Q64 et RTC

## État et avertissement

Ce document décrit le montage cible complet, comme pour un câblage réalisé
depuis zéro. Le montage et le firmware de diagnostic ne sont pas encore
validés ensemble sur le prototype.

Le firmware `v0.6` du commit `2875ae6` utilise encore GPIO20 comme sortie RESET
du TFT, considère le CS du TFT relié à GND et ne pilote pas BLK. Tant que le
firmware adapté n'a pas été téléversé :

- laisser `DO/MISO` du W25Q64 déconnecté de GPIO20 ;
- ne pas s'attendre à un affichage fonctionnel avec le nouveau câblage du CS ;
- ne réaliser ou modifier les connexions que lorsque l'USB et toute autre
  alimentation sont débranchés.

## Alimentation et masse communes

- alimenter le Super Mini par son connecteur USB lors du développement ;
- relier le `3,3 V` du Super Mini aux alimentations du TFT, du W25Q64 et du
  PCF8523 ;
- relier ensemble le GND du Super Mini, du TFT, du W25Q64, du PCF8523, du buzzer
  et des trois boutons ;
- ne jamais alimenter le TFT ou le W25Q64 en 5 V ;
- conserver GPIO18 et GPIO19 pour l'USB natif : ne rien y connecter.

## Liste exhaustive des GPIO

| GPIO ESP32-C3 | Connexion complète | État ou usage |
|---:|---|---|
| 0 | `SDA` du RTC Adafruit PCF8523 | I2C, pull-up déjà présent sur le breakout |
| 1 | `SCL` du RTC Adafruit PCF8523 | I2C, pull-up déjà présent sur le breakout |
| 2 | `CS` du W25Q64 | sortie, pull-up externe 10 kΩ vers 3,3 V |
| 3 | une borne du bouton OK | entrée `INPUT_PULLUP`, autre borne vers GND, réveil deep sleep |
| 4 | `SCL/CLK` du TFT et `CLK` du W25Q64 | horloge du bus SPI partagé |
| 5 | borne positive du buzzer passif | sortie audio, borne négative vers GND |
| 6 | `SDA` du TFT et `DI/IO0` du W25Q64 | MOSI du bus SPI partagé |
| 7 | `DC` du TFT | sélection données/commandes |
| 8 | `BLK` du TFT, connexion directe | HIGH = allumé, LOW = éteint |
| 9 | `CS` du TFT | sortie, pull-up externe 10 kΩ vers 3,3 V |
| 10 | une borne du bouton droite | entrée `INPUT_PULLUP`, autre borne vers GND |
| 20 | `DO/IO1` du W25Q64 | MISO, à connecter seulement après adaptation du firmware |
| 21 | une borne du bouton gauche | entrée `INPUT_PULLUP`, autre borne vers GND |
| 18, 19 | aucune connexion | USB natif |

GPIO2, GPIO8 et GPIO9 sont des broches de strapping. Les pull-ups des deux CS
et le pull-up interne du circuit BLK du module TFT les maintiennent à HIGH au
démarrage, conformément au montage cible.

## TFT ZJY154S0800TG01

Le connecteur du module comporte huit broches. Toutes doivent être câblées
ainsi :

| Broche TFT | Connexion |
|---|---|
| `GND` | GND commun |
| `VCC` | 3,3 V |
| `SCL` | GPIO4, SPI SCLK partagé |
| `SDA` | GPIO6, SPI MOSI partagé |
| `RES/RST` | réseau RC autonome décrit ci-dessous, aucun GPIO |
| `DC` | GPIO7 |
| `CS` | GPIO9 et résistance de 10 kΩ vers 3,3 V |
| `BLK` | GPIO8 directement, sans transistor ni résistance externe |

### Reset autonome du TFT

Le Super Mini utilisé ne possède pas de broche RESET ou EN exposée. Générer le
reset matériel du TFT au démarrage avec un réseau RC :

```text
3,3 V ── 10 kΩ ──┬── RES/RST du TFT
                  │
                100 nF
                  │
                 GND
```

Le condensateur doit être céramique et non polarisé. Le firmware déclarera
`RST = -1` ; l'initialisation Adafruit enverra ensuite la commande de reset
logiciel du ST7789.

### Commande du rétroéclairage

Le module TFT intègre déjà un transistor S8050, une résistance de base de 1 kΩ
et un pull-up de 10 kΩ. Aucun transistor externe n'est nécessaire :

- relier BLK directement à GPIO8 ;
- GPIO8 HIGH ou haute impédance : rétroéclairage allumé ;
- GPIO8 LOW : rétroéclairage éteint ;
- le firmware devra maintenir GPIO8 à LOW pendant le deep sleep.

## Mémoire SPI W25Q64 2,7–3,6 V

Toutes les broches du module doivent être câblées ainsi :

| Broche W25Q64 | Connexion |
|---|---|
| `VCC` | 3,3 V |
| `GND` | GND commun |
| `CLK` | GPIO4, SPI SCLK partagé |
| `DI/IO0` | GPIO6, SPI MOSI partagé |
| `DO/IO1` | GPIO20, SPI MISO — laisser ouvert avant le firmware adapté |
| `CS` | GPIO2 et résistance de 10 kΩ vers 3,3 V |
| `WP/IO2` | résistance de 10 kΩ vers 3,3 V |
| `HOLD`, `RESET` ou `IO3` | résistance de 10 kΩ vers 3,3 V |

Ajouter un condensateur céramique de 100 nF entre VCC et GND, au plus près du
W25Q64. Si le module utilisé intègre déjà les pull-ups de `CS`, `WP` ou `HOLD`,
ne pas ajouter une seconde résistance sur la même ligne.

## RTC Adafruit PCF8523

Toutes les connexions nécessaires sont les suivantes :

| Broche PCF8523 | Connexion |
|---|---|
| `VIN/VCC` | 3,3 V |
| `GND` | GND commun |
| `SDA` | GPIO0 |
| `SCL` | GPIO1 |
| `SQW` | aucune connexion pour la première intégration |

Le breakout Adafruit possède déjà des pull-ups de 10 kΩ sur SDA et SCL : ne
pas en ajouter. Installer une pile CR1220 dans son support. L'adresse I2C fixe
est `0x68`. Le futur firmware utilisera `RTClib` et ne modifiera l'heure que
sur commande explicite afin de ne pas la réinitialiser à chaque démarrage.

## Boutons

Les boutons n'ont pas besoin de résistance externe, car le firmware utilise
`INPUT_PULLUP` :

| Bouton | Première borne | Seconde borne |
|---|---|---|
| gauche | GPIO21 | GND commun |
| OK | GPIO3 | GND commun |
| droite | GPIO10 | GND commun |

Le bouton OK sur GPIO3 reste la source de réveil du deep sleep.

## Buzzer passif

| Borne du buzzer | Connexion |
|---|---|
| positive `+` | GPIO5 |
| négative `-` | GND commun |

Ce câblage reprend le buzzer déjà validé sur le prototype.

## Composants externes requis

- deux résistances de 10 kΩ pour les CS du TFT et du W25Q64 ;
- deux résistances de 10 kΩ pour `WP` et `HOLD/RESET` du W25Q64, sauf si elles
  sont déjà présentes sur le module ;
- une résistance de 10 kΩ pour le reset autonome du TFT ;
- un condensateur céramique de 100 nF pour le reset autonome du TFT ;
- un condensateur céramique de 100 nF pour le découplage du W25Q64 ;
- une pile CR1220 pour le PCF8523 ;
- aucun transistor externe pour BLK.

## Ordre de mise en service

1. Débrancher USB et toute autre alimentation.
2. Réaliser toutes les masses et alimentations 3,3 V.
3. Câbler les boutons et le buzzer.
4. Câbler entièrement le TFT, y compris son reset RC, son CS et BLK.
5. Câbler entièrement le PCF8523 et installer la CR1220.
6. Câbler VCC, GND, CLK, DI, CS, WP et HOLD du W25Q64 avec leurs composants.
7. Laisser uniquement `DO/MISO → GPIO20` ouvert.
8. Hors tension, vérifier au multimètre l'absence de court-circuit entre 3,3 V
   et GND, puis contrôler chaque liaison.
9. Adapter, compiler et téléverser le firmware de diagnostic.
10. Vérifier le TFT, le RTC et la commande BLK.
11. Débrancher l'alimentation, connecter `DO/MISO → GPIO20`, puis remettre sous
    tension et lire l'identifiant JEDEC sans écriture ni effacement.

## Prochaine étape logicielle

- déclarer TFT CS GPIO9, flash CS GPIO2, BLK GPIO8, MISO GPIO20 et I2C GPIO0/1 ;
- configurer BLK à HIGH pour allumer et à LOW pour éteindre ;
- mettre les deux CS à HIGH avant l'initialisation du bus SPI ;
- initialiser le ST7789 avec `CS = 9` et `RST = -1` ;
- partager le bus avec des transactions SPI indépendantes ;
- détecter le W25Q64 par son identifiant JEDEC, en lecture seule ;
- détecter le PCF8523 à l'adresse `0x68` et lire l'heure ;
- vérifier l'extinction réelle de BLK et son maintien à LOW en deep sleep ;
- ne choisir un système de fichiers qu'après ces validations électriques.

## Critères de validation

- démarrage normal et mode de téléchargement USB toujours accessibles ;
- reset fiable du TFT après plusieurs mises sous tension ;
- TFT identique à la version validée, sans conflit SPI ni clignotement ;
- identifiant JEDEC stable sur plusieurs redémarrages ;
- date PCF8523 conservée après coupure grâce à la CR1220 ;
- BLK complètement éteint pendant le deep sleep ;
- boutons, buzzer et réveil GPIO3 inchangés.

## Références techniques

- [schéma électrique du module TFT 8 broches](https://akizukidenshi.com/goodsaffix/M154-240240-RGB-8.pdf), notamment le reset exposé et la commande BLK avec S8050 intégré ;
- [pilote Adafruit ST7789](https://github.com/adafruit/Adafruit-ST7735-Library/blob/master/Adafruit_ST7789.cpp), qui accepte `RST = -1` et envoie un reset logiciel pendant l'initialisation.
