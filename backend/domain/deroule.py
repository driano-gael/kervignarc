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

Dérivé de la capacité `deroule_par_un_service` (ADR-0083). ⚠️ À ne pas confondre avec
`TYPES_EN_TABLEAU` : celui-ci répond « sait-on dessiner ses tours ? », celui-là « le moteur va-t-il
seulement monter cette phase ? ». Les types sans consommateur de production (`# DETTE-028`) n'y
figurent pas — leur prélèvement ne sera pas honoré, donc il ne peut justifier un refus de démarrage.
E05US023 y fait entrer les **poules** et en sort `placement`, qu'aucun service ne monte.
"""


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
        lui. Le nombre de poules et le fait qu'un départage inter-poules soit demandé décident si le
        serpent peut réunir deux membres d'un même groupe au premier tour.
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

    `anomalies` porte **tout**, y compris ce qui est déjà rattaché à un bloc, pour qu'un appelant
    qui ne veut qu'un verdict n'ait pas à parcourir les blocs. `effectif_minimum` est le plancher
    d'inscrits **déduit** des prélèvements (E05US021) — une donnée, **pas** une anomalie de plus :
    le cas « ce prélèvement ne prend personne » remonte déjà en `PrelevementVide`.
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

    Sans effectif, le format « reste abstrait » (CA) : la projection décrit sa structure sans
    compter personne. ⚠️ **Tolérante par construction** : une séquence incohérente ne fait pas
    échouer le calcul, elle le **décrit** — un brouillon doit pouvoir être regardé.
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

    Une phase à duels veut **deux** participants ; « à partir du rang *d* » n'en trouve deux que si
    sa source en classe *d + 1*, d'où `d - 1 + 2` inscrits. ⚠️ Le plancher vise **exactement ce que
    le moteur lira** (`_TYPES_CLASSANTS_LUS`) : viser autre chose ment dans les deux sens — tableau
    qui casse en salle, ou refus abusif le jour J. ⚠️ **La chaîne se remonte** (E05US024), et une
    fenêtre amont **bornée** ne fixe aucun plancher. Entre phases, le plus exigeant l'emporte.
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

Dérivé de la capacité `classement_lisible` (ADR-0083). ⚠️ **À ne pas confondre avec
`_TYPES_DEROULES`** : celui-là répond « le moteur va-t-il *monter* cette phase ? », celui-ci
« sait-il *lire ce qu'elle a classé* ? » — `qualification` est lue sans être montée, et c'est
pourquoi ce sont deux capacités et non une. Miroir exact de
`ServiceSaisieDuels._classement_de_l_ordre` : les faire diverger rouvre le défaut d'E05US021.
"""


