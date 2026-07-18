"""Tests de l'adapter ReportLab des documents de salle (E09US008) — **après** l'implémentation
(infra, pas d'oracle).

On prouve que le rendu fonctionne : étiquettes de cible (QR compris) et cartes de scoreur produisent
de vrais PDF (`%PDF` … `%%EOF`), tiennent sur les cas limites (aucune cible, aucun scoreur,
caractères spéciaux) et enveloppent leurs échecs en `InfrastructureError` sans laisser fuir
d'exception ReportLab brute. Le QR est produit nativement par ReportLab (aucune dépendance ajoutée).
"""

from __future__ import annotations

import pytest

from domain.documents_salle import CarteScoreur, CartesScoreurs, EtiquetteCible, EtiquettesCibles
from infrastructure.erreurs import InfrastructureError
from infrastructure.pdf import GenerateurDocumentsSallePdf


def _etiquette(cible_index: int, code: str) -> EtiquetteCible:
    return EtiquetteCible(cible_index, code, f"http://192.168.1.10:8000/?poste={code}")


def test_etiquettes_genere_un_pdf_valide() -> None:
    document = EtiquettesCibles("Tournoi Test", (_etiquette(1, "AAA111"), _etiquette(2, "BBB222")))

    octets = GenerateurDocumentsSallePdf().etiquettes_cibles(document)

    assert octets.startswith(b"%PDF")
    assert octets.rstrip().endswith(b"%%EOF")
    assert len(octets) > 1000  # un document non trivial (QR compris), pas un stub vide


def test_etiquettes_sans_cible_reste_un_pdf_valide() -> None:
    """Aucune cible préparée produit tout de même un document (robuste), pas une erreur."""
    octets = GenerateurDocumentsSallePdf().etiquettes_cibles(EtiquettesCibles("Tournoi Test", ()))

    assert octets.startswith(b"%PDF")


def test_plus_de_cibles_alourdit_le_document() -> None:
    """Le PDF croît avec le nombre de cibles (un QR par cible réellement rendu, pas fixe)."""
    generateur = GenerateurDocumentsSallePdf()

    une = generateur.etiquettes_cibles(EtiquettesCibles("T", (_etiquette(1, "AAA111"),)))
    trois = generateur.etiquettes_cibles(
        EtiquettesCibles("T", tuple(_etiquette(i, f"COD{i:03d}") for i in range(1, 4)))
    )

    assert len(trois) > len(une)


def test_caracteres_speciaux_dans_le_nom_ne_cassent_pas_le_rendu() -> None:
    """`&`, `<`, `>` dans le nom du tournoi ne doivent pas casser le balisage des `Paragraph`."""
    document = EtiquettesCibles("Club Dupont & <fils>", (_etiquette(1, "AAA111"),))

    octets = GenerateurDocumentsSallePdf().etiquettes_cibles(document)

    assert octets.startswith(b"%PDF")


def test_cartes_scoreurs_genere_un_pdf_valide() -> None:
    document = CartesScoreurs("Tournoi Test", (CarteScoreur("Alice", "AAA222"),))

    octets = GenerateurDocumentsSallePdf().cartes_scoreurs(document)

    assert octets.startswith(b"%PDF")
    assert octets.rstrip().endswith(b"%%EOF")


def test_cartes_sans_scoreur_reste_un_pdf_valide() -> None:
    octets = GenerateurDocumentsSallePdf().cartes_scoreurs(CartesScoreurs("Tournoi Test", ()))

    assert octets.startswith(b"%PDF")


def test_echec_de_rendu_enveloppe_en_infrastructure_error() -> None:
    """Une URL mal typée fait échouer la génération du QR : elle remonte en `InfrastructureError`,
    pas en exception ReportLab brute."""
    document = EtiquettesCibles("T", (EtiquetteCible(1, "AAA111", None),))  # type: ignore[arg-type]

    with pytest.raises(InfrastructureError):
        GenerateurDocumentsSallePdf().etiquettes_cibles(document)
