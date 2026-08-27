"""Listes imprimables — placement, et club & paiement. Ni HTTP, ni SQL, ni ReportLab ici.

⚠️ **Deux câblages volontairement différents** : le placement se reconstitue par **ports seuls**
(2ᵉ occurrence assumée de la chaîne de la feuille de marque), tandis que la vue club & paiement
**réutilise `ServicePaiements.recap_par_club`** — dupliquer cette règle non triviale (agrégation,
bucket « Sans club », tri) la ferait diverger d'E08US002.
"""

from __future__ import annotations

from typing import Protocol

from application.erreurs import DepartIntrouvable, TournoiIntrouvable
from application.paiements import RecapClub
from domain.archer import ArcherId
from domain.depart import Depart, DepartId
from domain.listes_impression import (
    GroupePaiementClub,
    LignePaiementImpression,
    LignePlacement,
    ListeClubPaiement,
    ListePlacement,
    TriPlacement,
)
from domain.placement import Affectation
from domain.ports import (
    ArcherRepository,
    CategorieRepository,
    DepartRepository,
    GenerateurListesImpression,
    InscriptionRepository,
    PlacementRepository,
    TournoiRepository,
)
from domain.tournoi import TournoiId


class LecteurRecapClub(Protocol):
    """Port étroit : lire le récap de paiement **par club** (réalisé par `ServicePaiements`).

    La liste club & paiement ne dépend pas de tout `ServicePaiements` (marquages compris) : juste de
    son agrégation dû/payé/reste par club, avec bucket « Sans club » (ADR-0014). Même discipline de
    ségrégation d'interface que `LecteurPaiements` (`application.completude`) : un faux lecteur
    suffit en test, et le service n'écrit aucun paiement.
    """

    def recap_par_club(self, tournoi_id: TournoiId) -> list[RecapClub]:
        """Totaux de paiement par club, avec le détail des archers ; lève `TournoiIntrouvable`."""
        ...


