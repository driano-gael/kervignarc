"""Tests du service applicatif Blasons (E01US005) — repositories factices.

Le service est testé **en isolation** : de faux repositories en mémoire (conformes aux ports
`TournoiRepository` / `BlasonRepository`) suffisent — ni base ni serveur.
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.blasons import ServiceBlasons
from application.erreurs import BlasonIntrouvable, TournoiIntrouvable
from domain.blason import Blason, BlasonId
from domain.erreurs import TailleBlasonInvalide
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


class FauxBlasonRepository:
    """Repository en mémoire conforme au port `BlasonRepository`."""

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


def _service_avec_tournoi() -> tuple[ServiceBlasons, int]:
    """Prépare un service avec un tournoi persisté ; renvoie (service, tournoi_id)."""
    tournois = FauxTournoiRepository()
    tournoi = tournois.ajouter(Tournoi.creer("Trophée", _DATE))
    assert tournoi.id is not None
    return ServiceBlasons(tournois, FauxBlasonRepository()), tournoi.id


def test_creer_persiste_et_rattache_au_tournoi() -> None:
    """`creer` attribue un id et rattache le blason au tournoi."""
    service, tournoi_id = _service_avec_tournoi()
    blason = service.creer(tournoi_id, "Trispot 40", 0.5, 3)
    assert blason.id == 1
    assert blason.tournoi_id == tournoi_id
    assert blason.nom == "Trispot 40"
    assert blason.taille == 0.5
    assert blason.capacite == 3


def test_creer_leve_si_tournoi_introuvable() -> None:
    """Créer dans un tournoi inconnu lève `TournoiIntrouvable`."""
    service = ServiceBlasons(FauxTournoiRepository(), FauxBlasonRepository())
    with pytest.raises(TournoiIntrouvable):
        service.creer(404, "Blason", 0.5, 1)


def test_creer_propage_l_erreur_de_domaine() -> None:
    """Une taille invalide fait remonter l'erreur du domaine (non persisté)."""
    service, tournoi_id = _service_avec_tournoi()
    with pytest.raises(TailleBlasonInvalide):
        service.creer(tournoi_id, "Blason", 0.0, 1)


def test_lister_ne_renvoie_que_les_blasons_du_tournoi() -> None:
    """`lister` renvoie les blasons du tournoi demandé (et lève si tournoi inconnu)."""
    service, tournoi_id = _service_avec_tournoi()
    assert service.lister(tournoi_id) == []
    service.creer(tournoi_id, "A", 0.5, 1)
    service.creer(tournoi_id, "B", 1.0, 2)
    assert [b.nom for b in service.lister(tournoi_id)] == ["A", "B"]
    with pytest.raises(TournoiIntrouvable):
        service.lister(404)


def test_modifier_persiste_les_attributs() -> None:
    """`modifier` met à jour le blason et conserve son identifiant."""
    service, tournoi_id = _service_avec_tournoi()
    cree = service.creer(tournoi_id, "Ancien", 0.25, 4)
    assert cree.id is not None
    modifie = service.modifier(cree.id, "Nouveau", 0.5, 2)
    assert modifie.id == cree.id
    assert modifie.nom == "Nouveau"
    assert modifie.taille == 0.5
    assert modifie.capacite == 2


def test_modifier_leve_si_introuvable() -> None:
    """`modifier` lève `BlasonIntrouvable` pour un identifiant inconnu."""
    service, _ = _service_avec_tournoi()
    with pytest.raises(BlasonIntrouvable):
        service.modifier(404, "X", 0.5, 1)


def test_supprimer_retire_le_blason() -> None:
    """`supprimer` retire le blason ; il n'apparaît plus dans la liste."""
    service, tournoi_id = _service_avec_tournoi()
    cree = service.creer(tournoi_id, "Monospot", 1.0, 1)
    assert cree.id is not None
    service.supprimer(cree.id)
    assert service.lister(tournoi_id) == []


def test_supprimer_leve_si_introuvable() -> None:
    """`supprimer` lève `BlasonIntrouvable` pour un identifiant inconnu."""
    service, _ = _service_avec_tournoi()
    with pytest.raises(BlasonIntrouvable):
        service.supprimer(404)
