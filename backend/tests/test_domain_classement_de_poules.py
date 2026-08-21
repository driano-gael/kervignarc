"""Le **classement d'une phase de poules** — « par rang de poule d'abord » (E05US023).

ADR-0083 §6.

⚠️ **Ces tests sont écrits depuis le CA, avant l'implémentation** (règle 9). L'oracle est la puce
« **CA — le classement de phase se lit "par rang de poule d'abord"** » de
`stories/E05-moteur-phases.md`, complétée de ses trois sous-puces et de la puce « **CA — un
prélèvement qui coupe un bloc de poules est refusé** ». Aucun des oracles ci-dessous n'a été relu
dans `domain/classement_de_poules.py` — il n'existait pas quand ce fichier a été écrit.

Les quatre propriétés que le CA impose, et qu'on éprouve une par une :

1. **L'ordre** : sur `P` poules, les rangs `1..P` sont les vainqueurs, `P+1..2P` les deuxièmes.
2. **Tout le monde y figure**, y compris au-delà de la barre de qualification, et le dernier bloc
   peut être **incomplet** (les surnuméraires vont en dernier).
3. **Un bloc est indécis** par défaut : c'est ce qui arme ADR-0081 et fait refuser une fenêtre qui
   le coupe. Le **départage optionnel** par décompte le referme.
4. **Un ex æquo interne à une poule** qui enjambe deux blocs rend ces blocs indécis **ensemble** —
   sans quoi on prétendrait savoir qui est 3ᵉ de sa poule alors que la poule ne le dit pas.

[ADR-0083]: ../../docs/adr/0083-le-contrat-de-phase-jouable.md
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from domain.classement import LigneClassement, StatutClassement
from domain.classement_de_poules import classement_de_poules
from domain.classement_de_tableau import ClassementSource
from domain.participant import Participant
from domain.politiques import DecompteDepartage, TiebreakPoules
from domain.poule import ModeDeComposition, RangPoule


def _ligne(archer_id: int) -> LigneClassement:
    """Une ligne de qualification quelconque : seule l'identité compte ici."""
    return LigneClassement(
        rang_scratch=archer_id,
        rang_categorie=archer_id,
        archer_id=archer_id,
        nom=f"N{archer_id}",
        prenom="P",
        categorie_id=1,
        categorie_libelle="Cat",
        cible=None,
        club_id=None,
        total=0,
        nb_dix=0,
        nb_neuf=0,
    )


def _decompte(points: int) -> DecompteDepartage:
    """Un décompte que `TiebreakPoules` ordonne par son **premier** critère, les points de match."""
    return DecompteDepartage(nb_dix=0, nb_neuf=0, points_match=points)


def _poule(*archers: int, decomptes: tuple[int, ...] | None = None) -> tuple[RangPoule, ...]:
    """Le classement d'une poule : les archers dans l'ordre, rangs 1..n, aucun ex æquo."""
    points = decomptes if decomptes is not None else tuple(range(len(archers), 0, -1))
    return tuple(
        RangPoule(rang=index, participant=Participant.individuel(archer), decompte=_decompte(pts))
        for index, (archer, pts) in enumerate(zip(archers, points, strict=True), start=1)
    )


def _ex_aequo(*archers: int, rangs: tuple[int, ...]) -> tuple[RangPoule, ...]:
    """Le classement d'une poule où `rangs` porte des doublons — les ex æquo du §10.1."""
    return tuple(
        RangPoule(
            rang=rang,
            participant=Participant.individuel(archer),
            decompte=_decompte(10 - rang),
            ex_aequo=rangs.count(rang) > 1,
        )
        for archer, rang in zip(archers, rangs, strict=True)
    )


def _lignes(*archers: int) -> dict[int, LigneClassement]:
    return {archer: _ligne(archer) for archer in archers}


def _rangs(source: ClassementSource) -> list[tuple[int | None, int]]:
    """`(rang_scratch, archer_id)` du classement rendu — la forme que `preleves` consomme."""
    return [(ligne.rang_scratch, ligne.archer_id) for ligne in source.classement.lignes]


