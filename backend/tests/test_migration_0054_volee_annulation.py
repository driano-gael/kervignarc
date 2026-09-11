"""Migration 0054 — l'acte de validation devient identifiable, sans rien changer pour personne.

Test **de non-régression** au sens de la règle 9 : l'oracle est le comportement décrit par la
docstring de la migration, et l'implémenteur est le mieux placé pour l'écrire.

⚠️ **Écrit en revue d'E16US019, où il manquait.** Le backfill ne fait pas que « remplir une
colonne » : il établit l'invariant dont `Serie.annuler_validation` dépend — `lot_validation` non
`NULL` **si et seulement si** `validee_par` l'est. Les tests de repository tournent sur une base
montée en tête de chaîne : ils prouvent le schéma d'arrivée, jamais le chemin de **reprise**, qui
est pourtant la seule garantie faite aux bases déjà en salle.

Ce que ces tests gardent :

1. une volée **déjà validée** ressort avec `lot_validation = numero` — un lot par volée, la seule
   convention honnête puisque les lots d'avant l'US n'ont laissé aucune trace ;
2. une volée **non validée** garde `lot_validation` à `NULL` — sans quoi l'invariant serait faux
   dans l'autre sens et `annuler_validation` rouvrirait des volées jamais validées ;
3. la descente retire les deux colonnes sans échouer, y compris avec une correction en cours.

Les clés étrangères sont désactivées côté Alembic (`env.py`) : on insère une volée sans matérialiser
sa série, comme les tests de migration voisins.
"""

from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

_BACKEND_ROOT = Path(__file__).resolve().parents[1]

_AVANT = "0053_placement_tableau_par_tour"
_ANNULATION = "0054_volee_annulation_validation"


def _config(url: str) -> Config:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _base(tmp_path: Path, nom: str) -> tuple[sa.Engine, Config]:
    """Une base montée **jusqu'à la veille** de 0054, avec deux volées déjà dedans.

    La volée 1 est validée (elle « compte »), la volée 2 seulement saisie — les deux états que le
    backfill doit distinguer.
    """
    url = f"sqlite:///{(tmp_path / nom).as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, _AVANT)
    engine = sa.create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO volee (serie_id, numero, valeurs, saisie_par, validee_par) VALUES "
                "(7, 1, '[\"10\",\"9\",\"8\"]', 'DURAND', 'MARTIN'), "
                '(7, 2, \'["9","9","9"]\', \'DURAND\', NULL)'
            )
        )
    return engine, cfg


def _lots(engine: sa.Engine) -> list[tuple[int, int | None, str | None]]:
    with engine.begin() as conn:
        lignes = conn.execute(
            sa.text(
                "SELECT numero, lot_validation, correction_ouverte_par FROM volee ORDER BY numero"
            )
        ).all()
    return [(ligne[0], ligne[1], ligne[2]) for ligne in lignes]


def test_une_volee_deja_validee_devient_son_propre_lot(tmp_path: Path) -> None:
    """La conséquence assumée : sur un tournoi antérieur, annuler rouvre **la volée seule**.

    Les lots d'avant l'US ne sont pas connus — aucune trace ne les distinguait — et les inventer
    par le grain serait faux, puisque le grain a pu changer entre-temps.
    """
    engine, cfg = _base(tmp_path, "reprise.db")

    command.upgrade(cfg, _ANNULATION)

    assert _lots(engine) == [(1, 1, None), (2, None, None)]
    engine.dispose()


def test_le_backfill_tient_l_invariant_dans_les_deux_sens(tmp_path: Path) -> None:
    """`lot_validation` non `NULL` **si et seulement si** `validee_par` l'est.

    ⚠️ C'est la moitié qu'on oublie : un backfill qui remplirait *toutes* les lignes passerait le
    test précédent et casserait `Serie.annuler_validation`, qui déduit de ce lot quelles volées
    rouvrir — une volée jamais validée en recevrait un, et se rouvrirait avec le lot voisin.
    """
    engine, cfg = _base(tmp_path, "invariant.db")

    command.upgrade(cfg, _ANNULATION)

    with engine.begin() as conn:
        incoherentes = conn.execute(
            sa.text(
                "SELECT COUNT(*) FROM volee "
                "WHERE (validee_par IS NULL) <> (lot_validation IS NULL)"
            )
        ).scalar_one()
    assert incoherentes == 0
    engine.dispose()


def test_la_descente_retire_les_colonnes_meme_avec_une_correction_en_cours(
    tmp_path: Path,
) -> None:
    """Le `downgrade` est destructeur et l'assume : une correction en cours redevient un verrou."""
    engine, cfg = _base(tmp_path, "descente.db")
    command.upgrade(cfg, _ANNULATION)
    with engine.begin() as conn:
        conn.execute(sa.text("UPDATE volee SET correction_ouverte_par = 'MARTIN' WHERE numero = 1"))

    command.downgrade(cfg, _AVANT)

    with engine.begin() as conn:
        colonnes = {ligne[1] for ligne in conn.execute(sa.text("PRAGMA table_info(volee)")).all()}
    assert "lot_validation" not in colonnes
    assert "correction_ouverte_par" not in colonnes
    engine.dispose()
