"""Service d'**audit** — l'appelant fournit *quoi*, le service **date** (le domaine reste pur).

⚠️ **Deux façons de produire une entrée, et `consigner` est la MINORITAIRE** : ne pas conclure d'un
`grep consigner` que l'audit n'a qu'un producteur. Le cas général (7 chemins d'écriture sur 8) écrit
la trace **dans la même méthode de repository** que l'écriture métier — une trace ne doit ni
survivre à l'écriture qu'elle décrit, ni manquer si celle-ci passe. `consigner` seul ne sert que
lorsqu'il n'y a **aucun agrégat** à écrire (le lancement d'un tour, ADR-0056).
"""

from __future__ import annotations

from application.erreurs import TournoiIntrouvable
from domain.entree_audit import ActionAuditee, EntreeAudit
from domain.ports import AuditRepository, Horloge, TournoiRepository
from domain.tournoi import TournoiId


class ServiceAudit:
    """Cas d'usage du journal d'audit métier : consigner (primitive) et lister (consultation)."""

    def __init__(
        self,
        audit_repository: AuditRepository,
        tournoi_repository: TournoiRepository,
        horloge: Horloge,
    ) -> None:
        self._audit = audit_repository
        self._tournois = tournoi_repository
        self._horloge = horloge

    def consigner(
        self,
        tournoi_id: TournoiId,
        action: ActionAuditee,
        auteur: str,
        objet: str,
        avant: str | None = None,
        apres: str | None = None,
    ) -> EntreeAudit:
        """Enregistre une entrée d'audit, **datée** par le port `Horloge`, et la renvoie.

        Lève `AuteurAuditInvalide` / `ObjetAuditInvalide` (domaine) si l'auteur ou l'objet est vide.
        `avant`/`apres` sont facultatifs (une validation n'en a pas ; une correction, si).
        """
        entree = EntreeAudit.creer(
            tournoi_id=tournoi_id,
            action=action,
            auteur=auteur,
            horodatage=self._horloge.maintenant(),
            objet=objet,
            avant=avant,
            apres=apres,
        )
        return self._audit.consigner(entree)

    def lister(self, tournoi_id: TournoiId) -> list[EntreeAudit]:
        """Renvoie les entrées d'audit d'un tournoi, en ordre chronologique (liste possible vide).

        Lève `TournoiIntrouvable` si le tournoi n'existe pas.
        """
        self._verifier_tournoi(tournoi_id)
        return self._audit.par_tournoi(tournoi_id)

    def _verifier_tournoi(self, tournoi_id: TournoiId) -> None:
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
