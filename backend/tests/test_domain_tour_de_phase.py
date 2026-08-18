"""Le **tour**, unité d'avancement générique d'une phase ([ADR-0090], E05US032).

Tests écrits **depuis le CA** de l'US, avant l'implémentation (règle 9) : la règle métier en jeu
est celle que le commanditaire a posée au cadrage du 18/08/2026 — *« un tour est une unité
d'avancement, jamais de classement »* —, pas ce que le code sait déjà faire. C'est précisément la
distinction que le code **viole** aujourd'hui : `AvancementTour` dérive les tours des braquets,
donc une phase qui ne classe pas au fil de l'eau n'a « aucun tour ».

Deux gardes ont une valeur particulière et méritent d'être lues avant les autres :

- `test_l_echauffement_qui_ne_classe_rien_avance_quand_meme_par_tours` est l'**oracle de
  l'invariant**. S'il tombe un jour, c'est que quelqu'un a re-branché le tour sur le classement.
- `test_le_libelle_d_un_tour_de_tableau_se_compte_a_rebours_de_la_finale` garde la **délégation**
  au domaine du tableau. Le CA l'exige explicitement : la résolution générique doit *absorber*
  `domain/tableau.py`, pas ouvrir un troisième domicile au libellé de tour (`DETTE-020`). Un
  libellé générique qui rendrait « Tour 3 » là où la salle dit « Demi-finale » passerait tous les
  autres tests de ce fichier.

[ADR-0090]: ../../docs/adr/0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md
"""

from __future__ import annotations

import pytest

from domain.contrat_phase import TypePhase, contrat_de
from domain.tour_de_phase import UniteDeTour, libelle_de_tour, unite_de_tour


def test_tout_type_de_phase_avance_par_tours() -> None:
    """CA — « toute phase compte des tours, quel que soit son format ».

    Complétude, pas recopie : on ne vérifie pas *quelle* unité chaque type porte (le registre le
    dirait deux fois), on vérifie qu'**aucun** type n'en est dépourvu. C'est la garde qui échouera
    le jour où un type neuf entrera au catalogue sans répondre à la 7ᵉ question du contrat.
    """
    for type_phase in TypePhase:
        assert isinstance(unite_de_tour(type_phase), UniteDeTour)


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


@pytest.mark.parametrize(
    ("type_phase", "attendue"),
    [
        (TypePhase.QUALIFICATION, UniteDeTour.PHASE_ENTIERE),
        (TypePhase.ECHAUFFEMENT, UniteDeTour.PHASE_ENTIERE),
        (TypePhase.ELIMINATION_DIRECTE, UniteDeTour.TOUR_DE_TABLEAU),
        (TypePhase.PLACEMENT, UniteDeTour.TOUR_DE_TABLEAU),
        (TypePhase.POULES, UniteDeTour.TOUR),
        (TypePhase.SUISSE, UniteDeTour.RONDE),
        (TypePhase.COLLINE, UniteDeTour.RONDE),
        (TypePhase.BIG_SHOOT_OFF, UniteDeTour.MANCHE),
    ],
)
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
