"""Tests du service applicatif Paiements (E08US002) — repositories factices, dérivés du **CA**.

Source : `stories/E08-paiements.md`, E08US002, ses trois puces CA (« statut », « vue par archer »,
« vue par club ») **et** ses deux arbitrages reversés au § Notes (marquage groupé archer + club ;
audit de chaque marquage). On y vérifie ce qui est propre au service : dériver les récapitulatifs de
paiement (dû/payé/reste) par archer et par club, regrouper les archers sans club (ADR-0014), et
**basculer** le statut — simple ou groupé — en **consignant une trace** (capturée par le faux
repository).
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.erreurs import (
    ArcherIntrouvable,
    ClubIntrouvable,
    InscriptionIntrouvable,
    TournoiIntrouvable,
)
from application.paiements import LIBELLE_SANS_CLUB, ServicePaiements
from domain.archer import Archer, ArcherId
from domain.club import Club, ClubId
from domain.depart import Depart, DepartId
from domain.entree_audit import ActionAuditee
from domain.inscription import Inscription
from domain.tournoi import Tournoi, TournoiId
from tests.conftest import (
    FauxArcherRepository,
    FauxClubRepository,
    FauxDepartRepository,
    FauxInscriptionRepository,
)

_TOURNOI = 1
_QUAND = datetime.datetime(2026, 7, 21, 9, 30, tzinfo=datetime.UTC)


class FauxTournoiRepository:
    """Repository de tournois en mémoire conforme au port `TournoiRepository`."""

    def __init__(self) -> None:
        self._tournois: dict[int, Tournoi] = {}
        self._sequence = 0

    def ajouter(self, tournoi: Tournoi) -> Tournoi:
        self._sequence += 1
        persiste = dataclasses.replace(tournoi, id=self._sequence)
        self._tournois[self._sequence] = persiste
        return persiste

    def par_id(self, tournoi_id: TournoiId) -> Tournoi | None:
        return self._tournois.get(tournoi_id)

    def lister(self) -> list[Tournoi]:
        return list(self._tournois.values())

    def enregistrer(self, tournoi: Tournoi) -> Tournoi:
        assert tournoi.id in self._tournois, "Tournoi à mettre à jour absent."
        self._tournois[tournoi.id] = tournoi
        return tournoi

    def supprimer(self, tournoi_id: TournoiId) -> None:
        del self._tournois[tournoi_id]


class HorlogeFigee:
    """Horloge déterministe conforme au port `Horloge` (règle 9) : toujours le même instant."""

    def __init__(self, instant: datetime.datetime) -> None:
        self._instant = instant

    def maintenant(self) -> datetime.datetime:
        return self._instant


class Montage:
    """Décor d'un test de paiements : le service et les fakes à garnir à la main."""

    def __init__(self) -> None:
        self.tournois = FauxTournoiRepository()
        self.archers = FauxArcherRepository()
        self.departs = FauxDepartRepository()
        self.inscriptions = FauxInscriptionRepository()
        self.clubs = FauxClubRepository()
        self.tournois.ajouter(Tournoi.creer("Tournoi", datetime.date(2026, 3, 14)))
        self.service = ServicePaiements(
            self.tournois,
            self.archers,
            self.departs,
            self.inscriptions,
            self.clubs,
            HorlogeFigee(_QUAND),
        )

    def club(self, nom: str) -> ClubId:
        club = self.clubs.ajouter(Club(nom=nom))
        assert club.id is not None
        return club.id

    def archer(self, nom: str, prenom: str, club_id: ClubId | None = None) -> ArcherId:
        archer = self.archers.ajouter(
            Archer.creer(nom, prenom, _TOURNOI, categorie_id=1, club_id=club_id)
        )
        assert archer.id is not None
        return archer.id

    def depart(self, numero: int, tarif_centimes: int) -> DepartId:
        depart = self.departs.ajouter(Depart.creer(_TOURNOI, numero, tarif_centimes))
        assert depart.id is not None
        return depart.id

    def inscrire(self, archer_id: ArcherId, depart_id: DepartId, paye: bool = False) -> int:
        """Inscrit directement (le service Inscriptions est testé ailleurs) ; renvoie l'id."""
        inscription = self.inscriptions.ajouter(
            Inscription(archer_id=archer_id, depart_id=depart_id, paye=paye)
        )
        assert inscription.id is not None
        return inscription.id

    def est_paye(self, inscription_id: int) -> bool:
        """Relit le statut de paiement d'une inscription (garde le `None` hors du chemin mypy)."""
        inscription = self.inscriptions.par_id(inscription_id)
        assert inscription is not None
        return inscription.paye


