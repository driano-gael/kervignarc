"""Entité de domaine `Inscription` — le lien archer ↔ départ (E02US009, ADR-0017).

Une inscription rattache un **archer** à un **départ** (créneau) du tournoi, et porte le seul fait
qui lui soit propre : `paye`. C'est un **agrégat mince** — presque toute la règle métier vit dans le
service (`application.inscriptions`), qui seul voit les deux côtés du lien :

- l'invariant « archer et départ du **même tournoi** » suppose de relire l'archer et le départ —
  l'entité ne porte que deux identifiants, elle ne peut pas le vérifier seule ;
- l'unicité du couple `(archer, départ)` est un fait d'**ensemble** (y a-t-il déjà cette
  inscription ?), donc un contrôle de service + une contrainte `UNIQUE` en base.

Le **montant dû** ne vit pas ici : il se **dérive** du `tarif_centimes` du départ à la lecture
(rien à stocker, rien à resynchroniser). Seul `paye`, non dérivable, est un attribut propre.

Pur et synchrone (règle 1) : aucun import de framework ni d'autre couche.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from domain.archer import ArcherId
from domain.depart import DepartId

InscriptionId = int


@dataclass(frozen=True)
class Inscription:
    """Inscription d'un archer sur un départ (créneau). Immuable (règle 4).

    `id` est `None` tant que l'inscription n'est pas persistée ; l'adapter le renseigne. Les deux
    clés `archer_id` / `depart_id` sont **fixes** une fois créées (on n'« édite » pas le couple : on
    désinscrit et on réinscrit) ; seul `paye` évolue, via `marquer_paye`.
    """

    archer_id: ArcherId
    depart_id: DepartId
    paye: bool = False
    id: InscriptionId | None = None

    @staticmethod
    def creer(archer_id: ArcherId, depart_id: DepartId) -> Inscription:
        """Crée une inscription **non encore payée** (`paye=False`).

        Aucune validation de bornes ici : les identifiants sont des FK dont l'existence et la
        cohérence (même tournoi) relèvent du service, pas de l'entité.
        """
        return Inscription(archer_id=archer_id, depart_id=depart_id, paye=False)

    def marquer_paye(self, paye: bool) -> Inscription:
        """Renvoie une copie avec le statut de paiement voulu ; le reste est préservé."""
        return replace(self, paye=paye)
