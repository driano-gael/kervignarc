"""Adapters repository SQLAlchemy — le **moteur de phases**

Séquence de phases, formats, plans de placement (qualification et duels).

Découpé de l'ancien `repositories.py` (3 378 lignes, 21 adapters) par l'action 2 de
[l'audit de maintenabilité](../../../../docs/audit-maintenabilite.md) : le fichier unique
figurait parmi les onze « passages obligés » du dépôt. Le contenu n'a pas bougé d'un
caractère ; seuls les imports inutiles ont été élagués.

Chaque opération ouvre une **session courte** (ADR-0005) et traduit les lignes ORM en agrégats
de domaine. Les pannes SQLAlchemy sont **enveloppées** en `InfrastructureError` — le domaine ne
voit jamais d'exception brute."""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Sequence
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from domain.bareme import BaremeQualification
from domain.depart import DepartId
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
from domain.tournoi import TournoiId
from infrastructure.db.models import (
    FormatTournoiORM,
    PhaseORM,
    PlacementORM,
    PlacementTableauORM,
)

# `AuditRepositorySQL` vit dans le thème `exploitation` mais s'annote ici : plusieurs
# adapters **co-écrivent** leur trace d'audit dans la même transaction (ADR-0035). Import
# direct et acyclique — `exploitation` n'importe aucun autre thème.
from infrastructure.db.repositories.exploitation import AuditRepositorySQL
from infrastructure.erreurs import InfrastructureError


