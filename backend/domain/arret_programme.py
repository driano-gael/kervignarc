"""L'**arrêt programmé** — couper le déroulé à la fin d'un tour ([ADR-0091], E05US033).

Le besoin du commanditaire n'est pas « déclencher chaque tour à la main » mais « **pouvoir
couper** » : une phase qui dure des heures doit pouvoir s'interrompre pour le repas, une
réorganisation de salle, une annonce. L'enchaînement **automatique reste donc le défaut** — une
phase sans arrêt programmé se comporte exactement comme avant cette US.

**Trois natures, délibérément séparées** ([ADR-0076] appliqué à la lettre) :

- `ArretProgramme` est une **définition** : « après le tour 3, portée départ ». Elle se pose à
  l'atelier, elle vit sur l'`EtapeDeroule` du tournoi comme le réglage de poules ou de suisse, et
  **tous les départs du tournoi la rejouent**. C'est le sens d'ADR-0076 : le déroulé se définit une
  fois, chaque créneau le rejoue — deux départs qui pourraient diverger sur leurs pauses seraient
  exactement la divergence silencieuse que cet ADR a rendue impossible.
- `ArretDeCirconstance` est une **décision de conduite** : « bloque-moi dans deux tours », posée
  au pilotage pendant que la salle tire (E05US034, [ADR-0092]). Elle appartient au **départ**
  (ADR-0076 §5, *faire vivre se fait au créneau*) et n'est rejouée par personne : la panne de
  chauffage du matin n'arrête pas l'après-midi.
- `FranchissementArret` est un **état d'avancement** : « cet arrêt-ci a coupé cette phase-là, et
  l'admin l'a relevé ». Il est propre au créneau, il vit dans sa propre table, et il est
  **persisté** — pas dérivé.

⚠️ **Pourquoi le franchissement doit être persisté**, alors que tout le reste de l'avancement est
dérivé à la lecture ([ADR-0090] §5) : parce que la condition de déclenchement est **monotone**. Une
fois le tour 2 achevé, « le tour 2 est achevé et un arrêt est posé après le tour 2 » reste vrai pour
toujours. Un déclencheur qui relirait cette condition sans mémoire remettrait la phase en pause à la
seconde suivant chaque reprise : l'organisateur perdrait la main **définitivement**, et la salle ne
repartirait jamais. La trace n'est donc pas un confort d'implémentation, c'est ce qui rend la
reprise possible.

**Pourquoi un état `ARME` intermédiaire.** Un arrêt de portée départ *« laisse chaque phase finir
son tour en cours »* (arbitrage du commanditaire, 18/08/2026) : il n'est **pas simultané**. Il faut
donc un moment où l'arrêt est décidé sans être encore appliqué partout — la salle s'éteint en
quelques minutes, pas d'un coup. Et comme aucun événement « tour fini » n'est écrit nulle part, on
note à l'armement le tour que chaque phase a en cours, et l'on constate qu'il est fini quand il a
**changé**. C'est la seule formulation compatible avec un avancement dérivé.

Module **pur et synchrone** (règle 1) : aucune lecture, aucun état, aucune horloge — un
franchissement **porte** l'instant de sa coupe (`arrete_depuis`, E05US034), mais c'est le service
qui le lui donne, par le port `Horloge`.

[ADR-0076]: ../../docs/adr/0076-un-deroule-defini-une-fois-un-avancement-par-depart.md
[ADR-0090]: ../../docs/adr/0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md
[ADR-0091]: ../../docs/adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md
[ADR-0092]: ../../docs/adr/0092-un-arret-pose-le-jour-j-appartient-au-creneau.md
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

    Le **départ** est la portée sportive du projet ([ADR-0075]) et correspond à « ce qui tire en
    salle en ce moment ». Le statut du **tournoi** n'est pas une portée d'arrêt : il a déjà sa
    propre pause, à une autre maille (ADR-0026 §3), et la confondre avec celle-ci mélangerait « la
    salle s'arrête dix minutes » et « la compétition est suspendue ».

    [ADR-0075]: ../../docs/adr/0075-le-depart-est-la-portee-sportive.md
    """

    PHASE = "phase"
    DEPART = "depart"


