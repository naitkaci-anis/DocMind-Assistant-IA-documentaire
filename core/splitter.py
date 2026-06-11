"""
core/splitter.py
================
Découpe un texte long en morceaux ("chunks") qui se chevauchent légèrement.

Pourquoi découper ?
  Un LLM a une fenêtre de contexte limitée (ex : 4096 tokens).
  Un PDF de 50 pages = ~100 000 caractères → trop grand pour une seule requête.
  On découpe en chunks de ~1000 caractères, indexés séparément dans ChromaDB.

Pourquoi le chevauchement (overlap) ?
  Couper net à 1000 caractères risque de couper une phrase en plein milieu.
  Avec 200 caractères d'overlap, la fin du chunk N est répétée au début du chunk N+1
  → le sens reste intact aux frontières.
"""

from config.settings import CHUNK_SIZE, CHUNK_OVERLAP


def split_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """
    Découpe un texte en chunks avec chevauchement.

    Stratégie : fenêtre glissante de `chunk_size` caractères.
    À chaque pas, on essaie de couper sur un retour à la ligne ou un espace
    pour ne pas tronquer une phrase au milieu.

    Args:
        text      : texte brut à découper
        chunk_size: taille max d'un chunk en caractères
        overlap   : nombre de caractères partagés entre deux chunks consécutifs

    Returns:
        Liste de strings (chunks), vide si le texte est vide.
    """
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)

        # Si on n'est pas à la fin du texte, cherche une coupure naturelle
        # dans les 20 derniers % du chunk pour ne pas couper en plein mot
        if end < text_len:
            search_from = start + int(chunk_size * 0.8)

            newline_pos = text.rfind("\n", search_from, end)
            if newline_pos > search_from:
                end = newline_pos
            else:
                space_pos = text.rfind(" ", search_from, end)
                if space_pos > search_from:
                    end = space_pos

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Dès qu'on a atteint la fin du texte, on s'arrête
        if end >= text_len:
            break

        # Sinon on avance de (chunk_size - overlap) pour créer le chevauchement
        start = end - overlap

    return chunks
