"""Tests unitaires de l'**effectif minimum d'un format** (E05US021) — domaine pur, sans base.

Écrits **depuis le CA** de `stories/E05-moteur-phases.md` (règle 9), avant l'implémentation. Les
puces couvertes, dans l'ordre :

- « **effectif minimum déduit** » — l'application dérive des prélèvements le nombre d'inscrits en
  dessous duquel le format ne peut pas se dérouler ; « les rangs 33 et suivants » exige 34 classés
  pour produire un tableau de 2 ;
- « **minimum exigé, facultatif** » — un format peut exiger davantage que son minimum technique,
  jamais moins ; l'énoncer plus bas rend le format inapplicable ;
- « **visible à la composition** » — la projection annonce le minimum, effectif simulé ou non ;
- « **portée du calcul** » — un rang se lit dans le classement de sa phase source : seuls les
  prélèvements visant la **première** phase se traduisent en nombre d'inscrits.

Le raisonnement du chiffre, une fois pour toutes : une phase en tableau a besoin de **deux**
participants ; un prélèvement « à partir du rang d » n'en a deux que lorsque la phase source en
classe `d + 1`. D'où `d - 1 + 2` inscrits, soit 34 pour d = 33.
"""

from __future__ import annotations

import pytest

from domain.anomalie import Anomalie, Gravite
from domain.bareme import BaremeQualification
from domain.deroule import effectif_minimum, projeter
from domain.erreurs import EffectifMinimumIncoherent, ExigenceEffectifInvalide
from domain.format_tournoi import FormatTournoi, ModelePhase
from domain.phase import IssueTour, SourcePhase, TypePhase


def _qualification(ordre: int = 1) -> ModelePhase:
    return ModelePhase.qualification(BaremeQualification.preset_ffta_18m(), ordre=ordre)


def _tableau(ordre: int, *sources: SourcePhase) -> ModelePhase:
    return ModelePhase(ordre=ordre, type=TypePhase.ELIMINATION_DIRECTE, sources=tuple(sources))


def _echauffement(ordre: int) -> ModelePhase:
    return ModelePhase(ordre=ordre, type=TypePhase.ECHAUFFEMENT)


def _codes(anomalies: tuple[Anomalie, ...]) -> list[str]:
    return [anomalie.code for anomalie in anomalies]


# --- CA « effectif minimum déduit » --------------------------------------------------------------


def test_une_qualification_seule_nexige_quun_archer() -> None:
    """Rien dans une qualification ne réclame un effectif : elle accueille qui se présente."""
    assert effectif_minimum([_qualification()]) == 1


def test_un_tableau_exige_deux_archers_pour_avoir_un_duel() -> None:
    assert effectif_minimum([_qualification(), _tableau(2, SourcePhase.par_rangs(1, 1, 32))]) == 2


def test_les_rangs_33_et_suivants_exigent_34_inscrits() -> None:
    """L'exemple même du CA — un tableau de 2 ne se monte qu'à partir du 34ᵉ classé."""
    etapes = [_qualification(), _tableau(2, SourcePhase.par_rangs(1, rang_debut=33))]

    assert effectif_minimum(etapes) == 34


def test_une_plage_fermee_haute_exige_autant_quune_plage_ouverte() -> None:
    """« Les rangs 33 à 64 » ne prend deux archers qu'au 34ᵉ, comme « 33 et suivants »."""
    etapes = [_qualification(), _tableau(2, SourcePhase.par_rangs(1, 33, 64))]

    assert effectif_minimum(etapes) == 34


def test_cest_la_phase_la_plus_exigeante_qui_fixe_le_minimum() -> None:
    """Le déroulé d'ADR-0068 : un tableau principal 1-32, un classement « 33 et suivants »."""
    etapes = [
        _qualification(),
        _tableau(2, SourcePhase.par_rangs(1, 1, 32)),
        _tableau(3, SourcePhase.par_rangs(1, rang_debut=33)),
    ]

    assert effectif_minimum(etapes) == 34


def test_plusieurs_prelevements_sur_une_phase_se_cumulent_donc_le_plus_bas_decide() -> None:
    """Une phase nourrie par « 1 à 8 » **et** « 33 à 40 » a ses deux archers dès le 2ᵉ inscrit."""
    etapes = [
        _qualification(),
        _tableau(2, SourcePhase.par_rangs(1, 1, 8), SourcePhase.par_rangs(1, 33, 40)),
    ]

    assert effectif_minimum(etapes) == 2


def test_un_format_sans_etape_nexige_rien() -> None:
    assert effectif_minimum([]) == 1


# --- Notes « portée du calcul » : un rang se lit dans sa phase source ----------------------------


