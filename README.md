# Collecte IRVE dynamique

Historisation des statuts temps reel des points de charge publics francais
(libre / occupe / hors service), a partir de la consolidation nationale du
Point d'Acces National [transport.data.gouv.fr](https://transport.data.gouv.fr).
Ces statuts sont publies en continu mais **aucun historique national n'est
conserve** : ce depot l'enregistre.

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
