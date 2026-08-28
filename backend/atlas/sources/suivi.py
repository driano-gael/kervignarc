"""Lecture du tracker — `journal-d-avancement/SUIVI-US.md`, le point de reprise du projet.

Ce fichier est écrit **à la main** et prévient lui-même qu'il est piégeux : sept variantes d'en-tête
de tableau, six glyphes d'état, du texte barré conservé, des US absorbées hors décompte. Il porte
**sa propre règle de comptage**, instituée le 08/08/2026 après que trois compteurs sur cinq se sont
révélés faux ; c'est elle l'oracle, pas ce code. ⚠️ Parti pris hérité de l'atlas : **échouer
bruyamment** sur une table qu'on ne sait pas lire plutôt que produire un décompte faux.
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
# Ancré en **fin de titre** : c'est la forme de toutes les sections réelles, et un `(2026/08)`
# glissé au milieu d'un libellé serait sinon lu comme un compteur — donc rejeté comme divergent,
# sur un titre parfaitement légitime.
_COMPTEUR = re.compile(r"\((\d+)/(\d+)\)\s*\**\s*$")
_BARRE = re.compile(r"~~")
_ADR = re.compile(r"ADR-(\d{4})")
# La ligne d'annonce porte les deux champs : « … · **112 US livrées** · dernière : `E00US019` ».
_DERNIERE = re.compile(r"derni[èe]re\s*:\s*`(E\d{2}US\d{3})`", re.I)
_TOTAL_LIVREES = re.compile(r"(\d+)\s+US\s+livr[ée]es?", re.I)
# « … qui donne J0 12/12, J1 46/46, J2 14/14, J3 16/18 et J4 0/7 », dans la Légende.
_RAPPEL_DE_JALON = re.compile(r"\bJ(\d)\s+(\d+)/(\d+)")


@dataclass(frozen=True, slots=True)
class Entete:
    """Ce que le tracker **déclare de lui-même**, et que rien d'autre ne vérifiait.

    L'annonce de tête (dernière US, total livré, ADR cités par le résumé) et le rappel des
    compteurs de jalon dans la Légende : des nombres et des noms écrits **à la main** dans le
    fichier qu'ils décrivent, donc recalculés comme les en-têtes de section. L'annonce et le résumé
    se recoupent : si le résumé décrit une **autre** US que celle annoncée — le défaut trouvé sur
    `main` le 16/08/2026 — l'ADR qu'il cite ne connaîtra pas l'US annoncée.
    """

    derniere: str
    adr_du_resume: tuple[str, ...]
    # Le total annoncé en tête. C'est un compteur au même titre que ceux des sections — et il se
    # trompe d'un mode qui leur est propre : une US **livrée mais jamais insérée dans un jalon**
    # (elle n'existe que dans la file d'attente, en citation) le gonfle sans qu'aucune section ne
    # bouge. Jamais optionnel : un en-tête illisible fait **échouer la lecture**, il ne rend pas un
    # champ vide que le contrôle traiterait comme « rien à dire ».
    livrees: int
    # Les compteurs de jalon rappelés en toutes lettres dans la Légende — cinquième écriture des
    # mêmes nombres, recalculée comme les autres.
    recapitulatif: tuple[tuple[str, int, int], ...] = ()


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

    def est_comptee(self, ligne: LigneUS) -> bool:
        """La règle de la Légende, définie **une seule fois**, ici.

        Trois exclusions, chacune tirée d'un mode de panne constaté : **pas d'identifiant d'US**
        (un relevé, du travail livré mais pas une unité de travail) ; **absorbée (⛔)**, la
        capacité ayant été livrée ailleurs ; **hors séquence** dans un jalon, l'US étant remontée
        d'une section d'ajouts où elle est déjà comptée. Exposée en **prédicat** et pas seulement
        en filtre : passer par l'identité mémoire des objets rendus deviendrait faux en silence.
        """
        return bool(
            ligne.identifiant
            and ligne.etat != ABSORBEE
            and not (self.a_colonne_seq and ligne.hors_sequence)
        )

    @property
    def comptees(self) -> tuple[LigneUS, ...]:
        """Les lignes qui entrent dans le `n/N`."""
        return tuple(ligne for ligne in self.lignes if self.est_comptee(ligne))


def compter(section: Section) -> tuple[int, int]:
    """Le `(n, N)` d'une section : N les lignes comptées, n celles qui sont livrées."""
    comptees = section.comptees
    return sum(1 for ligne in comptees if ligne.etat == LIVREE), len(comptees)


