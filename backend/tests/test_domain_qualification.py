"""Tests du découpage d'une **qualification en tours** (E05US035) — domaine pur.

Dérivés du **CA** (règle 9), écrits avant l'implémentation :

> *En tant qu'organisateur, je veux pouvoir découper une qualification en tours (« 20 volées en
> 2 tours de 10 »), afin de pouvoir y programmer une pause comme sur les quatre autres formats.*

- **CA** — une qualification se règle en `n` tours, et son avancement se lit tour par tour.
- **CA** — un arrêt programmé se pose sur une qualification (la table de refus cesse de l'écarter).
- ⚠️ **Le tour d'une qualification peut reculer** : un archer qui commence en retard fait baisser
  le minimum du plateau. Le calcul est écrit en le sachant — il n'a **aucune mémoire**.

Le *qui* du plateau (population réelle, plan de cibles, forfaits) n'est pas ici : c'est une
résolution applicative, prouvée dans `test_service_saisie`. Ce module ne prouve que l'arithmétique
du découpage, à laquelle on donne le compte du plus lent.
"""

from __future__ import annotations

import pytest

from domain.arret_programme import ArretProgramme, PorteeArret, verifier_type_arretable
from domain.bareme import BaremeQualification
from domain.contrat_phase import TYPES_ARRETABLES, TypePhase
from domain.deroule_etape import EtapeDeroule
from domain.erreurs import ArretProgrammeInvalide, DecoupageEnToursInvalide
from domain.format_tournoi import ModelePhase
from domain.grain_validation import GrainValidation
from domain.phase import Phase
from domain.qualification import DecoupageEnTours, verifier_decoupage
from domain.suisse import ConfigurationSuisse
from domain.suivi_deroule import avancement_de_qualification

_BAREME_18M = BaremeQualification.creer(20, 3)
"""Le preset FFTA 18 m : 20 volées de 3 flèches — le barème de l'exemple du CA."""


# --- CA « une qualification se règle en n tours » ------------------------------------------------


def test_un_decoupage_compte_au_moins_un_tour() -> None:
    """« Zéro tour » ne décrit aucun déroulé : le refus est au réglage, pas à la lecture."""
    with pytest.raises(DecoupageEnToursInvalide):
        DecoupageEnTours(nb_tours=0)


def test_un_decoupage_qui_ne_tombe_pas_juste_est_refuse() -> None:
    """20 volées en 3 tours ne fait pas des tours égaux : refusé **à la composition**.

    C'est l'arbitrage du cadrage du 20/08/2026 : l'organisateur saisit un **nombre de tours**, et
    le moteur en déduit la longueur. Un dernier tour plus court serait un déroulé où la pause ne
    tombe pas au même endroit pour tout le monde — on le refuse plutôt que de l'inventer.
    """
    with pytest.raises(DecoupageEnToursInvalide):
        verifier_decoupage(_BAREME_18M, DecoupageEnTours(nb_tours=3))


def test_un_decoupage_qui_tombe_juste_est_accepte() -> None:
    """L'exemple du CA : « 20 volées en 2 tours de 10 »."""
    verifier_decoupage(_BAREME_18M, DecoupageEnTours(nb_tours=2))


def test_un_decoupage_sans_bareme_ne_se_juge_pas() -> None:
    """Une étape en cours de composition n'a pas encore de barème : on ne refuse pas ce qu'on ne
    peut pas juger (la doctrine déjà tenue par `_verifier_rondes_appariables`)."""
    verifier_decoupage(None, DecoupageEnTours(nb_tours=3))


# --- CA « son avancement se lit tour par tour » --------------------------------------------------


@pytest.mark.parametrize(
    ("volees_du_plus_lent", "tour_attendu"),
    [
        (0, 1),  # personne n'a tiré : le premier tour tourne
        (9, 1),  # le plus lent est dans son 10ᵉ tir : le tour 1 n'est pas fini
        (10, 2),  # tout le monde a bouclé 10 volées : le tour 1 est franchi
        (19, 2),
        (20, None),  # tout est tiré : plus rien ne tourne (convention `AvancementDePhase`)
    ],
)
def test_le_tour_courant_se_derive_du_plus_lent(
    volees_du_plus_lent: int, tour_attendu: int | None
) -> None:
    """Une phase avance au rythme du **dernier** archer, jamais du premier.

    C'est l'invariant qui protège du pire mode de défaillance : couper la salle alors qu'une partie
    du pas de tir tire encore. Le compte fourni est déjà celui du plus lent — voir l'entête.
    """
    avancement = avancement_de_qualification(
        volees_du_plus_lent, _BAREME_18M, DecoupageEnTours(nb_tours=2)
    )
    assert (avancement.nb_tours, avancement.tour_courant) == (2, tour_attendu)


