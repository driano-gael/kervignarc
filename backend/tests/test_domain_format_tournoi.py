"""Tests unitaires de l'agrégat `FormatTournoi` (E01US023 / ADR-0060) — domaine pur, sans base.

Dérivés des puces **CA — format de tournoi** et **CA — copie à l'assemblage** de
`stories/E01-configuration.md` :

- « un format est une brique nommée portant une séquence de modèles de phases (type, barème, grain,
  effectif, source) ; il ne porte **ni statut, ni tournoi** » ;
- « l'appliquer à un tournoi **crée ses phases** (ordre 1..N, statut `à venir`), qui restent
  ensuite ajustables **sans altérer le format** ».
"""

from __future__ import annotations

import dataclasses

import pytest

from domain.bareme import BaremeQualification
from domain.erreurs import (
    FormatSansEtape,
    NomFormatInvalide,
    PhaseQualificationIncomplete,
    SequenceOrdreInvalide,
    SourceApresPhase,
)
from domain.format_tournoi import FormatTournoi, ModelePhase
from domain.grain_validation import GrainValidation, TypeGrain
from domain.patrimoine import OrigineBrique
from domain.phase import SourcePhase, StatutPhase, TypePhase

TOURNOI = 7


def _qualification(ordre: int = 1, effectif: int | None = None) -> ModelePhase:
    """Un modèle de qualification au barème FFTA, grain par défaut (fin de série)."""
    return ModelePhase.qualification(
        BaremeQualification.preset_ffta_18m(), ordre=ordre, effectif=effectif
    )


def _format(*etapes: ModelePhase) -> FormatTournoi:
    return FormatTournoi.creer("Mon format", etapes or (_qualification(),))


# --- CA « le format ne porte ni statut, ni tournoi » -------------------------------------------


def test_un_modele_de_phase_ne_porte_ni_statut_ni_tournoi() -> None:
    """Le CA distingue le modèle de la phase : ces deux champs n'existent **pas** sur le modèle.

    Vérifié par introspection plutôt que par un attribut absent : c'est la **forme** de l'agrégat
    qui est au CA (« sans statut ni tournoi »), et un `hasattr` négatif passerait aussi sur une
    faute de frappe.
    """
    champs = {champ.name for champ in dataclasses.fields(ModelePhase)}
    assert "statut" not in champs
    assert "tournoi_id" not in champs


def test_un_format_existe_sans_aucun_tournoi() -> None:
    """Brique de bibliothèque : le format se construit sans qu'aucun tournoi n'existe."""
    format_tournoi = _format()
    champs = {champ.name for champ in dataclasses.fields(FormatTournoi)}
    assert "tournoi_id" not in champs
    assert format_tournoi.nom == "Mon format"


# --- CA « appliquer crée les phases du tournoi » -----------------------------------------------


def test_appliquer_cree_une_phase_par_etape_dans_l_ordre() -> None:
    phases = FormatTournoi.creer(
        "Deux étapes",
        [
            _qualification(ordre=1, effectif=16),
            ModelePhase(
                ordre=2,
                type=TypePhase.ELIMINATION_DIRECTE,
                source=SourcePhase(ordre_source=1, rang_debut=1, rang_fin=8),
                effectif=8,
            ),
        ],
    ).appliquer(TOURNOI)

    assert [phase.ordre for phase in phases] == [1, 2]
    assert [phase.type for phase in phases] == [
        TypePhase.QUALIFICATION,
        TypePhase.ELIMINATION_DIRECTE,
    ]


def test_les_phases_appliquees_naissent_a_venir_et_rattachees_au_tournoi() -> None:
    """`statut` et `tournoi_id` **naissent** à l'application — ils n'existaient pas au modèle."""
    phases = _format().appliquer(TOURNOI)

    assert all(phase.statut is StatutPhase.A_VENIR for phase in phases)
    assert all(phase.tournoi_id == TOURNOI for phase in phases)


