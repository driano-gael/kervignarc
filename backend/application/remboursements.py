"""Service des **remboursements** — on consulte et on clôt ; l'inscription est créée ailleurs.

⚠️ **Marquer remboursé ou reporté est un MOUVEMENT D'ARGENT**, donc audité, et l'atomicité
acte↔trace est réalisée par l'adapter (ADR-0035) : jamais un poste clos sans trace. Un
remboursement déjà traité ne se re-traite pas (409) — la garde vit **ici**, pas dans l'entité :
c'est l'intention « clore ce poste » qui est refusée.
"""

from __future__ import annotations

from application.erreurs import (
    RemboursementDejaTraite,
    RemboursementIntrouvable,
    TournoiIntrouvable,
)
from domain.entree_audit import ActionAuditee, EntreeAudit
from domain.ports import Horloge, RemboursementRepository, TournoiRepository
from domain.remboursement import Remboursement, RemboursementId, StatutRemboursement
from domain.tournoi import TournoiId

# DETTE-017 : 3ᵉ site de cette constante (paiements, placement, remboursements).
_AUTEUR_ADMIN = "Administrateur"
"""Auteur des entrées d'audit de remboursement — l'admin agit sous une identité unique.

**3ᵉ site** de cette même constante (après `application.paiements` et `application.placement`) : le
seuil « factoriser au 3ᵉ cas » est atteint (**DETTE-017**), mais l'extraction d'une constante
partagée est un **remède structurel** — proposé en ADR/US dédiée, jamais en douce dans l'US courante
(CLAUDE.md § Dette). ADR-0057 le consigne comme suite à traiter ; on garde ici la duplication locale
assumée.
"""

_STATUTS_TRAITES = {
    StatutRemboursement.REMBOURSE: "remboursé",
    StatutRemboursement.REPORTE: "reporté",
}
"""Libellé humain des statuts terminaux, pour le champ `apres` de la trace d'audit."""


class ServiceRemboursements:
    """Cas d'usage du registre de remboursements : lister, marquer remboursé, marquer reporté."""

    def __init__(
        self,
        remboursement_repository: RemboursementRepository,
        tournoi_repository: TournoiRepository,
        horloge: Horloge,
    ) -> None:
        self._remboursements = remboursement_repository
        self._tournois = tournoi_repository
        self._horloge = horloge

    def lister(self, tournoi_id: TournoiId) -> list[Remboursement]:
        """Renvoie les remboursements d'un tournoi, **à traiter d'abord**, puis les plus récents.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas — consulter un tournoi inconnu répond
        404, pas une liste vide trompeuse. Tri d'affichage : les `à_rembourser` remontent (c'est le
        travail restant), puis par date de création **décroissante** (le plus récent en tête).
        L'`id`
        départage à date égale, ordre stable.
        """
        self._tournoi_existant(tournoi_id)
        remboursements = self._remboursements.par_tournoi(tournoi_id)
        # Clé de tri : `à_rembourser` d'abord (False < True), puis le plus **récent** en tête. La
        # date (UTC *aware*) se nie via `timestamp()` (float négatable) — `sorted` ne sait pas
        # soustraire des `datetime` ; `id` décroissant départage à date égale (ordre stable).
        return sorted(
            remboursements,
            key=lambda r: (
                r.statut is not StatutRemboursement.A_REMBOURSER,
                -r.cree_le.timestamp(),
                -(r.id or 0),
            ),
        )

    def marquer_rembourse(
        self, tournoi_id: TournoiId, remboursement_id: RemboursementId
    ) -> Remboursement:
        """Marque un remboursement **remboursé** (l'argent a été rendu) ; consigne l'audit.

        Lève `RemboursementIntrouvable` (404) si l'`id` est inconnu **ou n'est pas de ce tournoi**,
        `RemboursementDejaTraite` (409) s'il est déjà remboursé ou reporté (terminal). Datée par le
        port `Horloge`.
        """
        return self._traiter(tournoi_id, remboursement_id, StatutRemboursement.REMBOURSE)

    def marquer_reporte(
        self, tournoi_id: TournoiId, remboursement_id: RemboursementId
    ) -> Remboursement:
        """Marque un remboursement **reporté** (réaffecté à un autre créneau) ; consigne l'audit.

        « Reporté » consigne une **intention** — E08US005 ne ré-inscrit pas automatiquement l'archer
        (hors périmètre). Mêmes erreurs que `marquer_rembourse`.
        """
        return self._traiter(tournoi_id, remboursement_id, StatutRemboursement.REPORTE)

    # --- Helpers -----------------------------------------------------------------------------

    def _traiter(
        self,
        tournoi_id: TournoiId,
        remboursement_id: RemboursementId,
        cible: StatutRemboursement,
    ) -> Remboursement:
        """Applique une transition terminale (remboursé/reporté) et co-écrit sa trace.

        Garde de **terminalité** ici (le service) : on ne clôt que ce qui est encore
        `à_rembourser`. ⚠️ Le poste est **borné au tournoi** de l'URL — un `id` d'un autre tournoi
        est *introuvable* de son point de vue : on ne traite pas le poste d'un voisin par une URL
        mal formée. L'entité applique la transformation ; l'adapter scelle statut + trace en une
        transaction.
        """
        remboursement = self._remboursements.par_id(remboursement_id)
        if remboursement is None or remboursement.tournoi_id != tournoi_id:
            raise RemboursementIntrouvable(
                f"Aucun remboursement {remboursement_id} dans le tournoi {tournoi_id}."
            )
        if remboursement.statut is not StatutRemboursement.A_REMBOURSER:
            raise RemboursementDejaTraite(
                f"Le remboursement {remboursement_id} est déjà "
                f"{_STATUTS_TRAITES[remboursement.statut]} : il ne peut plus être traité."
            )
        instant = self._horloge.maintenant()
        maj = (
            remboursement.marquer_rembourse(instant)
            if cible is StatutRemboursement.REMBOURSE
            else remboursement.marquer_reporte(instant)
        )
        entree = EntreeAudit.creer(
            tournoi_id=remboursement.tournoi_id,
            action=ActionAuditee.REMBOURSEMENT,
            auteur=_AUTEUR_ADMIN,
            horodatage=instant,
            objet=(
                f"Remboursement — {remboursement.archer_prenom} {remboursement.archer_nom}, "
                f"{remboursement.creneau} ({_euros(remboursement.montant_centimes)})"
            ),
            avant="à rembourser",
            apres=_STATUTS_TRAITES[cible],
        )
        return self._remboursements.enregistrer_avec_trace(maj, entree)

    def _tournoi_existant(self, tournoi_id: TournoiId) -> None:
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")


def _euros(centimes: int) -> str:
    """Formate un montant en centimes pour la trace d'audit (« 8,10 € »)."""
    return f"{centimes / 100:.2f} €".replace(".", ",")
