"""
manage.py — Gestion de la base de données DocMind
==================================================
Utilisation :
    python manage.py users              → liste tous les comptes
    python manage.py delete <username>  → supprime un compte et ses données
    python manage.py delete-guests      → supprime tous les comptes invités
    python manage.py delete-all-users   → supprime TOUS les comptes (reset total)
"""

import sys
import sqlite3
from pathlib import Path

# Chemin vers la base de données
DB_PATH = Path(__file__).parent / "data" / "database" / "docmind.db"

# ChromaDB
VECTORS_DIR = Path(__file__).parent / "data" / "vectors"
UPLOADS_DIR = Path(__file__).parent / "data" / "uploads"


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def list_users():
    conn = get_conn()
    users = conn.execute("SELECT id, username, created_at FROM users ORDER BY created_at").fetchall()
    conn.close()

    if not users:
        print("Aucun utilisateur en base.")
        return

    print(f"\n{'ID':<5} {'Username':<25} {'Créé le'}")
    print("-" * 55)
    for u in users:
        guest = " [invité]" if u["username"].startswith("invité_") else ""
        print(f"{u['id']:<5} {u['username']:<25} {u['created_at']}{guest}")
    print()


def delete_user(username: str):
    conn = get_conn()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    if not user:
        print(f"❌ Utilisateur '{username}' introuvable.")
        conn.close()
        return

    user_id = user["id"]

    # Récupère les doc_ids pour nettoyer ChromaDB et fichiers
    docs = conn.execute("SELECT id, filename FROM documents WHERE user_id = ?", (user_id,)).fetchall()

    # Supprime les fichiers physiques
    for doc in docs:
        filepath = UPLOADS_DIR / doc["filename"]
        if filepath.exists():
            filepath.unlink()

    # Supprime en base (conversations + messages en cascade)
    conn.execute("DELETE FROM documents     WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users         WHERE id = ?",      (user_id,))
    conn.commit()
    conn.close()

    # Nettoie ChromaDB
    _clean_chroma([doc["id"] for doc in docs])

    print(f"✅ Compte '{username}' supprimé ({len(docs)} document(s) effacé(s)).")


def delete_guests():
    conn = get_conn()
    guests = conn.execute(
        "SELECT username FROM users WHERE username LIKE 'invité_%'"
    ).fetchall()
    conn.close()

    if not guests:
        print("Aucun compte invité trouvé.")
        return

    for g in guests:
        delete_user(g["username"])

    print(f"\n✅ {len(guests)} compte(s) invité(s) supprimé(s).")


def delete_all_users():
    confirm = input("⚠️  Supprimer TOUS les comptes ? (tape OUI pour confirmer) : ")
    if confirm.strip() != "OUI":
        print("Annulé.")
        return

    conn = get_conn()
    users = conn.execute("SELECT username FROM users").fetchall()
    conn.close()

    for u in users:
        delete_user(u["username"])

    print(f"\n✅ {len(users)} compte(s) supprimé(s). Base réinitialisée.")


def _clean_chroma(doc_ids: list[int]):
    """Supprime les vecteurs des documents dans ChromaDB."""
    if not doc_ids or not VECTORS_DIR.exists():
        return
    try:
        import chromadb
        client     = chromadb.PersistentClient(path=str(VECTORS_DIR))
        collection = client.get_or_create_collection("documents")
        for doc_id in doc_ids:
            existing = collection.get(where={"doc_id": doc_id})
            if existing["ids"]:
                collection.delete(ids=existing["ids"])
    except Exception as e:
        print(f"  (ChromaDB: {e})")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or args[0] == "users":
        list_users()

    elif args[0] == "delete" and len(args) == 2:
        delete_user(args[1])

    elif args[0] == "delete-guests":
        delete_guests()

    elif args[0] == "delete-all-users":
        delete_all_users()

    else:
        print(__doc__)
