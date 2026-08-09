"""Lectures **transverses** d'un tournoi, depuis que la portée sportive est le départ (ADR-0075).

Un tournoi n'a plus de phases en propre : il en a autant de séquences que de départs. Or plusieurs
services ont besoin d'une information qui, elle, est **commune** au tournoi — combien de volées
compte une qualification, à quel grain le scoreur valide.

**Et elle l'est réellement depuis [ADR-0076]** : ces réglages vivent sur l'`EtapeDeroule`, définie
**une fois** pour le tournoi, que le repository assemble sur la phase de chaque créneau. Les lire
sur un départ ou sur un autre ne « revient au même » plus par convention — c'est la *même* donnée.
La réserve « tant qu'ils n'ont pas divergé », que ce module portait, n'a plus d'objet : la
divergence n'est pas improbable, elle est impossible.

[ADR-0076]: ../../docs/adr/0076-un-deroule-defini-une-fois-un-avancement-par-depart.md

**Pourquoi un module et non un copier-coller de plus.** Six services faisaient déjà la même
résolution « la qualification de ce tournoi » : `bareme_qualification`, `grain_validation`,
`completude` (deux fois), `feuille_de_marque`, `forfaits`, `saisie` (deux fois). C'est la
duplication que `DETTE-022` signale depuis E04US018. La règle du projet autorise un remède
structurel sur **preuve dans le code d'aujourd'hui** (3ᵉ occurrence réelle) : il y en a six,
toutes existantes, aucune supposée. La factorisation se fait donc ici et non « plus tard ».

⚠️ **Ces lectures sont des raccourcis assumés, pas la vérité du moteur.** Le moteur, lui, raisonne
toujours dans un départ (`PhaseRepository.par_depart`). Quiconque a un `depart_id` sous la main doit
l'utiliser : passer par ici perdrait justement la distinction qu'ADR-0075 rétablit.

# ⚠️ **E05US025 — ce qui reste de `qualification_du_tournoi`, et pourquoi.** Un déroulé peut porter
# plusieurs qualifications (ADR-0082) : « la » qualification du tournoi n'existe donc plus en
# général, et cette fonction rend désormais **la première**. Les appelants ont été triés un par un ;
# les cinq qui subsistent le font pour deux raisons distinctes, à ne pas confondre :
#
# - **La famille `DETTE-047`** (`forfaits.declarer` — un seul site —,
#   `classements._forfaits_qualif`, `saisie._forfaits_qualif`) : le forfait s'**écrit** sur la
#   phase rendue ici et se **lit** par le même chemin. L'affichage est « cohérent par accident » ;
#   ne corriger que la lecture rendrait les forfaits **invisibles** au lieu de les rendre justes.
#   Les deux côtés se portent au départ ensemble, dans l'US de résorption — pas ici.
# - **Le repli assumé** (`saisie._phase_qualification_ou_none`, `pilotage_simulation`) : le premier
#   ne s'en sert que lorsqu'aucun créneau n'est résoluble (donnée incohérente), le second simule un
#   déroulé mono-qualification. Les deux sont justes tels quels.
#
# Ce qui **a** été porté au créneau : `saisie.avancement_cible`, les deux comptages de `completude`,
# et `feuille_de_marque._bareme_du_creneau` — tous trois recevaient déjà un `depart_id`, la portée
# tournoi n'y était qu'un raccourci.
#
# ⚠️ **Ce tri a été faux à sa première rédaction, et le compte tombait juste par compensation** :
# il annonçait six sites en comptant `forfaits` deux fois et en oubliant `feuille_de_marque`, qui
# imprimait donc une grille de 20 volées pour un tour qui s'en tire 15. Recompter par `grep` avant
# d'ajouter ou de retirer une ligne ici — une énumération fausse est pire qu'absente, la prochaine
# US s'y fiera.
#
# DETTE-048 : ce module concentre la portée tournoi résiduelle, et il est le seul à n'être **ni
# testé ni surveillé**. Aucun test ne l'importe ; et le garde-fou `tests/test_portee_sportive.py` le
# manque par construction — son balayage AST reconnaît des *noms de variables* (`phase`, `barrage`),
# pas un `tournoi_id` reçu en **paramètre**, qui est justement la forme d'ici. Les deux défauts de
# portée trouvés à la 2ᵉ revue d'E01US025 en sont sortis tous les deux (DETTE-047, et les verdicts
# de barrage corrigés dans l'US). Avant d'ajouter un dixième appelant, lire le registre.
"""

from __future__ import annotations

from collections.abc import Iterable

from domain.depart import DepartId
from domain.phase import Phase, PhaseId, StatutPhase, TypePhase
from domain.ports import PhaseRepository
from domain.tournoi import TournoiId

_STATUTS_EN_COURS = frozenset({StatutPhase.EN_COURS, StatutPhase.EN_PAUSE})
"""Les statuts d'une phase **démarrée mais pas finie** — celle où l'on tire en ce moment."""


