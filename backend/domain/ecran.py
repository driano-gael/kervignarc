"""Écran de salle — `SequenceVues` (ce qu'il fait tourner) et `Consigne` (ce qu'on lui impose).

⚠️ **Le domaine ne lit pas l'heure** : il reçoit un écart déjà calculé et rend une règle. C'est ce
qui rend l'expiration lisible **côté écran** sans aller-retour serveur, et c'est central à
ADR-0064 — la fin d'une prise de contrôle naît du temps qui passe, or aucun événement serveur ne
peut pousser le temps qui passe.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum

from domain.erreurs import (
    CadenceDePageInvalide,
    CadenceEcranInvalide,
    ConsigneEcranInvalide,
    DureePriseDeControleInvalide,
    NombreDeNomsParPageInvalide,
    SequenceVuesVide,
)

CADENCE_MIN_S = 5
"""Plancher de cadence : sous 5 s, un écran vu de loin clignote plus qu'il n'informe."""

CADENCE_MAX_S = 3600
"""Plafond de cadence : au-delà d'une heure, ce n'est plus un déroulé mais une vue figée qui
s'ignore — et le CA a un geste dédié pour figer (la prise de contrôle), qui, lui, sait se terminer.
"""


class VueEcran(str, Enum):
    """Les vues qu'un écran de salle sait afficher (CA « classement, affectations, tableaux »).

    ✅ Le catalogue s'est élargi **trois fois sans une seule migration**, ce qui valide le choix
    d'origine : persister la **chaîne** et non un rang. ⚠️ Le quatrième mouvement n'en était pas un
    et a coûté une migration (`0047`, `TABLEAUX` → `EN_COURS`) : persister la chaîne rend un
    **ajout** gratuit, pas un **renommage**. La règle qui a gouverné les trois ajouts : **on
    n'inscrit une vue qu'une fois son écran capable de l'afficher**.
    """

    CLASSEMENT = "classement"
    PLAN_CIBLES = "plan_cibles"
    SUIVI_DEROULE = "suivi_deroule"
    AFFECTATIONS = "affectations"
    EN_COURS = "en_cours"
    """**Ce qui se joue maintenant**, quel que soit le format — arbre de duels, poule, ronde de
    système suisse ou manche de Big Shoot Off (E05US031, ADR-0089).

    Comme `AFFECTATIONS`, elle n'a de contenu qu'**après** la qualification : elle n'entre donc pas
    au déroulé par défaut. ⚠️ Elle s'appelait `TABLEAUX`, et le renommage n'est pas cosmétique — un
    `Tableau` est au glossaire le nom d'un **format**, et le garder sur une vue qui rend aussi une
    poule aurait fait dire à la base quelque chose de faux (comme `poule_numero` sur une ronde).
    """
    PALMARES = "palmares"
    """Le classement **final** — podiums en tête (E06US004).

    Distinct de `CLASSEMENT`, qui est celui de la **qualification** : à 17 h, ce qu'on projette
    n'est plus qui a le mieux tiré le matin mais qui a gagné. C'est le motif même du CA de pilotage
    des écrans (E07US004, ADR-0064) — « basculer sur le podium à 17 h et partir serrer des mains ».
    """


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
        que le public cherche le plus souvent. ⚠️ **`AFFECTATIONS` n'y figure délibérément pas** :
        elle n'a de contenu qu'après la qualification, soit l'essentiel de la journée, et
        l'inscrire ferait cycler tout écran neuf pendant des heures sur « pas encore de tableau
        final ». Le déroulé par défaut est fait de vues **toujours pleines**.
        """
        return SequenceVues(
            (
                VueProgrammee(VueEcran.CLASSEMENT, 30),
                VueProgrammee(VueEcran.PLAN_CIBLES, 30),
                VueProgrammee(VueEcran.SUIVI_DEROULE, 30),
            )
        )


NOMS_PAR_PAGE_MIN = 5
"""Plancher du nombre de noms par page : sous 5 noms, le nombre de pages explose.

Sur 200 archers et à la cadence par défaut, en **temps d'affichage cumulé** : une liste de noms
ferait 40 pages (~13 min) ; le **classement projeté**, où le front convertit ce nombre en lignes
(~3 noms par ligne), en ferait près de cent (~33 min) — et près d'une heure et demie d'horloge,
l'écran ne montrant le classement qu'un tiers du temps. 5 est une borne d'essai, pas un réglage.
"""

