"""Service des **jalons « prêt à… »** — aucune garde n'est réécrite ici (ADR-0096). Tout vient des
gardes existantes : effectif, statut du tournoi, créneaux.

⚠️ **C'est le VERDICT qui est transmis au domaine, jamais ses ingrédients** : passer
`inscrits`/`minimum` laisserait le domaine refaire la comparaison, et rouvrirait par la fenêtre la
duplication sortie par la porte. `ARCHIVER` et `EXPORTER` lèvent `JalonNonInstruit`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from application.erreurs import JalonNonInstruit, TournoiIntrouvable
from application.tournois import ExigenceEffectifTournoi, LecteurDerouleDuTournoi
from domain.completude import Completude
from domain.jalon import (
    Jalon,
    NiveauPreparation,
    PreparationJalon,
    demarrer_sans_objet,
    evaluer_demarrer,
    evaluer_terminer,
    niveau_de_preparation,
    resume_du_manque,
    transition_offerte,
)
from domain.ports import DepartRepository, TournoiRepository
from domain.tournoi import StatutTournoi, TournoiId


class LecteurExigenceEffectif(Protocol):
    """Port étroit : « que ce tournoi exige-t-il d'inscrits, et qu'en a-t-il ? » (réalisé par
    `ServiceTournois`).

    Étroit **exprès** : le jalon n'a aucune raison de pouvoir démarrer, terminer ou annuler un
    tournoi. Dépendre de tout `ServiceTournois` depuis un chemin de lecture laisserait la porte
    ouverte à une écriture qui n'a rien à faire ici. Même patron que `LecteurPaiements`
    (`application/completude.py`) et `LecteurDerouleDuTournoi` (`application/tournois.py`).
    """

    def exigence_effectif(self, tournoi_id: TournoiId) -> ExigenceEffectifTournoi:
        """Ce que le tournoi exige d'inscrits, ce qu'il en a, et d'où vient le chiffre."""
        ...


class LecteurCompletude(Protocol):
    """Port étroit : la complétude d'un tournoi (réalisé par `ServiceCompletude`).

    Le jalon *terminer* **est** la complétude sportive : on la relit, on ne la recalcule pas.
    """

    def pour_tournoi(self, tournoi_id: TournoiId) -> Completude:
        """La complétude du tournoi (sportif et hors sportif, comptés séparément)."""
        ...


@dataclass(frozen=True)
class ApercuPreparation:
    """Ce qu'une **ligne de liste** a besoin de savoir d'un jalon (E16US010).

    Volontairement plus maigre que `PreparationJalon` : une liste rend une pastille, pas un écran.
    ⚠️ Ce n'est **pas** un second calcul — les deux champs se dérivent de la préparation complète.
    """

    tournoi_id: TournoiId
    niveau: NiveauPreparation
    resume: str | None


class ServiceJalons:
    """Cas d'usage : « puis-je passer à l'étape suivante, et sinon qu'est-ce qui manque ? »."""

    def __init__(
        self,
        tournoi_repository: TournoiRepository,
        depart_repository: DepartRepository,
        deroules: LecteurDerouleDuTournoi,
        exigences: LecteurExigenceEffectif,
        completudes: LecteurCompletude,
    ) -> None:
        self._tournois = tournoi_repository
        self._departs = depart_repository
        self._deroules = deroules
        self._exigences = exigences
        self._completudes = completudes

    def preparation(self, tournoi_id: TournoiId, jalon: Jalon) -> PreparationJalon:
        """La préparation d'un tournoi à un jalon donné.

        Lève `TournoiIntrouvable` (404) — comme la complétude, et pour la même raison : « rien ne
        manque » sur une ressource inexistante serait un 200 rassurant et faux. `JalonNonInstruit`
        (404) pour les membres pas encore spécifiés. Le tournoi est relu **une fois** : son
        existence est la garde d'entrée, son `statut` la garde partagée par toutes les transitions.
        """
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        if jalon is Jalon.DEMARRER:
            return self._demarrer(tournoi_id, tournoi.statut)
        if jalon is Jalon.TERMINER:
            return evaluer_terminer(
                completude=self._completudes.pour_tournoi(tournoi_id), statut=tournoi.statut
            )
        raise JalonNonInstruit(f"Il n'y a pas encore d'écran « prêt à {jalon.value} ».")

    def apercus(self, jalon: Jalon) -> list[ApercuPreparation]:
        """Le même jalon sur **tous** les tournois — de quoi pastiller une liste (E16US010).

        ⚠️ **Un seul appel, pas N** : c'est l'objet de la route, la complétude étant par ailleurs
        une lecture par tournoi. Un tournoi qui ne partira plus est tranché **sans lire ses
        créneaux ni son effectif** — `demarrer_sans_objet` rend la même réponse que le chemin
        complet. Seul `DEMARRER` est instruit : `TERMINER` exigerait la complétude sportive de
        chaque tournoi, un coût que la pastille du CA ne réclame pas.
        """
        if jalon is not Jalon.DEMARRER:
            raise JalonNonInstruit(f"Il n'y a pas d'aperçu de liste pour « prêt à {jalon.value} ».")
        apercus = []
        for tournoi in self._tournois.lister():
            if tournoi.id is None:
                continue
            preparation = (
                self._demarrer(tournoi.id, tournoi.statut)
                if transition_offerte(tournoi.statut, jalon)
                else demarrer_sans_objet(tournoi.statut)
            )
            apercus.append(
                ApercuPreparation(
                    tournoi_id=tournoi.id,
                    niveau=niveau_de_preparation(preparation),
                    resume=resume_du_manque(preparation),
                )
            )
        return apercus

    def _demarrer(self, tournoi_id: TournoiId, statut: StatutTournoi) -> PreparationJalon:
        """Rassemble ce que les gardes du feu vert vérifient, **sans les exécuter**.

        ⚠️ `exigence_effectif` lève `TournoiIntrouvable` — déjà écarté par l'appelant, mais c'est
        la raison pour laquelle l'existence est contrôlée **avant** : le jalon doit répondre 404
        quel que soit le membre, y compris ceux qui ne touchent pas à l'effectif.
        `message_de_refus()` est passé **tel quel**, sans quoi l'avertissement et le refus diraient
        deux choses différentes du même manque.
        """
        exigence = self._exigences.exigence_effectif(tournoi_id)
        return evaluer_demarrer(
            statut=statut,
            nb_creneaux=len(self._departs.par_tournoi(tournoi_id)),
            nb_etapes_deroule=len(self._deroules.par_tournoi(tournoi_id)),
            effectif_suffisant=exigence.suffisant,
            inscrits=exigence.inscrits,
            minimum=exigence.minimum,
            cause_effectif=None if exigence.suffisant else exigence.message_de_refus(),
        )
