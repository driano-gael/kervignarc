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
from domain.depart import DepartId
from domain.entree_audit import ActionAuditee, EntreeAudit
from domain.erreurs import NumeroVoleeInvalide, ValeurHorsBlason
from domain.grain_validation import GrainValidation
from domain.inscription import Inscription, InscriptionId
from domain.phase import Phase, PhaseId, TypePhase
from domain.placement import Affectation
from domain.serie import Serie
from domain.tournoi import TournoiId
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxInscriptionRepository,
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
        self._series: dict[tuple[int, int], Serie] = {}
        self.traces: list[EntreeAudit] = []
        self._sequence = 0
        # Le « quand » (created_at) est une métadonnée de persistance prouvée au repository
        # (test_serie_repository). Ce faux ne l'attribue pas seul, mais un test peut le **forcer**
        # (clé `(tournoi, archer)` → `{numéro: instant}`) pour couvrir la « dernière saisie » de la
        # supervision (E12US001, `avancement_cible`), qui lit ce « quand ».
        self.horodatages_forces: dict[tuple[int, int], dict[int, datetime.datetime]] = {}

    def par_archer(self, tournoi_id: TournoiId, archer_id: ArcherId) -> Serie | None:
        return self._series.get((tournoi_id, archer_id))

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Serie]:
        return [s for (t, _), s in self._series.items() if t == tournoi_id]

    def horodatages(
        self, tournoi_id: TournoiId, archer_id: ArcherId
    ) -> dict[int, datetime.datetime]:
        return self.horodatages_forces.get((tournoi_id, archer_id), {})

    def enregistrer(self, serie: Serie) -> Serie:
        if serie.id is None:
            self._sequence += 1
            serie = dataclasses.replace(serie, id=self._sequence)
        self._series[(serie.tournoi_id, serie.archer_id)] = serie
        return serie

    def enregistrer_avec_trace(self, serie: Serie, entree: EntreeAudit) -> Serie:
        self.traces.append(entree)
        return self.enregistrer(serie)


class FauxPhaseRepository:
    """Repository de phases en mémoire conforme au port `PhaseRepository`."""

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
        return next(
            (
                p
                for p in self._phases.values()
                if p.tournoi_id == tournoi_id and p.type is type_phase
            ),
            None,
        )

    def enregistrer(self, phase: Phase) -> Phase:
        assert phase.id in self._phases
        self._phases[phase.id] = phase
        return phase


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
        self.phases = FauxPhaseRepository()
        self.archers = FauxArcherRepository()
        self.categories = FauxCategorieRepository()
        self.blasons = FauxBlasonRepository()
        self.placements = FauxPlacementRepository()
        self.inscriptions = FauxInscriptionRepository()
        self.horloge = HorlogeFigee(_QUAND)
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
        if avec_phase:
            self.phases.ajouter(
                Phase.qualification(
                    tournoi_id=1,
                    bareme=BaremeQualification.creer(nb_volees, 3),
                    validation=GrainValidation.fin_de_serie(),
                )
            )
        self.service = ServiceSaisie(
            self.series,
            self.phases,
            self.archers,
            self.categories,
            self.blasons,
            self.placements,
            self.inscriptions,
            self.horloge,
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
    serie = m.series.par_archer(m.tournoi_id, m.archer_id)
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
    serie = m.series.par_archer(m.tournoi_id, m.archer_id)
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

    serie = m.series.par_archer(m.tournoi_id, m.archer_id)
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

    assert m.series.par_archer(m.tournoi_id, m.archer_id) is not None


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
    m.series.horodatages_forces[(m.tournoi_id, m.archer_id)] = {1: tot, 2: dernier}
    m.series.horodatages_forces[(m.tournoi_id, autre)] = {1: entre_deux}

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
