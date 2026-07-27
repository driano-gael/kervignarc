"""Tests du service applicatif Tournois (E00US009, E01US001, E01US002) — repository factice.

Le service est testé **en isolation** du domaine d'infrastructure : un faux repository
en mémoire (conforme au port `TournoiRepository`) suffit — ni base ni serveur.
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.erreurs import (
    TournoiArchiveNonModifiable,
    TournoiEnCoursNonSupprimable,
    TournoiIntrouvable,
    TransitionStatutInvalide,
)
from application.tournois import ServiceTournois
from domain.erreurs import NomTournoiInvalide
from domain.tournoi import StatutTournoi, Tournoi, TournoiId, TypeTournoi

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


def test_creer_persiste_et_attribue_un_id() -> None:
    """`creer` délègue au repository, qui attribue l'identifiant."""
    service = ServiceTournois(FauxTournoiRepository())
    tournoi = service.creer("Salle 18m", _DATE, "Quimper", TypeTournoi.OFFICIEL)
    assert tournoi.id == 1
    assert tournoi.nom == "Salle 18m"
    assert tournoi.date == _DATE
    assert tournoi.lieu == "Quimper"
    assert tournoi.type_tournoi is TypeTournoi.OFFICIEL


def test_creer_propage_l_erreur_de_domaine() -> None:
    """Un nom invalide fait remonter l'erreur du domaine (non persisté)."""
    service = ServiceTournois(FauxTournoiRepository())
    with pytest.raises(NomTournoiInvalide):
        service.creer("  ", _DATE)


def test_consulter_relit_un_tournoi_existant() -> None:
    """`consulter` renvoie l'agrégat persisté."""
    service = ServiceTournois(FauxTournoiRepository())
    cree = service.creer("Trophée", _DATE)
    assert cree.id is not None
    assert service.consulter(cree.id) == cree


def test_consulter_leve_si_introuvable() -> None:
    """`consulter` lève `TournoiIntrouvable` pour un identifiant inconnu."""
    service = ServiceTournois(FauxTournoiRepository())
    with pytest.raises(TournoiIntrouvable):
        service.consulter(404)


def test_lister_renvoie_tous_les_tournois() -> None:
    """`lister` renvoie tous les tournois créés."""
    service = ServiceTournois(FauxTournoiRepository())
    assert service.lister() == []
    service.creer("A", _DATE)
    service.creer("B", _DATE)
    assert [t.nom for t in service.lister()] == ["A", "B"]


# --- Édition des métadonnées (E01US002) ---


def test_modifier_persiste_les_metadonnees() -> None:
    """`modifier` met à jour le tournoi et conserve son identifiant."""
    service = ServiceTournois(FauxTournoiRepository())
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
    service = ServiceTournois(FauxTournoiRepository())
    with pytest.raises(TournoiIntrouvable):
        service.modifier(404, "X", _DATE)


def test_modifier_propage_l_erreur_de_domaine() -> None:
    """Un nom vide fait remonter l'erreur du domaine (non persisté)."""
    service = ServiceTournois(FauxTournoiRepository())
    cree = service.creer("Trophée", _DATE)
    assert cree.id is not None
    with pytest.raises(NomTournoiInvalide):
        service.modifier(cree.id, "   ", _DATE)


# --- Cycle de vie enrichi (E01US017, ADR-0026 §2) : graphe des transitions ---
# La garde de complétude du passage `brouillon → prêt` (E12US005 à froid) arrive avec la tranche
# suivante ; ici `vers_pret` n'est gardé que par la légalité de l'arête — un brouillon quelconque
# atteint `prêt` dans ces tests de graphe.


def _id_cree(service: ServiceTournois, nom: str = "Trophée") -> int:
    cree = service.creer(nom, _DATE)
    assert cree.id is not None
    return cree.id


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
    service = ServiceTournois(FauxTournoiRepository())
    tid = _id_cree(service)
    assert service.consulter(tid).statut is StatutTournoi.BROUILLON
    assert service.vers_pret(tid).statut is StatutTournoi.PRET
    assert service.demarrer(tid).statut is StatutTournoi.EN_COURS
    assert service.terminer(tid).statut is StatutTournoi.TERMINE
    assert service.archiver(tid).statut is StatutTournoi.ARCHIVE


def test_pret_peut_revenir_brouillon() -> None:
    """`brouillon ⇄ prêt` : un tournoi prêt peut revenir en brouillon pour rééditer."""
    service = ServiceTournois(FauxTournoiRepository())
    tid = _id_cree(service)
    service.vers_pret(tid)
    assert service.revenir_brouillon(tid).statut is StatutTournoi.BROUILLON


def test_pause_puis_reprise() -> None:
    """`en_cours ⇄ en_pause` : mise en pause réversible sans terminer."""
    service = ServiceTournois(FauxTournoiRepository())
    tid = _id_cree(service)
    _amener(service, tid, StatutTournoi.EN_COURS)
    assert service.mettre_en_pause(tid).statut is StatutTournoi.EN_PAUSE
    assert service.reprendre(tid).statut is StatutTournoi.EN_COURS


