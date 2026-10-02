"""Tests de l'adapter PDF du classement de qualification (E09US005).

Tests **après** l'implémentation (règle 9 : adapters). Le PDF s'inspecte par `_corps()`, comme
`test_pdf_palmares` : ReportLab n'offre pas de lecture, et les `Flowable` portent ce que l'adapter
a décidé d'émettre. Le débordement, lui, se vérifie par le **découpage réel** de la table
(`Table.split`) et par le nombre de pages du document rendu.
"""

from __future__ import annotations

import re

from reportlab.lib.pagesizes import A4
from reportlab.platypus import Flowable, PageBreak, Paragraph, Table

from domain.classement import LigneClassement, StatutClassement
from domain.classement_imprime import (
    BlocCategorie,
    ClassementQualificationImprime,
    SectionClassementQualification,
)
from infrastructure.pdf.classement_qualification import (
    PROVISOIRE,
    GenerateurClassementQualificationPdf,
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


def _textes(elements: list[Flowable]) -> list[str]:
    return [element.text for element in elements if isinstance(element, Paragraph)]


def _tables(elements: list[Flowable]) -> list[Table]:
    return [e for e in elements if isinstance(e, Table)]


def test_le_pdf_rend_une_page_par_categorie_qui_se_lit_seule() -> None:
    section = SectionClassementQualification("Départ n°1 — 09:00", False, (_SENIORS, _CADETS))

    elements = GenerateurClassementQualificationPdf()._corps(_document(section))

    assert sum(isinstance(e, PageBreak) for e in elements) == 1
    textes = _textes(elements)
    assert textes.count("Classement de qualification — Salle 18m") == 2
    assert textes.count("Départ n°1 — 09:00") == 2
    assert "Senior Homme" in textes and "Cadet" in textes
    assert PROVISOIRE not in textes


def test_le_pdf_marque_chaque_page_d_un_depart_provisoire() -> None:
    matin = SectionClassementQualification("Matin", False, (_SENIORS,))
    apres_midi = SectionClassementQualification("Après-midi", True, (_SENIORS, _CADETS))

    elements = GenerateurClassementQualificationPdf()._corps(_document(matin, apres_midi))

    assert _textes(elements).count(PROVISOIRE) == 2
    rappels = [table._cellvalues[0][0] for table in _tables(elements)]
    assert rappels == [
        "Salle 18m — Matin — Senior Homme",
        "Salle 18m — Après-midi — Senior Homme — Classement provisoire",
        "Salle 18m — Après-midi — Cadet — Classement provisoire",
    ]


def test_le_pdf_imprime_rang_de_categorie_avant_rang_general() -> None:
    section = SectionClassementQualification("Matin", False, (_SENIORS,))

    elements = GenerateurClassementQualificationPdf()._corps(_document(section))

    (table,) = _tables(elements)
    contenu = table._cellvalues
    assert contenu[1][:2] == ["Rang", "Général"]
    assert contenu[2] == [
        "1",
        "4",
        "NOM1",
        "Jean",
        "Compagnie de Kervignarc",
        "550",
        "20",
        "15",
        "",
    ]
    assert contenu[3][:2] == ["—", "—"] and contenu[3][-1] == "Disqualifié"


def test_une_categorie_qui_deborde_garde_son_rappel_sur_chaque_page() -> None:
    nombreux = BlocCategorie("Senior Homme", tuple(_ligne(n, n, n) for n in range(1, 61)))
    section = SectionClassementQualification("Après-midi", True, (nombreux,))
    generateur = GenerateurClassementQualificationPdf()

    (table,) = _tables(generateur._corps(_document(section)))
    largeur, hauteur = A4
    morceaux = table.split(largeur - 30 * 2.835, hauteur - 30 * 2.835)

    assert len(morceaux) >= 2
    for morceau in morceaux:
        assert morceau._cellvalues[0][0] == (
            "Salle 18m — Après-midi — Senior Homme — Classement provisoire"
        )
        assert morceau._cellvalues[1][0] == "Rang"
    octets = generateur.classement_qualification(_document(section))
    assert len(re.findall(rb"/Type /Page\b(?!s)", octets)) >= 2


def test_un_creneau_sans_archer_le_dit() -> None:
    section = SectionClassementQualification("Matin", True, ())

    elements = GenerateurClassementQualificationPdf()._corps(_document(section))

    assert "Aucun archer engagé dans ce créneau." in _textes(elements)


def test_le_pdf_rendu_est_un_document() -> None:
    section = SectionClassementQualification("Matin", False, (_SENIORS,))

    octets = GenerateurClassementQualificationPdf().classement_qualification(_document(section))

    assert octets.startswith(b"%PDF")
