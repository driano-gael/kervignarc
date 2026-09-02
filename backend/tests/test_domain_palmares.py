"""Tests unitaires du palmarès (E06US004) — fonction de domaine **pure**.

Dérivés du **CA** de `stories/E06-classements.md` (et non de l'implémentation) :

- **CA « podium »** : les rangs 1-4 sortent de la **finale et de la petite finale**, pas de la
  qualification. Un archer 6ᵉ de qualif qui gagne le tableau est 1ᵉʳ du palmarès ;
- **CA « agrégation »** : les rangs des différentes phases sont **fusionnés** en un classement
  cohérent **par catégorie**. Concrètement : ceux qui ont disputé le tableau occupent les premiers
  rangs, ceux qui n'y sont pas entrés suivent **dans l'ordre de la qualification** ;
- **arbitrage du 03/08/2026** (reversé dans `stories/`) : deux archers sortis **au même tour** ne
  sont départagés par **aucun match** — c'est une **politique injectable** (famille `aggregation`,
  ADR-0004) qui décide. Le défaut `AggregationParQualification` les range sur leur rang de qualif
  (usage World Archery) ; `AggregationExAequo` les laisse *ex æquo* sur une fourchette.

Le palmarès reçoit ce que **chaque phase a décidé** (`ResultatPhase`) et ne rejoue aucun tableau :
la lecture d'un tableau est le travail du service. Ce qui se teste ici est la **règle de fusion**,
pas la reconstruction de l'arbre.
"""

from __future__ import annotations

from domain.classement import Classement, LigneClassement, StatutClassement
from domain.palmares import (
    LignePalmares,
    OriginePalmares,
    Palmares,
    PositionPhase,
    ResultatPhase,
    calculer_palmares,
)
from domain.podium import PorteePodium, ReglagePodiums
from domain.politiques import AggregationExAequo, AggregationParQualification


def _ligne(
    archer_id: int,
    rang: int | None,
    categorie_id: int = 1,
    categorie_libelle: str = "Senior Homme",
    statut: StatutClassement = StatutClassement.EN_LICE,
    rang_categorie: int | None = None,
) -> LigneClassement:
    """Une ligne de classement de qualification, réduite à ce que le palmarès en lit."""
    return LigneClassement(
        rang_scratch=rang,
        rang_categorie=rang_categorie if rang_categorie is not None else rang,
        archer_id=archer_id,
        nom=f"Archer{archer_id}",
        prenom="Jean",
        categorie_id=categorie_id,
        categorie_libelle=categorie_libelle,
        cible=None,
        club_id=1,
        total=600 - archer_id,
        nb_dix=0,
        nb_neuf=0,
        statut=statut,
    )


def _qualification(*lignes: LigneClassement) -> Classement:
    return Classement(lignes=tuple(lignes))


def _huit_archers() -> Classement:
    """Huit archers, qualifiés du 1ᵉʳ au 8ᵉ rang, tous de la même catégorie."""
    return _qualification(*[_ligne(i, i) for i in range(1, 9)])


def _tableau_de_huit_joue() -> ResultatPhase:
    """Un tableau de 8 **entièrement joué**, où le 6ᵉ de qualif l'emporte.

    Rangs 1-4 décernés par les matchs terminaux (finale : 6 puis 1 ; petite finale : 3 puis 2).
    Les quatre battus des quarts ne sont départagés par **aucun** match : ils sortent tous les
    quatre sur la fourchette `[5..8]`, la moitié basse de la plage de leur quart (*Règle R*,
    ADR-0065).
    """
    return ResultatPhase(
        ordre=2,
        positions=(
            PositionPhase(archer_id=6, rang_min=1, rang_max=1),
            PositionPhase(archer_id=1, rang_min=2, rang_max=2),
            PositionPhase(archer_id=3, rang_min=3, rang_max=3),
            PositionPhase(archer_id=2, rang_min=4, rang_max=4),
            PositionPhase(archer_id=4, rang_min=5, rang_max=8),
            PositionPhase(archer_id=5, rang_min=5, rang_max=8),
            PositionPhase(archer_id=7, rang_min=5, rang_max=8),
            PositionPhase(archer_id=8, rang_min=5, rang_max=8),
        ),
    )


