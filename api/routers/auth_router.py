"""
routers/auth_router.py — Login JWT
"""
from fastapi import APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends
from pydantic import BaseModel
import auth, config

router = APIRouter(prefix="/auth", tags=["Authentification"])

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    nom: str

@router.post("/login", response_model=Token, summary="Connexion — obtenir un JWT")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = auth.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth.create_access_token(
        data={"sub": user["username"], "role": user["role"]}
    )
    return Token(
        access_token=token,
        token_type="bearer",
        role=user["role"],
        nom=user["nom"]
    )

@router.get("/me", summary="Profil utilisateur courant")
async def me(current_user=Depends(auth.get_current_user)):
    return {
        "username": current_user.username,
        "role": current_user.role,
        "permissions": auth.ROLE_PERMISSIONS.get(current_user.role, [])
    }
