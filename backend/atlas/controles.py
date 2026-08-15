"""Les écarts entre ce que l'écrit promet et ce que le dépôt contient.

C'est le vrai livrable de l'atlas. Le dessin rend le registre lisible ; ces contrôles le rendent
**opposable**. Ils mécanisent la leçon d'ADR-0075 : « un ADR sans lien vérifiable vers le code est
une intention, pas une décision » — et le rétro-équipement du 08/08/2026 avait déjà montré que la
section « Porté dans le code par » pouvait nommer des modules qui ne tiennent pas la promesse.

Calibrage des sévérités, délibéré :
- **bloquant** = un constat sans ambiguïté, corrigible en une minute (un chemin qui n'existe pas,
  un ADR cité qui n'existe pas). La CI a le droit de rougir dessus.
- **signal** = un constat heuristique ou un choix de forme (un symbole cité introuvable, une date
  hors format canonique). Affiché, jamais bloquant : une porte qui rougit sur de l'heuristique
  finit désactivée, et on perd aussi les contrôles qui, eux, étaient justes.
"""

from __future__ import annotations

import re
from pathlib import Path

from atlas import markdown
from atlas.modele import Controle, Decision, Regle, Severite

_US = re.compile(r"E\d{2}US\d{3}")
_DATE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _us_du_backlog(racine: Path) -> set[str]:
    dossier = racine / "stories"
    if not dossier.is_dir():
        return set()
    return {
        identifiant
        for fichier in sorted(dossier.glob("*.md"))
        for identifiant in _US.findall(markdown.lire(fichier))
    }


def verifier(
    racine: Path, regles: tuple[Regle, ...], decisions: tuple[Decision, ...]
) -> tuple[Controle, ...]:
    connues = {d.identifiant for d in decisions}
    us_connues = _us_du_backlog(racine)
    trouves: list[Controle] = []

    for decision in decisions:
        sujet = f"ADR-{decision.identifiant}"

        for portage in decision.portage:
            if not portage.existe:
                trouves.append(
                    Controle(
                        code="portage-inexistant",
                        severite=Severite.BLOQUANT,
                        sujet=sujet,
                        message=(
                            f"nomme « {portage.chemin} » comme portant sa décision, "
                            f"mais ce chemin n'existe plus dans le dépôt."
                        ),
                    )
                )
            elif portage.symboles_absents:
                trouves.append(
                    Controle(
                        code="portage-symbole-absent",
                        severite=Severite.SIGNAL,
                        sujet=sujet,
                        message=(
                            f"annonce {', '.join(portage.symboles_absents)} dans "
                            f"« {portage.chemin} » — introuvable(s) dans le fichier."
                        ),
                    )
                )
            elif not portage.verifiable:
                # Sans ce signal, une cible non lisible (un répertoire, une extension inconnue)
                # rendait « aucun symbole absent » — donc s'affichait comme **tenue** alors que
                # rien n'avait été vérifié. Une promesse non contrôlée doit se dire, pas se taire.
                trouves.append(
                    Controle(
                        code="portage-non-verifiable",
                        severite=Severite.SIGNAL,
                        sujet=sujet,
                        message=(
                            f"annonce {', '.join(portage.symboles)} dans « {portage.chemin} », "
                            f"qui n'est pas un fichier lisible symbole par symbole : la promesse "
                            f"existe mais n'est pas contrôlée."
                        ),
                    )
                )

        for lien in decision.liens:
            if lien.type.value == "us":
                if us_connues and lien.cible not in us_connues:
                    trouves.append(
                        Controle(
                            code="us-inconnue",
                            severite=Severite.SIGNAL,
                            sujet=sujet,
                            message=f"cite l'US {lien.cible}, absente de `stories/`.",
                        )
                    )
            elif lien.cible not in connues:
                trouves.append(
                    Controle(
                        code="adr-cible-inconnue",
                        severite=Severite.BLOQUANT,
                        sujet=sujet,
                        message=(
                            f"déclare « {lien.libelle} » vers ADR-{lien.cible}, "
                            f"qui n'existe pas dans `docs/adr/`."
                        ),
                    )
                )

        if not _DATE_ISO.match(decision.date_brute.strip()):
            trouves.append(
                Controle(
                    code="date-non-canonique",
                    severite=Severite.SIGNAL,
                    sujet=sujet,
                    message=(
                        f"date « {decision.date_brute} » hors du format ISO utilisé par le reste "
                        f"du registre (AAAA-MM-JJ)."
                    ),
                )
            )

        if decision.remplace_par and decision.remplace_par not in connues:
            trouves.append(
                Controle(
                    code="remplacant-inconnu",
                    severite=Severite.BLOQUANT,
                    sujet=sujet,
                    message=f"se dit remplacé par ADR-{decision.remplace_par}, qui n'existe pas.",
                )
            )

    for regle in regles:
        for cite in regle.adr:
            if cite not in connues:
                trouves.append(
                    Controle(
                        code="regle-cite-adr-inconnu",
                        severite=Severite.BLOQUANT,
                        sujet=f"règle « {regle.titre} »",
                        message=f"renvoie à ADR-{cite}, qui n'existe pas dans `docs/adr/`.",
                    )
                )

    return tuple(sorted(trouves, key=lambda c: (c.severite.value, c.code, c.sujet, c.message)))


def bloquants(controles: tuple[Controle, ...]) -> tuple[Controle, ...]:
    return tuple(c for c in controles if c.severite is Severite.BLOQUANT)
