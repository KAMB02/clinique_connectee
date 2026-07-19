#!/usr/bin/env python3
"""
════════════════════════════════════════════════════════════════════
  CLINIQUE CONNECTÉE — Simulateur v2.0
  7 chambres (5 hospitalisation + 2 soins intensifs)
  Auth MQTT username/password par device
  Remplace les 3 simulations Wokwi pour la démo live

  Usage :
    py simulateur_clinique_v2.py
    py simulateur_clinique_v2.py --broker localhost --port 8883
    py simulateur_clinique_v2.py --chambres 7
════════════════════════════════════════════════════════════════════
"""

import argparse
import random
import ssl
import time
import threading
import paho.mqtt.client as mqtt

parser = argparse.ArgumentParser(description="Simulateur Clinique Connectée v2")
parser.add_argument("--broker", default="localhost")
parser.add_argument("--port", type=int, default=8883)
parser.add_argument("--interval", type=int, default=10)
args = parser.parse_args()

BROKER   = args.broker
PORT     = args.port
INTERVAL = args.interval

# ──────────────────────────────────────────────────────────────────
# CREDENTIALS MQTT — un compte par device
# Doit correspondre à ce qui est configuré dans mosquitto.conf (passwordfile)
# ──────────────────────────────────────────────────────────────────
MQTT_CREDENTIALS = {
    "chambre":    {"username": "esp32_chambre",    "password": "clinique2026"},
    "securite":   {"username": "esp32_securite",   "password": "clinique2026"},
    "energie":    {"username": "esp32_energie",    "password": "clinique2026"},
    "controleur": {"username": "esp32_controleur", "password": "clinique2026"},
}

# ──────────────────────────────────────────────────────────────────
# 7 CHAMBRES : 5 hospitalisation (CH) + 2 soins intensifs (SI)
# ──────────────────────────────────────────────────────────────────
CHAMBRES_CONFIG = [
    {"id": "CH-001", "patient": "PAT-101", "service": "hospitalisation"},
    {"id": "CH-002", "patient": "PAT-102", "service": "hospitalisation"},
    {"id": "CH-003", "patient": "PAT-103", "service": "hospitalisation"},
    {"id": "CH-004", "patient": "PAT-104", "service": "hospitalisation"},
    {"id": "CH-005", "patient": "PAT-105", "service": "hospitalisation"},
    {"id": "SI-001", "patient": "PAT-201", "service": "soins_intensifs"},
    {"id": "SI-002", "patient": "PAT-202", "service": "soins_intensifs"},
]

print("════════════════════════════════════════════════════")
print("  CLINIQUE CONNECTÉE — Simulateur v2.0")
print(f"  Broker : {BROKER}:{PORT}")
print(f"  Chambres : {len(CHAMBRES_CONFIG)} (5 hospit + 2 soins intensifs)")
print(f"  Auth MQTT : activée (username/password)")
print(f"  Intervalle : {INTERVAL}s")
print("════════════════════════════════════════════════════\n")


def make_client(role: str) -> mqtt.Client:
    """Crée un client MQTT authentifié avec les credentials du rôle donné."""
    creds = MQTT_CREDENTIALS[role]
    c = mqtt.Client(
        client_id=f"clinique-{role}-{random.randint(1000,9999)}",
    )
    c.tls_set(ca_certs="certs/server.crt")
    # Certificat auto-signe : on desactive la verification du hostname
    # (comme le fait Telegraf avec insecure_skip_verify=true), sinon la
    # connexion echoue avec "Hostname mismatch" des que le hostname Docker
    # (clinique_mosquitto) ne correspond pas au CN/SAN du certificat.
    c.tls_insecure_set(True)
    c.username_pw_set(creds["username"], creds["password"])
    c.on_connect = lambda cl, ud, fl, rc: print(
        f"[MQTT] {role} connecté" if rc == 0 else f"[MQTT] {role} erreur rc={rc}"
    )
    c.connect(BROKER, PORT, keepalive=60)
    c.loop_start()
    return c


def randf(lo: float, hi: float) -> float:
    """
    Génère un nombre aléatoire uniforme dans l'intervalle [lo, hi].

    Args:
        lo: Borne inférieure (incluse).
        hi: Borne supérieure (incluse).

    Returns:
        float: Nombre aléatoire uniforme entre lo et hi.
    """
    return lo + random.random() * (hi - lo)
    
