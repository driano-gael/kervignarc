"""Tests du service applicatif `ServiceSaisie` (E04US002) — orchestration, contre des faux ports.

Dérivés des **CA** (règle 9) : le pavé se déduit du **blason** de l'archer (ex-003), la validation
**trace** au nom du scoreur (ex-007 + E10US005), la correction **trace avant/après** (ex-012).
On vérifie la **résolution** (zones du blason, barème/grain de la phase, nom de l'auteur) et la
construction des entrées d'audit — pas la logique du domaine, prouvée dans `test_domain_serie`.
"""

from __future__ import annotations

import dataclasses
import datetime
from collections.abc import Sequence

import pytest

from application.erreurs import (
    ArcherIntrouvable,
    BlasonIntrouvable,
    PhaseQualificationAbsente,
    SaisieHorsCible,
)
from application.saisie import ArcherPositionne, ContexteSaisie, ServiceSaisie
from domain.archer import Archer, ArcherId
from domain.bareme import BaremeQualification
from domain.blason import Blason, BlasonId, ZoneScore
from domain.categorie import Categorie, CategorieId
from domain.depart import Depart, DepartId
from domain.entree_audit import ActionAuditee, EntreeAudit
from domain.erreurs import NumeroVoleeInvalide, ValeurHorsBlason
from domain.forfait import Forfait, NatureForfait
from domain.grain_validation import GrainValidation
from domain.inscription import Inscription, InscriptionId
from domain.phase import Phase, PhaseId, TypePhase
from domain.placement import Affectation
from domain.serie import Serie
from domain.tournoi import TournoiId
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxDepartRepository,
    FauxForfaitRepository,
    FauxInscriptionRepository,
    FauxLecteurPopulations,
    FauxPhaseRepository,
)

_DEPART: DepartId = 7
"""Départ courant du poste dans les tests : un simple identifiant, aucun agrégat `Depart` requis
(le service de saisie reçoit un `depart_id`, déjà validé en amont par `ServicePostes`)."""

_QUAND = datetime.datetime(2026, 7, 19, 10, 42, tzinfo=datetime.UTC)
ZONES_SIMPLE = tuple(ZoneScore)
ZONES_TRIPLE = (
    ZoneScore.DIX,
    ZoneScore.NEUF,
    ZoneScore.HUIT,
    ZoneScore.SEPT,
    ZoneScore.SIX,
    ZoneScore.MANQUE,
)


def _v(*valeurs: str) -> tuple[ZoneScore, ...]:
    return tuple(ZoneScore(v) for v in valeurs)


class FauxSerieRepository:
    """Repository de séries en mémoire conforme au port `SerieRepository`.

    `enregistrer_avec_trace` **retient** l'entrée d'audit reçue (`traces`) : c'est ce que les tests
    inspectent pour vérifier que l'acte laisse bien sa trace, dans la même opération que l'écriture.
    """

    def __init__(self) -> None:
        # E05US025 : la cle d'une feuille est `(phase, archer)`, comme en base.
        self._series: dict[tuple[int, int], Serie] = {}
        self.traces: list[EntreeAudit] = []
        self._sequence = 0
        # Le « quand » (created_at) est une métadonnée de persistance prouvée au repository
        # (test_serie_repository). Ce faux ne l'attribue pas seul, mais un test peut le **forcer**
        # (clé `(tournoi, archer)` → `{numéro: instant}`) pour couvrir la « dernière saisie » de la
        # supervision (E12US001, `avancement_cible`), qui lit ce « quand ». Cle `(phase, archer)`.
        self.horodatages_forces: dict[tuple[int, int], dict[int, datetime.datetime]] = {}

    def par_archer(self, phase_id: PhaseId, archer_id: ArcherId) -> Serie | None:
        return self._series.get((phase_id, archer_id))

    def par_phase(self, phase_id: PhaseId) -> list[Serie]:
        """E05US025 : le classement lit les feuilles **d'une phase**, plus celles du tournoi."""
        return [s for (p, _), s in self._series.items() if p == phase_id]

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Serie]:
        return [s for s in self._series.values() if s.tournoi_id == tournoi_id]

    def horodatages(self, phase_id: PhaseId, archer_id: ArcherId) -> dict[int, datetime.datetime]:
        return self.horodatages_forces.get((phase_id, archer_id), {})

    def enregistrer(self, serie: Serie) -> Serie:
        if serie.id is None:
            self._sequence += 1
            serie = dataclasses.replace(serie, id=self._sequence)
        # E05US025 (correctif de revue) : la clé d'écriture **doit** être celle de la lecture.
        # Ce faux écrivait par `(tournoi, archer)` et relisait par `(phase, archer)` : la moitié du
        # doublage avait été portée, l'autre non, et le fichier ne restait vert que parce que le
        # montage fait valoir 1 au tournoi comme à la phase. Une doublure qui répond autrement que
        # la production ne prouve rien (`DETTE-049`).
        self._series[(serie.phase_id, serie.archer_id)] = serie
        return serie

    def enregistrer_avec_trace(self, serie: Serie, entree: EntreeAudit) -> Serie:
        self.traces.append(entree)
        return self.enregistrer(serie)


