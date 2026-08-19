"""Le **tour** — unité d'avancement générique d'une phase ([ADR-0090], E05US032).

Toute phase avance par tours, quel que soit son format, et **un tour n'est pas un braquet** : le
tour dit *où on en est*, le braquet dit *quels rangs ce tour attribue*. Certaines phases classent au
fil des tours (l'élimination directe : la *Règle R*), d'autres ne classent qu'à la fin (la
qualification : le total, pas la volée 12). Confondre les deux est ce que le code faisait jusqu'ici
— `domain.suivi_deroule` dérivait ses tours des braquets, d'où une qualification, une poule ou un
système suisse en cours qui affichaient « zéro tour ».

**Ce module porte la résolution du tour en libellé, et le réglage qui le détermine quand le format
ne le détermine pas** (E05US033). L'**unité** elle-même vit au registre de contrat
(`domain.contrat_phase.UniteDeTour`), avec les six autres questions du contrat — la séparer d'eux
obligerait le contrat à importer ce module pendant que ce module importe le contrat, soit exactement
le cycle qu'E05US023 avait déjà eu à défaire en déplaçant `TypePhase`. Le **nombre** de tours se
calcule là où vit la donnée qui le détermine (la projection pour un tableau, le réglage pour un
suisse), et le **tour courant** se demande au service qui déroule la phase — port
`LecteurAvancementDePhase`, ADR-0090 §5.

⚠️ **Élargissement assumé par E05US033**, et il faut dire pourquoi plutôt que de laisser la
docstring mentir. `DecoupageEnTours` est un réglage d'organisateur — « 20 volées en 2 tours de 10 »
— donc de la *configuration*, quand le reste du module est de la *résolution*. Il vit ici malgré
tout parce qu'il répond à « combien de tours » **pour les seuls formats dont la structure se tait**,
c'est-à-dire exactement le trou que `PHASE_ENTIERE` nomme. Le placer ailleurs ouvrirait un second
domicile à la question du tour, et `DETTE-020` documente déjà ce que coûte un domicile de trop.

Module **pur et synchrone** (règle 1) : aucune lecture, aucun état.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.contrat_phase import TypePhase, UniteDeTour, contrat_de
from domain.erreurs import DecoupageEnToursInvalide
from domain.plage import Plage
from domain.tableau import libelle_tour

# ⚠️ `UniteDeTour` n'est **pas** ré-exporté : il vit dans `domain.contrat_phase`, et deux chemins
# d'import pour un même type sont l'amorce exacte de la divergence que ce module combat par ailleurs
# (`DETTE-020`). Relevé en revue par deux axes.
__all__ = [
    "DecoupageEnTours",
    "libelle_de_tour",
    "nb_tours_regles",
    "unite_de_tour",
    "unite_de_tour_effective",
]

_MOT_DE_LA_SALLE: dict[UniteDeTour, str] = {
    UniteDeTour.TOUR: "Tour",
    UniteDeTour.RONDE: "Ronde",
    UniteDeTour.MANCHE: "Manche",
}


def unite_de_tour(type_phase: TypePhase) -> UniteDeTour:
    """Dans quelle unité ce type de phase avance-t-il.

    Lit le **registre de contrat** plutôt qu'une table locale : une table jumelle divergerait du
    jour où un type entrerait au catalogue. C'est la leçon de `TYPES_SIGNALES_EN_ECART` en E05US023
    — une table dérivée n'est sûre que si elle répond exactement à la même question.
    """
    return contrat_de(type_phase).unite_de_tour


def libelle_de_tour(
    unite: UniteDeTour,
    tour: int,
    nb_tours: int,
    place_en_jeu: tuple[int, int] | None = None,
    plage: Plage | None = None,
) -> str | None:
    """Le nom que la salle donne à ce tour, ou `None` si elle n'en donne aucun.

    `None` plutôt qu'une chaîne vide pour `PHASE_ENTIERE` : une qualification en cours se lit «
    Qualification », jamais « Qualification — tour 1 sur 1 ». L'appelant décide de n'afficher rien,
    et un `None` explicite l'empêche de concaténer un séparateur orphelin.

    ⚠️ **La même clause vaut pour toute phase à un seul tour**, pas seulement pour `PHASE_ENTIERE` :
    une poule de deux archers, un système suisse dont l'effectif n'autorise qu'une ronde, un Big
    Shoot Off à manche unique n'annoncent **rien**. C'est la lettre du CA (« il n'y a rien à
    distinguer »), et la première rédaction ne l'appliquait qu'au premier cas — relevé en revue (axe
    B), avec la précision qui compte : le test censé couvrir ce CA n'exerçait que le cas qui passait
    déjà. Le **tableau** fait exception et n'a pas besoin de la garde : son tour unique s'appelle «
    Finale », qui est un nom.

    ⚠️ **`TOUR_DE_TABLEAU` délègue, il ne recalcule pas.** `DETTE-020` compte déjà **deux**
    domiciles pour le libellé de tour d'un arbre (`domain.tableau.libelle_tour` et le front
    `saisie-duels/duel.ts`), et `E07US005` a failli en ouvrir un troisième avant de le refermer en
    servant le libellé du domaine au DTO. Réimplémenter « à rebours de la finale » ici en ouvrirait
    un quatrième — et surtout perdrait les deux règles que la fonction du tableau porte et qu'un
    générique ne devinerait pas : la petite finale se dispute **au même tour** que la finale, et un
    match de placement se nomme par sa **plage** et non par sa distance au titre.

    `place_en_jeu` et `plage` ne concernent donc que le tableau ; les autres unités les ignorent,
    n'ayant pas d'arbre où se perdre.
    """
    if unite is UniteDeTour.PHASE_ENTIERE:
        return None
    if unite is UniteDeTour.TOUR_DE_TABLEAU:
        # Pas de garde `nb_tours <= 1` ici : le tour unique d'un tableau de 2 s'appelle « Finale » —
        # un **nom**, pas un numéro. La clause du CA vise les numéros nus.
        return libelle_tour(tour, nb_tours, place_en_jeu, plage)
    if nb_tours <= 1:
        return None
    return f"{_MOT_DE_LA_SALLE[unite]} {tour}"


@dataclass(frozen=True)
class DecoupageEnTours:
    """Le découpage d'une phase en tours **décidé par l'organisateur** (E05US033, [ADR-0091]).

    « 20 volées en 2 tours de 10 » : rien dans la structure d'une qualification ne dit s'il y a un
    ou quatre tours — c'est un **choix**, et le CA d'E05US032 le disait déjà en reportant le réglage
    « là où il sert ». Il sert ici : sans lui, une qualification n'a qu'un tour, et un arrêt
    programmé « après le tour n » n'a nulle part où se poser.

    **Configuration, pas code** (règle 2) : le réglage vit sur l'`EtapeDeroule` du tournoi, comme le
    nombre de rondes d'un suisse, et tous les départs le rejouent (ADR-0076).

    `nb_tours=1` est le **défaut écrit en clair** — il ne découpe rien et laisse la phase entière.
    """

    nb_tours: int = 1

    def __post_init__(self) -> None:
        """Fait respecter l'invariant quelle que soit la porte d'entrée (`replace()` compris)."""
        if self.nb_tours < 1:
            raise DecoupageEnToursInvalide(
                f"une phase compte au moins un tour, pas {self.nb_tours}"
            )


def unite_de_tour_effective(type_phase: TypePhase, nb_tours: int) -> UniteDeTour:
    """L'unité d'avancement **réelle** d'une phase, sachant combien de tours elle compte.

    Le contrat donne l'unité **du format** ; ce nombre-là la précise pour les seuls formats dont la
    structure ne détermine pas les tours — ceux que le contrat déclare `PHASE_ENTIERE`. Une
    qualification d'un seul tenant reste « Qualification » ; découpée en deux, elle dit « Tour 2 ».

    ⚠️ **`nb_tours`, et non le réglage `DecoupageEnTours`** — c'est un correctif de revue, et la
    nuance porte tout. La première rédaction prenait le découpage en paramètre, donc l'affichage
    jugeait sur le *réglage* pendant que le déclencheur jugeait sur l'*avancement lu* : **deux
    sources pour le même nombre**, exactement ce que la docstring de cette fonction jurait ne jamais
    se produire. Les deux pouvaient diverger — un suisse réglé à 9 rondes n'en apparie que 5 — et
    l'axe adversarial l'a relevé.

    `nb_tours` est ce que le suivi **observe** (`AvancementDePhase.nb_tours`, rendu par le service
    qui déroule la phase, lui-même dérivé du réglage pour une qualification). Une seule source,
    celle du terrain.

    ⚠️ **Ce n'est pas une contradiction du contrat** : `PHASE_ENTIERE` signifie littéralement « rien
    dans la structure de ce format ne dit combien de tours » (ADR-0090). Quand l'organisateur le dit
    et que le lecteur le confirme, la source existe enfin.

    Sur un format qui compte déjà ses tours (un suisse par son réglage, une poule par son
    round-robin, un tableau par ses braquets), l'unité du contrat l'emporte : `nb_tours` n'y change
    rien, et un tableau à un seul tour s'appelle « Finale », pas « Tour 1 ».
    """
    unite = contrat_de(type_phase).unite_de_tour
    if unite is not UniteDeTour.PHASE_ENTIERE:
        return unite
    return UniteDeTour.TOUR if nb_tours > 1 else UniteDeTour.PHASE_ENTIERE


def nb_tours_regles(type_phase: TypePhase, decoupage: DecoupageEnTours | None) -> int:
    """Combien de tours le **réglage** annonce pour cette phase, avant toute lecture de terrain.

    Ne concerne que les formats `PHASE_ENTIERE` : partout ailleurs, le nombre de tours se lit de la
    donnée qui le détermine (`AvancementDePhase.nb_tours`, rendu par le service du format)
    et cette fonction n'a rien à en dire — elle rend `1`, la valeur du contrat, et l'appelant qui a
    besoin du vrai nombre demande au port. Le dire plutôt que de rendre `0` ou de lever : « 1 tour »
    est **vrai** pour une phase dont on ignore la structure, et c'est la convention d'E05US032.
    """
    if contrat_de(type_phase).unite_de_tour is not UniteDeTour.PHASE_ENTIERE:
        return 1
    return 1 if decoupage is None else decoupage.nb_tours
