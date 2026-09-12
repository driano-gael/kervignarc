"""Tests unitaires de l'**annulation de validation** (E16US019) — domaine pur, sans base.

Dérivés des **CA** d'E16US019 (`stories/E16-retours-maquettes.md`), pas de l'implémentation
(règle 9) : l'annulation rouvre **le lot** identifié en base, la volée rouverte **reste comptée**
dans les totaux, la ressaisie **préserve** cet état, et `corriger_volee` **survit**.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from domain.blason import ZoneScore
from domain.erreurs import (
    CorrectionOuverte,
    IncoherenceVolee,
    NomIntervenantInvalide,
    VoleeIntrouvable,
    VoleeNonVerrouillee,
)
from domain.grain_validation import GrainValidation
from domain.role import Role
from domain.serie import Serie, Volee

ZONES_SIMPLE = tuple(ZoneScore)

_PHASE = 4
"""La phase où se tire la feuille (ADR-0082) — inerte ici, cf. `test_domain_serie.py`."""


def _v(*valeurs: str) -> tuple[ZoneScore, ...]:
    """Raccourci : construit un tuple de `ZoneScore` à partir de libellés (« 10 », « M »)."""
    return tuple(ZoneScore(valeur) for valeur in valeurs)


def _saisir(serie: Serie, numero: int, valeurs: tuple[ZoneScore, ...], bareme: int) -> Serie:
    """Saisit la volée `numero` sans rien présumer des volées qui la précèdent."""
    return serie.saisir_volee(
        numero,
        valeurs,
        zones_admises=ZONES_SIMPLE,
        nb_fleches_par_volee=len(valeurs),
        nb_volees_bareme=bareme,
    )


def _serie(nb_volees: int, valeurs: tuple[ZoneScore, ...], *, bareme: int | None = None) -> Serie:
    """Une série de `nb_volees` volées identiques, saisies dans l'ordre, rien de validé."""
    total = bareme if bareme is not None else nb_volees
    serie = Serie.vide(tournoi_id=1, phase_id=_PHASE, archer_id=7)
    for numero in range(1, nb_volees + 1):
        serie = _saisir(serie, numero, valeurs, total)
    return serie


# --- Ce que l'annulation rouvre : le lot, et lui seul ---------------------------------------


def test_annuler_rouvre_toutes_les_volees_du_meme_lot() -> None:
    """CA « annuler rouvre LE LOT » : le bloc validé ensemble se rouvre ensemble."""
    serie = _serie(2, _v("10", "9", "8"), bareme=4).valider(
        "MARTIN", grain=GrainValidation.toutes_les_n_volees(2), nb_volees_bareme=4
    )

    serie = serie.annuler_validation(1, par="MARTIN")

    assert [v.en_correction for v in serie.volees] == [True, True]


def test_annuler_ne_rouvre_pas_les_autres_lots() -> None:
    """CA « annuler rouvre LE LOT » : un second lot validé à part n'est pas emporté."""
    serie = _serie(4, _v("10", "9", "8"))
    grain = GrainValidation.toutes_les_n_volees(2)
    serie = serie.valider("MARTIN", grain=grain, nb_volees_bareme=4)
    serie = serie.valider("DURAND", grain=grain, nb_volees_bareme=4)

    serie = serie.annuler_validation(3, par="MARTIN")

    assert [v.en_correction for v in serie.volees] == [False, False, True, True]


def test_annuler_rouvre_un_lot_non_contigu() -> None:
    """CA « annuler rouvre LE LOT » — le cas qui interdit de recalculer le lot par le rang.

    Rien n'impose de saisir dans l'ordre : les volées 1 et 3 valent un lot de deux, et la volée 2
    saisie ensuite n'en fait **pas** partie. Une tranche `(n-1) // N` emporterait 1 et 2.
    """
    serie = Serie.vide(tournoi_id=1, phase_id=_PHASE, archer_id=7)
    serie = _saisir(serie, 1, _v("10", "9", "8"), 4)
    serie = _saisir(serie, 3, _v("10", "9", "8"), 4)
    serie = serie.valider(
        "MARTIN", grain=GrainValidation.toutes_les_n_volees(2), nb_volees_bareme=4
    )
    serie = _saisir(serie, 2, _v("7", "7", "7"), 4)

    serie = serie.annuler_validation(3, par="MARTIN")

    rouvertes = {v.numero for v in serie.volees if v.en_correction}
    assert rouvertes == {1, 3}


