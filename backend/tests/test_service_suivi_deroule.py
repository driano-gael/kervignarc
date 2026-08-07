"""Tests du service de suivi du déroulé (E07US004) — **dérivés du CA**, avant impl (règle 9).

Source : `stories/E07-affichage-public.md`, E07US004, puce « CA — le plan de tournoi, en suivi » :
*« le **même schéma à braquets** que l'atelier (E01US024), mais **rempli par la réalité** : phase
terminée / en cours / à venir, **tour en cours**, duels joués sur duels attendus, braquets qui **se
remplissent** au fur et à mesure »*.

Deux exigences se testent **ici** et non dans le domaine : elles portent sur la composition.

1. la projection rendue est **la même** que celle de l'atelier (c'est le mot « même » du CA) ;
2. un **exempt** (bye) n'est pas un duel joué — sans quoi le premier tour d'un tableau incomplet
   s'afficherait terminé avant que quiconque ait tiré.
"""

from __future__ import annotations

import dataclasses
import datetime
from collections.abc import Sequence

import pytest

from application.erreurs import DepartIntrouvable
from application.suivi_deroule import ServiceSuiviDeroule
from domain.bareme import BaremeQualification
from domain.depart import Depart, DepartId
from domain.deroule import projeter
from domain.grain_validation import GrainValidation
from domain.participant import Participant
from domain.phase import NatureSource, Phase, PhaseId, SourcePhase, StatutPhase, TypePhase
from domain.politiques import (
    ByesAuxMieuxClasses,
    PlacementEnCascade,
    ProfondeurPodium,
    SeedingSerpent,
)
from domain.tableau import Tableau, construire_tableau
from domain.tournoi import StatutTournoi, Tournoi, TournoiId
from tests.conftest import (
    FauxDepartRepository,
    FauxDerouleRepository,
    FauxPhaseRepository,
    poser_phase_factice,
)

_DATE = datetime.date(2026, 3, 14)
# Identifiants de créneau **volontairement distincts** de celui du tournoi (qui vaut 1) : les
# doublures partent toutes de `_sequence = 0`, et sans cette désynchronisation un test qui passe un
# `tournoi_id` là où un `depart_id` est attendu reste vert par coïncidence numérique.
_MATIN = 41
_APRES_MIDI = 42


def _tableau(effectif: int) -> Tableau:
    """Un tableau d'élimination directe pour `effectif` participants, rangés par qualification."""
    return construire_tableau(
        [Participant.individuel(rang) for rang in range(1, effectif + 1)],
        SeedingSerpent(),
        ByesAuxMieuxClasses(),
        PlacementEnCascade(),
        ProfondeurPodium(),
    )


def _jouer(tableau: Tableau, numeros: Sequence[int]) -> Tableau:
    """Fait gagner le camp haut des matchs désignés, **dans l'ordre**.

    Le match est **relu dans le tableau courant** à chaque itération : `Tableau.jouer` rend une
    nouvelle instance où les occupants du tour suivant viennent d'être propagés. Itérer sur une
    photo prise avant le premier coup donnerait des occupants `None` dès le deuxième tour.
    """
    for numero in numeros:
        match = tableau.match(numero)
        assert match.haut is not None, f"Le match {numero} n'a pas d'occupant haut."
        tableau = tableau.jouer(numero, match.haut)
    return tableau


class FauxTournoiRepository:
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


class FauxCompteurEngages:
    """Combien d'archers sont engagés **dans un créneau** — l'effectif que la projection résout.

    ⚠️ Le compte est **par départ** depuis ADR-0075 : un tournoi de deux créneaux à 100 archers
    chacun ne projette pas un déroulé à 200. Le décor permet donc un effectif **différent par
    créneau** (`regler`), sans quoi aucun test ne pourrait distinguer « l'effectif du créneau » de
    « l'effectif du tournoi » — c'est précisément la confusion que ce port a portée.
    """

    def __init__(self, nb: int = 0) -> None:
        self.defaut = nb
        self.par_depart: dict[int, int] = {}

    def regler(self, depart_id: int, nb: int) -> None:
        self.par_depart[depart_id] = nb

    def nb_engages_du_depart(self, depart_id: DepartId) -> int:
        return self.par_depart.get(depart_id, self.defaut)


