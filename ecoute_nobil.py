"""Ecouteur du flux TEMPS REEL NOBIL (statuts des points nordiques).

Le temps reel NOBIL n'est pas un etat a sonder mais un FLUX WebSocket pousse
par la plateforme Enova (data.enova.no). Ce script est un service permanent
(systemd, voir README) :

  1. lit la cle d'abonnement Enova dans `cles/enova_subscription.txt`
     (gitignore) — produit « NOBIL Real-time » souscrit sur data.enova.no ;
  2. demande l'URL de connexion :
     GET https://data.enova.no/real-time/v1/Realtime
     (cle en en-tete Ocp-Apim-Subscription-Key) ;
  3. se connecte au WebSocket et AJOUTE chaque message recu, brut, dans
     donnees_no/evenements/AAAA/MM/AAAA-MM-JJ.jsonl.gz (une ligne JSON par
     evenement, horodatage de collecte ajoute). Le contrat exact du message
     (identifiant du point, statut, horodatage operateur) est conserve tel
     quel : l'aplatissement se fera a l'analyse.

Tant que la cle est absente, le script sort immediatement (code 0).
Reconnexion automatique avec attente progressive en cas de coupure.
"""
from __future__ import annotations

import gzip
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RACINE = Path(__file__).resolve().parent
CLE = RACINE / "cles" / "enova_subscription.txt"
CLE_NOBIL = RACINE / "cles" / "nobil_apikey.txt"
DONNEES = RACINE / "donnees_no" / "evenements"
URL_NEGO = "https://data.enova.no/real-time/v1/Realtime"


def url_flux(cle: str, cle_nobil: str) -> str:
    """Negociation constatee sur le portail Enova (08/2026) : POST avec la
    cle de souscription (Ocp-Apim-Subscription-Key) ET la cle API NOBIL
    (en-tete x-api-key). La reponse contient l'URL de connexion au flux."""
    import requests
    r = requests.post(URL_NEGO,
                      headers={"Ocp-Apim-Subscription-Key": cle,
                               "x-api-key": cle_nobil,
                               "Cache-Control": "no-cache"}, timeout=60)
    r.raise_for_status()
    d = r.json()
    for champ in ("url", "uri", "accessUrl", "webSocketUrl", "connectionUrl",
                  "wssUrl"):
        if isinstance(d, dict) and d.get(champ):
            return str(d[champ])
    raise RuntimeError(f"reponse inattendue de la negociation : {d}")


def ecrire(message: str) -> None:
    maintenant = datetime.now(timezone.utc)
    dest = (DONNEES / f"{maintenant:%Y}" / f"{maintenant:%m}"
            / f"{maintenant:%Y-%m-%d}.jsonl.gz")
    dest.parent.mkdir(parents=True, exist_ok=True)
    ligne = json.dumps({"recu": maintenant.isoformat(timespec="seconds"),
                        "message": json.loads(message)}, ensure_ascii=False)
    with gzip.open(dest, "at", encoding="utf-8") as fh:
        fh.write(ligne + "\n")


def main() -> int:
    if not CLE.exists() or not CLE_NOBIL.exists():
        print("nobil temps reel : cles absentes (cles/enova_subscription.txt "
              "et cles/nobil_apikey.txt requises) — ecoute sautee")
        return 0
    try:
        from websockets.sync.client import connect
    except ImportError:
        print("nobil temps reel : pip install websockets")
        return 1
    cle = CLE.read_text(encoding="utf-8").strip()
    cle_nobil = CLE_NOBIL.read_text(encoding="utf-8").strip()
    attente = 5
    while True:
        try:
            adresse = url_flux(cle, cle_nobil)
            print(f"connexion au flux : {adresse[:60]}...")
            with connect(adresse) as ws:
                attente = 5                      # connexion OK : raz du delai
                for message in ws:
                    ecrire(message)
        except KeyboardInterrupt:
            return 0
        except Exception as exc:                       # noqa: BLE001
            print(f"flux interrompu ({exc}) — reconnexion dans {attente} s")
            time.sleep(attente)
            attente = min(attente * 2, 300)


if __name__ == "__main__":
    sys.exit(main())
