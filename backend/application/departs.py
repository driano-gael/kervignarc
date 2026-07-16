"""Service applicatif Departs — orchestre les créneaux d'un tournoi (E02US004, ADR-0017).

Use cases de configuration des **départs** (créneaux horaires) d'un tournoi : créer, lister, éditer
(tarif/horaire), supprimer. Il ne connaît ni HTTP, ni SQL, ni la file d'écriture (sérialisation
assurée en amont, côté API) ; il reste synchrone et pur d'infrastructure.

Il arbitre l'**existence** — du tournoi (`TournoiIntrouvable`) et du départ dans ce tournoi
(`DepartIntrouvable`) — et **attribue le numéro** d'un nouveau créneau : le domaine ne voit qu'un
départ à la fois, il ne peut donc pas savoir quel numéro est libre. Le numéro est le plus grand
existant + 1 (1 pour le premier) ; une suppression laisse un trou, jamais réattribué — un numéro est
un repère stable, pas un rang recalculé.

Le lien archer↔départ (inscription) et le suivi `payé` sont E02US009 : ce service ne gère que la
**définition** des créneaux.
"""

from __future__ import annotations

from application.erreurs import DepartIntrouvable, TournoiIntrouvable
from domain.depart import Depart, DepartId
from domain.ports import DepartRepository, TournoiRepository
from domain.tournoi import TournoiId


class ServiceDeparts:
    """Cas d'usage des départs d'un tournoi : créer, lister, éditer, supprimer."""

    def __init__(
        self,
        depart_repository: DepartRepository,
        tournoi_repository: TournoiRepository,
    ) -> None:
        self._departs = depart_repository
        self._tournois = tournoi_repository

    def creer(
        self,
        tournoi_id: TournoiId,
        tarif_centimes: int,
        horaire: str | None = None,
    ) -> Depart:
        """Crée et persiste un départ dans un tournoi, avec un numéro attribué automatiquement.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas, `DomainError` si le tarif est hors
        plage. Le numéro est le plus grand existant + 1 (1 pour le premier créneau).

        Lecture (`par_tournoi`) puis écriture (`ajouter`) tiennent dans **une seule commande** en
        file (règle 7, ADR-0005) : aucune création concurrente ne peut se glisser entre le calcul du
        numéro et l'insertion. La contrainte `UNIQUE(tournoi_id, numero)` reste le garde-fou ultime.
        """
        self._verifier_tournoi(tournoi_id)
        existants = self._departs.par_tournoi(tournoi_id)
        numero = existants[-1].numero + 1 if existants else 1
        depart = Depart.creer(tournoi_id, numero, tarif_centimes, horaire)
        return self._departs.ajouter(depart)

    def lister(self, tournoi_id: TournoiId) -> list[Depart]:
        """Renvoie les départs d'un tournoi, triés par numéro (liste éventuellement vide).

        Lève `TournoiIntrouvable` si le tournoi n'existe pas.
        """
        self._verifier_tournoi(tournoi_id)
        return self._departs.par_tournoi(tournoi_id)

    def modifier(
        self,
        tournoi_id: TournoiId,
        depart_id: DepartId,
        tarif_centimes: int,
        horaire: str | None = None,
    ) -> Depart:
        """Édite le tarif et l'horaire d'un départ (le numéro est fixe).

        Lève `DepartIntrouvable` si le départ n'existe pas dans ce tournoi, `DomainError` si le
        tarif est hors plage.
        """
        depart = self._depart_du_tournoi(tournoi_id, depart_id)
        return self._departs.enregistrer(depart.modifier(tarif_centimes, horaire))

    def supprimer(self, tournoi_id: TournoiId, depart_id: DepartId) -> None:
        """Supprime un départ d'un tournoi.

        Lève `DepartIntrouvable` si le départ n'existe pas dans ce tournoi. La suppression est libre
        tant qu'aucune inscription n'existe (E02US009 ajoutera le garde-fou « départ avec archers
        inscrits », patron `ClubReference`).
        """
        depart = self._depart_du_tournoi(tournoi_id, depart_id)
        assert depart.id is not None, "Un départ relu est persisté."
        self._departs.supprimer(depart.id)

    def _verifier_tournoi(self, tournoi_id: TournoiId) -> None:
        """Lève `TournoiIntrouvable` si le tournoi n'existe pas."""
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")

    def _depart_du_tournoi(self, tournoi_id: TournoiId, depart_id: DepartId) -> Depart:
        """Relit un départ et vérifie qu'il appartient au tournoi ; sinon `DepartIntrouvable`."""
        depart = self._departs.par_id(depart_id)
        if depart is None or depart.tournoi_id != tournoi_id:
            raise DepartIntrouvable(
                f"Aucun départ d'identifiant {depart_id} dans le tournoi {tournoi_id}."
            )
        return depart
