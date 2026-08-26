"""Collecteur de statuts des points de charge NEERLANDAIS (DOT-NL / NDW).

Source : dump national OCPI 2.2.1 du Point d'Acces National neerlandais
(opendata.ndw.nu — gratuit, sans cle ni inscription, obligation AFIR
art. 20 : statuts rafraichis a la minute cote operateurs).

Meme architecture que collecte.py (France) : a chaque passage, telecharge le
dump complet (~80 000 stations, ~200 000 EVSE), aplatit les statuts EVSE,
compare au dernier etat connu et n'enregistre QUE les changements. Le
`last_updated` OCPI conserve est celui de l'OPERATEUR : les heures de debut
et fin de statut restent exactes meme si la collecte est irreguliere.
Photo quotidienne aplatie (tous les EVSE) et copie mensuelle du dump OCPI
complet (positions, puissances par connecteur, operateurs) + des tarifs.

Premier passage (aucun etat connu) : etat de reference seulement, pas
d'evenements.

Statuts OCPI : AVAILABLE, CHARGING, BLOCKED, RESERVED, OUTOFORDER,
INOPERATIVE, PLANNED, REMOVED, UNKNOWN. L'« occupation » au sens francais
(borne prise) correspond a CHARGING + BLOCKED (+ RESERVED selon lecture) —
le filtrage se fait a l'analyse, la collecte garde tout.
"""
from __future__ import annotations

import gzip
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

URL_OCPI = "https://opendata.ndw.nu/charging_point_locations_ocpi.json.gz"
URL_TARIFS = "https://opendata.ndw.nu/charging_point_tariffs_ocpi.json.gz"
RACINE = Path(os.environ.get("COLLECTE_NL_RACINE",
                             Path(__file__).resolve().parent))
ETAT = RACINE / "etat" / "etat_courant_nl.csv.gz"
DONNEES = RACINE / "donnees_nl"
COLS = ["evse_id", "statut", "last_updated"]


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
    """Dump OCPI -> une ligne par EVSE : evse_id, statut, last_updated."""
    locations = json.loads(gzip.decompress(brut))
    lignes = []
    for loc in locations:
        for evse in loc.get("evses") or []:
            eid = evse.get("evse_id") or evse.get("uid")
            if not eid:
                continue
            lignes.append((str(eid), str(evse.get("status", "UNKNOWN")),
                           str(evse.get("last_updated", ""))))
    df = pd.DataFrame(lignes, columns=COLS)
    # doublons d'evse_id entre stations : on garde le last_updated le plus
    # recent (comparaison lexicale suffisante sur des ISO 8601 UTC)
    df = (df.sort_values("last_updated")
            .drop_duplicates("evse_id", keep="last"))
    return df


def main() -> int:
    maintenant = datetime.now(timezone.utc)
    brut = telecharger(URL_OCPI)
    if brut is None:
        print("telechargement impossible — prochain passage dans 10 min")
        return 0
    df = aplatir(brut)

    if ETAT.exists():
        etat = pd.read_csv(ETAT, dtype=str)
        fus = df.merge(etat[["evse_id", "statut"]], on="evse_id",
                       how="left", suffixes=("", "_prec"))
        chg = fus["statut"] != fus["statut_prec"]
        ev = fus.loc[chg, COLS].copy()
        ev["horodatage_collecte"] = maintenant.isoformat(timespec="seconds")
        if len(ev):
            dest = (DONNEES / "evenements" / f"{maintenant:%Y}"
                    / f"{maintenant:%m}"
                    / f"{maintenant:%Y-%m-%d_%H%M%S}.csv.gz")
            dest.parent.mkdir(parents=True, exist_ok=True)
            ev.to_csv(dest, index=False)
        print(f"{len(df)} EVSE ; {len(ev)} changements enregistres")
    else:
        print(f"{len(df)} EVSE ; premier passage : etat de reference "
              "seulement")

    ETAT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ETAT, index=False)

    photo = DONNEES / "instantanes" / f"{maintenant:%Y-%m-%d}.csv.gz"
    if not photo.exists():
        photo.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(photo, index=False)
        print("photo complete du jour enregistree")

    statique = DONNEES / "statique" / f"{maintenant:%Y-%m}_locations.json.gz"
    if not statique.exists():
        statique.parent.mkdir(parents=True, exist_ok=True)
        statique.write_bytes(brut)
        brut_t = telecharger(URL_TARIFS)
        if brut_t is not None:
            (DONNEES / "statique"
             / f"{maintenant:%Y-%m}_tariffs.json.gz").write_bytes(brut_t)
        print("copie mensuelle du dump OCPI (locations + tarifs) enregistree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
