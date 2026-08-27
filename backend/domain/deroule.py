"""Projection d'un déroulé sur un effectif réel — le domaine projette, le front dessine (ADR-0063).
Deux régimes d'anomalie : **structurel** (vrai quel que soit l'effectif, bloquant) et
**conjoncturel** (né de la résolution, avertissant) — sinon « composé pour 120, jouable à 82 »
serait inutilisable.

⚠️ **Le nombre de tours n'est calculé QUE pour les phases en tableau** : poules, suisse et colline
le tirent d'une configuration que ce module ne consulte pas.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Protocol

from domain.anomalie import Anomalie, Gravite
from domain.bareme import BaremeQualification
from domain.contrat_phase import (
    TYPES_CLASSANTS_LUS,
    TYPES_DEROULES,
    TYPES_SANS_OPPOSITION,
)
from domain.erreurs import (
    ChocDePoulePossible,
    ConfigurationPouleInvalide,
    EffectifIncompatible,
    PhaseSansParticipant,
    PhaseSansSource,
    PrelevementVide,
    RangsSourceInexistants,
    SerpentApresDesPoules,
    SourcesQuiSeRecoupent,
)
from domain.grain_validation import GrainValidation
from domain.phase import (
    TYPES_EN_TABLEAU,
    EtapeSequencee,
    IssueTour,
    NatureSource,
    SourcePhase,
    TypePhase,
    anomalies_etape,
    anomalies_sequence,
)
from domain.plage import Plage
from domain.poule import (
    ModeDeComposition,
    ReglageDePoules,
    nb_poules_pour,
    tailles_de_niveau,
)

_TYPES_SANS_OPPOSITION = TYPES_SANS_OPPOSITION
"""Les types où l'archer tire **seul** : un participant leur suffit (E05US021).

Dérivé de la capacité `oppose_des_tireurs` du registre de contrat (`domain/contrat_phase.py`,
ADR-0083). Le parti d'origine tient toujours, il est seulement porté ailleurs : la capacité vaut
`True` par défaut, si bien qu'un type ajouté au catalogue hérite du plancher **prudent** (2) au
lieu du permissif — un oubli y sur-protège au lieu de laisser passer."""

_TYPES_DEROULES = TYPES_DEROULES
"""Les types qu'un service **exécute réellement** aujourd'hui (E05US021).

Dérivé de la capacité `deroule_par_un_service` (ADR-0083). Distinct de `TYPES_EN_TABLEAU`, qu'il
recoupait par coïncidence : celui-ci répond « sait-on dessiner ses tours ? », celui-là « le moteur
va-t-il seulement monter cette phase ? ». Les types qui ont un moteur de domaine mais **aucun
consommateur de production** (`# DETTE-028`) n'y figurent pas : leur prélèvement ne sera pas
honoré, donc il ne peut pas justifier un refus de démarrage.

⚠️ **Deux mouvements en E05US023**, tous deux voulus. Les **poules** y entrent (elles ont leur
service), et `placement` en **sort** : aucun service ne monte son tableau, ce que le registre
constate désormais au lieu de l'affirmer à l'envers. La divergence était signalée par E06US006 et
laissée en l'état — « corriger la table changerait le plancher, donc le comportement d'une autre
US ». Elle est tranchée ici, parce que le remède structurel la referme de toute façon : la garder
demanderait d'écrire un mensonge **explicite** dans le registre. Effet : une phase `placement` qui
prélève « les rangs 33 et suivants » cesse de relever le plancher d'inscrits pour une phase que
rien ne joue — c'est exactement le « refus abusif » qu'E05US021 nommait comme sa pire défaillance,
et il disparaît."""


class EtapeProjetable(EtapeSequencee, Protocol):
    """Ce dont la projection a besoin d'une étape : la séquence, **plus** ce qu'on y demande.

    Élargit `EtapeSequencee` de `bareme`, `validation` et `poules` — la quatrième question du CA
    (« ce qu'on
    leur demande ») ne se répond pas sans eux. L'élargissement reste ici plutôt que dans
    `domain.phase` : les contrôles de séquence n'en ont, eux, toujours pas besoin, et le protocole
    d'origine documente précisément cette frontière. `Phase` et `ModelePhase` satisfont les deux.
    """

    @property
    def bareme(self) -> BaremeQualification | None: ...

    @property
    def validation(self) -> GrainValidation | None: ...

    @property
    def poules(self) -> ReglageDePoules | None:
        """Le réglage d'une phase de poules — nécessaire au **signal de choc** (ADR-0083 §6).

        Ajouté pour la même raison que `bareme` et `validation` : la question ne se répond pas sans
        lui. Le nombre de poules **et** le fait qu'un départage inter-poules soit demandé décident
        si le serpent peut réunir deux membres d'un même groupe au premier tour.

        ⚠️ La première version de ce texte était posée **après** le `...`, donc c'était une
        expression morte et non une docstring : rien ne l'affichait.
        """
        ...


@dataclass(frozen=True)
class Flux:
    """Une **flèche** du schéma : un prélèvement, vu comme un mouvement d'une phase vers une autre.

    Le même objet sert de *sortie* au bloc amont et d'*entrée* au bloc aval — c'est ce qui garantit
    que le dessin ne peut pas montrer une flèche qui part sans arriver. `effectif` vaut `None` quand
    le compte ne se déduit pas de l'effectif simulé (issue de tour d'une phase inconnue).
    """

    ordre_source: int
    ordre_cible: int
    nature: NatureSource
    effectif: int | None
    rang_debut: int | None = None
    rang_fin: int | None = None
    tour: int | None = None
    issue: IssueTour | None = None


@dataclass(frozen=True)
class TourBraquet:
    """Un tour d'une phase en tableau — la *Règle R* rendue lisible.

    `plage_perdants` est le « braquet » : la tranche de rangs que les battus de ce tour se
    partagent, et qui devient le sous-tableau du tour suivant si le format en pose un. Les plages
    sont **absolues** (rangs du tournoi), pas relatives au tableau : un tableau des rangs 33-64 rend
    des perdants en 49-64, pas en 17-32.
    """

    tour: int
    duels: int
    plage_gagnants: tuple[int, int]
    plage_perdants: tuple[int, int]


@dataclass(frozen=True)
class BlocDeroule:
    """Un bloc du schéma — les **quatre questions** du CA, pour une phase, à un effectif donné.

    *Qui est là* : `effectif` et `tranche`. *Ce qu'on leur demande* : `nb_volees`,
    `nb_fleches_par_volee`. *Où ils vont après* : `sorties` (et `sans_suite`, ceux dont le tournoi
    s'arrête là). *Combien de tours* : `tours`.
    """

    ordre: int
    type: TypePhase
    effectif: int | None
    tranche: tuple[int, int] | None
    nb_volees: int | None
    nb_fleches_par_volee: int | None
    tours: tuple[TourBraquet, ...]
    entrees: tuple[Flux, ...]
    sorties: tuple[Flux, ...]
    sans_suite: int | None
    anomalies: tuple[Anomalie, ...]


@dataclass(frozen=True)
class ExigenceEffectif:
    """Le **plancher d'inscrits** d'un déroulé, et la phase qui le réclame (E05US021).

    `ordre` et `rang_debut` valent `None` quand aucune phase n'exprime d'exigence particulière : le
    minimum se réduit alors à ce qu'il faut pour que la structure tienne (deux archers pour un
    tableau, un pour une qualification). Ils sont **la matière du message** exigé par le CA — « le
    refus nomme la phase et son prélèvement » —, d'où leur transport avec le nombre plutôt qu'un
    entier nu que l'appelant devrait ré-expliquer.
    """

    minimum: int
    ordre: int | None = None
    rang_debut: int | None = None
    ordre_source: int | None = None
    """L'ordre de la phase **dans laquelle** `rang_debut` se lit (E05US024).

    Sans lui, le message de refus mêlait deux espaces de rangs : « la phase 3 prélève à partir du
    rang 5, il faut 22 classés » — or le rang 5 se lit dans la **phase 2**, et les deux chiffres ne
    se déduisent plus l'un de l'autre depuis que la chaîne se remonte. Relevé en revue (axe C1) sur
    un message que le CA veut « chiffré et actionnable » (D-16 / P-4)."""


@dataclass(frozen=True)
class ProjectionDeroule:
    """Le déroulé projeté : les blocs, leurs flèches, et tout ce qui cloche.

    `anomalies` porte **tout** — y compris ce qui est déjà rattaché à un bloc — pour que l'appelant
    qui ne veut qu'un verdict n'ait pas à parcourir les blocs.

    `effectif_minimum` est le plancher d'inscrits **déduit** des prélèvements (E05US021). Il est une
    donnée, **pas** une anomalie de plus : le cas « à cet effectif, ce prélèvement ne prend
    personne » remonte déjà en `PrelevementVide`, et l'ajouter une seconde fois ferait signaler le
    même défaut deux fois — le piège documenté sous `_anomalies_effectif_declare`. Un format qui
    *exige* davantage relève le chiffre au-dessus (`FormatTournoi.projeter`).
    """

    effectif: int | None
    blocs: tuple[BlocDeroule, ...]
    anomalies: tuple[Anomalie, ...]
    effectif_minimum: int = 1

    @property
    def bloquantes(self) -> tuple[Anomalie, ...]:
        """Les anomalies qui interdisent d'appliquer ce format à un tournoi."""
        return tuple(a for a in self.anomalies if a.gravite is Gravite.BLOQUANTE)

    @property
    def est_applicable(self) -> bool:
        """Vrai si ce format peut servir un vrai tournoi — le verdict du CA « le brouillon »."""
        return bool(self.blocs) and not self.bloquantes


