"""Service **Poules** — composer, poser, faire tirer, classer (E05US023, [ADR-0083]).

**Chaque test porte le CA dont il dérive** (`stories/E05-moteur-phases.md`, puces « CA »), et non
une lecture de l'implémentation — c'est la source qui fait l'indépendance, pas l'auteur (règle 9).

⚠️ **Honnêteté sur l'ordre d'écriture** : le service a été écrit avant ces tests, contrairement à
l'étage domaine de cette même US (`test_domain_reglage_poules.py` et son voisin de placement) qui,
lui, a bien précédé son implémentation. Les oracles ci-dessous sont donc relus **depuis les
puces du CA**, ligne à ligne, et non depuis le code — mais l'ordre inverse aurait mieux protégé, et
le dire vaut mieux que de le taire. Le risque résiduel est nommé : un CA mal compris se serait
transcrit deux fois de la même façon.

[ADR-0083]: ../../docs/adr/0083-le-contrat-de-phase-jouable.md
"""

from __future__ import annotations

import datetime
from dataclasses import replace

import pytest

from application.classements import ServiceClassement
from application.erreurs import PhasePasDesPoules, PhasePasReglee
from application.poules import ServicePoules
from application.saisie_duels import ServiceSaisieDuels
from domain.archer import Archer
from domain.barrage import BarrageDePlaces, PorteeBarrage, TirBarrage
from domain.blason import Blason, ZoneScore
from domain.categorie import Categorie
from domain.depart import Depart
from domain.duel import ResolveurBaremeDuelFfta
from domain.gabarit_salle import GabaritSalle
from domain.inscription import Inscription
from domain.participant import Participant
from domain.phase import Phase, TypePhase
from domain.politiques import (
    AggregationParQualification,
    ByesAuxMieuxClasses,
    PlacementEnCascade,
    SeedingSerpent,
    registre_par_defaut,
)
from domain.poule import ReglageDePoules
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxDepartRepository,
    FauxDuelRepository,
    FauxForfaitRepository,
    FauxInscriptionRepository,
    FauxPhaseRepository,
)
from tests.test_service_placement_duels import (
    FauxBlasonRepository,
    FauxSerieRepository,
    FauxTournoiRepository,
)
from tests.test_service_saisie_duels import ZONES_TRIPLE


class _FauxPlacementParBlocRepository:
    """Double du port `PlacementParBlocRepository` — deux gestes, comme le port."""

    def __init__(self) -> None:
        self._plans: dict[int, list[object]] = {}

    def par_phase(self, phase_id: int) -> list[object]:
        return list(self._plans.get(phase_id, []))

    def definir_plan(self, phase_id: int, blocs: object) -> None:
        self._plans[phase_id] = list(blocs)  # type: ignore[call-overload]


class _FauxBarrageRepository:
    """Double du port `BarrageRepository`, réduit à ce que `ServicePoules` en lit."""

    def __init__(self) -> None:
        self.barrages: list[object] = []

    def par_depart(self, depart_id: int) -> list[object]:
        return list(self.barrages)


