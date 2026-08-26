"""Collecteur ALLEMAGNE (Ladesaeulenregister BNetzA) — registre par millesime.

Le registre federal allemand (~210 000 points : positions, puissances,
operateurs, dates de mise en service) est publie en CSV sous licence
CC-BY 4.0 (attribution : Bundesnetzagentur.de), sous un nom de fichier
DATE (ex. Ladesaeulenregister_BNetzA_2026-07-28.csv), renouvele
periodiquement. Pas de statut temps reel ici : le dynamique allemand passe
par Mobilithek (compte + abonnements par operateur, DATEX II) — voir README.

Ce script verifie UNE FOIS PAR JOUR la page de la Ladesaeulenkarte, extrait
l'URL du millesime courant et ne telecharge que s'il est nouveau
(~51 Mo -> ~10 Mo gzip). Aucune cle requise.
"""
from __future__ import annotations

import gzip
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

RACINE = Path(__file__).resolve().parent
DONNEES = RACINE / "donnees_de" / "registre"
MARQUE = RACINE / "etat" / "verif_registre_de.txt"
PAGE = ("https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/"
        "E-Mobilitaet/Ladesaeulenkarte/start.html")
MOTIF = re.compile(
    r"https://data\.bundesnetzagentur\.de/[^\"'\s]*"
    r"Ladesaeulenregister[^\"'\s]*\d{4}-\d{2}-\d{2}\.csv")


def main() -> int:
    aujourdhui = f"{datetime.now(timezone.utc):%Y-%m-%d}"
    if MARQUE.exists() and MARQUE.read_text() == aujourdhui:
        return 0                       # une verification par jour suffit
    try:
        page = requests.get(PAGE, timeout=60,
                            headers={"User-Agent": "AFRY-collecte/1.0"}).text
    except Exception as exc:                           # noqa: BLE001
        print(f"allemagne : page indisponible ({exc})")
        return 0
    m = MOTIF.search(page)
    if not m:
        print("allemagne : lien du registre introuvable sur la page")
        return 0
    url = m.group(0)
    nom = url.rsplit("/", 1)[-1]
    dest = DONNEES / f"{nom}.gz"
    MARQUE.parent.mkdir(parents=True, exist_ok=True)
    MARQUE.write_text(aujourdhui)
    if dest.exists():
        return 0                       # millesime deja archive
    try:
        r = requests.get(url, timeout=600,
                         headers={"User-Agent": "AFRY-collecte/1.0"})
        r.raise_for_status()
    except Exception as exc:                           # noqa: BLE001
        print(f"allemagne : echec du telechargement ({exc})")
        return 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(dest, "wb") as fh:
        fh.write(r.content)
    print(f"allemagne : nouveau millesime archive — {nom} "
          f"({len(r.content) / 1e6:.0f} Mo -> {dest.stat().st_size / 1e6:.0f} "
          "Mo gzip)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
