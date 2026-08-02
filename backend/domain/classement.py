"""Calcul du classement de qualification — logique de domaine **pure** (E06US001).

`calculer_classement` ordonne les archers d'un tournoi sur leur **score cumulé** (la somme de
leurs volées **validées**, cf. `Serie.cumul`), puis applique le **départage FFTA** à total égal :
plus grand nombre de **10**, puis de **9** (`docs/referentiel-ffta.md` §8.1, art. C.3 — spécifique
au tir à 18 m). Les deux critères sont **séquentiels** (le nombre de 9 ne départage que si les 10
sont à égalité) et ne jouent **qu'à** total égal. Si l'égalité subsiste après les 10 et les 9,
E06US001 laisse l'**ex æquo** par défaut : les deux archers partagent le rang. Départager les places
à enjeu par un **barrage** de tir (§8.2) reste une **option configurable** (E06US003 ; politique
`tiebreak` d'ADR-0004) — les deux résolutions restent ouvertes, seul le défaut est fixé ici. Le X
(mouche) n'est pas un score distinct (ADR-0020) : on départage sur les 10, pas sur les X.

Chaque ligne porte **deux rangs** (arbitrage produit du 20/07/2026, reversé dans `stories/`) :

- `rang_scratch` : le classement **global**, toutes catégories confondues ;
- `rang_categorie` : le classement **au sein de la catégorie** de l'archer, **repartant de 1** par
  catégorie (ex æquo partagés avec sauts — même règle que le scratch, §8.1 ; ce n'est **pas**
  un rang « dense » sans trou : deux ex æquo en 2ᵉ place sont suivis d'un 4ᵉ, pas d'un 3ᵉ).

Les deux se calculent avec le **même** ordre ; ils ne diffèrent que par la numérotation (le scratch
saute les places prises par les autres catégories, la catégorie repart de 1). Le décompte de 10 et
de 9 est **restitué** dans la ligne : le CA veut le départage « traçable », c.-à-d. vérifiable à
l'œil sans rejouer le calcul.

Ce n'est **pas** encore la politique `tiebreak` injectable d'ADR-0004 : il n'existe qu'une règle (la
FFTA), et son moteur relève d'EPIC-05 (l'ADR se scope lui-même là-bas). On implémente donc la règle
comme une clé de tri **isolée et nommée** (`_cle_tri`, `_CLE_DEPARTAGE`) — la couture d'une future
injection — sans la plomberie de config prématurée (règle 12, « remède structurel sur preuve »).

Fonction pure sur des agrégats : testable sans base ni serveur.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum
from functools import cmp_to_key

from domain.archer import Archer, ArcherId
from domain.barrage import EgaliteADepartager, VerdictBarrage, egalites_a_departager
from domain.blason import ZoneScore
from domain.categorie import Categorie, CategorieId
from domain.club import ClubId
from domain.forfait import Forfait, NatureForfait
from domain.participant import GenreParticipant, Participant
from domain.politiques import DecompteDepartage, Tiebreak, TiebreakFftaDefaut
from domain.serie import Serie


class StatutClassement(str, Enum):
    """Le statut d'un archer **dans** le classement de qualification (E04US015, ADR-0050).

    `EN_LICE` (défaut) : l'archer concourt normalement, rangé sur son score. `ABANDON` : il a
    **abandonné** — relégué **en fin** de classement (derrière tous ceux qui ont fini), mais rangé
    et son score affiché (Q2 du cadrage). `DISQUALIFIE` : **sorti** du classement — pas de rang
    (`rang_* is None`), ses flèches restant conservées (Q3). Un archer sans forfait est `EN_LICE`.
    """

    EN_LICE = "en_lice"
    ABANDON = "abandon"
    DISQUALIFIE = "disqualifie"


# Ordre de relégation : un abandon passe **après** tout archer en lice, le DSQ après tout le monde.
# Le DSQ n'est **pas rangé** (il n'entre jamais dans `_ranger`) ; son ordinal ne sert qu'à donner à
# `_cle_tri` une clé totale pour l'ordre d'**affichage** des disqualifiés (en dernier).
_RANG_STATUT: dict[StatutClassement, int] = {
    StatutClassement.EN_LICE: 0,
    StatutClassement.ABANDON: 1,
    StatutClassement.DISQUALIFIE: 2,
}


def _statut_pour(nature: NatureForfait | None) -> StatutClassement:
    """Traduit la nature d'un forfait (ou son absence) en statut de classement."""
    if nature is None:
        return StatutClassement.EN_LICE
    if nature is NatureForfait.ABANDON:
        return StatutClassement.ABANDON
    return StatutClassement.DISQUALIFIE


