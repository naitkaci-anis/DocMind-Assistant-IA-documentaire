"""
backend/document_service.py
============================
Couche SERVICE — orchestration du pipeline document.

Responsabilités :
  - Sauvegarder le fichier sur le disque
  - Extraire le texte (core/loader)
  - Découper en chunks (core/splitter)
  - Générer les embeddings (core/embeddings)
  - Indexer dans ChromaDB (database/vector_store)
  - Persister les métadonnées en SQLite (database/repository)
  - Supprimer un document (disque + ChromaDB + SQLite)

La vue (pages/) appelle ce service et n'a aucune logique métier.
"""

from __future__ import annotations
from datetime import datetime
from pathlib import Path

from config.settings import UPLOADS_DIR
from core.loader import load_document
from core.splitter import split_text
from core.embeddings import embed_texts
from database.repository import DocumentRepository
from database.vector_store import VectorStore
from models.document import Document, DocumentStatus


class DocumentService:

    def __init__(self):
        self._repo   = DocumentRepository()
        self._vstore = VectorStore()

    # ── Sauvegarde ────────────────────────────────────────────────────────────

    def save_file(self, file_bytes: bytes, original_name: str) -> Path:
        """
        Sauvegarde les bytes d'un fichier uploadé dans UPLOADS_DIR.
        Ajoute un timestamp au nom pour éviter les collisions.

        Returns:
            Path absolu vers le fichier sauvegardé.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = Path(original_name).stem
        ext  = Path(original_name).suffix
        dest = UPLOADS_DIR / f"{stem}_{timestamp}{ext}"
        dest.write_bytes(file_bytes)
        return dest

    # ── Pipeline complet ──────────────────────────────────────────────────────

    def process(
        self,
        saved_path:    Path,
        original_name: str,
        file_size_mb:  float,
    ) -> Document:
        """
        Exécute le pipeline complet sur un fichier déjà sauvegardé.

        Étapes :
          1. Extraction du texte
          2. Découpage en chunks
          3. Génération des embeddings
          4. Indexation ChromaDB
          5. Enregistrement SQLite

        Returns:
            Document avec statut INDEXED et statistiques remplies.

        Raises:
            ValueError  : fichier vide, PDF scanné, extension non supportée
            Exception   : toute erreur d'embedding ou de base de données
        """
        # 1 — Extraction
        texte = load_document(saved_path)

        # 2 — Découpage
        chunks = split_text(texte)

        # 3 — Embeddings
        embeddings = embed_texts(chunks)

        # 4 — ChromaDB
        doc_stem   = saved_path.stem
        nb_indexed = self._vstore.add(
            doc_stem=doc_stem,
            chunks=chunks,
            embeddings=embeddings,
            metadata={
                "filename":      saved_path.name,
                "original_name": original_name,
                "extension":     saved_path.suffix,
            },
        )

        # 5 — SQLite
        doc = Document(
            filename=saved_path.name,
            original_name=original_name,
            file_path=str(saved_path),
            file_size_mb=file_size_mb,
            extension=saved_path.suffix,
        )
        doc_id  = self._repo.create(doc)
        self._repo.mark_indexed(doc_id, nb_chunks=nb_indexed, nb_chars=len(texte))

        doc.id        = doc_id
        doc.nb_chunks = nb_indexed
        doc.nb_chars  = len(texte)
        doc.status    = DocumentStatus.INDEXED

        return doc

    # ── Lecture ───────────────────────────────────────────────────────────────

    def list_all(self) -> list[Document]:
        """Retourne tous les documents triés du plus récent au plus ancien."""
        return self._repo.get_all()

    def total_chunks(self) -> int:
        """Nombre total de chunks dans ChromaDB."""
        return self._vstore.count()

    # ── Suppression ───────────────────────────────────────────────────────────

    def delete(self, filename: str) -> None:
        """
        Supprime un document des 3 endroits :
          1. Fichier sur le disque
          2. Chunks dans ChromaDB
          3. Ligne dans SQLite
        """
        # Disque
        target = UPLOADS_DIR / filename
        if target.exists():
            target.unlink()

        # ChromaDB
        self._vstore.delete(Path(filename).stem)

        # SQLite
        self._repo.delete(filename)
