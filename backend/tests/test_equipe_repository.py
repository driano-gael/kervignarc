"""Tests d'intégration de `EquipeRepositorySQL` (E13US002) sur une base migrée."""

from __future__ import annotations

import datetime
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

from domain.archer import Archer, ArcherId
from domain.categorie import Categorie
from domain.equipe import Equipe, TypeEquipe
from domain.tournoi import Tournoi, TournoiId
from infrastructure.db import (
    ArcherRepositorySQL,
    CategorieRepositorySQL,
    Database,
    EquipeRepositorySQL,
    TournoiRepositorySQL,
)
from tests.base_migree import preparer_base


@dataclass
class Base:
    equipes: EquipeRepositorySQL
    archers: ArcherRepositorySQL
    tournoi_id: TournoiId
    a: ArcherId
    b: ArcherId
    c: ArcherId


@pytest.fixture
def base(tmp_path: Path) -> Iterator[Base]:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    preparer_base(url)
    db = Database(url)
    try:
        tournoi = TournoiRepositorySQL(db.session_factory).ajouter(
            Tournoi.creer("Salle", datetime.date(2026, 11, 14))
        )
        assert tournoi.id is not None
        categorie = CategorieRepositorySQL(db.session_factory).ajouter(
            Categorie.creer(tournoi.id, "S1 H")
        )
        assert categorie.id is not None
        archers = ArcherRepositorySQL(db.session_factory)
        ids = []
        for prenom in ("Guillaume", "Walter", "Lucie"):
            archer = archers.ajouter(Archer.creer("Tell", prenom, tournoi.id, categorie.id))
            assert archer.id is not None
            ids.append(archer.id)
        yield Base(EquipeRepositorySQL(db.session_factory), archers, tournoi.id, *ids)
    finally:
        db.engine.dispose()


def test_enregistrer_cree_puis_relit_avec_les_membres_dans_l_ordre(base: Base) -> None:
    equipe = Equipe.creer(base.tournoi_id, "Les Archers", TypeEquipe.STANDARD)
    equipe = equipe.ajouter_membre(base.c).ajouter_membre(base.a)
    cree = base.equipes.enregistrer(equipe)
    assert cree.id is not None
    assert cree.membres == (base.c, base.a)
    assert base.equipes.par_id(cree.id) == cree
    assert base.equipes.par_id(999) is None


def test_enregistrer_met_a_jour_et_reordonne(base: Base) -> None:
    cree = base.equipes.enregistrer(
        Equipe.creer(base.tournoi_id, "Les Archers", TypeEquipe.STANDARD)
        .ajouter_membre(base.a)
        .ajouter_membre(base.b)
    )
    modifiee = cree.modifier("Le Duo", TypeEquipe.MIXTE, 5).retirer_membre(base.a)
    modifiee = modifiee.ajouter_membre(base.c).ajouter_membre(base.a)
    relue = base.equipes.enregistrer(modifiee)
    assert relue == modifiee
    assert base.equipes.par_tournoi(base.tournoi_id) == [modifiee]


def test_par_archer_et_supprimer(base: Base) -> None:
    standard = base.equipes.enregistrer(
        Equipe.creer(base.tournoi_id, "Les Archers", TypeEquipe.STANDARD).ajouter_membre(base.a)
    )
    mixte = base.equipes.enregistrer(
        Equipe.creer(base.tournoi_id, "Le Duo", TypeEquipe.MIXTE)
        .ajouter_membre(base.b)
        .ajouter_membre(base.a)
    )
    assert standard.id is not None and mixte.id is not None
    assert base.equipes.par_archer(base.a) == [standard, mixte]
    assert base.equipes.par_archer(base.c) == []
    base.equipes.supprimer(mixte.id)
    assert base.equipes.par_tournoi(base.tournoi_id) == [standard]
    assert base.archers.par_id(base.b) is not None


def test_supprimer_un_archer_le_retire_de_ses_equipes(base: Base) -> None:
    equipe = base.equipes.enregistrer(
        Equipe.creer(base.tournoi_id, "Les Archers", TypeEquipe.STANDARD)
        .ajouter_membre(base.a)
        .ajouter_membre(base.b)
    )
    assert equipe.id is not None
    base.archers.supprimer(base.a)
    relue = base.equipes.par_id(equipe.id)
    assert relue is not None and relue.membres == (base.b,)


def test_fusionner_transfere_au_meme_rang_ou_retire_le_doublon(base: Base) -> None:
    commune = base.equipes.enregistrer(
        Equipe.creer(base.tournoi_id, "Les Archers", TypeEquipe.STANDARD)
        .ajouter_membre(base.a)
        .ajouter_membre(base.b)
    )
    mixte = base.equipes.enregistrer(
        Equipe.creer(base.tournoi_id, "Le Duo", TypeEquipe.MIXTE)
        .ajouter_membre(base.b)
        .ajouter_membre(base.c)
    )
    assert commune.id is not None and mixte.id is not None
    base.archers.fusionner(base.c, base.b)
    transferee = base.equipes.par_id(commune.id)
    assert transferee is not None and transferee.membres == (base.a, base.c)
    dedoublonnee = base.equipes.par_id(mixte.id)
    assert dedoublonnee is not None and dedoublonnee.membres == (base.c,)
