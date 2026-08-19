"""Service **Arrêts programmés** — le déclencheur, le gel, la reprise (E05US033, [ADR-0091]).

Tests écrits **depuis le CA** (règle 9), avant l'implémentation. Le domaine
(`test_domain_arret_programme.py`) décide *quand* un arrêt est dû ; ce fichier-ci décide *quelle
phase passe en pause* et *ce qu'un geste d'admin rend*. Le troisième volet — **ce que la pause
interdit** — est dans `test_service_saisie.py` (section E05US033), là où le montage de saisie existe
déjà : il n'y avait pas de raison d'en remonter un second ici.

⚠️ **L'oracle du gel n'est pas le code existant, et c'est le point à comprendre avant de lire.** Au
cadrage du 19/08/2026, la vérification a montré que `StatutPhase.EN_PAUSE` **ne gelait rien** :
aucune garde dans `application/saisie.py`, aucune dans `application/saisie_duels.py`, et
`application/routage.py` traitait une phase en pause comme une phase en cours (filtre
`statut is not TERMINEE`). La pause était **cosmétique** — un libellé dans le suivi. Un test écrit
en lisant ce code aurait donc consacré une pause qui n'arrête personne, et l'US aurait livré une
étiquette. La fiche l'annonçait à l'envers (« `EN_PAUSE` gèle la validation » y figurait comme un
piège **à vérifier**) : c'est le cas d'école de la règle 9 — le CA, pas le code.

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
    ArretProgramme,
    EtatFranchissement,
    FranchissementArret,
    PorteeArret,
)
from domain.depart import Depart
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
        self.appels = 0

    def avancement_par_phase(self, depart_id: int) -> dict[PhaseId, AvancementDePhase]:
        self.appels += 1
        return {
            phase_id: AvancementDePhase(nb_tours=9, tour_courant=tour)
            for phase_id, tour in self.tours.items()
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
        self.suivi = FauxSuivi()
        self.service_phases = ServicePhases(self.tournois, self.phases, self.departs, self.deroules)
        self.service = ServiceArretsProgrammes(
            phases=self.phases,
            deroules=self.deroules,
            departs=self.departs,
            franchissements=self.franchissements,
            suivi=self.suivi,
            cycle_de_vie=self.service_phases,
        )

    def poser(
        self,
        ordre: int,
        type_phase: TypePhase = TypePhase.SUISSE,
        statut: StatutPhase = StatutPhase.EN_COURS,
        arrets: tuple[ArretProgramme, ...] = (),
        tour_courant: int | None = 1,
    ) -> PhaseId:
        """Pose une phase démarrée, son étape, ses arrêts, et son tour courant dans le suivi."""
        reglage = ConfigurationSuisse(nb_rondes=9) if type_phase is TypePhase.SUISSE else None
        phase = poser_phase_factice(
            self.departs,
            self.deroules,
            self.phases,
            dataclasses.replace(
                Phase(
                    depart_id=self.depart_id,
                    ordre=ordre,
                    type=type_phase,
                    suisse=reglage,
                ),
                statut=statut,
            ),
        )
        assert phase.id is not None
        if arrets:
            etape = next(e for e in self.deroules.par_tournoi(self.tournoi_id) if e.ordre == ordre)
            self.deroules.enregistrer(dataclasses.replace(etape, arrets=arrets))
        self.suivi.tours[phase.id] = tour_courant
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


def test_une_phase_dont_tout_est_joue_franchit_son_dernier_arret(decor: Decor) -> None:
    """Cas limite : `tour_courant is None` signifie *« plus rien ne tourne »* (ADR-0090).

    Le tour achevé est alors le **dernier**, et un arrêt posé avant lui est dû. Sans cette lecture,
    un arrêt après l'avant-dernier tour ne se déclencherait jamais si la phase finit d'un bloc.
    """
    phase_id = decor.poser(ordre=1, arrets=(ArretProgramme(apres_tour=8),), tour_courant=None)

    assert decor.service.evaluer(decor.depart_id) == (phase_id,)
    assert decor.statut(phase_id) is StatutPhase.EN_PAUSE


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
    couperait net serait plus simple à écrire — et il interromprait un duel engagé, quelqu'un
    l'arc levé. La salle s'éteint en quelques minutes, pas d'un coup.

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

    ⚠️ **Propriété non négociable** : le déclencheur est appelé après **chaque** validation de score,
    soit des centaines de fois dans une journée, et plusieurs tablettes peuvent valider dans la même
    seconde. Un déclencheur à effet cumulatif écrirait un franchissement par appel et rendrait la
    liste de relance du pilotage illisible.
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
