"""**L'oracle multi-départ** — deux créneaux d'un même tournoi sont étanches (ADR-0075).

Second remède promis par [ADR-0075], et le plus important des deux. Voici pourquoi.

L'**oracle 120** (`test_oracle_120_placement.py`) fait autorité sur le moteur de placement — mais
c'est un test de **domaine pur** : il construit un tableau à partir de rangs, sans base, sans
tournoi, sans départ. Il ne pouvait donc *structurellement pas* voir la confusion des portées. Et
tous les autres tests d'intégration montaient des décors **mono-départ**, cas où « portée tournoi »
et « portée départ » donnent exactement le même résultat. Le modèle était juste par accident, et
aucun test n'exerçait le seul cas qui distingue les deux.

C'est ce trou qui a laissé [ADR-0017] diverger **treize mois** : la décision était écrite, le code
ne la portait pas, et rien ne pouvait le dire. Ce fichier ferme le trou — il monte un tournoi à
**deux créneaux** sur les vrais adapters SQL, et vérifie ce qu'un décor mono-départ ne peut pas
prouver.

**Ce qu'il éprouve** (et qui échouerait sur le code d'avant le 06/08/2026) :

1. deux classements **distincts**, chacun sur ses seuls inscrits ;
2. un rang 1 dans **chaque** créneau — les deux vainqueurs coexistent, ne s'étant jamais
   affrontés ;
3. un archer du matin **n'apparaît jamais** au classement de l'après-midi ;
4. le meilleur score du matin **ne dégrade pas** le rang d'un archer de l'après-midi ;
5. chaque départ porte **sa propre séquence** 1..N, sans collision d'ordres.

Le point 4 est le cœur : c'est exactement ce que produisait le classement fusionné. Un archer de
l'après-midi se retrouvait derrière tous les tireurs du matin mieux notés, alors qu'il n'avait
jamais tiré contre eux.

[ADR-0017]: ../../docs/adr/0017-le-depart-est-un-creneau-du-tournoi.md
[ADR-0075]: ../../docs/adr/0075-le-depart-est-la-portee-sportive.md
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from application.classements import ServiceClassement
from domain.archer import Archer
from domain.bareme import BaremeQualification
from domain.blason import ZoneScore
from domain.categorie import Categorie
from domain.depart import Depart
from domain.inscription import Inscription
from domain.phase import Phase, SequencePhases, TypePhase
from domain.serie import Serie, Volee
from domain.tournoi import Tournoi
from infrastructure.db import (
    ArcherRepositorySQL,
    AuditRepositorySQL,
    CategorieRepositorySQL,
    Database,
    DepartRepositorySQL,
    ForfaitRepositorySQL,
    InscriptionRepositorySQL,
    PhaseRepositorySQL,
    SerieRepositorySQL,
    TournoiRepositorySQL,
)
from infrastructure.horloge import HorlogeSysteme
from tests.base_migree import preparer_base
from tests.conftest import poser_phase_sql

_DATE = datetime.date(2026, 3, 14)


class _TournoiADeuxDeparts:
    """Un tournoi réel, deux créneaux, trois archers chacun — sur les **vrais** adapters SQL.

    Les scores sont choisis pour que la fusion soit **visible** si elle revenait : le plus faible du
    matin (24) tire mieux que le meilleur de l'après-midi (21). Un classement fusionné placerait
    donc les trois archers du matin devant les trois de l'après-midi, et le vainqueur de
    l'après-midi n'aurait plus le rang 1 mais le rang 4.
    """

    # (matin, après-midi) — décroissants dans chaque vague, et les deux vagues se chevauchent.
    SCORES_MATIN = (("10", "10", "10"), ("9", "9", "9"), ("8", "8", "8"))  # 30, 27, 24
    SCORES_APRES_MIDI = (("7", "7", "7"), ("6", "6", "6"), ("5", "5", "5"))  # 21, 18, 15

    def __init__(self, tmp_path: Path) -> None:
        url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
        preparer_base(url)
        self.db = Database(url)
        sf = self.db.session_factory
        tournoi = TournoiRepositorySQL(sf).ajouter(Tournoi.creer("Salle 18 m", _DATE))
        assert tournoi.id is not None
        self.tournoi_id = tournoi.id
        categorie = CategorieRepositorySQL(sf).ajouter(Categorie.creer(tournoi.id, "Senior 1 H"))
        assert categorie.id is not None

        departs = DepartRepositorySQL(sf)
        self.matin = self._creneau(departs, numero=1, horaire="09:00")
        self.apres_midi = self._creneau(departs, numero=2, horaire="14:00")

        # **Une séquence par créneau**, aux mêmes ordres : c'est licite, et c'est le propos —
        # deux « ordre 1 » coexistent parce qu'ils vivent dans des départs différents.
        #
        # E05US025 : posées **avant** les vagues, parce qu'une feuille de marque pend désormais à sa
        # phase (`serie.phase_id`, NOT NULL). Chaque créneau garde la sienne : c'est précisément ce
        # que cet oracle éprouve — les scores du matin ne doivent pas peser sur l'après-midi.
        phases = PhaseRepositorySQL(sf)
        qualif_de: dict[int, int] = {}
        for depart_id in (self.matin, self.apres_midi):
            qualif = poser_phase_sql(
                sf, Phase.qualification(depart_id, BaremeQualification.creer(1, 3))
            )
            assert qualif.id is not None
            qualif_de[depart_id] = qualif.id
            poser_phase_sql(sf, Phase.creer(depart_id, 2, TypePhase.ELIMINATION_DIRECTE))

        self.archers_matin = self._vague(
            sf, categorie.id, self.matin, self.SCORES_MATIN, qualif_de[self.matin]
        )
        self.archers_apres_midi = self._vague(
            sf, categorie.id, self.apres_midi, self.SCORES_APRES_MIDI, qualif_de[self.apres_midi]
        )

        self.classement = ServiceClassement(
            TournoiRepositorySQL(sf),
            ArcherRepositorySQL(sf),
            SerieRepositorySQL(sf, AuditRepositorySQL(sf), HorlogeSysteme()),
            CategorieRepositorySQL(sf),
            phases,
            ForfaitRepositorySQL(sf, AuditRepositorySQL(sf)),
            departs,
            InscriptionRepositorySQL(sf, AuditRepositorySQL(sf)),
        )

    def _creneau(self, departs: DepartRepositorySQL, numero: int, horaire: str) -> int:
        depart = departs.ajouter(
            Depart.creer(
                tournoi_id=self.tournoi_id, numero=numero, tarif_centimes=800, horaire=horaire
            )
        )
        assert depart.id is not None
        return depart.id

    def _vague(
        self,
        sf: object,
        categorie_id: int,
        depart_id: int,
        scores: tuple[tuple[str, ...], ...],
        phase_id: int,
    ) -> list[int]:
        """Crée les archers d'un créneau, les y **inscrit**, et sème leur série validée.

        L'inscription n'est pas décorative : c'est elle qui dit *qui tire quand*, et donc elle seule
        qui définit le périmètre d'un classement (ADR-0075). `Archer.tournoi_id` ne le sait pas.
        """
        archers = ArcherRepositorySQL(sf)  # type: ignore[arg-type]
        inscriptions = InscriptionRepositorySQL(sf, AuditRepositorySQL(sf))  # type: ignore[arg-type]
        series = SerieRepositorySQL(sf, AuditRepositorySQL(sf), HorlogeSysteme())  # type: ignore[arg-type]
        ids: list[int] = []
        for rang, valeurs in enumerate(scores, start=1):
            archer = archers.ajouter(
                Archer(
                    nom=f"Tireur{depart_id}-{rang}",
                    prenom="Jean",
                    tournoi_id=self.tournoi_id,
                    categorie_id=categorie_id,
                )
            )
            assert archer.id is not None
            inscriptions.ajouter(Inscription.creer(archer.id, depart_id))
            series.enregistrer(
                Serie(
                    tournoi_id=self.tournoi_id,
                    archer_id=archer.id,
                    volees=(
                        Volee(
                            numero=1,
                            valeurs=tuple(ZoneScore(v) for v in valeurs),
                            validee_par="Scoreur",
                        ),
                    ),
                    phase_id=phase_id,
                )
            )
            ids.append(archer.id)
        return ids


@pytest.fixture
def tournoi(tmp_path: Path) -> _TournoiADeuxDeparts:
    return _TournoiADeuxDeparts(tmp_path)


def test_chaque_depart_a_son_classement(tournoi: _TournoiADeuxDeparts) -> None:
    """Deux créneaux → **deux** classements de trois, jamais un de six."""
    matin = tournoi.classement.pour_depart(tournoi.matin)
    apres_midi = tournoi.classement.pour_depart(tournoi.apres_midi)

    assert len(matin.lignes) == 3, "Le classement du matin ne compte que ses inscrits."
    assert len(apres_midi.lignes) == 3, "Celui de l'après-midi non plus."


def test_chaque_depart_a_son_vainqueur(tournoi: _TournoiADeuxDeparts) -> None:
    """Un rang 1 dans **chaque** créneau : les deux vainqueurs ne se sont pas affrontés.

    Sur un classement fusionné, l'après-midi n'aurait pas de rang 1 — son meilleur tireur (21)
    arriverait 4ᵉ, derrière les trois du matin.
    """
    for depart_id, attendus in (
        (tournoi.matin, tournoi.archers_matin),
        (tournoi.apres_midi, tournoi.archers_apres_midi),
    ):
        lignes = tournoi.classement.pour_depart(depart_id).lignes
        premiers = [ligne for ligne in lignes if ligne.rang_scratch == 1]
        assert len(premiers) == 1, f"Le départ {depart_id} doit avoir un et un seul rang 1."
        assert premiers[0].archer_id == attendus[0], "Le mieux noté du créneau le remporte."


def test_un_archer_du_matin_n_apparait_pas_l_apres_midi(tournoi: _TournoiADeuxDeparts) -> None:
    """Étanchéité stricte : les deux listes d'archers sont disjointes."""
    du_matin = {ligne.archer_id for ligne in tournoi.classement.pour_depart(tournoi.matin).lignes}
    de_l_apres_midi = {
        ligne.archer_id for ligne in tournoi.classement.pour_depart(tournoi.apres_midi).lignes
    }

    assert du_matin == set(tournoi.archers_matin)
    assert de_l_apres_midi == set(tournoi.archers_apres_midi)
    assert not du_matin & de_l_apres_midi, "Aucun archer ne figure dans les deux classements."


