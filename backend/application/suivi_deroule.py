"""Service applicatif du **suivi du déroulé** (E07US004, ADR-0064) — le plan rempli par la réalité.

Compose deux choses qui existent déjà, sans en recalculer aucune :

- la **projection** du format appliqué au tournoi (`domain.deroule.projeter`), c'est-à-dire *le même
  schéma à braquets* qu'à l'atelier — le mot « même » est dans le CA, et il est contraignant : si
  le suivi redessinait, l'organisateur ne reconnaîtrait pas ce qu'il a composé ;
- l'**avancement** (`domain.suivi_deroule`), c'est-à-dire ce qui est joué, dénombré ici depuis les
  tableaux reconstruits — et, depuis E05US032, **demandé au service du format** pour les phases qui
  ne se dessinent pas en braquets (port `LecteurAvancementDePhase`, ADR-0090 §5). Le module compose
  donc toujours sans recalculer de règle métier, mais il **fait recomposer** : c'est le coût inscrit
  à `DETTE-031`.

**Un exempt (bye) n'est pas un duel joué.** C'est le piège central de la composition : dans un
tableau incomplet, les exempts sont gagnés d'office dès la construction. Les compter afficherait
« premier tour terminé » avant que quiconque ait tiré — et surtout, la projection ne les compte pas
non plus (`domain.deroule._braquets` : *« 24 duellistes dans un tableau de 32 → 8 duels, 8
exemptés »*). Les deux comptes doivent parler de la même chose, sans quoi le rapport « joués /
attendus » est faux des deux côtés.

**Robustesse jour J.** Un tableau qu'on ne sait pas reconstruire — format retouché en cours de
route, phase mal câblée — laisse un bloc à zéro joué plutôt qu'une page d'erreur. L'écran de salle
tourne en permanence, souvent sans personne devant pour le relancer : une exception y coûte
l'affichage de toute la journée, un compteur à zéro coûte une ligne inexacte.

Lecture seule et synchrone hors boucle événementielle (règle 7).
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from application.erreurs import ApplicationError, DepartIntrouvable
from domain.depart import DepartId
from domain.deroule import ProjectionDeroule, TourBraquet, projeter
from domain.erreurs import DomainError
from domain.phase import TYPES_EN_TABLEAU, Phase, PhaseId, TypePhase
from domain.ports import (
    DepartRepository,
    InscriptionRepository,
    PhaseRepository,
    TournoiRepository,
)
from domain.suivi_deroule import (
    STATUTS_DEMARRES,
    AvancementDePhase,
    AvancementDeroule,
    avancement_bloc,
)
from domain.tableau import Match, Tableau
from domain.tournoi import TournoiId

_logger = logging.getLogger(__name__)


class LecteurAvancementDePhase(Protocol):
    """Port étroit : « **où en est** cette phase ? » ([ADR-0090] §5).

    Réalisé par les services de format — `ServicePoules`, `ServiceSuisse`, `ServiceBigShootOff` —,
    branché **par type** au composition root (règle 8), et consommé ici seulement. Le suivi ne
    connaît aucun de ces services : il connaît **cette question**, et `bootstrap/` dit qui y répond.

    ⚠️ **Même patron que `LecteurClassementDePhase`** ([ADR-0084]), et délibérément : le projet a
    déjà payé une fois le prix de deux ports jumeaux nés séparément puis fondus. Un second mécanisme
    de résolution par type aurait été la 4ᵉ occurrence de la même idée.

    Rend `None` quand le service ne sait rien dire de cette phase — pas réglée, pas encore montée.
    C'est une **réponse**, pas une erreur : l'écran de salle tourne en permanence, et une phase
    muette y coûte une ligne incomplète là où une exception coûte l'affichage de la journée.

    [ADR-0084]: ../../docs/adr/0084-un-seul-port-de-lecture-de-classement-resolu-par-type.md
    [ADR-0090]: ../../docs/adr/0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md
    """

    def avancement_de_phase(
        self, tournoi_id: TournoiId, phase_id: PhaseId
    ) -> AvancementDePhase | None:
        """Combien de tours cette phase compte aujourd'hui, et lequel tourne."""
        ...


