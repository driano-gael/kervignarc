"""Tests des services applicatifs Archers et Classement (E00US011, E02US002, E02US003).

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
    ArcherEngage,
    ArcherIntrouvable,
    CategorieHorsTournoi,
    ChangementCategorieArcherEngage,
    ClubIntrouvable,
    HomonymeArcher,
    SaisieHorsCible,
    TournoiIntrouvable,
)
from domain.archer import ArcherId
from domain.categorie import Categorie, CategorieId
from domain.club import Club
from domain.entree_audit import EntreeAudit
from domain.erreurs import (
    CibleInvalide,
    NomArcherInvalide,
    PrenomArcherInvalide,
    ScoreInvalide,
)
from domain.inscription import Inscription
from domain.poste import Poste
from domain.score import Score
from domain.serie import Serie
from domain.tournoi import Tournoi, TournoiId
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxClubRepository,
    FauxInscriptionRepository,
)

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
    """Repository en mémoire conforme au port `ScoreRepository`.

    **Les scores d'un archer supprimé deviennent invisibles**, comme en production : le vrai
    `ArcherRepositorySQL.supprimer` les efface dans sa transaction (E02US003). Le faux obtient la
    même chose en filtrant sur les archers encore présents — équivalence observable, sans mécanique
    d'abonnement. Un faux qui les laisserait apparaître verdirait un service à scores orphelins.
    """

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

    def par_archer(self, archer_id: ArcherId) -> list[Score]:
        # Le filtre sur `archer_id` rend testable le signalement portant sur **cet** archer-là :
        # un faux qui renverrait tous les scores du tournoi ferait passer au vert un service qui
        # signalerait tout inscrit dès la première flèche tirée. Le garde d'existence, lui,
        # reproduit la purge du vrai adapter (cf. docstring de la classe).
        if self._archers.par_id(archer_id) is None:
            return []
        return [s for s in self._scores if s.archer_id == archer_id]


class FauxSerieRepository:
    """Repository en mémoire conforme au port `SerieRepository`, réduit à ce que lit le classement.

    Depuis E06US001 le classement dérive des **séries** de saisie (E04US002), plus de l'agrégat
    `Score` du walking skeleton. Ces tests-là (service **archers**) n'ouvrent aucune série : le
    double renvoie une liste vide, et les méthodes d'écriture/lecture de saisie ne sont pas
    sollicitées ici — elles ne servent qu'à **conformer** le port (couvertes par `test_saisie_api`
    et `test_service_saisie`).
    """

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Serie]:
        return []

    def par_archer(self, tournoi_id: TournoiId, archer_id: ArcherId) -> Serie | None:
        raise NotImplementedError

    def horodatages(
        self, tournoi_id: TournoiId, archer_id: ArcherId
    ) -> dict[int, datetime.datetime]:
        raise NotImplementedError

    def enregistrer(self, serie: Serie) -> Serie:
        raise NotImplementedError

    def enregistrer_avec_trace(self, serie: Serie, entree: EntreeAudit) -> Serie:
        raise NotImplementedError


class Montage(NamedTuple):
    """Attelage d'un test : les deux services et ce qu'il faut pour inscrire un archer.

    Champs **nommés** plutôt qu'un n-uplet positionnel : depuis E02US002 il faut un tournoi, une
    catégorie *de ce tournoi* et le référentiel des clubs pour un simple `ajouter`, et un
    `_, _, _, x = _monter()` ne se relit pas.
    """

    archers: ServiceArchers
    classement: ServiceClassement
    inscrits: FauxArcherRepository
    scores: FauxScoreRepository
    clubs: FauxClubRepository
    categories: FauxCategorieRepository
    tournois: FauxTournoiRepository
    inscriptions: FauxInscriptionRepository
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
    series = FauxSerieRepository()
    clubs = FauxClubRepository()
    categories = FauxCategorieRepository()
    inscriptions = FauxInscriptionRepository()
    tournoi = tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
    assert tournoi.id is not None
    categorie = categories.ajouter(Categorie.creer(tournoi.id, "Senior 1 H"))
    assert categorie.id is not None
    return Montage(
        archers=ServiceArchers(tournois, archers, scores, clubs, categories, inscriptions),
        classement=ServiceClassement(tournois, archers, series, categories),
        inscrits=archers,
        scores=scores,
        clubs=clubs,
        categories=categories,
        tournois=tournois,
        inscriptions=inscriptions,
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


def _poste(tournoi_id: TournoiId, cible_index: int) -> Poste:
    """Un poste (credential de cible) prêt à contraindre une saisie (E10US007).

    Le `code` importe peu ici — le service compare `(tournoi_id, cible_index)`, pas le code — mais
    l'agrégat exige un code non vide : « CIBLE » fait l'affaire.
    """
    return Poste.creer(tournoi_id, cible_index, "CIBLE")


def test_saisir_score_par_un_poste_de_sa_cible_persiste() -> None:
    """Un poste saisit pour un archer placé sur **sa** cible (CA E10US007).

    C'est le geste nominal : la tablette fixée à la cible 4 marque une flèche d'un archer placé sur
    la cible 4 — aucune authentification d'utilisateur, l'identité est **le lieu**.
    """
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    m.archers.placer(archer.id, 4)
    score = m.archers.saisir_score(archer.id, 9, _poste(m.tournoi_id, 4))
    assert (score.archer_id, score.points) == (archer.id, 9)


def test_saisir_score_par_un_poste_d_une_autre_cible_leve() -> None:
    """Un poste ne peut **pas** saisir pour un archer d'une autre cible (CA E10US007).

    Le cœur de l'US : « un poste ne saisit que pour SA cible ». Le poste de la cible 5 qui vise un
    archer placé sur la cible 4 est refusé — 403 à la frontière (authentifié, mais pas pour cette
    cible), pas 401.
    """
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    m.archers.placer(archer.id, 4)
    with pytest.raises(SaisieHorsCible):
        m.archers.saisir_score(archer.id, 9, _poste(m.tournoi_id, 5))


def test_saisir_score_par_un_poste_d_un_autre_tournoi_leve() -> None:
    """« SA cible » se juge aussi sur le **tournoi**, pas seulement l'index (CA E10US007).

    Plusieurs tournois tournent en concurrence (intérieur + extérieur) et les numéros de cible se
    répètent : sans le contrôle du `tournoi_id`, le poste « cible 4 » du tournoi voisin saisirait
    pour la cible 4 de celui-ci. Même index, autre tournoi ⇒ refus.
    """
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    m.archers.placer(archer.id, 4)
    autre_tournoi_id, _ = m.autre_tournoi()
    with pytest.raises(SaisieHorsCible):
        m.archers.saisir_score(archer.id, 9, _poste(autre_tournoi_id, 4))


def test_saisir_score_par_un_poste_pour_un_archer_non_place_leve() -> None:
    """Un poste ne saisit pas pour un archer **sans cible** (CA E10US007).

    Un archer non placé n'est sur aucune cible, donc sur aucune cible d'un poste : la saisie par le
    lieu n'a pas d'ancrage. Seul l'admin peut saisir hors placement (démo du walking skeleton).
    """
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    with pytest.raises(SaisieHorsCible):
        m.archers.saisir_score(archer.id, 9, _poste(m.tournoi_id, 4))


def test_saisir_score_admin_ne_subit_aucune_contrainte_de_cible() -> None:
    """Sans poste (`poste_autorise=None`), la saisie n'est **pas** contrainte à une cible.

    L'admin (E10US001) reste autorisé partout, y compris pour un archer non placé : le paramètre par
    défaut `None` préserve exactement le comportement d'avant E10US007 (« l'admin reste autorisé »).
    """
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    score = m.archers.saisir_score(archer.id, 9)
    assert (score.archer_id, score.points) == (archer.id, 9)


def test_saisir_score_archer_inconnu_leve_meme_avec_un_poste() -> None:
    """L'existence de l'archer se contrôle **avant** sa cible, même via un poste (CA E10US007).

    Un archer inexistant n'a pas de cible à confronter au poste : l'ordre (`_archer_existant` avant
    le contrôle de cible) rend un 404, pas un 403 — rien ne le pinnait sans ce test.
    """
    m = _monter()
    with pytest.raises(ArcherIntrouvable):
        m.archers.saisir_score(404, 9, _poste(m.tournoi_id, 4))


def test_modifier_archer_met_a_jour_les_quatre_champs() -> None:
    """`modifier` édite le nom, le prénom, la catégorie et le club, et persiste (E02US003)."""
    m = _monter()
    rennes = m.clubs.ajouter(Club.creer("Arc Club Rennes"))
    fougeres = m.clubs.ajouter(Club.creer("Élan de Fougères"))
    autre_categorie = m.categories.ajouter(Categorie.creer(m.tournoi_id, "Senior 2 H"))
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id, rennes.id)
    assert archer.id is not None and autre_categorie.id is not None

    edite = m.archers.modifier(
        archer.id, "Robin des Bois", "Jeanne", autre_categorie.id, fougeres.id
    )
    assert (edite.nom, edite.prenom) == ("Robin des Bois", "Jeanne")
    assert (edite.categorie_id, edite.club_id) == (autre_categorie.id, fougeres.id)
    assert m.inscrits.par_id(archer.id) == edite


def test_modifier_archer_inconnu_leve() -> None:
    """Éditer un archer inexistant lève `ArcherIntrouvable`."""
    m = _monter()
    with pytest.raises(ArcherIntrouvable):
        m.archers.modifier(404, "Robin", "Jean", m.categorie_id)


def test_modifier_archer_propage_l_erreur_de_domaine_sur_le_nom() -> None:
    """L'édition rejoue les contrôles de l'inscription : un nom vide remonte du domaine."""
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    with pytest.raises(NomArcherInvalide):
        m.archers.modifier(archer.id, "  ", "Jean", m.categorie_id)


def test_modifier_archer_categorie_d_un_autre_tournoi_leve() -> None:
    """La catégorie éditée doit rester **du tournoi de l'archer** (règle inter-agrégats)."""
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    _, categorie_etrangere = m.autre_tournoi()
    with pytest.raises(CategorieHorsTournoi):
        m.archers.modifier(archer.id, "Robin", "Jean", categorie_etrangere)


