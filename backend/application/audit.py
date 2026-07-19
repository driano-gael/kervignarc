"""Service applicatif Audit (E10US005, **socle**) — consigner et consulter le journal métier.

Deux cas d'usage :

- **`consigner`** : la primitive d'écriture du journal. C'est elle que les **producteurs**
  appelleront — la validation et la correction d'un score (E04US002), le forfait (E12US004) —
  depuis leur propre commande d'écriture (dans la file, règle 7), pour laisser une trace *qui /
  quand / avant-après*. Le « quand » est lu **ici** via le port `Horloge` (jamais dans le domaine,
  qui reste pur et déterministe) : l'appelant fournit *quoi*, le service **date**. Aucune garde sur
  l'existence du tournoi : `consigner` est une primitive **interne**, invoquée par un producteur qui
  a déjà validé son contexte — y rajouter une relecture du tournoi alourdirait le chemin d'écriture
  sans rien garantir de plus (l'intégrité tient à la FK). Tant qu'E04US002/E12US004 ne sont pas
  livrées, cette méthode n'a **pas encore d'appelant** : c'est le socle, pas du code mort.

- **`lister`** : la consultation **admin** (« consultable par l'admin », CA). Garde
  `TournoiIntrouvable` pour qu'une consultation d'un tournoi inconnu réponde 404 (et non une liste
  vide trompeuse). L'ordre chronologique est garanti par le port `AuditRepository` (propriété de
  l'audit, pas un tri d'affichage).
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
