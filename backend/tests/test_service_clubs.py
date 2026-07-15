"""Tests du service applicatif Clubs (E02US001) — repositories factices.

Le service est testé **en isolation** : de faux repositories en mémoire (conformes aux ports)
suffisent — ni base ni serveur. Les deux faux consommés ici (`FauxClubRepository`,
`FauxArcherRepository`) vivent dans `conftest` : ils servent **aussi** aux tests de
`ServiceArchers`, et un faux partagé se déclare une fois — sans quoi une évolution de port
casserait deux endroits au lieu d'un.
"""

from __future__ import annotations

import pytest

from application.clubs import ServiceClubs
from application.erreurs import ClubIntrouvable, ClubReference, NomClubDejaPris
from domain.archer import Archer
from domain.club import Club, ClubId
from domain.erreurs import NomClubInvalide
from tests.conftest import FauxArcherRepository, FauxClubRepository


def _monter() -> tuple[ServiceClubs, FauxArcherRepository]:
    """Monte le service et **expose** le faux repository d'archers.

    Les tests qui n'ont pas besoin des archers passent par la fixture `service` ci-dessous ;
    ceux qui exercent le refus de suppression ont besoin d'y rattacher un archer.
    """
    archers = FauxArcherRepository()
    return ServiceClubs(FauxClubRepository(), archers), archers


@pytest.fixture
def service() -> ServiceClubs:
    return _monter()[0]


def _id(club: Club) -> ClubId:
    """Identifiant d'un club **persisté**, narrowé pour mypy (`Club.id` est `ClubId | None`).

    Évite un `type: ignore[arg-type]` à chaque appel : le backend n'en compte aucun, gardons-le
    ainsi (même parti que `test_domain_grain_validation`).
    """
    assert club.id is not None
    return club.id


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


def test_creer_refuse_un_homonyme_dont_la_casse_accentuee_differe(service: ServiceClubs) -> None:
    """« É » / « é » : un repli de casse limité à l'ASCII (`COLLATE NOCASE` de SQLite, `str.lower`)
    laisserait passer ce doublon — d'où le `casefold` de `cle_nom`, qui, lui, voit l'Unicode."""
    service.creer("Élan de Fougères")

    with pytest.raises(NomClubDejaPris):
        service.creer("élan de fougères")


def test_creer_refuse_un_homonyme_saisi_sans_ses_accents(service: ServiceClubs) -> None:
    """Le doublon le plus probable sur une tablette : le nom tapé sans accents."""
    service.creer("Élan de Fougères")

    with pytest.raises(NomClubDejaPris):
        service.creer("Elan de Fougeres")


def test_deux_clubs_de_noms_distincts_coexistent(service: ServiceClubs) -> None:
    service.creer("Arc Club Rennes")
    service.creer("Élan de Fougères")

    assert len(service.lister()) == 2


def test_lister_trie_par_nom_casse_et_accents_replies(service: ServiceClubs) -> None:
    """Le jeu d'essai contient un accentué **et** un « Z » : un tri par code point y échouerait.

    `casefold` seul classerait « Élan » (U+00C9) après « Zénith » — les clubs accentués
    s'entasseraient en fin de liste.
    """
    service.creer("Zénith Archerie")
    service.creer("Élan de Fougères")
    service.creer("arc club Rennes")
    service.creer("Bretagne Archerie")

    assert [club.nom for club in service.lister()] == [
        "arc club Rennes",
        "Bretagne Archerie",
        "Élan de Fougères",
        "Zénith Archerie",
    ]


def test_lister_un_referentiel_vide(service: ServiceClubs) -> None:
    assert service.lister() == []


def test_modifier_renomme_un_club(service: ServiceClubs) -> None:
    club = service.creer("Arc Club Rennes")

    renomme = service.modifier(_id(club), "Arc Club de Rennes")

    assert renomme.id == club.id
    assert renomme.nom == "Arc Club de Rennes"
    assert service.lister() == [renomme]


def test_modifier_accepte_de_reenregistrer_le_meme_nom(service: ServiceClubs) -> None:
    """Réémettre le nom inchangé (formulaire semé) ne doit pas se heurter à son propre homonyme."""
    club = service.creer("Arc Club Rennes")

    renomme = service.modifier(_id(club), "Arc Club Rennes")

    assert renomme.nom == "Arc Club Rennes"


def test_modifier_refuse_le_nom_d_un_autre_club(service: ServiceClubs) -> None:
    service.creer("Arc Club Rennes")
    autre = service.creer("Élan de Fougères")

    with pytest.raises(NomClubDejaPris):
        service.modifier(_id(autre), "arc club rennes")


def test_modifier_refuse_un_identifiant_inconnu(service: ServiceClubs) -> None:
    with pytest.raises(ClubIntrouvable):
        service.modifier(404, "Arc Club Rennes")


def test_supprimer_retire_le_club_du_referentiel(service: ServiceClubs) -> None:
    club = service.creer("Arc Club Rennes")

    service.supprimer(_id(club))

    assert service.lister() == []


def test_supprimer_refuse_un_identifiant_inconnu(service: ServiceClubs) -> None:
    with pytest.raises(ClubIntrouvable):
        service.supprimer(404)


def test_supprimer_libere_le_nom(service: ServiceClubs) -> None:
    club = service.creer("Arc Club Rennes")
    service.supprimer(_id(club))

    recree = service.creer("Arc Club Rennes")

    assert recree.nom == "Arc Club Rennes"


def test_supprimer_refuse_un_club_rattache_a_un_archer() -> None:
    """Le CA de l'US : un club **utilisé** n'est pas supprimable (`ClubReference` → 409)."""
    service, archers = _monter()
    club = service.creer("Arc Club Rennes")
    archers.ajouter(Archer.creer("Robin", tournoi_id=1, club_id=club.id))

    with pytest.raises(ClubReference):
        service.supprimer(_id(club))

    assert service.lister() == [club]


def test_supprimer_refuse_meme_si_l_archer_est_d_un_autre_tournoi() -> None:
    """La référence se cherche **tous tournois confondus** : le référentiel est global.

    Un club utilisé par une compétition passée est utilisé tout court ; le supprimer laisserait
    une référence pendante dans l'historique.
    """
    service, archers = _monter()
    club = service.creer("Arc Club Rennes")
    archers.ajouter(Archer.creer("Robin", tournoi_id=99, club_id=club.id))

    with pytest.raises(ClubReference):
        service.supprimer(_id(club))


def test_supprimer_ignore_les_archers_d_un_autre_club() -> None:
    """Un club sans archer reste supprimable, même si d'autres clubs en ont."""
    service, archers = _monter()
    rennes = service.creer("Arc Club Rennes")
    fougeres = service.creer("Élan de Fougères")
    archers.ajouter(Archer.creer("Robin", tournoi_id=1, club_id=fougeres.id))

    service.supprimer(_id(rennes))

    assert service.lister() == [fougeres]


def test_supprimer_possible_apres_desengagement_des_archers() -> None:
    """Un club redevient supprimable une fois ses archers réaffectés."""
    service, archers = _monter()
    club = service.creer("Arc Club Rennes")
    archer = archers.ajouter(Archer.creer("Robin", tournoi_id=1, club_id=club.id))
    archers.enregistrer(Archer(nom=archer.nom, tournoi_id=1, club_id=None, id=archer.id))

    service.supprimer(_id(club))

    assert service.lister() == []
