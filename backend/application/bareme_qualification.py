"""Service applicatif Barème de qualification (E01US009 / ADR-0011).

Orchestre le domaine derrière les ports repository. Ne connaît ni HTTP, ni SQL, ni la file
d'écriture (sérialisation assurée en amont, côté API) ; il reste synchrone et pur
d'infrastructure.

Le barème est porté par l'**étape** de type `qualification` du déroulé (ADR-0011, puis ADR-0076
qui l'a sortie de la phase). `definir` fait un **upsert** sur la première : il crée la
qualification avec son barème si le déroulé n'en a pas, sinon il met à jour la sienne. Fait
remonter des erreurs typées (`TournoiIntrouvable`).

⚠️ **Depuis E05US025 (ADR-0082), un déroulé peut porter plusieurs qualifications** : parler du
« barème du tournoi » n'a plus de sens en général. `definir_pour_etape` règle une étape
**désignée** et `qualifications` les liste — c'est ce que consomme l'écran. Les deux méthodes
historiques restent, servies par les routes d'origine et justes tant qu'il n'y a qu'une
qualification, ce qui est le cas de la quasi-totalité des tournois.

Depuis E01US015, la phase porte aussi un **grain de validation** (`config.validation`, `D-11`), et
l'agrégat garantit leur cohérence : réduire le barème **sous la cadence** du grain en place est
refusé (le grain ne validerait jamais). L'upsert n'est donc plus inconditionnel — cf. `definir`.
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

    def bareme_du_tournoi(self, tournoi_id: TournoiId) -> BaremeQualification | None:
        """Le barème de la **première** qualification, ou `None` si aucune n'est encore définie.

        ⚠️ **Le nom ment depuis E05US025** : un barème n'appartient plus au tournoi mais à une
        **étape** (ADR-0082), et un déroulé peut en porter plusieurs. La méthode est conservée
        telle quelle parce que la route historique `GET /tournois/{id}/bareme-qualification` la sert
        et que l'immense majorité des tournois n'a qu'une qualification — mais tout appelant qui
        veut être juste sur un déroulé composé passe par `qualifications`.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas.
        """
        # Lu sur le **déroulé** (ADR-0076) : c'est là que le barème est défini. Le lire sur une
        # phase passerait par l'assemblage de l'adapter — exact, mais indirect, et surtout faux tant
        # qu'aucun créneau n'existe encore.
        qualifications = self.qualifications(tournoi_id)
        return qualifications[0].bareme if qualifications else None

    def definir_pour_etape(
        self, tournoi_id: TournoiId, etape_id: int, nb_volees: int, nb_fleches_par_volee: int
    ) -> BaremeQualification:
        """Règle le barème d'une **étape désignée** (E05US025, ADR-0082).

        C'est le geste que réclame le CA « le barème se règle par qualification » : sur le déroulé
        de référence, la qualification de tête tire 3x20 et les deux suivantes 3x15. Aucune création
        ici — l'étape doit exister, composée à l'atelier ; ce service ne fabrique une qualification
        que dans le chemin historique de `definir`.

        Lève `TournoiIntrouvable`, `PhaseIntrouvable` si l'étape n'appartient pas à ce tournoi,
        `PhasePasUneQualification` si elle n'en est pas une (409 : un tableau n'a pas de barème de
        série), et `CadenceValidationSuperieureAuBareme` si le nouveau barème compte moins de volées
        que la cadence du grain en place.
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
        configuration d'un tournoi neuf, dont le déroulé est encore vide. Une fois le déroulé
        composé, régler une qualification **précise** passe par `definir_pour_etape` (E05US025).

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
        # ⚠️ **Décaler d'abord, insérer ensuite.** Un tournoi ne porte qu'une étape par rang : poser
        # la qualification en tête avant d'avoir libéré le rang 1 heurterait cette unicité. Le
        # décalage passe par `reordonner`, l'écriture d'ensemble du port — le faire étape par étape
        # produirait le même doublon transitoire, un cran plus bas.
        self._deroules.reordonner(decalees)
        posee = self._deroules.ajouter(neuve)

        # Les **avancements** suivent, au même ordre de gestes : une instance de la nouvelle étape
        # dans chaque créneau, et le rang des instances déjà posées décalé comme leur étape. C'est
        # le seul éventail qui subsiste, et il ne porte aucun réglage.
        for depart in departs:
            assert depart.id is not None, "Un départ relu du dépôt porte toujours son identifiant."
            a_decaler = [p.avec_ordre(p.ordre + 1) for p in self._phases.par_depart(depart.id)]
            if a_decaler:
                self._phases.reordonner(a_decaler)
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
