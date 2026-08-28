"""Lectures **transverses** d'un tournoi, alors que la portée sportive est le départ (ADR-0075).

Ces réglages-ci sont réellement communs : ils vivent sur l'`EtapeDeroule`, définie une fois pour le
tournoi (ADR-0076), que le repository assemble sur la phase de chaque créneau.

⚠️ **Raccourcis assumés, pas la vérité du moteur** : qui a un `depart_id` sous la main doit
l'utiliser. Ce module n'est ni testé ni couvert par le garde-fou de portée — `DETTE-048`.
"""

# DETTE-022, DETTE-047 — cinq appelants de `qualification_du_tournoi`, tous triés au registre : ne
# pas en ajouter un sixième sans l'y recompter. Portés au créneau (ADR-0082) : `forfaits`,
# `feuille_de_marque`, `saisie.avancement_cible` et les deux comptages de `completude` ; replis
# assumés : `saisie._phase_qualification_ou_none` et `pilotage_simulation`.

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

    ⚠️ **Cette lecture était une approximation ; ADR-0076 la rend exacte.** Chaque départ portait
    alors sa **copie** du déroulé, libre de diverger, et `qualification_representative` en
    désignait une au hasard des tris. Le déroulé étant désormais **défini une fois**, il n'y a plus
    qu'une valeur. Ce qui reste propre au créneau — `statut` et `id` de la phase — se lit par
    `par_depart` (ADR-0075). Le tri de `par_tournoi` rend le choix **stable** d'un appel à l'autre.
    """
    for phase in phases.par_tournoi(tournoi_id):
        if phase.type is TypePhase.QUALIFICATION:
            return phase
    return None


def qualification_courante(phases: PhaseRepository, depart_id: DepartId) -> Phase | None:
    """La qualification **où l'on tire en ce moment** dans ce créneau, ou `None`.

    Depuis E05US025 (ADR-0082) un créneau peut porter plusieurs qualifications, donc « la »
    qualification n'existe plus : on rend la première **démarrée et non terminée** (`en cours` ou
    `en pause`), à défaut la première **à venir**, à défaut la dernière. ⚠️ Le repli sur « à venir
    » n'est pas de la complaisance : démarrer est un geste **manuel**, et en dépendre bloquerait le
    pas de tir tout l'après-midi s'il est oublié (même parti que `ServicePalmares._resultat`).
    """
    return la_plus_courante(
        phase for phase in phases.par_depart(depart_id) if phase.type is TypePhase.QUALIFICATION
    )


def la_plus_avancee(phases: Iterable[Phase]) -> Phase | None:
    """Celle de ces phases où un archer **qu'elles admettent toutes** tire en ce moment.

    ⚠️ **Sens inverse de `la_plus_courante` sur les phases démarrées** : la qualification de tête
    accueille tout le monde, donc « la première démarrée » la désigne toujours — les 3x15 de la
    basse s'écrivaient à la suite des 3x20 du premier tour. Sur des phases admettant le même
    archer, l'`ordre` est un ordre topologique de son parcours : la **plus avancée** des démarrées
    est la sienne ; à défaut, la première à venir.
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
    plus que son départ (ADR-0075). L'appartenance se lit par la jointure que `par_tournoi` porte
    déjà. ⚠️ **Garde d'autorisation, pas de commodité** : la remplacer par un `par_id` nu
    rouvrirait la porte qu'elle existe pour fermer — un identifiant de phase d'un *autre* tournoi.
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
