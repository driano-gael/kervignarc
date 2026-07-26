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
    DestinationPerdant,
    EliminationSeche,
    Routing,
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
)

SEEDING = SeedingSerpent()
BYES = ByesAuxMieuxClasses()
ROUTING = EliminationSeche()


def p(rang: int) -> Participant:
    """Le participant à ce rang de qualification (`ref_id = rang` pour des tests lisibles)."""
    return Participant.individuel(rang)


def construire(effectif: int) -> Tableau:
    """Assemble un tableau pour `effectif` participants ordonnés par rang (p(1) = tête de série)."""
    return construire_tableau([p(r) for r in range(1, effectif + 1)], SEEDING, BYES, ROUTING)


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
        construire_tableau(joueurs, SEEDING, ByesAuxPlusMauvaisClasses(), ROUTING)


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


def test_routing_non_elimination_seche_est_refuse() -> None:
    # E05US005 ne gère que l'élimination sèche ; une cascade (E05US010) ressignera le routing.
    class RoutingEliminationSecheBis:
        def destination_du_perdant(self) -> DestinationPerdant:
            return DestinationPerdant.ELIMINE

    # Politique factice renvoyant une destination inconnue du moteur d'élimination directe.
    class RoutingInconnu:
        def destination_du_perdant(self) -> DestinationPerdant:
            return "cascade"  # type: ignore[return-value]

    joueurs = [p(r) for r in range(1, 9)]
    routing: Routing = RoutingInconnu()
    with pytest.raises(RoutingNonSupporte):
        construire_tableau(joueurs, SEEDING, BYES, routing).jouer(2, p(4))
    # Contrôle négatif : l'élimination sèche, elle, passe.
    assert construire_tableau(joueurs, SEEDING, BYES, RoutingEliminationSecheBis()).jouer(2, p(4))


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
    tableau = _derouler_gagne_mieux_classe(construire_tableau(equipes, SEEDING, BYES, ROUTING))
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
