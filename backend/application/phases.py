"""Service des **phases** — la cohérence de la séquence est au domaine, les conflits d'état ici.

`SequencePhases` rejette une séquence incohérente à la **construction** (422) ; le service n'en
réimplémente rien et arbitre les transitions illégales (409/404).

⚠️ **Le réordonnancement et la suppression REMAPPENT les références de source**, ancrées par
l'`ordre` de la phase amont et non par son identité. C'est `DETTE-026`.
"""

# DETTE-057 — le mode d'une poule n'est pas encore porté par un réglage dédié.

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
from domain.arret_programme import ArretProgramme
from domain.bareme import BaremeQualification
from domain.big_shoot_off import ConfigurationBigShootOff
from domain.colline import ConfigurationColline
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
from domain.qualification import DecoupageEnTours
from domain.suisse import ConfigurationSuisse
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
        tournoi, `avancement` dit *où en est* un créneau — c'est cette lecture que l'écran de
        pilotage consomme. Lève `DepartIntrouvable` si le créneau n'existe pas : rendre `[]` ferait
        passer « ce départ n'existe pas » pour « ce départ n'a rien à jouer », deux situations qui
        n'appellent pas la même réaction.
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
        suisse: ConfigurationSuisse | None = None,
        colline: ConfigurationColline | None = None,
        decoupage: DecoupageEnTours | None = None,
        arrets: tuple[ArretProgramme, ...] = (),
        titre: str | None = None,
    ) -> EtapeDeroule:
        """Ajoute une étape **en fin de déroulé** (ordre = N+1) et l'instancie dans chaque créneau.

        Rien n'est persisté si la validation échoue. ⚠️ **Une qualification composée ici reçoit des
        réglages de départ** (E05US025, ADR-0082) : `anomalies_etape` exige qu'elle porte barème
        **et** grain, si bien que composer une seconde qualification échouait — le CA « deux
        qualifications coexistent » était infaisable. Le barème de départ est le preset FFTA 18 m,
        et la valeur n'est pas cachée : l'écran la **liste** avec l'étape.
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
            suisse=suisse,
            colline=colline,
            decoupage=decoupage,
            arrets=arrets,
            titre=titre,
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
        suisse: ConfigurationSuisse | None = None,
        colline: ConfigurationColline | None = None,
        decoupage: DecoupageEnTours | None = None,
        arrets: tuple[ArretProgramme, ...] = (),
        titre: str | None = None,
    ) -> EtapeDeroule:
        """Édite le type, les sources et l'effectif d'une étape — édition **totale** de sa config.

        **Une seule écriture** (ADR-0076) : la définition ne vit qu'ici, donc tous les créneaux la
        voient changer d'un coup, et les avancements ne bougent pas. ⚠️ **Aucune garde sur le
        format du tir d'un Big Shoot Off déjà tiré** (`# DETTE-062`) : le découpage manche → volées
        est dérivé à chaque lecture, donc passer `volees` de 1 à 2 **re-partitionne des volées déjà
        validées** et rejoue les éliminations autrement, sans message.
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
            suisse=suisse,
            # E05US027 : passé explicitement lui aussi, pour la raison dite juste en dessous.
            colline=colline,
            # ⚠️ **Passé explicitement, comme ses trois voisins** : `replace` conserve ce qu'on ne
            # lui donne pas, et un découpage survivant à un retypage ferait lever
            # `DecoupageEnToursInvalide` sur une édition par ailleurs licite — l'organisateur ne
            # pourrait plus transformer sa qualification découpée en autre chose. L'édition est
            # **totale** : ce que le client omet est effacé.
            decoupage=decoupage,
            # E16US002 : passé explicitement lui aussi. Même motif que ses voisins — l'édition est
            # **totale**, donc un titre que le client omet est **effacé**, et non conservé par la
            # grâce de `replace`. Sans cette ligne, retirer un titre serait impossible depuis
            # l'écran : le champ vidé reviendrait rempli au rechargement.
            titre=titre,
            arrets=arrets,
        )
        autres = [e for e in self._deroules.par_tournoi(tournoi_id) if e.id != etape_id]
        verifier_sequence([*autres, modifiee])
        return self._deroules.enregistrer(modifiee)

    def reordonner(
        self, tournoi_id: TournoiId, etapes_ordonnees: list[EtapeDerouleId]
    ) -> list[EtapeDeroule]:
        """Réordonne **l'ensemble** du déroulé selon la liste d'identifiants fournie.

        Chaque étape reçoit un nouvel `ordre` ; les références de source sont **remappées** pour
        suivre l'étape qu'elles désignaient, et les avancements de chaque créneau réalignés dans la
        foulée — sinon une phase pointerait la mauvaise définition. Lève
        `ReordonnancementPhasesInvalide` (409) si la liste ne recouvre pas exactement le déroulé.
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
        # échange passerait par un doublon transitoire que la persistance refuse (ADR-0003).
        #
        # DETTE-025 : ces **deux** écritures ne forment pas une unité de travail. Une panne entre
        # elles laisse les étapes renumérotées et les avancements sur leurs anciens rangs, donc
        # chaque phase pointant la **définition voisine** — un autre barème, sans erreur ni signal.
        # Ne pas contourner en réordonnant une à une.
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
        # ⚠️ **On retire avant de recompacter, et les avancements avant leur étape.** Le rang
        # étant la clé de jointure vers la définition, décaler les étapes avant d'avoir retiré la
        # phase supprimée la ferait pointer sur l'étape voisine ; et un tournoi ne portant qu'une
        # étape par rang, recompacter d'abord écrirait son rang sur sa voisine.
        #
        # Le déroulé a donc, le temps de ces trois gestes, un trou dans sa numérotation — assumé,
        # rien ne le lit entre-temps (écrivain unique, règle 7).
        for depart_id in self._creneaux(tournoi_id):
            for phase in self._phases.par_depart(depart_id):
                if phase.ordre == cible.ordre:
                    assert phase.id is not None, "Une phase relue est persistée."
                    self._phases.supprimer(phase.id)
        assert cible.id is not None, "Une étape consultée est persistée."
        self._deroules.supprimer(cible.id)
        # ⚠️ **Réaligner AVANT de recompacter, jamais après** (revue E01US025).
        # `_realigner_avancements` relit les phases par `par_depart`, qui **assemble** — et
        # l'assemblage **écarte silencieusement** toute phase dont le rang n'a plus d'étape.
        # Recompacter d'abord rendait la dernière phase de chaque créneau invisible : jamais
        # réalignée, restée en base à son ancien rang, elle faisait heurter `uq_phase_depart_ordre`
        # à l'ajout suivant — écran d'atelier en 500, définitivement.
        #
        # DETTE-025 : même défaut qu'à `reordonner`, sur **trois** écritures ici.
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
        pointerait la définition d'une autre étape, sans la moindre erreur visible. L'écriture se
        fait **par créneau et en un bloc** — un créneau ne porte qu'un avancement par rang, donc
        les décaler un à un buterait sur cette unicité dès que deux rangs s'échangent.
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
        """Renvoie l'étape à son nouvel ordre, **chacune** de ses sources remappée.

        `# DETTE-026` — les ancres de source sont des `ordre`, non des `id` : déplacer une phase
        oblige à réécrire les références de toutes celles qui la citent. Depuis E05US010 une phase
        en porte **plusieurs**, et le remappage vaut pour chacune — sans quoi seule la première
        suivrait le déplacement. C'est la surface de ce raccourci qui a grandi, pas sa nature.
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