class FauxBlasonRepository:
    """Repository de blasons en mémoire conforme au port `BlasonRepository`."""

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

    def par_bibliotheque(self) -> list[Blason]:
        # Modèles de bibliothèque (E01US023) : ceux sans tournoi.
        return [x for x in self._blasons.values() if x.tournoi_id is None]

    def enregistrer(self, blason: Blason) -> Blason:
        assert blason.id in self._blasons
        self._blasons[blason.id] = blason
        return blason

    def supprimer(self, blason_id: BlasonId) -> None:
        del self._blasons[blason_id]


class FauxPlacementRepository:
    """Repository de placement en mémoire conforme au port `PlacementRepository`.

    Le service de saisie ne consomme que `par_depart` (reconstituer les archers d'une cible depuis
    le placement réel, ADR-0033) ; les écritures du port sont fournies pour la conformité. Fake
    **local** : `test_service_placement` et `test_service_feuille_de_marque` en ont chacun une copie
    — non factorisées ici, même parti que `FauxTournoiRepository` (on ne réécrit pas ce que cette US
    n'aggrave pas ; cf. doctrine des doublures, `conftest.py`).
    """

    def __init__(self) -> None:
        self._par_depart: dict[int, list[Affectation]] = {}

    def par_depart(self, depart_id: DepartId) -> list[Affectation]:
        return list(self._par_depart.get(depart_id, []))

    def definir_plan(self, depart_id: DepartId, affectations: Sequence[Affectation]) -> None:
        self._par_depart[depart_id] = list(affectations)

    def definir_plan_avec_trace(
        self, depart_id: DepartId, affectations: Sequence[Affectation], entree: EntreeAudit
    ) -> None:
        raise NotImplementedError("Non exercé par ServiceSaisie.")

    def poser_plusieurs(self, depart_id: DepartId, affectations: Sequence[Affectation]) -> None:
        self._par_depart.setdefault(depart_id, []).extend(affectations)

    def retirer(self, inscription_id: InscriptionId) -> None:
        for affectations in self._par_depart.values():
            affectations[:] = [a for a in affectations if a.inscription_id != inscription_id]


class HorlogeFigee:
    """Horloge déterministe conforme au port `Horloge` : renvoie toujours le même instant."""

    def __init__(self, instant: datetime.datetime) -> None:
        self._instant = instant

    def maintenant(self) -> datetime.datetime:
        return self._instant


