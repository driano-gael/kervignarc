"""Agrégat `FormatTournoi` — le **déroulé type** d'une compétition, brique du club (E01US023).

Un *format* est ce qui se réutilise d'une année sur l'autre quand on parle de phases : « FFTA
officiel : qualification 20 volées de 3 en fin de série, puis élimination directe à 16 ». Il porte
**séquence de modèles de phases** — et **ni statut, ni tournoi**.

**Pourquoi un agrégat de plus, et pas simplement `Phase.tournoi_id` nullable** (ADR-0060 §5). C'est
le geste qu'ont reçu `Categorie` et `Blason`, et il ne marche pas ici, pour deux raisons lues dans
le code :

1. **Le barème n'est pas une entité** — il vit dans la `config` de la phase de `qualification`
   (`application/bareme_qualification.py`). Il n'y a aucune colonne `tournoi_id` à relâcher.
2. **L'invariant d'une phase est collectif** — `SequencePhases` exige que les ordres forment la
   suite contiguë 1..N (ADR-0045 §3). Des phases de bibliothèque au `tournoi_id` nul porteraient un
   `statut = a_venir` vide de sens et des `ordre` en collision les uns avec les autres : une lecture
   globale renverrait `[1, 1, 2, 1…]` et la première composition lèverait `SequenceOrdreInvalide`.
   Il aurait fallu **désarmer** le garde-fou qui protège le moteur de phases.

D'où la maille retenue : le modèle n'est pas une phase, c'est une **séquence** de phases. Le
`statut` et le `tournoi_id` ne sont pas « vidés » dans le modèle — ils n'y **existent pas**, et
**naissent** à l'application (`appliquer`). Le patron reste celui du `gabarit_salle` (modèle →
copie → ajustement sans altérer le modèle), une maille au-dessus.

Agrégats de domaine **purs** (immuables, sans dépendance framework), validés à la construction.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace

from domain.anomalie import Anomalie, Gravite
from domain.arret_programme import ArretProgramme
from domain.bareme import BaremeQualification
from domain.big_shoot_off import ConfigurationBigShootOff
from domain.deroule import ProjectionDeroule, effectif_minimum, projeter
from domain.deroule_etape import EtapeDeroule
from domain.erreurs import (
    EffectifMinimumIncoherent,
    ExigenceEffectifInvalide,
    FormatSansEtape,
    NomFormatInvalide,
)
from domain.grain_validation import GrainValidation
from domain.patrimoine import OrigineBrique
from domain.phase import (
    SourcePhase,
    TypePhase,
    grain_par_defaut,
)
from domain.politiques import ProfondeurClassement
from domain.poule import ReglageDePoules
from domain.suisse import ConfigurationSuisse
from domain.tournoi import TournoiId

FormatTournoiId = int
"""Identifiant technique d'un format de tournoi, attribué par la persistance."""

# Preset « format club » du CA d'E01US009 : 5 volées de 3 flèches (les « 15 flèches » du CDC v0.2,
# qui ne sont **pas** la FFTA — cf. référentiel §10.1).
PRESET_CLUB_NB_VOLEES = 5
PRESET_CLUB_NB_FLECHES_PAR_VOLEE = 3


