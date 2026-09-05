"""Adapters repository SQLAlchemy — le **moteur de phases** : séquence, formats, plans de placement.

Session courte par opération et pannes SQLAlchemy enveloppées en `InfrastructureError` : ADR-0005.
Le découpage de l'ancien `repositories.py` est l'action 2 de
[l'audit de maintenabilité](../../../../docs/audit-maintenabilite.md).
"""

from __future__ import annotations

import dataclasses
import datetime
import json
from collections.abc import Sequence
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from domain.arret_programme import (
    ArretDeCirconstance,
    ArretProgramme,
    EtatFranchissement,
    FranchissementArret,
    PorteeArret,
    doublon_d_arret,
)
from domain.bareme import BaremeQualification
from domain.big_shoot_off import ConfigurationBigShootOff
from domain.colline import ConfigurationColline
from domain.depart import DepartId
from domain.deroule_etape import EtapeDeroule, EtapeDerouleId
from domain.entree_audit import EntreeAudit
from domain.erreurs import DomainError
from domain.format_tournoi import FormatTournoi, FormatTournoiId, ModelePhase
from domain.grain_validation import GrainValidation, TypeGrain
from domain.inscription import InscriptionId
from domain.patrimoine import OrigineBrique
from domain.phase import (
    IssueTour,
    NatureSource,
    Phase,
    PhaseId,
    SourcePhase,
    StatutPhase,
    TypePhase,
    grain_par_defaut,
)
from domain.placement import Affectation
from domain.placement_par_bloc import BlocDeCouloirs
from domain.politiques import NomProfondeur, ProfondeurClassement
from domain.poule import BaremePoule, ModeDeComposition, ReglageDePoules
from domain.qualification import DecoupageEnTours
from domain.suisse import ConfigurationSuisse
from domain.tournoi import TournoiId
from infrastructure.db.models import (
    ArretDeCirconstanceORM,
    DepartORM,
    DerouleEtapeORM,
    FormatTournoiORM,
    FranchissementArretORM,
    PhaseORM,
    PlacementORM,
    PlacementParBlocORM,
    PlacementTableauORM,
)

# `AuditRepositorySQL` vit dans le thème `exploitation` mais s'annote ici : plusieurs
# adapters **co-écrivent** leur trace d'audit dans la même transaction (ADR-0035). Import
# direct et acyclique — `exploitation` n'importe aucun autre thème.
from infrastructure.db.repositories.exploitation import AuditRepositorySQL
from infrastructure.erreurs import InfrastructureError


def _vers_etape(ligne: DerouleEtapeORM) -> EtapeDeroule:
    """Traduit une ligne ORM en `EtapeDeroule` (config JSON → barème, grain, source, effectif).

    ⚠️ Une `config` illisible **ou hors règle** est une **incohérence technique** (ce repository en
    est le seul rédacteur) : on relit par les fabriques du domaine pour qu'elle remonte en
    `InfrastructureError` (ADR-0007), jamais en value object silencieusement invalide. L'**absence**
    d'une clé est licite — preset du type, « politique sans migration » (ADR-0011) ; `_lire_scoring`
    tolère de même l'ancienne forme à plat `config.scoring` (ADR-0046, migration 0028).
    """
    try:
        config = json.loads(ligne.config)
        type_phase = TypePhase(ligne.type)
        bareme = None
        validation = None
        if type_phase is TypePhase.QUALIFICATION:
            scoring = _lire_scoring(config)
            bareme = BaremeQualification.creer(
                nb_volees=int(scoring["volees"]),
                nb_fleches_par_volee=int(scoring["fleches"]),
            )
        # Le grain se relit **quel que soit le type**, comme `_vers_modele_phase`. `_config_phase`
        # l'écrit pour tout type et `Phase` admet un `fin_de_duel` sur une élimination directe
        # (`_GRAINS_ADMIS`) : ne le relire que pour la qualification revenait à écrire ce qu'on ne
        # relit pas. La revue avait corrigé la lecture des **formats** en laissant celle des
        # **phases** intacte — le trou avait donc changé de table, pas disparu, et le scénario
        # invoqué (promouvoir un tournoi dont l'élimination porte un grain) restait cassé.
        if "validation" in config:
            validation = _vers_grain(config["validation"])
        elif type_phase is TypePhase.QUALIFICATION:
            # Absence sur une qualification = phase écrite avant E01US015 → preset du type
            # (mécanisme « politique sans migration », ADR-0011). Sur un autre type, l'absence
            # signifie simplement « pas de grain ».
            validation = grain_par_defaut(type_phase)
        sources = _vers_sources(config)
        effectif = config.get("effectif")
        effectif = None if effectif is None else int(effectif)
        barrage_jusqu_au = _lire_barrage_jusqu_au(config)
        profondeur = _lire_profondeur(config)
        poules = _lire_reglage_poules(config)
        big_shoot_off = _lire_reglage_big_shoot_off(config)
        suisse = _lire_reglage_suisse(config)
        colline = _lire_reglage_colline(config)
        decoupage = _lire_decoupage(config)
        arrets = _lire_arrets(config)
        titre = _lire_titre(config)
    except (
        json.JSONDecodeError,
        AttributeError,
        KeyError,
        TypeError,
        ValueError,
        DomainError,
    ) as exc:
        raise InfrastructureError("Configuration d'étape de déroulé illisible.") from exc
    try:
        return EtapeDeroule(
            tournoi_id=ligne.tournoi_id,
            ordre=ligne.ordre,
            type=type_phase,
            bareme=bareme,
            validation=validation,
            sources=sources,
            effectif=effectif,
            barrage_jusqu_au=barrage_jusqu_au,
            profondeur=profondeur,
            poules=poules,
            big_shoot_off=big_shoot_off,
            suisse=suisse,
            colline=colline,
            decoupage=decoupage,
            arrets=arrets,
            titre=titre,
            id=ligne.id,
        )
    except DomainError as exc:
        # Les politiques sont individuellement valides mais incohérentes entre elles : le repository
        # n'écrit jamais ça (l'agrégat le refuse en amont) — donc la base a été altérée.
        raise InfrastructureError("Configuration d'étape de déroulé illisible.") from exc


def _vers_phase(ligne: PhaseORM, etape: EtapeDeroule) -> Phase:
    """Assemble l'objet du moteur : l'**avancement** d'une ligne `phase` + la **définition** de son
    étape (ADR-0076).

    C'est *la* couture de la séparation. Le domaine et les services ne la voient pas : ils
    reçoivent une `Phase` complète, comme avant. La jointure est l'affaire de l'adapter (ADR-0003),
    et c'est ce qui permet aux 34 modules qui lisent `phase.bareme` de n'avoir pas bougé.
    """
    try:
        statut = StatutPhase(ligne.statut)
    except ValueError as exc:
        raise InfrastructureError("Statut de phase illisible.") from exc
    return dataclasses.replace(etape.instancier(ligne.depart_id), statut=statut, id=ligne.id)


def _lire_scoring(config: Any) -> Any:
    """Extrait l'objet `scoring` d'une `config` de phase, forme cible **ou** ancienne (ADR-0046).

    Cible (E05US003) : `config.policies.scoring`. Ancienne (E01US009, base non migrée / restaurée) :
    `config.scoring` à la racine. On préfère la cible ; on retombe sur la racine sinon. Le champ
    `nom`/`mode` n'est pas exploité (seuls `volees`/`fleches` alimentent le barème) — les deux
    formes sont donc relues à l'identique. Une forme inattendue (ni l'une ni l'autre) lève
    `KeyError`/`TypeError`, que `_vers_phase` enveloppe en `InfrastructureError`.
    """
    policies = config.get("policies")
    if isinstance(policies, dict) and "scoring" in policies:
        return policies["scoring"]
    return config["scoring"]


def _lire_scoring_facultatif(config: Any) -> Any:
    """Comme `_lire_scoring`, mais rend `None` au lieu de lever quand le barème est absent.

    Réservé aux **modèles d'étape** d'un format, seuls à pouvoir légitimement ne pas en porter
    (E01US024). Une **phase** de qualification en a toujours un — son invariant n'a pas bougé —,
    donc `_vers_phase` continue d'utiliser la version levante : une absence y reste une incohérence
    technique, et l'affaiblir masquerait une vraie corruption.
    """
    policies = config.get("policies")
    if isinstance(policies, dict) and "scoring" in policies:
        # Clé **présente** : sa valeur fait foi, `null` compris (barème délibérément absent).
        return policies["scoring"]
    # Repli sur la racine, par **symétrie** avec `_lire_scoring` et non par nécessité : la table
    # `format_tournoi` naît de la migration 0035, postérieure à 0028 (ADR-0046), donc aucune version
    # n'y a jamais écrit `scoring` à la racine. Le garder coûte une ligne et évite qu'une divergence
    # s'installe entre les deux lecteurs le jour où l'une des formes bougera.
    return config.get("scoring")


def _vers_source(source: Any) -> SourcePhase:
    """Relit **un** prélèvement depuis sa forme JSON.

    Passe par le constructeur de `SourcePhase` pour qu'une forme hors règle remonte en
    `DomainError`, enveloppée par l'appelant. `source` est typé `Any` (`json.loads`) : une forme
    inattendue lève `AttributeError`/`TypeError`, gérée de même. **Tolérante à l'ancienne forme**
    (sans clé `nature`) : une base d'avant la migration 0036 reste lisible, comme `_lire_scoring`
    tolère `config.scoring` (ADR-0046).
    """
    nature = NatureSource(source.get("nature", NatureSource.RANGS.value))
    if nature is NatureSource.ISSUE_DE_TOUR:
        return SourcePhase(
            ordre_source=int(source["ordre_source"]),
            nature=nature,
            tour=int(source["tour"]),
            issue=IssueTour(source["issue"]),
        )
    if nature is NatureSource.RESTE:
        return SourcePhase(ordre_source=int(source["ordre_source"]), nature=nature)
    rang_fin = source.get("rang_fin")
    return SourcePhase(
        ordre_source=int(source["ordre_source"]),
        rang_debut=int(source["rang_debut"]),
        rang_fin=None if rang_fin is None else int(rang_fin),
    )


