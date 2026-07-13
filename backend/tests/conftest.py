"""Fixtures partagées des tests backend.

`connecter_admin` : ouvre un accès admin (POST `/api/v1/auth/configurer`, E10US002) sur un client
de test et pose l'en-tête `Authorization: Bearer <jeton>` par défaut, pour que les appels suivants
vers les routes admin (ex. création de tournoi) soient autorisés. Suppose que le fichier `.env`
de l'app pointe vers un chemin jetable (voir les fixtures d'app qui passent `admin_env_path`).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

# Alias de type en **forward-ref** (chaîne) : `conftest.py` reste importable sans `fastapi`
# installé — nécessaire au hook pre-commit `domain-isolation`, qui exécute pytest dans un
# environnement minimal (pytest seul) et charge malgré tout ce conftest. Au runtime, les
# annotations sont différées (`from __future__ import annotations`), donc `fastapi` n'est
# jamais requis ici ; les tests qui s'en servent créent leur `TestClient` ailleurs.
ConnecterAdmin = Callable[["TestClient"], None]


@pytest.fixture
def connecter_admin() -> ConnecterAdmin:
    """Renvoie une fonction qui configure l'accès admin et authentifie le client de test."""

    def _connecter(
        client: TestClient, login: str = "admin", mot_de_passe: str = "secret-123"
    ) -> None:
        reponse = client.post(
            "/api/v1/auth/configurer", json={"login": login, "mot_de_passe": mot_de_passe}
        )
        assert reponse.status_code == 201, reponse.text
        client.headers["Authorization"] = f"Bearer {reponse.json()['jeton']}"

    return _connecter
