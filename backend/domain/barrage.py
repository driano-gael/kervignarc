"""Moteur du **tir de barrage** (shoot-off) — art. B.6.5.2, [référentiel §8.2] (E05US015).

Contrairement aux autres formats de cette US, la règle du barrage **n'a pas eu à être demandée** :
elle est entièrement écrite au règlement fédéral.

> - **Individuel** : **1 flèche**, le plus haut score gagne. Si l'égalité subsiste, on **répète au
>   plus près du centre** jusqu'à résolution. Tiré sur la cible centrale du triple vertical.
> - **Équipe** : une volée de **3 flèches** (1 par archer), plus haut total ; répété si nécessaire.
> - Le barrage **ne prend pas en compte** le nombre de 10/9 (B.6.5.2).
> - Un archer **absent** au barrage annoncé est déclaré **perdant** (B.6.5.2.4).

**Deux règles qui surprennent, et que le CA demandait de ne pas rater.** Le barrage est le **seul**
endroit du produit où le nombre de 10/9 ne départage pas — partout ailleurs (§8.1, poules) c'est un
critère. Et l'absence n'y est pas un forfait à instruire : elle **tranche**, immédiatement.

**Un moteur, trois usages.** Ce module sert (1) la phase de **barrage autonome** — départager des ex
æquo *avant* de monter un tableau, le CA de cette US —, (2) l'égalité au plus faible d'un **Big
Shoot Off**, (3) l'ex æquo d'un **classement de poule** (« barrage si nécessaire »). Les trois
appellent `resoudre_barrage` et appliquent son verdict ; aucun ne le réimplémente. C'est ce qui
justifiait de le sortir en module plutôt que de l'enfouir dans le premier des trois.

⚠️ **Un barrage n'est pas un duel.** `domain/duel.py` traite le barrage *interne* à un duel nul
(égalité de sets), qui oppose exactement deux camps sur un format connu. Ici on départage **N**
participants d'un coup — trois archers ex æquo au rang 8 tirent ensemble, ils ne s'affrontent pas
deux à deux. Domaine **pur** (règle 1).

[référentiel §8.2]: ../../docs/referentiel-ffta.md
"""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum

from domain.erreurs import ConfigurationBarrageInvalide
from domain.participant import Participant
from domain.phase import PhaseId
from domain.politiques import Tiebreak
from domain.tournoi import TournoiId

BarrageId = int

FLECHES_INDIVIDUEL = 1
"""Art. B.6.5.2 : le barrage individuel se tire à **une** flèche."""

FLECHES_EQUIPE = 3
"""Art. B.6.5.2.2 : une volée de **3** flèches, une par archer de l'équipe."""


@dataclass(frozen=True)
class ConfigurationBarrage:
    """Le format d'un barrage — individuel (1 flèche) ou par équipe (3).

    Le nombre de flèches **n'est pas un réglage libre** : le règlement le fixe, et un barrage à 2
    flèches ne serait pas un barrage mal réglé mais une autre épreuve. On le vérifie donc au lieu
    de l'accepter, contrairement au barème de poule ou au BSO où le club choisit.

    ⚠️ **Ce value object n'a aucun consommateur** : il décrit le **format de saisie** (combien de
    flèches on fait tirer), quand `resoudre_barrage` ne fait que **départager** des tirs déjà clos —
    d'où le retrait de son paramètre. Il attend donc la surface de saisie du barrage, en même temps
    que les autres moteurs de cette US ([DETTE-028](../../docs/dette.md)).
    """

    fleches: int = FLECHES_INDIVIDUEL
    equipe: bool = False

    def __post_init__(self) -> None:
        attendu = FLECHES_EQUIPE if self.equipe else FLECHES_INDIVIDUEL
        if self.fleches != attendu:
            raise ConfigurationBarrageInvalide(
                f"Un barrage {'par équipe' if self.equipe else 'individuel'} se tire à {attendu} "
                f"flèche(s) (art. B.6.5.2) ; {self.fleches} n'est pas un réglage mais une autre "
                "épreuve."
            )

    @staticmethod
    def individuel() -> ConfigurationBarrage:
        """Le barrage individuel du règlement : 1 flèche, plus haut score."""
        return ConfigurationBarrage(fleches=FLECHES_INDIVIDUEL, equipe=False)

    @staticmethod
    def par_equipe() -> ConfigurationBarrage:
        """Le barrage par équipe : une volée de 3 flèches, 1 par archer."""
        return ConfigurationBarrage(fleches=FLECHES_EQUIPE, equipe=True)