class FauxLecteurTableau:
    """Rend un `Tableau` pré-construit par phase ; lève si on l'interroge sur une phase inconnue."""

    def __init__(self) -> None:
        self.tableaux: dict[PhaseId, Tableau] = {}

    def reconstruire(self, tournoi_id: TournoiId, phase_id: PhaseId) -> tuple[Tableau, object]:
        return self.tableaux[phase_id], {}


def _qualification(
    depart_id: int, ordre: int = 1, statut: StatutPhase = StatutPhase.A_VENIR
) -> Phase:
    """La phase de qualification du tournoi, dans le statut voulu."""
    phase = Phase.qualification(
        depart_id=depart_id,
        bareme=BaremeQualification.creer(12, 3),
        validation=GrainValidation.fin_de_serie(),
    )
    phase = dataclasses.replace(phase, ordre=ordre)
    return phase.demarrer() if statut is StatutPhase.EN_COURS else phase


class Contexte:
    """Un tournoi à **deux créneaux**, chacun rejouant le même déroulé (ADR-0075 / ADR-0076).

    ⚠️ **Deux créneaux et non un**, et à identifiants **désynchronisés** de celui du tournoi
    (`_MATIN`, `_APRES_MIDI`). Le décor mono-départ précédent rendait vert tout code lisant les
    phases à la maille **tournoi** : avec un seul créneau, « les phases du tournoi » et « les phases
    du créneau » sont la même liste, et `tournoi.id == depart.id == 1` laissait de surcroît passer
    toute confusion des deux identifiants (`DETTE-044` — même type pour mypy). C'est le trou par
    lequel la portée départ n'a pas été appliquée ici, alors que le renommage de port l'avait
    imposée partout où le nom changeait.

    Les deux créneaux partagent la **même** définition d'étapes — c'est ce qu'ADR-0076 rend
    structurel — mais portent leur avancement et leur effectif propres.
    """

    def __init__(self, nb_engages: int = 8) -> None:
        self.tournois = FauxTournoiRepository()
        self.departs = FauxDepartRepository()
        self.deroules = FauxDerouleRepository()
        # `deroules` **câblé** : sans lui la doublure reste en « mode indulgent » et rend les phases
        # telles qu'elles ont été posées, sans jamais franchir la couture d'assemblage d'ADR-0076.
        self.phases = FauxPhaseRepository(self.departs, self.deroules)
        self.engages = FauxCompteurEngages(nb_engages)
        self.tableaux = FauxLecteurTableau()
        tournoi = self.tournois.ajouter(
            dataclasses.replace(Tournoi.creer("Tournoi", _DATE), statut=StatutTournoi.EN_COURS)
        )
        assert tournoi.id is not None
        self.tournoi_id: TournoiId = tournoi.id
        self.depart_id = self._creneau(numero=1, horaire="09:00", depart_id=_MATIN)
        self.depart_id_2 = self._creneau(numero=2, horaire="14:00", depart_id=_APRES_MIDI)
        self.service = ServiceSuiviDeroule(
            tournoi_repository=self.tournois,  # type: ignore[arg-type]
            depart_repository=self.departs,
            phase_repository=self.phases,
            engages=self.engages,
            tableaux=self.tableaux,
        )

    def _creneau(self, numero: int, horaire: str, depart_id: int) -> int:
        depart = self.departs.ajouter(
            dataclasses.replace(
                Depart.creer(
                    tournoi_id=self.tournoi_id, numero=numero, tarif_centimes=800, horaire=horaire
                ),
                id=depart_id,
            )
        )
        assert depart.id is not None
        return depart.id

    def ajouter_phase(self, phase: Phase, phase_id: PhaseId) -> Phase:
        """Définit l'**étape** au tournoi puis y pose l'**avancement** du créneau (ADR-0076).

        Passe par `poser_phase_factice` : poser la seule phase laisserait le tournoi sans déroulé,
        et l'assemblage écarterait l'orpheline — le test échouerait pour une raison de décor.
        """
        return poser_phase_factice(
            self.departs, self.deroules, self.phases, dataclasses.replace(phase, id=phase_id)
        )


@pytest.fixture
def ctx() -> Contexte:
    return Contexte()


