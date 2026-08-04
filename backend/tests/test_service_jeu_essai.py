"""Tests du service applicatif Jeu d'essai (E15US001) — écrits **depuis le CA** (règle 9).

Le service **compose** les vrais services applicatifs (Tournois, Catégories, Départs, Archers,
Inscriptions, Clubs) au-dessus de faux repositories en mémoire : c'est le même attelage qu'en
production, sans base ni serveur (le point de l'US, E15US002, est justement de rejouer les services
sur des adaptateurs en mémoire). On y prouve ce que le CA promet :

- **générateur** : un bouton peuple **N archers plausibles** (noms, clubs, catégories cohérentes),
  **déterministe** pour une graine donnée ;
- **scénarios** : le catalogue instancie un tournoi + ses inscrits, **prêt à lancer**.

`FauxDepartRepository`, `FauxInscriptionRepository`, `FauxCategorieRepository`,
`FauxArcherRepository`, `FauxClubRepository` viennent de `conftest` (faux partagés) ;
`FauxTournoiRepository`, `FauxScoreRepository`, `FauxSerieRepository` sont importés de
`test_service_archers` et `FauxBlasonRepository` de `test_service_categories` — on ne recopie pas un
faux qui existe déjà (les tests s'importent entre eux dans ce dépôt, cf. `test_service_archers`).
"""

from __future__ import annotations

import datetime
from typing import NamedTuple

import pytest

from application.archers import ServiceArchers
from application.categories import ServiceCategories
from application.clubs import ServiceClubs
from application.departs import ServiceDeparts
from application.erreurs import PeuplementTournoiDemarre, ScenarioInconnu
from application.inscriptions import ServiceInscriptions
from application.jeu_essai import CATALOGUE, ServiceJeuEssai
from application.referentiel_ffta import ARC_CLASSIQUE, ARC_NU, ARC_POULIES
from application.suivi_deroule import CompteurEngagesRepository
from application.tournois import ServiceTournois
from domain.categorie import Categorie
from domain.cycle_depart import AvancementDepart
from domain.depart import Depart, DepartId
from domain.phase import Phase
from domain.tournoi import StatutTournoi, TournoiId
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxClubRepository,
    FauxDepartRepository,
    FauxInscriptionRepository,
    HorlogeFigee,
)
from tests.test_service_archers import (
    FauxScoreRepository,
    FauxSerieRepository,
    FauxTournoiRepository,
)
from tests.test_service_categories import FauxBlasonRepository

_DATE = datetime.date(2026, 3, 14)


def _horloge() -> HorlogeFigee:
    """Horloge figée (le jeu d'essai ne désinscrit ni ne supprime de payées : la date n'est jamais
    lue en pratique — mais les services l'exigent au constructeur, E08US005)."""
    return HorlogeFigee(datetime.datetime(2026, 7, 29, 9, 0, tzinfo=datetime.UTC))


class _AvancementInerte:
    """Double du port `LecteurAvancementDepart` : jamais sollicité (le jeu d'essai ne fait que
    **créer** des départs, or `ServiceDeparts.creer` ne lit pas l'avancement)."""

    def avancement_depart(self, tournoi_id: TournoiId, depart_id: DepartId) -> AvancementDepart:
        raise NotImplementedError("Le jeu d'essai ne crée que des départs (pas de lecture d'état).")


class _PhasesVides:
    """Double du port `PhaseRepository` pour la garde d'effectif d'E05US021.

    Le jeu d'essai **peuple** un tournoi (archers, départs, inscriptions) mais ne lui compose aucun
    déroulé : sans phase, il n'y a aucun prélèvement à honorer, donc rien à exiger au démarrage.
    """

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Phase]:
        return []


class Attelage(NamedTuple):
    """Le service sous test + les repos/services dont les assertions ont besoin."""

    jeu: ServiceJeuEssai
    tournois: ServiceTournois
    categories: ServiceCategories
    archers: FauxArcherRepository
    inscriptions: FauxInscriptionRepository
    departs: FauxDepartRepository