# --- Ce que l'annulation NE touche pas : les totaux et les trois gardes ----------------------


def test_la_volee_rouverte_reste_comptee_dans_tous_les_totaux() -> None:
    """CA « la volée rouverte RESTE COMPTÉE » — la preuve, en une assertion par lecteur.

    `cumul` porte le classement, `compter` son départage, `nb_fleches_validees` les trois gardes
    (changement de catégorie, impact de replacement, complétude) et `est_complete` la clôture du
    créneau. Aucun ne doit bouger pendant qu'une volée est en correction.
    """
    serie = _serie(2, _v("10", "9", "8")).valider(
        "MARTIN", grain=GrainValidation.fin_de_serie(), nb_volees_bareme=2
    )
    avant = (serie.cumul, serie.compter(ZoneScore.DIX), serie.nb_fleches_validees)

    rouverte = serie.annuler_validation(1, par="MARTIN")

    assert (rouverte.cumul, rouverte.compter(ZoneScore.DIX), rouverte.nb_fleches_validees) == avant
    assert rouverte.est_complete(2) is True


# --- Ce que l'annulation ouvre : la ressaisie, sans perdre le compte -------------------------


def test_la_volee_rouverte_se_ressaisit_par_le_poste() -> None:
    """CA « elle rouvre la volée à l'écriture » : la tablette ressaisit, la volée est ouverte."""
    serie = _serie(1, _v("10", "9", "8")).valider(
        "MARTIN", grain=GrainValidation.fin_de_serie(), nb_volees_bareme=1
    )

    serie = serie.annuler_validation(1, par="MARTIN")
    serie = _saisir(serie, 1, _v("6", "6", "6"), 1)

    volee = serie.volee(1)
    assert volee is not None
    assert volee.valeurs == _v("6", "6", "6")


def test_la_ressaisie_preserve_la_validation_et_met_le_total_a_jour() -> None:
    """CA « la ressaisie ne doit pas faire sortir la volée du compte non plus ».

    `saisir_volee` reconstruit une `Volee` neuve : sans préservation explicite, la ressaisie
    effacerait `validee_par` et l'arbitrage serait perdu à l'endroit même où il sert.
    """
    serie = _serie(1, _v("10", "9", "8")).valider(
        "MARTIN", grain=GrainValidation.fin_de_serie(), nb_volees_bareme=1
    )

    serie = serie.annuler_validation(1, par="MARTIN")
    serie = _saisir(serie, 1, _v("6", "6", "6"), 1)

    volee = serie.volee(1)
    assert volee is not None
    assert volee.validee_par == "MARTIN"
    assert volee.en_correction is True
    assert serie.cumul == 18


def test_revalider_referme_la_correction_dans_un_nouveau_lot() -> None:
    """CA « annuler, corriger, revalider » : la revalidation clôt la fenêtre ouverte."""
    serie = _serie(1, _v("10", "9", "8")).valider(
        "MARTIN", grain=GrainValidation.fin_de_serie(), nb_volees_bareme=1
    )
    initiale = serie.volee(1)
    assert initiale is not None

    serie = serie.annuler_validation(1, par="MARTIN")
    serie = _saisir(serie, 1, _v("6", "6", "6"), 1)
    serie = serie.refermer_correction(1, par="DURAND")

    volee = serie.volee(1)
    assert volee is not None
    assert volee.en_correction is False
    assert volee.verrouillee is True
    assert volee.validee_par == "DURAND"
    assert volee.lot_validation != initiale.lot_validation


# --- Ce que l'annulation refuse -------------------------------------------------------------


def test_annuler_une_volee_jamais_validee_est_refuse() -> None:
    """CA « annuler une validation » : sans validation, il n'y a rien à annuler."""
    serie = _serie(1, _v("10", "9", "8"))

    with pytest.raises(VoleeNonVerrouillee):
        serie.annuler_validation(1, par="MARTIN")