class _Monde:
    """Décor : un tournoi, un créneau, une salle, N archers classés, une phase de **poules**.

    Les archers reçoivent des scores décroissants dans l'ordre de création → rang scratch 1..N,
    ce qui rend la composition au serpent prévisible : le 1ᵉʳ va en poule 1, le 2ᵉ en poule 2, etc.
    """

    def __init__(self, *, nb_cibles: int = 8, couloirs: int = 4) -> None:
        self.tournoi_id = 1
        self.tournois = FauxTournoiRepository({1})
        self.departs = FauxDepartRepository()
        depart = self.departs.ajouter(
            Depart.creer(tournoi_id=self.tournoi_id, numero=1, tarif_centimes=800, horaire="09:00")
        )
        assert depart.id is not None
        self.depart_id = depart.id
        self.inscriptions = FauxInscriptionRepository()
        self.phases = FauxPhaseRepository(self.departs)
        self.archers = FauxArcherRepository()
        self.categories = FauxCategorieRepository()
        self.blasons = FauxBlasonRepository()
        self.series = FauxSerieRepository()
        self.duels = FauxDuelRepository()
        self.forfaits = FauxForfaitRepository()
        self.placements = _FauxPlacementParBlocRepository()
        self.barrages = _FauxBarrageRepository()
        self.gabarits = _FauxGabaritRepository(nb_cibles, couloirs)
        blason = self.blasons.ajouter(
            Blason.creer(self.tournoi_id, "Triple", taille=0.25, capacite=1)
        )
        assert blason.id is not None
        self.blasons._blasons[blason.id] = replace(blason, zones=ZONES_TRIPLE)
        categorie = self.categories.ajouter(
            Categorie.creer(
                self.tournoi_id, "Cat", arme="Arc Classique", blason_id=blason.id, hauteur_cm=130
            )
        )
        assert categorie.id is not None
        self.categorie_id = categorie.id
        from domain.bareme import BaremeQualification

        qualif = self.phases.ajouter(
            Phase.qualification(self.depart_id, BaremeQualification.creer(1, 3))
        )
        assert qualif.id is not None
        self.qualif_id = qualif.id
        self.phase_id = 0

    def regler(self, reglage: ReglageDePoules | None, barrage_jusqu_au: int | None = None) -> int:
        """Pose la phase de poules avec son réglage (ou sans, pour éprouver le refus).

        `barrage_jusqu_au` est le **seuil de barrage** (ADR-0066) : il se règle sur la phase et se
        résout par le registre de politiques. Paramétrable ici depuis le correctif de revue — sans
        lui, aucun test ne pouvait exercer le chemin où la politique est réellement injectée.
        """
        phase = self.phases.ajouter(
            Phase(
                depart_id=self.depart_id,
                ordre=2,
                type=TypePhase.POULES,
                poules=reglage,
                barrage_jusqu_au=barrage_jusqu_au,
            )
        )
        assert phase.id is not None
        self.phase_id = phase.id
        return phase.id

    def inscrire(self, combien: int) -> list[int]:
        """Inscrit `combien` archers, classés par scores décroissants (rang 1 = le premier créé)."""
        ids: list[int] = []
        for rang in range(combien):
            archer = self.archers.ajouter(
                Archer(
                    nom=f"N{rang}",
                    prenom="P",
                    tournoi_id=self.tournoi_id,
                    categorie_id=self.categorie_id,
                )
            )
            assert archer.id is not None
            # Trois flèches décroissantes : le premier créé marque le plus, donc rang scratch 1.
            valeur = str(max(1, 10 - rang))
            self.series.semer(
                self.tournoi_id,
                archer.id,
                (ZoneScore(valeur), ZoneScore(valeur), ZoneScore(valeur)),
                self.qualif_id,
            )
            self.inscriptions.ajouter(Inscription.creer(archer.id, self.depart_id))
            ids.append(archer.id)
        return ids

    def service(self) -> ServicePoules:
        classement = ServiceClassement(
            self.tournois,
            self.archers,
            self.series,
            self.categories,
            self.phases,
            self.forfaits,
            self.departs,
            self.inscriptions,
        )
        saisie = ServiceSaisieDuels(
            self.tournois,
            self.phases,
            self.categories,
            self.blasons,
            self.duels,
            self.forfaits,
            classement,
            ResolveurBaremeDuelFfta(),
            SeedingSerpent(),
            ByesAuxMieuxClasses(),
            PlacementEnCascade(),
            registre_par_defaut(),
            AggregationParQualification(),
        )
        return ServicePoules(
            self.tournois,
            self.phases,
            self.gabarits,  # type: ignore[arg-type]
            self.placements,  # type: ignore[arg-type]
            self.duels,
            self.barrages,  # type: ignore[arg-type]
            classement,
            saisie,
            registre_par_defaut(),
        )


class _FauxGabaritRepository:
    """Double de `GabaritSalleRepository` : une salle homogène de `nb_cibles` sur `couloirs`."""

    def __init__(self, nb_cibles: int, couloirs: int) -> None:
        self._gabarit = GabaritSalle.creer("Salle", nb_cibles=nb_cibles, capacite=couloirs)

    def par_tournoi(self, tournoi_id: int) -> GabaritSalle:
        return self._gabarit


# --- CA « la taille commande, le nombre de groupes s'en déduit » --------------------------------


def test_trente_archers_en_poules_de_quatre_donnent_cinq_de_quatre_et_deux_de_cinq() -> None:
    """L'exemple **littéral** du CA (arbitrage du commanditaire du 09/08/2026).

    L'organisateur saisit « poules de 4 », **pas** « 8 poules » : le nombre de groupes vaut
    `effectif ÷ taille` arrondi **vers le bas**, et le reste gonfle quelques poules. Aucune poule ne
    compte donc **moins** que la taille demandée — « 8 poules dont deux de 3 » a été explicitement
    écarté.
    """
    monde = _Monde()
    monde.inscrire(30)
    phase_id = monde.regler(ReglageDePoules(taille_visee=4))

    repartition = monde.service().repartition(monde.tournoi_id, phase_id)

    assert repartition.nb_poules == 7
    assert sorted(repartition.tailles) == [4, 4, 4, 4, 4, 5, 5]


def test_sous_le_double_de_la_taille_il_ne_reste_quune_poule() -> None:
    """Le cas extrême que le CA veut **montré**, pas empêché.

    7 archers en poules de 4 donnent **une** poule de 7 : les deux invariants (« pas de poule sous
    la taille » et « pas plus d'une unité d'écart ») deviennent inconciliables et l'on garde le
    premier. C'est précisément pour ce cas que l'écran doit afficher la répartition obtenue avant
    de la valider — l'organisateur voit la poule de 7 et corrige sa taille s'il n'en veut pas.
    """
    monde = _Monde()
    monde.inscrire(7)
    phase_id = monde.regler(ReglageDePoules(taille_visee=4))

    assert monde.service().repartition(monde.tournoi_id, phase_id).tailles == (7,)


def test_la_repartition_se_lit_sans_salle_ni_plan_pose() -> None:
    """CA « la répartition obtenue est montrée **avant** d'être validée ».

    L'atelier affiche la répartition en direct sous la fiche de réglages. Exiger un gabarit de
    salle ou un plan posé pour la calculer rendrait le CA infaisable : l'organisateur règle ses
    poules des semaines avant de faire sa salle. Le décor de ce test n'appelle donc **jamais**
    `regenerer_plan`, et c'est tout son objet.
    """
    monde = _Monde()
    monde.inscrire(12)
    phase_id = monde.regler(ReglageDePoules(taille_visee=4))

    repartition = monde.service().repartition(monde.tournoi_id, phase_id)

    assert repartition.nb_poules == 3
    assert monde.placements.par_phase(phase_id) == []


