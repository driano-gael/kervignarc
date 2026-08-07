"""Tests du service applicatif Phases (E05US001) — repositories factices en mémoire.

Le service est testé **en isolation** : de faux repositories conformes aux ports
`TournoiRepository` / `PhaseRepository` suffisent (ni base ni serveur). Les assertions dérivent du
CA d'E05US001 (composer / éditer / ordonner / supprimer, cycle de vie, cohérence) et d'ADR-0045.
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.erreurs import (
    PhaseIntrouvable,
    PhaseSourceReferencee,
    ReordonnancementPhasesInvalide,
    TournoiIntrouvable,
    TransitionStatutInvalide,
)
from application.phases import ServicePhases
from domain.depart import Depart
from domain.erreurs import EffectifIncompatible, SourceApresPhase
from domain.phase import Phase, SourcePhase, StatutPhase, TypePhase
from domain.tournoi import Tournoi, TournoiId, TypeTournoi
from tests.conftest import (
    FauxDepartRepository,
    FauxDerouleRepository,
    FauxPhaseRepository,
    poser_phase_factice,
)

_DATE = datetime.date(2026, 3, 14)
_DEPART = 500
"""Identifiant du créneau du décor, **distinct** de celui du tournoi (1) : c'est ce qui fait
tomber un test qui confondrait les deux mailles."""


class FauxTournoiRepository:
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


def _service() -> tuple[ServicePhases, int]:
    """Le décor de composition — maille **tournoi**. Rend `(service, tournoi_id)`.

    ⚠️ **Le créneau porte un identifiant volontairement distinct** (`_DEPART`). Les doublures
    partent toutes de `_sequence = 0` : sans cette désynchronisation, `tournoi.id == depart.id == 1`
    et un test qui passe l'un pour l'autre reste **vert par coïncidence numérique**. C'est
    exactement `DETTE-044` (`TournoiId` et `DepartId` sont le même type pour mypy) reproduite dans
    les tests censés garder la correction qui la combat — le défaut a été relevé en revue sur les
    cinq tests de cycle de vie de ce fichier.
    """
    tournois = FauxTournoiRepository()
    tournoi = tournois.ajouter(
        Tournoi(nom="Kervignarc", date=_DATE, lieu=None, type_tournoi=TypeTournoi.NON_OFFICIEL)
    )
    assert tournoi.id is not None
    departs = FauxDepartRepository()
    depart = departs.ajouter(
        dataclasses.replace(
            Depart.creer(tournoi_id=tournoi.id, numero=1, tarif_centimes=800, horaire="09:00"),
            id=_DEPART,
        )
    )
    assert depart.id is not None
    deroules = FauxDerouleRepository()
    # `deroules` est **câblé** à la doublure de phases : sans lui elle reste en « mode indulgent »
    # et rend les phases telles qu'elles ont été posées — les tests de service ne franchiraient
    # jamais la couture d'assemblage, celle-là même qu'ADR-0076 introduit.
    phases = FauxPhaseRepository(departs, deroules)
    return ServicePhases(tournois, phases, departs, deroules), tournoi.id


def _service_avec_creneau() -> tuple[ServicePhases, int, int]:
    """Idem, plus l'identifiant du créneau — pour la maille **pilotage** (cycle de vie)."""
    service, tournoi_id = _service()
    return service, tournoi_id, _DEPART


def _phase_du_creneau(service: ServicePhases, depart_id: int, ordre: int = 1) -> int:
    """L'identifiant de l'**avancement** de rang `ordre` dans ce créneau.

    Le cycle de vie s'adresse à une **phase**, pas à une étape (ADR-0076) : `ServicePhases.ajouter`
    rend une `EtapeDeroule`, dont l'`id` n'a rien à voir. Les relire ici évite de reconduire la
    confusion que ce fichier vient de fermer.
    """
    phase = next(p for p in service.avancement(depart_id) if p.ordre == ordre)
    assert phase.id is not None
    return phase.id


# --- Lister / ajouter --------------------------------------------------------------------------


def test_un_tournoi_neuf_n_a_aucune_phase() -> None:
    service, tournoi_id = _service()
    assert service.lister(tournoi_id) == []


def test_lister_leve_si_tournoi_inconnu() -> None:
    service, _ = _service()
    with pytest.raises(TournoiIntrouvable):
        service.lister(404)


