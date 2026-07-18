"""Tests unitaires du moteur de placement (E03US001) — domaine pur, sans base.

Dérivés du CA (puce « capacité & fraction » clarifiée en trois budgets, puce « conflits », puce
« hauteur » d'ADR-0022), **avant** l'algorithme. On vérifie les invariants du placement, pas une
trace d'implémentation : les trois budgets d'une cible (espace ≤ 1,0 ; positions ≤ capacité ;
partage de carton ≤ capacité du blason), la contrainte de hauteur (une butte, une hauteur), le
rapport de conflits (pas d'échec silencieux) et le déterminisme (règle 9).
"""

from __future__ import annotations

from domain.gabarit_salle import Cible
from domain.placement import (
    ArcherAPlacer,
    CiblePlacee,
    Conflit,
    Placement,
    PlanDeCibles,
    PoseCalculee,
    RaisonConflit,
    cible_accepte,
    placer,
    placer_restants,
)


def _archer(
    archer_id: int,
    *,
    blason: int = 1,
    taille: float = 0.5,
    capacite_blason: int = 1,
    hauteur: int = 130,
) -> ArcherAPlacer:
    return ArcherAPlacer(
        archer_id=archer_id,
        blason_id=blason,
        taille=taille,
        capacite_blason=capacite_blason,
        hauteur_cm=hauteur,
    )


def _cibles(*capacites: int) -> tuple[Cible, ...]:
    return tuple(Cible(index=index, capacite=cap) for index, cap in enumerate(capacites, start=1))


def _positions(cible: CiblePlacee) -> tuple[str, ...]:
    return tuple(p.position for p in cible.placements)


def _archers_de(cible: CiblePlacee) -> tuple[int, ...]:
    return tuple(p.archer_id for p in cible.placements)


def test_chaque_archer_recoit_une_cible_et_une_position() -> None:
    """CA : chaque archer placé reçoit une cible et une position (lettres dans l'ordre)."""
    plan = placer(_cibles(4), (_archer(10, blason=1), _archer(20, blason=2)))
    assert _positions(plan.cibles[0]) == ("A", "B")
    assert _archers_de(plan.cibles[0]) == (10, 20)
    assert plan.conflits == ()


def test_espace_dune_cible_borne_a_1() -> None:
    """CA (budget espace) : la somme des fractions des cartons d'une cible ne dépasse pas 1,0.

    Deux blasons à 0,6 ne tiennent pas ensemble (1,2 > 1) : le second bascule sur la cible suivante,
    alors que les positions (capacité 4) en laisseraient largement la place."""
    plan = placer(
        _cibles(4, 4), (_archer(1, blason=1, taille=0.6), _archer(2, blason=2, taille=0.6))
    )
    assert _archers_de(plan.cibles[0]) == (1,)
    assert _archers_de(plan.cibles[1]) == (2,)


def test_trois_tiers_tiennent_sur_une_cible() -> None:
    """CA (budget espace) : trois blasons à 1/3 tiennent sur une cible malgré l'arrondi flottant."""
    tiers = 1 / 3
    plan = placer(
        _cibles(4),
        tuple(_archer(i, blason=i, taille=tiers) for i in (1, 2, 3)),
    )
    assert _archers_de(plan.cibles[0]) == (1, 2, 3)
    assert plan.conflits == ()


def test_positions_bornees_par_la_capacite_de_cible() -> None:
    """CA (budget positions) : le nombre d'archers d'une cible ne dépasse pas sa capacité.

    Trois petits blasons (0,25) tiennent en espace (0,75) mais une cible de capacité 2 n'accueille
    que 2 archers ; le troisième passe à la cible suivante."""
    plan = placer(
        _cibles(2, 4),
        tuple(_archer(i, blason=i, taille=0.25) for i in (1, 2, 3)),
    )
    assert _archers_de(plan.cibles[0]) == (1, 2)
    assert _archers_de(plan.cibles[1]) == (3,)


