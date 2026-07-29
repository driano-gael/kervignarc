"""Tests du service applicatif Remboursements (E08US005, ADR-0057) — dérivés du **CA**.

Source : `stories/E08-paiements.md`, E08US005, puce « **CA** » (« l'admin le marque **remboursé**
(daté, tracé) ou **reporté** ») et Notes (« registre daté »). On y vérifie ce qui est propre au
service : **lister** (à traiter d'abord, puis récents), **marquer** remboursé/reporté (audité,
daté), le refus de **re-traiter** un poste terminal, et le 404 sur un id inconnu. La création d'un
poste (à la suppression d'une inscription payée) est prouvée côté `test_service_inscriptions` /
`test_service_departs`.

Repos factices en mémoire ; horloge figée pour des dates et traces reproductibles (règle 9).
"""

from __future__ import annotations

import datetime

import pytest

from application.erreurs import (
    RemboursementDejaTraite,
    RemboursementIntrouvable,
    TournoiIntrouvable,
)
from application.remboursements import ServiceRemboursements
from domain.entree_audit import ActionAuditee
from domain.remboursement import MotifRemboursement, Remboursement, StatutRemboursement
from domain.tournoi import Tournoi, TournoiId
from tests.conftest import FauxRemboursementRepository, HorlogeFigee
from tests.test_service_departs import FauxTournoiRepository

_DATE = datetime.date(2026, 3, 14)
_QUAND = datetime.datetime(2026, 7, 29, 11, 0, tzinfo=datetime.UTC)


def _monter() -> tuple[ServiceRemboursements, FauxRemboursementRepository, TournoiId]:
    tournois = FauxTournoiRepository()
    remboursements = FauxRemboursementRepository()
    tournoi = tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
    assert tournoi.id is not None
    service = ServiceRemboursements(remboursements, tournois, HorlogeFigee(_QUAND))
    return service, remboursements, tournoi.id


def _poste(
    remboursements: FauxRemboursementRepository,
    tournoi_id: TournoiId,
    *,
    montant: int = 810,
    cree_le: datetime.datetime = datetime.datetime(2026, 7, 29, 9, 0, tzinfo=datetime.UTC),
    prenom: str = "Jean",
) -> Remboursement:
    """Peuple le registre d'un poste à traiter (comme le ferait un effacement d'inscription
    payée)."""
    return remboursements.ajouter(
        Remboursement.creer(
            tournoi_id,
            archer_prenom=prenom,
            archer_nom="Robin",
            creneau="Départ n°1 — 09:00",
            montant_centimes=montant,
            motif=MotifRemboursement.DESINSCRIPTION,
            cree_le=cree_le,
        )
    )


def test_lister_tournoi_inconnu_leve() -> None:
    """Lister les remboursements d'un tournoi inexistant lève `TournoiIntrouvable` (404)."""
    service, _, _ = _monter()
    with pytest.raises(TournoiIntrouvable):
        service.lister(999)


def test_lister_met_les_a_traiter_en_premier_puis_les_plus_recents() -> None:
    """Tri d'affichage : les `à_rembourser` d'abord, puis par date de création décroissante.

    Un poste traité (remboursé) passe derrière ceux à traiter, quelle que soit sa date.
    """
    service, remboursements, tournoi_id = _monter()
    vieux = _poste(
        remboursements,
        tournoi_id,
        cree_le=datetime.datetime(2026, 7, 29, 8, 0, tzinfo=datetime.UTC),
    )
    recent = _poste(
        remboursements,
        tournoi_id,
        cree_le=datetime.datetime(2026, 7, 29, 10, 0, tzinfo=datetime.UTC),
    )
    assert vieux.id is not None and recent.id is not None
    service.marquer_rembourse(
        tournoi_id, vieux.id
    )  # le + vieux, mais **traité** → passe en dernier

    ordre = [r.id for r in service.lister(tournoi_id)]
    assert ordre == [recent.id, vieux.id]  # à traiter d'abord (recent), puis le traité (vieux)


def test_marquer_rembourse_fige_le_statut_date_et_trace() -> None:
    """« L'admin le marque **remboursé** (daté, tracé) » (CA) : statut, date, et entrée
    `REMBOURSEMENT`."""
    service, remboursements, tournoi_id = _monter()
    poste = _poste(remboursements, tournoi_id)
    assert poste.id is not None

    maj = service.marquer_rembourse(tournoi_id, poste.id)
    assert maj.statut is StatutRemboursement.REMBOURSE
    assert maj.traite_le == _QUAND
    assert len(remboursements.traces) == 1
    trace = remboursements.traces[0]
    assert trace.action is ActionAuditee.REMBOURSEMENT
    assert trace.apres == "remboursé"
    assert trace.tournoi_id == tournoi_id


def test_marquer_reporte_fige_le_statut_et_trace() -> None:
    """« ou **reporté** » (CA) : statut `reporté`, trace `REMBOURSEMENT` avec `apres = reporté`."""
    service, remboursements, tournoi_id = _monter()
    poste = _poste(remboursements, tournoi_id)
    assert poste.id is not None

    maj = service.marquer_reporte(tournoi_id, poste.id)
    assert maj.statut is StatutRemboursement.REPORTE
    assert remboursements.traces[0].apres == "reporté"


def test_marquer_un_poste_deja_traite_est_refuse() -> None:
    """Un remboursement traité est **terminal** : le re-marquer lève `RemboursementDejaTraite`
    (409).

    Conflit d'état — on ne réécrit pas la date d'un mouvement d'argent. Aucune seconde trace n'est
    écrite (le refus précède l'écriture).
    """
    service, remboursements, tournoi_id = _monter()
    poste = _poste(remboursements, tournoi_id)
    assert poste.id is not None
    service.marquer_rembourse(tournoi_id, poste.id)

    with pytest.raises(RemboursementDejaTraite):
        service.marquer_rembourse(tournoi_id, poste.id)
    with pytest.raises(RemboursementDejaTraite):
        service.marquer_reporte(tournoi_id, poste.id)
    assert len(remboursements.traces) == 1  # une seule trace, celle du premier traitement


def test_marquer_un_poste_d_un_autre_tournoi_leve() -> None:
    """Traiter un poste via le **mauvais tournoi** lève `RemboursementIntrouvable` (on ne fuite pas
    le voisin) — symétrique du 404 de `lister` sur un tournoi inconnu (revue A)."""
    service, remboursements, tournoi_id = _monter()
    poste = _poste(remboursements, tournoi_id)
    assert poste.id is not None

    with pytest.raises(RemboursementIntrouvable):
        service.marquer_rembourse(tournoi_id + 999, poste.id)
    # Le poste n'a pas été traité (le refus a précédé toute écriture).
    intact = service.lister(tournoi_id)[0]
    assert intact.statut is StatutRemboursement.A_REMBOURSER
    assert remboursements.traces == []


def test_marquer_un_poste_inconnu_leve() -> None:
    """Traiter un remboursement inexistant lève `RemboursementIntrouvable` (404)."""
    service, _, tournoi_id = _monter()
    with pytest.raises(RemboursementIntrouvable):
        service.marquer_rembourse(tournoi_id, 404)
