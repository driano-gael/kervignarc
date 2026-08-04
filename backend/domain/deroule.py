"""Projection d'un **déroulé** : ce qu'un format produit à un effectif donné (E01US024, ADR-0063).

C'est le calcul derrière le « schéma à braquets » du CA — *« un visuel découpé par phase qui montre
où sont les archers, ce qui leur est demandé, où ils iront après leur phase […] en fonction du
nombre d'archers »*. Le module rend des **faits structurés** (combien, quelle tranche de rangs,
quelles flèches, combien de tours) ; l'habillage — libellés, SVG, couleurs — est au front.

**Pourquoi ici et pas côté front.** Les braquets sont la *Règle R* de
`moteur-placement-lucky-loser.md` (« les perdants du tour *t* forment la tranche de rangs basse
encore ouverte »), déjà portée par `domain.plage.Plage`. La recalculer en TypeScript dupliquerait un
invariant du moteur — exactement ce que le registre de dette proscrit. Le domaine projette, le front
dessine.

**Deux régimes d'anomalie** (ADR-0063 §3). Les défauts **structurels** viennent des générateurs de
`domain.phase` (`anomalies_sequence`, `anomalies_etape`) : ils sont vrais quel que soit l'effectif,
donc **bloquants**. Les défauts **conjoncturels** naissent ici, à la résolution : « les rangs 33 à
120 » sur 82 inscrits, une phase que plus personne n'atteint. Ils **avertissent** sans bloquer —
sans quoi les plages relatives du CA d'E05US010 (« composé pour 120, jouable à 82 ») seraient
inutilisables.

**Ce que ce module ne prétend pas savoir.** Le nombre de tours n'est calculé que pour les phases
**en tableau** (élimination directe, placement), où il se déduit de l'effectif. Poules, système
suisse, colline le tirent d'une configuration que le domaine ne modélise pas encore (`# DETTE-028`)
— la projection rend alors un bloc sans tours plutôt qu'un chiffre inventé.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Protocol

from domain.anomalie import Anomalie, Gravite
from domain.bareme import BaremeQualification
from domain.erreurs import (
    EffectifIncompatible,
    PhaseSansParticipant,
    PhaseSansSource,
    PrelevementVide,
    RangsSourceInexistants,
    SourcesQuiSeRecoupent,
)
from domain.grain_validation import GrainValidation
from domain.phase import (
    EtapeSequencee,
    IssueTour,
    NatureSource,
    SourcePhase,
    TypePhase,
    anomalies_etape,
    anomalies_sequence,
)
from domain.plage import Plage

_TYPES_EN_TABLEAU = frozenset({TypePhase.ELIMINATION_DIRECTE, TypePhase.PLACEMENT})
"""Les types dont le déroulé est un **arbre** : leur nombre de tours se déduit de l'effectif seul.

Les six autres types du catalogue (E05US015) tirent le leur d'une configuration que ni `Phase` ni
`ModelePhase` ne portent encore — cf. `# DETTE-028`."""

_TYPES_SANS_OPPOSITION = frozenset({TypePhase.QUALIFICATION, TypePhase.ECHAUFFEMENT})
"""Les types où l'archer tire **seul** : un participant leur suffit (E05US021).

