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
from domain.deroule_etape import EtapeDeroule
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
from domain.phase import SourceModele, SourcePhase, StatutPhase, TypePhase
from tests.conftest import appliquer_en_memoire, identite_d_etape

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
    assert "depart_id" not in champs


def test_un_format_existe_sans_aucun_tournoi() -> None:
    """Brique de bibliothèque : le format se construit sans qu'aucun tournoi n'existe."""
    format_tournoi = _format()
    champs = {champ.name for champ in dataclasses.fields(FormatTournoi)}
    assert "depart_id" not in champs
    assert format_tournoi.nom == "Mon format"


# --- CA « appliquer crée les phases du tournoi » -----------------------------------------------


def test_appliquer_cree_une_phase_par_etape_dans_l_ordre() -> None:
    phases = appliquer_en_memoire(
        FormatTournoi.creer(
            "Deux étapes",
            [
                _qualification(ordre=1, effectif=16),
                ModelePhase(
                    ordre=2,
                    type=TypePhase.ELIMINATION_DIRECTE,
                    sources=(SourceModele(ordre_source=1, rang_debut=1, rang_fin=8),),
                    effectif=8,
                ),
            ],
        ),
        TOURNOI,
    )

    assert [phase.ordre for phase in phases] == [1, 2]
    assert [phase.type for phase in phases] == [
        TypePhase.QUALIFICATION,
        TypePhase.ELIMINATION_DIRECTE,
    ]


def test_les_etapes_appliquees_sont_rattachees_au_tournoi() -> None:
    """`tournoi_id` **naît** à l'application — il n'existait pas au modèle de bibliothèque."""
    etapes = appliquer_en_memoire(_format(), TOURNOI)

    assert all(etape.tournoi_id == TOURNOI for etape in etapes)


def test_le_statut_naît_a_l_instanciation_dans_un_creneau() -> None:
    """L'autre moitié du CA, en **deux temps** depuis ADR-0076.

    Le CA disait « l'appliquer à un tournoi crée ses phases, statut *à venir* ». C'est toujours
    vrai, mais en deux gestes : `appliquer` définit le **déroulé** (une fois), `instancier`
    en crée l'**avancement** dans un créneau. Ce sont ces deux natures que l'ADR sépare — et les
    tenir ensemble était précisément ce qui laissait les copies diverger.
    """
    (etape,) = appliquer_en_memoire(_format(), TOURNOI)

    phase = etape.instancier(depart_id=7)

    assert phase.statut is StatutPhase.A_VENIR
    assert phase.depart_id == 7
    # La définition suit dans l'objet du moteur, sans être persistée en double.
    assert phase.bareme == BaremeQualification.preset_ffta_18m()


def test_instancier_un_modele_n_attribue_aucun_identifiant() -> None:
    """L'instanciation est **pure** : c'est le service qui décide d'écrire (aucun `id` attribué).

    ⚠️ **Le sujet a changé avec E05US022** (correctif de revue) : ce test portait sur
    `FormatTournoi.appliquer`, que l'US supprime — ancrer demande une identité que seule la
    persistance attribue. La propriété « rien n'est identifié tant que rien n'est écrit »
    appartient désormais à `ModelePhase.pour_tournoi`, et c'est elle qu'on épingle ; la viser sur
    le décor `appliquer_en_memoire` aurait fait affirmer au test une propriété du décor.
    """
    assert all(modele.pour_tournoi(TOURNOI).id is None for modele in _format().etapes_ordonnees)


def test_appliquer_transporte_bareme_grain_effectif_et_source() -> None:
    """Ce que le CA énumère comme contenu d'un modèle doit arriver intact dans la phase."""
    grain = GrainValidation.toutes_les_n_volees(4)
    bareme = BaremeQualification.creer(nb_volees=10, nb_fleches_par_volee=6)

    (phase,) = appliquer_en_memoire(
        FormatTournoi.creer(
            "Transport",
            [ModelePhase.qualification(bareme, validation=grain, effectif=24)],
        ),
        TOURNOI,
    )

    assert phase.bareme == bareme
    assert phase.validation == grain
    assert phase.effectif == 24


def test_appliquer_deux_fois_donne_des_phases_independantes() -> None:
    """Deux tournois assemblés depuis le **même** format ne partagent rien (CA « copie »)."""
    format_tournoi = _format()

    (phase_a,) = appliquer_en_memoire(format_tournoi, 1)
    (phase_b,) = appliquer_en_memoire(format_tournoi, 2)

    assert phase_a.tournoi_id == 1
    assert phase_b.tournoi_id == 2
    assert phase_a is not phase_b


# --- CA « modifier la copie n'altère pas le modèle » -------------------------------------------


def test_ajuster_une_phase_appliquee_n_altere_pas_le_format() -> None:
    """La promesse centrale de l'US, côté format : la copie s'ajuste, le modèle ne bouge pas."""
    format_tournoi = _format()
    (etape,) = appliquer_en_memoire(format_tournoi, TOURNOI)

    dataclasses.replace(etape, bareme=BaremeQualification.creer(3, 3))

    assert format_tournoi.etapes[0].bareme == BaremeQualification.preset_ffta_18m()


def test_modifier_le_format_n_altere_pas_les_phases_deja_appliquees() -> None:
    """Le sens inverse, qui est la raison d'être de la copie : l'archive ne doit pas bouger."""
    format_tournoi = _format()
    (etape,) = appliquer_en_memoire(format_tournoi, TOURNOI)

    format_tournoi.modifier(
        "Renommé",
        [ModelePhase.qualification(BaremeQualification.creer(1, 1))],
        None,
    )

    assert etape.bareme == BaremeQualification.preset_ffta_18m()


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
        None,
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