def projeter(etapes: Sequence[EtapeProjetable], effectif: int | None = None) -> ProjectionDeroule:
    """Projette un format sur `effectif` archers et rend le déroulé qui en découle.

    Sans effectif, le format « reste abstrait » (CA) : la projection décrit sa structure — types,
    flèches, ordre — mais ne compte personne. Avec, chaque bloc devient calculable, et les défauts
    propres à cet effectif apparaissent.

    Tolérante par construction : une séquence incohérente ne fait pas échouer le calcul, elle le
    **décrit**. C'est tout l'objet de l'US — un brouillon doit pouvoir être regardé.
    """
    triees = sorted(etapes, key=lambda etape: etape.ordre)
    structurelles = list(_anomalies_structurelles(triees))

    effectifs: dict[int, int | None] = {}
    tranches: dict[int, tuple[int, int] | None] = {}
    braquets: dict[int, tuple[TourBraquet, ...]] = {}
    conjoncturelles: list[Anomalie] = []
    flux: list[Flux] = []

    premier_ordre = triees[0].ordre if triees else None
    for etape in triees:
        entrees = [
            _resoudre(etape, source, effectifs, tranches, braquets, triees, conjoncturelles)
            for source in etape.sources
        ]
        flux.extend(entrees)
        resolu = _effectif_du_bloc(etape, entrees, effectif, premier_ordre)
        effectifs[etape.ordre] = resolu
        tranches[etape.ordre] = _tranche_du_bloc(etape, entrees, resolu, premier_ordre, braquets)
        braquets[etape.ordre] = _braquets(etape, resolu, tranches[etape.ordre])
        if resolu == 0:
            conjoncturelles.append(
                Anomalie(
                    PhaseSansParticipant(
                        f"À {effectif} archers, la phase {etape.ordre} n'accueille personne : "
                        "ses prélèvements ne trouvent aucun participant."
                    ),
                    etape.ordre,
                    Gravite.AVERTISSEMENT,
                )
            )
        conjoncturelles.extend(_anomalies_effectif_declare(etape, entrees, resolu))
        conjoncturelles.extend(_anomalies_choc_de_poule(etape, entrees, resolu, triees, effectifs))

    # Second passage : les sorties d'un bloc ne sont connues qu'une fois **toutes** les étapes
    # résolues (une phase peut être prélevée par n'importe laquelle de ses cadettes).
    for etape in triees:
        sorties = [f for f in flux if f.ordre_source == etape.ordre]
        conjoncturelles.extend(_anomalies_sur_souscription(etape, effectifs[etape.ordre], sorties))

    toutes = tuple(structurelles) + tuple(conjoncturelles)
    blocs = tuple(_bloc(etape, effectifs, tranches, braquets, flux, toutes) for etape in triees)
    return ProjectionDeroule(
        effectif=effectif,
        blocs=blocs,
        anomalies=toutes,
        effectif_minimum=exigence_minimale(triees).minimum,
    )


# --- Effectif minimum (E05US021) -----------------------------------------------------------------


def effectif_minimum(etapes: Sequence[EtapeSequencee]) -> int:
    """Le nombre d'inscrits **en dessous duquel** ce déroulé ne peut pas se dérouler."""
    return exigence_minimale(etapes).minimum


def exigence_minimale(etapes: Sequence[EtapeSequencee]) -> ExigenceEffectif:
    """Le plancher d'inscrits de ce déroulé, **et la phase qui le réclame** (E05US021).

    Le raisonnement, une fois pour toutes : une phase à duels a besoin de **deux** participants pour
    qu'un match existe ; un prélèvement « à partir du rang *d* » n'en trouve deux que lorsque sa
    phase source en classe *d + 1*. D'où `d - 1 + 2` inscrits — 34 pour « les rangs 33 et
    suivants », l'exemple même du CA. Seules la qualification et l'échauffement se contentent d'un
    participant : les six autres types du catalogue opposent des tireurs.

    **Ce plancher vise exactement ce que le moteur lira** — c'est une contrainte du **moteur**, pas
    une commodité, et s'en écarter le fait mentir dans les deux sens. Les types dont le moteur sait
    lire le classement sont énumérés par `_TYPES_CLASSANTS_LUS`, miroir de
    `ServiceSaisieDuels._classement_de_l_ordre` ; une source visant un autre type (poules, suisse,
    colline, Big Shoot Off) reste **inerte**, la phase reçoit *tous* les archers en lice, et aucun
    plancher n'est donc réclamé pour elle (reste ouvert de `# DETTE-028`, levé par E05US023).

    Les deux mensonges symétriques, tous deux constatés avant correction :

    - viser la **première phase** au lieu d'un type réellement lu laissait passer un déroulé
      « échauffement → qualification → tableau 33+ » avec un plancher de 1, alors que le moteur
      lèverait `EffectifTableauInvalide` en salle ;
    - à l'inverse, réclamer un plancher pour un prélèvement que **rien n'honore** est un refus
      abusif le jour J, qui coûte aussi cher qu'un oubli.

    ⚠️ **La chaîne se remonte** (E05US024). Un rang se lit dans le classement de sa **phase
    source**, et cette source a pu elle-même prélever : « les rangs 5 et suivants d'un tableau qui
    prend les rangs 17 à 32 » réclame **22** inscrits. Une version antérieure de cette docstring
    affirmait l'inverse (« ne dit rien sur le nombre d'inscrits nécessaires ») et citait une méthode
    aujourd'hui supprimée — elle décrivait le moteur d'avant l'US, dans la fonction même qui l'a
    changé. Restent hors de portée les natures qui ne se lisent pas en rangs (`issue_de_tour`,
    `le_reste`, `# DETTE-033`), dont le compte dépend du déroulé.

    ⚠️ **Une fenêtre amont bornée ne fixe aucun plancher.** « Les rangs 33 et suivants d'un tableau
    qui n'en prend que 32 » est infaisable à 34 inscrits comme à 400 : c'est un défaut de
    composition, que le diagnostic signale en `PrelevementVide`, et non un besoin d'effectif.
    Annoncer un chiffre y serait rassurant et faux.

    ⚠️ **Ces cas ne sont couverts par rien à la composition** — ni ici, ni par une anomalie :
    `PrelevementVide` et `RangsSourceInexistants` ne naissent que dans la branche `RANGS` de
    `_flux_de_source`, et `PhaseSansParticipant` exige un compte **nul**. Le plancher structurel
    (`base`) est donc le seul filet : il est **toujours** retenu, quelle que soit la nature des
    prélèvements, parce qu'un tableau exige deux tireurs quoi qu'il l'alimente. C'est une borne
    inférieure jamais surestimante.

    **Plusieurs prélèvements sur une phase se cumulent**, donc c'est le **plus bas** qui décide :
    une phase nourrie par « 1 à 8 » *et* « 33 à 40 » a ses deux archers dès le 2ᵉ inscrit. Entre
    phases, au contraire, c'est le **plus exigeant** qui l'emporte — toutes doivent pouvoir
    se dérouler.
    """
    triees = sorted(etapes, key=lambda etape: etape.ordre)
    if not triees:
        return ExigenceEffectif(minimum=1)

    par_ordre = {etape.ordre: etape for etape in triees}
    exigence = ExigenceEffectif(minimum=1)
    for etape in triees:
        candidate = _exigence_de_letape(etape, par_ordre)
        if candidate.minimum > exigence.minimum:
            exigence = candidate
    return exigence


