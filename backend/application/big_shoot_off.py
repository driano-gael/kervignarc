"""Service **Big Shoot Off** — la structure se recalcule, le tir se persiste (ADR-0084).

Persisté : les volées, dans `serie`/`volee`. Recalculé : qui sort, à quelle manche, à quel rang.

⚠️ **Aucun chemin de correction n'existe** (`DETTE-061`) : une volée validée est définitive, et
l'élimination qu'elle a produite avec elle. Le rejeu est correct — c'est le geste d'entrée qui
manque, et la fiche de recette a cru la capacité livrée.
"""

# DETTE-028 — moteur de format branché tardivement : la capacité précède son appelant.

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from application.classements import ServiceClassement
from application.erreurs import (
    ArcherDejaSorti,
    ArcherHorsBigShootOff,
    MancheIntrouvable,
    PhaseIntrouvable,
    PhasePasReglee,
    PhasePasUnBigShootOff,
    TournoiIntrouvable,
)
from application.gel_de_pause import (
    DeclencheurArrets,
    EvaluateurArrets,
    refuser_si_en_pause,
)
from application.portee import phase_du_tournoi
from application.prelevement import ResolveurClassement, preleves, tranche
from application.saisie_duels import Duelliste, ServiceSaisieDuels
from domain.barrage import PorteeBarrage
from domain.big_shoot_off import (
    ConfigurationBigShootOff,
    EtatBigShootOff,
    demarrer,
    eliminer_apres_barrage,
    jouer_manche,
)
from domain.blason import ZoneScore
from domain.classement import Classement, LigneClassement
from domain.classement_de_tableau import ClassementSource
from domain.contrat_phase import TypePhase
from domain.grain_validation import GrainValidation
from domain.participant import GenreParticipant, Participant
from domain.phase import Phase, PhaseId
from domain.ports import (
    BarrageRepository,
    PhaseRepository,
    SerieRepository,
    TournoiRepository,
)
from domain.serie import Serie
from domain.suivi_deroule import AvancementDePhase
from domain.tournoi import TournoiId


@dataclass(frozen=True)
class ProjectionBigShootOff:
    """Ce que la liste de sortants donne sur l'effectif **réel** — le CA « la répartition montrée ».

    Jumeau de `RepartitionPoules` : l'organisateur doit voir ce que son réglage produit **avant**
    de composer. `paliers` porte ce qu'il reste après chaque manche jouable ; `manches_ignorees`
    compte les cases qui ne se joueront pas faute d'effectif. ⚠️ Ce n'est pas une erreur mais le
    prix de « on joue tant que la manche est possible » — l'écran doit le **dire**, sinon
    l'organisateur croit jouer une liste qu'il ne joue pas.
    """

    effectif: int
    eliminations: tuple[int, ...]
    paliers: tuple[int, ...]
    volees: int
    fleches_par_volee: int
    """Le format du tir, porté par la projection parce que **l'écran de saisie en a besoin**.

    Sans lui, la ligne de tir ne sait pas combien de champs de flèche afficher : elle devrait le
    deviner, et un défaut en dur y serait faux dès qu'un club règle autre chose que 3."""

    @property
    def restants(self) -> int:
        return self.paliers[-1] if self.paliers else self.effectif

    @property
    def manches_jouables(self) -> int:
        return len(self.paliers)

    @property
    def manches_ignorees(self) -> int:
        return len(self.eliminations) - len(self.paliers)


@dataclass(frozen=True)
class TireurAffiche:
    """Un finaliste : son identité, son sort, et ce qu'il a marqué manche par manche.

    `rang` vaut `None` tant que l'archer est **en lice** : un rang annoncé avant la sortie serait un
    faux départ (même parti que `RoutageArcher`, E07US008). `scores` porte le score de chaque manche
    **validée**, dans l'ordre — c'est ce que l'écran affiche en colonnes.
    """

    archer_id: int
    nom: str
    prenom: str
    en_lice: bool
    rang: int | None
    scores: tuple[int, ...]
    prochaine_volee: int | None = None
    """La **prochaine volée à saisir** pour cet archer, ou `None` s'il n'y a rien à tirer.

    ⚠️ **Ferme un cas injouable** : la manche *m* occupe les volées `(m-1)·V+1 … m·V`, et sans ce
    champ l'écran envoyait toujours la première de la manche. Juste par accident à `V = 1`, seule
    valeur testée ; dès `V = 2` la volée 2 n'était jamais saisissable et `Serie.valider` refusait
    le lot (`RienAValider`). Le calcul appartient au serveur, qui tient la série et sait ce qui est
    validé — le front ne re-dérive pas une numérotation qu'il ne persiste pas.
    """


