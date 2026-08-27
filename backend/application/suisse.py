"""Service **Suisse** — une rencontre est un duel ordinaire ; seule la navigation diffère.
Ni appariements ni rondes ne sont persistés : tout se rejoue des duels validés (règle 9).

⚠️ **Le moteur REFUSE d'apparier par-dessus une ronde en cours de saisie**, et ce refus est le cœur
du service : apparier perdrait les rencontres non saisies et donnerait le bye à quelqu'un qui vient
de tirer. « Partiellement saisie » est le régime **normal** du jour J, pas un cas limite.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from application.classements import ServiceClassement
from application.erreurs import (
    DuelDesynchronise,
    GabaritDuTournoiAbsent,
    PhaseIntrouvable,
    PhasePasReglee,
    PhasePasUnSuisse,
    RencontreIntrouvable,
    TournoiIntrouvable,
)
from application.gel_de_pause import (
    DeclencheurArrets,
    EvaluateurArrets,
    refuser_si_en_pause,
)
from application.portee import phase_du_tournoi
from application.prelevement import ResolveurClassement, preleves, tranche
from application.routage import RencontreARouter, RencontresARouter
from application.saisie_duels import Duelliste, ServiceSaisieDuels
from domain.blason import ZoneScore
from domain.classement import LigneClassement
from domain.classement_de_suisse import classement_de_suisse
from domain.classement_de_tableau import ClassementSource
from domain.duel import BaremeDuel, Cote, Duel
from domain.participant import Participant
from domain.phase import Phase, PhaseId, TypePhase
from domain.placement_par_bloc import (
    BlocDeCouloirs,
    ConflitDeBloc,
    RaisonConflitBloc,
    couloirs_de_la_paire,
    placer_les_blocs,
)
from domain.ports import (
    DuelRepository,
    GabaritSalleRepository,
    PhaseRepository,
    PlacementParBlocRepository,
    TournoiRepository,
)
from domain.suisse import (
    POINTS_DEFAITE,
    POINTS_NUL,
    POINTS_VICTOIRE,
    Appariement,
    ConfigurationSuisse,
    RangSuisse,
    ResultatRonde,
    apparier_ronde,
    classement_suisse,
    rondes_maximales,
)
from domain.suivi_deroule import AvancementDePhase
from domain.tournoi import TournoiId


@dataclass(frozen=True)
class RencontreDeRonde:
    """Une rencontre d'une ronde, prête à l'affichage et à la saisie.

    `numero` est le `match_numero` de la table `duel` : un **compteur continu sur toute la phase**,
    ce qui permet de porter les rencontres de toutes les rondes sans table neuve. ⚠️ Un compteur,
    donc **pas une position stable** (DETTE-057) : si la population change après des tirs, les
    numéros glissent et `desynchronisee` le dit — le tir est alors **masqué** plutôt que
    ré-attribué (ADR-0049 §4).
    """

    numero: int
    ronde: int
    haut: Duelliste | None
    bas: Duelliste | None
    couloirs: tuple[tuple[int, str], tuple[int, str]] | None
    """Les deux couloirs de la rencontre, **dérivés** du bloc de la phase — `None` si le plan n'est
    pas posé. Jamais persistés : c'est le bloc qui l'est (ADR-0083 §3)."""

    duel: Duel | None
    desynchronisee: bool
    bareme: BaremeDuel
    zones: tuple[ZoneScore, ...]


@dataclass(frozen=True)
class RondeAffichee:
    """Une ronde : ses rencontres, son porteur de bye, et si elle est close.

    `close` est la seule information dont l'écran a besoin pour savoir s'il peut annoncer la ronde
    suivante — et c'est aussi ce qui empêche le service de l'apparier.
    """

    numero: int
    rencontres: tuple[RencontreDeRonde, ...]
    bye: Duelliste | None
    close: bool


@dataclass(frozen=True)
class EtatSuisse:
    """La photo complète d'une phase de suisse : ses rondes jouées ou en cours, son classement.

    `rondes_maximales` est la **borne** que l'effectif du jour autorise — ce que l'atelier affiche
    en clair sous le champ de réglage (CA « avec le maximum que l'effectif autorise »). Elle est
    rendue ici plutôt que calculée à l'écran : deux arithmétiques pour une même règle sont une
    divergence en attente, la leçon des dix filtres d'ADR-0083.
    """

    phase_id: PhaseId
    nb_rondes: int
    rondes_maximales: int
    effectif: int
    rondes: tuple[RondeAffichee, ...]
    classement: tuple[RangSuisse, ...]
    conflits: tuple[ConflitDeBloc, ...] = ()
    """Ce que la pose du plan n'a **pas** pu faire — **ou** le fait qu'elle n'a pas eu lieu.

    Le placement **rapporte** son échec au lieu de tronquer en silence. ⚠️ **Renseigné en lecture
    aussi** — rempli par la seule `regenerer_plan`, ce champ restait vide sur la route de saisie et
    le message « plan non posé » de l'écran scoreur était une branche morte. En relecture, la seule
    raison connaissable est `NON_POSEE` : les raisons réelles ne vivent que dans la réponse de
    `regenerer_plan` (régime hérité du jumeau poules).
    """


_PLAN_A_REPOSER = (ConflitDeBloc(1, RaisonConflitBloc.NON_POSEE),)
"""Le seul conflit qu'une **relecture** sait rapporter : le plan ne couvre pas le plateau."""


def _plan_suffisant(bloc: BlocDeCouloirs | None, effectif: int) -> bool:
    """Le bloc posé couvre-t-il **le plateau d'aujourd'hui** ?

    ⚠️ **Tester la seule présence du bloc ne suffit pas** : `regenerer_plan` le dimensionne sur
    l'effectif **du jour de la pose**, et son numéro est toujours 1 — un archer inscrit après coup
    le rend **trop court**, et les rencontres en débordement perdent leur cible sans signal. Le
    jumeau poules n'a pas ce trou (une croissance y ajoute des *groupes* que `_conflits_du_plan`
    voit), ce qui l'a rendu invisible par analogie. Empreinte attendue : deux couloirs par paire.
    """
    if bloc is None:
        return False
    return len(bloc.places) >= 2 * (effectif // 2)


class ServiceSuisse:
    """Cas d'usage du système suisse : consulter une phase, saisir ses rencontres, la classer."""

    def __init__(
        self,
        tournois: TournoiRepository,
        phases: PhaseRepository,
        gabarits: GabaritSalleRepository,
        placements: PlacementParBlocRepository,
        duels: DuelRepository,
        classements: ServiceClassement,
        saisie_duels: ServiceSaisieDuels,
    ) -> None:
        self._tournois = tournois
        self._phases = phases
        self._gabarits = gabarits
        self._placements = placements
        self._duels = duels
        self._classements = classements
        # ⚠️ **Pas pour saisir** — uniquement pour emprunter sa résolution de classement amont et sa
        # résolution de pavé (barème par arme, zones du blason). Même parti que `ServicePoules`, et
        # le sens de dépendance est sûr : `saisie_duels` ne connaît pas le suisse.
        self._saisie_duels = saisie_duels

        # E05US033 : collaborateur **partagé** par les cinq services qui écrivent un résultat
        # (`application.gel_de_pause`), inerte tant que le composition root n'y a rien branché.
        self._arrets = DeclencheurArrets()

    # --- Lecture ---------------------------------------------------------------------------------

    def etat(self, tournoi_id: TournoiId, phase_id: PhaseId) -> EtatSuisse:
        """La photo complète : rondes rejouées, ronde en cours, classement.

        `# DETTE-031` — recomposée **intégralement** à chaque lecture, chaîne de sources amont
        comprise, sans mémoïsation transverse aux requêtes. Même régime que les poules.

        Lève `TournoiIntrouvable` / `PhaseIntrouvable` (404), `PhasePasUnSuisse` ou
        `PhasePasReglee` (409).
        """
        phase, participants = self._population(tournoi_id, phase_id)
        return self._photo(phase, participants)

    def avancement_de_phase(
        self, tournoi_id: TournoiId, phase_id: PhaseId
    ) -> AvancementDePhase | None:
        """Où en est ce système suisse — le port `LecteurAvancementDePhase` (ADR-0090 §5).

        Le nombre de tours est celui que l'effectif du jour rend **jouable**, pas celui qui est
        réglé : un suisse réglé à 7 rondes n'en apparie que 5 à 12 archers. Le tour courant est la
        première ronde **non close**, `None` quand toutes le sont. ⚠️ **`None` — et non « zéro tour
        » — quand la borne vaut 0** (sous deux tireurs) : cas normal et durable d'une phase dont la
        source amont n'a classé personne, que le plancher du domaine ne rattrape pas.
        """
        etat = self.etat(tournoi_id, phase_id)
        if etat.rondes_maximales == 0:
            return None
        ouverte = next((ronde for ronde in etat.rondes if not ronde.close), None)
        return AvancementDePhase(
            nb_tours=min(etat.nb_rondes, etat.rondes_maximales),
            tour_courant=ouverte.numero if ouverte is not None else None,
        )

    def classement_de_phase(
        self, tournoi_id: TournoiId, phase_id: PhaseId, resolveur: ResolveurClassement
    ) -> ClassementSource:
        """Le classement que cette phase **produit** — le port `LecteurClassementDePhase`.

        Sans lui, un prélèvement visant un système suisse restait **inerte** : l'aval recevait tous
        les archers en lice, plausible et faux. `rang_premier` est posé avec le **même** résolveur
        que celui qui a servi à prélever — deux bases différentes situeraient la population et le
        décalage dans deux espaces de rangs distincts (`DETTE-034`).
        """
        phase, participants = self._population(tournoi_id, phase_id, resolveur)
        photo = self._photo(phase, participants)
        return replace(
            classement_de_suisse(
                photo.classement, {ligne.archer_id: ligne for ligne in participants}
            ),
            rang_premier=tranche(phase, resolveur),
        )

    def _photo(self, phase: Phase, participants: list[LigneClassement]) -> EtatSuisse:
        """Le cœur d'`etat`, séparé des gardes : rejouer les rondes, puis classer.

        Extrait pour que `classement_de_phase` réutilise exactement le même calcul sans repayer la
        résolution de population — et surtout sans la refaire avec un **autre** résolveur, ce qui
        rejouerait deux appariements différents pour la même phase.
        """
        phase_id = phase.id
        assert phase_id is not None, "`_population` a déjà refusé une phase sans identité."
        configuration = self._configuration(phase)
        lignes = {ligne.archer_id: ligne for ligne in participants}
        # Une phase encore vide est une photo **vide**, pas une erreur : elle se compose et se règle
        # avant que sa population existe. Sans cette porte, l'écran de saisie et toute phase avale
        # qui y prélève sortaient en 500 (le correctif que les poules ont dû faire en revue).
        if len(participants) < 2:
            return EtatSuisse(
                phase_id=phase_id,
                nb_rondes=configuration.nb_rondes,
                # **0, pas 1** : sous deux tireurs aucune ronde n'est appariable (`apparier_ronde`
                # refuse), et annoncer « 1 ronde au maximum » sur une phase vide serait faux.
                rondes_maximales=0,
                effectif=len(participants),
                rondes=(),
                classement=(),
            )
        tireurs = [Participant.individuel(ligne.archer_id) for ligne in participants]
        # ⚠️ **On borne ici, on ne lève pas** — la première version faisait l'inverse, bloquant de
        # revue reproduit par trois axes. `ConfigurationSuisse.nb_rondes` vaut **5** par défaut et
        # `EtapeDeroule` ne vérifie la borne que si l'effectif est **déclaré** : une phase réglée
        # par défaut et jouée à 4 archers faisait lever `apparier_ronde` dès la première ronde,
        # donc **422 sur le palmarès public, son PDF et le panneau de routage**.
        #
        # L'état expose les deux nombres — `nb_rondes` (le réglage) et `rondes_maximales` (ce que
        # l'effectif permet) — donc l'atelier montre l'écart au lieu de le subir.
        maximum = rondes_maximales(len(tireurs))
        jouables = replace(configuration, nb_rondes=min(configuration.nb_rondes, maximum))
        # Un **seul** bloc pour toute la phase : une ronde apparie tout le plateau d'un coup, il n'y
        # a donc pas de groupes à distinguer. Le numéro 1 est celui que `placer_les_blocs` attribue.
        bloc = next(iter(self._placements.par_phase(phase_id)), None)
        rondes, resultats, byes = self._rejouer(phase_id, tireurs, jouables, lignes, bloc)
        return EtatSuisse(
            phase_id=phase_id,
            nb_rondes=configuration.nb_rondes,
            rondes_maximales=maximum,
            effectif=len(tireurs),
            rondes=rondes,
            classement=classement_suisse(tireurs, resultats, byes),
            # ⚠️ **Le manque se rapporte à la LECTURE, pas seulement après une pose.** `conflits`
            # n'était renseigné que par `regenerer_plan` : sur la route de saisie il restait
            # toujours vide, donc le message « le plan de cibles n'est pas posé » de l'écran scoreur
            # était une **branche morte** — le scoreur voyait ses rondes sans cible ni explication.
            #
            # On **relaie** le manque, on ne le comble pas : poser le bloc ici écrirait un plan là
            # où l'appelant croit ne faire que lire (ADR-0083 §3). `NON_POSEE` et rien d'autre —
            # rien n'est persisté qui dise *pourquoi* le bloc manque.
            conflits=() if _plan_suffisant(bloc, len(tireurs)) else _PLAN_A_REPOSER,
        )

    def _rejouer(
        self,
        phase_id: PhaseId,
        tireurs: list[Participant],
        configuration: ConfigurationSuisse,
        lignes: dict[int, LigneClassement],
        bloc: BlocDeCouloirs | None,
    ) -> tuple[tuple[RondeAffichee, ...], list[ResultatRonde], list[Participant]]:
        """Rejoue les rondes des duels validés, et **s'arrête à la première ronde incomplète**.

        L'arrêt n'est pas une précaution : `apparier_ronde` **refuse** d'apparier par-dessus une
        ronde en cours, parce que la suivante perdrait les rencontres non saisies et donnerait le
        bye à quelqu'un qui vient de tirer. ⚠️ Les **byes** n'accompagnent que les rondes closes,
        pour la même raison. Le compteur de numéros court sur toute la phase et ne se recale
        jamais.
        """
        rondes: list[RondeAffichee] = []
        resultats: list[ResultatRonde] = []
        byes: list[Participant] = []
        numero = 0
        for index in range(configuration.nb_rondes):
            appariements = apparier_ronde(tireurs, resultats, configuration, byes)
            rencontres: list[RencontreDeRonde] = []
            acquis: list[ResultatRonde] = []
            bye: Participant | None = None
            close = True
            # La position **dans la ronde** décide des couloirs, et se recompte à chaque ronde : une
            # position cumulée ferait glisser la phase d'un cran par ronde et déborder de son bloc.
            position = 0
            for appariement in appariements:
                if appariement.est_bye:
                    bye = appariement.a
                    continue
                numero += 1
                rencontre = self._rencontre(
                    numero, index + 1, appariement, phase_id, lignes, bloc, position
                )
                position += 1
                rencontres.append(rencontre)
                resultat = _resultat_de(rencontre)
                if resultat is None:
                    close = False
                else:
                    acquis.append(resultat)
            rondes.append(
                RondeAffichee(
                    numero=index + 1,
                    rencontres=tuple(rencontres),
                    bye=None if bye is None else self._duelliste(bye, lignes),
                    close=close,
                )
            )
            if not close:
                break
            resultats.extend(acquis)
            if bye is not None:
                byes.append(bye)
        return tuple(rondes), resultats, byes

    def _rencontre(
        self,
        numero: int,
        ronde: int,
        appariement: Appariement,
        phase_id: PhaseId,
        lignes: dict[int, LigneClassement],
        bloc: BlocDeCouloirs | None,
        position: int,
    ) -> RencontreDeRonde:
        """Assemble une rencontre : ses adversaires résolus, son pavé, son tir.

        Le pavé est résolu par **le même code** que celui d'un duel de tableau
        (`ServiceSaisieDuels.bareme_de` / `zones_de`) : une rencontre de ronde *est* un duel
        ordinaire, et le même archer ne peut pas tirer en sets d'un côté et en cumul de l'autre.
        """
        a = appariement.a
        b = appariement.b
        assert b is not None, "`_rejouer` écarte les byes avant d'appeler cette méthode."
        bareme = self._saisie_duels.bareme_de(a, lignes)
        charge = self._duels.charger(phase_id, numero, bareme=bareme)
        # ⚠️ **L'ancrage d'ADR-0049 §4.** Un tir dont les duellistes enregistrés divergent des
        # adversaires recalculés est **masqué**, jamais ré-attribué : la rencontre s'affiche non
        # tirée plutôt que de prêter un score au mauvais couple.
        attendus = (a, b)
        concorde = (
            charge is not None
            and (
                charge.participant_haut,
                charge.participant_bas,
            )
            == attendus
        )
        return RencontreDeRonde(
            numero=numero,
            ronde=ronde,
            haut=self._duelliste(a, lignes),
            bas=self._duelliste(b, lignes),
            couloirs=couloirs_de_la_paire(bloc, position),
            duel=charge if concorde else None,
            # Masquer ne suffit pas : sans ce drapeau la rencontre s'afficherait « à tirer »,
            # indiscernable d'une rencontre jamais commencée, et le scoreur se prendrait un 409 sur
            # un écran qui l'invitait à saisir (leçon de la revue d'E05US023).
            desynchronisee=charge is not None and not concorde,
            bareme=bareme,
            zones=self._saisie_duels.zones_de(a, lignes),
        )

    def _duelliste(self, participant: Participant, lignes: dict[int, LigneClassement]) -> Duelliste:
        """Le duelliste résolu — nom et prénom depuis le classement."""
        ligne = lignes.get(participant.ref_id)
        if ligne is None:
            return Duelliste(archer_id=participant.ref_id, nom="?", prenom="")
        return Duelliste(archer_id=ligne.archer_id, nom=ligne.nom, prenom=ligne.prenom)

    def regenerer_plan(self, tournoi_id: TournoiId, phase_id: PhaseId) -> EtatSuisse:
        """Pose la phase sur la salle et **remplace** le plan existant.

        ⚠️ **Un seul bloc, là où les poules en posent un par groupe** : une ronde apparie **tout le
        plateau** d'un coup, donc la phase occupe une plage contiguë et les couloirs de chaque
        rencontre s'y dérivent ronde par ronde. À effectif impair le porteur de bye ne tire pas, et
        **ce n'est jamais le même** — d'où le bloc persisté plutôt qu'« archer → couloir »
        (ADR-0083 §3). Reposer après un changement d'effectif peut désynchroniser des tirs.
        """
        phase, participants = self._population(tournoi_id, phase_id)
        # ⚠️ **Toutes les gardes avant la moindre écriture** (correctif de revue). La version
        # d'origine appelait `definir_plan` puis `etat()` : une phase non réglée faisait donc lever
        # `PhasePasReglee` **après** que le plan ait été écrit, et l'organisateur recevait un 409
        # sur un geste qui avait bien eu lieu — il relançait en croyant que rien ne s'était passé.
        self._configuration(phase)
        gabarit = self._gabarits.par_tournoi(tournoi_id)
        if gabarit is None:
            raise GabaritDuTournoiAbsent(
                f"Aucun gabarit de salle n'est appliqué au tournoi {tournoi_id}."
            )
        plan = placer_les_blocs([2 * (len(participants) // 2)], gabarit)
        self._placements.definir_plan(phase_id, plan.blocs)
        # ⚠️ Les conflits **de la pose** l'emportent sur le silence de la relecture : la lecture ne
        # sait pas *pourquoi* un bloc manque (rien n'est persisté qui le dise), alors qu'ici on
        # vient de l'apprendre. Sans ce report, l'organisateur dont la salle est trop petite verrait
        # un plan vide sans explication, au moment même où il vient de le générer — le défaut relevé
        # en revue d'E05US023.
        # `_photo` plutôt qu'`etat()` : la population vient d'être résolue, la re-résoudre paierait
        # deux fois la chaîne amont sur le thread du writer unique (`DETTE-031`).
        return replace(self._photo(phase, participants), conflits=plan.conflits)

    def rencontres_a_tirer(self, tournoi_id: TournoiId, phase_id: PhaseId) -> RencontresARouter:
        """Les rencontres encore à tirer — le port `LecteurRencontresARouter` (E05US026).

        Dans l'ordre du déroulé, ronde par ronde : la **première** d'un archer est celle qui vient.
        Une rencontre **désynchronisée** est écartée — son écriture est refusée, l'annoncer
        enverrait un archer sur une cible où il ne peut rien saisir. ⚠️ **`epuisee` est le champ
        qui empêche de mentir** : un suisse ne montre que sa ronde courante, donc sans lui le
        porteur de bye passait pour « terminé » sur un panneau public.
        """
        etat = self.etat(tournoi_id, phase_id)
        rondes_dues = min(etat.nb_rondes, etat.rondes_maximales)
        epuisee = len(etat.rondes) >= rondes_dues and all(r.close for r in etat.rondes)
        return RencontresARouter(
            participants=tuple(ligne.participant.ref_id for ligne in etat.classement),
            epuisee=epuisee,
            rencontres=tuple(
                RencontreARouter(
                    numero=rencontre.numero,
                    tour=ronde.numero,
                    libelle=f"Ronde {ronde.numero}",
                    haut=rencontre.haut.archer_id,
                    bas=rencontre.bas.archer_id,
                    couloirs=rencontre.couloirs,
                )
                for ronde in etat.rondes
                for rencontre in ronde.rencontres
                if rencontre.haut is not None
                and rencontre.bas is not None
                and not rencontre.desynchronisee
                and (rencontre.duel is None or not rencontre.duel.verrouille)
            ),
        )

    # --- Gardes ----------------------------------------------------------------------------------

    def _population(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        resolveur: ResolveurClassement | None = None,
    ) -> tuple[Phase, list[LigneClassement]]:
        """Les gardes, puis **qui entre dans la phase** — la 1ʳᵉ question du contrat (ADR-0083 §1).

        Générique depuis ADR-0068 : `preleves` lit chaque source dans le classement de **sa**
        phase, en remontant la chaîne. Sans source déclarée, la phase est alimentée par le
        classement du départ. `resolveur` est fourni quand l'appel vient d'en haut : on réutilise
        son cache et sa chaîne de phases visitées (`DETTE-031`, et la détection de cycle avec).
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        phase = phase_du_tournoi(self._phases, tournoi_id, phase_id)
        if phase is None:
            raise PhaseIntrouvable(f"Aucune phase {phase_id} dans le tournoi {tournoi_id}.")
        if phase.type is not TypePhase.SUISSE:
            raise PhasePasUnSuisse(f"La phase {phase_id} n'est pas un système suisse.")
        classement = self._classements.pour_depart(phase.depart_id)
        participants = preleves(
            phase,
            classement,
            resolveur
            if resolveur is not None
            else self._saisie_duels.resolveur_de_classement(tournoi_id, phase.depart_id),
        )
        return phase, participants

    def _configuration(self, phase: Phase) -> ConfigurationSuisse:
        """Le réglage de la phase, ou `PhasePasReglee` (409).

        ⚠️ **Aucune vérification de la borne ici.** Elle est portée par `EtapeDeroule`, à la
        composition, là où l'effectif **déclaré** est connu. La refaire sur l'effectif *réel* du
        jour ferait tomber la lecture d'une phase que l'atelier a acceptée — un écran qui refuse de
        s'ouvrir vaut moins qu'un écran qui montre la borne. C'est `apparier_ronde` qui reste le
        dernier rempart, et il lève une `DomainError` que la frontière traduit.
        """
        if phase.suisse is None:
            raise PhasePasReglee(
                f"La phase {phase.id} n'a pas encore de nombre de rondes : réglez-la à l'atelier "
                "avant de la faire jouer."
            )
        return phase.suisse

    # --- Saisie d'une rencontre (via la file) ----------------------------------------------------
    #
    # ⚠️ Mêmes trois méthodes que `ServicePoules`, et le même écart avec `ServiceSaisieDuels` :
    # l'agrégat, le pavé et la table sont partagés, seule la **navigation** diffère (ADR-0083 §7).

    def saisir_manche(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        numero: int,
        manche: int,
        valeurs_haut: tuple[ZoneScore, ...],
        valeurs_bas: tuple[ZoneScore, ...],
    ) -> RencontreDeRonde:
        """Saisit une manche d'une rencontre — même agrégat, même contrôle qu'un duel de tableau."""
        return self._ecrire(
            tournoi_id,
            phase_id,
            numero,
            lambda duel, bareme, zones: duel.saisir_manche(
                manche,
                valeurs_haut,
                valeurs_bas,
                zones_admises=zones,
                nb_fleches_par_volee=bareme.nb_fleches_par_volee,
            ),
        )

    def saisir_barrage(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        numero: int,
        fleche_haut: ZoneScore,
        fleche_bas: ZoneScore,
        gagnant_designe: Cote | None = None,
    ) -> RencontreDeRonde:
        """Saisit le tir de barrage **interne** à une rencontre nulle (§8.2, E04US013).

        ⚠️ **Exigé, comme partout ailleurs** — et la première rédaction affirmait le contraire.
        `Duel.valider` refuse un duel non tranché. La confusion venait du **moteur** :
        `domain/suisse.py` sait représenter un nul, parce qu'un système suisse générique en admet ;
        mais le **décor de saisie** du projet est le duel FFTA (ADR-0083 §7), qui exige un
        vainqueur. La branche `POINTS_NUL` de `_resultat_de` est donc inatteignable par ce service.
        """
        return self._ecrire(
            tournoi_id,
            phase_id,
            numero,
            lambda duel, _bareme, zones: duel.saisir_barrage(
                fleche_haut, fleche_bas, zones_admises=zones, gagnant_designe=gagnant_designe
            ),
        )

    def valider(
        self, tournoi_id: TournoiId, phase_id: PhaseId, numero: int, scoreur: str
    ) -> RencontreDeRonde:
        """Valide le tir d'une rencontre — c'est ce qui la fait entrer au classement.

        ⚠️ **La validation est le geste qui clôt une ronde**, donc celui qui autorise l'appariement
        de la suivante. Un tir non validé laisse la ronde ouverte, et le moteur **refuse**
        d'apparier par-dessus — la règle de la reconstruction d'un tableau.
        """

        # E05US033 — **garde et signalement sont ici, sur `valider`, et non dans `_ecrire`** :
        # `_ecrire` est le tronc commun des **trois** écritures, et y poser la garde gelait aussi la
        # **rectification** d'une rencontre engagée pendant la pause — le cul-de-sac que
        # `refuser_si_en_pause` interdit. La pause gèle ce qui *avance*, jamais ce qui *répare*.
        # Y poser le signalement faisait en outre payer la recomposition intégrale du créneau à
        # chaque manche, sur le thread du writer unique (`DETTE-031`), pour un résultat identique :
        # un tour n'avance que sur des rencontres **validées**.
        phase = phase_du_tournoi(self._phases, tournoi_id, phase_id)
        if phase is not None:
            refuser_si_en_pause(phase)
        rencontre = self._ecrire(
            tournoi_id, phase_id, numero, lambda duel, _bareme, _zones: duel.valider(scoreur)
        )
        if phase is not None:
            self._arrets.signaler(phase.depart_id)
        return rencontre

    def brancher_evaluateur_arrets(self, evaluateur: EvaluateurArrets) -> None:
        """Dit à qui signaler qu'un résultat vient d'être validé (E05US033, ADR-0091).

        ⚠️ **Ce branchement manquait à la première livraison**, et c'était un bloquant : le
        déclencheur n'était appelé que depuis la qualification et l'élimination directe, si bien
        qu'un arrêt programmé sur ce format ne se déclenchait **jamais** — la phase tournant seule,
        aucune validation n'atteignait le déclencheur. Relevé par les quatre axes de revue.
        """
        self._arrets.brancher(evaluateur)

    def _ecrire(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        numero: int,
        appliquer: Callable[[Duel, BaremeDuel, tuple[ZoneScore, ...]], Duel],
    ) -> RencontreDeRonde:
        """Le tronc commun des trois écritures : retrouver la rencontre, appliquer, persister.

        `# DETTE-031` — appelle `etat()` à **chaque** manche, barrage et validation, donc rejoue la
        reconstruction complète sur le thread du writer unique. La rencontre est retrouvée **par
        recomposition**, jamais par une lecture de `duel` : la ligne persistée se fierait à un
        `match_numero` qui a pu changer de sens. ⚠️ Une rencontre désynchronisée **refuse
        l'écriture** — le `or Duel.vide(...)` des poules faisait disparaître un tir validé.
        """
        rencontre = self._trouver(tournoi_id, phase_id, numero)
        if rencontre.desynchronisee:
            raise DuelDesynchronise(
                f"Le tir de la rencontre {numero} oppose d'autres duellistes : la population de la "
                "phase a changé depuis. Rétablissez-la avant de saisir."
            )
        assert (
            rencontre.haut is not None and rencontre.bas is not None
        ), "`_rejouer` n'appareille que des rencontres à deux adversaires résolus."
        haut = Participant.individuel(rencontre.haut.archer_id)
        bas = Participant.individuel(rencontre.bas.archer_id)
        # Les zones sont relues en **strict** sur ce chemin d'écriture : un blason indéterminable
        # doit lever plutôt que produire un pavé vide, sinon on enregistrerait un score dont on ne
        # sait pas s'il est légal (même exigence qu'E04US002 et que les poules).
        zones = self._saisie_duels.zones_strictes(haut, self._lignes(phase_id))
        courant = rencontre.duel or Duel.vide(rencontre.bareme, haut, bas)
        duel = appliquer(courant, rencontre.bareme, zones)
        self._duels.enregistrer(phase_id, numero, duel)
        return replace(rencontre, duel=duel)

    def _trouver(self, tournoi_id: TournoiId, phase_id: PhaseId, numero: int) -> RencontreDeRonde:
        """La rencontre de ce numéro dans l'état rejoué, ou `RencontreIntrouvable` (404).

        Une rencontre d'une ronde **pas encore appariée** est introuvable, et c'est exact : elle
        n'existe pas tant que la ronde précédente n'est pas close.
        """
        etat = self.etat(tournoi_id, phase_id)
        for ronde in etat.rondes:
            for rencontre in ronde.rencontres:
                if rencontre.numero == numero:
                    return rencontre
        raise RencontreIntrouvable(
            f"Aucune rencontre {numero} dans la phase {phase_id} : soit elle n'existe pas, soit sa "
            "ronde n'est pas encore appariée — la précédente doit être close d'abord."
        )

    def _lignes(self, phase_id: PhaseId) -> dict[int, LigneClassement]:
        """Le classement du départ de cette phase, indexé par archer — pour résoudre le blason."""
        phase = self._phases.par_id(phase_id)
        assert phase is not None, "`etat` a déjà refusé une phase inconnue."
        return {
            ligne.archer_id: ligne
            for ligne in self._classements.pour_depart(phase.depart_id).lignes
        }


def _resultat_de(rencontre: RencontreDeRonde) -> ResultatRonde | None:
    """Traduit un tir **validé** en résultat consommable par le moteur d'appariement.

    ⚠️ **Seuls les duels validés comptent** : l'appariement de la ronde suivante changerait sinon
    sous les yeux du juge. Les points sont ceux du barème classique **doublé** (2 / 1 / 0) que
    `domain/suisse.py` emploie pour rester en entiers — une victoire vaut 1 et un nul 0,5, et le
    domaine évite le flottant. ⚠️ La branche `POINTS_NUL` n'est pas atteignable ici (le décor de
    saisie est le duel FFTA) ; elle est conservée parce que le moteur, lui, produit des nuls.
    """
    duel = rencontre.duel
    if duel is None or not duel.verrouille:
        return None
    vainqueur = duel.resultat.vainqueur
    points_a, points_b = (
        (POINTS_VICTOIRE, POINTS_DEFAITE)
        if vainqueur is Cote.HAUT
        else (POINTS_DEFAITE, POINTS_VICTOIRE)
        if vainqueur is Cote.BAS
        else (POINTS_NUL, POINTS_NUL)
    )
    haut = _volees_de(duel, cote_haut=True)
    bas = _volees_de(duel, cote_haut=False)
    return ResultatRonde(
        a=duel.participant_haut,
        b=duel.participant_bas,
        points_a=points_a,
        points_b=points_b,
        nb_dix_a=_compter(haut, "10"),
        nb_neuf_a=_compter(haut, "9"),
        nb_dix_b=_compter(bas, "10"),
        nb_neuf_b=_compter(bas, "9"),
    )


def _volees_de(duel: Duel, *, cote_haut: bool) -> tuple[str, ...]:
    """Les zones tirées par un camp, toutes manches confondues — pour le décompte FFTA."""
    return tuple(
        valeur
        for manche in duel.manches
        for volee in ((manche.volee_haut,) if cote_haut else (manche.volee_bas,))
        if volee is not None
        for valeur in volee.valeurs
    )


def _compter(valeurs: tuple[str, ...], zone: str) -> int:
    """Combien de flèches dans cette zone — le décompte de départage du §8.1."""
    return sum(1 for valeur in valeurs if valeur == zone)


__all__ = [
    "EtatSuisse",
    "RencontreDeRonde",
    "RondeAffichee",
    "ServiceSuisse",
]
