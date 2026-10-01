"""Tests de l'adapter tableur du classement de qualification (E09US005).

Tests **après** l'implémentation (règle 9 : adapters).
"""

from __future__ import annotations

from io import BytesIO

from openpyxl import load_workbook

from domain.classement import LigneClassement, StatutClassement
from domain.classement_imprime import (
    BlocCategorie,
    ClassementQualificationImprime,
    SectionClassementQualification,
)
from infrastructure.tableur import (
    GenerateurClassementQualificationTableur,
    rendre_csv,
    rendre_xlsx,
)


def _ligne(
    archer_id: int,
    rang_categorie: int | None,
    rang_scratch: int | None,
    statut: StatutClassement = StatutClassement.EN_LICE,
) -> LigneClassement:
    return LigneClassement(
        rang_scratch=rang_scratch,
        rang_categorie=rang_categorie,
        archer_id=archer_id,
        nom=f"NOM{archer_id}",
        prenom="Jean",
        categorie_id=1,
        categorie_libelle="Senior Homme",
        cible=None,
        club_id=7,
        total=550,
        nb_dix=20,
        nb_neuf=15,
        statut=statut,
    )


def _document(*sections: SectionClassementQualification) -> ClassementQualificationImprime:
    return ClassementQualificationImprime(
        tournoi="Salle 18m", sections=sections, clubs={7: "Compagnie de Kervignarc"}
    )


# Rangs de catégorie et général **différents** : des fixtures à rangs égaux laissaient passer
# l'inversion des deux colonnes (revue, axe B).
_SENIORS = BlocCategorie(
    "Senior Homme", (_ligne(1, 1, 4), _ligne(2, None, None, StatutClassement.DISQUALIFIE))
)
_CADETS = BlocCategorie("Cadet", (_ligne(3, 1, 2),))


def test_le_tableur_rend_a_plat_avec_depart_categorie_et_etat() -> None:
    matin = SectionClassementQualification("Matin", False, (_SENIORS,))
    apres_midi = SectionClassementQualification("Après-midi", True, (_CADETS,))

    octets = GenerateurClassementQualificationTableur(rendre_csv).classement_qualification(
        _document(matin, apres_midi)
    )

    lignes = octets.decode("utf-8-sig").splitlines()
    assert lignes[1:] == [
        "Matin;Senior Homme;1;4;NOM1;Jean;Compagnie de Kervignarc;550;20;15;;Définitif",
        "Matin;Senior Homme;;;NOM2;Jean;Compagnie de Kervignarc;550;20;15;Disqualifié;Définitif",
        "Après-midi;Cadet;1;2;NOM3;Jean;Compagnie de Kervignarc;550;20;15;;Provisoire",
    ]


def test_les_rangs_sont_des_nombres_dans_le_classeur() -> None:
    # Un rang en texte se trie 1, 10, 2 (revue, axe D).
    section = SectionClassementQualification("Matin", False, (_SENIORS,))

    octets = GenerateurClassementQualificationTableur(rendre_xlsx).classement_qualification(
        _document(section)
    )

    feuille = load_workbook(BytesIO(octets)).active
    assert feuille is not None
    assert feuille["C2"].value == 1 and feuille["D2"].value == 4
    assert feuille["C2"].data_type == "n" and feuille["D2"].data_type == "n"
