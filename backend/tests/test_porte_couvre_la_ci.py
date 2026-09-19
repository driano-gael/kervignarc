"""La porte locale couvre exactement les vérifications de `ci.yml` (ADR-0110)."""

from __future__ import annotations

import re
from pathlib import Path

from porte import GROUPES

CI = Path(__file__).resolve().parent.parent.parent / ".github" / "workflows" / "ci.yml"

# Lignes de `run:` que `porte.py` ne reproduit **pas**, et pourquoi.
# ⚠️ Y ajouter une ligne, c'est décider qu'une vérification de la CI ne sera pas jouée en
# local : ne le faire que pour de l'installation ou du pilotage shell, jamais pour un
# contrôle. Les trois `pip install` préparent l'environnement, que le venv local porte déjà ;
# la boucle de reprise de `npm audit` est reproduite par le champ `essais` de la porte.
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
        if nue == "run: |":
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


def test_le_parseur_voit_bien_la_ci() -> None:
    commandes = _commandes_de_la_ci()
    assert "pytest" in commandes, "Le parseur de ci.yml ne retrouve plus `pytest` : il est cassé."
    assert len(commandes) >= 12, f"Seulement {len(commandes)} commandes lues dans ci.yml."
