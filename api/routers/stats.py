"""
routers/stats.py — Métriques temps-série depuis InfluxDB (Flux)
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import json

import auth, database, config

router = APIRouter(prefix="/api/stats", tags=["Statistiques & Métriques"])

def _flux_to_list(tables) -> list:
    """Convertit les tables InfluxDB en liste de dicts."""
    results = []
    for table in tables:
        for record in table.records:
            results.append({
                "time": record.get_time().isoformat(),
                "field": record.get_field(),
                "value": record.get_value(),
                "chambre": record.values.get("chambre_id", ""),
                "zone": record.values.get("zone", ""),
            })
    return results

# ══════════════════════════════════════════════════════
#  GET /api/stats/vitaux/{chambre_id}
#  Derniers vitaux d'une chambre (cache 30s)
# ══════════════════════════════════════════════════════
@router.get("/vitaux/{chambre_id}", summary="Derniers vitaux d'une chambre")
async def vitaux_chambre(
    chambre_id: str,
    range_min: int = 30,
    current_user=Depends(auth.require_role("stats", "patients"))
):
    redis = database.get_redis()
    cache_key = f"stats:vitaux:{chambre_id}:{range_min}"

    try:
        cached = redis.get(cache_key)
        if cached:
            return {"source": "cache", "chambre_id": chambre_id, **json.loads(cached)}
    except Exception:
        pass

    query_api = database.get_query_api()
    # Mesures réelles publiées par simulateur_clinique_v2.py :
    #   vitaux_chambre  → spo2, ecg_bpm, temperature, pression_sys, pression_dia, alerte_active
    #   co2_ambiant     → co2_ppm
    #   perfuseur       → debit_ml_h, niveau_poche_ml, alarme
    flux = f"""
    from(bucket: "{config.INFLUX_BUCKET}")
      |> range(start: -{range_min}m)
      |> filter(fn: (r) => r["chambre_id"] == "{chambre_id}")
      |> filter(fn: (r) => r["_measurement"] == "vitaux_chambre"
                        or r["_measurement"] == "co2_ambiant"
                        or r["_measurement"] == "perfuseur")
      |> filter(fn: (r) => r["_field"] == "spo2"
                        or r["_field"] == "ecg_bpm"
                        or r["_field"] == "temperature"
                        or r["_field"] == "pression_sys"
                        or r["_field"] == "pression_dia"
                        or r["_field"] == "alerte_active"
                        or r["_field"] == "co2_ppm"
                        or r["_field"] == "niveau_poche_ml")
      |> last()
    """
    try:
        tables = query_api.query(flux, org=config.INFLUX_ORG)
        records = _flux_to_list(tables)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"InfluxDB indisponible : {str(e)}")

    # Aplatit la liste de records Flux en un objet plat {champ: valeur}
    # pour matcher normalizeVitaux() côté dashboard React.
    flat = {r["field"]: r["value"] for r in records}
    data = {
        "spo2": flat.get("spo2"),
        "ecg_bpm": flat.get("ecg_bpm"),
        "temperature": flat.get("temperature"),
        "pression_sys": flat.get("pression_sys"),
        "pression_dia": flat.get("pression_dia"),
        "alerte_active": flat.get("alerte_active"),
        "co2_ppm": flat.get("co2_ppm"),
        "niveau_poche_ml": flat.get("niveau_poche_ml"),
    }

    try:
        redis.setex(cache_key, config.REDIS_TTL_VITAUX, json.dumps(data))
    except Exception:
        pass

    return {"source": "influxdb", "chambre_id": chambre_id, **data}

# ══════════════════════════════════════════════════════
#  GET /api/stats/energie
#  Consommation électrique par zone (cache 2 min)
# ══════════════════════════════════════════════════════
@router.get("/energie", summary="Consommation électrique par zone")
async def stats_energie(
    range_min: int = 60,
    current_user=Depends(auth.require_role("stats", "energie"))
):
    redis = database.get_redis()
    cache_key = f"stats:energie:{range_min}"

    try:
        cached = redis.get(cache_key)
        if cached:
            return {"source": "cache", **json.loads(cached)}
    except Exception:
        pass

    query_api = database.get_query_api()
    # Mesures réelles publiées par simulateur_clinique_v2.py :
    #   energie_ups        → niveau_pct, tension_v, autonomie_min, en_charge
    #   energie_generateur → actif, charge_pct, statut
    #   energie_compteur   → consommation_w, tag "circuit" (BLOC-A/BLOC-B/URGENCE)
    flux = f"""
    from(bucket: "{config.INFLUX_BUCKET}")
      |> range(start: -{range_min}m)
      |> filter(fn: (r) => r["_measurement"] == "energie_ups"
                        or r["_measurement"] == "energie_generateur"
                        or r["_measurement"] == "energie_compteur")
      |> last()
    """
    try:
        tables = query_api.query(flux, org=config.INFLUX_ORG)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"InfluxDB indisponible : {str(e)}")

    ups_vals, gen_vals, conso_par_circuit = {}, {}, {}
    for table in tables:
        for record in table.records:
            measurement = record.get_measurement()
            field, value = record.get_field(), record.get_value()
            if measurement == "energie_ups":
                ups_vals[field] = value
            elif measurement == "energie_generateur":
                gen_vals[field] = value
            elif measurement == "energie_compteur":
                circuit = record.values.get("circuit", "")
                conso_par_circuit[circuit] = value if field == "consommation_w" else conso_par_circuit.get(circuit)

    data = {
        "ups_niveau_pct":  ups_vals.get("niveau_pct"),
        "tension_v":       ups_vals.get("tension_v"),
        "autonomie_min":   ups_vals.get("autonomie_min"),
        "en_charge":       ups_vals.get("en_charge"),
        "statut":          gen_vals.get("statut"),
        "generateur_actif": gen_vals.get("actif"),
        "generateur_charge_pct": gen_vals.get("charge_pct"),
        "conso_bloc_a":    conso_par_circuit.get("BLOC-A"),
        "conso_bloc_b":    conso_par_circuit.get("BLOC-B"),
        "conso_urgence":   conso_par_circuit.get("URGENCE"),
    }

    try:
        redis.setex(cache_key, config.REDIS_TTL_STATS, json.dumps(data))
    except Exception:
        pass

    return {"source": "influxdb", **data}

# ══════════════════════════════════════════════════════
#  GET /api/stats/securite
#  Accès et mouvements (cache 1 min)
# ══════════════════════════════════════════════════════
@router.get("/securite", summary="Événements de sécurité récents")
async def stats_securite(
    range_min: int = 60,
    current_user=Depends(auth.require_role("stats", "securite"))
):
    redis = database.get_redis()
    cache_key = f"stats:securite:{range_min}"

    try:
        cached = redis.get(cache_key)
        if cached:
            return {"source": "cache", "data": json.loads(cached)}
    except Exception:
        pass

    query_api = database.get_query_api()
    # Mesures réelles : securite_acces (porte_ouverte, duree_ouverte_ms),
    # mouvement (mouvement, chute_detectee), badge_acces (badge_id, autorise),
    # camera_intrusion (intrusion_ia, confiance_pct)
    flux = f"""
    from(bucket: "{config.INFLUX_BUCKET}")
      |> range(start: -{range_min}m)
      |> filter(fn: (r) => r["_measurement"] == "securite_acces"
                        or r["_measurement"] == "mouvement"
                        or r["_measurement"] == "badge_acces"
                        or r["_measurement"] == "camera_intrusion")
    """
    try:
        tables = query_api.query(flux, org=config.INFLUX_ORG)
        data = _flux_to_list(tables)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"InfluxDB indisponible : {str(e)}")

    try:
        redis.setex(cache_key, config.REDIS_TTL_ALERTES, json.dumps(data))
    except Exception:
        pass

    return {"source": "influxdb", "data": data}

# ══════════════════════════════════════════════════════
#  GET /api/stats/resume — Tableau de bord agrégé
# ══════════════════════════════════════════════════════
@router.get("/resume", summary="Résumé global (dashboard)")
async def resume_global(
    current_user=Depends(auth.require_role("stats", "patients"))
):
    redis = database.get_redis()
    cache_key = "stats:resume"

    try:
        cached = redis.get(cache_key)
        if cached:
            return {"source": "cache", "data": json.loads(cached)}
    except Exception:
        pass

    # Nombre de patients actifs
    nb_patients = await database.col_patients().count_documents({"statut": "hospitalise"})
    nb_critiques = await database.col_patients().count_documents({"statut": "critique"})
    nb_alertes_actives = await database.col_alertes().count_documents({"statut": "active"})
    nb_alertes_rouge  = await database.col_alertes().count_documents({"statut": "active", "niveau": "ROUGE"})
    nb_alertes_orange = await database.col_alertes().count_documents({"statut": "active", "niveau": "ORANGE"})

    data = {
        "patients": {"total": nb_patients, "critiques": nb_critiques},
        "alertes": {
            "actives": nb_alertes_actives,
            "rouge": nb_alertes_rouge,
            "orange": nb_alertes_orange
        }
    }

    try:
        redis.setex(cache_key, 60, json.dumps(data))
    except Exception:
        pass

    return {"source": "mongodb", "data": data}