def test_de_deroule_capture_la_regle_et_oublie_le_rattachement() -> None:
    """On promeut une **règle**, pas une édition : le tournoi ne remonte pas dans le format.

    Le statut ne peut plus remonter *par construction* depuis ADR-0076 — une étape n'en porte
    aucun. Ce test garde donc son intention (« ce qui appartient à l'édition ne devient pas une
    propriété du format ») en la portant sur ce qui reste séparable : le `tournoi_id`.
    """
    (etape,) = appliquer_en_memoire(_format(), TOURNOI)

    promu = FormatTournoi.de_deroule("Le format de l'an dernier", [etape])

    assert promu.etapes[0].bareme == BaremeQualification.preset_ffta_18m()
    champs = {champ.name for champ in dataclasses.fields(type(promu.etapes[0]))}
    assert "tournoi_id" not in champs
    assert "statut" not in champs


def test_de_phases_diagnostique_un_tournoi_sans_phase_au_lieu_de_le_refuser() -> None:
    """Capturer un tournoi sans phase donne un **brouillon vide**, signalé comme tel.

    Le refus n'a pas disparu du produit : `ServiceFormats.promouvoir` lève toujours
    `TournoiSansPhase` (409) avant d'en arriver là — c'est lui qui porte cette règle, et il ne
    dépendait déjà pas du domaine pour l'appliquer.
    """
    capture = FormatTournoi.de_deroule("Vide", [])

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
        appliquer_en_memoire(vide, TOURNOI)


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
        appliquer_en_memoire(troue, TOURNOI)


def test_une_source_posterieure_s_enregistre_mais_ne_s_applique_pas() -> None:
    en_avant = FormatTournoi.creer(
        "Source en avant",
        [
            ModelePhase(
                ordre=1,
                type=TypePhase.ELIMINATION_DIRECTE,
                sources=(SourceModele(ordre_source=2, rang_debut=1, rang_fin=8),),
            ),
            _qualification(ordre=2),
        ],
    )

    assert "source_apres_phase" in _codes(en_avant)
    with pytest.raises(SourceApresPhase):
        appliquer_en_memoire(en_avant, TOURNOI)


def test_un_modele_de_qualification_sans_bareme_se_compose_mais_ne_s_applique_pas() -> None:
    """Les invariants **internes** d'une phase valent toujours pour la phase produite — c'est
    `pour_tournoi` qui construit une `Phase`, et `Phase.__post_init__` n'a pas bougé."""
    brouillon = FormatTournoi.creer(
        "Qualif à finir", [ModelePhase(ordre=1, type=TypePhase.QUALIFICATION)]
    )

    assert "phase_qualification_incomplete" in _codes(brouillon)
    with pytest.raises(PhaseQualificationIncomplete):
        appliquer_en_memoire(brouillon, TOURNOI)


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
        appliquer_en_memoire(impossible, TOURNOI)
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


def test_la_promotion_redescend_les_prelevements_sur_les_rangs() -> None:
    """**Le sens retour de la conversion** (ADR-0078 §4), qu'aucun test n'exerçait.

    Le CA ajouté le 20/09/2026 dit que la traduction va dans les **deux** sens : appliquer un
    format ancre les prélèvements sur des identités, promouvoir un déroulé les redescend sur des
    rangs — un format de bibliothèque n'ayant aucune identité à citer (ADR-0060 §5). Les décors de
    promotion existants ne portaient **aucune source**, donc `id_vers_ordre` n'était jamais
    exercé : un `d_etape` resté sur la table vide aurait produit des formats aux prélèvements
    perdus, sans un seul rouge.
    """
    qualif = EtapeDeroule(
        tournoi_id=TOURNOI,
        ordre=1,
        type=TypePhase.QUALIFICATION,
        bareme=BaremeQualification.preset_ffta_18m(),
        validation=GrainValidation.fin_de_serie(),
        id=identite_d_etape(1),
    )
    tableau = EtapeDeroule(
        tournoi_id=TOURNOI,
        ordre=2,
        type=TypePhase.ELIMINATION_DIRECTE,
        sources=(SourcePhase.par_rangs(identite_d_etape(1), 1, 8),),
        id=identite_d_etape(2),
    )

    promu = FormatTournoi.de_deroule("L'an dernier", [qualif, tableau])

    # Le **rang**, pas l'identité : 1, et surtout pas `identite_d_etape(1)`.
    assert promu.etapes[1].sources == (SourceModele.par_rangs(1, 1, 8),)


def test_promouvoir_puis_reappliquer_rend_le_meme_ancrage() -> None:
    """L'aller-retour prouve que les deux traductions sont **réciproques** — « une seule traduction
    sert les deux sens » est le CA, et c'est ce qui le vérifie."""
    depart = FormatTournoi.creer(
        "Aller",
        [
            _qualification(ordre=1, effectif=16),
            ModelePhase(
                ordre=2,
                type=TypePhase.ELIMINATION_DIRECTE,
                sources=(SourceModele(ordre_source=1, rang_debut=1, rang_fin=8),),
                effectif=8,
            ),
        ],
    )

    etapes = appliquer_en_memoire(depart, TOURNOI)
    retour = FormatTournoi.de_deroule("Retour", list(etapes))

    assert retour.etapes[1].sources == depart.etapes[1].sources
