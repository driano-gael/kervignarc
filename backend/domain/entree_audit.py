"""Trace d'audit — **qui / quand / avant-après** (`D-04`), en **ajout seul** et immuable.

⚠️ **L'`auteur` est le NOM, jamais une clé étrangère** : la trace d'une validation doit survivre à
la **suppression** du scoreur qui l'a faite. Stocker son `id` casserait à sa suppression ; on fige
donc le nom au moment de l'acte — même parti que le registre des remboursements.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum

from domain.erreurs import AuteurAuditInvalide, HorodatageAuditInvalide, ObjetAuditInvalide
from domain.tournoi import TournoiId

EntreeAuditId = int
"""Identifiant technique d'une entrée d'audit, attribué par la persistance."""


class ActionAuditee(str, Enum):
    """Nature de l'acte sensible tracé — l'ensemble **fermé** des actions du CA E10US005.

    `(str, Enum)` : la valeur est un slug stable, stocké tel quel en base (comme `StatutTournoi`).
    Producteurs : `VALIDATION`/`CORRECTION_SCORE` (E04US002), `FORFAIT` (ADR-0050), `REPLACEMENT`
    (ADR-0040, régénération massive quand des scores existent), `PAIEMENT` (E08US002), `LANCEMENT`
    (ADR-0056), `REMBOURSEMENT` (ADR-0057 — le *traitement*, pas la création du poste : la ligne du
    registre est déjà sa trace datée, l'audit ne suit que l'acte **humain**).
    """

    VALIDATION = "validation"
    CORRECTION_SCORE = "correction_score"
    FORFAIT = "forfait"
    REPLACEMENT = "replacement"
    PAIEMENT = "paiement"
    LANCEMENT = "lancement"
    REMBOURSEMENT = "remboursement"


@dataclass(frozen=True)
class EntreeAudit:
    """Une entrée du journal d'audit. `id` vaut `None` tant qu'elle n'est pas persistée.

    `avant`/`apres` sont **optionnels** : une **validation** est un évènement sans état antérieur,
    une **correction** les renseigne (ancienne et nouvelle valeur). Ce sont des représentations
    **textuelles** libres, laissées au producteur — le socle ne présume pas de leur forme.
    """

    tournoi_id: TournoiId
    action: ActionAuditee
    auteur: str
    horodatage: datetime.datetime
    objet: str
    avant: str | None = None
    apres: str | None = None
    id: EntreeAuditId | None = None

    @staticmethod
    def creer(
        tournoi_id: TournoiId,
        action: ActionAuditee,
        auteur: str,
        horodatage: datetime.datetime,
        objet: str,
        avant: str | None = None,
        apres: str | None = None,
    ) -> EntreeAudit:
        """Construit une entrée valide.

        `auteur` et `objet` sont normalisés et non vides (`AuteurAuditInvalide`,
        `ObjetAuditInvalide`) — sans eux la trace ne dit ni *qui* ni *sur quoi*. ⚠️ `horodatage`
        est fourni par l'appelant via le port `Horloge` (le domaine reste pur) et doit être **UTC**
        *aware* : la persistance réattache UTC en aveugle à la relecture, ce qui n'est fidèle que
        si l'écrit l'était déjà. `avant`/`apres` restent **verbatim**.
        """
        return EntreeAudit(
            tournoi_id=tournoi_id,
            action=action,
            auteur=_auteur_valide(auteur),
            horodatage=_horodatage_valide(horodatage),
            objet=_objet_valide(objet),
            avant=avant,
            apres=apres,
        )


def _auteur_valide(auteur: str) -> str:
    """Normalise l'auteur ; lève `AuteurAuditInvalide` s'il est vide."""
    auteur_normalise = auteur.strip()
    if not auteur_normalise:
        raise AuteurAuditInvalide("L'auteur d'une entrée d'audit ne peut pas être vide.")
    return auteur_normalise


def _objet_valide(objet: str) -> str:
    """Normalise l'objet ; lève `ObjetAuditInvalide` s'il est vide."""
    objet_normalise = objet.strip()
    if not objet_normalise:
        raise ObjetAuditInvalide("L'objet d'une entrée d'audit ne peut pas être vide.")
    return objet_normalise


def _horodatage_valide(horodatage: datetime.datetime) -> datetime.datetime:
    """Vérifie que l'horodatage est un instant UTC *aware* ; lève `HorodatageAuditInvalide` sinon.

    `utcoffset()` vaut `None` pour un datetime **naïf** et un `timedelta` non nul pour un fuseau
    **non-UTC** : un unique test `!= timedelta(0)` couvre les deux cas fautifs. On ne convertit pas
    en UTC en douce — un horodatage mal fuseauté est un **bug de l'appelant** (une horloge non
    conforme au contrat du port `Horloge`), pas une entrée à corriger silencieusement.
    """
    if horodatage.utcoffset() != datetime.timedelta(0):
        raise HorodatageAuditInvalide(
            "L'horodatage d'une entrée d'audit doit être un instant UTC (datetime aware)."
        )
    return horodatage
