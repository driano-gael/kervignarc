"""Endpoints REST du **panneau de routage** (E04US018) — « où est-ce que je tire ensuite ? ».

Expose `ServiceRoutage` aux deux surfaces de saisie : la tablette de **qualification** (E04US002),
qui route ses archers A→D vers leur duel de 1ᵉʳ tour une fois les séries validées, et l'écran
**scoreur de duels** (E04US013), qui route les deux duellistes dès le duel tranché. Une seule route
sert les deux : c'est la même question, seul l'ensemble d'archers change.

**Lecture publique, sans authentification** — comme le déroulé (E07US009, ADR-0039) et conformément
au contrat d'E10US001 (toute lecture répond sans jeton). C'est cohérent avec la destination de cette
projection : les trois autres canaux de routage (`D-09`) sont l'appli publique (E07US008) et l'écran
de salle (E07US004). Rien ici n'est confidentiel — la cible d'un match est affichée en salle.

Aucune erreur métier propre : un archer qu'on ne sait pas router rend une ligne **motivée**
(`indisponible`), jamais un 4xx — un panneau qui échoue en bloc parce qu'un archer sur quatre n'est
pas au tableau serait inutilisable le jour J. Les gardes de phase (`PhaseIntrouvable` /
`PhasePasUnTableau`) ne remontent que si le client **impose** un `phase_id`, comme partout ailleurs.

DTO Pydantic distincts des dataclasses d'application (règle 6) ; on réutilise `DuellisteReponse` de
la saisie de duels — l'adversaire s'affiche avec les mêmes noms que la grille du scoreur.
"""

from __future__ import annotations

from typing import Annotated, Literal, cast

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.v1.saisie_duels import DuellisteReponse
from application.routage import (
    DestinationRepechage,
    ProchainDuel,
    ProchaineManche,
    Routage,
    RoutageArcher,
    ServiceRoutage,
)
from domain.phase import TypePhase

router = APIRouter(prefix="/api/v1/routage", tags=["routage"])

IssueRoutageReponse = Literal[
    "prochain_duel", "prochaine_manche", "termine", "repeche", "en_attente", "indisponible"
]
"""Les seules issues du panneau — publiées au schéma OpenAPI plutôt que laissées en `str`,
pour que le client (qui les code en dur) voie une divergence d'énumération au lieu de la subir.
Miroir fermé de `IssueRoutage`, sans exposer l'énumération d'application (règle 6).

`repeche` est ajouté par E07US008 : **élargissement**, pas rupture — un client qui ne le connaît
pas ne peut pas le rencontrer sur un tournoi sans repêchage, et le test miroir garantit qu'aucune
valeur du domaine ne circule sans être déclarée ici.

`en_attente` est ajouté par E05US030, et **c'est un rétrécissement d'`indisponible`, pas seulement
un élargissement** : `E05US026` servait cette valeur-ci sous `indisponible` avec un motif, faute de
pouvoir toucher au contrat depuis une US backend seule. Un client resté à l'ancienne union verra
donc une valeur inconnue là où il lisait « on ne sait pas ».

⚠️ **Ce que les garde-fous couvrent, exactement** (précisé en revue, la première rédaction
promettait plus) : le test miroir (`test_issue_reponse_est_le_miroir_de_l_enumeration`) garde la
cohérence **entre l'énumération d'application et ce DTO**, rien d'autre ; le `Record` exhaustif du
front (`features/routage/presentation.ts`, `EN_LICE`) ne fait échouer la compilation qu'**une fois
l'union TypeScript élargie** — il est indexé par le type du front, pas par celui du serveur. Une
issue ajoutée **côté serveur seul** ne rougit donc nulle part : elle rendrait `EN_LICE[inconnue]`
→ `undefined` → falsy, et l'archer partirait chez les sortis. Les deux côtés se livrent ensemble,
c'est ce qui rend le rétrécissement sûr — pas un mécanisme."""


# --- DTO ---


