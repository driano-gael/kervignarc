"""Service applicatif Audit (E10US005, **socle**) — consigner et consulter le journal métier.

Deux cas d'usage :

- **`consigner`** : la primitive d'écriture du journal, pour un producteur qui écrit sa trace
  **séparément** de son agrégat. Le « quand » est lu **ici** via le port `Horloge` (jamais dans le
  domaine, qui reste pur et déterministe) : l'appelant fournit *quoi*, le service **date**. Aucune
  garde sur l'existence du tournoi : `consigner` est une primitive **interne**, invoquée par un
  producteur qui a déjà validé son contexte — y rajouter une relecture du tournoi alourdirait le
  chemin d'écriture sans rien garantir de plus (l'intégrité tient à la FK).

  ⚠️ **Il y a deux façons de produire une entrée d'audit dans ce projet, et `consigner` est la
  minoritaire.** Ne pas conclure d'un `grep consigner` que l'audit n'a qu'un producteur :

  1. **Trace atomique avec l'agrégat** — le cas **général** : **7 des 8 chemins d'écriture**.
     ⚠️ L'unité est le *chemin d'écriture*, pas l'action : `ActionAuditee` n'a que **7** membres,
     le forfait en consommant deux (`declarer` et `annuler`). Compter l'enum donne 6/7, pas 7/8 —
     les deux comptes décrivent la même réalité. Le service
     construit l'`EntreeAudit` lui-même et la passe au repository dans **la même** méthode que son
     écriture métier : `declarer_avec_trace` / `annuler_avec_trace` (`application/forfaits.py`),
     et de même pour `PAIEMENT`, `REPLACEMENT`, `REMBOURSEMENT`, `VALIDATION`, `CORRECTION_SCORE`.
     La raison est un invariant, pas une commodité : **une trace ne doit pas survivre à l'écriture
     qu'elle décrit** si celle-ci est annulée, ni manquer si celle-ci passe. Deux appels successifs
     dans la file ne le garantissent pas ; une seule méthode de repository, si.
  2. **`consigner` seul** — quand il n'y a **pas d'agrégat à écrire**. Un seul cas aujourd'hui :
     `ActionAuditee.LANCEMENT` (`application/pilotage_tour.py`, E12US002 / ADR-0056) — lancer un
     tour ne pose **aucun statut** (le tableau est reconstruit, ADR-0049), donc la trace *est* le
     seul écrit. C'est ce qui rend la primitive nécessaire malgré son unique appelant.

  *(Réécrit le 08/08/2026. La version précédente affirmait que `consigner` n'avait « pas encore
  d'appelant » et attendait E04US002 et E12US004 : E04US002 est livrée depuis le 30/07, E12US004
  est **absorbée par E04US015** (27/07, ADR-0050) et n'arrivera jamais, et la méthode **a** un
  appelant. Trois affirmations fausses dans un paragraphe qui sert de porte d'entrée au module.)*

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
