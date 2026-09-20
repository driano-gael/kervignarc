"""Tests du service `ServiceSimulation` (E15US002) — depuis le CA (ADR-0054).

La **règle métier** de l'US vit ici, dérivée des critères d'acceptation :

- **Garde-fou** : on ne simule qu'un tournoi **avant démarrage** (`brouillon`/`prêt`) ; démarré/figé
  → `SimulationTournoiDemarre` (409). Tournoi inconnu → `TournoiIntrouvable`.
- **Rejeu éphémère fidèle** : le classement rejoué sur le harnais in-memory est **identique** à
  celui que calcule le même moteur sur les données réelles (l'hydratation ne perd rien).
- **Non-pollution (mécanisme)** : après une simulation, les repositories **réels** (côté lecture)
  sont **inchangés** — la simulation n'écrit que dans le harnais jetable. La non-pollution de la
  **vraie base SQLite** est prouvée à part (`test_simulation_non_pollution.py`).
- **Chemin duels** : sur une phase d'élimination directe, la simulation exerce placement + saisie de
  duels et renvoie l'état du tableau — sans rien persister.

On monte le côté « réel » avec les **adapters in-memory de production** (`infrastructure/memory`) :
ils implémentent les ports comme le feraient les adapters SQL, et l'US les double ainsi au passage.
Le harnais de simulation, lui, est fabriqué **neuf** par `_fabriquer_harnais` (comme la composition
root le fait en production).
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.classements import ServiceClassement
from application.erreurs import (
    SimulationTournoiDemarre,
    TournoiIntrouvable,
    TournoiSansDepart,
)
from application.simulation import CreneauSimule, ResultatSimulation, ServiceSimulation
from bootstrap.composition import fabriquer_harnais_simulation
from domain.archer import Archer
from domain.bareme import BaremeQualification
from domain.blason import Blason, ZoneScore
from domain.categorie import Categorie
from domain.depart import Depart
from domain.deroule_etape import EtapeDeroule
from domain.gabarit_salle import GabaritSalle
from domain.grain_validation import GrainValidation
from domain.inscription import Inscription
from domain.phase import TypePhase
from domain.serie import Serie, Volee
from domain.tournoi import StatutTournoi, Tournoi
from infrastructure.memory.repositories import (
    InMemoryArcherRepository,
    InMemoryBlasonRepository,
    InMemoryCategorieRepository,
    InMemoryDepartRepository,
    InMemoryDerouleRepository,
    InMemoryForfaitRepository,
    InMemoryGabaritSalleRepository,
    InMemoryInscriptionRepository,
    InMemoryPhaseRepository,
    InMemorySerieRepository,
    InMemoryTournoiRepository,
)

_DATE = datetime.date(2026, 3, 14)
_ZONES_TRIPLE = (
    ZoneScore.DIX,
    ZoneScore.NEUF,
    ZoneScore.HUIT,
    ZoneScore.SEPT,
    ZoneScore.SIX,
    ZoneScore.MANQUE,
)


class _Reel:
    """Le côté « réel » (lu par la simulation) : adapters in-memory de production peuplés.

    Un tournoi `brouillon` par défaut ; des archers classés par des séries décroissantes ; en
    option une catégorie armée, un blason zoné, un gabarit et une phase de tableau (chemin duels).
    """

    def __init__(self, *, avec_tableau: bool = False) -> None:
        self.tournois = InMemoryTournoiRepository()
        self.archers = InMemoryArcherRepository()
        self.categories = InMemoryCategorieRepository()
        self.blasons = InMemoryBlasonRepository()
        self.gabarits = InMemoryGabaritSalleRepository()
        self.inscriptions = InMemoryInscriptionRepository()
        self.deroules = InMemoryDerouleRepository()
        # Le créneau conventionnel de ce décor (`depart_id=1` dans les inscriptions ci-dessous) :
        # le classement est celui d'un départ depuis ADR-0075, il doit donc exister vraiment.
        self.departs = InMemoryDepartRepository()
        self.departs.ajouter(
            dataclasses.replace(
                Depart.creer(tournoi_id=1, numero=1, tarif_centimes=800, horaire="09:00"), id=1
            )
        )
        self.phases = InMemoryPhaseRepository(self.departs, self.deroules)
        self.series = InMemorySerieRepository()

        tournoi = self.tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
        assert tournoi.id is not None
        self.tournoi_id = tournoi.id

        blason = self.blasons.ajouter(
            Blason.creer(self.tournoi_id, "Triple", taille=0.25, capacite=1)
        )
        assert blason.id is not None
        self.blasons.enregistrer(dataclasses.replace(blason, zones=_ZONES_TRIPLE))
        categorie = self.categories.ajouter(
            Categorie.creer(
                self.tournoi_id, "Sénior Homme", arme="Arc Classique", blason_id=blason.id
            )
        )
        assert categorie.id is not None
        self.categorie_id = categorie.id

        # E05US025 : une feuille de marque pend à sa phase (ADR-0082), et le classement se lit
        # sur elle. Ce décor ne posait que le tableau ; il lui faut désormais la qualification, qui
        # est de toute façon ce que la simulation rejoue (`SessionSimulation.phase_qualif_id`).
        etape_qualif = self.deroules.ajouter(
            EtapeDeroule(
                tournoi_id=self.tournoi_id,
                ordre=1,
                type=TypePhase.QUALIFICATION,
                bareme=BaremeQualification.creer(1, 3),
                validation=GrainValidation.fin_de_serie(),
            )
        )
        self._etape_qualif = etape_qualif
        qualif = self.phases.ajouter(etape_qualif.instancier(1))
        assert qualif.id is not None
        self.qualif_id = qualif.id

        self.phase_tableau_id: int | None = None
        self._etape_tableau: EtapeDeroule | None = None
        if avec_tableau:
            self.gabarits.ajouter(
                GabaritSalle(nom="Salle", capacites=(4,), tournoi_id=self.tournoi_id)
            )
            # Deux gestes depuis ADR-0076 : l'étape définit le tableau **au tournoi**, la phase en
            # porte l'avancement **dans le créneau**. Poser l'avancement seul est refusé par
            # l'adapter — une instance sans définition serait invisible à toute lecture.
            etape = self.deroules.ajouter(
                EtapeDeroule(
                    tournoi_id=self.tournoi_id, ordre=2, type=TypePhase.ELIMINATION_DIRECTE
                )
            )
            self._etape_tableau = etape
            phase = self.phases.ajouter(etape.instancier(1))
            assert phase.id is not None
            self.phase_tableau_id = phase.id

    def ajouter_creneau(self, numero: int, horaire: str, depart_id: int) -> int:
        """Un créneau de plus, avec **sa** qualification — et son tableau si le décor en a un.

        ⚠️ **L'étape est réutilisée, la phase est instanciée** (ADR-0076) : un déroulé se définit
        une fois au tournoi et porte un avancement par départ. Poser une seconde étape ferait un
        déroulé à deux qualifications, ce qui n'est pas le cas qu'on veut couvrir ici.
        """
        self.departs.ajouter(
            dataclasses.replace(
                Depart.creer(
                    tournoi_id=self.tournoi_id,
                    numero=numero,
                    tarif_centimes=800,
                    horaire=horaire,
                ),
                id=depart_id,
            )
        )
        qualif = self.phases.ajouter(self._etape_qualif.instancier(depart_id))
        assert qualif.id is not None
        if self._etape_tableau is not None:
            self.phases.ajouter(self._etape_tableau.instancier(depart_id))
        return qualif.id

    def inscrire_classe(
        self,
        valeurs: tuple[ZoneScore, ...],
        depart_id: int = 1,
        qualif_id: int | None = None,
    ) -> int:
        """Ajoute un archer inscrit avec une série (une volée validée) ; renvoie son `archer_id`.

        `depart_id` / `qualif_id` visent un **autre** créneau (cf. `ajouter_creneau`) : la série
        pend à la qualification **de ce créneau**, sans quoi le classement du second départ serait
        vide et le décor ne prouverait rien.
        """
        archer = self.archers.ajouter(
            Archer(nom="N", prenom="P", tournoi_id=self.tournoi_id, categorie_id=self.categorie_id)
        )
        assert archer.id is not None
        inscription = self.inscriptions.ajouter(
            Inscription(archer_id=archer.id, depart_id=depart_id)
        )
        assert inscription.id is not None
        self.series.enregistrer(
            Serie(
                tournoi_id=self.tournoi_id,
                archer_id=archer.id,
                volees=(Volee(numero=1, valeurs=valeurs, validee_par="Scoreur"),),
                phase_id=qualif_id if qualif_id is not None else self.qualif_id,
            )
        )
        return archer.id

    def classement_reel(self) -> ServiceClassement:
        """Le même calcul de classement, mais sur les repositories **réels** (oracle du rejeu)."""
        return ServiceClassement(
            self.tournois,
            self.archers,
            self.series,
            self.categories,
            self.phases,
            InMemoryForfaitRepository(),
            self.departs,
            self.inscriptions,
        )

    def service(self) -> ServiceSimulation:
        return ServiceSimulation(
            self.tournois,
            self.archers,
            self.categories,
            self.blasons,
            self.gabarits,
            self.inscriptions,
            self.departs,
            self.deroules,
            self.phases,
            self.series,
            # L'**usine de production** (pas une copie) : le harnais éprouvé ici est celui déployé
            # (revue E15US002 — évite la dérive silencieuse composition ↔ test).
            fabriquer_harnais_simulation,
        )

    def statut(self, statut: StatutTournoi) -> None:
        """Force le statut du tournoi réel (pour éprouver le garde-fou)."""
        base = self.tournois.par_id(self.tournoi_id)
        assert base is not None
        self.tournois.enregistrer(dataclasses.replace(base, statut=statut))


def _creneau(resultat: ResultatSimulation) -> CreneauSimule:
    """Le **seul** créneau du résultat — les décors d'ici montent un tournoi mono-départ.

    ⚠️ **Le dépliage `(x,) = ...` est l'assertion** : il lève si la simulation en rend deux, ce qui
    voudrait dire que le décor a changé sans que ces tests le sachent. Le cas multi-créneaux est
    couvert plus bas, par `test_la_simulation_rejoue_chaque_creneau` — écrit **après** que la revue
    eut constaté que ce renvoi désignait un test qui n'existait pas.
    """
    (creneau,) = resultat.creneaux
    return creneau


def test_tournoi_inconnu_leve_tournoi_introuvable() -> None:
    reel = _Reel()
    with pytest.raises(TournoiIntrouvable):
        reel.service().simuler(999)


def test_tournoi_sans_creneau_leve_une_erreur_metier_et_non_un_500() -> None:
    """Un tournoi `brouillon` **sans aucun départ** est un état ordinaire de l'atelier.

    On crée le tournoi, *puis* ses créneaux : entre les deux, la simulation est parfaitement
    légitime et doit répondre par une erreur métier lisible. Relevé en revue E01US025 : l'accès
    indexé `par_tournoi(tournoi_id)[0]` levait un `IndexError` — donc un **500** sans message
    exploitable — là où `ServicePalmares` lève déjà `TournoiSansDepart` sur exactement le même
    état. Deux routes ne doivent pas se comporter différemment sur le même tournoi.
    """
    reel = _Reel()
    reel.departs.supprimer(1)

    with pytest.raises(TournoiSansDepart):
        reel.service().simuler(reel.tournoi_id)


@pytest.mark.parametrize("statut", [StatutTournoi.BROUILLON, StatutTournoi.PRET])
def test_tournoi_avant_demarrage_est_simulable(statut: StatutTournoi) -> None:
    """CA garde-fou : `brouillon` et `prêt` se simulent sans lever."""
    reel = _Reel()
    reel.inscrire_classe((ZoneScore.DIX, ZoneScore.DIX))
    reel.statut(statut)
    resultat = reel.service().simuler(reel.tournoi_id)
    assert resultat.tournoi_id == reel.tournoi_id


@pytest.mark.parametrize(
    "statut",
    [
        StatutTournoi.EN_COURS,
        StatutTournoi.EN_PAUSE,
        StatutTournoi.TERMINE,
        StatutTournoi.ARCHIVE,
        StatutTournoi.ANNULE,
    ],
)
def test_tournoi_demarre_ou_fige_est_refuse(statut: StatutTournoi) -> None:
    """CA garde-fou : dès `en_cours` et au-delà, la simulation est refusée (409)."""
    reel = _Reel()
    reel.statut(statut)
    with pytest.raises(SimulationTournoiDemarre):
        reel.service().simuler(reel.tournoi_id)


def test_rejeu_ephemere_reproduit_le_classement_reel() -> None:
    """CA rejeu éphémère : le classement simulé est **identique** au classement réel (hydratation
    sans perte)."""
    reel = _Reel()
    reel.inscrire_classe((ZoneScore.HUIT, ZoneScore.HUIT))  # 16
    reel.inscrire_classe((ZoneScore.DIX, ZoneScore.DIX))  # 20 → 1er
    reel.inscrire_classe((ZoneScore.NEUF, ZoneScore.NEUF))  # 18

    attendu = reel.classement_reel().pour_depart(reel.tournoi_id)
    resultat = reel.service().simuler(reel.tournoi_id)

    assert _creneau(resultat).classement == attendu
    assert [ligne.rang_scratch for ligne in _creneau(resultat).classement.lignes] == [1, 2, 3]


def test_simulation_ne_pollue_pas_les_repositories_reels() -> None:
    """CA non-pollution (mécanisme) : les repositories réels sont **inchangés** après simulation.

    La simulation n'écrit que dans le harnais jetable ; les magasins côté lecture ne gagnent aucune
    entité et gardent leur contenu à l'identique.
    """
    reel = _Reel()
    for valeurs in ((ZoneScore.DIX, ZoneScore.DIX), (ZoneScore.NEUF, ZoneScore.NEUF)):
        reel.inscrire_classe(valeurs)

    archers_avant = reel.archers.par_tournoi(reel.tournoi_id)
    series_avant = reel.series.par_tournoi(reel.tournoi_id)

    reel.service().simuler(reel.tournoi_id)

    assert reel.archers.par_tournoi(reel.tournoi_id) == archers_avant
    assert reel.series.par_tournoi(reel.tournoi_id) == series_avant


def test_chemin_duels_est_exerce_et_renvoie_le_tableau() -> None:
    """CA « qualif → duels → classement » : une phase de tableau produit un `EtatTableau` simulé.

    Quatre archers classés → un tableau à quatre → placement + reconstruction de l'arbre, le tout
    en mémoire (rien de persisté).
    """
    reel = _Reel(avec_tableau=True)
    for valeurs in (
        (ZoneScore.DIX, ZoneScore.DIX),  # rang 1
        (ZoneScore.NEUF, ZoneScore.NEUF),  # rang 2
        (ZoneScore.HUIT, ZoneScore.HUIT),  # rang 3
        (ZoneScore.SEPT, ZoneScore.SEPT),  # rang 4
    ):
        reel.inscrire_classe(valeurs)

    resultat = reel.service().simuler(reel.tournoi_id)

    assert len(_creneau(resultat).tableaux) == 1
    tableau = _creneau(resultat).tableaux[0]
    assert tableau.effectif == 4
    assert tableau.taille == 4
    # Rien n'a été persisté côté réel : aucun plan de duel matérialisé, aucune série ajoutée.
    assert len(reel.archers.par_tournoi(reel.tournoi_id)) == 4


def test_phase_tableau_non_puissance_de_deux() -> None:
    """Effectif non-puissance-de-2 : le tableau se dimensionne à la puissance supérieure (byes).

    Trois duellistes classés → tableau de taille 4 (un bye), effectif 3. Vérifie qu'on ne suppose
    jamais `effectif == taille` (borne que la fixture à 4 masquait).
    """
    reel = _Reel(avec_tableau=True)
    for valeurs in (
        (ZoneScore.DIX, ZoneScore.DIX),
        (ZoneScore.NEUF, ZoneScore.NEUF),
        (ZoneScore.HUIT, ZoneScore.HUIT),
    ):
        reel.inscrire_classe(valeurs)

    resultat = reel.service().simuler(reel.tournoi_id)

    assert len(_creneau(resultat).tableaux) == 1
    assert _creneau(resultat).tableaux[0].effectif == 3
    assert _creneau(resultat).tableaux[0].taille == 4


def test_phase_tableau_pas_encore_jouable_est_ignoree() -> None:
    """CA « n'importe quel tournoi créé » : une phase de tableau à < 2 classés ne fait pas échouer.

    Un seul duelliste classé → `construire_tableau` lèverait `EffectifTableauInvalide` ; `simuler`
    saute la phase (pas encore jouable) et renvoie le classement, sans tableau ni exception.
    """
    reel = _Reel(avec_tableau=True)
    reel.inscrire_classe((ZoneScore.DIX, ZoneScore.DIX))

    resultat = reel.service().simuler(reel.tournoi_id)

    assert _creneau(resultat).tableaux == ()
    assert len(_creneau(resultat).classement.lignes) == 1


def test_tournoi_brouillon_vide_se_simule_sans_erreur() -> None:
    """Borne basse : un tournoi sans archer ni série se simule et rend un classement vide."""
    reel = _Reel()  # aucun archer inscrit

    resultat = reel.service().simuler(reel.tournoi_id)

    assert _creneau(resultat).classement.lignes == ()
    assert _creneau(resultat).tableaux == ()


def test_la_simulation_rejoue_chaque_creneau() -> None:
    """CA « la simulation suit » (E06US009) : deux créneaux peuplés, deux créneaux rejoués.

    ⚠️ **Ce test n'existait pas quand la docstring de `_creneau` le disait déjà écrit.** La revue
    l'a relevé : les six autres tests de ce fichier déplient `(x,) = resultat.creneaux`, donc ils
    assèrent l'unicité — exactement le décor sous lequel l'ancien `creneaux[0]` était déjà juste.
    Un diff futur qui remettrait `phases.par_tournoi` dans `_creneau_simule` passerait au vert sur
    tout le reste du fichier.

    ⚠️ **L'assertion porte sur l'identité des archers, pas sur `len(creneaux) == 2`** : un rejeu
    qui rendrait deux fois le classement du matin a bien deux créneaux.
    """
    reel = _Reel()
    matin = [
        reel.inscrire_classe(v)
        for v in (
            (ZoneScore.DIX, ZoneScore.DIX, ZoneScore.DIX),
            (ZoneScore.NEUF, ZoneScore.NEUF, ZoneScore.NEUF),
        )
    ]
    qualif_2 = reel.ajouter_creneau(numero=2, horaire="14:00", depart_id=2)
    apres_midi = [
        reel.inscrire_classe(v, depart_id=2, qualif_id=qualif_2)
        for v in (
            (ZoneScore.DIX, ZoneScore.DIX, ZoneScore.NEUF),
            (ZoneScore.NEUF, ZoneScore.NEUF, ZoneScore.HUIT),
        )
    ]

    resultat = reel.service().simuler(reel.tournoi_id)

    assert [creneau.depart_id for creneau in resultat.creneaux] == [1, 2]
    assert [creneau.libelle for creneau in resultat.creneaux] == [
        "Départ n°1 — 09:00",
        "Départ n°2 — 14:00",
    ]
    vus = [
        {ligne.archer_id for ligne in creneau.classement.lignes} for creneau in resultat.creneaux
    ]
    assert vus == [set(matin), set(apres_midi)]


def test_chaque_creneau_simule_ne_porte_que_ses_propres_tableaux() -> None:
    """Le second piège, nommé par le ⚠️ de `_creneau_simule` : la portée des ARBRES, pas du rang.

    Passer de `phases.par_tournoi` à `phases.par_depart` corrige le classement ; oublier de le faire
    pour les tableaux met **tous** les arbres du tournoi sous **chaque** classement. C'est le même
    défaut de portée, retourné, et il ne se voit qu'à deux créneaux portant chacun un tableau.
    """
    reel = _Reel(avec_tableau=True)
    for valeurs in (
        (ZoneScore.DIX, ZoneScore.DIX, ZoneScore.DIX),
        (ZoneScore.NEUF, ZoneScore.NEUF, ZoneScore.NEUF),
        (ZoneScore.NEUF, ZoneScore.NEUF, ZoneScore.HUIT),
    ):
        reel.inscrire_classe(valeurs)
    qualif_2 = reel.ajouter_creneau(numero=2, horaire="14:00", depart_id=2)
    for valeurs in (
        (ZoneScore.DIX, ZoneScore.DIX, ZoneScore.NEUF),
        (ZoneScore.NEUF, ZoneScore.HUIT, ZoneScore.HUIT),
        (ZoneScore.HUIT, ZoneScore.HUIT, ZoneScore.HUIT),
    ):
        reel.inscrire_classe(valeurs, depart_id=2, qualif_id=qualif_2)

    resultat = reel.service().simuler(reel.tournoi_id)

    # ⚠️ **`== 1`, et non `<= 1` ni `isdisjoint` seuls** : `set().isdisjoint(set())` est vrai et
    # `len(set()) <= 1` aussi. `_creneau_simule` **avale en silence** `EffectifTableauInvalide` et
    # `PrelevementEnAttente` (il rend `()`), donc « plus aucun arbre » est le mode de panne le plus
    # probable de ce code — et il passait au vert. Mesuré en revue (axe D), sabotage à l'appui.
    phases_vues = [{etat.phase_id for etat in creneau.tableaux} for creneau in resultat.creneaux]
    assert [len(vues) for vues in phases_vues] == [1, 1], "un arbre par créneau, ni zéro ni deux"
    assert phases_vues[0].isdisjoint(phases_vues[1]), "un arbre ne pend qu'à son créneau"
