"""E05US026 — le **classement de phase** d'un système suisse, prêt à être prélevé.

Tests dérivés du **CA** (`stories/E05-moteur-phases.md` → E05US026), écrits **avant**
l'implémentation : ce qu'ils décrivent est la règle voulue, pas le code livré (règle 9).

Le CA n'a pas de puce « classement » en propre — il dit « **habiter le contrat de phase jouable** »,
et la 4ᵉ question de ce contrat (ADR-0083 §1) est « *qui est classé, et dans quel ordre ?* ». Y
répondre est la condition pour qu'une phase avale prélève (`classement_lisible`), et c'est ce que
ces tests fixent.

**Ce qui distingue ce classement de celui des poules.** Une phase de poules range « par rang de
poule d'abord » et déclare ses blocs **indécis** parce que rien ne compare deux vainqueurs de
groupes différents. Un système suisse n'a pas ce problème : tout le monde joue dans le même vivier,
et `classement_suisse` rend un ordre **total** — points, puis Buchholz, puis critères FFTA. Le seul
indécis qui subsiste est l'**ex æquo irréductible** : deux archers que même les critères FFTA ne
séparent pas. C'est exactement le cas qu'ADR-0081 demande de déclarer plutôt que de trancher au
hasard.
"""

from __future__ import annotations

from domain.archer import ArcherId
from domain.classement import Classement, LigneClassement, StatutClassement
from domain.classement_de_suisse import classement_de_suisse
from domain.participant import Participant
from domain.politiques import DecompteDepartage
from domain.suisse import RangSuisse


def _ligne(archer_id: int, rang: int) -> LigneClassement:
    """Une ligne de classement de qualification — l'identité, que la phase reprend telle quelle."""
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


def _rang(rang: int, archer_id: int, points: int, *, ex_aequo: bool = False) -> RangSuisse:
    return RangSuisse(
        rang=rang,
        participant=Participant.individuel(archer_id),
        points=points,
        buchholz=0,
        decompte=DecompteDepartage(nb_dix=0, nb_neuf=0),
        ex_aequo=ex_aequo,
    )


def test_le_classement_de_phase_suit_l_ordre_du_suisse() -> None:
    """CA « habiter le contrat », 4ᵉ question : qui est classé, et dans quel ordre.

    L'ordre rendu est celui de `classement_suisse` — points, Buchholz, critères FFTA — **réécrit
    dans l'espace de rangs de la phase** (1..N). C'est `rang_scratch` que `preleves` lit : le
    renuméroter est tout le travail de ce module, l'ordre étant déjà décidé par le moteur.
    """
    rangs = (_rang(1, 3, 8), _rang(2, 1, 6), _rang(3, 2, 4))

    source = classement_de_suisse(rangs, _lignes(3))

    assert [ligne.archer_id for ligne in source.classement.lignes] == [3, 1, 2]
    assert [ligne.rang_scratch for ligne in source.classement.lignes] == [1, 2, 3]


def test_un_classement_sans_ex_aequo_n_a_aucune_plage_indecise() -> None:
    """Un suisse départagé est **entièrement décidé** — et c'est sa différence avec les poules.

    Une phase de poules déclare ses blocs indécis par défaut : rien ne compare le vainqueur de la
    poule 1 à celui de la poule 2. Ici tout le monde a joué dans le même vivier, donc l'ordre est
    total et une phase avale peut prélever **n'importe quelle** fenêtre.
    """
    source = classement_de_suisse((_rang(1, 1, 8), _rang(2, 2, 6)), _lignes(2))

    assert source.plages_indecises == ()
    assert source.coupe(1, 1) is None


