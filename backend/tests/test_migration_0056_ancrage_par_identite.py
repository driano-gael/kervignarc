"""Migration 0056 — la séquence s'ancre sur l'identité de l'étape (E05US022, ADR-0078).

La suite d'API migre toujours une base **vide** jusqu'à `head` (`base_migree.py`) : les trois
gestes de **données** de cette migration — remplir `phase.etape_id` par la jointure d'hier,
réécrire les `config`, supprimer les avancements orphelins — ne seraient exercés sur aucune ligne.
C'est le défaut que la revue a relevé en bloquant : le dépôt compte quatorze tests de migration, et
celle-ci en manquait.

Test **de non-régression** au sens de la règle 9 : l'oracle est le comportement décrit par la
docstring de la migration, et l'auteur de la migration est le mieux placé pour l'écrire.

⚠️ **Deux tournois, aux mêmes rangs.** C'est le décor qui fait la preuve : la résolution
`rang → identité` doit se faire **dans le tournoi de l'étape**, et un décor mono-tournoi passerait
avec une résolution globale fausse.

Les clés étrangères sont désactivées côté Alembic (`env.py`) : on insère des identifiants parents
fictifs sans matérialiser les lignes — même geste que les tests de migration 0018/0020/0032/0036.
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_AVANT = "0055_volee_role_de_saisie"
_APRES = "0056_ancrage_par_identite"


def _config(url: str) -> Config:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _etape(conn: sa.Connection, identifiant: int, tournoi: int, ordre: int, config: object) -> None:
    conn.execute(
        sa.text(
            "INSERT INTO deroule_etape (id, tournoi_id, ordre, type, config) "
            "VALUES (:id, :tournoi, :ordre, 'placement', :config)"
        ),
        {"id": identifiant, "tournoi": tournoi, "ordre": ordre, "config": json.dumps(config)},
    )


def _phase(conn: sa.Connection, identifiant: int, depart: int, ordre: int) -> None:
    conn.execute(
        sa.text(
            "INSERT INTO phase (id, depart_id, ordre, statut) "
            "VALUES (:id, :depart, :ordre, 'a_venir')"
        ),
        {"id": identifiant, "depart": depart, "ordre": ordre},
    )


def _depart(conn: sa.Connection, identifiant: int, tournoi: int) -> None:
    conn.execute(
        sa.text(
            "INSERT INTO depart (id, tournoi_id, numero, horaire, tarif_centimes) "
            "VALUES (:id, :tournoi, :id, '09:00', 800)"
        ),
        {"id": identifiant, "tournoi": tournoi},
    )


def _semer(conn: sa.Connection) -> None:
    """Deux tournois aux **mêmes rangs**, deux créneaux, et les deux formes historiques de source.

    ⚠️ Les identités d'étape sont choisies **décalées des rangs** (41-43 pour le tournoi 1, 51-52
    pour le tournoi 2) : si elles coïncidaient, une résolution fautive passerait inaperçue.
    """
    _depart(conn, 1, tournoi=1)
    _depart(conn, 2, tournoi=1)
    _depart(conn, 3, tournoi=2)

    # Tournoi 1 : rangs 1, 2, 3. L'étape 3 prélève dans la 2 (forme E05US010, liste).
    _etape(conn, 41, tournoi=1, ordre=1, config={})
    _etape(conn, 42, tournoi=1, ordre=2, config={"effectif": 32})
    _etape(
        conn,
        43,
        tournoi=1,
        ordre=3,
        config={
            "sources": [{"nature": "rangs", "ordre_source": 2, "rang_debut": 1, "rang_fin": 8}]
        },
    )
    # Tournoi 2 : **mêmes rangs**, et la forme historique E05US001 (`config.source`, objet unique).
    _etape(conn, 51, tournoi=2, ordre=1, config={})
    _etape(
        conn,
        52,
        tournoi=2,
        ordre=2,
        config={"source": {"ordre_source": 1, "rang_debut": 1, "rang_fin": 4}},
    )

    for depart in (1, 2):
        for rang in (1, 2, 3):
            _phase(conn, identifiant=depart * 10 + rang, depart=depart, ordre=rang)
    _phase(conn, identifiant=31, depart=3, ordre=1)
    _phase(conn, identifiant=32, depart=3, ordre=2)
    # ⚠️ Orpheline : un rang qu'aucune étape ne porte. Déjà invisible à toute lecture avant la
    # migration (les deux adapters l'écartent), elle doit disparaître — `etape_id` est NOT NULL.
    _phase(conn, identifiant=99, depart=1, ordre=9)


def _configs(engine: sa.Engine) -> dict[int, dict[str, object]]:
    with engine.connect() as conn:
        lignes = conn.execute(sa.text("SELECT id, config FROM deroule_etape")).all()
    return {int(ligne[0]): json.loads(ligne[1]) for ligne in lignes}


def _rattachements(engine: sa.Engine) -> dict[int, int]:
    with engine.connect() as conn:
        lignes = conn.execute(sa.text("SELECT id, etape_id FROM phase")).all()
    return {int(ligne[0]): int(ligne[1]) for ligne in lignes}


def test_upgrade_rattache_l_avancement_a_l_etape_de_son_rang_dans_son_propre_tournoi(
    tmp_path: Path,
) -> None:
    """`phase.etape_id` reprend **exactement** la jointure que le code faisait à la lecture.

    Le tournoi 2 porte les mêmes rangs que le tournoi 1 : c'est ce qui prouve que la résolution
    est cloisonnée par tournoi, et pas globale.
    """
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, _AVANT)
    engine = sa.create_engine(url)
    try:
        with engine.begin() as conn:
            _semer(conn)

        command.upgrade(cfg, _APRES)

        rattachements = _rattachements(engine)
        # Départs 1 et 2 : tournoi 1, donc les étapes 41/42/43.
        assert rattachements[11] == 41 and rattachements[12] == 42 and rattachements[13] == 43
        assert rattachements[21] == 41 and rattachements[22] == 42 and rattachements[23] == 43
        # Départ 3 : tournoi 2, donc 51/52 — **pas** 41/42, malgré des rangs identiques.
        assert rattachements[31] == 51 and rattachements[32] == 52
    finally:
        engine.dispose()


def test_upgrade_supprime_l_avancement_orphelin(tmp_path: Path) -> None:
    """Un avancement dont le rang n'a aucune étape disparaît : `etape_id` est `NOT NULL`.

    Il était déjà invisible à toute lecture — les deux adapters l'écartent de l'assemblage —, donc
    rien d'observable n'est perdu. ⚠️ **Ce n'est pas le seul retrait de la reprise** : un
    prélèvement dont le rang ne se résout pas disparaît lui aussi (test ci-dessous). Les deux sont
    annoncés par la fiche fonctionnelle et comptés au journal d'Alembic.
    """
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, _AVANT)
    engine = sa.create_engine(url)
    try:
        with engine.begin() as conn:
            _semer(conn)

        command.upgrade(cfg, _APRES)

        with engine.connect() as conn:
            restantes = {int(r[0]) for r in conn.execute(sa.text("SELECT id FROM phase"))}
        assert 99 not in restantes
        assert restantes == {11, 12, 13, 21, 22, 23, 31, 32}
    finally:
        engine.dispose()


def test_upgrade_reecrit_les_deux_formes_historiques_de_prelevement(tmp_path: Path) -> None:
    """`config.sources` (E05US010) **et** `config.source` (E05US001) passent à l'identité.

    Oublier la seconde laisserait muets les prélèvements des plus vieux tournois : elle est
    normalisée en liste au passage, puisque le lecteur cible ne consulte plus `config.source`.
    """
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, _AVANT)
    engine = sa.create_engine(url)
    try:
        with engine.begin() as conn:
            _semer(conn)

        command.upgrade(cfg, _APRES)

        configs = _configs(engine)
        assert configs[43]["sources"] == [
            {"nature": "rangs", "rang_debut": 1, "rang_fin": 8, "etape_source_id": 42}
        ]
        # Forme ancienne : normalisée en liste, ancrée sur l'étape 51 (rang 1 **du tournoi 2**).
        assert configs[52]["sources"] == [{"rang_debut": 1, "rang_fin": 4, "etape_source_id": 51}]
        assert "source" not in configs[52]
        # Une étape sans prélèvement n'acquiert pas de clé `sources`.
        assert "sources" not in configs[41]
    finally:
        engine.dispose()


def test_upgrade_retire_un_prelevement_que_le_rang_ne_resout_pas(tmp_path: Path) -> None:
    """Un `ordre_source` sans étape est **retiré**, pas laissé sans ancre (correctif de revue).

    ⚠️ C'est le cas que la première rédaction laissait à demi écrit : la source repartait sans
    aucune ancre, et la relecture (`_vers_sources_d_etape`) faisait alors tomber **tout le
    déroulé** du tournoi en `InfrastructureError` — écran d'administration en erreur, sans recours.
    Le prélèvement ne désignait déjà rien ; le retirer conserve le comportement observé (inerte).
    """
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, _AVANT)
    engine = sa.create_engine(url)
    try:
        with engine.begin() as conn:
            _semer(conn)
            _etape(
                conn,
                44,
                tournoi=1,
                ordre=4,
                config={
                    "sources": [
                        {"nature": "rangs", "ordre_source": 1, "rang_debut": 1, "rang_fin": 2},
                        {"nature": "rangs", "ordre_source": 9, "rang_debut": 1, "rang_fin": 2},
                    ]
                },
            )

        command.upgrade(cfg, _APRES)

        sources = _configs(engine)[44]["sources"]
        assert sources == [
            {"nature": "rangs", "rang_debut": 1, "rang_fin": 2, "etape_source_id": 41}
        ], "le prélèvement résoluble survit, l'autre est retiré"
    finally:
        engine.dispose()


def test_l_aller_retour_restitue_les_rangs_et_les_ancres(tmp_path: Path) -> None:
    """`downgrade` rend `phase.ordre` et `ordre_source` — la migration est réellement réversible.

    Seule différence assumée, sans conséquence : la forme historique `config.source` ressort
    normalisée en `config.sources`, que le lecteur de `0055` acceptait déjà.
    """
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, _AVANT)
    engine = sa.create_engine(url)
    try:
        with engine.begin() as conn:
            _semer(conn)

        command.upgrade(cfg, _APRES)
        command.downgrade(cfg, _AVANT)

        with engine.connect() as conn:
            rangs = {
                int(r[0]): int(r[1]) for r in conn.execute(sa.text("SELECT id, ordre FROM phase"))
            }
        assert rangs == {11: 1, 12: 2, 13: 3, 21: 1, 22: 2, 23: 3, 31: 1, 32: 2}

        configs = _configs(engine)
        assert configs[43]["sources"] == [
            {"nature": "rangs", "rang_debut": 1, "rang_fin": 8, "ordre_source": 2}
        ]
        assert configs[52]["sources"] == [{"rang_debut": 1, "rang_fin": 4, "ordre_source": 1}]
    finally:
        engine.dispose()


def _preparer(tmp_path: Path) -> tuple[Config, sa.Engine]:
    """Base migrée jusqu'à `0055` et semée — le préambule commun des tests ci-dessous."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, _AVANT)
    engine = sa.create_engine(url)
    with engine.begin() as conn:
        _semer(conn)
    return cfg, engine


