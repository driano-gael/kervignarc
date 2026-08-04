"""Endpoint REST **public** des tableaux d'un tournoi (E07US005) — « voir les arbres en direct ».

Expose `ServiceTableauxPublics` à l'appli publique et à l'écran de salle. **Aucune
authentification** : c'est le régime de toutes les vues publiques (E07US001) et la condition pour
qu'un écran de salle, qui n'a pas de session admin, puisse afficher un tableau.

⚠️ **C'est ici que vit la restriction de contenu (règle 6), et c'est tout l'enjeu du fichier.**
Le tableau du **scoreur** (`api/v1/duels.py`, `exiger_scoreur`) rend le même `EtatTableau` avec
tout ce qu'il faut pour saisir : chaque flèche de chaque manche, le barrage, les zones du blason,
le barème du pavé, et le **nom du scoreur qui a validé**. Rien de tout cela n'a de raison d'être
public. Le DTO ci-dessous garde ce qu'un spectateur vient lire — qui rencontre qui, où en est le
match, qui a gagné — et **rien d'autre** :

- pas de `validee_par` (identité d'un bénévole), remplacé par un booléen `validee` : le public a
  besoin de savoir si un résultat est **acquis** ou encore en attente, jamais de savoir par qui ;
- pas de `manches` ni de `barrage` : le détail flèche à flèche est une donnée de saisie. Ce que le
  public lit d'un duel, c'est son **score de sets** (`points_haut`/`points_bas`) ;
- pas de `bareme` ni de `zones` : ils dimensionnent le pavé de saisie, ils n'ont pas de lecteur ici.

Un DTO **distinct** et non un `exclude` sur celui du scoreur : un champ ajouté au DTO du scoreur
n'apparaît pas ici par défaut, alors qu'une liste d'exclusions aurait laissé passer le suivant.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from application.saisie_duels import Duelliste, EtatDuel
from application.tableaux_publics import ServiceTableauxPublics, TableauPublic

router = APIRouter(prefix="/api/v1/tableaux", tags=["tableaux"])


# --- DTO ---


class DuellisteReponse(BaseModel):
    """Un duelliste, réduit à ce qui s'affiche sur un arbre : son identité sportive.

    `archer_id` est conservé — il n'a rien de confidentiel (le classement public le porte déjà) et
    c'est lui qui permet à la vue « mon chemin » de reconnaître un archer suivi sans faire
    correspondre des noms, comparaison qui casse au premier homonyme.
    """

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


class DuelPublicReponse(BaseModel):
    """Un match de l'arbre, vu du public.

    `place_en_jeu` est ce qui distingue la finale (`[1, 2]`) d'un match de placement (`[5, 8]`) :
    c'est lui qui permet de nommer l'enjeu sans le déduire du numéro de tour, déduction fausse dès
    qu'un tableau descend sous le podium (E06US006).

    `termine` et `validee` disent deux choses différentes, et les confondre afficherait un
    vainqueur qui n'en est pas encore un : `termine` = le tir est allé au bout ; `validee` = le
    scoreur a scellé, et c'est **seulement** à partir de là que l'arbre avance. Le public voit donc
    « en attente de validation » entre les deux — le même vocabulaire qu'E07US009.
    """

    numero: int
    tour: int
    place_en_jeu: list[int] | None
    haut: DuellisteReponse | None
    bas: DuellisteReponse | None
    est_bye: bool
    points_haut: int | None
    points_bas: int | None
    vainqueur: str | None
    termine: bool
    validee: bool

    @staticmethod
    def de_etat(etat: EtatDuel) -> DuelPublicReponse:
        duel = etat.duel
        issue = None if duel is None else duel.resultat
        return DuelPublicReponse(
            numero=etat.numero,
            tour=etat.tour,
            place_en_jeu=None if etat.place_en_jeu is None else list(etat.place_en_jeu),
            haut=DuellisteReponse.de_duelliste(etat.haut),
            bas=DuellisteReponse.de_duelliste(etat.bas),
            est_bye=etat.est_bye,
            points_haut=None if issue is None else issue.points_haut,
            points_bas=None if issue is None else issue.points_bas,
            vainqueur=None if issue is None or issue.vainqueur is None else issue.vainqueur.value,
            termine=False if issue is None else issue.termine,
            validee=False if duel is None else duel.verrouille,
        )


class PlaceReponse(BaseModel):
    """Une place acquise du classement de la phase : le rang et qui l'occupe."""

    rang: int
    duelliste: DuellisteReponse


class TableauPublicReponse(BaseModel):
    """Un arbre du tournoi : de quelle phase il relève, ses dimensions, ses matchs, son podium.

    `ordre` et `type` plutôt qu'un libellé tout fait : le front tient déjà le catalogue des types
    (`shared/phases/catalogue.ts`) et le traduit une fois pour toutes (règle 3).
    """

    phase_id: int
    ordre: int
    type: str
    effectif: int
    taille: int
    nb_tours: int
    est_termine: bool
    duels: list[DuelPublicReponse]
    podium: list[PlaceReponse]

    @staticmethod
    def de_tableau(tableau: TableauPublic) -> TableauPublicReponse:
        etat = tableau.etat
        return TableauPublicReponse(
            phase_id=tableau.phase_id,
            ordre=tableau.ordre,
            type=tableau.type.value,
            effectif=etat.effectif,
            taille=etat.taille,
            nb_tours=etat.nb_tours,
            est_termine=etat.est_termine,
            duels=[DuelPublicReponse.de_etat(duel) for duel in etat.duels],
            podium=[
                PlaceReponse(rang=rang, duelliste=reponse)
                for rang, duelliste in etat.podium
                if (reponse := DuellisteReponse.de_duelliste(duelliste)) is not None
            ],
        )


class TableauxReponse(BaseModel):
    """Tous les arbres lisibles du tournoi, dans l'ordre du déroulé."""

    tournoi_id: int
    tableaux: list[TableauPublicReponse]


# --- Lecture ---


@router.get("/{tournoi_id}", response_model=TableauxReponse)
async def lire_tableaux(tournoi_id: int, request: Request) -> TableauxReponse:
    """Les arbres du tournoi, lecture publique. `404` si le tournoi n'existe pas.

    Lecture **synchrone hors boucle événementielle** (règle 7) : la reconstruction est du calcul
    pur mais lourd, elle n'a rien à faire dans l'`event loop` d'un serveur qui sert aussi des
    WebSockets.

    Aucun plafond, comme `/routage/{id}/affectations` et pour la même raison : le client ne demande
    rien, la taille de la réponse est celle des tableaux du tournoi. Le coût dominant reste la
    **reconstruction**, payée une fois par phase et par appel — c'est le régime de `# DETTE-031`,
    que cette US élargit (une route publique de plus, et une surface de polling par spectateur).
    """
    service: ServiceTableauxPublics = request.app.state.service_tableaux_publics
    tableaux = await run_in_threadpool(service.pour_tournoi, tournoi_id)
    return TableauxReponse(
        tournoi_id=tableaux.tournoi_id,
        tableaux=[TableauPublicReponse.de_tableau(t) for t in tableaux.tableaux],
    )