def test_ajouter_empile_les_phases_en_ordre() -> None:
    """Chaque ajout prend le rang suivant (1, 2, 3…)."""
    service, tournoi_id = _service()
    p1 = service.ajouter(tournoi_id, TypePhase.ELIMINATION_DIRECTE)
    p2 = service.ajouter(tournoi_id, TypePhase.PLACEMENT)

    assert (p1.ordre, p2.ordre) == (1, 2)
    assert [p.id for p in service.lister(tournoi_id)] == [p1.id, p2.id]


def test_ajouter_leve_si_tournoi_inconnu() -> None:
    service, _ = _service()
    with pytest.raises(TournoiIntrouvable):
        service.ajouter(404, TypePhase.ELIMINATION_DIRECTE)


def test_ajouter_une_phase_avec_source_incoherente_ne_persiste_rien() -> None:
    """Une source qui vise une phase postérieure est rejetée (cohérence de séquence, 422)."""
    service, tournoi_id = _service()
    service.ajouter(tournoi_id, TypePhase.ELIMINATION_DIRECTE)  # ordre 1
    with pytest.raises(SourceApresPhase):
        service.ajouter(
            tournoi_id,
            TypePhase.PLACEMENT,
            sources=(
                SourcePhase(ordre_source=2, rang_debut=1, rang_fin=8),
            ),  # se référence lui-même
        )
    assert len(service.lister(tournoi_id)) == 1  # rien ajouté


# --- Modifier ----------------------------------------------------------------------------------


def test_modifier_change_type_source_effectif() -> None:
    service, tournoi_id = _service()
    p1 = service.ajouter(tournoi_id, TypePhase.PLACEMENT, effectif=40)
    p2 = service.ajouter(tournoi_id, TypePhase.PLACEMENT)
    assert p2.id is not None

    modifiee = service.modifier(
        tournoi_id,
        p2.id,
        type=TypePhase.ELIMINATION_DIRECTE,
        sources=(SourcePhase(ordre_source=1, rang_debut=1, rang_fin=16),),
        effectif=16,
    )

    assert modifiee.type is TypePhase.ELIMINATION_DIRECTE
    assert modifiee.effectif == 16
    assert modifiee.sources == (SourcePhase(ordre_source=1, rang_debut=1, rang_fin=16),)
    assert modifiee.ordre == 2  # préservé
    _ = p1


def test_modifier_effectif_incompatible_est_refuse() -> None:
    service, tournoi_id = _service()
    service.ajouter(tournoi_id, TypePhase.PLACEMENT, effectif=40)
    p2 = service.ajouter(tournoi_id, TypePhase.ELIMINATION_DIRECTE)
    assert p2.id is not None

    with pytest.raises(EffectifIncompatible):
        service.modifier(
            tournoi_id,
            p2.id,
            type=TypePhase.ELIMINATION_DIRECTE,
            sources=(SourcePhase(ordre_source=1, rang_debut=1, rang_fin=8),),  # 8 prélevés
            effectif=16,  # mais 16 attendus
        )


def test_modifier_leve_si_phase_d_un_autre_tournoi() -> None:
    service, tournoi_id = _service()
    with pytest.raises(PhaseIntrouvable):
        service.modifier(tournoi_id, 999, type=TypePhase.PLACEMENT, sources=(), effectif=None)


# --- Réordonner --------------------------------------------------------------------------------


def test_reordonner_reassigne_les_ordres() -> None:
    service, tournoi_id = _service()
    p1 = service.ajouter(tournoi_id, TypePhase.ELIMINATION_DIRECTE)
    p2 = service.ajouter(tournoi_id, TypePhase.PLACEMENT)
    assert p1.id is not None and p2.id is not None

    reordonnees = service.reordonner(tournoi_id, [p2.id, p1.id])

    ordres = {p.id: p.ordre for p in reordonnees}
    assert ordres == {p2.id: 1, p1.id: 2}


def test_reordonner_remappe_les_sources() -> None:
    """La source suit la phase qu'elle désignait, même après permutation (DETTE-015)."""
    service, tournoi_id = _service()
    a = service.ajouter(tournoi_id, TypePhase.PLACEMENT, effectif=40)  # ordre 1
    b = service.ajouter(tournoi_id, TypePhase.PLACEMENT)  # ordre 2
    assert b.id is not None
    # b tire des 16 premiers de a.
    service.modifier(
        tournoi_id,
        b.id,
        type=TypePhase.ELIMINATION_DIRECTE,
        sources=(SourcePhase(ordre_source=1, rang_debut=1, rang_fin=16),),
        effectif=16,
    )
    assert a.id is not None
    # On insère une nouvelle phase, puis on réordonne a, b, c → c, a, b : a passe en 2, b en 3.
    c = service.ajouter(tournoi_id, TypePhase.PLACEMENT)
    assert c.id is not None

    reordonnees = service.reordonner(tournoi_id, [c.id, a.id, b.id])

    par_id = {p.id: p for p in reordonnees}
    assert par_id[a.id].ordre == 2
    assert par_id[b.id].ordre == 3
    # La source de b désigne toujours a — désormais en ordre 2.
    assert par_id[b.id].sources == (SourcePhase(ordre_source=2, rang_debut=1, rang_fin=16),)