class Montage:
    """Attelage d'un test : service, faux repos, un archer prêt à tirer, une phase de qualif."""

    def __init__(
        self,
        *,
        zones: tuple[ZoneScore, ...] = ZONES_SIMPLE,
        avec_phase: bool = True,
        avec_blason: bool = True,
        nb_volees: int = 2,
    ) -> None:
        self.series = FauxSerieRepository()
        # Le créneau conventionnel `_DEPART` de ce montage, matérialisé : la doublure de phases
        # en a besoin pour la vue transverse « phases du tournoi » que lit le service.
        self.departs = FauxDepartRepository()
        self.departs.ajouter(
            dataclasses.replace(
                Depart.creer(tournoi_id=1, numero=1, tarif_centimes=800, horaire="09:00"),
                id=_DEPART,
            )
        )
        self.phases = FauxPhaseRepository(self.departs)
        self.archers = FauxArcherRepository()
        self.categories = FauxCategorieRepository()
        self.blasons = FauxBlasonRepository()
        self.placements = FauxPlacementRepository()
        self.inscriptions = FauxInscriptionRepository()
        self.forfaits = FauxForfaitRepository()
        self.horloge = HorlogeFigee(_QUAND)
        # Inerte par défaut (aucune population déclarée) : le service retombe alors sur « la
        # qualification en cours du créneau », le comportement mono-qualification. Le test de la
        # fourche la renseigne.
        self.populations = FauxLecteurPopulations()
        self.tournoi_id: TournoiId = 1
        blason_id: BlasonId | None = None
        if avec_blason:
            blason = self.blasons.ajouter(
                Blason(tournoi_id=1, nom="Simple", taille=1.0, capacite=1, zones=zones)
            )
            blason_id = blason.id
        categorie = self.categories.ajouter(
            Categorie(tournoi_id=1, libelle="Senior Homme", blason_id=blason_id)
        )
        assert categorie.id is not None
        self.categorie_id: CategorieId = categorie.id
        archer = self.archers.ajouter(
            Archer(nom="DUPONT", prenom="Jean", tournoi_id=1, categorie_id=categorie.id)
        )
        assert archer.id is not None
        self.archer_id: ArcherId = archer.id
        # `phase_id` est publié par le montage : les tests lisent la feuille **par sa phase**
        # (clé du port depuis E05US025), et non par le tournoi — dont l'identifiant ne coïncide
        # plus, précisément pour que la confusion échoue au lieu de passer (`DETTE-044`).
        self.phase_id: PhaseId = 0
        if avec_phase:
            posee = self.phases.ajouter(
                Phase.qualification(
                    depart_id=_DEPART,
                    bareme=BaremeQualification.creer(nb_volees, 3),
                    validation=GrainValidation.fin_de_serie(),
                )
            )
            assert posee.id is not None
            self.phase_id = posee.id
        self.service = ServiceSaisie(
            self.series,
            self.phases,
            self.archers,
            self.categories,
            self.blasons,
            self.placements,
            self.inscriptions,
            self.forfaits,
            self.horloge,
            self.populations,
        )

    def saisir_serie_complete(self) -> None:
        """Saisit les deux volées du barème (préalable à une validation de fin de série)."""
        self.service.saisir_volee(self.tournoi_id, self.archer_id, 1, _v("10", "9", "8"), "DURAND")
        self.service.saisir_volee(self.tournoi_id, self.archer_id, 2, _v("9", "9", "9"), "DURAND")

    def nouvel_archer(self, nom: str) -> ArcherId:
        """Ajoute un second archer (même catégorie/blason) et renvoie son id (grille à N)."""
        archer = self.archers.ajouter(
            Archer(nom=nom, prenom="Paul", tournoi_id=1, categorie_id=self.categorie_id)
        )
        assert archer.id is not None
        return archer.id

    def placer(
        self, archer_id: ArcherId, depart_id: DepartId, cible_index: int, position: str
    ) -> None:
        """Inscrit l'archer sur `depart_id` puis le place sur `(cible, position)` — cf. ADR-0033.

        Reproduit le placement réel (ADR-0033) : une inscription `(archer, départ)` et son
        affectation `(cible, position)`. Sans appel à `placer`, l'archer est en **réserve**.
        """
        inscription = self.inscriptions.ajouter(Inscription.creer(archer_id, depart_id))
        assert inscription.id is not None
        self.placements.poser_plusieurs(
            depart_id, [Affectation(inscription.id, cible_index, position)]
        )


def test_saisir_volee_persiste_avec_le_marqueur() -> None:
    """ex-005/017 : la volée saisie est persistée, avec le nom du marqueur."""
    m = Montage()
    m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "9", "8"), saisie_par="DURAND")
    serie = m.series.par_archer(m.phase_id, m.archer_id)
    assert serie is not None
    volee = serie.volee(1)
    assert volee is not None
    assert volee.valeurs == _v("10", "9", "8")
    assert volee.saisie_par == "DURAND"


def test_le_pave_vient_du_blason_de_l_archer() -> None:
    """ex-003 : les zones admises se déduisent du blason — un « 5 » sur un triple 40 est refusé."""
    m = Montage(zones=ZONES_TRIPLE)
    with pytest.raises(ValeurHorsBlason):
        m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "9", "5"))


def test_valider_trace_une_entree_au_nom_du_scoreur() -> None:
    """ex-007 : valider verrouille la série et trace une VALIDATION au nom du scoreur, datée."""
    m = Montage()
    m.saisir_serie_complete()
    m.service.valider(m.tournoi_id, m.archer_id, scoreur="MARTIN")
    serie = m.series.par_archer(m.phase_id, m.archer_id)
    assert serie is not None
    assert all(v.verrouillee for v in serie.volees)
    assert len(m.series.traces) == 1
    trace = m.series.traces[0]
    assert trace.action is ActionAuditee.VALIDATION
    assert trace.auteur == "MARTIN"
    assert trace.horodatage == _QUAND
    assert (trace.avant, trace.apres) == (None, None)


