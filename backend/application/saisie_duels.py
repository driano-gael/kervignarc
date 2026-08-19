"""Service applicatif Saisie en duels — scorer un match du tableau (E04US013, ADR-0049).

Assemble ce que le domaine tient séparé : le **classement** (source d'ensemencement), l'**arbre**
d'élimination (`construire_tableau`, qui donne l'appariement), le **résolveur de barème** (par arme)
et l'agrégat **`Duel`** (le scoring). Le tableau n'est **pas** persisté (ADR-0023/0048) : il est
**reconstruit** du classement et **rejoué** des duels validés (`Tableau.jouer`) ; seul le **tir**
est persisté (`DuelRepository`). Le vainqueur d'un duel validé fait donc **avancer** le tableau à la
reconstruction suivante — c'est le sens de « transmis au moteur E05US005 ».

MVP (ADR-0049) : **ensemencement scratch**, tableau **tournoi-large** (les tableaux par catégorie
sont downstream). Le barème (et les zones du pavé) est résolu **par duel** depuis l'arme du **camp
haut** — en tableau par division les deux duellistes partagent la catégorie, donc la même arme ;
le bracket mixte-armes du MVP prend celle du haut (hypothèse d'homogénéité assumée). Résolveur FFTA
par défaut (cumul en poulies, sets sinon) ; E01US011 branchera les catalogues configurables au même
point d'injection. Les `Participant` de genre **équipe** sont ignorés (pas d'entité avant E13US002).
Le pont `Participant → archer` (nom, catégorie, blason) vit ici (couche haute, ADR-0028).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace

# ⚠️ **Le port `EvaluateurArrets` est importé de son *réalisateur*, pas défini ici** (E05US033).
# La convention du projet place un port étroit chez son **consommateur** (`LecteurAvancementDePhase`
# dans `application.suivi_deroule`, `DiffusionSimulation` dans `application.pilotage_simulation`).
# Elle est enfreinte sciemment : ce port a **deux** consommateurs — les deux services de saisie —,
# et le définir chez l'un obligerait l'autre à l'importer de son jumeau, ou à en tenir une copie.
# Un port en double se désaccorde ; un import de Protocol ne couple aucun comportement, et il n'y a
# pas de cycle (`arrets_programmes` n'importe aucun service de saisie).
from application.arrets_programmes import EvaluateurArrets
from application.classements import ServiceClassement
from application.erreurs import (
    BlasonIntrouvable,
    DerouleCyclique,
    DuelDesynchronise,
    PhaseEnPause,
    PhaseIntrouvable,
    PhasePasUnTableau,
    TournoiIntrouvable,
)
from application.portee import phase_du_tournoi
from application.prelevement import (
    LecteurClassementDePhase,
    ResolveurClassement,
    preleves,
    profondeur_de,
    tranche,
)
from domain.blason import ZoneScore
from domain.classement import LigneClassement
from domain.classement_de_tableau import ClassementSource, classement_de_tableau
from domain.contrat_phase import TYPES_CLASSANTS_LUS, TYPES_EN_TABLEAU_JOUE
from domain.depart import DepartId
from domain.duel import BaremeDuel, Cote, Duel, ResolveurBaremeDuel
from domain.erreurs import MatchNonJouable
from domain.participant import GenreParticipant, Participant
from domain.phase import PhaseId, StatutPhase, TypePhase
from domain.politiques import (
    Aggregation,
    Byes,
    RegistrePolitiques,
    Routing,
    Seeding,
)
from domain.ports import (
    BlasonRepository,
    CategorieRepository,
    DuelRepository,
    ForfaitRepository,
    PhaseRepository,
    TournoiRepository,
)
from domain.tableau import Match, Tableau, construire_tableau, libelle_tour
from domain.tournoi import TournoiId

_TYPES_RESOLUS_SUR_PLACE: frozenset[TypePhase] = frozenset(
    {TypePhase.QUALIFICATION, TypePhase.ELIMINATION_DIRECTE}
)
"""Les deux types dont ce service produit lui-même le classement, sans passer par un port.

Ce ne sont pas des formats « à part » : ce sont ceux dont la lecture ne demande **rien de plus**
que ce que ce service a déjà en main — le classement de tir pour l'une, l'arbre qu'il reconstruit
pour l'autre. Les autres formats demandent le réglage, le plan et les tirs de leur phase, soit
trois repositories qu'un service de tableau n'a aucune raison de connaître : d'où la délégation.
"""

TYPES_DELEGUES: frozenset[TypePhase] = TYPES_CLASSANTS_LUS - _TYPES_RESOLUS_SUR_PLACE
"""Les types dont le classement est lu par un `LecteurClassementDePhase` branché ([ADR-0084]).

**Dérivé du registre de contrat**, pas énuméré à la main : un format qui devient
`classement_lisible` entre ici automatiquement, et le composition root doit alors lui brancher son
lecteur — le test de câblage le vérifie. C'est la promesse d'ADR-0083 appliquée à ce site-ci.

[ADR-0084]: ../../docs/adr/0084-un-seul-port-de-lecture-de-classement-resolu-par-type.md
"""


_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Duelliste:
    """Un duelliste **résolu** pour l'affichage : son archer et son nom (depuis le classement)."""

    archer_id: int
    nom: str
    prenom: str


