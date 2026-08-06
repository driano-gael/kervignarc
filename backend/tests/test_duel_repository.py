"""Tests d'intégration du repository SQL du tir de duel (E04US013, ADR-0049).

Exerce l'adapter sur une **vraie base** migrée (`alembic upgrade head`) : aller-retour du tir d'un
match (manches + barrage + validateur) **et de l'identité des duellistes** (ancrage
anti-ré-attribution, ADR-0049 §4), réhydratation avec le seul barème réinjecté, upsert sur `(phase,
match)`, et le repérage des matchs porteurs d'un tir. Tests **après** l'implémentation (adapter, pas
d'oracle métier — règle 9).
"""

from __future__ import annotations

import datetime
from pathlib import Path

from domain.blason import ZoneScore
from domain.depart import Depart
from domain.duel import BaremeDuel, Cote, Duel
from domain.participant import Participant
from domain.phase import Phase, TypePhase
from domain.tournoi import Tournoi
from infrastructure.db import (
    Database,
    DepartRepositorySQL,
    DuelRepositorySQL,
    PhaseRepositorySQL,
    TournoiRepositorySQL,
)
from tests.base_migree import preparer_base

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)

HAUT = Participant.individuel(1)
BAS = Participant.individuel(2)
ZONES = (ZoneScore.DIX, ZoneScore.NEUF, ZoneScore.HUIT, ZoneScore.SEPT, ZoneScore.SIX)


def _migrer(url: str) -> None:
    preparer_base(url)


class _Decor:
    """Base jetable migrée + tournoi/phase d'élimination prêts pour enregistrer un duel."""

    def __init__(self, tmp_path: Path) -> None:
        url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
        _migrer(url)
        self.db = Database(url)
        tournoi = TournoiRepositorySQL(self.db.session_factory).ajouter(
            Tournoi.creer("Salle 18m", _DATE)
        )
        assert tournoi.id is not None
        depart = DepartRepositorySQL(self.db.session_factory).ajouter(
            Depart.creer(tournoi_id=tournoi.id, numero=1, tarif_centimes=800, horaire="09:00")
        )
        assert depart.id is not None
        self.depart_id = depart.id
        _depart_id = depart.id
        phase = PhaseRepositorySQL(self.db.session_factory).ajouter(
            Phase.creer(_depart_id, 2, TypePhase.ELIMINATION_DIRECTE)
        )
        assert phase.id is not None
        self.phase_id = phase.id

    @property
    def duels(self) -> DuelRepositorySQL:
        return DuelRepositorySQL(self.db.session_factory)


def _saisir(duel: Duel, numero: int, haut: tuple[str, ...], bas: tuple[str, ...]) -> Duel:
    return duel.saisir_manche(
        numero,
        tuple(ZoneScore(v) for v in haut),
        tuple(ZoneScore(v) for v in bas),
        zones_admises=ZONES,
        nb_fleches_par_volee=3,
    )


def _charger(decor: _Decor, numero: int) -> Duel | None:
    return decor.duels.charger(decor.phase_id, numero, bareme=BaremeDuel.preset_ffta_classique())


def test_enregistrer_puis_charger_un_duel_valide(tmp_path: Path) -> None:
    """Aller-retour d'un duel tranché et validé : manches + validateur préservés à l'identique."""
    decor = _Decor(tmp_path)
    try:
        duel = Duel.vide(BaremeDuel.preset_ffta_classique(), HAUT, BAS)
        for numero in (1, 2, 3):
            duel = _saisir(duel, numero, ("10", "10", "10"), ("9", "9", "9"))
        duel = duel.valider("DURAND")
        decor.duels.enregistrer(decor.phase_id, 5, duel)
        relu = _charger(decor, 5)
        assert relu == duel
        assert relu is not None and relu.validee_par == "DURAND"
        assert relu.vainqueur == HAUT
    finally:
        decor.db.engine.dispose()


def test_aller_retour_avec_barrage(tmp_path: Path) -> None:
    """Le barrage (flèches + gagnant désigné) survit à l'aller-retour."""
    decor = _Decor(tmp_path)
    try:
        duel = Duel.vide(BaremeDuel.preset_ffta_classique(), HAUT, BAS)
        duel = _saisir(duel, 1, ("10", "10", "10"), ("6", "6", "6"))
        duel = _saisir(duel, 2, ("10", "10", "10"), ("6", "6", "6"))
        duel = _saisir(duel, 3, ("6", "6", "6"), ("10", "10", "10"))
        duel = _saisir(duel, 4, ("6", "6", "6"), ("10", "10", "10"))
        duel = _saisir(duel, 5, ("9", "9", "9"), ("9", "9", "9"))
        duel = duel.saisir_barrage(
            ZoneScore.DIX, ZoneScore.DIX, gagnant_designe=Cote.BAS, zones_admises=ZONES
        )
        decor.duels.enregistrer(decor.phase_id, 3, duel)
        relu = _charger(decor, 3)
        assert relu == duel
        assert relu is not None and relu.barrage is not None
        assert relu.barrage.gagnant_designe is Cote.BAS
        assert relu.vainqueur == BAS
    finally:
        decor.db.engine.dispose()


def test_charger_un_match_sans_tir_renvoie_none(tmp_path: Path) -> None:
    """Un match sans tir enregistré n'a pas de duel (`None`)."""
    decor = _Decor(tmp_path)
    try:
        assert _charger(decor, 1) is None
    finally:
        decor.db.engine.dispose()


def test_enregistrer_est_un_upsert(tmp_path: Path) -> None:
    """Réenregistrer le même `(phase, match)` remplace le tir (pas de doublon)."""
    decor = _Decor(tmp_path)
    try:
        duel = _saisir(
            Duel.vide(BaremeDuel.preset_ffta_classique(), HAUT, BAS),
            1,
            ("10", "10", "10"),
            ("6", "6", "6"),
        )
        decor.duels.enregistrer(decor.phase_id, 2, duel)
        duel2 = _saisir(duel, 2, ("6", "6", "6"), ("10", "10", "10"))
        decor.duels.enregistrer(decor.phase_id, 2, duel2)
        relu = _charger(decor, 2)
        assert relu == duel2
        assert decor.duels.numeros_enregistres(decor.phase_id) == frozenset({2})
    finally:
        decor.db.engine.dispose()


def test_numeros_enregistres_liste_les_matchs_avec_tir(tmp_path: Path) -> None:
    """`numeros_enregistres` repère les matchs porteurs d'un tir (pour la reconstruction)."""
    decor = _Decor(tmp_path)
    try:
        duel = _saisir(
            Duel.vide(BaremeDuel.preset_ffta_classique(), HAUT, BAS),
            1,
            ("10", "10", "10"),
            ("6", "6", "6"),
        )
        decor.duels.enregistrer(decor.phase_id, 1, duel)
        decor.duels.enregistrer(decor.phase_id, 4, duel)
        assert decor.duels.numeros_enregistres(decor.phase_id) == frozenset({1, 4})
    finally:
        decor.db.engine.dispose()
