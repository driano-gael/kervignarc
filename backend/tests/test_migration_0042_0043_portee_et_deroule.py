"""Migrations 0042 / 0043 — bascule de portée, puis séparation déroulé / avancement.

**Les deux migrations les plus lourdes de l'historique n'avaient aucun test** (0018, 0019, 0020,
0021, 0032 et 0036 en ont chacune un), alors qu'elles déplacent la table `phase` d'un parent à
l'autre puis lui retirent deux colonnes. La suite d'API migre toujours une base **vide** jusqu'à
`head` : ni la reprise de données ni le `downgrade` n'étaient exercés nulle part.

Ce que ces tests éprouvent, et qui n'est pas décoratif :

1. **la reprise** — les phases d'un tournoi multi-créneaux atterrissent sur le premier départ
   (0042), puis leur définition est promue en `deroule_etape` une seule fois (0043) ;
2. **l'aller-retour `upgrade → downgrade → upgrade`**, qui **échouait**. Le `downgrade` de la 0042
   rebranchait *toutes* les phases sur leur tournoi, y compris les N copies créées par créneau
   depuis. Le tournoi se retrouvait avec plusieurs phases de même `ordre` — un état que le modèle
   d'avant la 0042 n'a jamais connu (la séquence y est 1..N par tournoi) —, et la 0042 les
   rattachait ensuite toutes au premier départ. La 0043 butait alors sur son propre
   `INSERT … SELECT`, qui insérait deux fois `(tournoi, ordre)` dans une table qui l'interdit :
   la base restait **bloquée à mi-migration**, sans chemin de sortie.

Test **de non-régression** au sens de la règle 9 : l'oracle est le comportement décrit par les
docstrings des deux migrations, et l'implémenteur est le mieux placé pour l'écrire — il connaît
les coutures.

Les clés étrangères sont désactivées côté Alembic (`env.py`) : on insère des identifiants parents
fictifs sans matérialiser toute la descendance, comme les tests de migration 0018/0020/0032/0036.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

_BACKEND_ROOT = Path(__file__).resolve().parents[1]

_AVANT = "0041_cloisonnement_cible"
_PORTEE = "0042_portee_sportive_depart"
_DEROULE = "0043_deroule_defini_une_fois"

_CONFIG_QUALIF: dict[str, object] = {
    "policies": {"scoring": {"nom": "cumul", "volees": 12, "fleches": 3}},
    "validation": {"grain": "fin_de_serie"},
}
_CONFIG_TABLEAU: dict[str, object] = {
    "sources": [{"nature": "rangs", "ordre_source": 1, "rang_debut": 1, "rang_fin": 8}],
    "effectif": 8,
}


def _config(url: str) -> Config:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _tournoi(conn: sa.Connection, tournoi_id: int) -> None:
    conn.execute(
        sa.text(
            "INSERT INTO tournoi (id, nom, date, statut, type_tournoi) "
            "VALUES (:id, :nom, '2026-03-14', 'brouillon', 'non_officiel')"
        ),
        {"id": tournoi_id, "nom": f"Tournoi {tournoi_id}"},
    )


def _depart(
    conn: sa.Connection, depart_id: int, tournoi_id: int, numero: int, horaire: str
) -> None:
    conn.execute(
        sa.text(
            "INSERT INTO depart (id, tournoi_id, numero, horaire, tarif_centimes, quota) "
            "VALUES (:id, :tournoi_id, :numero, :horaire, 800, NULL)"
        ),
        {"id": depart_id, "tournoi_id": tournoi_id, "numero": numero, "horaire": horaire},
    )


def _phase_au_tournoi(
    conn: sa.Connection,
    phase_id: int,
    tournoi_id: int,
    ordre: int,
    type_phase: str,
    config: dict[str, object],
) -> None:
    """Une phase d'avant la 0042 : elle pend au tournoi et porte sa définition."""
    conn.execute(
        sa.text(
            "INSERT INTO phase (id, tournoi_id, ordre, type, config, statut) "
            "VALUES (:id, :tournoi_id, :ordre, :type, :config, 'a_venir')"
        ),
        {
            "id": phase_id,
            "tournoi_id": tournoi_id,
            "ordre": ordre,
            "type": type_phase,
            "config": json.dumps(config),
        },
    )


def _semer_un_tournoi_a_deux_creneaux(engine: sa.Engine) -> None:
    """Le décor commun : un tournoi, **deux** créneaux, un déroulé de deux phases au tournoi.

    Deux créneaux et non un : c'est le seul décor où « les phases du tournoi » et « celles du
    créneau » ne sont pas la même liste — donc le seul qui puisse voir la duplication.
    """
    with engine.begin() as conn:
        _tournoi(conn, 1)
        _depart(conn, 41, tournoi_id=1, numero=1, horaire="09:00")
        _depart(conn, 42, tournoi_id=1, numero=2, horaire="14:00")
        _phase_au_tournoi(conn, 1, 1, 1, "qualification", _CONFIG_QUALIF)
        _phase_au_tournoi(conn, 2, 1, 2, "elimination_directe", _CONFIG_TABLEAU)