# --- CA « une poule occupe un bloc de couloirs contigus » ---------------------------------------


def test_une_poule_de_cinq_tient_sur_quatre_couloirs_comme_une_poule_de_quatre() -> None:
    """L'arbitrage qui surprend (CA du 09/08/2026) : l'empreinte est le **parallélisme**.

    La méthode du cercle ne fait tirer que `effectif ÷ 2` rencontres par tour — à effectif impair,
    un membre se repose. Une poule de 5 ne met donc que 4 archers sur la ligne. Réserver un couloir
    par membre aurait fait déborder toute poule impaire sans raison, et décalé la salle entière d'un
    cran par poule.
    """
    monde = _Monde()
    monde.inscrire(10)  # 10 en poules de 4 → 2 poules de 5
    phase_id = monde.regler(ReglageDePoules(taille_visee=4))

    etat = monde.service().regenerer_plan(monde.tournoi_id, phase_id)

    assert etat.repartition.tailles == (5, 5)
    assert [poule.bloc.nb_couloirs for poule in etat.poules if poule.bloc] == [4, 4]


def test_la_poule_suivante_demarre_au_couloir_libre_juste_apres() -> None:
    """CA : une poule qui déborde n'ouvre **pas** une cible neuve pour la suivante.

    Avec des poules de 6 sur des cibles de 4, la poule 1 prend la cible 1 entière puis deux couloirs
    de la cible 2 ; la poule 2 démarre au couloir C de cette même cible 2. La salle se remplit en
    continu, sans trou — règle donnée par le commanditaire le 09/08/2026.
    """
    monde = _Monde()
    monde.inscrire(12)
    phase_id = monde.regler(ReglageDePoules(taille_visee=6))

    etat = monde.service().regenerer_plan(monde.tournoi_id, phase_id)

    premiere, seconde = (poule.bloc for poule in etat.poules)
    assert premiere is not None and seconde is not None
    assert premiere.places == ((1, "A"), (1, "B"), (1, "C"), (1, "D"), (2, "A"), (2, "B"))
    assert seconde.places[0] == (2, "C")


def test_une_salle_trop_petite_rapporte_les_poules_non_posees() -> None:
    """Le placement **rapporte** ce qu'il n'a pas pu faire au lieu de tronquer en silence.

    Même parti que `PlanDeCibles.conflits` en qualification (ADR-0024) : l'organisateur doit voir à
    l'atelier qu'une poule n'a pas de cible, pas le découvrir le jour J.
    """
    monde = _Monde(nb_cibles=2)  # 8 couloirs pour 3 poules de 4 → la 3ᵉ ne tient pas
    monde.inscrire(12)
    phase_id = monde.regler(ReglageDePoules(taille_visee=4))

    etat = monde.service().regenerer_plan(monde.tournoi_id, phase_id)

    assert [conflit.groupe for conflit in etat.conflits] == [3]


# --- CA « les rencontres se saisissent comme des duels ordinaires » -----------------------------


def test_les_rencontres_sont_presentees_par_tour_et_numerotees_de_facon_continue() -> None:
    """CA : « les rencontres sont présentées **par tour**, l'ordre que le moteur produit déjà ».

    C'est le tour qui garantit qu'un archer ne figure pas deux fois dans le même tour, donc que le
    tour se tire en parallèle. La numérotation, elle, est continue sur toute la phase : c'est ce
    qui permet à la table `duel` de porter les rencontres de tous les groupes sans les distinguer —
    donc de réutiliser `(phase_id, match_numero)` tel quel, sans table ni migration neuve.
    """
    monde = _Monde()
    monde.inscrire(8)
    phase_id = monde.regler(ReglageDePoules(taille_visee=4))

    etat = monde.service().etat(monde.tournoi_id, phase_id)

    numeros = [r.numero for poule in etat.poules for r in poule.rencontres]
    assert numeros == list(range(1, len(numeros) + 1))
    for poule in etat.poules:
        # Une poule de 4 : 3 tours de 2 rencontres, et aucun archer deux fois dans un tour.
        assert [r.tour for r in poule.rencontres] == [1, 1, 2, 2, 3, 3]
        for tour in (1, 2, 3):
            du_tour = [r for r in poule.rencontres if r.tour == tour]
            archers = [d.archer_id for r in du_tour for d in (r.haut, r.bas) if d is not None]
            assert len(archers) == len(set(archers))


