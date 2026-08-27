"""Format de tournoi — un modèle est une **séquence** de phases, pas des phases sans tournoi.

⚠️ **`Phase.tournoi_id` nullable ne marche pas ici**, contrairement à `Categorie` et `Blason` :
l'invariant d'une phase est **collectif** — `SequencePhases` exige des ordres contigus 1..N. Des
phases de bibliothèque entreraient en collision d'`ordre` et il aurait fallu **désarmer** le
garde-fou du moteur. `statut` et `tournoi_id` n'existent pas dans le modèle : ils **naissent** à
l'application.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace

from domain.anomalie import Anomalie, Gravite
from domain.arret_programme import ArretProgramme
from domain.bareme import BaremeQualification
from domain.big_shoot_off import ConfigurationBigShootOff
from domain.colline import ConfigurationColline
from domain.deroule import ProjectionDeroule, effectif_minimum, projeter
from domain.deroule_etape import EtapeDeroule, titre_normalise
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
from domain.qualification import DecoupageEnTours
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

    ⚠️ **Un modèle de phase ne valide plus rien à la construction** depuis E01US024 (ADR-0063) : le
    CA a déplacé la vérification vers l'**usage** — « on doit pouvoir sauvegarder le brouillon tout
    le temps ». Une `qualification` sans barème est donc licite, mais un format qui en contient un
    refusera de s'appliquer : le garde-fou a **changé de porte**, `pour_tournoi` construisant une
    `Phase` dont le `__post_init__` valide toujours. Satisfait `EtapeSequencee`/`EtapeProjetable`.
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

    colline: ConfigurationColline | None = None
    """Le réglage d'une **colline** — nombre de manches et portée de défi (E05US027).

    Même régime de brouillon, et **exactement la même raison** que ses deux voisins ci-dessus de ne
    rien vérifier ici : une portée de 3 est jouable à 12 archers et ne l'est pas à 3. La borne se
    juge sur le couple (réglage, effectif), donc sur l'**étape** d'un tournoi, jamais sur la brique
    de bibliothèque."""

    decoupage: DecoupageEnTours | None = None
    """Le découpage d'une **qualification** en tours (E05US035, ADR-0093).

    ⚠️ **Présent ici pour la même raison qu'`arrets`** : capturer un tournoi en format perdrait son
    découpage en silence, et le format réappliqué rendrait sa qualification **non arrêtable** —
    donc toutes les pauses posées dessus, refusées. Le dépôt a payé cette leçon deux fois
    (`barrage_jusqu_au`, puis `arrets`). Même régime de brouillon : la divisibilité se juge sur
    l'**étape**, un format s'écrivant sans connaître le barème du tournoi qui l'appliquera.
    """

    arrets: tuple[ArretProgramme, ...] = ()
    """Les **pauses programmées** de cette étape (E05US033, ADR-0091).

    ⚠️ **Présent ici parce que son absence serait le défaut de `barrage_jusqu_au`** : capturer un
    tournoi en format perdrait ses pauses **en silence**. Même régime de brouillon : aucune
    vérification contre le nombre de tours ici — un format est réutilisé sur des effectifs qu'il ne
    connaît pas, et « après le tour 5 » est applicable à un suisse de 7 rondes, inerte à un de 5.
    Le refus vit sur l'`EtapeDeroule`, là où l'effectif est déclaré.
    """

    titre: str | None = None
    """Le **libellé** de cette étape dans le format — voir `EtapeDeroule.titre` (E16US002).

    Porté par le modèle **et** par l'étape : c'est ce qui fait qu'un format rejoué d'une année sur
    l'autre remonte avec ses titres. Un champ présent d'un seul côté de la traversée est le défaut
    `barrage_jusqu_au` qu'ADR-0076 a fermé."""

    def __post_init__(self) -> None:
        """Normalise le titre — **sans rien valider** (E16US002).

        ⚠️ **`ModelePhase` est l'AUTRE porte d'entrée du titre, et elle était ouverte** : ne
        normaliser que dans `EtapeDeroule` laissait un titre posté sur un *format* traverser sans
        strip, si bien que la même saisie avait **deux valeurs selon l'écran**. ⚠️ Ce
        `__post_init__` normalise, il ne **valide** pas : `ModelePhase` n'a délibérément aucun
        invariant depuis E01US024 — ajouter une garde rouvrirait ce débat.
        """
        object.__setattr__(self, "titre", titre_normalise(self.titre))

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

        C'est ici que `tournoi_id` naît. L'étape obtenue est ajustable **sans altérer** le format —
        même promesse qu'un gabarit appliqué. **Vers le tournoi et non vers un départ** (ADR-0076)
        : le déroulé se définit une fois, et `EtapeDeroule.instancier` descend ensuite au départ en
        ne créant qu'un **avancement**. Passe par le constructeur d'`EtapeDeroule`, donc par les
        mêmes invariants qu'une phase : un format impossible échoue **à l'application**.
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
            colline=self.colline,
            decoupage=self.decoupage,
            arrets=self.arrets,
            titre=self.titre,
        )

    @staticmethod
    def d_etape(etape: EtapeDeroule) -> ModelePhase:
        """Extrait le **modèle** d'une étape de déroulé : on retient la règle, on oublie l'édition.

        Sert à la **promotion** (« ce format est permanent ») : le déroulé d'un tournoi remonte en
        brique de bibliothèque, le `tournoi_id` étant délibérément perdu. **Depuis une étape et non
        d'une phase** (ADR-0076) : la définition ne vit plus que là — avant, promouvoir lisait
        *l'une des N copies*, sans que rien ne garantisse laquelle.
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
            colline=etape.colline,
            decoupage=etape.decoupage,
            arrets=etape.arrets,
            titre=etape.titre,
        )


@dataclass(frozen=True)
class FormatTournoi:
    """Un format — **modèle de bibliothèque** du patrimoine du club (E01US023, ADR-0060).

    Contrairement à `Categorie` et `Blason`, un format n'a **pas** de forme « copie de tournoi » :
    sa copie, dans un tournoi, ce sont ses **phases**. Il n'a donc pas de `tournoi_id` du tout —
    c'est ce qui le distingue des deux autres briques, et la raison pour laquelle son application
    produit des agrégats d'un **autre type**. `id` vaut `None` tant qu'il n'est pas persisté.
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

        Il l'est parce qu'il est la **clé d'unicité** de la bibliothèque : assemblage et promotion
        dédoublonnent par le nom. Un format sans nom ne serait pas un brouillon, il serait
        introuvable. Tout le reste se **diagnostique** et se refuse à l'**application**. L'exigence
        d'effectif fait exception **de forme** : un zéro n'est pas un brouillon incomplet, c'est
        une valeur qui ne veut rien dire — sa cohérence avec le déroulé, elle, se diagnostique.
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

        Ajoute à la projection générique la seule anomalie qui appartienne au **format** : n'avoir
        aucune étape. Une séquence vide est licite pour un tournoi, pas pour un format qu'appliquer
        ne créerait rien. **Source unique du diagnostic** — `anomalies()` en dérive : un premier
        jet avait deux chemins, la projection oubliait `FormatSansEtape` et l'écran affichait «
        inapplicable » sans dire pourquoi.
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
        """Renvoie une copie au nom, aux étapes et à l'exigence d'effectif remplacés.

        L'`id` et l'`origine` sont **préservés** : modifier un format officiel sur place le laisse
        officiel (ADR-0060 §4). ⚠️ `effectif_minimum_exige` est **remplacé**, pas fusionné — le
        passer à `None` *efface* l'exigence, contrat d'un `PUT`. Le paramètre est **sans défaut**,
        et c'est un garde-fou : un défaut `None` avait laissé deux appelants de production effacer
        la règle du club en silence. Un paramètre dont l'omission détruit une donnée ne s'omet pas.
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

        **Vers le tournoi, plus vers des départs** (ADR-0076) : ce sont les **avancements** qui se
        déclinent par créneau, et eux ne portent aucun réglage. **C'est ici que l'invariant est
        tenu** (ADR-0063) : l'enregistrement accepte le brouillon, l'application refuse en **disant
        pourquoi**. Seules les **bloquantes** arrêtent — une anomalie conjoncturelle n'empêche pas
        d'appliquer, le déroulé s'adaptant à l'effectif.
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

        **Depuis le déroulé, plus depuis les phases d'un départ** (ADR-0076) : tant que la
        définition était dupliquée par créneau, promouvoir obligeait à choisir *laquelle* des N
        copies faisait foi. Le `tournoi_id` est perdu — on promeut une **règle**, pas un
        rattachement. L'exigence d'effectif **remonte** si l'appelant la fournit : elle n'est pas
        lisible depuis les étapes (le tournoi la porte), d'où le paramètre explicite.
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
