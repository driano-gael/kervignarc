"""Service applicatif Departs — orchestre les créneaux d'un tournoi (E02US004, ADR-0017).

Use cases de configuration des **départs** (créneaux horaires) d'un tournoi : créer, lister, éditer
(tarif/horaire), supprimer. Il ne connaît ni HTTP, ni SQL, ni la file d'écriture (sérialisation
assurée en amont, côté API) ; il reste synchrone et pur d'infrastructure.

Il arbitre l'**existence** — du tournoi (`TournoiIntrouvable`) et du départ dans ce tournoi
(`DepartIntrouvable`) — et **attribue le numéro** d'un nouveau créneau : le domaine ne voit qu'un
départ à la fois, il ne peut donc pas savoir quel numéro est libre. Le numéro est toujours **le plus
grand existant + 1** (1 pour le premier) — jamais un rang recalculé. Supprimer un créneau
**intermédiaire** laisse donc un trou définitif ; supprimer **le dernier** (le plus grand numéro)
libère son numéro, que la création suivante reprendra (le max a baissé). Les inscriptions et le
placement référencent l'`id` technique, pas le `numero`, donc cette réutilisation est sans effet.

Le lien archer↔départ (inscription) et le suivi `payé` sont E02US009 : ce service ne gère que la
**définition** des créneaux.
"""

from __future__ import annotations

from application.erreurs import (
    DepartAvecInscriptions,
    DepartIntrouvable,
    TournoiIntrouvable,
)
from domain.depart import Depart, DepartId
from domain.ports import DepartRepository, InscriptionRepository, TournoiRepository
from domain.tournoi import TournoiId


class ServiceDeparts:
    """Cas d'usage des départs d'un tournoi : créer, lister, éditer, supprimer."""

    def __init__(
        self,
        depart_repository: DepartRepository,
        tournoi_repository: TournoiRepository,
        inscription_repository: InscriptionRepository,
    ) -> None:
        self._departs = depart_repository
        self._tournois = tournoi_repository
        self._inscriptions = inscription_repository

    def creer(
        self,
        tournoi_id: TournoiId,
        tarif_centimes: int,
        horaire: str | None = None,
        quota: int | None = None,
    ) -> Depart:
        """Crée et persiste un départ dans un tournoi, avec un numéro attribué automatiquement.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas, `DomainError` si le tarif ou le quota
        sont hors plage. Le numéro est le plus grand existant + 1 (1 pour le premier créneau) ; le
        `quota` est facultatif (`None` = créneau sans plafond, E02US006).

        Lecture (`par_tournoi`) puis écriture (`ajouter`) tiennent dans **une seule commande** en
        file (règle 7, ADR-0005) : aucune création concurrente ne peut se glisser entre le calcul du
        numéro et l'insertion. La contrainte `UNIQUE(tournoi_id, numero)` reste le garde-fou ultime.
        """
        self._verifier_tournoi(tournoi_id)
        existants = self._departs.par_tournoi(tournoi_id)
        numero = existants[-1].numero + 1 if existants else 1
        depart = Depart.creer(tournoi_id, numero, tarif_centimes, horaire, quota)
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
        quota: int | None = None,
    ) -> Depart:
        """Édite le tarif, l'horaire et le quota d'un départ (le numéro est fixe).

        **Remplacement complet** : tarif, horaire et quota sont réécrits ; un `quota` omis (`None`)
        **retire** le plafond (E02US006, comme l'horaire). Lève `DepartIntrouvable` si le départ
        n'existe pas dans ce tournoi, `DomainError` si le tarif ou le quota sont hors plage.
        """
        depart = self._depart_du_tournoi(tournoi_id, depart_id)
        return self._departs.enregistrer(depart.modifier(tarif_centimes, horaire, quota))

    def supprimer(
        self,
        tournoi_id: TournoiId,
        depart_id: DepartId,
        autoriser_suppression_inscrits: bool = False,
    ) -> None:
        """Supprime un départ d'un tournoi (E02US004, garde-fou E02US009).

        Lève `DepartIntrouvable` si le départ n'existe pas dans ce tournoi. Si le créneau porte des
        **inscriptions**, lève `DepartAvecInscriptions` — un **signalement**, pas un refus
        ([ADR-0018](../../docs/adr/0018-supprimer-un-depart-a-inscriptions-confirmable.md), famille
        d'`ArcherEngage`) : l'admin confirme via `autoriser_suppression_inscrits=True`, et la
        suppression **efface les inscriptions** du créneau (cascade applicative de l'adapter).

        Le message **décompte les inscriptions, dont les payées**, pour rendre visible l'effet de
        bord monétaire (remboursement déporté en E08US005).
        """
        depart = self._depart_du_tournoi(tournoi_id, depart_id)
        assert depart.id is not None, "Un départ relu est persisté."
        # DETTE-007 : la confirmation est **aveugle**. Le décompte annoncé (inscriptions, dont
        # payées) n'est pas revérifié au rejeu — entre le 409 et la confirmation, d'autres tablettes
        # peuvent inscrire ou marquer payé, et l'on effacerait plus que le message n'a annoncé.
        if not autoriser_suppression_inscrits:
            self._signaler_inscriptions(depart)
        self._departs.supprimer(depart.id)

    def _signaler_inscriptions(self, depart: Depart) -> None:
        """Lève `DepartAvecInscriptions` si le créneau porte des inscriptions (E02US009).

        Le message énumère ce qui sera détruit — nombre d'inscriptions **et** de payées — plutôt que
        d'inviter à confirmer : les payées sont une somme encaissée qui deviendra un remboursement
        (E08US005), l'admin doit le voir avant de trancher.
        """
        assert depart.id is not None, "Un départ relu est persisté."
        inscriptions = self._inscriptions.par_depart(depart.id)
        if not inscriptions:
            return
        nombre = len(inscriptions)
        payees = sum(1 for inscription in inscriptions if inscription.paye)
        accord = "inscription" if nombre == 1 else "inscriptions"
        detail = f"{nombre} {accord}"
        if payees:
            detail += f", dont {payees} déjà payée" + ("s" if payees > 1 else "")
        message = (
            f"Le départ n° {depart.numero} porte {detail}. Le supprimer les effacera définitivement"
        )
        # La clause de remboursement ne s'affiche **que** s'il y a des payées : sinon elle
        # évoquerait un remboursement fictif (créneau gratuit ou aucune inscription réglée).
        if payees:
            message += " ; les sommes déjà payées seront à rembourser (E08US005)"
        message += ". Confirmez seulement si ce créneau est bien annulé."
        raise DepartAvecInscriptions(message)

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
