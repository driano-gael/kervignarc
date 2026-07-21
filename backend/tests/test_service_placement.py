"""Tests du service applicatif Placement (E03US001) — repositories factices.

Le service est testé **en isolation** : de faux repositories en mémoire (conformes aux ports)
suffisent — ni base ni serveur. On y vérifie l'**orchestration** — gardes 404, jointure archer →
catégorie → blason par défaut, fusion des conflits « sans blason » (données) avec les conflits
« non placé » (faisabilité) du moteur pur, déjà couvert par `test_domain_placement`. Tests écrits
**après** l'implémentation : câblage applicatif, pas d'oracle métier (règle 9).

`FauxArcherRepository`/`FauxCategorieRepository`/`FauxDepartRepository`/`FauxInscriptionRepository`
viennent de `conftest` ; `FauxTournoiRepository`/`FauxGabaritRepository`/`FauxBlasonRepository`
restent locaux, comme dans les autres tests de service (patron `FauxTournoiRepository`).
"""

from __future__ import annotations

import dataclasses
import datetime
from collections.abc import Sequence

import pytest

from application.erreurs import (
    DepartIntrouvable,
    DeplacementInvalide,
    GabaritDuTournoiAbsent,
    ReplacementNonConfirme,
    TournoiIntrouvable,
)
from application.placement import ServicePlacement
from domain.archer import Archer, ArcherId
from domain.blason import Blason, BlasonId, ZoneScore
from domain.categorie import Categorie
from domain.depart import Depart, DepartId
from domain.entree_audit import ActionAuditee, EntreeAudit
from domain.gabarit_salle import GabaritSalle, GabaritSalleId
from domain.impact import NiveauImpact
from domain.inscription import Inscription, InscriptionId
from domain.placement import Affectation, CiblePlacee, PlanDeCibles, RaisonConflit
from domain.serie import Serie, Volee
from domain.tournoi import Tournoi, TournoiId, TypeTournoi
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxDepartRepository,
    FauxInscriptionRepository,
)

_DATE = datetime.date(2026, 3, 14)
_QUAND = datetime.datetime(2026, 3, 14, 10, 42, tzinfo=datetime.UTC)


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


class FauxGabaritRepository:
    """Repository en mémoire conforme au port `GabaritSalleRepository` (seul `par_tournoi` sert)."""

    def __init__(self) -> None:
        self._gabarits: dict[int, GabaritSalle] = {}
        self._sequence = 0

    def ajouter(self, gabarit: GabaritSalle) -> GabaritSalle:
        self._sequence += 1
        persiste = dataclasses.replace(gabarit, id=self._sequence)
        self._gabarits[self._sequence] = persiste
        return persiste

    def par_id(self, gabarit_id: GabaritSalleId) -> GabaritSalle | None:
        return self._gabarits.get(gabarit_id)

    def lister(self) -> list[GabaritSalle]:
        return [g for g in self._gabarits.values() if g.tournoi_id is None]

    def par_tournoi(self, tournoi_id: TournoiId) -> GabaritSalle | None:
        instances = [g for g in self._gabarits.values() if g.tournoi_id == tournoi_id]
        return instances[-1] if instances else None

    def enregistrer(self, gabarit: GabaritSalle) -> GabaritSalle:
        assert gabarit.id in self._gabarits
        self._gabarits[gabarit.id] = gabarit
        return gabarit

    def supprimer(self, gabarit_id: GabaritSalleId) -> None:
        del self._gabarits[gabarit_id]