def test_modifier_archer_club_inconnu_leve() -> None:
    """Éditer vers un club inexistant lève `ClubIntrouvable` ; l'archer reste intact."""
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    with pytest.raises(ClubIntrouvable):
        m.archers.modifier(archer.id, "Robin", "Jean", m.categorie_id, 404)
    assert m.inscrits.par_id(archer.id) == archer


def test_modifier_archer_renseigne_le_club_reste_inconnu() -> None:
    """Le cas d'usage d'ADR-0014 : la licence retrouvée, l'admin corrige le club inconnu."""
    m = _monter()
    club = m.clubs.ajouter(Club.creer("Arc Club Rennes"))
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None and archer.club_id is None
    assert (
        m.archers.modifier(archer.id, "Robin", "Jean", m.categorie_id, club.id).club_id == club.id
    )


def test_modifier_archer_detache_le_club() -> None:
    """Repasser à « club inconnu » est possible : `club_id=None` détache (ADR-0014)."""
    m = _monter()
    club = m.clubs.ajouter(Club.creer("Arc Club Rennes"))
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id, club.id)
    assert archer.id is not None
    assert m.archers.modifier(archer.id, "Robin", "Jean", m.categorie_id, None).club_id is None


def test_modifier_archer_a_l_identique_est_accepte() -> None:
    """Réenregistrer un archer sans rien changer ne se signale pas lui-même comme homonyme.

    Sans le `sauf=archer_id` de `_signaler_homonyme`, l'archer serait son propre doublon et
    toute édition deviendrait impossible (patron `ServiceClubs.modifier`, E02US001).
    """
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    assert m.archers.modifier(archer.id, "Robin", "Jean", m.categorie_id) == archer