def gauss(mu, sigma, min_val=None, max_val=None):
    """Générateur gaussien avec bornes optionnelles"""
    val = random.gauss(mu, sigma)
    if min_val is not None:
        val = max(min_val, val)
    if max_val is not None:
        val = min(max_val, val)
    return val

def smooth_transition(current, target, alpha=0.3):
    """Lissage temporel : nouvelle valeur = alpha*cible + (1-alpha)*courante"""
    return alpha * target + (1 - alpha) * current
    return lo + random.random() * (hi - lo)


def now_ms():
    return int(time.time() * 1000)


def lp(measurement, tags: dict, fields: dict) -> str:
    """Construit une ligne InfluxDB Line Protocol."""
    tag_str = ",".join(f"{k}={v}" for k, v in tags.items())
    parts = []
    for k, v in fields.items():
        if isinstance(v, bool):
            parts.append(f"{k}={'true' if v else 'false'}")
        elif isinstance(v, str):
            parts.append(f'{k}="{v}"')
        elif isinstance(v, int):
            # Suffixe "i" obligatoire en Line Protocol pour les entiers,
            # sinon InfluxDB les interprete comme des float et rejette
            # l'ecriture si ce champ a deja ete vu comme integer ailleurs
            # (ex: firmware ESP32 d'origine, conflit de type par champ).
            parts.append(f"{k}={v}i")
        else:
            parts.append(f"{k}={v}")
    return f"{measurement},{tag_str} {','.join(parts)}"


