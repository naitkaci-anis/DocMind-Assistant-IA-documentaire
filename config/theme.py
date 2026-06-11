"""
config/theme.py
===============
Charge les fichiers statiques (CSS + JS) et les injecte dans Streamlit.

Les designs sont dans :
  static/css/animations.css  — @keyframes
  static/css/theme.css       — styles des composants Streamlit
  static/js/stars.js         — fond canvas (étoiles + faisceau violet)
"""

from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

_STATIC = Path(__file__).parent.parent / "frontend" / "static"


def _read(rel: str) -> str:
    return (_STATIC / rel).read_text(encoding="utf-8")


def apply_theme() -> None:
    """
    Injecte le thème dark violet dans la page courante.
    À appeler juste après st.set_page_config().
    """

    # ── 1. CSS (animations + composants) ──────────────────────────────
    css = _read("css/animations.css") + "\n" + _read("css/theme.css")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

    # ── 2. JS canvas — fond étoilé + faisceau ─────────────────────────
    # st.components.v1.html() crée une micro-iframe.
    # Le script accède à window.parent pour ajouter le canvas
    # directement sur la vraie page Streamlit (en dehors de l'iframe).
    js = _read("js/stars.js")
    components.html(f"<script>{js}</script>", height=0, scrolling=False)
