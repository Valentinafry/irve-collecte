"""Collecteur SUISSE (ich-tanke-strom / DIEMO, Office federal de l'energie).

Deux JSON federaux ouverts, sans cle, mis a jour en continu
(data.geo.admin.ch, infrastructure DIEMO) :
  - statuts : EVSEStatusRecord (EvseID + statut Available/Occupied/...) ;
  - statique : EVSEData (positions, puissances, operateurs).

Meme architecture que la France : a chaque passage, telecharge les statuts,
compare au dernier etat connu, n'enregistre QUE les changements.
Particularite : les statuts suisses ne portent PAS d'horodatage operateur —
l'heure de changement n'est donc connue qu'a la cadence de collecte pres
(~10 min), contrairement a la France et aux Pays-Bas. Photo quotidienne
aplatie et copie mensuelle du fichier statique.

Donnees ouvertes de la Confederation (open data, attribution BFE/DIEMO).
"""
from __future__ import annotations

import gzip
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

RACINE = Path(__file__).resolve().parent
ETAT = RACINE / "etat" / "etat_courant_ch.csv.gz"
DONNEES = RACINE / "donnees_ch"
URL_STATUTS = ("https://data.geo.admin.ch/ch.bfe.ladestellen-elektromobilitaet"
               "/status/ch.bfe.ladestellen-elektromobilitaet.json")
URL_STATIQUE = ("https://data.geo.admin.ch/ch.bfe.ladestellen-elektromobilitaet"
                "/data/ch.bfe.ladestellen-elektromobilitaet.json")
COLS = ["evse_id", "statut"]


def telecharger(url: str, essais: int = 3) -> bytes | None:
    for i in range(essais):
        try:
            r = requests.get(url, timeout=180)
            r.raise_for_status()
            return r.content
        except Exception as exc:                       # noqa: BLE001
            print(f"  essai {i + 1}/{essais} echoue : {exc}")
    return None


def aplatir(brut: bytes) -> pd.DataFrame:
    """Collecte recursive des EVSEStatusRecord, ou qu'ils soient."""
    lignes = []

    def parcourir(o) -> None:
        if isinstance(o, dict):
            for rec in o.get("EVSEStatusRecord") or []:
                eid = (rec.get("EvseID") or rec.get("EvseId")
                       or rec.get("evseId"))
                if eid:
                    lignes.append((str(eid),
                                   str(rec.get("EVSEStatus", "Unknown"))))
            for v in o.values():
                if isinstance(v, (dict, list)):
                    parcourir(v)
        elif isinstance(o, list):
            for v in o:
                parcourir(v)

    parcourir(json.loads(brut))
    return (pd.DataFrame(lignes, columns=COLS)
            .drop_duplicates("evse_id", keep="last"))


def main() -> int:
    maintenant = datetime.now(timezone.utc)
    brut = telecharger(URL_STATUTS)
    if brut is None:
        print("suisse : telechargement impossible — prochain passage")
        return 0
    df = aplatir(brut)

    if ETAT.exists():
        etat = pd.read_csv(ETAT, dtype=str)
        fus = df.merge(etat, on="evse_id", how="left", suffixes=("", "_prec"))
        chg = fus["statut"] != fus["statut_prec"]
        ev = fus.loc[chg, COLS].copy()
        ev["horodatage_collecte"] = maintenant.isoformat(timespec="seconds")
        if len(ev):
            dest = (DONNEES / "evenements" / f"{maintenant:%Y}"
                    / f"{maintenant:%m}"
                    / f"{maintenant:%Y-%m-%d_%H%M%S}.csv.gz")
            dest.parent.mkdir(parents=True, exist_ok=True)
            ev.to_csv(dest, index=False)
        print(f"suisse : {len(df)} EVSE ; {len(ev)} changements")
    else:
        print(f"suisse : {len(df)} EVSE ; premier passage (reference)")

    ETAT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ETAT, index=False)

    photo = DONNEES / "instantanes" / f"{maintenant:%Y-%m-%d}.csv.gz"
    if not photo.exists():
        photo.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(photo, index=False)

    statique = DONNEES / "statique" / f"{maintenant:%Y-%m}.json.gz"
    if not statique.exists():
        brut_s = telecharger(URL_STATIQUE)
        if brut_s is not None:
            statique.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(statique, "wb") as fh:
                fh.write(brut_s)
            print("suisse : copie mensuelle du statique enregistree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
