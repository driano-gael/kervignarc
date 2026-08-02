"""Tests d'intégration de `BarrageRepositorySQL` (E06US003) — adapter SQLite du port.

Écrits **après** l'implémentation, conformément à la règle 9 : il n'y a pas d'oracle en jeu ici. La
règle du barrage vit dans le domaine (testée depuis le CA en `test_domain_barrage_de_places.py`) ;
ce fichier vérifie une **traduction** — que ce qu'on écrit se relit à l'identique, et que les deux
pièges du modèle ne se referment pas :

- un `score` nul se relit **absent** (issue réglementaire), et non « pas encore saisi » ;
- ressaisir une manche **remplace** ses tirs au lieu de s'y ajouter, ce qui est le mode de
  correction d'une flèche mal notée.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from domain.archer import Archer
from domain.barrage import BarrageDePlaces, PorteeBarrage, TirBarrage
from domain.categorie import Categorie
from domain.erreurs import ConfigurationBarrageInvalide
from domain.participant import Participant
from domain.tournoi import Tournoi
from infrastructure.db import (
    ArcherRepositorySQL,
    BarrageRepositorySQL,
    CategorieRepositorySQL,
    Database,
    TournoiRepositorySQL,
)
from tests.base_migree import preparer_base

_DATE = datetime.date(2026, 3, 14)
_QUAND = datetime.datetime(2026, 3, 14, 10, 42, tzinfo=datetime.UTC)


def _contexte(tmp_path: Path, nb_archers: int = 3) -> tuple[Database, int, list[int]]:
    """Migre une base jetable, crée un tournoi et `nb_archers` archers ; rend les identifiants."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    preparer_base(url)
    db = Database(url)
    tournoi = TournoiRepositorySQL(db.session_factory).ajouter(Tournoi.creer("Salle 18m", _DATE))
    assert tournoi.id is not None
    categorie = CategorieRepositorySQL(db.session_factory).ajouter(
        Categorie.creer(tournoi.id, "Senior 1 H")
    )
    assert categorie.id is not None
    depot = ArcherRepositorySQL(db.session_factory)
    ids: list[int] = []
    for rang in range(nb_archers):
        archer = depot.ajouter(Archer.creer(f"Martin{rang}", "Alice", tournoi.id, categorie.id))
        assert archer.id is not None
        ids.append(archer.id)
    return db, tournoi.id, ids


def _annonce(tournoi_id: int, archers: list[int], rang: int = 8) -> BarrageDePlaces:
    return BarrageDePlaces(
        tournoi_id=tournoi_id,
        portee=PorteeBarrage.QUALIFICATION,
        participants=tuple(Participant.individuel(archer_id) for archer_id in archers),
        cree_le=_QUAND,
        rang_dispute=rang,
    )


def test_ouvrir_puis_relire(tmp_path: Path) -> None:
    db, tournoi_id, archers = _contexte(tmp_path, 2)
    depot = BarrageRepositorySQL(db.session_factory)

    ouvert = depot.ouvrir(_annonce(tournoi_id, archers))

    assert ouvert.id is not None
    relu = depot.par_id(ouvert.id)
    assert relu is not None
    assert relu.portee is PorteeBarrage.QUALIFICATION
    assert relu.rang_dispute == 8
    assert relu.participants == tuple(Participant.individuel(a) for a in archers)
    assert relu.manches == ()
    assert not relu.clos


def test_un_barrage_sans_manche_est_a_tirer_et_non_resolu(tmp_path: Path) -> None:
    """Tant que rien n'est saisi, tout le monde est à égalité — un barrage « à tirer », pas un
    verdict vide qui laisserait croire à une résolution."""
    db, tournoi_id, archers = _contexte(tmp_path, 2)
    depot = BarrageRepositorySQL(db.session_factory)
    ouvert = depot.ouvrir(_annonce(tournoi_id, archers))
    assert ouvert.id is not None

    resultat = ouvert.resultat()

    assert not resultat.est_resolu
    assert resultat.groupes_a_rejouer == (ouvert.participants,)
    assert ouvert.verdict().ordre == ()


def test_une_manche_saisie_se_relit_et_departage(tmp_path: Path) -> None:
    db, tournoi_id, archers = _contexte(tmp_path, 2)
    depot = BarrageRepositorySQL(db.session_factory)
    ouvert = depot.ouvrir(_annonce(tournoi_id, archers))
    assert ouvert.id is not None
    premier, second = (Participant.individuel(a) for a in archers)

    barrage = depot.enregistrer_manche(
        ouvert.id, 1, [TirBarrage(premier, 9), TirBarrage(second, 10)]
    )

    assert len(barrage.manches) == 1
    assert barrage.resultat().est_resolu
    assert barrage.verdict().rangs() == {second: 8, premier: 9}


def test_un_score_nul_se_relit_absent_et_fait_perdre(tmp_path: Path) -> None:
    """B.6.5.2.4 : l'archer absent au barrage annoncé est **déclaré perdant**. Le `NULL` en base
    porte cette issue réglementaire — ce n'est pas une saisie manquante, qui n'aurait pas de ligne.
    """
    db, tournoi_id, archers = _contexte(tmp_path, 2)
    depot = BarrageRepositorySQL(db.session_factory)
    ouvert = depot.ouvrir(_annonce(tournoi_id, archers))
    assert ouvert.id is not None
    present, absent = (Participant.individuel(a) for a in archers)

    barrage = depot.enregistrer_manche(
        ouvert.id, 1, [TirBarrage(present, 3), TirBarrage(absent, None)]
    )

    assert barrage.manches[0][1].score is None
    assert barrage.resultat().ordre == (present, absent)