@dataclass(frozen=True)
class LigneClassement:
    """Une ligne de classement : les deux rangs de l'archer, son identité et son décompte.

    Porte `prenom` et `club_id` depuis E02US002, pour deux raisons distinctes : le classement est
    la surface où un archer **inscrit** apparaît, donc (a) c'est ici que se **signale** un club
    encore inconnu (`club_id is None`), l'anomalie que le CA impose de rendre visible (ADR-0014) ;
    et (b) deux homonymes confirmés (un père et son fils) seraient indiscernables sur le seul
    patronyme. `club_id` et non le nom du club : le classement ne charge pas le référentiel —
    signaler une absence ne demande pas de résoudre les présences.

    `nb_dix`/`nb_neuf` rendent le départage **traçable** (CA) : on voit *pourquoi* deux archers à
    total égal sont ordonnés ainsi, sans rejouer le calcul.
    """

    rang_scratch: int | None
    rang_categorie: int | None
    archer_id: ArcherId
    nom: str
    prenom: str
    categorie_id: CategorieId
    categorie_libelle: str
    cible: int | None
    club_id: ClubId | None
    total: int
    nb_dix: int
    nb_neuf: int
    statut: StatutClassement = StatutClassement.EN_LICE


@dataclass(frozen=True)
class Classement:
    """Classement d'un tournoi, ordonné par rang **scratch** (du meilleur au moins bon).

    `egalites_a_departager` (E06US003) liste les ex æquo que la politique `tiebreak` réclame de
    trancher **au tir**, sur les rangs **scratch** — c'est là que se jouent les places décisives
    (l'entrée au tableau se fait sur l'ordre général, pas sur le rang de catégorie). Vide par
    défaut : sans seuil réglé, le classement se comporte exactement comme E06US001 le livrait.
    """

    lignes: tuple[LigneClassement, ...]
    egalites_a_departager: tuple[EgaliteADepartager, ...] = ()


@dataclass(frozen=True)
class _Decompte:
    """Ce dont le classement a besoin pour un archer : total et décomptes de départage."""

    total: int
    nb_dix: int
    nb_neuf: int


def _decompte(serie: Serie | None) -> _Decompte:
    """Réduit la série d'un archer à son total et ses décomptes de 10/9 (volées validées).

    `None` (archer inscrit sans série encore ouverte) → tout à zéro : il figure au classement avec
    un total nul, comme l'exige le CA « un archer sans flèche apparaît quand même ».
    """
    if serie is None:
        return _Decompte(total=0, nb_dix=0, nb_neuf=0)
    return _Decompte(
        total=serie.cumul,
        nb_dix=serie.compter(ZoneScore.DIX),
        nb_neuf=serie.compter(ZoneScore.NEUF),
    )


@dataclass(frozen=True)
class _Entree:
    """Une entrée à classer : l'archer, son décompte, son statut et son éventuel verdict de barrage.

    `position_barrage` est le rang qu'un **barrage déjà tiré** a attribué à cet archer (E06US003),
    `0` quand aucun ne le concerne. Il n'intervient qu'**après** épuisement de la politique de
    départage — c'est-à-dire exactement là où le rang serait resté partagé.
    """

    archer: Archer
    archer_id: ArcherId
    decompte: _Decompte
    departage: DecompteDepartage
    statut: StatutClassement
    position_barrage: int = 0


def _comparer_classant(a: _Entree, b: _Entree, tiebreak: Tiebreak) -> int:
    """Les critères qui **rangent** — deux entrées nulles ici sont **ex æquo**.

    Ordre séquentiel : le **statut** d'abord (`_RANG_STATUT` : en lice = 0, abandon = 1), donc un
    abandon passe après tous les en-lice quel que soit son score (« relégation en fin », Q2) ; puis
    le **total** ; puis la **politique** `tiebreak` — c'est la couture qu'E06US001 avait laissée en
    attente et que DETTE-028 réclamait, `classement.py` ne réimplémentant plus §8.1 à la main ;
    puis le **verdict de barrage**, qui ne joue que sur ce que la politique a laissé à égalité.

    ⚠️ **Un comparateur, pas une clé de tri.** Une politique injectable rend un ordre relatif
    (`departager`), pas une valeur ordonnable : il n'existe aucune clé qui exprimerait les cinq
    critères de poule et les deux de la qualification sans les figer ici — c'est précisément ce que
    l'injection sert à éviter. D'où `cmp_to_key` au moment du tri.
    """
    if a.statut is not b.statut:
        return _RANG_STATUT[a.statut] - _RANG_STATUT[b.statut]
    if a.decompte.total != b.decompte.total:
        return b.decompte.total - a.decompte.total
    ecart = tiebreak.departager(a.departage, b.departage)
    if ecart:
        return ecart
    return a.position_barrage - b.position_barrage


