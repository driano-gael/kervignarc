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
from domain.depart import Depart
from domain.erreurs import ConfigurationBarrageInvalide
from domain.participant import Participant
from domain.tournoi import Tournoi
from infrastructure.db import (
    ArcherRepositorySQL,
    BarrageRepositorySQL,
    CategorieRepositorySQL,
    Database,
    DepartRepositorySQL,
    TournoiRepositorySQL,
)
from tests.base_migree import preparer_base

_DATE = datetime.date(2026, 3, 14)
_QUAND = datetime.datetime(2026, 3, 14, 10, 42, tzinfo=datetime.UTC)


def _contexte(tmp_path: Path, nb_archers: int = 3) -> tuple[Database, int, int, list[int]]:
    """Migre une base jetable, crée un tournoi, **son créneau** et `nb_archers` archers.

    Rend `(db, tournoi_id, depart_id, archer_ids)` : un barrage pend au **départ** depuis E01US025
    (ADR-0075), et la FK refuse un identifiant de tournoi. Mais la vue **transverse**
    `par_tournoi` attend, elle, un identifiant de tournoi — et les tests lui passaient le
    `depart_id`, vert par la seule coïncidence des deux `id` valant 1. Rendre les **deux** supprime
    l'ambiguïté à l'appel plutôt que de compter sur la vigilance (`DETTE-044` : même type pour
    mypy).

    ⚠️ Un tournoi **leurre** est créé d'abord, exprès : sans lui, `tournoi.id == depart.id == 1` et
    la confusion redeviendrait invisible au premier test distrait.
    """
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    preparer_base(url)
    db = Database(url)
    depot_tournois = TournoiRepositorySQL(db.session_factory)
    depot_tournois.ajouter(Tournoi.creer("Leurre — désynchronise les identifiants", _DATE))
    tournoi = depot_tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
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
    depart = DepartRepositorySQL(db.session_factory).ajouter(
        Depart.creer(tournoi_id=tournoi.id, numero=1, tarif_centimes=800, horaire="09:00")
    )
    assert depart.id is not None
    return db, tournoi.id, depart.id, ids


def _annonce(depart_id: int, archers: list[int], rang: int = 8) -> BarrageDePlaces:
    return BarrageDePlaces(
        depart_id=depart_id,
        portee=PorteeBarrage.QUALIFICATION,
        participants=tuple(Participant.individuel(archer_id) for archer_id in archers),
        cree_le=_QUAND,
        rang_dispute=rang,
    )


def test_ouvrir_puis_relire(tmp_path: Path) -> None:
    db, tournoi_id, depart_id, archers = _contexte(tmp_path, 2)
    depot = BarrageRepositorySQL(db.session_factory)

    ouvert = depot.ouvrir(_annonce(depart_id, archers))

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
    db, tournoi_id, depart_id, archers = _contexte(tmp_path, 2)
    depot = BarrageRepositorySQL(db.session_factory)
    ouvert = depot.ouvrir(_annonce(depart_id, archers))
    assert ouvert.id is not None

    resultat = ouvert.resultat()

    assert not resultat.est_resolu
    assert resultat.groupes_a_rejouer == (ouvert.participants,)
    assert ouvert.verdict().ordre == ()


def test_une_manche_saisie_se_relit_et_departage(tmp_path: Path) -> None:
    db, tournoi_id, depart_id, archers = _contexte(tmp_path, 2)
    depot = BarrageRepositorySQL(db.session_factory)
    ouvert = depot.ouvrir(_annonce(depart_id, archers))
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
    db, tournoi_id, depart_id, archers = _contexte(tmp_path, 2)
    depot = BarrageRepositorySQL(db.session_factory)
    ouvert = depot.ouvrir(_annonce(depart_id, archers))
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
    db, tournoi_id, depart_id, archers = _contexte(tmp_path, 2)
    depot = BarrageRepositorySQL(db.session_factory)
    ouvert = depot.ouvrir(_annonce(depart_id, archers))
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
    db, tournoi_id, depart_id, archers = _contexte(tmp_path, 2)
    depot = BarrageRepositorySQL(db.session_factory)
    ouvert = depot.ouvrir(_annonce(depart_id, archers))
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
    db, tournoi_id, depart_id, archers = _contexte(tmp_path, 2)
    depot = BarrageRepositorySQL(db.session_factory)
    ouvert = depot.ouvrir(_annonce(depart_id, archers))
    assert ouvert.id is not None
    premier, second = (Participant.individuel(a) for a in archers)

    barrage = depot.enregistrer_manche(
        ouvert.id,
        1,
        [TirBarrage(premier, 10, distance_au_centre=42), TirBarrage(second, 10, 17)],
    )

    assert barrage.resultat().ordre == (second, premier)


