"""E05US027 — le service de la **colline** : les manches s'enchaînent, le gagnant monte.

Tests dérivés du **CA** (`stories/E05-moteur-phases.md` → E05US027), écrits **avant**
l'implémentation du service : ce qu'ils décrivent est la règle voulue, pas le code livré (règle 9).

Les puces éprouvées ici :

- « **habiter le contrat de phase jouable**, mêmes termes qu'E05US026 » ;
- « **réglages à l'atelier** : portée de défi et nombre de manches (`ConfigurationColline`) » ;
- « **les manches s'enchaînent** et le classement se lit de l'ordre final de la colline ».

⚠️ **Le décor discriminant.** Quatre archers classés 1-2-3-4. La manche 1 d'une colline à portée 1
oppose les voisins — (1,2) et (3,4) — et l'on fait gagner les **challengers** (position basse) dans
les deux cas : la colline devient `2 1 4 3`. La manche 2 décale d'un cran et n'apparie que les
positions 2 et 3, soit **l'archer 1 contre l'archer 4** — ordre qu'aucune lecture du classement
amont ne produirait, et qu'un service oubliant d'appliquer les issues ne produirait pas non plus
(il rendrait à nouveau (1,2) et (3,4), ou (2,3) sur la colline d'origine). C'est ce qui rend ces
tests capables d'échouer.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

import pytest

from application.classements import ServiceClassement
from application.colline import ServiceColline
from application.erreurs import PhaseEnPause, PhasePasReglee, PhasePasUneColline
from application.saisie_duels import ServiceSaisieDuels
from domain.archer import Archer
from domain.bareme import BaremeQualification
from domain.blason import Blason, ZoneScore
from domain.categorie import Categorie
from domain.colline import ConfigurationColline
from domain.depart import Depart
from domain.duel import ResolveurBaremeDuelFfta
from domain.gabarit_salle import GabaritSalle
from domain.inscription import Inscription
from domain.phase import Phase, PhaseId, StatutPhase, TypePhase
from domain.placement_par_bloc import BlocDeCouloirs
from domain.politiques import (
    AggregationParQualification,
    ByesAuxMieuxClasses,
    PlacementEnCascade,
    SeedingSerpent,
    registre_par_defaut,
)
from domain.tournoi import TournoiId
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxDepartRepository,
    FauxDuelRepository,
    FauxForfaitRepository,
    FauxInscriptionRepository,
    FauxPhaseRepository,
)
from tests.test_service_placement_duels import (
    FauxBlasonRepository,
    FauxSerieRepository,
    FauxTournoiRepository,
)
from tests.test_service_saisie_duels import ZONES_TRIPLE


class _FauxPlacementParBlocRepository:
    """Double du port `PlacementParBlocRepository` — deux gestes, comme le port.

    ⚠️ **Typé sur le port, sans `# type: ignore`** (correctif de revue, axe A). Les deux jumeaux
    (`test_service_suisse.py`, `test_service_poules.py`) typent leurs doubles en `object` et
    réduisent au silence les erreurs qui en découlent. Ça marche, et c'est précisément le problème :
    ce que mypy cesse alors de prouver, c'est que **le double satisfait le port** — or c'est la
    seule
    chose qu'un double de port doit garantir. Le jour où `PlacementParBlocRepository` change de
    signature, un double typé `object` continue de compiler contre l'ancienne, et les tests restent
    verts sur un service qui ne pourrait plus tourner en production.

    Un outil contourné n'est jamais « vert » : ici il n'y avait pas à le contourner, les vrais types
    marchent tels quels. Les deux jumeaux sont **hérités** et ne sont pas rouverts par cette US.
    """

    def __init__(self) -> None:
        self._plans: dict[PhaseId, list[BlocDeCouloirs]] = {}

    def par_phase(self, phase_id: PhaseId) -> list[BlocDeCouloirs]:
        return list(self._plans.get(phase_id, []))

    def definir_plan(self, phase_id: PhaseId, blocs: Sequence[BlocDeCouloirs]) -> None:
        self._plans[phase_id] = list(blocs)


class _FauxGabaritRepository:
    """Double de `GabaritSalleRepository` : une salle homogène de `nb_cibles` sur `couloirs`."""

    def __init__(self, nb_cibles: int = 8, couloirs: int = 4) -> None:
        self._gabarit = GabaritSalle.creer("Salle", nb_cibles=nb_cibles, capacite=couloirs)

    def par_tournoi(self, tournoi_id: TournoiId) -> GabaritSalle | None:
        return self._gabarit


class _Monde:
    """Décor : un tournoi, un créneau, N archers classés, une phase de **colline**.

    Les archers reçoivent des scores décroissants dans l'ordre de création → rang scratch 1..N,
    donc l'ordre initial de la colline est celui de leur création.
    """

    def __init__(self) -> None:
        self.tournoi_id = 1
        self.tournois = FauxTournoiRepository({1})
        self.departs = FauxDepartRepository()
        depart = self.departs.ajouter(
            Depart.creer(tournoi_id=self.tournoi_id, numero=1, tarif_centimes=800, horaire="09:00")
        )
        assert depart.id is not None
        self.depart_id = depart.id
        self.inscriptions = FauxInscriptionRepository()
        self.phases = FauxPhaseRepository(self.departs)
        self.archers = FauxArcherRepository()
        self.categories = FauxCategorieRepository()
        self.blasons = FauxBlasonRepository()
        self.series = FauxSerieRepository()
        self.duels = FauxDuelRepository()
        self.forfaits = FauxForfaitRepository()
        self.placements = _FauxPlacementParBlocRepository()
        self.gabarits = _FauxGabaritRepository()
        blason = self.blasons.ajouter(
            Blason.creer(self.tournoi_id, "Triple", taille=0.25, capacite=1)
        )
        assert blason.id is not None
        self.blasons._blasons[blason.id] = replace(blason, zones=ZONES_TRIPLE)
        categorie = self.categories.ajouter(
            Categorie.creer(
                self.tournoi_id, "Cat", arme="Arc Classique", blason_id=blason.id, hauteur_cm=130
            )
        )
        assert categorie.id is not None
        self.categorie_id = categorie.id
        qualif = self.phases.ajouter(
            Phase.qualification(self.depart_id, BaremeQualification.creer(1, 3))
        )
        assert qualif.id is not None
        self.qualif_id = qualif.id
        self.phase_id = 0

    def regler(
        self, reglage: ConfigurationColline | None, type_phase: TypePhase = TypePhase.COLLINE
    ) -> int:
        """Pose la phase de colline avec son réglage (ou sans, pour éprouver le refus)."""
        phase = self.phases.ajouter(
            Phase(depart_id=self.depart_id, ordre=2, type=type_phase, colline=reglage)
        )
        assert phase.id is not None
        self.phase_id = phase.id
        return phase.id

    def inscrire(self, combien: int) -> list[int]:
        """Inscrit `combien` archers, classés par scores décroissants (rang 1 = le premier créé)."""
        ids: list[int] = []
        for rang in range(combien):
            archer = self.archers.ajouter(
                Archer(
                    nom=f"N{rang}",
                    prenom="P",
                    tournoi_id=self.tournoi_id,
                    categorie_id=self.categorie_id,
                )
            )
            assert archer.id is not None
            valeur = str(max(1, 10 - rang))
            self.series.semer(
                self.tournoi_id,
                archer.id,
                (ZoneScore(valeur), ZoneScore(valeur), ZoneScore(valeur)),
                self.qualif_id,
            )
            self.inscriptions.ajouter(Inscription.creer(archer.id, self.depart_id))
            ids.append(archer.id)
        return ids

    def service(self) -> ServiceColline:
        classement = ServiceClassement(
            self.tournois,
            self.archers,
            self.series,
            self.categories,
            self.phases,
            self.forfaits,
            self.departs,
            self.inscriptions,
        )
        saisie = ServiceSaisieDuels(
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
            registre_par_defaut(),
            AggregationParQualification(),
        )
        return ServiceColline(
            self.tournois,
            self.phases,
            # ⚠️ **Cet `ignore`-ci reste, et il est le SEUL des trois** (arbitrage de revue) :
            # `_FauxGabaritRepository` est délibérément **partiel** — il sert une méthode sur les
            # six
            # du port, parce que `ServiceColline` n'en consomme qu'une. Le compléter serait cinq
            # stubs de bruit. Les deux autres `ignore` (le double de plan par blocs) ont été retirés
            # :
            # là, les vrais types du port marchaient tels quels, et ce que mypy cessait de prouver
            # était justement que le double satisfait le port.
            self.gabarits,  # type: ignore[arg-type]
            self.placements,
            self.duels,
            classement,
            saisie,
        )


def _gagner(service: ServiceColline, monde: _Monde, numero: int, *, le_bas: bool) -> None:
    """Fait gagner un camp d'un défi, puis **valide** — c'est la validation qui compte.

    Le camp « bas » est le **challenger** (celui qui défie depuis la position la plus basse) ; le
    camp « haut » est le défié. Trois manches gagnées d'affilée closent le duel en sets.
    """
    fort = (ZoneScore("10"),) * 3
    faible = (ZoneScore("6"),) * 3
    for manche in (1, 2, 3):
        service.saisir_manche(
            monde.tournoi_id,
            monde.phase_id,
            numero,
            manche,
            faible if le_bas else fort,
            fort if le_bas else faible,
        )
    service.valider(monde.tournoi_id, monde.phase_id, numero, "scoreur")


def _jouer_la_manche_ouverte(service: ServiceColline, monde: _Monde) -> None:
    """Clôt la première manche non close, quels que soient les numéros de ses défis.

    ⚠️ **Les numéros ne se devinent pas d'une manche à l'autre** : à portée 1 et à 4 archers, la
    manche 1 apparie deux défis et la manche 2 un seul (les extrémités se reposent). Un test qui
    rejouerait « le défi 1 puis le défi 2 » à chaque manche taperait donc à côté — c'est exactement
    le régime ordinaire du format, pas un cas limite.
    """
    etat = service.etat(monde.tournoi_id, monde.phase_id)
    ouverte = next(manche for manche in etat.manches if not manche.close)
    for defi in ouverte.defis:
        _gagner(service, monde, defi.numero, le_bas=True)


def _manches(service: ServiceColline, monde: _Monde) -> tuple[tuple[tuple[int, int], ...], ...]:
    """Les manches appariées, chacune comme un tuple de couples (défié, challenger)."""
    etat = service.etat(monde.tournoi_id, monde.phase_id)
    return tuple(
        tuple(
            (defi.haut.archer_id, defi.bas.archer_id)
            for defi in manche.defis
            if defi.haut is not None and defi.bas is not None
        )
        for manche in etat.manches
    )


def _ordre(service: ServiceColline, monde: _Monde) -> list[int]:
    """L'ordre courant de la colline, position par position."""
    etat = service.etat(monde.tournoi_id, monde.phase_id)
    return [rang.duelliste.archer_id for rang in etat.classement]


