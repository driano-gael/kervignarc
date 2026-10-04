"""Tests de l'adapter PDF du déroulé horaire (E09US007).

Tests **après** l'implémentation (règle 9 : adapters). Le PDF s'inspecte par `_corps()`, comme
`test_pdf_classement_qualification` : ReportLab n'offre pas de lecture.
"""

from __future__ import annotations

import re
from pathlib import Path

from reportlab.platypus import Flowable, KeepTogether, Paragraph, Table

from domain.contrat_phase import TypePhase
from domain.deroule_imprime import BlocDeroule, DerouleImprime, LigneDeroule
from domain.horaire_prevu import HeurePrevue
from infrastructure.libelles import LIBELLES_TYPE_PHASE
from infrastructure.pdf.deroule_horaire import A_PRECISER, GenerateurDerouleHorairePdf

_CATALOGUE_FRONT = (
    Path(__file__).resolve().parents[2] / "frontend" / "src" / "shared" / "phases" / "catalogue.ts"
)


def _ligne(
    ordre: int,
    type_phase: TypePhase,
    *,
    titre: str | None = None,
    debut: int | None = None,
    fin: int | None = None,
    tours: str | None = None,
) -> LigneDeroule:
    return LigneDeroule(
        ordre=ordre,
        type=type_phase,
        titre=titre,
        debut=None if debut is None else HeurePrevue(debut),
        fin=None if fin is None else HeurePrevue(fin),
        tours=tours,
    )


def _a_plat(elements: list[Flowable]) -> list[Flowable]:
    sortie: list[Flowable] = []
    for element in elements:
        if isinstance(element, KeepTogether):
            sortie.extend(_a_plat(list(element._content)))
        else:
            sortie.append(element)
    return sortie


def _textes(elements: list[Flowable]) -> list[str]:
    return [e.text for e in _a_plat(elements) if isinstance(e, Paragraph)]


def _tables(elements: list[Flowable]) -> list[Table]:
    return [e for e in _a_plat(elements) if isinstance(e, Table)]


def _lignes(table: Table) -> list[list[str]]:
    """Le texte de chaque cellule — le nom de la phase est un `Paragraph`, lu par son `.text`."""
    return [
        [c.text if isinstance(c, Paragraph) else c for c in ligne] for ligne in table._cellvalues
    ]


_DOCUMENT = DerouleImprime(
    tournoi="Salle 18m",
    blocs=(
        BlocDeroule(
            "Départ n°1 — 09:00",
            (
                _ligne(1, TypePhase.QUALIFICATION, debut=540, fin=720, tours="2 tours"),
                _ligne(2, TypePhase.ELIMINATION_DIRECTE, titre="Tableau des jeunes", debut=720),
            ),
        ),
        BlocDeroule(
            "Départ n°2 — 23:00",
            (_ligne(1, TypePhase.SUISSE, debut=23 * 60, fin=25 * 60 + 30, tours="5 rondes"),),
        ),
    ),
)


def test_un_titre_puis_un_bloc_par_creneau() -> None:
    textes = _textes(GenerateurDerouleHorairePdf()._corps(_DOCUMENT))

    assert textes == ["Déroulé horaire — Salle 18m", "Départ n°1 — 09:00", "Départ n°2 — 23:00"]


def test_une_ligne_par_phase_avec_heures_et_tours() -> None:
    matin, soir = _tables(GenerateurDerouleHorairePdf()._corps(_DOCUMENT))

    assert _lignes(matin) == [
        ["Phase", "Début", "Fin", "Tours"],
        ["Qualification", "09:00", "12:00", "2 tours"],
        ["Tableau des jeunes", "12:00", A_PRECISER, ""],
    ]
    assert _lignes(soir)[1] == ["Système suisse", "23:00", "01:30 (lendemain)", "5 rondes"]


def test_les_heures_particulieres_s_ecrivent_comme_a_l_ecran() -> None:
    """Arbitrage du 03/10/2026 : « (lendemain) » puis « (J+n) », comme `decrireHeure` ; seul
    l'inconnu diverge — « à préciser » au lieu de « — »."""
    bloc = BlocDeroule(
        "Départ n°1 — 22:00",
        (_ligne(1, TypePhase.QUALIFICATION, debut=22 * 60, fin=2 * 24 * 60 + 60),),
    )
    document = DerouleImprime(tournoi="Salle 18m", blocs=(bloc,))

    (table,) = _tables(GenerateurDerouleHorairePdf()._corps(document))

    assert _lignes(table)[1][1:3] == ["22:00", "01:00 (J+2)"]
    assert A_PRECISER == "à préciser"


def test_un_titre_long_passe_a_la_ligne_au_lieu_de_recouvrir_l_heure() -> None:
    """Le DTO admet 80 caractères ; une cellule texte n'en tient qu'environ 45 dans sa colonne."""
    titre = "Tableau des jeunes & cadets <arc classique> — poussins, benjamins, minimes 2026!"
    assert len(titre) == 80
    document = DerouleImprime(
        tournoi="Salle 18m",
        blocs=(BlocDeroule("Départ n°1 — 09:00", (_ligne(1, TypePhase.POULES, titre=titre),)),),
    )

    (table,) = _tables(GenerateurDerouleHorairePdf()._corps(document))
    cellule = table._cellvalues[1][0]

    assert isinstance(cellule, Paragraph)
    assert "&amp;" in cellule.text and "&lt;arc classique&gt;" in cellule.text
    largeur = table._argW[0] - 12  # marges intérieures par défaut de la cellule (6 + 6)
    cellule.wrap(largeur, 1000)
    assert len(cellule.blPara.lines) > 1


def test_un_bloc_sans_phase_le_dit() -> None:
    document = DerouleImprime(tournoi="Salle 18m", blocs=(BlocDeroule("Départ n°1 — 09:00", ()),))

    elements = GenerateurDerouleHorairePdf()._corps(document)

    assert "Aucune phase au déroulé." in _textes(elements)
    assert _tables(elements) == []


def test_le_document_rendu_est_un_pdf() -> None:
    assert GenerateurDerouleHorairePdf().deroule_horaire(_DOCUMENT).startswith(b"%PDF")


def test_un_nom_a_caracteres_speciaux_est_echappe_dans_le_titre() -> None:
    document = DerouleImprime(tournoi="A & B <club>", blocs=())

    assert _textes(GenerateurDerouleHorairePdf()._corps(document)) == [
        "Déroulé horaire — A &amp; B &lt;club&gt;"
    ]


def test_chaque_type_de_phase_a_un_libelle_imprime() -> None:
    assert set(LIBELLES_TYPE_PHASE) == set(TypePhase)


def test_le_libelle_imprime_est_celui_de_l_ecran() -> None:
    """Garde de la copie : `LIBELLE_TYPE` du front et le registre serveur ne divergent pas."""
    source = _CATALOGUE_FRONT.read_text(encoding="utf-8")
    bloc = re.search(r"export const LIBELLE_TYPE[^{]*\{(.*?)\n\}", source, re.DOTALL)
    assert bloc is not None, "LIBELLE_TYPE introuvable dans catalogue.ts"
    front = dict(re.findall(r"^\s*(\w+):\s*'([^']*)',?$", bloc.group(1), re.MULTILINE))

    assert front == {
        type_phase.value: libelle for type_phase, libelle in LIBELLES_TYPE_PHASE.items()
    }
