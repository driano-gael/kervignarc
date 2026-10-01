"""Tests du service `ServiceClassementImprime` (E09US005).

Écrits **depuis le CA** de `stories/E09-exports.md`, avant l'implémentation (règle 9). Ce que le
service ajoute au domaine (`test_domain_classement_imprime.py`) :

- « un document **par départ** — tous les départs à la suite, ou un seul choisi » ;
- « même calcul que l'écran » : les lignes sont celles de `ServiceClassement.pour_depart` ;
- « provisoire » se juge **départ par départ** ;
- le club s'imprime par son **nom** ;
- les formats PDF, CSV et Excel passent par le registre (ADR-0101).
"""

from __future__ import annotations

import datetime

import pytest

from application.classement_imprime import ServiceClassementImprime
from application.classements import ServiceClassement
from application.erreurs import DepartIntrouvable, TournoiIntrouvable, TournoiSansDepart
from application.exports import FormatExport, RegistreDeFormats
from domain.archer import Archer
from domain.bareme import BaremeQualification
from domain.blason import ZoneScore
from domain.categorie import Categorie
from domain.classement_imprime import ClassementQualificationImprime
from domain.club import Club
from domain.depart import Depart
from domain.inscription import Inscription
from domain.phase import Phase
from domain.serie import Serie, Volee
from domain.tournoi import Tournoi
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxClubRepository,
    FauxDepartRepository,
    FauxForfaitRepository,
    FauxInscriptionRepository,
    FauxPhaseRepository,
    FauxTournoiRepository,
)
from tests.test_service_classement import FauxSerieRepository

_DATE = datetime.date(2026, 3, 14)


class _GenerateurEspion:
    """Double du port : retient le document reçu et rend des octets marqués par son format."""

    def __init__(self, marque: bytes) -> None:
        self._marque = marque
        self.recu: ClassementQualificationImprime | None = None

    def classement_qualification(self, document: ClassementQualificationImprime) -> bytes:
        self.recu = document
        return self._marque


class _Decor:
    """Un tournoi, deux créneaux de deux archers chacun, barème de 2 volées.

    Le matin est **terminé** (toutes les volées validées), l'après-midi **en cours** (une volée
    manque) — de quoi distinguer le provisoire départ par départ.
    """

    def __init__(self) -> None:
        self.tournois = FauxTournoiRepository()
        tournoi = self.tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
        assert tournoi.id is not None
        self.tournoi_id = tournoi.id
        autre = self.tournois.ajouter(Tournoi.creer("Autre", _DATE))
        assert autre.id is not None
        self.autre_tournoi_id = autre.id

        self.clubs = FauxClubRepository()
        club = self.clubs.ajouter(Club.creer("Compagnie de Kervignarc"))
        assert club.id is not None

        self.categories = FauxCategorieRepository()
        senior = self.categories.ajouter(Categorie.creer(self.tournoi_id, "Senior Homme"))
        cadet = self.categories.ajouter(Categorie.creer(self.tournoi_id, "Cadet"))
        assert senior.id is not None and cadet.id is not None

        self.archers = FauxArcherRepository()
        self.departs = FauxDepartRepository()
        self.inscriptions = FauxInscriptionRepository()
        self.phases = FauxPhaseRepository(self.departs)
        series: list[Serie] = []

        matin = self.departs.ajouter(
            Depart.creer(tournoi_id=self.tournoi_id, numero=1, tarif_centimes=800, horaire="09:00")
        )
        apres_midi = self.departs.ajouter(
            Depart.creer(tournoi_id=self.tournoi_id, numero=2, tarif_centimes=800, horaire="14:00")
        )
        ailleurs = self.departs.ajouter(
            Depart.creer(
                tournoi_id=self.autre_tournoi_id, numero=1, tarif_centimes=800, horaire="09:00"
            )
        )
        assert matin.id is not None and apres_midi.id is not None and ailleurs.id is not None
        self.matin, self.apres_midi, self.ailleurs = matin, apres_midi, ailleurs

        for depart, volees_du_second in ((matin, 2), (apres_midi, 1)):
            assert depart.id is not None
            qualif = self.phases.ajouter(
                Phase.qualification(depart.id, BaremeQualification.creer(2, 1))
            )
            assert qualif.id is not None
            for indice, (categorie_id, volees) in enumerate(
                ((senior.id, 2), (cadet.id, volees_du_second))
            ):
                archer = self.archers.ajouter(
                    Archer.creer(
                        f"NOM{depart.numero}{indice}",
                        "Jean",
                        self.tournoi_id,
                        categorie_id,
                        club_id=club.id,
                    )
                )
                assert archer.id is not None
                self.inscriptions.ajouter(Inscription.creer(archer.id, depart.id, cree_le=None))
                series.append(
                    Serie(
                        tournoi_id=self.tournoi_id,
                        archer_id=archer.id,
                        phase_id=qualif.id,
                        volees=tuple(
                            Volee(numero=n, valeurs=(ZoneScore.DIX,), validee_par="Scoreur")
                            for n in range(1, volees + 1)
                        ),
                    )
                )
        self.series = FauxSerieRepository(series)
        self.classements = ServiceClassement(
            self.tournois,
            self.archers,
            self.series,
            self.categories,
            self.phases,
            FauxForfaitRepository(),
            self.departs,
            self.inscriptions,
        )
        self.pdf = _GenerateurEspion(b"pdf")
        self.csv = _GenerateurEspion(b"csv")

    def service(self) -> ServiceClassementImprime:
        return ServiceClassementImprime(
            tournois=self.tournois,
            departs=self.departs,
            categories=self.categories,
            clubs=self.clubs,
            series=self.series,
            classements=self.classements,
            generateurs=RegistreDeFormats({FormatExport.PDF: self.pdf, FormatExport.CSV: self.csv}),
        )