class FauxBlasonRepository:
    """Repository en mémoire conforme au port `BlasonRepository` (seul `par_id` sert ici)."""

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
    """Repository en mémoire conforme au port `PlacementRepository` (E03US004, E12US007).

    Stocke une affectation par inscription, avec son départ, pour rejouer `par_depart`,
    `definir_plan` (purge + réécriture), `definir_plan_avec_trace` (purge + réécriture **+** trace),
    `poser_plusieurs` (upsert) et `retirer`. `traces` **retient** l'entrée d'audit reçue — c'est ce
    que les tests inspectent pour vérifier qu'une régénération massive laisse sa trace, dans la même
    opération que l'écriture (patron de `FauxSerieRepository`, test_service_saisie)."""

    def __init__(self) -> None:
        self._affectation: dict[int, Affectation] = {}
        self._depart: dict[int, int] = {}
        self.traces: list[EntreeAudit] = []

    def par_depart(self, depart_id: DepartId) -> list[Affectation]:
        affectations = [a for i, a in self._affectation.items() if self._depart[i] == depart_id]
        return sorted(affectations, key=lambda a: (a.cible_index, a.position))

    def definir_plan(self, depart_id: DepartId, affectations: Sequence[Affectation]) -> None:
        for inscription_id in [i for i, d in self._depart.items() if d == depart_id]:
            self._affectation.pop(inscription_id, None)
            self._depart.pop(inscription_id, None)
        self.poser_plusieurs(depart_id, affectations)

    def definir_plan_avec_trace(
        self, depart_id: DepartId, affectations: Sequence[Affectation], entree: EntreeAudit
    ) -> None:
        self.definir_plan(depart_id, affectations)
        self.traces.append(entree)

    def poser_plusieurs(self, depart_id: DepartId, affectations: Sequence[Affectation]) -> None:
        for affectation in affectations:
            self._affectation[affectation.inscription_id] = affectation
            self._depart[affectation.inscription_id] = depart_id

    def retirer(self, inscription_id: InscriptionId) -> None:
        self._affectation.pop(inscription_id, None)
        self._depart.pop(inscription_id, None)


class FauxSerieRepository:
    """Repository de séries en mémoire (port `SerieRepository`) — seul `par_tournoi` sert au calcul
    d'impact (E12US007). On y **sème** des scores pour marquer qu'une cible « a des données
    réelles ».

    Les autres méthodes du port ne sont pas exercées par `ServicePlacement` : elles restent des
    stubs
    conformes à la signature (le port est structurel, mypy exige leur présence)."""

    def __init__(self) -> None:
        self._series: list[Serie] = []

    def semer_score(self, tournoi_id: int, archer_id: ArcherId) -> None:
        """Donne à un archer une série avec **une volée validée** — il « a des scores » (impact).

        Validée (`validee_par`), pas seulement saisie : « données réelles produites » = tir
        **validé** (arbitrage daté, cf. `Serie.nb_fleches_validees`) ; une volée provisoire ne
        rendrait pas l'impact massif."""
        volee = Volee(
            numero=1,
            valeurs=(ZoneScore.DIX, ZoneScore.DIX, ZoneScore.DIX),
            validee_par="Scoreur",
        )
        self._series.append(Serie(tournoi_id=tournoi_id, archer_id=archer_id, volees=(volee,)))

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Serie]:
        return [s for s in self._series if s.tournoi_id == tournoi_id]

    def par_archer(self, tournoi_id: TournoiId, archer_id: ArcherId) -> Serie | None:
        return next(
            (s for s in self._series if s.tournoi_id == tournoi_id and s.archer_id == archer_id),
            None,
        )

    def horodatages(
        self, tournoi_id: TournoiId, archer_id: ArcherId
    ) -> dict[int, datetime.datetime]:
        return {}

    def enregistrer(self, serie: Serie) -> Serie:
        self._series.append(serie)
        return serie

    def enregistrer_avec_trace(self, serie: Serie, entree: EntreeAudit) -> Serie:
        raise NotImplementedError("Non exercé par ServicePlacement.")


class HorlogeFigee:
    """Horloge déterministe conforme au port `Horloge` (règle 9) : toujours le même instant."""

    def __init__(self, instant: datetime.datetime) -> None:
        self._instant = instant

    def maintenant(self) -> datetime.datetime:
        return self._instant


