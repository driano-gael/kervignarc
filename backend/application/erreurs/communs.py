"""Erreurs **transverses** — celles qu'aucun module ne revendique seul, ou que plusieurs
thèmes lèvent. Volontairement peu nombreuses : une erreur qui atterrit ici sans raison est
le signe qu'elle mérite un thème.

Découpé de l'ancien module plat par l'action 2 de
[l'audit de maintenabilité](../../../docs/audit-maintenabilite.md) (E00US018) : 77 classes
dans un seul fichier faisaient de lui un **passage obligé** de presque chaque US.
Le contenu des classes n'a pas bougé d'un caractère."""

from __future__ import annotations

from application.erreurs.base import ApplicationError


class DepartCourantNonDefini(ApplicationError):
    """Un poste tente de saisir (ou lister ses archers) sans avoir fixé son départ courant. → 409.

    ADR-0034 §1 : tant qu'aucun départ n'est fixé, le poste connaît son lieu mais **ne sait pas qui
    afficher** — refus **explicite**, jamais un affichage vide ambigu. Conflit d'**état** (le poste
    n'est pas en état de saisir), d'où 409 : le front doit d'abord fixer le départ (« mode départ »)
    avant d'afficher la grille. Distinct de `SaisieHorsCible` (403 : le départ *est* fixé, mais
    l'archer visé n'y est pas).
    """

    code = "depart_courant_non_defini"
