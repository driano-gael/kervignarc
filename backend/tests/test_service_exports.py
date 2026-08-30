"""Tests du catalogue d'exports (E16US007) — dérivés du CA, avant implémentation (règle 9).

Trois CA sont vérifiables ici :

- **« chaque export propose ses formats disponibles »** — le catalogue énumère les exports et, pour
  chacun, ce que le serveur sait produire ;
- **« l'ajout d'un format ne demande pas de toucher l'écran »** — la propriété n'est tenue que si
  les formats d'une entrée **dérivent du câblage** et non d'une table écrite à côté. On le prouve
  en branchant un générateur de plus : le catalogue le publie sans qu'aucune entrée soit modifiée ;
- **« un export n'offre que les formats qui ont un sens »** — la liste est **par export**. Un
  catalogue dont toutes les entrées offriraient les mêmes formats ne prouverait rien : le décor de
  ces tests contient donc, exprès, un document mono-format.

Le rendu lui-même n'est pas testé ici (adapters, testés à part) : `RegistreDeFormats` ne décide que
*quel* générateur répond, et le catalogue *ce qu'on annonce au client*.
"""

from __future__ import annotations

import pytest

from application.erreurs import FormatExportIndisponible
from application.exports import (
    LIBELLES_FORMAT,
    CatalogueExports,
    EntreeCatalogueExport,
    FormatExport,
    RegistreDeFormats,
    construire_catalogue,
)

# --- Doublures ------------------------------------------------------------------------------------


class FauxGenerateur:
    """Générateur sentinelle : porte seulement de quoi l'identifier dans une assertion."""

    def __init__(self, marque: str) -> None:
        self.marque = marque


# --- « chaque export propose ses formats disponibles » ------------------------------------------


def test_le_catalogue_enumere_chaque_export_avec_ses_formats() -> None:
    catalogue = CatalogueExports(
        (
            EntreeCatalogueExport(
                identifiant="placement", formats=(FormatExport.PDF, FormatExport.CSV)
            ),
        )
    )

    (entree,) = catalogue.entrees

    assert entree.identifiant == "placement"
    assert entree.formats == (FormatExport.PDF, FormatExport.CSV)


def test_un_export_mono_format_n_annonce_qu_un_format() -> None:
    """CA « que les formats qui ont un sens » : une feuille de marque se remplit à la main."""
    registre = RegistreDeFormats({FormatExport.PDF: FauxGenerateur("pdf")})

    entree = EntreeCatalogueExport(identifiant="feuille-de-marque", formats=registre.formats)

    assert entree.formats == (FormatExport.PDF,)


def test_deux_exports_du_meme_catalogue_peuvent_offrir_des_formats_differents() -> None:
    catalogue = CatalogueExports(
        (
            EntreeCatalogueExport(
                identifiant="placement",
                formats=RegistreDeFormats(
                    {
                        FormatExport.PDF: FauxGenerateur("pdf"),
                        FormatExport.CSV: FauxGenerateur("csv"),
                    }
                ).formats,
            ),
            EntreeCatalogueExport(
                identifiant="feuille-de-marque",
                formats=RegistreDeFormats({FormatExport.PDF: FauxGenerateur("pdf")}).formats,
            ),
        )
    )

    formats = {entree.identifiant: entree.formats for entree in catalogue.entrees}

    assert formats == {
        "placement": (FormatExport.PDF, FormatExport.CSV),
        "feuille-de-marque": (FormatExport.PDF,),
    }


# --- « l'ajout d'un format ne demande pas de toucher l'écran » ----------------------------------


def test_les_formats_annonces_derivent_du_cablage() -> None:
    """Le catalogue ne tient **aucune** liste de formats en propre : il lit le registre câblé.

    C'est ce qui rend le CA vérifiable. Une entrée qui figerait `(PDF, CSV)` en dur serait une
    seconde source : elle continuerait d'annoncer le CSV après un débranchement, et le client
    recevrait une 400 sur un format que le serveur lui a lui-même proposé.
    """
    avec_un_seul = RegistreDeFormats({FormatExport.PDF: FauxGenerateur("pdf")})
    assert avec_un_seul.formats == (FormatExport.PDF,)

    # Un format de plus au câblage — **rien d'autre ne change**, ni l'entrée, ni le catalogue.
    avec_deux = RegistreDeFormats(
        {FormatExport.PDF: FauxGenerateur("pdf"), FormatExport.CSV: FauxGenerateur("csv")}
    )
    assert avec_deux.formats == (FormatExport.PDF, FormatExport.CSV)