def test_modifier_archer_signale_un_homonyme() -> None:
    """Éditer un archer **vers** l'identité d'un autre inscrit est signalé (E02US003)."""
    m = _monter()
    m.archers.ajouter(m.tournoi_id, "Dupont", "Jean", m.categorie_id)
    autre = m.archers.ajouter(m.tournoi_id, "Martin", "Alice", m.categorie_id)
    assert autre.id is not None
    with pytest.raises(HomonymeArcher):
        m.archers.modifier(autre.id, "Dupont", "Jean", m.categorie_id)


def test_modifier_archer_confirme_accepte_l_homonyme() -> None:
    """`autoriser_homonyme=True` : l'admin confirme deux personnes distinctes, comme à l'ajout."""
    m = _monter()
    m.archers.ajouter(m.tournoi_id, "Dupont", "Jean", m.categorie_id)
    autre = m.archers.ajouter(m.tournoi_id, "Martin", "Alice", m.categorie_id)
    assert autre.id is not None
    edite = m.archers.modifier(autre.id, "Dupont", "Jean", m.categorie_id, autoriser_homonyme=True)
    assert (edite.nom, edite.prenom) == ("Dupont", "Jean")


def test_modifier_archer_ne_resignale_pas_un_homonyme_deja_confirme() -> None:
    """Éditer autre chose que l'identité d'un homonyme **déjà confirmé** ne redemande rien.

    Le fils a été inscrit sur confirmation (même nom, prénom et club que son père) ; corriger sa
    seule catégorie ne fait apparaître aucun doublon nouveau. Re-signaler ici rejouerait
    l'arbitrage à chaque édition, jusqu'à ce que l'admin confirme sans lire.
    """
    m = _monter()
    club = m.clubs.ajouter(Club.creer("Arc Club Rennes"))
    autre_categorie = m.categories.ajouter(Categorie.creer(m.tournoi_id, "Senior 2 H"))
    m.archers.ajouter(m.tournoi_id, "Dupont", "Jean", m.categorie_id, club.id)
    fils = m.archers.ajouter(
        m.tournoi_id, "Dupont", "Jean", m.categorie_id, club.id, autoriser_homonyme=True
    )
    assert fils.id is not None and autre_categorie.id is not None
    edite = m.archers.modifier(fils.id, "Dupont", "Jean", autre_categorie.id, club.id)
    assert edite.categorie_id == autre_categorie.id


