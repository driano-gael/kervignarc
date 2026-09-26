"""Service d'import des inscrits (E02US007) — arbitrage 4 : aperçu sans écriture, puis confirmation.

Source : `stories/E02-inscriptions.md`, fiche E02US007. La décision ligne à ligne est prouvée au
domaine (`test_domain_import_inscrits.py`) ; ici, ce que le service lit, et ce qu'il écrit ou non.
"""

from __future__ import annotations

import datetime

import pytest

from application.erreurs import TournoiIntrouvable
from application.import_inscrits import ServiceImportInscrits
from domain.archer import Archer
from domain.categorie import Categorie, SexeCategorie
from domain.club import Club
from domain.depart import Depart
from domain.import_inscrits import (
    Decision,
    FichierInscrits,
    LigneFichier,
    PlanImport,
    SourceImport,
)
from domain.inscription import Inscription
from domain.tournoi import Tournoi, TournoiId
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxClubRepository,
    FauxDepartRepository,
    FauxInscriptionRepository,
    FauxTournoiRepository,
    HorlogeFigee,
)

_CONTENU = b"fichier"
_INSTANT = datetime.datetime(2026, 11, 2, 18, 30, tzinfo=datetime.UTC)


class LecteurFactice:
    def __init__(self, fichier: FichierInscrits) -> None:
        self._fichier = fichier
        self.lus: list[bytes] = []

    def lire(self, contenu: bytes) -> FichierInscrits:
        self.lus.append(contenu)
        return self._fichier


class EcrivainFactice:
    def __init__(self) -> None:
        self.appliques: list[tuple[TournoiId, PlanImport, datetime.datetime]] = []

    def appliquer(
        self, tournoi_id: TournoiId, plan: PlanImport, cree_le: datetime.datetime
    ) -> None:
        self.appliques.append((tournoi_id, plan, cree_le))


def _ligne(numero: int, licence: str | None, depart: int = 1, nom: str = "Dupont") -> LigneFichier:
    return LigneFichier(
        numero=numero,
        licence=licence,
        depart_numero=depart,
        nom=nom,
        prenom="Jeanne",
        sexe=SexeCategorie.FEMME,
        date_naissance=datetime.date(1990, 1, 1),
        club="Kervignac",
    )


class _Montage:
    def __init__(self, *lignes: LigneFichier) -> None:
        self.tournois = FauxTournoiRepository()
        self.archers = FauxArcherRepository()
        self.categories = FauxCategorieRepository()
        self.departs = FauxDepartRepository()
        self.clubs = FauxClubRepository()
        self.inscriptions = FauxInscriptionRepository()
        tournoi = self.tournois.ajouter(Tournoi.creer("Challenge", datetime.date(2026, 11, 15)))
        assert tournoi.id is not None
        self.tournoi_id = tournoi.id
        self.categories.ajouter(Categorie.creer(tournoi.id, "Femmes", sexe=SexeCategorie.FEMME))
        self.depart = self.departs.ajouter(Depart.creer(tournoi.id, 1, 800, "09:00"))
        self.clubs.ajouter(Club.creer("Kervignac"))
        self.lecteur = LecteurFactice(FichierInscrits(SourceImport.IANSEO, tuple(lignes)))
        self.ecrivain = EcrivainFactice()
        self.service = ServiceImportInscrits(
            tournois=self.tournois,
            categories=self.categories,
            departs=self.departs,
            archers=self.archers,
            clubs=self.clubs,
            inscriptions=self.inscriptions,
            lecteur=self.lecteur,
            ecrivain=self.ecrivain,
            horloge=HorlogeFigee(_INSTANT),
        )


def test_l_apercu_rend_le_rapport_sans_rien_ecrire() -> None:
    m = _Montage(_ligne(1, "1234567A"))

    plan = m.service.apercu(m.tournoi_id, _CONTENU)

    assert [ligne.decision for ligne in plan.lignes] == [Decision.CREER]
    assert m.lecteur.lus == [_CONTENU]
    assert m.ecrivain.appliques == []


def test_confirmer_ecrit_le_plan_des_lignes_importables() -> None:
    m = _Montage(_ligne(1, "1234567A"), _ligne(2, "2222222B", depart=9))

    plan = m.service.importer(m.tournoi_id, m.service.lire(_CONTENU), frozenset())

    ((tournoi_id, applique, cree_le),) = m.ecrivain.appliques
    assert tournoi_id == m.tournoi_id
    assert applique == plan
    # E17US012 : une inscription non datée passerait pour la plus ancienne dette du tournoi.
    assert cree_le == _INSTANT
    assert [ligne.ligne.numero for ligne in plan.importables] == [1]
    assert [ligne.ligne.numero for ligne in plan.rejetees] == [2]


def test_confirmer_transmet_les_homonymes_coches() -> None:
    m = _Montage(_ligne(3, None))
    m.archers.ajouter(Archer.creer("Dupont", "Jeanne", m.tournoi_id, 1, club_id=1))

    sans = m.service.apercu(m.tournoi_id, _CONTENU)
    avec = m.service.importer(m.tournoi_id, m.service.lire(_CONTENU), frozenset({3}))

    assert sans.lignes[0].decision is Decision.HOMONYME
    assert avec.lignes[0].decision is Decision.CREER


def test_rien_d_importable_n_ecrit_rien() -> None:
    m = _Montage(_ligne(1, "1234567A", depart=9))

    m.service.importer(m.tournoi_id, m.service.lire(_CONTENU), frozenset())

    assert m.ecrivain.appliques == []


def test_l_instantane_ne_voit_que_le_tournoi_importe() -> None:
    """Une licence connue d'un **autre** tournoi ne désigne aucune fiche ici."""
    m = _Montage(_ligne(1, "1234567A"))
    autre = m.tournois.ajouter(Tournoi.creer("Autre", datetime.date(2026, 12, 1)))
    assert autre.id is not None
    ailleurs = m.archers.ajouter(Archer.creer("Dupont", "Jeanne", autre.id, 1, licence="1234567A"))
    autre_depart = m.departs.ajouter(Depart.creer(autre.id, 1, 0, "10:00"))
    assert ailleurs.id is not None and autre_depart.id is not None
    m.inscriptions.ajouter(Inscription.creer(ailleurs.id, autre_depart.id, cree_le=None))

    plan = m.service.apercu(m.tournoi_id, _CONTENU)

    assert plan.lignes[0].decision is Decision.CREER
    assert plan.lignes[0].depart_id == m.depart.id


def test_un_tournoi_inconnu_leve() -> None:
    m = _Montage()
    with pytest.raises(TournoiIntrouvable):
        m.service.apercu(999, _CONTENU)