@dataclass(frozen=True)
class MancheAffichee:
    """Une manche : son rang, combien elle élimine, où en est sa saisie.

    `complete` dit que **tous** les archers en lice à cette manche ont leurs V volées validées —
    c'est la condition pour que le moteur la joue. `jouee` dit qu'elle l'a été.
    """

    numero: int
    elimine: int
    volees: tuple[int, ...]
    complete: bool
    jouee: bool


@dataclass(frozen=True)
class EtatBigShootOffAffiche:
    """La photo d'un Big Shoot Off : sa projection, ses tireurs, ses manches, son barrage éventuel.

    `barrage_entre` et `places_au_barrage` relaient l'égalité qui **suspend** la phase. L'écran doit
    la montrer : sans elle, le scoreur verrait une manche saisie et validée qui n'élimine personne,
    sans comprendre pourquoi la suivante refuse de s'ouvrir.
    """

    phase_id: PhaseId
    projection: ProjectionBigShootOff
    tireurs: tuple[TireurAffiche, ...]
    manches: tuple[MancheAffichee, ...]
    termine: bool
    barrage_entre: tuple[Duelliste, ...] = ()
    places_au_barrage: int = 0


class LecteurEtatBigShootOff(Protocol):
    """Port étroit : « où en est ce Big Shoot Off ? » — réalisé par `ServiceBigShootOff`.

    Consommé par `ServicePalmares`, qui a besoin des rangs décernés sans connaître les volées. ⚠️
    **Ce port n'est pas branché tardivement**, contrairement à `LecteurClassementDePhase` : il n'y
    a **pas de cycle** ici. Le branchement tardif existe pour en casser un ; le reproduire sans
    cycle échangerait un contrôle du compilateur contre un test de câblage.
    """

    def etat(self, tournoi_id: TournoiId, phase_id: PhaseId) -> EtatBigShootOffAffiche:
        """La photo de ce Big Shoot Off : qui est sorti, à quel rang."""
        ...


