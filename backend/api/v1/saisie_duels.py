"""Endpoints REST de la saisie en duels (E04US013) — le **scoreur** score un match du tableau.

Expose le service `ServiceSaisieDuels` au scoreur : consulter le **tableau reconstruit** (matchs,
occupants, tirs, podium), **saisir une manche** (les deux volées d'un set), **saisir le barrage**
(shoot-off à égalité), et **valider** un duel tranché — son vainqueur fait alors avancer le tableau
(« transmis au moteur E05US005 »). La validation est un acte du **scoreur** (comme la qualification,
E04US002 : validation = scoreur seul) ; le scoreur, itinérant, n'agit que dans **son** tournoi
(`403 scoreur_hors_tournoi`). Écritures routées par la **file** (writer unique) et **dédoublonnées**
par identifiant de saisie (ADR-0036). DTO Pydantic distincts des agrégats ; erreurs typées traduites
à la frontière (`api/erreurs.py`).
"""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_scoreur
from application.erreurs import ScoreurHorsTournoi
from application.saisie_duels import Duelliste, EtatDuel, EtatTableau, ServiceSaisieDuels
from domain.blason import ZoneScore
from domain.duel import Cote
from domain.scoreur import Scoreur
from infrastructure.db import WriteQueue
from infrastructure.idempotence import RegistreIdempotence

router = APIRouter(prefix="/api/v1/duels", tags=["duels"])


# --- DTO ---


class DuellisteReponse(BaseModel):
    """Un duelliste résolu pour l'affichage : son archer et son nom (depuis le classement)."""

    archer_id: int
    nom: str
    prenom: str

    @staticmethod
    def de_duelliste(duelliste: Duelliste | None) -> DuellisteReponse | None:
        if duelliste is None:
            return None
        return DuellisteReponse(
            archer_id=duelliste.archer_id, nom=duelliste.nom, prenom=duelliste.prenom
        )


class MancheReponse(BaseModel):
    """Une manche (set) : son rang et les deux volées (codes de zone)."""

    numero: int
    haut: list[str]
    bas: list[str]


class BarrageReponse(BaseModel):
    """Le tir de barrage : une flèche par camp et le gagnant désigné (au plus près du centre)."""

    haut: str
    bas: str
    gagnant_designe: str | None


class ResultatReponse(BaseModel):
    """L'issue calculée : points de chaque camp, vainqueur (`haut`/`bas`), fin, barrage requis."""

    points_haut: int
    points_bas: int
    vainqueur: str | None
    termine: bool
    barrage_requis: bool


class DuelReponse(BaseModel):
    """L'état d'un match : câblage, occupants, pavé (mode/barème/zones), tir et résultat.

    `mode`, `nb_manches`, `nb_fleches_par_volee`, `points_pour_gagner` et `zones` **dimensionnent le
    pavé** de saisie du front (comme la grille + le barème de qualification, E04US002) : renseignés
    dès qu'un match est **jouable**, avant tout tir, `None`/vides pour un bye ou des occupants pas
    encore connus. `zones` vide sur un match jouable = blason indéterminable (pavé indisponible UI).
    """

    numero: int
    tour: int
    place_en_jeu: list[int] | None
    haut: DuellisteReponse | None
    bas: DuellisteReponse | None
    est_bye: bool
    mode: str | None
    nb_manches: int | None
    nb_fleches_par_volee: int | None
    points_pour_gagner: int | None
    zones: list[str]
    validee_par: str | None
    manches: list[MancheReponse]
    barrage: BarrageReponse | None
    resultat: ResultatReponse | None

    @staticmethod
    def de_etat(etat: EtatDuel) -> DuelReponse:
        duel = etat.duel
        bareme = etat.bareme
        manches: list[MancheReponse] = []
        barrage: BarrageReponse | None = None
        resultat: ResultatReponse | None = None
        # Le mode (sets/cumul) et les dimensions du pavé viennent du **barème du match**, résolu par
        # l'arme dès que le match est jouable : connus avant la première manche (au contraire de
        # `validee_par`/`manches`/`resultat`, qui n'existent qu'une fois un tir saisi).
        mode: str | None = None if bareme is None else bareme.mode.value
        validee_par: str | None = None
        if duel is not None:
            validee_par = duel.validee_par
            manches = [
                MancheReponse(
                    numero=manche.numero,
                    haut=[zone.value for zone in manche.volee_haut.valeurs],
                    bas=[zone.value for zone in manche.volee_bas.valeurs],
                )
                for manche in duel.manches
            ]
            if duel.barrage is not None:
                designe = duel.barrage.gagnant_designe
                barrage = BarrageReponse(
                    haut=duel.barrage.fleche_haut.value,
                    bas=duel.barrage.fleche_bas.value,
                    gagnant_designe=None if designe is None else designe.value,
                )
            issue = duel.resultat
            resultat = ResultatReponse(
                points_haut=issue.points_haut,
                points_bas=issue.points_bas,
                vainqueur=None if issue.vainqueur is None else issue.vainqueur.value,
                termine=issue.termine,
                barrage_requis=issue.barrage_requis,
            )
        return DuelReponse(
            numero=etat.numero,
            tour=etat.tour,
            place_en_jeu=None if etat.place_en_jeu is None else list(etat.place_en_jeu),
            haut=DuellisteReponse.de_duelliste(etat.haut),
            bas=DuellisteReponse.de_duelliste(etat.bas),
            est_bye=etat.est_bye,
            mode=mode,
            nb_manches=None if bareme is None else bareme.nb_manches,
            nb_fleches_par_volee=None if bareme is None else bareme.nb_fleches_par_volee,
            points_pour_gagner=None if bareme is None else bareme.points_pour_gagner,
            zones=[zone.value for zone in etat.zones],
            validee_par=validee_par,
            manches=manches,
            barrage=barrage,
            resultat=resultat,
        )


