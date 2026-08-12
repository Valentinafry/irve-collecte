"""Collecteur de statuts IRVE dynamiques (transport.data.gouv.fr).

A chaque passage (GitHub Actions, ~5 min) : telecharge la consolidation
nationale dynamique, compare au dernier etat connu et n'enregistre QUE les
changements de statut (occupation ou etat de service). L'horodatage conserve
est celui de l'OPERATEUR : les heures de debut/fin de statut restent exactes
meme si la collecte est irreguliere. Une photo complete par jour (controle)
et une copie mensuelle du fichier statique (positions, puissances, enseignes).

Premier passage (aucun etat connu) : etat de reference seulement, pas
d'evenements — evite de compter 105 000 faux changements.

Donnees sous Licence Ouverte v2.0 (Etalab), source : Point d'Acces National
transport.data.gouv.fr.
"""
from __future__ import annotations

import gzip
import io
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

URL_DYN = ("https://proxy.transport.data.gouv.fr/resource/"
           "consolidation-nationale-irve-dynamique")
URL_STA = ("https://proxy.transport.data.gouv.fr/resource/"
           "consolidation-transport-irve-statique")
RACINE = Path(__file__).resolve().parent
ETAT = RACINE / "etat" / "etat_courant.csv.gz"
DONNEES = RACINE / "donnees"
COLS = ["id_pdc_itinerance", "etat_pdc", "occupation_pdc", "horodatage"]


def telecharger(url: str, essais: int = 3) -> bytes | None:
    for i in range(essais):
        try:
            r = requests.get(url, timeout=180)
            r.raise_for_status()
            return r.content
        except Exception as exc:                       # noqa: BLE001
            print(f"  essai {i + 1}/{essais} echoue : {exc}")
    return None


def main() -> int:
    maintenant = datetime.now(timezone.utc)
    brut = telecharger(URL_DYN)
    if brut is None:
        print("telechargement impossible — prochain passage dans 5 min")
        return 0

    df = pd.read_csv(io.BytesIO(brut), usecols=lambda c: c in COLS,
                     dtype=str)
    df["_h"] = pd.to_datetime(df["horodatage"], errors="coerce", utc=True,
                              format="mixed")
    df = (df.sort_values("_h").drop_duplicates("id_pdc_itinerance",
                                               keep="last")
            .drop(columns="_h"))
    for c in ["etat_pdc", "occupation_pdc"]:
        df[c] = df[c].fillna("absent")

    if ETAT.exists():
        etat = pd.read_csv(ETAT, dtype=str)
        fus = df.merge(etat[["id_pdc_itinerance", "etat_pdc",
                             "occupation_pdc"]],
                       on="id_pdc_itinerance", how="left",
                       suffixes=("", "_prec"))
        chg = ((fus["occupation_pdc"] != fus["occupation_pdc_prec"])
               | (fus["etat_pdc"] != fus["etat_pdc_prec"]))
        ev = fus.loc[chg, COLS].copy()
        ev["horodatage_collecte"] = maintenant.isoformat(timespec="seconds")
        if len(ev):
            dest = (DONNEES / "evenements" / f"{maintenant:%Y}"
                    / f"{maintenant:%m}"
                    / f"{maintenant:%Y-%m-%d_%H%M%S}.csv.gz")
            dest.parent.mkdir(parents=True, exist_ok=True)
            ev.to_csv(dest, index=False)
        print(f"{len(df)} points ; {len(ev)} changements enregistres")
    else:
        print(f"{len(df)} points ; premier passage : etat de reference "
              "seulement")

    ETAT.parent.mkdir(parents=True, exist_ok=True)
    df[COLS].to_csv(ETAT, index=False)

    photo = DONNEES / "instantanes" / f"{maintenant:%Y-%m-%d}.csv.gz"
    if not photo.exists():
        photo.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(photo, "wb") as fh:
            fh.write(brut)
        print("photo complete du jour enregistree")

    statique = DONNEES / "statique" / f"{maintenant:%Y-%m}.csv.gz"
    if not statique.exists():
        brut_sta = telecharger(URL_STA)
        if brut_sta is not None:
            statique.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(statique, "wb") as fh:
                fh.write(brut_sta)
            print("copie mensuelle du statique enregistree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
