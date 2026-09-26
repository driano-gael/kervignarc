"""Adapter d'écriture de l'import (E02US007) — une transaction par fichier, sur base migrée."""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from domain.archer import Archer
from domain.categorie import Categorie
from domain.depart import Depart
from domain.import_inscrits import Decision, LigneFichier, LignePlan, PlanImport, SourceImport
from domain.tournoi import Tournoi
from infrastructure.db import (
    ArcherRepositorySQL,
    AuditRepositorySQL,
    CategorieRepositorySQL,
    ClubRepositorySQL,
    Database,
    DepartRepositorySQL,
    ImportInscritsRepositorySQL,
    InscriptionRepositorySQL,
    TournoiRepositorySQL,
)
from infrastructure.erreurs import InfrastructureError
from tests.base_migree import preparer_base

_QUAND = datetime.datetime(2026, 11, 2, 18, 30, tzinfo=datetime.UTC)


class _Base:
    def __init__(self, tmp_path: Path) -> None:
        url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
        preparer_base(url)
        self.db = Database(url)
        fabrique = self.db.session_factory
        self.archers = ArcherRepositorySQL(fabrique)
        self.clubs = ClubRepositorySQL(fabrique)
        self.inscriptions = InscriptionRepositorySQL(fabrique, AuditRepositorySQL(fabrique))
        tournoi = TournoiRepositorySQL(fabrique).ajouter(
            Tournoi.creer("Challenge", datetime.date(2026, 11, 15))
        )
        assert tournoi.id is not None
        self.tournoi_id = tournoi.id
        categorie = CategorieRepositorySQL(fabrique).ajouter(Categorie.creer(tournoi.id, "Femmes"))
        assert categorie.id is not None
        self.categorie_id = categorie.id
        depart = DepartRepositorySQL(fabrique).ajouter(Depart.creer(tournoi.id, 1, 800, "09:00"))
        assert depart.id is not None
        self.depart_id = depart.id
        self.ecrivain = ImportInscritsRepositorySQL(fabrique)

    def creer(
        self, numero: int, licence: str | None, club: str | None = "Montoir", nom: str = "Dupont"
    ) -> LignePlan:
        return LignePlan(
            ligne=LigneFichier(
                numero=numero, licence=licence, depart_numero=1, nom=nom, prenom="Jo"
            ),
            decision=Decision.CREER,
            depart_id=self.depart_id,
            categorie_id=self.categorie_id,
            club_a_creer=club,
            licence=licence,
        )


def _plan(*lignes: LignePlan) -> PlanImport:
    return PlanImport(source=SourceImport.IANSEO, lignes=lignes)


def test_le_plan_cree_clubs_fiches_et_inscriptions(tmp_path: Path) -> None:
    b = _Base(tmp_path)

    b.ecrivain.appliquer(
        b.tournoi_id,
        _plan(b.creer(1, "1234567A"), b.creer(2, "7654321B", club="MONTOIR", nom="Martin")),
        _QUAND,
    )

    archers = b.archers.par_tournoi(b.tournoi_id)
    assert sorted(a.licence or "" for a in archers) == ["1234567A", "7654321B"]
    assert [club.nom for club in b.clubs.lister()] == ["Montoir"]  # créé une seule fois
    inscrites = b.inscriptions.par_depart(b.depart_id)
    assert len(inscrites) == 2
    assert {i.cree_le for i in inscrites} == {_QUAND}


def test_une_inscription_designee_par_la_ligne_creatrice(tmp_path: Path) -> None:
    b = _Base(tmp_path)
    second = DepartRepositorySQL(b.db.session_factory).ajouter(
        Depart.creer(b.tournoi_id, 2, 800, "14:00")
    )
    inscrire = LignePlan(
        ligne=LigneFichier(numero=2, licence="1234567A", depart_numero=2),
        decision=Decision.INSCRIRE,
        depart_id=second.id,
        fiche_de_la_ligne=1,
    )

    b.ecrivain.appliquer(b.tournoi_id, _plan(b.creer(1, "1234567A"), inscrire), _QUAND)

    (archer,) = b.archers.par_tournoi(b.tournoi_id)
    assert archer.id is not None
    assert len(b.inscriptions.par_archer(archer.id)) == 2


def test_les_lignes_non_importables_ne_sont_pas_ecrites(tmp_path: Path) -> None:
    b = _Base(tmp_path)
    rejetee = LignePlan(
        ligne=LigneFichier(numero=2, licence=None, depart_numero=9),
        decision=Decision.REJETEE,
        motif="départ",
    )

    b.ecrivain.appliquer(b.tournoi_id, _plan(b.creer(1, None, club=None), rejetee), _QUAND)

    assert len(b.archers.par_tournoi(b.tournoi_id)) == 1


def test_un_echec_en_cours_de_fichier_n_ecrit_rien(tmp_path: Path) -> None:
    """La 2ᵉ ligne heurte l'index `UNIQUE` partiel : la 1ʳᵉ ne survit pas (CA « rapport »)."""
    b = _Base(tmp_path)
    b.archers.ajouter(
        Archer.creer("Existant", "Jo", b.tournoi_id, b.categorie_id, licence="9999999Z")
    )

    with pytest.raises(InfrastructureError):
        b.ecrivain.appliquer(
            b.tournoi_id, _plan(b.creer(1, "1234567A"), b.creer(2, "9999999Z")), _QUAND
        )

    assert [a.licence for a in b.archers.par_tournoi(b.tournoi_id)] == ["9999999Z"]
    assert b.clubs.lister() == []
    assert b.inscriptions.par_depart(b.depart_id) == []


def test_l_index_partiel_admet_plusieurs_archers_sans_licence(tmp_path: Path) -> None:
    b = _Base(tmp_path)
    for nom in ("A", "B"):
        b.archers.ajouter(Archer.creer(nom, "Jo", b.tournoi_id, b.categorie_id))

    assert len(b.archers.par_tournoi(b.tournoi_id)) == 2


def test_l_index_refuse_la_meme_licence_dans_le_tournoi(tmp_path: Path) -> None:
    b = _Base(tmp_path)
    b.archers.ajouter(Archer.creer("A", "Jo", b.tournoi_id, b.categorie_id, licence="1234567A"))

    with pytest.raises(InfrastructureError):
        b.archers.ajouter(Archer.creer("B", "Jo", b.tournoi_id, b.categorie_id, licence="1234567A"))


def test_la_licence_survit_a_l_edition(tmp_path: Path) -> None:
    b = _Base(tmp_path)
    archer = b.archers.ajouter(Archer.creer("A", "Jo", b.tournoi_id, b.categorie_id))

    b.archers.enregistrer(archer.modifier("A", "Jo", b.categorie_id, None, "1234567A"))

    assert b.archers.par_id(archer.id or 0) is not None
    assert (b.archers.par_id(archer.id or 0) or archer).licence == "1234567A"


def test_la_fusion_transmet_la_licence_de_l_absorbe_dans_sa_transaction(tmp_path: Path) -> None:
    """Revue d'E02US007 (axes A, C2) : le report ne vit plus dans un second `enregistrer`."""
    b = _Base(tmp_path)
    gagnant = b.archers.ajouter(Archer.creer("A", "Jo", b.tournoi_id, b.categorie_id))
    perdant = b.archers.ajouter(
        Archer.creer("A", "Jo", b.tournoi_id, b.categorie_id, licence="1234567A")
    )
    assert gagnant.id is not None and perdant.id is not None

    b.archers.fusionner(gagnant.id, perdant.id)

    relu = b.archers.par_id(gagnant.id)
    assert relu is not None and relu.licence == "1234567A"
