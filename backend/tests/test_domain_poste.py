"""Tests de l'agrégat `Poste` (E04US001, élargi E07US004) — écrits **depuis le CA** (règle 9).

Le `Poste` est le **credential d'un point de rattachement** d'un tournoi, plus un `code`
distribuable. Deux natures depuis E07US004 : une **cible** (le couple `(tournoi_id, cible_index)`,
ADR-0029) et un **écran de salle** (un libellé de place dans le gymnase — CA « l'écran est un poste
de l'appli publique rattaché par jeton », « plusieurs écrans possibles »). Le domaine ne garantit
que ses **invariants de construction** ; l'unicité du code et sa génération sont des règles
d'**ensemble** (service + `UNIQUE` en base), testées ailleurs.
"""

from __future__ import annotations

import pytest

from domain.erreurs import CibleInvalide, CodePosteInvalide, LibelleEcranInvalide, PosteSansCible
from domain.poste import Poste, TypePoste, normaliser_code


def test_creer_construit_un_poste_valide() -> None:
    poste = Poste.creer(tournoi_id=7, cible_index=12, code="AB12CD")

    assert poste.id is None
    assert poste.tournoi_id == 7
    assert poste.cible_index == 12
    assert poste.code == "AB12CD"


def test_creer_normalise_le_code() -> None:
    """Le code est stocké sous forme canonique (majuscules, espaces de bord retirés)."""
    poste = Poste.creer(tournoi_id=1, cible_index=1, code="  ab12cd ")

    assert poste.code == "AB12CD"


def test_creer_refuse_une_cible_non_positive() -> None:
    with pytest.raises(CibleInvalide):
        Poste.creer(tournoi_id=1, cible_index=0, code="AB12CD")


def test_creer_refuse_un_code_vide() -> None:
    """Le code est **généré** (jamais saisi ici) : cette garde protège l'invariant de l'agrégat."""
    with pytest.raises(CodePosteInvalide):
        Poste.creer(tournoi_id=1, cible_index=1, code="   ")


def test_normaliser_code_replie_casse_et_espaces() -> None:
    assert normaliser_code("  ab12cd ") == "AB12CD"
    assert normaliser_code("AB12CD") == "AB12CD"


# --- Écran de salle (E07US004) -------------------------------------------------------------------


def test_creer_cible_est_de_type_cible() -> None:
    """Non-régression : un poste de cible garde sa nature, et n'a pas de libellé."""
    poste = Poste.creer(tournoi_id=7, cible_index=12, code="AB12CD")

    assert poste.type is TypePoste.CIBLE
    assert poste.libelle is None


def test_creer_ecran_construit_un_poste_sans_cible() -> None:
    """CA « l'écran est un poste rattaché par jeton » : même credential, autre nature.

    Un écran n'est pas devant une cible — il est *quelque part* dans le gymnase, d'où un **libellé**
    à la place de l'index (« près du pas de tir »), qui sert à le désigner dans la supervision.
    """
    ecran = Poste.creer_ecran(tournoi_id=7, libelle="  Près du pas de tir ", code="ec01zz")

    assert ecran.type is TypePoste.ECRAN
    assert ecran.tournoi_id == 7
    assert ecran.libelle == "Près du pas de tir"
    assert ecran.cible_index is None
    assert ecran.code == "EC01ZZ"


def test_creer_ecran_refuse_un_libelle_vide() -> None:
    """Un écran sans nom serait indésignable dans la console : « écran n°2 » ne se pilote pas."""
    with pytest.raises(LibelleEcranInvalide):
        Poste.creer_ecran(tournoi_id=1, libelle="   ", code="EC01ZZ")


def test_cible_rend_l_index_d_un_poste_de_cible() -> None:
    assert Poste.creer(tournoi_id=1, cible_index=4, code="AB12CD").cible() == 4


def test_cible_refuse_un_ecran() -> None:
    """Un écran ne saisit pas de score : lui demander sa cible est une **erreur de programme**.

    L'accesseur remplace un `cible_index` devenu `int | None` : plutôt que de laisser chaque
    appelant décider quoi faire d'un `None` (et parfois l'oublier), l'invariant « seul un poste de
    cible a une cible » est **rendu exigible** au point d'usage.
    """
    ecran = Poste.creer_ecran(tournoi_id=1, libelle="Podium", code="EC01ZZ")

    with pytest.raises(PosteSansCible):
        ecran.cible()
