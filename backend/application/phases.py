"""Service applicatif Phases — compose et fait vivre la séquence de phases d'un tournoi (E05US001).

Use cases : lister, ajouter, éditer (type/source/effectif), réordonner, supprimer, et faire
avancer le **cycle de vie** de chaque phase (`a_venir → en_cours ⇄ en_pause → terminee`).

Répartition des responsabilités (ADR-0045, ADR-0007) :

- **La cohérence de la séquence** (ordres contigus, sources bien formées : source vide / rangs
  inexistants / effectif incompatible) est une **règle du domaine** : le service assemble les phases
  en `SequencePhases`, dont la **construction** rejette une séquence incohérente (→ `DomainError`,
  traduite en 422). Le service n'en réimplémente rien.
- **Les conflits d'état** (transition de statut illégale, suppression d'une phase qui en alimente
  une autre, existence d'une phase dans *ce* tournoi) sont arbitrés **ici** (`ApplicationError`,
  409/404), comme `ServiceTournois` pour le cycle de vie du tournoi.

Le service ignore HTTP, SQL et la file d'écriture (sérialisation assurée en amont, côté API) : il
reste synchrone et pur d'infrastructure.

**Le peuplement admet plusieurs sources** depuis E05US010 (ADR-0061) : une phase se compose de
prélèvements de natures mêlées (rangs, issue de tour, « le reste »), éventuellement relatifs à
l'effectif réel. DETTE-015 est résorbée.
Le réordonnancement et la suppression **remappent** les références de source (portées par l'`ordre`
de la phase source) pour qu'elles suivent la phase qu'elles désignaient. Cet **ancrage par `ordre`**
— plutôt que par identité — survit à E05US010, qui l'a seulement généralisé à N sources : c'est
`# DETTE-026`, la seule facette de DETTE-015 qui n'ait pas été résorbée.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from application.erreurs import (
    DepartIntrouvable,
    PhaseIntrouvable,
    PhaseQualificationNonSupprimable,
    PhaseSourceReferencee,
    ReordonnancementPhasesInvalide,
    TournoiIntrouvable,
    TransitionStatutInvalide,
)
from application.portee import phase_du_depart
from domain.bareme import BaremeQualification
from domain.big_shoot_off import ConfigurationBigShootOff
from domain.depart import DepartId
from domain.deroule_etape import EtapeDeroule, EtapeDerouleId
from domain.phase import (
    Phase,
    PhaseId,
    SourcePhase,
    StatutPhase,
    TypePhase,
    grain_par_defaut,
    verifier_sequence,
)
from domain.politiques import ProfondeurClassement
from domain.ports import (
    DepartRepository,
    DerouleRepository,
    PhaseRepository,
    TournoiRepository,
)
from domain.poule import ReglageDePoules
from domain.tournoi import TournoiId


class ServicePhases:
    """Cas d'usage de la séquence de phases : composer, éditer, ordonner, cycle de vie."""

    def __init__(
        self,
        tournois: TournoiRepository,
        phases: PhaseRepository,
        departs: DepartRepository,
        deroules: DerouleRepository,
    ) -> None:
        self._tournois = tournois
        self._phases = phases
        # ⚠️ **Ce service compose une séquence, donc il travaille dans un départ** (E01US025,
        # ADR-0075). Il lisait `par_tournoi`, qui rend désormais la **concaténation** des séquences
        # de tous les créneaux : la passer à `SequencePhases` lèverait `SequenceOrdreInvalide`,
        # puisque les ordres y repartent de 1 à chaque départ. Le magasin de créneaux sert à
        # valider l'existence de celui qu'on compose.
        self._departs = departs
        # Le **déroulé** : la définition, une fois par tournoi (ADR-0076). Ce service porte
        # donc deux mailles, délibérément — composer au tournoi, faire vivre au départ.
        self._deroules = deroules

    # --- Lecture -------------------------------------------------------------------------------

    def lister(self, tournoi_id: TournoiId) -> list[EtapeDeroule]:
        """Renvoie le **déroulé** du tournoi, ordonné (liste éventuellement vide).

        **Au tournoi et non au départ** (ADR-0076) : le déroulé se définit une fois, et chaque
        créneau le rejoue. Pour savoir *où en est* un créneau, c'est `PhaseRepository.par_depart`
        qu'il faut lire — deux questions différentes, deux lectures différentes.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas.
        """
        self._exiger_tournoi(tournoi_id)
        return self._deroules.par_tournoi(tournoi_id)

    def avancement(self, depart_id: DepartId) -> list[Phase]:
        """Renvoie **où en est ce créneau** : ses phases, ordonnées, définition assemblée.

        Pendant de `lister` à l'autre maille (ADR-0076) : `lister` dit *ce qui est prévu* pour le
        tournoi, `avancement` dit *où en est* un créneau. C'est cette lecture-ci que l'écran de
        pilotage consomme — le déroulé seul ne lui donnerait aucun identifiant de phase à faire
        vivre, ni le statut de chacune.

        Lève `DepartIntrouvable` si le créneau n'existe pas : rendre `[]` ferait passer « ce départ
        n'existe pas » pour « ce départ n'a rien à jouer », deux situations qui n'appellent pas la
        même réaction côté écran.
        """
        if self._departs.par_id(depart_id) is None:
            raise DepartIntrouvable(f"Aucun départ d'identifiant {depart_id}.")
        return self._phases.par_depart(depart_id)

    # --- Composition & édition (maille **tournoi**, à l'atelier) --------------------------------

    def ajouter(
        self,
        tournoi_id: TournoiId,
        type: TypePhase,
        sources: tuple[SourcePhase, ...] = (),
        effectif: int | None = None,
        barrage_jusqu_au: int | None = None,
        profondeur: ProfondeurClassement | None = None,
        poules: ReglageDePoules | None = None,
        big_shoot_off: ConfigurationBigShootOff | None = None,
    ) -> EtapeDeroule:
        """Ajoute une étape **en fin de déroulé** (ordre = N+1) et l'instancie dans chaque créneau.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas, une `DomainError` (→ 422) si l'étape
        ou la séquence obtenue est incohérente (source mal formée, effectif nul…). Rien n'est
        persisté si la validation échoue.

        ⚠️ **Une qualification composée ici reçoit des réglages de départ** (E05US025, ADR-0082).
        L'invariant `anomalies_etape` exige qu'une qualification porte barème **et** grain ; cette
        méthode n'en posait aucun, si bien que composer une **seconde** qualification à l'atelier
        échouait en `PhaseQualificationIncomplete` — le CA « deux qualifications coexistent » était
        infaisable de bout en bout, alors que le domaine et le moteur l'acceptaient.

        Le barème de départ est le **preset FFTA 18 m**, celui du club, et le grain celui du type.
        C'est un arbitrage assumé : `ServiceGrainValidation` refuse par ailleurs « d'inventer un
        barème que l'organisateur n'a pas choisi », mais la comparaison ne tient pas — là-bas
        l'alternative était de demander le barème d'abord, ici c'est de ne pas pouvoir composer du
        tout. La valeur n'est d'ailleurs pas cachée : l'écran la **liste** avec l'étape, et
        `PUT /tournois/{id}/qualifications/{etape_id}/bareme` la règle.
        """
        self._exiger_tournoi(tournoi_id)
        existantes = self._deroules.par_tournoi(tournoi_id)
        nouvelle = EtapeDeroule(
            tournoi_id=tournoi_id,
            ordre=len(existantes) + 1,
            type=type,
            bareme=(
                BaremeQualification.preset_ffta_18m() if type is TypePhase.QUALIFICATION else None
            ),
            validation=(
                grain_par_defaut(TypePhase.QUALIFICATION)
                if type is TypePhase.QUALIFICATION
                else None
            ),
            sources=sources,
            effectif=effectif,
            barrage_jusqu_au=barrage_jusqu_au,
            profondeur=profondeur,
            poules=poules,
            big_shoot_off=big_shoot_off,
        )
        # Valide la séquence complète (la nouvelle incluse) avant d'écrire.
        verifier_sequence([*existantes, nouvelle])
        posee = self._deroules.ajouter(nouvelle)
        for depart_id in self._creneaux(tournoi_id):
            self._phases.ajouter(posee.instancier(depart_id))
        return posee

    def modifier(
        self,
        tournoi_id: TournoiId,
        etape_id: EtapeDerouleId,
        type: TypePhase,
        sources: tuple[SourcePhase, ...],
        effectif: int | None,
        barrage_jusqu_au: int | None = None,
        profondeur: ProfondeurClassement | None = None,
        poules: ReglageDePoules | None = None,
        big_shoot_off: ConfigurationBigShootOff | None = None,
    ) -> EtapeDeroule:
        """Édite le type, les sources et l'effectif d'une étape (édition **totale** de sa config de
        séquence — `ordre` et barème/grain sont préservés).

        **Une seule écriture** (ADR-0076) : la définition ne vit qu'ici, donc tous les créneaux la
        voient changer d'un coup. Les avancements ne bougent pas — modifier le déroulé ne remet
        personne à zéro.

        Lève `PhaseIntrouvable` si l'étape n'est pas dans ce tournoi, une `DomainError` (→ 422) si
        le résultat est incohérent (ex. retyper en `qualification` sans barème, source hors bornes).

        ⚠️ **Aucune garde sur le format du tir d'un Big Shoot Off déjà tiré** (`# DETTE-062`, relevé
        à la revue d'E05US028). Le découpage manche → volées est **dérivé du réglage à chaque
        lecture** (`(m-1)·V+1 … m·V`) et n'est stocké nulle part : passer `volees` de 1 à 2 en cours
        de phase **re-partitionne des volées déjà validées** dans d'autres manches, donc rejoue les
        éliminations autrement, sans le moindre message. C'est une classe de risque neuve — la
        qualification n'a aucun regroupement dérivé — et c'est le pendant de `DETTE-057` côté format
        du tir plutôt que population. `eliminations` et les options, elles, ne déplacent aucune
        borne : seuls `volees` et `fleches_par_volee` sont en cause.
        """
        etape = self._exiger_etape(tournoi_id, etape_id)
        modifiee = replace(
            etape,
            type=type,
            sources=sources,
            effectif=effectif,
            barrage_jusqu_au=barrage_jusqu_au,
            profondeur=profondeur,
            poules=poules,
            big_shoot_off=big_shoot_off,
        )
        autres = [e for e in self._deroules.par_tournoi(tournoi_id) if e.id != etape_id]
        verifier_sequence([*autres, modifiee])
        return self._deroules.enregistrer(modifiee)

    def reordonner(
        self, tournoi_id: TournoiId, etapes_ordonnees: list[EtapeDerouleId]
    ) -> list[EtapeDeroule]:
        """Réordonne **l'ensemble** du déroulé selon la liste d'identifiants fournie.

        Chaque étape reçoit un nouvel `ordre` (position dans la liste) ; les références de source
        sont **remappées** pour suivre l'étape qu'elles désignaient. Les avancements de chaque
        créneau sont réalignés dans la foulée, sinon une phase pointerait la mauvaise définition.

        Lève `ReordonnancementPhasesInvalide` (→ 409) si la liste ne recouvre pas exactement le
        déroulé, et une `DomainError` (→ 422) si l'ordre demandé rend la séquence incohérente (ex.
        une source se retrouve **après** l'étape qu'elle alimente).
        """
        self._exiger_tournoi(tournoi_id)
        actuelles = self._deroules.par_tournoi(tournoi_id)
        if not actuelles and not etapes_ordonnees:
            return []
        par_id: dict[int, EtapeDeroule] = {}
        for etape in actuelles:
            assert etape.id is not None, "Une étape listée est persistée."
            par_id[etape.id] = etape
        if sorted(etapes_ordonnees) != sorted(par_id):
            raise ReordonnancementPhasesInvalide(
                "Réordonner exige la liste complète des étapes du déroulé, chacune une seule fois."
            )
        # Ancien ordre → nouvel ordre (position dans la liste, 1-indexée).
        ancien_vers_nouveau = {
            par_id[etape_id].ordre: rang for rang, etape_id in enumerate(etapes_ordonnees, start=1)
        }
        reordonnees = [
            self._remapper(
                par_id[etape_id], nouvel_ordre=rang, ancien_vers_nouveau=ancien_vers_nouveau
            )
            for rang, etape_id in enumerate(etapes_ordonnees, start=1)
        ]
        verifier_sequence(reordonnees)  # valide l'ordre demandé
        # **En un bloc, pas étape par étape** : un déroulé n'a qu'une étape par rang, donc tout
        # échange passerait par un doublon transitoire que la persistance refuse. Le port porte
        # cette écriture d'ensemble, à charge pour l'adapter de savoir s'y prendre (ADR-0003).
        # DETTE-025 (docs/dette.md) : ces **deux** écritures ne forment pas une unité de travail —
        # chaque appel de repository ouvre sa session et son commit. Une panne entre elles laisse
        # les étapes renumérotées et les avancements sur leurs anciens rangs, donc chaque phase
        # pointant la **définition voisine** : le créneau exécuterait un autre barème, sans erreur
        # ni signal. Le remède est un geste atomique sur l'adapter concret (patron
        # `consigner_dans`), hors périmètre ici ; ne pas contourner en réordonnant une à une.
        posees = self._deroules.reordonner(reordonnees)
        self._realigner_avancements(tournoi_id, ancien_vers_nouveau)
        return posees

    def supprimer(self, tournoi_id: TournoiId, etape_id: EtapeDerouleId) -> None:
        """Retire une étape du déroulé et **recompacte** les ordres (1..N sans trou).

        Les avancements correspondants disparaissent de chaque créneau : une phase sans définition
        ne pourrait rien dire d'utile.

        Lève `PhaseIntrouvable` si l'étape n'est pas dans ce tournoi, `PhaseSourceReferencee`
        (→ 409) si une **autre** étape tire d'elle ses participants (il faut d'abord la réaffecter).
        """
        cible = self._exiger_etape(tournoi_id, etape_id)
        if cible.type is TypePhase.QUALIFICATION:
            raise PhaseQualificationNonSupprimable(
                "La phase de qualification se gère via le barème ; elle ne se supprime pas ici."
            )
        restantes = [e for e in self._deroules.par_tournoi(tournoi_id) if e.id != etape_id]
        if any(s.ordre_source == cible.ordre for e in restantes for s in e.sources):
            raise PhaseSourceReferencee(
                "Cette phase alimente une autre phase de la séquence ; réaffectez-la d'abord."
            )
        # Recompactage : les ordres au-delà de l'étape retirée descendent d'un cran.
        ancien_vers_nouveau = {
            e.ordre: (e.ordre if e.ordre < cible.ordre else e.ordre - 1) for e in restantes
        }
        recompactees = [
            self._remapper(
                e,
                nouvel_ordre=ancien_vers_nouveau[e.ordre],
                ancien_vers_nouveau=ancien_vers_nouveau,
            )
            for e in restantes
        ]
        verifier_sequence(recompactees)
        # ⚠️ **On retire avant de recompacter, et les avancements avant leur étape.** Deux raisons,
        # dans cet ordre :
        # 1. le rang étant la clé de jointure vers la définition, décaler les étapes avant d'avoir
        #    retiré la phase supprimée la ferait pointer sur l'étape voisine — une phase orpheline
        #    qui ressusciterait sous une autre définition ;
        # 2. un tournoi ne porte qu'une étape par rang : recompacter avant d'avoir retiré la cible
        #    ferait écrire son rang sur sa voisine alors qu'elle l'occupe encore.
        # Le déroulé a donc, le temps de ces trois gestes, un trou dans sa numérotation. C'est
        # assumé : rien ne le lit entre-temps (écrivain unique, règle 7), et l'alternative — poser
        # la séquence complète en une écriture — demanderait au port de savoir supprimer et
        # renuméroter du même mouvement, pour un gain nul ici.
        for depart_id in self._creneaux(tournoi_id):
            for phase in self._phases.par_depart(depart_id):
                if phase.ordre == cible.ordre:
                    assert phase.id is not None, "Une phase relue est persistée."
                    self._phases.supprimer(phase.id)
        assert cible.id is not None, "Une étape consultée est persistée."
        self._deroules.supprimer(cible.id)
        # ⚠️ **Réaligner AVANT de recompacter, jamais après** (revue E01US025, axe C2).
        # `_realigner_avancements` relit les phases par `par_depart`, qui **assemble** — et
        # l'assemblage **écarte silencieusement** toute phase dont le rang n'a plus d'étape.
        # Recompacter d'abord rendait donc la dernière phase de chaque créneau invisible à la
        # relecture : elle n'était jamais réalignée, restait en base à son ancien rang, et l'ajout
        # d'étape suivant heurtait `uq_phase_depart_ordre` — écran d'atelier en 500, définitivement.
        # Ici les rangs des phases correspondent encore tous à une étape : elles se relisent toutes.
        # DETTE-025 : même défaut qu'à `reordonner`, sur **trois** écritures ici (retrait des
        # avancements, retrait de l'étape, réalignement + recompactage). Le trou de numérotation
        # décrit ci-dessus est assumé *dans* le geste ; ce qui ne l'est pas, c'est une panne qui le
        # fige — le déroulé garderait un rang manquant et des phases mal appariées.
        self._realigner_avancements(tournoi_id, ancien_vers_nouveau)
        self._deroules.reordonner(recompactees)

    def _creneaux(self, tournoi_id: TournoiId) -> list[int]:
        """Les identifiants des créneaux du tournoi — là où les avancements se déclinent."""
        return [d.id for d in self._departs.par_tournoi(tournoi_id) if d.id is not None]

    def _realigner_avancements(
        self, tournoi_id: TournoiId, ancien_vers_nouveau: dict[int, int]
    ) -> None:
        """Fait suivre le rang des phases quand celui de leur étape change.

        Le rang **est** la clé de jointure (ADR-0076) : une phase restée sur son ancien ordre
        pointerait la définition d'une autre étape, sans la moindre erreur visible. C'est le seul
        éventail qui subsiste après la séparation — et il ne déplace aucun réglage, juste un rang.

        L'écriture se fait **par créneau et en un bloc** : un créneau ne porte qu'un avancement par
        rang, donc les décaler un à un buterait sur cette unicité dès que deux rangs s'échangent.
        """
        for depart_id in self._creneaux(tournoi_id):
            a_realigner = [
                phase.avec_ordre(ancien_vers_nouveau[phase.ordre])
                for phase in self._phases.par_depart(depart_id)
                if ancien_vers_nouveau.get(phase.ordre, phase.ordre) != phase.ordre
            ]
            if a_realigner:
                self._phases.reordonner(a_realigner)

    # --- Cycle de vie (transitions gardées, patron ServiceTournois) ----------------------------

    def demarrer(self, depart_id: DepartId, phase_id: PhaseId) -> Phase:
        """`a_venir → en_cours`. Lève `TransitionStatutInvalide` (→ 409) hors de `a_venir`."""
        return self._transition(depart_id, phase_id, StatutPhase.A_VENIR, Phase.demarrer, "à venir")

    def mettre_en_pause(self, depart_id: DepartId, phase_id: PhaseId) -> Phase:
        """`en_cours → en_pause`. Lève `TransitionStatutInvalide` (→ 409) hors de `en_cours`."""
        return self._transition(
            depart_id, phase_id, StatutPhase.EN_COURS, Phase.mettre_en_pause, "en cours"
        )

    def reprendre(self, depart_id: DepartId, phase_id: PhaseId) -> Phase:
        """`en_pause → en_cours`. Lève `TransitionStatutInvalide` (→ 409) hors de `en_pause`."""
        return self._transition(
            depart_id, phase_id, StatutPhase.EN_PAUSE, Phase.reprendre, "en pause"
        )

    def terminer(self, depart_id: DepartId, phase_id: PhaseId) -> Phase:
        """`en_cours → terminee`. Lève `TransitionStatutInvalide` (→ 409) hors de `en_cours`."""
        return self._transition(
            depart_id, phase_id, StatutPhase.EN_COURS, Phase.terminer, "en cours"
        )

    # --- Internes ------------------------------------------------------------------------------

    def _transition(
        self,
        depart_id: DepartId,
        phase_id: PhaseId,
        attendu: StatutPhase,
        muter: Callable[[Phase], Phase],
        libelle_attendu: str,
    ) -> Phase:
        phase = self._exiger_phase(depart_id, phase_id)
        if phase.statut is not attendu:
            raise TransitionStatutInvalide(
                f"Cette transition n'est possible que sur une phase {libelle_attendu}."
            )
        return self._phases.enregistrer(muter(phase))

    @staticmethod
    def _remapper(
        etape: EtapeDeroule, *, nouvel_ordre: int, ancien_vers_nouveau: dict[int, int]
    ) -> EtapeDeroule:
        """Renvoie l'étape à son nouvel ordre, **chacune** de ses sources remappée sur le nouvel
        ordre de l'étape qu'elle désignait.

        `# DETTE-026` — les ancres de source sont des `ordre`, non des `id` : déplacer une phase
        oblige donc à réécrire les références de toutes celles qui la citent. Depuis E05US010 une
        phase en porte **plusieurs** — le remappage vaut pour chacune, sans quoi seule la première
        suivrait le déplacement et les autres pointeraient une phase arbitraire. C'est la surface de
        ce raccourci qui a grandi, pas sa nature.
        """
        deplacee = etape.avec_ordre(nouvel_ordre)
        if not etape.sources:
            return deplacee
        return deplacee.avec_sources(
            tuple(
                replace(source, ordre_source=ancien_vers_nouveau[source.ordre_source])
                for source in etape.sources
            )
        )

    def _exiger_tournoi(self, tournoi_id: TournoiId) -> None:
        """Le tournoi doit exister : c'est lui qui porte le **déroulé** (ADR-0076)."""
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")

    def _exiger_etape(self, tournoi_id: TournoiId, etape_id: EtapeDerouleId) -> EtapeDeroule:
        """L'étape `etape_id` **si elle appartient à ce tournoi** — garde d'autorisation.

        Sans elle, l'identifiant d'une étape d'un *autre* tournoi serait accepté sur cette route.
        """
        etape = next((e for e in self._deroules.par_tournoi(tournoi_id) if e.id == etape_id), None)
        if etape is None:
            raise PhaseIntrouvable(
                f"Aucune étape d'identifiant {etape_id} dans le déroulé du tournoi {tournoi_id}."
            )
        return etape

    def _exiger_phase(self, depart_id: DepartId, phase_id: PhaseId) -> Phase:
        """La phase `phase_id` **si elle appartient à ce créneau** — maille du cycle de vie."""
        phase = phase_du_depart(self._phases, depart_id, phase_id)
        if phase is None:
            raise PhaseIntrouvable(
                f"Aucune phase d'identifiant {phase_id} dans le départ {depart_id}."
            )
        return phase
