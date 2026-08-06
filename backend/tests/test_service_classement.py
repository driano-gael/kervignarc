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
from application.erreurs import DepartIntrouvable
from domain.archer import Archer, ArcherId
from domain.blason import ZoneScore
from domain.categorie import Categorie
from domain.depart import Depart
from domain.entree_audit import EntreeAudit
from domain.inscription import Inscription
from domain.serie import Serie, Volee
from domain.tournoi import Tournoi, TournoiId
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxDepartRepository,
    FauxForfaitRepository,
    FauxInscriptionRepository,
    FauxPhaseRepository,
)

_DATE = datetime.date(2026, 3, 14)

# Le créneau du décor : premier départ créé, donc identifiant 1 (la doublure alloue en séquence).
_DEPART_ID = 1


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
    # Le classement est celui **d'un départ** (ADR-0075) : le décor lui donne son créneau, et y
    # inscrit les trois archers — c'est l'inscription qui dit qui tire ici, pas `Archer.tournoi_id`.
    departs = FauxDepartRepository()
    depart = departs.ajouter(
        Depart.creer(tournoi_id=1, numero=1, tarif_centimes=800, horaire="09:00")
    )
    assert depart.id is not None
    inscriptions = FauxInscriptionRepository()
    for archer_id in (alice.id, bob.id, chloe.id):
        inscriptions.ajouter(Inscription.creer(archer_id, depart.id))
    return ServiceClassement(
        tournois,
        archers,
        series,
        categories,
        FauxPhaseRepository(departs),
        FauxForfaitRepository(),
        departs,
        inscriptions,
    )


def test_depart_inconnu_leve_depart_introuvable() -> None:
    """Un créneau inexistant ne rend pas un classement vide : il lève une erreur métier.

    ⚠️ **L'erreur a changé avec la portée** (E01US025, ADR-0075) : c'était `TournoiIntrouvable`,
    c'est désormais `DepartIntrouvable`, parce que l'identifiant reçu désigne un départ. Le contrat
    « on ne rend pas un classement vide pour une entité inconnue » est, lui, inchangé — c'est lui
    que ce test protège.
    """
    with pytest.raises(DepartIntrouvable):
        _service().pour_depart(999)


def test_sans_filtre_le_classement_couvre_toutes_les_categories() -> None:
    """`categorie_id=None` → tous les archers, dans l'ordre scratch (meilleur total d'abord)."""
    lignes = _service().pour_depart(_DEPART_ID).lignes
    assert [(ligne.nom, ligne.rang_scratch) for ligne in lignes] == [
        ("Durand", 1),
        ("Martin", 2),
        ("Petit", 3),
    ]


def test_filtre_par_categorie_ne_garde_que_ses_archers_sans_recalculer_les_rangs() -> None:
    """CA catégorie : filtrer à la catégorie 1 ne garde qu'Alice et Chloé, mais leurs rangs restent
    ceux du classement complet — scratch **global** (2 et 3), catégorie **repart de 1** (1 et 2)."""
    lignes = _service().pour_depart(_DEPART_ID, categorie_id=1).lignes
    assert [(ligne.nom, ligne.rang_scratch, ligne.rang_categorie) for ligne in lignes] == [
        ("Martin", 2, 1),
        ("Petit", 3, 2),
    ]
