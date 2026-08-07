"""Service applicatif Barème de qualification (E01US009 / ADR-0011).

Orchestre le domaine derrière les ports repository. Ne connaît ni HTTP, ni SQL, ni la file
d'écriture (sérialisation assurée en amont, côté API) ; il reste synchrone et pur
d'infrastructure.

Le barème de qualification d'un tournoi est porté par sa **phase** de type `qualification`
(introduite minimalement, ADR-0011). `definir` fait un **upsert** : il crée la phase de
qualification avec le barème si elle n'existe pas encore, sinon il met à jour son barème. Fait
remonter des erreurs typées (`TournoiIntrouvable`).

Depuis E01US015, la phase porte aussi un **grain de validation** (`config.validation`, `D-11`), et
l'agrégat garantit leur cohérence : réduire le barème **sous la cadence** du grain en place est
refusé (le grain ne validerait jamais). L'upsert n'est donc plus inconditionnel — cf. `definir`.
"""

from __future__ import annotations

from dataclasses import replace

from application.erreurs import TournoiIntrouvable, TournoiSansDepart
from application.portee import qualification_representative
from domain.bareme import BaremeQualification
from domain.deroule_etape import EtapeDeroule
from domain.phase import TypePhase, grain_par_defaut, verifier_sequence
from domain.ports import (
    DepartRepository,
    DerouleRepository,
    PhaseRepository,
    TournoiRepository,
)
from domain.tournoi import TournoiId


class ServiceBaremeQualification:
    """Cas d'usage du barème de qualification : lire, définir (preset FFTA ou valeurs libres)."""

    def __init__(
        self,
        tournois: TournoiRepository,
        phases: PhaseRepository,
        departs: DepartRepository,
        deroules: DerouleRepository,
    ) -> None:
        self._tournois = tournois
        self._phases = phases
        # La qualification vit **par départ** (ADR-0075) : sans les créneaux, ce service ne
        # saurait ni sur quoi écrire, ni combien de fois.
        self._departs = departs
        # Le barème vit sur l'**étape** du déroulé depuis ADR-0076 : une définition, pas N.
        self._deroules = deroules

    def bareme_du_tournoi(self, tournoi_id: TournoiId) -> BaremeQualification | None:
        """Renvoie le barème de qualification du tournoi, ou `None` s'il n'est pas encore défini.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas.
        """
        self._tournoi_existant(tournoi_id)
        phase = qualification_representative(self._phases, tournoi_id)
        return None if phase is None else phase.bareme

    def definir(
        self, tournoi_id: TournoiId, nb_volees: int, nb_fleches_par_volee: int
    ) -> BaremeQualification:
        """Définit (crée ou met à jour) le barème de qualification d'un tournoi.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas, `DomainError` si une grandeur du
        barème est invalide (`< 1`), et `CadenceValidationSuperieureAuBareme` (E01US015) si le
        nouveau barème compte **moins de volées que la cadence** du grain de validation en place —
        il faut alors élargir le grain d'abord.
        """
        self._tournoi_existant(tournoi_id)
        bareme = BaremeQualification.creer(nb_volees, nb_fleches_par_volee)
        departs = self._departs.par_tournoi(tournoi_id)
        if not departs:
            raise TournoiSansDepart(
                "Ce tournoi n'a aucun créneau : le barème se règle sur la qualification, et une "
                "qualification que personne ne joue n'aurait pas de sens. Créez au moins un départ."
            )

        # **Une seule écriture** depuis ADR-0076 : le barème vit sur l'étape du déroulé, définie une
        # fois pour le tournoi. Avant, il fallait l'écrire « en éventail » sur la qualification de
        # chaque créneau — et rien n'empêchait les copies de diverger.
        etapes = self._deroules.par_tournoi(tournoi_id)
        qualification = next((e for e in etapes if e.type is TypePhase.QUALIFICATION), None)
        if qualification is not None:
            self._deroules.enregistrer(replace(qualification, bareme=bareme))
            return bareme

        # Création. La qualification est la **première** étape du déroulé (ordre 1, E05US001). Si
        # des étapes ont déjà été composées (l'écran « Phases » n'impose pas de définir le barème
        # d'abord), on les **décale d'un cran** pour lui faire place en tête : le barème et la
        # composition sont **deux écrivains** du même déroulé, et celui-ci ne doit pas contourner
        # l'invariant `SequencePhases` — sans ce décalage, deux « ordre 1 » coexisteraient et
        # bloqueraient toute composition ultérieure (revue E05US001, axe D).
        neuve = EtapeDeroule(
            tournoi_id=tournoi_id,
            ordre=1,
            type=TypePhase.QUALIFICATION,
            bareme=bareme,
            validation=grain_par_defaut(TypePhase.QUALIFICATION),
        )
        decalees = [_decaler_dun_cran(e) for e in etapes]
        verifier_sequence([neuve, *decalees])  # valide l'ensemble avant d'écrire
        posee = self._deroules.ajouter(neuve)
        for etape_decalee in decalees:
            self._deroules.enregistrer(etape_decalee)

        # Les **avancements** suivent : une instance de la nouvelle étape dans chaque créneau, et
        # le rang des instances déjà posées se décale comme leur étape. C'est le seul éventail qui
        # subsiste, et il ne porte aucun réglage.
        for depart in departs:
            assert depart.id is not None, "Un départ relu du dépôt porte toujours son identifiant."
            for phase in self._phases.par_depart(depart.id):
                self._phases.enregistrer(phase.avec_ordre(phase.ordre + 1))
            self._phases.ajouter(posee.instancier(depart.id))
        return bareme

    def _tournoi_existant(self, tournoi_id: TournoiId) -> None:
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")


def _decaler_dun_cran(etape: EtapeDeroule) -> EtapeDeroule:
    """Décale une phase d'un cran vers le bas (ordre +1) pour faire place à la qualification en
    tête. Les sources **suivent** : leur ancre `ordre_source` est incrémentée d'autant, toutes les
    phases se décalant du même cran, donc les références restent valides (E05US001).

    Depuis E05US010 une phase porte **plusieurs** prélèvements : ils se décalent tous, faute de quoi
    la séquence obtenue serait refusée (`SourceApresPhase`) ou, pire, pointerait la mauvaise phase.
    """
    decalee = etape.avec_ordre(etape.ordre + 1)
    if not etape.sources:
        return decalee
    return decalee.avec_sources(
        tuple(replace(source, ordre_source=source.ordre_source + 1) for source in etape.sources)
    )