def test_plusieurs_archers_partagent_un_carton() -> None:
    """CA (budget partage) : les archers d'un même blason mutualisent un carton (triple = 3).

    Un blason pleine cible (taille 1,0) de capacité 3 accueille 3 archers sur un seul carton ; le
    4e, même blason, exigerait un carton neuf sans espace disponible → cible suivante."""
    plan = placer(
        _cibles(4, 4),
        tuple(_archer(i, blason=1, taille=1.0, capacite_blason=3) for i in (1, 2, 3, 4)),
    )
    assert _positions(plan.cibles[0]) == ("A", "B", "C")
    assert _archers_de(plan.cibles[0]) == (1, 2, 3)
    assert all(p.blason_id == 1 for p in plan.cibles[0].placements)
    assert _archers_de(plan.cibles[1]) == (4,)


def test_archers_en_trop_ressortent_en_conflit() -> None:
    """CA (conflits) : sans cible disponible, l'archer non placé est signalé, pas ignoré."""
    plan = placer(_cibles(1), (_archer(1, blason=1, taille=1.0), _archer(2, blason=2, taille=1.0)))
    assert _archers_de(plan.cibles[0]) == (1,)
    assert plan.conflits == (Conflit(archer_id=2, raison=RaisonConflit.NON_PLACE),)


def test_le_plan_liste_toutes_les_cibles_meme_vides() -> None:
    """CA (plan de cibles) : le plan couvre toute la salle, cibles libres comprises."""
    plan = placer(_cibles(4, 4, 4), (_archer(1),))
    assert len(plan.cibles) == 3
    assert plan.cibles[1].placements == ()
    assert plan.cibles[2].placements == ()


def test_sans_archer_les_cibles_sont_listees_vides() -> None:
    """Un départ sans inscrit produit un plan de cibles vides, sans conflit."""
    plan = placer(_cibles(4, 4), ())
    assert plan == PlanDeCibles(
        cibles=(
            CiblePlacee(index=1, capacite=4, placements=()),
            CiblePlacee(index=2, capacite=4, placements=()),
        ),
        conflits=(),
    )


def test_une_cible_ne_mele_pas_deux_hauteurs() -> None:
    """CA hauteur (ADR-0022) : un U11 (110) et un adulte (130) ne partagent pas une cible.

    Malgré l'espace et les positions disponibles, la seconde hauteur bascule sur une cible neuve —
    une butte n'a qu'une hauteur de montage."""
    plan = placer(
        _cibles(4, 4),
        (
            _archer(1, blason=1, taille=0.25, hauteur=130),
            _archer(2, blason=2, taille=0.25, hauteur=110),
        ),
    )
    # Trié par hauteur : le U11 (110) est placé en premier, sur la cible 1 ; l'adulte sur la 2.
    assert _archers_de(plan.cibles[0]) == (2,)
    assert _archers_de(plan.cibles[1]) == (1,)


def test_hauteur_incompatible_sans_cible_libre_est_un_conflit() -> None:
    """CA hauteur : faute de cible libre, l'archer d'une hauteur incompatible ressort en conflit."""
    plan = placer(
        _cibles(4),
        (
            _archer(1, blason=1, taille=0.25, hauteur=110),
            _archer(2, blason=2, taille=0.25, hauteur=130),
        ),
    )
    assert _archers_de(plan.cibles[0]) == (1,)  # le U11, placé
    assert plan.conflits == (Conflit(archer_id=2, raison=RaisonConflit.NON_PLACE),)


def test_placement_est_deterministe() -> None:
    """Règle 9 : à jeu d'archers égal, l'ordre d'entrée n'influe pas sur le plan (tri interne)."""
    archers = tuple(_archer(i, blason=(i % 2) + 1, taille=0.5) for i in range(1, 7))
    cibles = _cibles(4, 4, 4)
    assert placer(cibles, archers) == placer(cibles, tuple(reversed(archers)))