@dataclass(frozen=True)
class TirBarrage:
    """Ce qu'un participant a réalisé au barrage.

    `score` à `None` signifie **absent au barrage annoncé** — pas « pas encore saisi ». La nuance
    est décisive : l'absence est une issue réglementaire (B.6.5.2.4, l'archer est déclaré perdant),
    tandis qu'une saisie en attente ne doit surtout pas faire perdre qui que ce soit. Le service
    n'appelle donc ce moteur qu'une fois les tirs **clos**.

    `distance_au_centre` est en dixièmes de millimètre, mesurée du centre à l'impact ; `None` quand
    la mesure n'a pas été faite. Elle ne sert **que** si les scores restent égaux — c'est le
    « répète au plus près du centre » du règlement, second critère **séquentiel**, pas fusionné avec
    le premier.
    """

    participant: Participant
    score: int | None
    distance_au_centre: int | None = None

    def __post_init__(self) -> None:
        """Un score et une distance sont des grandeurs **positives**.

        ⚠️ Une distance négative ne serait pas seulement absurde : elle **gagnerait**, le départage
        retenant la plus petite. On ferme le domaine de définition plutôt que de durcir un seul cas
        (le `None` traité comme un zéro, corrigé plus haut) et d'en laisser un autre ouvert.
        """
        if self.score is not None and self.score < 0:
            raise ConfigurationBarrageInvalide(
                f"Un score de barrage est positif ou nul (reçu {self.score})."
            )
        if self.distance_au_centre is not None and self.distance_au_centre < 0:
            raise ConfigurationBarrageInvalide(
                f"Une distance au centre est positive ou nulle (reçu {self.distance_au_centre})."
            )


@dataclass(frozen=True)
class ResultatBarrage:
    """L'issue d'un barrage : l'ordre obtenu, ou les ex æquo qu'il faut faire retirer.

    Les deux champs sont **exclusifs** : soit le barrage a départagé tout le monde (`ordre` plein,
    `groupes_a_rejouer` vide), soit il ne l'a pas fait (`ordre` vide, les groupes nommant ceux qui
    restent à égalité). On ne rend **pas** un ordre partiel : un classement à moitié vrai est plus
    dangereux qu'un refus, parce qu'il s'affiche sans avertir.

    ⚠️ **Les ex æquo sont rendus par GROUPES, et c'est ce qui rend le résultat exploitable.** Un
    barrage à quatre tireurs dont deux à 10 et deux à 8 laisse **deux** égalités distinctes, pas
    une seule. Les aplatir en une liste ferait retirer les quatre ensemble — et un tireur à 8
    pourrait alors passer devant un tireur à 10 que le premier tir avait déjà départagé. Chaque
    groupe se rejoue **séparément** ; c'est le sens de « on répète » au règlement.
    """

    ordre: tuple[Participant, ...] = ()
    groupes_a_rejouer: tuple[tuple[Participant, ...], ...] = ()

    @property
    def a_rejouer(self) -> tuple[Participant, ...]:
        """Tous les ex æquo, groupes confondus — commodité d'affichage **seulement**.

        Ne s'en servir pour organiser le retir serait exactement l'erreur que les groupes évitent :
        cette liste ne dit pas qui doit retirer *contre qui*.
        """
        return tuple(participant for groupe in self.groupes_a_rejouer for participant in groupe)

    @property
    def est_resolu(self) -> bool:
        return not self.groupes_a_rejouer

    @property
    def vainqueur(self) -> Participant | None:
        """Le mieux placé, ou `None` si le barrage doit être retiré."""
        return self.ordre[0] if self.ordre else None

    @property
    def perdant(self) -> Participant | None:
        """Le moins bien placé — c'est **lui** qu'attendent le Big Shoot Off (l'éliminé de la
        manche) et le barrage de dernière place. Un barrage ne sert pas qu'à désigner un vainqueur.
        """
        return self.ordre[-1] if self.ordre else None


