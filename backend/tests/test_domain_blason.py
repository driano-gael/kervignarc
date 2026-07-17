"""Tests unitaires de l'agrégat Blason (E01US005, zones : E01US014) — domaine pur, sans base."""

from __future__ import annotations

import pytest

from domain.blason import ZONES_CANONIQUES, ZONES_DEFAUT, Blason, ZoneScore, valider_zones
from domain.erreurs import (
    CapaciteBlasonInvalide,
    NomBlasonInvalide,
    TailleBlasonInvalide,
    ZonesBlasonInvalides,
)


def test_creer_un_blason_valide() -> None:
    """Nom, taille et capacité valides : id à None, rattaché au tournoi."""
    blason = Blason.creer(1, "Trispot 40", 0.5, 3)
    assert blason == Blason(
        tournoi_id=1, nom="Trispot 40", taille=0.5, capacite=3, zones=ZONES_DEFAUT, id=None
    )


def test_creer_normalise_le_nom() -> None:
    """Le nom est normalisé (espaces de bord retirés)."""
    blason = Blason.creer(1, "  Monospot 60  ", 1.0, 1)
    assert blason.nom == "Monospot 60"


@pytest.mark.parametrize("nom", ["", "   ", "\t\n"])
def test_creer_refuse_un_nom_vide(nom: str) -> None:
    """Un nom vide ou blanc lève une erreur de domaine typée."""
    with pytest.raises(NomBlasonInvalide):
        Blason.creer(1, nom, 0.5, 2)


def test_creer_accepte_taille_pleine() -> None:
    """La borne haute (taille = 1, place entière) est autorisée."""
    assert Blason.creer(1, "Monospot 60", 1.0, 1).taille == 1.0


@pytest.mark.parametrize("taille", [0.0, -0.5, 1.5, 2.0])
def test_creer_refuse_une_taille_hors_plage(taille: float) -> None:
    """Une taille hors de `]0, 1]` lève une erreur de domaine typée."""
    with pytest.raises(TailleBlasonInvalide):
        Blason.creer(1, "Blason", taille, 1)


@pytest.mark.parametrize("capacite", [0, -1])
def test_creer_refuse_une_capacite_inferieure_a_un(capacite: int) -> None:
    """Une capacité inférieure à 1 lève une erreur de domaine typée."""
    with pytest.raises(CapaciteBlasonInvalide):
        Blason.creer(1, "Blason", 0.5, capacite)


def test_modifier_met_a_jour_et_preserve_id_et_tournoi() -> None:
    """`modifier` change les attributs mais conserve `id` et `tournoi_id`."""
    blason = Blason(tournoi_id=3, nom="Ancien", taille=0.25, capacite=4, zones=ZONES_DEFAUT, id=9)
    modifie = blason.modifier("Nouveau", 0.5, 2, ZONES_DEFAUT)
    assert modifie == Blason(
        tournoi_id=3, nom="Nouveau", taille=0.5, capacite=2, zones=ZONES_DEFAUT, id=9
    )


def test_modifier_valide_les_attributs() -> None:
    """`modifier` applique les mêmes règles que `creer`."""
    blason = Blason.creer(1, "Blason", 0.5, 2)
    with pytest.raises(TailleBlasonInvalide):
        blason.modifier("Blason", 0.0, 2, ZONES_DEFAUT)
    with pytest.raises(CapaciteBlasonInvalide):
        blason.modifier("Blason", 0.5, 0, ZONES_DEFAUT)
    with pytest.raises(NomBlasonInvalide):
        blason.modifier("   ", 0.5, 2, ZONES_DEFAUT)


# --- Zones : valeurs de score admises (E01US014) --------------------------------------------
#
# Tests dérivés du CA d'E01US014 (`stories/E01-configuration.md`) et du référentiel FFTA
# (§4.2 vocabulaire des zones, §4.4 le triple 40 s'arrête à 6), écrits avant l'implémentation.


def test_creer_sans_zones_applique_le_blason_simple_complet() -> None:
    """CA « valeur par défaut cohérente » : le jeu FFTA complet d'un blason simple (§4.2).

    Le domaine ne peut pas déduire le type de blason : `taille` est une **fraction de place**,
    pas un diamètre. Le défaut est donc le sur-ensemble, que l'admin restreint pour un triple.
    """
    assert ZONES_DEFAUT == ("10", "9", "8", "7", "6", "5", "4", "3", "2", "1", "M")
    assert Blason.creer(1, "Monospot 60", 1.0, 1).zones == ZONES_DEFAUT