def test_meme_blason_hauteurs_differentes_ne_partagent_pas() -> None:
    """CA hauteur : deux archers du **même** blason mais de hauteurs différentes ne partagent pas.

    La hauteur est vérifiée **avant** la mutualisation de carton : même si le carton pourrait les
    accueillir tous les deux, la seconde hauteur bascule sur une cible neuve."""
    plan = placer(
        _cibles(4, 4),
        (
            _archer(1, blason=7, taille=1.0, capacite_blason=2, hauteur=130),
            _archer(2, blason=7, taille=1.0, capacite_blason=2, hauteur=110),
        ),
    )
    cible_de = {p.archer_id: c.index for c in plan.cibles for p in c.placements}
    assert cible_de[1] != cible_de[2]


def test_partage_de_carton_borne_par_le_plafond_de_positions() -> None:
    """CA (budgets combinés) : la mutualisation d'un carton ne dépasse pas le plafond de positions.

    Blason de capacité 3 sur une cible de capacité 2 → seuls 2 archers, le 3ᵉ bascule **malgré** la
    place restante sur le carton. C'est l'ordre des gardes dans `accueille` qui le garantit."""
    plan = placer(
        _cibles(2, 4),
        tuple(_archer(i, blason=5, taille=0.1, capacite_blason=3) for i in (1, 2, 3)),
    )
    assert _archers_de(plan.cibles[0]) == (1, 2)
    assert _archers_de(plan.cibles[1]) == (3,)


def test_sans_aucune_cible_tous_les_archers_sont_en_conflit() -> None:
    """Fonction pure : sans aucune cible, tous les archers ressortent en conflit `NON_PLACE`."""
    plan = placer((), (_archer(1), _archer(2)))
    assert plan.cibles == ()
    assert plan.conflits == (
        Conflit(archer_id=1, raison=RaisonConflit.NON_PLACE),
        Conflit(archer_id=2, raison=RaisonConflit.NON_PLACE),
    )


# --- Validation d'un déplacement manuel (E03US004, CA « déplacement invalide ») ------------------
# `cible_accepte` répond « ce candidat tiendrait-il sur cette cible déjà peuplée ? » — les quatre
# budgets d'ADR-0023 relus en lecture seule. Un déplacement/échange s'en compose côté service.


def test_cible_accepte_une_place_disponible() -> None:
    """CA : un déplacement sur une cible qui a la place (espace, position, hauteur) est autorisé."""
    (cible,) = _cibles(4)
    occupants = (_archer(1, blason=1, taille=0.5),)
    assert cible_accepte(cible, occupants, _archer(2, blason=2, taille=0.5)) is True


def test_cible_refuse_quand_les_positions_sont_pleines() -> None:
    """CA (budget positions) : une cible pleine en nombre refuse, même s'il reste de l'espace."""
    (cible,) = _cibles(2)
    occupants = (_archer(1, blason=1, taille=0.1), _archer(2, blason=2, taille=0.1))
    assert cible_accepte(cible, occupants, _archer(3, blason=3, taille=0.1)) is False


def test_cible_refuse_une_hauteur_incompatible() -> None:
    """CA (hauteur, ADR-0022) : déplacer un U11 (110) sur une butte d'adultes (130) est refusé."""
    (cible,) = _cibles(4)
    occupants = (_archer(1, blason=1, taille=0.25, hauteur=130),)
    assert cible_accepte(cible, occupants, _archer(2, blason=2, taille=0.25, hauteur=110)) is False


def test_cible_refuse_quand_l_espace_manque() -> None:
    """CA (espace) : un carton neuf qui déborde l'espace restant (0,6 + 0,6 > 1) est refusé."""
    (cible,) = _cibles(4)
    occupants = (_archer(1, blason=1, taille=0.6),)
    assert cible_accepte(cible, occupants, _archer(2, blason=2, taille=0.6)) is False


