"""Tests du service applicatif Tournois (E00US009, E01US001, E01US002, E01US017, E02US010).

Le service est testé **en isolation** du domaine d'infrastructure : de faux repositories
en mémoire (conformes aux ports `TournoiRepository` et `DepartRepository`) suffisent — ni base ni
serveur. Depuis E02US010, `ServiceTournois` lit aussi les **départs** : le passage à `prêt` exige au
moins un créneau (garde `TournoiSansDepart`), d'où le dépôt de départs injecté.
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.erreurs import (
    TournoiArchiveNonModifiable,
    TournoiEnCoursNonSupprimable,
    TournoiIntrouvable,
    TournoiSansDepart,
    TransitionStatutInvalide,
)
from application.tournois import ServiceTournois
from domain.depart import Depart
from domain.erreurs import NomTournoiInvalide
from domain.tournoi import StatutTournoi, Tournoi, TournoiId, TypeTournoi
from tests.conftest import FauxDepartRepository

_DATE = datetime.date(2026, 3, 14)


class FauxTournoiRepository:
    """Repository en mémoire conforme au port `TournoiRepository`."""

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
        assert tournoi.id in self._tournois, "Tournoi à mettre à jour absent."
        self._tournois[tournoi.id] = tournoi
        return tournoi

    def supprimer(self, tournoi_id: TournoiId) -> None:
        del self._tournois[tournoi_id]


def _service() -> tuple[ServiceTournois, FauxDepartRepository]:
    """Fabrique le service et son dépôt de départs (à garnir pour les tests de passage à `prêt`)."""
    departs = FauxDepartRepository()
    return ServiceTournois(FauxTournoiRepository(), departs), departs


def _id_cree(service: ServiceTournois, departs: FauxDepartRepository, nom: str = "Trophée") -> int:
    """Crée un tournoi **avec un départ** — condition du passage à `prêt` (E02US010).

    Tous les tests de cycle de vie amènent un tournoi jusqu'à `prêt`/`en_cours`/… : sans départ, la
    garde `TournoiSansDepart` les bloquerait. Le créneau est ici un détail d'attelage, pas le sujet.
    """
    cree = service.creer(nom, _DATE)
    assert cree.id is not None
    departs.ajouter(Depart.creer(cree.id, 1, 810, "09:00"))
    return cree.id


def test_creer_persiste_et_attribue_un_id() -> None:
    """`creer` délègue au repository, qui attribue l'identifiant."""
    service, _ = _service()
    tournoi = service.creer("Salle 18m", _DATE, "Quimper", TypeTournoi.OFFICIEL)
    assert tournoi.id == 1
    assert tournoi.nom == "Salle 18m"
    assert tournoi.date == _DATE
    assert tournoi.lieu == "Quimper"
    assert tournoi.type_tournoi is TypeTournoi.OFFICIEL


def test_creer_propage_l_erreur_de_domaine() -> None:
    """Un nom invalide fait remonter l'erreur du domaine (non persisté)."""
    service, _ = _service()
    with pytest.raises(NomTournoiInvalide):
        service.creer("  ", _DATE)


def test_consulter_relit_un_tournoi_existant() -> None:
    """`consulter` renvoie l'agrégat persisté."""
    service, _ = _service()
    cree = service.creer("Trophée", _DATE)
    assert cree.id is not None
    assert service.consulter(cree.id) == cree


def test_consulter_leve_si_introuvable() -> None:
    """`consulter` lève `TournoiIntrouvable` pour un identifiant inconnu."""
    service, _ = _service()
    with pytest.raises(TournoiIntrouvable):
        service.consulter(404)


def test_lister_renvoie_tous_les_tournois() -> None:
    """`lister` renvoie tous les tournois créés."""
    service, _ = _service()
    assert service.lister() == []
    service.creer("A", _DATE)
    service.creer("B", _DATE)
    assert [t.nom for t in service.lister()] == ["A", "B"]


# --- Édition des métadonnées (E01US002) ---


