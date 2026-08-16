"""Lecture du tracker — `journal-d-avancement/SUIVI-US.md`, le point de reprise du projet.

Ce fichier est écrit **à la main**, et il prévient lui-même qu'il est piégeux : sept variantes
d'en-tête de tableau, six glyphes d'état, du texte barré conservé pour rester trouvable, des US
absorbées hors décompte, et des lignes qui sont du travail livré sans être des US.

Il porte aussi **sa propre règle de comptage**, instituée le 08/08/2026 après que trois compteurs
sur cinq se sont révélés faux — chacun d'un mode différent. Ce module ne fait que l'appliquer à la
lettre ; c'est elle l'oracle, pas ce code.

Parti pris, hérité du reste de l'atlas : **échouer bruyamment** sur une table qu'on ne sait pas
lire plutôt que produire un décompte faux. Un compteur silencieusement faux est pire que pas de
vue du tout — c'est précisément ce que ce fichier existe pour empêcher.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from atlas import markdown
from atlas.modele import AtlasSourceInvalide

FICHIER = "journal-d-avancement/SUIVI-US.md"

# Les six glyphes d'état de la Légende. `⛔` (absorbée) et `🔒` (bloquée) ne sont pas des états
# d'avancement mais des états de **travail**, et la règle de comptage les traite différemment.
GLYPHES = "✅⬜🔶🎯🔒⛔"
ABSORBEE = "⛔"
LIVREE = "✅"

_US = re.compile(r"E\d{2}US\d{3}")
_COMPTEUR = re.compile(r"\((\d+)/(\d+)\)")
_BARRE = re.compile(r"~~")
_SEPARATEUR = re.compile(r"^[\s|:-]+$")
_ADR = re.compile(r"ADR-(\d{4})")
# « · dernière : `E00US018` », puis le résumé en italique jusqu'à « Précédente : ».
_DERNIERE = re.compile(r"derni[èe]re\s*:\s*`(E\d{2}US\d{3})`", re.I)
_TOTAL_LIVREES = re.compile(r"(\d+)\s+US\s+livr[ée]es", re.I)
_PRECEDENTE = re.compile(r"^\s*Pr[ée]c[ée]dente\s*:", re.I | re.M)


@dataclass(frozen=True, slots=True)
class Entete:
    """Ce que l'en-tête du tracker annonce : la dernière US livrée, et les ADR que son résumé cite.

    Les deux se recoupent : si le résumé décrit une **autre** US que celle annoncée — le défaut
    trouvé sur `main` le 16/08/2026 — l'ADR qu'il cite ne connaîtra pas l'US annoncée.
    """

    derniere: str
    adr_du_resume: tuple[str, ...]
    # Le total annoncé en tête. C'est un compteur au même titre que ceux des sections — et il se
    # trompe d'un mode qui leur est propre : une US **livrée mais jamais insérée dans un jalon**
    # (elle n'existe que dans la file d'attente, en citation) le gonfle sans qu'aucune section ne
    # bouge. `None` quand l'en-tête n'annonce rien.
    livrees: int | None = None


@dataclass(frozen=True, slots=True)
class LigneUS:
    """Une ligne de tableau. `identifiant` est vide quand la ligne n'est pas une US."""

    identifiant: str
    titre: str
    etat: str
    hors_sequence: bool


@dataclass(frozen=True, slots=True)
class Section:
    titre: str
    compteur_ecrit: tuple[int, int] | None
    lignes: tuple[LigneUS, ...]
    a_colonne_seq: bool

    @property
    def comptees(self) -> tuple[LigneUS, ...]:
        """Les lignes qui entrent dans le `n/N`, selon la règle de la Légende.

        Trois exclusions, et chacune correspond à un mode de panne réellement constaté :
        - **pas d'identifiant d'US** — un relevé, un lot hors US : du travail livré, pas une unité
          de travail ;
        - **absorbée (⛔)** — la capacité a été livrée par une autre US, celle-ci n'existe plus ;
        - **hors séquence (`Seq = —`)** dans un jalon — l'US est remontée d'une section d'ajouts et
          y est déjà comptée ; sans cette clause elle compterait deux fois.
        """
        return tuple(
            ligne
            for ligne in self.lignes
            if ligne.identifiant
            and ligne.etat != ABSORBEE
            and not (self.a_colonne_seq and ligne.hors_sequence)
        )


def compter(section: Section) -> tuple[int, int]:
    """Le `(n, N)` d'une section : N les lignes comptées, n celles qui sont livrées."""
    comptees = section.comptees
    return sum(1 for ligne in comptees if ligne.etat == LIVREE), len(comptees)


def _cellules(ligne: str) -> list[str]:
    return [cellule.strip() for cellule in ligne.strip().strip("|").split("|")]


def _glyphe(cellule: str) -> str:
    for caractere in cellule:
        if caractere in GLYPHES:
            return caractere
    return ""


