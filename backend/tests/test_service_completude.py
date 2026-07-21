"""Tests du service applicatif `ServiceCompletude` (E12US005) — dérivés du CA, avant impl.

Le **jugement** (OK / alerte / à venir / en attente, séparation sportif/tiers) est couvert au
domaine (`test_domain_completude.py`). Ici on prouve ce que le **service ajoute** depuis le CA :
l'agrégation des décomptes que le domaine reçoit —

- **cibles terminées / total** sur les couples `(départ, cible)` **placés** (données persistées :
  plan matérialisé + inscriptions), une cible étant terminée quand **tous** ses archers ont une
  série complète (barème validé) ;
- **archers réglés / total** (réglé = `reste == 0`), lu via le port `LecteurPaiements` ;

plus le refus d'un tournoi inconnu (`TournoiIntrouvable`). Fakes en mémoire (le service n'orchestre
que des ports) : `FauxDepartRepository`/`FauxInscriptionRepository` viennent de `conftest` ; les
doubles de tournoi, placement, série, phase et le lecteur de paiements sont locaux, réduits à ce que
le service lit (le reste ne fait que **conformer** le port).
"""

from __future__ import annotations

import datetime

import pytest

from application.completude import ServiceCompletude
from application.erreurs import TournoiIntrouvable
from application.paiements import LignePaiementArcher
from domain.archer import ArcherId
from domain.bareme import BaremeQualification
from domain.completude import (
    CLE_PAIEMENTS,
    CLE_QUALIFICATION,
    EtatSection,
)
from domain.depart import Depart, DepartId
from domain.entree_audit import EntreeAudit
from domain.inscription import Inscription, InscriptionId
from domain.paiement import RecapPaiement
from domain.phase import Phase, PhaseId, TypePhase
from domain.placement import Affectation
from domain.serie import Serie, Volee
from domain.tournoi import Tournoi, TournoiId
from tests.conftest import FauxDepartRepository, FauxInscriptionRepository

_DATE = datetime.date(2026, 3, 14)


class FauxTournoiRepository:
    """Double de `TournoiRepository` en mémoire (le service ne teste que `par_id` non nul)."""

    def __init__(self) -> None:
        self._tournois: dict[int, Tournoi] = {}
        self._sequence = 0

    def ajouter(self, tournoi: Tournoi) -> Tournoi:
        self._sequence += 1
        import dataclasses

        persiste = dataclasses.replace(tournoi, id=self._sequence)
        self._tournois[self._sequence] = persiste
        return persiste

    def par_id(self, tournoi_id: TournoiId) -> Tournoi | None:
        return self._tournois.get(tournoi_id)

    def lister(self) -> list[Tournoi]:
        raise NotImplementedError

    def enregistrer(self, tournoi: Tournoi) -> Tournoi:
        raise NotImplementedError

    def supprimer(self, tournoi_id: TournoiId) -> None:
        raise NotImplementedError


class FauxPlacementRepository:
    """Double de `PlacementRepository` : seul `par_depart` sert (reste = conformité)."""

    def __init__(self) -> None:
        self._par_depart: dict[int, list[Affectation]] = {}

    def poser(self, depart_id: DepartId, affectation: Affectation) -> None:
        self._par_depart.setdefault(depart_id, []).append(affectation)

    def par_depart(self, depart_id: DepartId) -> list[Affectation]:
        return list(self._par_depart.get(depart_id, []))

    def definir_plan(self, depart_id: DepartId, affectations: object) -> None:
        raise NotImplementedError

    def definir_plan_avec_trace(
        self, depart_id: DepartId, affectations: object, entree: EntreeAudit
    ) -> None:
        raise NotImplementedError

    def poser_plusieurs(self, depart_id: DepartId, affectations: object) -> None:
        raise NotImplementedError

    def retirer(self, inscription_id: InscriptionId) -> None:
        raise NotImplementedError


