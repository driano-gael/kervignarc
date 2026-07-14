"""Tests du service applicatif Gabarits de salle (E01US007, E01US008) — repositories factices.

Le service est testé **en isolation** : de faux repositories en mémoire (conformes aux ports
`TournoiRepository` / `GabaritSalleRepository`) suffisent — ni base ni serveur. Deux facettes :
la **bibliothèque** de modèles et l'**application** d'un modèle à un tournoi (copie ajustable).
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.erreurs import (
    GabaritDuTournoiAbsent,
    GabaritIntrouvable,
    TournoiIntrouvable,
)
from application.gabarits import ServiceGabarits
from domain.erreurs import CapaciteCibleInvalide, NombreCiblesInvalide, NomGabaritInvalide
from domain.gabarit_salle import GabaritSalle, GabaritSalleId
from domain.tournoi import Tournoi, TournoiId, TypeTournoi

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
    """Repository en mémoire conforme au port `GabaritSalleRepository`.

    `lister` ne renvoie que les **modèles** (`tournoi_id is None`) ; `par_tournoi` récupère
    l'instance appliquée à un tournoi — miroir fidèle de l'adapter SQL.
    """

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


def _service_avec_tournoi() -> tuple[ServiceGabarits, int]:
    """Construit le service et un tournoi persisté, renvoie le service et l'id du tournoi."""
    tournois = FauxTournoiRepository()
    tournoi = tournois.ajouter(
        Tournoi(nom="Kervignarc", date=_DATE, lieu=None, type_tournoi=TypeTournoi.NON_OFFICIEL)
    )
    assert tournoi.id is not None
    return ServiceGabarits(tournois, FauxGabaritRepository()), tournoi.id


def _service() -> ServiceGabarits:
    return ServiceGabarits(FauxTournoiRepository(), FauxGabaritRepository())


# --- Bibliothèque de modèles (E01US007) ---


def test_creer_persiste_et_attribue_un_id() -> None:
    """`creer` attribue un id, remplit les cibles au plafond demandé et reste un modèle."""
    service = _service()
    gabarit = service.creer("Salle A", 12, 4)
    assert gabarit.id == 1
    assert gabarit.nom == "Salle A"
    assert gabarit.nb_cibles == 12
    assert gabarit.capacites == (4,) * 12
    assert gabarit.tournoi_id is None


def test_creer_propage_l_erreur_de_domaine() -> None:
    """Un nom vide fait remonter l'erreur du domaine (non persisté)."""
    service = _service()
    with pytest.raises(NomGabaritInvalide):
        service.creer("   ", 4, 4)
    assert service.lister() == []


def test_lister_renvoie_les_modeles_dans_l_ordre() -> None:
    """`lister` renvoie tous les modèles créés (les instances de tournoi en sont exclues)."""
    service = _service()
    assert service.lister() == []
    service.creer("A", 2, 4)
    service.creer("B", 4, 2)
    assert [g.nom for g in service.lister()] == ["A", "B"]


def test_modifier_persiste_les_attributs() -> None:
    """`modifier` met à jour le gabarit et conserve son identifiant."""
    service = _service()
    cree = service.creer("Ancien", 4, 4)
    assert cree.id is not None
    modifie = service.modifier(cree.id, "Nouveau", 6, 2)
    assert modifie.id == cree.id
    assert modifie.nom == "Nouveau"
    assert modifie.capacites == (2,) * 6


def test_modifier_leve_si_introuvable() -> None:
    """`modifier` lève `GabaritIntrouvable` pour un identifiant inconnu."""
    service = _service()
    with pytest.raises(GabaritIntrouvable):
        service.modifier(404, "X", 1, 1)


def test_modifier_plafond_invalide_leve_domaine() -> None:
    """Un plafond hors plage à l'édition fait remonter l'erreur du domaine."""
    service = _service()
    cree = service.creer("Salle", 1, 4)
    assert cree.id is not None
    with pytest.raises(CapaciteCibleInvalide):
        service.modifier(cree.id, "Salle", 1, 9)


def test_supprimer_retire_le_gabarit() -> None:
    """`supprimer` retire le gabarit ; il n'apparaît plus dans la liste."""
    service = _service()
    cree = service.creer("Salle", 1, 1)
    assert cree.id is not None
    service.supprimer(cree.id)
    assert service.lister() == []


def test_supprimer_leve_si_introuvable() -> None:
    """`supprimer` lève `GabaritIntrouvable` pour un identifiant inconnu."""
    service = _service()
    with pytest.raises(GabaritIntrouvable):
        service.supprimer(404)


# --- Application à un tournoi (E01US008) ---


def test_gabarit_du_tournoi_absent_par_defaut() -> None:
    """Un tournoi neuf n'a aucun gabarit appliqué."""
    service, tournoi_id = _service_avec_tournoi()
    assert service.gabarit_du_tournoi(tournoi_id) is None


