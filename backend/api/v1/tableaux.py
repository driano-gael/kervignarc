"""Tableaux **publics** — c'est ici que vit la restriction de contenu (règle 6).

Le public lit qui rencontre qui, où en est le match, qui a gagné. Pas `validee_par` (l'identité d'un
bénévole), pas les manches ni le barrage (donnée de saisie), pas le barème ni les zones.

⚠️ **Un DTO DISTINCT, jamais un `exclude` sur celui du scoreur** : un champ ajouté au DTO du scoreur
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
    def de_connu(duelliste: Duelliste) -> DuellisteReponse:
        """Projection d'un duelliste **certain** (podium). Domicile unique de la conversion."""
        return DuellisteReponse(
            archer_id=duelliste.archer_id, nom=duelliste.nom, prenom=duelliste.prenom
        )

    @staticmethod
    def de_duelliste(duelliste: Duelliste | None) -> DuellisteReponse | None:
        """Projection d'un camp qui peut être **vide** (adversaire pas encore sorti de son duel)."""
        return None if duelliste is None else DuellisteReponse.de_connu(duelliste)


class DuelPublicReponse(BaseModel):
    """Un match de l'arbre, vu du public.

    ⚠️ **`libelle` vient du domaine, il n'est pas recalculé côté client.** Nommer un match est du
    **vocabulaire métier** (règle 3) : `domain.tableau.libelle_tour` en est le domicile, et le
    servir ici évite d'en ouvrir un troisième (`DETTE-020` en compte déjà deux). Un premier jet de
    cette US le recalculait en TypeScript et produisait **« Demi-finales » sur un match des places
    5-8** — le mot faux, sur la vue publique, au moment où le tournoi descend sous le podium.

    `place_en_jeu` ne dit **pas** tout, et c'est la leçon de cette US : il n'existe que sur les
    matchs **terminaux**. `plage` est la **branche** (`[5, 8]` pour le sous-tableau de placement),
    disponible dès le premier tour — c'est elle qui permet de grouper l'affichage par branche et
    non par numéro de tour, deux branches partageant le même tour.

    `termine` et `validee` disent deux choses différentes, et les confondre afficherait un
    vainqueur qui n'en est pas encore un : `termine` = le tir est allé au bout ; `validee` = le
    scoreur a scellé, et c'est **seulement** à partir de là que l'arbre avance. Le public voit donc
    « en attente de validation » entre les deux — même vocabulaire qu'E07US009 (livrée).
    """

    numero: int
    tour: int
    libelle: str
    place_en_jeu: list[int] | None
    plage: list[int] | None
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
            libelle=etat.libelle,
            place_en_jeu=None if etat.place_en_jeu is None else list(etat.place_en_jeu),
            plage=None if etat.plage is None else list(etat.plage),
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

    ⚠️ **Une phase peut être présente sans arbre** (E05US024, ADR-0081). `en_attente_de` porte
    l'`ordre` de la phase source dont les places ne sont pas encore attribuées ; les champs de
    dimensions valent alors 0 et les listes sont vides. Le front affiche « en attente de la phase
    *n* » plutôt qu'un bracket — avant cette US, la phase **disparaissait** de la liste, et un
    tableau à venir était indiscernable d'un tableau cassé.

    Les zéros sont un **choix de forme** : garder les champs obligatoires évite de rendre
    optionnelle toute la charge utile pour un cas de bord, et `en_attente_de` est le seul
    discriminant que le front doit lire. Il est **non nul si et seulement si** il n'y a pas d'arbre.
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
    en_attente_de: int | None = None

    @staticmethod
    def de_tableau(tableau: TableauPublic) -> TableauPublicReponse:
        etat = tableau.etat
        if etat is None:
            return TableauPublicReponse(
                phase_id=tableau.phase_id,
                ordre=tableau.ordre,
                type=tableau.type.value,
                effectif=0,
                taille=0,
                nb_tours=0,
                est_termine=False,
                duels=[],
                podium=[],
                en_attente_de=tableau.attente,
            )
        return TableauPublicReponse(
            phase_id=tableau.phase_id,
            ordre=tableau.ordre,
            type=tableau.type.value,
            effectif=etat.effectif,
            taille=etat.taille,
            nb_tours=etat.nb_tours,
            est_termine=etat.est_termine,
            duels=[DuelPublicReponse.de_etat(duel) for duel in etat.duels],
            # `de_connu` et non la fabrique optionnelle : `EtatTableau.podium` est typé
            # `tuple[tuple[int, Duelliste]]`, donc le filtre `is not None` d'un premier jet était
            # **toujours vrai** — et il aurait un jour supprimé une place du podium **en silence**
            # au lieu d'échouer. Deux fabriques, une seule conversion (correctif de revue : la
            # version intermédiaire recopiait le mapping en ligne, dans un fichier dont tout le
            # propos est « un domicile unique »).
            podium=[
                PlaceReponse(rang=rang, duelliste=DuellisteReponse.de_connu(d))
                for rang, d in etat.podium
            ],
        )


class TableauxReponse(BaseModel):
    """Tous les arbres lisibles du **créneau**, dans l'ordre du déroulé.

    ⚠️ `depart_id` et non `tournoi_id` (E01US025, ADR-0075) : deux créneaux portent chacun leur
    arbre de rang 2, et rien dans `TableauPublicReponse` ne les distinguerait.
    """

    depart_id: int
    tableaux: list[TableauPublicReponse]


# --- Lecture ---


@router.get("/departs/{depart_id}", response_model=TableauxReponse)
async def lire_tableaux(depart_id: int, request: Request) -> TableauxReponse:
    """Les arbres du créneau, lecture publique. `404` si le créneau n'existe pas.

    Lecture **synchrone hors boucle événementielle** (règle 7) : la reconstruction est du calcul
    pur mais lourd, elle n'a rien à faire dans l'`event loop` d'un serveur qui sert aussi des
    WebSockets.

    Aucun plafond, comme `/routage/{id}/affectations` et pour la même raison : le client ne demande
    rien, la taille de la réponse est celle des tableaux du tournoi. Le coût dominant reste la
    **reconstruction**, payée une fois par phase et par appel — c'est le régime de `# DETTE-031`,
    que cette US élargit (une route publique de plus, et une surface de polling par spectateur).
    """
    service: ServiceTableauxPublics = request.app.state.service_tableaux_publics
    tableaux = await run_in_threadpool(service.pour_depart, depart_id)
    return TableauxReponse(
        depart_id=tableaux.depart_id,
        tableaux=[TableauPublicReponse.de_tableau(t) for t in tableaux.tableaux],
    )
