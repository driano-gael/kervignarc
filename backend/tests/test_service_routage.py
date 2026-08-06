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

import datetime
from dataclasses import replace

import pytest

from application.classements import ServiceClassement
from application.erreurs import PhaseIntrouvable
from application.placement_duels import ServicePlacementDuels
from application.routage import (
    CIBLE_A_VENIR,
    CIBLE_NON_ATTRIBUEE,
    PLACEMENT_AUTRE_CIBLE,
    IssueRoutage,
    ServiceRoutage,
)
from application.saisie_duels import ServiceSaisieDuels
from domain.archer import Archer
from domain.bareme import BaremeQualification
from domain.blason import Blason, ZoneScore
from domain.categorie import Categorie
from domain.depart import Depart
from domain.duel import ResolveurBaremeDuelFfta
from domain.forfait import Forfait, NatureForfait
from domain.gabarit_salle import GabaritSalle
from domain.grain_validation import GrainValidation
from domain.inscription import Inscription
from domain.participant import Participant
from domain.phase import Phase, StatutPhase, TypePhase
from domain.politiques import (
    RANGS_DU_PODIUM,
    ByesAuxMieuxClasses,
    PlacementEnCascade,
    ProfondeurClassement,
    Routing,
    SeedingSerpent,
    registre_par_defaut,
)
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxDepartRepository,
    FauxForfaitRepository,
    FauxInscriptionRepository,
    FauxPhaseRepository,
)
from tests.test_service_placement_duels import (
    FauxBlasonRepository,
    FauxGabaritRepository,
    FauxPlacementTableauRepository,
    FauxSerieRepository,
    FauxTournoiRepository,
)
from tests.test_service_saisie_duels import ZONES_TRIPLE, FauxDuelRepository

_QUAND = datetime.datetime(2026, 3, 14, 14, 20, tzinfo=datetime.UTC)

_REGISTRE = registre_par_defaut()

_CASCADE = PlacementEnCascade()
_PODIUM = ProfondeurClassement.top(RANGS_DU_PODIUM)
"""Le routing par défaut du décor, en **singleton de module** : `ruff` refuse un appel de fonction
en argument par défaut (`B008`). Sans risque ici — les politiques sont des dataclasses `frozen`,
donc un exemplaire partagé ne peut garder aucun état d'un test à l'autre."""