def test_annuler_deux_fois_la_meme_validation_est_refuse() -> None:
    """CA « annuler une validation » : une volée déjà rouverte n'a plus de validation à annuler."""
    serie = _serie(1, _v("10", "9", "8")).valider(
        "MARTIN", grain=GrainValidation.fin_de_serie(), nb_volees_bareme=1
    )
    serie = serie.annuler_validation(1, par="MARTIN")

    with pytest.raises(VoleeNonVerrouillee):
        serie.annuler_validation(1, par="MARTIN")


def test_annuler_une_volee_inexistante_est_refuse() -> None:
    """CA « annuler une validation » : annuler n'est pas créer."""
    serie = _serie(1, _v("10", "9", "8")).valider(
        "MARTIN", grain=GrainValidation.fin_de_serie(), nb_volees_bareme=1
    )

    with pytest.raises(VoleeIntrouvable):
        serie.annuler_validation(9, par="MARTIN")


def test_annuler_porte_le_nom_de_qui_annule() -> None:
    """CA « tracé à l'audit » : l'acte porte un intervenant, comme validation et correction."""
    serie = _serie(1, _v("10", "9", "8")).valider(
        "MARTIN", grain=GrainValidation.fin_de_serie(), nb_volees_bareme=1
    )

    serie = serie.annuler_validation(1, par="  DURAND  ")

    volee = serie.volee(1)
    assert volee is not None
    assert volee.correction_ouverte_par == "DURAND"


def test_annuler_sans_nom_est_refuse() -> None:
    """CA « tracé à l'audit » : une trace anonyme ne trace rien."""
    serie = _serie(1, _v("10", "9", "8")).valider(
        "MARTIN", grain=GrainValidation.fin_de_serie(), nb_volees_bareme=1
    )

    with pytest.raises(NomIntervenantInvalide):
        serie.annuler_validation(1, par="   ")


# --- Ce que l'annulation ne remplace pas ----------------------------------------------------


def test_corriger_une_volee_validee_reste_possible() -> None:
    """CA « `corriger_volee` est CONSERVÉ » : l'annulation s'ajoute, elle ne se substitue à rien."""
    serie = _serie(1, _v("10", "9", "8")).valider(
        "MARTIN", grain=GrainValidation.fin_de_serie(), nb_volees_bareme=1
    )

    serie = serie.corriger_volee(
        1,
        _v("6", "6", "6"),
        par="DURAND",
        zones_admises=ZONES_SIMPLE,
        nb_fleches_par_volee=3,
        role_de_saisie=Role.SCOREUR,
    )

    volee = serie.volee(1)
    assert volee is not None
    assert serie.cumul == 18
    assert volee.verrouillee is True


def test_corriger_une_volee_en_correction_reste_possible() -> None:
    """⚠️ **Oracle RETOURNÉ en 2ᵉ passe** — il disait « les deux chemins ne se croisent pas ».

    Ils se croisent, et il le faut : c'est le **seul** recours quand une pause tombe entre
    l'annulation et la ressaisie. `saisir_volee` et `valider` portent `refuser_si_en_pause`, donc
    sans ce chemin la volée rouverte attendait la relance sans qu'aucun geste puisse la réparer —
    alors que la docstring, l'ADR et la recette promettaient toutes trois « on y répare par
    `corriger_volee` ». L'arbitrage du commanditaire (E05US033 : « la pause gèle ce qui *avance*,
    jamais ce qui *répare* ») primait sur le CA dérivé que j'avais écrit.

    ⚠️ **Corriger ne referme PAS la correction** : la volée reste rouverte, c'est le scoreur qui
    referme en revalidant. Sinon une correction faite en pause ferait, elle, avancer le tour.
    """
    serie = _serie(1, _v("10", "9", "8")).valider(
        "MARTIN", grain=GrainValidation.fin_de_serie(), nb_volees_bareme=1
    )
    serie = serie.annuler_validation(1, par="MARTIN")

    serie = serie.corriger_volee(
        1,
        _v("6", "6", "6"),
        par="DURAND",
        zones_admises=ZONES_SIMPLE,
        nb_fleches_par_volee=3,
        role_de_saisie=Role.SCOREUR,
    )

    volee = serie.volee(1)
    assert volee is not None
    assert volee.valeurs == _v("6", "6", "6")
    assert volee.en_correction is True, "la fenêtre reste ouverte : revalider est l'acte du scoreur"
    assert serie.cumul == 18