def test_un_prelevement_par_issue_de_tour_ne_fixe_aucun_minimum() -> None:
    """« Les perdants du tour 2 » ne se traduit pas en nombre d'inscrits — le déroulé en décide.

    Le plancher **structurel** subsiste : un tableau reste un tableau, il lui faut deux tireurs.
    """
    etapes = [
        _qualification(),
        _tableau(2, SourcePhase.par_rangs(1, 1, 32)),
        _tableau(3, SourcePhase.par_issue_de_tour(2, tour=2, issue=IssueTour.PERDANTS)),
    ]

    assert effectif_minimum(etapes) == 2


def test_le_reste_ne_chiffre_rien_mais_un_tableau_reste_un_tableau() -> None:
    """« Le reste » ne dit pas *combien* d'inscrits il faut, mais la phase qu'il alimente **oppose**
    toujours deux tireurs — le plancher structurel ne se perd pas en route.

    ⚠️ Un premier jet rendait `1` ici, et son test l'entérinait : à 1 inscrit, le moteur levait
    `EffectifTableauInvalide` **en salle**, soit le défaut même que l'US retire.
    """
    etapes = [_qualification(), _tableau(2, SourcePhase.le_reste(1))]

    assert effectif_minimum(etapes) == 2


def test_un_prelevement_dans_une_phase_intermediaire_ne_se_lit_pas_en_inscrits() -> None:
    """Le rang 33 **du tableau** n'est pas le 33ᵉ inscrit : ce cas relève du diagnostic, pas du
    minimum. L'annoncer comme un besoin de 34 inscrits serait annoncer un chiffre faux."""
    etapes = [
        _qualification(),
        _tableau(2, SourcePhase.par_rangs(1, 1, 32)),
        _tableau(3, SourcePhase.par_rangs(2, rang_debut=33)),
    ]

    assert effectif_minimum(etapes) == 2


# --- Le classement traduisible est celui de la QUALIFICATION, pas celui de la première phase -----
# L'oracle de cette section est le **moteur** : `ServiceSaisieDuels._ordre_de_la_qualification`
# n'honore un prélèvement que s'il vise la phase de type `qualification`. Un plancher qui viserait
# autre chose mentirait — et il a menti dans les deux sens avant d'être corrigé.


def test_un_echauffement_en_tete_ne_desactive_pas_le_controle() -> None:
    """Le déroulé d'ADR-0068, précédé d'un échauffement : le plancher ne bouge pas d'un cran.

    ⚠️ Le défaut que ce test verrouille était **bloquant** : viser la première phase au lieu de la
    qualification rendait un plancher de 1, l'écran n'affichait rien, le tournoi démarrait, et la
    consolante cassait sur la tablette. `echauffement` est l'un des types offerts par l'écran de
    composition — le déroulé n'a rien d'exotique.
    """
    etapes = [
        _echauffement(1),
        _qualification(ordre=2),
        _tableau(3, SourcePhase.par_rangs(2, 1, 32)),
        _tableau(4, SourcePhase.par_rangs(2, rang_debut=33)),
    ]

    assert effectif_minimum(etapes) == 34


def test_sans_qualification_aucun_rang_ne_se_traduit_en_inscrits() -> None:
    """Sans classement à lire, le moteur ensemence avec **tous** les archers en lice : réclamer le
    rang de départ serait un refus abusif le jour J.

    Il reste le plancher structurel — deux tireurs pour un tableau.
    """
    etapes = [
        _tableau(1),
        ModelePhase(
            ordre=2, type=TypePhase.PLACEMENT, sources=(SourcePhase.par_rangs(1, rang_debut=33),)
        ),
    ]

    assert effectif_minimum(etapes) == 2


def test_une_phase_sans_opposition_se_contente_dun_participant() -> None:
    """Qualification et échauffement font tirer l'archer **seul** ; les six autres opposent."""
    assert effectif_minimum([_echauffement(1)]) == 1
    assert effectif_minimum([_qualification()]) == 1


@pytest.mark.parametrize(
    "type_a_duels",
    [
        TypePhase.ELIMINATION_DIRECTE,
        TypePhase.PLACEMENT,
        TypePhase.POULES,
        TypePhase.SUISSE,
        TypePhase.COLLINE,
        TypePhase.BIG_SHOOT_OFF,
        TypePhase.BARRAGE,
    ],
)
def test_tout_type_qui_oppose_des_tireurs_en_exige_deux(type_a_duels: TypePhase) -> None:
    """« Les rangs 33 et suivants » vers une poule exige 34 inscrits, comme vers un tableau.

    Le plancher tient à ce que la phase **oppose** des tireurs, pas à sa structure d'arbre : un
    premier jet ne comptait que les deux types en tableau et minorait les cinq autres d'un cran.
    """
    etapes = [
        _qualification(),
        ModelePhase(ordre=2, type=type_a_duels, sources=(SourcePhase.par_rangs(1, rang_debut=33),)),
    ]

    assert effectif_minimum(etapes) == 34