def test_corriger_trace_l_avant_et_l_apres() -> None:
    """ex-012 : corriger une volée verrouillée laisse une trace CORRECTION_SCORE avant/après."""
    m = Montage()
    m.saisir_serie_complete()
    m.service.valider(m.tournoi_id, m.archer_id, scoreur="MARTIN")
    m.service.corriger_volee(m.tournoi_id, m.archer_id, 1, _v("9", "9", "9"), auteur="ARBITRE")
    trace = m.series.traces[-1]
    assert trace.action is ActionAuditee.CORRECTION_SCORE
    assert trace.auteur == "ARBITRE"
    assert trace.avant == "10, 9, 8"
    assert trace.apres == "9, 9, 9"


def test_saisir_pour_un_archer_inconnu_est_refuse() -> None:
    """Un archer inconnu rend `ArcherIntrouvable` (traduit en 404)."""
    m = Montage()
    with pytest.raises(ArcherIntrouvable):
        m.service.saisir_volee(m.tournoi_id, 999, 1, _v("10", "9", "8"))


def test_saisir_pour_un_archer_d_un_autre_tournoi_est_refuse() -> None:
    """Un archer d'un autre tournoi n'existe pas pour ce tournoi (`ArcherIntrouvable`)."""
    m = Montage()
    with pytest.raises(ArcherIntrouvable):
        m.service.saisir_volee(2, m.archer_id, 1, _v("10", "9", "8"))


def test_saisir_sans_phase_de_qualification_est_refuse() -> None:
    """Sans phase de qualification configurée, la saisie rend `PhaseQualificationAbsente`."""
    m = Montage(avec_phase=False)
    with pytest.raises(PhaseQualificationAbsente):
        m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "9", "8"))


def test_saisir_pour_un_archer_sans_blason_est_refuse() -> None:
    """Sans blason par défaut, le pavé est indéterminable : `BlasonIntrouvable`."""
    m = Montage(avec_blason=False)
    with pytest.raises(BlasonIntrouvable):
        m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "9", "8"))


def test_le_service_borne_le_rang_de_volee_par_le_bareme_de_la_phase() -> None:
    """Le service passe `nb_volees` de la phase au domaine : un rang hors barème est refusé."""
    m = Montage()  # barème de la phase : 2 volées de 3 flèches
    with pytest.raises(NumeroVoleeInvalide):
        m.service.saisir_volee(m.tournoi_id, m.archer_id, 3, _v("10", "9", "8"))


# --- Source des archers & garde « SA cible / SON départ » (ADR-0033) ---


def test_archers_du_poste_viennent_des_affectations_cible_depart() -> None:
    """CA « grille » : la grille = archers **placés** sur (cible, départ), positions A..D, triés."""
    m = Montage()
    a = m.nouvel_archer("ALPHA")
    b = m.nouvel_archer("BRAVO")
    autre_cible = m.nouvel_archer("CHARLIE")
    m.placer(b, _DEPART, cible_index=1, position="B")
    m.placer(a, _DEPART, cible_index=1, position="A")
    m.placer(autre_cible, _DEPART, cible_index=2, position="A")  # autre cible : hors grille

    grille = m.service.archers_du_poste(m.tournoi_id, cible_index=1, depart_id=_DEPART)

    assert [(ligne.position, ligne.archer.id) for ligne in grille] == [("A", a), ("B", b)]
    assert all(isinstance(ligne, ArcherPositionne) for ligne in grille)


def test_archers_du_poste_signalent_un_forfait_de_qualification() -> None:
    """E04US018 : un abandon / une DSQ (E04US015) laisse l'archer **dans la grille** avec une série
    qui ne se complétera jamais. Le client a besoin de le savoir pour cesser d'attendre ses volées —
    sans ce signal, une seule DSQ prive toute la cible du panneau de routage, à vie. C'est le
    serveur qui sait, comme `ServiceCompletude._serie_close` (DETTE-014) : le front ne re-dérive
    rien.
    """
    m = Montage()
    a = m.nouvel_archer("ALPHA")
    b = m.nouvel_archer("BRAVO")
    m.placer(a, _DEPART, cible_index=1, position="A")
    m.placer(b, _DEPART, cible_index=1, position="B")
    phase = m.phases.par_depart_et_type(_DEPART, TypePhase.QUALIFICATION)
    assert phase is not None and phase.id is not None
    m.forfaits.semer(
        Forfait.creer(m.tournoi_id, a, phase.id, NatureForfait.ABANDON, "DURAND", _QUAND)
    )

    grille = m.service.archers_du_poste(m.tournoi_id, cible_index=1, depart_id=_DEPART)

    assert [(ligne.archer.id, ligne.forfait) for ligne in grille] == [(a, True), (b, False)]


