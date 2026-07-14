"""Service applicatif Gabarits de salle — CRUD des gabarits réutilisables (E01US007).

Orchestre le domaine derrière le port repository. Ne connaît ni HTTP, ni SQL, ni la file
d'écriture (sérialisation assurée en amont, côté API) ; il reste synchrone et pur
d'infrastructure. Les gabarits sont **autonomes** (non rattachés à un tournoi) : le service ne
dépend d'aucune autre ressource et fait remonter des erreurs typées (`GabaritIntrouvable`).
"""

from __future__ import annotations

from application.erreurs import GabaritIntrouvable
from domain.gabarit_salle import GabaritSalle, GabaritSalleId
from domain.ports import GabaritSalleRepository


class ServiceGabarits:
    """Cas d'usage des gabarits de salle : créer, lister, éditer, supprimer."""

    def __init__(self, gabarits: GabaritSalleRepository) -> None:
        self._gabarits = gabarits

    def creer(self, nom: str, nb_cibles: int, capacite: int) -> GabaritSalle:
        """Crée un gabarit de `nb_cibles` cibles au plafond `capacite`.

        Lève `DomainError` si le nom est vide, le nombre de cibles `< 1`, ou le plafond hors
        de `[1, 4]`.
        """
        gabarit = GabaritSalle.creer(nom, nb_cibles, capacite)
        return self._gabarits.ajouter(gabarit)

    def lister(self) -> list[GabaritSalle]:
        """Renvoie tous les gabarits (liste éventuellement vide)."""
        return self._gabarits.lister()

    def modifier(
        self, gabarit_id: GabaritSalleId, nom: str, nb_cibles: int, capacite: int
    ) -> GabaritSalle:
        """Édite un gabarit (nom, nombre de cibles, plafond).

        Lève `GabaritIntrouvable` si l'identifiant est inconnu, `DomainError` si un attribut
        est invalide.
        """
        gabarit = self._gabarit_existant(gabarit_id)
        modifie = gabarit.modifier(nom, nb_cibles, capacite)
        return self._gabarits.enregistrer(modifie)

    def supprimer(self, gabarit_id: GabaritSalleId) -> None:
        """Supprime un gabarit. Lève `GabaritIntrouvable` si l'identifiant est inconnu."""
        self._gabarit_existant(gabarit_id)
        self._gabarits.supprimer(gabarit_id)

    def _gabarit_existant(self, gabarit_id: GabaritSalleId) -> GabaritSalle:
        gabarit = self._gabarits.par_id(gabarit_id)
        if gabarit is None:
            raise GabaritIntrouvable(f"Aucun gabarit de salle d'identifiant {gabarit_id}.")
        return gabarit
