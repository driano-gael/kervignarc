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
from domain.categorie import Categorie
from domain.club import Club
from domain.recherche import EntiteRecherchable
from domain.tournoi import Tournoi
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxClubRepository,
    FauxTournoiRepository,
)


def _attelage() -> tuple[ServiceRecherche, dict[str, int]]:
    """Trois tournois — dont deux de la MÊME année —, deux clubs, cinq archers dont quatre homonymes
    (deux éditions distinctes, une même année, et **le père et le fils dans le même tournoi**)."""
    tournois, archers, clubs, categories = (
        FauxTournoiRepository(),
        FauxArcherRepository(),
        FauxClubRepository(),
        FauxCategorieRepository(),
    )
    salle = tournois.ajouter(
        Tournoi(nom="Salle 18m", date=datetime.date(2026, 3, 14), lieu="Kervignarc")
    )
    ancien = tournois.ajouter(Tournoi(nom="Salle 18m", date=datetime.date(2025, 3, 15)))
    # ⚠️ **Même nom, MÊME ANNÉE que `salle`** : la saison salle court de novembre à mars, deux
    # éditions d'une même année civile sont ordinaires. C'est le cas que la 1ʳᵉ correction (l'année
    # seule) ne fermait pas et que la fixture d'alors ne pouvait pas exercer.
    jumelle = tournois.ajouter(Tournoi(nom="Salle 18m", date=datetime.date(2026, 11, 21)))
    kerv = clubs.ajouter(Club.creer("Arc Club de Kervignarc"))
    autre = clubs.ajouter(Club.creer("Compagnie de Saint-Mérien"))
    assert salle.id and ancien.id and jumelle.id and kerv.id and autre.id
    # Deux catégories dans le tournoi courant : c'est ce qui sépare deux fiches de même nom, même
    # prénom et même club — le père et le fils que `cle_identite` déclare « vraisemblablement le
    # même » et que la détection de doublons de cette US rapproche.
    senior = categories.ajouter(Categorie(tournoi_id=salle.id, libelle="Senior 1 H"))
    cadet = categories.ajouter(Categorie(tournoi_id=salle.id, libelle="Cadet H"))
    categories.ajouter(Categorie(tournoi_id=ancien.id, libelle="Senior 1 H"))
    categories.ajouter(Categorie(tournoi_id=jumelle.id, libelle="Senior 1 H"))
    assert senior.id and cadet.id

    archers.ajouter(
        Archer(
            nom="Lévêque",
            prenom="Jean",
            tournoi_id=salle.id,
            categorie_id=senior.id,
            club_id=kerv.id,
        )
    )
    archers.ajouter(
        Archer(
            nom="Lévêque",
            prenom="Jean",
            tournoi_id=ancien.id,
            categorie_id=senior.id,
            # ⚠️ **Même club que son homonyme, délibérément** : la 1ʳᵉ fixture leur donnait deux
            # clubs différents, ce qui rendait le test vert sans jamais exercer la
            # désambiguïsation d'ÉDITION que son nom annonce (relevé par les axes C1 et D).
            club_id=kerv.id,
        )
    )
    archers.ajouter(
        Archer(nom="Bordure", prenom="Luc", tournoi_id=salle.id, categorie_id=senior.id)
    )
    archers.ajouter(
        Archer(
            nom="Lévêque",
            prenom="Jean",
            tournoi_id=jumelle.id,
            categorie_id=senior.id,
            club_id=kerv.id,
        )
    )
    # ⚠️ **Le père et le fils** — même nom, même prénom, même club, MÊME TOURNOI. Aucune fixture ne
    # produisait ce cas, et c'est celui que la détection de doublons de cette US fabrique.
    archers.ajouter(
        Archer(
            nom="Lévêque",
            prenom="Jean",
            tournoi_id=salle.id,
            categorie_id=cadet.id,
            club_id=kerv.id,
        )
    )
    return ServiceRecherche(tournois, archers, clubs, categories), {
        "salle": salle.id,
        "ancien": ancien.id,
        "jumelle": jumelle.id,
    }


def test_un_archer_se_trouve_sans_accents_a_travers_tous_les_tournois() -> None:
    """Le CA « hors pilotage » : l'archer n'est pas cherché dans un tournoi, mais dans le dépôt."""
    service, _ = _attelage()

    recherche = service.chercher(EntiteRecherchable.ARCHER, "leveque")

    assert recherche.total == 4
    assert {r.libelle for r in recherche.resultats} == {"Lévêque Jean"}


def test_des_homonymes_du_meme_club_se_distinguent_par_leur_edition() -> None:
    """Sans cette décoration, la complétion propose deux lignes identiques : rien à choisir."""
    service, _ = _attelage()

    precisions = {
        r.precision for r in service.chercher(EntiteRecherchable.ARCHER, "leveque").resultats
    }

    # ⚠️ **Trois fiches, trois précisions distinctes** — dont deux de la MÊME année civile, que
    # l'année seule ne séparait pas. C'est la date complète qui les situe, comme pour les tournois.
    assert precisions == {
        "Arc Club de Kervignarc · Senior 1 H · Salle 18m — 14/03/2026 · Kervignarc",
        "Arc Club de Kervignarc · Cadet H · Salle 18m — 14/03/2026 · Kervignarc",
        "Arc Club de Kervignarc · Senior 1 H · Salle 18m — 15/03/2025",
        "Arc Club de Kervignarc · Senior 1 H · Salle 18m — 21/11/2026",
    }
    # Quatre fiches, quatre précisions : deux éditions du même nom, deux d'une même année, et
    # **deux du même tournoi et du même club** — le père et le fils.
    assert len(precisions) == 4


