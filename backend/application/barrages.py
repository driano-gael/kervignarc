"""Service applicatif Barrage (E06US003, ADR-0066) — organiser un départage au tir.

Cas d'usage d'**écriture** (donc consommés par la file du writer unique, règle 7) : annoncer un
barrage sur une égalité que la politique `tiebreak` a signalée, saisir ses manches, le clore. La
lecture (« quelles égalités restent à départager ? ») appartient au **classement**, qui les calcule
déjà : les recalculer ici en produirait une seconde version, qui dériverait.

**Le service ne décide pas qu'un barrage est nécessaire — il l'organise.** C'est la politique qui
signale (`Classement.egalites_a_departager`, seuil d'ADR-0066) et l'organisateur qui déclenche. Le
service se contente de vérifier que l'égalité annoncée est bien l'une de celles-là : sans ce
contrôle, on pourrait faire retirer trois archers qui ne sont pas à égalité, et publier le résultat.

⚠️ **Portée** : seule `PorteeBarrage.QUALIFICATION` est câblée de bout en bout. Les deux autres
portées (poule, Big Shoot Off) existent dans le modèle et dans le moteur, mais leurs types de phase
n'ont **aucun consommateur de production** (DETTE-028) — il n'y a littéralement pas de classement de
poule calculé quelque part où brancher un barrage. Les câbler produirait une surface pour une phase
que l'application ne sait pas encore dérouler.
"""

from __future__ import annotations

from collections.abc import Sequence

from application.classements import ServiceClassement
from application.erreurs import (
    BarrageDejaClos,
    BarrageIntrouvable,
    EgaliteNonDepartageable,
    TournoiIntrouvable,
)
from domain.barrage import (
    BarrageDePlaces,
    BarrageId,
    PorteeBarrage,
    TirBarrage,
)
from domain.erreurs import ConfigurationBarrageInvalide
from domain.participant import Participant
from domain.ports import BarrageRepository, Horloge, TournoiRepository
from domain.tournoi import TournoiId


