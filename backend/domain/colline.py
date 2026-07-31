"""Moteur de **colline** — King of the Hill et Ladder (E05US015, [ADR-0062]).

Règles **fournies par le commanditaire le 31/07/2026**, reproduites au [référentiel §10.1]. Les deux
formats y sont décrits séparément, mais ils partagent **une seule mécanique** : les participants
occupent des positions ordonnées, on en fait s'affronter certains, **le gagnant monte et le perdant
descend**. Ce qui les sépare est la **portée du défi** — un rang au-dessus (voisins) pour le King of
the Hill, deux pour le Ladder (« le n°6 peut seulement défier le 5 ou le 4 »). C'est donc un
paramètre, pas un second moteur : la règle 2 en fait de la configuration.

**Deux arbitrages qu'il faut connaître pour lire ce module.**

1. **Version « journée », pas classement permanent.** Les règles données décrivent un classement qui
   « évolue toute l'année » et des défis lancés au fil de l'eau — ce qui ne se modélise pas en
   `Phase` (une phase a des sources, un effectif, un début et une fin dans un tournoi). Arbitré avec
   le commanditaire au cadrage du 31/07/2026 : on retient la **variante de journée** — ordre initial
   donné par le classement source, `nb_manches` réglé à la composition, classement final = la
   colline à la fin. Le classement permanent de club reste un autre produit.
2. **La mécanique retenue est « deux voisins s'affrontent »**, la seconde des deux que la règle du
   King of the Hill propose (l'autre étant « tous peuvent défier le King »). Choisi par le
   commanditaire : elle fait jouer tout le monde à chaque manche, là où défier le King n'occupe que
   deux archers.

⚠️ **Écart signalé, non arbitré seul.** L'exemple chiffré du Ladder ne concorde pas avec sa propre
règle : partant de `1 2 3 4 5 6 7 8`, « le n°6 défie le 4 et gagne » y donne `1 2 3 5 6 4 7 8`,
c'est-à-dire le n°6 en **5ᵉ** position et le n°4 en **6ᵉ** — alors que gagner un défi contre le 4
devrait mener à la 4ᵉ. Ce module applique la **règle** (« le gagnant monte, le perdant descend » :
les deux positions s'échangent), pas l'exemple. À confirmer à la recette — c'est consigné dans
`stories/E05-moteur-phases.md` et dans `docs/fonctionnel/E05US015.md`.

Domaine **pur** (règle 1).

[référentiel §10.1]: ../../docs/referentiel-ffta.md
[ADR-0062]: ../../docs/adr/0062-catalogue-de-types-de-phase.md
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from domain.erreurs import ConfigurationCollineInvalide
from domain.participant import Participant


@dataclass(frozen=True)
class ConfigurationColline:
    """Le réglage d'une phase de colline.

    `portee_de_defi` **est** ce qui distingue les deux formats du catalogue : 1 = King of the Hill
    (on défie son voisin immédiat), 2 = Ladder (« le n°6 peut défier le 5 ou le 4 »). Rien d'autre
    ne change, ce qui est la meilleure preuve qu'il ne fallait pas deux moteurs.

    Une portée ≥ à l'effectif transformerait le format en « n'importe qui défie n'importe qui »,
    qui n'est plus ni un King of the Hill ni un Ladder — d'où le refus, contrôlé au démarrage
    puisqu'il dépend de l'effectif.
    """

    nb_manches: int
    portee_de_defi: int = 1

    def __post_init__(self) -> None:
        if self.nb_manches < 1:
            raise ConfigurationCollineInvalide(
                f"Une colline se dispute en au moins une manche (reçu {self.nb_manches})."
            )
        if self.portee_de_defi < 1:
            raise ConfigurationCollineInvalide(
                f"Un défi porte au moins sur la position juste au-dessus "
                f"(reçu {self.portee_de_defi})."
            )

    @staticmethod
    def king_of_the_hill(nb_manches: int) -> ConfigurationColline:
        """Défis entre **voisins immédiats** — la variante retenue au cadrage."""
        return ConfigurationColline(nb_manches=nb_manches, portee_de_defi=1)

    @staticmethod
    def ladder(nb_manches: int) -> ConfigurationColline:
        """Défis **encadrés** à deux rangs, comme le décrit la règle du Ladder."""
        return ConfigurationColline(nb_manches=nb_manches, portee_de_defi=2)


@dataclass(frozen=True)
class DefiColline:
    """Un défi d'une manche : le `challenger` (position basse) affronte le `defie` (position haute).

    Les positions sont **1-indexées**, comme la colline se lit (« le n°6 »), pas comme un tableau
    Python s'indexe. C'est le seul endroit du module où la distinction compte, et la confondre
    décalerait tout le classement d'un rang.
    """

    position_haute: int
    position_basse: int
    defie: Participant
    challenger: Participant


@dataclass(frozen=True)
class IssueDefi:
    """Qui a gagné un défi — le moteur applique, il ne fait pas tirer."""

    defi: DefiColline
    vainqueur: Participant


def defis_de_la_manche(
    colline: Sequence[Participant], manche: int, configuration: ConfigurationColline
) -> tuple[DefiColline, ...]:
    """Les défis **sans recouvrement** de la manche `manche` (1-indexée).

    ⚠️ **`portee_de_defi` est une distance MAXIMALE, pas une distance exacte** — « le n°6 peut
    défier le 5 **ou** le 4 » énonce un choix. La distance effective **tourne** d'une manche à
    l'autre (`1 + (manche-1) % portee`), et le découpage en blocs tourne avec elle.

    **C'est ce qui rend le Ladder capable de classer, et un premier jet de cette US l'avait raté.**
    En figeant la distance à `portee`, tout échange se faisait à distance 2 : la **parité** de la
    position devenait un invariant, la colline se scindait en deux moitiés étanches, et l'archer
    parti en position 2 ne pouvait **jamais** atteindre la position 1. Vérifié à l'époque : une
    colline inversée où le meilleur gagne toujours se stabilisait sur `2 1 4 3 6 5 8 7` — faux, et
    faux pour toujours. Les manches à distance 1 sont exactement ce qui brise cette parité.

    À portée 1, c'est l'alternance pair/impair : manche 1 → (1,2)(3,4)(5,6), manche 2 →
    (2,3)(4,5)(6,7). Les extrémités se reposent une manche sur deux — inévitable, et sans effet sur
    le classement puisqu'elles rejouent la manche suivante.
    """
    if manche < 1:
        raise ConfigurationCollineInvalide(
            f"Les manches sont numérotées à partir de 1 (reçu {manche})."
        )
    if manche > configuration.nb_manches:
        raise ConfigurationCollineInvalide(
            f"Cette colline compte {configuration.nb_manches} manches ; "
            f"la manche {manche} n'existe pas."
        )
    if configuration.portee_de_defi >= len(colline):
        raise ConfigurationCollineInvalide(
            f"Une portée de défi de {configuration.portee_de_defi} sur une colline de "
            f"{len(colline)} participants revient à laisser chacun défier n'importe qui : ce n'est "
            "plus un King of the Hill ni un Ladder."
        )
    # La distance parcourt 1..portée au fil des manches ; le découpage en blocs suit la distance
    # retenue, et son décalage tourne à chaque cycle complet de distances.
    distance = 1 + (manche - 1) % configuration.portee_de_defi
    pas = distance + 1
    decalage = ((manche - 1) // configuration.portee_de_defi) % pas
    defis: list[DefiColline] = []
    depart = decalage
    while depart + distance < len(colline):
        haute = depart
        basse = depart + distance
        defis.append(
            DefiColline(
                position_haute=haute + 1,
                position_basse=basse + 1,
                defie=colline[haute],
                challenger=colline[basse],
            )
        )
        depart += pas
    return tuple(defis)


def appliquer_manche(
    colline: Sequence[Participant], issues: Iterable[IssueDefi]
) -> tuple[Participant, ...]:
    """Applique les issues d'une manche : **le gagnant monte, le perdant descend**.

    Les deux positions du défi s'**échangent** quand le challenger l'emporte, et restent en place
    sinon. Les positions intermédiaires (à portée > 1) ne bougent pas : elles n'ont pas participé,
    rien ne justifie de les déplacer — c'est le point sur lequel l'exemple chiffré du Ladder diverge
    de sa règle (voir l'en-tête du module).

    ⚠️ Les défis d'une même manche étant **sans recouvrement** par construction, l'ordre
    d'application n'a aucune importance : deux échanges ne peuvent pas se marcher dessus. Si un jour
    une variante autorisait le recouvrement, ce ne serait plus vrai et il faudrait ordonner —
    raison pour laquelle `defis_de_la_manche` garantit la propriété plutôt que de la supposer.
    """
    nouvelle = list(colline)
    for issue in issues:
        haute = issue.defi.position_haute - 1
        basse = issue.defi.position_basse - 1
        if not 0 <= haute < len(nouvelle) or not 0 <= basse < len(nouvelle):
            raise ConfigurationCollineInvalide("Un défi désigne une position hors de la colline.")
        if issue.vainqueur not in (issue.defi.defie, issue.defi.challenger):
            raise ConfigurationCollineInvalide(
                "Le vainqueur d'un défi est l'un des deux participants engagés."
            )
        if issue.vainqueur == issue.defi.challenger:
            nouvelle[haute], nouvelle[basse] = nouvelle[basse], nouvelle[haute]
    return tuple(nouvelle)


def classement_colline(colline: Sequence[Participant]) -> tuple[tuple[Participant, int], ...]:
    """Le classement final : **la colline elle-même**, position par position.

    C'est tout l'intérêt du format et ce qui le rend lisible pour le public — le classement est
    visible à tout instant, il n'a pas à être calculé en fin de phase. Aucun ex æquo n'est
    possible : deux participants n'occupent jamais la même position.
    """
    return tuple((participant, rang) for rang, participant in enumerate(colline, start=1))
