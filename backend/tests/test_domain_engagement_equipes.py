"""Tests de l'engagement des équipes dans une phase (E13US004, CA 2 et 3) — sans infrastructure.

Écrits **depuis le CA** (règle 9), avant le code. L'engagement n'est pas un geste mais une
dérivation (ADR-0120 §2) : ces tests décrivent qui entre, qui est écarté et pourquoi, et dans quel
ordre les engagées entrent au tableau.
"""

from __future__ import annotations

from domain.categorie import SexeCategorie
from domain.classement import LigneClassement, StatutClassement
from domain.engagement_equipes import engager_les_equipes
from domain.equipe import EcartComposition, Equipe, ProfilMembre, TypeEquipe

H = SexeCategorie.HOMME
F = SexeCategorie.FEMME
CLASSIQUE_H = ProfilMembre(arme="Classique", sexe=H)
CLASSIQUE_F = ProfilMembre(arme="Classique", sexe=F)


def _equipe(
    id: int, nom: str, membres: tuple[int, ...], type: TypeEquipe = TypeEquipe.STANDARD
) -> Equipe:
    return Equipe(
        tournoi_id=1,
        nom=nom,
        type=type,
        effectif_attendu=len(membres) if membres else 3,
        membres=membres,
        id=id,
    )


def _ligne(
    archer_id: int,
    total: int,
    nb_dix: int = 0,
    nb_neuf: int = 0,
    statut: StatutClassement = StatutClassement.EN_LICE,
) -> LigneClassement:
    return LigneClassement(
        rang_scratch=1,
        rang_categorie=1,
        archer_id=archer_id,
        nom=f"Nom{archer_id}",
        prenom=f"Prenom{archer_id}",
        categorie_id=1,
        categorie_libelle="CHSH",
        cible=None,
        club_id=None,
        total=total,
        nb_dix=nb_dix,
        nb_neuf=nb_neuf,
        statut=statut,
    )


def _lignes(*lignes: LigneClassement) -> dict[int, LigneClassement]:
    return {ligne.archer_id: ligne for ligne in lignes}


def _profils(*archers: int, profil: ProfilMembre = CLASSIQUE_H) -> dict[int, ProfilMembre]:
    return {archer: profil for archer in archers}


# --- CA 3 : le rang d'entrée est la somme des qualifications ---------------------------------


def test_les_equipes_sont_rangees_par_la_somme_des_totaux_de_leurs_membres() -> None:
    faible = _equipe(1, "Faible", (1, 2, 3))
    forte = _equipe(2, "Forte", (4, 5, 6))
    lignes = _lignes(
        _ligne(1, 500), _ligne(2, 500), _ligne(3, 500),
        _ligne(4, 550), _ligne(5, 540), _ligne(6, 530),
    )  # fmt: skip

    engagement = engager_les_equipes(
        TypeEquipe.STANDARD, [faible, forte], _profils(1, 2, 3, 4, 5, 6), lignes
    )

    assert [(e.equipe.nom, e.rang, e.total) for e in engagement.engagees] == [
        ("Forte", 1, 1620),
        ("Faible", 2, 1500),
    ]
    assert engagement.ecartees == ()


def test_a_total_egal_la_somme_des_dix_puis_des_neuf_departage() -> None:
    a = _equipe(1, "A", (1, 2, 3))
    b = _equipe(2, "B", (4, 5, 6))
    c = _equipe(3, "C", (7, 8, 9))
    lignes = _lignes(
        _ligne(1, 500, nb_dix=5, nb_neuf=9), _ligne(2, 500), _ligne(3, 500),
        _ligne(4, 500, nb_dix=5, nb_neuf=10), _ligne(5, 500), _ligne(6, 500),
        _ligne(7, 500, nb_dix=6), _ligne(8, 500), _ligne(9, 500),
    )  # fmt: skip

    engagement = engager_les_equipes(
        TypeEquipe.STANDARD, [a, b, c], _profils(*range(1, 10)), lignes
    )

    assert [e.equipe.nom for e in engagement.engagees] == ["C", "B", "A"]
    assert [(e.nb_dix, e.nb_neuf) for e in engagement.engagees] == [(6, 0), (5, 10), (5, 9)]
    assert [e.rang for e in engagement.engagees] == [1, 2, 3]


def test_a_egalite_complete_l_ordre_alphabetique_du_nom_tranche() -> None:
    # DETTE-121 : un départage au tir du rang d'entrée n'existe pas encore.
    zulu = _equipe(1, "Zulu", (1, 2, 3))
    alpha = _equipe(2, "alpha", (4, 5, 6))
    lignes = _lignes(*(_ligne(archer, 500) for archer in range(1, 7)))

    engagement = engager_les_equipes(
        TypeEquipe.STANDARD, [zulu, alpha], _profils(*range(1, 7)), lignes
    )

    assert [(e.equipe.nom, e.rang) for e in engagement.engagees] == [("alpha", 1), ("Zulu", 2)]


# --- CA 2 : qui est engagé, qui est écarté et pourquoi ---------------------------------------


