"""Service applicatif **Big Shoot Off** — composer, faire tirer, éliminer, classer (E05US028).

C'est le consommateur de production qui manquait à `domain/big_shoot_off.py` depuis E05US015 : le
moteur existait, testé, et **personne ne l'appelait** (`DETTE-028`). Ce service assemble ce que le
domaine tient séparé — le **prélèvement** (`application/prelevement.py`), la **mécanique
d'élimination** (`demarrer` / `jouer_manche` / `eliminer_apres_barrage`), le **tir**
(`domain/serie.py`) et le **barrage** (`domain/barrage.py`, portée `BIG_SHOOT_OFF`).

## Ce qui est recalculé, ce qui est persisté

Le parti est celui des poules (ADR-0083) et du tableau (ADR-0023/0048), pour la même raison : **la
structure se recalcule, le tir se persiste**.

- **Persisté** : les **volées** de chaque archer, dans la table `serie`/`volee` — *sans table ni
  migration neuve*. C'est le pendant exact d'ADR-0083 §7, où une rencontre de poule réutilise la
  table `duel` : `Serie` est keyée `(phase_id, archer_id)` depuis E05US025 (ADR-0082), donc les V
  volées de chaque manche tiennent dans **une** feuille par archer.
- **Recalculé à chaque lecture** : qui est éliminé, à quelle manche, avec quel rang. Rien de tout
  cela n'est stocké — c'est une fonction déterministe des volées validées et du réglage. Le
  persister créerait une **seconde vérité**, périmée dès qu'une flèche mal saisie est corrigée.

⚠️ **Le second point est ce qui rend une correction possible en salle.** Si « éliminé à la manche 2 »
était une ligne en base, corriger une volée de la manche 1 laisserait l'élimination en place : le
classement dirait une chose, les scores une autre. Ici la correction remonte d'elle-même toute la
chaîne — au prix d'un rejeu complet à chaque lecture (`# DETTE-031`).

## La numérotation des volées, et son ancrage

Une manche est un **bloc de V volées consécutives** : la manche *m* occupe les volées
`(m-1)·V + 1 … m·V`. Le nombre total de volées d'un archer est donc `len(eliminations) · V` — le
« barème » au sens de `Serie`, qui borne la saisie.

La numérotation est **continue et dérivée**, jamais stockée : elle se recalcule du réglage. Un
archer éliminé à la manche 2 n'a simplement pas de volées au-delà — l'absence *est* l'information,
comme pour la réserve d'un plan de cibles (ADR-0024).

## Le grain de validation, et pourquoi le service ne lit pas `phase.validation`

Une manche se valide d'un bloc, et `Serie.valider` sait déjà le faire : `toutes_les_n_volees(V)`
verrouille « le prochain lot de V volées non validées », ce qui **est** la manche courante. Le grain
est donc dérivé du réglage (`configuration.volees`) plutôt que lu sur la phase.

⚠️ **C'est un écart assumé, et il est tracé** (`# DETTE-058`). `phase.validation` reste réglable à
l'atelier pour ce type (`_GRAINS_ADMIS` y admet `FIN_DE_SERIE` et `TOUTES_LES_N_VOLEES`), mais un
Big Shoot Off validé « en fin de série » serait injouable : on ne saurait qui est éliminé qu'après
la dernière manche, c'est-à-dire jamais, puisque la dernière manche dépend des précédentes. Le
service impose donc le seul grain cohérent au lieu d'honorer un réglage qui bloquerait la salle.
Le remède propre — retirer `FIN_DE_SERIE` des grains admis pour ce type — touche un invariant de
`domain/phase.py` partagé avec la qualification ; il vaut une US, pas un cavalier ici.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from application.classements import ServiceClassement
from application.erreurs import (
    MancheIntrouvable,
    PhaseIntrouvable,
    PhasePasReglee,
    PhasePasUnBigShootOff,
    TournoiIntrouvable,
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
from domain.tournoi import TournoiId


@dataclass(frozen=True)
class ProjectionBigShootOff:
    """Ce que la liste de sortants donne sur l'effectif **réel** — le CA « la répartition montrée ».

    Jumeau de `RepartitionPoules`, et pour la même raison : l'organisateur doit voir ce que son
    réglage produit **avant** de composer, pas le découvrir en salle. `paliers` porte ce qu'il reste
    après chaque manche réellement jouable ; `manches_ignorees` compte les cases de la liste qui ne
    se joueront pas faute d'effectif.

    ⚠️ `manches_ignorees` n'est pas une erreur : c'est le prix de « on joue tant que la manche est
    possible », qui rend un format réutilisable sur un effectif qu'il ignore. Mais c'est une
    information que l'écran doit **dire**, sinon l'organisateur croit jouer une liste qu'il ne joue
    pas.
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

    Consommé par `ServicePalmares`, qui a besoin des rangs décernés mais n'a aucune raison de
    connaître les volées, les barrages ni le prélèvement qui les produisent.

    ⚠️ **Ce port n'est pas branché tardivement**, contrairement à `LecteurClassementPoules` : il n'y
    a **pas de cycle** ici (`palmares` importe déjà `saisie_duels`, et `big_shoot_off` n'importe pas
    `palmares`). Le branchement tardif de `brancher_poules` existe pour casser un cycle réel ; le
    reproduire sans cycle n'aurait fait qu'échanger un contrôle du compilateur contre un test de
    câblage — un oubli au composition root serait passé en silence. Le port se passe donc au
    **constructeur**, comme toutes les autres dépendances du projet.
    """

    def etat(self, tournoi_id: TournoiId, phase_id: PhaseId) -> EtatBigShootOffAffiche:
        """La photo de ce Big Shoot Off : qui est sorti, à quel rang."""
        ...


class ServiceBigShootOff:
    """Cas d'usage du Big Shoot Off : consulter, saisir une volée, valider une manche.

    **Ce qui est partagé l'est réellement** : l'agrégat `Serie`, la table `serie`/`volee`, et la
    résolution de population (`preleves`). Faire écrire le tir autrement créerait une seconde façon
    de saisir des volées — l'exacte duplication qu'ADR-0083 se donne pour objet de fermer.

    **Ce qui diffère est le décor** : ici l'archer tire une **volée collective**, tout le monde sur
    la ligne, et c'est le *classement de la manche* qui décide — pas un adversaire. C'est le `decor`
    du contrat (`VOLEE_COLLECTIVE`, la 2ᵉ question), et c'est tout ce que ce service réimplémente.
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

    # --- Lecture ---------------------------------------------------------------------------------

    def projection(self, tournoi_id: TournoiId, phase_id: PhaseId) -> ProjectionBigShootOff:
        """Ce que la liste de sortants donne sur l'effectif réel, **sans rien écrire**.

        Volontairement séparé d'`etat` : montrer la projection ne doit exiger ni tir ni gabarit de
        salle — sinon l'organisateur ne pourrait pas régler son Big Shoot Off avant d'avoir fait sa
        salle. Même découpe que `ServicePoules.repartition`, et pour la même raison.
        """
        phase, participants = self._population(tournoi_id, phase_id)
        return self._projection(phase, len(participants))

    def etat(self, tournoi_id: TournoiId, phase_id: PhaseId) -> EtatBigShootOffAffiche:
        """La photo complète : qui tire, qui est sorti, à quel rang, et ce qui bloque.

        `# DETTE-031` — l'état est **rejoué intégralement** à chaque lecture, chaîne de sources
        amont comprise, sans mémoïsation transverse aux requêtes.

        Lève `TournoiIntrouvable` / `PhaseIntrouvable` (404), `PhasePasUnBigShootOff` ou
        `PhasePasReglee` (409).
        """
        phase, participants = self._population(tournoi_id, phase_id)
        return self._photo(phase, participants)

    def classement_de_phase(
        self, tournoi_id: TournoiId, phase_id: PhaseId, resolveur: ResolveurClassement
    ) -> ClassementSource:
        """Le classement que ce Big Shoot Off **produit** — le port `LecteurClassementBigShootOff`.

        C'est ce qui rend une phase avale alimentable par un Big Shoot Off : jusqu'ici
        `ServiceSaisieDuels._classement_de_l_ordre` rendait `None` sur ce type, donc un prélèvement
        le visant restait **inerte** — la phase aval recevait tous les archers en lice, ce qui est
        plausible et faux.

        ⚠️ **Aucune plage indécise n'est déclarée** (ADR-0081), et ce n'est pas un oubli : les rangs
        d'un Big Shoot Off sont **exacts** dès qu'ils sont décernés. Un archer encore en lice n'a
        pas de rang du tout — il n'apparaît donc pas dans une fourchette « 1ᵉʳ-5ᵉ à départager »
        comme un duelliste de tableau, il partage le rang 1 avec les autres rescapés jusqu'à sa
        sortie. Ce **partage** est en revanche une vraie indécision, et il est déclaré comme telle :
        sans quoi une phase avale prélevant « le rang 1 » d'un Big Shoot Off inachevé emporterait
        cinq archers en croyant en prendre un.

        `rang_premier` est posé ici avec le **même** résolveur que celui qui a servi à prélever :
        deux bases différentes situeraient la population et le décalage dans deux espaces de rangs
        distincts, ce qui est exactement `DETTE-034`.
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

        La validation reste **par archer** — c'est l'agrégat `Serie` qui se verrouille, et chaque
        finaliste a la sienne. C'est la *manche* qui se joue collectivement, pas la validation : le
        scoreur qui descend la ligne valide feuille par feuille, exactement comme en qualification.

        Le grain est dérivé du réglage (`toutes_les_n_volees(V)`) et non lu sur la phase — voir la
        note de module (`# DETTE-058`).
        """
        phase, _participants = self._population(tournoi_id, phase_id)
        configuration = self._configuration(phase)
        serie = self._feuille(tournoi_id, phase, archer_id)
        self._series.enregistrer(
            serie.valider(
                scoreur,
                grain=GrainValidation.toutes_les_n_volees(configuration.volees),
                nb_volees_bareme=_nb_volees(configuration),
            )
        )
        return self.etat(tournoi_id, phase_id)

    # --- Rouages ---------------------------------------------------------------------------------

    def _population(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        resolveur: ResolveurClassement | None = None,
    ) -> tuple[Phase, list[LigneClassement]]:
        """Les gardes, puis **qui entre dedans** — la 1ʳᵉ question du contrat (ADR-0083 §1).

        Générique depuis ADR-0068/E05US024 : `preleves` lit chaque source dans le classement de
        **sa** phase, en remontant la chaîne. Un Big Shoot Off sans source déclarée est donc
        alimenté par le classement du départ.

        `resolveur` est fourni quand l'appel vient **d'en haut** (une phase avale qui remonte la
        chaîne) : on réutilise alors son cache et sa chaîne de phases visitées plutôt que d'en
        ouvrir un second — sans quoi on repaierait la reconstruction d'un amont déjà résolu
        (`DETTE-031`) et on perdrait la détection de cycle.
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
        tireurs = tuple(
            TireurAffiche(
                archer_id=ligne.archer_id,
                nom=ligne.nom,
                prenom=ligne.prenom,
                en_lice=Participant.individuel(ligne.archer_id) in etat.en_lice,
                rang=rangs.get(Participant.individuel(ligne.archer_id)),
                scores=_scores_par_manche(series.get(ligne.archer_id), configuration),
            )
            for ligne in participants
        )
        return EtatBigShootOffAffiche(
            phase_id=phase_id,
            projection=projection,
            tireurs=tireurs,
            manches=self._manches(configuration, projection, etat, lices, series),
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

        ⚠️ **Seules les volées validées comptent.** Un tir en cours de saisie ferait bouger
        l'élimination à chaque flèche, et un archer apparaîtrait sorti puis rentré sous les yeux du
        juge. Même parti que la reconstruction d'un tableau, qui ne rejoue que les duels validés.

        On s'arrête à la première manche **incomplète** : tant qu'un archer en lice n'a pas validé
        ses V volées, la manche n'a pas eu lieu. La traiter en la comptant comme un zéro
        éliminerait quelqu'un sur une donnée absente — ce que `jouer_manche` refuse déjà
        (`ScoreDeMancheManquant`), et qu'on n'a donc pas à lui demander.

        Les **verdicts de barrage** déjà rendus sont appliqués au passage : sans eux, une manche
        suspendue par une égalité le resterait à chaque relecture, et la phase serait bloquée alors
        même que le barrage a été tiré.

        Rend aussi la **lice au début de chaque manche**, capturée au fil du rejeu. ⚠️ Un premier
        jet la reconstituait *après coup* en dépliant les rangs décernés à l'envers : exact tant
        qu'une manche ne sort qu'un archer, faux dès qu'elle en sort plusieurs à rangs partagés —
        et l'erreur ne se serait vue qu'en salle, sur l'écran de saisie d'une manche intermédiaire.
        Capturer ce que la boucle sait déjà coûte une ligne et supprime la classe d'erreur.
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
            # appliquer *tous* avant d'avancer (revue d'E05US028). Le domaine ne départage qu'un
            # groupe d'ex æquo à la fois — `_conclure` le dit : « s'il en reste un autre, la
            # conclusion rejouée le trouvera au tour suivant » — donc `eliminer_apres_barrage` peut
            # **re-suspendre** la même manche. Un premier jet n'appliquait qu'un seul verdict puis
            # rebouclait : `etat.manche` n'ayant pas avancé, `jouer_manche` retrouvait un barrage en
            # attente et levait `ConfigurationBigShootOffInvalide` — à *chaque lecture*, donc
            # l'écran de saisie, le panneau de routage et le palmarès tombaient tous les trois,
            # définitivement. Le cas est ordinaire dès que `departage_les_sortants` est réglé : deux
            # groupes d'ex æquo parmi les sortants suffisent, sur un shoot-off à 3 flèches.
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

        Indexés par l'**ensemble** des ex æquo, parce que c'est ce que le moteur nomme quand il
        suspend une manche : il ne connaît pas l'identifiant du barrage, seulement qui est à
        égalité.

        ⚠️ **On lit `resultat()`, jamais `verdict()`, et le domaine le disait déjà.** `verdict()`
        éclate un *rang partagé* en rangs consécutifs — il rend donc un ordre **vide** quand
        `rang_dispute is None`, ce qui est précisément le cas d'un Big Shoot Off : l'égalité au
        plus faible ne dispute aucun rang, elle désigne un **sortant**. Sa docstring renvoie
        explicitement l'appelant vers `resultat()`. Un premier jet de ce service lisait
        `verdict().rangs()` et trouvait donc toujours le vide : la manche restait suspendue **même
        après le barrage tiré**, et la phase se bloquait en salle sans rien dire. C'est le test de
        service qui l'a attrapé.

        ⚠️ **L'ordre est inversé ici.** `ResultatBarrage.ordre` classe du **meilleur au moins bon**
        (`_groupes_de_score`), quand `eliminer_apres_barrage` attend le plus faible en premier — le
        sortant. On inverse dans le service plutôt que dans le domaine : c'est une convention de
        lecture entre deux moteurs, pas une règle du Big Shoot Off.

        ⚠️ **Les barrages clos comptent**, comme en poules et en qualification : ce sont eux qui
        portent les verdicts déjà appliqués. Les filtrer ferait retomber en égalité, à la lecture
        suivante, une manche qu'on a fait tirer.

        Un barrage **non résolu** (ex æquo persistants au retir) est ignoré : `ordre` y est vide par
        contrat — « un classement à moitié vrai est plus dangereux qu'un refus » —, donc la manche
        reste suspendue, ce qui est exact.
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

        ⚠️ **La clé de lecture est `(phase_id, archer_id)`, et `tournoi_id` n'est qu'un cadre** —
        les confondre est le piège que `SerieRepository.par_archer` documente : `TournoiId`,
        `DepartId` et `PhaseId` sont trois alias d'`int` (`DETTE-044`), donc mypy ne dirait rien.
        Neuf sites l'avaient fait en silence à l'introduction de la clé (E05US025), et un premier
        jet de ce service dérivait le tournoi de `phase.depart_id` — faux, et invisible au
        compilateur. Le tournoi est donc **passé par l'appelant**, qui le tient de la route.
        """
        phase_id = phase.id
        assert phase_id is not None, "`_population` a déjà refusé une phase sans identité."
        existante = self._series.par_archer(phase_id, archer_id)
        if existante is not None:
            return existante
        return Serie.vide(tournoi_id, archer_id, phase_id)

    def _exiger_en_lice(self, photo: EtatBigShootOffAffiche, archer_id: int) -> None:
        """Refuse d'écrire pour un archer déjà sorti (ou étranger à la phase)."""
        tireur = next((t for t in photo.tireurs if t.archer_id == archer_id), None)
        if tireur is None:
            raise MancheIntrouvable(f"L'archer {archer_id} ne fait pas partie de ce Big Shoot Off.")
        if not tireur.en_lice:
            raise PhasePasReglee(
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

        `Serie.saisir_volee` borne déjà au « barème » (`len(eliminations) · V`), mais ce barème
        décrit la liste **complète** — or elle s'écourte quand l'effectif ne la porte pas. Sans
        cette garde, on pourrait saisir les volées d'une manche que la phase ne jouera jamais.
        """
        jouables = photo.projection.manches_jouables * configuration.volees
        if not 1 <= numero <= jouables:
            raise MancheIntrouvable(
                f"La volée {numero} n'appartient à aucune manche jouable : cet effectif n'en "
                f"permet que {photo.projection.manches_jouables}."
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
