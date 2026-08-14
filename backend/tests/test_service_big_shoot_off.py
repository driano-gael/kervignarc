"""Service **Big Shoot Off** — projeter, faire tirer, éliminer, classer (E05US028).

**Chaque test porte le CA dont il dérive** (`stories/E05-moteur-phases.md`, puces « CA », amendées
au cadrage du 14/08/2026), et non une lecture de l'implémentation — c'est la source qui fait
l'indépendance, pas l'auteur (règle 9).

⚠️ **Honnêteté sur l'ordre d'écriture**, comme pour `test_service_poules.py` : le service a été
écrit avant ces tests, contrairement à l'étage domaine de cette US (`test_domain_big_shoot_off.py`)
qui, lui, a bien précédé son implémentation. L'étage service n'est pas là où vit la règle métier —
c'est de l'assemblage —, mais l'ordre inverse aurait mieux protégé et le dire vaut mieux que de le
taire. Les oracles ci-dessous sont relus **depuis les puces du CA**, ligne à ligne.
"""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import replace

import pytest

from application.big_shoot_off import ServiceBigShootOff
from application.classements import ServiceClassement
from application.erreurs import PhasePasReglee, PhasePasUnBigShootOff
from application.saisie_duels import ServiceSaisieDuels
from domain.archer import Archer
from domain.bareme import BaremeQualification
from domain.barrage import BarrageDePlaces, PorteeBarrage, TirBarrage
from domain.big_shoot_off import ConfigurationBigShootOff
from domain.blason import Blason, ZoneScore
from domain.categorie import Categorie
from domain.depart import Depart
from domain.duel import ResolveurBaremeDuelFfta
from domain.inscription import Inscription
from domain.participant import Participant
from domain.phase import Phase, PhaseId, TypePhase
from domain.politiques import (
    AggregationParQualification,
    ByesAuxMieuxClasses,
    PlacementEnCascade,
    SeedingSerpent,
    registre_par_defaut,
)
from domain.serie import Serie, Volee
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxDepartRepository,
    FauxDuelRepository,
    FauxForfaitRepository,
    FauxInscriptionRepository,
    FauxPhaseRepository,
)
from tests.test_service_placement_duels import FauxBlasonRepository, FauxTournoiRepository
from tests.test_service_saisie_duels import ZONES_TRIPLE


class _FauxSerieRepository:
    """Double **complet** de `SerieRepository` — le Big Shoot Off y lit *et* y écrit.

    Celui de `test_service_placement_duels` lève `NotImplementedError` sur `par_archer` et
    `enregistrer` : il ne servait qu'au classement, en lecture par phase. Ici la feuille est le
    support du tir, donc les deux gestes comptent.
    """

    def __init__(self) -> None:
        self._series: list[Serie] = []

    def semer(
        self, tournoi_id: int, archer_id: int, valeurs: tuple[ZoneScore, ...], phase_id: int
    ) -> None:
        self._series.append(
            Serie(
                tournoi_id=tournoi_id,
                archer_id=archer_id,
                phase_id=phase_id,
                volees=(Volee(numero=1, valeurs=valeurs, validee_par="Scoreur"),),
            )
        )

    def par_phase(self, phase_id: int) -> list[Serie]:
        return [s for s in self._series if s.phase_id == phase_id]

    def par_tournoi(self, tournoi_id: int) -> list[Serie]:
        return [s for s in self._series if s.tournoi_id == tournoi_id]

    def par_archer(self, phase_id: int, archer_id: int) -> Serie | None:
        return next(
            (s for s in self._series if s.phase_id == phase_id and s.archer_id == archer_id),
            None,
        )

    def horodatages(self, phase_id: int, archer_id: int) -> dict[int, datetime.datetime]:
        return {}

    def enregistrer(self, serie: Serie) -> Serie:
        for index, existante in enumerate(self._series):
            if (existante.phase_id, existante.archer_id) == (serie.phase_id, serie.archer_id):
                self._series[index] = serie
                return serie
        self._series.append(serie)
        return serie

    def enregistrer_avec_trace(self, serie: Serie, entree: object) -> Serie:
        """Conformité au port. Le Big Shoot Off n'emprunte pas ce chemin : ses validations passent
        par `enregistrer`, comme la saisie ordinaire — la trace d'audit d'E12US007 n'est câblée que
        sur la correction habilitée."""
        return self.enregistrer(serie)


