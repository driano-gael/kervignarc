"""Tests de l'adapter `GenerateurPalmaresPdf` (E06US004, élargi par E16US014).

⚠️ **Cet adapter n'avait AUCUN test**, et c'est ce qui a laissé un bloquant traverser trois passes
de revue. Les deux seules assertions qui le traversaient (`test_palmares_api`) vérifiaient
`status_code == 200` et un flux commençant par `%PDF` ; le test qui *prétendait* couvrir le cas
fautif passait par le double `_FauxGenerateurPalmares`, lequel ne rend rien — il a fabriqué la
confiance pendant que le vrai générateur jetait les podiums qu'on venait de lui passer.

Tests **après implémentation** (règle 9 : intégration sur les adapters, pas d'oracle en jeu) : ce
qui se vérifie ici est le **contrat de rendu**, pas la règle de composition des podiums, couverte
en pur par `test_domain_podiums.py`.

Le document est inspecté par `_corps()` plutôt que par le PDF rendu : ReportLab n'offre pas de
lecture, et l'objet `Flowable` porte exactement ce que l'adapter a décidé d'émettre.
"""

from __future__ import annotations

from dataclasses import replace

from reportlab.platypus import Flowable, Paragraph

from domain.classement import StatutClassement
from domain.palmares import LignePalmares, OriginePalmares, Palmares
from domain.podium import PorteePodium, ReglagePodiums
from infrastructure.pdf.palmares import GenerateurPalmaresPdf

_REGLAGE = ReglagePodiums(portees=frozenset({PorteePodium.SCRATCH}))


def _ligne(archer_id: int, rang: int, categorie_id: int = 1) -> LignePalmares:
    """Une ligne classée par les duels — la seule forme qui peut occuper une place."""
    return LignePalmares(
        rang_min=rang,
        rang_max=rang,
        rang_categorie_min=rang,
        rang_categorie_max=rang,
        rang_club_min=rang,
        rang_club_max=rang,
        decerne=True,
        en_lice=False,
        archer_id=archer_id,
        nom=f"NOM{archer_id}",
        prenom="Jean",
        categorie_id=categorie_id,
        categorie_libelle="Senior Homme",
        club_id=1,
        club_libelle="Compagnie de Kervignarc",
        origine=OriginePalmares.DUELS,
        statut=StatutClassement.EN_LICE,
    )


def _textes(elements: list[Flowable]) -> list[str]:
    """Le texte des paragraphes émis. Les tables n'en portent pas : elles ne servent pas ici."""
    return [element.text for element in elements if isinstance(element, Paragraph)]


def test_un_filtre_qui_vide_le_classement_ne_retire_pas_les_podiums() -> None:
    """**Le bloquant de la 3ᵉ passe, au seul endroit où il vivait.**

    Filtrer sur une catégorie sans inscrit — atteignable en un clic, la déroulante liste toutes les
    catégories du tournoi — rendait `affiche` vide. La garde de vacuité étant posée dessus, le
    document sortait réduit à « Aucun archer classé » alors que le tournoi est classé. C'est celui
    qu'on affiche au mur.
    """
    complet = Palmares(lignes=(_ligne(1, 1), _ligne(2, 2)))
    vide = Palmares(lignes=())

    corps = GenerateurPalmaresPdf()._corps("Salle 18m", complet, vide, _REGLAGE)

    textes = _textes(corps)
    assert "Podium — Toutes catégories" in textes, "les podiums restent, ils sont ceux du tournoi"
    assert "Aucun archer classé." not in textes, "le tournoi EST classé"
    assert "Aucun archer dans la sélection imprimée." in textes, "seul le classement est vide"


def test_un_palmares_reellement_vide_ne_dit_que_cela() -> None:
    """La garde de vacuité n'est pas supprimée, elle est **portée sur le bon palmarès**.

    Sans elle, le scratch — qui ne regroupe rien, donc existe toujours — fabriquait un bloc à
    effectif zéro au-dessus duquel l'écran écrivait une phrase d'état sur personne.
    """
    vide = Palmares(lignes=())

    corps = GenerateurPalmaresPdf()._corps("Salle 18m", vide, vide, _REGLAGE)

    assert "Aucun archer classé." in _textes(corps)
    assert not [t for t in _textes(corps) if t.startswith("Podium —")]


