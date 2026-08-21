"""Les **poules de niveau** — une étape qui se déplie en groupes par tranches de rangs (E05US029).

⚠️ **Ces tests sont écrits depuis le CA, avant l'implémentation** (règle 9). L'oracle est la fiche
`stories/E05-moteur-phases.md` § `E05US029`, complétée des trois arbitrages tranchés au cadrage du
21/08/2026 :

1. la variante en **cascade à resserrement** entre dans le périmètre (36 → 18 → 9) ;
2. quand l'effectif ne tombe pas juste, **les groupes du bas gonflent** — les tranches du haut
   restent à la taille visée ;
3. le garde-fou « 2ᵉ phase de poules au serpent » est un **refus**, levé par une dérogation
   explicite.

Rien ici n'a été relu dans `domain/poule.py` ni `domain/classement_de_poules.py` au titre d'oracle :
le mode `PAR_NIVEAU` n'existait pas quand ce fichier a été écrit. Les helpers, eux, sont repris des
deux fichiers de tests voisins — ce sont des outils, pas des oracles.

Les quatre propriétés que le CA impose :

1. **La composition** : un groupe par tranche de rangs **contiguë**, au lieu du serpent.
2. **Le remplissage** : les groupes du bas absorbent le surplus (arbitrage 2 ci-dessus).
3. **Le classement de phase** se lit **groupe par groupe** — c'est ce qui donne à chaque poule son
   propre espace de rangs, et le vainqueur du dernier groupe n'est jamais 1ᵉʳ.
4. **Le serpent reste le défaut**, et rien de son comportement ne bouge.
"""

from __future__ import annotations

import pytest

from domain.classement import LigneClassement
from domain.classement_de_poules import classement_de_poules
from domain.erreurs import ConfigurationPouleInvalide
from domain.participant import Participant
from domain.politiques import DecompteDepartage, TiebreakPoules
from domain.poule import (
    ConfigurationPoules,
    ModeDeComposition,
    Poule,
    RangPoule,
    ReglageDePoules,
    composer_poules,
)


def archers(nombre: int) -> list[Participant]:
    """`nombre` participants individuels, **ordonnés par rang** de la phase source (1 = premier)."""
    return [Participant.individuel(rang) for rang in range(1, nombre + 1)]


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


def _poule(*archers_de_la_poule: int) -> tuple[RangPoule, ...]:
    """Le classement d'une poule : les archers dans l'ordre, rangs 1..n, aucun ex æquo."""
    total = len(archers_de_la_poule)
    return tuple(
        RangPoule(
            rang=index,
            participant=Participant.individuel(archer),
            decompte=DecompteDepartage(nb_dix=0, nb_neuf=0, points_match=total - index),
        )
        for index, archer in enumerate(archers_de_la_poule, start=1)
    )


def _ex_aequo_au_rang_deux(*archers_de_la_poule: int) -> tuple[RangPoule, ...]:
    """Un groupe dont les 2ᵉ et 3ᵉ partagent le rang 2 — l'ex æquo irréductible du §10.1."""
    rangs = (1, 2, 2)
    return tuple(
        RangPoule(
            rang=rang,
            participant=Participant.individuel(archer),
            decompte=DecompteDepartage(nb_dix=0, nb_neuf=0, points_match=10 - rang),
            ex_aequo=rangs.count(rang) > 1,
        )
        for archer, rang in zip(archers_de_la_poule, rangs, strict=True)
    )


def _membres(poules: tuple[Poule, ...]) -> list[list[int]]:
    """Les identités de chaque groupe, dans l'ordre des groupes."""
    return [[membre.ref_id for membre in poule.membres] for poule in poules]


# --- composition : « l'outil dérive les groupes par tranches de rangs contiguës » -----------------