class _FauxBarrageRepository:
    """Double du port `BarrageRepository`. Le service ne lit que `par_depart` ; le reste est de la
    **conformité au protocole** — mypy exige la surface complète, et une doublure partielle
    typée `Any` masquerait un jour un port qui a bougé."""

    def __init__(self) -> None:
        self.barrages: list[BarrageDePlaces] = []

    def par_depart(self, depart_id: int) -> list[BarrageDePlaces]:
        return list(self.barrages)

    def par_tournoi(self, tournoi_id: int) -> list[BarrageDePlaces]:
        return list(self.barrages)

    def par_id(self, barrage_id: int) -> BarrageDePlaces | None:
        raise NotImplementedError

    def ouvrir(self, barrage: BarrageDePlaces) -> BarrageDePlaces:
        raise NotImplementedError

    def enregistrer_manche(
        self, barrage_id: int, manche: int, tirs: Sequence[TirBarrage]
    ) -> BarrageDePlaces:
        raise NotImplementedError

    def supprimer(self, barrage_id: int) -> None:
        raise NotImplementedError

    def clore(self, barrage_id: int) -> BarrageDePlaces:
        raise NotImplementedError

    def rouvrir(self, barrage_id: int) -> BarrageDePlaces:
        raise NotImplementedError


class _Monde:
    """Décor : un tournoi, un créneau, N archers classés, une phase de **Big Shoot Off**.

    Les archers reçoivent des scores de qualification décroissants dans l'ordre de création, donc
    rang scratch 1..N — ce qui rend le prélèvement prévisible.
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
        self.series = _FauxSerieRepository()
        self.duels = FauxDuelRepository()
        self.forfaits = FauxForfaitRepository()
        self.barrages = _FauxBarrageRepository()
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
        self.phase_id: PhaseId = 0

    def regler(
        self, configuration: ConfigurationBigShootOff | None, type_phase: TypePhase | None = None
    ) -> PhaseId:
        """Pose la phase avec son réglage (ou sans, pour éprouver le refus)."""
        phase = self.phases.ajouter(
            Phase(
                depart_id=self.depart_id,
                ordre=2,
                type=type_phase or TypePhase.BIG_SHOOT_OFF,
                big_shoot_off=configuration,
            )
        )
        assert phase.id is not None
        self.phase_id = phase.id
        return phase.id

    def inscrire(self, combien: int) -> list[int]:
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
            valeur = str(max(6, 10 - rang))
            self.series.semer(
                self.tournoi_id,
                archer.id,
                (ZoneScore(valeur), ZoneScore(valeur), ZoneScore(valeur)),
                self.qualif_id,
            )
            self.inscriptions.ajouter(Inscription.creer(archer.id, self.depart_id))
            ids.append(archer.id)
        return ids

    def service(self) -> ServiceBigShootOff:
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
        return ServiceBigShootOff(
            self.tournois,
            self.phases,
            self.series,
            self.barrages,
            classement,
            saisie,
        )

    def tirer(self, service: ServiceBigShootOff, archer_id: int, numero: int, zone: str) -> None:
        """Saisit **et** valide la volée `numero` d'un archer (trois flèches de la même zone)."""
        valeurs = (ZoneScore(zone), ZoneScore(zone), ZoneScore(zone))
        service.saisir_volee(self.tournoi_id, self.phase_id, archer_id, numero, valeurs)
        service.valider_manche(self.tournoi_id, self.phase_id, archer_id, "Scoreur")


# --- CA « réglages à l'atelier » : la projection montre ce que la liste donne ---------------------


def test_la_projection_montre_les_paliers_sur_l_effectif_reel() -> None:
    """L'organisateur voit « 12 → 8 → 6 → 5 » **avant** de composer, patron `RepartitionPoules`.

    C'est ce qui rend inoffensif le choix « on joue tant que la manche est possible » : le moteur ne
    refuse rien, mais l'écran ne laisse pas l'organisateur découvrir le résultat en salle.
    """
    monde = _Monde()
    monde.inscrire(12)
    monde.regler(ConfigurationBigShootOff(eliminations=(4, 2, 1)))

    projection = monde.service().projection(monde.tournoi_id, monde.phase_id)

    assert projection.effectif == 12
    assert projection.paliers == (8, 6, 5)
    assert projection.restants == 5
    assert projection.manches_ignorees == 0


