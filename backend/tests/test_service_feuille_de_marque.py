"""Tests du service Feuille de marque (E09US001) — dérivés du CA, avant implémentation (règle 9).

Le CA (`stories/E09-exports.md`, E09US001) tient en deux exigences vérifiables ici :

- **feuille par cible/archer avec zones de scores** : une entrée par archer **placé**, portant sa
  cible, sa position, son identité, sa catégorie et son blason ; la grille de scores (volées et
  flèches par volée) **dérive du barème** du tournoi, pas d'une constante ;
- **conforme aux données** : ce sont les vraies valeurs (nom du tournoi, numéro de départ, plan
  persisté) qui remplissent la feuille — la réserve (archer non placé) n'y figure pas.

Le rendu PDF lui-même est un adapter (testé à part, `test_feuille_de_marque_reportlab.py`) : ici on
substitue un **faux générateur** qui capture la `FeuilleDeMarque` composée, seule chose que le
service décide. Les gardes 404 (`TournoiIntrouvable`, `DepartIntrouvable`) reprennent le contrat de
`ServicePlacement` (même couple tournoi/départ).
"""

from __future__ import annotations

import dataclasses
import datetime
from collections.abc import Sequence

import pytest

from application.erreurs import DepartIntrouvable, TournoiIntrouvable
from application.feuille_de_marque import ServiceFeuilleDeMarque
from domain.archer import Archer
from domain.bareme import BaremeQualification
from domain.blason import Blason, BlasonId
from domain.categorie import Categorie
from domain.depart import Depart, DepartId
from domain.feuille_marque import FeuilleDeMarque
from domain.inscription import Inscription
from domain.phase import Phase, PhaseId, TypePhase
from domain.placement import Affectation
from domain.tournoi import Tournoi, TournoiId
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxDepartRepository,
    FauxInscriptionRepository,
)

# --- Fakes locaux (patron des autres tests de service) -----------------------------------------


class FauxTournoiRepository:
    """Repository de tournois en mémoire (seul `par_id` est exercé ici)."""

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


class FauxBlasonRepository:
    """Repository de blasons en mémoire (seul `par_id` sert ici)."""

    def __init__(self) -> None:
        self._blasons: dict[int, Blason] = {}
        self._sequence = 0

    def ajouter(self, blason: Blason) -> Blason:
        self._sequence += 1
        persiste = dataclasses.replace(blason, id=self._sequence)
        self._blasons[self._sequence] = persiste
        return persiste

    def par_id(self, blason_id: BlasonId) -> Blason | None:
        return self._blasons.get(blason_id)

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Blason]:
        return [b for b in self._blasons.values() if b.tournoi_id == tournoi_id]

    def enregistrer(self, blason: Blason) -> Blason:
        assert blason.id in self._blasons
        self._blasons[blason.id] = blason
        return blason

    def supprimer(self, blason_id: BlasonId) -> None:
        del self._blasons[blason_id]


class FauxPlacementRepository:
    """Repository de placement en mémoire (le service ne lit que `par_depart`)."""

    def __init__(self) -> None:
        self._affectation: dict[int, Affectation] = {}
        self._depart: dict[int, int] = {}

    def par_depart(self, depart_id: DepartId) -> list[Affectation]:
        # Volontairement **non trié** : c'est le service qui doit ordonner (cible, position).
        return [a for i, a in self._affectation.items() if self._depart[i] == depart_id]

    def definir_plan(self, depart_id: DepartId, affectations: Sequence[Affectation]) -> None:
        self.poser_plusieurs(depart_id, affectations)

    def poser_plusieurs(self, depart_id: DepartId, affectations: Sequence[Affectation]) -> None:
        for affectation in affectations:
            self._affectation[affectation.inscription_id] = affectation
            self._depart[affectation.inscription_id] = depart_id

    def retirer(self, inscription_id: int) -> None:
        self._affectation.pop(inscription_id, None)
        self._depart.pop(inscription_id, None)


