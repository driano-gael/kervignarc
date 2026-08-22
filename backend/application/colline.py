"""Service applicatif de la **colline** (E05US027) — habiter le contrat de phase jouable.

Le moteur (`domain/colline.py`) est livré depuis E05US015 et n'avait **aucun appelant de
production** : c'est le dernier volet de `DETTE-028`, que cette US referme. Ce service est cet
appelant.

## Ce qui est partagé, et ce qui ne l'est pas

Comme pour les poules ([ADR-0083](../../docs/adr/0083-le-contrat-de-phase-jouable.md) §7), le
suisse et le Big Shoot Off, ce qui est partagé avec `ServiceSaisieDuels` l'est **réellement** :
l'agrégat `Duel`, le pavé de saisie (`bareme_de` / `zones_de`) et la table `duel`. Un défi de
colline **est** un duel ordinaire, et le faire écrire autrement créerait une énième façon de saisir
un tir — l'exacte duplication qu'ADR-0083 se donne pour objet de fermer.

Ce qui diffère est la **navigation**, c'est-à-dire le `decor` du contrat : là-bas on retrouve un
match dans un arbre, en poules une rencontre dans un groupe, au suisse une rencontre dans une ronde,
ici un **défi dans une manche**. C'est tout ce que ce module réimplémente.

## Le rejeu, et ce qui le rend plus contraint qu'ailleurs

Une phase de colline ne persiste **ni ses défis, ni ses manches, ni l'ordre courant de la
colline** :
elle rejoue tout des duels validés. L'ordre initial est le classement amont (référentiel §10.1,
« version de journée »), et chaque manche close l'échange par `appliquer_manche`.

⚠️ **Ne rien persister de l'ordre est une décision, et c'est la même qu'ADR-0090 §5** (« l'avancement
se dérive à la lecture »). Persister la colline aurait donné **deux** sources pour une même vérité —
l'ordre stocké et l'ordre rejouable — qui divergent à la première correction de score. Le rejeu est
reproductible parce que `defis_de_la_manche` et `appliquer_manche` sont déterministes à donnée
constante (règle 9) : aucun aléa, aucune horloge.

⚠️ **Le rejeu s'arrête à la première manche incomplète, et ici ce n'est pas une précaution mais une
nécessité de fond.** Chez le suisse, apparier par-dessus une ronde ouverte fausserait le bye ; ici,
c'est l'**ordre de la colline lui-même** qui n'existe pas encore — chaque défi non tranché est un
échange de positions en suspens, et les défis de la manche suivante se calculent sur ces positions.
Apparier par-dessus ne donnerait pas un appariement approximatif : il en donnerait un **faux**, qui
changerait sous les yeux du juge à chaque validation. L'état rendu le **dit** (`close`), ce qui
permet à l'écran de nommer l'attente au lieu d'afficher un bouton inerte.

## Personne n'a de bye, mais tout le monde se repose

Un système suisse donne un **bye** à effectif impair — un archer désigné, qui gagne d'office. Une
colline n'a pas de bye : elle a des archers **au repos**, qui ne marquent rien et ne bougent pas.
À portée 1 les extrémités se reposent une manche sur deux **quel que soit** l'effectif, et à portée
2 la distance tourne, donc le nombre de défis change d'une manche à l'autre. C'est ce qui rend
l'issue `EN_ATTENTE` ([ADR-0087](../../docs/adr/0087-une-attente-n-est-pas-une-indisponibilite.md))
indispensable ici, et non pas seulement utile : sans elle, la moitié du plateau passerait pour
« terminée » à chaque manche.
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
    PhasePasUneColline,
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
from domain.classement_de_colline import classement_de_colline
from domain.classement_de_tableau import ClassementSource
from domain.colline import (
    ConfigurationColline,
    DefiColline,
    IssueDefi,
    appliquer_manche,
    classement_colline,
    defis_de_la_manche,
    portee_maximale,
)
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
from domain.suivi_deroule import AvancementDePhase
from domain.tournoi import TournoiId


@dataclass(frozen=True)
class DefiDeLaManche:
    """Un défi d'une manche, prêt à l'affichage et à la saisie.

    `numero` est le `match_numero` de la table `duel` : un **compteur continu sur toute la phase**,
    manche après manche. C'est ce qui permet de porter les défis de toutes les manches sans table
    neuve — aucune migration, même parti que les poules et le suisse.

    ⚠️ **Un compteur, donc pas une position stable.** Si la population de la phase change après des
    tirs, les numéros glissent et les défis déjà tirés ne décrivent plus les mêmes duellistes.
    C'est `desynchronisee` qui le dit, et le tir est alors **masqué** plutôt que ré-attribué
    (ADR-0049 §4).

    `haut` est le **défié** (la position la plus haute de la colline, donc le mieux placé) et `bas`
    le **challenger**. L'orientation n'est pas cosmétique : c'est elle qui décide, à la lecture du
    vainqueur, s'il y a échange de positions ou non.
    """

    numero: int
    manche: int
    position_haute: int
    position_basse: int
    haut: Duelliste | None
    bas: Duelliste | None
    couloirs: tuple[tuple[int, str], tuple[int, str]] | None
    """Les deux couloirs du défi, **dérivés** du bloc de la phase — `None` si le plan n'est pas
    posé. Jamais persistés : c'est le bloc qui l'est (ADR-0083 §3)."""

    duel: Duel | None
    desynchronisee: bool
    bareme: BaremeDuel
    zones: tuple[ZoneScore, ...]
    defi: DefiColline
    """Le défi du **domaine**, conservé tel quel pour être rendu à `appliquer_manche`.

    Le reconstruire à partir des champs ci-dessus serait une seconde traduction des mêmes positions,
    donc une occasion de décaler le 1-indexé du 0-indexé — la seule subtilité que `DefiColline`
    signale dans sa docstring."""


@dataclass(frozen=True)
class MancheAffichee:
    """Une manche : ses défis, les archers au repos, et si elle est close.

    `close` est la seule information dont l'écran a besoin pour savoir s'il peut annoncer la manche
    suivante — et c'est aussi ce qui autorise le service à l'apparier.

    `au_repos` n'est pas décoratif : à portée 1 les deux extrémités ne tirent pas, et l'écran doit
    pouvoir le **dire** plutôt que de les laisser disparaître de la manche sans explication.
    """

    numero: int
    defis: tuple[DefiDeLaManche, ...]
    au_repos: tuple[Duelliste, ...]
    close: bool


@dataclass(frozen=True)
class RangColline:
    """Une position de la colline — le classement, qui **est** l'état courant du format.

    Aucun ex æquo n'est possible : deux participants n'occupent jamais la même position. C'est ce
    qui rend `classement_de_colline` si court, et ce qui fait qu'un prélèvement dans une colline
    n'est jamais retenu par le refus d'ADR-0081.
    """

    position: int
    duelliste: Duelliste


@dataclass(frozen=True)
class EtatColline:
    """La photo complète d'une phase de colline : ses manches jouées ou en cours, son ordre.

    `portee_maximale` est la **borne** que l'effectif du jour autorise — ce que l'atelier affiche en
    clair sous le champ de réglage, exactement comme `rondes_maximales` pour le suisse. Elle est
    rendue ici plutôt que calculée à l'écran : deux arithmétiques pour une même règle sont une
    divergence en attente, la leçon des dix filtres d'ADR-0083.

    Les deux nombres coexistent — `portee_de_defi` (ce que l'organisateur a réglé) et
    `portee_maximale` (ce que l'effectif du jour permet) — pour que l'atelier **montre** l'écart au
    lieu de le subir.
    """

    phase_id: PhaseId
    nb_manches: int
    portee_de_defi: int
    portee_maximale: int
    effectif: int
    manches: tuple[MancheAffichee, ...]
    classement: tuple[RangColline, ...]
    conflits: tuple[ConflitDeBloc, ...] = ()
    """Ce que la pose du plan n'a **pas** pu faire — **ou** le fait qu'elle n'a pas eu lieu.

    Même parti que les poules et le suisse : le placement **rapporte** son échec au lieu de tronquer
    en silence. L'organisateur doit voir à l'atelier que sa salle est trop petite, pas le découvrir
    le jour J.

    ⚠️ **Renseigné en lecture aussi**, et pas seulement après une pose — c'est le correctif de revue
    d'E05US030, repris ici d'emblée : rempli par la seule `regenerer_plan`, ce champ resterait vide
    sur la route de saisie, si bien que le message « le plan de cibles n'est pas posé » de l'écran
    scoreur serait une **branche morte**. En relecture, la seule raison connaissable est
    `NON_POSEE` — rien n'est persisté qui dise pourquoi un bloc manque."""


_PLAN_A_REPOSER = (ConflitDeBloc(1, RaisonConflitBloc.NON_POSEE),)
"""Le seul conflit qu'une **relecture** sait rapporter : le plan ne couvre pas le plateau."""


def _plan_suffisant(bloc: BlocDeCouloirs | None, effectif: int) -> bool:
    """Le bloc posé couvre-t-il **le plateau d'aujourd'hui** ?

    ⚠️ **Tester la seule présence du bloc ne suffit pas** : `regenerer_plan` dimensionne le bloc
    unique sur l'effectif **du jour de la pose**, et son numéro est toujours 1 — un archer inscrit
    après coup ne fait pas disparaître le bloc, il le rend **trop court**. Les défis en débordement
    perdraient alors leur cible sans que rien ne le signale. C'est le trou trouvé en revue sur le
    suisse (deux axes, sonde à l'appui), invisible par analogie avec les poules dont la croissance
    d'effectif ajoute des *groupes* que `_conflits_du_plan` voit.

    L'empreinte attendue est celle de `regenerer_plan` : `2 * (effectif // 2)` couloirs — c'est le
    nombre maximal d'archers qui tirent **en même temps**, atteint par la manche 1 à portée 1. Les
    manches suivantes en emploient moins (les archers au repos ne tirent pas), jamais plus.
    """
    if bloc is None:
        return False
    return len(bloc.places) >= 2 * (effectif // 2)


class ServiceColline:
    """Cas d'usage de la colline : consulter une phase, saisir ses défis, la classer."""

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
        # résolution de pavé (barème par arme, zones du blason). Même parti que `ServicePoules` et
        # `ServiceSuisse`, et le sens de dépendance est sûr : `saisie_duels` ne connaît pas la
        # colline.
        self._saisie_duels = saisie_duels

        # E05US033 : collaborateur **partagé** par les services qui écrivent un résultat
        # (`application.gel_de_pause`), inerte tant que le composition root n'y a rien branché.
        self._arrets = DeclencheurArrets()

    # --- Lecture ---------------------------------------------------------------------------------

    def etat(self, tournoi_id: TournoiId, phase_id: PhaseId) -> EtatColline:
        """La photo complète : manches rejouées, manche en cours, ordre de la colline.

        Lève `TournoiIntrouvable` / `PhaseIntrouvable` (404), `PhasePasUneColline` ou
        `PhasePasReglee` (409).
        """
        phase, participants = self._population(tournoi_id, phase_id)
        return self._photo(phase, participants)

    def avancement_de_phase(
        self, tournoi_id: TournoiId, phase_id: PhaseId
    ) -> AvancementDePhase | None:
        """Où en est cette colline — le port `LecteurAvancementDePhase` ([ADR-0090] §5).

        Le nombre de tours est le nombre de manches **réglé**, sans borne à appliquer : une colline
        n'a pas l'équivalent de `rondes_maximales`, puisque le ré-affrontement y est **légitime**
        (on rejoue son voisin, c'est le principe du format). Ce que l'effectif borne est la
        *portée*, pas le nombre de manches.

        Le tour courant est la première manche **non close**. `None` quand toutes le sont : plus
        rien ne tourne, même si la phase n'est pas clôturée.

        ⚠️ **Rend `None` — et non « zéro tour » — quand la borne de portée vaut 0**, c'est-à-dire
        sous deux tireurs. C'est le correctif de revue du suisse (axes B et C1), repris ici
        d'emblée : une phase réglée à l'atelier dont la source amont n'a encore classé personne est
        un cas **normal et durable**, et « zéro tour » est précisément ce que cette famille d'US
        existe pour supprimer. Ne rien savoir se dit `None`.

        [ADR-0090]: ../../docs/adr/0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md
        """
        etat = self.etat(tournoi_id, phase_id)
        if etat.portee_maximale == 0:
            return None
        ouverte = next((manche for manche in etat.manches if not manche.close), None)
        return AvancementDePhase(
            nb_tours=etat.nb_manches,
            tour_courant=ouverte.numero if ouverte is not None else None,
        )

    def classement_de_phase(
        self, tournoi_id: TournoiId, phase_id: PhaseId, resolveur: ResolveurClassement
    ) -> ClassementSource:
        """Le classement que cette phase **produit** — le port `LecteurClassementDePhase`.

        C'est ce qui rend une phase avale alimentable par une colline : jusqu'ici
        `ServiceSaisieDuels._classement_de_l_ordre` rendait `None` sur ce type, donc un prélèvement
        le visant restait **inerte** — la phase aval recevait tous les archers en lice, ce qui est
        plausible et faux.

        ⚠️ **4ᵉ occurrence du port unifié d'ADR-0084, et aucune duplication à écrire.** C'était la
        promesse faite en fondant les deux ports jumeaux ; elle est tenue.

        `rang_premier` est posé ici avec le **même** résolveur que celui qui a servi à prélever :
        deux bases différentes situeraient la population et le décalage dans deux espaces de rangs
        distincts, ce qui est exactement `DETTE-034`.
        """
        phase, participants = self._population(tournoi_id, phase_id, resolveur)
        photo = self._photo(phase, participants)
        lignes = {ligne.archer_id: ligne for ligne in participants}
        colline = tuple(
            (Participant.individuel(rang.duelliste.archer_id), rang.position)
            for rang in photo.classement
        )
        return replace(
            classement_de_colline(colline, lignes),
            rang_premier=tranche(phase, resolveur),
        )

    def _photo(self, phase: Phase, participants: list[LigneClassement]) -> EtatColline:
        """Le cœur d'`etat`, séparé des gardes : rejouer les manches, puis rendre la colline.

        Extrait pour que `classement_de_phase` réutilise exactement le même calcul sans repayer la
        résolution de population — et surtout sans la refaire avec un **autre** résolveur, ce qui
        rejouerait une colline différente pour la même phase.
        """
        phase_id = phase.id
        assert phase_id is not None, "`_population` a déjà refusé une phase sans identité."
        configuration = self._configuration(phase)
        lignes = {ligne.archer_id: ligne for ligne in participants}
        maximum = portee_maximale(len(participants))
        # Une phase encore vide est une photo **vide**, pas une erreur : elle se compose et se règle
        # avant que sa population existe. Sans cette porte, l'écran de saisie et toute phase avale
        # qui y prélève sortaient en 500 (le correctif que les poules ont dû faire en revue).
        #
        # `maximum == 0` couvre l'effectif 0 **et** l'effectif 1 : dans les deux cas aucun défi
        # n'est appariable, et `defis_de_la_manche` lèverait.
        if maximum == 0:
            return EtatColline(
                phase_id=phase_id,
                nb_manches=configuration.nb_manches,
                portee_de_defi=configuration.portee_de_defi,
                portee_maximale=0,
                effectif=len(participants),
                manches=(),
                classement=(),
            )
        tireurs = [Participant.individuel(ligne.archer_id) for ligne in participants]
        # ⚠️ **On borne ici, on ne lève pas** — la leçon du suisse, où l'inverse a été un bloquant
        # de revue reproduit par trois axes.
        #
        # `EtapeDeroule._verifier_portee_de_defi` ne vérifie la borne que si l'effectif est
        # **déclaré**, régime licite et testé. Une phase réglée à portée 3 et jouée à 3 archers
        # ferait donc lever `defis_de_la_manche` (`ConfigurationCollineInvalide`, une
        # `DomainError`) dès la première manche, ce qui remonterait en **422 sur le palmarès
        # public, son PDF et le panneau de routage**. Un écran qui refuse de s'ouvrir vaut moins
        # qu'un écran qui montre la borne.
        jouable = replace(configuration, portee_de_defi=min(configuration.portee_de_defi, maximum))
        # Un **seul** bloc pour toute la phase, comme le suisse : une manche apparie sur le plateau
        # entier, il n'y a pas de groupes à distinguer. Le numéro 1 est celui que `placer_les_blocs`
        # attribue.
        bloc = next(iter(self._placements.par_phase(phase_id)), None)
        manches, ordre = self._rejouer(phase_id, tireurs, jouable, lignes, bloc)
        return EtatColline(
            phase_id=phase_id,
            nb_manches=configuration.nb_manches,
            portee_de_defi=configuration.portee_de_defi,
            portee_maximale=maximum,
            effectif=len(tireurs),
            manches=manches,
            classement=tuple(
                RangColline(position=position, duelliste=self._duelliste(participant, lignes))
                for participant, position in classement_colline(ordre)
            ),
            # ⚠️ **Le manque se rapporte à la LECTURE**, pas seulement après une pose : voir la
            # docstring de `EtatColline.conflits`. On **relaie** le manque, on ne le comble pas —
            # poser le bloc ici reviendrait à écrire un plan là où l'appelant croit qu'on ne fait
            # que lire (ADR-0083 §3).
            conflits=() if _plan_suffisant(bloc, len(tireurs)) else _PLAN_A_REPOSER,
        )

    def _rejouer(
        self,
        phase_id: PhaseId,
        tireurs: list[Participant],
        configuration: ConfigurationColline,
        lignes: dict[int, LigneClassement],
        bloc: BlocDeCouloirs | None,
    ) -> tuple[tuple[MancheAffichee, ...], tuple[Participant, ...]]:
        """Rejoue les manches des duels validés, et **s'arrête à la première manche incomplète**.

        Rend les manches affichables **et** l'ordre courant de la colline — les deux sont produits
        par le même parcours, et les séparer en deux méthodes ferait rejouer la phase deux fois.

        ⚠️ **L'arrêt est structurel, pas prudentiel.** Les défis de la manche `n+1` se calculent sur
        les **positions** issues de la manche `n` : tant qu'un défi n'est pas tranché, ces positions
        n'existent pas. Apparier par-dessus ne donnerait pas un appariement approximatif mais un
        appariement **faux**, qui changerait à chaque validation.

        ⚠️ **Le compteur de numéros court sur toute la phase**, manche après manche, et il ne se
        recale jamais : c'est ce qui permet à `(phase_id, match_numero)` de porter les défis de
        toutes les manches sans table neuve.
        """
        manches: list[MancheAffichee] = []
        ordre: tuple[Participant, ...] = tuple(tireurs)
        numero = 0
        for index in range(configuration.nb_manches):
            defis_domaine = defis_de_la_manche(ordre, index + 1, configuration)
            defis: list[DefiDeLaManche] = []
            issues: list[IssueDefi] = []
            close = True
            engages: set[int] = set()
            # La position **dans la manche** décide des couloirs, et se recompte à chaque manche :
            # une position cumulée ferait glisser la phase d'un cran par manche et déborder de son
            # bloc.
            for position, defi_domaine in enumerate(defis_domaine):
                numero += 1
                defi = self._defi(numero, index + 1, defi_domaine, phase_id, lignes, bloc, position)
                defis.append(defi)
                engages.add(defi_domaine.defie.ref_id)
                engages.add(defi_domaine.challenger.ref_id)
                issue = _issue_de(defi)
                if issue is None:
                    close = False
                else:
                    issues.append(issue)
            manches.append(
                MancheAffichee(
                    numero=index + 1,
                    defis=tuple(defis),
                    au_repos=tuple(
                        self._duelliste(participant, lignes)
                        for participant in ordre
                        if participant.ref_id not in engages
                    ),
                    close=close,
                )
            )
            if not close:
                break
            ordre = appliquer_manche(ordre, issues)
        return tuple(manches), ordre

    def _defi(
        self,
        numero: int,
        manche: int,
        defi: DefiColline,
        phase_id: PhaseId,
        lignes: dict[int, LigneClassement],
        bloc: BlocDeCouloirs | None,
        position: int,
    ) -> DefiDeLaManche:
        """Assemble un défi : ses adversaires résolus, son pavé, son tir.

        Le pavé est résolu par **le même code** que celui d'un duel de tableau
        (`ServiceSaisieDuels.bareme_de` / `zones_de`) : un défi *est* un duel ordinaire, et le même
        archer ne peut pas tirer en sets d'un côté et en cumul de l'autre.
        """
        haut = defi.defie
        bas = defi.challenger
        bareme = self._saisie_duels.bareme_de(haut, lignes)
        charge = self._duels.charger(phase_id, numero, bareme=bareme)
        # ⚠️ **L'ancrage d'ADR-0049 §4.** Un tir dont les duellistes enregistrés divergent des
        # adversaires recalculés est **masqué**, jamais ré-attribué : le défi s'affiche non tiré
        # plutôt que de prêter un score au mauvais couple.
        concorde = charge is not None and (charge.participant_haut, charge.participant_bas) == (
            haut,
            bas,
        )
        return DefiDeLaManche(
            numero=numero,
            manche=manche,
            position_haute=defi.position_haute,
            position_basse=defi.position_basse,
            haut=self._duelliste(haut, lignes),
            bas=self._duelliste(bas, lignes),
            couloirs=couloirs_de_la_paire(bloc, position),
            duel=charge if concorde else None,
            # Masquer ne suffit pas : sans ce drapeau le défi s'afficherait « à tirer »,
            # indiscernable d'un défi jamais commencé, et le scoreur se prendrait un 409 sur un
            # écran qui l'invitait à saisir (leçon de la revue d'E05US023).
            desynchronisee=charge is not None and not concorde,
            bareme=bareme,
            zones=self._saisie_duels.zones_de(haut, lignes),
            defi=defi,
        )

    def _duelliste(self, participant: Participant, lignes: dict[int, LigneClassement]) -> Duelliste:
        """Le duelliste résolu — nom et prénom depuis le classement."""
        ligne = lignes.get(participant.ref_id)
        if ligne is None:
            return Duelliste(archer_id=participant.ref_id, nom="?", prenom="")
        return Duelliste(archer_id=ligne.archer_id, nom=ligne.nom, prenom=ligne.prenom)

    def regenerer_plan(self, tournoi_id: TournoiId, phase_id: PhaseId) -> EtatColline:
        """Pose la phase sur la salle et **remplace** le plan existant.

        Un seul bloc, comme le suisse : une manche apparie sur **tout le plateau**, il n'y a pas de
        groupes à séparer. L'empreinte est `2 * (effectif // 2)` — deux couloirs par défi, au
        maximum de défis simultanés, atteint par la manche 1 à portée 1.

        ⚠️ **Et à effectif pair, une manche peut quand même laisser des couloirs vides** : dès la
        manche 2, les extrémités se reposent. C'est voulu — dimensionner sur la manche la plus
        chargée est la seule façon de n'avoir jamais à **redimensionner en cours de phase**, ce qui
        déplacerait les archers déjà installés.

        Le geste est volontairement grossier — on repose tout. Reposer après un changement
        d'effectif est sûr, à ceci près que les tirs déjà saisis peuvent se retrouver rattachés à
        d'autres adversaires : c'est ce qu'ADR-0049 §4 détecte, et ce que `desynchronisee` dit.
        """
        phase, participants = self._population(tournoi_id, phase_id)
        # ⚠️ **Toutes les gardes avant la moindre écriture** (correctif de revue du suisse, repris
        # ici d'emblée) : une phase non réglée ferait lever `PhasePasReglee` **après** que le plan
        # ait été écrit, et l'organisateur recevrait un 409 sur un geste qui a bien eu lieu.
        self._configuration(phase)
        gabarit = self._gabarits.par_tournoi(tournoi_id)
        if gabarit is None:
            raise GabaritDuTournoiAbsent(
                f"Aucun gabarit de salle n'est appliqué au tournoi {tournoi_id}."
            )
        plan = placer_les_blocs([2 * (len(participants) // 2)], gabarit)
        self._placements.definir_plan(phase_id, plan.blocs)
        # ⚠️ Les conflits **de la pose** l'emportent sur le silence de la relecture : la lecture ne
        # sait pas *pourquoi* un bloc manque, alors qu'ici on vient de l'apprendre.
        # `_photo` plutôt qu'`etat()` : la population vient d'être résolue, la re-résoudre paierait
        # deux fois la chaîne amont sur le thread du writer unique (`DETTE-031`).
        return replace(self._photo(phase, participants), conflits=plan.conflits)

    def rencontres_a_tirer(self, tournoi_id: TournoiId, phase_id: PhaseId) -> RencontresARouter:
        """Les défis encore à tirer — le port `LecteurRencontresARouter`.

        Dans l'ordre du déroulé, donc manche par manche : le **premier** d'un archer est celui qui
        vient. Les manches ultérieures n'existent même pas tant que la courante n'est pas close,
        donc il n'y a rien à promettre au-delà.

        Un défi **désynchronisé** est écarté : son tir est masqué et son écriture refusée,
        l'annoncer enverrait un archer sur une cible où il ne peut rien saisir.

        ⚠️ **`epuisee` est le champ qui empêche de mentir**, et son absence a été un bloquant de
        revue sur le suisse. Ici l'enjeu est **plus grand encore** : une colline ne montre que sa
        manche courante, et à portée 1 les deux extrémités s'y reposent — sans ce champ, elles
        passeraient pour « terminées » sur un panneau public à chaque manche, et non pas seulement
        dans le cas limite d'un effectif impair. La phase n'est épuisée que si **toutes** les
        manches réglées sont closes.
        """
        etat = self.etat(tournoi_id, phase_id)
        epuisee = len(etat.manches) >= etat.nb_manches and all(m.close for m in etat.manches)
        return RencontresARouter(
            participants=tuple(rang.duelliste.archer_id for rang in etat.classement),
            epuisee=epuisee,
            rencontres=tuple(
                RencontreARouter(
                    numero=defi.numero,
                    tour=manche.numero,
                    libelle=f"Manche {manche.numero}",
                    haut=defi.haut.archer_id,
                    bas=defi.bas.archer_id,
                    couloirs=defi.couloirs,
                )
                for manche in etat.manches
                for defi in manche.defis
                if defi.haut is not None
                and defi.bas is not None
                and not defi.desynchronisee
                and (defi.duel is None or not defi.duel.verrouille)
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

        ⚠️ **L'ordre de cette liste est l'ordre initial de la colline**, et ce n'est pas un détail
        d'implémentation : le référentiel §10.1 le pose comme la « version de journée » du format —
        l'ordre initial est le classement source, par opposition au classement permanent de club
        que la règle d'origine décrit et qui ne se modélise pas en `Phase`.

        Générique depuis ADR-0068/E05US024 : `preleves` lit chaque source dans le classement de
        **sa** phase, en remontant la chaîne. Une colline sans source déclarée est donc alimentée
        par le classement du départ, comme un tableau de tête.

        `resolveur` est fourni quand l'appel vient **d'en haut** (une phase aval qui remonte la
        chaîne par `LecteurClassementDePhase`) : on réutilise alors son cache et sa chaîne de phases
        visitées plutôt que d'en ouvrir un second (`DETTE-031`, et la détection de cycle avec).
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        phase = phase_du_tournoi(self._phases, tournoi_id, phase_id)
        if phase is None:
            raise PhaseIntrouvable(f"Aucune phase {phase_id} dans le tournoi {tournoi_id}.")
        if phase.type is not TypePhase.COLLINE:
            raise PhasePasUneColline(f"La phase {phase_id} n'est pas une colline.")
        classement = self._classements.pour_depart(phase.depart_id)
        participants = preleves(
            phase,
            classement,
            resolveur
            if resolveur is not None
            else self._saisie_duels.resolveur_de_classement(tournoi_id, phase.depart_id),
        )
        return phase, participants

    def _configuration(self, phase: Phase) -> ConfigurationColline:
        """Le réglage de la phase, ou `PhasePasReglee` (409).

        ⚠️ **Aucune vérification de la borne ici.** Elle est portée par `EtapeDeroule`, à la
        composition, là où l'effectif **déclaré** est connu. La refaire sur l'effectif *réel* du
        jour ferait tomber la lecture d'une phase que l'atelier a acceptée — `_photo` **borne** à la
        place. C'est `defis_de_la_manche` qui reste le dernier rempart, et il lève une `DomainError`
        que la frontière traduit.
        """
        if phase.colline is None:
            raise PhasePasReglee(
                f"La phase {phase.id} n'a pas encore de nombre de manches ni de portée de défi : "
                "réglez-la à l'atelier avant de la faire jouer."
            )
        return phase.colline

    # --- Saisie d'un défi (via la file) ----------------------------------------------------------
    #
    # ⚠️ Mêmes trois méthodes que `ServicePoules` et `ServiceSuisse`, et le même écart avec
    # `ServiceSaisieDuels` : l'agrégat, le pavé et la table sont partagés, seule la **navigation**
    # diffère (ADR-0083 §7).

    def saisir_manche(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        numero: int,
        manche: int,
        valeurs_haut: tuple[ZoneScore, ...],
        valeurs_bas: tuple[ZoneScore, ...],
    ) -> DefiDeLaManche:
        """Saisit une manche d'un défi — même agrégat, même contrôle qu'un duel de tableau.

        ⚠️ **Deux sens du mot « manche » se croisent ici, et c'est inévitable.** Celui du format
        (la manche de la colline, `DefiDeLaManche.manche`) et celui du duel FFTA (la manche de
        sets, l'argument `manche`). Le second est celui de l'agrégat `Duel` et se retrouve à
        l'identique dans les quatre services ; le premier est le tour du format. Les renommer
        rendrait ce service incohérent avec ses trois jumeaux, ce qui coûterait plus cher que
        l'homonymie — mais elle est signalée ici et sur `MancheAffichee`.
        """
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
    ) -> DefiDeLaManche:
        """Saisit le tir de barrage **interne** à un défi nul (§8.2, E04US013).

        ⚠️ **Exigé, et ici la raison est plus forte qu'ailleurs.** `Duel.valider` refuse déjà un duel
        non tranché (`DuelIncomplet`) dans les quatre formats, mais la colline ne *pourrait* pas
        s'en accommoder même si l'agrégat le permettait : `appliquer_manche` exige un vainqueur qui
        soit l'un des deux engagés, parce qu'un défi décide d'un **échange de positions**. Un nul
        n'a pas de traduction dans ce format — il n'existe pas d'état « les deux restent où ils
        sont » qui soit distinct de « le défié a gagné », et les confondre donnerait au défié une
        victoire qu'il n'a pas obtenue.
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
    ) -> DefiDeLaManche:
        """Valide le tir d'un défi — c'est ce qui le fait entrer dans l'ordre de la colline.

        ⚠️ **La validation est le geste qui fait bouger les positions**, donc celui qui clôt une
        manche et autorise l'appariement de la suivante. Un tir non validé laisse la manche ouverte
        et la colline inchangée : c'est voulu, et c'est la règle de la reconstruction d'un tableau,
        qui ne rejoue lui aussi que les duels validés.
        """
        # E05US033 — **garde et signalement sont ici, sur `valider`, et non dans `_ecrire`** :
        # `_ecrire` est le tronc commun des **trois** écritures, et y poser la garde gelait aussi la
        # **rectification** d'un défi engagé pendant la pause — le cul-de-sac que le contrat de
        # `refuser_si_en_pause` interdit. Le CA est net : la pause gèle ce qui *avance*, jamais ce
        # qui *répare*.
        #
        # Y poser le **signalement** ferait en outre payer la recomposition intégrale du créneau à
        # chaque manche et chaque barrage, sur le thread du writer unique (règle 7, `DETTE-031`),
        # pour un résultat structurellement identique : un tour n'avance que sur des défis
        # **validés**.
        phase = phase_du_tournoi(self._phases, tournoi_id, phase_id)
        if phase is not None:
            refuser_si_en_pause(phase)
        defi = self._ecrire(
            tournoi_id, phase_id, numero, lambda duel, _bareme, _zones: duel.valider(scoreur)
        )
        if phase is not None:
            self._arrets.signaler(phase.depart_id)
        return defi

    def brancher_evaluateur_arrets(self, evaluateur: EvaluateurArrets) -> None:
        """Dit à qui signaler qu'un résultat vient d'être validé (E05US033, ADR-0091).

        ⚠️ **Ce branchement a manqué à la première livraison du suisse**, et c'était un bloquant :
        sans lui, un arrêt programmé sur ce format ne se déclenche **jamais**, la phase tournant
        seule sans qu'aucune validation atteigne le déclencheur. La colline est arrêtable dès cette
        US (`avancement_lisible` → `TYPES_ARRETABLES`), donc l'oubli aurait le même effet ici.
        """
        self._arrets.brancher(evaluateur)

    def _ecrire(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        numero: int,
        appliquer: Callable[[Duel, BaremeDuel, tuple[ZoneScore, ...]], Duel],
    ) -> DefiDeLaManche:
        """Le tronc commun des trois écritures : retrouver le défi, appliquer, persister.

        `# DETTE-031` — appelle `etat()` à **chaque** manche, barrage et validation, donc rejoue la
        reconstruction complète sur le thread du writer unique. Même régime que `ServicePoules` et
        `ServiceSuisse`, et la dette est élargie d'autant.

        Le défi est retrouvé **par recomposition**, jamais par une lecture de la table `duel` :
        c'est ce qui garantit que le tir écrit porte les deux adversaires que l'appariement du
        moment désigne. Écrire depuis la ligne persistée se fierait à un `match_numero` qui a pu
        changer de sens — précisément ce que l'ancrage d'ADR-0049 §4 sert à détecter.

        ⚠️ **Un défi désynchronisé refuse l'écriture** au lieu de reconstruire un duel vierge. C'est
        le correctif que les poules ont dû faire en revue : le `or Duel.vide(...)` remplaçait la
        ligne, un tir validé disparaissait sans trace, et le verrou de validation sautait avec.
        """
        defi = self._trouver(tournoi_id, phase_id, numero)
        if defi.desynchronisee:
            raise DuelDesynchronise(
                f"Le tir du défi {numero} oppose d'autres duellistes : la population de la phase a "
                "changé depuis. Rétablissez-la avant de saisir."
            )
        assert (
            defi.haut is not None and defi.bas is not None
        ), "`_rejouer` n'apparie que des défis à deux adversaires résolus."
        haut = Participant.individuel(defi.haut.archer_id)
        bas = Participant.individuel(defi.bas.archer_id)
        # Les zones sont relues en **strict** sur ce chemin d'écriture : un blason indéterminable
        # doit lever plutôt que produire un pavé vide, sinon on enregistrerait un score dont on ne
        # sait pas s'il est légal (même exigence qu'E04US002 et que les trois jumeaux).
        zones = self._saisie_duels.zones_strictes(haut, self._lignes(phase_id))
        courant = defi.duel or Duel.vide(defi.bareme, haut, bas)
        duel = appliquer(courant, defi.bareme, zones)
        self._duels.enregistrer(phase_id, numero, duel)
        return replace(defi, duel=duel)

    def _trouver(self, tournoi_id: TournoiId, phase_id: PhaseId, numero: int) -> DefiDeLaManche:
        """Le défi de ce numéro dans l'état rejoué, ou `RencontreIntrouvable` (404).

        Un défi d'une manche **pas encore appariée** est introuvable, et c'est exact : il n'existe
        pas tant que la manche précédente n'est pas close — les positions qu'il opposerait ne sont
        pas encore fixées.
        """
        etat = self.etat(tournoi_id, phase_id)
        for manche in etat.manches:
            for defi in manche.defis:
                if defi.numero == numero:
                    return defi
        raise RencontreIntrouvable(
            f"Aucun défi {numero} dans la phase {phase_id} : soit il n'existe pas, soit sa manche "
            "n'est pas encore appariée — la précédente doit être close d'abord."
        )

    def _lignes(self, phase_id: PhaseId) -> dict[int, LigneClassement]:
        """Le classement du départ de cette phase, indexé par archer — pour résoudre le blason."""
        phase = self._phases.par_id(phase_id)
        assert phase is not None, "`etat` a déjà refusé une phase inconnue."
        return {
            ligne.archer_id: ligne
            for ligne in self._classements.pour_depart(phase.depart_id).lignes
        }


def _issue_de(defi: DefiDeLaManche) -> IssueDefi | None:
    """Traduit un tir **validé** en issue consommable par `appliquer_manche`.

    ⚠️ **Seuls les duels validés comptent.** Un tir en cours de saisie ferait bouger la colline à
    chaque flèche, et surtout l'appariement de la manche suivante changerait sous les yeux du juge.
    Même parti que la reconstruction d'un tableau, les poules et le suisse.

    ⚠️ **Aucune branche « nul »**, à la différence du suisse dont le moteur sait représenter un
    match nul : `appliquer_manche` exige un vainqueur qui soit l'un des deux engagés, parce qu'un
    défi décide d'un **échange de positions** et qu'il n'existe pas d'état intermédiaire. Un duel
    validé a donc toujours un vainqueur (`Duel.valider` refuse l'inverse) ; l'assertion le dit
    plutôt que de rendre `None`, qui laisserait la manche indéfiniment ouverte sans que rien
    l'explique.
    """
    duel = defi.duel
    if duel is None or not duel.verrouille:
        return None
    vainqueur = duel.resultat.vainqueur
    assert vainqueur is not None, "`Duel.valider` refuse un duel non tranché (`DuelIncomplet`)."
    return IssueDefi(
        defi=defi.defi,
        vainqueur=defi.defi.defie if vainqueur is Cote.HAUT else defi.defi.challenger,
    )


__all__ = [
    "DefiDeLaManche",
    "EtatColline",
    "MancheAffichee",
    "RangColline",
    "ServiceColline",
]
