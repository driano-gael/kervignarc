"""**L'oracle 120** — le moteur de placement rejoue le tournoi réel de `Tableaux.xlsx` (E05US010).

Règle 9 : « L'oracle 120 doit rester vert ». Ce fichier est ce test — il n'existait pas avant cette
US, alors que la doctrine le citait déjà partout : la clause était **écrite mais pas outillée**.
E05US018 (« Oracle 120 ») a été absorbée par E05US010 le 31/07/2026, précisément pour qu'un moteur
de placement ne puisse pas être livré sans sa preuve (risque R1 du cahier des charges technique).

**Ce que compare l'oracle.** La fixture `donnees/oracle_120.json` est extraite du classeur par
`docs/sources/extraire_tableaux_xlsx.py` (voir sa docstring pour le « pourquoi une fixture »). On
compare des **structures** — appariements, byes, paires de rangs terminaux — et **jamais des numéros
de match** : `politiques.py` prévient que la numérotation du classeur (M1…M484) ne correspond pas à
celle qu'engendre le seeding serpent, faute de table de correspondance. Comparer des numéros
donnerait un test rouge sur un moteur juste.

**Ce que l'oracle ne peut pas couvrir, et pourquoi.** Le sommet du classeur n'est **pas** une
élimination directe : les rangs 1 à 10 y sortent d'une **Grande Finale en Big Shoot Off** alimentée
par les vainqueurs des quarts *et* un « Lucky-Looser » (onglet « TABLEAU 1 OK », colonnes
« GRANDE FINALE »). Le Big Shoot Off est un **type de phase** d'E05US015, et cette alimentation à
deux provenances est justement le cas d'usage réel du CA « sources multiples ». L'oracle porte donc
sur les rangs **5 à 120** — les 58 matchs terminaux M427-M484 — et laisse le sommet à E05US015. Ce
n'est pas une facilité : le classeur ne contient tout simplement pas de finale d'élimination directe
à comparer. *(Constat fait à l'extraction du 31/07/2026 ; consigné dans la story.)*
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from domain.participant import Participant
from domain.politiques import (
    ByesAuxMieuxClasses,
    PlacementEnCascade,
    ProfondeurUnVersN,
    SeedingSerpent,
)
from domain.tableau import Exempt, Tableau, TeteDeSerie, construire_tableau

FIXTURE = json.loads(
    (Path(__file__).parent / "donnees" / "oracle_120.json").read_text(encoding="utf8")
)
EFFECTIF = FIXTURE["effectif"]


@pytest.fixture(scope="module")
def tableau_120() -> Tableau:
    """Le tableau de placement intégral pour 120 archers classés 1..120."""
    return construire_tableau(
        [Participant.individuel(rang) for rang in range(1, EFFECTIF + 1)],
        seeding=SeedingSerpent(),
        byes=ByesAuxMieuxClasses(),
        routing=PlacementEnCascade(),
        depth=ProfondeurUnVersN(),
    )


@pytest.fixture(scope="module")
def tableau_deroule(tableau_120: Tableau) -> Tableau:
    """Le même tableau, joué de bout en bout en faisant gagner systématiquement le mieux classé.

    Déroulé « sans surprise » : il rend le classement final entièrement prédictible (chacun finit à
    son rang de départ), donc **discriminant** — la moindre erreur de routage ou de division de
    plage déplace au moins un rang parmi 120.
    """
    courant = tableau_120
    encore = True
    while encore:
        encore = False
        for m in courant.matchs:
            if m.est_jouable and m.haut is not None and m.bas is not None:
                courant = courant.jouer(m.numero, m.haut if m.haut.ref_id < m.bas.ref_id else m.bas)
                encore = True
                break
    return courant


# --- l'arbre : dimensionnement, ensemencement, byes (onglet « TABLEAU 1 OK ») --------------------


def test_le_tableau_est_dimensionne_comme_le_classeur(tableau_120: Tableau) -> None:
    """120 archers ⇒ 128 places, 8 exempts (§ 2 du document de formalisation)."""
    assert tableau_120.effectif == EFFECTIF
    assert tableau_120.taille == FIXTURE["taille"]


def test_les_appariements_du_premier_tour_sont_ceux_du_classeur(tableau_120: Tableau) -> None:
    """Le seeding serpent doit reproduire, à l'ensemble près, les 64 matchs du tournoi réel.

    On compare des **paires de rangs non ordonnées** : le classeur écrit tantôt « 65 vs 64 », tantôt
    « 97 vs 32 » — le camp haut/bas relève de la mise en page, pas de la structure.
    """
    attendus = {
        frozenset(rang for rang in paire if rang is not None) for paire in FIXTURE["premier_tour"]
    }
    obtenus = {
        frozenset(
            source.rang
            for source in (m.source_haut, m.source_bas)
            if isinstance(source, TeteDeSerie)
        )
        for m in tableau_120.matchs
        if m.tour == 1
    }
    assert obtenus == attendus


def test_les_exempts_sont_les_huit_tetes_de_serie(tableau_120: Tableau) -> None:
    """§ 2 : « 8 exempts attribués aux 8 têtes de série » — vérifié contre le classeur."""
    attendus = {paire[0] for paire in FIXTURE["premier_tour"] if paire[1] is None}
    obtenus = {
        source.rang
        for m in tableau_120.matchs
        if m.tour == 1 and m.est_bye
        for source in (m.source_haut, m.source_bas)
        if isinstance(source, TeteDeSerie)
    }
    assert obtenus == attendus == set(range(1, 9))


def test_aucun_match_du_premier_tour_n_oppose_deux_exempts(tableau_120: Tableau) -> None:
    """L'arrondi à la puissance de 2 *supérieure* garantit qu'un match a toujours un tireur réel."""
    for m in tableau_120.matchs:
        if m.tour == 1:
            assert not (isinstance(m.source_haut, Exempt) and isinstance(m.source_bas, Exempt))


# --- la cascade : matchs terminaux et Règle T (onglet « TABLEAU 2 OK ») --------------------------


def _paires_terminales_du_classeur() -> set[tuple[int, int]]:
    """Les paires de rangs `(gagnant, perdant)` que le classeur fait sortir d'un match terminal.

    Reconstituées depuis la table `rang → (issue, match)` : deux rangs partageant le même match
    terminal en forment la paire. Deux rangs de la table (5 et 38) n'ont pas d'étiquette lisible
    dans le classeur — leur **paire** reste néanmoins déduite de leur jumeau, puisque celui-ci
    nomme le match.
    """
    par_match: dict[int, dict[str, int]] = {}
    for rang, (issue, numero) in FIXTURE["rangs_terminaux"].items():
        par_match.setdefault(numero, {})[issue] = int(rang)
    paires: set[tuple[int, int]] = set()
    for issues in par_match.values():
        if "gagnant" in issues and "perdant" in issues:
            paires.add((issues["gagnant"], issues["perdant"]))
        elif "perdant" in issues:  # rang 5 : seul le perdant (6) est étiqueté
            paires.add((issues["perdant"] - 1, issues["perdant"]))
        else:
            paires.add((issues["gagnant"], issues["gagnant"] + 1))
    return paires


def test_le_moteur_produit_les_memes_matchs_terminaux_que_le_classeur(tableau_120: Tableau) -> None:
    """CA « rangs terminaux » : les paires (5,6) … (119,120) du classeur, une par match terminal.

    Les rangs 1 à 4 sont exclus de la comparaison : le classeur les fait sortir du Big Shoot Off
    (E05US015), pas d'un match terminal d'élimination.
    """
    attendues = _paires_terminales_du_classeur()
    obtenues = {
        m.place_en_jeu for m in tableau_120.matchs if m.place_en_jeu and m.place_en_jeu[0] >= 5
    }
    assert obtenues == attendues
    assert len(attendues) == 58  # M427 → M484, § 3 du document de formalisation


def test_la_regle_t_du_classeur_est_bien_gagnant_impair_perdant_pair() -> None:
    """*Règle T* lue **dans les données** : rang impair = gagnant, rang pair = perdant du terminal.

    Contrôle de la fixture elle-même (et donc de l'extraction) : si cette assertion tombe, c'est
    l'oracle qu'il faut regarder avant le moteur.
    """
    for rang, (issue, _numero) in FIXTURE["rangs_terminaux"].items():
        attendue = "gagnant" if int(rang) % 2 == 1 else "perdant"
        assert issue == attendue, f"rang {rang} : le classeur dit {issue}"


def test_chaque_rang_de_5_a_120_est_decide_par_un_match_terminal_unique(
    tableau_120: Tableau,
) -> None:
    """§ 3 : « chaque rang de 5 à 120 est décidé par un match terminal unique »."""
    decides = [rang for m in tableau_120.matchs if m.place_en_jeu for rang in m.place_en_jeu]
    assert sorted(rang for rang in decides if rang >= 5) == list(range(5, EFFECTIF + 1))


def test_personne_n_est_elimine(tableau_120: Tableau) -> None:
    """§ 1 : « Personne n'est éliminé » — tout perdant d'un match non terminal a un match aval."""
    for m in tableau_120.matchs:
        if m.est_bye or (m.plage is not None and m.plage.est_terminale):
            continue
        assert (
            tableau_120.match_aval_du_perdant(m.numero) is not None
        ), f"le perdant du match {m.numero} (plage {m.plage}) n'est routé nulle part"


# --- le classement : placement intégral 1→120 ---------------------------------------------------


def test_le_tournoi_se_deroule_jusqu_a_un_classement_complet(tableau_deroule: Tableau) -> None:
    """CA « oracle 120 » : le moteur classe les 120 archers, sans trou ni doublon."""
    classement = tableau_deroule.classement()
    assert [place.rang for place in classement] == list(range(1, EFFECTIF + 1))


def test_le_classement_sans_surprise_rend_l_ordre_d_ensemencement(
    tableau_deroule: Tableau,
) -> None:
    """Chaque archer finit à son rang de qualification quand le mieux classé gagne toujours.

    C'est l'assertion la plus forte du fichier : elle éprouve d'un coup le seeding, les byes, la
    *Règle R* (à chaque défaite, la moitié basse) et la *Règle T* sur 120 rangs.
    """
    attendu = [Participant.individuel(rang) for rang in range(1, EFFECTIF + 1)]
    assert [place.participant for place in tableau_deroule.classement()] == attendu


def test_aucun_match_ne_reste_en_suspens(tableau_deroule: Tableau) -> None:
    """Un tableau entièrement déroulé n'a plus de match jouable : la cascade se termine."""
    assert [m.numero for m in tableau_deroule.matchs if m.est_jouable] == []