def _ordre(source: ClassementSource) -> list[int]:
    return [ligne.archer_id for ligne in source.classement.lignes]


# --- 1. L'ordre : par rang de poule d'abord -------------------------------------------------------


def test_les_vainqueurs_de_poule_occupent_les_premiers_rangs() -> None:
    """CA — « sur `P` poules, les rangs `1..P` sont les vainqueurs, `P+1..2P` les deuxièmes ».

    L'exemple est celui du CA, verbatim : **4 poules de 3** → rangs 1-4 les premiers de poule, 5-8
    les deuxièmes, 9-12 les troisièmes.
    """
    classements: Sequence[Sequence[RangPoule]] = [
        _poule(1, 5, 9),
        _poule(2, 6, 10),
        _poule(3, 7, 11),
        _poule(4, 8, 12),
    ]
    source = classement_de_poules(
        classements, _lignes(*range(1, 13)), mode=ModeDeComposition.SERPENT
    )

    assert _rangs(source) == [(rang, rang) for rang in range(1, 13)]


def test_les_poules_se_jouent_en_parallele_donc_aucune_ne_precede_une_autre() -> None:
    """CA — « les poules se jouent **en parallèle** et donnent donc le même classement ».

    Contre-oracle explicite : concaténer poule après poule (1,2,3 puis 4,5,6) est **la** faute que
    ce CA interdit. Le 2ᵉ de la poule 1 ne doit pas devancer le vainqueur de la poule 2.
    """
    source = classement_de_poules(
        [_poule(1, 2, 3), _poule(4, 5, 6)],
        _lignes(1, 2, 3, 4, 5, 6),
        mode=ModeDeComposition.SERPENT,
    )

    assert _ordre(source) == [1, 4, 2, 5, 3, 6]


# --- 2. Tout le monde y figure, surnuméraires en dernier ------------------------------------------


def test_le_classement_porte_aussi_les_archers_sous_la_barre_de_qualification() -> None:
    """CA — « Tout le monde y figure, pas seulement les qualifiés ».

    C'est le **prélèvement** de la phase avale qui sélectionne, pas le classement qui tronque : une
    consolante « les rangs 9 à 16 » doit être composable sans réglage neuf. L'exemple du CA est
    `nb_qualifies = 2` sur 4 poules de 4 → les 3ᵉˢ en 9-12, les 4ᵉˢ en 13-16.
    """
    classements: Sequence[Sequence[RangPoule]] = [
        _poule(1, 5, 9, 13),
        _poule(2, 6, 10, 14),
        _poule(3, 7, 11, 15),
        _poule(4, 8, 12, 16),
    ]
    source = classement_de_poules(
        classements, _lignes(*range(1, 17)), mode=ModeDeComposition.SERPENT
    )

    assert len(source.classement.lignes) == 16
    assert [archer for rang, archer in _rangs(source) if rang is not None and 9 <= rang <= 12] == [
        9,
        10,
        11,
        12,
    ]
    assert [archer for rang, archer in _rangs(source) if rang is not None and 13 <= rang <= 16] == [
        13,
        14,
        15,
        16,
    ]


def test_le_dernier_bloc_peut_etre_incomplet_et_les_surnumeraires_vont_en_dernier() -> None:
    """CA — « 30 archers en poules de 4 donnent 7 poules (cinq de 4, deux de 5), donc les rangs
    29-30 ne portent que les **5ᵉˢ des deux poules de 5** ».

    On reproduit la forme, en plus petit et lisible : trois poules, deux de 3 et une de 4. Le 4ᵉ
    bloc n'a qu'un occupant, et il occupe le dernier rang.
    """
    classements: Sequence[Sequence[RangPoule]] = [
        _poule(1, 4, 7),
        _poule(2, 5, 8),
        _poule(3, 6, 9, 10),
    ]
    source = classement_de_poules(
        classements, _lignes(*range(1, 11)), mode=ModeDeComposition.SERPENT
    )

    assert _ordre(source) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert _rangs(source)[-1] == (10, 10)


# --- 3. Un bloc est indécis, sauf départage ------------------------------------------------------


