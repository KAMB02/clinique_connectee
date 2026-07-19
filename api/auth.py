"""
auth.py — JWT + RBAC
Rôles : admin > medecin > controleur > technicien
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, Request, Query
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
import config

# ── Crypto ────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ── Permissions par rôle ──────────────────────────────
ROLE_PERMISSIONS = {
    "admin":       ["patients", "alertes", "stats", "chambres", "securite", "energie", "admin"],
    "medecin":     ["patients", "alertes", "stats", "chambres"],
    "controleur":  ["alertes", "securite", "chambres"],
    "technicien":  ["stats", "energie", "chambres"],
}

class TokenData:
    def __init__(self, username: str, role: str):
        self.username = username
        self.role = role

# ══════════════════════════════════════════════════════
#  Fonctions JWT
# ══════════════════════════════════════════════════════
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=config.JWT_EXPIRE_MIN))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)

def decode_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role", "")
        if not username:
            raise HTTPException(status_code=401, detail="Token invalide")
        return TokenData(username=username, role=role)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expiré ou invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )

# ══════════════════════════════════════════════════════
#  Dépendances FastAPI
# ══════════════════════════════════════════════════════
async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    return decode_token(token)

def require_role(*required_permissions: str):
    async def checker(current_user: TokenData = Depends(get_current_user)):
        user_perms = ROLE_PERMISSIONS.get(current_user.role, [])
        if not any(p in user_perms for p in required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès refusé — rôle '{current_user.role}' insuffisant"
            )
        return current_user
    return checker

# ══════════════════════════════════════════════════════
#  Auth pour EventSource (SSE) — le navigateur ne peut pas
#  envoyer de header Authorization custom sur un flux SSE,
#  donc on accepte aussi le JWT via ?token=... en query string.
#  Le header Authorization reste supporté en priorité pour
#  les autres clients (curl, tests, etc.).
# ══════════════════════════════════════════════════════
async def get_current_user_sse(request: Request, token: Optional[str] = Query(default=None)) -> TokenData:
    jwt_token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        jwt_token = auth_header.split(" ", 1)[1]
    elif token:
        jwt_token = token

    if not jwt_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token manquant (header Authorization ou ?token=)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_token(jwt_token)

def require_role_sse(*required_permissions: str):
    async def checker(current_user: TokenData = Depends(get_current_user_sse)):
        user_perms = ROLE_PERMISSIONS.get(current_user.role, [])
        if not any(p in user_perms for p in required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès refusé — rôle '{current_user.role}' insuffisant"
            )
        return current_user
    return checker

# ══════════════════════════════════════════════════════
#  Rate limiting via Redis
# ══════════════════════════════════════════════════════
def check_rate_limit(redis_client, identifier: str) -> None:
    key = f"ratelimit:{identifier}"
    try:
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, config.RATE_LIMIT_WINDOW)
        results = pipe.execute()
        if results[0] > config.RATE_LIMIT_MAX:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Trop de requêtes — limite {config.RATE_LIMIT_MAX}/min atteinte"
            )
    except HTTPException:
        raise
    except Exception:
        pass

# ══════════════════════════════════════════════════════
#  Utilisateurs de démo — hash pré-calculé au chargement
#  bcrypt hash de "clinique2026"
# ══════════════════════════════════════════════════════
_PWD_HASH = None

def _get_pwd_hash():
    """Hash calculé une seule fois au premier appel."""
    global _PWD_HASH
    if _PWD_HASH is None:
        _PWD_HASH = hash_password("clinique2026")
    return _PWD_HASH

def _build_users():
    h = _get_pwd_hash()
    return {
        "medecin1":    {"password_hash": h, "role": "medecin",    "nom": "Dr. Kouassi"},
        "medecin2":    {"password_hash": h, "role": "medecin",    "nom": "Dr. N'Guessan"},
        "infirmier1":  {"password_hash": h, "role": "medecin",    "nom": "Inf. Coulibaly"},
        "controleur1": {"password_hash": h, "role": "controleur", "nom": "Sgt. Konaté"},
        "technicien1": {"password_hash": h, "role": "technicien", "nom": "Tech. Yao"},
        "admin":       {"password_hash": h, "role": "admin",      "nom": "Administrateur"},
    }

def authenticate_user(username: str, password: str) -> Optional[dict]:
    users = _build_users()
    user = users.get(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return {"username": username, **user}
