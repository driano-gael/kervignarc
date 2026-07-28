"""Service applicatif Jeu d'essai — peupler un tournoi & instancier des scénarios (E15US001).

Outil de **démo et de QA** (retours de la démo du 27/07/2026) : peupler un tournoi d'inscrits
réalistes sans saisie manuelle, ou instancier d'un coup un tournoi complet **prêt à lancer** depuis
un **catalogue de scénarios**. C'est de la **donnée réelle persistée** — un tournoi de test qu'on
assume comme tel — **à distinguer** de la simulation *éphémère* (E15US002), qui ne persiste rien.

**Réutilisation des services, pas de court-circuit du domaine.** Ce service n'écrit rien lui-même :
il **orchestre** les cas d'usage existants (`ServiceTournois`, `ServiceCategories`,
`ServiceDeparts`, `ServiceArchers`, `ServiceInscriptions`, `ServiceClubs`) — même patron que
`ServicePlacementDuels`, qui compose `ServiceClassement`. Toute la validation métier (catégorie,
unicité d'inscription…) et l'audit passent donc par les chemins normaux. La commande de file qui
appelle `peupler`/`instancier` enchaîne ainsi plusieurs écritures (une par service appelé), comme
`ServiceCategories.precharger_ffta` le fait déjà (règle 7 : le writer unique sérialise le tout ;
l'atomicité de bout en bout n'est pas requise — c'est un tournoi de test, règle 12).

**Déterminisme (règle 9).** La génération est pilotée par un `random.Random(graine)` construit à
partir d'une **graine explicite** : à graine égale (et catalogue de catégories égal), les mêmes
noms, clubs et catégories sont produits — le scénario est *rejouable*. Les identifiants de base
(auto-incrément) ne font pas partie de cette reproductibilité : ils croissent avec la base ; ce qui
est déterministe, ce sont les **données saisies** (nom, prénom, catégorie), pas leur `id` technique.
"""

from __future__ import annotations

import datetime
import random
from collections.abc import Callable
from dataclasses import dataclass

from application.archers import ServiceArchers
from application.categories import ServiceCategories
from application.clubs import ServiceClubs
from application.departs import ServiceDeparts
from application.erreurs import PeuplementTournoiDemarre, ScenarioInconnu
from application.inscriptions import ServiceInscriptions
from application.referentiel_ffta import ARC_CLASSIQUE, ARC_NU, ARC_POULIES
from application.tournois import ServiceTournois
from domain.archer import Archer
from domain.categorie import Categorie, TrancheAge
from domain.club import cle_nom
from domain.tournoi import StatutTournoi, TournoiId

# Statuts où peupler de la donnée de test est permis : **avant démarrage** seulement. Au-delà, le
# tournoi est une compétition vivante ou figée — on n'y injecte pas d'inscrits factices (EPIC-15,
# « ne pollue jamais le réel »).
_STATUTS_PEUPLABLES = frozenset({StatutTournoi.BROUILLON, StatutTournoi.PRET})

_GRAINE_DEFAUT = 0
"""Graine par défaut : un jeu **stable et rejouable** tant que l'appelant n'en fournit pas d'autre.

Fixe (jamais l'horloge, règle 9) : deux appels sans graine produisent le même jeu — ce qui, sur une
même base, crée des homonymes (assumé : `autoriser_homonyme=True`, ce sont des données de test)."""