def _glyphe(cellule: str) -> str:
    for caractere in cellule:
        if caractere in GLYPHES:
            return caractere
    return ""


def _colonnes(entete: list[str], *, titre: str, compte: bool) -> dict[str, int]:
    """Les colonnes du tableau d'une section, repérées par leur nom.

    Cf. `markdown.index_colonnes` : sept variantes d'en-tête coexistent dans ce fichier.
    """
    index = markdown.index_colonnes(entete)
    if "US" not in index:
        raise AtlasSourceInvalide(
            f"{FICHIER} : la section « {titre} » porte un tableau sans colonne « US ». "
            f"Le lecteur ne devine pas les colonnes — nomme-la, ou sors ce tableau de la section."
        )
    if compte and "État" not in index:
        # ⚠️ Le remède proposé ne mentionne **pas** « retire le `n/N` du titre », bien que ce soit
        # techniquement suffisant pour faire taire l'erreur : un message qui enseigne la porte de
        # sortie à parité du correctif transforme le garde-fou en option.
        raise AtlasSourceInvalide(
            f"{FICHIER} : la section « {titre} » annonce un compteur mais son tableau n'a pas de "
            f"colonne « État ». Un compteur qu'on ne peut pas recalculer ne prouve rien : "
            f"ajoute la colonne « État » au tableau."
        )
    return index


def lire_sections_du_texte(texte: str) -> tuple[Section, ...]:
    """Découpe le tracker en sections `## `, chacune avec ses lignes de tableau.

    Les tableaux **en citation** (`> | … |`, comme la file d'exécution de « 🎯 Prochaine US ») sont
    ignorés : ce sont des vues de priorité, pas des inventaires d'US, et leurs colonnes n'ont rien
    à voir. ⚠️ Corollaire à connaître : une US qui ne figure **que** dans un tel tableau est
    invisible à tous les contrôles de section. C'est l'angle mort qui a laissé `E05US026` et
    `E05US028`, livrées, hors de tout jalon — seul le total annoncé en tête les a trahies.
    """
    sections: list[Section] = []
    titre = ""
    compteur: tuple[int, int] | None = None
    entete: dict[str, int] | None = None
    largeur = 0
    lignes: list[LigneUS] = []
    dans_un_bloc_de_code = False

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
        # Un `## ` **dans un bloc de code** n'ouvre pas de section : ce fichier documente son propre
        # format, il cite donc ses propres titres. Sans cette clause, l'exemple devenait une section
        # fantôme — bruyante, mais avec un diagnostic faux.
        if brute.lstrip().startswith("```"):
            dans_un_bloc_de_code = not dans_un_bloc_de_code
            continue
        if dans_un_bloc_de_code:
            continue
        if brute.startswith("## "):
            fermer()
            titre = brute[3:].strip()
            trouve = _COMPTEUR.search(titre)
            compteur = (int(trouve.group(1)), int(trouve.group(2))) if trouve else None
            entete = None
            lignes = []
            continue
        if not brute.startswith("|"):
            # ⚠️ Toute ligne non vide hors tableau **ferme** le tableau courant. Sans cela, un
            # second tableau de la même section était lu avec les colonnes du premier : ses
            # lignes sortaient avec un identifiant vide, donc hors décompte, et disparaissaient
            # **en silence** — dans le module dont le parti pris est de ne jamais compter faux
            # sans le dire.
            if brute.strip():
                entete = None
            continue
        if markdown.est_separateur(brute):
            continue
        cellules = markdown.cellules(brute)
        if entete is None:
            entete = _colonnes(cellules, titre=titre, compte=compteur is not None)
            largeur = len(cellules)
            continue
        if len(cellules) != largeur:
            # ⚠️ Un décalage de colonnes, dans **les deux sens**. Trop court : l'état se lit vide,
            # donc « non livrée ». Trop long : l'état se lit sur la mauvaise cellule. Les deux
            # rendent le compteur faux, et la seconde moitié de ce garde a manqué jusqu'au
            # 16/08/2026 — le commentaire, lui, décrivait déjà les deux.
            raise AtlasSourceInvalide(
                f"{FICHIER} : dans « {titre} », une ligne porte {len(cellules)} cellules pour "
                f"{largeur} colonnes — l'état ne peut pas être lu de façon sûre.\n"
                f"Un tube littéral dans une cellule s'écrit `\\|`.\n"
                f"Ligne : {' | '.join(cellules)[:120]}"
            )
        lignes.append(_ligne(cellules, entete))

    fermer()
    return tuple(sections)