def _tableau_ed(depart_id: int, ordre: int, statut: StatutPhase) -> Phase:
    """Une élimination directe alimentée par les rangs 1..8 de la qualification."""
    phase = Phase.creer(
        depart_id=depart_id,
        ordre=ordre,
        type=TypePhase.ELIMINATION_DIRECTE,
        sources=(SourcePhase(ordre_source=1, rang_debut=1, rang_fin=8, nature=NatureSource.RANGS),),
        effectif=8,
    )
    if statut is StatutPhase.EN_COURS:
        return phase.demarrer()
    if statut is StatutPhase.TERMINEE:
        return phase.demarrer().terminer()
    return phase


# --- « le **même** schéma qu'à l'atelier » -------------------------------------------------------


def test_la_projection_est_celle_de_l_atelier(ctx: Contexte) -> None:
    """Le CA dit « le **même** schéma à braquets » : on ne recalcule pas, on réutilise `projeter`.

    Le test compare au résultat brut de `domain.deroule.projeter` sur les mêmes étapes et le même
    effectif — si un jour le suivi se mettait à dessiner autrement, il échouerait.
    """
    ctx.ajouter_phase(_qualification(ctx.depart_id), 1)
    ctx.ajouter_phase(_tableau_ed(ctx.depart_id, 2, StatutPhase.A_VENIR), 2)

    suivi = ctx.service.pour_depart(ctx.depart_id)

    attendue = projeter(ctx.phases.par_depart(ctx.depart_id), 8)
    assert suivi.projection == attendue
    assert suivi.effectif == 8


def test_toutes_les_phases_sont_suivies_meme_sans_braquet(ctx: Contexte) -> None:
    """Une qualification n'a pas de braquet : elle reste dans le suivi, avec son statut."""
    ctx.ajouter_phase(_qualification(ctx.depart_id, statut=StatutPhase.EN_COURS), 1)
    ctx.ajouter_phase(_tableau_ed(ctx.depart_id, 2, StatutPhase.A_VENIR), 2)

    suivi = ctx.service.pour_depart(ctx.depart_id)

    assert [b.ordre for b in suivi.avancement.blocs] == [1, 2]
    assert suivi.avancement.blocs[0].statut is StatutPhase.EN_COURS
    assert suivi.avancement.blocs[0].tours == ()
    assert suivi.avancement.ordre_courant == 1


# --- « duels joués sur duels attendus » -----------------------------------------------------------


def test_un_tableau_neuf_n_a_aucun_duel_joue(ctx: Contexte) -> None:
    ctx.ajouter_phase(_qualification(ctx.depart_id), 1)
    ctx.ajouter_phase(_tableau_ed(ctx.depart_id, 2, StatutPhase.EN_COURS), 2)
    ctx.tableaux.tableaux[2] = _tableau(8)

    bloc = ctx.service.pour_depart(ctx.depart_id).avancement.blocs[1]

    assert bloc.duels_joues == 0
    assert bloc.duels_attendus == 7
    assert bloc.tour_courant == 1


def test_les_duels_tranches_remplissent_leur_braquet(ctx: Contexte) -> None:
    """« braquets qui **se remplissent** au fur et à mesure »."""
    ctx.ajouter_phase(_qualification(ctx.depart_id), 1)
    ctx.ajouter_phase(_tableau_ed(ctx.depart_id, 2, StatutPhase.EN_COURS), 2)
    tableau = _tableau(8)
    ctx.tableaux.tableaux[2] = _jouer(
        tableau, [m.numero for m in tableau.matchs if m.tour == 1][:2]
    )

    bloc = ctx.service.pour_depart(ctx.depart_id).avancement.blocs[1]

    assert bloc.tours[0].duels_joues == 2
    assert bloc.tours[0].duels_attendus == 4
    assert bloc.tour_courant == 1


