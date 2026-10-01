"""Tests de `ServiceSaisie.file_du_scoreur` (E04US019) — contre les faux ports de la saisie.

Dérivés des CA d'E04US019 (`stories/E04-saisie-scores.md`) : une ligne par **cible** dont un
archer placé a une feuille à valider, l'**ancienneté** mesurée depuis la plus récente volée du lot
et calculée par le serveur, le tri du plus ancien au plus récent, et les exclusions (correction
ouverte, phase en pause, archer en réserve, autre créneau). La règle « à valider » elle-même est
prouvée au domaine (`test_domain_serie_lot_a_valider`).
"""

from __future__ import annotations

import dataclasses
import datetime

from domain.archer import ArcherId
from domain.bareme import BaremeQualification
from domain.grain_validation import GrainValidation
from domain.inscription import Inscription
from domain.phase import Phase, StatutPhase
from domain.role import Role
from tests.test_service_saisie import _DEPART, _QUAND, Montage, _v


def _minutes(n: float) -> datetime.timedelta:
    return datetime.timedelta(minutes=n)


def _saisir(m: Montage, archer_id: ArcherId, *numeros: int) -> None:
    for numero in numeros:
        m.service.saisir_volee(m.tournoi_id, archer_id, numero, _v("10", "9", "8"), role=Role.ADMIN)


def _dater(m: Montage, archer_id: ArcherId, **il_y_a: float) -> None:
    """Force le « quand » des volées : `v1=5` = volée 1 saisie il y a 5 minutes."""
    m.series.horodatages_forces[(m.phase_id, archer_id)] = {
        int(cle[1:]): _QUAND - _minutes(minutes) for cle, minutes in il_y_a.items()
    }


def test_rien_de_saisi_donne_une_file_vide() -> None:
    m = Montage()
    m.placer(m.archer_id, _DEPART, 3, "A")
    assert m.service.file_du_scoreur(m.tournoi_id, _DEPART) == []


def test_une_feuille_complete_place_sa_cible_dans_la_file() -> None:
    m = Montage()
    m.placer(m.archer_id, _DEPART, 3, "A")
    _saisir(m, m.archer_id, 1, 2)
    _dater(m, m.archer_id, v1=9, v2=4)

    (cible,) = m.service.file_du_scoreur(m.tournoi_id, _DEPART)

    assert cible.cible_index == 3
    assert [ligne.archer.nom for ligne in cible.archers] == ["DUPONT"]
    assert cible.archers[0].position == "A"
    # La volée 2 a complété la série : c'est elle qui l'a rendue validable.
    assert cible.attente == _minutes(4)


def test_une_feuille_incomplete_n_attend_rien() -> None:
    m = Montage()
    m.placer(m.archer_id, _DEPART, 3, "A")
    _saisir(m, m.archer_id, 1)
    assert m.service.file_du_scoreur(m.tournoi_id, _DEPART) == []


def test_une_feuille_validee_quitte_la_file() -> None:
    m = Montage()
    m.placer(m.archer_id, _DEPART, 3, "A")
    _saisir(m, m.archer_id, 1, 2)
    m.service.valider(m.tournoi_id, m.archer_id, scoreur="RIOU")
    assert m.service.file_du_scoreur(m.tournoi_id, _DEPART) == []


def test_les_cibles_sont_triees_de_la_plus_ancienne_a_la_plus_recente() -> None:
    m = Montage()
    autre = m.nouvel_archer("MARTIN")
    troisieme = m.nouvel_archer("CADIOU")
    m.placer(m.archer_id, _DEPART, 12, "A")
    m.placer(autre, _DEPART, 14, "A")
    m.placer(troisieme, _DEPART, 19, "A")
    for archer_id, attente in ((m.archer_id, 2), (autre, 4), (troisieme, 0.5)):
        _saisir(m, archer_id, 1, 2)
        _dater(m, archer_id, v1=10, v2=attente)

    file = m.service.file_du_scoreur(m.tournoi_id, _DEPART)

    assert [c.cible_index for c in file] == [14, 12, 19]


