"""Tests du service applicatif Departs (E02US004, ADR-0017) — repositories factices.

Le service est testé **en isolation** : de faux repositories en mémoire (conformes aux ports)
suffisent. On y vérifie ce qui est propre au service — l'**attribution du numéro** (max + 1, jamais
réutilisé après suppression), la vérification d'**existence** du tournoi et du départ dans ce
tournoi — le reste (bornes du tarif, normalisation de l'horaire) étant couvert par le domaine.
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.departs import ServiceDeparts
from application.erreurs import DepartIntrouvable, TournoiIntrouvable
from domain.depart import Depart, DepartId
from domain.erreurs import TarifDepartInvalide
from domain.tournoi import Tournoi, TournoiId

_DATE = datetime.date(2026, 3, 14)


class FauxTournoiRepository:
    """Repository de tournois en mémoire conforme au port `TournoiRepository`."""

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


class FauxDepartRepository:
    """Repository de départs en mémoire conforme au port `DepartRepository`."""

    def __init__(self) -> None:
        self._departs: dict[int, Depart] = {}
        self._sequence = 0

    def ajouter(self, depart: Depart) -> Depart:
        self._sequence += 1
        persiste = dataclasses.replace(depart, id=self._sequence)
        self._departs[self._sequence] = persiste
        return persiste

    def par_id(self, depart_id: DepartId) -> Depart | None:
        return self._departs.get(depart_id)

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Depart]:
        departs = [d for d in self._departs.values() if d.tournoi_id == tournoi_id]
        return sorted(departs, key=lambda d: d.numero)

    def enregistrer(self, depart: Depart) -> Depart:
        assert depart.id in self._departs, "Départ à mettre à jour absent."
        self._departs[depart.id] = depart
        return depart

    def supprimer(self, depart_id: DepartId) -> None:
        del self._departs[depart_id]


def _service_avec_tournoi() -> tuple[ServiceDeparts, TournoiId]:
    """Fabrique un service câblé sur des repos factices et un tournoi déjà créé."""
    tournois = FauxTournoiRepository()
    departs = FauxDepartRepository()
    tournoi = tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
    assert tournoi.id is not None
    return ServiceDeparts(departs, tournois), tournoi.id


def test_creer_attribue_les_numeros_dans_l_ordre() -> None:
    """Le premier créneau porte le n° 1, le suivant le n° 2, etc. — attribués par le service."""
    service, tournoi_id = _service_avec_tournoi()
    assert service.creer(tournoi_id, 810).numero == 1
    assert service.creer(tournoi_id, 810).numero == 2
    assert service.creer(tournoi_id, 1000).numero == 3


def test_creer_persiste_tarif_et_horaire() -> None:
    """Le tarif et l'horaire fournis sont conservés."""
    service, tournoi_id = _service_avec_tournoi()
    depart = service.creer(tournoi_id, 810, "9h00")
    assert (depart.tarif_centimes, depart.horaire, depart.tournoi_id) == (810, "9h00", tournoi_id)


def test_creer_leve_si_tournoi_introuvable() -> None:
    """Créer un départ sur un tournoi inexistant lève `TournoiIntrouvable` (→ 404)."""
    service, _ = _service_avec_tournoi()
    with pytest.raises(TournoiIntrouvable):
        service.creer(999, 810)


def test_creer_propage_l_erreur_de_tarif() -> None:
    """Un tarif hors plage fait remonter l'erreur du domaine (rien n'est persisté)."""
    service, tournoi_id = _service_avec_tournoi()
    with pytest.raises(TarifDepartInvalide):
        service.creer(tournoi_id, -1)
    assert service.lister(tournoi_id) == []