def test_modifier_persiste_les_metadonnees() -> None:
    """`modifier` met à jour le tournoi et conserve son identifiant."""
    service, _ = _service()
    cree = service.creer("Ancien", _DATE)
    assert cree.id is not None
    modifie = service.modifier(cree.id, "Nouveau", _DATE, "Quimper", TypeTournoi.OFFICIEL)
    assert modifie.id == cree.id
    assert modifie.nom == "Nouveau"
    assert modifie.lieu == "Quimper"
    assert modifie.type_tournoi is TypeTournoi.OFFICIEL
    assert service.consulter(cree.id) == modifie


def test_modifier_leve_si_introuvable() -> None:
    """`modifier` lève `TournoiIntrouvable` pour un identifiant inconnu."""
    service, _ = _service()
    with pytest.raises(TournoiIntrouvable):
        service.modifier(404, "X", _DATE)


def test_modifier_propage_l_erreur_de_domaine() -> None:
    """Un nom vide fait remonter l'erreur du domaine (non persisté)."""
    service, _ = _service()
    cree = service.creer("Trophée", _DATE)
    assert cree.id is not None
    with pytest.raises(NomTournoiInvalide):
        service.modifier(cree.id, "   ", _DATE)


# --- Cycle de vie enrichi (E01US017, ADR-0026 §2) : graphe des transitions ---
# Depuis E02US010, `vers_pret` exige **au moins un départ** : `_id_cree` en sème un, donc les tests
# de graphe atteignent `prêt`. La garde « ≥ 1 départ » a ses propres tests plus bas ; le reste de la
# complétude de préparation (catégories, blasons, gabarit, barème) viendra d'une tranche ultérieure.


def _amener(service: ServiceTournois, tid: int, statut: StatutTournoi) -> None:
    """Amène un tournoi neuf (brouillon) au statut voulu par le chemin nominal du graphe."""
    if statut is StatutTournoi.BROUILLON:
        return
    service.vers_pret(tid)
    if statut is StatutTournoi.PRET:
        return
    service.demarrer(tid)  # en_cours
    if statut is StatutTournoi.EN_COURS:
        return
    if statut is StatutTournoi.EN_PAUSE:
        service.mettre_en_pause(tid)
        return
    service.terminer(tid)  # termine
    if statut is StatutTournoi.TERMINE:
        return
    if statut is StatutTournoi.ARCHIVE:
        service.archiver(tid)
        return
    raise AssertionError(f"Chemin non couvert pour {statut}.")


def test_chemin_nominal_brouillon_pret_en_cours_termine_archive() -> None:
    """Le chemin de vie complet enchaîne les cinq statuts nominaux dans l'ordre."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    assert service.consulter(tid).statut is StatutTournoi.BROUILLON
    assert service.vers_pret(tid).statut is StatutTournoi.PRET
    assert service.demarrer(tid).statut is StatutTournoi.EN_COURS
    assert service.terminer(tid).statut is StatutTournoi.TERMINE
    assert service.archiver(tid).statut is StatutTournoi.ARCHIVE


def test_pret_peut_revenir_brouillon() -> None:
    """`brouillon ⇄ prêt` : un tournoi prêt peut revenir en brouillon pour rééditer."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    service.vers_pret(tid)
    assert service.revenir_brouillon(tid).statut is StatutTournoi.BROUILLON


def test_pause_puis_reprise() -> None:
    """`en_cours ⇄ en_pause` : mise en pause réversible sans terminer."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    _amener(service, tid, StatutTournoi.EN_COURS)
    assert service.mettre_en_pause(tid).statut is StatutTournoi.EN_PAUSE
    assert service.reprendre(tid).statut is StatutTournoi.EN_COURS


# --- Garde « ≥ 1 départ » du passage à prêt (E02US010) ---


def test_vers_pret_refuse_un_tournoi_sans_depart() -> None:
    """Un brouillon **sans départ** ne peut pas passer prêt → `TournoiSansDepart` (→ 409)."""
    service, _ = _service()
    cree = service.creer("Sans créneau", _DATE)
    assert cree.id is not None
    with pytest.raises(TournoiSansDepart):
        service.vers_pret(cree.id)
    assert service.consulter(cree.id).statut is StatutTournoi.BROUILLON


def test_vers_pret_accepte_des_qu_il_y_a_un_depart() -> None:
    """Dès qu'un créneau existe, le passage à prêt est permis (E02US010)."""
    service, departs = _service()
    tid = _id_cree(service, departs)  # sème un départ
    assert service.vers_pret(tid).statut is StatutTournoi.PRET