def test_modifier_archer_signale_le_changement_de_categorie_d_un_archer_engage() -> None:
    """Changer la catégorie d'un archer **qui a déjà tiré** est signalé (CA E02US003)."""
    m = _monter()
    autre_categorie = m.categories.ajouter(Categorie.creer(m.tournoi_id, "Senior 2 H"))
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None and autre_categorie.id is not None
    m.archers.saisir_score(archer.id, 9)
    with pytest.raises(ChangementCategorieArcherEngage):
        m.archers.modifier(archer.id, "Robin", "Jean", autre_categorie.id)


def test_modifier_archer_confirme_accepte_le_changement_de_categorie() -> None:
    """`autoriser_changement_categorie=True` : l'admin corrige une catégorie mal saisie."""
    m = _monter()
    autre_categorie = m.categories.ajouter(Categorie.creer(m.tournoi_id, "Senior 2 H"))
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None and autre_categorie.id is not None
    m.archers.saisir_score(archer.id, 9)
    edite = m.archers.modifier(
        archer.id, "Robin", "Jean", autre_categorie.id, autoriser_changement_categorie=True
    )
    assert edite.categorie_id == autre_categorie.id


def _archer_engage_et_homonyme_en_vue() -> tuple[Montage, ArcherId, CategorieId]:
    """Monte le seul cas où les **deux** signalements sont vrais du même coup (E02US003).

    Un archer qui a tiré, qu'on édite vers l'identité d'un inscrit **et** vers une autre
    catégorie : c'est le cas d'usage nominal du CA (corriger une catégorie mal saisie) croisé
    avec celui d'ADR-0014 (renseigner enfin le club) — donc tout sauf théorique.
    """
    m = _monter()
    autre_categorie = m.categories.ajouter(Categorie.creer(m.tournoi_id, "Senior 2 H"))
    m.archers.ajouter(m.tournoi_id, "Dupont", "Jean", m.categorie_id)
    tireur = m.archers.ajouter(m.tournoi_id, "Martin", "Alice", m.categorie_id)
    assert tireur.id is not None and autre_categorie.id is not None
    m.archers.saisir_score(tireur.id, 9)
    return m, tireur.id, autre_categorie.id


def test_modifier_archer_autoriser_homonyme_ne_leve_pas_le_signalement_de_categorie() -> None:
    """Un drapeau ne lève que **son** signalement : les deux sont indépendants (CA E02US003).

    Sans quoi confirmer un homonyme emporterait en douce le déplacement des flèches d'un archer
    vers un autre classement — que l'admin n'aurait jamais confirmé.
    """
    m, tireur_id, autre_categorie_id = _archer_engage_et_homonyme_en_vue()
    with pytest.raises(ChangementCategorieArcherEngage):
        m.archers.modifier(tireur_id, "Dupont", "Jean", autre_categorie_id, autoriser_homonyme=True)