@dataclass(frozen=True)
class ModelePhase:
    """Une étape d'un format — tout ce qu'une `Phase` porte, **sauf** son tournoi et son statut.

    ⚠️ **Un modèle de phase ne valide plus rien à la construction** depuis E01US024 (ADR-0063). Il
    portait les mêmes invariants internes qu'une `Phase` (`verifier_coherence_etape`) ; le CA a
    déplacé cette vérification vers l'**usage** : « *on doit pouvoir sauvegarder le brouillon tout
    le temps, mais on ne peut réellement l'utiliser pour un vrai tournoi que s'il est valide* ».
    Une `qualification` sans barème est donc un modèle **licite** — mais un format qui en contient
    un refusera de s'appliquer.

    Le garde-fou n'est pas désarmé, il a **changé de porte** : `pour_tournoi` construit une `Phase`,
    dont le `__post_init__` valide, lui, toujours. Aucun modèle incohérent ne peut donc atteindre un
    tournoi réel.

    Satisfait structurellement `domain.phase.EtapeSequencee` et `domain.deroule.EtapeProjetable`.
    """

    ordre: int
    type: TypePhase
    bareme: BaremeQualification | None = None
    validation: GrainValidation | None = None
    # Les prélèvements du modèle, **plusieurs** possibles depuis E05US010 (natures mêlées, plages
    # relatives) — exactement le même value object que sur une phase réelle, sérialisé ici dans une
    # **seconde** table (`format_tournoi.config`). C'est ce qui a rendu la migration d'E05US010
    # double ; DETTE-015 est résorbée.
    sources: tuple[SourcePhase, ...] = ()
    effectif: int | None = None
    barrage_jusqu_au: int | None = None
    """Jusqu'à quel rang un barrage départage (E06US003, ADR-0066).

    ⚠️ **Ce champ manquait** jusqu'au 07/08/2026, alors que `Phase` le portait : promouvoir un
    tournoi dont une phase avait un seuil de barrage **perdait ce seuil**, et le format réappliqué
    n'en avait plus. Défaut silencieux, trouvé en mesurant l'écart de champs entre les deux
    représentations pour ADR-0076."""

    profondeur: ProfondeurClassement | None = None
    """Jusqu'où cette étape départage (E06US006). Non validée ici — c'est le brouillon d'ADR-0063 :
    une profondeur réglée sur un type qui ne monte pas de tableau est un modèle **licite** qui
    refusera de s'appliquer, `Phase.__post_init__` faisant barrage à `pour_tournoi`."""

    poules: ReglageDePoules | None = None
    """Le réglage d'une phase de **poules** (E05US023) — même régime de brouillon que `profondeur` :
    un réglage de poules posé sur une élimination directe est un modèle **licite** qui refusera de
    s'appliquer (`ReglageDePoulesInvalide` à la construction de la `Phase`)."""

    big_shoot_off: ConfigurationBigShootOff | None = None
    """Le réglage d'un **Big Shoot Off** — combien sortent, manche par manche (E05US028).

    Même régime de brouillon. ⚠️ Ce champ est **la** raison pour laquelle le moteur refuse de
    rejeter une liste inadaptée à l'effectif : un format est réutilisé d'un tournoi à l'autre, sur
    des effectifs qu'il ne connaît pas au moment où on l'écrit."""

    suisse: ConfigurationSuisse | None = None
    """Le réglage d'un **système suisse** — le nombre de rondes (E05US026).

    Même régime de brouillon, et **exactement la même raison** que le Big Shoot Off ci-dessus de ne
    rien vérifier ici : « 5 rondes » est appariable à 12 archers et ne l'est pas à 5. La borne se
    juge sur le couple (réglage, effectif), donc sur l'**étape** d'un tournoi, jamais sur la brique
    de bibliothèque."""

    arrets: tuple[ArretProgramme, ...] = ()
    """Les **pauses programmées** de cette étape — après quel tour, jusqu'où (E05US033, [ADR-0091]).

    ⚠️ **Présent ici parce que son absence serait exactement le défaut de `barrage_jusqu_au`
    ci-dessus** : capturer un tournoi en format perdrait ses pauses **en silence**, et le format
    réappliqué n'en aurait plus. Le dépôt a déjà payé cette leçon une fois ; on ne la repaie pas.

    Même régime de brouillon : aucune vérification contre le nombre de tours ici, pour la raison
    donnée par le Big Shoot Off et le suisse — un format est réutilisé sur des effectifs qu'il ne
    connaît pas au moment où on l'écrit, et « après le tour 5 » est applicable à un suisse de
    7 rondes, inerte à un suisse de 5. Le refus vit sur l'`EtapeDeroule`, là où l'effectif est
    déclaré.

    [ADR-0091]: ../../docs/adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md
    """

    @staticmethod
    def qualification(
        bareme: BaremeQualification,
        validation: GrainValidation | None = None,
        ordre: int = 1,
        effectif: int | None = None,
    ) -> ModelePhase:
        """Modèle de phase de **qualification** ; sans grain, applique le preset du type."""
        return ModelePhase(
            ordre=ordre,
            type=TypePhase.QUALIFICATION,
            bareme=bareme,
            validation=validation or grain_par_defaut(TypePhase.QUALIFICATION),
            effectif=effectif,
        )

    def pour_tournoi(self, tournoi_id: TournoiId) -> EtapeDeroule:
        """Instancie ce modèle en **étape du déroulé** d'un tournoi.

        C'est ici que `tournoi_id` naît : le modèle de bibliothèque ne le portait pas. L'étape
        obtenue est ensuite ajustable (barème, grain, ordre…) **sans altérer** le format — même
        promesse qu'un gabarit appliqué (E01US008).

        **Vers le tournoi et non vers un départ** (ADR-0076) : le déroulé se définit **une fois**,
        et chaque créneau le rejoue. C'est `EtapeDeroule.instancier` qui descend ensuite au départ,
        en ne créant qu'un **avancement** — jamais une seconde copie de la définition.

        Passe par le constructeur d'`EtapeDeroule`, donc par les mêmes invariants qu'une phase : un
        format qui décrirait une étape impossible échoue **à l'application**, pas silencieusement à
        l'exécution du moteur.
        """
        return EtapeDeroule(
            tournoi_id=tournoi_id,
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
            arrets=self.arrets,
        )

    @staticmethod
    def d_etape(etape: EtapeDeroule) -> ModelePhase:
        """Extrait le **modèle** d'une étape de déroulé : on retient la règle, on oublie l'édition.

        Sert à la **promotion** (« ce format est permanent ») : le déroulé d'un tournoi remonte en
        brique de bibliothèque. Le `tournoi_id` est délibérément perdu — c'est le rattachement à une
        édition, pas une propriété du format.

        **Depuis une étape et non d'une phase** (ADR-0076) : la définition ne vit plus que là.
        Avant,
        promouvoir lisait une phase — donc *l'une des N copies*, et rien ne garantissait laquelle.
        """
        return ModelePhase(
            ordre=etape.ordre,
            type=etape.type,
            bareme=etape.bareme,
            validation=etape.validation,
            sources=etape.sources,
            effectif=etape.effectif,
            barrage_jusqu_au=etape.barrage_jusqu_au,
            profondeur=etape.profondeur,
            poules=etape.poules,
            big_shoot_off=etape.big_shoot_off,
            suisse=etape.suisse,
            arrets=etape.arrets,
        )


