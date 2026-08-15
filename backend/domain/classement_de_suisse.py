"""Le **classement d'une phase au système suisse** (E05US026), prêt à être prélevé.

Troisième jumeau de [`classement_de_tableau`](classement_de_tableau.py) et
[`classement_de_poules`](classement_de_poules.py), et pour la même raison : une phase aval prélève
« les rangs 1 à 8 » sans avoir à savoir de quel **type** de phase ces rangs viennent.
`application/prelevement.py` consomme un `ClassementSource` ; ce module en fabrique un à partir de
ce que `suisse.classement_suisse` produit.

## Pourquoi il est plus court que celui des poules

Une phase de poules doit **inventer** un ordre de phase : rien ne compare le vainqueur de la poule
1 à celui de la poule 2, d'où le rangement « par rang de poule d'abord », les blocs, et leur
indécision par défaut. Un système suisse n'a pas ce problème — tout le monde joue dans le **même
vivier**, et `classement_suisse` rend déjà un ordre **total** : points, Buchholz, critères FFTA.

Il ne reste donc ici que deux gestes :

1. **renuméroter** — `preleves` lit `rang_scratch`, qui doit être la *position* dans le classement
   de phase, de 1 à N sans trou ;
2. **déclarer les ex æquo irréductibles** — ceux que même les critères FFTA ne séparent pas.

## Position et rang sportif ne sont pas la même chose

`classement_suisse` applique la convention **« 1224 »** : deux ex æquo au rang 2 laissent le rang 3
vacant, et le suivant est 4ᵉ. C'est le rang **sportif**, celui qu'on affiche.

`rang_scratch`, lui, est un **indice de fenêtre** : « les rangs 1 à 3 » désigne les trois premières
places du classement. Y recopier le rang sportif ferait disparaître la 3ᵉ position, et cette fenêtre
ne prendrait que deux archers — un prélèvement bien formé, plausible, et faux.

Les deux coexistent donc : le rang sportif reste lisible sur `RangSuisse`, la position sert au
prélèvement, et c'est la **plage indécise** qui porte l'information « ces deux-là sont à égalité »
([ADR-0081](../../docs/adr/0081-une-phase-attend-que-sa-source-ait-departage-les-places-qu-elle-preleve.md)).
Départager sur le rang de qualification serait exactement la faute qu'ADR-0081 nomme.

⚠️ **`rang_premier` n'est pas posé ici**, comme chez les deux autres : une phase ne sait pas quelle
tranche du tournoi elle dispute — c'est une propriété de sa place dans le déroulé, que seul le
service qui remonte la chaîne connaît (`application/prelevement.py:tranche`). Le poser ici lui
donnerait une valeur qu'elle ne peut pas vérifier, c'est-à-dire `DETTE-034` rouverte.

Domaine **pur** : aucun framework, aucune autre couche (règle 1).

[ADR-0083]: ../../docs/adr/0083-le-contrat-de-phase-jouable.md
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from domain.archer import ArcherId
from domain.classement import Classement, LigneClassement
from domain.classement_de_tableau import ClassementSource, situee_au_rang
from domain.participant import GenreParticipant
from domain.suisse import RangSuisse


def classement_de_suisse(
    rangs: Sequence[RangSuisse],
    lignes: Mapping[ArcherId, LigneClassement],
) -> ClassementSource:
    """Le classement de la phase, et ce qu'il a d'encore indécis.

    `rangs` est ce que `suisse.classement_suisse` rend — déjà ordonné. `lignes` porte l'identité
    des archers (nom, catégorie, club), reprise telle quelle : un classement de suisse n'est pas un
    objet d'une autre nature, c'est le **même** archer situé autrement. Seul `rang_scratch` change.

    Un classement **vide** est une réponse licite, pas une erreur : une phase avale qui prélève dans
    un suisse pas encore commencé doit lire « rien à prendre » plutôt que tomber.
    """
    retenus = _retenus(rangs, lignes)
    return ClassementSource(
        classement=Classement(
            lignes=tuple(
                situee_au_rang(lignes[ligne.participant.ref_id], position)
                for position, ligne in enumerate(retenus, start=1)
            )
        ),
        plages_indecises=_indecises(retenus),
    )


def _retenus(
    rangs: Sequence[RangSuisse], lignes: Mapping[ArcherId, LigneClassement]
) -> list[RangSuisse]:
    """Les lignes dont l'archer existe au classement — l'ordre du suisse est conservé.

    Filtrer **avant** de numéroter, et non après : `preleves` lit `rang_scratch`, donc une
    numérotation trouée ferait manquer des archers à une fenêtre par ailleurs correcte. Même geste
    que `classement_de_poules._retenus`, et même motif.

    Les participants **équipe** sont écartés (leur `ref_id` n'est pas un archer, ADR-0028), comme le
    font déjà les deux autres classements de phase ; leur résolution viendra avec E13US002.
    """
    return [
        ligne
        for ligne in rangs
        if ligne.participant.genre is GenreParticipant.INDIVIDUEL
        and ligne.participant.ref_id in lignes
    ]


def _indecises(retenus: Sequence[RangSuisse]) -> tuple[tuple[int, int], ...]:
    """Les plages de **positions** que le suisse n'a pas départagées, bornes incluses.

    Deux archers sont à égalité quand ils partagent le même **rang sportif** — c'est la définition
    même de la convention « 1224 » appliquée par `classement_suisse`, et le drapeau `ex_aequo` le
    redit. On lit le rang plutôt que le drapeau : le rang est la donnée, le drapeau son résumé, et
    deux sources pour une information sont une divergence en attente.

    ⚠️ **Les positions, pas les rangs sportifs.** Les ex æquo aux rangs 2 et 2 occupent les
    positions 2 et 3 : c'est cette plage-là que `ClassementSource.coupe` compare à une fenêtre de
    prélèvement, puisque la fenêtre s'exprime elle aussi en positions.

    Un groupe d'un seul occupant n'est jamais indécis — il n'y a personne avec qui être à égalité.
    """
    plages: list[tuple[int, int]] = []
    debut = 1
    for position in range(1, len(retenus) + 1):
        dernier = position == len(retenus)
        if dernier or retenus[position].rang != retenus[position - 1].rang:
            if position > debut:
                plages.append((debut, position))
            debut = position + 1
    return tuple(plages)
