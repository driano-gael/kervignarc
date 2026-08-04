"""Tests unitaires du **cloisonnement catégorie/blason** au placement (E03US007) — domaine pur.

Dérivés du CA (« sur une cible, respect du blason associé à la catégorie ; conflits signalés »,
RG-4 « contrainte de placement **activable**, indépendante du type de tournoi ») et des arbitrages
de cadrage du 04/08/2026, **avant** l'implémentation :

- le réglage a **quatre** positions — `aucun` (défaut), `categorie`, `blason`,
  `blason_et_categorie` ;
- activé, il est **dur** : une cible ne mêle jamais deux catégories (resp. blasons) ; ce que le
  cloisonnement empêche de poser part en **réserve** avec une raison, jamais en silence ;
- il ne peut **pas** faire violer une contrainte de rang supérieur (capacité, espace, hauteur) ;
- `aucun` doit rendre le plan d'E03US001 **inchangé** (non-régression stricte).

Le fil rouge du fichier : `categorie` et `blason` **ne sont pas la même contrainte** — deux
catégories peuvent tirer sur le même blason (même `taille`, même carton), et c'est précisément le
cas que le cloisonnement par catégorie doit séparer alors que celui par blason les laisse ensemble.
"""

from __future__ import annotations

from domain.cloisonnement import Cloisonnement
from domain.gabarit_salle import Cible
from domain.placement import (
    ArcherAPlacer,
    CiblePlacee,
    Conflit,
    Placement,
    RaisonConflit,
    cible_accepte,
    cible_cloisonnement_non_respecte,
    placer,
    placer_restants,
)


def _archer(
    archer_id: int,
    *,
    blason: int = 1,
    categorie: int | None = 1,
    taille: float = 0.5,
    capacite_blason: int = 1,
    hauteur: int = 130,
    club: int | None = None,
) -> ArcherAPlacer:
    return ArcherAPlacer(
        archer_id=archer_id,
        blason_id=blason,
        taille=taille,
        capacite_blason=capacite_blason,
        hauteur_cm=hauteur,
        club_id=club,
        categorie_id=categorie,
    )


def _cibles(*capacites: int) -> tuple[Cible, ...]:
    return tuple(Cible(index=index, capacite=cap) for index, cap in enumerate(capacites, start=1))


def _archers_de(cible: CiblePlacee) -> tuple[int, ...]:
    return tuple(p.archer_id for p in cible.placements)


# --- Le réglage par défaut ne change rien (non-régression E03US001) -----------------------------


def test_sans_cloisonnement_deux_blasons_partagent_une_cible() -> None:
    """Défaut `aucun` : deux blasons différents cohabitent tant que l'espace le permet.

    C'est le comportement d'E03US001 — la cible est une face physique de 1,0, deux cartons de 0,5
    y tiennent quels que soient leurs blasons. C'est *cela* que l'US rend interdisable."""
    plan = placer(
        _cibles(2), (_archer(1, blason=1, categorie=1), _archer(2, blason=2, categorie=2))
    )

    assert _archers_de(plan.cibles[0]) == (1, 2)
    assert plan.conflits == ()


# --- Cloisonnement par blason -------------------------------------------------------------------


def test_cloisonnement_blason_separe_deux_blasons_malgre_la_place() -> None:
    """`blason` : un second blason n'entre pas sur une cible déjà entamée, même avec la place."""
    plan = placer(
        _cibles(2, 2),
        (_archer(1, blason=1, categorie=1), _archer(2, blason=2, categorie=2)),
        cloisonnement=Cloisonnement.BLASON,
    )

    assert _archers_de(plan.cibles[0]) == (1,)
    assert _archers_de(plan.cibles[1]) == (2,)
    assert plan.conflits == ()


def test_cloisonnement_blason_laisse_ensemble_deux_categories_du_meme_blason() -> None:
    """`blason` ne cloisonne **que** le blason : deux catégories qui tirent le même carton restent
    ensemble. C'est la différence de fond avec `categorie`, et la raison des quatre positions."""
    plan = placer(
        _cibles(2, 2),
        (_archer(1, blason=1, categorie=1), _archer(2, blason=1, categorie=2)),
        cloisonnement=Cloisonnement.BLASON,
    )

    assert _archers_de(plan.cibles[0]) == (1, 2)


# --- Cloisonnement par catégorie ----------------------------------------------------------------