def _rangs(palmares: Palmares) -> list[tuple[int, int | None, int | None]]:
    """`(archer_id, rang_min, rang_max)` de chaque ligne, dans l'ordre du palmarès."""
    return [(ligne.archer_id, ligne.rang_min, ligne.rang_max) for ligne in palmares.lignes]


def _ordre(palmares: Palmares) -> list[int]:
    return [ligne.archer_id for ligne in palmares.lignes]


def _podium(palmares: Palmares, categorie_id: int) -> tuple[LignePalmares, ...]:
    """Le podium d'une catégorie, tel qu'E06US004 le rendait.

    `Palmares.podium(categorie_id)` a été généralisé en `podiums(reglage)` par E16US014, qui rend
    des blocs pour trois portées. Cette aide ramène la forme d'avant pour que **l'oracle de ces
    tests ne bouge pas d'un chiffre** : ce qui est vérifié plus bas est le comportement livré, pas
    la nouvelle interface.
    """
    reglage = ReglagePodiums(portees=frozenset({PorteePodium.CATEGORIE}))
    for bloc in palmares.podiums(reglage):
        if bloc.cle == categorie_id:
            return tuple(place.ligne for place in bloc.places)
    return ()


# --- CA « podium » -------------------------------------------------------------------------------


def test_le_podium_sort_des_matchs_terminaux_pas_de_la_qualification() -> None:
    """CA podium : les rangs 1-4 sont ceux de la finale et de la petite finale.

    Le vainqueur du tableau n'était que 6ᵉ de qualification : le palmarès doit le donner 1ᵉʳ, sans
    quoi le classement final ne serait qu'un doublon de la qualification.
    """
    palmares = calculer_palmares(_huit_archers(), (_tableau_de_huit_joue(),))

    assert _ordre(palmares)[:4] == [6, 1, 3, 2]
    assert _rangs(palmares)[:4] == [(6, 1, 1), (1, 2, 2), (3, 3, 3), (2, 4, 4)]


def test_le_podium_est_la_restriction_aux_quatre_premiers() -> None:
    """CA podium : `podium()` est une **vue** du palmarès, pas un second calcul."""
    palmares = calculer_palmares(_huit_archers(), (_tableau_de_huit_joue(),))

    assert [ligne.archer_id for ligne in _podium(palmares, 1)] == [6, 1, 3, 2]


def test_le_podium_ne_retient_que_les_rangs_exacts() -> None:
    """Un archer *ex æquo* 3ᵉ-4ᵉ n'est pas sur le podium : personne ne saurait quelle médaille lui
    remettre. La fourchette est un résultat honnête au classement, pas une place de podium."""
    tableau = ResultatPhase(
        ordre=2,
        positions=(
            PositionPhase(archer_id=1, rang_min=1, rang_max=1),
            PositionPhase(archer_id=2, rang_min=2, rang_max=2),
            PositionPhase(archer_id=3, rang_min=3, rang_max=4),
            PositionPhase(archer_id=4, rang_min=3, rang_max=4),
        ),
    )
    qualification = _qualification(*[_ligne(i, i) for i in range(1, 5)])

    palmares = calculer_palmares(qualification, (tableau,), AggregationExAequo())

    assert [ligne.archer_id for ligne in _podium(palmares, 1)] == [1, 2]


# --- CA « agrégation » ---------------------------------------------------------------------------


