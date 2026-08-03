"""Tests du tableau d'élimination directe (E05US005) — dérivés des CA, pas de l'implémentation.

Règle 9 : ces cas dérivent des **cinq puces CA** d'E05US005 (`stories/E05-moteur-phases.md`) et des
règles écrites (`moteur-placement-lucky-loser.md` §2/§5, `docs/referentiel-ffta.md` §10) — jamais du
code, qui n'existait pas quand ils ont été écrits. Le moteur **orchestre** les politiques pures déjà
livrées en E05US003 : `SeedingSerpent`, `ByesAuxMieuxClasses`, `EliminationSeche`.

Le moteur oppose des `Participant` (ADR-0028, E13US001), pas des rangs : ici chaque participant est
un archer dont on fixe `ref_id = rang` (le participant `p(r)` occupe la tête de série n°`r`), pour
des assertions lisibles. Le mapping rang → participant vit dans les couches hautes ; le moteur ne
lit qu'une identité opaque.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import pytest

from domain.erreurs import (
    EffectifTableauInvalide,
    MatchIntrouvable,
    MatchNonJouable,
    RoutingNonSupporte,
    VainqueurHorsMatch,
)
from domain.participant import Participant
from domain.politiques import (
    ByesAuxMieuxClasses,
    ContexteRoutage,
    Destination,
    EliminationSeche,
    PlacementEnCascade,
    ProfondeurPodium,
    ProfondeurUnVersN,
    RoutingRepechage,
    SeedingSerpent,
)
from domain.tableau import (
    Exempt,
    PerdantDe,
    Place,
    Tableau,
    TeteDeSerie,
    VainqueurDe,
    construire_tableau,
    libelle_tour,
    paires_du_premier_tour,
)

SEEDING = SeedingSerpent()
BYES = ByesAuxMieuxClasses()
# Le format décrit par ce module — élimination directe **avec petite finale** — est, depuis
# E05US010, un placement en cascade tronqué au rang 4 (la profondeur `podium`, défaut de
# `construire_tableau`). Même arbre, même numérotation : c'est le contrat de non-régression.
ROUTING = PlacementEnCascade()
# La profondeur qui reproduit le format d'E05US005 : on ne départage que le podium.
DEPTH = ProfondeurPodium()


def p(rang: int) -> Participant:
    """Le participant à ce rang de qualification (`ref_id = rang` pour des tests lisibles)."""
    return Participant.individuel(rang)


def construire(effectif: int) -> Tableau:
    """Assemble un tableau pour `effectif` participants ordonnés par rang (p(1) = tête de série)."""
    return construire_tableau([p(r) for r in range(1, effectif + 1)], SEEDING, BYES, ROUTING, DEPTH)


def _appariements_premier_tour(
    tableau: Tableau,
) -> list[tuple[Participant | None, Participant | None]]:
    """Les couples (haut, bas) des matchs du premier tour, dans l'ordre de numérotation."""
    return [(m.haut, m.bas) for m in tableau.matchs if m.tour == 1]


def jouer_gagne_mieux_classe(tableau: Tableau, numero: int) -> Tableau:
    """Fait gagner le **mieux classé** (plus petit rang) du match `numero` — scénario stable."""
    m = tableau.match(numero)
    assert m.haut is not None and m.bas is not None
    mieux = m.haut if m.haut.ref_id < m.bas.ref_id else m.bas
    return tableau.jouer(numero, mieux)


# --- CA « dimensionnement & seeding » ----------------------------------------------------------
# moteur-placement-lucky-loser.md §2 : effectif → puissance de 2 supérieure ; seeding serpent, le
# rang r affronte 2^k+1-r ; référentiel §10 (décision projet, 32/16 places FFTA).


@pytest.mark.parametrize(
    ("effectif", "taille"),
    [(2, 2), (3, 4), (4, 4), (5, 8), (8, 8), (9, 16), (16, 16), (17, 32)],
)
def test_taille_arrondie_a_la_puissance_de_deux_superieure(effectif: int, taille: int) -> None:
    assert construire(effectif).taille == taille


def test_premier_tour_suit_l_ordre_serpent_sans_exempt() -> None:
    # Effectif = puissance de 2 exacte : aucun exempt, les appariements sont l'ordre serpent brut.
    appariements = _appariements_premier_tour(construire(8))
    assert appariements == [(p(1), p(8)), (p(4), p(5)), (p(2), p(7)), (p(3), p(6))]
    # Chaque match du premier tour oppose r et 2^k+1-r (somme constante) — invariant du serpent.
    for haut, bas in appariements:
        assert haut is not None and bas is not None
        assert haut.ref_id + bas.ref_id == 9


