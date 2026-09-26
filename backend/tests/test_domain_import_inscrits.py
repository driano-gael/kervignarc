"""Import d'un fichier d'inscrits (E02US007) — tests dérivés du CA et des arbitrages du 26/09/2026.

Source : `stories/E02-inscriptions.md`, fiche E02US007 (trois CA + arbitrages 1 à 5 des Notes) et
`docs/referentiel-ffta.md` §2 pour la tranche d'âge.
"""

from __future__ import annotations

import datetime

import pytest

from domain.archer import Archer
from domain.categorie import Categorie, SexeCategorie, TrancheAge
from domain.club import Club
from domain.depart import Depart
from domain.import_inscrits import (
    Decision,
    FichierInscrits,
    InstantaneDuTournoi,
    LigneFichier,
    SourceImport,
    planifier_import,
    tranche_age,
)
from domain.inscription import Inscription

TOURNOI = 1
DATE_TOURNOI = datetime.date(2026, 11, 15)  # saison 2026-2027 : âge atteint en 2027


# --- Tranche d'âge (référentiel §2 : âge atteint dans l'année civile de fin de saison) -----------


@pytest.mark.parametrize(
    ("naissance", "attendue"),
    [
        (datetime.date(2017, 12, 31), TrancheAge.U11),  # 10 ans en 2027
        (datetime.date(2016, 1, 1), TrancheAge.U13),  # 11 ans
        (datetime.date(2015, 6, 1), TrancheAge.U13),  # 12 ans
        (datetime.date(2014, 6, 1), TrancheAge.U15),  # 13 ans
        (datetime.date(2012, 6, 1), TrancheAge.U18),  # 15 ans
        (datetime.date(2010, 6, 1), TrancheAge.U18),  # 17 ans
        (datetime.date(2009, 6, 1), TrancheAge.U21),  # 18 ans
        (datetime.date(2007, 6, 1), TrancheAge.U21),  # 20 ans
        (datetime.date(2006, 6, 1), TrancheAge.S1),  # 21 ans
        (datetime.date(1988, 6, 1), TrancheAge.S1),  # 39 ans
        (datetime.date(1987, 6, 1), TrancheAge.S2),  # 40 ans
        (datetime.date(1968, 6, 1), TrancheAge.S2),  # 59 ans
        (datetime.date(1967, 6, 1), TrancheAge.S3),  # 60 ans
    ],
)
def test_tranche_d_age_sur_l_annee_civile_de_fin_de_saison(
    naissance: datetime.date, attendue: TrancheAge
) -> None:
    assert tranche_age(naissance, DATE_TOURNOI) == attendue


def test_la_saison_bascule_au_premier_septembre() -> None:
    naissance = datetime.date(2006, 6, 1)
    # Août 2026 : saison 2025-2026, âge atteint en 2026 = 20 ans.
    assert tranche_age(naissance, datetime.date(2026, 8, 31)) == TrancheAge.U21
    # Septembre 2026 : saison 2026-2027, âge atteint en 2027 = 21 ans.
    assert tranche_age(naissance, datetime.date(2026, 9, 1)) == TrancheAge.S1


# --- Fabriques ----------------------------------------------------------------------------------

SENIOR_FEMME = datetime.date(1990, 5, 1)
SENIOR_HOMME = datetime.date(1985, 3, 3)


def _categorie(
    cid: int,
    libelle: str,
    sexe: SexeCategorie | None = None,
    ages: tuple[TrancheAge, ...] = (),
    arme: str | None = None,
) -> Categorie:
    return Categorie(tournoi_id=TOURNOI, libelle=libelle, arme=arme, ages=ages, sexe=sexe, id=cid)


def _ianseo(
    numero: int,
    nom: str = "Dupont",
    prenom: str = "Jeanne",
    licence: str | None = "1234567A",
    depart: int | None = 1,
    sexe: SexeCategorie | None = SexeCategorie.FEMME,
    naissance: datetime.date | None = SENIOR_FEMME,
    club: str | None = "Kervignac",
    arme: str | None = None,
) -> LigneFichier:
    return LigneFichier(
        numero=numero,
        licence=licence,
        depart_numero=depart,
        nom=nom,
        prenom=prenom,
        sexe=sexe,
        date_naissance=naissance,
        club=club,
        arme=arme,
    )


def _fichier(*lignes: LigneFichier, source: SourceImport = SourceImport.IANSEO) -> FichierInscrits:
    return FichierInscrits(source=source, lignes=tuple(lignes))


