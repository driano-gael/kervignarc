"""Tests unitaires de l'agrégat de duel `Duel` / `BaremeDuel` (E04US013) — domaine pur, sans base.

Dérivés des **CA** d'E04US013 (`stories/E04-saisie-scores.md`) et du **référentiel FFTA**
(`docs/referentiel-ffta.md` §6-8), **avant** l'implémentation (règle 9) :

- CA « sets » : points de set 2 / 1-1 / 0 ; premier à **6 points de set** (5 manches) ; format club
  premier à **4 pts** ; **arc à poulies au cumul** sans sets (A.7.5.2).
- CA « vainqueur » : vainqueur calculé selon le barème, transmis au moteur (un `Participant`).
- CA « barrage/shoot-off » (§8.2) : à égalité, **1 flèche**, plus haut score ; si l'égalité
  persiste, **plus près du centre** — désigné par le scoreur (l'appli ne mesure pas la distance).
"""

from __future__ import annotations

import pytest

from domain.blason import ZoneScore
from domain.duel import (
    BaremeDuel,
    Cote,
    Duel,
    ModeDuel,
    ResolveurBaremeDuelFfta,
)
from domain.erreurs import (
    BarrageIndecis,
    BarrageNonRequis,
    DuelDejaTranche,
    DuelIncomplet,
    DuelVerrouille,
    NombreFlechesVoleeInvalide,
    NomIntervenantInvalide,
    NumeroMancheInvalide,
    ValeurHorsBlason,
)
from domain.participant import Participant
from domain.serie import Volee

# Triple vertical 40 des duels (référentiel §6.2) : zones 10 → 6 + M (pas de 5 → 1, §4.4).
ZONES = (
    ZoneScore.DIX,
    ZoneScore.NEUF,
    ZoneScore.HUIT,
    ZoneScore.SEPT,
    ZoneScore.SIX,
    ZoneScore.MANQUE,
)

HAUT = Participant.individuel(1)
BAS = Participant.individuel(2)


def _volee(*valeurs: str) -> tuple[ZoneScore, ...]:
    return tuple(ZoneScore(v) for v in valeurs)


def _duel_sets() -> Duel:
    """Un duel vierge au barème FFTA classique (sets, 1er à 6, 5 manches de 3 flèches)."""
    return Duel.vide(BaremeDuel.preset_ffta_classique(), HAUT, BAS)


def _duel_cumul() -> Duel:
    """Un duel vierge au barème FFTA poulies (cumul, 5 volées de 3, sans sets)."""
    return Duel.vide(BaremeDuel.preset_ffta_poulies(), HAUT, BAS)


def _saisir(duel: Duel, numero: int, haut: tuple[str, ...], bas: tuple[str, ...]) -> Duel:
    """Saisit une manche (deux volées) au barème du duel, zones du triple 40."""
    return duel.saisir_manche(
        numero,
        _volee(*haut),
        _volee(*bas),
        zones_admises=ZONES,
        nb_fleches_par_volee=duel.bareme.nb_fleches_par_volee,
    )


# --- BaremeDuel : presets et invariants -----------------------------------------------------


def test_preset_ffta_classique_est_sets_premier_a_six() -> None:
    """CA sets : classique/arc nu tirent en **sets**, premier à 6 points, 5 manches de 3."""
    bareme = BaremeDuel.preset_ffta_classique()
    assert bareme.mode is ModeDuel.SETS
    assert bareme.points_pour_gagner == 6
    assert bareme.nb_manches == 5
    assert bareme.nb_fleches_par_volee == 3


def test_preset_ffta_poulies_est_cumul() -> None:
    """CA/A.7.5.2 : l'arc à poulies tire **au cumul**, 5 volées de 3, sans sets."""
    bareme = BaremeDuel.preset_ffta_poulies()
    assert bareme.mode is ModeDuel.CUMUL
    assert bareme.nb_manches == 5
    assert bareme.nb_fleches_par_volee == 3


def test_preset_club_est_sets_premier_a_quatre() -> None:
    """CA sets : le **format club** (`Tableaux.xlsx`) tire en sets, premier à **4 pts** (§11)."""
    bareme = BaremeDuel.preset_club()
    assert bareme.mode is ModeDuel.SETS
    assert bareme.points_pour_gagner == 4


