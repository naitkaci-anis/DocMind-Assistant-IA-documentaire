"""
backend/upload.py
=================
Routes FastAPI pour l'upload et la gestion des documents.

Pipeline d'indexation (exécuté en arrière-plan après l'upload) :
  1. Extraction du texte (PDF, DOCX, TXT, MD, CSV)
  2. Découpage en chunks
  3. Génération des embeddings (SentenceTransformers)
  4. Stockage dans ChromaDB + mise à jour SQLite
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends

from config import UPLOADS_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB
from backend.extractor    import extract
from backend.chunker      import chunk_text
from backend.embeddings   import embed_texts
from backend.vector_store import vs_add_document, vs_delete_document
from backend.database     import (
    db_create_document, db_update_document_status,
    db_get_all_documents, db_get_document, db_delete_document,
)
from backend.deps import get_user_id

router = APIRouter()

GUEST_MAX_DOCS = 3  # Limite pour les sessions invité


def _is_guest_user(user_id: int) -> bool:
    """Un invité a un username commençant par 'invité_'."""
    from backend.database import db_get_user_by_id
    user = db_get_user_by_id(user_id)
    return bool(user and user.get("username", "").startswith("invité_"))


@router.post("/")
async def upload_document(
    background_tasks: BackgroundTasks,
    file   : UploadFile = File(...),
    user_id: int        = Depends(get_user_id),
):
    # Vérifie la limite invité (3 documents max)
    if _is_guest_user(user_id):
        existing = db_get_all_documents(user_id=user_id)
        if len(existing) >= GUEST_MAX_DOCS:
            raise HTTPException(
                status_code=403,
                detail=f"Limite d'essai atteinte ({GUEST_MAX_DOCS} documents max). Crée un compte gratuit pour continuer.",
            )

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporté. Acceptés : {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"Fichier trop volumineux ({size_mb:.1f} Mo). Maximum : {MAX_FILE_SIZE_MB} Mo",
        )

    unique_name = f"{uuid.uuid4().hex}{ext}"
    filepath    = UPLOADS_DIR / unique_name
    filepath.write_bytes(content)

    doc_id = db_create_document(
        filename      = unique_name,
        original_name = file.filename,
        file_size_kb  = round(len(content) / 1024, 1),
        user_id       = user_id,
    )

    background_tasks.add_task(_index_document, doc_id, str(filepath), file.filename)

    return {"doc_id": doc_id, "message": "Fichier reçu. Indexation en cours..."}


def _index_document(doc_id: int, filepath: str, original_name: str):
    """Pipeline complet d'indexation — exécuté en arrière-plan."""
    try:
        text = extract(filepath)
        if not text.strip():
            db_update_document_status(doc_id, "error")
            return

        chunks = chunk_text(text)
        if not chunks:
            db_update_document_status(doc_id, "error")
            return

        embeddings = embed_texts(chunks)
        vs_add_document(doc_id, chunks, embeddings, original_name)
        db_update_document_status(doc_id, "indexed", len(chunks))

    except Exception as e:
        db_update_document_status(doc_id, "error")
        print(f"[Erreur indexation doc {doc_id}] {e}")


@router.get("/")
async def get_documents(user_id: int = Depends(get_user_id)):
    """Retourne les documents de l'utilisateur connecté."""
    docs = db_get_all_documents(user_id=user_id)
    return {"documents": docs, "total": len(docs)}


@router.get("/{doc_id}/status")
async def get_status(doc_id: int, user_id: int = Depends(get_user_id)):
    doc = db_get_document(doc_id)
    if not doc or doc.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Document non trouvé")
    return {"status": doc["status"], "chunks_count": doc["chunks_count"]}


@router.delete("/{doc_id}")
async def delete_document(doc_id: int, user_id: int = Depends(get_user_id)):
    doc = db_get_document(doc_id)
    if not doc or doc.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Document non trouvé")

    filepath = UPLOADS_DIR / doc["filename"]
    if filepath.exists():
        filepath.unlink()

    vs_delete_document(doc_id)
    db_delete_document(doc_id)

    return {"message": f"'{doc['original_name']}' supprimé avec succès"}
