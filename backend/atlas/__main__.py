"""Point d'entrée du générateur : `python -m atlas [--verifier]`.

Une seule implémentation sert la génération **et** la vérification — un vérificateur écrit à part
finirait par diverger du générateur, ce qui est exactement le genre de dérive que l'atlas existe
pour rendre visible.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from atlas import controles as controles_module
from atlas import rendu
from atlas.modele import AtlasSourceInvalide, Controle, Severite
from atlas.sources import adr, corpus, historique, reglement

RACINE = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class Cartes:
    """Le résultat d'une passe de génération : les fichiers, les verdicts, et de quoi les dire."""

    fichiers: dict[str, str]
    verdicts: tuple[Controle, ...]
    resume: str


def assembler(racine: Path) -> Cartes:
    """Lit les sources **une seule fois** et en tire tout ce dont les deux modes ont besoin.

    ⚠️ La génération **exige git**. Sans lui, `historique()` rendrait un dictionnaire vide, qui
    serait écrit tel quel et annoncé « atlas généré » — l'histoire de toutes les règles effacée
    sans un mot, sur un fichier que `.gitattributes` soustrait à la relecture. Une archive sans
    `.git` doit pouvoir **lire** l'atlas ; elle n'a pas à le régénérer.
    """
    if not historique.disponible(racine):
        raise AtlasSourceInvalide(
            "git est introuvable, ou ce dossier n'est pas un dépôt : l'historique des règles ne "
            "peut pas être reconstitué.\nLa génération est refusée plutôt que de produire un "
            "atlas amputé de son histoire. La consultation, elle, ne demande pas git."
        )

    regles = reglement.lire_regles(racine)
    decisions = adr.lire_decisions(racine)
    verdicts = controles_module.verifier(racine, regles, decisions)
    bloquants = controles_module.bloquants(verdicts)

    charges: dict[str, Any] = {
        "reglement": {"sections": list(reglement.SECTIONS), "regles": list(regles)},
        "decisions": {"decisions": list(decisions)},
        "controles": {
            "controles": list(verdicts),
            "resume": {
                "bloquants": len(bloquants),
                "signaux": sum(1 for c in verdicts if c.severite is Severite.SIGNAL),
            },
        },
        "corpus": {"documents": corpus.construire(regles, decisions)},
        "historique": historique.historique(racine, regles),
    }
    amendes = sum(1 for d in decisions if d.amende_par)
    return Cartes(
        fichiers={cle: rendu.serialiser(cle, charge) for cle, charge in charges.items()},
        verdicts=verdicts,
        resume=(
            f"{len(regles)} règles · {len(decisions)} décisions "
            f"(dont {amendes} amendées par une décision plus récente) · "
            f"{len(bloquants)} écart(s) bloquant(s), "
            f"{len(verdicts) - len(bloquants)} signal(aux)"
        ),
    )


def construire(racine: Path) -> dict[str, str]:
    """Le contenu de chaque fichier de données, sans rien écrire."""
    return assembler(racine).fichiers


def _dire_les_bloquants(verdicts: tuple[Controle, ...]) -> None:
    print("atlas : l'écrit promet des choses que le dépôt ne contient pas.", file=sys.stderr)
    for controle in controles_module.bloquants(verdicts):
        print(f"  - {controle.sujet} {controle.message}", file=sys.stderr)
    print(
        "\nCorrige l'ADR ou le code. Ces écarts sont des constats sans ambiguïté : c'est "
        "exactement ce que l'atlas existe pour empêcher de laisser filer.",
        file=sys.stderr,
    )


def principal(arguments: list[str] | None = None, racine: Path = RACINE) -> int:
    """Les quatre issues : 0 à jour · 1 périmé · 2 source invalide · 3 écart bloquant.

    `racine` est un paramètre et non le global : sans cela la fonction n'était **pas testable**,
    et c'est précisément ce qui avait laissé le correctif « les écarts bloquants font rougir la
    porte » sans le moindre test — donc au même point qu'avant, à un code de retour près.
    """
    analyseur = argparse.ArgumentParser(
        prog="python -m atlas",
        description="Génère les données de l'atlas depuis les sources versionnées du dépôt.",
    )
    analyseur.add_argument(
        "--verifier",
        action="store_true",
        help="ne rien écrire ; sortir en erreur si les données sont périmées ou si le dépôt "
        "porte un écart bloquant.",
    )
    options = analyseur.parse_args(arguments)

    try:
        cartes = assembler(racine)
    except AtlasSourceInvalide as invalide:
        print(f"atlas : source invalide.\n{invalide}", file=sys.stderr)
        return 2

    if not options.verifier:
        # La génération **écrit toujours**, y compris en présence d'écarts bloquants : la page
        # « Écarts constatés » est précisément là pour les montrer. C'est `--verifier` qui refuse.
        rendu.ecrire(racine, cartes.fichiers)
        print(f"atlas généré — {cartes.resume}")
        return 0

    problemes = rendu.ecarts(racine, cartes.fichiers)
    if problemes:
        print("atlas : les données générées ne correspondent plus aux sources.", file=sys.stderr)
        for probleme in problemes:
            print(f"  - {probleme}", file=sys.stderr)
        print("\nRégénère : cd backend && python -m atlas", file=sys.stderr)
        return 1

    # La promesse d'ADR-0086 — « la CI a le droit de rougir dessus » — n'était portée par rien :
    # les écarts bloquants étaient comptés, affichés sur une page web, et la porte restait verte.
    if controles_module.bloquants(cartes.verdicts):
        _dire_les_bloquants(cartes.verdicts)
        return 3

    print(f"atlas à jour — {cartes.resume}")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