class ServiceBarrage:
    """Cas d'usage du barrage de places : annoncer, saisir une manche, clore."""

    def __init__(
        self,
        tournois: TournoiRepository,
        barrages: BarrageRepository,
        classements: ServiceClassement,
        horloge: Horloge,
    ) -> None:
        self._tournois = tournois
        self._barrages = barrages
        self._classements = classements
        self._horloge = horloge

    def lister(self, tournoi_id: TournoiId) -> list[BarrageDePlaces]:
        """Tous les barrages d'un tournoi, clos compris (les verdicts acquis en font partie)."""
        self._exiger_tournoi(tournoi_id)
        return self._barrages.par_tournoi(tournoi_id)

    def annoncer(self, tournoi_id: TournoiId, rang: int) -> BarrageDePlaces:
        """Annonce un barrage sur l'égalité **actuellement** signalée au rang donné.

        Les tireurs sont pris dans le classement **au moment de l'annonce**, puis figés : c'est ce
        qui empêche la liste de changer sous les pieds du juge quand une volée en retard est
        validée. Lève `EgaliteNonDepartageable` si plus rien n'est à départager à ce rang, et rend
        le barrage **déjà ouvert** s'il en existe un (l'annonce est idempotente — un double clic sur
        « faire tirer » ne doit pas ouvrir deux barrages sur la même place).
        """
        self._exiger_tournoi(tournoi_id)
        existant = self._ouvert_au_rang(tournoi_id, rang)
        if existant is not None:
            return existant
        egalite = next(
            (
                candidate
                for candidate in self._classements.pour_tournoi(tournoi_id).egalites_a_departager
                if candidate.rang == rang
            ),
            None,
        )
        if egalite is None:
            raise EgaliteNonDepartageable(
                f"Aucune égalité à départager au rang {rang} : soit elle n'existe plus, soit le "
                "format de ce tournoi ne prévoit pas de barrage à cette place."
            )
        return self._barrages.ouvrir(
            BarrageDePlaces(
                tournoi_id=tournoi_id,
                portee=PorteeBarrage.QUALIFICATION,
                participants=egalite.participants,
                cree_le=self._horloge.maintenant(),
                rang_dispute=egalite.rang,
            )
        )

    def saisir_manche(
        self,
        tournoi_id: TournoiId,
        barrage_id: BarrageId,
        tirs: Sequence[TirBarrage],
        manche: int | None = None,
    ) -> BarrageDePlaces:
        """Saisit (ou **corrige**) une manche, puis rend le barrage rechargé.

        `manche` absent = la **suivante** ; fourni, il désigne la manche à réécrire — c'est le mode
        de correction d'une flèche mal notée, le verdict n'étant jamais stocké mais recalculé.

        Le moteur valide le reste au moment où le verdict se recalcule : un tireur déjà départagé,
        un groupe retiré à moitié, un participant en double lèvent `ConfigurationBarrageInvalide`
        (→ 422). On ne les revérifie pas ici — les dupliquer ferait diverger deux gardes qui disent
        la même chose.
        """
        barrage = self._exiger_barrage(tournoi_id, barrage_id)
        if barrage.clos:
            raise BarrageDejaClos(
                "Ce barrage est clos : rouvrez-le avant d'y saisir une manche de plus."
            )
        numero = manche if manche is not None else len(barrage.manches) + 1
        if numero < 1:
            raise ConfigurationBarrageInvalide(
                "Les manches d'un barrage se comptent à partir de 1."
            )
        self._exiger_tireurs_du_barrage(barrage, tirs)
        return self._barrages.enregistrer_manche(barrage_id, numero, tirs)

    def clore(self, tournoi_id: TournoiId, barrage_id: BarrageId) -> BarrageDePlaces:
        """Clôt un barrage **résolu** — le juge acte le verdict, plus de retir attendu.

        Clore un barrage non résolu est refusé : sa clôture signifierait « c'est tranché » alors que
        des tireurs restent à égalité, et le classement afficherait un ex æquo que l'écran
        présenterait comme réglé.
        """
        barrage = self._exiger_barrage(tournoi_id, barrage_id)
        if not barrage.resultat().est_resolu:
            raise EgaliteNonDepartageable(
                "Ce barrage n'a pas départagé tout le monde : il reste au moins un groupe à faire "
                "retirer avant de le clore."
            )
        return self._barrages.clore(barrage_id)

    def _ouvert_au_rang(self, tournoi_id: TournoiId, rang: int) -> BarrageDePlaces | None:
        """Le barrage de qualification **non clos** déjà annoncé à ce rang, s'il y en a un."""
        return next(
            (
                barrage
                for barrage in self._barrages.par_tournoi(tournoi_id)
                if barrage.portee is PorteeBarrage.QUALIFICATION
                and barrage.rang_dispute == rang
                and not barrage.clos
            ),
            None,
        )

    def _exiger_tournoi(self, tournoi_id: TournoiId) -> None:
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")

    def _exiger_barrage(self, tournoi_id: TournoiId, barrage_id: BarrageId) -> BarrageDePlaces:
        """Le barrage, à condition qu'il appartienne bien à **ce** tournoi.

        Le contrôle d'appartenance n'est pas cosmétique : sans lui, un identifiant deviné laisserait
        saisir des flèches dans le barrage d'un autre tournoi — et deux tournois tournent en
        parallèle par conception (intérieur et extérieur).
        """
        self._exiger_tournoi(tournoi_id)
        barrage = self._barrages.par_id(barrage_id)
        if barrage is None or barrage.tournoi_id != tournoi_id:
            raise BarrageIntrouvable(
                f"Aucun barrage d'identifiant {barrage_id} dans le tournoi {tournoi_id}."
            )
        return barrage

    def _exiger_tireurs_du_barrage(
        self, barrage: BarrageDePlaces, tirs: Sequence[TirBarrage]
    ) -> None:
        """Refuse une manche où figure quelqu'un qui n'a jamais été annoncé sur ce barrage.

        Le moteur attrape déjà le tireur **déjà départagé** ; il ne peut pas attraper l'archer
        parfaitement **étranger** au barrage, puisqu'il ne connaît que les tirs qu'on lui donne. Le
        laisser passer classerait un tiers à une place qu'il n'a pas disputée.
        """
        etrangers = [tir.participant for tir in tirs if tir.participant not in barrage.participants]
        if etrangers:
            raise ConfigurationBarrageInvalide(
                f"{len(etrangers)} tireur(s) de cette manche ne font pas partie du barrage annoncé."
            )

    @staticmethod
    def tir(archer_id: int, score: int | None, distance_au_centre: int | None = None) -> TirBarrage:
        """Fabrique un tir depuis un identifiant d'archer — la frontière API parle archers.

        La conversion vit ici et non dans le DTO : `Participant` est l'abstraction du moteur
        (ADR-0028), et c'est la couche applicative qui résout « archer ↔ participant » — pas l'API.
        """
        return TirBarrage(
            participant=Participant.individuel(archer_id),
            score=score,
            distance_au_centre=distance_au_centre,
        )