# --- CA « les manches s'enchaînent » --------------------------------------------------------------


def test_la_premiere_manche_oppose_les_voisins() -> None:
    """L'ouverture d'un King of the Hill : (1,2) et (3,4), pas (1,4).

    C'est la mécanique retenue au cadrage du 31/07/2026 — « deux voisins s'affrontent » plutôt que
    « tous défient le King » — parce qu'elle fait tirer tout le monde à chaque manche. L'ordre
    initial est le classement amont (référentiel §10.1, « version de journée »).
    """
    monde = _Monde()
    archers = monde.inscrire(4)
    monde.regler(ConfigurationColline(nb_manches=3, portee_de_defi=1))

    manches = _manches(monde.service(), monde)

    assert manches[0] == ((archers[0], archers[1]), (archers[2], archers[3]))


def test_le_gagnant_monte_et_le_perdant_descend() -> None:
    """**Le CA de l'US**, versant ordre : un challenger qui l'emporte prend la place du défié.

    Les deux challengers gagnent la manche 1, donc la colline `1 2 3 4` devient `2 1 4 3`. Un
    service qui n'appliquerait pas les issues laisserait `1 2 3 4`.
    """
    monde = _Monde()
    archers = monde.inscrire(4)
    monde.regler(ConfigurationColline(nb_manches=3, portee_de_defi=1))
    service = monde.service()

    _gagner(service, monde, 1, le_bas=True)
    _gagner(service, monde, 2, le_bas=True)

    assert _ordre(service, monde) == [archers[1], archers[0], archers[3], archers[2]]


