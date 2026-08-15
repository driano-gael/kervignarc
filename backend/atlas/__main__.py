"""Point d'entrée du générateur : `python -m atlas [--verifier]`.

Une seule implémentation sert la génération **et** la vérification — un vérificateur écrit à part
finirait par diverger du générateur, ce qui est exactement le genre de dérive que l'atlas existe
pour rendre visible.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from atlas import controles as controles_module
from atlas import rendu
from atlas.modele import AtlasSourceInvalide, Severite
from atlas.sources import adr, corpus, historique, reglement

RACINE = Path(__file__).resolve().parents[2]


def construire(racine: Path) -> dict[str, str]:
    """Produit le contenu de chaque fichier de données, sans rien écrire."""
    regles = reglement.lire_regles(racine)
    decisions = adr.lire_decisions(racine)
    verdicts = controles_module.verifier(racine, regles, decisions)

    charges: dict[str, Any] = {
        "reglement": {
            "sections": list(reglement.SECTIONS),
            "regles": list(regles),
        },
        "decisions": {"decisions": list(decisions)},
        "controles": {
            "controles": list(verdicts),
            "resume": {
                "bloquants": sum(1 for c in verdicts if c.severite is Severite.BLOQUANT),
                "signaux": sum(1 for c in verdicts if c.severite is Severite.SIGNAL),
            },
        },
        "corpus": {"documents": corpus.construire(regles, decisions)},
        "historique": historique.historique(racine, regles),
    }
    return {cle: rendu.serialiser(cle, charge) for cle, charge in charges.items()}


def _resume(racine: Path) -> str:
    regles = reglement.lire_regles(racine)
    decisions = adr.lire_decisions(racine)
    verdicts = controles_module.verifier(racine, regles, decisions)
    amendes = sum(1 for d in decisions if d.amende_par)
    return (
        f"{len(regles)} règles · {len(decisions)} décisions "
        f"(dont {amendes} amendées par une décision plus récente) · "
        f"{len(controles_module.bloquants(verdicts))} écart(s) bloquant(s), "
        f"{len(verdicts) - len(controles_module.bloquants(verdicts))} signal(aux)"
    )


def principal(arguments: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(
        prog="python -m atlas",
        description="Génère les données de l'atlas depuis les sources versionnées du dépôt.",
    )
    analyseur.add_argument(
        "--verifier",
        action="store_true",
        help="ne rien écrire ; sortir en erreur si les données commitées sont périmées.",
    )
    options = analyseur.parse_args(arguments)

    try:
        fichiers = construire(RACINE)
    except AtlasSourceInvalide as invalide:
        print(f"atlas : source invalide.\n{invalide}", file=sys.stderr)
        return 2

    if not options.verifier:
        rendu.ecrire(RACINE, fichiers)
        print(f"atlas généré — {_resume(RACINE)}")
        return 0

    problemes = rendu.ecarts(RACINE, fichiers)
    if problemes:
        print("atlas : les données générées ne correspondent plus aux sources.", file=sys.stderr)
        for probleme in problemes:
            print(f"  - {probleme}", file=sys.stderr)
        print("\nRégénère : cd backend && python -m atlas", file=sys.stderr)
        return 1

    print(f"atlas à jour — {_resume(RACINE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
