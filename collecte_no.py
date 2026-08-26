"""Collecteur du REFERENTIEL NOBIL (Norvege + Suede) — datadump mensuel.

Necessite une cle API NOBIL (gratuite, formulaire sur nobil.no) deposee dans
`cles/nobil_apikey.txt` (dossier gitignore). Tant que la cle est absente, le
script ne fait rien (sortie 0) : il s'active tout seul des qu'elle est la.

Le datadump donne stations et points de charge (positions, puissances,
prises, operateurs) — PAS les statuts temps reel : ceux-ci arrivent par le
flux WebSocket d'Enova (voir ecoute_nobil.py). Ici : une copie mensuelle
par pays, comme le statique francais.

Donnees sous licence CC-BY (NOBIL / Enova) — mention de la source requise.
"""
from __future__ import annotations

import gzip
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

RACINE = Path(__file__).resolve().parent
CLE = RACINE / "cles" / "nobil_apikey.txt"
DONNEES = RACINE / "donnees_no"
PAYS = ["NOR", "SWE"]
URL = "https://nobil.no/api/server/datadump.php"


def main() -> int:
    if not CLE.exists():
        print("nobil : cle absente (cles/nobil_apikey.txt) — collecte sautee")
        return 0
    apikey = CLE.read_text(encoding="utf-8").strip()
    maintenant = datetime.now(timezone.utc)
    for pays in PAYS:
        dest = DONNEES / "statique" / f"{maintenant:%Y-%m}_{pays}.json.gz"
        if dest.exists():
            continue
        try:
            r = requests.get(URL, params={"apikey": apikey,
                                          "countrycode": pays,
                                          "format": "json"}, timeout=300)
            r.raise_for_status()
        except Exception as exc:                       # noqa: BLE001
            print(f"nobil {pays} : echec datadump ({exc})")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(dest, "wb") as fh:
            fh.write(r.content)
        print(f"nobil {pays} : datadump mensuel enregistre "
              f"({len(r.content) / 1e6:.1f} Mo)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