def test_chaque_rencontre_porte_les_deux_couloirs_de_ses_adversaires() -> None:
    """Les couloirs d'une rencontre sont **dérivés** du bloc, pas persistés (ADR-0083 §3).

    Les deux adversaires sont côte à côte — même intention qu'ADR-0048 pour un tableau, obtenue ici
    sans réordonnancement puisque le bloc est contigu par construction. La *n*-ième rencontre d'un
    tour prend les couloirs 2n et 2n+1 du bloc, et la numérotation **repart à chaque tour** : sinon
    la poule glisserait d'un cran par tour et déborderait de son propre bloc.
    """
    monde = _Monde()
    monde.inscrire(4)
    phase_id = monde.regler(ReglageDePoules(taille_visee=4))

    etat = monde.service().regenerer_plan(monde.tournoi_id, phase_id)

    (poule,) = etat.poules
    par_tour = {tour: [r for r in poule.rencontres if r.tour == tour] for tour in (1, 2, 3)}
    for rencontres in par_tour.values():
        assert [r.couloirs for r in rencontres] == [((1, "A"), (1, "B")), ((1, "C"), (1, "D"))]


def test_une_rencontre_porte_le_pave_de_saisie_avant_tout_tir() -> None:
    """CA : « le scoreur retrouve le **pavé de saisie de duel** d'E04US013 ».

    Le pavé (barème par arme, zones du blason) est résolu par le **même** code que celui d'un duel
    de tableau : sans quoi le même archer tirerait en sets au tableau et en cumul en poule.
    """
    monde = _Monde()
    monde.inscrire(4)
    phase_id = monde.regler(ReglageDePoules(taille_visee=4))

    (poule,) = monde.service().etat(monde.tournoi_id, phase_id).poules

    assert all(r.bareme is not None for r in poule.rencontres)
    assert all(r.zones == ZONES_TRIPLE for r in poule.rencontres)
    assert all(r.duel is None for r in poule.rencontres)


# --- CA « deux régimes d'ex æquo, selon ce que la poule produit » -------------------------------


def test_une_poule_qui_classe_ne_signale_aucun_barrage_avant_le_premier_tir() -> None:
    """Avant tout tir, **tous** les membres sont à 0 partout, donc tous ex æquo.

    Signaler un barrage là annoncerait un départage à faire avant que la poule ait commencé — et un
    signal qui s'allume tout seul apprend à être ignoré. Le CA parle d'ex æquo « irréductible »,
    c'est-à-dire *après* que les cinq critères ont été appliqués à des rencontres réellement
    tirées.
    """
    monde = _Monde()
    monde.inscrire(4)
    phase_id = monde.regler(ReglageDePoules(taille_visee=4))

    (poule,) = monde.service().etat(monde.tournoi_id, phase_id).poules

    assert not poule.barrage_requis


def test_une_poule_non_reglee_refuse_de_se_composer() -> None:
    """Le type se choisit avant ses paramètres — mais on ne compose pas sans eux.

    C'est la contrepartie assumée du brouillon d'ADR-0063 : l'agrégat accepte une phase de poules
    non réglée (l'atelier doit pouvoir enregistrer un déroulé en cours de composition), et le refus
    arrive au moment d'en **jouer** une. `PhasePasReglee` est distinct de `PhasePasDesPoules` parce
    que la correction l'est aussi : ici le type est bon, il manque un réglage.
    """
    monde = _Monde()
    monde.inscrire(8)
    phase_id = monde.regler(None)

    with pytest.raises(PhasePasReglee):
        monde.service().etat(monde.tournoi_id, phase_id)


def test_une_phase_dun_autre_type_est_refusee() -> None:
    """Chaque décor de saisie refuse ce qui n'est pas le sien — filtre dérivé du contrat."""
    monde = _Monde()
    monde.inscrire(8)

    with pytest.raises(PhasePasDesPoules):
        monde.service().etat(monde.tournoi_id, monde.qualif_id)


# --- CA « la phase avale consomme les qualifiés » ------------------------------------------------


def test_une_poule_qui_ne_qualifie_pas_ne_designe_personne() -> None:
    """`nb_qualifies` vide = « la poule **classe**, elle ne qualifie pas ».

    La sélection se fait alors par un prélèvement de la phase avale, qui lit le classement de la
    poule comme celui de n'importe quelle phase classante (E05US024). Rien n'est « qualifié » au
    sens du champ : inventer deux qualifiés par défaut serait deviner à la place de l'organisateur,
    ce que le commanditaire a explicitement refusé le 31/07/2026.
    """
    monde = _Monde()
    monde.inscrire(8)
    phase_id = monde.regler(ReglageDePoules(taille_visee=4))

    etat = monde.service().etat(monde.tournoi_id, phase_id)

    assert all(poule.qualifies == () for poule in etat.poules)


# --- CA « la poule se classe » (référentiel §10.1) -----------------------------------------------


def _gagner(service: ServicePoules, monde: _Monde, numero: int, cote: str) -> None:
    """Fait gagner 6-0 le camp `cote` de la rencontre `numero` (3 manches), puis valide."""
    haut = ("10", "10", "10") if cote == "haut" else ("6", "6", "6")
    bas = ("6", "6", "6") if cote == "haut" else ("10", "10", "10")
    for manche in (1, 2, 3):
        service.saisir_manche(
            monde.tournoi_id,
            monde.phase_id,
            numero,
            manche,
            tuple(ZoneScore(v) for v in haut),
            tuple(ZoneScore(v) for v in bas),
        )
    service.valider(monde.tournoi_id, monde.phase_id, numero, "DURAND")