def _atteler() -> Attelage:
    """Câble le service jeu d'essai comme la composition root, sur des faux repositories."""
    tournoi_repo = FauxTournoiRepository()
    categorie_repo = FauxCategorieRepository()
    blason_repo = FauxBlasonRepository()
    club_repo = FauxClubRepository()
    archer_repo = FauxArcherRepository()
    depart_repo = FauxDepartRepository()
    inscription_repo = FauxInscriptionRepository()
    score_repo = FauxScoreRepository(archer_repo)
    serie_repo = FauxSerieRepository(archer_repo)

    # E05US021 : `ServiceTournois` lit désormais phases et engagés (garde d'effectif au démarrage).
    # Le jeu d'essai ne compose aucun déroulé — la garde reste donc muette, et un dépôt de phases
    # vide suffit à câbler comme la composition root.
    service_tournois = ServiceTournois(
        tournoi_repo,
        depart_repo,
        _PhasesVides(),
        CompteurEngagesRepository(depart_repo, inscription_repo),
    )
    service_categories = ServiceCategories(tournoi_repo, categorie_repo, blason_repo)
    service_departs = ServiceDeparts(
        depart_repo, tournoi_repo, inscription_repo, _AvancementInerte(), archer_repo, _horloge()
    )
    service_archers = ServiceArchers(
        tournoi_repo,
        archer_repo,
        score_repo,
        club_repo,
        categorie_repo,
        inscription_repo,
        serie_repo,
    )
    service_inscriptions = ServiceInscriptions(
        inscription_repo, archer_repo, depart_repo, _horloge()
    )
    service_clubs = ServiceClubs(club_repo, archer_repo)

    jeu = ServiceJeuEssai(
        service_tournois,
        service_categories,
        service_departs,
        service_archers,
        service_inscriptions,
        service_clubs,
    )
    return Attelage(
        jeu,
        service_tournois,
        service_categories,
        archer_repo,
        inscription_repo,
        depart_repo,
    )


def _tournoi_brouillon(a: Attelage, nom: str = "Test") -> TournoiId:
    tournoi = a.tournois.creer(nom, _DATE)
    assert tournoi.id is not None
    return tournoi.id


def _armes_des_archers(a: Attelage, tournoi_id: TournoiId) -> set[str | None]:
    """Ensemble des divisions (armes) réellement portées par les archers générés d'un tournoi."""
    par_id: dict[int, Categorie] = {
        c.id: c for c in a.categories.lister(tournoi_id) if c.id is not None
    }
    return {par_id[ar.categorie_id].arme for ar in a.archers.par_tournoi(tournoi_id)}


# --- Générateur d'inscrits (CA « peupler N archers plausibles ») ---------------------------------


def test_peupler_cree_le_nombre_demande() -> None:
    a = _atteler()
    tid = _tournoi_brouillon(a)

    a.jeu.peupler(tid, nombre=16, graine=1)

    assert len(a.archers.par_tournoi(tid)) == 16


def test_peupler_precharge_les_categories_si_absentes() -> None:
    """Sur un tournoi sans catégorie, peupler pré-charge le jeu FFTA et rattache chaque archer à
    une catégorie **de ce tournoi** (CA « catégories FFTA cohérentes »)."""
    a = _atteler()
    tid = _tournoi_brouillon(a)
    assert a.categories.lister(tid) == []

    a.jeu.peupler(tid, nombre=10, graine=1)

    categories_ids = {c.id for c in a.categories.lister(tid)}
    assert categories_ids  # le jeu FFTA a bien été pré-chargé
    for archer in a.archers.par_tournoi(tid):
        assert archer.categorie_id in categories_ids


def test_peupler_utilise_les_categories_existantes_sans_precharger() -> None:
    """Si le tournoi a déjà des catégories, peupler puise dedans **sans** ajouter le jeu FFTA."""
    a = _atteler()
    tid = _tournoi_brouillon(a)
    categorie = a.categories.creer(tid, "Ma catégorie maison", arme=ARC_CLASSIQUE)

    a.jeu.peupler(tid, nombre=8, graine=1)

    categories = a.categories.lister(tid)
    assert len(categories) == 1  # aucune catégorie FFTA ajoutée
    for archer in a.archers.par_tournoi(tid):
        assert archer.categorie_id == categorie.id


