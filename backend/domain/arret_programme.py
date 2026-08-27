"""Arrêts du déroulé — trois natures séparées (ADR-0076, ADR-0091, ADR-0092) : `ArretProgramme`
est une **définition** que tous les départs rejouent, `ArretDeCirconstance` une **décision de
conduite** propre à un créneau, `FranchissementArret` un **état** persisté.

⚠️ **Le franchissement doit être PERSISTÉ**, contrairement au reste de l'avancement (ADR-0090 §5) :
la condition est **monotone**. Un déclencheur sans mémoire remettrait la phase en pause à chaque
reprise, et la salle ne repartirait jamais.
"""

from __future__ import annotations

import datetime
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, replace
from enum import Enum

from domain.contrat_phase import TYPES_ARRETABLES, TypePhase
from domain.depart import DepartId
from domain.erreurs import ArretProgrammeInvalide
from domain.phase import PhaseId

__all__ = [
    "ArretDeCirconstance",
    "ArretProgramme",
    "EtatFranchissement",
    "FranchissementArret",
    "PorteeArret",
    "arrets_applicables",
    "arrets_atteints",
    "phases_a_arreter",
    "tour_d_un_arret_relatif",
    "verifier_arrets",
    "verifier_type_arretable",
]


class PorteeArret(str, Enum):
    """Ce que l'arrêt éteint : cette phase seule, ou tout ce qui tire dans le créneau.

    Le **départ** est la portée sportive du projet (ADR-0075) et correspond à « ce qui tire en
    salle en ce moment ». Le statut du **tournoi** n'est pas une portée d'arrêt : il a sa propre
    pause, à une autre maille (ADR-0026 §3), et les confondre mélangerait « la salle s'arrête dix
    minutes » et « la compétition est suspendue ».
    """

    PHASE = "phase"
    DEPART = "depart"


class EtatFranchissement(str, Enum):
    """Où en est un arrêt atteint. Cycle **monotone**, comme celui d'une phase (ADR-0045).

    `ARME` — le tour déclencheur est atteint, les phases s'arrêteront à la fin de leur tour courant
    (transitoire, et seul un arrêt de portée **départ** y séjourne) ; `FRANCHI` — toutes les phases
    sont en pause, l'arrêt attend un geste d'admin ; `LEVE` — consommé, il ne se redéclenche plus.
    ⚠️ Il n'y a **pas** d'état « programmé » : c'est l'**absence** de franchissement. L'ajouter
    obligerait à écrire une ligne par arrêt dès la composition, ce qu'ADR-0076 a supprimé.
    """

    ARME = "arme"
    FRANCHI = "franchi"
    LEVE = "leve"


@dataclass(frozen=True)
class ArretProgramme:
    """Une coupe **prévue** : après quel tour, et jusqu'où elle porte.

    Pas d'identifiant : un arrêt est identifié par son `apres_tour` au sein de son étape, et deux
    arrêts après le même tour sont refusés (`verifier_arrets`). C'est la même économie que
    `SourcePhase` — un value object de configuration, pas une entité.
    """

    apres_tour: int
    portee: PorteeArret = PorteeArret.PHASE

    def __post_init__(self) -> None:
        """Fait respecter l'invariant quelle que soit la porte d'entrée (`replace()` compris)."""
        if self.apres_tour < 1:
            raise ArretProgrammeInvalide(
                f"un arrêt se pose après un tour existant, pas après le tour {self.apres_tour}"
            )


