"""Service d'archive de fin de tournoi (E11US003, CA « export/archive fin de tournoi »).

`ServiceArchive.composer` assemble, pour un tournoi donné et selon une **sélection** de parties
(cases à cocher côté UI), un paquet ZIP réunissant l'instantané SQLite complet, un dump CSV de
toute la base, les documents PDF régénérés du tournoi, et un manifeste. L'assemblage mécanique
(snapshot, CSV, ZIP) est délégué à un adapter d'infrastructure derrière le port
`ConstructeurArchive` — le service ne fait que l'**orchestration** métier :

- garde 404 (`TournoiIntrouvable`) si le tournoi n'existe pas, comme les autres services ;
- régénération des PDF via les services existants (feuille de marque par départ, listes du
  tournoi) — **best-effort** : un départ sans placement ne doit pas faire échouer toute l'archive,
  le document en échec est simplement omis (log serveur) ;
- métadonnées métier du manifeste (horodatage via le port `Horloge`, identité du tournoi).

**Port au niveau applicatif, pas domaine** : une archive est une préoccupation d'**exploitation**
(export/sauvegarde), pas une règle métier — elle n'a donc pas sa place dans `domain/` (règle 12 :
l'infra d'export reste simple, on ne pollue pas le domaine d'un concept opérationnel). Le sens des
dépendances reste respecté (règle 2) : l'infra implémente une interface, le service dépend de
l'abstraction.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import partial
from typing import Protocol

from application.erreurs import TournoiIntrouvable
from application.feuille_de_marque import ServiceFeuilleDeMarque
from application.listes_impression import ServiceListesImpression
from domain.listes_impression import TriPlacement
from domain.ports import DepartRepository, Horloge, TournoiRepository
from domain.tournoi import TournoiId

_logger = logging.getLogger(__name__)

_APPLICATION = "Kervignarc"


class ConstructeurArchive(Protocol):
    """Port : assemble le paquet ZIP à partir de la base et des documents fournis."""

    def construire(
        self,
        *,
        inclure_base: bool,
        inclure_csv: bool,
        documents: Mapping[str, bytes],
        metadonnees: Mapping[str, object],
    ) -> bytes:
        """Renvoie les octets du ZIP (snapshot SQLite, CSV, PDF, manifeste), selon inclusions."""
        ...


@dataclass(frozen=True)
class OptionsArchive:
    """Parties à inclure dans l'archive (cases à cocher). Tout est inclus par défaut."""

    base: bool = True
    donnees_csv: bool = True
    feuilles_de_marque: bool = True
    liste_placement: bool = True
    liste_club_paiement: bool = True


@dataclass(frozen=True)
class PaquetArchive:
    """Résultat d'une composition : le nom de fichier suggéré et les octets du ZIP."""

    nom_fichier: str
    contenu: bytes


class ServiceArchive:
    """Compose le paquet d'archive d'un tournoi selon les parties sélectionnées."""

    def __init__(
        self,
        tournoi_repository: TournoiRepository,
        depart_repository: DepartRepository,
        service_feuille_de_marque: ServiceFeuilleDeMarque,
        service_listes: ServiceListesImpression,
        constructeur: ConstructeurArchive,
        horloge: Horloge,
    ) -> None:
        self._tournois = tournoi_repository
        self._departs = depart_repository
        self._feuilles = service_feuille_de_marque
        self._listes = service_listes
        self._constructeur = constructeur
        self._horloge = horloge

    def composer(self, tournoi_id: TournoiId, options: OptionsArchive) -> PaquetArchive:
        """Assemble et renvoie l'archive du tournoi ; lève `TournoiIntrouvable` (404)."""
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")

        documents = self._rassembler_documents(tournoi_id, options)
        maintenant = self._horloge.maintenant()
        metadonnees: dict[str, object] = {
            "genere_le": maintenant.isoformat(),
            "application": _APPLICATION,
            "tournoi": {
                "id": tournoi.id,
                "nom": tournoi.nom,
                "date": tournoi.date.isoformat(),
                "statut": tournoi.statut.value,
            },
            "parties_incluses": {
                "base_sqlite": options.base,
                "donnees_csv": options.donnees_csv,
                "documents": sorted(documents),
            },
        }
        contenu = self._constructeur.construire(
            inclure_base=options.base,
            inclure_csv=options.donnees_csv,
            documents=documents,
            metadonnees=metadonnees,
        )
        horodatage = maintenant.strftime("%Y%m%d-%H%M%S")
        return PaquetArchive(f"archive-tournoi-{tournoi_id}-{horodatage}.zip", contenu)

    def _rassembler_documents(
        self, tournoi_id: TournoiId, options: OptionsArchive
    ) -> dict[str, bytes]:
        """Régénère les PDF sélectionnés du tournoi (best-effort, échec par document toléré)."""
        documents: dict[str, bytes] = {}
        if options.feuilles_de_marque:
            for depart in self._departs.par_tournoi(tournoi_id):
                if depart.id is None:
                    continue
                self._ajouter(
                    documents,
                    f"feuille-de-marque-depart-{depart.numero}.pdf",
                    partial(self._feuilles.generer, tournoi_id, depart.id),
                )
        if options.liste_placement:
            self._ajouter(
                documents,
                "placement.pdf",
                partial(self._listes.generer_placement, tournoi_id, None, TriPlacement.CIBLE),
            )
        if options.liste_club_paiement:
            self._ajouter(
                documents,
                "club-paiement.pdf",
                partial(self._listes.generer_club_paiement, tournoi_id),
            )
        return documents

    @staticmethod
    def _ajouter(documents: dict[str, bytes], nom: str, generer: Callable[[], bytes]) -> None:
        """Ajoute un document régénéré ; en cas d'échec, l'omet et journalise (best-effort)."""
        try:
            documents[nom] = generer()
        except Exception:  # best-effort : un document manquant ne casse pas l'archive
            _logger.warning("Document d'archive « %s » non généré (omis).", nom, exc_info=True)
