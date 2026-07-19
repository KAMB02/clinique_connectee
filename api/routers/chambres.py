"""
routers/chambres.py — Gestion des chambres
"""
from fastapi import APIRouter, HTTPException, Depends
import json, auth, database, config

router = APIRouter(prefix="/api/chambres", tags=["Chambres"])

def _serialize(doc) -> dict:
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc

@router.get("/", summary="Liste des chambres")
async def list_chambres(current_user=Depends(auth.require_role("chambres"))):
    redis = database.get_redis()
    cache_key = "chambres:list"
    try:
        cached = redis.get(cache_key)
        if cached:
            return {"source": "cache", "data": json.loads(cached)}
    except Exception:
        pass

    col = database.col_chambres()
    docs = await col.find({}).to_list(length=100)
    data = [_serialize(d) for d in docs]

    try:
        redis.setex(cache_key, 600, json.dumps(data))   # 10 min — statique
    except Exception:
        pass

    return {"source": "mongodb", "data": data}

@router.get("/{chambre_id}", summary="Détail d'une chambre + patient actuel")
async def get_chambre(
    chambre_id: str,
    current_user=Depends(auth.require_role("chambres"))
):
    redis = database.get_redis()
    cache_key = f"chambres:{chambre_id}"
    try:
        cached = redis.get(cache_key)
        if cached:
            return {"source": "cache", "data": json.loads(cached)}
    except Exception:
        pass

    chambre = await database.col_chambres().find_one({"chambre_id": chambre_id})
    if not chambre:
        raise HTTPException(status_code=404, detail=f"Chambre {chambre_id} introuvable")

    patient = await database.col_patients().find_one(
        {"chambre_id": chambre_id, "statut": {"$in": ["hospitalise", "critique"]}}
    )

    data = {
        "chambre": _serialize(chambre),
        "patient": _serialize(patient) if patient else None
    }

    try:
        redis.setex(cache_key, 120, json.dumps(data))
    except Exception:
        pass

    return {"source": "mongodb", "data": data}
