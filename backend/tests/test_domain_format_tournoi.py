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
                sources=(SourcePhase(ordre_source=1, rang_debut=1, rang_fin=8),),
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


def test_de_phases_diagnostique_un_tournoi_sans_phase_au_lieu_de_le_refuser() -> None:
    """Capturer un tournoi sans phase donne un **brouillon vide**, signalé comme tel.

    Le refus n'a pas disparu du produit : `ServiceFormats.promouvoir` lève toujours
    `TournoiSansPhase` (409) avant d'en arriver là — c'est lui qui porte cette règle, et il ne
    dépendait déjà pas du domaine pour l'appliquer.
    """
    capture = FormatTournoi.de_phases("Vide", [])

    assert capture.etapes == ()
    assert "format_sans_etape" in {anomalie.code for anomalie in capture.anomalies()}


# --- Invariants : ce qui bloque l'**usage**, non plus l'enregistrement ---------------------------
#
# ⚠️ **Cinq tests inversés en E01US024, délibérément.** Ils vérifiaient que la *construction*
# refuse ; ils vérifient désormais que le brouillon s'enregistre, que le diagnostic **nomme** le
# défaut avec le même code, et que `appliquer` refuse avec la **même exception qu'avant**. Le
# garde-fou n'est pas désarmé : il a changé de porte (ADR-0063). C'est le CA qui l'exige — « *on
# doit pouvoir sauvegarder le brouillon tout le temps, mais on ne peut réellement l'utiliser pour un
# vrai tournoi que s'il est valide* ». Précédent au projet : le test HTTP inversé de DETTE-009.


def _codes(format_tournoi: FormatTournoi) -> set[str]:
    return {anomalie.code for anomalie in format_tournoi.anomalies()}


def test_un_format_sans_etape_s_enregistre_mais_ne_s_applique_pas() -> None:
    """Appliquer un format vide ne créerait rien, et l'organisateur croirait avoir assemblé son
    tournoi — le refus reste, il est seulement rendu au moment de l'assemblage."""
    vide = FormatTournoi.creer("Vide", [])

    assert "format_sans_etape" in _codes(vide)
    with pytest.raises(FormatSansEtape):
        vide.appliquer(TOURNOI)


def test_un_nom_vide_reste_refuse_a_l_enregistrement() -> None:
    """**Seul** invariant qui n'a pas bougé : le nom est la clé d'unicité de la bibliothèque, un
    format sans nom ne serait pas un brouillon mais un modèle introuvable."""
    with pytest.raises(NomFormatInvalide):
        FormatTournoi.creer("   ", [_qualification()])


def test_le_nom_est_normalise() -> None:
    assert FormatTournoi.creer("  Mon format  ", [_qualification()]).nom == "Mon format"


def test_des_ordres_non_contigus_s_enregistrent_mais_ne_s_appliquent_pas() -> None:
    """Le **même** invariant que `SequencePhases` (ADR-0045 §3) — déplacé vers l'application."""
    troue = FormatTournoi.creer("Trou", [_qualification(ordre=1), _qualification(ordre=3)])

    assert "sequence_ordre_invalide" in _codes(troue)
    with pytest.raises(SequenceOrdreInvalide):
        troue.appliquer(TOURNOI)


def test_une_source_posterieure_s_enregistre_mais_ne_s_applique_pas() -> None:
    en_avant = FormatTournoi.creer(
        "Source en avant",
        [
            ModelePhase(
                ordre=1,
                type=TypePhase.ELIMINATION_DIRECTE,
                sources=(SourcePhase(ordre_source=2, rang_debut=1, rang_fin=8),),
            ),
            _qualification(ordre=2),
        ],
    )

    assert "source_apres_phase" in _codes(en_avant)
    with pytest.raises(SourceApresPhase):
        en_avant.appliquer(TOURNOI)


def test_un_modele_de_qualification_sans_bareme_se_compose_mais_ne_s_applique_pas() -> None:
    """Les invariants **internes** d'une phase valent toujours pour la phase produite — c'est
    `pour_tournoi` qui construit une `Phase`, et `Phase.__post_init__` n'a pas bougé."""
    brouillon = FormatTournoi.creer(
        "Qualif à finir", [ModelePhase(ordre=1, type=TypePhase.QUALIFICATION)]
    )

    assert "phase_qualification_incomplete" in _codes(brouillon)
    with pytest.raises(PhaseQualificationIncomplete):
        brouillon.appliquer(TOURNOI)


def test_un_format_qui_decrirait_une_phase_impossible_echoue_a_l_application() -> None:
    """Le garde-fou annoncé par l'ADR-0060 : l'échec précède l'exécution du moteur — mais il se
    produit désormais à l'**assemblage**, pas à la composition.

    Un grain `fin_de_duel` sur une qualification est refusé par la même règle
    (`anomalies_etape`) que celle qu'applique `Phase` : le format peut la **décrire**, aucun
    tournoi ne peut la **recevoir**.
    """
    impossible = FormatTournoi.creer(
        "Grain impossible",
        [
            ModelePhase(
                ordre=1,
                type=TypePhase.QUALIFICATION,
                bareme=BaremeQualification.preset_ffta_18m(),
                validation=GrainValidation.fin_de_duel(),
            )
        ],
    )

    assert "grain_incompatible_avec_type_phase" in _codes(impossible)
    with pytest.raises(Exception) as echec:
        impossible.appliquer(TOURNOI)
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
