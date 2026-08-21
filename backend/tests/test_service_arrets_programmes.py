"""Service **Arrêts programmés** — le déclencheur, le gel, la reprise (E05US033, [ADR-0091]).

Tests écrits **depuis le CA** (règle 9), avant l'implémentation. Le domaine
(`test_domain_arret_programme.py`) décide *quand* un arrêt est dû ; ce fichier-ci décide *quelle
phase passe en pause* et *ce qu'un geste d'admin rend*. Le troisième volet — **ce que la pause
interdit** — est dans `test_service_saisie.py` (section E05US033), là où le montage de saisie existe
déjà : il n'y avait pas de raison d'en remonter un second ici.

⚠️ **L'oracle du gel n'est pas le code existant, et c'est le point à comprendre avant de lire.** Au
cadrage du 19/08/2026, la vérification a montré que `StatutPhase.EN_PAUSE` **ne gelait rien** :
aucune garde dans `application/saisie.py`, aucune dans `application/saisie_duels.py`, et
`application/routage.py` traitait une phase en pause comme une phase en cours (filtre `statut is not
TERMINEE`). La pause était **cosmétique** — un libellé dans le suivi. Un test écrit en lisant ce
code aurait donc consacré une pause qui n'arrête personne, et l'US aurait livré une étiquette. La
fiche l'annonçait à l'envers (« `EN_PAUSE` gèle la validation » y figurait comme un piège **à
vérifier**) : c'est le cas d'école de la règle 9 — le CA, pas le code.

Deux gardes portent l'essentiel :

- `test_relancer_ne_remet_pas_la_phase_en_pause_aussitot` est le pendant service du piège structurel
  du domaine, et l'oracle y est le plus fort possible : on relance, **on rappelle le déclencheur**,
  et la phase doit toujours être en cours. C'est la séquence exacte de la salle — la validation
  suivante rappelle le déclencheur quelques secondes après la reprise.
- `test_un_arret_de_depart_ne_coupe_pas_une_phase_au_milieu_de_son_tour` tient l'arbitrage du
  commanditaire du 18/08/2026. Un arrêt qui couperait net serait *plus simple à écrire* et faux : il
  interromprait un duel engagé.

[ADR-0091]: ../../docs/adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.arrets_programmes import ServiceArretsProgrammes
from application.erreurs import ArretIntrouvable
from domain.arret_programme import (
    ArretDeCirconstance,
    ArretProgramme,
    EtatFranchissement,
    FranchissementArret,
    PorteeArret,
    doublon_d_arret,
)
from domain.bareme import BaremeQualification
from domain.depart import Depart, DepartId
from domain.erreurs import ArretProgrammeInvalide
from domain.grain_validation import GrainValidation, TypeGrain
from domain.phase import Phase, PhaseId, StatutPhase, TypePhase
from domain.suisse import ConfigurationSuisse
from domain.suivi_deroule import AvancementDePhase
from domain.tournoi import Tournoi, TypeTournoi
from tests.conftest import (
    FauxDepartRepository,
    FauxDerouleRepository,
    FauxPhaseRepository,
    poser_phase_factice,
)

_DATE = datetime.date(2026, 11, 14)


class FauxTournoiRepository:
    """Double de `TournoiRepository` : seul `par_id` sert ici (le reste conforme le port).

    Locale, comme dans les autres fichiers de tests qui en ont besoin — elle n'est pas hissée au
    `conftest`. Ce n'est pas un choix : c'est un constat, et la duplication est réelle (au moins
    trois copies). La hisser demanderait de réconcilier trois comportements légèrement différents,
    ce qui est un geste de refactoring à part entière — hors du périmètre d'une US de moteur.
    """

    def __init__(self) -> None:
        self._items: dict[int, Tournoi] = {}
        self._sequence = 0

    def par_id(self, tournoi_id: int) -> Tournoi | None:
        return self._items.get(tournoi_id)

    def ajouter(self, tournoi: Tournoi) -> Tournoi:
        self._sequence += 1
        persiste = dataclasses.replace(tournoi, id=self._sequence)
        self._items[self._sequence] = persiste
        return persiste

    def lister(self) -> list[Tournoi]:
        return list(self._items.values())

    def enregistrer(self, tournoi: Tournoi) -> Tournoi:
        assert tournoi.id in self._items
        self._items[tournoi.id] = tournoi
        return tournoi

    def supprimer(self, tournoi_id: int) -> None:
        self._items.pop(tournoi_id, None)


# ─────────────────────────────────── Décor ───────────────────────────────────


class FauxSuivi:
    """Doublure de la couture d'avancement : « quel tour tourne dans chaque phase de ce créneau ? ».

    ⚠️ **Elle double `ServiceSuiviDeroule`, seul endroit du projet sachant répondre pour *tous* les
    formats** — tableau compris, dont l'avancement n'est pas rendu par un `LecteurAvancementDePhase`
    mais reconstruit sur place (ADR-0090 §5). C'est la raison pour laquelle le service d'arrêts
    passe par lui plutôt que de tenir son propre registre par type : un second mécanisme de
    résolution par type aurait été la **quatrième** occurrence de la même idée, ce dont la docstring
    du port met explicitement en garde.

    On pilote ici des `tour_courant` à la main : l'oracle du CA porte sur *« le tour est fini »*,
    pas sur la façon dont chacun des six formats le calcule — six calculs déjà couverts par les
    tests de leurs services respectifs. Doubler le calcul ici ne prouverait rien de neuf et rendrait
    ces tests solidaires de six implémentations.
    """

    def __init__(self) -> None:
        self.tours: dict[PhaseId, int | None] = {}
        # ⚠️ **`nb_tours` est pilotable, et ne l'était pas.** La première rédaction le codait à `9`
        # en dur, si bien qu'aucun test n'atteignait la signature du **repli** d'`avancement_bloc`
        # (`nb_tours=1, tour_courant=None`, qui veut dire « je ne sais pas »). Les quatre axes de
        # revue ont relevé que c'est exactement ce que la doublure masquait : trois bloquants sont
        # passés au travers de 3453 tests verts parce que la borne n'était pas atteignable.
        self.nb_tours: dict[PhaseId, int] = {}
        # Le créneau de chaque phase, alimenté par `Decor.poser` — voir `avancement_par_phase`.
        self.creneaux: dict[PhaseId, int] = {}
        self.appels = 0

    def avancement_par_phase(self, depart_id: int) -> dict[PhaseId, AvancementDePhase]:
        # ⚠️ **Cloisonne par créneau, et ne le faisait pas** (correctif de revue, axe B). La doublure
        # rendait **toutes** les phases enregistrées, quel que soit le créneau demandé. C'était
        # neutre tant que le décor n'en avait qu'un ; depuis que `Decor.poser(depart_id=…)` existe,
        # un service qui itérerait sur `avancements` au lieu de `phases` fuirait d'un créneau à
        # l'autre et resterait **vert** — sur le test dont c'est précisément le sujet. Même défaut
        # de doublure trop généreuse que celui documenté sur `nb_tours` juste au-dessus.
        self.appels += 1
        return {
            phase_id: AvancementDePhase(nb_tours=self.nb_tours.get(phase_id, 9), tour_courant=tour)
            for phase_id, tour in self.tours.items()
            if self.creneaux.get(phase_id, depart_id) == depart_id
        }


class FauxFranchissements:
    """Franchissements en mémoire, conformes au port `FranchissementArretRepository`."""

    def __init__(self) -> None:
        self.items: list[FranchissementArret] = []
        # Séquence décalée, pour la raison écrite dans `FauxPhaseRepository` : trois alias d'`int`
        # (`DETTE-044`) rendent vert par coïncidence tout service qui confondrait deux identifiants.
        self._sequence = 900

    def par_depart(self, depart_id: int) -> list[FranchissementArret]:
        return list(self.items)

    def ajouter(self, franchissement: FranchissementArret) -> FranchissementArret:
        self._sequence += 1
        persiste = dataclasses.replace(franchissement, id=self._sequence)
        self.items.append(persiste)
        return persiste

    def enregistrer(self, franchissement: FranchissementArret) -> FranchissementArret:
        self.items = [
            franchissement if item.id == franchissement.id else item for item in self.items
        ]
        return franchissement

    def par_id(self, franchissement_id: int) -> FranchissementArret | None:
        return next((item for item in self.items if item.id == franchissement_id), None)


class FauxArretsDeCirconstance:
    """Arrêts de circonstance en mémoire, conformes au port `ArretDeCirconstanceRepository`.

    ⚠️ **Elle filtre réellement par créneau**, et ce n'est pas de la coquetterie : c'est la propriété
    que le concept existe pour tenir (ADR-0092). Une doublure qui rendrait tout, comme le fait
    `FauxFranchissements.par_depart` — légitimement, celle-là n'ayant qu'un créneau à servir —
    rendrait vert un service qui aurait rangé l'arrêt au tournoi.
    """

    def __init__(self) -> None:
        self.items: list[ArretDeCirconstance] = []
        # Séquence décalée, comme les autres doublures du fichier : trois alias d'`int`
        # (`DETTE-044`) rendent vert par coïncidence tout service qui confondrait deux identifiants.
        self._sequence = 700

    def par_depart(self, depart_id: int) -> list[ArretDeCirconstance]:
        return [item for item in self.items if item.depart_id == depart_id]

    def ajouter(self, arret: ArretDeCirconstance) -> ArretDeCirconstance:
        # ⚠️ **Honore l'unicité que le schéma tient** (correctif de revue, axe adversarial). Le
        # contrat du port lève `ArretProgrammeInvalide` quand un arrêt occupe déjà ce tour ; une
        # doublure permissive laissait le chemin de **course** — celui que la contrainte SQL ferme,
        # double-clic ou deux postes d'admin — sans oracle nulle part au-dessus de l'adapter.
        if any(
            item.depart_id == arret.depart_id
            and item.phase_id == arret.phase_id
            and item.apres_tour == arret.apres_tour
            for item in self.items
        ):
            raise doublon_d_arret([arret.apres_tour])
        self._sequence += 1
        persiste = dataclasses.replace(arret, id=self._sequence)
        self.items.append(persiste)
        return persiste


class FauxHorloge:
    """Horloge **figée** conforme au port `Horloge` — règle 9 : pas d'horloge non maîtrisée.

    `avancer` sert au seul test qui a besoin de deux instants distincts (la pastille ne doit pas
    rajeunir). Partout ailleurs, l'intérêt est qu'elle ne bouge pas : l'oracle peut alors comparer à
    `horloge.instant` au lieu d'un intervalle, et le test dit ce qu'il veut dire.
    """

    def __init__(self) -> None:
        self.instant = datetime.datetime(2026, 11, 14, 10, 30, tzinfo=datetime.UTC)

    def maintenant(self) -> datetime.datetime:
        return self.instant

    def avancer(self, duree: datetime.timedelta) -> None:
        self.instant = self.instant + duree


class Decor:
    """Un tournoi, un créneau, et de quoi poser des phases et des arrêts sans base ni horloge."""

    def __init__(self) -> None:
        from application.phases import ServicePhases

        self.tournois = FauxTournoiRepository()
        tournoi = self.tournois.ajouter(
            Tournoi(nom="Kervignarc", date=_DATE, lieu=None, type_tournoi=TypeTournoi.NON_OFFICIEL)
        )
        assert tournoi.id is not None
        self.tournoi_id = tournoi.id
        self.departs = FauxDepartRepository()
        depart = self.departs.ajouter(
            Depart.creer(tournoi_id=tournoi.id, numero=1, tarif_centimes=800, horaire="09:00")
        )
        assert depart.id is not None
        self.depart_id = depart.id
        self.deroules = FauxDerouleRepository()
        self.phases = FauxPhaseRepository(self.departs, self.deroules)
        self.franchissements = FauxFranchissements()
        self.arrets_de_circonstance = FauxArretsDeCirconstance()
        self.horloge = FauxHorloge()
        self.suivi = FauxSuivi()
        self.service_phases = ServicePhases(self.tournois, self.phases, self.departs, self.deroules)
        self.service = ServiceArretsProgrammes(
            phases=self.phases,
            deroules=self.deroules,
            departs=self.departs,
            franchissements=self.franchissements,
            arrets_de_circonstance=self.arrets_de_circonstance,
            suivi=self.suivi,
            cycle_de_vie=self.service_phases,
            horloge=self.horloge,
        )

    def poser(
        self,
        ordre: int,
        type_phase: TypePhase = TypePhase.SUISSE,
        statut: StatutPhase = StatutPhase.EN_COURS,
        arrets: tuple[ArretProgramme, ...] = (),
        tour_courant: int | None = 1,
        nb_tours: int | None = None,
        depart_id: DepartId | None = None,
    ) -> PhaseId:
        """Pose une phase démarrée, son étape, ses arrêts, et son tour courant dans le suivi.

        ⚠️ **`nb_tours` est un paramètre du décor, et il ne l'était pas** (correctif de revue,
        axe B). `FauxSuivi` repliait sur `9`, et tous les tests posaient des arrêts aux tours 2 à
        5 : la borne `apres_tour >= nb_tours` n'était **jamais atteinte** par un arrêt existant,
        donc deux refus documentés n'avaient aucun oracle. Une doublure trop généreuse est un
        trou de couverture invisible — le même défaut que celui qui a rendu `nb_tours` pilotable,
        un cran plus loin.
        """
        # ⚠️ Le réglage suit `nb_tours` quand il est piloté : un suisse « réglé à 9 rondes » dont le
        # suivi annonce 5 tours est un état que le serveur ne peut pas produire, et c'est le genre
        # de fixture qui rendrait vert un futur code lisant `phase.suisse.nb_rondes` (revue, axe B).
        reglage = (
            ConfigurationSuisse(nb_rondes=nb_tours if nb_tours is not None else 9)
            if type_phase is TypePhase.SUISSE
            else None
        )
        # ⚠️ **Barème et grain ne sont donnés qu'à la qualification**, comme dans le décor du fichier
        # de domaine. Sans eux, `PhaseQualificationIncomplete` tombe **avant** la garde qu'on veut
        # lire ; avec eux partout, c'est `GrainIncompatibleAvecTypePhase` qui tombe sur les autres.
        # Le décor satisfait ces deux vérifications voisines, il ne les teste pas.
        qualification = type_phase is TypePhase.QUALIFICATION
        phase = poser_phase_factice(
            self.departs,
            self.deroules,
            self.phases,
            dataclasses.replace(
                Phase(
                    depart_id=depart_id if depart_id is not None else self.depart_id,
                    ordre=ordre,
                    type=type_phase,
                    suisse=reglage,
                    bareme=BaremeQualification.creer(10, 3) if qualification else None,
                    validation=(
                        GrainValidation(type=TypeGrain.FIN_DE_SERIE) if qualification else None
                    ),
                ),
                statut=statut,
            ),
        )
        assert phase.id is not None
        if arrets:
            etape = next(e for e in self.deroules.par_tournoi(self.tournoi_id) if e.ordre == ordre)
            self.deroules.enregistrer(dataclasses.replace(etape, arrets=arrets))
        self.suivi.tours[phase.id] = tour_courant
        self.suivi.creneaux[phase.id] = depart_id if depart_id is not None else self.depart_id
        if nb_tours is not None:
            self.suivi.nb_tours[phase.id] = nb_tours
        return phase.id

    def statut(self, phase_id: PhaseId) -> StatutPhase:
        phase = self.phases.par_id(phase_id)
        assert phase is not None
        return phase.statut


@pytest.fixture
def decor() -> Decor:
    return Decor()


# ─────────────────────── CA : l'enchaînement automatique reste le défaut ───────────────────────


def test_une_phase_sans_arret_ne_passe_jamais_en_pause(decor: Decor) -> None:
    """CA — *« une phase sans arrêt programmé se comporte exactement comme aujourd'hui »*.

    La garde de non-régression de la livraison : aucune phase déjà en cours le jour du déploiement
    ne change de comportement. On fait avancer le tour de 1 à 9 et rien ne doit bouger.
    """
    phase_id = decor.poser(ordre=1, arrets=())

    for tour in range(1, 10):
        decor.suivi.tours[phase_id] = tour
        assert decor.service.evaluer(decor.depart_id) == ()

    assert decor.statut(phase_id) is StatutPhase.EN_COURS


def test_un_arret_ne_coupe_rien_avant_que_son_tour_soit_fini(decor: Decor) -> None:
    """CA — l'arrêt est posé *après le tour 3* : les tours 1 à 3 se jouent normalement.

    ⚠️ Le tour 3 **en cours** ne déclenche pas : c'est le tour 3 **fini** qui déclenche, ce que le
    suivi exprime en passant à `tour_courant = 4`. Confondre les deux couperait la salle un tour
    trop tôt — une pause repas au milieu de la ronde 3.
    """
    phase_id = decor.poser(ordre=1, arrets=(ArretProgramme(apres_tour=3),), tour_courant=1)

    for tour in (1, 2, 3):
        decor.suivi.tours[phase_id] = tour
        assert decor.service.evaluer(decor.depart_id) == ()
        assert decor.statut(phase_id) is StatutPhase.EN_COURS

    decor.suivi.tours[phase_id] = 4
    assert decor.service.evaluer(decor.depart_id) == (phase_id,)
    assert decor.statut(phase_id) is StatutPhase.EN_PAUSE


def test_une_phase_dont_tout_est_joue_consomme_son_arret_sans_se_mettre_en_pause(
    decor: Decor,
) -> None:
    """Cas limite : `tour_courant is None` signifie *« plus rien ne tourne »* (ADR-0090).

    L'arrêt est bien **dû** — la frontière de tour a été franchie, le déclencheur ne l'a simplement
    pas vue passer (évaluation sautée, lot de validations, reprise après incident). Mais il n'y a
    plus rien à interrompre : mettre la phase en pause la figerait alors que tout est tiré, et
    l'organisateur devrait la relancer **pour pouvoir la clôturer**. Une pause qui ne suspend
    rien et ajoute un geste obligatoire est une régression, pas un service.

    L'arrêt est donc traité comme un **manqué** : tracé, jamais réarmé, journalisé — ce qui est
    exactement sa nature. Correctif de 2ᵉ passe, axe adversarial : la première rédaction mettait la
    phase en pause, et un test consacrait ce comportement.
    """
    phase_id = decor.poser(ordre=1, arrets=(ArretProgramme(apres_tour=8),), tour_courant=None)

    assert decor.service.evaluer(decor.depart_id) == ()
    assert decor.statut(phase_id) is StatutPhase.EN_COURS
    # Tracé quand même : sans quoi il se redéclencherait à chaque validation suivante.
    trace = decor.franchissements.items
    assert [(f.apres_tour, f.etat) for f in trace] == [(8, EtatFranchissement.LEVE)]
    # Et il ne réapparaît pas dans la liste de relance : il n'y a aucun bouton à offrir.
    assert decor.service.en_attente_de_relance(decor.depart_id) == ()


# ────────────────────────── CA : la portée, et le tour qu'on laisse finir
# ──────────────────────────


def test_un_arret_de_portee_phase_ne_touche_pas_les_autres_phases(decor: Decor) -> None:
    """CA — *« cette phase seule »* : couper une phase n'éteint pas la salle."""
    coupee = decor.poser(ordre=1, arrets=(ArretProgramme(apres_tour=2),), tour_courant=3)
    voisine = decor.poser(ordre=2, tour_courant=1)

    assert decor.service.evaluer(decor.depart_id) == (coupee,)
    assert decor.statut(voisine) is StatutPhase.EN_COURS


