"""Qui entre dans une phase — **une seule règle, appelée par les deux services** (ADR-0068).

`ServiceSaisieDuels` (l'arbre) et `ServicePlacementDuels` (le plan) doivent ensemencer exactement la
même population : un écart, c'est un archer posté sans duel et un autre face au mauvais adversaire.

⚠️ **La règle a déjà lâché une fois recopiée** : mesuré en revue, plan de 8 placements pour un
tableau de 4. Aucune abstraction ici — une fonction pure, appelée deux fois.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from application.erreurs.moteur import PrelevementEnAttente
from domain.classement import Classement, LigneClassement, StatutClassement
from domain.classement_de_tableau import ClassementSource
from domain.depart import DepartId
from domain.phase import NatureSource, Phase, PhaseId, profondeur_par_defaut
from domain.politiques import Depth, RegistrePolitiques, assembler_politiques
from domain.tournoi import TournoiId


def profondeur_de(phase: Phase, registre: RegistrePolitiques) -> Depth:
    """Jusqu'où cette phase départage — la politique `depth` **résolue** (E06US006, ADR-0070).

    Extraite ici comme `preleves` : les deux services montent le même arbre et ne peuvent pas lui
    donner deux profondeurs. ⚠️ **La divergence n'est pas observable aujourd'hui** — sous
    `PlacementEnCascade` le premier tour est identique à toute profondeur, et
    `test_le_plan_de_cibles_reste_le_meme_a_toute_profondeur` fige cet état. Sans réglage, on
    retombe sur le **preset du type** ; la résolution passe par le **registre** (règle 2).
    """
    choix = phase.profondeur if phase.profondeur is not None else profondeur_par_defaut(phase.type)
    depth = assembler_politiques({"depth": choix.en_config()}, registre).depth
    if depth is None:
        # Inatteignable : `assembler_politiques` lève déjà `PolitiqueInconnue` sur un nom absent du
        # catalogue. ⚠️ **`RuntimeError` et non une erreur typée de couche** (corrigé en revue, axe
        # A) : une `DomainError` serait mappée en **422**, reprochant au client une faute métier
        # alors que la panne réelle est un **catalogue incomplet au composition root**. Cette
        # branche doit tomber dans `_sur_erreur_inattendue` (500).
        raise RuntimeError(
            f"Profondeur « {choix.nom.value} » absente du registre : catalogue mal peuplé."
        )
    return depth


ResolveurClassement = Callable[[int], ClassementSource | None]
"""Rend le classement produit par la phase de cet `ordre`, ou `None` si elle n'en produit aucun.

Un **résolveur** et non une table toute faite : résoudre un tableau amont coûte une reconstruction
complète (`DETTE-031`), qu'on ne paie donc que pour les ordres réellement déclarés en source. Rend
un `ClassementSource` et non un `Classement` nu — l'appelant a besoin des **plages encore
indécises** (ADR-0081) et du **rang de tournoi** du premier rang, pour que le décalage se cumule.
"""


class LecteurPopulationPhase(Protocol):
    """Port étroit : « quels archers cette phase a-t-elle reçus ? » (`ServiceSaisieDuels`).

    Deux services de qualification (saisie, complétude) doivent discriminer la population d'une
    phase : sur la fourche *haute*/*basse*, « la qualification du créneau » n'existe plus, et
    chacun la devinant de son côté retomberait dans `DETTE-034`. **Un port étroit plutôt que le
    service concret**, même parti que `LecteurPaiements` — cela évite aussi que
    `application/saisie.py` importe `application/saisie_duels.py`.
    """

    def resolveur_de_classement(
        self, tournoi_id: TournoiId, depart_id: DepartId
    ) -> ResolveurClassement:
        """De quoi lire le classement **produit** par n'importe quelle phase amont de ce créneau."""
        ...


class LecteurClassementDePhase(Protocol):
    """Port étroit : « quel classement **cette phase** a-t-elle produit ? » (ADR-0084).

    Réalisé par les services de format, consommé par `ServiceSaisieDuels` : le moteur ne connaît
    que **la question**, le composition root dit qui y répond, par type. Un import mutuel serait un
    **cycle de modules** ; le port le casse, au prix d'un branchement **tardif et visible** au
    composition root (`brancher_lecteur`). ⚠️ **Le résolveur vient de l'appelant** : il porte le
    cache (`DETTE-031`) et la détection de cycle (sinon 500 muet).
    """

    def classement_de_phase(
        self, tournoi_id: TournoiId, phase_id: PhaseId, resolveur: ResolveurClassement
    ) -> ClassementSource:
        """Le classement de la phase `phase_id`, prêt à être prélevé."""
        ...


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

    C'est ici que le moteur cesse d'ignorer `phase.sources` (`DETTE-028`) : un prélèvement garde
    les archers dont le rang tombe dans son intervalle, **au classement de la phase qu'il désigne**
    (E05US024). ⚠️ `le_reste` et `par_issue_de_tour` restent **inertes** (`DETTE-033`). ⚠️ Une
    fenêtre coupant un bloc indécis lève `PrelevementEnAttente` (ADR-0081) au lieu d'une population
    fausse mais bien formée. Sans source lisible : le `classement` reçu, dans l'ordre.
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

    Une phase prélevant « les rangs 5 et suivants » ne joue pas pour la victoire : son vainqueur
    est 5ᵉ. Le palmarès a besoin de ce décalage pour situer ses positions dans l'espace de rangs
    **du tournoi** (ADR-0068 §5, résorbe `DETTE-034`) — sans lui il couronnait le vainqueur d'une
    consolante. ⚠️ **Le décalage se cumule** : `classement_de_tableau` numérote 1..N dans l'espace
    **local**, d'où `rang_premier - 1 + rang_debut`.
    """
    debuts = [
        source_resolue.rang_premier - 1 + borne[0]
        for source in phase.sources
        if source.nature is NatureSource.RANGS
        if (source_resolue := resoudre_source(source.ordre_source)) is not None
        if (borne := source.intervalle(_effectif(source_resolue.classement))) is not None
    ]
    return min(debuts) if debuts else 1
