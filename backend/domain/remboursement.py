"""Agrégat `Remboursement` — une somme encaissée à rendre (E08US005, ADR-0057).

Jusqu'ici, le paiement est un **simple booléen** `paye` porté par l'`Inscription` : rien dans le
modèle ne représente un **mouvement d'argent**. Or quand une inscription **payée** disparaît — un
départ à inscriptions supprimé (ADR-0018) ou une désinscription — sa ligne est **détruite** : la
somme encaissée s'évanouit avec elle. Le `Remboursement` est la trace durable qui **survit** à cette
disparition : un poste à part, figé au moment de l'effacement, que l'admin traitera (« remboursé »
ou « reporté »).

Comme l'`EntreeAudit` fige le **nom** de son auteur (pas une FK — la trace doit survivre à la
suppression du scoreur, E10US003), ce registre fige un **instantané** de ce à quoi il se rapporte :
le **nom** de l'archer et le **libellé** du créneau détruit, plus le **montant** encaissé (le tarif
du créneau au moment de l'effacement). Aucune FK vers l'inscription (elle n'existe plus) ni vers le
départ (souvent détruit lui aussi) : un enregistrement comptable ne se répare pas en suivant un lien
vers une ligne partie. Seul `tournoi_id` reste une FK — le remboursement appartient à son tournoi.

Cycle de vie **à trois états** (le CA offre deux issues à un `à_rembourser`) :

    à_rembourser ──▶ remboursé   (l'argent a été rendu)
                 └─▶ reporté     (réaffecté à un autre créneau — simple **intention consignée** ici,
                                  la ré-inscription reste un geste manuel, hors périmètre E08US005)

Les deux transitions sont **terminales** : un remboursement traité ne se re-traite pas (le refus de
re-traiter est porté par le **service**, `RemboursementDejaTraite`, 409 — un conflit d'**état**, à
l'image des transitions de statut de tournoi). L'entité, elle, ne porte que l'invariant de
**construction** (`montant_centimes > 0` : un remboursement de 0 € n'a pas de raison d'exister — un
créneau gratuit marqué payé n'encaisse rien).

Pur et synchrone (règle 1) : aucun import de framework ni d'autre couche.
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