def resoudre_barrage(tirs: Sequence[TirBarrage]) -> ResultatBarrage:
    """Départage les participants d'un barrage (art. B.6.5.2).

    Ordre d'application, **séquentiel** :

    1. les **absents** (`score is None`) sont relégués derrière tous les présents, quelle que soit
       la suite — c'est B.6.5.2.4, et cela s'applique avant toute comparaison de score ;
    2. le **plus haut score** l'emporte ;
    3. à score égal, la **distance au centre** (la plus petite gagne) ;
    4. si l'égalité subsiste — distances égales, **ou l'une d'elles non mesurée** —, le barrage
       **n'est pas résolu** : le groupe part dans `groupes_a_rejouer`, et le règlement dit de
       répéter.

    ⚠️ **Une distance non mesurée n'est PAS une distance nulle.** C'est le point 4, et c'est le
    défaut qu'un premier jet de cette US a laissé passer : `None` était replié sur `0`, c'est-à-dire
    sur le **centre parfait**, donc le tir non mesuré gagnait contre un tir mesuré. Le cas est le
    plus probable du jour J — le juge mesure la flèche litigieuse, rarement les deux —, et le
    verdict rendu était faux **et silencieux**. Une mesure absente est une **inconnue** : on ne
    départage pas sur une inconnue, on fait retirer.

    ⚠️ **Le nombre de 10/9 n'intervient jamais** (B.6.5.2). C'est le seul endroit du produit où ce
    critère est écarté, et l'y réintroduire « pour éviter un retir » serait une faute réglementaire
    invisible : le classement produit aurait l'air correct.

    ⚠️ **Plusieurs absents restent ex æquo entre eux.** Deux absents sont tous deux « déclarés
    perdants » — le règlement ne les ordonne pas l'un par rapport à l'autre, et rien ne permet de le
    faire : ils n'ont pas tiré. Ils forment donc un groupe à rejouer plutôt qu'un ordre inventé,
    quitte à ce que ce soit au service d'en tirer les conséquences (généralement : rang partagé).
    """
    return _issue(partitionner_barrage(tirs))


def partitionner_barrage(tirs: Sequence[TirBarrage]) -> tuple[tuple[Participant, ...], ...]:
    """La même règle que `resoudre_barrage`, rendue **structurée** : la partition **ordonnée**.

    Chaque groupe rassemble des participants que ce tir n'a pas départagés ; les groupes sont rendus
    du mieux placé au moins bien, un **singleton** valant « départagé ». `((A, C), (B, D))` se lit
    donc : A et C devant B et D, mais indépartageables entre eux.

    ⚠️ **C'est l'information que `resoudre_barrage` doit jeter, et pourquoi ce découpage existe.**
    Son contrat interdit l'ordre partiel (« un classement à moitié vrai est plus dangereux qu'un
    refus »), donc il rend `groupes_a_rejouer` **sans** l'ordre relatif des groupes. Ce choix reste
    juste pour un appelant qui publie un résultat — mais la **répétition en manches**, elle, a
    besoin de savoir que le groupe à 10 précède le groupe à 8, sans quoi le retir pourrait faire
    passer un tireur à 8 devant un tireur à 10 déjà départagé. On expose donc la partition à côté,
    plutôt que d'affaiblir le contrat de `resoudre_barrage` pour un seul appelant.
    """
    if len(tirs) < 2:
        raise ConfigurationBarrageInvalide(
            "Un barrage départage au moins deux participants ; à un seul il n'y a rien "
            "à départager."
        )
    participants = [tir.participant for tir in tirs]
    if len(set(participants)) != len(participants):
        raise ConfigurationBarrageInvalide("Un même participant figure deux fois dans ce barrage.")

    partition: list[tuple[Participant, ...]] = []
    for groupe in _groupes_de_score(tirs):
        if groupe[0].score is None:
            # Les absents : indépartageables entre eux par construction, ils n'ont pas tiré.
            partition.append(tuple(tir.participant for tir in groupe))
            continue
        for sous_groupe in _departager_a_la_distance(groupe):
            partition.append(tuple(tir.participant for tir in sous_groupe))
    return tuple(partition)


def _issue(partition: Sequence[tuple[Participant, ...]]) -> ResultatBarrage:
    """Traduit une partition en `ResultatBarrage` — tout ou rien, conformément à son contrat."""
    groupes = tuple(groupe for groupe in partition if len(groupe) > 1)
    if groupes:
        return ResultatBarrage(groupes_a_rejouer=groupes)
    return ResultatBarrage(ordre=tuple(groupe[0] for groupe in partition))


