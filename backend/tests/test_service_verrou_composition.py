"""`VerrouCompositionEquipes`, la vraie classe (E13US004, CA 10, ADR-0120 §7) — dépôts factices.

Le faux de `conftest` code la règle par construction : ces tests éprouvent l'implémentation, cas
négatifs compris — un verrou qui oublierait le type ou le départ rougirait ici (relevé en revue).
"""

from __future__ import annotations

from dataclasses import replace

from application.verrou_bareme import VerrouBaremeDuel, VerrouCompositionEquipes
from domain.depart import Depart
from domain.deroule_etape import EtapeDeroule
from domain.duel import BaremeDuel, Duel, ResolveurBaremeDuelFfta
from domain.equipe import TypeEquipe
from domain.inscription import Inscription
from domain.participant import Participant
from domain.phase import TypePhase
from tests.conftest import (
    FauxDepartRepository,
    FauxDerouleRepository,
    FauxDuelRepository,
    FauxInscriptionRepository,
    FauxPhaseRepository,
)


class _Tournoi:
    """Deux départs (samedi, dimanche) rejouant les mêmes étapes, et des archers inscrits."""

    def __init__(self) -> None:
        self.departs = FauxDepartRepository()
        self.deroules = FauxDerouleRepository()
        self.phases = FauxPhaseRepository(self.departs)
        self.duels = FauxDuelRepository()
        self.inscriptions = FauxInscriptionRepository()
        self.samedi = self._depart(1)
        self.dimanche = self._depart(2)

    def _depart(self, numero: int) -> int:
        depart = self.departs.ajouter(
            Depart.creer(tournoi_id=1, numero=numero, tarif_centimes=800, horaire="09:00")
        )
        assert depart.id is not None
        return depart.id

    def etape(self, equipes: TypeEquipe | None) -> int:
        etape = self.deroules.ajouter(
            EtapeDeroule(
                tournoi_id=1,
                ordre=len(self.deroules.par_tournoi(1)) + 1,
                type=TypePhase.ELIMINATION_DIRECTE,
                equipes=equipes,
            )
        )
        assert etape.id is not None
        for depart_id in (self.samedi, self.dimanche):
            self.phases.ajouter(replace(etape.instancier(depart_id), etape_id=etape.id))
        return etape.id

    def tirer(self, etape_id: int, depart_id: int) -> None:
        (phase,) = [p for p in self.phases.par_depart(depart_id) if p.etape_id == etape_id]
        assert phase.id is not None
        self.duels.enregistrer(
            phase.id,
            1,
            Duel.vide(
                BaremeDuel.preset_ffta_classique(), Participant.equipe(1), Participant.equipe(2)
            ),
        )

    def archer(self, archer_id: int, depart_id: int) -> int:
        self.inscriptions.ajouter(Inscription(archer_id, depart_id))
        return archer_id

    def verrou(self) -> VerrouCompositionEquipes:
        bareme = VerrouBaremeDuel(
            self.departs, self.phases, self.deroules, self.duels, ResolveurBaremeDuelFfta()
        )
        return VerrouCompositionEquipes(bareme, self.deroules, self.inscriptions)


def test_un_tableau_tire_le_samedi_fige_les_equipes_du_samedi() -> None:
    tournoi = _Tournoi()
    tournoi.tirer(tournoi.etape(TypeEquipe.STANDARD), tournoi.samedi)

    assert tournoi.verrou().en_jeu(1, TypeEquipe.STANDARD, [tournoi.archer(11, tournoi.samedi)])


def test_il_ne_fige_pas_les_equipes_du_dimanche() -> None:
    tournoi = _Tournoi()
    tournoi.tirer(tournoi.etape(TypeEquipe.STANDARD), tournoi.samedi)

    assert not tournoi.verrou().en_jeu(
        1, TypeEquipe.STANDARD, [tournoi.archer(21, tournoi.dimanche)]
    )


def test_il_ne_fige_pas_un_autre_type_d_equipe() -> None:
    tournoi = _Tournoi()
    tournoi.tirer(tournoi.etape(TypeEquipe.STANDARD), tournoi.samedi)

    assert not tournoi.verrou().en_jeu(1, TypeEquipe.MIXTE, [tournoi.archer(11, tournoi.samedi)])


def test_un_tableau_individuel_tire_ne_fige_aucune_equipe() -> None:
    tournoi = _Tournoi()
    tournoi.tirer(tournoi.etape(None), tournoi.samedi)
    tournoi.etape(TypeEquipe.STANDARD)

    assert not tournoi.verrou().en_jeu(1, TypeEquipe.STANDARD, [tournoi.archer(11, tournoi.samedi)])


def test_une_equipe_sans_membre_n_est_jamais_en_jeu() -> None:
    tournoi = _Tournoi()
    tournoi.tirer(tournoi.etape(TypeEquipe.STANDARD), tournoi.samedi)

    assert not tournoi.verrou().en_jeu(1, TypeEquipe.STANDARD, [])