def _vers_sources(config: Any) -> tuple[SourcePhase, ...]:
    """Relit **tous** les prélèvements d'une étape, forme cible **ou** ancienne.

    Cible (E05US010) : `config.sources`, une liste. Ancienne (E05US001) : `config.source`, un objet
    unique — relu comme une liste d'un élément, puisque c'en est exactement le sous-cas. Absence
    des deux : la phase est alimentée par les inscriptions.
    """
    brutes = config.get("sources")
    if brutes is None:
        unique = config.get("source")
        brutes = [] if unique is None else [unique]
    return tuple(_vers_source(brute) for brute in brutes)


def _vers_grain(validation: Any) -> GrainValidation:
    """Relit le grain de validation depuis sa forme JSON (`config.validation`).

    Passe par `GrainValidation.creer` pour qu'une valeur hors règle remonte en `DomainError`,
    convertie en `InfrastructureError` par l'appelant — jamais en value object invalide.
    `validation` est typé `Any` (`json.loads`) : une forme inattendue lève
    `AttributeError`/`TypeError`, que l'appelant enveloppe comme le reste.
    """
    n_volees = validation.get("n_volees")
    return GrainValidation.creer(
        TypeGrain(validation["grain"]),
        None if n_volees is None else int(n_volees),
    )


def _config_etape(etape: EtapeDeroule) -> str:
    """Sérialise les politiques et le peuplement d'une phase en JSON (forme cible, ADR-0046).

    `{"policies"?: {...}, "validation"?: {...}, "source"?: {...}, "effectif"?: int}`. ⚠️ Seules les
    **familles d'ADR-0004** vivent sous `policies`, chacune `{"nom": …, …paramètres}` (E05US003 a
    tranché DETTE-003). Le grain de `validation` n'en est pas une : il reste **à la racine**, comme
    la source et l'effectif. La relecture reste tolérante à l'ancienne forme à plat.
    """
    return json.dumps(
        _politiques_json(
            etape.bareme,
            etape.validation,
            etape.sources,
            etape.effectif,
            barrage_jusqu_au=etape.barrage_jusqu_au,
            profondeur=etape.profondeur,
            poules=etape.poules,
            big_shoot_off=etape.big_shoot_off,
            suisse=etape.suisse,
            colline=etape.colline,
            decoupage=etape.decoupage,
            arrets=etape.arrets,
            titre=etape.titre,
        )
    )


def _politiques_json(
    bareme: BaremeQualification | None,
    validation: GrainValidation | None,
    sources: tuple[SourcePhase, ...],
    effectif: int | None,
    *,
    barrage_jusqu_au: int | None,
    profondeur: ProfondeurClassement | None,
    poules: ReglageDePoules | None,
    big_shoot_off: ConfigurationBigShootOff | None,
    suisse: ConfigurationSuisse | None,
    colline: ConfigurationColline | None,
    decoupage: DecoupageEnTours | None,
    arrets: tuple[ArretProgramme, ...],
    titre: str | None,
    marquer_absences: bool = False,
    porte_un_bareme: bool = False,
) -> dict[str, object]:
    """Corps commun d'une **étape** — une phase de tournoi ou un modèle d'étape d'un format.

    ⚠️ **Les champs de composition sont keyword-only et SANS DÉFAUT, et c'est le garde-fou** : deux
    appelants (`_config_etape`, `_config_format`), trois oublis payés (`barrage_jusqu_au`,
    `colline`, `titre`) qui, sous un défaut, compilaient et passaient mypy et les aller-retours.
    ⚠️ **`marquer_absences`** distingue « pas encore écrit » de « délibérément vide » (E01US024) :
    les **formats** écrivent la clé présente à `null`, les **phases** gardent le régime historique.
    """
    config: dict[str, object] = {}
    if bareme is not None:
        config["policies"] = {
            "scoring": {
                "nom": "cumul",
                "volees": bareme.nb_volees,
                "fleches": bareme.nb_fleches_par_volee,
            }
        }
    elif marquer_absences and porte_un_bareme:
        # Seule une **qualification** peut porter un barème : marquer son absence sur un autre type
        # écrirait « le rédacteur n'en a pas voulu » là où la question ne se pose pas, et
        # contredirait la règle de `_config_phase` (« `scoring`, et seulement pour une
        # qualification »). Sans effet aujourd'hui — la relecture n'y lit pas le scoring —, mais un
        # piège le jour où ces types porteront leurs propres politiques (ADR-0062).
        config["policies"] = {"scoring": None}
    if validation is not None:
        grain: dict[str, object] = {"grain": validation.type.value}
        if validation.n_volees is not None:
            grain["n_volees"] = validation.n_volees
        config["validation"] = grain
    elif marquer_absences:
        config["validation"] = None
    if barrage_jusqu_au is not None:
        # Forme ADR-0046 : `config.policies.tiebreak = {"nom": …, …paramètres}`, exactement comme
        # `scoring`. Le `policies` peut ne pas exister (phase sans barème) — un barrage se règle sur
        # une phase de n'importe quel type, alors que le barème est propre à la qualification.
        politiques = config.setdefault("policies", {})
        if isinstance(politiques, dict):
            politiques["tiebreak"] = {"nom": "barrage", "jusqu_au": barrage_jusqu_au}
    if profondeur is not None:
        # Même forme, même raison (E06US006) : `config.policies.depth = {"nom": …, "jusqu_au": …}`.
        # **Rien n'est écrit quand la profondeur n'est pas réglée**, et l'absence n'est pas ambiguë
        # ici — contrairement au grain, elle veut dire la même chose dans les deux tables : « preset
        # du type », soit le podium. C'est pourquoi `depth` échappe à `marquer_absences` : écrire
        # `null` pour distinguer « pas choisi » de « pas encore écrit » distinguerait deux états qui
        # se relisent à l'identique, et donnerait au lecteur une nuance sans conséquence.
        politiques_depth = config.setdefault("policies", {})
        if isinstance(politiques_depth, dict):
            politiques_depth["depth"] = profondeur.en_config()
    if poules is not None:
        # Le réglage d'une phase de poules vit **à la racine du `config`**, comme `validation`,
        # `sources` et `effectif` — et non sous `policies` (E05US023, ADR-0083).
        #
        # ⚠️ `config.policies` est un **catalogue fermé** : `FamillePolitique` l'énumère et
        # `assembler_politiques` lève `PolitiqueMalFormee` sur toute clé hors liste. Y ranger le
        # réglage rendait illisible **toute phase de poules** le jour où l'on branche cette
        # vérification. Et c'est juste sur le fond : une taille de poule est un **paramètre de
        # phase**, pas une stratégie injectable — d'où la disparition du `nom`.
        reglage: dict[str, object] = {"taille": poules.taille_visee}
        # Le barème est **toujours** écrit, y compris quand il vaut le défaut 3/1/0 : c'est un
        # choix de l'organisateur, et le relire d'un défaut de code ferait changer ses points
        # de match le jour où le défaut change. Les deux autres clés, elles, ne s'écrivent que
        # si elles sont réglées — leur absence *signifie* quelque chose (« la poule classe »,
        # « round-robin complet »), qu'un `null` explicite ne dirait pas mieux.
        reglage["bareme"] = [
            poules.bareme.victoire,
            poules.bareme.nul,
            poules.bareme.defaite,
        ]
        if poules.nb_qualifies is not None:
            reglage["qualifies"] = poules.nb_qualifies
        if poules.rencontres_par_archer is not None:
            reglage["rencontres"] = poules.rencontres_par_archer
        # Même règle que les deux clés ci-dessus : l'absence **signifie** le défaut (« les
        # archers d'un même rang de poule restent ex æquo »), qui est aussi le régime de toute
        # phase écrite avant que l'option existe. Écrire `false` explicitement ne dirait rien de
        # plus et ferait diverger deux documents équivalents.
        if poules.departage_inter_poules:
            reglage["departage"] = True
        # Même règle encore, et c'est elle qui évite la migration (E05US029) : le **serpent** étant
        # le défaut et le comportement de toujours, ne rien écrire dit exactement ce que disent les
        # documents déjà en base. Seul `par_niveau` s'inscrit, et la dérogation avec lui.
        if poules.mode is not ModeDeComposition.SERPENT:
            reglage["mode"] = poules.mode.value
        if poules.serpent_assume:
            reglage["serpent_assume"] = True
        config["poules"] = reglage
    if big_shoot_off is not None:
        # Même domicile et même raison que `poules` : racine du `config`, pas `policies` — c'est un
        # paramètre de phase, et `policies` est un catalogue **fermé** de stratégies injectables.
        # Aucune migration, donc : ADR-0046 laisse le document libre à la racine.
        souffle: dict[str, object] = {"eliminations": list(big_shoot_off.eliminations)}
        # Le format du tir est **toujours** écrit, y compris aux défauts (1 volée de 3), pour la
        # même raison que le barème de poule : c'est un choix de l'organisateur, et le relire d'un
        # défaut de code ferait changer son nombre de flèches le jour où le défaut change.
        souffle["volees"] = big_shoot_off.volees
        souffle["fleches"] = big_shoot_off.fleches_par_volee
        # Les deux options ne s'écrivent **que si elles sont actives** : leur absence signifie le
        # défaut, qui est aussi le régime de toute phase écrite avant qu'elles existent. Un `false`
        # explicite ne dirait rien de plus et ferait diverger deux documents équivalents.
        if big_shoot_off.cumul_des_manches:
            souffle["cumul"] = True
        if big_shoot_off.departage_les_sortants:
            souffle["departage_sortants"] = True
        config["big_shoot_off"] = souffle
    if suisse is not None:
        # Même domicile et même raison que ses deux voisins : racine du `config`, pas `policies`.
        # Un nombre de rondes est un **paramètre de phase**, et `policies` est le catalogue fermé
        # des familles injectables (`assembler_politiques` refuse toute clé hors énumération).
        # Aucune migration, donc : ADR-0046 laisse le document libre à la racine.
        config["suisse"] = {"rondes": suisse.nb_rondes}
    if colline is not None:
        # Même domicile et même raison que ses trois voisins : racine du `config`, hors `policies`.
        # Aucune migration — une étape écrite avant E05US027 se relit « non réglée », son état
        # antérieur : le type était composable, aucun service ne le déroulait.
        #
        # ⚠️ **Les DEUX champs s'écrivent toujours, `portee` comprise même à son défaut.** Elle
        # n'est pas une option qu'on active mais un **choix parmi deux formats** — 1 = King of the
        # Hill, 2+ = Ladder. L'omettre ferait disparaître de la base l'information « l'organisateur
        # a choisi le King of the Hill », et rendrait le document ambigu si le défaut changeait.
        config["colline"] = {
            "manches": colline.nb_manches,
            "portee": colline.portee_de_defi,
        }
    if decoupage is not None:
        # Même domicile et même raison que ses trois voisins : racine du `config`, hors `policies`
        # (catalogue fermé des familles injectables). **Aucune migration** — ADR-0046 laisse le
        # document libre à la racine, et une étape écrite avant E05US035 se relit « non découpée »,
        # soit exactement son comportement d'avant.
        config["decoupage"] = {"tours": decoupage.nb_tours}
    if arrets:
        # Une **liste**, et non un objet : c'est la lettre du CA (« plusieurs par phase »).
        # `portee` s'écrit toujours, y compris pour le défaut : ce n'est pas une option qu'on
        # active mais un choix parmi deux, et l'omettre rendrait un document relu ambigu le jour
        # où le défaut changerait — le raisonnement inverse de `cumul` du Big Shoot Off, où
        # l'absence *signifie* quelque chose.
        config["arrets"] = [
            {"apres_tour": arret.apres_tour, "portee": arret.portee.value} for arret in arrets
        ]
    if titre is not None:
        # Racine du `config`, hors `policies` — même domicile et même raison que `decoupage` et
        # `arrets` : un titre n'est pas une politique injectable (règle 2), c'est un libellé.
        # **Aucune migration** : une étape écrite avant E16US002 se relit sans titre, soit
        # exactement son comportement d'avant. Écrit **seulement s'il existe** — `None` et clé
        # absente disent la même chose ici (« pas de titre »), à la différence de `validation`
        # où la présence à `null` porte un sens.
        config["titre"] = titre
    if sources:
        config["sources"] = [_source_json(source) for source in sources]
    if effectif is not None:
        config["effectif"] = effectif
    return config


