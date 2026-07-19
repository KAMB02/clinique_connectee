"""
routers/patients.py — CRUD patients + cache Redis cache-aside
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json, uuid

import auth, database, config

router = APIRouter(prefix="/api/patients", tags=["Patients"])

# ── Modèles ───────────────────────────────────────────
class PatientCreate(BaseModel):
    nom: str
    prenom: str
    age: int
    chambre_id: str
    groupe_sanguin: Optional[str] = ""
    allergies: Optional[List[str]] = []
    antecedents: Optional[List[str]] = []
    medecin_referent: Optional[str] = ""

class PatientUpdate(BaseModel):
    chambre_id: Optional[str] = None
    statut: Optional[str] = None
    medecin_referent: Optional[str] = None
    antecedents: Optional[List[str]] = None

def _serialize(doc) -> dict:
    """Convertit ObjectId MongoDB en str pour JSON."""
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    if "date_admission" in doc and isinstance(doc["date_admission"], datetime):
        doc["date_admission"] = doc["date_admission"].isoformat()
    return doc

# ══════════════════════════════════════════════════════
#  GET /api/patients — Liste (cache 5 min)
# ══════════════════════════════════════════════════════
@router.get("/", summary="Liste de tous les patients")
async def list_patients(
    statut: Optional[str] = None,
    current_user=Depends(auth.require_role("patients"))
):
    redis = database.get_redis()
    cache_key = f"patients:list:{statut or 'all'}"

    # ── Cache-aside : lecture ─────────────────────────
    try:
        cached = redis.get(cache_key)
        if cached:
            return {"source": "cache", "data": json.loads(cached)}
    except Exception:
        pass

    # ── Fallback MongoDB ──────────────────────────────
    query = {}
    if statut:
        query["statut"] = statut

    col = database.col_patients()
    docs = await col.find(query).to_list(length=200)
    data = [_serialize(d) for d in docs]

    # ── Cache-aside : écriture ────────────────────────
    try:
        redis.setex(cache_key, config.REDIS_TTL_PATIENTS, json.dumps(data))
    except Exception:
        pass

    return {"source": "mongodb", "data": data}

# ══════════════════════════════════════════════════════
#  GET /api/patients/{patient_id}
# ══════════════════════════════════════════════════════
@router.get("/{patient_id}", summary="Détail d'un patient")
async def get_patient(
    patient_id: str,
    current_user=Depends(auth.require_role("patients"))
):
    redis = database.get_redis()
    cache_key = f"patients:{patient_id}"

    try:
        cached = redis.get(cache_key)
        if cached:
            return {"source": "cache", "data": json.loads(cached)}
    except Exception:
        pass

    col = database.col_patients()
    doc = await col.find_one({"patient_id": patient_id})
    if not doc:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} introuvable")

    data = _serialize(doc)

    try:
        redis.setex(cache_key, config.REDIS_TTL_PATIENTS, json.dumps(data))
    except Exception:
        pass

    return {"source": "mongodb", "data": data}

# ══════════════════════════════════════════════════════
#  POST /api/patients — Créer
# ══════════════════════════════════════════════════════
@router.post("/", status_code=201, summary="Admettre un nouveau patient")
async def create_patient(
    patient: PatientCreate,
    current_user=Depends(auth.require_role("medecin", "admin"))
):
    col = database.col_patients()
    patient_id = f"PAT-{uuid.uuid4().hex[:6].upper()}"
    doc = {
        "patient_id": patient_id,
        **patient.dict(),
        "statut": "hospitalise",
        "date_admission": datetime.utcnow()
    }
    await col.insert_one(doc)

    # Invalide le cache liste
    try:
        redis = database.get_redis()
        for key in redis.scan_iter("patients:list:*"):
            redis.delete(key)
    except Exception:
        pass

    return {"message": "Patient admis", "patient_id": patient_id}

# ══════════════════════════════════════════════════════
#  PUT /api/patients/{patient_id} — Modifier
# ══════════════════════════════════════════════════════
@router.put("/{patient_id}", summary="Mettre à jour un patient")
async def update_patient(
    patient_id: str,
    update: PatientUpdate,
    current_user=Depends(auth.require_role("medecin", "admin"))
):
    col = database.col_patients()
    changes = {k: v for k, v in update.dict().items() if v is not None}
    if not changes:
        raise HTTPException(status_code=400, detail="Aucune modification fournie")

    result = await col.update_one({"patient_id": patient_id}, {"$set": changes})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} introuvable")

    # Invalide cache
    try:
        redis = database.get_redis()
        redis.delete(f"patients:{patient_id}")
        for key in redis.scan_iter("patients:list:*"):
            redis.delete(key)
    except Exception:
        pass

    return {"message": "Patient mis à jour", "patient_id": patient_id}

# ══════════════════════════════════════════════════════
#  DELETE /api/patients/{patient_id} — Sortie/décharge
# ══════════════════════════════════════════════════════
@router.delete("/{patient_id}", summary="Décharger un patient")
async def discharge_patient(
    patient_id: str,
    current_user=Depends(auth.require_role("admin"))
):
    col = database.col_patients()
    result = await col.update_one(
        {"patient_id": patient_id},
        {"$set": {"statut": "sorti", "date_sortie": datetime.utcnow()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} introuvable")

    try:
        redis = database.get_redis()
        redis.delete(f"patients:{patient_id}")
        for key in redis.scan_iter("patients:list:*"):
            redis.delete(key)
    except Exception:
        pass

    return {"message": f"Patient {patient_id} déchargé"}
