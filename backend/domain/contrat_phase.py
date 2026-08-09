"""Le **contrat de phase jouable** — ce qu'un type de phase doit savoir répondre ([ADR-0083]).

**Pourquoi ce module existe.** Au 09/08/2026, **dix** endroits du code filtraient sur
`TypePhase.ELIMINATION_DIRECTE`, chacun répondant à une question légèrement différente : « monte-
t-elle un arbre ? », « le moteur va-t-il la monter ? », « sait-on lire ce qu'elle a classé ? »,
« peut-on y saisir un tir ? », « a-t-elle un plan de cibles ? »… Le code documentait lui-même que
ces tables « ne se recoupent que par coïncidence », et **deux divergences réelles** y étaient déjà
consignées. Ajouter les poules à dix tables indépendamment, puis le suisse, puis la colline,
garantissait la 3ᵉ, 4ᵉ et 5ᵉ : **la 3ᵉ occurrence réelle était atteinte**, donc le remède structurel
est justifié par le code d'aujourd'hui et non par une évolution supposée (règle « remède
structurel » de `CLAUDE.md`).

**Ce que le module fait, et ce qu'il ne fait pas.** Il ne supprime aucune des tables existantes —
leurs noms sont lus par une centaine de sites — il en fait des **dérivées** d'une source unique
*par capacité*. Ajouter un type se règle ici, à un seul endroit ; une table qui diverge devient
**impossible** plutôt qu'improbable. Il ne décide rien du **déroulé** : c'est un catalogue de
capacités, pas un moteur.

**Les six questions du contrat** (ADR-0083 §1) et où chacune est portée :

1. *Qui entre dedans ?* — générique depuis [ADR-0068] / E05US024 (`application/prelevement.py`),
   aucune capacité à déclarer ici.
2. *Qu'est-ce qu'on saisit ?* — `decor` (`DecorDeSaisie`).
3. *Quand est-ce validé ?* — le **grain**, déjà porté par `phase._GRAINS_ADMIS` : source unique
   depuis E05US015, donc rien à reprendre.
4. *Qui est classé, et dans quel ordre ?* — `produit_un_classement` et `classement_lisible`.
5. *Où l'archer tire-t-il ensuite ?* — `route_l_archer`.
6. *Combien de couloirs, et comment ?* — `plan_de_cibles` (`PlanDeCibles`).

Deux capacités s'y ajoutent, qu'aucune des six ne recouvre mais que le code posait déjà :
`oppose_des_tireurs` (le plancher d'inscrits d'E05US021) et `monte_les_oppositions` (« un service
de production **exécute** ce type aujourd'hui »).

⚠️ **`monte_les_oppositions` décrit le code du jour, pas l'intention.** C'est la capacité la plus
facile à mentir : elle vaut `True` seulement si un service de production monte réellement les
oppositions du type. `PLACEMENT` y vaut donc `False` — aucun service ne monte son tableau, ce que
`phase.py` consignait déjà (`# DETTE-028`) pendant que `deroule._TYPES_DEROULES` affirmait le
contraire. C'est l'une des deux divergences que ce module ferme.

Domaine **pur** : aucun framework, aucune autre couche (règle 1).

[ADR-0083]: ../../docs/adr/0083-le-contrat-de-phase-jouable.md
[ADR-0068]: ../../docs/adr/0068-le-moteur-consomme-les-prelevements-declares.md
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TypePhase(str, Enum):
    """Type d'une phase. E05US001 ouvre le typage aux formats dont la **règle est écrite** ;
    **E05US015 peuple le catalogue** avec les six types dont la règle a été obtenue du
    commanditaire le 31/07/2026 (référentiel §10.1) ou tirée du règlement (§8.2).

    ⚠️ La règle d'ADR-0045 §2 tient toujours — « on n'offre pas en façade un type qu'aucun moteur
    ne sait dérouler » : **chaque** valeur ajoutée ici vient avec son moteur de domaine
    (`poule.py`, `big_shoot_off.py`, `suisse.py`, `colline.py`, `barrage.py`) ; l'échauffement est
    le seul sans moteur, et c'est **son** contenu — une phase qui ne calcule rien.

    Trois formats du catalogue ouvert (EF-3.2) **n'apparaissent pas ici**, et ce n'est pas un
    oubli : le **repêchage** est une politique `routing`, le **handicap** une politique `scoring`,
    la **finale spectacle** un assemblage d'`elimination_directe` + `BaremeDuel` (E05US015,
    [ADR-0062]). Un type de phase se justifie par une **structure** propre, pas par un réglage.

    ⚠️ **Déplacé de `domain/phase.py` vers ce module en E05US023**, et le sens compte : le type et
    son **contrat** sont la même information, à deux niveaux de détail. Les laisser dans deux
    modules obligeait `phase.py` à importer le contrat pendant que le contrat importait le type —
    un cycle. `domain.phase` continue de le ré-exporter : les ~100 `from domain.phase import
    TypePhase` restent valides, il n'y avait rien à gagner à les réécrire.

    [ADR-0062]: ../../docs/adr/0062-catalogue-de-types-de-phase.md
    """

    QUALIFICATION = "qualification"
    ELIMINATION_DIRECTE = "elimination_directe"
    PLACEMENT = "placement"
    ECHAUFFEMENT = "echauffement"
    """Sans point et sans classement (§10.1) : elle occupe du temps et des cibles, rien de plus."""

    BARRAGE = "barrage"
    """Départage de tir **autonome** — 1 flèche, plus haut score (§8.2), avant de monter un
    tableau. Distinct du barrage *interne* à un duel nul (E04US013)."""

    POULES = "poules"
    """Groupes se rencontrant en round-robin, classement de poule à cinq critères (§10.1)."""

    BIG_SHOOT_OFF = "big_shoot_off"
    """Finale à N archers en parallèle, le plus faible éliminé à chaque manche (§10.1)."""

    SUISSE = "suisse"
    """Rondes appariant vainqueurs contre vainqueurs, personne n'est éliminé (§10.1)."""

    COLLINE = "colline"
    """King of the Hill et Ladder — **un seul moteur**, la portée de défi les sépare (§10.1)."""


