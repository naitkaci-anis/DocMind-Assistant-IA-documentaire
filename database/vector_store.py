"""
database/vector_store.py
========================
Couche d'accès à ChromaDB — base de données vectorielle.
Même rôle que repository.py mais pour les embeddings.
"""

from __future__ import annotations

import chromadb
from config.settings import CHROMA_DIR
from models.search_result import SearchResult

COLLECTION_NAME = "documents"

_client: chromadb.PersistentClient | None = None


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return _client


def _get_collection():
    return _get_client().get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


class VectorStore:
    """CRUD pour la collection ChromaDB."""

    def add(
        self,
        doc_stem:   str,
        chunks:     list[str],
        embeddings: list[list[float]],
        metadata:   dict | None = None,
    ) -> int:
        """Indexe les chunks d'un document. Retourne le nombre de chunks ajoutés."""
        if not chunks:
            return 0

        coll      = _get_collection()
        base_meta = metadata or {}
        ids       = [f"{doc_stem}_chunk_{i}" for i in range(len(chunks))]
        metas     = [{**base_meta, "chunk_index": i, "doc_stem": doc_stem} for i in range(len(chunks))]

        coll.add(ids=ids, documents=chunks, embeddings=embeddings, metadatas=metas)
        return len(chunks)

    def search(self, query_embedding: list[float], n_results: int = 5) -> list[SearchResult]:
        """Recherche les chunks les plus proches du vecteur requête."""
        coll  = _get_collection()
        total = coll.count()
        if total == 0:
            return []

        results = coll.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, total),
            include=["documents", "distances", "metadatas"],
        )

        return [
            SearchResult(
                text=doc,
                score=round(1 - dist, 4),
                doc_filename=meta.get("filename", ""),
                original_name=meta.get("original_name", ""),
                chunk_index=meta.get("chunk_index", 0),
            )
            for doc, dist, meta in zip(
                results["documents"][0],
                results["distances"][0],
                results["metadatas"][0],
            )
        ]

    def delete(self, doc_stem: str) -> int:
        """Supprime tous les chunks d'un document. Retourne le nombre supprimé."""
        coll    = _get_collection()
        results = coll.get(where={"doc_stem": doc_stem})
        ids     = results["ids"]
        if ids:
            coll.delete(ids=ids)
        return len(ids)

    def count(self) -> int:
        return _get_collection().count()
