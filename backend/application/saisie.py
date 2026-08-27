"""Service de **saisie** des scores de qualification.

⚠️ **L'autorisation par le poste vit ICI, jamais dans un `Depends` d'API** (ADR-0033 §3) : un
appelant hors HTTP — le writer WebSocket, l'orchestrateur de tour — contournerait une garde d'API.
La saisie est cloisonnée au triplet `(tournoi, cible, départ)` ; `contexte=None` vaut saisie admin.
Les archers de la grille se reconstituent depuis les `Affectation`, pas depuis `Archer.cible`.
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
from domain.suivi_deroule import AvancementDePhase, avancement_de_qualification
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

    Il reste dans la grille (un forfait ne déplace personne) mais sa série ne sera **jamais**
    complétée. Le signal est exposé parce que le client a besoin de savoir qu'une série incomplète
    est **close pour de bon** : sans lui, un écran qui attend « toutes les séries finies »
    attendrait indéfiniment des volées qui ne viendront pas (DETTE-014).
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

    `volee_courante` suit le **plus lent** des archers de la cible — **0** si aucun archer n'y est
    placé, **1** si des archers placés n'ont rien saisi. `nb_volees` vaut **0** si la qualification
    n'est pas configurée (la supervision affiche « — » plutôt que d'échouer). `derniere_saisie` est
    l'**activité** affichée, jamais le heartbeat (ADR-0038 §2).
    """

    volee_courante: int
    nb_volees: int
    derniere_saisie: datetime.datetime | None


def _valeurs_lisibles(serie: Serie, numero: int) -> str | None:
    """Rend les valeurs d'une volée sous forme lisible (« 10, 9, 8 ») pour l'audit, ou `None`."""
    volee = serie.volee(numero)
    return ", ".join(v.value for v in volee.valeurs) if volee is not None else None


