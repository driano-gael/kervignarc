"""Libellés imprimés partagés par les adapters de documents — PDF **et** tableur.

Le document du mur et celui de la presse nomment le même archer pareil (règle 3) : un seul
registre, que les deux familles d'adapters importent (revue d'E09US005, axes A, C1 et C2).
"""

from __future__ import annotations

from collections.abc import Mapping

from domain.classement import StatutClassement
from domain.contrat_phase import TypePhase

# ⚠️ Registre jumeau de `StatutClassement`, gardé par `test_tableur_palmares.py` : tout statut
# autre qu'`EN_LICE` doit y figurer, faute de quoi le tableur imprimerait la valeur brute.
LIBELLES_STATUT: Mapping[StatutClassement, str] = {
    StatutClassement.ABANDON: "Abandon",
    StatutClassement.DISQUALIFIE: "Disqualifié",
}


def libelle_statut(statut: StatutClassement) -> str:
    """Libellé imprimé du statut (ADR-0050) — vide pour un archer en lice, rien à signaler."""
    return LIBELLES_STATUT.get(statut, "")


# ⚠️ Copie de `LIBELLE_TYPE` (`frontend/src/shared/phases/catalogue.ts`), gardée égale par
# `test_pdf_deroule_horaire.py` : l'écran et le papier nomment une phase pareil (règle 3).
LIBELLES_TYPE_PHASE: Mapping[TypePhase, str] = {
    TypePhase.QUALIFICATION: "Qualification",
    TypePhase.ELIMINATION_DIRECTE: "Élimination directe",
    TypePhase.PLACEMENT: "Placement",
    TypePhase.ECHAUFFEMENT: "Échauffement",
    TypePhase.BARRAGE: "Barrage",
    TypePhase.POULES: "Poules",
    TypePhase.BIG_SHOOT_OFF: "Big Shoot Off",
    TypePhase.SUISSE: "Système suisse",
    TypePhase.COLLINE: "Colline (King of the Hill / Ladder)",
}