# ──────────────────────────────────────────────────────────────────
# CHAMBRE PATIENT
# ──────────────────────────────────────────────────────────────────
class ChambrePatient:
    def __init__(self, cfg: dict, client: mqtt.Client):
        self.chambre_id  = cfg["id"]
        self.patient_id  = cfg["patient"]
        self.service     = cfg["service"]
        self.device_id   = f"ESP32_{cfg['id'].replace('-','')}"
        self.client      = client

        # Soins intensifs : seuils plus serrés, monitoring plus fréquent
        self.si = (self.service == "soins_intensifs")
        self.spo2_base   = 95.0 if self.si else 97.5
        self.ecg_base    = 76.0 if self.si else 72.0
        self.press_sys   = 125.0 if self.si else 120.0
        self.press_dia   = 82.0  if self.si else 80.0
        self.perf_niveau = 500.0
        self.perf_debit  = 50.0

        self.spo2_drift  = 0.0
        self.ecg_drift   = 0.0
        self.event_type  = 0
        self.event_ticks = 0

    def tick(self):
        # Dérive SpO2 / ECG
        self.spo2_drift = max(-2.0, min(2.0, self.spo2_drift + randf(-0.3, 0.3)))
        spo2 = self.spo2_base + self.spo2_drift + randf(-0.2, 0.2)
        self.ecg_drift = max(-8.0, min(8.0, self.ecg_drift + randf(-1.0, 1.0)))
        ecg  = self.ecg_base + self.ecg_drift + randf(-1.0, 1.0)
        temp = 36.5 + randf(-0.2, 0.3)

        # Événements cliniques (~3% par tick, plus fréquents en SI)
        prob = 0.05 if self.si else 0.03
        if self.event_type == 0 and random.random() < prob:
            roll = random.randint(0, 3)
            self.event_type  = [1, 2, 3, 4][roll]
            self.event_ticks = [3, 5, 4, 8][roll]

        if self.event_type == 1:    # chute
            spo2 -= randf(1.0, 3.0); ecg += randf(15.0, 30.0)
            self.event_ticks -= 1
            if self.event_ticks <= 0: self.event_type = 0
        elif self.event_type == 2:  # hypoxie
            spo2 -= randf(3.0, 8.0)
            self.event_ticks -= 1
            if self.event_ticks <= 0: self.event_type = 0
        elif self.event_type == 3:  # tachycardie
            ecg += randf(20.0, 50.0)
            self.event_ticks -= 1
            if self.event_ticks <= 0: self.event_type = 0

        spo2 = max(70.0, min(100.0, spo2))
        ecg  = max(30.0, min(200.0, ecg))
        sys_v = max(90.0, min(180.0, self.press_sys + randf(-5.0, 5.0)))
        dia_v = max(50.0, min(120.0, self.press_dia + randf(-3.0, 3.0)))

        mvt   = 1 if random.random() < 0.15 else 0
        chute = 1 if self.event_type == 1 else 0

        self.perf_niveau = max(0.0, self.perf_niveau - (self.perf_debit / 120.0) - randf(0.0, 0.2))
        debit  = self.perf_debit + randf(-2.0, 2.0)
        alarme = 1 if (self.perf_niveau < 50.0 or self.event_type == 4) else 0
        if self.event_type == 4:
            self.event_ticks -= 1
            if self.event_ticks <= 0: self.event_type = 0
        if self.perf_niveau <= 0.0: self.perf_niveau = 500.0

        co2 = 620.0 + randf(-50.0, 60.0) + (120.0 if self.event_type != 0 else 0.0)

        # Seuils d'alerte — plus stricts pour soins intensifs
        spo2_warn  = 93.0 if self.si else 94.0
        spo2_rouge = 88.0 if self.si else 90.0
        ecg_warn   = 110.0 if self.si else 120.0
        ecg_rouge  = 140.0 if self.si else 150.0

        priorite = "VERT"
        if spo2 < spo2_rouge or ecg > ecg_rouge or chute == 1 or alarme == 1:
            priorite = "ROUGE"
        elif spo2 < spo2_warn or ecg > ecg_warn or temp > 38.5:
            priorite = "ORANGE"
        alerte = priorite != "VERT"

        tags = {
            "chambre_id": self.chambre_id,
            "patient_id": self.patient_id,
            "device_id":  self.device_id,
            "service":    self.service,
        }
        topic_base = f"clinique/chambre/{self.chambre_id}"

        # vitaux_chambre
        self.client.publish(f"{topic_base}/vitaux", lp("vitaux_chambre", tags, {
            "spo2": round(spo2, 1), "ecg_bpm": round(ecg, 1), "temperature": round(temp, 1),
            "pression_sys": round(sys_v, 1), "pression_dia": round(dia_v, 1),
            "alerte_active": alerte, "timestamp_esp": now_ms()
        }))
        # co2_ambiant
        self.client.publish(f"{topic_base}/co2", lp("co2_ambiant",
            {"chambre_id": self.chambre_id, "device_id": self.device_id, "service": self.service},
            {"co2_ppm": round(co2, 1), "timestamp_esp": now_ms()}))
        # mouvement
        self.client.publish(f"{topic_base}/mouvement", lp("mouvement", tags,
            {"mouvement": mvt, "chute_detectee": chute, "timestamp_esp": now_ms()}))
        # perfuseur
        self.client.publish(f"{topic_base}/perfuseur", lp("perfuseur",
            {"chambre_id": self.chambre_id, "patient_id": self.patient_id,
             "perfuseur_id": f"PERF-{self.chambre_id}", "service": self.service},
            {"debit_ml_h": round(debit, 1), "niveau_poche_ml": round(self.perf_niveau, 1),
             "alarme": alarme, "timestamp_esp": now_ms()}))

        svc = "SI" if self.si else "CH"
        print(f"[{self.chambre_id}|{self.patient_id}|{svc}] "
              f"SpO2={spo2:.1f}% ECG={ecg:.0f}bpm T={temp:.1f}C → {priorite}")

        # Appel patient aléatoire (~2% par tick)
        if random.random() < 0.02:
            duree = random.randint(200, 4500)
            if duree >= 3000:
                self.client.publish(f"{topic_base}/appel_securite", lp("appel_securite",
                    {"chambre_id": self.chambre_id, "patient_id": self.patient_id,
                     "type": "securite", "priorite": "ROUGE"},
                    {"duree_ms": duree, "timestamp": now_ms()}))
                print(f"  >> [{self.chambre_id}] APPEL SECURITE ({duree}ms)")
            else:
                self.client.publish(f"{topic_base}/appel", lp("appel",
                    {"chambre_id": self.chambre_id, "patient_id": self.patient_id,
                     "type": "medical", "priorite": "ORANGE"},
                    {"duree_ms": duree, "timestamp": now_ms()}))
                print(f"  >> [{self.chambre_id}] APPEL MEDICAL ({duree}ms)")


