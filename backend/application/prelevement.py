"""Ce que deux services de tableau doivent lire **de la même façon** (E05US020, E06US006).

Deux règles y vivent, pour un seul et même motif : `preleves` (qui entre dans une phase) et
`profondeur_de` (jusqu'où cette phase départage). Le module s'appelait « la règle d'ensemencement »
quand il n'en portait qu'une ; il porte désormais **ce que `ServicePlacementDuels` et
`ServiceSaisieDuels` ne peuvent pas lire différemment sans monter deux arbres distincts**.

Deux services montent le même tableau à partir du même classement : `ServiceSaisieDuels` (l'arbre
que l'on joue) et `ServicePlacementDuels` (le plan de cibles qui pose les duellistes côte à côte).
Ils doivent ensemencer **exactement** la même population : le premier dit qui affronte qui, le
second où ils tirent. Un écart entre les deux, c'est un archer posté sur une butte sans duel, et
un autre en face du mauvais adversaire — invisible jusqu'au jour J.

Cette règle vivait **recopiée** aux deux endroits, avec un commentaire affirmant leur parité. La
recopie a tenu tant que la règle était « tous les archers en lice » ; elle a lâché à la première
évolution — E05US020 a fait consommer les prélèvements d'un seul côté, et la revue adversariale a
mesuré le résultat : plan de 8 placements pour un tableau de 4. D'où cette extraction, qui n'ajoute
aucune abstraction : une fonction pure, appelée deux fois.

**Pourquoi en couche application et non dans le domaine** : `preleves` croise un `Classement`
(domaine) et une `Phase` (domaine), mais son *besoin* est celui de deux cas d'usage. La poser dans
`domain/phase.py` obligerait ce module à importer `domain/classement.py`, qui importe déjà
`domain/politiques.py` — on paierait un couplage de modules pour une fonction de quinze lignes.

⚠️ **Cet argument ne vaut pas pour `profondeur_de`**, et la revue l'a relevé : elle ne touche pas au
`Classement`, elle croise une `Phase` et un
`RegistrePolitiques`, tous deux du domaine — et `domain/phase.py` importe déjà
`domain/politiques.py` depuis E06US006. Le couplage invoqué serait donc nul, et la
descendre dans le domaine la rendrait testable comme unité de domaine. Elle reste ici pour une autre
raison, moins noble mais réelle : c'est **le lieu que les deux services partagent déjà**, et le
motif de son extraction est un motif de cas d'usage (« ces deux-là ne peuvent pas diverger »), pas
une règle métier. À rouvrir si une troisième politique de phase rejoint la file — cf. ADR-0070.
"""

from __future__ import annotations

from collections.abc import Callable

from application.erreurs.moteur import PrelevementEnAttente
from domain.classement import Classement, LigneClassement, StatutClassement
from domain.classement_de_tableau import ClassementSource
from domain.phase import NatureSource, Phase, profondeur_par_defaut
from domain.politiques import Depth, RegistrePolitiques, assembler_politiques


