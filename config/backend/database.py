"""
backend/database.py
===================
Base de données SQLite — création des tables et fonctions CRUD.

Tables :
  - users         : comptes utilisateurs
  - documents     : fichiers uploadés (par utilisateur)
  - conversations : fils de discussion (par utilisateur)
  - messages      : messages dans chaque conversation
"""

import sqlite3
import json
from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    """Ouvre une connexion SQLite. row_factory permet d'accéder aux colonnes par nom."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """
    Crée les tables si elles n'existent pas, et migre les colonnes manquantes.
    Appelé une seule fois au démarrage du serveur.
    """
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            username             TEXT NOT NULL UNIQUE,
            password_hash        TEXT NOT NULL,
            security_question    TEXT NOT NULL DEFAULT '',
            security_answer_hash TEXT NOT NULL DEFAULT '',
            created_at           TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS documents (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL DEFAULT 1,
            filename      TEXT NOT NULL,
            original_name TEXT NOT NULL,
            file_size_kb  REAL NOT NULL DEFAULT 0,
            status        TEXT NOT NULL DEFAULT 'pending',
            chunks_count  INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL DEFAULT 1,
            title      TEXT NOT NULL DEFAULT 'Nouvelle conversation',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS messages (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role            TEXT NOT NULL,
            content         TEXT NOT NULL,
            sources         TEXT NOT NULL DEFAULT '[]',
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );
    """)

    # Migration : ajoute les colonnes manquantes sur les tables existantes
    for sql in [
        "ALTER TABLE documents     ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE conversations ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE users ADD COLUMN security_question    TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE users ADD COLUMN security_answer_hash TEXT NOT NULL DEFAULT ''",
    ]:
        try:
            conn.execute(sql)
            conn.commit()
        except Exception:
            pass  # Colonne déjà présente

    conn.close()


# ── Utilisateurs ───────────────────────────────────────────────────────────────

def db_create_user(
    username            : str,
    password_hash       : str,
    security_question   : str = "",
    security_answer_hash: str = "",
) -> dict:
    """Crée un compte et retourne le user dict."""
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO users (username, password_hash, security_question, security_answer_hash) VALUES (?, ?, ?, ?)",
        (username, password_hash, security_question, security_answer_hash),
    )
    user_id = cursor.lastrowid
    conn.commit()
    row = conn.execute("SELECT id, username, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row)


def db_get_user_by_username(username: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def db_get_security_question(username: str) -> str | None:
    """Retourne la question secrète d'un utilisateur (sans exposer le hash)."""
    conn = get_connection()
    row  = conn.execute(
        "SELECT security_question FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    return row["security_question"] if row else None


def db_update_password(user_id: int, new_hash: str):
    """Met à jour le mot de passe haché d'un utilisateur."""
    conn = get_connection()
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
    conn.commit()
    conn.close()


def db_get_user_by_id(user_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT id, username, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Documents ──────────────────────────────────────────────────────────────────

def db_create_document(filename: str, original_name: str, file_size_kb: float, user_id: int = 1) -> int:
    """Insère un document (statut 'pending') et retourne son ID."""
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO documents (filename, original_name, file_size_kb, user_id) VALUES (?, ?, ?, ?)",
        (filename, original_name, file_size_kb, user_id),
    )
    doc_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return doc_id


def db_update_document_status(doc_id: int, status: str, chunks_count: int = 0):
    conn = get_connection()
    conn.execute(
        "UPDATE documents SET status = ?, chunks_count = ? WHERE id = ?",
        (status, chunks_count, doc_id),
    )
    conn.commit()
    conn.close()


def db_get_all_documents(user_id: int | None = None) -> list[dict]:
    conn = get_connection()
    if user_id is not None:
        rows = conn.execute(
            "SELECT * FROM documents WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def db_get_document(doc_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def db_delete_document(doc_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()


# ── Conversations ──────────────────────────────────────────────────────────────

def db_create_conversation(title: str = "Nouvelle conversation", user_id: int = 1) -> dict:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO conversations (title, user_id) VALUES (?, ?)",
        (title, user_id),
    )
    conv_id = cursor.lastrowid
    conn.commit()
    row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
    conn.close()
    return dict(row)


def db_list_conversations(user_id: int | None = None) -> list[dict]:
    conn = get_connection()
    if user_id is not None:
        rows = conn.execute(
            "SELECT * FROM conversations WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM conversations ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def db_update_conversation_title(conv_id: int, title: str):
    conn = get_connection()
    conn.execute("UPDATE conversations SET title = ? WHERE id = ?", (title, conv_id))
    conn.commit()
    conn.close()


def db_delete_conversation(conv_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    conn.commit()
    conn.close()


# ── Messages ───────────────────────────────────────────────────────────────────

def db_add_message(conv_id: int, role: str, content: str, sources: list[str] | None = None) -> dict:
    sources_json = json.dumps(sources or [])
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO messages (conversation_id, role, content, sources) VALUES (?, ?, ?, ?)",
        (conv_id, role, content, sources_json),
    )
    msg_id = cursor.lastrowid
    conn.commit()
    row = conn.execute("SELECT * FROM messages WHERE id = ?", (msg_id,)).fetchone()
    conn.close()
    msg = dict(row)
    msg["sources"] = json.loads(msg["sources"])
    return msg


def db_get_messages(conv_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
        (conv_id,),
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        m = dict(r)
        m["sources"] = json.loads(m["sources"])
        result.append(m)
    return result
