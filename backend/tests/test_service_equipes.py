"""Tests du service des équipes (E13US002) — écrits depuis le CA de `stories/E13-equipes.md`.

Le domaine (`Equipe`, `ecarts_de_composition`) est couvert par `test_domain_equipe.py` ; ici, les
règles **d'ensemble** que seul le service voit : tournoi, unicité du nom, appartenance au tournoi,
une équipe par type, et la lecture de la conformité depuis la catégorie de chaque membre.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

import pytest

from application.equipes import ServiceEquipes
from application.erreurs import (
    ArcherDejaEnEquipe,
    ArcherHorsTournoi,
    CompositionEquipeVerrouillee,
    EquipeIntrouvable,
    MembreIntrouvable,
    NomEquipeDejaPris,
    TournoiIntrouvable,
)
from domain.archer import Archer, ArcherId
from domain.categorie import Categorie, CategorieId, SexeCategorie
from domain.equipe import EcartComposition, TypeEquipe
from domain.erreurs import NomEquipeInvalide
from domain.tournoi import Tournoi, TournoiId
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxEquipeRepository,
    FauxTournoiRepository,
    FauxVerrouDeComposition,
)

_DATE = datetime.date(2026, 11, 14)


@dataclass
class Decor:
    service: ServiceEquipes
    equipes: FauxEquipeRepository
    archers: FauxArcherRepository
    categories: FauxCategorieRepository
    tournoi_id: TournoiId
    autre_tournoi_id: TournoiId
    clh: CategorieId
    clf: CategorieId
    verrou: FauxVerrouDeComposition

    def archer(
        self, prenom: str, categorie_id: CategorieId | None = None, tournoi_id: int | None = None
    ) -> ArcherId:
        archer = self.archers.ajouter(
            Archer.creer(
                "Tell",
                prenom,
                tournoi_id if tournoi_id is not None else self.tournoi_id,
                categorie_id if categorie_id is not None else self.clh,
            )
        )
        assert archer.id is not None
        return archer.id


@pytest.fixture
def decor() -> Decor:
    tournois = FauxTournoiRepository()
    archers = FauxArcherRepository()
    categories = FauxCategorieRepository()
    equipes = FauxEquipeRepository()
    tournoi = tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
    autre = tournois.ajouter(Tournoi.creer("Voisin", _DATE))
    assert tournoi.id is not None and autre.id is not None
    clh = categories.ajouter(
        Categorie.creer(tournoi.id, "Senior 1 H CL", arme="CL", sexe=SexeCategorie.HOMME)
    )
    clf = categories.ajouter(
        Categorie.creer(tournoi.id, "Senior 1 F CL", arme="CL", sexe=SexeCategorie.FEMME)
    )
    assert clh.id is not None and clf.id is not None
    verrou = FauxVerrouDeComposition()
    return Decor(
        service=ServiceEquipes(equipes, tournois, archers, categories, verrou=verrou),
        verrou=verrou,
        equipes=equipes,
        archers=archers,
        categories=categories,
        tournoi_id=tournoi.id,
        autre_tournoi_id=autre.id,
        clh=clh.id,
        clf=clf.id,
    )


# --- CA 1 : CRUD, nom non vide et unique, effectif prérempli selon le type ---


def test_creer_preremplit_l_effectif_selon_le_type(decor: Decor) -> None:
    standard = decor.service.creer(decor.tournoi_id, "Les Archers", TypeEquipe.STANDARD, None)
    mixte = decor.service.creer(decor.tournoi_id, "Le Duo", TypeEquipe.MIXTE, None)
    assert standard.equipe.effectif_attendu == 3
    assert mixte.equipe.effectif_attendu == 2


def test_creer_garde_un_effectif_choisi(decor: Decor) -> None:
    vue = decor.service.creer(decor.tournoi_id, "Les Quatre", TypeEquipe.STANDARD, 4)
    assert vue.equipe.effectif_attendu == 4


def test_creer_dans_un_tournoi_inconnu_est_refuse(decor: Decor) -> None:
    with pytest.raises(TournoiIntrouvable):
        decor.service.creer(999, "Les Archers", TypeEquipe.STANDARD, None)


def test_un_nom_vide_est_refuse(decor: Decor) -> None:
    with pytest.raises(NomEquipeInvalide):
        decor.service.creer(decor.tournoi_id, "   ", TypeEquipe.STANDARD, None)


def test_un_nom_deja_pris_dans_le_tournoi_est_refuse_sans_egard_a_la_casse(decor: Decor) -> None:
    decor.service.creer(decor.tournoi_id, "Les Archers", TypeEquipe.STANDARD, None)
    with pytest.raises(NomEquipeDejaPris):
        decor.service.creer(decor.tournoi_id, "  les archers ", TypeEquipe.MIXTE, None)


def test_le_meme_nom_reste_libre_dans_un_autre_tournoi(decor: Decor) -> None:
    decor.service.creer(decor.tournoi_id, "Les Archers", TypeEquipe.STANDARD, None)
    vue = decor.service.creer(decor.autre_tournoi_id, "Les Archers", TypeEquipe.STANDARD, None)
    assert vue.equipe.tournoi_id == decor.autre_tournoi_id


def test_renommer_vers_un_nom_pris_est_refuse(decor: Decor) -> None:
    decor.service.creer(decor.tournoi_id, "Les Archers", TypeEquipe.STANDARD, None)
    autre = decor.service.creer(decor.tournoi_id, "Les Flèches", TypeEquipe.STANDARD, None)
    assert autre.equipe.id is not None
    with pytest.raises(NomEquipeDejaPris):
        decor.service.modifier(
            decor.tournoi_id, autre.equipe.id, "LES ARCHERS", TypeEquipe.STANDARD, None
        )


def test_garder_son_propre_nom_au_renommage_n_est_pas_un_conflit(decor: Decor) -> None:
    vue = decor.service.creer(decor.tournoi_id, "Les Archers", TypeEquipe.STANDARD, None)
    assert vue.equipe.id is not None
    modifiee = decor.service.modifier(
        decor.tournoi_id, vue.equipe.id, "les Archers", TypeEquipe.STANDARD, 4
    )
    assert (modifiee.equipe.nom, modifiee.equipe.effectif_attendu) == ("les Archers", 4)


def test_modifier_change_type_et_effectif_en_gardant_les_membres(decor: Decor) -> None:
    vue = decor.service.creer(decor.tournoi_id, "Les Archers", TypeEquipe.STANDARD, None)
    assert vue.equipe.id is not None
    guillaume = decor.archer("Guillaume")
    decor.service.ajouter_membre(decor.tournoi_id, vue.equipe.id, guillaume)
    modifiee = decor.service.modifier(
        decor.tournoi_id, vue.equipe.id, "Le Duo", TypeEquipe.MIXTE, None
    )
    assert modifiee.equipe.type is TypeEquipe.MIXTE
    assert modifiee.equipe.effectif_attendu == 2
    assert modifiee.equipe.membres == (guillaume,)


def test_supprimer_une_equipe_ne_touche_a_aucun_archer(decor: Decor) -> None:
    vue = decor.service.creer(decor.tournoi_id, "Les Archers", TypeEquipe.STANDARD, None)
    assert vue.equipe.id is not None
    guillaume = decor.archer("Guillaume")
    decor.service.ajouter_membre(decor.tournoi_id, vue.equipe.id, guillaume)
    decor.service.supprimer(decor.tournoi_id, vue.equipe.id)
    assert decor.service.lister(decor.tournoi_id) == []
    assert decor.archers.par_id(guillaume) is not None


def test_une_equipe_d_un_autre_tournoi_est_introuvable(decor: Decor) -> None:
    vue = decor.service.creer(decor.autre_tournoi_id, "Voisins", TypeEquipe.STANDARD, None)
    assert vue.equipe.id is not None
    with pytest.raises(EquipeIntrouvable):
        decor.service.supprimer(decor.tournoi_id, vue.equipe.id)
    with pytest.raises(EquipeIntrouvable):
        decor.service.modifier(decor.tournoi_id, vue.equipe.id, "X", TypeEquipe.STANDARD, None)
    with pytest.raises(EquipeIntrouvable):
        decor.service.ajouter_membre(decor.tournoi_id, vue.equipe.id, decor.archer("Walter"))


def test_une_equipe_inconnue_est_introuvable(decor: Decor) -> None:
    with pytest.raises(EquipeIntrouvable):
        decor.service.retirer_membre(decor.tournoi_id, 999, 1)


def test_lister_trie_par_nom_et_refuse_un_tournoi_inconnu(decor: Decor) -> None:
    decor.service.creer(decor.tournoi_id, "Zéphyr", TypeEquipe.STANDARD, None)
    decor.service.creer(decor.tournoi_id, "Étoile", TypeEquipe.STANDARD, None)
    decor.service.creer(decor.tournoi_id, "azur", TypeEquipe.MIXTE, None)
    assert [v.equipe.nom for v in decor.service.lister(decor.tournoi_id)] == [
        "azur",
        "Étoile",
        "Zéphyr",
    ]
    with pytest.raises(TournoiIntrouvable):
        decor.service.lister(999)


# --- CA 1 / CA 2 : ajouter et retirer un membre, du même tournoi seulement ---


def test_ajouter_puis_retirer_un_membre_dans_l_ordre_d_ajout(decor: Decor) -> None:
    vue = decor.service.creer(decor.tournoi_id, "Les Archers", TypeEquipe.STANDARD, None)
    assert vue.equipe.id is not None
    a, b = decor.archer("Guillaume"), decor.archer("Walter")
    decor.service.ajouter_membre(decor.tournoi_id, vue.equipe.id, b)
    apres = decor.service.ajouter_membre(decor.tournoi_id, vue.equipe.id, a)
    assert [m.archer_id for m in apres.membres] == [b, a]
    retiree = decor.service.retirer_membre(decor.tournoi_id, vue.equipe.id, b)
    assert retiree.equipe.membres == (a,)


def test_un_membre_expose_nom_prenom_et_libelle_de_categorie(decor: Decor) -> None:
    vue = decor.service.creer(decor.tournoi_id, "Les Archers", TypeEquipe.STANDARD, None)
    assert vue.equipe.id is not None
    guillaume = decor.archer("Guillaume")
    apres = decor.service.ajouter_membre(decor.tournoi_id, vue.equipe.id, guillaume)
    (membre,) = apres.membres
    assert (membre.archer_id, membre.nom, membre.prenom, membre.categorie) == (
        guillaume,
        "Tell",
        "Guillaume",
        "Senior 1 H CL",
    )


def test_un_archer_d_un_autre_tournoi_est_refuse(decor: Decor) -> None:
    vue = decor.service.creer(decor.tournoi_id, "Les Archers", TypeEquipe.STANDARD, None)
    assert vue.equipe.id is not None
    etranger = decor.archer("Walter", tournoi_id=decor.autre_tournoi_id)
    with pytest.raises(ArcherHorsTournoi):
        decor.service.ajouter_membre(decor.tournoi_id, vue.equipe.id, etranger)


def test_un_archer_inexistant_est_refuse(decor: Decor) -> None:
    vue = decor.service.creer(decor.tournoi_id, "Les Archers", TypeEquipe.STANDARD, None)
    assert vue.equipe.id is not None
    with pytest.raises(ArcherHorsTournoi):
        decor.service.ajouter_membre(decor.tournoi_id, vue.equipe.id, 999)


def test_ajouter_deux_fois_le_meme_archer_est_un_conflit_qui_le_nomme(decor: Decor) -> None:
    vue = decor.service.creer(decor.tournoi_id, "Les Archers", TypeEquipe.STANDARD, None)
    assert vue.equipe.id is not None
    guillaume = decor.archer("Guillaume")
    decor.service.ajouter_membre(decor.tournoi_id, vue.equipe.id, guillaume)
    with pytest.raises(ArcherDejaEnEquipe) as leve:
        decor.service.ajouter_membre(decor.tournoi_id, vue.equipe.id, guillaume)
    assert "« Guillaume Tell »" in str(leve.value)
    assert "« Les Archers »" in str(leve.value)


def test_retirer_un_non_membre_est_introuvable_en_le_nommant(decor: Decor) -> None:
    vue = decor.service.creer(decor.tournoi_id, "Les Archers", TypeEquipe.STANDARD, None)
    assert vue.equipe.id is not None
    walter = decor.archer("Walter")
    with pytest.raises(MembreIntrouvable) as leve:
        decor.service.retirer_membre(decor.tournoi_id, vue.equipe.id, walter)
    assert str(leve.value) == "« Walter Tell » ne figure pas dans l'équipe « Les Archers »."


def test_un_membre_disparu_entre_deux_lectures_est_ignore(decor: Decor) -> None:
    """`lister` tourne hors writer : un archer supprimé entre deux lectures n'est pas un 500."""
    vue = decor.service.creer(decor.tournoi_id, "Les Archers", TypeEquipe.STANDARD, None)
    assert vue.equipe.id is not None
    guillaume, walter = decor.archer("Guillaume"), decor.archer("Walter")
    decor.service.ajouter_membre(decor.tournoi_id, vue.equipe.id, guillaume)
    decor.service.ajouter_membre(decor.tournoi_id, vue.equipe.id, walter)
    decor.archers.supprimer(walter)  # l'équipe le garde : la suppression a « couru » la lecture

    (lue,) = decor.service.lister(decor.tournoi_id)

    assert [m.archer_id for m in lue.membres] == [guillaume]