_TYPES_CLASSANTS_LUS = TYPES_CLASSANTS_LUS
"""Les types dont le moteur sait **lire le classement** pour y prélever (E05US024).

Dérivé de la capacité `classement_lisible` (ADR-0083).

⚠️ **À ne pas confondre avec `_TYPES_DEROULES`**, juste au-dessus, et la nuance décide de refus de
démarrage : celui-là répond « le moteur va-t-il *monter* cette phase ? », celui-ci « sait-il *lire
ce qu'elle a classé* ? ». Les deux ensembles ne coïncident toujours pas — `qualification` est lue
sans être montée. C'est précisément parce qu'ils ne coïncident pas qu'ils sont **deux capacités**
du registre, et non une seule.

Miroir exact de `ServiceSaisieDuels._classement_de_l_ordre` : ce qu'il résout, on l'exige ; ce qu'il
rend `None`, on ne l'exige pas. Faire diverger les deux rouvrirait le défaut symétrique qu'E05US021
a corrigé — soit un plancher réclamé pour un prélèvement que rien n'honore (refus abusif le jour J),
soit un plancher tu pour un prélèvement que le moteur lira (le tournoi démarre puis casse en salle).
E05US023 y fait entrer les **poules**, qui sont désormais montées *et* lues.
"""


def _exigence_de_letape(
    etape: EtapeSequencee, par_ordre: dict[int, EtapeSequencee]
) -> ExigenceEffectif:
    """Le plancher d'inscrits qu'une seule étape réclame.

    `base` est le plancher **structurel** : ce qu'il faut pour que l'étape ait un sens, quelle que
    soit sa provenance. Il est retenu dans **tous** les cas de repli — une phase à duels alimentée
    par « le reste » reste une phase à duels, et le moteur lui demandera deux tireurs.

    ⚠️ **Le plancher par rangs ne vaut que pour ce que le moteur déroule vraiment.** Un déroulé
    « qualification → poules (rangs 33 et suivants) » ne doit pas empêcher de démarrer à 28
    inscrits : aucun service n'exécute une poule (`# DETTE-028`), donc rien ne cassera en salle, et
    refuser le lancement serait un **refus abusif** — le pire mode de défaillance pour cette US,
    puisqu'il ne se répare que le jour J en éditant le déroulé. C'est la symétrie exacte du repli
    « pas de qualification » ci-dessous : l'oracle « ce que le moteur lira » s'applique dans les
    **deux** sens, pas seulement dans le permissif. *(Relevé en contre-revue adversariale.)*
    """
    base = 1 if etape.type in _TYPES_SANS_OPPOSITION else 2

    if not etape.sources:
        # Aucun prélèvement : la phase se peuple des inscrits (la première), ou de tout le monde
        # faute que le moteur sache lire ses sources (`# DETTE-028`). Dans les deux cas, il lui faut
        # juste de quoi tenir debout.
        return ExigenceEffectif(minimum=base)

    if etape.type not in _TYPES_DEROULES:
        # Aucun moteur pour dérouler cette phase : le prélèvement ne sera pas honoré, et réclamer
        # son rang de départ refuserait un tournoi qui se jouera.
        return ExigenceEffectif(minimum=base)

    # ⚠️ Une fenêtre de rangs **plus étroite que `base`** ne fournira jamais assez de participants,
    # à aucun effectif : « les rangs 33 à 33 » n'en donne qu'un. Elle ne fixe donc pas un plancher
    # d'inscrits — c'est un défaut de composition, qu'aucun effectif ne répare. L'inclure dans le
    # `min` produirait un chiffre rassurant et **faux** : « rangs 1 à 1 » + « rangs 33 et suivants »
    # annoncerait 2 là où il en faut 34. On l'écarte plutôt que d'annoncer un mensonge.
    lisibles = [
        source
        for source in etape.sources
        if _source_lisible(source, par_ordre) and _largeur(source) >= base
    ]
    if not lisibles:
        return ExigenceEffectif(minimum=base)

    # ⚠️ **E05US024 — on remonte la chaîne.** Avant, seule une source visant la qualification
    # comptait et « rangs 33+ » se traduisait directement en 34 inscrits. Depuis que le moteur lit
    # le classement de n'importe quelle phase classante, une source peut viser un **tableau**, qui
    # a lui-même prélevé : « les rangs 5+ d'un tableau qui prend les rangs 17 à 32 de la
    # qualification » réclame **22** inscrits (17 - 1 + (5 - 1 + 2)), pas 6. Traduire un rang en
    # inscrits sans remonter annoncerait un plancher trop bas — l'organisateur démarrerait, et la
    # phase manquerait de monde en salle.
    #
    # Le `min` porte sur les **exigences**, pas sur les `rang_debut` : deux sources peuvent viser
    # des phases de profondeurs différentes, auquel cas la plus basse en rang n'est pas la moins
    # exigeante (correctif de revue, axe C1). `_inscrits_pour_classer` applique la même règle un
    # cran plus bas.
    # ⚠️ **La source retenue voyage avec son exigence.** Un premier correctif prenait le `min` des
    # besoins d'un côté et, de l'autre, la source au plus petit `rang_debut` pour nommer la phase :
    # le message rendait alors un chiffre et une fenêtre qui **ne se correspondaient pas**, et pire,
    # pouvait nommer une fenêtre infaisable à tout effectif (écartée du calcul, mais toujours
    # candidate au `min` des rangs). L'organisateur était envoyé compléter ses inscriptions pour
    # débloquer ce qu'aucun effectif ne débloque. Reproduit en revue sur la fixture d'un test ajouté
    # par ce même commit — c'est exactement le défaut que `ordre_source` existe pour fermer.
    candidats = [
        (besoin, source)
        for source in lisibles
        if (
            besoin := _inscrits_pour_classer(
                par_ordre,
                source.ordre_source,
                source.rang_debut - 1 + base,
                frozenset({etape.ordre}),
            )
        )
        is not None
    ]
    if not candidats:
        return ExigenceEffectif(minimum=base)
    besoin, plus_bas = min(candidats, key=lambda candidat: candidat[0])
    return ExigenceEffectif(
        minimum=besoin,
        ordre=etape.ordre,
        rang_debut=plus_bas.rang_debut,
        ordre_source=plus_bas.ordre_source,
    )


def _source_lisible(source: SourcePhase, par_ordre: dict[int, EtapeSequencee]) -> bool:
    """Ce prélèvement sera-t-il **honoré** par le moteur (E05US024) ?

    Deux conditions, et les deux sont nécessaires : la nature doit être résolue (`RANGS` seule —
    `le_reste` et `par_issue_de_tour` restent inertes, `DETTE-033`), et la phase visée doit produire
    un classement que le moteur sait lire (`_TYPES_CLASSANTS_LUS`).
    """
    if source.nature is not NatureSource.RANGS:
        return False
    amont = par_ordre.get(source.ordre_source)
    return amont is not None and amont.type in _TYPES_CLASSANTS_LUS