# ──────────────────────────────────────────────────────────────────
# SÉCURITÉ
# ──────────────────────────────────────────────────────────────────
class Securite:
    BADGES_OK = ["BADGE-MED-001","BADGE-MED-002","BADGE-INF-007",
                 "BADGE-INF-008","BADGE-TECH-003","BADGE-CTRL-001"]
    BADGES_KO = ["BADGE-INCONNU-999","BADGE-EXPIRE-042","BADGE-VISITE-????"]

    def __init__(self, client: mqtt.Client):
        self.client      = client
        self.zone_id     = "couloir-B"
        self.device_id   = "ESP32_SECU"
        self.secu_event  = 0
        self.secu_ticks  = 0

    def _publish_alerte_rep(self, event_type: str, priorite: str, details: dict):
        payload = lp("alerte_rep",
            {"zone": self.zone_id, "device_id": self.device_id,
             "type": event_type, "priorite": priorite},
            {**details, "handled": True, "timestamp_esp": now_ms()})
        self.client.publish("clinique/alerte/rep", payload)
        print(f"  >> REPONSE ALERTE publiée sur clinique/alerte/rep ({event_type})")

    def pub_badge(self, intrusion: bool):
        autorise = not intrusion
        badge_id = random.choice(self.BADGES_KO if intrusion else self.BADGES_OK)
        self.client.publish(f"clinique/acces/{self.zone_id}/badge", lp("badge_acces",
            {"zone": self.zone_id, "device_id": self.device_id},
            {"badge_id": badge_id, "autorise": autorise, "timestamp_esp": now_ms()}))
        print(f"[BADGE] {badge_id} → {'OK' if autorise else 'REFUSE'}")
        if not autorise:
            self.client.publish("clinique/alerte/controleur", lp("alerte_controleur",
                {"zone": self.zone_id, "type": "intrusion_badge",
                 "device_id": self.device_id, "priorite": "ROUGE"},
                {"badge_id": badge_id, "autorise": False, "timestamp_esp": now_ms()}))
            self._publish_alerte_rep("intrusion_badge", "ROUGE", {
                "badge_id": badge_id,
                "autorise": False,
                "reponse": "prise_en_charge"
            })
            print("  >> ALERTE INTRUSION BADGE")

    def pub_camera(self, intrusion: bool):
        conf = randf(82.0, 99.0) if intrusion else randf(0.0, 15.0)
        self.client.publish(f"clinique/securite/{self.zone_id}/camera", lp("camera_intrusion",
            {"zone": self.zone_id, "camera_id": f"CAM-{self.zone_id}", "device_id": self.device_id},
            {"intrusion_ia": intrusion, "mouvement_detecte": intrusion,
             "confiance_pct": round(conf, 1), "timestamp_esp": now_ms()}))
        if intrusion:
            self.client.publish("clinique/alerte/controleur", lp("alerte_controleur",
                {"zone": self.zone_id, "type": "intrusion_camera",
                 "device_id": self.device_id, "priorite": "ROUGE"},
                {"confiance_pct": round(randf(82.0, 99.0), 1), "timestamp_esp": now_ms()}))
            self._publish_alerte_rep("intrusion_camera", "ROUGE", {
                "confiance_pct": round(randf(82.0, 99.0), 1),
                "reponse": "prise_en_charge"
            })
            print(f"[CAMERA] INTRUSION -- zone={self.zone_id}")
        else:
            print(f"[CAMERA] OK -- zone={self.zone_id}")

    def pub_porte(self, ouverte: bool):
        self.client.publish(f"clinique/acces/{self.zone_id}/porte", lp("securite_acces",
            {"zone": self.zone_id, "capteur_id": f"PORTE-{self.zone_id}", "device_id": self.device_id},
            {"porte_ouverte": ouverte,
             "duree_ouverte_ms": 0 if ouverte else random.randint(2000, 8000),
             "timestamp_esp": now_ms()}))

    def tick(self):
        if random.random() < 0.10:
            self.pub_porte(True)
            time.sleep(0.05)
            self.pub_badge(random.random() < 0.20)
            time.sleep(0.05)
            self.pub_porte(False)

        if self.secu_event == 0 and random.random() < 0.10:
            roll = random.randint(0, 2)
            self.secu_event, self.secu_ticks = [(1,2),(2,1),(3,3)][roll]

        if self.secu_event == 1:
            self.pub_camera(True)
            self.secu_ticks -= 1
            if self.secu_ticks <= 0: self.secu_event = 0
        elif self.secu_event == 2:
            self.pub_badge(True)
            self.secu_ticks -= 1
            if self.secu_ticks <= 0: self.secu_event = 0
        elif self.secu_event == 3:
            self.pub_camera(False); self.pub_badge(False)
            self.secu_ticks -= 1
            if self.secu_ticks <= 0: self.secu_event = 0
        else:
            self.pub_camera(False)