def _phases(engine: sa.Engine) -> list[tuple[int, int, int]]:
    """`(id, depart_id, ordre)` de chaque avancement, trié — l'état d'après 0043."""
    with engine.connect() as conn:
        lignes = conn.execute(
            sa.text("SELECT id, depart_id, ordre FROM phase ORDER BY depart_id, ordre")
        ).all()
    return [(int(a), int(b), int(c)) for a, b, c in lignes]


def _etapes(engine: sa.Engine) -> list[tuple[int, int, str]]:
    """`(tournoi_id, ordre, type)` de chaque étape du déroulé, trié."""
    with engine.connect() as conn:
        lignes = conn.execute(
            sa.text("SELECT tournoi_id, ordre, type FROM deroule_etape ORDER BY tournoi_id, ordre")
        ).all()
    return [(int(a), int(b), str(c)) for a, b, c in lignes]


# --- Reprise des données -------------------------------------------------------------------------


def test_0042_rattache_les_phases_au_premier_creneau(tmp_path: Path) -> None:
    """« Le premier départ au sens du **numéro** » — celui que l'organisateur voit en tête."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, _AVANT)
    engine = sa.create_engine(url)
    try:
        _semer_un_tournoi_a_deux_creneaux(engine)

        command.upgrade(cfg, _PORTEE)

        with engine.connect() as conn:
            lignes = conn.execute(
                sa.text("SELECT id, depart_id, ordre FROM phase ORDER BY ordre")
            ).all()
        assert [(int(a), int(b), int(c)) for a, b, c in lignes] == [(1, 41, 1), (2, 41, 2)]
    finally:
        engine.dispose()


def test_0043_promeut_la_definition_une_seule_fois(tmp_path: Path) -> None:
    """Deux phases, deux étapes — et `phase` ne porte plus ni `type` ni `config`."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, _AVANT)
    engine = sa.create_engine(url)
    try:
        _semer_un_tournoi_a_deux_creneaux(engine)

        command.upgrade(cfg, _DEROULE)

        assert _etapes(engine) == [(1, 1, "qualification"), (1, 2, "elimination_directe")]
        with engine.connect() as conn:
            colonnes = {
                str(ligne[1]) for ligne in conn.execute(sa.text("PRAGMA table_info(phase)")).all()
            }
        assert "type" not in colonnes and "config" not in colonnes
        assert colonnes >= {"id", "depart_id", "ordre", "statut"}
        # La définition est conservée à l'identique : la migration ne réinterprète pas la `config`.
        with engine.connect() as conn:
            config = conn.execute(
                sa.text("SELECT config FROM deroule_etape WHERE ordre = 1")
            ).scalar_one()
        assert json.loads(str(config)) == _CONFIG_QUALIF
    finally:
        engine.dispose()


def test_0043_instancie_le_deroule_dans_chaque_creneau(tmp_path: Path) -> None:
    """Une base migrée ne laisse **aucun créneau sans avancement** (ADR-0076).

    Relevé à la seconde revue d'E01US025. La 0042 rattache toutes les phases au *premier* créneau —
    dans le modèle d'avant, un tournoi n'avait qu'une séquence, sans notion de créneau. Les créneaux
    2..N ressortaient donc de la migration **vides** : pilotage impossible, « ce créneau ne joue
    encore aucune phase » sur un tournoi qui avait bel et bien deux départs, et rien ensuite pour le
    réparer (ajouter une étape n'instancie que celle-là).

    ⚠️ Ce test **exige deux créneaux**. Sur un tournoi mono-départ il passerait quel que soit le
    code — c'est exactement pourquoi le défaut avait survécu à la première revue.
    """
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, _AVANT)
    engine = sa.create_engine(url)
    try:
        _semer_un_tournoi_a_deux_creneaux(engine)

        command.upgrade(cfg, _DEROULE)

        # Le déroulé reste défini **une** fois, et chaque créneau porte les deux rangs.
        assert _etapes(engine) == [(1, 1, "qualification"), (1, 2, "elimination_directe")]
        assert [(depart, ordre) for _, depart, ordre in _phases(engine)] == [
            (41, 1),
            (41, 2),
            (42, 1),
            (42, 2),
        ]
        # Le créneau qui n'a rien joué part bien « à venir » — c'est la vérité, pas un défaut.
        with engine.connect() as conn:
            statuts = conn.execute(
                sa.text("SELECT statut FROM phase WHERE depart_id = 42 ORDER BY ordre")
            ).scalars()
            assert list(statuts) == ["a_venir", "a_venir"]
    finally:
        engine.dispose()


# --- L'aller-retour, qui échouait ----------------------------------------------------------------


