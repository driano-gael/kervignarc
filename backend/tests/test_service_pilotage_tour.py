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
from application.erreurs import (
    AucunDuelALancer,
    PhasePasUnTableau,
    RegenerationSurTourEnTir,
)
from application.forfaits import ServiceForfait
from application.phases import ServicePhases
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
    FauxDerouleRepository,
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
        self.deroules = FauxDerouleRepository()
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

    def inscription_de(self, archer_id: int) -> int:
        """L'`inscription_id` de cet archer dans le créneau du décor."""
        inscription = next(
            i for i in self.inscriptions.par_depart(self.depart_id) if i.archer_id == archer_id
        )
        assert inscription.id is not None
        return inscription.id

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
    def forfait(self) -> ServiceForfait:
        """Le service de forfait, **branché comme au composition root** : un walkover tranche un
        duel sans qu'aucun score soit saisi (ADR-0106 §5, 2ᵉ chemin)."""
        service = ServiceForfait(
            self.forfaits, self.tournois, self.archers, self.phases, HorlogeFigee(_QUAND)
        )
        service.brancher_poseur_de_tour(self.placement)
        return service

    @property
    def cycle_de_vie(self) -> ServicePhases:
        """Le service des transitions de phase, **branché comme au composition root** : c'est lui
        qui rattrape la pose sautée pendant une pause (ADR-0106 §5, 3ᵉ chemin)."""
        service = ServicePhases(self.tournois, self.phases, self.departs, self.deroules)
        service.brancher_poseur_de_tour(self.placement)
        return service

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
        d.numero
        for d in monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id).duels
        if d.tour == 1
    ):
        monde.gagner(numero)

    tour2 = [
        d for d in monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id).duels if d.tour == 2
    ]
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
        d.numero
        for d in monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id).duels
        if d.tour == 1
    )
    monde.gagner(premier)

    tour2 = [
        d for d in monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id).duels if d.tour == 2
    ]
    finale = next(d for d in tour2 if d.sources_en_attente)
    assert not finale.cible_attribuee
    assert finale.blocage is not None and finale.blocage.startswith("en attente du duel")


def test_le_tour_avance_se_regroupe_sur_les_premieres_cibles() -> None:
    """CA (arbitrage du commanditaire, 05/09/2026) : « un tour avancé se tasse sur les cibles de
    plus petit numéro et libère les cibles hautes ».

    ⚠️ **Il faut un effectif qui DÉCROÎT** (relevé en revue) : à 4 archers, le tour 2 compte encore
    4 duellistes (finale **et** petite finale) et occupe forcément les mêmes cibles — l'assertion
    passait quelle que soit l'implémentation, y compris une qui recopierait les poses du tour 1. À
    8 archers, le tour 2 n'en compte plus que 4 : les cibles hautes doivent se **libérer**.
    """
    monde = _Monde(capacites=(2, 2, 2, 2))
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
    assert {
        c.index
        for c in monde.placement.plan_de_duels(monde.tournoi_id, monde.phase_id).cibles
        if c.placements
    } == {1, 2, 3, 4}, "les 8 archers occupent les 4 cibles au tour 1"

    for numero in (1, 2, 3, 4):  # les quarts
        monde.gagner(numero)

    plan = monde.placement.plan_de_duels(monde.tournoi_id, monde.phase_id)
    assert plan.tour == 2, "le plan suit le tour qui se joue"
    occupees = {c.index for c in plan.cibles if c.placements}
    assert occupees == {1, 2}, f"le tour 2 doit se tasser sur les cibles basses, vu {occupees}"
    assert 3 not in occupees and 4 not in occupees, "les cibles hautes doivent se libérer"