def test_une_qualification_non_decoupee_compte_un_seul_tour() -> None:
    """Le défaut : la phase **est** son tour. Ce n'est pas un cas dégénéré — c'est vrai."""
    avancement = avancement_de_qualification(7, _BAREME_18M, None)
    assert (avancement.nb_tours, avancement.tour_courant) == (1, 1)


def test_une_qualification_non_decoupee_et_finie_ne_tourne_plus() -> None:
    avancement = avancement_de_qualification(20, _BAREME_18M, None)
    assert (avancement.nb_tours, avancement.tour_courant) == (1, None)


def test_le_tour_recule_quand_un_retardataire_rejoint_le_plateau() -> None:
    """⚠️ Le piège nommé par la fiche, à ne pas redécouvrir le jour J.

    Le plateau est au tour 2 (tout le monde a bouclé ses 10 volées) ; un archer qui commence en
    retard fait retomber le minimum à 0, donc le tour à 1. Le calcul **n'a aucune mémoire** : il
    dit ce qui tourne maintenant. C'est `phases_a_arreter` qui absorbe le recul, par une
    comparaison `>` et non `!=` (correctif de 2ᵉ passe d'E05US033) — et il ne peut le faire que si
    la lecture, elle, reste honnête.
    """
    decoupage = DecoupageEnTours(nb_tours=2)
    assert avancement_de_qualification(10, _BAREME_18M, decoupage).tour_courant == 2
    assert avancement_de_qualification(0, _BAREME_18M, decoupage).tour_courant == 1


# --- CA « un arrêt programmé se pose sur une qualification » -------------------------------------


def test_la_qualification_est_desormais_arretable() -> None:
    """La table de refus cesse de l'écarter : c'est l'objet même de l'US."""
    assert TypePhase.QUALIFICATION in TYPES_ARRETABLES
    verifier_type_arretable(TypePhase.QUALIFICATION)


def _qualification(
    *, nb_tours: int | None, arrets: tuple[ArretProgramme, ...] = ()
) -> EtapeDeroule:
    """Une étape de qualification composée à l'atelier, découpée ou non."""
    return EtapeDeroule(
        tournoi_id=1,
        ordre=1,
        type=TypePhase.QUALIFICATION,
        bareme=_BAREME_18M,
        validation=GrainValidation.fin_de_serie(),
        decoupage=None if nb_tours is None else DecoupageEnTours(nb_tours=nb_tours),
        arrets=arrets,
    )


def test_un_arret_se_pose_sur_une_qualification_decoupee() -> None:
    """Le geste complet du CA : « la salle s'arrête après le premier tour de qualification ».

    ⚠️ **Ce test montait un `ArretProgramme` nu et relisait son propre champ** — il serait passé à
    l'identique si l'US entière avait été annulée, et c'est ce trou qui a laissé passer le bloquant
    ci-dessous (relevé par les cinq axes de revue). Il compose désormais l'**étape**, seule porte
    où le refus vit.
    """
    etape = _qualification(nb_tours=2, arrets=(ArretProgramme(apres_tour=1),))

    assert etape.arrets == (ArretProgramme(apres_tour=1, portee=PorteeArret.PHASE),)


def test_un_arret_sur_une_qualification_non_decoupee_est_refuse() -> None:
    """⚠️ **Bloquant de revue — le mode de panne que tout le mécanisme existe pour interdire.**

    Une qualification non découpée compte **un** tour : « après le tour 1 » y est inerte. Le refus
    par *type* passe (elle est arrêtable), mais l'arrêtabilité réelle dépend ici d'un **réglage
    d'instance** — et le nombre de tours, contrairement aux quatre autres formats, est connu dès la
    composition. Sans ce refus, l'organisateur enregistrait sa pause repas, recevait un 201, et
    découvrait à midi qu'elle n'était jamais partie.

    C'est aussi ce que le message de `verifier_type_arretable` promet en toutes lettres (« une
    qualification **découpée en tours** ») : le code doit tenir la phrase qu'il affiche.
    """
    with pytest.raises(ArretProgrammeInvalide):
        _qualification(nb_tours=None, arrets=(ArretProgramme(apres_tour=1),))


def test_le_refus_d_une_qualification_non_decoupee_dit_quoi_faire() -> None:
    """Un refus sans issue est un cul-de-sac (`P-3`) : il doit nommer le geste réparateur.

    « La phase n'en compte que 1 » explique le *pourquoi* ; l'organisateur n'a aucune raison de
    deviner qu'un réglage de découpage existe deux blocs plus haut.
    """
    with pytest.raises(ArretProgrammeInvalide) as refus:
        _qualification(nb_tours=None, arrets=(ArretProgramme(apres_tour=1),))

    assert "Découpez" in str(refus.value)