def _vers_phase(ligne: PhaseORM) -> Phase:
    """Traduit une ligne ORM en agrégat `Phase` (config JSON → barème, grain, source, effectif).

    **Qualification** (E01US009/E01US015) : le barème est lu depuis `config.policies.scoring`
    (forme cible, ADR-0046), le grain depuis `config.validation`. Une `config` illisible **ou hors
    règle** (le repository en est le seul rédacteur et écrit toujours des valeurs valides) est une
    **incohérence technique** → on relit via les fabriques du domaine pour que même une valeur hors
    plage remonte en `InfrastructureError` (ADR-0007), jamais en value object silencieusement
    invalide. L'**absence** de `validation` n'est pas une incohérence — phase écrite avant E01US015
    → preset du type (mécanisme « politique sans migration », ADR-0011).

    **Compatibilité ascendante (ADR-0046).** E05US003 a fait basculer le `scoring` de la racine
    (`config.scoring`) vers `config.policies.scoring`. La migration Alembic `0028` réécrit les
    lignes existantes, mais `_lire_scoring` relit **aussi** l'ancienne forme à plat — au cas d'une
    base restaurée d'une sauvegarde antérieure — sans jamais dépendre du champ `nom`/`mode` (seuls
    `volees`/`fleches` alimentent le barème). Même patron « politique sans migration » que le grain.

    **Autres types** (E05US001/ADR-0045) : `bareme`/`validation` sont **absents** (`None`) — une
    phase d'élimination n'a pas de barème de qualification. La **source** de peuplement
    (`config.source`) et l'**effectif** (`config.effectif`) sont facultatifs, présents pour tout
    type. Leur absence est licite (première phase, effectif non déclaré) ; présents mais illisibles,
    ils restent une incohérence technique.
    """
    try:
        config = json.loads(ligne.config)
        type_phase = TypePhase(ligne.type)
        statut = StatutPhase(ligne.statut)
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
    except (
        json.JSONDecodeError,
        AttributeError,
        KeyError,
        TypeError,
        ValueError,
        DomainError,
    ) as exc:
        raise InfrastructureError("Configuration de phase illisible.") from exc
    try:
        return Phase(
            tournoi_id=ligne.tournoi_id,
            ordre=ligne.ordre,
            type=type_phase,
            bareme=bareme,
            validation=validation,
            sources=sources,
            effectif=effectif,
            barrage_jusqu_au=barrage_jusqu_au,
            statut=statut,
            id=ligne.id,
        )
    except DomainError as exc:
        # Les politiques sont individuellement valides mais incohérentes entre elles : le repository
        # n'écrit jamais ça (l'agrégat le refuse en amont) — donc la base a été altérée.
        raise InfrastructureError("Configuration de phase illisible.") from exc


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

    Passe par le constructeur de `SourcePhase` pour qu'une forme hors règle (plage vide, rang `< 1`,
    issue de tour sans tour) remonte en `DomainError`, enveloppée en `InfrastructureError` par
    l'appelant. `source` est typé `Any` (issu de `json.loads`) : une forme inattendue lève
    `AttributeError`/`TypeError`, gérée de même.

    **Tolérante à l'ancienne forme** (E05US001) : sans clé `nature`, c'est un prélèvement par rangs
    — la migration 0036 réécrit les lignes, mais une base restaurée d'avant elle reste lisible, au
    même titre que `_lire_scoring` tolère l'ancien `config.scoring` (ADR-0046).
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

    Passe par `GrainValidation.creer` pour qu'une valeur hors règle (cadence `< 1`, ou manquante
    sur un grain qui l'exige) remonte en `DomainError`, convertie en `InfrastructureError` par
    l'appelant — jamais en value object silencieusement invalide.

    `validation` est typé `Any` parce qu'il sort de `json.loads` : rien ne garantit que ce soit un
    objet. Une forme inattendue (scalaire, tableau) lève `AttributeError`/`TypeError`, que
    l'appelant enveloppe comme le reste.
    """
    n_volees = validation.get("n_volees")
    return GrainValidation.creer(
        TypeGrain(validation["grain"]),
        None if n_volees is None else int(n_volees),
    )


def _config_phase(phase: Phase) -> str:
    """Sérialise les politiques et le peuplement d'une phase en JSON (forme cible, ADR-0046).

    Forme : `{"policies"?: {...}, "validation"?: {...}, "source"?: {...}, "effectif"?: int}`. Les
    **politiques du moteur** (ADR-0004) vivent sous `config.policies`, chacune un objet
    `{"nom": <implémentation>, …paramètres}` — E05US003 a tranché DETTE-003 (`config.policies` +
    nom+paramètres). Ici seul `scoring` est écrit, et seulement pour une **qualification** :
    `{"nom": "cumul", "volees": N, "fleches": M}` (le `nom` désigne le classement au cumul, les
    paramètres portent le barème). Le grain de `validation` **n'est pas** une politique de moteur —
    il reste **hors** `policies`, à la racine (ADR-0046), et ne porte `n_volees` que pour le grain
    « toutes les N volées ». La **source** (peuplement) et l'**effectif** sont écrits s'ils sont
    déclarés, quel que soit le type. La relecture (`_vers_phase`) reste tolérante à l'ancienne forme
    à plat pour une base non migrée.
    """
    return json.dumps(
        _politiques_json(
            phase.bareme,
            phase.validation,
            phase.sources,
            phase.effectif,
            phase.barrage_jusqu_au,
        )
    )


def _politiques_json(
    bareme: BaremeQualification | None,
    validation: GrainValidation | None,
    sources: tuple[SourcePhase, ...],
    effectif: int | None,
    barrage_jusqu_au: int | None = None,
    *,
    marquer_absences: bool = False,
    porte_un_bareme: bool = False,
) -> dict[str, object]:
    """Corps commun d'une **étape** — une phase de tournoi ou un modèle d'étape d'un format.

    Extrait de `_config_phase` par E01US023 : `format_tournoi.config` stocke une **séquence** de ces
    objets (ADR-0060 §5), et recopier la forme aurait garanti qu'elles divergent au premier ajout de
    politique. Les deux tables se relisent donc avec les mêmes fonctions (`_lire_scoring`,
    `_vers_grain`, `_vers_source`).

    ⚠️ **`marquer_absences` distingue « pas encore écrit » de « délibérément vide » (E01US024).**
    Jusqu'ici l'absence d'une clé n'était **jamais** ambiguë : une qualification portait toujours
    barème et grain, l'invariant étant tenu à la construction. Depuis E01US024, un **modèle
    d'étape** peut légitimement n'en porter aucun — c'est le brouillon du CA. Mais l'absence de
    `validation` sur une qualification signifie déjà autre chose : « ligne écrite avant E01US015 »,
    qui retombe sur le preset du type (ADR-0011). Sans discriminant, un grain **choisi absent**
    serait silencieusement rempli à la relecture, et l'anomalie `phase_qualification_incomplete`
    deviendrait inatteignable pour ce cas.

    D'où : les **formats** écrivent la clé **présente à `null`** (choix du rédacteur), les
    **phases** gardent le régime historique (leur absence n'est pas ambiguë, leurs invariants n'ont
    pas bougé). Clé absente = ligne ancienne, dans les deux tables.
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
    if sources:
        config["sources"] = [_source_json(source) for source in sources]
    if effectif is not None:
        config["effectif"] = effectif
    return config


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

    Chaque étape reprend la forme d'une `config` de phase (`_politiques_json`), augmentée de son
    `ordre` et de son `type` — que `PhaseORM` porte en colonnes propres et qu'un format, lui, doit
    ranger dans le JSON puisqu'il en stocke plusieurs par ligne.

    `effectif_minimum_exige` (E05US021) s'ajoute **à côté** des étapes plutôt qu'en colonne : c'est
    une propriété du format entier, elle suit donc le même parti que la séquence — une donnée
    toujours lue et écrite en bloc, jamais requêtée. La clé est **omise** quand rien n'est exigé,
    pour qu'une config d'avant l'US et une config sans exigence soient le même document.
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

    Le barème n'est lu que pour une `qualification`, comme dans `_vers_phase` — les autres types
    n'en portent pas (ADR-0045 §2). Le grain absent d'une qualification retombe sur le preset du
    type, même mécanisme « politique sans migration » qu'ADR-0011 : un format écrit avant l'ajout
    d'une clé reste relisible.

    ⚠️ **Un modèle d'étape peut n'avoir ni barème ni grain depuis E01US024** — c'est le brouillon
    du CA, et c'est la relecture qui a failli l'interdire. Un premier jet lisait `_lire_scoring`
    **inconditionnellement** pour une qualification : le `KeyError` remontait en
    `InfrastructureError` → 500, **après** le `commit`. La ligne restait en base et `lister()`
    mappant *toutes* les lignes, un seul brouillon incomplet mettait la bibliothèque entière en
    500 — sans qu'aucune route ne permette de le supprimer, puisqu'elles relisent toutes. Défaut
    relevé par deux axes de la revue, reproduit de bout en bout. Cf. `_politiques_json` pour le
    discriminant « clé présente à `null` » vs « clé absente ».
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