def test_un_arret_de_depart_ne_coupe_pas_une_phase_au_milieu_de_son_tour(decor: Decor) -> None:
    """CA — *« un arrêt de portée départ laisse chaque phase finir son tour en cours »*.

    ⚠️ **Arbitrage du commanditaire du 18/08/2026, et c'est le test qui l'exige.** Un arrêt qui
    couperait net serait plus simple à écrire — et il interromprait un duel engagé, quelqu'un l'arc
    levé. La salle s'éteint en quelques minutes, pas d'un coup.

    La phase déclenchante s'arrête **tout de suite** : son tour vient précisément de finir.
    """
    declenchante = decor.poser(
        ordre=1, arrets=(ArretProgramme(apres_tour=2, portee=PorteeArret.DEPART),), tour_courant=3
    )
    en_cours_de_tour = decor.poser(ordre=2, tour_courant=5)

    arretees = decor.service.evaluer(decor.depart_id)

    assert arretees == (declenchante,)
    assert decor.statut(declenchante) is StatutPhase.EN_PAUSE
    assert decor.statut(en_cours_de_tour) is StatutPhase.EN_COURS

    # Le tour 5 de la voisine se termine : elle s'arrête alors, sans nouvel arrêt programmé.
    decor.suivi.tours[en_cours_de_tour] = 6
    assert decor.service.evaluer(decor.depart_id) == (en_cours_de_tour,)
    assert decor.statut(en_cours_de_tour) is StatutPhase.EN_PAUSE