def test_la_manche_suivante_apparie_sur_l_ordre_issu_de_la_precedente() -> None:
    """**Le CA de l'US**, versant enchaînement : la manche 2 se calcule de la colline mise à jour.

    Après `2 1 4 3`, la manche 2 décale d'un cran et n'apparie que les positions 2 et 3 — soit
    **l'archer 1 contre l'archer 4**. Aucune lecture du classement amont ne produit ce couple, et
    un service qui n'aurait pas appliqué la manche 1 apparierait 2 contre 3.

    ⚠️ Les extrémités se **reposent** une manche sur deux à portée 1 : c'est inévitable et sans
    effet sur le classement, puisqu'elles rejouent la manche suivante.
    """
    monde = _Monde()
    archers = monde.inscrire(4)
    monde.regler(ConfigurationColline(nb_manches=3, portee_de_defi=1))
    service = monde.service()

    _gagner(service, monde, 1, le_bas=True)
    _gagner(service, monde, 2, le_bas=True)

    manches = _manches(service, monde)

    assert len(manches) == 2
    assert manches[1] == ((archers[0], archers[3]),)


def test_une_manche_partiellement_saisie_n_apparie_pas_la_suivante() -> None:
    """L'appariement de la manche suivante dépend de l'ordre, donc de **toutes** les issues.

    Une manche se saisit cible par cible : l'état « en cours » est le régime **normal** du jour J.
    Apparier par-dessus ferait bouger les défis sous les yeux du juge, puisque chaque validation
    manquante peut encore changer l'ordre. Le service s'arrête donc, et l'état **dit** que la
    manche est ouverte — c'est ce qui permet à l'écran de nommer l'attente.
    """
    monde = _Monde()
    monde.inscrire(4)
    monde.regler(ConfigurationColline(nb_manches=3, portee_de_defi=1))
    service = monde.service()

    _gagner(service, monde, 1, le_bas=True)  # un seul des deux défis

    etat = service.etat(monde.tournoi_id, monde.phase_id)

    assert len(etat.manches) == 1
    assert etat.manches[0].close is False


