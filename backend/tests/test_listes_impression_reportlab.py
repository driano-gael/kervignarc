"""Tests de l'adapter ReportLab des listes imprimables (E09US003) — **après** l'implémentation.

Infra, pas d'oracle : on prouve que le rendu produit un vrai PDF (`%PDF`… `%%EOF`), tient sur les
cas limites (listes vides, caractères spéciaux) et enveloppe ses échecs en `InfrastructureError`
sans laisser fuir d'exception ReportLab brute.
"""

from __future__ import annotations

import pytest

from domain.listes_impression import (
    GroupePaiementClub,
    LignePaiementImpression,
    LignePlacement,
    ListeClubPaiement,
    ListePlacement,
    TriPlacement,
)
from infrastructure.erreurs import InfrastructureError
from infrastructure.pdf import GenerateurListesImpressionPdf


def _ligne_placement(nom: str = "Durand", categorie: str = "Sénior Homme") -> LignePlacement:
    return LignePlacement(
        nom=nom, prenom="Marie", categorie=categorie, depart_numero=1, cible_index=2, position="A"
    )


def test_placement_genere_un_pdf_valide() -> None:
    liste = ListePlacement(
        tournoi="Tournoi Test",
        depart_numero=None,
        tri=TriPlacement.CIBLE,
        lignes=(_ligne_placement(), _ligne_placement(nom="Zola")),
    )

    octets = GenerateurListesImpressionPdf().placement(liste)

    assert octets.startswith(b"%PDF")
    assert octets.rstrip().endswith(b"%%EOF")
    assert len(octets) > 1000


def test_placement_vide_reste_un_pdf_valide() -> None:
    """Une liste sans archer placé produit tout de même un document (socle robuste)."""
    liste = ListePlacement(tournoi="Tournoi Test", depart_numero=3, tri=TriPlacement.NOM, lignes=())

    octets = GenerateurListesImpressionPdf().placement(liste)

    assert octets.startswith(b"%PDF")


def test_placement_caracteres_speciaux_ne_cassent_pas_le_rendu() -> None:
    """`&`, `<`, `>` dans une donnée ne doivent pas casser le balisage des `Paragraph`."""
    liste = ListePlacement(
        tournoi="Tournoi & <cie>",
        depart_numero=None,
        tri=TriPlacement.CIBLE,
        lignes=(_ligne_placement(nom="Dupont & <fils>", categorie="Cat <U18>"),),
    )

    octets = GenerateurListesImpressionPdf().placement(liste)

    assert octets.startswith(b"%PDF")


def test_placement_echec_de_rendu_enveloppe_en_infrastructure_error() -> None:
    """Une donnée qui fait échouer le rendu remonte en `InfrastructureError`, pas en exception
    brute : une `position` non textuelle casse l'échappement du mini-HTML."""
    liste = ListePlacement(
        tournoi="T",
        depart_numero=None,
        tri=TriPlacement.CIBLE,
        lignes=(
            LignePlacement(
                nom="Durand",
                prenom="Marie",
                categorie="Cat",
                depart_numero=1,
                cible_index=2,
                position=None,  # type: ignore[arg-type]
            ),
        ),
    )
    with pytest.raises(InfrastructureError):
        GenerateurListesImpressionPdf().placement(liste)


def _groupe(club: str = "Arcs de Test") -> GroupePaiementClub:
    return GroupePaiementClub(
        club=club,
        lignes=(
            LignePaiementImpression(
                nom="Durand", prenom="Marie", departs=(1, 2), du_centimes=1600, paye_centimes=1600
            ),
            LignePaiementImpression(
                nom="Zola", prenom="Émile", departs=(1,), du_centimes=800, paye_centimes=0
            ),
        ),
        total_du_centimes=2400,
        total_paye_centimes=1600,
    )


def test_club_paiement_genere_un_pdf_valide() -> None:
    liste = ListeClubPaiement(
        tournoi="Tournoi Test", groupes=(_groupe(), _groupe(club="Sans club"))
    )

    octets = GenerateurListesImpressionPdf().club_paiement(liste)

    assert octets.startswith(b"%PDF")
    assert octets.rstrip().endswith(b"%%EOF")
    assert len(octets) > 1000


def test_club_paiement_vide_reste_un_pdf_valide() -> None:
    liste = ListeClubPaiement(tournoi="Tournoi Test", groupes=())

    octets = GenerateurListesImpressionPdf().club_paiement(liste)

    assert octets.startswith(b"%PDF")


def test_club_paiement_echec_de_rendu_enveloppe_en_infrastructure_error() -> None:
    """Un total non convertible casse la construction : l'échec remonte en `InfrastructureError`."""
    groupe = GroupePaiementClub(
        club="Club",
        lignes=(),
        total_du_centimes=None,  # type: ignore[arg-type]
        total_paye_centimes=0,
    )
    liste = ListeClubPaiement(tournoi="T", groupes=(groupe,))
    with pytest.raises(InfrastructureError):
        GenerateurListesImpressionPdf().club_paiement(liste)