# --- Points de set : 2 / 1-1 / 0 (référentiel §7) -------------------------------------------


def test_manche_gagnee_vaut_deux_points_perdue_zero() -> None:
    """§7 : le vainqueur de la manche marque **2** points de set, le perdant **0**."""
    duel = _saisir(_duel_sets(), 1, ("10", "10", "9"), ("9", "8", "8"))  # 29 vs 25
    resultat = duel.resultat
    assert (resultat.points_haut, resultat.points_bas) == (2, 0)


def test_manche_nulle_vaut_un_point_chacun() -> None:
    """§7 : **égalité de volée → 1 point de set chacun**."""
    duel = _saisir(_duel_sets(), 1, ("10", "9", "8"), ("9", "9", "9"))  # 27 vs 27
    resultat = duel.resultat
    assert (resultat.points_haut, resultat.points_bas) == (1, 1)


# --- Duel en sets : victoire, arrêt anticipé (§6.2, §7) -------------------------------------


def test_vainqueur_des_qu_un_camp_atteint_six_points() -> None:
    """CA vainqueur : à 6-0 après trois manches gagnées, le duel est tranché (pas de 4e manche)."""
    duel = _duel_sets()
    for numero in (1, 2, 3):
        duel = _saisir(duel, numero, ("10", "10", "10"), ("9", "9", "9"))  # 30 vs 27
    resultat = duel.resultat
    assert resultat.termine is True
    assert resultat.barrage_requis is False
    assert resultat.vainqueur is Cote.HAUT
    assert (resultat.points_haut, resultat.points_bas) == (6, 0)
    assert duel.vainqueur == HAUT


def test_duel_non_termine_tant_que_personne_n_a_six() -> None:
    """Un duel à 2-2 après deux manches n'est ni tranché ni en barrage."""
    duel = _saisir(_duel_sets(), 1, ("10", "10", "10"), ("6", "6", "6"))  # haut gagne
    duel = _saisir(duel, 2, ("6", "6", "6"), ("10", "10", "10"))  # bas gagne
    resultat = duel.resultat
    assert resultat.termine is False
    assert resultat.barrage_requis is False
    assert resultat.vainqueur is None
    assert duel.vainqueur is None


def test_ajouter_une_manche_a_un_duel_deja_tranche_est_refuse() -> None:
    """On ne tire pas une manche de plus une fois le duel gagné (6-0 en 3 manches)."""
    duel = _duel_sets()
    for numero in (1, 2, 3):
        duel = _saisir(duel, numero, ("10", "10", "10"), ("9", "9", "9"))
    with pytest.raises(DuelDejaTranche):
        _saisir(duel, 4, ("10", "10", "10"), ("9", "9", "9"))


# --- Barrage / shoot-off (référentiel §8.2) -------------------------------------------------


def _mener_a_egalite_cinq_partout(duel: Duel) -> Duel:
    """Cinq manches 2 gagnées / 2 perdues / 1 nulle → 5-5 (barrage requis, §7)."""
    duel = _saisir(duel, 1, ("10", "10", "10"), ("6", "6", "6"))  # haut +2
    duel = _saisir(duel, 2, ("10", "10", "10"), ("6", "6", "6"))  # haut +2
    duel = _saisir(duel, 3, ("6", "6", "6"), ("10", "10", "10"))  # bas +2
    duel = _saisir(duel, 4, ("6", "6", "6"), ("10", "10", "10"))  # bas +2
    duel = _saisir(duel, 5, ("9", "9", "9"), ("9", "9", "9"))  # nulle 1-1
    return duel


def test_egalite_de_sets_declenche_le_barrage() -> None:
    """§7 : 5-5 après 5 manches → **tir de barrage** requis, duel pas encore tranché."""
    duel = _mener_a_egalite_cinq_partout(_duel_sets())
    resultat = duel.resultat
    assert (resultat.points_haut, resultat.points_bas) == (5, 5)
    assert resultat.barrage_requis is True
    assert resultat.termine is False
    assert resultat.vainqueur is None


def test_barrage_plus_haut_score_gagne_et_ajoute_un_point() -> None:
    """§8.2 : au barrage, la flèche la plus haute gagne ; §7 : +1 point de set (6-5)."""
    duel = _mener_a_egalite_cinq_partout(_duel_sets())
    duel = duel.saisir_barrage(ZoneScore.DIX, ZoneScore.NEUF, zones_admises=ZONES)
    resultat = duel.resultat
    assert resultat.termine is True
    assert resultat.vainqueur is Cote.HAUT
    assert (resultat.points_haut, resultat.points_bas) == (6, 5)
    assert duel.vainqueur == HAUT


