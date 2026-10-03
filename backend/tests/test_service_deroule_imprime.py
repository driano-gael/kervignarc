"""Tests du service `ServiceDerouleImprime` (E09US007).

Écrits **depuis le CA** de `stories/E09-exports.md` (cadrage du 03/10/2026), avant
l'implémentation (règle 9). Ce que le service ajoute au domaine (`test_domain_deroule_imprime.py`) :

- « un seul PDF pour le tournoi, **un bloc par départ** » ; un paramètre restreint à **un** départ ;
- les heures sont **celles d'E03US010** — chaque départ rejoue le déroulé à sa propre heure ;
- **PDF seul**, par le registre de formats (ADR-0101) ;
- un tournoi sans départ se refuse ; un déroulé vide rend des blocs sans ligne.
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.deroule_imprime import ServiceDerouleImprime
from application.erreurs import (
    DepartIntrouvable,
    FormatExportIndisponible,
    TournoiIntrouvable,
    TournoiSansDepart,
)
from application.exports import FormatExport, RegistreDeFormats
from application.phases import ServicePhases
from application.verrou_bareme import VerrouBaremeDuel
from domain.depart import Depart
from domain.deroule_etape import EtapeDeroule
from domain.deroule_imprime import DerouleImprime
from domain.duel import ResolveurBaremeDuelFfta
from domain.horaire_prevu import HeurePrevue
from domain.phase import SourcePhase, TypePhase
from domain.tournoi import Tournoi
from tests.conftest import (
    FauxDepartRepository,
    FauxDerouleRepository,
    FauxDuelRepository,
    FauxPhaseRepository,
)
from tests.test_service_phases import FauxTournoiRepository

_DATE = datetime.date(2026, 3, 14)


class _GenerateurEspion:
    def __init__(self) -> None:
        self.recu: DerouleImprime | None = None

    def deroule_horaire(self, document: DerouleImprime) -> bytes:
        self.recu = document
        return b"%PDF-espion"


class _Decor:
    """Un tournoi à deux créneaux (09:00 et 14:00) ; un déroulé qualification → tableau."""

    def __init__(self, *, avec_departs: bool = True, avec_deroule: bool = True) -> None:
        self.tournois = FauxTournoiRepository()
        tournoi = self.tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
        autre = self.tournois.ajouter(Tournoi.creer("Autre", _DATE))
        assert tournoi.id is not None and autre.id is not None
        self.tournoi_id = tournoi.id
        self.departs = FauxDepartRepository()
        self.ids_departs: list[int] = []
        if avec_departs:
            for numero, horaire, ident in ((1, "09:00", 501), (2, "14:00", 502)):
                self.departs.ajouter(
                    dataclasses.replace(
                        Depart.creer(
                            tournoi_id=tournoi.id,
                            numero=numero,
                            tarif_centimes=800,
                            horaire=horaire,
                        ),
                        id=ident,
                    )
                )
                self.ids_departs.append(ident)
        autre_depart = self.departs.ajouter(
            dataclasses.replace(
                Depart.creer(tournoi_id=autre.id, numero=1, tarif_centimes=800, horaire="10:00"),
                id=900,
            )
        )
        self.depart_autre_tournoi = autre_depart.id
        deroules = FauxDerouleRepository()
        if avec_deroule:
            qualif = deroules.ajouter(
                EtapeDeroule(
                    tournoi_id=tournoi.id,
                    ordre=1,
                    type=TypePhase.ECHAUFFEMENT,
                    duree_prevue=60,
                )
            )
            assert qualif.id is not None
            deroules.ajouter(
                EtapeDeroule(
                    tournoi_id=tournoi.id,
                    ordre=2,
                    type=TypePhase.ELIMINATION_DIRECTE,
                    titre="Tableau",
                    sources=(SourcePhase.par_rangs(qualif.id),),
                    duree_prevue=90,
                )
            )
        phases_repo = FauxPhaseRepository(self.departs, deroules)
        verrou = VerrouBaremeDuel(
            self.departs, phases_repo, deroules, FauxDuelRepository(), ResolveurBaremeDuelFfta()
        )
        self.phases = ServicePhases(self.tournois, phases_repo, self.departs, deroules, verrou)
        self.espion = _GenerateurEspion()
        self.service = ServiceDerouleImprime(
            tournois=self.tournois,
            phases=self.phases,
            generateurs=RegistreDeFormats({FormatExport.PDF: self.espion}),
        )


# --- CA 1 : un bloc par départ, ou un seul -------------------------------------------------------


def test_un_bloc_par_depart_dans_l_ordre_des_departs() -> None:
    decor = _Decor()

    document = decor.service.document(decor.tournoi_id)

    assert document.tournoi == "Salle 18m"
    assert [bloc.libelle for bloc in document.blocs] == [
        "Départ n°1 — 09:00",
        "Départ n°2 — 14:00",
    ]


def test_chaque_depart_rejoue_le_deroule_a_sa_propre_heure() -> None:
    """CA 2 : les heures sont celles d'E03US010, calculées depuis l'heure du créneau."""
    decor = _Decor()

    matin, apres_midi = decor.service.document(decor.tournoi_id).blocs

    assert [(ligne.debut, ligne.fin) for ligne in matin.lignes] == [
        (HeurePrevue(9 * 60), HeurePrevue(10 * 60)),
        (HeurePrevue(10 * 60), HeurePrevue(11 * 60 + 30)),
    ]
    assert apres_midi.lignes[0].debut == HeurePrevue(14 * 60)
    assert apres_midi.lignes[1].titre == "Tableau"


def test_un_seul_depart_sur_demande() -> None:
    decor = _Decor()

    document = decor.service.document(decor.tournoi_id, decor.ids_departs[1])

    assert [bloc.libelle for bloc in document.blocs] == ["Départ n°2 — 14:00"]


def test_un_depart_d_un_autre_tournoi_est_introuvable() -> None:
    decor = _Decor()

    with pytest.raises(DepartIntrouvable):
        decor.service.document(decor.tournoi_id, decor.depart_autre_tournoi)
    with pytest.raises(DepartIntrouvable):
        decor.service.document(decor.tournoi_id, 12345)


# --- Refus et cas vides --------------------------------------------------------------------------


def test_un_tournoi_inconnu_est_refuse() -> None:
    decor = _Decor()

    with pytest.raises(TournoiIntrouvable):
        decor.service.document(999)


def test_un_tournoi_sans_depart_n_a_rien_a_imprimer() -> None:
    decor = _Decor(avec_departs=False)

    with pytest.raises(TournoiSansDepart):
        decor.service.document(decor.tournoi_id)


def test_un_deroule_vide_rend_des_blocs_sans_ligne() -> None:
    decor = _Decor(avec_deroule=False)

    document = decor.service.document(decor.tournoi_id)

    assert len(document.blocs) == 2
    assert all(bloc.lignes == () for bloc in document.blocs)


# --- CA 4 : PDF seul, par le registre ------------------------------------------------------------


def test_le_pdf_passe_par_le_generateur_du_registre() -> None:
    decor = _Decor()

    octets = decor.service.imprimer(decor.tournoi_id)

    assert octets == b"%PDF-espion"
    assert decor.espion.recu == decor.service.document(decor.tournoi_id)


def test_seul_le_pdf_est_publie() -> None:
    decor = _Decor()

    assert decor.service.formats_disponibles == (FormatExport.PDF,)
    with pytest.raises(FormatExportIndisponible):
        decor.service.imprimer(decor.tournoi_id, format_=FormatExport.CSV)
