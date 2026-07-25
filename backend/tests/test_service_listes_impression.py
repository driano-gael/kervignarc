"""Tests du service Listes imprimables (E09US003) — dérivés du CA, avant implémentation (règle 9).

Le CA (`stories/E09-exports.md`, E09US003) tient en deux documents vérifiables ici :

- **placement** : « liste archer → cible/position/départ ; triable par cible ou par nom ». On
  vérifie qu'une affectation = une ligne exacte (identité, catégorie, départ, cible, position), les
  deux ordres de tri, le filtre optionnel sur un départ (arbitrage de l'US, cf. Notes), l'absence de
  la réserve, et les gardes 404 (tournoi / départ étranger, même contrat que la feuille de marque) ;
- **club & paiement** : « par club/archer : nom/prénom, n° départ, nb départs, dû, payé/non ; totaux
  par club ». On vérifie le regroupement par club (bucket « Sans club » en dernier, ADR-0014), les
  numéros de départ et leur compte, le dû/payé, le statut de règlement (payé / dû / rien à régler)
  et les totaux du club.

Le rendu PDF est un adapter testé à part (`test_listes_impression_reportlab.py`) : ici un **faux
générateur** capture le contenu composé (`ListePlacement` / `ListeClubPaiement`), seule chose que le
service décide. L'agrégation des paiements n'est **pas** re-testée (c'est E08US002) : on branche le
**vrai** `ServicePaiements` sur des faux repositories, si bien que le contenu part de vraies données
(archers, inscriptions payées ou non, tarifs) — le service sous test ne fait qu'enrichir des numéros
de départ et transposer en contenu imprimable.
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.erreurs import DepartIntrouvable, TournoiIntrouvable
from application.listes_impression import ServiceListesImpression
from application.paiements import ServicePaiements
from domain.archer import Archer
from domain.categorie import Categorie
from domain.club import Club
from domain.depart import Depart
from domain.inscription import Inscription
from domain.listes_impression import (
    ListeClubPaiement,
    ListePlacement,
    StatutPaiement,
    TriPlacement,
)
from domain.placement import Affectation
from domain.tournoi import Tournoi, TournoiId
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxClubRepository,
    FauxDepartRepository,
    FauxInscriptionRepository,
    FauxPlacementRepository,
)

# --- Fakes locaux --------------------------------------------------------------------------------


class FauxTournoiRepository:
    """Repository de tournois en mémoire conforme au port `TournoiRepository`.

    Recopié localement — patron assumé du projet pour ce faux (cf. conftest, doctrine des
    doublures : « recopié dans trois modules, on le laisse »). Seul `par_id` est exercé ici.
    """

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


class FauxHorloge:
    """Horloge figée — le port est exigé par `ServicePaiements`, mais aucune lecture ne le sollicite
    (les vues de paiement sont pures ; seuls les marquages horodatent)."""

    def maintenant(self) -> datetime.datetime:
        return datetime.datetime(2026, 1, 18, 9, 0, tzinfo=datetime.UTC)


class FauxGenerateur:
    """Capture le contenu composé et renvoie des octets sentinelles par document.

    Le service ne connaît que le port (rendre une liste en octets) : ce faux prouve *quel* contenu
    est composé, sans dépendre de ReportLab (adapter testé à part)."""

    SENTINELLE_PLACEMENT = b"%PDF-placement"
    SENTINELLE_CLUB = b"%PDF-club-paiement"

    def __init__(self) -> None:
        self.placement_capture: ListePlacement | None = None
        self.club_capture: ListeClubPaiement | None = None

    def placement(self, liste: ListePlacement) -> bytes:
        self.placement_capture = liste
        return self.SENTINELLE_PLACEMENT

    def club_paiement(self, liste: ListeClubPaiement) -> bytes:
        self.club_capture = liste
        return self.SENTINELLE_CLUB


# --- Décor ---------------------------------------------------------------------------------------


@dataclasses.dataclass
class _Monde:
    service: ServiceListesImpression
    generateur: FauxGenerateur
    tournois: FauxTournoiRepository
    departs: FauxDepartRepository
    clubs: FauxClubRepository
    archers: FauxArcherRepository
    categories: FauxCategorieRepository
    inscriptions: FauxInscriptionRepository
    placements: FauxPlacementRepository
    tournoi_id: int
    categorie_id: int
    departs_par_numero: dict[int, int]  # numéro -> depart_id

    def creer_club(self, nom: str) -> int:
        club = self.clubs.ajouter(Club.creer(nom))
        assert club.id is not None
        return club.id

    def creer_categorie(self, libelle: str) -> int:
        categorie = self.categories.ajouter(Categorie.creer(self.tournoi_id, libelle))
        assert categorie.id is not None
        return categorie.id

    def inscrire(
        self, nom: str, prenom: str, *, numero_depart: int, paye: bool = False, club_id: int | None
    ) -> tuple[int, int]:
        """Crée un archer, l'inscrit sur un départ. Renvoie `(archer_id, inscription_id)`."""
        archer = self.archers.ajouter(
            Archer.creer(nom, prenom, self.tournoi_id, self.categorie_id, club_id=club_id)
        )
        assert archer.id is not None
        inscription = self.inscriptions.ajouter(
            Inscription.creer(archer.id, self.departs_par_numero[numero_depart])
        )
        assert inscription.id is not None
        if paye:
            self.inscriptions._inscriptions[inscription.id] = dataclasses.replace(
                inscription, paye=True
            )
        return archer.id, inscription.id

    def placer(
        self, nom: str, prenom: str, *, numero_depart: int, cible_index: int, position: str
    ) -> None:
        """Inscrit un archer sur un départ **et** le pose sur le plan (cible/position)."""
        _, inscription_id = self.inscrire(nom, prenom, numero_depart=numero_depart, club_id=None)
        self.placements.poser_plusieurs(
            self.departs_par_numero[numero_depart],
            [
                Affectation(
                    inscription_id=inscription_id, cible_index=cible_index, position=position
                )
            ],
        )