class _Monde:
    """Décor : un tournoi, un gabarit, une catégorie, N archers classés, une phase de tableau.

    `routing` est **injectable** parce qu'un format de tournoi est de la configuration, pas du code
    (règle 2) : E07US008 s'en sert pour monter un décor à **repêchage** sans dupliquer ce décor.
    """

    def __init__(
        self,
        capacites: tuple[int, ...] = (4, 4),
        routing: Routing = _CASCADE,
        profondeur: ProfondeurClassement | None = _PODIUM,
    ) -> None:
        self.routing = routing
        # Injectable pour la même raison que `routing` : la **profondeur** décide s'il y a un
        # match pour la 3ᵉ place (E06US004 s'en sert pour montrer qu'un tournoi sans petite
        # finale n'a pas de bronze). Depuis E06US006 elle est portée **par la phase** et non plus
        # par le service : le décor la pose donc sur la phase de tableau qu'il crée.
        #
        # `None` est une valeur **utile** et non un défaut : elle laisse la phase **non réglée**,
        # seul moyen d'exercer de bout en bout le repli sur le preset du type (ADR-0070 §3).
        self.profondeur = profondeur
        self.tournoi_id = 1
        self.tournois = FauxTournoiRepository({1})
        # Créneau et inscriptions : le classement dont dérive ce décor est celui d'un départ.
        self.departs = FauxDepartRepository()
        _d = self.departs.ajouter(
            Depart.creer(tournoi_id=1, numero=1, tarif_centimes=800, horaire="09:00")
        )
        assert _d.id is not None
        self.depart_id = _d.id
        self.phases = FauxPhaseRepository(self.departs)
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
        phase = self.phases.ajouter(
            Phase.creer(
                self.tournoi_id,
                2,
                TypePhase.ELIMINATION_DIRECTE,
                profondeur=self.profondeur,
            )
        )
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
            self.tournois,
            self.archers,
            self.series,
            self.categories,
            self.phases,
            self.forfaits,
            self.departs,
            self.inscriptions,
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
            self.routing,
            _REGISTRE,
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
            self.routing,
            _REGISTRE,
        )

    @property
    def routage(self) -> ServiceRoutage:
        return ServiceRoutage(self.saisie, self.placement, self.archers, self.phases)

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

    def reclasser(self, archer_id: int, valeurs: tuple[str, ...]) -> None:
        """Rejoue le score d'un archer : le **classement bouge**, donc l'appariement aussi.

        C'est le geste réel d'une correction de score (E04US013) : l'arbre est **recalculé** à
        chaque lecture (ADR-0023) tandis que le plan de duels reste **persisté**.
        """
        self.series._series = [
            serie for serie in self.series._series if serie.archer_id != archer_id
        ]
        self.series.semer(self.tournoi_id, archer_id, tuple(ZoneScore(v) for v in valeurs))

    def poses(self) -> dict[int, tuple[int, str]]:
        """`archer_id → (cible, position)` **tel que le plan de duels persisté le dit** — la source
        indépendante contre laquelle on croise ce que le panneau annonce."""
        assert self.phase_id is not None
        plan = self.placement.plan_de_duels(self.tournoi_id, self.phase_id)
        return {
            pose.archer_id: (cible.index, pose.position)
            for cible in plan.cibles
            for pose in cible.placements
        }

    def adversaire_de(self, archer_id: int) -> int:
        """L'`archer_id` que **l'arbre** oppose à celui-ci au tour 1 (source indépendante)."""
        assert self.phase_id is not None
        tableau, _ = self.saisie.reconstruire(self.tournoi_id, self.phase_id)
        moi = Participant.individuel(archer_id)
        for match in tableau.matchs:
            if match.tour != 1 or moi not in (match.haut, match.bas):
                continue
            autre = match.bas if match.haut == moi else match.haut
            assert autre is not None
            return autre.ref_id
        raise AssertionError(f"L'archer {archer_id} n'a pas de duel au tour 1.")


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

    poses = monde.poses()  # source indépendante : le plan de duels persisté
    routage = monde.routage.routage(monde.tournoi_id, tuple(archers))

    assert [r.archer_id for r in routage.archers] == archers  # l'ordre demandé est conservé
    for ligne in routage.archers:
        assert ligne.issue is IssueRoutage.PROCHAIN_DUEL
        assert ligne.prochain is not None
        assert ligne.prochain.tour == 1
        assert ligne.prochain.libelle == "Demi-finale"  # tableau de 4 : le tour 1 est la demie
        assert ligne.prochain.manque is None
        # On croise avec les **sources**, pas avec « ce n'est pas None » : une permutation des
        # poses, ou un panneau qui renverrait l'archer lui-même comme adversaire, passeraient une
        # assertion de non-nullité — et enverraient un archer sur la mauvaise butte le jour J.
        assert (ligne.prochain.cible, ligne.prochain.position) == poses[ligne.archer_id]
        assert ligne.prochain.adversaire is not None
        assert ligne.prochain.adversaire.archer_id == monde.adversaire_de(ligne.archer_id)
        assert ligne.prochain.adversaire.archer_id != ligne.archer_id
    # Les deux duellistes d'un même duel partagent leur cible (E03US009 les veut côte à côte).
    cibles = {r.archer_id: r.prochain.cible for r in routage.archers if r.prochain is not None}
    for ligne in routage.archers:
        assert cibles[ligne.archer_id] == cibles[monde.adversaire_de(ligne.archer_id)]


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
    # Égalité stricte, pas « contient le mot cible » : les trois motifs contiennent ce mot, et une
    # assertion lâche laisserait passer n'importe lequel des trois — donc ne prouverait rien.
    assert ligne.prochain.manque == CIBLE_A_VENIR
    assert ligne.prochain.alerte is None


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
    assert ligne.prochain.manque == CIBLE_NON_ATTRIBUEE  # neutre : rien n'est *promis* ici


# --- CA « son rang final s'il est éliminé » ----------------------------------------------------