def _volees_enchainees(serie: Serie | None) -> int:
    """Combien de volées l'archer a **réellement enchaînées**, en partant de la première.

    ⚠️ **Ce n'est pas `len(serie.volees)`, et la nuance décide de couper la salle ou non.**
    `Serie.saisir_volee` accepte n'importe quel rang : un scoreur qui rattrape une feuille papier
    produit une série `{1..9, 20}` — dix volées au cardinal, neuf réellement tirées. Si cet archer
    est le plus lent, compter le cardinal fait franchir la frontière de tour **avant** que la volée
    manquante soit tirée. Un préfixe contigu ne peut se tromper que dans le sens prudent.
    """
    if serie is None:
        return 0
    numeros = {volee.numero for volee in serie.volees}
    enchainees = 0
    while enchainees + 1 in numeros:
        enchainees += 1
    return enchainees


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

        Lecture seule. Le total vient du barème de qualification (**0** si elle n'est pas
        configurée : la supervision **ne lève pas**, elle affiche « — »). Le rythme se lit sur les
        séries des archers **placés** ; « volée courante » = celle du **plus lent**, les archers
        d'une cible tirant ensemble. La « dernière saisie » est le dernier **tir**, jamais le
        dernier heartbeat.
        """

        # E05US025 : la qualification **de ce créneau**, et celle qui s'y tire. Cette lecture
        # passait par la portée tournoi alors que la méthode reçoit un `depart_id` — la console
        # aurait annoncé « volée 3/20 » à des archers tirant un second tour de 15.
        phase = qualification_courante(self._phases, depart_id)
        # `bareme` optionnel depuis E05US001 (ADR-0045 §2), présent sur une qualification ; absent
        # (ou phase non configurée) → 0, la supervision affiche « — » sans lever d'erreur.
        nb_volees = phase.bareme.nb_volees if phase is not None and phase.bareme is not None else 0
        # ⚠️ **Un seul résolveur pour toute la cible** (2ᵉ correctif de revue). En construire un par
        # archer repartait d'un cache vide à chaque fois : sur un créneau à trois qualifications,
        # la console de supervision — sondée par 30 tablettes — reconstruisait le classement du
        # créneau quatre fois par cible. Le cache de `resolveur_de_classement` est fait pour être
        # **partagé sur toute la descente** (E05US024) ; le fabriquer en boucle l'annule.
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

    def avancement_de_phase(
        self, tournoi_id: TournoiId, phase_id: PhaseId
    ) -> AvancementDePhase | None:
        """*Où en est cette qualification ?* — réalisation du port `LecteurAvancementDePhase`.

        ⚠️ **Tout le travail est de compter la bonne population**, et il y a trois façons de la
        compter faux : le **créneau n'est pas la phase** (ADR-0082, d'où `_admet`) ; le **plan de
        cibles** décide qui tire ; les **forfaits** ne tireront plus. ⚠️ Ceux-ci se lisent par les
        **deux** chemins tant que `DETTE-047` n'est pas résorbée — `par_phase` seul rendait une
        liste vide hors du premier créneau, et un abandon gelait la phase pour la journée.
        """
        phase = self._phases.par_id(phase_id)
        if phase is None or phase.type is not TypePhase.QUALIFICATION or phase.bareme is None:
            return None
        volees = self._volees_du_plus_lent(tournoi_id, phase)
        if volees is None:
            return None
        return avancement_de_qualification(volees, phase.bareme, phase.decoupage)

    def _volees_du_plus_lent(self, tournoi_id: TournoiId, phase: Phase) -> int | None:
        """Le compte de volées **saisies** de l'archer le moins avancé de cette phase.

        `None` quand la phase n'a personne à faire tirer — plateau vide, tout le monde forfait, ou
        aucun archer placé. « Zéro volée » et « personne » ne sont pas la même chose : le premier
        maintient la phase au tour 1, le second n'a aucun tour à annoncer, et les confondre ferait
        annoncer « tour 1 » à une phase que rien ne joue.
        """
        assert phase.id is not None
        # DETTE-047 : l'écriture range tous les forfaits de qualification sur la phase du premier
        # créneau. `par_phase` seul en manquerait la totalité ailleurs — voir la docstring.
        forfaits = frozenset(
            f.archer_id for f in self._forfaits.par_phase(phase.id)
        ) | self._forfaits_qualif(tournoi_id)
        inscriptions = {i.id: i for i in self._inscriptions.par_depart(phase.depart_id)}
        # ⚠️ **Une lecture en bloc, pas une par archer** (correctif de revue, quatre axes). Ce
        # chemin est appelé après **chaque validation de série**, donc dans la file du writer
        # unique (règle 7 : pas de logique métier longue), et par la route publique de suivi
        # pollée toutes les 10 s. Un `par_archer` par archer placé, c'est ~120 requêtes par volée
        # validée sur un plateau de qualification — la phase la plus peuplée et la plus longue du
        # créneau. `par_phase` fait le même travail en une requête, et le port l'offrait déjà.
        volees_par_archer: dict[ArcherId, int] = {}
        # ⚠️ Les séries **trouées** sont journalisées : un archer dont la volée 1 manque reste à
        # zéro quel que soit ce qu'il tire ensuite, et gèlerait la phase s'il en est le plus lent
        # (cf. `_volees_enchainees`). Le compte reste prudent, mais le gel cesse d'être invisible.
        trouees: list[ArcherId] = []
        for serie in self._series.par_phase(phase.id):
            enchainees = _volees_enchainees(serie)
            volees_par_archer[serie.archer_id] = enchainees
            if enchainees < len(serie.volees):
                trouees.append(serie.archer_id)
        # ⚠️ **Un seul résolveur pour toute la phase**, comme `avancement_cible` : en construire un
        # par archer repartirait d'un cache vide à chaque fois, et le suivi est sondé en boucle par
        # le pilotage. C'est le correctif de 2ᵉ passe d'E05US025, à ne pas rejouer ici.
        # DETTE-031 : un résolveur **neuf par phase**, donc une descente complète de la chaîne
        # amont à chaque lecture. C'est le régime de cette dette (le port
        # `LecteurAvancementDePhase` n'a pas le `resolveur` partagé de son jumeau, ADR-0084), et la
        # qualification y entre comme la phase la plus peuplée et la plus longue du créneau.
        resolveur = self._populations.resolveur_de_classement(tournoi_id, phase.depart_id)
        # Une seule lecture, réutilisée par la garde de journalisation plus bas : ce chemin tourne
        # dans la file du writer après chaque validation de série, et le N+1 qu'on vient de fermer
        # deux lignes plus haut n'a pas à être rouvert à moitié (relevé en 2ᵉ passe).
        placements = list(self._placements.par_depart(phase.depart_id))
        comptes: list[int] = []
        for affectation in placements:
            inscription = inscriptions.get(affectation.inscription_id)
            if inscription is None:
                continue  # défensif : affectation sans inscription correspondante
            archer_id = inscription.archer_id
            if archer_id in forfaits or not self._admet(phase, archer_id, resolveur):
                continue
            comptes.append(volees_par_archer.get(archer_id, 0))
        if trouees:
            _logger.info(
                "Phase %s : %d série(s) à volées non enchaînées (archers %s). L'avancement compte "
                "le préfixe contigu ; une volée manquante à bas rang y fige l'archer, et peut "
                "retenir la phase si c'est le plus lent.",
                phase.id,
                len(trouees),
                ", ".join(str(a) for a in sorted(trouees)),
            )
        if not comptes:
            # Best-effort, mais pas muet : un plateau vide **alors que des archers sont placés**
            # signale un amont indécis (`_admet` rend `False` sur toute erreur de lecture) ou une
            # catégorie entièrement forfait. Dans les deux cas la phase n'annoncera plus de tour,
            # et rien ne le dirait sans cette ligne (correctif de revue, axe adversarial).
            if placements:
                _logger.info(
                    "Aucun archer ne compte pour l'avancement de la phase %s du créneau %s "
                    "(tous forfaits, ou population illisible) : aucun tour ne sera annoncé.",
                    phase.id,
                    phase.depart_id,
                )
            return None
        return min(comptes)

    def etat_serie(
        self,
        tournoi_id: TournoiId,
        archer_id: ArcherId,
        contexte: ContexteSaisie | None = None,
    ) -> EtatSerie | None:
        """L'état persisté de la série de l'archer (volées + « quand »), ou `None` si rien de saisi.

        ⚠️ **La lecture résout la phase comme l'écriture** : elle passait `tournoi_id` au port,
        dont le premier paramètre est un `phase_id` — deux alias d'`int` (`DETTE-044`), donc mypy
        n'a rien vu et la grille repartait **vierge sur des flèches en base**. ⚠️ `contexte` n'est
        pas décoratif : sans lui la lecture résout le créneau par `DETTE-052` alors que l'écriture
        le reçoit du poste, si bien que la tablette de l'après-midi relisait la phase du matin.
        """
        return self._etat_dans(
            self._phase_qualification_ou_none(tournoi_id, archer_id, contexte), archer_id
        )

    def horodatages(self, phase_id: PhaseId, archer_id: ArcherId) -> dict[int, datetime.datetime]:
        """Le « quand » de chaque volée de l'archer **dans cette phase** (`{}` sinon).

        Chemin de lecture **léger** pour bâtir la réponse d'un acte d'écriture depuis la `Serie`
        qu'il renvoie déjà : l'API dédoublonne l'**écriture** seule, puis lit ce « quand » **hors**
        de l'unité idempotente (ADR-0036). ⚠️ Le paramètre est la `phase_id`, pas le tournoi — les
        appelants tiennent déjà la `Serie` que l'écriture vient de rendre, donc **exact par
        construction** : aucune résolution à refaire, aucune chance de diverger.
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

        Verrouille les volées concernées et laisse une **trace** `VALIDATION` dans la même
        transaction. `contexte` cloisonne au poste (ADR-0033 §3). ⚠️ Le `scoreur` est un **nom**
        (pour l'audit) : ce service **ne peut pas** vérifier qu'il officie dans ce tournoi — cette
        garde vit à l'API (`exiger_scoreur`), asymétrique avec la garde poste descendue ici.
        E04US009 (writer WS) devra la répliquer s'il ouvre un chemin hors HTTP.
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

        ⚠️ **C'est ici que se tient le CA « la saisie sait dans quelle qualification elle écrit »**
        : résoudre « la » qualification du tournoi aurait fait réécrire les volées du premier tour
        par celles de la *haute*. Deux résolutions — le **créneau** (celui du poste, sinon le plus
        bas des inscriptions, `# DETTE-052`), puis la **phase** parmi les qualifications de ce
        créneau. Sur un déroulé à une seule qualification, le comportement est inchangé.
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

        ⚠️ **C'est ici que se tient le CA « une flèche ne peut pas atterrir dans la mauvaise
        feuille »** : `qualification_courante` rend la première démarrée, donc la *haute* pour tout
        le monde. La discrimination se fait sur la **population**, lue par le résolveur de
        `ServiceSaisieDuels` — **le même** que le plan de cibles et le palmarès. La tête n'étant
        jamais discriminante, le départage se fait par `la_plus_avancee`.
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
            # fenêtres. On ne refuse pas la saisie sur une lecture de classement (robustesse jour
            # J) — on retombe sur « la phase en cours du créneau », le comportement d'avant. C'est
            # un repli **destructeur** (des flèches peuvent atterrir dans la mauvaise feuille), à la
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

        Le résolveur rend le classement que la phase **produit** : l'appartenance s'y lit sans
        redire les règles de prélèvement. **La phase de tête rend `True` sans rien lire** — elle
        accueille tout le créneau, et lui résoudre un classement serait la plus chère des lectures
        pour une réponse acquise. Best-effort : le filet couvre `ApplicationError` **et**
        `DomainError`, sans quoi un déroulé incohérent faisait tomber la saisie en 500.
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
        que
        l'un d'eux retombe sur la maille tournoi — c'est-à-dire au défaut que l'US corrige.
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

        `None` quand l'archer n'a aucune inscription — donnée incohérente, pas un cas nominal : on
        ne casse pas la saisie dessus le jour J. Le départage se fait sur le **plus petit
        identifiant** de créneau et non son numéro d'affichage : lire ce numéro exigerait un
        `DepartRepository` entier pour un départage sans enjeu. Ce qui compte est d'être
        **déterministe** ; le vrai remède est que la route porte le créneau (`# DETTE-052`).
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
