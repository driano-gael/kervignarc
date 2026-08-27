"""Lecture **publique** des tableaux — la maille est le **créneau**, pas le tournoi (ADR-0075).
Service à part de `ServiceSaisieDuels`, qui est celui du scoreur : mêler deux audiences dans le même
objet finirait par exposer au public un champ ajouté pour la saisie.

⚠️ **La restriction du contenu n'est PAS ici, elle est au DTO** (règle 6) : ce service rend l'état
complet, la frontière API choisit ce que le public en voit.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from application.erreurs import ApplicationError, DepartIntrouvable, PrelevementEnAttente
from application.saisie_duels import EtatTableau, ServiceSaisieDuels
from domain.depart import DepartId
from domain.erreurs import DomainError
from domain.phase import TYPES_EN_TABLEAU, PhaseId, TypePhase
from domain.ports import DepartRepository, PhaseRepository

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TableauPublic:
    """Un arbre du tournoi : **quelle** phase (rang et type), et sa photo reconstruite.

    `ordre` et `type` plutôt qu'un libellé : une phase n'a pas de nom, et fabriquer « Élimination
    directe » ici mettrait du texte d'interface dans l'application alors que le front en tient le
    catalogue (règle 3). ⚠️ **`etat` est facultatif depuis ADR-0081** : une phase qui prélève des
    places non encore attribuées n'a pas d'arbre à montrer, `attente` portant alors l'ordre de la
    source. Les deux champs sont mutuellement exclusifs.
    """

    phase_id: PhaseId
    ordre: int
    type: TypePhase
    etat: EtatTableau | None = None
    attente: int | None = None

    def __post_init__(self) -> None:
        # L'invariant ci-dessus était énoncé en prose et vérifiable nulle part (relevé par trois
        # axes) : les deux champs ayant `None` pour défaut, un `TableauPublic` **ni monté ni en
        # attente** se construisait sans erreur, et le DTO le rendait alors en zéros sans
        # `en_attente_de` — soit « 0 archers » plus un arbre vide, le seul état que le front ne
        # sait pas lire. Un invariant de frontière API se garde là où il est bon marché.
        if (self.etat is None) == (self.attente is None):
            raise ValueError(
                "Un tableau public porte soit son arbre, soit l'ordre de la phase qu'il attend."
            )


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

        Un créneau **sans phase en tableau** rend une liste vide plutôt qu'une erreur : « pas
        encore de tableau » est une réponse, pas une panne. ⚠️ `# DETTE-031` : chaque appel
        **reconstruit** intégralement chaque tableau, **une fois par phase**, sur un endpoint
        public non authentifié pollé par autant d'appareils qu'il y a de spectateurs. Régime assumé
        (mono-club, local).
        """
        depart = self._departs.par_id(depart_id)
        if depart is None:
            raise DepartIntrouvable(f"Aucun départ d'identifiant {depart_id}.")
        phases = sorted(self._phases.par_depart(depart_id), key=lambda phase: phase.ordre)
        lisibles = []
        for phase in phases:
            if phase.type not in TYPES_EN_TABLEAU or phase.id is None:
                continue
            # Trois issues (E05US024, ADR-0081) : un arbre lisible, une phase **en attente** de sa
            # source, ou un échec avalé. Le matin, une source ne prélève encore personne et le
            # moteur refuse un arbre de moins de deux participants ; laisser remonter l'erreur
            # donnerait une **page blanche** sur une surface publique et projetée. On avale donc
            # l'échec **par phase, en le journalisant** — une phase absente le jour J serait sinon
            # indébogable (modèle : `ServicePalmares._resultat`). Un tableau **cassé** reste
            # indiscernable d'un tableau à venir, bon arbitrage pour le spectateur ; le diagnostic
            # vit à l'atelier. `KeyError` est capturé à part, en `warning` : c'est un défaut.
            try:
                etat = self._saisie.etat_tableau(depart.tournoi_id, phase.id)
            except PrelevementEnAttente as exc:
                lisibles.append(
                    TableauPublic(
                        phase_id=phase.id,
                        ordre=phase.ordre,
                        type=phase.type,
                        attente=exc.ordre_source,
                    )
                )
                continue
            except (ApplicationError, DomainError) as exc:
                _logger.info("Tableau de la phase %s écarté de la vue publique : %s", phase.id, exc)
                continue
            except KeyError as exc:
                _logger.warning(
                    "Défaut interne sur la phase %s, tableau écarté : %r", phase.id, exc
                )
                continue
            lisibles.append(
                TableauPublic(phase_id=phase.id, ordre=phase.ordre, type=phase.type, etat=etat)
            )
        return TableauxDuDepart(depart_id=depart_id, tableaux=tuple(lisibles))