def test_peupler_noms_plausibles_et_clubs() -> None:
    """Chaque archer a nom + prénom non vides ; la plupart portent un club (référentiel créé)."""
    a = _atteler()
    tid = _tournoi_brouillon(a)

    a.jeu.peupler(tid, nombre=30, graine=1)

    archers = a.archers.par_tournoi(tid)
    assert all(ar.nom.strip() and ar.prenom.strip() for ar in archers)
    avec_club = [ar for ar in archers if ar.club_id is not None]
    assert len(avec_club) >= 20  # la majorité rattachée à un club


def test_peupler_est_deterministe_pour_une_graine_donnee() -> None:
    """Même graine → mêmes archers (noms + catégories) ; graine ≠ → jeu différent (règle 9)."""
    a1, a2, a3 = _atteler(), _atteler(), _atteler()
    t1, t2, t3 = _tournoi_brouillon(a1), _tournoi_brouillon(a2), _tournoi_brouillon(a3)

    a1.jeu.peupler(t1, nombre=12, graine=42)
    a2.jeu.peupler(t2, nombre=12, graine=42)
    a3.jeu.peupler(t3, nombre=12, graine=7)

    def signature(a: Attelage, tid: TournoiId) -> list[tuple[str, str, int]]:
        return [(ar.nom, ar.prenom, ar.categorie_id) for ar in a.archers.par_tournoi(tid)]

    assert signature(a1, t1) == signature(a2, t2)
    assert signature(a1, t1) != signature(a3, t3)


def test_peupler_deterministe_independant_de_l_ordre_des_categories() -> None:
    """Le déterminisme ne doit pas dépendre de l'ordre où le repository renvoie les catégories.

    C'est ce que garantit le tri par libellé dans `_categories_cibles` : sans lui, deux bases où
    les mêmes catégories ont été insérées dans un ordre différent produiraient un tirage différent.
    On insère donc les **mêmes** catégories dans un **ordre opposé** dans deux attelages, on peuple
    à graine égale, et on compare la signature **par libellé** (l'`id`, lui, n'est pas garanti
    cross-base — cf. docstring du service). Ce test échouerait si l'on retirait le `sorted(...)`."""
    a1, a2 = _atteler(), _atteler()
    t1, t2 = _tournoi_brouillon(a1), _tournoi_brouillon(a2)
    libelles = ["Cat Alpha", "Cat Beta", "Cat Gamma"]
    for libelle in libelles:
        a1.categories.creer(t1, libelle, arme=ARC_CLASSIQUE)
    for libelle in reversed(libelles):  # ordre d'insertion **opposé**
        a2.categories.creer(t2, libelle, arme=ARC_CLASSIQUE)

    a1.jeu.peupler(t1, nombre=12, graine=9)
    a2.jeu.peupler(t2, nombre=12, graine=9)

    def signature_par_libelle(a: Attelage, tid: TournoiId) -> list[tuple[str, str, str]]:
        par_id = {c.id: c for c in a.categories.lister(tid) if c.id is not None}
        return [
            (ar.nom, ar.prenom, par_id[ar.categorie_id].libelle)
            for ar in a.archers.par_tournoi(tid)
        ]

    assert signature_par_libelle(a1, t1) == signature_par_libelle(a2, t2)


def test_peupler_refuse_un_tournoi_demarre() -> None:
    """On ne peuple pas une compétition vivante de données de test (garde-fou, esprit EPIC-15)."""
    a = _atteler()
    tid = _tournoi_brouillon(a)
    a.departs.ajouter(Depart.creer(tid, 1, 1000, "09:00", None))  # requis pour vers_pret
    a.tournois.vers_pret(tid)
    a.tournois.demarrer(tid)  # → en_cours

    with pytest.raises(PeuplementTournoiDemarre):
        a.jeu.peupler(tid, nombre=5, graine=1)


def test_peupler_autorise_un_tournoi_pret() -> None:
    """Un tournoi `prêt` (pas encore démarré) reste peuplable — la borne est « avant démarrage »."""
    a = _atteler()
    tid = _tournoi_brouillon(a)
    a.departs.ajouter(Depart.creer(tid, 1, 1000, "09:00", None))
    a.tournois.vers_pret(tid)

    a.jeu.peupler(tid, nombre=6, graine=1)

    assert len(a.archers.par_tournoi(tid)) == 6


