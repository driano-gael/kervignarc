"""Tests de l'adapter tableur du classement de qualification (E09US005).

Tests **après** l'implémentation (règle 9 : adapters).
"""

from __future__ import annotations

from domain.classement import LigneClassement, StatutClassement
from domain.classement_imprime import (
    BlocCategorie,
    ClassementQualificationImprime,
    SectionClassementQualification,
)
from infrastructure.tableur import GenerateurClassementQualificationTableur, rendre_csv


def _ligne(
    archer_id: int, rang: int | None, statut: StatutClassement = StatutClassement.EN_LICE
) -> LigneClassement:
    return LigneClassement(
        rang_scratch=rang,
        rang_categorie=rang,
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


_SENIORS = BlocCategorie(
    "Senior Homme", (_ligne(1, 1), _ligne(2, None, StatutClassement.DISQUALIFIE))
)
_CADETS = BlocCategorie("Cadet", (_ligne(3, 1),))


def test_le_tableur_rend_a_plat_avec_depart_categorie_et_etat() -> None:
    matin = SectionClassementQualification("Matin", False, (_SENIORS,))
    apres_midi = SectionClassementQualification("Après-midi", True, (_CADETS,))

    octets = GenerateurClassementQualificationTableur(rendre_csv).classement_qualification(
        _document(matin, apres_midi)
    )

    lignes = octets.decode("utf-8-sig").splitlines()
    assert lignes[1:] == [
        "Matin;Senior Homme;1;1;NOM1;Jean;Compagnie de Kervignarc;550;20;15;;Définitif",
        "Matin;Senior Homme;;;NOM2;Jean;Compagnie de Kervignarc;550;20;15;Disqualifié;Définitif",
        "Après-midi;Cadet;1;1;NOM3;Jean;Compagnie de Kervignarc;550;20;15;;Provisoire",
    ]