def test_a_attente_egale_la_plus_petite_cible_passe_devant() -> None:
    m = Montage()
    autre = m.nouvel_archer("MARTIN")
    m.placer(m.archer_id, _DEPART, 9, "A")
    m.placer(autre, _DEPART, 2, "A")
    for archer_id in (m.archer_id, autre):
        _saisir(m, archer_id, 1, 2)
        _dater(m, archer_id, v1=3, v2=3)

    assert [c.cible_index for c in m.service.file_du_scoreur(m.tournoi_id, _DEPART)] == [2, 9]


def test_une_cible_attend_depuis_son_archer_le_plus_ancien() -> None:
    m = Montage()
    voisin = m.nouvel_archer("MARTIN")
    m.placer(m.archer_id, _DEPART, 5, "B")
    m.placer(voisin, _DEPART, 5, "A")
    _saisir(m, m.archer_id, 1, 2)
    _dater(m, m.archer_id, v1=8, v2=1)
    _saisir(m, voisin, 1, 2)
    _dater(m, voisin, v1=8, v2=6)

    (cible,) = m.service.file_du_scoreur(m.tournoi_id, _DEPART)

    assert cible.attente == _minutes(6)
    assert [(a.position, a.attente) for a in cible.archers] == [
        ("A", _minutes(6)),
        ("B", _minutes(1)),
    ]


def test_seuls_les_archers_en_attente_sont_nommes() -> None:
    m = Montage()
    voisin = m.nouvel_archer("MARTIN")
    m.placer(m.archer_id, _DEPART, 5, "A")
    m.placer(voisin, _DEPART, 5, "B")
    _saisir(m, m.archer_id, 1, 2)
    _saisir(m, voisin, 1)

    (cible,) = m.service.file_du_scoreur(m.tournoi_id, _DEPART)

    assert [a.archer.nom for a in cible.archers] == ["DUPONT"]


def test_un_archer_en_reserve_n_est_pas_dans_la_file() -> None:
    m = Montage()
    m.inscriptions.ajouter(Inscription(m.archer_id, _DEPART))  # inscrit, jamais placé
    _saisir(m, m.archer_id, 1, 2)
    assert m.service.file_du_scoreur(m.tournoi_id, _DEPART) == []


def test_un_autre_creneau_n_est_pas_dans_la_file() -> None:
    m = Montage()
    m.placer(m.archer_id, _DEPART, 3, "A")
    _saisir(m, m.archer_id, 1, 2)
    assert m.service.file_du_scoreur(m.tournoi_id, _DEPART + 1) == []


def test_une_correction_ouverte_n_est_pas_dans_la_file() -> None:
    m = Montage()
    m.placer(m.archer_id, _DEPART, 3, "A")
    _saisir(m, m.archer_id, 1, 2)
    m.service.valider(m.tournoi_id, m.archer_id, scoreur="RIOU")
    m.service.annuler_validation(m.tournoi_id, m.archer_id, 1, "RIOU")
    assert m.service.file_du_scoreur(m.tournoi_id, _DEPART) == []


def test_une_phase_en_pause_n_est_pas_dans_la_file() -> None:
    m = Montage()
    m.placer(m.archer_id, _DEPART, 3, "A")
    _saisir(m, m.archer_id, 1, 2)
    phase = m.phases.par_id(m.phase_id)
    assert phase is not None
    m.phases.enregistrer(dataclasses.replace(phase, statut=StatutPhase.EN_PAUSE))
    assert m.service.file_du_scoreur(m.tournoi_id, _DEPART) == []


def test_au_grain_toutes_les_n_l_attente_part_du_lot_pas_de_la_derniere_volee() -> None:
    m = Montage(avec_phase=False)
    posee = m.phases.ajouter(
        Phase.qualification(
            depart_id=_DEPART,
            bareme=BaremeQualification.creer(6, 3),
            validation=GrainValidation.toutes_les_n_volees(2),
        )
    )
    assert posee.id is not None
    m.phase_id = posee.id
    m.placer(m.archer_id, _DEPART, 3, "A")
    _saisir(m, m.archer_id, 1, 2, 3)
    _dater(m, m.archer_id, v1=12, v2=7, v3=1)

    (cible,) = m.service.file_du_scoreur(m.tournoi_id, _DEPART)

    # Le lot 1-2 est validable depuis la volée 2 ; la volée 3, hors lot, n'y change rien.
    assert cible.attente == _minutes(7)
