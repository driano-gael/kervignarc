"""Tests du calcul de récapitulatif de paiement (E08US002) — dérivés du **CA**.

Source : `stories/E08-paiements.md`, E08US002, puces « vue par archer » (« dû / payé / reste ») et
« vue par club » (« totaux par club »). On y vérifie la **règle de dérivation** pure, sans
repository : dû = somme des tarifs, payé = somme des tarifs payés, reste = dû - payé, et le total
qui agrège des récapitulatifs (le club somme ses archers).
"""

from __future__ import annotations

import datetime

from domain.paiement import Dette, RecapPaiement, dater_la_dette, recapituler, total


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


# --- Ancienneté de la dette (E17US012, CA A17) -------------------------------------------------
# Source : `stories/E17-fidelite-aux-maquettes.md`, E17US012, puce « A17 » de l'arbitrage du
# 26/09/2026 : la dette date de la **plus ancienne inscription non réglée** ; une inscription
# antérieure à la migration n'a pas de date et s'affiche « date inconnue ».

_LUNDI = datetime.datetime(2026, 11, 2, 18, 0, tzinfo=datetime.UTC)
_MARDI = datetime.datetime(2026, 11, 3, 9, 0, tzinfo=datetime.UTC)


def test_sans_inscription_il_n_y_a_pas_de_dette() -> None:
    assert dater_la_dette([]) is None


def test_tout_regle_il_n_y_a_pas_de_dette() -> None:
    """Un archer qui ne doit plus rien n'a pas d'ancienneté, même inscrit à des dates connues."""
    assert dater_la_dette([(1400, True, _LUNDI), (1000, True, _MARDI)]) is None


def test_la_dette_date_de_la_plus_ancienne_inscription_non_reglee() -> None:
    """Deux créneaux non réglés : la dette court depuis le **premier** des deux."""
    dette = dater_la_dette([(1000, False, _MARDI), (1400, False, _LUNDI)])
    assert dette == Dette(depuis=_LUNDI)


def test_une_inscription_reglee_ne_date_pas_la_dette() -> None:
    """La plus ancienne inscription est **réglée** : elle ne compte pas, la suivante date."""
    dette = dater_la_dette([(1400, True, _LUNDI), (1000, False, _MARDI)])
    assert dette == Dette(depuis=_MARDI)


def test_un_creneau_gratuit_n_est_pas_une_dette() -> None:
    """Un créneau à 0 € non « réglé » ne doit rien : il ne crée ni ne date une dette.

    Sans cette exclusion, un archer au reste nul porterait une ancienneté — deux colonnes de la
    même ligne se contrediraient.
    """
    assert dater_la_dette([(0, False, _LUNDI)]) is None
    assert dater_la_dette([(0, False, _LUNDI), (1000, False, _MARDI)]) == Dette(depuis=_MARDI)


def test_une_inscription_non_datee_rend_l_anciennete_inconnue() -> None:
    """Une inscription sans date est antérieure à toutes les datées : la dette date d'**avant**
    la première date connue, on ne sait pas de quand — jamais la date de la suivante."""
    dette = dater_la_dette([(1000, False, _MARDI), (1400, False, None)])
    assert dette == Dette(depuis=None)


def test_une_inscription_reglee_non_datee_ne_rend_pas_la_dette_inconnue() -> None:
    """Le filtre « non réglé » passe **avant** l'examen de la date : une vieille inscription
    réglée, d'avant la migration, ne doit pas masquer la date de la dette en cours."""
    assert dater_la_dette([(1400, True, None), (1000, False, _MARDI)]) == Dette(depuis=_MARDI)


def test_une_dette_existe_exactement_quand_il_reste_a_payer() -> None:
    """Invariant de ligne : ancienneté présente ⇔ reste > 0 (les deux colonnes ne divergent pas)."""
    cas: list[list[tuple[int, bool, datetime.datetime | None]]] = [
        [],
        [(0, False, _LUNDI)],
        [(1000, True, _LUNDI)],
        [(1000, False, None)],
        [(1000, True, _LUNDI), (500, False, _MARDI)],
    ]
    for lignes in cas:
        reste = recapituler((tarif, paye) for tarif, paye, _ in lignes).reste_centimes
        assert (dater_la_dette(lignes) is not None) == (reste > 0), lignes