@pytest.mark.parametrize("depuis", [StatutTournoi.BROUILLON, StatutTournoi.EN_COURS])
def test_vers_pret_refuse_hors_brouillon(depuis: StatutTournoi) -> None:
    """`vers_pret` n'est légal que depuis `brouillon` (en cours → 409)."""
    if depuis is StatutTournoi.BROUILLON:
        return  # cas légal, couvert ailleurs
    service, departs = _service()
    tid = _id_cree(service, departs)
    _amener(service, tid, depuis)
    with pytest.raises(TransitionStatutInvalide):
        service.vers_pret(tid)


def test_demarrer_refuse_si_pas_pret() -> None:
    """Démarrer passe désormais par `prêt` : depuis un brouillon → 409."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    with pytest.raises(TransitionStatutInvalide):
        service.demarrer(tid)  # encore brouillon, pas prêt


def test_reprendre_refuse_si_pas_en_pause() -> None:
    """Reprendre un tournoi qui n'est pas en pause lève `TransitionStatutInvalide`."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    _amener(service, tid, StatutTournoi.EN_COURS)
    with pytest.raises(TransitionStatutInvalide):
        service.reprendre(tid)


def test_terminer_refuse_si_pas_en_cours() -> None:
    """Terminer un tournoi non démarré lève `TransitionStatutInvalide` (→ 409)."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    with pytest.raises(TransitionStatutInvalide):
        service.terminer(tid)


def test_archiver_refuse_si_pas_termine() -> None:
    """Archiver un tournoi non terminé lève `TransitionStatutInvalide` (→ 409)."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    _amener(service, tid, StatutTournoi.EN_COURS)
    with pytest.raises(TransitionStatutInvalide):
        service.archiver(tid)


@pytest.mark.parametrize(
    "depuis",
    [
        StatutTournoi.BROUILLON,
        StatutTournoi.PRET,
        StatutTournoi.EN_COURS,
        StatutTournoi.EN_PAUSE,
    ],
)
def test_annuler_depuis_les_etats_vivants(depuis: StatutTournoi) -> None:
    """`annuler` part de brouillon/prêt/en_cours/en_pause et mène à `annulé` (terminal)."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    _amener(service, tid, depuis)
    assert service.annuler(tid).statut is StatutTournoi.ANNULE


@pytest.mark.parametrize("depuis", [StatutTournoi.TERMINE, StatutTournoi.ARCHIVE])
def test_annuler_refuse_depuis_termine_ou_archive(depuis: StatutTournoi) -> None:
    """On n'annule pas un tournoi joué jusqu'au bout (terminé) ni archivé (→ 409)."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    _amener(service, tid, depuis)
    with pytest.raises(TransitionStatutInvalide):
        service.annuler(tid)


# --- Transitions offertes (E14US001) : cohérence topologie ↔ gardes ---
# `transitions_possibles` (topologie du domaine, lue par l'accueil admin) et les gardes `depuis`
# éparpillées dans le service sont **deux encodages** du même graphe : ce test les recoupe pour
# qu'ils ne divergent pas (règle 1, anti-duplication). C'est un test **après** implémentation — la
# règle métier vit dans le domaine (testée depuis le CA dans `test_domain_tournoi`), ici on vérifie
# le **câblage** service ↔ domaine.

_TOUS_LES_NOMS = {
    "vers-pret",
    "revenir-brouillon",
    "demarrer",
    "mettre-en-pause",
    "reprendre",
    "terminer",
    "archiver",
    "annuler",
}


def _amener_complet(service: ServiceTournois, tid: int, statut: StatutTournoi) -> None:
    """Comme `_amener`, mais couvre aussi `annulé` (annuler depuis brouillon)."""
    if statut is StatutTournoi.ANNULE:
        service.annuler(tid)
        return
    _amener(service, tid, statut)