class FauxPhaseRepository:
    """Repository de phases en mémoire (barème via `par_tournoi_et_type`)."""

    def __init__(self) -> None:
        self._phases: dict[int, Phase] = {}
        self._sequence = 0

    def ajouter(self, phase: Phase) -> Phase:
        self._sequence += 1
        persiste = dataclasses.replace(phase, id=self._sequence)
        self._phases[self._sequence] = persiste
        return persiste

    def par_id(self, phase_id: PhaseId) -> Phase | None:
        return self._phases.get(phase_id)

    def par_tournoi_et_type(self, tournoi_id: TournoiId, type_phase: TypePhase) -> Phase | None:
        trouvees = [
            p for p in self._phases.values() if p.tournoi_id == tournoi_id and p.type is type_phase
        ]
        return trouvees[-1] if trouvees else None

    def enregistrer(self, phase: Phase) -> Phase:
        assert phase.id in self._phases
        self._phases[phase.id] = phase
        return phase


class FauxGenerateur:
    """Capture la `FeuilleDeMarque` composée et renvoie des octets sentinelles.

    Le service ne connaît que le port (rendre une feuille en octets) : ce faux prouve *quelle*
    feuille est composée, sans dépendre de ReportLab (adapter testé à part)."""

    SENTINELLE = b"%PDF-feuille-de-marque"

    def __init__(self) -> None:
        self.derniere: FeuilleDeMarque | None = None

    def generer(self, feuille: FeuilleDeMarque) -> bytes:
        self.derniere = feuille
        return self.SENTINELLE


# --- Décor -------------------------------------------------------------------------------------

# Barème par défaut **non-FFTA** (4 volées de 6) : prouve que la grille suit le barème du tournoi,
# pas une constante. Au niveau module (et non en défaut d'argument) — B008.
_BAREME_DEFAUT = BaremeQualification.creer(4, 6)


@dataclasses.dataclass
class _Monde:
    service: ServiceFeuilleDeMarque
    generateur: FauxGenerateur
    archers: FauxArcherRepository
    inscriptions: FauxInscriptionRepository
    placements: FauxPlacementRepository
    tournoi_id: int
    depart_id: int
    categorie_id: int

    def placer(self, nom: str, prenom: str, cible_index: int, position: str) -> None:
        """Inscrit un archer sur le départ **et** le pose sur le plan (cible/position)."""
        archer = self.archers.ajouter(Archer.creer(nom, prenom, self.tournoi_id, self.categorie_id))
        assert archer.id is not None
        inscription = self.inscriptions.ajouter(Inscription.creer(archer.id, self.depart_id))
        assert inscription.id is not None
        self.placements.poser_plusieurs(
            self.depart_id,
            [
                Affectation(
                    inscription_id=inscription.id, cible_index=cible_index, position=position
                )
            ],
        )

    def inscrire_sans_placer(self, nom: str, prenom: str) -> None:
        """Inscrit un archer sur le départ **sans** le poser : il reste en réserve."""
        archer = self.archers.ajouter(Archer.creer(nom, prenom, self.tournoi_id, self.categorie_id))
        assert archer.id is not None
        self.inscriptions.ajouter(Inscription.creer(archer.id, self.depart_id))


def _monde(*, avec_bareme: BaremeQualification | None = _BAREME_DEFAUT) -> _Monde:
    """Un tournoi peuplé : une catégorie (blason « Blason 40 »), prêt à recevoir des archers.

    `avec_bareme` par défaut = `_BAREME_DEFAUT` (4 volées de 6). `avec_bareme=None` = pas de phase
    de qualification (le service doit alors replier sur le preset FFTA).
    """
    tournois = FauxTournoiRepository()
    departs = FauxDepartRepository()
    placements = FauxPlacementRepository()
    inscriptions = FauxInscriptionRepository()
    archers = FauxArcherRepository()
    categories = FauxCategorieRepository()
    blasons = FauxBlasonRepository()
    phases = FauxPhaseRepository()
    generateur = FauxGenerateur()

    tournoi = tournois.ajouter(Tournoi.creer("Tournoi Test", datetime.date(2026, 1, 18)))
    assert tournoi.id is not None
    if avec_bareme is not None:
        phases.ajouter(Phase.qualification(tournoi.id, avec_bareme))
    depart = departs.ajouter(Depart.creer(tournoi.id, numero=1, tarif_centimes=800))
    assert depart.id is not None
    blason = blasons.ajouter(
        Blason.creer(tournoi.id, "Blason 40", taille=1.0, capacite=1, zones=None)
    )
    categorie = categories.ajouter(Categorie.creer(tournoi.id, "Sénior Homme", blason_id=blason.id))
    assert categorie.id is not None

    service = ServiceFeuilleDeMarque(
        tournois,
        departs,
        placements,
        inscriptions,
        archers,
        categories,
        blasons,
        phases,
        generateur,
    )
    return _Monde(
        service=service,
        generateur=generateur,
        archers=archers,
        inscriptions=inscriptions,
        placements=placements,
        tournoi_id=tournoi.id,
        depart_id=depart.id,
        categorie_id=categorie.id,
    )