class _Monde:
    """Petit décor : les fakes câblés + un tournoi et un gabarit appliqué, prêts à peupler."""

    def __init__(self, *, avec_gabarit: bool = True, capacites: tuple[int, ...] = (4, 4)) -> None:
        self.tournois = FauxTournoiRepository()
        self.departs = FauxDepartRepository()
        self.gabarits = FauxGabaritRepository()
        self.inscriptions = FauxInscriptionRepository()
        self.archers = FauxArcherRepository()
        self.categories = FauxCategorieRepository()
        self.blasons = FauxBlasonRepository()
        self.placements = FauxPlacementRepository()
        self.series = FauxSerieRepository()
        self.horloge = HorlogeFigee(_QUAND)
        self.inscription_par_archer: dict[int, int] = {}
        tournoi = self.tournois.ajouter(
            Tournoi(nom="Kervignarc", date=_DATE, lieu=None, type_tournoi=TypeTournoi.NON_OFFICIEL)
        )
        assert tournoi.id is not None
        self.tournoi_id = tournoi.id
        if avec_gabarit:
            self.gabarits.ajouter(
                GabaritSalle(nom="Salle", capacites=capacites, tournoi_id=self.tournoi_id)
            )

    @property
    def service(self) -> ServicePlacement:
        return ServicePlacement(
            self.tournois,
            self.departs,
            self.gabarits,
            self.inscriptions,
            self.archers,
            self.categories,
            self.blasons,
            self.placements,
            self.series,
            self.horloge,
        )

    def semer_score(self, archer_id: int) -> None:
        """Donne un score (une volée **validée**) à un archer inscrit — pour les tests d'impact."""
        self.series.semer_score(self.tournoi_id, archer_id)

    def depart(self, numero: int) -> int:
        depart = self.departs.ajouter(
            Depart(tournoi_id=self.tournoi_id, numero=numero, tarif_centimes=0)
        )
        assert depart.id is not None
        return depart.id

    def categorie(
        self, *, taille: float = 0.5, hauteur: int = 130, avec_blason: bool = True
    ) -> int:
        blason_id = None
        if avec_blason:
            blason = self.blasons.ajouter(
                Blason.creer(self.tournoi_id, "B", taille=taille, capacite=1)
            )
            blason_id = blason.id
        categorie = self.categories.ajouter(
            Categorie.creer(self.tournoi_id, "Cat", blason_id=blason_id, hauteur_cm=hauteur)
        )
        assert categorie.id is not None
        return categorie.id

    def inscrire(self, depart_id: int, categorie_id: int) -> int:
        archer = self.archers.ajouter(
            Archer(nom="N", prenom="P", tournoi_id=self.tournoi_id, categorie_id=categorie_id)
        )
        assert archer.id is not None
        inscription = self.inscriptions.ajouter(
            Inscription(archer_id=archer.id, depart_id=depart_id)
        )
        assert inscription.id is not None
        self.inscription_par_archer[archer.id] = inscription.id
        return archer.id

    def inscription(self, archer_id: int) -> int:
        """Identifiant d'inscription d'un archer (pour cibler un déplacement, E03US004)."""
        return self.inscription_par_archer[archer_id]


def _archers_places(plan_cibles: tuple[CiblePlacee, ...]) -> set[int]:
    return {p.archer_id for cible in plan_cibles for p in cible.placements}


def test_place_les_archers_inscrits_au_depart() -> None:
    """La régénération place les inscrits sur les cibles du gabarit, chacun avec une position."""
    monde = _Monde(capacites=(4,))
    depart = monde.depart(1)
    cat = monde.categorie(taille=0.5)
    a1 = monde.inscrire(depart, cat)
    a2 = monde.inscrire(depart, cat)

    plan = monde.service.regenerer(monde.tournoi_id, depart)

    assert _archers_places(plan.cibles) == {a1, a2}
    assert tuple(p.position for p in plan.cibles[0].placements) == ("A", "B")
    assert plan.conflits == ()


def test_categorie_sans_blason_donne_un_conflit_sans_blason() -> None:
    """Un archer dont la catégorie n'a pas de blason par défaut ressort en conflit `SANS_BLASON`."""
    monde = _Monde(capacites=(4,))
    depart = monde.depart(1)
    cat = monde.categorie(avec_blason=False)
    archer = monde.inscrire(depart, cat)

    plan = monde.service.regenerer(monde.tournoi_id, depart)

    assert _archers_places(plan.cibles) == set()
    assert plan.conflits[0].archer_id == archer
    assert plan.conflits[0].raison is RaisonConflit.SANS_BLASON


def test_fusionne_conflits_sans_blason_et_non_place() -> None:
    """Le rapport réunit les conflits « sans blason » (données) et « non placé » (faisabilité)."""
    monde = _Monde(capacites=(1,))  # une seule cible, capacité 1
    depart = monde.depart(1)
    cat = monde.categorie(taille=1.0)  # remplit la cible à elle seule
    cat_sans = monde.categorie(avec_blason=False)
    place = monde.inscrire(depart, cat)
    surnombre = monde.inscrire(depart, cat)  # plus de place → NON_PLACE
    sans = monde.inscrire(depart, cat_sans)  # pas de blason → SANS_BLASON

    plan = monde.service.regenerer(monde.tournoi_id, depart)

    raisons = {c.archer_id: c.raison for c in plan.conflits}
    assert _archers_places(plan.cibles) == {place}
    assert raisons[sans] is RaisonConflit.SANS_BLASON
    assert raisons[surnombre] is RaisonConflit.NON_PLACE


def test_ne_place_que_les_inscrits_du_depart_demande() -> None:
    """Le plan d'un départ ignore les inscrits d'un autre départ du même tournoi."""
    monde = _Monde(capacites=(4, 4))
    depart1, depart2 = monde.depart(1), monde.depart(2)
    cat = monde.categorie(taille=0.5)
    a1 = monde.inscrire(depart1, cat)
    monde.inscrire(depart2, cat)

    plan1 = monde.service.regenerer(monde.tournoi_id, depart1)
    assert _archers_places(plan1.cibles) == {a1}


def test_u11_et_adultes_sont_separes_sur_deux_cibles() -> None:
    """Intégration hauteur (ADR-0022) : U11 (110) et adulte (130) ne partagent pas une cible."""
    monde = _Monde(capacites=(4, 4))
    depart = monde.depart(1)
    cat_u11 = monde.categorie(taille=0.25, hauteur=110)
    cat_adulte = monde.categorie(taille=0.25, hauteur=130)
    u11 = monde.inscrire(depart, cat_u11)
    adulte = monde.inscrire(depart, cat_adulte)

    plan = monde.service.regenerer(monde.tournoi_id, depart)

    cible_de = {p.archer_id: cible.index for cible in plan.cibles for p in cible.placements}
    assert cible_de[u11] != cible_de[adulte]


def test_depart_sans_inscrit_donne_un_plan_de_cibles_vides() -> None:
    """Un départ sans inscription produit un plan de cibles vides, sans conflit."""
    monde = _Monde(capacites=(4, 4))
    depart = monde.depart(1)

    plan = monde.service.plan_de_cibles(monde.tournoi_id, depart)

    assert len(plan.cibles) == 2
    assert _archers_places(plan.cibles) == set()
    assert plan.conflits == ()


def test_tournoi_inconnu_leve_tournoi_introuvable() -> None:
    """Garde 404 : un tournoi inexistant est rejeté avant tout calcul."""
    monde = _Monde()
    with pytest.raises(TournoiIntrouvable):
        monde.service.plan_de_cibles(999, 1)


def test_depart_dun_autre_tournoi_leve_depart_introuvable() -> None:
    """Garde 404 : un départ qui n'appartient pas au tournoi de l'URL n'existe pas pour lui."""
    monde = _Monde()
    autre = monde.tournois.ajouter(
        Tournoi(nom="Autre", date=_DATE, lieu=None, type_tournoi=TypeTournoi.NON_OFFICIEL)
    )
    assert autre.id is not None
    depart_autre = monde.departs.ajouter(Depart(tournoi_id=autre.id, numero=1, tarif_centimes=0))
    assert depart_autre.id is not None
    with pytest.raises(DepartIntrouvable):
        monde.service.plan_de_cibles(monde.tournoi_id, depart_autre.id)


def test_sans_gabarit_applique_leve_gabarit_du_tournoi_absent() -> None:
    """Sans gabarit appliqué au tournoi, il n'y a pas de cible à remplir → 404."""
    monde = _Monde(avec_gabarit=False)
    depart = monde.depart(1)
    with pytest.raises(GabaritDuTournoiAbsent):
        monde.service.plan_de_cibles(monde.tournoi_id, depart)


# --- Plan matérialisé et ajustable (E03US004, ADR-0024) ------------------------------------------
# Nuance vs l'en-tête de fichier (« tests après impl », qui vise l'orchestration E03US001) : les
# tests ci-dessous portent des **règles métier de service** (échange atomique, refus en bloc, dépôt
# réserve→occupée refusé, réserve motivée) et dérivent donc du **CA** d'E03US004 (`stories/`, puce
# CA + Notes) **avant** implémentation — règle 9.


def _cible_de(plan: object) -> dict[int, int]:
    """archer_id → index de cible où il est posé, pour les assertions de placement."""
    assert isinstance(plan, PlanDeCibles)
    return {p.archer_id: cible.index for cible in plan.cibles for p in cible.placements}


def test_lecture_avant_generation_met_tout_en_reserve() -> None:
    """ADR-0024 : la lecture ne recalcule plus ; sans génération, les inscrits sont en réserve."""
    monde = _Monde(capacites=(4,))
    depart = monde.depart(1)
    cat = monde.categorie(taille=0.25)
    a1 = monde.inscrire(depart, cat)

    plan = monde.service.plan_de_cibles(monde.tournoi_id, depart)

    assert _archers_places(plan.cibles) == set()
    assert {c.archer_id: c.raison for c in plan.conflits} == {a1: RaisonConflit.EN_RESERVE}


def test_deplacer_vers_une_case_libre() -> None:
    """CA glisser-déposer : l'archer va sur la case libre visée, l'autre ne bouge pas."""
    monde = _Monde(capacites=(4, 4))
    depart = monde.depart(1)
    cat = monde.categorie(taille=0.25)
    a1, a2 = monde.inscrire(depart, cat), monde.inscrire(depart, cat)
    service = monde.service
    service.regenerer(monde.tournoi_id, depart)

    plan = service.deplacer(monde.tournoi_id, depart, monde.inscription(a2), 2, "A")

    cible_de = _cible_de(plan)
    assert cible_de[a1] == 1
    assert cible_de[a2] == 2


def test_deplacement_invalide_est_refuse_etat_inchange() -> None:
    """CA invalide : poser un adulte sur une butte de U11 est refusé ; rien ne change."""
    monde = _Monde(capacites=(4, 4))
    depart = monde.depart(1)
    u11 = monde.inscrire(depart, monde.categorie(taille=0.25, hauteur=110))
    adulte = monde.inscrire(depart, monde.categorie(taille=0.25, hauteur=130))
    service = monde.service
    service.regenerer(monde.tournoi_id, depart)
    avant = _cible_de(service.plan_de_cibles(monde.tournoi_id, depart))

    with pytest.raises(DeplacementInvalide):
        service.deplacer(monde.tournoi_id, depart, monde.inscription(adulte), avant[u11], "B")

    assert _cible_de(service.plan_de_cibles(monde.tournoi_id, depart)) == avant


def test_mettre_en_reserve_libere_la_case() -> None:
    """CA réserve : mettre un archer en réserve (sans cible) le retire du plan (EN_RESERVE)."""
    monde = _Monde(capacites=(4,))
    depart = monde.depart(1)
    cat = monde.categorie(taille=0.25)
    a1 = monde.inscrire(depart, cat)
    service = monde.service
    service.regenerer(monde.tournoi_id, depart)

    plan = service.deplacer(monde.tournoi_id, depart, monde.inscription(a1), None, None)

    assert _archers_places(plan.cibles) == set()
    assert {c.archer_id: c.raison for c in plan.conflits} == {a1: RaisonConflit.EN_RESERVE}


def test_echange_atomique_permute_deux_archers() -> None:
    """CA échange : déposer un archer sur une case occupée permute les deux."""
    monde = _Monde(capacites=(4, 4))
    depart = monde.depart(1)
    cat = monde.categorie(taille=0.25)
    a1, a2 = monde.inscrire(depart, cat), monde.inscrire(depart, cat)
    service = monde.service
    service.regenerer(monde.tournoi_id, depart)
    service.deplacer(monde.tournoi_id, depart, monde.inscription(a2), 2, "A")  # a2 → cible 2

    plan = service.deplacer(monde.tournoi_id, depart, monde.inscription(a1), 2, "A")  # sur a2

    cible_de = _cible_de(plan)
    assert cible_de[a1] == 2
    assert cible_de[a2] == 1


def test_echange_refuse_en_bloc_si_un_ne_tient_pas() -> None:
    """CA échange : refus **en bloc** si l'un ne tient pas chez l'autre ; état inchangé.

    Deux U11 sur la cible 1, un adulte seul sur la cible 2 : échanger un U11 avec l'adulte
    mettrait l'adulte sur une butte de U11 (hauteur incompatible) → refus total."""
    monde = _Monde(capacites=(4, 4))
    depart = monde.depart(1)
    cat_u11 = monde.categorie(taille=0.25, hauteur=110)
    cat_adulte = monde.categorie(taille=0.25, hauteur=130)
    u11a, u11b = monde.inscrire(depart, cat_u11), monde.inscrire(depart, cat_u11)
    adulte = monde.inscrire(depart, cat_adulte)
    service = monde.service
    service.regenerer(monde.tournoi_id, depart)
    avant = _cible_de(service.plan_de_cibles(monde.tournoi_id, depart))

    with pytest.raises(DeplacementInvalide):
        service.deplacer(monde.tournoi_id, depart, monde.inscription(u11a), avant[adulte], "A")

    assert _cible_de(service.plan_de_cibles(monde.tournoi_id, depart)) == avant
    assert {u11a, u11b, adulte} == set(avant)


def test_deposer_depuis_la_reserve_sur_une_case_occupee_est_refuse() -> None:
    """CA échange : depuis la réserve, on ne peut pas prendre une case occupée (rien à permuter)."""
    monde = _Monde(capacites=(4,))
    depart = monde.depart(1)
    cat = monde.categorie(taille=0.25)
    a1, a2 = monde.inscrire(depart, cat), monde.inscrire(depart, cat)
    service = monde.service
    service.regenerer(monde.tournoi_id, depart)
    place = _cible_de(service.plan_de_cibles(monde.tournoi_id, depart))
    service.deplacer(monde.tournoi_id, depart, monde.inscription(a2), None, None)  # a2 en réserve

    with pytest.raises(DeplacementInvalide):
        service.deplacer(monde.tournoi_id, depart, monde.inscription(a2), place[a1], "A")


def test_placer_les_restants_comble_la_reserve_sans_bouger_les_places() -> None:
    """CA placer les restants : la réserve est reposée dans les trous, les placés ne bougent pas."""
    monde = _Monde(capacites=(4,))
    depart = monde.depart(1)
    cat = monde.categorie(taille=0.25)
    a1, a2 = monde.inscrire(depart, cat), monde.inscrire(depart, cat)
    service = monde.service
    service.regenerer(monde.tournoi_id, depart)
    service.deplacer(monde.tournoi_id, depart, monde.inscription(a2), None, None)  # a2 réserve

    plan = service.placer_les_restants(monde.tournoi_id, depart)

    assert _archers_places(plan.cibles) == {a1, a2}
    assert plan.conflits == ()


def test_regenerer_ecrase_les_ajustements_manuels() -> None:
    """CA annuler : régénérer repart de l'auto déterministe et efface les déplacements manuels."""
    monde = _Monde(capacites=(4, 4))
    depart = monde.depart(1)
    cat = monde.categorie(taille=0.25)
    a1, a2 = monde.inscrire(depart, cat), monde.inscrire(depart, cat)
    service = monde.service
    service.regenerer(monde.tournoi_id, depart)
    service.deplacer(monde.tournoi_id, depart, monde.inscription(a2), 2, "A")  # ajustement manuel

    plan = service.regenerer(monde.tournoi_id, depart)  # « annuler les modifications »

    cible_de = _cible_de(plan)
    assert cible_de[a1] == 1
    assert cible_de[a2] == 1  # l'auto les remet ensemble sur la cible 1


def test_echange_sur_la_meme_cible_permute_les_positions() -> None:
    """CA échange : permuter deux archers d'une **même** cible échange leurs positions."""
    monde = _Monde(capacites=(4,))
    depart = monde.depart(1)
    cat = monde.categorie(taille=0.25)
    a1, a2 = monde.inscrire(depart, cat), monde.inscrire(depart, cat)
    service = monde.service
    service.regenerer(monde.tournoi_id, depart)  # a1 en A, a2 en B (tri déterministe par id)

    # a1 déposé sur la case de a2 (B) → permutation des positions sur la même cible.
    plan = service.deplacer(monde.tournoi_id, depart, monde.inscription(a1), 1, "B")

    positions = {p.archer_id: p.position for cible in plan.cibles for p in cible.placements}
    assert positions[a1] == "B"
    assert positions[a2] == "A"


def test_cible_disparue_du_gabarit_retombe_en_reserve() -> None:
    """Revue C1/D « archers fantômes » : réduire le gabarit après matérialisation renvoie l'archer
    d'une cible disparue **en réserve**, jamais perdu (ligne rouge « aucun archer perdu »)."""
    monde = _Monde(capacites=(4, 4))
    depart = monde.depart(1)
    cat = monde.categorie(taille=0.25)
    a1, a2 = monde.inscrire(depart, cat), monde.inscrire(depart, cat)
    service = monde.service
    service.regenerer(monde.tournoi_id, depart)
    service.deplacer(monde.tournoi_id, depart, monde.inscription(a2), 2, "A")  # a2 sur la cible 2
    # La salle est reconfigurée à 1 cible : la cible 2 disparaît du gabarit courant.
    monde.gabarits.ajouter(GabaritSalle(nom="Salle", capacites=(4,), tournoi_id=monde.tournoi_id))

    plan = service.plan_de_cibles(monde.tournoi_id, depart)

    places = _archers_places(plan.cibles)
    reserve = {conflit.archer_id for conflit in plan.conflits}
    assert a1 in places
    assert a2 not in places
    assert a2 in reserve  # retombé en réserve, pas disparu en silence


def test_placer_les_restants_repose_un_archer_de_cible_disparue() -> None:
    """Revue D (F1) : après réduction du gabarit, « placer les restants » **repose** l'archer
    retombé en réserve dans une cible restante — le bouton n'est pas inopérant pour lui."""
    monde = _Monde(capacites=(4, 4))
    depart = monde.depart(1)
    cat = monde.categorie(taille=0.25)
    a1, a2 = monde.inscrire(depart, cat), monde.inscrire(depart, cat)
    service = monde.service
    service.regenerer(monde.tournoi_id, depart)
    service.deplacer(monde.tournoi_id, depart, monde.inscription(a2), 2, "A")  # a2 sur la cible 2
    monde.gabarits.ajouter(GabaritSalle(nom="Salle", capacites=(4,), tournoi_id=monde.tournoi_id))
    # a2 est retombé en réserve (cible 2 disparue) ; « placer les restants » doit le reposer.

    plan = service.placer_les_restants(monde.tournoi_id, depart)

    assert _archers_places(plan.cibles) == {a1, a2}
    assert plan.conflits == ()


# --- Alerte par calcul d'impact (E12US007, ADR-0040) ---------------------------------------------
# Tests dérivés du **CA** (`stories/E12-pilotage-jour-j.md`, E12US007 + section « Arbitrages »)
# **avant**
# implémentation (règle 9) : l'échelle d'impact et le geste délibéré sur la régénération massive
# sont
# des règles métier. L'endpoint/DTO se testent après (test_placement_api).


def test_impact_sans_placement_est_aucun() -> None:
    """Plan jamais généré : impact nul (aucune affectation) → aucune alerte, première génération."""
    monde = _Monde(capacites=(4,))
    depart = monde.depart(1)
    monde.inscrire(depart, monde.categorie(taille=0.25))

    impact = monde.service.impact_regeneration(monde.tournoi_id, depart)

    assert impact.niveau is NiveauImpact.AUCUN
    assert impact.archers_deplaces == 0


def test_impact_apres_placement_sans_score_est_confirmation() -> None:
    """Des archers placés mais **aucun score** : niveau confirmation, cibles avec scores = 0."""
    monde = _Monde(capacites=(4,))
    depart = monde.depart(1)
    cat = monde.categorie(taille=0.25)
    monde.inscrire(depart, cat)
    monde.inscrire(depart, cat)
    service = monde.service
    service.regenerer(monde.tournoi_id, depart)

    impact = service.impact_regeneration(monde.tournoi_id, depart)

    assert impact.niveau is NiveauImpact.CONFIRMATION
    assert impact.archers_deplaces == 2
    assert impact.cibles_avec_scores == 0


def test_impact_compte_les_cibles_avec_scores_sans_doublon() -> None:
    """Un score rend l'impact **massif** ; deux archers scorés d'**une même cible** comptent pour 1.

    Prouve que `cibles_avec_scores` dédoublonne par cible (pas par archer) — c'est bien « M cibles
    ont des scores » du CDC, pas « M archers »."""
    monde = _Monde(capacites=(4,))
    depart = monde.depart(1)
    cat = monde.categorie(taille=0.25)
    a1 = monde.inscrire(depart, cat)
    a2 = monde.inscrire(depart, cat)
    service = monde.service
    service.regenerer(monde.tournoi_id, depart)  # a1 et a2 sur la même cible 1
    monde.semer_score(a1)
    monde.semer_score(a2)

    impact = service.impact_regeneration(monde.tournoi_id, depart)

    assert impact.niveau is NiveauImpact.MASSIF
    assert impact.archers_deplaces == 2
    assert impact.cibles_avec_scores == 1  # une seule cible, malgré deux archers scorés


def test_impact_compte_les_cibles_scorees_de_maniere_additive() -> None:
    """Le chiffre-titre « M cibles » s'additionne sur des cibles **distinctes** (U11 et adulte
    séparés par la hauteur, ADR-0022) : deux cibles scorées → 2, pas 1."""
    monde = _Monde(capacites=(4, 4))
    depart = monde.depart(1)
    u11 = monde.inscrire(depart, monde.categorie(taille=0.25, hauteur=110))
    adulte = monde.inscrire(depart, monde.categorie(taille=0.25, hauteur=130))
    service = monde.service
    service.regenerer(monde.tournoi_id, depart)  # u11 et adulte sur deux cibles distinctes
    monde.semer_score(u11)
    monde.semer_score(adulte)

    impact = service.impact_regeneration(monde.tournoi_id, depart)

    assert impact.niveau is NiveauImpact.MASSIF
    assert impact.cibles_avec_scores == 2


def test_impact_exclut_une_cible_sans_score() -> None:
    """Parmi plusieurs cibles, seules celles avec **au moins un archer scoré** comptent : la cible
    sans donnée réelle est exclue (une scorée sur deux → 1)."""
    monde = _Monde(capacites=(4, 4))
    depart = monde.depart(1)
    u11 = monde.inscrire(depart, monde.categorie(taille=0.25, hauteur=110))
    monde.inscrire(depart, monde.categorie(taille=0.25, hauteur=130))  # adulte, non scoré
    service = monde.service
    service.regenerer(monde.tournoi_id, depart)
    monde.semer_score(u11)  # seule la cible de l'U11 a un score

    impact = service.impact_regeneration(monde.tournoi_id, depart)

    assert impact.niveau is NiveauImpact.MASSIF
    assert impact.cibles_avec_scores == 1


def test_regenerer_massif_sans_confirmation_est_refuse_et_chiffre() -> None:
    """CA : une régénération massive **non confirmée** est refusée (409 chiffré) ; rien ne change.

    Le décompte est porté par `details` (première utilisation du canal `{code, message,
    details?}`) —
    et **recalculé** ici, pas cru sur parole (ce qui distingue de DETTE-007)."""
    monde = _Monde(capacites=(4,))
    depart = monde.depart(1)
    cat = monde.categorie(taille=0.25)
    a1 = monde.inscrire(depart, cat)
    monde.inscrire(depart, cat)
    service = monde.service
    service.regenerer(monde.tournoi_id, depart)
    monde.semer_score(a1)
    avant = _cible_de(service.plan_de_cibles(monde.tournoi_id, depart))

    with pytest.raises(ReplacementNonConfirme) as exc:
        service.regenerer(monde.tournoi_id, depart)

    assert exc.value.details == {"archers_deplaces": 2, "cibles_avec_scores": 1}
    assert _cible_de(service.plan_de_cibles(monde.tournoi_id, depart)) == avant  # état inchangé
    assert monde.placements.traces == []  # rien écrit → rien tracé


def test_regenerer_massif_confirme_ecrase_et_laisse_une_trace() -> None:
    """CA : confirmée, la régénération massive écrase le plan **et** laisse une trace d'audit datée.

    La trace co-écrite (ADR-0035) porte l'action `REPLACEMENT`, l'objet (le départ), l'horodatage de
    l'**horloge injectée** (déterminisme) et le décompte chiffré en `avant` — la valeur de
    preuve."""
    monde = _Monde(capacites=(4,))
    depart = monde.depart(1)
    cat = monde.categorie(taille=0.25)
    a1 = monde.inscrire(depart, cat)
    a2 = monde.inscrire(depart, cat)
    service = monde.service
    service.regenerer(monde.tournoi_id, depart)
    monde.semer_score(a1)

    plan = service.regenerer(monde.tournoi_id, depart, confirme=True)

    assert _archers_places(plan.cibles) == {a1, a2}  # plan bien régénéré
    assert len(monde.placements.traces) == 1
    trace = monde.placements.traces[0]
    assert trace.action is ActionAuditee.REPLACEMENT
    assert trace.tournoi_id == monde.tournoi_id
    assert str(depart) in trace.objet
    assert trace.horodatage == _QUAND
    assert "2 archer" in (trace.avant or "")


def test_regenerer_sans_score_ne_demande_ni_confirmation_ni_trace() -> None:
    """CA « pas d'impact → aucune alerte » : régénérer un plan **sans score** passe sans confirmer
    ni tracer — même en cours de tournoi, tant qu'aucune donnée réelle n'a été produite."""
    monde = _Monde(capacites=(4,))
    depart = monde.depart(1)
    cat = monde.categorie(taille=0.25)
    monde.inscrire(depart, cat)
    monde.inscrire(depart, cat)
    service = monde.service
    service.regenerer(monde.tournoi_id, depart)

    plan = service.regenerer(monde.tournoi_id, depart)  # aucun score → pas de garde

    assert len(plan.cibles) == 1
    assert monde.placements.traces == []
