"""Le **tour**, unité d'avancement générique d'une phase ([ADR-0090], E05US032).

Tests écrits **depuis le CA** de l'US, avant l'implémentation (règle 9) : la règle métier en jeu
est celle que le commanditaire a posée au cadrage du 18/08/2026 — *« un tour est une unité
d'avancement, jamais de classement »* —, pas ce que le code sait déjà faire. C'est précisément la
distinction que le code **violait** avant cette US : `AvancementTour` dérivait les tours des
braquets, donc une phase qui ne classe pas au fil de l'eau n'avait « aucun tour ».

Deux gardes ont une valeur particulière et méritent d'être lues avant les autres :

- `test_l_echauffement_qui_ne_classe_rien_avance_quand_meme_par_tours` garde le **registre** :
  un type qui ne classe rien porte quand même une unité de tour. ⚠️ Il ne garde **pas** le calcul —
  `avancement_bloc` pourrait re-dériver les tours des braquets qu'il resterait vert. L'oracle de
  l'invariant est `test_une_phase_sans_braquet_affiche_le_tour_lu_a_son_format`, dans
  `test_domain_suivi_deroule.py` ; la première rédaction de cet en-tête promettait le contraire
  (relevé en revue, axe B).
- `test_le_libelle_d_un_tour_de_tableau_se_compte_a_rebours_de_la_finale` garde la **délégation**
  au domaine du tableau. Le CA l'exige explicitement : la résolution générique doit *absorber*
  `domain/tableau.py`, pas ouvrir un troisième domicile au libellé de tour (`DETTE-020`). Un
  libellé générique qui rendrait « Tour 3 » là où la salle dit « Demi-finale » passerait tous les
  autres tests de ce fichier.

[ADR-0090]: ../../docs/adr/0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md
"""

from __future__ import annotations

import pytest

from domain.contrat_phase import TypePhase, UniteDeTour, contrat_de
from domain.tour_de_phase import libelle_de_tour, unite_de_tour


def test_tout_type_de_phase_avance_par_tours() -> None:
    """CA — « toute phase compte des tours, quel que soit son format ».

    ⚠️ **La garde est l'exhaustivité du tableau ci-dessous, pas un `isinstance`.** La première
    rédaction itérait sur `TypePhase` en vérifiant que l'unité est bien une `UniteDeTour` : comme
    `ContratDePhase.unite_de_tour` porte une **valeur par défaut**, un type neuf répond toujours, et
    l'assertion ne pouvait pas échouer — elle promettait une détection qu'elle n'offrait pas
    (relevé en revue, axes C1 et adversarial). Ce qu'on veut réellement empêcher, c'est qu'un type
    neuf entre au catalogue sans que **quelqu'un ait décidé** de son unité ; le seul endroit où
    cette décision se lit est le tableau de vocabulaire du test suivant.
    """
    couverts = {cas.values[0] for cas in _UNITES_ATTENDUES}
    assert couverts == set(TypePhase)


def test_l_echauffement_qui_ne_classe_rien_avance_quand_meme_par_tours() -> None:
    """CA — « un tour est une unité d'*avancement*, jamais de *classement* ».

    L'échauffement est le seul type qui ne produit **aucun** classement (`produit_un_classement`
    est faux pour lui seul, référentiel §10.1) : il n'attribue rien et n'élimine personne. Il
    occupe pourtant du temps et des cibles — donc il avance, donc il a des tours.

    C'est le cas-test de l'invariant, et il est choisi pour ça : tout code qui re-dériverait le
    tour du classement (ou du braquet, qui en est la trace) le ferait retomber à zéro tour.
    """
    assert contrat_de(TypePhase.ECHAUFFEMENT).produit_un_classement is False
    assert unite_de_tour(TypePhase.ECHAUFFEMENT) is UniteDeTour.PHASE_ENTIERE


_UNITES_ATTENDUES = [
    # ⚠️ **`TOUR` depuis E05US035** (ADR-0093) : « 20 volées en 2 tours de 10 » est le mot que la
    # salle emploie, et le réglage qui le rend vrai existe désormais. Une qualification **non
    # découpée** compte alors un seul tour, ce qui reste vrai — la phase *est* son tour —, et
    # `libelle_de_tour` n'annonce rien à `nb_tours == 1` (test juste au-dessus).
    pytest.param(TypePhase.QUALIFICATION, UniteDeTour.TOUR),
    pytest.param(TypePhase.ECHAUFFEMENT, UniteDeTour.PHASE_ENTIERE),
    # `BARRAGE` est le seul type dont le diff d'E05US032 ne touche pas le contrat : il hérite du
    # défaut. C'est donc précisément celui qu'un tableau de vocabulaire doit épingler — son absence
    # a été relevée en revue par deux axes.
    pytest.param(TypePhase.BARRAGE, UniteDeTour.PHASE_ENTIERE),
    pytest.param(TypePhase.ELIMINATION_DIRECTE, UniteDeTour.TOUR_DE_TABLEAU),
    pytest.param(TypePhase.PLACEMENT, UniteDeTour.TOUR_DE_TABLEAU),
    pytest.param(TypePhase.POULES, UniteDeTour.TOUR),
    pytest.param(TypePhase.SUISSE, UniteDeTour.RONDE),
    # ⚠️ **`MANCHE` depuis E05US027, et cette ligne disait `RONDE` — à tort.** Le référentiel §10.1,
    # qui fait foi ici, écrit « après plusieurs **manches** » et « nombre de **manches** réglé à la
    # composition » ; le réglage s'appelle `nb_manches`, l'écran de saisie et l'écran public disent
    # « Manche 2 sur 3 ». Le contrat, lui, avait hérité de `RONDE` d'E05US015 — sans conséquence
    # tant que la colline n'était pas `avancement_lisible`, puisque le mot n'atteignait aucun écran.
    # L'US qui l'y expose a rendu la divergence visible : la même phase annonçait « Manche 2 sur 3 »
    # au scoreur et « Ronde 2 » au suivi du déroulé et sur le bandeau de pause, lui aussi public.
    # Trois axes de revue l'ont relevée. C'est exactement l'inversion silencieuse entre deux formats
    # que ce tableau existe pour attraper — il l'a attrapée, une fois le registre corrigé.
    pytest.param(TypePhase.COLLINE, UniteDeTour.MANCHE),
    pytest.param(TypePhase.BIG_SHOOT_OFF, UniteDeTour.MANCHE),
]