def _lire_profondeur(config: Any) -> ProfondeurClassement | None:
    """La profondeur de classement d'une phase, lue dans `config.policies.depth` (E06US006).

    Absence = **non réglée**, donc preset du type à l'usage — pas une incohérence : c'est le régime
    de toute phase écrite avant cette US (« politique sans migration », ADR-0011).

    Un `nom` inconnu lève `ValueError` via l'enum, traduit en « configuration illisible » : le
    trouver là veut dire que la base a été altérée.
    """
    politiques = config.get("policies")
    if not isinstance(politiques, dict):
        return None
    depth = politiques.get("depth")
    if not isinstance(depth, dict):
        return None
    jusqu_au = depth.get("jusqu_au")
    return ProfondeurClassement(
        nom=NomProfondeur(depth["nom"]),
        jusqu_au=None if jusqu_au is None else int(jusqu_au),
    )


def _lire_barrage_jusqu_au(config: Any) -> int | None:
    """Le seuil de barrage d'une phase, lu dans `config.policies.tiebreak` (E06US003, ADR-0066).

    Absence = **aucun barrage**, qui est le défaut d'E06US001 (les ex æquo partagent leur rang) —
    pas une incohérence. Un `tiebreak` d'un autre `nom` (`ffta_defaut`, `poules`) est un départage
    **sans** barrage : il n'a pas de seuil, et on n'en invente pas.
    """
    politiques = config.get("policies")
    if not isinstance(politiques, dict):
        return None
    tiebreak = politiques.get("tiebreak")
    if not isinstance(tiebreak, dict) or tiebreak.get("nom") != "barrage":
        return None
    return int(tiebreak["jusqu_au"])


def _lire_reglage_big_shoot_off(config: Any) -> ConfigurationBigShootOff | None:
    """Le réglage d'un Big Shoot Off, lu **à la racine** du `config` (E05US028).

    Même domicile et même régime d'absence que `_lire_reglage_poules` : racine plutôt que
    `policies`, et absence = **non réglé** — le type se choisit avant ses paramètres.
    ⚠️ **On relit par la fabrique du domaine**, jamais à la main : liste vide, case à zéro, flèches
    nulles sont des choses que le repository n'écrit jamais. Les trouver ici veut dire que la base a
    été altérée, et une liste altérée décrirait **qui sort** — la tolérer éliminerait des archers.
    """
    souffle = config.get("big_shoot_off")
    if not isinstance(souffle, dict):
        return None
    eliminations = souffle.get("eliminations")
    if not isinstance(eliminations, list):
        # Erreur **typée** plutôt que `None` : « pas de liste » se lirait « phase non réglée », et
        # la composition du jour J inventerait un déroulé là où la base dit quelque chose
        # d'incohérent. Même raisonnement que la `taille` absente d'un réglage de poules.
        raise InfrastructureError("Configuration d'étape de déroulé illisible.")
    volees = souffle.get("volees")
    fleches = souffle.get("fleches")
    return ConfigurationBigShootOff(
        eliminations=tuple(int(quota) for quota in eliminations),
        # Repli sur le défaut du domaine seulement si la clé manque — ce qui ne peut venir que
        # d'une ligne écrite à la main, l'écriture les posant toujours.
        volees=1 if volees is None else int(volees),
        fleches_par_volee=3 if fleches is None else int(fleches),
        cumul_des_manches=bool(souffle.get("cumul", False)),
        departage_les_sortants=bool(souffle.get("departage_sortants", False)),
    )


def _lire_reglage_suisse(config: Any) -> ConfigurationSuisse | None:
    """Le réglage d'une phase au système suisse, lu **à la racine** du `config` (E05US026).

    Même domicile et même régime d'absence que ses deux voisins ; on relit par la fabrique du
    domaine, un nombre de rondes nul signalant une base altérée (ADR-0007).
    ⚠️ **Aucune vérification contre l'effectif ici**, délibérément : la borne appariable est une
    propriété du couple (rondes, effectif), portée par `EtapeDeroule`. La refaire ici refuserait de
    **charger** un brouillon légitime — on ne rend pas illisible ce qui est seulement injouable.
    """
    souffle = config.get("suisse")
    if not isinstance(souffle, dict):
        return None
    rondes = souffle.get("rondes")
    if rondes is None:
        # Erreur **typée** plutôt que `None` : « pas de nombre de rondes » se lirait « phase non
        # réglée », et la composition du jour J inventerait un déroulé là où la base dit quelque
        # chose d'incohérent. Même raisonnement que la `taille` absente d'un réglage de poules.
        raise InfrastructureError("Configuration d'étape de déroulé illisible.")
    return ConfigurationSuisse(nb_rondes=int(rondes))


def _lire_reglage_colline(config: Any) -> ConfigurationColline | None:
    """Le réglage d'une phase de colline, lu **à la racine** du `config` (E05US027).

    Même domicile et même régime d'absence que ses trois voisins ; on relit par la fabrique du
    domaine, un nombre de manches ou une portée nuls signalant une base altérée (ADR-0007).
    ⚠️ **Une portée absente fait échouer la relecture** — elle ne se replie **pas** sur 1. Deviner
    « King of the Hill » sur un document qui disait « Ladder » ne produirait pas une phase un peu
    différente mais **un autre format**. Quand on ne sait pas, on refuse plutôt qu'on invente.
    """
    souffle = config.get("colline")
    if not isinstance(souffle, dict):
        return None
    manches = souffle.get("manches")
    portee = souffle.get("portee")
    if manches is None or portee is None:
        # Erreur **typée** plutôt que `None` : « pas de réglage » se lirait « phase non réglée », et
        # la composition du jour J inventerait un déroulé là où la base dit quelque chose
        # d'incohérent. Même raisonnement que le nombre de rondes absent d'un suisse.
        raise InfrastructureError("Configuration d'étape de déroulé illisible.")
    return ConfigurationColline(nb_manches=int(manches), portee_de_defi=int(portee))


def _lire_decoupage(config: Any) -> DecoupageEnTours | None:
    """Le découpage en tours d'une qualification, lu **à la racine** du `config` (E05US035).

    Absence = **pas de découpage**, donc la phase est son tour — le comportement de toute étape
    écrite avant cette US, ce qui rend la livraison sûre sans toucher au schéma.
    ⚠️ **Un nombre de tours illisible fait échouer la relecture**, à la différence d'une portée
    d'arrêt absente : un découpage deviné couperait la salle **au mauvais endroit**, et personne ne
    s'en apercevrait avant le jour J.
    """
    souffle = config.get("decoupage")
    if souffle is None:
        return None
    if not isinstance(souffle, dict) or souffle.get("tours") is None:
        raise InfrastructureError("Configuration d'étape de déroulé illisible.")
    return DecoupageEnTours(nb_tours=int(souffle["tours"]))