def _etat(
    categories: tuple[Categorie, ...] = (
        _categorie(10, "Femmes", SexeCategorie.FEMME),
        _categorie(11, "Hommes", SexeCategorie.HOMME),
    ),
    departs: tuple[Depart, ...] = (
        Depart(tournoi_id=TOURNOI, numero=1, tarif_centimes=800, horaire="09:00", id=100),
        Depart(tournoi_id=TOURNOI, numero=2, tarif_centimes=800, horaire="14:00", id=200),
    ),
    archers: tuple[Archer, ...] = (),
    clubs: tuple[Club, ...] = (Club(nom="Kervignac", id=7),),
    inscriptions: tuple[Inscription, ...] = (),
) -> InstantaneDuTournoi:
    return InstantaneDuTournoi(
        date_tournoi=DATE_TOURNOI,
        categories=categories,
        departs=departs,
        archers=archers,
        clubs=clubs,
        inscriptions=inscriptions,
    )


# --- CA « parsing & mapping » : création des archers / clubs, sur un départ existant -------------


def test_une_ligne_ianseo_valide_cree_la_fiche_et_l_inscrit_sur_son_depart() -> None:
    plan = planifier_import(_fichier(_ianseo(1)), _etat())

    (ligne,) = plan.lignes
    assert ligne.decision is Decision.CREER
    assert ligne.categorie_id == 10
    assert ligne.club_id == 7
    assert ligne.club_a_creer is None
    assert ligne.depart_id == 100
    assert ligne.motif is None


def test_le_club_se_retrouve_casse_et_accents_replies() -> None:
    etat = _etat(clubs=(Club(nom="Saint-Agathon É", id=8),))
    plan = planifier_import(_fichier(_ianseo(1, club="SAINT-AGATHON E")), etat)

    assert plan.lignes[0].club_id == 8


def test_un_club_absent_est_a_creer() -> None:
    plan = planifier_import(_fichier(_ianseo(1, club="Montoir de Bretagne")), _etat())

    (ligne,) = plan.lignes
    assert ligne.decision is Decision.CREER
    assert ligne.club_id is None
    assert ligne.club_a_creer == "Montoir de Bretagne"


def test_le_depart_doit_exister() -> None:
    plan = planifier_import(_fichier(_ianseo(1, depart=3)), _etat())

    (ligne,) = plan.lignes
    assert ligne.decision is Decision.REJETEE
    assert ligne.motif is not None and "départ n° 3" in ligne.motif


def test_une_ligne_sans_depart_est_rejetee() -> None:
    plan = planifier_import(_fichier(_ianseo(1, depart=None)), _etat())

    assert plan.lignes[0].decision is Decision.REJETEE


def test_une_ligne_illisible_est_rejetee_avec_le_motif_de_lecture() -> None:
    illisible = LigneFichier(numero=4, licence=None, depart_numero=None, anomalie="date illisible")
    plan = planifier_import(_fichier(illisible), _etat())

    (ligne,) = plan.lignes
    assert ligne.decision is Decision.REJETEE
    assert ligne.motif is not None and "date illisible" in ligne.motif


def test_nom_ou_prenom_vide_rejette_la_ligne() -> None:
    plan = planifier_import(_fichier(_ianseo(1, nom="  "), _ianseo(2, prenom="")), _etat())

    assert [ligne.decision for ligne in plan.lignes] == [Decision.REJETEE, Decision.REJETEE]


# --- Arbitrage 2 : catégorie déduite, sinon rejet -----------------------------------------------


def test_categorie_deduite_du_sexe_de_l_age_et_de_l_arme() -> None:
    categories = (
        _categorie(20, "Femmes classique S1", SexeCategorie.FEMME, (TrancheAge.S1,), "Classique"),
        _categorie(21, "Femmes poulies S1", SexeCategorie.FEMME, (TrancheAge.S1,), "Poulies"),
        _categorie(22, "Femmes classique S2", SexeCategorie.FEMME, (TrancheAge.S2,), "Classique"),
    )
    ligne = _ianseo(1, naissance=SENIOR_FEMME, arme="CLASSIQUE")

    plan = planifier_import(_fichier(ligne), _etat(categories=categories))

    assert plan.lignes[0].categorie_id == 20


def test_une_categorie_sans_restriction_accepte_tout_le_monde() -> None:
    plan = planifier_import(
        _fichier(_ianseo(1, arme="TA")), _etat(categories=(_categorie(30, "Scratch"),))
    )

    assert plan.lignes[0].categorie_id == 30


def test_une_categorie_mixte_accepte_les_deux_sexes() -> None:
    categories = (_categorie(31, "Mixte", SexeCategorie.MIXTE),)
    plan = planifier_import(
        _fichier(_ianseo(1), _ianseo(2, licence="7654321B", sexe=SexeCategorie.HOMME)),
        _etat(categories=categories),
    )

    assert [ligne.categorie_id for ligne in plan.lignes] == [31, 31]