class ProchaineMancheReponse(BaseModel):
    """Le prochain rendez-vous d'un finaliste de **Big Shoot Off** (E05US028).

    ⚠️ **Un DTO distinct de `ProchainDuelReponse`, et non son élargissement.** Un Big Shoot Off
    n'oppose personne : tous les finalistes sont sur la ligne, et c'est le classement de la manche
    qui élimine. Réutiliser le DTO de duel aurait publié au schéma un `adversaire` toujours `null`
    et un `numero` de match qui n'existe pas — le genre de nom trop étroit qu'ADR-0083 a dû
    corriger côté domaine.

    `elimine` dit combien d'archers sortiront à l'issue de ce tour : c'est l'information qui compte
    pour le tireur, davantage que le numéro de la manche.

    `cible`/`position` sont **toujours `null` aujourd'hui**, et `manque` le dit en clair : le
    routage ne lit pas le plan du créneau pour cette phase (`DETTE-059`). Nommer le manque plutôt
    que le taire est la règle `P-3` — un panneau muet se prend pour une panne réseau.
    """

    numero: int
    elimine: int
    cible: int | None
    position: str | None
    manque: str | None

    @staticmethod
    def de_manche(manche: ProchaineManche) -> ProchaineMancheReponse:
        return ProchaineMancheReponse(
            numero=manche.numero,
            elimine=manche.elimine,
            cible=manche.cible,
            position=manche.position,
            manque=manche.manque,
        )


class ProchainDuelReponse(BaseModel):
    """Le prochain rendez-vous d'un archer : où, quand dans l'arbre, contre qui.

    `cible`/`position` sont `null` au-delà du tour 1 (placement intégral = E05US010) et `manque` dit
    alors pourquoi. `alerte` est l'inverse : la cible **est** là, mais quelque chose cloche (le duel
    n'est pas côte à côte). Les deux ne se remplacent pas : l'un dit « je n'ai pas », l'autre
    « j'ai, mais méfiance ». Pas de champ « heure » : aucun horaire n'existe par tour de tableau —
    c'est le lancement du tour (E12US002) qui fait partir les duels.
    """

    numero: int
    tour: int
    libelle: str
    cible: int | None
    position: str | None
    adversaire: DuellisteReponse | None
    sources_en_attente: list[int]
    manque: str | None
    alerte: str | None

    @staticmethod
    def de_prochain(prochain: ProchainDuel) -> ProchainDuelReponse:
        return ProchainDuelReponse(
            numero=prochain.numero,
            tour=prochain.tour,
            libelle=prochain.libelle,
            cible=prochain.cible,
            position=prochain.position,
            adversaire=DuellisteReponse.de_duelliste(prochain.adversaire),
            sources_en_attente=list(prochain.sources_en_attente),
            manque=prochain.manque,
            alerte=prochain.alerte,
        )


class DestinationRepechageReponse(BaseModel):
    """La phase qui **reprend** un repêché (E07US008) : son id, son rang de séquence, son type.

    Pas de libellé tout fait : le front sait déjà nommer un type de phase (`LIBELLE_TYPE`), et une
    phase n'a pas de nom propre dans le modèle. Envoyer « 3. Élimination directe » depuis le serveur
    dupliquerait ce vocabulaire à un deuxième endroit, où il finirait par diverger.

    `type` est déclaré sur l'**énumération** `TypePhase`, comme dans `api/v1/phases.py` et
    `api/v1/formats.py` (correctif de revue, axe A) : un `str` ouvert publiait une chaîne libre au
    schéma OpenAPI. L'énumération fermée y rend une divergence **visible** au client au lieu de la
    lui faire subir, exactement comme `IssueRoutageReponse` ci-dessus. La sérialisation JSON est
    **inchangée** (`TypePhase` est un `str, Enum` : Pydantic rend `"elimination_directe"`), donc le
    client existant ne voit aucune différence.

    ⚠️ Le miroir TS reste volontairement `type: string`, et ce n'est pas un oubli (précision de
    revue) : le front doit pouvoir nommer un type qu'un serveur **plus récent** lui enverrait, et le
    durcir rendrait mort le repli de `nommerType` — c'est ce repli, pas cette déclaration, qui a
    supprimé le cast côté client.
    """

    phase_id: int
    ordre: int
    type: TypePhase

    @staticmethod
    def de_destination(destination: DestinationRepechage) -> DestinationRepechageReponse:
        return DestinationRepechageReponse(
            phase_id=destination.phase_id,
            ordre=destination.ordre,
            type=destination.type,
        )


