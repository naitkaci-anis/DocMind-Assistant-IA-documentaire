"""
backend/auth.py
===============
Routes d'authentification : inscription, connexion, déconnexion.

Sécurité :
  - Les mots de passe sont hachés avec bcrypt (passlib)
  - La session est stockée dans un cookie HTTP signé (starlette SessionMiddleware)
  - Le cookie contient uniquement user_id + username (pas le mot de passe)
"""

import hashlib
import hmac
import secrets

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.database import (
    db_create_user, db_get_user_by_username,
    db_get_security_question, db_update_password,
)

router = APIRouter()


def _hash_password(password: str) -> str:
    """
    Hache un mot de passe avec PBKDF2-HMAC-SHA256 (stdlib Python).
    Format : "salt_hex:hash_hex"
    100 000 itérations = lent volontairement pour freiner les attaques brute-force.
    """
    salt = secrets.token_hex(16)
    key  = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}:{key.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    """Vérifie un mot de passe contre son hash stocké."""
    try:
        salt, key_hex = stored.split(":", 1)
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
        return hmac.compare_digest(key.hex(), key_hex)
    except Exception:
        return False


# ── Schémas ────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username          : str
    password          : str
    security_question : str = ""
    security_answer   : str = ""

class LoginRequest(BaseModel):
    username: str
    password: str

class ForgotQuestionRequest(BaseModel):
    username: str

class ForgotResetRequest(BaseModel):
    username    : str
    answer      : str
    new_password: str


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/register")
async def register(req: RegisterRequest, request: Request):
    """
    Crée un nouveau compte.
    Valide le nom d'utilisateur et le mot de passe, puis hache le mdp avant stockage.
    """
    username = req.username.strip()
    if len(username) < 3:
        raise HTTPException(400, "Nom d'utilisateur trop court (minimum 3 caractères)")
    if len(username) > 30:
        raise HTTPException(400, "Nom d'utilisateur trop long (maximum 30 caractères)")
    if len(req.password) < 6:
        raise HTTPException(400, "Mot de passe trop court (minimum 6 caractères)")

    if db_get_user_by_username(username):
        raise HTTPException(400, "Ce nom d'utilisateur est déjà pris")

    hashed          = _hash_password(req.password)
    answer_hash     = _hash_password(req.security_answer.strip().lower()) if req.security_answer.strip() else ""
    user            = db_create_user(username, hashed, req.security_question, answer_hash)

    request.session["user_id"]  = user["id"]
    request.session["username"] = user["username"]
    request.session["is_guest"] = False  # Efface le mode invité si actif

    return {"message": "Compte créé avec succès", "username": user["username"]}


@router.post("/login")
async def login(req: LoginRequest, request: Request):
    """
    Connecte un utilisateur.
    Vérifie le mot de passe haché, puis ouvre une session.
    """
    user = db_get_user_by_username(req.username.strip())

    # Même message d'erreur pour username inconnu et mauvais mot de passe
    # (évite de révéler si un compte existe)
    if not user or not _verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Identifiants incorrects")

    request.session["user_id"]  = user["id"]
    request.session["username"] = user["username"]
    request.session["is_guest"] = False  # Efface le mode invité si actif

    return {"message": "Connecté", "username": user["username"]}


@router.post("/logout")
async def logout(request: Request):
    """Efface la session (déconnexion)."""
    request.session.clear()
    return {"message": "Déconnecté"}


@router.post("/forgot/question")
async def forgot_get_question(req: ForgotQuestionRequest):
    """Étape 1 — retourne la question secrète pour un nom d'utilisateur."""
    question = db_get_security_question(req.username.strip())

    # None = utilisateur introuvable
    if question is None:
        raise HTTPException(404, "Aucun compte trouvé avec ce nom d'utilisateur")

    # "" = compte existant mais sans question secrète (compte ancien)
    if not question.strip():
        raise HTTPException(400,
            "Ce compte n'a pas de question secrète. "
            "Connecte-toi normalement, puis définis une question dans tes paramètres.")

    return {"question": question}


@router.post("/forgot/reset")
async def forgot_reset(req: ForgotResetRequest):
    """
    Étape 2 — vérifie la réponse et met à jour le mot de passe.
    La réponse est comparée en minuscules (insensible à la casse).
    """
    user = db_get_user_by_username(req.username.strip())
    if not user:
        raise HTTPException(404, "Compte introuvable")

    stored_answer_hash = user.get("security_answer_hash", "")
    if not stored_answer_hash:
        raise HTTPException(400, "Ce compte n'a pas de question secrète")

    if not _verify_password(req.answer.strip().lower(), stored_answer_hash):
        raise HTTPException(401, "Réponse incorrecte")

    if len(req.new_password) < 6:
        raise HTTPException(400, "Mot de passe trop court (minimum 6 caractères)")

    new_hash = _hash_password(req.new_password)
    db_update_password(user["id"], new_hash)
    return {"message": "Mot de passe mis à jour avec succès"}


@router.get("/me")
async def me(request: Request):
    """Retourne les infos de l'utilisateur connecté, ou 401 si non connecté."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(401, "Non connecté")
    return {
        "user_id" : user_id,
        "username": request.session.get("username"),
    }