class ServiceListesImpression:
    """Cas d'usage : composer et rendre les listes imprimables (placement, club & paiement)."""

    def __init__(
        self,
        tournois: TournoiRepository,
        departs: DepartRepository,
        placements: PlacementRepository,
        inscriptions: InscriptionRepository,
        archers: ArcherRepository,
        categories: CategorieRepository,
        paiements: LecteurRecapClub,
        generateur: GenerateurListesImpression,
    ) -> None:
        self._tournois = tournois
        self._departs = departs
        self._placements = placements
        self._inscriptions = inscriptions
        self._archers = archers
        self._categories = categories
        self._paiements = paiements
        self._generateur = generateur

    # --- Liste de placement ------------------------------------------------------------------

    def generer_placement(
        self,
        tournoi_id: TournoiId,
        depart_id: DepartId | None = None,
        tri: TriPlacement = TriPlacement.CIBLE,
    ) -> bytes:
        """Rend en PDF la liste de placement du tournoi (ou d'un seul départ si `depart_id`).

        Lève `TournoiIntrouvable` si le tournoi n'existe pas, `DepartIntrouvable` si `depart_id` ne
        désigne pas un départ **de ce tournoi** (même contrat que la feuille de marque). Seuls les
        archers **placés** figurent (la réserve ne tire pas) ; l'ordre suit `tri` (par cible =
        départ/cible/position, ordre physique ; par nom = nom/prénom, casse repliée).
        """
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")

        departs = self._departs.par_tournoi(tournoi_id)
        depart_numero_entete: int | None = None
        if depart_id is not None:
            depart = next((d for d in departs if d.id == depart_id), None)
            if depart is None:
                raise DepartIntrouvable(
                    f"Aucun départ d'identifiant {depart_id} dans le tournoi {tournoi_id}."
                )
            departs = [depart]
            depart_numero_entete = depart.numero

        lignes = [
            ligne
            for depart in departs
            for affectation in self._placements.par_depart(_depart_id(depart))
            if (ligne := self._ligne_placement(affectation, depart.numero)) is not None
        ]
        if tri is TriPlacement.NOM:
            # Par nom : nom puis prénom (casse repliée), départagé ensuite par départ/cible/position
            # pour un ordre déterministe (deux homonymes sur des postes distincts restent stables).
            lignes.sort(
                key=lambda ligne: (
                    ligne.nom.casefold(),
                    ligne.prenom.casefold(),
                    ligne.depart_numero,
                    ligne.cible_index,
                    ligne.position,
                )
            )
        else:
            # Par cible : ordre physique de la salle — départ, puis cible, puis position.
            lignes.sort(key=lambda ligne: (ligne.depart_numero, ligne.cible_index, ligne.position))

        liste = ListePlacement(
            tournoi=tournoi.nom,
            depart_numero=depart_numero_entete,
            tri=tri,
            lignes=tuple(lignes),
        )
        return self._generateur.placement(liste)

    def _ligne_placement(
        self, affectation: Affectation, depart_numero: int
    ) -> LignePlacement | None:
        """Reconstitue la ligne d'un archer placé, ou `None` si la chaîne de jointure est rompue.

        `None` ne devrait pas arriver pour un archer **placé** : garde défensive contre une
        incohérence de données, pas un cas nominal (même parti que `ServiceFeuilleDeMarque._ligne`).
        Le libellé de catégorie absent retombe sur `""` pour ne jamais perdre un archer réellement
        sur une cible.
        """
        inscription = self._inscriptions.par_id(affectation.inscription_id)
        if inscription is None:
            return None
        archer = self._archers.par_id(inscription.archer_id)
        if archer is None:
            return None
        categorie = self._categories.par_id(archer.categorie_id)
        return LignePlacement(
            nom=archer.nom,
            prenom=archer.prenom,
            categorie=categorie.libelle if categorie is not None else "",
            depart_numero=depart_numero,
            cible_index=affectation.cible_index,
            position=affectation.position,
        )

    # --- Liste club & paiement ---------------------------------------------------------------

    def generer_club_paiement(self, tournoi_id: TournoiId) -> bytes:
        """Rend en PDF la liste club & paiement du tournoi (un bloc par club, avec totaux).

        Lève `TournoiIntrouvable` (via `recap_par_club`) si le tournoi n'existe pas. La vue porte
        sur **tout le tournoi** : un dû d'archer additionne ses départs, un filtre par départ n'y a
        pas de sens (cf. Notes de l'US) — au contraire du placement, physique et par départ.
        """
        recaps = self._paiements.recap_par_club(tournoi_id)
        tournoi = self._tournois.par_id(tournoi_id)
        assert tournoi is not None, "recap_par_club a déjà validé l'existence du tournoi."

        numeros = {
            depart.id: depart.numero
            for depart in self._departs.par_tournoi(tournoi_id)
            if depart.id is not None
        }
        groupes = [
            GroupePaiementClub(
                club=recap_club.nom,
                lignes=tuple(
                    LignePaiementImpression(
                        nom=ligne.nom,
                        prenom=ligne.prenom,
                        departs=self._departs_de_l_archer(ligne.archer_id, numeros),
                        du_centimes=ligne.recap.du_centimes,
                        paye_centimes=ligne.recap.paye_centimes,
                    )
                    for ligne in recap_club.archers
                ),
                total_du_centimes=recap_club.recap.du_centimes,
                total_paye_centimes=recap_club.recap.paye_centimes,
            )
            for recap_club in recaps
        ]
        liste = ListeClubPaiement(tournoi=tournoi.nom, groupes=tuple(groupes))
        return self._generateur.club_paiement(liste)

    def _departs_de_l_archer(
        self, archer_id: ArcherId, numeros: dict[DepartId, int]
    ) -> tuple[int, ...]:
        """Numéros (triés) des départs inscrits par un archer, pour l'affichage n° / nb départs.

        Une inscription dont le créneau est absent de `numeros` (instantané périmé) est ignorée —
        même tolérance que `ServicePaiements._ligne`, dont on reprend la source d'inscriptions.
        """
        return tuple(
            sorted(
                numeros[inscription.depart_id]
                for inscription in self._inscriptions.par_archer(archer_id)
                if inscription.depart_id in numeros
            )
        )


def _depart_id(depart: Depart) -> DepartId:
    """Identifiant d'un départ relu (toujours persisté) — resserre le type pour `par_depart`."""
    assert depart.id is not None, "Un départ relu est persisté."
    return depart.id