def test_par_niveau_decoupe_le_classement_en_tranches_contigues() -> None:
    """Le CA phare, sur le format décrit par le commanditaire : 36 archers, 6 poules de 6.

    La poule A réunit les rangs 1 à 6, la B les rangs 7 à 12, et ainsi de suite — l'inverse exact
    du serpent, dont tout l'objet est au contraire d'éparpiller les têtes de série.
    """
    poules = composer_poules(
        archers(36), ConfigurationPoules(nb_poules=6, mode=ModeDeComposition.PAR_NIVEAU)
    )
    assert _membres(poules) == [
        [1, 2, 3, 4, 5, 6],
        [7, 8, 9, 10, 11, 12],
        [13, 14, 15, 16, 17, 18],
        [19, 20, 21, 22, 23, 24],
        [25, 26, 27, 28, 29, 30],
        [31, 32, 33, 34, 35, 36],
    ]


def test_par_niveau_gonfle_les_groupes_du_bas() -> None:
    """Arbitrage du cadrage : quand l'effectif ne tombe pas juste, le surplus va **au bas**.

    34 archers en poules de 6 donnent 5 groupes (`nb_poules_pour` arrondit vers le bas), soit 4
    archers à replacer. Les tranches du haut restent à la taille visée — le haut du classement,
    celui qui a le plus d'enjeu, tire dans les conditions annoncées.
    """
    poules = composer_poules(
        archers(34), ConfigurationPoules(nb_poules=5, mode=ModeDeComposition.PAR_NIVEAU)
    )
    assert [len(poule.membres) for poule in poules] == [6, 7, 7, 7, 7]


def test_par_niveau_reste_contigu_meme_quand_les_groupes_gonflent() -> None:
    """Le gonflement ne doit pas trouer les tranches : un groupe reste un intervalle de rangs.

    C'est la propriété qui fait tout le format — si une tranche sautait un rang, deux archers de
    niveaux voisins joueraient dans des groupes disputant des espaces de rangs différents.
    """
    poules = composer_poules(
        archers(34), ConfigurationPoules(nb_poules=5, mode=ModeDeComposition.PAR_NIVEAU)
    )
    assert _membres(poules) == [
        [1, 2, 3, 4, 5, 6],
        [7, 8, 9, 10, 11, 12, 13],
        [14, 15, 16, 17, 18, 19, 20],
        [21, 22, 23, 24, 25, 26, 27],
        [28, 29, 30, 31, 32, 33, 34],
    ]


def test_le_serpent_reste_le_mode_par_defaut() -> None:
    """« Le mode de composition est un réglage, pas un type de phase neuf », et son défaut est le
    comportement d'aujourd'hui : une configuration qui ne dit rien compose au serpent."""
    poules = composer_poules(archers(6), ConfigurationPoules(nb_poules=3))
    assert _membres(poules) == [[1, 6], [2, 5], [3, 4]]


def test_le_serpent_demande_explicitement_donne_le_meme_resultat() -> None:
    """Nommer le mode ne change rien à ce que le serpent produisait — non-régression du format
    déjà joué, dont aucun tournoi enregistré ne doit voir la composition bouger."""
    poules = composer_poules(
        archers(6), ConfigurationPoules(nb_poules=3, mode=ModeDeComposition.SERPENT)
    )
    assert _membres(poules) == [[1, 6], [2, 5], [3, 4]]


# --- classement de phase : « chaque groupe dispute son propre espace de rangs » -------------------


def test_le_classement_par_niveau_se_lit_groupe_par_groupe() -> None:
    """Là où le serpent range « par rang de poule d'abord » (tous les vainqueurs, puis tous les
    deuxièmes), une phase de niveau range **groupe par groupe** : la poule A occupe les trois
    premiers rangs de la phase, la B les trois suivants.

    C'est l'exigence « chaque groupe dispute son propre espace de rangs » : elle se tient dans
    l'ordre du classement de phase, sans qu'aucun décalage n'ait à être porté par le groupe.
    """
    resultat = classement_de_poules(
        [_poule(1, 2, 3), _poule(4, 5, 6), _poule(7, 8, 9)],
        {archer: _ligne(archer) for archer in range(1, 10)},
        mode=ModeDeComposition.PAR_NIVEAU,
    )
    assert [ligne.archer_id for ligne in resultat.classement.lignes] == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert [ligne.rang_scratch for ligne in resultat.classement.lignes] == list(range(1, 10))