def test_archers_du_poste_ignorent_un_forfait_declare_en_duels() -> None:
    """Le forfait qui clôt une série de **qualification** est celui déclaré **en qualification**
    (ADR-0050 : un abandon en duels ne relègue pas un rang de qualif). Sans ce filtre, un abandon de
    phase finale ferait croire à la tablette que la série de qualif est close."""
    m = Montage()
    a = m.nouvel_archer("ALPHA")
    m.placer(a, _DEPART, cible_index=1, position="A")
    tableau = m.phases.ajouter(Phase.creer(m.tournoi_id, 2, TypePhase.ELIMINATION_DIRECTE))
    assert tableau.id is not None
    m.forfaits.semer(
        Forfait.creer(m.tournoi_id, a, tableau.id, NatureForfait.ABANDON, "DURAND", _QUAND)
    )

    grille = m.service.archers_du_poste(m.tournoi_id, cible_index=1, depart_id=_DEPART)

    assert [ligne.forfait for ligne in grille] == [False]


def test_archers_du_poste_sans_phase_de_qualification_n_echouent_pas() -> None:
    """Robustesse jour J : sans phase de qualification configurée, personne n'est forfait et la
    grille s'affiche quand même — même parti que le barème dans `avancement_cible`."""
    m = Montage(avec_phase=False)
    a = m.nouvel_archer("ALPHA")
    m.placer(a, _DEPART, cible_index=1, position="A")

    grille = m.service.archers_du_poste(m.tournoi_id, cible_index=1, depart_id=_DEPART)

    assert [ligne.forfait for ligne in grille] == [False]


def test_archers_du_poste_excluent_un_autre_depart() -> None:
    """Une cible sert plusieurs départs : seule la grille du **départ courant** remonte (0033)."""
    m = Montage()
    matin = m.nouvel_archer("MATIN")
    apres_midi = m.nouvel_archer("APREM")
    m.placer(matin, _DEPART, cible_index=1, position="A")
    m.placer(apres_midi, 99, cible_index=1, position="A")  # même cible, autre départ

    grille = m.service.archers_du_poste(m.tournoi_id, cible_index=1, depart_id=_DEPART)

    assert [ligne.archer.id for ligne in grille] == [matin]


def test_archers_du_poste_vide_sans_affectation() -> None:
    """Aucun archer placé sur (cible, départ) → grille vide (tout en réserve)."""
    m = Montage()
    assert m.service.archers_du_poste(m.tournoi_id, cible_index=1, depart_id=_DEPART) == []


def test_la_grille_expose_le_pave_du_blason_de_chaque_archer() -> None:
    """CA « pavé » : chaque ligne porte les zones du blason de l'archer (le pavé de saisie)."""
    m = Montage(zones=ZONES_TRIPLE)
    a = m.nouvel_archer("ALPHA")
    m.placer(a, _DEPART, cible_index=1, position="A")

    grille = m.service.archers_du_poste(m.tournoi_id, cible_index=1, depart_id=_DEPART)

    assert [ligne.zones for ligne in grille] == [ZONES_TRIPLE]


def test_la_grille_remonte_un_pave_vide_si_le_blason_est_indeterminable() -> None:
    """Robustesse jour J : un archer sans blason par défaut n'efface pas la cible — pavé `()`.

    Le chemin d'**écriture** (`saisir_volee`), lui, refuse cet archer en `BlasonIntrouvable` (404) :
    la lecture tolère pour afficher, l'écriture reste stricte (erreur visible, pas silencieuse)."""
    m = Montage(avec_blason=False)  # catégorie sans blason par défaut
    a = m.nouvel_archer("SANSBLASON")
    m.placer(a, _DEPART, cible_index=1, position="A")

    grille = m.service.archers_du_poste(m.tournoi_id, cible_index=1, depart_id=_DEPART)

    assert [ligne.zones for ligne in grille] == [()]