def _monde(*, numeros_departs: tuple[int, ...] = (1,), tarif_centimes: int = 800) -> _Monde:
    """Un tournoi peuplé d'une catégorie et de `numeros_departs` créneaux, prêt à recevoir."""
    tournois = FauxTournoiRepository()
    departs = FauxDepartRepository()
    clubs = FauxClubRepository()
    archers = FauxArcherRepository()
    categories = FauxCategorieRepository()
    inscriptions = FauxInscriptionRepository()
    placements = FauxPlacementRepository()
    generateur = FauxGenerateur()

    tournoi = tournois.ajouter(Tournoi.creer("Tournoi Test", datetime.date(2026, 1, 18)))
    assert tournoi.id is not None
    departs_par_numero: dict[int, int] = {}
    for numero in numeros_departs:
        depart = departs.ajouter(
            Depart.creer(tournoi.id, numero=numero, tarif_centimes=tarif_centimes)
        )
        assert depart.id is not None
        departs_par_numero[numero] = depart.id
    categorie = categories.ajouter(Categorie.creer(tournoi.id, "Sénior Homme"))
    assert categorie.id is not None

    paiements = ServicePaiements(tournois, archers, departs, inscriptions, clubs, FauxHorloge())
    service = ServiceListesImpression(
        tournois, departs, placements, inscriptions, archers, categories, paiements, generateur
    )
    return _Monde(
        service=service,
        generateur=generateur,
        tournois=tournois,
        departs=departs,
        clubs=clubs,
        archers=archers,
        categories=categories,
        inscriptions=inscriptions,
        placements=placements,
        tournoi_id=tournoi.id,
        categorie_id=categorie.id,
        departs_par_numero=departs_par_numero,
    )


# --- Placement -----------------------------------------------------------------------------------


def test_placement_conforme_aux_donnees() -> None:
    """Une affectation = une ligne exacte (identité, catégorie, départ, cible, position) ; l'en-tête
    porte le tournoi et, sans filtre, aucun départ (toute la salle)."""
    monde = _monde()
    monde.placer("Durand", "Marie", numero_depart=1, cible_index=1, position="A")

    octets = monde.service.generer_placement(monde.tournoi_id)

    assert octets == FauxGenerateur.SENTINELLE_PLACEMENT
    liste = monde.generateur.placement_capture
    assert liste is not None
    assert liste.tournoi == "Tournoi Test"
    assert liste.depart_numero is None
    assert liste.tri is TriPlacement.CIBLE
    assert len(liste.lignes) == 1
    ligne = liste.lignes[0]
    assert (ligne.nom, ligne.prenom) == ("Durand", "Marie")
    assert ligne.categorie == "Sénior Homme"
    assert (ligne.depart_numero, ligne.cible_index, ligne.position) == (1, 1, "A")