def test_barrage_a_egalite_de_fleche_exige_une_designation() -> None:
    """§8.2 : flèches égales → « plus près du centre », que l'appli ne mesure pas : à désigner."""
    duel = _mener_a_egalite_cinq_partout(_duel_sets())
    with pytest.raises(BarrageIndecis):
        duel.saisir_barrage(ZoneScore.DIX, ZoneScore.DIX, zones_admises=ZONES)


def test_barrage_egalite_de_fleche_tranche_par_designation() -> None:
    """§8.2 : à flèches égales, le scoreur désigne le plus près du centre → vainqueur."""
    duel = _mener_a_egalite_cinq_partout(_duel_sets())
    duel = duel.saisir_barrage(
        ZoneScore.DIX, ZoneScore.DIX, gagnant_designe=Cote.BAS, zones_admises=ZONES
    )
    resultat = duel.resultat
    assert resultat.termine is True
    assert resultat.vainqueur is Cote.BAS
    assert duel.vainqueur == BAS


def test_barrage_re_editable_tant_que_non_valide() -> None:
    """Un barrage erroné se corrige avant validation (comme une manche) — pas de faux figé."""
    duel = _mener_a_egalite_cinq_partout(_duel_sets())
    duel = duel.saisir_barrage(ZoneScore.DIX, ZoneScore.NEUF, zones_admises=ZONES)  # haut gagne
    assert duel.resultat.vainqueur is Cote.HAUT
    duel = duel.saisir_barrage(ZoneScore.NEUF, ZoneScore.DIX, zones_admises=ZONES)  # correction
    assert duel.resultat.vainqueur is Cote.BAS


def test_barrage_refuse_si_non_requis() -> None:
    """Pas de barrage tant que le duel n'est pas à égalité de sets."""
    duel = _saisir(_duel_sets(), 1, ("10", "10", "10"), ("9", "9", "9"))
    with pytest.raises(BarrageNonRequis):
        duel.saisir_barrage(ZoneScore.DIX, ZoneScore.NEUF, zones_admises=ZONES)


# --- Duel au cumul (arc à poulies, A.7.5.2) -------------------------------------------------


def test_cumul_plus_haut_total_gagne() -> None:
    """A.7.5.2 : en poulies, pas de sets — le **plus haut cumul** des 5 volées gagne."""
    duel = _duel_cumul()
    for numero in range(1, 6):
        duel = _saisir(duel, numero, ("10", "10", "9"), ("10", "9", "9"))  # 29 vs 28 / volée
    resultat = duel.resultat
    assert resultat.termine is True
    assert resultat.barrage_requis is False
    assert resultat.vainqueur is Cote.HAUT
    assert (resultat.points_haut, resultat.points_bas) == (29 * 5, 28 * 5)
    assert duel.vainqueur == HAUT


def test_cumul_non_termine_avant_toutes_les_volees() -> None:
    """Au cumul, le duel n'est tranché qu'une fois les 5 volées de chaque camp saisies."""
    duel = _saisir(_duel_cumul(), 1, ("10", "10", "10"), ("9", "9", "9"))
    assert duel.resultat.termine is False
    assert duel.resultat.vainqueur is None


def test_cumul_egalite_declenche_le_barrage() -> None:
    """Au cumul, égalité de total après 5 volées → barrage (1 flèche, §8.2)."""
    duel = _duel_cumul()
    for numero in range(1, 6):
        duel = _saisir(duel, numero, ("10", "9", "8"), ("9", "9", "9"))  # 27 vs 27 / volée
    assert duel.resultat.barrage_requis is True
    duel = duel.saisir_barrage(ZoneScore.DIX, ZoneScore.NEUF, zones_admises=ZONES)
    assert duel.resultat.vainqueur is Cote.HAUT
    assert duel.resultat.termine is True


# --- Gardes de saisie -----------------------------------------------------------------------