# --- CA 3 : au plus une équipe par type ---


def test_une_seconde_equipe_du_meme_type_est_refusee_en_nommant_la_premiere(decor: Decor) -> None:
    premiere = decor.service.creer(decor.tournoi_id, "Les Archers", TypeEquipe.STANDARD, None)
    seconde = decor.service.creer(decor.tournoi_id, "Les Flèches", TypeEquipe.STANDARD, None)
    assert premiere.equipe.id is not None and seconde.equipe.id is not None
    guillaume = decor.archer("Guillaume")
    decor.service.ajouter_membre(decor.tournoi_id, premiere.equipe.id, guillaume)
    with pytest.raises(ArcherDejaEnEquipe, match="Les Archers"):
        decor.service.ajouter_membre(decor.tournoi_id, seconde.equipe.id, guillaume)


def test_une_standard_et_une_mixte_sont_permises(decor: Decor) -> None:
    standard = decor.service.creer(decor.tournoi_id, "Les Archers", TypeEquipe.STANDARD, None)
    mixte = decor.service.creer(decor.tournoi_id, "Le Duo", TypeEquipe.MIXTE, None)
    assert standard.equipe.id is not None and mixte.equipe.id is not None
    guillaume = decor.archer("Guillaume")
    decor.service.ajouter_membre(decor.tournoi_id, standard.equipe.id, guillaume)
    vue = decor.service.ajouter_membre(decor.tournoi_id, mixte.equipe.id, guillaume)
    assert vue.equipe.membres == (guillaume,)


