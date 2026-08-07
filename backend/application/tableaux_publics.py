"""Lecture **publique** des tableaux d'un **créneau** (E07US005) — « voir les arbres en direct ».

Le CA d'E07US005 dit « rendu de l'arbre (**principal + placement**) mis à jour en live ». Ce
service est le côté serveur de cette phrase : il rend, pour un **départ**, **tous** ses arbres —
élimination directe *et* placement (`TYPES_EN_TABLEAU`, E05US010) — dans l'ordre du déroulé.

⚠️ **La maille est le créneau** depuis E01US025 (ADR-0075) : un départ rejoue le tournoi en entier,
donc chaque créneau a ses propres arbres, aux mêmes rangs. Lire à la maille tournoi les concaténait
sans marqueur d'origine — cf. `TableauxDuDepart`.

**Pourquoi un service à part et non une méthode de `ServiceSaisieDuels`.** `ServiceSaisieDuels` est
le service du **scoreur** : il saisit, il valide, et sa lecture `etat_tableau` est protégée par
`exiger_scoreur`. Y accrocher une lecture publique mêlerait deux audiences dans le même objet, et
c'est le genre de mélange qui finit par exposer au public un champ ajouté pour le scoreur. On suit
donc la forme déjà en place pour les autres lectures publiques dérivées du même arbre —
`ServiceRoutage` (E04US018/E07US008) et `ServiceSuiviDeroule` (E07US004) sont eux aussi des
services de lecture qui **consomment** `ServiceSaisieDuels` sans en faire partie.

⚠️ **La restriction du contenu n'est pas ici, elle est au DTO** (`api/v1/tableaux.py`, règle 6) :
ce service rend l'`EtatTableau` complet, la frontière API choisit ce que le public en voit. Le
partage est volontaire — le domaine et l'application n'ont pas à connaître la notion de « public ».
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from application.erreurs import ApplicationError, DepartIntrouvable
from application.saisie_duels import EtatTableau, ServiceSaisieDuels
from domain.depart import DepartId
from domain.erreurs import DomainError
from domain.phase import TYPES_EN_TABLEAU, PhaseId, TypePhase
from domain.ports import DepartRepository, PhaseRepository
from domain.tournoi import TournoiId

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TableauPublic:
    """Un arbre du tournoi : **quelle** phase (rang et type), et sa photo reconstruite.

    `ordre` et `type` plutôt qu'un libellé : une phase n'a pas de nom (`domain.phase.Phase`), et
    fabriquer « Élimination directe » ici mettrait du texte d'interface dans l'application alors que
    le front en tient déjà le catalogue (`shared/phases/catalogue.ts`). La règle 3 veut le même
    vocabulaire partout — le plus sûr moyen est qu'il n'existe qu'à un endroit.
    """

    phase_id: PhaseId
    ordre: int
    type: TypePhase
    etat: EtatTableau


@dataclass(frozen=True)
class TableauxDuDepart:
    """Tous les arbres lisibles d'un **créneau**, dans l'ordre du déroulé.

    ⚠️ **D'un créneau et non d'un tournoi** (E01US025, ADR-0075) : les phases pendent au départ, et
    deux créneaux portent chacun leur rang 2. À la maille tournoi, la liste rendait N tableaux
    d'`ordre` identique **sans rien pour les distinguer** — `TableauPublic` ne porte pas de
    `depart_id` —, donc un client incapable de dire de quel créneau il regardait l'arbre.
    """

    depart_id: DepartId
    tableaux: tuple[TableauPublic, ...]


class ServiceTableauxPublics:
    """Cas d'usage « voir les arbres du créneau » — lecture pure, publique, sans identité."""

    def __init__(
        self,
        departs: DepartRepository,
        phases: PhaseRepository,
        saisie: ServiceSaisieDuels,
    ) -> None:
        # `TournoiRepository` a disparu du câblage avec la bascule de maille : la garde d'existence
        # porte désormais sur le **créneau**, et le tournoi se lit sur le départ retrouvé. Garder le
        # repository « au cas où » aurait laissé une dépendance que rien n'exerce.
        self._departs = departs
        self._phases = phases
        self._saisie = saisie

    def pour_depart(self, depart_id: DepartId) -> TableauxDuDepart:
        """Les arbres de ce créneau. `DepartIntrouvable` si le créneau n'existe pas.

        Un créneau **sans phase en tableau** rend une liste vide plutôt qu'une erreur : l'onglet
        s'ouvre à 8 h du matin comme à 17 h, et « pas encore de tableau » est une réponse, pas une
        panne.

        # DETTE-031 : chaque appel **reconstruit** intégralement chaque tableau (classement complet
        # du départ, arbre rebâti, duels rejoués, forfaits appliqués) — et ici **une fois par
        # phase**, sur un endpoint public non authentifié pollé par autant d'appareils qu'il y a de
        # spectateurs. Régime assumé au contexte mono-club et local ; cf. docs/dette.md.
        """
        depart = self._departs.par_id(depart_id)
        if depart is None:
            raise DepartIntrouvable(f"Aucun départ d'identifiant {depart_id}.")
        phases = sorted(self._phases.par_depart(depart_id), key=lambda phase: phase.ordre)
        lisibles = []
        for phase in phases:
            if phase.type not in TYPES_EN_TABLEAU or phase.id is None:
                continue
            etat = self._etat_ou_rien(depart.tournoi_id, phase.id)
            if etat is not None:
                lisibles.append(
                    TableauPublic(phase_id=phase.id, ordre=phase.ordre, type=phase.type, etat=etat)
                )
        return TableauxDuDepart(depart_id=depart_id, tableaux=tuple(lisibles))

    def _etat_ou_rien(self, tournoi_id: TournoiId, phase_id: PhaseId) -> EtatTableau | None:
        """La photo d'un tableau, ou `None` s'il n'est **pas encore lisible**.

        Le matin, un déroulé composé pour 8 archers porte des phases dont la source ne prélève
        encore personne : le moteur refuse à juste titre de monter un arbre de moins de deux
        participants. Laisser remonter l'erreur donnerait une **page blanche** — sur une surface
        publique et projetée, pour tout le monde, à cause d'une phase qui n'a pas commencé.

        On avale donc l'échec **par phase**. La contrepartie est réelle et assumée : un tableau
        **cassé** est indiscernable d'un tableau **à venir** — les deux disparaissent de la liste.
        C'est le bon arbitrage **pour le spectateur** (il n'a rien à réparer), pas pour une surface
        d'administration ; le diagnostic de format, lui, vit à l'atelier (E01US024).

        ⚠️ **L'indiscernabilité s'arrête au client : le serveur, lui, journalise** (correctif de
        revue, relevé par quatre axes). Un premier jet copiait `ServiceSuiviDeroule._duels_tranches`
        — même tuple, aucun log. Le modèle juste est `ServicePalmares._resultat` (E06US004), même
        surface publique et projetée, dont la docstring dit exactement pourquoi : « une phase
        absente du palmarès le jour J serait sinon **indébogable** ». La conséquence est ici plus
        lourde que pour le suivi du déroulé, qui dégrade vers un bloc à zéro — **visible** : ici le
        tableau **disparaît**, de l'onglet public *et* de l'écran de salle, et sans trace personne
        ne peut relier les deux.

        `KeyError` est capturé **à part** et en `warning` : aucun code de ce chemin ne le lève
        délibérément (le domaine s'y refuse explicitement — `phase.py`, `politiques.py`, `poule.py`
        disent tous « explicite plutôt qu'un `KeyError` »). Un `KeyError` ici est donc un **défaut
        de programmation**, pas une phase à venir, et le confondre avec elle le rendrait invisible.
        """
        try:
            return self._saisie.etat_tableau(tournoi_id, phase_id)
        except (ApplicationError, DomainError) as exc:
            _logger.info("Tableau de la phase %s écarté de la vue publique : %s", phase_id, exc)
            return None
        except KeyError as exc:
            _logger.warning("Défaut interne sur la phase %s, tableau écarté : %r", phase_id, exc)
            return None
