"""Barème de qualification — porté par l'**étape** du déroulé (ADR-0011, ADR-0076).

⚠️ **Un déroulé peut porter PLUSIEURS qualifications** (ADR-0082) : « le barème du tournoi » n'a
plus de sens en général. `definir_pour_etape` règle une étape désignée ; les méthodes historiques
restent, justes tant qu'il n'y en a qu'une. ⚠️ Réduire le barème **sous la cadence** du grain en
place est refusé — le grain ne validerait jamais.
"""

from __future__ import annotations

from dataclasses import replace

from application.erreurs import (
    PhaseIntrouvable,
    PhasePasUneQualification,
    TournoiIntrouvable,
    TournoiSansDepart,
)
from domain.bareme import BaremeQualification
from domain.deroule_etape import EtapeDeroule, EtapeDerouleId, vues_du_deroule
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

    def qualifications(self, tournoi_id: TournoiId) -> list[EtapeDeroule]:
        """Les étapes de **qualification** du déroulé, dans l'ordre de la séquence.

        Ce que l'écran « Barème & validation » doit lister depuis E05US025 (ADR-0082) : un déroulé
        peut en porter plusieurs — 3x20, puis une *haute* et une *basse* à 3x15 —, chacune avec ses
        propres réglages. Liste éventuellement vide (aucune qualification composée).

        Lève `TournoiIntrouvable` si le tournoi n'existe pas.
        """
        self._tournoi_existant(tournoi_id)
        return [
            e for e in self._deroules.par_tournoi(tournoi_id) if e.type is TypePhase.QUALIFICATION
        ]

    # DETTE-053 : le nom promet un réglage de tournoi, le code rend celui de la première phase.
    def bareme_du_tournoi(self, tournoi_id: TournoiId) -> BaremeQualification | None:
        """Le barème de la **première** qualification, ou `None` si aucune n'est encore définie.

        ⚠️ **Le nom ment depuis E05US025** : un barème appartient à une **étape** (ADR-0082), et un
        déroulé peut en porter plusieurs. Conservée parce que la route historique la sert et que
        l'immense majorité des tournois n'a qu'une qualification — pour être juste sur un déroulé
        composé, passer par `qualifications`. Lève `TournoiIntrouvable`.
        """

        # Lu sur le **déroulé** (ADR-0076) : c'est là que le barème est défini. Le lire sur une
        # phase passerait par l'assemblage de l'adapter — exact, mais indirect, et surtout faux tant
        # qu'aucun créneau n'existe encore.
        qualifications = self.qualifications(tournoi_id)
        return qualifications[0].bareme if qualifications else None

    def definir_pour_etape(
        self,
        tournoi_id: TournoiId,
        etape_id: EtapeDerouleId,
        nb_volees: int,
        nb_fleches_par_volee: int,
    ) -> BaremeQualification:
        """Règle le barème d'une **étape désignée** (E05US025, ADR-0082).

        Le geste que réclame le CA « le barème se règle par qualification » : la tête tire 3x20,
        les deux suivantes 3x15. **Aucune création ici** — l'étape doit exister ; seul le chemin
        historique de `definir` fabrique une qualification. Lève `TournoiIntrouvable`,
        `PhaseIntrouvable`, `PhasePasUneQualification` (409),
        `CadenceValidationSuperieureAuBareme`.
        """
        self._tournoi_existant(tournoi_id)
        bareme = BaremeQualification.creer(nb_volees, nb_fleches_par_volee)
        etape = next((e for e in self._deroules.par_tournoi(tournoi_id) if e.id == etape_id), None)
        if etape is None:
            raise PhaseIntrouvable(
                f"Aucune étape d'identifiant {etape_id} dans le déroulé du tournoi {tournoi_id}."
            )
        if etape.type is not TypePhase.QUALIFICATION:
            raise PhasePasUneQualification(
                f"L'étape {etape_id} est de type « {etape.type.value} » : un barème de série ne se "
                "règle que sur une qualification."
            )
        # `replace` sur l'agrégat : c'est lui qui refuse un barème sous la cadence du grain en place
        # (`CadenceValidationSuperieureAuBareme`, E01US015). Contourner par une écriture directe
        # rendrait le grain inopérant sans le dire.
        self._deroules.enregistrer(replace(etape, bareme=bareme))
        return bareme

    def definir(
        self, tournoi_id: TournoiId, nb_volees: int, nb_fleches_par_volee: int
    ) -> BaremeQualification:
        """Définit (crée ou met à jour) le barème de la **première** qualification d'un tournoi.

        Chemin historique, et **le seul qui crée** une qualification : c'est par lui que passe la
        configuration d'un tournoi neuf, dont le déroulé est vide. Une fois le déroulé composé,
        régler une qualification précise passe par `definir_pour_etape`. Lève `TournoiIntrouvable`,
        `DomainError` (`< 1`), et `CadenceValidationSuperieureAuBareme` — élargir le grain d'abord.
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
        decalees = [e.avec_ordre(e.ordre + 1) for e in etapes]
        verifier_sequence(vues_du_deroule([neuve, *decalees]))  # valide l'ensemble avant d'écrire
        # ⚠️ **Seul le rang bouge** (ADR-0078). Les prélèvements des étapes décalées citent des
        # identités, qui ne changent pas ; les avancements citent l'identité de leur étape, donc
        # ils n'ont rien à suivre non plus. Jusqu'à cette US il fallait incrémenter chaque ancre
        # de source **et** réaligner le rang des phases de chaque créneau.
        self._deroules.enregistrer_plusieurs(decalees)
        posee = self._deroules.ajouter(neuve)

        # Le seul éventail qui subsiste : une instance de la nouvelle étape dans chaque créneau.
        for depart in departs:
            assert depart.id is not None, "Un départ relu du dépôt porte toujours son identifiant."
            self._phases.ajouter(posee.instancier(depart.id))
        return bareme

    def _tournoi_existant(self, tournoi_id: TournoiId) -> None:
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
