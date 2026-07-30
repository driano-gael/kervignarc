"""Adapters repository SQLAlchemy (E00US009) — implémentent les ports du domaine.

`TournoiRepositorySQL` réalise `domain.ports.TournoiRepository` (conformité structurelle,
vérifiée au câblage). Chaque opération ouvre une **session courte** (une par opération,
ADR-0005) et traduit les lignes ORM en agrégats de domaine. Les pannes SQLAlchemy sont
**enveloppées** en `InfrastructureError` — le domaine ne voit jamais d'exception brute.
"""

from __future__ import annotations

import dataclasses
import datetime
import json
from collections.abc import Sequence
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from domain.archer import Archer, ArcherId
from domain.bareme import BaremeQualification
from domain.blason import Blason, BlasonId, ZoneScore, valider_zones
from domain.categorie import Categorie, CategorieId, SexeCategorie, TrancheAge
from domain.club import Club, ClubId, cle_nom
from domain.depart import Depart, DepartId
from domain.duel import BaremeDuel, Barrage, Cote, Duel, MancheDuel
from domain.entree_audit import ActionAuditee, EntreeAudit
from domain.erreurs import DomainError
from domain.forfait import Forfait, NatureForfait
from domain.format_tournoi import FormatTournoi, FormatTournoiId, ModelePhase
from domain.gabarit_salle import GabaritSalle, GabaritSalleId
from domain.grain_validation import GrainValidation, TypeGrain
from domain.inscription import Inscription, InscriptionId
from domain.participant import GenreParticipant, Participant
from domain.patrimoine import OrigineBrique
from domain.phase import Phase, PhaseId, SourcePhase, StatutPhase, TypePhase, grain_par_defaut
from domain.placement import Affectation
from domain.ports import Horloge
from domain.poste import Poste, PosteId
from domain.poste import normaliser_code as normaliser_code_poste
from domain.remboursement import (
    MotifRemboursement,
    Remboursement,
    RemboursementId,
    StatutRemboursement,
)
from domain.score import Score
from domain.scoreur import Scoreur, ScoreurId, normaliser_code
from domain.serie import Serie, SerieId, Volee
from domain.tournoi import StatutTournoi, Tournoi, TournoiId, TypeTournoi
from infrastructure.db.models import (
    ArcherORM,
    BlasonORM,
    CategorieORM,
    ClubORM,
    DepartORM,
    DuelORM,
    EntreeAuditORM,
    ForfaitORM,
    FormatTournoiORM,
    GabaritSalleORM,
    InscriptionORM,
    PhaseORM,
    PlacementORM,
    PlacementTableauORM,
    PosteORM,
    RemboursementORM,
    ScoreORM,
    ScoreurORM,
    SerieORM,
    TournoiORM,
    VoleeORM,
)
from infrastructure.erreurs import InfrastructureError


def _vers_tournoi(ligne: TournoiORM) -> Tournoi:
    """Traduit une ligne ORM en agrégat de domaine `Tournoi`."""
    return Tournoi(
        nom=ligne.nom,
        date=ligne.date,
        lieu=ligne.lieu,
        type_tournoi=TypeTournoi(ligne.type_tournoi),
        statut=StatutTournoi(ligne.statut),
        id=ligne.id,
    )


def _vers_archer(ligne: ArcherORM) -> Archer:
    """Traduit une ligne ORM en agrégat de domaine `Archer`."""
    return Archer(
        nom=ligne.nom,
        prenom=ligne.prenom,
        tournoi_id=ligne.tournoi_id,
        categorie_id=ligne.categorie_id,
        cible=ligne.cible,
        club_id=ligne.club_id,
        id=ligne.id,
    )


def _vers_club(ligne: ClubORM) -> Club:
    """Traduit une ligne ORM en agrégat de domaine `Club`."""
    return Club(nom=ligne.nom, id=ligne.id)


def _vers_depart(ligne: DepartORM) -> Depart:
    """Traduit une ligne ORM en agrégat de domaine `Depart` (E02US004)."""
    return Depart(
        tournoi_id=ligne.tournoi_id,
        numero=ligne.numero,
        tarif_centimes=ligne.tarif_centimes,
        horaire=ligne.horaire,
        quota=ligne.quota,
        id=ligne.id,
    )


def _vers_scoreur(ligne: ScoreurORM) -> Scoreur:
    """Traduit une ligne ORM en agrégat de domaine `Scoreur` (E10US003)."""
    return Scoreur(
        tournoi_id=ligne.tournoi_id,
        nom=ligne.nom,
        code=ligne.code,
        id=ligne.id,
    )


def _vers_poste(ligne: PosteORM) -> Poste:
    """Traduit une ligne ORM en agrégat de domaine `Poste` (E04US001)."""
    return Poste(
        tournoi_id=ligne.tournoi_id,
        cible_index=ligne.cible_index,
        code=ligne.code,
        id=ligne.id,
    )


def _vers_entree_audit(ligne: EntreeAuditORM) -> EntreeAudit:
    """Traduit une ligne ORM en agrégat de domaine `EntreeAudit` (E10US005).

    SQLite stocke un `DateTime` **sans fuseau** : la valeur relue est *naive*. On lui **réattache
    UTC**, car le service n'écrit jamais que de l'UTC (port `Horloge`) — l'entrée relue redevient
    ainsi *aware*, comme celle qui a été consignée (round-trip fidèle à l'instant).
    """
    horodatage = ligne.horodatage
    if horodatage.tzinfo is None:
        horodatage = horodatage.replace(tzinfo=datetime.UTC)
    return EntreeAudit(
        tournoi_id=ligne.tournoi_id,
        action=ActionAuditee(ligne.action),
        auteur=ligne.auteur,
        horodatage=horodatage,
        objet=ligne.objet,
        avant=ligne.avant,
        apres=ligne.apres,
        id=ligne.id,
    )


def _vers_volee(ligne: VoleeORM) -> Volee:
    """Traduit une ligne ORM en value object de domaine `Volee` (E04US002).

    `valeurs` est écrit par le repository comme un tableau JSON de codes de zone (« ["10","9"] »,
    même procédé que `BlasonORM.zones`). Un contenu illisible **ou** un code hors `ZoneScore` est
    une **incohérence technique** (le repository en est le seul rédacteur et n'écrit que des zones
    valides) → enveloppée en `InfrastructureError` (ADR-0007), jamais laissée fuir en value object
    silencieusement invalide. Le verrou n'est pas une colonne : `validee_par` non `NULL` **est** le
    verrou (cf. `domain.serie.Volee.verrouillee`).
    """
    try:
        valeurs = tuple(ZoneScore(v) for v in json.loads(ligne.valeurs))
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise InfrastructureError("Valeurs de volée illisibles.") from exc
    return Volee(
        numero=ligne.numero,
        valeurs=valeurs,
        saisie_par=ligne.saisie_par,
        validee_par=ligne.validee_par,
    )


def _vers_serie(ligne: SerieORM, volees: Sequence[VoleeORM]) -> Serie:
    """Traduit une ligne ORM `serie` et ses volées enfants en agrégat de domaine `Serie`.

    Les `volees` sont supposées **déjà triées par numéro** par l'appelant (le repository les relit
    `ORDER BY numero`) : l'agrégat conserve l'ordre du barème.
    """
    return Serie(
        tournoi_id=ligne.tournoi_id,
        archer_id=ligne.archer_id,
        volees=tuple(_vers_volee(v) for v in volees),
        id=ligne.id,
    )


def _valeurs_json(volee: Volee) -> str:
    """Sérialise les zones d'une volée en tableau JSON de codes (procédé de `BlasonORM.zones`)."""
    return json.dumps([zone.value for zone in volee.valeurs])


def _manches_json(duel: Duel) -> str:
    """Sérialise les manches d'un duel en JSON (E04US013) : `[{numero, haut:[…], bas:[…]}]`."""
    return json.dumps(
        [
            {
                "numero": manche.numero,
                "haut": [zone.value for zone in manche.volee_haut.valeurs],
                "bas": [zone.value for zone in manche.volee_bas.valeurs],
            }
            for manche in duel.manches
        ]
    )


def _barrage_json(duel: Duel) -> str | None:
    """Sérialise le barrage d'un duel en JSON (`None` si aucun) : `{haut, bas, gagnant}`."""
    if duel.barrage is None:
        return None
    designe = duel.barrage.gagnant_designe
    return json.dumps(
        {
            "haut": duel.barrage.fleche_haut.value,
            "bas": duel.barrage.fleche_bas.value,
            "gagnant": None if designe is None else designe.value,
        }
    )


def _vers_duel(ligne: DuelORM, *, bareme: BaremeDuel) -> Duel:
    """Réhydrate un `Duel` d'une ligne ORM, complété du seul **barème** (ADR-0049).

    Le tir (manches, barrage, validateur) **et l'identité des duellistes** viennent de la base ; le
    **barème** (dérivé de l'arme, re-résolu à la lecture) est **fourni** par l'appelant. Les
    duellistes stockés **ancrent** le tir : l'appelant compare l'identité réhydratée aux occupants
    recalculés pour détecter une divergence (ADR-0049 §4). Un contenu JSON illisible est une
    incohérence technique (`InfrastructureError`), le repository en étant le seul rédacteur.
    """
    participant_haut = Participant(genre=GenreParticipant(ligne.haut_genre), ref_id=ligne.haut_ref)
    participant_bas = Participant(genre=GenreParticipant(ligne.bas_genre), ref_id=ligne.bas_ref)
    try:
        manches = tuple(
            MancheDuel(
                numero=int(brute["numero"]),
                volee_haut=Volee(
                    numero=int(brute["numero"]),
                    valeurs=tuple(ZoneScore(v) for v in brute["haut"]),
                ),
                volee_bas=Volee(
                    numero=int(brute["numero"]),
                    valeurs=tuple(ZoneScore(v) for v in brute["bas"]),
                ),
            )
            for brute in json.loads(ligne.manches)
        )
        barrage = None
        if ligne.barrage is not None:
            brut = json.loads(ligne.barrage)
            gagnant = brut["gagnant"]
            barrage = Barrage(
                fleche_haut=ZoneScore(brut["haut"]),
                fleche_bas=ZoneScore(brut["bas"]),
                gagnant_designe=None if gagnant is None else Cote(gagnant),
            )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise InfrastructureError("Tir de duel illisible.") from exc
    return Duel(
        bareme=bareme,
        participant_haut=participant_haut,
        participant_bas=participant_bas,
        manches=manches,
        barrage=barrage,
        validee_par=ligne.validee_par,
    )


