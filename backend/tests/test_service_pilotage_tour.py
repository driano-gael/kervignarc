"""Tests du service `ServicePilotageTour` (E12US002, ADR-0056) — repositories factices.

Ici vit la **règle métier du pilotage du jour J**, dérivée du CA (`stories/E12-pilotage-jour-j.md`,
E12US002) — écrite **avant** l'implémentation (règle 9) :

- **Feu vert** : pour chaque duel *à venir*, les trois questions du CA (*participants connus ?*,
  *cible attribuée ?*, *source validée ?*) et le blocage **nommé** (« en attente du duel n°X »),
  jamais un simple drapeau (`P-3`).
- **Lancement** : le bouton **chiffre** ce qu'il déclenche (duels, cibles, archers) ; l'unité
  lançable est le **duel** (`D-23`) ; le serveur **recalcule** et n'écarte que les prêts (jamais
  cru sur parole, E12US007) ; l'acte laisse une **trace d'audit** `LANCEMENT`.

Le monde compose les **mêmes** services que la production (saisie + placement de duels + audit) sur
des repositories en mémoire ; le classement est **vrai** (`ServiceClassement` sur séries semées)
pour un ensemencement réaliste et déterministe. On réutilise les doubles des jumeaux (saisie,
placement, audit) plutôt que d'en refaire.
"""

from __future__ import annotations

import dataclasses
import datetime
from dataclasses import replace

import pytest

from application.audit import ServiceAudit
from application.classements import ServiceClassement
from application.erreurs import AucunDuelALancer, PhasePasUnTableau
from application.pilotage_tour import ServicePilotageTour
from application.placement_duels import ServicePlacementDuels
from application.saisie_duels import ServiceSaisieDuels
from domain.archer import Archer
from domain.bareme import BaremeQualification
from domain.blason import Blason, ZoneScore
from domain.categorie import Categorie
from domain.depart import Depart
from domain.duel import ResolveurBaremeDuelFfta
from domain.entree_audit import ActionAuditee
from domain.forfait import Forfait, NatureForfait
from domain.gabarit_salle import GabaritSalle
from domain.inscription import Inscription
from domain.phase import Phase, StatutPhase, TypePhase
from domain.politiques import (
    AggregationParQualification,
    ByesAuxMieuxClasses,
    PlacementEnCascade,
    SeedingSerpent,
    registre_par_defaut,
)
from domain.tableau import Tableau
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxDepartRepository,
    FauxDuelRepository,
    FauxForfaitRepository,
    FauxInscriptionRepository,
    FauxPhaseRepository,
)
from tests.test_domain_tableau import construire, jouer_gagne_mieux_classe
from tests.test_service_audit import FauxAuditRepository, HorlogeFigee
from tests.test_service_placement_duels import (
    FauxBlasonRepository,
    FauxGabaritRepository,
    FauxPlacementTableauRepository,
    FauxSerieRepository,
    FauxTournoiRepository,
)
from tests.test_service_saisie_duels import ZONES_TRIPLE

_QUAND = datetime.datetime(2026, 3, 14, 14, 20, tzinfo=datetime.UTC)


