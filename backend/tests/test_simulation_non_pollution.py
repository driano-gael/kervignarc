"""Non-pollution de la **vraie base** par la simulation éphémère (E15US002, ADR-0054) — intégration.

Le test de service (`test_service_simulation.py`) prouve le rejeu et la non-pollution *au niveau du
mécanisme* (repositories réels inchangés). Ici on va au bout du CA « non-pollution **vérifiable** »
: sur une **vraie base SQLite migrée**, on **photographie le contenu** de chaque table (les lignes
elles-mêmes, pas seulement leur nombre — un UPDATE en place laisserait le compte inchangé), on lance
une simulation, et on vérifie que **rien n'a bougé**. Deux chemins sont exercés contre la vraie
base : le **classement** (scénario du jeu d'essai) et les **duels** (`regenerer`, la seule écriture
du moteur — via un tournoi doté d'une salle et d'une phase de tableau). C'est la garantie que la
simulation câblée sur des adapters in-memory n'atteint jamais SQLite.
"""

from __future__ import annotations

import datetime
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy import text

from bootstrap.composition import create_app
from domain.gabarit_salle import GabaritSalle
from domain.phase import Phase, TypePhase
from infrastructure.db import GabaritSalleRepositorySQL, PhaseRepositorySQL

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


@pytest.fixture
def app_simulation(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _photo(app: FastAPI) -> dict[str, list[str]]:
    """Contenu de chaque table applicative : la liste **triée** de ses lignes (repr stable).

    Par **contenu** et non par `count(*)` : une modification **en place** (UPDATE) laisse le compte
    inchangé mais changerait une ligne — la photo de contenu l'attrape, le compteur la manquerait.
    Le nom de table vient de `sqlite_master` (schéma de confiance), jamais d'une entrée utilisateur.
    """
    with app.state.database.engine.connect() as conn:
        tables = [
            nom
            for nom in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'table'")
            ).scalars()
            if not nom.startswith("sqlite_") and not nom.startswith("alembic")
        ]
        return {
            table: sorted(
                repr(tuple(row))
                for row in conn.execute(text(f'SELECT * FROM "{table}"')).fetchall()
            )
            for table in tables
        }


def test_une_simulation_ne_modifie_pas_la_base(app_simulation: FastAPI) -> None:
    """Peupler un scénario, simuler, et constater la base **strictement inchangée**."""
    resultat = app_simulation.state.service_jeu_essai.instancier("petit", _DATE)
    tournoi_id = resultat.tournoi_id

    avant = _photo(app_simulation)
    assert len(avant.get("archer", [])) >= 1, "Le scénario a peuplé la base (préalable du test)."

    simulation = app_simulation.state.service_simulation.simuler(tournoi_id)
    assert simulation.tournoi_id == tournoi_id
    # **Fidélité SQL → in-memory** : le classement simulé (hydraté depuis SQLite) est **identique**
    # à celui que la production calcule sur les mêmes adapters SQL — l'hydratation ne perd rien.
    # (On compare le contenu, pas seulement le nombre de lignes.)
    oracle_sql = app_simulation.state.service_classement.pour_tournoi(tournoi_id)
    assert simulation.classement == oracle_sql

    apres = _photo(app_simulation)
    assert apres == avant, "La simulation a écrit dans la vraie base — non-pollution violée."


def test_le_chemin_duels_ne_pollue_pas_la_base(app_simulation: FastAPI) -> None:
    """Chemin **duels** contre la vraie base : `regenerer` (seule écriture du moteur) n'atteint pas
    SQLite.

    Le scénario « petit » n'a ni salle ni phase de tableau — le moteur ne tenterait aucune écriture,
    et le test qualif ne couvrirait donc pas le chemin le plus exposé (`ServicePlacementDuels`). On
    **ajoute** donc au tournoi une salle et une phase d'élimination directe (données réelles), pour
    que `simuler` exerce réellement `regenerer` (qui matérialise un plan de duels). Ce plan doit
    atterrir dans le harnais in-memory — **jamais** dans la table `placement_tableau` réelle. Une
    régression qui recâblerait un repo réel dans le harnais écrirait ici, et la photo de contenu
    l'attraperait.
    """
    resultat = app_simulation.state.service_jeu_essai.instancier("petit", _DATE)
    tournoi_id = resultat.tournoi_id
    fabrique = app_simulation.state.database.session_factory
    GabaritSalleRepositorySQL(fabrique).ajouter(
        GabaritSalle(nom="Salle", capacites=(4, 4, 4, 4, 4), tournoi_id=tournoi_id)
    )
    PhaseRepositorySQL(fabrique).ajouter(Phase.creer(tournoi_id, 2, TypePhase.ELIMINATION_DIRECTE))

    avant = _photo(app_simulation)  # photo APRÈS l'ajout salle + phase (données réelles assumées)
    simulation = app_simulation.state.service_simulation.simuler(tournoi_id)
    assert simulation.tableaux, "Le moteur a bien joué la phase de tableau (chemin duels exercé)."

    apres = _photo(app_simulation)
    assert apres == avant, "regenerer a écrit dans la vraie base — non-pollution violée."


def test_simuler_un_tournoi_demarre_est_refuse_sans_ecrire(app_simulation: FastAPI) -> None:
    """Le garde-fou tient aussi sur la vraie base : un tournoi démarré est refusé, base intacte."""
    from application.erreurs import SimulationTournoiDemarre

    resultat = app_simulation.state.service_jeu_essai.instancier("petit", _DATE)
    # Passer prêt puis démarrer via le service de cycle de vie (donnée réelle).
    app_simulation.state.service_tournois.vers_pret(resultat.tournoi_id)
    app_simulation.state.service_tournois.demarrer(resultat.tournoi_id)

    avant = _photo(app_simulation)
    with pytest.raises(SimulationTournoiDemarre):
        app_simulation.state.service_simulation.simuler(resultat.tournoi_id)
    assert _photo(app_simulation) == avant
