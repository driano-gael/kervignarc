"""Service applicatif Palmarès (E06US004) — lecture du classement final d'un tournoi.

Cas d'usage de **lecture** : compose le classement de qualification (E06US001) et ce que chaque
phase à tableau a décidé, puis délègue la fusion à la fonction pure du domaine
(`calculer_palmares`). Sans écriture, il s'exécute hors de la file d'écriture (règle 7).

**Choix de câblage : service → service, comme le routage et le pilotage.** Reconstruire un tableau
(classement → arbre → rejeu des duels validés → forfaits appliqués) est une règle métier non
triviale que `ServiceSaisieDuels.reconstruire` porte déjà et que deux services consomment
(E12US002, E04US018/E07US008). La recoder par ports seuls la ferait **diverger** de la saisie : le
palmarès annoncerait un vainqueur que l'écran de duels ne montre pas. C'est la même exception que
`ServiceListesImpression` s'accorde sur `ServicePaiements.recap_par_club` — on duplique une
chaîne de ports, jamais une règle métier.

**Portée : qualification + phases à tableau.** Les autres types classants (`poules`, `suisse`,
`colline`, `big_shoot_off`) ont un moteur de domaine (E05US015) mais **aucun service ne les
déroule** (`# DETTE-028`) : il n'existe littéralement rien à lire. Ils entreront au palmarès sans
toucher au domaine — `calculer_palmares` ne connaît que des positions acquises.
"""

from __future__ import annotations

import logging

from application.classements import ServiceClassement
from application.erreurs import PhaseIntrouvable, TournoiIntrouvable, TournoiSansDepart
from application.portee import qualification_du_tournoi
from application.prelevement import tranche
from application.saisie_duels import ServiceSaisieDuels
from domain.categorie import CategorieId
from domain.depart import DepartId
from domain.erreurs import EffectifTableauInvalide
from domain.palmares import (
    Palmares,
    PositionPhase,
    ResultatPhase,
    calculer_palmares,
)
from domain.participant import GenreParticipant
from domain.phase import Phase, TypePhase
from domain.politiques import Aggregation, AggregationParQualification
from domain.ports import (
    DepartRepository,
    DuelRepository,
    GenerateurPalmares,
    PhaseRepository,
    TournoiRepository,
)
from domain.tournoi import TournoiId

_logger = logging.getLogger(__name__)

_TYPES_RECONSTRUCTIBLES = (TypePhase.ELIMINATION_DIRECTE,)
"""Les types de phase dont ce service sait lire le résultat aujourd'hui.

Une **liste blanche**, à rebours de `produit_un_classement` qui est écrit en négatif : là-bas
l'oubli probable est d'ajouter un vrai format (donc classant par défaut), ici c'est de croire lire
une phase dont aucun moteur ne déroule le résultat. Un type absent de cette liste ne casse pas le
palmarès — il n'y apporte simplement rien.
"""