def _vers_inscription(ligne: InscriptionORM) -> Inscription:
    """Traduit une ligne ORM en agrégat de domaine `Inscription` (E02US009)."""
    return Inscription(
        archer_id=ligne.archer_id,
        depart_id=ligne.depart_id,
        paye=ligne.paye,
        id=ligne.id,
    )


def _vers_blason(ligne: BlasonORM) -> Blason:
    """Traduit une ligne ORM en agrégat de domaine `Blason`.

    `zones` est écrit par le repository comme un tableau JSON de valeurs de score (E01US014). Un
    contenu illisible, **ou lisible mais hors règle**, est une **incohérence technique** (le
    repository en est le seul rédacteur, il écrit toujours un jeu valide) → enveloppée en
    `InfrastructureError` (ADR-0007), jamais laissée fuir en agrégat silencieusement invalide.

    On **rejoue `valider_zones`** plutôt que de se contenter d'une coercition `ZoneScore(...)`,
    pour la même raison que `_vers_phase` repasse par `BaremeQualification.creer` : la coercition
    seule ne voit que le vocabulaire, pas la structure. Un `'{"10": 1}'` en base réhydraterait
    `('10',)` — clés d'un objet JSON, vocabulaire valide, mais **sans `M`** — c'est-à-dire un
    blason hors invariant, qui piloterait le pavé d'EPIC-04 sans qu'aucune erreur ne soit levée.
    """
    try:
        zones = valider_zones(json.loads(ligne.zones))
    except (json.JSONDecodeError, TypeError, ValueError, DomainError) as exc:
        raise InfrastructureError("Zones de blason illisibles.") from exc
    return Blason(
        tournoi_id=ligne.tournoi_id,
        origine=OrigineBrique(ligne.origine),
        nom=ligne.nom,
        taille=ligne.taille,
        capacite=ligne.capacite,
        zones=zones,
        id=ligne.id,
    )


