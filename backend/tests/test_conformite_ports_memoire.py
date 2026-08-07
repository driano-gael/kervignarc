"""Conformité de port : adapters **in-memory** vs adapters **SQL** (E15US002, ADR-0054 §5).

Le risque d'un second jeu d'adapters (in-memory, pour la simulation), c'est qu'il **diverge** de la
sémantique SQL — un `par_tournoi` qui ne filtre pas, un `par_id` introuvable qui ne rend pas `None`,
un ordre non garanti. Ces tests **partagés** exécutent le **même** contrat sur les deux
implémentations : ce qui passe sur SQL doit passer à l'identique en mémoire.

Sous-ensemble représentatif (extensible port par port) : `TournoiRepository` (sans FK :
`par_id`/`lister`), `PhaseRepository` (filtrage `par_tournoi` **et** ordre par `ordre`, plus
`par_tournoi_et_type`), `ArcherRepository` (filtrage `par_tournoi` **porteur de FK** — celui dont
l'hydratation dépend pour l'intégrité référentielle) et `GabaritSalleRepository` (le partage
**modèles (`tournoi_id is None`) vs instance** que la simulation exploite). Le contrat vit dans les
fonctions `_contrat_*`, jouées une fois par adapter.
"""

from __future__ import annotations

import datetime
from collections.abc import Iterator
from pathlib import Path

import pytest

from domain.archer import Archer
from domain.categorie import Categorie
from domain.depart import Depart
from domain.deroule_etape import EtapeDeroule
from domain.gabarit_salle import GabaritSalle
from domain.phase import Phase, TypePhase
from domain.ports import (
    ArcherRepository,
    CategorieRepository,
    DepartRepository,
    DerouleRepository,
    GabaritSalleRepository,
    PhaseRepository,
    TournoiRepository,
)
from domain.tournoi import Tournoi
from infrastructure.db import (
    ArcherRepositorySQL,
    CategorieRepositorySQL,
    Database,
    DepartRepositorySQL,
    DerouleEtapeRepositorySQL,
    GabaritSalleRepositorySQL,
    PhaseRepositorySQL,
    TournoiRepositorySQL,
)
from infrastructure.erreurs import InfrastructureError
from infrastructure.memory.repositories import (
    InMemoryArcherRepository,
    InMemoryCategorieRepository,
    InMemoryDepartRepository,
    InMemoryDerouleRepository,
    InMemoryGabaritSalleRepository,
    InMemoryPhaseRepository,
    InMemoryTournoiRepository,
)
from tests.base_migree import preparer_base

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)