def test_une_phase_en_pause_ne_prepare_pas_la_butte_d_apres() -> None:
    """CA / ADR-0106 §4 : un arrêt éteint la salle — on ne pose pas les cibles du tour suivant.

    Sans cette garde, le panneau de routage annoncerait une butte à des archers qu'on vient
    d'arrêter.
    """
    monde = _Monde(capacites=(4,))
    _quatre(monde)
    monde.placer()
    for numero in (
        d.numero
        for d in monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id).duels
        if d.tour == 1
    ):
        monde.gagner(numero)
    # On défait la pose du tour 2 pour observer le geste suivant : c'est l'ordre réel du jour J —
    # la validation signale d'abord les arrêts (qui mettent la phase en pause), **puis** la pose.
    for affectation in monde.placements.par_phase_et_tour(monde.phase_id, 2):
        monde.placements.retirer(monde.phase_id, 2, affectation.inscription_id)
    phase = monde.phases.par_id(monde.phase_id)
    assert phase is not None
    monde.phases.enregistrer(dataclasses.replace(phase, statut=StatutPhase.EN_PAUSE))

    monde.placement.poser_le_tour_courant(monde.tournoi_id, monde.phase_id)

    assert (
        monde.placements.par_phase_et_tour(monde.phase_id, 2) == []
    ), "une phase en pause ne prepare pas la butte suivante"


def test_valider_un_duel_du_tour_pose_ne_supprime_pas_ses_cibles() -> None:
    """Non-régression du **bloquant** de revue : l'acte automatique ne détruit rien.

    Le décor du tour était bâti sur `est_jouable`, qui exige `vainqueur is None` : dès qu'un duel
    du tour posé était tranché, ses deux archers quittaient le décor, donc `_poses_a_jour` les
    traitait en **orphelins** et supprimait leurs poses. Le plan se vidait au fil du tour, puis
    entièrement à la fin de la phase — y compris au tour 1, qui n'était même pas censé changer.
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
    poses_tour1 = monde.placements.par_phase_et_tour(monde.phase_id, 1)
    assert len(poses_tour1) == 8

    monde.gagner(1)
    assert (
        monde.placements.par_phase_et_tour(monde.phase_id, 1) == poses_tour1
    ), "valider un duel ne doit pas retirer les poses de ses duellistes"

    for numero in (2, 3, 4):
        monde.gagner(numero)
    poses_tour2 = monde.placements.par_phase_et_tour(monde.phase_id, 2)
    assert len(poses_tour2) == 4, "le tour 2 est posé"
    monde.gagner(5)
    assert monde.placements.par_phase_et_tour(monde.phase_id, 2) == poses_tour2


def test_le_plan_de_la_finale_reste_consultable_une_fois_le_tableau_termine() -> None:
    """L'ADR promet que le dernier tour reste affiché ; il se vidait (relevé en revue)."""
    monde = _Monde(capacites=(4,))
    _quatre(monde)
    monde.placer()
    for numero in (
        d.numero
        for d in monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id).duels
        if d.tour == 1
    ):
        monde.gagner(numero)
    for numero in (
        d.numero
        for d in monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id).duels
        if d.tour == 2
    ):
        monde.gagner(numero)

    plan = monde.placement.plan_de_duels(monde.tournoi_id, monde.phase_id)
    assert plan.tour == 2
    assert any(cible.placements for cible in plan.cibles), "le plan du dernier tour reste visible"


def test_la_reprise_apres_une_pause_pose_le_tour_qui_attendait() -> None:
    """Non-régression du **bloquant** de revue : sans ce chemin, la pose n'a jamais lieu.

    Un arrêt programmé coupe **à la fin d'un tour** (ADR-0091), donc exactement quand le tour
    suivant devrait être posé — et la pose est sautée, la phase étant en pause. Il ne reste alors
    plus aucun duel amont à valider : seule la reprise peut la rattraper.
    """
    monde = _Monde(capacites=(4,))
    _quatre(monde)
    monde.placer()
    for numero in (
        d.numero
        for d in monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id).duels
        if d.tour == 1
    ):
        monde.gagner(numero)
    # On rejoue la situation : le tour 2 n'a pas été posé (la phase était en pause à cet instant).
    for affectation in monde.placements.par_phase_et_tour(monde.phase_id, 2):
        monde.placements.retirer(monde.phase_id, 2, affectation.inscription_id)
    phase = monde.phases.par_id(monde.phase_id)
    assert phase is not None
    monde.phases.enregistrer(dataclasses.replace(phase, statut=StatutPhase.EN_PAUSE))

    monde.cycle_de_vie.reprendre(monde.depart_id, monde.phase_id)

    assert monde.placements.par_phase_et_tour(
        monde.phase_id, 2
    ), "la reprise doit poser le tour resté sans cibles pendant la pause"