def profondeur_de(phase: Phase, registre: RegistrePolitiques) -> Depth:
    """Jusqu'où cette phase départage — la politique `depth` **résolue** (E06US006, ADR-0070).

    Extraite ici pour la **même raison** que `preleves` : les deux services montent le même arbre
    (`construire_tableau`) et ne peuvent pas lui donner deux profondeurs différentes. Une seule
    lecture, deux appels.

    ⚠️ **La divergence n'est pas observable aujourd'hui**, et un premier jet affirmait le contraire
    (« les cibles d'un arbre qu'on ne joue pas »). Mesuré : sous `PlacementEnCascade`, les paires du
    **premier tour** sont identiques à toute profondeur, et `ServicePlacementDuels` ne consomme que
    ce tour — sa sortie est donc structurellement insensible au réglage. Ce que la lecture partagée
    achète est une garantie **future**, pour le jour où le plan couvrira les tours suivants ;
    `test_le_plan_de_cibles_reste_le_meme_a_toute_profondeur` fige l'état actuel et échouera alors.
    Le précédent d'E05US020 (plan de 8 pour un tableau de 4) reste la raison d'être du module, mais
    il portait sur l'**ensemencement**, pas sur la profondeur (ADR-0070 §5).

    Une phase qui ne règle rien retombe sur le **preset de son type** — le podium pour une
    élimination directe, le classement **intégral** pour un placement, qui n'a aucun existant à
    préserver. L'absence de réglage rejoue ce qui se jouait hier, elle ne convertit rien (ADR-0070).

    La résolution passe par le **registre** (règle 2) : le descripteur porté par la phase est de la
    donnée, la stratégie sort du catalogue. L'instancier à la main ferait de la politique une
    décoration — même parti que le `tiebreak` d'E06US003 (ADR-0066).
    """
    choix = phase.profondeur if phase.profondeur is not None else profondeur_par_defaut(phase.type)
    depth = assembler_politiques({"depth": choix.en_config()}, registre).depth
    if depth is None:
        # Inatteignable : `assembler_politiques` lève déjà `PolitiqueInconnue` sur un nom absent du
        # catalogue, et la clé est toujours fournie ci-dessus. Explicite plutôt que silencieux — un
        # repli maison réintroduirait ici la stratégie en dur que tout le chemin s'applique à ne pas
        # écrire.
        #
        # ⚠️ **`RuntimeError` et non une erreur typée de couche** (corrigé en revue, axe A). Une
        # `DomainError` serait mappée en **422** : le client s'entendrait reprocher une faute
        # métier alors que la panne réelle est un **catalogue incomplet au composition root**. Cette
        # branche doit tomber dans le filet `_sur_erreur_inattendue` (500), qui dit la vérité — un
        # défaut de câblage serveur — sans rien laisser fuir vers le client.
        raise RuntimeError(
            f"Profondeur « {choix.nom.value} » absente du registre : catalogue mal peuplé."
        )
    return depth


ResolveurClassement = Callable[[int], ClassementSource | None]
"""Rend le classement produit par la phase de cet `ordre`, ou `None` si elle n'en produit aucun.

Le paramètre qui a remplacé `ordre_qualification` (E05US024). Un **résolveur** et non une table
toute faite : la résolution d'un tableau amont coûte une reconstruction complète (`DETTE-031`), on
ne la paie donc que pour les ordres réellement déclarés en source.

Rend un `ClassementSource` et non un `Classement` nu : l'appelant a besoin de deux choses de plus
que les lignes — les **plages encore indécises** (pour refuser une fenêtre à laquelle la compétition
n'a pas répondu, ADR-0081) et le **rang de tournoi** du premier rang de ce classement (pour que le
décalage se cumule le long de la chaîne, cf. `tranche`).
"""


def _en_lice(classement: Classement) -> list[LigneClassement]:
    """Les lignes prélevables d'un classement, du meilleur rang au moins bon.

    **Seuls les archers en lice.** Un forfait déclaré en qualification (abandon relégué, DSQ exclu)
    n'accède pas à la phase suivante, et son rang scratch peut être `None` (ADR-0050).
    """
    return sorted(
        (ligne for ligne in classement.lignes if ligne.statut is StatutClassement.EN_LICE),
        key=lambda ligne: ligne.rang_scratch or 0,
    )


def _effectif(classement: Classement) -> int:
    """Les archers **classés** — un disqualifié n'a pas de rang (ADR-0050).

    C'est la borne que `SourcePhase.intervalle` réclame pour résoudre une fin ouverte (« les rangs
    33 **et suivants** ») : elle se lit sur le classement **de la phase source**, pas sur celui du
    tournoi. C'est toute la différence qu'apporte E05US024 — une consolante prélevant « le reste »
    d'un tableau de 32 ne doit pas se croire ouverte jusqu'au 120ᵉ inscrit.
    """
    return sum(1 for ligne in classement.lignes if ligne.rang_scratch is not None)