class FauxSerieRepository:
    """Double de `SerieRepository` : seul `par_tournoi` sert ici (reste = conformité)."""

    def __init__(self) -> None:
        self._series: list[Serie] = []

    def poser(self, serie: Serie) -> None:
        self._series.append(serie)

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Serie]:
        return [s for s in self._series if s.tournoi_id == tournoi_id]

    def par_archer(self, tournoi_id: TournoiId, archer_id: ArcherId) -> Serie | None:
        raise NotImplementedError

    def horodatages(
        self, tournoi_id: TournoiId, archer_id: ArcherId
    ) -> dict[int, datetime.datetime]:
        raise NotImplementedError

    def enregistrer(self, serie: Serie) -> Serie:
        raise NotImplementedError

    def enregistrer_avec_trace(self, serie: Serie, entree: EntreeAudit) -> Serie:
        raise NotImplementedError


class FauxPhaseRepository:
    """Double de `PhaseRepository` : seul `par_tournoi_et_type` sert (reste = conformité)."""

    def __init__(self) -> None:
        self._phase: Phase | None = None

    def definir(self, phase: Phase) -> None:
        self._phase = phase

    def par_tournoi_et_type(self, tournoi_id: TournoiId, type_phase: TypePhase) -> Phase | None:
        if self._phase is None or type_phase is not TypePhase.QUALIFICATION:
            return None
        return self._phase

    def ajouter(self, phase: Phase) -> Phase:
        raise NotImplementedError

    def par_id(self, phase_id: PhaseId) -> Phase | None:
        raise NotImplementedError

    def enregistrer(self, phase: Phase) -> Phase:
        raise NotImplementedError


class FauxLecteurPaiements:
    """Double du port étroit `LecteurPaiements` : réponses pré-réglées par archer réglé / dû."""

    def __init__(self) -> None:
        self._lignes: list[LignePaiementArcher] = []

    def ajouter_archer(self, archer_id: ArcherId, du: int, paye: int) -> None:
        self._lignes.append(
            LignePaiementArcher(
                archer_id=archer_id,
                nom=f"Archer{archer_id}",
                prenom="X",
                club_id=None,
                recap=RecapPaiement(du_centimes=du, paye_centimes=paye),
            )
        )

    def lister_par_archer(self, tournoi_id: TournoiId) -> list[LignePaiementArcher]:
        return list(self._lignes)


def _serie(archer_id: ArcherId, *, volees_validees: int, nb_saisies: int | None = None) -> Serie:
    """Une série de `nb_saisies` volées (défaut `volees_validees`), dont `volees_validees` validées.

    Permet une série complète (toutes validées), partielle (moins de volées) ou saisie-mais-non-
    validée (`volees_validees=0`) — sans dépendre du chemin de saisie, on construit l'état visé.
    """
    total = nb_saisies if nb_saisies is not None else volees_validees
    from domain.blason import ZoneScore

    volees = tuple(
        Volee(
            numero=n,
            valeurs=(ZoneScore.DIX,),
            validee_par="MARTIN" if n <= volees_validees else None,
        )
        for n in range(1, total + 1)
    )
    return Serie(tournoi_id=1, archer_id=archer_id, volees=volees)