def test_numero_de_manche_hors_bareme_refuse() -> None:
    """Le rang d'une manche est borné par le barème (5 manches) — serveur autoritaire."""
    with pytest.raises(NumeroMancheInvalide):
        _saisir(_duel_sets(), 6, ("10", "10", "10"), ("9", "9", "9"))


def test_volee_de_duel_valeurs_hors_blason_refusee() -> None:
    """Le pavé du triple 40 n'a pas les zones 5 → 1 (§4.4) : une valeur hors zones est refusée."""
    with pytest.raises(ValeurHorsBlason):
        _saisir(_duel_sets(), 1, ("10", "10", "5"), ("9", "9", "9"))


def test_volee_de_duel_mauvais_nombre_de_fleches_refusee() -> None:
    """Une volée de duel compte exactement `nb_fleches_par_volee` flèches (3)."""
    with pytest.raises(NombreFlechesVoleeInvalide):
        _saisir(_duel_sets(), 1, ("10", "10"), ("9", "9", "9"))


# --- Validation (grain fin de duel) ---------------------------------------------------------


def test_valider_un_duel_non_termine_est_refuse() -> None:
    """On ne valide un duel qu'une fois le vainqueur connu (grain fin de duel)."""
    duel = _saisir(_duel_sets(), 1, ("10", "10", "10"), ("9", "9", "9"))
    with pytest.raises(DuelIncomplet):
        duel.valider("DURAND")


def test_valider_verrouille_le_duel_et_nomme_le_scoreur() -> None:
    """La validation porte le nom du scoreur et verrouille le duel (plus de saisie)."""
    duel = _duel_sets()
    for numero in (1, 2, 3):
        duel = _saisir(duel, numero, ("10", "10", "10"), ("9", "9", "9"))
    duel = duel.valider("DURAND")
    assert duel.validee_par == "DURAND"
    assert duel.verrouille is True
    with pytest.raises(DuelVerrouille):
        _saisir(duel, 1, ("6", "6", "6"), ("9", "9", "9"))


def test_valider_un_duel_deja_valide_refuse() -> None:
    """La validation ne se réécrit pas : re-valider un duel scellé n'écrase pas le validateur."""
    duel = _duel_sets()
    for numero in (1, 2, 3):
        duel = _saisir(duel, numero, ("10", "10", "10"), ("9", "9", "9"))
    duel = duel.valider("DURAND")
    with pytest.raises(DuelVerrouille):
        duel.valider("MARTIN")


def test_valider_refuse_un_nom_vide() -> None:
    """Le nom du scoreur qui valide ne peut être vide (comme la série de qualification)."""
    duel = _duel_sets()
    for numero in (1, 2, 3):
        duel = _saisir(duel, numero, ("10", "10", "10"), ("9", "9", "9"))
    with pytest.raises(NomIntervenantInvalide):
        duel.valider("   ")


# --- Résolveur de barème par arme (défaut FFTA) ---------------------------------------------


@pytest.mark.parametrize("arme", ["Arc à Poulies", "poulies", "COMPOUND"])
def test_resolveur_ffta_poulies_donne_le_cumul(arme: str) -> None:
    """Le résolveur par défaut donne le **cumul** pour l'arc à poulies (A.7.5.2)."""
    bareme = ResolveurBaremeDuelFfta().bareme_pour(arme)
    assert bareme.mode is ModeDuel.CUMUL


@pytest.mark.parametrize("arme", ["Arc Classique", "Arc Nu", None, "recurve"])
def test_resolveur_ffta_autres_armes_donnent_les_sets(arme: str | None) -> None:
    """Le résolveur par défaut donne les **sets** (1er à 6) pour toute arme non-poulies."""
    bareme = ResolveurBaremeDuelFfta().bareme_pour(arme)
    assert bareme.mode is ModeDuel.SETS
    assert bareme.points_pour_gagner == 6


# --- Réutilisation de `Volee` : une manche porte deux volées de `ZoneScore` -----------------


def test_manche_expose_ses_deux_volees() -> None:
    """Une `MancheDuel` réutilise `Volee` (mutualisation, ADR-0049) : deux volées de `ZoneScore`."""
    duel = _saisir(_duel_sets(), 1, ("10", "9", "8"), ("7", "6", "6"))
    manche = duel.manche(1)
    assert manche is not None
    assert isinstance(manche.volee_haut, Volee)
    assert manche.volee_haut.points == 27
    assert manche.volee_bas.points == 19