def preleves(
    phase: Phase, classement: Classement, resoudre_source: ResolveurClassement
) -> list[LigneClassement]:
    """Les archers prélevés, chacun lu dans le classement de **sa** phase source.

    C'est ici que le moteur cesse d'ignorer `phase.sources` (cœur de `DETTE-028`). Jusqu'à
    E05US020, le tableau était ensemencé avec **tous** les archers en lice : un format déclarant
    « les rangs 1 à 32 » se jouait à 120 si 120 archers étaient classés, et l'organisateur repartait
    avec un tournoi qui ne suivait pas le schéma qu'il avait composé et validé (E01US024).

    La règle tient en une phrase : **un prélèvement par rangs garde les archers dont le rang tombe
    dans son intervalle, au classement de la phase qu'il désigne**. Les bornes viennent du domaine
    (`SourcePhase.intervalle`), qui sait déjà résoudre une fin ouverte. On consomme cette
    sémantique, on ne la réécrit pas.

    ⚠️ **E05US024 — chaque source est lue dans son propre classement.** E05US020 n'honorait que les
    sources visant la **qualification** : « les rangs 1 à 8 de la phase 2 » prenait les 8 premiers
    de
    la *qualification* en croyant prendre ceux du tableau principal. Sa note invoquait un cycle
    service → service ; vérifié depuis, il n'y en a pas — la lecture nécessaire
    (`tableau.positions_acquises`) est produite par `ServiceSaisieDuels` **lui-même**, donc c'est
    une
    récursion, sur un graphe acyclique par construction (`verifier_sequence` exige une source
    **antérieure**).

    ⚠️ **Deux natures restent inertes** : `le_reste` et `par_issue_de_tour`. Vérifié au cadrage —
    ni l'une ni l'autre n'est résolue nulle part (`effectif_selectionne`, `resoudre` et `intervalle`
    rendent `None`). Leur donner un sens dans un service d'exécution serait décider une règle métier
    au mauvais endroit — l'erreur qu'ADR-0065 §3 a refusé de commettre, que `DETTE-033` acte. Cette
    US élargit **quelle phase** on lit, pas **quelles natures** on sait résoudre.

    ⚠️ **Une fenêtre qui coupe un bloc indécis lève `PrelevementEnAttente`** (ADR-0081,
    correctif de revue adversariale). Un tableau de 8 non commencé porte ses huit archers sur la
    plage `[1..8]` de leur quart en cours : lui demander « les rangs 5 à 8 » rendait les 4 derniers
    **qualifiés** au lieu des 4 battus des quarts — bien formé, plausible, et faux, exactement la
    classe de défaut que
    cette US ferme par ailleurs, en **moins détectable** qu'avant (la population avait le bon
    cardinal). Le refus est typé pour que les trois consommateurs — écran public, plan de cibles,
    saisie — puissent dire « en attente » au lieu d'afficher une fiction.

    Une phase **sans source** (ou qui n'en déclare que d'illisibles) est alimentée par le
    `classement` reçu — les inscriptions du créneau. C'est la première de sa séquence, et c'est le
    comportement d'avant l'US, à ne pas casser (CA « la phase de tête est inchangée »).

    **L'ordre du résultat** est `(ordre de la phase source, rang dans ce classement)`. Il est
    déterministe et, à source unique, identique à celui d'avant l'US — ce qui compte, parce que le
    `Seeding` consomme cette liste dans l'ordre : la permuter changerait les appariements.
    """
    retenus: list[tuple[int, int, LigneClassement]] = []
    lisible = False
    for source in phase.sources:
        # Nature inerte (`le_reste`, `par_issue_de_tour`, `DETTE-033`) : on sort **avant** de
        # résoudre. Résoudre d'abord coûtait une reconstruction complète du tableau amont pour
        # jeter le résultat — et pire, faisait **échouer** la phase aval quand cette
        # reconstruction levait, alors que la source est par contrat sans effet (relevé en revue,
        # axe C1 : régression mesurée contre `main`).
        if source.nature is not NatureSource.RANGS:
            continue
        source_resolue = resoudre_source(source.ordre_source)
        if source_resolue is None:
            continue
        borne = source.intervalle(_effectif(source_resolue.classement))
        if borne is None:
            continue
        lisible = True
        debut, fin = borne
        coupee = source_resolue.coupe(debut, fin)
        if coupee is not None:
            raise PrelevementEnAttente(
                f"La phase {phase.ordre} prélève les rangs {debut} à {fin} de la phase "
                f"{source.ordre_source}, qui n'a pas encore départagé les rangs {coupee[0]} à "
                f"{coupee[1]}.",
                source.ordre_source,
            )
        for ligne in _en_lice(source_resolue.classement):
            if ligne.rang_scratch is not None and debut <= ligne.rang_scratch <= fin:
                retenus.append((source.ordre_source, ligne.rang_scratch, ligne))
    if not lisible:
        return _en_lice(classement)
    # Dédoublonnage : deux sources peuvent viser le même archer (« les demi-finalistes **et** le
    # gagnant du secondaire » ne se recoupent pas, mais rien ne l'impose entre phases sources
    # distinctes — `verifier_sequence` ne contrôle le non-recoupement qu'**au sein** d'une phase).
    # Un archer présent deux fois dans un tableau y disputerait deux duels à la fois.
    vus: set[int] = set()
    ordonnes: list[LigneClassement] = []
    for _, _, ligne in sorted(retenus, key=lambda entree: (entree[0], entree[1])):
        if ligne.archer_id not in vus:
            vus.add(ligne.archer_id)
            ordonnes.append(ligne)
    return ordonnes


