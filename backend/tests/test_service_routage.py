"""Tests du service `ServiceRoutage` (E04US018) — repositories factices.

Ici vit la règle métier du **panneau de routage** : « où est-ce que je tire ensuite ? ». Les cas
dérivent du CA d'E04US018 (`stories/E04-saisie-scores.md`) — écrits **avant** l'implémentation
(règle 9) :

- « pour **chaque** archer de la cible, sa **prochaine affectation** (cible, position, tour) » ;
- « ou son **rang final** s'il est éliminé » ;
- « l'affichage est **instantané** — **rien n'est calculé à cet instant** » (`D-08`) : le routage
  est une **lecture pure**, il ne place pas, ne trace pas, n'écrit rien ;
- et, arbitré au cadrage du 30/07/2026, **ce qui n'est pas encore connu est nommé** plutôt que
  masqué (`P-3`, comme le `blocage` du feu vert d'E12US002) : la cible d'un tour ≥ 2 (E05US010 non
  livrée), le rang intermédiaire (E06US004), l'adversaire pas encore sorti de son duel amont.

Le monde est celui d'E12US002 (`test_service_pilotage_tour`) : mêmes services composés sur des
repositories en mémoire, classement **vrai** sur des séries semées — le routage lit exactement ce
que le pilotage lit (le tableau reconstruit + le plan de duels persisté).
"""

from __future__ import annotations

from dataclasses import replace

from application.classements import ServiceClassement
from application.placement_duels import ServicePlacementDuels
from application.routage import IssueRoutage, ServiceRoutage
from application.saisie_duels import ServiceSaisieDuels
from domain.archer import Archer
from domain.blason import Blason, ZoneScore
from domain.categorie import Categorie
from domain.duel import ResolveurBaremeDuelFfta
from domain.gabarit_salle import GabaritSalle
from domain.inscription import Inscription
from domain.phase import Phase, TypePhase
from domain.politiques import ByesAuxMieuxClasses, EliminationSeche, SeedingSerpent
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxForfaitRepository,
    FauxInscriptionRepository,
)
from tests.test_service_placement_duels import (
    FauxBlasonRepository,
    FauxGabaritRepository,
    FauxPhaseRepository,
    FauxPlacementTableauRepository,
    FauxSerieRepository,
    FauxTournoiRepository,
)
from tests.test_service_saisie_duels import ZONES_TRIPLE, FauxDuelRepository


