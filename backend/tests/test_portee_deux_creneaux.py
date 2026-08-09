"""Non-régression des **résidus de portée tournoi** trouvés à la revue d'E01US025.

Ces tests ont tous la même forme, et c'est le propos : **deux créneaux dans un même tournoi**.
La revue a montré que la suite ne pouvait pas, structurellement, voir ces défauts — sur un tournoi
mono-départ, `depart_id` et `tournoi_id` sélectionnent le même ensemble, et les décors où le premier
tournoi et le premier départ portent tous deux l'`id` 1 rendent les deux mailles indiscernables. Six
correctifs de portée ont été appliqués sans qu'**aucun** des 957 tests existants ne vire au rouge :
c'est la mesure exacte de ce que la suite ne prouvait pas.

L'oracle n'est donc pas le comportement observé — il n'aurait rien dit — mais [ADR-0075] : *une
place se dispute dans le classement d'un départ*, et rien de ce qui appartient à un créneau ne doit
franchir la frontière vers un autre.

⚠️ **Chaque test ici doit échouer si l'on repasse la ligne corrigée en `par_tournoi`.** C'est le seul
critère qui vaille : un test de portée qui reste vert dans les deux mailles ne teste pas la portée.

[ADR-0075]: ../../docs/adr/0075-le-depart-est-la-portee-sportive.md
"""

from __future__ import annotations

import dataclasses
import datetime
from collections.abc import Sequence

import pytest

from application.barrages import ServiceBarrage
from application.classements import ServiceClassement
from application.erreurs import TireursDesignesInvalides
from domain.archer import Archer, ArcherId
from domain.bareme import BaremeQualification
from domain.barrage import BarrageDePlaces, PorteeBarrage, TirBarrage
from domain.blason import ZoneScore
from domain.categorie import Categorie
from domain.depart import Depart
from domain.entree_audit import EntreeAudit
from domain.inscription import Inscription
from domain.participant import Participant
from domain.phase import Phase, PhaseId
from domain.serie import Serie, Volee
from domain.tournoi import Tournoi, TournoiId
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxDepartRepository,
    FauxDerouleRepository,
    FauxForfaitRepository,
    FauxInscriptionRepository,
    FauxPhaseRepository,
    HorlogeFigee,
    poser_phase_factice,
)

_DATE = datetime.date(2026, 3, 14)
_TOURNOI = 1

# ⚠️ **Les identifiants de créneau sont volontairement éloignés de 1.** Le défaut que ces tests
# protègent survivait précisément parce que `tournoi_id == depart_id == 1` dans la plupart des
# décors : toute confusion des deux mailles y restait verte par coïncidence numérique.
_MATIN = 41
_APRES_MIDI = 42


class FauxTournoiRepository:
    """Double de `TournoiRepository` : seul `par_id` sert ici (le reste conforme le port)."""

    def par_id(self, tournoi_id: TournoiId) -> Tournoi | None:
        return Tournoi.creer("Salle 18m", _DATE) if tournoi_id == _TOURNOI else None

    def ajouter(self, tournoi: Tournoi) -> Tournoi:
        raise NotImplementedError

    def lister(self) -> list[Tournoi]:
        raise NotImplementedError

    def enregistrer(self, tournoi: Tournoi) -> Tournoi:
        raise NotImplementedError

    def supprimer(self, tournoi_id: TournoiId) -> None:
        raise NotImplementedError


class FauxSerieRepository:
    """Double de `SerieRepository` : seul `par_tournoi` sert au classement."""

    def __init__(self, series: list[Serie]) -> None:
        self._series = series

    def par_phase(self, phase_id: PhaseId) -> list[Serie]:
        """E05US025 : le classement lit les feuilles **d'une phase**, plus celles du tournoi."""
        return [s for s in self._series if s.phase_id == phase_id]

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Serie]:
        return [s for s in self._series if s.tournoi_id == tournoi_id]

    # Le reste du port : présent pour **conformer**, jamais appelé par le classement.
    def par_archer(self, phase_id: PhaseId, archer_id: ArcherId) -> Serie | None:
        raise NotImplementedError

    def horodatages(self, phase_id: PhaseId, archer_id: ArcherId) -> dict[int, datetime.datetime]:
        raise NotImplementedError

    def enregistrer(self, serie: Serie) -> Serie:
        raise NotImplementedError

    def enregistrer_avec_trace(self, serie: Serie, entree: EntreeAudit) -> Serie:
        raise NotImplementedError


