"""E05US026 — le service du **système suisse** : les rondes s'enchaînent.

Tests dérivés du **CA** (`stories/E05-moteur-phases.md` → E05US026), écrits **avant**
l'implémentation du service : ce qu'ils décrivent est la règle voulue, pas le code livré (règle 9).

Les deux puces éprouvées ici :

- « **les rondes s'enchaînent** : l'appariement de la ronde `n+1` se calcule des résultats de la
  ronde `n` » ;
- « **réglages à l'atelier** : nombre de rondes, avec le maximum que l'effectif autorise affiché en
  clair ».

⚠️ **Le décor discriminant.** Quatre archers classés 1-2-3-4 : la ronde 1 d'un suisse apparie fort
contre faible (1 vs 3, 2 vs 4), et l'on fait gagner les **mal classés**. La ronde 2 doit alors
opposer 3 à 4 (les vainqueurs) et 1 à 2 (les perdants) — ordre qu'aucune lecture du classement de
qualification ne produirait. C'est ce qui rend ces tests capables d'échouer : un service qui
oublierait de consommer les résultats rendrait le même appariement qu'à la ronde 1.
"""

from __future__ import annotations

import pytest

from application.classements import ServiceClassement
from application.erreurs import PhasePasReglee, PhasePasUnSuisse
from application.saisie_duels import ServiceSaisieDuels
from application.suisse import ServiceSuisse
from domain.archer import Archer
from domain.blason import Blason, ZoneScore
from domain.categorie import Categorie
from domain.depart import Depart
from domain.duel import ResolveurBaremeDuelFfta
from domain.gabarit_salle import GabaritSalle
from domain.inscription import Inscription
from domain.phase import Phase, TypePhase
from domain.politiques import (
    AggregationParQualification,
    ByesAuxMieuxClasses,
    PlacementEnCascade,
    SeedingSerpent,
    registre_par_defaut,
)
from domain.suisse import ConfigurationSuisse
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
    """Double du port `PlacementParBlocRepository` — deux gestes, comme le port."""

    def __init__(self) -> None:
        self._plans: dict[int, list[object]] = {}

    def par_phase(self, phase_id: int) -> list[object]:
        return list(self._plans.get(phase_id, []))

    def definir_plan(self, phase_id: int, blocs: object) -> None:
        self._plans[phase_id] = list(blocs)  # type: ignore[call-overload]


class _FauxGabaritRepository:
    """Double de `GabaritSalleRepository` : une salle homogène de `nb_cibles` sur `couloirs`."""

    def __init__(self, nb_cibles: int = 8, couloirs: int = 4) -> None:
        self._gabarit = GabaritSalle.creer("Salle", nb_cibles=nb_cibles, capacite=couloirs)

    def par_tournoi(self, tournoi_id: int) -> GabaritSalle:
        return self._gabarit


class _Monde:
    """Décor : un tournoi, un créneau, N archers classés, une phase de **système suisse**.

    Les archers reçoivent des scores décroissants dans l'ordre de création → rang scratch 1..N.
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
        from dataclasses import replace

        self.blasons._blasons[blason.id] = replace(blason, zones=ZONES_TRIPLE)
        categorie = self.categories.ajouter(
            Categorie.creer(
                self.tournoi_id, "Cat", arme="Arc Classique", blason_id=blason.id, hauteur_cm=130
            )
        )
        assert categorie.id is not None
        self.categorie_id = categorie.id
        from domain.bareme import BaremeQualification

        qualif = self.phases.ajouter(
            Phase.qualification(self.depart_id, BaremeQualification.creer(1, 3))
        )
        assert qualif.id is not None
        self.qualif_id = qualif.id
        self.phase_id = 0

    def regler(self, reglage: ConfigurationSuisse | None) -> int:
        """Pose la phase de suisse avec son réglage (ou sans, pour éprouver le refus)."""
        phase = self.phases.ajouter(
            Phase(depart_id=self.depart_id, ordre=2, type=TypePhase.SUISSE, suisse=reglage)
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

    def service(self) -> ServiceSuisse:
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
        return ServiceSuisse(
            self.tournois,
            self.phases,
            self.gabarits,  # type: ignore[arg-type]
            self.placements,  # type: ignore[arg-type]
            self.duels,
            classement,
            saisie,
        )


def _gagner(service: ServiceSuisse, monde: _Monde, numero: int, *, le_bas: bool) -> None:
    """Fait gagner un camp d'une rencontre, puis **valide** — c'est la validation qui compte.

    Trois manches gagnées d'affilée closent le duel en sets ; on tire au maximum ce qu'il faut.
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