def test_les_archers_du_tableau_precedent_ceux_qui_n_y_sont_pas_entres() -> None:
    """CA agrégation : avoir disputé le tableau passe avant tout.

    Les archers 1 à 8 disputent le tableau, 9 et 10 non : le palmarès rend d'abord les huit, dans
    l'ordre que les duels ont décidé, puis les deux autres dans l'ordre de la qualification. Même
    le battu du 1ᵉʳ tour devance le non-qualifié — il a franchi une porte que l'autre n'a pas
    franchie. C'est la fusion demandée par le CA.
    """
    qualification = _qualification(*[_ligne(i, i) for i in range(1, 11)])

    palmares = calculer_palmares(qualification, (_tableau_de_huit_joue(),))

    assert _ordre(palmares) == [6, 1, 3, 2, 4, 5, 7, 8, 9, 10]
    assert _rangs(palmares)[-2:] == [(9, 9, 9), (10, 10, 10)]


def test_les_non_qualifies_sont_renumerotes_sans_trou() -> None:
    """Le palmarès est un classement **1→N contigu** : un rang de qualification manquant (l'archer
    disqualifié en est sorti) ne laisse pas de trou dans le classement final."""
    qualification = _qualification(
        _ligne(1, 1),
        _ligne(2, 2),
        _ligne(3, None, statut=StatutClassement.DISQUALIFIE),
        _ligne(4, 3),
    )
    tableau = ResultatPhase(
        ordre=2,
        positions=(
            PositionPhase(archer_id=2, rang_min=1, rang_max=1),
            PositionPhase(archer_id=1, rang_min=2, rang_max=2),
        ),
    )

    palmares = calculer_palmares(qualification, (tableau,))

    assert _rangs(palmares) == [(2, 1, 1), (1, 2, 2), (4, 3, 3), (3, None, None)]


def test_sans_phase_de_duels_le_palmares_reprend_la_qualification() -> None:
    """Un tournoi qui s'arrête à la qualification a tout de même un palmarès : le sien."""
    palmares = calculer_palmares(_huit_archers(), ())

    assert _ordre(palmares) == [1, 2, 3, 4, 5, 6, 7, 8]
    assert all(ligne.origine is OriginePalmares.QUALIFICATION for ligne in palmares.lignes)


def test_l_origine_du_rang_est_portee_par_la_ligne() -> None:
    """D'où vient le rang — duels ou qualification — se **lit**, il ne se devine pas : c'est ce qui
    permet à l'écran de dire « 9ᵉ (qualification) » sans laisser croire à un duel perdu."""
    qualification = _qualification(*[_ligne(i, i) for i in range(1, 11)])

    palmares = calculer_palmares(qualification, (_tableau_de_huit_joue(),))

    origines = {ligne.archer_id: ligne.origine for ligne in palmares.lignes}
    assert origines[6] is OriginePalmares.DUELS
    assert origines[9] is OriginePalmares.QUALIFICATION


def test_la_phase_la_plus_tardive_l_emporte_pour_un_archer_donne() -> None:
    """Deux phases classantes : c'est la **dernière** disputée qui donne son rang à l'archer.

    Un archer classé 3ᵉ-4ᵉ par la phase d'ordre 2 puis 1ᵉʳ par la phase d'ordre 3 est 1ᵉʳ : le
    rang acquis plus tard **remplace** le précédent, il ne s'y ajoute pas.

    ⚠️ **Ce test disait autrefois autre chose**, et le disait faux. Il fixait aussi l'ordre
    **entre** archers sur l'`ordre` de phase (`DETTE-034`), ce qui plaçait le vainqueur d'une
    consolante devant le finaliste du tableau principal. L'ordre se lit désormais sur le rang
    **absolu** (E05US020, ADR-0068 §5) ; ce test ne garde donc que ce qui était vrai — la règle
    par archer.
    """
    qualification = _qualification(*[_ligne(i, i) for i in range(1, 5)])
    phase2 = ResultatPhase(
        ordre=2,
        positions=(
            PositionPhase(archer_id=1, rang_min=3, rang_max=4),
            PositionPhase(archer_id=3, rang_min=3, rang_max=4),
        ),
    )
    phase3 = ResultatPhase(
        ordre=3,
        positions=(
            PositionPhase(archer_id=3, rang_min=1, rang_max=1),
            PositionPhase(archer_id=1, rang_min=2, rang_max=2),
        ),
    )

    palmares = calculer_palmares(qualification, (phase2, phase3))

    par_archer = {ligne.archer_id: ligne for ligne in palmares.lignes}
    assert (par_archer[3].rang_min, par_archer[3].rang_max) == (1, 1)
    assert (par_archer[1].rang_min, par_archer[1].rang_max) == (2, 2)