# --- Vue par archer (CA « liste des archers avec dû / payé / reste ») --------------------------


def test_vue_par_archer_derive_du_paye_reste() -> None:
    """Chaque archer porte dû (somme des tarifs), payé (tarifs payés) et reste = dû - payé."""
    m = Montage()
    archer = m.archer("Robin", "Jean")
    m.inscrire(archer, m.depart(1, 810), paye=True)
    m.inscrire(archer, m.depart(2, 1000), paye=False)

    (ligne,) = m.service.lister_par_archer(_TOURNOI)
    assert (ligne.recap.du_centimes, ligne.recap.paye_centimes, ligne.recap.reste_centimes) == (
        1810,
        810,
        1000,
    )


def test_vue_par_archer_inclut_les_archers_sans_inscription() -> None:
    """Un archer inscrit sur aucun créneau figure quand même, à 0 (CA — il est du tournoi)."""
    m = Montage()
    m.archer("Sansdepart", "Zoe")

    (ligne,) = m.service.lister_par_archer(_TOURNOI)
    assert ligne.recap.du_centimes == 0
    assert ligne.recap.reste_centimes == 0


def test_vue_par_archer_triee_par_nom_puis_prenom() -> None:
    """La liste est ordonnée par nom puis prénom (casse repliée), ordre d'affichage stable."""
    m = Montage()
    m.archer("Zephir", "Alice")
    m.archer("archer", "Bob")  # minuscule : le tri replie la casse
    m.archer("Archer", "Anne")

    noms = [(ligne.nom, ligne.prenom) for ligne in m.service.lister_par_archer(_TOURNOI)]
    assert noms == [("Archer", "Anne"), ("archer", "Bob"), ("Zephir", "Alice")]


def test_vue_par_archer_tournoi_inconnu_leve() -> None:
    """Consulter un tournoi inexistant lève `TournoiIntrouvable` (404), pas une liste vide."""
    m = Montage()
    with pytest.raises(TournoiIntrouvable):
        m.service.lister_par_archer(404)


# --- Vue par club (CA « totaux par club ; détail des archers du club ») ------------------------


def test_vue_par_club_agrege_les_totaux_et_detaille_les_archers() -> None:
    """Un club porte le total dû/payé/reste de ses archers, et la liste de ses archers (CA)."""
    m = Montage()
    club_id = m.club("Arc Rennes")
    a = m.archer("Un", "Alice", club_id)
    b = m.archer("Deux", "Bob", club_id)
    m.inscrire(a, m.depart(1, 810), paye=True)
    m.inscrire(b, m.depart(2, 1000), paye=False)

    (recap_club,) = m.service.recap_par_club(_TOURNOI)
    assert recap_club.club_id == club_id
    assert recap_club.nom == "Arc Rennes"
    assert (recap_club.recap.du_centimes, recap_club.recap.paye_centimes) == (1810, 810)
    assert recap_club.recap.reste_centimes == 1000
    assert {a_.prenom for a_ in recap_club.archers} == {"Alice", "Bob"}


def test_vue_par_club_regroupe_les_sans_club_en_dernier() -> None:
    """Les archers sans club (`club_id` NULL, ADR-0014) forment un bucket `Sans club`, placé après.

    Preuve que la somme des groupes retombe sur le tournoi : on ne perd pas les archers non
    rattachés.
    """
    m = Montage()
    club_id = m.club("Arc Rennes")
    m.inscrire(m.archer("Club", "Cyril", club_id), m.depart(1, 500), paye=False)
    m.inscrire(m.archer("Orphelin", "Olga", None), m.depart(2, 700), paye=True)

    recaps = m.service.recap_par_club(_TOURNOI)
    assert [r.nom for r in recaps] == ["Arc Rennes", LIBELLE_SANS_CLUB]
    sans_club = recaps[-1]
    assert sans_club.club_id is None
    assert sans_club.recap.du_centimes == 700


# --- Marquage simple (CA « statut modifiable ») + audit (arbitrage) ----------------------------


def test_marquer_inscription_bascule_le_statut() -> None:
    """Marquer une inscription bascule `paye` ; le montant (dérivé) ne bouge pas."""
    m = Montage()
    inscription_id = m.inscrire(m.archer("Robin", "Jean"), m.depart(1, 810))

    detail = m.service.marquer_inscription(inscription_id, True)
    assert detail.inscription.paye is True
    assert detail.montant_du_centimes == 810
    assert m.service.marquer_inscription(inscription_id, False).inscription.paye is False