def test_les_scores_du_matin_ne_degradent_pas_les_rangs_de_l_apres_midi(
    tournoi: _TournoiADeuxDeparts,
) -> None:
    """**Le cœur de l'oracle.** Les rangs de l'après-midi sont 1, 2, 3 — pas 4, 5, 6.

    Le décor est monté pour que la fusion soit impossible à manquer : le plus faible du matin (24)
    tire mieux que le meilleur de l'après-midi (21). Avant ADR-0075, ce classement unique de six
    plaçait l'après-midi aux rangs 4 à 6 — des archers jugés sur des flèches tirées par d'autres,
    à une autre heure, qu'ils n'ont jamais affrontés.
    """
    lignes = tournoi.classement.pour_depart(tournoi.apres_midi).lignes
    assert [ligne.rang_scratch for ligne in lignes] == [1, 2, 3]


def test_chaque_depart_porte_sa_propre_sequence(tournoi: _TournoiADeuxDeparts) -> None:
    """Deux séquences 1..2 coexistent, une par créneau — et chacune est **valide** isolément.

    C'est ce qu'interdisait l'ancien modèle : à la portée tournoi, deux « ordre 1 » entraient en
    collision et `SequencePhases` refusait toute composition ultérieure. La vue transverse, elle,
    rend bien les quatre phases — mais ce n'est **pas** une séquence, et l'assembler en une seule
    lèverait `SequenceOrdreInvalide`. Les deux lectures sont ici mises côte à côte, pour que la
    différence soit lisible plutôt que déduite.
    """
    phases = PhaseRepositorySQL(self_sf := tournoi.db.session_factory)
    assert self_sf is not None

    for depart_id in (tournoi.matin, tournoi.apres_midi):
        sequence = phases.par_depart(depart_id)
        assert [phase.ordre for phase in sequence] == [1, 2]
        SequencePhases(phases=tuple(sequence))  # ne lève pas : la séquence tient debout

    transverse = phases.par_tournoi(tournoi.tournoi_id)
    assert len(transverse) == 4, "La vue transverse couvre les deux créneaux."
    assert [phase.ordre for phase in transverse] == [
        1,
        2,
        1,
        2,
    ], "Les ordres repartent de 1 à chaque départ : la vue transverse n'est pas une séquence."