def test_une_rencontre_se_saisit_et_se_valide_comme_un_duel() -> None:
    """CA : « une poule n'invente pas une façon de tirer, seulement une façon d'apparier ».

    Le tir passe par l'agrégat `Duel` et la table `duel`, keyée `(phase_id, match_numero)` — sans
    table ni migration supplémentaires (ADR-0083 §7). Ce qui diffère d'un duel de tableau est la
    *navigation*, pas le tir.
    """
    monde = _Monde()
    monde.inscrire(4)
    phase_id = monde.regler(ReglageDePoules(taille_visee=4))
    service = monde.service()

    _gagner(service, monde, 1, "haut")

    (poule,) = service.etat(monde.tournoi_id, phase_id).poules
    premiere = poule.rencontres[0]
    assert premiere.duel is not None
    assert premiere.duel.verrouille


def test_seules_les_rencontres_validees_entrent_au_classement() -> None:
    """Un tir en cours de saisie ne doit pas faire bouger le classement à chaque flèche.

    Sinon le barrage requis apparaîtrait puis disparaîtrait sous les yeux du juge. Même parti que la
    reconstruction d'un tableau, qui ne rejoue que les duels validés.
    """
    monde = _Monde()
    monde.inscrire(4)
    phase_id = monde.regler(ReglageDePoules(taille_visee=4))
    service = monde.service()

    service.saisir_manche(
        monde.tournoi_id,
        phase_id,
        1,
        1,
        (ZoneScore.DIX, ZoneScore.DIX, ZoneScore.DIX),
        (ZoneScore.SIX, ZoneScore.SIX, ZoneScore.SIX),
    )

    (poule,) = service.etat(monde.tournoi_id, phase_id).poules
    assert all(ligne.decompte.points_match == 0 for ligne in poule.classement)


def test_le_bareme_de_points_de_match_classe_la_poule() -> None:
    """CA : « un barème de points attribue les victoires, nuls et défaites » (défaut 3 / 1 / 0).

    Une poule de 4 se joue en 3 tours de 2 rencontres. On fait gagner le même archer partout où il
    figure : il doit finir premier avec 3 victoires, soit 9 points de match.
    """
    monde = _Monde()
    monde.inscrire(4)
    phase_id = monde.regler(ReglageDePoules(taille_visee=4))
    service = monde.service()
    (poule,) = service.etat(monde.tournoi_id, phase_id).poules
    vainqueur = poule.rencontres[0].haut
    assert vainqueur is not None

    for rencontre in poule.rencontres:
        if rencontre.haut is not None and rencontre.haut.archer_id == vainqueur.archer_id:
            _gagner(service, monde, rencontre.numero, "haut")
        elif rencontre.bas is not None and rencontre.bas.archer_id == vainqueur.archer_id:
            _gagner(service, monde, rencontre.numero, "bas")

    (poule,) = service.etat(monde.tournoi_id, phase_id).poules
    tete = poule.classement[0]
    assert tete.participant.ref_id == vainqueur.archer_id
    assert tete.rang == 1
    assert tete.decompte.points_match == 9


def test_une_poule_qui_qualifie_designe_ses_premiers() -> None:
    """CA « la phase avale consomme les qualifiés » : `nb_qualifies = k` désigne les k premiers."""
    monde = _Monde()
    monde.inscrire(4)
    phase_id = monde.regler(ReglageDePoules(taille_visee=4, nb_qualifies=1))
    service = monde.service()
    (poule,) = service.etat(monde.tournoi_id, phase_id).poules
    vainqueur = poule.rencontres[0].haut
    assert vainqueur is not None

    for rencontre in poule.rencontres:
        if rencontre.haut is not None and rencontre.haut.archer_id == vainqueur.archer_id:
            _gagner(service, monde, rencontre.numero, "haut")
        elif rencontre.bas is not None and rencontre.bas.archer_id == vainqueur.archer_id:
            _gagner(service, monde, rencontre.numero, "bas")
        else:
            _gagner(service, monde, rencontre.numero, "haut")

    (poule,) = service.etat(monde.tournoi_id, phase_id).poules
    assert [q.archer_id for q in poule.qualifies] == [vainqueur.archer_id]


# --------------------------------------------------------------------------------------------
# CA — « le verdict du barrage referme le classement de la poule »
# --------------------------------------------------------------------------------------------
#
# ⚠️ Ces tests **manquaient**, et c'est leur absence qui a laissé passer un bloquant : le double
# `_FauxBarrageRepository` existait, déclaré, et n'était peuplé par aucun test.
# `_verdicts_de_barrage` et `_appliquer_verdicts` n'avaient donc **aucune** couverture, à
# aucun niveau — alors qu'ils portent le CA central de l'US, celui qui ferme la boucle
# que `DETTE-028` laissait ouverte.
#
# Ils sont écrits depuis le CA (« le barrage se tire et se saisit », « le verdict referme ce
# classement »), pas depuis le code : chacun décrit ce que l'organisateur observe.