# ──────────────────────────────────────────────────────────────────
# ÉNERGIE
# ──────────────────────────────────────────────────────────────────
class Energie:
    def __init__(self, client: mqtt.Client):
        self.client      = client
        self.device_id   = "ESP32_ENERGIE"
        self.niveau_ups  = 85.0
        self.tension     = 220.0
        self.source      = "SECTEUR"
        self.gen_actif   = False
        self.gen_charge  = 0.0
        self.pub_count   = 0

    def tick(self):
        self.pub_count += 1
        panne = (self.pub_count % 20 == 0)
        if panne:
            self.source = "UPS" if self.niveau_ups > 10 else "GENERATEUR"
            if self.source == "GENERATEUR": self.gen_actif = True
        elif self.pub_count % 20 < 5 and self.source != "SECTEUR":
            self.source = "SECTEUR"; self.gen_actif = False

        if self.source != "SECTEUR":
            self.niveau_ups = max(0.0, self.niveau_ups - randf(0.5, 1.5))
        else:
            self.niveau_ups = min(100.0, self.niveau_ups + randf(0.1, 0.5))

        self.tension = 220.0 + randf(-8.0, 8.0)
        if self.gen_actif:
            self.gen_charge = min(100.0, self.gen_charge + randf(2.0, 5.0))
        else:
            self.gen_charge = max(0.0, self.gen_charge - randf(1.0, 3.0))

        autonomie = (self.niveau_ups / 100.0) * 45.0
        tags = {"device_id": self.device_id}

        self.client.publish("clinique/energie/ups", lp("energie_ups", tags, {
            "statut": self.source, "niveau_pct": round(self.niveau_ups, 1),
            "autonomie_min": round(autonomie, 1), "en_charge": (self.source == "SECTEUR"),
            "tension_v": round(self.tension, 1), "timestamp_esp": now_ms()
        }))
        self.client.publish("clinique/energie/generateur", lp("energie_generateur", tags, {
            "actif": self.gen_actif, "charge_pct": round(self.gen_charge, 1),
            "statut": "ON" if self.gen_actif else "OFF", "timestamp_esp": now_ms()
        }))
        for circuit, base in [("BLOC-A", 1200), ("BLOC-B", 800), ("URGENCE", 2600)]:
            conso = base + randf(-150, 200)
            self.client.publish(f"clinique/energie/compteur/{circuit}", lp("energie_compteur",
                {"device_id": self.device_id, "circuit": circuit},
                {"consommation_w": round(conso, 1), "timestamp_esp": now_ms()}))

        print(f"[ENERGIE] {self.source} UPS={self.niveau_ups:.0f}% "
              f"Gen={'ON' if self.gen_actif else 'OFF'} V={self.tension:.0f}V")


# ──────────────────────────────────────────────────────────────────
# BOUCLE PRINCIPALE
# ──────────────────────────────────────────────────────────────────
def run_chambre(ch):
    time.sleep(random.uniform(0, 2))  # décalage pour éviter les rafales simultanées
    while True:
        ch.tick()
        interval = INTERVAL // 2 if ch.si else INTERVAL  # SI publie 2x plus vite
        time.sleep(interval)

def run_securite(s):
    while True:
        s.tick()
        time.sleep(INTERVAL + 5)

def run_energie(e):
    while True:
        e.tick()
        time.sleep(INTERVAL + 5)

def main():
    # Clients MQTT séparés par rôle (auth différente si besoin)
    client_ch   = make_client("chambre")
    client_secu = make_client("securite")
    client_ener = make_client("energie")
    time.sleep(1.5)  # laisser les connexions s'établir

    chambres  = [ChambrePatient(cfg, client_ch) for cfg in CHAMBRES_CONFIG]
    securite  = Securite(client_secu)
    energie   = Energie(client_ener)

    threads = [threading.Thread(target=run_chambre,   args=(ch,), daemon=True) for ch in chambres]
    threads.append(threading.Thread(target=run_securite, args=(securite,), daemon=True))
    threads.append(threading.Thread(target=run_energie,  args=(energie,),  daemon=True))

    for t in threads: t.start()

    print(f"\n[SIMULATEUR] 7 chambres (5 hospit + 2 SI) + sécurité + énergie — DÉMARRÉ")
    print("[SIMULATEUR] Auth MQTT activée — credentials par device\n")

    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SIMULATEUR] Arrêt")
        for c in [client_ch, client_secu, client_ener]:
            c.loop_stop(); c.disconnect()

if __name__ == "__main__":
    main()