def tranche(phase: Phase, resoudre_source: ResolveurClassement) -> int:
    """Le **premier rang du tournoi** que cette phase dispute — 1 si elle les dispute tous.

    Une phase qui prélève « les rangs 5 et suivants » ne joue **pas** pour la victoire : elle
    dispute les places 5 et au-delà. Son vainqueur est 5ᵉ du tournoi, pas 1ᵉʳ. Le palmarès a besoin
    de ce décalage pour situer ses positions dans l'espace de rangs **du tournoi** au lieu de celui
    du tableau (ADR-0068 §5, résorbe `DETTE-034`).

    Sans lui, le palmarès situait les archers par l'`ordre` de leur phase — « la plus tardive
    l'emporte » — et couronnait donc le vainqueur d'une **consolante** devant le finaliste du
    tableau principal. Le défaut était inatteignable tant qu'aucun moteur ne consommait les
    prélèvements ; E05US020 l'a rendu atteignable, et la revue adversariale l'a mesuré.

    ⚠️ **Le rang rendu est celui du tournoi, pas celui de la phase source** (E05US024). Une phase
    prélevant « les rangs 1 à 2 » d'un tableau qui disputait lui-même les places 5 à 8 joue pour la
    **5ᵉ** place, pas pour la 1ᵉʳᵉ : le décalage se **cumule** le long de la chaîne.

    ⚠️ **Un premier jet affirmait ce cumul sans le faire** (bloquant de revue, relevé par trois
    axes). Il invoquait le `rang_scratch` du classement source, « qui porte déjà ce décalage quand
    la
    source est un tableau » : c'est faux, `classement_de_tableau` numérote **1 à N dans l'espace de
    rangs du tableau**, précisément pour que les fenêtres déclarées à la composition (« les rangs 1
    à
    2 de la phase 2 ») gardent leur sens local. Le décalage ne se cumulait donc pas, et le
    vainqueur d'une finale de consolante disputant les places 33 à 36 était publié **1ᵉʳ du
    tournoi**, devant le champion — `DETTE-034` rouverte un cran plus bas par l'US censée l'élargir.

    Le cumul se fait donc ici, explicitement : `ClassementSource.rang_premier` porte le rang de
    tournoi du rang 1 de ce classement, et l'on compose `rang_premier - 1 + rang_debut`. Une source
    visant la qualification (`rang_premier = 1`) redonne `rang_debut` — le comportement d'avant, à
    ne pas casser.

    Rend **1** quand la phase ne déclare aucun prélèvement lisible en rangs : elle est alimentée par
    les inscriptions et dispute donc le tournoi entier.
    """
    debuts = [
        source_resolue.rang_premier - 1 + borne[0]
        for source in phase.sources
        if source.nature is NatureSource.RANGS
        if (source_resolue := resoudre_source(source.ordre_source)) is not None
        if (borne := source.intervalle(_effectif(source_resolue.classement))) is not None
    ]
    return min(debuts) if debuts else 1