def _barrage_de_poule(
    monde: _Monde,
    phase_id: int | None,
    rang_dispute: int | None,
    archers: list[int],
    scores: list[int],
) -> BarrageDePlaces:
    """Un barrage de portée `poule`, tiré en une manche — le geste de l'organisateur, en objet.

    `phase_id` et `rang_dispute` sont **paramétrés** parce que ce sont eux qui décident si le
    verdict s'applique : les passer en dur aurait masqué les deux pannes que ces tests ancrent.
    """
    participants = tuple(Participant.individuel(archer_id) for archer_id in archers)
    return BarrageDePlaces(
        depart_id=monde.depart_id,
        portee=PorteeBarrage.POULE,
        participants=participants,
        cree_le=datetime.datetime(2026, 8, 10, 9, 0, tzinfo=datetime.UTC),
        manches=(
            tuple(
                TirBarrage(participant, score)
                for participant, score in zip(participants, scores, strict=True)
            ),
        ),
        rang_dispute=rang_dispute,
        phase_id=phase_id,
    )


def _poule_a_deux_ex_aequo(monde: _Monde) -> tuple[ServicePoules, int, list[int]]:
    """Une poule de 3 où les trois se battent en cycle : personne ne se détache, tout est ex æquo.

    Le cycle à trois (A bat B, B bat C, C bat A) est le cas d'égalité **irréductible** par
    excellence — les cinq critères du §10.1 rendent le même décompte pour les trois. C'est
    exactement la situation que le CA destine au barrage.
    """
    monde.inscrire(3)
    phase_id = monde.regler(ReglageDePoules(taille_visee=3))
    service = monde.service()
    (poule,) = service.etat(monde.tournoi_id, phase_id).poules
    membres = sorted(membre.archer_id for membre in poule.membres)
    # Le **cycle** : chacun bat le suivant, le dernier bat le premier. Chaque membre finit à une
    # victoire et une défaite, avec les mêmes sets, le même score et les mêmes 10 — les cinq
    # critères du §10.1 rendent donc le même décompte pour les trois. Faire gagner « le haut »
    # partout, au contraire, produit un ordre net : le décor doit construire l'égalité, pas
    # l'espérer.
    suivant = {membres[i]: membres[(i + 1) % 3] for i in range(3)}
    for rencontre in poule.rencontres:
        assert rencontre.haut is not None and rencontre.bas is not None
        vainqueur = (
            "haut" if suivant[rencontre.haut.archer_id] == rencontre.bas.archer_id else "bas"
        )
        _gagner(service, monde, rencontre.numero, vainqueur)
    (poule,) = service.etat(monde.tournoi_id, phase_id).poules
    return service, phase_id, [ligne.participant.ref_id for ligne in poule.classement]


def test_sans_barrage_les_ex_aequo_dune_poule_restent_partages() -> None:
    """L'état de départ : le moteur **signale** l'égalité, il ne la tranche pas tout seul."""
    monde = _Monde()
    service, phase_id, _ = _poule_a_deux_ex_aequo(monde)

    (poule,) = service.etat(monde.tournoi_id, phase_id).poules

    assert poule.barrage_requis is True
    assert any(ligne.ex_aequo for ligne in poule.classement)


def test_le_verdict_dun_barrage_de_poule_referme_le_classement() -> None:
    """CA — « le verdict **referme le classement** de la poule concernée ».

    C'est la boucle complète : une poule finit à égalité, l'organisateur fait tirer un barrage de
    portée `poule` sur cette phase et sur le rang partagé, et le classement cesse d'être ex æquo.
    """
    monde = _Monde()
    service, phase_id, archers = _poule_a_deux_ex_aequo(monde)
    (poule,) = service.etat(monde.tournoi_id, phase_id).poules
    rang_partage = min(ligne.rang for ligne in poule.classement if ligne.ex_aequo)

    monde.barrages.barrages.append(
        _barrage_de_poule(monde, phase_id, rang_partage, archers, scores=[10, 9, 8])
    )

    (poule,) = service.etat(monde.tournoi_id, phase_id).poules
    assert [ligne.rang for ligne in poule.classement] == sorted(
        ligne.rang for ligne in poule.classement
    )
    assert not any(
        ligne.ex_aequo for ligne in poule.classement
    ), "le verdict a été tiré et clos : plus aucun rang ne doit rester partagé"
    assert poule.barrage_requis is False


def test_un_barrage_qui_ne_designe_pas_sa_phase_ne_referme_rien() -> None:
    """⚠️ Le bloquant, retourné en oracle : **sans `phase_id`, le verdict n'est pas applicable**.

    C'est la première des deux pannes qu'avait le formulaire d'annonce. Le service filtre les
    barrages sur l'égalité des phases, et `None` n'égale aucune phase : le barrage se tirait, se
    clôturait, et le classement restait ex æquo — sans le moindre message. Le test l'ancre pour que
    le filtre ne se relâche pas « pour faire marcher un cas ».
    """
    monde = _Monde()
    service, phase_id, archers = _poule_a_deux_ex_aequo(monde)

    monde.barrages.barrages.append(_barrage_de_poule(monde, None, 1, archers, scores=[10, 9, 8]))

    (poule,) = service.etat(monde.tournoi_id, phase_id).poules
    assert poule.barrage_requis is True
    assert any(ligne.ex_aequo for ligne in poule.classement)