def _ligne(cellules: list[str], entete: dict[str, int]) -> LigneUS:
    def cellule(nom: str) -> str:
        return markdown.cellule(cellules, entete, nom)

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
    """Ce que le tracker déclare de lui-même : son annonce de tête et le rappel de sa Légende.

    ⚠️ **Refuse plutôt que de rendre un en-tête à moitié lu.** La version précédente rendait des
    champs vides quand une regex ne mordait pas : déplacer un `**` suffisait à **éteindre en
    silence** le seul contrôle capable de voir une US livrée restée hors jalon, et un tracker
    annonçant « 999 US livrées » passait au vert (mesuré le 16/08/2026). Les deux champs se lisent
    sur **la même ligne** et le résumé court jusqu'à la première ligne vide : une borne locale.
    """
    lignes = texte.split("\n")
    for rang, ligne in enumerate(lignes):
        annonce = _DERNIERE.search(ligne)
        if not annonce:
            continue
        total = _TOTAL_LIVREES.search(ligne)
        if not total:
            raise AtlasSourceInvalide(
                f"{FICHIER} : la ligne d'annonce nomme la dernière US "
                f"({annonce.group(1)}) mais n'annonce pas de total.\n"
                f"Forme attendue sur une seule ligne : « … · **N US livrées** · dernière : "
                f"`ExxUSyyy` ».\nLigne : {ligne.strip()[:120]}"
            )
        resume: list[str] = []
        for suite in lignes[rang + 1 :]:
            if not suite.strip():
                break
            resume.append(suite)
        return Entete(
            derniere=annonce.group(1),
            adr_du_resume=tuple(dict.fromkeys(_ADR.findall("\n".join(resume)))),
            livrees=int(total.group(1)),
            recapitulatif=_recapitulatif(texte),
        )
    raise AtlasSourceInvalide(
        f"{FICHIER} : aucune ligne d'annonce lisible.\n"
        f"Forme attendue : « … · **N US livrées** · dernière : `ExxUSyyy` ».\n"
        f"Sans elle, le total annoncé n'est comparable à rien — et une US livrée restée hors "
        f"jalon redeviendrait invisible."
    )


def _recapitulatif(texte: str) -> tuple[tuple[str, int, int], ...]:
    """Les compteurs de jalon rappelés en toutes lettres dans la Légende.

    « C'est cette règle qui donne J0 12/12, J1 46/46, … » — une **cinquième** écriture des mêmes
    nombres, éditée à la main, et qui se périmait exactement comme les en-têtes de section qu'elle
    récapitule. Elle est donc recalculée comme elles.
    """
    return tuple(
        (f"J{jalon}", int(n), int(total)) for jalon, n, total in _RAPPEL_DE_JALON.findall(texte)
    )


def lire_sections(racine: Path) -> tuple[Section, ...]:
    return lire_sections_du_texte(markdown.lire(racine / FICHIER))


def lire_entete(racine: Path) -> Entete:
    return lire_entete_du_texte(markdown.lire(racine / FICHIER))
