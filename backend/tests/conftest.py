"""Fixtures et doublures partagées des tests backend.

`connecter_admin` : ouvre un accès admin (POST `/api/v1/auth/configurer`, E10US002) sur un client de
test et pose l'en-tête `Authorization: Bearer <jeton>` par défaut, pour que les appels suivants vers
les routes admin (ex. création de tournoi) soient autorisés. Suppose que le fichier `.env` de l'app
pointe vers un chemin jetable (voir les fixtures d'app qui passent `admin_env_path`).

**Doctrine des doublures** : un faux repository consommé par **≥ 2 modules** de test vit ici ; celui
qui n'a qu'un consommateur reste dans son module (`FauxScoreRepository` reste dans
`test_service_archers`). Depuis E02US001, `FauxClubRepository` et `FauxArcherRepository` servent **à
la fois** aux tests de `ServiceClubs` (qui refuse de supprimer un club utilisé) et à ceux de
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

Seules des dépendances **stdlib** sont ajoutées ici (`domain` est pur, règle 1) : ce conftest reste
importable sans fastapi, comme l'exige le hook pre-commit `domain-isolation`, qui exécute pytest
avec pytest pour seule dépendance — d'où aussi `fastapi` sous `TYPE_CHECKING` ci-dessous.
"""

from __future__ import annotations

import dataclasses
import datetime
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any

import pytest

from domain.archer import Archer, ArcherId
from domain.blason import BlasonId
from domain.categorie import Categorie, CategorieId
from domain.classement import Classement, LigneClassement
from domain.classement_de_tableau import ClassementSource
from domain.club import Club, ClubId, cle_nom
from domain.depart import Depart, DepartId
from domain.deroule_etape import EtapeDeroule, EtapeDerouleId
from domain.duel import BaremeDuel, Duel
from domain.entree_audit import EntreeAudit
from domain.forfait import Forfait
from domain.inscription import Inscription, InscriptionId
from domain.phase import Phase, PhaseId, TypePhase
from domain.placement import Affectation
from domain.remboursement import Remboursement, RemboursementId
from domain.tournoi import TournoiId

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

# Alias de type en **forward-ref** (chaîne) : `conftest.py` reste importable sans `fastapi` installé
# — nécessaire au hook pre-commit `domain-isolation`, qui exécute pytest dans un environnement
# minimal (pytest seul) et charge malgré tout ce conftest. Au runtime, les annotations sont
# différées (`from __future__ import annotations`), donc `fastapi` n'est jamais requis ici ; les
# tests qui s'en servent créent leur `TestClient` ailleurs.
ConnecterAdmin = Callable[["TestClient"], None]


class HorlogeFigee:
    """Horloge déterministe conforme au port `Horloge` (règle 9) : toujours le même instant.

    Partagée par les tests de service qui **datent** un acte (paiement, remboursement,
    désinscription payée) : un instant UTC figé rend la trace et les dates d'ouverture/traitement
    reproductibles,
    sans horloge système. (`test_service_paiements` garde sa propre copie locale, historique.)
    """

    def __init__(self, instant: datetime.datetime) -> None:
        self._instant = instant

    def maintenant(self) -> datetime.datetime:
        return self._instant


