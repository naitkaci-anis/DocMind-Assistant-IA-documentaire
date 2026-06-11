"""
models/document.py
==================
Modèle de données Document — couche MODEL du MVC.

Aucune dépendance externe : juste des dataclasses Python.
La couche base de données et les services manipulent ces objets.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class DocumentStatus(str, Enum):
    PENDING = "pending"
    INDEXED = "indexed"
    ERROR   = "error"


@dataclass
class Document:
    filename:      str
    original_name: str
    file_path:     str
    file_size_mb:  float
    extension:     str
    id:            int | None      = None
    nb_chunks:     int             = 0
    nb_chars:      int             = 0
    uploaded_at:   datetime        = field(default_factory=datetime.utcnow)
    status:        DocumentStatus  = DocumentStatus.PENDING

    @classmethod
    def from_dict(cls, d: dict) -> Document:
        return cls(
            id=d["id"],
            filename=d["filename"],
            original_name=d["original_name"],
            file_path=d["file_path"],
            file_size_mb=d["file_size_mb"],
            extension=d["extension"],
            nb_chunks=d["nb_chunks"],
            nb_chars=d["nb_chars"],
            uploaded_at=d["uploaded_at"],
            status=d["status"],
        )

    @property
    def stem(self) -> str:
        """Nom sans extension — utilisé comme clé dans ChromaDB."""
        return Path(self.filename).stem

    @property
    def is_indexed(self) -> bool:
        return self.status == DocumentStatus.INDEXED
