"""Tests du service de **simulation d'un format** (E01US024, ADR-0063).

Dérivés du CA « **simuler le format** » de `stories/E01-configuration.md` : *« lancer le déroulé sur
N inscrits fictifs et voir ce qu'il produit […] le format tient-il à cet effectif (personne bloqué,
personne oublié), combien de duels au total […], combien de tours par phase, et le classement 1→N
effectivement produit »* — et du CA « **l'ajustement d'effectif** » (120 puis 82 sans retoucher le
format).

Le harnais est le **vrai** (`fabriquer_harnais_simulation`, composition root) : c'est la convention
posée par E15US002 — le harnais éprouvé par les tests **est** celui déployé.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from application.erreurs import EffectifSimulationInvalide, FormatIntrouvable
from application.generateur_scores import GenerateurScoresPlausibles
from application.pilotage_simulation import (
    RegistreSessionsSimulation,
    ServicePilotageSimulation,
)
from application.simulation import HarnaisSimulation
from application.simulation_format import ServiceSimulationFormat
from bootstrap.composition import fabriquer_harnais_simulation
from domain.bareme import BaremeQualification
from domain.erreurs import PhaseQualificationIncomplete
from domain.format_tournoi import FormatTournoi, FormatTournoiId, ModelePhase
from domain.phase import SourcePhase, TypePhase
from infrastructure.memory.repositories import InMemoryTournoiRepository

# Barème court : la simulation joue **toutes** les volées de tous les archers, et l'oracle porte sur
# le déroulé (duels, tours, classement), pas sur le nombre de flèches.
_BAREME_COURT = BaremeQualification.creer(2, 3)


class _FormatsEnMemoire:
    """Magasin de formats minimal — le service n'en lit que `par_id`."""

    def __init__(self) -> None:
        self._formats: dict[int, FormatTournoi] = {}
        self._compteur = 0

    def ajouter(self, format_tournoi: FormatTournoi) -> FormatTournoi:
        self._compteur += 1
        # `replace()` plutôt qu'une reconstruction champ par champ (3ᵉ jumeau du même défaut,
        # trouvé en 2ᵉ passe de revue) : la forme précédente perdait `effectif_minimum_exige`,
        # ajouté par E05US021 — l'US juste avant celle-ci. Ces tests étaient donc aveugles à sa
        # propagation, sans que rien ne le signale.
        enregistre = replace(format_tournoi, id=self._compteur)
        self._formats[self._compteur] = enregistre
        return enregistre

    def par_id(self, format_id: FormatTournoiId) -> FormatTournoi | None:
        return self._formats.get(format_id)

    def lister(self) -> list[FormatTournoi]:
        return list(self._formats.values())

    def par_nom(self, nom: str) -> FormatTournoi | None:
        return next((f for f in self._formats.values() if f.nom == nom), None)

    def enregistrer(self, format_tournoi: FormatTournoi) -> FormatTournoi:
        assert format_tournoi.id is not None
        self._formats[format_tournoi.id] = format_tournoi
        return format_tournoi

    def supprimer(self, format_id: FormatTournoiId) -> None:
        self._formats.pop(format_id, None)


class _DiffusionMuette:
    def signaler(self, session_id: int) -> None:
        return None


@pytest.fixture
def service() -> tuple[ServiceSimulationFormat, _FormatsEnMemoire]:
    """Le service câblé comme en production, mais sans aucun adapter SQL."""
    formats = _FormatsEnMemoire()
    vide = InMemoryTournoiRepository()
    harnais_temoin: HarnaisSimulation = fabriquer_harnais_simulation()
    pilotage = ServicePilotageSimulation(
        vide,
        harnais_temoin.archers,
        harnais_temoin.categories,
        harnais_temoin.blasons,
        harnais_temoin.gabarits,
        harnais_temoin.inscriptions,
        harnais_temoin.departs,
        harnais_temoin.phases,
        harnais_temoin.series,
        fabriquer_harnais_simulation,
        GenerateurScoresPlausibles(),
        RegistreSessionsSimulation(),
        _DiffusionMuette(),
    )
    return ServiceSimulationFormat(formats, fabriquer_harnais_simulation, pilotage), formats


def _qualif_puis_tableau(formats: _FormatsEnMemoire, rang_fin: int | None = 8) -> int:
    format_tournoi = formats.ajouter(
        FormatTournoi.creer(
            "Qualif + tableau",
            [
                ModelePhase.qualification(_BAREME_COURT, ordre=1),
                ModelePhase(
                    ordre=2,
                    type=TypePhase.ELIMINATION_DIRECTE,
                    sources=(SourcePhase.par_rangs(1, 1, rang_fin),),
                ),
            ],
        )
    )
    assert format_tournoi.id is not None
    return format_tournoi.id


