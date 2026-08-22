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
`oppose_des_tireurs` (le plancher d'inscrits d'E05US021) et `deroule_par_un_service` (« un service
de production **exécute** ce type aujourd'hui »).

⚠️ **`deroule_par_un_service` décrit le code du jour, pas l'intention.** C'est la capacité la plus
facile à mentir : elle vaut `True` seulement si un service de production fait réellement jouer ce
type. `PLACEMENT` y vaut donc `False` — aucun service ne monte son tableau, ce que `phase.py`
consignait déjà (`# DETTE-028`) pendant que `deroule._TYPES_DEROULES` affirmait le contraire. C'est
l'une des deux divergences que ce module ferme.

⚠️ **Elle s'appelait `monte_les_oppositions` jusqu'à E05US028**, et le renommage est le premier
endroit où ce contrat a cédé — exactement là où [ADR-0083] §2 annonçait qu'il céderait. Le Big Shoot
Off n'a **ni matchs ni groupes** : il fait tirer une volée collective. La mettre à `True` pour lui
aurait été faux au sens de sa **propre définition**, et la laisser à `False` aurait fait mentir le
signal d'écart de l'atelier sur un format désormais jouable. Aucune des deux réponses n'était juste,
ce qui est la signature d'un nom trop étroit et non d'un cas particulier : la capacité a toujours
répondu « un service exécute-t-il ce type ? », c'est son nom qui décrivait *comment*. Les tables
dérivées ont suivi (`TYPES_MONTES` → `TYPES_DEROULES`).

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


class UniteDeTour(str, Enum):
    """*En combien de tours, et sous quel nom ?* — la 7ᵉ question du contrat ([ADR-0090]).

    Toute phase avance par tours, et **un tour n'est pas un braquet** : le tour dit *où on en
    est*, le braquet dit *quels rangs ce tour attribue*. Certaines phases classent au fil des
    tours (l'élimination directe, Règle R), d'autres ne classent qu'à la fin (la qualification :
    le total, pas la volée 12). L'unité vit ici, avec les autres questions du contrat ; sa
    **résolution en libellé** vit dans `domain/tour_de_phase.py`, qui délègue au tableau ce que
    le tableau sait déjà faire.

    L'unité est le **mot de la salle**, pas une forme technique : deux formats qui avancent de la
    même façon peuvent porter deux unités si le métier les nomme différemment (règle 3).

    [ADR-0090]: ../../docs/adr/0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md
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
    """Une ronde appariée : le système suisse et la colline (référentiel §10.1)."""

    MANCHE = "manche"
    """Une manche collective : le Big Shoot Off — tous les finalistes tirent en parallèle."""


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

    deroule_par_un_service: bool = False
    """Un service de **production** fait réellement jouer ce type, aujourd'hui.

    ⚠️ Se vérifie dans le code, jamais par l'intention. `PLACEMENT` vaut `False` parce qu'aucun
    service ne monte son tableau, quand bien même son *décor* est un arbre de duels.

    ⚠️ **Le nom ne dit pas *comment*, et c'est le correctif d'E05US028** : `monte_les_oppositions`
    supposait des matchs ou des groupes, que le Big Shoot Off n'a pas. Une capacité doit nommer la
    **question** qu'elle tranche, pas la forme que prend la réponse pour les types déjà écrits —
    sans quoi le premier format d'une autre forme la rend inrépondable."""

    classement_lisible: bool = False
    """Le moteur sait **lire** le classement de cette phase pour y prélever (E05US024).

    Distinct de `produit_un_classement` : une poule *produisait* un classement depuis E05US015
    sans que rien ne sache le *lire*, et un prélèvement la visant restait inerte."""

    avancement_lisible: bool = False
    """Un service sait dire **où en est** cette phase, tour par tour, aujourd'hui (E05US035).

    ⚠️ **À ne pas confondre avec `deroule_par_un_service`**, et la nuance décide de refus d'arrêt :
    celle-là répond « le moteur *fait jouer* cette phase ? » — donc si son prélèvement sera honoré,
    donc si son rang de départ **relève le plancher d'inscrits** (E05US021) —, celle-ci « sait-on
    *observer son tour* ? ». Les deux ensembles ne coïncident pas : la **qualification** s'observe
    (`ServiceSaisie.avancement_de_phase` compte les volées du plus lent) sans être « montée » par
    personne — elle n'a aucune opposition à monter. C'est exactement la raison pour laquelle
    `classement_lisible` est déjà une capacité distincte plutôt qu'un alias, et l'élargir en
    réutilisant `deroule_par_un_service` aurait fait réclamer un plancher par rangs à toute
    qualification prélevée : un refus de démarrage, le jour J, pour un réglage d'affichage.

    C'est de cette table que dérive `TYPES_ARRETABLES` — un arrêt programmé ne coupe qu'à une
    frontière de tour **observée** ([ADR-0091], [ADR-0093]).

    ⚠️ Se vérifie dans le code, jamais par l'intention : la mettre à `True` « puisque le format
    existe » reproduirait `DETTE-028`.

    [ADR-0091]: ../../docs/adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md
    [ADR-0093]: ../../docs/adr/0093-une-qualification-se-decoupe-en-tours-egaux.md
    """

    unite_de_tour: UniteDeTour = UniteDeTour.PHASE_ENTIERE
    """Dans quelle unité cette phase **avance**, et sous quel mot la salle la nomme ([ADR-0090]).

    ⚠️ **Sans rapport avec `produit_un_classement`**, et c'est tout l'objet de l'ADR : l'échauffement
    ne classe rien mais occupe du temps et des cibles — donc il avance, donc il a un tour. Le code
    dérivait jusqu'ici les tours des **braquets**, ce qui faisait afficher « zéro tour » à toute
    phase ne classant pas au fil de l'eau.

    [ADR-0090]: ../../docs/adr/0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md
    """

    route_l_archer: bool = False
    route_tout_le_plateau: bool = True
    """Cette phase concerne-t-elle **tous** les archers du créneau, ou une population restreinte ?

    ⚠️ **Capacité ajoutée à la revue d'E05US028**, sur un défaut constaté et non sur un pronostic.
    `route_l_archer` répond à « sait-on dire où cet archer tire ensuite ? » ; elle ne dit rien de
    *combien d'archers* la phase concerne. Tant que seule l'élimination directe routait, les deux
    questions se confondaient — un tableau reçoit le plateau. Le Big Shoot Off les sépare : il route
    **huit finalistes** sur cent vingt.

    Ce que la confusion coûtait, en production : `ServiceRoutage._phase_de_tableau` dérive sa cible
    de `TYPES_ROUTES` et, en résolution **implicite** (`phase_id=None`, le régime par défaut des
    tablettes), prend la dernière phase routée du créneau. Dès que l'élimination directe passait à
    `TERMINEE`, le Big Shoot Off devenait cette cible et les **112 non-finalistes** lisaient « Cet
    archer ne fait pas partie de ce Big Shoot Off » à la place de leur rang final — définitivement,
    puisque `tableaux[-1]` reste le Big Shoot Off une fois tout terminé. C'est le défaut que le
    commentaire de `_phase_de_tableau` disait vouloir éviter, appliqué à l'envers.
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
        # ✅ **`classement_lisible` bascule à `True` en fin de tranche E05US023** — et seulement une
        # fois le code écrit. Ce qui l'autorise, module par module :
        # `domain/classement_de_poules.py` range la phase « par rang de poule d'abord » (ADR-0083
        # §6), `ServicePoules.classement_de_phase` rend le `ClassementSource`, et
        # `ServiceSaisieDuels._classement_de_l_ordre` le lit par le port `LecteurClassementDePhase`.
        #
        # ⚠️ L'effet de cette ligne est **mesurable**, et c'est pourquoi elle a attendu : elle fait
        # réclamer le plancher d'inscrits (E05US021) pour un prélèvement visant des poules. Un
        # `True` posé par anticipation aurait exigé 34 inscrits pour une source que rien n'honore —
        # le « refus abusif le jour J » que cette US-là nommait comme sa pire défaillance.
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
        # ✅ Les trois capacités basculent **en fin de tranche E05US028**, et seulement une fois le
        # code écrit — même discipline qu'E05US023 pour les poules. Ce qui les autorise, module par
        # module :
        # `application/big_shoot_off.py` rejoue la phase des volées validées et rend son état
        # (`deroule_par_un_service`), `ServiceBigShootOff.classement_de_phase` rend le
        # `ClassementSource` que `ServiceSaisieDuels._classement_de_l_ordre` lit par le port
        # `LecteurClassementDePhase` (`classement_lisible`), et
        # `ServiceRoutage._routage_big_shoot_off` dit à un finaliste quelle manche il tire
        # (`route_l_archer`).
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
        # ✅ Les deux capacités basculent **en fin de tranche E05US026**, et seulement une fois le
        # code écrit — même discipline qu'E05US023 et E05US028. Ce qui les autorise, module par
        # module : `application/suisse.py` rejoue la phase des duels validés, ronde après ronde, et
        # rend son état (`deroule_par_un_service`) ; `ServiceSuisse.classement_de_phase` rend le
        # `ClassementSource` que `ServiceSaisieDuels._classement_de_l_ordre` lit par le port
        # `LecteurClassementDePhase`, via `domain/classement_de_suisse.py` (`classement_lisible`).
        #
        # ⚠️ L'effet de `classement_lisible` est **mesurable** : elle fait réclamer le plancher
        # d'inscrits (E05US021) pour un prélèvement visant un suisse. Elle n'est légitime que parce
        # que le prélèvement est réellement honoré — un `True` posé par anticipation aurait exigé
        # des inscrits pour une source que rien n'honore.
        deroule_par_un_service=True,
        avancement_lisible=True,
        classement_lisible=True,
        # ✅ **`route_l_archer` bascule ici aussi**, par le même chemin
        # (`ServiceRoutage._routage_par_rencontres`) : une rencontre de ronde **est** un duel, avec
        # deux adversaires nommés et deux couloirs — aucun champ de rendez-vous neuf n'a donc été
        # nécessaire, à la différence du Big Shoot Off dont la manche collective n'oppose personne.
        #
        # ⚠️ **Une issue neuve l'a été, en revanche** (E05US030, ce commentaire disait le contraire
        # jusque-là) : `EN_ATTENTE`. Elle ne vient pas de la forme du rendez-vous mais du **rythme**
        # du format — seule la ronde courante existe, donc un archer peut être en course sans rien
        # à tirer à cet instant (le porteur du bye, ou celui dont la rencontre vient d'être
        # validée). Un format à groupes connus d'avance, comme les poules, n'a pas ce régime.
        route_l_archer=True,
    ),
    TypePhase.COLLINE: ContratDePhase(
        decor=DecorDeSaisie.RONDES_APPARIEES,
        unite_de_tour=UniteDeTour.RONDE,
        # ✅ **Bascule en fin d'E05US027**, une fois `ServiceColline.regenerer_plan` écrit — et
        # `AUCUN` jusque-là, ce qui était exact tant que rien ne faisait tirer ce format.
        #
        # Même raisonnement que le suisse, et pour une raison **plus forte encore** : les défis
        # d'une manche ne changent pas seulement de composition, ils changent de **nombre**. À
        # portée 1 les extrémités se reposent une manche sur deux, et à portée 2 la distance tourne
        # — une manche à 4 archers apparie deux défis, la suivante un seul. « Archer → couloir »
        # serait donc une information non seulement fausse mais **instable**. C'est le bloc qui est
        # persisté (ADR-0083 §3), les couloirs de chaque défi s'y dérivant manche par manche.
        plan_de_cibles=PlanDeCibles.PAR_BLOC_DE_COULOIRS,
        # ✅ Les quatre capacités basculent **en fin de tranche E05US027**, et seulement une fois le
        # code écrit — même discipline qu'E05US023, E05US026 et E05US028. Ce qui les autorise,
        # module par module : `application/colline.py` rejoue la phase des duels validés, manche
        # après manche, en appliquant `appliquer_manche` à chaque manche close, et rend son état
        # (`deroule_par_un_service`) ; `ServiceColline.classement_de_phase` rend le
        # `ClassementSource` que `ServiceSaisieDuels._classement_de_l_ordre` lit par le port
        # `LecteurClassementDePhase`, via `domain/classement_de_colline.py`
        # (`classement_lisible`) ; `ServiceColline.avancement_de_phase` répond au port
        # `LecteurAvancementDePhase` (`avancement_lisible`, ADR-0090) ; et
        # `ServiceRoutage._routage_par_rencontres` dit à un archer quel défi il tire
        # (`route_l_archer`).
        #
        # ⚠️ **`avancement_lisible` est aussi ce qui rend la colline arrêtable** : `TYPES_ARRETABLES`
        # en dérive (ADR-0093). Une pause programmée peut donc se poser sur ce format dès cette US,
        # sans que rien n'ait à être ajouté du côté d'`ArretProgramme`.
        #
        # ⚠️ **`classement_lisible` a un effet mesurable** : elle fait réclamer le plancher
        # d'inscrits (E05US021) pour un prélèvement visant une colline. Elle n'est légitime que
        # parce que le prélèvement est réellement honoré — un `True` posé par anticipation aurait
        # exigé des inscrits pour une source que rien n'honore.
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

⚠️ **Nommée `TYPES_MONTES` jusqu'à E05US028** : « monter » supposait des oppositions à monter, ce
qu'un Big Shoot Off n'a pas. Le verbe « dérouler » est celui qu'emploie déjà tout le reste du code
(`domain/deroule.py`, « le moteur ne sait pas encore dérouler ce type »), donc le renommage
**supprime** un vocabulaire au lieu d'en ajouter un.

Répond à « le moteur va-t-il seulement monter cette phase ? ». C'est cette table qui décide si le
prélèvement d'une phase sera honoré, donc si son rang de départ **relève le plancher d'inscrits**
(E05US021)."""

TYPES_ARRETABLES: frozenset[TypePhase] = frozenset(
    type_phase for type_phase, contrat in _CONTRATS.items() if contrat.avancement_lisible
)
"""Les types sur lesquels une **pause programmée** peut se poser (E05US035, [ADR-0093]).

Répond à « sait-on *observer* le tour de cette phase ? », et c'est la seule question qui décide :
le déclencheur ne coupe qu'à une frontière de tour observée, donc un arrêt posé sur un type qu'on
ne sait pas lire serait accepté à l'atelier puis **définitivement inerte** le jour J.

⚠️ **Ce n'est pas `TYPES_DEROULES`**, bien que les deux aient coïncidé jusqu'à E05US035 — et c'est
la qualification qui les sépare : on sait dire où elle en est sans qu'aucun service ne la *monte*.
Le refus lisait `TYPES_DEROULES` tant qu'ils coïncidaient ; l'y laisser aurait obligé à mentir sur
l'autre capacité pour lever ce refus-ci, donc à réclamer un plancher d'inscrits par rangs à toute
qualification prélevée (E05US021). Deux questions, deux tables.

Miroir du registre `ServiceSuiviDeroule._avancements`, à l'élimination directe près — dont le
suivi reconstruit l'avancement des braquets projetés sans passer par le port. Le vis-à-vis des deux
oracles est tenu par `backend/tests/test_arrets_api.py`.

[ADR-0093]: ../../docs/adr/0093-une-qualification-se-decoupe-en-tours-egaux.md
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
définition*, donc annoncer un écart à son sujet serait un faux positif. Le signal doit cesser de
viser les poules et **continuer de viser** le suisse, la colline, le Big Shoot Off, le barrage
autonome et le placement — sans quoi il mentirait pour ceux qui restent (CA d'E05US023)."""


def produit_un_classement(type_phase: TypePhase) -> bool:
    """Cette phase ordonne-t-elle ses participants en sortie ? (E05US015, référentiel §10.1)"""
    return type_phase not in TYPES_SANS_CLASSEMENT