class FauxClubRepository:
    """Repository en mémoire conforme au port `ClubRepository`.

    `par_nom` applique `cle_nom`, **la fonction de production** — pas une réimplémentation : un faux
    qui recoderait la règle de comparaison ferait passer les tests de service quoi qu'il arrive à
    l'adapter réel.
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
        # Le filtre sur `tournoi_id` est ce qui rend testable le refus d'une catégorie **étrangère
        # au tournoi** (`CategorieHorsTournoi`, E02US002) : un faux qui renverrait tout ferait
        # passer au vert un service incapable de cloisonner les tournois.
        return [c for c in self._categories.values() if c.tournoi_id == tournoi_id]

    def par_bibliotheque(self) -> list[Categorie]:
        # Modèles de bibliothèque (E01US023) : ceux sans tournoi.
        return [x for x in self._categories.values() if x.tournoi_id is None]

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
        """Persiste le départ ; un `id` **déjà fourni est préservé**, sinon un est attribué.

        Même règle que `FauxPhaseRepository` et que l'adapter in-memory de production : des tests
        posent un décor à identifiants choisis (`_DEPART = 7`) pour pouvoir s'y référer depuis le
        module. Écraser l'`id` fourni les obligerait à contourner le port — et, plus insidieux,
        laisserait les phases pointer un créneau que le magasin ne connaît pas : la vue transverse
        rendrait alors « ce tournoi n'a aucune phase » sans que rien ne le signale.
        """
        if depart.id is not None:
            self._sequence = max(self._sequence, depart.id)
            self._departs[depart.id] = depart
            return depart
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
        # Remboursements ouverts par `supprimer_avec_remboursement` (désinscription payée, E08US005)
        # : le test de service y lit *quel* poste le service a construit. Atomicité = contrat
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


class FauxPhaseRepository:
    """Repository de phases en mémoire conforme au port `PhaseRepository` (E01US025, ADR-0075).

    **Hissée ici depuis neuf fichiers de tests** qui en portaient chacun une copie quasi identique.
    Ce n'est pas un patron introduit par anticipation : les neuf existaient, et la bascule de portée
    (`tournoi_id` → `depart_id`) aurait demandé la même correction neuf fois — avec neuf occasions
    de la faire à moitié. C'est exactement la duplication d'invariant que le registre de dette
    proscrit.

    ⚠️ **`departs` est nécessaire à la seule vue transverse `par_tournoi`** : une phase ne connaît
    plus que son créneau, donc « les phases de ce tournoi » exige la jointure `phase → depart`. Les
    tests qui n'interrogent que `par_depart` peuvent l'omettre ; ceux qui passent par un service
    lisant le barème « du tournoi » (`application/portee.py`) doivent le câbler, sans quoi
    l'assertion ci-dessous les arrête au lieu de les laisser croire à un tournoi sans phase.
    """

    def __init__(
        self,
        departs: FauxDepartRepository | None = None,
        deroules: FauxDerouleRepository | None = None,
    ) -> None:
        self._phases: dict[int, Phase] = {}
        # ⚠️ **La séquence ne démarre pas à 0** (correctif de revue E05US025). `TournoiId`,
        # `DepartId` et `PhaseId` sont trois alias d'`int` (`DETTE-044`) : un décor où la première
        # phase reçoit l'identifiant 1, comme le tournoi, rend **vert par coïncidence** tout service
        # qui confondrait les deux — c'est exactement ce qui a laissé passer le bloquant d'E05US025
        # (la feuille de marque lue au tournoi là où le port attend la phase). Décaler la séquence
        # fait échouer la confusion au lieu de la couvrir ; c'est la discipline que
        # `test_domain_serie.py` s'imposait déjà localement (`_PHASE = 4`), généralisée.
        self._sequence = 100
        self._departs = departs
        # ⚠️ **Câblé, cette doublure `assemble` comme les deux adapters de production** (ADR-0076) :
        # la définition rendue vient de l'étape de même rang, pas de ce qui dort dans le magasin.
        # Sans lui, elle reste en **mode indulgent** et rend la phase telle qu'elle a été posée — ce
        # qui suffit aux décors qui ne lisent que des statuts, mais **ment** dès qu'un test édite
        # une définition : il verrait l'ancienne valeur et conclurait à un bug qui n'existe que dans
        # son décor.
        self._deroules = deroules

    def _assembler(self, phases: list[Phase]) -> list[Phase]:
        """Complète chaque phase de sa définition ; une **orpheline** est écartée, comme en SQL."""
        if self._departs is None or self._deroules is None:
            return phases
        assemblees = []
        for phase in phases:
            depart = self._departs.par_id(phase.depart_id)
            if depart is None:
                continue
            deroule = self._deroules.par_tournoi(depart.tournoi_id)
            etape = next((e for e in deroule if e.ordre == phase.ordre), None)
            if etape is not None:
                assemblees.append(
                    dataclasses.replace(
                        etape.instancier(phase.depart_id), statut=phase.statut, id=phase.id
                    )
                )
        return assemblees

    def _assembler_une(self, phase: Phase) -> Phase | None:
        assemblees = self._assembler([phase])
        return assemblees[0] if assemblees else None

    def ajouter(self, phase: Phase) -> Phase:
        """Persiste la phase ; un `id` **déjà fourni est préservé**, sinon un est attribué.

        Même règle que l'adapter in-memory de production (`_AllocateurId`) : certains tests posent
        un décor à identifiants choisis pour pouvoir s'y référer. Écraser l'`id` fourni les
        obligerait à contourner le port — ce que faisaient plusieurs des neuf copies, chacune à sa
        manière.
        """
        if phase.id is not None:
            self._sequence = max(self._sequence, phase.id)
            self._phases[phase.id] = phase
            return phase
        self._sequence += 1
        persiste = dataclasses.replace(phase, id=self._sequence)
        self._phases[self._sequence] = persiste
        return persiste

    def par_id(self, phase_id: PhaseId) -> Phase | None:
        phase = self._phases.get(phase_id)
        return None if phase is None else self._assembler_une(phase)

    def par_depart_et_type(self, depart_id: DepartId, type_phase: TypePhase) -> Phase | None:
        """La phase de ce type dans ce créneau ; la **plus récente** en cas de multiplicité.

        Même règle que l'adapter SQL (`ORDER BY id DESC`) : une doublure qui rendrait la première
        divergerait du vrai comportement, et le test passerait là où la production échouerait.
        """
        trouvees = [p for p in self.par_depart(depart_id) if p.type is type_phase]
        return trouvees[-1] if trouvees else None

    def par_depart(self, depart_id: DepartId) -> list[Phase]:
        phases = [p for p in self._phases.values() if p.depart_id == depart_id]
        return self._assembler(sorted(phases, key=lambda p: p.ordre))

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Phase]:
        """Vue transverse : les phases de **tous** les départs, triées (départ, ordre).

        Ce n'est **pas** une séquence — c'est la concaténation de N suites 1..M. La passer à
        `SequencePhases` lèverait `SequenceOrdreInvalide`, et c'est le comportement voulu.
        """
        assert self._departs is not None, (
            "Cette doublure a besoin du magasin de départs pour la vue transverse « phases du "
            "tournoi » : passez-le au constructeur (FauxPhaseRepository(departs))."
        )
        connus = {d.id for d in self._departs.par_tournoi(tournoi_id)}
        phases = [p for p in self._phases.values() if p.depart_id in connus]
        return self._assembler(sorted(phases, key=lambda p: (p.depart_id, p.ordre)))

    def enregistrer(self, phase: Phase) -> Phase:
        """Met à jour l'**avancement** ; la définition passée est ignorée (contrat du port)."""
        assert phase.id in self._phases
        self._phases[phase.id] = phase
        assemblee = self._assembler_une(phase)
        return phase if assemblee is None else assemblee

    def reordonner(self, phases: list[Phase]) -> None:
        """Réaligne les rangs du lot ; seul l'`ordre` bouge, comme les deux adapters réels."""
        for phase in phases:
            assert phase.id in self._phases
            self._phases[phase.id] = dataclasses.replace(self._phases[phase.id], ordre=phase.ordre)

    def supprimer(self, phase_id: PhaseId) -> None:
        del self._phases[phase_id]


