"""Point d'entrée du backend Kervignarc.

Squelette minimal (E00US001) servant à valider la chaîne d'outillage
(venv + pip + FastAPI + uvicorn). Le câblage réel (composition root) est posé en
E00US005, la première tranche métier de bout en bout en E00US009.

Lancement (dev) :
    uvicorn main:app --reload
"""

from fastapi import FastAPI

app = FastAPI(title="Kervignarc", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Sonde de santé — confirme que le serveur répond."""
    return {"status": "ok"}
