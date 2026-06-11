"""
backend/llm_service.py
=======================
Interface avec Ollama — génération de texte en streaming.

Deux modes :
  - RAG one-shot  : question + chunks → réponse
  - Chat          : historique de messages + chunks → réponse conversationnelle
"""

from __future__ import annotations
from typing import Generator

import ollama

from config.settings import OLLAMA_MODEL, OLLAMA_BASE_URL
from models.search_result import SearchResult
from models.message import Message


# ── Prompt RAG ────────────────────────────────────────────────────────────────

def _build_rag_context(results: list[SearchResult]) -> str:
    parts = []
    for i, r in enumerate(results, 1):
        parts.append(
            f"[Source {i} — {r.original_name}, passage #{r.chunk_index + 1}]\n{r.text}"
        )
    return "\n\n".join(parts)


_SYSTEM_RAG = """Tu es DocMind, un assistant IA expert en analyse documentaire.
Règles strictes :
- Réponds UNIQUEMENT à partir des extraits fournis.
- Si l'information est absente des extraits, réponds : "Je ne trouve pas cette information dans les documents fournis."
- Cite les sources utilisées à la fin de ta réponse (nom du fichier).
- Sois concis, précis et structuré.
- Réponds toujours en français."""

_SYSTEM_CHAT = """Tu es DocMind, un assistant IA de gestion documentaire.
Tu as accès à une base de documents indexés.
Réponds en français, de façon claire et professionnelle.
Si une question porte sur les documents, utilise le contexte fourni.
Sinon, réponds de façon générale."""


# ── Fonctions de génération ───────────────────────────────────────────────────

def stream_rag_answer(
    question: str,
    results:  list[SearchResult],
    model:    str | None = None,
) -> Generator[str, None, None]:
    """
    Génère une réponse RAG en streaming.

    Construit un prompt avec les chunks pertinents et appelle Ollama.
    Retourne un générateur de tokens pour st.write_stream().

    Args:
        question: question de l'utilisateur
        results : chunks trouvés par ChromaDB
        model   : modèle Ollama (défaut : settings.OLLAMA_MODEL)
    """
    model = model or OLLAMA_MODEL
    context = _build_rag_context(results)

    prompt = f"""{_SYSTEM_RAG}

=== EXTRAITS DE DOCUMENTS ===
{context}

=== QUESTION ===
{question}

=== RÉPONSE ==="""

    stream = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        options={"temperature": 0.1},   # température basse = réponses factuelles
    )

    for chunk in stream:
        content = chunk.get("message", {}).get("content", "")
        if content:
            yield content


def stream_chat_answer(
    history:  list[Message],
    question: str,
    results:  list[SearchResult] | None = None,
    model:    str | None = None,
) -> Generator[str, None, None]:
    """
    Génère une réponse conversationnelle en streaming.

    Inclut l'historique des messages pour maintenir le contexte,
    et injecte les chunks RAG si des documents pertinents sont trouvés.

    Args:
        history : messages précédents de la conversation
        question: nouvelle question de l'utilisateur
        results : chunks RAG (optionnel)
        model   : modèle Ollama
    """
    model = model or OLLAMA_MODEL

    messages: list[dict] = []

    # Message système
    if results:
        context = _build_rag_context(results)
        system = f"""{_SYSTEM_CHAT}

=== CONTEXTE DOCUMENTAIRE DISPONIBLE ===
{context}"""
    else:
        system = _SYSTEM_CHAT

    messages.append({"role": "system", "content": system})

    # Historique (max 10 derniers messages pour rester dans le contexte)
    for msg in history[-10:]:
        messages.append(msg.to_ollama())

    # Nouvelle question
    messages.append({"role": "user", "content": question})

    stream = ollama.chat(
        model=model,
        messages=messages,
        stream=True,
        options={"temperature": 0.3},
    )

    for chunk in stream:
        content = chunk.get("message", {}).get("content", "")
        if content:
            yield content


def list_models() -> list[str]:
    """Retourne les modèles Ollama disponibles localement."""
    try:
        response = ollama.list()
        return [m.model for m in response.models]
    except Exception:
        return [OLLAMA_MODEL]
