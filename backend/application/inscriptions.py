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
    DepartComplet,
    DepartIntrouvable,
    InscriptionIntrouvable,
    InscriptionPayeeARembourser,
)
from domain.archer import Archer, ArcherId
from domain.depart import Depart, DepartId
from domain.inscription import Inscription, InscriptionId
from domain.ports import ArcherRepository, DepartRepository, Horloge, InscriptionRepository
from domain.remboursement import MotifRemboursement, Remboursement


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
    """Cas d'usage des inscriptions : inscrire, lister (avec montant dû dérivé), désinscrire.

    Le **marquage du paiement** (`paye`) ne vit plus ici : il a migré vers `application.paiements`
    (E08US002), où il est **audité** et complété du marquage groupé (par archer, par club). Ce
    service ne fait plus que le lien archer↔départ et la dérivation du montant dû (E08US001).
    """

    def __init__(
        self,
        inscription_repository: InscriptionRepository,
        archer_repository: ArcherRepository,
        depart_repository: DepartRepository,
        horloge: Horloge,
    ) -> None:
        self._inscriptions = inscription_repository
        self._archers = archer_repository
        self._departs = depart_repository
        self._horloge = horloge

    def inscrire(self, archer_id: ArcherId, depart_id: DepartId) -> InscriptionDetaillee:
        """Inscrit un archer sur un départ de **son** tournoi.

        Lève `ArcherIntrouvable` si l'archer n'existe pas, `DepartIntrouvable` si le départ n'existe
        pas **ou n'appartient pas au tournoi de l'archer**, `DejaInscrit` s'il est déjà inscrit sur
        ce créneau, `DepartComplet` si le créneau porte un quota déjà **atteint** (E02US006).

        Contrôle d'unicité, **contrôle de quota** et insertion tiennent dans **une seule commande**
        en file (règle 7) : aucune inscription concurrente ne peut se glisser entre le comptage et
        l'insertion, donc franchir la dernière place. La contrainte `UNIQUE(archer_id, depart_id)`
        reste le garde-fou ultime de l'unicité — mais le quota, lui, n'a **aucun** filet en base
        (rien ne l'exprime en SQL) : la sérialisation par le writer unique **est** ce garde-fou.
        """
        archer = self._archer_existant(archer_id)
        depart = self._depart_de_l_archer(archer, depart_id)
        if self._inscriptions.par_archer_et_depart(archer_id, depart_id) is not None:
            raise DejaInscrit(
                f"« {archer.prenom} {archer.nom} » est déjà inscrit sur le départ n° "
                f"{depart.numero}."
            )
        # `is not None` et non la vérité de `quota` : un quota de `0` ne peut pas exister (le
        # domaine le refuse), mais l'idiome garde « défini » distinct de « absent » sans ambiguïté.
        # On compte **toutes** les inscriptions du créneau (payées ou non — une place réservée dès
        # l'inscription) ; l'archer courant n'y est pas (l'unicité vient d'être vérifiée), donc
        # `len >= quota` bloque bien la place *quota + 1*, pas une de trop.
        if depart.quota is not None:
            inscrits = len(self._inscriptions.par_depart(depart_id))
            if inscrits >= depart.quota:
                raise DepartComplet(
                    f"Le départ n° {depart.numero} est complet "
                    f"({depart.quota} inscrit{'s' if depart.quota > 1 else ''} maximum)."
                )
        inscription = self._inscriptions.ajouter(Inscription.creer(archer_id, depart_id))
        return InscriptionDetaillee(inscription, depart)

    def lister_par_archer(self, archer_id: ArcherId) -> list[InscriptionDetaillee]:
        """Renvoie les inscriptions d'un archer, avec leur montant, triées par n° de départ.

        Lève `ArcherIntrouvable` si l'archer n'existe pas — un archer inconnu n'a pas « zéro
        inscription », il n'existe pas.
        """
        self._archer_existant(archer_id)
        detaillees = []
        for inscription in self._inscriptions.par_archer(archer_id):
            depart = self._departs.par_id(inscription.depart_id)
            # Lecture **hors file d'écriture**, en sessions séparées (règle 7) : entre le
            # `par_archer` ci-dessus et ce `par_id`, une autre tablette peut avoir confirmé la
            # suppression du départ, qui purge ses inscriptions en cascade. L'inscription lue est
            # alors le vestige d'un instantané périmé — on l'**ignore** (un re-fetch rendra la liste
            # cohérente, plus courte) au lieu d'asserter : un `assert` saute sous `python -O`, et
            # l'on déréférencerait alors `None.tarif_centimes` → 500 (fuite non typée, règle 5).
            if depart is None:
                continue
            detaillees.append(InscriptionDetaillee(inscription, depart))
        return sorted(detaillees, key=lambda d: d.depart.numero)

    def montant_du_par_archer(self, archer_id: ArcherId) -> int:
        """Montant total dû par un archer = **somme des tarifs** de ses créneaux (E08US001).

        Dérivé à la lecture, jamais stocké (ADR-0017) : délègue à `lister_par_archer`, donc suit
        tout changement de tarif **ou** d'inscription, et ignore de la même façon une inscription
        dont le départ vient d'être purgé en cascade — le total compte **exactement** les créneaux
        que la liste montre, jamais un de plus. C'est une **somme**, pas un tarif unique multiplié
        par le nombre de créneaux : les prix diffèrent par créneau (ADR-0017). Lève
        `ArcherIntrouvable` si l'archer n'existe pas — un archer inconnu ne « doit » rien, il
        n'existe pas (patron `lister_par_archer`).
        """
        return sum(detail.montant_du_centimes for detail in self.lister_par_archer(archer_id))

    def desinscrire(self, inscription_id: InscriptionId, confirme: bool = False) -> None:
        """Désinscrit un archer d'un départ. Lève `InscriptionIntrouvable` si elle n'existe pas.

        Une inscription **non payée** (ou d'un créneau **gratuit**) se désinscrit **librement**
        (comportement E02US009 inchangé). Une inscription **payée** d'un créneau **tarifé** efface
        une somme encaissée : elle est **confirmable** (E08US005, ADR-0057). Tant que `confirme` est
        faux, lève `InscriptionPayeeARembourser` (409) — `details` chiffre le montant et nomme
        l'archer. Confirmée, la désinscription **supprime l'inscription ET ouvre le remboursement en
        une transaction** (`supprimer_avec_remboursement`) : jamais de somme effacée sans
        contrepartie (le but de l'US), jamais de remboursement en double.

        Le créneau peut avoir disparu (vestige d'un instantané périmé, purge en cascade concurrente)
        ou l'archer être introuvable : dans ces cas on ne peut/doit pas ouvrir de remboursement — on
        retombe sur la suppression simple (le départ détruit a déjà ouvert ses propres
        remboursements par son propre chemin).
        """
        inscription = self._inscription_existante(inscription_id)
        assert inscription.id is not None, "Une inscription relue est persistée."
        depart = self._departs.par_id(inscription.depart_id)
        archer = self._archers.par_id(inscription.archer_id)
        a_rembourser = (
            inscription.paye
            and depart is not None
            and depart.tarif_centimes > 0
            and archer is not None
        )
        if not a_rembourser:
            self._inscriptions.supprimer(inscription.id)
            return
        assert depart is not None and archer is not None  # garanti par `a_rembourser`
        if not confirme:
            raise InscriptionPayeeARembourser(
                f"« {archer.prenom} {archer.nom} » a réglé le départ n° {depart.numero} : le "
                "désinscrire ouvrira un remboursement. Confirmez seulement si c'est voulu.",
                montant_centimes=depart.tarif_centimes,
                archer=f"{archer.prenom} {archer.nom}",
            )
        remboursement = Remboursement.creer(
            archer.tournoi_id,
            archer_prenom=archer.prenom,
            archer_nom=archer.nom,
            creneau=_libelle_creneau(depart),
            # DETTE-016 : montant = tarif **courant** du départ, pas la somme réellement encaissée
            # (le modèle ne stocke que le booléen `paye`) — faux si le tarif a bougé après paiement.
            montant_centimes=depart.tarif_centimes,
            motif=MotifRemboursement.DESINSCRIPTION,
            cree_le=self._horloge.maintenant(),
        )
        self._inscriptions.supprimer_avec_remboursement(inscription.id, remboursement)

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


def _libelle_creneau(depart: Depart) -> str:
    """Instantané textuel d'un créneau pour un remboursement (E08US005) : « Départ n°3 — 09:00 ».

    Figé au moment de l'effacement — le remboursement doit survivre à la disparition du départ, il
    ne peut pas suivre une FK vers une ligne partie (ADR-0057). Dupliqué à l'identique dans
    `ServiceDeparts` (2ᵉ occurrence assumée, pas de constante partagée — règle 12).
    """
    return f"Départ n°{depart.numero} — {depart.horaire}"