def test_la_projection_dit_combien_de_manches_ne_se_joueront_pas() -> None:
    """CA « on joue tant que la manche est possible » — mais l'écran doit le **dire**.

    Sur 6 archers, `[4, 2, 1]` ne joue qu'une manche : la deuxième sortirait 2 archers sur 2. Sans
    `manches_ignorees`, l'organisateur croirait jouer une liste qu'il ne joue pas.
    """
    monde = _Monde()
    monde.inscrire(6)
    monde.regler(ConfigurationBigShootOff(eliminations=(4, 2, 1)))

    projection = monde.service().projection(monde.tournoi_id, monde.phase_id)

    assert projection.paliers == (2,)
    assert projection.manches_jouables == 1
    assert projection.manches_ignorees == 2


def test_une_phase_non_reglee_est_refusee_a_l_usage_pas_a_la_composition() -> None:
    """Le type se choisit **avant** ses paramètres (brouillon d'ADR-0063) : c'est le service du jour
    J qui exige le réglage, pas l'agrégat."""
    monde = _Monde()
    monde.inscrire(4)
    monde.regler(None)

    with pytest.raises(PhasePasReglee):
        monde.service().etat(monde.tournoi_id, monde.phase_id)


def test_une_phase_d_un_autre_type_est_refusee() -> None:
    """Chaque décor refuse ce qui n'est pas le sien — et le refus est **dérivé du contrat**."""
    monde = _Monde()
    monde.inscrire(4)
    monde.regler(None, type_phase=TypePhase.ELIMINATION_DIRECTE)

    with pytest.raises(PhasePasUnBigShootOff):
        monde.service().etat(monde.tournoi_id, monde.phase_id)


# --- CA « habiter le contrat » : une manche validée élimine et décerne les rangs ------------------


def test_une_manche_validee_elimine_les_plus_faibles_et_les_classe() -> None:
    """CA du 14/08 : plusieurs sortants par manche, **classés entre eux au score de la manche**.

    Quatre archers, la manche 1 en sort deux. Les deux plus faibles prennent les rangs 4 et 3, dans
    l'ordre de leur score.
    """
    monde = _Monde()
    a, b, c, d = monde.inscrire(4)
    monde.regler(ConfigurationBigShootOff(eliminations=(2,)))
    service = monde.service()
    for archer_id, zone in ((a, "10"), (b, "9"), (c, "8"), (d, "7")):
        monde.tirer(service, archer_id, 1, zone)

    etat = service.etat(monde.tournoi_id, monde.phase_id)

    sorts = {t.archer_id: (t.en_lice, t.rang) for t in etat.tireurs}
    assert sorts[d] == (False, 4)
    assert sorts[c] == (False, 3)
    assert sorts[a] == (True, None)
    assert sorts[b] == (True, None)


def test_une_manche_incomplete_n_elimine_personne() -> None:
    """⚠️ Un score **manquant n'est pas un zéro** : tant qu'un archer en lice n'a pas validé, la
    manche n'a pas eu lieu. La compter éliminerait quelqu'un sur une donnée absente."""
    monde = _Monde()
    a, b, c, d = monde.inscrire(4)
    monde.regler(ConfigurationBigShootOff(eliminations=(2,)))
    service = monde.service()
    for archer_id, zone in ((a, "10"), (b, "9"), (c, "8")):
        monde.tirer(service, archer_id, 1, zone)

    etat = service.etat(monde.tournoi_id, monde.phase_id)

    assert all(tireur.en_lice for tireur in etat.tireurs)
    assert etat.manches[0].complete is False


def test_une_volee_saisie_mais_non_validee_ne_fait_rien_bouger() -> None:
    """Un tir en cours de saisie ferait bouger l'élimination à chaque flèche, et un archer
    apparaîtrait sorti puis rentré sous les yeux du juge."""
    monde = _Monde()
    a, b, c, d = monde.inscrire(4)
    monde.regler(ConfigurationBigShootOff(eliminations=(2,)))
    service = monde.service()
    for archer_id, zone in ((a, "10"), (b, "9"), (c, "8"), (d, "7")):
        service.saisir_volee(
            monde.tournoi_id,
            monde.phase_id,
            archer_id,
            1,
            (ZoneScore(zone), ZoneScore(zone), ZoneScore(zone)),
        )

    etat = service.etat(monde.tournoi_id, monde.phase_id)

    assert all(tireur.en_lice for tireur in etat.tireurs)