class PlaceReponse(BaseModel):
    """Une place de podium : le rang et le duelliste qui l'occupe."""

    rang: int
    duelliste: DuellisteReponse


class TableauReponse(BaseModel):
    """La photo du tableau reconstruit : dimensions, matchs (avec tirs) et podium acquis."""

    effectif: int
    taille: int
    nb_tours: int
    est_termine: bool
    duels: list[DuelReponse]
    podium: list[PlaceReponse]

    @staticmethod
    def de_etat(etat: EtatTableau) -> TableauReponse:
        return TableauReponse(
            effectif=etat.effectif,
            taille=etat.taille,
            nb_tours=etat.nb_tours,
            est_termine=etat.est_termine,
            duels=[DuelReponse.de_etat(d) for d in etat.duels],
            podium=[
                PlaceReponse(rang=rang, duelliste=reponse)
                for rang, duelliste in etat.podium
                if (reponse := DuellisteReponse.de_duelliste(duelliste)) is not None
            ],
        )


class SaisirMancheRequete(BaseModel):
    """Corps de la saisie d'une manche : le match, le rang de manche, les deux volées.

    `valeurs_*` sont des `ZoneScore` : Pydantic valide l'appartenance à l'énuméré (422 sur code
    inconnu), comme la saisie de qualification (E04US002) — cohérence de la frontière API.
    """

    tournoi_id: int
    phase_id: int
    match_numero: int
    numero: int
    valeurs_haut: list[ZoneScore]
    valeurs_bas: list[ZoneScore]
    identifiant_saisie: str | None = None


class SaisirBarrageRequete(BaseModel):
    """Corps du barrage : le match, une flèche par camp, le gagnant désigné (si flèches égales)."""

    tournoi_id: int
    phase_id: int
    match_numero: int
    fleche_haut: ZoneScore
    fleche_bas: ZoneScore
    gagnant_designe: Cote | None = None
    identifiant_saisie: str | None = None


class ValiderDuelRequete(BaseModel):
    """Corps de la validation d'un duel : le match à sceller au nom du scoreur."""

    tournoi_id: int
    phase_id: int
    match_numero: int
    identifiant_saisie: str | None = None


def _exiger_meme_tournoi(scoreur: Scoreur, tournoi_id: int) -> None:
    """Refuse (`403 scoreur_hors_tournoi`) un scoreur agissant hors de **son** tournoi."""
    if scoreur.tournoi_id != tournoi_id:
        raise ScoreurHorsTournoi("Ce scoreur n'officie pas dans ce tournoi.")


def _cle_idempotence(operation: str, identifiant: str | None, *portee: int) -> str | None:
    """Clé d'idempotence **scopée** (opération + cible), ou `None` sans identifiant (ADR-0036)."""
    if not identifiant:
        return None
    return ":".join((operation, identifiant, *(str(p) for p in portee)))


# --- Lecture ---


@router.get("/tableau/{tournoi_id}/{phase_id}", response_model=TableauReponse)
async def lire_tableau(
    tournoi_id: int,
    phase_id: int,
    request: Request,
    scoreur: Annotated[Scoreur, Depends(exiger_scoreur)],
) -> TableauReponse:
    """Le tableau reconstruit d'une phase (matchs, tirs, podium). Scoreur, dans son tournoi."""
    service: ServiceSaisieDuels = request.app.state.service_saisie_duels
    _exiger_meme_tournoi(scoreur, tournoi_id)
    etat = await run_in_threadpool(service.etat_tableau, tournoi_id, phase_id)
    return TableauReponse.de_etat(etat)


