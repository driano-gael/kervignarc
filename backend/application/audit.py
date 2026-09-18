"""Service d'**audit** — l'appelant fournit *quoi*, le service **date** (le domaine reste pur).

⚠️ **Deux façons de produire une entrée, et `consigner` est la MINORITAIRE** : ne pas conclure d'un
`grep consigner` que l'audit n'a qu'un producteur. Le cas général (7 chemins d'écriture sur 8) écrit
la trace **dans la même méthode de repository** que l'écriture métier — une trace ne doit ni
survivre à l'écriture qu'elle décrit, ni manquer si celle-ci passe. `consigner` seul ne sert que
lorsqu'il n'y a **aucun agrégat** à écrire (le lancement d'un tour, ADR-0056).
"""

from __future__ import annotations

from typing import Protocol

from application.erreurs import TournoiIntrouvable
from application.exports import FormatExport, RegistreDeFormats
from domain.entree_audit import ActionAuditee, EntreeAudit, JournalAudit
from domain.ports import AuditRepository, GenerateurJournalAudit, Horloge, TournoiRepository
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


class LecteurJournalAudit(Protocol):
    """Port étroit : **lire** le journal d'un tournoi (réalisé par `ServiceAudit`).

    Même discipline de ségrégation d'interface que `LecteurRecapClub`
    (`application.listes_impression`) : l'export ne dépend pas de tout `ServiceAudit` — surtout pas
    de `consigner` —, juste de la consultation. Un faux lecteur suffit donc en test, et le service
    d'export ne peut structurellement **rien écrire** dans le journal qu'il rend.
    """

    def lister(self, tournoi_id: TournoiId) -> list[EntreeAudit]:
        """Entrées du tournoi, chronologiques ; lève `TournoiIntrouvable` s'il n'existe pas."""
        ...


class ServiceExportAudit:
    """Cas d'usage : sortir le journal d'audit en document téléchargeable (E16US016).

    ⚠️ **Séparé de `ServiceAudit` à dessein** : celui-ci est le socle d'**écriture** de la trace,
    appelé par huit chemins de production. Lui injecter un registre de formats de fichier ferait
    dépendre l'écriture d'une trace de l'outillage d'exploitation qui la relit.
    """

    def __init__(
        self,
        journal: LecteurJournalAudit,
        tournois: TournoiRepository,
        generateurs: RegistreDeFormats[GenerateurJournalAudit],
    ) -> None:
        self._journal = journal
        self._tournois = tournois
        self._generateurs = generateurs

    @property
    def formats_disponibles(self) -> tuple[FormatExport, ...]:
        """Formats que ce service sait produire — ce que le catalogue publie (ADR-0101 §3)."""
        return self._generateurs.formats

    def exporter(self, tournoi_id: TournoiId, format_: FormatExport = FormatExport.CSV) -> bytes:
        """Rend le journal d'audit du tournoi dans le format demandé.

        Lève `TournoiIntrouvable` (via le lecteur) si le tournoi n'existe pas,
        `FormatExportIndisponible` si le format n'est pas câblé pour ce document.
        ⚠️ Le défaut est le **CSV** et non le PDF, contrairement aux autres exports : ce document
        n'a pas de rendu PDF (`GenerateurJournalAudit`), un défaut aligné lèverait donc à vide.
        """
        entrees = self._journal.lister(tournoi_id)
        tournoi = self._tournois.par_id(tournoi_id)
        assert tournoi is not None, "Le lecteur a déjà validé l'existence du tournoi."
        document = JournalAudit(tournoi=tournoi.nom, entrees=tuple(entrees))
        return self._generateurs.pour(format_).journal(document)
