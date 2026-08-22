"""Le **classement d'une phase de colline** (E05US027), prêt à être prélevé.

Quatrième et dernier jumeau de [`classement_de_tableau`](classement_de_tableau.py),
[`classement_de_poules`](classement_de_poules.py) et
[`classement_de_suisse`](classement_de_suisse.py), et pour la même raison : une phase aval prélève
« les rangs 1 à 8 » sans avoir à savoir de quel **type** de phase ces rangs viennent.
`application/prelevement.py` consomme un `ClassementSource` ; ce module en fabrique un à partir de
ce que `colline.classement_colline` produit.

## Pourquoi c'est le plus court des quatre

Les trois autres doivent **inventer** quelque chose que leur format ne dit pas :

- un tableau, l'ordre entre battus d'un même tour ;
- une phase de poules, l'ordre entre vainqueurs de groupes différents — rien ne compare la poule 1
  à la poule 2, d'où ses blocs indécis ;
- un système suisse, rien pour l'ordre (il est total), mais il peut laisser des **ex æquo
  irréductibles** que même les critères FFTA ne séparent pas.

Une colline n'invente rien : elle **est** son classement. Les participants occupent des positions
ordonnées, deux d'entre eux n'en occupent jamais la même, et l'ordre final est le résultat sportif
lui-même — c'est tout l'intérêt du format, dont le classement est lisible à tout instant sans
attendre une fin de phase.

⚠️ **`plages_indecises` est donc toujours vide ICI, et c'est une propriété, pas une commodité.**
Une plage indécise déclenche le refus d'ADR-0081 (« une phase attend que sa source ait départagé les
places qu'elle prélève ») : qu'il n'y en ait jamais signifie qu'un prélèvement dans une colline
n'est jamais retenu par une **égalité**. `test_une_colline_ne_declare_aucun_ex_aequo` garde
l'affirmation vérifiée si le format évoluait — une variante autorisant deux archers à la même
position rendrait ce module faux, pas seulement incomplet.

⚠️ **Mais « ICI » n'est pas « nulle part », et la nuance a coûté un majeur en revue.**
`ServiceColline.classement_de_phase` **surcharge** ce champ tant que la phase n'est pas achevée. Ce
module ne peut pas le savoir — il ne voit qu'un ordre, pas un avancement —, et il aurait tort de
prétendre le contraire : *l'indécision par inachèvement n'est pas visible d'ici*. Lire la phrase
ci-dessus comme « un prélèvement dans une colline n'est jamais retenu » serait donc faux, et c'est
exactement ce qu'elle laissait croire. Deux causes d'indécision cohabitent désormais — l'**égalité**
(que ce module tranche, et il n'y en a jamais) et l'**inachèvement** (que seul le service voit) —
cf. [ADR-0081] § « Deux causes d'indécision ».

## Position sportive et indice de fenêtre coïncident ici

Chez le suisse, les deux divergent : la convention « 1224 » laisse un rang vacant après deux ex
æquo, alors que `rang_scratch` doit rester une position de 1 à N sans trou. Sans ex æquo possible,
la colline fait coïncider les deux — mais la **numérotation reste faite ici**, et non recopiée de
`classement_colline`, parce qu'un participant écarté (équipe, archer absent du classement amont)
creuserait sinon un trou dans la fenêtre de prélèvement.

⚠️ **`rang_premier` n'est pas posé ici**, comme chez les trois autres : une phase ne sait pas quelle
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
