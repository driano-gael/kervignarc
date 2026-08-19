"""Agrégat `EtapeDeroule` — la **définition** d'une étape, portée par le tournoi (ADR-0076).

Le déroulé d'un tournoi est défini **une fois** ; chaque départ le **rejoue**. Cette étape porte
donc tout ce qui *décrit* une phase — type, barème, grain de validation, prélèvements, effectif,
profondeur, seuil de barrage — et **rien** de ce qui *avance* : ni statut, ni départ. L'avancement
est l'affaire de `Phase`, une par créneau.

**Pourquoi séparer** (ADR-0076). Jusqu'au 07/08/2026, appliquer un format créait **N copies
complètes** de chaque phase, une par départ. Trois défauts en découlaient :

1. **les copies pouvaient diverger en silence** — au point que `application/portee.py` a dû
   documenter que sa lecture transverse ne rendait qu'« une approximation d'affichage, jamais une
   base de calcul » ;
2. **éditer devenait une écriture en éventail**, et « la phase 2 » désignait N objets aux N
   identifiants — d'où une question d'adressage insoluble, née du modèle et non de l'API ;
3. **`Phase` mêlait deux natures** : sa définition (commune au tournoi) et son avancement (propre au
   créneau).

Avec une définition unique, la divergence n'est plus improbable : elle est **impossible**.

⚠️ **`Phase` reste l'objet du moteur.** Elle porte toujours sa définition **en mémoire** — le
repository l'assemble depuis l'étape de même `ordre`. Les modules qui lisent `phase.bareme` ne
connaissent pas cette couture, et c'est voulu : la jointure est l'affaire de l'adapter (ADR-0003).

Agrégat de domaine **pur** (immuable, sans dépendance framework), validé à la construction.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from domain.arret_programme import ArretProgramme, verifier_arrets
from domain.bareme import BaremeQualification
from domain.big_shoot_off import ConfigurationBigShootOff
from domain.contrat_phase import UniteDeTour
from domain.depart import DepartId
from domain.erreurs import ConfigurationBigShootOffInvalide, ConfigurationSuisseInvalide
from domain.grain_validation import GrainValidation
from domain.phase import (
    Phase,
    SourcePhase,
    StatutPhase,
    TypePhase,
    verifier_coherence_etape,
)
from domain.politiques import ProfondeurClassement
from domain.poule import ReglageDePoules
from domain.suisse import ConfigurationSuisse, rondes_maximales
from domain.tour_de_phase import DecoupageEnTours, nb_tours_regles, unite_de_tour
from domain.tournoi import TournoiId

EtapeDerouleId = int
"""Identifiant technique d'une étape de déroulé, attribué par la persistance."""