@pytest.mark.parametrize("depuis", [StatutTournoi.BROUILLON, StatutTournoi.EN_COURS])
def test_vers_pret_refuse_hors_brouillon(depuis: StatutTournoi) -> None:
    """`vers_pret` n'est légal que depuis `brouillon` (en cours → 409)."""
    if depuis is StatutTournoi.BROUILLON:
        return  # cas légal, couvert ailleurs
    service = ServiceTournois(FauxTournoiRepository())
    tid = _id_cree(service)
    _amener(service, tid, depuis)
    with pytest.raises(TransitionStatutInvalide):
        service.vers_pret(tid)


def test_demarrer_refuse_si_pas_pret() -> None:
    """Démarrer passe désormais par `prêt` : depuis un brouillon → 409."""
    service = ServiceTournois(FauxTournoiRepository())
    tid = _id_cree(service)
    with pytest.raises(TransitionStatutInvalide):
        service.demarrer(tid)  # encore brouillon, pas prêt


def test_reprendre_refuse_si_pas_en_pause() -> None:
    """Reprendre un tournoi qui n'est pas en pause lève `TransitionStatutInvalide`."""
    service = ServiceTournois(FauxTournoiRepository())
    tid = _id_cree(service)
    _amener(service, tid, StatutTournoi.EN_COURS)
    with pytest.raises(TransitionStatutInvalide):
        service.reprendre(tid)


def test_terminer_refuse_si_pas_en_cours() -> None:
    """Terminer un tournoi non démarré lève `TransitionStatutInvalide` (→ 409)."""
    service = ServiceTournois(FauxTournoiRepository())
    tid = _id_cree(service)
    with pytest.raises(TransitionStatutInvalide):
        service.terminer(tid)


def test_archiver_refuse_si_pas_termine() -> None:
    """Archiver un tournoi non terminé lève `TransitionStatutInvalide` (→ 409)."""
    service = ServiceTournois(FauxTournoiRepository())
    tid = _id_cree(service)
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
    service = ServiceTournois(FauxTournoiRepository())
    tid = _id_cree(service)
    _amener(service, tid, depuis)
    assert service.annuler(tid).statut is StatutTournoi.ANNULE


@pytest.mark.parametrize("depuis", [StatutTournoi.TERMINE, StatutTournoi.ARCHIVE])
def test_annuler_refuse_depuis_termine_ou_archive(depuis: StatutTournoi) -> None:
    """On n'annule pas un tournoi joué jusqu'au bout (terminé) ni archivé (→ 409)."""
    service = ServiceTournois(FauxTournoiRepository())
    tid = _id_cree(service)
    _amener(service, tid, depuis)
    with pytest.raises(TransitionStatutInvalide):
        service.annuler(tid)


def test_modifier_refuse_si_archive() -> None:
    """Un tournoi archivé est en lecture seule → `TournoiArchiveNonModifiable` (409)."""
    service = ServiceTournois(FauxTournoiRepository())
    tid = _id_cree(service)
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
    service = ServiceTournois(FauxTournoiRepository())
    tid = _id_cree(service)
    _amener(service, tid, depuis)
    service.supprimer(tid)
    assert service.lister() == []


def test_supprimer_un_annule() -> None:
    """Un tournoi annulé (trace) reste supprimable si on veut vraiment l'effacer."""
    service = ServiceTournois(FauxTournoiRepository())
    tid = _id_cree(service)
    service.annuler(tid)
    service.supprimer(tid)
    assert service.lister() == []


@pytest.mark.parametrize("depuis", [StatutTournoi.EN_COURS, StatutTournoi.EN_PAUSE])
def test_supprimer_refuse_si_vivant(depuis: StatutTournoi) -> None:
    """Un tournoi en cours ou en pause n'est pas supprimable → `TournoiEnCoursNonSupprimable`."""
    service = ServiceTournois(FauxTournoiRepository())
    tid = _id_cree(service)
    _amener(service, tid, depuis)
    with pytest.raises(TournoiEnCoursNonSupprimable):
        service.supprimer(tid)
    assert service.consulter(tid).statut is depuis


def test_supprimer_refuse_si_archive() -> None:
    """Un tournoi archivé est en lecture seule → `TournoiArchiveNonModifiable` (409)."""
    service = ServiceTournois(FauxTournoiRepository())
    tid = _id_cree(service)
    _amener(service, tid, StatutTournoi.ARCHIVE)
    with pytest.raises(TournoiArchiveNonModifiable):
        service.supprimer(tid)
    assert service.consulter(tid).statut is StatutTournoi.ARCHIVE


def test_supprimer_leve_si_introuvable() -> None:
    """`supprimer` lève `TournoiIntrouvable` pour un identifiant inconnu."""
    service = ServiceTournois(FauxTournoiRepository())
    with pytest.raises(TournoiIntrouvable):
        service.supprimer(404)
