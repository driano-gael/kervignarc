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
élimination directe : les rangs **1 à 5** y sortent d'une **Grande Finale en Big Shoot Off** à
**cinq** archers — les 4 vainqueurs du 8ᵉ tour (M305-M308) et un « **Lucky-Looser** » —, tirée sur
les postes 6 à 10 (onglet « TABLEAU 1 OK », colonnes « GRANDE FINALE » ; l'échelle 5→4→3→2 des
colonnes suivantes montre l'élimination du plus faible à chaque manche). Le Big Shoot Off est un
**type de phase** d'E05US015, et cette alimentation à deux provenances est justement le cas d'usage
réel du CA « sources multiples ». L'oracle porte donc sur les rangs **6 à 120** et laisse le sommet
à E05US015 : le classeur ne contient tout simplement pas de finale d'élimination à comparer.

⚠️ **Le format du club repêche, le moteur livré non.** Le « Lucky-Looser » est le **gagnant de
M427** — le meilleur des battus —, qui remonte disputer le titre au lieu de prendre le rang 5. C'est
pourquoi M427 ne décerne qu'**un** rang (le 6, à son perdant) et pourquoi le classeur compte 115
rangs terminaux et non 116. Le moteur, lui, fait un placement *pur* : chez lui M427 décerne (5, 6).
Les deux formats divergent donc **par construction** au-dessus du rang 6 — d'où le seuil de
comparaison.

*(Ces faits ont été **corrigés en revue** : un premier jet de cette US lisait les postes de tir
« 6…10 » comme un compte d'archers et annonçait « un BSO à dix archers, rangs 1 à 10 »,
puis fabriquait la paire (5, 6) que la source ne donne pas. L'arbitrage faux était déjà reversé dans
la story — donc en route vers E05US015, qui en aurait dérivé ses tests.)*
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
from domain.tableau import Exempt, PerdantDe, Tableau, TeteDeSerie, construire_tableau

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
    son rang de départ).

    ⚠️ **Ne pas surestimer ce qu'il prouve.** Ce déroulé éprouve la **partition** des rangs (chaque
    archer atterrit dans la bonne plage), *pas* les appariements : le classement identité est
    invariant par toute permutation des entrants d'un même groupe, donc permuter le câblage de
    descente ne le fait pas broncher. C'est
    `test_la_cascade_apparie_les_perdants_comme_le_classeur` qui couvre ce volet — les deux sont
    nécessaires.
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
    """Les paires `(gagnant, perdant)` **complètes** que le classeur fait sortir d'un terminal.

    Reconstituées depuis la table `rang → (issue, match)` : deux rangs partageant le même match
    terminal en forment la paire. Un match dont **un seul** côté est classé est écarté — il en
    existe exactement un, `M427`, et ce n'est pas une lacune d'étiquetage : voir
    `test_un_seul_match_terminal_du_classeur_ne_classe_qu_un_cote`.
    """
    par_match: dict[int, dict[str, int]] = {}
    for rang, (issue, numero) in FIXTURE["rangs_terminaux"].items():
        par_match.setdefault(numero, {})[issue] = int(rang)
    return {
        (issues["gagnant"], issues["perdant"])
        for issues in par_match.values()
        if "gagnant" in issues and "perdant" in issues
    }


def test_un_seul_match_terminal_du_classeur_ne_classe_qu_un_cote() -> None:
    """Le sommet du format du club **repêche** — et c'est la clé de lecture de tout cet oracle.

    Le classeur étiquette les rangs **6 à 120**, jamais 1 à 5. L'arithmétique le confirme : 5 rangs
    au Big Shoot Off + 115 au placement = 120, alors que 58 matchs terminaux qui classeraient deux
    archers chacun en feraient 116. Il y a donc **un** match terminal qui ne décerne qu'un rang :
    `M427`, le terminal du sous-tableau le plus haut. Son **perdant** prend le rang 6 ; son
    **gagnant** — le meilleur des battus — n'est pas classé là, il est **repêché** en Grande Finale,
    et c'est lui le « Lucky-Looser » de l'onglet.

    Ce test verrouille cette lecture parce qu'un premier jet de l'oracle avait **fabriqué** la paire
    `(5, 6)` en supposant une étiquette manquante — masquant du même coup le seul endroit où le
    format du club fait revenir un battu disputer le titre.
    """
    par_match: dict[int, set[str]] = {}
    for _rang, (issue, numero) in FIXTURE["rangs_terminaux"].items():
        par_match.setdefault(numero, set()).add(issue)
    incomplets = {numero for numero, issues in par_match.items() if len(issues) == 1}
    assert incomplets == {427}
    assert FIXTURE["rangs_terminaux"]["6"] == ["perdant", 427]
    assert "5" not in FIXTURE["rangs_terminaux"]


