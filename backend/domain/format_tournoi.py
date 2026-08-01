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
from domain.bareme import BaremeQualification
from domain.deroule import ProjectionDeroule, projeter
from domain.erreurs import FormatSansEtape, NomFormatInvalide
from domain.grain_validation import GrainValidation
from domain.patrimoine import OrigineBrique
from domain.phase import (
    Phase,
    SourcePhase,
    StatutPhase,
    TypePhase,
    grain_par_defaut,
)
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

    def pour_tournoi(self, tournoi_id: TournoiId) -> Phase:
        """Instancie ce modèle en **phase réelle** d'un tournoi, au statut `à venir`.

        C'est ici que `tournoi_id` et `statut` **naissent** : le modèle ne les portait pas. La phase
        obtenue est ensuite ajustable (barème, grain, ordre…) **sans altérer** le format — même
        promesse qu'un gabarit appliqué (E01US008).

        Passe par le constructeur de `Phase`, donc par ses invariants : un format qui décrirait une
        phase impossible échoue **à l'application**, pas silencieusement à l'exécution du moteur.
        """
        return Phase(
            tournoi_id=tournoi_id,
            ordre=self.ordre,
            type=self.type,
            bareme=self.bareme,
            validation=self.validation,
            sources=self.sources,
            effectif=self.effectif,
            statut=StatutPhase.A_VENIR,
        )

    @staticmethod
    def de_phase(phase: Phase) -> ModelePhase:
        """Extrait le **modèle** d'une phase réelle : on retient le déroulé, on oublie l'édition.

        Sert à la **promotion** (« ce format est permanent ») : les phases d'un tournoi remontent
        en brique de bibliothèque. Le `statut` est délibérément perdu — c'est l'avancement d'une
        édition, pas une propriété du format.
        """
        return ModelePhase(
            ordre=phase.ordre,
            type=phase.type,
            bareme=phase.bareme,
            validation=phase.validation,
            sources=phase.sources,
            effectif=phase.effectif,
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
    id: FormatTournoiId | None = None

    def __post_init__(self) -> None:
        """**Seul** le nom est un invariant d'enregistrement (E01US024, ADR-0063).

        Il l'est parce qu'il est la **clé d'unicité** de la bibliothèque : l'assemblage et la
        promotion dédoublonnent par le nom (arbitrage d'E01US023, point 1). Un format sans nom ne
        serait pas un brouillon, il serait introuvable. Tout le reste — étapes manquantes, ordres,
        sources — se **diagnostique** (`anomalies`) et se refuse à l'**application** (`appliquer`).
        """
        if not self.nom.strip():
            raise NomFormatInvalide("Le nom d'un format de tournoi ne peut pas être vide.")

    @staticmethod
    def creer(
        nom: str,
        etapes: Iterable[ModelePhase],
        origine: OrigineBrique = OrigineBrique.UTILISATEUR,
    ) -> FormatTournoi:
        """Crée un format, **cohérent ou non** ; le nom est normalisé (espaces de bord retirés).

        Lève `NomFormatInvalide` si le nom est vide — et rien d'autre : depuis E01US024 un format
        s'enregistre à tout moment, même incomplet. Pour savoir s'il tient debout, appeler
        `anomalies()` ; pour être sûr qu'il ne salira pas un tournoi, `appliquer()` refuse.
        """
        return FormatTournoi(nom=_nom_valide(nom), etapes=tuple(etapes), origine=origine)

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
        if self.etapes:
            return projection
        return replace(
            projection,
            anomalies=(
                Anomalie(
                    FormatSansEtape(
                        "Ce format ne décrit aucune phase : l'appliquer à un tournoi ne créerait "
                        "rien."
                    )
                ),
                *projection.anomalies,
            ),
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

    def modifier(self, nom: str, etapes: Iterable[ModelePhase]) -> FormatTournoi:
        """Renvoie une copie au nom et aux étapes remplacés (mêmes règles que `creer`).

        L'`id` et l'`origine` sont **préservés** : modifier un format officiel sur place le laisse
        officiel (le règlement évolue — ADR-0060 §4). Pour obtenir deux modèles distincts,
        l'appelant passe par `en_creation_utilisateur`.
        """
        return replace(self, nom=_nom_valide(nom), etapes=tuple(etapes))

    def en_creation_utilisateur(self, nom: str) -> FormatTournoi:
        """Détache une **copie** marquée « création utilisateur », **non persistée**.

        C'est l'issue « en faire une copie pour garder les deux modèles » du CA : l'original reste
        intact. L'`id` est remis à `None` — c'est un nouveau modèle, pas une mise à jour.
        """
        return replace(self, nom=_nom_valide(nom), origine=OrigineBrique.UTILISATEUR, id=None)

    def appliquer(self, tournoi_id: TournoiId) -> tuple[Phase, ...]:
        """Instancie le format en **phases** d'un tournoi (statut `à venir`, ordres 1..N).

        **C'est ici que l'invariant est tenu** (ADR-0063). L'enregistrement accepte le brouillon ;
        l'application, elle, refuse en **disant pourquoi** : la première anomalie bloquante est
        levée telle quelle, donc avec le même type d'exception, le même code et le même message
        d'organisateur qu'avant l'US — et donc le même 422 à la frontière API.

        Seules les **bloquantes** arrêtent : un format dont la seule anomalie est conjoncturelle
        (« les rangs 33 à 120 » alors qu'il n'y a que 82 inscrits) s'applique, parce qu'il n'est pas
        faux — le tournoi n'a simplement pas l'effectif prévu, et le déroulé s'y adapte (CA
        « ajustement d'effectif »). Ce contrôle-là est le rôle du diagnostic, à l'écran.

        Le format d'origine reste intact : les phases produites sont des copies indépendantes,
        ajustables sans remonter. Aucune écriture ici — le service décide quoi persister et
        comment traiter les phases déjà présentes.
        """
        for anomalie in self.anomalies():
            if anomalie.gravite is Gravite.BLOQUANTE:
                raise anomalie.erreur
        return tuple(etape.pour_tournoi(tournoi_id) for etape in self.etapes)

    @staticmethod
    def de_phases(nom: str, phases: Iterable[Phase]) -> FormatTournoi:
        """Capture les phases d'un tournoi en format de bibliothèque (**promotion**).

        Les statuts sont perdus (cf. `ModelePhase.de_phase`) : on promeut un **déroulé**, pas un
        avancement. Lève `FormatSansEtape` si le tournoi n'a aucune phase à promouvoir, et les
        erreurs de séquence si ses phases n'en forment pas une valide.
        """
        return FormatTournoi.creer(nom, [ModelePhase.de_phase(phase) for phase in phases])


def _nom_valide(nom: str) -> str:
    """Normalise le nom d'un format ; lève `NomFormatInvalide` s'il est vide."""
    nom_normalise = nom.strip()
    if not nom_normalise:
        raise NomFormatInvalide("Le nom d'un format de tournoi ne peut pas être vide.")
    return nom_normalise
