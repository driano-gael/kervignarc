"""Tests unitaires des agrégats `Volee` / `Serie` (E04US002) — domaine pur, sans base.

Dérivés des **CA** d'E04US002 (`stories/E04-saisie-scores.md`), pas de l'implémentation
(règle 9) : pavé déduit du blason (ex-003), valeurs légales (ex-004), édition avant
validation (ex-006), validation & verrou + grain (ex-007), cumul (ex-008), correction
d'une volée verrouillée (ex-012), et « qui a saisi » (ex-017).
"""

from __future__ import annotations

import pytest

from domain.blason import ZoneScore
from domain.erreurs import (
    NombreFlechesVoleeInvalide,
    NomIntervenantInvalide,
    NumeroVoleeInvalide,
    RienAValider,
    SerieIncomplete,
    ValeurHorsBlason,
    VoleeIntrouvable,
    VoleeNonVerrouillee,
    VoleeVerrouillee,
)
from domain.grain_validation import GrainValidation
from domain.serie import Serie

# Zones d'un blason simple (10 → 1 + M) et d'un triple 40 (10 → 6 + M, référentiel §4.4).
ZONES_SIMPLE = tuple(ZoneScore)
ZONES_TRIPLE = (
    ZoneScore.DIX,
    ZoneScore.NEUF,
    ZoneScore.HUIT,
    ZoneScore.SEPT,
    ZoneScore.SIX,
    ZoneScore.MANQUE,
)


def _v(*valeurs: str) -> tuple[ZoneScore, ...]:
    """Raccourci : construit un tuple de `ZoneScore` à partir de libellés (« 10 », « M »)."""
    return tuple(ZoneScore(v) for v in valeurs)


def _serie_pleine(
    nb_volees: int, valeurs: tuple[ZoneScore, ...], *, nb_volees_bareme: int | None = None
) -> Serie:
    """Une série de `nb_volees` volées identiques (non validées).

    `nb_volees_bareme` (défaut : `nb_volees`) permet une série **incomplète** — k volées sur N — en
    gardant un **seul** barème cohérent entre saisie et validation (une phase n'a qu'un barème).
    """
    bareme = nb_volees_bareme if nb_volees_bareme is not None else nb_volees
    serie = Serie.vide(tournoi_id=1, archer_id=7)
    for numero in range(1, nb_volees + 1):
        serie = serie.saisir_volee(
            numero,
            valeurs,
            zones_admises=ZONES_SIMPLE,
            nb_fleches_par_volee=len(valeurs),
            nb_volees_bareme=bareme,
        )
    return serie


# --- Volee : pavé, valeurs légales, points, « qui a saisi » ---------------------------------


def test_saisir_une_volee_enregistre_valeurs_et_marqueur() -> None:
    """ex-005/017 : une volée porte ses valeurs et le nom du marqueur qui l'a saisie."""
    serie = Serie.vide(tournoi_id=1, archer_id=7).saisir_volee(
        1,
        _v("10", "9", "8"),
        zones_admises=ZONES_SIMPLE,
        nb_fleches_par_volee=3,
        nb_volees_bareme=3,
        saisie_par="DURAND",
    )
    volee = serie.volee(1)
    assert volee is not None
    assert volee.valeurs == _v("10", "9", "8")
    assert volee.saisie_par == "DURAND"
    assert volee.verrouillee is False


def test_points_d_une_volee_somme_les_zones_le_manque_vaut_zero() -> None:
    """ex-008 : le total d'une volée somme les zones ; `M` (manqué) vaut 0."""
    serie = Serie.vide(tournoi_id=1, archer_id=7).saisir_volee(
        1,
        _v("10", "M", "7"),
        zones_admises=ZONES_SIMPLE,
        nb_fleches_par_volee=3,
        nb_volees_bareme=3,
    )
    assert serie.volee(1).points == 17  # type: ignore[union-attr]