def test_la_petite_finale_ne_termine_pas_la_phase(ctx: Contexte) -> None:
    """**Non-régression** (trouvée par la revue adversariale) : le dernier tour a **deux** branches.

    Une élimination directe en placement (`PlacementEnCascade` + `ProfondeurPodium`) fait rejouer
    les perdants des demies : au dernier tour, il y a la **finale** (places 1-2) *et* la **petite
    finale** (places 3-4). Le braquet projeté, lui, ne suit que la branche des gagnants et n'annonce
    qu'**un** duel — c'est délibéré (E01US024), et le CA impose de garder *le même* schéma.

    Le défaut : en comptant les deux matchs sous le même numéro de tour, on obtenait « 2 joués sur 1
    attendu », plafonné à 1. La petite finale étant souvent tranchée **avant** la finale (ou en
    parallèle), l'écran projeté affichait « phase terminée · 7/7 duels » **pendant que la finale se
    tirait** — au moment de la journée où il est le plus regardé.

    Ce test joue la petite finale et **pas** la finale : c'est exactement le couple qui ouvrait le
    trou. Jouer tout le tableau ne prouverait rien, et n'en jouer qu'un tour non plus — ce que
    faisaient les tests d'origine.
    """
    ctx.ajouter_phase(_qualification(ctx.depart_id), 1)
    ctx.ajouter_phase(_tableau_ed(ctx.depart_id, 2, StatutPhase.EN_COURS), 2)
    tableau = _tableau(8)
    petite_finale = next(m.numero for m in tableau.matchs if m.place_en_jeu == (3, 4))
    # Tous les duels **sauf la finale** : les 4 du tour 1, les 2 demies, puis la petite finale.
    ordre = [m.numero for m in tableau.matchs if m.tour < 3] + [petite_finale]
    ctx.tableaux.tableaux[2] = _jouer(tableau, ordre)

    bloc = ctx.service.pour_depart(ctx.depart_id).avancement.blocs[1]

    # Le dernier braquet reste **ouvert** : la finale n'est pas tirée.
    assert bloc.tours[-1].duels_joues == 0
    assert bloc.tour_courant == 3
    assert bloc.duels_joues == 6
    assert bloc.duels_attendus == 7


def test_la_finale_tranchee_ferme_le_dernier_braquet(ctx: Contexte) -> None:
    """Le pendant du test précédent : c'est bien **la finale** qui clôt le dernier braquet."""
    ctx.ajouter_phase(_qualification(ctx.depart_id), 1)
    ctx.ajouter_phase(_tableau_ed(ctx.depart_id, 2, StatutPhase.EN_COURS), 2)
    tableau = _tableau(8)
    finale = next(m.numero for m in tableau.matchs if m.place_en_jeu == (1, 2))
    ordre = [m.numero for m in tableau.matchs if m.tour < 3] + [finale]
    ctx.tableaux.tableaux[2] = _jouer(tableau, ordre)

    bloc = ctx.service.pour_depart(ctx.depart_id).avancement.blocs[1]

    assert bloc.tours[-1].duels_joues == 1
    assert bloc.tour_courant is None
    assert bloc.duels_joues == bloc.duels_attendus == 7


def test_un_tableau_alimente_par_une_tranche_haute_compte_correctement() -> None:
    """**Non-régression** (2ᵉ passe adversariale) : deux systèmes de coordonnées, un seul comparé.

    `_braquets` produit des plages **absolues** (« un tableau des rangs 33-64 rend des perdants en
    49-64 ») ; `construire_tableau` produit des `Match.plage` **relatives au tableau**, toujours à
    partir de 1. La comparaison directe ne pouvait fonctionner que pour un tableau partant du rang 1
    — le seul cas que montaient toutes les fixtures, y compris celles ajoutées au premier correctif.

    Le comptage ne compare donc plus de **positions** : il apparie les braquets aux tours réels
    **par la fin**, et ne retient que la branche des gagnants, reconnue à sa **largeur** — une
    largeur est un nombre de rangs, donc indépendante du repère.

    Ce test tient les deux exigences à la fois : le compte avance sur une tranche haute, **et** la
    petite finale n'achève pas la phase.

    ⚠️ La première version montait une phase de type `PLACEMENT`. Fixture **irréelle**, relevée en
    3ᵉ passe : en production `ServiceSaisieDuels.reconstruire` refuse tout type autre
    qu'`ELIMINATION_DIRECTE`, donc une phase de placement rend **toujours** zéro duel — le test
    prouvait une arithmétique sur un chemin que le produit n'emprunte jamais.
    """
    ctx = Contexte(nb_engages=16)
    ctx.ajouter_phase(_qualification(ctx.depart_id), 1)
    tranche_haute = Phase.creer(
        depart_id=ctx.depart_id,
        ordre=2,
        type=TypePhase.ELIMINATION_DIRECTE,
        sources=(
            SourcePhase(ordre_source=1, rang_debut=9, rang_fin=16, nature=NatureSource.RANGS),
        ),
        effectif=8,
    ).demarrer()
    ctx.ajouter_phase(tranche_haute, 2)
    tableau = _tableau(8)
    petite_finale = next(m.numero for m in tableau.matchs if m.place_en_jeu == (3, 4))
    ctx.tableaux.tableaux[2] = _jouer(
        tableau, [m.numero for m in tableau.matchs if m.tour < 3] + [petite_finale]
    )

    bloc = ctx.service.pour_depart(ctx.depart_id).avancement.blocs[1]

    # Le décalage est appliqué : les six duels des deux premiers tours sont bien comptés.
    assert bloc.duels_joues == 6
    # Et la petite finale ne ferme pas le dernier braquet : la finale reste à tirer.
    assert bloc.tours[-1].duels_joues == 0
    assert bloc.tour_courant == 3