def test_un_bloc_sans_place_ne_s_imprime_pas() -> None:
    """Sur le papier, un tableau à en-tête seul se lit comme un groupe sans archers.

    L'écran, lui, garde le bloc et **nomme** l'attente (parti `P-3`, ADR-0103 §6) : il peut, le
    papier non. C'est la seule divergence assumée entre les deux surfaces.
    """
    en_lice = _ligne(1, 1)
    complet = Palmares(lignes=(replace(en_lice, en_lice=True),))

    corps = GenerateurPalmaresPdf()._corps("Salle 18m", complet, complet, _REGLAGE)

    assert not [t for t in _textes(corps) if t.startswith("Podium —")]
    assert "Classement complet" in _textes(corps)


def test_le_document_rendu_est_un_pdf_non_vide() -> None:
    """Le chemin complet, ReportLab compris — `_corps` seul ne prouve pas que le rendu passe."""
    complet = Palmares(lignes=(_ligne(1, 1),))

    document = GenerateurPalmaresPdf().palmares(
        "Salle 18m", complet=complet, affiche=complet, reglage=_REGLAGE
    )

    assert document.startswith(b"%PDF")
    assert len(document) > 1000


def test_la_table_du_classement_suit_la_selection_demandee() -> None:
    """Le **miroir** du cas précédent, et il manquait : les podiums viennent de `complet`, mais la
    table du classement doit venir d'`affiche`.

    Sans ce cas, remplacer `affiche.lignes` par `complet.lignes` dans `_table_classement` laissait
    toute la suite verte — le CA « un podium est celui du tournoi, pas de la vue » n'était pris que
    par un seul de ses deux bouts, sur le document affiché au mur.
    """
    complet = Palmares(lignes=(_ligne(1, 1), _ligne(2, 2), _ligne(3, 3, categorie_id=2)))
    affiche = complet.pour_categorie(2)

    corps = GenerateurPalmaresPdf()._corps("Salle 18m", complet, affiche, _REGLAGE)

    table = corps[-1]
    noms = [cellule[2] for cellule in table._cellvalues[1:]]
    assert noms == ["NOM3"], "la table ne porte que la catégorie demandée"
    assert "Podium — Toutes catégories" in _textes(corps), "le podium, lui, reste celui du tournoi"


def test_le_classement_des_clubs_s_imprime_avec_ses_trois_colonnes_de_metaux() -> None:
    """E16US017 : le trophée du club se remet en même temps que les médailles, donc il figure sur
    la même feuille — l'organisateur n'a pas un second document à sortir au pied du podium.

    ⚠️ **Assertion positionnelle, relevée en revue (axe B)** : la 1ʳᵉ rédaction ne vérifiait que la
    présence du titre. Une permutation `argent` ↔ `bronze` dans le générateur restait verte — et un
    trophée remis sur la mauvaise colonne est le « cohérent et faux » que `DETTE-029` décrit. Les
    trois compteurs sont donc **distincts** ici.
    """
    # Deux archers au rang 1, un au rang 2, aucun au rang 3 : le seul club de la fixture sort à
    # **2 or / 1 argent / 0 bronze**. Trois valeurs distinctes — c'est ce qui fait tomber une
    # permutation. (Palmarès monté à la main : la composition réaliste est couverte au domaine.)
    palmares = Palmares(lignes=(_ligne(1, 1), _ligne(2, 1), _ligne(3, 2)))

    corps = GenerateurPalmaresPdf()._corps(
        "Tournoi", complet=palmares, affiche=palmares, reglage=_REGLAGE
    )

    assert "Classement des clubs" in _textes(corps)
    table = next(
        element
        for element in corps
        if getattr(element, "_cellvalues", [[None]])[0]
        == ["Rang", "Club", "Or", "Argent", "Bronze"]
    )
    assert table._cellvalues[1] == ["1", "Compagnie de Kervignarc", "2", "1", "0"]