def test_l_elimine_sort_du_tableau_et_son_tour_de_sortie_est_nomme() -> None:
    """CA : l'archer éliminé n'a plus de prochaine affectation. Son **rang final** n'est pas encore
    publiable — l'agrégation des rangs de tableau est E06US004 — donc le panneau dit *où* il est
    sorti et **quels rangs il a acquis**.

    ⚠️ **Attendu révisé par E07US008** (arbitrage du commanditaire, 02/08/2026), reversé au CA
    d'E04US018. Ce test exigeait auparavant `motif is not None` — « rang publié en fin de phase ».
    C'était vrai du code, pas du besoin : le battu d'un quart **est** 5ᵉ-8ᵉ *ex æquo*, aucun match
    ne départage les quatre battus des quarts, et cette fourchette était déjà lisible dans la plage
    du match. On l'annonce donc, et `rang_final` reste `None` — il n'y a pas de rang **exact** ici.
    """
    monde = _Monde()
    _huit(monde)
    monde.placer()
    perdant = monde.perd_de(1)
    monde.gagner(1)

    ligne = monde.routage.routage(monde.tournoi_id, (perdant,)).archers[0]

    assert ligne.issue is IssueRoutage.TERMINE
    assert ligne.prochain is None
    assert ligne.rang_final is None  # pas de rang exact : les quatre battus sont ex æquo
    assert (ligne.rang_min, ligne.rang_max) == (5, 8)
    assert ligne.tour_sortie == "Quart de finale"
    assert ligne.motif is None  # plus d'« en attente » : ce qui est acquis est dit


def test_le_battu_qui_descend_en_placement_lit_le_nom_de_sa_branche() -> None:
    """**Non-régression du correctif d'E07US005** — ce test rend vraie la promesse « un domicile
    unique, corrigé une fois, corrige toutes les surfaces ».

    En profondeur intégrale (E06US006), le battu d'un quart ne sort pas : il descend dans le
    sous-tableau des places 5-8, qui se dispute **au tour d'une demi-finale**. Ce match n'a pas de
    `place_en_jeu` (il n'est pas terminal), si bien que `libelle_tour` le nommait « Demi-finale » —
    et le panneau de routage annonçait donc une demi-finale à quelqu'un qui joue la 5ᵉ place.

    Le correctif a fait passer la **plage** à `libelle_tour` ; sans ce test, les deux lignes
    modifiées de `ServiceRoutage` n'étaient exercées par rien — aucun test de ce fichier ne tourne
    en profondeur intégrale, et un refactor qui retirerait l'argument ne casserait rien.
    """
    monde = _Monde(profondeur=ProfondeurClassement.integrale())
    _huit(monde)
    monde.placer()
    perdant = monde.perd_de(1)
    monde.gagner(1)

    ligne = monde.routage.routage(monde.tournoi_id, (perdant,)).archers[0]

    assert (
        ligne.issue is IssueRoutage.PROCHAIN_DUEL
    ), "sous profondeur intégrale, un battu tire encore"
    assert ligne.prochain is not None
    assert ligne.prochain.libelle == "Places 5 à 8"


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


def test_pose_perimee_par_un_reclassement_est_signalee() -> None:
    """Le plan de duels est **persisté**, l'appariement est **recalculé** (ADR-0023). Une correction
    de score suffit à les désaccorder : l'archer garde sa pose mais affronte désormais quelqu'un
    placé ailleurs. Le panneau **garde sa cible** — c'est bien sa place physique, la lui retirer
    serait échanger une information juste contre un vide — et **alerte** : c'est ce dont il a besoin
    pour ne pas partir en confiance. Le signal vient du domaine (`duels_separes`), pas d'un calcul
    refait ici."""
    monde = _Monde(capacites=(2, 2))  # un duel par cible : deux poses distinctes
    archers = _quatre(monde)
    monde.placer()
    avant = monde.routage.routage(monde.tournoi_id, (archers[0],)).archers[0].prochain
    assert avant is not None and avant.cible is not None  # sain au départ
    assert avant.alerte is None
    assert avant.adversaire is not None

    # Le 1er tombe au 2e rang : le serpent l'oppose maintenant au 3e, posé sur l'autre cible.
    monde.reclasser(archers[0], ("9", "8"))
    apres = monde.routage.routage(monde.tournoi_id, (archers[0],)).archers[0].prochain

    assert apres is not None
    assert apres.adversaire is not None
    assert apres.adversaire.archer_id != avant.adversaire.archer_id  # l'appariement a changé
    assert apres.cible == avant.cible  # sa place physique n'a pas bougé
    # Deux buttes différentes : la pose annoncée n'est **pas** là où le duel se tirera. Le panneau
    # nomme donc la cible de l'autre — c'est ce qui fait comprendre qu'il faut voir l'organisateur
    # plutôt que de s'installer. Un message générique laisserait partir sur la mauvaise butte.
    assert apres.alerte is not None and apres.alerte.startswith("placement à revoir")
    assert "cible" in apres.alerte
    assert apres.manque is None  # rien ne *manque* : c'est une alerte, pas un trou


