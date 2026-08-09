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
from application.portee import qualification_courante
from domain.archer import ArcherId
from domain.completude import Completude, evaluer_completude
from domain.cycle_depart import AvancementDepart
from domain.depart import DepartId
from domain.phase import Phase
from domain.ports import (
    DepartRepository,
    ForfaitRepository,
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
        forfait_repository: ForfaitRepository,
        paiements: LecteurPaiements,
    ) -> None:
        self._tournois = tournoi_repository
        self._departs = depart_repository
        self._placements = placement_repository
        self._inscriptions = inscription_repository
        self._series = serie_repository
        self._phases = phase_repository
        self._forfaits = forfait_repository
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

    def avancement_depart(self, tournoi_id: TournoiId, depart_id: DepartId) -> AvancementDepart:
        """Avancement d'un créneau (E12US008) : archers placés, ayant tiré, séries closes.

        Réalise le port `LecteurAvancementDepart` consommé par `ServiceDeparts` (garde-fou cycle).
        On réutilise la même notion de série **close** que la complétude — `_serie_close` : barème
        validé **ou** forfait (DETTE-014, ADR-0050) — d'où la place naturelle de ce calcul ici. « A
        tiré » = **au moins une flèche validée** (`Serie.nb_fleches_validees > 0`), le fait réel qui
        fait basculer un créneau *ouvert → lancé* (le CA E12US008).

        **Barème non configuré** (phase de qualification absente) → aucune série n'est *scorable* ni
        validable : `nb_ayant_tire` et `nb_series_closes` tombent à 0 (hors forfaits), le créneau
        reste donc **ouvert** — librement éditable, robustesse jour J (même parti que
        `_compter_cibles`). La résolution barème + forfaits est **dupliquée** de `_compter_cibles`
        (`# DETTE-022` — le 3ᵉ cas est arrivé avec `ServiceSaisie` en E04US018 ; l'extraction
        est inscrite au registre, elle se fera en US dédiée).
        """
        # E05US025 : la qualification **de ce créneau**, et celle qui s'y tire en ce moment —
        # plus « la » qualification du tournoi. Un créneau peut en enchaîner plusieurs, et son
        # avancement se juge sur celle qui est au pas de tir, pas sur la première de la séquence.
        phase = qualification_courante(self._phases, depart_id)
        nb_volees = phase.bareme.nb_volees if phase is not None and phase.bareme is not None else 0
        forfaits_qualif: set[ArcherId] = (
            {f.archer_id for f in self._forfaits.par_phase(phase.id)}
            if phase is not None and phase.id is not None
            else set()
        )
        series: dict[ArcherId, Serie] = self._feuilles(phase)
        inscriptions = {i.id: i for i in self._inscriptions.par_depart(depart_id)}
        nb_places = 0
        nb_ayant_tire = 0
        nb_series_closes = 0
        for affectation in self._placements.par_depart(depart_id):
            inscription = inscriptions.get(affectation.inscription_id)
            if inscription is None:
                continue  # défensif : affectation sans inscription correspondante
            archer_id = inscription.archer_id
            nb_places += 1
            serie = series.get(archer_id)
            if serie is not None and serie.nb_fleches_validees > 0:
                nb_ayant_tire += 1
            if self._serie_close(serie, nb_volees, archer_id in forfaits_qualif):
                nb_series_closes += 1
        return AvancementDepart(
            nb_places=nb_places,
            nb_ayant_tire=nb_ayant_tire,
            nb_series_closes=nb_series_closes,
        )

    # DETTE-022 : 2ᵉ des quatre écritures de « phase de qualif -> forfaits » (avec
    # `avancement_depart`, `ServiceClassement` et `ServiceSaisie`).
    def _compter_cibles(self, tournoi_id: TournoiId) -> tuple[int, int]:
        """`(cibles_terminees, cibles_total)` sur l'ensemble des couples `(départ, cible)` placés.

        Une cible est *terminée* quand tous ses archers placés ont une série complète (barème
        validé). **Barème non configuré** (phase de qualification absente) → on renvoie `(0, 0)` :
        rien n'est encore *scorable* (aucune série ne peut se valider sans barème), donc la ligne
        remonte en **« en attente »** — pas un « 0/N à finir » trompeur qui laisserait croire la
        saisie en cours. On n'échoue pas là-dessus (robustesse jour J).
        """
        total = 0
        terminees = 0
        for depart in self._departs.par_tournoi(tournoi_id):
            if depart.id is None:
                continue  # défensif : un départ lu en base a toujours un id
            # E05US025 : **par créneau**, et non une phase pour tout le tournoi. Chaque créneau a sa
            # séquence (ADR-0075) et peut y enchaîner plusieurs qualifications (ADR-0082) ; ses
            # cibles se jugent sur le barème de celle qui s'y tire. Un créneau non scorable (pas de
            # qualification, ou pas de barème) n'apporte **aucune** cible au compte plutôt que d'en
            # apporter des fausses — même parti que le `(0, 0)` d'avant l'US, ramené au créneau.
            phase = qualification_courante(self._phases, depart.id)
            nb_volees = (
                phase.bareme.nb_volees if phase is not None and phase.bareme is not None else 0
            )
            if phase is None or nb_volees <= 0:
                continue
            series = self._feuilles(phase)
            # DETTE-014 résorbée (E04US015, ADR-0050) : un archer déclaré **forfait en
            # qualification** a sa série **close par forfait** — sa cible ne reste plus « à finir »
            # à jamais malgré ses volées partielles préservées.
            forfaits_qualif = (
                {f.archer_id for f in self._forfaits.par_phase(phase.id)}
                if phase.id is not None
                else set()
            )
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
                if all(
                    self._serie_close(series.get(aid), nb_volees, aid in forfaits_qualif)
                    for aid in archer_ids
                ):
                    terminees += 1
        return terminees, total

    def _feuilles(self, phase: Phase | None) -> dict[ArcherId, Serie]:
        """Les feuilles de marque **de cette phase**, indexées par archer.

        ⚠️ **`par_phase`, jamais `par_tournoi`** (E05US025, ADR-0082). L'indexation par `archer_id`
        est ici légitime — dans une phase donnée, un archer n'a qu'une feuille — mais elle ne
        l'était
        plus sur `par_tournoi`, qui rend désormais une ligne **par phase tirée** : le `dict` n'en
        aurait gardé qu'une, au hasard de l'ordre du repository, si bien que la complétude aurait
        jugé le premier tour sur les volées du second (ou l'inverse) d'un rafraîchissement à
        l'autre.
        """
        if phase is None or phase.id is None:
            return {}
        return {serie.archer_id: serie for serie in self._series.par_phase(phase.id)}

    @staticmethod
    def _serie_close(serie: Serie | None, nb_volees: int, est_forfait: bool) -> bool:
        """La saisie de l'archer est **close** : soit sa série est complète (barème validé), soit il
        est **forfait** (E04US015, ADR-0050).

        Un archer forfait garde ses volées partielles (les flèches sont préservées, ADR-0016), donc
        sa série n'est **jamais** complète ; le compter comme clos évite qu'une cible reste « à
        finir » à jamais — c'était DETTE-014 (désormais résorbée). `None` (rien saisi) et non
        forfait → incomplète.
        """
        return est_forfait or (serie is not None and serie.est_complete(nb_volees))

    def _compter_paiements(self, tournoi_id: TournoiId) -> tuple[int, int]:
        """`(archers_regles, archers_total)` — réglé = plus rien à payer (`reste_centimes == 0`)."""
        lignes = self._paiements.lister_par_archer(tournoi_id)
        regles = sum(1 for ligne in lignes if ligne.recap.reste_centimes == 0)
        return regles, len(lignes)
