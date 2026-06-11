"""
models/message.py
=================
Modèles de données pour le chat — couche MODEL.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    role:            str            # "user" | "assistant"
    content:         str
    conversation_id: int
    id:              int | None   = None
    created_at:      datetime     = field(default_factory=datetime.utcnow)
    sources:         list[str]    = field(default_factory=list)

    def to_ollama(self) -> dict:
        """Format attendu par l'API Ollama."""
        return {"role": self.role, "content": self.content}


@dataclass
class Conversation:
    title:      str
    id:         int | None    = None
    created_at: datetime      = field(default_factory=datetime.utcnow)

    @property
    def short_title(self) -> str:
        """Titre tronqué à 40 caractères pour la sidebar."""
        return self.title[:40] + "…" if len(self.title) > 40 else self.title
