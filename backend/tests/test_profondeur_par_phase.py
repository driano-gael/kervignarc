"""La profondeur lue **sur la phase** par les services de tableau (E06US006, ADR-0070).

Ces tests comblent le trou mesuré en revue adversariale : `profondeur_de` n'avait **aucun** test
direct, et neutraliser son appel dans `ServicePlacementDuels` laissait la suite entièrement verte.

⚠️ **Ce que ce fichier a appris, et que l'ADR affirmait à tort.** La revue attribuait ce trou à un
défaut de couverture ; la mesure dit autre chose. Sous `PlacementEnCascade`, les **paires du premier
tour sont identiques** quelle que soit la profondeur (vérifié : `top_n(4)` et `un_vers_n` sur 8
participants rendent `[(1,8), (4,5), (2,7), (3,6)]`), et `ServicePlacementDuels` ne consomme **que**
ce premier tour. Sa sortie est donc **structurellement insensible** à la profondeur aujourd'hui :
aucun test ne peut distinguer une profondeur juste d'une profondeur fausse de ce côté-là, parce
qu'il n'y a rien à distinguer.

Écrire malgré tout un test « les deux services s'accordent » aurait produit un **test décoratif** :
vert quoi qu'il arrive, donnant l'illusion d'un garde-fou. On teste donc ce qui est réellement
observable — la profondeur honorée de bout en bout par le service qui joue l'arbre — et l'on dit
ici ce que la lecture partagée achète vraiment : non pas une divergence évitée aujourd'hui, mais la
garantie qu'elle ne naîtra pas le jour où le plan couvrira les tours suivants.
"""

from __future__ import annotations

import pytest

from application.prelevement import profondeur_de
from domain.phase import Phase, TypePhase
from domain.politiques import (
    ProfondeurClassement,
    ProfondeurPodium,
    ProfondeurUnVersN,
    registre_par_defaut,
)
from tests.test_service_routage import _Monde

_QUATRE_SCORES = (
    ("10", "10", "10"),
    ("10", "10", "9"),
    ("10", "9", "9"),
    ("9", "9", "9"),
)
_HUIT_SCORES = (
    *_QUATRE_SCORES,
    ("9", "9", "8"),
    ("9", "8", "8"),
    ("8", "8", "8"),
    ("8", "8", "7"),
)


# --- `profondeur_de` : la lecture partagée par les deux services ---------------------------------


def test_une_phase_reglee_rend_la_politique_quelle_declare() -> None:
    registre = registre_par_defaut()
    phase = Phase.creer(
        1,
        ordre=2,
        type=TypePhase.ELIMINATION_DIRECTE,
        profondeur=ProfondeurClassement.integrale(),
    )
    assert profondeur_de(phase, registre) == ProfondeurUnVersN()


def test_une_phase_non_reglee_rend_le_preset_de_son_type() -> None:
    """Le cœur de la rétro-compatibilité d'ADR-0070 : sans réglage, on rejoue ce qui se jouait."""
    registre = registre_par_defaut()
    phase = Phase.creer(1, ordre=2, type=TypePhase.ELIMINATION_DIRECTE)
    assert profondeur_de(phase, registre) == ProfondeurPodium(jusqu_au=4)


def test_un_placement_non_regle_classe_tout_le_monde() -> None:
    """L'asymétrie voulue (ADR-0070 §3) : le type `placement` n'a **pas** d'existant à préserver,
    et son intitulé promet à l'organisateur qu'il classe du 1ᵉʳ au dernier."""
    registre = registre_par_defaut()
    phase = Phase.creer(1, ordre=2, type=TypePhase.PLACEMENT)
    assert profondeur_de(phase, registre) == ProfondeurUnVersN()


def test_un_top_n_rend_la_profondeur_parametree() -> None:
    registre = registre_par_defaut()
    phase = Phase.creer(
        1, ordre=2, type=TypePhase.ELIMINATION_DIRECTE, profondeur=ProfondeurClassement.top(8)
    )
    assert profondeur_de(phase, registre) == ProfondeurPodium(jusqu_au=8)


# --- de bout en bout : le service qui joue l'arbre honore la phase --------------------------------


def _monde(profondeur: ProfondeurClassement | None, scores: tuple[tuple[str, ...], ...]) -> _Monde:
    monde = _Monde(profondeur=profondeur)
    for valeurs in scores:
        monde.inscrire_classe(valeurs)
    monde.creer_phase_tableau()
    return monde


@pytest.mark.parametrize(
    ("profondeur", "matchs_attendus"),
    [
        # `None` = phase **réellement non réglée**, donc repli sur le preset du type : c'est le
        # cœur d'ADR-0070 §3, et l'étiqueter sans l'exercer était un faux témoignage (relevé en
        # 2ᵉ passe — le décor posait un `top_n(4)` explicite).
        (None, 8),
        (ProfondeurClassement.top(2), 7),  # finale seule, aucune petite finale
        (ProfondeurClassement.integrale(), 12),  # un match par rang : 8/2 fois log2(8)
    ],
)
def test_le_tableau_joue_a_la_profondeur_declaree_par_la_phase(
    profondeur: ProfondeurClassement | None, matchs_attendus: int
) -> None:
    """La profondeur réglée sur la phase change le **nombre de matchs à tirer**, de bout en bout.

    C'est la seule assertion de service que la profondeur rend réellement discriminante — et c'est
    la charge de la journée qu'elle mesure : à 8 archers, un classement intégral fait tirer 12 duels
    là où le podium en fait tirer 8.
    """
    monde = _monde(profondeur, _HUIT_SCORES)
    tableau, _ = monde.saisie.reconstruire(monde.tournoi_id, monde.phase_id or 0)
    assert len(tableau.matchs) == matchs_attendus


def test_le_plan_de_cibles_reste_le_meme_a_toute_profondeur() -> None:
    """Test de **caractérisation** : il fige ce qui est vrai aujourd'hui, pas ce qu'on souhaite.

    Le plan ne pose que les duellistes du **premier tour**, et celui-ci ne dépend pas de la
    profondeur. Le jour où le plan couvrira les tours suivants, ce test **échouera** — et c'est
    exactement ce qu'on lui demande : il signalera que la lecture partagée (`profondeur_de`) est
    devenue observable des deux côtés, donc qu'un vrai test de parité est enfin possible.

    ⚠️ **Huit archers, et non quatre** (corrigé en 2ᵉ passe de revue). À quatre, `top_n(4)` et
    `un_vers_n` produisent le **même arbre entier** (4 matchs des deux côtés) : le test comparait
    deux fois le même tableau et serait resté vert quoi qu'il arrive — le « test décoratif » que
    l'en-tête de ce fichier condamne, reproduit un cran au-dessus. À huit, les arbres diffèrent
    (8 matchs contre 12) et l'égalité des plans devient un vrai témoin.
    """
    paires = []
    for profondeur in (None, ProfondeurClassement.integrale()):
        monde = _monde(profondeur, _HUIT_SCORES)
        monde.placer()
        plan = monde.placement.plan_de_duels(monde.tournoi_id, monde.phase_id or 0)
        paires.append(sorted(plan.duels_separes))
    assert paires[0] == paires[1]