def test_creer_accepte_les_zones_d_un_triple_40() -> None:
    """Le cas qui motive l'US : un triple 40 n'a pas les zones 5 → 1, son minimum est 6 (§4.4)."""
    blason = Blason.creer(1, "Trispot 40", 0.5, 3, zones=["10", "9", "8", "7", "6", "M"])
    assert blason.zones == ("10", "9", "8", "7", "6", "M")


def test_les_zones_sont_immuables() -> None:
    """Agrégat `frozen` (règle 4) : les zones sont un tuple, pas une liste partagée."""
    saisie = ["10", "9", "M"]
    blason = Blason.creer(1, "Blason", 0.5, 1, zones=saisie)
    saisie.append("8")
    assert blason.zones == ("10", "9", "M")


def test_creer_normalise_l_ordre_des_zones() -> None:
    """L'ordre saisi ne porte pas d'information : seul l'ensemble compte, l'ordre est canonique."""
    blason = Blason.creer(1, "Trispot 40", 0.5, 3, zones=["M", "6", "9", "10", "7", "8"])
    assert blason.zones == ("10", "9", "8", "7", "6", "M")


@pytest.mark.parametrize(
    "zones", [["10", "9", "X", "M"], ["11", "10", "M"], ["dix", "M"], ["10", "", "M"]]
)
def test_creer_refuse_une_zone_hors_vocabulaire(zones: list[str]) -> None:
    """Le vocabulaire est celui du référentiel §4.2 : 10 → 1 et M.

    Ce n'est pas une vérification de conformité FFTA (RG-8 l'interdit) : c'est une contrainte
    d'intégrité aval — EPIC-04 doit **sommer** ces valeurs, un jeton inconnu n'a pas de sens.
    """
    with pytest.raises(ZonesBlasonInvalides):
        Blason.creer(1, "Blason", 0.5, 1, zones=zones)


def test_creer_refuse_un_doublon() -> None:
    """Une même zone ne peut pas être admise deux fois."""
    with pytest.raises(ZonesBlasonInvalides):
        Blason.creer(1, "Blason", 0.5, 1, zones=["10", "9", "9", "M"])


def test_creer_refuse_des_zones_sans_manque() -> None:
    """`M` est obligatoire : un manqué est toujours possible, le scoreur doit pouvoir le saisir."""
    with pytest.raises(ZonesBlasonInvalides):
        Blason.creer(1, "Blason", 0.5, 1, zones=["10", "9", "8"])


@pytest.mark.parametrize("zones", [[], ["M"]])
def test_creer_refuse_des_zones_sans_valeur_marquante(zones: list[str]) -> None:
    """Un blason sans aucune zone marquante n'existe pas."""
    with pytest.raises(ZonesBlasonInvalides):
        Blason.creer(1, "Blason", 0.5, 1, zones=zones)


def test_creer_admet_un_jeu_non_contigu() -> None:
    """RG-8 : l'app **n'impose pas** la conformité au règlement.

    Un jeu troué n'existe sur aucun blason FFTA, mais l'interdire reviendrait à vérifier la
    conformité — ce que RG-8 exclut. Le CA veut restreindre la saisie, pas normer le carton.
    """
    blason = Blason.creer(1, "Exotique", 0.5, 1, zones=["10", "8", "M"])
    assert blason.zones == ("10", "8", "M")


def test_modifier_met_a_jour_les_zones() -> None:
    """CA « modifiable comme le reste du blason » (RG-8) : les zones s'éditent comme le nom."""
    blason = Blason.creer(1, "Trispot 40", 0.5, 3)
    modifie = blason.modifier("Trispot 40", 0.5, 3, zones=["10", "9", "8", "7", "6", "M"])
    assert modifie.zones == ("10", "9", "8", "7", "6", "M")


def test_modifier_valide_les_zones() -> None:
    """`modifier` applique les mêmes règles de zones que `creer`."""
    blason = Blason.creer(1, "Blason", 0.5, 2)
    with pytest.raises(ZonesBlasonInvalides):
        blason.modifier("Blason", 0.5, 2, zones=["10", "9"])