class EtatFranchissement(str, Enum):
    """Où en est un arrêt qui a été atteint. Cycle **monotone**, comme celui d'une phase (ADR-0045).

    - `ARME` — le tour déclencheur est atteint ; les phases concernées s'arrêteront à la fin de leur
      tour courant. État transitoire, et seul un arrêt de portée **départ** y séjourne : un arrêt de
      portée phase est franchi d'emblée, puisque le tour qui vient de s'achever est le sien.
    - `FRANCHI` — toutes les phases concernées sont en pause. L'arrêt attend un geste d'admin.
    - `LEVE` — l'admin a relancé. L'arrêt est consommé et **ne se redéclenche plus jamais** ; la
      phase repart en automatique jusqu'au prochain arrêt.

    ⚠️ Il n'y a **pas** d'état « programmé » : c'est l'**absence** de franchissement. Un état de
    plus dupliquerait une information que la table porte déjà par une ligne manquante, et obligerait
    à écrire une ligne par arrêt dès la composition — donc à ré-écrire l'avancement de tous les
    créneaux à chaque édition du déroulé, ce qu'ADR-0076 a précisément supprimé.
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

    `phase_id` est la phase **déclenchante** — celle qui portait l'arrêt et dont le tour s'est
    achevé. `apres_tour` désigne l'arrêt dans la définition de son étape : le couple
    (`phase_id`, `apres_tour`) est donc l'identité fonctionnelle, et c'est lui qui porte l'unicité
    en base.

    `tours_a_finir` n'est peuplé que pour une portée **départ** : c'est la photo, prise à
    l'armement, du tour que chaque autre phase avait en cours. Une paire `(phase, None)` dit « cette
    phase n'avait plus rien en cours » — elle s'arrête donc immédiatement.

    `arrete_depuis` est l'instant où cet arrêt a éteint sa **première** phase (E05US034). C'est ce
    que la pastille de rappel décompte (« 2 phases attendent votre relance depuis 14 min »), et il
    ne se dérive de rien : ni le statut de phase ni l'avancement ne portent d'heure, l'avancement
    étant même recalculé à chaque lecture (ADR-0090 §5).

    ⚠️ **La première, pas la dernière**, et c'est le contraire du réflexe d'implémentation. Un arrêt
    de créneau éteint la salle en plusieurs minutes ; ré-horodater à chaque phase coupée ferait
    *rajeunir* la pastille — elle annoncerait « depuis 1 min » sur une salle arrêtée depuis vingt,
    c'est-à-dire qu'elle mentirait dans le sens qui endort la vigilance.
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
    """Refuse une pause sur un type dont l'application ne lit pas le tour. Périmètre du 19/08/2026.

    ⚠️ **Hissée ici en E05US034 parce qu'il existe désormais deux portes d'entrée.** La règle est
    née dans `EtapeDeroule._verifier_arrets_applicables` — l'atelier — et il n'y avait rien d'autre
    à garder. Le pilotage en ouvre une seconde (poser un arrêt le jour J) : la laisser sur l'étape
    aurait obligé la seconde porte à instancier une étape pour rien, ou — bien plus probable — à
    réécrire le test de type. Deux copies d'un même refus divergent, et celle qui diverge est
    toujours celle qu'on a écrite en second.

    Le déclencheur ne coupe qu'à une frontière de tour **observée**. Les types dont aucun service
    ne lit l'avancement — échauffement, barrage, placement, colline — n'ont aucun tour à observer :
    l'arrêt y serait accepté puis définitivement inerte, et l'organisateur découvrirait le jour J
    que sa pause repas n'a jamais eu lieu. Un refus explicite vaut mieux qu'un réglage mort, et il
    dit **où** poser la pause (`P-3` : un refus sans issue est un cul-de-sac).

    ⚠️ **L'oracle est `TYPES_ARRETABLES`, et non `TYPES_DEROULES` comme jusqu'à E05US035.** Les
    deux tables coïncidaient, ce qui rendait la confusion invisible ; la **qualification** les
    sépare — on sait désormais dire où elle en est (`ServiceSaisie.avancement_de_phase`) sans
    qu'aucun service ne la monte. Lever le refus en basculant l'autre capacité aurait fait réclamer
    un plancher d'inscrits par rangs à toute qualification prélevée (E05US021), soit un refus de
    démarrage le jour J pour un réglage d'affichage.
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

    ⚠️ **Extrait en revue** (axe adversarial) parce qu'un second exemplaire venait d'apparaître :
    l'adapter SQLite le recopiait à la main pour traduire la violation d'unicité
    `(depart_id, phase_id, apres_tour)` que la **course** déclenche — deux postes d'admin, ou le
    double-clic d'un seul. Les deux textes coïncidaient au singulier et auraient divergé à la
    première retouche, celle qui diverge étant toujours la seconde copie. C'est mot pour mot ce que
    `verifier_type_arretable` interdit deux cents lignes plus haut, et pour la même raison.

    Rend l'exception au lieu de la lever : l'appelant écrit `raise doublon_d_arret(...)`, ce qui
    garde la levée visible à l'endroit où elle se produit.
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

    Les invariants d'un arrêt seul sont à son `__post_init__` ; ceux du **couple** (deux arrêts
    entre eux, un arrêt face au nombre de tours) sont ici, là où l'information existe. C'est la
    même répartition que `ConfigurationSuisse` face à `EtapeDeroule._verifier_rondes_appariables` :
    le réglage refuse ce qu'il peut juger seul, l'étape refuse ce qui dépend de son contexte.

    `nb_tours=None` signifie « inconnu » et ne déclenche aucun refus : un système suisse réglé à
    7 rondes n'en joue que 5 si l'effectif ne permet pas plus, et l'atelier ne connaît pas toujours
    l'effectif. On ne refuse pas ce qu'on ne peut pas juger.

    ⚠️ **`geste_reparateur` existe parce qu'un refus sans issue est un cul-de-sac** (`P-3`). Le
    message générique dit *pourquoi* c'est refusé ; sur une qualification non découpée il ne dit
    pas *quoi faire*, et « la phase n'en compte que 1 » laisse l'organisateur sans prise — il n'a
    aucune raison de deviner qu'un réglage de découpage existe deux blocs plus haut. L'appelant qui
    connaît le geste le fournit ; les autres gardent le message d'origine.
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

    `deja_traites` porte les `apres_tour` des arrêts qui ont déjà un franchissement, **quel qu'en
    soit l'état** — `ARME`, `FRANCHI` ou `LEVE`. C'est la mémoire qui empêche la boucle décrite en
    tête de module.

    ⚠️ **Le test est `<=`, pas `==`**, et c'est un choix. Rien ne garantit que le déclencheur soit
    évalué à chaque frontière de tour : une correction en cascade, un lot de validations ou une
    phase reprise après incident peuvent faire passer le tour courant de 2 à 5 entre deux
    évaluations. Comparer par égalité perdrait alors silencieusement les arrêts intermédiaires —
    l'organisateur aurait programmé trois pauses et n'en verrait aucune. On les rend tous : le
    service n'appliquera qu'une pause (la phase ne peut être en pause qu'une fois) mais marquera les
    autres traités, ce qui est la lecture honnête — ces pauses-là ont été **manquées**, pas
    annulées.
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

    Une phase a fini son tour quand son tour courant n'est **plus** celui noté à l'armement. Deux
    cas s'y ajoutent, et tous deux comptent comme « finie » :

    - `tours_a_finir[phase] is None` — elle n'avait déjà plus rien en cours à l'armement (convention
      d'`AvancementDePhase`, ADR-0090 : tout est joué même si la phase n'est pas clôturée). Lui
      faire attendre un changement qui ne viendra jamais la laisserait `EN_COURS` pour l'éternité,
      et l'arrêt resterait `ARME` sans jamais devenir relançable ;
    - la phase a disparu de `tours_courants` — clôturée à la main pendant l'armement (E12US008).
    Elle
      n'a plus d'avancement à lire ; l'attendre ferait d'un geste de clôture légitime un gel de la
      reprise.

    ⚠️ **La comparaison est `>` et non `!=`, et c'est un correctif de bloquant de 2ᵉ passe** (axe
    adversarial). Un tour qui **recule** n'est pas un tour fini — et il peut reculer : le tour d'une
    qualification se dérive du tireur le **moins** avancé du plateau, or un archer qui commence en
    retard fait baisser ce minimum. Avec `!=`, toute différence valait « a fini son tour », donc la
    phase était **mise en pause en plein tour** par un arrêt de créneau à la première volée d'un
    retardataire.

    La correction vit **ici**, au domaine, et non chez le lecteur qui produit le tour : c'est ce qui
    ferme la classe entière quel que soit le format et quelle que soit la façon dont son service
    calcule son avancement. La corriger côté lecteur aurait rejoué le même raisonnement un cran plus
    haut, une fois par format — et l'axe adversarial a montré qu'une première tentative y avait
    aussitôt réintroduit deux trous.

    `tour_courant is None` compte aussi comme « fini » : c'est la convention d'`AvancementDePhase`
    (ADR-0090), et une phase dont plus rien ne tourne n'a effectivement plus de tour à finir.

    Rendu **trié par identifiant** pour que deux évaluations successives produisent la même liste :
    un ordre instable rendrait les diffs de trace illisibles et les tests dépendants du hasard.
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
    """Une coupe décidée **en cours de journée**, propre à un créneau ([ADR-0092], E05US034).

    Troisième nature du mécanisme, et la frontière est celle d'ADR-0076 :

    - `ArretProgramme` est de la **composition** — posé à l'atelier, porté par l'`EtapeDeroule` du
      tournoi, **rejoué par tous les créneaux** (ADR-0076 §4) ;
    - `ArretDeCirconstance` est de la **conduite** — posé au pilotage pendant que la salle tire,
      porté par le **départ** (ADR-0076 §5), et rejoué par **personne** ;
    - `FranchissementArret` reste l'**avancement** : cet arrêt-là a coupé, ici, et l'admin l'a
      relevé.

    ⚠️ **Pourquoi pas simplement ajouter l'arrêt au déroulé.** Parce que le déroulé est la
    définition du tournoi : un arrêt ajouté à 14 h pour cause de panne de chauffage y serait rejoué
    par le créneau de l'après-midi, qui n'a aucune raison de s'arrêter. La divergence serait
    exactement du type qu'ADR-0076 a rendu impossible — sauf qu'ici elle jouerait dans l'autre sens,
    en **propageant** ce qui devait rester local.

    ⚠️ **Pourquoi pas un état `PROGRAMME` de plus sur le franchissement.** L'en-tête
    d'`EtatFranchissement` explique pourquoi cet état n'existe pas : « programmé » est l'**absence**
    de franchissement. Le réintroduire pour les seuls arrêts de circonstance ferait porter à la
    table de l'avancement une moitié de la définition, et « un arrêt franchi » cesserait de vouloir
    dire « un arrêt atteint ».

    `portee` a le même sens que sur `ArretProgramme` : cette phase seule, ou tout le créneau.

    [ADR-0076]: ../../docs/adr/0076-un-deroule-defini-une-fois-un-avancement-par-depart.md
    [ADR-0092]: ../../docs/adr/0092-un-arret-pose-le-jour-j-appartient-au-creneau.md
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
    tourne finit, puis on s'arrête*. C'est la lecture de l'organisateur, qui a le numéro du tour
    sous les yeux au moment où il clique. La convention inverse (`tour_courant + x`) couperait un
    tour trop tard — sur un système suisse, une demi-heure après le repas.

    `tour_courant is None` est **refusé** et non réparé : ce `None` a au moins cinq provenances (cf.
    `ServiceArretsProgrammes._tour_acheve`), de « tout est joué » à « aucun lecteur branché pour ce
    type ». Aucune n'autorise à deviner une origine — poser l'arrêt « après le tour 1 » par défaut
    couperait la salle au premier tour d'une phase qu'on croyait au cinquième.

    `dans_x_tours < 1` est refusé pour la même raison de franchise : le mécanisme coupe **à la fin
    d'un tour** (ADR-0091), jamais au milieu. Se replier silencieusement sur 1 laisserait croire
    qu'un arrêt immédiat existe.
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

    CA E05US034 : l'arrêt du jour J *« s'ajoute aux arrêts programmés, il ne les remplace pas »*.

    ⚠️ **Tolérant sur la collision, là où la pose est stricte** — et l'asymétrie est délibérée.
    Poser un arrêt de circonstance sur un tour déjà pris est refusé à l'organisateur, qui a l'écran
    devant lui et peut corriger. Mais la collision peut naître **après** la pose, sans que personne
    ne se trompe : l'atelier ajoute un arrêt après le tour 4 au déroulé du tournoi pendant qu'un
    créneau porte déjà un arrêt de circonstance après le tour 4. L'atelier ne **peut pas** le
    savoir : ADR-0076 lui interdit de voir l'avancement d'un créneau. Lever ici gèlerait le
    déclencheur du créneau entier — plus aucune pause ne tomberait, pour aucune phase.

    Fusionner garde aussi vraie l'unicité `(phase_id, apres_tour)` du franchissement : une coupe,
    une trace, un bouton de relance.

    **La portée la plus large gagne.** Un arrêt de créneau *contient* un arrêt de phase :
    l'appliquer honore les deux. L'inverse laisserait tirer une salle que l'un des deux voulait
    éteindre.

    Rendu **trié par tour** : `arrets_atteints` en dépend, et `_appliquer` n'applique que le plus
    ancien dû.
    """
    par_tour: dict[int, ArretProgramme] = {}
    for arret in (*arrets_de_l_etape, *(a.definition() for a in arrets_de_circonstance)):
        connu = par_tour.get(arret.apres_tour)
        if connu is None or (
            connu.portee is PorteeArret.PHASE and arret.portee is PorteeArret.DEPART
        ):
            par_tour[arret.apres_tour] = arret
    return tuple(par_tour[tour] for tour in sorted(par_tour))