def test_modifier_archer_autoriser_changement_categorie_ne_leve_pas_l_homonyme() -> None:
    """Pendant du test ci-dessus, dans l'autre sens : confirmer la catégorie ne dédouble pas."""
    m, tireur_id, autre_categorie_id = _archer_engage_et_homonyme_en_vue()
    with pytest.raises(HomonymeArcher):
        m.archers.modifier(
            tireur_id,
            "Dupont",
            "Jean",
            autre_categorie_id,
            autoriser_changement_categorie=True,
        )


def test_modifier_archer_les_deux_confirmations_ensemble_passent() -> None:
    """Les deux drapeaux ensemble enregistrent : c'est la **sortie** du protocole en cascade.

    Sans ce test, rien ne dit que la séquence a une fin — et le front peut boucler entre les deux
    409 sans que la suite bronche (c'est arrivé : il n'accumulait pas les drapeaux).
    """
    m, tireur_id, autre_categorie_id = _archer_engage_et_homonyme_en_vue()
    edite = m.archers.modifier(
        tireur_id,
        "Dupont",
        "Jean",
        autre_categorie_id,
        autoriser_homonyme=True,
        autoriser_changement_categorie=True,
    )
    assert (edite.nom, edite.prenom) == ("Dupont", "Jean")
    assert edite.categorie_id == autre_categorie_id


def test_modifier_categorie_d_un_archer_place_sans_score_ne_signale_rien() -> None:
    """« Engagé » n'a pas le même sens dans les deux règles, et c'est voulu (CA E02US003).

    `ArcherEngage` (suppression) = placé **ou** scores ; le signalement de catégorie = scores
    **seuls**. Un placement ne fausse aucun classement : rien à confirmer. Sans ce test, élargir
    le signalement à `cible is not None` passerait toute la suite au vert.
    """
    m = _monter()
    autre_categorie = m.categories.ajouter(Categorie.creer(m.tournoi_id, "Senior 2 H"))
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None and autre_categorie.id is not None
    m.archers.placer(archer.id, 3)
    edite = m.archers.modifier(archer.id, "Robin", "Jean", autre_categorie.id)
    assert (edite.categorie_id, edite.cible) == (autre_categorie.id, 3)


def test_modifier_archer_engage_sans_toucher_a_la_categorie_ne_signale_rien() -> None:
    """Le signalement porte sur le **changement** de catégorie, pas sur l'archer engagé.

    Corriger l'orthographe du nom d'un archer qui a tiré n'a rien à confirmer : sa catégorie
    est la même qu'avant.
    """
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robain", "Jean", m.categorie_id)
    assert archer.id is not None
    m.archers.saisir_score(archer.id, 9)
    assert m.archers.modifier(archer.id, "Robin", "Jean", m.categorie_id).nom == "Robin"


def test_modifier_archer_non_engage_change_de_categorie_sans_confirmation() -> None:
    """Sans score, la catégorie s'édite librement : il n'y a rien qui puisse être faussé."""
    m = _monter()
    autre_categorie = m.categories.ajouter(Categorie.creer(m.tournoi_id, "Senior 2 H"))
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None and autre_categorie.id is not None
    edite = m.archers.modifier(archer.id, "Robin", "Jean", autre_categorie.id)
    assert edite.categorie_id == autre_categorie.id


def test_modifier_archer_preserve_le_placement() -> None:
    """Corriger l'état civil d'un archer placé ne le retire pas de sa cible (E02US003)."""
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    m.archers.placer(archer.id, 4)
    assert m.archers.modifier(archer.id, "Robin", "Jeanne", m.categorie_id).cible == 4


def test_modifier_archer_saisie_invalide_leve_avant_les_conflits() -> None:
    """Une entrée invalide rend le 422 du domaine, pas un conflit — même ordre qu'à l'ajout."""
    m = _monter()
    m.archers.ajouter(m.tournoi_id, "Dupont", "Jean", m.categorie_id)
    autre = m.archers.ajouter(m.tournoi_id, "Martin", "Alice", m.categorie_id)
    assert autre.id is not None
    with pytest.raises(PrenomArcherInvalide):
        m.archers.modifier(autre.id, "Dupont", "   ", m.categorie_id)