def test_un_tir_non_valide_ne_clot_pas_la_manche() -> None:
    """Seuls les duels **validés** comptent — sinon l'ordre bougerait à chaque flèche.

    Même règle que la reconstruction d'un tableau, des poules et du suisse.
    """
    monde = _Monde()
    monde.inscrire(4)
    monde.regler(ConfigurationColline(nb_manches=3, portee_de_defi=1))
    service = monde.service()

    fort = (ZoneScore("10"),) * 3
    faible = (ZoneScore("6"),) * 3
    for numero in (1, 2):
        for manche in (1, 2, 3):
            service.saisir_manche(monde.tournoi_id, monde.phase_id, numero, manche, faible, fort)

    etat = service.etat(monde.tournoi_id, monde.phase_id)

    assert etat.manches[0].close is False


# --- CA « réglages à l'atelier » ------------------------------------------------------------------


def test_la_portee_de_defi_change_les_appariements() -> None:
    """**Le CA « portée de défi »** : c'est le seul réglage qui sépare Ladder et King of the Hill.

    Les défiés gagnent la manche 1, donc la colline reste `1 2 3 4` dans les deux cas — ce qui
    isole l'effet de la portée. La manche 2 d'un King of the Hill (portée 1) décale d'un cran et
    apparie les positions 2 et 3 ; celle d'un Ladder (portée 2) passe à la distance 2 et apparie
    les positions 1 et 3.

    ⚠️ **La distance tourne d'une manche à l'autre**, elle n'est pas figée à la portée : « le n°6
    peut défier le 5 **ou** le 4 » énonce un choix, pas une distance exacte. Figer la distance à 2
    ferait de la parité des positions un invariant, et la colline se scinderait en deux moitiés
    étanches — l'archer parti en position 2 n'atteindrait jamais la position 1.
    """
    resultats: dict[int, tuple[tuple[tuple[int, int], ...], list[int]]] = {}
    for portee in (1, 2):
        monde = _Monde()
        archers = monde.inscrire(4)
        monde.regler(ConfigurationColline(nb_manches=3, portee_de_defi=portee))
        service = monde.service()
        _gagner(service, monde, 1, le_bas=False)
        _gagner(service, monde, 2, le_bas=False)
        resultats[portee] = (_manches(service, monde)[1], archers)

    king, archers = resultats[1]
    ladder, _ = resultats[2]
    assert king == ((archers[1], archers[2]),)
    assert ladder == ((archers[0], archers[2]),)