def _vers_gabarit(ligne: GabaritSalleORM) -> GabaritSalle:
    """Traduit une ligne ORM en agrégat de domaine `GabaritSalle` (config JSON → tuple).

    Une `config` illisible ou d'un format inattendu est une **incohérence technique** (le
    repository est le seul rédacteur et écrit toujours un JSON valide) : elle est enveloppée en
    `InfrastructureError` — jamais laissée fuir en traceback brut à la frontière (ADR-0007).
    """
    try:
        capacites = tuple(int(c) for c in json.loads(ligne.config)["capacites"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise InfrastructureError("Configuration de gabarit de salle illisible.") from exc
    return GabaritSalle(
        nom=ligne.nom, capacites=capacites, id=ligne.id, tournoi_id=ligne.tournoi_id
    )


def _config_gabarit(gabarit: GabaritSalle) -> str:
    """Sérialise le plafond par cible d'un gabarit en JSON (`{"capacites": [...]}`)."""
    return json.dumps({"capacites": list(gabarit.capacites)})


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
            validation = (
                grain_par_defaut(type_phase)
                if "validation" not in config
                else _vers_grain(config["validation"])
            )
        source = None if "source" not in config else _vers_source(config["source"])
        effectif = config.get("effectif")
        effectif = None if effectif is None else int(effectif)
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
            source=source,
            effectif=effectif,
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


def _vers_source(source: Any) -> SourcePhase:
    """Relit la source de peuplement depuis sa forme JSON (`config.source`).

    Passe par le constructeur de `SourcePhase` pour qu'une plage hors règle (vide, rang `< 1`)
    remonte en `DomainError`, enveloppée en `InfrastructureError` par l'appelant. `source` est typé
    `Any` (issu de `json.loads`) : une forme inattendue lève `AttributeError`/`TypeError`, gérée de
    même.
    """
    return SourcePhase(
        ordre_source=int(source["ordre_source"]),
        rang_debut=int(source["rang_debut"]),
        rang_fin=int(source["rang_fin"]),
    )


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
        _politiques_json(phase.bareme, phase.validation, phase.source, phase.effectif)
    )


def _politiques_json(
    bareme: BaremeQualification | None,
    validation: GrainValidation | None,
    source: SourcePhase | None,
    effectif: int | None,
) -> dict[str, object]:
    """Corps commun d'une **étape** — une phase de tournoi ou un modèle d'étape d'un format.

    Extrait de `_config_phase` par E01US023 : `format_tournoi.config` stocke une **séquence** de ces
    objets (ADR-0060 §5), et recopier la forme aurait garanti qu'elles divergent au premier ajout de
    politique. Les deux tables se relisent donc avec les mêmes fonctions (`_lire_scoring`,
    `_vers_grain`, `_vers_source`).
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
    if validation is not None:
        grain: dict[str, object] = {"grain": validation.type.value}
        if validation.n_volees is not None:
            grain["n_volees"] = validation.n_volees
        config["validation"] = grain
    if source is not None:
        config["source"] = {
            "ordre_source": source.ordre_source,
            "rang_debut": source.rang_debut,
            "rang_fin": source.rang_fin,
        }
    if effectif is not None:
        config["effectif"] = effectif
    return config


def _config_format(format_tournoi: FormatTournoi) -> str:
    """Sérialise la séquence de modèles de phases d'un format (`{"etapes": [...]}`).

    Chaque étape reprend la forme d'une `config` de phase (`_politiques_json`), augmentée de son
    `ordre` et de son `type` — que `PhaseORM` porte en colonnes propres et qu'un format, lui, doit
    ranger dans le JSON puisqu'il en stocke plusieurs par ligne.
    """
    return json.dumps(
        {
            "etapes": [
                {
                    "ordre": etape.ordre,
                    "type": etape.type.value,
                    **_politiques_json(
                        etape.bareme, etape.validation, etape.source, etape.effectif
                    ),
                }
                for etape in format_tournoi.etapes
            ]
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
        etapes = [_vers_modele_phase(brute) for brute in json.loads(ligne.config)["etapes"]]
        return dataclasses.replace(
            FormatTournoi.creer(ligne.nom, etapes, OrigineBrique(ligne.origine)), id=ligne.id
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
    """
    type_phase = TypePhase(brute["type"])
    bareme = None
    if type_phase is TypePhase.QUALIFICATION:
        scoring = _lire_scoring(brute)
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
    if "validation" in brute:
        validation = _vers_grain(brute["validation"])
    elif type_phase is TypePhase.QUALIFICATION:
        validation = grain_par_defaut(type_phase)
    effectif = brute.get("effectif")
    return ModelePhase(
        ordre=int(brute["ordre"]),
        type=type_phase,
        bareme=bareme,
        validation=validation,
        source=None if "source" not in brute else _vers_source(brute["source"]),
        effectif=None if effectif is None else int(effectif),
    )


def _vers_categorie(ligne: CategorieORM) -> Categorie:
    """Traduit une ligne ORM en agrégat de domaine `Categorie` (ages JSON → tuple de `TrancheAge`).

    `ages` est écrit par le repository comme un tableau JSON de codes de tranche (E01US013). Un
    contenu illisible ou une valeur hors des huit tranches FFTA est une **incohérence technique**
    (le repository en est le seul rédacteur, il écrit toujours des codes valides) → enveloppée en
    `InfrastructureError` (ADR-0007), jamais laissée fuir en value object silencieusement invalide.
    """
    try:
        ages = tuple(TrancheAge(code) for code in json.loads(ligne.ages))
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise InfrastructureError("Tranches d'âge de catégorie illisibles.") from exc
    return Categorie(
        tournoi_id=ligne.tournoi_id,
        origine=OrigineBrique(ligne.origine),
        libelle=ligne.libelle,
        arme=ligne.arme,
        ages=ages,
        sexe=None if ligne.sexe is None else SexeCategorie(ligne.sexe),
        blason_id=ligne.blason_id,
        hauteur_cm=ligne.hauteur_cm,
        id=ligne.id,
    )


def _ages_categorie(categorie: Categorie) -> str:
    """Sérialise les tranches d'âge en tableau JSON de codes (ex. `["U15","U18"]`)."""
    return json.dumps([tranche.value for tranche in categorie.ages])


class TournoiRepositorySQL:
    """Adapter SQLite du port `TournoiRepository`."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, tournoi: Tournoi) -> Tournoi:
        """Persiste le tournoi et le renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = TournoiORM(
                    nom=tournoi.nom,
                    date=tournoi.date,
                    lieu=tournoi.lieu,
                    type_tournoi=tournoi.type_tournoi.value,
                    statut=tournoi.statut.value,
                )
                session.add(ligne)
                session.commit()
                return _vers_tournoi(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance du tournoi.") from exc

    def par_id(self, tournoi_id: TournoiId) -> Tournoi | None:
        """Relit le tournoi d'identifiant donné, ou `None` s'il n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(TournoiORM, tournoi_id)
                return None if ligne is None else _vers_tournoi(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du tournoi.") from exc

    def lister(self) -> list[Tournoi]:
        """Renvoie tous les tournois, du plus récent au plus ancien (par identifiant)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(TournoiORM).order_by(TournoiORM.id.desc())
                ).scalars()
                return [_vers_tournoi(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des tournois.") from exc

    def enregistrer(self, tournoi: Tournoi) -> Tournoi:
        """Met à jour un tournoi déjà persisté (édition, transition de statut) et le renvoie.

        **Contrat** : l'appelant (le service) garantit l'existence du tournoi (vérifiée en
        amont). La ligne absente est donc une **incohérence technique**, non un cas métier
        — d'où `InfrastructureError` (et non une erreur applicative « 404 »).
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(TournoiORM, tournoi.id)
                if ligne is None:
                    raise InfrastructureError("Tournoi à mettre à jour introuvable en base.")
                ligne.nom = tournoi.nom
                ligne.date = tournoi.date
                ligne.lieu = tournoi.lieu
                ligne.type_tournoi = tournoi.type_tournoi.value
                ligne.statut = tournoi.statut.value
                session.commit()
                return _vers_tournoi(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour du tournoi.") from exc

    def supprimer(self, tournoi_id: TournoiId) -> None:
        """Supprime le tournoi d'identifiant donné (existence garantie par l'appelant)."""
        try:
            with self._session_factory() as session:
                ligne = session.get(TournoiORM, tournoi_id)
                if ligne is None:
                    raise InfrastructureError("Tournoi à supprimer introuvable en base.")
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression du tournoi.") from exc


class ArcherRepositorySQL:
    """Adapter SQLite du port `ArcherRepository` (E00US011, E02US003)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, archer: Archer) -> Archer:
        """Persiste l'archer et le renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = ArcherORM(
                    tournoi_id=archer.tournoi_id,
                    nom=archer.nom,
                    prenom=archer.prenom,
                    categorie_id=archer.categorie_id,
                    cible=archer.cible,
                    club_id=archer.club_id,
                )
                session.add(ligne)
                session.commit()
                return _vers_archer(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance de l'archer.") from exc

    def par_id(self, archer_id: ArcherId) -> Archer | None:
        """Relit l'archer d'identifiant donné, ou `None` s'il n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(ArcherORM, archer_id)
                return None if ligne is None else _vers_archer(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture de l'archer.") from exc

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Archer]:
        """Renvoie tous les archers d'un tournoi (liste éventuellement vide)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(ArcherORM).where(ArcherORM.tournoi_id == tournoi_id)
                ).scalars()
                return [_vers_archer(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des archers du tournoi.") from exc

    def par_club(self, club_id: ClubId) -> list[Archer]:
        """Renvoie les archers rattachés à un club, **tous tournois confondus** (E02US001)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(ArcherORM).where(ArcherORM.club_id == club_id).order_by(ArcherORM.id)
                ).scalars()
                return [_vers_archer(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des archers du club.") from exc

    def enregistrer(self, archer: Archer) -> Archer:
        """Met à jour un archer déjà persisté (placement E00US011, édition E02US003).

        **Contrat** : l'appelant (le service applicatif) garantit l'existence de l'archer
        (vérifiée en amont). La ligne absente est donc une **incohérence technique**, non
        un cas métier — d'où `InfrastructureError` (et non une erreur applicative « 404 »).
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(ArcherORM, archer.id)
                if ligne is None:
                    raise InfrastructureError("Archer à mettre à jour introuvable en base.")
                # Tous les champs mutables sont recopiés, et ils ont désormais **deux** appelants
                # aux besoins disjoints : `nom`/`prenom`/`categorie_id`/`club_id` sont ceux de
                # l'édition (E02US003), `cible` celui du placement (E00US011). Un `enregistrer`
                # partiel perdrait donc l'un ou l'autre en silence — le genre d'oubli qui ne se
                # voit qu'en base, longtemps après.
                ligne.nom = archer.nom
                ligne.prenom = archer.prenom
                ligne.categorie_id = archer.categorie_id
                ligne.cible = archer.cible
                ligne.club_id = archer.club_id
                session.commit()
                return _vers_archer(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour de l'archer.") from exc

    def supprimer(self, archer_id: ArcherId) -> None:
        """Supprime l'archer, **ses scores, ses inscriptions, sa série de saisie et ses forfaits**
        (E02US003, E02US009, E04US002, E04US015).

        **Contrat** (même que `enregistrer`) : l'existence est garantie par le service ; une ligne
        absente est une incohérence technique, pas un 404. Le service a par ailleurs déjà obtenu
        la confirmation de l'admin si l'archer était placé, engagé ou inscrit (`ArcherEngage`) :
        ici, la destruction est voulue.

        **Une seule transaction** pour tous les `DELETE`, dans cet ordre : `score.archer_id`,
        `inscription.archer_id`, `serie.archer_id` **et** `forfait.archer_id` sont des FK **sans
        `ON DELETE`** (DETTE-001), donc supprimer l'archer d'abord échouerait. `serie` (E04US002) et
        `forfait` (E04US015) sont des enfants de plus : les retirer ici étend la **cascade
        applicative maîtrisée** (qui manque au reste de la descendance de `tournoi` — DETTE-001). Le
        `forfait` **doit** être purgé ici, pas seulement « assumé en dette » : sa FK est *enforced*
        (`PRAGMA foreign_keys=ON`), une ligne orpheline ferait échouer la suppression (500, archer
        indéracinable — trouvé en revue adversariale). Les **volées** de la série suivent
        automatiquement (`volee.serie_id` est `ON DELETE CASCADE` — composant strict de l'agrégat) :
        le `DELETE` de la série déclenche la cascade SQLite. Deux transactions successives
        laisseraient, si la seconde échouait, un archer à demi dépouillé — un état que personne n'a
        demandé.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(ArcherORM, archer_id)
                if ligne is None:
                    raise InfrastructureError("Archer à supprimer introuvable en base.")
                session.execute(delete(ScoreORM).where(ScoreORM.archer_id == archer_id))
                session.execute(delete(InscriptionORM).where(InscriptionORM.archer_id == archer_id))
                # `serie` (E04US002) : `DELETE` SQL, donc la cascade `volee` (ON DELETE CASCADE)
                # s'applique au niveau base — contrairement à un `session.delete` ORM.
                session.execute(delete(SerieORM).where(SerieORM.archer_id == archer_id))
                # `forfait` (E04US015) : même cascade applicative que `serie` — FK enforced, sinon
                # une ligne orpheline bloque la suppression (revue adversariale E04US015).
                session.execute(delete(ForfaitORM).where(ForfaitORM.archer_id == archer_id))
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression de l'archer.") from exc

    def fusionner(self, gagnant_id: ArcherId, perdant_id: ArcherId) -> None:
        """Réassigne la descendance du perdant au gagnant, puis supprime le perdant (E02US005).

        **Miroir de `supprimer`** : mêmes FK sans `ON DELETE` (DETTE-001), même transaction unique,
        mais on **réattribue** au lieu de purger. Tout en instructions **Core** (`update`/`delete`),
        comme `supprimer` : une collision d'inscription est effacée par un `DELETE` SQL, qui
        déclenche la cascade base `placement.inscription_id` (`ON DELETE CASCADE`) — un
        `session.delete` ORM
        laisserait SQLAlchemy deviner la descendance (cf. `supprimer`, la série et ses volées).

        Contrat (garanti par le service) : deux archers distincts, même tournoi, **pas tous les
        deux** une série (sinon `UNIQUE(tournoi_id, archer_id)` sauterait). Les collisions d'unicité
        d'**inscription** (par départ) **et de forfait** (par phase, E04US015) sont résolues **ici**
        (le service ne les voit pas) : voir `ArcherRepository.fusionner`.
        """
        try:
            with self._session_factory() as session:
                if session.get(ArcherORM, gagnant_id) is None or (
                    session.get(ArcherORM, perdant_id) is None
                ):
                    raise InfrastructureError("Archer(s) à fusionner introuvable(s) en base.")
                # Inscriptions : réassigner celles du perdant, sauf collision sur un départ où le
                # gagnant est déjà inscrit (UNIQUE(archer_id, depart_id)) — on garde alors celle du
                # gagnant, en y **reportant le paiement** (paye vrai si l'une des deux l'était),
                # et on supprime celle du perdant (son placement éventuel cascade).
                gagnant_par_depart = {
                    depart_id: (inscription_id, paye)
                    for inscription_id, depart_id, paye in session.execute(
                        select(
                            InscriptionORM.id, InscriptionORM.depart_id, InscriptionORM.paye
                        ).where(InscriptionORM.archer_id == gagnant_id)
                    ).all()
                }
                for inscription_id, depart_id, paye in session.execute(
                    select(InscriptionORM.id, InscriptionORM.depart_id, InscriptionORM.paye).where(
                        InscriptionORM.archer_id == perdant_id
                    )
                ).all():
                    collision = gagnant_par_depart.get(depart_id)
                    if collision is None:
                        session.execute(
                            update(InscriptionORM)
                            .where(InscriptionORM.id == inscription_id)
                            .values(archer_id=gagnant_id)
                        )
                        continue
                    gagnant_inscription_id, gagnant_paye = collision
                    if paye and not gagnant_paye:
                        session.execute(
                            update(InscriptionORM)
                            .where(InscriptionORM.id == gagnant_inscription_id)
                            .values(paye=True)
                        )
                    session.execute(
                        delete(InscriptionORM).where(InscriptionORM.id == inscription_id)
                    )
                # Scores (agrégat legacy, DETTE-011) : aucune unicité, réassignation nue.
                session.execute(
                    update(ScoreORM)
                    .where(ScoreORM.archer_id == perdant_id)
                    .values(archer_id=gagnant_id)
                )
                # Série : au plus une côté perdant (contrat « pas les deux »), donc pas de collision
                # sur UNIQUE(tournoi_id, archer_id) — ses volées la suivent (via serie_id).
                session.execute(
                    update(SerieORM)
                    .where(SerieORM.archer_id == perdant_id)
                    .values(archer_id=gagnant_id)
                )
                # Forfaits (E04US015) : réassigner ceux du perdant, sauf collision sur une phase où
                # le gagnant est déjà forfait (UNIQUE(tournoi_id, archer_id, phase_id)) — on garde
                # alors celui du gagnant et on supprime celui du perdant. Sans ce nettoyage, la FK
                # `forfait.archer_id` (enforced) ferait échouer le `DELETE` du perdant (revue
                # adversariale E04US015). Même tournoi (contrat), la clé de collision est la phase.
                gagnant_phases = {
                    phase_id
                    for (phase_id,) in session.execute(
                        select(ForfaitORM.phase_id).where(ForfaitORM.archer_id == gagnant_id)
                    ).all()
                }
                for forfait_id, phase_id in session.execute(
                    select(ForfaitORM.id, ForfaitORM.phase_id).where(
                        ForfaitORM.archer_id == perdant_id
                    )
                ).all():
                    if phase_id in gagnant_phases:
                        session.execute(delete(ForfaitORM).where(ForfaitORM.id == forfait_id))
                    else:
                        session.execute(
                            update(ForfaitORM)
                            .where(ForfaitORM.id == forfait_id)
                            .values(archer_id=gagnant_id)
                        )
                session.execute(delete(ArcherORM).where(ArcherORM.id == perdant_id))
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de la fusion des archers.") from exc


class ClubRepositorySQL:
    """Adapter SQLite du port `ClubRepository` (E02US001)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, club: Club) -> Club:
        """Persiste le club et le renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = ClubORM(nom=club.nom)
                session.add(ligne)
                session.commit()
                return _vers_club(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance du club.") from exc

    def par_id(self, club_id: ClubId) -> Club | None:
        """Relit le club d'identifiant donné, ou `None` s'il n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(ClubORM, club_id)
                return None if ligne is None else _vers_club(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du club.") from exc

    def par_nom(self, nom: str) -> Club | None:
        """Relit le club de même nom au sens de `domain.club.cle_nom`, ou `None` s'il n'y en a pas.

        La comparaison est faite **côté Python**, via la clé du domaine, plutôt qu'en SQL : le
        `COLLATE NOCASE` de SQLite ne replie que la casse **ASCII** — il laisserait passer « Élan »
        / « élan » comme « Élan » / « Elan », alors que les noms de clubs sont accentués. L'adapter
        n'invente donc aucune règle de comparaison : il applique celle du domaine.

        Le référentiel compte quelques dizaines de lignes et cette lecture n'a lieu qu'à la
        création/au renommage (donc dans la file d'écriture, jamais sur un chemin chaud) : les
        parcourir est sans conséquence, et l'unique lecture reste courte.
        """
        try:
            with self._session_factory() as session:
                recherche = cle_nom(nom)
                lignes = session.execute(select(ClubORM)).scalars()
                for ligne in lignes:
                    if cle_nom(ligne.nom) == recherche:
                        return _vers_club(ligne)
                return None
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du club par nom.") from exc

    def lister(self) -> list[Club]:
        """Renvoie tout le référentiel des clubs (liste éventuellement vide)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(select(ClubORM).order_by(ClubORM.id)).scalars()
                return [_vers_club(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du référentiel des clubs.") from exc

    def enregistrer(self, club: Club) -> Club:
        """Met à jour un club déjà persisté (renommage) et le renvoie.

        **Contrat** : l'appelant (le service) garantit l'existence (vérifiée en amont). La ligne
        absente est une **incohérence technique** (non un cas métier) → `InfrastructureError`.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(ClubORM, club.id)
                if ligne is None:
                    raise InfrastructureError("Club à mettre à jour introuvable en base.")
                ligne.nom = club.nom
                session.commit()
                return _vers_club(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour du club.") from exc

    def supprimer(self, club_id: ClubId) -> None:
        """Supprime le club d'identifiant donné (existence garantie par l'appelant)."""
        try:
            with self._session_factory() as session:
                ligne = session.get(ClubORM, club_id)
                if ligne is None:
                    raise InfrastructureError("Club à supprimer introuvable en base.")
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression du club.") from exc


class DepartRepositorySQL:
    """Adapter SQLite du port `DepartRepository` (E02US004)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, depart: Depart) -> Depart:
        """Persiste le départ et le renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = DepartORM(
                    tournoi_id=depart.tournoi_id,
                    numero=depart.numero,
                    horaire=depart.horaire,
                    tarif_centimes=depart.tarif_centimes,
                    quota=depart.quota,
                )
                session.add(ligne)
                session.commit()
                return _vers_depart(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance du départ.") from exc

    def par_id(self, depart_id: DepartId) -> Depart | None:
        """Relit le départ d'identifiant donné, ou `None` s'il n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(DepartORM, depart_id)
                return None if ligne is None else _vers_depart(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du départ.") from exc

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Depart]:
        """Renvoie tous les départs d'un tournoi, **triés par numéro** (liste éventuellement vide).

        Le tri par numéro rend l'ordre d'affichage stable et sert au service à calculer le prochain
        numéro (le plus grand + 1).
        """
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(DepartORM)
                    .where(DepartORM.tournoi_id == tournoi_id)
                    .order_by(DepartORM.numero)
                ).scalars()
                return [_vers_depart(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des départs du tournoi.") from exc

    def enregistrer(self, depart: Depart) -> Depart:
        """Met à jour un départ déjà persisté (édition tarif/horaire) et le renvoie.

        **Contrat** : l'appelant (le service) garantit l'existence (vérifiée en amont). La ligne
        absente est une **incohérence technique** (non un cas métier) → `InfrastructureError`. Le
        `numero` et le `tournoi_id` d'un départ persisté ne changent pas (édition sur place).
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(DepartORM, depart.id)
                if ligne is None:
                    raise InfrastructureError("Départ à mettre à jour introuvable en base.")
                ligne.horaire = depart.horaire
                ligne.tarif_centimes = depart.tarif_centimes
                ligne.quota = depart.quota
                session.commit()
                return _vers_depart(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour du départ.") from exc

    def supprimer(self, depart_id: DepartId) -> None:
        """Supprime le départ d'identifiant donné **et ses inscriptions** (E02US004, E02US009).

        **Contrat** : existence garantie par l'appelant, qui a déjà obtenu la confirmation de
        l'admin si le départ portait des inscriptions (`DepartAvecInscriptions`). **Une seule
        transaction** pour les deux `DELETE`, dans cet ordre : `inscription.depart_id` est une FK
        **sans `ON DELETE`** (DETTE-001), donc supprimer le départ d'abord échouerait. Même patron
        que `ArcherRepositorySQL.supprimer` avec les scores — cascade applicative maîtrisée.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(DepartORM, depart_id)
                if ligne is None:
                    raise InfrastructureError("Départ à supprimer introuvable en base.")
                session.execute(delete(InscriptionORM).where(InscriptionORM.depart_id == depart_id))
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression du départ.") from exc

    def supprimer_avec_remboursements(
        self, depart_id: DepartId, remboursements: Sequence[Remboursement]
    ) -> None:
        """Supprime le départ (et ses inscriptions) **et** ouvre les remboursements — une
        transaction.

        Variante de `supprimer` (E08US005, ADR-0057) : les `remboursements` (un par inscription
        payée
        d'un créneau tarifé) sont **insérés** dans la **même** session que les deux `DELETE`,
        scellés
        par un **unique** `commit`. Ordre des `DELETE` inchangé (`inscription` avant `depart` — FK
        sans `ON DELETE`, DETTE-001). Atomicité « on n'efface une inscription payée que si son
        remboursement est ouvert » — jamais de somme encaissée effacée sans contrepartie, jamais de
        remboursement en double (un échec avant le `commit` annule **tout**). Une liste vide est
        tolérée (équivalente à `supprimer`) — mais le service appelle `supprimer` dans ce cas.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(DepartORM, depart_id)
                if ligne is None:
                    raise InfrastructureError("Départ à supprimer introuvable en base.")
                for remboursement in remboursements:
                    session.add(_remboursement_orm(remboursement))
                session.execute(delete(InscriptionORM).where(InscriptionORM.depart_id == depart_id))
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError(
                "Échec de suppression du départ avec remboursements."
            ) from exc


class ScoreurRepositorySQL:
    """Adapter SQLite du port `ScoreurRepository` (E10US003)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, scoreur: Scoreur) -> Scoreur:
        """Persiste le scoreur et le renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = ScoreurORM(
                    tournoi_id=scoreur.tournoi_id, nom=scoreur.nom, code=scoreur.code
                )
                session.add(ligne)
                session.commit()
                return _vers_scoreur(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance du scoreur.") from exc

    def par_id(self, scoreur_id: ScoreurId) -> Scoreur | None:
        """Relit le scoreur d'identifiant donné, ou `None` s'il n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(ScoreurORM, scoreur_id)
                return None if ligne is None else _vers_scoreur(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du scoreur.") from exc

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Scoreur]:
        """Renvoie tous les scoreurs d'un tournoi (liste éventuellement vide).

        L'ordre d'affichage (par nom) est appliqué par le service ; l'adapter renvoie par `id`.
        """
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(ScoreurORM)
                    .where(ScoreurORM.tournoi_id == tournoi_id)
                    .order_by(ScoreurORM.id)
                ).scalars()
                return [_vers_scoreur(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des scoreurs du tournoi.") from exc

    def par_code(self, code: str) -> Scoreur | None:
        """Relit le scoreur portant ce `code`, **tous tournois confondus**, ou `None`.

        Comparaison **exacte** sur la forme canonique (`domain.scoreur.normaliser_code`) : le code
        est stocké déjà normalisé (majuscules), la requête normalise la saisie — un simple `WHERE`
        indexé par la contrainte `UNIQUE` suffit (nul besoin du balayage Python de
        `ClubRepositorySQL`, qui, lui, replie des accents que SQL ne sait pas comparer).
        """
        try:
            with self._session_factory() as session:
                ligne = session.execute(
                    select(ScoreurORM).where(ScoreurORM.code == normaliser_code(code))
                ).scalar_one_or_none()
                return None if ligne is None else _vers_scoreur(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du scoreur par code.") from exc

    def enregistrer(self, scoreur: Scoreur) -> Scoreur:
        """Met à jour un scoreur déjà persisté (renommage) et le renvoie.

        **Contrat** : existence garantie par l'appelant (le service). La ligne absente est une
        **incohérence technique** → `InfrastructureError`. Le `code` et le `tournoi_id` d'un scoreur
        persisté ne changent pas (édition sur place, comme `DepartRepositorySQL`).
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(ScoreurORM, scoreur.id)
                if ligne is None:
                    raise InfrastructureError("Scoreur à mettre à jour introuvable en base.")
                ligne.nom = scoreur.nom
                session.commit()
                return _vers_scoreur(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour du scoreur.") from exc

    def supprimer(self, scoreur_id: ScoreurId) -> None:
        """Supprime le scoreur d'identifiant donné (existence garantie par l'appelant).

        **Feuille** : aucun enfant en base (les validations tracées d'E10US005 porteront le **nom**,
        pas une FK), donc pas de cascade — au contraire de `DepartRepositorySQL.supprimer`.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(ScoreurORM, scoreur_id)
                if ligne is None:
                    raise InfrastructureError("Scoreur à supprimer introuvable en base.")
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression du scoreur.") from exc


class PosteRepositorySQL:
    """Adapter SQLite du port `PosteRepository` — credential d'une cible (E04US001)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, poste: Poste) -> Poste:
        """Persiste le poste et le renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = PosteORM(
                    tournoi_id=poste.tournoi_id,
                    cible_index=poste.cible_index,
                    code=poste.code,
                )
                session.add(ligne)
                session.commit()
                return _vers_poste(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance du poste.") from exc

    def par_id(self, poste_id: PosteId) -> Poste | None:
        """Relit le poste d'identifiant donné, ou `None` s'il n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(PosteORM, poste_id)
                return None if ligne is None else _vers_poste(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du poste.") from exc

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Poste]:
        """Renvoie tous les postes d'un tournoi (ordonnés par numéro de cible)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(PosteORM)
                    .where(PosteORM.tournoi_id == tournoi_id)
                    .order_by(PosteORM.cible_index)
                ).scalars()
                return [_vers_poste(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des postes du tournoi.") from exc

    def par_code(self, code: str) -> Poste | None:
        """Relit le poste portant ce `code`, **tous tournois confondus**, ou `None`.

        Comparaison **exacte** sur la forme canonique (`domain.poste.normaliser_code`) : le code
        est stocké déjà normalisé (majuscules), la requête normalise la saisie — un `WHERE` indexé
        par la contrainte `UNIQUE` suffit.
        """
        try:
            with self._session_factory() as session:
                ligne = session.execute(
                    select(PosteORM).where(PosteORM.code == normaliser_code_poste(code))
                ).scalar_one_or_none()
                return None if ligne is None else _vers_poste(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du poste par code.") from exc


class InscriptionRepositorySQL:
    """Adapter SQLite du port `InscriptionRepository` — liens archer↔départ (E02US009, E08US002).

    `definir_paye_avec_trace` réalise la **couture de session partagée** (ADR-0035), comme
    `SerieRepositorySQL.enregistrer_avec_trace` : le nouveau statut de paiement **et** son entrée
    d'audit s'écrivent dans **une seule session, un seul `commit`**. D'où l'`AuditRepositorySQL`
    injecté — couplage **infra → infra** (le port `InscriptionRepository` ignore cette couture ; sa
    signature ne cite aucune session).
    """

    def __init__(
        self, session_factory: sessionmaker[Session], audit_repository: AuditRepositorySQL
    ) -> None:
        self._session_factory = session_factory
        self._audit = audit_repository

    def ajouter(self, inscription: Inscription) -> Inscription:
        """Persiste l'inscription et la renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = InscriptionORM(
                    archer_id=inscription.archer_id,
                    depart_id=inscription.depart_id,
                    paye=inscription.paye,
                )
                session.add(ligne)
                session.commit()
                return _vers_inscription(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance de l'inscription.") from exc

    def par_id(self, inscription_id: InscriptionId) -> Inscription | None:
        """Relit l'inscription d'identifiant donné, ou `None` si elle n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(InscriptionORM, inscription_id)
                return None if ligne is None else _vers_inscription(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture de l'inscription.") from exc

    def par_archer(self, archer_id: ArcherId) -> list[Inscription]:
        """Renvoie les inscriptions d'un archer, triées par départ (liste éventuellement vide)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(InscriptionORM)
                    .where(InscriptionORM.archer_id == archer_id)
                    .order_by(InscriptionORM.depart_id)
                ).scalars()
                return [_vers_inscription(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des inscriptions de l'archer.") from exc

    def par_depart(self, depart_id: DepartId) -> list[Inscription]:
        """Renvoie les inscriptions portant sur un départ (liste éventuellement vide)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(InscriptionORM)
                    .where(InscriptionORM.depart_id == depart_id)
                    .order_by(InscriptionORM.id)
                ).scalars()
                return [_vers_inscription(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des inscriptions du départ.") from exc

    def par_archer_et_depart(self, archer_id: ArcherId, depart_id: DepartId) -> Inscription | None:
        """Renvoie l'inscription du couple `(archer, départ)`, ou `None` (contrôle d'unicité)."""
        try:
            with self._session_factory() as session:
                ligne = session.execute(
                    select(InscriptionORM).where(
                        InscriptionORM.archer_id == archer_id,
                        InscriptionORM.depart_id == depart_id,
                    )
                ).scalar_one_or_none()
                return None if ligne is None else _vers_inscription(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture de l'inscription du couple.") from exc

    def enregistrer(self, inscription: Inscription) -> Inscription:
        """Met à jour une inscription déjà persistée (bascule de `paye`) et la renvoie.

        **Contrat** : l'appelant (le service) garantit l'existence. Le couple `(archer, départ)`
        d'une inscription persistée ne change pas — seule `paye` évolue.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(InscriptionORM, inscription.id)
                if ligne is None:
                    raise InfrastructureError("Inscription à mettre à jour introuvable en base.")
                ligne.paye = inscription.paye
                session.commit()
                return _vers_inscription(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour de l'inscription.") from exc

    def definir_paye_avec_trace(
        self, inscription_ids: Sequence[InscriptionId], paye: bool, entree: EntreeAudit
    ) -> list[Inscription]:
        """Bascule `paye` sur plusieurs inscriptions **et** co-écrit sa trace — une transaction.

        Tout ou rien (ADR-0035) : les inscriptions visées passent à `paye`, la trace est ajoutée
        dans **la même** session (via `AuditRepositorySQL.consigner_dans`, qui ne commit pas), puis
        un **unique** `commit` scelle l'ensemble. Un échec avant le commit ne laisse ni marquage non
        tracé, ni trace fantôme. Une ligne absente est une **incohérence technique** (l'appelant
        garantit l'existence) → `InfrastructureError`. Les inscriptions mises à jour sont renvoyées
        dans l'ordre des identifiants fournis.
        """
        try:
            with self._session_factory() as session:
                maj: list[InscriptionORM] = []
                for inscription_id in inscription_ids:
                    ligne = session.get(InscriptionORM, inscription_id)
                    if ligne is None:
                        raise InfrastructureError("Inscription à marquer introuvable en base.")
                    ligne.paye = paye
                    maj.append(ligne)
                self._audit.consigner_dans(session, entree)
                session.commit()
                return [_vers_inscription(ligne) for ligne in maj]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de marquage du paiement et de sa trace.") from exc

    def supprimer(self, inscription_id: InscriptionId) -> None:
        """Supprime l'inscription d'identifiant donné (désinscription ; existence garantie)."""
        try:
            with self._session_factory() as session:
                ligne = session.get(InscriptionORM, inscription_id)
                if ligne is None:
                    raise InfrastructureError("Inscription à supprimer introuvable en base.")
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression de l'inscription.") from exc

    def supprimer_avec_remboursement(
        self, inscription_id: InscriptionId, remboursement: Remboursement
    ) -> None:
        """Supprime l'inscription **et** ouvre son remboursement — une transaction (E08US005).

        Tout ou rien (ADR-0057, couture de session partagée comme `definir_paye_avec_trace`) : le
        remboursement est **inséré** puis l'inscription **supprimée** dans la **même** session, un
        **unique** `commit` scelle l'ensemble. Ordre insertion-avant-suppression sans importance
        (un seul commit), mais l'atomicité garantit qu'on n'efface **jamais** une inscription payée
        sans ouvrir sa contrepartie, ni l'inverse. Ligne absente = incohérence technique (l'appelant
        garantit l'existence) → `InfrastructureError`.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(InscriptionORM, inscription_id)
                if ligne is None:
                    raise InfrastructureError("Inscription à supprimer introuvable en base.")
                session.add(_remboursement_orm(remboursement))
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de désinscription avec remboursement.") from exc


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


class CategorieRepositorySQL:
    """Adapter SQLite du port `CategorieRepository` (E01US003)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, categorie: Categorie) -> Categorie:
        """Persiste la catégorie et la renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = CategorieORM(
                    tournoi_id=categorie.tournoi_id,
                    origine=categorie.origine.value,
                    libelle=categorie.libelle,
                    arme=categorie.arme,
                    ages=_ages_categorie(categorie),
                    sexe=None if categorie.sexe is None else categorie.sexe.value,
                    blason_id=categorie.blason_id,
                    hauteur_cm=categorie.hauteur_cm,
                )
                session.add(ligne)
                session.commit()
                return _vers_categorie(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance de la catégorie.") from exc

    def par_id(self, categorie_id: CategorieId) -> Categorie | None:
        """Relit la catégorie d'identifiant donné, ou `None` si elle n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(CategorieORM, categorie_id)
                return None if ligne is None else _vers_categorie(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture de la catégorie.") from exc

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Categorie]:
        """Renvoie toutes les catégories d'un tournoi (liste éventuellement vide)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(CategorieORM)
                    .where(CategorieORM.tournoi_id == tournoi_id)
                    .order_by(CategorieORM.id)
                ).scalars()
                return [_vers_categorie(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des catégories du tournoi.") from exc

    def par_bibliotheque(self) -> list[Categorie]:
        """Renvoie les modèles de bibliothèque — patrimoine du club, sans tournoi (E01US023)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(CategorieORM)
                    .where(CategorieORM.tournoi_id.is_(None))
                    .order_by(CategorieORM.id)
                ).scalars()
                return [_vers_categorie(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture de la bibliothèque de catégories.") from exc

    def par_blason(self, blason_id: BlasonId) -> list[Categorie]:
        """Renvoie les catégories dont le blason par défaut est `blason_id` (E01US006)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(CategorieORM)
                    .where(CategorieORM.blason_id == blason_id)
                    .order_by(CategorieORM.id)
                ).scalars()
                return [_vers_categorie(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des catégories par blason.") from exc

    def enregistrer(self, categorie: Categorie) -> Categorie:
        """Met à jour une catégorie déjà persistée (édition) et la renvoie.

        **Contrat** : l'appelant (le service) garantit l'existence (vérifiée en amont). La ligne
        absente est une **incohérence technique** (non un cas métier) → `InfrastructureError`.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(CategorieORM, categorie.id)
                if ligne is None:
                    raise InfrastructureError("Catégorie à mettre à jour introuvable en base.")
                ligne.libelle = categorie.libelle
                ligne.arme = categorie.arme
                ligne.ages = _ages_categorie(categorie)
                ligne.sexe = None if categorie.sexe is None else categorie.sexe.value
                ligne.blason_id = categorie.blason_id
                ligne.hauteur_cm = categorie.hauteur_cm
                session.commit()
                return _vers_categorie(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour de la catégorie.") from exc

    def supprimer(self, categorie_id: CategorieId) -> None:
        """Supprime la catégorie d'identifiant donné (existence garantie par l'appelant)."""
        try:
            with self._session_factory() as session:
                ligne = session.get(CategorieORM, categorie_id)
                if ligne is None:
                    raise InfrastructureError("Catégorie à supprimer introuvable en base.")
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression de la catégorie.") from exc


class BlasonRepositorySQL:
    """Adapter SQLite du port `BlasonRepository` (E01US005)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, blason: Blason) -> Blason:
        """Persiste le blason et le renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = BlasonORM(
                    tournoi_id=blason.tournoi_id,
                    origine=blason.origine.value,
                    nom=blason.nom,
                    taille=blason.taille,
                    capacite=blason.capacite,
                    zones=json.dumps([zone.value for zone in blason.zones]),
                )
                session.add(ligne)
                session.commit()
                return _vers_blason(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance du blason.") from exc

    def par_id(self, blason_id: BlasonId) -> Blason | None:
        """Relit le blason d'identifiant donné, ou `None` s'il n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(BlasonORM, blason_id)
                return None if ligne is None else _vers_blason(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du blason.") from exc

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Blason]:
        """Renvoie tous les blasons d'un tournoi (liste éventuellement vide)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(BlasonORM)
                    .where(BlasonORM.tournoi_id == tournoi_id)
                    .order_by(BlasonORM.id)
                ).scalars()
                return [_vers_blason(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des blasons du tournoi.") from exc

    def par_bibliotheque(self) -> list[Blason]:
        """Renvoie les modèles de bibliothèque — patrimoine du club, sans tournoi (E01US023)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(BlasonORM).where(BlasonORM.tournoi_id.is_(None)).order_by(BlasonORM.id)
                ).scalars()
                return [_vers_blason(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture de la bibliothèque de blasons.") from exc

    def enregistrer(self, blason: Blason) -> Blason:
        """Met à jour un blason déjà persisté (édition) et le renvoie.

        **Contrat** : l'appelant (le service) garantit l'existence (vérifiée en amont). La ligne
        absente est une **incohérence technique** (non un cas métier) → `InfrastructureError`.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(BlasonORM, blason.id)
                if ligne is None:
                    raise InfrastructureError("Blason à mettre à jour introuvable en base.")
                ligne.nom = blason.nom
                ligne.taille = blason.taille
                ligne.capacite = blason.capacite
                ligne.zones = json.dumps([zone.value for zone in blason.zones])
                session.commit()
                return _vers_blason(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour du blason.") from exc

    def supprimer(self, blason_id: BlasonId) -> None:
        """Supprime le blason d'identifiant donné (existence garantie par l'appelant)."""
        try:
            with self._session_factory() as session:
                ligne = session.get(BlasonORM, blason_id)
                if ligne is None:
                    raise InfrastructureError("Blason à supprimer introuvable en base.")
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression du blason.") from exc


class GabaritSalleRepositorySQL:
    """Adapter SQLite du port `GabaritSalleRepository` (E01US007, E01US008)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, gabarit: GabaritSalle) -> GabaritSalle:
        """Persiste le gabarit (modèle ou instance) et le renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = GabaritSalleORM(
                    nom=gabarit.nom,
                    nb_cibles=gabarit.nb_cibles,
                    config=_config_gabarit(gabarit),
                    tournoi_id=gabarit.tournoi_id,
                )
                session.add(ligne)
                session.commit()
                return _vers_gabarit(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance du gabarit de salle.") from exc

    def par_id(self, gabarit_id: GabaritSalleId) -> GabaritSalle | None:
        """Relit le gabarit d'identifiant donné, ou `None` s'il n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(GabaritSalleORM, gabarit_id)
                return None if ligne is None else _vers_gabarit(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du gabarit de salle.") from exc

    def lister(self) -> list[GabaritSalle]:
        """Renvoie les gabarits **modèles** (bibliothèque, `tournoi_id IS NULL`), par identifiant.

        Les instances appliquées à un tournoi (E01US008) sont **exclues** : elles se lisent via
        `par_tournoi`.
        """
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(GabaritSalleORM)
                    .where(GabaritSalleORM.tournoi_id.is_(None))
                    .order_by(GabaritSalleORM.id)
                ).scalars()
                return [_vers_gabarit(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des gabarits de salle.") from exc

    def par_tournoi(self, tournoi_id: TournoiId) -> GabaritSalle | None:
        """Renvoie l'instance de gabarit appliquée à un tournoi, ou `None` s'il n'y en a pas.

        Un tournoi porte au plus une instance ; en cas de multiplicité (ne devrait pas survenir),
        la plus récente (`id` le plus élevé) l'emporte.
        """
        try:
            with self._session_factory() as session:
                ligne = (
                    session.execute(
                        select(GabaritSalleORM)
                        .where(GabaritSalleORM.tournoi_id == tournoi_id)
                        .order_by(GabaritSalleORM.id.desc())
                    )
                    .scalars()
                    .first()
                )
                return None if ligne is None else _vers_gabarit(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du gabarit du tournoi.") from exc

    def enregistrer(self, gabarit: GabaritSalle) -> GabaritSalle:
        """Met à jour un gabarit déjà persisté (édition, ajustement) et le renvoie.

        **Contrat** : l'appelant (le service) garantit l'existence (vérifiée en amont). La ligne
        absente est une **incohérence technique** (non un cas métier) → `InfrastructureError`.
        Le rattachement `tournoi_id` d'un gabarit persisté ne change pas (édition sur place).
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(GabaritSalleORM, gabarit.id)
                if ligne is None:
                    raise InfrastructureError("Gabarit à mettre à jour introuvable en base.")
                ligne.nom = gabarit.nom
                ligne.nb_cibles = gabarit.nb_cibles
                ligne.config = _config_gabarit(gabarit)
                session.commit()
                return _vers_gabarit(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour du gabarit de salle.") from exc

    def supprimer(self, gabarit_id: GabaritSalleId) -> None:
        """Supprime le gabarit d'identifiant donné (existence garantie par l'appelant)."""
        try:
            with self._session_factory() as session:
                ligne = session.get(GabaritSalleORM, gabarit_id)
                if ligne is None:
                    raise InfrastructureError("Gabarit à supprimer introuvable en base.")
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression du gabarit de salle.") from exc


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


class ScoreRepositorySQL:
    """Adapter SQLite du port `ScoreRepository` (E00US011, E02US003)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, score: Score) -> Score:
        """Persiste le score et le renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = ScoreORM(archer_id=score.archer_id, points=score.points)
                session.add(ligne)
                session.commit()
                return Score(archer_id=ligne.archer_id, points=ligne.points, id=ligne.id)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance du score.") from exc

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Score]:
        """Renvoie tous les scores des archers d'un tournoi (jointure archer→tournoi)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(ScoreORM)
                    .join(ArcherORM, ScoreORM.archer_id == ArcherORM.id)
                    .where(ArcherORM.tournoi_id == tournoi_id)
                ).scalars()
                return [
                    Score(archer_id=ligne.archer_id, points=ligne.points, id=ligne.id)
                    for ligne in lignes
                ]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des scores du tournoi.") from exc

    def par_archer(self, archer_id: ArcherId) -> list[Score]:
        """Renvoie les scores d'un archer (liste éventuellement vide) — E02US003."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(ScoreORM).where(ScoreORM.archer_id == archer_id)
                ).scalars()
                return [
                    Score(archer_id=ligne.archer_id, points=ligne.points, id=ligne.id)
                    for ligne in lignes
                ]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des scores de l'archer.") from exc


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


class AuditRepositorySQL:
    """Adapter SQLite du port `AuditRepository` (E10US005) — journal en **ajout seul**.

    Ni `enregistrer` ni `supprimer` : une trace ne se retouche pas (valeur de preuve). `consigner`
    insère ; `par_tournoi` relit en **ordre chronologique** (`ORDER BY id`), l'id croissant
    coïncidant avec l'ordre d'insertion.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def consigner(self, entree: EntreeAudit) -> EntreeAudit:
        """Persiste une entrée d'audit et la renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = EntreeAuditORM(
                    tournoi_id=entree.tournoi_id,
                    action=entree.action.value,
                    auteur=entree.auteur,
                    horodatage=entree.horodatage,
                    objet=entree.objet,
                    avant=entree.avant,
                    apres=entree.apres,
                )
                session.add(ligne)
                session.commit()
                return _vers_entree_audit(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance de l'entrée d'audit.") from exc

    def consigner_dans(self, session: Session, entree: EntreeAudit) -> None:
        """Ajoute une entrée d'audit dans une session **fournie**, **sans commit** (ADR-0035).

        Face « session partagée » de `consigner`, réservée à la **co-écriture atomique**
        acte↔trace : l'appelant (un repository de co-écriture,
        `SerieRepositorySQL.enregistrer_avec_trace`) tient la transaction et fait le **commit
        unique** — score et trace tiennent dans un seul « tout ou rien ». Cette méthode **ne commit
        pas** : hors d'une telle couture, l'entrée ne serait jamais persistée. C'est délibérément
        une méthode de l'**adapter concret**, pas du port `AuditRepository` (domaine) : un paramètre
        `Session` (SQLAlchemy) ne peut franchir la frontière du domaine (règle 1, garde-fou AST).
        Le couplage reste **infra → infra**, entre adapters d'une même couche.
        """
        ligne = EntreeAuditORM(
            tournoi_id=entree.tournoi_id,
            action=entree.action.value,
            auteur=entree.auteur,
            horodatage=entree.horodatage,
            objet=entree.objet,
            avant=entree.avant,
            apres=entree.apres,
        )
        session.add(ligne)

    def par_tournoi(self, tournoi_id: TournoiId) -> list[EntreeAudit]:
        """Renvoie les entrées d'audit d'un tournoi, en ordre chronologique (id croissant)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(EntreeAuditORM)
                    .where(EntreeAuditORM.tournoi_id == tournoi_id)
                    .order_by(EntreeAuditORM.id)
                ).scalars()
                return [_vers_entree_audit(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du journal d'audit.") from exc


class RemboursementRepositorySQL:
    """Adapter SQLite du port `RemboursementRepository` (E08US005, ADR-0057).

    Registre des sommes encaissées à rendre. Les **créations** ne passent pas par cet adapter : une
    ligne naît **atomiquement** avec la suppression de l'inscription payée qui la provoque
    (`InscriptionRepositorySQL.supprimer_avec_remboursement`,
    `DepartRepositorySQL.supprimer_avec_remboursements`, via `_remboursement_orm`). Cet adapter sert
    la **lecture** (`par_tournoi`, `par_id`) et le **traitement** (`enregistrer_avec_trace`).

    `enregistrer_avec_trace` réalise la **couture de session partagée** (ADR-0035, comme
    `InscriptionRepositorySQL.definir_paye_avec_trace`) : le nouveau statut du remboursement **et**
    son entrée d'audit `REMBOURSEMENT` s'écrivent dans **une seule session, un seul `commit`**. D'où
    l'`AuditRepositorySQL` injecté — collaboration **infra → infra** (le port du domaine ignore la
    couture). L'entrée arrive **déjà construite et datée** par le service (via `Horloge`).
    """

    def __init__(
        self, session_factory: sessionmaker[Session], audit_repository: AuditRepositorySQL
    ) -> None:
        self._session_factory = session_factory
        self._audit = audit_repository

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Remboursement]:
        """Renvoie les remboursements d'un tournoi (ordre non garanti — le service trie)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(RemboursementORM).where(RemboursementORM.tournoi_id == tournoi_id)
                ).scalars()
                return [_vers_remboursement(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des remboursements.") from exc

    def par_id(self, remboursement_id: RemboursementId) -> Remboursement | None:
        """Renvoie le remboursement d'identifiant donné, ou `None` s'il n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(RemboursementORM, remboursement_id)
                return None if ligne is None else _vers_remboursement(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du remboursement.") from exc

    def enregistrer_avec_trace(
        self, remboursement: Remboursement, entree: EntreeAudit
    ) -> Remboursement:
        """Met à jour le remboursement traité **et** co-écrit sa trace `REMBOURSEMENT` — une
        transaction.

        Tout ou rien (ADR-0035) : le nouveau `statut`/`traite_le` et l'entrée d'audit (via
        `AuditRepositorySQL.consigner_dans`, qui ne commit pas) tiennent dans un **unique**
        `commit`.
        Ligne absente = incohérence technique (l'appelant garantit l'existence) →
        `InfrastructureError`.
        """
        assert remboursement.id is not None, "Un remboursement à traiter est persisté."
        try:
            with self._session_factory() as session:
                ligne = session.get(RemboursementORM, remboursement.id)
                if ligne is None:
                    raise InfrastructureError("Remboursement à traiter introuvable en base.")
                ligne.statut = remboursement.statut.value
                ligne.traite_le = remboursement.traite_le
                self._audit.consigner_dans(session, entree)
                session.commit()
                return _vers_remboursement(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError(
                "Échec de traitement du remboursement et de sa trace."
            ) from exc


class SerieRepositorySQL:
    """Adapter SQLite du port `SerieRepository` (E04US002) — série + volées enfants.

    Une série est un agrégat parent (`serie`) + ses volées (`volee`, table enfant). La saisie
    réécrit **toute** la série à chaque opération : le service charge l'agrégat, le mute (une volée
    ajoutée/validée/corrigée) et le repasse en entier — comme `PlacementRepositorySQL.definir_plan`,
    l'écriture est un **purge + réinsertion** des volées, la série étant la source de vérité (les
    volées sont des value objects sans identité propre côté domaine).

    `enregistrer_avec_trace` réalise la **couture de session partagée** (ADR-0035) : la série **et**
    son entrée d'audit s'écrivent dans **une seule session, un seul `commit`** (tout ou rien). D'où
    l'`AuditRepositorySQL` injecté au constructeur — collaboration **infra → infra** (le port du
    domaine `SerieRepository` ignore cette couture ; `enregistrer_avec_trace(serie, entree)` ne
    mentionne aucune session). L'entrée arrive **déjà construite et datée** par le service (via
    `Horloge`) : le repository ne construit ni ne date **le contenu** (série, trace).

    Il date en revanche une **métadonnée de persistance** : le `created_at` d'une volée (le
    « quand » de la saisie, ex-017), posé via le port `Horloge` — comme il attribue l'`id`. Il est
    **préservé par numéro** au travers du purge + réinsertion : réécrire une série (upsert) ne
    réinitialise pas l'horodatage de ses volées déjà saisies, seules les volées **nouvelles** sont
    datées de l'instant courant.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        audit_repository: AuditRepositorySQL,
        horloge: Horloge,
    ) -> None:
        self._session_factory = session_factory
        self._audit = audit_repository
        self._horloge = horloge

    def par_archer(self, tournoi_id: TournoiId, archer_id: ArcherId) -> Serie | None:
        """Relit la série de qualification de l'archer (volées triées par numéro), ou `None`."""
        try:
            with self._session_factory() as session:
                ligne = session.execute(
                    select(SerieORM).where(
                        SerieORM.tournoi_id == tournoi_id,
                        SerieORM.archer_id == archer_id,
                    )
                ).scalar_one_or_none()
                if ligne is None:
                    return None
                return _vers_serie(ligne, self._volees(session, ligne.id))
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture de la série.") from exc

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Serie]:
        """Relit toutes les séries d'un tournoi (volées triées par numéro), pour le classement.

        Deux requêtes (les séries, puis **toutes** leurs volées d'un bloc regroupées par série) —
        pas de N+1 par archer. L'ordre des séries n'est pas garanti (le classement trie) ; les
        volées de chacune le sont, par numéro (même contrat que `par_archer`).
        """
        try:
            with self._session_factory() as session:
                series = (
                    session.execute(select(SerieORM).where(SerieORM.tournoi_id == tournoi_id))
                    .scalars()
                    .all()
                )
                if not series:
                    return []
                volees_par_serie: dict[SerieId, list[VoleeORM]] = {}
                lignes_volees = (
                    session.execute(
                        select(VoleeORM)
                        .where(VoleeORM.serie_id.in_([s.id for s in series]))
                        .order_by(VoleeORM.serie_id, VoleeORM.numero)
                    )
                    .scalars()
                    .all()
                )
                for volee in lignes_volees:
                    volees_par_serie.setdefault(volee.serie_id, []).append(volee)
                return [_vers_serie(s, volees_par_serie.get(s.id, [])) for s in series]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des séries du tournoi.") from exc

    def horodatages(
        self, tournoi_id: TournoiId, archer_id: ArcherId
    ) -> dict[int, datetime.datetime]:
        """Le « quand » (`created_at`, UTC-aware) de chaque volée de l'archer, par **numéro** — `{}`
        s'il n'a pas de série.

        Chemin de lecture/consultation du « quand » (ex-017), tenu **à l'écart du domaine** `Volee`
        (métadonnée de persistance, arbitrage de revue) : l'API le joint à la série par numéro pour
        afficher « volée N saisie par … à HH:MM ». UTC réattaché comme l'`horodatage` d'audit
        (SQLite stocke sans fuseau, l'application n'écrit que de l'UTC).
        """
        try:
            with self._session_factory() as session:
                ligne = session.execute(
                    select(SerieORM).where(
                        SerieORM.tournoi_id == tournoi_id,
                        SerieORM.archer_id == archer_id,
                    )
                ).scalar_one_or_none()
                if ligne is None:
                    return {}
                return {
                    volee.numero: (
                        volee.created_at
                        if volee.created_at.tzinfo is not None
                        else volee.created_at.replace(tzinfo=datetime.UTC)
                    )
                    for volee in self._volees(session, ligne.id)
                }
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des horodatages de volées.") from exc

    def enregistrer(self, serie: Serie) -> Serie:
        """Persiste une série (saisie sans trace) — **une** transaction (parent + volées)."""
        try:
            with self._session_factory() as session:
                ligne = self._poser_serie(session, serie)
                session.commit()
                return _vers_serie(ligne, self._volees(session, ligne.id))
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance de la série.") from exc

    def enregistrer_avec_trace(self, serie: Serie, entree: EntreeAudit) -> Serie:
        """Persiste la série **et** son entrée d'audit dans **une seule transaction** (ADR-0035).

        Tout ou rien : la série est réécrite, la trace est ajoutée dans **la même** session (via
        `AuditRepositorySQL.consigner_dans`, qui ne commit pas), puis un **unique** `commit` scelle
        les deux. Un échec avant le commit ne laisse ni validation/correction non tracée, ni trace
        fantôme (testé sur injection d'échec).
        """
        try:
            with self._session_factory() as session:
                ligne = self._poser_serie(session, serie)
                self._audit.consigner_dans(session, entree)
                session.commit()
                return _vers_serie(ligne, self._volees(session, ligne.id))
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance de la série et de sa trace.") from exc

    def _poser_serie(self, session: Session, serie: Serie) -> SerieORM:
        """Upsert le parent `serie` (clé métier `tournoi_id, archer_id`) et réécrit ses volées.

        Ne commit pas — l'appelant tient la transaction (une seule, éventuellement partagée avec
        l'audit). Renvoie la ligne parente (id attribué). Les volées sont **purgées puis
        réinsérées** (la série passée est la source de vérité) ; `flush` attribue l'id d'une série
        nouvelle avant de rattacher ses volées.

        Le `created_at` de chaque volée est **préservé par numéro** : on relit les horodatages
        existants **avant** la purge et on les réapplique aux volées de même numéro ; une volée
        **nouvelle** (numéro absent) est datée de l'instant courant (`Horloge`). Sans quoi le purge
        + réinsertion réinitialiserait le « quand » à chaque sauvegarde (ex-017).
        """
        ligne = self._ligne_serie(session, serie)
        horodatages = {v.numero: v.created_at for v in self._volees(session, ligne.id)}
        maintenant = self._horloge.maintenant()
        session.execute(delete(VoleeORM).where(VoleeORM.serie_id == ligne.id))
        session.add_all(
            VoleeORM(
                serie_id=ligne.id,
                numero=volee.numero,
                valeurs=_valeurs_json(volee),
                saisie_par=volee.saisie_par,
                validee_par=volee.validee_par,
                created_at=horodatages.get(volee.numero, maintenant),
            )
            for volee in serie.volees
        )
        return ligne

    def _ligne_serie(self, session: Session, serie: Serie) -> SerieORM:
        """Retrouve la ligne parente **par sa clé métier** `(tournoi_id, archer_id)`, ou la crée.

        L'identité d'une série **est** son couple `(tournoi, archer)` — « une série par archer »
        (port `SerieRepository`, garanti par `uq_serie_tournoi_archer`). On ne cherche donc **pas**
        par `serie.id` : ce lookup PK n'était qu'une micro-optimisation, ouvrant une surface de
        corruption silencieuse (un `id` incohérent avec la clé métier — venu d'un futur appelant —
        aurait fait réécrire les volées sur la **mauvaise** série). La clé métier est la requête
        d'identité canonique (celle de `par_archer`). `flush` attribue l'id d'une série nouvelle
        avant qu'on lui rattache ses volées.
        """
        ligne = session.execute(
            select(SerieORM).where(
                SerieORM.tournoi_id == serie.tournoi_id,
                SerieORM.archer_id == serie.archer_id,
            )
        ).scalar_one_or_none()
        if ligne is None:
            ligne = SerieORM(tournoi_id=serie.tournoi_id, archer_id=serie.archer_id)
            session.add(ligne)
            session.flush()
        return ligne

    def _volees(self, session: Session, serie_id: SerieId) -> Sequence[VoleeORM]:
        """Les volées d'une série, triées par numéro (ordre du barème)."""
        return (
            session.execute(
                select(VoleeORM).where(VoleeORM.serie_id == serie_id).order_by(VoleeORM.numero)
            )
            .scalars()
            .all()
        )


class DuelRepositorySQL:
    """Adapter SQLite du port `DuelRepository` — le tir d'un match du tableau (E04US013, ADR-0049).

    On ne persiste que le **tir** (manches, barrage, validateur), keyé `(phase_id, match_numero)` :
    ni barème ni participants (l'appariement, recalculé du classement — ADR-0048). `charger`
    réhydrate donc un `Duel` en **recevant** ce contexte du service. Écriture idempotente par upsert
    sur la clé composite (patron `PlacementTableauRepositorySQL`).
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def numeros_enregistres(self, phase_id: PhaseId) -> frozenset[int]:
        """Les `match_numero` de la phase porteurs d'un tir (pour ne charger que ceux-là)."""
        try:
            with self._session_factory() as session:
                numeros = session.execute(
                    select(DuelORM.match_numero).where(DuelORM.phase_id == phase_id)
                ).scalars()
                return frozenset(numeros)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des duels d'une phase.") from exc

    def charger(self, phase_id: PhaseId, match_numero: int, *, bareme: BaremeDuel) -> Duel | None:
        """Réhydrate le duel d'un match (duellistes stockés + barème), ou `None` si absent."""
        try:
            with self._session_factory() as session:
                ligne = session.get(DuelORM, (phase_id, match_numero))
                if ligne is None:
                    return None
                return _vers_duel(ligne, bareme=bareme)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture d'un duel.") from exc

    def enregistrer(self, phase_id: PhaseId, match_numero: int, duel: Duel) -> Duel:
        """Persiste le tir **et l'identité des duellistes** (upsert sur `(phase, match)`)."""
        try:
            with self._session_factory() as session:
                ligne = session.get(DuelORM, (phase_id, match_numero))
                if ligne is None:
                    session.add(
                        DuelORM(
                            phase_id=phase_id,
                            match_numero=match_numero,
                            haut_genre=duel.participant_haut.genre.value,
                            haut_ref=duel.participant_haut.ref_id,
                            bas_genre=duel.participant_bas.genre.value,
                            bas_ref=duel.participant_bas.ref_id,
                            manches=_manches_json(duel),
                            barrage=_barrage_json(duel),
                            validee_par=duel.validee_par,
                        )
                    )
                else:
                    ligne.haut_genre = duel.participant_haut.genre.value
                    ligne.haut_ref = duel.participant_haut.ref_id
                    ligne.bas_genre = duel.participant_bas.genre.value
                    ligne.bas_ref = duel.participant_bas.ref_id
                    ligne.manches = _manches_json(duel)
                    ligne.barrage = _barrage_json(duel)
                    ligne.validee_par = duel.validee_par
                session.commit()
                return duel
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance d'un duel.") from exc


def _vers_forfait(ligne: ForfaitORM) -> Forfait:
    """Traduit une ligne ORM en agrégat de domaine `Forfait` (E04US015, ADR-0050).

    `nature` : la valeur relue redevient l'énumération `NatureForfait`. `declare_le` : SQLite stocke
    un `DateTime` **sans fuseau** ; on lui **réattache UTC** (le service n'écrit que de l'UTC via
    `Horloge`), round-trip fidèle comme l'horodatage d'audit.
    """
    declare_le = ligne.declare_le
    if declare_le.tzinfo is None:
        declare_le = declare_le.replace(tzinfo=datetime.UTC)
    return Forfait(
        tournoi_id=ligne.tournoi_id,
        archer_id=ligne.archer_id,
        phase_id=ligne.phase_id,
        nature=NatureForfait(ligne.nature),
        declare_par=ligne.declare_par,
        declare_le=declare_le,
        motif=ligne.motif,
        id=ligne.id,
    )


def _remboursement_orm(remboursement: Remboursement) -> RemboursementORM:
    """Construit une ligne ORM `remboursement` depuis l'agrégat (statut/motif → valeur d'énum).

    Partagé par les trois sites d'écriture — la co-écriture à la désinscription
    (`InscriptionRepositorySQL`), à la suppression d'un départ (`DepartRepositorySQL`) — d'où une
    fonction libre plutôt qu'une méthode. `id` reste `None` (auto-attribué par SQLite à
    l'insertion).
    """
    return RemboursementORM(
        tournoi_id=remboursement.tournoi_id,
        archer_prenom=remboursement.archer_prenom,
        archer_nom=remboursement.archer_nom,
        creneau=remboursement.creneau,
        montant_centimes=remboursement.montant_centimes,
        motif=remboursement.motif.value,
        statut=remboursement.statut.value,
        cree_le=remboursement.cree_le,
        traite_le=remboursement.traite_le,
    )


def _vers_remboursement(ligne: RemboursementORM) -> Remboursement:
    """Traduit une ligne ORM `remboursement` en agrégat de domaine (E08US005, ADR-0057).

    `motif`/`statut` : la valeur relue redevient l'énumération. `cree_le`/`traite_le` : SQLite
    stocke
    un `DateTime` **sans fuseau** ; on **réattache UTC** (le service n'écrit que de l'UTC via
    `Horloge`), round-trip fidèle comme l'horodatage d'audit. `traite_le` reste `None` tant que le
    poste est à traiter.
    """
    cree_le = ligne.cree_le
    if cree_le.tzinfo is None:
        cree_le = cree_le.replace(tzinfo=datetime.UTC)
    traite_le = ligne.traite_le
    if traite_le is not None and traite_le.tzinfo is None:
        traite_le = traite_le.replace(tzinfo=datetime.UTC)
    return Remboursement(
        tournoi_id=ligne.tournoi_id,
        archer_prenom=ligne.archer_prenom,
        archer_nom=ligne.archer_nom,
        creneau=ligne.creneau,
        montant_centimes=ligne.montant_centimes,
        motif=MotifRemboursement(ligne.motif),
        cree_le=cree_le,
        statut=StatutRemboursement(ligne.statut),
        traite_le=traite_le,
        id=ligne.id,
    )


class ForfaitRepositorySQL:
    """Adapter SQLite du port `ForfaitRepository` (E04US015, ADR-0050) — forfait + trace atomiques.

    `declarer_avec_trace` / `annuler_avec_trace` co-écrivent le forfait (ajout / suppression) **et**
    son entrée d'audit dans **une seule session, un seul `commit`** (ADR-0035, comme
    `SerieRepositorySQL`) — d'où l'`AuditRepositorySQL` injecté (collaboration infra → infra ; le
    port du domaine ignore la couture de session). L'entrée arrive **déjà construite et datée** par
    le service (via `Horloge`) ; le forfait porte lui aussi sa propre date de déclaration.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        audit_repository: AuditRepositorySQL,
    ) -> None:
        self._session_factory = session_factory
        self._audit = audit_repository

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Forfait]:
        """Tous les forfaits d'un tournoi (ordre non garanti)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(ForfaitORM).where(ForfaitORM.tournoi_id == tournoi_id)
                ).scalars()
                return [_vers_forfait(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des forfaits du tournoi.") from exc

    def par_phase(self, phase_id: PhaseId) -> list[Forfait]:
        """Les forfaits déclarés dans une phase (qualif → classement ; tableau → walkover duels)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(ForfaitORM).where(ForfaitORM.phase_id == phase_id)
                ).scalars()
                return [_vers_forfait(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des forfaits de la phase.") from exc

    def par_archer_et_phase(
        self, tournoi_id: TournoiId, archer_id: ArcherId, phase_id: PhaseId
    ) -> Forfait | None:
        """Le forfait de cet archer dans cette phase, ou `None` (garde de doublon / annulation)."""
        try:
            with self._session_factory() as session:
                ligne = session.execute(
                    select(ForfaitORM).where(
                        ForfaitORM.tournoi_id == tournoi_id,
                        ForfaitORM.archer_id == archer_id,
                        ForfaitORM.phase_id == phase_id,
                    )
                ).scalar_one_or_none()
                return None if ligne is None else _vers_forfait(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du forfait.") from exc

    def declarer_avec_trace(self, forfait: Forfait, entree: EntreeAudit) -> Forfait:
        """Insère le forfait **et** sa trace dans **une seule transaction** (tout ou rien)."""
        try:
            with self._session_factory() as session:
                ligne = ForfaitORM(
                    tournoi_id=forfait.tournoi_id,
                    archer_id=forfait.archer_id,
                    phase_id=forfait.phase_id,
                    nature=forfait.nature.value,
                    declare_par=forfait.declare_par,
                    declare_le=forfait.declare_le,
                    motif=forfait.motif,
                )
                session.add(ligne)
                self._audit.consigner_dans(session, entree)
                session.commit()
                return _vers_forfait(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance du forfait et de sa trace.") from exc

    def annuler_avec_trace(self, forfait: Forfait, entree: EntreeAudit) -> None:
        """Supprime le forfait (`forfait.id`) et consigne sa trace d'annulation, atomiquement."""
        try:
            with self._session_factory() as session:
                session.execute(delete(ForfaitORM).where(ForfaitORM.id == forfait.id))
                self._audit.consigner_dans(session, entree)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de l'annulation du forfait et de sa trace.") from exc
