"""
config.py
=========
Centralise toute la configuration du projet.
Modifie ce fichier pour changer le modèle, les chemins, etc.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # Charge les variables depuis le fichier .env

# ── Sécurité ──────────────────────────────────────────────────────────────────
# Clé secrète pour les sessions (cookies signés) — change-la en production !
SECRET_KEY = os.getenv("SECRET_KEY", "docmind-super-secret-change-in-prod-2024")

# ── Dossiers ──────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
DATA_DIR    = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
VECTORS_DIR = DATA_DIR / "vectors"
DB_DIR      = DATA_DIR / "database"
DB_PATH     = DB_DIR   / "docmind.db"

# Crée automatiquement les dossiers s'ils n'existent pas
for folder in [UPLOADS_DIR, VECTORS_DIR, DB_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# ── LLM — Provider : "ollama" (local) ou "groq" (en ligne gratuit) ───────────
LLM_PROVIDER    = os.getenv("LLM_PROVIDER",    "ollama")   # "ollama" | "groq"

# Ollama (local)
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL",    "qwen2.5:0.5b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Groq (cloud gratuit — https://console.groq.com)
GROQ_API_KEY    = os.getenv("GROQ_API_KEY",    "")
GROQ_MODEL      = os.getenv("GROQ_MODEL",      "llama3-8b-8192")

# ── Embeddings ────────────────────────────────────────────────────────────────
# Modèle léger (384 dimensions), tourne sur CPU, pas de GPU requis
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ── Découpage de texte (chunking) ─────────────────────────────────────────────
CHUNK_SIZE    = 1000   # Nombre de caractères par chunk
CHUNK_OVERLAP = 200    # Chevauchement pour garder le contexte entre chunks

# ── Upload ────────────────────────────────────────────────────────────────────
MAX_FILE_SIZE_MB   = 20
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv"}