def test_cloisonnement_categorie_separe_deux_categories_du_meme_blason() -> None:
    """`categorie` : même blason, même hauteur, place disponible — mais catégories différentes, donc
    cibles différentes."""
    plan = placer(
        _cibles(2, 2),
        (_archer(1, blason=1, categorie=1), _archer(2, blason=1, categorie=2)),
        cloisonnement=Cloisonnement.CATEGORIE,
    )

    assert _archers_de(plan.cibles[0]) == (1,)
    assert _archers_de(plan.cibles[1]) == (2,)


def test_cloisonnement_categorie_regroupe_les_archers_d_une_meme_categorie() -> None:
    """L'ordre d'entrée rend les catégories **contiguës** quand le cloisonnement les sépare.

    Sans ce regroupement, le glouton (qui ne revient jamais en arrière, ADR-0023) fermerait une
    cible à chaque alternance : quatre archers en A/B/A/B occuperaient quatre cibles au lieu de
    deux. Le test observe donc le **gaspillage évité**, pas l'ordre de tri lui-même."""
    archers = (
        _archer(1, categorie=1),
        _archer(2, categorie=2),
        _archer(3, categorie=1),
        _archer(4, categorie=2),
    )

    plan = placer(_cibles(2, 2, 2, 2), archers, cloisonnement=Cloisonnement.CATEGORIE)

    assert _archers_de(plan.cibles[0]) == (1, 3)
    assert _archers_de(plan.cibles[1]) == (2, 4)
    assert plan.conflits == ()


def test_categorie_inconnue_n_est_jamais_reputee_identique() -> None:
    """`categorie_id` à `None` = **indécidable** (esprit d'ADR-0014) : jamais « même catégorie ».

    Le cloisonnement étant **dur**, l'indécidable se résout en refus — on ne mêle pas deux archers
    dont on ne peut pas affirmer qu'ils sont de la même catégorie."""
    plan = placer(
        _cibles(2, 2),
        (_archer(1, categorie=None), _archer(2, categorie=None)),
        cloisonnement=Cloisonnement.CATEGORIE,
    )

    assert _archers_de(plan.cibles[0]) == (1,)
    assert _archers_de(plan.cibles[1]) == (2,)


# --- Cloisonnement par blason **et** catégorie --------------------------------------------------


def test_cloisonnement_blason_et_categorie_refuse_des_que_l_un_differe() -> None:
    """`blason_et_categorie` sépare dès qu'une des deux grandeurs diffère (conjonction)."""
    archers = (
        _archer(1, blason=1, categorie=1),
        _archer(2, blason=1, categorie=2),  # même blason, autre catégorie
        _archer(3, blason=2, categorie=1),  # même catégorie, autre blason
    )

    plan = placer(_cibles(3, 3, 3), archers, cloisonnement=Cloisonnement.BLASON_ET_CATEGORIE)

    assert _archers_de(plan.cibles[0]) == (1,)
    assert _archers_de(plan.cibles[1]) == (2,)
    assert _archers_de(plan.cibles[2]) == (3,)


# --- Conflits signalés, jamais d'échec silencieux -----------------------------------------------


def test_archer_que_le_cloisonnement_empeche_de_placer_ressort_en_conflit() -> None:
    """Une seule cible, deux catégories : le second archer est **signalé**, pas perdu (CA
    « conflits »). Le moteur pur ne qualifie pas la cause (`NON_PLACE`) : c'est le service qui
    distingue « saturé » de « cloisonné » à la lecture, là où les deux plans sont comparables."""
    plan = placer(
        _cibles(4),
        (_archer(1, categorie=1), _archer(2, categorie=2)),
        cloisonnement=Cloisonnement.CATEGORIE,
    )

    assert _archers_de(plan.cibles[0]) == (1,)
    assert plan.conflits == (Conflit(archer_id=2, raison=RaisonConflit.NON_PLACE),)


def test_le_cloisonnement_ne_fait_jamais_violer_une_contrainte_de_rang_superieur() -> None:
    """Priorité : capacité / espace / hauteur **avant** cloisonnement (arbitrage de cadrage).

    Deux archers de même catégorie mais de hauteurs différentes restent séparés — le cloisonnement
    ne peut que **retirer** des cohabitations, jamais en autoriser une."""
    plan = placer(
        _cibles(2, 2),
        (_archer(1, categorie=1, hauteur=110), _archer(2, categorie=1, hauteur=130)),
        cloisonnement=Cloisonnement.CATEGORIE,
    )

    assert _archers_de(plan.cibles[0]) == (1,)
    assert _archers_de(plan.cibles[1]) == (2,)