class CompteurEngages(Protocol):
    """Port étroit : combien d'archers sont engagés dans ce **créneau**.

    C'est l'effectif sur lequel la projection se résout — l'équivalent live du « je simule à N
    archers » de l'atelier. Port étroit plutôt que dépendance à un service entier, même parti que
    `application.supervision.LecteurAvancement`.

    ⚠️ **Par départ, et le nom le dit** (E01US025, ADR-0075). La méthode s'appelait `nb_engages` et
    prenait un `tournoi_id` : un départ **rejoue le tournoi en entier**, donc un déroulé se résout
    sur les inscrits **de son créneau** — quatre créneaux de 100 archers dimensionnaient un tableau
    pour 400. Le renommage n'est pas cosmétique : `TournoiId` et `DepartId` sont le même type pour
    mypy (`DETTE-044`), donc seul un **nom qui change** force la revisite de chaque appel. C'est la
    leçon du reste de cette US — tout ce qui gardait un nom valide est resté en portée tournoi.
    """

    def nb_engages_du_depart(self, depart_id: DepartId) -> int:
        """Nombre d'archers inscrits sur ce créneau."""
        ...


class LecteurTableau(Protocol):
    """Port étroit : reconstruire l'arbre d'une phase (réalisé par `ServiceSaisieDuels`).

    Le suivi ne dépend pas de tout `ServiceSaisieDuels` : juste de sa capacité à rendre le tableau
    reconstruit. On **ne duplique pas** la reconstruction — une seule source de vérité de la
    progression, comme la saisie, le placement et le feu vert la partagent déjà.
    """

    def reconstruire(self, tournoi_id: TournoiId, phase_id: PhaseId) -> tuple[Tableau, object]:
        """Rend le tableau de la phase (et son classement, **ignoré ici**).

        Le second membre est typé `object` et non `dict[int, LigneClassement]` : le suivi n'en fait
        rien, et un `dict` étant **invariant** en typage, l'annoter précisément aurait fait échouer
        la conformité de `ServiceSaisieDuels` au port pour une valeur qu'on jette. Un port étroit ne
        décrit que ce dont il a besoin.
        """
        ...


def _correspondance(tableau: Tableau, braquets: Sequence[TourBraquet]) -> dict[int, TourBraquet]:
    """Quel braquet projeté correspond à quel tour **réel** — alignés **par la fin**.

    ⚠️ **C'est le point que trois passes de revue ont mis à jour, une couche à la fois.** Il vaut
    d'être exposé en entier, parce que chaque correctif intermédiaire était juste sur le cas testé
    et faux sur sa classe :

    1. compter tous les matchs d'un tour faisait terminer la phase **quand la petite finale
       tombait**, la finale non tirée ;
    2. filtrer sur l'égalité des plages était impossible — `_braquets` produit des rangs **absolus**
       (« un tableau des rangs 33-64 rend des perdants en 49-64 »), `construire_tableau` des plages
       **relatives** au tableau, toujours à partir de 1 ;
    3. normaliser par un décalage et ne plus filtrer quand la branche est absente rendait le compte
       **confiant et faux** : les tailles diffèrent dès que `# DETTE-028` s'applique, et le filtre
       basculait alors de « exact » à « aucun » **sur toute la phase**, créditant les premiers tours
       réels aux premiers braquets. À 32 déclarés pour 120 en lice, l'écran affichait `31/31`
       pendant que la finale se tirait.

    **Le bon repère est la fin, pas le début.** Un braquet décrit la branche des gagnants qui se
    resserre jusqu'à la finale ; le tableau réel s'y resserre aussi. Les faire coïncider par leur
    **dernier** tour rend la correspondance vraie quelle que soit la taille d'entrée : les *N* tours
    projetés sont les *N* **derniers** tours réels. Quand le tableau est plus large que la phase
    déclarée (DETTE-028), les premiers tours réels ne remplissent donc rien — ce qui est **honnête**
    : ils font tirer des archers que le format déclaré ne comptait pas.

    Propriétés obtenues, vérifiées par construction sur les deux régimes : **identité** quand les
    structures concordent, et sur 32 déclarés / 120 en lice une lecture `0, 0, 16, 24, 28, 30, 31` —
    monotone et jamais prématurée.
    """
    decalage = tableau.nb_tours - len(braquets)
    return {braquet.tour + decalage: braquet for braquet in braquets}


