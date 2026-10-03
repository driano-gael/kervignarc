"""Un tableau d'équipes se joue de bout en bout (E13US004, CA 2 à 5 et 7) — repositories factices.

Écrits **depuis le CA** (règle 9), avant le code. Le classement de qualification est **vrai**
(`ServiceClassement` sur des séries semées) : c'est lui que l'engagement somme (CA 3).
"""

from __future__ import annotations

import datetime
from dataclasses import replace

import pytest

from application.classements import ServiceClassement
from application.equipes import ServiceEquipes
from application.saisie_duels import (
    Duelliste,
    DuellisteEquipe,
    EtatDuel,
    EtatTableau,
    ServiceSaisieDuels,
)
from domain.archer import Archer
from domain.bareme import BaremeQualification
from domain.blason import Blason, ZoneScore
from domain.categorie import Categorie, SexeCategorie
from domain.depart import Depart
from domain.duel import BaremeDuel, ModeDuel, ReglageBaremeDuel, ResolveurBaremeDuelFfta
from domain.equipe import EcartComposition, Equipe, TypeEquipe
from domain.erreurs import EffectifTableauInvalide, NombreFlechesVoleeInvalide
from domain.forfait import Forfait, NatureForfait
from domain.inscription import Inscription
from domain.participant import GenreParticipant
from domain.phase import Phase, TypePhase
from domain.politiques import (
    AggregationParQualification,
    ByesAuxMieuxClasses,
    PlacementEnCascade,
    SeedingSerpent,
    registre_par_defaut,
)
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxDepartRepository,
    FauxDuelRepository,
    FauxEquipeRepository,
    FauxForfaitRepository,
    FauxInscriptionRepository,
    FauxPhaseRepository,
    FauxVerrouDeComposition,
    identite_d_etape,
)
from tests.test_service_placement_duels import (
    FauxBlasonRepository,
    FauxSerieRepository,
    FauxTournoiRepository,
)
from tests.test_service_saisie_duels import ZONES_TRIPLE

DIX = ZoneScore.DIX
NEUF = ZoneScore.NEUF
SIX = ZoneScore.SIX


class _Monde:
    """Un tournoi, un départ, une qualification, une phase d'élimination réglée par équipes."""

    def __init__(
        self,
        type_equipe: TypeEquipe = TypeEquipe.STANDARD,
        *,
        arme: str = "Arc Classique",
        bareme_duel: ReglageBaremeDuel | None = None,
    ) -> None:
        self.tournoi_id = 1
        self.tournois = FauxTournoiRepository({1})
        self.departs = FauxDepartRepository()
        depart = self.departs.ajouter(
            Depart.creer(tournoi_id=1, numero=1, tarif_centimes=800, horaire="09:00")
        )
        assert depart.id is not None
        self.depart_id = depart.id
        self.inscriptions = FauxInscriptionRepository()
        self.phases = FauxPhaseRepository(self.departs)
        self.archers = FauxArcherRepository()
        self.categories = FauxCategorieRepository()
        self.blasons = FauxBlasonRepository()
        self.series = FauxSerieRepository()
        self.duels = FauxDuelRepository()
        self.forfaits = FauxForfaitRepository()
        self.equipes = FauxEquipeRepository()
        blason = self.blasons.ajouter(Blason.creer(1, "Triple", taille=0.25, capacite=1))
        assert blason.id is not None
        self.blasons._blasons[blason.id] = replace(blason, zones=ZONES_TRIPLE)
        self.categories_par_sexe: dict[SexeCategorie, int] = {}
        for sexe in (SexeCategorie.HOMME, SexeCategorie.FEMME):
            categorie = self.categories.ajouter(
                Categorie.creer(1, f"Cat {sexe.value}", arme=arme, sexe=sexe, blason_id=blason.id)
            )
            assert categorie.id is not None
            self.categories_par_sexe[sexe] = categorie.id
        qualif = self.phases.ajouter(
            Phase.qualification(
                self.depart_id, BaremeQualification.creer(1, 3), etape_id=identite_d_etape(1)
            )
        )
        assert qualif.id is not None
        self.qualif_id = qualif.id
        phase = Phase.creer(
            self.depart_id, 2, TypePhase.ELIMINATION_DIRECTE, etape_id=identite_d_etape(2)
        )
        phase = self.phases.ajouter(replace(phase, equipes=type_equipe, bareme_duel=bareme_duel))
        assert phase.id is not None
        self.phase_id = phase.id

    def archer(
        self,
        total_par_fleche: int,
        sexe: SexeCategorie = SexeCategorie.HOMME,
        *,
        inscrit: bool = True,
    ) -> int:
        archer = self.archers.ajouter(
            Archer(nom="N", prenom="P", tournoi_id=1, categorie_id=self.categories_par_sexe[sexe])
        )
        assert archer.id is not None
        if inscrit:
            self.series.semer(1, archer.id, (ZoneScore(str(total_par_fleche)),) * 3, self.qualif_id)
            self.inscriptions.ajouter(Inscription(archer.id, self.depart_id))
        return archer.id

    def equipe(
        self, nom: str, membres: tuple[int, ...], type: TypeEquipe = TypeEquipe.STANDARD
    ) -> int:
        equipe = self.equipes.enregistrer(
            Equipe(tournoi_id=1, nom=nom, type=type, effectif_attendu=3 if type is
                   TypeEquipe.STANDARD else 2, membres=membres)
        )  # fmt: skip
        assert equipe.id is not None
        return equipe.id

    def equipe_de_trois(self, nom: str, valeur: int) -> int:
        return self.equipe(nom, tuple(self.archer(valeur) for _ in range(3)))

    def service(self) -> ServiceSaisieDuels:
        classement = ServiceClassement(
            self.tournois,
            self.archers,
            self.series,
            self.categories,
            self.phases,
            self.forfaits,
            self.departs,
            self.inscriptions,
        )
        return ServiceSaisieDuels(
            self.tournois,
            self.phases,
            self.categories,
            self.blasons,
            self.duels,
            self.forfaits,
            classement,
            ResolveurBaremeDuelFfta(),
            SeedingSerpent(),
            ByesAuxMieuxClasses(),
            PlacementEnCascade(),
            registre_par_defaut(),
            AggregationParQualification(),
            equipes=ServiceEquipes(
                self.equipes,
                self.tournois,
                self.archers,
                self.categories,
                verrou=FauxVerrouDeComposition(),
            ),
        )


