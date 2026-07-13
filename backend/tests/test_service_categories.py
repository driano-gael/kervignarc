"""Tests du service applicatif Catégories (E01US003) — repositories factices.

Le service est testé **en isolation** : de faux repositories en mémoire (conformes aux ports
`TournoiRepository` / `CategorieRepository`) suffisent — ni base ni serveur.
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.categories import ServiceCategories
from application.erreurs import CategorieIntrouvable, TournoiIntrouvable
from domain.categorie import Categorie, CategorieId, SexeCategorie
from domain.erreurs import LibelleCategorieInvalide
from domain.tournoi import Tournoi, TournoiId

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


class FauxCategorieRepository:
    """Repository en mémoire conforme au port `CategorieRepository`."""

    def __init__(self) -> None:
        self._categories: dict[int, Categorie] = {}
        self._sequence = 0

    def ajouter(self, categorie: Categorie) -> Categorie:
        self._sequence += 1
        persiste = dataclasses.replace(categorie, id=self._sequence)
        self._categories[self._sequence] = persiste
        return persiste

    def par_id(self, categorie_id: CategorieId) -> Categorie | None:
        return self._categories.get(categorie_id)

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Categorie]:
        return [c for c in self._categories.values() if c.tournoi_id == tournoi_id]

    def enregistrer(self, categorie: Categorie) -> Categorie:
        assert categorie.id in self._categories
        self._categories[categorie.id] = categorie
        return categorie

    def supprimer(self, categorie_id: CategorieId) -> None:
        del self._categories[categorie_id]


def _service_avec_tournoi() -> tuple[ServiceCategories, int]:
    """Prépare un service avec un tournoi persisté ; renvoie (service, tournoi_id)."""
    tournois = FauxTournoiRepository()
    tournoi = tournois.ajouter(Tournoi.creer("Trophée", _DATE))
    assert tournoi.id is not None
    return ServiceCategories(tournois, FauxCategorieRepository()), tournoi.id


def test_creer_persiste_et_rattache_au_tournoi() -> None:
    """`creer` attribue un id et rattache la catégorie au tournoi."""
    service, tournoi_id = _service_avec_tournoi()
    categorie = service.creer(
        tournoi_id, "Senior H Classique", "classique", "senior", SexeCategorie.HOMME
    )
    assert categorie.id == 1
    assert categorie.tournoi_id == tournoi_id
    assert categorie.libelle == "Senior H Classique"
    assert categorie.sexe is SexeCategorie.HOMME


def test_creer_leve_si_tournoi_introuvable() -> None:
    """Créer dans un tournoi inconnu lève `TournoiIntrouvable`."""
    service = ServiceCategories(FauxTournoiRepository(), FauxCategorieRepository())
    with pytest.raises(TournoiIntrouvable):
        service.creer(404, "Libre")


def test_creer_propage_l_erreur_de_domaine() -> None:
    """Un libellé vide fait remonter l'erreur du domaine (non persisté)."""
    service, tournoi_id = _service_avec_tournoi()
    with pytest.raises(LibelleCategorieInvalide):
        service.creer(tournoi_id, "   ")


def test_lister_ne_renvoie_que_les_categories_du_tournoi() -> None:
    """`lister` renvoie les catégories du tournoi demandé (et lève si tournoi inconnu)."""
    service, tournoi_id = _service_avec_tournoi()
    assert service.lister(tournoi_id) == []
    service.creer(tournoi_id, "A")
    service.creer(tournoi_id, "B")
    assert [c.libelle for c in service.lister(tournoi_id)] == ["A", "B"]
    with pytest.raises(TournoiIntrouvable):
        service.lister(404)


def test_modifier_persiste_les_attributs() -> None:
    """`modifier` met à jour la catégorie et conserve son identifiant."""
    service, tournoi_id = _service_avec_tournoi()
    cree = service.creer(tournoi_id, "Ancien")
    assert cree.id is not None
    modifiee = service.modifier(cree.id, "Nouveau", "poulie", "vétéran", SexeCategorie.FEMME)
    assert modifiee.id == cree.id
    assert modifiee.libelle == "Nouveau"
    assert modifiee.arme == "poulie"
    assert modifiee.sexe is SexeCategorie.FEMME


def test_modifier_leve_si_introuvable() -> None:
    """`modifier` lève `CategorieIntrouvable` pour un identifiant inconnu."""
    service, _ = _service_avec_tournoi()
    with pytest.raises(CategorieIntrouvable):
        service.modifier(404, "X")


def test_supprimer_retire_la_categorie() -> None:
    """`supprimer` retire la catégorie ; elle n'apparaît plus dans la liste."""
    service, tournoi_id = _service_avec_tournoi()
    cree = service.creer(tournoi_id, "Libre")
    assert cree.id is not None
    service.supprimer(cree.id)
    assert service.lister(tournoi_id) == []


def test_supprimer_leve_si_introuvable() -> None:
    """`supprimer` lève `CategorieIntrouvable` pour un identifiant inconnu."""
    service, _ = _service_avec_tournoi()
    with pytest.raises(CategorieIntrouvable):
        service.supprimer(404)