def test_les_manches_s_enchainent() -> None:
    """CA « les manches s'enchaînent » : la manche 2 se calcule des survivants de la manche 1."""
    monde = _Monde()
    a, b, c, d = monde.inscrire(4)
    monde.regler(ConfigurationBigShootOff(eliminations=(2, 1)))
    service = monde.service()
    for archer_id, zone in ((a, "10"), (b, "9"), (c, "8"), (d, "7")):
        monde.tirer(service, archer_id, 1, zone)
    # Manche 2 : `b` s'effondre et sort, bien qu'il ait été 2ᵉ à la manche 1 (remise à zéro).
    for archer_id, zone in ((a, "9"), (b, "6")):
        monde.tirer(service, archer_id, 2, zone)

    etat = service.etat(monde.tournoi_id, monde.phase_id)

    sorts = {t.archer_id: (t.en_lice, t.rang) for t in etat.tireurs}
    assert sorts[b] == (False, 2)
    assert sorts[a] == (True, None)
    assert etat.termine is True


def test_l_ecran_ne_propose_que_les_manches_jouables() -> None:
    """Annoncer une manche qui ne se jouera pas ferait attendre au scoreur un tour qui n'arrive
    jamais."""
    monde = _Monde()
    monde.inscrire(6)
    monde.regler(ConfigurationBigShootOff(eliminations=(4, 2, 1)))

    etat = monde.service().etat(monde.tournoi_id, monde.phase_id)

    assert [manche.numero for manche in etat.manches] == [1]
    assert etat.manches[0].elimine == 4


# --- « la structure se recalcule » : une correction remonte toute la chaîne -----------------------


def test_corriger_une_volee_defait_l_elimination_qu_elle_avait_causee() -> None:
    """**Le test qui justifie de ne rien persister de l'élimination.**

    Si « éliminé à la manche 1 » était une ligne en base, corriger la volée qui l'a causée
    laisserait l'élimination en place : le classement dirait une chose, les scores une autre. Ici la
    correction remonte d'elle-même — au prix d'un rejeu complet à chaque lecture (`DETTE-031`).
    """
    monde = _Monde()
    a, b, c, d = monde.inscrire(4)
    monde.regler(ConfigurationBigShootOff(eliminations=(1,)))
    service = monde.service()
    for archer_id, zone in ((a, "10"), (b, "9"), (c, "8"), (d, "7")):
        monde.tirer(service, archer_id, 1, zone)
    assert {
        t.archer_id for t in service.etat(monde.tournoi_id, monde.phase_id).tireurs if not t.en_lice
    } == {d}

    # Le scoreur s'était trompé de ligne : `d` avait en fait tiré 10, et `a` 7.
    serie_d = monde.series.par_archer(monde.phase_id, d)
    serie_a = monde.series.par_archer(monde.phase_id, a)
    assert serie_d is not None and serie_a is not None
    monde.series.enregistrer(
        replace(serie_d, volees=(Volee(1, (ZoneScore.DIX,) * 3, validee_par="Scoreur"),))
    )
    monde.series.enregistrer(
        replace(serie_a, volees=(Volee(1, (ZoneScore.SEPT,) * 3, validee_par="Scoreur"),))
    )

    etat = service.etat(monde.tournoi_id, monde.phase_id)

    assert {t.archer_id for t in etat.tireurs if not t.en_lice} == {a}


def test_on_refuse_d_ecrire_pour_un_archer_deja_sorti() -> None:
    """Une tablette restée ouverte sur la manche 2 affiche encore un archer sorti à la manche 1.
    Sans ce refus, ses flèches entreraient dans une manche qu'il ne tire pas, et le classement de
    cette manche changerait **pour tout le monde**."""
    monde = _Monde()
    a, b, c, d = monde.inscrire(4)
    monde.regler(ConfigurationBigShootOff(eliminations=(1, 1)))
    service = monde.service()
    for archer_id, zone in ((a, "10"), (b, "9"), (c, "8"), (d, "7")):
        monde.tirer(service, archer_id, 1, zone)

    with pytest.raises(PhasePasReglee):
        service.saisir_volee(
            monde.tournoi_id, monde.phase_id, d, 2, (ZoneScore.DIX, ZoneScore.DIX, ZoneScore.DIX)
        )


# --- CA « le classement de la phase est lisible » -------------------------------------------------