class _Monde:
    """Décor : un tournoi, un gabarit, une catégorie (arc + blason), N archers, une phase tableau.

    Scores **décroissants** à la création → rangs scratch 1..N. On peut **placer** (via le plan de
    duels) et **scorer** (via la saisie) : le pilotage lit les deux.
    """

    def __init__(self, capacites: tuple[int, ...] = (4,)) -> None:
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
        self.audit = FauxAuditRepository()
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
        phase = self.phases.ajouter(Phase.creer(self.tournoi_id, 2, TypePhase.ELIMINATION_DIRECTE))
        assert phase.id is not None
        self.phase_id = phase.id
        self.inscription_par_archer: dict[int, int] = {}

    @property
    def qualif_id(self) -> int:
        """La qualification de ce créneau — **posée à la demande** si le décor n'en a pas.

        E05US025 (ADR-0082) : une feuille de marque pend à sa phase, et le classement se lit sur
        elle. Beaucoup de décors ne posaient que le tableau (ordre 2) et semaient les scores « dans
        le tournoi » ; il leur faut désormais une qualification réelle. Paresseuse pour ne rien
        changer aux décors qui ne sèment aucun score — et **idempotente**, pour ne pas en créer une
        seconde à chaque appel (ce qui serait licite depuis cette US, donc silencieux).
        """
        existante = next(
            (
                p
                for p in self.phases.par_depart(self.depart_id)
                if p.type is TypePhase.QUALIFICATION
            ),
            None,
        )
        if existante is not None and existante.id is not None:
            return existante.id
        # Ce décor n'a pas de dépôt de déroulé : `FauxPhaseRepository` n'assemble donc pas et
        # `ajouter` suffit (contrairement aux décors qui en ont un, où une phase sans étape serait
        # écartée comme orpheline — ADR-0076).
        posee = self.phases.ajouter(
            Phase.qualification(self.depart_id, BaremeQualification.creer(1, 3))
        )
        assert posee.id is not None
        return posee.id

    def inscrire_classe(self, valeurs: tuple[str, ...]) -> int:
        archer = self.archers.ajouter(
            Archer(nom="N", prenom="P", tournoi_id=self.tournoi_id, categorie_id=self.categorie_id)
        )
        assert archer.id is not None
        inscription = self.inscriptions.ajouter(
            Inscription(archer_id=archer.id, depart_id=self.depart_id)
        )
        assert inscription.id is not None
        self.inscription_par_archer[archer.id] = inscription.id
        self.series.semer(
            self.tournoi_id, archer.id, tuple(ZoneScore(v) for v in valeurs), self.qualif_id
        )
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
            PlacementEnCascade(),
            registre_par_defaut(),
            AggregationParQualification(),
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
            self.saisie,
        )

    @property
    def pilotage(self) -> ServicePilotageTour:
        audit_service = ServiceAudit(self.audit, self.tournois, HorlogeFigee(_QUAND))
        return ServicePilotageTour(self.saisie, self.placement, audit_service)

    def placer(self) -> None:
        """Matérialise le plan de duels du 1er tour (les duellistes reçoivent une cible)."""
        self.placement.regenerer(self.tournoi_id, self.phase_id)

    def gagner(self, numero: int) -> None:
        """Fait gagner 6-0 le camp **haut** du match `numero` (3 manches) puis valide.

        Le poseur de tour est branché **comme au composition root** (ADR-0106 §5) : sans lui, la
        pose automatique du tour suivant serait muette, et le décor mentirait sur le produit.
        """
        saisie = self.saisie
        saisie.brancher_poseur_de_tour(self.placement)
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


def _quatre(monde: _Monde) -> None:
    for valeurs in (("10", "10"), ("9", "9"), ("8", "8"), ("7", "7")):
        monde.inscrire_classe(valeurs)


def test_feu_vert_frais_tour1_place_tous_prets() -> None:
    """CA feu vert : quatre archers placés → les deux duels du 1er tour sont **prêts** (participants
    connus, cible attribuée, aucun blocage) ; les tours suivants attendent leur source."""
    monde = _Monde(capacites=(4,))
    _quatre(monde)
    monde.placer()

    feu = monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id)
    tour1 = [d for d in feu.duels if d.tour == 1]
    assert len(tour1) == 2
    assert all(d.pret_a_lancer for d in tour1)
    assert all(d.participants_connus and d.cible_attribuee for d in tour1)
    assert all(d.blocage is None for d in tour1)
    assert feu.nb_prets == 2
    # Les matchs de tour 2 (finale, petite finale) sont à venir mais bloqués : occupants inconnus.
    tour2 = [d for d in feu.duels if d.tour == 2]
    assert tour2 and all(not d.participants_connus and not d.pret_a_lancer for d in tour2)


def test_feu_vert_nomme_la_source_non_validee() -> None:
    """CA « ce qui bloque est nommé » : après avoir joué un seul demi, la finale attend l'autre demi
    — et le blocage **cite** le numéro du duel manquant (« en attente du duel n°2 »)."""
    monde = _Monde(capacites=(4,))
    _quatre(monde)
    monde.placer()
    monde.gagner(1)  # on tranche le demi n°1 ; le n°2 reste à jouer

    feu = monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id)
    numeros_a_venir = {d.numero for d in feu.duels}
    assert 1 not in numeros_a_venir  # le demi tranché n'est plus « à venir »
    tour2 = [d for d in feu.duels if d.tour == 2]
    assert tour2
    for duel in tour2:
        assert duel.sources_en_attente == (2,)  # attend le demi n°2
        assert duel.blocage is not None and "n°2" in duel.blocage


