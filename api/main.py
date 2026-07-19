"""
main.py — Clinique Connectée | API FastAPI
M1 BD-GL UFHB 2025-2026 | Rôle : Traoré Siaka
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import time

import config, database, auth
from routers import auth_router, patients, alertes, stats, chambres

# ══════════════════════════════════════════════════════
#  Lifecycle (startup / shutdown)
# ══════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[STARTUP] Instance #{config.INSTANCE_ID} démarrage...")
    await database.startup()
    # Warmup bcrypt : évite que la 1ère requête /auth/login paie le
    # coût du hash (calcul CPU synchrone qui peut faire timeout côté
    # client si la 1ère requête arrive juste après un cold start).
    auth._get_pwd_hash()
    print(f"[STARTUP] Instance #{config.INSTANCE_ID} prête ✓")
    yield
    await database.shutdown()
    print(f"[SHUTDOWN] Instance #{config.INSTANCE_ID} arrêtée")

# ══════════════════════════════════════════════════════
#  Application
# ══════════════════════════════════════════════════════
app = FastAPI(
    title="Clinique Connectée — API",
    description="""
## API REST — Système IoT Clinique de Cocody

Gestion des patients, alertes médicales, métriques capteurs et sécurité.

**Authentification :** JWT Bearer (via `/auth/login`)

**Rôles :**
- `admin` — accès total
- `medecin` — patients, alertes, statistiques vitales
- `controleur` — alertes sécurité, accès
- `technicien` — statistiques énergie, équipements

**Instance courante :** {}
""".format(config.INSTANCE_ID),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# ── CORS ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Middleware : temps de réponse ─────────────────────
# IMPORTANT : middleware ASGI pur (PAS @app.middleware("http") /
# BaseHTTPMiddleware). BaseHTTPMiddleware fait tourner l'endpoint dans
# une tâche séparée et surveille la déconnexion du client par polling ;
# sur un StreamingResponse infini (notre SSE /api/alertes/stream), ce
# polling génère de faux positifs de déconnexion et coupe le flux au
# bout de quelques secondes. Un middleware ASGI qui ne fait qu'intercepter
# l'événement "http.response.start" n'a pas ce problème : il ne touche
# jamais au corps de la réponse.
class ProcessTimeMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.time()

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                duration = round((time.time() - start) * 1000, 2)
                headers = message.setdefault("headers", [])
                headers.append((b"x-process-time-ms", str(duration).encode()))
                headers.append((b"x-instance-id", str(config.INSTANCE_ID).encode()))
            await send(message)

        await self.app(scope, receive, send_wrapper)

app.add_middleware(ProcessTimeMiddleware)

# ── Routers ───────────────────────────────────────────
app.include_router(auth_router.router)
app.include_router(patients.router)
app.include_router(alertes.router)
app.include_router(stats.router)
app.include_router(chambres.router)

# ── Health check ──────────────────────────────────────
@app.get("/health", tags=["Système"], summary="Santé de l'instance")
async def health():
    checks = {"mongodb": False, "redis": False, "influxdb": False}

    try:
        await database.get_mongo_client().admin.command("ping")
        checks["mongodb"] = True
    except Exception:
        pass

    try:
        database.get_redis().ping()
        checks["redis"] = True
    except Exception:
        pass

    try:
        h = database.get_influx().health()
        checks["influxdb"] = (h.status == "pass")
    except Exception:
        pass

    all_ok = all(checks.values())
    return {
        "status": "healthy" if all_ok else "degraded",
        "instance": config.INSTANCE_ID,
        "services": checks
    }

# ── Racine ────────────────────────────────────────────
@app.get("/", tags=["Système"])
async def root():
    return {
        "app": "Clinique Connectée API",
        "instance": config.INSTANCE_ID,
        "docs": "/docs",
        "health": "/health"
    }