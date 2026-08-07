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

from domain.bareme import BaremeQualification
from domain.depart import DepartId
from domain.grain_validation import GrainValidation
from domain.phase import (
    Phase,
    SourcePhase,
    StatutPhase,
    TypePhase,
    verifier_coherence_etape,
)
from domain.politiques import ProfondeurClassement
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
    id: EtapeDerouleId | None = None

    def __post_init__(self) -> None:
        """Fait respecter la cohérence quelle que soit la porte d'entrée (`replace()` compris)."""
        verifier_coherence_etape(self.type, self.bareme, self.validation, self.effectif)

    def instancier(self, depart_id: DepartId) -> Phase:
        """Crée la **phase** qui joue cette étape dans un créneau, au statut `à venir`.

        C'est ici que `depart_id` et `statut` naissent : l'étape ne les portait pas. La phase
        obtenue est l'objet du moteur — elle porte la définition **recopiée en mémoire**, jamais
        persistée en double (ADR-0076).
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
            statut=StatutPhase.A_VENIR,
        )

    def avec_ordre(self, ordre: int) -> EtapeDeroule:
        """Renvoie une copie à un nouveau rang dans le déroulé (réordonnancement)."""
        return replace(self, ordre=ordre)

    def avec_sources(self, sources: tuple[SourcePhase, ...]) -> EtapeDeroule:
        """Renvoie une copie aux prélèvements remplacés."""
        return replace(self, sources=sources)
