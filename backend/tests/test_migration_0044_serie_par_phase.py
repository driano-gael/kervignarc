"""Migration 0044 — la feuille de marque se rattache à sa phase (E05US025, ADR-0082).

**234 lignes de reprise de données que rien n'exécutait** (relevé de revue) : `base_migree.py` ne
rejoue `upgrade head` que sur une base **vide**, et `backend/migrations/` est exclu de mypy. Ni les
trois cas de reprise, ni le `DELETE` journalisé, ni le `downgrade` n'étaient couverts — alors que
cette migration touche la seule table qui contient des **scores**, sur des bases déjà remplies.

Ce que ces tests éprouvent :

1. **les trois cas de reprise** — l'archer inscrit à un créneau doté d'une qualification, celui qui
   n'en a pas (repli sur la première du tournoi), et la série d'un tournoi sans aucune
   qualification (supprimée, avec ses volées) ;
2. **les volées ne restent jamais orphelines**, dans les deux sens. `volee.serie_id` est en
   `ON DELETE CASCADE`, mais Alembic n'active pas `PRAGMA foreign_keys` — c'est le piège que la
   `0042` documente et que la `0044` reproduisait ;
3. **l'aller-retour `upgrade → downgrade → upgrade`** sur un déroulé à deux qualifications, où le
   modèle antérieur n'a qu'un emplacement par `(tournoi, archer)`.

Test **de non-régression** au sens de la règle 9 : l'oracle est le comportement décrit par la
docstring de la migration, et l'implémenteur est le mieux placé pour l'écrire.

Les clés étrangères sont désactivées côté Alembic (`env.py`) : on insère des identifiants parents
fictifs sans matérialiser toute la descendance, comme les tests de migration voisins.
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

_BACKEND_ROOT = Path(__file__).resolve().parents[1]

_AVANT = "0043_deroule_defini_une_fois"
_SERIE_PAR_PHASE = "0044_serie_par_phase"

_CONFIG_QUALIF: dict[str, object] = {
    "policies": {"scoring": {"nom": "cumul", "volees": 12, "fleches": 3}},
    "validation": {"grain": "fin_de_serie"},
}


def _config(url: str) -> Config:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _base(tmp_path: Path, nom: str) -> tuple[sa.Engine, Config]:
    url = f"sqlite:///{(tmp_path / nom).as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, _AVANT)
    return sa.create_engine(url), cfg


def _tournoi(conn: sa.Connection, tournoi_id: int) -> None:
    conn.execute(
        sa.text(
            "INSERT INTO tournoi (id, nom, date, statut, type_tournoi) "
            "VALUES (:id, :nom, '2026-03-14', 'brouillon', 'non_officiel')"
        ),
        {"id": tournoi_id, "nom": f"Tournoi {tournoi_id}"},
    )


def _depart(conn: sa.Connection, depart_id: int, tournoi_id: int, numero: int) -> None:
    conn.execute(
        sa.text(
            "INSERT INTO depart (id, tournoi_id, numero, horaire, tarif_centimes, quota) "
            "VALUES (:id, :tournoi_id, :numero, '09:00', 800, NULL)"
        ),
        {"id": depart_id, "tournoi_id": tournoi_id, "numero": numero},
    )


def _etape(conn: sa.Connection, etape_id: int, tournoi_id: int, ordre: int) -> None:
    """Une étape de déroulé de type `qualification` : c'est elle qui porte le type (ADR-0076)."""
    conn.execute(
        sa.text(
            "INSERT INTO deroule_etape (id, tournoi_id, ordre, type, config) "
            "VALUES (:id, :tournoi_id, :ordre, 'qualification', :config)"
        ),
        {
            "id": etape_id,
            "tournoi_id": tournoi_id,
            "ordre": ordre,
            "config": json.dumps(_CONFIG_QUALIF),
        },
    )


def _phase(conn: sa.Connection, phase_id: int, depart_id: int, ordre: int) -> None:
    conn.execute(
        sa.text(
            "INSERT INTO phase (id, depart_id, ordre, statut) "
            "VALUES (:id, :depart_id, :ordre, 'a_venir')"
        ),
        {"id": phase_id, "depart_id": depart_id, "ordre": ordre},
    )


