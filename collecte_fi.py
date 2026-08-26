"""Collecteur FINLANDE (Fintraffic / Digitraffic, API AFIR).

API publique ouverte, sans cle (afir.digitraffic.fi) : statuts temps reel
des EVSE (AVAILABLE / CHARGING / OUTOFORDER...), snapshots regeneres a la
minute cote source. Meme architecture que la France : a chaque passage,
recupere tous les statuts (pagination par curseur, 500/page), compare au
dernier etat connu et n'enregistre QUE les changements. Le `lastUpdatedAt`
conserve est l'horodatage de l'OPERATEUR : les heures de changement restent
exactes meme si la collecte saute. Copie mensuelle des locations (GeoJSON,
positions/puissances/operateurs) et des tarifs.

Donnees ouvertes Fintraffic (licence CC-BY 4.0, attribution Fintraffic /
Digitraffic).
"""
from __future__ import annotations

import gzip
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

RACINE = Path(__file__).resolve().parent
ETAT = RACINE / "etat" / "etat_courant_fi.csv.gz"
DONNEES = RACINE / "donnees_fi"
BASE = "https://afir.digitraffic.fi/api/charging-network/v1"
COLS = ["evse_id", "statut", "last_updated"]
H = {"User-Agent": "AFRY-collecte/1.0", "Accept": "application/json"}


def telecharger(url: str, params: dict | None = None,
                essais: int = 3) -> dict | None:
    for i in range(essais):
        try:
            r = requests.get(url, params=params, headers=H, timeout=120)
            r.raise_for_status()
            return r.json()
        except Exception as exc:                       # noqa: BLE001
            print(f"  essai {i + 1}/{essais} echoue : {exc}")
    return None


def tous_les_statuts() -> pd.DataFrame:
    """Parcourt toutes les pages (curseur) -> une ligne par EVSE."""
    lignes, curseur = [], None
    while True:
        d = telecharger(f"{BASE}/locations/statuses",
                        {"cursor": curseur} if curseur else None)
        if d is None:
            break
        for s in d.get("statuses") or []:
            eid = s.get("evseId")
            if eid:
                lignes.append((str(eid), str(s.get("status", "UNKNOWN")),
                               str(s.get("lastUpdatedAt", ""))))
        curseur = (d.get("pagination") or {}).get("nextCursor")
        if not curseur:
            break
    return (pd.DataFrame(lignes, columns=COLS)
            .drop_duplicates("evse_id", keep="last"))


def main() -> int:
    maintenant = datetime.now(timezone.utc)
    df = tous_les_statuts()
    if df.empty:
        print("finlande : aucun statut recupere — prochain passage")
        return 0

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
        print(f"finlande : {len(df)} EVSE ; {len(ev)} changements")
    else:
        print(f"finlande : {len(df)} EVSE ; premier passage (reference)")

    ETAT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ETAT, index=False)

    photo = DONNEES / "instantanes" / f"{maintenant:%Y-%m-%d}.csv.gz"
    if not photo.exists():
        photo.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(photo, index=False)

    mensuel = DONNEES / "statique" / f"{maintenant:%Y-%m}_locations.geojson.gz"
    if not mensuel.exists():
        loc, curseur = [], None
        while True:
            d = telecharger(f"{BASE}/locations",
                            {"cursor": curseur} if curseur else None)
            if d is None:
                break
            loc.extend(d.get("features") or [])
            curseur = (d.get("pagination") or {}).get("nextCursor")
            if not curseur:
                break
        if loc:
            import json
            mensuel.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(mensuel, "wt", encoding="utf-8") as fh:
                json.dump({"type": "FeatureCollection", "features": loc}, fh,
                          ensure_ascii=False)
            tar = telecharger(f"{BASE}/tariffs")
            if tar is not None:
                with gzip.open(DONNEES / "statique"
                               / f"{maintenant:%Y-%m}_tariffs.json.gz",
                               "wt", encoding="utf-8") as fh:
                    import json as _json
                    _json.dump(tar, fh, ensure_ascii=False)
            print(f"finlande : copie mensuelle ({len(loc)} locations + tarifs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