def test_pose_perimee_meme_quand_les_deux_restent_sur_la_meme_cible() -> None:
    """Le cas que la comparaison « même index de cible » ratait — et c'est la disposition **la plus
    courante** (une cible de salle porte les quatre archers). Après reclassement, les deux
    duellistes
    sont toujours sur la même butte mais **plus côte à côte** : la position annoncée est périmée,
    l'archer se rangerait à côté du mauvais adversaire. Le signal du domaine, lui, le voit."""
    monde = _Monde(capacites=(4,))  # les quatre sur une seule cible
    archers = _quatre(monde)
    monde.placer()
    avant = monde.routage.routage(monde.tournoi_id, (archers[0],)).archers[0].prochain
    assert avant is not None and avant.alerte is None

    monde.reclasser(archers[0], ("9", "8"))
    apres = monde.routage.routage(monde.tournoi_id, (archers[0],)).archers[0].prochain

    assert apres is not None
    assert apres.cible == avant.cible  # même butte, forcément : il n'y en a qu'une
    # Même butte : la pose est le **bon** conseil, il n'y a qu'à se décaler d'une place. Le ton est
    # donc neutre — alarmer ici, ce serait confondre deux situations opposées.
    assert apres.alerte is not None
    assert apres.alerte.startswith("votre adversaire tire sur la même cible")
    assert not apres.alerte.startswith("placement à revoir")


def test_un_plan_sain_mais_separe_garde_sa_cible() -> None:
    """Des cibles à **une** place : le moteur ne *peut* pas mettre les duellistes côte à côte, et le
    placement l'**accepte** en le signalant (E03US009). Le plan est frais et correct — refuser
    d'annoncer la cible priverait tous les archers d'une information juste. On annonce, avec
    l'alerte : c'est le sens de « alerte » plutôt que « manque »."""
    monde = _Monde(capacites=(1, 1, 1, 1))
    archers = _quatre(monde)
    monde.placer()

    routage = monde.routage.routage(monde.tournoi_id, tuple(archers))

    for ligne in routage.archers:
        assert ligne.prochain is not None
        assert ligne.prochain.cible is not None  # la cible réelle, pas un vide
        assert ligne.prochain.alerte == PLACEMENT_AUTRE_CIBLE.format(
            cible=monde.poses()[monde.adversaire_de(ligne.archer_id)][0]
        )


def test_le_panneau_degrade_reste_nominatif() -> None:
    """Sans phase de tableau — l'état le plus fréquent de la journée — le panneau ne sait router
    personne, mais il sait encore dire **qui** est qui : quatre lignes anonymes et identiques
    seraient illisibles. Les noms viennent du classement, lisible sans phase de tableau."""
    monde = _Monde()
    archers = [monde.inscrire_classe(v) for v in (("10", "10"), ("9", "9"))]
    # aucune phase ELIMINATION_DIRECTE créée

    routage = monde.routage.routage(monde.tournoi_id, tuple(archers))

    assert all(ligne.issue is IssueRoutage.INDISPONIBLE for ligne in routage.archers)
    assert all(ligne.nom != "" for ligne in routage.archers)


def test_phase_imposee_introuvable_est_refusee() -> None:
    """Un `phase_id` **fourni par le client** est validé, comme partout ailleurs. Sans cette garde,
    un identifiant périmé (phase supprimée) rendrait un placide « phase finale non configurée » —
    l'écran afficherait une absence de configuration au lieu d'un vrai refus."""
    monde = _Monde()
    archers = _quatre(monde)

    with pytest.raises(PhaseIntrouvable):
        monde.routage.routage(monde.tournoi_id, (archers[0],), phase_id=9999)