def test_saisir_pour_un_archer_de_sa_cible_est_autorise() -> None:
    """ADR-0033 §3 : le poste saisit pour un archer affecté à SA cible / SON départ."""
    m = Montage()
    m.placer(m.archer_id, _DEPART, cible_index=1, position="A")
    contexte = ContexteSaisie(cible_index=1, depart_id=_DEPART)

    m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "9", "8"), contexte=contexte)

    serie = m.series.par_archer(m.phase_id, m.archer_id)
    assert serie is not None and serie.volee(1) is not None


def test_saisir_pour_un_archer_d_une_autre_cible_est_refuse() -> None:
    """ADR-0033 §3 : un archer placé sur une **autre cible** → `SaisieHorsCible` (403)."""
    m = Montage()
    m.placer(m.archer_id, _DEPART, cible_index=2, position="A")
    contexte = ContexteSaisie(cible_index=1, depart_id=_DEPART)

    with pytest.raises(SaisieHorsCible):
        m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "9", "8"), contexte=contexte)


def test_saisir_pour_un_archer_d_un_autre_depart_est_refuse() -> None:
    """Triplet (tournoi, cible, départ) : même cible mais **autre départ** courant → hors cible."""
    m = Montage()
    m.placer(m.archer_id, 99, cible_index=1, position="A")  # placé sur un autre départ
    contexte = ContexteSaisie(cible_index=1, depart_id=_DEPART)

    with pytest.raises(SaisieHorsCible):
        m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "9", "8"), contexte=contexte)


def test_saisir_pour_un_archer_en_reserve_est_refuse() -> None:
    """Un archer **inscrit mais non placé** (réserve) n'est sur aucune cible → `SaisieHorsCible`."""
    m = Montage()
    m.inscriptions.ajouter(Inscription.creer(m.archer_id, _DEPART))  # inscrit, jamais placé
    contexte = ContexteSaisie(cible_index=1, depart_id=_DEPART)

    with pytest.raises(SaisieHorsCible):
        m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "9", "8"), contexte=contexte)


def test_saisir_sans_contexte_reste_ouvert_a_l_admin() -> None:
    """`contexte=None` = saisie **admin**, sans contrainte de cible (E10US001) : sans placement."""
    m = Montage()  # archer ni inscrit ni placé

    m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "9", "8"))  # contexte par défaut

    assert m.series.par_archer(m.phase_id, m.archer_id) is not None


def test_valider_est_aussi_cloisonnee_au_poste() -> None:
    """La garde vaut pour **tout** chemin d'écriture, pas seulement `saisir_volee` (ADR-0033 §3)."""
    m = Montage()
    m.placer(m.archer_id, _DEPART, cible_index=2, position="A")  # archer sur une autre cible
    m.saisir_serie_complete()  # rempli en admin (sans contexte)
    contexte = ContexteSaisie(cible_index=1, depart_id=_DEPART)

    with pytest.raises(SaisieHorsCible):
        m.service.valider(m.tournoi_id, m.archer_id, scoreur="MARTIN", contexte=contexte)


def test_corriger_est_aussi_cloisonnee_au_poste() -> None:
    """Idem pour la correction tracée : un poste ne corrige que pour SA cible (ADR-0033 §3)."""
    m = Montage()
    m.placer(m.archer_id, _DEPART, cible_index=2, position="A")
    m.saisir_serie_complete()
    m.service.valider(m.tournoi_id, m.archer_id, scoreur="MARTIN")  # admin
    contexte = ContexteSaisie(cible_index=1, depart_id=_DEPART)

    with pytest.raises(SaisieHorsCible):
        m.service.corriger_volee(
            m.tournoi_id, m.archer_id, 1, _v("9", "9", "9"), auteur="ARBITRE", contexte=contexte
        )


# --- Avancement d'une cible (E12US001, ADR-0038 §2) : lu par la console de supervision ---
#
# Règle métier arbitrée dans la story (E12US001) : « volée courante = celle du **plus lent** des
# archers de la cible » et « dernière activité = dernier tir (max `created_at`), pas le heartbeat ».
# C'est le cœur du CA (« sinon la lenteur serait invisible »). Testé **ici, depuis le CA**, sur le
# vrai `ServiceSaisie` — le `FauxLecteurAvancement` du test de supervision isole *ce* service et ne
# prouve donc rien de ce calcul (règle 9 : la logique de service se teste depuis le CA).


def _saisir_volees(m: Montage, archer_id: ArcherId, combien: int) -> None:
    """Saisit `combien` volées pleines (numéros 1..combien) pour un archer — chacune complète."""
    for numero in range(1, combien + 1):
        m.service.saisir_volee(m.tournoi_id, archer_id, numero, _v("10", "9", "8"), "DURAND")