def test_un_arret_de_depart_est_franchi_quand_toutes_ses_phases_sont_arretees(
    decor: Decor,
) -> None:
    """L'arrêt reste `ARME` tant qu'une phase tire encore, puis devient `FRANCHI`.

    C'est cet état qui distingue « la coupe est décidée » de « la coupe est faite », et c'est lui
    que le pilotage lira pour savoir qu'il y a quelque chose à relancer.
    """
    declenchante = decor.poser(
        ordre=1, arrets=(ArretProgramme(apres_tour=2, portee=PorteeArret.DEPART),), tour_courant=3
    )
    voisine = decor.poser(ordre=2, tour_courant=5)

    decor.service.evaluer(decor.depart_id)
    assert [f.etat for f in decor.franchissements.items] == [EtatFranchissement.ARME]

    decor.suivi.tours[voisine] = 6
    decor.service.evaluer(decor.depart_id)

    (franchissement,) = decor.franchissements.items
    assert franchissement.etat is EtatFranchissement.FRANCHI
    assert set(franchissement.phases_arretees) == {declenchante, voisine}


def test_un_arret_de_depart_n_arrete_pas_une_phase_pas_encore_demarree(decor: Decor) -> None:
    """Une phase `à venir` n'a rien à interrompre — et elle ne doit pas non plus être empêchée.

    ⚠️ Le point sensible est **ce que l'arrêt ne fait pas** : il ne marque pas la phase future. Une
    phase qui démarre après la coupe démarre normalement. Le CA ne demande pas de geler l'avenir du
    créneau, seulement d'arrêter ce qui tire — et l'organisateur qui démarre une phase pendant une
    pause fait un geste explicite qu'on n'a pas à contredire.
    """
    declenchante = decor.poser(
        ordre=1, arrets=(ArretProgramme(apres_tour=2, portee=PorteeArret.DEPART),), tour_courant=3
    )
    future = decor.poser(ordre=2, statut=StatutPhase.A_VENIR, tour_courant=None)

    assert decor.service.evaluer(decor.depart_id) == (declenchante,)
    assert decor.statut(future) is StatutPhase.A_VENIR

    (franchissement,) = decor.franchissements.items
    assert future not in franchissement.phases_arretees


# ───────────────────────────── CA : la reprise, d'un seul geste ─────────────────────────────


def test_relancer_un_arret_de_depart_rend_toutes_ses_phases_d_un_seul_geste(
    decor: Decor,
) -> None:
    """CA — *« un arrêt de portée départ se relance d'un seul geste »*.

    *« Quatre boutons pour un seul arrêt créerait exactement le piège qu'on cherche à éviter — en
    oublier une. »*
    """
    premiere = decor.poser(
        ordre=1, arrets=(ArretProgramme(apres_tour=2, portee=PorteeArret.DEPART),), tour_courant=3
    )
    seconde = decor.poser(ordre=2, tour_courant=None)
    decor.service.evaluer(decor.depart_id)
    assert decor.statut(premiere) is StatutPhase.EN_PAUSE
    assert decor.statut(seconde) is StatutPhase.EN_PAUSE

    (franchissement,) = decor.franchissements.items
    assert franchissement.id is not None
    relancees = decor.service.lever(decor.depart_id, franchissement.id)

    assert set(relancees) == {premiere, seconde}
    assert decor.statut(premiere) is StatutPhase.EN_COURS
    assert decor.statut(seconde) is StatutPhase.EN_COURS


