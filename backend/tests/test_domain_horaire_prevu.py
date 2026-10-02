"""E03US010 — l'horaire prévu d'un déroulé, calculé par départ depuis des durées d'étape.

Écrits **depuis le CA** (`stories/E03-placement.md` → E03US010), avant l'implémentation ; les
numéros cités sont ceux de ses points. ADR-0118.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from domain.deroule_etape import EtapeDeroule
from domain.erreurs import DureePrevueInvalide
from domain.format_tournoi import ModelePhase
from domain.horaire_prevu import HeurePrevue, horaires_prevus
from domain.phase import SourcePhase, TypePhase


def _etape(
    etape_id: int,
    *,
    duree: int | None = None,
    sources: tuple[int, ...] = (),
) -> EtapeDeroule:
    """Une élimination directe — le type qui ne demande ni barème ni grain."""
    return EtapeDeroule(
        tournoi_id=1,
        ordre=etape_id,
        type=TypePhase.ELIMINATION_DIRECTE,
        sources=tuple(SourcePhase.par_rangs(source) for source in sources),
        duree_prevue=duree,
        id=etape_id,
    )


def _par_etape(
    heure_depart: str, *etapes: EtapeDeroule
) -> dict[int, tuple[str | None, str | None]]:
    """`{etape_id: (debut, fin)}` en `HH:MM` — `None` pour l'inconnu."""
    return {
        horaire.etape_id: (
            None if horaire.debut is None else horaire.debut.libelle,
            None if horaire.fin is None else horaire.fin.libelle,
        )
        for horaire in horaires_prevus(heure_depart, etapes)
    }


# --- CA 1 : la durée prévue, facultative, bornée ---------------------------------------------


def test_une_etape_porte_sa_duree_prevue() -> None:
    assert _etape(1, duree=90).duree_prevue == 90


def test_la_duree_prevue_est_facultative() -> None:
    """Tous les déroulés déjà composés n'en ont aucune : l'exiger les rendrait illisibles."""
    assert _etape(1).duree_prevue is None


@pytest.mark.parametrize("duree", [1, 1440])
def test_les_bornes_de_la_duree_sont_admises(duree: int) -> None:
    assert _etape(1, duree=duree).duree_prevue == duree


@pytest.mark.parametrize("duree", [0, -5, 1441])
def test_une_duree_hors_bornes_est_refusee(duree: int) -> None:
    with pytest.raises(DureePrevueInvalide):
        _etape(1, duree=duree)


def test_la_duree_est_refusee_aussi_par_replace() -> None:
    """« Quelle que soit la porte d'entrée » — `replace()` repasse par `__post_init__`."""
    with pytest.raises(DureePrevueInvalide):
        replace(_etape(1, duree=30), duree_prevue=0)


def test_la_duree_voyage_de_l_etape_au_format_et_retour() -> None:
    """CA 8 : capturer un tournoi en format, puis l'appliquer, garde la durée. Un champ présent
    d'un seul côté de la traversée la perdrait en silence (le défaut `barrage_jusqu_au`)."""
    modele = ModelePhase.d_etape(_etape(1, duree=75))
    assert modele.duree_prevue == 75
    assert modele.pour_tournoi(tournoi_id=1).duree_prevue == 75


def test_appliquer_un_format_a_duree_hors_bornes_est_refuse() -> None:
    """`ModelePhase` reste sans invariant (E01US024) : le refus tombe à l'instanciation."""
    modele = ModelePhase(ordre=1, type=TypePhase.ELIMINATION_DIRECTE, duree_prevue=0)
    with pytest.raises(DureePrevueInvalide):
        modele.pour_tournoi(tournoi_id=1)


# --- CA 2 : début = départ ou fin la plus tardive des sources ; fin = début + durée -----------


def test_une_etape_sans_source_commence_a_l_heure_du_depart() -> None:
    assert _par_etape("09:00", _etape(1, duree=150)) == {1: ("09:00", "11:30")}


def test_une_etape_commence_a_la_fin_de_sa_source() -> None:
    horaires = _par_etape("09:00", _etape(1, duree=150), _etape(2, duree=60, sources=(1,)))
    assert horaires[2] == ("11:30", "12:30")