def _inscrits_pour_classer(
    par_ordre: dict[int, EtapeSequencee],
    ordre: int,
    combien: int,
    vus: frozenset[int] = frozenset(),
) -> int | None:
    """Combien d'**inscrits** il faut pour que la phase `ordre` classe `combien` participants.

    La récursion du plancher (E05US024). Une phase alimentée par les inscriptions en réclame
    exactement autant ; une phase qui prélève « à partir du rang *a* » a besoin que **sa** source en
    classe `a - 1 + combien` — et ainsi de suite jusqu'à la tête du déroulé.

    Rend **`None`** quand aucun effectif ne suffirait : une phase dont la fenêtre est **bornée** ne
    classera jamais plus que sa largeur. « Les rangs 33 et suivants d'un tableau qui prend les rangs
    1 à 32 » est infaisable à 34 inscrits comme à 400 — c'est un **défaut de composition**, que le
    diagnostic de déroulé signale, et non un plancher. Annoncer 34 y serait un chiffre rassurant et
    faux, exactement ce que la garde `_largeur(source) >= base` refuse un cran plus bas.

    ⚠️ **Le plafond est mesuré sur la source la plus basse, pas sur la somme des sources.** Une
    phase nourrie par « 1 à 32 » *et* « 40 à 50 » en accueille 43 ; on n'en compte que 32. C'est une
    **sous-estimation de capacité**, donc un `None` rendu un peu trop tôt, donc un plancher **tu**
    plutôt qu'un refus indu — le sens sûr, celui que cette US et E05US021 ont choisi partout
    ailleurs (« refuser à tort est le pire mode de défaillance »). À resserrer le jour où un déroulé
    réel en souffrira, pas avant.

    ⚠️ **`vus` n'est pas une ceinture de sécurité, c'est la seule chose qui fasse terminer cette
    fonction sur le chemin où elle est appelée** (bloquant de revue, reproduit par deux axes). Un
    premier jet fondait sa terminaison sur « une source est toujours **antérieure** (ADR-0045 §3,
    vérifié par `verifier_sequence`) ». L'argument est juste — pour les chemins d'**écriture**. Or
    `exigence_minimale` est atteinte par `projeter`, dont la docstring dit l'inverse en toutes
    lettres : « tolérante par construction : une séquence incohérente ne fait pas échouer le calcul,
    elle le **décrit** ». Et depuis E01US024/ADR-0063, un format s'enregistre **incomplet** sans
    passer par `verifier_sequence`. Un brouillon dont une étape se désigne elle-même en source est
    donc parfaitement persistable, et c'est l'écran de **diagnostic** — celui dont le métier est
    justement de dire à l'organisateur que sa composition boucle — qui partait en `RecursionError`,
    donc en **500**, donc en page éteinte.

    On rend `None` (« aucun plancher chiffrable ») plutôt que de lever : le cycle est déjà signalé
    comme anomalie par `anomalies_sequence`, le plancher n'a rien à y ajouter, et `projeter` doit
    rester tolérante.
    """
    if ordre in vus:
        return None
    etape = par_ordre.get(ordre)
    if etape is None:
        return combien
    lisibles = [source for source in etape.sources if _source_lisible(source, par_ordre)]
    if not lisibles:
        return combien  # alimentée par les inscriptions : ce qu'elle classe, on l'y inscrit
    # ⚠️ **Une exigence par source, puis le minimum des exigences** (correctif de revue, axe C1).
    # Prendre d'abord la source au plus petit `rang_debut` supposait que toutes visent la **même**
    # phase — vrai tant que seule la qualification était lisible, faux depuis que les sources
    # peuvent viser des phases de **profondeurs de chaîne différentes**. L'erreur allait dans les
    # deux sens : « rangs 1+ d'un tableau des places 49-64 » **et** « rangs 5+ de la qualification »
    # réclamait 50 inscrits au lieu de 6 (refus abusif au démarrage), et une source dont la fenêtre
    # bornée rendait `None` **éteignait** les autres, ramenant le plancher à `base`.
    besoins: list[int] = []
    for source in lisibles:
        # Fenêtre **bornée** trop étroite : cette source ne classera jamais `combien` participants,
        # à 34 inscrits comme à 400. Ce n'est pas un plancher, c'est un défaut de composition — que
        # `_resoudre` signale déjà en `PrelevementVide`. On l'écarte des candidats plutôt que de
        # rendre un chiffre rassurant et faux. Le filtre était appliqué au niveau haut
        # (`_exigence_de_letape`) mais **pas** dans la récursion, où une fenêtre étroite masquait la
        # vraie exigence de sa voisine (relevé par l'axe adversarial, m8).
        if _largeur(source) < combien:
            continue
        besoin = _inscrits_pour_classer(
            par_ordre, source.ordre_source, source.rang_debut - 1 + combien, vus | {ordre}
        )
        if besoin is not None:
            besoins.append(besoin)
    return min(besoins) if besoins else None


def _largeur(source: SourcePhase) -> int:
    """Combien de rangs cette fenêtre peut prélever **au plus** (`sys.maxsize` si fin ouverte)."""
    if source.rang_fin is None:
        return sys.maxsize
    return source.rang_fin - source.rang_debut + 1


# --- Anomalies structurelles ---------------------------------------------------------------------


def _anomalies_structurelles(etapes: Sequence[EtapeProjetable]) -> Iterator[Anomalie]:
    """Les défauts vrais à tout effectif — **la même source de règles** que la version levante.

    Aucune règle n'est recopiée : `anomalies_etape` et `anomalies_sequence` *sont* les fonctions
    qu'appellent `Phase.__post_init__` et `SequencePhases.__post_init__`.
    """
    for etape in etapes:
        yield from anomalies_etape(
            etape.type, etape.bareme, etape.validation, etape.effectif, etape.ordre
        )
    yield from anomalies_sequence(etapes)
    yield from _anomalies_blocs_orphelins(etapes)
    yield from _anomalies_serpent_apres_poules(etapes)