class Montage:
    """Attelage : service + repos garnis, un tournoi prêt (barème de qualification à 3 volées)."""

    def __init__(self, nb_volees_bareme: int = 3) -> None:
        self.tournois = FauxTournoiRepository()
        self.departs = FauxDepartRepository()
        self.placements = FauxPlacementRepository()
        self.inscriptions = FauxInscriptionRepository()
        self.series = FauxSerieRepository()
        self.phases = FauxPhaseRepository()
        self.paiements = FauxLecteurPaiements()
        tournoi = self.tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
        assert tournoi.id is not None
        self.tournoi_id: TournoiId = tournoi.id
        self.nb_volees_bareme = nb_volees_bareme
        if nb_volees_bareme > 0:
            self.phases.definir(
                Phase.qualification(self.tournoi_id, BaremeQualification.creer(nb_volees_bareme, 3))
            )
        self._numero = 0
        self.service = ServiceCompletude(
            self.tournois,
            self.departs,
            self.placements,
            self.inscriptions,
            self.series,
            self.phases,
            self.paiements,
        )

    def creer_depart(self) -> DepartId:
        self._numero += 1
        depart = self.departs.ajouter(
            Depart.creer(self.tournoi_id, numero=self._numero, tarif_centimes=1000)
        )
        assert depart.id is not None
        return depart.id

    def placer(
        self, depart_id: DepartId, cible_index: int, archer_id: ArcherId, position: str
    ) -> None:
        """Inscrit un archer sur le départ et l'affecte à une cible (une case du plan)."""
        inscription = self.inscriptions.ajouter(Inscription.creer(archer_id, depart_id))
        assert inscription.id is not None
        self.placements.poser(
            depart_id,
            Affectation(inscription_id=inscription.id, cible_index=cible_index, position=position),
        )

    def qualification(self) -> object:
        return next(
            ligne
            for ligne in self.service.pour_tournoi(self.tournoi_id).sportif
            if ligne.cle == CLE_QUALIFICATION
        )


# --- Tournoi ---------------------------------------------------------------------------------


def test_completude_d_un_tournoi_inexistant_leve_introuvable() -> None:
    m = Montage()
    with pytest.raises(TournoiIntrouvable):
        m.service.pour_tournoi(999)


# --- Qualification : cibles (départ, cible) terminées / total --------------------------------


def test_une_cible_dont_tous_les_archers_ont_fini_est_terminee() -> None:
    """Une cible = un couple (départ, cible) placé ; terminée quand toutes ses séries le sont."""
    m = Montage(nb_volees_bareme=3)
    depart = m.creer_depart()
    m.placer(depart, cible_index=1, archer_id=10, position="A")
    m.placer(depart, cible_index=1, archer_id=11, position="B")
    m.series.poser(_serie(10, volees_validees=3))
    m.series.poser(_serie(11, volees_validees=3))

    qualif = m.service.pour_tournoi(m.tournoi_id).sportif[0]
    assert qualif.cle == CLE_QUALIFICATION
    assert (qualif.fait, qualif.total) == (1, 1)
    assert qualif.etat is EtatSection.OK


def test_une_cible_avec_un_archer_pas_fini_n_est_pas_terminee() -> None:
    """Il suffit d'**un** archer qui n'a pas fini pour que la cible ne compte pas comme terminée."""
    m = Montage(nb_volees_bareme=3)
    depart = m.creer_depart()
    m.placer(depart, cible_index=1, archer_id=10, position="A")
    m.placer(depart, cible_index=1, archer_id=11, position="B")
    m.series.poser(_serie(10, volees_validees=3))  # fini
    m.series.poser(_serie(11, volees_validees=2, nb_saisies=3))  # 2 validées / 3 : pas fini

    qualif = m.service.pour_tournoi(m.tournoi_id).sportif[0]
    assert (qualif.fait, qualif.total) == (0, 1)
    assert qualif.etat is EtatSection.ALERTE


def test_series_saisies_mais_non_validees_ne_terminent_pas_la_cible() -> None:
    """Tout saisi mais rien validé : la cible n'est pas *close* (cohérent avec le classement)."""
    m = Montage(nb_volees_bareme=3)
    depart = m.creer_depart()
    m.placer(depart, cible_index=1, archer_id=10, position="A")
    m.series.poser(_serie(10, volees_validees=0, nb_saisies=3))

    assert m.service.pour_tournoi(m.tournoi_id).sportif[0].etat is EtatSection.ALERTE


