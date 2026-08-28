"""Fil rouge du walking skeleton : inscrire, placer, saisir, classer.

⚠️ **Tranche verticale provisoire** — elle sera démantelée quand le placement (E03) et la saisie
(E04) auront leurs propres surfaces. Ne rien y ajouter qui ait vocation à durer.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import autoriser_saisie, exiger_admin
from application.archers import ServiceArchers
from application.classements import ServiceClassement
from domain.archer import Archer
from domain.classement import Classement
from domain.doublons import PaireDoublon
from domain.poste import Poste
from domain.score import Score
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["competition"])


class AjouterArcherRequete(BaseModel):
    """Corps d'inscription d'un archer à un tournoi (E02US002).

    `categorie_id` est **obligatoire** et doit désigner une catégorie du tournoi visé. `club_id`
    reste **facultatif** : absent, il vaut « club encore inconnu » — jamais « aucun club »
    (ADR-0014). `autoriser_homonyme` est la **confirmation** de l'admin après un premier refus
    `homonyme_archer` (409) : il déclare que ce nouvel archer, malgré des nom, prénom et club
    identiques à un inscrit, est bien une autre personne (un père et son fils, typiquement).
    """

    nom: str
    prenom: str
    categorie_id: int
    club_id: int | None = None
    autoriser_homonyme: bool = False


class ModifierArcherRequete(BaseModel):
    """Corps d'édition d'un archer inscrit (E02US003) — **remplacement total**.

    DTO distinct d'`AjouterArcherRequete` : les deux corps divergent déjà, et le patron est un DTO
    par cas d'usage (E02US001). Les quatre champs sont **tous** attendus, c'est un PUT ; `club_id`
    absent ou `null` **détache** le club (ADR-0014), jamais « laisse en l'état ». ⚠️ Les deux
    drapeaux sont des **confirmations indépendantes** après un premier 409 — si les deux faits sont
    vrais, le client reçoit un 409 pour l'un puis pour l'autre, pas un blanc-seing.
    """

    nom: str
    prenom: str
    categorie_id: int
    club_id: int | None = None
    autoriser_homonyme: bool = False
    autoriser_changement_categorie: bool = False


class DefinirHandicapRequete(BaseModel):
    """Corps de réglage du handicap d'un archer (E05US015) — **remplacement total**.

    Les deux valeurs sont attendues ensemble : `officiel` (la référence entretenue par le club) et
    `surcharge` (celle qui la prime pour cette édition). Absentes ou `null`, elles **effacent** —
    même convention que `club_id` dans `ModifierArcherRequete`, et pour la même raison : « je
    retire la surcharge » est une action que l'organisateur demandera, elle doit être exprimable.
    """

    officiel: int | None = None
    surcharge: int | None = None


class PlacerArcherRequete(BaseModel):
    """Corps de placement d'un archer sur une cible."""

    cible: int


class SaisirScoreRequete(BaseModel):
    """Corps de saisie d'une flèche marquée."""

    points: int


