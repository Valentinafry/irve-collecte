# Collecte IRVE dynamique (France + Pays-Bas)

Historisation des statuts temps reel des points de charge publics francais
(libre / occupe / hors service), a partir de la consolidation nationale du
Point d'Acces National [transport.data.gouv.fr](https://transport.data.gouv.fr).
Ces statuts sont publies en continu mais **aucun historique national n'est
conserve** : ce depot l'enregistre.

Depuis le 26/08/2026, le depot collecte aussi les PAYS-BAS (`collecte_nl.py`,
donnees dans `donnees_nl/`) : dump national OCPI 2.2.1 du Point d'Acces
National neerlandais [opendata.ndw.nu](https://opendata.ndw.nu) (obligation
AFIR art. 20) — ~80 000 stations, ~200 000 EVSE, statuts OCPI (AVAILABLE /
CHARGING / BLOCKED...), positions, puissances par connecteur et tarifs dans
la copie mensuelle. Meme principe : seuls les changements de statut sont
enregistres, horodates par l'operateur (`last_updated`).

## Pays en attente de cles (scripts dormants, actives des depot de la cle)

Les cles vivent dans `cles/` (gitignore, a creer sur la VM ET en local).

**Norvege + Suede (NOBIL / Enova)** — deux inscriptions :

1. Cle API NOBIL (referentiel) : formulaire sur
   [nobil.no](https://info.nobil.no/api) -> deposer la cle dans
   `cles/nobil_apikey.txt`. `collecte_no.py` archive alors le datadump
   mensuel (stations, puissances, prises) pour NOR et SWE.
2. Flux temps reel : compte sur [data.enova.no/signup](https://data.enova.no/signup),
   souscrire le produit « NOBIL Real-time », deposer la cle d'abonnement
   dans `cles/enova_subscription.txt`. Lancer `ecoute_nobil.py` en service
   permanent (systemd) sur la VM : il negocie l'URL WebSocket et ajoute
   chaque evenement de statut, brut, dans `donnees_no/evenements/` (jsonl).
   Exemple d'unite systemd :

       [Unit]
       Description=Ecoute NOBIL temps reel
       After=network-online.target
       [Service]
       WorkingDirectory=/home/debian/irve-collecte
       ExecStart=/usr/bin/python3 ecoute_nobil.py
       Restart=always
       RestartSec=30
       [Install]
       WantedBy=multi-user.target

**Finlande (Fintraffic / Digitraffic, API AFIR) — ACTIF depuis le 26/08/2026** :
`collecte_fi.py`, statuts temps reel de ~19 850 EVSE (AVAILABLE / CHARGING /
OUTOFORDER...) via l'API ouverte afir.digitraffic.fi (sans cle, pagination
par curseur, snapshots a la minute) + locations (GeoJSON) et tarifs en copie
mensuelle. Horodatage operateur (`lastUpdatedAt`) conserve. Donnees dans
`donnees_fi/`.

**Suisse (ich-tanke-strom / DIEMO, OFEN) — ACTIF depuis le 26/08/2026** :
`collecte_ch.py`, statuts temps reel de ~19 200 EVSE (JSON federal sans
cle, data.geo.admin.ch) + statique mensuel. Pas d'horodatage operateur :
precision = cadence de collecte. Donnees dans `donnees_ch/`.

**Luxembourg (Chargy) — ACTIF depuis le 26/08/2026** : `collecte_lu.py`,
occupation PAR STATION (disponibles/occupes) des ~530 stations Chargy, KML
officiel de data.public.lu (cle publique, rafraichi ~5 min, rate-limite :
un appel par cycle maximum). Donnees dans `donnees_lu/`.

**Allemagne (Ladesaeulenregister BNetzA) — ACTIF depuis le 26/08/2026** :
`collecte_de.py` archive chaque nouveau MILLESIME du registre federal
(~210 000 points : operateurs, puissances, dates de mise en service ;
CC-BY 4.0, attribution Bundesnetzagentur.de, ~9 Mo gzip par millesime,
renouvele environ mensuellement). Sans cle. Pas de statut temps reel :
le dynamique allemand passe par Mobilithek (compte gratuit + abonnement
par operateur, DATEX II obligatoire depuis le 14/04/2026) — a brancher
quand le besoin le justifiera. Interface REST quotidienne du registre
disponible sur demande a ladesaeulenregister@bnetza.de.

**Autriche (Ladestellenverzeichnis E-Control) — ACTIF depuis le 26/08/2026** :
`collecte_at.py` archive une photo QUOTIDIENNE du parc complet via le flux
groupe `/search/stations` (~15 800 stations, ~40 000 points, avec les PRIX
structures — cent/kWh, frais de demarrage et de blocage). Cle API en
en-tete `Apikey` (en minuscules) + `Referer: https://afry.com` (domaine
declare), stockee dans `cles/ladestellen_identifiants.txt`. Le statut temps
reel n'existe pas dans le flux groupe (detail par station uniquement,
~15 800 requetes par balayage) : piste = flux DATEX II AFIR, a demander a
support@ladestellen.at.

## Fonctionnement

Toutes les ~5 minutes (GitHub Actions), `collecte.py` :

1. telecharge la [consolidation nationale IRVE dynamique](https://proxy.transport.data.gouv.fr/resource/consolidation-nationale-irve-dynamique)
   (~105 000 points de charge, dont ~20 000 avec statut rafraichi en continu) ;
2. compare au dernier etat connu et enregistre **uniquement les changements**
   dans `donnees/evenements/AAAA/MM/*.csv.gz`
   (colonnes : `id_pdc_itinerance`, `etat_pdc`, `occupation_pdc`,
   `horodatage` opérateur, `horodatage_collecte`) ;
3. conserve une photo complete par jour (`donnees/instantanes/`) et une copie
   mensuelle du fichier statique (`donnees/statique/` : coordonnees GPS,
   puissance, enseigne, adresse — jointure par `id_pdc_itinerance`).

L'horodatage des evenements est celui de l'**operateur** : les heures de
changement de statut restent exactes meme si un passage de collecte saute.
Un trou de collecte n'est qu'un trou, rien ne se corrompt.

## Exploitation

L'empilement des evenements permet de reconstituer, par point de charge :
le taux d'occupation (part du temps « occupe », par heure et jour de
semaine), le taux de disponibilite technique (part du temps « hors_service »)
et une approximation du nombre et de la duree des sessions.

## Licence

Donnees sources sous [Licence Ouverte v2.0](https://www.etalab.gouv.fr/licence-ouverte-open-licence/)
(Etalab) — reutilisation libre avec mention de la source :
`transport.data.gouv.fr`. Ce depot republie ces donnees sans modification,
enrichies du seul horodatage de collecte.