class RoutageArcherReponse(BaseModel):
    """La ligne d'un archer : son issue et le détail qui va avec.

    `issue` est fermée (`IssueRoutageReponse`), et chacune de ses valeurs dit quel champ lire
    ensuite : `prochain` pour `prochain_duel`, `prochaine_manche` pour `prochaine_manche`,
    `rang_final`/`rang_min`/`rang_max` pour `termine`, `destination` pour `repeche`, `motif` pour
    `en_attente` et pour `indisponible`.

    ⚠️ **`en_attente` et `indisponible` ne se disent pas de la même façon** malgré le champ commun :
    le premier veut dire « il est dans la phase, en course, mais rien n'est apparié pour lui à cet
    instant » — il **compte parmi les tireurs encore en lice** ; le second, « on ne sait pas le
    router ». Les confondre a été le défaut d'E05US026, corrigé en E05US030.

    **Trois champs de rang, et ils ne se répètent pas** (E07US008) : `rang_final` est le rang
    **exact** quand un match terminal l'a décerné ; `rang_min`/`rang_max` la **fourchette acquise**,
    qui vaut aussi dans un tableau tronqué au podium (le battu d'un quart est 5ᵉ-8ᵉ *ex æquo*).
    Quand le rang exact existe, la fourchette s'y referme. Un client qui n'affiche que `rang_final`
    continue de fonctionner : il perd l'*ex æquo*, il ne lit rien de faux.
    """

    archer_id: int
    nom: str
    prenom: str
    issue: IssueRoutageReponse
    prochain: ProchainDuelReponse | None
    rang_final: int | None
    rang_min: int | None
    rang_max: int | None
    tour_sortie: str | None
    destination: DestinationRepechageReponse | None
    motif: str | None
    prochaine_manche: ProchaineMancheReponse | None = None
    """Le rendez-vous d'un finaliste de Big Shoot Off (E05US028), quand `issue` vaut
    `prochaine_manche`. **Exclusif de `prochain`** : un archer n'a jamais les deux, et son issue
    dit lequel lire. Champ **ajouté** avec un défaut, donc un client d'avant E05US028 ne casse
    pas — il ne peut simplement pas rencontrer cette issue sur un tournoi sans Big Shoot Off."""

    @staticmethod
    def de_archer(ligne: RoutageArcher) -> RoutageArcherReponse:
        return RoutageArcherReponse(
            archer_id=ligne.archer_id,
            nom=ligne.nom,
            prenom=ligne.prenom,
            issue=cast(IssueRoutageReponse, ligne.issue.value),
            prochain=(
                ProchainDuelReponse.de_prochain(ligne.prochain)
                if ligne.prochain is not None
                else None
            ),
            rang_final=ligne.rang_final,
            rang_min=ligne.rang_min,
            rang_max=ligne.rang_max,
            tour_sortie=ligne.tour_sortie,
            destination=(
                DestinationRepechageReponse.de_destination(ligne.destination)
                if ligne.destination is not None
                else None
            ),
            motif=ligne.motif,
            prochaine_manche=(
                ProchaineMancheReponse.de_manche(ligne.prochaine_manche)
                if ligne.prochaine_manche is not None
                else None
            ),
        )


class RoutageReponse(BaseModel):
    """La réponse du panneau : la phase de tableau visée et une ligne par archer.

    `phase_id` à `null` signifie **« aucune phase d'élimination configurée »** — à distinguer d'une
    liste vide, qui dirait « le tableau ne route personne ». C'est la seule chose qui permette à
    l'écran de salle de dire « on n'en est pas là » au lieu d'afficher un pas de tir désert.
    """

    phase_id: int | None
    archers: list[RoutageArcherReponse]

    @staticmethod
    def de_routage(routage: Routage) -> RoutageReponse:
        return RoutageReponse(
            phase_id=routage.phase_id,
            archers=[RoutageArcherReponse.de_archer(ligne) for ligne in routage.archers],
        )