def test_le_vainqueur_du_dernier_groupe_n_est_pas_premier() -> None:
    """Le défaut que le CA nomme : « le vainqueur du groupe des 31ᵉ-36ᵉ est **31ᵉ**, jamais 1ᵉʳ ».

    Un classement bien formé, plausible et faux est le mode de panne le plus coûteux du moteur
    (ADR-0081) — on l'éprouve sur le format complet plutôt que sur un cas réduit.
    """
    groupes = [_poule(*range(debut, debut + 6)) for debut in range(1, 37, 6)]
    resultat = classement_de_poules(
        groupes,
        {archer: _ligne(archer) for archer in range(1, 37)},
        mode=ModeDeComposition.PAR_NIVEAU,
    )
    par_archer = {ligne.archer_id: ligne.rang_scratch for ligne in resultat.classement.lignes}
    assert par_archer[31] == 31, "le vainqueur du dernier groupe ouvre sa tranche, il n'est pas 1ᵉʳ"
    assert par_archer[1] == 1
    assert par_archer[36] == 36


def test_le_classement_au_serpent_reste_par_rang_de_poule() -> None:
    """Non-régression : sans mode déclaré, l'ordre d'ADR-0083 §6 est inchangé — les trois
    vainqueurs occupent les rangs 1 à 3, quel que soit leur groupe."""
    resultat = classement_de_poules(
        [_poule(1, 2, 3), _poule(4, 5, 6), _poule(7, 8, 9)],
        {archer: _ligne(archer) for archer in range(1, 10)},
        mode=ModeDeComposition.SERPENT,
    )
    assert [ligne.archer_id for ligne in resultat.classement.lignes] == [1, 4, 7, 2, 5, 8, 3, 6, 9]


def test_par_niveau_ne_produit_aucun_bloc_indecis_inter_poules() -> None:
    """Corollaire de la lecture groupe par groupe, et il vaut d'être éprouvé : deux archers de
    poules différentes ne partagent plus jamais un rang de phase.

    Au serpent, les `P` vainqueurs forment un bloc indécis — comparer leurs décomptes n'a de valeur
    qu'au besoin (ADR-0083 §6). Par niveau, la question ne se pose pas : chaque groupe a sa tranche,
    donc plus rien à départager entre groupes. Seul un ex æquo **interne** à une poule reste
    irréductible.
    """
    resultat = classement_de_poules(
        [_poule(1, 2, 3), _poule(4, 5, 6)],
        {archer: _ligne(archer) for archer in range(1, 7)},
        mode=ModeDeComposition.PAR_NIVEAU,
    )
    assert resultat.plages_indecises == ()


# --- Correctifs de revue E05US029 ----------------------------------------------------------------
#
# Chaque test ci-dessous verrouille une remarque de `/revue-us`. L'oracle reste le CA — ces cas
# sont ceux que le CA impliquait sans que personne les ait écrits, pas des descriptions du
# correctif : c'est la distinction qui décide si un test après coup vaut quelque chose.


def test_des_poules_de_niveau_ne_designent_pas_de_qualifies() -> None:
    """⚠️ **Bloquant relevé en revue (axe C1).** « k qualifiés par poule » n'est pas exprimable.

    Sous `SERPENT`, les `k` premiers de chaque groupe occupent les rangs `1..k*P` — une fenêtre
    **contiguë**, que la phase avale prélève par rangs. Sous `PAR_NIVEAU` les qualifiés forment un
    **peigne** ({1,2, 5,6, 9,10, 13,14} sur 4 groupes de 4 qualifiant 2), qu'aucun prélèvement par
    fenêtre ne désigne : « les rangs 1 à 8 » rendrait les groupes A et B entiers, un autre ensemble
    de même cardinal — plausible et faux.
    """
    with pytest.raises(ConfigurationPouleInvalide):
        ReglageDePoules(taille_visee=6, nb_qualifies=3, mode=ModeDeComposition.PAR_NIVEAU)