def test_pave_deduit_du_blason_refuse_une_valeur_hors_zones() -> None:
    """ex-003/004 : sur un triple 40 les zones 5 → 1 n'existent pas ; un « 5 » est refusé."""
    serie = Serie.vide(tournoi_id=1, archer_id=7)
    with pytest.raises(ValeurHorsBlason):
        serie.saisir_volee(
            1,
            _v("10", "9", "5"),
            zones_admises=ZONES_TRIPLE,
            nb_fleches_par_volee=3,
            nb_volees_bareme=3,
        )


def test_valeurs_legales_refuse_un_mauvais_nombre_de_fleches() -> None:
    """ex-004 : le nombre de flèches d'une volée doit être conforme au barème."""
    serie = Serie.vide(tournoi_id=1, archer_id=7)
    with pytest.raises(NombreFlechesVoleeInvalide):
        serie.saisir_volee(
            1,
            _v("10", "9"),
            zones_admises=ZONES_SIMPLE,
            nb_fleches_par_volee=3,
            nb_volees_bareme=3,
        )


@pytest.mark.parametrize("numero", [0, -1])
def test_numero_de_volee_doit_etre_positif(numero: int) -> None:
    """Un numéro de volée est un rang `>= 1`."""
    serie = Serie.vide(tournoi_id=1, archer_id=7)
    with pytest.raises(NumeroVoleeInvalide):
        serie.saisir_volee(
            numero,
            _v("10", "9", "8"),
            zones_admises=ZONES_SIMPLE,
            nb_fleches_par_volee=3,
            nb_volees_bareme=3,
        )


# --- Édition avant validation (ex-006) ------------------------------------------------------


def test_editer_une_volee_non_validee_remplace_ses_valeurs() -> None:
    """ex-006 : une volée est modifiable tant qu'elle n'est pas validée."""
    serie = Serie.vide(tournoi_id=1, archer_id=7).saisir_volee(
        1,
        _v("10", "9", "8"),
        zones_admises=ZONES_SIMPLE,
        nb_fleches_par_volee=3,
        nb_volees_bareme=3,
    )
    serie = serie.saisir_volee(
        1, _v("9", "9", "9"), zones_admises=ZONES_SIMPLE, nb_fleches_par_volee=3, nb_volees_bareme=3
    )
    assert serie.volee(1).valeurs == _v("9", "9", "9")  # type: ignore[union-attr]
    assert len(serie.volees) == 1  # remplacement, pas ajout


def test_editer_une_volee_verrouillee_par_saisie_est_refuse() -> None:
    """ex-006/007 : une fois validée, une volée n'est plus modifiable par simple saisie."""
    serie = _serie_pleine(1, _v("10", "9", "8")).valider(
        "MARTIN", grain=GrainValidation.fin_de_serie(), nb_volees_bareme=1
    )
    with pytest.raises(VoleeVerrouillee):
        serie.saisir_volee(
            1,
            _v("9", "9", "9"),
            zones_admises=ZONES_SIMPLE,
            nb_fleches_par_volee=3,
            nb_volees_bareme=1,
        )


# --- Validation, verrou, grain (ex-007) & cumul (ex-008) -----------------------------------


def test_valider_fin_de_serie_verrouille_tout_et_porte_le_nom_du_scoreur() -> None:
    """ex-007 : en fin de série, la validation verrouille toutes les volées au nom du scoreur."""
    serie = _serie_pleine(3, _v("10", "10", "10")).valider(
        "MARTIN", grain=GrainValidation.fin_de_serie(), nb_volees_bareme=3
    )
    assert all(v.verrouillee for v in serie.volees)
    assert all(v.validee_par == "MARTIN" for v in serie.volees)


def test_valider_fin_de_serie_avant_la_derniere_volee_est_refuse() -> None:
    """ex-007 : « fin de série » suppose la série complète — valider à 2/3 volées est refusé."""
    serie = _serie_pleine(2, _v("10", "9", "8"), nb_volees_bareme=3)
    with pytest.raises(SerieIncomplete):
        serie.valider("MARTIN", grain=GrainValidation.fin_de_serie(), nb_volees_bareme=3)