def test_upgrade_purge_les_trois_tables_filles_de_l_avancement_orphelin(tmp_path: Path) -> None:
    """Supprimer la phase 99 sans purger ses filles **casserait l'intégrité référentielle**.

    Aucune des trois FK n'est `ON DELETE CASCADE`, et Alembic tourne sans `PRAGMA foreign_keys` :
    la suppression passerait en silence et la base sortirait de la migration dans un état que son
    propre runtime (`engine.py`, FK actives) refuse. `barrage.phase_id` étant **nullable**, la
    ligne survit détachée — un barrage est un tir réellement effectué.
    """
    cfg, engine = _preparer(tmp_path)
    try:
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO franchissement_arret (phase_id, apres_tour, etat) "
                    "VALUES (99, 1, 'ouvert')"
                )
            )
            conn.execute(
                sa.text(
                    "INSERT INTO arret_de_circonstance (depart_id, phase_id, apres_tour, portee) "
                    "VALUES (1, 99, 1, 'depart')"
                )
            )
            conn.execute(
                sa.text(
                    "INSERT INTO barrage "
                    "(id, phase_id, portee, participants_json, cree_le, depart_id) "
                    "VALUES (7, 99, 'phase', '[]', '2026-09-20T09:00:00', 1)"
                )
            )

        command.upgrade(cfg, _APRES)

        with engine.connect() as conn:
            # ⚠️ Filtré sur le parent `phase` : le décor insère des parents **fictifs** (tournoi,
            # depart), FK désactivées côté Alembic, donc un `foreign_key_check` nu remonte le
            # décor lui-même. C'est bien la phase disparue que ce test surveille.
            manquements = [
                violation
                for violation in conn.execute(sa.text("PRAGMA foreign_key_check")).all()
                if violation[2] == "phase"
            ]
            franchissements = conn.execute(
                sa.text("SELECT COUNT(*) FROM franchissement_arret")
            ).scalar_one()
            arrets = conn.execute(
                sa.text("SELECT COUNT(*) FROM arret_de_circonstance")
            ).scalar_one()
            # `scalar_one` : la ligne doit **exister** (sinon le barrage a été supprimé, pas
            # détaché) et son `phase_id` valoir `None`.
            barrage = conn.execute(
                sa.text("SELECT phase_id FROM barrage WHERE id = 7")
            ).scalar_one_or_none()
        assert manquements == [], "aucune ligne ne doit pointer une phase disparue"
        assert (franchissements, arrets) == (0, 0)
        assert barrage is None, "le barrage survit, détaché"
    finally:
        engine.dispose()