def test_le_numero_n_est_pas_reutilise_apres_suppression() -> None:
    """Supprimer un créneau laisse un trou : le suivant prend max + 1, jamais le numéro libéré.

    Un numéro est un repère stable (il pourra servir au placement, EPIC-03), pas un rang recalculé.
    """
    service, tournoi_id = _service_avec_tournoi()
    service.creer(tournoi_id, 810)  # n° 1
    deuxieme = service.creer(tournoi_id, 810)  # n° 2
    service.creer(tournoi_id, 810)  # n° 3
    assert deuxieme.id is not None
    service.supprimer(tournoi_id, deuxieme.id)

    assert service.creer(tournoi_id, 810).numero == 4
    assert [d.numero for d in service.lister(tournoi_id)] == [1, 3, 4]


def test_lister_trie_par_numero_et_isole_le_tournoi() -> None:
    """`lister` renvoie les départs du tournoi, triés par numéro — pas ceux d'un autre tournoi."""
    tournois = FauxTournoiRepository()
    departs = FauxDepartRepository()
    a = tournois.ajouter(Tournoi.creer("A", _DATE))
    b = tournois.ajouter(Tournoi.creer("B", _DATE))
    assert a.id is not None and b.id is not None
    service = ServiceDeparts(departs, tournois)
    service.creer(a.id, 810)
    service.creer(a.id, 810)
    service.creer(b.id, 810)

    assert [d.numero for d in service.lister(a.id)] == [1, 2]
    assert [d.numero for d in service.lister(b.id)] == [1]


def test_lister_leve_si_tournoi_introuvable() -> None:
    service, _ = _service_avec_tournoi()
    with pytest.raises(TournoiIntrouvable):
        service.lister(999)


def test_modifier_change_tarif_et_horaire_garde_le_numero() -> None:
    """`modifier` édite tarif et horaire ; le numéro et le rattachement ne bougent pas."""
    service, tournoi_id = _service_avec_tournoi()
    depart = service.creer(tournoi_id, 810, "9h00")
    assert depart.id is not None

    modifie = service.modifier(tournoi_id, depart.id, 1250, "14h00")
    assert (modifie.numero, modifie.tarif_centimes, modifie.horaire) == (1, 1250, "14h00")


def test_modifier_leve_si_depart_d_un_autre_tournoi() -> None:
    """Éditer un départ via le mauvais tournoi → `DepartIntrouvable` (on ne fuite pas le voisin)."""
    tournois = FauxTournoiRepository()
    departs = FauxDepartRepository()
    a = tournois.ajouter(Tournoi.creer("A", _DATE))
    b = tournois.ajouter(Tournoi.creer("B", _DATE))
    assert a.id is not None and b.id is not None
    service = ServiceDeparts(departs, tournois)
    depart = service.creer(a.id, 810)
    assert depart.id is not None

    with pytest.raises(DepartIntrouvable):
        service.modifier(b.id, depart.id, 900)


def test_modifier_leve_si_introuvable() -> None:
    service, tournoi_id = _service_avec_tournoi()
    with pytest.raises(DepartIntrouvable):
        service.modifier(tournoi_id, 999, 900)


def test_supprimer_retire_le_depart() -> None:
    service, tournoi_id = _service_avec_tournoi()
    depart = service.creer(tournoi_id, 810)
    assert depart.id is not None
    service.supprimer(tournoi_id, depart.id)
    assert service.lister(tournoi_id) == []


def test_supprimer_leve_si_depart_d_un_autre_tournoi() -> None:
    tournois = FauxTournoiRepository()
    departs = FauxDepartRepository()
    a = tournois.ajouter(Tournoi.creer("A", _DATE))
    b = tournois.ajouter(Tournoi.creer("B", _DATE))
    assert a.id is not None and b.id is not None
    service = ServiceDeparts(departs, tournois)
    depart = service.creer(a.id, 810)
    assert depart.id is not None

    with pytest.raises(DepartIntrouvable):
        service.supprimer(b.id, depart.id)


def test_supprimer_leve_si_introuvable() -> None:
    service, tournoi_id = _service_avec_tournoi()
    with pytest.raises(DepartIntrouvable):
        service.supprimer(tournoi_id, 999)
