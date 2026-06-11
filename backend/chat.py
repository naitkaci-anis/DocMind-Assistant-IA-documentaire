"""
backend/chat.py
===============
Chat conversationnel avec mémoire et enrichissement RAG.

À chaque message :
  1. On sauvegarde la question de l'utilisateur en base
  2. On fait une recherche RAG sur les documents de l'utilisateur
  3. On construit le prompt avec : système + contexte RAG + historique + question
  4. On streame la réponse du LLM token par token (SSE)
  5. On sauvegarde la réponse complète + les sources en base
"""

import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.embeddings   import embed_text
from backend.vector_store import vs_search
from backend.llm          import stream_response
from backend.database     import (
    db_create_conversation, db_list_conversations,
    db_update_conversation_title, db_delete_conversation,
    db_add_message, db_get_messages, db_get_all_documents,
)
from backend.deps import get_user_id

router = APIRouter()


class ConversationCreate(BaseModel):
    title: str = "Nouvelle conversation"

class ConversationRename(BaseModel):
    title: str

class MessageRequest(BaseModel):
    content  : str
    n_results: int = 5


# ── Conversations ──────────────────────────────────────────────────────────────

@router.post("/conversations")
async def create_conversation(
    data   : ConversationCreate,
    user_id: int = Depends(get_user_id),
):
    conv = db_create_conversation(data.title, user_id=user_id)
    return conv


@router.get("/conversations")
async def list_conversations(user_id: int = Depends(get_user_id)):
    return {"conversations": db_list_conversations(user_id=user_id)}


@router.patch("/conversations/{conv_id}")
async def rename_conversation(
    conv_id: int,
    data   : ConversationRename,
    user_id: int = Depends(get_user_id),
):
    title = data.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Le titre ne peut pas être vide")
    db_update_conversation_title(conv_id, title[:80])
    return {"message": "Conversation renommée", "title": title[:80]}


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: int, user_id: int = Depends(get_user_id)):
    db_delete_conversation(conv_id)
    return {"message": "Conversation supprimée"}


# ── Messages ───────────────────────────────────────────────────────────────────

@router.get("/conversations/{conv_id}/messages")
async def get_messages(conv_id: int, user_id: int = Depends(get_user_id)):
    return {"messages": db_get_messages(conv_id)}


@router.post("/conversations/{conv_id}/messages")
async def send_message(
    conv_id: int,
    req    : MessageRequest,
    user_id: int = Depends(get_user_id),
):
    # Recherche RAG filtrée sur les documents de l'utilisateur
    user_docs    = db_get_all_documents(user_id=user_id)
    user_doc_ids = [d["id"] for d in user_docs if d["status"] == "indexed"]

    query_vec   = embed_text(req.content)
    rag_results = vs_search(query_vec, n_results=req.n_results, user_doc_ids=user_doc_ids)

    db_add_message(conv_id, "user", req.content)

    history   = db_get_messages(conv_id)
    user_msgs = [m for m in history if m["role"] == "user"]
    if len(user_msgs) == 1:
        short_title = req.content[:50] + ("…" if len(req.content) > 50 else "")
        db_update_conversation_title(conv_id, short_title)

    if rag_results:
        context = "\n\n".join(
            f"[Source {i+1} — {r['original_name']}]\n{r['text']}"
            for i, r in enumerate(rag_results)
        )
        system_content = (
            "Tu es DocMind, un assistant IA de gestion documentaire.\n"
            "Utilise le contexte documentaire fourni pour répondre avec précision.\n"
            "Réponds en français de façon claire et professionnelle.\n\n"
            f"=== CONTEXTE DOCUMENTAIRE ===\n{context}"
        )
    else:
        system_content = (
            "Tu es DocMind, un assistant documentaire IA.\n"
            "Réponds en français de façon claire et professionnelle."
        )

    llm_messages = [{"role": "system", "content": system_content}]
    past = [m for m in history if not (m["role"] == "user" and m == history[-1])]
    for m in past[-10:]:
        llm_messages.append({"role": m["role"], "content": m["content"]})
    llm_messages.append({"role": "user", "content": req.content})

    sources       = list({r["original_name"] for r in rag_results})
    full_response = []

    def generate():
        try:
            for token in stream_response(llm_messages, temperature=0.3):
                full_response.append(token)
                safe = token.replace("\n", "\\n")
                yield f"data: {safe}\n\n"
        except Exception as e:
            yield f"data: ❌ Erreur LLM : {e}\\nVérifie qu'Ollama est lancé (ollama serve).\n\n"
            yield "data: [DONE]\n\n"
            return

        answer = "".join(full_response)
        if answer:
            db_add_message(conv_id, "assistant", answer, sources)

        yield f"event: sources\ndata: {json.dumps(sources)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