def _anomalies_serpent_apres_poules(etapes: Sequence[EtapeProjetable]) -> Iterator[Anomalie]:
    """Une phase de poules qui prélève dans des poules et compose au **serpent** (E05US029).

    **Structurel, donc bloquant** — et les deux vont ensemble, c'est la ligne de partage d'ADR-0063
    (« ce qui est faux quel que soit l'effectif bloque »). Le défaut ne dépend d'aucun effectif :
    équilibrer des groupes dont les niveaux sont déjà connus est l'inverse de ce que
    l'enchaînement de deux phases de poules cherche à faire, à 12 archers comme à 120.

    ⚠️ **Le prédicat porte sur la source, pas sur le rang dans le déroulé.** Une phase de poules
    sans source déclarée est alimentée par le classement du départ (ADR-0068) : ses niveaux
    viennent de la qualification, pas des poules qui la précèdent, et le serpent y reste le bon
    réglage. Lire « la 2ᵉ phase de poules du déroulé » aurait produit un faux positif systématique
    sur ce cas — et manqué celui d'une phase de poules prélevant dans une phase de poules **non
    adjacente**.

    ⚠️ **Seules les sources `RANGS` comptent** (correctif de revue, axe D, bloquant). `preleves`
    n'honore que celles-là : `le_reste` et `issue_de_tour` sont **inertes** (`DETTE-033`), et une
    phase dont toutes les sources le sont retombe sur le classement du **départ** — donc le cas que
    le paragraphe ci-dessus déclare légitime, atteint par une autre porte. Sans ce filtre, un
    format « la phase 3 prend *le reste* de la phase 2 » — geste offert par l'atelier — devenait
    **inapplicable** après mise à jour, et son message invitait à composer par niveau une phase
    peuplée du plateau entier en ordre de qualification. C'est le précédent qu'énonce
    `_anomalies_blocs_orphelins` : « un format du club qui cesse de fonctionner ».

    ⚠️ **Une phase qui ne peut donner qu'UN groupe n'est jamais en cause** (correctif de revue, axe
    C2). À un seul groupe, serpent et niveau composent la **même** poule : rien n'est éparpillé, et
    exiger un geste qui ne change rien est un refus non justifiable. Le cas n'a rien de théorique —
    c'est la façon dont ce format se composait **avant** cette US, une étape par niveau portant une
    poule et sa tranche (« les rangs 1 à 6 »). Sans cette garde, six étapes de ce genre rendaient
    six anomalies bloquantes et le format entier basculait non applicable. Le test reste
    **structurel** (il lit l'effectif *déclaré*, pas un effectif de tournoi), donc la gravité
    bloquante d'ADR-0063 reste justifiée.

    ⚠️ **Borné aux sources de type POULES par le CA d'E05US029.** Le motif — « la source établit
    déjà des niveaux » — vaudrait identiquement pour un système suisse ou une élimination directe,
    tous deux `classement_lisible`. Ce n'est pas un oubli mais un périmètre : l'élargir demande un
    arbitrage du commanditaire, pas une extension de prédicat en douce.

    ⚠️ **On ne cite que les sources réellement en cause**, comme `_anomalies_choc_de_poule` a appris
    à le faire : nommer une source de qualification à côté d'une source de poules enverrait
    l'organisateur corriger un prélèvement qui n'a rien à se reprocher.
    """
    par_ordre = {etape.ordre: etape for etape in etapes}
    for etape in etapes:
        reglage = etape.poules
        if etape.type is not TypePhase.POULES or reglage is None:
            continue
        if reglage.mode is not ModeDeComposition.SERPENT or reglage.serpent_assume:
            continue
        sources_de_poules = sorted(
            {
                source.ordre_source
                for source in etape.sources
                if source.nature is NatureSource.RANGS
                and (amont := par_ordre.get(source.ordre_source)) is not None
                and amont.type is TypePhase.POULES
            }
        )
        if not sources_de_poules:
            continue
        if _ne_donne_qu_un_groupe(etape, reglage):
            continue
        pluriel = "les phases" if len(sources_de_poules) > 1 else "la phase"
        citees = ", ".join(str(ordre) for ordre in sources_de_poules)
        yield Anomalie(
            SerpentApresDesPoules(
                f"La phase {etape.ordre} prélève dans {pluriel} {citees} (poules) et compose ses "
                "groupes au serpent : les niveaux déjà établis y seraient éparpillés. Choisissez "
                "« par niveau », ou assumez le serpent explicitement."
            ),
            etape.ordre,
        )


def _ne_donne_qu_un_groupe(etape: EtapeProjetable, reglage: ReglageDePoules) -> bool:
    """L'étape ne peut-elle composer qu'**une** poule, d'après tout ce qu'elle déclare (E05US029) ?

    On lit l'effectif **déclaré** — celui de l'étape *et* la largeur cumulée de ses fenêtres — et
    non un effectif de tournoi : le contrôle reste ainsi vrai à tout effectif, donc structurel, ce
    qui est la condition de la gravité bloquante (ADR-0063).

    ⚠️ **Les deux évidences doivent concorder, et la première version ne le faisait pas**
    (correctif de 2ᵉ passe, axes C1 et D). L'effectif déclaré court-circuitait la lecture des
    fenêtres — or ce n'est qu'une *déclaration*, jamais opposable : au tournoi c'est
    `len(participants)` qui compose. Une phase déclarant « 6 » avec une source « à partir du rang
    1 » recevait 36 archers, composait 6 poules au serpent après des poules, et le refus ne tombait
    pas. On ne se tait donc que si **aucun** signal déclarable n'annonce plus d'un groupe.

    ⚠️ **Un effectif déclaré invalide ne fait pas lever ici** (même correctif, axes A, C1 et D).
    `nb_poules_pour` refuse `effectif < 1`, et un `ModelePhase` de brouillon accepte `0` — c'est le
    régime d'ADR-0063, « l'enregistrement accepte le brouillon, le diagnostic dit pourquoi ». Sans
    cette garde, une `DomainError` s'échappait du générateur d'anomalies et le diagnostic répondait
    **422** au lieu de lister le défaut qu'`anomalies_etape` produit déjà. Le voisin
    `_motif_de_choc` portait cette précaution depuis toujours ; la fonction neuve ne l'avait pas.
    """
    if etape.effectif is not None:
        if etape.effectif < 1:
            # Effectif de brouillon : `anomalies_etape` le signale, on ne conclut rien ici.
            return False
        if nb_poules_pour(etape.effectif, reglage.taille_visee) > 1:
            return False
    largeurs = [_largeur(source) for source in etape.sources if source.nature is NatureSource.RANGS]
    if not largeurs or any(largeur == sys.maxsize for largeur in largeurs):
        # Fenêtre à fin ouverte : le compte n'est pas déclarable, donc on ne peut pas certifier le
        # groupe unique — « on ne refuse pas ce qu'on ne peut pas juger » vaut dans les deux sens.
        return (
            etape.effectif is not None
            and nb_poules_pour(etape.effectif, reglage.taille_visee) == 1
            and not largeurs
        )
    return nb_poules_pour(sum(largeurs), reglage.taille_visee) == 1


def _anomalies_blocs_orphelins(etapes: Sequence[EtapeProjetable]) -> Iterator[Anomalie]:
    """Une phase qui n'est pas la première et ne prélève nulle part : d'où viennent ses archers ?

    Le schéma dessinait sinon un rectangle isolé « effectif inconnu / suite inconnue » sous un
    verdict « tient debout » — le contraire exact de ce que le CA appelle « un trou visible ».

    ⚠️ **Avertissement, et non bloquant** — la revue a démontré que le bloquer serait une
    **régression**. Deux raisons, et la seconde suffirait :

    1. **C'est un déroulé livré et documenté.** `docs/fonctionnel/E05US015.md` (mergé la veille)
       décrit comme résultat attendu « enregistrez la phase d'élimination directe **sans source** :
       c'est accepté ». Un format promu depuis un tel tournoi serait devenu inapplicable après mise
       à jour — un format du club qui cesse de fonctionner.
    2. **Le message serait faux.** « Personne ne peut l'atteindre » suppose que le moteur lit les
       prélèvements. Il lit désormais ceux **par rangs** (E05US020, ADR-0068) ; pour les autres
       natures il ne les lit toujours pas (`# DETTE-028` : `_decor` ensemence avec
       *tous* les archers en lice) : une phase sans source accueille en réalité tout le monde.

    L'anomalie garde donc son utilité — elle **montre** le bloc qui ne dit pas d'où viennent ses
    archers — sans interdire ce que le produit accepte par ailleurs. Elle redeviendra candidate au
    blocage le jour où le peuplement honorera les sources, et c'est ce jour-là que la règle aura un
    sens dans `anomalies_sequence`, pour les phases d'un tournoi.

    La première phase, elle, se peuple des inscrits : son absence de source est normale.
    """
    if not etapes:
        return
    premier_ordre = min(etape.ordre for etape in etapes)
    for etape in etapes:
        if etape.ordre != premier_ordre and not etape.sources:
            yield Anomalie(
                PhaseSansSource(
                    f"La phase {etape.ordre} ne dit pas d'où viennent ses archers : elle ne "
                    "prélève dans aucune phase antérieure. Seule la première phase se peuple des "
                    "inscrits."
                ),
                etape.ordre,
                Gravite.AVERTISSEMENT,
            )