def _comparer(a: _Entree, b: _Entree, tiebreak: Tiebreak) -> int:
    """Le comparateur **total** : les critères classants, puis un ordre d'affichage stable.

    À égalité **parfaite**, `(nom, prenom, archer_id)` fixe l'ordre d'écran (mêmes homonymes, même
    affichage d'une lecture à l'autre). Ce suffixe **n'entre pas** dans le partage de rang : deux
    archers qu'il sépare restent ex æquo.
    """
    ecart = _comparer_classant(a, b, tiebreak)
    if ecart:
        return ecart
    cle_a = (a.archer.nom, a.archer.prenom, a.archer_id)
    cle_b = (b.archer.nom, b.archer.prenom, b.archer_id)
    if cle_a < cle_b:
        return -1
    return 1 if cle_a > cle_b else 0


def _ranger(entrees_ordonnees: Sequence[_Entree], tiebreak: Tiebreak) -> dict[ArcherId, int]:
    """Attribue un rang à des entrées **déjà triées**, ex æquo partagés (ex. 1-2-2-4).

    Deux entrées que `_comparer_classant` ne sépare pas gardent le même rang ; on repart du rang
    « index + 1 » dès qu'il les sépare — d'où les sauts après un groupe d'ex æquo. Un abandon, trié
    après les en-lice, reçoit ainsi un rang qui **continue** leur numérotation (relégation).
    """
    # DETTE-029 (docs/dette.md) : 3ᵉ écriture de « rang partagé à clé égale, avec sauts » dans le
    # domaine (`classement._ranger`, `poule.classement_de_poule`, `suisse.classement_suisse`), et
    # les trois divergent déjà. Remède proposé (fonction pure `attribuer_rangs`) en US dédiée.
    rangs: dict[ArcherId, int] = {}
    rang = 0
    tete: _Entree | None = None
    for index, entree in enumerate(entrees_ordonnees):
        if tete is None or _comparer_classant(tete, entree, tiebreak) != 0:
            rang = index + 1
            tete = entree
        rangs[entree.archer_id] = rang
    return rangs


def _positions_de_barrage(verdicts: Iterable[VerdictBarrage]) -> dict[ArcherId, int]:
    """Les rangs qu'ont attribués les barrages **déjà tirés**, par archer.

    Un verdict **non résolu** (`ordre` vide) n'apporte rien : le rang reste partagé, et c'est le
    contrat de `ResultatBarrage` — pas de classement à moitié vrai. Seuls les participants
    **individuels** sont retenus : un classement de qualification range des archers (une épreuve par
    équipes classe des équipes, ailleurs).
    """
    positions: dict[ArcherId, int] = {}
    for verdict in verdicts:
        for participant, rang in verdict.rangs().items():
            if participant.genre is GenreParticipant.INDIVIDUEL:
                positions[participant.ref_id] = rang
    return positions