def _rondes(service: ServiceSuisse, monde: _Monde) -> tuple[tuple[tuple[int, int], ...], ...]:
    """Les rondes appariées, chacune comme un tuple de couples d'archers."""
    etat = service.etat(monde.tournoi_id, monde.phase_id)
    return tuple(
        tuple(
            (rencontre.haut.archer_id, rencontre.bas.archer_id)
            for rencontre in ronde.rencontres
            if rencontre.haut is not None and rencontre.bas is not None
        )
        for ronde in etat.rondes
    )


# --- CA « les rondes s'enchaînent » ---------------------------------------------------------------


def test_la_premiere_ronde_apparie_fort_contre_faible() -> None:
    """L'ouverture d'un suisse : 1 vs N/2+1, 2 vs N/2+2 — pas 1 vs N.

    C'est la façon habituelle d'ouvrir : elle évite qu'un favori sorte dès la première ronde, sans
    introduire d'aléa. À quatre archers classés 1-2-3-4, cela donne 1-3 et 2-4 (et non 1-4, 2-3, qui
    serait l'ensemencement **serpent** d'un tableau — la confusion à ne pas faire).
    """
    monde = _Monde()
    archers = monde.inscrire(4)
    monde.regler(ConfigurationSuisse(nb_rondes=3))

    rondes = _rondes(monde.service(), monde)

    assert rondes[0] == ((archers[0], archers[2]), (archers[1], archers[3]))


def test_la_ronde_suivante_se_calcule_des_resultats_de_la_precedente() -> None:
    """**Le CA de l'US.** Les vainqueurs rencontrent les vainqueurs, les perdants les perdants.

    On fait gagner les **mal classés** (3 et 4) : la ronde 2 doit donc opposer 3 à 4 et 1 à 2 —
    ordre qu'aucune lecture du classement de qualification ne produirait. Un service qui oublierait
    de consommer les résultats rendrait le même appariement qu'à la ronde 1, et ce test tomberait.
    """
    monde = _Monde()
    archers = monde.inscrire(4)
    monde.regler(ConfigurationSuisse(nb_rondes=3))
    service = monde.service()

    # Ronde 1 : 1 vs 3 et 2 vs 4 — le **bas** l'emporte dans les deux cas.
    _gagner(service, monde, 1, le_bas=True)
    _gagner(service, monde, 2, le_bas=True)

    rondes = _rondes(service, monde)

    assert len(rondes) == 2
    assert set(rondes[1]) == {(archers[2], archers[3]), (archers[0], archers[1])}


def test_une_ronde_partiellement_saisie_n_apparie_pas_la_suivante() -> None:
    """Une ronde se saisit cible par cible : l'état « en cours » est le régime **normal** du jour J.

    Le moteur **refuse** d'apparier par-dessus (`_rondes_closes` lève), parce que la ronde suivante
    perdrait les rencontres non encore saisies et donnerait le bye à quelqu'un qui vient de tirer.
    Le service ne tente donc pas l'appel : il s'arrête, et l'état **dit** que la ronde est ouverte —
    c'est ce qui permet à l'écran de nommer l'attente au lieu d'afficher un bouton inerte.
    """
    monde = _Monde()
    monde.inscrire(4)
    monde.regler(ConfigurationSuisse(nb_rondes=3))
    service = monde.service()

    _gagner(service, monde, 1, le_bas=True)  # une seule des deux rencontres

    etat = service.etat(monde.tournoi_id, monde.phase_id)

    assert len(etat.rondes) == 1
    assert etat.rondes[0].close is False