def test_sans_depart_choisi_une_section_par_depart_du_tournoi_dans_l_ordre() -> None:
    decor = _Decor()

    document = decor.service().document(decor.tournoi_id)

    assert document.tournoi == "Salle 18m"
    assert [section.libelle for section in document.sections] == [
        decor.matin.libelle_creneau(),
        decor.apres_midi.libelle_creneau(),
    ]


def test_un_depart_choisi_ne_rend_que_sa_section() -> None:
    decor = _Decor()
    assert decor.apres_midi.id is not None

    document = decor.service().document(decor.tournoi_id, decor.apres_midi.id)

    assert [section.libelle for section in document.sections] == [
        decor.apres_midi.libelle_creneau()
    ]


def test_les_lignes_sont_celles_du_classement_affiche() -> None:
    decor = _Decor()
    assert decor.matin.id is not None

    document = decor.service().document(decor.tournoi_id, decor.matin.id)

    imprimees = [ligne for bloc in document.sections[0].categories for ligne in bloc.lignes]
    affichees = decor.classements.pour_depart(decor.matin.id).lignes
    assert sorted(imprimees, key=lambda ligne: ligne.archer_id) == sorted(
        affichees, key=lambda ligne: ligne.archer_id
    )
    assert [bloc.libelle for bloc in document.sections[0].categories] == ["Senior Homme", "Cadet"]


def test_le_provisoire_se_juge_depart_par_depart() -> None:
    decor = _Decor()

    document = decor.service().document(decor.tournoi_id)

    assert [section.provisoire for section in document.sections] == [False, True]


def test_le_club_s_imprime_par_son_nom() -> None:
    decor = _Decor()

    document = decor.service().document(decor.tournoi_id)

    ligne = document.sections[0].categories[0].lignes[0]
    assert ligne.club_id is not None
    assert document.clubs[ligne.club_id] == "Compagnie de Kervignarc"


def test_tournoi_inconnu_leve_tournoi_introuvable() -> None:
    with pytest.raises(TournoiIntrouvable):
        _Decor().service().document(999)


def test_tournoi_sans_depart_leve_tournoi_sans_depart() -> None:
    decor = _Decor()
    vide = decor.tournois.ajouter(Tournoi.creer("Vide", _DATE))
    assert vide.id is not None

    with pytest.raises(TournoiSansDepart):
        decor.service().document(vide.id)


def test_un_depart_d_un_autre_tournoi_est_introuvable() -> None:
    decor = _Decor()
    assert decor.ailleurs.id is not None

    with pytest.raises(DepartIntrouvable):
        decor.service().document(decor.tournoi_id, decor.ailleurs.id)


def test_imprimer_passe_le_document_au_generateur_du_format_demande() -> None:
    decor = _Decor()

    octets = decor.service().imprimer(decor.tournoi_id, None, FormatExport.CSV)

    assert octets == b"csv"
    assert decor.csv.recu is not None and len(decor.csv.recu.sections) == 2
    assert decor.pdf.recu is None


def test_les_formats_annonces_sont_ceux_du_registre() -> None:
    decor = _Decor()

    assert decor.service().formats_disponibles == (FormatExport.PDF, FormatExport.CSV)