def _anomalies_effectif_declare(
    etape: EtapeProjetable, entrees: Sequence[Flux], resolu: int | None
) -> Iterator[Anomalie]:
    """L'effectif **déclaré** est-il tenable par ce que les prélèvements amènent réellement ?

    `_anomalies_somme` (`domain.phase`) abandonne l'égalité dès qu'un prélèvement est **relatif** —
    « le reste », une issue de tour, une fin ouverte — parce qu'elle ne se décide pas au format. Or
    la projection, elle, **sait** les résoudre à l'effectif simulé : ne pas s'en servir laissait
    dessiner une flèche « 120 » entrant dans un bloc « 16 archers », verdict vert.

    Conjoncturel par nature (le compte dépend de l'effectif) → avertissement, ADR-0063 §3.
    """
    if etape.effectif is None or not entrees or resolu is None:
        return
    if any(entree.effectif is None for entree in entrees):
        return
    # ⚠️ **Seulement là où `_anomalies_somme` abandonne.** Quand *tous* les prélèvements sont
    # dénombrables au format, elle rend déjà un `effectif_incompatible` **bloquant** : en ajouter un
    # second, avertissement et de même code, ferait remonter le même défaut deux fois avec deux
    # gravités. Le cas propre à la projection est celui du prélèvement **relatif** — « le reste »,
    # une issue de tour, une fin ouverte —, que le format ne sait pas compter et que l'effectif
    # simulé, lui, résout.
    if all(source.effectif_selectionne is not None for source in etape.sources):
        return
    apporte = sum(entree.effectif or 0 for entree in entrees)
    if apporte != etape.effectif:
        yield Anomalie(
            EffectifIncompatible(
                f"La phase {etape.ordre} déclare {etape.effectif} participants, mais ses "
                f"prélèvements en amènent {apporte} à cet effectif."
            ),
            etape.ordre,
            Gravite.AVERTISSEMENT,
        )


def _anomalies_choc_de_poule(
    etape: EtapeProjetable,
    entrees: Sequence[Flux],
    resolu: int | None,
    etapes: Sequence[EtapeProjetable],
    effectifs: dict[int, int | None],
) -> Iterator[Anomalie]:
    """Deux archers d'une même poule peuvent-ils se croiser au **premier tour** du tableau aval ?

    C'est l'exception mesurée d'ADR-0083 §6, signalée à l'atelier plutôt que corrigée en douce.

    ⚠️ **Deux oracles faux se sont succédé ici ; celui-ci est vérifié contre le moteur.** Le premier
    tenait « effectif puissance de 2 ⇒ pas de choc » — faux, un nombre **impair** de poules produit
    des chocs à tout effectif (à `P = 3` et 16 places, le serpent apparie (1, 16), soit le n° 1
    contre un membre de sa propre poule). Le second corrigeait la parité mais avertissait sur les
    **byes**, ce qui est un faux positif systématique à `P` pair, et se taisait sur des réglages où
    l'arithmétique ne s'applique tout simplement pas.

    Le prédicat retenu est exact **au serpent**, et il l'est au sens strict : `P impair ET
    (M+1+P)//2 <= N`, où
    `M` est la puissance de 2 **supérieure ou égale** à `N`. Confronté à l'appariement réel du
    serpent sur `P = 2..39` croisé avec `N = 2..256` — 9945 configurations —, **zéro désaccord**.
    ⚠️ Cette mesure ne dit **rien** du mode `PAR_NIVEAU`, qui révoque l'hypothèse d'espacement
    elle-même (E05US029) : ce cas est écarté en tête de `_motif_de_choc`, avant tout calcul.

    Avertissement, jamais bloquant : corriger demanderait une politique de croisement, donc une
    règle métier que personne n'a demandée (arbitrage du 09/08/2026). Et rien ne se signale sur une
    phase que le moteur ne monte pas — l'appariement n'y existe pas.
    """
    if resolu is None or resolu < 2 or etape.type not in TYPES_EN_TABLEAU:
        return
    if etape.type not in _TYPES_DEROULES:
        return
    amont = {autre.ordre: autre for autre in etapes}
    sources_poules = sorted(
        {
            entree.ordre_source
            for entree in entrees
            if amont.get(entree.ordre_source) is not None
            and amont[entree.ordre_source].type is TypePhase.POULES
        }
    )
    # ⚠️ **On ne cite que les phases réellement en cause.** Une version antérieure listait toutes
    # les sources de poules et ne rendait qu'un seul motif : un tableau nourri par une phase saine
    # et une phase à risque nommait les deux, et attribuait à la première le motif de la seconde.
    # C'est le défaut même que le bandeau d'atelier corrigeait un cran plus haut.
    en_cause = [
        (ordre, motif)
        for ordre in sources_poules
        if (motif := _motif_de_choc(resolu, amont[ordre], effectifs.get(ordre))) is not None
    ]
    if not en_cause:
        return
    citees = ", ".join(str(ordre) for ordre, _ in en_cause)
    motifs = " ; ".join(dict.fromkeys(motif for _, motif in en_cause))
    yield Anomalie(
        ChocDePoulePossible(
            f"La phase {etape.ordre} prélève {resolu} archers dans la phase {citees} (poules) : "
            f"{motifs}, donc deux archers d'une même poule peuvent se rencontrer dès le "
            "premier tour."
        ),
        etape.ordre,
        Gravite.AVERTISSEMENT,
    )


def _puissance_de_deux_au_moins(valeur: int) -> int:
    """La plus petite puissance de 2 supérieure ou égale à `valeur` — la **taille du tableau**."""
    taille = 1
    while taille < valeur:
        taille *= 2
    return taille