def test_ressaisir_une_manche_remplace_ses_tirs(tmp_path: Path) -> None:
    """Le mode de **correction** d'une flèche mal notée : on ressaisit la manche, et le verdict —
    qui n'est jamais stocké — se recalcule. Des tirs qui s'ajouteraient laisseraient deux flèches au
    même archer pour la même manche, donc un verdict faux et plausible."""
    db, tournoi_id, archers = _contexte(tmp_path, 2)
    depot = BarrageRepositorySQL(db.session_factory)
    ouvert = depot.ouvrir(_annonce(tournoi_id, archers))
    assert ouvert.id is not None
    premier, second = (Participant.individuel(a) for a in archers)

    depot.enregistrer_manche(ouvert.id, 1, [TirBarrage(premier, 9), TirBarrage(second, 10)])
    corrige = depot.enregistrer_manche(
        ouvert.id, 1, [TirBarrage(premier, 10), TirBarrage(second, 9)]
    )

    assert len(corrige.manches) == 1
    assert len(corrige.manches[0]) == 2
    assert corrige.resultat().ordre == (premier, second)


def test_les_manches_se_relisent_dans_l_ordre(tmp_path: Path) -> None:
    """L'ordre des manches porte le sens : ce que la manche 1 a acquis, les suivantes ne le défont
    pas. Les relire triées est donc une exigence, pas un confort."""
    db, tournoi_id, archers = _contexte(tmp_path, 2)
    depot = BarrageRepositorySQL(db.session_factory)
    ouvert = depot.ouvrir(_annonce(tournoi_id, archers))
    assert ouvert.id is not None
    premier, second = (Participant.individuel(a) for a in archers)

    depot.enregistrer_manche(ouvert.id, 1, [TirBarrage(premier, 9), TirBarrage(second, 9)])
    barrage = depot.enregistrer_manche(
        ouvert.id, 2, [TirBarrage(premier, 8), TirBarrage(second, 10)]
    )

    assert len(barrage.manches) == 2
    assert barrage.manches[0][0].score == 9
    assert barrage.resultat().ordre == (second, premier)


def test_la_distance_au_centre_survit_a_l_aller_retour(tmp_path: Path) -> None:
    db, tournoi_id, archers = _contexte(tmp_path, 2)
    depot = BarrageRepositorySQL(db.session_factory)
    ouvert = depot.ouvrir(_annonce(tournoi_id, archers))
    assert ouvert.id is not None
    premier, second = (Participant.individuel(a) for a in archers)

    barrage = depot.enregistrer_manche(
        ouvert.id,
        1,
        [TirBarrage(premier, 10, distance_au_centre=42), TirBarrage(second, 10, 17)],
    )

    assert barrage.resultat().ordre == (second, premier)


def test_clore_marque_le_barrage_sans_toucher_aux_tirs(tmp_path: Path) -> None:
    db, tournoi_id, archers = _contexte(tmp_path, 2)
    depot = BarrageRepositorySQL(db.session_factory)
    ouvert = depot.ouvrir(_annonce(tournoi_id, archers))
    assert ouvert.id is not None
    premier, second = (Participant.individuel(a) for a in archers)
    depot.enregistrer_manche(ouvert.id, 1, [TirBarrage(premier, 9), TirBarrage(second, 10)])

    clos = depot.clore(ouvert.id)

    assert clos.clos
    assert len(clos.manches) == 1
    assert clos.resultat().est_resolu


def test_par_tournoi_rend_les_barrages_clos_aussi(tmp_path: Path) -> None:
    """Ce sont les barrages **clos** qui portent les verdicts déjà appliqués : les filtrer ferait
    retomber en ex æquo des rangs pourtant tranchés."""
    db, tournoi_id, archers = _contexte(tmp_path, 3)
    depot = BarrageRepositorySQL(db.session_factory)
    premier = depot.ouvrir(_annonce(tournoi_id, archers[:2], rang=4))
    second = depot.ouvrir(_annonce(tournoi_id, archers[1:], rang=8))
    assert premier.id is not None and second.id is not None
    depot.clore(premier.id)

    tous = depot.par_tournoi(tournoi_id)

    assert [barrage.rang_dispute for barrage in tous] == [4, 8]
    assert [barrage.clos for barrage in tous] == [True, False]


def test_par_tournoi_vide_rend_liste_vide(tmp_path: Path) -> None:
    db, tournoi_id, _ = _contexte(tmp_path, 2)
    assert BarrageRepositorySQL(db.session_factory).par_tournoi(tournoi_id) == []


def test_par_id_inconnu_rend_none(tmp_path: Path) -> None:
    db, _, _ = _contexte(tmp_path, 2)
    assert BarrageRepositorySQL(db.session_factory).par_id(4242) is None


def test_un_barrage_a_un_seul_tireur_est_refuse(tmp_path: Path) -> None:
    """Garde d'agrégat : à un seul participant, il n'y a rien à départager."""
    _, tournoi_id, archers = _contexte(tmp_path, 2)
    with pytest.raises(ConfigurationBarrageInvalide, match="au moins deux"):
        _annonce(tournoi_id, archers[:1])