@dataclass(frozen=True)
class EtapeDeroule:
    """Une étape du déroulé **d'un tournoi** — sa définition, sans avancement ni créneau.

    C'est `ModelePhase` (le contenu d'un format) doté d'un tournoi et d'une identité : le format
    décrit un déroulé *réutilisable*, cette étape décrit le déroulé *de cette édition*.

    **Invariants** : les mêmes qu'une phase, et par la **même** fonction
    (`verifier_coherence_etape`) — une qualification porte barème **et** grain, le grain est admis
    par le type, sa cadence ne dépasse pas le barème, l'effectif est ≥ 1 s'il est déclaré. Les
    recopier serait la duplication d'invariant que le registre proscrit.

    Satisfait structurellement `domain.phase.EtapeSequencee` (ordre, type, sources, effectif) : la
    séquence 1..N se valide donc sur les étapes, exactement comme elle se validait sur les phases
    avant ADR-0076 — seule la **portée** a changé, pas la règle (ADR-0045 §3).
    """

    tournoi_id: TournoiId
    ordre: int
    type: TypePhase
    bareme: BaremeQualification | None = None
    validation: GrainValidation | None = None
    sources: tuple[SourcePhase, ...] = ()
    effectif: int | None = None
    barrage_jusqu_au: int | None = None
    """Jusqu'à quel rang un barrage départage (E06US003, ADR-0066).

    ⚠️ **Ce champ manquait à `ModelePhase`** alors que `Phase` le portait : promouvoir un tournoi
    dont une phase avait un seuil de barrage **perdait ce seuil** en silence, et le format
    réappliqué n'en avait plus. Le défaut est structurellement clos ici — il n'y a plus qu'une
    définition, donc plus d'écart de champs possible entre deux représentations de la même chose.
    """

    profondeur: ProfondeurClassement | None = None
    poules: ReglageDePoules | None = None
    """Le réglage d'une phase de **poules** — taille visée, barème, régime d'ex æquo (E05US023).

    ⚠️ **Porté par l'étape, donc par le tournoi, et non par la phase d'un départ** (ADR-0076) : une
    taille de poule est une propriété du *format*, pas de l'avancement d'un créneau. Deux départs
    du même tournoi jouent donc des poules de la même taille — l'inverse serait une divergence de
    définition, exactement ce qu'ADR-0076 a rendu impossible.

    `None` sur tout autre type, et sur une phase de poules pas encore réglée : le type se choisit
    avant ses paramètres, et l'atelier doit pouvoir enregistrer un déroulé en cours de composition
    (le brouillon d'ADR-0063)."""

    big_shoot_off: ConfigurationBigShootOff | None = None
    """Le réglage d'un **Big Shoot Off** — combien sortent, manche par manche (E05US028).

    Même régime que `poules` ci-dessus, et pour les mêmes raisons : porté par l'étape donc par le
    tournoi (ADR-0076), `None` tant que le type est choisi sans ses paramètres."""

    suisse: ConfigurationSuisse | None = None
    """Le réglage d'un **système suisse** — le nombre de rondes (E05US026).

    Même régime que les deux ci-dessus. **Une seule classe**, comme le Big Shoot Off et à la
    différence des poules : un nombre de rondes se décide à la composition, il ne dépend pas de
    l'effectif. Ce dont l'effectif décide est le **maximum** appariable sans ré-affrontement
    (`rondes_maximales`), qui est une *borne* affichée à l'atelier, pas un paramètre à stocker."""

    decoupage: DecoupageEnTours | None = None
    """En combien de tours l'organisateur découpe cette étape (E05US033, [ADR-0091]).

    Même régime que `poules`, `big_shoot_off` et `suisse` : porté par l'étape donc par le tournoi
    (ADR-0076), et `None` tant que le type est choisi sans ses paramètres. Ne concerne que la
    qualification et l'échauffement — les types que le contrat déclare `PHASE_ENTIERE`, faute que
    leur structure dise combien de tours ils comptent. Le refus sur un autre type vit sur `Phase`,
    avec ses trois jumeaux.

    [ADR-0091]: ../../docs/adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md
    """

    arrets: tuple[ArretProgramme, ...] = ()
    """Les **pauses programmées** de cette étape — après quel tour, jusqu'où (E05US033).

    ⚠️ **Porté par l'étape, donc par le tournoi**, et la conséquence mérite d'être dite en clair :
    **tous les départs du tournoi rejouent les mêmes arrêts.** C'est voulu, et c'est même le sens
    d'ADR-0076 — un planning de journée est une propriété du *déroulé*, et deux créneaux libres de
    diverger sur leurs pauses seraient exactement la divergence silencieuse que cet ADR a rendue
    impossible. La conséquence pratique est bénigne : les créneaux d'un tournoi de salle enchaînent
    le même programme, et la pause repas tombe au même endroit du déroulé pour chacun.

    Ce qui **avance** — l'arrêt a-t-il coupé, l'admin l'a-t-il relevé — n'est pas ici : c'est un
    `FranchissementArret`, propre au créneau, dans sa propre table (`domain.arret_programme`).
    """

    id: EtapeDerouleId | None = None

    def __post_init__(self) -> None:
        """Fait respecter la cohérence quelle que soit la porte d'entrée (`replace()` compris)."""
        verifier_coherence_etape(self.type, self.bareme, self.validation, self.effectif)
        self._verifier_convergence_du_big_shoot_off()
        self._verifier_rondes_appariables()
        self._verifier_arrets_applicables()

    def _verifier_arrets_applicables(self) -> None:
        """Les arrêts programmés décrivent-ils des coupes que cette étape peut appliquer (E05US033).

        **Même place et même raison que les deux vérifications ci-dessus** : un arrêt seul se juge à
        son `__post_init__` (le tour 0 n'existe pas), mais un arrêt **face au nombre de tours** est
        une propriété du couple, et le nombre de tours n'est connu qu'ici.

        ⚠️ **Il n'est connu que pour les types que l'organisateur règle** — la qualification et
        l'échauffement, dont le découpage *est* la source. Partout ailleurs le nombre de tours se
        lit
        du terrain le jour J (braquets projetés, round-robin, rondes appariables selon l'effectif,
        manches d'un Big Shoot Off) et l'atelier ne peut pas le juger : on passe alors `None`, et
        seul le doublon est refusé. C'est la doctrine déjà tenue par les deux vérifications voisines
        — « on ne refuse pas ce qu'on ne peut pas juger » —, et la reprendre évite d'inventer une
        seconde règle de silence.

        Le cas utile de ce refus est le plus courant de tous : un arrêt posé sur une qualification
        **non découpée**. Elle ne compte qu'un tour, donc « après le tour 1 » tombe après la fin —
        l'arrêt serait inerte, et l'organisateur le découvrirait le jour J en constatant que sa
        pause repas n'a jamais eu lieu.
        """
        if not self.arrets:
            return
        connu = unite_de_tour(self.type) is UniteDeTour.PHASE_ENTIERE
        verifier_arrets(
            self.arrets,
            nb_tours=nb_tours_regles(self.type, self.decoupage) if connu else None,
        )

    def _verifier_rondes_appariables(self) -> None:
        """À N participants, on ne peut pas apparier plus de N-1 rondes sans ré-affrontement.

        **Même place et même raison que la convergence du Big Shoot Off juste au-dessus** : c'est
        une propriété du **couple** (nb_rondes, effectif), pas du réglage seul.
        `ConfigurationSuisse` refuse donc par contrat toute validation dépendant de l'effectif —
        c'est ce qui rend un format de bibliothèque réutilisable d'un tournoi à l'autre (règle 2) —
        et le refus vit ici, là où l'effectif est déclaré.

        ⚠️ **Le dire à la composition, c'est éviter de le découvrir à la ronde 6, le jour J.**
        `apparier_ronde` lève déjà `ConfigurationSuisseInvalide` sur ce même motif, mais il le lève
        *en salle*, une fois les rondes précédentes tirées : l'organisateur n'a alors plus aucun
        geste de rattrapage. La docstring de `ConfigurationSuisse` annonçait exactement ce
        contrôle-ci comme « validé contre l'effectif au démarrage et non ici ».

        Silencieux quand l'effectif n'est **pas** déclaré : on ne refuse pas ce qu'on ne peut pas
        juger. L'atelier montre alors le maximum atteignable et l'organisateur décide.
        """
        if self.suisse is None or self.effectif is None:
            return
        maximum = rondes_maximales(self.effectif)
        if self.suisse.nb_rondes > maximum:
            raise ConfigurationSuisseInvalide(
                f"À {self.effectif} archers, {maximum} rondes au plus sont appariables sans "
                f"ré-affrontement ; {self.suisse.nb_rondes} en sont demandées."
            )

    def _verifier_convergence_du_big_shoot_off(self) -> None:
        """Une finale doit désigner **un** vainqueur : la liste doit converger sur cet effectif.

        ⚠️ **Arbitrage du commanditaire du 15/08/2026** (revue d'E05US028, référentiel §10.1), et sa
        place ici n'est pas un détail. Un Big Shoot Off terminé à plusieurs rescapés les laisse tous
        au rang 1 : le palmarès leur décernait l'or à tous, et une phase avale prélevant « les rangs
        1 à 2 » restait bloquée en `PrelevementEnAttente` **pour toujours** — plus aucune flèche à
        tirer pour lever l'attente. Deux défauts, une seule cause.

        ⚠️ **Le refus vit sur l'étape, pas sur `ConfigurationBigShootOff`**, et c'est délibéré. La
        convergence est une propriété du **couple** (liste, effectif), pas de la liste : `(4, 2, 1)`
        laisse 5 rescapés sur 12 archers et exactement 1 sur 8. La configuration, elle, refuse par
        contrat toute validation dépendant de l'effectif — c'est ce qui rend un format de
        bibliothèque réutilisable d'un tournoi à l'autre (règle 2). Mettre le refus là aurait
        échangé un défaut contre un autre.

        Silencieux quand l'effectif n'est **pas** déclaré : on ne refuse pas ce qu'on ne peut pas
        juger. L'atelier montre alors la projection (`paliers_pour`) et l'organisateur décide.
        """
        if self.big_shoot_off is None or self.effectif is None:
            return
        restants = self.big_shoot_off.restants_pour(self.effectif)
        if restants != 1:
            raise ConfigurationBigShootOffInvalide(
                f"Sur {self.effectif} archers, cette liste laisse {restants} rescapés à égalité au "
                "rang 1 : la finale ne désignerait aucun vainqueur, et la phase suivante ne "
                "pourrait jamais y prélever de rang. Ajoutez ou ajustez une manche."
            )

    def instancier(self, depart_id: DepartId) -> Phase:
        """Crée la **phase** qui joue cette étape dans un créneau, au statut `à venir`.

        C'est ici que `depart_id` et `statut` naissent : l'étape ne les portait pas. La phase
        obtenue est l'objet du moteur — elle porte la définition **recopiée en mémoire**, jamais
        persistée en double (ADR-0076).

        ⚠️ **`arrets` n'est délibérément pas recopié**, et ce n'est pas un oubli : `Phase` ne porte
        pas ce champ. Les arrêts programmés ne sont lus que par `ServiceArretsProgrammes`, qui
        adresse le déroulé par rang ; les faire voyager ici ajouterait un champ que personne ne lit
        et fermerait un cycle d'import (`phase` → `arret_programme` → `phase`). Le raisonnement
        complet est sur `Phase.decoupage`, qui est le champ voisin ayant fait le choix inverse.
        """
        return Phase(
            depart_id=depart_id,
            ordre=self.ordre,
            type=self.type,
            bareme=self.bareme,
            validation=self.validation,
            sources=self.sources,
            effectif=self.effectif,
            barrage_jusqu_au=self.barrage_jusqu_au,
            profondeur=self.profondeur,
            poules=self.poules,
            big_shoot_off=self.big_shoot_off,
            suisse=self.suisse,
            decoupage=self.decoupage,
            statut=StatutPhase.A_VENIR,
        )

    def avec_ordre(self, ordre: int) -> EtapeDeroule:
        """Renvoie une copie à un nouveau rang dans le déroulé (réordonnancement)."""
        return replace(self, ordre=ordre)

    def avec_sources(self, sources: tuple[SourcePhase, ...]) -> EtapeDeroule:
        """Renvoie une copie aux prélèvements remplacés."""
        return replace(self, sources=sources)