def test_corriger_une_volee_jamais_validee_reste_refuse() -> None:
    """La moitié qui ne bouge pas : sans validation, il n'y a rien à corriger — on saisit."""
    serie = _serie(1, _v("10", "9", "8"))

    with pytest.raises(VoleeNonVerrouillee):
        serie.corriger_volee(
            1,
            _v("6", "6", "6"),
            par="DURAND",
            zones_admises=ZONES_SIMPLE,
            nb_fleches_par_volee=3,
            role_de_saisie=Role.SCOREUR,
        )


# --- Refermer une correction est un ACTE : un lot par geste (bloquant de revue) --------------


def test_revalider_ne_referme_qu_un_lot_a_la_fois() -> None:
    """Miroir exact de `test_annuler_ne_rouvre_pas_les_autres_lots`, au retour.

    ⚠️ **Bloquant de revue, sondé à l'exécution.** Une première rédaction refermait *toutes* les
    corrections de la feuille : deux lots annulés séparément — par deux personnes, pour deux motifs
    — se retrouvaient re-signés d'un seul clic. Les volées **jamais ressaisies** redevenaient
    « valides » avec leurs valeurs fausses, perdaient leur marqueur à l'écran, et changeaient de
    validateur au profit de qui avait cliqué. Les deux lots fusionnaient ensuite en un seul, si
    bien qu'une annulation ultérieure en rouvrait six au lieu de trois.
    """
    serie = _serie(4, _v("10", "9", "8"))
    grain = GrainValidation.toutes_les_n_volees(2)
    serie = serie.valider("MARTIN", grain=grain, nb_volees_bareme=4)
    serie = serie.valider("DURAND", grain=grain, nb_volees_bareme=4)
    serie = serie.annuler_validation(1, par="MARTIN")
    serie = serie.annuler_validation(3, par="ARBITRE")
    # ⚠️ Le marqueur ne ressaisit QUE le second lot : c'est le décor qui a démasqué les deux
    # rédactions devinettes. Refermer doit viser **ce** lot, pas « le plus ancien ».
    serie = _saisir(serie, 3, _v("7", "7", "7"), 4)
    serie = _saisir(serie, 4, _v("7", "7", "7"), 4)

    serie = serie.refermer_correction(3, par="ARBITRE")

    assert [v.en_correction for v in serie.volees] == [True, True, False, False]
    assert [v.validee_par for v in serie.volees] == ["MARTIN", "MARTIN", "ARBITRE", "ARBITRE"]


def test_deux_lots_refermes_restent_deux_lots() -> None:
    """La conséquence durable du bloquant : le lot est l'identité d'un acte, il ne fusionne pas.

    Sans cela, `annuler_validation` sur l'une des six volées les rouvrirait toutes — le lot
    cesserait de nommer « ce qu'un même acte a verrouillé », qui est le fondement d'ADR-0109.
    """
    serie = _serie(4, _v("10", "9", "8"))
    grain = GrainValidation.toutes_les_n_volees(2)
    serie = serie.valider("MARTIN", grain=grain, nb_volees_bareme=4)
    serie = serie.valider("DURAND", grain=grain, nb_volees_bareme=4)
    serie = serie.annuler_validation(1, par="MARTIN").annuler_validation(3, par="MARTIN")
    serie = serie.refermer_correction(1, par="MARTIN")
    serie = serie.refermer_correction(3, par="MARTIN")

    serie = serie.annuler_validation(1, par="MARTIN")

    assert {v.numero for v in serie.volees if v.en_correction} == {1, 2}


def test_refermer_une_correction_ne_valide_pas_le_lot_en_attente() -> None:
    """Le geste referme la correction **et elle seule** : les volées neuves attendent leur tour.

    C'est le prix assumé de la priorité (ADR-0109 § Décision 4). L'écran doit donc distinguer les
    deux gestes — sans ce test, la propriété n'est écrite nulle part.
    """
    serie = _serie(2, _v("10", "9", "8"), bareme=4)
    grain = GrainValidation.toutes_les_n_volees(2)
    serie = serie.valider("MARTIN", grain=grain, nb_volees_bareme=4)
    serie = serie.annuler_validation(1, par="MARTIN")
    serie = _saisir(serie, 3, _v("7", "7", "7"), 4)
    serie = _saisir(serie, 4, _v("7", "7", "7"), 4)

    with pytest.raises(CorrectionOuverte):
        serie.valider("MARTIN", grain=grain, nb_volees_bareme=4)

    serie = serie.refermer_correction(1, par="MARTIN")
    # ⚠️ L'assertion qui porte le nom du test : refermer **n'a pas** validé 3 et 4 au passage.
    assert [v.validee_par for v in serie.volees] == ["MARTIN", "MARTIN", None, None]

    serie = serie.valider("MARTIN", grain=grain, nb_volees_bareme=4)
    assert [v.validee_par for v in serie.volees] == ["MARTIN", "MARTIN", "MARTIN", "MARTIN"]