# --- CA « agrégation » : départage des sortis au même tour (politique injectable) -----------------


def test_les_sortis_au_meme_tour_sont_departages_par_le_rang_de_qualification() -> None:
    """Politique **par défaut** : aucun match n'ayant départagé les quatre battus des quarts, c'est
    leur rang de qualification qui les ordonne (usage World Archery) — 4, 5, 7, 8 dans cet ordre,
    aux rangs 5, 6, 7 et 8."""
    palmares = calculer_palmares(
        _huit_archers(), (_tableau_de_huit_joue(),), AggregationParQualification()
    )

    assert _rangs(palmares)[4:] == [(4, 5, 5), (5, 6, 6), (7, 7, 7), (8, 8, 8)]


def test_la_politique_ex_aequo_laisse_la_fourchette_partagee() -> None:
    """Politique **ex æquo** : on ne classe que ce que la compétition a décidé. Les quatre battus
    des quarts restent 5ᵉ-8ᵉ, tous les quatre, et aucun n'est dit meilleur qu'un autre."""
    palmares = calculer_palmares(_huit_archers(), (_tableau_de_huit_joue(),), AggregationExAequo())

    assert _rangs(palmares)[4:] == [(4, 5, 8), (5, 5, 8), (7, 5, 8), (8, 5, 8)]


def test_le_departage_ne_decale_pas_les_archers_suivants() -> None:
    """Départager un groupe *ex æquo* redistribue **ses** rangs, sans déplacer personne d'autre :
    les non-qualifiés commencent au même rang dans les deux politiques."""
    qualification = _qualification(*[_ligne(i, i) for i in range(1, 11)])

    par_qualif = calculer_palmares(
        qualification, (_tableau_de_huit_joue(),), AggregationParQualification()
    )
    ex_aequo = calculer_palmares(qualification, (_tableau_de_huit_joue(),), AggregationExAequo())

    assert _rangs(par_qualif)[-2:] == [(9, 9, 9), (10, 10, 10)]
    assert _rangs(ex_aequo)[-2:] == [(9, 9, 9), (10, 10, 10)]


def test_deux_ex_aequo_en_qualification_le_restent_apres_departage() -> None:
    """La politique par défaut départage **sur** la qualification : quand celle-ci les donne déjà
    ex æquo, elle ne dit rien de plus, et l'ex æquo demeure. Départager ici reviendrait à inventer
    un ordre que ni les duels ni la qualification n'ont produit."""
    qualification = _qualification(
        _ligne(1, 1),
        _ligne(2, 2),
        _ligne(3, 3),
        _ligne(4, 3),  # ex æquo 3ᵉ en qualification : même total, mêmes 10 et 9
    )
    tableau = ResultatPhase(
        ordre=2,
        positions=(
            PositionPhase(archer_id=1, rang_min=1, rang_max=1),
            PositionPhase(archer_id=2, rang_min=2, rang_max=2),
            PositionPhase(archer_id=3, rang_min=3, rang_max=4),
            PositionPhase(archer_id=4, rang_min=3, rang_max=4),
        ),
    )

    palmares = calculer_palmares(qualification, (tableau,), AggregationParQualification())

    assert _rangs(palmares)[2:] == [(3, 3, 4), (4, 3, 4)]


