"""Fixtures et doublures partagées des tests backend.

`connecter_admin` : ouvre un accès admin (POST `/api/v1/auth/configurer`, E10US002) sur un client
de test et pose l'en-tête `Authorization: Bearer <jeton>` par défaut, pour que les appels suivants
vers les routes admin (ex. création de tournoi) soient autorisés. Suppose que le fichier `.env`
de l'app pointe vers un chemin jetable (voir les fixtures d'app qui passent `admin_env_path`).

**Doctrine des doublures** : un faux repository consommé par **≥ 2 modules** de test vit ici ;
celui qui n'a qu'un consommateur reste dans son module (`FauxScoreRepository` reste dans
`test_service_archers`). Depuis E02US001, `FauxClubRepository` et `FauxArcherRepository` servent
**à la fois** aux tests de `ServiceClubs` (qui refuse de supprimer un club utilisé) et à ceux de
`ServiceArchers` (qui valide le club de rattachement) — les héberger dans l'un des deux modules
ferait importer l'autre en retour, jusqu'au **cycle d'imports**.

`FauxCategorieRepository` a rejoint ce fichier en E02US002, qui en devenait le **3ᵉ** consommateur
(`ServiceArchers` valide désormais la catégorie de l'archer) après `test_service_categories` et
`test_service_blasons`, où deux copies identiques vivaient chacune de leur côté. C'est la preuve
d'aujourd'hui que réclame le projet avant de factoriser, pas une évolution supposée.

`FauxDepartRepository` et `FauxInscriptionRepository` ont rejoint ce fichier en E02US009.
`FauxInscriptionRepository` naît partagé — trois consommateurs du premier jour
(`test_service_inscriptions`, `test_service_departs` pour le garde-fou « départ avec inscriptions »,
`test_service_archers` pour l'« engagé » élargi). `FauxDepartRepository`, lui, vivait dans
`test_service_departs` : `test_service_inscriptions` en devient le **2ᵉ** consommateur (il faut de
vrais départs pour y inscrire un archer), d'où la migration. `FauxInscriptionRepository` est un
simple magasin, **sans** couplage à l'archer (au contraire de `FauxScoreRepository`) :
les tests de service ne vérifient pas la purge en cascade — c'est un contrat d'adapter, prouvé au
niveau du repository (`test_inscription_repository`).

> `FauxTournoiRepository` est, lui, recopié dans trois modules. On le laisse : cette US n'en ajoute
> pas d'usage, et on ne réécrit pas ce qu'on n'aggrave pas.

Seules des dépendances **stdlib** sont ajoutées ici (`domain` est pur, règle 1) : ce conftest
reste importable sans fastapi, comme l'exige le hook pre-commit `domain-isolation`, qui exécute
pytest avec pytest pour seule dépendance — d'où aussi `fastapi` sous `TYPE_CHECKING` ci-dessous.
"""

from __future__ import annotations

import dataclasses
import datetime
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

import pytest

from domain.archer import Archer, ArcherId
from domain.blason import BlasonId
from domain.categorie import Categorie, CategorieId
from domain.club import Club, ClubId, cle_nom
from domain.depart import Depart, DepartId
from domain.entree_audit import EntreeAudit
from domain.forfait import Forfait
from domain.inscription import Inscription, InscriptionId
from domain.phase import PhaseId
from domain.placement import Affectation
from domain.remboursement import Remboursement, RemboursementId
from domain.tournoi import TournoiId

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

# Alias de type en **forward-ref** (chaîne) : `conftest.py` reste importable sans `fastapi`
# installé — nécessaire au hook pre-commit `domain-isolation`, qui exécute pytest dans un
# environnement minimal (pytest seul) et charge malgré tout ce conftest. Au runtime, les
# annotations sont différées (`from __future__ import annotations`), donc `fastapi` n'est
# jamais requis ici ; les tests qui s'en servent créent leur `TestClient` ailleurs.
ConnecterAdmin = Callable[["TestClient"], None]