def test_une_phase_ne_se_termine_jamais_avant_sa_finale() -> None:
    """**LA propriété du suivi**, et celle que trois correctifs successifs ont manquée.

    Le format FFTA courant : qualification à 120, puis élimination directe déclarée « rangs 1-32 ».
    `# DETTE-028` fait que le tableau réel est ensemencé avec les **120** archers en lice — donc 7
    tours là où la projection en annonce 5. Les trois versions précédentes du comptage donnaient, à
    l'issue du 5ᵉ tour réel — **quatre duels restants, dont les demi-finales et la finale** —, un
    schéma **entièrement rempli** (`31/31`, plus aucun tour en cours) sur l'écran projeté.

    On ne vérifie donc pas un chiffre : on vérifie l'**invariant** qui compte pour le public — tant
    qu'un duel du dernier braquet n'est pas tiré, la phase n'est **pas** terminée. Et on le vérifie
    à chaque tour, parce que c'est la progression tour à tour qui a menti, pas l'état final.
    """
    ctx = Contexte(nb_engages=120)
    ctx.ajouter_phase(_qualification(ctx.depart_id), 1)
    phase = Phase.creer(
        depart_id=ctx.depart_id,
        ordre=2,
        type=TypePhase.ELIMINATION_DIRECTE,
        sources=(
            SourcePhase(ordre_source=1, rang_debut=1, rang_fin=32, nature=NatureSource.RANGS),
        ),
        effectif=32,
    ).demarrer()
    ctx.ajouter_phase(phase, 2)
    tableau = _tableau(120)
    dernier_tour = max(m.tour for m in tableau.matchs)

    precedent = 0
    for jusqu_au_tour in range(1, dernier_tour):
        tableau = _jouer(
            tableau,
            [m.numero for m in tableau.matchs if m.tour == jusqu_au_tour and not m.est_bye],
        )
        ctx.tableaux.tableaux[2] = tableau
        bloc = ctx.service.pour_depart(ctx.depart_id).avancement.blocs[1]

        # Tant que la finale n'est pas tirée, la phase reste ouverte — quel que soit le tour.
        assert bloc.tour_courant is not None, f"phase close au tour réel {jusqu_au_tour}"
        assert bloc.duels_joues < bloc.duels_attendus
        # Et l'avancement ne recule jamais.
        assert bloc.duels_joues >= precedent
        precedent = bloc.duels_joues

    # Le dernier tour réel porte la finale : là, et là seulement, le schéma se ferme.
    ctx.tableaux.tableaux[2] = _jouer(
        tableau, [m.numero for m in tableau.matchs if m.tour == dernier_tour and not m.est_bye]
    )
    bloc = ctx.service.pour_depart(ctx.depart_id).avancement.blocs[1]
    assert bloc.tour_courant is None
    assert bloc.duels_joues == bloc.duels_attendus