def test_changer_le_type_vers_celui_d_une_autre_equipe_d_un_membre_est_refuse(
    decor: Decor,
) -> None:
    standard = decor.service.creer(decor.tournoi_id, "Les Archers", TypeEquipe.STANDARD, None)
    mixte = decor.service.creer(decor.tournoi_id, "Le Duo", TypeEquipe.MIXTE, None)
    assert standard.equipe.id is not None and mixte.equipe.id is not None
    guillaume = decor.archer("Guillaume")
    decor.service.ajouter_membre(decor.tournoi_id, standard.equipe.id, guillaume)
    decor.service.ajouter_membre(decor.tournoi_id, mixte.equipe.id, guillaume)
    with pytest.raises(ArcherDejaEnEquipe, match="Les Archers"):
        decor.service.modifier(
            decor.tournoi_id, mixte.equipe.id, "Le Duo", TypeEquipe.STANDARD, None
        )


# --- CA 4 / CA 5 : composition signalée, lue sur la catégorie de chaque membre ---


def test_une_equipe_non_conforme_s_enregistre_et_expose_ses_ecarts(decor: Decor) -> None:
    vue = decor.service.creer(decor.tournoi_id, "Les Archers", TypeEquipe.STANDARD, None)
    assert vue.equipe.id is not None
    assert vue.ecarts == (EcartComposition.EFFECTIF_INSUFFISANT,)
    assert not vue.conforme
    decor.service.ajouter_membre(decor.tournoi_id, vue.equipe.id, decor.archer("Guillaume"))
    apres = decor.service.ajouter_membre(
        decor.tournoi_id, vue.equipe.id, decor.archer("Lucie", decor.clf)
    )
    assert apres.ecarts == (
        EcartComposition.EFFECTIF_INSUFFISANT,
        EcartComposition.SEXES_DIFFERENTS,
    )


