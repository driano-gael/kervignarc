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
from domain.erreurs import ArretProgrammeInvalide, DecoupageEnToursInvalide
from domain.qualification import DecoupageEnTours, verifier_decoupage
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


def test_un_arret_se_pose_sur_une_qualification_decoupee() -> None:
    """Le geste complet du CA : « la salle s'arrête après le premier tour de qualification »."""
    arret = ArretProgramme(apres_tour=1, portee=PorteeArret.PHASE)
    assert arret.apres_tour == 1


@pytest.mark.parametrize(
    "type_phase",
    [TypePhase.ECHAUFFEMENT, TypePhase.BARRAGE, TypePhase.PLACEMENT, TypePhase.COLLINE],
)
def test_les_types_hors_perimetre_restent_refuses(type_phase: TypePhase) -> None:
    """🔭 Hors périmètre, et le refus doit le **rester** : un réglage inerte est pire qu'un refus.

    L'échauffement n'a ni barème ni feuille de marque — aucune donnée existante ne dit où il en
    est. Les trois autres ne sont déroulés par aucun service (`DETTE-028`). Ce test est le
    garde-fou de la coupe : élargir la table sans lecteur d'avancement rendrait le réglage
    acceptable à l'atelier et **définitivement muet** le jour J.
    """
    with pytest.raises(ArretProgrammeInvalide):
        verifier_type_arretable(type_phase)
