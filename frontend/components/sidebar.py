"""
frontend/components/sidebar.py
================================
Composant VUE — sidebar réutilisable injectée dans chaque page.
Importe depuis le service pour afficher les stats en temps réel.
"""

import streamlit as st
from config.settings import SQLITE_PATH
from database.vector_store import VectorStore
from database.repository import DocumentRepository


def render_sidebar() -> None:
    """Affiche la sidebar DocMind avec les stats système."""
    repo   = DocumentRepository()
    vstore = VectorStore()

    with st.sidebar:
        st.title("🧠 DocMind")
        st.caption("Assistant IA de gestion documentaire")
        st.divider()

        st.subheader("État du système")

        docs        = repo.get_all()
        nb_indexed  = sum(1 for d in docs if d.status == "indexed")
        nb_chunks   = vstore.count()
        db_status   = "✅ Connectée" if SQLITE_PATH.exists() else "⏳ Non initialisée"

        col1, col2 = st.columns(2)
        col1.metric("Documents", nb_indexed)
        col2.metric("Chunks",    nb_chunks)

        st.text(f"Base SQLite : {db_status}")
        st.divider()
        st.caption("💡 Navigue via le menu ci-dessus")