class FauxDerouleRepository:
    """Repository du **déroulé** en mémoire, conforme au port `DerouleRepository` (ADR-0076).

    Porte la **définition** des étapes d'un tournoi — une seule fois, quel que soit le nombre de
    créneaux. Son pendant `FauxPhaseRepository` ne porte que l'avancement.
    """

    def __init__(self) -> None:
        self._items: dict[int, EtapeDeroule] = {}
        self._sequence = 0

    def ajouter(self, etape: EtapeDeroule) -> EtapeDeroule:
        """Persiste l'étape ; un `id` **déjà fourni est préservé** (même règle que les phases)."""
        if etape.id is not None:
            self._sequence = max(self._sequence, etape.id)
            self._items[etape.id] = etape
            return etape
        self._sequence += 1
        persiste = dataclasses.replace(etape, id=self._sequence)
        self._items[self._sequence] = persiste
        return persiste

    def par_tournoi(self, tournoi_id: TournoiId) -> list[EtapeDeroule]:
        etapes = [e for e in self._items.values() if e.tournoi_id == tournoi_id]
        return sorted(etapes, key=lambda e: e.ordre)

    def enregistrer(self, etape: EtapeDeroule) -> EtapeDeroule:
        assert etape.id in self._items
        self._items[etape.id] = etape
        return etape

    def reordonner(self, etapes: list[EtapeDeroule]) -> list[EtapeDeroule]:
        """Réécrit le lot d'un coup (contrat « ou tout, ou rien » de `DerouleRepository`)."""
        for etape in etapes:
            assert etape.id in self._items
            self._items[etape.id] = etape
        return list(etapes)

    def supprimer(self, etape_id: EtapeDerouleId) -> None:
        self._items.pop(etape_id, None)