class DecorDeSaisie(str, Enum):
    """*Qu'est-ce qu'on saisit ?* — la 2ᵉ question du contrat (ADR-0083 §1).

    Le décor est ce que le scoreur a **sous les yeux**, pas la règle de comptage. Deux types au
    même décor se saisissent avec le même écran : c'est précisément ce qui permet aux rencontres
    de poule de réutiliser le pavé de duel d'E04US013 sans écran neuf.
    """

    AUCUN = "aucun"
    """Rien à saisir — l'échauffement n'attribue rien (§10.1)."""

    SERIE_INDIVIDUELLE = "serie_individuelle"
    """L'archer tire seul sa série de volées : la qualification."""

    ARBRE_DE_DUELS = "arbre_de_duels"
    """Un arbre de matchs dont le nombre de tours se déduit de l'effectif seul."""

    RENCONTRES_EN_GROUPES = "rencontres_en_groupes"
    """Des rencontres appariées **dans un groupe**, présentées par tour : les poules.

    Même **pavé** de saisie qu'un arbre de duels (une rencontre *est* un duel ordinaire,
    ADR-0083 §6), mais une autre **navigation** : on entre par la poule et le tour, pas par le
    numéro de match d'un arbre."""

    RONDES_APPARIEES = "rondes_appariees"
    """Des rondes appariées ronde après ronde, sans élimination : suisse et colline."""

    VOLEE_COLLECTIVE = "volee_collective"
    """Tous les finalistes tirent la même volée en parallèle : le Big Shoot Off."""

    DEPARTAGE_A_LA_FLECHE = "departage_a_la_fleche"
    """Une flèche par archer à départager, au plus haut score puis au plus près du centre."""


class PlanDeCibles(str, Enum):
    """*Combien de couloirs, et comment ?* — la 6ᵉ question du contrat (ADR-0083 §1).

    L'**unité placée** diffère d'un format à l'autre, et c'est tout le sujet : un archer en
    qualification, une paire d'adversaires en élimination directe ([ADR-0048]), un **bloc de
    couloirs contigus** en poules (ADR-0083 §3, `domain/placement_poules.py`).

    [ADR-0048]: ../../docs/adr/0048-cote-a-cote-des-duellistes-par-reordonnancement.md
    """

    AUCUN = "aucun"
    """Cette phase ne produit pas de plan de cibles aujourd'hui."""

    PAR_ARCHER = "par_archer"
    """Un couloir par archer (`domain/placement.py`, ADR-0024)."""

    PAR_DUEL = "par_duel"
    """Les deux duellistes côte à côte (`ServicePlacementDuels`, ADR-0048)."""

    PAR_BLOC_DE_POULE = "par_bloc_de_poule"
    """Un bloc de couloirs contigus par **poule** — jamais « archer → couloir » (ADR-0083 §3).

    La raison est dans `poule.couloirs_occupes` : le membre au repos change à chaque tour, donc
    aucun membre n'a de couloir attitré. Persister l'archer écrirait une information *fausse*, pas
    seulement incomplète."""


