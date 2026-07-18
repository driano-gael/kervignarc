"""Tests du service Documents de salle (E09US008) — dérivés du CA, avant implémentation (règle 9).

Le CA (`stories/E09-exports.md`, E09US008) tient en exigences vérifiables ici :

- **un QR par cible** : une étiquette par cible **préparée** (poste), portant le `cible_index`, le
  `code` en clair et l'**URL de rattachement** (`…/?poste=<code>`, la forme lue par le front,
  `frontend/src/features/poste/url.ts`) ;
- **un papier par scoreur** : une carte par scoreur, avec son nom et son code personnel ;
- **lié au tournoi** : seuls les postes/scoreurs de **ce** tournoi figurent, et son nom en-tête ;
- **régénérable** : régénérer deux fois donne le **même** document (les codes sont persistés,
  stables — on réimprime, on ne réémet pas).

Le rendu PDF (QR compris) est un adapter, testé à part (`test_documents_salle_reportlab.py`) : ici
on substitue un **faux générateur** qui capture le document composé, seule chose que le service
décide.
La garde 404 (`TournoiIntrouvable`) reprend le contrat des autres services du tournoi.
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.documents_salle import ServiceDocumentsSalle
from application.erreurs import TournoiIntrouvable
from domain.documents_salle import CartesScoreurs, EtiquettesCibles
from domain.poste import Poste, PosteId, normaliser_code
from domain.scoreur import Scoreur, ScoreurId
from domain.tournoi import Tournoi, TournoiId

_ORIGINE = "http://192.168.1.10:8000/"


# --- Fakes locaux (patron des autres tests de service) -----------------------------------------


class FauxTournoiRepository:
    """Repository de tournois en mémoire (seul `par_id` est exercé ici)."""

    def __init__(self) -> None:
        self._tournois: dict[int, Tournoi] = {}
        self._sequence = 0

    def ajouter(self, tournoi: Tournoi) -> Tournoi:
        self._sequence += 1
        persiste = dataclasses.replace(tournoi, id=self._sequence)
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


class FauxPosteRepository:
    """Repository de postes en mémoire ; `par_tournoi` renvoie **non trié** (le service ordonne)."""

    def __init__(self) -> None:
        self._postes: dict[int, Poste] = {}
        self._sequence = 0

    def ajouter(self, poste: Poste) -> Poste:
        self._sequence += 1
        persiste = dataclasses.replace(poste, id=self._sequence)
        self._postes[self._sequence] = persiste
        return persiste

    def par_id(self, poste_id: PosteId) -> Poste | None:
        return self._postes.get(poste_id)

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Poste]:
        # Ordre inverse volontaire : prouve que le service trie par numéro de cible.
        return [p for p in self._postes.values() if p.tournoi_id == tournoi_id][::-1]

    def par_code(self, code: str) -> Poste | None:
        recherche = normaliser_code(code)
        return next((p for p in self._postes.values() if p.code == recherche), None)


class FauxScoreurRepository:
    """Repository de scoreurs en mémoire ; `par_tournoi` renvoie **non trié** (le service trie)."""

    def __init__(self) -> None:
        self._scoreurs: dict[int, Scoreur] = {}
        self._sequence = 0

    def ajouter(self, scoreur: Scoreur) -> Scoreur:
        self._sequence += 1
        persiste = dataclasses.replace(scoreur, id=self._sequence)
        self._scoreurs[self._sequence] = persiste
        return persiste

    def par_id(self, scoreur_id: ScoreurId) -> Scoreur | None:
        return self._scoreurs.get(scoreur_id)

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Scoreur]:
        return [s for s in self._scoreurs.values() if s.tournoi_id == tournoi_id][::-1]

    def par_code(self, code: str) -> Scoreur | None:
        recherche = normaliser_code(code)
        return next((s for s in self._scoreurs.values() if s.code == recherche), None)

    def enregistrer(self, scoreur: Scoreur) -> Scoreur:
        assert scoreur.id is not None
        self._scoreurs[scoreur.id] = scoreur
        return scoreur

    def supprimer(self, scoreur_id: ScoreurId) -> None:
        del self._scoreurs[scoreur_id]


class FauxGenerateur:
    """Capture le dernier document composé et renvoie des octets sentinelles, par type de document.

    Le service ne connaît que le port : ce faux prouve *quel* document est composé, sans dépendre de
    ReportLab (adapter testé à part)."""

    SENTINELLE_CIBLES = b"%PDF-etiquettes"
    SENTINELLE_SCOREURS = b"%PDF-cartes"

    def __init__(self) -> None:
        self.dernieres_cibles: EtiquettesCibles | None = None
        self.dernieres_cartes: CartesScoreurs | None = None

    def etiquettes_cibles(self, document: EtiquettesCibles) -> bytes:
        self.dernieres_cibles = document
        return self.SENTINELLE_CIBLES

    def cartes_scoreurs(self, document: CartesScoreurs) -> bytes:
        self.dernieres_cartes = document
        return self.SENTINELLE_SCOREURS


# --- Décor -------------------------------------------------------------------------------------


@dataclasses.dataclass
class _Monde:
    service: ServiceDocumentsSalle
    generateur: FauxGenerateur
    postes: FauxPosteRepository
    scoreurs: FauxScoreurRepository
    tournoi_id: int

    def preparer_cible(self, cible_index: int, code: str) -> None:
        self.postes.ajouter(Poste.creer(self.tournoi_id, cible_index, code))

    def definir_scoreur(self, nom: str, code: str) -> None:
        self.scoreurs.ajouter(Scoreur.creer(self.tournoi_id, nom, code))


def _monde() -> _Monde:
    tournois = FauxTournoiRepository()
    postes = FauxPosteRepository()
    scoreurs = FauxScoreurRepository()
    generateur = FauxGenerateur()

    tournoi = tournois.ajouter(Tournoi.creer("Tournoi Test", datetime.date(2026, 1, 18)))
    assert tournoi.id is not None

    service = ServiceDocumentsSalle(tournois, postes, scoreurs, generateur)
    return _Monde(
        service=service,
        generateur=generateur,
        postes=postes,
        scoreurs=scoreurs,
        tournoi_id=tournoi.id,
    )


# --- Étiquettes de cible -----------------------------------------------------------------------


def test_une_etiquette_par_cible_avec_url_et_code() -> None:
    """Un QR par cible : chaque étiquette porte son numéro, son code en clair et l'URL de
    rattachement `…/?poste=<code>` (la forme lue par le front)."""
    monde = _monde()
    monde.preparer_cible(1, "AAA111")
    monde.preparer_cible(2, "BBB222")

    octets = monde.service.etiquettes_cibles(monde.tournoi_id, _ORIGINE)

    assert octets == FauxGenerateur.SENTINELLE_CIBLES
    document = monde.generateur.dernieres_cibles
    assert document is not None
    assert document.nom_tournoi == "Tournoi Test"
    assert [(e.cible_index, e.code) for e in document.etiquettes] == [(1, "AAA111"), (2, "BBB222")]
    assert document.etiquettes[0].url == "http://192.168.1.10:8000/?poste=AAA111"
    assert document.etiquettes[1].url == "http://192.168.1.10:8000/?poste=BBB222"


def test_etiquettes_triees_par_numero_de_cible() -> None:
    """Les étiquettes suivent l'ordre physique de la salle (cible croissante), même si le
    repository les rend dans le désordre."""
    monde = _monde()
    monde.preparer_cible(3, "CCC333")
    monde.preparer_cible(1, "AAA111")
    monde.preparer_cible(2, "BBB222")

    monde.service.etiquettes_cibles(monde.tournoi_id, _ORIGINE)

    document = monde.generateur.dernieres_cibles
    assert document is not None
    assert [e.cible_index for e in document.etiquettes] == [1, 2, 3]


def test_url_sans_double_slash_si_origine_sans_slash_final() -> None:
    """L'URL reste `…/?poste=<code>` que l'origine se termine ou non par `/` (pas de `//`)."""
    monde = _monde()
    monde.preparer_cible(1, "AAA111")

    monde.service.etiquettes_cibles(monde.tournoi_id, "http://192.168.1.10:8000")

    document = monde.generateur.dernieres_cibles
    assert document is not None
    assert document.etiquettes[0].url == "http://192.168.1.10:8000/?poste=AAA111"


def test_etiquettes_liees_au_tournoi() -> None:
    """« Lié au tournoi » : seuls les postes de ce tournoi figurent."""
    monde = _monde()
    monde.preparer_cible(1, "AAA111")
    # Une cible d'un AUTRE tournoi ne doit pas fuiter dans le document.
    monde.postes.ajouter(Poste.creer(999, 1, "ZZZ999"))

    monde.service.etiquettes_cibles(monde.tournoi_id, _ORIGINE)

    document = monde.generateur.dernieres_cibles
    assert document is not None
    assert [e.code for e in document.etiquettes] == ["AAA111"]


def test_etiquettes_regenerables_a_l_identique() -> None:
    """« Régénérable » : régénérer deux fois donne le même document (codes persistés, stables)."""
    monde = _monde()
    monde.preparer_cible(1, "AAA111")
    monde.preparer_cible(2, "BBB222")

    monde.service.etiquettes_cibles(monde.tournoi_id, _ORIGINE)
    premier = monde.generateur.dernieres_cibles
    monde.service.etiquettes_cibles(monde.tournoi_id, _ORIGINE)
    second = monde.generateur.dernieres_cibles

    assert premier == second


def test_etiquettes_sans_cible_preparee_est_un_document_vide() -> None:
    """Aucune cible préparée : document vide (pas d'erreur) — rien à imprimer n'est pas un échec."""
    monde = _monde()

    monde.service.etiquettes_cibles(monde.tournoi_id, _ORIGINE)

    document = monde.generateur.dernieres_cibles
    assert document is not None
    assert document.etiquettes == ()


def test_etiquettes_tournoi_inconnu_leve_tournoi_introuvable() -> None:
    monde = _monde()
    with pytest.raises(TournoiIntrouvable):
        monde.service.etiquettes_cibles(9999, _ORIGINE)


# --- Cartes de scoreur -------------------------------------------------------------------------


def test_une_carte_par_scoreur_triee_par_nom() -> None:
    """Un papier par scoreur : chaque carte porte son nom et son code, triées par nom."""
    monde = _monde()
    monde.definir_scoreur("Zoé", "ZZZ111")
    monde.definir_scoreur("Alice", "AAA222")

    octets = monde.service.cartes_scoreurs(monde.tournoi_id)

    assert octets == FauxGenerateur.SENTINELLE_SCOREURS
    document = monde.generateur.dernieres_cartes
    assert document is not None
    assert document.nom_tournoi == "Tournoi Test"
    assert [(c.nom, c.code) for c in document.cartes] == [("Alice", "AAA222"), ("Zoé", "ZZZ111")]


def test_cartes_liees_au_tournoi() -> None:
    """« Lié au tournoi » : seuls les scoreurs de ce tournoi figurent."""
    monde = _monde()
    monde.definir_scoreur("Alice", "AAA222")
    monde.scoreurs.ajouter(Scoreur.creer(999, "Autre", "ZZZ999"))

    monde.service.cartes_scoreurs(monde.tournoi_id)

    document = monde.generateur.dernieres_cartes
    assert document is not None
    assert [c.nom for c in document.cartes] == ["Alice"]


def test_cartes_sans_scoreur_est_un_document_vide() -> None:
    monde = _monde()

    monde.service.cartes_scoreurs(monde.tournoi_id)

    document = monde.generateur.dernieres_cartes
    assert document is not None
    assert document.cartes == ()


def test_cartes_tournoi_inconnu_leve_tournoi_introuvable() -> None:
    monde = _monde()
    with pytest.raises(TournoiIntrouvable):
        monde.service.cartes_scoreurs(9999)
