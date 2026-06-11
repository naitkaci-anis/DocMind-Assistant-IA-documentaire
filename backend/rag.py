"""
backend/rag.py
==============
RAG = Retrieval-Augmented Generation

Principe :
  1. L'utilisateur pose une question
  2. On transforme la question en vecteur (embed_text)
  3. On cherche les passages les plus proches dans ChromaDB,
     en filtrant uniquement sur les documents de l'utilisateur connecté
  4. On construit un prompt avec ces passages comme contexte
  5. Le LLM génère une réponse basée uniquement sur ce contexte
"""

import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.embeddings   import embed_text
from backend.vector_store import vs_search, vs_is_ready, vs_count
from backend.llm          import stream_response
from backend.database     import db_get_all_documents
from backend.deps         import get_user_id

router = APIRouter()


class SearchRequest(BaseModel):
    query    : str
    n_results: int = 5


@router.get("/status")
async def get_status(user_id: int = Depends(get_user_id)):
    """Vérifie si des documents sont indexés pour cet utilisateur."""
    docs = db_get_all_documents(user_id=user_id)
    indexed_count = sum(1 for d in docs if d["status"] == "indexed")
    # Compte uniquement les chunks des documents de CET utilisateur
    user_chunks   = sum(d.get("chunks_count", 0) for d in docs if d["status"] == "indexed")
    return {"ready": indexed_count > 0, "chunks": user_chunks}


@router.get("/documents")
async def list_documents(user_id: int = Depends(get_user_id)):
    """Liste les documents de l'utilisateur avec leurs statistiques."""
    docs     = db_get_all_documents(user_id=user_id)
    total_kb = sum(d.get("file_size_kb", 0) for d in docs)
    return {
        "documents"    : docs,
        "total"        : len(docs),
        "total_size_mb": round(total_kb / 1024, 2),
    }


@router.post("/ask")
async def ask_question(req: SearchRequest, user_id: int = Depends(get_user_id)):
    """
    RAG complet : question → recherche → LLM → réponse en streaming SSE.
    La recherche est limitée aux documents de l'utilisateur connecté.
    """
    # Récupère uniquement les doc_ids indexés de l'utilisateur
    user_docs    = db_get_all_documents(user_id=user_id)
    user_doc_ids = [d["id"] for d in user_docs if d["status"] == "indexed"]

    query_vec   = embed_text(req.query)
    rag_results = vs_search(query_vec, n_results=req.n_results, user_doc_ids=user_doc_ids)

    if rag_results:
        context_parts = [
            f"[Source {i+1} — {r['original_name']}, passage #{r['chunk_index']+1}]\n{r['text']}"
            for i, r in enumerate(rag_results)
        ]
        context = "\n\n".join(context_parts)
        system  = (
            "Tu es DocMind, un assistant IA expert en analyse documentaire.\n"
            "Règles strictes :\n"
            "- Réponds UNIQUEMENT à partir des extraits fournis.\n"
            "- Si l'information est absente, dis : \"Je ne trouve pas cette information dans les documents fournis.\"\n"
            "- Cite les sources à la fin (nom du fichier).\n"
            "- Sois concis, précis et réponds en français.\n\n"
            f"=== EXTRAITS DE DOCUMENTS ===\n{context}"
        )
    else:
        system = (
            "Tu es DocMind, un assistant documentaire IA.\n"
            "Aucun document pertinent trouvé. Réponds en français de façon générale."
        )

    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": req.query},
    ]
    sources = list({r["original_name"] for r in rag_results})

    def generate():
        yield f"event: context\ndata: {json.dumps(rag_results)}\n\n"
        try:
            for token in stream_response(messages, temperature=0.1):
                safe = token.replace("\n", "\\n")
                yield f"data: {safe}\n\n"
        except Exception as e:
            yield f"data: ❌ Erreur LLM : {e}\\nVérifie qu'Ollama est lancé.\n\n"
            yield "data: [DONE]\n\n"
            return
        yield f"event: sources\ndata: {json.dumps(sources)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
