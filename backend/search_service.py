"""
backend/search_service.py
==========================
Couche SERVICE — recherche sémantique (Semaine 3).

Principe :
  1. Convertir la question utilisateur en vecteur (embedding)
  2. Interroger ChromaDB pour trouver les chunks les plus proches
  3. Retourner les résultats triés par score de similarité
"""

from __future__ import annotations

from core.embeddings import embed_text
from database.vector_store import VectorStore
from models.search_result import SearchResult


class SearchService:

    def __init__(self):
        self._vstore = VectorStore()

    def search(self, query: str, n_results: int = 5) -> list[SearchResult]:
        """
        Recherche les chunks les plus pertinents pour une question.

        Étapes :
          1. Embed la question (même modèle que les documents)
          2. Query ChromaDB par similarité cosinus
          3. Retourne les résultats triés par score décroissant

        Args:
            query    : question en langage naturel
            n_results: nombre max de résultats à retourner

        Returns:
            Liste de SearchResult triés du plus au moins pertinent.
            Liste vide si aucun document indexé.
        """
        if not query.strip():
            return []

        query_vector = embed_text(query)
        results      = self._vstore.search(query_vector, n_results=n_results)

        # Tri défensif par score décroissant (ChromaDB retourne déjà trié,
        # mais on garantit l'ordre côté service)
        return sorted(results, key=lambda r: r.score, reverse=True)

    def is_ready(self) -> bool:
        """Retourne True si au moins un document est indexé dans ChromaDB."""
        return self._vstore.count() > 0