def _appliquer(service: ServiceTournois, tid: int, nom: str) -> None:
    """Applique la transition d'identifiant `nom` (suffixe d'endpoint) sur le service."""
    getattr(service, nom.replace("-", "_"))(tid)


@pytest.mark.parametrize("statut", list(StatutTournoi))
def test_transitions_possibles_coherentes_avec_les_gardes(statut: StatutTournoi) -> None:
    """Pour chaque statut, les transitions offertes sont exactement celles acceptées par le service.

    Toute arête **offerte** par `transitions_possibles` est acceptée (aucune
    `TransitionStatutInvalide`) ; toute arête **non offerte** est refusée (→ 409). Un départ est
    semé (`_id_cree`), donc `vers-pret` n'est pas bloquée par la garde de complétude `≥ 1 départ`.
    """
    service, departs = _service()
    tid = _id_cree(service, departs)
    _amener_complet(service, tid, statut)
    offertes = {transition.nom for transition in service.transitions_possibles(tid)}

    for nom in _TOUS_LES_NOMS:
        # Appliquer une transition mute l'état : on repart d'un tournoi neuf au même statut.
        autre, autres_departs = _service()
        autre_tid = _id_cree(autre, autres_departs)
        _amener_complet(autre, autre_tid, statut)
        if nom in offertes:
            try:
                _appliquer(autre, autre_tid, nom)
            except TransitionStatutInvalide:  # pragma: no cover - filet anti-régression
                pytest.fail(f"{nom} offerte depuis {statut} mais refusée par le service.")
        else:
            with pytest.raises(TransitionStatutInvalide):
                _appliquer(autre, autre_tid, nom)


def test_transitions_possibles_leve_si_introuvable() -> None:
    """`transitions_possibles` relit le tournoi : identifiant inconnu → `TournoiIntrouvable`."""
    service, _ = _service()
    with pytest.raises(TournoiIntrouvable):
        service.transitions_possibles(404)


def test_modifier_refuse_si_archive() -> None:
    """Un tournoi archivé est en lecture seule → `TournoiArchiveNonModifiable` (409)."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    _amener(service, tid, StatutTournoi.ARCHIVE)
    with pytest.raises(TournoiArchiveNonModifiable):
        service.modifier(tid, "Renommé", _DATE)


# --- Suppression (E01US002, permissions élargies E01US017) ---


@pytest.mark.parametrize(
    "depuis",
    [StatutTournoi.BROUILLON, StatutTournoi.PRET, StatutTournoi.TERMINE],
)
def test_supprimer_autorise_hors_etats_vivants(depuis: StatutTournoi) -> None:
    """Un tournoi brouillon, prêt ou terminé est supprimable."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    _amener(service, tid, depuis)
    service.supprimer(tid)
    assert service.lister() == []


def test_supprimer_un_annule() -> None:
    """Un tournoi annulé (trace) reste supprimable si on veut vraiment l'effacer."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    service.annuler(tid)
    service.supprimer(tid)
    assert service.lister() == []


@pytest.mark.parametrize("depuis", [StatutTournoi.EN_COURS, StatutTournoi.EN_PAUSE])
def test_supprimer_refuse_si_vivant(depuis: StatutTournoi) -> None:
    """Un tournoi en cours ou en pause n'est pas supprimable → `TournoiEnCoursNonSupprimable`."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    _amener(service, tid, depuis)
    with pytest.raises(TournoiEnCoursNonSupprimable):
        service.supprimer(tid)
    assert service.consulter(tid).statut is depuis


def test_supprimer_refuse_si_archive() -> None:
    """Un tournoi archivé est en lecture seule → `TournoiArchiveNonModifiable` (409)."""
    service, departs = _service()
    tid = _id_cree(service, departs)
    _amener(service, tid, StatutTournoi.ARCHIVE)
    with pytest.raises(TournoiArchiveNonModifiable):
        service.supprimer(tid)
    assert service.consulter(tid).statut is StatutTournoi.ARCHIVE


def test_supprimer_leve_si_introuvable() -> None:
    """`supprimer` lève `TournoiIntrouvable` pour un identifiant inconnu."""
    service, _ = _service()
    with pytest.raises(TournoiIntrouvable):
        service.supprimer(404)
