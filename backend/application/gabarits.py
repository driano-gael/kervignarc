"""Service applicatif Gabarits de salle — bibliothèque de modèles (E01US007) et application à un
tournoi (E01US008).

Orchestre le domaine derrière les ports repository. Ne connaît ni HTTP, ni SQL, ni la file
d'écriture (sérialisation assurée en amont, côté API) ; il reste synchrone et pur
d'infrastructure.

Deux facettes :
- **bibliothèque** : CRUD des gabarits **modèles** (`tournoi_id is None`), réutilisables ;
- **application à un tournoi** : appliquer un modèle en crée une **copie** propre au tournoi, que
  l'on peut ensuite **ajuster** (nom, plafond cible par cible) **sans altérer** le modèle.

Fait remonter des erreurs typées (`GabaritIntrouvable`, `TournoiIntrouvable`,
`GabaritDuTournoiAbsent`).
"""

from __future__ import annotations

from application.erreurs import (
    GabaritDuTournoiAbsent,
    GabaritIntrouvable,
    TournoiIntrouvable,
)
from domain.gabarit_salle import GabaritSalle, GabaritSalleId
from domain.ports import GabaritSalleRepository, TournoiRepository
from domain.tournoi import TournoiId


class ServiceGabarits:
    """Cas d'usage des gabarits : CRUD des modèles ; appliquer/ajuster le plan d'un tournoi."""

    def __init__(self, tournois: TournoiRepository, gabarits: GabaritSalleRepository) -> None:
        self._tournois = tournois
        self._gabarits = gabarits

    def creer(self, nom: str, nb_cibles: int, capacite: int) -> GabaritSalle:
        """Crée un gabarit **modèle** de `nb_cibles` cibles au plafond `capacite`.

        Lève `DomainError` si le nom est vide, le nombre de cibles `< 1`, ou le plafond hors
        de `[1, 4]`.
        """
        gabarit = GabaritSalle.creer(nom, nb_cibles, capacite)
        return self._gabarits.ajouter(gabarit)

    def lister(self) -> list[GabaritSalle]:
        """Renvoie tous les gabarits **modèles** de la bibliothèque (liste éventuellement vide)."""
        return self._gabarits.lister()

    def modifier(
        self, gabarit_id: GabaritSalleId, nom: str, nb_cibles: int, capacite: int
    ) -> GabaritSalle:
        """Édite un gabarit modèle (nom, nombre de cibles, plafond uniforme).

        Lève `GabaritIntrouvable` si l'identifiant est inconnu, `DomainError` si un attribut
        est invalide.
        """
        gabarit = self._gabarit_existant(gabarit_id)
        modifie = gabarit.modifier(nom, nb_cibles, capacite)
        return self._gabarits.enregistrer(modifie)

    def supprimer(self, gabarit_id: GabaritSalleId) -> None:
        """Supprime un gabarit modèle. Lève `GabaritIntrouvable` si l'identifiant est inconnu.

        Les tournois qui l'avaient appliqué gardent leur **copie** intacte (indépendante).
        """
        self._gabarit_existant(gabarit_id)
        self._gabarits.supprimer(gabarit_id)

    def gabarit_du_tournoi(self, tournoi_id: TournoiId) -> GabaritSalle | None:
        """Renvoie l'instance de gabarit appliquée au tournoi, ou `None` s'il n'y en a pas.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas.
        """
        self._tournoi_existant(tournoi_id)
        return self._gabarits.par_tournoi(tournoi_id)

    def appliquer(self, tournoi_id: TournoiId, modele_id: GabaritSalleId) -> GabaritSalle:
        """Applique un gabarit **modèle** à un tournoi (E01US008) : en crée/rafraîchit la copie.

        La copie reprend le nom et les plafonds du modèle. Si le tournoi avait déjà une instance,
        elle est **remplacée sur place** (même identifiant, pour ne pas casser d'éventuelles
        références) ; sinon une nouvelle copie est persistée. Le modèle d'origine reste intact.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas, `GabaritIntrouvable` si
        `modele_id` n'est pas un modèle applicable (inconnu ou déjà rattaché à un tournoi).
        """
        self._tournoi_existant(tournoi_id)
        modele = self._modele_existant(modele_id)
        instance = self._gabarits.par_tournoi(tournoi_id)
        if instance is None:
            return self._gabarits.ajouter(modele.pour_tournoi(tournoi_id))
        rafraichie = instance.ajuster(modele.nom, modele.capacites)
        return self._gabarits.enregistrer(rafraichie)

    def ajuster(self, tournoi_id: TournoiId, nom: str, capacites: tuple[int, ...]) -> GabaritSalle:
        """Ajuste le gabarit appliqué à un tournoi (E01US008) : nom + plafond cible par cible.

        `capacites` porte une valeur par cible (son nombre fixe le nombre de cibles). N'affecte
        que la copie du tournoi. Lève `TournoiIntrouvable` si le tournoi n'existe pas,
        `GabaritDuTournoiAbsent` si aucun gabarit n'y est appliqué, `DomainError` si un plafond
        ou le nombre de cibles est invalide.
        """
        self._tournoi_existant(tournoi_id)
        instance = self._gabarits.par_tournoi(tournoi_id)
        if instance is None:
            raise GabaritDuTournoiAbsent(f"Aucun gabarit n'est appliqué au tournoi {tournoi_id}.")
        ajustee = instance.ajuster(nom, capacites)
        return self._gabarits.enregistrer(ajustee)

    def _gabarit_existant(self, gabarit_id: GabaritSalleId) -> GabaritSalle:
        gabarit = self._gabarits.par_id(gabarit_id)
        if gabarit is None:
            raise GabaritIntrouvable(f"Aucun gabarit de salle d'identifiant {gabarit_id}.")
        return gabarit

    def _modele_existant(self, modele_id: GabaritSalleId) -> GabaritSalle:
        """Le gabarit visé doit exister **et** être un modèle (non rattaché à un tournoi)."""
        gabarit = self._gabarits.par_id(modele_id)
        if gabarit is None or gabarit.tournoi_id is not None:
            raise GabaritIntrouvable(f"Aucun gabarit modèle d'identifiant {modele_id}.")
        return gabarit

    def _tournoi_existant(self, tournoi_id: TournoiId) -> None:
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
