"""Le **contrat de phase jouable** — une source unique par capacité (ADR-0083 §1).

Les tables historiques en sont **dérivées** : un type s'ajoute à un seul endroit, et une table qui
diverge devient impossible. Catalogue de capacités, pas un moteur.

⚠️ **`deroule_par_un_service` décrit le CODE DU JOUR, pas l'intention** — la capacité la plus facile
à mentir. `True` seulement si un service de production joue ce type ; `PLACEMENT` vaut `False`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TypePhase(str, Enum):
    """Type d'une phase — catalogue peuplé par E05US015 (référentiel §10.1, §8.2).

    ⚠️ ADR-0045 §2 tient toujours : **chaque** valeur ajoutée vient avec son moteur de domaine ;
    l'échauffement est le seul sans moteur, et c'est **son** contenu — une phase qui ne calcule
    rien. Repêchage, handicap et finale spectacle n'y figurent pas : ce sont des politiques ou un
    assemblage (ADR-0062). Un type se justifie par une **structure** propre, pas par un réglage.
    `domain.phase` le ré-exporte — le déplacer ici (E05US023) a rompu un cycle d'imports.
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


class UniteDeTour(str, Enum):
    """*En combien de tours, et sous quel nom ?* — la 7ᵉ question du contrat (ADR-0090).

    Toute phase avance par tours, et **un tour n'est pas un braquet** : le tour dit *où on en est*,
    le braquet *quels rangs ce tour attribue*. L'unité vit ici ; sa **résolution en libellé** vit
    dans `domain/tour_de_phase.py`.
    ⚠️ L'unité est le **mot de la salle**, pas une forme technique : deux formats qui avancent de la
    même façon peuvent porter deux unités si le métier les nomme différemment (règle 3).
    """

    PHASE_ENTIERE = "phase_entiere"
    """La phase **est** son tour — un seul, et il ne s'annonce pas.

    Qualification, échauffement, barrage : rien dans « 20 volées » ne dit s'il y a un ou quatre
    tours, c'est un choix de l'organisateur, et ce réglage arrive avec `E05US033` (les pauses
    programmées), là où il sert. En attendant, « un tour » est **vrai** — la phase entière en est
    un — et non un cas dégénéré à traiter à part. C'est aussi le **défaut prudent** du registre :
    un type ajouté demain et laissé au défaut avance d'un bloc, ce qui n'affiche rien de faux."""

    TOUR_DE_TABLEAU = "tour_de_tableau"
    """Un tour d'arbre, nommé par sa **distance au titre** : « Quart de finale », « 1/8 ».

    Le seul dont le libellé ne se déduit pas du numéro seul, et le seul qui connaisse des
    exceptions (petite finale, sous-tableau de placement)."""

    TOUR = "tour"
    """Un tour de round-robin : les poules."""

    RONDE = "ronde"
    """Une ronde appariée : le système suisse."""

    MANCHE = "manche"
    """Une manche : le Big Shoot Off — tous les finalistes tirent en parallèle — et la **colline**.

    ⚠️ La colline a porté `RONDE` jusqu'à E05US027, et c'était invisible tant qu'elle n'était pas
    `avancement_lisible` : la même phase annonçait « Manche 2 sur 3 » à la saisie et « Ronde 2 » au
    suivi du déroulé, tous deux publics. Le mot du métier est « manche » — `nb_manches` au réglage,
    `MancheAffichee` au service, et le référentiel §10.1. Que l'une soit collective et l'autre
    appariée ne change rien : l'unité est le **mot de la salle** (règle 3).
    """


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
    ADR-0083 §7), mais une autre **navigation** : on entre par la poule et le tour, pas par le
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
    couloirs contigus** en poules (ADR-0083 §3, `domain/placement_par_bloc.py`).

    [ADR-0048]: ../../docs/adr/0048-cote-a-cote-des-duellistes-par-reordonnancement.md
    """

    AUCUN = "aucun"
    """Cette phase ne produit pas de plan de cibles aujourd'hui."""

    PAR_ARCHER = "par_archer"
    """Un couloir par archer (`domain/placement.py`, ADR-0024)."""

    PAR_DUEL = "par_duel"
    """Les deux duellistes côte à côte (`ServicePlacementDuels`, ADR-0048)."""

    PAR_BLOC_DE_COULOIRS = "par_bloc_de_couloirs"
    """Un bloc de couloirs contigus par **poule** — jamais « archer → couloir » (ADR-0083 §3).

    La raison est dans `poule.couloirs_occupes` : le membre au repos change à chaque tour, donc
    aucun membre n'a de couloir attitré. Persister l'archer écrirait une information *fausse*, pas
    seulement incomplète."""


