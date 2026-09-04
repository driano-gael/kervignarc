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


def test_le_classement_des_clubs_s_imprime_avec_le_palmares() -> None:
    """E16US017 : le trophée du club se remet en même temps que les médailles, donc il figure sur
    la même feuille — l'organisateur n'a pas un second document à sortir au pied du podium."""
    palmares = Palmares(lignes=(_ligne(1, 1), _ligne(2, 2)))

    corps = GenerateurPalmaresPdf()._corps(
        "Tournoi", complet=palmares, affiche=palmares, reglage=_REGLAGE
    )

    assert "Classement des clubs" in _textes(corps)


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