def test_un_barrage_sans_rang_dispute_ne_referme_rien() -> None:
    """⚠️ La **seconde** panne, indépendante de la première.

    Même sur la bonne phase, un barrage sans `rang_dispute` rend un verdict d'ordre vide (c'est le
    régime Big Shoot Off, qui désigne un sortant et non une place). Corriger `phase_id` seul aurait
    donné un correctif qui paraît juste et ne referme toujours rien.
    """
    monde = _Monde()
    service, phase_id, archers = _poule_a_deux_ex_aequo(monde)

    monde.barrages.barrages.append(
        _barrage_de_poule(monde, phase_id, None, archers, scores=[10, 9, 8])
    )

    (poule,) = service.etat(monde.tournoi_id, phase_id).poules
    assert poule.barrage_requis is True


def test_un_barrage_non_resolu_laisse_le_rang_partage() -> None:
    """Un barrage annoncé mais **pas encore tranché** n'apporte rien — et ne doit rien casser.

    Le classement reste partagé, et l'annonce reste affichée : c'est ce qui empêche l'écran de
    déclarer une poule close pendant que ses archers sont encore sur la ligne.
    """
    monde = _Monde()
    service, phase_id, archers = _poule_a_deux_ex_aequo(monde)

    monde.barrages.barrages.append(_barrage_de_poule(monde, phase_id, 1, archers, scores=[9, 9, 9]))

    (poule,) = service.etat(monde.tournoi_id, phase_id).poules
    assert poule.barrage_requis is True


# --------------------------------------------------------------------------------------------
# CA — les **deux régimes** d'ex æquo (ADR-0083 §5)
# --------------------------------------------------------------------------------------------
#
# « La poule qui **classe** départage tout ex æquo irréductible ; celle qui **qualifie** ne
# départage que la barre. » Seule la garde négative (« avant le premier tir, rien n'est signalé »)
# était couverte : les deux régimes eux-mêmes ne l'étaient ni l'un ni l'autre, y compris l'exemple
# que le CA donne verbatim (relevé en revue).


def _poule_de_quatre_avec_un_premier_net(monde: _Monde, nb_qualifies: int | None) -> ServicePoules:
    """Une poule de 4 : un premier qui gagne tout, et **trois autres en cycle** derrière lui.

    Le cycle rend les trois derniers irréductiblement ex æquo (une victoire, une défaite, mêmes
    sets, mêmes scores) pendant que le premier se détache proprement. C'est le décor qui permet de
    placer la barre **au-dessus** de l'égalité (rang 1) ou **dedans** (rang 2), donc de distinguer
    les deux régimes sur un même tirage.
    """
    monde.inscrire(4)
    phase_id = monde.regler(ReglageDePoules(taille_visee=4, nb_qualifies=nb_qualifies))
    service = monde.service()
    (poule,) = service.etat(monde.tournoi_id, phase_id).poules
    membres = sorted(membre.archer_id for membre in poule.membres)
    premier, autres = membres[0], membres[1:]
    suivant = {autres[i]: autres[(i + 1) % 3] for i in range(3)}

    for rencontre in poule.rencontres:
        assert rencontre.haut is not None and rencontre.bas is not None
        haut, bas = rencontre.haut.archer_id, rencontre.bas.archer_id
        if premier in (haut, bas):
            gagnant = "haut" if haut == premier else "bas"
        else:
            gagnant = "haut" if suivant[haut] == bas else "bas"
        _gagner(service, monde, rencontre.numero, gagnant)
    return service


def test_une_poule_qui_classe_departage_tout_ex_aequo_irreductible() -> None:
    """Régime « classe » (`nb_qualifies` non déclaré) : le classement **est** le livrable.

    Trois archers que les cinq critères ne séparent pas, aux rangs 2-3-4 : il n'y a pas de barre,
    donc l'égalité compte, où qu'elle soit.
    """
    monde = _Monde()
    service = _poule_de_quatre_avec_un_premier_net(monde, nb_qualifies=None)

    (poule,) = service.etat(monde.tournoi_id, monde.phase_id).poules

    assert poule.barrage_requis is True
    assert sum(1 for ligne in poule.classement if ligne.ex_aequo) == 3


def test_une_poule_qui_qualifie_ignore_une_egalite_entierement_sous_la_barre() -> None:
    """⚠️ **L'exemple du CA, verbatim** — et le seul cas qui distingue l'implémentation retenue
    de la lecture naïve « tout ex æquo se départage ».

    « Deux archers à égalité aux rangs 3-4 d'une poule qui en qualifie 2 restent à égalité. » Ici
    l'égalité tient les rangs 2-3-4 et la poule n'en qualifie qu'**un** : elle est entièrement sous
    la barre, donc aucun barrage n'est requis — et la qualification est pourtant décidée.
    """
    monde = _Monde()
    service = _poule_de_quatre_avec_un_premier_net(monde, nb_qualifies=1)

    (poule,) = service.etat(monde.tournoi_id, monde.phase_id).poules

    assert (
        poule.barrage_requis is False
    ), "une égalité qui ne franchit pas la barre ne se départage pas : le CA l'exige"
    assert len(poule.qualifies) == 1
    assert any(
        ligne.ex_aequo for ligne in poule.classement
    ), "l'égalité subsiste et reste visible — elle n'est simplement pas à trancher"


