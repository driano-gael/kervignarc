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

from atlas import markdown, normalisation
from atlas.modele import Controle, Decision, Regle, Severite
from atlas.sources import suivi
from atlas.sources.backlog import Dette, Epic, UsSpecifiee
from atlas.sources.suivi import Entete, Section, compter

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


def trier(controles: tuple[Controle, ...]) -> tuple[Controle, ...]:
    """L'ordre d'affichage, unique et déterministe : bloquants d'abord, puis par code et sujet.

    Sortie **commitée puis comparée en CI** : deux passes doivent rendre le même octet, quel que
    soit l'ordre dans lequel les contrôles ont été produits.
    """
    return tuple(sorted(controles, key=lambda c: (c.severite.value, c.code, c.sujet, c.message)))


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

    return trier(tuple(trouves))


def _mots(titre: str) -> set[str]:
    """Les mots significatifs d'un libellé — sans accent, sans casse, sans les mots outils."""
    return {mot for mot in re.split(r"[^a-z0-9]+", normalisation.cle(titre)) if len(mot) > 2}


def _titres_concordent(tracker: str, story: str) -> bool:
    """Le tracker et la story désignent-ils visiblement le même travail ?

    Comparer à l'égalité ne marche pas : les deux libellés du **même** travail sont presque
    toujours des reformulations — « Repository + endpoint bout-en-bout » contre « … de bout en
    bout », un titre augmenté d'une glose ou tronqué. Mesuré sur le dépôt le 16/08/2026, l'égalité
    stricte donnait **23 signaux sur 109 US livrées**, presque tous des synonymes : un contrôle à
    ce niveau de bruit n'est plus lu, et sa disparition emporte les constats qui, eux, étaient bons.

    On mesure donc le **recouvrement** des mots significatifs, rapporté au plus court des deux
    libellés (le plus court est souvent une troncature volontaire, qu'on ne veut pas pénaliser).
    Sous la moitié des mots en commun, les deux titres ne parlent visiblement plus de la même
    chose. Seuil **calibré sur le dépôt**, pas déduit : il y laisse deux signaux, tous deux réels.
    """
    a, b = _mots(tracker), _mots(story)
    if not a or not b:
        return True
    return len(a & b) / min(len(a), len(b)) >= 0.5