def test_le_tour_1_n_est_jamais_pose_d_office() -> None:
    """ADR-0106 §4 : le tour 1 garde son geste explicite — le compléter reposerait un archer que
    l'organisateur a délibérément mis en réserve. La garde n'avait aucun test."""
    monde = _Monde(capacites=(4,))
    _quatre(monde)
    assert monde.placements.par_phase_et_tour(monde.phase_id, 1) == []

    monde.placement.poser_le_tour_courant(monde.tournoi_id, monde.phase_id)

    assert (
        monde.placements.par_phase_et_tour(monde.phase_id, 1) == []
    ), "le tour 1 ne se pose que sur le geste « Générer le plan »"


def test_un_tour_deja_pose_n_est_pas_recomplete_donc_la_reserve_tient() -> None:
    """ADR-0106 §4 : « compléter les trous » **reposerait** l'archer mis en réserve — une réserve
    *est* un trou. C'est l'objection qui exclut le tour 1, et elle vaut à tous les tours."""
    monde = _Monde(capacites=(4,))
    _quatre(monde)
    monde.placer()
    for numero in (
        d.numero
        for d in monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id).duels
        if d.tour == 1
    ):
        monde.gagner(numero)
    poses = monde.placements.par_phase_et_tour(monde.phase_id, 2)
    assert poses, "le tour 2 est posé"
    ecarte = poses[0].inscription_id
    monde.placement.deplacer(monde.tournoi_id, monde.phase_id, ecarte, None, None)

    monde.placement.poser_le_tour_courant(monde.tournoi_id, monde.phase_id)

    restants = {a.inscription_id for a in monde.placements.par_phase_et_tour(monde.phase_id, 2)}
    assert ecarte not in restants, "un archer mis en réserve ne doit pas être reposé d'office"


def test_regenerer_un_tour_dont_un_duel_a_tire_est_refuse() -> None:
    """La justification « au tour 1 aucun score n'existe » est tombée avec E03US012 : le tour posé
    est celui **qui se joue**. Régénérer y déplacerait des archers sur la butte."""
    monde = _Monde(capacites=(4,))
    _quatre(monde)
    monde.placer()
    saisie = monde.saisie
    saisie.saisir_manche(
        monde.tournoi_id, monde.phase_id, 1, 1, (ZoneScore.DIX,) * 3, (ZoneScore.SIX,) * 3
    )

    with pytest.raises(RegenerationSurTourEnTir):
        monde.placement.regenerer(monde.tournoi_id, monde.phase_id)


def test_un_tour_acheve_par_walkover_recoit_ses_cibles() -> None:
    """CA E03US012, 2ᵉ chemin : un forfait tranche un duel **sans qu'aucun score soit saisi**.

    Le seul test existant était un test de **câblage** : retirer l'appel `signaler` de
    `declarer_en_duel` l'aurait laissé vert. Celui-ci prouve le comportement — c'est le cas banal
    du jour J que la story met en ⚠️.
    """
    monde = _Monde(capacites=(4,))
    _quatre(monde)
    monde.placer()
    numeros = [
        d.numero
        for d in monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id).duels
        if d.tour == 1
    ]
    monde.gagner(numeros[0])
    perdant = monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id)
    duel = next(d for d in perdant.duels if d.numero == numeros[1])
    assert duel.haut is not None

    monde.forfait.declarer_en_duel(
        monde.tournoi_id, monde.phase_id, duel.haut.archer_id, NatureForfait.ABANDON, "ADMIN"
    )

    tour2 = [
        d for d in monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id).duels if d.tour == 2
    ]
    assert tour2 and all(
        d.cible_attribuee for d in tour2
    ), "le walkover achève le tour 1 : le tour 2 doit recevoir ses cibles sans clic"


