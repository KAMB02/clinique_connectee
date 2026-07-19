# 🏥 Clinique Connectée — Backend

## 📋 Description

Backend complet du système IoT **Clinique Connectée** — une simulation de clinique médicale à Cocody, Abidjan. Cette partie gère :

- **API REST** FastAPI × 3 instances avec JWT et RBAC
- **MongoDB** — stockage des patients, alertes, chambres
- **Redis Sentinel** — cache-aside, Pub/Sub, haute disponibilité
- **Nginx** — load balancer sur les 3 instances
- **Node-RED** — traitement des flux MQTT et création d'alertes
- **Tests Pytest** — 27 tests, couverture > 70%

---

## 🗂️ Structure

```
back-end/
├── api/
│   ├── main.py              # Point d'entrée FastAPI
│   ├── auth.py              # JWT + RBAC + rate limiting
│   ├── config.py            # Variables d'environnement
│   ├── database.py          # Connexions MongoDB / Redis / InfluxDB
│   ├── Dockerfile           # Image Python 3.11-slim
│   ├── requirements.txt     # Dépendances Python
│   └── routers/
│       ├── auth_router.py   # POST /auth/login, GET /auth/me
│       ├── patients.py      # CRUD patients + cache Redis
│       ├── alertes.py       # Alertes + Redis Pub/Sub + SSE
│       ├── stats.py         # Statistiques InfluxDB
│       └── chambres.py      # Carte des chambres
├── mongodb/
│   └── init.js              # Init DB, collections, données démo
├── nginx/
│   └── nginx.conf           # Load balancer 3 instances
├── node-red/
│   └── flow_alertes.json    # Flow MQTT → analyse → API alertes
├── redis/
│   ├── sentinel1/sentinel.conf
│   ├── sentinel2/sentinel.conf
│   └── sentinel3/sentinel.conf
└── tests/
    ├── test_api.py          # 27 tests Pytest
    └── pytest.ini           # Config pytest asyncio
```

---

## ⚡ Démarrage rapide

### Prérequis
- Docker Desktop installé et lancé
- Git

### 1. Cloner la branche
```bash
git clone -b back-end https://github.com/KAMB02/clinique_connectee.git
cd clinique_connectee
```

### 2. Lancer les services (depuis la racine du projet complet)
```bash
docker compose up --build -d
```

### 3. Vérifier que l'API tourne
```bash
curl http://localhost:80/health
# {"status":"healthy","services":{"mongodb":true,"redis":true,"influxdb":true}}
```

### 4. Accéder à la documentation
```
http://localhost:80/docs
```

---

## 🔐 Authentification

| Utilisateur   | Mot de passe   | Rôle        |
|---------------|----------------|-------------|
| `medecin1`    | `clinique2026` | medecin     |
| `controleur1` | `clinique2026` | controleur  |
| `technicien1` | `clinique2026` | technicien  |
| `admin`       | `clinique2026` | admin       |

**Login :**
```bash
curl -X POST http://localhost:80/auth/login \
  -d "username=medecin1&password=clinique2026"
```

---

## 🧪 Tests

```bash
# Installer les dépendances
pip install fastapi httpx pytest pytest-asyncio motor pymongo redis \
  influxdb-client python-jose "passlib==1.7.4" "bcrypt==4.0.1" python-multipart

# Lancer les 27 tests
pytest tests/test_api.py -v
```

---

## 🔑 Variables d'environnement clés

| Variable              | Valeur par défaut            |
|-----------------------|------------------------------|
| `MONGO_URI`           | `mongodb://admin:...@mongodb` |
| `JWT_SECRET`          | `clinique_jwt_secret_...`    |
| `REDIS_SENTINEL_HOSTS`| `sentinel1:26379,...`        |
| `REDIS_MASTER_NAME`   | `clinique_master`            |
| `INFLUX_URL`          | `http://influxdb:8086`       |

---

## 📡 Endpoints principaux

| Méthode | Route                    | Description              |
|---------|--------------------------|--------------------------|
| POST    | `/auth/login`            | Obtenir un JWT           |
| GET     | `/api/patients/`         | Liste patients (cache)   |
| POST    | `/api/alertes/`          | Créer alerte → Pub/Sub   |
| PUT     | `/api/alertes/{id}/ack`  | Acquitter une alerte     |
| GET     | `/api/stats/resume`      | Dashboard agrégé         |
| GET     | `/health`                | Santé des services       |

---
