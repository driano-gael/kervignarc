"""Tests du contenu imprimable du classement de qualification (E09US005).

Écrits **depuis le CA** de `stories/E09-exports.md`, avant l'implémentation (règle 9) :

- « une page par catégorie ayant au moins un archer engagé, dans l'ordre des catégories du
  tournoi » — `blocs_par_categorie` ;
- « provisoire tant qu'un archer **en lice et placé** n'a pas validé toutes les volées du barème
  (ou que le barème n'est pas réglé), **ou** qu'une égalité attend son barrage ; un forfait ou un
  inscrit non placé ne retient pas le départ » — `qualification_provisoire` (CA amendé en revue).
"""

from __future__ import annotations

from domain.barrage import EgaliteADepartager
from domain.blason import ZoneScore
from domain.categorie import Categorie, CategorieId
from domain.classement import Classement, LigneClassement, StatutClassement
from domain.classement_imprime import blocs_par_categorie, qualification_provisoire
from domain.participant import Participant
from domain.serie import Serie, Volee

_SENIOR = CategorieId(1)
_CADET = CategorieId(2)
_VETERAN = CategorieId(3)

_CATEGORIES = (
    Categorie(tournoi_id=1, libelle="Senior Homme", id=_SENIOR),
    Categorie(tournoi_id=1, libelle="Cadet", id=_CADET),
    Categorie(tournoi_id=1, libelle="Vétéran", id=_VETERAN),
)


def _ligne(
    archer_id: int,
    categorie_id: CategorieId,
    rang: int | None,
    statut: StatutClassement = StatutClassement.EN_LICE,
) -> LigneClassement:
    libelle = next(c.libelle for c in _CATEGORIES if c.id == categorie_id)
    return LigneClassement(
        rang_scratch=rang,
        rang_categorie=rang,
        archer_id=archer_id,
        nom=f"NOM{archer_id}",
        prenom="Jean",
        categorie_id=categorie_id,
        categorie_libelle=libelle,
        cible=None,
        club_id=None,
        total=0,
        nb_dix=0,
        nb_neuf=0,
        statut=statut,
    )


def _serie(archer_id: int, volees_validees: int, volees_saisies: int = 0) -> Serie:
    """`volees_validees` validées, puis `volees_saisies` **saisies mais non validées**."""
    return Serie(
        tournoi_id=1,
        archer_id=archer_id,
        phase_id=1,
        volees=tuple(
            Volee(
                numero=n,
                valeurs=(ZoneScore.DIX,),
                validee_par="Scoreur" if n <= volees_validees else None,
            )
            for n in range(1, volees_validees + volees_saisies + 1)
        ),
    )


_TOUS = frozenset({1, 2, 3})


# --- CA « une page par catégorie » -----------------------------------------------------------


def test_un_bloc_par_categorie_engagee_dans_l_ordre_des_categories_du_tournoi() -> None:
    # Le classement est scratch : un cadet en tête, puis un senior. L'ordre des blocs n'en dépend
    # pas — c'est celui des catégories du tournoi (Senior, puis Cadet).
    classement = Classement(
        lignes=(_ligne(1, _CADET, 1), _ligne(2, _SENIOR, 2), _ligne(3, _CADET, 3))
    )

    blocs = blocs_par_categorie(classement, _CATEGORIES)

    assert [bloc.libelle for bloc in blocs] == ["Senior Homme", "Cadet"]


def test_une_categorie_sans_archer_engage_n_a_pas_de_page() -> None:
    classement = Classement(lignes=(_ligne(1, _SENIOR, 1),))

    blocs = blocs_par_categorie(classement, _CATEGORIES)

    assert [bloc.libelle for bloc in blocs] == ["Senior Homme"]


def test_un_bloc_garde_l_ordre_du_classement_et_seulement_ses_archers() -> None:
    disqualifie = _ligne(5, _CADET, None, StatutClassement.DISQUALIFIE)
    classement = Classement(
        lignes=(
            _ligne(1, _CADET, 1),
            _ligne(2, _SENIOR, 2),
            _ligne(3, _CADET, 3),
            disqualifie,
        )
    )

    (_, cadets) = blocs_par_categorie(classement, _CATEGORIES)

    assert [ligne.archer_id for ligne in cadets.lignes] == [1, 3, 5]