def _noms(etat: EtatTableau, tour: int = 1) -> set[tuple[str | None, str | None]]:
    return {
        (m.haut.nom if m.haut else None, m.bas.nom if m.bas else None)
        for m in etat.duels
        if m.tour == tour
    }


def _premier_match(service: ServiceSaisieDuels, monde: _Monde) -> EtatDuel:
    return next(
        m
        for m in service.etat_tableau(1, monde.phase_id).duels
        if m.tour == 1 and m.haut is not None and m.bas is not None and not m.est_bye
    )


# --- CA 2 et 3 : engagement et ensemencement ------------------------------------------------


def test_le_tableau_oppose_les_equipes_ensemencees_par_la_somme_de_leurs_qualifications() -> None:
    monde = _Monde()
    monde.equipe_de_trois("Quatrième", 7)
    monde.equipe_de_trois("Première", 10)
    monde.equipe_de_trois("Troisième", 8)
    monde.equipe_de_trois("Deuxième", 9)

    etat = monde.service().etat_tableau(1, monde.phase_id)

    assert etat.effectif == 4
    # Serpent : 1 contre 4, 2 contre 3.
    assert _noms(etat) == {("Première", "Quatrième"), ("Deuxième", "Troisième")}


def test_un_camp_d_equipe_se_nomme_et_liste_ses_membres() -> None:
    monde = _Monde()
    forte = monde.equipe_de_trois("Forte", 10)
    monde.equipe_de_trois("Faible", 8)

    match = _premier_match(monde.service(), monde)

    assert isinstance(match.haut, DuellisteEquipe)
    assert match.haut.equipe_id == forte
    assert match.haut.nom == "Forte"
    assert len(match.haut.membres) == 3


def test_une_equipe_non_conforme_est_ecartee_et_listee_avec_ses_ecarts() -> None:
    monde = _Monde()
    monde.equipe_de_trois("A", 10)
    monde.equipe_de_trois("B", 9)
    monde.equipe("Incomplète", (monde.archer(10), monde.archer(10)))
    absent = monde.archer(10, inscrit=False)
    monde.equipe("Dispersée", (monde.archer(10), monde.archer(10), absent))

    etat = monde.service().etat_tableau(1, monde.phase_id)

    assert etat.effectif == 2
    assert [(e.nom, e.ecarts, e.membres_hors_course) for e in etat.equipes_ecartees] == [
        ("Dispersée", (), ("P N",)),
        ("Incomplète", (EcartComposition.EFFECTIF_INSUFFISANT,), ()),
    ]
    dispersee = monde.equipes.par_id(etat.equipes_ecartees[0].equipe_id)
    assert dispersee is not None and absent in dispersee.membres