@pytest.fixture
def base_sql(tmp_path: Path) -> Iterator[Database]:
    """Une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    preparer_base(url)
    database = Database(url)
    try:
        yield database
    finally:
        database.engine.dispose()


# --- Contrats partagés (indépendants de l'adapter) ---------------------------------------------


def _contrat_tournoi(repo: TournoiRepository) -> None:
    assert repo.par_id(999) is None, "par_id sur un identifiant absent → None."
    a = repo.ajouter(Tournoi.creer("Salle A", _DATE))
    b = repo.ajouter(Tournoi.creer("Salle B", _DATE))
    assert (
        a.id is not None and b.id is not None and a.id != b.id
    ), "Identifiants attribués, distincts."
    relu = repo.par_id(a.id)
    assert relu is not None and relu.nom == "Salle A", "par_id relit l'entité ajoutée."
    assert {t.nom for t in repo.lister()} == {"Salle A", "Salle B"}, "lister renvoie tout."


def _contrat_phase(
    tournois: TournoiRepository,
    phases: PhaseRepository,
    departs: DepartRepository,
    deroules: DerouleRepository,
) -> None:
    """Contrat du port `PhaseRepository`, **à la maille du départ** (E01US025, ADR-0075/0076).

    Le contrat portait sur le tournoi ; il porte désormais sur le créneau, et vérifie **les deux**
    lectures : `par_depart` (la séquence, celle du moteur) et `par_tournoi` (la vue transverse,
    concaténation des séquences de tous les créneaux). Les distinguer ici a du sens : c'est leur
    confusion qui a produit le défaut qu'ADR-0075 corrige.

    ⚠️ **Depuis ADR-0076, une phase n'est qu'un avancement** : sa définition (type, barème…) vient
    de l'`EtapeDeroule` de même rang, dans le tournoi de son créneau. Le décor pose donc **d'abord**
    le déroulé, une fois par tournoi, puis les instances — et le contrat vérifie que les deux
    adapters **assemblent** pareil, ce qui est précisément ce qu'un second jeu d'adapters risque de
    ne pas faire.
    """
    assert phases.par_id(999) is None, "par_id sur un identifiant absent → None."
    tournoi = tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
    autre = tournois.ajouter(Tournoi.creer("Autre salle", _DATE))
    assert tournoi.id is not None and autre.id is not None
    matin = departs.ajouter(
        Depart.creer(tournoi_id=tournoi.id, numero=1, tarif_centimes=800, horaire="09:00")
    )
    apres_midi = departs.ajouter(
        Depart.creer(tournoi_id=tournoi.id, numero=2, tarif_centimes=800, horaire="14:00")
    )
    ailleurs = departs.ajouter(
        Depart.creer(tournoi_id=autre.id, numero=1, tarif_centimes=800, horaire="09:00")
    )
    assert matin.id is not None and apres_midi.id is not None and ailleurs.id is not None

    # Le déroulé, **une fois par tournoi** : c'est lui qui porte le type de chaque rang.
    # (On évite le type `qualification`, qui exigerait un barème — hors sujet ici.)
    for ordre, type_etape in ((1, TypePhase.PLACEMENT), (2, TypePhase.ELIMINATION_DIRECTE)):
        deroules.ajouter(EtapeDeroule(tournoi_id=tournoi.id, ordre=ordre, type=type_etape))
    deroules.ajouter(
        EtapeDeroule(tournoi_id=tournoi.id, ordre=3, type=TypePhase.ELIMINATION_DIRECTE)
    )
    deroules.ajouter(EtapeDeroule(tournoi_id=autre.id, ordre=1, type=TypePhase.PLACEMENT))

    # Les instances, ajoutées dans le désordre (3, 1, 2) : `par_depart` doit les rendre **triées**.
    phases.ajouter(Phase.creer(matin.id, 3, TypePhase.ELIMINATION_DIRECTE))
    phases.ajouter(Phase.creer(matin.id, 1, TypePhase.PLACEMENT))
    phases.ajouter(Phase.creer(matin.id, 2, TypePhase.ELIMINATION_DIRECTE))
    phases.ajouter(Phase.creer(apres_midi.id, 1, TypePhase.PLACEMENT))  # même tournoi, autre vague
    phases.ajouter(Phase.creer(ailleurs.id, 1, TypePhase.PLACEMENT))  # d'un autre tournoi

    du_depart = phases.par_depart(matin.id)
    assert [p.ordre for p in du_depart] == [1, 2, 3], "par_depart filtre puis trie par ordre."
    assert [p.type for p in du_depart] == [
        TypePhase.PLACEMENT,
        TypePhase.ELIMINATION_DIRECTE,
        TypePhase.ELIMINATION_DIRECTE,
    ], "la définition est **assemblée** depuis l'étape de même rang (ADR-0076)."

    # La vue transverse voit **les deux** créneaux du tournoi, et aucun de l'autre tournoi. Les
    # ordres y repartent de 1 à chaque départ : ce n'est pas une séquence, et c'est le propos.
    du_tournoi = phases.par_tournoi(tournoi.id)
    assert len(du_tournoi) == 4, "par_tournoi couvre tous les départs du tournoi."
    assert {p.depart_id for p in du_tournoi} == {matin.id, apres_midi.id}

    placement = phases.par_depart_et_type(matin.id, TypePhase.PLACEMENT)
    assert placement is not None and placement.ordre == 1, "par_depart_et_type résout la phase."
    assert (
        phases.par_depart_et_type(matin.id, TypePhase.QUALIFICATION) is None
    ), "par_depart_et_type → None si le type est absent."

    # Une instance dont le rang n'existe pas au déroulé serait **invisible** à toute lecture (elle
    # n'a pas de définition à assembler) : les deux adapters refusent de l'écrire plutôt que de la
    # laisser croire posée. C'est exactement le genre d'écart qu'un second jeu d'adapters creuse.
    with pytest.raises(InfrastructureError):
        phases.ajouter(Phase.creer(matin.id, 9, TypePhase.PLACEMENT))


def _contrat_archer(
    tournois: TournoiRepository, categories: CategorieRepository, archers: ArcherRepository
) -> None:
    assert archers.par_id(999) is None, "par_id sur un identifiant absent → None."
    tournoi = tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
    autre = tournois.ajouter(Tournoi.creer("Autre salle", _DATE))
    assert tournoi.id is not None and autre.id is not None
    cat = categories.ajouter(Categorie.creer(tournoi.id, "Sénior"))
    cat_autre = categories.ajouter(Categorie.creer(autre.id, "Sénior"))
    assert cat.id is not None and cat_autre.id is not None

    ici = archers.ajouter(
        Archer(nom="Martin", prenom="Alice", tournoi_id=tournoi.id, categorie_id=cat.id)
    )
    archers.ajouter(Archer(nom="Durand", prenom="Bob", tournoi_id=tournoi.id, categorie_id=cat.id))
    archers.ajouter(
        Archer(nom="Petit", prenom="Chloé", tournoi_id=autre.id, categorie_id=cat_autre.id)
    )

    du_tournoi = archers.par_tournoi(tournoi.id)
    assert {a.nom for a in du_tournoi} == {
        "Martin",
        "Durand",
    }, "par_tournoi filtre par tournoi (aucune fuite inter-tournois)."
    assert ici.id is not None
    relu = archers.par_id(ici.id)
    assert relu is not None and relu.nom == "Martin", "par_id relit l'entité ajoutée."


def _contrat_gabarit(tournois: TournoiRepository, gabarits: GabaritSalleRepository) -> None:
    assert gabarits.par_id(999) is None, "par_id sur un identifiant absent → None."
    tournoi = tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
    assert tournoi.id is not None
    gabarits.ajouter(GabaritSalle(nom="Modèle", capacites=(4,), tournoi_id=None))  # bibliothèque
    gabarits.ajouter(GabaritSalle(nom="Instance", capacites=(4,), tournoi_id=tournoi.id))

    assert [g.nom for g in gabarits.lister()] == [
        "Modèle"
    ], "lister ne renvoie que les modèles (tournoi_id is None)."
    instance = gabarits.par_tournoi(tournoi.id)
    assert instance is not None and instance.nom == "Instance", "par_tournoi rend l'instance."
    assert gabarits.par_tournoi(999) is None, "par_tournoi → None si le tournoi n'a pas d'instance."


# --- Un test par (contrat, adapter) ; les deux adapters passent le même contrat -------------------


def test_tournoi_memoire() -> None:
    _contrat_tournoi(InMemoryTournoiRepository())


def test_tournoi_sql(base_sql: Database) -> None:
    _contrat_tournoi(TournoiRepositorySQL(base_sql.session_factory))


def test_phase_memoire() -> None:
    departs = InMemoryDepartRepository()
    deroules = InMemoryDerouleRepository()
    _contrat_phase(
        InMemoryTournoiRepository(),
        InMemoryPhaseRepository(departs, deroules),
        departs,
        deroules,
    )


def test_phase_sql(base_sql: Database) -> None:
    _contrat_phase(
        TournoiRepositorySQL(base_sql.session_factory),
        PhaseRepositorySQL(base_sql.session_factory),
        DepartRepositorySQL(base_sql.session_factory),
        DerouleEtapeRepositorySQL(base_sql.session_factory),
    )


def test_archer_memoire() -> None:
    _contrat_archer(
        InMemoryTournoiRepository(),
        InMemoryCategorieRepository(),
        InMemoryArcherRepository(),
    )


def test_archer_sql(base_sql: Database) -> None:
    fabrique = base_sql.session_factory
    _contrat_archer(
        TournoiRepositorySQL(fabrique),
        CategorieRepositorySQL(fabrique),
        ArcherRepositorySQL(fabrique),
    )


def test_gabarit_memoire() -> None:
    _contrat_gabarit(InMemoryTournoiRepository(), InMemoryGabaritSalleRepository())


def test_gabarit_sql(base_sql: Database) -> None:
    fabrique = base_sql.session_factory
    _contrat_gabarit(TournoiRepositorySQL(fabrique), GabaritSalleRepositorySQL(fabrique))