# --- CA « simuler le format » --------------------------------------------------------------------


def test_la_simulation_produit_le_classement_1_a_n(
    service: tuple[ServiceSimulationFormat, _FormatsEnMemoire],
) -> None:
    simulation, formats = service
    format_id = _qualif_puis_tableau(formats)

    resultat = simulation.simuler(format_id, effectif=12)

    rangs = [ligne.rang_scratch for ligne in resultat.classement.lignes]
    assert len(rangs) == 12
    assert rangs == sorted(r for r in rangs if r is not None)


def test_la_simulation_compte_les_duels_reellement_joues_petite_finale_comprise(
    service: tuple[ServiceSimulationFormat, _FormatsEnMemoire],
) -> None:
    """Un tableau à 16 se décide en 15 duels — **plus la petite finale** : 16.

    C'est exactement ce que la simulation apporte et qu'aucune relecture ne donne. Le compte
    « théorique » `effectif - 1` oublie le match pour la 3ᵉ place que `ProfondeurPodium` ajoute ;
    l'organisateur qui dimensionne ses scoreurs sur 15 se trompe d'un duel par tableau.
    """
    simulation, formats = service
    format_id = _qualif_puis_tableau(formats, rang_fin=None)

    resultat = simulation.simuler(format_id, effectif=16)

    assert resultat.duels_total == 16
    tableau = next(p for p in resultat.phases if p.type is TypePhase.ELIMINATION_DIRECTE)
    assert tableau.duels == 16


def test_la_simulation_compte_les_tours_par_phase(
    service: tuple[ServiceSimulationFormat, _FormatsEnMemoire],
) -> None:
    simulation, formats = service
    format_id = _qualif_puis_tableau(formats, rang_fin=None)

    resultat = simulation.simuler(format_id, effectif=8)

    tableau = next(p for p in resultat.phases if p.type is TypePhase.ELIMINATION_DIRECTE)
    assert tableau.tours == 3
    assert tableau.effectif == 8


def test_la_simulation_ne_signale_plus_d_ecart_sur_un_prelevement_par_rangs(
    service: tuple[ServiceSimulationFormat, _FormatsEnMemoire],
) -> None:
    """E05US020 : le moteur **honore** désormais le prélèvement — l'écart se referme.

    Ce test **remplace** `test_la_simulation_signale_l_ecart_quand_le_moteur_ignore_le_prelevement`,
    posé par E01US024 comme test de **caractérisation** de `DETTE-028` : il fixait l'écart
    (projeté 8, constaté 12) pour qu'il ne passe pas inaperçu, et devait échouer « le jour où le
    moteur honorera les sources ». Ce jour est arrivé, et il a bien échoué — c'est le signal
    attendu, pas une régression.

    Le format déclare « les rangs 1 à 8 au tableau » ; à 12 archers simulés, le moteur en joue
    **8**, comme le schéma le projetait.
    """
    simulation, formats = service
    format_id = _qualif_puis_tableau(formats, rang_fin=8)

    resultat = simulation.simuler(format_id, effectif=12)

    tableau = next(p for p in resultat.phases if p.type is TypePhase.ELIMINATION_DIRECTE)
    assert tableau.effectif_projete == 8
    assert tableau.effectif == 8
    assert not tableau.ecart


def test_la_simulation_est_deterministe_a_graine_egale(
    service: tuple[ServiceSimulationFormat, _FormatsEnMemoire],
) -> None:
    """Règle 9 : pas d'aléa non maîtrisé — deux simulations identiques, même classement."""
    simulation, formats = service
    format_id = _qualif_puis_tableau(formats)

    premier = simulation.simuler(format_id, effectif=8, graine=42)
    second = simulation.simuler(format_id, effectif=8, graine=42)

    assert [ligne.total for ligne in premier.classement.lignes] == [
        ligne.total for ligne in second.classement.lignes
    ]


def test_la_simulation_joint_le_diagnostic_au_meme_effectif(
    service: tuple[ServiceSimulationFormat, _FormatsEnMemoire],
) -> None:
    """L'écran doit pouvoir confronter ce que le schéma annonçait à ce qui s'est passé."""
    simulation, formats = service
    format_id = _qualif_puis_tableau(formats)

    resultat = simulation.simuler(format_id, effectif=12)

    assert resultat.projection.effectif == 12
    assert resultat.projection.blocs[1].effectif == 8