def test_l_aller_retour_est_reversible_meme_avec_des_phases_dans_chaque_creneau(
    tmp_path: Path,
) -> None:
    """**La garde.** `upgrade → downgrade → upgrade` doit aboutir, pas rester à mi-chemin.

    Le décor reproduit l'état réel d'après 0043 : chaque créneau porte son avancement des mêmes
    rangs — ici quatre lignes `phase` pour deux étapes. Au `downgrade`, ces quatre lignes
    revenaient toutes au tournoi, qui se retrouvait avec deux phases d'`ordre` 1 et deux d'`ordre`
    2 ; le second `upgrade` les rattachait au même créneau, et la 0043 doublonnait
    `(tournoi, ordre)` dans `deroule_etape`.

    Le `downgrade` de la 0042 **replie** donc désormais les copies : seules les phases du premier
    créneau remontent au tournoi, les autres sont supprimées. C'est l'inverse exact de son
    `upgrade`, qui ne connaissait qu'une séquence par tournoi — et c'est une perte assumée, du même
    ordre que celle qu'annonce déjà la 0043 sur les définitions divergentes.
    """
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, _AVANT)
    engine = sa.create_engine(url)
    try:
        _semer_un_tournoi_a_deux_creneaux(engine)
        command.upgrade(cfg, _DEROULE)
        # ⚠️ L'état d'après 0043 **n'a plus besoin d'être simulé** : depuis le correctif de revue
        # E01US025, la 0043 instancie elle-même le déroulé dans les créneaux 2..N. Le décor posait
        # ces deux lignes à la main, ce qui masquait précisément le défaut — la migration les
        # laissait manquantes, et le test les rajoutait avant de vérifier l'aller-retour.
        assert len(_phases(engine)) == 4

        command.downgrade(cfg, _AVANT)
        command.upgrade(cfg, _DEROULE)

        # Le déroulé est intact — une définition par rang, pas deux.
        assert _etapes(engine) == [(1, 1, "qualification"), (1, 2, "elimination_directe")]
        # L'avancement du premier créneau a survécu au voyage, identifiants compris ; celui du
        # second est réinstancié par la 0043 (le downgrade l'a replié, cf. la docstring).
        assert _phases(engine)[:2] == [(1, 41, 1), (2, 41, 2)]
        assert [(depart, ordre) for _, depart, ordre in _phases(engine)[2:]] == [(42, 1), (42, 2)]
    finally:
        engine.dispose()


def test_le_downgrade_redistribue_la_definition_dans_chaque_phase(tmp_path: Path) -> None:
    """Le `downgrade` de la 0043 rend à `phase` son `type` et sa `config`, depuis l'étape de son
    rang — sans quoi la colonne `NOT NULL` qu'il rétablit ne pourrait pas être remplie."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, _AVANT)
    engine = sa.create_engine(url)
    try:
        _semer_un_tournoi_a_deux_creneaux(engine)
        command.upgrade(cfg, _DEROULE)

        command.downgrade(cfg, _PORTEE)

        with engine.connect() as conn:
            lignes = conn.execute(
                sa.text("SELECT ordre, type, config FROM phase ORDER BY depart_id, ordre")
            ).all()
        # Quatre lignes et non deux : la 0043 instancie le déroulé dans **chaque** créneau, et le
        # downgrade doit rendre sa définition à chacune — y compris à celles du second créneau, qui
        # n'existaient pas avant le correctif de revue E01US025.
        assert [(int(a), str(b)) for a, b, _ in lignes] == [
            (1, "qualification"),
            (2, "elimination_directe"),
            (1, "qualification"),
            (2, "elimination_directe"),
        ]
        assert json.loads(str(lignes[0][2])) == _CONFIG_QUALIF
    finally:
        engine.dispose()


@pytest.mark.parametrize("cible", [_PORTEE, _DEROULE])
def test_un_tournoi_sans_depart_recoit_un_creneau_de_reprise(tmp_path: Path, cible: str) -> None:
    """Cas de bord n°3 de la 0042 : des phases, aucun créneau pour les accueillir.

    Sans ce rattrapage, la contrainte `NOT NULL` sur `depart_id` les supprimerait — un tournoi
    perdrait son déroulé en silence, à la migration. Le créneau créé est **gratuit** et à 09:00 :
    reconnaissable, et un tarif nul se voit alors qu'un tarif inventé fausserait la facturation.
    """
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, _AVANT)
    engine = sa.create_engine(url)
    try:
        with engine.begin() as conn:
            _tournoi(conn, 7)
            _phase_au_tournoi(conn, 9, 7, 1, "qualification", _CONFIG_QUALIF)

        command.upgrade(cfg, cible)

        with engine.connect() as conn:
            depart = conn.execute(
                sa.text("SELECT numero, horaire, tarif_centimes FROM depart WHERE tournoi_id = 7")
            ).one()
            reste = conn.execute(sa.text("SELECT COUNT(*) FROM phase")).scalar_one()
        assert (int(depart[0]), str(depart[1]), int(depart[2])) == (1, "09:00", 0)
        assert int(reste) == 1, "la phase doit survivre, rattachée au créneau de reprise"
    finally:
        engine.dispose()