@dataclass(frozen=True)
class EtatDuel:
    """L'état d'un match du tableau : son câblage, ses occupants résolus et son tir (`duel`).

    `duel` est `None` tant qu'aucun tir n'y est saisi ; sinon il porte manches, barrage et résultat
    (`duel.resultat`). `est_bye` marque un match gagné d'office (pas de duel à saisir).

    `bareme` et `zones` dimensionnent le **pavé de saisie** du front (nombre de manches, de flèches,
    zones légales du blason tiré — E04US002 les expose déjà pour la qualif) : disponibles dès qu'un
    match est **jouable** (deux occupants connus, pas un bye), **avant** tout tir, pour que la
    grille sache d'emblée sets ou cumul. `bareme` est `None` et `zones` vide pour un bye ou un
    match dont les occupants ne sont pas encore connus.
    """

    numero: int
    tour: int
    place_en_jeu: tuple[int, int] | None
    haut: Duelliste | None
    bas: Duelliste | None
    est_bye: bool
    duel: Duel | None
    bareme: BaremeDuel | None = None
    zones: tuple[ZoneScore, ...] = ()
    plage: tuple[int, int] | None = field(default=None, kw_only=True)
    """La **branche** du match — `[1..8]` pour le tableau principal, `[5..8]` pour le sous-tableau
    de placement qui en descend (E07US005).

    Distincte de `place_en_jeu`, et c'est **tout l'intérêt** : `place_en_jeu` n'existe que sur les
    matchs **terminaux**, si bien qu'un match des places 5-8 disputé au tour d'une demi-finale
    n'avait, avant cette US, aucun champ qui le distinguât d'une demi-finale. Tout consommateur
    qui nommait ce match par son seul numéro de tour l'appelait « Demi-finale ». C'est ce que
    `libelle` ci-dessous corrige — et pourquoi la plage doit remonter jusqu'ici."""
    libelle: str = field(kw_only=True)
    """Le nom que la salle donne au match, calculé par `domain.tableau.libelle_tour`.

    Porté par l'application plutôt que recalculé par chaque surface : c'est du **vocabulaire
    métier** (règle 3), il n'a qu'un domicile légitime, le domaine (`DETTE-020`).

    **Sans défaut** (`kw_only`, correctif de revue) : le DTO public le sert comme `str` obligatoire,
    et un défaut vide aurait publié un titre de section vide — que le repli `?? '—'` du front ne
    rattrape pas, puisqu'il ne teste que `null`. `kw_only` permet un champ obligatoire **après** des
    champs à défaut, sans réordonner la dataclass."""


@dataclass(frozen=True)
class EtatTableau:
    """La photo du tableau reconstruit : ses matchs (avec tir), son podium acquis, sa complétude.

    `phase_id` a été ajouté par E01US024 : sans lui, tout appelant qui reçoit **plusieurs** tableaux
    devait les rapparier à leurs phases **par position** — or `_tableaux` (pilotage de simulation)
    **saute** une phase non encore jouable, ce qui décalait silencieusement toute la suite. Un
    identifiant porté par la donnée supprime la classe entière de ces bugs d'appariement.
    """

    phase_id: PhaseId
    effectif: int
    taille: int
    nb_tours: int
    est_termine: bool
    duels: tuple[EtatDuel, ...]
    podium: tuple[tuple[int, Duelliste], ...]