def resoudre_barrage_en_manches(manches: Sequence[Sequence[TirBarrage]]) -> ResultatBarrage:
    """Applique les manches successives d'un barrage — le « on répète » du règlement (§8.2).

    `manches[0]` est le barrage annoncé, chaque manche suivante le **retir** des ex æquo qu'il n'a
    pas départagés. Le verdict se **recalcule** intégralement depuis les tirs : rien n'est stocké
    d'un ordre saisi à la main, donc corriger une flèche mal saisie corrige le classement (CA
    « verdict rejouable »).

    Trois règles de saisie, refusées plutôt qu'absorbées en silence :

    1. **un tireur déjà départagé ne retire pas** — le laisser passer réordonnerait des places que
       la manche précédente avait tranchées, et c'est exactement l'accident que la partition
       ordonnée existe pour empêcher ;
    2. **un groupe se retire en entier ou pas du tout** — deux ex æquo dont un seul a tiré ne se
       départagent sur rien ; l'accepter ferait gagner celui qui a tiré, faute d'adversaire ;
    3. un groupe **absent** de la manche n'est pas résolu pour autant : il reste à égalité. C'est le
       cas normal du jour J, où le juge fait retirer une égalité puis l'autre, pas les deux
       ensemble.
    """
    if not manches:
        raise ConfigurationBarrageInvalide(
            "Un barrage compte au moins une manche : celle qui a été annoncée."
        )
    partition = partitionner_barrage(manches[0])
    for numero, manche in enumerate(manches[1:], start=2):
        partition = _rejouer(partition, manche, numero)
    return _issue(partition)


def _rejouer(
    partition: Sequence[tuple[Participant, ...]], manche: Sequence[TirBarrage], numero: int
) -> tuple[tuple[Participant, ...], ...]:
    """Applique une manche de retir à une partition, en n'y touchant que les groupes concernés."""
    tirs: dict[Participant, TirBarrage] = {}
    for tir in manche:
        if tir.participant in tirs:
            raise ConfigurationBarrageInvalide(
                f"Un même participant figure deux fois dans la manche {numero}."
            )
        tirs[tir.participant] = tir

    a_egalite = {participant for groupe in partition if len(groupe) > 1 for participant in groupe}
    intrus = [participant for participant in tirs if participant not in a_egalite]
    if intrus:
        raise ConfigurationBarrageInvalide(
            f"{len(intrus)} tireur(s) de la manche {numero} étaient déjà départagés : un retir ne "
            "rouvre pas des places tranchées."
        )

    nouvelle: list[tuple[Participant, ...]] = []
    for groupe in partition:
        presents = [participant for participant in groupe if participant in tirs]
        if len(groupe) == 1 or not presents:
            # Départagé, ou groupe que cette manche n'a pas fait retirer : inchangé.
            nouvelle.append(groupe)
            continue
        if len(presents) != len(groupe):
            raise ConfigurationBarrageInvalide(
                f"Manche {numero} : {len(presents)} tireur(s) sur {len(groupe)} d'une même "
                "égalité ont retiré. Un groupe se retire en entier ou pas du tout."
            )
        nouvelle.extend(partitionner_barrage([tirs[participant] for participant in groupe]))
    return tuple(nouvelle)


def _groupes_de_score(tirs: Sequence[TirBarrage]) -> list[list[TirBarrage]]:
    """Regroupe les tirs par score, du meilleur au moins bon, les absents relégués en dernier."""
    tries = sorted(tirs, key=lambda tir: (1, 0) if tir.score is None else (0, -tir.score))
    groupes: list[list[TirBarrage]] = []
    for tir in tries:
        meme_score = (
            groupes
            and (groupes[-1][0].score is None) == (tir.score is None)
            and groupes[-1][0].score == tir.score
        )
        if meme_score:
            groupes[-1].append(tir)
        else:
            groupes.append([tir])
    return groupes


def _departager_a_la_distance(groupe: Sequence[TirBarrage]) -> list[list[TirBarrage]]:
    """Second critère (§8.2) sur un groupe **de même score** : la distance au centre.

    Rend des sous-groupes, du plus près du centre au plus loin ; un sous-groupe de plus d'un tir est
    indépartageable et devra être rejoué. Si **une seule** distance du groupe manque, tout le groupe
    est indépartageable : on ne compare pas une mesure à une absence de mesure.
    """
    if len(groupe) == 1:
        return [list(groupe)]
    if any(tir.distance_au_centre is None for tir in groupe):
        return [list(groupe)]
    tries = sorted(groupe, key=lambda tir: tir.distance_au_centre or 0)
    sous_groupes: list[list[TirBarrage]] = []
    for tir in tries:
        if sous_groupes and sous_groupes[-1][0].distance_au_centre == tir.distance_au_centre:
            sous_groupes[-1].append(tir)
        else:
            sous_groupes.append([tir])
    return sous_groupes