def test_feu_vert_cible_non_attribuee_sans_placement() -> None:
    """CA « cible attribuée ? » : sans plan de duels, les adversaires connus mais **sans cible**
    — le duel n'est pas prêt et le blocage le dit. `P-3` : rien n'est empêché, c'est montré."""
    monde = _Monde(capacites=(4,))
    _quatre(monde)
    # pas de `placer()` : aucune cible attribuée

    feu = monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id)
    tour1 = [d for d in feu.duels if d.tour == 1]
    assert tour1 and all(d.participants_connus for d in tour1)
    assert all(not d.cible_attribuee and not d.pret_a_lancer for d in tour1)
    assert all(d.blocage == "cible non attribuée" for d in tour1)
    assert feu.nb_prets == 0


def test_feu_vert_tour2_annonce_les_cibles_du_tour_2() -> None:
    """L'invariant de sûreté d'ADR-0056 **survit** à E03US012, sous une forme généralisée.

    L'ancienne rédaction refusait toute cible au-delà du tour 1, faute de pose fraîche : une cible
    de tour 1 est **périmée** au tour 2, et l'annoncer enverrait les finalistes, venus de deux
    cibles distinctes, chacun sur son ancienne. La garde n'a pas disparu — elle compare désormais
    au **tour posé** (ADR-0106 §2). Ce test verrouille que les cibles annoncées viennent bien du
    plan du **tour 2**, jamais d'un report du tour 1."""
    monde = _Monde(capacites=(4,))
    _quatre(monde)
    monde.placer()
    monde.gagner(1)  # demi n°1 tranché
    monde.gagner(2)  # demi n°2 tranché → la finale a ses deux occupants (vainqueurs propagés)

    plan = monde.placement.plan_de_duels(monde.tournoi_id, monde.phase_id)
    assert plan.tour == 2, "le plan a suivi le tour qui se joue"
    poses = {pose.archer_id: cible.index for cible in plan.cibles for pose in cible.placements}
    feu = monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id)
    tour2 = [d for d in feu.duels if d.tour == 2]
    assert tour2
    for duel in tour2:
        assert duel.participants_connus and duel.cible_attribuee and duel.pret_a_lancer
        assert duel.blocage is None
        # L'assertion qui compte : la cible annoncée EST celle du plan du tour 2.
        assert duel.haut is not None and duel.bas is not None
        assert duel.cible_haut == poses[duel.haut.archer_id]
        assert duel.cible_bas == poses[duel.bas.archer_id]
    assert feu.nb_prets == len(tour2)


def test_feu_vert_ignore_les_byes() -> None:
    """Un match gagné d'office (bye, effectif impair) n'est **pas** un duel à lancer : il est résolu
    (vainqueur d'office, `vainqueur is not None`) et n'apparaît pas parmi les duels à venir."""
    monde = _Monde(capacites=(4,))
    for valeurs in (("10", "10"), ("9", "9"), ("8", "8")):  # 3 archers → un bye au tour 1
        monde.inscrire_classe(valeurs)
    monde.placer()

    feu = monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id)
    tour1 = [d for d in feu.duels if d.tour == 1]
    assert len(tour1) == 1  # le bye (2ᵉ match du tour 1) est résolu et absent du feu vert


def test_feu_vert_ne_pose_que_le_tour_qui_se_joue_sur_trois_tours() -> None:
    """Un seul tour est posé à la fois (ADR-0106 §2), et ce tour n'est ni le 1er ni le dernier.

    Sur un tableau à 8 (trois tours), une fois les quarts validés, **les demies** sont posées et
    prêtes, tandis que la finale (tour 3) attend encore ses occupants. C'est le cas qui distingue
    « le tour posé » d'un `tour == 1` **et** d'un `tour == nb_tours` — indiscernables à 4 archers.
    """
    monde = _Monde(capacites=(4, 4))
    for valeurs in (
        ("10", "10"),
        ("9", "9"),
        ("8", "8"),
        ("7", "7"),
        ("6", "6"),
        ("5", "5"),
        ("4", "4"),
        ("3", "3"),
    ):
        monde.inscrire_classe(valeurs)
    monde.placer()
    for numero in (1, 2, 3, 4):  # les quarts (tour 1)
        monde.gagner(numero)

    feu = monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id)
    assert feu.tour_pose == 2
    demies = [d for d in feu.duels if d.tour == 2]
    assert demies and all(d.pret_a_lancer for d in demies), "le tour qui se joue est posé"
    tour3 = [d for d in feu.duels if d.tour == 3]
    assert tour3, "la finale est à venir"
    for duel in tour3:
        # Pas encore déterminée : ses sources sont les demies, non tranchées. Le blocage est donc
        # **nommé** (« en attente du duel n°X »), jamais « cible non attribuée », qui laisserait
        # croire à un oubli de placement.
        assert not duel.participants_connus
        assert duel.cible_haut is None and duel.cible_bas is None
        assert not duel.pret_a_lancer
        assert duel.blocage is not None and duel.blocage.startswith("en attente du duel")