def test_valider_fin_de_serie_avec_un_trou_au_milieu_est_refuse() -> None:
    """Complétude sur l'ensemble `{1..N}`, pas un décompte : une série **trouée** (volées 1 et 3,
    barème 3) est refusée en fin de série — comme une série courte, alors que `len` vaudrait 2."""
    serie = Serie.vide(tournoi_id=1, archer_id=7)
    for numero in (1, 3):  # volée 2 absente : trou au milieu, pas en queue
        serie = serie.saisir_volee(
            numero,
            _v("10", "9", "8"),
            zones_admises=ZONES_SIMPLE,
            nb_fleches_par_volee=3,
            nb_volees_bareme=3,
        )
    with pytest.raises(SerieIncomplete):
        serie.valider("MARTIN", grain=GrainValidation.fin_de_serie(), nb_volees_bareme=3)


def test_cumul_ne_compte_que_les_volees_validees() -> None:
    """ex-008 : le cumul se met à jour à chaque validation ; les non validées n'y sont pas."""
    serie = _serie_pleine(3, _v("10", "9", "8"))  # 27 par volée, rien de validé
    assert serie.cumul == 0
    serie = serie.valider("MARTIN", grain=GrainValidation.fin_de_serie(), nb_volees_bareme=3)
    assert serie.cumul == 81  # 3 x 27


def test_nb_fleches_validees_ne_compte_que_les_volees_validees() -> None:
    """« A tiré » (E02US003, gardes d'engagement) = flèches des volées **validées**.

    Arbitrage du 20/07/2026 (`stories/E02-inscriptions.md`) : miroir de `cumul` — tant que le
    scoreur n'a pas validé, la volée est un état intermédiaire, elle ne compte pas comme un tir.
    Le manqué (`M`) est **compté** : une flèche manquée reste une flèche tirée (le total l'ignore).
    """
    serie = _serie_pleine(2, _v("10", "9", "M"))  # 2 volées de 3 flèches, rien de validé
    assert serie.nb_fleches_validees == 0
    serie = serie.valider("MARTIN", grain=GrainValidation.fin_de_serie(), nb_volees_bareme=2)
    assert serie.nb_fleches_validees == 6  # 2 x 3 flèches, le M compris


def test_valider_toutes_les_n_volees_verrouille_par_lots() -> None:
    """ex-007 : « toutes les N volées » verrouille le prochain lot de N volées complètes."""
    serie = _serie_pleine(3, _v("10", "9", "8"), nb_volees_bareme=6)
    grain = GrainValidation.toutes_les_n_volees(2)
    serie = serie.valider("MARTIN", grain=grain, nb_volees_bareme=6)
    # Seules les 2 premieres volees sont verrouillees ; la 3e attend le prochain lot.
    assert serie.volee(1).verrouillee and serie.volee(2).verrouillee  # type: ignore[union-attr]
    assert not serie.volee(3).verrouillee  # type: ignore[union-attr]
    assert serie.cumul == 54  # 2 x 27


def test_valider_toutes_les_n_volees_verrouille_le_reliquat_en_fin_de_bareme() -> None:
    """ex-007 : le reliquat (< N volées) est validé une fois toutes les volées du barème saisies."""
    serie = _serie_pleine(3, _v("10", "9", "8"))  # barème de 3, grain toutes les 2
    grain = GrainValidation.toutes_les_n_volees(2)
    serie = serie.valider("MARTIN", grain=grain, nb_volees_bareme=3)  # lot 1-2
    serie = serie.valider("MARTIN", grain=grain, nb_volees_bareme=3)  # reliquat : volée 3
    assert all(v.verrouillee for v in serie.volees)
    assert serie.cumul == 81


def test_valider_sans_lot_complet_ni_reliquat_ne_valide_rien() -> None:
    """ex-007 : sans lot de N complet ni fin de barème, il n'y a rien à valider."""
    serie = _serie_pleine(1, _v("10", "9", "8"), nb_volees_bareme=6)  # 1 volée sur 6, grain « 2 »
    with pytest.raises(RienAValider):
        serie.valider("MARTIN", grain=GrainValidation.toutes_les_n_volees(2), nb_volees_bareme=6)