def test_un_tableau_plus_large_que_la_tranche_declaree_ne_reste_pas_bloque() -> None:
    """**Non-régression** (2ᵉ passe) : le compteur ne doit pas rester bloqué à zéro.

    `# DETTE-028` : un tableau est ensemencé avec *tous* les archers en lice, sans lire
    `Phase.sources`, alors que les braquets se calculent sur l'effectif **déclaré**. Une phase
    déclarant « rangs 1..8 » jouée à 12 archers a donc **quatre** tours réels contre trois projetés.

    ⚠️ Avec l'alignement **par la fin** (`_correspondance`), le **premier** tour réel ne remplit
    rien : les trois braquets sont les trois **derniers** tours. C'est voulu et c'est honnête — ce
    premier tour fait tirer des archers que le format déclaré ne comptait pas. La version d'origine
    de ce test affirmait l'inverse (« un duel du tour 1 doit compter ») : elle encodait la
    sémantique d'alors, pas une exigence du CA.

    Ce qu'on garde de sa valeur : après les tours qui, eux, correspondent, le suivi **avance** — il
    ne reste pas bloqué à zéro comme il l'avait fait après le premier correctif.
    """
    ctx = Contexte(nb_engages=12)
    ctx.ajouter_phase(_qualification(ctx.depart_id), 1)
    ctx.ajouter_phase(_tableau_ed(ctx.depart_id, 2, StatutPhase.EN_COURS), 2)
    tableau = _tableau(12)
    dernier = max(m.tour for m in tableau.matchs)
    ctx.tableaux.tableaux[2] = _jouer(
        tableau, [m.numero for m in tableau.matchs if m.tour < dernier and not m.est_bye]
    )

    bloc = ctx.service.pour_depart(ctx.depart_id).avancement.blocs[1]

    assert bloc.duels_joues > 0
    # La finale n'est pas tirée : la phase reste ouverte.
    assert bloc.tour_courant is not None


def test_un_exempt_n_est_pas_un_duel_joue() -> None:
    """Piège central : un tableau **incomplet** distribue des exempts, gagnés d'office.

    Les compter ferait afficher « premier tour terminé » avant que quiconque ait tiré — et la
    projection, elle, ne les compte pas (`_braquets` : « 24 duellistes dans un tableau de 32 →
    8 duels, 8 exemptés »). Les deux comptes doivent parler de la même chose.
    """
    ctx = Contexte(nb_engages=6)
    ctx.ajouter_phase(_qualification(ctx.depart_id), 1)
    phase = Phase.creer(
        depart_id=ctx.depart_id,
        ordre=2,
        type=TypePhase.ELIMINATION_DIRECTE,
        sources=(SourcePhase(ordre_source=1, rang_debut=1, rang_fin=6, nature=NatureSource.RANGS),),
        effectif=6,
    ).demarrer()
    ctx.ajouter_phase(phase, 2)
    ctx.tableaux.tableaux[2] = _tableau(6)

    bloc = ctx.service.pour_depart(ctx.depart_id).avancement.blocs[1]

    assert bloc.tours[0].duels_attendus == 2
    assert bloc.tours[0].duels_joues == 0
    assert bloc.tour_courant == 1


# --- Robustesse -----------------------------------------------------------------------------------


def test_un_creneau_inconnu_est_refuse(ctx: Contexte) -> None:
    """La garde porte sur le **créneau**, seule maille que le suivi sache lire (ADR-0075)."""
    with pytest.raises(DepartIntrouvable):
        ctx.service.pour_depart(9999)


def test_un_tournoi_sans_phase_rend_un_suivi_vide(ctx: Contexte) -> None:
    """Avant qu'un format soit appliqué, l'écran doit afficher « rien à suivre », pas planter."""
    suivi = ctx.service.pour_depart(ctx.depart_id)

    assert suivi.avancement.blocs == ()
    assert suivi.avancement.ordre_courant is None


def test_un_tableau_illisible_ne_fait_pas_tomber_le_suivi(ctx: Contexte) -> None:
    """Robustesse jour J : un tableau qu'on ne sait pas reconstruire (format changé, phase mal
    câblée) laisse un bloc **à zéro joué**, jamais une page d'erreur — l'écran de salle tourne
    en permanence et personne n'est devant pour le relancer.
    """
    ctx.ajouter_phase(_qualification(ctx.depart_id), 1)
    ctx.ajouter_phase(_tableau_ed(ctx.depart_id, 2, StatutPhase.EN_COURS), 2)
    # aucun tableau enregistré pour la phase 2 : le lecteur lèvera un KeyError

    bloc = ctx.service.pour_depart(ctx.depart_id).avancement.blocs[1]

    assert bloc.duels_joues == 0
    assert bloc.duels_attendus == 7


