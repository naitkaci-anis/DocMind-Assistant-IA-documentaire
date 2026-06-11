"""
backend/summary.py
==================
Génération de résumés automatiques de documents via le LLM.

Modes :
  - "full"   : résumé complet structuré
  - "short"  : résumé en 3-5 phrases
  - "points" : liste de 5-10 points clés
"""

import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.vector_store import _get_collection
from backend.llm          import stream_response
from backend.database     import db_get_all_documents, db_get_document
from backend.deps         import get_user_id

router = APIRouter()


class SummaryRequest(BaseModel):
    doc_id: int
    mode  : str = "full"


PROMPTS = {
    "full": (
        "Tu es un assistant expert en synthèse documentaire.\n"
        "Génère un résumé complet et structuré du document ci-dessous.\n"
        "Inclus : contexte, idées principales, conclusions.\n"
        "Réponds en français, avec des titres et sous-titres si pertinent."
    ),
    "short": (
        "Tu es un assistant expert en synthèse documentaire.\n"
        "Résume ce document en 3 à 5 phrases maximum.\n"
        "Sois concis, clair et garde l'essentiel.\n"
        "Réponds en français."
    ),
    "points": (
        "Tu es un assistant expert en synthèse documentaire.\n"
        "Extrais les 5 à 10 points clés de ce document.\n"
        "Format : liste à puces, une idée par ligne.\n"
        "Chaque point doit être une phrase courte et précise.\n"
        "Réponds en français."
    ),
}


@router.get("/documents")
async def list_summarizable_documents(user_id: int = Depends(get_user_id)):
    """Retourne uniquement les documents indexés de l'utilisateur connecté."""
    docs    = db_get_all_documents(user_id=user_id)
    indexed = [d for d in docs if d["status"] == "indexed"]
    return {"documents": indexed}


@router.post("/generate")
async def generate_summary(req: SummaryRequest, user_id: int = Depends(get_user_id)):
    """Génère un résumé en streaming SSE."""
    doc = db_get_document(req.doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouvé")
    if doc.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    if doc["status"] != "indexed":
        raise HTTPException(status_code=400, detail="Document pas encore indexé")

    collection = _get_collection()
    result     = collection.get(
        where   = {"doc_id": req.doc_id},
        include = ["documents", "metadatas"],
    )

    if not result["ids"]:
        raise HTTPException(status_code=404, detail="Aucun chunk trouvé pour ce document")

    chunks_with_index = sorted(
        zip(result["metadatas"], result["documents"]),
        key=lambda x: x[0].get("chunk_index", 0),
    )
    chunks    = [text for _, text in chunks_with_index]
    full_text = "\n\n".join(chunks)
    if len(full_text) > 8000:
        full_text = full_text[:8000] + "\n\n[... texte tronqué ...]"

    system_prompt = PROMPTS.get(req.mode, PROMPTS["full"])
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": f"=== DOCUMENT : {doc['original_name']} ===\n\n{full_text}\n\n=== RÉSUMÉ ==="},
    ]

    def generate():
        try:
            for token in stream_response(messages, temperature=0.2):
                safe = token.replace("\n", "\\n")
                yield f"data: {safe}\n\n"
        except Exception as e:
            yield f"data: ❌ Erreur LLM : {e}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