@dataclass(frozen=True)
class ContratDePhase:
    """Ce qu'un type de phase sait répondre — une ligne du registre ci-dessous.

    **Les valeurs par défaut penchent du côté prudent**, et c'est délibéré : un type ajouté demain
    et laissé au défaut est *classant* et *opposant* (donc il réclame son plancher d'inscrits) mais
    n'est **ni monté, ni lu, ni routé** — l'oubli le plus probable est d'inscrire un vrai format au
    catalogue avant que son service existe, exactement ce qui s'est produit avec E05US015. Le
    défaut le fait alors se comporter comme un format inerte, ce qui est vrai, plutôt que comme un
    format joué, ce qui casserait en salle.
    """

    decor: DecorDeSaisie
    plan_de_cibles: PlanDeCibles
    produit_un_classement: bool = True
    """La phase **ordonne** ses participants en sortie. Faux pour le seul échauffement."""

    oppose_des_tireurs: bool = True
    """Un match y oppose **deux** tireurs — donc le plancher structurel est 2, pas 1 (E05US021)."""

    monte_les_oppositions: bool = False
    """Un service de **production** monte réellement les matchs/groupes de ce type, aujourd'hui.

    ⚠️ Se vérifie dans le code, jamais par l'intention. `PLACEMENT` vaut `False` parce qu'aucun
    service ne monte son tableau, quand bien même son *décor* est un arbre de duels."""

    classement_lisible: bool = False
    """Le moteur sait **lire** le classement de cette phase pour y prélever (E05US024).

    Distinct de `produit_un_classement` : une poule *produisait* un classement depuis E05US015
    sans que rien ne sache le *lire*, et un prélèvement la visant restait inerte."""

    route_l_archer: bool = False
    """Le routage sait dire où un archer de cette phase tire ensuite (`application/routage.py`)."""


# Le **registre** : une ligne par type, et la seule source de vérité des tables dérivées.
#
# ⚠️ Chaque ligne se lit comme un constat sur le code du jour, pas comme une promesse. Le rappel
# vaut surtout pour `monte_les_oppositions` : le mettre à `True` « puisque le moteur de domaine
# existe » reproduirait exactement `DETTE-028` — six moteurs livrés, aucun appelé.
_CONTRATS: dict[TypePhase, ContratDePhase] = {
    TypePhase.QUALIFICATION: ContratDePhase(
        decor=DecorDeSaisie.SERIE_INDIVIDUELLE,
        plan_de_cibles=PlanDeCibles.PAR_ARCHER,
        # L'archer tire **seul** sa série : un participant suffit à ce qu'elle ait un sens.
        oppose_des_tireurs=False,
        classement_lisible=True,
    ),
    TypePhase.ELIMINATION_DIRECTE: ContratDePhase(
        decor=DecorDeSaisie.ARBRE_DE_DUELS,
        plan_de_cibles=PlanDeCibles.PAR_DUEL,
        monte_les_oppositions=True,
        classement_lisible=True,
        route_l_archer=True,
    ),
    TypePhase.PLACEMENT: ContratDePhase(
        decor=DecorDeSaisie.ARBRE_DE_DUELS,
        plan_de_cibles=PlanDeCibles.PAR_DUEL,
        # ⚠️ **Aucun service ne monte ce tableau** — les deux services de duels filtrent sur
        # `ELIMINATION_DIRECTE` seul. `deroule._TYPES_DEROULES` l'y comptait pourtant, ce qui
        # **relevait le plancher d'inscrits** (E05US021) pour une phase que rien ne joue : le
        # « refus abusif le jour J » que cette US-là se donnait pour pire défaillance. Divergence
        # constatée et signalée par E06US006, tranchée ici (ADR-0083).
        monte_les_oppositions=False,
    ),
    TypePhase.ECHAUFFEMENT: ContratDePhase(
        decor=DecorDeSaisie.AUCUN,
        plan_de_cibles=PlanDeCibles.AUCUN,
        # « Sans point et sans classement » (§10.1) : c'est la définition du format, pas un manque.
        produit_un_classement=False,
        oppose_des_tireurs=False,
    ),
    TypePhase.BARRAGE: ContratDePhase(
        decor=DecorDeSaisie.DEPARTAGE_A_LA_FLECHE,
        plan_de_cibles=PlanDeCibles.AUCUN,
    ),
    TypePhase.POULES: ContratDePhase(
        decor=DecorDeSaisie.RENCONTRES_EN_GROUPES,
        plan_de_cibles=PlanDeCibles.PAR_BLOC_DE_POULE,
        monte_les_oppositions=True,
        # ⚠️ **`classement_lisible` reste `False` au 09/08/2026**, et c'est le constat le plus
        # inconfortable de ce registre. Le CA d'E05US023 exige qu'une phase avale consomme les
        # qualifiés d'une poule ; `ServicePoules` produit bien le classement de chaque groupe —
        # mais `ServiceSaisieDuels._classement_de_l_ordre` ne sait pas encore le rendre en
        # `ClassementSource`, faute d'un ordre inter-poules arrêté (les premiers de chaque poule,
        # puis les seconds ?) et d'un branchement cassant le cycle `ServicePoules` →
        # `ServiceSaisieDuels`.
        #
        # Le mettre à `True` par anticipation aurait un effet **mesurable et faux** : le plancher
        # d'inscrits (E05US021) serait réclamé pour un prélèvement que rien n'honore, soit le
        # « refus abusif le jour J » que cette US-là nommait comme sa pire défaillance. C'est
        # exactement le défaut d'ADR-0017 à l'échelle d'une capacité, et le registre ne vaut que
        # s'il décrit le code du jour.
        #
        # ⚠️ **`route_l_archer` reste `False`** pour une raison voisine mais distincte : le routage
        # est la 5ᵉ question du contrat, et `application/routage.py` ne sait pas dire à un membre de
        # poule où il tire ensuite. Celle-là n'est ni au CA ni à la liste d'ADR-0083 §« Restent à
        # écrire » — c'est une capacité **hors périmètre**, quand la précédente est une capacité
        # **au périmètre et non encore livrée**. Les distinguer importe : la première attendra une
        # US, la seconde doit être close avant que celle-ci parte en revue.
    ),
    TypePhase.BIG_SHOOT_OFF: ContratDePhase(
        decor=DecorDeSaisie.VOLEE_COLLECTIVE,
        plan_de_cibles=PlanDeCibles.AUCUN,
    ),
    TypePhase.SUISSE: ContratDePhase(
        decor=DecorDeSaisie.RONDES_APPARIEES,
        plan_de_cibles=PlanDeCibles.AUCUN,
    ),
    TypePhase.COLLINE: ContratDePhase(
        decor=DecorDeSaisie.RONDES_APPARIEES,
        plan_de_cibles=PlanDeCibles.AUCUN,
    ),
}


