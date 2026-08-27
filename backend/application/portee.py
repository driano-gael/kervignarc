"""Lectures **transverses** d'un tournoi, alors que la portée sportive est le départ (ADR-0075).

Ces réglages-ci sont réellement communs : ils vivent sur l'`EtapeDeroule`, définie une fois pour le
tournoi (ADR-0076), que le repository assemble sur la phase de chaque créneau.

⚠️ **Raccourcis assumés, pas la vérité du moteur** : qui a un `depart_id` sous la main doit
l'utiliser. Ce module n'est ni testé ni couvert par le garde-fou de portée — `DETTE-048`.
"""

from __future__ import annotations

from collections.abc import Iterable

from domain.depart import DepartId
from domain.phase import Phase, PhaseId, StatutPhase, TypePhase
from domain.ports import PhaseRepository
from domain.tournoi import TournoiId

_STATUTS_EN_COURS = frozenset({StatutPhase.EN_COURS, StatutPhase.EN_PAUSE})
"""Les statuts d'une phase **démarrée mais pas finie** — celle où l'on tire en ce moment."""


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


def qualification_courante(phases: PhaseRepository, depart_id: DepartId) -> Phase | None:
    """La qualification **où l'on tire en ce moment** dans ce créneau, ou `None` s'il n'y en a pas.

    Depuis E05US025 (ADR-0082) un créneau peut porter plusieurs qualifications — 3x20, puis une
    *haute* et une *basse* à 3x15. « La » qualification n'existe donc plus ; ce qui existe, c'est
    celle qui se tire maintenant. Trois cas, par ordre croissant :

    1. la première **démarrée et non terminée** (`en cours` ou `en pause` — une pause suspend le
    tir,
       elle ne rend pas la feuille à une autre phase) ;
    2. à défaut, la première **à venir** ;
    3. à défaut, la dernière (tout est terminé — on parle encore de la plus récente).

    Le repli sur « à venir » n'est pas de la complaisance. Démarrer une phase est un geste
    **manuel**
    de l'organisateur (`ServicePhases.demarrer`) : faire dépendre la saisie et la complétude de sa
    discipline bloquerait le pas de tir tout l'après-midi s'il l'oublie. C'est le même parti que
    `ServicePalmares._resultat`, qui refuse déjà de lire `phase.statut` pour décider d'un affichage.

    ⚠️ **Contrairement au reste de ce module, ce n'est pas un raccourci de portée** : la fonction
    travaille bien à la maille du créneau (`par_depart`), là où le moteur raisonne. Elle vit ici
    parce que trois services la réclamaient — `ServiceSaisie` et `ServiceCompletude` (deux fois) —,
    ce qui est la 3ᵉ occurrence que la règle du projet exige avant de factoriser, et parce que
    `DETTE-022` recense précisément cette famille de duplications.
    """
    return la_plus_courante(
        phase for phase in phases.par_depart(depart_id) if phase.type is TypePhase.QUALIFICATION
    )


def la_plus_avancee(phases: Iterable[Phase]) -> Phase | None:
    """Celle de ces phases où un archer **qu'elles admettent toutes** tire en ce moment.

    ⚠️ **Sens inverse de `la_plus_courante` sur les phases démarrées, et c'est tout l'objet de cette
    fonction** (2ᵉ correctif de revue E05US025). Un archer de la *haute* est admis par sa phase
    **et** par la qualification de tête, qui accueille tout le monde par construction : sur cet
    ensemble-là, « la première démarrée » désigne toujours la tête. L'organisateur qui lance la
    fourche sans avoir marqué le premier tour « terminé » — geste manuel, et rien ne l'exige —
    voyait donc les 3x15 de la basse s'écrire à la suite des 3x20 dans la feuille du premier tour.
    Le bloquant précédent, déplacé d'un cran.

    Sur un ensemble de phases **qui admettent toutes le même archer**, l'`ordre` est un ordre
    topologique de son propre parcours : la plus avancée des phases démarrées est celle où il tire.
    À défaut de phase démarrée, la **première à venir** est la prochaine qu'il tirera ; à défaut, la
    dernière (tout est terminé).

    Ne pas confondre avec `la_plus_courante`, qui répond à une autre question — « que se tire-t-il
    dans ce créneau ? », pour un affichage — et sur un ensemble non filtré par archer.
    """
    triees = sorted(phases, key=lambda phase: phase.ordre)
    if not triees:
        return None
    demarrees = [p for p in triees if p.statut in _STATUTS_EN_COURS]
    if demarrees:
        return demarrees[-1]
    a_venir = [p for p in triees if p.statut is StatutPhase.A_VENIR]
    return a_venir[0] if a_venir else triees[-1]


def la_plus_courante(phases: Iterable[Phase]) -> Phase | None:
    """Celle de ces phases où l'on tire **en ce moment** (priorité de statut), ou `None` si aucune.

    Extraite de `qualification_courante` (correctif de revue E05US025) parce qu'un second appelant
    l'a réclamée : `ServiceSaisie` doit appliquer la **même** priorité, mais après avoir filtré les
    qualifications sur celle qui **admet** l'archer — sur la fourche *haute*/*basse*, « la première
    démarrée du créneau » n'est pas la sienne. Recopier la priorité aurait laissé les deux dériver.
    """
    qualifications = sorted(phases, key=lambda phase: phase.ordre)
    if not qualifications:
        return None
    demarrees = [p for p in qualifications if p.statut in _STATUTS_EN_COURS]
    if demarrees:
        return demarrees[0]
    a_venir = [p for p in qualifications if p.statut is StatutPhase.A_VENIR]
    return a_venir[0] if a_venir else qualifications[-1]


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
