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

from application.classements import ServiceClassement
from application.erreurs import PhaseIntrouvable, PhasePasUnTableau, TournoiIntrouvable
from application.saisie_duels import ServiceSaisieDuels
from domain.categorie import CategorieId
from domain.erreurs import EffectifTableauInvalide
from domain.palmares import (
    Palmares,
    PositionPhase,
    ResultatPhase,
    calculer_palmares,
)
from domain.participant import GenreParticipant
from domain.phase import Phase, TypePhase
from domain.politiques import Aggregation, AgregationParQualification
from domain.ports import GenerateurPalmares, PhaseRepository, TournoiRepository
from domain.tournoi import TournoiId

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
        generateur: GenerateurPalmares,
        agregation: Aggregation | None = None,
    ) -> None:
        self._tournois = tournois
        self._phases = phases
        self._classements = classements
        self._saisie_duels = saisie_duels
        self._generateur = generateur
        # Politique de **départage des sortis au même tour** (ADR-0067), injectée par la
        # composition root — un format de tournoi est de la configuration (règle 2). Elle n'est pas
        # encore *réglable* par l'organisateur : `Phase` ne persiste aucune `config.policies`
        # générique (seul `barrage_jusqu_au` l'est, E06US003), donc il n'existe aucun champ où
        # écrire le choix. Injectable aujourd'hui, réglable le jour où les phases porteront leur
        # config — c'est un manque de **surface**, pas de conception.
        self._agregation = agregation if agregation is not None else AgregationParQualification()

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
        qualification = self._classements.pour_tournoi(tournoi_id)
        resultats = tuple(
            resultat
            for phase in self._phases.par_tournoi(tournoi_id)
            if phase.type in _TYPES_RECONSTRUCTIBLES
            if (resultat := self._resultat(tournoi_id, phase)) is not None
        )
        palmares = calculer_palmares(qualification, resultats, self._agregation)
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

    def _resultat(self, tournoi_id: TournoiId, phase: Phase) -> ResultatPhase | None:
        """Ce qu'une phase à tableau a décidé — `None` si elle n'a rien à dire (encore).

        Les trois échecs absorbés sont ceux d'un tableau **pas encore montable** : effectif
        insuffisant (`EffectifTableauInvalide`, comme le routage), phase disparue entre deux
        lectures, phase requalifiée. Le palmarès est **public et projeté en salle** : une phase
        vide de la séquence ne doit pas éteindre l'écran, elle doit simplement n'y rien ajouter —
        même parti que le filet d'E06US003 sur les barrages.
        """
        if phase.id is None:
            return None
        try:
            tableau, _lignes = self._saisie_duels.reconstruire(tournoi_id, phase.id)
        except (EffectifTableauInvalide, PhaseIntrouvable, PhasePasUnTableau):
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
        return ResultatPhase(ordre=phase.ordre, positions=positions)