def test_lancer_global_chiffre_et_trace() -> None:
    """CA lancement : le lancement global fait partir tous les duels prêts, **chiffre** ce qu'il
    déclenche (duels/cibles/archers) et laisse une **trace d'audit** `LANCEMENT` datée/attribuée."""
    monde = _Monde(capacites=(4,))
    _quatre(monde)
    monde.placer()

    resume = monde.pilotage.lancer(monde.tournoi_id, monde.phase_id)
    assert resume.nb_duels == 2
    assert resume.nb_archers == 4  # deux tireurs par duel
    assert 1 in resume.cibles  # au moins une cible concernée
    assert resume.numeros == (1, 2)

    traces = monde.audit.par_tournoi(monde.tournoi_id)
    assert len(traces) == 1
    assert traces[0].action is ActionAuditee.LANCEMENT
    assert traces[0].auteur == "Administrateur"
    assert "2 duel(s)" in (traces[0].apres or "")


def test_lancer_sous_ensemble_ecarte_les_non_prets() -> None:
    """CA « l'unité lançable est le duel » + « jamais cru sur parole » : on demande un duel prêt (1)
    et un qui ne l'est pas (la finale, occupants inconnus) — seul le prêt part."""
    monde = _Monde(capacites=(4,))
    _quatre(monde)
    monde.placer()
    finale = next(
        d.numero
        for d in monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id).duels
        if d.tour == 2
    )

    resume = monde.pilotage.lancer(monde.tournoi_id, monde.phase_id, numeros=(1, finale))
    assert resume.numeros == (1,)  # la finale non prête a été écartée
    assert resume.nb_duels == 1


def test_lancer_sans_duel_pret_est_refuse() -> None:
    """CA/`P-3` : rien de prêt (aucun placement) → il n'y a **rien à émettre**, 409 sans trace."""
    monde = _Monde(capacites=(4,))
    _quatre(monde)  # placés nulle part

    with pytest.raises(AucunDuelALancer):
        monde.pilotage.lancer(monde.tournoi_id, monde.phase_id)
    assert monde.audit.par_tournoi(monde.tournoi_id) == []  # aucune trace émise


def test_impact_lancement_est_le_miroir_sans_ecrire() -> None:
    """Le bouton **prévisualise** sans émettre : `impact_lancement` = ce que `lancer` fera, mais
    aucune trace n'est écrite (lecture pure, comme `impact_regeneration` d'E12US007)."""
    monde = _Monde(capacites=(4,))
    _quatre(monde)
    monde.placer()

    impact = monde.pilotage.impact_lancement(monde.tournoi_id, monde.phase_id)
    assert impact.nb_duels == 2
    assert monde.audit.par_tournoi(monde.tournoi_id) == []  # prévisualisation : rien d'écrit


def test_tableau_termine_n_a_plus_rien_a_lancer() -> None:
    """Un tableau joué jusqu'au bout : `est_termine`, aucun duel à venir, `nb_prets` nul."""
    monde = _Monde(capacites=(4,))
    monde.inscrire_classe(("10", "10"))
    monde.inscrire_classe(("8", "8"))  # deux archers → un unique match (la finale)
    monde.placer()
    monde.gagner(1)  # la finale est tranchée

    feu = monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id)
    assert feu.est_termine
    assert feu.duels == ()
    assert feu.nb_prets == 0


def test_feu_vert_refuse_une_phase_de_qualification() -> None:
    """Garde : le feu vert n'a de sens que pour une élimination directe (`PhasePasUnTableau`)."""
    monde = _Monde(capacites=(4,))
    _quatre(monde)
    qualif = monde.phases.ajouter(
        Phase.qualification(monde.tournoi_id, BaremeQualification.creer(1, 3))
    )
    assert qualif.id is not None
    with pytest.raises(PhasePasUnTableau):
        monde.pilotage.feu_vert(monde.tournoi_id, qualif.id)