def test_une_ligne_de_categorie_inconnue_n_est_pas_perdue() -> None:
    classement = Classement(lignes=(_ligne(1, _VETERAN, 1), _ligne(2, _SENIOR, 2)))

    blocs = blocs_par_categorie(classement, _CATEGORIES[:2])

    assert [bloc.libelle for bloc in blocs] == ["Senior Homme", "Vétéran"]


def test_sans_archer_aucun_bloc() -> None:
    assert blocs_par_categorie(Classement(lignes=()), _CATEGORIES) == ()


# --- CA « provisoire » -----------------------------------------------------------------------


def test_toutes_les_series_en_lice_completes_le_classement_est_definitif() -> None:
    classement = Classement(lignes=(_ligne(1, _SENIOR, 1), _ligne(2, _SENIOR, 2)))

    assert not qualification_provisoire(
        classement, [_serie(1, 2), _serie(2, 2)], nb_volees=2, places=_TOUS
    )


def test_une_volee_manquante_rend_le_classement_provisoire() -> None:
    classement = Classement(lignes=(_ligne(1, _SENIOR, 1), _ligne(2, _SENIOR, 2)))

    assert qualification_provisoire(
        classement, [_serie(1, 2), _serie(2, 1)], nb_volees=2, places=_TOUS
    )


def test_une_volee_saisie_mais_non_validee_rend_le_classement_provisoire() -> None:
    # Le CA dit « validé » : une volée présente mais sans validation ne compte pas (axe B).
    classement = Classement(lignes=(_ligne(1, _SENIOR, 1),))

    assert qualification_provisoire(
        classement, [_serie(1, 1, volees_saisies=1)], nb_volees=2, places=_TOUS
    )


def test_un_archer_en_lice_sans_feuille_rend_le_classement_provisoire() -> None:
    classement = Classement(lignes=(_ligne(1, _SENIOR, 1), _ligne(2, _SENIOR, 2)))

    assert qualification_provisoire(classement, [_serie(1, 2)], nb_volees=2, places=_TOUS)


def test_un_archer_forfait_ne_retient_pas_le_classement_en_provisoire() -> None:
    classement = Classement(
        lignes=(
            _ligne(1, _SENIOR, 1),
            _ligne(2, _SENIOR, 2, StatutClassement.ABANDON),
            _ligne(3, _SENIOR, None, StatutClassement.DISQUALIFIE),
        )
    )

    assert not qualification_provisoire(
        classement, [_serie(1, 2), _serie(2, 1)], nb_volees=2, places=_TOUS
    )


def test_un_inscrit_non_place_ne_retient_pas_le_classement_en_provisoire() -> None:
    classement = Classement(lignes=(_ligne(1, _SENIOR, 1), _ligne(2, _SENIOR, 2)))

    assert not qualification_provisoire(
        classement, [_serie(1, 2)], nb_volees=2, places=frozenset({1})
    )


def test_un_barrage_en_attente_rend_le_classement_provisoire() -> None:
    classement = Classement(
        lignes=(_ligne(1, _SENIOR, 1), _ligne(2, _SENIOR, 1)),
        egalites_a_departager=(
            EgaliteADepartager(
                rang=1, participants=(Participant.individuel(1), Participant.individuel(2))
            ),
        ),
    )

    assert qualification_provisoire(
        classement, [_serie(1, 2), _serie(2, 2)], nb_volees=2, places=_TOUS
    )


def test_un_creneau_sans_archer_n_attend_rien() -> None:
    assert not qualification_provisoire(Classement(lignes=()), [], nb_volees=2, places=_TOUS)


def test_sans_bareme_regle_le_classement_reste_provisoire() -> None:
    classement = Classement(lignes=(_ligne(1, _SENIOR, 1),))

    assert qualification_provisoire(classement, [_serie(1, 2)], nb_volees=0, places=_TOUS)
