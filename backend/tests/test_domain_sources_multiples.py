"""Sources multiples & plages relatives d'une phase (E05US010) — tests écrits **depuis le CA**.

Règle 9 : dérivés des CA « sources multiples », « plages relatives » et « cohérence des sources »
de `stories/E05-moteur-phases.md` § E05US010, dont deux sont des demandes du commanditaire citées
mot pour mot dans la story. Écrits avant l'implémentation.

Le CA qui commande tout : *« il faut que la phase et le format du tournoi soient capables de
s'ajuster si j'ai prévu 120 archers et qu'il n'y en a que 82 »*. Un format n'est donc pas une liste
de rangs figée : il décrit des **prélèvements relatifs** à l'effectif réel.
"""

from __future__ import annotations

import pytest

from domain.bareme import BaremeQualification
from domain.erreurs import (
    EffectifIncompatible,
    PlageSourceVide,
    RangSourceInvalide,
    RangsSourceInexistants,
    SourceApresPhase,
    SourceIntrouvable,
    SourceMalFormee,
    SourcesQuiSeRecoupent,
)
from domain.phase import (
    IssueTour,
    NatureSource,
    Phase,
    SequencePhases,
    SourcePhase,
    TypePhase,
)
from domain.tournoi import TournoiId

TOURNOI = TournoiId(1)


def _qualification(effectif: int | None = None) -> Phase:
    """La phase de qualification (ordre 1), source usuelle des tableaux."""
    phase = Phase.qualification(TOURNOI, bareme=BaremeQualification.preset_ffta_18m())
    return phase.avec_effectif(effectif)


def _tableau(ordre: int, sources: tuple[SourcePhase, ...], effectif: int | None = None) -> Phase:
    return Phase.creer(
        TOURNOI, ordre, TypePhase.ELIMINATION_DIRECTE, sources=sources, effectif=effectif
    )


# --- CA « sources multiples » : plusieurs sources, de natures différentes ------------------------


def test_une_phase_se_peuple_de_plusieurs_sources_de_natures_differentes() -> None:
    """L'exemple du commanditaire : « les demi-finalistes du tableau principal, et le gagnant du
    tableau secondaire »."""
    demi_finalistes = SourcePhase.par_issue_de_tour(
        ordre_source=2, tour=3, issue=IssueTour.PERDANTS
    )
    vainqueur_secondaire = SourcePhase.par_rangs(ordre_source=3, rang_debut=1, rang_fin=1)
    phase = _tableau(4, (demi_finalistes, vainqueur_secondaire))
    assert len(phase.sources) == 2
    assert {s.nature for s in phase.sources} == {NatureSource.ISSUE_DE_TOUR, NatureSource.RANGS}


def test_une_source_peut_prelever_les_gagnants_d_un_tour() -> None:
    """CA « peuplement gagnants/perdants » : « gagnants du tour X » / « perdants du tour X »."""
    source = SourcePhase.par_issue_de_tour(ordre_source=1, tour=2, issue=IssueTour.GAGNANTS)
    assert source.nature is NatureSource.ISSUE_DE_TOUR
    assert (source.tour, source.issue) == (2, IssueTour.GAGNANTS)


def test_une_source_par_rangs_reste_la_forme_par_defaut() -> None:
    """CA « peuplement par rangs » (E05US001) : « rangs N→M » d'un classement source, inchangé."""
    source = SourcePhase(ordre_source=1, rang_debut=1, rang_fin=32)
    assert source.nature is NatureSource.RANGS
    assert source.effectif_selectionne == 32


def test_une_phase_sans_source_reste_licite() -> None:
    """La première phase d'une séquence est alimentée par les inscriptions, pas par une phase."""
    assert _qualification().sources == ()


# --- CA « plages relatives » : fin ouverte et « le reste » --------------------------------------


def test_une_plage_a_fin_ouverte_ne_declare_pas_son_dernier_rang() -> None:
    """« les rangs 33 et suivants » : la fin dépend de l'effectif réel, pas du format."""
    source = SourcePhase.par_rangs(ordre_source=1, rang_debut=33, rang_fin=None)
    assert source.rang_fin is None
    assert source.effectif_selectionne is None  # indéterminé tant que l'effectif n'est pas connu


def test_une_plage_a_fin_ouverte_se_resout_sur_l_effectif_reel() -> None:
    """« les rangs 33 à 120 » serait faux à 82 inscrits ; « 33 et suivants » tient dans les deux."""
    source = SourcePhase.par_rangs(ordre_source=1, rang_debut=33, rang_fin=None)
    assert source.resoudre(effectif_source=120) == 88
    assert source.resoudre(effectif_source=82) == 50


def test_le_reste_prend_ce_qu_aucune_autre_source_n_a_preleve() -> None:
    """Le vocabulaire « le reste » du CA : un prélèvement défini par complément."""
    source = SourcePhase.le_reste(ordre_source=1)
    assert source.nature is NatureSource.RESTE
    assert source.effectif_selectionne is None


def test_un_format_prevu_pour_120_tient_a_82_inscrits() -> None:
    """Le CA fondateur, vérifié de bout en bout : la même séquence vaut pour deux effectifs."""
    sources = (
        SourcePhase.par_rangs(ordre_source=1, rang_debut=1, rang_fin=32),
        SourcePhase.le_reste(ordre_source=1),
    )
    for effectif in (120, 82):
        qualif = _qualification(effectif=effectif)
        tableau = _tableau(2, sources, effectif=effectif)
        SequencePhases((qualif, tableau))  # ne lève pas : le format s'ajuste


