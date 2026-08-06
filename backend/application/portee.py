"""Lectures **transverses** d'un tournoi, depuis que la portée sportive est le départ (ADR-0075).

Un tournoi n'a plus de phases en propre : il en a autant de séquences que de départs. Or plusieurs
services ont besoin d'une information qui, elle, est **commune** au tournoi — combien de volées
compte une qualification, à quel grain le scoreur valide. Ces réglages viennent du **format**, qui
distribue le même déroulé à tous les départs (`FormatTournoi.appliquer`), donc les lire sur un
départ ou sur un autre revient au même tant qu'ils n'ont pas divergé.

**Pourquoi un module et non un copier-coller de plus.** Six services faisaient déjà la même
résolution « la qualification de ce tournoi » : `bareme_qualification`, `grain_validation`,
`completude` (deux fois), `feuille_de_marque`, `forfaits`, `saisie` (deux fois). C'est la
duplication que `DETTE-022` signale depuis E04US018. La règle du projet autorise un remède
structurel sur **preuve dans le code d'aujourd'hui** (3ᵉ occurrence réelle) : il y en a six,
toutes existantes, aucune supposée. La factorisation se fait donc ici et non « plus tard ».

⚠️ **Ces lectures sont des raccourcis assumés, pas la vérité du moteur.** Le moteur, lui, raisonne
toujours dans un départ (`PhaseRepository.par_depart`). Quiconque a un `depart_id` sous la main doit
l'utiliser : passer par ici perdrait justement la distinction qu'ADR-0075 rétablit.
"""

from __future__ import annotations

from domain.depart import DepartId
from domain.phase import Phase, PhaseId, TypePhase
from domain.ports import PhaseRepository
from domain.tournoi import TournoiId


def qualification_representative(phases: PhaseRepository, tournoi_id: TournoiId) -> Phase | None:
    """La qualification **d'un** départ du tournoi, ou `None` si aucun n'en porte.

    « Représentative » et non « du tournoi » : le mot dit le raccourci. Les départs reçoivent des
    copies **identiques** du déroulé du format, donc la première trouvée porte le même barème et le
    même grain que les autres — jusqu'au jour où l'organisateur en ajuste une seule depuis l'écran
    des phases. Ce jour-là, les vues transverses afficheront la valeur d'un départ pour tous : c'est
    une **approximation d'affichage**, jamais une base de calcul.

    `par_tournoi` (transverse, jointure `phase → depart → tournoi`) sert de source : les phases y
    sont triées par départ puis par ordre, donc « la première qualification » est celle du premier
    départ — un choix **stable** d'un appel à l'autre, ce qui évite qu'un écran change de valeur
    entre deux rafraîchissements.
    """
    for phase in phases.par_tournoi(tournoi_id):
        if phase.type is TypePhase.QUALIFICATION:
            return phase
    return None


def qualifications_de_chaque_depart(phases: PhaseRepository, tournoi_id: TournoiId) -> list[Phase]:
    """Toutes les qualifications du tournoi, **une par départ** qui en porte une.

    C'est la lecture des services qui **écrivent** en éventail — régler le barème « pour le
    tournoi » signifie l'écrire sur la qualification de chaque départ. Une écriture ne peut pas se
    contenter d'un représentant : elle laisserait les autres départs sur l'ancienne valeur, et la
    divergence serait invisible jusqu'au jour J.
    """
    return [
        phase for phase in phases.par_tournoi(tournoi_id) if phase.type is TypePhase.QUALIFICATION
    ]


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