def test_un_arret_apres_le_dernier_tour_est_refuse() -> None:
    """« Après le tour 2 » sur une phase de 2 tours ne coupe rien — elle est finie à ce moment-là.

    Le cas est banal, pas tordu : `n` est petit (2 ou 4) et saisi à la main. Sans ce refus, l'arrêt
    se déclenchait par la branche « tout est joué » et mettait en pause une phase **entièrement
    tirée**, qu'il fallait relancer pour pouvoir la clôturer.
    """
    with pytest.raises(ArretProgrammeInvalide):
        _qualification(nb_tours=2, arrets=(ArretProgramme(apres_tour=2),))


def test_les_autres_formats_gardent_leur_nombre_de_tours_inconnu() -> None:
    """La correction ne doit pas déborder : hors qualification, le nombre de tours se lit le jour J.

    Un système suisse réglé à 7 rondes n'en joue que 5 si l'effectif ne le permet pas — refuser
    « après le tour 6 » à la composition serait le refus abusif que la doctrine « on ne refuse pas
    ce qu'on ne peut pas juger » interdit.
    """
    etape = EtapeDeroule(
        tournoi_id=1,
        ordre=2,
        type=TypePhase.SUISSE,
        suisse=ConfigurationSuisse(nb_rondes=5),
        arrets=(ArretProgramme(apres_tour=9),),
    )

    assert etape.arrets[0].apres_tour == 9


def test_un_decoupage_sur_un_type_qui_n_est_pas_une_qualification_est_refuse() -> None:
    """La garde de réglage fantôme, revendiquée par trois docstrings de DTO et testée par aucune.

    Retyper une phase sans nettoyer son réglage laisserait derrière une valeur que rien ne lit —
    invisible et fausse. Même garde que `poules`, `big_shoot_off` et `suisse` sur `Phase`.
    """
    with pytest.raises(DecoupageEnToursInvalide):
        Phase(depart_id=7, ordre=2, type=TypePhase.POULES, decoupage=DecoupageEnTours(nb_tours=2))
    with pytest.raises(DecoupageEnToursInvalide):
        EtapeDeroule(
            tournoi_id=1, ordre=2, type=TypePhase.POULES, decoupage=DecoupageEnTours(nb_tours=2)
        )


def test_le_decoupage_voyage_de_l_etape_a_la_phase() -> None:
    """`instancier` recopie le découpage : sans lui, le lecteur d'avancement verrait `None`.

    Conséquence si la recopie manquait — `nb_tours=1`, donc **aucune pause ne partirait jamais**,
    et rien ne le signalerait. C'est le pendant du défaut `barrage_jusqu_au` d'ADR-0076.
    """
    etape = _qualification(nb_tours=2)

    assert etape.instancier(depart_id=7).decoupage == DecoupageEnTours(nb_tours=2)


def test_le_decoupage_survit_a_la_capture_en_format_et_a_sa_reapplication() -> None:
    """Aller-retour `EtapeDeroule` → `ModelePhase` → `EtapeDeroule` (ADR-0093 § Conséquences).

    Sans ce voyage, capturer un tournoi en format perdrait son découpage **en silence**, et le
    format réappliqué rendrait sa qualification non arrêtable — donc toutes les pauses posées
    dessus, refusées. Le dépôt a déjà payé cette leçon deux fois (`barrage_jusqu_au`, puis
    `arrets`) ; ce test est ce qui empêche la troisième.
    """
    etape = _qualification(nb_tours=2)

    rejouee = ModelePhase.d_etape(etape).pour_tournoi(tournoi_id=2)

    assert rejouee.decoupage == DecoupageEnTours(nb_tours=2)


@pytest.mark.parametrize(
    "type_phase",
    [TypePhase.ECHAUFFEMENT, TypePhase.BARRAGE, TypePhase.PLACEMENT],
)
def test_les_types_hors_perimetre_restent_refuses(type_phase: TypePhase) -> None:
    """🔭 Hors périmètre, et le refus doit le **rester** : un réglage inerte est pire qu'un refus.

    L'échauffement n'a ni barème ni feuille de marque — aucune donnée existante ne dit où il en
    est. Les deux autres ne sont déroulés par aucun service, et ne le seront pas : le `placement`
    n'a jamais eu de service pour monter son arbre, le `barrage` est un **départage**.

    Ce test est le garde-fou de la coupe : élargir la table sans lecteur d'avancement rendrait le
    réglage acceptable à l'atelier et **définitivement muet** le jour J.

    ⚠️ **La colline en est sortie le 22/08/2026** (E05US027), et par le chemin exact qu'ADR-0093 a
    dessiné : elle n'a pas été ajoutée à la main à une table d'arrêtables, elle a gagné
    `avancement_lisible` au registre de contrat — parce que `ServiceColline.avancement_de_phase`
    existe — et `TYPES_ARRETABLES` en **dérive**. C'est la vérification à l'usage de la séparation
    posée par cet ADR : la capacité *avancement lisible* et la capacité *déroulé* sont deux
    questions distinctes, et c'est la première qui commande l'arrêt.
    """
    with pytest.raises(ArretProgrammeInvalide):
        verifier_type_arretable(type_phase)
