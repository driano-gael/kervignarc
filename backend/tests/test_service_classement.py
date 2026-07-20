"""Tests du service applicatif `ServiceClassement` (E06US001).

Le calcul (cumul, départage, rangs) est couvert exhaustivement au domaine
(`test_domain_classement.py`). Ici on teste ce que le **service** ajoute, depuis le CA :

- il refuse un tournoi inconnu (`TournoiIntrouvable`) ;
- `categorie_id` **filtre** l'affichage à une catégorie **sans** recalculer les rangs (le CA veut
  « voir une catégorie » sans perdre la position d'ensemble : le rang scratch reste global).

Fakes en mémoire plutôt que la base : le service n'orchestre que des ports. `FauxArcherRepository`
et `FauxCategorieRepository` (complets) viennent de `conftest` ; les doubles de tournoi et de série
sont locaux, réduits à ce que le service lit (le reste ne fait que **conformer** le port).
"""

from __future__ import annotations

import datetime

import pytest

from application.classements import ServiceClassement
from application.erreurs import TournoiIntrouvable
from domain.archer import Archer, ArcherId
from domain.blason import ZoneScore
from domain.categorie import Categorie
from domain.entree_audit import EntreeAudit
from domain.serie import Serie, Volee
from domain.tournoi import Tournoi, TournoiId
from tests.conftest import FauxArcherRepository, FauxCategorieRepository

_DATE = datetime.date(2026, 3, 14)


class FauxTournoiRepository:
    """Double de `TournoiRepository` : seul `par_id` importe au classement (reste = conformité)."""

    def __init__(self, ids: set[int]) -> None:
        self._ids = ids

    def par_id(self, tournoi_id: TournoiId) -> Tournoi | None:
        # Le service ne teste que la non-nullité (le tournoi existe-t-il ?) : une instance suffit.
        return Tournoi.creer("Salle 18m", _DATE) if tournoi_id in self._ids else None

    def ajouter(self, tournoi: Tournoi) -> Tournoi:
        raise NotImplementedError

    def lister(self) -> list[Tournoi]:
        raise NotImplementedError

    def enregistrer(self, tournoi: Tournoi) -> Tournoi:
        raise NotImplementedError

    def supprimer(self, tournoi_id: TournoiId) -> None:
        raise NotImplementedError


class FauxSerieRepository:
    """Double de `SerieRepository` : seul `par_tournoi` sert au classement (reste = conformité)."""

    def __init__(self, series: list[Serie]) -> None:
        self._series = series

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Serie]:
        return [s for s in self._series if s.tournoi_id == tournoi_id]

    def par_archer(self, tournoi_id: TournoiId, archer_id: ArcherId) -> Serie | None:
        raise NotImplementedError

    def horodatages(
        self, tournoi_id: TournoiId, archer_id: ArcherId
    ) -> dict[int, datetime.datetime]:
        raise NotImplementedError

    def enregistrer(self, serie: Serie) -> Serie:
        raise NotImplementedError

    def enregistrer_avec_trace(self, serie: Serie, entree: EntreeAudit) -> Serie:
        raise NotImplementedError


def _serie(archer_id: int, valeurs: tuple[ZoneScore, ...]) -> Serie:
    return Serie(
        tournoi_id=1,
        archer_id=archer_id,
        volees=(Volee(numero=1, valeurs=valeurs, validee_par="Scoreur"),),
    )


def _service() -> ServiceClassement:
    # Trois archers, deux catégories : Bob (cat 2) domine au scratch ; Alice puis Chloé en cat 1.
    tournois = FauxTournoiRepository({1})
    archers = FauxArcherRepository()
    categories = FauxCategorieRepository()
    cat_1 = categories.ajouter(Categorie.creer(1, "Senior Homme"))
    cat_2 = categories.ajouter(Categorie.creer(1, "Cadet"))
    assert cat_1.id is not None and cat_2.id is not None
    alice = archers.ajouter(Archer.creer("Martin", "Alice", 1, cat_1.id))
    bob = archers.ajouter(Archer.creer("Durand", "Bob", 1, cat_2.id))
    chloe = archers.ajouter(Archer.creer("Petit", "Chloé", 1, cat_1.id))
    assert alice.id is not None and bob.id is not None and chloe.id is not None
    series = FauxSerieRepository(
        [
            _serie(alice.id, (ZoneScore.NEUF, ZoneScore.NEUF)),  # 18
            _serie(bob.id, (ZoneScore.DIX, ZoneScore.DIX)),  # 20
            _serie(chloe.id, (ZoneScore.HUIT, ZoneScore.HUIT)),  # 16
        ]
    )
    return ServiceClassement(tournois, archers, series, categories)


def test_tournoi_inconnu_leve_tournoi_introuvable() -> None:
    """Un tournoi inexistant ne rend pas un classement vide : il lève une erreur métier."""
    with pytest.raises(TournoiIntrouvable):
        _service().pour_tournoi(999)


def test_sans_filtre_le_classement_couvre_toutes_les_categories() -> None:
    """`categorie_id=None` → tous les archers, dans l'ordre scratch (meilleur total d'abord)."""
    lignes = _service().pour_tournoi(1).lignes
    assert [(ligne.nom, ligne.rang_scratch) for ligne in lignes] == [
        ("Durand", 1),
        ("Martin", 2),
        ("Petit", 3),
    ]


def test_filtre_par_categorie_ne_garde_que_ses_archers_sans_recalculer_les_rangs() -> None:
    """CA catégorie : filtrer à la catégorie 1 ne garde qu'Alice et Chloé, mais leurs rangs restent
    ceux du classement complet — scratch **global** (2 et 3), catégorie **repart de 1** (1 et 2)."""
    lignes = _service().pour_tournoi(1, categorie_id=1).lignes
    assert [(ligne.nom, ligne.rang_scratch, ligne.rang_categorie) for ligne in lignes] == [
        ("Martin", 2, 1),
        ("Petit", 3, 2),
    ]
