"""
backend/vector_store.py
=======================
Interface avec ChromaDB — la base de données vectorielle.

ChromaDB stocke :
  - Les vecteurs (embeddings) de chaque chunk
  - Les textes originaux
  - Les métadonnées (nom du fichier, numéro de chunk...)

La recherche consiste à trouver les vecteurs les plus proches
du vecteur de la question (distance cosinus).
"""

import chromadb
from config import VECTORS_DIR

# ── Client ChromaDB (singleton) ───────────────────────────────────────────────
_client: chromadb.ClientAPI | None = None


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(VECTORS_DIR))
    return _client


def _get_collection():
    return _get_client().get_or_create_collection(
        name     = "documents",
        metadata = {"hnsw:space": "cosine"},
    )


# ── Opérations ────────────────────────────────────────────────────────────────

def vs_add_document(doc_id: int, chunks: list[str], embeddings: list[list[float]], original_name: str):
    """Indexe tous les chunks d'un document dans ChromaDB."""
    collection = _get_collection()

    ids = [f"doc_{doc_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {"doc_id": doc_id, "original_name": original_name, "chunk_index": i}
        for i in range(len(chunks))
    ]

    collection.add(
        ids        = ids,
        documents  = chunks,
        embeddings = embeddings,
        metadatas  = metadatas,
    )


def vs_search(
    query_embedding: list[float],
    n_results      : int = 5,
    user_doc_ids   : list[int] | None = None,
) -> list[dict]:
    """
    Recherche les chunks les plus proches du vecteur de la question.

    Args:
        user_doc_ids : restreint la recherche aux documents de l'utilisateur connecté.
                       Liste vide → aucun doc disponible → retourne [].
    """
    # L'utilisateur n'a aucun document → résultat vide immédiat
    if user_doc_ids is not None and len(user_doc_ids) == 0:
        return []

    collection = _get_collection()
    total = collection.count()
    if total == 0:
        return []

    # Filtre ChromaDB par doc_id si une liste est fournie
    where_filter = None
    if user_doc_ids is not None:
        if len(user_doc_ids) == 1:
            where_filter = {"doc_id": user_doc_ids[0]}
        else:
            where_filter = {"doc_id": {"$in": user_doc_ids}}

    query_kwargs = {
        "query_embeddings": [query_embedding],
        "n_results"       : min(n_results, total),
        "include"         : ["documents", "metadatas", "distances"],
    }
    if where_filter:
        query_kwargs["where"] = where_filter

    results = collection.query(**query_kwargs)

    chunks = []
    for i, text in enumerate(results["documents"][0]):
        distance = results["distances"][0][i]
        score    = round(1 - distance, 4)
        meta     = results["metadatas"][0][i]

        chunks.append({
            "text"         : text,
            "score"        : score,
            "score_pct"    : round(score * 100),
            "original_name": meta.get("original_name", "Inconnu"),
            "chunk_index"  : meta.get("chunk_index", 0),
        })

    return sorted(chunks, key=lambda x: x["score"], reverse=True)


def vs_delete_document(doc_id: int):
    """Supprime tous les chunks d'un document de ChromaDB."""
    collection = _get_collection()
    existing   = collection.get(where={"doc_id": doc_id})
    if existing["ids"]:
        collection.delete(ids=existing["ids"])


def vs_count() -> int:
    return _get_collection().count()


def vs_is_ready() -> bool:
    return vs_count() > 0