def test_supprimer_archer_retire_l_inscription() -> None:
    """`supprimer` retire un archer ni placé ni engagé (E02US003)."""
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    m.archers.supprimer(archer.id)
    assert m.inscrits.par_id(archer.id) is None
    assert m.classement.pour_tournoi(m.tournoi_id).lignes == ()


def test_supprimer_archer_inconnu_leve() -> None:
    """Supprimer un archer inexistant lève `ArcherIntrouvable`."""
    m = _monter()
    with pytest.raises(ArcherIntrouvable):
        m.archers.supprimer(404)


def test_supprimer_archer_place_signale() -> None:
    """Occuper une cible suspend la suppression — un signalement, pas un refus (CA E02US003)."""
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    m.archers.placer(archer.id, 4)
    with pytest.raises(ArcherEngage):
        m.archers.supprimer(archer.id)
    assert m.inscrits.par_id(archer.id) is not None


def test_supprimer_archer_avec_scores_signale() -> None:
    """Dès la première flèche, la suppression se confirme : on ne l'efface pas d'un clic."""
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    m.archers.saisir_score(archer.id, 9)
    with pytest.raises(ArcherEngage):
        m.archers.supprimer(archer.id)
    assert m.inscrits.par_id(archer.id) is not None


def test_supprimer_archer_signale_ne_detruit_rien() -> None:
    """Le 409 est une **question**, pas un début d'exécution (CA E02US003).

    L'invariant central de l'US : tant que l'admin n'a pas confirmé, l'archer, sa cible **et ses
    flèches** sont intacts. Les tests de signalement ci-dessus n'assertent que la survie de
    l'archer — une purge déplacée avant le contrôle les laisserait tous verts en détruisant les
    scores sur le refus même.
    """
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    m.archers.saisir_score(archer.id, 9)
    m.archers.placer(archer.id, 4)

    with pytest.raises(ArcherEngage):
        m.archers.supprimer(archer.id)

    intact = m.inscrits.par_id(archer.id)
    assert intact is not None and intact.cible == 4
    # Les flèches survivent au refus : on l'observe sur le repository de scores (le classement, lui,
    # dérive désormais des séries de saisie E04US002, pas de l'agrégat `Score` — E06US001).
    assert [s.points for s in m.scores.par_archer(archer.id)] == [9]


def test_supprimer_archer_inconnu_leve_meme_confirme() -> None:
    """`autoriser_suppression_engage` lève un **signalement**, pas le contrôle d'existence.

    Un drapeau de confirmation ne doit jamais avaler un 404 : l'ordre (`_archer_existant` avant
    le signalement) est juste aujourd'hui, rien ne le pinnait.
    """
    m = _monter()
    with pytest.raises(ArcherIntrouvable):
        m.archers.supprimer(404, autoriser_suppression_engage=True)


def test_signalement_d_engagement_dit_ce_qui_sera_detruit() -> None:
    """Le message énumère les flèches **et** le placement (CA E02US003).

    C'est la seule chose qui, à l'écran, distingue une suppression légitime (erreur de saisie)
    d'un abandon mal enregistré — que le forfait d'E12US004 doit servir. Un message vague ferait
    de la destruction le chemin par défaut de l'archer qui s'en va, et les flèches partiraient
    avec.
    """
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    m.archers.saisir_score(archer.id, 9)
    m.archers.saisir_score(archer.id, 10)
    m.archers.placer(archer.id, 4)
    with pytest.raises(ArcherEngage) as leve:
        m.archers.supprimer(archer.id)
    assert "2 flèches déjà tirées" in leve.value.message
    assert "cible 4" in leve.value.message
    assert "forfait" in leve.value.message


def test_signalement_d_engagement_accorde_au_singulier() -> None:
    """Une seule flèche s'écrit « 1 flèche », pas « 1 flèche(s) ».

    **Non-régression, pas un CA** : le CA est muet sur la typographie du message, et l'oracle est
    ici le rendu actuel. Il vaut quand même d'être figé — ce message est lu par un bénévole au
    moment où il s'apprête à détruire des données : il doit se lire, pas se décoder. La faute
    d'origine (« 1 flèche(s) ») n'a été vue qu'en lisant la vraie sortie à l'écran.
    """
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    m.archers.saisir_score(archer.id, 9)
    with pytest.raises(ArcherEngage) as leve:
        m.archers.supprimer(archer.id)
    assert "1 flèche déjà tirée" in leve.value.message
    assert "(s)" not in leve.value.message


