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
from collections import Counter
from pathlib import Path

from atlas import markdown
from atlas.modele import AreteCode, Controle, Decision, NoeudEnchevetre, Port, Regle, Severite
from atlas.sources import suivi
from atlas.sources.backlog import Dette, Epic, UsSpecifiee
from atlas.sources.code import SENS_AUTORISE, autorise, est_hors_domaine, est_sans_adapter
from atlas.sources.suivi import Entete, Section, compter

_US = re.compile(r"E\d{2}US\d{3}")
_DATE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _us_du_backlog(racine: Path) -> set[str]:
    """Tout identifiant **cité** dans `stories/`, fiche ou simple mention en prose.

    ⚠️ Volontairement plus large que `backlog.lire_us_specifiees`, qui n'accepte qu'un **titre**
    de fiche. Les deux répondent à « cette US est-elle dans `stories/` ? » et divergent sur le cas
    intermédiaire — une US mentionnée sans fiche propre. C'est délibéré : ici, un ADR qui cite une
    US inconnue est un **signal** et la mention suffit à lever le doute ; là-bas, une US **livrée**
    sans fiche est un **bloquant** et seule une vraie fiche l'acquitte.
    """
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


def _cycles(epics: tuple[Epic, ...]) -> tuple[str, ...]:
    """Les epics engagés dans un cycle de dépendances, par ordre d'identifiant.

    Parcours en profondeur avec pile explicite : le graphe est minuscule, mais une récursion
    Python sur un graphe faux buterait sur la limite d'appels avant de dire quoi que ce soit.
    """
    dependances = {epic.identifiant: epic.depend_de for epic in epics}
    engages: set[str] = set()
    for depart in dependances:
        pile = [(depart, iter(dependances.get(depart, ())))]
        en_cours = {depart}
        while pile:
            noeud, voisins = pile[-1]
            suivant = next(voisins, None)
            if suivant is None:
                pile.pop()
                en_cours.discard(noeud)
                continue
            if suivant == depart:
                engages.add(depart)
                pile.clear()
                break
            if suivant in en_cours or suivant not in dependances:
                continue
            en_cours.add(suivant)
            pile.append((suivant, iter(dependances[suivant])))
    return tuple(sorted(engages))


