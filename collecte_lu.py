"""Collecteur LUXEMBOURG (reseau Chargy) — occupation par station.

KML officiel publie sur data.public.lu (« Bornes de chargement publiques
pour voitures electriques »), rafraichi ~5 min, avec pour chaque station le
nombre de connecteurs TOTAL / DISPONIBLES / OCCUPES. La cle API figurant
dans l'URL est PUBLIQUE : c'est celle publiee par Chargy sur le portail
open data officiel — pas un secret.

ATTENTION : l'endpoint limite la cadence (429 constate a ~3 appels en
2 minutes) — un appel par cycle de 10 minutes passe, ne pas multiplier
les essais rapproches.

A chaque passage : telecharge le KML, extrait les comptes par station,
n'enregistre que les stations dont les comptes ont change. L'occupation se
mesure ici PAR STATION (x occupes sur n), pas par point individuel — assez
pour des taux d'occupation exacts par station. Pas d'horodatage operateur :
precision = cadence de collecte (~10 min). Copie mensuelle du KML brut.
"""
from __future__ import annotations

import gzip
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

import pandas as pd
import requests

RACINE = Path(__file__).resolve().parent
ETAT = RACINE / "etat" / "etat_courant_lu.csv.gz"
DONNEES = RACINE / "donnees_lu"
URL = ("https://my.chargy.lu/b2bev-external-services/resources/kml"
       "?API-KEY=486ac6e4-93b8-4369-9c6a-28f7c4e1a81f")   # cle publique
NS = "{http://www.opengis.net/kml/2.2}"
COLS = ["station", "lat", "lon", "total", "disponibles", "occupes"]


def aplatir(brut: bytes) -> pd.DataFrame:
    racine = ElementTree.fromstring(brut)
    lignes = []
    for pm in racine.iter(f"{NS}Placemark"):
        nom = (pm.findtext(f"{NS}name") or "?").strip()
        desc = pm.findtext(f"{NS}description") or ""
        coord = pm.findtext(f".//{NS}coordinates") or ","
        lon, lat = (coord.strip().split(",") + ["", ""])[:2]
        total = sum(int(x) for x in
                    re.findall(r"<b>(\d+)</b>\s*connectors with", desc))
        dispo = sum(int(x) for x in
                    re.findall(r"<b>(\d+)</b>\s*available connectors", desc))
        occ = sum(int(x) for x in
                  re.findall(r"<b>(\d+)</b>\s*occupied connectors", desc))
        lignes.append((nom, lat, lon, total, dispo, occ))
    df = pd.DataFrame(lignes, columns=COLS)
    return df.drop_duplicates("station", keep="last")


def main() -> int:
    maintenant = datetime.now(timezone.utc)
    try:
        r = requests.get(URL, timeout=120)
        r.raise_for_status()
    except Exception as exc:                           # noqa: BLE001
        print(f"luxembourg : telechargement impossible ({exc})")
        return 0
    # le KML encode la description en HTML echappe : on la desechappe
    brut = r.content.replace(b"&lt;", b"<").replace(b"&gt;", b">")
    try:
        df = aplatir(r.content)
    except ElementTree.ParseError:
        print("luxembourg : KML illisible ce passage")
        return 0
    if df["total"].sum() == 0:          # descriptions echappees : re-essai
        df = aplatir(brut)

    if ETAT.exists():
        etat = pd.read_csv(ETAT, dtype=str)
        fus = df.astype(str).merge(etat, on="station", how="left",
                                   suffixes=("", "_prec"))
        chg = ((fus["disponibles"] != fus["disponibles_prec"])
               | (fus["occupes"] != fus["occupes_prec"]))
        ev = fus.loc[chg, COLS].copy()
        ev["horodatage_collecte"] = maintenant.isoformat(timespec="seconds")
        if len(ev):
            dest = (DONNEES / "evenements" / f"{maintenant:%Y}"
                    / f"{maintenant:%m}"
                    / f"{maintenant:%Y-%m-%d_%H%M%S}.csv.gz")
            dest.parent.mkdir(parents=True, exist_ok=True)
            ev.to_csv(dest, index=False)
        print(f"luxembourg : {len(df)} stations ; {len(ev)} changements")
    else:
        print(f"luxembourg : {len(df)} stations ; premier passage (reference)")

    ETAT.parent.mkdir(parents=True, exist_ok=True)
    df.astype(str).to_csv(ETAT, index=False)

    photo = DONNEES / "instantanes" / f"{maintenant:%Y-%m-%d}.csv.gz"
    if not photo.exists():
        photo.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(photo, index=False)

    mensuel = DONNEES / "statique" / f"{maintenant:%Y-%m}.kml.gz"
    if not mensuel.exists():
        mensuel.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(mensuel, "wb") as fh:
            fh.write(r.content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