def test_supprimer_archer_inscrit_sur_un_depart_signale() -> None:
    """Une inscription sur un départ suffit à rendre l'archer « engagé » (CA E02US009, glossaire).

    Ni score ni placement — seulement une inscription : la suppression se signale quand même, car
    la confirmer effacera cette inscription (et sa ligne de facturation).
    """
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    m.inscriptions.ajouter(Inscription.creer(archer.id, depart_id=1))
    with pytest.raises(ArcherEngage):
        m.archers.supprimer(archer.id)
    assert m.inscrits.par_id(archer.id) is not None


def test_signalement_d_engagement_mentionne_les_inscriptions() -> None:
    """Le message énumère les inscriptions au même titre que les flèches (CA E02US009).

    Une seule inscription s'écrit « 1 inscription sur un départ » — même soin d'accord que pour les
    flèches : le message est lu au moment de détruire des données.
    """
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    m.inscriptions.ajouter(Inscription.creer(archer.id, 1))
    m.inscriptions.ajouter(Inscription.creer(archer.id, 2))
    with pytest.raises(ArcherEngage) as leve:
        m.archers.supprimer(archer.id)
    assert "2 inscriptions sur des départs" in leve.value.message


def test_signalement_d_engagement_inscription_accorde_au_singulier() -> None:
    """Une seule inscription s'écrit « 1 inscription sur un départ » (CA E02US009).

    **Non-régression de lisibilité**, symétrique de l'accord des flèches : le message est lu par un
    bénévole au moment de détruire des données, il doit se lire, pas se décoder. Le pluriel est
    couvert au-dessus ; on fige ici le singulier (« un départ », pas « des départs »).
    """
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    m.inscriptions.ajouter(Inscription.creer(archer.id, 1))
    with pytest.raises(ArcherEngage) as leve:
        m.archers.supprimer(archer.id)
    assert "1 inscription sur un départ" in leve.value.message
    assert "inscriptions sur des départs" not in leve.value.message


def test_supprimer_archer_inscrit_confirme_efface_l_archer() -> None:
    """`autoriser_suppression_engage=True` : l'admin confirme, l'archer (et ses liens) partent.

    La purge des inscriptions elle-même est un contrat d'adapter (prouvé au niveau du repository) ;
    ici on vérifie que la confirmation lève bien le signalement et retire l'archer.
    """
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    m.inscriptions.ajouter(Inscription.creer(archer.id, 1))
    m.archers.supprimer(archer.id, autoriser_suppression_engage=True)
    assert m.inscrits.par_id(archer.id) is None


def test_supprimer_archer_engage_confirme_efface_l_archer_et_ses_scores() -> None:
    """`autoriser_suppression_engage=True` : l'admin confirme une erreur d'inscription.

    La suppression **emporte les scores** — c'est le contrat du port, et c'est le prix que le
    message annonce. Un archer qui abandonne ne passe pas par là (forfait, E12US004).
    """
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    m.archers.saisir_score(archer.id, 9)
    m.archers.placer(archer.id, 4)

    m.archers.supprimer(archer.id, autoriser_suppression_engage=True)
    assert m.inscrits.par_id(archer.id) is None
    assert m.classement.pour_tournoi(m.tournoi_id).lignes == ()


def test_supprimer_archer_engage_confirme_ne_touche_pas_aux_autres() -> None:
    """La purge est cloisonnée : les flèches des autres inscrits survivent (CA E02US003)."""
    m = _monter()
    partant = m.archers.ajouter(m.tournoi_id, "Durand", "Bob", m.categorie_id)
    reste = m.archers.ajouter(m.tournoi_id, "Martin", "Alice", m.categorie_id)
    assert partant.id is not None and reste.id is not None
    m.archers.saisir_score(partant.id, 9)
    m.archers.saisir_score(reste.id, 8)

    m.archers.supprimer(partant.id, autoriser_suppression_engage=True)
    # La purge est cloisonnée : les flèches de l'archer resté (Alice) survivent, celles du partant
    # ont disparu. On l'observe sur le repo de scores (le classement ne reflète plus l'agrégat
    # `Score` depuis E06US001).
    assert [s.points for s in m.scores.par_archer(reste.id)] == [8]
    assert m.scores.par_archer(partant.id) == []