class _Monde:
    """Décor : un tournoi, un gabarit, une catégorie, N archers classés, une phase de tableau."""

    def __init__(self, capacites: tuple[int, ...] = (4, 4)) -> None:
        self.tournoi_id = 1
        self.tournois = FauxTournoiRepository({1})
        self.phases = FauxPhaseRepository()
        self.gabarits = FauxGabaritRepository()
        self.inscriptions = FauxInscriptionRepository()
        self.archers = FauxArcherRepository()
        self.categories = FauxCategorieRepository()
        self.blasons = FauxBlasonRepository()
        self.series = FauxSerieRepository()
        self.forfaits = FauxForfaitRepository()
        self.placements = FauxPlacementTableauRepository()
        self.duels = FauxDuelRepository()
        self.gabarits.ajouter(
            GabaritSalle(nom="Salle", capacites=capacites, tournoi_id=self.tournoi_id)
        )
        blason = self.blasons.ajouter(Blason.creer(self.tournoi_id, "B", taille=0.25, capacite=1))
        assert blason.id is not None
        self.blasons._blasons[blason.id] = replace(blason, zones=ZONES_TRIPLE)
        categorie = self.categories.ajouter(
            Categorie.creer(
                self.tournoi_id, "Cat", arme="Arc Classique", blason_id=blason.id, hauteur_cm=130
            )
        )
        assert categorie.id is not None
        self.categorie_id = categorie.id
        self.depart_id = 1
        self.phase_id: int | None = None

    def creer_phase_tableau(self) -> int:
        phase = self.phases.ajouter(Phase.creer(self.tournoi_id, 2, TypePhase.ELIMINATION_DIRECTE))
        assert phase.id is not None
        self.phase_id = phase.id
        return phase.id

    def inscrire_classe(self, valeurs: tuple[str, ...]) -> int:
        archer = self.archers.ajouter(
            Archer(nom="N", prenom="P", tournoi_id=self.tournoi_id, categorie_id=self.categorie_id)
        )
        assert archer.id is not None
        inscription = self.inscriptions.ajouter(
            Inscription(archer_id=archer.id, depart_id=self.depart_id)
        )
        assert inscription.id is not None
        self.series.semer(self.tournoi_id, archer.id, tuple(ZoneScore(v) for v in valeurs))
        return archer.id

    def _classement(self) -> ServiceClassement:
        return ServiceClassement(
            self.tournois, self.archers, self.series, self.categories, self.phases, self.forfaits
        )

    @property
    def saisie(self) -> ServiceSaisieDuels:
        return ServiceSaisieDuels(
            self.tournois,
            self.phases,
            self.categories,
            self.blasons,
            self.duels,
            self.forfaits,
            self._classement(),
            ResolveurBaremeDuelFfta(),
            SeedingSerpent(),
            ByesAuxMieuxClasses(),
            EliminationSeche(),
        )

    @property
    def placement(self) -> ServicePlacementDuels:
        return ServicePlacementDuels(
            self.tournois,
            self.phases,
            self.gabarits,
            self.inscriptions,
            self.archers,
            self.categories,
            self.blasons,
            self.placements,
            self._classement(),
            SeedingSerpent(),
            ByesAuxMieuxClasses(),
            EliminationSeche(),
        )

    @property
    def routage(self) -> ServiceRoutage:
        return ServiceRoutage(self.saisie, self.placement, self.phases)

    def placer(self) -> None:
        """Matérialise le plan de duels du 1er tour (les duellistes reçoivent cible et position)."""
        assert self.phase_id is not None
        self.placement.regenerer(self.tournoi_id, self.phase_id)

    def gagner(self, numero: int) -> None:
        """Fait gagner 6-0 le camp **haut** du match `numero` (3 manches) puis valide."""
        assert self.phase_id is not None
        saisie = self.saisie
        for manche in (1, 2, 3):
            saisie.saisir_manche(
                self.tournoi_id,
                self.phase_id,
                numero,
                manche,
                (ZoneScore.DIX,) * 3,
                (ZoneScore.SIX,) * 3,
            )
        saisie.valider(self.tournoi_id, self.phase_id, numero, "DURAND")

    def gagne_de(self, numero: int) -> int:
        """L'`archer_id` du camp **haut** du match `numero` — celui que `gagner` fait gagner."""
        assert self.phase_id is not None
        tableau, _ = self.saisie.reconstruire(self.tournoi_id, self.phase_id)
        haut = tableau.match(numero).haut
        assert haut is not None
        return haut.ref_id

    def perd_de(self, numero: int) -> int:
        """L'`archer_id` du camp **bas** du match `numero` — celui que `gagner` fait perdre."""
        assert self.phase_id is not None
        tableau, _ = self.saisie.reconstruire(self.tournoi_id, self.phase_id)
        bas = tableau.match(numero).bas
        assert bas is not None
        return bas.ref_id


def _quatre(monde: _Monde) -> list[int]:
    """Quatre archers aux totaux décroissants → rangs scratch 1..4, puis la phase de tableau."""
    archers = [monde.inscrire_classe(v) for v in (("10", "10"), ("9", "9"), ("8", "8"), ("7", "7"))]
    monde.creer_phase_tableau()
    return archers


def _huit(monde: _Monde) -> list[int]:
    """Huit archers → tableau de 8 (quarts, demies, finale) : le seul effectif où un battu est
    **réellement** éliminé. À quatre, le perdant d'une demie va en petite finale — il a encore un
    duel devant lui."""
    totaux = (
        ("10", "10"),
        ("10", "9"),
        ("9", "9"),
        ("9", "8"),
        ("8", "8"),
        ("8", "7"),
        ("7", "7"),
        ("7", "6"),
    )
    archers = [monde.inscrire_classe(v) for v in totaux]
    monde.creer_phase_tableau()
    return archers


# --- CA « sa prochaine affectation (cible, position, tour) » ------------------------------------