def test_le_moteur_refuse_aussi_la_configuration_qui_qualifie_par_niveau() -> None:
    """Le même invariant sur l'objet que le **moteur** consomme, `pour_effectif` n'étant pas la
    seule porte d'entrée de `qualifies_de_poule`."""
    with pytest.raises(ConfigurationPouleInvalide):
        ConfigurationPoules(nb_poules=6, nb_qualifies=3, mode=ModeDeComposition.PAR_NIVEAU)


def test_des_poules_de_niveau_qui_classent_restent_licites() -> None:
    """Le contre-test qui empêche le refus d'être trop large : une phase de niveau **classe**, et
    c'est son cas nominal — elle décerne le classement final du tournoi."""
    reglage = ReglageDePoules(taille_visee=6, mode=ModeDeComposition.PAR_NIVEAU)
    assert reglage.produit_un_classement


def test_la_derogation_ne_survit_pas_au_passage_par_niveau() -> None:
    """⚠️ **Majeur relevé en revue (axes C1 et D).** L'invariant n'était tenu que par le front.

    Une dérogation persistée sous `PAR_NIVEAU` restait **armée à froid** : au retour au serpent,
    elle levait le refus sans que personne ne l'ait assumée pour ce réglage-là — « voulu » et
    « pas vu » redevenaient indiscernables, ce que ce champ existe précisément pour empêcher.

    Normalisée et non refusée : cocher la case puis changer de mode n'est pas une faute.
    """
    reglage = ReglageDePoules(
        taille_visee=6, mode=ModeDeComposition.PAR_NIVEAU, serpent_assume=True
    )
    assert reglage.serpent_assume is False


def test_la_derogation_est_conservee_sous_le_serpent() -> None:
    """Le contre-test : c'est bien le **couple** qui est normalisé, pas la case elle-même."""
    reglage = ReglageDePoules(taille_visee=6, serpent_assume=True)
    assert reglage.serpent_assume is True


def test_le_departage_inter_poules_est_ignore_par_niveau() -> None:
    """⚠️ **Trou de couverture relevé en revue (axes B et D).** La docstring de `_par_groupe`
    promet que le départage est *sans objet* sous `PAR_NIVEAU` ; rien ne l'épinglait.

    Sans ce test, une branche `PAR_NIVEAU` placée un jour **après** le tri réordonnerait les
    groupes sans que personne ne le voie — et le réglage reste atteignable, `application/poules.py`
    construisant bien un `TiebreakPoules()` quand la case est restée cochée d'un passage au serpent.
    """
    resultat = classement_de_poules(
        [_poule(1, 2, 3), _poule(4, 5, 6)],
        {archer: _ligne(archer) for archer in range(1, 7)},
        departage=TiebreakPoules(),
        mode=ModeDeComposition.PAR_NIVEAU,
    )
    assert [ligne.archer_id for ligne in resultat.classement.lignes] == [1, 2, 3, 4, 5, 6]
    assert resultat.plages_indecises == ()


def test_un_ex_aequo_interne_reste_indecis_sans_contaminer_le_groupe_suivant() -> None:
    """⚠️ **Trou de couverture relevé en revue (axes B et D).** Le seul test d'indécision employait
    des poules **sans ex æquo** : il aurait passé si `_par_groupe` rendait `[]` en dur.

    Deux archers que le §10.1 n'a pas séparés occupent deux rangs consécutifs de la phase, et cette
    paire — elle seule — reste indécise. La table `positions` a désormais **deux** producteurs
    (`_par_groupe` et la boucle par blocs) pour un unique consommateur, `_liaisons_internes` : c'est
    la couture que ce test surveille.
    """
    resultat = classement_de_poules(
        [_poule(1, 2, 3), _ex_aequo_au_rang_deux(4, 5, 6), _poule(7, 8, 9)],
        {archer: _ligne(archer) for archer in range(1, 10)},
        mode=ModeDeComposition.PAR_NIVEAU,
    )
    assert resultat.plages_indecises == ((5, 6),)