def poser_phase_factice(
    departs: FauxDepartRepository,
    deroules: FauxDerouleRepository,
    phases: FauxPhaseRepository,
    phase: Phase,
) -> Phase:
    """Jumeau en mémoire de `poser_phase_sql` : définit l'**étape**, puis l'instancie (ADR-0076).

    Les décors de service posaient une `Phase` complète en un seul `phases.ajouter(...)`. Depuis la
    séparation déroulé / avancement, faire cela laisse le tournoi **sans déroulé** : le service qui
    lit `DerouleRepository` n'y trouve rien, et le test échoue pour une raison de décor — non pour
    ce qu'il voulait éprouver. Ce helper rétablit le confort d'un seul appel sans rétablir la
    duplication : l'étape est **réutilisée** si son rang existe déjà, si bien que deux créneaux d'un
    même tournoi partagent bien la même définition.

    `statut` et `id` de la phase reçue sont **conservés** : plusieurs décors posent un avancement
    déjà engagé, ou à identifiant choisi pour pouvoir s'y référer.
    """
    depart = departs.par_id(phase.depart_id)
    assert depart is not None, (
        "Le décor doit créer le créneau avant d'y poser une phase — une phase pend au départ "
        "(ADR-0075), et son déroulé au tournoi de ce départ (ADR-0076)."
    )
    etape = next(
        (e for e in deroules.par_tournoi(depart.tournoi_id) if e.ordre == phase.ordre), None
    )
    if etape is None:
        etape = deroules.ajouter(
            EtapeDeroule(
                tournoi_id=depart.tournoi_id,
                ordre=phase.ordre,
                type=phase.type,
                bareme=phase.bareme,
                validation=phase.validation,
                sources=phase.sources,
                effectif=phase.effectif,
                barrage_jusqu_au=phase.barrage_jusqu_au,
                profondeur=phase.profondeur,
                # E05US023 : le réglage de poules aussi. Les deux jumeaux le perdaient, si bien
                # qu'un décor posant une phase de poules réglée obtenait une phase **non réglée** —
                # exactement la classe de divergence que la docstring ci-dessus décrit.
                poules=phase.poules,
                # ⚠️ **Le même oubli s'est reproduit en E05US028**, à l'identique : un décor posant
                # un Big Shoot Off réglé obtenait une phase non réglée, et le test d'API échouait en
                # `phase_pas_reglee` sur une phase qui l'était. C'est la **2ᵉ** occurrence — ce
                # recopiage champ par champ est structurellement fragile (rien ne rougit quand on en
                # oublie un), et il le sera à chaque réglage neuf. Le remède serait de dériver
                # l'étape de la phase par une fabrique unique, côté domaine ; il vaut une US.
                big_shoot_off=phase.big_shoot_off,
                # ⚠️ **3ᵉ occurrence, E05US026** — et la prédiction ci-dessus s'est vérifiée mot
                # pour mot : le réglage du système suisse a été oublié ici, et quatre tests d'API
                # ont échoué en `phase_pas_reglee` sur une phase parfaitement réglée. Le seuil du «
                # remède structurel » de `CLAUDE.md` est atteint **sur preuve**, et la dette est
                # désormais **tracée** (`DETTE-064`) au lieu de ne vivre qu'en commentaire — c'est
                # ce qui manquait pour qu'elle soit prise. Remède : une fabrique unique du domaine
                # (`EtapeDeroule.de_phase(phase)`), en US dédiée.
                suisse=phase.suisse,
                # ⚠️ **4ᵉ occurrence, E05US033** (`DETTE-064`, élargie et non contournée) : le
                # découpage en tours. Les **arrêts**, eux, ne sont pas recopiables depuis une
                # `Phase` — elle ne porte pas ce champ — et se posent directement sur l'étape : ce
                # n'est donc pas une 5ᵉ occurrence du même piège, comme la première rédaction le
                # comptait (relevé en revue, axe A). Le premier suit le patron des quatre réglages
                # ci-dessus ; le second n'a **pas** de miroir sur `Phase` et ne peut donc pas être
                # recopié depuis elle — il se pose sur l'étape, ce que les décors d'arrêts font
                # directement. Le recopiage champ par champ reste ce qu'il était : rien ne rougit
                # quand on en oublie un. Le remède (`EtapeDeroule.de_phase`) est identifié et **hors
                # périmètre ici** — un remède structurel se traite en ADR + US dédiée, pas en douce
                # dans l'US courante (§ Dette).
                decoupage=phase.decoupage,
            )
        )
    return phases.ajouter(
        dataclasses.replace(etape.instancier(phase.depart_id), statut=phase.statut, id=phase.id)
    )