def test_chaque_archer_de_la_cible_voit_son_prochain_duel() -> None:
    """CA : « pour **chaque** archer de la cible, sa prochaine affectation ». Sortie de qualif, le
    panneau du poste route ses quatre archers vers leur duel de 1er tour : cible, position, tour et
    adversaire — tout est connu **avant** que le duel se joue (les cibles sont attribuées aux
    *matchs*, note du CA)."""
    monde = _Monde()
    archers = _quatre(monde)
    monde.placer()

    routage = monde.routage.routage(monde.tournoi_id, tuple(archers))

    assert [r.archer_id for r in routage.archers] == archers  # l'ordre demandé est conservé
    for ligne in routage.archers:
        assert ligne.issue is IssueRoutage.PROCHAIN_DUEL
        assert ligne.prochain is not None
        assert ligne.prochain.tour == 1
        assert ligne.prochain.libelle == "Demi-finale"  # tableau de 4 : le tour 1 est la demie
        assert ligne.prochain.cible is not None
        assert ligne.prochain.position in {"A", "B", "C", "D"}
        assert ligne.prochain.adversaire is not None
        assert ligne.prochain.manque is None


def test_le_vainqueur_est_route_vers_le_tour_suivant() -> None:
    """CA : la prochaine affectation **suit** l'archer. Le duel validé, son vainqueur a un nouveau
    rendez-vous (la finale) — c'est le geste que le panneau accompagne côté duels."""
    monde = _Monde()
    _quatre(monde)
    monde.placer()
    vainqueur = monde.gagne_de(1)
    monde.gagner(1)

    ligne = monde.routage.routage(monde.tournoi_id, (vainqueur,)).archers[0]

    assert ligne.issue is IssueRoutage.PROCHAIN_DUEL
    assert ligne.prochain is not None
    assert ligne.prochain.tour == 2
    assert ligne.prochain.libelle == "Finale"


def test_l_exempt_est_route_directement_au_tour_deux() -> None:
    """Un archer dispensé du 1er tour (bye) n'a pas de duel à disputer là où il est « inscrit » :
    son prochain rendez-vous est le tour 2. Sans ce cas, le panneau enverrait la tête de série sur
    un match gagné d'office."""
    monde = _Monde()
    archers = [monde.inscrire_classe(v) for v in (("10", "10"), ("9", "9"), ("8", "8"))]
    monde.creer_phase_tableau()
    monde.placer()

    ligne = monde.routage.routage(monde.tournoi_id, (archers[0],)).archers[0]

    assert ligne.issue is IssueRoutage.PROCHAIN_DUEL
    assert ligne.prochain is not None
    assert ligne.prochain.tour == 2


# --- Ce qui n'est pas encore connu est **nommé** (arbitrage de cadrage du 30/07/2026) -----------


def test_pas_de_cible_au_dela_du_premier_tour_et_le_manque_est_nomme() -> None:
    """Le placement ne pose que le **1er tour** (ADR-0048 ; l'intégral 1→N est E05US010). Le duel
    suivant n'a donc **aucune** cible — et surtout pas celle du tour 1, qui serait **périmée** et
    enverrait le finaliste sur son ancienne butte. Le panneau dit que la cible viendra."""
    monde = _Monde()
    _quatre(monde)
    monde.placer()
    vainqueur = monde.gagne_de(1)
    monde.gagner(1)

    ligne = monde.routage.routage(monde.tournoi_id, (vainqueur,)).archers[0]

    assert ligne.prochain is not None
    assert ligne.prochain.cible is None
    assert ligne.prochain.position is None
    assert ligne.prochain.manque is not None and "cible" in ligne.prochain.manque.lower()


def test_adversaire_pas_encore_connu_nomme_le_duel_attendu() -> None:
    """Le vainqueur du demi n°1 ne sait pas encore qui il affrontera : le panneau **nomme** la
    source attendue (« en attente du duel n°2 ») plutôt que d'afficher un blanc."""
    monde = _Monde()
    _quatre(monde)
    monde.placer()
    vainqueur = monde.gagne_de(1)
    monde.gagner(1)

    ligne = monde.routage.routage(monde.tournoi_id, (vainqueur,)).archers[0]

    assert ligne.prochain is not None
    assert ligne.prochain.adversaire is None
    assert ligne.prochain.sources_en_attente == (2,)


def test_sans_plan_de_duels_la_cible_manque_sans_faire_echouer_le_panneau() -> None:
    """`P-3` : le panneau **montre**, il n'empêche rien. Sans plan de duels matérialisé, le duel
    existe (l'appariement se recalcule du classement) mais la cible n'est pas attribuée."""
    monde = _Monde()
    archers = _quatre(monde)
    # pas de `placer()`

    ligne = monde.routage.routage(monde.tournoi_id, (archers[0],)).archers[0]

    assert ligne.issue is IssueRoutage.PROCHAIN_DUEL
    assert ligne.prochain is not None
    assert ligne.prochain.cible is None
    assert ligne.prochain.manque is not None


