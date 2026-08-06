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
from domain.depart import DepartId
from domain.phase import Phase, SequencePhases, TypePhase
from domain.ports import DepartRepository, PhaseRepository, TournoiRepository
from domain.tournoi import TournoiId


class ServiceBaremeQualification:
    """Cas d'usage du barème de qualification : lire, définir (preset FFTA ou valeurs libres)."""

    def __init__(
        self,
        tournois: TournoiRepository,
        phases: PhaseRepository,
        departs: DepartRepository,
    ) -> None:
        self._tournois = tournois
        self._phases = phases
        # La qualification vit **par départ** (ADR-0075) : sans les créneaux, ce service ne
        # saurait ni sur quoi écrire, ni combien de fois.
        self._departs = departs

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
                "Ce tournoi n'a aucun créneau : le barème se règle sur la qualification d'un "
                "départ. Créez au moins un départ avant de définir le barème."
            )
        # **Écriture en éventail** (E01US025, ADR-0075) : la portée sportive est le départ, donc la
        # qualification existe **par départ**. Régler « le barème du tournoi » l'écrit sur chacune —
        # se contenter d'un représentant laisserait les autres créneaux sur l'ancienne valeur, et la
        # divergence ne se verrait que le jour J, sur la tablette.
        for depart in departs:
            assert depart.id is not None, "Un départ relu du dépôt porte toujours son identifiant."
            self._definir_sur_depart(depart.id, bareme)
        # Le barème persisté est celui qu'on vient d'écrire (l'aller-retour ne le transforme pas) ;
        # le renvoyer directement évite de re-narrower `phase.bareme` (optionnel depuis E05US001,
        # mais toujours présent sur une qualification — ADR-0045 §2).
        return bareme

    def _definir_sur_depart(self, depart_id: DepartId, bareme: BaremeQualification) -> None:
        """Écrit le barème sur la qualification de **ce** départ, en la créant au besoin."""
        phase = self._phases.par_depart_et_type(depart_id, TypePhase.QUALIFICATION)
        if phase is not None:
            self._phases.enregistrer(phase.avec_bareme(bareme))
            return
        # Création. La qualification est la **première** phase de la séquence (ordre 1, E05US001).
        # Si des phases ont déjà été composées (l'écran « Phases » n'impose pas de définir le barème
        # d'abord), on les **décale d'un cran** pour lui faire place en tête : la qualification et
        # la composition de séquence sont **deux écrivains** de la même table `phase`, et celui-ci
        # ne doit pas contourner l'invariant `SequencePhases` — sans ce décalage, deux « ordre 1 »
        # coexisteraient et bloqueraient toute composition ultérieure (revue E05US001, axe D).
        # La séquence validée est bien celle **du départ** : mêler les phases de deux créneaux
        # produirait des ordres en doublon et ferait échouer une composition pourtant licite.
        qualification = Phase.qualification(depart_id, bareme)
        decalees = [_decaler_dun_cran(p) for p in self._phases.par_depart(depart_id)]
        SequencePhases(phases=(qualification, *decalees))  # valide l'ensemble avant d'écrire
        self._phases.ajouter(qualification)
        for phase_decalee in decalees:
            self._phases.enregistrer(phase_decalee)

    def _tournoi_existant(self, tournoi_id: TournoiId) -> None:
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")


def _decaler_dun_cran(phase: Phase) -> Phase:
    """Décale une phase d'un cran vers le bas (ordre +1) pour faire place à la qualification en
    tête. Les sources **suivent** : leur ancre `ordre_source` est incrémentée d'autant, toutes les
    phases se décalant du même cran, donc les références restent valides (E05US001).

    Depuis E05US010 une phase porte **plusieurs** prélèvements : ils se décalent tous, faute de quoi
    la séquence obtenue serait refusée (`SourceApresPhase`) ou, pire, pointerait la mauvaise phase.
    """
    decalee = phase.avec_ordre(phase.ordre + 1)
    if not phase.sources:
        return decalee
    return decalee.avec_sources(
        tuple(replace(source, ordre_source=source.ordre_source + 1) for source in phase.sources)
    )