class PlacementTableauRepositorySQL:
    """Adapter SQLite du port `PlacementTableauRepository` — plan de duels matérialisé (E03US009).

    Jumeau de `PlacementRepositorySQL`, scoppé par **phase** au lieu du départ, clé composite
    `(phase_id, inscription_id)`. Pas de couture d'audit ici : au moment de placer les duellistes
    (tour 1), aucun score de duel n'existe encore — la régénération n'est jamais « massive » au sens
    d'E12US007 (ADR-0048), donc pas de `definir_plan_avec_trace`.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def par_phase(self, phase_id: PhaseId) -> list[Affectation]:
        """Renvoie les affectations d'une phase, triées par cible puis position (ordre stable)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(PlacementTableauORM)
                    .where(PlacementTableauORM.phase_id == phase_id)
                    .order_by(PlacementTableauORM.cible_index, PlacementTableauORM.position)
                ).scalars()
                return [_vers_affectation_tableau(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du plan de duels.") from exc

    def definir_plan(self, phase_id: PhaseId, affectations: Sequence[Affectation]) -> None:
        """Purge le plan de duels de la phase puis insère les affectations — **une** transaction."""
        try:
            with self._session_factory() as session:
                session.execute(
                    delete(PlacementTableauORM).where(PlacementTableauORM.phase_id == phase_id)
                )
                session.add_all(
                    PlacementTableauORM(
                        phase_id=phase_id,
                        inscription_id=affectation.inscription_id,
                        cible_index=affectation.cible_index,
                        position=affectation.position,
                    )
                    for affectation in affectations
                )
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de définition du plan de duels.") from exc

    def poser_plusieurs(self, phase_id: PhaseId, affectations: Sequence[Affectation]) -> None:
        """Insère/met à jour chaque affectation (clé phase + inscription), **une** transaction."""
        try:
            with self._session_factory() as session:
                for affectation in affectations:
                    ligne = session.get(PlacementTableauORM, (phase_id, affectation.inscription_id))
                    if ligne is None:
                        session.add(
                            PlacementTableauORM(
                                phase_id=phase_id,
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

    def retirer(self, phase_id: PhaseId, inscription_id: InscriptionId) -> None:
        """Retire l'affectation d'un inscrit dans cette phase ; sans effet s'il n'en avait pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(PlacementTableauORM, (phase_id, inscription_id))
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


class PhaseRepositorySQL:
    """Adapter SQLite du port `PhaseRepository` (introduction minimale, E01US009/ADR-0011)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, phase: Phase) -> Phase:
        """Persiste la phase et la renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = PhaseORM(
                    tournoi_id=phase.tournoi_id,
                    ordre=phase.ordre,
                    type=phase.type.value,
                    config=_config_phase(phase),
                    statut=phase.statut.value,
                )
                session.add(ligne)
                session.commit()
                return _vers_phase(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance de la phase.") from exc

    def par_id(self, phase_id: PhaseId) -> Phase | None:
        """Relit la phase d'identifiant donné, ou `None` si elle n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(PhaseORM, phase_id)
                return None if ligne is None else _vers_phase(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture de la phase.") from exc

    def par_tournoi_et_type(self, tournoi_id: TournoiId, type_phase: TypePhase) -> Phase | None:
        """Renvoie la phase d'un tournoi pour un type donné, ou `None` s'il n'y en a pas.

        En cas de multiplicité (ne devrait pas survenir en E01US009), la plus récente (`id` le
        plus élevé) l'emporte.
        """
        try:
            with self._session_factory() as session:
                ligne = (
                    session.execute(
                        select(PhaseORM)
                        .where(
                            PhaseORM.tournoi_id == tournoi_id,
                            PhaseORM.type == type_phase.value,
                        )
                        .order_by(PhaseORM.id.desc())
                    )
                    .scalars()
                    .first()
                )
                return None if ligne is None else _vers_phase(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture de la phase du tournoi.") from exc

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Phase]:
        """Renvoie toutes les phases d'un tournoi, **ordonnées par `ordre`** (E05US001).

        Le tri à la source garantit l'invariant de séquence exploité par `ServicePhases` (les
        phases se lisent, se composent et se valident dans leur ordre).
        """
        try:
            with self._session_factory() as session:
                lignes = (
                    session.execute(
                        select(PhaseORM)
                        .where(PhaseORM.tournoi_id == tournoi_id)
                        .order_by(PhaseORM.ordre)
                    )
                    .scalars()
                    .all()
                )
                return [_vers_phase(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des phases du tournoi.") from exc

    def enregistrer(self, phase: Phase) -> Phase:
        """Met à jour une phase déjà persistée (barème, type, source, effectif, statut, ordre).

        **Contrat** : l'appelant (le service) garantit l'existence. La ligne absente est une
        **incohérence technique** (non un cas métier) → `InfrastructureError`.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(PhaseORM, phase.id)
                if ligne is None:
                    raise InfrastructureError("Phase à mettre à jour introuvable en base.")
                ligne.ordre = phase.ordre
                ligne.type = phase.type.value
                ligne.config = _config_phase(phase)
                ligne.statut = phase.statut.value
                session.commit()
                return _vers_phase(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour de la phase.") from exc

    def supprimer(self, phase_id: PhaseId) -> None:
        """Supprime une phase persistée (retrait d'une phase de la séquence, E05US001).

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
