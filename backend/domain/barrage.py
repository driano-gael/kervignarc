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
from itertools import pairwise

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


@dataclass(frozen=True)
class ResultatBarrage:
    """L'issue d'un barrage : l'ordre obtenu, ou les ex æquo qu'il faut faire retirer.

    Les deux champs sont **exclusifs** : soit le barrage a départagé tout le monde (`ordre` plein,
    `a_rejouer` vide), soit il ne l'a pas fait (`ordre` vide, `a_rejouer` nommant ceux qui restent à
    égalité). On ne rend **pas** un ordre partiel : un classement à moitié vrai est plus dangereux
    qu'un refus, parce qu'il s'affiche sans avertir.
    """

    ordre: tuple[Participant, ...] = ()
    a_rejouer: tuple[Participant, ...] = ()

    @property
    def est_resolu(self) -> bool:
        return not self.a_rejouer

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


def resoudre_barrage(
    tirs: Sequence[TirBarrage], configuration: ConfigurationBarrage | None = None
) -> ResultatBarrage:
    """Départage les participants d'un barrage (art. B.6.5.2).

    Ordre d'application, **séquentiel** :

    1. les **absents** (`score is None`) sont relégués derrière tous les présents, quelle que soit
       la suite — c'est B.6.5.2.4, et cela s'applique avant toute comparaison de score ;
    2. le **plus haut score** l'emporte ;
    3. à score égal, la **distance au centre** (la plus petite gagne) ;
    4. si l'égalité subsiste — scores égaux et distances égales ou non mesurées —, le barrage
       **n'est pas résolu** : les ex æquo sont renvoyés dans `a_rejouer`, et le règlement dit de
       répéter.

    ⚠️ **Le nombre de 10/9 n'intervient jamais** (B.6.5.2). C'est le seul endroit du produit où ce
    critère est écarté, et l'y réintroduire « pour éviter un retir » serait une faute réglementaire
    invisible : le classement produit aurait l'air correct.

    ⚠️ **Plusieurs absents restent ex æquo entre eux.** Deux absents sont tous deux « déclarés
    perdants » — le règlement ne les ordonne pas l'un par rapport à l'autre, et rien ne permet de le
    faire : ils n'ont pas tiré. On les renvoie donc à `a_rejouer` plutôt que d'inventer un ordre,
    quitte à ce que ce soit au service d'en tirer les conséquences (généralement : rang partagé).
    """
    del configuration  # le format (1 ou 3 flèches) contraint la saisie, pas le départage
    if len(tirs) < 2:
        raise ConfigurationBarrageInvalide(
            "Un barrage départage au moins deux participants ; à un seul il n'y a rien "
            "à départager."
        )
    participants = [tir.participant for tir in tirs]
    if len(set(participants)) != len(participants):
        raise ConfigurationBarrageInvalide("Un même participant figure deux fois dans ce barrage.")

    # Clé de tri : présent avant absent, puis score décroissant, puis distance croissante. Les
    # absents partagent une clé unique, ce qui les rend ex æquo entre eux — voir la docstring.
    def clef(tir: TirBarrage) -> tuple[int, int, int]:
        if tir.score is None:
            return (1, 0, 0)
        distance = tir.distance_au_centre if tir.distance_au_centre is not None else 0
        return (0, -tir.score, distance)

    tries = sorted(tirs, key=clef)
    a_rejouer: list[Participant] = []
    for precedent, suivant in pairwise(tries):
        if clef(precedent) != clef(suivant):
            continue
        # Deux tirs de clé identique : indépartageables **en l'état**. Si la distance n'a pas été
        # mesurée, c'est peut-être elle qui manque ; le règlement ne distingue pas les deux cas et
        # demande de répéter dans les deux.
        for tir in (precedent, suivant):
            if tir.participant not in a_rejouer:
                a_rejouer.append(tir.participant)
    if a_rejouer:
        return ResultatBarrage(a_rejouer=tuple(a_rejouer))
    return ResultatBarrage(ordre=tuple(tir.participant for tir in tries))