def test_deux_archers_ex_aequo_forment_une_plage_indecise() -> None:
    """CA « habiter le contrat » + ADR-0081 : on **déclare** l'égalité, on ne la tranche pas.

    Deux archers que ni les points, ni le Buchholz, ni les critères FFTA ne séparent partagent le
    rang 2. Les départager sur leur rang de qualification serait exactement la faute qu'ADR-0081
    nomme : une population bien formée, plausible, et fausse.

    La fenêtre « le rang 2 » **coupe** donc la plage et doit être refusée ; « les rangs 2 à 3 » la
    **contient** et passe — on prend les deux ex æquo, ce qui est la bonne réponse.
    """
    rangs = (
        _rang(1, 1, 8),
        _rang(2, 2, 6, ex_aequo=True),
        _rang(2, 3, 6, ex_aequo=True),
        _rang(4, 4, 2),
    )

    source = classement_de_suisse(rangs, _lignes(4))

    assert source.plages_indecises == ((2, 3),)
    assert source.coupe(2, 2) == (2, 3)
    assert source.coupe(2, 3) is None
    assert source.coupe(1, 1) is None


def test_le_rang_partage_ne_renumerote_pas_le_classement_de_phase() -> None:
    """`rang_scratch` est une **position**, pas le rang sportif — et les deux diffèrent aux ex æquo.

    `classement_suisse` applique la convention « 1224 » : deux ex æquo au rang 2 laissent le rang 3
    vacant, et le suivant est 4ᵉ. Mais `preleves` lit `rang_scratch` comme un **indice de fenêtre**
    (« les rangs 1 à 3 ») : y recopier le rang sportif ferait disparaître la 3ᵉ place du classement
    de phase, et « les rangs 1 à 3 » ne prendrait que deux archers.

    Les deux informations coexistent donc : le rang sportif reste lisible sur `RangSuisse`, la
    position sert au prélèvement. La plage indécise, elle, dit ce que la position ne dit pas.
    """
    rangs = (
        _rang(1, 1, 8),
        _rang(2, 2, 6, ex_aequo=True),
        _rang(2, 3, 6, ex_aequo=True),
        _rang(4, 4, 2),
    )

    source = classement_de_suisse(rangs, _lignes(4))

    assert [ligne.rang_scratch for ligne in source.classement.lignes] == [1, 2, 3, 4]


def test_le_rang_premier_n_est_pas_pose_ici() -> None:
    """Une phase ne sait pas quelle tranche du tournoi elle dispute — c'est l'affaire du service.

    Même parti que `classement_de_tableau` et `classement_de_poules` : `rang_premier` est une
    propriété de la **place dans le déroulé**, que seul le service qui remonte la chaîne connaît
    (`application/prelevement.py:tranche`). Le poser ici donnerait à la fonction une valeur qu'elle
    ne peut pas vérifier — c'est-à-dire `DETTE-034` rouverte.
    """
    source = classement_de_suisse((_rang(1, 1, 8), _rang(2, 2, 6)), _lignes(2))

    assert source.rang_premier == 1


def test_un_participant_absent_du_classement_est_ecarte() -> None:
    """Filtrer **avant** de numéroter : une numérotation trouée ferait manquer des archers.

    Le cas vise les participants **équipe** (leur `ref_id` n'est pas un archer, ADR-0028) et les
    archers sortis du classement entre deux lectures. Même geste que `classement_de_poules._retenus`
    — et pour la même raison : `preleves` lit `rang_scratch`, donc un trou dans la numérotation
    ferait qu'une fenêtre par ailleurs correcte manquerait des archers.
    """
    rangs = (_rang(1, 1, 8), _rang(2, 99, 6), _rang(3, 2, 4))

    source = classement_de_suisse(rangs, _lignes(2))

    assert [ligne.archer_id for ligne in source.classement.lignes] == [1, 2]
    assert [ligne.rang_scratch for ligne in source.classement.lignes] == [1, 2]


def test_un_classement_vide_se_lit_sans_erreur() -> None:
    """Une phase pas encore jouée est un classement **vide**, pas une erreur.

    Même parti que la photo vide d'une phase de poules sans participant : une phase avale qui
    prélève dans un suisse pas encore commencé doit lire « rien à prendre », pas tomber en 500.
    """
    source = classement_de_suisse((), {})

    assert source.classement == Classement(lignes=())
    assert source.plages_indecises == ()
