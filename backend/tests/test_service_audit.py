"""Tests du service applicatif Audit (E10US005, socle) — repositories & horloge factices.

Écrits **depuis le CA** (règle 9). Le service est testé **en isolation** : un faux repository en
mémoire (conforme au port `AuditRepository`), un faux tournoi et une **horloge figée** suffisent —
ni base ni serveur. On vérifie ce qui est propre au service : l'horodatage **daté par l'horloge**
(déterminisme, règle 9), la consultation restreinte au tournoi et son ordre chronologique, et le
404 sur tournoi inconnu. Les invariants de l'entrée (auteur/objet non vides) sont couverts par le
domaine (`test_domain_entree_audit`).
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.audit import ServiceAudit
from application.erreurs import TournoiIntrouvable
from domain.entree_audit import ActionAuditee, EntreeAudit
from domain.erreurs import AuteurAuditInvalide
from domain.tournoi import Tournoi, TournoiId

_DATE = datetime.date(2026, 3, 14)
_QUAND = datetime.datetime(2026, 3, 14, 10, 42, tzinfo=datetime.UTC)


class FauxAuditRepository:
    """Journal en mémoire conforme au port `AuditRepository` (ajout seul, ordre chronologique)."""

    def __init__(self) -> None:
        self._entrees: list[EntreeAudit] = []
        self._sequence = 0

    def consigner(self, entree: EntreeAudit) -> EntreeAudit:
        self._sequence += 1
        persiste = dataclasses.replace(entree, id=self._sequence)
        self._entrees.append(persiste)
        return persiste

    def par_tournoi(self, tournoi_id: TournoiId) -> list[EntreeAudit]:
        # Conservées dans l'ordre d'insertion (chronologique) : l'adapter SQL, lui, ordonne par id.
        return [e for e in self._entrees if e.tournoi_id == tournoi_id]


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


class HorlogeFigee:
    """Horloge déterministe conforme au port `Horloge` : renvoie toujours le même instant."""

    def __init__(self, instant: datetime.datetime) -> None:
        self._instant = instant

    def maintenant(self) -> datetime.datetime:
        return self._instant


class Montage:
    """Attelage d'un test : service + repos + horloge figée + `tournoi_id`."""

    def __init__(self, instant: datetime.datetime = _QUAND) -> None:
        self.audit = FauxAuditRepository()
        self.tournois = FauxTournoiRepository()
        self.horloge = HorlogeFigee(instant)
        tournoi = self.tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
        assert tournoi.id is not None
        self.tournoi_id: TournoiId = tournoi.id
        self.service = ServiceAudit(self.audit, self.tournois, self.horloge)


def test_consigner_date_l_entree_par_l_horloge() -> None:
    """CA « quand » : l'horodatage vient de l'**horloge injectée**, pas de `datetime.now`."""
    m = Montage()

    entree = m.service.consigner(
        m.tournoi_id, ActionAuditee.VALIDATION, "DURAND Jean", "Série 3 — cible 4A"
    )

    assert entree.id is not None
    assert entree.horodatage == _QUAND
    assert entree.action is ActionAuditee.VALIDATION
    assert entree.auteur == "DURAND Jean"


def test_consigner_une_correction_conserve_avant_apres() -> None:
    m = Montage()

    entree = m.service.consigner(
        m.tournoi_id,
        ActionAuditee.CORRECTION_SCORE,
        "ROUX Sophie",
        "Série 3, flèche 2",
        avant="8",
        apres="9",
    )

    assert (entree.avant, entree.apres) == ("8", "9")


def test_consigner_propage_un_auteur_vide() -> None:
    """L'invariant domaine remonte tel quel (pas de garde applicative qui l'avalerait)."""
    m = Montage()
    with pytest.raises(AuteurAuditInvalide):
        m.service.consigner(m.tournoi_id, ActionAuditee.VALIDATION, "  ", "Série 3")


def test_lister_ne_renvoie_que_les_entrees_du_tournoi() -> None:
    m = Montage()
    autre = m.tournois.ajouter(Tournoi.creer("Autre", _DATE))
    assert autre.id is not None
    du_tournoi = m.service.consigner(m.tournoi_id, ActionAuditee.VALIDATION, "DURAND", "Série 3")
    m.service.consigner(autre.id, ActionAuditee.VALIDATION, "MARTIN", "Série 1")

    assert m.service.lister(m.tournoi_id) == [du_tournoi]


def test_lister_rend_l_ordre_chronologique() -> None:
    """Un journal se lit dans le sens du temps (ordre d'insertion préservé)."""
    m = Montage()
    a = m.service.consigner(m.tournoi_id, ActionAuditee.VALIDATION, "DURAND", "Série 1")
    b = m.service.consigner(m.tournoi_id, ActionAuditee.VALIDATION, "DURAND", "Série 2")
    c = m.service.consigner(m.tournoi_id, ActionAuditee.CORRECTION_SCORE, "ROUX", "Série 1, f2")

    assert m.service.lister(m.tournoi_id) == [a, b, c]


def test_lister_vide_sans_entree() -> None:
    m = Montage()
    assert m.service.lister(m.tournoi_id) == []


def test_lister_refuse_un_tournoi_inexistant() -> None:
    m = Montage()
    with pytest.raises(TournoiIntrouvable):
        m.service.lister(404)