def test_seeding_serpent_place_les_tetes_pour_se_croiser_le_plus_tard() -> None:
    # Sur un tableau de 16, la tête 1 et la tête 2 ne peuvent se rencontrer qu'en finale : elles
    # partent dans des demi-tableaux opposés (premier match 1 vs 16, la tête 2 dans l'autre moitié).
    tableau = construire(16)
    premier = tableau.match(1)
    assert (premier.haut, premier.bas) == (p(1), p(16))
    # La tête 2 n'apparaît pas dans la première moitié des matchs du premier tour.
    matchs_t1 = [m for m in tableau.matchs if m.tour == 1]
    premiere_moitie = matchs_t1[: len(matchs_t1) // 2]
    assert all(p(2) not in (m.haut, m.bas) for m in premiere_moitie)


def test_effectif_inferieur_a_deux_refuse() -> None:
    # Un tableau oppose au moins deux tireurs : à un seul, il n'y a pas de duel à disputer.
    with pytest.raises(EffectifTableauInvalide):
        construire(1)


# --- CA E03US009 « paires du premier tour » (source des duels à placer côte à côte) -------------


def test_paires_du_premier_tour_donne_les_duels_disputes() -> None:
    # Effectif = puissance de 2 : tous les matchs du 1er tour sont disputés (aucun exempt).
    # Le serpent oppose r et 2^k+1-r (cf. test_premier_tour_suit_l_ordre_serpent) : (1,4) et (2,3).
    paires = paires_du_premier_tour(construire(4))
    assert {frozenset((a.ref_id, b.ref_id)) for a, b in paires} == {
        frozenset((1, 4)),
        frozenset((2, 3)),
    }


def test_paires_du_premier_tour_exclut_les_exempts() -> None:
    # 5 archers dans un tableau de 8 : les têtes 1, 2, 3 sont exemptées (byes), seul 4 vs 5 se joue.
    # Un exempté n'a pas d'adversaire à placer à côté de lui : le bye est exclu des paires.
    paires = paires_du_premier_tour(construire(5))
    assert {frozenset((a.ref_id, b.ref_id)) for a, b in paires} == {frozenset((4, 5))}


# --- CA « byes » -------------------------------------------------------------------------------
# ByesAuxMieuxClasses : 2^k - effectif exempts, attribués aux têtes 1..nb_byes ; calcul universel.


@pytest.mark.parametrize("effectif", [3, 5, 6, 9, 17])
def test_byes_attribues_aux_mieux_classes(effectif: int) -> None:
    tableau = construire(effectif)
    # Les participants dispensés du premier tour (leur match est un bye, gagné d'office) sont
    # exactement les têtes que la politique ByesAuxMieuxClasses désigne — « aux mieux classés ».
    dispenses = {
        m.vainqueur for m in tableau.matchs if m.tour == 1 and m.est_bye and m.vainqueur is not None
    }
    assert dispenses == {p(r) for r in BYES.porteurs_de_bye(effectif)}


def test_un_seul_match_contest_pour_cinq_archers() -> None:
    # Effectif 5, tableau de 8 : 3 byes (têtes 1, 2, 3), un seul match réel au tour 1 (4 vs 5).
    tableau = construire(5)
    contestes = [(m.haut, m.bas) for m in tableau.matchs if m.tour == 1 and not m.est_bye]
    assert contestes == [(p(4), p(5))]


def test_seed_dispense_de_bye_avance_au_tour_suivant() -> None:
    # La tête 1 (bye) est présente comme occupant d'un match du deuxième tour sans avoir tiré.
    tableau = construire(5)
    au_tour_2 = {
        occupant
        for m in tableau.matchs
        if m.tour == 2
        for occupant in (m.haut, m.bas)
        if occupant is not None
    }
    assert {p(1), p(2), p(3)} <= au_tour_2


def test_aucun_bye_quand_effectif_est_une_puissance_de_deux() -> None:
    assert all(not m.est_bye for m in construire(8).matchs)


def test_politique_byes_incoherente_avec_le_seeding_refusee() -> None:
    # Règle 2 : la politique byes est réellement consommée (l'injecter doit avoir un effet). Un byes
    # « aux plus mauvais classés » contredit la structure serpent (qui exempte les mieux classés).
    from domain.erreurs import FormatTableauIncoherent

    class ByesAuxPlusMauvaisClasses:
        def porteurs_de_bye(self, effectif: int) -> frozenset[int]:
            taille = 2 ** (effectif - 1).bit_length()
            nb = taille - effectif
            return frozenset(range(effectif - nb + 1, effectif + 1))

    joueurs = [p(r) for r in range(1, 6)]
    with pytest.raises(FormatTableauIncoherent):
        construire_tableau(joueurs, SEEDING, ByesAuxPlusMauvaisClasses(), ROUTING, DEPTH)


# --- CA « génération de l'arbre » --------------------------------------------------------------
# Matchs numérotés, tours ordonnés, chaque match relié à ses sources (seeds/byes puis vainqueurs).


def test_matchs_numerotes_de_un_a_n_sans_trou() -> None:
    tableau = construire(8)
    numeros = [m.numero for m in tableau.matchs]
    assert numeros == list(range(1, len(tableau.matchs) + 1))


def test_nombre_de_matchs_et_petite_finale() -> None:
    # Un tableau de 2^k a 2^k-1 matchs, plus la petite finale dès qu'il y a des demi-finales (≥ 4).
    assert len(construire(8).matchs) == 8  # 7 + petite finale
    assert len(construire(4).matchs) == 4  # 3 + petite finale
    assert len(construire(2).matchs) == 1  # finale seule, pas de petite finale


def test_tours_ordonnes_et_contigus() -> None:
    tableau = construire(8)
    tours = sorted({m.tour for m in tableau.matchs})
    assert tours == [1, 2, 3]  # log2(8) tours


def test_sources_du_premier_tour_sont_seeds_ou_exempts() -> None:
    for m in construire(5).matchs:
        if m.tour == 1:
            assert isinstance(m.source_haut, TeteDeSerie | Exempt)
            assert isinstance(m.source_bas, TeteDeSerie | Exempt)


def test_sources_des_tours_suivants_sont_des_vainqueurs() -> None:
    tableau = construire(8)
    semi = next(m for m in tableau.matchs if m.tour == 2)
    assert isinstance(semi.source_haut, VainqueurDe)
    assert isinstance(semi.source_bas, VainqueurDe)
    # La source pointe un match d'un tour antérieur.
    assert tableau.match(semi.source_haut.numero).tour < semi.tour


def test_finale_et_petite_finale_portent_les_places_en_jeu() -> None:
    tableau = construire(8)
    assert tableau.finale.place_en_jeu == (1, 2)
    petite = tableau.petite_finale
    assert petite is not None
    assert petite.place_en_jeu == (3, 4)
    # La petite finale oppose les perdants des deux demi-finales.
    assert isinstance(petite.source_haut, PerdantDe)
    assert isinstance(petite.source_bas, PerdantDe)


# --- CA « progression » ------------------------------------------------------------------------
# À réception du vainqueur, le match suivant est peuplé ; le perdant est éliminé (sèche).


def test_le_vainqueur_peuple_le_match_suivant() -> None:
    tableau = construire(8)
    # Le match 2 (4 vs 5) alimente une demi-finale (VainqueurDe(2)).
    suivant = next(m for m in tableau.matchs if VainqueurDe(2) in (m.source_haut, m.source_bas))
    assert suivant.haut is None or suivant.bas is None  # place encore vide avant le match
    apres = tableau.jouer(2, p(4))
    suivant_apres = apres.match(suivant.numero)
    assert p(4) in (suivant_apres.haut, suivant_apres.bas)


def test_le_perdant_est_elimine_pas_reinjecte() -> None:
    tableau = construire(8).jouer(2, p(4))  # 5 perd
    # Le match joué garde la trace de ses deux tireurs (4 et 5) ; « éliminé » = le perdant 5 n'est
    # réinjecté dans **aucun autre** match (élimination sèche, pas de cascade vers un sous-tableau).
    occupants_aval = {
        occ for m in tableau.matchs if m.numero != 2 for occ in (m.haut, m.bas) if occ is not None
    }
    assert p(5) not in occupants_aval


def test_jouer_un_match_inconnu_leve_match_introuvable() -> None:
    with pytest.raises(MatchIntrouvable):
        construire(8).jouer(999, p(1))


def test_jouer_un_bye_est_refuse() -> None:
    # Le match d'un participant exempté est déjà résolu : on ne le « joue » pas.
    tableau = construire(5)
    bye = next(m for m in tableau.matchs if m.est_bye)
    with pytest.raises(MatchNonJouable):
        tableau.jouer(bye.numero, bye.vainqueur or p(1))


def test_jouer_un_match_aux_places_incompletes_est_refuse() -> None:
    # Une demi-finale dont les deux occupants ne sont pas encore connus n'est pas jouable.
    tableau = construire(8)
    demi = next(m for m in tableau.matchs if m.tour == 2)
    assert not demi.est_jouable
    with pytest.raises(MatchNonJouable):
        tableau.jouer(demi.numero, p(1))


def test_jouer_deux_fois_le_meme_match_est_refuse() -> None:
    tableau = construire(8).jouer(2, p(4))
    with pytest.raises(MatchNonJouable):
        tableau.jouer(2, p(4))


def test_vainqueur_hors_du_match_est_refuse() -> None:
    with pytest.raises(VainqueurHorsMatch):
        construire(8).jouer(2, p(7))  # 7 ne dispute pas le match 2 (4 vs 5)


def test_l_elimination_seche_ne_departage_meme_pas_la_troisieme_place() -> None:
    """Le routing « le perdant sort » supprime jusqu'à la petite finale (E05US010).

    Remplace l'ancien `test_routing_non_elimination_seche_est_refuse` : le moteur ne refuse plus
    les destinations autres qu'`ELIMINE`, il les honore. Ce qui reste vérifiable, c'est que les
    **deux** routings produisent bien deux formats distincts — sinon la politique ne servirait à
    rien.
    """
    joueurs = [p(r) for r in range(1, 9)]
    sec = construire_tableau(joueurs, SEEDING, BYES, EliminationSeche(), DEPTH)
    assert sec.petite_finale is None
    assert len(sec.matchs) == 7  # 4 quarts + 2 demies + 1 finale, aucun match de classement
    avec_petite_finale = construire_tableau(joueurs, SEEDING, BYES, PlacementEnCascade(), DEPTH)
    assert avec_petite_finale.petite_finale is not None
    assert len(avec_petite_finale.matchs) == 8


# --- CA « podium » -----------------------------------------------------------------------------
# Finale → rangs 1-2 ; petite finale → rangs 3-4 (moteur-placement-lucky-loser.md §2, Rangs 1 à 4).


def _derouler_gagne_mieux_classe(tableau: Tableau) -> Tableau:
    """Joue tout le tableau jusqu'au bout, le mieux classé l'emportant à chaque match jouable."""
    en_cours = tableau
    progresse = True
    while progresse:
        progresse = False
        for m in en_cours.matchs:
            if m.est_jouable:
                en_cours = jouer_gagne_mieux_classe(en_cours, m.numero)
                progresse = True
                break
    return en_cours


def test_podium_de_huit_le_mieux_classe_gagne() -> None:
    tableau = _derouler_gagne_mieux_classe(construire(8))
    assert tableau.est_termine
    # Le mieux classé gagne partout : podium = têtes 1, 2, 3, 4 dans l'ordre.
    assert tableau.podium() == (
        Place(1, p(1)),
        Place(2, p(2)),
        Place(3, p(3)),
        Place(4, p(4)),
    )


def test_finale_donne_rangs_un_et_deux() -> None:
    tableau = construire(2).jouer(1, p(1))  # finale 1 vs 2, la tête 1 gagne
    assert tableau.est_termine
    assert tableau.podium() == (Place(1, p(1)), Place(2, p(2)))
    assert tableau.petite_finale is None


def test_podium_de_trois_avec_bye_pas_de_rang_quatre() -> None:
    # 3 archers, tableau de 4 : la tête 1 a un bye ; il n'y a pas de 4e place à décerner.
    tableau = _derouler_gagne_mieux_classe(construire(3))
    assert tableau.est_termine
    assert tableau.podium() == (Place(1, p(1)), Place(2, p(2)), Place(3, p(3)))


def test_podium_suit_le_vainqueur_reel_pas_la_tete_de_serie() -> None:
    # « Finale → rangs 1-2 » désigne les finalistes par leur **résultat**, pas les meilleures têtes.
    # sur un upset (une tête plus faible gagne), le podium doit suivre le vainqueur réel du match.
    tableau = construire(4)
    for num in [m.numero for m in tableau.matchs if m.tour == 1]:  # demi-finales (1v4), (2v3)
        tableau = jouer_gagne_mieux_classe(tableau, num)  # → finale 1 vs 2, petite finale 4 vs 3
    petite = tableau.petite_finale
    assert petite is not None
    tableau = tableau.jouer(tableau.finale.numero, p(2))  # upset : la tête 2 bat la tête 1
    tableau = tableau.jouer(petite.numero, p(3))  # 3 bat 4 en petite finale
    assert tableau.podium() == (Place(1, p(2)), Place(2, p(1)), Place(3, p(3)), Place(4, p(4)))


def test_le_moteur_traite_les_equipes_comme_les_archers() -> None:
    # Opacité (ADR-0028) : un tableau d'**équipes** se déroule à l'identique — le moteur ne branche
    # jamais sur le genre du participant, il n'en lit que l'identité.
    equipes = [Participant.equipe(i) for i in range(1, 5)]
    tableau = _derouler_gagne_mieux_classe(
        construire_tableau(equipes, SEEDING, BYES, ROUTING, DEPTH)
    )
    assert tableau.est_termine
    assert tableau.podium() == (
        Place(1, Participant.equipe(1)),
        Place(2, Participant.equipe(2)),
        Place(3, Participant.equipe(3)),
        Place(4, Participant.equipe(4)),
    )


def test_podium_incomplet_avant_la_fin() -> None:
    tableau = construire(8)
    assert not tableau.est_termine
    assert tableau.podium() == ()  # rien de décidé tant que la finale n'est pas jouée


# --- Libellé de tour (E04US018) -----------------------------------------------------------------
#
# Dérivé du CA d'E04US018 (« sa prochaine affectation — cible, position, heure, **tour** ») : ce que
# le panneau de routage doit dire à un archer, ce n'est pas « tour 2 » (un rang technique dans
# l'arbre) mais le nom que la salle emploie — « quart de finale ». Le libellé se compte **à
# rebours** de la finale : c'est la distance au titre qui le nomme, jamais le rang du tour.


def test_libelle_tour_se_compte_a_rebours_de_la_finale() -> None:
    # Tableau de 8 (3 tours) : quarts → demi → finale. Le même numéro de tour ne donne pas le même
    # libellé selon la taille du tableau — d'où le `nb_tours` en paramètre.
    assert libelle_tour(tour=1, nb_tours=3) == "Quart de finale"
    assert libelle_tour(tour=2, nb_tours=3) == "Demi-finale"
    assert libelle_tour(tour=3, nb_tours=3) == "Finale"
    # Tableau de 4 : le tour 1 est déjà la demi-finale.
    assert libelle_tour(tour=1, nb_tours=2) == "Demi-finale"


def test_libelle_tour_au_dela_des_quarts_est_une_fraction() -> None:
    # Au-delà du quart, la FFTA nomme les tours par leur fraction (1/8, 1/16, 1/32…).
    assert libelle_tour(tour=1, nb_tours=4) == "1/8 de finale"
    assert libelle_tour(tour=1, nb_tours=5) == "1/16 de finale"
    assert libelle_tour(tour=2, nb_tours=6) == "1/16 de finale"


def test_libelle_petite_finale_prime_sur_le_tour() -> None:
    # La petite finale se joue au **même tour** que la finale : sans son `place_en_jeu`, les deux
    # matchs porteraient le libellé « Finale » et enverraient les demi-finalistes battus au mauvais
    # rendez-vous. C'est la place en jeu qui la nomme.
    assert libelle_tour(tour=3, nb_tours=3, place_en_jeu=(3, 4)) == "Petite finale"
    assert libelle_tour(tour=3, nb_tours=3, place_en_jeu=(1, 2)) == "Finale"


def test_le_podium_publie_les_rangs_trois_quatre_avant_la_finale() -> None:
    """La petite finale se tire couramment **avant** la finale (le bronze avant l'or, en salle).

    Test ajouté en revue : un premier jet d'E05US010 avait posé une garde « rien tant que la finale
    n'est pas jouée », qui privait l'écran de duels et le panneau de routage des rangs 3-4 pendant
    tout l'intervalle. Aucun test existant ne jouait les matchs dans cet ordre — celui-ci le fait.
    """
    tableau = construire(8)
    for numero in (1, 2, 3, 4):  # les quarts
        tableau = jouer_gagne_mieux_classe(tableau, numero)
    for numero in (5, 6):  # les demi-finales
        tableau = jouer_gagne_mieux_classe(tableau, numero)
    petite = tableau.petite_finale
    assert petite is not None
    tableau = jouer_gagne_mieux_classe(tableau, petite.numero)

    assert tableau.finale.vainqueur is None  # la finale n'est pas encore tirée
    assert [place.rang for place in tableau.podium()] == [3, 4]


# --- E05US015 : la destination « repêchage » -----------------------------------------------------


def test_un_routing_de_repechage_n_engendre_pas_la_moitie_basse() -> None:
    """La branche `VersRepechage` de `construire_tableau`, **jamais atteinte par un test**.

    ⚠️ C'est exactement le cas que le garde-fou d'E05US010 laissait en garde : « le jour où E05US015
    ajoute la destination repêchage, le moteur n'aurait construit aucun sous-tableau d'accueil,
    n'aurait rien levé, et mypy n'aurait rien dit ». Ne rien engendrer **est** ici la bonne réponse
    (le repêché ne se classe pas dans ce tableau, une phase avale le reprend), mais rien ne le
    figeait : un refactor du dispatch de routing l'aurait cassé en silence.

    Un tableau de 8 en cascade pure produit 12 matchs ; avec les perdants du 1ᵉʳ tour repêchés, la
    moitié basse (places 5-8) n'est plus engendrée et il n'en reste que 8.
    """
    joueurs = [p(rang) for rang in range(1, 9)]
    cascade = construire_tableau(joueurs, SEEDING, BYES, PlacementEnCascade(), ProfondeurUnVersN())
    repechage = construire_tableau(
        joueurs,
        SEEDING,
        BYES,
        RoutingRepechage(tours_repeches=frozenset({1}), sinon=PlacementEnCascade()),
        ProfondeurUnVersN(),
    )
    assert len(cascade.matchs) == 12
    assert len(repechage.matchs) == 8
    # Aucun match du tableau repêché ne dispute les places 5 à 8 : elles sont laissées à la phase
    # de repêchage, et c'est le diagnostic de déroulé (E01US024) qui signalera son absence.
    assert all(match.plage is None or match.plage.debut <= 4 for match in repechage.matchs)


def test_le_repechage_ne_desarme_pas_le_refus_des_destinations_inconnues() -> None:
    """Le garde-fou d'E05US010 doit survivre à l'ajout d'une destination : une destination que le
    moteur ne sait pas honorer lève toujours, elle ne tombe pas dans la branche du repêchage."""

    @dataclass(frozen=True)
    class DestinationInventee:
        pass

    @dataclass(frozen=True)
    class RoutingInconnu:
        def route(self, contexte: ContexteRoutage) -> Destination:
            return cast("Destination", DestinationInventee())

    with pytest.raises(RoutingNonSupporte):
        construire_tableau(
            [p(rang) for rang in range(1, 5)],
            SEEDING,
            BYES,
            RoutingInconnu(),
            ProfondeurUnVersN(),
        )


# --- CA E06US004 « agrégation » : la position acquise de chaque participant ---------------------
# Le palmarès a besoin, pour chaque archer, de ce que *ce tableau* a décidé — rang exact quand un
# match terminal l'a décerné, fourchette sinon (*Règle R*, ADR-0065). La lecture vit ici parce que
# la règle y vit déjà (`Plage.moitie_basse`, `classement()`) : E06US004 la lit, ne la réécrit pas.


def _positions(tableau: Tableau) -> dict[int, tuple[int, int]]:
    """`ref_id → (rang_min, rang_max)`, pour des assertions lisibles."""
    return {
        participant.ref_id: (acquise.rang_min, acquise.rang_max)
        for participant, acquise in tableau.positions_acquises().items()
    }


def test_positions_acquises_rend_les_rangs_exacts_des_matchs_terminaux() -> None:
    """Un tableau de 4 entièrement joué : les quatre rangs sont décernés, aucune fourchette."""
    tableau = construire(4)
    for numero in (1, 2, 3, 4):
        tableau = jouer_gagne_mieux_classe(tableau, numero)

    assert _positions(tableau) == {1: (1, 1), 2: (2, 2), 3: (3, 3), 4: (4, 4)}


def test_positions_acquises_rend_la_fourchette_des_battus_non_departages() -> None:
    """Tableau de 8 tronqué au podium : les quatre battus des quarts sortent tous sur `[5..8]`.

    Aucun match ne les a départagés — c'est le cas que la politique `aggregation` (E06US004)
    tranche ensuite, et la raison pour laquelle cette lecture rend une **fourchette** plutôt qu'un
    rang inventé.
    """
    tableau = construire(8)
    for numero in range(1, 9):
        tableau = jouer_gagne_mieux_classe(tableau, numero)

    positions = _positions(tableau)
    assert positions[1] == (1, 1)
    assert positions[2] == (2, 2)
    assert {positions[r] for r in (5, 6, 7, 8)} == {(5, 8)}


def test_positions_acquises_ecrete_la_fourchette_a_l_effectif_reel() -> None:
    """La plage est bornée par la **taille** du tableau (une puissance de 2), pas par l'effectif :
    à 6 archers (taille 8), un battu du 1ᵉʳ tour est 5ᵉ-**6**ᵉ, pas 5ᵉ-8ᵉ — les rangs 7 et 8
    n'existent pas. Écrêtage relevé en revue d'E07US008 (ADR-0065)."""
    tableau = construire(6)
    for numero in range(1, len(tableau.matchs) + 1):
        match = tableau.match(numero)
        if match.est_jouable:
            tableau = jouer_gagne_mieux_classe(tableau, numero)

    positions = _positions(tableau)
    assert positions[5] == (5, 6)
    assert positions[6] == (5, 6)


def test_positions_acquises_rend_la_plage_courante_d_un_archer_encore_en_lice() -> None:
    """Un archer qui a un match devant lui a déjà **acquis** quelque chose : la plage de ce match.

    En demi-finale d'un tableau de 8, il est assuré d'être au mieux 1ᵉʳ et au pire 4ᵉ. Le palmarès
    est consulté **pendant** le tournoi (écran public) : lui refuser tout rang jusqu'à la fin le
    ferait tomber derrière des archers déjà éliminés, ce qui serait faux.
    """
    tableau = construire(8)
    for numero in (1, 2, 3, 4):
        tableau = jouer_gagne_mieux_classe(tableau, numero)

    assert _positions(tableau)[1] == (1, 4)
    assert tableau.positions_acquises()[p(1)].en_lice is True


def test_positions_acquises_distingue_l_ex_aequo_du_match_a_venir() -> None:
    """Deux fourchettes de même forme, deux sens opposés — et c'est `en_lice` qui les sépare.

    Tableau de 8 tronqué au podium, quarts joués : les quatre vainqueurs portent `[1..4]` parce
    qu'ils vont **tirer** les demies ; les quatre battus portent `[5..8]` parce que **plus rien**
    ne les départagera (la profondeur `podium` élague leur sous-tableau). Confondre les deux fait
    décerner l'or au mieux qualifié avant la finale — le défaut qu'a relevé le test de service
    d'E06US004.

    ⚠️ Le même essai sur un tableau de **4** ne montrerait rien : en cascade, les battus du 1ᵉʳ
    tour y descendent en **petite finale**, donc restent en lice. Il faut un tableau où la
    profondeur élague vraiment pour que l'ex æquo définitif existe.
    """
    tableau = construire(8)
    for numero in (1, 2, 3, 4):
        tableau = jouer_gagne_mieux_classe(tableau, numero)

    acquises = tableau.positions_acquises()
    vainqueurs = [r for r in range(1, 9) if acquises[p(r)].en_lice]
    battus = [r for r in range(1, 9) if not acquises[p(r)].en_lice]
    assert len(vainqueurs) == 4 and len(battus) == 4
    assert {(acquises[p(r)].rang_min, acquises[p(r)].rang_max) for r in vainqueurs} == {(1, 4)}
    assert {(acquises[p(r)].rang_min, acquises[p(r)].rang_max) for r in battus} == {(5, 8)}


def test_positions_acquises_ignore_qui_n_est_pas_dans_le_tableau() -> None:
    """Seuls les occupants d'au moins un camp y figurent : le palmarès classera les autres par la
    qualification, et une entrée vide les ferait passer pour éliminés."""
    tableau = construire(4)

    assert p(9) not in tableau.positions_acquises()