def test_une_ligne_bloquee_attend_une_ou_deux_sources_selon_ce_qui_reste_a_trancher() -> None:
    """L'ORACLE de ce que les écrans annoncent après un forfait (E16US008).

    ⚠️ Ce test existe parce que la prose s'est trompée **quatre fois de suite** en revue : « une
    source », puis « deux sources », puis « deux sauf byes ». Un `VainqueurDe`/`PerdantDe` ne compte
    comme attente que si son camp est **vide** ; un camp se remplit de DEUX façons — un bye à la
    construction, **ou un duel amont déjà tranché**. D'où le régime **1 ou 2, à tout effectif**.
    ⚠️ Le fixture doit être un tableau **EN COURS** : l'organisateur ne lit jamais le feu vert sur un
    tableau vierge, et c'est en ne mesurant que le vierge qu'on a conclu « puissance de 2 ⇒ toujours
    deux ». Les décomptes exacts dépendent de la profondeur injectée (règle 2) ; le régime 1-ou-2,
    lui, est **structurel** — un match n'a que deux camps.
    """

    def repartition(tableau: Tableau) -> dict[int, int]:
        compte: dict[int, int] = {}
        for match in tableau.matchs:
            if match.est_bye or match.vainqueur is not None:
                continue
            attendues = len(ServicePilotageTour._sources_en_attente(match))
            if attendues:
                compte[attendues] = compte.get(attendues, 0) + 1
        return compte

    # À la construction, les byes seuls font varier le régime (profondeur `podium`, défaut).
    assert repartition(construire(8)) == {2: 4}
    assert repartition(construire(6)) == {1: 2, 2: 2}
    assert repartition(construire(3)) == {1: 1}

    # ⚠️ EN COURS, et sans le moindre bye : trancher un amont suffit à faire naître le régime « une
    # source ». C'est l'assertion qui aurait rougi sur les quatre versions fausses de la prose.
    en_cours = jouer_gagne_mieux_classe(construire(8), 1)
    assert repartition(en_cours) == {1: 1, 2: 3}


def test_un_forfait_sur_un_amont_de_tour_2_ne_fait_pas_bouger_le_compteur() -> None:
    """Le volet « compteur » de l'oracle (E16US008), **réécrit** par E03US012.

    ⚠️ La prémisse d'origine est **abolie** : elle tenait à ce qu'un duel de tour ≥ 2 n'ait jamais
    de cible (`place = match.tour == 1`), donc ne soit jamais compté. Depuis ADR-0106 la finale est
    posée dès qu'elle est déterminée, donc **comptée** — et un forfait qui la tranche fait bien
    baisser le compteur. C'est la phrase que la recette rend à l'organisateur (ADR-0013 §10) : elle
    vit ici, pas dans la prose, et c'est pourquoi elle change avec le comportement.
    """
    monde = _Monde(capacites=(4,))
    _quatre(monde)
    monde.placer()
    monde.gagner(1)
    monde.gagner(2)
    avant = monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id)
    finale = next(d for d in avant.duels if d.tour == 2)
    assert finale.participants_connus and finale.pret_a_lancer
    assert avant.nb_prets >= 1

    monde.forfaits.semer(
        Forfait.creer(
            monde.tournoi_id,
            finale.haut.archer_id if finale.haut else 0,
            monde.phase_id,
            NatureForfait.ABANDON,
            "Administrateur",
            datetime.datetime(2026, 8, 28, 10, 0, tzinfo=datetime.UTC),
        )
    )
    apres = monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id)
    # Le tableau a avancé (le duel forfait est tranché, il quitte les duels à venir)...
    assert len(apres.duels) < len(avant.duels)
    # ...et le compteur **suit**, puisque ce duel y figurait désormais.
    assert apres.nb_prets == avant.nb_prets - 1


# --- CA E03US012 « poser les cibles des tours suivants » (ADR-0106) -----------------------------
# Ces tests dérivent du CA de `stories/E03-placement.md` § E03US012, pas du code : ce que
# l'organisateur doit constater, c'est qu'un duel devient **prêt à lancer** passé le premier tour.