class ServicePalmares:
    """Cas d'usage du palmarès : consulter le classement final d'un tournoi."""

    def __init__(
        self,
        tournois: TournoiRepository,
        phases: PhaseRepository,
        classements: ServiceClassement,
        saisie_duels: ServiceSaisieDuels,
        duels: DuelRepository,
        generateur: GenerateurPalmares,
        departs: DepartRepository,
        aggregation: Aggregation | None = None,
    ) -> None:
        self._tournois = tournois
        # Le classement — donc le palmarès — vit par départ depuis ADR-0075.
        self._departs = departs
        self._phases = phases
        self._classements = classements
        self._saisie_duels = saisie_duels
        # Lu pour une seule question : **un tir a-t-il été enregistré** dans cette phase ? Le
        # tableau reconstruit ne sait pas le dire — un match peut y porter un vainqueur sans
        # qu'une flèche ait été tirée (bye, walkover de forfait).
        self._duels = duels
        self._generateur = generateur
        # Politique de **départage des sortis au même tour** (ADR-0067), injectée par la
        # composition root — un format de tournoi est de la configuration (règle 2). Elle n'est pas
        # encore *réglable* par l'organisateur : `Phase` ne persiste aucune `config.policies`
        # générique (seul `barrage_jusqu_au` l'est, E06US003), donc il n'existe aucun champ où
        # écrire le choix. Injectable aujourd'hui, réglable le jour où les phases porteront leur
        # config — c'est un manque de **surface**, pas de conception.
        self._aggregation = (
            aggregation if aggregation is not None else AggregationParQualification()
        )

    def pour_tournoi(
        self, tournoi_id: TournoiId, categorie_id: CategorieId | None = None
    ) -> Palmares:
        """Renvoie le palmarès d'un tournoi, éventuellement **filtré** à une catégorie.

        Lève `TournoiIntrouvable` si le tournoi manque. Le calcul se fait **toujours en entier**
        (les rangs scratch et de catégorie sont ceux du tournoi complet) ; `categorie_id` ne fait
        que restreindre l'affichage — même parti qu'E06US001, pour ne pas transformer le 1ᵉʳ de sa
        catégorie en 1ᵉʳ tout court.
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        # Le palmarès d'un **départ** (ADR-0075) : il s'appuie sur le classement de qualification,
        # qui n'existe plus qu'à cette maille. Le premier départ qui en porte un fait référence
        # tant que la route reste au niveau tournoi — cf. DETTE-045.
        premier = self._premier_depart(tournoi_id)
        qualification = self._classements.pour_depart(premier)
        # ⚠️ **Les phases du même créneau que la qualification**, pas celles du tournoi. Le résultat
        # affiché ne changeait pas — `calculer_palmares` écarte les archers absents du classement de
        # référence —, mais on reconstruisait le tableau de **tous** les créneaux pour les jeter
        # ensuite : sur quatre départs, quatre fois le travail de `ServiceSaisieDuels.reconstruire`
        # (DETTE-031) sur deux routes **publiques**, l'écran et le PDF. Et le résultat n'était juste
        # que par ricochet : un archer engagé sur deux créneaux (cas soutenu, DETTE-046) pouvait se
        # voir attribuer la position acquise dans le tableau de l'autre créneau, les rangs se
        # répétant d'un départ à l'autre.
        resultats = tuple(
            resultat
            for phase in self._phases.par_depart(premier)
            if phase.type in _TYPES_RECONSTRUCTIBLES
            if (resultat := self._resultat(tournoi_id, phase)) is not None
        )
        palmares = calculer_palmares(qualification, resultats, self._aggregation)
        return palmares if categorie_id is None else palmares.pour_categorie(categorie_id)

    def imprimer(self, tournoi_id: TournoiId, categorie_id: CategorieId | None = None) -> bytes:
        """Rend le palmarès en **PDF** (CA « affiché et exportable »).

        Même calcul que `pour_tournoi` — un document qui divergerait de l'écran serait pire que
        pas de document du tout : c'est celui-là qu'on affiche au mur et qu'on remet aux archers.
        Le rendu part au port `GenerateurPalmares` ; le service ne connaît ni ReportLab ni HTTP.
        """
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        return self._generateur.palmares(tournoi.nom, self.pour_tournoi(tournoi_id, categorie_id))

    def _premier_depart(self, tournoi_id: TournoiId) -> DepartId:
        """Le premier créneau du tournoi — référence tant que la route reste au niveau tournoi.

        ⚠️ **Raccourci tracé (`DETTE-045`).** Le palmarès est rendu « du tournoi » alors que le
        classement dont il dérive est celui d'un **départ** : sur un tournoi multi-créneaux, il
        n'affiche donc que le podium du premier. La question métier qui bloquait la résorption —
        additionne-t-on les podiums de chaque créneau, ou les juxtapose-t-on ? — a été **tranchée
        par le commanditaire le 07/08/2026** : *juxtaposé*, quatre départs font quatre podiums. Il
        n'y a donc aucune agrégation à écrire, et le remède se réduit à une route par départ,
        planifiée en **E06US009**.
        """
        departs = self._departs.par_tournoi(tournoi_id)
        if not departs:
            raise TournoiSansDepart(
                "Ce tournoi n'a aucun créneau : il n'y a pas de classement dont tirer un palmarès."
            )
        premier = departs[0]
        assert premier.id is not None, "Un départ relu du dépôt porte toujours son identifiant."
        return premier.id

    def _resultat(self, tournoi_id: TournoiId, phase: Phase) -> ResultatPhase | None:
        """Ce qu'une phase à tableau a décidé — `None` si elle n'a **rien** décidé (encore).

        ⚠️ **Une phase qui n'a tranché aucun duel est écartée**, et c'est un correctif de revue
        relevé par trois axes. Le déroulé se compose à l'avance (E01US024), donc la phase de
        tableau existe **dès le matin** ; `_decor` l'ensemence alors avec tous les archers en lice
        (`# DETTE-028`), et chacun n'a acquis que la plage de son premier match — c'est-à-dire le
        tableau **entier**. Le palmarès affichait donc « 1ᵉʳ-120ᵉ · à départager » sur 120 lignes,
        pendant toute la qualification, sur l'onglet public et l'écran de salle.

        Le critère est **ce que le tableau a décidé**, pas `phase.statut` : le passage à `en_cours`
        est une action **manuelle** de l'organisateur (`ServicePhases.demarrer`), et faire dépendre
        un écran public de sa discipline le laisserait muet tout l'après-midi s'il l'oublie. Un
        tableau dont un duel est tranché a forcément commencé ; la lecture est auto-corrective.

        Deux choses ne comptent pas, et les distinguer a demandé une contre-revue : un **bye**
        avance un archer sans que rien ne se soit joué, et un **walkover de forfait**
        (`_appliquer_forfaits`, ADR-0050) fait de même sur un match qui n'est pourtant **pas**
        un bye. `est_bye` seul laissait donc revenir la régression dès qu'un organisateur
        enregistrait un forfait le matin — geste que le produit encourage. D'où le second
        critère : **un tir enregistré**. Aucun tir, aucun duel, quelle que soit la façon dont
        l'arbre s'est avancé tout seul.

        ⚠️ Le correctif symétrique proposé en revue — écarter côté domaine toute position couvrant
        le tableau entier — a été **écarté** : il casserait le milieu de tour. Après le premier
        duel d'un tableau de 8, six archers n'ont encore rien acquis (`[1..8]`) ; les faire retomber
        sur la qualification les classerait **derrière le battu** qu'ils n'ont pas rencontré.

        Les échecs absorbés sont ceux d'un tableau pas encore montable : effectif insuffisant
        (`EffectifTableauInvalide`, comme le routage) et phase disparue entre deux lectures. Le
        palmarès est **public et projeté en salle** : une phase de la séquence ne doit pas éteindre
        l'écran, elle doit simplement n'y rien ajouter — même parti que le filet d'E06US003. Ils
        sont **journalisés** : une phase absente du palmarès le jour J serait sinon indébogable.
        `PhasePasUnTableau` n'y figure plus — `pour_tournoi` filtre déjà sur le type, la garde était
        morte et une garde morte finit par masquer autre chose.
        """
        if phase.id is None:
            return None
        # DETTE-031 : cette lecture appelle `ServiceSaisieDuels.reconstruire` — tout le classement
        # du tournoi, l'arbre rebâti, les duels rejoués — **une fois par phase à tableau**, sans
        # cache et sans plafond, sur deux routes publiques non authentifiées (dont le PDF).
        try:
            tableau, _lignes = self._saisie_duels.reconstruire(tournoi_id, phase.id)
        except (EffectifTableauInvalide, PhaseIntrouvable) as exc:
            _logger.info("Phase %s écartée du palmarès : %s", phase.id, exc)
            return None
        if not self._duels.numeros_enregistres(phase.id):
            return None
        if not any(match.vainqueur is not None and not match.est_bye for match in tableau.matchs):
            return None
        positions = tuple(
            PositionPhase(
                archer_id=participant.ref_id,
                rang_min=acquise.rang_min,
                rang_max=acquise.rang_max,
                en_lice=acquise.en_lice,
            )
            for participant, acquise in tableau.positions_acquises().items()
            # Les participants **équipe** (E13US002) sont écartés : leur `ref_id` n'est pas un
            # archer, et le palmarès classe des archers. La résolution équipe → ligne viendra avec
            # les équipes elles-mêmes, comme pour le routage.
            if participant.genre is GenreParticipant.INDIVIDUEL
        )
        # ⚠️ La **tranche** que cette phase dispute (E05US020, ADR-0068 §5) : une consolante
        # prélevant « les rangs 5 et suivants » joue pour la 5ᵉ place, pas pour la victoire. Sans
        # ce décalage, son vainqueur passait devant le finaliste du tableau principal — c'était
        # `DETTE-034`, inatteignable tant qu'aucun moteur ne consommait les prélèvements.
        qualification = qualification_du_tournoi(self._phases, tournoi_id)
        rang_premier = tranche(
            phase,
            self._classements.pour_depart(phase.depart_id),
            qualification.ordre if qualification is not None else None,
        )
        return ResultatPhase(ordre=phase.ordre, positions=positions, rang_premier=rang_premier)