# --- Catalogue de scénarios (CA « scénarios rejouables ») ----------------------------------------


def test_catalogue_expose_les_trois_scenarios() -> None:
    a = _atteler()
    ids = {s.id for s in a.jeu.scenarios()}
    assert ids == {"petit", "gros", "multi-format"}


def test_scenario_inconnu_est_refuse() -> None:
    a = _atteler()
    with pytest.raises(ScenarioInconnu):
        a.jeu.instancier("inexistant", _DATE)


def test_scenario_petit_cree_un_tournoi_pret_a_lancer() -> None:
    """« Petit » crée un tournoi brouillon complet : catégories, ≥ 1 départ, archers **inscrits**,
    et il peut passer `prêt` (garde `TournoiSansDepart`, E02US010) — le CA « prêt à lancer »."""
    a = _atteler()

    resultat = a.jeu.instancier("petit", _DATE, graine=1)

    assert resultat.nombre_archers == 16
    assert resultat.nombre_departs == 1
    archers = a.archers.par_tournoi(resultat.tournoi_id)
    assert len(archers) == 16
    # Chaque archer est inscrit sur au moins un départ.
    for archer in archers:
        assert archer.id is not None
        assert a.inscriptions.par_archer(archer.id), "archer non inscrit"
    # Le tournoi a un départ : il peut passer prêt (sinon `TournoiSansDepart`).
    pret = a.tournois.vers_pret(resultat.tournoi_id)
    assert pret.statut is StatutTournoi.PRET


def test_scenario_petit_concentre_sur_arc_classique_senior() -> None:
    """« Petit » concentre les inscrits sur l'arc classique sénior — assez d'archers par catégorie
    pour un tableau de duels (justification du filtre du scénario)."""
    a = _atteler()
    resultat = a.jeu.instancier("petit", _DATE, graine=1)
    assert _armes_des_archers(a, resultat.tournoi_id) == {ARC_CLASSIQUE}


def test_scenario_gros_a_plusieurs_departs_et_beaucoup_d_archers() -> None:
    a = _atteler()
    resultat = a.jeu.instancier("gros", _DATE, graine=1)
    assert resultat.nombre_archers == 120
    assert resultat.nombre_departs == 3
    assert len(a.departs.par_tournoi(resultat.tournoi_id)) == 3
    assert len(a.archers.par_tournoi(resultat.tournoi_id)) == 120


def test_scenario_multi_format_couvre_les_trois_armes() -> None:
    """« Multi-format » mêle les trois divisions — cohabitation des formats (CA multi-format).

    La couverture des 3 armes est **quasi certaine** (60 archers tirés parmi les catégories des 3
    divisions), et le test est **déterministe** (graine fixée) — donc non-flaky : à cette graine, la
    propriété tient. Ce n'est pas garanti par construction (un archer par arme n'est pas réservé) ;
    si un jour on voulait cet invariant dur, il faudrait forcer au moins un tirage par division."""
    a = _atteler()
    resultat = a.jeu.instancier("multi-format", _DATE, graine=1)
    assert _armes_des_archers(a, resultat.tournoi_id) == {ARC_CLASSIQUE, ARC_POULIES, ARC_NU}


def test_instancier_est_deterministe() -> None:
    """Deux instanciations du même scénario à graine égale produisent le même jeu d'archers."""
    a1, a2 = _atteler(), _atteler()
    r1 = a1.jeu.instancier("petit", _DATE, graine=5)
    r2 = a2.jeu.instancier("petit", _DATE, graine=5)

    def signature(a: Attelage, tid: TournoiId) -> list[tuple[str, str]]:
        return [(ar.nom, ar.prenom) for ar in a.archers.par_tournoi(tid)]

    assert signature(a1, r1.tournoi_id) == signature(a2, r2.tournoi_id)


def test_catalogue_module_est_le_meme_que_celui_du_service() -> None:
    """Garde-fou : le service expose bien le catalogue du module (pas une copie divergente)."""
    a = _atteler()
    assert tuple(a.jeu.scenarios()) == CATALOGUE
