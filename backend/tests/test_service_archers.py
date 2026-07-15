"""Tests des services applicatifs Archers et Classement (E00US011, E02US002) — factices.

Les services sont testés **en isolation** : de faux repositories en mémoire (conformes aux
ports) suffisent — ni base ni serveur. `FauxArcherRepository`, `FauxClubRepository` et
`FauxCategorieRepository` vivent dans `conftest` : ils sont partagés avec d'autres modules de
test, et un faux partagé se déclare une fois. `FauxTournoiRepository` et `FauxScoreRepository`
restent ici — ce module est leur seul consommateur.
"""

from __future__ import annotations

import datetime
from typing import NamedTuple

import pytest

from application.archers import ServiceArchers
from application.classements import ServiceClassement
from application.erreurs import (
    ArcherIntrouvable,
    CategorieHorsTournoi,
    ClubIntrouvable,
    HomonymeArcher,
    TournoiIntrouvable,
)
from domain.categorie import Categorie, CategorieId
from domain.club import Club
from domain.erreurs import (
    CibleInvalide,
    NomArcherInvalide,
    PrenomArcherInvalide,
    ScoreInvalide,
)
from domain.score import Score
from domain.tournoi import Tournoi, TournoiId
from tests.conftest import FauxArcherRepository, FauxCategorieRepository, FauxClubRepository

_DATE = datetime.date(2026, 3, 14)


class FauxTournoiRepository:
    """Repository en mémoire conforme au port `TournoiRepository`."""

    def __init__(self) -> None:
        self._tournois: dict[int, Tournoi] = {}
        self._sequence = 0

    def ajouter(self, tournoi: Tournoi) -> Tournoi:
        self._sequence += 1
        persiste = Tournoi(
            nom=tournoi.nom,
            date=tournoi.date,
            lieu=tournoi.lieu,
            type_tournoi=tournoi.type_tournoi,
            id=self._sequence,
        )
        self._tournois[self._sequence] = persiste
        return persiste

    def par_id(self, tournoi_id: TournoiId) -> Tournoi | None:
        return self._tournois.get(tournoi_id)

    def lister(self) -> list[Tournoi]:
        return list(self._tournois.values())

    def enregistrer(self, tournoi: Tournoi) -> Tournoi:
        assert tournoi.id is not None
        self._tournois[tournoi.id] = tournoi
        return tournoi

    def supprimer(self, tournoi_id: TournoiId) -> None:
        del self._tournois[tournoi_id]


class FauxScoreRepository:
    """Repository en mémoire conforme au port `ScoreRepository`."""

    def __init__(self, archers: FauxArcherRepository) -> None:
        self._archers = archers
        self._scores: list[Score] = []
        self._sequence = 0

    def ajouter(self, score: Score) -> Score:
        self._sequence += 1
        persiste = Score(archer_id=score.archer_id, points=score.points, id=self._sequence)
        self._scores.append(persiste)
        return persiste

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Score]:
        ids = {a.id for a in self._archers.par_tournoi(tournoi_id)}
        return [s for s in self._scores if s.archer_id in ids]


class Montage(NamedTuple):
    """Attelage d'un test : les deux services et ce qu'il faut pour inscrire un archer.

    Champs **nommés** plutôt qu'un n-uplet positionnel : depuis E02US002 il faut un tournoi, une
    catégorie *de ce tournoi* et le référentiel des clubs pour un simple `ajouter`, et un
    `_, _, _, x = _monter()` ne se relit pas.
    """

    archers: ServiceArchers
    classement: ServiceClassement
    clubs: FauxClubRepository
    categories: FauxCategorieRepository
    tournois: FauxTournoiRepository
    tournoi_id: TournoiId
    categorie_id: CategorieId

    def autre_tournoi(self) -> tuple[TournoiId, CategorieId]:
        """Persiste un **second** tournoi avec sa propre catégorie ; renvoie leurs identifiants."""
        tournoi = self.tournois.ajouter(Tournoi.creer("Trophée d'hiver", _DATE))
        assert tournoi.id is not None
        categorie = self.categories.ajouter(Categorie.creer(tournoi.id, "Senior 1 H"))
        assert categorie.id is not None
        return tournoi.id, categorie.id


