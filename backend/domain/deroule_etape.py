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

    colline: ConfigurationColline | None = None
    """Le réglage d'une **colline** — nombre de manches et portée de défi (E05US027).

    Même régime que les trois ci-dessus. **Une seule classe**, comme le Big Shoot Off et le suisse :
    ni le nombre de manches ni la portée ne dépendent de l'effectif. Ce dont l'effectif décide est
    la **borne** de portée (`portee_maximale`), une *borne* affichée à l'atelier et vérifiée par
    `_verifier_portee_de_defi`, pas un paramètre à stocker.

    ⚠️ **Deux champs pour un seul réglage** : la portée distingue le King of the Hill du Ladder,
    que le référentiel §10.1 présente comme deux formats et que la règle 2 range en **un** format à
    deux réglages."""

    decoupage: DecoupageEnTours | None = None
    """Le découpage d'une **qualification** en tours — « 20 volées en 2 tours de 10 » (E05US035).

    Même régime que `poules`, `big_shoot_off` et `suisse` ci-dessus : porté par l'étape donc par le
    tournoi (ADR-0076), `None` sur tout autre type et sur une qualification non découpée — auquel
    cas la phase **est** son tour, ce qui reste vrai.

    ⚠️ **Ce n'est pas du barème**, et l'y ranger aurait été le raccourci naturel : `nb_volees` vit
    sur `BaremeQualification`, `nb_tours` semblait sa voisine. Mais un barème dit comment on
    **classe** (le cumul, le total), un découpage dit comment on **avance** — l'invariant
    *avancer ≠ classer* d'ADR-0090, posé par le commanditaire. Les mêler aurait fait croire qu'un
    tour de qualification produit un classement intermédiaire, qu'aucune règle FFTA ne prévoit.

    Le seul usage est de rendre la qualification **arrêtable** (ADR-0093) : sans découpage, une
    pause n'a aucune frontière de tour où tomber.
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

    titre: str | None = None
    """Le **libellé** que l'organisateur donne à cette étape — « Tableau des jeunes » (E16US002).

    ⚠️ **Un libellé, pas une identité.** L'étape reste adressée par son `id` et située par son
    `ordre` dans la séquence 1..N (ADR-0045 §3) ; deux étapes du même déroulé peuvent donc porter
    le même titre. Imposer l'unicité aurait fait échouer la composition sur une gêne d'affichage.

    `None` quand l'organisateur n'en a pas donné — et c'est le cas de **tous les déroulés déjà
    composés**. L'écran retombe alors sur le libellé du type, comme avant. Rendre le titre
    obligatoire aurait invalidé l'existant à la première lecture.

    ⚠️ **Reste sur l'étape, absent de `Phase`.** Le titre décrit la *composition* — il est lu par
    l'écran qui lit des étapes (`GET /tournois/{id}/phases`). C'est le régime déjà retenu pour
    `arrets` (E05US033), et non l'écart de champs qu'ADR-0076 a fermé sur `barrage_jusqu_au` :
    celui-là opposait deux représentations de la **même** définition, alors qu'ici il n'y en a
    qu'une, l'étape, et que `Phase` ne porte que ce dont le moteur a besoin pour avancer.
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

        **Même place et même raison que les deux vérifications ci-dessus** : un arrêt seul se juge à
        son `__post_init__` (le tour 0 n'existe pas), mais un arrêt **face au type de la phase** est
        une propriété du couple, et le type n'est connu qu'ici.

        ⚠️ **Le nombre de tours n'est connu à la composition que pour la qualification**, et cette
        exception est née avec E05US035. Pour les quatre autres formats il se lit du terrain le
        jour J (braquets projetés, round-robin, rondes appariables selon l'effectif, manches d'un
        Big Shoot Off) : on passe `None`, et `verifier_arrets` ne refuse alors que le doublon —
        « on ne refuse pas ce qu'on ne peut pas juger », la doctrine des deux vérifications
        voisines.

        ⚠️ **Une qualification, elle, tire son nombre de tours d'un réglage posé sur cette même
        étape** (`decoupage`), donc il est connu ici. Continuer à passer `None` rouvrait très
        exactement le mode de panne que `verifier_type_arretable` existe pour fermer, et par le
        chemin **par défaut** : une qualification non découpée compte **un** tour, un arrêt « après
        le tour 1 » y est donc inerte — accepté à l'atelier, jamais déclenché le jour J, découvert
        à midi. Le message de refus de `verifier_type_arretable` promet d'ailleurs cette
        contrainte (« une **qualification découpée en tours** ») ; il fallait que le code la tienne.
        *(Relevé par les cinq axes de revue d'E05US035, dont trois l'ont trouvé indépendamment.)*
        """
        # ⚠️ **Le refus vit ICI, pas seulement sur `Phase`** (correctif de revue, axe C1) :
        # `ServicePhases.modifier` n'instancie **aucune phase**, si bien qu'un `PUT` posant un arrêt
        # sur un type qui ne l'admet pas répondait **200** et persistait l'étape. Ensuite, chaque
        # lecture de phase passe par `etape.instancier(...)`, qui lève — et le suivi, le pilotage et
        # l'affichage public du créneau tombaient tous les trois en 422. Un tournoi rendu illisible
        # par une entrée client qu'aucun agrégat porteur ne jugeait.
        if not self.arrets:
            return
        # ⚠️ **Un arrêt n'est licite que sur un type dont l'application sait LIRE le tour.** Le
        # déclencheur ne coupe qu'à une frontière de tour **observée** ; les types dont personne ne
        # lit l'avancement — échauffement, barrage, placement — n'ont aucun tour à observer, et un
        # arrêt posé dessus serait **accepté à l'atelier puis inerte le jour J** : l'organisateur
        # découvrirait en pleine compétition que sa pause repas n'a jamais eu lieu.
        #
        # ⚠️ **Le type ne suffit PLUS à décider.** Pour la qualification (ADR-0093), l'arrêtabilité
        # dépend d'un **réglage d'instance** — le découpage —, pas du type :
        # `verifier_type_arretable` ne voit que le type, et c'est `verifier_arrets`, nourri par
        # `_nb_tours_a_la_composition`, qui ferme le cas d'une qualification non découpée. Les deux
        # refus sont nécessaires, aucun ne remplace l'autre.
        #
        # ⚠️ **Le refus lui-même vit dans le module d'arrêt**, pas ici : le pilotage ouvre une
        # seconde porte (poser un arrêt le jour J), et deux copies d'une même règle divergent — la
        # seconde écrite rate le cas nouveau. Ce qui reste ici est le *moment* de la vérification,
        # qui est bien une propriété de l'étape.
        verifier_type_arretable(self.type)
        verifier_arrets(
            self.arrets,
            nb_tours=self._nb_tours_a_la_composition(),
            geste_reparateur=self._geste_reparateur_d_un_arret(),
        )

    def _geste_reparateur_d_un_arret(self) -> str | None:
        """Que faire quand un arrêt est refusé — et **ça dépend de l'état, pas du type**.

        ⚠️ **Un premier jet conditionnait ce texte au seul type**, si bien qu'une qualification
        **déjà découpée** en 4 tours portant un arrêt « après le tour 4 » s'entendait répondre
        « Découpez d'abord la qualification en tours ». L'organisateur serait allé chercher un
        réglage déjà fait et aurait conclu que l'application est cassée : c'est pire qu'un refus
        muet — `P-3` demandait de supprimer un cul-de-sac, ce texte en fléchait un vers le mur.
        *(Relevé par l'axe adversarial en 2ᵉ passe, sur le correctif d'un bloquant de 1ʳᵉ passe.)*
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

        `None` = inconnu, et c'est le cas des formats dont l'avancement se lit le jour J : braquets
        projetés, round-robin, rondes appariables selon l'effectif, manches d'un Big Shoot Off.
        **Deux** formats font exception, et la question à leur poser est toujours la même — *le
        nombre de tours est-il un réglage porté par cette étape, ou une conséquence du terrain ?*

        - la **qualification** depuis E05US035 : son découpage est un réglage de composition. Non
          découpée, elle compte **un** tour — ce n'est pas un cas dégénéré, c'est la vérité qui
          rend tout arrêt inerte, et c'est pourquoi on la dit ;
        - la **colline** depuis E05US027 : `nb_manches` est réglé à la composition, exactement comme
          `decoupage.nb_tours`. `ServiceColline.avancement_de_phase` le confirme — il rend le
          réglage brut, « sans borne à appliquer », une colline n'ayant pas d'équivalent de
          `rondes_maximales`.

        ⚠️ **La colline a été oubliée ici à sa livraison, et relevée en revue par deux axes.**
        Rendue arrêtable par la seule bascule d'`avancement_lisible`, elle acceptait une pause
        « après la manche 7 » sur une phase réglée à 3 manches : `verifier_arrets` ne refuse rien
        quand `nb_tours is None`, donc la pause était **acceptée à l'atelier et définitivement
        inerte**. C'est mot pour mot le mode de panne qu'E05US035 avait fermé pour la
        qualification — un trou *déplacé*, pas ouvert : le raisonnement ci-dessus n'avait pas été
        rejoué sur le format neuf. Il est à rejouer pour **tout** type ajouté à `TYPES_ARRETABLES`.
        """
        # DETTE-062 : rien n'interdit de changer ce nombre sur une phase **en cours**, et le
        # changer déplace les frontières de tour — une pause non encore atteinte peut devenir
        # immédiatement due, ou passer pour manquée. Aucun score n'est re-partitionné (le découpage
        # vit hors du barème), et la recette dit de régler avant de démarrer : c'est une consigne,
        # pas un garde-fou.
        if self.type is TypePhase.COLLINE:
            # `None` sur une colline non réglée : on ne borne pas ce qu'on ne peut pas juger — le
            # réglage manquant est déjà refusé ailleurs, au démarrage de la phase.
            return self.colline.nb_manches if self.colline is not None else None
        if self.type is not TypePhase.QUALIFICATION:
            return None
        return self.decoupage.nb_tours if self.decoupage is not None else 1

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

    def _verifier_portee_de_defi(self) -> None:
        """Une portée ≥ à l'effectif n'est plus ni un King of the Hill ni un Ladder (E05US027).

        **Troisième vérification de la même famille, même place et même raison** que les deux
        ci-dessus : c'est une propriété du **couple** (portée, effectif), pas du réglage seul.
        `ConfigurationColline` refuse par contrat toute validation dépendant de l'effectif — c'est
        ce qui rend un format de bibliothèque réutilisable d'un tournoi à l'autre (règle 2) — et le
        refus vit ici, là où l'effectif est déclaré.

        ⚠️ **Le dire à la composition, c'est éviter de le découvrir en salle.**
        `defis_de_la_manche` lève déjà `ConfigurationCollineInvalide` sur ce motif, mais il le lève
        au moment d'apparier, la phase déjà lancée : le format y perd son sens (« chacun défie
        n'importe qui ») et l'organisateur n'a plus de geste de rattrapage.

        Silencieux quand l'effectif n'est **pas** déclaré : on ne refuse pas ce qu'on ne peut pas
        juger. L'atelier montre alors la borne atteignable et l'organisateur décide — et le service
        **borne** au lieu de lever, pour qu'un écran s'ouvre toujours.
        """
        if self.colline is not None and self.type is not TypePhase.COLLINE:
            # DETTE-078
            # ⚠️ **Le refus existait déjà, mais UN CRAN TROP TARD** (relevé par l'axe adversarial,
            # qui l'a reproduit par exécution). Il vivait dans `Phase.__post_init__`, donc à
            # `instancier()` — c'est-à-dire **après** que l'étape a rejoint le déroulé. Une entrée
            # client refusée en 422 laissait derrière elle une étape sans aucune instance de phase,
            # occupant un rang que l'ajout suivant ne réutilise pas : le déroulé du tournoi
            # devenait troué par une requête *invalide*. Le refuser ici le rend antérieur à toute
            # écriture.
            #
            # Les quatre réglages voisins (`poules`, `big_shoot_off`, `suisse`, `decoupage`)
            # partagent ce défaut, hérité et non introduit ici ; il est inscrit au registre plutôt
            # que corrigé en douce dans cette US. Le champ neuf, lui, n'a aucune
            # raison de naître troué.
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

        ⚠️ **`decoupage` est recopié, `arrets` ne l'est pas**, et l'asymétrie est le sujet. Le
        découpage décide de l'avancement que le moteur **lit sur la phase** — `ServiceSaisie`
        reçoit un `phase_id`, pas une étape — donc il doit voyager. Les arrêts, eux, ne sont lus
        que par `ServiceArretsProgrammes`, qui adresse le déroulé par rang.

        ⚠️ **`arrets` n'est donc délibérément pas recopié**, et ce n'est pas un oubli : `Phase` ne
        porte pas ce champ. Les arrêts programmés ne sont lus que par `ServiceArretsProgrammes`, qui
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

    Effacer le champ est le geste par lequel l'organisateur *retire* un titre : le refuser lui
    interdirait de revenir au libellé automatique sans supprimer la phase. La normalisation est
    alignée sur `Tournoi._nom_valide`, qui strippe déjà nom et lieu — deux conventions pour deux
    libellés saisis au clavier auraient été une incohérence gratuite.

    ⚠️ **Publique depuis E16US002** (correctif de revue) : `ModelePhase.__post_init__` l'appelle
    aussi, pour que la même saisie ait la même valeur des **deux** côtés de la traversée
    format ↔ étape. Sans cela, un titre posté sur un format traversait sans strip, et `"  Jeunes  "`
    y était stocké tel quel pendant que le même texte revenait normalisé côté tournoi.

    ⚠️ **Appelée depuis `__post_init__`, donc par `object.__setattr__`** — premier usage du geste
    dans le domaine. La convention du dépôt normalise plutôt en fabrique (`Tournoi.creer`), mais
    `EtapeDeroule` n'en a pas : elle promet dans sa docstring de tenir la cohérence « quelle que
    soit la porte d'entrée, `replace()` compris ». Normaliser en amont aurait laissé passer un
    `replace(etape, titre="  x  ")` — soit exactement la porte que cette promesse ferme.
    """
    if titre is None:
        return None
    normalise = titre.strip()
    return normalise or None
