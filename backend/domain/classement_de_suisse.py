"""Classement de phase d'un système suisse — l'ordre est déjà **total** (ADR-0083). Deux gestes :
renuméroter, et déclarer les ex æquo irréductibles.

⚠️ **Position et rang sportif ne sont PAS la même chose.** Le rang sportif suit « 1224 » (rang 3
vacant après deux ex æquo) ; `rang_scratch` est un **indice de fenêtre**, de 1 à N sans trou. Y
recopier le rang sportif ferait qu'un prélèvement « rangs 1 à 3 » n'en prendrait que deux — bien
formé, plausible, et faux (ADR-0081). `rang_premier` n'est pas posé ici.
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
