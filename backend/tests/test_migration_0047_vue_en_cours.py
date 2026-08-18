"""Migration 0047 — la vue d'écran `tableaux` devient `en_cours`, **sans perdre un réglage**.

Test **de non-régression** au sens de la règle 9 : l'oracle est le comportement décrit par la
docstring de la migration, et l'implémenteur est le mieux placé pour l'écrire.

Ce que ces tests gardent :

1. un déroulé qui **contient** la vue renommée est réécrit — c'est la seule raison d'être de la
   migration, un écran réglé sur « Tableaux » la veille doit rester réglé le lendemain ;
2. les **autres** vues du même document ne bougent pas. C'est le cas que la substitution ciblée
   protège et qu'un `replace` sur `"tableaux"` seul aurait pu casser le jour où le format du
   document s'enrichirait ;
3. l'**aller-retour** `upgrade → downgrade → upgrade` rend la donnée intacte, comme pour la `0046`.
   C'est ce qui rend la migration sûre à jouer sur une base réelle ;
4. un écran **sans déroulé** (`deroule_json IS NULL`, le régime par défaut) traverse sans dommage —
   le `WHERE` de la migration existe pour lui.

Les clés étrangères sont désactivées côté Alembic (`env.py`) : on insère un `tournoi_id` fictif sans
matérialiser toute la descendance, comme les tests de migration voisins.
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

_BACKEND_ROOT = Path(__file__).resolve().parents[1]

_AVANT = "0046_placement_par_bloc"
_EN_COURS = "0047_vue_en_cours"

# Un déroulé **mixte** : la vue renommée entourée de deux autres. C'est la forme qui distingue une
# substitution ciblée d'un remplacement aveugle — un `replace` maladroit sur le document entier
# abîmerait les voisines, et un test à une seule vue ne le verrait jamais.
_AVANT_MIGRATION = [
    {"vue": "classement", "cadence_s": 30},
    {"vue": "tableaux", "cadence_s": 45},
    {"vue": "palmares", "cadence_s": 20},
]
_APRES_MIGRATION = [
    {"vue": "classement", "cadence_s": 30},
    {"vue": "en_cours", "cadence_s": 45},
    {"vue": "palmares", "cadence_s": 20},
]


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


def _semer(engine: sa.Engine) -> None:
    """Deux écrans : l'un avec un déroulé réglé, l'autre sur le déroulé par défaut (`NULL`)."""
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO poste (tournoi_id, cible_index, code, type, libelle, deroule_json) "
                "VALUES (1, NULL, 'ECR1', 'ecran', 'Hall', :deroule)"
            ),
            {"deroule": json.dumps(_AVANT_MIGRATION)},
        )
        conn.execute(
            sa.text(
                "INSERT INTO poste (tournoi_id, cible_index, code, type, libelle, deroule_json) "
                "VALUES (1, NULL, 'ECR2', 'ecran', 'Buvette', NULL)"
            )
        )


def _lire(engine: sa.Engine, code: str) -> list[dict[str, object]] | None:
    with engine.begin() as conn:
        brut = conn.execute(
            sa.text("SELECT deroule_json FROM poste WHERE code = :code"), {"code": code}
        ).scalar_one()
    if brut is None:
        return None
    charge: list[dict[str, object]] = json.loads(brut)
    return charge


def test_le_deroule_regle_sur_les_tableaux_bascule_sur_en_cours(tmp_path: Path) -> None:
    """La promesse de la migration : un écran réglé la veille reste réglé le lendemain.

    Sans elle, `_vers_sequence_vues` relèverait `VueEcran("tableaux")` — une valeur que l'enum ne
    connaît plus — et le repository enveloppe cette erreur en `InfrastructureError` : l'écran ne se
    contenterait pas d'afficher autre chose, il deviendrait **illisible**.
    """
    engine, cfg = _base(tmp_path, "regle.db")
    _semer(engine)

    command.upgrade(cfg, _EN_COURS)

    assert _lire(engine, "ECR1") == _APRES_MIGRATION


def test_les_autres_vues_du_meme_deroule_ne_bougent_pas(tmp_path: Path) -> None:
    """La substitution est **ciblée** sur la paire clé/valeur, pas sur le mot.

    L'assertion ci-dessus le couvre déjà de fait ; celle-ci le dit **en propre**, pour qu'un futur
    remaniement de la migration ne puisse pas élargir sa portée sans faire tomber un test qui nomme
    la raison.
    """
    engine, cfg = _base(tmp_path, "voisines.db")
    _semer(engine)

    command.upgrade(cfg, _EN_COURS)

    apres = _lire(engine, "ECR1")
    assert apres is not None
    assert [v["vue"] for v in apres if v["vue"] != "en_cours"] == ["classement", "palmares"]
    assert [v["cadence_s"] for v in apres] == [30, 45, 20]


def test_un_ecran_sans_deroule_traverse_sans_dommage(tmp_path: Path) -> None:
    """`deroule_json IS NULL` est le **régime par défaut**, pas une anomalie : l'écran joue la
    séquence par défaut. Le `WHERE` de la migration existe pour lui."""
    engine, cfg = _base(tmp_path, "defaut.db")
    _semer(engine)

    command.upgrade(cfg, _EN_COURS)

    assert _lire(engine, "ECR2") is None


def test_l_aller_retour_rend_la_donnee_intacte(tmp_path: Path) -> None:
    """`upgrade → downgrade → upgrade` sans perte — c'est ce qui rend la migration sûre.

    La descente compte pour de bon ici : un club qui redescend d'une version doit retrouver un
    déroulé que le bundle d'avant sait lire. Il montrera l'arbre seul, ce qu'il savait faire.
    """
    engine, cfg = _base(tmp_path, "aller_retour.db")
    _semer(engine)

    command.upgrade(cfg, _EN_COURS)
    command.downgrade(cfg, _AVANT)
    assert _lire(engine, "ECR1") == _AVANT_MIGRATION

    command.upgrade(cfg, _EN_COURS)
    assert _lire(engine, "ECR1") == _APRES_MIGRATION