def test_une_equipe_complete_et_homogene_est_conforme(decor: Decor) -> None:
    vue = decor.service.creer(decor.tournoi_id, "Le Duo", TypeEquipe.MIXTE, None)
    assert vue.equipe.id is not None
    decor.service.ajouter_membre(decor.tournoi_id, vue.equipe.id, decor.archer("Guillaume"))
    apres = decor.service.ajouter_membre(
        decor.tournoi_id, vue.equipe.id, decor.archer("Lucie", decor.clf)
    )
    assert apres.conforme
    assert apres.ecarts == ()


def test_l_arme_est_lue_sur_la_categorie(decor: Decor) -> None:
    arc_a_poulies = decor.categories.ajouter(
        Categorie.creer(decor.tournoi_id, "Senior 1 F CO", arme="CO", sexe=SexeCategorie.FEMME)
    )
    assert arc_a_poulies.id is not None
    vue = decor.service.creer(decor.tournoi_id, "Le Duo", TypeEquipe.MIXTE, None)
    assert vue.equipe.id is not None
    decor.service.ajouter_membre(decor.tournoi_id, vue.equipe.id, decor.archer("Guillaume"))
    apres = decor.service.ajouter_membre(
        decor.tournoi_id, vue.equipe.id, decor.archer("Lucie", arc_a_poulies.id)
    )
    assert apres.ecarts == (EcartComposition.ARMES_DIFFERENTES,)


