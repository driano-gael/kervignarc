"""Normaliser le vocabulaire des sources — sans jamais perdre la nuance d'origine.

Le registre d'ADR emploie **33 libellés d'en-tête distincts** pour ~6 sens de relation, et il en
gagne un nouveau tous les trois ou quatre ADR. Sans table explicite, le graphe perdrait des arêtes
en silence ; avec une table qui « ignore ce qu'elle ne connaît pas », il en perdrait tout autant.
D'où le parti pris : **tout libellé inconnu fait échouer le générateur**. Écrire un ADR avec un
verbe neuf oblige alors à décider de son sens, au lieu de laisser le registre se déliter. ADR-0059
"""

from __future__ import annotations

import re
import unicodedata

from atlas.modele import AtlasSourceInvalide, Sens, Statut, TypeLien

# Champs d'en-tête qui ne décrivent aucune relation : métadonnées ou prose libre.
_METADONNEES = frozenset(
    {
        "statut",
        "date",
        "decideurs",
        "contexte",
        "ce qui a change",
        "portee",
        "source metier",
    }
)

# Les 26 libellés de relation réellement employés, ramenés à six sens.
# La clé est le libellé sans accent et en minuscules ; la valeur, (type, sens).
# ⚠️ `Prolongé par` et `Complété et partiellement révisé par` sont des arêtes **entrantes** :
# l'ADR y désigne ce qui agit **sur lui**, pas ce sur quoi il agit. Les traiter comme sortantes
# inverserait la chronologie du graphe d'amendement.
_RELATIONS: dict[str, tuple[TypeLien, Sens]] = {
    "amende": (TypeLien.AMENDE, Sens.SORTANT),
    "revise": (TypeLien.AMENDE, Sens.SORTANT),
    "precise": (TypeLien.AMENDE, Sens.SORTANT),
    "raffine": (TypeLien.AMENDE, Sens.SORTANT),
    "resorbe": (TypeLien.AMENDE, Sens.SORTANT),
    "complete / amende": (TypeLien.AMENDE, Sens.SORTANT),
    "precise / anticipe": (TypeLien.AMENDE, Sens.SORTANT),
    "complete et partiellement revise par": (TypeLien.AMENDE, Sens.ENTRANT),
    "remplace": (TypeLien.REMPLACE, Sens.SORTANT),
    "renverse": (TypeLien.REMPLACE, Sens.SORTANT),
    "complete": (TypeLien.COMPLETE, Sens.SORTANT),
    "prolonge": (TypeLien.COMPLETE, Sens.SORTANT),
    "etend": (TypeLien.COMPLETE, Sens.SORTANT),
    "prepare": (TypeLien.COMPLETE, Sens.SORTANT),
    "suit": (TypeLien.COMPLETE, Sens.SORTANT),
    "prolonge par": (TypeLien.COMPLETE, Sens.ENTRANT),
    "s'appuie sur": (TypeLien.SOCLE, Sens.SORTANT),
    "lie": (TypeLien.VOISIN, Sens.SYMETRIQUE),
    "lies": (TypeLien.VOISIN, Sens.SYMETRIQUE),
    "voisin": (TypeLien.VOISIN, Sens.SYMETRIQUE),
    "voisins": (TypeLien.VOISIN, Sens.SYMETRIQUE),
    "s'articule avec": (TypeLien.VOISIN, Sens.SYMETRIQUE),
    "refs": (TypeLien.VOISIN, Sens.SYMETRIQUE),
    "us": (TypeLien.US, Sens.SORTANT),
    "introduit par": (TypeLien.US, Sens.SORTANT),
    "porte dans le code par": (TypeLien.CODE, Sens.SORTANT),
}


def sans_accent(texte: str) -> str:
    """Retire les diacritiques — pour comparer des libellés, jamais pour afficher.

    Passe par la catégorie Unicode `Mn` (*mark, nonspacing*) plutôt que par une plage de
    caractères écrite en dur : une plage littérale dépend de l'encodage du fichier source.
    """
    return "".join(
        c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn"
    )


def cle(libelle: str) -> str:
    """La forme canonique d'un libellé d'en-tête : sans accent, minuscule, espaces resserrés."""
    return re.sub(r"\s+", " ", sans_accent(libelle).lower()).strip()


def est_metadonnee(libelle: str) -> bool:
    return cle(libelle) in _METADONNEES


def relation(libelle: str, *, fichier: str) -> tuple[TypeLien, Sens]:
    """Traduit un libellé d'en-tête en (type, sens).

    Lève si le libellé est inconnu : c'est le garde-fou central de l'atlas. Le message nomme le
    fichier fautif et la ligne exacte à ajouter, pour que la correction soit un copier-coller —
    un message approximatif ici, et quelqu'un finira par désactiver le contrôle.
    """
    canonique = cle(libelle)
    connue = _RELATIONS.get(canonique)
    if connue is not None:
        return connue
    raise AtlasSourceInvalide(
        f"{fichier} : libellé de relation inconnu « {libelle} ».\n"
        f"Le vocabulaire des ADR est ouvert : décide de son sens et ajoute-le à "
        f"`backend/atlas/normalisation.py`, table `_RELATIONS` :\n"
        f'    "{canonique}": (TypeLien.<AMENDE|REMPLACE|COMPLETE|SOCLE|VOISIN|US>, '
        f"Sens.<SORTANT|ENTRANT|SYMETRIQUE>),\n"
        f"S'il ne décrit aucune relation, ajoute-le plutôt à `_METADONNEES`."
    )


_ADR_CITE = re.compile(r"ADR-(\d{4})")


def normaliser_statut(brut: str, *, fichier: str) -> tuple[Statut, str]:
    """Rend (statut normalisé, identifiant du remplaçant ou chaîne vide).

    Le champ est écrit à la main : on normalise pour trier, l'appelant garde le texte brut.
    """
    # ⚠️ Les deux ordres de test sont des pièges de **polarité opposée** : « remplac » d'abord
    # classe un « Accepté (remplace en partie …) » comme obsolète, « accepté » d'abord fait passer
    # une décision morte pour vivante. Aucune des deux formes n'existe au registre : on **refuse
    # de deviner**.
    canonique = cle(brut)
    accepte = canonique.startswith("accepte")
    remplace = "remplac" in canonique
    if accepte and remplace:
        raise AtlasSourceInvalide(
            f"{fichier} : statut ambigu « {brut} » — il dit à la fois « accepté » et "
            f"« remplacé ». Tranche dans l'ADR : un statut qui se contredit ne peut être ni "
            f"affiché ni filtré honnêtement."
        )
    if accepte:
        return Statut.ACCEPTE, ""
    if remplace:
        cite = _ADR_CITE.search(brut)
        return Statut.REMPLACE, cite.group(1) if cite else ""
    raise AtlasSourceInvalide(
        f"{fichier} : statut d'ADR non reconnu « {brut} ». "
        f"Attendu « Accepté » ou « Remplacé par [ADR-nnnn] »."
    )