@dataclass(frozen=True)
class FranchissementArret:
    """La trace d'un arrêt **atteint** dans un créneau donné, et de ce qu'il a coupé.

    `phase_id` est la phase **déclenchante** ; le couple (`phase_id`, `apres_tour`) porte l'unicité
    en base. `tours_a_finir` n'est peuplé que pour une portée **départ** : la photo, prise à
    l'armement, du tour que chaque autre phase avait en cours. ⚠️ `arrete_depuis` est l'instant de
    la **première** extinction : ré-horodater ferait *rajeunir* la pastille, qui annoncerait «
    depuis 1 min » sur une salle arrêtée depuis vingt.
    """

    phase_id: PhaseId
    apres_tour: int
    etat: EtatFranchissement
    tours_a_finir: tuple[tuple[PhaseId, int | None], ...] = ()
    phases_arretees: tuple[PhaseId, ...] = ()
    arrete_depuis: datetime.datetime | None = None
    id: int | None = None

    def franchir(self, phases_arretees: Sequence[PhaseId]) -> FranchissementArret:
        """Constate que toutes les phases concernées sont en pause.

        Refuse de revenir d'un arrêt déjà `LEVE` : le cycle est monotone. Sans ce refus, une
        évaluation du déclencheur tombant après une reprise re-franchirait l'arrêt, ce qui est
        exactement la boucle infinie que l'en-tête de ce module décrit.
        """
        if self.etat is EtatFranchissement.LEVE:
            raise ArretProgrammeInvalide(
                "un arrêt levé ne se re-franchit pas : la phase est repartie en automatique"
            )
        return replace(
            self, etat=EtatFranchissement.FRANCHI, phases_arretees=tuple(phases_arretees)
        )

    def lever(self) -> FranchissementArret:
        """Le geste de l'admin : la salle repart. Les phases à relancer sont `phases_arretees`.

        Refuse un second levage — un arrêt déjà consommé n'a plus de phase à rendre, et le tolérer
        ferait d'un double-clic une relance de phases que l'organisateur avait suspendues depuis.
        """
        if self.etat is EtatFranchissement.LEVE:
            raise ArretProgrammeInvalide("cet arrêt a déjà été levé")
        return replace(self, etat=EtatFranchissement.LEVE)


def verifier_type_arretable(type_phase: TypePhase) -> None:
    """Refuse une pause sur un type dont l'application ne lit pas le tour (périmètre du 19/08/2026).

    ⚠️ **Hissée ici en E05US034 parce qu'il existe deux portes d'entrée** — l'atelier et le
    pilotage : la laisser sur l'étape aurait fait réécrire le test de type par la seconde. Le
    déclencheur ne coupe qu'à une frontière de tour **observée**, donc sur un type illisible
    l'arrêt serait accepté puis inerte. ⚠️ L'oracle est `TYPES_ARRETABLES`, **non**
    `TYPES_DEROULES` : la qualification les sépare depuis E05US035.
    """
    if type_phase not in TYPES_ARRETABLES:
        raise ArretProgrammeInvalide(
            # ⚠️ **L'énumération est un texte d'UTILISATEUR : elle doit suivre `TYPES_ARRETABLES`
            # à chaque US qui l'élargit.** Elle omettait la colline après E05US027, si bien qu'un
            # organisateur se voyant refuser une pause lisait une liste où le format qu'il venait
            # de régler ne figurait pas — un refus qui désigne un cul-de-sac au lieu d'une issue
            # (`P-3`). Relevé par l'axe adversarial en 2ᵉ passe.
            f"Une phase de type « {type_phase.value} » n'annonce pas ses tours : l'application "
            "ne saurait pas quand y appliquer une pause. Les pauses se posent sur une "
            "qualification découpée en tours, une élimination directe, des poules, un système "
            "suisse, un Big Shoot Off ou une colline."
        )


def doublon_d_arret(tours: Sequence[int]) -> ArretProgrammeInvalide:
    """Le refus « deux arrêts au même endroit », **composé une seule fois** dans le projet.

    ⚠️ **Extrait en revue** parce qu'un second exemplaire venait d'apparaître : l'adapter SQLite le
    recopiait pour traduire la violation d'unicité que la **course** déclenche (deux postes
    d'admin, ou un double-clic). Les deux textes coïncidaient au singulier et auraient divergé à la
    première retouche. Rend l'exception au lieu de la lever : l'appelant écrit `raise
    doublon_d_arret(...)`, ce qui garde la levée visible là où elle se produit.
    """
    pluriel = "s" if len(tours) > 1 else ""
    liste = ", ".join(str(tour) for tour in tours)
    return ArretProgrammeInvalide(
        f"deux arrêts sont posés après le{pluriel} même{pluriel} tour{pluriel} {liste} : "
        "la phase ne peut pas être mise en pause deux fois au même endroit"
    )


