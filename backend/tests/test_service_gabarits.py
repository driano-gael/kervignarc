"""Tests du service applicatif Gabarits de salle (E01US007) — repository factice.

Le service est testé **en isolation** : un faux repository en mémoire (conforme au port
`GabaritSalleRepository`) suffit — ni base ni serveur. Le gabarit est autonome (aucun tournoi).
"""

from __future__ import annotations

import dataclasses

import pytest

from application.erreurs import GabaritIntrouvable
from application.gabarits import ServiceGabarits
from domain.erreurs import CapaciteCibleInvalide, NomGabaritInvalide
from domain.gabarit_salle import GabaritSalle, GabaritSalleId


class FauxGabaritRepository:
    """Repository en mémoire conforme au port `GabaritSalleRepository`."""

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
        return list(self._gabarits.values())

    def enregistrer(self, gabarit: GabaritSalle) -> GabaritSalle:
        assert gabarit.id in self._gabarits
        self._gabarits[gabarit.id] = gabarit
        return gabarit

    def supprimer(self, gabarit_id: GabaritSalleId) -> None:
        del self._gabarits[gabarit_id]


def test_creer_persiste_et_attribue_un_id() -> None:
    """`creer` attribue un id et remplit les cibles au plafond demandé."""
    service = ServiceGabarits(FauxGabaritRepository())
    gabarit = service.creer("Salle A", 12, 4)
    assert gabarit.id == 1
    assert gabarit.nom == "Salle A"
    assert gabarit.nb_cibles == 12
    assert gabarit.capacites == (4,) * 12


def test_creer_propage_l_erreur_de_domaine() -> None:
    """Un nom vide fait remonter l'erreur du domaine (non persisté)."""
    service = ServiceGabarits(FauxGabaritRepository())
    with pytest.raises(NomGabaritInvalide):
        service.creer("   ", 4, 4)
    assert service.lister() == []


def test_lister_renvoie_les_gabarits_dans_l_ordre() -> None:
    """`lister` renvoie tous les gabarits créés."""
    service = ServiceGabarits(FauxGabaritRepository())
    assert service.lister() == []
    service.creer("A", 2, 4)
    service.creer("B", 4, 2)
    assert [g.nom for g in service.lister()] == ["A", "B"]


def test_modifier_persiste_les_attributs() -> None:
    """`modifier` met à jour le gabarit et conserve son identifiant."""
    service = ServiceGabarits(FauxGabaritRepository())
    cree = service.creer("Ancien", 4, 4)
    assert cree.id is not None
    modifie = service.modifier(cree.id, "Nouveau", 6, 2)
    assert modifie.id == cree.id
    assert modifie.nom == "Nouveau"
    assert modifie.capacites == (2,) * 6


def test_modifier_leve_si_introuvable() -> None:
    """`modifier` lève `GabaritIntrouvable` pour un identifiant inconnu."""
    service = ServiceGabarits(FauxGabaritRepository())
    with pytest.raises(GabaritIntrouvable):
        service.modifier(404, "X", 1, 1)


def test_modifier_plafond_invalide_leve_domaine() -> None:
    """Un plafond hors plage à l'édition fait remonter l'erreur du domaine."""
    service = ServiceGabarits(FauxGabaritRepository())
    cree = service.creer("Salle", 1, 4)
    assert cree.id is not None
    with pytest.raises(CapaciteCibleInvalide):
        service.modifier(cree.id, "Salle", 1, 9)


def test_supprimer_retire_le_gabarit() -> None:
    """`supprimer` retire le gabarit ; il n'apparaît plus dans la liste."""
    service = ServiceGabarits(FauxGabaritRepository())
    cree = service.creer("Salle", 1, 1)
    assert cree.id is not None
    service.supprimer(cree.id)
    assert service.lister() == []


def test_supprimer_leve_si_introuvable() -> None:
    """`supprimer` lève `GabaritIntrouvable` pour un identifiant inconnu."""
    service = ServiceGabarits(FauxGabaritRepository())
    with pytest.raises(GabaritIntrouvable):
        service.supprimer(404)
