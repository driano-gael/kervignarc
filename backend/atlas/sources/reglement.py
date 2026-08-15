"""Lecture du règlement — les règles du projet, telles qu'elles sont en vigueur aujourd'hui.

Une règle est identifiée par son **ancre** (`<!--regle:slug-->`), jamais par son numéro ni par son
titre. C'est le point dur de tout l'atlas : `CLAUDE.md` a été remanié dix-neuf fois en cinq
semaines, et un identifiant dérivé du rang ou du libellé aurait détaché chaque historique de sa
règle au premier réordonnancement — sans rien casser de visible. L'ancre rend l'identité explicite
et opposable ; en contrepartie, une règle qui en manque fait échouer le générateur.

Périmètre : les quatre sections qui portent les règles d'ingénierie. « Communication avec
l'utilisateur » et « Apprendre à piloter l'assistant » en sont exclues — elles cadrent la façon de
s'exprimer de l'assistant, pas le projet.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from atlas import markdown
from atlas.modele import Amendement, AtlasSourceInvalide, Regle

SECTIONS = ("Règles non négociables", "Dette", "Économie de contexte", "Workflow")

_ANCRE = re.compile(r"<!--regle:(?P<identifiant>[a-z0-9-]+)-->")
_GRAS = re.compile(r"\*\*(?P<titre>.+?)\*\*", re.DOTALL)
_ADR_CITE = re.compile(r"ADR-(\d{4})")
_US_CITEE = re.compile(r"E\d{2}US\d{3}")

# Les amendements écrits à la main vivent tous dans une incise en italique parenthésée. Le motif
# est paresseux jusqu'au `)*` littéral, pour survivre au gras et aux parenthèses imbriquées que
# ces incises contiennent presque toujours.
_INCISE = re.compile(r"\*\((?P<corps>(?:(?!\)\*).)*?)\)\*", re.DOTALL)
_DATE_FR = re.compile(r"(?P<jour>\d{2})/(?P<mois>\d{2})/(?P<annee>\d{4})")

# La nature se lit à la tête de l'incise. Une tête inconnue donne « autre » **sans échouer** :
# c'est de la prose, et une porte qui rougit sur un choix de style serait désactivée en un mois.
# Le contraste avec la table `_RELATIONS` est délibéré — là-bas on perdrait une arête du graphe,
# ici on perd une étiquette.
_NATURES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^\s*Ajout[ée]?e?\s+le\b", re.IGNORECASE), "ajout"),
    (re.compile(r"^\s*R[èe]gle\s+resserr[ée]e?\b", re.IGNORECASE), "resserrement"),
    (re.compile(r"^\s*Cas\s+r[ée]el\b", re.IGNORECASE), "cas réel"),
    (re.compile(r"^\s*Manqu[ée]\s+sur\b", re.IGNORECASE), "manquement"),
    (re.compile(r"^\s*Pr[ée]cis[ée]?\b", re.IGNORECASE), "précision"),
    (re.compile(r"^\s*Institu[ée]e?\b", re.IGNORECASE), "institution"),
)


def _nature(corps: str) -> str:
    for motif, nom in _NATURES:
        if motif.match(corps):
            return nom
    return "autre"


def _amendements(corps: str) -> tuple[Amendement, ...]:
    """Les changements datés que la règle porte en clair dans son propre texte."""
    trouves: list[Amendement] = []
    for incise in _INCISE.finditer(corps):
        texte = " ".join(incise.group("corps").split())
        date = _DATE_FR.search(texte)
        if date is None:
            continue  # une parenthèse en italique sans date n'est pas un amendement
        trouves.append(
            Amendement(
                date="-".join(date.group("annee", "mois", "jour")),
                nature=_nature(texte),
                motif=markdown.en_clair(texte),
                us=tuple(dict.fromkeys(_US_CITEE.findall(texte))),
                adr=tuple(dict.fromkeys(_ADR_CITE.findall(texte))),
                origine="incise",
            )
        )
    return tuple(sorted(trouves, key=lambda a: (a.date, a.motif)))


_MARQUEUR_DE_LISTE = re.compile(r"^(?:\d+\.|[-*])\s*")


def _sans_decor(bloc: str) -> str:
    """Le bloc débarrassé de son ancre et de son marqueur de liste."""
    return _MARQUEUR_DE_LISTE.sub("", _ANCRE.sub("", bloc).strip()).strip()


def _corps(bloc: str) -> str:
    """Le texte de la règle **sans le titre** qui l'ouvre.

    Sans cette coupe, la fiche afficherait deux fois le même intitulé — une fois en titre, une fois
    en tête du corps. Quand la règle n'a pas de titre en gras et tient en une phrase, le titre dit
    déjà tout : le corps est alors vide plutôt que redondant.
    """
    texte = _sans_decor(bloc)
    gras = _GRAS.match(texte)
    if gras:
        return texte[gras.end() :].lstrip(" .:\n").strip()
    return "" if len(texte) <= 120 else texte


def _titre(bloc: str) -> str:
    """Le titre en gras **qui ouvre** la règle ; à défaut, sa première phrase.

    Deux pièges que le dépôt contient réellement :
    - le gras court parfois sur deux lignes et **enferme un lien Markdown** (« Le suivi des US
      ([`journal-d-avancement/SUIVI-US.md`](…)) est tenu à jour… ») — d'où le `DOTALL` et le
      passage par `en_clair` ;
    - certaines règles n'ont **pas** de titre en gras, mais du gras au milieu de leur phrase
      (« …doit être **redécoupée** ») : prendre le premier gras venu donnerait « redécoupée » pour
      titre. D'où `match` et non `search` — le gras ne fait titre que s'il ouvre la règle.
    """
    texte = _sans_decor(bloc)
    gras = _GRAS.match(texte)
    return markdown.tronquer(markdown.en_clair(gras.group("titre") if gras else texte), 80).rstrip(
        " .:"
    )


def lire_regles(racine: Path) -> tuple[Regle, ...]:
    chemin = racine / "CLAUDE.md"
    lignes = markdown.lire(chemin).split("\n")

    reperes: list[tuple[int, str, str]] = []  # (index, identifiant, section)
    section = ""
    for index, ligne in enumerate(lignes):
        if ligne.startswith("## "):
            section = ligne[3:].strip()
        ancre = _ANCRE.search(ligne)
        if ancre and section in SECTIONS:
            reperes.append((index, ancre.group("identifiant"), section))

    if not reperes:
        raise AtlasSourceInvalide(
            "CLAUDE.md : aucune ancre `<!--regle:slug-->` trouvée. Les règles doivent être ancrées "
            "pour que leur historique leur reste attaché à travers les réorganisations."
        )

    regles: list[Regle] = []
    rangs: dict[str, int] = {}
    for position, (debut, identifiant, section_courante) in enumerate(reperes):
        fin = _fin_du_bloc(lignes, debut, reperes, position)
        bloc = "\n".join(lignes[debut:fin])
        # On extrait depuis le bloc **entier** et on n'affiche que le corps allégé de son titre :
        # chercher dans le texte tronqué perdrait les incises et les renvois d'une règle dont le
        # titre porte toute la phrase.
        entier = _sans_decor(bloc)
        rangs[section_courante] = rangs.get(section_courante, 0) + 1
        regles.append(
            Regle(
                identifiant=identifiant,
                section=section_courante,
                rang=rangs[section_courante],
                titre=_titre(bloc),
                corps=_corps(bloc),
                fichier="CLAUDE.md",
                ligne=debut + 1,
                ligne_fin=fin,
                amendements=_amendements(entier),
                adr=tuple(dict.fromkeys(_ADR_CITE.findall(entier))),
                us=tuple(dict.fromkeys(_US_CITEE.findall(entier))),
            )
        )

    comptes = Counter(r.identifiant for r in regles)
    doublons = sorted(identifiant for identifiant, n in comptes.items() if n > 1)
    if doublons:
        raise AtlasSourceInvalide(
            f"CLAUDE.md : ancres en double {doublons}. Une ancre identifie une règle et une seule."
        )
    return tuple(regles)


def _fin_du_bloc(
    lignes: list[str], debut: int, reperes: list[tuple[int, str, str]], position: int
) -> int:
    """La borne haute (exclue) du bloc d'une règle : l'ancre suivante, ou la fin de la section."""
    suivante = reperes[position + 1][0] if position + 1 < len(reperes) else len(lignes)
    for index in range(debut + 1, min(suivante, len(lignes))):
        if lignes[index].startswith("## "):
            return index
    return suivante