def _exigence_de_letape(
    etape: EtapeSequencee, par_ordre: dict[int, EtapeSequencee]
) -> ExigenceEffectif:
    """Le plancher d'inscrits qu'une seule étape réclame.

    `base` est le plancher **structurel** — ce qu'il faut pour que l'étape ait un sens —, retenu
    dans **tous** les cas de repli. ⚠️ **Le plancher par rangs ne vaut que pour ce que le moteur
    déroule vraiment** : refuser un démarrage pour une phase que rien n'exécute est un **refus
    abusif**, le pire mode de défaillance de cette US puisqu'il ne se répare que le jour J. L'oracle
    « ce que le moteur lira » s'applique dans les deux sens, pas seulement dans le permissif.
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

    # ⚠️ **E05US024 — on remonte la chaîne.** Une source peut viser un **tableau**, qui a lui-même
    # prélevé : « les rangs 5+ d'un tableau qui prend les rangs 17 à 32 » réclame **22** inscrits
    # (17 - 1 + (5 - 1 + 2)), pas 6. Sans remonter, le plancher annoncé serait trop bas.
    #
    # ⚠️ Le `min` porte sur les **exigences**, pas sur les `rang_debut` : deux sources peuvent viser
    # des phases de profondeurs différentes. Et la source retenue **voyage avec son exigence** —
    # sinon le message rend un chiffre et une fenêtre qui ne se correspondent pas, et peut nommer
    # une fenêtre infaisable à tout effectif.
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

    La récursion du plancher (E05US024) : prélever « à partir du rang *a* » demande que **sa**
    source en classe `a - 1 + combien`. Rend **`None`** quand aucun effectif ne suffirait — une
    fenêtre **bornée** ne classera jamais plus que sa largeur : défaut de composition, pas plancher.
    ⚠️ **`vus` est ce qui fait terminer cette fonction** : `projeter` est tolérante par contrat, un
    brouillon qui se désigne lui-même en source est persistable, et l'écran partait en 500.
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

    **Structurel, donc bloquant** (ADR-0063) : équilibrer des groupes dont les niveaux sont déjà
    connus est l'inverse de ce que cet enchaînement cherche, à 12 archers comme à 120.
    ⚠️ Le prédicat porte sur la **source**, pas sur le rang dans le déroulé ; seules les sources
    `RANGS` comptent (les autres sont inertes, `DETTE-033`) ; une phase qui ne peut donner qu'**un**
    groupe n'est jamais en cause ; et le périmètre est borné aux sources de type poules par le CA.
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

    On lit l'effectif **déclaré** — celui de l'étape *et* la largeur cumulée de ses fenêtres — pour
    que le contrôle reste vrai à tout effectif, condition de la gravité bloquante (ADR-0063).
    ⚠️ Les deux évidences doivent **concorder** : un effectif déclaré n'est jamais opposable (au
    tournoi c'est `len(participants)` qui compose), donc on ne se tait que si **aucun** signal
    n'annonce plus d'un groupe. ⚠️ Un effectif déclaré invalide ne fait pas lever ici (ADR-0063).
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

    Le schéma dessinait sinon un rectangle isolé sous un verdict « tient debout » — le contraire de
    ce que le CA appelle « un trou visible ».
    ⚠️ **Avertissement, et non bloquant** : c'est un déroulé livré et documenté
    (`docs/fonctionnel/E05US015.md`), et le message serait faux — le moteur ne lit pas encore toutes
    les natures de prélèvement (`# DETTE-028`), donc une phase sans source accueille tout le monde.
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

    `_anomalies_somme` abandonne l'égalité dès qu'un prélèvement est **relatif**, parce qu'elle ne
    se décide pas au format. Or la projection **sait** les résoudre à l'effectif simulé : ne pas
    s'en servir laissait dessiner une flèche « 120 » entrant dans un bloc « 16 archers », au vert.
    Conjoncturel par nature → avertissement (ADR-0063 §3).
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

    L'exception mesurée d'ADR-0083 §6, signalée à l'atelier plutôt que corrigée en douce.

    ⚠️ **Deux oracles faux se sont succédé ici ; celui-ci est vérifié contre le moteur** : `P impair
    ET (M+1+P)//2 <= N`, où `M` est la puissance de 2 ≥ `N` — zéro désaccord sur 9945 configurations
    au serpent. Il ne dit **rien** du mode `PAR_NIVEAU`, écarté en tête de `_motif_de_choc`.
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

    Le raisonnement suppose que **le membre `k` d'une poule occupe les rangs `k, k+P, k+2P…`**.
    Trois choses la cassent sans qu'on puisse conclure — départage inter-poules (qui réordonne un
    bloc), poules de tailles inégales, nombre de poules inconnu — et on **signale** alors, faute de
    pouvoir démontrer l'innocuité. Le mode **`PAR_NIVEAU`** la casse d'une quatrième façon, la seule
    calculable : les rangs y sont contigus, donc `_choc_entre_tranches` tranche exactement.
    """
    reglage = source.poules
    effectif = effectif_resolu if effectif_resolu is not None else source.effectif
    if reglage is None or effectif is None or effectif < 1:
        return (
            "le nombre de poules ne se déduit pas de ce schéma (phase non réglée, ou effectif "
            "inconnu), donc l'appariement ne peut pas être prouvé sûr"
        )
    if reglage.mode is ModeDeComposition.PAR_NIVEAU:
        # ⚠️ **La 4ᵉ chose qui casse l'hypothèse d'espacement** (E05US029). Tout ce qui suit repose
        # sur « le membre `k` occupe les rangs `k, k+P, k+2P…` », la lecture **au serpent** ; par
        # niveau, les membres d'une poule occupent des rangs **contigus**.
        #
        # ⚠️ **On calcule le prédicat exact plutôt que de signaler par prudence** : une première
        # version rendait le motif inconditionnellement — 25,1 % de faux positifs mesurés sur
        # 89 408 configurations. Un avertissement systématique est le bruit qui fait ignorer les
        # vrais signaux.
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

    Exact et vérifiable à la main : les groupes sont des intervalles de rangs (`tailles_de_niveau`,
    domicile unique de la règle), et le tableau oppose le rang `r` au rang `M+1-r`. Il y a choc dès
    qu'une paire tombe deux fois dans la même tranche. Rend `None` dans le cas nominal — un
    prélèvement de **groupes entiers** apparie le groupe A contre le B et ne réunit personne.
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
    """Déroule la *Règle R* : à chaque tour, les gagnants gardent la moitié haute, les perdants la
    basse, jusqu'à la paire terminale.

    Calculé pour les phases **en tableau** et quand la tranche d'entrée est connue : sans elle, les
    rangs seraient relatifs au tableau, donc faux dès qu'il ne part pas du rang 1. Le nombre de
    duels d'un tour est `engagés - places gagnantes`, la somme valant `effectif - 1`.
    ⚠️ `# DETTE-035` — c'est l'arbre **nu** : les duels ajoutés par `depth` n'y sont pas comptés.
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

    Ce n'est pas une anomalie : les 88 non-qualifiés d'une qualification à 120 rentrent chez eux.
    Le CA demande que le dessin le **montre**.
    ⚠️ **Rend une valeur signée.** `_anomalies_recoupements` compare les prélèvements d'une **même**
    phase cible, jamais ceux de deux phases avales puisant dans la même source : « rangs 1 à 32 »
    puis « rangs 32 à 64 » passait au vert. `_anomalies_sur_souscription` le signale désormais.
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