@dataclass(frozen=True)
class ContratDePhase:
    """Ce qu'un type de phase sait répondre — une ligne du registre ci-dessous.

    ⚠️ **Les valeurs par défaut penchent du côté prudent** : un type ajouté demain et laissé au
    défaut est *classant* et *opposant* mais n'est **ni monté, ni lu, ni routé**. L'oubli le plus
    probable est d'inscrire un format au catalogue avant que son service existe (E05US015) — le
    défaut le fait alors se comporter comme un format inerte, ce qui est vrai.
    """

    decor: DecorDeSaisie
    plan_de_cibles: PlanDeCibles
    produit_un_classement: bool = True
    """La phase **ordonne** ses participants en sortie. Faux pour le seul échauffement."""

    oppose_des_tireurs: bool = True
    """Un match y oppose **deux** tireurs — donc le plancher structurel est 2, pas 1 (E05US021)."""

    deroule_par_un_service: bool = False
    """Un service de **production** fait réellement jouer ce type, aujourd'hui.

    ⚠️ Se vérifie dans le code, jamais par l'intention : `PLACEMENT` vaut `False` parce qu'aucun
    service ne monte son tableau, quand bien même son *décor* est un arbre de duels.
    ⚠️ **Le nom ne dit pas *comment*** (E05US028) : une capacité nomme la **question** qu'elle
    tranche, pas la forme que prend la réponse pour les types déjà écrits.
    """

    classement_lisible: bool = False
    """Le moteur sait **lire** le classement de cette phase pour y prélever (E05US024).

    Distinct de `produit_un_classement` : une poule *produisait* un classement depuis E05US015
    sans que rien ne sache le *lire*, et un prélèvement la visant restait inerte."""

    avancement_lisible: bool = False
    """Un service sait dire **où en est** cette phase, tour par tour, aujourd'hui (E05US035).

    ⚠️ **À ne pas confondre avec `deroule_par_un_service`** : celle-là répond « le moteur *fait
    jouer* cette phase ? », donc si son rang de départ relève le plancher (E05US021) ; celle-ci
    « sait-on *observer son tour* ? ». La **qualification** s'observe sans être montée — les
    confondre aurait fait réclamer un plancher à toute qualification prélevée, donc un refus de
    démarrage pour un réglage d'affichage. `TYPES_ARRETABLES` en dérive (ADR-0091, ADR-0093).
    """

    unite_de_tour: UniteDeTour = UniteDeTour.PHASE_ENTIERE
    """Dans quelle unité cette phase **avance**, et sous quel mot la salle la nomme (ADR-0090).

    ⚠️ **Sans rapport avec `produit_un_classement`** : l'échauffement ne classe rien mais occupe du
    temps et des cibles — donc il avance, donc il a un tour. Le code dérivait jusqu'ici les tours
    des **braquets**, ce qui faisait afficher « zéro tour » à toute phase ne classant pas au fil.
    """

    route_l_archer: bool = False
    route_tout_le_plateau: bool = True
    """Cette phase concerne-t-elle **tous** les archers du créneau, ou une population restreinte ?

    ⚠️ `route_l_archer` répond à « sait-on dire où cet archer tire ensuite ? » et ne dit rien de
    *combien d'archers* la phase concerne. Le Big Shoot Off les sépare : il route huit finalistes
    sur cent vingt. Ce que la confusion coûtait : en résolution **implicite**,
    `ServiceRoutage._phase_de_tableau` prenait la dernière phase routée du créneau, si bien que les
    112 non-finalistes lisaient « ne fait pas partie de ce Big Shoot Off » au lieu de leur rang.
    """

    """Le routage sait dire où un archer de cette phase tire ensuite (`application/routage.py`)."""