def test_phase_imposee_d_un_autre_tournoi_est_refusee() -> None:
    """La moitié la plus sensible de la garde : la route est **publique et non authentifiée**, un
    `phase_id` d'un autre tournoi ne doit pas ouvrir son arbre par l'URL de celui-ci."""
    monde = _Monde()
    archers = _quatre(monde)
    autre = monde.phases.ajouter(
        Phase.creer(depart_id=42, ordre=2, type=TypePhase.ELIMINATION_DIRECTE)
    )
    assert autre.id is not None

    with pytest.raises(PhaseIntrouvable):
        monde.routage.routage(monde.tournoi_id, (archers[0],), phase_id=autre.id)


def test_la_phase_visee_est_le_tableau_qui_vient() -> None:
    """Deux tableaux à la suite : une fois le premier **terminé**, la résolution implicite doit
    passer au suivant. Prendre « la première élimination directe » tout court épinglerait le tournoi
    sur le premier à jamais, et routerait tout le monde en « terminé »."""
    monde = _Monde()
    archers = _quatre(monde)
    premier = monde.phase_id
    assert premier is not None
    monde.phases._phases[premier] = replace(
        monde.phases._phases[premier], statut=StatutPhase.TERMINEE
    )
    second = monde.creer_phase_tableau()

    routage = monde.routage.routage(monde.tournoi_id, (archers[0],))

    assert routage.phase_id == second


def test_tous_les_tableaux_termines_vise_le_dernier() -> None:
    """Le repli du repli. Quand plus aucun tableau n'est en cours, viser le **premier** renverrait
    « non retenu pour le tableau » à qui n'a joué que le second — alors qu'il y a un rang à
    afficher. C'est le **dernier** qui porte le dénouement."""
    monde = _Monde()
    archers = _quatre(monde)
    premier = monde.phase_id
    assert premier is not None
    second = monde.creer_phase_tableau()
    for phase_id in (premier, second):
        monde.phases._phases[phase_id] = replace(
            monde.phases._phases[phase_id], statut=StatutPhase.TERMINEE
        )

    routage = monde.routage.routage(monde.tournoi_id, (archers[0],))

    assert routage.phase_id == second


def test_un_archer_disqualifie_garde_son_nom() -> None:
    """Une DSQ **sort** l'archer du classement (ADR-0050) — donc du tableau. Il reste pourtant dans
    la grille du poste, donc le panneau le route encore : sa ligne doit porter son **nom**, sinon
    c'est précisément lui qu'on rend anonyme. Les identités viennent des archers, pas du classement.
    """
    monde = _Monde()
    archers = _quatre(monde)
    monde.placer()
    qualif = monde.phases.ajouter(
        Phase.qualification(
            monde.tournoi_id,
            BaremeQualification.creer(1, 2),
            GrainValidation.fin_de_serie(),
        )
    )
    assert qualif.id is not None
    monde.forfaits.semer(
        Forfait.creer(
            monde.tournoi_id,
            archers[0],
            qualif.id,
            NatureForfait.DISQUALIFICATION,
            "DURAND",
            _QUAND,
        )
    )

    ligne = monde.routage.routage(monde.tournoi_id, (archers[0],)).archers[0]

    assert ligne.issue is IssueRoutage.INDISPONIBLE  # sorti du classement, donc du tableau
    assert ligne.nom != ""


def test_un_participant_equipe_n_est_pas_route() -> None:
    """Le moteur oppose des `Participant` (ADR-0028), mais le panneau ne sait router que des
    **archers**. Un identifiant qui ne correspond à aucun archer du tableau rend une ligne motivée,
    jamais une erreur : les équipes (E13US002) passeront par ce chemin tant qu'elles ne sont pas
    routables."""
    monde = _Monde()
    archers = _quatre(monde)
    monde.placer()

    ligne = monde.routage.routage(monde.tournoi_id, (archers[0], 4242)).archers[1]

    assert ligne.issue is IssueRoutage.INDISPONIBLE
    assert ligne.motif is not None


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
