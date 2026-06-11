
# DocMind — Assistant IA documentaire

> Dépose tes PDF et Word, pose des questions en langage naturel, obtiens des réponses générées par IA avec les sources citées.

---

## Fonctionnalités

| Page | Description | Statut |
|---|---|---|
| 🏠 **Dashboard** | Métriques, modules, guide de démarrage | ✅ Disponible |
| 📄 **Documents** | Import PDF/Word/TXT/MD/CSV, indexation automatique | ✅ Disponible |
| 🔍 **Recherche** | Question → réponse RAG + sources citées | ✅ Disponible |
| 💬 **Chat** | Chat conversationnel avec historique persisté | ✅ Disponible |
| 📝 **Résumés** | Résumé complet, court ou points clés, export TXT | ✅ Disponible |

- **Thème clair / sombre** commutable sur toutes les pages (persisté dans localStorage)
- **Interface premium** : fond galaxie animé, aurora boréale dans le chat, glassmorphism

---

## Architecture

```
DocMind/
│
├── app.py                          # Point d'entrée FastAPI — routes + Jinja2
│
├── backend/                        # Routers FastAPI
│   ├── auth.py                     # Authentification (login, register, logout)
│   ├── chat.py                     # Conversations + messages (SSE streaming)
│   ├── rag.py                      # Documents + recherche sémantique
│   ├── summary.py                  # Résumés automatiques
│   ├── upload.py                   # Upload de fichiers
│   ├── chat_service.py             # Orchestration chat + historique
│   ├── document_service.py         # Pipeline upload → extraction → embedding
│   ├── llm_service.py              # Interface Groq (streaming SSE)
│   └── search_service.py           # Recherche sémantique ChromaDB
│
├── core/                           # Utilitaires bas niveau
│   ├── loader.py                   # Extraction texte (PDF via PyMuPDF, DOCX)
│   ├── splitter.py                 # Découpage en chunks (sliding window)
│   └── embeddings.py               # Embeddings SentenceTransformers
│
├── models/                         # Dataclasses (Document, Message, SearchResult…)
│
├── database/                       # Persistance
│   ├── repository.py               # SQLite — documents (SQLAlchemy ORM)
│   ├── vector_store.py             # ChromaDB — vecteurs et recherche
│   └── chat_repository.py          # SQLite — conversations et messages
│
├── config/
│   └── settings.py                 # Variables de configuration
│
├── frontend/
│   ├── templates/                  # Pages Jinja2 (base.html + 6 pages)
│   └── static/
│       ├── css/style.css           # Design system complet (tokens CSS, thèmes)
│       └── js/
│           ├── stars.js            # Fond galaxie animé (canvas)
│           ├── theme.js            # Système thème clair/sombre
│           ├── chat.js             # Logique chat (SSE, conversations)
│           └── upload-widget.js    # Widget upload drag & drop
│
├── tests/
│   └── test_settings.py
│
├── .env                            # Variables secrètes (non commité)
├── requirements.txt
└── .gitignore
```

---

## Stack technique

| Composant | Technologie |
|---|---|
| Backend | **FastAPI** + Uvicorn |
| Templates | **Jinja2** (HTML/CSS/JS pur — pas de React) |
| LLM | **Groq** cloud — `llama-3.1-8b-instant` (rapide, gratuit) |
| Embeddings | SentenceTransformers — `all-MiniLM-L6-v2` |
| Base vectorielle | **ChromaDB** (cosine distance) |
| Base relationnelle | **SQLite** via SQLAlchemy 2.0 |
| Extraction PDF | PyMuPDF (`fitz`) |
| Extraction DOCX | python-docx |
| Streaming | **SSE** (Server-Sent Events) |
| Design | Glassmorphism, fond galaxie canvas, aurora boréale, thème clair/sombre |

---

## Prérequis