def test_un_lot_repris_d_une_seule_volee_se_revalide_hors_grain() -> None:
    """Le cas par défaut des bases migrées : la reprise 0054 donne **un lot par volée**.

    Sous un grain « toutes les 2 » sur une série incomplète, appliquer le grain à la refermeture
    rendrait `RienAValider` — le lot rouvert resterait ouvert jusqu'à ce que deux volées se
    libèrent. C'est le cas qui a motivé la clause « hors grain », et il n'était joué nulle part.
    """
    reprise = Volee(numero=1, valeurs=_v("10", "9", "8"), validee_par="MARTIN", lot_validation=1)
    serie = replace(_serie(1, _v("10", "9", "8"), bareme=4), volees=(reprise,))
    serie = serie.annuler_validation(1, par="MARTIN")

    serie = serie.refermer_correction(1, par="MARTIN")

    volee = serie.volee(1)
    assert volee is not None
    assert volee.en_correction is False and volee.verrouillee is True


def test_un_acte_ne_prend_jamais_le_rang_d_une_volee_reprise() -> None:
    """Les deux conventions de lot partagent un espace de valeurs — elles doivent rester disjointes.

    ⚠️ **L'ORDRE de ce décor est tout le test**, et une première rédaction l'avait à l'envers : la
    reprise y précédait l'acte, si bien que les deux formules de rang donnaient le même résultat et
    que le test passait **aussi sans le correctif** (placebo relevé en 3ᵉ passe de revue).

    Ici la reprise arrive **après** l'acte — ce que ferait un import de feuilles papier ou un script
    de reprise sur une série déjà jouée. Sans la borne, l'acte sur la volée 5 reçoit le rang **1**
    (aucun lot n'existe encore dans la série), la reprise n° 1 se normalise en lot **1** elle aussi,
    et annuler l'une rouvre l'autre — deux volées que personne n'a jamais validées ensemble.
    """
    serie = Serie.vide(tournoi_id=1, phase_id=_PHASE, archer_id=7)
    serie = _saisir(serie, 5, _v("10", "9", "8"), 5)
    serie = serie.valider(
        "MARTIN", grain=GrainValidation.toutes_les_n_volees(1), nb_volees_bareme=5
    )
    reprise = Volee(numero=1, valeurs=_v("7", "7", "7"), validee_par="ANCIEN")
    serie = replace(serie, volees=tuple(sorted((*serie.volees, reprise), key=lambda v: v.numero)))

    serie = serie.annuler_validation(1, par="MARTIN")

    assert {v.numero for v in serie.volees if v.en_correction} == {1}


# --- L'invariant « validée ⇔ lot », des deux côtés -------------------------------------------


def test_une_volee_validee_sans_lot_devient_son_propre_lot() -> None:
    """La reprise de la migration 0054, portée par le domaine pour valoir partout."""
    volee = Volee(numero=3, valeurs=_v("10", "9", "8"), validee_par="MARTIN")

    assert volee.lot_validation == 3


def test_un_lot_sans_validateur_est_refuse() -> None:
    """L'incohérence inverse n'a aucune lecture sensée : elle signale un producteur fautif."""
    with pytest.raises(IncoherenceVolee):
        Volee(numero=1, valeurs=_v("10", "9", "8"), lot_validation=1)


def test_une_correction_sans_validation_est_refusee() -> None:
    """Sans cette garde, une volée jamais validée pouvait porter `en_correction`.

    Elle aurait alors détourné la priorité de `valider` et fait écrire une trace de correction sur
    un score que personne n'a jamais signé (relevé en revue).
    """
    with pytest.raises(IncoherenceVolee):
        Volee(numero=1, valeurs=_v("10", "9", "8"), correction_ouverte_par="MARTIN")
