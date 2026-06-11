"""
config/settings.py
==================
Centralise toutes les variables de configuration du projet.
Avantage : si tu changes un paramètre (ex: le modèle OpenAI),
tu le modifies une seule fois ici plutôt que partout dans le code.
"""

import os
from pathlib import Path
from dotenv import load_dotenv   # pip install python-dotenv

# ── Chargement des variables d'environnement ──────────────────────────────────
# Le fichier .env (ignoré par git) contient tes clés secrètes.
# load_dotenv() les charge dans os.environ pour qu'on puisse y accéder.
load_dotenv()

# ── Chemins du projet ─────────────────────────────────────────────────────────
# Path(__file__) → chemin absolu de CE fichier (settings.py)
# .parent.parent → remonte deux niveaux → racine du projet (docmind/)
BASE_DIR = Path(__file__).parent.parent

DATA_DIR        = BASE_DIR / "data"          # fichiers uploadés
CHROMA_DIR      = DATA_DIR / "chroma_db"     # base vectorielle persistée
SQLITE_PATH     = DATA_DIR / "docmind.db"    # historique des conversations
UPLOADS_DIR     = DATA_DIR / "uploads"       # documents bruts

# Crée automatiquement les dossiers s'ils n'existent pas encore
for d in [DATA_DIR, CHROMA_DIR, UPLOADS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── LLM (Large Language Model) ────────────────────────────────────────────────
# On supporte deux modes :
#   "openai"  → appelle l'API OpenAI (nécessite une clé)
#   "ollama"  → appelle un modèle local via Ollama (gratuit, tourne en local)
LLM_PROVIDER    = os.getenv("LLM_PROVIDER", "openai")   # valeur par défaut : openai
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL    = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "llama3.2:latest")

# ── Embeddings ────────────────────────────────────────────────────────────────
# Les embeddings transforment du texte en vecteurs numériques.
# "all-MiniLM-L6-v2" est un modèle léger qui tourne sur CPU.
# On en reparlera en S2 quand on intégrera ChromaDB.
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ── Découpage de texte (chunking) ─────────────────────────────────────────────
# Un document PDF est découpé en petits morceaux ("chunks") avant d'être indexé.
# CHUNK_SIZE    → nombre de caractères par chunk
# CHUNK_OVERLAP → chevauchement entre deux chunks consécutifs
#                 (évite de couper une phrase en plein milieu)
CHUNK_SIZE      = 1000
CHUNK_OVERLAP   = 200

# ── Classification ────────────────────────────────────────────────────────────
# Catégories que CamemBERT apprendra à reconnaître (S3)
DOC_CLASSES     = ["contrat", "facture", "rapport", "email", "autre"]
CLASSIFIER_MODEL_PATH = BASE_DIR / "models" / "camembert_classifier"

# ── Résumé ────────────────────────────────────────────────────────────────────
# Modèle BART fine-tuné pour la génération de résumés (S4)
SUMMARIZER_MODEL_PATH = BASE_DIR / "models" / "bart_summarizer"

# ── Interface Streamlit ───────────────────────────────────────────────────────
APP_TITLE       = "DocMind — Assistant documentaire IA"
MAX_UPLOAD_MB   = 20                           # taille max d'upload en Mo
ALLOWED_EXTENSIONS = [".pdf", ".docx"]