def test_aucune_categorie_candidate_rejette_la_ligne() -> None:
    categories = (_categorie(11, "Hommes", SexeCategorie.HOMME),)
    plan = planifier_import(_fichier(_ianseo(1)), _etat(categories=categories))

    (ligne,) = plan.lignes
    assert ligne.decision is Decision.REJETEE
    assert ligne.motif is not None and "catégorie" in ligne.motif


def test_plusieurs_categories_candidates_rejette_la_ligne_en_les_nommant() -> None:
    categories = (_categorie(40, "Femmes A"), _categorie(41, "Femmes B"))
    plan = planifier_import(_fichier(_ianseo(1)), _etat(categories=categories))

    (ligne,) = plan.lignes
    assert ligne.decision is Decision.REJETEE
    assert ligne.motif is not None
    assert "Femmes A" in ligne.motif and "Femmes B" in ligne.motif


def test_sans_date_de_naissance_une_categorie_par_age_n_est_pas_deductible() -> None:
    categories = (_categorie(50, "Seniors", ages=(TrancheAge.S1,)),)
    plan = planifier_import(_fichier(_ianseo(1, naissance=None)), _etat(categories=categories))

    assert plan.lignes[0].decision is Decision.REJETEE


def test_sans_sexe_une_categorie_sexuee_n_est_pas_deductible() -> None:
    plan = planifier_import(_fichier(_ianseo(1, sexe=None)), _etat())

    assert plan.lignes[0].decision is Decision.REJETEE


# --- Arbitrage 3 : une fiche par licence dans le tournoi ----------------------------------------


def _archer_existant(
    aid: int = 500, licence: str | None = "1234567A", nom: str = "Dupont", club_id: int | None = 7
) -> Archer:
    return Archer(
        nom=nom,
        prenom="Jeanne",
        tournoi_id=TOURNOI,
        categorie_id=10,
        club_id=club_id,
        licence=licence,
        id=aid,
    )


def test_une_licence_connue_du_tournoi_inscrit_la_fiche_existante_sur_son_depart() -> None:
    etat = _etat(
        archers=(_archer_existant(),),
        inscriptions=(Inscription(archer_id=500, depart_id=100, id=1),),
    )
    plan = planifier_import(_fichier(_ianseo(1, depart=2)), etat)

    (ligne,) = plan.lignes
    assert ligne.decision is Decision.INSCRIRE
    assert ligne.archer_id == 500
    assert ligne.depart_id == 200


def test_la_licence_fait_foi_meme_si_le_nom_differe() -> None:
    etat = _etat(archers=(_archer_existant(nom="Dupond"),))
    plan = planifier_import(_fichier(_ianseo(1, nom="Dupont")), etat)

    assert plan.lignes[0].decision is Decision.INSCRIRE


def test_une_licence_deja_inscrite_sur_ce_depart_est_rejetee() -> None:
    etat = _etat(
        archers=(_archer_existant(),),
        inscriptions=(Inscription(archer_id=500, depart_id=100, id=1),),
    )
    plan = planifier_import(_fichier(_ianseo(1, depart=1)), etat)

    (ligne,) = plan.lignes
    assert ligne.decision is Decision.REJETEE
    assert ligne.motif is not None and "départ n° 1" in ligne.motif


def test_la_licence_se_compare_normalisee() -> None:
    etat = _etat(archers=(_archer_existant(licence="1234567A"),))
    plan = planifier_import(_fichier(_ianseo(1, licence=" 1234567a ")), etat)

    assert plan.lignes[0].decision is Decision.INSCRIRE


def test_meme_licence_deux_fois_dans_le_fichier_sur_deux_departs_une_fiche_deux_inscriptions() -> (
    None
):
    plan = planifier_import(_fichier(_ianseo(1, depart=1), _ianseo(2, depart=2)), _etat())

    premiere, seconde = plan.lignes
    assert premiere.decision is Decision.CREER
    assert seconde.decision is Decision.INSCRIRE
    assert seconde.archer_id is None
    assert seconde.fiche_de_la_ligne == 1
    assert seconde.depart_id == 200


def test_meme_licence_deux_fois_dans_le_fichier_sur_le_meme_depart_rejette_la_seconde() -> None:
    plan = planifier_import(_fichier(_ianseo(1), _ianseo(2)), _etat())

    assert [ligne.decision for ligne in plan.lignes] == [Decision.CREER, Decision.REJETEE]


# --- CA « rapport » + ADR-0015 : les homonymes sont collectés, pas tranchés ---------------------