@router.get("/duels/{tournoi_id}/{phase_id}/{match_numero}", response_model=DuelReponse)
async def lire_duel(
    tournoi_id: int,
    phase_id: int,
    match_numero: int,
    request: Request,
    scoreur: Annotated[Scoreur, Depends(exiger_scoreur)],
) -> DuelReponse:
    """L'état d'un match précis. `422 match_introuvable` si le rang n'existe pas. Scoreur."""
    service: ServiceSaisieDuels = request.app.state.service_saisie_duels
    _exiger_meme_tournoi(scoreur, tournoi_id)
    etat = await run_in_threadpool(service.etat_duel, tournoi_id, phase_id, match_numero)
    return DuelReponse.de_etat(etat)


# --- Écritures (via la file) ---


@router.post("/manches", response_model=DuelReponse)
async def saisir_manche(
    requete: SaisirMancheRequete,
    request: Request,
    scoreur: Annotated[Scoreur, Depends(exiger_scoreur)],
) -> DuelReponse:
    """Saisit (ou réédite) une manche d'un duel. Scoreur ; via la **file**, dédoublonnée."""
    service: ServiceSaisieDuels = request.app.state.service_saisie_duels
    write_queue: WriteQueue = request.app.state.write_queue
    registre: RegistreIdempotence = request.app.state.registre_idempotence
    _exiger_meme_tournoi(scoreur, requete.tournoi_id)
    valeurs_haut = tuple(requete.valeurs_haut)
    valeurs_bas = tuple(requete.valeurs_bas)
    cle = _cle_idempotence(
        "manche",
        requete.identifiant_saisie,
        requete.tournoi_id,
        requete.phase_id,
        requete.match_numero,
        requete.numero,
    )

    def ecrire() -> EtatDuel:
        return service.saisir_manche(
            requete.tournoi_id,
            requete.phase_id,
            requete.match_numero,
            requete.numero,
            valeurs_haut,
            valeurs_bas,
        )

    etat = await asyncio.wrap_future(write_queue.submit(lambda: registre.executer(cle, ecrire)))
    return DuelReponse.de_etat(etat)


@router.post("/barrages", response_model=DuelReponse)
async def saisir_barrage(
    requete: SaisirBarrageRequete,
    request: Request,
    scoreur: Annotated[Scoreur, Depends(exiger_scoreur)],
) -> DuelReponse:
    """Saisit le tir de barrage d'un duel à égalité (§8.2). Scoreur ; via la **file**."""
    service: ServiceSaisieDuels = request.app.state.service_saisie_duels
    write_queue: WriteQueue = request.app.state.write_queue
    registre: RegistreIdempotence = request.app.state.registre_idempotence
    _exiger_meme_tournoi(scoreur, requete.tournoi_id)
    fleche_haut = requete.fleche_haut
    fleche_bas = requete.fleche_bas
    designe = requete.gagnant_designe
    cle = _cle_idempotence(
        "barrage",
        requete.identifiant_saisie,
        requete.tournoi_id,
        requete.phase_id,
        requete.match_numero,
    )

    def ecrire() -> EtatDuel:
        return service.saisir_barrage(
            requete.tournoi_id,
            requete.phase_id,
            requete.match_numero,
            fleche_haut,
            fleche_bas,
            designe,
        )

    etat = await asyncio.wrap_future(write_queue.submit(lambda: registre.executer(cle, ecrire)))
    return DuelReponse.de_etat(etat)


@router.post("/validations", response_model=DuelReponse)
async def valider_duel(
    requete: ValiderDuelRequete,
    request: Request,
    scoreur: Annotated[Scoreur, Depends(exiger_scoreur)],
) -> DuelReponse:
    """Valide un duel **tranché** au nom du scoreur : son vainqueur avancera le tableau (E05US005).

    Scoreur borné à **son** tournoi (`403` sinon). `422 duel_incomplet` si le vainqueur n'est pas
    connu. Via la **file**, dédoublonnée par identifiant (ADR-0036). Renvoie l'état du duel.
    """
    service: ServiceSaisieDuels = request.app.state.service_saisie_duels
    write_queue: WriteQueue = request.app.state.write_queue
    registre: RegistreIdempotence = request.app.state.registre_idempotence
    _exiger_meme_tournoi(scoreur, requete.tournoi_id)
    cle = _cle_idempotence(
        "validation_duel",
        requete.identifiant_saisie,
        requete.tournoi_id,
        requete.phase_id,
        requete.match_numero,
    )

    def ecrire() -> EtatDuel:
        return service.valider(
            requete.tournoi_id, requete.phase_id, requete.match_numero, scoreur.nom
        )

    etat = await asyncio.wrap_future(write_queue.submit(lambda: registre.executer(cle, ecrire)))
    return DuelReponse.de_etat(etat)