def test_les_phases_appliquees_ne_sont_pas_persistees() -> None:
    """L'application est **pure** : c'est le service qui décide d'écrire (aucun `id` attribué)."""
    assert all(phase.id is None for phase in _format().appliquer(TOURNOI))


def test_appliquer_transporte_bareme_grain_effectif_et_source() -> None:
    """Ce que le CA énumère comme contenu d'un modèle doit arriver intact dans la phase."""
    grain = GrainValidation.toutes_les_n_volees(4)
    bareme = BaremeQualification.creer(nb_volees=10, nb_fleches_par_volee=6)

    (phase,) = FormatTournoi.creer(
        "Transport",
        [ModelePhase.qualification(bareme, validation=grain, effectif=24)],
    ).appliquer(TOURNOI)

    assert phase.bareme == bareme
    assert phase.validation == grain
    assert phase.effectif == 24


def test_appliquer_deux_fois_donne_des_phases_independantes() -> None:
    """Deux tournois assemblés depuis le **même** format ne partagent rien (CA « copie »)."""
    format_tournoi = _format()

    (phase_a,) = format_tournoi.appliquer(1)
    (phase_b,) = format_tournoi.appliquer(2)

    assert phase_a.tournoi_id == 1
    assert phase_b.tournoi_id == 2
    assert phase_a is not phase_b


# --- CA « modifier la copie n'altère pas le modèle » -------------------------------------------


def test_ajuster_une_phase_appliquee_n_altere_pas_le_format() -> None:
    """La promesse centrale de l'US, côté format : la copie s'ajuste, le modèle ne bouge pas."""
    format_tournoi = _format()
    (phase,) = format_tournoi.appliquer(TOURNOI)

    phase.avec_bareme(BaremeQualification.creer(nb_volees=3, nb_fleches_par_volee=3))

    assert format_tournoi.etapes[0].bareme == BaremeQualification.preset_ffta_18m()


def test_modifier_le_format_n_altere_pas_les_phases_deja_appliquees() -> None:
    """Le sens inverse, qui est la raison d'être de la copie : l'archive ne doit pas bouger."""
    format_tournoi = _format()
    (phase,) = format_tournoi.appliquer(TOURNOI)

    format_tournoi.modifier(
        "Renommé",
        [ModelePhase.qualification(BaremeQualification.creer(1, 1))],
    )

    assert phase.bareme == BaremeQualification.preset_ffta_18m()


# --- CA « modifier un officiel : copie ou sur place » ------------------------------------------


def test_modifier_un_officiel_sur_place_le_laisse_officiel() -> None:
    """« Le règlement peut évoluer » : l'issue « modifier sur place » conserve l'origine."""
    officiel = FormatTournoi.preset_ffta_18m()

    modifie = officiel.modifier(
        "FFTA officiel 18 m",
        [
            ModelePhase.qualification(
                BaremeQualification.creer(nb_volees=18, nb_fleches_par_volee=3)
            )
        ],
    )

    assert modifie.origine is OrigineBrique.FFTA


def test_en_creation_utilisateur_detache_une_copie_non_persistee() -> None:
    """L'autre issue : « en faire une copie pour garder les deux modèles »."""
    officiel = dataclasses.replace(FormatTournoi.preset_ffta_18m(), id=12)

    copie = officiel.en_creation_utilisateur("Ma variante")

    assert copie.origine is OrigineBrique.UTILISATEUR
    assert copie.id is None, "une copie est un nouveau modèle, pas une mise à jour de l'officiel"
    assert officiel.origine is OrigineBrique.FFTA, "l'original n'est pas touché"


# --- CA « promotion » : capturer les phases d'un tournoi en format -----------------------------


