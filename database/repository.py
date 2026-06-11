"""
database/repository.py
======================
Couche d'accès aux données — SQLite via SQLAlchemy.
Implémente le pattern Repository : la logique métier ne connaît
que les méthodes CRUD, pas le SQL ni l'ORM.
"""

from __future__ import annotations
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session

from config.settings import SQLITE_PATH
from models.document import Document, DocumentStatus


# ── ORM ───────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


class DocumentRow(Base):
    __tablename__ = "documents"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    filename      = Column(String,  nullable=False)
    original_name = Column(String,  nullable=False)
    file_path     = Column(String,  nullable=False)
    file_size_mb  = Column(Float,   nullable=False)
    extension     = Column(String,  nullable=False)
    nb_chunks     = Column(Integer, default=0)
    nb_chars      = Column(Integer, default=0)
    uploaded_at   = Column(DateTime, default=datetime.utcnow)
    status        = Column(String,  default=DocumentStatus.PENDING)


# ── Engine singleton ──────────────────────────────────────────────────────────

_engine = None

def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(f"sqlite:///{SQLITE_PATH}")
        Base.metadata.create_all(_engine)
    return _engine


# ── Conversions ───────────────────────────────────────────────────────────────

def _row_to_model(row: DocumentRow) -> Document:
    return Document(
        id=row.id,
        filename=row.filename,
        original_name=row.original_name,
        file_path=row.file_path,
        file_size_mb=row.file_size_mb,
        extension=row.extension,
        nb_chunks=row.nb_chunks,
        nb_chars=row.nb_chars,
        uploaded_at=row.uploaded_at,
        status=row.status,
    )


# ── Repository ────────────────────────────────────────────────────────────────

class DocumentRepository:
    """CRUD pour la table documents."""

    def create(self, doc: Document) -> int:
        """Insère un document (status=pending) et retourne son id."""
        with Session(_get_engine()) as s:
            row = DocumentRow(
                filename=doc.filename,
                original_name=doc.original_name,
                file_path=str(doc.file_path),
                file_size_mb=doc.file_size_mb,
                extension=doc.extension,
                status=DocumentStatus.PENDING,
            )
            s.add(row)
            s.commit()
            s.refresh(row)
            return row.id

    def mark_indexed(self, doc_id: int, nb_chunks: int, nb_chars: int) -> None:
        with Session(_get_engine()) as s:
            row = s.get(DocumentRow, doc_id)
            if row:
                row.nb_chunks = nb_chunks
                row.nb_chars  = nb_chars
                row.status    = DocumentStatus.INDEXED
                s.commit()

    def mark_error(self, doc_id: int, message: str) -> None:
        with Session(_get_engine()) as s:
            row = s.get(DocumentRow, doc_id)
            if row:
                row.status = f"{DocumentStatus.ERROR}: {message[:200]}"
                s.commit()

    def get_all(self) -> list[Document]:
        with Session(_get_engine()) as s:
            rows = s.query(DocumentRow).order_by(DocumentRow.uploaded_at.desc()).all()
            return [_row_to_model(r) for r in rows]

    def get_by_filename(self, filename: str) -> Document | None:
        with Session(_get_engine()) as s:
            row = s.query(DocumentRow).filter_by(filename=filename).first()
            return _row_to_model(row) if row else None

    def delete(self, filename: str) -> bool:
        with Session(_get_engine()) as s:
            row = s.query(DocumentRow).filter_by(filename=filename).first()
            if row:
                s.delete(row)
                s.commit()
                return True
            return False