# --- CA « par catégorie » ------------------------------------------------------------------------


def test_le_rang_de_categorie_est_recalcule_sur_l_ordre_final() -> None:
    """CA agrégation : le classement est cohérent **par catégorie**.

    Le rang de catégorie ne se recopie pas de la qualification : il repart de 1 sur l'ordre **du
    palmarès**. L'archer 3, 2ᵉ de sa catégorie en qualification, en devient 1ᵉʳ parce qu'il a battu
    en duel celui qui le précédait.
    """
    qualification = _qualification(
        _ligne(1, 1, categorie_id=1, rang_categorie=1),
        _ligne(2, 2, categorie_id=2, rang_categorie=1),
        _ligne(3, 3, categorie_id=1, rang_categorie=2),
        _ligne(4, 4, categorie_id=2, rang_categorie=2),
    )
    tableau = ResultatPhase(
        ordre=2,
        positions=(
            PositionPhase(archer_id=3, rang_min=1, rang_max=1),
            PositionPhase(archer_id=2, rang_min=2, rang_max=2),
            PositionPhase(archer_id=1, rang_min=3, rang_max=3),
            PositionPhase(archer_id=4, rang_min=4, rang_max=4),
        ),
    )

    palmares = calculer_palmares(qualification, (tableau,))

    par_archer = {ligne.archer_id: ligne for ligne in palmares.lignes}
    assert (par_archer[3].rang_categorie_min, par_archer[3].rang_categorie_max) == (1, 1)
    assert (par_archer[1].rang_categorie_min, par_archer[1].rang_categorie_max) == (2, 2)
    assert (par_archer[2].rang_categorie_min, par_archer[2].rang_categorie_max) == (1, 1)
    assert (par_archer[4].rang_categorie_min, par_archer[4].rang_categorie_max) == (2, 2)


def test_le_podium_d_une_categorie_est_celui_de_cette_categorie() -> None:
    """CA podium + catégorie : les médailles se remettent **par catégorie**. Le podium d'une
    catégorie est celui de ses archers, renuméroté de 1 — pas la restriction du podium scratch, qui
    serait vide pour toute catégorie n'ayant personne dans les quatre premiers."""
    qualification = _qualification(
        _ligne(1, 1, categorie_id=1),
        _ligne(2, 2, categorie_id=1),
        _ligne(3, 3, categorie_id=2),
        _ligne(4, 4, categorie_id=2),
    )
    tableau = ResultatPhase(
        ordre=2,
        positions=(
            PositionPhase(archer_id=1, rang_min=1, rang_max=1),
            PositionPhase(archer_id=2, rang_min=2, rang_max=2),
            PositionPhase(archer_id=3, rang_min=3, rang_max=3),
            PositionPhase(archer_id=4, rang_min=4, rang_max=4),
        ),
    )

    palmares = calculer_palmares(qualification, (tableau,))

    assert [ligne.archer_id for ligne in _podium(palmares, 2)] == [3, 4]


def test_le_palmares_se_filtre_sans_perdre_le_rang_scratch() -> None:
    """Comme le classement de qualification (E06US001) : filtrer sur une catégorie **restreint
    l'affichage**, il ne renumérote pas le rang scratch."""
    qualification = _qualification(
        _ligne(1, 1, categorie_id=1),
        _ligne(2, 2, categorie_id=2),
        _ligne(3, 3, categorie_id=1),
    )

    palmares = calculer_palmares(qualification, ()).pour_categorie(1)

    assert _rangs(palmares) == [(1, 1, 1), (3, 3, 3)]


# --- Forfaits : le statut de la qualification est repris -----------------------------------------


