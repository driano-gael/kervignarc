"""La vue d'avancement : ce que les quatre livrables de suivi disent, mis côte à côte.

`SUIVI-US.md` dit l'**état**, `stories/` dit ce que l'US **est**, `epics/README.md` dit à quelle
capacité elle appartient et de quoi celle-ci dépend, `docs/dette.md` dit ce qu'elle a laissé
derrière elle. Aucun des quatre ne connaît les trois autres. Ce module ne tranche rien : il
rapproche, et laisse `controles.verifier_avancement` dire là où le rapprochement échoue.

⚠️ **L'état d'une US ne se déduit jamais de git.** Le tracker prévient lui-même que `E00US016`,
`E01US018` et `E01US019` ont un commit dans `main` sans être livrées : une vue qui lirait le
journal des commits les compterait faites. Le glyphe écrit à la main fait autorité.
"""

from __future__ import annotations

from typing import Any

from atlas.modele import Decision
from atlas.sources import suivi
from atlas.sources.backlog import Dette, Epic, UsSpecifiee
from atlas.sources.suivi import LIVREE, Entete, Section, compter


def _epic_de(identifiant: str) -> str:
    """`E05US026` → `05`. L'appartenance d'une US à un epic est portée par son identifiant."""
    return identifiant[1:3]


def construire(
    sections: tuple[Section, ...],
    epics: tuple[Epic, ...],
    dettes: tuple[Dette, ...],
    us_specifiees: tuple[UsSpecifiee, ...],
    decisions: tuple[Decision, ...],
    entete: Entete,
) -> dict[str, Any]:
    """La charge utile de la page d'avancement — triée, sans horodatage, sans chemin absolu."""
    specifiees = {us.identifiant: us for us in us_specifiees}
    titres_epic = {epic.identifiant: epic.titre for epic in epics}

    adr_par_us: dict[str, list[str]] = {}
    for decision in decisions:
        for identifiant in decision.us:
            adr_par_us.setdefault(identifiant, []).append(decision.identifiant)

    introduites: dict[str, list[str]] = {}
    resorbees: dict[str, list[str]] = {}
    for dette in dettes:
        for identifiant in dette.introduite_par:
            introduites.setdefault(identifiant, []).append(dette.identifiant)
        for identifiant in dette.resorption_us:
            resorbees.setdefault(identifiant, []).append(dette.identifiant)

    vues: dict[str, dict[str, Any]] = {}
    rendu_sections: list[dict[str, Any]] = []
    for section in sections:
        calcule = compter(section)
        rendu_sections.append(
            {
                "titre": section.titre,
                "compteur_ecrit": list(section.compteur_ecrit) if section.compteur_ecrit else None,
                "calcule": list(calcule),
                "lignes": [
                    {
                        "identifiant": ligne.identifiant,
                        "titre": ligne.titre,
                        "etat": ligne.etat,
                        "comptee": section.est_comptee(ligne),
                    }
                    for ligne in section.lignes
                ],
            }
        )
        for ligne in section.lignes:
            if not ligne.identifiant:
                continue
            fiche = vues.setdefault(
                ligne.identifiant,
                {
                    "identifiant": ligne.identifiant,
                    "titre": ligne.titre,
                    "titre_retenu": False,
                    "etat": ligne.etat,
                    "sections": [],
                    "epic": _epic_de(ligne.identifiant),
                    "epic_titre": titres_epic.get(_epic_de(ligne.identifiant), ""),
                    "story": "",
                    "titre_story": "",
                    "adr": sorted(set(adr_par_us.get(ligne.identifiant, ()))),
                    "dettes_introduites": sorted(set(introduites.get(ligne.identifiant, ()))),
                    "dettes_resorbees": sorted(set(resorbees.get(ligne.identifiant, ()))),
                },
            )
            fiche["sections"].append(section.titre)
            # Une US listée dans deux sections (remontée d'un lot d'ajouts) : l'état le plus avancé
            # gagne — c'est le glyphe de la section où elle a réellement été livrée. Une éventuelle
            # contradiction n'est pas tue pour autant : `etat-contradictoire` la signale.
            if ligne.etat == LIVREE:
                fiche["etat"] = LIVREE
            # Le titre affiché doit être celui que le contrôle compare — la première ligne
            # **comptée**. Sans cette clause, la fiche d'`E00US015` montrait le libellé de sa ligne
            # hors décompte, donc un titre que rien n'avait vérifié.
            if section.est_comptee(ligne) and not fiche["titre_retenu"]:
                fiche["titre_retenu"] = True
                fiche["titre"] = ligne.titre
            story = specifiees.get(ligne.identifiant)
            if story is not None:
                fiche["story"] = story.fichier
                fiche["titre_story"] = story.titre

    # `titre_retenu` n'est qu'un drapeau de construction : il ne sort pas. Une clé interne
    # sérialisée serait comparée à l'octet par la CI et lue par le site — donc un contrat de fait.
    fiches = [{c: v for c, v in vues[i].items() if c != "titre_retenu"} for i in sorted(vues)]
    vivantes = [fiche for fiche in fiches if fiche["etat"] != suivi.ABSORBEE]

    return {
        "entete": {"derniere": entete.derniere, "adr_du_resume": list(entete.adr_du_resume)},
        # Les nombres de la page sont calculés **ici**, par la même règle que les contrôles. Les
        # recalculer en JavaScript aurait fait une **troisième** écriture de la règle de comptage,
        # sur la page dont le sujet est précisément que les compteurs ne se contredisent pas.
        "resume": {
            "livrees": sum(1 for fiche in vivantes if fiche["etat"] == LIVREE),
            "vivantes": len(vivantes),
        },
        "sections": rendu_sections,
        "epics": [
            {
                "identifiant": epic.identifiant,
                "titre": epic.titre,
                "priorite": epic.priorite,
                "depend_de": list(epic.depend_de),
            }
            for epic in epics
        ],
        "dettes": [
            {
                "identifiant": dette.identifiant,
                "ouverte": dette.ouverte,
                "severite": dette.severite,
                "introduite_par": list(dette.introduite_par),
                "resorption_us": list(dette.resorption_us),
            }
            for dette in dettes
            if dette.ouverte
        ],
        "fiches": fiches,
    }
