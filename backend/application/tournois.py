"""Service applicatif Tournois — orchestre le domaine derrière le port repository.

Use cases de configuration d'un tournoi : créer, consulter, lister (E01US001) ; éditer et
piloter le **cycle de vie à sept statuts** (E01US017, [ADR-0026]) — passer prêt, démarrer,
mettre en pause / reprendre, terminer, archiver, annuler — et supprimer. Il ne connaît ni HTTP,
ni SQL, ni la file d'écriture (sérialisation assurée en amont, côté API) ; il reste synchrone et
pur d'infrastructure. Il arbitre l'**existence** (`TournoiIntrouvable`) et les **conflits d'état**
du cycle de vie (`TransitionStatutInvalide`, `TournoiEnCoursNonSupprimable`,
`TournoiArchiveNonModifiable`) — l'agrégat, lui, ne valide que les valeurs (ADR-0007/0026 §4).
"""

from __future__ import annotations

import datetime
from collections.abc import Callable, Iterable

from application.erreurs import (
    TournoiArchiveNonModifiable,
    TournoiEnCoursNonSupprimable,
    TournoiIntrouvable,
    TournoiSansDepart,
    TransitionStatutInvalide,
)
from domain.ports import DepartRepository, TournoiRepository
from domain.tournoi import StatutTournoi, Tournoi, TournoiId, TypeTournoi