def test_relancer_ne_touche_pas_une_phase_suspendue_a_la_main(decor: Decor) -> None:
    """La reprise rend **ce que l'arrêt a coupé**, pas tout ce qui est en pause dans le créneau.

    ⚠️ C'est la raison d'être de `phases_arretees`. Déduire la liste à la reprise (« toutes les
    phases en pause de ce départ ») relancerait aussi une phase que l'organisateur avait suspendue à
    la main pour une autre raison — un effet de bord qu'aucun écran ne lui expliquerait, et qui
    remettrait des archers en piste sans que personne l'ait demandé.
    """
    declenchante = decor.poser(
        ordre=1, arrets=(ArretProgramme(apres_tour=2, portee=PorteeArret.DEPART),), tour_courant=3
    )
    a_la_main = decor.poser(ordre=2, statut=StatutPhase.EN_PAUSE, tour_courant=4)
    decor.service.evaluer(decor.depart_id)

    (franchissement,) = decor.franchissements.items
    assert franchissement.id is not None
    relancees = decor.service.lever(decor.depart_id, franchissement.id)

    assert relancees == (declenchante,)
    assert decor.statut(a_la_main) is StatutPhase.EN_PAUSE


def test_relancer_ne_remet_pas_la_phase_en_pause_aussitot(decor: Decor) -> None:
    """CA — *« après reprise, la phase repart en automatique jusqu'au prochain arrêt »*.

    ⚠️ **Le test le plus important du fichier.** L'avancement est dérivé à la lecture : une fois le
    tour 2 achevé, « le tour 2 est achevé et un arrêt est posé après le tour 2 » reste vrai pour
    toujours. Le déclencheur est rappelé à chaque validation, donc **quelques secondes après la
    reprise** — s'il n'avait pas de mémoire, la salle se rebloquerait immédiatement et
    l'organisateur perdrait la main définitivement.

    On éprouve donc la séquence réelle : couper, relancer, **rappeler le déclencheur trois fois**.
    """
    phase_id = decor.poser(
        ordre=1,
        arrets=(ArretProgramme(apres_tour=2), ArretProgramme(apres_tour=6)),
        tour_courant=3,
    )
    decor.service.evaluer(decor.depart_id)
    (franchissement,) = decor.franchissements.items
    assert franchissement.id is not None
    decor.service.lever(decor.depart_id, franchissement.id)

    for _ in range(3):
        assert decor.service.evaluer(decor.depart_id) == ()
        assert decor.statut(phase_id) is StatutPhase.EN_COURS

    # ... et le second arrêt fonctionne toujours : la phase est bien repartie en automatique.
    decor.suivi.tours[phase_id] = 7
    assert decor.service.evaluer(decor.depart_id) == (phase_id,)
    assert decor.statut(phase_id) is StatutPhase.EN_PAUSE


def test_relancer_un_arret_inconnu_est_refuse(decor: Decor) -> None:
    """Un identifiant d'arrêt qui n'existe pas est un refus explicite, pas un silence.

    Le geste vient d'un écran d'admin : un silence laisserait le bouton sans effet et l'organisateur
    devant une salle arrêtée qu'il croit avoir relancée.
    """
    decor.poser(ordre=1)

    with pytest.raises(ArretIntrouvable):
        decor.service.lever(decor.depart_id, 123456)


def test_un_arret_deja_leve_ne_se_releve_pas(decor: Decor) -> None:
    """Un double-clic ne doit pas relancer une seconde fois.

    Entre les deux clics, l'organisateur peut avoir suspendu une phase à la main : la relancer sur
    la foi d'une liste consommée serait un geste qu'il n'a pas fait.
    """
    decor.poser(ordre=1, arrets=(ArretProgramme(apres_tour=2),), tour_courant=3)
    decor.service.evaluer(decor.depart_id)
    (franchissement,) = decor.franchissements.items
    assert franchissement.id is not None
    decor.service.lever(decor.depart_id, franchissement.id)

    with pytest.raises(ArretIntrouvable):
        decor.service.lever(decor.depart_id, franchissement.id)


# ─────────────────────────── Idempotence du déclencheur ───────────────────────────


def test_le_declencheur_est_idempotent(decor: Decor) -> None:
    """Rappelé sans que rien ne change, il ne coupe rien de plus et n'écrit rien de plus.

    ⚠️ **Propriété non négociable** : le déclencheur est appelé après **chaque** validation de
    score, soit des centaines de fois dans une journée, et plusieurs tablettes peuvent valider dans
    la même seconde. Un déclencheur à effet cumulatif écrirait un franchissement par appel et
    rendrait la liste de relance du pilotage illisible.
    """
    phase_id = decor.poser(ordre=1, arrets=(ArretProgramme(apres_tour=2),), tour_courant=3)

    assert decor.service.evaluer(decor.depart_id) == (phase_id,)
    for _ in range(5):
        assert decor.service.evaluer(decor.depart_id) == ()

    assert len(decor.franchissements.items) == 1


def test_les_arrets_manques_sont_consommes_sans_couper_deux_fois(decor: Decor) -> None:
    """Cas limite tranché ici : plusieurs arrêts dus d'un coup ne produisent **qu'une** pause.

    Le domaine rend tous les arrêts dus (`arrets_atteints` compare avec `<=`, pour ne rien sauter
    silencieusement). Le service, lui, n'a qu'une pause à poser — une phase ne peut pas être en
    pause deux fois. Les autres sont donc **consommés** : ces pauses-là ont été *manquées*, pas
    annulées, et les laisser en attente les ferait se déclencher l'une après l'autre à chaque
    reprise, obligeant l'organisateur à relancer trois fois pour une seule coupe.

    ⚠️ La visibilité de ce cas — dire à l'organisateur qu'une pause a été manquée — relève
    d'`E05US034` (la tranche « personne ne reste dans le noir »). Ici on garantit seulement qu'il ne
    se retrouve pas avec trois relances à faire.
    """
    phase_id = decor.poser(
        ordre=1,
        arrets=(
            ArretProgramme(apres_tour=2),
            ArretProgramme(apres_tour=3),
            ArretProgramme(apres_tour=4),
        ),
        tour_courant=5,
    )

    assert decor.service.evaluer(decor.depart_id) == (phase_id,)
    assert len(decor.franchissements.items) == 3

    en_attente = [f for f in decor.franchissements.items if f.etat is EtatFranchissement.FRANCHI]
    assert len(en_attente) == 1, "une seule relance à faire, pas trois"

    (a_relancer,) = en_attente
    assert a_relancer.id is not None
    assert decor.service.lever(decor.depart_id, a_relancer.id) == (phase_id,)
    assert decor.statut(phase_id) is StatutPhase.EN_COURS
    assert decor.service.evaluer(decor.depart_id) == ()


def test_les_arrets_en_attente_se_lisent_pour_le_pilotage(decor: Decor) -> None:
    """Ce que le pilotage doit montrer : les arrêts franchis **et pas encore levés**, eux seuls.

    Un arrêt `ARME` n'est pas encore une relance à faire (la salle finit son tour), et un arrêt
    `LEVE` n'en est plus une.
    """
    decor.poser(ordre=1, arrets=(ArretProgramme(apres_tour=2),), tour_courant=3)
    assert decor.service.en_attente_de_relance(decor.depart_id) == ()

    decor.service.evaluer(decor.depart_id)
    (attendu,) = decor.service.en_attente_de_relance(decor.depart_id)
    assert attendu.etat is EtatFranchissement.FRANCHI

    assert attendu.id is not None
    decor.service.lever(decor.depart_id, attendu.id)
    assert decor.service.en_attente_de_relance(decor.depart_id) == ()