def _inscription(conn: sa.Connection, inscription_id: int, archer_id: int, depart_id: int) -> None:
    conn.execute(
        sa.text(
            "INSERT INTO inscription (id, archer_id, depart_id, paye) "
            "VALUES (:id, :archer_id, :depart_id, 0)"
        ),
        {"id": inscription_id, "archer_id": archer_id, "depart_id": depart_id},
    )


def _serie(conn: sa.Connection, serie_id: int, tournoi_id: int, archer_id: int) -> None:
    """Une série d'avant la 0044 : elle pend au tournoi, et porte une volée."""
    conn.execute(
        sa.text(
            "INSERT INTO serie (id, tournoi_id, archer_id) " "VALUES (:id, :tournoi_id, :archer_id)"
        ),
        {"id": serie_id, "tournoi_id": tournoi_id, "archer_id": archer_id},
    )
    conn.execute(
        sa.text(
            "INSERT INTO volee (id, serie_id, numero, valeurs, saisie_par) "
            "VALUES (:id, :serie_id, 1, :valeurs, 'DURAND Jean')"
        ),
        {"id": serie_id * 10, "serie_id": serie_id, "valeurs": json.dumps(["10", "9", "8"])},
    )


def _rattachements(engine: sa.Engine) -> list[tuple[int, int | None]]:
    """`(id de série, phase_id)` — l'état d'après la reprise."""
    with engine.connect() as conn:
        lignes = conn.execute(sa.text("SELECT id, phase_id FROM serie ORDER BY id")).all()
    return [(int(a), None if b is None else int(b)) for a, b in lignes]


def _volees(engine: sa.Engine) -> list[int]:
    """Les `serie_id` encore référencés par une volée, triés — pour traquer les orphelines."""
    with engine.connect() as conn:
        return [int(x) for x in conn.execute(sa.text("SELECT serie_id FROM volee")).scalars()]


# --- Reprise des données -------------------------------------------------------------------------


def test_la_serie_suit_le_creneau_ou_l_archer_est_inscrit(tmp_path: Path) -> None:
    """Cas 1 — l'archer inscrit à un créneau doté d'une qualification y voit sa feuille rattachée.

    Deux créneaux, chacun avec sa qualification ; deux archers, chacun inscrit sur l'un des deux.
    C'est le seul décor où « la qualification du tournoi » et « celle du créneau » diffèrent — donc
    le seul qui puisse voir la reprise se tromper. C'est aussi `DETTE-046` vue de l'autre bout.
    """
    engine, cfg = _base(tmp_path, "cas1.db")
    with engine.begin() as conn:
        _tournoi(conn, 1)
        _depart(conn, 41, tournoi_id=1, numero=1)
        _depart(conn, 42, tournoi_id=1, numero=2)
        _etape(conn, 7, tournoi_id=1, ordre=1)
        _phase(conn, 101, depart_id=41, ordre=1)
        _phase(conn, 102, depart_id=42, ordre=1)
        _inscription(conn, 1, archer_id=10, depart_id=41)
        _inscription(conn, 2, archer_id=11, depart_id=42)
        _serie(conn, 1, tournoi_id=1, archer_id=10)
        _serie(conn, 2, tournoi_id=1, archer_id=11)

    command.upgrade(cfg, _SERIE_PAR_PHASE)

    assert _rattachements(engine) == [(1, 101), (2, 102)]
    engine.dispose()


def test_l_archer_sans_inscription_retombe_sur_la_premiere_qualification(tmp_path: Path) -> None:
    """Cas 2 — repli sur la première qualification du tournoi (départ de numéro le plus bas).

    C'est mot pour mot ce que faisait `portee.qualification_du_tournoi`, que tous les lecteurs
    empruntaient : le comportement observable est **inchangé** pour ces lignes.
    """
    engine, cfg = _base(tmp_path, "cas2.db")
    with engine.begin() as conn:
        _tournoi(conn, 1)
        _depart(conn, 41, tournoi_id=1, numero=1)
        _depart(conn, 42, tournoi_id=1, numero=2)
        _etape(conn, 7, tournoi_id=1, ordre=1)
        _phase(conn, 101, depart_id=41, ordre=1)
        _phase(conn, 102, depart_id=42, ordre=1)
        _serie(conn, 1, tournoi_id=1, archer_id=10)  # aucune inscription

    command.upgrade(cfg, _SERIE_PAR_PHASE)

    assert _rattachements(engine) == [(1, 101)]
    engine.dispose()