def test_l_abandon_reste_relegue_derriere_les_archers_en_lice() -> None:
    """Un archer qui a abandonné est relégué en fin de classement de qualification (ADR-0050) ;
    n'entrant pas au tableau, il le reste au palmarès — derrière tous ceux qui ont fini."""
    qualification = _qualification(
        _ligne(1, 1),
        _ligne(2, 3, statut=StatutClassement.ABANDON),
        _ligne(3, 2),
    )

    palmares = calculer_palmares(qualification, ())

    assert _ordre(palmares) == [1, 3, 2]
    assert palmares.lignes[-1].statut is StatutClassement.ABANDON


def test_le_disqualifie_reste_hors_du_palmares() -> None:
    """Un disqualifié est **sorti** du classement (ADR-0050) : pas de rang, listé en dernier. Lui en
    donner un au palmarès le réintégrerait par la bande."""
    qualification = _qualification(
        _ligne(1, 1),
        _ligne(2, None, statut=StatutClassement.DISQUALIFIE),
        _ligne(3, 2),
    )

    palmares = calculer_palmares(qualification, ())

    assert _rangs(palmares) == [(1, 1, 1), (3, 2, 2), (2, None, None)]
    assert palmares.lignes[-1].rang_categorie_min is None


def test_un_resultat_de_phase_ignore_les_archers_inconnus_de_la_qualification() -> None:
    """Le palmarès liste **les archers du tournoi**. Une position portant un archer absent du
    classement (donnée incohérente) est ignorée plutôt que de faire naître une ligne anonyme."""
    qualification = _qualification(_ligne(1, 1), _ligne(2, 2))
    tableau = ResultatPhase(
        ordre=2,
        positions=(
            PositionPhase(archer_id=2, rang_min=1, rang_max=1),
            PositionPhase(archer_id=99, rang_min=2, rang_max=2),
        ),
    )

    palmares = calculer_palmares(qualification, (tableau,))

    assert _ordre(palmares) == [2, 1]


# --- CA « podium » : ce qu'aucun match n'a décerné n'est pas une médaille -------------------------
# Les trois cas ci-dessous ont été **trouvés en revue** (axes B, C1 et adversarial) : chacun
# décernait de l'or que la compétition n'avait pas produit, et aucun test ne les voyait.


def test_sans_phase_de_duels_aucun_podium_n_est_decerne() -> None:
    """CA podium : « rangs 1-4 issus de la **finale/petite finale** ».

    Un rang de qualification est exact par construction — sans garde, le podium se remplissait
    donc sur les seuls scores du matin, et l'écran public décernait « Or / Argent / Bronze » avant
    le moindre duel. Ce n'est pas un cas limite : c'est l'état du tournoi pendant toute la
    matinée.
    """
    palmares = calculer_palmares(_huit_archers(), ())

    assert _podium(palmares, 1) == ()
    assert all(not ligne.decerne for ligne in palmares.lignes)


def test_le_vainqueur_d_une_demi_finale_n_a_pas_encore_l_or() -> None:
    """Deux demi-finales ne se valident **jamais au même instant**.

    Entre les deux, le vainqueur de la première est seul sur sa position `[1..2]` : la
    renumérotation lui donnait un rang **exact** — donc « 1ᵉʳ », médaille comprise — alors que la
    finale n'est pas tirée. Le drapeau `en_lice` protégeait le *groupement*, pas la
    *numérotation* (défaut trouvé en revue, axe adversarial).

    Attendu : il garde sa fourchette acquise « 1ᵉʳ-2ᵉ », et le podium reste vide.
    """
    qualification = _qualification(*[_ligne(i, i) for i in range(1, 5)])
    tableau = ResultatPhase(
        ordre=2,
        positions=(
            PositionPhase(archer_id=1, rang_min=1, rang_max=2, en_lice=True),
            PositionPhase(archer_id=2, rang_min=1, rang_max=4, en_lice=True),
            PositionPhase(archer_id=3, rang_min=1, rang_max=4, en_lice=True),
            PositionPhase(archer_id=4, rang_min=3, rang_max=4, en_lice=True),
        ),
    )

    palmares = calculer_palmares(qualification, (tableau,))

    par_archer = {ligne.archer_id: ligne for ligne in palmares.lignes}
    assert (par_archer[1].rang_min, par_archer[1].rang_max) == (1, 2)
    assert not par_archer[1].decerne
    assert _podium(palmares, 1) == ()