def test_une_phase_reprise_a_la_main_sort_du_rappel_de_relance(decor: Decor) -> None:
    """Le rappel s'éteint aussi quand l'organisateur prend l'autre bouton (revue, axe adversarial).

    ⚠️ **Le pilotage offre deux gestes côte à côte** sur une phase en pause : « Relancer » (qui lève
    le franchissement) et « Reprendre » (la transition de cycle de vie). Le second ne marquait rien
    du côté des arrêts : le franchissement restait « en attente de relance » **pour toujours**, sur
    une salle qui tire.

    Le trou datait d'`E05US033` mais restait confiné au panneau de pilotage, à côté de la phase, là
    où la contradiction se voyait. `E05US034` le **hisse au tableau de bord** avec un compteur
    croissant (« Une phase attend votre relance depuis 47 min ») : un rappel qu'on ne peut pas
    éteindre use la vigilance sur tous les autres — le filet de sécurité devenu source de fatigue
    d'alarme.

    Le critère est donc l'état **réel de la salle** : si plus rien n'est éteint, il n'y a plus de
    geste à réclamer, quel que soit le chemin par lequel la phase est repartie.
    """
    phase_id = decor.poser(ordre=1, arrets=(ArretProgramme(apres_tour=2),), tour_courant=3)
    decor.service.evaluer(decor.depart_id)
    assert len(decor.service.en_attente_de_relance(decor.depart_id)) == 1
    assert decor.statut(phase_id) is StatutPhase.EN_PAUSE

    decor.service_phases.reprendre(decor.depart_id, phase_id)

    assert decor.statut(phase_id) is StatutPhase.EN_COURS
    assert decor.service.en_attente_de_relance(decor.depart_id) == ()


def test_un_arret_de_creneau_reste_relancable_tant_qu_une_phase_est_eteinte(decor: Decor) -> None:
    """Le cas adverse du test précédent, et il porte le vrai risque (revue de 2ᵉ passe, axe B).

    ⚠️ **Le filtre est un `any`, pas un `all`, et la différence est un bouton perdu.** Un arrêt de
    portée créneau éteint plusieurs phases d'un coup ; si l'organisateur en reprend **une** à la
    main, les autres restent noires. Un critère « toutes les phases sont reparties » ferait alors
    sortir l'arrêt de la liste de relance — donc plus aucun bouton pour rallumer ce qui est encore
    éteint, sur une salle à moitié arrêtée. C'est le mode de panne que `en_attente_de_relance`
    existe pour empêcher, et que le correctif de la 1ʳᵉ passe pouvait rouvrir en le refermant.
    """
    premiere = decor.poser(
        ordre=1, arrets=(ArretProgramme(apres_tour=2, portee=PorteeArret.DEPART),)
    )
    seconde = decor.poser(ordre=2)
    decor.suivi.tours[premiere] = 3
    decor.suivi.tours[seconde] = 3
    decor.service.evaluer(decor.depart_id)
    decor.suivi.tours[seconde] = 4
    decor.service.evaluer(decor.depart_id)
    assert decor.statut(premiere) is StatutPhase.EN_PAUSE
    assert decor.statut(seconde) is StatutPhase.EN_PAUSE

    decor.service_phases.reprendre(decor.depart_id, premiere)

    # Une phase repartie, l'autre toujours éteinte : le bouton doit rester.
    (encore,) = decor.service.en_attente_de_relance(decor.depart_id)
    assert encore.id is not None
    decor.service.lever(decor.depart_id, encore.id)
    assert decor.statut(seconde) is StatutPhase.EN_COURS


def test_le_rappel_ne_compte_que_les_phases_encore_eteintes(decor: Decor) -> None:
    """Le **chiffre** suit l'état de la salle, pas l'historique (2ᵉ passe, axe adversarial).

    ⚠️ **Le premier correctif avait déplacé le trou plutôt que de le fermer.** Filtrer sur « une
    phase est encore en pause » éteignait bien le rappel quand tout était reparti, mais laissait
    `phases_arretees` — la trace **historique**, jamais élaguée — servir de compteur. Sur un arrêt
    de créneau qui a éteint deux phases dont une a été reprise à la main, le tableau de bord
    annonçait donc « **2 phases** attendent votre relance » quand une seule était noire, et le clic
    n'en repartait qu'une : l'écran promettait deux, le serveur en rendait une.

    Un chiffre faux dans le sens qui **alarme** est celui qui use la vigilance le plus vite — c'est
    ce que `resumeDeRelance` s'interdit dans sa propre docstring, et le compteur qui l'alimente
    vient d'ici.
    """
    premiere = decor.poser(
        ordre=1, arrets=(ArretProgramme(apres_tour=2, portee=PorteeArret.DEPART),)
    )
    seconde = decor.poser(ordre=2)
    decor.suivi.tours[premiere] = 3
    decor.suivi.tours[seconde] = 3
    decor.service.evaluer(decor.depart_id)
    decor.suivi.tours[seconde] = 4
    decor.service.evaluer(decor.depart_id)
    (avant,) = decor.service.en_attente_de_relance(decor.depart_id)
    assert len(avant.phases_arretees) == 2

    decor.service_phases.reprendre(decor.depart_id, premiere)

    (apres,) = decor.service.en_attente_de_relance(decor.depart_id)
    assert apres.phases_arretees == (seconde,)
    # Et la relance rend bien ce que l'écran a annoncé — ni plus, ni moins.
    assert apres.id is not None
    assert decor.service.lever(decor.depart_id, apres.id) == (seconde,)


def test_relancer_apres_une_reprise_manuelle_consomme_l_arret_sans_404(decor: Decor) -> None:
    """Un bouton vu il y a dix secondes ne doit pas répondre « introuvable » (revue, axe D).

    ⚠️ `lever` prenait sa source dans `en_attente_de_relance`, donc héritait de son filtre : un
    arrêt dont la **dernière** phase venait d'être reprise à la main devenait introuvable, et
    l'organisateur recevait un 404 sur un bouton encore affiché (le poll est à 10 s). Or les quatre
    cas que la docstring de `lever` énumère sont les seuls qui méritent un 404. Il n'y a plus rien
    à relancer — ce n'est pas la même chose qu'un identifiant inconnu : l'arrêt est **consommé**,
    la relance est vide, et le rappel disparaît comme il le devait.
    """
    phase_id = decor.poser(ordre=1, arrets=(ArretProgramme(apres_tour=2),), tour_courant=3)
    decor.service.evaluer(decor.depart_id)
    (arret,) = decor.service.en_attente_de_relance(decor.depart_id)
    assert arret.id is not None
    decor.service_phases.reprendre(decor.depart_id, phase_id)

    assert decor.service.lever(decor.depart_id, arret.id) == ()
    assert decor.service.en_attente_de_relance(decor.depart_id) == ()


# ───────────── Ce que la revue a trouvé, et qu'aucun test n'attrapait ───────────── Cette section
# est née des quatre axes de `/revue-us`. Chacun de ces tests correspond à un défaut **reproduit**
# sur le code livré, et chacun était invisible parce que la doublure d'avancement ne produisait
# jamais la valeur qui casse. C'est la leçon à retenir plus que les correctifs : une doublure qui ne
# sait pas exprimer le cas limite le rend intestable.


def test_un_avancement_inconnu_ne_declenche_aucun_arret(decor: Decor) -> None:
    """**Bloquant.** `tour_courant=None` + `nb_tours=1` veut dire « je ne sais pas », pas « fini ».

    ⚠️ C'est le défaut central de la première livraison. `None` a **cinq** provenances et une seule
    signifie « tout est joué » : aucun lecteur branché pour ce type, service de format qui refuse,
    rien encore composé, phase sans braquet… Le déclencheur les lisait toutes comme « le dernier
    tour est achevé » et **coupait la salle au premier score validé du créneau**, avant que personne
    ait tiré.

    La signature `nb_tours=1, tour_courant=None` est exactement le repli d'`avancement_bloc`, que sa
    propre docstring appelle « dégradation lisible ».
    """
    phase_id = decor.poser(ordre=1, arrets=(ArretProgramme(apres_tour=2),), tour_courant=None)
    decor.suivi.nb_tours[phase_id] = 1

    assert decor.service.evaluer(decor.depart_id) == ()
    assert decor.statut(phase_id) is StatutPhase.EN_COURS
    assert decor.franchissements.items == []


