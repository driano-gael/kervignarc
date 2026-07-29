"""Tests de l'agrégat `Remboursement` (E08US005) — dérivés du **CA**.

Source : `stories/E08-paiements.md`, E08US005, puce « **CA** » (« le montant encaissé devient un
remboursement à traiter ; l'admin le marque **remboursé** (daté, tracé) ou **reporté** ») et Notes
(« registre daté »). On vérifie ici la seule règle qui vive dans l'entité — le cycle de vie à trois
états et l'invariant de construction `montant > 0`. Le refus de **re-traiter** un poste déjà traité
est un conflit d'état porté par le **service** (testé dans `test_service_remboursements`), pas par
l'entité : rien à en tester ici.

Pur : aucune persistance, aucune horloge réelle — un instant UTC figé sert de date.
"""

from __future__ import annotations

import datetime

import pytest

from domain.erreurs import RemboursementMontantInvalide
from domain.remboursement import MotifRemboursement, Remboursement, StatutRemboursement

_INSTANT = datetime.datetime(2026, 7, 29, 10, 0, tzinfo=datetime.UTC)
_PLUS_TARD = datetime.datetime(2026, 7, 29, 11, 30, tzinfo=datetime.UTC)


def _remboursement(montant: int = 810) -> Remboursement:
    """Un remboursement à traiter typique (désinscription d'une inscription payée)."""
    return Remboursement.creer(
        1,
        archer_prenom="Jean",
        archer_nom="Dupont",
        creneau="Départ n°1 — 09:00",
        montant_centimes=montant,
        motif=MotifRemboursement.DESINSCRIPTION,
        cree_le=_INSTANT,
    )


def test_creer_ouvre_un_poste_a_rembourser_non_traite() -> None:
    """Un remboursement naît **à traiter** (CA « devient un remboursement à traiter ») : statut
    `à_rembourser`, `traite_le` vide, montant et instantanés préservés."""
    remboursement = _remboursement()
    assert remboursement.statut is StatutRemboursement.A_REMBOURSER
    assert remboursement.traite_le is None
    assert remboursement.montant_centimes == 810
    assert remboursement.cree_le == _INSTANT
    assert (remboursement.archer_prenom, remboursement.archer_nom) == ("Jean", "Dupont")


def test_creer_refuse_un_montant_nul_ou_negatif() -> None:
    """Un remboursement de 0 € (ou négatif) n'a pas de raison d'exister (`montant > 0`).

    Garde-fou d'un créneau **gratuit** marqué payé : rien n'a été encaissé, rien à rendre — le site
    appelant filtre déjà les créneaux tarifés, mais l'entité défend l'invariant elle-même.
    """
    with pytest.raises(RemboursementMontantInvalide):
        _remboursement(montant=0)
    with pytest.raises(RemboursementMontantInvalide):
        _remboursement(montant=-100)


def test_marquer_rembourse_fige_le_statut_et_la_date() -> None:
    """« L'admin le marque **remboursé** (daté) » : statut `remboursé`, `traite_le` renseigné."""
    traite = _remboursement().marquer_rembourse(_PLUS_TARD)
    assert traite.statut is StatutRemboursement.REMBOURSE
    assert traite.traite_le == _PLUS_TARD


def test_marquer_reporte_fige_le_statut_et_la_date() -> None:
    """« ou **reporté** » : statut `reporté`, `traite_le` renseigné (intention consignée)."""
    traite = _remboursement().marquer_reporte(_PLUS_TARD)
    assert traite.statut is StatutRemboursement.REPORTE
    assert traite.traite_le == _PLUS_TARD


def test_le_traitement_ne_mute_pas_l_original() -> None:
    """L'agrégat est immuable (règle 4) : marquer renvoie une **copie**, l'original reste à
    traiter."""
    original = _remboursement()
    original.marquer_rembourse(_PLUS_TARD)
    assert original.statut is StatutRemboursement.A_REMBOURSER
    assert original.traite_le is None