def test_chaque_bloc_est_indecis_par_defaut() -> None:
    """CA — « À l'intérieur d'un bloc, les archers sont ex æquo par défaut ».

    Conséquence exigée par la puce suivante du CA : sur 4 poules, « les rangs 1 à 4 » **contient**
    le bloc des vainqueurs et passe ; « les rangs 1 à 2 » le **coupe** et doit être refusé. C'est
    `ClassementSource.coupe` qui répond, à condition que le bloc soit déclaré indécis.
    """
    classements: Sequence[Sequence[RangPoule]] = [
        _poule(1, 5),
        _poule(2, 6),
        _poule(3, 7),
        _poule(4, 8),
    ]
    source = classement_de_poules(
        classements, _lignes(*range(1, 9)), mode=ModeDeComposition.SERPENT
    )

    assert source.plages_indecises == ((1, 4), (5, 8))
    assert source.coupe(1, 4) is None
    assert source.coupe(1, 2) == (1, 4)


def test_un_bloc_a_un_seul_occupant_nest_pas_indecis() -> None:
    """Corollaire du CA : à **une** poule, il n'y a rien à départager entre blocs.

    Le classement de la phase *est* celui de la poule, rang par rang — aucune fenêtre n'y coupe
    quoi que ce soit.
    """
    source = classement_de_poules(
        [_poule(1, 2, 3)], _lignes(1, 2, 3), mode=ModeDeComposition.SERPENT
    )

    assert source.plages_indecises == ()
    assert source.coupe(1, 1) is None


def test_le_departage_optionnel_referme_les_blocs_par_le_decompte() -> None:
    """CA — « Un **départage optionnel** par décompte affine le classement si l'organisateur le
    demande » (les cinq critères du référentiel §10.1).

    Deux poules de deux. Les deux vainqueurs ont des décomptes distincts (7 points de match contre
    9) : le départage doit les ordonner **par le décompte**, pas par le numéro de poule, et le bloc
    cesse d'être indécis.
    """
    classements: Sequence[Sequence[RangPoule]] = [
        _poule(1, 3, decomptes=(7, 2)),
        _poule(2, 4, decomptes=(9, 1)),
    ]
    source = classement_de_poules(
        classements, _lignes(1, 2, 3, 4), departage=TiebreakPoules(), mode=ModeDeComposition.SERPENT
    )

    assert _ordre(source) == [2, 1, 3, 4]
    assert source.plages_indecises == ()
    assert source.coupe(1, 1) is None


def test_le_departage_ne_ferme_pas_ce_que_le_decompte_ne_separe_pas() -> None:
    """CA — le départage est « par décompte » : deux décomptes **identiques** restent ex æquo.

    L'option n'est pas un ordre arbitraire de secours ; elle affine là où les cinq critères parlent,
    et se tait ailleurs. Sur trois poules dont deux vainqueurs à 9 et un à 7, le premier bloc n'est
    indécis que sur les deux premiers.
    """
    classements: Sequence[Sequence[RangPoule]] = [
        _poule(1, 4, decomptes=(9, 1)),
        _poule(2, 5, decomptes=(9, 1)),
        _poule(3, 6, decomptes=(7, 1)),
    ]
    source = classement_de_poules(
        classements,
        _lignes(1, 2, 3, 4, 5, 6),
        departage=TiebreakPoules(),
        mode=ModeDeComposition.SERPENT,
    )

    assert source.plages_indecises == ((1, 2), (4, 6))
    assert source.coupe(1, 2) is None
    assert source.coupe(1, 1) == (1, 2)


# --- 4. Un ex æquo interne à une poule enjambe deux blocs -----------------------------------------