def test_un_arret_de_depart_ne_coupe_pas_une_phase_dont_le_tour_est_inconnu(decor: Decor) -> None:
    """**Bloquant.** Le CA du 18/08/2026 : *« personne n'est coupé en plein tir »*.

    ⚠️ **Deux correctifs successifs ont été nécessaires ici, et le premier était faux.** Il excluait
    de la photo les phases *absentes* du dictionnaire d'avancement — or le suivi rend une entrée
    pour **chaque** phase du créneau, donc ce signal ne discriminait rien et le défaut était intact.
    L'axe adversarial l'a démontré contre l'arbre de travail. Le seul signal qui marche est
    `tour_courant is not None` : « un tour tourne, on peut le laisser finir ».

    Sans lui, une qualification en train de tirer était notée « n'avait plus rien en cours » et
    coupée **dans la seconde** par un arrêt de créneau.
    """
    declenchante = decor.poser(
        ordre=1, arrets=(ArretProgramme(apres_tour=2, portee=PorteeArret.DEPART),), tour_courant=3
    )
    tour_inconnu = decor.poser(ordre=2, tour_courant=None)
    decor.suivi.nb_tours[tour_inconnu] = 1

    arretees = decor.service.evaluer(decor.depart_id)

    assert arretees == (declenchante,)
    assert decor.statut(tour_inconnu) is StatutPhase.EN_COURS


def test_deux_arrets_dus_au_meme_appel_ne_font_pas_echouer_le_declencheur(decor: Decor) -> None:
    """**Bloquant.** Le cliché des phases était périmé entre les deux passes.

    ⚠️ Séquence exacte : la passe 1 met la phase 2 en pause (arrêt de créneau de la phase 1) ; la
    passe 2 relit son statut **dans le cliché**, y voit encore `EN_COURS`, et rappelle
    `mettre_en_pause` sur une phase déjà en pause — `TransitionStatutInvalide`.

    Ce que ça coûtait est pire que l'exception : elle était **avalée** par le `except Exception` du
    signalement et **abandonnait la boucle**, si bien que l'arrêt de la phase 2 n'était jamais tracé
    et se redéclenchait après la relance. C'est-à-dire « l'organisateur perd la main », que tout
    l'ADR est construit pour empêcher. Le CA autorise « un arrêt à chaque tour » : la collision
    n'est pas exotique.
    """
    premiere = decor.poser(
        ordre=1, arrets=(ArretProgramme(apres_tour=2, portee=PorteeArret.DEPART),), tour_courant=3
    )
    seconde = decor.poser(ordre=2, arrets=(ArretProgramme(apres_tour=4),), tour_courant=5)

    arretees = decor.service.evaluer(decor.depart_id)

    assert set(arretees) == {premiere, seconde}
    assert decor.statut(seconde) is StatutPhase.EN_PAUSE
    # Et surtout : l'arrêt propre de la seconde est **tracé**, donc il ne se redéclenchera pas.
    traites = {(f.phase_id, f.apres_tour) for f in decor.franchissements.items}
    assert (seconde, 4) in traites


def test_deux_arrets_de_depart_armes_ensemble_aboutissent_tous_les_deux(decor: Decor) -> None:
    """**Majeur.** Deux arrêts de créneau s'attendaient mutuellement, sans fin.

    Chacun attendait que l'autre phase finisse un tour — or celle-ci venait d'être mise en pause par
    l'autre arrêt, donc son tour ne bougerait plus jamais. Les deux restaient `ARME`, donc **absents
    de la liste de relance**, donc la salle était arrêtée sans aucun bouton pour la repartir.

    Le correctif : une phase qui n'est plus `EN_COURS` compte comme « a fini son tour » — elle est
    arrêtée, c'est bien le résultat voulu.
    """
    premiere = decor.poser(
        ordre=1, arrets=(ArretProgramme(apres_tour=2, portee=PorteeArret.DEPART),), tour_courant=3
    )
    seconde = decor.poser(
        ordre=2, arrets=(ArretProgramme(apres_tour=4, portee=PorteeArret.DEPART),), tour_courant=5
    )

    decor.service.evaluer(decor.depart_id)

    assert decor.statut(premiere) is StatutPhase.EN_PAUSE
    assert decor.statut(seconde) is StatutPhase.EN_PAUSE
    etats = [f.etat for f in decor.franchissements.items]
    assert EtatFranchissement.ARME not in etats, "un arrêt armé n'est pas relançable"
    assert len(decor.service.en_attente_de_relance(decor.depart_id)) == 2


def test_une_phase_suspendue_a_la_main_apres_l_armement_ne_bloque_pas_l_arret(decor: Decor) -> None:
    """**Majeur.** Même interblocage, par une autre porte : la pause manuelle.

    L'exclusion des phases déjà en pause **au moment de l'armement** avait été corrigée ; celle
    d'une phase suspendue **après** ne l'était pas. Son tour se figeait, l'arrêt restait `ARME` pour
    toujours, et l'organisateur perdait la main sur tout le créneau à cause d'un geste qu'il avait
    fait lui-même.
    """
    declenchante = decor.poser(
        ordre=1, arrets=(ArretProgramme(apres_tour=2, portee=PorteeArret.DEPART),), tour_courant=3
    )
    voisine = decor.poser(ordre=2, tour_courant=5)
    decor.service.evaluer(decor.depart_id)
    assert [f.etat for f in decor.franchissements.items] == [EtatFranchissement.ARME]

    # L'organisateur suspend la voisine à la main, pour une raison à lui.
    decor.service_phases.mettre_en_pause(decor.depart_id, voisine)
    decor.service.evaluer(decor.depart_id)

    (franchissement,) = decor.franchissements.items
    assert franchissement.etat is EtatFranchissement.FRANCHI
    assert declenchante in franchissement.phases_arretees


def test_sans_aucun_arret_le_declencheur_ne_lit_meme_pas_l_avancement(decor: Decor) -> None:
    """**Majeur.** La promesse « rien ne change sans pause » portait aussi sur le **coût**.

    ⚠️ `evaluer` est appelé **depuis la file d'écriture**, donc sur le thread du writer unique qui
    sérialise toutes les écritures de l'application (règle 7). Payer la recomposition intégrale du
    créneau après chaque validation, sur un tournoi qui n'a programmé **aucune** pause, retardait
    toutes les tablettes pour rien.

    L'oracle est la doublure : si elle n'est pas appelée, la lecture lourde n'a pas eu lieu.
    """
    decor.poser(ordre=1, arrets=(), tour_courant=3)
    decor.poser(ordre=2, arrets=(), tour_courant=1)

    assert decor.service.evaluer(decor.depart_id) == ()
    assert decor.suivi.appels == 0, "aucun arrêt nulle part : rien ne justifie de lire l'avancement"


def test_un_arret_au_dela_du_dernier_tour_joue_ne_coupe_pas_une_phase_finie(decor: Decor) -> None:
    """Cas limite : un suisse réglé à 9 rondes qui n'en apparie que 5.

    L'arrêt « après le tour 7 » ne doit pas se déclencher **à la fin** de la phase : il mettrait en
    pause une phase dont tout est tiré, qu'il faudrait relancer pour pouvoir la clôturer. Le tour
    achevé est borné par le nombre de tours **réellement joué**.
    """
    phase_id = decor.poser(ordre=1, arrets=(ArretProgramme(apres_tour=7),), tour_courant=None)
    decor.suivi.nb_tours[phase_id] = 5

    assert decor.service.evaluer(decor.depart_id) == ()
    assert decor.statut(phase_id) is StatutPhase.EN_COURS


# ══════════ E05US034 — poser un arrêt le jour J, et voir qu'on attend ══════════
#
# Tests écrits **depuis le CA** d'`E05US034`, avant l'implémentation (règle 9). Deux CA sont en jeu
# ici — les trois autres sont du front :
#
# - *« le jour J, l'organisateur pose un arrêt relatif depuis le pilotage : bloquer dans x tours. Il
#   s'ajoute aux arrêts programmés, il ne les remplace pas »* ;
# - *« l'application rappelle qu'une phase attend sa relance »* — la pastille « depuis 14 min »,
#   donc un instant à lire, donc un horodatage à écrire.
#
# ⚠️ **L'oracle du cloisonnement par créneau ne vient pas du code mais d'ADR-0076 §5.** Le code
# d'`E05US033` ne connaît que des arrêts de tournoi ; en dériver un test aurait conclu qu'un arrêt
# est forcément rejoué par tous les créneaux — exactement la propriété que ce CA refuse.