def test_seules_les_equipes_du_type_de_la_phase_sont_considerees() -> None:
    standard = _equipe(1, "Standard", (1, 2, 3))
    mixte = _equipe(2, "Mixte", (4, 5), type=TypeEquipe.MIXTE)
    lignes = _lignes(*(_ligne(archer, 500) for archer in range(1, 6)))
    profils = {**_profils(1, 2, 3), 4: CLASSIQUE_H, 5: CLASSIQUE_F}

    engagement = engager_les_equipes(TypeEquipe.MIXTE, [standard, mixte], profils, lignes)

    assert [e.equipe.nom for e in engagement.engagees] == ["Mixte"]
    assert engagement.ecartees == ()


def test_une_equipe_non_conforme_est_ecartee_en_nommant_ses_ecarts() -> None:
    incomplete = Equipe(
        tournoi_id=1, nom="Incomplète", type=TypeEquipe.STANDARD, effectif_attendu=3,
        membres=(1, 2), id=1,
    )  # fmt: skip
    conforme = _equipe(2, "Conforme", (3, 4, 5))
    lignes = _lignes(*(_ligne(archer, 500) for archer in range(1, 6)))

    engagement = engager_les_equipes(
        TypeEquipe.STANDARD, [incomplete, conforme], _profils(*range(1, 6)), lignes
    )

    assert [e.equipe.nom for e in engagement.engagees] == ["Conforme"]
    (ecartee,) = engagement.ecartees
    assert ecartee.equipe.nom == "Incomplète"
    assert ecartee.ecarts == (EcartComposition.EFFECTIF_INSUFFISANT,)
    assert ecartee.membres_hors_course == ()


def test_une_equipe_aux_sexes_differents_est_ecartee() -> None:
    melangee = _equipe(1, "Mélangée", (1, 2, 3))
    profils = {1: CLASSIQUE_H, 2: CLASSIQUE_H, 3: CLASSIQUE_F}
    lignes = _lignes(*(_ligne(archer, 500) for archer in range(1, 4)))

    engagement = engager_les_equipes(TypeEquipe.STANDARD, [melangee], profils, lignes)

    assert engagement.engagees == ()
    assert engagement.ecartees[0].ecarts == (EcartComposition.SEXES_DIFFERENTS,)


def test_un_membre_absent_du_classement_du_depart_ecarte_l_equipe() -> None:
    # Le membre 3 tire un autre départ : il n'a pas de ligne dans ce classement.
    equipe = _equipe(1, "Dispersée", (1, 2, 3))
    lignes = _lignes(_ligne(1, 500), _ligne(2, 500))

    engagement = engager_les_equipes(TypeEquipe.STANDARD, [equipe], _profils(1, 2, 3), lignes)

    assert engagement.engagees == ()
    (ecartee,) = engagement.ecartees
    assert ecartee.ecarts == ()
    assert ecartee.membres_hors_course == (3,)


def test_un_membre_forfait_ou_disqualifie_ecarte_l_equipe() -> None:
    equipe = _equipe(1, "Diminuée", (1, 2, 3))
    lignes = _lignes(
        _ligne(1, 500),
        _ligne(2, 500, statut=StatutClassement.ABANDON),
        _ligne(3, 500, statut=StatutClassement.DISQUALIFIE),
    )

    engagement = engager_les_equipes(TypeEquipe.STANDARD, [equipe], _profils(1, 2, 3), lignes)

    assert engagement.engagees == ()
    assert engagement.ecartees[0].membres_hors_course == (2, 3)


def test_ecarts_et_membres_hors_course_se_cumulent() -> None:
    equipe = _equipe(1, "Cumul", (1, 2, 3))
    profils = {1: CLASSIQUE_H, 2: CLASSIQUE_H, 3: ProfilMembre(arme="Poulies", sexe=H)}
    lignes = _lignes(_ligne(1, 500), _ligne(2, 500))

    engagement = engager_les_equipes(TypeEquipe.STANDARD, [equipe], profils, lignes)

    (ecartee,) = engagement.ecartees
    assert ecartee.ecarts == (EcartComposition.ARMES_DIFFERENTES,)
    assert ecartee.membres_hors_course == (3,)


def test_un_membre_sans_profil_connu_rend_la_composition_non_verifiable() -> None:
    # On ne devine dans aucun sens (E13US002) : sans catégorie résolue, l'équipe n'entre pas.
    equipe = _equipe(1, "Inconnue", (1, 2, 3))
    lignes = _lignes(*(_ligne(archer, 500) for archer in range(1, 4)))

    engagement = engager_les_equipes(TypeEquipe.STANDARD, [equipe], _profils(1, 2), lignes)

    assert engagement.engagees == ()
    assert EcartComposition.ARME_NON_VERIFIABLE in engagement.ecartees[0].ecarts


def test_les_equipes_ecartees_sont_listees_par_nom() -> None:
    lignes = _lignes(*(_ligne(archer, 500) for archer in range(1, 5)))
    b_incomplete = Equipe(1, "B", TypeEquipe.STANDARD, 3, (1, 2), id=1)
    a_incomplete = Equipe(1, "a", TypeEquipe.STANDARD, 3, (3, 4), id=2)

    engagement = engager_les_equipes(
        TypeEquipe.STANDARD, [b_incomplete, a_incomplete], _profils(1, 2, 3, 4), lignes
    )

    assert [e.equipe.nom for e in engagement.ecartees] == ["a", "B"]


def test_aucune_equipe_rend_un_engagement_vide() -> None:
    engagement = engager_les_equipes(TypeEquipe.STANDARD, [], {}, {})

    assert engagement.engagees == ()
    assert engagement.ecartees == ()
