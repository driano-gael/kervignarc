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
    """Les vues qu'un écran de salle sait afficher (CA : « classement, affectations, tableaux,
    plans »).

    ✅ **Le catalogue couvre désormais le CA en entier** (E07US005, 04/08/2026). Il s'est élargi
    **trois fois sans une seule migration** — `PALMARES` (E06US004), `AFFECTATIONS` (E07US008),
    `TABLEAUX` (E07US005) —, ce qui valide au-delà du doute le choix d'origine : persister la
    **chaîne** et non un rang. Chaque élargissement a coûté une ligne ici et zéro dans la base.

    ⚠️ **Le quatrième mouvement n'était pas un élargissement, et il a coûté une migration**
    (E05US031, `0047`) : `TABLEAUX` est devenue `EN_COURS`. Persister la chaîne rend un **ajout**
    gratuit, pas un **renommage** — la propriété validée trois fois ci-dessus ne couvrait pas ce
    cas-là, et la lire comme « le catalogue ne coûte jamais de migration » aurait été un contresens.

    La règle qui a gouverné les trois ajouts, et qui vaut pour le suivant : **on n'inscrit une vue
    qu'une fois son écran capable de l'afficher**, sinon le réglage programme une page vide — un
    écran de salle n'a personne devant lui pour comprendre ce qui manque.
    """

    CLASSEMENT = "classement"
    PLAN_CIBLES = "plan_cibles"
    SUIVI_DEROULE = "suivi_deroule"
    AFFECTATIONS = "affectations"
    EN_COURS = "en_cours"
    """**Ce qui se joue maintenant**, quel que soit le format — l'arbre de duels, mais aussi la
    poule, la ronde de système suisse et la manche de Big Shoot Off (E05US031, ADR-0089).

    Complète le CA d'E07US004 (« classement, affectations, **tableaux**, plans »). Comme
    `AFFECTATIONS`, elle n'a de contenu qu'**après** la qualification — elle n'entre donc pas non
    plus au déroulé par défaut, pour la même raison (cf. `SequenceVues.par_defaut`).

    ⚠️ **Elle s'appelait `TABLEAUX` jusqu'à E05US031**, et le renommage n'est pas cosmétique : un
    `Tableau` est, au glossaire, un « arbre de matchs à élimination » — le nom d'un **format**. Le
    garder sur une vue qui rend aussi une poule aurait fait dire à la base quelque chose de faux,
    au même titre que `poule_numero` sur une ronde de suisse (migration `0046`, E05US026) : ce
    n'est pas un synonyme mal choisi, c'est le mauvais concept. Le mot juste ici est celui de
    l'onglet public — **« En cours »** — et non `PHASE`, exact mais illisible pour un spectateur."""
    PALMARES = "palmares"
    """Le classement **final** — podiums en tête (E06US004).

    Distinct de `CLASSEMENT`, qui est celui de la **qualification** : à 17 h, ce qu'on projette
    n'est plus qui a le mieux tiré le matin mais qui a gagné. C'est le motif même du CA de pilotage
    des écrans (**E07US004**, ADR-0064) — « basculer sur le podium à 17 h et partir serrer des
    mains ».

    *(Référence corrigée le 08/08/2026 : elle citait `E12US003`, qui est **doublement fausse** —
    l'identifiant est absorbé par `E12US002` depuis le 17/07/2026, et `E12US002` est le **feu vert
    et le lancement d'un tour**, pas le pilotage des écrans. La citation vient du CA d'`E07US004`,
    `stories/E07-affichage-public.md`.)*"""


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


NOMS_PAR_PAGE_MIN = 5
"""Plancher du nombre de noms par page : sous 5 noms, le nombre de pages explose — 200 archers
feraient 40 pages, soit plus de treize minutes avant de revoir la sienne à la cadence par défaut.
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

    ⚠️ **Deux durées coexistent sur un écran, et les confondre est le piège de cette US** :
    `VueProgrammee.cadence_s` dit combien de temps l'écran reste sur *une vue* ; `cadence_page_s`
    dit à quel rythme la *liste* tourne **à l'intérieur** de cette vue. Rien n'exige que l'une
    divise l'autre — la séquence de pages reprend où elle s'était arrêtée au passage suivant.

    **Réglage de l'écran, pas de la vue** (CA : « se règle **par écran** »), et ce n'est pas
    qu'une commodité : les deux valeurs dépendent de la **diagonale du projecteur, de la distance de
    lecture et de la longueur des noms du club** — trois propriétés du lieu, identiques pour toutes
    les vues d'un même écran et différentes d'un écran à l'autre. Les porter sur `VueProgrammee`
    aurait demandé de les répéter à chaque étape du déroulé, avec la possibilité d'en diverger sans
    qu'aucune règle ne le justifie.

    Résorbe `DETTE-039`, qui tenait ces deux valeurs en dur dans le front.
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

        Les valeurs sont **celles que le front tenait en dur** avant cette US (`NOMS_PAR_PAGE = 40`,
        `SECONDES_PAR_PAGE = 20`, `DETTE-039`) : un écran déjà installé ne change donc pas de
        comportement au déploiement, et la migration n'a aucune donnée à écrire.

        Les 20 s viennent du questionnaire P06 — *« on peut dire que 20 s (réglable) par écran de
        liste de noms est correct »*. Les 40 noms sont un pari jamais confronté à un vidéoprojecteur
        réel ; le rendre réglable est précisément ce qui permet de le corriger sans toucher au code.
        """
        return ReglagePages(noms_par_page=40, cadence_page_s=20)


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