class HorlogeFigee:
    """Horloge déterministe conforme au port `Horloge` (règle 9) : toujours le même instant.

    Partagée par les tests de service qui **datent** un acte (paiement, remboursement,
    désinscription
    payée) : un instant UTC figé rend la trace et les dates d'ouverture/traitement reproductibles,
    sans horloge système. (`test_service_paiements` garde sa propre copie locale, historique.)
    """

    def __init__(self, instant: datetime.datetime) -> None:
        self._instant = instant

    def maintenant(self) -> datetime.datetime:
        return self._instant


class FauxClubRepository:
    """Repository en mémoire conforme au port `ClubRepository`.

    `par_nom` applique `cle_nom`, **la fonction de production** — pas une réimplémentation : un
    faux qui recoderait la règle de comparaison ferait passer les tests de service quoi qu'il
    arrive à l'adapter réel.
    """

    def __init__(self) -> None:
        self._clubs: dict[int, Club] = {}
        self._sequence = 0

    def ajouter(self, club: Club) -> Club:
        self._sequence += 1
        persiste = dataclasses.replace(club, id=self._sequence)
        self._clubs[self._sequence] = persiste
        return persiste

    def par_id(self, club_id: ClubId) -> Club | None:
        return self._clubs.get(club_id)

    def par_nom(self, nom: str) -> Club | None:
        recherche = cle_nom(nom)
        for club in self._clubs.values():
            if cle_nom(club.nom) == recherche:
                return club
        return None

    def lister(self) -> list[Club]:
        return list(self._clubs.values())

    def enregistrer(self, club: Club) -> Club:
        assert club.id is not None
        self._clubs[club.id] = club
        return club

    def supprimer(self, club_id: ClubId) -> None:
        del self._clubs[club_id]


class FauxArcherRepository:
    """Repository en mémoire conforme au port `ArcherRepository`."""

    def __init__(self) -> None:
        self._archers: dict[int, Archer] = {}
        self._sequence = 0

    def ajouter(self, archer: Archer) -> Archer:
        self._sequence += 1
        # `club_id` est **recopié** : un faux qui le laisserait tomber ferait passer au vert un
        # service incapable de rattacher un archer à son club.
        persiste = dataclasses.replace(archer, id=self._sequence)
        self._archers[self._sequence] = persiste
        return persiste

    def par_id(self, archer_id: ArcherId) -> Archer | None:
        return self._archers.get(archer_id)

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Archer]:
        return [a for a in self._archers.values() if a.tournoi_id == tournoi_id]

    def par_club(self, club_id: ClubId) -> list[Archer]:
        # Sans filtre sur le tournoi : le référentiel des clubs est global (E02US001).
        return [a for a in self._archers.values() if a.club_id == club_id]

    def enregistrer(self, archer: Archer) -> Archer:
        assert archer.id is not None
        self._archers[archer.id] = archer
        return archer

    def supprimer(self, archer_id: ArcherId) -> None:
        del self._archers[archer_id]

    def fusionner(self, gagnant_id: ArcherId, perdant_id: ArcherId) -> None:
        # Effet observable **au niveau archer** : le perdant disparaît, le gagnant reste. La
        # réassignation des inscriptions/scores/séries est un contrat d'adapter (prouvé au niveau du
        # repository, `test_archer_score_repository`), invisible ici — comme `supprimer` ne purge
        # pas la descendance dans ce faux. Un faux qui la simulerait recoderait la règle.
        del self._archers[perdant_id]