def test_un_format_fige_sur_120_devient_faux_a_82() -> None:
    """Contrôle négatif : c'est bien la **fin ouverte** qui sauve le format, pas la tolérance."""
    qualif = _qualification(effectif=82)
    tableau = _tableau(2, (SourcePhase(ordre_source=1, rang_debut=33, rang_fin=120),), effectif=88)
    with pytest.raises(RangsSourceInexistants):
        SequencePhases((qualif, tableau))


# --- CA « cohérence des sources » ---------------------------------------------------------------


def test_deux_sources_ne_peuvent_pas_preleve_le_meme_archer() -> None:
    """CA : « deux sources d'une même phase ne se recoupent pas (un archer prélevé deux fois) »."""
    qualif = _qualification(effectif=64)
    tableau = _tableau(
        2,
        (
            SourcePhase(ordre_source=1, rang_debut=1, rang_fin=32),
            SourcePhase(ordre_source=1, rang_debut=16, rang_fin=48),
        ),
    )
    with pytest.raises(SourcesQuiSeRecoupent):
        SequencePhases((qualif, tableau))


def test_deux_plages_jointives_ne_se_recoupent_pas() -> None:
    """[1..32] et [33..64] se touchent sans se chevaucher : c'est le découpage normal."""
    qualif = _qualification(effectif=64)
    tableau = _tableau(
        2,
        (
            SourcePhase(ordre_source=1, rang_debut=1, rang_fin=32),
            SourcePhase(ordre_source=1, rang_debut=33, rang_fin=64),
        ),
        effectif=64,
    )
    SequencePhases((qualif, tableau))


def test_deux_sources_de_phases_differentes_ne_se_recoupent_jamais() -> None:
    """Le recoupement se juge **par phase source** : les rangs 1-4 de deux phases sont 8 archers."""
    qualif = _qualification(effectif=64)
    principal = _tableau(2, (SourcePhase(ordre_source=1, rang_debut=1, rang_fin=32),), effectif=32)
    finale = _tableau(
        3,
        (
            SourcePhase(ordre_source=1, rang_debut=1, rang_fin=2),
            SourcePhase(ordre_source=2, rang_debut=1, rang_fin=2),
        ),
        effectif=4,
    )
    SequencePhases((qualif, principal, finale))


def test_la_somme_des_sources_doit_couvrir_l_effectif_declare() -> None:
    """CA : « leur somme est compatible avec l'effectif déclaré »."""
    qualif = _qualification(effectif=64)
    tableau = _tableau(
        2,
        (
            SourcePhase(ordre_source=1, rang_debut=1, rang_fin=8),
            SourcePhase(ordre_source=1, rang_debut=9, rang_fin=16),
        ),
        effectif=32,
    )
    with pytest.raises(EffectifIncompatible):
        SequencePhases((qualif, tableau))


def test_une_source_a_fin_ouverte_dispense_du_compte_exact() -> None:
    """Avec « le reste », la somme n'est pas calculable au format : le contrôle exact ne s'applique
    pas — c'est tout l'objet des plages relatives."""
    qualif = _qualification(effectif=64)
    tableau = _tableau(
        2,
        (
            SourcePhase(ordre_source=1, rang_debut=1, rang_fin=8),
            SourcePhase.le_reste(ordre_source=1),
        ),
        effectif=32,
    )
    SequencePhases((qualif, tableau))


def test_une_source_designant_une_phase_posterieure_reste_refusee() -> None:
    qualif = _qualification(effectif=64)
    tableau = _tableau(2, (SourcePhase(ordre_source=3, rang_debut=1, rang_fin=8),))
    troisieme = _tableau(3, ())
    with pytest.raises(SourceApresPhase):
        SequencePhases((qualif, tableau, troisieme))


def test_une_source_designant_une_phase_absente_reste_refusee() -> None:
    qualif = _qualification(effectif=64)
    tableau = _tableau(2, (SourcePhase(ordre_source=9, rang_debut=1, rang_fin=8),))
    with pytest.raises(SourceIntrouvable):
        SequencePhases((qualif, tableau))


# --- invariants du value object -----------------------------------------------------------------


def test_un_rang_de_depart_nul_est_refuse() -> None:
    with pytest.raises(RangSourceInvalide):
        SourcePhase(ordre_source=1, rang_debut=0, rang_fin=8)


def test_une_plage_inversee_est_refusee() -> None:
    with pytest.raises(PlageSourceVide):
        SourcePhase(ordre_source=1, rang_debut=8, rang_fin=4)


def test_une_source_par_issue_de_tour_exige_son_tour() -> None:
    """Le tour n'a de sens que pour cette nature — mais il y est **obligatoire** : « les gagnants »
    sans dire de quel tour ne désigne personne."""
    with pytest.raises(SourceMalFormee):
        SourcePhase(ordre_source=1, nature=NatureSource.ISSUE_DE_TOUR, issue=IssueTour.GAGNANTS)


def test_une_source_par_rangs_ne_porte_pas_de_tour() -> None:
    """Contrôle symétrique : un tour sur un prélèvement par rangs est une config incohérente."""
    with pytest.raises(SourceMalFormee):
        SourcePhase(ordre_source=1, rang_debut=1, rang_fin=8, tour=2)
