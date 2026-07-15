"""Tests du service applicatif Catégories (E01US003) — repositories factices.

Le service est testé **en isolation** : de faux repositories en mémoire (conformes aux ports
`TournoiRepository` / `CategorieRepository`) suffisent — ni base ni serveur.
`FauxCategorieRepository` vient de `conftest` : il est partagé avec `test_service_blasons` et,
depuis E02US002, `test_service_archers` — un faux partagé se déclare une fois.
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.categories import ServiceCategories
from application.erreurs import BlasonHorsTournoi, CategorieIntrouvable, TournoiIntrouvable
from domain.blason import Blason, BlasonId
from domain.categorie import SexeCategorie
from domain.erreurs import LibelleCategorieInvalide
from domain.tournoi import Tournoi, TournoiId
from tests.conftest import FauxCategorieRepository

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
    """Repository de blasons minimal (seul `par_id` est exercé par ce service)."""

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


def _service_avec_tournoi() -> tuple[ServiceCategories, int, FauxBlasonRepository]:
    """Prépare un service avec un tournoi persisté ; renvoie (service, tournoi_id, blasons)."""
    tournois = FauxTournoiRepository()
    tournoi = tournois.ajouter(Tournoi.creer("Trophée", _DATE))
    assert tournoi.id is not None
    blasons = FauxBlasonRepository()
    return ServiceCategories(tournois, FauxCategorieRepository(), blasons), tournoi.id, blasons


def test_creer_persiste_et_rattache_au_tournoi() -> None:
    """`creer` attribue un id et rattache la catégorie au tournoi."""
    service, tournoi_id, _ = _service_avec_tournoi()
    categorie = service.creer(
        tournoi_id, "Senior H Classique", "classique", "senior", SexeCategorie.HOMME
    )
    assert categorie.id == 1
    assert categorie.tournoi_id == tournoi_id
    assert categorie.libelle == "Senior H Classique"
    assert categorie.sexe is SexeCategorie.HOMME


def test_creer_leve_si_tournoi_introuvable() -> None:
    """Créer dans un tournoi inconnu lève `TournoiIntrouvable`."""
    service = ServiceCategories(
        FauxTournoiRepository(), FauxCategorieRepository(), FauxBlasonRepository()
    )
    with pytest.raises(TournoiIntrouvable):
        service.creer(404, "Libre")


def test_creer_propage_l_erreur_de_domaine() -> None:
    """Un libellé vide fait remonter l'erreur du domaine (non persisté)."""
    service, tournoi_id, _ = _service_avec_tournoi()
    with pytest.raises(LibelleCategorieInvalide):
        service.creer(tournoi_id, "   ")


def test_lister_ne_renvoie_que_les_categories_du_tournoi() -> None:
    """`lister` renvoie les catégories du tournoi demandé (et lève si tournoi inconnu)."""
    service, tournoi_id, _ = _service_avec_tournoi()
    assert service.lister(tournoi_id) == []
    service.creer(tournoi_id, "A")
    service.creer(tournoi_id, "B")
    assert [c.libelle for c in service.lister(tournoi_id)] == ["A", "B"]
    with pytest.raises(TournoiIntrouvable):
        service.lister(404)


def test_precharger_ffta_cree_le_jeu_officiel() -> None:
    """`precharger_ffta` crée les 32 catégories FFTA, rattachées au tournoi."""
    service, tournoi_id, _ = _service_avec_tournoi()
    creees = service.precharger_ffta(tournoi_id)
    assert len(creees) == 32
    assert all(c.id is not None and c.tournoi_id == tournoi_id for c in creees)
    assert [c.libelle for c in service.lister(tournoi_id)] == [c.libelle for c in creees]


def test_precharger_ffta_ignore_les_doublons() -> None:
    """Rejouable : un second pré-chargement ne recrée rien ; un libellé déjà présent est ignoré."""
    service, tournoi_id, _ = _service_avec_tournoi()
    service.creer(tournoi_id, "Arc Classique U11 Homme")  # collision de libellé (casse identique)
    premier = service.precharger_ffta(tournoi_id)
    assert len(premier) == 31  # la catégorie déjà saisie est ignorée
    assert service.precharger_ffta(tournoi_id) == []  # tout est déjà présent
    assert len(service.lister(tournoi_id)) == 32


def test_precharger_ffta_leve_si_tournoi_introuvable() -> None:
    """Pré-charger dans un tournoi inconnu lève `TournoiIntrouvable` (rien créé)."""
    service = ServiceCategories(
        FauxTournoiRepository(), FauxCategorieRepository(), FauxBlasonRepository()
    )
    with pytest.raises(TournoiIntrouvable):
        service.precharger_ffta(404)


