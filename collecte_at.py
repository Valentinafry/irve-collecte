"""Collecteur AUTRICHE (Ladestellenverzeichnis E-Control) — photo quotidienne.

API publique du registre national autrichien (obligation AFIR / Ladepunkt-
Daten-Verordnung). Acces : cle API en en-tete `Apikey` (EN MINUSCULES — la
page d'accueil l'affiche en majuscules mais l'API la refuse ainsi) + en-tete
`Referer` du domaine declare a l'inscription.

Le flux groupe `/search/stations` (pagine par 1000) livre TOUT le parc :
~15 800 stations avec leurs points (evseId, kW, connecteurs) et les PRIX
structures (cent/kWh, frais de demarrage, frais de blocage) — une richesse
qu'aucun autre pays n'offre. En revanche il ne porte PAS le statut temps
reel (disponible uniquement au detail par station, ~15 800 requetes par
balayage : exclu sans accord — piste : flux DATEX II AFIR aupres de
support@ladestellen.at).

V1 : une photo complete PAR JOUR (16 requetes, ~0,5 s d'ecart) ->
historique du parc et des prix autrichiens. Cle dans
`cles/ladestellen_identifiants.txt` (gitignore) : la cle seule sur la
premiere ligne.
"""
from __future__ import annotations

import gzip
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

RACINE = Path(__file__).resolve().parent
CLE = RACINE / "cles" / "ladestellen_identifiants.txt"
DONNEES = RACINE / "donnees_at"
BASE = "https://api.e-control.at/charge/1.0"
REFERER = "https://afry.com"          # domaine declare a l'inscription
PAGE = 1000


def main() -> int:
    if not CLE.exists():
        print("autriche : cle absente "
              "(cles/ladestellen_identifiants.txt) — collecte sautee")
        return 0
    maintenant = datetime.now(timezone.utc)
    photo = DONNEES / "instantanes" / f"{maintenant:%Y-%m-%d}.json.gz"
    if photo.exists():
        return 0                       # une photo par jour suffit
    entetes = {"Apikey": CLE.read_text(encoding="utf-8").split()[0].lower(),
               "Referer": REFERER}
    stations = []
    idx = 0
    while True:
        try:
            r = requests.get(f"{BASE}/search/stations",
                             params={"fromIndex": idx},
                             headers=entetes, timeout=120)
            r.raise_for_status()
        except Exception as exc:                       # noqa: BLE001
            print(f"autriche : echec page {idx} ({exc}) — abandon du jour")
            return 0
        d = r.json()
        stations.extend(d.get("stations") or [])
        total = int(d.get("totalResults", 0))
        idx = int(d.get("endIndex", idx)) + 1
        if idx >= total or not d.get("stations"):
            break
        time.sleep(0.5)                # politesse
    photo.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(photo, "wt", encoding="utf-8") as fh:
        json.dump({"collecte": maintenant.isoformat(timespec="seconds"),
                   "total": len(stations), "stations": stations}, fh,
                  ensure_ascii=False)
    n_pts = sum(len(s.get("points") or []) for s in stations)
    print(f"autriche : photo du jour — {len(stations)} stations, "
          f"{n_pts} points ({photo.stat().st_size / 1e6:.1f} Mo)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