def test_les_formats_sortent_dans_l_ordre_du_catalogue_pas_du_cablage() -> None:
    """Ordre **stable** : l'écran présente toujours les formats dans le même ordre.

    Sans cela, l'ordre des boutons dépendrait de l'ordre d'écriture au composition root — un
    détail invisible en revue qui déplacerait un bouton sous le doigt de l'organisateur.
    """
    registre = RegistreDeFormats(
        {FormatExport.CSV: FauxGenerateur("csv"), FormatExport.PDF: FauxGenerateur("pdf")}
    )

    assert registre.formats == (FormatExport.PDF, FormatExport.CSV)


# --- Résolution d'un format demandé ---------------------------------------------------------------


def test_le_registre_rend_le_generateur_du_format_demande() -> None:
    pdf, csv = FauxGenerateur("pdf"), FauxGenerateur("csv")
    registre = RegistreDeFormats({FormatExport.PDF: pdf, FormatExport.CSV: csv})

    assert registre.pour(FormatExport.PDF) is pdf
    assert registre.pour(FormatExport.CSV) is csv


def test_un_format_non_cable_est_refuse_et_nomme_ceux_qui_le_sont() -> None:
    """Le refus est une **erreur applicative** (→ 400), pas un `KeyError` qui partirait en 500.

    Le message nomme les formats disponibles : c'est la seule information utile au client, et elle
    n'expose rien d'interne (règle 5).
    """
    registre = RegistreDeFormats({FormatExport.PDF: FauxGenerateur("pdf")})

    with pytest.raises(FormatExportIndisponible) as echec:
        registre.pour(FormatExport.CSV)

    assert "csv" in str(echec.value)
    assert "pdf" in str(echec.value)


def test_un_registre_vide_est_refuse_a_la_construction() -> None:
    """Un document sans aucun générateur est un défaut de câblage, pas une entrée à zéro format.

    ⚠️ Le laisser passer publierait au catalogue un export que l'écran afficherait **sans aucun
    bouton** — l'organisateur verrait un document qu'il ne peut pas sortir, sans savoir pourquoi.
    """
    with pytest.raises(ValueError):
        RegistreDeFormats[FauxGenerateur]({})


# --- Cohérence du registre de formats -------------------------------------------------------------


def test_chaque_format_a_un_libelle() -> None:
    """Garde-fou de registres jumeaux : l'énumération et la table de libellés ne dérivent pas.

    Patron déjà employé entre `TYPES_DEROULES` et `TYPES_ARRETABLES` (E05US035). Sans lui, ajouter
    un membre à `FormatExport` sans son libellé ne casserait rien avant la première requête.
    ⚠️ Le **type MIME** a son jumeau à la frontière API (`test_listes_impression_api.py`) : il y a
    deux tables, parce qu'elles n'appartiennent pas à la même couche.
    """
    assert set(LIBELLES_FORMAT) == set(FormatExport)


def test_l_extension_de_fichier_est_le_code_du_format() -> None:
    """Le nom de fichier proposé au client dérive du format — pas d'une table de plus."""
    assert FormatExport.PDF.value == "pdf"
    assert FormatExport.CSV.value == "csv"


# --- La fabrique du catalogue (là où la dérivation peut casser) ---------------------------------


def test_le_catalogue_construit_annonce_les_formats_qu_on_lui_donne() -> None:
    """⚠️ **Le seul test qui garde la dérivation là où elle vit.** Relevé en revue (axe B) : tant
    que le catalogue était composé dans `bootstrap/`, réécrire `formats=(PDF, CSV)` à la main y
    passait sans rien faire rougir — alors qu'ADR-0101 §3 en fait l'invariant central. Le décor
    donne aux listes **un seul** format : une liste écrite en dur en annoncerait deux.
    """
    catalogue = construire_catalogue(
        formats_listes=(FormatExport.PDF,), formats_feuille=(FormatExport.PDF,)
    )

    formats = {entree.identifiant: entree.formats for entree in catalogue.entrees}

    assert formats == {
        "placement": (FormatExport.PDF,),
        "club-paiement": (FormatExport.PDF,),
        "feuille-de-marque": (FormatExport.PDF,),
    }


def test_le_catalogue_construit_distingue_les_listes_de_la_feuille_de_marque() -> None:
    catalogue = construire_catalogue(
        formats_listes=(FormatExport.PDF, FormatExport.CSV), formats_feuille=(FormatExport.PDF,)
    )

    formats = {entree.identifiant: entree.formats for entree in catalogue.entrees}

    assert formats["placement"] == (FormatExport.PDF, FormatExport.CSV)
    assert formats["feuille-de-marque"] == (FormatExport.PDF,)
