"""
core/embeddings.py
==================
Transforme du texte en vecteurs numériques ("embeddings").

C'est quoi un embedding ?
  Un embedding projette un texte dans un espace vectoriel à haute dimension
  (ici 384 dimensions). Des textes proches sémantiquement ont des vecteurs proches.
  Exemple : "chien" et "canin" auront des vecteurs très similaires,
  même si les mots sont différents.

  C'est ce mécanisme qui rend la recherche sémantique possible :
  "Comment résilier mon contrat ?" trouvera un chunk parlant d'"annulation"
  même si le mot "résilier" n'y apparaît pas.

Modèle utilisé : all-MiniLM-L6-v2
  - Léger (~80 Mo), tourne sur CPU sans GPU
  - Produit des vecteurs de 384 dimensions
  - Entraîné sur des milliards de paires de phrases
  - Téléchargé automatiquement depuis HuggingFace au premier appel
"""

from sentence_transformers import SentenceTransformer
from config.settings import EMBEDDING_MODEL

# Singleton module-level : le modèle est chargé une seule fois par session
# et réutilisé à chaque appel, évitant un rechargement coûteux (~2s).
_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """Charge (ou retourne) le modèle SentenceTransformer."""
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Génère les embeddings pour une liste de textes.

    Args:
        texts: liste de chaînes à vectoriser

    Returns:
        Liste de vecteurs (chaque vecteur = liste de 384 floats).
        Même ordre que `texts`.
    """
    if not texts:
        return []

    model = get_model()
    # encode() retourne un numpy array (n_texts × 384)
    # .tolist() le convertit en liste Python standard pour ChromaDB
    return model.encode(texts, show_progress_bar=False).tolist()


def embed_text(text: str) -> list[float]:
    """Raccourci pour vectoriser un seul texte (ex : une requête utilisateur)."""
    return embed_texts([text])[0]
