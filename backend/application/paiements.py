"""Service applicatif Paiements — suivre et marquer les règlements (E08US002).

Le **suivi** des paiements est trois facettes d'une même capacité (maille révisée du 17/07/2026,
`stories/E08-paiements.md`) : **marquer** un statut de paiement (simple ou groupé), le **consulter
par archer** (dû / payé / reste) et **par club** (mêmes totaux agrégés, détail des archers). Le fait
brut vit ailleurs — le booléen `paye` d'une `Inscription` (par créneau) ; ici on l'**agrège** (règle
de calcul dans `domain.paiement`) et on le **fait basculer**.

Deux arbitrages de l'US, reversés dans le CA (`stories/`, § Notes) :

- **Règlements groupés** (but de l'US) : on peut marquer d'un geste **tout un archer** ou **tout un
  club** — pas seulement inscription par inscription. Le marquage simple d'E02US009 **migre ici**
  (`marquer_inscription`) : une **seule** voie d'écriture du paiement, donc **toute auditée**, et
  non un chemin tracé et un autre non.
- **Audit** : un paiement est un **mouvement d'argent**, donc tracé (E10US005). Chaque marquage —
  simple ou groupé — consigne **une** entrée `PAIEMENT`. L'atomicité acte↔trace est réalisée par
  l'adapter (`InscriptionRepository.definir_paye_avec_trace`, co-écriture en une transaction,
  ADR-0035, comme la validation d'une série) : jamais un paiement basculé sans trace, ni de trace
  fantôme. Le service **date** l'entrée (port `Horloge`) ; le domaine reste pur.

Les vues sont des **lectures pures** (hors file d'écriture) ; les marquages sont des **écritures**
routées par la file (writer unique, règle 7 — assuré côté API).
"""

from __future__ import annotations

from dataclasses import dataclass

from application.erreurs import (
    ArcherIntrouvable,
    ClubIntrouvable,
    InscriptionIntrouvable,
    TournoiIntrouvable,
)
from application.inscriptions import InscriptionDetaillee
from domain.archer import Archer, ArcherId
from domain.club import ClubId
from domain.depart import DepartId
from domain.entree_audit import ActionAuditee, EntreeAudit
from domain.paiement import RecapPaiement, recapituler, total
from domain.ports import (
    ArcherRepository,
    ClubRepository,
    DepartRepository,
    Horloge,
    InscriptionRepository,
    TournoiRepository,
)
from domain.tournoi import TournoiId

_AUTEUR_ADMIN = "Administrateur"
"""Auteur des entrées d'audit de paiement — l'admin agit sous une identité unique (pas un nom).

Même valeur que la trace de régénération massive du plan (`application.placement`) : les deux sont
des actes de l'**administrateur**. Deuxième occurrence assumée (règle « dupliquer une 2ᵉ fois, ne
factoriser qu'au 3ᵉ cas ») — pas de constante partagée tant qu'un 3ᵉ producteur admin n'existe pas.
"""

LIBELLE_SANS_CLUB = "Sans club"
"""Libellé du regroupement des archers **sans club** (`club_id` `NULL`, ADR-0014).

Le club est un rattachement **facultatif** (`NULL` = inconnu, sans ligne sentinelle — ADR-0014). La
vue par club regroupe donc les archers non rattachés sous un bucket **virtuel** (pas un club réel) :
il n'a pas d'`id`, ne peut pas être marqué en lot par `marquer_club` (qui exige un club existant),
mais ses totaux comptent — sans quoi la somme des clubs ne retomberait pas sur le total du tournoi.
"""


@dataclass(frozen=True)
class LignePaiementArcher:
    """Vue de lecture : un archer et son récapitulatif de paiement (dû / payé / reste).

    Porte le `club_id` (éventuellement `None`) pour permettre le regroupement par club sans une
    seconde lecture. Le nom du club, lui, est résolu au niveau de la vue par club.
    """

    archer_id: ArcherId
    nom: str
    prenom: str
    club_id: ClubId | None
    recap: RecapPaiement


@dataclass(frozen=True)
class RecapClub:
    """Vue de lecture : un club, son total de paiement et le détail de ses archers (vue par club).

    `club_id is None` désigne le bucket **virtuel** des archers sans club (`LIBELLE_SANS_CLUB`) : il
    agrège des totaux mais ne correspond à aucun club réel (ADR-0014).
    """

    club_id: ClubId | None
    nom: str
    recap: RecapPaiement
    archers: list[LignePaiementArcher]


