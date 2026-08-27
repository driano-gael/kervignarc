"""Contenus imprimables — de simples valeurs immuables : liste de placement, liste club & paiement.

⚠️ **Le `tri` n'est porté ici que pour l'imprimer en en-tête** : c'est le **service** qui trie, et
qui borne la liste sur un départ. Montants en **centimes entiers** — le formatage en euros est un
détail de rendu.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TriPlacement(Enum):
    """Ordre d'impression de la liste de placement (CA « triable par cible ou par nom »)."""

    CIBLE = "cible"  # ordre physique de la salle : départ, cible, position
    NOM = "nom"  # ordre alphabétique : nom puis prénom


@dataclass(frozen=True)
class LignePlacement:
    """Un archer placé, tel qu'il figure sur la liste de placement (une ligne = une affectation).

    Un archer inscrit sur plusieurs départs et placé sur chacun apparaît sur **plusieurs** lignes
    (une par départ) : la liste décrit des postes physiques, pas des personnes.
    """

    nom: str
    prenom: str
    categorie: str
    depart_numero: int
    cible_index: int  # rang de la cible dans la salle (1-based)
    position: str  # lettre de la position sur la cible ("A".."D")


@dataclass(frozen=True)
class ListePlacement:
    """Le document « liste de placement » : en-tête + une ligne par archer placé, déjà ordonnée.

    `depart_numero` vaut `None` quand la liste couvre **tout le tournoi**, ou le numéro du départ
    quand elle est filtrée sur un seul (affiché en en-tête). `tri` indique l'ordre choisi (pour
    l'imprimer) ; les `lignes` sont déjà dans cet ordre — le rendu ne trie pas.
    """

    tournoi: str
    depart_numero: int | None
    tri: TriPlacement
    lignes: tuple[LignePlacement, ...]


class StatutPaiement(Enum):
    """Statut de règlement d'un archer sur la liste club & paiement (CA « payé/non »)."""

    RIEN = "—"  # rien à régler (aucune inscription, dû nul)
    PAYE = "payé"  # tout est réglé (reste nul avec un dû non nul)
    DU = "dû"  # il reste à payer (reste non nul)


@dataclass(frozen=True)
class LignePaiementImpression:
    """Un archer sur la liste club & paiement : ses départs, son dû et son statut de règlement.

    `departs` porte les **numéros** des départs inscrits (triés), d'où découlent l'affichage « n°
    départ » et « nb départs » du CA. `du_centimes`/`paye_centimes` (centimes entiers, cf.
    `domain.paiement`) donnent le reste et le statut par dérivation — pas de champ redondant à
    désynchroniser (même parti que `RecapPaiement.reste_centimes`).
    """

    nom: str
    prenom: str
    departs: tuple[int, ...]
    du_centimes: int
    paye_centimes: int

    @property
    def nb_departs(self) -> int:
        """Nombre de départs inscrits (CA « nb départs »)."""
        return len(self.departs)

    @property
    def reste_centimes(self) -> int:
        """Reste à payer = dû - payé (jamais négatif : le payé n'agrège que des tarifs dus)."""
        return self.du_centimes - self.paye_centimes

    @property
    def statut(self) -> StatutPaiement:
        """« payé/non » (CA), avec un 3ᵉ cas honnête : rien à régler quand le dû est nul.

        Un archer sans inscription (dû nul) n'est ni « payé » ni « en retard » — l'afficher « payé »
        serait trompeur. `PAYE` n'a de sens que face à un dû réel entièrement soldé.
        """
        if self.du_centimes == 0:
            return StatutPaiement.RIEN
        return StatutPaiement.PAYE if self.reste_centimes == 0 else StatutPaiement.DU


@dataclass(frozen=True)
class GroupePaiementClub:
    """Un club (ou le bucket « Sans club », ADR-0014) : ses archers et ses totaux de paiement.

    `total_du_centimes`/`total_paye_centimes` sont les totaux du club (CA « totaux par club ») ;
    ils proviennent du récapitulatif agrégé (`ServicePaiements`), pas d'une re-somme locale.
    """

    club: str
    lignes: tuple[LignePaiementImpression, ...]
    total_du_centimes: int
    total_paye_centimes: int


@dataclass(frozen=True)
class ListeClubPaiement:
    """Le document « liste club & paiement » : en-tête + un groupe par club, chacun avec ses totaux.

    Les groupes sont déjà ordonnés (clubs par nom, « Sans club » en dernier) par le service, qui
    reprend l'ordre de `ServicePaiements.recap_par_club` — le rendu ne réordonne pas.
    """

    tournoi: str
    groupes: tuple[GroupePaiementClub, ...]