NOMS_PAR_PAGE_MAX = 100
"""Plafond du nombre de noms par page : au-delà, la hauteur de ligne d'un 1920x1080 tombe sous ce
qui se lit **à dix mètres** — or c'est exactement ce que la pagination existe pour préserver. Le
plafond ne prétend pas dire la bonne valeur : il borne un réglage dont le CA dit lui-même qu'il est
« à confirmer sur le vidéoprojecteur réel ».
"""

CADENCE_PAGE_MIN_S = 5
"""Plancher de cadence d'une page : même jugement que `CADENCE_MIN_S` — sous 5 s, une liste vue de
loin clignote plus qu'elle n'informe."""

CADENCE_PAGE_MAX_S = 300
"""Plafond de cadence d'une page : au-delà de cinq minutes, la liste ne défile plus, elle est figée
— et l'archer dont le nom est en page 3 ne le verra pas de la matinée."""


@dataclass(frozen=True)
class ReglagePages:
    """Comment une **liste projetée** se découpe et à quel rythme elle tourne (E16US009).

    ⚠️ **Deux durées coexistent sur un écran** : `VueProgrammee.cadence_s` dit combien de temps
    l'écran reste sur *une vue*, `cadence_page_s` à quel rythme la *liste* tourne **à
    l'intérieur**. Rien n'exige que l'une divise l'autre. **Réglage de l'écran, pas de la vue** :
    les deux valeurs dépendent de la diagonale du projecteur, de la distance de lecture et de la
    longueur des noms — trois propriétés du **lieu**. Résorbe `DETTE-039`.
    """

    noms_par_page: int
    cadence_page_s: int

    def __post_init__(self) -> None:
        if not NOMS_PAR_PAGE_MIN <= self.noms_par_page <= NOMS_PAR_PAGE_MAX:
            raise NombreDeNomsParPageInvalide(
                f"Une page projetée porte entre {NOMS_PAR_PAGE_MIN} et {NOMS_PAR_PAGE_MAX} noms "
                f"(reçu : {self.noms_par_page})."
            )
        if not CADENCE_PAGE_MIN_S <= self.cadence_page_s <= CADENCE_PAGE_MAX_S:
            raise CadenceDePageInvalide(
                f"La cadence d'une page doit être comprise entre {CADENCE_PAGE_MIN_S} et "
                f"{CADENCE_PAGE_MAX_S} secondes (reçu : {self.cadence_page_s})."
            )

    @staticmethod
    def par_defaut() -> ReglagePages:
        """Le réglage d'un écran qui n'a rien réglé — même parti que `SequenceVues.par_defaut`.

        Les valeurs sont **celles que le front tenait en dur** avant cette US (`DETTE-039`) : un
        écran déjà installé ne change donc pas de comportement, et la migration n'écrit rien. Les
        20 s viennent du questionnaire P06 ; les 40 noms sont un pari jamais confronté à un
        vidéoprojecteur réel — le rendre réglable permet de le corriger sans toucher au code.
        """
        return ReglagePages(noms_par_page=40, cadence_page_s=20)


@dataclass(frozen=True)
class Consigne:
    """Ce que l'admin impose à un écran, et jusqu'à quand.

    **Exactement l'un** de `vue` (figée) ou `sequence` (autre déroulé) : les deux, l'écran ne
    saurait laquelle honorer ; ni l'un ni l'autre, ce n'est pas une prise de contrôle mais un
    retour à la main. `duree_s` à `None` signifie « jusqu'à ce que je rende la main » — licite
    (arbitrage Q-UX7), mais cela porte un devoir de rappel (cf. `exige_rappel`).
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

    Alimente le compte à rebours des deux surfaces : la console et l'écran lui-même, qui décompte
    en local — la reprise ne dépend d'aucun message serveur. **Borné des deux côtés** : le plafond
    n'est pas décoratif, `secondes_ecoulees` étant un écart d'horloge qu'une mise à l'heure peut
    rendre négatif — la console annoncerait « reprise dans 12 min » sur une prise de 10 min.
    """
    if consigne.duree_s is None:
        return None
    return min(float(consigne.duree_s), max(0.0, consigne.duree_s - secondes_ecoulees))