def test_reordonner_qui_place_la_source_apres_la_consommatrice_est_refuse() -> None:
    service, tournoi_id = _service()
    a = service.ajouter(tournoi_id, TypePhase.PLACEMENT, effectif=40)
    b = service.ajouter(tournoi_id, TypePhase.PLACEMENT)
    assert a.id is not None and b.id is not None
    service.modifier(
        tournoi_id,
        b.id,
        type=TypePhase.ELIMINATION_DIRECTE,
        sources=(SourcePhase(ordre_source=1, rang_debut=1, rang_fin=16),),
        effectif=16,
    )

    # Inverser met la source (a) après la consommatrice (b) → incohérent.
    with pytest.raises(SourceApresPhase):
        service.reordonner(tournoi_id, [b.id, a.id])


def test_reordonner_liste_incomplete_est_refuse() -> None:
    service, tournoi_id = _service()
    p1 = service.ajouter(tournoi_id, TypePhase.ELIMINATION_DIRECTE)
    service.ajouter(tournoi_id, TypePhase.PLACEMENT)
    assert p1.id is not None

    with pytest.raises(ReordonnancementPhasesInvalide):
        service.reordonner(tournoi_id, [p1.id])  # une seule sur deux


# --- Supprimer ---------------------------------------------------------------------------------


def test_supprimer_retire_et_recompacte_les_ordres() -> None:
    service, tournoi_id = _service()
    p1 = service.ajouter(tournoi_id, TypePhase.ELIMINATION_DIRECTE)
    p2 = service.ajouter(tournoi_id, TypePhase.PLACEMENT)
    p3 = service.ajouter(tournoi_id, TypePhase.PLACEMENT)
    assert p1.id is not None

    service.supprimer(tournoi_id, p1.id)

    restantes = service.lister(tournoi_id)
    assert [p.id for p in restantes] == [p2.id, p3.id]
    assert [p.ordre for p in restantes] == [1, 2]  # recompacté


def test_supprimer_une_phase_source_d_une_autre_est_refuse() -> None:
    service, tournoi_id = _service()
    a = service.ajouter(tournoi_id, TypePhase.PLACEMENT, effectif=40)
    b = service.ajouter(tournoi_id, TypePhase.PLACEMENT)
    assert a.id is not None and b.id is not None
    service.modifier(
        tournoi_id,
        b.id,
        type=TypePhase.ELIMINATION_DIRECTE,
        sources=(SourcePhase(ordre_source=1, rang_debut=1, rang_fin=16),),
        effectif=16,
    )

    with pytest.raises(PhaseSourceReferencee):
        service.supprimer(tournoi_id, a.id)  # a alimente b


def test_supprimer_recompacte_et_remappe_la_source_restante() -> None:
    """Retirer une phase avant une source décale l'ancre de celle-ci d'un cran (DETTE-015)."""
    service, tournoi_id = _service()
    filler = service.ajouter(tournoi_id, TypePhase.PLACEMENT)  # ordre 1, sans source
    a = service.ajouter(tournoi_id, TypePhase.PLACEMENT, effectif=40)  # ordre 2
    b = service.ajouter(tournoi_id, TypePhase.PLACEMENT)  # ordre 3
    assert filler.id is not None and a.id is not None and b.id is not None
    service.modifier(
        tournoi_id,
        b.id,
        type=TypePhase.ELIMINATION_DIRECTE,
        sources=(SourcePhase(ordre_source=2, rang_debut=1, rang_fin=16),),  # b ← a (ordre 2)
        effectif=16,
    )

    service.supprimer(tournoi_id, filler.id)  # tout remonte d'un cran

    par_id = {p.id: p for p in service.lister(tournoi_id)}
    assert par_id[a.id].ordre == 1
    assert par_id[b.id].ordre == 2
    assert par_id[b.id].sources == (SourcePhase(ordre_source=1, rang_debut=1, rang_fin=16),)


