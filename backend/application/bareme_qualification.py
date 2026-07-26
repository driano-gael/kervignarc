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

from application.erreurs import TournoiIntrouvable
from domain.bareme import BaremeQualification
from domain.phase import Phase, SequencePhases, TypePhase
from domain.ports import PhaseRepository, TournoiRepository
from domain.tournoi import TournoiId


class ServiceBaremeQualification:
    """Cas d'usage du barème de qualification : lire, définir (preset FFTA ou valeurs libres)."""

    def __init__(self, tournois: TournoiRepository, phases: PhaseRepository) -> None:
        self._tournois = tournois
        self._phases = phases

    def bareme_du_tournoi(self, tournoi_id: TournoiId) -> BaremeQualification | None:
        """Renvoie le barème de qualification du tournoi, ou `None` s'il n'est pas encore défini.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas.
        """
        self._tournoi_existant(tournoi_id)
        phase = self._phases.par_tournoi_et_type(tournoi_id, TypePhase.QUALIFICATION)
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
        phase = self._phases.par_tournoi_et_type(tournoi_id, TypePhase.QUALIFICATION)
        if phase is not None:
            self._phases.enregistrer(phase.avec_bareme(bareme))
            # Le barème persisté est celui qu'on vient d'écrire (l'aller-retour ne le transforme
            # pas) ; le renvoyer directement évite de re-narrower `phase.bareme` (optionnel depuis
            # E05US001, mais toujours présent sur une qualification — ADR-0045 §2).
            return bareme
        # Création. La qualification est la **première** phase de la séquence (ordre 1, E05US001).
        # Si des phases ont déjà été composées (l'écran « Phases » n'impose pas de définir le barème
        # d'abord), on les **décale d'un cran** pour lui faire place en tête : la qualification et
        # la composition de séquence sont **deux écrivains** de la même table `phase`, et celui-ci
        # ne doit pas contourner l'invariant `SequencePhases` — sans ce décalage, deux « ordre 1 »
        # coexisteraient et bloqueraient toute composition ultérieure (revue E05US001, axe D).
        qualification = Phase.qualification(tournoi_id, bareme)
        decalees = [_decaler_dun_cran(p) for p in self._phases.par_tournoi(tournoi_id)]
        SequencePhases(phases=(qualification, *decalees))  # valide l'ensemble avant d'écrire
        self._phases.ajouter(qualification)
        for phase_decalee in decalees:
            self._phases.enregistrer(phase_decalee)
        return bareme

    def _tournoi_existant(self, tournoi_id: TournoiId) -> None:
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")


def _decaler_dun_cran(phase: Phase) -> Phase:
    """Décale une phase d'un cran vers le bas (ordre +1) pour faire place à la qualification en
    tête. La source **suit** : son ancre `ordre_source` est incrémentée d'autant, toutes les phases
    se décalant du même cran, donc les références restent valides (E05US001)."""
    decalee = phase.avec_ordre(phase.ordre + 1)
    if phase.source is None:
        return decalee
    return decalee.avec_source(replace(phase.source, ordre_source=phase.source.ordre_source + 1))