def _est_de_la_branche(match: Match, braquet: TourBraquet) -> bool:
    """Ce match est-il celui de la branche des gagnants que ce braquet décrit ?

    Deux conditions, **toutes deux indépendantes du repère** — c'est ce qui rend la comparaison
    robuste là où l'égalité de plages échouait :

    - `plage.debut == 1` : la branche des gagnants est celle qui part du haut du tableau
      (`construire_tableau` engendre toujours depuis `Plage(1, taille)`) ; la **petite finale**, qui
      départage les places 3-4, part plus bas et se trouve ainsi écartée ;
    - **même largeur** que le braquet : une largeur est un nombre de rangs, pas une position, donc
      elle se compare sans conversion entre rangs absolus et rangs relatifs.

    `Match.plage` absente (les `Match` bâtis à la main dans les tests) → on compte, faute de mieux.
    """
    if match.plage is None:
        return True
    largeur_projetee = braquet.plage_perdants[1] - braquet.plage_gagnants[0] + 1
    return match.plage.debut == 1 and match.plage.fin - match.plage.debut + 1 == largeur_projetee


class CompteurEngagesRepository:
    """Réalisation de `CompteurEngages` sur les repositories : les inscriptions **d'un créneau**.

    C'est l'effectif que la projection doit résoudre — « combien de personnes ce déroulé doit-il
    faire tirer *dans ce créneau* », pas « combien de dossards le tournoi a vendus ». Les archers
    sont **dédoublonnés** : une double inscription au même créneau ne fait pas deux tireurs.

    Vit ici plutôt qu'en `infrastructure/` : il ne connaît que des **ports** (règle 2), aucune
    technologie de persistance.
    """

    def __init__(
        self, depart_repository: DepartRepository, inscription_repository: InscriptionRepository
    ) -> None:
        self._departs = depart_repository
        self._inscriptions = inscription_repository

    def nb_engages_du_depart(self, depart_id: DepartId) -> int:
        """Nombre d'archers **distincts** inscrits sur ce créneau."""
        return len({i.archer_id for i in self._inscriptions.par_depart(depart_id)})


@dataclass(frozen=True)
class SuiviDeroule:
    """Le déroulé d'une édition : le dessin (projection) **et** son remplissage (avancement).

    Les deux restent **séparés** plutôt que fusionnés en un objet unique : c'est ce qui garantit que
    le composant de dessin reçoit à l'atelier et au pilotage exactement la même structure, et que le
    suivi n'est qu'un calque par-dessus (la « décision de conception centrale » du CA : un seul
    composant, trois surfaces).
    """

    effectif: int
    projection: ProjectionDeroule
    avancement: AvancementDeroule