def test_placement_tri_par_cible() -> None:
    """Par défaut : ordre physique de la salle — départ, puis cible, puis position, même si le plan
    est lu dans le désordre."""
    monde = _monde(numeros_departs=(1, 2))
    monde.placer("SurDepart2", "X", numero_depart=2, cible_index=1, position="A")
    monde.placer("Cible2PosA", "Y", numero_depart=1, cible_index=2, position="A")
    monde.placer("Cible1PosB", "Z", numero_depart=1, cible_index=1, position="B")
    monde.placer("Cible1PosA", "W", numero_depart=1, cible_index=1, position="A")

    monde.service.generer_placement(monde.tournoi_id, tri=TriPlacement.CIBLE)

    liste = monde.generateur.placement_capture
    assert liste is not None
    assert [(x.depart_numero, x.cible_index, x.position) for x in liste.lignes] == [
        (1, 1, "A"),
        (1, 1, "B"),
        (1, 2, "A"),
        (2, 1, "A"),
    ]


def test_placement_tri_par_nom() -> None:
    """Tri par nom : ordre alphabétique (nom puis prénom), casse repliée — pour l'accueil."""
    monde = _monde(numeros_departs=(1, 2))
    monde.placer("Zola", "Émile", numero_depart=1, cible_index=1, position="A")
    monde.placer("durand", "Marie", numero_depart=2, cible_index=5, position="C")
    monde.placer("Durand", "Alice", numero_depart=1, cible_index=3, position="B")

    monde.service.generer_placement(monde.tournoi_id, tri=TriPlacement.NOM)

    liste = monde.generateur.placement_capture
    assert liste is not None
    assert liste.tri is TriPlacement.NOM
    assert [(x.nom, x.prenom) for x in liste.lignes] == [
        ("Durand", "Alice"),
        ("durand", "Marie"),
        ("Zola", "Émile"),
    ]


def test_placement_filtre_par_depart() -> None:
    """Le filtre optionnel borne la liste à un seul départ ; l'en-tête porte son numéro."""
    monde = _monde(numeros_departs=(1, 2))
    monde.placer("Depart1", "A", numero_depart=1, cible_index=1, position="A")
    monde.placer("Depart2", "B", numero_depart=2, cible_index=1, position="A")

    monde.service.generer_placement(monde.tournoi_id, depart_id=monde.departs_par_numero[2])

    liste = monde.generateur.placement_capture
    assert liste is not None
    assert liste.depart_numero == 2
    assert [x.nom for x in liste.lignes] == ["Depart2"]


def test_placement_archer_sur_plusieurs_departs_apparait_par_placement() -> None:
    """Un archer placé sur deux départs figure sur **deux** lignes (postes physiques distincts)."""
    monde = _monde(numeros_departs=(1, 2))
    monde.placer("Multi", "Jean", numero_depart=1, cible_index=1, position="A")
    monde.placer("Multi", "Jean", numero_depart=2, cible_index=4, position="D")

    monde.service.generer_placement(monde.tournoi_id)

    liste = monde.generateur.placement_capture
    assert liste is not None
    assert [(x.depart_numero, x.cible_index, x.position) for x in liste.lignes] == [
        (1, 1, "A"),
        (2, 4, "D"),
    ]


def test_placement_reserve_absente() -> None:
    """Un archer inscrit mais non placé (réserve) ne figure pas sur la liste de placement."""
    monde = _monde()
    monde.placer("Place", "Marie", numero_depart=1, cible_index=1, position="A")
    monde.inscrire("Reserve", "Paul", numero_depart=1, club_id=None)

    monde.service.generer_placement(monde.tournoi_id)

    liste = monde.generateur.placement_capture
    assert liste is not None
    assert [x.nom for x in liste.lignes] == ["Place"]


def test_placement_tournoi_inconnu_leve_tournoi_introuvable() -> None:
    monde = _monde()
    with pytest.raises(TournoiIntrouvable):
        monde.service.generer_placement(9999)