def test_un_homonyme_sans_licence_commune_est_signale_et_non_importe() -> None:
    etat = _etat(archers=(_archer_existant(licence=None),))
    plan = planifier_import(_fichier(_ianseo(3)), etat)

    (ligne,) = plan.lignes
    assert ligne.decision is Decision.HOMONYME
    assert ligne.homonyme_de is not None and "Jeanne Dupont" in ligne.homonyme_de
    assert plan.importables == ()


def test_un_homonyme_coche_par_l_admin_est_importe() -> None:
    etat = _etat(archers=(_archer_existant(licence=None),))
    plan = planifier_import(_fichier(_ianseo(3)), etat, homonymes_acceptes=frozenset({3}))

    (ligne,) = plan.lignes
    assert ligne.decision is Decision.CREER
    assert ligne.homonyme_de is not None  # le rapport garde la trace de la confirmation


def test_deux_licences_differentes_ne_sont_jamais_des_homonymes() -> None:
    etat = _etat(archers=(_archer_existant(licence="7777777Z"),))
    plan = planifier_import(_fichier(_ianseo(1, licence="1234567A")), etat)

    assert plan.lignes[0].decision is Decision.CREER


def test_deux_lignes_homonymes_sans_licence_dans_le_fichier() -> None:
    plan = planifier_import(_fichier(_ianseo(1, licence=None), _ianseo(2, licence=None)), _etat())

    assert [ligne.decision for ligne in plan.lignes] == [Decision.CREER, Decision.HOMONYME]


# --- Vigilance quota (E02US006) : re-contrôlé ligne à ligne -------------------------------------


def test_le_quota_du_depart_est_tenu_en_comptant_l_existant_et_le_fichier() -> None:
    departs = (
        Depart(tournoi_id=TOURNOI, numero=1, tarif_centimes=0, horaire="09:00", quota=2, id=100),
    )
    etat = _etat(
        departs=departs,
        archers=(_archer_existant(licence="9999999X"),),
        inscriptions=(Inscription(archer_id=500, depart_id=100, id=1),),
    )
    plan = planifier_import(
        _fichier(_ianseo(1, licence="1111111A"), _ianseo(2, licence="2222222B", prenom="Anne")),
        etat,
    )

    assert [ligne.decision for ligne in plan.lignes] == [Decision.CREER, Decision.REJETEE]
    assert plan.lignes[1].motif is not None and "complet" in plan.lignes[1].motif


def test_une_ligne_rejetee_ne_consomme_pas_de_place() -> None:
    departs = (
        Depart(tournoi_id=TOURNOI, numero=1, tarif_centimes=0, horaire="09:00", quota=1, id=100),
    )
    plan = planifier_import(
        _fichier(_ianseo(1, nom=""), _ianseo(2, licence="2222222B")), _etat(departs=departs)
    )

    assert [ligne.decision for ligne in plan.lignes] == [Decision.REJETEE, Decision.CREER]


# --- Arbitrage 1 : Résult'Arc ne crée personne ---------------------------------------------------


def _resultarc(numero: int, licence: str | None, depart: int | None = 2) -> LigneFichier:
    return LigneFichier(numero=numero, licence=licence, depart_numero=depart)


def test_resultarc_inscrit_la_fiche_designee_par_la_licence() -> None:
    plan = planifier_import(
        _fichier(_resultarc(2, "1234567A"), source=SourceImport.RESULTARC),
        _etat(archers=(_archer_existant(),)),
    )

    (ligne,) = plan.lignes
    assert ligne.decision is Decision.INSCRIRE
    assert ligne.archer_id == 500 and ligne.depart_id == 200


def test_resultarc_rejette_une_licence_inconnue_du_tournoi() -> None:
    plan = planifier_import(
        _fichier(_resultarc(2, "1234567A"), source=SourceImport.RESULTARC), _etat()
    )

    (ligne,) = plan.lignes
    assert ligne.decision is Decision.REJETEE
    assert ligne.motif is not None and "Ianseo" in ligne.motif


def test_resultarc_rejette_une_ligne_sans_licence() -> None:
    plan = planifier_import(_fichier(_resultarc(2, None), source=SourceImport.RESULTARC), _etat())

    assert plan.lignes[0].decision is Decision.REJETEE


# --- Le rapport ------------------------------------------------------------------------------


def test_le_rapport_ventile_importables_rejetees_et_homonymes() -> None:
    etat = _etat(archers=(_archer_existant(aid=501, licence=None, nom="Martin"),))
    plan = planifier_import(
        _fichier(
            _ianseo(1),
            _ianseo(2, licence="2222222B", depart=9),
            _ianseo(3, licence=None, nom="Martin"),
        ),
        etat,
    )

    assert [ligne.ligne.numero for ligne in plan.importables] == [1]
    assert [ligne.ligne.numero for ligne in plan.rejetees] == [2]
    assert [ligne.ligne.numero for ligne in plan.homonymes] == [3]