@dataclass(frozen=True)
class FormatTournoi:
    """Un format — **modèle de bibliothèque** du patrimoine du club (E01US023, ADR-0060).

    Contrairement à `Categorie` et `Blason`, un format n'a **pas** de forme « copie de tournoi » :
    sa copie, dans un tournoi, ce sont ses **phases**. Il n'a donc pas de `tournoi_id` du tout —
    c'est ce qui le distingue des deux autres briques, et la raison pour laquelle son application
    produit des agrégats d'un **autre type**.

    `id` vaut `None` tant qu'il n'est pas persisté.
    """

    nom: str
    etapes: tuple[ModelePhase, ...]
    origine: OrigineBrique = OrigineBrique.UTILISATEUR
    # E05US021 : le minimum d'inscrits **exigé en plus** du plancher technique — « pas de tournoi de
    # ce type sous 40 archers ». `None` = aucune exigence propre, le déduit fait seul la règle.
    effectif_minimum_exige: int | None = None
    id: FormatTournoiId | None = None

    def __post_init__(self) -> None:
        """**Seul** le nom est un invariant d'enregistrement (E01US024, ADR-0063).

        Il l'est parce qu'il est la **clé d'unicité** de la bibliothèque : l'assemblage et la
        promotion dédoublonnent par le nom (arbitrage d'E01US023, point 1). Un format sans nom ne
        serait pas un brouillon, il serait introuvable. Tout le reste — étapes manquantes, ordres,
        sources — se **diagnostique** (`anomalies`) et se refuse à l'**application** (`appliquer`).

        L'exigence d'effectif fait exception **de forme**, pas de fond : un zéro ou un négatif n'est
        pas un brouillon incomplet, c'est une valeur qui ne veut rien dire. Sa cohérence avec le
        déroulé (« exiger 20 quand il en faut 34 »), elle, se diagnostique comme le reste.
        """
        if not self.nom.strip():
            raise NomFormatInvalide("Le nom d'un format de tournoi ne peut pas être vide.")
        if self.effectif_minimum_exige is not None and self.effectif_minimum_exige < 1:
            raise ExigenceEffectifInvalide(
                "Le minimum d'inscrits exigé par un format est un entier positif "
                f"(reçu {self.effectif_minimum_exige}) ; « aucune exigence » se dit en ne réglant "
                "rien."
            )

    @staticmethod
    def creer(
        nom: str,
        etapes: Iterable[ModelePhase],
        origine: OrigineBrique = OrigineBrique.UTILISATEUR,
        effectif_minimum_exige: int | None = None,
    ) -> FormatTournoi:
        """Crée un format, **cohérent ou non** ; le nom est normalisé (espaces de bord retirés).

        Lève `NomFormatInvalide` si le nom est vide, `ExigenceEffectifInvalide` si l'exigence
        d'effectif n'est pas positive — et rien d'autre : depuis E01US024 un format s'enregistre à
        tout moment, même incomplet. Pour savoir s'il tient debout, appeler `anomalies()` ; pour
        être sûr qu'il ne salira pas un tournoi, `appliquer()` refuse.
        """
        return FormatTournoi(
            nom=_nom_valide(nom),
            etapes=tuple(etapes),
            origine=origine,
            effectif_minimum_exige=effectif_minimum_exige,
        )

    @property
    def effectif_minimum(self) -> int:
        """Le nombre d'inscrits **en dessous duquel ce format ne peut pas se dérouler** (E05US021).

        Le plancher **déduit** des prélèvements, relevé par l'exigence du club si elle est plus
        haute. Une exigence plus **basse** ne l'abaisse pas — elle est signalée comme incohérente
        (`EffectifMinimumIncoherent`) et rend le format inapplicable : c'est le déduit qui a le
        dernier mot, parce que c'est lui que le moteur fera respecter sur la tablette.
        """
        return max(effectif_minimum(self.etapes), self.effectif_minimum_exige or 0)

    def projeter(self, effectif: int | None = None) -> ProjectionDeroule:
        """Le déroulé que ce format produit à `effectif` archers (schéma à braquets, E01US024).

        Ajoute à la projection générique la seule anomalie qui appartienne au **format** et non à sa
        séquence : n'avoir aucune étape. Une séquence vide est licite pour un tournoi
        (`SequencePhases`, ADR-0045) — pas pour un format, qu'appliquer ne créerait rien. La
        distinction reste donc ici, et non dans `domain.deroule`.

        **Source unique du diagnostic** : `anomalies()` en dérive, et le service comme l'API
        n'appellent que celle-ci. Un premier jet avait deux chemins — la projection oubliait
        `FormatSansEtape`, et l'écran affichait « inapplicable » sans dire pourquoi.
        """
        projection = projeter(self.etapes, effectif)
        propres = tuple(self._anomalies_propres(projection))
        if propres:
            projection = replace(projection, anomalies=propres + projection.anomalies)
        if self.effectif_minimum_exige is not None:
            # L'exigence du club relève le chiffre annoncé à l'écran de composition — sans quoi il
            # afficherait le plancher technique, non ce que l'organisateur devra réunir.
            projection = replace(projection, effectif_minimum=self.effectif_minimum)
        return projection

    def _anomalies_propres(self, projection: ProjectionDeroule) -> Iterable[Anomalie]:
        """Les anomalies qui appartiennent au **format** et non à sa séquence de phases.

        Deux seulement, et elles se ressemblent : n'avoir aucune étape, et exiger un effectif que le
        déroulé contredit. Toutes deux portent sur le format **en tant qu'objet de bibliothèque** —
        `domain.deroule`, qui ne voit qu'une suite d'étapes, ne peut ni l'une ni l'autre.
        """
        if not self.etapes:
            yield Anomalie(
                FormatSansEtape(
                    "Ce format ne décrit aucune phase : l'appliquer à un tournoi ne créerait rien."
                )
            )
        exige = self.effectif_minimum_exige
        if exige is not None and exige < projection.effectif_minimum:
            yield Anomalie(
                EffectifMinimumIncoherent(
                    f"Ce format exige {exige} inscrits, mais son déroulé en réclame au moins "
                    f"{projection.effectif_minimum} : l'exigence ne peut pas descendre sous ce que "
                    "les prélèvements imposent."
                ),
                gravite=Gravite.BLOQUANTE,
            )

    def anomalies(self, effectif: int | None = None) -> tuple[Anomalie, ...]:
        """Tout ce qui cloche dans ce format, à `effectif` archers — le diagnostic du CA."""
        return self.projeter(effectif).anomalies

    @staticmethod
    def preset_ffta_18m() -> FormatTournoi:
        """Format officiel FFTA 18 m : qualification de 20 volées de 3 flèches, fin de série.

        **Une seule phase**, délibérément : le MVP est « qualification seule » (E01US009 / notes
        d'E01US010), et déclarer une élimination directe qu'aucun moteur ne sait dérouler
        offrirait en façade un format qui échouerait à l'usage (même principe qu'ADR-0045 §2).
        """
        return FormatTournoi.creer(
            "FFTA officiel 18 m",
            [ModelePhase.qualification(BaremeQualification.preset_ffta_18m())],
            origine=OrigineBrique.FFTA,
        )

    @staticmethod
    def preset_club() -> FormatTournoi:
        """Le format « club » du CA d'E01US009 : 5 volées de 3 flèches (référentiel §10.1).

        Marqué `FFTA` **non** — c'est un format maison, et `origine` dit la **provenance**
        (ADR-0060 §4). Le pré-charger ne le rend pas officiel.
        """
        return FormatTournoi.creer(
            "Format club",
            [
                ModelePhase.qualification(
                    BaremeQualification.creer(
                        PRESET_CLUB_NB_VOLEES, PRESET_CLUB_NB_FLECHES_PAR_VOLEE
                    )
                )
            ],
        )

    def modifier(
        self,
        nom: str,
        etapes: Iterable[ModelePhase],
        effectif_minimum_exige: int | None,
    ) -> FormatTournoi:
        """Renvoie une copie au nom, aux étapes et à l'exigence d'effectif remplacés (mêmes règles
        que `creer`).

        L'`id` et l'`origine` sont **préservés** : modifier un format officiel sur place le laisse
        officiel (le règlement évolue — ADR-0060 §4). Pour obtenir deux modèles distincts,
        l'appelant passe par `en_creation_utilisateur`.

        ⚠️ `effectif_minimum_exige` est **remplacé**, pas fusionné : le passer à `None` *efface*
        l'exigence, exactement comme passer une liste vide efface les étapes. C'est le contrat
        d'un `PUT`.

        **Le paramètre est délibérément sans défaut**, et c'est un garde-fou, pas une rigidité : un
        défaut `None` avait laissé **deux** appelants de production effacer la règle du club en
        silence (`ServiceFormats.promouvoir` et l'écran Patrimoine). Sans défaut, mypy les nomme.
        Un paramètre dont l'omission détruit une donnée ne doit pas pouvoir s'omettre.
        """
        return replace(
            self,
            nom=_nom_valide(nom),
            etapes=tuple(etapes),
            effectif_minimum_exige=effectif_minimum_exige,
        )

    def en_creation_utilisateur(self, nom: str) -> FormatTournoi:
        """Détache une **copie** marquée « création utilisateur », **non persistée**.

        C'est l'issue « en faire une copie pour garder les deux modèles » du CA : l'original reste
        intact. L'`id` est remis à `None` — c'est un nouveau modèle, pas une mise à jour.
        """
        return replace(self, nom=_nom_valide(nom), origine=OrigineBrique.UTILISATEUR, id=None)

    def appliquer(self, tournoi_id: TournoiId) -> tuple[EtapeDeroule, ...]:
        """Instancie le format en **déroulé** du tournoi : une séquence 1..N, définie **une fois**.

        **Vers le tournoi, plus vers des départs** (ADR-0076). ADR-0075 faisait produire ici N
        séquences, une par créneau — donc N copies de chaque définition, libres de diverger. Le
        déroulé se définit désormais une seule fois ; ce sont les **avancements** qui se déclinent
        par départ (`EtapeDeroule.instancier`), et eux ne portent aucun réglage.

        Le domaine ignore donc les créneaux : c'est le **service** qui, connaissant les départs,
        crée les instances et refuse un tournoi qui n'en aurait aucun. Faire descendre les départs
        jusqu'ici aurait mêlé une contrainte de logistique à une règle de déroulé.

        **C'est ici que l'invariant est tenu** (ADR-0063). L'enregistrement accepte le brouillon ;
        l'application, elle, refuse en **disant pourquoi** : la première anomalie bloquante est
        levée telle quelle, donc avec le même type d'exception, le même code et le même message
        d'organisateur — et donc le même 422 à la frontière API.

        Seules les **bloquantes** arrêtent : un format dont la seule anomalie est conjoncturelle
        (« les rangs 33 à 120 » alors qu'il n'y a que 82 inscrits) s'applique, parce qu'il n'est pas
        faux — le tournoi n'a simplement pas l'effectif prévu, et le déroulé s'y adapte (CA
        « ajustement d'effectif »). Ce contrôle-là est le rôle du diagnostic, à l'écran.

        Le format d'origine reste intact : les étapes produites sont des copies indépendantes,
        ajustables sans remonter. Aucune écriture ici — le service décide quoi persister.
        """
        for anomalie in self.anomalies():
            if anomalie.gravite is Gravite.BLOQUANTE:
                raise anomalie.erreur
        return tuple(etape.pour_tournoi(tournoi_id) for etape in self.etapes)

    @staticmethod
    def de_deroule(
        nom: str, etapes: Iterable[EtapeDeroule], effectif_minimum_exige: int | None = None
    ) -> FormatTournoi:
        """Capture le **déroulé d'un tournoi** en format de bibliothèque (**promotion**).

        **Depuis le déroulé, plus depuis les phases d'un départ** (ADR-0076). Tant que la définition
        était dupliquée par créneau, promouvoir obligeait à choisir *laquelle* des N copies faisait
        foi — et à refuser les lots mêlés (`PhasesDeDepartsMeles`, désormais sans objet). Le déroulé
        étant unique, la question ne se pose plus : il n'y a rien à départager.

        Le `tournoi_id` est perdu (cf. `ModelePhase.d_etape`) : on promeut une **règle**, pas un
        rattachement. L'exigence d'effectif, elle, **remonte** si l'appelant la fournit : à la
        différence du rattachement, c'est une propriété du déroulé et non de l'édition. Elle n'est
        pas lisible depuis les étapes — le tournoi la porte —, d'où le paramètre explicite.

        Lève `FormatSansEtape` si le tournoi n'a aucun déroulé à promouvoir, et les erreurs de
        séquence si ses étapes n'en forment pas une valide.
        """
        return FormatTournoi.creer(
            nom,
            [ModelePhase.d_etape(etape) for etape in etapes],
            effectif_minimum_exige=effectif_minimum_exige,
        )


def _nom_valide(nom: str) -> str:
    """Normalise le nom d'un format ; lève `NomFormatInvalide` s'il est vide."""
    nom_normalise = nom.strip()
    if not nom_normalise:
        raise NomFormatInvalide("Le nom d'un format de tournoi ne peut pas être vide.")
    return nom_normalise