def test_un_tir_non_valide_ne_clot_pas_la_ronde() -> None:
    """Seuls les duels **validés** comptent — sinon l'appariement bougerait à chaque flèche.

    Le tir est complet (trois manches gagnées), mais pas validé. La ronde reste ouverte : c'est le
    même parti que la reconstruction d'un tableau et que les poules, et il protège le juge d'un
    appariement qui changerait sous ses yeux.
    """
    monde = _Monde()
    monde.inscrire(4)
    monde.regler(ConfigurationSuisse(nb_rondes=3))
    service = monde.service()

    for numero in (1, 2):
        for manche in (1, 2, 3):
            service.saisir_manche(
                monde.tournoi_id,
                monde.phase_id,
                numero,
                manche,
                (ZoneScore("6"),) * 3,
                (ZoneScore("10"),) * 3,
            )

    etat = service.etat(monde.tournoi_id, monde.phase_id)

    assert len(etat.rondes) == 1
    assert etat.rondes[0].close is False


def test_le_rejeu_s_arrete_au_nombre_de_rondes_regle() -> None:
    """On ne joue pas plus de rondes que réglé — le réglage est une **fin**, pas un minimum."""
    monde = _Monde()
    monde.inscrire(4)
    monde.regler(ConfigurationSuisse(nb_rondes=1))
    service = monde.service()

    _gagner(service, monde, 1, le_bas=True)
    _gagner(service, monde, 2, le_bas=True)

    etat = service.etat(monde.tournoi_id, monde.phase_id)

    assert len(etat.rondes) == 1
    assert etat.rondes[0].close is True


# --- CA « le maximum que l'effectif autorise, affiché en clair » ---------------------------------


def test_l_etat_rend_la_borne_que_l_effectif_autorise() -> None:
    """CA « avec le maximum que l'effectif autorise affiché en clair ».

    La borne est **rendue par le service**, pas recalculée à l'écran : deux arithmétiques pour une
    même règle sont une divergence en attente — la leçon des dix filtres d'ADR-0083. À 5 archers
    (effectif impair), le bye coûte un tour et la borne vaut 5, pas 4.
    """
    monde = _Monde()
    monde.inscrire(5)
    monde.regler(ConfigurationSuisse(nb_rondes=2))

    etat = monde.service().etat(monde.tournoi_id, monde.phase_id)

    assert etat.effectif == 5
    assert etat.rondes_maximales == 5
    assert etat.nb_rondes == 2


def test_a_effectif_impair_une_ronde_decerne_un_bye() -> None:
    """À effectif impair, un participant chôme — et il est **nommé**, pas déduit d'une absence.

    Le moteur a appris cette leçon : déduire le bye des « rencontres manquantes » le confondait avec
    une ronde partiellement saisie. Le service le lit donc de l'appariement et le rend tel quel.
    """
    monde = _Monde()
    monde.inscrire(5)
    monde.regler(ConfigurationSuisse(nb_rondes=2))

    etat = monde.service().etat(monde.tournoi_id, monde.phase_id)

    assert len(etat.rondes[0].rencontres) == 2
    assert etat.rondes[0].bye is not None


# --- Gardes ---------------------------------------------------------------------------------------


def test_une_phase_non_reglee_refuse_de_se_jouer() -> None:
    """Le type se choisit avant ses paramètres — mais on ne déroule pas une phase sans réglage."""
    monde = _Monde()
    monde.inscrire(4)
    monde.regler(None)

    with pytest.raises(PhasePasReglee):
        monde.service().etat(monde.tournoi_id, monde.phase_id)


def test_une_phase_d_un_autre_type_est_refusee() -> None:
    """Chaque décor refuse ce qui n'est pas le sien — et le message nomme le format attendu."""
    monde = _Monde()
    monde.inscrire(4)

    with pytest.raises(PhasePasUnSuisse):
        monde.service().etat(monde.tournoi_id, monde.qualif_id)


def test_une_phase_sans_population_est_une_photo_vide_pas_une_erreur() -> None:
    """Une phase se compose et se règle **avant** que sa population existe.

    Sans cette porte, l'écran de saisie et toute phase avale qui y prélève sortiraient en 500 — le
    correctif que les poules ont dû faire en revue, repris ici plutôt que refait après coup.
    """
    monde = _Monde()
    monde.regler(ConfigurationSuisse(nb_rondes=3))

    etat = monde.service().etat(monde.tournoi_id, monde.phase_id)

    assert etat.effectif == 0
    assert etat.rondes == ()
    assert etat.classement == ()


# --- CA « le plan de cibles suit » ----------------------------------------------------------------