def test_en_pilotage_la_recherche_est_scopee_au_tournoi() -> None:
    """Le second CA — **même** chemin, restreint : un seul des deux homonymes remonte."""
    service, ids = _attelage()

    recherche = service.chercher(EntiteRecherchable.ARCHER, "leveque", tournoi_id=ids["salle"])

    assert recherche.total == 2


def test_en_pilotage_la_precision_cesse_de_repeter_le_tournoi() -> None:
    """On y est déjà : le répéter à chaque ligne noierait ce qui distingue vraiment les fiches.

    ⚠️ **La catégorie, elle, reste** — et c'est le correctif de la 3ᵉ passe : en pilotage le club
    est par construction le même pour un père et son fils, donc la catégorie est le **seul**
    discriminant. Sans elle, les deux lignes étaient identiques.
    """
    service, ids = _attelage()

    precisions = {
        r.precision
        for r in service.chercher(
            EntiteRecherchable.ARCHER, "leveque", tournoi_id=ids["salle"]
        ).resultats
    }

    assert precisions == {
        "Arc Club de Kervignarc · Senior 1 H",
        "Arc Club de Kervignarc · Cadet H",
    }
    assert all("Salle 18m" not in (p or "") for p in precisions)


def test_le_pere_et_le_fils_du_meme_tournoi_restent_distinguables() -> None:
    """Le cas que la détection de doublons de CETTE US fabrique, et qu'aucune fixture n'avait.

    `domain.archer.cle_identite` le dit : « un père et son fils partagent nom, prénom et club ».
    Hors pilotage comme en pilotage, deux lignes identiques laissaient l'organisateur ouvrir la
    fiche du fils pour le père — et lire son couloir de tir.
    """
    service, ids = _attelage()

    partout = service.chercher(EntiteRecherchable.ARCHER, "leveque").resultats
    dans_le_tournoi = service.chercher(
        EntiteRecherchable.ARCHER, "leveque", tournoi_id=ids["salle"]
    ).resultats

    du_tournoi = [r for r in partout if r.tournoi_id == ids["salle"]]
    assert len(du_tournoi) == 2
    assert len({r.precision for r in du_tournoi}) == 2
    assert len({r.precision for r in dans_le_tournoi}) == 2


def test_un_archer_se_trouve_par_le_nom_de_son_club() -> None:
    """« Qui de l'Arc Club ? » est une question que l'organisateur pose vraiment."""
    service, _ = _attelage()

    recherche = service.chercher(EntiteRecherchable.ARCHER, "arc club")

    assert recherche.total == 4


def test_un_archer_sans_club_connu_reste_trouvable() -> None:
    """« Club inconnu » est un cas réel (ADR-0014), pas une anomalie à filtrer."""
    service, _ = _attelage()

    recherche = service.chercher(EntiteRecherchable.ARCHER, "bordure")

    assert recherche.total == 1
    assert recherche.resultats[0].precision == "Senior 1 H · Salle 18m — 14/03/2026 · Kervignarc"


def test_chaque_resultat_dit_ou_ouvrir_sa_fiche() -> None:
    """Le CA promet d'**ouvrir** la fiche : un archer d'une autre édition est sinon inatteignable.

    ⚠️ Le nom du tournoi (`precision`) se lit mais ne s'adresse pas — d'où l'identifiant.
    """
    service, ids = _attelage()

    archers = service.chercher(EntiteRecherchable.ARCHER, "leveque").resultats
    tournois = service.chercher(EntiteRecherchable.TOURNOI, "salle").resultats
    clubs = service.chercher(EntiteRecherchable.CLUB, "compagnie").resultats

    assert {a.tournoi_id for a in archers} == {ids["salle"], ids["ancien"], ids["jumelle"]}
    assert all(t.tournoi_id == t.id for t in tournois)
    # Un club est un référentiel **global** : aucune édition ne le porte.
    assert clubs[0].tournoi_id is None


def test_un_tournoi_se_trouve_par_son_nom_ou_son_lieu_et_sa_date_le_situe() -> None:
    """Deux éditions portent le même nom : c'est la date qui les sépare."""
    service, _ = _attelage()

    par_nom = service.chercher(EntiteRecherchable.TOURNOI, "salle")
    par_lieu = service.chercher(EntiteRecherchable.TOURNOI, "kervignarc")

    assert par_nom.total == 3
    assert {r.precision for r in par_nom.resultats} == {
        "14/03/2026 · Kervignarc",
        "15/03/2025",
        "21/11/2026",
    }
    assert par_lieu.total == 1


def test_un_club_se_trouve_par_son_nom() -> None:
    service, _ = _attelage()

    assert service.chercher(EntiteRecherchable.CLUB, "compagnie").total == 1


def test_le_scope_tournoi_est_ignore_hors_des_archers() -> None:
    """Clubs et tournois sont des référentiels **globaux** : un scope les viderait sans le dire.

    La docstring du service l'affirmait, rien ne le tenait (relevé par l'axe B).
    """
    service, ids = _attelage()
    scope = ids["salle"]

    assert service.chercher(EntiteRecherchable.CLUB, "compagnie", tournoi_id=scope).total == 1
    assert service.chercher(EntiteRecherchable.TOURNOI, "salle", tournoi_id=scope).total == 3


def test_un_fragment_vide_ne_propose_rien_sur_aucune_entite() -> None:
    """La déroulante ne doit pas déverser le référentiel entier dès qu'on la choisit."""
    service, _ = _attelage()

    for entite in EntiteRecherchable:
        assert service.chercher(entite, "  ").total == 0, entite
