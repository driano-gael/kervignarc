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
from domain.erreurs import DuelIncomplet
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


# --- CA « le routage sait où l'archer tire ensuite » (arbitrage du 15/08/2026) ------------------


def test_le_routage_annonce_la_rencontre_qui_vient_avec_sa_cible() -> None:
    """Le port `LecteurRencontresARouter` : la **première** rencontre non tirée est celle qui vient.

    ⚠️ **Et sa cible est connue**, à la différence du Big Shoot Off (`DETTE-059`) : le plan de
    cibles d'un suisse est posé, donc `couloirs` est renseigné.
    """
    monde = _Monde()
    archers = monde.inscrire(4)
    monde.regler(ConfigurationSuisse(nb_rondes=3))
    service = monde.service()
    service.regenerer_plan(monde.tournoi_id, monde.phase_id)

    lecture = service.rencontres_a_tirer(monde.tournoi_id, monde.phase_id)

    a_tirer = lecture.rencontres
    assert [(r.numero, r.tour, r.libelle) for r in a_tirer] == [
        (1, 1, "Ronde 1"),
        (2, 1, "Ronde 1"),
    ]
    assert a_tirer[0].couloir_de(archers[0]) == (1, "A")
    assert a_tirer[0].couloir_de(archers[2]) == (1, "B")


def test_une_rencontre_validee_ne_reste_pas_a_tirer() -> None:
    """Le routage n'envoie personne sur une rencontre déjà scellée.

    Et il **n'annonce pas la ronde suivante** tant que la courante n'est pas close : son appariement
    n'existe pas encore, il n'y a rien à promettre.
    """
    monde = _Monde()
    archers = monde.inscrire(4)
    monde.regler(ConfigurationSuisse(nb_rondes=3))
    service = monde.service()
    service.regenerer_plan(monde.tournoi_id, monde.phase_id)
    _gagner(service, monde, 1, le_bas=True)

    lecture = service.rencontres_a_tirer(monde.tournoi_id, monde.phase_id)

    assert [r.numero for r in lecture.rencontres] == [2]
    # ⚠️ **La phase n'est pas épuisée pour autant** : c'est ce que le port doit dire, et son
    # absence était un bloquant de revue. Sans `epuisee`, l'archer dont la rencontre vient
    # d'être validée passait pour « terminé » alors qu'il lui reste deux rondes.
    assert lecture.epuisee is False
    assert set(lecture.participants) == set(archers)


# --- Correctifs de revue : les bornes que les fixtures d'origine évitaient toutes ----------------


def test_le_reglage_par_defaut_se_borne_a_ce_que_l_effectif_permet() -> None:
    """**Bloquant de revue.** `nb_rondes` vaut 5 par défaut ; à 4 archers, 3 rondes au plus.

    `EtapeDeroule` ne vérifie la borne que si l'effectif est **déclaré** — régime licite et testé
    juste à côté. Une phase réglée par défaut et jouée à 4 archers faisait donc lever
    `apparier_ronde` (`ConfigurationSuisseInvalide`, une **erreur de domaine**), ce qui remontait en
    422 sur le palmarès public, son PDF et le panneau de routage.

    On **borne à la lecture** plutôt que de lever : c'est la seule façon de tenir la promesse que
    `_configuration` écrit noir sur blanc — « un écran qui refuse de s'ouvrir vaut moins qu'un écran
    qui montre la borne ». L'état expose les deux nombres, donc l'atelier montre l'écart.

    ⚠️ Aucune fixture d'origine ne franchissait cette borne (`nb_rondes ∈ {1,2,3}` à 4 archers) :
    c'est ce qui rendait le défaut invisible en CI.
    """
    monde = _Monde()
    monde.inscrire(4)
    monde.regler(ConfigurationSuisse())  # défaut = 5 rondes

    etat = monde.service().etat(monde.tournoi_id, monde.phase_id)

    assert etat.nb_rondes == 5
    assert etat.rondes_maximales == 3
    assert len(etat.rondes) == 1  # la ronde 1 est appariée, pas une exception


def test_une_phase_vide_annonce_zero_ronde_appariable() -> None:
    """Sous deux tireurs, aucune ronde n'est appariable — la borne honnête est 0, pas 1."""
    monde = _Monde()
    monde.regler(ConfigurationSuisse(nb_rondes=3))

    assert monde.service().etat(monde.tournoi_id, monde.phase_id).rondes_maximales == 0


