"""Endpoint REST des **jalons « prêt à… »** (E16US012).

`GET /api/v1/tournois/{tournoi_id}/jalons/{jalon}` (**admin**) : « puis-je passer à l'étape
suivante, et sinon qu'est-ce qui manque ? ». Une **route unique paramétrée par le membre**, image
directe de la forme unique décidée au domaine — quatre routes jumelles auraient rouvert côté API
la divergence que l'US ferme (ADR-0096).

Lecture ; le front la **poll** comme la complétude et la supervision. DTO Pydantic distincts des
value objects du domaine (règle 6). Erreurs typées traduites à la frontière (`api/erreurs.py`) :
tournoi inconnu **et** membre pas encore instruit → 404.

⚠️ `LigneCompletudeReponse` est **réutilisée** depuis `api.v1.completude` et non recopiée : c'est
littéralement la même ligne (`domain.completude.LigneCompletude`), et le jalon *terminer* rend
exactement les lignes que l'écran de complétude rendait déjà. Une 2ᵉ écriture du même DTO aurait
fait diverger deux contrats que le front consomme avec le **même** composant — c'est le motif de
`DETTE-065`, qu'on ne va pas alimenter en le sachant.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from api.v1.completude import LigneCompletudeReponse
from application.jalons import ServiceJalons
from domain.jalon import Jalon, PreparationJalon, question

router = APIRouter(prefix="/api/v1/tournois/{tournoi_id}", tags=["jalons"])


class PreparationJalonReponse(BaseModel):
    """La réponse d'un jalon : la question posée, ce qui manque, et si l'action passera.

    - `question` : « Prêt à démarrer ? » — **dérivée** du jalon, pour que le front n'ait pas à
      tenir sa propre table de libellés (elle divergerait au premier membre ajouté) ;
    - `lignes` : ce qui manque, en états (`D-17`) — jamais un pourcentage. ⚠️ **Une liste vide ne
      veut pas dire « rien ne manque »** : elle veut dire *il n'y a plus rien à préparer* — la
      transition n'est plus offerte **depuis le statut courant** — tournoi déjà lancé, annulé ou
      archivé. Elle s'accompagne alors de `pret: false`, `bloquant: true`, et c'est
      `detail` qui dit pourquoi. Un client qui la lirait « tout est bon » commettrait exactement le
      contresens que cette US existe pour supprimer ; c'est sur cette convention que le front se
      dispense de connaître le statut.

      ⚠️ **Cela vaut pour *démarrer*, pas pour *terminer*** — asymétrie assumée. Chez *démarrer*, la
      liste **est** la préparation : plus rien à préparer, plus rien à lister. Chez *terminer*, elle
      **est l'état sportif**, qui existe à tout statut : ce membre rend donc toujours ses lignes, et
      c'est **`question_posee`** (ci-dessous) qui dit que la question ne se pose plus, accompagné de
      `bloquant` et `detail`. Un client
      qui viderait cet écran hors *en cours* retirerait ce que l'organisateur vient y chercher
      pendant la pause ;
    - `pret` : la réponse binaire ;
    - `question_posee` : la question a-t-elle encore un objet depuis le statut courant ? À `false`,
      l'écran ne rend **pas** de verdict et se contente de `detail`. ⚠️ **Ne le déduisez pas de
      `lignes`** : c'était vrai tant que les deux membres vidaient leur liste, ça ne l'est plus —
      *terminer* rend la sienne à tout statut (voir ci-dessus). C'est le seul champ qui porte cette
      information, et il est là pour que les membres suivants n'aient pas à la deviner ;
    - `bloquant` : à `false`, l'action passe **quand même** malgré `pret: false` (`D-15`) ;
    - `detail` : la **cause chiffrée** du blocage quand il y en a une (« 8 archer(s) inscrit(s) sur
      le départ 2 pour 34 requis… »), `null` sinon. C'est la phrase que la garde met dans son
      refus : l'avertissement et le refus ne peuvent donc pas énoncer deux causes différentes.
      ⚠️ **Une exception, assumée** : la garde de **statut de *démarrer***, où le jalon rédige une
      explication propre à chaque statut terminal (« annulé », « archivé », « déjà lancé »), quand
      le refus serveur, lui, n'en distingue aucun (« Seul un tournoi prêt peut être démarré. ») ;
    - `moment` : **quand** tombera le *premier* refus (« au démarrage », « dès le passage en
      « prêt » »). Les gardes d'un même jalon ne tombent pas toutes au même clic — les créneaux dès
      « Marquer prêt », l'effectif au démarrage — et c'est celle qui bloque en premier qui
      commande.
      ⚠️ `null` veut dire **deux** choses : il n'y a rien à refuser (`bloquant: false` ou `pret:
      true`), **ou** la transition n'est plus offerte du tout — le refus existe alors
      (`bloquant: true`) mais ne tombe à aucun clic, l'action n'étant plus proposée. `moment` ne se
      lit donc jamais seul : toujours avec `bloquant` et `question_posee`.

    ⚠️ `bloquant` ne sert **pas** à désactiver un bouton : il choisit ce que l'écran annonce (un
    refus à venir, ou une simple gêne). E05US021 avait déjà tranché — le refus remonte du serveur,
    le front ne décide d'aucune garde.
    """

    jalon: str
    question: str
    lignes: list[LigneCompletudeReponse]
    pret: bool
    bloquant: bool
    question_posee: bool
    detail: str | None
    moment: str | None

    @staticmethod
    def de_preparation(preparation: PreparationJalon) -> PreparationJalonReponse:
        """Traduit la préparation du domaine en DTO de réponse."""
        return PreparationJalonReponse(
            jalon=preparation.jalon.value,
            question=question(preparation.jalon),
            lignes=[LigneCompletudeReponse.de_ligne(ligne) for ligne in preparation.lignes],
            pret=preparation.pret,
            bloquant=preparation.bloquant,
            question_posee=preparation.question_posee,
            detail=preparation.detail,
            moment=preparation.moment,
        )


@router.get(
    "/jalons/{jalon}",
    response_model=PreparationJalonReponse,
    dependencies=[Depends(exiger_admin)],
)
async def preparation_jalon(
    tournoi_id: int, jalon: Jalon, request: Request
) -> PreparationJalonReponse:
    """Préparation d'un tournoi à un jalon (**admin**).

    `404` si le tournoi n'existe pas **ou** si le membre n'a pas encore d'écran (`archiver`,
    `exporter`). `400` si le segment n'est pas un membre de la famille : l'énumération du domaine
    sert de validation de chemin, et le projet remappe `RequestValidationError` en 400
    (`api/erreurs.py`).

    ⚠️ **`Jalon` (domaine) sert de type de chemin, et c'est délibéré** — la revue a proposé de le
    recopier à la frontière au nom de la règle 6. Écarté : la règle vise les **DTO de corps**, dont
    la structure ne doit pas fuir (c'est fait, `PreparationJalonReponse` est distinct), tandis que
    dupliquer ici la liste des quatre membres rouvrirait exactement la divergence que l'US ferme —
    un membre ajouté au domaine et oublié dans la copie deviendrait un 400 silencieux. Le risque
    inverse (renommer un membre du domaine casse l'URL sans rien faire rougir) est couvert : les
    tests d'API demandent les segments **littéraux** `demarrer` / `terminer` / `archiver`.

    Lecture pure (départs, déroulé, séries, plan en base) : hors file d'écriture, dans le
    threadpool.
    """
    service: ServiceJalons = request.app.state.service_jalons
    preparation = await run_in_threadpool(service.preparation, tournoi_id, jalon)
    return PreparationJalonReponse.de_preparation(preparation)