Liste énoncée **en négatif** des six autres à dessein. Poule, système suisse, colline, Big Shoot
Off, barrage et les deux tableaux **opposent** des tireurs : il leur en faut deux. Énumérer les
« accueillants » plutôt que les « opposants » fait qu'un type ajouté au catalogue hérite du
plancher **prudent** (2) au lieu du permissif — un oubli y sur-protège au lieu de laisser passer."""


class EtapeProjetable(EtapeSequencee, Protocol):
    """Ce dont la projection a besoin d'une étape : la séquence, **plus** ce qu'on y demande.

    Élargit `EtapeSequencee` de `bareme` et `validation` — la quatrième question du CA (« ce qu'on
    leur demande ») ne se répond pas sans eux. L'élargissement reste ici plutôt que dans
    `domain.phase` : les contrôles de séquence n'en ont, eux, toujours pas besoin, et le protocole
    d'origine documente précisément cette frontière. `Phase` et `ModelePhase` satisfont les deux.
    """

    @property
    def bareme(self) -> BaremeQualification | None: ...

    @property
    def validation(self) -> GrainValidation | None: ...


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

    **Le seul classement traduisible en inscrits est celui de la QUALIFICATION** — et c'est une
    contrainte du **moteur**, pas une commodité. `ServiceSaisieDuels._ordre_de_la_qualification`
    n'honore les prélèvements que s'ils visent la phase de type `qualification` ; tout autre
    prélèvement par rangs est ignoré et la phase reçoit *tous* les archers en lice (`# DETTE-028`).
    Ce plancher doit donc viser **exactement ce que le moteur lira**, sinon il ment dans les deux
    sens — et il a menti dans les deux sens avant d'être corrigé :

    - viser la **première phase** au lieu de la qualification laissait passer un déroulé
      « échauffement → qualification → tableau 33+ » avec un plancher de 1, alors que le moteur
      lèverait `EffectifTableauInvalide` en salle. C'est le défaut même que l'US retire ;
    - à l'inverse, un déroulé **sans qualification** se voyait réclamer 34 inscrits alors que le
      moteur, n'ayant aucun classement à lire, ensemence avec tout le monde et se contente de deux.
      Un refus abusif le jour J coûte aussi cher qu'un oubli.

    D'où : sans phase de qualification, **aucun prélèvement par rangs n'est traduisible** et seul le
    plancher structurel de chaque étape subsiste.

    **Portée délibérément étroite** (note du CA). Un rang se lit dans le classement de sa **phase
    source** : « les rangs 33 et suivants *du tableau* » ne dit rien sur le nombre d'inscrits
    nécessaires, et l'inclure produirait un chiffre **faux** — pire que pas de chiffre. Même raison
    pour les natures qui ne se lisent pas en rangs (`issue_de_tour`, `le_reste`), dont le compte
    dépend du déroulé.

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

    ordre_qualification = next(
        (etape.ordre for etape in triees if etape.type is TypePhase.QUALIFICATION), None
    )
    exigence = ExigenceEffectif(minimum=1)
    for etape in triees:
        candidate = _exigence_de_letape(etape, ordre_qualification)
        if candidate.minimum > exigence.minimum:
            exigence = candidate
    return exigence


def _exigence_de_letape(etape: EtapeSequencee, ordre_qualification: int | None) -> ExigenceEffectif:
    """Le plancher d'inscrits qu'une seule étape réclame.

    `base` est le plancher **structurel** : ce qu'il faut pour que l'étape ait un sens, quelle que
    soit sa provenance. Il est retenu dans **tous** les cas de repli — une phase à duels alimentée
    par « le reste » reste une phase à duels, et le moteur lui demandera deux tireurs.
    """
    base = 1 if etape.type in _TYPES_SANS_OPPOSITION else 2

    if not etape.sources:
        # Aucun prélèvement : la phase se peuple des inscrits (la première), ou de tout le monde
        # faute que le moteur sache lire ses sources (`# DETTE-028`). Dans les deux cas, il lui faut
        # juste de quoi tenir debout.
        return ExigenceEffectif(minimum=base)

    if ordre_qualification is None:
        # Aucun classement à lire : le moteur ignore les prélèvements et ensemence avec tous les
        # archers en lice. Réclamer le rang de départ serait un refus abusif.
        return ExigenceEffectif(minimum=base)

    rangs = [
        source.rang_debut
        for source in etape.sources
        if source.nature is NatureSource.RANGS and source.ordre_source == ordre_qualification
    ]
    if not rangs:
        return ExigenceEffectif(minimum=base)

    plus_bas = min(rangs)
    return ExigenceEffectif(minimum=plus_bas - 1 + base, ordre=etape.ordre, rang_debut=plus_bas)


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
    """
    if etape.type not in _TYPES_EN_TABLEAU or resolu is None or tranche is None or resolu < 2:
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