class ArcherReponse(BaseModel):
    """Représentation d'un archer renvoyée au client."""

    id: int
    tournoi_id: int
    nom: str
    prenom: str
    categorie_id: int
    cible: int | None
    club_id: int | None
    handicap_officiel: int | None
    handicap_surcharge: int | None
    handicap: int
    """Le handicap **effectif** — la surcharge si elle existe, sinon l'officiel, sinon 0.

    Champ **dérivé** exposé en plus des deux sources, délibérément : c'est lui que la feuille de
    marque et l'écran de classement affichent, et le recalculer côté client obligerait chaque
    surface à réimplémenter la règle de priorité. Une règle métier dupliquée dans trois écrans finit
    toujours par diverger dans l'un d'eux."""

    @staticmethod
    def de_agregat(archer: Archer) -> ArcherReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de réponse."""
        assert archer.id is not None, "Un archer persisté a toujours un identifiant."
        return ArcherReponse(
            id=archer.id,
            tournoi_id=archer.tournoi_id,
            nom=archer.nom,
            prenom=archer.prenom,
            categorie_id=archer.categorie_id,
            cible=archer.cible,
            club_id=archer.club_id,
            handicap_officiel=archer.handicap_officiel,
            handicap_surcharge=archer.handicap_surcharge,
            handicap=archer.handicap,
        )


class FusionnerArcherRequete(BaseModel):
    """Corps de fusion d'un doublon (E02US005).

    L'`{gagnant_id}` de l'URL est la fiche **maître** (celle qui survit) ; `perdant_id` est la fiche
    **absorbée**. C'est l'admin qui choisit ce sens : la machine ne fusionne jamais d'office (le
    rapprochement est heuristique, ADR-0015).
    """

    perdant_id: int


class PaireDoublonReponse(BaseModel):
    """Une paire de fiches rapprochées et son niveau de certitude (E02US005).

    `niveau` vaut `"probable"` (doublon très vraisemblable) ou `"a_verifier"` (rapprochement
    approximatif à confirmer). Les deux fiches sont ordonnées par identifiant croissant
    (déterminisme d'affichage) ; l'écran laisse l'admin désigner la maître avant de fusionner.
    """

    niveau: str
    a: ArcherReponse
    b: ArcherReponse

    @staticmethod
    def de_paire(paire: PaireDoublon) -> PaireDoublonReponse:
        """Traduit une paire de domaine en DTO de réponse."""
        return PaireDoublonReponse(
            niveau=paire.niveau.value,
            a=ArcherReponse.de_agregat(paire.a),
            b=ArcherReponse.de_agregat(paire.b),
        )


class ScoreReponse(BaseModel):
    """Représentation d'un score renvoyée au client."""

    id: int
    archer_id: int
    points: int

    @staticmethod
    def de_agregat(score: Score) -> ScoreReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de réponse."""
        assert score.id is not None, "Un score persisté a toujours un identifiant."
        return ScoreReponse(id=score.id, archer_id=score.archer_id, points=score.points)


class LigneClassementReponse(BaseModel):
    """Une ligne de classement renvoyée au client (E06US001).

    Deux rangs : `rang_scratch` (global) et `rang_categorie`. `nb_dix`/`nb_neuf` rendent le
    **départage traçable**. `club_id` à `null` = club encore **inconnu**, le signal que l'écran
    affiche pour que l'anomalie soit résorbée (ADR-0014) ; le nom n'est pas résolu ici. ⚠️ `statut`
    `disqualifie` **sort** l'archer du classement — les deux rangs sont donc **nullables**, son
    score restant affiché (ADR-0050). `abandon` est relégué en fin, mais rangé.
    """

    rang_scratch: int | None
    rang_categorie: int | None
    archer_id: int
    nom: str
    prenom: str
    categorie_id: int
    categorie_libelle: str
    cible: int | None
    club_id: int | None
    total: int
    nb_dix: int
    nb_neuf: int
    statut: str


class EgaliteADepartagerReponse(BaseModel):
    """Un ex æquo que le format de ce tournoi veut voir tranché **au tir** (E06US003, ADR-0066).

    Signalé, pas organisé : c'est l'organisateur qui décide de faire tirer. Vide tant qu'aucun seuil
    de barrage n'est réglé sur la phase de qualification — le défaut reste l'ex æquo partagé.
    """

    rang: int
    archer_ids: list[int]


class ClassementReponse(BaseModel):
    """Classement d'un **créneau** renvoyé au client.

    ⚠️ `depart_id` et non `tournoi_id` (correctif de revue E01US025) : le DTO **publiait un
    identifiant de départ sous un nom de tournoi**. C'est `DETTE-044` en acte — `DepartId` et
    `TournoiId` sont deux alias de `int`, mypy ne voit rien — et le test censé l'attraper le
    consacrait, vert parce que le tournoi et le départ du décor portaient tous deux l'`id` 1.
    """

    depart_id: int
    lignes: list[LigneClassementReponse]
    egalites_a_departager: list[EgaliteADepartagerReponse] = []

    @staticmethod
    def de_agregat(depart_id: int, classement: Classement) -> ClassementReponse:
        """Traduit le classement de domaine en DTO de réponse."""
        return ClassementReponse(
            depart_id=depart_id,
            egalites_a_departager=[
                EgaliteADepartagerReponse(
                    rang=egalite.rang,
                    archer_ids=[p.ref_id for p in egalite.participants],
                )
                for egalite in classement.egalites_a_departager
            ],
            lignes=[
                LigneClassementReponse(
                    rang_scratch=ligne.rang_scratch,
                    rang_categorie=ligne.rang_categorie,
                    archer_id=ligne.archer_id,
                    nom=ligne.nom,
                    prenom=ligne.prenom,
                    categorie_id=ligne.categorie_id,
                    categorie_libelle=ligne.categorie_libelle,
                    cible=ligne.cible,
                    club_id=ligne.club_id,
                    total=ligne.total,
                    nb_dix=ligne.nb_dix,
                    nb_neuf=ligne.nb_neuf,
                    statut=ligne.statut.value,
                )
                for ligne in classement.lignes
            ],
        )


@router.post(
    "/tournois/{tournoi_id}/archers",
    status_code=201,
    response_model=ArcherReponse,
    dependencies=[Depends(exiger_admin)],
)
async def ajouter_archer(
    tournoi_id: int, requete: AjouterArcherRequete, request: Request
) -> ArcherReponse:
    """Inscrit un archer à un tournoi (**écriture**, session requise — E10US001 ; ADR-0005).

    Renvoie `409 homonyme_archer` si un archer de mêmes nom, prénom et club est déjà inscrit :
    c'est un **signalement**, que le client lève en rejouant l'appel avec `autoriser_homonyme`
    (E02US002).
    """
    service: ServiceArchers = request.app.state.service_archers
    write_queue: WriteQueue = request.app.state.write_queue
    archer = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.ajouter(
                tournoi_id,
                requete.nom,
                requete.prenom,
                requete.categorie_id,
                requete.club_id,
                requete.autoriser_homonyme,
            )
        )
    )
    return ArcherReponse.de_agregat(archer)


@router.get("/tournois/{tournoi_id}/archers", response_model=list[ArcherReponse])
async def lister_archers(tournoi_id: int, request: Request) -> list[ArcherReponse]:
    """Renvoie les inscrits d'un tournoi, triés par nom puis prénom (lecture hors boucle).

    Alimente l'écran d'administration des archers (E02US003). Lecture **ouverte**, comme le
    classement : la liste des inscrits est affichée publiquement le jour J.
    """
    service: ServiceArchers = request.app.state.service_archers
    archers = await run_in_threadpool(service.lister, tournoi_id)
    return [ArcherReponse.de_agregat(archer) for archer in archers]


@router.put(
    "/archers/{archer_id}",
    response_model=ArcherReponse,
    dependencies=[Depends(exiger_admin)],
)
async def modifier_archer(
    archer_id: int, requete: ModifierArcherRequete, request: Request
) -> ArcherReponse:
    """Corrige un archer inscrit (**écriture**, session requise — E10US001 ; E02US003).

    Renvoie `409 homonyme_archer` ou `409 changement_categorie_archer_engage` — des
    **signalements**, que le client lève en rejouant l'appel avec le drapeau correspondant.
    """
    service: ServiceArchers = request.app.state.service_archers
    write_queue: WriteQueue = request.app.state.write_queue
    archer = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.modifier(
                archer_id,
                requete.nom,
                requete.prenom,
                requete.categorie_id,
                requete.club_id,
                requete.autoriser_homonyme,
                requete.autoriser_changement_categorie,
            )
        )
    )
    return ArcherReponse.de_agregat(archer)


@router.put(
    "/archers/{archer_id}/handicap",
    response_model=ArcherReponse,
    dependencies=[Depends(exiger_admin)],
)
async def definir_handicap_archer(
    archer_id: int, requete: DefinirHandicapRequete, request: Request
) -> ArcherReponse:
    """Fixe le handicap d'un archer (**écriture**, session requise — E10US001 ; E05US015).

    Ressource **séparée** de `PUT /archers/{id}` : mêler les deux obligerait à renvoyer
    nom/prénom/catégorie à chaque ajustement, donc à écraser une correction faite entre-temps
    depuis un autre poste. `422 handicap_invalide` sur une valeur négative **ou supérieure au score
    parfait d'une qualification** : un handicap s'**ajoute** au score, au-delà il le remplacerait.
    """
    service: ServiceArchers = request.app.state.service_archers
    write_queue: WriteQueue = request.app.state.write_queue
    archer = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.definir_handicap(archer_id, requete.officiel, requete.surcharge)
        )
    )
    return ArcherReponse.de_agregat(archer)


@router.delete(
    "/archers/{archer_id}",
    status_code=204,
    dependencies=[Depends(exiger_admin)],
)
async def supprimer_archer(
    archer_id: int, request: Request, autoriser_suppression_engage: bool = False
) -> Response:
    """Désinscrit un archer (**écriture**, session requise — E10US001 ; E02US003).

    `409 archer_engage` si l'archer est placé ou a déjà tiré : un **signalement**, que le client
    lève avec `autoriser_suppression_engage` ; la suppression confirmée **efface ses scores et son
    placement**. Un abandon relève du forfait (E04US015, ADR-0050), pas d'ici. ⚠️ Le drapeau est en
    **paramètre de requête** et non dans le corps — divergence à ADR-0015 qu'ADR-0016 sanctionne :
    un `DELETE` n'a pas de corps par convention, et des intermédiaires le suppriment.
    """
    service: ServiceArchers = request.app.state.service_archers
    write_queue: WriteQueue = request.app.state.write_queue
    await asyncio.wrap_future(
        write_queue.submit(lambda: service.supprimer(archer_id, autoriser_suppression_engage))
    )
    return Response(status_code=204)


@router.get(
    "/tournois/{tournoi_id}/doublons",
    response_model=list[PaireDoublonReponse],
    dependencies=[Depends(exiger_admin)],
)
async def detecter_doublons(tournoi_id: int, request: Request) -> list[PaireDoublonReponse]:
    """Liste les paires d'inscrits vraisemblablement en double (lecture hors boucle — E02US005).

    Réservée à l'**admin** : c'est un outil de nettoyage de la liste, pas une vue publique. Le
    rapprochement (nom/prénom/club, exact et approximatif) est **heuristique** : chaque paire porte
    un niveau (`probable` / `a_verifier`) et l'admin tranche par la fusion.
    """
    service: ServiceArchers = request.app.state.service_archers
    paires = await run_in_threadpool(service.detecter_doublons, tournoi_id)
    return [PaireDoublonReponse.de_paire(paire) for paire in paires]


@router.post(
    "/archers/{gagnant_id}/fusionner",
    response_model=ArcherReponse,
    dependencies=[Depends(exiger_admin)],
)
async def fusionner_archer(
    gagnant_id: int, requete: FusionnerArcherRequete, request: Request
) -> ArcherReponse:
    """Fusionne un doublon : la fiche `{gagnant_id}` absorbe `perdant_id` (**écriture** — E02US005).

    Renvoie `409 fusion_impossible` (même fiche, ou deux tournois) ou `409 fusion_archers_engages`
    (les deux fiches ont déjà tiré) ; `404 archer_introuvable` si une fiche n'existe pas. En cas de
    succès, la fiche maître est renvoyée et l'absorbée a disparu, ses inscriptions et scores repris.
    """
    service: ServiceArchers = request.app.state.service_archers
    write_queue: WriteQueue = request.app.state.write_queue
    archer = await asyncio.wrap_future(
        write_queue.submit(lambda: service.fusionner(gagnant_id, requete.perdant_id))
    )
    return ArcherReponse.de_agregat(archer)


@router.post(
    "/archers/{archer_id}/placement",
    response_model=ArcherReponse,
    dependencies=[Depends(exiger_admin)],
)
async def placer_archer(
    archer_id: int, requete: PlacerArcherRequete, request: Request
) -> ArcherReponse:
    """Place un archer sur une cible (**écriture**, session requise — E10US001)."""
    service: ServiceArchers = request.app.state.service_archers
    write_queue: WriteQueue = request.app.state.write_queue
    archer = await asyncio.wrap_future(
        write_queue.submit(lambda: service.placer(archer_id, requete.cible))
    )
    return ArcherReponse.de_agregat(archer)


@router.post(
    "/archers/{archer_id}/scores",
    status_code=201,
    response_model=ScoreReponse,
)
async def saisir_score(
    archer_id: int,
    requete: SaisirScoreRequete,
    request: Request,
    poste_autorise: Annotated[Poste | None, Depends(autoriser_saisie)],
) -> ScoreReponse:
    """Enregistre une flèche marquée par un archer (**écriture** — E10US001, E10US007).

    Autorisée à l'**admin** ou au **poste de cible** (E04US001), qui ne peut marquer que pour
    **sa** cible : `autoriser_saisie` rend le `Poste`, transmis au service qui fait respecter
    l'invariant (403 sinon). La **validation** reste réservée au scoreur (E04US002).
    `Annotated[..., Depends]` plutôt qu'un défaut : premier endpoint à exploiter la **valeur**
    rendue par sa dépendance, et cette forme évite le faux positif B008 sans `noqa`.
    """
    service: ServiceArchers = request.app.state.service_archers
    write_queue: WriteQueue = request.app.state.write_queue
    score = await asyncio.wrap_future(
        write_queue.submit(lambda: service.saisir_score(archer_id, requete.points, poste_autorise))
    )
    return ScoreReponse.de_agregat(score)


@router.get("/departs/{depart_id}/classement", response_model=ClassementReponse)
async def consulter_classement(
    depart_id: int, request: Request, categorie_id: int | None = None
) -> ClassementReponse:
    """Renvoie le classement de qualification **d'un départ** (lecture directe hors boucle).

    ⚠️ **La route a changé de parent en E01US025** (ADR-0075) : elle pendait au tournoi et
    fusionnait tous les créneaux — 4 départs de 100 rendaient un classement de 400, où l'archer du
    matin était rangé contre celui du soir. Rupture assumée : aucun client tiers. `categorie_id`
    **filtre** l'affichage ; les rangs restent ceux du classement complet **du départ**.
    """
    service: ServiceClassement = request.app.state.service_classement
    classement = await run_in_threadpool(service.pour_depart, depart_id, categorie_id)
    return ClassementReponse.de_agregat(depart_id, classement)