def test_placement_deterministe_sous_cloisonnement() -> None:
    """Même entrée, même plan (règle 9) : le cloisonnement n'introduit aucun aléa."""
    archers = tuple(_archer(i, categorie=1 + i % 3) for i in range(1, 10))
    cibles = _cibles(2, 2, 2, 2, 2)

    premier = placer(cibles, archers, cloisonnement=Cloisonnement.BLASON_ET_CATEGORIE)
    second = placer(cibles, archers, cloisonnement=Cloisonnement.BLASON_ET_CATEGORIE)

    assert premier == second


# --- Ajustement manuel : la même règle vaut au glisser-déposer ----------------------------------


def test_cible_accepte_refuse_un_candidat_d_une_autre_categorie() -> None:
    """`cible_accepte` (validation d'un déplacement manuel, E03US004) applique le cloisonnement.

    Sans cela, la contrainte serait « dure à la génération, molle à la main » — l'admin la
    contournerait d'un geste sans même le savoir."""
    cible = Cible(index=1, capacite=4)
    occupants = (_archer(1, categorie=1),)

    assert cible_accepte(
        cible, occupants, _archer(2, categorie=1), cloisonnement=Cloisonnement.CATEGORIE
    )
    assert not cible_accepte(
        cible, occupants, _archer(2, categorie=2), cloisonnement=Cloisonnement.CATEGORIE
    )
    # Sans réglage, le même geste passe : c'est bien le réglage qui décide, pas la donnée.
    assert cible_accepte(cible, occupants, _archer(2, categorie=2))


def test_placer_restants_respecte_le_cloisonnement() -> None:
    """« Placer les restants » comble les trous **sans** casser le cloisonnement : l'archer d'une
    autre catégorie saute la cible entamée et prend la suivante."""
    cibles = _cibles(2, 2)
    plan_actuel = (
        CiblePlacee(
            index=1,
            capacite=2,
            placements=(Placement(position="A", archer_id=1, blason_id=1),),
        ),
        CiblePlacee(index=2, capacite=2),
    )
    donnees = {1: _archer(1, categorie=1)}
    candidat = _archer(2, categorie=2)

    poses, conflits = placer_restants(
        cibles, plan_actuel, donnees, (candidat,), cloisonnement=Cloisonnement.CATEGORIE
    )

    assert poses[0].cible_index == 2
    assert conflits == ()


# --- Signal sur un plan persisté antérieur au réglage -------------------------------------------


def test_cible_cloisonnement_non_respecte_signale_un_plan_devenu_non_conforme() -> None:
    """Activer le réglage ne déplace personne : un plan déjà posé peut le violer — il est
    **signalé**.

    Propriété **dérivée** (jamais persistée), du même régime que `mixite_non_garantie` (ADR-0047) :
    calculée à la lecture depuis la jointure déjà chargée."""
    melange = (_archer(1, categorie=1), _archer(2, categorie=2))
    homogene = (_archer(1, categorie=1), _archer(2, categorie=1))

    assert cible_cloisonnement_non_respecte(Cloisonnement.CATEGORIE, melange)
    assert not cible_cloisonnement_non_respecte(Cloisonnement.CATEGORIE, homogene)
    # Sans réglage, rien à signaler ; une cible à 0 ou 1 archer est sans objet.
    assert not cible_cloisonnement_non_respecte(Cloisonnement.AUCUN, melange)
    assert not cible_cloisonnement_non_respecte(Cloisonnement.CATEGORIE, melange[:1])
    assert not cible_cloisonnement_non_respecte(Cloisonnement.CATEGORIE, ())


def test_signal_de_cloisonnement_porte_par_le_plan() -> None:
    """Le plan rendu par le moteur porte le drapeau par cible (ce que l'API expose au badge)."""
    plan = placer(
        _cibles(4),
        (_archer(1, categorie=1), _archer(2, categorie=2)),
        cloisonnement=Cloisonnement.AUCUN,
    )
    assert plan.cibles[0].cloisonnement_non_respecte is False

    conforme = placer(
        _cibles(4, 4),
        (_archer(1, categorie=1), _archer(2, categorie=2)),
        cloisonnement=Cloisonnement.CATEGORIE,
    )
    assert all(cible.cloisonnement_non_respecte is False for cible in conforme.cibles)