def test_deux_finalistes_ne_sont_pas_departages_par_la_politique() -> None:
    """CA départage : « le départage ne s'applique **qu'à ce qui est joué** ».

    La règle vit dans le domaine ; elle n'était couverte que par un test de service. Deux
    finalistes partagent « 1ᵉʳ-2ᵉ » — leur rang de qualification n'a pas le droit de trancher.
    """
    qualification = _qualification(_ligne(1, 1), _ligne(2, 2))
    tableau = ResultatPhase(
        ordre=2,
        positions=(
            PositionPhase(archer_id=1, rang_min=1, rang_max=2, en_lice=True),
            PositionPhase(archer_id=2, rang_min=1, rang_max=2, en_lice=True),
        ),
    )

    palmares = calculer_palmares(qualification, (tableau,), AggregationParQualification())

    assert _rangs(palmares) == [(1, 1, 2), (2, 1, 2)]


def test_un_groupe_mixte_en_lice_n_est_pas_departage() -> None:
    """Un seul membre encore en lice suffit à geler tout le groupe : tant qu'un match peut
    trancher, la politique n'a rien à décider."""
    qualification = _qualification(_ligne(1, 1), _ligne(2, 2))
    tableau = ResultatPhase(
        ordre=2,
        positions=(
            PositionPhase(archer_id=1, rang_min=1, rang_max=2, en_lice=True),
            PositionPhase(archer_id=2, rang_min=1, rang_max=2, en_lice=False),
        ),
    )

    palmares = calculer_palmares(qualification, (tableau,), AggregationParQualification())

    assert _rangs(palmares) == [(1, 1, 2), (2, 1, 2)]


def test_un_disqualifie_ne_prend_pas_une_position_de_phase() -> None:
    """Un disqualifié est **sorti** du classement (ADR-0050) : une position de phase ne l'y
    ramène pas.

    L'invariant est tenu en amont par l'ensemencement du tableau (seuls les archers en lice y
    entrent), mais ADR-0067 promet de brancher d'autres producteurs de `ResultatPhase` « sans
    toucher au domaine » — ceux-là n'auront aucune raison de refaire le filtre. Sans cette garde,
    un DSQ prenait le rang 1 et l'or (relevé en revue, axe adversarial).
    """
    qualification = _qualification(
        _ligne(1, 1),
        _ligne(2, None, statut=StatutClassement.DISQUALIFIE),
    )
    tableau = ResultatPhase(
        ordre=2, positions=(PositionPhase(archer_id=2, rang_min=1, rang_max=1),)
    )

    palmares = calculer_palmares(qualification, (tableau,))

    assert _rangs(palmares) == [(1, 1, 1), (2, None, None)]
    assert _podium(palmares, 1) == ()


def test_un_archer_sans_rang_de_qualification_passe_en_dernier() -> None:
    """`AggregationParQualification` départage **sur** la qualification : celui dont elle ne dit
    rien passe derrière, et deux sans-rang restent ensemble. Affirmé en docstring, épinglé ici."""
    groupe = [7, 8, 9]
    paquets = AggregationParQualification().departager(groupe, {7: None, 8: 3, 9: None})

    assert paquets == ((8,), (7, 9))