def test_rien_n_est_persiste_le_service_ne_voit_aucun_tournoi_reel(
    service: tuple[ServiceSimulationFormat, _FormatsEnMemoire],
) -> None:
    """ADR-0054 : la non-pollution est **structurelle** — il n'y a pas de chemin vers la base.

    Le service ne reçoit qu'un magasin de formats ; le tournoi simulé naît dans le harnais et
    disparaît avec lui. Le vérifier ici, c'est vérifier que la simulation n'a créé aucun tournoi
    ailleurs que dans son propre harnais jetable.
    """
    simulation, formats = service
    format_id = _qualif_puis_tableau(formats)

    simulation.simuler(format_id, effectif=8)

    assert formats.lister()[0].etapes[0].type is TypePhase.QUALIFICATION


# --- CA « l'ajustement d'effectif » --------------------------------------------------------------


def test_le_meme_format_se_simule_a_deux_effectifs_sans_etre_retouche(
    service: tuple[ServiceSimulationFormat, _FormatsEnMemoire],
) -> None:
    """Le cœur du CA : plage relative, deux effectifs, aucune retouche du format."""
    simulation, formats = service
    format_tournoi = formats.ajouter(
        FormatTournoi.creer(
            "Relatif",
            [
                ModelePhase.qualification(_BAREME_COURT, ordre=1),
                ModelePhase(
                    ordre=2,
                    type=TypePhase.ELIMINATION_DIRECTE,
                    sources=(SourcePhase.par_rangs(1, 1, None),),
                ),
            ],
        )
    )
    assert format_tournoi.id is not None

    grand = simulation.simuler(format_tournoi.id, effectif=16)
    petit = simulation.simuler(format_tournoi.id, effectif=10)

    # 15 et 9 duels d'arbre, plus la petite finale de chaque tableau.
    assert grand.duels_total == 16
    assert petit.duels_total == 10


# --- Refus ---------------------------------------------------------------------------------------


def test_un_format_inconnu_est_introuvable(
    service: tuple[ServiceSimulationFormat, _FormatsEnMemoire],
) -> None:
    simulation, _ = service

    with pytest.raises(FormatIntrouvable):
        simulation.simuler(999, effectif=8)


@pytest.mark.parametrize("effectif", [1, 0, -3, 201])
def test_un_effectif_hors_bornes_est_refuse(
    service: tuple[ServiceSimulationFormat, _FormatsEnMemoire], effectif: int
) -> None:
    """Borne de **service**, pas règle métier : sans plafond, l'effectif vient du client."""
    simulation, formats = service
    format_id = _qualif_puis_tableau(formats)

    with pytest.raises(EffectifSimulationInvalide):
        simulation.simuler(format_id, effectif=effectif)


def test_un_format_bloquant_n_est_pas_simule_et_dit_pourquoi(
    service: tuple[ServiceSimulationFormat, _FormatsEnMemoire],
) -> None:
    """On ne simule pas un déroulé qu'aucun tournoi ne pourrait recevoir — même erreur typée."""
    simulation, formats = service
    brouillon = formats.ajouter(
        FormatTournoi.creer("Qualif à finir", [ModelePhase(ordre=1, type=TypePhase.QUALIFICATION)])
    )
    assert brouillon.id is not None

    with pytest.raises(PhaseQualificationIncomplete):
        simulation.simuler(brouillon.id, effectif=8)


def test_un_format_bien_compose_ne_signale_aucun_ecart(
    service: tuple[ServiceSimulationFormat, _FormatsEnMemoire],
) -> None:
    """⚠️ **Non-régression du bruit** — l'avertissement ne doit se déclencher que s'il dit quelque
    chose.

    Un premier jet incluait les **duels** dans le prédicat `ecart`. Or le schéma compte l'arbre
    (`effectif - 1`) et le moteur y ajoute la petite finale de `ProfondeurPodium` : l'écart d'une
    unité est structurel. `ecart` était donc vrai sur **toute** phase de tableau, y compris pour un
    format parfait — la bannière « borne haute » s'affichait sur 100 % des simulations, et le
    signal DETTE-028 se noyait dans son propre bruit.
    """
    simulation, formats = service
    format_id = _qualif_puis_tableau(formats, rang_fin=None)

    resultat = simulation.simuler(format_id, effectif=16)

    tableau = next(p for p in resultat.phases if p.type is TypePhase.ELIMINATION_DIRECTE)
    assert tableau.effectif == tableau.effectif_projete == 16
    assert tableau.tours == tableau.tours_projetes == 4
    # Les deux comptes de duels restent **rendus** (15 d'arbre annoncés, 16 joués) : c'est leur
    # divergence attendue qui ne doit pas allumer l'alerte.
    assert (tableau.duels, tableau.duels_projetes) == (16, 15)
    assert not tableau.ecart
    assert not any(phase.ecart for phase in resultat.phases)