def qualification_du_tournoi(phases: PhaseRepository, tournoi_id: TournoiId) -> Phase | None:
    """La qualification du tournoi — telle que jouée dans un créneau —, ou `None` s'il n'y en a pas.

    ⚠️ **Cette lecture était une approximation ; ADR-0076 la rend exacte.** Elle s'appelait
    `qualification_representative`, et sa docstring devait reconnaître ne rendre « une approximation
    d'affichage, jamais une base de calcul » : chaque départ portait alors sa **copie** du déroulé,
    libre de diverger, et cette fonction en désignait une au hasard des tris. Le déroulé étant
    désormais **défini une fois** (`EtapeDeroule`), toutes les instances portent la même définition
    — l'adapter l'assemble depuis l'étape de même rang. Il n'y a plus de représentant : il n'y a
    plus qu'une valeur. Le renommage est délibéré, pour que rien ne continue de citer l'ancienne
    prudence comme si elle valait encore.

    Ce qui **reste** propre au créneau, et donc à lire par `par_depart` : le `statut` et l'`id` de
    la phase. Quiconque a un `depart_id` sous la main doit l'utiliser (ADR-0075).

    `par_tournoi` (transverse, jointure `phase → depart → tournoi`) sert de source : les phases y
    sont triées par départ puis par ordre, donc la première trouvée est celle du premier départ —
    un choix **stable** d'un appel à l'autre, ce qui évite qu'un écran change d'identifiant entre
    deux rafraîchissements.
    """
    for phase in phases.par_tournoi(tournoi_id):
        if phase.type is TypePhase.QUALIFICATION:
            return phase
    return None


def qualification_courante(phases: PhaseRepository, depart_id: DepartId) -> Phase | None:
    """La qualification **où l'on tire en ce moment** dans ce créneau, ou `None` s'il n'y en a pas.

    Depuis E05US025 (ADR-0082) un créneau peut porter plusieurs qualifications — 3x20, puis une
    *haute* et une *basse* à 3x15. « La » qualification n'existe donc plus ; ce qui existe, c'est
    celle qui se tire maintenant. Trois cas, par ordre croissant :

    1. la première **démarrée et non terminée** (`en cours` ou `en pause` — une pause suspend le
    tir,
       elle ne rend pas la feuille à une autre phase) ;
    2. à défaut, la première **à venir** ;
    3. à défaut, la dernière (tout est terminé — on parle encore de la plus récente).

    Le repli sur « à venir » n'est pas de la complaisance. Démarrer une phase est un geste
    **manuel**
    de l'organisateur (`ServicePhases.demarrer`) : faire dépendre la saisie et la complétude de sa
    discipline bloquerait le pas de tir tout l'après-midi s'il l'oublie. C'est le même parti que
    `ServicePalmares._resultat`, qui refuse déjà de lire `phase.statut` pour décider d'un affichage.

    ⚠️ **Contrairement au reste de ce module, ce n'est pas un raccourci de portée** : la fonction
    travaille bien à la maille du créneau (`par_depart`), là où le moteur raisonne. Elle vit ici
    parce que trois services la réclamaient — `ServiceSaisie` et `ServiceCompletude` (deux fois) —,
    ce qui est la 3ᵉ occurrence que la règle du projet exige avant de factoriser, et parce que
    `DETTE-022` recense précisément cette famille de duplications.
    """
    return la_plus_courante(
        phase for phase in phases.par_depart(depart_id) if phase.type is TypePhase.QUALIFICATION
    )


def la_plus_courante(phases: Iterable[Phase]) -> Phase | None:
    """Celle de ces phases où l'on tire **en ce moment** (priorité de statut), ou `None` si aucune.

    Extraite de `qualification_courante` (correctif de revue E05US025) parce qu'un second appelant
    l'a réclamée : `ServiceSaisie` doit appliquer la **même** priorité, mais après avoir filtré les
    qualifications sur celle qui **admet** l'archer — sur la fourche *haute*/*basse*, « la première
    démarrée du créneau » n'est pas la sienne. Recopier la priorité aurait laissé les deux dériver.
    """
    qualifications = sorted(phases, key=lambda phase: phase.ordre)
    if not qualifications:
        return None
    demarrees = [p for p in qualifications if p.statut in _STATUTS_EN_COURS]
    if demarrees:
        return demarrees[0]
    a_venir = [p for p in qualifications if p.statut is StatutPhase.A_VENIR]
    return a_venir[0] if a_venir else qualifications[-1]


def phase_du_tournoi(
    phases: PhaseRepository, tournoi_id: TournoiId, phase_id: PhaseId
) -> Phase | None:
    """La phase `phase_id` **si elle appartient à ce tournoi**, sinon `None`.

    Remplace la garde `phase.tournoi_id != tournoi_id`, devenue impossible : une phase ne connaît
    plus que son départ (ADR-0075). L'appartenance au tournoi se lit donc par la jointure
    `phase → depart → tournoi`, que `par_tournoi` porte déjà — inutile d'injecter un
    `DepartRepository` dans les six services qui font ce contrôle.

    ⚠️ **Garde d'autorisation, pas de commodité** : elle empêche qu'un identifiant de phase d'un
    *autre* tournoi soit accepté sur cette route. La remplacer par un `par_id` nu rouvrirait cette
    porte — c'est précisément ce que le contrôle existait pour fermer.
    """
    return next((phase for phase in phases.par_tournoi(tournoi_id) if phase.id == phase_id), None)


def phase_du_depart(
    phases: PhaseRepository, depart_id: DepartId, phase_id: PhaseId
) -> Phase | None:
    """La phase `phase_id` **si elle appartient à ce créneau**, sinon `None`.

    Pendant de `phase_du_tournoi`, à la maille où le moteur travaille. Garde d'autorisation, pas de
    commodité : sans elle, une phase d'un autre départ — voire d'un autre tournoi — serait acceptée
    sur la route.
    """
    return next((phase for phase in phases.par_depart(depart_id) if phase.id == phase_id), None)