def contrat_de(type_phase: TypePhase) -> ContratDePhase:
    """Le contrat d'un type de phase.

    Lève `KeyError` sur un type absent du registre — volontairement **non rattrapé** : un type du
    catalogue sans contrat est une incohérence de code, pas une donnée douteuse. Le test
    `test_domain_contrat_phase` garantit qu'aucun `TypePhase` n'y manque, ce qui rend le cas
    inatteignable en production et fait échouer l'oubli à l'endroit utile — la suite, pas la salle.
    """
    return _CONTRATS[type_phase]


TYPES_EN_TABLEAU: frozenset[TypePhase] = frozenset(
    type_phase
    for type_phase, contrat in _CONTRATS.items()
    if contrat.decor is DecorDeSaisie.ARBRE_DE_DUELS
)
"""Les types qui montent un **arbre de duels** — leur profondeur de classement est un réglage.

Répond à « sait-on **dessiner** ses tours ? », donc porte sur le *décor* et non sur l'existence
d'un service : `placement` en fait partie sans être monté par personne."""

TYPES_MONTES: frozenset[TypePhase] = frozenset(
    type_phase for type_phase, contrat in _CONTRATS.items() if contrat.monte_les_oppositions
)
"""Les types qu'un service **exécute réellement** aujourd'hui (`deroule._TYPES_DEROULES`).

Répond à « le moteur va-t-il seulement monter cette phase ? ». C'est cette table qui décide si le
prélèvement d'une phase sera honoré, donc si son rang de départ **relève le plancher d'inscrits**
(E05US021)."""

TYPES_CLASSANTS_LUS: frozenset[TypePhase] = frozenset(
    type_phase for type_phase, contrat in _CONTRATS.items() if contrat.classement_lisible
)
"""Les types dont le moteur sait **lire le classement** pour y prélever (E05US024).

Miroir exact de `ServiceSaisieDuels._classement_de_l_ordre` : ce qu'il résout, on l'exige ; ce
qu'il rend `None`, on ne l'exige pas."""

