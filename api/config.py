"""
config.py — Variables d'environnement centralisées
"""
import os

# ── Instance ──────────────────────────────────────────
INSTANCE_ID = os.getenv("INSTANCE_ID", "1")

# ── JWT ───────────────────────────────────────────────
JWT_SECRET      = os.getenv("JWT_SECRET", "clinique_jwt_secret_tres_securise_2025")
JWT_ALGORITHM   = "HS256"
JWT_EXPIRE_MIN  = 60  # 1 heure

# ── MongoDB ───────────────────────────────────────────
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://admin:tp-iot26%40@localhost:27017/clinique_db"
)
MONGO_DB = "clinique_db"

# ── InfluxDB ──────────────────────────────────────────
INFLUX_URL    = os.getenv("INFLUX_URL",    "http://localhost:8086")
INFLUX_TOKEN  = os.getenv("INFLUX_TOKEN",  "mon-super-token-123456789")
INFLUX_ORG    = os.getenv("INFLUX_ORG",   "clinique_abidjan")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "mesures_capteurs")

# ── Redis Sentinel ────────────────────────────────────
REDIS_SENTINEL_HOSTS_RAW = os.getenv(
    "REDIS_SENTINEL_HOSTS",
    "localhost:26379"
)
REDIS_MASTER_NAME = os.getenv("REDIS_MASTER_NAME", "clinique_master")
REDIS_PASSWORD    = os.getenv("REDIS_PASSWORD",    "tp-iot26@")

# Parse "host1:port1,host2:port2" → [(host, port), ...]
def parse_sentinel_hosts():
    hosts = []
    for entry in REDIS_SENTINEL_HOSTS_RAW.split(","):
        parts = entry.strip().split(":")
        if len(parts) == 2:
            hosts.append((parts[0], int(parts[1])))
    return hosts or [("localhost", 26379)]

REDIS_SENTINEL_HOSTS = parse_sentinel_hosts()

# ── Redis TTL ─────────────────────────────────────────
REDIS_TTL_VITAUX    = 30   # secondes — derniers vitaux
REDIS_TTL_PATIENTS  = 300  # 5 min — liste patients
REDIS_TTL_ALERTES   = 60   # 1 min — alertes actives
REDIS_TTL_STATS     = 120  # 2 min — statistiques

# ── MQTT ──────────────────────────────────────────────
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT   = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USER   = "nodered_agent"
MQTT_PASS   = "clinique2026"

# ── Rate limiting (Redis) ─────────────────────────────
RATE_LIMIT_MAX      = 60   # requêtes
RATE_LIMIT_WINDOW   = 60   # par fenêtre en secondes