# --- déclenchement : quelles égalités méritent un barrage (E06US003) -----------------------------


@dataclass(frozen=True)
class EgaliteADepartager:
    """Un ex æquo que la politique `tiebreak` désigne comme **à trancher au tir**.

    `rang` est le rang **partagé** par le groupe — celui que le barrage va éclater en rangs
    consécutifs. Une égalité signalée n'est pas un barrage déjà organisé : le moteur **constate**,
    l'organisateur fait tirer (même partage des rôles que `TiebreakPoules`, dont le `0` constate
    l'ex æquo sans faire tirer personne).
    """

    rang: int
    participants: tuple[Participant, ...]


def egalites_a_departager(
    rangs: Sequence[tuple[int, Participant]], tiebreak: Tiebreak
) -> tuple[EgaliteADepartager, ...]:
    """Les égalités de `rangs` que `tiebreak` veut voir départagées au tir (E06US003).

    `rangs` associe à chaque participant son rang, **ex æquo déjà partagés** — c'est-à-dire la
    sortie d'un classement, quel qu'il soit : qualification (§8.1), poule (§10.1) ou tout autre.
    C'est ce qui permet aux trois consommateurs du CA de partager ce déclenchement sans qu'aucun ne
    connaisse la structure des autres.

    Un rang **non partagé** n'est jamais une égalité, et un groupe que la politique ne réclame pas
    reste **ex æquo** — le défaut d'E06US001, que le seuil ne fait qu'ouvrir là où on le règle.
    Rendu trié par rang : la sortie est une surface d'affichage, elle doit être déterministe.
    """
    par_rang: dict[int, list[Participant]] = {}
    for rang, participant in rangs:
        par_rang.setdefault(rang, []).append(participant)
    return tuple(
        EgaliteADepartager(rang=rang, participants=tuple(participants))
        for rang, participants in sorted(par_rang.items())
        if len(participants) > 1 and tiebreak.barrage_requis(rang)
    )


@dataclass(frozen=True)
class VerdictBarrage:
    """L'ordre qu'un barrage a produit sur un groupe d'ex æquo, prêt à être appliqué au classement.

    `rang` est le rang partagé d'origine, `ordre` le classement obtenu au tir. Un barrage **non
    résolu** rend un `ordre` vide : il ne range personne et le rang **reste partagé**. C'est la
    même exigence que `ResultatBarrage` — ne jamais publier un ordre à moitié vrai, parce qu'il
    s'affiche sans avertir.
    """

    rang: int
    ordre: tuple[Participant, ...] = ()

    def rangs(self) -> dict[Participant, int]:
        """Les rangs **consécutifs** que ce verdict attribue, à partir du rang partagé.

        Trois ex æquo au rang 8 départagés donnent 8, 9 et 10 — le barrage tranche donc aussi des
        places situées **au-delà** du seuil qui l'a déclenché, ce qui est voulu (ADR-0066).
        """
        return {participant: self.rang + ecart for ecart, participant in enumerate(self.ordre)}


# --- l'agrégat persisté : un barrage annoncé, ses manches et son verdict (E06US003) --------------


class PorteeBarrage(str, Enum):
    """Le classement qu'un barrage vient trancher — les **trois usages** du moteur (§8.2).

    Le champ existe dès maintenant, bien qu'une seule portée soit câblée de bout en bout : c'est ce
    qui évite une migration le jour où les moteurs de poule et de Big Shoot Off recevront leurs
    consommateurs (DETTE-028). Un discriminant ajouté d'emblée ne coûte rien ; l'ajouter après coup
    oblige à réécrire des lignes existantes.
    """

    QUALIFICATION = "qualification"
    """Ex æquo du classement de qualification, §8.1 épuisé — la seule portée câblée à ce jour."""

    POULE = "poule"
    """Ex æquo d'un classement de poule (« barrage si nécessaire », §10.1)."""

    BIG_SHOOT_OFF = "big_shoot_off"
    """Égalité **au plus faible** d'une manche de Big Shoot Off — celle qui suspend la manche."""