def poser_phase_sql(session_factory: Any, phase: Phase) -> Phase:
    """Définit l'**étape** puis l'instancie dans le créneau — les deux gestes d'ADR-0076.

    Depuis la séparation déroulé / avancement, poser une phase demande deux écritures : la
    définition va sur `deroule_etape` (au tournoi), l'avancement sur `phase` (au créneau). Les
    décors de tests posaient une `Phase` complète en un seul appel ; ce helper préserve ce confort
    sans rétablir la duplication — l'étape est **réutilisée** si elle existe déjà, si bien que deux
    créneaux d'un même tournoi partagent bien la même définition.

    Passer par le repository plutôt que par l'ORM est délibéré : c'est le chemin de production, et
    un décor qui l'emprunte éprouve la vraie couture d'assemblage.

    ⚠️ **`statut` et `id` de la phase reçue sont conservés**, comme dans le jumeau en mémoire
    (`poser_phase_factice`). Ce helper les **perdait** : `etape.instancier()` rend une phase
    `a_venir` sans identifiant, si bien qu'un décor SQL posant un avancement déjà engagé —
    `Phase.qualification(...).demarrer()` — obtenait silencieusement une phase `à venir`. Deux
    jumeaux qui divergent sur ce qu'ils préservent, c'est un test qui passe en mémoire et échoue en
    base (ou l'inverse) sans que la différence se voie à l'appel.
    """
    from domain.deroule_etape import EtapeDeroule
    from infrastructure.db import (
        DepartRepositorySQL,
        DerouleEtapeRepositorySQL,
        PhaseRepositorySQL,
    )

    depart = DepartRepositorySQL(session_factory).par_id(phase.depart_id)
    assert depart is not None, "Le décor doit avoir créé le créneau avant d'y poser une phase."
    deroules = DerouleEtapeRepositorySQL(session_factory)
    etape = next(
        (e for e in deroules.par_tournoi(depart.tournoi_id) if e.ordre == phase.ordre), None
    )
    if etape is None:
        etape = deroules.ajouter(
            EtapeDeroule(
                tournoi_id=depart.tournoi_id,
                ordre=phase.ordre,
                type=phase.type,
                bareme=phase.bareme,
                validation=phase.validation,
                sources=phase.sources,
                effectif=phase.effectif,
                barrage_jusqu_au=phase.barrage_jusqu_au,
                profondeur=phase.profondeur,
                # E05US023 : le réglage de poules aussi. Les deux jumeaux le perdaient, si bien
                # qu'un décor posant une phase de poules réglée obtenait une phase **non réglée** —
                # exactement la classe de divergence que la docstring ci-dessus décrit.
                poules=phase.poules,
                # ⚠️ **Le même oubli s'est reproduit en E05US028**, à l'identique : un décor posant
                # un Big Shoot Off réglé obtenait une phase non réglée, et le test d'API échouait en
                # `phase_pas_reglee` sur une phase qui l'était. C'est la **2ᵉ** occurrence — ce
                # recopiage champ par champ est structurellement fragile (rien ne rougit quand on en
                # oublie un), et il le sera à chaque réglage neuf. Le remède serait de dériver
                # l'étape de la phase par une fabrique unique, côté domaine ; il vaut une US.
                big_shoot_off=phase.big_shoot_off,
                # ⚠️ **3ᵉ occurrence, E05US026** — et la prédiction ci-dessus s'est vérifiée mot
                # pour mot : le réglage du système suisse a été oublié ici, et quatre tests d'API
                # ont échoué en `phase_pas_reglee` sur une phase parfaitement réglée. Le seuil du «
                # remède structurel » de `CLAUDE.md` est atteint **sur preuve**, et la dette est
                # désormais **tracée** (`DETTE-064`) au lieu de ne vivre qu'en commentaire — c'est
                # ce qui manquait pour qu'elle soit prise. Remède : une fabrique unique du domaine
                # (`EtapeDeroule.de_phase(phase)`), en US dédiée.
                suisse=phase.suisse,
                # ⚠️ **4ᵉ occurrence, E05US033** (`DETTE-064`, élargie et non contournée) : le
                # découpage en tours. Les **arrêts**, eux, ne sont pas recopiables depuis une
                # `Phase` — elle ne porte pas ce champ — et se posent directement sur l'étape : ce
                # n'est donc pas une 5ᵉ occurrence du même piège, comme la première rédaction le
                # comptait (relevé en revue, axe A). Le premier suit le patron des quatre réglages
                # ci-dessus ; le second n'a **pas** de miroir sur `Phase` et ne peut donc pas être
                # recopié depuis elle — il se pose sur l'étape, ce que les décors d'arrêts font
                # directement. Le recopiage champ par champ reste ce qu'il était : rien ne rougit
                # quand on en oublie un. Le remède (`EtapeDeroule.de_phase`) est identifié et **hors
                # périmètre ici** — un remède structurel se traite en ADR + US dédiée, pas en douce
                # dans l'US courante (§ Dette).
                decoupage=phase.decoupage,
            )
        )
    return PhaseRepositorySQL(session_factory).ajouter(
        dataclasses.replace(etape.instancier(phase.depart_id), statut=phase.statut, id=phase.id)
    )


