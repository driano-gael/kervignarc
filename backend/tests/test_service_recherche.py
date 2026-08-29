"""Tests du service de **recherche transverse** (E16US010).

Tests **après** implémentation (règle 9) : la règle métier — ce qui correspond, dans quel ordre —
vit au domaine et se teste depuis le CA (`test_domain_recherche.py`). Ce qui se vérifie ici est de
l'**agrégation** : le service lit-il les bons dépôts, décore-t-il de quoi distinguer deux fiches,
et le scope « pilotage » restreint-il bien le **même** chemin ?
"""

from __future__ import annotations

import datetime

from application.recherche import ServiceRecherche
from domain.archer import Archer
from domain.club import Club
from domain.recherche import EntiteRecherchable
from domain.tournoi import Tournoi
from tests.conftest import FauxArcherRepository, FauxClubRepository, FauxTournoiRepository

_CATEGORIE = 1


def _attelage() -> tuple[ServiceRecherche, dict[str, int]]:
    """Deux tournois, deux clubs, trois archers dont deux homonymes d'éditions différentes."""
    tournois, archers, clubs = (
        FauxTournoiRepository(),
        FauxArcherRepository(),
        FauxClubRepository(),
    )
    salle = tournois.ajouter(
        Tournoi(nom="Salle 18m", date=datetime.date(2026, 3, 14), lieu="Kervignarc")
    )
    ancien = tournois.ajouter(Tournoi(nom="Salle 18m", date=datetime.date(2025, 3, 15)))
    kerv = clubs.ajouter(Club.creer("Arc Club de Kervignarc"))
    autre = clubs.ajouter(Club.creer("Compagnie de Saint-Mérien"))
    assert salle.id and ancien.id and kerv.id and autre.id

    archers.ajouter(
        Archer(
            nom="Lévêque",
            prenom="Jean",
            tournoi_id=salle.id,
            categorie_id=_CATEGORIE,
            club_id=kerv.id,
        )
    )
    archers.ajouter(
        Archer(
            nom="Lévêque",
            prenom="Jean",
            tournoi_id=ancien.id,
            categorie_id=_CATEGORIE,
            club_id=autre.id,
        )
    )
    archers.ajouter(
        Archer(nom="Bordure", prenom="Luc", tournoi_id=salle.id, categorie_id=_CATEGORIE)
    )
    return ServiceRecherche(tournois, archers, clubs), {"salle": salle.id, "ancien": ancien.id}


def test_un_archer_se_trouve_sans_accents_a_travers_tous_les_tournois() -> None:
    """Le CA « hors pilotage » : l'archer n'est pas cherché dans un tournoi, mais dans le dépôt."""
    service, _ = _attelage()

    recherche = service.chercher(EntiteRecherchable.ARCHER, "leveque")

    assert recherche.total == 2
    assert {r.libelle for r in recherche.resultats} == {"Lévêque Jean"}


def test_deux_homonymes_se_distinguent_par_leur_club_et_leur_tournoi() -> None:
    """Sans cette décoration, la complétion propose deux lignes identiques : rien à choisir."""
    service, _ = _attelage()

    precisions = {
        r.precision for r in service.chercher(EntiteRecherchable.ARCHER, "leveque").resultats
    }

    assert precisions == {
        "Arc Club de Kervignarc · Salle 18m",
        "Compagnie de Saint-Mérien · Salle 18m",
    }


def test_en_pilotage_la_recherche_est_scopee_au_tournoi() -> None:
    """Le second CA — **même** chemin, restreint : un seul des deux homonymes remonte."""
    service, ids = _attelage()

    recherche = service.chercher(EntiteRecherchable.ARCHER, "leveque", tournoi_id=ids["salle"])

    assert recherche.total == 1


def test_en_pilotage_la_precision_cesse_de_repeter_le_tournoi() -> None:
    """On y est déjà : le répéter à chaque ligne noie le club, seule chose qui distingue."""
    service, ids = _attelage()

    resultat = service.chercher(
        EntiteRecherchable.ARCHER, "leveque", tournoi_id=ids["salle"]
    ).resultats[0]

    assert resultat.precision == "Arc Club de Kervignarc"


def test_un_archer_se_trouve_par_le_nom_de_son_club() -> None:
    """« Qui de Saint-Mérien ? » est une question que l'organisateur pose vraiment."""
    service, _ = _attelage()

    recherche = service.chercher(EntiteRecherchable.ARCHER, "saint-merien")

    assert recherche.total == 1


def test_un_archer_sans_club_connu_reste_trouvable() -> None:
    """« Club inconnu » est un cas réel (ADR-0014), pas une anomalie à filtrer."""
    service, _ = _attelage()

    recherche = service.chercher(EntiteRecherchable.ARCHER, "bordure")

    assert recherche.total == 1
    assert recherche.resultats[0].precision == "Salle 18m"


def test_un_tournoi_se_trouve_par_son_nom_ou_son_lieu_et_sa_date_le_situe() -> None:
    """Deux éditions portent le même nom : c'est la date qui les sépare."""
    service, _ = _attelage()

    par_nom = service.chercher(EntiteRecherchable.TOURNOI, "salle")
    par_lieu = service.chercher(EntiteRecherchable.TOURNOI, "kervignarc")

    assert par_nom.total == 2
    assert {r.precision for r in par_nom.resultats} == {"14/03/2026 · Kervignarc", "15/03/2025"}
    assert par_lieu.total == 1


def test_un_club_se_trouve_par_son_nom() -> None:
    service, _ = _attelage()

    assert service.chercher(EntiteRecherchable.CLUB, "compagnie").total == 1


def test_un_fragment_vide_ne_propose_rien_sur_aucune_entite() -> None:
    """La déroulante ne doit pas déverser le référentiel entier dès qu'on la choisit."""
    service, _ = _attelage()

    for entite in EntiteRecherchable:
        assert service.chercher(entite, "  ").total == 0, entite
