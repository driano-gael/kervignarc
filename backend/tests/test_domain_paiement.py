"""Tests du calcul de récapitulatif de paiement (E08US002) — dérivés du **CA**.

Source : `stories/E08-paiements.md`, E08US002, puces « vue par archer » (« dû / payé / reste ») et
« vue par club » (« totaux par club »). On y vérifie la **règle de dérivation** pure, sans
repository : dû = somme des tarifs, payé = somme des tarifs payés, reste = dû - payé, et le total
qui agrège des récapitulatifs (le club somme ses archers).
"""

from __future__ import annotations

from domain.paiement import RecapPaiement, recapituler, total


def test_recap_vide_est_zero() -> None:
    """Un périmètre sans inscription doit 0, a réglé 0, reste 0 (et non une erreur)."""
    recap = recapituler([])
    assert (recap.du_centimes, recap.paye_centimes, recap.reste_centimes) == (0, 0, 0)


def test_du_est_la_somme_de_tous_les_tarifs() -> None:
    """Le dû additionne **tous** les créneaux inscrits, payés ou non (CA « dû »)."""
    recap = recapituler([(810, False), (1000, True), (0, False)])
    assert recap.du_centimes == 1810


def test_paye_ne_compte_que_les_lignes_payees() -> None:
    """Le payé n'additionne que les tarifs des créneaux **marqués payés** (CA « payé »)."""
    recap = recapituler([(810, False), (1000, True), (500, True)])
    assert recap.paye_centimes == 1500  # 1000 + 500, pas les 810 non payés


def test_reste_est_du_moins_paye() -> None:
    """Le reste = dû - payé (CA « reste ») : ici 1810 dû, 1000 payé, 810 restant."""
    recap = recapituler([(810, False), (1000, True)])
    assert recap.reste_centimes == 810


def test_tout_paye_ne_laisse_aucun_reste() -> None:
    """Quand chaque créneau est payé, le reste tombe à 0 (le payé rejoint le dû)."""
    recap = recapituler([(810, True), (1000, True)])
    assert (recap.du_centimes, recap.paye_centimes, recap.reste_centimes) == (1810, 1810, 0)


def test_total_agrege_champ_a_champ() -> None:
    """Le total d'un club = somme des récapitulatifs de ses archers, champ à champ (CA « totaux »).

    Deux archers : l'un doit 1810 dont 1000 payé, l'autre 500 dont 0 payé — le club doit 2310, a
    réglé 1000, reste 1310.
    """
    archer_a = recapituler([(810, False), (1000, True)])
    archer_b = recapituler([(500, False)])
    club = total([archer_a, archer_b])
    assert (club.du_centimes, club.paye_centimes, club.reste_centimes) == (2310, 1000, 1310)


def test_total_vide_est_zero() -> None:
    """Un club sans archer (ou un tournoi sans club) totalise 0 / 0 / 0."""
    vide = total([])
    assert (vide.du_centimes, vide.paye_centimes, vide.reste_centimes) == (0, 0, 0)


def test_recap_est_immuable() -> None:
    """`RecapPaiement` est un value object gelé (règle 4) : reste n'est pas un champ modifiable."""
    recap = RecapPaiement(du_centimes=1000, paye_centimes=300)
    assert recap.reste_centimes == 700
