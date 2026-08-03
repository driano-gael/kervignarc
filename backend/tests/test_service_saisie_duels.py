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

import datetime
from dataclasses import replace

import pytest

from application.classements import ServiceClassement
from application.erreurs import DuelDesynchronise, PhasePasUnTableau
from application.saisie_duels import EtatDuel, ServiceSaisieDuels
from domain.bareme import BaremeQualification
from domain.blason import Blason, ZoneScore
from domain.categorie import Categorie
from domain.classement import StatutClassement
from domain.duel import BaremeDuel, Duel, ModeDuel, ResolveurBaremeDuelFfta
from domain.entree_audit import ActionAuditee, EntreeAudit
from domain.erreurs import EffectifTableauInvalide, MatchNonJouable
from domain.forfait import Forfait, NatureForfait
from domain.phase import IssueTour, Phase, PhaseId, SourcePhase, TypePhase
from domain.politiques import (
    ByesAuxMieuxClasses,
    PlacementEnCascade,
    ProfondeurPodium,
    SeedingSerpent,
)
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxForfaitRepository,
)
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
        self.forfaits = FauxForfaitRepository()
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
        # Phase de qualification (pour les tests de scope de phase du forfait, E04US015) : le
        # classement lit ses forfaits, le tableau lit les siens — les deux ne se mélangent pas.
        qualif = self.phases.ajouter(
            Phase.qualification(self.tournoi_id, BaremeQualification.creer(1, 3))
        )
        assert qualif.id is not None
        self.qualif_id = qualif.id

    def inscrire_classe(self, valeurs: tuple[str, ...]) -> int:
        from domain.archer import Archer

        archer = self.archers.ajouter(
            Archer(nom="N", prenom="P", tournoi_id=self.tournoi_id, categorie_id=self.categorie_id)
        )
        assert archer.id is not None
        self.series.semer(self.tournoi_id, archer.id, tuple(ZoneScore(v) for v in valeurs))
        return archer.id

    def service(self) -> ServiceSaisieDuels:
        classement = ServiceClassement(
            self.tournois, self.archers, self.series, self.categories, self.phases, self.forfaits
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
            ProfondeurPodium(),
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


def _forfait_duel(monde: _Monde, archer_id: int) -> Forfait:
    """Un forfait d'abandon de l'archer dans la phase de tableau du monde (E04US015, ADR-0050)."""
    return Forfait.creer(
        tournoi_id=monde.tournoi_id,
        archer_id=archer_id,
        phase_id=monde.phase_id,
        nature=NatureForfait.ABANDON,
        declare_par="Scoreur",
        declare_le=datetime.datetime(2026, 3, 14, 10, 0, tzinfo=datetime.UTC),
    )


def test_forfait_en_duel_fait_passer_l_adversaire() -> None:
    """CA E04US015 (ex-E12US004) : un duelliste forfait dans une phase de tableau **cède** son match
    — l'adversaire passe d'office (walkover), le tableau reste cohérent.

    Deux archers → un unique match (la finale). L'archer classé 2ᵉ abandonne : le 1ᵉ gagne d'office,
    le tableau est terminé et le podium le couronne, **sans qu'aucun tir n'ait été saisi**.
    """
    monde = _Monde()
    gagnant = monde.inscrire_classe(("10", "10"))  # rang 1
    forfaitaire = monde.inscrire_classe(("8", "8"))  # rang 2
    monde.forfaits.semer(_forfait_duel(monde, forfaitaire))
    etat = monde.service().etat_tableau(monde.tournoi_id, monde.phase_id)
    assert etat.est_termine
    assert etat.podium[0][0] == 1
    assert etat.podium[0][1].archer_id == gagnant


def test_annuler_le_forfait_de_duel_retire_le_walkover() -> None:
    """La réversibilité (`D-15`) : sans forfait enregistré, le match redevient à jouer."""
    monde = _Monde()
    monde.inscrire_classe(("10", "10"))
    perdant = monde.inscrire_classe(("8", "8"))
    forfait = monde.forfaits.semer(_forfait_duel(monde, perdant))
    trace = EntreeAudit.creer(
        tournoi_id=monde.tournoi_id,
        action=ActionAuditee.FORFAIT,
        auteur="Scoreur",
        horodatage=datetime.datetime(2026, 3, 14, 11, 0, tzinfo=datetime.UTC),
        objet="annulation",
    )
    monde.forfaits.annuler_avec_trace(forfait, trace)
    etat = monde.service().etat_tableau(monde.tournoi_id, monde.phase_id)
    assert not etat.est_termine
    assert etat.podium == ()


def _forfait(
    monde: _Monde,
    archer_id: int,
    phase_id: int,
    nature: NatureForfait = NatureForfait.ABANDON,
) -> Forfait:
    return Forfait.creer(
        tournoi_id=monde.tournoi_id,
        archer_id=archer_id,
        phase_id=phase_id,
        nature=nature,
        declare_par="Scoreur",
        declare_le=datetime.datetime(2026, 3, 14, 10, 0, tzinfo=datetime.UTC),
    )


def _classement_du(monde: _Monde) -> ServiceClassement:
    return ServiceClassement(
        monde.tournois, monde.archers, monde.series, monde.categories, monde.phases, monde.forfaits
    )


def test_forfait_de_duel_ne_relegue_pas_le_rang_de_qualif() -> None:
    """CA/ADR-0050 (scope de phase) : un forfait déclaré en **phase de tableau** ne touche PAS le
    classement de qualification — l'archer avait qualifié, il garde son rang et reste en lice."""
    monde = _Monde()
    fort = monde.inscrire_classe(("10", "10", "10"))  # rang 1
    monde.inscrire_classe(("8", "8"))  # rang 2
    monde.forfaits.semer(_forfait(monde, fort, monde.phase_id))  # forfait EN DUELS
    classement = _classement_du(monde).pour_tournoi(monde.tournoi_id)
    lignes = {ligne.archer_id: ligne for ligne in classement.lignes}
    assert lignes[fort].rang_scratch == 1  # rang de qualif intact
    assert lignes[fort].statut is StatutClassement.EN_LICE


def test_forfait_de_qualif_est_exclu_du_bracket() -> None:
    """CA/ADR-0050 (scope de phase) : un abandon déclaré en **qualification** exclut l'archer de
    l'ensemencement du tableau — il n'apparaît dans aucun duel."""
    monde = _Monde()
    forfaitaire = monde.inscrire_classe(("10", "10", "10"))  # rang 1, mais abandon en qualif
    b = monde.inscrire_classe(("9", "9"))
    c = monde.inscrire_classe(("8", "8"))
    monde.forfaits.semer(_forfait(monde, forfaitaire, monde.qualif_id))  # forfait EN QUALIF
    etat = monde.service().etat_tableau(monde.tournoi_id, monde.phase_id)
    dans_tableau = {d.archer_id for m in etat.duels for d in (m.haut, m.bas) if d is not None}
    assert forfaitaire not in dans_tableau  # exclu du bracket
    assert dans_tableau == {b, c}  # seuls les deux en-lice s'affrontent


def test_walkover_se_propage_au_tour_suivant() -> None:
    """CA « impact correct sur la progression » : un forfait au tour 1 fait avancer l'adversaire
    jusqu'au tour 2 (walkover propagé, pas seulement une finale à deux)."""
    monde = _Monde()
    a = monde.inscrire_classe(("10", "10", "10"))  # rang 1 (affronte le rang 4 au tour 1)
    b = monde.inscrire_classe(("10", "10", "9"))  # rang 2
    c = monde.inscrire_classe(("10", "9", "9"))  # rang 3
    d = monde.inscrire_classe(("9", "9", "9"))  # rang 4
    monde.forfaits.semer(_forfait(monde, d, monde.phase_id))  # d abandonne → a passe d'office
    etat = monde.service().etat_tableau(monde.tournoi_id, monde.phase_id)
    finale = next(m for m in etat.duels if m.place_en_jeu == (1, 2))
    occupants = {m.archer_id for m in (finale.haut, finale.bas) if m is not None}
    assert a in occupants  # a a avancé au tour 2 par walkover
    _ = (b, c)


def test_double_forfait_le_camp_haut_avance() -> None:
    """Convention ADR-0050 : deux forfaits face à face → le camp **haut** (mieux classé) avance."""
    monde = _Monde()
    a = monde.inscrire_classe(("10", "10", "10"))  # rang 1 (haut du match 1v4)
    monde.inscrire_classe(("10", "10", "9"))  # rang 2
    monde.inscrire_classe(("10", "9", "9"))  # rang 3
    d = monde.inscrire_classe(("9", "9", "9"))  # rang 4 (bas du match 1v4)
    monde.forfaits.semer(_forfait(monde, a, monde.phase_id))
    monde.forfaits.semer(_forfait(monde, d, monde.phase_id))
    etat = monde.service().etat_tableau(monde.tournoi_id, monde.phase_id)
    finale = next(m for m in etat.duels if m.place_en_jeu == (1, 2))
    occupants = {m.archer_id for m in (finale.haut, finale.bas) if m is not None}
    assert a in occupants  # le haut (rang 1) avance malgré son forfait
    assert d not in occupants


# --- CA E05US020 : le moteur consomme les prélèvements déclarés (résorbe DETTE-028) -------------
# Écrits **depuis le CA** de `stories/E05-moteur-phases.md` (puce « CA ») avant l'implémentation :
# jusqu'ici `_decor` ensemençait le tableau avec *tous* les archers en lice, quel que soit ce que la
# phase déclarait prélever — l'organisateur composait « les rangs 1 à 32 » et le moteur en jouait
# 120.


def _monde_classe(nb: int) -> _Monde:
    """`nb` archers aux scores décroissants : le rang scratch suit l'ordre de création."""
    monde = _Monde()
    for rang in range(nb):
        monde.inscrire_classe(("10", "10", str(max(1, 10 - rang))))
    return monde


def _prelever(monde: _Monde, *sources: SourcePhase) -> None:
    """Déclare les prélèvements de la phase de tableau (elle est d'ordre 2, la qualif d'ordre 1)."""
    phase = monde.phases.par_id(monde.phase_id)
    assert phase is not None
    monde.phases._phases[monde.phase_id] = replace(phase, sources=sources)


def _effectif_du_tableau(monde: _Monde) -> int:
    return monde.service().etat_tableau(monde.tournoi_id, monde.phase_id).effectif


def _archers_du_tableau(monde: _Monde) -> list[int]:
    tableau, _ = monde.service().reconstruire(monde.tournoi_id, monde.phase_id)
    vus: dict[int, None] = {}
    for match in tableau.matchs:
        for camp in (match.haut, match.bas):
            if camp is not None:
                vus.setdefault(camp.ref_id, None)
    return list(vus)


def test_le_tableau_ne_prend_que_les_rangs_declares() -> None:
    """CA « prélèvement par rangs » : « les rangs 1 à 8 de la phase 1 » monte un tableau de **8**.

    C'est le cœur de DETTE-028 : à 12 archers classés, le moteur en jouait 12 et l'organisateur
    repartait avec un tournoi qui ne se déroulait pas comme le schéma qu'il avait validé.
    """
    monde = _monde_classe(12)
    _prelever(monde, SourcePhase.par_rangs(ordre_source=1, rang_debut=1, rang_fin=8))

    assert _effectif_du_tableau(monde) == 8


def test_le_tableau_prend_les_bons_archers_pas_seulement_le_bon_compte() -> None:
    """Un compte juste sur les mauvais archers serait un faux positif : on vérifie l'**identité**.

    Les rangs 1 à 8 sont les huit **premiers du classement** — pas huit archers quelconques.
    """
    monde = _monde_classe(12)
    attendus = [ligne.archer_id for ligne in _classement_du(monde).pour_tournoi(1).lignes[:8]]
    _prelever(monde, SourcePhase.par_rangs(ordre_source=1, rang_debut=1, rang_fin=8))

    assert sorted(_archers_du_tableau(monde)) == sorted(attendus)


def test_une_plage_ouverte_se_resout_sur_l_effectif_reel() -> None:
    """CA « plage relative » : « les rangs 9 **et suivants** » vaut 4 archers à 12 classés.

    C'est la promesse d'E05US010 (`rang_fin=None`, « et tous les suivants ») — tenue jusqu'ici par
    la seule composition. Le même déroulé doit accueillir un effectif qu'il ne connaissait pas.
    """
    monde = _monde_classe(12)
    _prelever(monde, SourcePhase.par_rangs(ordre_source=1, rang_debut=9))

    assert _effectif_du_tableau(monde) == 4


def test_une_plage_ouverte_suit_l_effectif_quand_il_change() -> None:
    """Le même prélèvement, deux effectifs : c'est ce que « relative » veut dire."""
    petit = _monde_classe(10)
    _prelever(petit, SourcePhase.par_rangs(ordre_source=1, rang_debut=5))
    grand = _monde_classe(16)
    _prelever(grand, SourcePhase.par_rangs(ordre_source=1, rang_debut=5))

    assert (_effectif_du_tableau(petit), _effectif_du_tableau(grand)) == (6, 12)


def test_sans_source_declaree_le_tableau_prend_tout_le_monde() -> None:
    """CA « première phase » : le comportement d'aujourd'hui ne doit pas casser.

    Une phase sans prélèvement est alimentée par les inscriptions — c'est le cas de la
    qualification, et celui du tableau tant que l'organisateur n'a rien déclaré.
    """
    monde = _monde_classe(12)

    assert _effectif_du_tableau(monde) == 12


def test_le_rang_preleve_suit_le_classement_au_moment_de_la_lecture() -> None:
    """CA « le rang prélevé est celui du classement » : l'abandon du 5ᵉ ne laisse **pas** de trou.

    Un abandon est relégué en fin de classement (ADR-0050) et les suivants **remontent** : « les
    rangs 1 à 8 » prélève donc toujours 8 archers, le 9ᵉ prenant la place laissée. Ce n'est pas un
    repêchage décidé par le moteur, c'est la conséquence du classement, recalculé à chaque lecture.
    """
    monde = _monde_classe(12)
    avant = [ligne.archer_id for ligne in _classement_du(monde).pour_tournoi(1).lignes]
    cinquieme, neuvieme = avant[4], avant[8]
    monde.forfaits.semer(_forfait(monde, cinquieme, monde.qualif_id))
    _prelever(monde, SourcePhase.par_rangs(ordre_source=1, rang_debut=1, rang_fin=8))

    archers = _archers_du_tableau(monde)
    assert _effectif_du_tableau(monde) == 8
    assert cinquieme not in archers
    assert neuvieme in archers


def test_un_prelevement_par_issue_de_tour_reste_inerte() -> None:
    """Hors périmètre, **épinglé** : `par_issue_de_tour` n'est résolu nulle part (`DETTE-033`).

    Le moteur retombe donc sur « tous les archers en lice » plutôt que de deviner une sémantique
    que la séquence n'a pas tranchée. Ce test **tombera** le jour où l'US du prélèvement la
    décidera — c'est le signal attendu.
    """
    monde = _monde_classe(12)
    _prelever(
        monde, SourcePhase.par_issue_de_tour(ordre_source=1, tour=1, issue=IssueTour.GAGNANTS)
    )

    assert _effectif_du_tableau(monde) == 12


def test_deux_sources_de_rangs_se_cumulent() -> None:
    """L'exemple canonique du commanditaire : « les demi-finalistes **et** le gagnant du
    secondaire ».

    Une phase porte **plusieurs** prélèvements (ADR-0061) ; le tableau prend leur **union**.
    Relevé en revue : le `any(...)` du service n'était jamais exercé à plus d'un intervalle.
    """
    monde = _monde_classe(12)
    ordonnes = [ligne.archer_id for ligne in _classement_du(monde).pour_tournoi(1).lignes]
    _prelever(
        monde,
        SourcePhase.par_rangs(ordre_source=1, rang_debut=1, rang_fin=4),
        SourcePhase.par_rangs(ordre_source=1, rang_debut=9, rang_fin=12),
    )

    assert _effectif_du_tableau(monde) == 8
    assert sorted(_archers_du_tableau(monde)) == sorted(ordonnes[:4] + ordonnes[8:])


def test_l_effectif_source_compte_les_classes_pas_les_inscrits() -> None:
    """« Les rangs 9 **et suivants** » se résout sur les archers **classés**, pas sur les inscrits.

    Un disqualifié est **sorti** du classement (ADR-0050) : il n'a pas de rang. Le compter
    étendrait « et suivants » jusqu'à un rang qui n'existe pas — la même erreur que l'écrêtage
    d'ADR-0065 a corrigée sur les plages de tableau. Relevé en revue : deux mutations de cette
    ligne survivaient, alors que c'est la plus commentée du diff.
    """
    monde = _monde_classe(12)
    dernier = _classement_du(monde).pour_tournoi(1).lignes[-1].archer_id
    monde.forfaits.semer(
        _forfait(monde, dernier, monde.qualif_id, nature=NatureForfait.DISQUALIFICATION)
    )
    _prelever(monde, SourcePhase.par_rangs(ordre_source=1, rang_debut=9))

    # 11 archers classés (le DSQ est sorti) → les rangs 9, 10 et 11, soit 3 archers.
    assert _effectif_du_tableau(monde) == 3


def test_une_source_qui_ne_vise_pas_la_qualification_est_ignoree() -> None:
    """CA, note (b) : une source dont la phase amont **n'est pas la qualification** garde le
    comportement d'avant l'US.

    Le service ne sait lire qu'**un** classement, celui de la qualification. Appliquer « les rangs
    1 à 8 de la phase 2 » à ce classement-là prendrait les 8 premiers de la **qualification** en
    croyant prendre ceux du tableau principal : un tableau bien formé, plausible, et faux, que rien
    ne signalerait. Défaut relevé en revue — le CA promettait déjà ce comportement, le code ne le
    tenait pas.
    """
    monde = _monde_classe(12)
    _prelever(monde, SourcePhase.par_rangs(ordre_source=2, rang_debut=1, rang_fin=8))

    assert _effectif_du_tableau(monde) == 12


def test_un_prelevement_le_reste_reste_inerte() -> None:
    """Jumeau du test sur `par_issue_de_tour` : `le_reste` n'est résolu nulle part non plus.

    L'ADR, la docstring, le message de l'écran et la recette nomment **les deux** systématiquement ;
    les épingler tous les deux évite qu'un seul soit décidé en silence un jour.
    """
    monde = _monde_classe(12)
    _prelever(monde, SourcePhase.le_reste(ordre_source=1))

    assert _effectif_du_tableau(monde) == 12


def test_un_prelevement_qui_ne_garde_personne_refuse_de_monter_un_tableau() -> None:
    """« Les rangs 33 et suivants » avec 12 classés ne prélève **personne** — et le dit.

    Le déroulé est mal composé : la phase déclare un prélèvement que l'effectif réel ne peut pas
    honorer, et le contrôle de composition ne le voit pas (il compare à l'effectif **déclaré**, pas
    au réel). Le moteur **refuse** plutôt que d'inventer un tableau : `EffectifTableauInvalide`, que
    la frontière traduit — un écran qui dit « ce tableau ne peut pas se monter » vaut mieux qu'un
    tableau silencieusement peuplé de tout le monde, qui est précisément le défaut que cette US
    corrige. Comportement **décidé**, pas accidentel (relevé en revue).
    """
    monde = _monde_classe(12)
    _prelever(monde, SourcePhase.par_rangs(ordre_source=1, rang_debut=33))

    with pytest.raises(EffectifTableauInvalide):
        _effectif_du_tableau(monde)
