"""
database/chat_repository.py
============================
Persistance des conversations et messages — SQLite via SQLAlchemy.
"""

from __future__ import annotations
import json
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, relationship

from config.settings import SQLITE_PATH
from models.message import Conversation, Message


# ── ORM ───────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


class ConversationRow(Base):
    __tablename__ = "conversations"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    title      = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    messages   = relationship("MessageRow", back_populates="conversation",
                              cascade="all, delete-orphan", order_by="MessageRow.id")


class MessageRow(Base):
    __tablename__ = "messages"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role            = Column(String,  nullable=False)
    content         = Column(Text,    nullable=False)
    sources_json    = Column(Text,    default="[]")
    created_at      = Column(DateTime, default=datetime.utcnow)
    conversation    = relationship("ConversationRow", back_populates="messages")


# ── Engine singleton ──────────────────────────────────────────────────────────

_engine = None

def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(f"sqlite:///{SQLITE_PATH}")
        Base.metadata.create_all(_engine)
    return _engine


# ── Conversions ───────────────────────────────────────────────────────────────

def _conv_to_model(row: ConversationRow) -> Conversation:
    return Conversation(id=row.id, title=row.title, created_at=row.created_at)

def _msg_to_model(row: MessageRow) -> Message:
    return Message(
        id=row.id,
        conversation_id=row.conversation_id,
        role=row.role,
        content=row.content,
        sources=json.loads(row.sources_json or "[]"),
        created_at=row.created_at,
    )


# ── Repository ────────────────────────────────────────────────────────────────

class ChatRepository:

    def create_conversation(self, title: str = "Nouvelle conversation") -> Conversation:
        with Session(_get_engine()) as s:
            row = ConversationRow(title=title)
            s.add(row)
            s.commit()
            s.refresh(row)
            return _conv_to_model(row)

    def update_title(self, conv_id: int, title: str) -> None:
        with Session(_get_engine()) as s:
            row = s.get(ConversationRow, conv_id)
            if row:
                row.title = title
                s.commit()

    def list_conversations(self) -> list[Conversation]:
        with Session(_get_engine()) as s:
            rows = s.query(ConversationRow).order_by(ConversationRow.created_at.desc()).all()
            return [_conv_to_model(r) for r in rows]

    def delete_conversation(self, conv_id: int) -> None:
        with Session(_get_engine()) as s:
            row = s.get(ConversationRow, conv_id)
            if row:
                s.delete(row)
                s.commit()

    def add_message(
        self,
        conv_id: int,
        role:    str,
        content: str,
        sources: list[str] | None = None,
    ) -> Message:
        with Session(_get_engine()) as s:
            row = MessageRow(
                conversation_id=conv_id,
                role=role,
                content=content,
                sources_json=json.dumps(sources or []),
            )
            s.add(row)
            s.commit()
            s.refresh(row)
            return _msg_to_model(row)

    def get_messages(self, conv_id: int) -> list[Message]:
        with Session(_get_engine()) as s:
            rows = (
                s.query(MessageRow)
                .filter_by(conversation_id=conv_id)
                .order_by(MessageRow.id)
                .all()
            )
            return [_msg_to_model(r) for r in rows]