class FauxBarrageRepository:
    """Double de `BarrageRepository` — les deux lectures de maille, pour pouvoir les opposer.

    ⚠️ `par_tournoi` est **implémenté**, et c'est délibéré : un double qui lèverait
    `NotImplementedError` ferait échouer le test pour la mauvaise raison (une exception au lieu
    d'une assertion), et surtout il ne dirait rien du **cas où l'ancien code rendait un résultat
    faux mais plausible**. On veut voir le mauvais classement, pas une trace.
    """

    def __init__(self, departs: FauxDepartRepository) -> None:
        self._departs = departs
        self._items: list[BarrageDePlaces] = []

    def ouvrir(self, barrage: BarrageDePlaces) -> BarrageDePlaces:
        persiste = BarrageDePlaces(
            depart_id=barrage.depart_id,
            portee=barrage.portee,
            participants=barrage.participants,
            cree_le=barrage.cree_le,
            manches=barrage.manches,
            rang_dispute=barrage.rang_dispute,
            phase_id=barrage.phase_id,
            reference=barrage.reference,
            clos=barrage.clos,
            id=len(self._items) + 1,
        )
        self._items.append(persiste)
        return persiste

    def par_depart(self, depart_id: int) -> list[BarrageDePlaces]:
        return [b for b in self._items if b.depart_id == depart_id]

    def par_tournoi(self, tournoi_id: TournoiId) -> list[BarrageDePlaces]:
        creneaux = {d.id for d in self._departs.par_tournoi(tournoi_id)}
        return [b for b in self._items if b.depart_id in creneaux]

    def par_id(self, barrage_id: int) -> BarrageDePlaces | None:
        return next((b for b in self._items if b.id == barrage_id), None)

    # Le reste du port : présent pour **conformer**, jamais appelé par ces tests.
    def enregistrer_manche(
        self, barrage_id: int, manche: int, tirs: Sequence[TirBarrage]
    ) -> BarrageDePlaces:
        raise NotImplementedError

    def supprimer(self, barrage_id: int) -> None:
        raise NotImplementedError

    def clore(self, barrage_id: int) -> BarrageDePlaces:
        raise NotImplementedError

    def rouvrir(self, barrage_id: int) -> BarrageDePlaces:
        raise NotImplementedError


class Decor:
    """Un tournoi, **deux** créneaux, les mêmes deux archers inscrits aux deux, à égalité partout.

    L'égalité est la condition du piège : les rangs se répètent d'un créneau à l'autre, si bien
    qu'un barrage du matin et une égalité de l'après-midi portent le **même** `rang_dispute`. C'est
    exactement ce qui faisait passer l'un pour l'autre.
    """

    def __init__(self) -> None:
        self.tournois = FauxTournoiRepository()
        self.archers = FauxArcherRepository()
        self.categories = FauxCategorieRepository()
        categorie = self.categories.ajouter(Categorie.creer(_TOURNOI, "Senior Homme"))
        assert categorie.id is not None
        alice = self.archers.ajouter(Archer.creer("Martin", "Alice", _TOURNOI, categorie.id))
        bob = self.archers.ajouter(Archer.creer("Durand", "Bob", _TOURNOI, categorie.id))
        assert alice.id is not None and bob.id is not None
        self.alice, self.bob = alice.id, bob.id

        self.departs = FauxDepartRepository()
        for numero, identifiant, horaire in ((1, _MATIN, "09:00"), (2, _APRES_MIDI, "14:00")):
            depart = Depart.creer(
                tournoi_id=_TOURNOI, numero=numero, tarif_centimes=800, horaire=horaire
            )
            self.departs.ajouter(
                Depart(
                    tournoi_id=depart.tournoi_id,
                    numero=depart.numero,
                    horaire=depart.horaire,
                    tarif_centimes=depart.tarif_centimes,
                    quota=depart.quota,
                    id=identifiant,
                )
            )

        self.inscriptions = FauxInscriptionRepository()
        for depart_id in (_MATIN, _APRES_MIDI):
            for archer_id in (self.alice, self.bob):
                self.inscriptions.ajouter(Inscription.creer(archer_id, depart_id))

        # Le déroulé est composé **une fois** (ADR-0076) et instancié dans les deux créneaux : une
        # qualification au rang 1, avec un seuil de barrage jusqu'au rang 1.
        self.deroules = FauxDerouleRepository()
        self.phases = FauxPhaseRepository(self.departs, self.deroules)
        self.qualif: dict[int, int] = {}
        for depart_id in (_MATIN, _APRES_MIDI):
            qualification = Phase.qualification(
                depart_id=depart_id, bareme=BaremeQualification.preset_ffta_18m()
            )
            phase = poser_phase_factice(
                self.departs,
                self.deroules,
                self.phases,
                dataclasses.replace(qualification, barrage_jusqu_au=1),
            )
            assert phase.id is not None
            self.qualif[depart_id] = phase.id

        # Même total : ex æquo au rang 1 dans **chacun** des deux créneaux.
        #
        # E05US025 : **une feuille par (archer, phase)**, donc quatre — c'est précisément le cas que
        # `DETTE-046` décrivait comme cassé (un archer sur deux créneaux n'avait qu'un emplacement
        # pour ses flèches). Le décor le rend maintenant fidèlement : Alice et Bob tirent le matin
        # *et* l'après-midi, et chaque tir a sa feuille.
        self.series = FauxSerieRepository(
            [
                self._serie(archer, (ZoneScore.NEUF, ZoneScore.NEUF), self.qualif[depart_id])
                for depart_id in (_MATIN, _APRES_MIDI)
                for archer in (self.alice, self.bob)
            ]
        )

        self.barrages = FauxBarrageRepository(self.departs)

    @staticmethod
    def _serie(archer_id: int, valeurs: tuple[ZoneScore, ...], phase_id: int) -> Serie:
        return Serie(
            tournoi_id=_TOURNOI,
            archer_id=archer_id,
            phase_id=phase_id,
            volees=(Volee(numero=1, valeurs=valeurs, validee_par="Scoreur"),),
        )

    def classement(self) -> ServiceClassement:
        return ServiceClassement(
            self.tournois,
            self.archers,
            self.series,
            self.categories,
            self.phases,
            FauxForfaitRepository(),
            self.departs,
            self.inscriptions,
            self.barrages,
        )

    def barrage(self) -> ServiceBarrage:
        return ServiceBarrage(
            self.tournois,
            self.barrages,
            self.classement(),
            HorlogeFigee(datetime.datetime(2026, 3, 14, 12, 0)),
            self.archers,
            self.phases,
            self.departs,
        )

    def departager_le_matin(self) -> None:
        """Tire et clôt, **au matin uniquement**, le barrage du rang 1 : Alice devant Bob."""
        self.barrages.ouvrir(
            BarrageDePlaces(
                depart_id=_MATIN,
                portee=PorteeBarrage.QUALIFICATION,
                participants=(
                    Participant.individuel(self.alice),
                    Participant.individuel(self.bob),
                ),
                cree_le=datetime.datetime(2026, 3, 14, 12, 0),
                manches=(
                    (
                        TirBarrage(participant=Participant.individuel(self.alice), score=10),
                        TirBarrage(participant=Participant.individuel(self.bob), score=8),
                    ),
                ),
                rang_dispute=1,
                phase_id=self.qualif[_MATIN],
                clos=True,
            )
        )