def test_le_classement_des_clubs_ne_s_imprime_pas_sans_base() -> None:
    """Réglé sur la seule portée *club*, le décompte n'a aucune base : le papier saute la section.

    ⚠️ Même parti que `_podiums` : une table vide se lirait « aucun club », alors que la cause est
    le réglage. L'écran, lui, peut l'écrire — le papier ne le peut pas.
    """
    palmares = Palmares(lignes=(_ligne(1, 1), _ligne(2, 2)))
    reglage = replace(_REGLAGE, portees=frozenset({PorteePodium.CLUB}))

    corps = GenerateurPalmaresPdf()._corps(
        "Tournoi", complet=palmares, affiche=palmares, reglage=reglage
    )

    assert "Classement des clubs" not in _textes(corps)


def test_un_decompte_provisoire_se_dit_sur_le_papier() -> None:
    """Une feuille imprimée à 10 h et relue à 17 h n'a aucun indice de fraîcheur : le document doit
    porter lui-même la réserve, là où l'écran se rafraîchit tout seul."""
    palmares = Palmares(lignes=(_ligne(1, 1), _ligne(2, 2)), duels_non_commences=True)

    corps = GenerateurPalmaresPdf()._corps(
        "Tournoi", complet=palmares, affiche=palmares, reglage=_REGLAGE
    )

    assert any(texte.startswith("Décompte provisoire") for texte in _textes(corps))


def test_le_papier_dit_qu_aucun_club_n_a_de_medaille_au_lieu_de_se_taire() -> None:
    """⚠️ **Relevé en revue (axe B)** : la 1ʳᵉ rédaction sautait la section dans ce cas, ce qui la
    faisait diverger de l'écran — qui, lui, nomme la cause.

    Le cas est atteignable et il est **informatif** : un tournoi dont aucun archer n'a de club
    rattaché est une fiche d'inscription à corriger. Le taire prive l'organisateur du signal.
    """
    sans_club = replace(_ligne(1, 1), club_id=None, club_libelle=None)
    palmares = Palmares(lignes=(sans_club,))

    corps = GenerateurPalmaresPdf()._corps(
        "Tournoi", complet=palmares, affiche=palmares, reglage=_REGLAGE
    )

    assert "Classement des clubs" in _textes(corps), "la section reste : la base existe"
    # Le papier dit sa base, comme l'écran.
    assert "Compté sur : Toutes catégories" in _textes(corps)
    # « encore » seulement si le décompte peut bouger : ici le tableau est joué, il ne bougera plus.
    assert "Aucun club n'a de médaille." in _textes(corps)


def test_un_reglage_vide_n_imprime_aucune_section_de_clubs() -> None:
    """Ne rien récompenser est un réglage licite (ADR-0103 §1) : il n'y a rien à commenter."""
    palmares = Palmares(lignes=(_ligne(1, 1), _ligne(2, 2)))

    corps = GenerateurPalmaresPdf()._corps(
        "Tournoi",
        complet=palmares,
        affiche=palmares,
        reglage=replace(_REGLAGE, portees=frozenset()),
    )

    assert "Classement des clubs" not in _textes(corps)


def test_le_filtre_par_categorie_ne_rogne_pas_le_classement_des_clubs_imprime() -> None:
    """Même parti que les podiums (ADR-0103 §7) : le trophée est celui du **tournoi**.

    ⚠️ **Relevé en revue (axe C2)** : l'invariant « composer sur `complet`, jamais sur `affiche` »
    n'était ancré qu'au site API. Le papier, lui, part au mur — et personne n'y relit les colonnes.
    """
    complet = Palmares(lignes=(_ligne(1, 1), _ligne(2, 2), _ligne(3, 3, categorie_id=2)))
    affiche = complet.pour_categorie(2)

    entier = GenerateurPalmaresPdf()._corps("Tournoi", complet, complet, _REGLAGE)
    filtre = GenerateurPalmaresPdf()._corps("Tournoi", complet, affiche, _REGLAGE)

    clubs = [
        element._cellvalues
        for corps in (entier, filtre)
        for element in corps
        if getattr(element, "_cellvalues", [[None]])[0]
        == ["Rang", "Club", "Or", "Argent", "Bronze"]
    ]
    assert len(clubs) == 2, "la section est imprimée dans les deux cas"
    assert clubs[0] == clubs[1], "et au chiffre près : le filtre ne la touche pas"
