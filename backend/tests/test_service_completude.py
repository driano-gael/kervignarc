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
    LigneCompletude,
)
from domain.depart import Depart, DepartId
from domain.entree_audit import EntreeAudit
from domain.forfait import Forfait, NatureForfait
from domain.grain_validation import GrainValidation
from domain.inscription import Inscription, InscriptionId
from domain.paiement import RecapPaiement
from domain.phase import Phase, PhaseId, SourcePhase, TypePhase
from domain.placement import Affectation
from domain.serie import Serie, Volee
from domain.tournoi import Tournoi, TournoiId
from tests.conftest import (
    FauxDepartRepository,
    FauxForfaitRepository,
    FauxInscriptionRepository,
    FauxLecteurPopulations,
    FauxPhaseRepository,
)

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

    def par_phase(self, phase_id: PhaseId) -> list[Serie]:
        """E05US025 : le classement lit les feuilles **d'une phase**, plus celles du tournoi."""
        return [s for s in self._series if s.phase_id == phase_id]

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Serie]:
        return [s for s in self._series if s.tournoi_id == tournoi_id]

    def par_archer(self, phase_id: PhaseId, archer_id: ArcherId) -> Serie | None:
        raise NotImplementedError

    def horodatages(self, phase_id: PhaseId, archer_id: ArcherId) -> dict[int, datetime.datetime]:
        raise NotImplementedError

    def enregistrer(self, serie: Serie) -> Serie:
        raise NotImplementedError

    def enregistrer_avec_trace(self, serie: Serie, entree: EntreeAudit) -> Serie:
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


def _serie(
    archer_id: ArcherId, phase_id: int, *, volees_validees: int, nb_saisies: int | None = None
) -> Serie:
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
    return Serie(tournoi_id=1, archer_id=archer_id, phase_id=phase_id, volees=volees)


class Montage:
    """Attelage : service + repos garnis, un tournoi prêt (barème de qualification à 3 volées)."""

    def __init__(self, nb_volees_bareme: int = 3) -> None:
        self.tournois = FauxTournoiRepository()
        self.departs = FauxDepartRepository()
        self.placements = FauxPlacementRepository()
        self.inscriptions = FauxInscriptionRepository()
        self.series = FauxSerieRepository()
        self.phases = FauxPhaseRepository(self.departs)
        self.forfaits = FauxForfaitRepository()
        self.paiements = FauxLecteurPaiements()
        tournoi = self.tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
        assert tournoi.id is not None
        self.tournoi_id: TournoiId = tournoi.id
        # Le créneau qui porte la qualification (ADR-0075).
        depart = self.departs.ajouter(
            Depart.creer(tournoi_id=tournoi.id, numero=1, tarif_centimes=800, horaire="09:00")
        )
        assert depart.id is not None
        self.depart_id = depart.id
        self.nb_volees_bareme = nb_volees_bareme
        self.qualif_phase_id = 1
        if nb_volees_bareme > 0:
            import dataclasses

            self.phases.ajouter(
                dataclasses.replace(
                    Phase.qualification(
                        self.depart_id, BaremeQualification.creer(nb_volees_bareme, 3)
                    ),
                    id=self.qualif_phase_id,
                )
            )
        self._numero = 0
        # Inerte par défaut : sans population déclarée, chaque qualification prend tous les
        # archers placés — le comportement mono-qualification. Le test de la fourche la renseigne.
        self.populations = FauxLecteurPopulations()
        self.service = ServiceCompletude(
            self.tournois,
            self.departs,
            self.placements,
            self.inscriptions,
            self.series,
            self.phases,
            self.forfaits,
            self.paiements,
            self.populations,
        )

    def qualif_de(self, depart_id: DepartId) -> int:
        """La qualification de ce créneau (E05US025) — chaque créneau a la sienne."""
        phase = next(
            p for p in self.phases.par_depart(depart_id) if p.type is TypePhase.QUALIFICATION
        )
        assert phase.id is not None
        return phase.id

    def semer(
        self,
        depart_id: DepartId,
        archer_id: ArcherId,
        *,
        volees_validees: int,
        nb_saisies: int | None = None,
    ) -> None:
        """Pose la feuille de cet archer **dans la qualification de son créneau**.

        E05US025 : une feuille pend à sa phase. Les tests posaient `_serie(...)` sans dire où, ce
        qui marchait tant qu'une phase valait pour tout le tournoi ; sur deux créneaux, la feuille
        atterrissait dans la qualification du premier et le second se lisait vide.
        """
        self.series.poser(
            _serie(
                archer_id,
                self.qualif_de(depart_id),
                volees_validees=volees_validees,
                nb_saisies=nb_saisies,
            )
        )

    def creer_depart(self) -> DepartId:
        """Un créneau **et sa qualification**, comme le fait l'application d'un format.

        E05US025 : la complétude se calcule désormais **par créneau** — chacun a sa séquence
        (ADR-0075) et peut y enchaîner plusieurs qualifications (ADR-0082). Ce décor ne posait la
        qualification que sur le premier créneau, ce qui suffisait tant qu'une phase valait pour
        tout le tournoi ; les créneaux suivants seraient maintenant « en attente », sans cible à
        compter. Depuis ADR-0076 le déroulé se définit une fois et **chaque** départ l'instancie :
        le décor le reproduit.
        """
        self._numero += 1
        depart = self.departs.ajouter(
            Depart.creer(self.tournoi_id, numero=self._numero, tarif_centimes=1000, horaire="09:00")
        )
        assert depart.id is not None
        if self.nb_volees_bareme > 0:
            self.phases.ajouter(
                Phase.qualification(depart.id, BaremeQualification.creer(self.nb_volees_bareme, 3))
            )
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

    def qualification(self) -> LigneCompletude:
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
    m.semer(depart, 10, volees_validees=3)
    m.semer(depart, 11, volees_validees=3)

    qualif = m.service.pour_tournoi(m.tournoi_id).sportif[0]
    assert qualif.cle == CLE_QUALIFICATION
    assert (qualif.fait, qualif.total) == (1, 1)
    assert qualif.etat is EtatSection.OK