def test_changer_la_categorie_d_un_membre_change_la_conformite(decor: Decor) -> None:
    vue = decor.service.creer(decor.tournoi_id, "Le Duo", TypeEquipe.MIXTE, None)
    assert vue.equipe.id is not None
    decor.service.ajouter_membre(decor.tournoi_id, vue.equipe.id, decor.archer("Guillaume"))
    lucie = decor.archer("Lucie", decor.clf)
    decor.service.ajouter_membre(decor.tournoi_id, vue.equipe.id, lucie)
    archer = decor.archers.par_id(lucie)
    assert archer is not None
    decor.archers.enregistrer(archer.modifier(archer.nom, archer.prenom, decor.clh, None, None))
    (relue,) = decor.service.lister(decor.tournoi_id)
    assert relue.ecarts == (EcartComposition.MIXITE_MANQUANTE,)


def test_une_categorie_sans_sexe_rend_le_sexe_non_verifiable(decor: Decor) -> None:
    sans_sexe = decor.categories.ajouter(Categorie.creer(decor.tournoi_id, "Débutants", arme="CL"))
    assert sans_sexe.id is not None
    vue = decor.service.creer(decor.tournoi_id, "Le Duo", TypeEquipe.MIXTE, None)
    assert vue.equipe.id is not None
    decor.service.ajouter_membre(decor.tournoi_id, vue.equipe.id, decor.archer("Guillaume"))
    apres = decor.service.ajouter_membre(
        decor.tournoi_id, vue.equipe.id, decor.archer("Lucie", sans_sexe.id)
    )
    assert apres.ecarts == (EcartComposition.SEXE_NON_VERIFIABLE,)


# --- E13US004, arbitrage de revue (03/10/2026) : la composition se fige au premier tir ----------
# Le tableau d'équipes se recalcule à chaque lecture (ADR-0120 §2) : changer la population ou la
# composition d'un type déjà en jeu réécrirait l'ensemencement et masquerait les tirs faits.


