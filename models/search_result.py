"""
models/search_result.py
=======================
Modèle de données pour un résultat de recherche sémantique.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class SearchResult:
    text:          str
    score:         float   # similarité cosinus [0..1], 1 = parfaite correspondance
    doc_filename:  str
    original_name: str
    chunk_index:   int

    @property
    def score_pct(self) -> int:
        """Score en pourcentage arrondi."""
        return round(self.score * 100)

    @property
    def relevance_label(self) -> str:
        if self.score >= 0.80:
            return "Très pertinent"
        if self.score >= 0.60:
            return "Pertinent"
        if self.score >= 0.40:
            return "Possible"
        return "Faible"
