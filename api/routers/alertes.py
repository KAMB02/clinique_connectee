"""
routers/alertes.py — Alertes médicales/sécurité + Redis Pub/Sub
Niveaux : ROUGE (critique) | ORANGE (avertissement) | VERT (info)
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json, uuid, asyncio

import auth, database, config

router = APIRouter(prefix="/api/alertes", tags=["Alertes"])

# ── Modèles ───────────────────────────────────────────
class AlerteCreate(BaseModel):
    chambre_id: str
    type_alerte: str          # "vitaux" | "intrusion" | "energie" | "equipement" | "appel"
    niveau: str               # "ROUGE" | "ORANGE" | "VERT"
    message: str
    valeur_capteur: Optional[float] = None
    unite: Optional[str] = None
    source: Optional[str] = "capteur"

CANAUX_REDIS = {
    "ROUGE":  "alertes:critique",
    "ORANGE": "alertes:avertissement",
    "VERT":   "alertes:info",
}

def _serialize(doc) -> dict:
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    for field in ["timestamp", "ack_at"]:
        if field in doc and isinstance(doc[field], datetime):
            doc[field] = doc[field].isoformat()
    return doc

# ══════════════════════════════════════════════════════
#  GET /api/alertes — Liste (cache 1 min)
# ══════════════════════════════════════════════════════
@router.get("/", summary="Alertes actives")
async def list_alertes(
    niveau: Optional[str] = None,
    chambre_id: Optional[str] = None,
    limit: int = 50,
    current_user=Depends(auth.require_role("alertes", "patients"))
):
    redis = database.get_redis()
    cache_key = f"alertes:list:{niveau or 'all'}:{chambre_id or 'all'}:{limit}"

    try:
        cached = redis.get(cache_key)
        if cached:
            return {"source": "cache", "data": json.loads(cached)}
    except Exception:
        pass

    query: dict = {"statut": {"$ne": "acquittée"}}
    if niveau:
        query["niveau"] = niveau.upper()
    if chambre_id:
        query["chambre_id"] = chambre_id

    col = database.col_alertes()
    docs = await col.find(query).sort("timestamp", -1).limit(limit).to_list(length=limit)
    data = [_serialize(d) for d in docs]

    try:
        redis.setex(cache_key, config.REDIS_TTL_ALERTES, json.dumps(data))
    except Exception:
        pass

    return {"source": "mongodb", "data": data}

# ══════════════════════════════════════════════════════
#  GET /api/alertes/historique
# ══════════════════════════════════════════════════════
@router.get("/historique", summary="Historique complet des alertes")
async def historique_alertes(
    limit: int = 100,
    current_user=Depends(auth.require_role("alertes", "admin"))
):
    col = database.col_alertes()
    docs = await col.find({}).sort("timestamp", -1).limit(limit).to_list(length=limit)
    return {"data": [_serialize(d) for d in docs]}

# ══════════════════════════════════════════════════════
#  POST /api/alertes — Créer une alerte (Node-RED → API)
# ══════════════════════════════════════════════════════
@router.post("/", status_code=201, summary="Créer une alerte (Node-RED ou capteur)")
async def create_alerte(
    alerte: AlerteCreate,
    current_user=Depends(auth.require_role("alertes", "admin"))
):
    alerte_id = f"ALT-{uuid.uuid4().hex[:8].upper()}"
    doc = {
        "alerte_id": alerte_id,
        **alerte.dict(),
        "niveau": alerte.niveau.upper(),
        "statut": "active",
        "timestamp": datetime.utcnow(),
        "ack_by": None,
        "ack_at": None
    }

    col = database.col_alertes()
    await col.insert_one(doc)

    # ── Pub/Sub Redis : broadcast en temps réel ───────
    canal = CANAUX_REDIS.get(doc["niveau"], "alertes:info")
    try:
        redis = database.get_redis()
        payload = {
            "alerte_id": alerte_id,
            "chambre_id": doc["chambre_id"],
            "niveau": doc["niveau"],
            "type_alerte": doc["type_alerte"],
            "message": doc["message"],
            "timestamp": doc["timestamp"].isoformat()
        }
        redis.publish(canal, json.dumps(payload))

        # Invalide cache liste
        for key in redis.scan_iter("alertes:list:*"):
            redis.delete(key)
    except Exception:
        pass

    return {"message": "Alerte enregistrée", "alerte_id": alerte_id, "canal": canal}

# ══════════════════════════════════════════════════════
#  PUT /api/alertes/{alerte_id}/ack — Acquitter
# ══════════════════════════════════════════════════════
@router.put("/{alerte_id}/ack", summary="Acquitter une alerte")
async def acquitter_alerte(
    alerte_id: str,
    current_user=Depends(auth.require_role("alertes", "patients"))
):
    col = database.col_alertes()
    result = await col.update_one(
        {"alerte_id": alerte_id, "statut": "active"},
        {"$set": {
            "statut": "acquittée",
            "ack_by": current_user.username,
            "ack_at": datetime.utcnow()
        }}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Alerte introuvable ou déjà acquittée")

    try:
        redis = database.get_redis()
        for key in redis.scan_iter("alertes:list:*"):
            redis.delete(key)
    except Exception:
        pass

    return {"message": f"Alerte {alerte_id} acquittée par {current_user.username}"}

# ══════════════════════════════════════════════════════
#  GET /api/alertes/stream — SSE (Server-Sent Events)
#  Écoute Redis Pub/Sub et pousse les alertes en temps réel
# ══════════════════════════════════════════════════════
@router.get("/stream", summary="Flux temps réel des alertes (SSE)")
async def stream_alertes(
    current_user=Depends(auth.require_role_sse("alertes", "patients"))
):
    async def event_generator():
        try:
            import redis as redis_lib
            # Connexion directe (pas Sentinel) pour le blocking subscribe
            sentinel = database.get_sentinel()
            r = sentinel.master_for(
                config.REDIS_MASTER_NAME,
                socket_timeout=None,        # Bloquant
                password=config.REDIS_PASSWORD,
                decode_responses=True
            )
            pubsub = r.pubsub()
            pubsub.subscribe("alertes:critique", "alertes:avertissement", "alertes:info")
            yield "data: {\"type\":\"connected\",\"message\":\"Flux alertes actif\"}\n\n"

            for message in pubsub.listen():
                if message["type"] == "message":
                    yield f"data: {message['data']}\n\n"
                    await asyncio.sleep(0)
        except Exception as e:
            yield f"data: {{\"type\":\"error\",\"message\":\"{str(e)}\"}}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )
