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
    TournoiIntrouvable,
)
from application.placement import ServicePlacement
from domain.archer import Archer
from domain.blason import Blason, BlasonId
from domain.categorie import Categorie
from domain.depart import Depart, DepartId
from domain.gabarit_salle import GabaritSalle, GabaritSalleId
from domain.inscription import Inscription, InscriptionId
from domain.placement import Affectation, CiblePlacee, PlanDeCibles, RaisonConflit
from domain.tournoi import Tournoi, TournoiId, TypeTournoi
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxDepartRepository,
    FauxInscriptionRepository,
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
    """Repository en mémoire conforme au port `PlacementRepository` (E03US004).

    Stocke une affectation par inscription, avec son départ, pour rejouer `par_depart`,
    `definir_plan` (purge + réécriture), `poser_plusieurs` (upsert) et `retirer`."""

    def __init__(self) -> None:
        self._affectation: dict[int, Affectation] = {}
        self._depart: dict[int, int] = {}

    def par_depart(self, depart_id: DepartId) -> list[Affectation]:
        affectations = [a for i, a in self._affectation.items() if self._depart[i] == depart_id]
        return sorted(affectations, key=lambda a: (a.cible_index, a.position))

    def definir_plan(self, depart_id: DepartId, affectations: Sequence[Affectation]) -> None:
        for inscription_id in [i for i, d in self._depart.items() if d == depart_id]:
            self._affectation.pop(inscription_id, None)
            self._depart.pop(inscription_id, None)
        self.poser_plusieurs(depart_id, affectations)

    def poser_plusieurs(self, depart_id: DepartId, affectations: Sequence[Affectation]) -> None:
        for affectation in affectations:
            self._affectation[affectation.inscription_id] = affectation
            self._depart[affectation.inscription_id] = depart_id

    def retirer(self, inscription_id: InscriptionId) -> None:
        self._affectation.pop(inscription_id, None)
        self._depart.pop(inscription_id, None)


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
        )

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