def test_precharger_ffta_categories_modifiables_et_supprimables() -> None:
    """CA : une catégorie pré-chargée reste éditable et supprimable comme les autres."""
    service, tournoi_id, _ = _service_avec_tournoi()
    creees = service.precharger_ffta(tournoi_id)
    premiere, deuxieme = creees[0], creees[1]
    assert premiere.id is not None and deuxieme.id is not None
    modifiee = service.modifier(premiere.id, "Libellé personnalisé")
    assert modifiee.libelle == "Libellé personnalisé"
    service.supprimer(deuxieme.id)
    assert len(service.lister(tournoi_id)) == 31


def test_creer_avec_blason_du_tournoi() -> None:
    """E01US006 : on peut rattacher un blason du même tournoi comme blason par défaut."""
    service, tournoi_id, blasons = _service_avec_tournoi()
    blason = blasons.ajouter(Blason.creer(tournoi_id, "Trispot 40", 0.5, 3))
    categorie = service.creer(tournoi_id, "Senior H", blason_id=blason.id)
    assert categorie.blason_id == blason.id


def test_creer_avec_blason_d_un_autre_tournoi_leve() -> None:
    """E01US006 : un blason d'un autre tournoi est refusé (`BlasonHorsTournoi`, rien créé)."""
    service, tournoi_id, blasons = _service_avec_tournoi()
    blason_autre = blasons.ajouter(Blason.creer(tournoi_id + 999, "Ailleurs", 1.0, 1))
    with pytest.raises(BlasonHorsTournoi):
        service.creer(tournoi_id, "Senior H", blason_id=blason_autre.id)
    assert service.lister(tournoi_id) == []


def test_creer_avec_blason_inexistant_leve() -> None:
    """E01US006 : un blason par défaut inexistant est refusé (`BlasonHorsTournoi`)."""
    service, tournoi_id, _ = _service_avec_tournoi()
    with pytest.raises(BlasonHorsTournoi):
        service.creer(tournoi_id, "Senior H", blason_id=404)


def test_modifier_attache_puis_detache_le_blason() -> None:
    """E01US006 : `modifier` pose un blason par défaut valide, puis le retire (`None`)."""
    service, tournoi_id, blasons = _service_avec_tournoi()
    blason = blasons.ajouter(Blason.creer(tournoi_id, "Monospot", 1.0, 1))
    cree = service.creer(tournoi_id, "Libre")
    assert cree.id is not None
    attachee = service.modifier(cree.id, "Libre", blason_id=blason.id)
    assert attachee.blason_id == blason.id
    detachee = service.modifier(cree.id, "Libre", blason_id=None)
    assert detachee.blason_id is None


def test_modifier_avec_blason_d_un_autre_tournoi_leve() -> None:
    """E01US006 : `modifier` refuse un blason d'un autre tournoi (`BlasonHorsTournoi`)."""
    service, tournoi_id, blasons = _service_avec_tournoi()
    blason_autre = blasons.ajouter(Blason.creer(tournoi_id + 999, "Ailleurs", 1.0, 1))
    cree = service.creer(tournoi_id, "Libre")
    assert cree.id is not None
    with pytest.raises(BlasonHorsTournoi):
        service.modifier(cree.id, "Libre", blason_id=blason_autre.id)


def test_modifier_persiste_les_attributs() -> None:
    """`modifier` met à jour la catégorie et conserve son identifiant."""
    service, tournoi_id, _ = _service_avec_tournoi()
    cree = service.creer(tournoi_id, "Ancien")
    assert cree.id is not None
    modifiee = service.modifier(cree.id, "Nouveau", "poulie", "vétéran", SexeCategorie.FEMME)
    assert modifiee.id == cree.id
    assert modifiee.libelle == "Nouveau"
    assert modifiee.arme == "poulie"
    assert modifiee.sexe is SexeCategorie.FEMME


def test_modifier_leve_si_introuvable() -> None:
    """`modifier` lève `CategorieIntrouvable` pour un identifiant inconnu."""
    service, _, _ = _service_avec_tournoi()
    with pytest.raises(CategorieIntrouvable):
        service.modifier(404, "X")


def test_supprimer_retire_la_categorie() -> None:
    """`supprimer` retire la catégorie ; elle n'apparaît plus dans la liste."""
    service, tournoi_id, _ = _service_avec_tournoi()
    cree = service.creer(tournoi_id, "Libre")
    assert cree.id is not None
    service.supprimer(cree.id)
    assert service.lister(tournoi_id) == []


def test_supprimer_leve_si_introuvable() -> None:
    """`supprimer` lève `CategorieIntrouvable` pour un identifiant inconnu."""
    service, _, _ = _service_avec_tournoi()
    with pytest.raises(CategorieIntrouvable):
        service.supprimer(404)