# --- Correction tracée d'une volée verrouillée (ex-012) -------------------------------------


def test_corriger_une_volee_verrouillee_remplace_les_valeurs_et_recalcule_le_cumul() -> None:
    """ex-012 : corriger une volée verrouillée recalcule le cumul — prouvé sur une somme DIFFÉRENTE.

    Série de 2 volées à 27 (cumul 54) ; corriger la 1ʳᵉ de 27 à 15 (5,5,5) : le cumul doit passer
    à 42 (15 + 27), ce qui échoue si la correction ne réécrit pas les valeurs *et* le cumul.
    """
    serie = _serie_pleine(2, _v("10", "9", "8")).valider(
        "MARTIN", grain=GrainValidation.fin_de_serie(), nb_volees_bareme=2
    )
    assert serie.cumul == 54
    serie = serie.corriger_volee(
        1, _v("5", "5", "5"), par="ARBITRE", zones_admises=ZONES_SIMPLE, nb_fleches_par_volee=3
    )
    assert serie.volee(1).valeurs == _v("5", "5", "5")  # type: ignore[union-attr]
    assert serie.volee(1).verrouillee  # type: ignore[union-attr]
    assert serie.cumul == 42  # 15 (volée 1 corrigée) + 27 (volée 2 intacte)


def test_corriger_une_volee_non_verrouillee_est_refuse() -> None:
    """ex-012 : seul le verrouillé se corrige ; une volée en cours se modifie par saisie."""
    serie = _serie_pleine(1, _v("10", "9", "8"))  # non validée
    with pytest.raises(VoleeNonVerrouillee):
        serie.corriger_volee(
            1, _v("9", "9", "9"), par="ARBITRE", zones_admises=ZONES_SIMPLE, nb_fleches_par_volee=3
        )


def test_corriger_une_volee_inexistante_est_refuse() -> None:
    """Corriger une volée qui n'existe pas est une erreur, pas une création."""
    serie = _serie_pleine(1, _v("10", "9", "8")).valider(
        "MARTIN", grain=GrainValidation.fin_de_serie(), nb_volees_bareme=1
    )
    with pytest.raises(VoleeIntrouvable):
        serie.corriger_volee(
            9, _v("9", "9", "9"), par="ARBITRE", zones_admises=ZONES_SIMPLE, nb_fleches_par_volee=3
        )


# --- Garde-fous du serveur autoritaire (durcissement de revue) -------------------------------


def test_saisir_une_volee_au_dela_du_bareme_est_refuse() -> None:
    """Serveur autoritaire : un rang de volée au-delà du barème est refusé — sinon cumul gonflable.

    Symétrique de la garde sur le nombre de flèches (ex-004) : sans borne haute, saisir la volée 3
    d'un barème à 2 volées entrerait dans le cumul à la validation.
    """
    serie = Serie.vide(tournoi_id=1, archer_id=7)
    with pytest.raises(NumeroVoleeInvalide):
        serie.saisir_volee(
            3,
            _v("10", "9", "8"),
            zones_admises=ZONES_SIMPLE,
            nb_fleches_par_volee=3,
            nb_volees_bareme=2,
        )


def test_valider_refuse_un_validateur_vide() -> None:
    """Un verrou nomme son validateur : un nom vide (ou en blancs) est refusé au domaine."""
    serie = _serie_pleine(1, _v("10", "9", "8"))
    with pytest.raises(NomIntervenantInvalide):
        serie.valider("   ", grain=GrainValidation.fin_de_serie(), nb_volees_bareme=1)


def test_corriger_refuse_un_correcteur_vide() -> None:
    """La correction aussi nomme son auteur : un correcteur vide est refusé au domaine."""
    serie = _serie_pleine(1, _v("10", "9", "8")).valider(
        "MARTIN", grain=GrainValidation.fin_de_serie(), nb_volees_bareme=1
    )
    with pytest.raises(NomIntervenantInvalide):
        serie.corriger_volee(
            1, _v("9", "9", "9"), par="", zones_admises=ZONES_SIMPLE, nb_fleches_par_volee=3
        )
