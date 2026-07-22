"""Service applicatif **Complétude du tournoi** (E12US005) — « qu'est-ce qui manque pour finir ? ».

Cas d'usage de **lecture** : agrège, depuis les ports, les décomptes qui répondent à la question de
l'organisateur, puis délègue l'assemblage à la politique pure `domain.completude.evaluer_completude`
(le service compte, le domaine juge). Lecture seule (hors file d'écriture, règle 7) : l'endpoint
l'exécute dans le threadpool et le front la **poll** (live, comme la supervision).

Deux décomptes agrégés :

- **Qualification, en cibles terminées / total.** Une « cible » ici = un couple `(départ, cible)`
  portant au moins un archer placé (donnée **persistante** : plan matérialisé + inscriptions,
  ADR-0024 / E02US009) — pas l'état runtime d'un poste rattaché (celui-là, c'est la supervision,
  E12US001). Elle est *terminée* quand **toutes** ses séries sont complètes (`Serie.est_complete` :
  toutes les volées du barème **validées**). Arbitrage de maille reversé dans `stories/` : le compte
  se fait sur `(départ, cible)`, pas sur la cible physique, car un même numéro de cible sert sur
  plusieurs créneaux et chacun est une session de tir à terminer.
- **Paiements, en archers réglés / total.** Réglé = `reste_centimes == 0` (un archer qui ne doit
  rien — sans inscription — est réglé d'office). Lu via un **port étroit** sur `ServicePaiements`
  (`LecteurPaiements`), qui porte déjà la règle de calcul dû/payé/reste (E08US002) : on ne la
  redérive pas ici.

Les **phases éliminatoires** et l'état *prêt / en attente* du classement sont dérivés par le domaine
(cf. `domain.completude`) — le premier séquencé (EPIC-05), le second de la qualification.
"""

from __future__ import annotations

from typing import Protocol

from application.erreurs import TournoiIntrouvable
from application.paiements import LignePaiementArcher
from domain.archer import ArcherId
from domain.completude import Completude, evaluer_completude
from domain.phase import TypePhase
from domain.ports import (
    DepartRepository,
    InscriptionRepository,
    PhaseRepository,
    PlacementRepository,
    SerieRepository,
    TournoiRepository,
)
from domain.serie import Serie
from domain.tournoi import TournoiId


class LecteurPaiements(Protocol):
    """Port étroit : lire le récapitulatif de paiement par archer (réalisé par `ServicePaiements`).

    La complétude ne dépend pas de tout `ServicePaiements` (marquages compris) : juste de sa
    capacité à énumérer dû/payé/reste par archer. Découplage utile en test (un faux lecteur suffit)
    et honnête (la complétude n'écrit aucun paiement).
    """

    def lister_par_archer(self, tournoi_id: TournoiId) -> list[LignePaiementArcher]:
        """Le récapitulatif de paiement de chaque archer du tournoi (dû / payé / reste)."""
        ...


class ServiceCompletude:
    """Cas d'usage de la complétude : agréger les décomptes d'un tournoi et en juger l'état."""

    def __init__(
        self,
        tournoi_repository: TournoiRepository,
        depart_repository: DepartRepository,
        placement_repository: PlacementRepository,
        inscription_repository: InscriptionRepository,
        serie_repository: SerieRepository,
        phase_repository: PhaseRepository,
        paiements: LecteurPaiements,
    ) -> None:
        self._tournois = tournoi_repository
        self._departs = depart_repository
        self._placements = placement_repository
        self._inscriptions = inscription_repository
        self._series = serie_repository
        self._phases = phase_repository
        self._paiements = paiements

    def pour_tournoi(self, tournoi_id: TournoiId) -> Completude:
        """Complétude d'un tournoi. Lève `TournoiIntrouvable` si le tournoi n'existe pas.

        Lecture seule ; les décomptes sont agrégés ici (règle métier de *complétude* déléguée au
        domaine). Voir le module pour la définition des deux décomptes.
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        qualif = self._compter_cibles(tournoi_id)
        paiements = self._compter_paiements(tournoi_id)
        return evaluer_completude(qualif=qualif, paiements=paiements)

    def _compter_cibles(self, tournoi_id: TournoiId) -> tuple[int, int]:
        """`(cibles_terminees, cibles_total)` sur l'ensemble des couples `(départ, cible)` placés.

        Une cible est *terminée* quand tous ses archers placés ont une série complète (barème
        validé). **Barème non configuré** (phase de qualification absente) → on renvoie `(0, 0)` :
        rien n'est encore *scorable* (aucune série ne peut se valider sans barème), donc la ligne
        remonte en **« en attente »** — pas un « 0/N à finir » trompeur qui laisserait croire la
        saisie en cours. On n'échoue pas là-dessus (robustesse jour J).
        """
        phase = self._phases.par_tournoi_et_type(tournoi_id, TypePhase.QUALIFICATION)
        nb_volees = phase.bareme.nb_volees if phase is not None else 0
        if nb_volees <= 0:
            return 0, 0
        series: dict[ArcherId, Serie] = {
            s.archer_id: s for s in self._series.par_tournoi(tournoi_id)
        }
        total = 0
        terminees = 0
        for depart in self._departs.par_tournoi(tournoi_id):
            if depart.id is None:
                continue  # défensif : un départ lu en base a toujours un id
            inscriptions = {i.id: i for i in self._inscriptions.par_depart(depart.id)}
            archers_par_cible: dict[int, list[ArcherId]] = {}
            for affectation in self._placements.par_depart(depart.id):
                inscription = inscriptions.get(affectation.inscription_id)
                if inscription is None:
                    continue  # défensif : affectation sans inscription correspondante
                archers_par_cible.setdefault(affectation.cible_index, []).append(
                    inscription.archer_id
                )
            for archer_ids in archers_par_cible.values():
                total += 1
                if all(self._serie_complete(series.get(aid), nb_volees) for aid in archer_ids):
                    terminees += 1
        return terminees, total

    @staticmethod
    def _serie_complete(serie: Serie | None, nb_volees: int) -> bool:
        """Une série existante et complète (barème validé) ; `None` (rien saisi) → incomplète.

        # DETTE-014 : cette définition **ignore le forfait** (E12US004, non livrée). Un archer qui
        # abandonne garde ses volées partielles (le CA d'E12US004 préserve les flèches tirées) : sa
        # série ne sera **jamais** complète, donc sa cible resterait « à finir » à jamais et la
        # complétude mentirait dès qu'un forfait existe. À la livraison d'E12US004, y traiter un
        # archer forfait comme « série close par forfait » (cf. docs/dette.md).
        """
        return serie is not None and serie.est_complete(nb_volees)

    def _compter_paiements(self, tournoi_id: TournoiId) -> tuple[int, int]:
        """`(archers_regles, archers_total)` — réglé = plus rien à payer (`reste_centimes == 0`)."""
        lignes = self._paiements.lister_par_archer(tournoi_id)
        regles = sum(1 for ligne in lignes if ligne.recap.reste_centimes == 0)
        return regles, len(lignes)
