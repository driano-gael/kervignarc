"""Service applicatif Saisie (E04US002) — saisir, valider, corriger la qualification d'un archer.

Orchestre le moteur métier `Serie`/`Volee` : il **résout la configuration** depuis la phase et le
blason (le pavé se déduit du blason tiré — `Blason.zones` — pas du barème), pilote l'agrégat, et
**bâtit les entrées d'audit** de validation et de correction (« qui / quand / avant-après »,
E10US005). Le « quand » est lu via le port `Horloge` (jamais dans le domaine, resté déterministe).

Frontières (cf. `stories/E04-saisie-scores.md`) :

- L'**autorisation par le poste** vit **ici**, pas dans un `Depends` d'API : les méthodes d'écriture
  reçoivent un `ContexteSaisie | None` (cible + départ courant) et cloisonnent la saisie au triplet
  `(tournoi, cible, départ)` — `SaisieHorsCible` sinon (ADR-0033 §3). Au service car un appelant
  **hors HTTP** (writer WS E04US009, orchestrateur E12US002) contournerait une garde d'API. Les
  archers de la grille se reconstituent depuis les `Affectation` (`archers_du_poste`), pas depuis le
  champ hérité `Archer.cible` (ADR-0033 §1). `contexte=None` = saisie **admin**, sans contrainte.
- Le **nom** de qui agit (scoreur en validation, rôle habilité en correction) est **fourni** au
  service (résolu par `exiger_scoreur` côté API) : le service reste pur, sans jeton ni session.
- L'**atomicité acte↔trace** (validation/correction) passe par le port
  `SerieRepository.enregistrer_avec_trace` (série + audit en une transaction, ADR-0035).
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass

from application.erreurs import (
    ApplicationError,
    ArcherIntrouvable,
    BlasonIntrouvable,
    CategorieIntrouvable,
    PhaseQualificationAbsente,
    SaisieHorsCible,
)
from application.gel_de_pause import (
    DeclencheurArrets,
    EvaluateurArrets,
    refuser_si_en_pause,
)
from application.portee import (
    la_plus_avancee,
    la_plus_courante,
    qualification_courante,
    qualification_du_tournoi,
)
from application.prelevement import LecteurPopulationPhase, ResolveurClassement
from domain.archer import Archer, ArcherId
from domain.blason import ZoneScore
from domain.depart import DepartId
from domain.entree_audit import ActionAuditee, EntreeAudit
from domain.erreurs import DomainError
from domain.phase import Phase, PhaseId, TypePhase
from domain.ports import (
    ArcherRepository,
    BlasonRepository,
    CategorieRepository,
    ForfaitRepository,
    Horloge,
    InscriptionRepository,
    PhaseRepository,
    PlacementRepository,
    SerieRepository,
)
from domain.serie import Serie
from domain.suivi_deroule import AvancementDePhase
from domain.tour_de_phase import nb_tours_regles
from domain.tournoi import TournoiId

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ContexteSaisie:
    """Contexte d'autorisation d'une saisie **par un poste** : sa cible et son départ courant.

    Passé aux méthodes d'écriture pour cloisonner la saisie au **triplet** `(tournoi, cible,
    départ)` (ADR-0033 §3) : un poste ne saisit que pour un archer affecté à `(cible, départ)`.
    `None` (contexte absent) = saisie **admin**, sans contrainte de cible (E10US001) — l'admin, lui,
    n'est pas rattaché à un lieu.
    """

    cible_index: int
    depart_id: DepartId


@dataclass(frozen=True)
class ArcherPositionne:
    """Un archer, sa **position** (A..D) et son **pavé** — une ligne de la grille de saisie.

    Reconstitué depuis les `Affectation` du placement réel (ADR-0033), pas depuis `Archer.cible`.
    `zones` est le pavé légal de l'archer (les valeurs de son `Blason`, touches illégales absentes —
    CA « pavé ») : le serveur est l'autorité du barème, le front n'a pas à re-dériver la chaîne
    `catégorie → blason → zones`. `()` si le blason est indéterminable (cf.
    `_zones_du_blason_grille`).
    """

    position: str
    archer: Archer
    zones: tuple[ZoneScore, ...] = ()
    forfait: bool = False
    """L'archer a **abandonné ou été disqualifié** en qualification (E04US015, ADR-0050).

    Il reste dans la grille (un forfait ne déplace personne) mais sa série ne sera **jamais
    complétée**. Le signal est exposé parce que le client a besoin de savoir qu'une série incomplète
    est **close pour de bon** : sans lui, un écran qui attend « toutes les séries finies » (le
    panneau de routage, E04US018) attendrait indéfiniment des volées qui ne viendront pas. Même
    notion que `ServiceCompletude._serie_close` — « barème validé **ou** forfait », DETTE-014 :
    c'est le serveur qui sait, pas le front.
    """


@dataclass(frozen=True)
class EtatSerie:
    """État persisté d'une série, en **lecture** : l'agrégat `Serie` et le « quand » de ses volées.

    Le `created_at` de chaque volée (ex-017) vit **hors** du domaine `Volee` (arbitrage de revue) :
    il accompagne la série ici, par numéro, pour la consultation « volée N saisie par … à HH:MM ».
    """

    serie: Serie
    horodatages: dict[int, datetime.datetime]


@dataclass(frozen=True)
class AvancementCible:
    """Avancement de saisie d'une cible, pour la supervision (E12US001, ADR-0038 §2).

    `volee_courante` : la volée en cours (1-based) au rythme du **plus lent** des archers de la
    cible — **0** si **aucun archer** n'est placé sur la cible (grille vide) ; des archers placés
    mais qui n'ont rien saisi donnent **1** (le retardataire tient la cible). `nb_volees` : total
    attendu (barème de qualification), **0** si la qualification n'est pas configurée (la
    supervision n'échoue pas là-dessus, elle affiche « — »). `derniere_saisie` : « quand » de la
    dernière volée saisie sur la cible, tous archers confondus, ou `None` — c'est l'**activité**
    affichée, jamais le heartbeat (ADR-0038 §2).
    """

    volee_courante: int
    nb_volees: int
    derniere_saisie: datetime.datetime | None


def _valeurs_lisibles(serie: Serie, numero: int) -> str | None:
    """Rend les valeurs d'une volée sous forme lisible (« 10, 9, 8 ») pour l'audit, ou `None`."""
    volee = serie.volee(numero)
    return ", ".join(v.value for v in volee.valeurs) if volee is not None else None


class ServiceSaisie:
    """Cas d'usage de la saisie de qualification : saisir une volée, valider, corriger (tracé)."""

    def __init__(
        self,
        series: SerieRepository,
        phases: PhaseRepository,
        archers: ArcherRepository,
        categories: CategorieRepository,
        blasons: BlasonRepository,
        placements: PlacementRepository,
        inscriptions: InscriptionRepository,
        forfaits: ForfaitRepository,
        horloge: Horloge,
        populations: LecteurPopulationPhase,
    ) -> None:
        # ⚠️ `populations` depuis le correctif de revue d'E05US025 : la saisie doit savoir **quelle
        # qualification admet cet archer** quand le créneau en porte plusieurs (fourche
        # *haute*/*basse*), et cette population se lit par `resolveur_de_classement`. C'est le
        # **même** résolveur que le plan de cibles (`ServicePlacementDuels`) et le palmarès — 4ᵉ
        # consommateur du même idiome, pas un pattern neuf : c'est la raison d'être
        # d'`application/prelevement.py` (« ces deux-là ne peuvent pas diverger »), élargie à un
        # troisième qui ne le peut pas davantage. Le port est **étroit** (`LecteurPopulationPhase`)
        # pour que ce module n'importe pas le service de duels entier.
        self._series = series
        self._phases = phases
        self._archers = archers
        self._categories = categories
        self._blasons = blasons
        self._placements = placements
        self._inscriptions = inscriptions
        self._forfaits = forfaits
        self._horloge = horloge
        self._populations = populations
        # E05US033 : collaborateur **partagé** par les cinq services qui écrivent un résultat
        # (`application.gel_de_pause`). Construit sans argument et **inerte** tant que le
        # composition root n'y a rien branché — donc les décors de test existants sont inchangés.
        self._arrets = DeclencheurArrets()

    def archers_du_poste(
        self, tournoi_id: TournoiId, cible_index: int, depart_id: DepartId
    ) -> list[ArcherPositionne]:
        """Les archers **placés** sur `(cible, départ)`, avec leur position A..D, triés.

        La source de la grille de saisie (CA « grille ») : reconstituée depuis les `Affectation` du
        placement **réel** et ajustable (ADR-0033), donc un glisser-déposer d'archer (E03US004)
        déplace aussi *où il saisit*, sans code ici. Un archer en **réserve** (aucune affectation)
        n'apparaît pas. L'appelant fournit le départ courant du poste (déjà validé, ADR-0034).
        """
        inscriptions = {i.id: i for i in self._inscriptions.par_depart(depart_id)}
        forfaits = self._forfaits_qualif(tournoi_id)
        grille: list[ArcherPositionne] = []
        for affectation in self._placements.par_depart(depart_id):
            if affectation.cible_index != cible_index:
                continue
            inscription = inscriptions.get(affectation.inscription_id)
            if inscription is None:
                continue  # défensif : affectation sans inscription correspondante
            archer = self._archers.par_id(inscription.archer_id)
            if archer is None or archer.tournoi_id != tournoi_id:
                continue
            grille.append(
                ArcherPositionne(
                    position=affectation.position,
                    archer=archer,
                    zones=self._zones_du_blason_grille(archer),
                    forfait=archer.id in forfaits,
                )
            )
        grille.sort(key=lambda ligne: ligne.position)
        return grille

    def avancement_cible(
        self, tournoi_id: TournoiId, cible_index: int, depart_id: DepartId
    ) -> AvancementCible:
        """Compose l'avancement d'une cible pour la console de supervision (E12US001, ADR-0038 §2).

        Lecture seule. Le total de volées vient du barème de qualification (**0** si elle n'est pas
        configurée : la supervision **ne lève pas** `PhaseQualificationAbsente`, affiche « — »). Le
        rythme se lit sur les séries des archers **placés** sur la cible ; « volée courante » =
        celle du **plus lent** (les archers d'une cible tirent ensemble, avance en bloc). La «
        dernière saisie » (dernier `created_at`) alimente la colonne *dernière activité* — le
        dernier **tir**, jamais le dernier heartbeat.
        """
        # E05US025 : la qualification **de ce créneau**, et celle qui s'y tire. Cette lecture
        # passait par la portée tournoi alors que la méthode reçoit un `depart_id` — sur un déroulé
        # à plusieurs qualifications, la console aurait annoncé « volée 3/20 » à des archers en
        # train de tirer un second tour de 15.
        phase = qualification_courante(self._phases, depart_id)
        # `bareme` optionnel depuis E05US001 (ADR-0045 §2), présent sur une qualification ; absent
        # (ou phase non configurée) → 0, la supervision affiche « — » sans lever d'erreur.
        nb_volees = phase.bareme.nb_volees if phase is not None and phase.bareme is not None else 0
        # ⚠️ **Un seul résolveur pour toute la cible** (2ᵉ correctif de revue). En construire un par
        # archer repartait d'un cache vide à chaque fois : sur un créneau à trois qualifications, la
        # console de supervision — sondée par 30 tablettes — reconstruisait le classement du créneau
        # quatre fois par cible. Le cache de `resolveur_de_classement` est fait pour être **partagé
        # sur toute la descente** (E05US024) ; le fabriquer en boucle l'annule.
        resolveur = self._populations.resolveur_de_classement(tournoi_id, depart_id)
        completes: list[int] = []
        derniere: datetime.datetime | None = None
        for ligne in self.archers_du_poste(tournoi_id, cible_index, depart_id):
            if ligne.archer.id is None:
                continue  # défensif : un archer non persisté n'a pas de série
            # La feuille se lit dans la phase **de cet archer** : sur la fourche du CA, une même
            # cible mêle des tireurs de la *haute* et de la *basse*, et lire tout le monde dans la
            # phase courante du créneau rendrait la moitié d'entre eux « à 0 volée » — la cible
            # n'aurait jamais fini. Le `nb_volees` affiché reste, lui, celui de la phase courante :
            # la console rend **une** ligne par cible, elle ne peut afficher qu'un dénominateur.
            etat = self._etat_dans(
                self._qualification_de_l_archer(tournoi_id, depart_id, ligne.archer.id, resolveur),
                ligne.archer.id,
            )
            if etat is None:
                completes.append(0)
                continue
            completes.append(len(etat.serie.volees))
            for instant in etat.horodatages.values():
                if derniere is None or instant > derniere:
                    derniere = instant
        if not completes:
            return AvancementCible(volee_courante=0, nb_volees=nb_volees, derniere_saisie=derniere)
        volee_courante = min(completes) + 1
        if nb_volees and volee_courante > nb_volees:
            volee_courante = nb_volees  # toutes les volées saisies : la cible a fini
        return AvancementCible(
            volee_courante=volee_courante, nb_volees=nb_volees, derniere_saisie=derniere
        )

    def etat_serie(
        self,
        tournoi_id: TournoiId,
        archer_id: ArcherId,
        contexte: ContexteSaisie | None = None,
    ) -> EtatSerie | None:
        """L'état persisté de la série de l'archer (volées + « quand »), ou `None` si rien de saisi.

        Chemin de lecture de la grille : la série (valeurs, marqueurs, verrou, cumul) **et** le
        `created_at` de chaque volée (ex-017), joints par numéro. Ne cloisonne pas à la cible : une
        lecture, l'appelant (API) a déjà établi le droit d'accès du poste.

        ⚠️ **La lecture résout la phase comme l'écriture** (correctif de revue E05US025). Elle
        passait `tournoi_id` au port, dont le premier paramètre est un `phase_id` depuis cette US :
        `TournoiId` et `PhaseId` étant deux alias de `int` (`DETTE-044`), mypy n'a rien vu et la
        grille repartait **vierge sur des flèches réellement en base** dès que les deux entiers
        cessaient de coïncider — c'est-à-dire dès le second tournoi de la base. La résolution est
        celle du chemin d'écriture, à la nuance près qu'elle ne **lève** pas : une lecture sans
        qualification configurée rend `None`, comme une série jamais ouverte.

        ⚠️ **`contexte` n'est pas décoratif** (2ᵉ correctif de revue) : sans lui, la lecture résout
        le créneau par « le plus petit identifiant où l'archer est inscrit » (`DETTE-052`) alors que
        l'écriture le reçoit du poste. Sur un archer inscrit matin **et** après-midi, la tablette de
        l'après-midi écrivait dans sa phase et relisait celle du matin : grille vide sur des flèches
        en base, ou pire, les volées verrouillées du matin. La limite `DETTE-052` ne vaut que pour
        la saisie **admin** — le poste sait où il est, encore fallait-il le lui demander.
        """
        return self._etat_dans(
            self._phase_qualification_ou_none(tournoi_id, archer_id, contexte), archer_id
        )

    def horodatages(self, phase_id: PhaseId, archer_id: ArcherId) -> dict[int, datetime.datetime]:
        """Le « quand » de chaque volée de l'archer **dans cette phase** (`{}` sinon).

        Chemin de lecture **léger** pour bâtir la réponse d'un acte d'écriture depuis la `Serie`
        qu'il renvoie déjà, sans re-lire la série entière (`etat_serie`) : l'API dédoublonne
        l'**écriture** seule, puis lit ce « quand » **hors** de l'unité idempotente (ADR-0036).

        ⚠️ **Le paramètre est la `phase_id`, pas le tournoi** (correctif de revue E05US025). Les
        trois appelants d'API tiennent déjà la `Serie` que l'écriture vient de rendre : ils passent
        son `phase_id`, ce qui est **exact par construction** — aucune résolution à refaire, donc
        aucune chance qu'elle diverge de celle qui a écrit.
        """
        return self._series.horodatages(phase_id, archer_id)

    def _etat_dans(self, phase: Phase | None, archer_id: ArcherId) -> EtatSerie | None:
        """L'état de la feuille de cet archer **dans cette phase**, ou `None` (phase ou feuille
        absente).

        Pendant, en lecture, de `_feuille` : un seul endroit joint la série et ses horodatages sur
        le couple `(phase, archer)`, pour qu'aucun chemin de lecture ne retombe sur la maille
        tournoi — le défaut que cette US a introduit puis corrigé.
        """
        if phase is None or phase.id is None:
            return None
        serie = self._series.par_archer(phase.id, archer_id)
        if serie is None:
            return None
        return EtatSerie(serie=serie, horodatages=self._series.horodatages(phase.id, archer_id))

    def saisir_volee(
        self,
        tournoi_id: TournoiId,
        archer_id: ArcherId,
        numero: int,
        valeurs: tuple[ZoneScore, ...],
        saisie_par: str | None = None,
        contexte: ContexteSaisie | None = None,
    ) -> Serie:
        """Saisit ou réédite (avant validation) la volée `numero` de l'archer.

        Le pavé (zones admises) se déduit du **blason** de l'archer, le nombre de flèches du
        **barème** de la phase. Persiste sans trace (une saisie ordinaire n'est pas un acte de fin).
        `contexte` cloisonne la saisie à la cible/départ du poste (ADR-0033 §3) ; `None` = admin.
        """
        archer = self._charger_archer(tournoi_id, archer_id, contexte)
        zones = self._zones_du_blason(archer)
        phase = self._phase_qualification(tournoi_id, archer_id, contexte)
        refuser_si_en_pause(phase)
        assert phase.bareme is not None, "Une qualification porte toujours un barème (ADR-0045 §2)."
        serie = self._feuille(tournoi_id, archer_id, phase)
        serie = serie.saisir_volee(
            numero,
            valeurs,
            zones_admises=zones,
            nb_fleches_par_volee=phase.bareme.nb_fleches_par_volee,
            nb_volees_bareme=phase.bareme.nb_volees,
            saisie_par=saisie_par,
        )
        return self._series.enregistrer(serie)

    def valider(
        self,
        tournoi_id: TournoiId,
        archer_id: ArcherId,
        scoreur: str,
        contexte: ContexteSaisie | None = None,
    ) -> Serie:
        """Valide la série de l'archer selon le grain de la phase, au nom du `scoreur`.

        Verrouille les volées concernées (fin de série ou lot de N, cf. `Serie.valider`) et laisse
        une **trace** `VALIDATION` (sans avant/après) dans la même transaction que l'écriture.
        `contexte` cloisonne au poste (ADR-0033 §3) — la garde vaut pour **tout** chemin d'écriture.

        ⚠️ Le `scoreur` est un **nom** (pour l'audit) : ce service **ne peut pas** vérifier que le
        scoreur officie dans **ce** tournoi. Cette garde (`ScoreurHorsTournoi`, 403) vit **à l'API**
        (`exiger_scoreur` résout le `Scoreur` + `_exiger_meme_tournoi`) — asymétrique avec la garde
        poste, descendue ici. Aucun appelant hors HTTP ne valide aujourd'hui ; **E04US009 (writer
        WS) devra la répliquer** — ou passer le tournoi du scoreur — s'il ouvre un tel chemin.
        """
        self._charger_archer(tournoi_id, archer_id, contexte)
        phase = self._phase_qualification(tournoi_id, archer_id, contexte)
        refuser_si_en_pause(phase)
        assert (
            phase.bareme is not None and phase.validation is not None
        ), "Une qualification porte toujours barème et grain (ADR-0045 §2)."
        serie = self._feuille(tournoi_id, archer_id, phase)
        serie = serie.valider(
            scoreur, grain=phase.validation, nb_volees_bareme=phase.bareme.nb_volees
        )
        entree = EntreeAudit.creer(
            tournoi_id=tournoi_id,
            action=ActionAuditee.VALIDATION,
            auteur=scoreur,
            horodatage=self._horloge.maintenant(),
            objet=f"série de qualification de l'archer {archer_id}",
        )
        enregistree = self._series.enregistrer_avec_trace(serie, entree)
        # Le résultat est **écrit** : c'est maintenant qu'un tour peut être achevé (E05US033).
        self._arrets.signaler(phase.depart_id)
        return enregistree

    def corriger_volee(
        self,
        tournoi_id: TournoiId,
        archer_id: ArcherId,
        numero: int,
        nouvelles_valeurs: tuple[ZoneScore, ...],
        auteur: str,
        contexte: ContexteSaisie | None = None,
    ) -> Serie:
        """Corrige une volée **verrouillée** de l'archer, au nom de l'`auteur` (rôle habilité).

        Chemin d'écriture unique sur une volée validée. Laisse une trace `CORRECTION_SCORE` portant
        l'**avant** et l'**après**, dans la même transaction que la réécriture (ADR-0035). Le cumul
        se recalcule mécaniquement. `contexte` cloisonne au poste (ADR-0033 §3) ; `None` = admin.
        """
        archer = self._charger_archer(tournoi_id, archer_id, contexte)
        zones = self._zones_du_blason(archer)
        phase = self._phase_qualification(tournoi_id, archer_id, contexte)
        assert phase.bareme is not None, "Une qualification porte toujours un barème (ADR-0045 §2)."
        serie = self._feuille(tournoi_id, archer_id, phase)
        avant = _valeurs_lisibles(serie, numero)
        serie = serie.corriger_volee(
            numero,
            nouvelles_valeurs,
            par=auteur,
            zones_admises=zones,
            nb_fleches_par_volee=phase.bareme.nb_fleches_par_volee,
        )
        entree = EntreeAudit.creer(
            tournoi_id=tournoi_id,
            action=ActionAuditee.CORRECTION_SCORE,
            auteur=auteur,
            horodatage=self._horloge.maintenant(),
            objet=f"volée {numero} de l'archer {archer_id}",
            avant=avant,
            apres=_valeurs_lisibles(serie, numero),
        )
        return self._series.enregistrer_avec_trace(serie, entree)

    def avancement_de_phase(
        self, tournoi_id: TournoiId, phase_id: PhaseId
    ) -> AvancementDePhase | None:
        """Où en est cette **qualification** — réalise `LecteurAvancementDePhase` (E05US033).

        ⚠️ **Ce lecteur manquait, et son absence était le bloquant central de l'US** (relevé par les
        quatre axes de revue). `DecoupageEnTours` était écrit, validé, sérialisé, exposé en DTO et
        éditable à l'écran — et **lu par personne**. Une qualification n'ayant aucun lecteur
        branché, son `tour_courant` restait `None` pour toujours, et le déclencheur d'arrêt lisait
        ce `None` comme « tout est joué » : une pause « après le tour 1 » se déclenchait à la
        **première** série validée, avant que quiconque ait tiré ses dix volées. Le CA « la
        qualification devient divisible en tours — sans lui, ce type n'a qu'un tour et ne peut pas
        s'arrêter en cours de route » n'était pas livré, et le mécanisme se retournait contre lui.

        **Comment le tour se dérive.** Le découpage donne `nb_tours` ; chaque tour vaut `nb_volees /
        nb_tours` volées du barème. Le tour courant est celui de la **volée la moins avancée du
        plateau** : une phase avance au rythme du dernier archer, pas du premier. Compter sur le
        plus avancé ferait couper la salle alors qu'une cible tire encore.

        ⚠️ **Seules les volées VALIDÉES comptent**, et c'est la même définition d'« achevé » que
        partout ailleurs dans le moteur (`AvancementTour` ne compte que les duels tranchés, un tour
        de poule que les rencontres verrouillées). Une volée saisie mais non validée laisse le tour
        ouvert — sinon un arrêt tomberait sur une saisie que le scoreur n'a pas encore confirmée.

        Rend `None` — « je ne sais pas » — dans deux cas, et il faut que ce soit `None` et non «
        tour 1 » : phase qui n'est pas une qualification (le lecteur est branché par type, mais une
        phase peut être retypée), et phase sans barème lisible. Le déclencheur ne coupe alors rien,
        ce qui est le repli sûr.

        ⚠️ **L'échauffement n'est PAS couvert**, alors que le CA le nommait avec la qualification.
        Il n'a ni barème ni série (`ContratDePhase` : `decor=AUCUN`, `plan_de_cibles=AUCUN`), donc
        il n'existe **rien** dont dériver un tour : ce n'est pas un manque d'implémentation mais une
        absence de donnée. Le CA est amputé de cette moitié, l'atelier refuse désormais un découpage
        sur un échauffement, et `stories/` est aligné en conséquence.
        """
        phase = self._phases.par_id(phase_id)
        if phase is None or phase.type is not TypePhase.QUALIFICATION or phase.bareme is None:
            return None
        nb_tours = nb_tours_regles(phase.type, phase.decoupage)
        volees_par_tour = phase.bareme.nb_volees / nb_tours
        series = self._series.par_phase(phase_id)
        if not series:
            # Phase démarrée mais rien de tiré : le tour 1 tourne. Ce n'est pas « inconnu » — on
            # sait parfaitement où elle en est —, et rendre `None` ici ferait retomber le
            # déclencheur sur son repli prudent, donc rendrait tout arrêt de cette phase inerte.
            return AvancementDePhase(nb_tours=nb_tours, tour_courant=1)
        validees = min(sum(1 for volee in serie.volees if volee.verrouillee) for serie in series)
        if validees >= phase.bareme.nb_volees:
            # Tout est tiré et validé : plus rien ne tourne, la convention d'ADR-0090.
            return AvancementDePhase(nb_tours=nb_tours, tour_courant=None)
        return AvancementDePhase(
            nb_tours=nb_tours, tour_courant=min(nb_tours, int(validees // volees_par_tour) + 1)
        )

    def brancher_evaluateur_arrets(self, evaluateur: EvaluateurArrets) -> None:
        """Dit à qui signaler qu'un résultat vient d'être validé (E05US033) — délègue au partagé."""
        self._arrets.brancher(evaluateur)

    def _charger_archer(
        self, tournoi_id: TournoiId, archer_id: ArcherId, contexte: ContexteSaisie | None
    ) -> Archer:
        """L'archer du tournoi ; `ArcherIntrouvable` s'il est inconnu ou d'un autre tournoi.

        Si un `contexte` de poste est fourni, cloisonne en plus au triplet `(tournoi, cible,
        départ)` (ADR-0033 §3) : l'archer doit être **affecté** à cette cible sur ce départ, sinon
        `SaisieHorsCible` (403). `contexte=None` (admin) laisse la saisie ouverte, sans contrainte.
        """
        archer = self._archers.par_id(archer_id)
        if archer is None or archer.tournoi_id != tournoi_id:
            raise ArcherIntrouvable(f"Aucun archer d'identifiant {archer_id} dans ce tournoi.")
        if contexte is not None:
            self._verifier_archer_sur_poste(archer_id, contexte)
        return archer

    def _verifier_archer_sur_poste(self, archer_id: ArcherId, contexte: ContexteSaisie) -> None:
        """Refuse (`SaisieHorsCible`) un archer non affecté à la cible/départ courant du poste.

        Reconstitue l'appartenance depuis le placement réel (ADR-0033) : l'archer doit être inscrit
        **sur ce départ** et son affectation porter **cette cible**. Non inscrit, en réserve, ou
        placé ailleurs → éconduit. Numéros de cible répétés d'un tournoi à l'autre : le départ (donc
        le tournoi) et la cible ferment la faille (ADR-0033 §3, triplet).
        """
        inscription = self._inscriptions.par_archer_et_depart(archer_id, contexte.depart_id)
        if inscription is not None and inscription.id is not None:
            for affectation in self._placements.par_depart(contexte.depart_id):
                if (
                    affectation.inscription_id == inscription.id
                    and affectation.cible_index == contexte.cible_index
                ):
                    return
        raise SaisieHorsCible(f"Ce poste ne sert pas l'archer {archer_id} sur cette cible.")

    def _phase_qualification(
        self,
        tournoi_id: TournoiId,
        archer_id: ArcherId,
        contexte: ContexteSaisie | None = None,
    ) -> Phase:
        """La qualification **dans laquelle cet archer tire en ce moment**.

        `PhaseQualificationAbsente` s'il n'y en a aucune.

        ⚠️ **C'est ici que se tient le CA « la saisie sait dans quelle qualification elle écrit »**
        (E05US025, ADR-0082). Cette méthode résolvait « **la** » qualification du tournoi
        (`portee.qualification_du_tournoi`, c'est-à-dire celle du **premier** créneau) : avec un
        déroulé qui en porte plusieurs, les 3x15 de la *haute* seraient allés réécrire les volées
        des 3x20 du premier tour, dans la même feuille et sans le moindre signal.

        Deux résolutions successives, et aucune n'est facultative :

        1. **Le créneau.** Celui du poste (`contexte.depart_id`) quand la saisie vient d'une
        tablette
           — c'est l'autorité, le poste sait où il est. En saisie **admin** (`contexte is None`), le
           créneau se lit sur les inscriptions de l'archer, au numéro le plus bas s'il en a
           plusieurs. Ce dernier point reste un **raccourci** : un archer engagé matin et après-midi
           verra l'admin écrire dans son créneau du matin. C'est `DETTE-046` vue de l'autre bout —
           la donnée sait désormais les distinguer (la clé est `(phase, archer)`), mais cette
           **route** ne porte pas encore le créneau. Marqué `# DETTE-052`.

        2. **La phase, parmi les qualifications de ce créneau**, par ordre : celle qui est
           **démarrée et non terminée** d'abord (c'est « la phase en cours », au sens de
           l'arbitrage) ; à défaut la première **à venir** ; à défaut la dernière.

           Le repli sur « à venir » n'est pas de la complaisance : démarrer une phase est un geste
           **manuel** de l'organisateur (`ServicePhases.demarrer`), et faire dépendre la saisie de
           sa discipline bloquerait le pas de tir tout l'après-midi s'il l'oublie. Même parti que
           `ServicePalmares._resultat`, qui refuse déjà de lire `phase.statut` pour décider ce qu'un
           écran affiche.

        Sur un déroulé à **une seule** qualification — tous les tournois d'aujourd'hui — les deux
        résolutions rendent cette unique phase : le comportement est inchangé, oracle 120 compris.
        """
        phase = self._phase_qualification_ou_none(tournoi_id, archer_id, contexte)
        if phase is None:
            raise PhaseQualificationAbsente(
                "La qualification n'est pas encore configurée pour ce tournoi."
            )
        return phase

    def _phase_qualification_ou_none(
        self,
        tournoi_id: TournoiId,
        archer_id: ArcherId,
        contexte: ContexteSaisie | None,
    ) -> Phase | None:
        """Comme `_phase_qualification`, mais rend `None` au lieu de lever (chemins de **lecture**).

        Les lectures (grille de saisie, déroulé public, supervision) ne doivent pas échouer parce
        qu'un tournoi n'a pas encore de qualification : elles rendent « rien de saisi ». L'écriture,
        elle, lève — on ne laisse pas une flèche sans destination.
        """
        depart_id = self._depart_de_saisie(tournoi_id, archer_id, contexte)
        courante = (
            self._qualification_de_l_archer(tournoi_id, depart_id, archer_id)
            if depart_id is not None
            else None
        )
        if courante is not None:
            return courante
        # Aucun créneau résolu, ou un créneau sans déroulé : on retombe sur la résolution d'avant
        # l'US plutôt que de refuser la saisie. Sur un tournoi mono-qualification c'est la même
        # phase ; sur un tournoi qui en porte plusieurs, un archer sans inscription est de toute
        # façon une donnée incohérente, pas un cas nominal.
        return qualification_du_tournoi(self._phases, tournoi_id)

    def _qualification_de_l_archer(
        self,
        tournoi_id: TournoiId,
        depart_id: DepartId,
        archer_id: ArcherId,
        resolveur: ResolveurClassement | None = None,
    ) -> Phase | None:
        """La qualification de ce créneau **qui admet cet archer**, ou `None` s'il n'y en a aucune.

        ⚠️ **C'est ici que se tient le CA « une flèche ne peut pas atterrir dans la mauvaise feuille
        »** — et un premier jet ne le tenait pas (bloquant de revue). `qualification_courante` rend
        la **première démarrée** du créneau : sur la fourche du CA (*haute* et *basse* composées
        ensemble, démarrées ensemble, cf. l'arbitrage du 09/08/2026 « rien n'impose une seule phase
        en cours à la fois »), elle rendait la *haute* pour **tout le monde**. Les 60 archers de la
        *basse* auraient écrit leurs 3x15 dans la feuille de la haute, et la basse serait restée
        vide — le défaut même que l'US existe pour fermer, déplacé du tournoi vers le créneau.

        La discrimination se fait sur la **population** : une qualification prélevée ne reçoit que
        les archers que ses sources lui ont donnés. On la lit par le résolveur de classement de
        `ServiceSaisieDuels` — **le même** que le plan de cibles et le palmarès (raison d'être
        d'`application/prelevement.py`) : deux résolutions distinctes remettraient un archer à un
        poste dont l'arbre le croit ailleurs.

        ⚠️ **La tête n'est jamais discriminante** : une qualification sans source accueille tout le
        créneau, donc elle admet *aussi* l'archer de la *basse*. Le départage final se fait par
        `la_plus_avancee` et non `la_plus_courante` — sens **inverse** sur les phases démarrées,
        pour la raison écrite là-bas. Un premier correctif s'y était trompé : tant que le premier
        tour restait « en cours », il captait toute la saisie.

        **Court-circuit voulu sur un créneau mono-qualification** : la lecture de classement n'est
        même pas tentée. C'est le cas de tous les tournois d'aujourd'hui — non-régression par
        construction (oracle 120 compris), et surtout aucun coût ajouté au chemin chaud de la
        saisie, qui reconstruirait sinon le classement du créneau à **chaque flèche** (`DETTE-031`,
        pas de cache transverse aux requêtes). Sur un créneau qui en porte plusieurs, `resolveur`
        permet à un appelant qui boucle sur des archers (`avancement_cible`) de **partager** le
        cache d'une résolution à l'autre : le construire par appel l'annulait.
        """
        qualifications = [
            phase
            for phase in self._phases.par_depart(depart_id)
            if phase.type is TypePhase.QUALIFICATION
        ]
        if len(qualifications) <= 1:
            return la_plus_courante(qualifications)
        resoudre = (
            resolveur
            if resolveur is not None
            else self._populations.resolveur_de_classement(tournoi_id, depart_id)
        )
        admises = [phase for phase in qualifications if self._admet(phase, archer_id, resoudre)]
        if not admises:
            # Aucune ne le réclame : classement amont illisible, ou archer hors de toutes les
            # fenêtres. On ne refuse pas la saisie sur une lecture de classement (robustesse jour J)
            # — on retombe sur « la phase en cours du créneau », le comportement d'avant. C'est un
            # repli **destructeur** (des flèches peuvent atterrir dans la mauvaise feuille), à la
            # différence de celui de la complétude qui, lui, est conservateur : on le **journalise**
            # plutôt que de le laisser muet.
            _logger.warning(
                "Aucune qualification du créneau %s ne réclame l'archer %s parmi %d candidates : "
                "repli sur la phase en cours. Déroulé incohérent ou classement amont illisible.",
                depart_id,
                archer_id,
                len(qualifications),
            )
            return la_plus_courante(qualifications)
        return la_plus_avancee(admises)

    @staticmethod
    def _admet(phase: Phase, archer_id: ArcherId, resoudre: ResolveurClassement) -> bool:
        """Cette phase compte-t-elle cet archer dans sa population ?

        Le résolveur rend, pour l'`ordre` d'une phase, le classement qu'elle **produit** — donc
        restreint aux archers qu'elle a reçus (`ClassementSource`, cf.
        `ServiceSaisieDuels._classement_de_l_ordre`). L'appartenance s'y lit directement, sans
        redire les règles de prélèvement ici.

        **La phase de tête (sans source) rend `True` sans rien lire.** Elle accueille tout le
        créneau par construction : lui résoudre un classement complet pour conclure « oui » est la
        plus chère des lectures pour une réponse acquise — sur le chemin **d'écriture**, dans la
        file du writer unique.

        Best-effort assumé : toute erreur de lecture du moteur rend `False` — l'appelant retombe
        alors sur la phase en cours, et le journalise. Le filet couvre `ApplicationError`
        (`PrelevementEnAttente` sur une source indécise) **et** `DomainError` : une qualification
        peut se prélever d'un tableau, dont la reconstruction lève des erreurs de domaine
        (`EffectifTableauInvalide`, `FormatTableauIncoherent`) — les omettre aurait fait tomber la
        saisie en 500 sur un déroulé incohérent, à rebours de ce que ce repli promet.
        """
        if not phase.sources:
            return True
        try:
            source = resoudre(phase.ordre)
        except (ApplicationError, DomainError):
            return False
        if source is None:
            return False
        return any(ligne.archer_id == archer_id for ligne in source.classement.lignes)

    def _feuille(self, tournoi_id: TournoiId, archer_id: ArcherId, phase: Phase) -> Serie:
        """La feuille de cet archer **dans cette phase**, ou une feuille vierge prête à la recevoir.

        Un seul endroit résout le couple `(phase, archer)` pour les trois chemins d'écriture
        (saisie, validation, correction) : les laisser le refaire chacun rouvrirait la porte à ce
        que l'un d'eux retombe sur la maille tournoi — c'est-à-dire au défaut que l'US corrige.
        """
        assert phase.id is not None, "Une phase relue du dépôt porte toujours son identifiant."
        return self._series.par_archer(phase.id, archer_id) or Serie.vide(
            tournoi_id, archer_id, phase.id
        )

    # DETTE-052 : la saisie admin devine le créneau de l'archer au lieu de le recevoir.
    def _depart_de_saisie(
        self,
        tournoi_id: TournoiId,
        archer_id: ArcherId,
        contexte: ContexteSaisie | None,
    ) -> DepartId | None:
        """Le créneau où cet archer tire : celui du poste, sinon le premier où il est inscrit.

        `None` quand l'archer n'a aucune inscription — l'appelant retombe alors sur la résolution au
        tournoi. C'est une donnée incohérente (on ne tire pas sans être inscrit), pas un cas nominal
        : on ne casse pas la saisie dessus le jour J.

        Le départage entre plusieurs inscriptions se fait sur le **plus petit identifiant** de
        créneau, et non sur son numéro d'affichage : il faudrait injecter un `DepartRepository` pour
        lire ce numéro, ce qui ferait porter à la composition root une dépendance entière au service
        d'un départage sans enjeu — les deux ordres ne diffèrent que si les créneaux ont été
        renumérotés après coup. Ce qui compte ici est d'être **déterministe** : deux saisies
        successives du même archer doivent atterrir dans la même feuille. Le vrai remède n'est pas
        un meilleur tri, c'est que la route porte le créneau (`# DETTE-052`).
        """
        if contexte is not None:
            return contexte.depart_id
        candidats = [
            inscription.depart_id
            for inscription in self._inscriptions.par_archer(archer_id)
            if inscription.depart_id is not None
        ]
        return min(candidats) if candidats else None

    def _zones_du_blason(self, archer: Archer) -> tuple[ZoneScore, ...]:
        """Les zones admises du blason par défaut de la catégorie de l'archer (le pavé de saisie).

        `CategorieIntrouvable` si la catégorie manque ; `BlasonIntrouvable` si la catégorie n'a pas
        de blason par défaut (pavé indéterminable) ou si ce blason n'existe pas.
        """
        categorie = self._categories.par_id(archer.categorie_id)
        if categorie is None:
            raise CategorieIntrouvable(f"Catégorie {archer.categorie_id} introuvable.")
        if categorie.blason_id is None:
            raise BlasonIntrouvable(
                "L'archer n'a pas de blason par défaut : le pavé de saisie est indéterminable."
            )
        blason = self._blasons.par_id(categorie.blason_id)
        if blason is None:
            raise BlasonIntrouvable(f"Blason {categorie.blason_id} introuvable.")
        return blason.zones

    # DETTE-022 : 4ᵉ écriture de « phase de qualif -> forfaits » (classements, complétude deux
    # fois).
    def _forfaits_qualif(self, tournoi_id: TournoiId) -> frozenset[ArcherId]:
        """Les archers **forfaits en qualification** (abandon / DSQ, E04US015, ADR-0050).

        Best-effort : sans phase de qualification configurée, personne n'est forfait — la grille
        s'affiche quand même (robustesse jour J, même parti que `avancement_cible` sur le barème).
        """
        phase = qualification_du_tournoi(self._phases, tournoi_id)
        if phase is None or phase.id is None:
            return frozenset()
        return frozenset(forfait.archer_id for forfait in self._forfaits.par_phase(phase.id))

    def _zones_du_blason_grille(self, archer: Archer) -> tuple[ZoneScore, ...]:
        """Le pavé de l'archer pour la **grille** (lecture), ou `()` s'il est indéterminable.

        Contrairement au chemin d'**écriture** (`_zones_du_blason`, qui lève), la grille est une
        lecture : un archer dont la catégorie n'a pas de blason par défaut ne doit pas faire échouer
        **toute** la cible (robustesse jour J). Son pavé remonte vide — le front le signale (« pavé
        indisponible ») ; sa **saisie**, elle, échouera en `BlasonIntrouvable` (404) : erreur
        visible.
        """
        try:
            return self._zones_du_blason(archer)
        except (CategorieIntrouvable, BlasonIntrouvable):
            return ()