def _colonnes(entete: list[str], *, titre: str, compte: bool) -> dict[str, int]:
    """Repère les colonnes **par leur nom**, jamais par leur position.

    Sept variantes d'en-tête coexistent (`Seq|US|Titre|État`, `US|Titre|Jalon|État`,
    `US|Titre|Épic|État`…) : se caler sur un rang aurait lu l'épic comme un état au premier
    tableau venu.
    """
    index = {nom.strip("* "): rang for rang, nom in enumerate(entete)}
    if "US" not in index:
        raise AtlasSourceInvalide(
            f"{FICHIER} : la section « {titre} » porte un tableau sans colonne « US ». "
            f"Le lecteur ne devine pas les colonnes — nomme-la, ou sors ce tableau de la section."
        )
    if compte and "État" not in index:
        raise AtlasSourceInvalide(
            f"{FICHIER} : la section « {titre} » annonce un compteur mais son tableau n'a pas de "
            f"colonne « État ». Un compteur qu'on ne peut pas recalculer ne prouve rien : "
            f"ajoute la colonne, ou retire le `n/N` du titre."
        )
    return index


def lire_sections_du_texte(texte: str) -> tuple[Section, ...]:
    """Découpe le tracker en sections `## `, chacune avec ses lignes de tableau.

    Les tableaux **en citation** (`> | … |`, comme la file d'exécution de « 🎯 Prochaine US ») sont
    ignorés : ce sont des vues de priorité, pas des inventaires d'US, et leurs colonnes n'ont rien
    à voir.
    """
    sections: list[Section] = []
    titre = ""
    compteur: tuple[int, int] | None = None
    entete: dict[str, int] | None = None
    largeur = 0
    lignes: list[LigneUS] = []

    def fermer() -> None:
        if titre:
            sections.append(
                Section(
                    titre=titre,
                    compteur_ecrit=compteur,
                    lignes=tuple(lignes),
                    a_colonne_seq=bool(entete and "Seq" in entete),
                )
            )

    for brute in texte.split("\n"):
        if brute.startswith("## "):
            fermer()
            titre = brute[3:].strip()
            trouve = _COMPTEUR.search(titre)
            compteur = (int(trouve.group(1)), int(trouve.group(2))) if trouve else None
            entete = None
            lignes = []
            continue
        if not brute.startswith("|"):
            continue
        cellules = _cellules(brute)
        if _SEPARATEUR.match(brute):
            continue
        if entete is None:
            entete = _colonnes(cellules, titre=titre, compte=compteur is not None)
            largeur = len(cellules)
            continue
        if len(cellules) < largeur:
            # ⚠️ Une ligne plus courte que son en-tête décale toutes les colonnes suivantes : l'état
            # se lirait vide, donc « non livrée », et le compteur serait faux **sans un mot**. C'est
            # exactement le décompte silencieux que ce module refuse.
            raise AtlasSourceInvalide(
                f"{FICHIER} : dans « {titre} », une ligne porte {len(cellules)} cellules pour "
                f"{largeur} colonnes — l'état ne peut pas être lu de façon sûre.\n"
                f"Ligne : {' | '.join(cellules)[:120]}"
            )
        lignes.append(_ligne(cellules, entete))

    fermer()
    return tuple(sections)


def _ligne(cellules: list[str], entete: dict[str, int]) -> LigneUS:
    def cellule(nom: str) -> str:
        rang = entete.get(nom)
        return cellules[rang] if rang is not None and rang < len(cellules) else ""

    brut_us = _BARRE.sub("", cellule("US"))
    trouve = _US.search(brut_us)
    seq = _BARRE.sub("", cellule("Seq")).strip()
    return LigneUS(
        identifiant=trouve.group(0) if trouve else "",
        titre=markdown.en_clair(cellule("Titre")),
        etat=_glyphe(cellule("État")),
        # « — » sans chiffre : l'US est hors séquence, remontée d'une section d'ajouts.
        hors_sequence=bool(seq) and not any(c.isdigit() for c in seq),
    )


def lire_entete_du_texte(texte: str) -> Entete:
    """L'annonce de tête : « dernière : `ExxUSyyy` » et les ADR cités par le résumé qui la suit.

    Le résumé court de l'annonce jusqu'à « Précédente : » — pas jusqu'à la fin du fichier, sans
    quoi le contrôle ramasserait les ADR de **toutes** les US et ne dirait plus rien.
    """
    annonce = _DERNIERE.search(texte)
    if not annonce:
        return Entete(derniere="", adr_du_resume=())
    suivant = _PRECEDENTE.search(texte, annonce.end())
    resume = texte[annonce.end() : suivant.start() if suivant else len(texte)]
    total = _TOTAL_LIVREES.search(texte[: annonce.end()])
    return Entete(
        derniere=annonce.group(1),
        adr_du_resume=tuple(dict.fromkeys(_ADR.findall(resume))),
        livrees=int(total.group(1)) if total else None,
    )


def lire_sections(racine: Path) -> tuple[Section, ...]:
    return lire_sections_du_texte(markdown.lire(racine / FICHIER))


def lire_entete(racine: Path) -> Entete:
    return lire_entete_du_texte(markdown.lire(racine / FICHIER))