def test_clore_marque_le_barrage_sans_toucher_aux_tirs(tmp_path: Path) -> None:
    db, tournoi_id, depart_id, archers = _contexte(tmp_path, 2)
    depot = BarrageRepositorySQL(db.session_factory)
    ouvert = depot.ouvrir(_annonce(depart_id, archers))
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
    db, tournoi_id, depart_id, archers = _contexte(tmp_path, 3)
    depot = BarrageRepositorySQL(db.session_factory)
    premier = depot.ouvrir(_annonce(depart_id, archers[:2], rang=4))
    second = depot.ouvrir(_annonce(depart_id, archers[1:], rang=8))
    assert premier.id is not None and second.id is not None
    depot.clore(premier.id)

    tous = depot.par_tournoi(tournoi_id)

    assert [barrage.rang_dispute for barrage in tous] == [4, 8]
    assert [barrage.clos for barrage in tous] == [True, False]


def test_par_tournoi_vide_rend_liste_vide(tmp_path: Path) -> None:
    db, tournoi_id, depart_id, _ = _contexte(tmp_path, 2)
    assert BarrageRepositorySQL(db.session_factory).par_tournoi(tournoi_id) == []


def test_par_id_inconnu_rend_none(tmp_path: Path) -> None:
    db, tournoi_id, _, _ = _contexte(tmp_path, 2)
    assert BarrageRepositorySQL(db.session_factory).par_id(4242) is None


def test_un_barrage_a_un_seul_tireur_est_refuse(tmp_path: Path) -> None:
    """Garde d'agrégat : à un seul participant, il n'y a rien à départager."""
    _, _, depart_id, archers = _contexte(tmp_path, 2)
    with pytest.raises(ConfigurationBarrageInvalide, match="au moins deux"):
        _annonce(depart_id, archers[:1])


# --- cascade archer et barrage (correctif de revue, bloquant) -------------------------------------


def test_supprimer_un_archer_qui_a_tire_un_barrage(tmp_path: Path) -> None:
    """`barrage_tir.archer_id` est une FK **enforced** sans `ON DELETE` : sans nettoyage, l'archer
    devient indéracinable (500).

    C'est exactement le défaut qu'une revue adversariale avait fait corriger sur `forfait`, dont le
    docstring de `supprimer` garde le récit — rejoué ici sur une table neuve. On supprime le
    **barrage entier**, pas seulement les tirs : un barrage amputé d'un tireur annoncé serait refusé
    à la relecture.
    """
    db, tournoi_id, depart_id, archers = _contexte(tmp_path, 2)
    depot = BarrageRepositorySQL(db.session_factory)
    ouvert = depot.ouvrir(_annonce(depart_id, archers))
    assert ouvert.id is not None
    premier, second = (Participant.individuel(a) for a in archers)
    depot.enregistrer_manche(ouvert.id, 1, [TirBarrage(premier, 9), TirBarrage(second, 10)])

    ArcherRepositorySQL(db.session_factory).supprimer(archers[0])

    assert depot.par_tournoi(tournoi_id) == []


def test_supprimer_un_archer_seulement_annonce_au_barrage(tmp_path: Path) -> None:
    """Un archer peut être **annoncé sans avoir tiré** : il n'a alors aucune ligne de tir, et seul
    `participants_json` le mentionne. C'est le cas que la lecture des seuls tirs manquerait."""
    db, tournoi_id, depart_id, archers = _contexte(tmp_path, 2)
    depot = BarrageRepositorySQL(db.session_factory)
    depot.ouvrir(_annonce(depart_id, archers))

    ArcherRepositorySQL(db.session_factory).supprimer(archers[1])

    assert depot.par_tournoi(tournoi_id) == []


def test_fusionner_deux_archers_dont_un_a_tire_un_barrage(tmp_path: Path) -> None:
    """La fusion de doublons (E02US005) ne doit pas casser dès qu'un des deux a barré."""
    db, tournoi_id, depart_id, archers = _contexte(tmp_path, 3)
    gagnant, perdant, tiers = archers
    depot = BarrageRepositorySQL(db.session_factory)
    ouvert = depot.ouvrir(_annonce(depart_id, [perdant, tiers]))
    assert ouvert.id is not None
    depot.enregistrer_manche(
        ouvert.id,
        1,
        [
            TirBarrage(Participant.individuel(perdant), 9),
            TirBarrage(Participant.individuel(tiers), 10),
        ],
    )

    ArcherRepositorySQL(db.session_factory).fusionner(gagnant, perdant)

    relu = depot.par_tournoi(tournoi_id)
    assert len(relu) == 1
    # Le tir du perdant est reporté sur le gagnant, et la liste des tireurs le suit.
    assert Participant.individuel(gagnant) in relu[0].participants
    assert Participant.individuel(perdant) not in relu[0].participants
    assert relu[0].resultat().ordre == (
        Participant.individuel(tiers),
        Participant.individuel(gagnant),
    )