class FauxCategorieRepository:
    """Repository en mémoire conforme au port `CategorieRepository`."""

    def __init__(self) -> None:
        self._categories: dict[int, Categorie] = {}
        self._sequence = 0

    def ajouter(self, categorie: Categorie) -> Categorie:
        self._sequence += 1
        persiste = dataclasses.replace(categorie, id=self._sequence)
        self._categories[self._sequence] = persiste
        return persiste

    def par_id(self, categorie_id: CategorieId) -> Categorie | None:
        return self._categories.get(categorie_id)

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Categorie]:
        # Le filtre sur `tournoi_id` est ce qui rend testable le refus d'une catégorie
        # **étrangère au tournoi** (`CategorieHorsTournoi`, E02US002) : un faux qui renverrait
        # tout ferait passer au vert un service incapable de cloisonner les tournois.
        return [c for c in self._categories.values() if c.tournoi_id == tournoi_id]

    def par_blason(self, blason_id: BlasonId) -> list[Categorie]:
        return [c for c in self._categories.values() if c.blason_id == blason_id]

    def enregistrer(self, categorie: Categorie) -> Categorie:
        assert categorie.id in self._categories
        self._categories[categorie.id] = categorie
        return categorie

    def supprimer(self, categorie_id: CategorieId) -> None:
        del self._categories[categorie_id]


class FauxDepartRepository:
    """Repository de départs en mémoire conforme au port `DepartRepository`."""

    def __init__(self) -> None:
        self._departs: dict[int, Depart] = {}
        self._sequence = 0
        # Remboursements ouverts par `supprimer_avec_remboursements` : le test de service y lit
        # *quels* postes le service a construits (archer, créneau, montant, motif). L'ouverture
        # atomique avec les `DELETE` est un contrat d'adapter, prouvé au niveau du repository.
        self.remboursements: list[Remboursement] = []

    def ajouter(self, depart: Depart) -> Depart:
        self._sequence += 1
        persiste = dataclasses.replace(depart, id=self._sequence)
        self._departs[self._sequence] = persiste
        return persiste

    def par_id(self, depart_id: DepartId) -> Depart | None:
        return self._departs.get(depart_id)

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Depart]:
        departs = [d for d in self._departs.values() if d.tournoi_id == tournoi_id]
        return sorted(departs, key=lambda d: d.numero)

    def enregistrer(self, depart: Depart) -> Depart:
        assert depart.id in self._departs, "Départ à mettre à jour absent."
        self._departs[depart.id] = depart
        return depart

    def supprimer(self, depart_id: DepartId) -> None:
        del self._departs[depart_id]

    def supprimer_avec_remboursements(
        self, depart_id: DepartId, remboursements: Sequence[Remboursement]
    ) -> None:
        # Supprime le départ et **capture** les remboursements ouverts (E08US005). L'atomicité et la
        # cascade des inscriptions sont un contrat d'adapter, hors des tests de service.
        del self._departs[depart_id]
        self.remboursements.extend(remboursements)