# --- Portée : le suivi est celui d'un créneau, jamais du tournoi (ADR-0075) ----------------------
#
# Ces quatre tests sont la **garde** posée avant correction : sur un décor mono-départ, un service
# lisant `PhaseRepository.par_tournoi` reste vert — « les phases du tournoi » et « celles du
# créneau » y sont la même liste. Ils échouent tous sur la version qui lisait à la maille tournoi.


def test_le_deroule_n_est_pas_affiche_en_double_sur_deux_creneaux(ctx: Contexte) -> None:
    """Deux créneaux qui rejouent le **même** déroulé de 2 étapes en affichent 2, pas 4.

    `par_tournoi` rend la **concaténation** de N suites 1..M : la lire comme une séquence dessinait
    le déroulé autant de fois qu'il y a de créneaux.
    """
    ctx.ajouter_phase(_qualification(ctx.depart_id), 1)
    ctx.ajouter_phase(_tableau_ed(ctx.depart_id, 2, StatutPhase.A_VENIR), 2)
    ctx.ajouter_phase(_qualification(ctx.depart_id_2), 3)
    ctx.ajouter_phase(_tableau_ed(ctx.depart_id_2, 2, StatutPhase.A_VENIR), 4)

    suivi = ctx.service.pour_depart(ctx.depart_id)

    assert [bloc.ordre for bloc in suivi.projection.blocs] == [1, 2]
    assert [bloc.ordre for bloc in suivi.avancement.blocs] == [1, 2]


def test_l_avancement_d_un_creneau_n_est_pas_ecrase_par_celui_de_l_autre(ctx: Contexte) -> None:
    """Le matin peut être en duels pendant que l'après-midi n'a pas commencé (ADR-0076 §5).

    L'indexation `{phase.ordre: phase}` sur la liste transverse écrasait silencieusement : le
    dernier créneau lu gagnait, et les deux surfaces affichaient le **même** avancement.
    """
    ctx.ajouter_phase(_qualification(ctx.depart_id, statut=StatutPhase.EN_COURS), 1)
    ctx.ajouter_phase(_qualification(ctx.depart_id_2, statut=StatutPhase.A_VENIR), 2)

    matin = ctx.service.pour_depart(ctx.depart_id)
    apres_midi = ctx.service.pour_depart(ctx.depart_id_2)

    assert matin.avancement.blocs[0].statut is StatutPhase.EN_COURS
    assert apres_midi.avancement.blocs[0].statut is StatutPhase.A_VENIR


def test_l_effectif_projete_est_celui_du_creneau_pas_du_tournoi(ctx: Contexte) -> None:
    """Un tableau se dimensionne sur les inscrits **du créneau**, pas sur la somme du tournoi.

    C'est le symptôme le plus coûteux du bug : quatre créneaux de 100 archers faisaient dessiner
    un tableau pour 400 — un déroulé que la salle ne peut pas jouer.
    """
    ctx.engages.regler(ctx.depart_id, 8)
    ctx.engages.regler(ctx.depart_id_2, 32)
    ctx.ajouter_phase(_qualification(ctx.depart_id), 1)
    ctx.ajouter_phase(_qualification(ctx.depart_id_2), 2)

    assert ctx.service.pour_depart(ctx.depart_id).effectif == 8
    assert ctx.service.pour_depart(ctx.depart_id_2).effectif == 32


def test_un_creneau_sans_phase_ne_voit_pas_celles_de_son_voisin(ctx: Contexte) -> None:
    """Le créneau de l'après-midi, pas encore composé, rend un suivi **vide**.

    À la maille tournoi il héritait du déroulé du matin — un écran affichant une qualification en
    cours sur un créneau où personne n'a encore tiré.
    """
    ctx.ajouter_phase(_qualification(ctx.depart_id, statut=StatutPhase.EN_COURS), 1)

    suivi = ctx.service.pour_depart(ctx.depart_id_2)

    assert suivi.avancement.blocs == ()
    assert suivi.avancement.ordre_courant is None
