"""E05US026 — le réglage d'une phase au **système suisse**, posé à l'atelier.

Tests dérivés du **CA** (`stories/E05-moteur-phases.md` → E05US026, puce « réglages à l'atelier ») :
« *nombre de rondes (`ConfigurationSuisse`), avec le maximum que l'effectif autorise affiché en
clair (`rondes_maximales`)* ».

⚠️ **Honnêteté sur l'ordre d'écriture** (règle 9). Ces tests dérivent du CA et de lui seul — c'est
la garantie qui compte —, mais ils ont été écrits **après** le champ, pas avant. L'ordre inverse
aurait été tenu si la puce du CA avait porté une règle métier neuve ; elle n'en porte pas : elle
nomme un réglage et une borne que `domain/suisse.py` calculait déjà depuis E05US015. Le risque que
la règle 9 combat — un test qui décrit l'implémentation au lieu de la règle — se lit ici sur la
**borne**, et c'est précisément là que le CA est explicite. Signalé plutôt que tu.

**Ce que ces tests ferment.** `ConfigurationSuisse` annonce dans sa propre docstring que le nombre
de rondes est « validé contre l'effectif **au démarrage** et non ici ». Ce démarrage-là n'existait
pas : le seul refus vivait dans `apparier_ronde`, c'est-à-dire **en salle**, une fois les rondes
précédentes déjà tirées — moment où l'organisateur n'a plus aucun geste de rattrapage. La borne se
juge donc sur le couple (réglage, effectif), là où l'effectif est déclaré : l'étape de déroulé.
"""

from __future__ import annotations

import pytest

from domain.deroule_etape import EtapeDeroule
from domain.erreurs import ConfigurationSuisseInvalide
from domain.format_tournoi import ModelePhase
from domain.phase import Phase, StatutPhase, TypePhase
from domain.suisse import ConfigurationSuisse, rondes_maximales


def _etape(**champs: object) -> EtapeDeroule:
    """Une étape de système suisse, réglée à 5 rondes sauf mention contraire."""
    defauts: dict[str, object] = {
        "tournoi_id": 1,
        "ordre": 1,
        "type": TypePhase.SUISSE,
        "suisse": ConfigurationSuisse(nb_rondes=5),
    }
    defauts.update(champs)
    return EtapeDeroule(**defauts)  # type: ignore[arg-type]


def test_le_reglage_se_pose_sur_l_etape_et_descend_dans_chaque_creneau() -> None:
    """CA « réglages à l'atelier » : le nombre de rondes voyage de l'étape jusqu'à la phase.

    ⚠️ **Porté par l'étape, donc par le tournoi** (ADR-0076), et non par la phase d'un départ : un
    nombre de rondes est une propriété du *format*, pas de l'avancement d'un créneau. Deux créneaux
    du même tournoi tirent donc le même nombre de rondes — l'inverse serait une divergence de
    définition, exactement ce qu'ADR-0076 a rendu impossible.
    """
    phase = _etape().instancier(depart_id=7)

    assert phase.suisse == ConfigurationSuisse(nb_rondes=5)
    assert phase.statut is StatutPhase.A_VENIR


def test_un_nombre_de_rondes_que_l_effectif_ne_permet_pas_est_refuse_a_la_composition() -> None:
    """CA « avec le maximum que l'effectif autorise » — et le refus tombe **avant** le jour J.

    À 4 participants, chacun n'a que 3 adversaires : une 4ᵉ ronde rejouerait forcément une paire.
    Le refus existait déjà, mais dans `apparier_ronde` — donc à la ronde 4, en salle, les trois
    premières déjà tirées. Le déplacer à la composition est tout l'objet de cette puce du CA.
    """
    with pytest.raises(ConfigurationSuisseInvalide, match="3 rondes au plus"):
        _etape(effectif=4, suisse=ConfigurationSuisse(nb_rondes=4))


def test_a_effectif_impair_le_bye_paie_un_tour_de_plus() -> None:
    """5 archers autorisent **5** rondes, pas 4 — et l'écart n'est pas cosmétique.

    À effectif impair chacun a bien `n-1` adversaires, mais **chôme une fois** : il faut donc `n`
    rondes pour les rencontrer tous, le bye tournant. Le raccourci `n-1` dans les deux cas
    refuserait une composition parfaitement jouable — le genre d'écart qui ne se voit qu'en
    refusant un format légitime le jour J.
    """
    assert rondes_maximales(5) == 5
    assert rondes_maximales(4) == 3

    _etape(effectif=5, suisse=ConfigurationSuisse(nb_rondes=5))  # ne lève pas


def test_sans_effectif_declare_rien_n_est_refuse() -> None:
    """On ne refuse pas ce qu'on ne peut pas juger : l'atelier montre la borne, il ne devine pas.

    Une étape sans effectif déclaré est le régime **normal** d'une composition en cours (brouillon
    d'ADR-0063). Refuser ici obligerait à déclarer l'effectif avant de choisir ses rondes, ce que le
    CA ne demande nulle part.
    """
    _etape(effectif=None, suisse=ConfigurationSuisse(nb_rondes=64))  # ne lève pas


def test_le_format_de_bibliotheque_ne_borne_rien() -> None:
    """Un format est réutilisé sur des effectifs qu'il ignore — règle 2, un format est de la config.

    « 5 rondes » est appariable à 12 archers et ne l'est pas à 5. Poser la borne sur `ModelePhase`
    figerait la brique sur un effectif supposé ; elle se juge sur l'**étape**, une fois le tournoi
    connu. C'est le régime brouillon d'ADR-0063, et le même parti que `ConfigurationBigShootOff`.
    """
    modele = ModelePhase(ordre=1, type=TypePhase.SUISSE, suisse=ConfigurationSuisse(nb_rondes=5))

    assert modele.suisse == ConfigurationSuisse(nb_rondes=5)
    # Et il refuse de s'appliquer à un tournoi dont l'effectif ne le permet pas — le garde-fou a
    # changé de porte, il n'a pas disparu.
    with pytest.raises(ConfigurationSuisseInvalide):
        ModelePhase(
            ordre=1,
            type=TypePhase.SUISSE,
            effectif=4,
            suisse=ConfigurationSuisse(nb_rondes=5),
        ).pour_tournoi(tournoi_id=1)


def test_un_reglage_suisse_sur_un_autre_type_est_refuse() -> None:
    """Un réglage que rien ne lit est invisible et faux — même garde que poules et Big Shoot Off.

    Le cas visé est le **retypage** : on compose une phase en suisse, on la repasse en élimination
    directe, et le nombre de rondes reste accroché à un type qui ne le lira jamais.
    """
    with pytest.raises(ConfigurationSuisseInvalide, match="n'est pas un système suisse"):
        Phase(
            depart_id=1,
            ordre=1,
            type=TypePhase.ELIMINATION_DIRECTE,
            suisse=ConfigurationSuisse(nb_rondes=5),
        )


def test_un_nombre_de_rondes_nul_est_refuse_par_le_reglage_lui_meme() -> None:
    """La borne basse, elle, ne dépend d'aucun effectif : elle vit sur `ConfigurationSuisse`.

    C'est la ligne de partage que cette US a dû tracer : ce qui est vrai du réglage **seul** reste
    sur le réglage, ce qui dépend du couple (réglage, effectif) monte à l'étape.
    """
    with pytest.raises(ConfigurationSuisseInvalide, match="au moins une ronde"):
        ConfigurationSuisse(nb_rondes=0)
