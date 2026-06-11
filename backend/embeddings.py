"""
backend/embeddings.py
=====================
Génération d'embeddings (représentations vectorielles du texte).

Qu'est-ce qu'un embedding ?
  Un embedding transforme du texte en une liste de nombres (vecteur).
  Deux textes au sens proche ont des vecteurs mathématiquement proches.

  "Bonjour"  →  [0.23, -0.45, 0.12, ...]   (384 nombres)
  "Hello"    →  [0.25, -0.43, 0.11, ...]   ← vecteur proche !
  "Pizza"    →  [-0.81, 0.32, -0.67, ...]  ← vecteur éloigné

C'est ce qui rend la recherche "sémantique" possible :
on cherche par sens, pas par mots-clés.

Modèle utilisé : all-MiniLM-L6-v2
  - Léger (22M paramètres), rapide, tourne sur CPU
  - 384 dimensions
  - Multilingue (français supporté)
"""

from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL

# Singleton : le modèle est chargé une seule fois en mémoire
# (le charger à chaque appel serait trop lent)
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Retourne le modèle, le charge la première fois."""
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed_text(text: str) -> list[float]:
    """
    Encode un texte en vecteur numérique.

    Args:
        text : texte à encoder
    Returns:
        liste de 384 floats
    """
    vector = _get_model().encode(text, normalize_embeddings=True)
    return vector.tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Encode plusieurs textes en une seule passe (plus efficace qu'un par un).

    Args:
        texts : liste de textes à encoder
    Returns:
        liste de vecteurs (un vecteur par texte)
    """
    vectors = _get_model().encode(texts, normalize_embeddings=True, batch_size=32)
    return vectors.tolist()
