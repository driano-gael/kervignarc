"""Tests du service applicatif Grain de validation (E01US015, `D-11`) — repositories factices.

Le service est testé **en isolation** : de faux repositories en mémoire (conformes aux ports
`TournoiRepository` / `PhaseRepository`) suffisent — ni base ni serveur.
"""

from __future__ import annotations

import dataclasses
import datetime
from dataclasses import dataclass

import pytest

from application.bareme_qualification import ServiceBaremeQualification
from application.erreurs import PhaseQualificationAbsente, TournoiIntrouvable
from application.grain_validation import ServiceGrainValidation
from domain.bareme import BaremeQualification
from domain.depart import Depart
from domain.erreurs import (
    CadenceValidationSuperieureAuBareme,
    GrainIncompatibleAvecTypePhase,
    NombreVoleesParValidationInvalide,
    NombreVoleesParValidationManquant,
)
from domain.grain_validation import GrainValidation, TypeGrain
from domain.phase import Phase, TypePhase
from domain.tournoi import Tournoi, TournoiId, TypeTournoi
from tests.conftest import (
    FauxDepartRepository,
    FauxDerouleRepository,
    FauxPhaseRepository,
    poser_phase_factice,
)

_DATE = datetime.date(2026, 3, 14)


class FauxTournoiRepository:
    """Repository de tournois minimal (seul `par_id` est exercé par ce service)."""

    def __init__(self) -> None:
        self._tournois: dict[int, Tournoi] = {}
        self._sequence = 0

    def ajouter(self, tournoi: Tournoi) -> Tournoi:
        self._sequence += 1
        persiste = dataclasses.replace(tournoi, id=self._sequence)
        self._tournois[self._sequence] = persiste
        return persiste

    def par_id(self, tournoi_id: TournoiId) -> Tournoi | None:
        return self._tournois.get(tournoi_id)

    def lister(self) -> list[Tournoi]:
        return list(self._tournois.values())

    def enregistrer(self, tournoi: Tournoi) -> Tournoi:
        assert tournoi.id is not None
        self._tournois[tournoi.id] = tournoi
        return tournoi

    def supprimer(self, tournoi_id: TournoiId) -> None:
        del self._tournois[tournoi_id]


@dataclass
class _Decor:
    """Le décor partagé : un tournoi, son créneau, et **le même déroulé** vu par tous les services.

    ⚠️ Depuis ADR-0076, le grain vit sur l'`EtapeDeroule`. Deux services qui règlent « la même »
    qualification doivent donc partager le **magasin de déroulé** — leur donner chacun le sien les
    ferait travailler sur deux tournois qui n'ont de commun que leur identifiant, et le test le plus
    important du fichier (l'invariant grain ↔ barème de bout en bout) passerait au vert sans rien
    éprouver.
    """

    service: ServiceGrainValidation
    tournois: FauxTournoiRepository
    departs: FauxDepartRepository
    deroules: FauxDerouleRepository
    phases: FauxPhaseRepository
    tournoi_id: int
    depart_id: int


def _decor() -> _Decor:
    """Un tournoi **et son créneau** : le grain se règle sur la qualification, qui se joue dans un
    créneau (ADR-0075) — un tournoi sans départ n'a rien à valider."""
    tournois = FauxTournoiRepository()
    departs = FauxDepartRepository()
    deroules = FauxDerouleRepository()
    phases = FauxPhaseRepository(departs, deroules)
    tournoi = tournois.ajouter(
        Tournoi(nom="Kervignarc", date=_DATE, lieu=None, type_tournoi=TypeTournoi.NON_OFFICIEL)
    )
    assert tournoi.id is not None
    depart = departs.ajouter(
        Depart.creer(tournoi_id=tournoi.id, numero=1, tarif_centimes=800, horaire="09:00")
    )
    assert depart.id is not None
    return _Decor(
        service=ServiceGrainValidation(tournois, deroules),
        tournois=tournois,
        departs=departs,
        deroules=deroules,
        phases=phases,
        tournoi_id=tournoi.id,
        depart_id=depart.id,
    )


def _contexte() -> tuple[ServiceGrainValidation, FauxPhaseRepository, int, int]:
    decor = _decor()
    return decor.service, decor.phases, decor.tournoi_id, decor.depart_id


def _poser_qualification(decor: _Decor, bareme: BaremeQualification) -> None:
    """Pose l'étape de qualification **et** son avancement dans le créneau (ADR-0076)."""
    poser_phase_factice(
        decor.departs, decor.deroules, decor.phases, Phase.qualification(decor.depart_id, bareme)
    )


def _avec_qualification(nb_volees: int = 20) -> tuple[ServiceGrainValidation, int, int]:
    """Un tournoi dont le barème de qualification est déjà défini (donc l'étape existe)."""
    decor = _decor()
    _poser_qualification(decor, BaremeQualification.creer(nb_volees, 3))
    return decor.service, decor.tournoi_id, decor.depart_id


def test_grain_absent_tant_que_la_qualification_nexiste_pas() -> None:
    """Sans barème défini, il n'y a pas de phase — donc pas de grain à lire (`null`, pas 404)."""
    service, _, tournoi_id, depart_id = _contexte()

    assert service.grain_du_tournoi(tournoi_id) is None


def test_grain_du_tournoi_leve_si_tournoi_inconnu() -> None:
    service, _, _, _ = _contexte()

    with pytest.raises(TournoiIntrouvable):
        service.grain_du_tournoi(404)


