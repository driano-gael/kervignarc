"""Fixtures et doublures partagées des tests backend.

`connecter_admin` : ouvre un accès admin (POST `/api/v1/auth/configurer`, E10US002) sur un client
de test et pose l'en-tête `Authorization: Bearer <jeton>` par défaut, pour que les appels suivants
vers les routes admin (ex. création de tournoi) soient autorisés. Suppose que le fichier `.env`
de l'app pointe vers un chemin jetable (voir les fixtures d'app qui passent `admin_env_path`).

**Doctrine des doublures** : un faux repository consommé par **≥ 2 modules** de test vit ici ;
celui qui n'a qu'un consommateur reste dans son module (`FauxScoreRepository` reste dans
`test_service_archers`). Depuis E02US001, `FauxClubRepository` et `FauxArcherRepository` servent
**à la fois** aux tests de `ServiceClubs` (qui refuse de supprimer un club utilisé) et à ceux de
`ServiceArchers` (qui valide le club de rattachement) — les héberger dans l'un des deux modules
ferait importer l'autre en retour, jusqu'au **cycle d'imports**.

`FauxCategorieRepository` a rejoint ce fichier en E02US002, qui en devenait le **3ᵉ** consommateur
(`ServiceArchers` valide désormais la catégorie de l'archer) après `test_service_categories` et
`test_service_blasons`, où deux copies identiques vivaient chacune de leur côté. C'est la preuve
d'aujourd'hui que réclame le projet avant de factoriser, pas une évolution supposée.

> `FauxTournoiRepository` est, lui, recopié dans trois modules. On le laisse : cette US n'en ajoute
> pas d'usage, et on ne réécrit pas ce qu'on n'aggrave pas.

Seules des dépendances **stdlib** sont ajoutées ici (`domain` est pur, règle 1) : ce conftest
reste importable sans fastapi, comme l'exige le hook pre-commit `domain-isolation`, qui exécute
pytest avec pytest pour seule dépendance — d'où aussi `fastapi` sous `TYPE_CHECKING` ci-dessous.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

from domain.archer import Archer, ArcherId
from domain.blason import BlasonId
from domain.categorie import Categorie, CategorieId
from domain.club import Club, ClubId, cle_nom
from domain.tournoi import TournoiId

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


class FauxArcherRepository:
    """Repository en mémoire conforme au port `ArcherRepository`."""

    def __init__(self) -> None:
        self._archers: dict[int, Archer] = {}
        self._sequence = 0
        self._a_la_suppression: list[Callable[[ArcherId], None]] = []

    def a_la_suppression(self, rappel: Callable[[ArcherId], None]) -> None:
        """Abonne un rappel à `supprimer` — cf. `supprimer` pour le pourquoi.

        Hors du port : c'est une couture **de test**, qui permet à un faux `ScoreRepository` de
        reproduire la purge que le vrai adapter fait dans sa transaction.
        """
        self._a_la_suppression.append(rappel)

    def ajouter(self, archer: Archer) -> Archer:
        self._sequence += 1
        # `club_id` est **recopié** : un faux qui le laisserait tomber ferait passer au vert un
        # service incapable de rattacher un archer à son club.
        persiste = dataclasses.replace(archer, id=self._sequence)
        self._archers[self._sequence] = persiste
        return persiste

    def par_id(self, archer_id: ArcherId) -> Archer | None:
        return self._archers.get(archer_id)

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Archer]:
        return [a for a in self._archers.values() if a.tournoi_id == tournoi_id]

    def par_club(self, club_id: ClubId) -> list[Archer]:
        # Sans filtre sur le tournoi : le référentiel des clubs est global (E02US001).
        return [a for a in self._archers.values() if a.club_id == club_id]

    def enregistrer(self, archer: Archer) -> Archer:
        assert archer.id is not None
        self._archers[archer.id] = archer
        return archer

    def supprimer(self, archer_id: ArcherId) -> None:
        # Le port exige que les **scores** partent avec l'archer (E02US003) : le vrai adapter le
        # fait dans sa transaction. Un faux qui les laisserait derrière lui verdirait un service
        # laissant des scores orphelins — d'où les rappels, que `FauxScoreRepository` branche.
        del self._archers[archer_id]
        for rappel in self._a_la_suppression:
            rappel(archer_id)


class FauxCategorieRepository:
    """Repository en mémoire conforme au port `CategorieRepository`."""

    def __init__(self) -> None:
        self._categories: dict[int, Categorie] = {}
        self._sequence = 0

    def ajouter(self, categorie: Categorie) -> Categorie:
        self._sequence += 1
        persiste = dataclasses.replace(categorie, id=self._sequence)
        self._categories[self._sequence] = persiste
        return persiste

    def par_id(self, categorie_id: CategorieId) -> Categorie | None:
        return self._categories.get(categorie_id)

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Categorie]:
        # Le filtre sur `tournoi_id` est ce qui rend testable le refus d'une catégorie
        # **étrangère au tournoi** (`CategorieHorsTournoi`, E02US002) : un faux qui renverrait
        # tout ferait passer au vert un service incapable de cloisonner les tournois.
        return [c for c in self._categories.values() if c.tournoi_id == tournoi_id]

    def par_blason(self, blason_id: BlasonId) -> list[Categorie]:
        return [c for c in self._categories.values() if c.blason_id == blason_id]

    def enregistrer(self, categorie: Categorie) -> Categorie:
        assert categorie.id in self._categories
        self._categories[categorie.id] = categorie
        return categorie

    def supprimer(self, categorie_id: CategorieId) -> None:
        del self._categories[categorie_id]


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
