"""
backend/llm.py
==============
Interface LLM — supporte deux modes :
  - "ollama" : LLM local (développement sur ton PC)
  - "groq"   : API Groq cloud gratuite (hébergement en ligne)

Choix du mode via la variable d'environnement LLM_PROVIDER dans .env
"""

from typing import Generator
from config import LLM_PROVIDER, OLLAMA_MODEL, GROQ_API_KEY, GROQ_MODEL


def stream_response(
    messages   : list[dict],
    temperature: float = 0.3,
) -> Generator[str, None, None]:
    """
    Génère une réponse en streaming token par token.
    Route automatiquement vers Ollama ou Groq selon LLM_PROVIDER.
    """
    if LLM_PROVIDER == "groq":
        yield from _stream_groq(messages, temperature)
    else:
        yield from _stream_ollama(messages, temperature)


def _stream_ollama(messages: list[dict], temperature: float) -> Generator[str, None, None]:
    """Streaming via Ollama local."""
    import ollama
    stream = ollama.chat(
        model    = OLLAMA_MODEL,
        messages = messages,
        stream   = True,
        options  = {"temperature": temperature},
    )
    for chunk in stream:
        token = chunk.get("message", {}).get("content", "")
        if token:
            yield token


def _stream_groq(messages: list[dict], temperature: float) -> Generator[str, None, None]:
    """
    Streaming via API Groq (compatible OpenAI).
    Nécessite : pip install openai
    Clé gratuite sur https://console.groq.com
    """
    from openai import OpenAI

    if not GROQ_API_KEY:
        yield "❌ GROQ_API_KEY manquante dans .env"
        return

    client = OpenAI(
        api_key  = GROQ_API_KEY,
        base_url = "https://api.groq.com/openai/v1",
    )

    stream = client.chat.completions.create(
        model       = GROQ_MODEL,
        messages    = messages,
        temperature = temperature,
        stream      = True,
    )

    for chunk in stream:
        token = chunk.choices[0].delta.content or ""
        if token:
            yield token


def list_models() -> list[str]:
    """Retourne les modèles disponibles selon le provider actif."""
    if LLM_PROVIDER == "groq":
        return [GROQ_MODEL]
    try:
        import ollama
        response = ollama.list()
        return [m.model for m in response.models]
    except Exception:
        return [OLLAMA_MODEL]