def verifier_avancement(
    sections: tuple[Section, ...],
    epics: tuple[Epic, ...],
    dettes: tuple[Dette, ...],
    us_specifiees: tuple[UsSpecifiee, ...],
    decisions: tuple[Decision, ...],
    entete: Entete,
) -> tuple[Controle, ...]:
    """Les contradictions entre les quatre livrables de suivi, qui se citent sans se vérifier.

    Le compteur d'une section est **recalculé** et son écart est bloquant : le tracker est le point
    de reprise du projet, un compteur faux ne se rattrape pas à la lecture — il fait repartir la
    session suivante sur une base fausse.
    """
    trouves: list[Controle] = []
    specifiees = {us.identifiant: us for us in us_specifiees}

    for section in sections:
        if section.compteur_ecrit is not None:
            calcule = compter(section)
            if calcule != section.compteur_ecrit:
                trouves.append(
                    Controle(
                        code="compteur-divergent",
                        severite=Severite.BLOQUANT,
                        sujet=f"section « {section.titre} »",
                        message=(
                            f"annonce {section.compteur_ecrit[0]}/{section.compteur_ecrit[1]} "
                            f"alors que la règle de comptage de la Légende donne "
                            f"{calcule[0]}/{calcule[1]}."
                        ),
                    )
                )

    # Le total annoncé en tête compte des **US**, pas des lignes : deux US sont légitimement
    # re-listées dans un lot d'ajouts postérieur, et les compter deux fois ferait dériver l'atlas
    # du tracker plutôt que l'inverse.
    distinctes = {
        ligne.identifiant
        for section in sections
        for ligne in section.comptees
        if ligne.etat == suivi.LIVREE
    }
    if entete.livrees is not None and sections and entete.livrees != len(distinctes):
        trouves.append(
            Controle(
                code="total-annonce-divergent",
                severite=Severite.BLOQUANT,
                sujet="l'en-tête du tracker",
                message=(
                    f"annonce {entete.livrees} US livrées, alors que les sections comptées n'en "
                    f"portent que {len(distinctes)} de distinctes. Une US livrée qui n'a jamais "
                    f"été insérée dans un jalon n'existe que dans la file d'attente — un tableau "
                    f"en citation, qu'aucun compteur ne voit."
                ),
            )
        )

    # Une même US peut être listée ✅ dans deux sections (une US remontée d'un lot d'ajouts) : sans
    # ce dédoublonnage, le même constat s'afficherait deux fois pour un seul défaut.
    vues: set[str] = set()
    for section in sections:
        for ligne in section.comptees:
            # Le contrôle ne porte que sur les ✅ : une US planifiée mais pas encore spécifiée est
            # un état normal du backlog. Sur une US livrée, l'absence de spécification est en
            # revanche un constat sans ambiguïté — on ne livre pas ce qui n'a jamais été écrit.
            if ligne.etat != suivi.LIVREE or ligne.identifiant in vues:
                continue
            vues.add(ligne.identifiant)
            story = specifiees.get(ligne.identifiant)
            if story is None:
                trouves.append(
                    Controle(
                        code="us-hors-stories",
                        severite=Severite.BLOQUANT,
                        sujet=ligne.identifiant,
                        message=(
                            f"est portée livrée par le tracker « {section.titre} », "
                            f"mais aucune fiche ne la spécifie dans `stories/`."
                        ),
                    )
                )
            elif not _titres_concordent(ligne.titre, story.titre):
                trouves.append(
                    Controle(
                        code="titre-divergent",
                        severite=Severite.SIGNAL,
                        sujet=ligne.identifiant,
                        message=(
                            f"s'intitule « {ligne.titre} » au tracker et « {story.titre} » "
                            f"dans `{story.fichier}`."
                        ),
                    )
                )

    connus = {epic.identifiant for epic in epics}
    for epic in epics:
        for cible in epic.depend_de:
            if cible not in connus:
                trouves.append(
                    Controle(
                        code="epic-inexistant",
                        severite=Severite.BLOQUANT,
                        sujet=f"EPIC-{epic.identifiant}",
                        message=f"déclare dépendre d'EPIC-{cible}, absent d'`epics/README.md`.",
                    )
                )

    ouvertes = {dette.identifiant for dette in dettes if dette.ouverte}
    resorbees = {dette.identifiant for dette in dettes if not dette.ouverte}
    for identifiant in sorted(ouvertes & resorbees):
        trouves.append(
            Controle(
                code="dette-dans-les-deux-tables",
                severite=Severite.BLOQUANT,
                sujet=f"DETTE-{identifiant}",
                message=(
                    "figure à la fois dans « Dette ouverte » et dans « Dette résorbée » : "
                    "une résorption **déplace** la ligne, elle ne la recopie pas."
                ),
            )
        )

    reclamees: set[str] = set()
    for dette in dettes:
        for us in dette.resorption_us:
            if us in specifiees or us in reclamees:
                continue
            reclamees.add(us)
            trouves.append(
                Controle(
                    code="resorption-hors-stories",
                    severite=Severite.SIGNAL,
                    sujet=f"DETTE-{dette.identifiant}",
                    message=f"annonce sa résorption par {us}, absente de `stories/`.",
                )
            )

    par_identifiant = {decision.identifiant: decision for decision in decisions}
    cites = [adr for adr in entete.adr_du_resume if adr in par_identifiant]
    if (
        entete.derniere
        and cites
        and not any(entete.derniere in par_identifiant[adr].us for adr in cites)
    ):
        trouves.append(
            Controle(
                code="derniere-us-orpheline",
                severite=Severite.SIGNAL,
                sujet=entete.derniere,
                message=(
                    f"est annoncée « dernière » en tête du tracker, mais son résumé cite "
                    f"{', '.join('ADR-' + adr for adr in cites)}, qui ne la mentionne pas — "
                    f"le résumé décrit peut-être une autre US."
                ),
            )
        )

    return trier(tuple(trouves))


def bloquants(controles: tuple[Controle, ...]) -> tuple[Controle, ...]:
    return tuple(c for c in controles if c.severite is Severite.BLOQUANT)