def _decor_a_deux_creneaux() -> tuple[Decor, int]:
    """Le décor ordinaire, plus un **second créneau** dans le même tournoi.

    Nécessaire parce que la propriété centrale de l'arrêt de circonstance — *il n'est rejoué par
    personne* — ne s'observe pas sur un créneau unique. Rendre l'identifiant du second départ plutôt
    que de l'exposer sur `Decor` : un seul test s'en sert, et le décor commun n'a pas à porter le
    coût d'un créneau que personne d'autre ne regarde.
    """
    decor = Decor()
    autre = decor.departs.ajouter(
        Depart.creer(tournoi_id=decor.tournoi_id, numero=2, tarif_centimes=800, horaire="14:00")
    )
    assert autre.id is not None
    return decor, autre.id


# ─────────── CA : « bloquer dans x tours », posé depuis le pilotage ───────────


def test_poser_un_arret_relatif_le_traduit_en_arret_apres_le_tour_courant(decor: Decor) -> None:
    """CA — *« bloquer dans x tours »* : « dans 1 tour » coupe à la fin du tour qui tourne.

    Le service ne fait pas l'arithmétique lui-même — c'est `tour_d_un_arret_relatif`, au domaine —
    mais c'est lui qui va **chercher** le tour courant dans le suivi. Le test tient cette couture :
    poser depuis le pilotage, c'est poser *par rapport à ce que l'écran montre*.
    """
    phase_id = decor.poser(ordre=1, tour_courant=3)

    arret = decor.service.poser_arret_relatif(decor.depart_id, phase_id, dans_x_tours=1)

    assert arret.apres_tour == 3
    assert arret.depart_id == decor.depart_id
    assert arret.portee is PorteeArret.PHASE


def test_un_arret_relatif_peut_couper_tout_le_creneau(decor: Decor) -> None:
    """La portée est un **choix** au moment de poser, comme à l'atelier (ADR-0091).

    Le cas d'usage du jour J est même plus souvent celui-là que l'autre : on arrête *la salle* pour
    une annonce, pas une phase en particulier.
    """
    phase_id = decor.poser(ordre=1, tour_courant=2)

    arret = decor.service.poser_arret_relatif(
        decor.depart_id, phase_id, dans_x_tours=1, portee=PorteeArret.DEPART
    )

    assert arret.portee is PorteeArret.DEPART


def test_un_arret_relatif_coupe_la_phase_quand_son_tour_s_acheve(decor: Decor) -> None:
    """CA — l'arrêt posé le jour J **coupe vraiment** : c'est le même déclencheur, pas un doublon.

    Le test est écrit en deux temps délibérément — évaluer *avant* que le tour ait avancé, puis
    après. Sans le premier temps, un service qui couperait dès la pose passerait au vert alors qu'il
    interromprait la salle en plein tir.
    """
    phase_id = decor.poser(ordre=1, tour_courant=3)
    decor.service.poser_arret_relatif(decor.depart_id, phase_id, dans_x_tours=1)

    decor.service.evaluer(decor.depart_id)
    assert decor.statut(phase_id) is StatutPhase.EN_COURS

    decor.suivi.tours[phase_id] = 4
    decor.service.evaluer(decor.depart_id)

    assert decor.statut(phase_id) is StatutPhase.EN_PAUSE


def test_un_arret_relatif_s_ajoute_aux_arrets_programmes(decor: Decor) -> None:
    """CA — *« il s'ajoute aux arrêts programmés, il ne les remplace pas »*.

    L'étape porte une pause repas après le tour 2 ; l'organisateur en ajoute une après le tour 4. Le
    créneau doit s'arrêter **deux fois**, et le test le vérifie en relançant entre les deux — sans
    quoi la seconde coupe serait indiscernable d'une première qui n'a jamais été levée.
    """
    phase_id = decor.poser(ordre=1, tour_courant=2, arrets=(ArretProgramme(apres_tour=2),))
    decor.service.poser_arret_relatif(decor.depart_id, phase_id, dans_x_tours=3)

    decor.suivi.tours[phase_id] = 3
    decor.service.evaluer(decor.depart_id)
    assert decor.statut(phase_id) is StatutPhase.EN_PAUSE

    en_attente = decor.service.en_attente_de_relance(decor.depart_id)
    assert len(en_attente) == 1
    assert en_attente[0].id is not None
    decor.service.lever(decor.depart_id, en_attente[0].id)
    assert decor.statut(phase_id) is StatutPhase.EN_COURS

    decor.suivi.tours[phase_id] = 5
    decor.service.evaluer(decor.depart_id)

    assert decor.statut(phase_id) is StatutPhase.EN_PAUSE


def test_un_arret_relatif_n_est_rejoue_par_aucun_autre_creneau() -> None:
    """**Le CA qui justifie le concept** (ADR-0092) : la panne du matin n'arrête pas l'après-midi.

    C'est la différence entre poser un arrêt et *éditer le déroulé*. Un `ArretProgramme` ajouté à
    l'`EtapeDeroule` serait rejoué par tous les créneaux (ADR-0076 §4) — donc le créneau de
    l'après-midi s'arrêterait au même tour, pour une raison qui n'existe plus.
    """
    decor, autre_depart = _decor_a_deux_creneaux()
    phase_id = decor.poser(ordre=1, tour_courant=3)
    # Le second créneau rejoue **la même étape** (ADR-0076 §4) : c'est ce partage qui rend la
    # propriété non triviale — si l'arrêt vivait dans le déroulé, cette phase-ci s'arrêterait aussi.
    autre_phase = decor.poser(ordre=1, tour_courant=3, depart_id=autre_depart)

    decor.service.poser_arret_relatif(decor.depart_id, phase_id, dans_x_tours=1)

    # ⚠️ **L'oracle porte sur le mécanisme, pas sur la doublure** (correctif de revue, axe B). La
    # première rédaction assertait sur `FauxArretsDeCirconstance.par_depart`, dont le filtre par
    # créneau est écrit trois cents lignes plus haut : elle vérifiait le décor, pas le service. On
    # fait donc **avancer le second créneau au-delà du tour visé** et on constate qu'il ne s'arrête
    # pas — la seule formulation qui rougirait si l'arrêt était rejoué.
    decor.suivi.tours[autre_phase] = 5
    assert decor.service.evaluer(autre_depart) == ()
    assert decor.statut(autre_phase) is StatutPhase.EN_COURS

    # Et le créneau du matin, lui, coupe bien : sans cette moitié, un service qui n'arrête *jamais*
    # rien passerait le test.
    decor.suivi.tours[phase_id] = 4
    assert decor.service.evaluer(decor.depart_id) == (phase_id,)


# ─────────── Ce que la pose refuse, et pourquoi elle le dit ───────────


def test_poser_un_arret_relatif_est_refuse_sur_un_type_qui_ne_lit_pas_son_tour(
    decor: Decor,
) -> None:
    """Même refus qu'à l'atelier, et c'est **une seule règle** appliquée à deux portes d'entrée.

    `E05US033` a livré la table des types dont l'application lit le tour. Une seconde porte qui ne
    la consulterait pas laisserait poser, depuis le pilotage, un arrêt qui ne partirait jamais —
    précisément le réglage inerte que l'atelier refuse d'enregistrer.

    ⚠️ **Le cas de garde était la qualification jusqu'à E05US035**, qui l'a rendue arrêtable
    (ADR-0093). L'échauffement prend sa place : il n'a ni barème ni feuille de marque, donc aucune
    donnée existante ne dit où il en est.
    """
    phase_id = decor.poser(ordre=1, type_phase=TypePhase.ECHAUFFEMENT, tour_courant=1)

    with pytest.raises(ArretProgrammeInvalide):
        decor.service.poser_arret_relatif(decor.depart_id, phase_id, dans_x_tours=1)