def _monter() -> Montage:
    """Monte les deux services sur un tournoi persisté portant une catégorie « Senior 1 H »."""
    tournois = FauxTournoiRepository()
    archers = FauxArcherRepository()
    scores = FauxScoreRepository(archers)
    clubs = FauxClubRepository()
    categories = FauxCategorieRepository()
    tournoi = tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
    assert tournoi.id is not None
    categorie = categories.ajouter(Categorie.creer(tournoi.id, "Senior 1 H"))
    assert categorie.id is not None
    return Montage(
        archers=ServiceArchers(tournois, archers, scores, clubs, categories),
        classement=ServiceClassement(tournois, archers, scores),
        clubs=clubs,
        categories=categories,
        tournois=tournois,
        tournoi_id=tournoi.id,
        categorie_id=categorie.id,
    )


def test_ajouter_archer_persiste_et_attribue_un_id() -> None:
    """`ajouter` inscrit l'archer au tournoi, dans sa catégorie, et lui attribue un identifiant."""
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id == 1
    assert (archer.nom, archer.prenom) == ("Robin", "Jean")
    assert archer.tournoi_id == m.tournoi_id
    assert archer.categorie_id == m.categorie_id
    assert archer.cible is None


def test_ajouter_archer_tournoi_inconnu_leve() -> None:
    """Inscrire dans un tournoi inexistant lève `TournoiIntrouvable`."""
    m = _monter()
    with pytest.raises(TournoiIntrouvable):
        m.archers.ajouter(404, "Robin", "Jean", m.categorie_id)


def test_ajouter_archer_propage_l_erreur_de_domaine_sur_le_nom() -> None:
    """Un nom d'archer vide fait remonter l'erreur du domaine (non persisté)."""
    m = _monter()
    with pytest.raises(NomArcherInvalide):
        m.archers.ajouter(m.tournoi_id, "  ", "Jean", m.categorie_id)


def test_ajouter_archer_propage_l_erreur_de_domaine_sur_le_prenom() -> None:
    """Un prénom d'archer vide fait remonter l'erreur du domaine (CA E02US002)."""
    m = _monter()
    with pytest.raises(PrenomArcherInvalide):
        m.archers.ajouter(m.tournoi_id, "Robin", "  ", m.categorie_id)


def test_ajouter_archer_categorie_inconnue_leve() -> None:
    """Une catégorie inexistante lève `CategorieHorsTournoi` (rien n'est persisté)."""
    m = _monter()
    with pytest.raises(CategorieHorsTournoi):
        m.archers.ajouter(m.tournoi_id, "Robin", "Jean", 404)
    assert m.classement.pour_tournoi(m.tournoi_id).lignes == ()


def test_ajouter_archer_categorie_d_un_autre_tournoi_leve() -> None:
    """La catégorie doit appartenir **au tournoi de l'archer** — règle inter-agrégats E02US002."""
    m = _monter()
    _, categorie_etrangere = m.autre_tournoi()
    with pytest.raises(CategorieHorsTournoi):
        m.archers.ajouter(m.tournoi_id, "Robin", "Jean", categorie_etrangere)
    assert m.classement.pour_tournoi(m.tournoi_id).lignes == ()


def test_ajouter_archer_sans_club_laisse_le_rattachement_vide() -> None:
    """Le club est **facultatif** : sans lui, `club_id` reste `None` (club inconnu, ADR-0014)."""
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.club_id is None


def test_ajouter_archer_avec_club_le_rattache() -> None:
    """Un `club_id` existant est porté par l'archer persisté (E02US001)."""
    m = _monter()
    club = m.clubs.ajouter(Club.creer("Arc Club Rennes"))
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id, club.id)
    assert archer.club_id == club.id