class ServiceBigShootOff:
    """Cas d'usage du Big Shoot Off : consulter, saisir une volée, valider une manche.

    **Ce qui est partagé l'est réellement** : l'agrégat `Serie`, les tables `serie`/`volee`, la
    résolution de population. Écrire le tir autrement créerait une seconde façon de saisir des
    volées. **Ce qui diffère est le décor** : l'archer tire une **volée collective**, et c'est le
    classement de la manche qui décide — pas un adversaire (`VOLEE_COLLECTIVE`, ADR-0083 §2).
    """

    def __init__(
        self,
        tournois: TournoiRepository,
        phases: PhaseRepository,
        series: SerieRepository,
        barrages: BarrageRepository,
        classements: ServiceClassement,
        saisie_duels: ServiceSaisieDuels,
    ) -> None:
        self._tournois = tournois
        self._phases = phases
        self._series = series
        self._barrages = barrages
        self._classements = classements
        # ⚠️ **Pas pour saisir des duels** — uniquement pour emprunter sa résolution de classement
        # amont (`resolveur_de_classement`) et son pavé de zones. Même parti que `ServicePoules` et
        # `ServicePlacementDuels`, et le sens de dépendance est sûr : `saisie_duels` ne connaît pas
        # le Big Shoot Off. L'alternative — recopier le résolveur ici — est exactement ce
        # qu'`application/prelevement.py` existe pour empêcher.
        self._saisie_duels = saisie_duels

        # E05US033 : collaborateur **partagé** par les cinq services qui écrivent un résultat
        # (`application.gel_de_pause`), inerte tant que le composition root n'y a rien branché.
        self._arrets = DeclencheurArrets()

    # --- Lecture ---------------------------------------------------------------------------------

    def projection(self, tournoi_id: TournoiId, phase_id: PhaseId) -> ProjectionBigShootOff:
        """Ce que la liste de sortants donne sur l'effectif réel, **sans rien écrire**.

        Volontairement séparé d'`etat` : montrer la projection ne doit exiger ni tir ni gabarit de
        salle — sinon l'organisateur ne pourrait pas régler son Big Shoot Off avant d'avoir fait sa
        salle. Même découpe que `ServicePoules.repartition`, et pour la même raison.
        """
        phase, participants = self._population(tournoi_id, phase_id)
        # ⚠️ **Aucune garde de pause ici, et c'est le point** : `projection` est une **lecture** —
        # « ce que la liste de sortants donne sur l'effectif réel, sans rien écrire ». Un correctif
        # de 2ᵉ passe y avait posé le refus par erreur, sur le seul critère de la ressemblance des
        # deux premières lignes : l'organisateur ne pouvait plus consulter sa projection pendant une
        # pause, alors que c'est exactement le moment où il la regarde. Le gel est aux **écritures**
        # (`saisir_volee`, `valider_manche`), et nulle part ailleurs — ADR-0091 §6.
        return self._projection(phase, len(participants))

    def etat(self, tournoi_id: TournoiId, phase_id: PhaseId) -> EtatBigShootOffAffiche:
        """La photo complète : qui tire, qui est sorti, à quel rang, et ce qui bloque.

        `# DETTE-031` — l'état est **rejoué intégralement** à chaque lecture, chaîne de sources
        amont comprise. ⚠️ **Élargie par E05US031** : cette lecture n'était servie qu'à des
        scoreurs authentifiés, elle l'est désormais sur une route **ouverte**, montée par l'onglet
        public en autant d'exemplaires qu'il y a de spectateurs.
        """
        phase, participants = self._population(tournoi_id, phase_id)
        return self._photo(phase, participants)

    def avancement_de_phase(
        self, tournoi_id: TournoiId, phase_id: PhaseId
    ) -> AvancementDePhase | None:
        """Où en est ce Big Shoot Off — le port `LecteurAvancementDePhase` (ADR-0090 §5).

        Une manche est le tour de ce format ; le tour courant est la première manche **non jouée**,
        et `None` quand la phase est terminée même s'il reste une manche au programme (la liste
        s'écourte d'elle-même). ⚠️ **Un barrage suspend la phase, donc plus aucun tour ne tourne**
        : `_photo` porte déjà cette règle, et n'en reprendre que la moitié annonçait « Manche 3 »
        pendant que l'écran de saisie disait qu'il n'y avait rien à tirer.
        """
        etat = self.etat(tournoi_id, phase_id)
        if not etat.manches:
            return None
        ouverte = next((manche for manche in etat.manches if not manche.jouee), None)
        suspendue = bool(etat.barrage_entre)
        return AvancementDePhase(
            nb_tours=len(etat.manches),
            tour_courant=(None if etat.termine or suspendue or ouverte is None else ouverte.numero),
        )

    def classement_de_phase(
        self, tournoi_id: TournoiId, phase_id: PhaseId, resolveur: ResolveurClassement
    ) -> ClassementSource:
        """Le classement que ce Big Shoot Off **produit** — le port `LecteurClassementDePhase`.

        Sans lui, un prélèvement le visant restait **inerte** : l'aval recevait tous les archers en
        lice, plausible et faux. ⚠️ **Aucune plage indécise pour les rangs décernés** (ADR-0081) :
        ils sont **exacts**. En revanche le **partage du rang 1** entre rescapés est une vraie
        indécision, déclarée comme telle — sans quoi une phase avale prélevant « le rang 1 »
        emporterait cinq archers.
        """
        phase, participants = self._population(tournoi_id, phase_id, resolveur)
        photo = self._photo(phase, participants)
        lignes = {ligne.archer_id: ligne for ligne in participants}
        classees = [
            _avec_rang(lignes[tireur.archer_id], rang)
            for tireur in photo.tireurs
            if tireur.archer_id in lignes
            for rang in ((tireur.rang if tireur.rang is not None else 1),)
        ]
        classees.sort(key=lambda ligne: ligne.rang_scratch or 1)
        # Les rescapés partagent le rang 1 tant qu'ils sont en lice : c'est une **indécision**, au
        # sens exact d'ADR-0081, et la déclarer est ce qui fait refuser (et annoncer) un prélèvement
        # qui la couperait, au lieu de qualifier en silence sur un ordre d'affichage.
        en_lice = sum(1 for tireur in photo.tireurs if tireur.en_lice)
        indecises = ((1, en_lice),) if en_lice > 1 else ()
        return ClassementSource(
            classement=Classement(lignes=tuple(classees)),
            plages_indecises=indecises,
            rang_premier=tranche(phase, resolveur),
        )

    # --- Écriture (via la file) ------------------------------------------------------------------

    def brancher_evaluateur_arrets(self, evaluateur: EvaluateurArrets) -> None:
        """Dit à qui signaler qu'un résultat vient d'être validé (E05US033, ADR-0091).

        ⚠️ **Ce branchement manquait à la première livraison**, et c'était un bloquant : le
        déclencheur n'était appelé que depuis la qualification et l'élimination directe, si bien
        qu'un arrêt programmé sur ce format ne se déclenchait **jamais** — la phase tournant seule,
        aucune validation n'atteignait le déclencheur. Relevé par les quatre axes de revue.
        """
        self._arrets.brancher(evaluateur)

    def saisir_volee(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        archer_id: int,
        numero: int,
        valeurs: tuple[ZoneScore, ...],
        saisie_par: str | None = None,
    ) -> EtatBigShootOffAffiche:
        """Saisit une volée d'un finaliste — même agrégat et même pavé qu'une qualification.

        ⚠️ **On refuse d'écrire pour un archer qui n'est plus en lice**, et la garde n'est pas
        théorique : une tablette restée ouverte sur la manche 2 continue d'afficher un archer sorti
        à la manche 1 si l'élimination vient d'être calculée ailleurs. Sans ce refus, ses flèches
        entreraient dans une manche qu'il ne tire pas, et le classement de cette manche changerait
        pour tout le monde.
        """
        phase, participants = self._population(tournoi_id, phase_id)
        # E05US033 — **le gel d'un résultat neuf**, par symétrie avec la qualification. Une volée de
        # Big Shoot Off est un résultat neuf pour un archer : la doctrine de `refuser_si_en_pause`
        # la gèle. Ce qu'elle ne gèle pas, c'est la **poursuite d'une rencontre engagée** — un duel,
        # une manche de poule —, ce qui n'existe pas ici : le Big Shoot Off tire par feuille.
        refuser_si_en_pause(phase)
        configuration = self._configuration(phase)
        photo = self._photo(phase, participants)
        self._exiger_en_lice(photo, archer_id)
        self._exiger_manche_de_la_volee(photo, configuration, numero)
        serie = self._feuille(tournoi_id, phase, archer_id)
        zones = self._saisie_duels.zones_strictes(
            Participant.individuel(archer_id),
            {ligne.archer_id: ligne for ligne in participants},
        )
        self._series.enregistrer(
            serie.saisir_volee(
                numero,
                valeurs,
                zones_admises=zones,
                nb_fleches_par_volee=configuration.fleches_par_volee,
                nb_volees_bareme=_nb_volees(configuration),
                saisie_par=saisie_par,
            )
        )
        return self.etat(tournoi_id, phase_id)

    def valider_manche(
        self, tournoi_id: TournoiId, phase_id: PhaseId, archer_id: int, scoreur: str
    ) -> EtatBigShootOffAffiche:
        """Valide le lot de volées de la manche courante pour **un** archer.

        La validation reste **par archer** — c'est l'agrégat `Serie` qui se verrouille. C'est la
        *manche* qui se joue collectivement, pas la validation : le scoreur descend la ligne
        feuille par feuille, comme en qualification. Le grain est dérivé du réglage (DETTE-058).
        """
        phase, _participants = self._population(tournoi_id, phase_id)
        # E05US033 — **le gel**. Cette garde manquait à la première livraison : la pause restait
        # **cosmétique** sur ce format, l'archer lisait « en attente » pendant que le scoreur
        # continuait de valider. Relevé par les quatre axes de revue.
        refuser_si_en_pause(phase)
        configuration = self._configuration(phase)
        serie = self._feuille(tournoi_id, phase, archer_id)
        self._series.enregistrer(
            serie.valider(
                scoreur,
                grain=GrainValidation.toutes_les_n_volees(configuration.volees),
                nb_volees_bareme=_nb_volees(configuration),
            )
        )
        # E05US033 — **le signalement**, après l'écriture : une manche s'achève sur la validation de
        # la dernière feuille, et c'est ici que le déclencheur peut le constater.
        self._arrets.signaler(phase.depart_id)
        return self.etat(tournoi_id, phase_id)

    # --- Rouages ---------------------------------------------------------------------------------

    def _population(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        resolveur: ResolveurClassement | None = None,
    ) -> tuple[Phase, list[LigneClassement]]:
        """Les gardes, puis **qui entre dedans** — la 1ʳᵉ question du contrat (ADR-0083 §1).

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
        if phase.type is not TypePhase.BIG_SHOOT_OFF:
            raise PhasePasUnBigShootOff(f"La phase {phase_id} n'est pas un Big Shoot Off.")
        classement = self._classements.pour_depart(phase.depart_id)
        participants = preleves(
            phase,
            classement,
            resolveur
            if resolveur is not None
            else self._saisie_duels.resolveur_de_classement(tournoi_id, phase.depart_id),
        )
        return phase, participants

    def _configuration(self, phase: Phase) -> ConfigurationBigShootOff:
        """Le réglage de la phase, ou `PhasePasReglee` — la garde du jour J.

        Le type se choisit **avant** ses paramètres (brouillon d'ADR-0063), donc l'agrégat tolère
        `None` ; c'est ici, au moment de faire jouer, que l'absence devient un refus.
        """
        if phase.big_shoot_off is None:
            raise PhasePasReglee(
                f"La phase {phase.id} est un Big Shoot Off, mais son nombre de sortants n'est pas "
                "réglé : l'organisateur doit le fixer à l'atelier avant de faire tirer."
            )
        return phase.big_shoot_off

    def _photo(self, phase: Phase, participants: list[LigneClassement]) -> EtatBigShootOffAffiche:
        """Le cœur d'`etat`, séparé des gardes : **rejouer** la phase depuis les volées validées.

        Extrait pour que `classement_de_phase` réutilise exactement le même calcul sans repayer la
        résolution de population — et surtout sans la refaire avec un **autre** résolveur, ce qui
        composerait deux populations différentes pour la même phase.
        """
        phase_id = phase.id
        assert phase_id is not None, "`_population` a déjà refusé une phase sans identité."
        configuration = self._configuration(phase)
        projection = self._projection(phase, len(participants))
        if not participants:
            # Une phase encore vide est une photo **vide**, pas une erreur : elle se compose et se
            # règle avant que sa population existe (source amont qui ne prélève encore rien). Sans
            # cette porte, l'écran de saisie sortait en 500 — correctif appris d'E05US023.
            return EtatBigShootOffAffiche(
                phase_id=phase_id,
                projection=projection,
                tireurs=(),
                manches=(),
                termine=True,
            )
        lignes = {ligne.archer_id: ligne for ligne in participants}
        series = {
            ligne.archer_id: self._series.par_archer(phase_id, ligne.archer_id)
            for ligne in participants
        }
        etat, lices = self._rejouer(phase, configuration, participants, series)
        rangs = dict(etat.rangs)
        manches = self._manches(configuration, projection, etat, lices, series)
        # La manche que la salle tire **en ce moment** : la première non jouée. `None` quand la
        # phase est finie ou suspendue par un barrage — dans les deux cas il n'y a rien à saisir, et
        # `prochaine_volee` doit le dire au lieu de laisser l'écran proposer un pavé inopérant.
        courante = next((m.numero - 1 for m in manches if not m.jouee), None)
        if etat.barrage_en_cours:
            courante = None
        tireurs = tuple(
            TireurAffiche(
                archer_id=ligne.archer_id,
                nom=ligne.nom,
                prenom=ligne.prenom,
                en_lice=Participant.individuel(ligne.archer_id) in etat.en_lice,
                rang=rangs.get(Participant.individuel(ligne.archer_id)),
                scores=_scores_par_manche(series.get(ligne.archer_id), configuration),
                prochaine_volee=(
                    _prochaine_volee(series.get(ligne.archer_id), configuration, courante)
                    if Participant.individuel(ligne.archer_id) in etat.en_lice
                    else None
                ),
            )
            for ligne in participants
        )
        return EtatBigShootOffAffiche(
            phase_id=phase_id,
            projection=projection,
            tireurs=tireurs,
            manches=manches,
            termine=etat.est_termine,
            barrage_entre=tuple(
                duelliste
                for participant in etat.barrage_en_cours
                if (duelliste := self._duelliste(participant, lignes)) is not None
            ),
            places_au_barrage=etat.places_au_barrage,
        )

    def _rejouer(
        self,
        phase: Phase,
        configuration: ConfigurationBigShootOff,
        participants: list[LigneClassement],
        series: dict[int, Serie | None],
    ) -> tuple[EtatBigShootOff, tuple[tuple[int, ...], ...]]:
        """Rejoue le Big Shoot Off manche par manche depuis les volées **validées**.

        ⚠️ Un tir en cours de saisie ferait bouger l'élimination à chaque flèche. On s'arrête à la
        première manche **incomplète** : la compter comme un zéro éliminerait quelqu'un sur une
        donnée absente. Les **verdicts de barrage** déjà rendus sont appliqués au passage. La lice
        au début de chaque manche est capturée au fil du rejeu — la reconstituer après coup était
        faux dès qu'une manche sort plusieurs archers à rangs partagés.
        """
        etat = demarrer(
            [Participant.individuel(ligne.archer_id) for ligne in participants], configuration
        )
        verdicts = self._verdicts_de_barrage(phase)
        lices: list[tuple[int, ...]] = []
        while not etat.est_termine:
            lices.append(tuple(participant.ref_id for participant in etat.en_lice))
            scores = _scores_de_la_manche(etat, configuration, series)
            if scores is None:
                break
            issue = jouer_manche(etat, scores)
            # ⚠️ **Une manche peut demander plusieurs barrages successifs**, et le rejeu doit les
            # appliquer *tous* avant d'avancer. Le domaine ne départage qu'un groupe d'ex æquo à la
            # fois, donc `eliminer_apres_barrage` peut **re-suspendre** la même manche. N'appliquer
            # qu'un verdict puis reboucler faisait lever `ConfigurationBigShootOffInvalide` à
            # *chaque lecture* — écran de saisie, routage et palmarès tombaient définitivement. Le
            # cas est ordinaire dès que `departage_les_sortants` est réglé.
            while issue.barrage_entre:
                ordre = verdicts.get(frozenset(issue.barrage_entre))
                if ordre is None:
                    break
                issue = eliminer_apres_barrage(issue.etat, ordre)
            etat = issue.etat
            if issue.barrage_entre:
                # Un barrage n'a pas encore parlé : la phase s'arrête là, et l'écran le dit.
                break
        return etat, tuple(lices)

    def _verdicts_de_barrage(
        self, phase: Phase
    ) -> dict[frozenset[Participant], tuple[Participant, ...]]:
        """Les verdicts qu'un barrage de portée **Big Shoot Off** a rendus dans cette phase.

        Indexés par l'**ensemble** des ex æquo : c'est ce que le moteur nomme quand il suspend une
        manche. ⚠️ On lit `resultat()`, **jamais** `verdict()`, qui rend un ordre vide quand
        `rang_dispute is None` — le cas ici. ⚠️ L'ordre est **inversé** : `resultat.ordre` va du
        meilleur au moins bon, `eliminer_apres_barrage` attend le plus faible d'abord. Les barrages
        clos comptent ; un non résolu est ignoré, donc la manche reste suspendue.
        """
        verdicts: dict[frozenset[Participant], tuple[Participant, ...]] = {}
        for barrage in self._barrages.par_depart(phase.depart_id):
            if barrage.portee is not PorteeBarrage.BIG_SHOOT_OFF or barrage.phase_id != phase.id:
                continue
            resultat = barrage.resultat()
            if not resultat.ordre:
                continue
            verdicts[frozenset(resultat.ordre)] = tuple(reversed(resultat.ordre))
        return verdicts

    def _manches(
        self,
        configuration: ConfigurationBigShootOff,
        projection: ProjectionBigShootOff,
        etat: EtatBigShootOff,
        lices: tuple[tuple[int, ...], ...],
        series: dict[int, Serie | None],
    ) -> tuple[MancheAffichee, ...]:
        """Les manches **jouables** sur cet effectif, avec l'avancement de leur saisie.

        Seules les manches que la projection retient sont rendues : annoncer une manche qui ne se
        jouera pas ferait attendre au scoreur un tour qui n'arrivera jamais.
        """
        volees = configuration.volees
        affichees: list[MancheAffichee] = []
        for index in range(projection.manches_jouables):
            numeros = tuple(range(index * volees + 1, (index + 1) * volees + 1))
            # « Complète » se juge sur les archers **encore en lice à cette manche-là**, pas sur
            # tous les participants : un archer sorti à la manche 1 n'a pas à tirer la manche 2, et
            # exiger ses volées bloquerait la phase pour toujours.
            attendus = lices[index] if index < len(lices) else ()
            affichees.append(
                MancheAffichee(
                    numero=index + 1,
                    elimine=configuration.eliminations[index],
                    volees=numeros,
                    complete=all(
                        _volees_validees(series.get(archer_id), numeros) for archer_id in attendus
                    ),
                    jouee=index < etat.manche,
                )
            )
        return tuple(affichees)

    def _projection(self, phase: Phase, effectif: int) -> ProjectionBigShootOff:
        """La projection de la liste de sortants sur cet effectif — pure lecture."""
        configuration = self._configuration(phase)
        return ProjectionBigShootOff(
            effectif=effectif,
            eliminations=configuration.eliminations,
            paliers=configuration.paliers_pour(effectif),
            volees=configuration.volees,
            fleches_par_volee=configuration.fleches_par_volee,
        )

    def _feuille(self, tournoi_id: TournoiId, phase: Phase, archer_id: int) -> Serie:
        """La feuille de cet archer **dans cette phase**, ou une feuille vierge.

        ⚠️ **La clé de lecture est `(phase_id, archer_id)`, `tournoi_id` n'est qu'un cadre** :
        `TournoiId`, `DepartId` et `PhaseId` sont trois alias d'`int` (`DETTE-044`), donc mypy ne
        dirait rien. Un premier jet dérivait le tournoi de `phase.depart_id` — faux et invisible au
        compilateur ; il est donc **passé par l'appelant**, qui le tient de la route.
        """
        phase_id = phase.id
        assert phase_id is not None, "`_population` a déjà refusé une phase sans identité."
        existante = self._series.par_archer(phase_id, archer_id)
        if existante is not None:
            return existante
        return Serie.vide(tournoi_id, archer_id, phase_id)

    def _exiger_en_lice(self, photo: EtatBigShootOffAffiche, archer_id: int) -> None:
        """Refuse d'écrire pour un archer déjà sorti (ou étranger à la phase).

        ⚠️ **Deux erreurs dédiées**, là où ce refus empruntait `MancheIntrouvable` et
        `PhasePasReglee`. Le même code sortait du même endpoint pour deux situations aux
        corrections **opposées** — « allez régler la phase » et « rechargez, cet archer est éliminé
        ». Le champ `code` existe pour qu'un client aiguille dessus (règle 5).
        """
        tireur = next((t for t in photo.tireurs if t.archer_id == archer_id), None)
        if tireur is None:
            raise ArcherHorsBigShootOff(
                f"L'archer {archer_id} ne fait pas partie de ce Big Shoot Off."
            )
        if not tireur.en_lice:
            raise ArcherDejaSorti(
                f"L'archer {archer_id} est sorti au rang {tireur.rang} : il ne tire plus dans ce "
                "Big Shoot Off."
            )

    def _exiger_manche_de_la_volee(
        self,
        photo: EtatBigShootOffAffiche,
        configuration: ConfigurationBigShootOff,
        numero: int,
    ) -> None:
        """Refuse une volée hors des manches jouables sur cet effectif.

        `Serie.saisir_volee` borne au « barème » (`len(eliminations) · V`), mais ce barème décrit
        la liste **complète**, qui s'écourte quand l'effectif ne la porte pas. ⚠️ **Borne resserrée
        à la manche COURANTE** : `Serie.valider` verrouille « le prochain lot de V volées non
        validées, par numéro », donc saisir la volée 4 avant la 3 laissait le lot emporter une
        volée de la manche suivante et rendait la courante **incomplétable**.
        """
        jouables = photo.projection.manches_jouables * configuration.volees
        if not 1 <= numero <= jouables:
            raise MancheIntrouvable(
                f"La volée {numero} n'appartient à aucune manche jouable : cet effectif n'en "
                f"permet que {photo.projection.manches_jouables}."
            )
        courante = next((manche for manche in photo.manches if not manche.jouee), None)
        if courante is not None and numero not in courante.volees:
            raise MancheIntrouvable(
                f"La volée {numero} n'appartient pas à la manche en cours (manche "
                f"{courante.numero}) : les manches se tirent dans l'ordre."
            )

    def _duelliste(
        self, participant: Participant, lignes: dict[int, LigneClassement]
    ) -> Duelliste | None:
        """Résout un participant en `Duelliste` (nom lu au classement), ou `None`."""
        if participant.genre is not GenreParticipant.INDIVIDUEL:
            return None
        ligne = lignes.get(participant.ref_id)
        if ligne is None:
            return None
        return Duelliste(archer_id=participant.ref_id, nom=ligne.nom, prenom=ligne.prenom)


def _nb_volees(configuration: ConfigurationBigShootOff) -> int:
    """Le « barème » d'une feuille de Big Shoot Off : toutes les manches de la liste, V volées."""
    return len(configuration.eliminations) * configuration.volees


def _scores_de_la_manche(
    etat: EtatBigShootOff,
    configuration: ConfigurationBigShootOff,
    series: dict[int, Serie | None],
) -> dict[Participant, int] | None:
    """Le score de la manche courante pour chaque archer en lice, ou `None` si elle est incomplète.

    « Incomplète » = au moins un archer en lice n'a pas **validé** ses V volées. On rend `None`
    plutôt qu'un dictionnaire partiel : `jouer_manche` refuserait de toute façon
    (`ScoreDeMancheManquant`), et lui poser la question reviendrait à traiter une erreur de
    programmation par une exception métier.
    """
    debut = etat.manche * configuration.volees
    numeros = tuple(range(debut + 1, debut + configuration.volees + 1))
    scores: dict[Participant, int] = {}
    for participant in etat.en_lice:
        serie = series.get(participant.ref_id)
        if serie is None or not _volees_validees(serie, numeros):
            return None
        scores[participant] = sum(
            volee.points for numero in numeros if (volee := serie.volee(numero)) is not None
        )
    return scores


def _volees_validees(serie: Serie | None, numeros: tuple[int, ...]) -> bool:
    """Toutes ces volées existent-elles **et** sont-elles verrouillées ?"""
    if serie is None:
        return False
    return all(
        (volee := serie.volee(numero)) is not None and volee.verrouillee for numero in numeros
    )


def _prochaine_volee(
    serie: Serie | None,
    configuration: ConfigurationBigShootOff,
    manche: int | None,
) -> int | None:
    """La prochaine volée à saisir pour cet archer dans `manche`, ou `None` s'il n'y a rien à tirer.

    `manche` est **0-indexée**. On rend la première volée du bloc `(manche·V+1 … (manche+1)·V)` qui
    n'est **pas encore posée**. ⚠️ « Pas encore posée » et non « pas encore verrouillée » : une
    manche se valide d'un **bloc**, donc entre la première saisie et la validation les V volées
    coexistent non verrouillées — viser la première non verrouillée ramènerait le pavé sur la volée
    1. `None` quand le bloc est complet : il n'y a plus qu'à valider.
    """
    if manche is None:
        return None
    debut = manche * configuration.volees
    for numero in range(debut + 1, debut + configuration.volees + 1):
        if serie is None or serie.volee(numero) is None:
            return numero
    return None


def _scores_par_manche(
    serie: Serie | None, configuration: ConfigurationBigShootOff
) -> tuple[int, ...]:
    """Le score de chaque manche **entièrement validée** d'un archer, dans l'ordre.

    S'arrête à la première manche incomplète : afficher un total partiel ferait lire « 12 » pour une
    manche dont deux volées manquent, et le scoreur croirait l'archer en difficulté.
    """
    if serie is None:
        return ()
    scores: list[int] = []
    for index in range(len(configuration.eliminations)):
        debut = index * configuration.volees
        numeros = tuple(range(debut + 1, debut + configuration.volees + 1))
        if not _volees_validees(serie, numeros):
            break
        scores.append(
            sum(volee.points for numero in numeros if (volee := serie.volee(numero)) is not None)
        )
    return tuple(scores)


def _avec_rang(ligne: LigneClassement, rang: int) -> LigneClassement:
    """La ligne de classement d'un finaliste, au rang que le Big Shoot Off lui a décerné."""
    return replace(ligne, rang_scratch=rang)
