"""Tests du service applicatif Tournois (E00US009, E01US001, E01US002) — repository factice.

Le service est testé **en isolation** du domaine d'infrastructure : un faux repository
en mémoire (conforme au port `TournoiRepository`) suffit — ni base ni serveur.
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.erreurs import (
    TournoiEnCoursNonSupprimable,
    TournoiIntrouvable,
    TransitionStatutInvalide,
)
from application.tournois import ServiceTournois
from domain.erreurs import NomTournoiInvalide, TarifDepartInvalide
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


# --- Tarif d'un départ (E01US010) ---


def test_creer_persiste_le_tarif() -> None:
    """`creer` transmet le tarif (en centimes) au domaine puis au repository."""
    service = ServiceTournois(FauxTournoiRepository())

    tournoi = service.creer("Salle 18m", _DATE, tarif_depart_centimes=810)

    assert tournoi.tarif_depart_centimes == 810
    assert tournoi.id is not None
    assert service.consulter(tournoi.id).tarif_depart_centimes == 810


def test_creer_sans_tarif_laisse_non_defini() -> None:
    """Omettre le tarif ne le met pas à zéro : il reste **non défini**."""
    service = ServiceTournois(FauxTournoiRepository())

    assert service.creer("Salle 18m", _DATE).tarif_depart_centimes is None


def test_creer_propage_l_erreur_de_tarif() -> None:
    """Un tarif négatif fait remonter l'erreur du domaine (non persisté)."""
    service = ServiceTournois(FauxTournoiRepository())

    with pytest.raises(TarifDepartInvalide):
        service.creer("Salle 18m", _DATE, tarif_depart_centimes=-1)
    assert service.lister() == []


def test_modifier_persiste_le_tarif() -> None:
    service = ServiceTournois(FauxTournoiRepository())
    cree = service.creer("Salle 18m", _DATE, tarif_depart_centimes=810)
    assert cree.id is not None

    modifie = service.modifier(cree.id, "Salle 18m", _DATE, tarif_depart_centimes=1250)

    assert modifie.tarif_depart_centimes == 1250
    assert service.consulter(cree.id).tarif_depart_centimes == 1250


def test_modifier_propage_l_erreur_de_domaine() -> None:
    """Un nom vide fait remonter l'erreur du domaine (non persisté)."""
    service = ServiceTournois(FauxTournoiRepository())
    cree = service.creer("Trophée", _DATE)
    assert cree.id is not None
    with pytest.raises(NomTournoiInvalide):
        service.modifier(cree.id, "   ", _DATE)


# --- Cycle de vie : démarrer / terminer (E01US002) ---


def test_demarrer_puis_terminer() -> None:
    """`demarrer` fait passer en cours ; `terminer` fait passer à terminé."""
    service = ServiceTournois(FauxTournoiRepository())
    cree = service.creer("Trophée", _DATE)
    assert cree.id is not None
    assert cree.statut is StatutTournoi.BROUILLON
    assert service.demarrer(cree.id).statut is StatutTournoi.EN_COURS
    assert service.terminer(cree.id).statut is StatutTournoi.TERMINE


def test_demarrer_refuse_si_deja_demarre() -> None:
    """Démarrer un tournoi non brouillon lève `TransitionStatutInvalide` (→ 409)."""
    service = ServiceTournois(FauxTournoiRepository())
    cree = service.creer("Trophée", _DATE)
    assert cree.id is not None
    service.demarrer(cree.id)
    with pytest.raises(TransitionStatutInvalide):
        service.demarrer(cree.id)


def test_terminer_refuse_si_pas_en_cours() -> None:
    """Terminer un tournoi non démarré lève `TransitionStatutInvalide` (→ 409)."""
    service = ServiceTournois(FauxTournoiRepository())
    cree = service.creer("Trophée", _DATE)
    assert cree.id is not None
    with pytest.raises(TransitionStatutInvalide):
        service.terminer(cree.id)


# --- Suppression (E01US002) ---


def test_supprimer_un_brouillon() -> None:
    """Un tournoi brouillon est supprimable."""
    service = ServiceTournois(FauxTournoiRepository())
    cree = service.creer("Trophée", _DATE)
    assert cree.id is not None
    service.supprimer(cree.id)
    assert service.lister() == []


def test_supprimer_un_termine() -> None:
    """Un tournoi terminé est supprimable."""
    service = ServiceTournois(FauxTournoiRepository())
    cree = service.creer("Trophée", _DATE)
    assert cree.id is not None
    service.demarrer(cree.id)
    service.terminer(cree.id)
    service.supprimer(cree.id)
    assert service.lister() == []


def test_supprimer_refuse_si_en_cours() -> None:
    """Un tournoi en cours n'est pas supprimable → `TournoiEnCoursNonSupprimable` (409)."""
    service = ServiceTournois(FauxTournoiRepository())
    cree = service.creer("Trophée", _DATE)
    assert cree.id is not None
    service.demarrer(cree.id)
    with pytest.raises(TournoiEnCoursNonSupprimable):
        service.supprimer(cree.id)
    assert service.consulter(cree.id).statut is StatutTournoi.EN_COURS


def test_supprimer_leve_si_introuvable() -> None:
    """`supprimer` lève `TournoiIntrouvable` pour un identifiant inconnu."""
    service = ServiceTournois(FauxTournoiRepository())
    with pytest.raises(TournoiIntrouvable):
        service.supprimer(404)