def test_supprimer_leve_si_phase_inconnue() -> None:
    service, tournoi_id = _service()
    with pytest.raises(PhaseIntrouvable):
        service.supprimer(tournoi_id, 999)


def test_supprimer_la_qualification_est_refuse() -> None:
    """Garde en profondeur (revue axe D) : la qualification se gère via le barème, pas ici — la
    retirer par cet écran l'orphelinerait (barème sans phase porteuse).

    ⚠️ On supprime une **étape du déroulé du tournoi** (ADR-0076), pas une phase d'un créneau : la
    composition se fait à l'atelier, et retirer l'étape retirerait l'avancement de *tous* les
    créneaux d'un coup — raison de plus pour que la garde tienne.
    """
    from application.erreurs import PhaseQualificationNonSupprimable
    from domain.bareme import BaremeQualification

    tournois = FauxTournoiRepository()
    tournoi = tournois.ajouter(
        Tournoi(nom="Kervignarc", date=_DATE, lieu=None, type_tournoi=TypeTournoi.NON_OFFICIEL)
    )
    assert tournoi.id is not None
    departs = FauxDepartRepository()
    depart = departs.ajouter(
        Depart.creer(tournoi_id=tournoi.id, numero=1, tarif_centimes=800, horaire="09:00")
    )
    assert depart.id is not None
    phases = FauxPhaseRepository(departs)
    deroules = FauxDerouleRepository()
    service = ServicePhases(tournois, phases, departs, deroules)
    poser_phase_factice(
        departs,
        deroules,
        phases,
        Phase.qualification(depart.id, BaremeQualification.preset_ffta_18m()),
    )
    (etape,) = deroules.par_tournoi(tournoi.id)
    assert etape.id is not None

    with pytest.raises(PhaseQualificationNonSupprimable):
        service.supprimer(tournoi.id, etape.id)


def test_reordonner_leve_si_tournoi_inconnu() -> None:
    service, _ = _service()
    with pytest.raises(TournoiIntrouvable):
        service.reordonner(404, [1, 2])


# --- Cycle de vie ------------------------------------------------------------------------------


def test_cycle_de_vie_nominal() -> None:
    service, tournoi_id, depart_id = _service_avec_creneau()
    service.ajouter(tournoi_id, TypePhase.ELIMINATION_DIRECTE)
    phase_id = _phase_du_creneau(service, depart_id)

    assert service.demarrer(depart_id, phase_id).statut is StatutPhase.EN_COURS
    assert service.mettre_en_pause(depart_id, phase_id).statut is StatutPhase.EN_PAUSE
    assert service.reprendre(depart_id, phase_id).statut is StatutPhase.EN_COURS
    assert service.terminer(depart_id, phase_id).statut is StatutPhase.TERMINEE


def test_demarrer_une_phase_deja_en_cours_est_refuse() -> None:
    service, tournoi_id, depart_id = _service_avec_creneau()
    service.ajouter(tournoi_id, TypePhase.ELIMINATION_DIRECTE)
    phase_id = _phase_du_creneau(service, depart_id)
    service.demarrer(depart_id, phase_id)

    with pytest.raises(TransitionStatutInvalide):
        service.demarrer(depart_id, phase_id)


def test_mettre_en_pause_une_phase_a_venir_est_refuse() -> None:
    service, tournoi_id, depart_id = _service_avec_creneau()
    service.ajouter(tournoi_id, TypePhase.ELIMINATION_DIRECTE)
    phase_id = _phase_du_creneau(service, depart_id)

    with pytest.raises(TransitionStatutInvalide):
        service.mettre_en_pause(depart_id, phase_id)


def test_terminer_une_phase_non_en_cours_est_refuse() -> None:
    service, tournoi_id, depart_id = _service_avec_creneau()
    service.ajouter(tournoi_id, TypePhase.ELIMINATION_DIRECTE)
    phase_id = _phase_du_creneau(service, depart_id)

    with pytest.raises(TransitionStatutInvalide):
        service.terminer(depart_id, phase_id)


def test_transition_leve_si_phase_hors_du_creneau() -> None:
    """Garde d'autorisation : un identifiant de phase étranger au créneau est refusé.

    Renommé — l'ancien nom parlait d'« un autre tournoi », mais la garde porte désormais sur le
    **créneau** (`phase_du_depart`), qui est la maille du cycle de vie (ADR-0076).
    """
    service, _, depart_id = _service_avec_creneau()
    with pytest.raises(PhaseIntrouvable):
        service.demarrer(depart_id, 999)