class ServicePaiements:
    """Cas d'usage du suivi des paiements : consulter (par archer, par club) et marquer (simple,
    par archer, par club — tout audité)."""

    def __init__(
        self,
        tournoi_repository: TournoiRepository,
        archer_repository: ArcherRepository,
        depart_repository: DepartRepository,
        inscription_repository: InscriptionRepository,
        club_repository: ClubRepository,
        horloge: Horloge,
    ) -> None:
        self._tournois = tournoi_repository
        self._archers = archer_repository
        self._departs = depart_repository
        self._inscriptions = inscription_repository
        self._clubs = club_repository
        self._horloge = horloge

    # --- Lectures (vues) ---------------------------------------------------------------------

    def lister_par_archer(self, tournoi_id: TournoiId) -> list[LignePaiementArcher]:
        """Récapitulatif de paiement de **chaque** archer du tournoi (CA « vue par archer »).

        Un archer sans inscription figure quand même (dû 0) — il fait partie du tournoi. Trié par
        nom puis prénom (casse repliée), ordre d'affichage stable. Lève `TournoiIntrouvable` si le
        tournoi n'existe pas — une consultation d'un tournoi inconnu répond 404, pas une liste vide
        trompeuse. « Filtrable » (CA) est une affordance d'écran : la liste complète est renvoyée,
        le front filtre (quelques dizaines de lignes).
        """
        self._tournoi_existant(tournoi_id)
        tarifs = self._tarifs(tournoi_id)
        lignes = [self._ligne(archer, tarifs) for archer in self._archers.par_tournoi(tournoi_id)]
        return sorted(lignes, key=lambda ligne: (ligne.nom.casefold(), ligne.prenom.casefold()))

    def recap_par_club(self, tournoi_id: TournoiId) -> list[RecapClub]:
        """Totaux de paiement **par club**, avec le détail des archers (CA « vue par club »).

        Les archers sans club (`club_id` `NULL`, ADR-0014) forment un bucket `LIBELLE_SANS_CLUB`
        placé **en dernier**. Les clubs réels sont triés par nom (casse repliée). Lève
        `TournoiIntrouvable` si le tournoi n'existe pas.
        """
        lignes = self.lister_par_archer(tournoi_id)
        noms_clubs = {club.id: club.nom for club in self._clubs.lister()}
        groupes: dict[ClubId | None, list[LignePaiementArcher]] = {}
        for ligne in lignes:
            groupes.setdefault(ligne.club_id, []).append(ligne)
        recaps = [
            RecapClub(
                club_id=club_id,
                nom=(
                    LIBELLE_SANS_CLUB
                    if club_id is None
                    else noms_clubs.get(club_id, LIBELLE_SANS_CLUB)
                ),
                recap=total(ligne.recap for ligne in archers),
                archers=archers,
            )
            for club_id, archers in groupes.items()
        ]
        # Les clubs réels par nom ; le bucket « sans club » (club_id None) toujours en dernier.
        return sorted(recaps, key=lambda r: (r.club_id is None, r.nom.casefold()))

    # --- Écritures (marquages, audités) ------------------------------------------------------

    def marquer_inscription(self, inscription_id: int, paye: bool) -> InscriptionDetaillee:
        """Bascule le statut d'**une** inscription (CA « statut modifiable ») ; consigne l'audit.

        Lève `InscriptionIntrouvable` si l'inscription n'existe pas (ou si son créneau a disparu,
        vestige d'un instantané périmé qui n'est plus marquable). L'entrée d'audit garde le statut
        **avant** et **après** (valeur de preuve).
        """
        inscription = self._inscriptions.par_id(inscription_id)
        if inscription is None:
            raise InscriptionIntrouvable(f"Aucune inscription d'identifiant {inscription_id}.")
        assert inscription.id is not None, "Une inscription relue est persistée."
        archer = self._archer_existant(inscription.archer_id)
        depart = self._departs.par_id(inscription.depart_id)
        if depart is None:
            raise InscriptionIntrouvable(
                f"Le créneau de l'inscription {inscription_id} n'existe plus."
            )
        entree = self._trace(
            archer.tournoi_id,
            objet=f"Paiement — {archer.prenom} {archer.nom}, départ n°{depart.numero}",
            paye=paye,
            avant=_statut(inscription.paye),
        )
        (maj,) = self._inscriptions.definir_paye_avec_trace([inscription.id], paye, entree)
        return InscriptionDetaillee(maj, depart)

    def marquer_archer(
        self, tournoi_id: TournoiId, archer_id: ArcherId, paye: bool
    ) -> LignePaiementArcher:
        """Marque **toutes** les inscriptions d'un archer en un geste (règlement groupé) ; audite.

        Lève `ArcherIntrouvable` si l'archer n'existe pas ou n'est pas du tournoi. Sans inscription,
        c'est un no-op **sans trace** (rien n'a bougé). Renvoie le récapitulatif rafraîchi.
        """
        self._tournoi_existant(tournoi_id)
        archer = self._archer_du_tournoi(tournoi_id, archer_id)
        assert archer.id is not None, "Un archer relu est persisté."
        inscriptions = self._inscriptions.par_archer(archer.id)
        ids = [i.id for i in inscriptions if i.id is not None]
        if ids:
            entree = self._trace(
                tournoi_id,
                objet=f"Paiement groupé — {archer.prenom} {archer.nom} "
                f"({len(ids)} inscription(s))",
                paye=paye,
            )
            self._inscriptions.definir_paye_avec_trace(ids, paye, entree)
        return self._ligne(archer, self._tarifs(tournoi_id))

    def marquer_club(self, tournoi_id: TournoiId, club_id: ClubId, paye: bool) -> RecapClub:
        """Marque **toutes** les inscriptions des archers d'un club (de ce tournoi) ; audite.

        Lève `ClubIntrouvable` si le club n'existe pas. Le périmètre est **borné au tournoi** (le
        référentiel des clubs est global, mais on ne marque que les archers *ici présents*). Sans
        inscription, no-op sans trace. Renvoie le récapitulatif rafraîchi du club.
        """
        self._tournoi_existant(tournoi_id)
        club = self._clubs.par_id(club_id)
        if club is None:
            raise ClubIntrouvable(f"Aucun club d'identifiant {club_id}.")
        archers = [a for a in self._archers.par_tournoi(tournoi_id) if a.club_id == club_id]
        ids = [
            i.id
            for archer in archers
            if archer.id is not None
            for i in self._inscriptions.par_archer(archer.id)
            if i.id is not None
        ]
        if ids:
            entree = self._trace(
                tournoi_id,
                objet=f"Paiement groupé — club {club.nom} ({len(ids)} inscription(s))",
                paye=paye,
            )
            self._inscriptions.definir_paye_avec_trace(ids, paye, entree)
        tarifs = self._tarifs(tournoi_id)
        lignes = sorted(
            (self._ligne(a, tarifs) for a in archers),
            key=lambda ligne: (ligne.nom.casefold(), ligne.prenom.casefold()),
        )
        return RecapClub(
            club_id=club_id,
            nom=club.nom,
            recap=total(ligne.recap for ligne in lignes),
            archers=lignes,
        )

    # --- Helpers -----------------------------------------------------------------------------

    def _tarifs(self, tournoi_id: TournoiId) -> dict[DepartId, int]:
        """Table `départ → tarif` du tournoi (une lecture), pour dériver les récapitulatifs."""
        return {
            depart.id: depart.tarif_centimes
            for depart in self._departs.par_tournoi(tournoi_id)
            if depart.id is not None
        }

    def _ligne(self, archer: Archer, tarifs: dict[DepartId, int]) -> LignePaiementArcher:
        """Récapitule un archer depuis ses inscriptions et la table des tarifs.

        Une inscription dont le créneau est absent de `tarifs` (purge en cascade concurrente,
        instantané périmé) est **ignorée** — tolérance de `ServiceInscriptions.lister_par_archer`.
        """
        assert archer.id is not None, "Un archer relu est persisté."
        lignes = [
            (tarifs[i.depart_id], i.paye)
            for i in self._inscriptions.par_archer(archer.id)
            if i.depart_id in tarifs
        ]
        return LignePaiementArcher(
            archer_id=archer.id,
            nom=archer.nom,
            prenom=archer.prenom,
            club_id=archer.club_id,
            recap=recapituler(lignes),
        )

    def _trace(
        self,
        tournoi_id: TournoiId,
        *,
        objet: str,
        paye: bool,
        avant: str | None = None,
    ) -> EntreeAudit:
        """Construit l'entrée d'audit d'un marquage, **datée** par le port `Horloge` (domaine pur).

        `apres` est le statut visé ; `avant` n'est renseigné que pour le marquage **simple** (le
        seul où un statut antérieur unique a un sens — un lot part de statuts hétérogènes).
        """
        return EntreeAudit.creer(
            tournoi_id=tournoi_id,
            action=ActionAuditee.PAIEMENT,
            auteur=_AUTEUR_ADMIN,
            horodatage=self._horloge.maintenant(),
            objet=objet,
            avant=avant,
            apres=_statut(paye),
        )

    def _tournoi_existant(self, tournoi_id: TournoiId) -> None:
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")

    def _archer_existant(self, archer_id: ArcherId) -> Archer:
        archer = self._archers.par_id(archer_id)
        if archer is None:
            raise ArcherIntrouvable(f"Aucun archer d'identifiant {archer_id}.")
        return archer

    def _archer_du_tournoi(self, tournoi_id: TournoiId, archer_id: ArcherId) -> Archer:
        """Relit un archer et exige qu'il soit **de ce tournoi** ; sinon `ArcherIntrouvable`.

        Un archer d'un autre tournoi est introuvable du point de vue de celui de l'URL — même parti
        que `DepartIntrouvable`/`CategorieHorsTournoi` (on ne fuite pas les voisins).
        """
        archer = self._archers.par_id(archer_id)
        if archer is None or archer.tournoi_id != tournoi_id:
            raise ArcherIntrouvable(
                f"Aucun archer d'identifiant {archer_id} dans le tournoi {tournoi_id}."
            )
        return archer


def _statut(paye: bool) -> str:
    """Rend le statut de paiement en clair pour la trace d'audit (« payé » / « non payé »)."""
    return "payé" if paye else "non payé"
