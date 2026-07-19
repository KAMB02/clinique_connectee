"""
tests/test_api.py — Tests Pytest complets
Clinique Connectée | M1 BD-GL UFHB 2025-2026
Lance avec : pytest tests/ -v
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
import json
from datetime import datetime

# ── Import de l'app ───────────────────────────────────
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

from main import app
import auth

# ══════════════════════════════════════════════════════
#  Fixtures
# ══════════════════════════════════════════════════════

PATIENTS_FAKE = [
    {
        "_id": "507f1f77bcf86cd799439011",
        "patient_id": "PAT-001",
        "nom": "Koné", "prenom": "Aminata", "age": 45,
        "chambre_id": "CH-001", "statut": "hospitalise",
        "groupe_sanguin": "O+", "allergies": [],
        "antecedents": ["hypertension"],
        "medecin_referent": "Dr. Kouassi",
        "date_admission": datetime.utcnow().isoformat()
    }
]

ALERTES_FAKE = [
    {
        "_id": "507f1f77bcf86cd799439022",
        "alerte_id": "ALT-ABCD1234",
        "chambre_id": "CH-001",
        "type_alerte": "vitaux",
        "niveau": "ROUGE",
        "message": "FC critique : 160 bpm",
        "statut": "active",
        "timestamp": datetime.utcnow().isoformat(),
        "ack_by": None,
        "ack_at": None
    }
]

@pytest.fixture
def token_medecin():
    return auth.create_access_token({"sub": "medecin1", "role": "medecin"})

@pytest.fixture
def token_controleur():
    return auth.create_access_token({"sub": "controleur1", "role": "controleur"})

@pytest.fixture
def token_technicien():
    return auth.create_access_token({"sub": "technicien1", "role": "technicien"})

@pytest.fixture
def token_admin():
    return auth.create_access_token({"sub": "admin", "role": "admin"})

@pytest.fixture
def headers_medecin(token_medecin):
    return {"Authorization": f"Bearer {token_medecin}"}

@pytest.fixture
def headers_admin(token_admin):
    return {"Authorization": f"Bearer {token_admin}"}

@pytest.fixture
def headers_controleur(token_controleur):
    return {"Authorization": f"Bearer {token_controleur}"}

# ── Mock Redis ────────────────────────────────────────
@pytest.fixture
def mock_redis():
    r = MagicMock()
    r.get.return_value = None          # Pas de cache → fallback MongoDB
    r.setex.return_value = True
    r.ping.return_value = True
    r.delete.return_value = 1
    r.scan_iter.return_value = []
    r.incr.return_value = 1
    r.expire.return_value = True
    pipe = MagicMock()
    pipe.execute.return_value = [1, True]
    r.pipeline.return_value = pipe
    return r

# ── Mock MongoDB cursor ───────────────────────────────
def make_cursor(data):
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=data)
    cursor.sort.return_value = cursor
    cursor.limit.return_value = cursor
    return cursor

# ══════════════════════════════════════════════════════
#  Tests Authentification
# ══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_login_succes():
    """Login avec credentials valides retourne un JWT."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/auth/login", data={"username": "medecin1", "password": "clinique2026"})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["role"] == "medecin"

@pytest.mark.asyncio
async def test_login_echec_mauvais_mdp():
    """Login avec mauvais mot de passe → 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/auth/login", data={"username": "medecin1", "password": "mauvais"})
    assert r.status_code == 401

@pytest.mark.asyncio
async def test_login_utilisateur_inconnu():
    """Login avec username inexistant → 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/auth/login", data={"username": "fantome", "password": "abc"})
    assert r.status_code == 401

@pytest.mark.asyncio
async def test_me_avec_token(headers_medecin):
    """GET /auth/me retourne le profil de l'utilisateur connecté."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/auth/me", headers=headers_medecin)
    assert r.status_code == 200
    assert r.json()["username"] == "medecin1"
    assert r.json()["role"] == "medecin"

@pytest.mark.asyncio
async def test_me_sans_token():
    """GET /auth/me sans token → 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/auth/me")
    assert r.status_code == 401