def test_une_qualification_neuve_vaut_fin_de_serie() -> None:
    """Le preset du type s'applique dès la création de la phase (`D-11`)."""
    service, tournoi_id, depart_id = _avec_qualification()

    assert service.grain_du_tournoi(tournoi_id) == GrainValidation.fin_de_serie()


def test_definir_met_a_jour_le_grain() -> None:
    service, tournoi_id, depart_id = _avec_qualification()

    grain = service.definir(tournoi_id, TypeGrain.TOUTES_LES_N_VOLEES, 2)

    assert grain == GrainValidation.toutes_les_n_volees(2)
    assert service.grain_du_tournoi(tournoi_id) == grain


def test_definir_revient_a_fin_de_serie() -> None:
    """Le grain est modifiable dans les deux sens (`D-11` : réglé une fois, mais ajustable)."""
    service, tournoi_id, depart_id = _avec_qualification()
    service.definir(tournoi_id, TypeGrain.TOUTES_LES_N_VOLEES, 2)

    grain = service.definir(tournoi_id, TypeGrain.FIN_DE_SERIE, None)

    assert grain == GrainValidation.fin_de_serie()
    assert grain.n_volees is None


def test_definir_preserve_le_bareme() -> None:
    """Régler le grain ne touche pas à l'autre politique de la même phase."""
    decor = _decor()
    _poser_qualification(decor, BaremeQualification.creer(12, 6))
    service, phases, tournoi_id, depart_id = (
        decor.service,
        decor.phases,
        decor.tournoi_id,
        decor.depart_id,
    )

    service.definir(tournoi_id, TypeGrain.TOUTES_LES_N_VOLEES, 3)

    phase = phases.par_depart_et_type(depart_id, TypePhase.QUALIFICATION)
    assert phase is not None and phase.bareme is not None
    assert (phase.bareme.nb_volees, phase.bareme.nb_fleches_par_volee) == (12, 6)


def test_definir_leve_si_tournoi_inconnu() -> None:
    service, _, _, _ = _contexte()

    with pytest.raises(TournoiIntrouvable):
        service.definir(404, TypeGrain.FIN_DE_SERIE, None)


def test_definir_leve_si_le_bareme_nest_pas_encore_defini() -> None:
    """Le grain ne **crée pas** la phase : il refuse plutôt que d'inventer un barème (E01US015)."""
    service, _, tournoi_id, depart_id = _contexte()

    with pytest.raises(PhaseQualificationAbsente):
        service.definir(tournoi_id, TypeGrain.FIN_DE_SERIE, None)


def test_definir_refuse_fin_de_duel_sur_une_qualification() -> None:
    service, tournoi_id, depart_id = _avec_qualification()

    with pytest.raises(GrainIncompatibleAvecTypePhase):
        service.definir(tournoi_id, TypeGrain.FIN_DE_DUEL, None)
    assert service.grain_du_tournoi(tournoi_id) == GrainValidation.fin_de_serie()


def test_definir_refuse_une_cadence_manquante() -> None:
    service, tournoi_id, depart_id = _avec_qualification()

    with pytest.raises(NombreVoleesParValidationManquant):
        service.definir(tournoi_id, TypeGrain.TOUTES_LES_N_VOLEES, None)


def test_definir_refuse_une_cadence_invalide() -> None:
    service, tournoi_id, depart_id = _avec_qualification()

    with pytest.raises(NombreVoleesParValidationInvalide):
        service.definir(tournoi_id, TypeGrain.TOUTES_LES_N_VOLEES, 0)


def test_definir_refuse_une_cadence_au_dela_du_bareme() -> None:
    """Valider toutes les 30 volées d'une qualification de 20, c'est ne jamais valider."""
    service, tournoi_id, depart_id = _avec_qualification(nb_volees=20)

    with pytest.raises(CadenceValidationSuperieureAuBareme):
        service.definir(tournoi_id, TypeGrain.TOUTES_LES_N_VOLEES, 30)
    assert service.grain_du_tournoi(tournoi_id) == GrainValidation.fin_de_serie()


def test_reduire_le_bareme_sous_la_cadence_est_refuse_de_bout_en_bout() -> None:
    """Les deux services partagent la phase : l'invariant tient aussi depuis le barème (E01US009).

    C'est la contrepartie assumée de l'invariant — l'admin doit élargir son grain d'abord.
    """
    decor = _decor()
    # **Le même magasin de déroulé** pour les deux services : c'est là que vivent barème et grain
    # depuis ADR-0076, donc c'est lui, et non le magasin de phases, qui les fait « partager la
    # qualification ».
    baremes = ServiceBaremeQualification(
        decor.tournois, decor.phases, decor.departs, decor.deroules
    )
    grains = decor.service
    baremes.definir(decor.tournoi_id, 20, 3)
    grains.definir(decor.tournoi_id, TypeGrain.TOUTES_LES_N_VOLEES, 10)

    with pytest.raises(CadenceValidationSuperieureAuBareme):
        baremes.definir(decor.tournoi_id, 5, 3)

    # Rien n'a bougé : ni le barème, ni le grain.
    bareme = baremes.bareme_du_tournoi(decor.tournoi_id)
    assert bareme is not None and bareme.nb_volees == 20
    assert grains.grain_du_tournoi(decor.tournoi_id) == GrainValidation.toutes_les_n_volees(10)
