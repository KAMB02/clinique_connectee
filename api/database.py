"""
database.py — Connexions MongoDB, Redis Sentinel, InfluxDB
"""
import redis.sentinel
from motor.motor_asyncio import AsyncIOMotorClient
from influxdb_client import InfluxDBClient
from influxdb_client.client.query_api import QueryApi
import config

# ══════════════════════════════════════════════════════
#  MongoDB (Motor async)
# ══════════════════════════════════════════════════════
_mongo_client: AsyncIOMotorClient = None

def get_mongo_client() -> AsyncIOMotorClient:
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(config.MONGO_URI, serverSelectionTimeoutMS=5000)
    return _mongo_client

def get_db():
    return get_mongo_client()[config.MONGO_DB]

def col_patients():    return get_db()["patients"]
def col_alertes():     return get_db()["alertes"]
def col_chambres():    return get_db()["chambres"]
def col_utilisateurs():return get_db()["utilisateurs"]
def col_dossiers():    return get_db()["dossiers_soins"]
def col_incidents():   return get_db()["incidents_securite"]

# ══════════════════════════════════════════════════════
#  Redis Sentinel (HA)
# ══════════════════════════════════════════════════════
_sentinel = None

def get_sentinel():
    global _sentinel
    if _sentinel is None:
        # Les sentinelles elles-mêmes n'ont pas de requirepass
        # Le password est uniquement pour se connecter au master/replicas
        _sentinel = redis.sentinel.Sentinel(
            config.REDIS_SENTINEL_HOSTS,
            socket_timeout=2,
            sentinel_kwargs={}
        )
    return _sentinel

def get_redis():
    sentinel = get_sentinel()
    return sentinel.master_for(
        config.REDIS_MASTER_NAME,
        socket_timeout=2,
        password=config.REDIS_PASSWORD,
        decode_responses=True
    )

# ══════════════════════════════════════════════════════
#  InfluxDB 2.x
# ══════════════════════════════════════════════════════
_influx_client = None

def get_influx():
    global _influx_client
    if _influx_client is None:
        _influx_client = InfluxDBClient(
            url=config.INFLUX_URL,
            token=config.INFLUX_TOKEN,
            org=config.INFLUX_ORG
        )
    return _influx_client

def get_query_api():
    return get_influx().query_api()

# ══════════════════════════════════════════════════════
#  Startup / Shutdown — NON BLOQUANT
#  L'API démarre même si un service est lent
# ══════════════════════════════════════════════════════
async def startup():
    # MongoDB
    try:
        await get_mongo_client().admin.command("ping")
        print("[DB] MongoDB connecté ✓")
    except Exception as e:
        print(f"[DB] MongoDB non disponible au démarrage : {e} (sera retenté à chaque requête)")

    # Redis
    try:
        get_redis().ping()
        print(f"[DB] Redis Sentinel connecté ✓")
    except Exception as e:
        print(f"[DB] Redis non disponible au démarrage : {e} (sera retenté à chaque requête)")

    # InfluxDB
    try:
        h = get_influx().health()
        print(f"[DB] InfluxDB connecté ✓ (status={h.status})")
    except Exception as e:
        print(f"[DB] InfluxDB non disponible au démarrage : {e} (sera retenté à chaque requête)")

async def shutdown():
    global _mongo_client, _influx_client
    if _mongo_client:
        _mongo_client.close()
    if _influx_client:
        _influx_client.close()