def test_un_barrage_du_matin_ne_departage_pas_l_egalite_de_l_apres_midi() -> None:
    """Le verdict d'un créneau ne franchit pas la frontière vers l'autre (ADR-0075).

    Alice et Bob sont ex æquo au rang 1 **dans les deux créneaux**. Un barrage tiré et clos le matin
    tranche en faveur d'Alice — pour le matin. L'après-midi, personne n'a encore tiré de barrage :
    l'égalité doit rester entière et rester **signalée à départager**.

    Avec `_verdicts_qualif` lu `par_tournoi`, le verdict du matin s'appliquait à l'après-midi : deux
    archers qui ne se sont pas départagés dans ce créneau y apparaissaient pourtant classés, et
    l'organisateur ne voyait plus l'égalité qu'il devait faire tirer.
    """
    decor = Decor()
    decor.departager_le_matin()
    service = decor.classement()

    matin = service.pour_depart(_MATIN)
    apres_midi = service.pour_depart(_APRES_MIDI)

    # Le matin est bien départagé : c'est le témoin, sans lui le test passerait aussi sur un
    # classement qui ignorerait tous les barrages.
    assert [ligne.rang_scratch for ligne in matin.lignes] == [1, 2]
    assert matin.egalites_a_departager == ()

    # L'après-midi ne l'est pas : rang partagé, et l'égalité reste à faire tirer.
    assert [ligne.rang_scratch for ligne in apres_midi.lignes] == [1, 1]
    assert [egalite.rang for egalite in apres_midi.egalites_a_departager] == [1]


def test_un_barrage_ne_peut_pas_citer_la_phase_d_un_autre_creneau() -> None:
    """`_participants_designes` valide la phase **du créneau**, pas celle du tournoi.

    Un barrage de poule annoncé sur l'après-midi en citant la phase de qualification **du matin**
    doit être refusé. Accepté, il produisait une donnée croisée — et, à la suppression du créneau du
    matin, un barrage pointant une phase disparue, donc une `IntegrityError` sur une purge qui
    existe justement pour éviter cela.
    """
    decor = Decor()
    service = decor.barrage()

    with pytest.raises(TireursDesignesInvalides, match="créneau"):
        service.annoncer(
            _TOURNOI,
            depart_id=_APRES_MIDI,
            portee=PorteeBarrage.POULE,
            archer_ids=[decor.alice, decor.bob],
            phase_id=decor.qualif[_MATIN],
        )


def test_la_phase_du_propre_creneau_reste_acceptee() -> None:
    """Le pendant du test précédent — sans lui, un refus **systématique** passerait pour un succès.

    C'est la moitié qui manque le plus souvent : une garde trop serrée est aussi un bug, et elle
    est invisible tant qu'on ne teste que le cas refusé.
    """
    decor = Decor()
    service = decor.barrage()

    barrage = service.annoncer(
        _TOURNOI,
        depart_id=_APRES_MIDI,
        portee=PorteeBarrage.POULE,
        archer_ids=[decor.alice, decor.bob],
        phase_id=decor.qualif[_APRES_MIDI],
    )

    assert barrage.depart_id == _APRES_MIDI
    assert barrage.phase_id == decor.qualif[_APRES_MIDI]