def test_regenerer_le_tour_2_reste_possible_malgre_les_tirs_du_tour_1() -> None:
    """La garde de régénération porte sur le **tour posé**, pas sur la phase entière.

    ⚠️ Le seul test de cette garde l'exerçait au tour 1, où l'intersection avec `numeros_du_tour`
    est indistinguable d'un simple `if numeros:` — il ne prouvait donc pas la moitié qui compte
    (relevé en revue). Sans l'intersection, « Régénérer » deviendrait 409 **définitivement** dès le
    premier tir du tournoi, et le rattrapage que la recette recommande serait inatteignable.
    """
    monde = _Monde(capacites=(4,))
    _quatre(monde)
    monde.placer()
    for numero in (
        d.numero
        for d in monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id).duels
        if d.tour == 1
    ):
        monde.gagner(numero)

    plan = monde.placement.regenerer(monde.tournoi_id, monde.phase_id)

    assert plan.tour == 2


def test_regenerer_est_refuse_des_qu_un_duel_du_tour_pose_a_tire() -> None:
    """Le cas que l'arbitrage invoque : « redistribuerait des archers déjà sur la butte »."""
    monde = _Monde(capacites=(4,))
    _quatre(monde)
    monde.placer()
    for numero in (
        d.numero
        for d in monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id).duels
        if d.tour == 1
    ):
        monde.gagner(numero)
    finale = next(
        d.numero
        for d in monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id).duels
        if d.tour == 2
    )
    monde.saisie.saisir_manche(
        monde.tournoi_id,
        monde.phase_id,
        finale,
        1,
        (ZoneScore.DIX,) * 3,
        (ZoneScore.SIX,) * 3,
    )

    with pytest.raises(RegenerationSurTourEnTir):
        monde.placement.regenerer(monde.tournoi_id, monde.phase_id)


def test_un_duel_tranche_par_walkover_n_occupe_pas_de_place_sur_la_butte() -> None:
    """Un forfait tranche un duel qui ne sera **jamais tiré** : l'asseoir gaspille deux places.

    ⚠️ Régression introduite par le correctif du 1ᵉʳ bloquant : en cessant de filtrer sur
    `est_jouable`, `paires_du_tour` a fait entrer au décor les duels tranchés — y compris les
    walkovers, qui gardent leurs **deux** occupants. Le bon discriminant n'est pas « tranché » mais
    « tranché **avant** la pose » : ils restent au décor (leurs poses ne sont pas orphelines) et
    sortent du **placement**.
    """
    monde = _Monde(capacites=(4,))
    _quatre(monde)
    duel = next(
        d for d in monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id).duels if d.numero == 1
    )
    assert duel.haut is not None
    monde.forfait.declarer_en_duel(
        monde.tournoi_id, monde.phase_id, duel.haut.archer_id, NatureForfait.ABANDON, "ADMIN"
    )

    monde.placer()

    poses = {a.inscription_id for a in monde.placements.par_phase_et_tour(monde.phase_id, 1)}
    forfaitaire = monde.inscription_de(duel.haut.archer_id)
    assert forfaitaire not in poses, "un archer forfait n'occupe pas de couloir"


def test_annuler_un_forfait_laisse_le_tour_suivant_posable() -> None:
    """`D-15` : le forfait est réversible, et la pose doit suivre le recul du tour.

    ⚠️ La garde « un tour ne se pose qu'une fois » testait « au moins une pose ». Après annulation,
    le tour amont redevient jouable, un **autre** archer peut le gagner — et le tour aval gardait
    ses anciennes poses, donc passait pour posé : le nouveau qualifié restait sans cible,
    définitivement (relevé en revue, sondé). Les tours aval sont désormais purgés au recul.
    """
    monde = _Monde(capacites=(4,))
    _quatre(monde)
    monde.placer()
    monde.gagner(1)
    duel = next(
        d for d in monde.pilotage.feu_vert(monde.tournoi_id, monde.phase_id).duels if d.numero == 2
    )
    assert duel.haut is not None and duel.bas is not None
    monde.forfait.declarer_en_duel(
        monde.tournoi_id, monde.phase_id, duel.bas.archer_id, NatureForfait.ABANDON, "ADMIN"
    )
    assert monde.placements.par_phase_et_tour(monde.phase_id, 2), "le tour 2 est posé"

    monde.forfait.annuler_en_duel(monde.tournoi_id, monde.phase_id, duel.bas.archer_id, "ADMIN")

    assert (
        monde.placements.par_phase_et_tour(monde.phase_id, 2) == []
    ), "le recul du tour purge les poses aval, sans quoi le tour aval passe pour posé"
