"""Les objets de l'atlas : règles, décisions, liens, contrôles.

Tous `frozen` — l'atlas ne mute rien, il projette. Les collections sont des `tuple` pour rester
hachables et pour que l'ordre de sérialisation soit celui du tri décidé à la construction : la
sortie est **commitée et comparée en CI**, donc le moindre indéterminisme la ferait clignoter.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AtlasSourceInvalide(Exception):
    """Une source versionnée ne respecte pas la forme attendue.

    Levée fort et tôt, jamais avalée : un parseur qui « fait de son mieux » sur une source qu'il
    ne comprend plus produit un atlas faux, ce qui est pire qu'un atlas absent.
    """


class TypeLien(StrEnum):
    """Les six sens réels derrière les ~26 libellés de relation employés par les ADR."""

    AMENDE = "amende"
    REMPLACE = "remplace"
    COMPLETE = "complete"
    SOCLE = "socle"
    VOISIN = "voisin"
    US = "us"
    CODE = "code"


class Sens(StrEnum):
    SORTANT = "sortant"
    ENTRANT = "entrant"
    SYMETRIQUE = "symetrique"


class Statut(StrEnum):
    ACCEPTE = "accepte"
    REMPLACE = "remplace"


class Severite(StrEnum):
    BLOQUANT = "bloquant"
    SIGNAL = "signal"


@dataclass(frozen=True, slots=True)
class Amendement:
    """Un changement daté subi par une règle.

    `origine` distingue les deux sources : `incise` = la parenthèse en italique écrite à la main
    dans `CLAUDE.md` (elle porte le *pourquoi*), `git` = un commit ayant touché le bloc de la règle
    (il porte l'*exhaustivité*). Les deux se complètent et ne se remplacent pas.
    """

    date: str
    nature: str
    motif: str
    us: tuple[str, ...]
    adr: tuple[str, ...]
    origine: str
    reference: str = ""


@dataclass(frozen=True, slots=True)
class Regle:
    """Une règle du projet, identifiée par son ancre — jamais par son numéro ni son titre."""

    identifiant: str
    section: str
    rang: int
    titre: str
    corps: str
    fichier: str
    ligne: int
    ligne_fin: int
    amendements: tuple[Amendement, ...]
    adr: tuple[str, ...]
    us: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Lien:
    """Une relation déclarée par l'en-tête d'un ADR, normalisée mais sans perte.

    `libelle` conserve le verbe d'origine (`Amende`, `Prolongé par`, `Raffine`…) : la normalisation
    sert au graphe, la nuance reste lisible sur la fiche.
    """

    type: TypeLien
    sens: Sens
    cible: str
    libelle: str


@dataclass(frozen=True, slots=True)
class Portage:
    """Un module qu'un ADR déclare porter sa décision — et l'état réel de cette promesse.

    `existe` est un constat sans ambiguïté, donc **bloquant** ; `symboles_absents` repose sur une
    extraction heuristique (les symboles sont cités en prose, après un tiret), donc **signalé** et
    non bloquant : un contrôle heuristique qui bloque la CI finit désactivé.
    """

    chemin: str
    existe: bool
    symboles: tuple[str, ...] = ()
    symboles_absents: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Decision:
    """Un ADR."""

    identifiant: str
    titre: str
    statut: Statut
    statut_brut: str
    remplace_par: str
    date: str
    date_brute: str
    fichier: str
    liens: tuple[Lien, ...]
    portage: tuple[Portage, ...]
    us: tuple[str, ...]
    extrait: str
    amende_par: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Controle:
    """Un écart constaté entre ce que l'écrit promet et ce que le dépôt contient."""

    code: str
    severite: Severite
    sujet: str
    message: str