def _lire_titre(config: Any) -> str | None:
    """Relit le libellé d'une étape (E16US002) ; absent sur tout document antérieur.

    Aucune tolérance de forme à prévoir : les deux agrégats qui le portent (`EtapeDeroule`,
    `ModelePhase`) normalisent les espaces et ramènent le blanc à `None`. Ce qui n'est pas une
    chaîne remonte en `TypeError` → « configuration illisible », le régime de tous ses voisins.
    """
    souffle = config.get("titre")
    if souffle is None:
        return None
    if not isinstance(souffle, str):
        raise TypeError("Le titre d'une étape doit être une chaîne.")
    return souffle


def _lire_arrets(config: Any) -> tuple[ArretProgramme, ...]:
    """Les arrêts programmés d'une étape, lus **à la racine** du `config` (E05US033, ADR-0091).

    Absence = **aucun arrêt**, cas de toute étape écrite avant cette US : une base non migrée se
    relit en comportement inchangé. ⚠️ **La relecture vérifie bien la liste** — `_vers_etape`
    construit une `EtapeDeroule`, dont le `__post_init__` appelle `_verifier_arrets_applicables` :
    un doublon ou un arrêt inerte rend l'étape **inchargeable**. ⚠️ `portee` absente se relit
    `PHASE` — en cas de doute on coupe le moins, une portée inconnue élargissant l'arrêt.
    """
    souffle = config.get("arrets")
    if not isinstance(souffle, list):
        return ()
    arrets = []
    for brut in souffle:
        if not isinstance(brut, dict):
            raise InfrastructureError("Configuration d'étape de déroulé illisible.")
        apres_tour = brut.get("apres_tour")
        if apres_tour is None:
            raise InfrastructureError("Configuration d'étape de déroulé illisible.")
        portee = brut.get("portee")
        arrets.append(
            ArretProgramme(
                apres_tour=int(apres_tour),
                portee=PorteeArret(portee) if portee else PorteeArret.PHASE,
            )
        )
    return tuple(arrets)


def _lire_reglage_poules(config: Any) -> ReglageDePoules | None:
    """Le réglage d'une phase de poules, lu **à la racine** du `config` (E05US023, ADR-0083).

    Racine et non `policies` (catalogue fermé, cf. l'écriture). Absence = **non réglée**, licite :
    c'est la composition du jour J qui exigera le réglage, pas la relecture (brouillon d'ADR-0063).
    ⚠️ **On relit par la fabrique du domaine** — taille de 1, barème récompensant la défaite, plus
    de qualifiés que de membres signalent une base altérée. Le `bareme` est relu de la liste écrite
    et **jamais** du défaut de code : si 3/1/0 changeait, les tournois réglés le garderaient.
    """
    poules = config.get("poules")
    if not isinstance(poules, dict):
        return None
    taille = poules.get("taille")
    if taille is None:
        # ⚠️ Erreur **typée**, et non `KeyError` nu ni `None` silencieux.
        #
        # `_vers_modele_phase` appelle cette fonction **hors** du `try/except` qui enveloppe la
        # lecture d'une étape : un `int(poules["taille"])` sur une clé absente en sortait donc en
        # `KeyError`, donc en 500 brut, au lieu du « configuration illisible » d'ADR-0007 que la
        # docstring annonce (relevé en revue). Rendre `None` serait pire encore : « pas de taille »
        # se lirait « phase non réglée », et le jour J la composition inventerait une répartition
        # là où la base dit quelque chose d'incohérent.
        raise InfrastructureError("Configuration d'étape de déroulé illisible.")
    bareme = poules.get("bareme")
    qualifies = poules.get("qualifies")
    rencontres = poules.get("rencontres")
    return ReglageDePoules(
        taille_visee=int(taille),
        bareme=(
            BaremePoule(victoire=int(bareme[0]), nul=int(bareme[1]), defaite=int(bareme[2]))
            if isinstance(bareme, list) and len(bareme) >= 3
            else BaremePoule()
        ),
        nb_qualifies=None if qualifies is None else int(qualifies),
        rencontres_par_archer=None if rencontres is None else int(rencontres),
        departage_inter_poules=poules.get("departage") is True,
        mode=_mode_de_composition(poules.get("mode")),
        serpent_assume=poules.get("serpent_assume") is True,
    )


def _mode_de_composition(valeur: object) -> ModeDeComposition:
    """Le mode de composition écrit au JSON, ou le **serpent** (E05US029).

    ⚠️ **Aucune migration** : le réglage vit dans le `config` JSON, pas dans une colonne. Un
    document écrit avant cette US n'a pas la clé et compose au serpent — ce qu'il faisait déjà.

    Une valeur **inconnue** remonte en « configuration illisible » plutôt que de retomber sur le
    défaut : composer au serpent « par prudence » monterait un tournoi que personne n'a réglé.
    """
    if valeur is None:
        return ModeDeComposition.SERPENT
    try:
        return ModeDeComposition(valeur)
    except ValueError as erreur:
        raise InfrastructureError("Configuration d'étape de déroulé illisible.") from erreur


def _source_json(source: SourcePhase) -> dict[str, object]:
    """Un prélèvement en JSON — **seuls** les champs de sa nature sont écrits.

    N'écrire que le pertinent garde le document lisible et empêche qu'un champ mort (un `tour` sur
    un prélèvement par rangs) ressuscite à la relecture en `SourceMalFormee`.
    """
    if source.nature is NatureSource.ISSUE_DE_TOUR:
        return {
            "nature": source.nature.value,
            "ordre_source": source.ordre_source,
            "tour": source.tour,
            "issue": source.issue.value if source.issue is not None else None,
        }
    if source.nature is NatureSource.RESTE:
        return {"nature": source.nature.value, "ordre_source": source.ordre_source}
    return {
        "nature": source.nature.value,
        "ordre_source": source.ordre_source,
        "rang_debut": source.rang_debut,
        "rang_fin": source.rang_fin,
    }


def _config_format(format_tournoi: FormatTournoi) -> str:
    """Sérialise la séquence de modèles de phases d'un format (`{"etapes": [...]}`).

    Chaque étape reprend la forme d'une `config` de phase, augmentée de son `ordre` et de son
    `type` — que `PhaseORM` porte en colonnes et qu'un format doit ranger dans le JSON.
    `effectif_minimum_exige` s'ajoute **à côté** des étapes : propriété du format entier, lue et
    écrite en bloc. La clé est **omise** quand rien n'est exigé, pour qu'une config d'avant l'US et
    une config sans exigence soient le même document.
    """
    exigence = (
        {}
        if format_tournoi.effectif_minimum_exige is None
        else {"effectif_minimum_exige": format_tournoi.effectif_minimum_exige}
    )
    return json.dumps(
        {
            "etapes": [
                {
                    "ordre": etape.ordre,
                    "type": etape.type.value,
                    **_politiques_json(
                        etape.bareme,
                        etape.validation,
                        etape.sources,
                        etape.effectif,
                        # ⚠️ **`barrage_jusqu_au` était omis ici** alors que `ModelePhase` le porte
                        # depuis le 07/08/2026 : un format promu depuis un tournoi dont une phase
                        # avait un seuil de barrage le perdait **en silence** — exactement le
                        # défaut que l'ajout du champ prétendait fermer, déplacé de l'agrégat à sa
                        # sérialisation. Constaté en câblant `poules` par le même chemin ; corrigé
                        # ici plutôt que consigné, parce qu'il coûte un argument et qu'il détruit
                        # de la donnée d'organisateur (règle « un bug corrigeable dans l'US »).
                        barrage_jusqu_au=etape.barrage_jusqu_au,
                        profondeur=etape.profondeur,
                        poules=etape.poules,
                        big_shoot_off=etape.big_shoot_off,
                        suisse=etape.suisse,
                        # E05US027 : câblé dès l'ajout du champ, comme `arrets` ci-dessous et pour
                        # la raison que le commentaire de `barrage_jusqu_au` porte — un champ ajouté
                        # à l'agrégat mais absent de sa sérialisation rouvre le défaut que l'ajout
                        # prétendait fermer, et détruit de la donnée d'organisateur. Ici il ferait
                        # perdre au **format capturé** son King of the Hill, qui se rejouerait non
                        # réglé.
                        colline=etape.colline,
                        decoupage=etape.decoupage,
                        # E05US033 : câblés dès l'ajout du champ, et non « plus tard ». Le
                        # commentaire de `barrage_jusqu_au` juste au-dessus dit ce que coûte
                        # l'oubli — un champ ajouté à l'agrégat mais absent de sa sérialisation
                        # rouvre exactement le défaut que l'ajout prétendait fermer, déplacé de
                        # l'agrégat à sa persistance, et il détruit de la donnée d'organisateur.
                        arrets=etape.arrets,
                        # E16US002 : **le défaut que les trois commentaires ci-dessus racontent a
                        # été rejoué ici même**, et quatre axes de revue l'ont relevé. `titre` avait
                        # été câblé sur `_config_etape` (la table `deroule_etape`) et **oublié sur
                        # cet appelant-ci** : un format perdait donc TOUS ses titres à l'écriture,
                        # le champ de « Composer un format » était inerte, et `promouvoir` faisait
                        # remonter un format anonyme l'année suivante. `_politiques_json` a **deux**
                        # appelants ; en câbler un seul est le mode de panne de ce fichier.
                        titre=etape.titre,
                        marquer_absences=True,
                        porte_un_bareme=etape.type is TypePhase.QUALIFICATION,
                    ),
                }
                for etape in format_tournoi.etapes
            ],
            **exigence,
        }
    )