# Le **registre** : une ligne par type, et la seule source de vérité des tables dérivées.
#
# ⚠️ Chaque ligne se lit comme un constat sur le code du jour, pas comme une promesse. Le rappel
# vaut surtout pour `deroule_par_un_service` : le mettre à `True` « puisque le moteur de domaine
# existe » reproduirait exactement `DETTE-028` — six moteurs livrés, aucun appelé.
_CONTRATS: dict[TypePhase, ContratDePhase] = {
    TypePhase.QUALIFICATION: ContratDePhase(
        decor=DecorDeSaisie.SERIE_INDIVIDUELLE,
        plan_de_cibles=PlanDeCibles.PAR_ARCHER,
        # L'archer tire **seul** sa série : un participant suffit à ce qu'elle ait un sens.
        oppose_des_tireurs=False,
        classement_lisible=True,
        # E05US035 : la qualification **s'observe** — `ServiceSaisie.avancement_de_phase` compte
        # les volées du plus lent de sa population — sans être « déroulée » au sens du
        # prélèvement, qu'elle n'a pas à monter. Elle reste donc `deroule_par_un_service=False`.
        avancement_lisible=True,
        # `TOUR` et non `PHASE_ENTIERE` depuis E05US035 : « 20 volées en 2 tours de 10 » est le
        # mot que la salle emploie, et le réglage qui le rend vrai existe désormais. La docstring
        # de `PHASE_ENTIERE` annonçait exactement ce changement (« ce réglage arrive avec les
        # pauses programmées, là où il sert »). Une qualification **non découpée** compte alors un
        # seul tour, ce qui reste vrai — la phase *est* son tour.
        unite_de_tour=UniteDeTour.TOUR,
    ),
    TypePhase.ELIMINATION_DIRECTE: ContratDePhase(
        decor=DecorDeSaisie.ARBRE_DE_DUELS,
        plan_de_cibles=PlanDeCibles.PAR_DUEL,
        unite_de_tour=UniteDeTour.TOUR_DE_TABLEAU,
        deroule_par_un_service=True,
        avancement_lisible=True,
        classement_lisible=True,
        route_l_archer=True,
    ),
    TypePhase.PLACEMENT: ContratDePhase(
        decor=DecorDeSaisie.ARBRE_DE_DUELS,
        plan_de_cibles=PlanDeCibles.PAR_DUEL,
        # Un tableau de placement se joue par tours comme un autre, même si aucun service
        # ne le monte encore : l'unité décrit la **forme** du format, pas son état
        # d'avancement dans le code (contrairement à `deroule_par_un_service` juste en
        # dessous, qui est un constat sur le code du jour).
        unite_de_tour=UniteDeTour.TOUR_DE_TABLEAU,
        # ⚠️ **Aucun service ne monte ce tableau** — les deux services de duels filtrent sur
        # `ELIMINATION_DIRECTE` seul. `deroule._TYPES_DEROULES` l'y comptait pourtant, ce qui
        # **relevait le plancher d'inscrits** (E05US021) pour une phase que rien ne joue : le
        # « refus abusif le jour J » que cette US-là se donnait pour pire défaillance. Divergence
        # constatée et signalée par E06US006, tranchée ici (ADR-0083).
        deroule_par_un_service=False,
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
        plan_de_cibles=PlanDeCibles.PAR_BLOC_DE_COULOIRS,
        unite_de_tour=UniteDeTour.TOUR,
        deroule_par_un_service=True,
        avancement_lisible=True,
        # ✅ **`classement_lisible` bascule à `True` en fin de tranche E05US023**, une fois le
        # code écrit : `domain/classement_de_poules.py` range la phase par rang de poule
        # (ADR-0083 §6), `ServicePoules.classement_de_phase` rend le `ClassementSource`, et
        # `ServiceSaisieDuels._classement_de_l_ordre` le lit par `LecteurClassementDePhase`.
        #
        # ⚠️ L'effet est **mesurable** : elle fait réclamer le plancher d'inscrits (E05US021) pour
        # un prélèvement visant des poules. Posée par anticipation, elle aurait exigé 34 inscrits
        # pour une source que rien n'honore — le « refus abusif le jour J ».
        classement_lisible=True,
        # ✅ **`route_l_archer` bascule en E05US026.** Elle valait `False` depuis E05US023, où le
        # routage était une capacité **explicitement hors périmètre** — au point que les poules
        # étaient devenues le seul format jouable sans routage une fois le Big Shoot Off livré.
        # Le commanditaire l'a fait entrer au périmètre le 15/08/2026 : le calcul s'écrivait de
        # toute façon pour le suisse, et `ServiceRoutage._routage_par_rencontres` sert les deux.
        route_l_archer=True,
    ),
    TypePhase.BIG_SHOOT_OFF: ContratDePhase(
        decor=DecorDeSaisie.VOLEE_COLLECTIVE,
        unite_de_tour=UniteDeTour.MANCHE,
        # ⚠️ **Reste `AUCUN`, et c'est un manque assumé** (E05US028). Les finalistes tirent bien en
        # parallèle, donc ils occupent des couloirs — mais aucun service ne les leur attribue : ce
        # sont des inscrits du créneau, et leur couloir de qualification n'est pas relu par le
        # moteur du format. Le routage le **nomme** au lieu de le taire (`DETTE-059`).
        plan_de_cibles=PlanDeCibles.AUCUN,
        # ✅ Les trois capacités basculent **en fin de tranche E05US028**, une fois le code écrit
        # — même discipline qu'E05US023. `application/big_shoot_off.py` rejoue la phase et rend son
        # état (`deroule_par_un_service`), `ServiceBigShootOff.classement_de_phase` rend le
        # `ClassementSource` (`classement_lisible`), et `ServiceRoutage._routage_big_shoot_off` dit
        # à un finaliste quelle manche il tire (`route_l_archer`).
        deroule_par_un_service=True,
        avancement_lisible=True,
        classement_lisible=True,
        route_l_archer=True,
        # ⚠️ **La seule phase du registre à population restreinte** : les finalistes, pas le
        # plateau. C'est ce qui la retire de la résolution *implicite* du routage (revue
        # d'E05US028) — elle reste routée, mais seulement quand on la désigne.
        route_tout_le_plateau=False,
    ),
    TypePhase.SUISSE: ContratDePhase(
        decor=DecorDeSaisie.RONDES_APPARIEES,
        unite_de_tour=UniteDeTour.RONDE,
        # ✅ **Bascule en fin de tranche E05US026**, une fois `ServiceSuisse.regenerer_plan` écrit.
        # Une ronde apparie tout le plateau et **ré-apparie à chaque ronde** : personne n'a de
        # couloir attitré, donc « archer → couloir » serait une information *fausse* — exactement la
        # raison pour laquelle les poules persistent un bloc (ADR-0083 §3). Le suisse en pose **un
        # seul**, là où une phase de poules en pose un par groupe : il n'y a rien à séparer.
        plan_de_cibles=PlanDeCibles.PAR_BLOC_DE_COULOIRS,
        # ✅ Les deux capacités basculent **en fin de tranche E05US026**, une fois le code écrit :
        # `application/suisse.py` rejoue la phase ronde après ronde (`deroule_par_un_service`) et
        # `ServiceSuisse.classement_de_phase` rend le `ClassementSource` via
        # `domain/classement_de_suisse.py` (`classement_lisible`).
        #
        # ⚠️ L'effet de `classement_lisible` est **mesurable** : elle fait réclamer le plancher
        # d'inscrits (E05US021) pour un prélèvement visant un suisse — légitime seulement parce que
        # ce prélèvement est réellement honoré.
        deroule_par_un_service=True,
        avancement_lisible=True,
        classement_lisible=True,
        # ✅ **`route_l_archer` bascule ici aussi** (`ServiceRoutage._routage_par_rencontres`) :
        # une rencontre de ronde **est** un duel, avec deux adversaires et deux couloirs — aucun
        # champ de rendez-vous neuf, à la différence du Big Shoot Off.
        #
        # ⚠️ **Une issue neuve l'a été** (E05US030) : `EN_ATTENTE`. Elle vient du **rythme** du
        # format — seule la ronde courante existe, donc un archer peut être en course sans rien à
        # tirer (le porteur du bye). Un format à groupes connus d'avance n'a pas ce régime.
        route_l_archer=True,
    ),
    TypePhase.COLLINE: ContratDePhase(
        decor=DecorDeSaisie.RONDES_APPARIEES,
        # ⚠️ **`MANCHE` et non `RONDE`** (correctif de revue, trois axes) : le décor est bien celui
        # du suisse — on saisit des rencontres appariées — mais l'unité est le mot de la salle, et
        # la salle dit « manche ». Les deux champs répondent à deux questions différentes du
        # contrat, et c'est précisément pourquoi ils ne se déduisent pas l'un de l'autre.
        unite_de_tour=UniteDeTour.MANCHE,
        # ✅ **Bascule en fin d'E05US027**, une fois `ServiceColline.regenerer_plan` écrit.
        #
        # Même raisonnement que le suisse, en plus fort : les défis d'une manche changent de
        # **nombre** — à portée 1 les extrémités se reposent une manche sur deux. « Archer →
        # couloir » serait donc non seulement faux mais **instable**. C'est le bloc qui est
        # persisté (ADR-0083 §3), les couloirs de chaque défi s'y dérivant manche par manche.
        plan_de_cibles=PlanDeCibles.PAR_BLOC_DE_COULOIRS,
        # ✅ Les quatre capacités basculent **en fin de tranche E05US027**, une fois le code écrit
        # : `application/colline.py` rejoue la phase manche après manche
        # (`deroule_par_un_service`), `classement_de_phase` rend le `ClassementSource`
        # (`classement_lisible`), `avancement_de_phase` répond au port `LecteurAvancementDePhase`
        # (ADR-0090), et `_routage_par_rencontres` dit quel défi un archer tire (`route_l_archer`).
        #
        # ⚠️ `avancement_lisible` rend aussi la colline **arrêtable** (`TYPES_ARRETABLES`,
        # ADR-0093), et `classement_lisible` fait réclamer le plancher d'inscrits (E05US021).
        deroule_par_un_service=True,
        avancement_lisible=True,
        classement_lisible=True,
        # ✅ Par le même chemin que le suisse (`_routage_par_rencontres`) : un défi **est** un duel,
        # avec deux adversaires nommés et deux couloirs. L'issue `EN_ATTENTE` (ADR-0087) y est déjà,
        # et la colline en a besoin pour la même raison de **rythme** que le suisse — l'archer au
        # repos d'une manche est en course sans rien à tirer à cet instant. Ici ce n'est même pas le
        # cas limite du bye à effectif impair : à portée 1, les deux extrémités se reposent une
        # manche sur deux, **quel que soit** l'effectif.
        route_l_archer=True,
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

TYPES_DEROULES: frozenset[TypePhase] = frozenset(
    type_phase for type_phase, contrat in _CONTRATS.items() if contrat.deroule_par_un_service
)
"""Les types qu'un service **exécute réellement** aujourd'hui (`deroule._TYPES_DEROULES`).

Répond à « le moteur va-t-il seulement monter cette phase ? ». C'est cette table qui décide si le
prélèvement d'une phase sera honoré, donc si son rang de départ **relève le plancher d'inscrits**
(E05US021). ⚠️ Nommée `TYPES_MONTES` jusqu'à E05US028 : « monter » supposait des oppositions à
monter, ce qu'un Big Shoot Off n'a pas.
"""

TYPES_ARRETABLES: frozenset[TypePhase] = frozenset(
    type_phase for type_phase, contrat in _CONTRATS.items() if contrat.avancement_lisible
)
"""Les types sur lesquels une **pause programmée** peut se poser (E05US035, ADR-0093).

Répond à « sait-on *observer* le tour de cette phase ? » : le déclencheur ne coupe qu'à une
frontière de tour observée, donc un arrêt posé sur un type illisible serait accepté à l'atelier puis
**définitivement inerte**. ⚠️ **Ce n'est pas `TYPES_DEROULES`** — la qualification les sépare : on
sait dire où elle en est sans qu'aucun service ne la *monte*. Miroir de
`ServiceSuiviDeroule._avancements`, vis-à-vis tenu par `backend/tests/test_arrets_api.py`.
"""

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

TYPES_ROUTES_IMPLICITEMENT: frozenset[TypePhase] = frozenset(
    type_phase
    for type_phase, contrat in _CONTRATS.items()
    if contrat.route_l_archer and contrat.route_tout_le_plateau
)
"""Les types qu'une tablette peut atteindre **sans les nommer** (`phase_id=None`).

Sous-ensemble strict de `TYPES_ROUTES` : une phase à population restreinte reste routée, mais
seulement quand on la désigne. Sans quoi elle capte le routage de tout le plateau — cf.
`ContratDePhase.route_tout_le_plateau`."""

TYPES_EN_TABLEAU_JOUE: frozenset[TypePhase] = frozenset(
    type_phase
    for type_phase, contrat in _CONTRATS.items()
    if contrat.deroule_par_un_service and contrat.decor is DecorDeSaisie.ARBRE_DE_DUELS
)
"""Les types dont un service monte **et** déroule l'arbre de duels — l'élimination directe, seule.

Conjonction de deux capacités, toutes deux nécessaires : un arbre (le décor) **et** un service qui
le monte. `placement` a le premier sans le second, les poules le second sans le premier. C'est le
filtre de `ServiceSaisieDuels`, `ServicePlacementDuels` et du palmarès — trois sites qui écrivaient
chacun `phase.type is not TypePhase.ELIMINATION_DIRECTE`. ⚠️ Les poules en sont absentes bien
qu'elles soient montées et lues : elles n'ont pas d'arbre.
"""

TYPES_RECONSTRUCTIBLES: frozenset[TypePhase] = TYPES_EN_TABLEAU_JOUE
"""Les types dont le palmarès sait **rejouer l'arbre** (`application/palmares.py`).

⚠️ Alias de `TYPES_EN_TABLEAU_JOUE`, et **pas** une capacité de plus : `ServicePalmares` délègue à
`ServiceSaisieDuels.reconstruire`. Le nom subsiste parce qu'il dit ce que le palmarès en fait ; en
faire une entrée distincte du registre inviterait la divergence qu'on ferme.

Les **poules** n'entrent donc pas au palmarès : limite de périmètre, pas oubli (CA d'E05US023).
"""

TYPES_JOUES: frozenset[TypePhase] = TYPES_CLASSANTS_LUS | TYPES_DEROULES
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
définition*. Le signal doit continuer de viser le barrage autonome et le placement. ⚠️ La table est
**dérivée** (compréhension sur `_CONTRATS`), donc jamais fausse — mais la phrase qui l'explique a
énuméré cinq types jusqu'à E05US027 alors qu'elle n'en contient plus que deux : rien ne rougit quand
le commentaire d'un ensemble calculé cesse de lui correspondre.
"""


def produit_un_classement(type_phase: TypePhase) -> bool:
    """Cette phase ordonne-t-elle ses participants en sortie ? (E05US015, référentiel §10.1)"""
    return type_phase not in TYPES_SANS_CLASSEMENT