class FauxDuelRepository:
    """Double de `DuelRepository` : ne garde que le **tir** ; réinjecte le contexte à `charger`.

    Hissé ici depuis `test_service_saisie_duels.py` par **E05US024** : le test du plan de cibles en
    a désormais besoin lui aussi (le plan emprunte la résolution de classement amont de la saisie),
    et l'importer d'un module de test qui importe déjà celui du placement aurait fait un cycle.
    """

    def __init__(self) -> None:
        self._tirs: dict[tuple[int, int], Duel] = {}

    def numeros_enregistres(self, phase_id: PhaseId) -> frozenset[int]:
        return frozenset(numero for (phase, numero) in self._tirs if phase == phase_id)

    def charger(self, phase_id: PhaseId, match_numero: int, *, bareme: BaremeDuel) -> Duel | None:
        duel = self._tirs.get((phase_id, match_numero))
        if duel is None:
            return None
        # Mime « le tir + l'identité des duellistes sont persistés » : seul le barème est réinjecté
        # (dérivé de l'arme, ADR-0049). Les participants **stockés** sont conservés.
        return dataclasses.replace(duel, bareme=bareme)

    def enregistrer(self, phase_id: PhaseId, match_numero: int, duel: Duel) -> Duel:
        self._tirs[(phase_id, match_numero)] = duel
        return duel


