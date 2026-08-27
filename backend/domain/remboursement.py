"""Registre des **remboursements** — un instantané, jamais des liens vers ce qui a disparu.

Fige le nom de l'archer, le libellé du créneau détruit et le montant encaissé ; seul `tournoi_id`
reste une FK. Un enregistrement comptable ne se répare pas en suivant un lien vers une ligne partie.

⚠️ **Les deux transitions sont TERMINALES** (`remboursé`, `reporté`) : le refus de re-traiter est
porté par le **service** (409), l'entité ne portant que l'invariant de construction.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, replace
from enum import Enum

from domain.erreurs import RemboursementMontantInvalide
from domain.tournoi import TournoiId

RemboursementId = int
"""Identifiant technique d'un remboursement, attribué par la persistance."""


class MotifRemboursement(str, Enum):
    """Pourquoi une somme encaissée est devenue un remboursement à traiter.

    `(str, Enum)` : la valeur est un slug stable, stocké tel quel en base (comme `ActionAuditee`).
    Les deux motifs sont les **deux déclencheurs** du CA — l'inscription payée détruite l'a été soit
    par la suppression de son **départ** (ADR-0018), soit par une **désinscription** individuelle.
    """

    DEPART_SUPPRIME = "depart_supprime"
    DESINSCRIPTION = "desinscription"


class StatutRemboursement(str, Enum):
    """État d'un remboursement dans son cycle de vie (à_rembourser → remboursé | reporté)."""

    A_REMBOURSER = "a_rembourser"
    REMBOURSE = "rembourse"
    REPORTE = "reporte"


@dataclass(frozen=True)
class Remboursement:
    """Une somme encaissée à rendre. Immuable (règle 4) ; `id` `None` tant que non persistée.

    Les champs `archer_prenom` / `archer_nom` / `creneau` sont des **instantanés textuels** (pas des
    FK) : ils décrivent ce qui a disparu et doivent lui survivre. `montant_centimes` fige le tarif
    encaissé. `cree_le` date la naissance du poste (port `Horloge`) ; `traite_le` reste `None` tant
    que le remboursement est `à_rembourser`, et fige l'instant du traitement sinon.
    """

    tournoi_id: TournoiId
    archer_prenom: str
    archer_nom: str
    creneau: str
    montant_centimes: int
    motif: MotifRemboursement
    cree_le: datetime.datetime
    statut: StatutRemboursement = StatutRemboursement.A_REMBOURSER
    traite_le: datetime.datetime | None = None
    id: RemboursementId | None = None

    @staticmethod
    def creer(
        tournoi_id: TournoiId,
        *,
        archer_prenom: str,
        archer_nom: str,
        creneau: str,
        montant_centimes: int,
        motif: MotifRemboursement,
        cree_le: datetime.datetime,
    ) -> Remboursement:
        """Crée un remboursement **à traiter** (statut `à_rembourser`, `traite_le` vide).

        Lève `RemboursementMontantInvalide` si `montant_centimes <= 0` : un remboursement porte une
        somme réellement encaissée (le site appelant ne construit un remboursement que pour une
        inscription payée d'un créneau **tarifé** — mais l'entité défend l'invariant elle-même).
        """
        if montant_centimes <= 0:
            raise RemboursementMontantInvalide(
                "Le montant d'un remboursement doit être strictement positif "
                f"(reçu {montant_centimes} centimes)."
            )
        return Remboursement(
            tournoi_id=tournoi_id,
            archer_prenom=archer_prenom,
            archer_nom=archer_nom,
            creneau=creneau,
            montant_centimes=montant_centimes,
            motif=motif,
            cree_le=cree_le,
            statut=StatutRemboursement.A_REMBOURSER,
            traite_le=None,
        )

    def marquer_rembourse(self, traite_le: datetime.datetime) -> Remboursement:
        """Renvoie une copie **remboursée** (l'argent a été rendu), datée `traite_le`.

        Transformation pure : le refus de re-traiter un remboursement déjà traité est un conflit
        d'**état** porté par le service (`RemboursementDejaTraite`, 409), pas un invariant de
        construction — l'entité ne connaît pas l'intention de l'appelant, seulement l'effet voulu.
        """
        return replace(self, statut=StatutRemboursement.REMBOURSE, traite_le=traite_le)

    def marquer_reporte(self, traite_le: datetime.datetime) -> Remboursement:
        """Renvoie une copie **reportée** (réaffectée à un autre créneau), datée `traite_le`.

        « Reporté » consigne une **intention** : E08US005 ne ré-inscrit pas automatiquement l'archer
        ailleurs (ce serait re-tarifer, gérer l'écart — capacité à part). L'admin marque « reporté »
        puis, s'il le souhaite, ré-inscrit à la main. Transformation pure, comme
        `marquer_rembourse`.
        """
        return replace(self, statut=StatutRemboursement.REPORTE, traite_le=traite_le)