def test_le_classement_de_phase_rend_les_rangs_decernes() -> None:
    """CA ajouté au cadrage : une phase avale peut prélever dans un Big Shoot Off, et le palmarès
    consomme ses rangs. Jusqu'ici le résolveur rendait `None` sur ce type, donc un prélèvement le
    visant restait **inerte** — la phase aval recevait tout le monde, ce qui est plausible et faux.
    """
    monde = _Monde()
    a, b, c, d = monde.inscrire(4)
    monde.regler(ConfigurationBigShootOff(eliminations=(1, 1, 1)))
    service = monde.service()
    for archer_id, zone in ((a, "10"), (b, "9"), (c, "8"), (d, "7")):
        monde.tirer(service, archer_id, 1, zone)
    for archer_id, zone in ((a, "10"), (b, "9"), (c, "8")):
        monde.tirer(service, archer_id, 2, zone)
    for archer_id, zone in ((a, "10"), (b, "9")):
        monde.tirer(service, archer_id, 3, zone)

    source = service.classement_de_phase(
        monde.tournoi_id,
        monde.phase_id,
        service._saisie_duels.resolveur_de_classement(monde.tournoi_id, monde.depart_id),
    )

    rangs = {ligne.archer_id: ligne.rang_scratch for ligne in source.classement.lignes}
    assert rangs == {a: 1, b: 2, c: 3, d: 4}
    assert source.plages_indecises == ()


def test_les_rescapes_encore_en_lice_sont_declares_indecis() -> None:
    """⚠️ ADR-0081 : sans cette déclaration, une phase avale prélevant « le rang 1 » d'un Big Shoot
    Off inachevé emporterait **tous** les rescapés en croyant en prendre un.

    Les rescapés partagent le rang 1 tant qu'ils sont en lice — c'est la règle du 31/07, et c'est
    une vraie indécision au sens exact d'ADR-0081.
    """
    monde = _Monde()
    a, b, c, d = monde.inscrire(4)
    monde.regler(ConfigurationBigShootOff(eliminations=(1,)))
    service = monde.service()
    for archer_id, zone in ((a, "10"), (b, "9"), (c, "8"), (d, "7")):
        monde.tirer(service, archer_id, 1, zone)

    source = service.classement_de_phase(
        monde.tournoi_id,
        monde.phase_id,
        service._saisie_duels.resolveur_de_classement(monde.tournoi_id, monde.depart_id),
    )

    assert source.plages_indecises == ((1, 3),)


# --- « égalité à la barre » : le barrage suspend, son verdict débloque ----------------------------


def test_une_egalite_a_la_barre_suspend_la_phase_et_l_ecran_le_dit() -> None:
    """Sans ce relais, le scoreur verrait une manche saisie **et validée** qui n'élimine personne,
    sans comprendre pourquoi la suivante refuse de s'ouvrir."""
    monde = _Monde()
    a, b, c, d = monde.inscrire(4)
    monde.regler(ConfigurationBigShootOff(eliminations=(1,)))
    service = monde.service()
    for archer_id, zone in ((a, "10"), (b, "9"), (c, "7"), (d, "7")):
        monde.tirer(service, archer_id, 1, zone)

    etat = service.etat(monde.tournoi_id, monde.phase_id)

    assert {duelliste.archer_id for duelliste in etat.barrage_entre} == {c, d}
    assert etat.places_au_barrage == 1
    assert all(tireur.en_lice for tireur in etat.tireurs)


def test_le_verdict_du_barrage_debloque_la_manche() -> None:
    """Le service **applique** le verdict de `domain/barrage.py`, il ne le rejoue pas.

    ⚠️ Les barrages **clos** comptent : les filtrer ferait retomber en égalité, à la lecture
    suivante, une manche qu'on a fait tirer.
    """
    monde = _Monde()
    a, b, c, d = monde.inscrire(4)
    monde.regler(ConfigurationBigShootOff(eliminations=(1,)))
    service = monde.service()
    for archer_id, zone in ((a, "10"), (b, "9"), (c, "7"), (d, "7")):
        monde.tirer(service, archer_id, 1, zone)

    monde.barrages.barrages.append(
        BarrageDePlaces(
            depart_id=monde.depart_id,
            portee=PorteeBarrage.BIG_SHOOT_OFF,
            phase_id=monde.phase_id,
            rang_dispute=None,
            participants=(Participant.individuel(c), Participant.individuel(d)),
            cree_le=datetime.datetime(2026, 8, 14, 9, 0, tzinfo=datetime.UTC),
            manches=(
                (
                    TirBarrage(Participant.individuel(c), 10),
                    TirBarrage(Participant.individuel(d), 8),
                ),
            ),
        )
    )

    etat = service.etat(monde.tournoi_id, monde.phase_id)

    sorts = {t.archer_id: (t.en_lice, t.rang) for t in etat.tireurs}
    assert sorts[d] == (False, 4)
    assert sorts[c] == (True, None)
    assert etat.barrage_entre == ()
