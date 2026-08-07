"""Lectures **transverses** d'un tournoi, depuis que la portée sportive est le départ (ADR-0075).

Un tournoi n'a plus de phases en propre : il en a autant de séquences que de départs. Or plusieurs
services ont besoin d'une information qui, elle, est **commune** au tournoi — combien de volées
compte une qualification, à quel grain le scoreur valide.

**Et elle l'est réellement depuis [ADR-0076]** : ces réglages vivent sur l'`EtapeDeroule`, définie
**une fois** pour le tournoi, que le repository assemble sur la phase de chaque créneau. Les lire
sur un départ ou sur un autre ne « revient au même » plus par convention — c'est la *même* donnée.
La réserve « tant qu'ils n'ont pas divergé », que ce module portait, n'a plus d'objet : la
divergence n'est pas improbable, elle est impossible.

[ADR-0076]: ../../docs/adr/0076-un-deroule-defini-une-fois-un-avancement-par-depart.md

**Pourquoi un module et non un copier-coller de plus.** Six services faisaient déjà la même
résolution « la qualification de ce tournoi » : `bareme_qualification`, `grain_validation`,
`completude` (deux fois), `feuille_de_marque`, `forfaits`, `saisie` (deux fois). C'est la
duplication que `DETTE-022` signale depuis E04US018. La règle du projet autorise un remède
structurel sur **preuve dans le code d'aujourd'hui** (3ᵉ occurrence réelle) : il y en a six,
toutes existantes, aucune supposée. La factorisation se fait donc ici et non « plus tard ».

⚠️ **Ces lectures sont des raccourcis assumés, pas la vérité du moteur.** Le moteur, lui, raisonne
toujours dans un départ (`PhaseRepository.par_depart`). Quiconque a un `depart_id` sous la main doit
l'utiliser : passer par ici perdrait justement la distinction qu'ADR-0075 rétablit.

# DETTE-048 : ce module concentre la portée tournoi résiduelle, et il est le seul à n'être **ni
# testé ni surveillé**. Aucun test ne l'importe ; et le garde-fou `tests/test_portee_sportive.py` le
# manque par construction — son balayage AST reconnaît des *noms de variables* (`phase`, `barrage`),
# pas un `tournoi_id` reçu en **paramètre**, qui est justement la forme d'ici. Les deux défauts de
# portée trouvés à la 2ᵉ revue d'E01US025 en sont sortis tous les deux (DETTE-047, et les verdicts
# de barrage corrigés dans l'US). Avant d'ajouter un dixième appelant, lire le registre.
"""

from __future__ import annotations

from domain.depart import DepartId
from domain.phase import Phase, PhaseId, TypePhase
from domain.ports import PhaseRepository
from domain.tournoi import TournoiId


def qualification_du_tournoi(phases: PhaseRepository, tournoi_id: TournoiId) -> Phase | None:
    """La qualification du tournoi — telle que jouée dans un créneau —, ou `None` s'il n'y en a pas.

    ⚠️ **Cette lecture était une approximation ; ADR-0076 la rend exacte.** Elle s'appelait
    `qualification_representative`, et sa docstring devait reconnaître ne rendre « une approximation
    d'affichage, jamais une base de calcul » : chaque départ portait alors sa **copie** du déroulé,
    libre de diverger, et cette fonction en désignait une au hasard des tris. Le déroulé étant
    désormais **défini une fois** (`EtapeDeroule`), toutes les instances portent la même définition
    — l'adapter l'assemble depuis l'étape de même rang. Il n'y a plus de représentant : il n'y a
    plus qu'une valeur. Le renommage est délibéré, pour que rien ne continue de citer l'ancienne
    prudence comme si elle valait encore.

    Ce qui **reste** propre au créneau, et donc à lire par `par_depart` : le `statut` et l'`id` de
    la phase. Quiconque a un `depart_id` sous la main doit l'utiliser (ADR-0075).

    `par_tournoi` (transverse, jointure `phase → depart → tournoi`) sert de source : les phases y
    sont triées par départ puis par ordre, donc la première trouvée est celle du premier départ —
    un choix **stable** d'un appel à l'autre, ce qui évite qu'un écran change d'identifiant entre
    deux rafraîchissements.
    """
    for phase in phases.par_tournoi(tournoi_id):
        if phase.type is TypePhase.QUALIFICATION:
            return phase
    return None


def phase_du_tournoi(
    phases: PhaseRepository, tournoi_id: TournoiId, phase_id: PhaseId
) -> Phase | None:
    """La phase `phase_id` **si elle appartient à ce tournoi**, sinon `None`.

    Remplace la garde `phase.tournoi_id != tournoi_id`, devenue impossible : une phase ne connaît
    plus que son départ (ADR-0075). L'appartenance au tournoi se lit donc par la jointure
    `phase → depart → tournoi`, que `par_tournoi` porte déjà — inutile d'injecter un
    `DepartRepository` dans les six services qui font ce contrôle.

    ⚠️ **Garde d'autorisation, pas de commodité** : elle empêche qu'un identifiant de phase d'un
    *autre* tournoi soit accepté sur cette route. La remplacer par un `par_id` nu rouvrirait cette
    porte — c'est précisément ce que le contrôle existait pour fermer.
    """
    return next((phase for phase in phases.par_tournoi(tournoi_id) if phase.id == phase_id), None)


def phase_du_depart(
    phases: PhaseRepository, depart_id: DepartId, phase_id: PhaseId
) -> Phase | None:
    """La phase `phase_id` **si elle appartient à ce créneau**, sinon `None`.

    Pendant de `phase_du_tournoi`, à la maille où le moteur travaille. Garde d'autorisation, pas de
    commodité : sans elle, une phase d'un autre départ — voire d'un autre tournoi — serait acceptée
    sur la route.
    """
    return next((phase for phase in phases.par_depart(depart_id) if phase.id == phase_id), None)