def test_placement_depart_d_un_autre_tournoi_leve_depart_introuvable() -> None:
    monde = _monde()
    with pytest.raises(DepartIntrouvable):
        monde.service.generer_placement(monde.tournoi_id, depart_id=9999)


# --- Club & paiement -----------------------------------------------------------------------------


def test_club_paiement_groupe_par_club_avec_totaux() -> None:
    """Les archers sont groupés par club ; le total du club somme dû et payé de ses archers."""
    monde = _monde(tarif_centimes=800)
    arcs = monde.creer_club("Arcs de Test")
    monde.inscrire("Durand", "Marie", numero_depart=1, paye=True, club_id=arcs)
    monde.inscrire("Zola", "Émile", numero_depart=1, paye=False, club_id=arcs)

    monde.service.generer_club_paiement(monde.tournoi_id)

    liste = monde.generateur.club_capture
    assert liste is not None
    assert liste.tournoi == "Tournoi Test"
    assert [g.club for g in liste.groupes] == ["Arcs de Test"]
    groupe = liste.groupes[0]
    assert (groupe.total_du_centimes, groupe.total_paye_centimes) == (1600, 800)
    assert [x.nom for x in groupe.lignes] == ["Durand", "Zola"]


def test_club_paiement_numeros_de_depart_et_compte() -> None:
    """Chaque archer porte les numéros de ses départs (triés) et leur compte (CA n°/nb départs)."""
    monde = _monde(numeros_departs=(1, 2, 3), tarif_centimes=500)
    club = monde.creer_club("Club")
    archer_id, _ = monde.inscrire("Multi", "Jean", numero_depart=3, paye=False, club_id=club)
    # Deuxième inscription du même archer (sur un autre départ) via le repository.
    autre = monde.inscriptions.ajouter(Inscription.creer(archer_id, monde.departs_par_numero[1]))
    assert autre.id is not None

    monde.service.generer_club_paiement(monde.tournoi_id)

    liste = monde.generateur.club_capture
    assert liste is not None
    ligne = liste.groupes[0].lignes[0]
    assert ligne.departs == (1, 3)
    assert ligne.nb_departs == 2
    assert ligne.du_centimes == 1000  # 2 departs a 500


def test_club_paiement_statut_de_reglement() -> None:
    """Statut « payé/non » (CA), avec le 3ᵉ cas honnête « rien à régler » quand le dû est nul."""
    monde = _monde(tarif_centimes=800)
    club = monde.creer_club("Club")
    monde.inscrire("Solde", "Tout", numero_depart=1, paye=True, club_id=club)
    monde.inscrire("Doit", "Encore", numero_depart=1, paye=False, club_id=club)
    # Un archer du club, sans aucune inscription : rien à régler.
    sans_inscription = monde.archers.ajouter(
        Archer.creer("Sans", "Inscription", monde.tournoi_id, monde.categorie_id, club_id=club)
    )
    assert sans_inscription.id is not None

    monde.service.generer_club_paiement(monde.tournoi_id)

    liste = monde.generateur.club_capture
    assert liste is not None
    statuts = {x.nom: x.statut for x in liste.groupes[0].lignes}
    assert statuts == {
        "Solde": StatutPaiement.PAYE,
        "Doit": StatutPaiement.DU,
        "Sans": StatutPaiement.RIEN,
    }


def test_club_paiement_sans_club_en_dernier() -> None:
    """Les archers sans club (ADR-0014) forment un bucket « Sans club » placé en dernier."""
    monde = _monde()
    club = monde.creer_club("Arcs de Test")
    monde.inscrire("AvecClub", "A", numero_depart=1, club_id=club)
    monde.inscrire("SansClub", "B", numero_depart=1, club_id=None)

    monde.service.generer_club_paiement(monde.tournoi_id)

    liste = monde.generateur.club_capture
    assert liste is not None
    assert [g.club for g in liste.groupes] == ["Arcs de Test", "Sans club"]
    assert [x.nom for x in liste.groupes[-1].lignes] == ["SansClub"]


def test_club_paiement_tournoi_inconnu_leve_tournoi_introuvable() -> None:
    monde = _monde()
    with pytest.raises(TournoiIntrouvable):
        monde.service.generer_club_paiement(9999)