@pytest.mark.asyncio
async def test_token_expire():
    """Token avec expiration passée → 401."""
    from datetime import timedelta
    expired = auth.create_access_token(
        {"sub": "medecin1", "role": "medecin"},
        expires_delta=timedelta(seconds=-1)
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401

# ══════════════════════════════════════════════════════
#  Tests Patients
# ══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_patients(headers_medecin, mock_redis):
    """GET /api/patients retourne la liste des patients."""
    fake_data = [{**p, "_id": p["_id"]} for p in PATIENTS_FAKE]

    with patch("database.get_redis", return_value=mock_redis), \
         patch("database.col_patients") as mock_col:
        mock_col.return_value.find.return_value = make_cursor(fake_data)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/patients/", headers=headers_medecin)

    assert r.status_code == 200
    body = r.json()
    assert "data" in body
    assert len(body["data"]) == 1
    assert body["data"][0]["patient_id"] == "PAT-001"

@pytest.mark.asyncio
async def test_list_patients_depuis_cache(headers_medecin, mock_redis):
    """Cache Redis retourné si disponible."""
    mock_redis.get.return_value = json.dumps(PATIENTS_FAKE)

    with patch("database.get_redis", return_value=mock_redis):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/patients/", headers=headers_medecin)

    assert r.status_code == 200
    assert r.json()["source"] == "cache"

@pytest.mark.asyncio
async def test_get_patient_par_id(headers_medecin, mock_redis):
    """GET /api/patients/{id} retourne le détail."""
    fake = {**PATIENTS_FAKE[0]}
    with patch("database.get_redis", return_value=mock_redis), \
         patch("database.col_patients") as mock_col:
        mock_col.return_value.find_one = AsyncMock(return_value=fake)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/patients/PAT-001", headers=headers_medecin)

    assert r.status_code == 200
    assert r.json()["data"]["patient_id"] == "PAT-001"

@pytest.mark.asyncio
async def test_get_patient_introuvable(headers_medecin, mock_redis):
    """GET patient inexistant → 404."""
    with patch("database.get_redis", return_value=mock_redis), \
         patch("database.col_patients") as mock_col:
        mock_col.return_value.find_one = AsyncMock(return_value=None)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/patients/PAT-INCONNU", headers=headers_medecin)

    assert r.status_code == 404

@pytest.mark.asyncio
async def test_create_patient(headers_medecin, mock_redis):
    """POST /api/patients crée un patient."""
    new_patient = {
        "nom": "Touré", "prenom": "Salif", "age": 50,
        "chambre_id": "CH-004"
    }
    with patch("database.get_redis", return_value=mock_redis), \
         patch("database.col_patients") as mock_col:
        mock_col.return_value.insert_one = AsyncMock(return_value=MagicMock(inserted_id="abc123"))

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/patients/", json=new_patient, headers=headers_medecin)

    assert r.status_code == 201
    assert "patient_id" in r.json()

@pytest.mark.asyncio
async def test_create_patient_acces_refuse(headers_controleur):
    """Contrôleur ne peut pas créer un patient → 403."""
    new_patient = {"nom": "Touré", "prenom": "Salif", "age": 50, "chambre_id": "CH-004"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/patients/", json=new_patient, headers=headers_controleur)
    assert r.status_code == 403

@pytest.mark.asyncio
async def test_update_patient(headers_medecin, mock_redis):
    """PUT /api/patients/{id} met à jour un patient."""
    with patch("database.get_redis", return_value=mock_redis), \
         patch("database.col_patients") as mock_col:
        result = MagicMock()
        result.matched_count = 1
        mock_col.return_value.update_one = AsyncMock(return_value=result)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.put("/api/patients/PAT-001",
                            json={"statut": "critique"},
                            headers=headers_medecin)

    assert r.status_code == 200

# ══════════════════════════════════════════════════════
#  Tests Alertes
# ══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_alertes(headers_medecin, mock_redis):
    """GET /api/alertes retourne les alertes actives."""
    fake = [{**a} for a in ALERTES_FAKE]
    with patch("database.get_redis", return_value=mock_redis), \
         patch("database.col_alertes") as mock_col:
        mock_col.return_value.find.return_value = make_cursor(fake)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/alertes/", headers=headers_medecin)

    assert r.status_code == 200
    assert len(r.json()["data"]) == 1
    assert r.json()["data"][0]["niveau"] == "ROUGE"

@pytest.mark.asyncio
async def test_create_alerte(headers_medecin, mock_redis):
    """POST /api/alertes crée une alerte et publie sur Redis."""
    alerte = {
        "chambre_id": "CH-001",
        "type_alerte": "vitaux",
        "niveau": "ROUGE",
        "message": "FC critique : 160 bpm",
        "valeur_capteur": 160.0,
        "unite": "bpm"
    }
    with patch("database.get_redis", return_value=mock_redis), \
         patch("database.col_alertes") as mock_col:
        mock_col.return_value.insert_one = AsyncMock(return_value=MagicMock(inserted_id="xyz"))

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/alertes/", json=alerte, headers=headers_medecin)

    assert r.status_code == 201
    assert "alerte_id" in r.json()
    assert r.json()["canal"] == "alertes:critique"

@pytest.mark.asyncio
async def test_create_alerte_orange(headers_medecin, mock_redis):
    """Alerte ORANGE publiée sur le bon canal Redis."""
    alerte = {
        "chambre_id": "CH-002",
        "type_alerte": "vitaux",
        "niveau": "ORANGE",
        "message": "Température élevée : 38.7°C",
    }
    with patch("database.get_redis", return_value=mock_redis), \
         patch("database.col_alertes") as mock_col:
        mock_col.return_value.insert_one = AsyncMock(return_value=MagicMock())

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/alertes/", json=alerte, headers=headers_medecin)

    assert r.status_code == 201
    assert r.json()["canal"] == "alertes:avertissement"

@pytest.mark.asyncio
async def test_acquitter_alerte(headers_medecin, mock_redis):
    """PUT /api/alertes/{id}/ack acquitte une alerte."""
    with patch("database.get_redis", return_value=mock_redis), \
         patch("database.col_alertes") as mock_col:
        result = MagicMock()
        result.matched_count = 1
        mock_col.return_value.update_one = AsyncMock(return_value=result)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.put("/api/alertes/ALT-ABCD1234/ack", headers=headers_medecin)

    assert r.status_code == 200
    assert "acquittée" in r.json()["message"]

@pytest.mark.asyncio
async def test_acquitter_alerte_introuvable(headers_medecin, mock_redis):
    """ACK d'une alerte inexistante → 404."""
    with patch("database.get_redis", return_value=mock_redis), \
         patch("database.col_alertes") as mock_col:
        result = MagicMock()
        result.matched_count = 0
        mock_col.return_value.update_one = AsyncMock(return_value=result)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.put("/api/alertes/ALT-INCONNU/ack", headers=headers_medecin)

    assert r.status_code == 404

# ══════════════════════════════════════════════════════
#  Tests RBAC
# ══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_rbac_technicien_ne_peut_pas_voir_patients(headers_controleur, mock_redis):
    """Contrôleur ne peut pas accéder aux patients."""
    with patch("database.get_redis", return_value=mock_redis):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/patients/", headers=headers_controleur)
    assert r.status_code == 403

@pytest.mark.asyncio
async def test_rbac_sans_token():
    """Toute route protégée sans token → 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/patients/")
    assert r.status_code == 401

@pytest.mark.asyncio
async def test_rbac_token_invalide():
    """Token falsifié → 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/patients/", headers={"Authorization": "Bearer faux.token.ici"})
    assert r.status_code == 401

# ══════════════════════════════════════════════════════
#  Tests Health & système
# ══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_health_endpoint(mock_redis):
    """GET /health retourne le statut des services."""
    with patch("database.get_redis", return_value=mock_redis), \
         patch("database.get_mongo_client") as mock_mongo, \
         patch("database.get_influx") as mock_influx:

        mock_mongo.return_value.admin.command = AsyncMock(return_value={"ok": 1})
        health_obj = MagicMock()
        health_obj.status = "pass"
        mock_influx.return_value.health.return_value = health_obj

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/health")

    assert r.status_code == 200
    body = r.json()
    assert "status" in body
    assert "services" in body

@pytest.mark.asyncio
async def test_root():
    """GET / retourne les infos de base de l'API."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/")
    assert r.status_code == 200
    assert "instance" in r.json()

# ══════════════════════════════════════════════════════
#  Tests Chambres
# ══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_chambres(headers_medecin, mock_redis):
    """GET /api/chambres retourne les chambres."""
    fake_chambres = [
        {"_id": "abc", "chambre_id": "CH-001", "type": "hospitalisation", "etage": 1}
    ]
    with patch("database.get_redis", return_value=mock_redis), \
         patch("database.col_chambres") as mock_col:
        mock_col.return_value.find.return_value = make_cursor(fake_chambres)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/chambres/", headers=headers_medecin)

    assert r.status_code == 200
    assert r.json()["data"][0]["chambre_id"] == "CH-001"

# ══════════════════════════════════════════════════════
#  Tests Redis cache-aside
# ══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_cache_ecrit_apres_mongo(headers_medecin, mock_redis):
    """Redis.setex doit être appelé après un retour MongoDB."""
    fake = [{**p} for p in PATIENTS_FAKE]
    with patch("database.get_redis", return_value=mock_redis), \
         patch("database.col_patients") as mock_col:
        mock_col.return_value.find.return_value = make_cursor(fake)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.get("/api/patients/", headers=headers_medecin)

    mock_redis.setex.assert_called_once()

@pytest.mark.asyncio
async def test_cache_lu_avant_mongo(headers_medecin, mock_redis):
    """Si Redis a la donnée, MongoDB ne doit pas être appelé."""
    mock_redis.get.return_value = json.dumps(PATIENTS_FAKE)

    with patch("database.get_redis", return_value=mock_redis), \
         patch("database.col_patients") as mock_col:

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/patients/", headers=headers_medecin)

    mock_col.assert_not_called()
    assert r.json()["source"] == "cache"