def _motif_de_choc(resolu: int, source: EtapeProjetable, effectif_resolu: int | None) -> str | None:
    """Pourquoi le serpent peut réunir deux membres d'une poule — ou `None` s'il ne le peut pas.

    Le raisonnement ne vaut que sous une hypothèse : **le membre `k` d'une poule occupe les rangs
    `k, k+P, k+2P…`** du classement de phase. Quatre choses la cassent, et chacune est vérifiée ici
    plutôt que supposée — c'est ce qui a manqué à la version précédente :

    1. le **départage inter-poules** : `classement_de_poules` trie alors chaque bloc de niveau
       indépendamment, si bien que la position d'une poule change d'un bloc à l'autre. Le module le
       documente lui-même (« le départage peut réordonner un bloc »). Aggravant : c'est le geste que
       le produit **recommande** quand un prélèvement coupe un bloc (ADR-0081), donc le cas est
       fréquent, pas exotique ;
    2. des **poules de tailles inégales** : au-delà du dernier niveau complet, le bloc est plus
       court que `P` et l'espacement n'est plus régulier. On ne conclut donc que si le prélèvement
       tient dans les niveaux pleins ;
    3. un **nombre de poules inconnu** (phase non réglée, effectif ni résolu ni déclaré).

    Dans ces trois cas on **signale** : l'innocuité n'est pas démontrable, et un avertissement de
    trop coûte une lecture là où un avertissement manquant coûte un tournoi mal apparié.

    4. le mode **`PAR_NIVEAU`** (E05US029) casse l'hypothèse d'une **quatrième** façon, et c'est la
       seule qui ne mène pas à « signaler faute de savoir » : les membres d'une poule y occupent des
       rangs **contigus**, donc l'appariement se **calcule** exactement
       (`_choc_entre_tranches`) au lieu de se supposer. Ce cas ne passe jamais par l'arithmétique
       d'espacement ci-dessous — il en sort avant.
    """
    reglage = source.poules
    effectif = effectif_resolu if effectif_resolu is not None else source.effectif
    if reglage is None or effectif is None or effectif < 1:
        return (
            "le nombre de poules ne se déduit pas de ce schéma (phase non réglée, ou effectif "
            "inconnu), donc l'appariement ne peut pas être prouvé sûr"
        )
    if reglage.mode is ModeDeComposition.PAR_NIVEAU:
        # ⚠️ **La 4ᵉ chose qui casse l'hypothèse d'espacement** (E05US029, relevée par trois axes de
        # revue). Tout ce qui suit repose sur « le membre `k` occupe les rangs `k, k+P, k+2P…` » —
        # c'est la lecture **au serpent**. Par niveau, `classement_de_poules` range groupe par
        # groupe : les membres d'une poule occupent des rangs **contigus**, et le prédicat validé
        # sur 9945 configurations ne décrit plus rien.
        #
        # ⚠️ **On calcule le prédicat exact plutôt que de signaler par prudence** (2ᵉ correctif de
        # revue). Une première version rendait le motif **inconditionnellement**, en affirmant que
        # c'était « exact plutôt que prudent » : mesuré, c'était faux **une fois sur quatre**
        # (25,1 % de faux positifs sur 89 408 configurations, axe D). Or les tranches étant
        # **contiguës et dérivables**, l'appariement se vérifie directement — et un avertissement
        # systématique sur un format nominal est le bruit qui fait ignorer les vrais signaux,
        # exactement l'argument que cette fonction oppose déjà à l'un de ses oracles passés.
        return _choc_entre_tranches(effectif, resolu, reglage.taille_visee)
    if reglage.departage_inter_poules:
        return (
            "le départage inter-poules réordonne chaque bloc de rangs, donc les membres d'une "
            "poule ne sont plus régulièrement espacés"
        )
    try:
        nb_poules = nb_poules_pour(effectif, reglage.taille_visee)
    except ConfigurationPouleInvalide:
        return "le réglage de poules est incohérent, donc l'appariement n'est pas calculable"
    if resolu > (effectif // nb_poules) * nb_poules:
        return (
            f"le prélèvement dépasse les {(effectif // nb_poules) * nb_poules} premiers rangs, "
            "au-delà desquels les poules n'ont plus toutes le même effectif"
        )
    taille_tableau = _puissance_de_deux_au_moins(resolu)
    if nb_poules % 2 == 1 and (taille_tableau + 1 + nb_poules) // 2 <= resolu:
        return f"le nombre de poules ({nb_poules}) est impair, donc le serpent ne les sépare pas"
    return None


def _choc_entre_tranches(effectif: int, resolu: int, taille_visee: int) -> str | None:
    """Le tableau apparie-t-il deux membres d'une **même tranche de niveau** au premier tour ?

    Exact, et vérifiable à la main : les groupes sont des intervalles de rangs (`tailles_de_niveau`,
    domicile unique de la règle), et le tableau oppose le rang `r` au rang `M+1-r` où `M` est sa
    taille — la puissance de 2 au moins égale au prélèvement. Il y a choc dès qu'une de ces paires
    tombe deux fois dans la même tranche.

    Rend `None` — donc *pas* d'avertissement — dans le cas nominal que le format vise : un
    prélèvement de **groupes entiers** (« les rangs 1 à 16 » sur des groupes de 8) apparie
    systématiquement le groupe A contre le groupe B, et ne réunit personne.
    """
    try:
        nb_poules = nb_poules_pour(effectif, taille_visee)
    except ConfigurationPouleInvalide:
        return "le réglage de poules est incohérent, donc l'appariement n'est pas calculable"
    groupe_du_rang: dict[int, int] = {}
    rang = 1
    for numero, taille in enumerate(tailles_de_niveau(effectif, nb_poules)):
        for _ in range(taille):
            groupe_du_rang[rang] = numero
            rang += 1
    taille_tableau = _puissance_de_deux_au_moins(resolu)
    for rang in range(1, resolu + 1):
        adverse = taille_tableau + 1 - rang
        if adverse <= rang or adverse > resolu:
            continue
        if groupe_du_rang.get(rang) == groupe_du_rang.get(adverse):
            return (
                f"les groupes sont composés par niveau, donc contigus, et le tableau apparie les "
                f"rangs {rang} et {adverse} — tous deux de la même poule"
            )
    return None


# --- Résolution d'un prélèvement -----------------------------------------------------------------


def _resoudre(
    etape: EtapeProjetable,
    source: SourcePhase,
    effectifs: dict[int, int | None],
    tranches: dict[int, tuple[int, int] | None],
    braquets: dict[int, tuple[TourBraquet, ...]],
    etapes: Sequence[EtapeProjetable],
    conjoncturelles: list[Anomalie],
) -> Flux:
    """Compte ce que ce prélèvement prend réellement, et signale ce qui ne tient pas à cet effectif.

    Les phases sont projetées dans l'ordre : quand on résout une source, sa phase amont est déjà
    comptée. Une source qui pointe vers l'aval (défaut structurel, déjà signalé comme bloquant) rend
    un flux à l'effectif inconnu plutôt que de faire échouer le calcul.
    """
    amont = effectifs.get(source.ordre_source)

    def flux(
        effectif: int | None, rang_debut: int | None = None, rang_fin: int | None = None
    ) -> Flux:
        return Flux(
            ordre_source=source.ordre_source,
            ordre_cible=etape.ordre,
            nature=source.nature,
            effectif=effectif,
            rang_debut=rang_debut,
            rang_fin=rang_fin,
            tour=source.tour,
            issue=source.issue,
        )

    if source.nature is NatureSource.RANGS:
        if amont is None:
            return flux(None, source.rang_debut, source.rang_fin)
        if source.rang_fin is not None and source.rang_fin > amont:
            conjoncturelles.append(
                Anomalie(
                    RangsSourceInexistants(
                        f"La phase {etape.ordre} prélève jusqu'au rang {source.rang_fin} de la "
                        f"phase {source.ordre_source}, qui n'en classe que {amont} à cet effectif.",
                    ),
                    etape.ordre,
                    Gravite.AVERTISSEMENT,
                )
            )
        fin = min(source.rang_fin if source.rang_fin is not None else amont, amont)
        compte = max(0, fin - source.rang_debut + 1)
        if compte == 0:
            conjoncturelles.append(
                Anomalie(
                    PrelevementVide(
                        f"La phase {etape.ordre} prélève à partir du rang {source.rang_debut} de "
                        f"la phase {source.ordre_source}, qui n'en classe que {amont} : ce "
                        "prélèvement ne prend personne.",
                    ),
                    etape.ordre,
                    Gravite.AVERTISSEMENT,
                )
            )
        return flux(compte, source.rang_debut, fin if compte else None)

    if source.nature is NatureSource.ISSUE_DE_TOUR:
        return flux(_compte_issue_de_tour(source, braquets, effectifs))

    # « Le reste » : ce qu'aucun **autre** prélèvement de la séquence n'a pris dans cette phase.
    return flux(_compte_du_reste(source, etape, etapes, amont))


def _compte_issue_de_tour(
    source: SourcePhase,
    braquets: dict[int, tuple[TourBraquet, ...]],
    effectifs: dict[int, int | None],
) -> int | None:
    """Combien sortent d'un tour : les duels du tour disent les perdants, la moitié dit les
    gagnants."""
    tours = braquets.get(source.ordre_source, ())
    amont = effectifs.get(source.ordre_source)
    if source.tour is None or amont is None or not tours or source.tour > len(tours):
        return None
    tour = tours[source.tour - 1]
    if source.issue is IssueTour.PERDANTS:
        return tour.duels
    # Les gagnants du tour *t* sont les places encore ouvertes après lui : la moitié haute.
    debut, fin = tour.plage_gagnants
    return fin - debut + 1


def _compte_du_reste(
    source: SourcePhase,
    etape: EtapeProjetable,
    etapes: Sequence[EtapeProjetable],
    amont: int | None,
) -> int | None:
    """« Tout ce qu'aucune autre source n'a prélevé » — le complément, calculé sur la séquence.

    « Autre » s'entend sur **toute** la séquence, pas seulement sur la phase courante : deux phases
    qui puisent dans la même qualification se partagent ses classés. Indéterminable si l'un des
    autres prélèvements l'est.
    """
    if amont is None:
        return None
    pris = 0
    for autre in etapes:
        for candidate in autre.sources:
            if candidate.ordre_source != source.ordre_source:
                continue
            if autre.ordre == etape.ordre and candidate == source:
                continue
            if candidate.nature is not NatureSource.RANGS:
                return None
            fin = min(candidate.rang_fin if candidate.rang_fin is not None else amont, amont)
            pris += max(0, fin - candidate.rang_debut + 1)
    return max(0, amont - pris)


# --- Effectif, tranche, braquets d'un bloc -------------------------------------------------------


def _effectif_du_bloc(
    etape: EtapeProjetable,
    entrees: Sequence[Flux],
    effectif_simule: int | None,
    premier_ordre: int | None,
) -> int | None:
    """Combien d'archers ce bloc accueille.

    Un effectif **déclaré** sur la phase prime : c'est une contrainte du format (« ce tableau est à
    16 »), pas une inconnue à deviner. Sinon la première phase reçoit tout le monde, et les autres
    la somme de leurs prélèvements — inconnue dès qu'un seul l'est.
    """
    if etape.effectif is not None:
        return etape.effectif
    if not etape.sources:
        return effectif_simule if etape.ordre == premier_ordre else None
    if any(entree.effectif is None for entree in entrees):
        return None
    return sum(entree.effectif or 0 for entree in entrees)


def _tranche_du_bloc(
    etape: EtapeProjetable,
    entrees: Sequence[Flux],
    resolu: int | None,
    premier_ordre: int | None,
    braquets: dict[int, tuple[TourBraquet, ...]],
) -> tuple[int, int] | None:
    """La tranche de **rangs du tournoi** que ce bloc se partage — son braquet d'entrée.

    Connue dans trois cas seulement : la phase d'entrée (tout le monde, rangs 1..N), un prélèvement
    unique par rangs (la tranche prélevée), un prélèvement unique par issue de tour (la plage des
    gagnants ou des perdants de ce tour, déjà calculée en amont par la *Règle R*). Deux
    prélèvements venus d'endroits différents ne forment **pas** une tranche contiguë : rendre
    `None` est plus honnête qu'une enveloppe qui mentirait sur les rangs intermédiaires.
    """
    if not etape.sources:
        return (1, resolu) if etape.ordre == premier_ordre and resolu else None
    if len(entrees) != 1:
        return None
    entree = entrees[0]
    if entree.nature is NatureSource.RANGS:
        if entree.rang_debut is None or entree.rang_fin is None:
            return None
        return (entree.rang_debut, entree.rang_fin)
    if entree.nature is NatureSource.ISSUE_DE_TOUR and entree.tour is not None:
        tours = braquets.get(entree.ordre_source, ())
        if entree.tour > len(tours):
            return None
        tour = tours[entree.tour - 1]
        return tour.plage_perdants if entree.issue is IssueTour.PERDANTS else tour.plage_gagnants
    return None


def _braquets(
    etape: EtapeProjetable, resolu: int | None, tranche: tuple[int, int] | None
) -> tuple[TourBraquet, ...]:
    """Déroule la *Règle R* : à chaque tour, les gagnants gardent la moitié haute, les perdants
    prennent la basse, jusqu'à la paire terminale.

    Calculé seulement pour les phases **en tableau** et quand la tranche d'entrée est connue : sans
    elle, les rangs rendus seraient relatifs au tableau, donc faux dès qu'il ne part pas du rang 1.

    Le nombre de duels d'un tour est `engagés - places gagnantes` : au premier tour d'un tableau
    incomplet, cela donne exactement les byes que `ByesAuxMieuxClasses` distribuera (24 duellistes
    dans un tableau de 32 → 8 duels, 8 exemptés). La somme des duels vaut toujours `effectif - 1`.

    ⚠️ `# DETTE-035` — c'est l'arbre **nu** : les duels que la politique `depth` ajoute (une petite
    finale au preset, toute la cascade de placement en 1→N) **n'y sont pas comptés**. Depuis
    E06US006 l'organisateur choisit cette profondeur juste à côté du schéma, sans en voir le coût
    en duels. Les deux corrections évidentes sont pires que le mal (ensemencer un vrai tableau ici,
    ou recopier la formule de l'arbre) : cf. le registre de dette.
    """
    if etape.type not in TYPES_EN_TABLEAU or resolu is None or tranche is None or resolu < 2:
        return ()
    taille = 1 << (resolu - 1).bit_length()
    plage = Plage(tranche[0], tranche[0] + taille - 1)
    tours: list[TourBraquet] = []
    engages = resolu
    numero = 1
    while True:
        if plage.est_terminale:
            tours.append(
                TourBraquet(
                    numero,
                    1 if engages >= 2 else 0,
                    (plage.debut, plage.debut),
                    (plage.fin, plage.fin),
                )
            )
            return tuple(tours)
        haute, basse = plage.moitie_haute(), plage.moitie_basse()
        gagnants = plage.largeur // 2
        tours.append(
            TourBraquet(
                numero,
                max(0, engages - gagnants),
                (haute.debut, haute.fin),
                (basse.debut, basse.fin),
            )
        )
        plage, engages, numero = haute, gagnants, numero + 1


# --- Assemblage du bloc --------------------------------------------------------------------------


def _bloc(
    etape: EtapeProjetable,
    effectifs: dict[int, int | None],
    tranches: dict[int, tuple[int, int] | None],
    braquets: dict[int, tuple[TourBraquet, ...]],
    flux: Sequence[Flux],
    anomalies: Sequence[Anomalie],
) -> BlocDeroule:
    entrees = tuple(f for f in flux if f.ordre_cible == etape.ordre)
    sorties = tuple(f for f in flux if f.ordre_source == etape.ordre)
    resolu = effectifs[etape.ordre]
    return BlocDeroule(
        ordre=etape.ordre,
        type=etape.type,
        effectif=resolu,
        tranche=tranches[etape.ordre],
        nb_volees=etape.bareme.nb_volees if etape.bareme is not None else None,
        nb_fleches_par_volee=(
            etape.bareme.nb_fleches_par_volee if etape.bareme is not None else None
        ),
        tours=braquets[etape.ordre],
        entrees=entrees,
        sorties=sorties,
        sans_suite=_sans_suite(resolu, sorties),
        anomalies=tuple(a for a in anomalies if a.ordre == etape.ordre),
    )


def _sans_suite(resolu: int | None, sorties: Sequence[Flux]) -> int | None:
    """Combien d'archers voient leur tournoi s'arrêter dans ce bloc — le reste du CA « trou ».

    Ce n'est pas une anomalie en soi : les 88 non-qualifiés d'une qualification à 120 gardent leur
    rang et rentrent chez eux, c'est le déroulé normal. Ce que le CA demande, c'est que le dessin le
    **montre** au lieu de le laisser deviner.

    ⚠️ **Rend une valeur signée.** Un premier jet écrasait le négatif par `max(0, …)` en affirmant
    « négatif impossible : une sur-souscription est déjà un recoupement, signalé comme tel ». C'est
    faux, et c'est exactement ce qui a laissé passer le trou : `_anomalies_recoupements` compare les
    prélèvements **d'une même phase cible**, jamais ceux de deux phases avales différentes puisant
    dans la même source. « Rangs 1 à 32 » puis « rangs 32 à 64 » — l'erreur de borne d'un rang —
    passait donc au vert. Le négatif est désormais **rendu**, et `_anomalies_sur_souscription` le
    signale.
    """
    if resolu is None or any(sortie.effectif is None for sortie in sorties):
        return None
    return resolu - sum(sortie.effectif or 0 for sortie in sorties)


def _anomalies_sur_souscription(
    etape: EtapeProjetable, resolu: int | None, sorties: Sequence[Flux]
) -> Iterator[Anomalie]:
    """Les phases avales prélèvent-elles, **ensemble**, plus que ce bloc ne compte de participants ?

    Le contrôle manquait : `_anomalies_recoupements` (`domain.phase`) juge le recoupement *par phase
    cible*, ce qui laisse deux phases avales se disputer les mêmes rangs sans que rien ne le dise.
    Comme il dépend de l'effectif résolu, il est **conjoncturel** — donc avertissement (ADR-0063
    §3) : les mêmes plages peuvent tenir à 120 et déborder à 82.
    """
    reste = _sans_suite(resolu, sorties)
    if reste is None or reste >= 0 or resolu is None:
        return
    yield Anomalie(
        SourcesQuiSeRecoupent(
            f"Les phases suivantes prélèvent au total {resolu - reste} participants dans la phase "
            f"{etape.ordre}, qui n'en compte que {resolu} : {-reste} archer(s) sont pris deux fois."
        ),
        etape.ordre,
        Gravite.AVERTISSEMENT,
    )