def test_ajouter_archer_club_inconnu_leve() -> None:
    """Inscrire avec un club inexistant lève `ClubIntrouvable` (rien n'est persisté)."""
    m = _monter()
    with pytest.raises(ClubIntrouvable):
        m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id, 404)
    assert m.classement.pour_tournoi(m.tournoi_id).lignes == ()


def test_ajouter_archer_saisie_invalide_leve_avant_l_homonymie() -> None:
    """Une entrée invalide rend l'erreur du **domaine**, pas un conflit d'homonyme (E02US002).

    Un prénom vide et un doublon peuvent être vrais en même temps ; c'est le 422 qui doit sortir —
    une saisie invalide n'est pas un conflit. Verrouille l'ordre : `Archer.creer` avant
    `_signaler_homonyme`, ce dont dépend aussi le fait que la clé porte sur le nom **normalisé**.
    """
    m = _monter()
    m.archers.ajouter(m.tournoi_id, "Dupont", "Jean", m.categorie_id)
    with pytest.raises(PrenomArcherInvalide):
        m.archers.ajouter(m.tournoi_id, "Dupont", "   ", m.categorie_id)


def test_ajouter_archer_signale_un_homonyme_du_meme_club() -> None:
    """Mêmes nom, prénom et club : doublon probable → `HomonymeArcher`, l'admin tranche."""
    m = _monter()
    club = m.clubs.ajouter(Club.creer("Arc Club Rennes"))
    m.archers.ajouter(m.tournoi_id, "Dupont", "Jean", m.categorie_id, club.id)
    with pytest.raises(HomonymeArcher):
        m.archers.ajouter(m.tournoi_id, "Dupont", "Jean", m.categorie_id, club.id)


def test_ajouter_archer_signale_un_homonyme_malgre_la_casse_et_les_accents() -> None:
    """« LEFEVRE remi » ressaisi pour « Lefèvre Rémi » est le doublon le plus probable."""
    m = _monter()
    m.archers.ajouter(m.tournoi_id, "Lefèvre", "Rémi", m.categorie_id)
    with pytest.raises(HomonymeArcher):
        m.archers.ajouter(m.tournoi_id, "  LEFEVRE ", "remi", m.categorie_id)


def test_ajouter_archer_confirme_inscrit_l_homonyme() -> None:
    """`autoriser_homonyme=True` : l'admin confirme deux personnes distinctes (père et fils)."""
    m = _monter()
    club = m.clubs.ajouter(Club.creer("Arc Club Rennes"))
    m.archers.ajouter(m.tournoi_id, "Dupont", "Jean", m.categorie_id, club.id)
    fils = m.archers.ajouter(
        m.tournoi_id, "Dupont", "Jean", m.categorie_id, club.id, autoriser_homonyme=True
    )
    assert fils.id == 2


def test_ajouter_archer_homonyme_d_un_autre_club_passe_sans_confirmation() -> None:
    """Deux homonymes de clubs **différents** sont deux archers distincts, pas un doublon."""
    m = _monter()
    rennes = m.clubs.ajouter(Club.creer("Arc Club Rennes"))
    fougeres = m.clubs.ajouter(Club.creer("Élan de Fougères"))
    m.archers.ajouter(m.tournoi_id, "Dupont", "Jean", m.categorie_id, rennes.id)
    autre = m.archers.ajouter(m.tournoi_id, "Dupont", "Jean", m.categorie_id, fougeres.id)
    assert autre.id == 2


