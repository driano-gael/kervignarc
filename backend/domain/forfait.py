"""Forfait — **daté, attribué, réversible**, et scopé à une **phase** (ADR-0050).

⚠️ **Le scope par phase est la clé** : un abandon en qualification relègue l'archer du classement de
qualification ; un forfait en duels n'y touche **pas** — il fait passer l'adversaire. Sans lui, un
abandon en duels reléguerait le rang d'un archer qui avait pourtant qualifié. `nature` porte l'effet
sur le classement : **abandon** = relégué en fin, **disqualification** = sorti du classement, les
flèches restant conservées.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum

from domain.archer import ArcherId
from domain.erreurs import DeclarantForfaitInvalide, HorodatageForfaitInvalide
from domain.phase import PhaseId
from domain.tournoi import TournoiId

ForfaitId = int
"""Identifiant technique d'un forfait, attribué par la persistance."""


class NatureForfait(str, Enum):
    """La nature d'un forfait — l'ensemble **fermé** des deux issues du CA E04US015.

    `(str, Enum)` : la valeur est un slug stable, stocké tel quel en base (comme `StatutTournoi`).
    L'écart entre les deux n'est **pas** l'audit ni la préservation des flèches (identiques) mais
    l'**effet sur le classement** (cf. `Forfait.exclu_du_classement`).
    """

    ABANDON = "abandon"
    DISQUALIFICATION = "disqualification"


@dataclass(frozen=True)
class Forfait:
    """Un forfait déclaré : qui, quand, sur quel archer, dans quelle phase, pourquoi (optionnel).

    `id` vaut `None` tant qu'il n'est pas persisté. `motif` est **facultatif** : un abandon n'a pas
    toujours de raison consignée ; une DSQ en a d'ordinaire une, mais on ne l'**exige** pas (le
    domaine ne présume pas du process du jury). Un forfait par `(tournoi, archer, phase)` : annuler
    = **supprimer** l'enregistrement (les flèches, elles, n'ont jamais été touchées), pas un drapeau
    `actif` — la réversibilité est une **suppression de la déclaration**, pas un troisième état.
    """

    tournoi_id: TournoiId
    archer_id: ArcherId
    phase_id: PhaseId
    nature: NatureForfait
    declare_par: str
    declare_le: datetime.datetime
    motif: str | None = None
    id: ForfaitId | None = None

    @staticmethod
    def creer(
        tournoi_id: TournoiId,
        archer_id: ArcherId,
        phase_id: PhaseId,
        nature: NatureForfait,
        declare_par: str,
        declare_le: datetime.datetime,
        motif: str | None = None,
    ) -> Forfait:
        """Construit un forfait valide.

        `declare_par` est normalisé (espaces de bord retirés) et ne peut être vide
        (`DeclarantForfaitInvalide`) — sans lui, le forfait ne dit pas *qui* l'a prononcé, comme
        l'audit exige un auteur. `declare_le` (« quand ») doit être un instant **UTC** *aware*
        (`HorodatageForfaitInvalide` sinon), même contrat que `EntreeAudit` : la persistance
        réattache UTC en aveugle à la relecture, ce qui n'est fidèle que si l'écrit était déjà UTC.
        `motif` est normalisé : un motif vide (après strip) équivaut à « non renseigné » (`None`).
        """
        return Forfait(
            tournoi_id=tournoi_id,
            archer_id=archer_id,
            phase_id=phase_id,
            nature=nature,
            declare_par=_declarant_valide(declare_par),
            declare_le=_horodatage_valide(declare_le),
            motif=_motif_normalise(motif),
        )

    @property
    def exclu_du_classement(self) -> bool:
        """`True` si ce forfait **sort** l'archer du classement (DSQ) ; `False` s'il l'y **relègue**
        (abandon). Seul écart d'effet entre les deux natures (Q2/Q3 du cadrage E04US015)."""
        return self.nature is NatureForfait.DISQUALIFICATION


def _declarant_valide(declare_par: str) -> str:
    """Normalise le déclarant ; lève `DeclarantForfaitInvalide` s'il est vide."""
    normalise = declare_par.strip()
    if not normalise:
        raise DeclarantForfaitInvalide("Le déclarant d'un forfait ne peut pas être vide.")
    return normalise


def _motif_normalise(motif: str | None) -> str | None:
    """Réduit un motif à `None` s'il est vide (après normalisation) ; le conserve sinon."""
    if motif is None:
        return None
    return motif.strip() or None


def _horodatage_valide(horodatage: datetime.datetime) -> datetime.datetime:
    """Vérifie que l'horodatage est un instant UTC *aware* ; lève `HorodatageForfaitInvalide` sinon.

    Même raison que l'audit (`EntreeAudit`) : un `datetime` **naïf** ou **aware non-UTC** serait
    stocké puis relu comme de l'UTC, faisant **mentir** la date du forfait en silence. `utcoffset()`
    vaut `None` (naïf) ou un `timedelta` non nul (fuseau non-UTC) : un unique test `!= timedelta(0)`
    couvre les deux cas fautifs. On ne convertit pas en douce — c'est un bug de l'appelant.
    """
    if horodatage.utcoffset() != datetime.timedelta(0):
        raise HorodatageForfaitInvalide(
            "L'horodatage d'un forfait doit être un instant UTC (datetime aware)."
        )
    return horodatage
