"""Tests du service `ServiceSaisieDuels` (E04US013) — repositories factices.

Ici vit l'**orchestration** dérivée du CA (ADR-0049) : à partir d'un **classement**, l'arbre est
construit, un duel se saisit et se valide, et son **vainqueur fait avancer le tableau** (« transmis
au moteur E05US005 »). Le scoring pur (sets/cumul/barrage) est couvert par `test_domain_duel` ; on
vérifie ici la reconstruction + rejeu, la résolution du **barème par arme**, et les gardes.

Fakes en mémoire conformes aux ports ; le classement est **vrai** (`ServiceClassement` sur des
séries semées) pour un ensemencement réaliste et déterministe. On réutilise les doubles du jumeau
(plan de duels), qui reconstruit le même arbre.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from application.classements import ServiceClassement
from application.erreurs import DuelDesynchronise, PhasePasUnTableau
from application.saisie_duels import EtatDuel, ServiceSaisieDuels
from domain.bareme import BaremeQualification
from domain.blason import Blason, ZoneScore
from domain.categorie import Categorie
from domain.duel import BaremeDuel, Duel, ModeDuel, ResolveurBaremeDuelFfta
from domain.erreurs import MatchNonJouable
from domain.phase import Phase, PhaseId, TypePhase
from domain.politiques import ByesAuxMieuxClasses, EliminationSeche, SeedingSerpent
from tests.conftest import FauxArcherRepository, FauxCategorieRepository
from tests.test_service_placement_duels import (
    FauxBlasonRepository,
    FauxPhaseRepository,
    FauxSerieRepository,
    FauxTournoiRepository,
)

ZONES_TRIPLE = (
    ZoneScore.DIX,
    ZoneScore.NEUF,
    ZoneScore.HUIT,
    ZoneScore.SEPT,
    ZoneScore.SIX,
    ZoneScore.MANQUE,
)


class FauxDuelRepository:
    """Double de `DuelRepository` : ne garde que le **tir** ; réinjecte le contexte à `charger`."""

    def __init__(self) -> None:
        self._tirs: dict[tuple[int, int], Duel] = {}

    def numeros_enregistres(self, phase_id: PhaseId) -> frozenset[int]:
        return frozenset(numero for (phase, numero) in self._tirs if phase == phase_id)

    def charger(self, phase_id: PhaseId, match_numero: int, *, bareme: BaremeDuel) -> Duel | None:
        duel = self._tirs.get((phase_id, match_numero))
        if duel is None:
            return None
        # Mime « le tir + l'identité des duellistes sont persistés » : seul le barème est réinjecté
        # (dérivé de l'arme, ADR-0049). Les participants **stockés** sont conservés.
        return replace(duel, bareme=bareme)

    def enregistrer(self, phase_id: PhaseId, match_numero: int, duel: Duel) -> Duel:
        self._tirs[(phase_id, match_numero)] = duel
        return duel


class _Monde:
    """Décor : un tournoi, une catégorie (arme + blason), N archers classés, une phase de tableau.

    Les archers reçoivent des scores **décroissants** dans l'ordre de création → rang scratch 1..N.
    """

    def __init__(self, *, arme: str = "Arc Classique", avec_blason: bool = True) -> None:
        self.tournoi_id = 1
        self.tournois = FauxTournoiRepository({1})
        self.phases = FauxPhaseRepository()
        self.archers = FauxArcherRepository()
        self.categories = FauxCategorieRepository()
        self.blasons = FauxBlasonRepository()
        self.series = FauxSerieRepository()
        self.duels = FauxDuelRepository()
        blason_id: int | None = None
        if avec_blason:
            blason = self.blasons.ajouter(
                Blason.creer(self.tournoi_id, "Triple", taille=0.25, capacite=1)
            )
            assert blason.id is not None
            # Zones du triple 40 (pas de 5 → 1) — pour un pavé de duel réaliste.
            self.blasons._blasons[blason.id] = replace(blason, zones=ZONES_TRIPLE)
            blason_id = blason.id
        categorie = self.categories.ajouter(
            Categorie.creer(self.tournoi_id, "Cat", arme=arme, blason_id=blason_id, hauteur_cm=130)
        )
        assert categorie.id is not None
        self.categorie_id = categorie.id
        phase = self.phases.ajouter(Phase.creer(self.tournoi_id, 2, TypePhase.ELIMINATION_DIRECTE))
        assert phase.id is not None
        self.phase_id = phase.id

    def inscrire_classe(self, valeurs: tuple[str, ...]) -> int:
        from domain.archer import Archer

        archer = self.archers.ajouter(
            Archer(nom="N", prenom="P", tournoi_id=self.tournoi_id, categorie_id=self.categorie_id)
        )
        assert archer.id is not None
        self.series.semer(self.tournoi_id, archer.id, tuple(ZoneScore(v) for v in valeurs))
        return archer.id

    def service(self) -> ServiceSaisieDuels:
        classement = ServiceClassement(self.tournois, self.archers, self.series, self.categories)
        return ServiceSaisieDuels(
            self.tournois,
            self.phases,
            self.categories,
            self.blasons,
            self.duels,
            classement,
            ResolveurBaremeDuelFfta(),
            SeedingSerpent(),
            ByesAuxMieuxClasses(),
            EliminationSeche(),
        )


def _gagner_manches(service: ServiceSaisieDuels, monde: _Monde, numero: int, cote: str) -> EtatDuel:
    """Fait gagner 6-0 le camp `cote` du match `numero` (3 manches), puis valide."""
    haut = ("10", "10", "10") if cote == "haut" else ("6", "6", "6")
    bas = ("6", "6", "6") if cote == "haut" else ("10", "10", "10")
    for manche in (1, 2, 3):
        service.saisir_manche(
            monde.tournoi_id,
            monde.phase_id,
            numero,
            manche,
            tuple(ZoneScore(v) for v in haut),
            tuple(ZoneScore(v) for v in bas),
        )
    return service.valider(monde.tournoi_id, monde.phase_id, numero, "DURAND")


def test_vainqueur_valide_avance_le_tableau() -> None:
    """CA vainqueur : les gagnants des demis peuplent la finale (transmis au moteur E05US005)."""
    monde = _Monde()
    a = monde.inscrire_classe(("10", "10", "10"))  # rang 1
    b = monde.inscrire_classe(("10", "10", "9"))  # rang 2
    c = monde.inscrire_classe(("10", "9", "9"))  # rang 3
    d = monde.inscrire_classe(("9", "9", "9"))  # rang 4
    service = monde.service()

    # Tour 1 (serpent : 1v4, 2v3). On identifie les demi-finales par leurs occupants.
    etat = service.etat_tableau(monde.tournoi_id, monde.phase_id)
    demis = {m.numero: (m.haut, m.bas) for m in etat.duels if m.tour == 1}
    assert len(demis) == 2

    # Le mieux classé de chaque demi gagne (a et b, rangs 1 et 2).
    for numero, (haut, _bas) in demis.items():
        gagnant_cote = "haut" if haut is not None and haut.archer_id in (a, b) else "bas"
        _gagner_manches(service, monde, numero, gagnant_cote)

    # La finale (tour 2) oppose désormais a et b : la progression a été transmise au moteur.
    apres = service.etat_tableau(monde.tournoi_id, monde.phase_id)
    finale = next(m for m in apres.duels if m.place_en_jeu == (1, 2))
    assert finale.haut is not None and finale.bas is not None
    assert {finale.haut.archer_id, finale.bas.archer_id} == {a, b}
    assert finale.duel is None  # pas encore joué
    _ = (c, d)


def test_barème_résolu_par_arme_poulies_donne_le_cumul() -> None:
    """CA sets : une catégorie **arc à poulies** score le duel **au cumul** (A.7.5.2)."""
    monde = _Monde(arme="Arc à Poulies")
    monde.inscrire_classe(("10", "10", "10"))
    monde.inscrire_classe(("9", "9", "9"))
    service = monde.service()
    numero = next(m.numero for m in service.etat_tableau(1, monde.phase_id).duels if m.tour == 1)
    etat = service.saisir_manche(
        1, monde.phase_id, numero, 1, (ZoneScore.DIX,) * 3, (ZoneScore.NEUF,) * 3
    )
    assert etat.duel is not None
    assert etat.duel.bareme.mode is ModeDuel.CUMUL


def test_finale_pas_saisissable_avant_les_demies() -> None:
    """On ne saisit pas un match dont les adversaires ne sont pas encore connus (tour 2)."""
    monde = _Monde()
    for valeurs in (("10", "10", "10"), ("10", "10", "9"), ("10", "9", "9"), ("9", "9", "9")):
        monde.inscrire_classe(valeurs)
    service = monde.service()
    duels = service.etat_tableau(1, monde.phase_id).duels
    finale = next(m for m in duels if m.place_en_jeu == (1, 2))
    with pytest.raises(MatchNonJouable):
        service.saisir_manche(
            1, monde.phase_id, finale.numero, 1, (ZoneScore.DIX,) * 3, (ZoneScore.NEUF,) * 3
        )


def test_duel_desynchronise_quand_le_classement_change() -> None:
    """ADR-0049 §4 : un tir validé n'est **jamais** ré-attribué au mauvais couple après re-seed.

    On score et valide la finale (a bat b), puis une correction de qualif fait passer b devant a :
    la finale oppose désormais b (haut) vs a (bas). Le tir enregistré (a vs b) **diverge** — il est
    masqué (pas de vainqueur avancé en silence) et toute écriture dessus est refusée (409).
    """
    monde = _Monde()
    a = monde.inscrire_classe(("10", "10", "10"))  # rang 1
    b = monde.inscrire_classe(("9", "9", "9"))  # rang 2
    service = monde.service()
    numero = next(m.numero for m in service.etat_tableau(1, monde.phase_id).duels if m.tour == 1)
    _gagner_manches(service, monde, numero, "haut")  # a (haut) gagne et valide

    # Correction de qualification : b passe devant a.
    monde.series._series = []
    monde.series.semer(1, b, tuple(ZoneScore(v) for v in ("10", "10", "10")))
    monde.series.semer(1, a, tuple(ZoneScore(v) for v in ("9", "9", "9")))

    apres = service.etat_tableau(1, monde.phase_id)
    finale = next(m for m in apres.duels if m.place_en_jeu == (1, 2))
    assert finale.haut is not None and finale.haut.archer_id == b  # b est désormais tête n°1
    assert finale.duel is None  # tir divergent masqué
    assert apres.est_termine is False  # aucun vainqueur avancé en silence
    with pytest.raises(DuelDesynchronise):
        service.saisir_manche(
            1, monde.phase_id, numero, 1, (ZoneScore.DIX,) * 3, (ZoneScore.NEUF,) * 3
        )


def test_match_bye_pas_saisissable() -> None:
    """Un match gagné d'office (bye, effectif impair) n'a pas de duel (`MatchNonJouable`)."""
    monde = _Monde()
    for valeurs in (("10", "10", "10"), ("9", "9", "9"), ("8", "8", "8")):  # 3 archers → 1 bye
        monde.inscrire_classe(valeurs)
    service = monde.service()
    bye = next(m for m in service.etat_tableau(1, monde.phase_id).duels if m.est_bye)
    with pytest.raises(MatchNonJouable):
        service.saisir_manche(
            1, monde.phase_id, bye.numero, 1, (ZoneScore.DIX,) * 3, (ZoneScore.NEUF,) * 3
        )


def test_lecture_expose_le_bareme_et_les_zones_du_pave() -> None:
    """Le pavé du front est déterminé côté serveur dès qu'un match est **jouable**, avant tout tir.

    L'état d'un match expose le barème (mode, nb de manches, de flèches, seuil) et les zones légales
    du blason tiré — l'analogue duel de ce que la grille + le barème de qualification livrent au
    poste (E04US002). Un arc classique tire en **sets**, premier à 6, 5 manches de 3 flèches.
    """
    monde = _Monde()  # arc classique, blason « triple »
    monde.inscrire_classe(("10", "10", "10"))
    monde.inscrire_classe(("9", "9", "9"))
    service = monde.service()

    finale = next(
        m for m in service.etat_tableau(1, monde.phase_id).duels if m.place_en_jeu == (1, 2)
    )
    assert finale.duel is None  # aucun tir encore
    assert finale.bareme is not None
    assert finale.bareme.mode is ModeDuel.SETS
    assert finale.bareme.nb_manches == 5
    assert finale.bareme.nb_fleches_par_volee == 3
    assert finale.bareme.points_pour_gagner == 6
    assert finale.zones == ZONES_TRIPLE  # zones légales du blason, pour le pavé


def test_lecture_pas_de_bareme_ni_zones_hors_match_jouable() -> None:
    """Un bye (gagné d'office) n'a pas de pavé : ni barème ni zones (rien à saisir)."""
    monde = _Monde()
    for valeurs in (("10", "10", "10"), ("9", "9", "9"), ("8", "8", "8")):  # 3 archers → 1 bye
        monde.inscrire_classe(valeurs)
    service = monde.service()
    bye = next(m for m in service.etat_tableau(1, monde.phase_id).duels if m.est_bye)
    assert bye.bareme is None
    assert bye.zones == ()


def test_lecture_zones_vides_si_blason_indeterminable() -> None:
    """Best-effort en lecture : blason introuvable → pavé **vide**, sans faire échouer le tableau.

    Le chemin d'écriture reste strict (`BlasonIntrouvable`, 404) ; la lecture, elle, tolère — le
    front affichera « pavé indisponible » sur ce match plutôt que de perdre tout le tableau, comme
    la grille de qualification renvoie des zones vides (E04US002).
    """
    monde = _Monde(avec_blason=False)  # catégorie sans blason → zones indéterminables
    monde.inscrire_classe(("10", "10", "10"))
    monde.inscrire_classe(("9", "9", "9"))
    service = monde.service()

    finale = next(
        m for m in service.etat_tableau(1, monde.phase_id).duels if m.place_en_jeu == (1, 2)
    )
    assert finale.bareme is not None  # le barème (par arme) reste résolu, lui
    assert finale.zones == ()  # zones vides, pas d'exception


def test_phase_de_qualification_refusee() -> None:
    """La saisie en duels ne vaut que pour une élimination directe (`PhasePasUnTableau`)."""
    monde = _Monde()
    monde.inscrire_classe(("10", "10", "10"))
    monde.inscrire_classe(("9", "9", "9"))
    quali = monde.phases.ajouter(
        Phase.qualification(monde.tournoi_id, BaremeQualification.preset_ffta_18m())
    )
    assert quali.id is not None
    service = monde.service()
    with pytest.raises(PhasePasUnTableau):
        service.etat_tableau(monde.tournoi_id, quali.id)