def test_cible_accepte_le_partage_de_carton_sans_espace_neuf() -> None:
    """CA (budget partage) : un archer rejoint un carton du même blason sans coût d'espace.

    Le carton occupe toute la cible (1,0) mais sa capacité (2) laisse une place : le 2ᵉ du même
    blason est accepté alors même qu'aucun carton neuf ne tiendrait."""
    (cible,) = _cibles(4)
    occupants = (_archer(1, blason=7, taille=1.0, capacite_blason=2),)
    candidat = _archer(2, blason=7, taille=1.0, capacite_blason=2)
    assert cible_accepte(cible, occupants, candidat) is True


def test_cible_refuse_un_carton_plein_sans_espace() -> None:
    """CA (budgets) : carton du blason saturé **et** plus d'espace → refus d'un autre blason."""
    (cible,) = _cibles(4)
    occupants = (_archer(1, blason=7, taille=1.0, capacite_blason=1),)
    assert cible_accepte(cible, occupants, _archer(2, blason=8, taille=0.5)) is False


# --- Placement automatique des restants (E03US004, CA « placer les restants ») -------------------
# `placer_restants` comble les trous du plan avec la réserve, sans déplacer les archers en place.


def test_placer_restants_comble_un_trou_sans_bouger_les_places() -> None:
    """CA : la réserve prend la première case libre ; l'archer déjà placé ne bouge pas."""
    cibles = _cibles(4)
    plan = (CiblePlacee(index=1, capacite=4, placements=(Placement("A", 1, 1),)),)
    donnees = {1: _archer(1, blason=1, taille=0.25), 2: _archer(2, blason=2, taille=0.25)}
    poses, conflits = placer_restants(cibles, plan, donnees, (donnees[2],))
    assert poses == (PoseCalculee(archer_id=2, cible_index=1, position="B"),)
    assert conflits == ()


def test_placer_restants_preserve_une_position_creuse() -> None:
    """CA : un occupant en position B est **préservé** ; la réserve prend A (1ʳᵉ lettre libre)."""
    cibles = _cibles(4)
    plan = (CiblePlacee(index=1, capacite=4, placements=(Placement("B", 1, 1),)),)
    donnees = {1: _archer(1, blason=1, taille=0.25), 2: _archer(2, blason=2, taille=0.25)}
    poses, _ = placer_restants(cibles, plan, donnees, (donnees[2],))
    assert poses == (PoseCalculee(archer_id=2, cible_index=1, position="A"),)


def test_placer_restants_respecte_la_hauteur_de_la_cible() -> None:
    """CA (hauteur) : un U11 de la réserve évite la butte d'adultes montée, va sur une libre."""
    cibles = _cibles(4, 4)
    plan = (
        CiblePlacee(index=1, capacite=4, placements=(Placement("A", 1, 1),)),
        CiblePlacee(index=2, capacite=4, placements=()),
    )
    donnees = {
        1: _archer(1, blason=1, taille=0.25, hauteur=130),
        2: _archer(2, blason=2, taille=0.25, hauteur=110),
    }
    poses, conflits = placer_restants(cibles, plan, donnees, (donnees[2],))
    assert poses == (PoseCalculee(archer_id=2, cible_index=2, position="A"),)
    assert conflits == ()


def test_placer_restants_signale_les_irreductibles() -> None:
    """CA : ce qu'aucune cible ne peut prendre reste en réserve, signalé `NON_PLACE`, pas perdu."""
    cibles = _cibles(1)
    plan = (CiblePlacee(index=1, capacite=1, placements=(Placement("A", 1, 1),)),)
    donnees = {1: _archer(1, blason=1, taille=1.0), 2: _archer(2, blason=2, taille=1.0)}
    poses, conflits = placer_restants(cibles, plan, donnees, (donnees[2],))
    assert poses == ()
    assert conflits == (Conflit(archer_id=2, raison=RaisonConflit.NON_PLACE),)