def test_gabarit_du_tournoi_leve_si_tournoi_inconnu() -> None:
    """Lire le gabarit d'un tournoi inexistant lève `TournoiIntrouvable`."""
    service = _service()
    with pytest.raises(TournoiIntrouvable):
        service.gabarit_du_tournoi(404)


def test_appliquer_cree_une_copie_rattachee_au_tournoi() -> None:
    """Appliquer un modèle crée une instance copiée, rattachée au tournoi, d'id distinct."""
    service, tournoi_id = _service_avec_tournoi()
    modele = service.creer("Salle municipale", 12, 4)
    assert modele.id is not None

    instance = service.appliquer(tournoi_id, modele.id)

    assert instance.id != modele.id
    assert instance.tournoi_id == tournoi_id
    assert instance.nom == "Salle municipale"
    assert instance.capacites == (4,) * 12
    assert service.gabarit_du_tournoi(tournoi_id) == instance
    # L'instance n'apparaît pas dans la bibliothèque (réservée aux modèles).
    assert [g.id for g in service.lister()] == [modele.id]


def test_ajuster_n_altere_pas_le_modele_d_origine() -> None:
    """Ajuster la copie du tournoi ne touche pas au modèle de bibliothèque."""
    service, tournoi_id = _service_avec_tournoi()
    modele = service.creer("Salle municipale", 4, 4)
    assert modele.id is not None
    service.appliquer(tournoi_id, modele.id)

    ajustee = service.ajuster(tournoi_id, "Salle municipale (adaptée)", (4, 2, 2, 1))

    assert ajustee.capacites == (4, 2, 2, 1)
    assert ajustee.nom == "Salle municipale (adaptée)"
    # Le modèle d'origine, relu depuis la bibliothèque, est intact.
    (modele_relu,) = service.lister()
    assert modele_relu.nom == "Salle municipale"
    assert modele_relu.capacites == (4,) * 4


def test_appliquer_remplace_l_instance_existante_sur_place() -> None:
    """Réappliquer (un autre) modèle remplace la copie du tournoi en conservant son identifiant."""
    service, tournoi_id = _service_avec_tournoi()
    petit = service.creer("Petite salle", 4, 2)
    grand = service.creer("Grande salle", 20, 4)
    assert petit.id is not None and grand.id is not None

    premiere = service.appliquer(tournoi_id, petit.id)
    seconde = service.appliquer(tournoi_id, grand.id)

    assert seconde.id == premiere.id  # même ligne, remplacée sur place
    assert seconde.nom == "Grande salle"
    assert seconde.nb_cibles == 20
    assert service.gabarit_du_tournoi(tournoi_id) == seconde


def test_appliquer_leve_si_tournoi_inconnu() -> None:
    """Appliquer à un tournoi inexistant lève `TournoiIntrouvable`."""
    service = _service()
    modele = service.creer("Salle", 4, 4)
    assert modele.id is not None
    with pytest.raises(TournoiIntrouvable):
        service.appliquer(404, modele.id)


def test_appliquer_leve_si_modele_inconnu() -> None:
    """Appliquer un identifiant de modèle inconnu lève `GabaritIntrouvable`."""
    service, tournoi_id = _service_avec_tournoi()
    with pytest.raises(GabaritIntrouvable):
        service.appliquer(tournoi_id, 404)


def test_appliquer_refuse_une_instance_comme_modele() -> None:
    """On ne peut appliquer qu'un **modèle** : passer une instance déjà rattachée est refusé."""
    service, tournoi_id = _service_avec_tournoi()
    modele = service.creer("Salle", 4, 4)
    assert modele.id is not None
    instance = service.appliquer(tournoi_id, modele.id)
    assert instance.id is not None
    with pytest.raises(GabaritIntrouvable):
        service.appliquer(tournoi_id, instance.id)


def test_ajuster_leve_si_aucun_gabarit_applique() -> None:
    """Ajuster sans gabarit appliqué lève `GabaritDuTournoiAbsent`."""
    service, tournoi_id = _service_avec_tournoi()
    with pytest.raises(GabaritDuTournoiAbsent):
        service.ajuster(tournoi_id, "Salle", (4, 4))


def test_ajuster_plafond_invalide_leve_domaine() -> None:
    """Un plafond hors plage à l'ajustement fait remonter l'erreur du domaine."""
    service, tournoi_id = _service_avec_tournoi()
    modele = service.creer("Salle", 2, 4)
    assert modele.id is not None
    service.appliquer(tournoi_id, modele.id)
    with pytest.raises(CapaciteCibleInvalide):
        service.ajuster(tournoi_id, "Salle", (4, 9))


def test_ajuster_sans_cible_leve_domaine() -> None:
    """Ajuster vers zéro cible fait remonter l'erreur du domaine."""
    service, tournoi_id = _service_avec_tournoi()
    modele = service.creer("Salle", 2, 4)
    assert modele.id is not None
    service.appliquer(tournoi_id, modele.id)
    with pytest.raises(NombreCiblesInvalide):
        service.ajuster(tournoi_id, "Salle", ())