def test_un_archer_forfait_ne_bloque_pas_la_completude_de_sa_cible() -> None:
    """DETTE-014 résorbée (E04US015, ADR-0050) : un archer **forfait** en qualification a sa série
    **close par forfait** malgré ses volées partielles — sa cible n'est plus « à finir » à jamais.
    """
    m = Montage(nb_volees_bareme=3)
    depart = m.creer_depart()
    m.placer(depart, cible_index=1, archer_id=10, position="A")
    m.placer(depart, cible_index=1, archer_id=11, position="B")
    m.semer(depart, 10, volees_validees=3)  # fini
    m.semer(depart, 11, volees_validees=1, nb_saisies=1)  # abandon : partiel
    m.forfaits.semer(
        Forfait.creer(
            tournoi_id=m.tournoi_id,
            archer_id=11,
            phase_id=m.qualif_de(depart),
            nature=NatureForfait.ABANDON,
            declare_par="Scoreur",
            declare_le=datetime.datetime(2026, 3, 14, 10, 0, tzinfo=datetime.UTC),
        )
    )

    qualif = m.service.pour_tournoi(m.tournoi_id).sportif[0]
    assert (qualif.fait, qualif.total) == (1, 1)  # cible terminée : forfait = clos


def test_une_cible_avec_un_archer_pas_fini_n_est_pas_terminee() -> None:
    """Il suffit d'**un** archer qui n'a pas fini pour que la cible ne compte pas comme terminée."""
    m = Montage(nb_volees_bareme=3)
    depart = m.creer_depart()
    m.placer(depart, cible_index=1, archer_id=10, position="A")
    m.placer(depart, cible_index=1, archer_id=11, position="B")
    m.semer(depart, 10, volees_validees=3)  # fini
    m.semer(depart, 11, volees_validees=2, nb_saisies=3)  # 2 validées / 3 : pas fini

    qualif = m.service.pour_tournoi(m.tournoi_id).sportif[0]
    assert (qualif.fait, qualif.total) == (0, 1)
    assert qualif.etat is EtatSection.ALERTE


def test_series_saisies_mais_non_validees_ne_terminent_pas_la_cible() -> None:
    """Tout saisi mais rien validé : la cible n'est pas *close* (cohérent avec le classement)."""
    m = Montage(nb_volees_bareme=3)
    depart = m.creer_depart()
    m.placer(depart, cible_index=1, archer_id=10, position="A")
    m.semer(depart, 10, volees_validees=0, nb_saisies=3)

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
    for archer_id, creneau in ((10, d1), (11, d1), (20, d2)):
        m.semer(creneau, archer_id, volees_validees=3)
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
    m.semer(depart, 10, volees_validees=3)

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


# --- E05US025 : la fourche (correctifs de revue) ------------------------------------------------