class FauxInscriptionRepository:
    """Repository d'inscriptions en mémoire conforme au port `InscriptionRepository`.

    Magasin **simple** : pas de couplage à l'existence de l'archer ou du départ (au contraire de
    `FauxScoreRepository`, qui filtre pour reproduire la purge). Les tests de service ne prouvent
    pas la cascade de suppression — c'est un contrat d'adapter, prouvé au niveau du repository.
    `par_archer_et_depart` applique la **règle d'unicité** (le premier lien du couple), ce qui rend
    testable le refus `DejaInscrit` sans réimplémenter une contrainte.
    """

    def __init__(self) -> None:
        self._inscriptions: dict[int, Inscription] = {}
        self._sequence = 0
        # Entrées d'audit capturées par `definir_paye_avec_trace` : le test de service y lit
        # *quelle* trace le service a construite (auteur, action, avant/après). L'**atomicité**
        # acte↔trace, elle, est un contrat d'adapter, prouvé au niveau du repository.
        self.traces: list[EntreeAudit] = []
        # Remboursements ouverts par `supprimer_avec_remboursement` (désinscription payée,
        # E08US005) :
        # le test de service y lit *quel* poste le service a construit. Atomicité = contrat
        # d'adapter.
        self.remboursements: list[Remboursement] = []

    def ajouter(self, inscription: Inscription) -> Inscription:
        self._sequence += 1
        persiste = dataclasses.replace(inscription, id=self._sequence)
        self._inscriptions[self._sequence] = persiste
        return persiste

    def par_id(self, inscription_id: InscriptionId) -> Inscription | None:
        return self._inscriptions.get(inscription_id)

    def par_archer(self, archer_id: ArcherId) -> list[Inscription]:
        return [i for i in self._inscriptions.values() if i.archer_id == archer_id]

    def par_depart(self, depart_id: DepartId) -> list[Inscription]:
        return [i for i in self._inscriptions.values() if i.depart_id == depart_id]

    def par_archer_et_depart(self, archer_id: ArcherId, depart_id: DepartId) -> Inscription | None:
        for inscription in self._inscriptions.values():
            if inscription.archer_id == archer_id and inscription.depart_id == depart_id:
                return inscription
        return None

    def enregistrer(self, inscription: Inscription) -> Inscription:
        assert inscription.id in self._inscriptions, "Inscription à mettre à jour absente."
        self._inscriptions[inscription.id] = inscription
        return inscription

    def definir_paye_avec_trace(
        self, inscription_ids: Sequence[InscriptionId], paye: bool, entree: EntreeAudit
    ) -> list[Inscription]:
        # Bascule `paye` et **capture** la trace (la vraie co-écriture atomique est un contrat
        # d'adapter, hors des tests de service). Les inscriptions doivent exister (contrat du port).
        maj = []
        for inscription_id in inscription_ids:
            inscription = dataclasses.replace(self._inscriptions[inscription_id], paye=paye)
            self._inscriptions[inscription_id] = inscription
            maj.append(inscription)
        self.traces.append(entree)
        return maj

    def supprimer(self, inscription_id: InscriptionId) -> None:
        del self._inscriptions[inscription_id]

    def supprimer_avec_remboursement(
        self, inscription_id: InscriptionId, remboursement: Remboursement
    ) -> None:
        # Supprime l'inscription et **capture** le remboursement ouvert (E08US005). L'atomicité est
        # un contrat d'adapter, hors des tests de service.
        del self._inscriptions[inscription_id]
        self.remboursements.append(remboursement)


class FauxRemboursementRepository:
    """Repository de remboursements en mémoire conforme au port `RemboursementRepository`
    (E08US005).

    Sert les tests de `ServiceRemboursements` : `ajouter` n'est **pas** du port (les postes naissent
    d'un effacement d'inscription, pas d'un ajout direct) — c'est un utilitaire de test pour peupler
    le registre. `enregistrer_avec_trace` capture la trace `REMBOURSEMENT` (l'atomicité acte↔trace
    est un contrat d'adapter, hors des tests de service).
    """

    def __init__(self) -> None:
        self._remboursements: dict[int, Remboursement] = {}
        self._sequence = 0
        self.traces: list[EntreeAudit] = []

    def ajouter(self, remboursement: Remboursement) -> Remboursement:
        """Utilitaire de test (hors port) : peuple le registre comme le ferait un effacement."""
        self._sequence += 1
        persiste = dataclasses.replace(remboursement, id=self._sequence)
        self._remboursements[self._sequence] = persiste
        return persiste

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Remboursement]:
        return [r for r in self._remboursements.values() if r.tournoi_id == tournoi_id]

    def par_id(self, remboursement_id: RemboursementId) -> Remboursement | None:
        return self._remboursements.get(remboursement_id)

    def enregistrer_avec_trace(
        self, remboursement: Remboursement, entree: EntreeAudit
    ) -> Remboursement:
        assert remboursement.id in self._remboursements, "Remboursement à traiter absent."
        self._remboursements[remboursement.id] = remboursement
        self.traces.append(entree)
        return remboursement