def test_une_poule_qui_qualifie_departage_une_egalite_qui_enjambe_la_barre() -> None:
    """L'autre versant : la barre tombe **dans** l'égalité, donc elle décide qui passe.

    Trois archers ex æquo aux rangs 2-3-4 et deux qualifiés : le second billet se joue entre eux,
    et il n'est pas attribuable sans barrage. La qualification reste donc **vide** tant qu'il n'a
    pas été tiré — un billet attribué au hasard serait pire qu'un billet en attente.
    """
    monde = _Monde()
    service = _poule_de_quatre_avec_un_premier_net(monde, nb_qualifies=2)

    (poule,) = service.etat(monde.tournoi_id, monde.phase_id).poules

    assert poule.barrage_requis is True
    assert poule.qualifies == ()


def test_un_seuil_de_barrage_ne_remplace_pas_l_ordre_de_classement_d_une_poule() -> None:
    """⚠️ Un seuil de barrage **ajoute** un cran de départage, il ne change pas la règle sportive.

    Le §10.1 (points de match, différence de sets, différence de score, 10, 9) **précède** le §8.1
    (10, puis 9) de trois critères — le référentiel avertit explicitement de ne pas confondre les
    deux ordres. Un `barrage_jusqu_au` réglé sur la phase doit donc **envelopper** `TiebreakPoules`,
    jamais s'y substituer.

    Le décor sépare exprès les deux ordres, ce qu'un décor naïf ne fait pas : le vainqueur gagne
    ses trois manches **27 à 26**, sans un seul 10, pendant que le battu en aligne six. Sous §10.1
    il est premier (3 points de match contre 0) ; sous §8.1 il serait **dernier**. Un décor où le
    gagnant tire des 10 corrèle les deux critères et ne prouve rien — c'est le piège dans lequel la
    première version de ce test est tombée.

    Il **échoue** sur le premier correctif de revue : celui-ci résolvait bien la politique par le
    registre — ce qu'on lui demandait — mais laissait la fabrique retomber sur son défaut
    `ffta_defaut`, si bien que tout le classement de poule se triait soudain au nombre de 10.
    Rendre une politique opérante en lui faisant appliquer la mauvaise règle est pire que la
    laisser décorative : c'est faux **et** silencieux.
    """
    monde = _Monde()
    monde.inscrire(2)
    phase_id = monde.regler(ReglageDePoules(taille_visee=2), barrage_jusqu_au=2)
    service = monde.service()
    (poule,) = service.etat(monde.tournoi_id, phase_id).poules
    (rencontre,) = poule.rencontres
    assert rencontre.haut is not None

    # Le haut gagne chaque manche 27-26 **sans aucun 10** ; le bas en tire six et perd.
    for manche in (1, 2, 3):
        service.saisir_manche(
            monde.tournoi_id,
            phase_id,
            rencontre.numero,
            manche,
            (ZoneScore("9"), ZoneScore("9"), ZoneScore("9")),
            (ZoneScore("10"), ZoneScore("10"), ZoneScore("6")),
        )
    service.valider(monde.tournoi_id, phase_id, rencontre.numero, "DURAND")

    (poule,) = service.etat(monde.tournoi_id, phase_id).poules
    tete = poule.classement[0]

    assert tete.participant.ref_id == rencontre.haut.archer_id, (
        "le vainqueur des trois manches est premier de sa poule, même sans un seul 10 : "
        "un seuil de barrage enveloppe l'ordre §10.1, il ne lui substitue pas le §8.1"
    )
    assert tete.decompte.points_match == 3
    assert tete.decompte.nb_dix == 0
    assert (
        poule.classement[1].decompte.nb_dix == 6
    ), "le battu aligne bien plus de 10 : c'est ce qui rend les deux ordres discriminables"


def test_une_rencontre_dont_les_duellistes_ont_change_est_signalee_bloquee() -> None:
    """Un tir masqué (ADR-0049 §4) doit se **voir** comme bloqué, pas comme « à tirer ».

    Masquer un score dont les duellistes ne correspondent plus est juste — l'attribuer au mauvais
    couple serait pire. Mais la rencontre s'affichait alors exactement comme une rencontre jamais
    commencée, et le service refusait l'écriture en 409 : l'écran invitait à saisir ce qu'il allait
    refuser. Le drapeau distingue les deux cas (correctif de revue).

    Le décor recompose la phase sous un tir déjà validé — un archer de plus, et le serpent
    redistribue les groupes.
    """
    monde = _Monde()
    monde.inscrire(4)
    phase_id = monde.regler(ReglageDePoules(taille_visee=4))
    service = monde.service()
    (poule,) = service.etat(monde.tournoi_id, phase_id).poules
    numero = poule.rencontres[0].numero
    _gagner(service, monde, numero, "haut")

    avant = service.etat(monde.tournoi_id, phase_id).poules[0].rencontres[0]
    assert avant.duel is not None
    assert avant.desynchronisee is False

    # Quatre archers de plus : deux poules de 4, le serpent redistribue, donc d'autres
    # appariements portent les mêmes numéros de rencontre.
    monde.inscrire(4)

    rencontres = [r for p in service.etat(monde.tournoi_id, phase_id).poules for r in p.rencontres]
    bloquees = [r for r in rencontres if r.desynchronisee]

    assert bloquees, "la recomposition doit désynchroniser au moins la rencontre déjà tirée"
    assert all(
        r.duel is None for r in bloquees
    ), "le tir reste masqué : on ne prête pas un score au mauvais couple"
