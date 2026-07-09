"""Router de santé — adapter entrant minimal (couche API).

Sonde `/health` : confirme que le serveur répond. Séparé de la composition root pour
illustrer le patron « les routers vivent dans api/, l'assemblage dans bootstrap/ ».
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Sonde de santé."""
    return {"status": "ok"}
