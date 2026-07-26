"""Tests de l'adapter ReportLab des listes imprimables (E09US003) — **après** l'implémentation.

Infra, pas d'oracle : on prouve que le rendu produit un vrai PDF (`%PDF`… `%%EOF`), tient sur les
cas limites (listes vides, caractères spéciaux) et enveloppe ses échecs en `InfrastructureError`
sans laisser fuir d'exception ReportLab brute.
"""

from __future__ import annotations

import base64
import re
import zlib

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
from infrastructure.pdf.listes_impression import _euros


def test_euros_formate_les_centimes() -> None:
    """Centimes entiers → euros « x,xx € » (virgule décimale) : zéro, unité, gros montant."""
    assert _euros(0) == "0,00 €"
    assert _euros(800) == "8,00 €"
    assert _euros(810) == "8,10 €"
    assert _euros(1_234_567) == "12345,67 €"


def _texte_pdf(octets: bytes) -> str:
    """Texte réellement dessiné dans un PDF ReportLab (flux de page décompressés).

    ReportLab encode les flux de page en **ASCII85 puis Flate** (chaîne de filtres par défaut) : on
    les décode pour inspecter le texte tel qu'il sera imprimé — sans dépendance externe (`base64` et
    `zlib` sont stdlib). Sert à prouver qu'une cellule de `Table` n'est **pas** doublement échappée
    (« &amp; » au lieu de « & »). Si l'encodage ReportLab changeait, l'extraction retournerait vide
    et l'assertion « texte présent » du test échouerait franchement — jamais un faux vert muet."""
    morceaux: list[bytes] = []
    for bloc in re.findall(rb"stream\r?\n(.*?)endstream", octets, re.DOTALL):
        donnees = bloc.strip(b"\r\n \t")
        try:
            if donnees.endswith(b"~>"):  # flux ASCII85 (défaut ReportLab), puis Flate
                donnees = base64.a85decode(donnees[:-2])
            morceaux.append(zlib.decompress(donnees))
        except (zlib.error, ValueError):
            morceaux.append(bloc)
    return b"\n".join(morceaux).decode("latin-1", errors="replace")


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


def test_placement_caracteres_speciaux_rendus_litteralement() -> None:
    """`&`, `<`, `>` dans une donnée s'impriment **tels quels**, ni cassés ni doublement échappés.

    Les cellules de `Table` sont dessinées brutes (pas de mini-HTML) : un nom « Dupont & Cie » doit
    apparaître littéralement, jamais « Dupont &amp; Cie ». Ce test verrouille le correctif de revue
    (axe C1) — l'ancienne version échappait à tort les cellules."""
    liste = ListePlacement(
        tournoi="Tournoi Test",
        depart_numero=None,
        tri=TriPlacement.CIBLE,
        lignes=(_ligne_placement(nom="Dupont & Cie", categorie="Cat <U18>"),),
    )

    octets = GenerateurListesImpressionPdf().placement(liste)

    assert octets.startswith(b"%PDF")
    texte = _texte_pdf(octets)
    assert (
        "Dupont" in texte
    ), "extraction du texte PDF opérante (sinon l'assertion suivante est vide)"
    assert "&amp;" not in texte  # pas de double échappement en cellule
    assert "&lt;" not in texte


def test_placement_echec_de_rendu_enveloppe_en_infrastructure_error() -> None:
    """Une donnée qui fait échouer le rendu remonte en `InfrastructureError`, pas en exception
    brute : un nom de tournoi non textuel casse l'échappement du titre (`Paragraph`)."""
    liste = ListePlacement(
        tournoi=None,  # type: ignore[arg-type]
        depart_numero=None,
        tri=TriPlacement.CIBLE,
        lignes=(_ligne_placement(),),
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
