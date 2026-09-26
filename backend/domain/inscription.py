"""Agrégat **Inscription** — deux identifiants, et rien de plus.

Les invariants « même tournoi » et « unicité du couple » supposent de relire d'autres agrégats :
ils vivent au service.

⚠️ **Le montant dû ne vit PAS ici** : il se dérive du tarif du départ à la lecture — rien à
stocker, rien à resynchroniser. Seuls `paye` et `cree_le`, non dérivables, sont des attributs
propres. ADR-0017
"""

from __future__ import annotations

import datetime
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
    # `None` : inscription antérieure à E17US012 (migration `0057`), jamais datée — on ne lui
    # invente pas de date, l'ancienneté de sa dette reste « inconnue » (`domain.paiement`).
    cree_le: datetime.datetime | None = None

    @staticmethod
    def creer(
        archer_id: ArcherId, depart_id: DepartId, cree_le: datetime.datetime | None = None
    ) -> Inscription:
        """Crée une inscription **non encore payée** (`paye=False`).

        Aucune validation de bornes ici : les identifiants sont des FK dont l'existence et la
        cohérence (même tournoi) relèvent du service, pas de l'entité. ⚠️ `cree_le` a un défaut
        pour les décors de test : le seul créateur de production, `ServiceInscriptions.inscrire`,
        le renseigne — et un test l'y épingle.
        """
        return Inscription(archer_id=archer_id, depart_id=depart_id, paye=False, cree_le=cree_le)

    def marquer_paye(self, paye: bool) -> Inscription:
        """Renvoie une copie avec le statut de paiement voulu ; le reste est préservé."""
        return replace(self, paye=paye)