def _vers_format(ligne: FormatTournoiORM) -> FormatTournoi:
    """Traduit une ligne ORM en agrégat `FormatTournoi` (config JSON → séquence de modèles).

    Même régime qu'`_vers_phase` (ADR-0007) : le repository est le **seul** rédacteur de cette
    colonne et n'écrit que des valeurs valides, donc une `config` illisible **ou hors règle** est
    une incohérence **technique** → `InfrastructureError`, jamais un agrégat silencieusement
    invalide. On repasse donc par les fabriques du domaine, `FormatTournoi.creer` comprise : c'est
    elle qui rejoue les invariants de séquence (ordres contigus, sources antérieures).
    """
    try:
        config = json.loads(ligne.config)
        etapes = [_vers_modele_phase(brute) for brute in config["etapes"]]
        return dataclasses.replace(
            FormatTournoi.creer(
                ligne.nom,
                etapes,
                OrigineBrique(ligne.origine),
                # Absente des configs antérieures à E05US021 : leur relecture rend `None`, soit
                # exactement le comportement d'avant l'US.
                effectif_minimum_exige=config.get("effectif_minimum_exige"),
            ),
            id=ligne.id,
        )
    except (
        json.JSONDecodeError,
        AttributeError,
        KeyError,
        TypeError,
        ValueError,
        DomainError,
    ) as exc:
        raise InfrastructureError("Configuration de format de tournoi illisible.") from exc


def _vers_modele_phase(brute: Any) -> ModelePhase:
    """Relit un modèle d'étape depuis sa forme JSON.

    Le barème n'est lu que pour une `qualification` (ADR-0045 §2) ; le grain absent retombe sur le
    preset du type (ADR-0011). ⚠️ **Un modèle d'étape peut n'avoir ni barème ni grain depuis
    E01US024** — le brouillon du CA. Lire `_lire_scoring` inconditionnellement faisait remonter un
    `KeyError` en 500 **après** le commit ; `lister()` mappant *toutes* les lignes, un seul
    brouillon incomplet mettait la bibliothèque entière en 500 sans route pour l'effacer.
    """
    type_phase = TypePhase(brute["type"])
    bareme = None
    scoring = _lire_scoring_facultatif(brute) if type_phase is TypePhase.QUALIFICATION else None
    if scoring is not None:
        bareme = BaremeQualification.creer(
            nb_volees=int(scoring["volees"]),
            nb_fleches_par_volee=int(scoring["fleches"]),
        )
    # Le grain se relit **quel que soit le type**, contrairement à `_vers_phase`. Motif :
    # `_politiques_json` l'**écrit** pour tout type, et `ModelePhase` accepte un `fin_de_duel` sur
    # une élimination directe (`_GRAINS_ADMIS`). Ne le relire que pour la qualification revenait à
    # écrire ce qu'on ne relit pas — un aller-retour infidèle, sans erreur : un format promu depuis
    # un tournoi dont l'élimination porte un grain le perdait en silence. Le repli sur le preset du
    # type reste réservé à la qualification, où l'absence signifie « écrit avant E01US015 ».
    validation = None
    if brute.get("validation") is not None:
        validation = _vers_grain(brute["validation"])
    elif "validation" not in brute and type_phase is TypePhase.QUALIFICATION:
        # Clé **absente** = format écrit avant E01US015 → preset du type. Clé **présente à `null`**
        # = le rédacteur n'a pas (encore) choisi de grain : on ne la remplit pas, sans quoi le
        # diagnostic ne pourrait jamais signaler `phase_qualification_incomplete` pour ce cas.
        validation = grain_par_defaut(type_phase)
    effectif = brute.get("effectif")
    return ModelePhase(
        ordre=int(brute["ordre"]),
        type=type_phase,
        bareme=bareme,
        validation=validation,
        sources=_vers_sources(brute),
        effectif=None if effectif is None else int(effectif),
        barrage_jusqu_au=_lire_barrage_jusqu_au(brute),
        profondeur=_lire_profondeur(brute),
        poules=_lire_reglage_poules(brute),
        big_shoot_off=_lire_reglage_big_shoot_off(brute),
        suisse=_lire_reglage_suisse(brute),
        colline=_lire_reglage_colline(brute),
        decoupage=_lire_decoupage(brute),
        arrets=_lire_arrets(brute),
        titre=_lire_titre(brute),
    )


def _vers_affectation(ligne: PlacementORM) -> Affectation:
    """Traduit une ligne ORM `placement` en value object de domaine `Affectation`."""
    return Affectation(
        inscription_id=ligne.inscription_id,
        cible_index=ligne.cible_index,
        position=ligne.position,
    )


class PlacementRepositorySQL:
    """Adapter SQLite du port `PlacementRepository` — plan de cibles matérialisé (E03US004).

    `definir_plan_avec_trace` (E12US007) réalise la **couture de session partagée** (ADR-0035),
    comme `SerieRepositorySQL.enregistrer_avec_trace` : le plan **et** son entrée d'audit s'écrivent
    dans **une seule session, un seul `commit`**. D'où l'`AuditRepositorySQL` injecté — couplage
    **infra → infra** (le port `PlacementRepository` ignore cette couture ; sa signature ne cite
    aucune session).
    """

    def __init__(
        self, session_factory: sessionmaker[Session], audit_repository: AuditRepositorySQL
    ) -> None:
        self._session_factory = session_factory
        self._audit = audit_repository

    def par_depart(self, depart_id: DepartId) -> list[Affectation]:
        """Renvoie les affectations d'un départ, triées par cible puis position (ordre stable)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(PlacementORM)
                    .where(PlacementORM.depart_id == depart_id)
                    .order_by(PlacementORM.cible_index, PlacementORM.position)
                ).scalars()
                return [_vers_affectation(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du plan de cibles.") from exc

    def definir_plan(self, depart_id: DepartId, affectations: Sequence[Affectation]) -> None:
        """Purge le plan du départ puis insère les affectations données — **une** transaction."""
        try:
            with self._session_factory() as session:
                session.execute(delete(PlacementORM).where(PlacementORM.depart_id == depart_id))
                session.add_all(
                    PlacementORM(
                        inscription_id=affectation.inscription_id,
                        depart_id=depart_id,
                        cible_index=affectation.cible_index,
                        position=affectation.position,
                    )
                    for affectation in affectations
                )
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de définition du plan de cibles.") from exc

    def definir_plan_avec_trace(
        self, depart_id: DepartId, affectations: Sequence[Affectation], entree: EntreeAudit
    ) -> None:
        """Remplace le plan **et** co-écrit sa trace d'audit en une transaction (E12US007).

        Tout ou rien : purge + réinsertion du plan, puis la trace via
        `AuditRepositorySQL.consigner_dans` (qui ne commit pas), puis un **unique** `commit` scelle
        les deux (ADR-0035). Un échec avant le commit ne laisse ni replacement massif non tracé, ni
        trace fantôme.
        """
        try:
            with self._session_factory() as session:
                session.execute(delete(PlacementORM).where(PlacementORM.depart_id == depart_id))
                session.add_all(
                    PlacementORM(
                        inscription_id=affectation.inscription_id,
                        depart_id=depart_id,
                        cible_index=affectation.cible_index,
                        position=affectation.position,
                    )
                    for affectation in affectations
                )
                self._audit.consigner_dans(session, entree)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError(
                "Échec de définition du plan de cibles et de sa trace."
            ) from exc

    def poser_plusieurs(self, depart_id: DepartId, affectations: Sequence[Affectation]) -> None:
        """Insère ou met à jour chaque affectation (clé = inscription) — **une** transaction."""
        try:
            with self._session_factory() as session:
                for affectation in affectations:
                    ligne = session.get(PlacementORM, affectation.inscription_id)
                    if ligne is None:
                        session.add(
                            PlacementORM(
                                inscription_id=affectation.inscription_id,
                                depart_id=depart_id,
                                cible_index=affectation.cible_index,
                                position=affectation.position,
                            )
                        )
                    else:
                        ligne.depart_id = depart_id
                        ligne.cible_index = affectation.cible_index
                        ligne.position = affectation.position
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec d'écriture du plan de cibles.") from exc

    def retirer(self, inscription_id: InscriptionId) -> None:
        """Retire l'affectation d'un inscrit (mise en réserve) ; sans effet s'il n'en avait pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(PlacementORM, inscription_id)
                if ligne is not None:
                    session.delete(ligne)
                    session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise en réserve.") from exc


def _vers_affectation_tableau(ligne: PlacementTableauORM) -> Affectation:
    """Traduit une ligne ORM `placement_tableau` en value object de domaine `Affectation`."""
    return Affectation(
        inscription_id=ligne.inscription_id,
        cible_index=ligne.cible_index,
        position=ligne.position,
    )


