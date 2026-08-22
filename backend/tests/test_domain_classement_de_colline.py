"""E05US027 — le **classement de phase** d'une colline, prêt à être prélevé.

Tests dérivés du **CA** (`stories/E05-moteur-phases.md` → E05US027), écrits **avant**
l'implémentation : ce qu'ils décrivent est la règle voulue, pas le code livré (règle 9).

Deux puces du CA se rejoignent ici : « **habiter le contrat de phase jouable** », dont la 4ᵉ
question (ADR-0083 §1) est « *qui est classé, et dans quel ordre ?* », et « **le classement se lit
de l'ordre final de la colline** ».

**Ce qui distingue ce classement de ses trois jumeaux**, et le rend le plus court des quatre :

- un tableau doit **inventer** un ordre entre battus d'un même tour ;
- une phase de poules doit inventer un ordre entre vainqueurs de groupes différents, faute de quoi
  rien ne compare la poule 1 à la poule 2 — d'où ses blocs indécis ;
- un système suisse rend un ordre total, mais peut laisser des **ex æquo irréductibles** que même
  les critères FFTA ne séparent pas ;
- une colline, elle, **est** son classement. Deux participants n'occupent jamais la même position :
  l'ordre est total par construction, et `plages_indecises` est donc **toujours vide**.

⚠️ **C'est une propriété, pas une simplification de confort.** Une plage indécise déclenche le refus
d'ADR-0081 (« une phase attend que sa source ait départagé les places qu'elle prélève »). Qu'elle
soit vide ici signifie qu'un prélèvement dans une colline n'est **jamais** bloqué par une égalité —
et ce test existe pour que l'affirmation reste vérifiée si le format évoluait.
"""

from __future__ import annotations

from domain.archer import ArcherId
from domain.classement import LigneClassement, StatutClassement
from domain.classement_de_colline import classement_de_colline
from domain.participant import Participant


def _ligne(archer_id: int, rang: int) -> LigneClassement:
    """Une ligne de classement amont — l'identité, que la phase reprend telle quelle."""
    return LigneClassement(
        archer_id=archer_id,
        nom=f"Nom{archer_id}",
        prenom=f"Prenom{archer_id}",
        categorie_id=1,
        categorie_libelle="Senior Homme Arc Classique",
        cible=None,
        club_id=None,
        total=600 - rang,
        nb_dix=10,
        nb_neuf=10,
        rang_scratch=rang,
        rang_categorie=rang,
        statut=StatutClassement.EN_LICE,
    )


def _lignes(nb: int) -> dict[ArcherId, LigneClassement]:
    return {archer_id: _ligne(archer_id, archer_id) for archer_id in range(1, nb + 1)}


def _colline(*archer_ids: int) -> tuple[tuple[Participant, int], ...]:
    """Ce que `colline.classement_colline` rend : la colline, position par position."""
    return tuple(
        (Participant.individuel(archer_id), position)
        for position, archer_id in enumerate(archer_ids, start=1)
    )


def test_le_classement_de_phase_suit_l_ordre_final_de_la_colline() -> None:
    """**Le CA de l'US** : le classement *est* la colline, dans son état final.

    Le décor est discriminant : la colline finit `3, 1, 2`, c'est-à-dire un ordre qu'aucune lecture
    du classement amont ne produirait (il rendrait `1, 2, 3`). Un module qui se contenterait de
    recopier la source rendrait `[1, 2, 3]` et ce test tomberait.
    """
    source = classement_de_colline(_colline(3, 1, 2), _lignes(3))

    assert [ligne.archer_id for ligne in source.classement.lignes] == [3, 1, 2]
    assert [ligne.rang_scratch for ligne in source.classement.lignes] == [1, 2, 3]


def test_une_colline_ne_declare_aucun_ex_aequo() -> None:
    """Aucun ex æquo n'est possible : deux archers n'occupent jamais la même position.

    C'est ce qui garantit qu'un prélèvement visant une colline n'est jamais retenu par une
    **égalité** — il n'y a rien à départager.

    ⚠️ **Ce test s'appelait `…_ne_declare_aucune_plage_indecise`, et le nom promettait trop**
    (relevé en 2ᵉ passe de revue). Il porte sur ce que le **domaine** rend, or le service surcharge
    ce champ depuis E05US027 : une colline inachevée déclare bien une plage indécise, par
    **inachèvement** et non par égalité. Le test restait vert tout en gardant une affirmation
    devenue fausse du comportement observable — un garde-fou nommé qui ne garde pas ce que son nom
    dit. Le renommer était le correctif, pas le supprimer : ce qu'il vérifie reste vrai et utile.
    """
    source = classement_de_colline(_colline(3, 1, 2), _lignes(3))

    assert source.plages_indecises == ()


def test_une_colline_vide_est_un_classement_vide_et_non_une_erreur() -> None:
    """Une phase avale qui prélève dans une colline pas encore commencée lit « rien à prendre ».

    Même régime que les trois jumeaux : c'est une réponse licite, pas un cas d'erreur. Sans cette
    porte, l'écran de saisie et toute phase avale sortaient en 500 sur une phase encore vide — le
    correctif que les poules ont dû faire en revue.
    """
    source = classement_de_colline((), _lignes(3))

    assert source.classement.lignes == ()
    assert source.plages_indecises == ()


def test_un_participant_absent_du_classement_amont_est_ecarte_avant_la_numerotation() -> None:
    """Filtrer **avant** de numéroter, jamais après — même geste que les trois jumeaux.

    `preleves` lit `rang_scratch` comme un indice de fenêtre : une numérotation trouée ferait
    manquer des archers à une fenêtre par ailleurs correcte (« les rangs 1 à 2 » n'en prendrait
    qu'un). L'archer 9 n'existe pas au classement amont ; les deux autres doivent occuper les
    positions 1 et 2, pas 1 et 3.
    """
    source = classement_de_colline(_colline(3, 9, 1), _lignes(3))

    assert [ligne.archer_id for ligne in source.classement.lignes] == [3, 1]
    assert [ligne.rang_scratch for ligne in source.classement.lignes] == [1, 2]


def test_un_participant_equipe_est_ecarte() -> None:
    """Le `ref_id` d'une équipe n'est pas un archer (ADR-0028) — sa résolution vient avec
    E13US002.

    Les trois classements de phase existants l'écartent déjà ; ne pas le faire ici ferait résoudre
    un identifiant d'équipe dans la table des archers, donc décrirait le mauvais tireur.
    """
    colline = (
        (Participant.individuel(1), 1),
        (Participant.equipe(2), 2),
        (Participant.individuel(3), 3),
    )

    source = classement_de_colline(colline, _lignes(3))

    assert [ligne.archer_id for ligne in source.classement.lignes] == [1, 3]
