"""Fixtures et doublures partagées des tests backend.

`connecter_admin` : ouvre un accès admin (POST `/api/v1/auth/configurer`, E10US002) sur un client
de test et pose l'en-tête `Authorization: Bearer <jeton>` par défaut, pour que les appels suivants
vers les routes admin (ex. création de tournoi) soient autorisés. Suppose que le fichier `.env`
de l'app pointe vers un chemin jetable (voir les fixtures d'app qui passent `admin_env_path`).

`FauxClubRepository` vit ici plutôt que dans un module de test : depuis E02US001, il sert **à la
fois** aux tests de `ServiceClubs` et à ceux de `ServiceArchers` (qui valide le club de
rattachement). L'héberger dans l'un des deux modules ferait importer l'autre en retour — un
**cycle d'imports** entre modules de test. Seules des dépendances **stdlib** sont ajoutées ici
(`domain` est pur, règle 1) : le conftest reste importable sans fastapi, comme l'exige le hook
pre-commit `domain-isolation`, qui exécute pytest avec pytest pour seule dépendance.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

from domain.club import Club, ClubId, cle_nom

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

# Alias de type en **forward-ref** (chaîne) : `conftest.py` reste importable sans `fastapi`
# installé — nécessaire au hook pre-commit `domain-isolation`, qui exécute pytest dans un
# environnement minimal (pytest seul) et charge malgré tout ce conftest. Au runtime, les
# annotations sont différées (`from __future__ import annotations`), donc `fastapi` n'est
# jamais requis ici ; les tests qui s'en servent créent leur `TestClient` ailleurs.
ConnecterAdmin = Callable[["TestClient"], None]


class FauxClubRepository:
    """Repository en mémoire conforme au port `ClubRepository`.

    `par_nom` applique `cle_nom`, **la fonction de production** — pas une réimplémentation : un
    faux qui recoderait la règle de comparaison ferait passer les tests de service quoi qu'il
    arrive à l'adapter réel.
    """

    def __init__(self) -> None:
        self._clubs: dict[int, Club] = {}
        self._sequence = 0

    def ajouter(self, club: Club) -> Club:
        self._sequence += 1
        persiste = dataclasses.replace(club, id=self._sequence)
        self._clubs[self._sequence] = persiste
        return persiste

    def par_id(self, club_id: ClubId) -> Club | None:
        return self._clubs.get(club_id)

    def par_nom(self, nom: str) -> Club | None:
        recherche = cle_nom(nom)
        for club in self._clubs.values():
            if cle_nom(club.nom) == recherche:
                return club
        return None

    def lister(self) -> list[Club]:
        return list(self._clubs.values())

    def enregistrer(self, club: Club) -> Club:
        assert club.id is not None
        self._clubs[club.id] = club
        return club

    def supprimer(self, club_id: ClubId) -> None:
        del self._clubs[club_id]


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