TYPES_SANS_CLASSEMENT: frozenset[TypePhase] = frozenset(
    type_phase for type_phase, contrat in _CONTRATS.items() if not contrat.produit_un_classement
)
"""Les types qui **n'ordonnent pas** leurs participants — l'échauffement, et lui seul.

Source du contrôle `PhaseSansClassementPrelevee` : « les rangs 1 à 32 de l'échauffement » n'a pas
de sens, la seule succession licite étant `SourcePhase.le_reste`."""

TYPES_SANS_OPPOSITION: frozenset[TypePhase] = frozenset(
    type_phase for type_phase, contrat in _CONTRATS.items() if not contrat.oppose_des_tireurs
)
"""Les types où l'archer tire **seul** : un participant leur suffit (E05US021)."""

TYPES_ROUTES: frozenset[TypePhase] = frozenset(
    type_phase for type_phase, contrat in _CONTRATS.items() if contrat.route_l_archer
)
"""Les types dont le routage sait dire où l'archer tire ensuite (`application/routage.py`)."""

TYPES_EN_TABLEAU_JOUE: frozenset[TypePhase] = frozenset(
    type_phase
    for type_phase, contrat in _CONTRATS.items()
    if contrat.monte_les_oppositions and contrat.decor is DecorDeSaisie.ARBRE_DE_DUELS
)
"""Les types dont un service monte **et** déroule l'arbre de duels — l'élimination directe, seule.

Conjonction des deux capacités, et les deux sont nécessaires : il faut un arbre (le décor) **et**
un service qui le monte. `placement` a le premier sans le second, les poules le second sans le
premier. C'est le filtre de `ServiceSaisieDuels`, de `ServicePlacementDuels` et du palmarès —
trois sites qui écrivaient chacun `phase.type is not TypePhase.ELIMINATION_DIRECTE`.

⚠️ **Les poules en sont absentes**, bien qu'elles soient montées et lues : elles n'ont pas d'arbre.
Leur saisie, leur plan de cibles et leur classement passent par leur propre service — le contrat
sépare les deux formats **ici**, une fois, au lieu de le redemander à chaque appelant."""

TYPES_RECONSTRUCTIBLES: frozenset[TypePhase] = TYPES_EN_TABLEAU_JOUE
"""Les types dont le palmarès sait **rejouer l'arbre** (`application/palmares.py`).

⚠️ Alias de `TYPES_EN_TABLEAU_JOUE`, et **pas** une capacité de plus : « rejouer l'arbre » et
« monter l'arbre » sont la même chose ici, `ServicePalmares` déléguant à
`ServiceSaisieDuels.reconstruire`. Le nom subsiste parce qu'il dit ce que le palmarès en fait ;
en faire une entrée distincte du registre inviterait précisément la divergence qu'on ferme.

Les **poules** n'entrent donc pas au palmarès dans cette tranche. Ce n'est pas un oubli mais une
limite de périmètre (le CA d'E05US023 ne le demande pas) ; l'y verser demanderait un `_resultat`
propre au format, pas une entrée de plus dans une table."""

TYPES_JOUES: frozenset[TypePhase] = TYPES_CLASSANTS_LUS | TYPES_MONTES
"""Les types que la production sait **faire jouer**, montage ou classement (`ToursPhase.joue`).

Union assumée : la qualification n'a aucune opposition à monter mais se joue de bout en bout,
l'élimination directe et les poules ont les deux. C'est ce que le client affiche plutôt que des
zéros qui passeraient pour des constats — et ce sur quoi l'atelier signale un **écart** (E01US024)
pour les types qui, eux, ne se jouent pas encore."""

TYPES_SIGNALES_EN_ECART: frozenset[TypePhase] = frozenset(
    type_phase
    for type_phase, contrat in _CONTRATS.items()
    if type_phase not in TYPES_JOUES and contrat.produit_un_classement
)
"""Les types que l'atelier signale comme **composables mais pas jouables** (E01US024).

Un type non joué **et** non classant n'y figure pas : l'échauffement ne produit rien *par
définition*, donc annoncer un écart à son sujet serait un faux positif. Le signal doit cesser de
viser les poules et **continuer de viser** le suisse, la colline, le Big Shoot Off, le barrage
autonome et le placement — sans quoi il mentirait pour ceux qui restent (CA d'E05US023)."""


def produit_un_classement(type_phase: TypePhase) -> bool:
    """Cette phase ordonne-t-elle ses participants en sortie ? (E05US015, référentiel §10.1)"""
    return type_phase not in TYPES_SANS_CLASSEMENT
