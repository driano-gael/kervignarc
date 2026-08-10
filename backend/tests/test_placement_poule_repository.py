"""Tests d'intégration du repository SQL du plan de **poules** (E05US023, [ADR-0083] §3).

Exerce l'adapter sur une **vraie base** migrée (`alembic upgrade head`) : aller-retour d'un plan,
remplacement intégral, ordre de restitution, invariant « un couloir, un occupant » tenu par la base,
et `ON DELETE CASCADE` vers la phase. Tests **après** l'implémentation (adapter, pas d'oracle
métier — règle 9).

**Le décor est plus léger que celui de `placement_tableau`**, et l'écart dit tout du format : ce
plan-ci n'a besoin ni d'archer, ni d'inscription, ni de catégorie. L'unité posée est la **poule**,
pas l'archer — le membre au repos change à chaque tour, donc aucun membre n'a de couloir attitré, et
persister l'archer écrirait une information *fausse*. Un test dont le décor n'a pas d'archer est la
forme la plus courte de cette affirmation.

[ADR-0083]: ../../docs/adr/0083-le-contrat-de-phase-jouable.md
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
import sqlalchemy as sa

from domain.depart import Depart
from domain.phase import Phase, TypePhase
from domain.placement_poules import BlocDePoule
from domain.tournoi import Tournoi
from infrastructure.db import (
    Database,
    DepartRepositorySQL,
    PlacementPouleRepositorySQL,
    TournoiRepositorySQL,
)
from infrastructure.erreurs import InfrastructureError
from tests.base_migree import preparer_base
from tests.conftest import poser_phase_sql

_DATE = datetime.date(2026, 3, 14)


class _Decor:
    """Base jetable migrée + tournoi / départ / phase de poules."""

    def __init__(self, tmp_path: Path) -> None:
        url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
        preparer_base(url)
        self.db = Database(url)
        tournoi = TournoiRepositorySQL(self.db.session_factory).ajouter(
            Tournoi.creer("Salle 18m", _DATE)
        )
        assert tournoi.id is not None
        self.tournoi_id = tournoi.id
        depart = DepartRepositorySQL(self.db.session_factory).ajouter(
            Depart.creer(self.tournoi_id, 1, 0, "09:00")
        )
        assert depart.id is not None
        self.depart_id = depart.id
        phase = poser_phase_sql(
            self.db.session_factory, Phase.creer(self.tournoi_id, 2, TypePhase.POULES)
        )
        assert phase.id is not None
        self.phase_id = phase.id

    @property
    def placements(self) -> PlacementPouleRepositorySQL:
        return PlacementPouleRepositorySQL(self.db.session_factory)


def test_definir_plan_puis_relire(tmp_path: Path) -> None:
    """Un bloc fait l'aller-retour **dans son ordre de remplissage**, débordement compris.

    Le plan posé ici est celui du CA : deux poules de 4 sur une salle de cibles à 4 couloirs, la
    seconde commençant au couloir libre juste après la première — donc à cheval si la première a
    débordé. Ce qui se vérifie n'est pas seulement « les couloirs sont là » mais « dans cet
    ordre » : c'est de l'ordre du bloc que se dérivent les couloirs de chaque rencontre.
    """
    decor = _Decor(tmp_path)
    try:
        blocs = [
            BlocDePoule(poule=1, places=((1, "A"), (1, "B"), (1, "C"), (1, "D"))),
            BlocDePoule(poule=2, places=((2, "A"), (2, "B"), (2, "C"), (2, "D"))),
        ]

        decor.placements.definir_plan(decor.phase_id, blocs)

        assert decor.placements.par_phase(decor.phase_id) == blocs
    finally:
        decor.db.engine.dispose()


def test_un_bloc_qui_deborde_se_relit_dans_lordre_et_non_par_cible(tmp_path: Path) -> None:
    """⚠️ Le tri porte sur `(poule, rang)`, **jamais** sur `(cible, couloir)`.

    Les deux donneraient le même résultat sur une salle homogène — et divergeraient dès qu'une
    poule occupe la fin d'une cible puis le début de la suivante avec un couloir de moindre lettre.
    Ici la poule 1 finit en cible 1 couloir D et reprend en cible 2 couloir A : trier par cible
    marcherait encore. Mais la poule 2 démarre en cible 2 couloir B, et un tri par cible mêlerait
    les deux blocs. C'est le rang, et lui seul, qui rend la lecture sûre.
    """
    decor = _Decor(tmp_path)
    try:
        poule_1 = BlocDePoule(poule=1, places=((1, "C"), (1, "D"), (2, "A")))
        poule_2 = BlocDePoule(poule=2, places=((2, "B"), (2, "C")))

        decor.placements.definir_plan(decor.phase_id, [poule_1, poule_2])

        assert decor.placements.par_phase(decor.phase_id) == [poule_1, poule_2]
    finally:
        decor.db.engine.dispose()


def test_definir_plan_remplace_tout(tmp_path: Path) -> None:
    """Reposer le plan purge l'ancien — c'est le seul geste d'ajustement qu'offre le port.

    Un plan de poules ne se déplace pas archer par archer : l'organisateur déplace une **poule**,
    ce qui revient à reposer l'ensemble. Offrir un upsert par couloir, comme le fait le plan de
    duels, inviterait à casser la contiguïté du bloc — l'invariant de tout le format.
    """
    decor = _Decor(tmp_path)
    try:
        decor.placements.definir_plan(
            decor.phase_id, [BlocDePoule(poule=1, places=((1, "A"), (1, "B")))]
        )
        decor.placements.definir_plan(
            decor.phase_id, [BlocDePoule(poule=1, places=((3, "C"), (3, "D")))]
        )

        assert decor.placements.par_phase(decor.phase_id) == [
            BlocDePoule(poule=1, places=((3, "C"), (3, "D")))
        ]
    finally:
        decor.db.engine.dispose()


def test_un_plan_non_pose_se_lit_comme_une_liste_vide(tmp_path: Path) -> None:
    """L'absence *est* l'information (même parti qu'ADR-0024) : pas de plan, pas d'exception."""
    decor = _Decor(tmp_path)
    try:
        assert decor.placements.par_phase(decor.phase_id) == []
    finally:
        decor.db.engine.dispose()


def test_deux_poules_ne_peuvent_pas_partager_un_couloir(tmp_path: Path) -> None:
    """L'invariant *un couloir, un occupant* est tenu par la **base**, pas par le seul service.

    C'est la raison pour laquelle la clé primaire est le couloir (`phase_id, cible_index,
    position`) et non la poule : deux archers sur le même couloir est la faute qui se voit le plus
    tard — au moment où ils se présentent devant la cible. Un service peut se tromper ; une clé
    primaire, non.

    L'exception attendue est `InfrastructureError` et non l'`IntegrityError` de SQLAlchemy :
    l'adapter **enveloppe** les pannes du moteur (ADR-0007), et c'est ce contrat-là qu'on garde. Le
    vérifier sur l'erreur brute lierait le test à l'implémentation du driver.
    """
    decor = _Decor(tmp_path)
    try:
        with pytest.raises(InfrastructureError):
            decor.placements.definir_plan(
                decor.phase_id,
                [
                    BlocDePoule(poule=1, places=((1, "A"), (1, "B"))),
                    BlocDePoule(poule=2, places=((1, "B"), (1, "C"))),
                ],
            )
    finally:
        decor.db.engine.dispose()


def test_le_plan_disparait_avec_sa_phase(tmp_path: Path) -> None:
    """`ON DELETE CASCADE` sur `phase_id` — donnée dérivée, feuille (exception DETTE-001).

    ⚠️ Le `PRAGMA foreign_keys` est activé par le moteur d'`infrastructure/db/engine.py` ; ce test
    passe donc par ce moteur-là, et non par une connexion nue. C'est le piège que les migrations
    `0042` et `0044` documentent : sous SQLite, une cascade déclarée n'est pas une cascade active.
    """
    decor = _Decor(tmp_path)
    try:
        decor.placements.definir_plan(
            decor.phase_id, [BlocDePoule(poule=1, places=((1, "A"), (1, "B")))]
        )

        with decor.db.session_factory() as session:
            session.execute(sa.text("DELETE FROM phase WHERE id = :id"), {"id": decor.phase_id})
            session.commit()

        assert decor.placements.par_phase(decor.phase_id) == []
    finally:
        decor.db.engine.dispose()