def _equipe_en_jeu(decor: Decor) -> int:
    vue = decor.service.creer(decor.tournoi_id, "En jeu", TypeEquipe.STANDARD, None)
    assert vue.equipe.id is not None
    decor.service.ajouter_membre(decor.tournoi_id, vue.equipe.id, decor.archer("Guillaume"))
    decor.verrou.tires.add(TypeEquipe.STANDARD)
    return vue.equipe.id


def test_apres_le_premier_tir_on_ne_supprime_plus_une_equipe_du_type(decor: Decor) -> None:
    equipe_id = _equipe_en_jeu(decor)

    with pytest.raises(CompositionEquipeVerrouillee):
        decor.service.supprimer(decor.tournoi_id, equipe_id)


def test_apres_le_premier_tir_on_ne_change_plus_ses_membres(decor: Decor) -> None:
    equipe_id = _equipe_en_jeu(decor)
    equipe = decor.equipes.par_id(equipe_id)
    assert equipe is not None
    (membre,) = equipe.membres

    with pytest.raises(CompositionEquipeVerrouillee):
        decor.service.ajouter_membre(decor.tournoi_id, equipe_id, decor.archer("Walter"))
    with pytest.raises(CompositionEquipeVerrouillee):
        decor.service.retirer_membre(decor.tournoi_id, equipe_id, membre)


def test_creer_reste_libre_une_equipe_vide_n_entre_dans_aucun_tableau(decor: Decor) -> None:
    _equipe_en_jeu(decor)

    retardataire = decor.service.creer(decor.tournoi_id, "Retardataire", TypeEquipe.STANDARD, None)

    assert retardataire.equipe.membres == ()


def test_apres_le_premier_tir_type_et_effectif_sont_figes_mais_pas_le_nom(decor: Decor) -> None:
    equipe_id = _equipe_en_jeu(decor)

    with pytest.raises(CompositionEquipeVerrouillee):
        decor.service.modifier(decor.tournoi_id, equipe_id, "En jeu", TypeEquipe.MIXTE, None)
    with pytest.raises(CompositionEquipeVerrouillee):
        decor.service.modifier(decor.tournoi_id, equipe_id, "En jeu", TypeEquipe.STANDARD, 4)
    renommee = decor.service.modifier(
        decor.tournoi_id, equipe_id, "Nouveau nom", TypeEquipe.STANDARD, None
    )
    assert renommee.equipe.nom == "Nouveau nom"


def test_un_autre_type_reste_libre(decor: Decor) -> None:
    _equipe_en_jeu(decor)

    mixte = decor.service.creer(decor.tournoi_id, "Duo", TypeEquipe.MIXTE, None)
    assert mixte.equipe.id is not None
    decor.service.supprimer(decor.tournoi_id, mixte.equipe.id)


def test_passer_dans_un_type_en_jeu_est_refuse(decor: Decor) -> None:
    mixte = decor.service.creer(decor.tournoi_id, "Duo", TypeEquipe.MIXTE, None)
    assert mixte.equipe.id is not None
    decor.service.ajouter_membre(decor.tournoi_id, mixte.equipe.id, decor.archer("Arnold"))
    decor.verrou.tires.add(TypeEquipe.STANDARD)

    with pytest.raises(CompositionEquipeVerrouillee):
        decor.service.modifier(decor.tournoi_id, mixte.equipe.id, "Duo", TypeEquipe.STANDARD, None)


def test_le_premier_membre_d_une_equipe_vide_est_soumis_au_verrou(decor: Decor) -> None:
    # Créer est libre parce qu'une équipe vide n'entre nulle part ; c'est l'ajout du premier
    # membre qui doit être gardé, sur l'union des membres et du nouvel archer.
    _equipe_en_jeu(decor)
    retardataire = decor.service.creer(decor.tournoi_id, "Retardataire", TypeEquipe.STANDARD, None)
    assert retardataire.equipe.id is not None

    with pytest.raises(CompositionEquipeVerrouillee):
        decor.service.ajouter_membre(
            decor.tournoi_id, retardataire.equipe.id, decor.archer("Walter")
        )