def test_une_phase_sans_reglage_refuse_de_se_lire() -> None:
    """Le type se choisit avant ses paramètres : une colline non réglée est un 409, pas un 500.

    L'atelier doit pouvoir enregistrer un déroulé en cours de composition ; c'est la lecture du
    jour J qui exige le réglage.
    """
    monde = _Monde()
    monde.inscrire(4)
    monde.regler(None)
    service = monde.service()

    with pytest.raises(PhasePasReglee):
        service.etat(monde.tournoi_id, monde.phase_id)


def test_une_phase_d_un_autre_type_est_refusee() -> None:
    """Le service ne lit que des collines — lire un tableau par cette porte serait un contresens."""
    monde = _Monde()
    monde.inscrire(4)
    monde.regler(None, type_phase=TypePhase.ELIMINATION_DIRECTE)
    service = monde.service()

    with pytest.raises(PhasePasUneColline):
        service.etat(monde.tournoi_id, monde.phase_id)


def test_une_portee_superieure_a_l_effectif_est_bornee_et_non_levee() -> None:
    """Un écran qui refuse de s'ouvrir vaut moins qu'un écran qui montre la borne.

    ⚠️ C'est la leçon du suisse, où l'inverse a été un **bloquant de revue reproduit par trois
    axes** : le domaine refuse une portée ≥ à l'effectif (« ce n'est plus ni un King of the Hill ni
    un Ladder »), mais l'effectif du jour n'est pas connu quand un format de bibliothèque s'écrit.
    Lever à la lecture ferait sortir en 422 le palmarès public, son PDF et le panneau de routage
    d'une phase que l'atelier a pourtant acceptée.

    L'état continue d'exposer les deux nombres — ce qui est réglé et ce que l'effectif permet —
    pour que l'atelier montre l'écart au lieu de le subir.
    """
    monde = _Monde()
    monde.inscrire(3)
    monde.regler(ConfigurationColline(nb_manches=2, portee_de_defi=5))
    service = monde.service()

    etat = service.etat(monde.tournoi_id, monde.phase_id)

    assert etat.portee_de_defi == 5
    assert etat.portee_maximale == 2
    assert len(etat.manches) >= 1


def test_une_phase_vide_est_une_photo_vide_et_non_une_erreur() -> None:
    """Une phase se compose et se règle **avant** que sa population existe.

    Sans cette porte, l'écran de saisie et toute phase avale qui y prélève sortaient en 500 — le
    correctif que les poules ont dû faire en revue.
    """
    monde = _Monde()
    monde.regler(ConfigurationColline(nb_manches=3, portee_de_defi=1))
    service = monde.service()

    etat = service.etat(monde.tournoi_id, monde.phase_id)

    assert etat.effectif == 0
    assert etat.manches == ()
    assert etat.portee_maximale == 0
    assert etat.classement == ()


def test_un_archer_seul_occupe_la_position_1_meme_sans_defi_appariable() -> None:
    """Ne pas apparier de défi **n'est pas** ne classer personne (correctif de revue, axe A).

    À un archer, `portee_maximale` vaut 0 : aucun défi n'existe, et c'est exact. Mais l'archer
    prélevé, lui, **existe** et occupe la position 1. Le classement était rendu vide dans ce cas,
    ce qui se voyait à trois endroits : une colline **vide** sur l'écran public alors qu'un archer y
    est, un `INDISPONIBLE` au panneau de routage — « il n'y figure pas » — au lieu d'`EN_ATTENTE`,
    et une source **vide** servie à une phase avale au lieu d'un rang.

    Le cas est atteignable **dès la composition**, avant que la source amont ait classé du monde :
    c'est le régime que la docstring d'`avancement_de_phase` qualifie de « normal et durable », pas
    un cas tordu. La contrepartie est le test ci-dessus : à effectif **0**, le classement reste
    vide.
    """
    monde = _Monde()
    archers = monde.inscrire(1)
    monde.regler(ConfigurationColline(nb_manches=3, portee_de_defi=1))
    service = monde.service()

    etat = service.etat(monde.tournoi_id, monde.phase_id)

    assert etat.effectif == 1
    assert etat.portee_maximale == 0
    assert etat.manches == ()
    assert [(rang.position, rang.duelliste.archer_id) for rang in etat.classement] == [
        (1, archers[0])
    ]


