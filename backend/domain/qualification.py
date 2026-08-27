"""Réglage du **découpage en tours** d'une qualification — *avancer ≠ classer* (ADR-0090, ADR-0093).
Le classement reste **toujours au total**, jamais au tour : d'où le réglage ici plutôt que sur le
barème. Ce module porte le réglage, pas la lecture du terrain.

⚠️ **Le tour d'une qualification peut RECULER** — un archer qui commence en retard fait baisser le
minimum du plateau. Ce calcul n'a aucune mémoire, et c'est `arret_programme` qui absorbe le recul.
Lisser ici ferait mentir la lecture au moment précis où elle protège le pas de tir.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.bareme import BaremeQualification
from domain.contrat_phase import TypePhase
from domain.erreurs import DecoupageEnToursInvalide

__all__ = [
    "DecoupageEnTours",
    "verifier_decoupage",
    "verifier_decoupage_applicable",
    "volees_par_tour",
]


@dataclass(frozen=True)
class DecoupageEnTours:
    """Le réglage de découpage d'une qualification : **en combien de tours**, et rien d'autre.

    L'organisateur saisit un **nombre de tours**, pas une longueur (cadrage du 20/08/2026) ; le
    moteur en déduit `volees_par_tour` et **refuse** un nombre qui ne divise pas le barème (cf.
    `verifier_decoupage`, pendant d'`EtapeDeroule._verifier_rondes_appariables` : une propriété du
    **couple** (barème, découpage) ne se juge pas sur le réglage seul). Une seule classe pour un
    seul champ, comme `ConfigurationSuisse`.
    """

    nb_tours: int = 1

    def __post_init__(self) -> None:
        if self.nb_tours < 1:
            raise DecoupageEnToursInvalide(
                f"Une qualification compte au moins un tour (reçu {self.nb_tours})."
            )


def volees_par_tour(bareme: BaremeQualification, decoupage: DecoupageEnTours | None) -> int:
    """Combien de volées dans un tour. Sans découpage, la phase **est** son tour."""
    if decoupage is None:
        return bareme.nb_volees
    return bareme.nb_volees // decoupage.nb_tours


def verifier_decoupage(
    bareme: BaremeQualification | None, decoupage: DecoupageEnTours | None
) -> None:
    """Le découpage tombe-t-il juste sur ce barème ? Lève `DecoupageEnToursInvalide` sinon.

    **Des tours égaux, ou pas de découpage** : 20 volées en 3 tours donnerait 7/7/6, et « après le
    tour 2 » ne désignerait plus le même instant selon l'archer. ⚠️ **Le message nomme le LIEU du
    geste** (`P-3`) : changer le **barème** d'une qualification découpée passe par ici, et
    l'organisateur reçoit un 422 sur un écran qui ne porte aucun réglage de tours. **Silencieux
    quand le barème manque** — on ne refuse pas ce qu'on ne peut pas juger (ADR-0063).
    """
    if decoupage is None or bareme is None:
        return
    if bareme.nb_volees % decoupage.nb_tours != 0:
        raise DecoupageEnToursInvalide(
            f"{bareme.nb_volees} volées ne se découpent pas en {decoupage.nb_tours} tours égaux. "
            "Choisissez un nombre de tours qui divise le nombre de volées, dans le bloc "
            "« Découpage en tours » de l'écran Phases."
        )


def verifier_decoupage_applicable(
    type_phase: TypePhase,
    bareme: BaremeQualification | None,
    decoupage: DecoupageEnTours | None,
) -> None:
    """Ce découpage a-t-il un sens sur **cette** phase ? — la garde des deux agrégats porteurs.

    Deux refus qui ne se recouvrent pas : un découpage sur un type non-qualification est un
    **réglage fantôme** (retyper une phase sans nettoyer son réglage laisse une valeur que rien ne
    lit), et un découpage qui ne divise pas le barème est un déroulé **inégal**. ⚠️ **Appelée par
    `EtapeDeroule` *et* par `Phase`** (ADR-0076) : n'en garder qu'un laisserait l'autre porte
    ouverte — le défaut qu'E05US033 a corrigé (`PUT` 200, puis chaque lecture en 422).
    """
    if decoupage is not None and type_phase is not TypePhase.QUALIFICATION:
        raise DecoupageEnToursInvalide(
            f"Une phase de type « {type_phase.value} » n'est pas une qualification : elle n'a pas "
            "de découpage en tours à régler."
        )
    verifier_decoupage(bareme, decoupage)