# ⚠️ **Il n'y a pas de contrôle de « titre divergent » ici, et c'est un constat, pas un oubli.**
# La première version comparait le libellé du tracker à celui de `stories/` par recouvrement de
# mots. Mesuré le 16/08/2026, puis attaqué en revue : à l'égalité stricte il criait sur 23 des 109
# US livrées, **toutes** des reformulations du même travail ; au seuil qui les taisait, on
# construisait sans effort des faux négatifs — « Supprimer un archer » concordait avec « Supprimer
# un club », « Placement automatique des cibles » avec « Placement manuel des cibles ». Précision
# mesurée : **0 vrai positif sur 2 signaux**. Aucun seuil ne sépare les deux populations, parce
# qu'un titre reformulé et un titre changé se ressemblent exactement autant.
# Un signal à la fois bruyant et poreux n'apprend qu'une chose au lecteur : ignorer la page. Le
# retirer est plus honnête que de le documenter comme « calibré ».


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
    if sections and entete.livrees != len(distinctes):
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
    # Un même identifiant porté par deux glyphes différents dans deux sections. En **signal** et
    # non en bloquant : la colonne « État » ne dit pas partout la même chose — dans « Résorptions
    # de dette planifiées », elle dit si la résorption est faite, pas si l'US est livrée. Trancher
    # mécaniquement entre les deux lectures reviendrait à arbitrer un sens que le tracker n'a pas
    # fixé ; le dire à l'humain est le bon niveau.
    etats: dict[str, dict[str, str]] = {}
    for section in sections:
        for ligne in section.comptees:
            etats.setdefault(ligne.identifiant, {})[section.titre] = ligne.etat
    for identifiant, par_section in sorted(etats.items()):
        if len(set(par_section.values())) > 1:
            trouves.append(
                Controle(
                    code="etat-contradictoire",
                    severite=Severite.SIGNAL,
                    sujet=identifiant,
                    message=(
                        "porte deux états différents selon la section : "
                        + " · ".join(
                            f"{glyphe or '(vide)'} dans « {titre} »"
                            for titre, glyphe in sorted(par_section.items())
                        )
                        + "."
                    ),
                )
            )

    connus = {epic.identifiant for epic in epics}
    for identifiant in _cycles(epics):
        trouves.append(
            Controle(
                code="cycle-entre-epics",
                severite=Severite.BLOQUANT,
                sujet=f"EPIC-{identifiant}",
                message=(
                    "appartient à un cycle de dépendances : aucun de ces epics ne peut commencer "
                    "avant les autres. ⚠️ Un cycle est aussi la seule erreur que le schéma ne "
                    "montre pas — sa réduction transitive en efface toutes les arêtes, chacune "
                    "étant impliquée par le chemin qui passe par les suivantes."
                ),
            )
        )

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

    # ⚠️ Le doublon **dans une même table** est un cas distinct du précédent, et c'est **celui qui
    # s'est réellement produit** : deux `DETTE-065` ont atteint `main`, toutes deux dans « Dette
    # ouverte ». `ouvertes & resorbees` était vide, donc muet. Le garde-fou né de ce défaut ne le
    # voyait pas — il vivait dans un test, pas dans la porte.
    comptes = Counter(dette.identifiant for dette in dettes)
    for identifiant, combien in sorted(comptes.items()):
        if combien > 1:
            trouves.append(
                Controle(
                    code="dette-numero-en-double",
                    severite=Severite.BLOQUANT,
                    sujet=f"DETTE-{identifiant}",
                    message=(
                        f"est inscrite {combien} fois au registre. Deux dettes distinctes ont pris "
                        f"le même numéro libre et, chacune l'ayant écrite loin de l'autre **pour "
                        f"éviter un conflit**, git les a fusionnées sans un mot."
                    ),
                )
            )

    reclamees: set[tuple[str, str]] = set()
    for dette in dettes:
        for us in dette.resorption_us:
            # Dédoublonné par **(dette, US)** et non par US seule : trois dettes qui réclament la
            # même US absente sont trois faits, pas un — le sujet du contrôle est la dette.
            if us in specifiees or (dette.identifiant, us) in reclamees:
                continue
            reclamees.add((dette.identifiant, us))
            trouves.append(
                Controle(
                    code="resorption-hors-stories",
                    severite=Severite.SIGNAL,
                    sujet=f"DETTE-{dette.identifiant}",
                    message=f"annonce sa résorption par {us}, absente de `stories/`.",
                )
            )

    # Le rappel « … qui donne J0 12/12, J1 46/46, … » de la Légende : une **cinquième** écriture
    # des mêmes nombres, à la main, dans le fichier même qui édicte la règle de comptage. Elle se
    # périme exactement comme les en-têtes de section qu'elle récapitule — mode de panne n°1 du
    # 08/08/2026, un cran au-dessus.
    calcules = {
        section.titre.split(" ", 1)[0]: compter(section)
        for section in sections
        if section.compteur_ecrit is not None
    }
    for jalon, n, total in entete.recapitulatif:
        attendu = calcules.get(jalon)
        if attendu is not None and attendu != (n, total):
            trouves.append(
                Controle(
                    code="recapitulatif-divergent",
                    severite=Severite.BLOQUANT,
                    sujet=f"le rappel de la Légende, {jalon}",
                    message=(
                        f"annonce {n}/{total} alors que la section donne "
                        f"{attendu[0]}/{attendu[1]}."
                    ),
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


def verifier_code(
    aretes: tuple[AreteCode, ...],
    ports: tuple[Port, ...],
    noeuds: tuple[NoeudEnchevetre, ...],
) -> tuple[Controle, ...]:
    """Ce que le code fait des règles d'architecture — un seul bloquant, et il est exact.

    Calibrage, dans la ligne des sévérités posées en tête de module :

    - **bloquant** — `sens-des-dependances`. Constat AST, donc sans approximation, et **satisfait
      au moment de la livraison** : la porte est verte le premier jour et ne fait que verrouiller
      un invariant. C'est le trou réel que cette tranche bouche —
      `tests/test_domain_isolation.py` ne surveille que le domaine, les quatre autres sens ne
      l'étaient par rien ;
    - **signal** — tout le reste. `port-hors-domaine` est un écart de **conception** qui peut être
      légitime ; `port-sans-adapter` repose sur un appariement structurel heuristique ;
      `features-enchevetrees` est lu à l'expression régulière. Bloquer là-dessus ferait rougir la
      CI dès la livraison (19 features sont déjà enchevêtrées) et la ferait désactiver — on
      perdrait alors aussi le bloquant ci-dessus, qui, lui, était juste.
    """
    trouves: list[Controle] = []

    for arete in aretes:
        if autorise(arete.couche_source, arete.couche_cible):
            continue
        permis = sorted(SENS_AUTORISE.get(arete.couche_source, frozenset()))
        # `origines` ne peut pas être vide par construction, mais `AreteCode` est une dataclass
        # publique : une garde vaut mieux qu'un `IndexError` au milieu d'un contrôle bloquant.
        exemple = f", dont {arete.origines[0]}" if arete.origines else ""
        trouves.append(
            Controle(
                code="sens-des-dependances",
                severite=Severite.BLOQUANT,
                sujet=arete.paquet_source,
                message=(
                    f"importe {arete.paquet_cible} ({arete.occurrences} fois{exemple}) : la "
                    f"couche « {arete.couche_source} » ne peut dépendre que de "
                    f"{', '.join(permis) or '— aucune couche'} (règle 2)."
                ),
            )
        )

    # ⚠️ **Agrégé, et non un signal par port.** Vingt ports hors domaine faisaient vingt verdicts
    # au message identique — 39 % de la page « Écarts constatés » réduits à une seule ligne
    # répétée, relevant tous du **même** arbitrage déjà tranché. C'est le mécanisme que le
    # calibrage ci-dessus dit vouloir éviter, appliqué un cran plus bas : une page de signaux
    # qu'on cesse de lire. Le détail port par port vit sur « La carte du code », qui l'affiche.
    hors_domaine = [port for port in ports if est_hors_domaine(port)]
    if hors_domaine:
        trouves.append(
            Controle(
                code="port-hors-domaine",
                severite=Severite.SIGNAL,
                sujet=", ".join(sorted({port.couche for port in hors_domaine})),
                message=(
                    f"déclare {len(hors_domaine)} port(s) hors du domaine "
                    f"({', '.join(port.nom for port in hors_domaine[:4])}"
                    f"{'…' if len(hors_domaine) > 4 else ''}) — la règle 2 veut les ports dans le "
                    f"domaine et les adapters dans l'infrastructure. Écart peut-être légitime "
                    f"(une préoccupation technique n'est pas du métier de tir à l'arc) : à "
                    f"trancher par un humain, pas par la porte. Détail sur « La carte du code »."
                ),
            )
        )

    for port in ports:
        if est_sans_adapter(port):
            trouves.append(
                Controle(
                    code="port-sans-adapter",
                    severite=Severite.SIGNAL,
                    sujet=port.nom,
                    message=(
                        f"({port.fichier}) n'est satisfait par aucune classe du backend : "
                        f"aucune ne porte ses {len(port.methodes)} membre(s) public(s). "
                        f"Port mort, ou adapter hors des cinq couches."
                    ),
                )
            )

    for noeud in noeuds:
        trouves.append(
            Controle(
                code="features-enchevetrees",
                severite=Severite.SIGNAL,
                sujet=noeud.features[0],
                message=(
                    f"et {len(noeud.features) - 1} autre(s) feature(s) s'importent mutuellement "
                    f"({', '.join(noeud.features)}) : aucune ne peut plus être lue, testée ni "
                    f"retirée seule (règle 10). Lecture heuristique — jamais bloquante."
                ),
            )
        )

    return trier(tuple(trouves))


def bloquants(controles: tuple[Controle, ...]) -> tuple[Controle, ...]:
    return tuple(c for c in controles if c.severite is Severite.BLOQUANT)
