"""
backend/chat_service.py
========================
Couche SERVICE — orchestration du chat RAG avec historique.

Coordonne :
  - La recherche sémantique (SearchService)
  - La génération LLM (llm_service)
  - La persistance des conversations (ChatRepository)
"""

from __future__ import annotations
from typing import Generator

from backend.search_service import SearchService
from backend.llm_service import stream_rag_answer, stream_chat_answer
from database.chat_repository import ChatRepository
from models.message import Conversation, Message
from models.search_result import SearchResult


class ChatService:

    def __init__(self):
        self._search = SearchService()
        self._repo   = ChatRepository()

    # ── Conversations ─────────────────────────────────────────────────────────

    def new_conversation(self, title: str = "Nouvelle conversation") -> Conversation:
        return self._repo.create_conversation(title)

    def list_conversations(self) -> list[Conversation]:
        return self._repo.list_conversations()

    def delete_conversation(self, conv_id: int) -> None:
        self._repo.delete_conversation(conv_id)

    def get_history(self, conv_id: int) -> list[Message]:
        return self._repo.get_messages(conv_id)

    # ── Envoi d'un message ────────────────────────────────────────────────────

    def ask(
        self,
        conv_id:   int,
        question:  str,
        n_results: int = 5,
    ) -> tuple[list[SearchResult], Generator[str, None, None]]:
        """
        Traite une question dans le contexte d'une conversation.

        Étapes :
          1. Recherche sémantique dans ChromaDB
          2. Sauvegarde du message utilisateur
          3. Retourne les chunks trouvés + générateur de réponse LLM

        Le générateur doit être consommé par la vue (st.write_stream).
        Après streaming, la vue appelle save_answer() pour persister la réponse.

        Returns:
            (results, generator)
        """
        results  = self._search.search(question, n_results=n_results)
        history  = self._repo.get_messages(conv_id)

        # Sauvegarde immédiate de la question utilisateur
        self._repo.add_message(conv_id, "user", question)

        # Mise à jour du titre avec la première question
        convs = self.list_conversations()
        conv  = next((c for c in convs if c.id == conv_id), None)
        if conv and conv.title == "Nouvelle conversation":
            short = question[:50] + "…" if len(question) > 50 else question
            self._repo.update_title(conv_id, short)

        generator = stream_chat_answer(
            history=history,
            question=question,
            results=results if results else None,
        )

        return results, generator

    def save_answer(
        self,
        conv_id: int,
        answer:  str,
        sources: list[str],
    ) -> None:
        """Persiste la réponse du LLM après streaming."""
        self._repo.add_message(conv_id, "assistant", answer, sources)

    def is_ready(self) -> bool:
        return self._search.is_ready()