class ServiceSaisieDuels:
    """Cas d'usage de la saisie en duels : consulter le tableau, saisir un duel, le valider."""

    def __init__(
        self,
        tournois: TournoiRepository,
        phases: PhaseRepository,
        categories: CategorieRepository,
        blasons: BlasonRepository,
        duels: DuelRepository,
        forfaits: ForfaitRepository,
        classements: ServiceClassement,
        resolveur: ResolveurBaremeDuel,
        seeding: Seeding,
        byes: Byes,
        routing: Routing,
        registre: RegistrePolitiques,
        aggregation: Aggregation,
    ) -> None:
        self._tournois = tournois
        self._phases = phases
        self._categories = categories
        self._blasons = blasons
        self._duels = duels
        self._forfaits = forfaits
        self._classements = classements
        self._resolveur = resolveur
        # Politiques du tableau (E05US003) : le format est de la configuration (règle 2). MVP =
        # défauts (serpent / byes aux mieux classés / élimination sèche), comme le plan de duels.
        self._seeding = seeding
        self._byes = byes
        self._routing = routing
        # Profondeur lue **sur la phase** depuis E06US006 (`profondeur_de`), comme le plan de
        # duels : les deux montent le même arbre, ils ne peuvent pas le tronquer différemment.
        self._registre = registre
        # E05US024 : ferme les fourchettes *ex æquo* d'un tableau amont pour qu'une phase aval
        # puisse y prélever par rangs. Même patron d'injection que `ServicePalmares` — et **la même
        # politique doit y être câblée**, sinon un archer entrerait dans la consolante par un ordre
        # que le palmarès contredirait le même jour, sur le même écran.
        #
        # ⚠️ **Paramètre obligatoire, sans défaut** (correctif de revue, relevé par les quatre
        # axes). Un premier jet le laissait optionnel avec un `AggregationParQualification()`
        # instancié en dur ici — et **aucun** des deux composition roots ne le câblait. L'invariant
        # ci-dessus n'était donc tenu que par la coïncidence des deux valeurs : le jour où le
        # palmarès résout `ex_aequo`, la saisie serait restée sur `par_qualification` sans que rien
        # ne rougisse. Le typage est désormais le garde-fou — un oubli de câblage ne construit plus.
        self._aggregation = aggregation
        # Les classements que ce service ne sait pas produire lui-même, délégués par type au
        # service du format ([ADR-0084]). Branchés **après** construction (`brancher_lecteur`)
        # parce que ces services reçoivent celui-ci dans leur propre constructeur : les deux côtés
        # se tiennent par les deux bouts, et aucun ordre de construction ne les satisfait.
        #
        # ⚠️ Une entrée **absente** n'est pas un défaut de câblage silencieux : c'est le régime
        # légitime de tout montage qui n'a pas ce format — le harnais de simulation, les tests de
        # tableau. Le prix est que l'oubli au composition root ne construit pas moins bien, il
        # *lit* moins bien ; le test de câblage `test_composition` est donc le garde-fou, pas le
        # typage.
        #
        # [ADR-0084]: ../../docs/adr/0084-un-seul-port-de-lecture-de-classement-resolu-par-type.md
        self._lecteurs: dict[TypePhase, LecteurClassementDePhase] = {}
        # E05US033 : branché **tardivement** (`brancher_evaluateur_arrets`), donc `None` ici.
        self._evaluateur_arrets: EvaluateurArrets | None = None

    def brancher_lecteur(self, type_phase: TypePhase, lecteur: LecteurClassementDePhase) -> None:
        """Donne à ce service de quoi lire le classement d'un type de phase ([ADR-0084]).

        Appelé **une fois par format, au composition root** (règle 8), juste après la construction
        du service concerné. Sans branchement, une source visant ce type reste inerte — exactement
        le comportement d'avant que le format ne soit jouable, donc sûr par défaut.

        ⚠️ **Refuse un type que le registre de contrat ne dit pas lisible.** `classement_lisible`
        (`domain/contrat_phase.py`, ADR-0083) est la source unique de « sait-on lire ce que cette
        phase a classé ? » ; brancher un lecteur pour un type qui l'a à `False` ferait diverger le
        câblage du registre, c'est-à-dire exactement le défaut qu'ADR-0083 s'est donné pour tâche
        de rendre **impossible** plutôt qu'improbable. C'est une erreur de programmation, pas une
        donnée d'exécution : elle casse au démarrage, pas en salle.
        """
        if type_phase not in TYPES_DELEGUES:
            raise ValueError(
                f"Le type de phase « {type_phase.value} » n'attend aucun lecteur : il n'est pas "
                "déclaré `classement_lisible` au registre de contrat, ou ce service produit son "
                "classement lui-même (ADR-0083)."
            )
        self._lecteurs[type_phase] = lecteur

    # --- Lecture -------------------------------------------------------------------------------

    def etat_tableau(self, tournoi_id: TournoiId, phase_id: PhaseId) -> EtatTableau:
        """Reconstruit le tableau (duels validés rejoués) et renvoie ses matchs + podium."""
        tableau, lignes = self._decor(tournoi_id, phase_id)
        duels = tuple(
            self._etat_du_match(m, phase_id, lignes, tableau.nb_tours) for m in tableau.matchs
        )
        podium = tuple(
            (place.rang, duelliste)
            for place in tableau.podium()
            if (duelliste := self._duelliste(place.participant, lignes)) is not None
        )
        return EtatTableau(
            phase_id=phase_id,
            effectif=tableau.effectif,
            taille=tableau.taille,
            nb_tours=tableau.nb_tours,
            est_termine=tableau.est_termine,
            duels=duels,
            podium=podium,
        )

    def etat_duel(self, tournoi_id: TournoiId, phase_id: PhaseId, match_numero: int) -> EtatDuel:
        """L'état d'un match précis (câblage, occupants, tir). `MatchIntrouvable` si rang absent."""
        tableau, lignes = self._decor(tournoi_id, phase_id)
        return self._etat_du_match(tableau.match(match_numero), phase_id, lignes, tableau.nb_tours)

    def reconstruire(
        self, tournoi_id: TournoiId, phase_id: PhaseId
    ) -> tuple[Tableau, dict[int, LigneClassement]]:
        """Reconstruit le tableau (duels validés **rejoués**, forfaits **appliqués**) pour un
        lecteur externe — le **pilotage du tour** (E12US002, feu vert) — avec le classement (noms).

        Même décor que la saisie (`_decor`), simplement **exposé en lecture** : le pilotage a besoin
        du `Tableau` brut (occupants connus, vainqueurs propagés, câblage des sources) pour dire,
        par duel à venir, ce qui manque avant de lancer. On ne duplique donc pas la reconstruction —
        une
        seule source de vérité de la progression, comme la saisie et le placement partagent l'arbre.
        Mêmes gardes que `_decor` (`TournoiIntrouvable` / `PhaseIntrouvable` / `PhasePasUnTableau`).
        """
        return self._decor(tournoi_id, phase_id)

    def duelliste(
        self, participant: Participant | None, lignes: dict[int, LigneClassement]
    ) -> Duelliste | None:
        """Résout un participant en `Duelliste` (nom du classement), pour un lecteur externe.

        Expose la même résolution que la saisie applique à ses propres occupants (le pilotage
        affiche les mêmes noms) — `None` pour un camp vide ou une équipe (hors périmètre, E13US002).
        """
        return self._duelliste(participant, lignes)

    # --- Écritures (via la file) ---------------------------------------------------------------

    def saisir_manche(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        match_numero: int,
        numero: int,
        valeurs_haut: tuple[ZoneScore, ...],
        valeurs_bas: tuple[ZoneScore, ...],
    ) -> EtatDuel:
        """Saisit (ou réédite) une manche d'un match : les deux volées opposées."""
        self._refuser_si_en_pause(tournoi_id, phase_id)
        tableau, lignes = self._decor(tournoi_id, phase_id)
        match, haut, bas = self._match_saisissable(tableau, match_numero)
        bareme = self._bareme_du(haut, lignes)
        zones = self._zones_du(haut, lignes)
        duel = self._duel_courant(phase_id, match_numero, bareme, haut, bas)
        duel = duel.saisir_manche(
            numero,
            valeurs_haut,
            valeurs_bas,
            zones_admises=zones,
            nb_fleches_par_volee=bareme.nb_fleches_par_volee,
        )
        self._duels.enregistrer(phase_id, match_numero, duel)
        return self._etat_du_match(match, phase_id, lignes, tableau.nb_tours, duel=duel)

    def saisir_barrage(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        match_numero: int,
        fleche_haut: ZoneScore,
        fleche_bas: ZoneScore,
        gagnant_designe: Cote | None = None,
    ) -> EtatDuel:
        """Saisit le tir de barrage d'un match à égalité (§8.2)."""
        self._refuser_si_en_pause(tournoi_id, phase_id)
        tableau, lignes = self._decor(tournoi_id, phase_id)
        match, haut, bas = self._match_saisissable(tableau, match_numero)
        bareme = self._bareme_du(haut, lignes)
        zones = self._zones_du(haut, lignes)
        duel = self._duel_courant(phase_id, match_numero, bareme, haut, bas)
        duel = duel.saisir_barrage(
            fleche_haut, fleche_bas, zones_admises=zones, gagnant_designe=gagnant_designe
        )
        self._duels.enregistrer(phase_id, match_numero, duel)
        return self._etat_du_match(match, phase_id, lignes, tableau.nb_tours, duel=duel)

    def valider(
        self, tournoi_id: TournoiId, phase_id: PhaseId, match_numero: int, scoreur: str
    ) -> EtatDuel:
        """Valide un match **tranché** au nom du scoreur : son vainqueur avancera le tableau."""
        self._refuser_si_en_pause(tournoi_id, phase_id)
        tableau, lignes = self._decor(tournoi_id, phase_id)
        match, haut, bas = self._match_saisissable(tableau, match_numero)
        bareme = self._bareme_du(haut, lignes)
        duel = self._duel_courant(phase_id, match_numero, bareme, haut, bas)
        duel = duel.valider(scoreur)
        self._duels.enregistrer(phase_id, match_numero, duel)
        # Le duel est **écrit** : c'est maintenant qu'un tour de tableau peut être achevé
        # (E05US033). ⚠️ Ici et non dans `saisir_manche` / `saisir_barrage` : un braquet n'avance
        # que sur des duels **tranchés et validés** (`AvancementTour`, ADR-0090), donc une manche
        # saisie ne franchit aucune frontière de tour. Y appeler le déclencheur aurait payé la
        # recomposition du créneau à chaque volée de duel pour un résultat toujours identique
        # (`DETTE-031`).
        phase = phase_du_tournoi(self._phases, tournoi_id, phase_id)
        if phase is not None:
            self._signaler_validation(phase.depart_id)
        return self._etat_du_match(match, phase_id, lignes, tableau.nb_tours, duel=duel)

    def brancher_evaluateur_arrets(self, evaluateur: EvaluateurArrets) -> None:
        """Dit à qui signaler qu'un résultat vient d'être validé (E05US033, ADR-0091).

        Branchement **tardif et visible** au composition root, sur le patron de
        `ServiceSuiviDeroule.brancher_lecteur_avancement` (ADR-0090) et de
        `ServiceSaisieDuels.brancher_lecteur` (ADR-0084) : le service d'arrêts est construit après
        celui-ci — il consomme le suivi, qui consomme les services de format — et un cycle qu'on ne
        voit pas est un cycle qu'on réintroduit.

        Non branché, ce service se comporte **exactement** comme avant E05US033 : aucun arrêt ne se
        déclenche. C'est ce qui rend les décors de test existants indifférents à cette US, et c'est
        aussi le mode de panne à connaître — un branchement oublié rend toute l'US inerte sans
        qu'une seule ligne rougisse (`DETTE-028`, six moteurs livrés dont aucun appelé).
        """
        self._evaluateur_arrets = evaluateur

    def _signaler_validation(self, depart_id: DepartId) -> None:
        """Fait évaluer les arrêts programmés du créneau après une validation (E05US033).

        ⚠️ **Appelé après l'écriture, jamais avant.** L'arrêt se déclenche sur un tour *achevé* :
        évaluer avant que le résultat soit persisté ferait lire l'avancement d'avant, donc manquer
        la frontière de tour — et le suivant l'attraperait, avec un tour de retard visible en salle.

        ⚠️ **Les erreurs du déclencheur ne remontent pas au scoreur.** La validation, elle, a réussi
        : faire échouer la requête parce qu'une phase voisine a été clôturée entre-temps rendrait un
        500 à un archer qui a bien tiré, et lui ferait ressaisir une volée déjà enregistrée. On
        journalise et l'on rend la main ; la validation suivante réévaluera, le déclencheur étant
        idempotent.
        """
        if self._evaluateur_arrets is None:
            return
        try:
            self._evaluateur_arrets.evaluer(depart_id)
        except Exception as exc:
            # ⚠️ **`Exception` et non le triplet typé habituel**, et c'est un choix, pas un
            # raccourci. Le tuple `(ApplicationError, DomainError)` — celui de
            # `ServiceSuiviDeroule._avancement_lu` — laisserait passer une `InfrastructureError`
            # (SQLite occupé, base altérée), et l'attraper nommément demanderait à cette couche
            # d'importer `infrastructure`, donc d'inverser le sens des dépendances (règle 2) pour
            # une seule ligne de `except`. Le vrai argument est ailleurs : la validation **a réussi
            # et est persistée**. Toute exception d'ici est celle d'un *effet de bord*, et la
            # laisser remonter rendrait un 500 à un archer qui a bien tiré — qui ressaisirait alors
            # une volée déjà enregistrée. Le déclencheur étant idempotent, la validation suivante
            # réévaluera : le pire coût est une pause qui tombe un résultat plus tard.
            _logger.warning(
                "Arrêts programmés non évalués après validation sur le créneau %s : %r",
                depart_id,
                exc,
            )

    def _refuser_si_en_pause(self, tournoi_id: TournoiId, phase_id: PhaseId) -> None:
        """Refuse un résultat **neuf** sur une phase en pause (E05US033) — `PhaseEnPause`, 409.

        ⚠️ **La garde est aux trois écritures, pas dans `_decor`**, et c'est le point à ne pas
        simplifier. `_decor` est le passage obligé des écritures **et** des lectures (sept appels,
        dont l'état d'un match, la grille et la reconstruction récursive d'une phase amont) : y
        poser le refus rendrait le tableau **illisible** pendant la pause — le pilotage, l'écran de
        salle et l'affichage public tomberaient tous les trois, au moment précis où l'organisateur
        a besoin de voir où il en est.

        ⚠️ **Les duels n'ont aucun chemin de correction**, à la différence de la qualification
        (`ServiceSaisie.corriger_volee`). Le CA « une correction reste possible pendant la pause »
        est donc sans objet ici : il n'y a rien à préserver. C'est un manque **préexistant** — un
        duel validé de travers ne se rectifie nulle part aujourd'hui —, ni introduit ni aggravé par
        cette US, et signalé pour ce qu'il est plutôt que passé sous silence.
        """
        phase = phase_du_tournoi(self._phases, tournoi_id, phase_id)
        if phase is not None and phase.statut is StatutPhase.EN_PAUSE:
            raise PhaseEnPause(
                "Cette phase est en pause : les duels reprendront quand l'organisateur relancera."
            )

    # --- Interne : reconstruction du décor (classement → arbre → rejeu des duels validés) -------

    def _decor(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        _chaine: tuple[PhaseId, ...] = (),
        _cache: dict[int, ClassementSource | None] | None = None,
    ) -> tuple[Tableau, dict[int, LigneClassement]]:
        """Valide les gardes puis reconstruit l'arbre, duels validés **rejoués** (progression).

        `_chaine` porte les phases déjà en cours de reconstruction dans la descente courante
        (E05US024) : une phase qui prélève dans un tableau amont fait reconstruire celui-ci, qui
        peut
        à son tour en prélever un autre. Elle ne sert qu'à refuser un déroulé qui bouclerait —
        impossible par la composition, possible par une base incohérente.
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        phase = phase_du_tournoi(self._phases, tournoi_id, phase_id)
        if phase is None:
            raise PhaseIntrouvable(f"Aucune phase {phase_id} dans le tournoi {tournoi_id}.")
        # Filtre **dérivé** du contrat de phase (ADR-0083) : ce service ne sait dérouler qu'un
        # arbre de duels monté par un service. Les rencontres de poule se saisissent avec le même
        # *pavé* (une rencontre est un duel ordinaire) mais dans un autre **décor**, donc par
        # `ServicePoules` — la distinction est portée une fois, dans le registre.
        if phase.type not in TYPES_EN_TABLEAU_JOUE:
            raise PhasePasUnTableau(
                f"La phase {phase_id} n'est pas une élimination directe : pas de duels."
            )
        # Le classement **du départ de cette phase** (ADR-0075) : ensemencer un tableau avec les
        # rangs tous créneaux confondus y ferait entrer des archers qui ne tirent pas ici.
        # Le cache est **créé au sommet et descendu** dans toute la récursion (correctif de revue,
        # axe C2). Créé par niveau, il ne servait qu'à l'intérieur d'un appel : sur un déroulé en
        # **diamant** (une super-finale nourrie par le principal *et* la consolante, tous deux nés
        # du même tableau), la phase commune était reconstruite une fois par chemin — coût
        # exponentiel en profondeur, là où le registre et l'ADR annonçaient « fois la profondeur ».
        cache: dict[int, ClassementSource | None] = {} if _cache is None else _cache
        classement = self._classements.pour_depart(phase.depart_id)
        lignes = {ligne.archer_id: ligne for ligne in classement.lignes}
        # Le classement du départ vient d'être calculé : on l'installe au cache pour que la source
        # visant la qualification ne le recalcule pas (`ServiceClassement.pour_depart` n'est pas
        # mémoïsé — 7 accès repository, cf. `DETTE-031`). Sans ça, tout déroulé composé depuis
        # E01US024 le payait **deux fois** par reconstruction, sur le thread écrivain unique.
        # Sous `if phase.sources` : sans source déclarée, `preleves` n'appelle jamais le résolveur
        # et l'entrée de cache est pure perte — un SELECT de plus par saisie de manche, sur le
        # thread écrivain unique, pour le cas de la quasi-totalité des phases (relevé en revue).
        qualification = next(
            (
                p
                for p in self._phases.par_depart(phase.depart_id)
                if p.type is TypePhase.QUALIFICATION
            ),
            None,
        )
        if phase.sources and qualification is not None and qualification.ordre not in cache:
            cache[qualification.ordre] = ClassementSource(classement=classement)
        # Ensemencement : **seuls les archers en lice** entrent dans le tableau. Un forfait déclaré
        # en **qualification** (abandon relégué / DSQ exclu, `statut != EN_LICE`) n'accède pas aux
        # duels ; son rang scratch peut d'ailleurs être `None` (DSQ). Le classement complet reste
        # dans `lignes` pour résoudre les noms.
        participants = [
            Participant.individuel(ligne.archer_id)
            for ligne in preleves(
                phase,
                classement,
                self.resolveur_de_classement(
                    tournoi_id, phase.depart_id, (*_chaine, phase_id), cache
                ),
            )
        ]
        tableau = construire_tableau(
            participants,
            self._seeding,
            self._byes,
            self._routing,
            profondeur_de(phase, self._registre),
        )
        tableau = self._rejouer(tableau, phase_id, lignes)
        return self._appliquer_forfaits(tableau, phase_id), lignes

    def resolveur_de_classement(
        self,
        tournoi_id: TournoiId,
        depart_id: DepartId,
        _chaine: tuple[PhaseId, ...] = (),
        _cache: dict[int, ClassementSource | None] | None = None,
    ) -> ResolveurClassement:
        """De quoi lire le classement de **n'importe quelle** phase amont de ce créneau (E05US024).

        Remplace `_ordre_de_la_qualification`, qui ne désignait qu'un seul ordre lisible : toute
        autre source était ignorée en silence et la phase recevait *tous* les archers en lice.

        **Exposé** (et non privé) parce que `ServicePlacementDuels` doit lire **exactement** la même
        chose : les deux services ensemencent le même arbre, l'un pour dire qui affronte qui,
        l'autre
        où ils tirent. C'est la raison d'être d'`application/prelevement.py`, et l'écart mesuré à la
        revue d'E05US020 — plan de 8 placements pour un tableau de 4 — est ce qui arrive quand la
        règle est recopiée au lieu d'être partagée.

        **Mémoïsé sur toute la descente** : le cache est créé au sommet et **transmis** aux niveaux
        inférieurs, si bien qu'une phase amont partagée par deux chemins n'est reconstruite qu'une
        fois. Le coût est donc linéaire en **nombre de phases** de la chaîne, quelle que soit la
        forme du graphe de sources — et non en nombre de chemins, comme le faisait un premier jet
        (correctif de revue, axe C2). Le cache **transverse aux requêtes** reste `DETTE-031`, que
        cette US ne rouvre pas.
        """
        cache: dict[int, ClassementSource | None] = {} if _cache is None else _cache

        def resoudre(ordre: int) -> ClassementSource | None:
            if ordre not in cache:
                cache[ordre] = self._classement_de_l_ordre(
                    tournoi_id, depart_id, ordre, _chaine, cache
                )
            return cache[ordre]

        return resoudre

    def _classement_de_l_ordre(
        self,
        tournoi_id: TournoiId,
        depart_id: DepartId,
        ordre: int,
        chaine: tuple[PhaseId, ...],
        cache: dict[int, ClassementSource | None],
    ) -> ClassementSource | None:
        """Le classement produit par la phase de cet `ordre` **dans ce créneau**, ou `None`.

        Quatre cas, et le dernier compte autant que les trois autres :

        1. **qualification** — le classement de tir du départ (ADR-0075 : jamais tous créneaux
           confondus, ce qui y ferait entrer des archers qui ne tirent pas ici) ;
        2. **élimination directe** — l'arbre reconstruit, lu comme un classement
           (`domain/classement_de_tableau.py`). C'est ici que le service **s'appelle lui-même** ;
        3. **tout type délégué** (`TYPES_DELEGUES` — poules, Big Shoot Off, système suisse) — le
           classement est produit par le service du format et lu par le port
           `LecteurClassementDePhase`, [ADR-0084]. Le service n'y touche pas lui-même : rejouer une
           de ces phases demande son réglage, son plan et ses tirs, c'est-à-dire trois repositories
           qu'un service de tableau n'a aucune raison de connaître ;
        4. **tout autre type** — `None`. C'est aussi la réponse quand le type est délégué mais
           qu'**aucun lecteur n'est branché** : le montage n'a pas ce format. Rendre `None` fait
           retomber la phase sur son comportement d'avant plutôt que d'inventer un ordre — le
           prélèvement reste **inerte**, pas faux.

        ⚠️ **La cascade était écrite un type par branche jusqu'à E05US026**, et les deux dernières
        étaient identiques au type près. C'est la duplication qu'[ADR-0084] a refermée sur sa 3ᵉ
        occurrence : ajouter la colline (`E05US027`) ne demandera plus de brancher ici.

        [ADR-0084]: ../../docs/adr/0084-un-seul-port-de-lecture-de-classement-resolu-par-type.md
        """
        phase = next((p for p in self._phases.par_depart(depart_id) if p.ordre == ordre), None)
        if phase is None:
            return None
        if phase.type is TypePhase.QUALIFICATION:
            # Un classement de qualification n'a **aucune plage indécise** : les rangs de tir sont
            # fermes dès que les volées sont validées.
            #
            # ⚠️ **Mais il ne dispute plus forcément le tournoi entier** (E05US025, ADR-0082). Ce
            # bloc rendait `pour_depart(depart_id)` — le classement de la qualification de tête —
            # pour **toute** phase de type qualification, quel que soit son ordre. Sur le déroulé de
            # référence, la *haute* et la *basse* auraient donc toutes deux relu le classement du
            # premier tour : leurs 3x15 n'auraient servi à rien, et les deux auraient prélevé dans
            # les mêmes rangs. C'était le vrai câblage à casser, bien plus que les appels de portée.
            if not phase.sources:
                # La qualification de tête : tous les inscrits, elle dispute le tournoi entier.
                return ClassementSource(classement=self._classements.pour_depart(depart_id))
            # Une qualification **prélevée** : sa population est ce que ses sources lui ont donné,
            # et elle dispute la tranche de rangs correspondante. Le résolveur passé à `preleves` et
            # à `tranche` est **le même** (cache compris) : deux bases différentes situeraient la
            # population et le décalage dans deux espaces de rangs distincts, ce qui est exactement
            # `DETTE-034`.
            resolveur = self.resolveur_de_classement(
                tournoi_id,
                depart_id,
                (*chaine, phase.id) if phase.id is not None else chaine,
                cache,
            )
            admis = [
                ligne.archer_id
                for ligne in preleves(phase, self._classements.pour_depart(depart_id), resolveur)
            ]
            return ClassementSource(
                classement=self._classements.pour_phase(depart_id, phase, admis=admis),
                rang_premier=tranche(phase, resolveur),
            )
        if phase.type in TYPES_DELEGUES and phase.id is not None:
            lecteur = self._lecteurs.get(phase.type)
            if lecteur is None:
                # Aucun lecteur branché pour ce type : ce montage n'a pas ce format (harnais de
                # simulation, test de tableau). On retombe sur le comportement d'avant que le
                # format ne soit jouable — inerte, pas faux.
                return None
            if phase.id in chaine:
                raise DerouleCyclique(
                    f"Le déroulé boucle sur la phase {phase.id} : une phase ne peut pas se "
                    "prélever elle-même, directement ou par une chaîne de sources."
                )
            # Le résolveur **descendant** porte le cache et la chaîne : le service du format remonte
            # à son tour ses sources, et une phase amont partagée n'est reconstruite qu'une fois.
            return lecteur.classement_de_phase(
                tournoi_id,
                phase.id,
                self.resolveur_de_classement(tournoi_id, depart_id, (*chaine, phase.id), cache),
            )
        if phase.type is not TypePhase.ELIMINATION_DIRECTE or phase.id is None:
            return None
        if phase.id in chaine:
            # Inatteignable par la composition : `verifier_sequence` exige qu'une source soit
            # **antérieure**, donc le déroulé est acyclique. La garde vise une base incohérente
            # (import, migration à la main) : mieux vaut un refus typé qu'un `RecursionError` en
            # salle, qui remonterait en 500 sans rien dire de la cause.
            raise DerouleCyclique(
                f"Le déroulé boucle sur la phase {phase.id} : une phase ne peut pas se prélever "
                "elle-même, directement ou par une chaîne de sources."
            )
        # `_decor` ajoute lui-même `phase.id` à la chaîne : lui passer `chaine` **sans** l'ajouter
        # ici évite de l'y voir deux fois (sans effet sur le test d'appartenance, mais trompeur).
        tableau, lignes = self._decor(tournoi_id, phase.id, chaine, cache)
        descendante = (*chaine, phase.id)
        # Le rang de tournoi que dispute **ce tableau-ci**, pour que le décalage se cumule chez son
        # aval (ADR-0081) : un tableau des places 33+ doit dire à sa consolante que son rang 1 vaut
        # 33. Le résolveur partage le cache, la remontée ne recalcule donc rien.
        return replace(
            classement_de_tableau(tableau, lignes, self._aggregation),
            rang_premier=tranche(
                phase,
                self.resolveur_de_classement(tournoi_id, depart_id, descendante, cache),
            ),
        )

    def _appliquer_forfaits(self, tableau: Tableau, phase_id: PhaseId) -> Tableau:
        """Fait **passer l'adversaire** de tout duelliste déclaré forfait **dans cette phase de
        tableau** (E04US015 / ADR-0050, ex-E12US004).

        Un forfait en duels est un **walkover** : l'archer garde ses duels déjà validés (rejoués
        avant), mais tout match **jouable et non encore tranché** où il figure est gagné d'office
        par son adversaire — analogue à la résolution d'un bye. On traite par **tour croissant**
        (un tour ≥ 2 n'a ses occupants qu'après propagation amont). L'annulation du forfait fait
        **disparaître** le walkover à la reconstruction suivante (réversibilité, `D-15`). Deux
        forfaits face à face (rare) : le camp **haut** avance par convention — lui-même walkover
        en aval s'il reste forfait. Les forfaits de **qualification** ne passent pas ici : leurs
        archers ne sont pas dans le tableau (exclus à l'ensemencement).
        """
        forfaits = {f.archer_id for f in self._forfaits.par_phase(phase_id)}
        if not forfaits:
            return tableau
        for numero in sorted(
            (m.numero for m in tableau.matchs), key=lambda n: tableau.match(n).tour
        ):
            match = tableau.match(numero)
            if (
                match.est_bye
                or match.haut is None
                or match.bas is None
                or match.vainqueur is not None
            ):
                continue
            haut_forfait = match.haut.ref_id in forfaits
            bas_forfait = match.bas.ref_id in forfaits
            if haut_forfait and not bas_forfait:
                tableau = tableau.jouer(numero, match.bas)
            elif (bas_forfait and not haut_forfait) or (haut_forfait and bas_forfait):
                tableau = tableau.jouer(numero, match.haut)
        return tableau

    def _rejouer(
        self, tableau: Tableau, phase_id: PhaseId, lignes: dict[int, LigneClassement]
    ) -> Tableau:
        """Rejoue les duels **validés** dans l'ordre des tours pour peupler les tours ≥ 2.

        Un tour ≥ 2 ne connaît ses occupants qu'une fois les vainqueurs amont propagés : on traite
        donc les matchs **par tour croissant**. On ne rejoue qu'un duel **validé** (officiel) et
        tranché — un tir non validé n'avance pas le tableau (comme le cumul de qualif ne compte que
        le validé). Un tir dont les **duellistes enregistrés divergent** des occupants (le
        classement a changé depuis) est **ignoré**, jamais rejoué pour d'autres archers (ADR-0049
        §4) ; un `match_numero` **hors tableau** (effectif rétréci) est écarté avant tout accès.
        """
        numeros = self._duels.numeros_enregistres(phase_id)
        valides = {m.numero for m in tableau.matchs}
        for numero in sorted(numeros & valides, key=lambda n: tableau.match(n).tour):
            match = tableau.match(numero)
            if match.est_bye or match.haut is None or match.bas is None:
                continue
            bareme = self._bareme_du(match.haut, lignes)
            duel = self._duels.charger(phase_id, numero, bareme=bareme)
            if duel is None or duel.validee_par is None:
                continue
            if (duel.participant_haut, duel.participant_bas) != (match.haut, match.bas):
                continue  # divergence : le tir oppose d'autres duellistes, on ne le rejoue pas
            vainqueur = duel.vainqueur
            if vainqueur is not None:
                tableau = tableau.jouer(numero, vainqueur)
        return tableau

    # --- Interne : accès à un match / au duel courant ------------------------------------------

    @staticmethod
    def _match_saisissable(
        tableau: Tableau, match_numero: int
    ) -> tuple[Match, Participant, Participant]:
        """Le match et ses deux occupants connus, ou `MatchNonJouable` (bye / adversaires inconnus).

        On **n'exige pas** l'absence de vainqueur : un match déjà validé garde ses occupants et
        c'est l'agrégat `Duel` qui refuse la réécriture (`DuelVerrouille`)."""
        match = tableau.match(match_numero)  # MatchIntrouvable si le rang n'existe pas
        if match.est_bye:
            raise MatchNonJouable(f"Le match {match_numero} est un bye : pas de duel à saisir.")
        if match.haut is None or match.bas is None:
            raise MatchNonJouable(
                f"Les adversaires du match {match_numero} ne sont pas encore connus."
            )
        return match, match.haut, match.bas

    def _duel_courant(
        self,
        phase_id: PhaseId,
        match_numero: int,
        bareme: BaremeDuel,
        haut: Participant,
        bas: Participant,
    ) -> Duel:
        """Le duel persisté du match, ou un duel vierge (première saisie).

        **Refuse** (`DuelDesynchronise`, 409) un tir qui oppose d'**autres** duellistes que
        `(haut, bas)` recalculés : le classement a changé depuis, on n'écrit pas un score sur le
        mauvais couple (ADR-0049 §4). À première saisie (aucun tir), le duel vierge porte les
        occupants courants, qui seront enregistrés.
        """
        duel = self._duels.charger(phase_id, match_numero, bareme=bareme)
        if duel is None:
            return Duel.vide(bareme, haut, bas)
        if (duel.participant_haut, duel.participant_bas) != (haut, bas):
            raise DuelDesynchronise(
                f"Le tir du match {match_numero} oppose d'autres duellistes : le classement a "
                "changé depuis. Régénérez ou rétablissez le classement avant de saisir."
            )
        return duel

    # --- Résolution de pavé, **partagée** ------------------------------------------------------

    def bareme_de(self, participant: Participant, lignes: dict[int, LigneClassement]) -> BaremeDuel:
        """Le barème d'un duel, résolu par l'arme du participant — **exposé** pour `ServicePoules`.

        Même motif que `resolveur_de_classement` : une rencontre de poule *est* un duel ordinaire
        (ADR-0083 §7), donc son pavé doit être résolu par le **même** code, sans quoi le même
        archer tirerait en sets au tableau et en cumul en poule. La recopie a déjà lâché une fois
        sur l'ensemencement (E05US020, plan de 8 pour un tableau de 4) ; on n'en écrit pas une
        seconde.
        """
        return self._bareme_du(participant, lignes)

    def zones_de(
        self, participant: Participant, lignes: dict[int, LigneClassement]
    ) -> tuple[ZoneScore, ...]:
        """Les zones du pavé pour la **lecture** — tolérant, exposé pour la même raison."""
        return self._zones_best_effort(participant, lignes)

    def zones_strictes(
        self, participant: Participant, lignes: dict[int, LigneClassement]
    ) -> tuple[ZoneScore, ...]:
        """Les zones du pavé pour l'**écriture** — lève si le blason est indéterminable.

        Le pendant strict de `zones_de`, et la distinction n'est pas cosmétique : en lecture un
        blason introuvable rend un pavé vide (« pavé indisponible » sur cette rencontre), en
        écriture il **lève** — sans quoi on enregistrerait un score sans savoir s'il est légal.
        Exposer les deux évite que `ServicePoules` choisisse le mauvais par commodité.
        """
        return self._zones_du(participant, lignes)

    # --- Interne : résolution barème / zones / duelliste ---------------------------------------

    def _bareme_du(
        self, participant: Participant, lignes: dict[int, LigneClassement]
    ) -> BaremeDuel:
        """Le barème du duel, résolu par l'**arme** du participant (défaut FFTA, ADR-0049)."""
        return self._resolveur.bareme_pour(self._arme_du(participant, lignes))

    def _arme_du(self, participant: Participant, lignes: dict[int, LigneClassement]) -> str | None:
        """L'arme (texte libre de la catégorie) d'un participant individuel, ou `None`."""
        if participant.genre is not GenreParticipant.INDIVIDUEL:
            return None
        ligne = lignes.get(participant.ref_id)
        if ligne is None:
            return None
        categorie = self._categories.par_id(ligne.categorie_id)
        return None if categorie is None else categorie.arme

    def _zones_du(
        self, participant: Participant, lignes: dict[int, LigneClassement]
    ) -> tuple[ZoneScore, ...]:
        """Les zones admises du blason tiré (le pavé). **Strict** sur le chemin d'écriture : blason
        indéterminable → `BlasonIntrouvable` (404, erreur **visible**, jamais de score faux
        silencieux — même exigence que la grille de qualification, E04US002)."""
        individuel = participant.genre is GenreParticipant.INDIVIDUEL
        ligne = lignes.get(participant.ref_id) if individuel else None
        categorie = None if ligne is None else self._categories.par_id(ligne.categorie_id)
        blason_id = None if categorie is None else categorie.blason_id
        blason = None if blason_id is None else self._blasons.par_id(blason_id)
        if blason is None:
            raise BlasonIntrouvable("Blason du duelliste indéterminable : pavé indisponible.")
        return tuple(blason.zones)

    def _zones_best_effort(
        self, participant: Participant, lignes: dict[int, LigneClassement]
    ) -> tuple[ZoneScore, ...]:
        """Les zones du pavé pour la **lecture** — tolérant, jumeau de `_zones_du`.

        Sur le chemin d'**écriture**, un blason indéterminable lève `BlasonIntrouvable` (404, jamais
        de score faux silencieux). En **lecture**, il ne doit pas faire échouer tout le tableau : on
        renvoie un pavé **vide** (le front affiche « pavé indisponible » sur ce match), exactement
        comme la grille de qualification renvoie des zones vides plutôt qu'un 404 (E04US002).
        """
        try:
            return self._zones_du(participant, lignes)
        except BlasonIntrouvable:
            return ()

    def _duelliste(
        self, participant: Participant | None, lignes: dict[int, LigneClassement]
    ) -> Duelliste | None:
        """Résout un participant en `Duelliste` (nom du classement), ou `None` (vide / équipe)."""
        if participant is None or participant.genre is not GenreParticipant.INDIVIDUEL:
            return None
        ligne = lignes.get(participant.ref_id)
        if ligne is None:
            return None
        return Duelliste(archer_id=participant.ref_id, nom=ligne.nom, prenom=ligne.prenom)

    def _etat_du_match(
        self,
        match: Match,
        phase_id: PhaseId,
        lignes: dict[int, LigneClassement],
        nb_tours: int,
        *,
        duel: Duel | None = None,
    ) -> EtatDuel:
        """Assemble l'`EtatDuel` d'un match ; charge son tir au besoin (si le match a un duel).

        Un tir dont les duellistes enregistrés **divergent** des occupants recalculés (classement
        changé) est **masqué** (`duel=None`) : le match s'affiche non joué plutôt que de prêter un
        score au mauvais couple (ADR-0049 §4).
        """
        haut, bas = match.haut, match.bas
        bareme: BaremeDuel | None = None
        zones: tuple[ZoneScore, ...] = ()
        if haut is not None and bas is not None and not match.est_bye:
            # Match jouable : le pavé est déterminé (barème par arme + zones du blason), même avant
            # tout tir — la grille front sait d'emblée sets/cumul, nb de manches et zones légales.
            bareme = self._bareme_du(haut, lignes)
            zones = self._zones_best_effort(haut, lignes)
            if duel is None:
                charge = self._duels.charger(phase_id, match.numero, bareme=bareme)
                if (charge is not None) and (
                    (charge.participant_haut, charge.participant_bas) == (haut, bas)
                ):
                    duel = charge
        return EtatDuel(
            numero=match.numero,
            tour=match.tour,
            place_en_jeu=match.place_en_jeu,
            haut=self._duelliste(match.haut, lignes),
            bas=self._duelliste(match.bas, lignes),
            est_bye=match.est_bye,
            duel=duel,
            bareme=bareme,
            zones=zones,
            plage=None if match.plage is None else (match.plage.debut, match.plage.fin),
            libelle=libelle_tour(match.tour, nb_tours, match.place_en_jeu, match.plage),
        )