# --- CA « habiter le contrat de phase jouable » ---------------------------------------------------


def test_le_classement_de_phase_est_l_ordre_final_de_la_colline() -> None:
    """**Le CA de l'US**, versant classement : c'est ce qui rend une phase avale alimentable.

    Jusqu'ici `ServiceSaisieDuels._classement_de_l_ordre` rendait `None` sur ce type, donc un
    prélèvement le visant restait **inerte** — la phase aval recevait tous les archers en lice, ce
    qui est plausible et faux.
    """
    monde = _Monde()
    archers = monde.inscrire(4)
    monde.regler(ConfigurationColline(nb_manches=1, portee_de_defi=1))
    service = monde.service()

    _gagner(service, monde, 1, le_bas=True)
    _gagner(service, monde, 2, le_bas=True)

    resolveur = service._saisie_duels.resolveur_de_classement(monde.tournoi_id, monde.depart_id)
    source = service.classement_de_phase(monde.tournoi_id, monde.phase_id, resolveur)

    assert [ligne.archer_id for ligne in source.classement.lignes] == [
        archers[1],
        archers[0],
        archers[3],
        archers[2],
    ]
    assert [ligne.rang_scratch for ligne in source.classement.lignes] == [1, 2, 3, 4]
    # Toutes les manches réglées sont closes : la colline a **fini**, donc plus rien ne retient un
    # prélèvement (cf. le test suivant, qui garde l'autre moitié).
    assert source.plages_indecises == ()


def test_une_colline_en_cours_retient_les_prelevements_de_ses_phases_avales() -> None:
    """ADR-0081 : « une phase attend que sa source ait départagé les places qu'elle prélève ».

    ⚠️ **La colline en était dépourvue, et elle est le seul format dans ce cas** (relevé en revue).
    Le domaine a raison de rendre `plages_indecises=()` : une colline n'a **jamais** d'ex æquo, deux
    archers n'occupant jamais la même position. Mais « personne n'est à égalité » n'est pas « tout
    est joué » — et c'est la seconde question que pose ADR-0081.

    Sans ce frein, une colline dont **aucune** manche n'est close rendait un classement complet et
    parfaitement départagé… qui n'est que le classement **amont** recopié. Une phase avale s'y
    ensemençait donc sans que rien ne dise « en attente » : l'organisateur posait son tableau et son
    plan de cibles pendant que la colline tournait, puis voyait l'ensemencement changer à chaque
    manche validée et les duels déjà tirés basculer en `desynchronisee`.

    Les trois autres formats ont ce frein **par accident** : une phase non commencée y met tout le
    monde à égalité, donc leur calcul d'ex æquo remplit la plage. Le garde-fou d'ADR-0081 ne tenait
    chez eux que par un effet de bord de leur mode de classement, ce que la colline a révélé en
    n'ayant pas cet effet de bord.
    """
    monde = _Monde()
    monde.inscrire(4)
    monde.regler(ConfigurationColline(nb_manches=2, portee_de_defi=1))
    service = monde.service()
    resolveur = service._saisie_duels.resolveur_de_classement(monde.tournoi_id, monde.depart_id)

    # Rien de tiré : le classement rendu **est** l'ordre amont, et il n'a rien décidé.
    source = service.classement_de_phase(monde.tournoi_id, monde.phase_id, resolveur)
    assert source.plages_indecises == ((1, 4),)

    # Première manche close, la seconde reste à jouer : les positions vont encore bouger.
    _jouer_la_manche_ouverte(service, monde)
    source = service.classement_de_phase(monde.tournoi_id, monde.phase_id, resolveur)
    assert source.plages_indecises == ((1, 4),)

    # Les deux manches closes : la colline a fini, le prélèvement passe.
    _jouer_la_manche_ouverte(service, monde)
    source = service.classement_de_phase(monde.tournoi_id, monde.phase_id, resolveur)
    assert source.plages_indecises == ()


