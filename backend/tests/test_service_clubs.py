"""Tests du service applicatif Clubs (E02US001) — repository factice.

Le service est testé **en isolation** : un faux repository en mémoire, conforme au port
`ClubRepository`, suffit — ni base ni serveur.
"""

from __future__ import annotations

import dataclasses

import pytest

from application.clubs import ServiceClubs
from application.erreurs import ClubIntrouvable, NomClubDejaPris
from domain.club import Club, ClubId
from domain.erreurs import NomClubInvalide


class FauxClubRepository:
    """Repository en mémoire conforme au port `ClubRepository`."""

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
        recherche = nom.strip().casefold()
        for club in self._clubs.values():
            if club.nom.casefold() == recherche:
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
def service() -> ServiceClubs:
    return ServiceClubs(FauxClubRepository())


def test_creer_ajoute_un_club_au_referentiel(service: ServiceClubs) -> None:
    club = service.creer("Arc Club Rennes")

    assert club.id is not None
    assert club.nom == "Arc Club Rennes"
    assert service.lister() == [club]


def test_creer_refuse_un_nom_vide(service: ServiceClubs) -> None:
    with pytest.raises(NomClubInvalide):
        service.creer("   ")


def test_creer_refuse_un_homonyme_exact(service: ServiceClubs) -> None:
    service.creer("Arc Club Rennes")

    with pytest.raises(NomClubDejaPris):
        service.creer("Arc Club Rennes")


def test_creer_refuse_un_homonyme_a_la_casse_pres(service: ServiceClubs) -> None:
    """Le référentiel existe pour ne pas ressaisir : deux entrées pour un club le trahirait."""
    service.creer("Arc Club Rennes")

    with pytest.raises(NomClubDejaPris):
        service.creer("  arc club RENNES  ")


def test_creer_refuse_un_homonyme_accentue_a_la_casse_pres(service: ServiceClubs) -> None:
    """`casefold` replie les accents, là où le `COLLATE NOCASE` de SQLite ne voit que l'ASCII."""
    service.creer("Élan de Fougères")

    with pytest.raises(NomClubDejaPris):
        service.creer("élan de fougères")


def test_deux_clubs_de_noms_distincts_coexistent(service: ServiceClubs) -> None:
    service.creer("Arc Club Rennes")
    service.creer("Élan de Fougères")

    assert len(service.lister()) == 2


def test_lister_trie_par_nom_sans_tenir_compte_de_la_casse(service: ServiceClubs) -> None:
    service.creer("Élan de Fougères")
    service.creer("arc club Rennes")
    service.creer("Bretagne Archerie")

    assert [club.nom for club in service.lister()] == [
        "arc club Rennes",
        "Bretagne Archerie",
        "Élan de Fougères",
    ]


def test_lister_un_referentiel_vide(service: ServiceClubs) -> None:
    assert service.lister() == []


def test_modifier_renomme_un_club(service: ServiceClubs) -> None:
    club = service.creer("Arc Club Rennes")

    renomme = service.modifier(club.id, "Arc Club de Rennes")  # type: ignore[arg-type]

    assert renomme.id == club.id
    assert renomme.nom == "Arc Club de Rennes"
    assert service.lister() == [renomme]


def test_modifier_accepte_de_reenregistrer_le_meme_nom(service: ServiceClubs) -> None:
    """Réémettre le nom inchangé (formulaire semé) ne doit pas se heurter à son propre homonyme."""
    club = service.creer("Arc Club Rennes")

    renomme = service.modifier(club.id, "Arc Club Rennes")  # type: ignore[arg-type]

    assert renomme.nom == "Arc Club Rennes"


def test_modifier_refuse_le_nom_d_un_autre_club(service: ServiceClubs) -> None:
    service.creer("Arc Club Rennes")
    autre = service.creer("Élan de Fougères")

    with pytest.raises(NomClubDejaPris):
        service.modifier(autre.id, "arc club rennes")  # type: ignore[arg-type]


def test_modifier_refuse_un_identifiant_inconnu(service: ServiceClubs) -> None:
    with pytest.raises(ClubIntrouvable):
        service.modifier(404, "Arc Club Rennes")


def test_supprimer_retire_le_club_du_referentiel(service: ServiceClubs) -> None:
    club = service.creer("Arc Club Rennes")

    service.supprimer(club.id)  # type: ignore[arg-type]

    assert service.lister() == []


def test_supprimer_refuse_un_identifiant_inconnu(service: ServiceClubs) -> None:
    with pytest.raises(ClubIntrouvable):
        service.supprimer(404)


def test_supprimer_libere_le_nom(service: ServiceClubs) -> None:
    club = service.creer("Arc Club Rennes")
    service.supprimer(club.id)  # type: ignore[arg-type]

    recree = service.creer("Arc Club Rennes")

    assert recree.nom == "Arc Club Rennes"
