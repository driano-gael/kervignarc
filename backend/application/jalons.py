"""Service applicatif des **jalons « prêt à… »** (E16US012) — le foyer unique de la famille.

Cas d'usage de **lecture** : rassemble, depuis les ports, ce que les gardes du cycle de vie
vérifient, et confie le jugement à la politique pure `domain.jalon` (le service compte, le domaine
juge). Lecture seule, hors file d'écriture (règle 7) ; l'endpoint l'exécute dans le threadpool.

**Un seul foyer, et c'est le sujet de l'US.** Ce que `E16US007` (exports) et `E16US008` (feu vert)
allaient faire chacune dans son coin — décider quoi afficher avant une action, sous quelle forme —
se décide ici, une fois (ADR-0096).

**Aucune garde n'est réécrite ici.** C'est le CA « sans doublonner ce qui existe », et c'est
l'endroit où il se joue :

- l'effectif vient de `ServiceTournois.exigence_effectif` — **la méthode que la garde de démarrage
  exécute elle-même** (`_exiger_un_effectif_suffisant`). Un second calcul aurait dérivé au premier
  changement d'ADR-0075 (« l'exigence se juge sur le créneau le moins garni, pas sur la somme ») ;
  ⚠️ et c'est le **verdict** (`suffisant`) qui est transmis, pas ses ingrédients : la première
  version passait `inscrits`/`minimum` et laissait le domaine refaire la comparaison, ce qui
  rouvrait par la fenêtre la duplication sortie par la porte (relevé par quatre axes de revue) ;
- le **statut** vient du tournoi déjà relu pour contrôler son existence : c'est la garde que
  `ServiceTournois` lève avant toutes les autres (`TransitionStatutInvalide`), et elle manquait ;
- les créneaux viennent du **même** `DepartRepository.par_tournoi` que la garde de `vers_pret` ;
- « prêt à terminer » relit `ServiceCompletude.pour_tournoi` sans y toucher.

Là où le partage mécanique s'arrête — le service décide qu'*aucun créneau* vaut `EN_ATTENTE`, la
garde décide que ça vaut `TournoiSansDepart` —, l'accord est **épinglé par un test de cohérence**
(`test_service_jalons.py`), sur le patron déjà employé entre `domain.tournoi._TRANSITIONS` et la
légalité effective du service. Une garde qui bougerait sans son jalon fait tomber ce test.

**Deux membres sur quatre sont instruits.** `ARCHIVER` et `EXPORTER` ont leur place dans la famille
(la forme est posée, la question se dérive) mais aucune règle : ils lèvent `JalonNonInstruit`
plutôt que de rendre une réponse vide qui se lirait « rien ne manque ». C'est la couture où leurs
US respectives se brancheront.
"""

from __future__ import annotations

from typing import Protocol

from application.erreurs import JalonNonInstruit, TournoiIntrouvable
from application.tournois import ExigenceEffectifTournoi, LecteurDerouleDuTournoi
from domain.completude import Completude
from domain.jalon import Jalon, PreparationJalon, evaluer_demarrer, evaluer_terminer
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

        Lève `TournoiIntrouvable` (→ 404) si le tournoi n'existe pas — comme la complétude, et pour
        la même raison : rendre « rien ne manque » sur une ressource inexistante serait un 200
        rassurant et faux. Lève `JalonNonInstruit` (→ 404) pour les deux membres pas encore
        spécifiés.

        Le tournoi est relu **une fois** : son existence est la garde d'entrée, et son `statut` est
        la garde que toutes les transitions partagent. Les deux membres instruits le reçoivent.
        """
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        if jalon is Jalon.DEMARRER:
            return self._demarrer(tournoi_id, tournoi.statut)
        if jalon is Jalon.TERMINER:
            return evaluer_terminer(self._completudes.pour_tournoi(tournoi_id), tournoi.statut)
        raise JalonNonInstruit(f"Il n'y a pas encore d'écran « prêt à {jalon.value} ».")

    def _demarrer(self, tournoi_id: TournoiId, statut: StatutTournoi) -> PreparationJalon:
        """Rassemble ce que les gardes du feu vert vérifient, **sans les exécuter**.

        ⚠️ `exigence_effectif` lève `TournoiIntrouvable` — déjà écarté par l'appelant, donc sans
        effet ici, mais c'est la raison pour laquelle l'existence est contrôlée **avant** et non
        laissée à cet appel : le jalon doit répondre 404 quel que soit le membre demandé, y compris
        ceux qui ne touchent pas à l'effectif.

        `message_de_refus()` est passé **tel quel** : c'est la phrase que la garde met dans son
        `EffectifInsuffisantPourDemarrer`, et la rédiger une seconde fois ici pour l'avertissement
        aurait laissé l'avertissement et le refus dire deux choses différentes du même manque.
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