def test_l_avancement_de_phase_se_lit_manche_par_manche() -> None:
    """Le port `LecteurAvancementDePhase` (ADR-0090 §5) — « Manche 2 sur 3 ».

    Le tour courant est la première manche **non close** ; `None` quand toutes le sont, car plus
    rien ne tourne même si la phase n'est pas clôturée.
    """
    monde = _Monde()
    monde.inscrire(4)
    monde.regler(ConfigurationColline(nb_manches=3, portee_de_defi=1))
    service = monde.service()

    _gagner(service, monde, 1, le_bas=True)
    _gagner(service, monde, 2, le_bas=True)

    avancement = service.avancement_de_phase(monde.tournoi_id, monde.phase_id)

    assert avancement is not None
    assert avancement.nb_tours == 3
    assert avancement.tour_courant == 2


def test_un_archer_au_repos_reste_en_course_sans_rencontre_a_tirer() -> None:
    """L'issue `EN_ATTENTE` (ADR-0087) : « en course, mais rien à tirer maintenant ».

    À portée 1, les extrémités se reposent une manche sur deux. Sans ce régime, elles passeraient
    pour **terminées** sur le panneau public — le bloquant qu'`epuisee` a corrigé sur le suisse.
    La phase n'est épuisée que si **toutes** les manches réglées sont closes.
    """
    monde = _Monde()
    archers = monde.inscrire(4)
    monde.regler(ConfigurationColline(nb_manches=3, portee_de_defi=1))
    service = monde.service()

    _gagner(service, monde, 1, le_bas=True)
    _gagner(service, monde, 2, le_bas=True)

    a_tirer = service.rencontres_a_tirer(monde.tournoi_id, monde.phase_id)

    engages = {
        archer for rencontre in a_tirer.rencontres for archer in (rencontre.haut, rencontre.bas)
    }
    assert a_tirer.epuisee is False
    assert archers[1] not in engages  # au repos : il occupe la position 1
    assert set(a_tirer.participants) == set(archers)


def test_le_plan_de_cibles_se_pose_et_les_couloirs_se_derivent() -> None:
    """3ᵉ question du contrat (ADR-0083 §3) : où ça se joue.

    Un **seul** bloc pour toute la phase, comme le suisse : une manche apparie sur le plateau
    entier et les défis **changent** d'une manche à l'autre — personne n'a de couloir attitré, donc
    « archer → couloir » serait une information *fausse*. C'est le bloc qui est persisté, les
    couloirs de chaque défi s'y dérivant manche par manche.
    """
    monde = _Monde()
    monde.inscrire(4)
    monde.regler(ConfigurationColline(nb_manches=3, portee_de_defi=1))
    service = monde.service()

    etat = service.regenerer_plan(monde.tournoi_id, monde.phase_id)

    assert etat.conflits == ()
    assert etat.manches[0].defis[0].couloirs is not None


def test_le_plan_absent_est_rapporte_en_lecture() -> None:
    """Le manque se rapporte à la **lecture**, pas seulement après une pose.

    Correctif de revue d'E05US030 : renseigné par la seule pose, le champ restait vide sur la route
    de saisie, si bien que le message « le plan de cibles n'est pas posé » de l'écran scoreur était
    une **branche morte** — le scoreur voyait ses défis sans aucune cible et sans un mot.
    """
    monde = _Monde()
    monde.inscrire(4)
    monde.regler(ConfigurationColline(nb_manches=3, portee_de_defi=1))
    service = monde.service()

    etat = service.etat(monde.tournoi_id, monde.phase_id)

    assert etat.conflits != ()


def test_une_phase_en_pause_refuse_la_validation_mais_pas_la_rectification() -> None:
    """E05US033 : la pause gèle ce qui **avance**, jamais ce qui **répare**.

    La validation est le geste qui fait avancer la colline (elle clôt une manche et autorise la
    suivante) : elle est donc refusée. La saisie d'une manche déjà engagée reste possible, sans
    quoi une rencontre entamée avant la pause serait dans un cul-de-sac.
    """
    monde = _Monde()
    monde.inscrire(4)
    phase_id = monde.regler(ConfigurationColline(nb_manches=3, portee_de_defi=1))
    service = monde.service()
    phase = monde.phases.par_id(phase_id)
    assert phase is not None
    monde.phases.enregistrer(replace(phase, statut=StatutPhase.EN_PAUSE))

    service.saisir_manche(
        monde.tournoi_id, phase_id, 1, 1, (ZoneScore("6"),) * 3, (ZoneScore("10"),) * 3
    )
    with pytest.raises(PhaseEnPause):
        service.valider(monde.tournoi_id, phase_id, 1, "scoreur")