def test_upgrade_rend_une_liste_vide_quand_le_seul_prelevement_est_irresoluble(
    tmp_path: Path,
) -> None:
    """Retirer **le dernier** prélèvement laisse `sources == []`, pas une clé disparue.

    C'est le cas limite du retrait (correctif de revue) : l'étape devient une phase **sans
    peuplement**, état parfaitement légal que l'organisateur peut corriger à l'écran. Une `config`
    qui perdrait la clé serait tout aussi lisible, mais le contrat écrit par la reprise est bien
    « le prélèvement est retiré », pas « la clé est retirée » — et c'est ce que relit l'adapter.
    """
    cfg, engine = _preparer(tmp_path)
    try:
        with engine.begin() as conn:
            _etape(
                conn,
                45,
                tournoi=1,
                ordre=5,
                config={
                    "sources": [
                        {"nature": "rangs", "ordre_source": 9, "rang_debut": 1, "rang_fin": 2}
                    ]
                },
            )

        command.upgrade(cfg, _APRES)

        assert _configs(engine)[45]["sources"] == []
    finally:
        engine.dispose()


def test_upgrade_leve_l_unicite_du_rang_dans_le_deroule(tmp_path: Path) -> None:
    """Deux étapes au **même rang** deviennent insérables : `uq_deroule_tournoi_ordre` est levée.

    C'est l'arbitrage du commanditaire du 20/09/2026 (ADR-0078 § Conséquences) : le rang n'étant
    plus qu'un affichage, le second verrou coûtait la manœuvre de garage en négatif sans rien
    protéger. Sans ce test, la ligne 3 de la migration n'était vérifiée **par rien** — et son
    oubli n'aurait fait rougir aucune suite, seulement rallongé `reordonner` le jour où il faut
    permuter deux rangs.
    """
    cfg, engine = _preparer(tmp_path)
    try:
        command.upgrade(cfg, _APRES)

        with engine.begin() as conn:
            _etape(conn, 46, tournoi=1, ordre=1, config={})

        with engine.connect() as conn:
            au_rang_1 = conn.execute(
                sa.text("SELECT COUNT(*) FROM deroule_etape WHERE tournoi_id = 1 AND ordre = 1")
            ).scalar_one()
        assert au_rang_1 == 2
    finally:
        engine.dispose()
