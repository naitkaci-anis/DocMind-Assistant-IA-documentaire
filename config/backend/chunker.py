"""
backend/chunker.py
==================
Découpage de texte en "chunks" (morceaux).

Pourquoi découper les documents ?
  - Les LLMs ont une limite de tokens en entrée (contexte limité)
  - On veut indexer des passages précis, pas tout le document
  - La recherche sémantique est plus précise sur de courts extraits

Algorithme — fenêtre glissante avec chevauchement :

  Texte : [..........................................]
  Chunk 1 : [==========]
  Chunk 2 :        [==========]
  Chunk 3 :               [==========]
                   ^^^^^^^
                   overlap (chevauchement)

  Le chevauchement évite de couper une phrase en plein milieu.
"""

from config import CHUNK_SIZE, CHUNK_OVERLAP


def chunk_text(
    text      : str,
    chunk_size: int = CHUNK_SIZE,
    overlap   : int = CHUNK_OVERLAP,
) -> list[str]:
    """
    Découpe un texte en chunks avec chevauchement.

    Args:
        text       : texte à découper
        chunk_size : taille max d'un chunk en caractères
        overlap    : nombre de caractères partagés entre deux chunks consécutifs

    Returns:
        liste de strings, chaque string étant un chunk
    """
    text = text.strip()
    if not text:
        return []

    chunks   = []
    start    = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size

        # Cherche une coupure naturelle (saut de ligne ou espace)
        # dans les 20 % finaux du chunk, pour éviter de couper en plein mot
        if end < text_len:
            search_from = end - chunk_size // 5
            nl_pos    = text.rfind("\n", search_from, end)
            space_pos = text.rfind(" ",  search_from, end)
            cut = nl_pos if nl_pos > search_from else space_pos
            if cut > search_from:
                end = cut

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Arrête si on a atteint la fin du texte
        if end >= text_len:
            break

        # Prochain chunk : recule de 'overlap' pour garder le contexte
        next_start = end - overlap
        if next_start <= start:
            # Sécurité : évite une boucle infinie si overlap >= chunk_size
            next_start = start + max(1, chunk_size - overlap)
        start = next_start

    return chunks
