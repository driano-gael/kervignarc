"""Tests du service applicatif Departs (E02US004, ADR-0017) — repositories factices.

Le service est testé **en isolation** : de faux repositories en mémoire (conformes aux ports)
suffisent. On y vérifie ce qui est propre au service — l'**attribution du numéro** (max + 1, jamais
réutilisé après suppression), la vérification d'**existence** du tournoi et du départ dans ce
tournoi — le reste (bornes du tarif, normalisation de l'horaire) étant couvert par le domaine.
"""

from __future__ import annotations

import dataclasses
import datetime
from typing import NamedTuple

import pytest

from application.departs import ServiceDeparts
from application.erreurs import (
    DepartAvecInscriptions,
    DepartIntrouvable,
    TournoiIntrouvable,
)
from domain.erreurs import TarifDepartInvalide
from domain.inscription import Inscription
from domain.tournoi import Tournoi, TournoiId
from tests.conftest import FauxDepartRepository, FauxInscriptionRepository

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


class Montage(NamedTuple):
    """Attelage d'un test de départs : le service et les repos qu'on doit garnir à la main.

    Le garde-fou « départ avec inscriptions » (E02US009) suppose de poser des inscriptions dans le
    repo avant de supprimer — d'où l'exposition des repos, invisible dans le n-uplet initial
    `(service, tournoi_id)`.
    """

    service: ServiceDeparts
    departs: FauxDepartRepository
    inscriptions: FauxInscriptionRepository
    tournoi_id: TournoiId


def _monter() -> Montage:
    """Fabrique un service câblé sur des repos factices et un tournoi déjà créé."""
    tournois = FauxTournoiRepository()
    departs = FauxDepartRepository()
    inscriptions = FauxInscriptionRepository()
    tournoi = tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
    assert tournoi.id is not None
    return Montage(
        ServiceDeparts(departs, tournois, inscriptions), departs, inscriptions, tournoi.id
    )


def _service_avec_tournoi() -> tuple[ServiceDeparts, TournoiId]:
    """Raccourci `(service, tournoi_id)` pour les tests qui ignorent les repos."""
    montage = _monter()
    return montage.service, montage.tournoi_id


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


def test_supprimer_un_creneau_intermediaire_laisse_un_trou_definitif() -> None:
    """Supprimer un créneau **du milieu** laisse un trou : le suivant prend max + 1, pas le trou.

    Le numéro est toujours max + 1 (pas un rang recalculé) : le n° 2 supprimé n'est pas réattribué,
    le suivant prend 4.
    """
    service, tournoi_id = _service_avec_tournoi()
    service.creer(tournoi_id, 810)  # n° 1
    deuxieme = service.creer(tournoi_id, 810)  # n° 2
    service.creer(tournoi_id, 810)  # n° 3
    assert deuxieme.id is not None
    service.supprimer(tournoi_id, deuxieme.id)

    assert service.creer(tournoi_id, 810).numero == 4
    assert [d.numero for d in service.lister(tournoi_id)] == [1, 3, 4]


def test_supprimer_le_dernier_creneau_libere_son_numero() -> None:
    """Supprimer **le dernier** créneau (plus grand n°) libère son numéro : max + 1 le reprend.

    Conséquence assumée de « toujours max + 1 » (pas un rang recalculé). Sans effet : inscriptions
    et placement référencent l'`id` technique, pas le `numero`.
    """
    service, tournoi_id = _service_avec_tournoi()
    service.creer(tournoi_id, 810)  # n° 1
    dernier = service.creer(tournoi_id, 810)  # n° 2
    assert dernier.id is not None
    service.supprimer(tournoi_id, dernier.id)

    assert service.creer(tournoi_id, 810).numero == 2
    assert [d.numero for d in service.lister(tournoi_id)] == [1, 2]