def calculer_classement(
    archers: Iterable[Archer],
    series: Iterable[Serie],
    categories: Iterable[Categorie],
    forfaits: Iterable[Forfait] = (),
    tiebreak: Tiebreak | None = None,
    verdicts: Iterable[VerdictBarrage] = (),
) -> Classement:
    """Construit le classement des `archers` à partir de leurs `series`, avec départage FFTA.

    - `series` dont l'`archer_id` n'appartient pas au lot d'archers sont ignorées ;
    - `categories` sert à libeller la catégorie de chaque ligne (jointure par `categorie_id`) ;
    - `forfaits` (E04US015, ADR-0050) : les forfaits **de cette phase de qualification** (le service
      les filtre par phase — un forfait en duels ne relègue pas le rang de qualif). Un archer
      **abandon** est **relégué en fin** de son classement (scratch et catégorie), rangé mais après
      tous les en-lice ; un archer **disqualifié** est **sorti** du classement (`rang_* is None`),
      listé en dernier avec son statut et son score (ses flèches restent — Q2/Q3 du cadrage).

    - `tiebreak` (E06US003) : la politique de **départage** de la phase (ADR-0004). `None` retombe
      sur `TiebreakFftaDefaut` — §8.1, exactement la règle qu'E06US001 écrivait à la main. C'est
      donc un changement de **plomberie**, pas de règle : la couture réclamée par DETTE-028 ;
    - `verdicts` (E06US003) : les **barrages déjà tirés**. Ils n'interviennent que là où le
      départage a laissé un ex æquo, et y rendent les rangs **consécutifs** — sans décaler les
      archers suivants, un barrage éclatant un rang partagé plutôt qu'insérant quelqu'un.

    Renvoie les lignes ordonnées par **rang scratch** (en lice, puis abandons relégués, puis DSQ).
    Chaque ligne porte aussi son rang **dans sa catégorie** (repartant de 1 par catégorie, ex æquo
    partagés avec sauts), calculé sur le même ordre restreint aux archers de la catégorie — un
    barrage tranche donc les **deux** rangs, l'ordre étant commun.
    """
    departage = tiebreak if tiebreak is not None else TiebreakFftaDefaut()
    serie_par_archer = {s.archer_id: s for s in series}
    libelle_par_categorie = {c.id: c.libelle for c in categories if c.id is not None}
    nature_par_archer = {f.archer_id: f.nature for f in forfaits}
    positions = _positions_de_barrage(verdicts)
    entrees: list[_Entree] = []
    for archer in archers:
        assert archer.id is not None, "Le classement se calcule sur des archers persistés."
        decompte = _decompte(serie_par_archer.get(archer.id))
        entrees.append(
            _Entree(
                archer=archer,
                archer_id=archer.id,
                decompte=decompte,
                departage=DecompteDepartage(nb_dix=decompte.nb_dix, nb_neuf=decompte.nb_neuf),
                statut=_statut_pour(nature_par_archer.get(archer.id)),
                position_barrage=positions.get(archer.id, 0),
            )
        )

    # Les **classables** (en lice + abandon) reçoivent un rang ; les **disqualifiés** en sont sortis
    # (rang `None`) et affichés en dernier, triés pour un ordre stable (même statut pour tous).
    # L'abandon, trié après les en-lice, est relégué avec un rang qui les prolonge.
    classables = [e for e in entrees if e.statut is not StatutClassement.DISQUALIFIE]
    disqualifies = [e for e in entrees if e.statut is StatutClassement.DISQUALIFIE]

    def comparer(a: _Entree, b: _Entree) -> int:
        """Ferme le comparateur sur la politique — `cmp_to_key` est générique, il lui faut des
        paramètres annotés pour inférer le type comparé."""
        return _comparer(a, b, departage)

    cle = cmp_to_key(comparer)
    ordre_classables = sorted(classables, key=cle)
    rangs_scratch = _ranger(ordre_classables, departage)

    # Rangs par catégorie : même comparateur, appliqué au sous-ensemble de chaque catégorie.
    # L'ordre relatif y est **identique** à l'ordre scratch (mêmes archers, même clé) — seule la
    # numérotation diffère (repart de 1 par catégorie). On regroupe depuis l'ordre scratch trié.
    rangs_categorie: dict[ArcherId, int] = {}
    par_categorie: dict[CategorieId, list[_Entree]] = {}
    for entree in ordre_classables:
        par_categorie.setdefault(entree.archer.categorie_id, []).append(entree)
    for groupe in par_categorie.values():
        rangs_categorie.update(_ranger(groupe, departage))

    ordre_final = ordre_classables + sorted(disqualifies, key=cle)

    # `categorie_libelle` retombe sur "" si la catégorie de l'archer manque au lot passé — ne
    # devrait pas arriver (FK obligatoire depuis E02US002). Contrairement au `club_id` inconnu
    # qu'on **signale** (ADR-0014), un libellé vide ne trompe personne et ne mérite pas de rendre
    # l'anomalie visible ici.
    lignes: list[LigneClassement] = []
    for entree in ordre_final:
        archer = entree.archer
        assert archer.id is not None
        lignes.append(
            LigneClassement(
                rang_scratch=rangs_scratch.get(archer.id),
                rang_categorie=rangs_categorie.get(archer.id),
                archer_id=archer.id,
                nom=archer.nom,
                prenom=archer.prenom,
                categorie_id=archer.categorie_id,
                categorie_libelle=libelle_par_categorie.get(archer.categorie_id, ""),
                cible=archer.cible,
                club_id=archer.club_id,
                total=entree.decompte.total,
                nb_dix=entree.decompte.nb_dix,
                nb_neuf=entree.decompte.nb_neuf,
                statut=entree.statut,
            )
        )
    # Les égalités se lisent sur les rangs **définitifs** : un barrage déjà tiré ne doit plus être
    # réclamé, sans quoi l'écran redemanderait éternellement ce qui vient d'être fait.
    egalites = egalites_a_departager(
        [
            (rangs_scratch[entree.archer_id], Participant.individuel(entree.archer_id))
            for entree in ordre_classables
        ],
        departage,
    )
    return Classement(lignes=tuple(lignes), egalites_a_departager=egalites)