class FauxPlacementRepository:
    """Repository de placement en mémoire conforme au port `PlacementRepository`.

    Magasin **simple** clé par `inscription_id` (une affectation par inscription) : les appelants
    lisent `par_depart`, volontairement **non trié** (c'est au service d'ordonner). Migré ici en
    E09US003, 2ᵉ consommateur (`test_service_feuille_de_marque` et `test_service_listes_impression`)
    — jusque-là local à la feuille de marque.
    """

    def __init__(self) -> None:
        self._affectation: dict[int, Affectation] = {}
        self._depart: dict[int, int] = {}

    def par_depart(self, depart_id: DepartId) -> list[Affectation]:
        return [a for i, a in self._affectation.items() if self._depart[i] == depart_id]

    def definir_plan(self, depart_id: DepartId, affectations: Sequence[Affectation]) -> None:
        self.poser_plusieurs(depart_id, affectations)

    def definir_plan_avec_trace(
        self, depart_id: DepartId, affectations: Sequence[Affectation], entree: object
    ) -> None:
        raise NotImplementedError("Non exercé par les tests de service qui consomment ce faux.")

    def poser_plusieurs(self, depart_id: DepartId, affectations: Sequence[Affectation]) -> None:
        for affectation in affectations:
            self._affectation[affectation.inscription_id] = affectation
            self._depart[affectation.inscription_id] = depart_id

    def retirer(self, inscription_id: int) -> None:
        self._affectation.pop(inscription_id, None)
        self._depart.pop(inscription_id, None)


class FauxForfaitRepository:
    """Double de `ForfaitRepository` (E04US015) : liste en mémoire, **vide par défaut**.

    `semer` ajoute des forfaits pour les tests qui en veulent (relégation au classement, walkover en
    duels) ; les tests qui n'en veulent pas obtiennent un repository conforme mais inerte.
    `declarer_avec_trace` / `annuler_avec_trace` ignorent la trace d'audit (co-écriture non
    pertinente hors intégration) et mutent la liste, pour couvrir un cycle déclarer → annuler.
    """

    def __init__(self, forfaits: list[Forfait] | None = None) -> None:
        self._forfaits: list[Forfait] = list(forfaits or [])
        self._sequence = 0

    def semer(self, forfait: Forfait) -> Forfait:
        self._sequence += 1
        persiste = dataclasses.replace(forfait, id=self._sequence)
        self._forfaits.append(persiste)
        return persiste

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Forfait]:
        return [f for f in self._forfaits if f.tournoi_id == tournoi_id]

    def par_phase(self, phase_id: PhaseId) -> list[Forfait]:
        return [f for f in self._forfaits if f.phase_id == phase_id]

    def par_archer_et_phase(
        self, tournoi_id: TournoiId, archer_id: ArcherId, phase_id: PhaseId
    ) -> Forfait | None:
        return next(
            (
                f
                for f in self._forfaits
                if f.tournoi_id == tournoi_id
                and f.archer_id == archer_id
                and f.phase_id == phase_id
            ),
            None,
        )

    def declarer_avec_trace(self, forfait: Forfait, entree: EntreeAudit) -> Forfait:
        return self.semer(forfait)

    def annuler_avec_trace(self, forfait: Forfait, entree: EntreeAudit) -> None:
        self._forfaits = [f for f in self._forfaits if f.id != forfait.id]


@pytest.fixture
def connecter_admin() -> ConnecterAdmin:
    """Renvoie une fonction qui configure l'accès admin et authentifie le client de test."""

    def _connecter(
        client: TestClient, login: str = "admin", mot_de_passe: str = "secret-123"
    ) -> None:
        reponse = client.post(
            "/api/v1/auth/configurer", json={"login": login, "mot_de_passe": mot_de_passe}
        )
        assert reponse.status_code == 201, reponse.text
        client.headers["Authorization"] = f"Bearer {reponse.json()['jeton']}"

    return _connecter