def test_lister_trie_par_numero_et_isole_le_tournoi() -> None:
    """`lister` renvoie les départs du tournoi, triés par numéro — pas ceux d'un autre tournoi."""
    tournois = FauxTournoiRepository()
    departs = FauxDepartRepository()
    a = tournois.ajouter(Tournoi.creer("A", _DATE))
    b = tournois.ajouter(Tournoi.creer("B", _DATE))
    assert a.id is not None and b.id is not None
    service = ServiceDeparts(departs, tournois, FauxInscriptionRepository())
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
    service = ServiceDeparts(departs, tournois, FauxInscriptionRepository())
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
    service = ServiceDeparts(departs, tournois, FauxInscriptionRepository())
    depart = service.creer(a.id, 810)
    assert depart.id is not None

    with pytest.raises(DepartIntrouvable):
        service.supprimer(b.id, depart.id)


def test_supprimer_leve_si_introuvable() -> None:
    service, tournoi_id = _service_avec_tournoi()
    with pytest.raises(DepartIntrouvable):
        service.supprimer(tournoi_id, 999)


def test_supprimer_depart_avec_inscriptions_signale() -> None:
    """Un créneau qui porte des inscriptions ne se supprime pas d'un clic (CA E02US009, ADR-0018).

    Un **signalement** (`DepartAvecInscriptions`), pas un refus : l'admin peut confirmer. Tant qu'il
    ne l'a pas fait, rien n'est détruit — le départ survit.
    """
    m = _monter()
    depart = m.service.creer(m.tournoi_id, 810)
    assert depart.id is not None
    m.inscriptions.ajouter(Inscription.creer(archer_id=1, depart_id=depart.id))

    with pytest.raises(DepartAvecInscriptions):
        m.service.supprimer(m.tournoi_id, depart.id)
    assert [d.id for d in m.service.lister(m.tournoi_id)] == [depart.id]


def test_signalement_depart_decompte_les_inscriptions_dont_payees() -> None:
    """Le message énumère le nombre d'inscriptions **et** de payées (CA E02US009, ADR-0018).

    Les payées sont une somme encaissée qui deviendra un remboursement (E08US005) : l'admin doit la
    voir avant de trancher. Un message vague ferait disparaître l'argent en silence.
    """
    m = _monter()
    depart = m.service.creer(m.tournoi_id, 810)
    assert depart.id is not None
    m.inscriptions.ajouter(Inscription.creer(1, depart.id))
    m.inscriptions.ajouter(Inscription.creer(2, depart.id).marquer_paye(True))

    with pytest.raises(DepartAvecInscriptions) as leve:
        m.service.supprimer(m.tournoi_id, depart.id)
    assert "2 inscriptions" in leve.value.message
    assert "1 déjà payée" in leve.value.message


def test_signalement_depart_accorde_au_singulier() -> None:
    """Une seule inscription, aucune payée : « 1 inscription », sans mention de payée.

    Non-régression de lisibilité (patron du message d'`ArcherEngage`) : un message lu au moment de
    détruire des données se lit, il ne se décode pas.
    """
    m = _monter()
    depart = m.service.creer(m.tournoi_id, 810)
    assert depart.id is not None
    m.inscriptions.ajouter(Inscription.creer(1, depart.id))

    with pytest.raises(DepartAvecInscriptions) as leve:
        m.service.supprimer(m.tournoi_id, depart.id)
    assert "1 inscription" in leve.value.message
    # Le décompte n'ajoute pas de « dont N déjà payée » — aucune n'est payée. (La phrase fixe
    # « sommes déjà payées seront à rembourser » contient « payées » : d'où la cible sur « dont ».)
    assert "dont" not in leve.value.message


def test_supprimer_depart_avec_inscriptions_confirme_efface() -> None:
    """`autoriser_suppression_inscrits=True` : l'admin confirme, le créneau part (CA E02US009)."""
    m = _monter()
    depart = m.service.creer(m.tournoi_id, 810)
    assert depart.id is not None
    m.inscriptions.ajouter(Inscription.creer(1, depart.id))

    m.service.supprimer(m.tournoi_id, depart.id, autoriser_suppression_inscrits=True)
    assert m.service.lister(m.tournoi_id) == []