def test_une_phase_sans_prelevement_est_peuplee_par_les_inscrits() -> None:
    """Une phase en tableau que rien n'alimente reçoit tout le monde (`# DETTE-028`) : deux archers
    lui suffisent, mais il en faut deux."""
    assert effectif_minimum([_tableau(1)]) == 2


# --- CA « minimum exigé, facultatif » ------------------------------------------------------------


def test_un_format_peut_exiger_plus_que_son_minimum_technique() -> None:
    """« Pas de tournoi de ce type sous 40 archers » — une règle de club, au-dessus du déduit."""
    format_tournoi = FormatTournoi.creer(
        "Salle 120",
        [_qualification(), _tableau(2, SourcePhase.par_rangs(1, rang_debut=33))],
        effectif_minimum_exige=40,
    )

    assert format_tournoi.effectif_minimum == 40


def test_sans_exigence_le_minimum_du_format_est_celui_quil_deduit() -> None:
    format_tournoi = FormatTournoi.creer(
        "Salle 120", [_qualification(), _tableau(2, SourcePhase.par_rangs(1, rang_debut=33))]
    )

    assert format_tournoi.effectif_minimum == 34
    assert format_tournoi.anomalies() == ()


def test_exiger_exactement_le_minimum_deduit_est_licite() -> None:
    format_tournoi = FormatTournoi.creer(
        "Salle 120",
        [_qualification(), _tableau(2, SourcePhase.par_rangs(1, rang_debut=33))],
        effectif_minimum_exige=34,
    )

    assert format_tournoi.effectif_minimum == 34
    assert format_tournoi.anomalies() == ()


def test_exiger_moins_que_le_minimum_deduit_rend_le_format_inapplicable() -> None:
    """Un chiffre saisi sous le plancher technique est un mensonge : il laisserait lancer un tournoi
    que le moteur ne saura pas dérouler — le défaut même que l'US corrige."""
    format_tournoi = FormatTournoi.creer(
        "Salle 120",
        [_qualification(), _tableau(2, SourcePhase.par_rangs(1, rang_debut=33))],
        effectif_minimum_exige=20,
    )

    anomalies = format_tournoi.anomalies()

    assert _codes(anomalies) == ["effectif_minimum_incoherent"]
    assert anomalies[0].gravite is Gravite.BLOQUANTE
    assert not format_tournoi.projeter().est_applicable


def test_un_format_au_minimum_incoherent_refuse_de_sappliquer() -> None:
    format_tournoi = FormatTournoi.creer(
        "Salle 120",
        [_qualification(), _tableau(2, SourcePhase.par_rangs(1, rang_debut=33))],
        effectif_minimum_exige=20,
    )

    with pytest.raises(EffectifMinimumIncoherent):
        format_tournoi.appliquer(tournoi_id=1)


@pytest.mark.parametrize("absurde", [0, -1])
def test_une_exigence_absurde_est_refusee_des_la_saisie(absurde: int) -> None:
    """Zéro ou négatif ne veut rien dire : « aucune exigence » se dit en ne réglant rien."""
    with pytest.raises(ExigenceEffectifInvalide):
        FormatTournoi.creer("Salle 120", [_qualification()], effectif_minimum_exige=absurde)


# --- CA « visible à la composition » -------------------------------------------------------------


def test_la_projection_annonce_le_minimum_sans_effectif_simule() -> None:
    """Le minimum est une propriété du **format**, pas de l'effectif : il s'affiche d'emblée."""
    format_tournoi = FormatTournoi.creer(
        "Salle 120", [_qualification(), _tableau(2, SourcePhase.par_rangs(1, rang_debut=33))]
    )

    assert format_tournoi.projeter().effectif_minimum == 34


def test_la_projection_annonce_le_minimum_avec_un_effectif_simule() -> None:
    format_tournoi = FormatTournoi.creer(
        "Salle 120", [_qualification(), _tableau(2, SourcePhase.par_rangs(1, rang_debut=33))]
    )

    assert format_tournoi.projeter(effectif=28).effectif_minimum == 34


def test_la_projection_dun_format_exigeant_annonce_lexigence() -> None:
    format_tournoi = FormatTournoi.creer(
        "Salle 120",
        [_qualification(), _tableau(2, SourcePhase.par_rangs(1, rang_debut=33))],
        effectif_minimum_exige=40,
    )

    assert format_tournoi.projeter(effectif=28).effectif_minimum == 40


def test_la_projection_generique_annonce_le_minimum_deduit() -> None:
    """`projeter` ne connaît que des étapes : il annonce le déduit, que le format relève ensuite."""
    projection = projeter([_qualification(), _tableau(2, SourcePhase.par_rangs(1, rang_debut=33))])

    assert projection.effectif_minimum == 34