def test_le_moteur_produit_les_memes_matchs_terminaux_que_le_classeur(tableau_120: Tableau) -> None:
    """CA « rangs terminaux » : les paires (7,8) … (119,120), une par match terminal du classeur.

    **Périmètre de la comparaison, et pourquoi il s'arrête au rang 7.** Le moteur livré fait un
    placement *pur* : il classe 1→120 par élimination, sans jamais repêcher. Le format du club, lui,
    coiffe son tableau d'un Big Shoot Off à 5 archers (4 vainqueurs des quarts + 1 repêché) qui
    décerne les rangs 1 à 5. Les deux formats ne peuvent donc **pas** coïncider au-dessus du rang 6,
    et ce n'est pas un défaut du moteur : c'est un type de phase qu'E05US015 livrera.

    Restent 57 paires strictement comparables — et elles doivent l'être exactement.
    """
    attendues = _paires_terminales_du_classeur()
    obtenues = {
        m.place_en_jeu for m in tableau_120.matchs if m.place_en_jeu and m.place_en_jeu[0] >= 7
    }
    assert obtenues == attendues
    assert len(attendues) == 57  # M428 → M484 ; M427 ne classe que son perdant


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


def test_la_cascade_apparie_les_perdants_comme_le_classeur(tableau_120: Tableau) -> None:
    """*Règle R* comparée au **câblage réel** : qui retrouve qui dans le tableau de placement.

    ⚠️ **C'est l'assertion qui donne sa valeur à l'oracle**, et elle a failli manquer. Les autres
    tests de ce fichier vérifient la **partition** des rangs (qui finit dans quelle plage) ; aucun
    ne vérifiait les **appariements** à l'intérieur d'une plage. Or, quand le mieux classé gagne
    toujours, le classement final est invariant par toute permutation des entrants d'un groupe : un
    relecteur adversarial l'a démontré en mutant `entrants[::-1]`, `gagnants[::-1]` et une rotation
    — **les trois mutants survivaient** à la suite complète. L'oracle affirmait pourtant que « la
    moindre erreur de routage déplace au moins un rang ». C'était faux.

    La comparaison est **indépendante de la numérotation** (avertissement de `politiques.py`) :
    chaque match du premier tour est identifié par l'**ensemble de ses rangs d'ensemencement**, et
    l'on compare les paires de matchs amont qui se retrouvent dans chaque match de placement.
    """
    par_rangs_du_classeur = {
        numero: frozenset(rang for rang in paire if rang is not None)
        for numero, paire in enumerate(FIXTURE["premier_tour"], start=1)
    }
    attendu = {
        frozenset(par_rangs_du_classeur[amont] for amont in descente)
        for descente in FIXTURE["descentes_premier_niveau"]
    }

    rangs_du_match = {
        m.numero: frozenset(
            source.rang
            for source in (m.source_haut, m.source_bas)
            if isinstance(source, TeteDeSerie)
        )
        for m in tableau_120.matchs
        if m.tour == 1
    }
    obtenu = set()
    for m in tableau_120.matchs:
        amonts = [
            source.numero
            for source in (m.source_haut, m.source_bas)
            if isinstance(source, PerdantDe) and source.numero in rangs_du_match
        ]
        if amonts:
            obtenu.add(frozenset(rangs_du_match[numero] for numero in amonts))

    assert obtenu == attendu


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
    assert tableau_deroule.est_termine


def test_le_nombre_de_matchs_diverge_de_celui_du_classeur_et_c_est_documente(
    tableau_120: Tableau,
) -> None:
    """⚠️ Le moteur produit **436** matchs, le classeur en compte **484**. L'écart est réel.

    Ce test ne prétend pas les égaler : il **fige les deux nombres** pour que l'écart ne se découvre
    pas une seconde fois, et pour qu'une dérive du moteur (436 qui bouge) se voie immédiatement.
    Décomposition mesurée le 31/07/2026 :

    | | classeur | moteur | écart |
    |---|---|---|---|
    | tableau principal | 124 (5 niveaux, s'arrete aux quarts) | 127 (7 niveaux) | **-3** |
    | placement | 360 | 309 | **+51** |

    - Les **-3** s'expliquent : le classeur remplace demi-finales et finale par la **Grande Finale
      en Big Shoot Off**, qui ne porte pas d'étiquette `M`.
    - Sur les **+51**, **12** s'expliquent par l'élagage du sous-tableau des rangs 121-128, que le
      moteur n'engendre pas (aucun rang réel à y décerner) et que le classeur matérialise. **Les 39
      restants ne sont pas expliqués** : une cascade pure de 128 places compte 448 matchs, le
      classeur en aligne 39 de plus. L'hypothèse la plus probable est la présence de tableaux de
      **consolation** supplémentaires (« LUCKY LOSER 1 » de l'onglet PLAN), qui ne relèvent pas de
      la division par deux formalisée au § 4.

    C'est une divergence entre le **classeur réel** et sa formalisation
    (`moteur-placement-lucky-loser.md`, qui annonce 484 matchs *et* décrit une cascade pure) : elle
    est **antérieure** à cette US et l'excède. Matière pour E05US015, consignée dans la story.
    """
    assert len(tableau_120.matchs) == 436
    assert FIXTURE["matchs_du_classeur"] == 484