def test_ajouter_archer_sans_club_n_est_pas_homonyme_d_un_archer_rattache() -> None:
    """`None` = club **inconnu** : rapprocher les deux supposerait de savoir ce qu'on ignore.

    Ce rapprochement-là relève de E02US005 (détecter et fusionner), pas d'un refus à la saisie.
    """
    m = _monter()
    club = m.clubs.ajouter(Club.creer("Arc Club Rennes"))
    m.archers.ajouter(m.tournoi_id, "Dupont", "Jean", m.categorie_id, club.id)
    sans_club = m.archers.ajouter(m.tournoi_id, "Dupont", "Jean", m.categorie_id)
    assert sans_club.id == 2


def test_ajouter_archer_signale_un_homonyme_entre_deux_archers_sans_club() -> None:
    """Sans club, la clé reste discriminante : deux « Dupont Jean » restent un doublon probable."""
    m = _monter()
    m.archers.ajouter(m.tournoi_id, "Dupont", "Jean", m.categorie_id)
    with pytest.raises(HomonymeArcher):
        m.archers.ajouter(m.tournoi_id, "Dupont", "Jean", m.categorie_id)


def test_ajouter_archer_homonyme_d_un_autre_tournoi_passe() -> None:
    """L'homonymie se juge **dans le tournoi** : le même archer revient d'un tournoi à l'autre."""
    m = _monter()
    m.archers.ajouter(m.tournoi_id, "Dupont", "Jean", m.categorie_id)
    autre_tournoi_id, autre_categorie_id = m.autre_tournoi()
    revenant = m.archers.ajouter(autre_tournoi_id, "Dupont", "Jean", autre_categorie_id)
    assert revenant.id == 2


def test_placer_archer_pose_la_cible() -> None:
    """`placer` met à jour la cible de l'archer persisté."""
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    assert m.archers.placer(archer.id, 4).cible == 4


def test_placer_archer_inconnu_leve() -> None:
    """Placer un archer inexistant lève `ArcherIntrouvable`."""
    m = _monter()
    with pytest.raises(ArcherIntrouvable):
        m.archers.placer(404, 1)


def test_placer_archer_propage_l_erreur_de_domaine() -> None:
    """Une cible invalide fait remonter l'erreur du domaine."""
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    with pytest.raises(CibleInvalide):
        m.archers.placer(archer.id, 0)


def test_saisir_score_persiste_la_fleche() -> None:
    """`saisir_score` enregistre une flèche pour un archer existant."""
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    score = m.archers.saisir_score(archer.id, 9)
    assert (score.id, score.archer_id, score.points) == (1, archer.id, 9)


def test_saisir_score_archer_inconnu_leve() -> None:
    """Saisir un score pour un archer inexistant lève `ArcherIntrouvable`."""
    m = _monter()
    with pytest.raises(ArcherIntrouvable):
        m.archers.saisir_score(404, 9)


def test_saisir_score_propage_l_erreur_de_domaine() -> None:
    """Un score hors plage fait remonter l'erreur du domaine."""
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    with pytest.raises(ScoreInvalide):
        m.archers.saisir_score(archer.id, 11)


def test_classement_reflete_les_scores_saisis() -> None:
    """Le service de classement agrège les scores des archers du tournoi."""
    m = _monter()
    alice = m.archers.ajouter(m.tournoi_id, "Martin", "Alice", m.categorie_id)
    bob = m.archers.ajouter(m.tournoi_id, "Durand", "Bob", m.categorie_id)
    assert alice.id is not None and bob.id is not None
    m.archers.saisir_score(alice.id, 10)
    m.archers.saisir_score(alice.id, 9)
    m.archers.saisir_score(bob.id, 8)

    lignes = m.classement.pour_tournoi(m.tournoi_id).lignes
    assert [(ligne.nom, ligne.rang, ligne.total) for ligne in lignes] == [
        ("Martin", 1, 19),
        ("Durand", 2, 8),
    ]


def test_classement_tournoi_inconnu_leve() -> None:
    """Consulter le classement d'un tournoi inexistant lève `TournoiIntrouvable`."""
    m = _monter()
    with pytest.raises(TournoiIntrouvable):
        m.classement.pour_tournoi(404)