def test_le_compte_de_cibles_couvre_plusieurs_departs() -> None:
    """« 30/30 cibles » à l'échelle du test : deux départs, deux cibles chacun, 3 terminées sur 4.

    Un même numéro de cible sur deux créneaux compte pour **deux** sessions (arbitrage de maille).
    """
    m = Montage(nb_volees_bareme=3)
    d1 = m.creer_depart()
    d2 = m.creer_depart()
    # Départ 1 : cible 1 finie, cible 2 finie.
    m.placer(d1, 1, 10, "A")
    m.placer(d1, 2, 11, "A")
    # Départ 2 : cible 1 finie, cible 2 PAS finie (archer sans série).
    m.placer(d2, 1, 20, "A")
    m.placer(d2, 2, 21, "A")
    for archer_id in (10, 11, 20):
        m.series.poser(_serie(archer_id, volees_validees=3))
    # archer 21 : aucune série → cible 2 du départ 2 non terminée

    qualif = m.service.pour_tournoi(m.tournoi_id).sportif[0]
    assert (qualif.fait, qualif.total) == (3, 4)
    assert qualif.etat is EtatSection.ALERTE


def test_un_archer_en_reserve_ne_cree_pas_de_cible() -> None:
    """Un inscrit **sans** affectation (réserve) n'est sur aucune cible : hors du total."""
    m = Montage(nb_volees_bareme=3)
    depart = m.creer_depart()
    # inscription sans affectation (réserve) : on l'ajoute directement, sans `placer`
    m.inscriptions.ajouter(Inscription.creer(archer_id=99, depart_id=depart))
    m.placer(depart, cible_index=1, archer_id=10, position="A")
    m.series.poser(_serie(10, volees_validees=3))

    qualif = m.service.pour_tournoi(m.tournoi_id).sportif[0]
    assert (qualif.fait, qualif.total) == (1, 1)  # la réserve ne gonfle pas le total


def test_aucun_placement_qualification_en_attente() -> None:
    """Rien de placé : 0/0 cibles → le domaine remonte « en attente » (pas un « 0/0 OK »)."""
    m = Montage(nb_volees_bareme=3)
    m.creer_depart()  # un créneau, mais aucune affectation

    qualif = m.service.pour_tournoi(m.tournoi_id).sportif[0]
    assert (qualif.fait, qualif.total) == (0, 0)
    assert qualif.etat is EtatSection.EN_ATTENTE


def test_bareme_non_configure_qualification_en_attente_meme_avec_placements() -> None:
    """Barème de qualification absent : rien n'est *scorable* → « en attente », pas « 0/N à finir ».

    Même avec des cibles placées : sans barème, aucune série ne peut se valider, l'écran ne doit pas
    laisser croire la saisie en cours. Le service renvoie (0, 0) → le domaine remonte EN_ATTENTE.
    """
    m = Montage(nb_volees_bareme=0)  # aucune phase de qualification définie
    depart = m.creer_depart()
    m.placer(depart, cible_index=1, archer_id=10, position="A")

    qualif = m.service.pour_tournoi(m.tournoi_id).sportif[0]
    assert (qualif.fait, qualif.total) == (0, 0)
    assert qualif.etat is EtatSection.EN_ATTENTE


# --- Paiements : archers réglés / total ------------------------------------------------------


def test_paiements_comptent_les_archers_dont_le_reste_est_nul() -> None:
    """Réglé = plus rien à payer. Deux réglés (dont un sans dû) sur trois → 2/3, alerte."""
    m = Montage()
    m.paiements.ajouter_archer(archer_id=10, du=1000, paye=1000)  # réglé
    m.paiements.ajouter_archer(archer_id=11, du=0, paye=0)  # ne doit rien → réglé d'office
    m.paiements.ajouter_archer(archer_id=12, du=1000, paye=0)  # reste dû

    paie = next(
        ligne
        for ligne in m.service.pour_tournoi(m.tournoi_id).hors_sportif
        if ligne.cle == CLE_PAIEMENTS
    )
    assert (paie.fait, paie.total) == (2, 3)
    assert paie.etat is EtatSection.ALERTE
