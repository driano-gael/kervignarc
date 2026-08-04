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

from domain.classement import Classement, LigneClassement, StatutClassement
from domain.phase import Phase, profondeur_par_defaut
from domain.politiques import Depth, RegistrePolitiques, assembler_politiques


def profondeur_de(phase: Phase, registre: RegistrePolitiques) -> Depth:
    """Jusqu'où cette phase départage — la politique `depth` **résolue** (E06US006, ADR-0070).

    Extraite ici pour la **même raison** que `preleves`, et pour un risque identique : les deux
    services montent le même arbre (`construire_tableau`) et doivent lui donner la **même**
    profondeur. S'ils divergeaient, `ServicePlacementDuels` poserait les cibles d'un tableau et
    `ServiceSaisieDuels` en jouerait un autre — la panne exacte qu'E05US020 a produite sur
    l'ensemencement, mesurée en revue (plan de 8 pour un tableau de 4). Une seule lecture, deux
    appels.

    Une phase qui ne règle rien retombe sur le **preset de son type** (le podium), et non sur 1→N :
    l'absence de réglage doit rejouer ce qui se jouait hier, pas convertir les tournois existants
    au placement intégral (ADR-0070).

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


def preleves(
    phase: Phase, classement: Classement, ordre_qualification: int | None
) -> list[LigneClassement]:
    """Les archers que **cette phase déclare prélever**, dans l'ordre du classement source.

    C'est ici que le moteur cesse d'ignorer `phase.sources` (cœur de `DETTE-028`). Jusqu'à
    E05US020, le tableau était ensemencé avec **tous** les archers en lice : un format déclarant
    « les rangs 1 à 32 » se jouait à 120 si 120 archers étaient classés, et l'organisateur repartait
    avec un tournoi qui ne suivait pas le schéma qu'il avait composé et validé (E01US024).

    La règle tient en une phrase : **un prélèvement par rangs garde les archers dont le rang scratch
    tombe dans son intervalle**. Les bornes viennent du domaine (`SourcePhase.intervalle`), qui sait
    déjà résoudre une fin ouverte — « les rangs 33 et suivants ». On consomme cette sémantique, on
    ne la réécrit pas.

    ⚠️ **Seules les sources visant la QUALIFICATION sont honorées** (`ordre_qualification`). C'est
    le seul classement lisible ici ; appliquer « les rangs 1 à 8 de la phase 2 » à ce classement
    prendrait les 8 premiers de la **qualification** en croyant prendre ceux du tableau principal —
    un tableau bien formé, plausible, et faux, que rien ne signalerait. Lire le classement d'un
    tableau amont demande la lecture d'E06US004 et créerait un cycle service → service.

    ⚠️ **Deux natures restent inertes** : `le_reste` et `par_issue_de_tour`. Vérifié au cadrage —
    ni l'une ni l'autre n'est résolue nulle part (`effectif_selectionne`, `resoudre` et `intervalle`
    rendent `None`). Leur donner un sens dans un service d'exécution serait décider une règle métier
    au mauvais endroit — l'erreur qu'ADR-0065 §3 a refusé de commettre, que `DETTE-033` acte.

    Une phase **sans source** (ou qui n'en déclare que d'inertes) est alimentée par les
    inscriptions : c'est la première de sa séquence, et c'est le comportement d'avant l'US.
    """
    en_lice = sorted(
        (ligne for ligne in classement.lignes if ligne.statut is StatutClassement.EN_LICE),
        key=lambda ligne: ligne.rang_scratch or 0,
    )
    # L'effectif de la phase source : les archers **classés**. Un disqualifié n'a pas de rang
    # (ADR-0050). ⚠️ Cette borne est aujourd'hui **redondante** avec le classement lui-même — le
    # rang d'une ligne classée ne dépasse jamais le nombre de lignes classées, donc la borne haute
    # d'une fin ouverte ne filtre rien. On la passe quand même parce que c'est l'appel
    # sémantiquement juste : le jour où `intervalle` changera d'écrêtage, le site sera correct sans
    # retouche. *(Un premier jet de l'ADR en faisait un argument central ; la revue adversariale a
    # montré, mutation à l'appui, qu'aucun test ne pouvait le distinguer — parce qu'il n'y a rien à
    # distinguer. L'argument a été retiré plutôt que d'être illustré par un test décoratif.)*
    effectif_source = sum(1 for ligne in classement.lignes if ligne.rang_scratch is not None)
    intervalles = [
        borne
        for source in phase.sources
        if source.ordre_source == ordre_qualification
        if (borne := source.intervalle(effectif_source)) is not None
    ]
    if not intervalles:
        return en_lice
    return [
        ligne
        for ligne in en_lice
        if ligne.rang_scratch is not None
        and any(debut <= ligne.rang_scratch <= fin for debut, fin in intervalles)
    ]


def tranche(phase: Phase, classement: Classement, ordre_qualification: int | None) -> int:
    """Le **premier rang du tournoi** que cette phase dispute — 1 si elle les dispute tous.

    Une phase qui prélève « les rangs 5 et suivants » ne joue **pas** pour la victoire : elle
    dispute les places 5 et au-delà. Son vainqueur est 5ᵉ du tournoi, pas 1ᵉʳ. Le palmarès a besoin
    de ce décalage pour situer ses positions dans l'espace de rangs **du tournoi** au lieu de celui
    du tableau (ADR-0068 §5, résorbe `DETTE-034`).

    Sans lui, le palmarès situait les archers par l'`ordre` de leur phase — « la plus tardive
    l'emporte » — et couronnait donc le vainqueur d'une **consolante** devant le finaliste du
    tableau principal. Le défaut était inatteignable tant qu'aucun moteur ne consommait les
    prélèvements ; E05US020 l'a rendu atteignable, et la revue adversariale l'a mesuré.

    Rend **1** quand la phase ne déclare aucun prélèvement lisible en rangs : elle est alimentée par
    les inscriptions et dispute donc le tournoi entier.
    """
    effectif_source = sum(1 for ligne in classement.lignes if ligne.rang_scratch is not None)
    debuts = [
        borne[0]
        for source in phase.sources
        if source.ordre_source == ordre_qualification
        if (borne := source.intervalle(effectif_source)) is not None
    ]
    return min(debuts) if debuts else 1