def test_poser_un_arret_relatif_est_refuse_quand_le_tour_courant_est_inconnu(decor: Decor) -> None:
    """Sans origine, « dans x tours » ne se compte pas — et deviner couperait au mauvais endroit.

    Le refus remonte du domaine (`tour_d_un_arret_relatif`) ; ce qu'on tient ici est que le service
    **lit** bien le suivi au lieu de se rabattre sur une valeur par défaut.
    """
    phase_id = decor.poser(ordre=1, tour_courant=None)

    with pytest.raises(ArretProgrammeInvalide):
        decor.service.poser_arret_relatif(decor.depart_id, phase_id, dans_x_tours=2)


def test_poser_un_arret_relatif_sur_un_tour_deja_pris_est_refuse(decor: Decor) -> None:
    """Deux arrêts au même endroit ne coupent qu'une fois : le dire au lieu de l'absorber.

    ⚠️ **C'est la moitié stricte de l'asymétrie** décrite par `arrets_applicables` : le déclencheur
    fusionne (il n'a personne à qui parler), la pose refuse (l'organisateur est devant l'écran).
    Absorber ici laisserait croire qu'une seconde pause a été programmée.
    """
    phase_id = decor.poser(ordre=1, tour_courant=1, arrets=(ArretProgramme(apres_tour=3),))

    with pytest.raises(ArretProgrammeInvalide):
        decor.service.poser_arret_relatif(decor.depart_id, phase_id, dans_x_tours=3)


def test_poser_deux_fois_le_meme_arret_relatif_est_refuse(decor: Decor) -> None:
    """Le double-clic est un geste du jour J, pas un cas limite de laboratoire.

    Sans ce refus, deux lignes identiques cohabiteraient et la seconde deviendrait une pause
    fantôme : consommée « manquée » au premier franchissement, journalisée en avertissement, pour
    un geste que l'organisateur croyait unique.
    """
    phase_id = decor.poser(ordre=1, tour_courant=2)
    decor.service.poser_arret_relatif(decor.depart_id, phase_id, dans_x_tours=2)

    with pytest.raises(ArretProgrammeInvalide):
        decor.service.poser_arret_relatif(decor.depart_id, phase_id, dans_x_tours=2)


def test_poser_un_arret_relatif_au_dela_de_la_phase_est_refuse(decor: Decor) -> None:
    """Le quatrième refus documenté, qui n'avait **aucun** oracle (correctif de revue, axe B).

    Demander « dans 9 tours » sur une phase qui n'en compte que 5, c'est programmer une coupe pour
    un moment où la salle sera éteinte. Le refus existait, la fiche de recette le promettait, et
    rien ne le vérifiait : la doublure repliait `nb_tours` sur 9, donc la borne était inatteignable.
    Si l'implémentation avait passé `nb_tours=None`, toute la suite serait restée verte.
    """
    phase_id = decor.poser(ordre=1, tour_courant=2, nb_tours=5)

    with pytest.raises(ArretProgrammeInvalide):
        decor.service.poser_arret_relatif(decor.depart_id, phase_id, dans_x_tours=9)


def test_un_arret_d_atelier_hors_de_portee_n_interdit_pas_de_poser_une_pause(
    decor: Decor,
) -> None:
    """Le geste du jour J ne meurt pas sur un réglage de la veille (correctif de bloquant, 3 axes).

    ⚠️ **Le cas est banal, pas tordu.** Un suisse réglé à 7 rondes n'en joue que 5 si l'effectif ne
    le permet pas — `verifier_arrets` le dit mot pour mot pour justifier son `nb_tours=None` à la
    composition. L'arrêt d'atelier après le tour 6 est donc **légitime et inerte**, et l'atelier ne
    pouvait pas le savoir.

    La première rédaction validait l'**union** (arrêts d'étape + circonstance + voulu) avec le
    `nb_tours` du jour : elle refusait alors **toute** pose sur cette phase, pour toute la journée,
    en nommant un tour que l'organisateur n'a pas demandé et qu'il ne peut pas retirer depuis le
    pilotage — l'éditer irait dans le déroulé du **tournoi**, donc dans tous les créneaux, ce
    qu'ADR-0092 interdit précisément. Un cul-de-sac (`P-3`) sur le CA central de l'US.

    L'inertie se juge donc sur le **seul arrêt demandé** ; la collision, elle, reste jugée sur
    l'union — c'est l'objet du test précédent.
    """
    phase_id = decor.poser(
        ordre=1, tour_courant=2, nb_tours=5, arrets=(ArretProgramme(apres_tour=6),)
    )

    pose = decor.service.poser_arret_relatif(decor.depart_id, phase_id, dans_x_tours=1)

    assert pose.apres_tour == 2


# ─────────── CA : « l'application rappelle qu'une phase attend sa relance » ───────────


def test_un_arret_qui_a_coupe_porte_l_instant_de_la_coupe(decor: Decor) -> None:
    """CA — la pastille annonce « depuis 14 min » : il faut donc un instant, et il faut l'écrire.

    Seul état **daté** du mécanisme, et il ne se dérive de rien : ni le statut de phase ni le
    franchissement ne portent d'heure, et l'avancement est recalculé à chaque lecture (ADR-0090 §5).
    L'horloge passe par le port `Horloge` (règle 2) — un `datetime.now()` dans le service rendrait
    ce test non déterministe (règle 9).
    """
    phase_id = decor.poser(ordre=1, tour_courant=2, arrets=(ArretProgramme(apres_tour=2),))
    decor.suivi.tours[phase_id] = 3

    decor.service.evaluer(decor.depart_id)

    (arret,) = decor.service.en_attente_de_relance(decor.depart_id)
    assert arret.arrete_depuis == decor.horloge.instant


def test_l_instant_de_coupe_est_celui_de_la_premiere_phase_eteinte(decor: Decor) -> None:
    """Un arrêt de créneau s'éteint en plusieurs minutes : la pastille compte la **première**.

    ⚠️ **C'est ce que le CA demande, et c'est le contraire du réflexe d'implémentation** — mettre à
    jour l'horodatage à chaque phase coupée serait plus simple et ferait mentir la pastille dans le
    sens dangereux : elle rajeunirait à chaque nouvelle extinction, donc annoncerait « depuis
    1 min » sur une salle éteinte depuis vingt.
    """
    premiere = decor.poser(
        ordre=1,
        tour_courant=2,
        arrets=(ArretProgramme(apres_tour=2, portee=PorteeArret.DEPART),),
    )
    tardive = decor.poser(ordre=2, tour_courant=5)

    decor.suivi.tours[premiere] = 3
    decor.service.evaluer(decor.depart_id)
    coupe = decor.horloge.instant

    decor.horloge.avancer(datetime.timedelta(minutes=12))
    decor.suivi.tours[tardive] = 6
    decor.service.evaluer(decor.depart_id)

    (arret,) = decor.service.en_attente_de_relance(decor.depart_id)
    assert arret.arrete_depuis == coupe


def test_un_arret_manque_n_est_pas_date_puisqu_il_n_a_rien_eteint(decor: Decor) -> None:
    """Pas de coupe, pas d'horloge : la pastille ne décompte pas une attente qui n'existe pas.

    Une phase dont **tout est tiré** consomme son arrêt sans se mettre en pause (`E05US033`) : la
    trace est écrite `LEVE`, sans phase arrêtée. La dater ferait apparaître un instant sur un fait
    qui n'a jamais eu lieu — et l'horodatage est précisément ce que la pastille lit.

    ⚠️ Le test vise l'invariant « seule une coupe réelle est datée » plutôt que l'écran : il tient
    aussi pour les traces qui ne remontent pas au pilotage aujourd'hui, et c'est ce qui le rend
    utile le jour où une autre lecture s'y branchera.
    """
    decor.poser(ordre=1, tour_courant=None, arrets=(ArretProgramme(apres_tour=2),))

    decor.service.evaluer(decor.depart_id)

    assert decor.franchissements.items != []
    for franchissement in decor.franchissements.items:
        assert franchissement.phases_arretees == ()
        assert franchissement.arrete_depuis is None
