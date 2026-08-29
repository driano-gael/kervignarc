"""Tests de la politique pure de la **recherche transverse** (E16US010).

Source : `stories/E16-retours-maquettes.md`, E16US010, puce « **CA — recherche transverse hors
pilotage** » : *« entité choisie dans une déroulante + champ de saisie, complétion, ouverture de la
fiche en modification »*, et le questionnaire A02 dont elle vient : *« une complétion de recherche
montre une liste des items possibles avec la possibilité de cliquer dessus »*.

⚠️ **Ces tests ont été écrits APRÈS `domain/recherche.py`, contrairement à la règle 9** (le
domaine se teste depuis le CA, avant d'implémenter). La liste des cas ci-dessous avait bien été
dérivée du CA avant d'écrire le module, mais l'ordre a été inversé à l'exécution : c'est un
manquement, signalé plutôt que masqué. Il est relevé au corps du commit.

Domaine pur : aucune I/O — on part de résultats déjà constitués.
"""

from __future__ import annotations

from domain.recherche import (
    LIMITE_COMPLETION,
    EntiteRecherchable,
    ResultatRecherche,
    classer,
    completer,
    correspond,
)


def _archer(id_: int, libelle: str) -> ResultatRecherche:
    return ResultatRecherche(entite=EntiteRecherchable.ARCHER, id=id_, libelle=libelle)


def test_la_correspondance_replie_la_casse_et_les_accents() -> None:
    """Sur tablette, un nom se saisit sans accents — « leveque » doit trouver « Lévêque ».

    C'est le même repli que la détection de doublons (`cle_nom`) : deux normalisations
    différentes rendraient la recherche et le rapprochement incohérents sur les mêmes fiches.
    """
    assert correspond("leveque", "Lévêque Jean") is True
    assert correspond("LÉVÊQUE", "leveque jean") is True


def test_la_correspondance_cherche_dans_le_libelle_entier_pas_seulement_au_debut() -> None:
    """Un nom composé se saisit souvent par sa seconde moitié, et le prénom peut précéder."""
    assert correspond("dupont", "Jean Dupont") is True
    assert correspond("mer", "Compagnie de Saint-Mérien") is True


def test_plusieurs_champs_sont_interrogeables() -> None:
    """Chercher un archer par son club doit marcher : le service passe les deux champs."""
    assert correspond("arc club", "Jean Dupont", "Arc Club de Kervignarc") is True


def test_un_fragment_vide_ne_correspond_a_rien() -> None:
    """Sinon la déroulante déverse tout le référentiel dès qu'on la choisit.

    ⚠️ Un fragment fait **d'espaces seuls** compte comme vide : `cle_nom` replie les bords, et
    « contient la chaîne vide » est vrai de tout libellé.
    """
    assert correspond("", "Jean Dupont") is False
    assert correspond("   ", "Jean Dupont") is False


def test_les_prefixes_sortent_en_tete_de_la_completion() -> None:
    """Taper « du » propose « Dupont » avant « Bordure » — sinon la complétion ne sert à rien."""
    classes = classer([_archer(1, "Bordure Luc"), _archer(2, "Dupont Jean")], "du")

    assert [r.libelle for r in classes] == ["Dupont Jean", "Bordure Luc"]


def test_a_privilege_egal_le_classement_est_alphabetique_et_deterministe() -> None:
    """Deux préfixes valides se rangent par libellé replié, l'`id` tranchant les homonymes.

    Un ordre instable ferait sauter les propositions d'une frappe à l'autre.
    """
    classes = classer(
        [_archer(3, "Dupré Éva"), _archer(1, "Dupont Jean"), _archer(2, "dupont ana")], "dup"
    )

    assert [r.id for r in classes] == [2, 1, 3]


def test_la_completion_borne_la_liste_mais_annonce_le_total_reel() -> None:
    """« 8 sur 34 » : une liste tronquée en silence se lit « il n'y a que ça ».

    L'organisateur cesserait alors de préciser sa saisie, alors que c'est le geste qui le mène à
    la bonne fiche.
    """
    beaucoup = [_archer(i, f"Dupont {i:02d}") for i in range(20)]

    recherche = completer(beaucoup, "dupont")

    assert len(recherche.resultats) == LIMITE_COMPLETION
    assert recherche.total == 20
