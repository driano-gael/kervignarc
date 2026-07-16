"""Tests du service applicatif Inscriptions (E02US009, ADR-0017) — repositories factices.

Le service est testé **en isolation** : de faux repositories en mémoire (conformes aux ports)
suffisent. On y vérifie ce qui lui est propre — les règles inter-agrégats que l'entité `Inscription`
(mince) ne peut pas porter : inscrire sur un départ **du tournoi de l'archer**, refuser un
**doublon** de couple, **dériver** le montant du tarif du départ, basculer `payé`, désinscrire.
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.erreurs import (
    ArcherIntrouvable,
    DejaInscrit,
    DepartIntrouvable,
    InscriptionIntrouvable,
)
from application.inscriptions import ServiceInscriptions
from domain.archer import Archer, ArcherId
from domain.depart import Depart, DepartId
from domain.tournoi import TournoiId
from tests.conftest import (
    FauxArcherRepository,
    FauxDepartRepository,
    FauxInscriptionRepository,
)

_DATE = datetime.date(2026, 3, 14)
_TOURNOI = 1


def _monter() -> (
    tuple[
        ServiceInscriptions, FauxArcherRepository, FauxDepartRepository, FauxInscriptionRepository
    ]
):
    archers = FauxArcherRepository()
    departs = FauxDepartRepository()
    inscriptions = FauxInscriptionRepository()
    return ServiceInscriptions(inscriptions, archers, departs), archers, departs, inscriptions


def _archer(archers: FauxArcherRepository, tournoi_id: TournoiId = _TOURNOI) -> ArcherId:
    """Persiste un archer minimal (catégorie non validée par ce service) ; renvoie son id."""
    archer = archers.ajouter(Archer.creer("Robin", "Jean", tournoi_id, categorie_id=1))
    assert archer.id is not None
    return archer.id


def _depart(
    departs: FauxDepartRepository,
    tarif_centimes: int = 810,
    numero: int = 1,
    tournoi_id: TournoiId = _TOURNOI,
) -> DepartId:
    """Persiste un départ ; renvoie son id."""
    depart = departs.ajouter(Depart.creer(tournoi_id, numero, tarif_centimes))
    assert depart.id is not None
    return depart.id


def test_inscrire_cree_un_lien_non_paye_avec_montant_derive() -> None:
    """Inscrire crée une inscription **non payée** dont le montant dû est le tarif du départ."""
    service, archers, departs, _ = _monter()
    archer_id = _archer(archers)
    depart_id = _depart(departs, tarif_centimes=810)

    detail = service.inscrire(archer_id, depart_id)
    assert detail.inscription.archer_id == archer_id
    assert detail.inscription.depart_id == depart_id
    assert detail.inscription.paye is False
    assert detail.montant_du_centimes == 810


def test_inscrire_archer_inconnu_leve() -> None:
    """Inscrire un archer inexistant lève `ArcherIntrouvable`."""
    service, _, departs, _ = _monter()
    depart_id = _depart(departs)
    with pytest.raises(ArcherIntrouvable):
        service.inscrire(404, depart_id)


def test_inscrire_depart_inconnu_leve() -> None:
    """Inscrire sur un départ inexistant lève `DepartIntrouvable`."""
    service, archers, _, _ = _monter()
    archer_id = _archer(archers)
    with pytest.raises(DepartIntrouvable):
        service.inscrire(archer_id, 404)


def test_inscrire_depart_d_un_autre_tournoi_leve() -> None:
    """Un départ d'un **autre tournoi** est introuvable du point de vue de l'archer (CA E02US009).

    Même parti que `CategorieHorsTournoi`/`DepartIntrouvable` : on ne fuite pas les voisins, et
    surtout on n'inscrit pas un archer sur un tournoi qui n'est pas le sien.
    """
    service, archers, departs, _ = _monter()
    archer_id = _archer(archers, tournoi_id=_TOURNOI)
    depart_etranger = _depart(departs, tournoi_id=2)
    with pytest.raises(DepartIntrouvable):
        service.inscrire(archer_id, depart_etranger)


def test_inscrire_deux_fois_le_meme_couple_leve() -> None:
    """Un second lien `(archer, départ)` n'a aucun sens → `DejaInscrit` (CA E02US009)."""
    service, archers, departs, _ = _monter()
    archer_id = _archer(archers)
    depart_id = _depart(departs)
    service.inscrire(archer_id, depart_id)
    with pytest.raises(DejaInscrit):
        service.inscrire(archer_id, depart_id)


def test_inscrire_le_meme_archer_sur_deux_departs_passe() -> None:
    """Un archer s'inscrit sur **plusieurs** créneaux — c'est tout l'objet de l'US."""
    service, archers, departs, _ = _monter()
    archer_id = _archer(archers)
    premier = _depart(departs, numero=1)
    second = _depart(departs, numero=2)
    service.inscrire(archer_id, premier)
    service.inscrire(archer_id, second)
    assert [d.inscription.depart_id for d in service.lister_par_archer(archer_id)] == [
        premier,
        second,
    ]