def test_avancement_cible_volee_courante_est_celle_du_plus_lent() -> None:
    """Deux archers d'une cible à 3 et 5 volées → la cible est sur la volée du plus lent (min+1)."""
    m = Montage(nb_volees=12)
    autre = m.nouvel_archer("MARTIN")
    m.placer(m.archer_id, _DEPART, cible_index=1, position="A")
    m.placer(autre, _DEPART, cible_index=1, position="B")
    _saisir_volees(m, m.archer_id, 3)
    _saisir_volees(m, autre, 5)

    avancement = m.service.avancement_cible(m.tournoi_id, cible_index=1, depart_id=_DEPART)

    assert (avancement.volee_courante, avancement.nb_volees) == (4, 12)  # min(3, 5) + 1


def test_avancement_cible_un_retardataire_sans_serie_tient_la_cible() -> None:
    """Un archer placé qui n'a **rien** saisi maintient la cible à la volée 1 (le min compte 0)."""
    m = Montage(nb_volees=12)
    autre = m.nouvel_archer("MARTIN")
    m.placer(m.archer_id, _DEPART, cible_index=1, position="A")
    m.placer(autre, _DEPART, cible_index=1, position="B")
    _saisir_volees(m, m.archer_id, 4)  # `autre` n'a aucune série

    avancement = m.service.avancement_cible(m.tournoi_id, cible_index=1, depart_id=_DEPART)

    assert avancement.volee_courante == 1  # min(4, 0) + 1


def test_avancement_cible_est_cape_a_nb_volees_quand_tout_est_saisi() -> None:
    """Toutes les volées saisies → « volée N/N » (le min+1 est capé, pas N+1)."""
    m = Montage(nb_volees=2)
    m.placer(m.archer_id, _DEPART, cible_index=1, position="A")
    _saisir_volees(m, m.archer_id, 2)  # les deux volées du barème

    avancement = m.service.avancement_cible(m.tournoi_id, cible_index=1, depart_id=_DEPART)

    assert (avancement.volee_courante, avancement.nb_volees) == (2, 2)  # 3 capé à 2


def test_avancement_cible_derniere_saisie_est_le_dernier_tir_tous_archers_confondus() -> None:
    """« Dernière activité » = max des `created_at`, pas le dernier archer parcouru (ADR-0038)."""
    m = Montage(nb_volees=12)
    autre = m.nouvel_archer("MARTIN")
    m.placer(m.archer_id, _DEPART, cible_index=1, position="A")
    m.placer(autre, _DEPART, cible_index=1, position="B")
    _saisir_volees(m, m.archer_id, 2)
    _saisir_volees(m, autre, 1)
    tot = datetime.datetime(2026, 7, 19, 10, 40, tzinfo=datetime.UTC)
    dernier = datetime.datetime(2026, 7, 19, 10, 45, tzinfo=datetime.UTC)
    entre_deux = datetime.datetime(2026, 7, 19, 10, 43, tzinfo=datetime.UTC)
    m.series.horodatages_forces[(m.phase_id, m.archer_id)] = {1: tot, 2: dernier}
    m.series.horodatages_forces[(m.phase_id, autre)] = {1: entre_deux}

    avancement = m.service.avancement_cible(m.tournoi_id, cible_index=1, depart_id=_DEPART)

    assert avancement.derniere_saisie == dernier


def test_avancement_cible_sans_phase_de_qualification_ne_leve_pas() -> None:
    """La supervision ne doit jamais échouer sur une qualif non configurée : `nb_volees` vaut 0."""
    m = Montage(avec_phase=False)
    m.placer(m.archer_id, _DEPART, cible_index=1, position="A")

    avancement = m.service.avancement_cible(m.tournoi_id, cible_index=1, depart_id=_DEPART)

    assert avancement.nb_volees == 0  # aucune `PhaseQualificationAbsente` levée


def test_avancement_cible_sans_archer_place_est_a_zero() -> None:
    """Cible sans archer placé sur ce départ : volée 0, aucune dernière saisie (console tirete)."""
    m = Montage(nb_volees=12)

    avancement = m.service.avancement_cible(m.tournoi_id, cible_index=1, depart_id=_DEPART)

    assert (avancement.volee_courante, avancement.nb_volees, avancement.derniere_saisie) == (
        0,
        12,
        None,
    )


# --- E05US025 : la fourche (correctifs de revue) ------------------------------------------------