def qualification_de_secours(
    session_factory: Any, tournoi_id: int, depart_id: int | None = None
) -> int:
    """L'identifiant de la qualification d'un créneau (le **premier** par défaut), posée au besoin.

    Échafaudage introduit par **E05US025** (ADR-0082). Une feuille de marque pend désormais à sa
    phase (`serie.phase_id`, `NOT NULL`) : un décor qui sème des scores « directement par le
    repository » — parce que dérouler la chorégraphie HTTP de saisie serait hors sujet pour ce qu'il
    éprouve — doit donc disposer d'une phase réelle, ce que plusieurs n'avaient pas.

    Le helper est **idempotent** : il réutilise la qualification si le créneau en porte déjà une, et
    n'en pose une (ordre 1, barème minimal) que sinon. Il lève si le tournoi n'a aucun créneau — un
    décor sans départ ne peut de toute façon rien classer depuis ADR-0075, et un échec net vaut
    mieux qu'une phase fabriquée sur un tournoi vide.
    """
    from domain.bareme import BaremeQualification
    from domain.phase import Phase, TypePhase
    from infrastructure.db import DepartRepositorySQL, PhaseRepositorySQL

    departs = DepartRepositorySQL(session_factory).par_tournoi(tournoi_id)
    if not departs:
        raise AssertionError(
            "Ce décor n'a aucun créneau : depuis ADR-0075 une phase pend au départ, il n'y a "
            "donc nulle part où poser la qualification que réclame `serie.phase_id`."
        )
    if depart_id is None:
        depart_id = departs[0].id
    assert depart_id is not None
    existante = next(
        (
            p
            for p in PhaseRepositorySQL(session_factory).par_depart(depart_id)
            if p.type is TypePhase.QUALIFICATION
        ),
        None,
    )
    if existante is not None and existante.id is not None:
        return existante.id
    phase = poser_phase_sql(
        session_factory, Phase.qualification(depart_id, BaremeQualification.creer(1, 3))
    )
    assert phase.id is not None
    return phase.id


class FauxLecteurPopulations:
    """Doublure du port `LecteurPopulationPhase` (E05US025, correctif de revue).

    Dit, pour l'`ordre` d'une phase, **quels archers elle a reçus** — la seule chose que la saisie
    et la complétude lui demandent. `populations` vide ⇒ le résolveur rend `None` partout, et les
    deux services retombent sur leur comportement mono-qualification : c'est le montage par défaut,
    et il est **volontairement inerte** pour que les décors existants ne changent pas de sens.

    Renseigner `populations[ordre]` monte la **fourche** du CA (une *haute* et une *basse* qui se
    jouent ensemble) sans avoir à câbler tout le moteur de classement dans un test de service.

    ⚠️ **`tous` n'est pas un confort, c'est la fidélité à la production** (2ᵉ correctif de revue).
    En production, une phase **sans source** — la qualification de tête — rend
    `ClassementSource(pour_depart(...))`, c'est-à-dire **tout le créneau**, y compris les archers à
    zéro flèche. Une doublure qui rendrait `None` pour l'ordre de tête ferait croire que la tête ne
    réclame personne, donc que l'ensemble des phases admissibles est toujours un singleton — et le
    départage entre elles, seul endroit où la production peut se tromper, ne serait exercé par aucun
    test. C'est le doublage « porté à moitié » que cette même US a dénoncé deux fois ; on ne le
    refait pas ici. Renseigner `tous` pose donc la population par défaut de tout ordre non déclaré.
    """

    def __init__(
        self, populations: dict[int, list[int]] | None = None, tous: list[int] | None = None
    ) -> None:
        self.populations: dict[int, list[int]] = {} if populations is None else populations
        self.tous: list[int] | None = tous

    def resolveur_de_classement(
        self, tournoi_id: int, depart_id: int
    ) -> Callable[[int], ClassementSource | None]:
        def resoudre(ordre: int) -> ClassementSource | None:
            archers = self.populations.get(ordre, self.tous)
            if archers is None:
                return None
            return ClassementSource(
                classement=Classement(
                    lignes=tuple(
                        LigneClassement(
                            rang_scratch=rang,
                            rang_categorie=rang,
                            archer_id=archer_id,
                            nom="",
                            prenom="",
                            categorie_id=1,
                            categorie_libelle="",
                            cible=None,
                            club_id=None,
                            total=0,
                            nb_dix=0,
                            nb_neuf=0,
                        )
                        for rang, archer_id in enumerate(archers, start=1)
                    )
                )
            )

        return resoudre