def test_seules_les_equipes_du_type_de_la_phase_entrent() -> None:
    monde = _Monde(TypeEquipe.MIXTE)
    monde.equipe_de_trois("Standard", 10)
    for nom in ("M1", "M2"):
        monde.equipe(
            nom,
            (monde.archer(9, SexeCategorie.HOMME), monde.archer(9, SexeCategorie.FEMME)),
            TypeEquipe.MIXTE,
        )

    etat = monde.service().etat_tableau(1, monde.phase_id)

    assert _noms(etat) == {("M1", "M2")}
    assert etat.equipes_ecartees == ()


def test_une_phase_individuelle_ignore_les_equipes() -> None:
    monde = _Monde()
    monde.phases._phases[monde.phase_id] = replace(
        monde.phases._phases[monde.phase_id], equipes=None
    )
    monde.equipe_de_trois("A", 10)
    monde.equipe_de_trois("B", 9)

    etat = monde.service().etat_tableau(1, monde.phase_id)

    assert etat.effectif == 6
    assert all(
        m.haut is None or isinstance(m.haut, Duelliste) for m in etat.duels
    ), "un tableau individuel n'oppose que des archers"


# --- CA 4 : barème ---------------------------------------------------------------------------


def test_sans_reglage_le_duel_d_equipes_joue_le_preset_du_type() -> None:
    monde = _Monde()
    monde.equipe_de_trois("A", 10)
    monde.equipe_de_trois("B", 9)

    match = _premier_match(monde.service(), monde)

    assert match.bareme == BaremeDuel(ModeDuel.SETS, 4, 6, 5, 3)


def test_les_poulies_jouent_le_preset_equipe_au_cumul() -> None:
    monde = _Monde(arme="Arc à poulies")
    monde.equipe_de_trois("A", 10)
    monde.equipe_de_trois("B", 9)

    match = _premier_match(monde.service(), monde)

    assert match.bareme == BaremeDuel(ModeDuel.CUMUL, 4, 6, 0, 3)


def test_le_reglage_de_la_phase_l_emporte_sur_le_preset() -> None:
    reglage = ReglageBaremeDuel(BaremeDuel(ModeDuel.SETS, 3, 6, 4, 3))
    monde = _Monde(bareme_duel=reglage)
    monde.equipe_de_trois("A", 10)
    monde.equipe_de_trois("B", 9)

    match = _premier_match(monde.service(), monde)

    assert match.bareme == BaremeDuel(ModeDuel.SETS, 3, 6, 4, 3)


# --- CA 5 et 7 : saisie, barrage, validation, podium -----------------------------------------


def test_une_manche_enregistre_la_volee_du_camp() -> None:
    monde = _Monde()
    monde.equipe_de_trois("A", 10)
    monde.equipe_de_trois("B", 9)
    service = monde.service()
    match = _premier_match(service, monde)

    etat = service.saisir_manche(1, monde.phase_id, match.numero, 1, (DIX,) * 6, (NEUF,) * 6)

    assert etat.duel is not None
    assert etat.duel.participant_haut.genre is GenreParticipant.EQUIPE
    assert etat.duel.manches[0].volee_haut.valeurs == (DIX,) * 6


def test_une_volee_de_camp_au_mauvais_nombre_de_fleches_est_refusee() -> None:
    monde = _Monde()
    monde.equipe_de_trois("A", 10)
    monde.equipe_de_trois("B", 9)
    service = monde.service()
    match = _premier_match(service, monde)

    with pytest.raises(NombreFlechesVoleeInvalide):
        service.saisir_manche(1, monde.phase_id, match.numero, 1, (DIX,) * 3, (NEUF,) * 3)