@pytest.mark.parametrize(("type_phase", "attendue"), _UNITES_ATTENDUES)
def test_chaque_format_avance_dans_l_unite_de_son_metier(
    type_phase: TypePhase, attendue: UniteDeTour
) -> None:
    """CA — « le libellé affiché est le mot du métier, résolu par le type de phase ».

    Ici on **recopie** délibérément le registre, contrairement au test de complétude ci-dessus : ce
    ne sont pas des valeurs de configuration mais du **vocabulaire FFTA** (règle 3), et le
    référentiel §10.1 en fait foi — le suisse tire des *rondes*, le Big Shoot Off des *manches*.
    Une inversion silencieuse entre deux formats se lit dans ce tableau, nulle part ailleurs.
    """
    assert unite_de_tour(type_phase) is attendue


@pytest.mark.parametrize(
    ("unite", "tour", "nb_tours", "attendu"),
    [
        (UniteDeTour.RONDE, 3, 5, "Ronde 3"),
        (UniteDeTour.RONDE, 1, 5, "Ronde 1"),
        (UniteDeTour.MANCHE, 2, 3, "Manche 2"),
        (UniteDeTour.TOUR, 3, 5, "Tour 3"),
    ],
)
def test_le_libelle_nomme_le_tour_dans_le_mot_de_la_salle(
    unite: UniteDeTour, tour: int, nb_tours: int, attendu: str
) -> None:
    """CA — « Ronde 3 », « Manche 2 », « Tour 3 »."""
    assert libelle_de_tour(unite, tour, nb_tours) == attendu


@pytest.mark.parametrize(
    ("unite", "attendu"),
    [
        (UniteDeTour.RONDE, None),
        (UniteDeTour.TOUR, None),
        (UniteDeTour.MANCHE, None),
        # Le tableau fait exception, et c'est le point : son tour unique porte un **nom**, pas un
        # numéro. La clause du CA vise « ne pas annoncer de numéro », pas « ne rien dire ».
        (UniteDeTour.TOUR_DE_TABLEAU, "Finale"),
    ],
)
def test_une_phase_a_un_seul_tour_n_annonce_pas_de_numero(
    unite: UniteDeTour, attendu: str | None
) -> None:
    """CA — « une phase à **un seul** tour n'annonce pas de numéro : il n'y a rien à distinguer ».

    Cas réels sur un petit plateau de club : une poule de deux archers, un système suisse dont
    l'effectif n'autorise qu'une ronde, un Big Shoot Off à manche unique.

    ⚠️ **Ce test est né d'un relevé de revue, et le défaut vaut d'être nommé** : la clause n'était
    appliquée qu'à `PHASE_ENTIERE`, et le test censé la couvrir citait le CA en docstring puis
    n'exerçait que le cas qui passait déjà. Le paramètre `nb_tours`, présent dans la signature et
    inutilisé, était la trace de la règle lue puis perdue. C'est exactement le mode de défaillance
    que la règle 9 vise — un test rédigé d'après l'implémentation entérine le malentendu.
    """
    assert libelle_de_tour(unite, 1, 1) == attendu


def test_une_phase_entiere_n_annonce_aucun_libelle_de_tour() -> None:
    """CA — « une phase à un seul tour n'annonce pas de numéro : il n'y a rien à distinguer ».

    Une qualification en cours se lit « Qualification », jamais « Qualification — tour 1 sur 1 ».
    Le libellé rendu est donc `None` et non une chaîne vide : c'est l'appelant qui décide de
    n'afficher rien, et un `None` explicite l'empêche de concaténer un séparateur orphelin.
    """
    assert libelle_de_tour(UniteDeTour.PHASE_ENTIERE, 1, 1) is None


@pytest.mark.parametrize(
    ("tour", "nb_tours", "attendu"),
    [
        (4, 4, "Finale"),
        (3, 4, "Demi-finale"),
        (2, 4, "Quart de finale"),
        (1, 4, "1/8 de finale"),
    ],
)
def test_le_libelle_d_un_tour_de_tableau_se_compte_a_rebours_de_la_finale(
    tour: int, nb_tours: int, attendu: str
) -> None:
    """CA — la résolution générique **absorbe** `domain/tableau.py`, elle ne s'y ajoute pas.

    Un archer ne se repère pas au rang du tour dans l'arbre mais à sa **distance au titre** : le
    tour 2 d'un tableau de 16 est un quart de finale, pas « le tour 2 ». Cette règle est déjà
    écrite (`domain.tableau.libelle_tour`) et `DETTE-020` compte déjà **deux** domiciles pour
    elle — un générique qui la réimplémenterait en ouvrirait un troisième, ce que le CA interdit
    nommément.

    Le test le vérifie par l'**effet** plutôt que par l'appel : il n'inspecte pas qui délègue à
    qui, il exige le vocabulaire que seule la fonction du tableau sait produire. Un `f"Tour {n}"`
    générique échouerait ici, et c'est tout l'objet de cette garde.
    """
    assert libelle_de_tour(UniteDeTour.TOUR_DE_TABLEAU, tour, nb_tours) == attendu
