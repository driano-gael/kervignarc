"""Lecteurs de fichiers d'inscrits (E02US007) — sur les deux exports réels versés au dépôt."""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from application.referentiel_ffta import ARC_CLASSIQUE, ARC_NU, ARC_POULIES
from domain.categorie import SexeCategorie
from domain.erreurs import FichierInscritsIllisible
from domain.import_inscrits import SourceImport
from infrastructure.import_inscrits import LecteurFichierInscritsAuto

_ECHANTILLONS = Path(__file__).resolve().parents[2] / "docs" / "sources" / "import inscription"
_IANSEO = _ECHANTILLONS / "Export_Ianseo_challenge-des-champions-de-kervignac.csv"
_RESULTARC = _ECHANTILLONS / "Resultarc_challenge-des-champions-de-kervignac.xls"

lecteur = LecteurFichierInscritsAuto()


def test_l_export_ianseo_reel_se_lit_en_entier() -> None:
    fichier = lecteur.lire(_IANSEO.read_bytes())

    assert fichier.source is SourceImport.IANSEO
    assert len(fichier.lignes) == 99
    premiere = fichier.lignes[0]
    assert premiere.numero == 1
    assert premiere.licence == "1025022Q"
    assert premiere.depart_numero == 1
    assert (premiere.nom, premiere.prenom) == ("ADVENARD", "VALÉRIE")
    assert premiere.sexe is SexeCategorie.FEMME
    assert premiere.date_naissance == datetime.date(1975, 8, 21)
    assert premiere.club == "MONTOIR DE BRETAGNE"
    assert premiere.arme is None  # `TA` = tous arcs (arbitrage du 26/09/2026)
    assert all(ligne.anomalie is None for ligne in fichier.lignes)
    assert sum(ligne.sexe is SexeCategorie.HOMME for ligne in fichier.lignes) == 71


def test_le_classeur_resultarc_reel_se_lit_malgre_sa_table_ole2_mal_formee() -> None:
    fichier = lecteur.lire(_RESULTARC.read_bytes())

    assert fichier.source is SourceImport.RESULTARC
    assert len(fichier.lignes) == 99
    premiere = fichier.lignes[0]
    assert premiere.numero == 2  # rangée 2 du classeur : la 1ʳᵉ est l'en-tête
    assert premiere.licence == "1025022Q"
    assert premiere.depart_numero == 1
    assert premiere.nom is None
    assert "Mode Paiement" in fichier.colonnes_ignorees
    assert "Trispot" in fichier.colonnes_ignorees


def test_ianseo_une_ligne_courte_revient_en_anomalie_sans_faire_echouer_le_fichier() -> None:
    bonne = "1234567A;1;CL;F;;1;1;1;1;1;DUPONT;JEANNE;1;0356098;KERVIGNAC;1990-01-01;;;;;"
    contenu = f"{bonne}\nPAS;ASSEZ\n".encode("latin-1")

    fichier = lecteur.lire(contenu)

    assert [ligne.anomalie is None for ligne in fichier.lignes] == [True, False]
    assert fichier.lignes[1].numero == 2


def test_ianseo_une_date_illisible_revient_en_anomalie() -> None:
    contenu = b"1234567A;1;CL;F;;1;1;1;1;1;DUPONT;JEANNE;1;0356098;KERVIGNAC;hier;;;;;"

    (ligne,) = lecteur.lire(contenu).lignes

    assert ligne.anomalie is not None and "hier" in ligne.anomalie


def test_ianseo_accepte_une_date_a_la_francaise_et_l_utf8() -> None:
    contenu = "1234567A;2;CL;F;;1;1;1;1;1;DUPONT;CÉLIA;1;0356098;KERVIGNAC;21/08/1975;;;".encode()

    (ligne,) = lecteur.lire(contenu).lignes

    assert ligne.prenom == "CÉLIA"
    assert ligne.date_naissance == datetime.date(1975, 8, 21)
    assert ligne.depart_numero == 2


@pytest.mark.parametrize(
    "contenu",
    [
        b"",
        b"   \n",
        b"nom;prenom\nDupont;Jeanne\n",
        b"PK\x03\x04 un xlsx",
        b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1 tronque",
    ],
)
def test_un_fichier_d_aucune_source_connue_est_refuse(contenu: bytes) -> None:
    with pytest.raises(FichierInscritsIllisible):
        lecteur.lire(contenu)


# --- Revue d'E02US007 : traduction des armes (axes B, C1 ; arbitrage « TA = tous arcs ») ---------


def _ligne_ianseo(division: str, session: str = "1") -> bytes:
    return (
        f"1234567A;{session};{division};F;;1;1;1;1;1;DUPONT;JEANNE;1;0356098;KERVIGNAC;1990-01-01;;;"
    ).encode("latin-1")


@pytest.mark.parametrize(
    ("division", "arme"),
    [
        ("CL", ARC_CLASSIQUE),
        ("R", ARC_CLASSIQUE),
        ("CO", ARC_POULIES),
        ("C", ARC_POULIES),
        ("BB", ARC_NU),
        ("B", ARC_NU),
        ("cl", ARC_CLASSIQUE),
        ("TA", None),
        ("", None),
        ("XY", "XY"),
    ],
)
def test_ianseo_traduit_la_division_en_arme_du_catalogue(division: str, arme: str | None) -> None:
    (ligne,) = lecteur.lire(_ligne_ianseo(division)).lignes

    assert ligne.arme == arme


def test_ianseo_une_session_non_decimale_ne_fait_pas_echouer_le_fichier() -> None:
    """`"²".isdigit()` est vrai mais `int("²")` lève : l'octet 0xB2 en Latin-1 donne « ² »."""
    fichier = lecteur.lire(
        _ligne_ianseo("CL", session="\xb2") + b"\n" + _ligne_ianseo("CL", "9" * 5000)
    )

    assert [ligne.depart_numero for ligne in fichier.lignes] == [None, None]


def test_ianseo_un_champ_demesure_rend_le_fichier_illisible_et_non_une_erreur_interne() -> None:
    contenu = b'"' + b"x" * 200_000 + b"\n" + _ligne_ianseo("CL")

    with pytest.raises(FichierInscritsIllisible):
        lecteur.lire(contenu)