class PlacementParBlocRepositorySQL:
    """Adapter SQLite du port `PlacementParBlocRepository` — plan de blocs matérialisé (E05US023).

    Seul adapter de placement dont l'unité posée soit un **groupe** : une ligne par couloir, portant
    sa poule et son rang dans le bloc (ADR-0083 §3). Deux gestes contre quatre pour son aîné — un
    plan de blocs se repose, il ne s'ajuste pas archer par archer. Pas de couture d'audit (même
    raison que `PlacementTableauRepositorySQL`) : aucune rencontre n'est encore tirée quand on pose
    les poules, la repose n'est jamais « massive » (E12US007).
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def par_phase(self, phase_id: PhaseId) -> list[BlocDeCouloirs]:
        """Relit les blocs d'une phase, chacun dans son **ordre de remplissage**.

        Le tri porte sur `(groupe_numero, rang)` et non sur `(cible_index, position)` : c'est le
        **rang** qui dit l'ordre du bloc, et lui seul. Trier par cible donnerait le même résultat
        sur une salle homogène — et se tromperait dès qu'une cible a une capacité réduite,
        précisément le cas que `GabaritSalle.ajuster` rend possible.
        """
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(PlacementParBlocORM)
                    .where(PlacementParBlocORM.phase_id == phase_id)
                    .order_by(PlacementParBlocORM.groupe_numero, PlacementParBlocORM.rang)
                ).scalars()
                blocs: dict[int, list[tuple[int, str]]] = {}
                for ligne in lignes:
                    blocs.setdefault(ligne.groupe_numero, []).append(
                        (ligne.cible_index, ligne.position)
                    )
                return [
                    BlocDeCouloirs(groupe=numero, places=tuple(places))
                    for numero, places in blocs.items()
                ]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du plan de blocs.") from exc

    def definir_plan(self, phase_id: PhaseId, blocs: Sequence[BlocDeCouloirs]) -> None:
        """Purge le plan de blocs de la phase puis insère les blocs — **une** transaction."""
        try:
            with self._session_factory() as session:
                session.execute(
                    delete(PlacementParBlocORM).where(PlacementParBlocORM.phase_id == phase_id)
                )
                session.add_all(
                    PlacementParBlocORM(
                        phase_id=phase_id,
                        cible_index=cible_index,
                        position=position,
                        groupe_numero=bloc.groupe,
                        rang=rang,
                    )
                    for bloc in blocs
                    for rang, (cible_index, position) in enumerate(bloc.places, start=1)
                )
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de définition du plan de blocs.") from exc


class PlacementTableauRepositorySQL:
    """Adapter SQLite du port `PlacementTableauRepository` — plan de duels matérialisé (E03US009).

    Jumeau de `PlacementRepositorySQL`, scoppé par **phase** et **tour** au lieu du départ, clé
    composite `(phase_id, tour, inscription_id)` — l'ordre de la clé suit celui des colonnes du
    modèle, dont dépendent les `session.get` ci-dessous. Pas de couture d'audit : le service
    **refuse** de régénérer un tour qui a déjà tiré, jamais de régénération « massive » au sens
    d'E12US007 (ADR-0048/0106) — donc pas de `definir_plan_avec_trace`.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def par_phase_et_tour(self, phase_id: PhaseId, tour: int) -> list[Affectation]:
        """Les affectations d'un tour, triées par cible puis position (ordre stable)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(PlacementTableauORM)
                    .where(
                        PlacementTableauORM.phase_id == phase_id,
                        PlacementTableauORM.tour == tour,
                    )
                    .order_by(PlacementTableauORM.cible_index, PlacementTableauORM.position)
                ).scalars()
                return [_vers_affectation_tableau(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du plan de duels.") from exc

    def par_phase(self, phase_id: PhaseId) -> list[Affectation]:
        """**Toutes** les poses d'une phase, tous tours confondus — question distincte du plan.

        ⚠️ Ne sert **pas** au plan de duels (qui lit un tour, `par_phase_et_tour`) mais au port
        `application.formats.LecteurDonneesDePhase` : « cette phase porte-t-elle des données qui
        s'opposent à un remplacement de format ? ». Une pose à n'importe quel tour compte.
        """
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(PlacementTableauORM)
                    .where(PlacementTableauORM.phase_id == phase_id)
                    .order_by(
                        PlacementTableauORM.tour,
                        PlacementTableauORM.cible_index,
                        PlacementTableauORM.position,
                    )
                ).scalars()
                return [_vers_affectation_tableau(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du plan de duels.") from exc

    def definir_plan(
        self, phase_id: PhaseId, tour: int, affectations: Sequence[Affectation]
    ) -> None:
        """Purge le plan **de ce tour** puis insère les affectations — **une** transaction."""
        try:
            with self._session_factory() as session:
                session.execute(
                    delete(PlacementTableauORM).where(
                        PlacementTableauORM.phase_id == phase_id,
                        PlacementTableauORM.tour == tour,
                    )
                )
                session.add_all(
                    PlacementTableauORM(
                        phase_id=phase_id,
                        tour=tour,
                        inscription_id=affectation.inscription_id,
                        cible_index=affectation.cible_index,
                        position=affectation.position,
                    )
                    for affectation in affectations
                )
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de définition du plan de duels.") from exc

    def poser_plusieurs(
        self, phase_id: PhaseId, tour: int, affectations: Sequence[Affectation]
    ) -> None:
        """Insère/met à jour chaque affectation (clé phase + tour + inscription), **une**
        transaction."""
        try:
            with self._session_factory() as session:
                for affectation in affectations:
                    ligne = session.get(
                        PlacementTableauORM, (phase_id, tour, affectation.inscription_id)
                    )
                    if ligne is None:
                        session.add(
                            PlacementTableauORM(
                                phase_id=phase_id,
                                tour=tour,
                                inscription_id=affectation.inscription_id,
                                cible_index=affectation.cible_index,
                                position=affectation.position,
                            )
                        )
                    else:
                        ligne.cible_index = affectation.cible_index
                        ligne.position = affectation.position
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec d'écriture du plan de duels.") from exc

    def retirer(self, phase_id: PhaseId, tour: int, inscription_id: InscriptionId) -> None:
        """Retire l'affectation d'un inscrit à ce tour ; sans effet s'il n'en avait pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(PlacementTableauORM, (phase_id, tour, inscription_id))
                if ligne is not None:
                    session.delete(ligne)
                    session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise en réserve.") from exc


