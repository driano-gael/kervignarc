"""Tests de la **colline** — King of the Hill et Ladder (E05US015).

**Dérivés du CA** (règle 9) : les règles données par le commanditaire le 31/07/2026 (référentiel
§10.1) et les deux arbitrages du cadrage — version **journée** (et non classement permanent de
club), mécanique **« deux voisins s'affrontent »** pour le King of the Hill.

⚠️ Un test consigne l'**écart** entre la règle du Ladder et son exemple chiffré : le module applique
la règle, pas l'exemple. Le test le dit explicitement pour que la recette tranche.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from domain.colline import (
    ConfigurationColline,
    DefiColline,
    IssueDefi,
    appliquer_manche,
    classement_colline,
    defis_de_la_manche,
)
from domain.erreurs import ConfigurationCollineInvalide
from domain.participant import Participant


def colline(nombre: int) -> tuple[Participant, ...]:
    """Colline initiale : l'ordre du **classement source** (position 1 = premier)."""
    return tuple(Participant.individuel(rang) for rang in range(1, nombre + 1))


def positions(defis: Sequence[DefiColline]) -> list[tuple[int, int]]:
    return [(d.position_haute, d.position_basse) for d in defis]


# --- la portée de défi **est** ce qui sépare les deux formats -------------------------------------


def test_king_of_the_hill_defie_le_voisin_immediat() -> None:
    assert ConfigurationColline.king_of_the_hill(nb_manches=3).portee_de_defi == 1


def test_ladder_defie_a_deux_rangs() -> None:
    """« Le n°6 peut seulement défier le 5 ou le 4 » : la portée encadre le défi."""
    assert ConfigurationColline.ladder(nb_manches=3).portee_de_defi == 2


def test_une_portee_qui_couvre_toute_la_colline_est_refusee() -> None:
    """Défier n'importe qui n'est plus ni un King of the Hill ni un Ladder."""
    with pytest.raises(ConfigurationCollineInvalide):
        defis_de_la_manche(colline(3), 1, ConfigurationColline(nb_manches=1, portee_de_defi=3))


# --- « chaque manche oppose deux voisins » -------------------------------------------------------


def test_les_defis_d_une_manche_ne_se_recouvrent_jamais() -> None:
    """Condition pour que l'ordre d'application des issues n'ait aucune importance — et pour que la
    manche puisse se tirer en parallèle sur plusieurs cibles."""
    configuration = ConfigurationColline.king_of_the_hill(nb_manches=4)
    for manche in range(1, 5):
        engagees = [
            position
            for defi in defis_de_la_manche(colline(8), manche, configuration)
            for position in (defi.position_haute, defi.position_basse)
        ]
        assert len(engagees) == len(set(engagees))


def test_le_decoupage_tourne_d_une_manche_a_l_autre() -> None:
    """Sans rotation, les mêmes paires s'affronteraient éternellement et la colline se figerait
    après une manche. Manche 1 → (1,2)(3,4)… ; manche 2 → (2,3)(4,5)…"""
    configuration = ConfigurationColline.king_of_the_hill(nb_manches=2)
    assert positions(defis_de_la_manche(colline(6), 1, configuration)) == [(1, 2), (3, 4), (5, 6)]
    assert positions(defis_de_la_manche(colline(6), 2, configuration)) == [(2, 3), (4, 5)]


def test_les_extremites_se_reposent_une_manche_sur_deux() -> None:
    """Inévitable à portée 1, et sans effet : elles rejouent la manche suivante."""
    configuration = ConfigurationColline.king_of_the_hill(nb_manches=2)
    defis = defis_de_la_manche(colline(6), 2, configuration)
    engagees = {p for defi in defis for p in (defi.position_haute, defi.position_basse)}
    assert 1 not in engagees and 6 not in engagees


# --- « le gagnant monte, le perdant descend » ----------------------------------------------------


def test_le_challenger_vainqueur_prend_la_position_du_defie() -> None:
    depart = colline(4)
    configuration = ConfigurationColline.king_of_the_hill(nb_manches=1)
    defis = defis_de_la_manche(depart, 1, configuration)
    # Le challenger de (1,2) gagne : les positions 1 et 2 s'échangent.
    issues = [IssueDefi(defi=defis[0], vainqueur=defis[0].challenger)]
    apres = appliquer_manche(depart, issues)
    assert [p.ref_id for p in apres] == [2, 1, 3, 4]