class ServiceSuiviDeroule:
    """Cas d'usage : « où en est ce **créneau** ? », pour le pilotage et pour l'écran de salle."""

    def __init__(
        self,
        tournoi_repository: TournoiRepository,
        depart_repository: DepartRepository,
        phase_repository: PhaseRepository,
        engages: CompteurEngages,
        tableaux: LecteurTableau,
    ) -> None:
        self._tournois = tournoi_repository
        self._departs = depart_repository
        self._phases = phase_repository
        self._engages = engages
        self._tableaux = tableaux
        self._avancements: dict[TypePhase, LecteurAvancementDePhase] = {}

    def brancher_lecteur_avancement(
        self, type_phase: TypePhase, lecteur: LecteurAvancementDePhase
    ) -> None:
        """Dit qui sait répondre « où en est cette phase ? » pour ce type ([ADR-0090] §5).

        Branchement **tardif et visible** au composition root, comme celui de
        `ServiceSaisieDuels.brancher_lecteur` (ADR-0084) : les services de format sont construits
        après le suivi, et un cycle qu'on ne voit pas est un cycle qu'on réintroduit.

        [ADR-0090]: ../../docs/adr/0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md
        """
        self._avancements[type_phase] = lecteur

    def pour_depart(self, depart_id: DepartId) -> SuiviDeroule:
        """Le suivi complet d'un **créneau**. `DepartIntrouvable` si le créneau n'existe pas.

        ⚠️ **La maille est le départ, pas le tournoi** (E01US025, ADR-0075). Cette méthode
        s'appelait `pour_tournoi` et lisait `PhaseRepository.par_tournoi`, dont la docstring dit
        pourtant « ce
        n'est **pas** une séquence : c'est la concaténation de N suites 1..M ». Sur deux créneaux,
        cela produisait quatre défauts d'un coup : le déroulé dessiné **en double**, l'avancement
        du dernier créneau **écrasant** celui des autres (`{phase.ordre: phase}`), l'effectif
        **fusionné** (donc des tableaux dimensionnés pour 400 au lieu de 100), et deux anomalies
        fausses sur une route **publique** pollée toutes les 10 s — `SequenceOrdreInvalide`, et
        l'unicité de la qualification, dont l'erreur a depuis disparu (E05US025 : un déroulé peut
        porter plusieurs qualifications, cf. ADR-0082). Le suivi n'a de sens que dans un créneau :
        c'est lui qui a son effectif, son avancement et son horaire.

        Un créneau **sans phase** rend un suivi vide plutôt qu'une erreur : avant qu'un format soit
        appliqué, l'écran doit afficher « rien à suivre », pas une page cassée.

        # DETTE-031 : tout est **recalculé à chaque appel** — le compte des engagés, la
        # reconstruction de chaque phase en tableau (qui rejoue le classement complet du départ), et
        # depuis E05US032 la recomposition de chaque phase **déroulée par un service de format**
        # (poules, suisse, Big Shoot Off) qui tourne, cf. `_avancement_lu`.
        # Endpoint public, pollé toutes les 10 s par deux surfaces. Assumé au contexte mono-club et
        # local ; le remède est borné (mémoïsation par version, invalidée par donnees_modifiees),
        # mais aucune mesure ne le réclame aujourd'hui. Cf. docs/dette.md.
        """
        depart = self._departs.par_id(depart_id)
        if depart is None:
            raise DepartIntrouvable(f"Aucun départ d'identifiant {depart_id}.")
        tournoi_id = depart.tournoi_id
        phases = sorted(self._phases.par_depart(depart_id), key=lambda phase: phase.ordre)
        effectif = self._engages.nb_engages_du_depart(depart_id)
        projection = projeter(phases, effectif)
        par_ordre = {phase.ordre: phase for phase in phases}
        blocs = tuple(
            avancement_bloc(
                ordre=bloc.ordre,
                statut=par_ordre[bloc.ordre].statut,
                tours=bloc.tours,
                joues_par_tour=self._duels_tranches(tournoi_id, par_ordre[bloc.ordre], bloc.tours),
                avancement_lu=self._avancement_lu(tournoi_id, par_ordre[bloc.ordre]),
            )
            for bloc in projection.blocs
        )
        return SuiviDeroule(
            effectif=effectif,
            projection=projection,
            avancement=AvancementDeroule(blocs=blocs),
        )

    def avancement_par_phase(self, depart_id: DepartId) -> dict[PhaseId, AvancementDePhase]:
        """Où en est chaque phase de ce créneau, **par identifiant de phase** (E05US033).

        Réalise le port `LecteurAvancementDuDepart` d'`application.arrets_programmes`. Deux raisons
        pour que cette couture vive **ici** plutôt que dans le service qui la consomme :

        - c'est le seul endroit du projet qui sait répondre pour **tous** les formats. Les poules,
        le
          suisse et le Big Shoot Off répondent par le port `LecteurAvancementDePhase` ;
          l'élimination directe — le format le plus courant d'un tournoi de salle — n'a **aucun**
          lecteur branché et voit son avancement reconstruit sur place à partir des braquets
          (`_duels_tranches`). Un consommateur qui interrogerait le port par phase laisserait donc
          les tableaux hors du mécanisme d'arrêt, sans que rien ne rougisse ;
        - `avancement_bloc` réconcilie déjà les deux sources et porte la règle « `nb_tours` n'est
        pas
          `len(tours)` » (ADR-0090). La refaire ailleurs ouvrirait un second calcul du tour courant.

        ⚠️ **La clé change de nature au passage** : `AvancementBloc` est indexé par `ordre` (le rang
        dans la séquence), qui n'a de sens qu'à l'intérieur d'un créneau ; les arrêts, eux,
        s'attachent à des `PhaseId`. La jointure se fait ici, une fois, plutôt que chez chaque
        appelant — trois alias d'`int` (`DETTE-044`) rendent cette confusion parfaitement
        silencieuse.

        Une phase sans identifiant persisté est écartée : elle n'existe pas encore pour un arrêt.
        """
        suivi = self.pour_depart(depart_id)
        par_ordre = {
            phase.ordre: phase.id
            for phase in self._phases.par_depart(depart_id)
            if phase.id is not None
        }
        avancements: dict[PhaseId, AvancementDePhase] = {}
        for bloc in suivi.avancement.blocs:
            phase_id = par_ordre.get(bloc.ordre)
            if phase_id is None:
                continue
            avancements[phase_id] = AvancementDePhase(
                nb_tours=bloc.nb_tours, tour_courant=bloc.tour_courant
            )
        return avancements

    def _avancement_lu(self, tournoi_id: TournoiId, phase: Phase) -> AvancementDePhase | None:
        """Ce que le service du format dit de l'avancement de cette phase, ou `None`.

        ⚠️ **Aucune exception ne remonte d'ici**, même parti que `_duels_tranches` juste en dessous
        et pour la même raison : cette méthode alimente un endpoint **public**, pollé toutes les
        10 s par l'écran de salle et par l'appli du public. Une phase mal réglée — cas courant en
        cours de composition — ferait tomber tout le schéma au lieu d'une ligne.

        Le tuple rattrapé **inclut `KeyError`**, comme `_duels_tranches` et comme
        `tableaux_publics` : `contrat_de` le lève par conception, et les `etat()` traversent des
        tables indexées. La première rédaction promettait « aucune exception » avec un tuple plus
        étroit que celui dont elle se réclamait — cinq axes de revue l'ont relevé.

        **Et chaque cas est journalisé**, pour la raison écrite dans `tableaux_publics` : un
        branchement type→service erroné au composition root lèverait une `ApplicationError` avalée
        en silence, et la phase afficherait « 1 tour » pour toujours. Le jour J, « pourquoi la ronde
        ne s'affiche pas ? » serait indébogable. `info` pour un refus attendu du service, `warning`
        pour un `KeyError` — qui est un défaut de programmation, pas une donnée douteuse.

        # DETTE-031 : cette lecture appelle `ServicePoules.etat` / `ServiceSuisse.etat` /
        # `ServiceBigShootOff.etat`, qui recomposent **intégralement** leur phase, chaîne de sources
        # amont comprise, à chaque appel — sur une route publique pollée toutes les 10 s. La garde
        # de statut ci-dessous borne le surcoût aux seules phases qui tournent (une ou deux par
        # créneau, contre toutes) ; il n'y a pas de mémoïsation par requête, et le port n'a pas le
        # `resolveur` partagé de son jumeau (ADR-0084) qui éviterait de repayer une chaîne amont
        # commune. Cf. docs/dette.md.

        Un type sans lecteur branché rend `None` sans rien tenter : c'est le cas de la
        qualification, de l'échauffement, du barrage, du placement — qui comptent un tour et n'ont
        rien à faire dire à personne (ADR-0090 §3) — **et de la colline**, qui en compterait
        plusieurs mais qu'aucun service ne déroule encore (`DETTE-028`). Cette dernière est le seul
        cas où le repli à 1 est faux, et c'est pour ça qu'elle est nommée ici.
        """
        lecteur = self._avancements.get(phase.type)
        if lecteur is None or phase.id is None or phase.statut not in STATUTS_DEMARRES:
            return None
        try:
            return lecteur.avancement_de_phase(tournoi_id, phase.id)
        except (ApplicationError, DomainError) as exc:
            _logger.info("Avancement de la phase %s non lisible : %s", phase.id, exc)
            return None
        except KeyError as exc:
            _logger.warning("Défaut interne sur la phase %s, avancement écarté : %r", phase.id, exc)
            return None

    def _duels_tranches(
        self, tournoi_id: TournoiId, phase: Phase, braquets: Sequence[TourBraquet]
    ) -> dict[int, int]:
        """Les duels **réellement disputés et tranchés**, par numéro de tour.

        Trois filtres. Les deux premiers sont évidents une fois écrits ; le troisième est celui que
        la revue a dû trouver, et c'est le seul qui produisait un affichage **faux devant le
        public** :

        - `vainqueur is not None` : le duel est allé au bout ;
        - `not est_bye` : un exempt occupe une place du braquet mais **n'est pas un duel** — la
          projection ne le compte pas davantage ;
        - **même branche que le braquet** : un braquet décrit *une* branche à une profondeur donnée
          (`[plage_gagnants.debut … plage_perdants.fin]`), pas tous les matchs de ce rang. Au
          dernier tour d'une élimination directe, il y en a **deux** : la finale (places 1-2) et la
          **petite finale** (places 3-4), que `PlacementEnCascade` fait jouer aux perdants des
          demies. Les compter ensemble donnait « 2 joués sur 1 attendu », plafonné à 1 : dès que la
          petite finale tombait — souvent avant la finale, ou en parallèle — la phase s'affichait
          **terminée pendant que la finale se tirait**, sur l'écran projeté, au moment de la journée
          où il est le plus regardé.

        On filtre donc la **réalité** plutôt que de corriger la projection : le CA impose « le
        **même** schéma » qu'à l'atelier, et `_braquets` (E01US024) ne suit délibérément que la
        branche des gagnants. Corriger le dessin ici, c'est le faire diverger de ce que
        l'organisateur a composé.

        Le résultat est indexé par **numéro de braquet**, pas par tour réel : la correspondance
        entre les deux est faite par `_correspondance` (alignement par la fin).

        Rend un dictionnaire vide dès que le tableau n'est pas lisible : phase non persistée, type
        sans arbre, ou reconstruction en échec (voir la note de robustesse jour J).
        """
        # Sans braquet, il n'y a rien à remplir : on évite la reconstruction, qui est l'opération la
        # plus coûteuse du service (`# DETTE-031`) — cas d'une phase à plusieurs sources, dont la
        # tranche d'entrée est indéterminable.
        if phase.type not in TYPES_EN_TABLEAU or phase.id is None or not braquets:
            return {}
        try:
            tableau, _ = self._tableaux.reconstruire(tournoi_id, phase.id)
        except (ApplicationError, DomainError, KeyError):
            return {}
        par_tour_reel = _correspondance(tableau, braquets)
        comptes: Counter[int] = Counter()
        for match in tableau.matchs:
            if match.vainqueur is None or match.est_bye:
                continue
            braquet = par_tour_reel.get(match.tour)
            if braquet is not None and _est_de_la_branche(match, braquet):
                comptes[braquet.tour] += 1
        return comptes
