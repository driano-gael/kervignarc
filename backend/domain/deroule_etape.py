"""L'**étape de déroulé** — la définition, commune au tournoi ; l'avancement reste au départ
(ADR-0076). Avec une définition unique, la divergence entre créneaux n'est plus improbable : elle
est **impossible**.

⚠️ **`Phase` reste l'objet du moteur** et porte toujours sa définition **en mémoire** : le
repository l'assemble depuis l'étape de même `ordre`. Les modules qui lisent `phase.bareme`
ignorent cette couture, et c'est voulu — la jointure est l'affaire de l'adapter (ADR-0003).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from domain.arret_programme import (
    ArretProgramme,
    verifier_arrets,
    verifier_type_arretable,
)
from domain.bareme import BaremeQualification
from domain.big_shoot_off import ConfigurationBigShootOff
from domain.colline import ConfigurationColline, portee_maximale
from domain.depart import DepartId
from domain.erreurs import (
    ConfigurationBigShootOffInvalide,
    ConfigurationCollineInvalide,
    ConfigurationSuisseInvalide,
)
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
from domain.qualification import DecoupageEnTours, verifier_decoupage_applicable
from domain.suisse import ConfigurationSuisse, rondes_maximales
from domain.tournoi import TournoiId

EtapeDerouleId = int
"""Identifiant technique d'une étape de déroulé, attribué par la persistance."""