def test_un_match_a_4_4_se_tranche_au_barrage_de_trois_fleches_et_nomme_le_podium() -> None:
    monde = _Monde()
    a = monde.equipe_de_trois("A", 10)
    monde.equipe_de_trois("B", 9)
    service = monde.service()
    numero = _premier_match(service, monde).numero
    # Deux manches gagnées de chaque côté : 4-4 après quatre manches (§7).
    for manche, (haut, bas) in enumerate([(DIX, SIX), (SIX, DIX), (DIX, SIX), (SIX, DIX)], start=1):
        service.saisir_manche(1, monde.phase_id, numero, manche, (haut,) * 6, (bas,) * 6)

    service.saisir_barrage(1, monde.phase_id, numero, (DIX, DIX, NEUF), (DIX, NEUF, NEUF))
    valide = service.valider(1, monde.phase_id, numero, "DURAND")

    assert valide.duel is not None
    resultat = valide.duel.resultat
    assert (resultat.points_haut, resultat.points_bas) == (5, 4)

    etat = service.etat_tableau(1, monde.phase_id)
    assert etat.est_termine
    podium = dict(etat.podium)
    assert isinstance(podium[1], DuellisteEquipe)
    assert podium[1].equipe_id == a
    assert podium[1].nom == "A"
    assert len(podium[1].membres) == 3
    assert podium[2].nom == "B"


def test_un_forfait_individuel_n_atteint_pas_un_tableau_d_equipes() -> None:
    # L'archer 1 et l'équipe 1 partagent leur identifiant : un forfait déclaré pour l'archer ne
    # doit pas faire perdre l'équipe (DETTE-120 : le forfait d'équipe n'existe pas encore).
    monde = _Monde()
    a = monde.equipe_de_trois("A", 10)
    monde.equipe_de_trois("B", 9)
    assert a == 1
    monde.forfaits.semer(
        Forfait(
            tournoi_id=1,
            archer_id=1,
            phase_id=monde.phase_id,
            nature=NatureForfait.ABANDON,
            declare_par="JURY",
            declare_le=datetime.datetime(2026, 10, 3, 10, 0),
        )
    )

    etat = monde.service().etat_tableau(1, monde.phase_id)

    assert not etat.est_termine, "la finale ne doit pas être gagnée d'office"


# --- Arbitrage de revue (03/10/2026) et cas limites relevés en revue --------------------------


def test_une_equipe_aux_blasons_differents_est_ecartee() -> None:
    monde = _Monde()
    monde.equipe_de_trois("A", 10)
    monde.equipe_de_trois("B", 9)
    autre_blason = monde.blasons.ajouter(Blason.creer(1, "60 cm", taille=0.6, capacite=1))
    minimes = monde.categories.ajouter(
        Categorie.creer(
            1, "Minimes H", arme="Arc Classique", sexe=SexeCategorie.HOMME,
            blason_id=autre_blason.id,
        )
    )  # fmt: skip
    assert minimes.id is not None
    minime = monde.archers.ajouter(
        Archer(nom="M", prenom="P", tournoi_id=1, categorie_id=minimes.id)
    )
    assert minime.id is not None
    monde.series.semer(1, minime.id, (ZoneScore.DIX,) * 3, monde.qualif_id)
    monde.inscriptions.ajouter(Inscription(minime.id, monde.depart_id))
    monde.equipe("Mêlée", (monde.archer(10), monde.archer(10), minime.id))

    etat = monde.service().etat_tableau(1, monde.phase_id)

    assert _noms(etat) == {("A", "B")}
    assert [(e.nom, e.ecarts) for e in etat.equipes_ecartees] == [
        ("Mêlée", (EcartComposition.BLASONS_DIFFERENTS,))
    ]


def test_sous_deux_equipes_engagees_le_tableau_est_vide_mais_dit_pourquoi() -> None:
    # Relevé par l'axe D : la liste des écartées doit atteindre l'écran quand elle sert le plus.
    monde = _Monde()
    monde.equipe_de_trois("Seule", 10)
    monde.equipe("Incomplète", (monde.archer(9),))

    etat = monde.service().etat_tableau(1, monde.phase_id)

    assert (etat.effectif, etat.duels, etat.podium) == (1, (), ())
    assert [e.nom for e in etat.equipes_ecartees] == ["Incomplète"]


def test_une_phase_individuelle_sous_deux_archers_leve_toujours() -> None:
    monde = _Monde()
    monde.phases._phases[monde.phase_id] = replace(
        monde.phases._phases[monde.phase_id], equipes=None
    )
    monde.archer(10)

    with pytest.raises(EffectifTableauInvalide):
        monde.service().etat_tableau(1, monde.phase_id)