def test_marquer_inscription_consigne_une_trace_de_paiement() -> None:
    """Marquer un paiement laisse **une** trace d'audit `PAIEMENT` (arbitrage — mouvement d'argent).

    La trace garde le statut avant/après (valeur de preuve) et l'auteur admin ; elle est datée par
    l'horloge injectée (déterminisme).
    """
    m = Montage()
    inscription_id = m.inscrire(m.archer("Robin", "Jean"), m.depart(1, 810), paye=False)

    m.service.marquer_inscription(inscription_id, True)

    (trace,) = m.inscriptions.traces
    assert trace.action is ActionAuditee.PAIEMENT
    assert trace.auteur == "Administrateur"
    assert trace.avant == "non payé"
    assert trace.apres == "payé"
    assert trace.horodatage == _QUAND
    assert trace.tournoi_id == _TOURNOI


def test_marquer_inscription_inconnue_leve() -> None:
    """Marquer une inscription inexistante lève `InscriptionIntrouvable` (404)."""
    m = Montage()
    with pytest.raises(InscriptionIntrouvable):
        m.service.marquer_inscription(404, True)


# --- Marquage groupé par archer (arbitrage — règlements groupés) -------------------------------


def test_marquer_archer_marque_toutes_ses_inscriptions() -> None:
    """Un geste marque **tous** les créneaux d'un archer, et laisse **une seule** trace groupée."""
    m = Montage()
    archer = m.archer("Robin", "Jean")
    i1 = m.inscrire(archer, m.depart(1, 810), paye=False)
    i2 = m.inscrire(archer, m.depart(2, 1000), paye=False)

    ligne = m.service.marquer_archer(_TOURNOI, archer, True)

    assert m.est_paye(i1) is True
    assert m.est_paye(i2) is True
    assert ligne.recap.paye_centimes == 1810  # tout payé → reste 0
    assert ligne.recap.reste_centimes == 0
    assert len(m.inscriptions.traces) == 1
    assert m.inscriptions.traces[0].action is ActionAuditee.PAIEMENT


def test_marquer_archer_sans_inscription_est_un_noop_sans_trace() -> None:
    """Marquer un archer sans créneau ne bascule rien et ne trace rien (aucun mouvement)."""
    m = Montage()
    archer = m.archer("Vide", "Vera")

    ligne = m.service.marquer_archer(_TOURNOI, archer, True)
    assert ligne.recap.du_centimes == 0
    assert m.inscriptions.traces == []


def test_marquer_archer_d_un_autre_tournoi_leve() -> None:
    """Marquer un archer inexistant (ou d'un autre tournoi) lève `ArcherIntrouvable`."""
    m = Montage()
    with pytest.raises(ArcherIntrouvable):
        m.service.marquer_archer(_TOURNOI, 404, True)


# --- Marquage groupé par club (arbitrage — règlements groupés) ---------------------------------


def test_marquer_club_marque_les_inscriptions_de_ses_archers() -> None:
    """Marquer un club bascule les inscriptions de **ses** archers, en une trace ; renvoie le total.

    Un archer d'un **autre** club du même tournoi n'est pas touché (le périmètre est le club).
    """
    m = Montage()
    club_id = m.club("Arc Rennes")
    autre_club = m.club("Arc Brest")
    a = m.archer("Un", "Alice", club_id)
    b = m.archer("Deux", "Bob", club_id)
    etranger = m.archer("Trois", "Chloe", autre_club)
    i_a = m.inscrire(a, m.depart(1, 810), paye=False)
    i_b = m.inscrire(b, m.depart(2, 1000), paye=False)
    i_etranger = m.inscrire(etranger, m.depart(3, 500), paye=False)

    recap_club = m.service.marquer_club(_TOURNOI, club_id, True)

    assert m.est_paye(i_a) is True
    assert m.est_paye(i_b) is True
    assert m.est_paye(i_etranger) is False  # autre club, intact
    assert recap_club.recap.reste_centimes == 0
    assert len(m.inscriptions.traces) == 1


def test_marquer_club_inconnu_leve() -> None:
    """Marquer un club inexistant lève `ClubIntrouvable` (404)."""
    m = Montage()
    with pytest.raises(ClubIntrouvable):
        m.service.marquer_club(_TOURNOI, 404, True)