def test_supprimer_archer_libre_ne_demande_aucune_confirmation() -> None:
    """Ni placé ni engagé : rien à détruire, donc rien à confirmer (CA E02US003)."""
    m = _monter()
    archer = m.archers.ajouter(m.tournoi_id, "Robin", "Jean", m.categorie_id)
    assert archer.id is not None
    m.archers.supprimer(archer.id)
    assert m.inscrits.par_id(archer.id) is None


def test_supprimer_archer_ignore_les_scores_des_autres() -> None:
    """Le refus se juge sur les scores **de cet archer**, pas sur ceux du tournoi.

    Sans ce filtre, la première flèche du tournoi rendrait tous les inscrits indéboulonnables.
    """
    m = _monter()
    tireur = m.archers.ajouter(m.tournoi_id, "Martin", "Alice", m.categorie_id)
    absent = m.archers.ajouter(m.tournoi_id, "Durand", "Bob", m.categorie_id)
    assert tireur.id is not None and absent.id is not None
    m.archers.saisir_score(tireur.id, 9)
    m.archers.supprimer(absent.id)
    assert m.inscrits.par_id(absent.id) is None


def test_lister_archers_du_tournoi_trie_par_nom_et_prenom() -> None:
    """L'écran d'admin liste les inscrits **du tournoi**, dans l'ordre où on les cherche à l'œil.

    « Élan » entre « Dupont » et « Zola » : c'est le repli des accents (`cle_nom`) qui le place là.
    Un tri sur le nom brut le renverrait après « Zola », en fin de liste.
    """
    m = _monter()
    m.archers.ajouter(m.tournoi_id, "Zola", "Émile", m.categorie_id)
    m.archers.ajouter(m.tournoi_id, "Élan", "Bruno", m.categorie_id)
    m.archers.ajouter(m.tournoi_id, "Dupont", "Paul", m.categorie_id)
    m.archers.ajouter(m.tournoi_id, "Dupont", "Anne", m.categorie_id)
    autre_tournoi_id, autre_categorie_id = m.autre_tournoi()
    m.archers.ajouter(autre_tournoi_id, "Aaron", "Zoé", autre_categorie_id)

    listes = [(a.nom, a.prenom) for a in m.archers.lister(m.tournoi_id)]
    assert listes == [("Dupont", "Anne"), ("Dupont", "Paul"), ("Élan", "Bruno"), ("Zola", "Émile")]


def test_lister_archers_ordonne_deux_homonymes_de_facon_stable() -> None:
    """Deux homonymes confirmés ont la **même clé** de tri : l'`id` doit les départager.

    Sans ce 3ᵉ terme, leur ordre serait celui du `SELECT` sans `ORDER BY` de `par_tournoi`, que
    SQLite ne garantit pas — les deux lignes permuteraient d'un rafraîchissement à l'autre, sur
    l'écran même où le bénévole doit les distinguer à l'œil.
    """
    m = _monter()
    club = m.clubs.ajouter(Club.creer("Arc Club Rennes"))
    pere = m.archers.ajouter(m.tournoi_id, "Dupont", "Jean", m.categorie_id, club.id)
    fils = m.archers.ajouter(
        m.tournoi_id, "Dupont", "Jean", m.categorie_id, club.id, autoriser_homonyme=True
    )
    assert [a.id for a in m.archers.lister(m.tournoi_id)] == [pere.id, fils.id]


def test_lister_archers_tournoi_inconnu_leve() -> None:
    """Lister les archers d'un tournoi inexistant lève `TournoiIntrouvable`."""
    m = _monter()
    with pytest.raises(TournoiIntrouvable):
        m.archers.lister(404)


# Le contenu du classement (cumul, départage, catégories) et son refus de tournoi inconnu sont
# désormais couverts par `test_service_classement` et `test_domain_classement` : depuis E06US001, le
# classement dérive des séries de saisie (E04US002), pas de l'agrégat `Score` que pilote ce service.