def test_la_phase_occupe_un_seul_bloc_de_couloirs_contigus() -> None:
    """CA « le plan de cibles suit », et **un seul** bloc là où les poules en posent un par groupe.

    C'est toute la différence entre les deux formats : une ronde de suisse apparie **tout le
    plateau** d'un coup, il n'y a donc pas de groupes à séparer. À 4 archers, l'empreinte vaut
    `2 * (4 // 2) = 4` couloirs — deux rencontres côte à côte.
    """
    monde = _Monde()
    monde.inscrire(4)
    monde.regler(ConfigurationSuisse(nb_rondes=3))
    service = monde.service()

    etat = service.regenerer_plan(monde.tournoi_id, monde.phase_id)

    couloirs = [r.couloirs for r in etat.rondes[0].rencontres]
    assert couloirs == [((1, "A"), (1, "B")), ((1, "C"), (1, "D"))]
    assert etat.conflits == ()


def test_a_effectif_impair_le_porteur_de_bye_ne_consomme_aucun_couloir() -> None:
    """5 archers → 2 rencontres → **4** couloirs, pas 5.

    Le porteur de bye ne tire pas ; mais ce n'est jamais le même d'une ronde à l'autre, et c'est
    exactement pourquoi on persiste le **bloc** et non « archer → couloir » (ADR-0083 §3). Réserver
    un 5ᵉ couloir pour un absent tournant serait une salle mal remplie **et** une information
    fausse.
    """
    monde = _Monde()
    monde.inscrire(5)
    monde.regler(ConfigurationSuisse(nb_rondes=2))
    service = monde.service()

    etat = service.regenerer_plan(monde.tournoi_id, monde.phase_id)

    assert [r.couloirs for r in etat.rondes[0].rencontres] == [
        ((1, "A"), (1, "B")),
        ((1, "C"), (1, "D")),
    ]
    assert etat.rondes[0].bye is not None


def test_la_ronde_suivante_retrouve_les_memes_couloirs() -> None:
    """La position se compte **par ronde**, jamais cumulée sur la phase.

    Une position cumulée ferait glisser la phase d'un cran à chaque ronde et déborder de son propre
    bloc — la même erreur que les poules ont dû éviter tour par tour. Les couloirs sont donc
    identiques d'une ronde à l'autre : c'est le **plateau** qui est réservé, pas la rencontre.
    """
    monde = _Monde()
    monde.inscrire(4)
    monde.regler(ConfigurationSuisse(nb_rondes=3))
    service = monde.service()
    service.regenerer_plan(monde.tournoi_id, monde.phase_id)
    _gagner(service, monde, 1, le_bas=True)
    _gagner(service, monde, 2, le_bas=True)

    etat = service.etat(monde.tournoi_id, monde.phase_id)

    assert len(etat.rondes) == 2
    assert [r.couloirs for r in etat.rondes[1].rencontres] == [
        ((1, "A"), (1, "B")),
        ((1, "C"), (1, "D")),
    ]


def test_sans_plan_pose_les_couloirs_ne_s_inventent_pas() -> None:
    """Un plan non posé se **voit** non posé : `None`, jamais un couloir deviné.

    L'écran doit pouvoir dire « générez le plan » plutôt que d'afficher une salle plausible et
    fausse — même parti que les poules et que le plan de cibles de qualification.
    """
    monde = _Monde()
    monde.inscrire(4)
    monde.regler(ConfigurationSuisse(nb_rondes=3))

    etat = monde.service().etat(monde.tournoi_id, monde.phase_id)

    assert all(r.couloirs is None for r in etat.rondes[0].rencontres)


def test_une_salle_trop_petite_est_rapportee_et_non_tronquee() -> None:
    """Le placement **rapporte** ce qu'il n'a pas pu faire (ADR-0024), il ne tronque pas en silence.

    Sans ce report, l'organisateur dont la salle est trop petite verrait un plan vide sans
    explication, au moment même où il vient de le générer — le défaut relevé en revue d'E05US023.
    """
    monde = _Monde()
    monde.inscrire(8)
    monde.regler(ConfigurationSuisse(nb_rondes=3))
    monde.gabarits = _FauxGabaritRepository(nb_cibles=1, couloirs=2)

    etat = monde.service().regenerer_plan(monde.tournoi_id, monde.phase_id)

    assert [c.raison.value for c in etat.conflits] == ["salle_pleine"]
