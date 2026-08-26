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


class CorpsHorsDeProportion(ApplicationError):
    """Le corps d'une requête dépasse la coupure de sécurité de la frontière → **413**.

    ⚠️ **Ce n'est pas la règle métier.** Un logo trop lourd, c'est `LogoTropVolumineux` (domaine,
    422), qui sait dire « ce logo pèse 900 Ko, la limite est de 512 Ko ». Cette erreur-ci est la
    coupure **en amont** : elle borne ce que le serveur accepte de mettre en mémoire avant même de
    savoir de quoi il s'agit, et son message reste volontairement muet.

    Vit ici plutôt que dans un module thématique parce qu'elle ne parle d'aucun thème : elle parle
    de la frontière. Le projet n'a pas de famille `ApiError` distincte (règle 5 la nomme, le code ne
    l'a jamais matérialisée) et tous les routeurs qui lèvent lèvent des `ApplicationError` — on suit
    le précédent plutôt que d'ouvrir une taxinomie pour une classe.
    """

    code = "corps_hors_de_proportion"