- **Windows 10/11**
- **Python 3.11+**
- **Git**
- Un compte **Groq** gratuit → [console.groq.com](https://console.groq.com) pour obtenir une clé API

---

## Installation

### 1. Cloner le dépôt

```powershell
git clone <url-du-repo>
cd "DocMind — Assistant IA documentaire"
```

### 2. Créer l'environnement virtuel

```powershell
python -m venv venv
venv\Scripts\activate
```

### 3. Installer les dépendances

```powershell
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

Crée un fichier `.env` à la racine :

```env
GROQ_API_KEY=gsk_...        # Ta clé Groq (obligatoire)
SECRET_KEY=change_moi       # Clé secrète pour les sessions
```

---

## Lancer l'application

```powershell
venv\Scripts\activate
python -m uvicorn app:app --reload
```

L'application est accessible sur **[http://localhost:8000](http://localhost:8000)**

> Si le port 8000 est occupé : `python -m uvicorn app:app --reload --port 8001`

---

## Utilisation

### Importer des documents

1. Va dans **Documents**
2. Glisse-dépose un PDF, Word, TXT, Markdown ou CSV
3. L'indexation est automatique : extraction → chunking → embeddings → ChromaDB

### Recherche RAG

1. Va dans **Recherche**
2. Tape ta question en langage naturel
3. DocMind retrouve les passages pertinents et génère une réponse sourcée via Groq

### Chat conversationnel

1. Va dans **Chat**
2. Crée une nouvelle conversation
3. Pose tes questions — l'IA garde le contexte de toute la conversation
4. Les réponses arrivent en streaming (token par token)

### Résumés automatiques

1. Va dans **Résumés**
2. Sélectionne un document et un mode (complet / court / points clés)
3. Exporte le résumé en `.txt`

---

## Thème clair / sombre

Le bouton ☀️/🌙 est disponible :
- Dans la **sidebar** (pages Dashboard, Documents, Recherche, Chat, Résumés)
- Dans la **navbar** de la page d'accueil
- En bas à droite sur les pages **Connexion** et **Inscription**

Le choix est mémorisé dans `localStorage` et respecte `prefers-color-scheme` si aucune préférence n'est enregistrée.

---

## Configuration avancée

Paramètres dans `config/settings.py` :

| Variable | Défaut | Description |
|---|---|---|
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Modèle LLM Groq |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Modèle d'embeddings |
| `CHUNK_SIZE` | `1000` | Taille des chunks (caractères) |
| `CHUNK_OVERLAP` | `200` | Chevauchement entre chunks |
| `MAX_UPLOAD_MB` | `20` | Taille max des fichiers |

---

## Tests

```powershell
venv\Scripts\activate
python -m pytest tests -v
```

---

## Dépannage

**`GROQ_API_KEY` manquante**
```
KeyError: 'GROQ_API_KEY'
```
Vérifie que ton fichier `.env` existe à la racine avec la bonne clé.

**Port 8000 déjà utilisé (WinError 10013)**
```powershell
python -m uvicorn app:app --reload --port 8001
```

**`pymupdf` échoue à l'installation**
Installe Visual Studio Build Tools avec "Desktop development with C++".

---

## Roadmap

- [x] Upload multi-format + pipeline RAG complet
- [x] Recherche sémantique avec sources
- [x] Chat conversationnel SSE streaming
- [x] Résumés automatiques (complet / court / points clés)
- [x] Authentification utilisateurs (register / login / sessions)
- [x] Interface premium glassmorphism + fond galaxie animé
- [x] Aurora boréale animée dans le chat
- [x] Thème clair / sombre (toutes les pages)
- [ ] Export conversations en PDF
- [ ] Classification automatique des documents
- [ ] Recherche multi-documents avec filtres

---

## Auteur

**ANIS-NAIT-KACI** — [anisnaitkaci831@gmail.com](mailto:anisnaitkaci831@gmail.com)
=======
# DocMind-Assistant-IA-documentaire