# Vivier de noms/prénoms/clubs **plausibles** (français), volontairement modeste : on veut du
# réalisme de lecture (une liste crédible à l'écran), pas un annuaire. La répétition des noms
# au-delà de la taille du vivier est assumée (homonymes de test). Aucune donnée réelle : noms
# courants et clubs fictifs bâtis sur des villes.
_PRENOMS: tuple[str, ...] = (
    "Camille",
    "Lucas",
    "Emma",
    "Hugo",
    "Léa",
    "Nathan",
    "Chloé",
    "Louis",
    "Manon",
    "Gabriel",
    "Sarah",
    "Jules",
    "Inès",
    "Arthur",
    "Zoé",
    "Paul",
    "Jade",
    "Tom",
    "Louise",
    "Raphaël",
    "Alice",
    "Ethan",
    "Lina",
    "Noah",
    "Anna",
    "Théo",
    "Rose",
    "Sacha",
    "Julie",
    "Maxime",
    "Clara",
    "Antoine",
    "Éva",
    "Baptiste",
    "Nora",
    "Adam",
    "Mila",
    "Victor",
    "Lou",
    "Enzo",
)
_NOMS: tuple[str, ...] = (
    "Martin",
    "Bernard",
    "Thomas",
    "Petit",
    "Robert",
    "Richard",
    "Durand",
    "Dubois",
    "Moreau",
    "Laurent",
    "Simon",
    "Michel",
    "Lefebvre",
    "Leroy",
    "Roux",
    "David",
    "Bertrand",
    "Morel",
    "Fournier",
    "Girard",
    "Bonnet",
    "Dupont",
    "Lambert",
    "Fontaine",
    "Rousseau",
    "Vincent",
    "Muller",
    "Lefevre",
    "Faure",
    "Andre",
    "Mercier",
    "Blanc",
    "Guerin",
    "Boyer",
    "Garnier",
    "Chevalier",
    "Francois",
    "Legrand",
    "Gauthier",
    "Garcia",
)
_CLUBS: tuple[str, ...] = (
    "Compagnie d'arc de Rennes",
    "Les Archers de Vannes",
    "Arc Club Quimper",
    "Compagnie de Lorient",
    "Les Archers de Saint-Malo",
    "Arc Nature Brocéliande",
    "Compagnie de Fougères",
    "Les Archers de Redon",
    "Arc Club Dinan",
    "Compagnie de Pontivy",
)

# Un archer sur ~huit reste **sans club** (club « inconnu », ADR-0014) : ça alimente le bucket
# « Sans club » du suivi des paiements (E08US002), utile à tester. Le tirage passe par le
# `random.Random` injecté, donc reste déterministe.
_PROBA_SANS_CLUB = 0.12

# Créneaux et tarif fixes d'un scénario : trois horaires suffisent (aucun scénario ne dépasse 3
# départs). Données de test, volontairement simples (règle 12).
_HORAIRES: tuple[str, ...] = ("09:00", "10:30", "14:00")
_TARIF_CENTIMES = 1000


@dataclass(frozen=True)
class Scenario:
    """Un scénario rejouable du catalogue : de quoi instancier un tournoi de test complet.

    `filtre_categorie` sélectionne, **parmi les catégories du tournoi**, celles où puiser les
    archers — un prédicat **interne** (jamais exposé à l'API : seuls `id`, `libelle`, `description`
    et les compteurs le sont). Il permet de concentrer un petit tournoi sur peu de catégories (duels
    jouables tout de suite) ou d'étaler un gros tournoi sur toute une division.
    """

    id: str
    libelle: str
    description: str
    nombre_archers: int
    nombre_departs: int
    filtre_categorie: Callable[[Categorie], bool]


def _est_senior(categorie: Categorie) -> bool:
    """Vrai si la catégorie couvre au moins une tranche **sénior** (S1/S2/S3).

    Sert le scénario « petit » : concentrer les inscrits sur les catégories adultes d'arc classique
    donne assez d'archers par catégorie pour un vrai tableau de duels, là où étaler 16 archers sur
    les 16 catégories classiques n'en laisserait qu'un par catégorie (aucun duel possible)."""
    return bool({TrancheAge.S1, TrancheAge.S2, TrancheAge.S3} & set(categorie.ages))


# Catalogue **figé** des scénarios (arbitré au cadrage de l'US). Trois profils complémentaires :
# petit (démo rapide d'un tableau), gros (charge du placement), multi-format (cohabitation des
# armes).
CATALOGUE: tuple[Scenario, ...] = (
    Scenario(
        id="petit",
        libelle="Petit tournoi",
        description=(
            "Une poignée d'archers en arc classique sénior, un seul créneau — pour tester vite "
            "un tableau de duels."
        ),
        nombre_archers=16,
        nombre_departs=1,
        filtre_categorie=lambda c: c.arme == ARC_CLASSIQUE and _est_senior(c),
    ),
    Scenario(
        id="gros",
        libelle="Gros tournoi",
        description=(
            "Beaucoup d'archers en arc classique sur plusieurs créneaux — pour tester le placement "
            "et la charge."
        ),
        nombre_archers=120,
        nombre_departs=3,
        filtre_categorie=lambda c: c.arme == ARC_CLASSIQUE,
    ),
    Scenario(
        id="multi-format",
        libelle="Multi-format",
        description=(
            "Les trois types d'arc mêlés (classique, poulies, arc nu) sur deux créneaux — pour "
            "tester la cohabitation des formats."
        ),
        nombre_archers=60,
        nombre_departs=2,
        filtre_categorie=lambda c: c.arme in (ARC_CLASSIQUE, ARC_POULIES, ARC_NU),
    ),
)


