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

from domain.classement import LigneClassement
from domain.classement_de_poules import classement_de_poules
from domain.participant import Participant
from domain.politiques import DecompteDepartage
from domain.poule import (
    ConfigurationPoules,
    ModeDeComposition,
    Poule,
    RangPoule,
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