def test_le_tour_suivant_recoit_ses_cibles_des_qu_il_est_determine() -> None:
    """CA : « quand tous les duels d'un tour sont tranchés, les duellistes du tour suivant
    reçoivent leur pose sans geste de l'organisateur ».

    C'est la capacité neuve, et c'est aussi la non-régression qui compte le plus : avant E03US012,
    `pret_a_lancer` était **toujours faux** au-delà du tour 1, donc plus rien ne partait de la
    journée passé le premier tour.
    """
    monde = _Monde(capacites=(4,))
    _quatre(monde)
    monde.placer()
    for numero in (
        d.numero for d in monde.pilotage.feu_vert(1, monde.phase_id).duels if d.tour == 1
    ):
        monde.gagner(numero)

    tour2 = [d for d in monde.pilotage.feu_vert(1, monde.phase_id).duels if d.tour == 2]
    assert tour2, "le tour 2 doit exister une fois le tour 1 tranché"
    assert all(d.participants_connus for d in tour2)
    assert all(d.cible_attribuee for d in tour2), "le tour 2 doit avoir reçu ses cibles sans geste"
    assert all(d.pret_a_lancer and d.blocage is None for d in tour2)


def test_rien_ne_se_pose_tant_que_le_tour_n_est_pas_determine() -> None:
    """CA : « un duel dont les sources ne sont pas tranchées n'a aucune pose ».

    Un seul des deux duels du tour 1 est joué : le tour 2 n'est pas déterminé, donc rien ne se
    pose, et le blocage reste **nommé** — « en attente du duel n°X », jamais « cible non
    attribuée », qui laisserait croire à un oubli de placement.
    """
    monde = _Monde(capacites=(4,))
    _quatre(monde)
    monde.placer()
    premier = next(
        d.numero for d in monde.pilotage.feu_vert(1, monde.phase_id).duels if d.tour == 1
    )
    monde.gagner(premier)

    tour2 = [d for d in monde.pilotage.feu_vert(1, monde.phase_id).duels if d.tour == 2]
    finale = next(d for d in tour2 if d.sources_en_attente)
    assert not finale.cible_attribuee
    assert finale.blocage is not None and finale.blocage.startswith("en attente du duel")


def test_le_tour_avance_se_regroupe_sur_les_premieres_cibles() -> None:
    """CA (arbitrage du commanditaire, 05/09/2026) : « un tour avancé se tasse sur les cibles de
    plus petit numéro et libère les cibles hautes »."""
    monde = _Monde(capacites=(2, 2, 2))
    _quatre(monde)
    monde.placer()
    for numero in (
        d.numero for d in monde.pilotage.feu_vert(1, monde.phase_id).duels if d.tour == 1
    ):
        monde.gagner(numero)

    plan = monde.placement.plan_de_duels(1, monde.phase_id)
    assert plan.tour == 2, "le plan suit le tour qui se joue"
    occupees = {c.index for c in plan.cibles if c.placements}
    assert occupees and max(occupees) < 3, "la cible haute doit rester libre"


def test_une_phase_en_pause_ne_prepare_pas_la_butte_d_apres() -> None:
    """CA / ADR-0106 §4 : un arrêt éteint la salle — on ne pose pas les cibles du tour suivant.

    Sans cette garde, le panneau de routage annoncerait une butte à des archers qu'on vient
    d'arrêter.
    """
    monde = _Monde(capacites=(4,))
    _quatre(monde)
    monde.placer()
    for numero in (
        d.numero for d in monde.pilotage.feu_vert(1, monde.phase_id).duels if d.tour == 1
    ):
        monde.gagner(numero)
    # On défait la pose du tour 2 pour observer le geste suivant : c'est l'ordre réel du jour J —
    # la validation signale d'abord les arrêts (qui mettent la phase en pause), **puis** la pose.
    for affectation in monde.placements.par_phase_et_tour(monde.phase_id, 2):
        monde.placements.retirer(monde.phase_id, 2, affectation.inscription_id)
    phase = monde.phases.par_id(monde.phase_id)
    assert phase is not None
    monde.phases.enregistrer(dataclasses.replace(phase, statut=StatutPhase.EN_PAUSE))

    monde.placement.poser_le_tour_courant(1, monde.phase_id)

    assert (
        monde.placements.par_phase_et_tour(monde.phase_id, 2) == []
    ), "une phase en pause ne prepare pas la butte suivante"