class FormatTournoiRepositorySQL:
    """Adapter SQLite du port `FormatTournoiRepository` (E01US023, ADR-0060 §5).

    Pas de `par_tournoi` : un format n'existe qu'en bibliothèque, sa copie dans un tournoi étant
    les **phases** produites par son application (`PhaseRepositorySQL`).
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, format_tournoi: FormatTournoi) -> FormatTournoi:
        """Persiste un format et le renvoie avec son identifiant attribué.

        Le `nom` étant `UNIQUE`, un homonyme remonte en `InfrastructureError` : le refus
        fonctionnel (409) est porté en amont par le service, qui interroge `par_nom` d'abord — la
        contrainte n'est ici qu'un garde-fou d'intégrité (même patron que `club`).
        """
        try:
            with self._session_factory() as session:
                ligne = FormatTournoiORM(
                    nom=format_tournoi.nom,
                    origine=format_tournoi.origine.value,
                    config=_config_format(format_tournoi),
                )
                session.add(ligne)
                session.commit()
                return _vers_format(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance du format de tournoi.") from exc

    def par_id(self, format_id: FormatTournoiId) -> FormatTournoi | None:
        """Relit le format d'identifiant donné, ou `None` s'il n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(FormatTournoiORM, format_id)
                return None if ligne is None else _vers_format(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du format de tournoi.") from exc

    def lister(self) -> list[FormatTournoi]:
        """Renvoie toute la bibliothèque de formats, par identifiant croissant."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(FormatTournoiORM).order_by(FormatTournoiORM.id)
                ).scalars()
                return [_vers_format(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des formats de tournoi.") from exc

    def par_nom(self, nom: str) -> FormatTournoi | None:
        """Renvoie le format de ce nom exact, ou `None` (sert à l'idempotence de la promotion)."""
        try:
            with self._session_factory() as session:
                ligne = session.execute(
                    select(FormatTournoiORM).where(FormatTournoiORM.nom == nom)
                ).scalar_one_or_none()
                return None if ligne is None else _vers_format(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du format de tournoi.") from exc

    def enregistrer(self, format_tournoi: FormatTournoi) -> FormatTournoi:
        """Met à jour un format déjà persisté (édition, promotion) et le renvoie."""
        assert format_tournoi.id is not None, "Un format enregistré a déjà un identifiant."
        try:
            with self._session_factory() as session:
                ligne = session.get(FormatTournoiORM, format_tournoi.id)
                if ligne is None:
                    raise InfrastructureError("Format de tournoi à mettre à jour introuvable.")
                ligne.nom = format_tournoi.nom
                ligne.origine = format_tournoi.origine.value
                ligne.config = _config_format(format_tournoi)
                session.commit()
                return _vers_format(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour du format de tournoi.") from exc

    def supprimer(self, format_id: FormatTournoiId) -> None:
        """Supprime un format. Les phases appliquées ne le référencent pas : elles survivent."""
        try:
            with self._session_factory() as session:
                ligne = session.get(FormatTournoiORM, format_id)
                if ligne is None:
                    raise InfrastructureError("Format de tournoi à supprimer introuvable en base.")
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression du format de tournoi.") from exc


class DerouleEtapeRepositorySQL:
    """Adapter SQLite du port `DerouleRepository` — la **définition** du déroulé (ADR-0076)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, etape: EtapeDeroule) -> EtapeDeroule:
        """Persiste une étape et la renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = DerouleEtapeORM(
                    tournoi_id=etape.tournoi_id,
                    ordre=etape.ordre,
                    type=etape.type.value,
                    config=_config_etape(etape),
                )
                session.add(ligne)
                session.commit()
                return _vers_etape(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance de l'étape de déroulé.") from exc

    def par_tournoi(self, tournoi_id: TournoiId) -> list[EtapeDeroule]:
        """Le déroulé du tournoi, **ordonné par `ordre`** — le tri est garanti par le port."""
        try:
            with self._session_factory() as session:
                lignes = (
                    session.execute(
                        select(DerouleEtapeORM)
                        .where(DerouleEtapeORM.tournoi_id == tournoi_id)
                        .order_by(DerouleEtapeORM.ordre)
                    )
                    .scalars()
                    .all()
                )
                return [_vers_etape(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du déroulé du tournoi.") from exc

    def enregistrer(self, etape: EtapeDeroule) -> EtapeDeroule:
        """Met à jour une étape déjà persistée (barème, grain, type, sources, rang…)."""
        try:
            with self._session_factory() as session:
                ligne = session.get(DerouleEtapeORM, etape.id)
                if ligne is None:
                    raise InfrastructureError("Étape de déroulé à mettre à jour introuvable.")
                ligne.ordre = etape.ordre
                ligne.type = etape.type.value
                ligne.config = _config_etape(etape)
                session.commit()
                return _vers_etape(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour de l'étape de déroulé.") from exc

    def reordonner(self, etapes: list[EtapeDeroule]) -> list[EtapeDeroule]:
        """Réécrit les rangs de tout un déroulé en **une** transaction, en deux passes.

        `uq_deroule_tournoi_ordre` interdit deux étapes de même rang, or échanger deux rangs voisins
        passe par cet état. On **gare** donc tous les rangs en négatif — domaine que la séquence
        1..N n'atteint jamais — avant de poser les rangs voulus. ⚠️ Un `flush` sépare les deux
        passes : sans lui, SQLAlchemy ordonne librement les `UPDATE` d'un même vidage et la
        collision réapparaît au hasard des exécutions — le bug qui passe en test, tombe le jour J.
        """
        try:
            with self._session_factory() as session:
                lignes = []
                for etape in etapes:
                    ligne = session.get(DerouleEtapeORM, etape.id)
                    if ligne is None:
                        raise InfrastructureError(
                            "Étape de déroulé à réordonner introuvable en base."
                        )
                    lignes.append(ligne)
                for rang, ligne in enumerate(lignes, start=1):
                    ligne.ordre = -rang
                session.flush()
                for etape, ligne in zip(etapes, lignes, strict=True):
                    ligne.ordre = etape.ordre
                    ligne.type = etape.type.value
                    ligne.config = _config_etape(etape)
                session.commit()
                return [_vers_etape(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec du réordonnancement du déroulé.") from exc

    def supprimer(self, etape_id: EtapeDerouleId) -> None:
        """Supprime une étape du déroulé (existence garantie par l'appelant)."""
        try:
            with self._session_factory() as session:
                ligne = session.get(DerouleEtapeORM, etape_id)
                if ligne is None:
                    raise InfrastructureError("Étape de déroulé à supprimer introuvable.")
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression de l'étape de déroulé.") from exc


class FranchissementArretRepositorySQL:
    """Adapter SQLite du port `FranchissementArretRepository` (E05US033, ADR-0091).

    Ne persiste que l'**avancement** d'un arrêt, jamais sa définition — celle-ci vit dans
    `deroule_etape.config` et se lit par `DerouleRepository`. La lecture **par créneau** impose une
    jointure `franchissement_arret → phase` : dupliquer `depart_id` serait une seconde source pour
    ce que la phase dit déjà (DETTE-026).
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def par_depart(self, depart_id: DepartId) -> list[FranchissementArret]:
        """Tous les franchissements du créneau, quel qu'en soit l'état."""
        try:
            with self._session_factory() as session:
                lignes = (
                    session.execute(
                        select(FranchissementArretORM)
                        .join(PhaseORM, PhaseORM.id == FranchissementArretORM.phase_id)
                        .where(PhaseORM.depart_id == depart_id)
                        .order_by(FranchissementArretORM.id)
                    )
                    .scalars()
                    .all()
                )
                return [_vers_franchissement(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des arrêts programmés.") from exc

    def par_id(self, franchissement_id: int) -> FranchissementArret | None:
        try:
            with self._session_factory() as session:
                ligne = session.get(FranchissementArretORM, franchissement_id)
                return None if ligne is None else _vers_franchissement(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture d'un arrêt programmé.") from exc

    def ajouter(self, franchissement: FranchissementArret) -> FranchissementArret:
        try:
            with self._session_factory() as session:
                ligne = FranchissementArretORM(
                    phase_id=franchissement.phase_id,
                    apres_tour=franchissement.apres_tour,
                    etat=franchissement.etat.value,
                    tours_a_finir=_tours_a_finir_json(franchissement.tours_a_finir),
                    phases_arretees=json.dumps(list(franchissement.phases_arretees)),
                    arrete_depuis=franchissement.arrete_depuis,
                )
                session.add(ligne)
                session.commit()
                session.refresh(ligne)
                return _vers_franchissement(ligne)
        except IntegrityError as exc:
            # L'unicité `(phase_id, apres_tour)` a parlé : deux écritures concurrentes du même
            # franchissement. Ce n'est pas une incohérence mais la **course** que la contrainte est
            # là pour arbitrer — le déclencheur tourne après chaque validation, et ~30 tablettes
            # valident.
            raise InfrastructureError("Cet arrêt a déjà été franchi dans ce créneau.") from exc
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec d'enregistrement d'un arrêt franchi.") from exc

    def enregistrer(self, franchissement: FranchissementArret) -> FranchissementArret:
        try:
            with self._session_factory() as session:
                ligne = session.get(FranchissementArretORM, franchissement.id)
                if ligne is None:
                    raise InfrastructureError("Arrêt programmé à mettre à jour introuvable.")
                ligne.etat = franchissement.etat.value
                ligne.tours_a_finir = _tours_a_finir_json(franchissement.tours_a_finir)
                ligne.phases_arretees = json.dumps(list(franchissement.phases_arretees))
                ligne.arrete_depuis = franchissement.arrete_depuis
                session.commit()
                session.refresh(ligne)
                return _vers_franchissement(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour d'un arrêt programmé.") from exc


def _tours_a_finir_json(tours: tuple[tuple[PhaseId, int | None], ...]) -> str:
    """Sérialise la photo des tours à finir. Les clés JSON sont des **chaînes**, par nature."""
    return json.dumps({str(phase_id): tour for phase_id, tour in tours})


def _vers_franchissement(ligne: FranchissementArretORM) -> FranchissementArret:
    """Relit un franchissement. Une ligne illisible est une base altérée, pas un doute.

    ⚠️ SQLite stocke un `DateTime` **sans fuseau** : on **réattache UTC** à la valeur relue, le
    service n'écrivant jamais que de l'UTC (port `Horloge`). Même geste que `_vers_entree_audit` et
    les relectures de `referentiel.py` / `tir.py`. L'omission ne se voit pas côté serveur : sans
    offset, `Date.parse` lit la forme en **heure locale**, et le « depuis N min » annonçait `+120`
    sur une salle arrêtée depuis une minute.
    """
    try:
        tours = json.loads(ligne.tours_a_finir)
        arretees = json.loads(ligne.phases_arretees)
        arrete_depuis = ligne.arrete_depuis
        if arrete_depuis is not None and arrete_depuis.tzinfo is None:
            arrete_depuis = arrete_depuis.replace(tzinfo=datetime.UTC)
        return FranchissementArret(
            phase_id=ligne.phase_id,
            apres_tour=ligne.apres_tour,
            etat=EtatFranchissement(ligne.etat),
            tours_a_finir=tuple((int(clef), valeur) for clef, valeur in tours.items()),
            phases_arretees=tuple(int(phase_id) for phase_id in arretees),
            arrete_depuis=arrete_depuis,
            id=ligne.id,
        )
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError) as exc:
        raise InfrastructureError("Arrêt programmé illisible en base.") from exc


class ArretDeCirconstanceRepositorySQL:
    """Adapter SQLite du port `ArretDeCirconstanceRepository` (E05US034, ADR-0092).

    Ne persiste que les arrêts **posés le jour J** ; ceux de l'atelier vivent dans
    `deroule_etape.config` (ADR-0076 §4 contre §5). ⚠️ **La table porte `depart_id`, contrairement
    à sa voisine** : `FranchissementArretRepositorySQL` joint sur `phase` parce que le créneau y est
    déductible, ici il ne l'est pas — le `depart_id` **est** ce qui distingue cet arrêt.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def par_depart(self, depart_id: DepartId) -> list[ArretDeCirconstance]:
        """Les arrêts de circonstance de **ce créneau seul**, du plus ancien tour au plus tardif."""
        try:
            with self._session_factory() as session:
                lignes = (
                    session.execute(
                        select(ArretDeCirconstanceORM)
                        .where(ArretDeCirconstanceORM.depart_id == depart_id)
                        .order_by(ArretDeCirconstanceORM.apres_tour)
                    )
                    .scalars()
                    .all()
                )
                return [_vers_arret_de_circonstance(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError(
                "Échec de lecture des pauses posées en cours de tournoi."
            ) from exc

    def ajouter(self, arret: ArretDeCirconstance) -> ArretDeCirconstance:
        try:
            with self._session_factory() as session:
                ligne = ArretDeCirconstanceORM(
                    depart_id=arret.depart_id,
                    phase_id=arret.phase_id,
                    apres_tour=arret.apres_tour,
                    portee=arret.portee.value,
                )
                session.add(ligne)
                session.commit()
                session.refresh(ligne)
                return _vers_arret_de_circonstance(ligne)
        except IntegrityError as exc:
            # L'unicité a parlé : deux poses du même arrêt. Le service refuse le doublon qu'il
            # voit ; celle-ci ferme la **course** — deux postes d'admin, ou un double-clic.
            #
            # ⚠️ **`ArretProgrammeInvalide` et non `InfrastructureError`** : le second est mappé en
            # **500 générique**, et l'organisateur qui double-clique en plein tournoi recevait
            # « erreur interne » pour un geste ordinaire. Le franchissement de couche est assumé —
            # cet adapter implémente un port du **domaine**, son contrat d'erreur est celui du
            # domaine (règle 2). Le message vient du domaine, il n'est pas recopié.
            raise doublon_d_arret([arret.apres_tour]) from exc
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec d'enregistrement d'une pause.") from exc


def _vers_arret_de_circonstance(ligne: ArretDeCirconstanceORM) -> ArretDeCirconstance:
    """Relit un arrêt de circonstance. Une ligne illisible est une base altérée, pas un doute."""
    try:
        return ArretDeCirconstance(
            depart_id=ligne.depart_id,
            phase_id=ligne.phase_id,
            apres_tour=ligne.apres_tour,
            portee=PorteeArret(ligne.portee),
            id=ligne.id,
        )
    except ValueError as exc:
        raise InfrastructureError("Pause posée illisible en base.") from exc


class PhaseRepositorySQL:
    """Adapter SQLite du port `PhaseRepository` — l'**avancement** d'une étape (ADR-0076).

    ⚠️ Chaque lecture **assemble** : la ligne `phase` ne porte que `depart_id`, `ordre` et `statut`,
    et la définition vient de l'étape de même rang, dans le tournoi du créneau. C'est la couture de
    la séparation, et elle vit ici pour que le domaine et les services l'ignorent (ADR-0003).
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def _etapes(
        self, session: Session, depart_ids: Sequence[int]
    ) -> dict[tuple[int, int], EtapeDeroule]:
        """Les définitions applicables aux créneaux donnés, indexées `(depart_id, ordre)`.

        Une seule requête pour tout un lot : lire l'étape phase par phase ferait N+1 requêtes sur un
        écran qui en affiche déjà plusieurs dizaines.
        """
        if not depart_ids:
            return {}
        lignes = session.execute(
            select(DepartORM.id, DerouleEtapeORM)
            .join(DerouleEtapeORM, DerouleEtapeORM.tournoi_id == DepartORM.tournoi_id)
            .where(DepartORM.id.in_(depart_ids))
        ).all()
        return {(depart_id, etape.ordre): _vers_etape(etape) for depart_id, etape in lignes}

    def _assembler(self, session: Session, lignes: Sequence[PhaseORM]) -> list[Phase]:
        """Assemble les phases d'un lot ; une instance **orpheline** de définition est ignorée.

        L'orphelin ne devrait pas exister — le service tient instances et étapes alignées. S'il en
        reste un (base altérée, étape retirée hors service), l'écarter vaut mieux que lever : une
        phase sans définition ne peut rien dire d'utile, et faire échouer *toute* la lecture pour
        elle priverait l'organisateur du reste de son déroulé le jour J.
        """
        etapes = self._etapes(session, [ligne.depart_id for ligne in lignes])
        assemblees = []
        for ligne in lignes:
            etape = etapes.get((ligne.depart_id, ligne.ordre))
            if etape is not None:
                assemblees.append(_vers_phase(ligne, etape))
        return assemblees

    def ajouter(self, phase: Phase) -> Phase:
        """Persiste l'**avancement** d'une phase ; sa définition n'est **pas** écrite ici.

        Le barème, le grain et les prélèvements portés par l'objet reçu sont ignorés : ils vivent
        sur l'étape (`DerouleRepository`). Seuls `depart_id`, `ordre` et `statut` sont écrits.
        """
        try:
            with self._session_factory() as session:
                ligne = PhaseORM(
                    depart_id=phase.depart_id,
                    ordre=phase.ordre,
                    statut=phase.statut.value,
                )
                session.add(ligne)
                # ⚠️ **`flush` et non `commit` avant le contrôle** (revue E01US025). Committer
                # d'abord laissait une ligne orpheline **en base** quand l'exception partait :
                # invisible à toute lecture, mais occupant le couple `(depart_id, ordre)` de
                # `uq_phase_depart_ordre` — l'instanciation légitime de ce rang butait ensuite sur
                # l'unicité, sans recours par l'écran. Le `flush` donne l'identifiant sans rien
                # acter ; sortir du `with` sans commit annule tout. L'adapter en mémoire fait déjà
                # ce choix : les deux ne doivent pas diverger.
                session.flush()
                assemblees = self._assembler(session, [ligne])
                if not assemblees:
                    raise InfrastructureError(
                        "Phase créée sans étape de déroulé de même rang : le tournoi de ce créneau "
                        "n'a pas ce rang à son déroulé."
                    )
                session.commit()
                return assemblees[0]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance de la phase.") from exc

    def par_id(self, phase_id: PhaseId) -> Phase | None:
        """Relit la phase d'identifiant donné, ou `None` si elle n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(PhaseORM, phase_id)
                if ligne is None:
                    return None
                assemblees = self._assembler(session, [ligne])
                return assemblees[0] if assemblees else None
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture de la phase.") from exc

    def par_depart_et_type(self, depart_id: DepartId, type_phase: TypePhase) -> Phase | None:
        """La phase d'un **départ** pour un type donné, ou `None`.

        Le type vient de la **définition** : le filtre s'applique donc après assemblage, non en SQL.
        En cas de multiplicité, la plus récente (`ordre` le plus élevé) l'emporte — même règle que
        l'adapter en mémoire, pour que les deux ne divergent pas.
        """
        candidates = [p for p in self.par_depart(depart_id) if p.type is type_phase]
        return candidates[-1] if candidates else None

    def par_depart(self, depart_id: DepartId) -> list[Phase]:
        """Toutes les phases d'un **départ**, **ordonnées par `ordre`** (E05US001)."""
        try:
            with self._session_factory() as session:
                lignes = list(
                    session.execute(
                        select(PhaseORM)
                        .where(PhaseORM.depart_id == depart_id)
                        .order_by(PhaseORM.ordre)
                    ).scalars()
                )
                return self._assembler(session, lignes)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des phases du départ.") from exc

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Phase]:
        """Les phases de **tous les départs** d'un tournoi, triées (départ, ordre).

        ⚠️ **Ce n'est pas une séquence** — c'est la concaténation de N suites 1..M, une par créneau.
        Réservée aux vues transverses ; le moteur passe toujours par `par_depart`.
        """
        try:
            with self._session_factory() as session:
                lignes = list(
                    session.execute(
                        select(PhaseORM)
                        .join(DepartORM, PhaseORM.depart_id == DepartORM.id)
                        .where(DepartORM.tournoi_id == tournoi_id)
                        .order_by(PhaseORM.depart_id, PhaseORM.ordre)
                    ).scalars()
                )
                return self._assembler(session, lignes)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des phases du tournoi.") from exc

    def enregistrer(self, phase: Phase) -> Phase:
        """Met à jour l'**avancement** d'une phase — son `statut`, et son rang.

        La définition n'est pas touchée : l'éditer passe par `DerouleRepository.enregistrer`. Un
        appelant qui modifierait `phase.bareme` avant d'appeler ici ne verrait **rien** changer, et
        c'est le contrat — le port le dit explicitement.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(PhaseORM, phase.id)
                if ligne is None:
                    raise InfrastructureError("Phase à mettre à jour introuvable en base.")
                ligne.ordre = phase.ordre
                ligne.statut = phase.statut.value
                # ⚠️ **`flush` puis contrôle puis `commit`** — même discipline que `ajouter`, et
                # pour la même raison (relevé en revue E01US025 : le correctif avait été appliqué à
                # `ajouter` seul, le trou était déplacé, pas fermé). En committant d'abord, un
                # avancement orphelin — sans étape de déroulé de même rang — était **acté en base**
                # puis signalé en `InfrastructureError` : l'appelant recevait un échec sur une
                # écriture qui, elle, avait bien eu lieu.
                session.flush()
                assemblees = self._assembler(session, [ligne])
                if not assemblees:
                    raise InfrastructureError(
                        "Phase mise à jour sans étape de déroulé de même rang."
                    )
                session.commit()
                return assemblees[0]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour de la phase.") from exc

    def reordonner(self, phases: list[Phase]) -> None:
        """Réaligne les rangs d'un lot de phases en **une** transaction, en deux passes.

        Même piège et même sortie que `DerouleEtapeRepositorySQL.reordonner` :
        `uq_phase_depart_ordre` interdit deux avancements de même rang, or un décalage y passe — les
        rangs sont **garés en négatif**, puis reposés. Ne touche que l'`ordre` : le `statut` n'a
        aucune raison de bouger parce que l'étape a changé de place.
        """
        try:
            with self._session_factory() as session:
                lignes = []
                for phase in phases:
                    ligne = session.get(PhaseORM, phase.id)
                    if ligne is None:
                        raise InfrastructureError("Phase à réordonner introuvable en base.")
                    lignes.append(ligne)
                for rang, ligne in enumerate(lignes, start=1):
                    ligne.ordre = -rang
                session.flush()
                for phase, ligne in zip(phases, lignes, strict=True):
                    ligne.ordre = phase.ordre
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec du réalignement des phases du créneau.") from exc

    def supprimer(self, phase_id: PhaseId) -> None:
        """Supprime l'avancement d'une phase (retrait d'une étape de la séquence, E05US001).

        **Contrat** : l'appelant (le service) garantit l'existence et l'absence de référence
        (`PhaseSourceReferencee` est arbitré en amont). La ligne absente est une incohérence
        technique → `InfrastructureError`.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(PhaseORM, phase_id)
                if ligne is None:
                    raise InfrastructureError("Phase à supprimer introuvable en base.")
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression de la phase.") from exc