def test_le_defie_vainqueur_reste_en_place() -> None:
    depart = colline(4)
    configuration = ConfigurationColline.king_of_the_hill(nb_manches=1)
    defis = defis_de_la_manche(depart, 1, configuration)
    issues = [IssueDefi(defi=defi, vainqueur=defi.defie) for defi in defis]
    assert appliquer_manche(depart, issues) == depart


def test_les_meilleurs_remontent_naturellement() -> None:
    """« Après plusieurs manches, les meilleurs remontent naturellement » (règle du commanditaire).

    On part d'une colline **inversée** (le plus fort en dernière position) et on fait gagner
    systématiquement l'archer de plus petit `ref_id`. La colline doit se remettre à l'endroit.
    """
    depart = tuple(Participant.individuel(rang) for rang in range(6, 0, -1))
    configuration = ConfigurationColline.king_of_the_hill(nb_manches=10)
    courante = depart
    for manche in range(1, 11):
        defis = defis_de_la_manche(courante, manche, configuration)
        issues = [
            IssueDefi(
                defi=defi,
                vainqueur=min(defi.defie, defi.challenger, key=lambda p: p.ref_id),
            )
            for defi in defis
        ]
        courante = appliquer_manche(courante, issues)
    assert [p.ref_id for p in courante] == [1, 2, 3, 4, 5, 6]


# --- l'écart entre la règle du Ladder et son exemple chiffré -------------------------------------


def test_le_ladder_applique_la_regle_et_non_son_exemple() -> None:
    """⚠️ **Écart consigné, à confirmer à la recette.**

    L'exemple fourni part de `1 2 3 4 5 6 7 8`, fait gagner le n°6 contre le n°4, et donne
    `1 2 3 5 6 4 7 8` — soit le n°6 en **5ᵉ** position. La règle, elle, dit « le gagnant monte, le
    perdant descend » : gagner contre le n°4 mène à la **4ᵉ** position. Le moteur applique la règle
    (échange des deux positions), donc `1 2 3 6 5 4 7 8`.

    Ce test **fige l'arbitrage** plutôt que de le laisser implicite : s'il tombe un jour, c'est que
    quelqu'un aura suivi l'exemple, et il faudra que ce soit une décision, pas un glissement.
    """
    depart = colline(8)
    configuration = ConfigurationColline.ladder(nb_manches=1)
    defis = defis_de_la_manche(depart, 1, configuration)
    defi_4_6 = next(d for d in defis if (d.position_haute, d.position_basse) == (4, 6))
    apres = appliquer_manche(depart, [IssueDefi(defi=defi_4_6, vainqueur=defi_4_6.challenger)])
    assert [p.ref_id for p in apres] == [1, 2, 3, 6, 5, 4, 7, 8]


# --- classement final ----------------------------------------------------------------------------


def test_le_classement_est_la_colline_elle_meme() -> None:
    """Ce qui rend le format lisible pour le public : le classement est visible à tout instant, il
    n'a pas à être calculé en fin de phase. Et aucun ex æquo n'est possible."""
    a, b, c = colline(3)
    assert classement_colline((c, a, b)) == ((c, 1), (a, 2), (b, 3))


# --- garde-fous ----------------------------------------------------------------------------------


def test_zero_manche_est_refuse() -> None:
    with pytest.raises(ConfigurationCollineInvalide):
        ConfigurationColline(nb_manches=0)


def test_une_manche_hors_du_format_est_refusee() -> None:
    configuration = ConfigurationColline.king_of_the_hill(nb_manches=2)
    with pytest.raises(ConfigurationCollineInvalide):
        defis_de_la_manche(colline(4), 3, configuration)


def test_un_vainqueur_etranger_au_defi_est_refuse() -> None:
    depart = colline(4)
    configuration = ConfigurationColline.king_of_the_hill(nb_manches=1)
    defi = defis_de_la_manche(depart, 1, configuration)[0]
    with pytest.raises(ConfigurationCollineInvalide):
        appliquer_manche(depart, [IssueDefi(defi=defi, vainqueur=Participant.individuel(99))])
