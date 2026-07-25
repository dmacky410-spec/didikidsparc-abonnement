#!/usr/bin/env python3
"""Pont RFID — lit les cartes MIFARE Classic 1K sur un lecteur ACR122U
et envoie l'UID au logiciel Didikids Parc.

Installation (une seule fois, sur le poste d'accueil) :
    pip install pyscard

Utilisation :
    python3 acr122u_bridge.py [--server http://localhost:8730] [--token JETON]

Le jeton s'affiche au démarrage de server.py (inutile si le pont tourne
sur le même ordinateur que le serveur).
"""
import argparse
import json
import sys
import time
import urllib.request

try:
    from smartcard.System import readers
    from smartcard.Exceptions import NoCardException, CardConnectionException
except ImportError:
    print("ERREUR : le module pyscard n'est pas installé.")
    print("Installez-le avec :  pip install pyscard")
    sys.exit(1)

GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]  # commande APDU standard PC/SC


def send_uid(server, token, uid):
    data = json.dumps({"uid": uid, "token": token}).encode()
    req = urllib.request.Request(
        server.rstrip("/") + "/api/scan", data=data,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status == 200


def find_reader():
    for r in readers():
        if "ACR122" in str(r) or "ACR 122" in str(r):
            return r
    rs = readers()
    return rs[0] if rs else None


def main():
    parser = argparse.ArgumentParser(description="Pont ACR122U → Didikids Parc")
    parser.add_argument("--server", default="http://localhost:8730")
    parser.add_argument("--token", default="")
    args = parser.parse_args()

    print("Pont RFID Didikids Parc — Ctrl+C pour arrêter")
    print(f"Serveur : {args.server}")

    last_uid, last_time = None, 0
    reader = None

    while True:
        try:
            if reader is None:
                reader = find_reader()
                if reader is None:
                    print("Aucun lecteur détecté… branchez l'ACR122U (nouvel essai dans 3 s)")
                    time.sleep(3)
                    continue
                print(f"Lecteur : {reader}")

            connection = reader.createConnection()
            try:
                connection.connect()
                data, sw1, sw2 = connection.transmit(GET_UID)
                if sw1 == 0x90:
                    uid = "".join(f"{b:02X}" for b in data)
                    now = time.time()
                    # anti-rebond : ignorer la même carte pendant 3 secondes
                    if uid != last_uid or now - last_time > 3:
                        last_uid, last_time = uid, now
                        try:
                            send_uid(args.server, args.token, uid)
                            print(f"[{time.strftime('%H:%M:%S')}] Carte lue : {uid} → envoyé")
                        except Exception as e:
                            print(f"Envoi impossible ({e}) — le serveur est-il lancé ?")
                connection.disconnect()
            except NoCardException:
                pass  # pas de carte posée : normal
            except CardConnectionException:
                pass  # carte retirée trop vite
            time.sleep(0.3)
        except KeyboardInterrupt:
            print("\nArrêt du pont RFID.")
            break
        except Exception as e:
            print(f"Erreur lecteur ({e}) — reconnexion…")
            reader = None
            time.sleep(2)


if __name__ == "__main__":
    main()
