"""Déroulé de vues d'un écran de salle et **prise de contrôle** admin (E07US004, ADR-0064).

Deux notions, un même module parce qu'elles répondent à la même question — *que montre cet écran,
maintenant ?* — et que la seconde est un **remplacement temporaire** de la première.

- `SequenceVues` : ce que l'écran fait tourner tout seul, « paramétré à la préparation du tournoi
  […] avec cadence réglable » (CA). Persisté par écran : *« plusieurs écrans possibles, chacun son
  déroulé »*.
- `Consigne` : ce que l'admin lui **impose** depuis la console — « soit une vue figée (ex. podium),
  soit une autre séquence » —, avec une **échéance** parce que le CA exige qu'« une prise de
  contrôle sache se terminer » et qu'il n'y ait « jamais un état forcé qu'on oublie ».

**Le domaine ne lit pas l'heure** (règle 9, déterminisme). Comme `domain.supervision.etat_poste`, il
reçoit un **écart déjà calculé** — `secondes_ecoulees` — et rend une règle. C'est aussi ce qui rend
l'expiration lisible **côté écran** sans aller-retour serveur : l'écran connaît le début et la
durée, il décompte lui-même. Le point est central au choix d'architecture d'ADR-0064 : la fin d'une
prise de contrôle **naît du temps qui passe**, or aucun événement serveur ne peut pousser le temps
qui passe (le même raisonnement qu'ADR-0038 §4 pour le passage hors-ligne d'un poste).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum

from domain.erreurs import (
    CadenceEcranInvalide,
    ConsigneEcranInvalide,
    DureePriseDeControleInvalide,
    SequenceVuesVide,
)

CADENCE_MIN_S = 5
"""Plancher de cadence : sous 5 s, un écran vu de loin clignote plus qu'il n'informe."""

CADENCE_MAX_S = 3600
"""Plafond de cadence : au-delà d'une heure, ce n'est plus un déroulé mais une vue figée qui
s'ignore — et le CA a un geste dédié pour figer (la prise de contrôle), qui, lui, sait se terminer.
"""


class VueEcran(str, Enum):
    """Les vues qu'un écran de salle sait afficher (CA : « classement, affectations, tableaux,
    plans »).

    ⚠️ **Le catalogue reste plus court que le CA** : `TABLEAUX` (E07US005) n'est pas livrée —
    l'inscrire ici ferait programmer un déroulé qui afficherait une page vide. Elle s'ajoutera avec
    son US, et la migration n'aura rien à reprendre : la valeur persistée est la chaîne, pas un
    rang.

    `AFFECTATIONS` est entrée avec E07US008, **sans migration**, exactement comme annoncé : la
    prévision de conception s'est vérifiée, ce qui est la meilleure preuve que persister la chaîne
    plutôt qu'un rang était le bon choix.
    """

    CLASSEMENT = "classement"
    PLAN_CIBLES = "plan_cibles"
    SUIVI_DEROULE = "suivi_deroule"
    AFFECTATIONS = "affectations"


@dataclass(frozen=True)
class VueProgrammee:
    """Une étape du déroulé : **quelle** vue, **combien de temps**."""

    vue: VueEcran
    cadence_s: int

    def __post_init__(self) -> None:
        if not CADENCE_MIN_S <= self.cadence_s <= CADENCE_MAX_S:
            raise CadenceEcranInvalide(
                f"La cadence d'une vue doit être comprise entre {CADENCE_MIN_S} et "
                f"{CADENCE_MAX_S} secondes (reçu : {self.cadence_s})."
            )


@dataclass(frozen=True)
class SequenceVues:
    """Le déroulé d'un écran : une liste **ordonnée**, jouée en boucle.

    Une liste et non un ensemble : « classement, plan, classement » est un réglage légitime — la
    vue qui intéresse le plus revient plus souvent.
    """

    vues: tuple[VueProgrammee, ...]

    def __post_init__(self) -> None:
        if not self.vues:
            raise SequenceVuesVide(
                "Un écran de salle doit programmer au moins une vue : un écran vide ne se plaint "
                "pas, et c'est précisément la panne que la supervision doit révéler."
            )

    @staticmethod
    def par_defaut() -> SequenceVues:
        """Le déroulé d'un écran neuf — CA « déroulé de vues **par défaut** ».

        Un écran doit informer **sans configuration** : on le branche, il tourne. L'ordre suit ce
        que le public cherche le plus souvent (où j'en suis, où je tire, où en est le tournoi).

        ⚠️ **`AFFECTATIONS` (E07US008) n'y figure délibérément pas** — question posée en revue, et
        tranchée par l'essai. Elle n'a de contenu qu'une fois un tableau constitué, c'est-à-dire
        **après la qualification**, soit l'essentiel de la journée. L'inscrire au défaut ferait
        cycler tout écran neuf, toutes les 90 secondes et pendant des heures, sur une page « pas
        encore de tableau final » : moins informatif que de ne pas l'afficher du tout. Le déroulé
        par défaut est fait de vues **toujours pleines** ; celle-ci s'ajoute à la main, quand elle
        a quelque chose à dire (scénario 3 de `docs/fonctionnel/E07US008.md`).
        """
        return SequenceVues(
            (
                VueProgrammee(VueEcran.CLASSEMENT, 30),
                VueProgrammee(VueEcran.PLAN_CIBLES, 30),
                VueProgrammee(VueEcran.SUIVI_DEROULE, 30),
            )
        )


@dataclass(frozen=True)
class Consigne:
    """Ce que l'admin impose à un écran, et jusqu'à quand.

    **Exactement l'un** de `vue` (figée) ou `sequence` (autre déroulé) : les deux, l'écran ne
    saurait laquelle honorer ; ni l'un ni l'autre, ce n'est pas une prise de contrôle mais un retour
    à la main — un **autre** geste, le seul qui efface la consigne.

    `duree_s` à `None` signifie « jusqu'à ce que je rende la main » : c'est licite (arbitrage Q-UX7
    du 01/08/2026, durée **et** retour explicite), mais cela porte un devoir de rappel (cf.
    `exige_rappel`).
    """

    vue: VueEcran | None
    sequence: SequenceVues | None
    duree_s: int | None

    def __post_init__(self) -> None:
        if (self.vue is None) == (self.sequence is None):
            raise ConsigneEcranInvalide(
                "Une prise de contrôle impose soit une vue figée, soit une autre séquence — "
                "exactement l'une des deux."
            )
        if self.duree_s is not None and self.duree_s <= 0:
            raise DureePriseDeControleInvalide(
                "La durée d'une prise de contrôle doit être strictement positive ; « jusqu'à ce "
                "que je rende la main » s'exprime par une durée absente, pas par zéro."
            )

    @property
    def exige_rappel(self) -> bool:
        """Vrai quand la consigne n'a **aucune échéance** — CA « jamais un état forcé qu'on
        oublie ».

        Le domaine ne peut pas empêcher un oubli ; il peut le **nommer**, et c'est ce drapeau que la
        console consomme pour afficher un rappel très visible. Sans lui, « jamais oublié » resterait
        une intention de rédaction sans point d'ancrage dans le code.
        """
        return self.duree_s is None

    def expiree(self, *, secondes_ecoulees: float) -> bool:
        """Vrai si la durée impartie est écoulée (borne **inclusive** : à 600 s, une consigne de
        10 min est terminée). Toujours faux sans durée."""
        if self.duree_s is None:
            return False
        return secondes_ecoulees >= self.duree_s


@dataclass(frozen=True)
class PriseDeControle:
    """Une consigne **posée**, avec l'instant où elle l'a été.

    Le domaine porte l'instant (comme `domain.supervision.ActivitePoste`) sans le **lire** :
    c'est le service qui, via le port `Horloge`, calcule l'écart et le repasse aux règles ci-dessus.
    La distinction est ce qui garde les tests déterministes (règle 9).
    """

    consigne: Consigne
    debut: datetime.datetime


def reste_secondes(consigne: Consigne, *, secondes_ecoulees: float) -> float | None:
    """Temps restant avant reprise automatique du déroulé ; `None` sans durée.

    Alimente le compte à rebours des deux surfaces : la console (« reprise dans 7 min ») et l'écran
    lui-même, qui décompte en local — la reprise ne dépend donc d'aucun message serveur.

    **Borné des deux côtés** : jamais négatif (plancher à 0), et jamais supérieur à la durée
    demandée (plafond). Le plafond n'est pas décoratif — `secondes_ecoulees` est calculé par le
    service comme un écart d'horloge, et une mise à l'heure en cours de journée peut le rendre
    négatif : la console annoncerait alors « reprise dans 12 min » sur une prise de 10 min, ce qui
    ferait douter de tout le reste de l'affichage (correctif de revue). Le front, lui, normalise
    déjà son propre modulo.
    """
    if consigne.duree_s is None:
        return None
    return min(float(consigne.duree_s), max(0.0, consigne.duree_s - secondes_ecoulees))