@dataclass(frozen=True)
class BarrageDePlaces:
    """Un barrage **annoncé** : qui il départage, ce qui a été tiré, et ce qu'il en résulte.

    Agrégat de persistance du barrage de places (E06US003). `participants` est figé à l'annonce —
    et non recalculé depuis le classement à chaque lecture : les scores continuent d'évoluer (une
    volée validée en retard, un forfait), et un barrage dont la liste de tireurs change sous les
    pieds du juge ne serait pas un barrage. `manches` porte les tirs, manche par manche ; le verdict
    s'en **recalcule** intégralement : corriger une flèche mal saisie corrige le classement.

    `rang_dispute` est le rang partagé que ce barrage vient éclater. Il est `None` pour un Big Shoot
    Off, dont l'égalité au plus faible n'a pas de rang à disputer — elle désigne un **sortant**.

    ⚠️ **Un tir absent de `manches` n'est pas un tireur absent.** L'absence réglementaire
    (B.6.5.2.4, l'archer est déclaré perdant) se saisit comme un `TirBarrage` de `score` à `None` ;
    « pas encore saisi », c'est l'absence de la **ligne** elle-même. Confondre les deux ferait
    perdre quelqu'un qui n'a pas encore tiré, ce dont `TirBarrage` avertit déjà.
    """

    tournoi_id: TournoiId
    portee: PorteeBarrage
    participants: tuple[Participant, ...]
    cree_le: datetime.datetime
    manches: tuple[tuple[TirBarrage, ...], ...] = ()
    rang_dispute: int | None = None
    phase_id: PhaseId | None = None
    reference: str | None = None
    clos: bool = False
    id: BarrageId | None = field(default=None)

    def __post_init__(self) -> None:
        if len(self.participants) < 2:
            raise ConfigurationBarrageInvalide(
                "Un barrage départage au moins deux participants ; à un seul il n'y a rien "
                "à départager."
            )
        if len(set(self.participants)) != len(self.participants):
            raise ConfigurationBarrageInvalide(
                "Un même participant figure deux fois parmi les tireurs de ce barrage."
            )

    def resultat(self) -> ResultatBarrage:
        """L'issue du barrage au vu des manches saisies — recalculée, jamais mémorisée.

        Tant qu'aucune manche n'est saisie, tout le monde est à égalité : le barrage est « à
        tirer », ce qui est un `groupes_a_rejouer` d'un seul groupe et non un ordre vide ambigu.

        ⚠️ **La manche 1 doit faire tirer TOUS les participants annoncés.** C'est le pendant, pour
        la première manche, de la règle « un groupe se retire en entier ou pas du tout » que
        `_rejouer` applique aux suivantes — et l'oubli qui rendait le reste inopérant : la manche 1
        ne passe pas par `_rejouer`, elle va droit à `partitionner_barrage`, qui ne connaît **que
        les tirs qu'on lui donne** et ne peut donc pas remarquer qu'il en manque. Un barrage annoncé
        à trois dont on ne saisissait que deux tirs rendait `est_resolu = True` en **oubliant** le
        troisième, lequel gardait ensuite `position_barrage = 0` au classement et passait devant
        ceux qui avaient tiré. L'invariant vit ici, dans le domaine, parce que `self.participants`
        n'est connu que de l'agrégat — le moteur, lui, ne voit jamais que des tirs.
        """
        if not self.manches:
            return ResultatBarrage(groupes_a_rejouer=(self.participants,))
        tireurs = {tir.participant for tir in self.manches[0]}
        if tireurs != set(self.participants):
            manquants = len(set(self.participants) - tireurs)
            raise ConfigurationBarrageInvalide(
                "La première manche d'un barrage fait tirer tous les participants annoncés : "
                f"{manquants} manquant(s). Un absent se saisit avec un score nul, il ne s'omet pas."
            )
        return resoudre_barrage_en_manches(self.manches)

    def verdict(self) -> VerdictBarrage:
        """Ce que ce barrage apporte au classement — **rien** tant qu'il n'a pas tout départagé.

        Un barrage non résolu rend un verdict d'`ordre` vide : le rang **reste partagé**. C'est la
        même exigence qu'en E05US015 — ne pas publier un classement à moitié vrai, qui s'afficherait
        sans avertir. Sans `rang_dispute` (Big Shoot Off), il n'y a pas de rang à éclater : le
        verdict n'a pas de sens et l'appelant lit `resultat()` pour connaître le sortant.
        """
        if self.rang_dispute is None:
            return VerdictBarrage(rang=0, ordre=())
        resultat = self.resultat()
        return VerdictBarrage(
            rang=self.rang_dispute, ordre=resultat.ordre if resultat.est_resolu else ()
        )