def test_fusionner_deux_archers_du_meme_barrage_le_rend_caduc(tmp_path: Path) -> None:
    """Si les deux fiches fusionnées étaient les **seuls** tireurs, le barrage n'oppose plus
    personne : on le supprime plutôt que de laisser un agrégat que le domaine rejetterait."""
    db, tournoi_id, depart_id, archers = _contexte(tmp_path, 2)
    gagnant, perdant = archers
    depot = BarrageRepositorySQL(db.session_factory)
    ouvert = depot.ouvrir(_annonce(depart_id, archers))
    assert ouvert.id is not None
    depot.enregistrer_manche(
        ouvert.id,
        1,
        [
            TirBarrage(Participant.individuel(gagnant), 9),
            TirBarrage(Participant.individuel(perdant), 10),
        ],
    )

    ArcherRepositorySQL(db.session_factory).fusionner(gagnant, perdant)

    assert depot.par_tournoi(tournoi_id) == []


def test_reecrire_une_manche_tronque_les_suivantes(tmp_path: Path) -> None:
    """Corriger la manche 1 change la partition : les retirs qui en découlaient n'ont plus d'objet.

    Les conserver produisait un agrégat que le moteur refuse à la relecture, donc un classement en
    422 permanent.
    """
    db, tournoi_id, depart_id, archers = _contexte(tmp_path, 2)
    depot = BarrageRepositorySQL(db.session_factory)
    ouvert = depot.ouvrir(_annonce(depart_id, archers))
    assert ouvert.id is not None
    premier, second = (Participant.individuel(a) for a in archers)
    depot.enregistrer_manche(ouvert.id, 1, [TirBarrage(premier, 9), TirBarrage(second, 9)])
    depot.enregistrer_manche(ouvert.id, 2, [TirBarrage(premier, 8), TirBarrage(second, 10)])

    corrige = depot.enregistrer_manche(
        ouvert.id, 1, [TirBarrage(premier, 10), TirBarrage(second, 8)]
    )

    assert len(corrige.manches) == 1
    assert corrige.resultat().ordre == (premier, second)


def test_supprimer_un_barrage_efface_ses_tirs(tmp_path: Path) -> None:
    db, tournoi_id, depart_id, archers = _contexte(tmp_path, 2)
    depot = BarrageRepositorySQL(db.session_factory)
    ouvert = depot.ouvrir(_annonce(depart_id, archers))
    assert ouvert.id is not None
    premier, second = (Participant.individuel(a) for a in archers)
    depot.enregistrer_manche(ouvert.id, 1, [TirBarrage(premier, 9), TirBarrage(second, 10)])

    depot.supprimer(ouvert.id)

    assert depot.par_id(ouvert.id) is None
    assert depot.par_tournoi(tournoi_id) == []


def test_fusionner_preserve_un_barrage_qui_se_relit_encore(tmp_path: Path) -> None:
    """La suppression ne doit frapper que ce qui **ne se relit plus**.

    Une première version supprimait le barrage dès que la fusion touchait deux de ses participants
    — ce qui détruisait aussi des cas parfaitement sains : à une seule manche, le report des tirs
    produit un agrégat relisible. L'organisateur nettoyait un doublon d'inscription, geste de
    routine, et un barrage tiré et acté sur la dernière place qualificative disparaissait sans
    trace, le classement revenant silencieusement au rang partagé.
    """
    db, tournoi_id, depart_id, archers = _contexte(tmp_path, 3)
    gagnant, perdant, tiers = archers
    depot = BarrageRepositorySQL(db.session_factory)
    ouvert = depot.ouvrir(_annonce(depart_id, archers))
    assert ouvert.id is not None
    depot.enregistrer_manche(
        ouvert.id,
        1,
        [
            TirBarrage(Participant.individuel(gagnant), 10),
            TirBarrage(Participant.individuel(perdant), 9),
            TirBarrage(Participant.individuel(tiers), 8),
        ],
    )

    ArcherRepositorySQL(db.session_factory).fusionner(gagnant, perdant)

    relu = depot.par_tournoi(tournoi_id)
    assert len(relu) == 1, "un barrage encore relisible ne doit pas être détruit"
    assert relu[0].participants == (
        Participant.individuel(gagnant),
        Participant.individuel(tiers),
    )
    assert relu[0].resultat().est_resolu


def test_fusionner_supprime_un_barrage_devenu_illisible(tmp_path: Path) -> None:
    """…mais un agrégat que le moteur refuse doit bien partir : sinon chaque lecture lèverait."""
    db, tournoi_id, depart_id, archers = _contexte(tmp_path, 3)
    gagnant, perdant, tiers = archers
    depot = BarrageRepositorySQL(db.session_factory)
    ouvert = depot.ouvrir(_annonce(depart_id, archers))
    assert ouvert.id is not None
    depot.enregistrer_manche(
        ouvert.id,
        1,
        [
            TirBarrage(Participant.individuel(gagnant), 10),
            TirBarrage(Participant.individuel(perdant), 8),
            TirBarrage(Participant.individuel(tiers), 8),
        ],
    )
    depot.enregistrer_manche(
        ouvert.id,
        2,
        [
            TirBarrage(Participant.individuel(perdant), 9),
            TirBarrage(Participant.individuel(tiers), 7),
        ],
    )

    ArcherRepositorySQL(db.session_factory).fusionner(gagnant, perdant)

    assert depot.par_tournoi(tournoi_id) == []