def test_la_basse_ne_bloque_pas_les_cibles_de_la_haute() -> None:
    """CA E05US025 — « la complétude juge chaque qualification sur son propre effectif ».

    Bloquant de revue. Un premier jet ne retenait que `qualification_courante` tout en comptant
    **tous** les archers placés du créneau : sur la fourche, les archers de la *basse* n'ayant
    aucune feuille dans la *haute*, aucune cible n'était jamais terminée et « Prêt à terminer ? »
    restait rouge **pour toujours** — l'exact contraire de la fiche de recette (« un archer éliminé
    à la coupe ne bloque jamais le second tour »).

    Décor : une cible, deux archers, la qualification de tête close pour les deux, puis une *haute*
    qui ne prend que le premier et une *basse* qui ne prend que le second. Chacun a fini son propre
    second tour → la cible est terminée.
    """
    m = Montage(nb_volees_bareme=2)
    depart = m.depart_id
    m.placer(depart, cible_index=1, archer_id=10, position="A")
    m.placer(depart, cible_index=1, archer_id=11, position="B")
    m.semer(depart, 10, volees_validees=2)
    m.semer(depart, 11, volees_validees=2)
    haute, basse = _poser_la_fourche(m, depart)
    m.populations.populations = {2: [10], 3: [11]}
    m.series.poser(_serie(10, haute, volees_validees=2))
    m.series.poser(_serie(11, basse, volees_validees=2))

    ligne = m.qualification()

    assert ligne.fait == 1 and ligne.total == 1, "La cible est terminée : chacun a fini chez lui."


def test_une_seconde_qualification_inachevee_retient_la_cible() -> None:
    """Le pendant : la *haute* non close retient sa cible, même si le premier tour l'est.

    C'est la moitié du CA que le décor précédent ne prouve pas — sans elle, un service qui
    ignorerait purement et simplement les qualifications aval passerait le test d'à côté.
    """
    m = Montage(nb_volees_bareme=2)
    depart = m.depart_id
    m.placer(depart, cible_index=1, archer_id=10, position="A")
    m.placer(depart, cible_index=1, archer_id=11, position="B")
    m.semer(depart, 10, volees_validees=2)
    m.semer(depart, 11, volees_validees=2)
    haute, basse = _poser_la_fourche(m, depart)
    m.populations.populations = {2: [10], 3: [11]}
    m.series.poser(_serie(10, haute, volees_validees=1))  # une volée manque
    m.series.poser(_serie(11, basse, volees_validees=2))

    ligne = m.qualification()

    assert ligne.fait == 0 and ligne.total == 1, "Le second tour inachevé retient la cible."


def test_avancement_du_creneau_attend_les_deux_moitiés_de_la_fourche() -> None:
    """Le cycle de vie du créneau (E12US008) suit la même règle que « Prêt à terminer ? ».

    Sans cela, `nb_series_closes` n'atteignait jamais `nb_places` et le créneau ne pouvait plus se
    clore — un blocage silencieux du jour J, sur un chemin qu'aucun écran n'explique.
    """
    m = Montage(nb_volees_bareme=2)
    depart = m.depart_id
    m.placer(depart, cible_index=1, archer_id=10, position="A")
    m.placer(depart, cible_index=1, archer_id=11, position="B")
    m.semer(depart, 10, volees_validees=2)
    m.semer(depart, 11, volees_validees=2)
    haute, basse = _poser_la_fourche(m, depart)
    m.populations.populations = {2: [10], 3: [11]}
    m.series.poser(_serie(10, haute, volees_validees=2))

    partiel = m.service.avancement_depart(m.tournoi_id, depart)
    m.series.poser(_serie(11, basse, volees_validees=2))
    complet = m.service.avancement_depart(m.tournoi_id, depart)

    assert (partiel.nb_places, partiel.nb_series_closes) == (2, 1)
    assert (complet.nb_places, complet.nb_series_closes) == (2, 2)


def _poser_la_fourche(m: Montage, depart_id: DepartId) -> tuple[int, int]:
    """Ajoute une *haute* (ordre 2) et une *basse* (ordre 3) prélevées, et rend leurs id."""
    posees = []
    for ordre in (2, 3):
        phase = m.phases.ajouter(
            Phase(
                depart_id=depart_id,
                ordre=ordre,
                type=TypePhase.QUALIFICATION,
                bareme=BaremeQualification.creer(m.nb_volees_bareme, 3),
                validation=GrainValidation.fin_de_serie(),
                sources=(SourcePhase.par_rangs(1),),
            ).demarrer()
        )
        assert phase.id is not None
        posees.append(phase.id)
    return posees[0], posees[1]


def test_un_creneau_sans_qualification_scorable_n_est_pas_clos_d_office() -> None:
    """Sans barème, rien n'est validable : le créneau reste ouvert, il n'est pas « tout clos ».

    Correctif de revue : `_est_clos` rend `all([])`, donc `True`, sur un créneau sans jugement —
    `nb_series_closes` aurait égalé `nb_places` alors que personne n'a pu tirer.
    """
    m = Montage(nb_volees_bareme=0)  # aucune qualification posée
    depart = m.creer_depart()
    m.placer(depart, cible_index=1, archer_id=10, position="A")

    avancement = m.service.avancement_depart(m.tournoi_id, depart)

    assert (avancement.nb_places, avancement.nb_ayant_tire, avancement.nb_series_closes) == (
        1,
        0,
        0,
    )
