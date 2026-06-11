"""
backend/deps.py
===============
Dépendances FastAPI réutilisables.

Une "dépendance" FastAPI est une fonction injectée automatiquement
dans les routes via `Depends(...)`. Si elle lève une exception,
FastAPI retourne l'erreur avant même d'entrer dans la route.

Utilisation dans une route :
    @router.get("/")
    async def ma_route(user_id: int = Depends(get_user_id)):
        ...
"""

from fastapi import Depends, HTTPException, Request


def get_user_id(request: Request) -> int:
    """
    Récupère l'ID de l'utilisateur connecté depuis la session.
    Lève HTTP 401 si personne n'est connecté.
    """
    uid = request.session.get("user_id")
    if not uid:
        raise HTTPException(status_code=401, detail="Non connecté — va sur /login")
    return int(uid)
