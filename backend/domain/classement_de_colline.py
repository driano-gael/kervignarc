"""Classement de phase d'une colline — le format **est** son classement (ADR-0083).

⚠️ **`plages_indecises` est toujours vide ICI, et « ici » n'est pas « nulle part »** :
`ServiceColline` **surcharge** ce champ tant que la phase n'est pas achevée. Deux causes
d'indécision cohabitent — l'égalité (tranchée ici, jamais rencontrée) et l'inachèvement (visible du
seul service), cf. ADR-0081. `rang_premier` n'est pas posé ici (`DETTE-034`).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from domain.archer import ArcherId
from domain.classement import Classement, LigneClassement
from domain.classement_de_tableau import ClassementSource, situee_au_rang
from domain.participant import GenreParticipant, Participant


def classement_de_colline(
    colline: Sequence[tuple[Participant, int]],
    lignes: Mapping[ArcherId, LigneClassement],
) -> ClassementSource:
    """Le classement de la phase — la colline, dans son état final.

    `colline` est ce que `colline.classement_colline` rend : les participants dans l'ordre de leurs
    positions. `lignes` porte l'identité des archers (nom, catégorie, club), reprise telle quelle —
    un classement de colline n'est pas un objet d'une autre nature, c'est le **même** archer situé
    autrement. Seul `rang_scratch` change.

    Une colline **vide** est une réponse licite, pas une erreur : une phase avale qui prélève dans
    une colline pas encore commencée doit lire « rien à prendre » plutôt que tomber.
    """
    retenus = _retenus(colline, lignes)
    return ClassementSource(
        classement=Classement(
            lignes=tuple(
                situee_au_rang(lignes[participant.ref_id], position)
                for position, participant in enumerate(retenus, start=1)
            )
        ),
        # Vide **par construction** : voir l'en-tête du module. Ce n'est pas un oubli de calcul.
        plages_indecises=(),
    )


def _retenus(
    colline: Sequence[tuple[Participant, int]],
    lignes: Mapping[ArcherId, LigneClassement],
) -> list[Participant]:
    """Les participants dont l'archer existe au classement amont — l'ordre de la colline est gardé.

    Filtrer **avant** de numéroter, et non après : `preleves` lit `rang_scratch`, donc une
    numérotation trouée ferait manquer des archers à une fenêtre par ailleurs correcte. Même geste
    que les trois jumeaux, et même motif.

    Les participants **équipe** sont écartés (leur `ref_id` n'est pas un archer, ADR-0028), comme le
    font déjà les trois autres classements de phase ; leur résolution viendra avec E13US002.
    """
    return [
        participant
        for participant, _position in colline
        if participant.genre is GenreParticipant.INDIVIDUEL and participant.ref_id in lignes
    ]


__all__ = ["classement_de_colline"]