def test_le_porteur_de_bye_n_est_pas_annonce_termine() -> None:
    """**Bloquant de revue.** À effectif impair, un archer chôme — il n'a pas fini pour autant.

    Le port ne rendait que les rencontres : le porteur de bye en était absent, donc le panneau lui
    disait « Plus aucune rencontre à tirer dans cette phase ». Un archer à qui l'on dit terminé
    range son arc. `participants` et `epuisee` existent pour rendre les trois cas distincts.
    """
    monde = _Monde()
    archers = monde.inscrire(5)
    monde.regler(ConfigurationSuisse(nb_rondes=2))
    service = monde.service()

    lecture = service.rencontres_a_tirer(monde.tournoi_id, monde.phase_id)

    apparies = {a for r in lecture.rencontres for a in (r.haut, r.bas)}
    porteur = set(archers) - apparies
    assert len(porteur) == 1
    # Il est bien **dans** la phase, et la phase n'est pas épuisée : le routage ne peut donc pas
    # conclure « terminé ».
    assert porteur.issubset(set(lecture.participants))
    assert lecture.epuisee is False


def test_une_phase_entierement_jouee_est_epuisee() -> None:
    """Le seul cas où « terminé » est vrai : plus aucune rencontre ne viendra."""
    monde = _Monde()
    monde.inscrire(4)
    monde.regler(ConfigurationSuisse(nb_rondes=1))
    service = monde.service()
    _gagner(service, monde, 1, le_bas=True)
    _gagner(service, monde, 2, le_bas=True)

    lecture = service.rencontres_a_tirer(monde.tournoi_id, monde.phase_id)

    assert lecture.rencontres == ()
    assert lecture.epuisee is True


def test_une_rencontre_a_egalite_exige_son_barrage_avant_validation() -> None:
    """⚠️ **Ce test a corrigé une docstring fausse, pas un bug** — et c'est le garde-fou règle 9.

    Deux docstrings de cette US affirmaient qu'« un nul est ici un résultat **légitime** : le barème
    du format le prévoit (`POINTS_NUL`) […] ne pas tirer le barrage laisse la rencontre à 1-1, ce
    qui est une réponse ». C'est **faux au niveau de l'agrégat** : `Duel.valider` refuse un duel non
    tranché (`DuelIncomplet`), exactement comme pour une poule ou un tableau.

    La confusion venait du **moteur de domaine** : `domain/suisse.py` sait représenter un nul
    (`ResultatRonde.nul`, `POINTS_NUL`) parce qu'un système suisse générique en admet. Mais le
    **décor de saisie** du projet est le duel FFTA (ADR-0083 §7), et lui exige un vainqueur. La
    branche `POINTS_NUL` de `_resultat_de` est donc **inatteignable par le service** aujourd'hui.

    Écrire le test depuis la règle annoncée est ce qui a fait tomber l'écart : les docstrings ont
    été corrigées, le code non — il était juste.
    """
    monde = _Monde()
    monde.inscrire(4)
    monde.regler(ConfigurationSuisse(nb_rondes=2))
    service = monde.service()
    # Cinq manches nulles : 5-5, le duel est complet et l'égalité appelle le barrage (§8.2).
    egal = (ZoneScore("9"),) * 3
    for manche in (1, 2, 3, 4, 5):
        service.saisir_manche(monde.tournoi_id, monde.phase_id, 1, manche, egal, egal)

    with pytest.raises(DuelIncomplet):
        service.valider(monde.tournoi_id, monde.phase_id, 1, "scoreur")

    # Le barrage tranche, et la rencontre entre alors au classement.
    service.saisir_barrage(
        monde.tournoi_id,
        monde.phase_id,
        1,
        ZoneScore("10"),
        ZoneScore("9"),
    )
    service.valider(monde.tournoi_id, monde.phase_id, 1, "scoreur")
    # La seconde rencontre clôt la ronde : sans elle, aucun résultat n'entre au classement — c'est
    # le refus d'apparier par-dessus une ronde en cours, éprouvé plus haut.
    _gagner(service, monde, 2, le_bas=True)

    etat = service.etat(monde.tournoi_id, monde.phase_id)
    assert etat.rondes[0].close is True
    # Le barrage a tranché : le camp haut de la rencontre 1 marque la victoire pleine.
    assert sorted(ligne.points for ligne in etat.classement) == [0, 0, 2, 2]