def verifier_arrets(
    arrets: Sequence[ArretProgramme],
    nb_tours: int | None = None,
    *,
    geste_reparateur: str | None = None,
) -> None:
    """Vérifie qu'une **liste** d'arrêts est applicable. Lève `ArretProgrammeInvalide` sinon.

    Les invariants d'un arrêt seul sont à son `__post_init__` ; ceux du **couple** sont ici, là où
    l'information existe — même répartition que `ConfigurationSuisse` face à `EtapeDeroule`.
    `nb_tours=None` signifie « inconnu » et ne déclenche aucun refus : on ne refuse pas ce qu'on ne
    peut pas juger. ⚠️ `geste_reparateur` existe parce qu'un refus sans issue est un cul-de-sac
    (`P-3`) : « la phase n'en compte que 1 » laisse l'organisateur sans prise.
    """
    tours = [arret.apres_tour for arret in arrets]
    doublons = {tour for tour in tours if tours.count(tour) > 1}
    if doublons:
        raise doublon_d_arret(sorted(doublons))
    if nb_tours is None:
        return
    inertes = sorted(tour for tour in tours if tour >= nb_tours)
    if inertes:
        liste = ", ".join(str(tour) for tour in inertes)
        issue = f" {geste_reparateur}" if geste_reparateur else ""
        raise ArretProgrammeInvalide(
            f"un arrêt posé après le tour {liste} ne couperait rien : la phase n'en compte que "
            f"{nb_tours}, elle est terminée à ce moment-là.{issue}"
        )


def arrets_atteints(
    arrets: Sequence[ArretProgramme],
    tour_acheve: int,
    deja_traites: Collection[int],
) -> tuple[ArretProgramme, ...]:
    """Les arrêts **dus** maintenant que `tour_acheve` est fini, du plus ancien au plus récent.

    `deja_traites` porte les `apres_tour` déjà franchis, **quel qu'en soit l'état** : c'est la
    mémoire qui empêche la boucle décrite en tête de module. ⚠️ **Le test est `<=`, pas `==`** :
    rien ne garantit que le déclencheur soit évalué à chaque frontière de tour, et une comparaison
    par égalité perdrait silencieusement les arrêts intermédiaires. On les rend tous — le service
    n'appliquera qu'une pause mais marquera les autres **manquées**, ce qui est la lecture honnête.
    """
    traites = set(deja_traites)
    return tuple(
        sorted(
            (
                arret
                for arret in arrets
                if arret.apres_tour <= tour_acheve and arret.apres_tour not in traites
            ),
            key=lambda arret: arret.apres_tour,
        )
    )


def phases_a_arreter(
    tours_a_finir: Mapping[PhaseId, int | None],
    tours_courants: Mapping[PhaseId, int | None],
) -> tuple[PhaseId, ...]:
    """Parmi les phases qu'un arrêt de départ doit couper, celles qui ont fini leur tour.

    Une phase a fini quand son tour courant n'est plus celui noté à l'armement ; comptent aussi
    `tours_a_finir[phase] is None` et la disparition de `tours_courants` (clôturée à la main). ⚠️
    **La comparaison est `>` et non `!=`** : un tour peut **reculer** — celui d'une qualification
    se dérive du tireur le moins avancé, qu'un retardataire fait baisser. Avec `!=`, la phase était
    mise en pause **en plein tour**. La correction vit au domaine, pas chez le lecteur.
    """

    def a_fini(phase_id: PhaseId, tour_a_finir: int | None) -> bool:
        if tour_a_finir is None:
            return True
        if phase_id not in tours_courants:
            return True
        courant = tours_courants[phase_id]
        return courant is None or courant > tour_a_finir

    return tuple(
        sorted(
            phase_id
            for phase_id, tour_a_finir in tours_a_finir.items()
            if a_fini(phase_id, tour_a_finir)
        )
    )


