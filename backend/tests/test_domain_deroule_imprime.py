"""E09US007 — le déroulé horaire imprimable : ses lignes et ses tours annoncés.

Écrits **depuis le CA** (`stories/E09-exports.md` → E09US007, cadrage du 03/10/2026), avant
l'implémentation ; les numéros cités sont ceux de ses points.
"""

from __future__ import annotations

import pytest

from domain.bareme import BaremeQualification
from domain.colline import ConfigurationColline
from domain.deroule_etape import EtapeDeroule
from domain.deroule_imprime import lignes_du_deroule, tours_annonces
from domain.grain_validation import GrainValidation
from domain.horaire_prevu import HeurePrevue, HorairePrevu
from domain.phase import TypePhase
from domain.poule import ReglageDePoules
from domain.qualification import DecoupageEnTours
from domain.suisse import ConfigurationSuisse


def _qualification(nb_tours: int | None, *, etape_id: int = 1, ordre: int = 1) -> EtapeDeroule:
    return EtapeDeroule(
        tournoi_id=1,
        ordre=ordre,
        type=TypePhase.QUALIFICATION,
        bareme=BaremeQualification.creer(20, 3),
        validation=GrainValidation.fin_de_serie(),
        decoupage=None if nb_tours is None else DecoupageEnTours(nb_tours=nb_tours),
        id=etape_id,
    )


def _etape(
    type_phase: TypePhase, *, etape_id: int = 2, ordre: int = 2, titre: str | None = None
) -> EtapeDeroule:
    return EtapeDeroule(tournoi_id=1, ordre=ordre, type=type_phase, titre=titre, id=etape_id)


# --- CA 3 : les tours en information, quand l'étape les règle ----------------------------------


def test_une_qualification_decoupee_annonce_ses_tours() -> None:
    assert tours_annonces(_qualification(2)) == "2 tours"


def test_un_systeme_suisse_annonce_ses_rondes() -> None:
    etape = EtapeDeroule(
        tournoi_id=1, ordre=2, type=TypePhase.SUISSE, suisse=ConfigurationSuisse(nb_rondes=5)
    )

    assert tours_annonces(etape) == "5 rondes"


def test_une_colline_annonce_ses_manches() -> None:
    etape = EtapeDeroule(
        tournoi_id=1,
        ordre=2,
        type=TypePhase.COLLINE,
        colline=ConfigurationColline(nb_manches=3),
    )

    assert tours_annonces(etape) == "3 manches"


def test_un_seul_tour_ne_s_annonce_pas() -> None:
    """« rien pour un seul tour » — non découpée, la qualification est son propre tour."""
    assert tours_annonces(_qualification(None)) is None
    assert tours_annonces(_qualification(1)) is None


def test_un_tableau_n_annonce_pas_de_tours() -> None:
    """Sa taille dépend de l'effectif et de la politique de `seeding` : rien n'est imprimé."""
    assert tours_annonces(_etape(TypePhase.ELIMINATION_DIRECTE)) is None


def test_des_poules_n_annoncent_pas_de_tours() -> None:
    etape = EtapeDeroule(
        tournoi_id=1, ordre=2, type=TypePhase.POULES, poules=ReglageDePoules(taille_visee=4)
    )

    assert tours_annonces(etape) is None


def test_un_suisse_ou_une_colline_non_regles_n_annoncent_rien() -> None:
    """Le réglage manquant est refusé au démarrage, pas ici : on n'imprime pas ce qu'on ignore."""
    assert tours_annonces(_etape(TypePhase.SUISSE)) is None
    assert tours_annonces(_etape(TypePhase.COLLINE)) is None


# --- CA 2 : une ligne par phase, dans l'ordre du déroulé, aux heures d'E03US010 -----------------


def test_une_ligne_par_etape_dans_l_ordre_du_deroule() -> None:
    etapes = [
        _etape(TypePhase.ELIMINATION_DIRECTE, etape_id=7, ordre=2, titre="Tableau des jeunes"),
        _qualification(2, etape_id=3, ordre=1),
    ]
    horaires = [
        HorairePrevu(etape_id=7, ordre=2, debut=HeurePrevue(14 * 60), fin=None),
        HorairePrevu(etape_id=3, ordre=1, debut=HeurePrevue(9 * 60), fin=HeurePrevue(14 * 60)),
    ]

    lignes = lignes_du_deroule(etapes, horaires)

    assert [ligne.ordre for ligne in lignes] == [1, 2]
    qualification, tableau = lignes
    assert qualification.type is TypePhase.QUALIFICATION
    assert qualification.titre is None
    assert qualification.debut == HeurePrevue(9 * 60)
    assert qualification.fin == HeurePrevue(14 * 60)
    assert qualification.tours == "2 tours"
    assert tableau.titre == "Tableau des jeunes"
    assert tableau.debut == HeurePrevue(14 * 60)
    assert tableau.fin is None
    assert tableau.tours is None


def test_une_etape_sans_horaire_calcule_garde_des_heures_inconnues() -> None:
    """L'heure n'est jamais devinée : sans horaire rapproché, la ligne dit « inconnu »."""
    lignes = lignes_du_deroule([_qualification(None, etape_id=3)], [])

    assert len(lignes) == 1
    assert lignes[0].debut is None
    assert lignes[0].fin is None


def test_un_deroule_vide_ne_rend_aucune_ligne() -> None:
    assert lignes_du_deroule([], []) == ()


# --- Garde : chaque type de phase est classé explicitement -------------------------------------

_ANNONCENT_LEURS_TOURS: frozenset[TypePhase] = frozenset(
    {TypePhase.QUALIFICATION, TypePhase.SUISSE, TypePhase.COLLINE}
)
"""Les types dont le nombre de tours est un **réglage de l'étape** (CA 3). ⚠️ Un type ajouté à
`TypePhase` fait échouer le test ci-dessous tant qu'il n'est pas rangé ici ou dans le complément
— le raté de la colline dans `_nb_tours_a_la_composition`, à ne pas rejouer."""

_N_ANNONCENT_RIEN: frozenset[TypePhase] = frozenset(
    {
        TypePhase.ELIMINATION_DIRECTE,
        TypePhase.PLACEMENT,
        TypePhase.ECHAUFFEMENT,
        TypePhase.BARRAGE,
        TypePhase.POULES,
        TypePhase.BIG_SHOOT_OFF,
    }
)


def test_chaque_type_de_phase_est_classe() -> None:
    assert set(TypePhase) == _ANNONCENT_LEURS_TOURS | _N_ANNONCENT_RIEN
    assert not _ANNONCENT_LEURS_TOURS & _N_ANNONCENT_RIEN


@pytest.mark.parametrize("valeur", sorted(t.value for t in _N_ANNONCENT_RIEN))
def test_un_type_sans_reglage_de_tours_n_annonce_rien(valeur: str) -> None:
    assert tours_annonces(_etape(TypePhase(valeur))) is None