# --- Tests -------------------------------------------------------------------------------------


def test_feuille_conforme_aux_donnees() -> None:
    """En-tête (tournoi, départ) et grille (barème) sont ceux des données ; un archer placé = une
    ligne exacte (cible, position, identité, catégorie, blason)."""
    monde = _monde()
    monde.placer("Durand", "Marie", cible_index=1, position="A")

    octets = monde.service.generer(monde.tournoi_id, monde.depart_id)

    assert octets == FauxGenerateur.SENTINELLE
    feuille = monde.generateur.derniere
    assert feuille is not None
    assert feuille.tournoi == "Tournoi Test"
    assert feuille.depart_numero == 1
    assert (feuille.nb_volees, feuille.nb_fleches_par_volee) == (4, 6)
    assert len(feuille.archers) == 1
    ligne = feuille.archers[0]
    assert (ligne.nom, ligne.prenom) == ("Durand", "Marie")
    assert (ligne.cible_index, ligne.position) == (1, "A")
    assert ligne.categorie == "Sénior Homme"
    assert ligne.blason == "Blason 40"


def test_reserve_absente_de_la_feuille() -> None:
    """Un archer inscrit mais **non placé** (réserve) ne tire pas : pas de feuille pour lui."""
    monde = _monde()
    monde.placer("Durand", "Marie", cible_index=1, position="A")
    monde.inscrire_sans_placer("Enréserve", "Paul")

    monde.service.generer(monde.tournoi_id, monde.depart_id)

    feuille = monde.generateur.derniere
    assert feuille is not None
    assert [a.nom for a in feuille.archers] == ["Durand"]


def test_archers_ordonnes_par_cible_puis_position() -> None:
    """Les feuilles suivent l'ordre physique de la salle : cible croissante, puis position (A, B…),
    même si le plan est lu dans le désordre."""
    monde = _monde()
    monde.placer("SurCible2", "X", cible_index=2, position="A")
    monde.placer("Cible1PosB", "Y", cible_index=1, position="B")
    monde.placer("Cible1PosA", "Z", cible_index=1, position="A")

    monde.service.generer(monde.tournoi_id, monde.depart_id)

    feuille = monde.generateur.derniere
    assert feuille is not None
    assert [(a.cible_index, a.position) for a in feuille.archers] == [(1, "A"), (1, "B"), (2, "A")]


def test_grille_repli_sur_preset_ffta_si_bareme_absent() -> None:
    """Sans barème de qualification défini, la grille prend le preset FFTA 18 m (20 volées de 3)."""
    monde = _monde(avec_bareme=None)
    monde.placer("Durand", "Marie", cible_index=1, position="A")

    monde.service.generer(monde.tournoi_id, monde.depart_id)

    feuille = monde.generateur.derniere
    assert feuille is not None
    assert (feuille.nb_volees, feuille.nb_fleches_par_volee) == (20, 3)


def test_tournoi_inconnu_leve_tournoi_introuvable() -> None:
    monde = _monde()
    with pytest.raises(TournoiIntrouvable):
        monde.service.generer(9999, monde.depart_id)


def test_depart_d_un_autre_tournoi_leve_depart_introuvable() -> None:
    monde = _monde()
    with pytest.raises(DepartIntrouvable):
        monde.service.generer(monde.tournoi_id, 9999)