def test_de_phases_capture_le_deroule_et_oublie_l_avancement() -> None:
    """On promeut un **déroulé**, pas un état : le statut d'une phase en cours ne remonte pas."""
    (phase,) = _format().appliquer(TOURNOI)
    en_cours = phase.demarrer()

    promu = FormatTournoi.de_phases("Le format de l'an dernier", [en_cours])

    assert promu.etapes[0].bareme == BaremeQualification.preset_ffta_18m()
    assert "statut" not in {champ.name for champ in dataclasses.fields(type(promu.etapes[0]))}


def test_de_phases_refuse_un_tournoi_sans_phase() -> None:
    with pytest.raises(FormatSansEtape):
        FormatTournoi.de_phases("Vide", [])


# --- Invariants : ceux d'une phase, plus ceux d'une séquence -----------------------------------


def test_un_format_sans_etape_est_refuse() -> None:
    """Distinct d'une `SequencePhases` vide, qui est licite : appliquer un format vide ne créerait
    rien, et l'organisateur croirait avoir assemblé son tournoi."""
    with pytest.raises(FormatSansEtape):
        FormatTournoi.creer("Vide", [])


def test_un_nom_vide_est_refuse() -> None:
    with pytest.raises(NomFormatInvalide):
        FormatTournoi.creer("   ", [_qualification()])


def test_le_nom_est_normalise() -> None:
    assert FormatTournoi.creer("  Mon format  ", [_qualification()]).nom == "Mon format"


def test_les_ordres_doivent_former_la_suite_contigue() -> None:
    """Le **même** invariant que `SequencePhases` (ADR-0045 §3), appliqué au format."""
    with pytest.raises(SequenceOrdreInvalide):
        FormatTournoi.creer("Trou", [_qualification(ordre=1), _qualification(ordre=3)])


def test_une_source_ne_peut_pas_designer_une_etape_posterieure() -> None:
    with pytest.raises(SourceApresPhase):
        FormatTournoi.creer(
            "Source en avant",
            [
                ModelePhase(
                    ordre=1,
                    type=TypePhase.ELIMINATION_DIRECTE,
                    source=SourcePhase(ordre_source=2, rang_debut=1, rang_fin=8),
                ),
                _qualification(ordre=2),
            ],
        )


def test_un_modele_de_qualification_sans_bareme_est_refuse() -> None:
    """Les invariants **internes** d'une phase valent aussi pour un modèle."""
    with pytest.raises(PhaseQualificationIncomplete):
        ModelePhase(ordre=1, type=TypePhase.QUALIFICATION)


def test_un_format_qui_decrirait_une_phase_impossible_echoue_a_la_construction() -> None:
    """Le garde-fou annoncé par l'ADR : l'échec est à la construction, pas à l'exécution du moteur.

    Un grain `fin_de_duel` sur une qualification est refusé par `verifier_coherence_etape`, la même
    fonction que celle qu'applique `Phase` — le format ne peut pas contenir ce qu'un tournoi
    refuserait.
    """
    with pytest.raises(Exception) as echec:
        ModelePhase.qualification(
            BaremeQualification.preset_ffta_18m(),
            validation=GrainValidation.fin_de_duel(),
        )
    assert echec.typename == "GrainIncompatibleAvecTypePhase"


# --- Presets ------------------------------------------------------------------------------------


def test_le_preset_ffta_est_marque_ffta_et_porte_le_bareme_officiel() -> None:
    preset = FormatTournoi.preset_ffta_18m()

    assert preset.origine is OrigineBrique.FFTA
    assert preset.etapes[0].bareme == BaremeQualification.preset_ffta_18m()
    assert preset.etapes[0].validation == GrainValidation(type=TypeGrain.FIN_DE_SERIE)


def test_le_preset_club_n_est_pas_marque_officiel() -> None:
    """`origine` dit la provenance, pas la conformité (ADR-0060 §4) : maison reste maison."""
    preset = FormatTournoi.preset_club()

    assert preset.origine is OrigineBrique.UTILISATEUR
    assert preset.etapes[0].bareme == BaremeQualification.creer(5, 3)