@dataclass(frozen=True)
class ArretDeCirconstance:
    """Une coupe décidée **en cours de journée**, propre à un créneau (ADR-0092, E05US034).

    Troisième nature, frontière d'ADR-0076 : `ArretProgramme` est de la **composition** (porté par
    l'étape, rejoué par tous les créneaux), celui-ci de la **conduite** (porté par le départ,
    rejoué par personne), `FranchissementArret` reste l'**avancement**. ⚠️ Pas d'ajout au déroulé :
    un arrêt posé à 14 h pour une panne y serait rejoué le soir. ⚠️ Pas d'état `PROGRAMME` : c'est
    l'**absence** de franchissement.
    """

    depart_id: DepartId
    phase_id: PhaseId
    apres_tour: int
    portee: PorteeArret = PorteeArret.PHASE
    id: int | None = None

    def __post_init__(self) -> None:
        """Même invariant qu'`ArretProgramme`, redit ici plutôt que délégué à `definition()`.

        Les deux types entrent par des portes différentes — le JSON d'étape pour l'un, une route de
        pilotage pour l'autre — et un invariant qui ne tient que sur l'une des deux n'est pas un
        invariant. Le vérifier au `__post_init__` le rend vrai pour `replace()` aussi.
        """
        if self.apres_tour < 1:
            raise ArretProgrammeInvalide(
                f"un arrêt se pose après un tour existant, pas après le tour {self.apres_tour}"
            )

    def definition(self) -> ArretProgramme:
        """La coupe **telle que le déclencheur la lit** — sans le créneau ni l'identité.

        Le déclencheur travaille déjà par phase, dans un créneau donné : lui livrer les deux natures
        sous une seule forme évite un second chemin d'évaluation, donc une seconde occasion de
        diverger. C'est le même parti que `Phase`, qui porte en mémoire la définition de son étape.
        """
        return ArretProgramme(apres_tour=self.apres_tour, portee=self.portee)


def tour_d_un_arret_relatif(tour_courant: int | None, dans_x_tours: int) -> int:
    """Traduit « bloquer dans x tours » en « après le tour n » (CA E05US034).

    ⚠️ **Le tour courant compte dans les x**, d'où le `- 1` : « dans 1 tour » veut dire *celui qui
    tourne finit, puis on s'arrête* — la lecture de l'organisateur, qui a le numéro sous les yeux.
    `tour_courant is None` est **refusé** et non réparé : ce `None` a au moins cinq provenances, et
    aucune n'autorise à deviner. `dans_x_tours < 1` est refusé pour la même franchise — le
    mécanisme coupe **à la fin d'un tour**, jamais au milieu.
    """
    if tour_courant is None:
        raise ArretProgrammeInvalide(
            "impossible de poser un arrêt relatif sur une phase dont le tour en cours n'est pas "
            "lisible : on ne saurait pas à partir de quand compter."
        )
    if dans_x_tours < 1:
        raise ArretProgrammeInvalide(
            "un arrêt coupe à la fin d'un tour : il faut en laisser finir au moins un. "
            "Pour arrêter tout de suite, mettez la phase en pause depuis le pilotage."
        )
    return tour_courant + dans_x_tours - 1


def arrets_applicables(
    arrets_de_l_etape: Sequence[ArretProgramme],
    arrets_de_circonstance: Sequence[ArretDeCirconstance],
) -> tuple[ArretProgramme, ...]:
    """Le jeu d'arrêts que le déclencheur doit lire pour une phase : les deux natures fondues.

    CA E05US034 : l'arrêt du jour J « s'ajoute aux arrêts programmés, il ne les remplace pas ». ⚠️
    **Tolérant sur la collision, là où la pose est stricte** : celle-ci peut naître **après** la
    pose sans que personne ne se trompe — l'atelier ne peut pas voir l'avancement d'un créneau
    (ADR-0076). Lever ici gèlerait le déclencheur du créneau entier. **La portée la plus large
    gagne** : un arrêt de créneau *contient* un arrêt de phase. Rendu **trié par tour**.
    """
    par_tour: dict[int, ArretProgramme] = {}
    for arret in (*arrets_de_l_etape, *(a.definition() for a in arrets_de_circonstance)):
        connu = par_tour.get(arret.apres_tour)
        if connu is None or (
            connu.portee is PorteeArret.PHASE and arret.portee is PorteeArret.DEPART
        ):
            par_tour[arret.apres_tour] = arret
    return tuple(par_tour[tour] for tour in sorted(par_tour))