def test_un_ex_aequo_interne_a_une_poule_lie_les_blocs_quil_enjambe() -> None:
    """CA §5 — « deux archers à égalité aux rangs 3-4 d'une poule qui en qualifie 2 **restent à
    égalité** », et le classement de phase doit le dire.

    Ces deux-là occupent le 3ᵉ et le 4ᵉ bloc. Prétendre que le premier est « 3ᵉ de sa poule »
    reviendrait à qualifier sur l'ordre d'affichage — la faute même que `qualifies_de_poule` refuse.
    Départage activé, donc les blocs eux-mêmes sont fermés : ce qui reste indécis vient **du seul**
    ex æquo interne, et il court du rang 5 au rang 7.
    """
    classements: Sequence[Sequence[RangPoule]] = [
        _ex_aequo(1, 3, 5, 7, rangs=(1, 2, 3, 3)),
        _poule(2, 4, 6, 8),
    ]
    source = classement_de_poules(
        classements,
        _lignes(*range(1, 9)),
        departage=TiebreakPoules(),
        mode=ModeDeComposition.SERPENT,
    )

    assert source.plages_indecises == ((5, 7),)
    assert source.coupe(5, 6) == (5, 7)
    assert source.coupe(5, 7) is None
    # La fusion est **locale** : sans cette borne, un ex æquo de fond de poule rendrait toute la
    # phase illisible et refuserait des prélèvements décidés — le « refus abusif » d'E05US021.
    assert source.coupe(1, 2) is None
    assert source.coupe(3, 4) is None


def test_sans_departage_lex_aequo_interne_soude_les_deux_blocs_entiers() -> None:
    """Le cas nominal : sans départage, les blocs 3 et 4 étaient déjà indécis chacun de son côté.

    L'ex æquo interne les **soude** — sans quoi « les rangs 5 à 6 » passerait, en prenant le 3ᵉ de
    la poule 1 pour un 3ᵉ avéré. C'est exactement la population « plausible et fausse » d'ADR-0081.
    """
    classements: Sequence[Sequence[RangPoule]] = [
        _ex_aequo(1, 3, 5, 7, rangs=(1, 2, 3, 3)),
        _poule(2, 4, 6, 8),
    ]
    source = classement_de_poules(
        classements, _lignes(*range(1, 9)), mode=ModeDeComposition.SERPENT
    )

    assert source.plages_indecises == ((1, 2), (3, 4), (5, 8))
    assert source.coupe(5, 6) == (5, 8)


# --- Bordures ------------------------------------------------------------------------------------


def test_un_archer_sans_ligne_de_classement_est_ecarte_sans_trouer_les_rangs() -> None:
    """Même parti que `classement_de_tableau` : les rangs rendus doivent exister.

    Un participant dont la ligne manque (équipe — ADR-0028 — ou archer retiré du créneau) sort du
    classement, et les rangs se renumérotent **sans trou** : `preleves` lit `rang_scratch`, une
    numérotation trouée y ferait manquer des archers à une fenêtre par ailleurs correcte.
    """
    source = classement_de_poules(
        [_poule(1, 3), _poule(2, 4)], _lignes(1, 2, 4), mode=ModeDeComposition.SERPENT
    )

    assert _rangs(source) == [(1, 1), (2, 2), (3, 4)]


def test_une_phase_sans_aucun_participant_rend_un_classement_vide() -> None:
    """Aucune poule composée : rien à classer, et surtout aucune plage à déclarer indécise."""
    source = classement_de_poules([], {}, mode=ModeDeComposition.SERPENT)

    assert source.classement.lignes == ()
    assert source.plages_indecises == ()


def test_le_statut_est_remis_en_lice_comme_pour_un_tableau() -> None:
    """Un archer présent dans une poule y a sa place, quoi que la qualification ait dit de lui.

    Le filtre des sortis a déjà eu lieu à l'entrée de la phase (`preleves` ne prélève que les
    `EN_LICE`) ; le rejouer ici retirerait deux fois le même archer — le raisonnement de
    `classement_de_tableau._situee`, repris tel quel.
    """
    lignes = _lignes(1, 2)
    lignes[2] = replace(lignes[2], statut=StatutClassement.ABANDON)
    source = classement_de_poules([_poule(1), _poule(2)], lignes, mode=ModeDeComposition.SERPENT)

    assert [ligne.statut for ligne in source.classement.lignes] == [
        StatutClassement.EN_LICE,
        StatutClassement.EN_LICE,
    ]