def test_inscrire_deux_archers_sur_le_meme_depart_passe() -> None:
    """Un créneau est **partagé** : deux archers peuvent s'y inscrire (ADR-0017)."""
    service, archers, departs, _ = _monter()
    un = _archer(archers)
    autre = archers.ajouter(Archer.creer("Martin", "Alice", _TOURNOI, categorie_id=1))
    assert autre.id is not None
    depart_id = _depart(departs)
    service.inscrire(un, depart_id)
    service.inscrire(autre.id, depart_id)
    assert len(service.lister_par_archer(un)) == 1
    assert len(service.lister_par_archer(autre.id)) == 1


def test_lister_par_archer_trie_par_numero_de_depart() -> None:
    """`lister_par_archer` renvoie les inscriptions triées par n° de créneau, avec leur montant."""
    service, archers, departs, _ = _monter()
    archer_id = _archer(archers)
    tardif = _depart(departs, tarif_centimes=1000, numero=2)
    matinal = _depart(departs, tarif_centimes=810, numero=1)
    service.inscrire(archer_id, tardif)
    service.inscrire(archer_id, matinal)

    lignes = service.lister_par_archer(archer_id)
    assert [d.depart.numero for d in lignes] == [1, 2]
    assert [d.montant_du_centimes for d in lignes] == [810, 1000]


def test_lister_par_archer_inconnu_leve() -> None:
    """Lister les inscriptions d'un archer inexistant lève `ArcherIntrouvable`."""
    service, _, _, _ = _monter()
    with pytest.raises(ArcherIntrouvable):
        service.lister_par_archer(404)


def test_lister_par_archer_ignore_une_inscription_dont_le_depart_a_disparu() -> None:
    """Un départ purgé en cascade **pendant** la lecture ne provoque pas de 500 (revue E02US009).

    `lister_par_archer` lit hors file d'écriture, en sessions séparées : entre le relevé des
    inscriptions et la relecture d'un départ, une autre tablette peut confirmer la suppression du
    créneau (qui purge ses inscriptions). L'inscription relue est alors un vestige d'un instantané
    périmé — le service l'**ignore** au lieu d'asserter (sinon 500, et déréférencement de `None`
    sous `python -O`). On simule la course en supprimant le départ dans son magasin tout en
    laissant l'inscription orpheline (le faux magasin d'inscriptions ne cascade pas, à dessein).
    """
    service, archers, departs, inscriptions = _monter()
    archer_id = _archer(archers)
    present = _depart(departs, numero=1)
    disparu = _depart(departs, numero=2)
    service.inscrire(archer_id, present)
    service.inscrire(archer_id, disparu)

    departs.supprimer(disparu)  # course : le départ part, l'inscription reste orpheline

    lignes = service.lister_par_archer(archer_id)
    assert [d.depart.numero for d in lignes] == [1]  # l'orpheline est filtrée, pas de levée


def test_montant_du_suit_le_tarif_du_depart_sans_etre_stocke() -> None:
    """Le montant se **dérive** : changer le tarif du départ change le montant lu (CA E02US009).

    Preuve qu'il n'est pas recopié à l'inscription — l'erreur que la v0.3 du modèle faisait en
    posant `montant_du` sur `DEPART`. Ici on modifie le tarif après coup et la lecture suit.
    """
    service, archers, departs, _ = _monter()
    archer_id = _archer(archers)
    depart_id = _depart(departs, tarif_centimes=810)
    service.inscrire(archer_id, depart_id)

    depart = departs.par_id(depart_id)
    assert depart is not None
    departs.enregistrer(dataclasses.replace(depart, tarif_centimes=1250))

    assert service.lister_par_archer(archer_id)[0].montant_du_centimes == 1250


def test_marquer_paye_bascule_le_statut_sans_changer_le_montant() -> None:
    """`marquer_paye` bascule `payé` ; le montant dû (dérivé du tarif) ne bouge pas."""
    service, archers, departs, _ = _monter()
    archer_id = _archer(archers)
    depart_id = _depart(departs, tarif_centimes=810)
    inscription = service.inscrire(archer_id, depart_id).inscription
    assert inscription.id is not None

    detail = service.marquer_paye(inscription.id, True)
    assert detail.inscription.paye is True
    assert detail.montant_du_centimes == 810
    assert service.marquer_paye(inscription.id, False).inscription.paye is False


def test_marquer_paye_inscription_inconnue_leve() -> None:
    """Marquer payé une inscription inexistante lève `InscriptionIntrouvable`."""
    service, _, _, _ = _monter()
    with pytest.raises(InscriptionIntrouvable):
        service.marquer_paye(404, True)


def test_desinscrire_retire_le_lien() -> None:
    """Désinscrire est **libre** (inverse de l'inscription) : le lien disparaît."""
    service, archers, departs, _ = _monter()
    archer_id = _archer(archers)
    depart_id = _depart(departs)
    inscription = service.inscrire(archer_id, depart_id).inscription
    assert inscription.id is not None

    service.desinscrire(inscription.id)
    assert service.lister_par_archer(archer_id) == []


def test_desinscrire_inconnue_leve() -> None:
    """Désinscrire une inscription inexistante lève `InscriptionIntrouvable`."""
    service, _, _, _ = _monter()
    with pytest.raises(InscriptionIntrouvable):
        service.desinscrire(404)