# --- CA « son rang final s'il est éliminé » ----------------------------------------------------


def test_l_elimine_sort_du_tableau_et_son_tour_de_sortie_est_nomme() -> None:
    """CA : l'archer éliminé n'a plus de prochaine affectation. Son **rang final** n'est pas encore
    publiable — l'agrégation des rangs de tableau est E06US004 — donc le panneau dit *où* il est
    sorti et **annonce** le rang à venir plutôt que d'inventer un chiffre."""
    monde = _Monde()
    _huit(monde)
    monde.placer()
    perdant = monde.perd_de(1)
    monde.gagner(1)

    ligne = monde.routage.routage(monde.tournoi_id, (perdant,)).archers[0]

    assert ligne.issue is IssueRoutage.TERMINE
    assert ligne.prochain is None
    assert ligne.rang_final is None
    assert ligne.tour_sortie == "Quart de finale"
    assert ligne.motif is not None


def test_rang_final_publie_quand_le_podium_est_acquis() -> None:
    """CA « son rang final » : une fois finale et petite finale jouées, les quatre archers portent
    leur rang de podium (1-4) — le seul rang que le tableau sache attribuer aujourd'hui."""
    monde = _Monde()
    archers = _quatre(monde)
    monde.placer()
    monde.gagner(1)
    monde.gagner(2)
    tableau, _ = monde.saisie.reconstruire(monde.tournoi_id, monde.phase_id or 0)
    petite = tableau.petite_finale
    assert petite is not None
    monde.gagner(tableau.finale.numero)
    monde.gagner(petite.numero)

    routage = monde.routage.routage(monde.tournoi_id, tuple(archers))

    rangs = {r.archer_id: r.rang_final for r in routage.archers}
    assert sorted(rang for rang in rangs.values() if rang is not None) == [1, 2, 3, 4]
    assert all(r.issue is IssueRoutage.TERMINE and r.prochain is None for r in routage.archers)


# --- Ce que le panneau ne sait pas router ------------------------------------------------------


def test_sans_phase_de_tableau_le_panneau_le_dit() -> None:
    """Un tournoi dont la phase finale n'est pas configurée : le panneau ne peut router personne et
    **le nomme**, plutôt que de rendre une liste vide qu'on prendrait pour une panne."""
    monde = _Monde()
    archer = monde.inscrire_classe(("10", "10"))
    monde.inscrire_classe(("9", "9"))
    # aucune phase ELIMINATION_DIRECTE créée

    routage = monde.routage.routage(monde.tournoi_id, (archer,))

    assert routage.phase_id is None
    ligne = routage.archers[0]
    assert ligne.issue is IssueRoutage.INDISPONIBLE
    assert ligne.motif is not None


def test_archer_absent_du_tableau_le_panneau_le_dit() -> None:
    """Un archer qui n'a pas de place dans le tableau (identifiant inconnu du classement) : ni
    prochain duel ni rang — le panneau l'annonce au lieu d'échouer sur la ligne des autres."""
    monde = _Monde()
    archers = _quatre(monde)
    monde.placer()

    routage = monde.routage.routage(monde.tournoi_id, (archers[0], 9999))

    assert routage.archers[0].issue is IssueRoutage.PROCHAIN_DUEL
    assert routage.archers[1].issue is IssueRoutage.INDISPONIBLE
    assert routage.archers[1].motif is not None


# --- CA « rien n'est calculé à cet instant » (`D-08`) ------------------------------------------


def test_le_routage_est_une_lecture_pure() -> None:
    """`D-08` : l'affichage est **instantané** parce que **rien n'est calculé** au moment de la
    bascule — le placement est déjà posé, la progression déjà propagée. Deux appels successifs
    rendent le même résultat et **aucune écriture** n'a lieu (ni placement, ni duel)."""
    monde = _Monde()
    archers = _quatre(monde)
    monde.placer()
    poses_avant = len(monde.placements.par_phase(monde.phase_id or 0))
    duels_avant = len(monde.duels._tirs)

    premier = monde.routage.routage(monde.tournoi_id, tuple(archers))
    second = monde.routage.routage(monde.tournoi_id, tuple(archers))

    assert premier == second
    assert len(monde.placements.par_phase(monde.phase_id or 0)) == poses_avant
    assert len(monde.duels._tirs) == duels_avant
