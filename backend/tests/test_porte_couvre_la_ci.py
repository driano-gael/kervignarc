"""La porte locale couvre exactement les vérifications de `ci.yml` (ADR-0110)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from porte import GROUPES, PY, PYTEST_RAPIDE, Verification

RACINE = Path(__file__).resolve().parent.parent.parent
CI = RACINE / ".github" / "workflows" / "ci.yml"
REGLAGES = RACINE / ".claude" / "settings.json"

# Lignes de `run:` que `porte.py` ne reproduit **pas**, et pourquoi.
# ⚠️ Y ajouter une ligne, c'est décider qu'une vérification de la CI ne sera pas jouée en
# local : ne le faire que pour de l'installation ou du pilotage shell, jamais pour un
# contrôle. Les **quatre** `pip install` préparent l'environnement, que le venv local porte
# déjà ; `pip-audit` lui-même reste dans la porte, et c'est ce qui referme `DETTE-093`.
COMMANDES_HORS_PORTE: frozenset[str] = frozenset(
    {
        "python -m pip install --upgrade pip",
        "pip install -r requirements.txt",
        "pip install -e . --no-deps",
        "pip install pip-audit",
    }
)

# Mots-clés du shell de pilotage : ce sont des enveloppes, pas des vérifications.
# ⚠️ Le test s'applique **après** `_nettoyer`, jamais avant : `if npm audit …; then` porte une
# vraie vérification sous une enveloppe, et la filtrer sur son `if` la ferait disparaître.
PILOTAGE = re.compile(r"^(for|do|done|if|then|fi|else|elif|echo|exit|sleep)\b")

# Ouverture d'un bloc YAML, quel que soit son style de scalaire.
# ⚠️ Une égalité stricte à `run: |` rendrait **invisible** au parseur tout bloc écrit `run: >`
# ou `run: |-` : ses commandes n'entreraient dans aucune comparaison, et une vérification
# ajoutée à la CI ne serait jouée nulle part sans faire rougir quoi que ce soit.
OUVERTURE_DE_BLOC = re.compile(r"^run:\s*[|>][-+]?$")

# Ce qu'il faut retirer d'une commande pour la comparer à sa citation de `ci.yml`.
ALIAS_DE_MODULE = {"pip_audit": "pip-audit"}


def _normaliser(jetons: list[str]) -> str:
    if jetons and jetons[0] == PY[0]:
        jetons = ["python", *jetons[1:]]
    if len(jetons) >= 3 and jetons[0] == "python" and jetons[1] == "-m":
        jetons = jetons[2:]
    return " ".join(ALIAS_DE_MODULE.get(jeton, jeton) for jeton in jetons)


def _toutes_les_verifications() -> list[Verification]:
    return [v for groupe in GROUPES.values() for v in groupe] + [PYTEST_RAPIDE]


def _commandes_de_la_ci() -> set[str]:
    lignes = CI.read_text(encoding="utf-8").splitlines()
    commandes: set[str] = set()
    dans_un_bloc = False
    indentation = 0
    for ligne in lignes:
        nue = ligne.strip()
        if dans_un_bloc:
            if nue and len(ligne) - len(ligne.lstrip()) < indentation:
                dans_un_bloc = False
            else:
                candidate = _nettoyer(nue)
                if candidate and not PILOTAGE.match(candidate):
                    commandes.add(candidate)
                continue
        if OUVERTURE_DE_BLOC.match(nue):
            dans_un_bloc = True
            indentation = len(ligne) - len(ligne.lstrip()) + 2
        elif nue.startswith("run: "):
            commandes.add(_nettoyer(nue.removeprefix("run: ")))
    return {c for c in commandes if c}


def _nettoyer(commande: str) -> str:
    sans_condition = re.sub(r"^if\s+", "", commande).rstrip(";")
    return re.sub(r";?\s*(then|do)$", "", sans_condition).strip()


def _commandes_de_la_porte() -> set[str]:
    return {v.ligne_ci for groupe in GROUPES.values() for v in groupe if v.ligne_ci}


def test_la_porte_ne_rate_aucune_verification_de_la_ci() -> None:
    oubliees = _commandes_de_la_ci() - _commandes_de_la_porte() - COMMANDES_HORS_PORTE
    assert not oubliees, (
        f"Ces vérifications de ci.yml ne sont pas dans porte.py : {sorted(oubliees)}. "
        "Ajoutez-les à porte.py, ou inscrivez-les dans COMMANDES_HORS_PORTE en disant pourquoi."
    )


def test_la_porte_n_invente_aucune_verification() -> None:
    inventees = _commandes_de_la_porte() - _commandes_de_la_ci()
    assert not inventees, (
        f"Ces lignes de porte.py ne correspondent à aucun `run:` de ci.yml : {sorted(inventees)}. "
        "Le champ `ligne_ci` doit citer la CI à la lettre."
    )


def test_chaque_citation_decrit_la_commande_reellement_lancee() -> None:
    """Sans ce test, `ligne_ci` n'est qu'une étiquette : la citation serait déclarée, pas vérifiée.

    Une `Verification(commande=(…, "pytest", "-x", "--ignore=…"), ligne_ci="pytest")` passerait
    les deux comparaisons ci-dessus — la porte locale jouerait autre chose que la CI, en silence.
    """
    ecarts = {
        v.nom: (_normaliser(list(v.commande)), _normaliser(v.ligne_ci.split()))
        for v in _toutes_les_verifications()
        if v.ligne_ci and _normaliser(list(v.commande)) != _normaliser(v.ligne_ci.split())
    }
    assert not ecarts, (
        f"Ces vérifications lancent autre chose que ce qu'elles citent : {ecarts}. "
        "Le format est (commande réelle, citation de ci.yml)."
    )


def test_aucune_verification_de_la_ci_n_echappe_aux_comparaisons() -> None:
    """Une `ligne_ci` vide rend une vérification invisible aux deux comparaisons ci-dessus.

    C'est légitime pour `PYTEST_RAPIDE`, qui n'a pas d'équivalent dans la CI ; ça ne l'est pour
    aucune vérification de `GROUPES`.
    """
    muettes = [v.nom for groupe in GROUPES.values() for v in groupe if not v.ligne_ci]
    assert not muettes, f"Ces vérifications n'ont pas de citation de ci.yml : {muettes}"


def test_la_porte_ne_lance_aucune_commande_refusee_par_le_depot() -> None:
    """Le contrôle a suivi les commandes : il portait sur `porte-mecanique.md` jusqu'en E00US031.

    ⚠️ Il porte sur la **commande réellement lancée**, pas sur sa citation. Et il ne remplace pas
    le système de permissions : les vérifications sont des sous-processus de `porte.py`, donc
    hors de portée du `deny` de `.claude/settings.json` — ce test est ce qui en tient lieu.
    """
    reglages = json.loads(REGLAGES.read_text(encoding="utf-8"))
    refuses = [
        entree[len("Bash(") : -len(":*)")]
        for entree in reglages["permissions"]["deny"]
        if entree.startswith("Bash(") and entree.endswith(":*)")
    ]
    assert refuses, "aucun refus lu : ce garde-fou ne vérifierait plus rien"

    collisions = {
        v.nom
        for v in _toutes_les_verifications()
        for refus in refuses
        if _normaliser(list(v.commande)) == refus
        or _normaliser(list(v.commande)).startswith(f"{refus} ")
    }
    assert not collisions, (
        f"porte.py lance {sorted(collisions)}, que .claude/settings.json refuse. "
        "Soit la permission s'ouvre, soit la vérification sort de la porte."
    )


def test_le_parseur_voit_bien_la_ci() -> None:
    commandes = _commandes_de_la_ci()
    assert "pytest" in commandes, "Le parseur de ci.yml ne retrouve plus `pytest` : il est cassé."
    assert len(commandes) >= 17, f"Seulement {len(commandes)} commandes lues dans ci.yml."


def test_aucune_cle_run_n_echappe_au_parseur() -> None:
    """Le canari du parseur : une forme de `run:` non reconnue ne dit rien d'elle-même."""
    formes = [
        ligne.strip()
        for ligne in CI.read_text(encoding="utf-8").splitlines()
        if ligne.strip().startswith("run:")
    ]
    inconnues = [
        forme
        for forme in formes
        if not OUVERTURE_DE_BLOC.match(forme) and not forme.startswith("run: ") and forme != "run:"
    ]
    assert not inconnues, f"Formes de `run:` que ce parseur ignore en silence : {inconnues}"