_MAX_ARCHERS = 64
"""Plafond du nombre d'archers routés en un appel — au-delà, **400** avant que le service tourne.

(400 et non 422 : ce projet mappe `RequestValidationError` sur 400, le 422 étant réservé aux
`DomainError` — cf. la table de `api/erreurs.py`.)

Les deux appelants réels en demandent 4 (une cible) et 2 (un duel) ; 64 laisse une marge
confortable. La borne est **secondaire** dans la défense : le coût dominant d'un appel est la
reconstruction de l'arbre, payée **une fois par requête** quel que soit le nombre d'identifiants, et
elle n'est bornée par rien. Ce plafond ne ferme donc que l'amplification requête→réponse (le
régime
de DETTE-008) sur une route **publique et non authentifiée** ; à ne pas lire comme une protection
générale contre la charge."""


# --- Lecture ---


@router.get("/departs/{depart_id}", response_model=RoutageReponse)
async def lire_routage(
    depart_id: int,
    request: Request,
    archer_id: Annotated[
        list[int] | None,
        Query(
            max_length=_MAX_ARCHERS,
            description="Archers à router, dans l'ordre d'affichage",
        ),
    ] = None,
    phase_id: Annotated[int | None, Query(description="Phase de tableau visée")] = None,
) -> RoutageReponse:
    """Où tirent ensuite ces archers. Lecture pure (`D-08`), hors boucle événementielle.

    `phase_id` omis ⇒ le service vise le **tableau qui vient** — la première élimination directe
    non terminée, sinon la dernière : la tablette de qualification ne connaît que sa cible et son
    départ.
    Fourni, il est **validé** (404 s'il est inconnu ou relève d'un autre tournoi). L'ordre des
    `archer_id` est **conservé** dans la réponse — le panneau affiche A, B, C, D dans l'ordre de la
    grille.
    """
    service: ServiceRoutage = request.app.state.service_routage
    routage = await run_in_threadpool(service.routage, depart_id, tuple(archer_id or ()), phase_id)
    return RoutageReponse.de_routage(routage)


@router.get("/departs/{depart_id}/affectations", response_model=RoutageReponse)
async def lire_affectations(
    depart_id: int,
    request: Request,
    phase_id: Annotated[int | None, Query(description="Phase de tableau visée")] = None,
) -> RoutageReponse:
    """**Toutes** les affectations du tableau, dans l'ordre du pas de tir (E07US008).

    Même projection et **même DTO** que la route précédente : les quatre canaux de routage doivent
    dire la même chose, et deux formes de réponse finiraient par diverger sur la butte annoncée.
    Seule l'entrée change — ici, aucun `archer_id` : ni l'écran de salle ni la table de
    l'organisation ne connaissent la liste, et la leur faire reconstituer serait leur faire
    connaître le tableau.

    **Pas de plafond `_MAX_ARCHERS` ici, et ce n'est pas un oubli.** Ce plafond bornait
    l'amplification requête→réponse (le régime de `DETTE-008`) : un client pouvait demander 64
    lignes pour un coût de reconstruction déjà payé. Ici le client ne demande rien — la taille de la
    réponse est celle du tableau, donc bornée par les inscrits du tournoi, pas par la requête.

    Le coût dominant reste la **reconstruction de l'arbre**, payée une fois par appel, sur une route
    publique non authentifiée : c'est le régime de **`# DETTE-031`**, que cette US **aggrave** et
    dont elle élargit la ligne au registre (correctif de revue — trois axes ont relevé que ces
    textes citaient `DETTE-008`, qui traite de tout autre chose : l'écho non borné de l'entrée
    client dans une réponse 400).
    """
    service: ServiceRoutage = request.app.state.service_routage
    routage = await run_in_threadpool(service.affectations, depart_id, phase_id)
    return RoutageReponse.de_routage(routage)