# --- Correctif de revue E05US030 : la lecture dit que le plan n'est pas posé -------------------


def test_une_phase_sans_plan_rapporte_le_manque_a_la_lecture() -> None:
    """**Branche morte relevée en revue (axe adversarial).**

    `EtatSuisse.conflits` n'était rempli que par `regenerer_plan` : sur la route de saisie, la
    liste était **toujours vide**, donc le message « le plan de cibles n'est pas posé » de l'écran
    scoreur ne pouvait jamais s'afficher. Le scoreur voyait ses rondes sans aucune cible et sans un
    mot d'explication — exactement ce que la fiche de recette promet l'inverse.

    Le jumeau poules le fait depuis E05US023 (`ServicePoules._conflits_du_plan`) : on relaie le
    manque, on ne le comble pas — poser le bloc ici reviendrait à écrire un plan dans une méthode
    dont l'appelant croit qu'elle ne fait que lire.
    """
    monde = _Monde()
    monde.inscrire(4)
    monde.regler(ConfigurationSuisse(nb_rondes=2))

    etat = monde.service().etat(monde.tournoi_id, monde.phase_id)

    assert [c.raison.value for c in etat.conflits] == ["non_posee"]
    assert etat.rondes[0].rencontres[0].couloirs is None


def test_une_phase_dont_le_plan_est_pose_ne_rapporte_aucun_conflit() -> None:
    """Le miroir : sans lui, rendre `NON_POSEE` en tout cas passerait le test précédent."""
    monde = _Monde()
    monde.inscrire(4)
    monde.regler(ConfigurationSuisse(nb_rondes=2))
    service = monde.service()
    service.regenerer_plan(monde.tournoi_id, monde.phase_id)

    etat = service.etat(monde.tournoi_id, monde.phase_id)

    assert etat.conflits == ()
    assert etat.rondes[0].rencontres[0].couloirs is not None


def test_une_phase_vide_ne_rapporte_pas_un_plan_manquant() -> None:
    """Sous deux tireurs il n'y a **rien** à poser : réclamer un plan serait un contresens.

    C'est la borne que le jumeau poules tient par construction (aucune poule composée ⇒ aucun
    conflit) et que la photo vide du suisse doit tenir explicitement.
    """
    monde = _Monde()
    monde.regler(ConfigurationSuisse(nb_rondes=2))

    assert monde.service().etat(monde.tournoi_id, monde.phase_id).conflits == ()


def test_un_plan_pose_sur_un_effectif_plus_petit_est_rapporte() -> None:
    """**Le trou déplacé, relevé au 2ᵉ tour de revue par deux axes indépendants.**

    Le premier correctif ne testait que la **présence** d'un bloc. Or `regenerer_plan` dimensionne
    le bloc unique sur l'effectif **du jour de la pose**, et son numéro est toujours 1 : un archer
    qui s'inscrit après la pose ne fait pas disparaître le bloc, il le rend **trop court**. Les
    rencontres en débordement perdaient alors leur cible **sans que rien ne le dise** — très
    exactement la branche morte d'origine, un cran plus loin.

    ⚠️ **Le jumeau poules ne connaît pas ce cas** : une croissance d'effectif y ajoute des *groupes*,
    dont les numéros n'ont aucun bloc, donc `_conflits_du_plan` les détecte. Le suisse n'a qu'un
    groupe, qui ne disparaît jamais. `RaisonConflitBloc.NON_POSEE` couvre pourtant explicitement ce
    cas dans sa propre docstring — « posé, **ou l'a été sur une autre composition** ».
    """
    monde = _Monde()
    monde.inscrire(4)
    monde.regler(ConfigurationSuisse(nb_rondes=3))
    service = monde.service()
    service.regenerer_plan(monde.tournoi_id, monde.phase_id)
    monde.inscrire(2)  # deux retardataires, après la pose

    etat = service.etat(monde.tournoi_id, monde.phase_id)

    assert etat.effectif == 6
    assert [c.raison.value for c in etat.conflits] == ["non_posee"]