def test_la_serie_sans_qualification_part_avec_ses_volees(tmp_path: Path) -> None:
    """Cas 3 — la seule perte délibérée de la migration, **et elle n'abandonne rien derrière elle**.

    ⚠️ `volee.serie_id` déclare `ON DELETE CASCADE`, mais Alembic n'active pas
    `PRAGMA foreign_keys` : s'en remettre à la cascade laissait des volées orphelines. `serie.id`
    étant un rowid **réutilisable**, une feuille créée plus tard en aurait hérité — une feuille de
    marque corrompue en silence. C'est le piège que la `0042` documente ; ce test le ferme.
    """
    engine, cfg = _base(tmp_path, "cas3.db")
    with engine.begin() as conn:
        _tournoi(conn, 1)
        _depart(conn, 41, tournoi_id=1, numero=1)
        _serie(conn, 1, tournoi_id=1, archer_id=10)  # aucune qualification dans ce tournoi

    command.upgrade(cfg, _SERIE_PAR_PHASE)

    assert _rattachements(engine) == [], "La série sans rattachement sportif est supprimée."
    assert _volees(engine) == [], "…et ses volées avec elle, pas laissées orphelines."
    engine.dispose()


# --- Aller-retour ---------------------------------------------------------------------------------


def test_le_downgrade_ne_garde_qu_une_feuille_et_purge_les_autres_volees(tmp_path: Path) -> None:
    """Le modèle antérieur n'a qu'un emplacement par `(tournoi, archer)` : la plus précoce reste.

    Et l'aller-retour `upgrade → downgrade → upgrade` doit rester praticable — une base bloquée à
    mi-migration n'a pas de chemin de sortie le jour J.
    """
    engine, cfg = _base(tmp_path, "aller_retour.db")
    with engine.begin() as conn:
        _tournoi(conn, 1)
        _depart(conn, 41, tournoi_id=1, numero=1)
        _etape(conn, 7, tournoi_id=1, ordre=1)
        _phase(conn, 101, depart_id=41, ordre=1)
        _inscription(conn, 1, archer_id=10, depart_id=41)
        _serie(conn, 1, tournoi_id=1, archer_id=10)
    command.upgrade(cfg, _SERIE_PAR_PHASE)
    # Une seconde qualification, et la feuille que l'archer y tient : l'état que le modèle
    # antérieur ne sait pas représenter.
    with engine.begin() as conn:
        _etape(conn, 8, tournoi_id=1, ordre=2)
        _phase(conn, 102, depart_id=41, ordre=2)
        conn.execute(
            sa.text(
                "INSERT INTO serie (id, tournoi_id, archer_id, phase_id) VALUES (2, 1, 10, 102)"
            )
        )
        conn.execute(
            sa.text(
                "INSERT INTO volee (id, serie_id, numero, valeurs, saisie_par) "
                "VALUES (20, 2, 1, :valeurs, 'DURAND Jean')"
            ),
            {"valeurs": json.dumps(["7", "6", "M"])},
        )

    command.downgrade(cfg, _AVANT)

    with engine.connect() as conn:
        restantes = [int(x) for x in conn.execute(sa.text("SELECT id FROM serie")).scalars()]
    assert restantes == [1], "Seule la feuille de la qualification la plus précoce est conservée."
    assert _volees(engine) == [1], "Les volées de la feuille écartée partent avec elle."

    command.upgrade(cfg, _SERIE_PAR_PHASE)  # ne doit pas rester bloqué à mi-chemin
    assert _rattachements(engine) == [(1, 101)]
    engine.dispose()