def test_une_etape_a_deux_sources_attend_la_plus_tardive() -> None:
    horaires = _par_etape(
        "09:00",
        _etape(1, duree=60),
        _etape(2, duree=120),
        _etape(3, duree=30, sources=(1, 2)),
    )
    assert horaires[3] == ("11:00", "11:30")


def test_le_calcul_suit_les_sources_et_non_l_ordre() -> None:
    """L'`ordre` est topologique, pas chronologique (ADR-0082) : une étape sans source commence au
    départ même si son rang est le dernier."""
    tardive = replace(_etape(9, duree=45), ordre=9)
    horaires = _par_etape("14:00", _etape(1, duree=60), _etape(2, duree=60, sources=(1,)), tardive)
    assert horaires[9] == ("14:00", "14:45")


def test_chaque_depart_a_ses_propres_horaires() -> None:
    """Une même définition, deux créneaux : l'horaire dépend de l'heure du départ."""
    etapes = (_etape(1, duree=120), _etape(2, duree=60, sources=(1,)))
    assert _par_etape("09:00", *etapes)[2] == ("11:00", "12:00")
    assert _par_etape("14:00", *etapes)[2] == ("16:00", "17:00")


def test_un_horaire_par_etape_dans_l_ordre_du_deroule() -> None:
    etapes = (_etape(1, duree=10), _etape(2, duree=10, sources=(1,)), _etape(3, duree=10))
    assert [h.etape_id for h in horaires_prevus("09:00", etapes)] == [1, 2, 3]


# --- CA 3 : l'inconnu se propage --------------------------------------------------------------


def test_une_etape_sans_duree_a_un_debut_connu_et_une_fin_inconnue() -> None:
    assert _par_etape("09:00", _etape(1)) == {1: ("09:00", None)}


def test_l_inconnu_se_propage_a_toute_la_descendance() -> None:
    horaires = _par_etape(
        "09:00",
        _etape(1),
        _etape(2, duree=60, sources=(1,)),
        _etape(3, duree=60, sources=(2,)),
    )
    assert horaires[2] == (None, None)
    assert horaires[3] == (None, None)


def test_une_seule_source_inconnue_suffit_a_rendre_le_debut_inconnu() -> None:
    """« La plus tardive » de deux fins dont l'une est inconnue n'est pas connue : prendre l'autre
    serait deviner."""
    horaires = _par_etape(
        "09:00",
        _etape(1, duree=60),
        _etape(2),
        _etape(3, duree=30, sources=(1, 2)),
    )
    assert horaires[3] == (None, None)


def test_une_source_absente_du_deroule_rend_le_debut_inconnu() -> None:
    """Une source qui ne désigne aucune étape connue n'a pas de fin : rien à en déduire."""
    assert _par_etape("09:00", _etape(2, duree=30, sources=(99,))) == {2: (None, None)}


# --- CA 4 : deux étapes nourries des mêmes sources commencent ensemble ------------------------


def test_deux_etapes_soeurs_commencent_a_la_meme_heure() -> None:
    horaires = _par_etape(
        "09:00",
        _etape(1, duree=120),
        _etape(2, duree=90, sources=(1,)),
        _etape(3, duree=45, sources=(1,)),
    )
    assert horaires[2] == ("11:00", "12:30")
    assert horaires[3] == ("11:00", "11:45")


# --- CA 5 : passer minuit ---------------------------------------------------------------------


def test_une_heure_apres_minuit_se_signale_du_lendemain() -> None:
    (horaire,) = horaires_prevus("23:00", (_etape(1, duree=90),))
    assert horaire.debut == HeurePrevue(23 * 60)
    assert horaire.fin is not None
    assert (horaire.fin.libelle, horaire.fin.jours_apres) == ("00:30", 1)


def test_une_heure_du_jour_meme_n_est_pas_du_lendemain() -> None:
    assert HeurePrevue(9 * 60 + 5).libelle == "09:05"
    assert HeurePrevue(9 * 60 + 5).jours_apres == 0