def _monter_la_fourche(m: Montage) -> tuple[PhaseId, PhaseId, ArcherId]:
    """Ajoute au montage une *haute* et une *basse*, et un second archer. Rend leurs identifiants.

    Reproduit l'exemple de référence du CA à l'échelle d'un test : une qualification de tête (celle
    du montage), puis deux qualifications **prélevées** qui se jouent **ensemble** — l'arbitrage du
    09/08/2026 dit explicitement que rien n'impose une seule phase en cours à la fois. C'est cette
    simultanéité qui rend le cas piégeux : « la phase en cours du créneau » ne désigne alors plus
    personne en particulier.
    """
    autre = m.archers.ajouter(
        Archer(nom="MARTIN", prenom="Luc", tournoi_id=m.tournoi_id, categorie_id=m.categorie_id)
    )
    assert autre.id is not None
    haute = m.phases.ajouter(
        Phase(
            depart_id=_DEPART,
            ordre=2,
            type=TypePhase.QUALIFICATION,
            bareme=BaremeQualification.creer(2, 3),
            validation=GrainValidation.fin_de_serie(),
        ).demarrer()
    )
    basse = m.phases.ajouter(
        Phase(
            depart_id=_DEPART,
            ordre=3,
            type=TypePhase.QUALIFICATION,
            bareme=BaremeQualification.creer(2, 3),
            validation=GrainValidation.fin_de_serie(),
        ).demarrer()
    )
    assert haute.id is not None and basse.id is not None
    # Les deux archers sont **placés sur la même cible** : c'est le cas du CA (le plan de cibles
    # reste commun aux trois tours), et c'est aussi ce qui donne un créneau à la saisie admin.
    m.placer(m.archer_id, _DEPART, cible_index=1, position="A")
    m.placer(autre.id, _DEPART, cible_index=1, position="B")
    m.populations.populations = {2: [m.archer_id], 3: [autre.id]}
    return haute.id, basse.id, autre.id


def test_la_fourche_ecrit_chaque_archer_dans_sa_propre_qualification() -> None:
    """CA E05US025 — « une flèche saisie ne peut pas atterrir dans la mauvaise feuille ».

    Bloquant de revue. Sur la fourche, `qualification_courante` rend la **première démarrée** du
    créneau : les 60 archers de la *basse* auraient écrit leurs 3x15 dans la feuille de la *haute*,
    et la basse serait restée vide — le défaut même que l'US existe pour fermer, déplacé du tournoi
    vers le créneau. La discrimination se fait sur la **population** de chaque phase.
    """
    m = Montage()
    haute, basse, autre = _monter_la_fourche(m)

    m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "9", "8"))
    m.service.saisir_volee(m.tournoi_id, autre, 1, _v("6", "5", "M"))

    feuille_haute = m.series.par_archer(haute, m.archer_id)
    feuille_basse = m.series.par_archer(basse, autre)
    assert feuille_haute is not None, "L'archer de la haute écrit dans la haute."
    assert feuille_basse is not None, "L'archer de la basse écrit dans la basse."
    assert m.series.par_archer(haute, autre) is None, "…et pas dans la feuille de l'autre phase."
    assert m.series.par_archer(basse, m.archer_id) is None


def test_la_fourche_relit_chaque_archer_dans_sa_propre_qualification() -> None:
    """Le chemin de **lecture** résout la phase comme celui d'écriture (bloquant de revue).

    `etat_serie` passait `tournoi_id` au port, dont le premier paramètre est un `phase_id` depuis
    cette US : la grille de saisie repartait **vierge sur des flèches réellement en base**. Deux
    alias d'`int` (`DETTE-044`), donc rien à la compilation — seul un décor où les identifiants ne
    coïncident pas le montre.
    """
    m = Montage()
    _haute, _basse, autre = _monter_la_fourche(m)
    m.service.saisir_volee(m.tournoi_id, autre, 1, _v("6", "5", "M"))

    etat = m.service.etat_serie(m.tournoi_id, autre)

    assert etat is not None, "La feuille écrite est relue, pas une grille vide."
    assert len(etat.serie.volees) == 1


def test_la_lecture_retrouve_la_feuille_sur_un_deroule_ordinaire() -> None:
    """Non-régression du bloquant, hors fourche : `tournoi_id` (1) ≠ `phase_id` suffit à le voir."""
    m = Montage()
    m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "9", "8"))

    etat = m.service.etat_serie(m.tournoi_id, m.archer_id)

    assert m.phase_id != m.tournoi_id, "Le décor doit distinguer les deux identifiants."
    assert etat is not None and len(etat.serie.volees) == 1