@dataclass(frozen=True)
class EtapeDeroule:
    """Une étape du déroulé **d'un tournoi** — sa définition, sans avancement ni créneau.

    C'est `ModelePhase` (le contenu d'un format) doté d'un tournoi et d'une identité : le format
    décrit un déroulé *réutilisable*, cette étape le déroulé *de cette édition*. Les invariants
    sont ceux d'une phase, par la **même** fonction (`verifier_coherence_etape`). Satisfait
    structurellement `domain.phase.EtapeSequencee` : la séquence 1..N se valide sur les étapes,
    seule la **portée** ayant changé (ADR-0045 §3).
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
    taille de poule est une propriété du *format*, pas de l'avancement d'un créneau. `None` sur
    tout autre type, et sur une phase de poules pas encore réglée — le type se choisit avant ses
    paramètres, et l'atelier doit pouvoir enregistrer un brouillon (ADR-0063).
    """

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

    colline: ConfigurationColline | None = None
    """Le réglage d'une **colline** — nombre de manches et portée de défi (E05US027).

    Même régime que les trois ci-dessus. **Une seule classe** : ni le nombre de manches ni la
    portée ne dépendent de l'effectif — ce dont l'effectif décide est la **borne** de portée,
    affichée à l'atelier et vérifiée par `_verifier_portee_de_defi`. ⚠️ Deux champs pour un seul
    réglage : la portée distingue le King of the Hill du Ladder, un format à deux réglages.
    """

    decoupage: DecoupageEnTours | None = None
    """Le découpage d'une **qualification** en tours — « 20 volées en 2 tours de 10 » (E05US035).

    Même régime que ses voisins : porté par l'étape (ADR-0076), `None` sur une qualification non
    découpée — auquel cas la phase **est** son tour. ⚠️ **Ce n'est pas du barème** : un barème dit
    comment on **classe**, un découpage comment on **avance** (invariant *avancer ≠ classer*,
    ADR-0090) ; les mêler ferait croire qu'un tour produit un classement intermédiaire. Seul usage
    : rendre la qualification **arrêtable** (ADR-0093).
    """

    arrets: tuple[ArretProgramme, ...] = ()
    """Les **pauses programmées** de cette étape — après quel tour, jusqu'où (E05US033).

    ⚠️ **Porté par l'étape, donc par le tournoi** : **tous les départs rejouent les mêmes arrêts**.
    C'est le sens d'ADR-0076 — deux créneaux libres de diverger sur leurs pauses seraient la
    divergence silencieuse qu'il a fermée. Ce qui **avance** (l'arrêt a-t-il coupé, l'admin
    l'a-t-il relevé) n'est pas ici : c'est un `FranchissementArret`, propre au créneau.
    """

    titre: str | None = None
    """Le **libellé** que l'organisateur donne à cette étape — « Tableau des jeunes » (E16US002).

    ⚠️ **Un libellé, pas une identité** : l'étape reste adressée par son `id` et située par son
    `ordre`, donc deux étapes peuvent porter le même titre — imposer l'unicité ferait échouer la
    composition sur une gêne d'affichage. `None` quand il n'y en a pas, ce qui est le cas de tous
    les déroulés déjà composés. ⚠️ Reste sur l'étape, absent de `Phase` : le titre décrit la
    *composition*, et `Phase` ne porte que ce dont le moteur a besoin pour avancer.
    """

    id: EtapeDerouleId | None = None

    def __post_init__(self) -> None:
        """Fait respecter la cohérence quelle que soit la porte d'entrée (`replace()` compris)."""
        object.__setattr__(self, "titre", titre_normalise(self.titre))
        verifier_coherence_etape(self.type, self.bareme, self.validation, self.effectif)
        verifier_decoupage_applicable(self.type, self.bareme, self.decoupage)
        self._verifier_convergence_du_big_shoot_off()
        self._verifier_rondes_appariables()
        self._verifier_portee_de_defi()
        self._verifier_arrets_applicables()

    def _verifier_arrets_applicables(self) -> None:
        """Les arrêts programmés décrivent-ils des coupes que cette étape peut appliquer (E05US033).

        Un arrêt seul se juge à son `__post_init__` ; un arrêt **face au type de la phase** est une
        propriété du couple, et le type n'est connu qu'ici. ⚠️ Le nombre de tours n'est connu à la
        composition que pour la **qualification** et la **colline** ; ailleurs on passe `None` et
        `verifier_arrets` ne refuse que le doublon. Une qualification non découpée compte **un**
        tour, donc un arrêt « après le tour 1 » y serait accepté à l'atelier et jamais déclenché.
        """

        # ⚠️ **Le refus vit ICI, pas seulement sur `Phase`** : `ServicePhases.modifier` n'instancie
        # aucune phase, si bien qu'un `PUT` posant un arrêt sur un type qui ne l'admet pas répondait
        # **200** et persistait l'étape — puis chaque lecture passant par `etape.instancier(...)`,
        # le suivi, le pilotage et l'affichage public tombaient tous les trois en 422.
        if not self.arrets:
            return
        # ⚠️ **Un arrêt n'est licite que sur un type dont l'application sait LIRE le tour.** Les
        # types dont personne ne lit l'avancement n'ont aucun tour à observer, et un arrêt posé
        # dessus serait **accepté à l'atelier puis inerte le jour J**.
        #
        # ⚠️ **Le type ne suffit PLUS à décider** : pour la qualification (ADR-0093),
        # l'arrêtabilité dépend d'un **réglage d'instance**. Les deux refus sont nécessaires. Le
        # refus lui-même vit dans le module d'arrêt — le pilotage ouvre une seconde porte, et deux
        # copies d'une même règle divergent ; ce qui reste ici est le *moment* de la vérification.
        verifier_type_arretable(self.type)
        verifier_arrets(
            self.arrets,
            nb_tours=self._nb_tours_a_la_composition(),
            geste_reparateur=self._geste_reparateur_d_un_arret(),
        )

    def _geste_reparateur_d_un_arret(self) -> str | None:
        """Que faire quand un arrêt est refusé — et **ça dépend de l'état, pas du type**.

        ⚠️ Conditionner ce texte au seul type faisait répondre « Découpez d'abord la qualification
        en tours » à une qualification **déjà découpée** en 4 tours portant un arrêt « après le
        tour 4 ». L'organisateur serait allé chercher un réglage déjà fait : `P-3` demandait de
        supprimer un cul-de-sac, ce texte en fléchait un vers le mur.
        """
        if self.type is TypePhase.COLLINE:
            return (
                "Retirez cette pause, ou augmentez le nombre de manches de la colline : une pause "
                "posée après la dernière manche ne coupe rien."
            )
        if self.type is not TypePhase.QUALIFICATION:
            return None
        if self.decoupage is None:
            return "Découpez d'abord la qualification en tours pour qu'une pause ait où tomber."
        return (
            "Retirez cette pause, ou augmentez le nombre de tours du découpage : une pause posée "
            "après le dernier tour ne coupe rien."
        )

    def _nb_tours_a_la_composition(self) -> int | None:
        """Combien de tours cette étape comptera, **quand on peut le savoir sans le terrain**.

        `None` = inconnu, le cas des formats dont l'avancement se lit le jour J. Deux exceptions,
        celles dont le nombre de tours est un **réglage porté par l'étape** : la qualification et
        la colline. ⚠️ La colline a été oubliée ici à sa livraison — une pause « après la manche 7
        » sur une phase réglée à 3 était acceptée et **définitivement inerte**. À rejouer pour tout
        type ajouté à `TYPES_ARRETABLES`.
        """

        # DETTE-062 : rien n'interdit de changer ce nombre sur une phase **en cours**, et le
        # changer déplace les frontières de tour — une pause non encore atteinte peut devenir
        # immédiatement due, ou passer pour manquée. La recette dit de régler avant de démarrer :
        # c'est une consigne, pas un garde-fou.
        if self.type is TypePhase.COLLINE:
            # `None` sur une colline non réglée : on ne borne pas ce qu'on ne peut pas juger — le
            # réglage manquant est déjà refusé ailleurs, au démarrage de la phase.
            return self.colline.nb_manches if self.colline is not None else None
        if self.type is not TypePhase.QUALIFICATION:
            return None
        return self.decoupage.nb_tours if self.decoupage is not None else 1

    def _verifier_rondes_appariables(self) -> None:
        """À N participants, on ne peut pas apparier plus de N-1 rondes sans ré-affrontement.

        Propriété du **couple** (nb_rondes, effectif), comme la convergence du Big Shoot Off :
        `ConfigurationSuisse` refuse par contrat toute validation dépendant de l'effectif (règle
        2), et le refus vit ici, là où l'effectif est déclaré. ⚠️ Le dire à la composition évite de
        le découvrir à la ronde 6, sans rattrapage. Silencieux quand l'effectif n'est pas déclaré.
        """
        if self.suisse is None or self.effectif is None:
            return
        maximum = rondes_maximales(self.effectif)
        if self.suisse.nb_rondes > maximum:
            raise ConfigurationSuisseInvalide(
                f"À {self.effectif} archers, {maximum} rondes au plus sont appariables sans "
                f"ré-affrontement ; {self.suisse.nb_rondes} en sont demandées."
            )

    def _verifier_portee_de_defi(self) -> None:
        """Une portée ≥ à l'effectif n'est plus ni un King of the Hill ni un Ladder (E05US027).

        Troisième vérification de la même famille : propriété du **couple** (portée, effectif), et
        `ConfigurationColline` refuse par contrat toute validation dépendant de l'effectif (règle
        2). ⚠️ Le dire à la composition évite de le découvrir en salle, la phase déjà lancée.
        Silencieux quand l'effectif n'est pas déclaré — et le service **borne** au lieu de lever,
        pour qu'un écran s'ouvre toujours.
        """
        if self.colline is not None and self.type is not TypePhase.COLLINE:
            # DETTE-078
            # ⚠️ **Le refus existait déjà, mais UN CRAN TROP TARD** : il vivait dans
            # `Phase.__post_init__`, donc à `instancier()`, c'est-à-dire **après** que l'étape a
            # rejoint le déroulé. Une entrée refusée en 422 laissait une étape sans phase, occupant
            # un rang que l'ajout suivant ne réutilise pas. Le refuser ici le rend antérieur à
            # toute écriture. Les quatre réglages voisins partagent ce défaut, hérité et inscrit au
            # registre plutôt que corrigé en douce ici.
            raise ConfigurationCollineInvalide(
                "Un réglage de colline ne se pose que sur une phase de type « colline »."
            )
        if self.colline is None or self.effectif is None:
            return
        maximum = portee_maximale(self.effectif)
        if self.colline.portee_de_defi > maximum:
            raise ConfigurationCollineInvalide(
                f"À {self.effectif} archers, un défi porte au plus sur {maximum} rang(s) ; "
                f"une portée de {self.colline.portee_de_defi} laisserait chacun défier n'importe "
                "qui, ce qui n'est plus ni un King of the Hill ni un Ladder."
            )

    def _verifier_convergence_du_big_shoot_off(self) -> None:
        """Une finale doit désigner **un** vainqueur : la liste doit converger sur cet effectif.

        ⚠️ Arbitrage du commanditaire du 15/08/2026. Un Big Shoot Off terminé à plusieurs rescapés
        les laisse tous au rang 1 : le palmarès leur décernait l'or à tous, et une phase avale
        prélevant « les rangs 1 à 2 » restait bloquée **pour toujours**. ⚠️ Le refus vit sur
        l'étape : la convergence est une propriété du **couple** (liste, effectif), et la
        configuration refuse par contrat toute validation qui en dépend.
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

        C'est ici que `depart_id` et `statut` naissent. La phase porte la définition **recopiée en
        mémoire**, jamais persistée en double (ADR-0076). ⚠️ `decoupage` est recopié, `arrets` ne
        l'est pas : le découpage décide de l'avancement que le moteur **lit sur la phase**, alors
        que les arrêts ne sont lus que par `ServiceArretsProgrammes`, qui adresse le déroulé par
        rang — les faire voyager fermerait un cycle d'import.
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
            colline=self.colline,
            decoupage=self.decoupage,
            statut=StatutPhase.A_VENIR,
        )

    def avec_ordre(self, ordre: int) -> EtapeDeroule:
        """Renvoie une copie à un nouveau rang dans le déroulé (réordonnancement)."""
        return replace(self, ordre=ordre)

    def avec_sources(self, sources: tuple[SourcePhase, ...]) -> EtapeDeroule:
        """Renvoie une copie aux prélèvements remplacés."""
        return replace(self, sources=sources)


def titre_normalise(titre: str | None) -> str | None:
    """Retire les espaces de bord ; un titre blanc **vaut absence de titre**, jamais une erreur.

    Effacer le champ est le geste par lequel l'organisateur *retire* un titre. La normalisation est
    alignée sur `Tournoi._nom_valide`. ⚠️ **Publique depuis E16US002** :
    `ModelePhase.__post_init__` l'appelle aussi, pour que la même saisie ait la même valeur des
    deux côtés de la traversée format ↔ étape. ⚠️ Appelée depuis `__post_init__` faute de fabrique,
    pour tenir la promesse « quelle que soit la porte d'entrée, `replace()` compris ».
    """
    if titre is None:
        return None
    normalise = titre.strip()
    return normalise or None
