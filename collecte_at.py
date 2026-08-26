"""Collecteur AUTRICHE (Ladestellenverzeichnis E-Control) — EN ATTENTE.

L'API du registre autrichien (ladestellen.at) est gratuite mais exige une
inscription (https://admin.ladestellen.at/#/api/registrieren) ; les
identifiants arrivent par e-mail et la documentation des endpoints n'est
accessible qu'apres inscription.

Ce script s'activera une fois les identifiants deposes dans
`cles/ladestellen_identifiants.txt` (gitignore) ET le script finalise avec
la documentation obtenue. D'ici la : sortie silencieuse (code 0), le cron
de la VM peut l'appeler sans risque.
"""
from __future__ import annotations

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent
CLE = RACINE / "cles" / "ladestellen_identifiants.txt"


def main() -> int:
    if not CLE.exists():
        print("autriche : identifiants absents "
              "(cles/ladestellen_identifiants.txt) — collecte sautee")
        return 0
    print("autriche : identifiants presents — script A FINALISER avec la "
          "documentation API obtenue apres inscription (support@ladestellen.at)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
