"""Service applicatif Inscriptions — inscrire un archer sur des départs (E02US009, ADR-0017).

Orchestre le lien **archer ↔ départ** derrière les ports repository. Ne connaît ni HTTP, ni SQL, ni
la file d'écriture (sérialisation assurée en amont, côté API) ; synchrone et pur d'infrastructure.

C'est ici — et pas dans l'entité `Inscription`, qui ne voit que deux clés — que vivent les règles
inter-agrégats de l'US :

- **même tournoi** : un archer ne s'inscrit que sur un départ **de son propre tournoi** ; un départ
  d'un autre tournoi est *introuvable* de son point de vue (`DepartIntrouvable`, comme
  `CategorieHorsTournoi` cachait la catégorie voisine) ;
- **unicité** : pas deux fois le même couple `(archer, départ)` (`DejaInscrit`), pendant applicatif
  de la contrainte `UNIQUE` en base ;
- **montant dérivé** : le montant dû d'une inscription **n'est pas stocké**, il se lit sur le
  `tarif_centimes` du départ à chaque lecture (`InscriptionDetaillee`).
"""

from __future__ import annotations

from dataclasses import dataclass

from application.erreurs import (
    ArcherIntrouvable,
    DejaInscrit,
    DepartIntrouvable,
    InscriptionIntrouvable,
)
from domain.archer import Archer, ArcherId
from domain.depart import Depart, DepartId
from domain.inscription import Inscription, InscriptionId
from domain.ports import ArcherRepository, DepartRepository, InscriptionRepository


@dataclass(frozen=True)
class InscriptionDetaillee:
    """Vue applicative de lecture : une inscription **et** le départ qu'elle vise.

    Le montant dû se **dérive** du tarif du départ (`montant_du_centimes`) — il n'est pas un champ
    stocké de l'inscription (ADR-0017). Porter le départ entier, et pas seulement le montant, permet
    à l'écran d'afficher aussi le numéro et l'horaire du créneau sans une seconde lecture.
    """

    inscription: Inscription
    depart: Depart

    @property
    def montant_du_centimes(self) -> int:
        """Montant dû = tarif du créneau (ADR-0017 ; la somme par archer est E08US001)."""
        return self.depart.tarif_centimes


class ServiceInscriptions:
    """Cas d'usage des inscriptions : inscrire, lister, marquer payé, désinscrire."""

    def __init__(
        self,
        inscription_repository: InscriptionRepository,
        archer_repository: ArcherRepository,
        depart_repository: DepartRepository,
    ) -> None:
        self._inscriptions = inscription_repository
        self._archers = archer_repository
        self._departs = depart_repository

    def inscrire(self, archer_id: ArcherId, depart_id: DepartId) -> InscriptionDetaillee:
        """Inscrit un archer sur un départ de **son** tournoi.

        Lève `ArcherIntrouvable` si l'archer n'existe pas, `DepartIntrouvable` si le départ n'existe
        pas **ou n'appartient pas au tournoi de l'archer**, `DejaInscrit` s'il est déjà inscrit sur
        ce créneau.

        Contrôle d'unicité et insertion tiennent dans **une seule commande** en file (règle 7) :
        aucune inscription concurrente ne peut se glisser entre les deux. La contrainte
        `UNIQUE(archer_id, depart_id)` reste le garde-fou ultime.
        """
        archer = self._archer_existant(archer_id)
        depart = self._depart_de_l_archer(archer, depart_id)
        if self._inscriptions.par_archer_et_depart(archer_id, depart_id) is not None:
            raise DejaInscrit(
                f"« {archer.prenom} {archer.nom} » est déjà inscrit sur le départ n° "
                f"{depart.numero}."
            )
        inscription = self._inscriptions.ajouter(Inscription.creer(archer_id, depart_id))
        return InscriptionDetaillee(inscription, depart)

    def lister_par_archer(self, archer_id: ArcherId) -> list[InscriptionDetaillee]:
        """Renvoie les inscriptions d'un archer, avec leur montant, triées par n° de départ.

        Lève `ArcherIntrouvable` si l'archer n'existe pas — un archer inconnu n'a pas « zéro
        inscription », il n'existe pas.
        """
        self._archer_existant(archer_id)
        detaillees = [
            InscriptionDetaillee(inscription, self._depart_lie(inscription))
            for inscription in self._inscriptions.par_archer(archer_id)
        ]
        return sorted(detaillees, key=lambda d: d.depart.numero)

    def marquer_paye(self, inscription_id: InscriptionId, paye: bool) -> InscriptionDetaillee:
        """Bascule le statut de paiement d'une inscription. Lève `InscriptionIntrouvable` sinon."""
        inscription = self._inscription_existante(inscription_id)
        maj = self._inscriptions.enregistrer(inscription.marquer_paye(paye))
        return InscriptionDetaillee(maj, self._depart_lie(maj))

    def desinscrire(self, inscription_id: InscriptionId) -> None:
        """Désinscrit un archer d'un départ (libre). Lève `InscriptionIntrouvable` sinon."""
        inscription = self._inscription_existante(inscription_id)
        assert inscription.id is not None, "Une inscription relue est persistée."
        self._inscriptions.supprimer(inscription.id)

    def _archer_existant(self, archer_id: ArcherId) -> Archer:
        archer = self._archers.par_id(archer_id)
        if archer is None:
            raise ArcherIntrouvable(f"Aucun archer d'identifiant {archer_id}.")
        return archer

    def _depart_de_l_archer(self, archer: Archer, depart_id: DepartId) -> Depart:
        """Relit un départ et exige qu'il soit **du tournoi de l'archer** ; sinon introuvable.

        Patron `ServiceDeparts._depart_du_tournoi`, mais borné au tournoi de l'archer : de son point
        de vue, un créneau d'un autre tournoi n'existe pas — on ne lui fuite pas les voisins.
        """
        depart = self._departs.par_id(depart_id)
        if depart is None or depart.tournoi_id != archer.tournoi_id:
            raise DepartIntrouvable(
                f"Aucun départ d'identifiant {depart_id} dans le tournoi {archer.tournoi_id}."
            )
        return depart

    def _inscription_existante(self, inscription_id: InscriptionId) -> Inscription:
        inscription = self._inscriptions.par_id(inscription_id)
        if inscription is None:
            raise InscriptionIntrouvable(f"Aucune inscription d'identifiant {inscription_id}.")
        return inscription

    def _depart_lie(self, inscription: Inscription) -> Depart:
        """Relit le départ d'une inscription persistée — il existe forcément (FK garantie)."""
        depart = self._departs.par_id(inscription.depart_id)
        assert depart is not None, "Une inscription pointe toujours vers un départ existant."
        return depart