@dataclass(frozen=True)
class ResultatJeuEssai:
    """Ce qu'un scénario a instancié : le tournoi créé et ce qu'il porte (écran & tests)."""

    tournoi_id: TournoiId
    nom: str
    nombre_archers: int
    nombre_departs: int


class ServiceJeuEssai:
    """Cas d'usage du jeu d'essai : peupler un tournoi, instancier un scénario, lister le catalogue.

    Aucun accès direct aux repositories — tout passe par les services applicatifs injectés."""

    def __init__(
        self,
        tournois: ServiceTournois,
        categories: ServiceCategories,
        departs: ServiceDeparts,
        archers: ServiceArchers,
        inscriptions: ServiceInscriptions,
        clubs: ServiceClubs,
    ) -> None:
        self._tournois = tournois
        self._categories = categories
        self._departs = departs
        self._archers = archers
        self._inscriptions = inscriptions
        self._clubs = clubs

    def scenarios(self) -> list[Scenario]:
        """Le catalogue de scénarios rejouables (lecture pure, pour l'écran de sélection)."""
        return list(CATALOGUE)

    def peupler(
        self,
        tournoi_id: TournoiId,
        nombre: int,
        graine: int = _GRAINE_DEFAUT,
        filtre_categorie: Callable[[Categorie], bool] | None = None,
    ) -> list[Archer]:
        """Peuple un tournoi **existant** de `nombre` archers de test plausibles (E15US001).

        Les archers sont répartis sur les catégories du tournoi (celles retenues par
        `filtre_categorie`, ou toutes). Si le tournoi n'a **aucune** catégorie, le jeu FFTA est
        pré-chargé au passage (`precharger_ffta`, idempotent) — sinon on puise dans les catégories
        déjà définies, sans en ajouter.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas, `PeuplementTournoiDemarre` (→ 409)
        s'il est **déjà démarré** (hors `brouillon`/`prêt`) — on ne pollue pas une compétition
        vivante avec des inscrits de test. Génération **déterministe** pour une `graine` (règle 9).
        Chaque archer est ajouté via `ServiceArchers.ajouter(..., autoriser_homonyme=True)` — les
        noms tirés au hasard peuvent se répéter, deux homonymes de test n'interrompent pas le lot.
        """
        self._exiger_tournoi_peuplable(tournoi_id)
        alea = random.Random(graine)
        categories = self._categories_cibles(tournoi_id, filtre_categorie)
        clubs_ids = self._garantir_clubs()
        archers: list[Archer] = []
        for _ in range(nombre):
            prenom = alea.choice(_PRENOMS)
            nom = alea.choice(_NOMS)
            categorie = alea.choice(categories)
            club_id = None if alea.random() < _PROBA_SANS_CLUB else alea.choice(clubs_ids)
            assert categorie.id is not None, "Une catégorie relue est persistée."
            archer = self._archers.ajouter(
                tournoi_id, nom, prenom, categorie.id, club_id, autoriser_homonyme=True
            )
            archers.append(archer)
        return archers

    def instancier(
        self,
        scenario_id: str,
        date: datetime.date,
        graine: int = _GRAINE_DEFAUT,
    ) -> ResultatJeuEssai:
        """Instancie un scénario du catalogue : un tournoi **brouillon complet, prêt à lancer**.

        Crée le tournoi, pré-charge les catégories FFTA, ajoute ses créneaux, peuple ses archers et
        les **inscrit** (répartis en tourniquet sur les créneaux). Le tournoi obtenu a au moins un
        départ : il peut donc passer `prêt` puis démarrer (garde `TournoiSansDepart`, E02US010).

        Lève `ScenarioInconnu` si l'identifiant ne correspond à aucun scénario du catalogue. `date`
        est fournie par l'appelant (l'API la lit sur l'horloge ; les tests la fixent) : le service
        ne lit pas l'horloge lui-même, pour rester déterministe (règle 9).
        """
        scenario = _scenario_par_id(scenario_id)
        # Invariant du catalogue figé : 1 ≤ départs ≤ nombre d'horaires disponibles. Un scénario
        # ajouté avec 0 départ (tourniquet → division par zéro) ou trop de départs (`_HORAIRES` trop
        # court → IndexError) doit échouer **au test**, pas silencieusement en production.
        assert 1 <= scenario.nombre_departs <= len(_HORAIRES), "Départs du scénario hors bornes."
        tournoi = self._tournois.creer(f"{scenario.libelle} (jeu d'essai)", date)
        assert tournoi.id is not None, "Un tournoi créé est persisté."
        self._categories.precharger_ffta(tournoi.id)
        departs = [
            self._departs.creer(tournoi.id, _TARIF_CENTIMES, _HORAIRES[k])
            for k in range(scenario.nombre_departs)
        ]
        archers = self.peupler(
            tournoi.id, scenario.nombre_archers, graine, scenario.filtre_categorie
        )
        for index, archer in enumerate(archers):
            depart = departs[index % len(departs)]
            assert archer.id is not None and depart.id is not None, "Entités persistées."
            self._inscriptions.inscrire(archer.id, depart.id)
        return ResultatJeuEssai(
            tournoi_id=tournoi.id,
            nom=tournoi.nom,
            nombre_archers=len(archers),
            nombre_departs=len(departs),
        )

    def _exiger_tournoi_peuplable(self, tournoi_id: TournoiId) -> None:
        """Lève `TournoiIntrouvable` si inconnu, `PeuplementTournoiDemarre` si déjà démarré.

        `ServiceTournois.consulter` porte le refus « tournoi inconnu » ; on ne borne qu'ensuite sur
        le statut, pour ne peupler qu'un tournoi **avant démarrage** (`_STATUTS_PEUPLABLES`)."""
        tournoi = self._tournois.consulter(tournoi_id)
        if tournoi.statut not in _STATUTS_PEUPLABLES:
            raise PeuplementTournoiDemarre(
                f"Le tournoi « {tournoi.nom} » est {tournoi.statut.value} : on ne peuple d'archers "
                "de test qu'un tournoi avant démarrage (brouillon ou prêt), pour ne pas polluer "
                "une compétition. Créez un tournoi de test, ou instanciez un scénario."
            )

    def _categories_cibles(
        self, tournoi_id: TournoiId, filtre: Callable[[Categorie], bool] | None
    ) -> list[Categorie]:
        """Catégories où puiser les archers, triées par libellé (ordre **stable**, déterminisme).

        Pré-charge le jeu FFTA si le tournoi n'a aucune catégorie. Applique `filtre` s'il est
        fourni ; si le filtre ne retient rien (catégories définies, aucune ne correspond), on
        **retombe**
        sur toutes les catégories du tournoi plutôt que de ne rien pouvoir générer.
        """
        categories = self._categories.lister(tournoi_id)
        if not categories:
            self._categories.precharger_ffta(tournoi_id)
            categories = self._categories.lister(tournoi_id)
        retenues = [c for c in categories if filtre is None or filtre(c)]
        if not retenues:
            retenues = categories
        # Tri par libellé : rend l'ordre indépendant de celui que renvoie le repository, donc le
        # tirage `alea.choice` **reproductible** d'une base à l'autre (règle 9).
        return sorted(retenues, key=lambda c: c.libelle)

    def _garantir_clubs(self) -> list[int]:
        """Garantit que le vivier de clubs existe dans le référentiel et renvoie leurs identifiants.

        Le référentiel des clubs est **global** (E02US001) : on réutilise un club de même nom s'il
        existe déjà (comparaison `cle_nom`, comme le service), on ne crée que les manquants — le
        peuplement reste rejouable sans doublonner le référentiel."""
        existants = {cle_nom(club.nom): club for club in self._clubs.lister()}
        ids: list[int] = []
        for nom in _CLUBS:
            club = existants.get(cle_nom(nom))
            if club is None:
                club = self._clubs.creer(nom)
                existants[cle_nom(nom)] = club
            assert club.id is not None, "Un club créé/relu est persisté."
            ids.append(club.id)
        return ids


def _scenario_par_id(scenario_id: str) -> Scenario:
    """Résout un scénario du catalogue par son `id`, ou lève `ScenarioInconnu` (→ 404)."""
    for scenario in CATALOGUE:
        if scenario.id == scenario_id:
            return scenario
    raise ScenarioInconnu(f"Aucun scénario de jeu d'essai nommé « {scenario_id} ».")
