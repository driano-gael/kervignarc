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

from collections.abc import Sequence
from dataclasses import dataclass

from domain.erreurs import ConfigurationBarrageInvalide
from domain.participant import Participant

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
    if len(tirs) < 2:
        raise ConfigurationBarrageInvalide(
            "Un barrage départage au moins deux participants ; à un seul il n'y a rien "
            "à départager."
        )
    participants = [tir.participant for tir in tirs]
    if len(set(participants)) != len(participants):
        raise ConfigurationBarrageInvalide("Un même participant figure deux fois dans ce barrage.")

    ordre: list[Participant] = []
    groupes: list[tuple[Participant, ...]] = []
    for groupe in _groupes_de_score(tirs):
        if groupe[0].score is None:
            # Les absents : indépartageables entre eux par construction, ils n'ont pas tiré.
            if len(groupe) == 1:
                ordre.append(groupe[0].participant)
            else:
                groupes.append(tuple(tir.participant for tir in groupe))
            continue
        for sous_groupe in _departager_a_la_distance(groupe):
            if len(sous_groupe) == 1:
                ordre.append(sous_groupe[0].participant)
            else:
                groupes.append(tuple(tir.participant for tir in sous_groupe))
    if groupes:
        return ResultatBarrage(groupes_a_rejouer=tuple(groupes))
    return ResultatBarrage(ordre=tuple(ordre))


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
