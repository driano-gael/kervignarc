"""Filet catch-all de la frontière API (mapping d'erreurs, ADR-0007, règle 5).

Vérifie qu'une exception **non typée** — qui échappe aux familles domaine / application /
infrastructure — est traduite en 500 au **format uniforme** `{code, message}`, sans fuite du
message d'origine. Une route jetable qui lève une exception nue suffit : on éprouve le
gestionnaire, pas un vrai endpoint.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.erreurs import enregistrer_gestionnaires_erreurs


def test_exception_non_typee_rend_500_au_format_uniforme() -> None:
    """Une exception nue (ni Domain/Application/Infrastructure) → 500 `{code, message}` générique.

    `raise_server_exceptions=False` : sans lui, `TestClient` **relèverait** l'exception (son
    défaut) au lieu de laisser le gestionnaire produire sa réponse — or c'est la réponse rendue
    **au client** qu'on veut éprouver, pas la propagation vers le serveur de test. Le message
    d'origine ne doit pas fuir dans le corps (aucune fuite de détail interne, règle 5).
    """
    app = FastAPI()
    enregistrer_gestionnaires_erreurs(app)

    @app.get("/boum")
    def _boum() -> None:
        raise RuntimeError("detail interne qui ne doit pas fuir")

    client = TestClient(app, raise_server_exceptions=False)
    reponse = client.get("/boum")

    assert reponse.status_code == 500
    corps = reponse.json()
    assert corps["code"] == "erreur_interne"
    assert corps["message"] == "Erreur interne du serveur."
    assert "detail interne" not in reponse.text  # le message d'origine ne fuit pas