class ServiceTournois:
    """Cas d'usage des tournois : créer, consulter, lister, éditer, cycle de vie, supprimer."""

    def __init__(self, repository: TournoiRepository, depart_repository: DepartRepository) -> None:
        self._repository = repository
        # E02US010 : le passage à `prêt` exige **au moins un départ**. `ServiceTournois` lit donc
        # les créneaux (port `DepartRepository`, un port de domaine — pas l'autre service, pas
        # d'infra), comme il lit les tournois. Couplage minimal : une seule lecture (`par_tournoi`),
        # dont on ne prend que le compte.
        self._departs = depart_repository

    def creer(
        self,
        nom: str,
        date: datetime.date,
        lieu: str | None = None,
        type_tournoi: TypeTournoi = TypeTournoi.NON_OFFICIEL,
    ) -> Tournoi:
        """Crée et persiste un tournoi. Lève `DomainError` si les champs sont invalides.

        Le tarif ne se fixe plus ici : il vit sur chaque départ (créneau), configuré par
        `ServiceDeparts` (E02US004, ADR-0017).
        """
        tournoi = Tournoi.creer(nom, date, lieu, type_tournoi)
        return self._repository.ajouter(tournoi)

    def consulter(self, tournoi_id: TournoiId) -> Tournoi:
        """Relit un tournoi. Lève `TournoiIntrouvable` s'il n'existe pas."""
        tournoi = self._repository.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        return tournoi

    def lister(self) -> list[Tournoi]:
        """Renvoie tous les tournois (liste éventuellement vide)."""
        return self._repository.lister()

    def modifier(
        self,
        tournoi_id: TournoiId,
        nom: str,
        date: datetime.date,
        lieu: str | None = None,
        type_tournoi: TypeTournoi = TypeTournoi.NON_OFFICIEL,
    ) -> Tournoi:
        """Édite les métadonnées d'un tournoi (nom, date, lieu, type), statut préservé.

        Lève `TournoiIntrouvable` si l'identifiant est inconnu, `DomainError` si le nom est
        vide. L'édition est autorisée quel que soit le statut. Le tarif ne fait plus partie des
        métadonnées du tournoi (il vit sur chaque départ — E02US004).
        """
        tournoi = self.consulter(tournoi_id)
        if tournoi.statut is StatutTournoi.ARCHIVE:
            raise TournoiArchiveNonModifiable(
                "Un tournoi archivé est en lecture seule ; il ne peut plus être édité."
            )
        modifie = tournoi.modifier(nom, date, lieu, type_tournoi)
        return self._repository.enregistrer(modifie)

    # --- Cycle de vie enrichi (E01US017, ADR-0026) ---
    # L'agrégat ne porte que la valeur ; le service arbitre l'**enchaînement** légal (ADR-0007/0026
    # §4). `_transition` factorise le patron « relire → vérifier le statut de départ → produire la
    # copie → persister » pour les arêtes à garde de simple légalité. `vers_pret` fait bande à part
    # (garde de complétude en plus, E12US005 à froid) ; `supprimer` n'est pas une transition.

    def vers_pret(self, tournoi_id: TournoiId) -> Tournoi:
        """Passe un tournoi `brouillon` à `prêt` (feu vert au démarrage).

        Lève `TournoiIntrouvable` si inconnu, `TransitionStatutInvalide` (→ 409) s'il n'est pas
        `brouillon`, `TournoiSansDepart` (→ 409) s'il n'a **aucun départ** (E02US010). Cette garde
        « ≥ 1 départ » est la **première brique** de la garde de complétude de préparation
        (catégories, blasons associés, gabarit, barème — [ADR-0026] §2) : le reste est ajouté par
        une tranche ultérieure.
        """
        tournoi = self.consulter(tournoi_id)
        if tournoi.statut is not StatutTournoi.BROUILLON:
            raise TransitionStatutInvalide("Seul un tournoi en brouillon peut passer prêt.")
        if not self._departs.par_tournoi(tournoi_id):
            raise TournoiSansDepart(
                "Ce tournoi n'a aucun départ ; ajoutez au moins un créneau avant de le passer prêt."
            )
        return self._repository.enregistrer(tournoi.vers_pret())

    def revenir_brouillon(self, tournoi_id: TournoiId) -> Tournoi:
        """Repasse un tournoi `prêt` en `brouillon` (renoncer au feu vert pour rééditer)."""
        return self._transition(
            tournoi_id,
            {StatutTournoi.PRET},
            Tournoi.revenir_brouillon,
            "Seul un tournoi prêt peut revenir en brouillon.",
        )

    def demarrer(self, tournoi_id: TournoiId) -> Tournoi:
        """Passe un tournoi `prêt` à `en_cours` (le démarrage passe désormais par `prêt`)."""
        return self._transition(
            tournoi_id,
            {StatutTournoi.PRET},
            Tournoi.demarrer,
            "Seul un tournoi prêt peut être démarré.",
        )

    def mettre_en_pause(self, tournoi_id: TournoiId) -> Tournoi:
        """Gèle un tournoi `en_cours` en `en_pause` (la saisie s'arrête jusqu'à `reprendre`)."""
        return self._transition(
            tournoi_id,
            {StatutTournoi.EN_COURS},
            Tournoi.mettre_en_pause,
            "Seul un tournoi en cours peut être mis en pause.",
        )

    def reprendre(self, tournoi_id: TournoiId) -> Tournoi:
        """Reprend un tournoi `en_pause` en `en_cours`."""
        return self._transition(
            tournoi_id,
            {StatutTournoi.EN_PAUSE},
            Tournoi.reprendre,
            "Seul un tournoi en pause peut être repris.",
        )

    def terminer(self, tournoi_id: TournoiId) -> Tournoi:
        """Passe un tournoi `en_cours` à `terminé` (fige les résultats sportifs)."""
        return self._transition(
            tournoi_id,
            {StatutTournoi.EN_COURS},
            Tournoi.terminer,
            "Seul un tournoi en cours peut être terminé.",
        )

    def archiver(self, tournoi_id: TournoiId) -> Tournoi:
        """Archive un tournoi `terminé` (verrou total, lecture seule définitive)."""
        return self._transition(
            tournoi_id,
            {StatutTournoi.TERMINE},
            Tournoi.archiver,
            "Seul un tournoi terminé peut être archivé.",
        )

    def annuler(self, tournoi_id: TournoiId) -> Tournoi:
        """Annule un tournoi abandonné (terminal, conserve la trace ≠ suppression).

        Accessible depuis `brouillon`, `prêt`, `en_cours`, `en_pause` — **pas** depuis `terminé`
        (un tournoi joué jusqu'au bout n'est pas « annulé ») ni `archivé` ([ADR-0026] §2).
        """
        return self._transition(
            tournoi_id,
            {
                StatutTournoi.BROUILLON,
                StatutTournoi.PRET,
                StatutTournoi.EN_COURS,
                StatutTournoi.EN_PAUSE,
            },
            Tournoi.annuler,
            "Un tournoi terminé ou archivé ne peut pas être annulé.",
        )

    def _transition(
        self,
        tournoi_id: TournoiId,
        depuis: Iterable[StatutTournoi],
        produire: Callable[[Tournoi], Tournoi],
        message: str,
    ) -> Tournoi:
        """Applique une transition de cycle de vie gardée par le seul statut de départ.

        Relit le tournoi (`TournoiIntrouvable` si inconnu), refuse si son statut n'est pas dans
        `depuis` (`TransitionStatutInvalide` → 409), sinon persiste la copie produite.
        """
        tournoi = self.consulter(tournoi_id)
        if tournoi.statut not in set(depuis):
            raise TransitionStatutInvalide(message)
        return self._repository.enregistrer(produire(tournoi))

    def supprimer(self, tournoi_id: TournoiId) -> None:
        """Supprime un tournoi.

        Lève `TournoiIntrouvable` si inconnu ; `TournoiEnCoursNonSupprimable` (→ 409) si le tournoi
        est `en_cours` ou `en_pause` (le terminer/annuler d'abord) ; `TournoiArchiveNonModifiable`
        (→ 409) s'il est `archivé` (lecture seule). Un `brouillon`, `prêt`, `terminé` ou `annulé`
        reste supprimable ([ADR-0026] §1).
        """
        tournoi = self.consulter(tournoi_id)
        if tournoi.statut in {StatutTournoi.EN_COURS, StatutTournoi.EN_PAUSE}:
            raise TournoiEnCoursNonSupprimable(
                "Un tournoi en cours ou en pause ne peut pas être supprimé ; terminez-le ou "
                "annulez-le d'abord."
            )
        if tournoi.statut is StatutTournoi.ARCHIVE:
            raise TournoiArchiveNonModifiable(
                "Un tournoi archivé est en lecture seule ; il ne peut pas être supprimé."
            )
        assert tournoi.id is not None, "Un tournoi consulté est persisté."
        self._repository.supprimer(tournoi.id)