def test_un_rang_tranche_par_la_politique_monte_au_podium_mais_le_dit() -> None:
    """Un rang **définitif** vaut une place ; `decerne` dit s'il a été **gagné au tir**.

    Les deux battus des demies d'un tableau tronqué reçoivent 3ᵉ et 4ᵉ de la politique
    `AggregationParQualification`. Aucun match ne les a départagés — mais leur rang ne bougera
    plus. Arbitrage du commanditaire (03/08/2026) : ils montent sur le podium, et l'écran comme le
    PDF **disent** que la place vient du classement. Exiger un match amputait la majorité des
    catégories de leurs médailles, le moteur ne montant qu'un seul tableau scratch (DETTE-028).
    """
    qualification = _qualification(*[_ligne(i, i) for i in range(1, 5)])
    tableau = ResultatPhase(
        ordre=2,
        positions=(
            PositionPhase(archer_id=1, rang_min=1, rang_max=1),
            PositionPhase(archer_id=2, rang_min=2, rang_max=2),
            PositionPhase(archer_id=3, rang_min=3, rang_max=4),
            PositionPhase(archer_id=4, rang_min=3, rang_max=4),
        ),
    )

    palmares = calculer_palmares(qualification, (tableau,), AggregationParQualification())

    assert _rangs(palmares)[2:] == [(3, 3, 3), (4, 4, 4)]
    assert [ligne.archer_id for ligne in _podium(palmares, 1)] == [1, 2, 3, 4]
    par_archer = {ligne.archer_id: ligne for ligne in palmares.lignes}
    assert par_archer[1].decerne and par_archer[2].decerne
    assert not par_archer[3].decerne and not par_archer[4].decerne


# --- CA E05US020 : une phase dispute une TRANCHE de rangs, pas toujours la victoire ------------


def test_le_vainqueur_d_une_consolante_ne_passe_pas_devant_le_finaliste() -> None:
    """Une phase qui prélève « les rangs 5 et suivants » dispute les places **5 et au-delà**.

    Son vainqueur est 5ᵉ du tournoi, pas 1ᵉʳ. Sans cette notion de **tranche**, le palmarès situait
    chaque archer par l'`ordre` de sa phase — « la plus tardive l'emporte » — et couronnait donc le
    vainqueur de la **consolante** (phase 3) devant le finaliste du tableau principal (phase 2).

    Le défaut était inatteignable tant qu'aucun moteur ne consommait les prélèvements ; E05US020 l'a
    rendu atteignable, et la revue adversariale l'a mesuré sur un déroulé que `verifier_sequence`
    **accepte**. C'est `DETTE-034`, ici résorbée.
    """
    qualification = _qualification(*[_ligne(i, i) for i in range(1, 9)])
    principal = ResultatPhase(
        ordre=2,
        rang_premier=1,
        positions=(
            PositionPhase(archer_id=1, rang_min=1, rang_max=1),
            PositionPhase(archer_id=2, rang_min=2, rang_max=2),
            PositionPhase(archer_id=3, rang_min=3, rang_max=3),
            PositionPhase(archer_id=4, rang_min=4, rang_max=4),
        ),
    )
    consolante = ResultatPhase(
        ordre=3,
        rang_premier=5,
        positions=(
            PositionPhase(archer_id=5, rang_min=1, rang_max=1),
            PositionPhase(archer_id=6, rang_min=2, rang_max=2),
            PositionPhase(archer_id=7, rang_min=3, rang_max=3),
            PositionPhase(archer_id=8, rang_min=4, rang_max=4),
        ),
    )

    palmares = calculer_palmares(qualification, (principal, consolante))

    assert _ordre(palmares) == [1, 2, 3, 4, 5, 6, 7, 8]
    assert _rangs(palmares)[4] == (5, 5, 5)


def test_sans_tranche_declaree_une_phase_dispute_le_tournoi_entier() -> None:
    """Le défaut : une phase sans prélèvement lisible dispute les rangs 1→N (`rang_premier=1`)."""
    palmares = calculer_palmares(_huit_archers(), (_tableau_de_huit_joue(),))

    assert _rangs(palmares)[:2] == [(6, 1, 1), (1, 2, 2)]
