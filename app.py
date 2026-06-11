"""
app.py
======
Point d'entrée de DocMind — serveur FastAPI.

Pour lancer l'app :
    python -m uvicorn app:app --reload --port 8000
Puis ouvre http://localhost:8000
"""

import hashlib
import secrets
import uuid as _uuid

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
import ollama as _ollama

from config import SECRET_KEY
from backend.database import init_db, db_create_user
from backend.auth    import router as auth_router
from backend.upload  import router as upload_router
from backend.rag     import router as rag_router
from backend.chat    import router as chat_router
from backend.summary import router as summary_router

# ── Création de l'app ─────────────────────────────────────────────────────────
app = FastAPI(
    title       = "DocMind",
    description = "Assistant IA documentaire — RAG avec Ollama",
    version     = "2.1.0",
    docs_url    = "/docs",
)

# ── Middleware sessions (cookie signé) ────────────────────────────────────────
# Doit être ajouté EN PREMIER pour que request.session soit disponible partout
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, https_only=False)

# ── Fichiers statiques (CSS, JS, images) ──────────────────────────────────────
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# ── Moteur de templates HTML (Jinja2) ─────────────────────────────────────────
templates = Jinja2Templates(directory="frontend/templates")

# ── Routes API ─────────────────────────────────────────────────────────────────
app.include_router(auth_router,    prefix="/api/auth",    tags=["Auth"])
app.include_router(upload_router,  prefix="/api/upload",  tags=["Documents"])
app.include_router(rag_router,     prefix="/api/rag",     tags=["Recherche"])
app.include_router(chat_router,    prefix="/api/chat",    tags=["Chat"])
app.include_router(summary_router, prefix="/api/summary", tags=["Résumés"])


@app.on_event("startup")
async def on_startup():
    init_db()


# ── Santé / Statut Ollama ──────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    try:
        result = _ollama.list()
        models = [m.model for m in result.models]
        return {"ollama": "ok", "models": models}
    except Exception:
        return JSONResponse(status_code=503, content={"ollama": "error", "models": []})


# ── Helper : vérifie si connecté ──────────────────────────────────────────────

def _is_logged_in(request: Request) -> bool:
    return bool(request.session.get("user_id"))


def _user_context(request: Request) -> dict:
    """Contexte Jinja2 commun à toutes les pages protégées."""
    return {
        "username": request.session.get("username", ""),
        "user_id" : request.session.get("user_id"),
        "is_guest": request.session.get("is_guest", False),
    }


# ── Page publique d'accueil ───────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def page_landing(request: Request):
    """Landing page publique. Redirige vers /dashboard si déjà connecté."""
    if _is_logged_in(request):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "landing.html")


@app.get("/try", response_class=HTMLResponse)
async def page_try(request: Request):
    """
    Crée une session invité temporaire (sans inscription).
    L'invité peut tester avec 3 documents max.
    """
    if _is_logged_in(request):
        return RedirectResponse("/dashboard", status_code=302)

    # Génère un identifiant invité unique
    guest_token    = _uuid.uuid4().hex[:10]
    guest_username = f"invité_{guest_token}"

    # Mot de passe aléatoire inutilisable (l'invité ne peut pas se connecter manuellement)
    rand_pwd = secrets.token_hex(16)
    salt     = secrets.token_hex(8)
    key      = hashlib.pbkdf2_hmac("sha256", rand_pwd.encode(), salt.encode(), 1000)
    fake_hash = f"{salt}:{key.hex()}"

    user = db_create_user(guest_username, fake_hash)

    request.session["user_id"]  = user["id"]
    request.session["username"] = guest_username
    request.session["is_guest"] = True

    return RedirectResponse("/dashboard", status_code=302)


# ── Pages publiques (auth) ────────────────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
async def page_login(request: Request):
    # Un invité peut accéder à la page login pour se connecter avec un vrai compte
    is_guest = request.session.get("is_guest", False)
    if _is_logged_in(request) and not is_guest:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "login.html")

@app.get("/register", response_class=HTMLResponse)
async def page_register(request: Request):
    is_guest = request.session.get("is_guest", False)
    if _is_logged_in(request) and not is_guest:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "register.html")

@app.get("/forgot-password", response_class=HTMLResponse)
async def page_forgot_password(request: Request):
    return templates.TemplateResponse(request, "forgot_password.html")


# ── Pages protégées (redirige vers / si non connecté) ────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
async def page_home(request: Request):
    if not _is_logged_in(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request, "index.html", _user_context(request))

@app.get("/documents", response_class=HTMLResponse)
async def page_documents(request: Request):
    if not _is_logged_in(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request, "documents.html", _user_context(request))

@app.get("/search", response_class=HTMLResponse)
async def page_search(request: Request):
    if not _is_logged_in(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request, "search.html", _user_context(request))

@app.get("/chat", response_class=HTMLResponse)
async def page_chat(request: Request):
    if not _is_logged_in(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request, "chat.html", _user_context(request))

@app.get("/summary", response_class=HTMLResponse)
async def page_summary(request: Request):
    if not _is_logged_in(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request, "summary.html", _user_context(request))


# ── Lancement direct ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