def test_zones_defaut_n_est_pas_alias_du_vocabulaire() -> None:
    """Fil-piège : `ZONES_DEFAUT` est énuméré à part du vocabulaire.

    ⚠️ **Si vous ajoutez une zone à `ZoneScore`** (X, pour le départage FFTA d'EPIC-06), c'est
    l'égalité ci-dessous qui doit **sauter** — et vous devez la corriger *ici*, pas « réparer »
    `ZONES_DEFAUT` en le réalignant : une zone ajoutée au vocabulaire ne doit pas entrer en
    silence dans le défaut de tous les blasons, ni se désaligner du littéral gelé de la migration
    `0019`. C'est tout l'objet de la séparation.
    """
    assert ZONES_DEFAUT == ZONES_CANONIQUES, "les deux coïncident aujourd'hui"
    assert ZONES_DEFAUT is not ZONES_CANONIQUES, "mais ne sont pas le même objet"


def test_creer_refuse_une_chaine_en_guise_de_zones() -> None:
    """`str` est un `Iterable[str]` : `zones="1M"` doit échouer, pas se lire ('1', 'M')."""
    with pytest.raises(ZonesBlasonInvalides):
        Blason.creer(1, "Blason", 0.5, 1, zones="1M")


def test_creer_sans_zones_marquantes_le_dit() -> None:
    """`zones=[]` parle de zone marquante, pas d'un « M » que l'admin n'a jamais retiré."""
    with pytest.raises(ZonesBlasonInvalides, match="marquante"):
        Blason.creer(1, "Blason", 0.5, 1, zones=[])


def test_creer_sans_manque_le_dit() -> None:
    """Retirer `M` d'un jeu par ailleurs valide donne bien le message sur le manqué."""
    with pytest.raises(ZonesBlasonInvalides, match="manqué"):
        Blason.creer(1, "Blason", 0.5, 1, zones=["10", "9"])


def test_les_zones_sont_des_zones_de_score() -> None:
    """Le domaine porte l'énuméré, pas des chaînes libres — une chaîne saisie est convertie."""
    blason = Blason.creer(1, "Trispot 40", 0.5, 3, zones=["10", "9", "8", "7", "6", "M"])
    assert all(isinstance(zone, ZoneScore) for zone in blason.zones)
    assert blason.zones[0] is ZoneScore.DIX
    assert blason.zones[-1] is ZoneScore.MANQUE


def test_creer_refuse_des_zones_non_textuelles() -> None:
    """Un script qui enverrait les entiers JSON `[10, 9]` est refusé, pas coercé en silence.

    Le message nomme le **type** : sans lui, « 10 est inconnue, valeurs admises : 10, 9… » serait
    vrai mais incompréhensible pour l'auteur du script.
    """
    with pytest.raises(ZonesBlasonInvalides, match="type int"):
        Blason.creer(1, "Blason", 0.5, 1, zones=[10, 9, "M"])  # type: ignore[list-item]


def test_le_message_borne_l_echo_de_l_entree() -> None:
    """Le client choisit ce qu'il envoie, pas la taille du message qu'il récupère.

    La troncature porte sur la **valeur** puis représente : tronquer `repr()` couperait au milieu
    du littéral et laisserait un guillemet orphelin.
    """
    with pytest.raises(ZonesBlasonInvalides) as capture:
        Blason.creer(1, "Blason", 0.5, 1, zones=["A" * 5_000, "M"])
    message = str(capture.value)
    assert "A" * 20 in message
    assert "A" * 21 not in message
    assert "…" in message


@pytest.mark.parametrize("zones", [None, 42, True, object()])
def test_valider_zones_refuse_un_non_iterable_en_erreur_typee(zones: object) -> None:
    """`valider_zones` est **publique** pour les appelants internes (import, script, relecture) :
    elle leur doit une erreur de domaine typée (règle 5), pas un `TypeError` nu venu de ses
    entrailles.

    Appelée directement, et non via `creer` : là, `None` est la sentinelle « applique le défaut ».
    """
    with pytest.raises(ZonesBlasonInvalides):
        valider_zones(zones)  # type: ignore[arg-type]


def test_le_message_ne_leve_pas_sur_une_valeur_irrepresentable() -> None:
    """Construire un message d'erreur ne doit jamais masquer l'erreur d'origine.

    `repr()` d'un entier gigantesque lève `ValueError` (limite de conversion int → str) — et il
    le lèverait **à l'intérieur** du `except` qui formate le message.
    """
    with pytest.raises(ZonesBlasonInvalides):
        Blason.creer(1, "Blason", 0.5, 1, zones=[10**10_000, "M"])  # type: ignore[list-item]
