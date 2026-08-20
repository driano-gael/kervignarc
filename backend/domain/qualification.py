"""Le **découpage d'une qualification en tours** (E05US035, [ADR-0093]).

Une qualification est un bloc de `n` volées au cumul : rien dans « 20 volées » ne dit s'il y a un
ou quatre tours. C'est un **choix de l'organisateur** — « 20 volées en 2 tours de 10 » —, et il
n'existe que pour une raison : pouvoir y poser une **pause programmée** comme sur les quatre autres
formats déroulés ([ADR-0091]). Le découpage ne change **rien** au score : la qualification se classe
toujours au total, jamais au tour. C'est l'invariant *avancer ≠ classer* posé par [ADR-0090], et
c'est pourquoi le réglage vit ici et non sur `BaremeQualification`.

**Ce module porte le *réglage*, pas la lecture du terrain.** Il dit ce qu'un découpage doit
respecter et combien de volées fait un tour ; la fabrique d'`AvancementDePhase` qui s'en sert vit
dans `domain.suivi_deroule`, auprès du type qu'elle construit — l'y laisser aurait fermé un cycle
d'import (`phase` → `qualification` → `suivi_deroule` → `phase`), et le cycle n'aurait fait que
signaler ce que la place dit mieux : une fabrique appartient au module de ce qu'elle fabrique.

Quant à *qui* tire — résoudre la population réelle d'une qualification (deux peuvent coexister dans
un créneau, [ADR-0082]), la croiser au plan de cibles et en soustraire les forfaits — c'est une
résolution **applicative** (`ServiceSaisie.avancement_de_phase`), et c'est ce qui rend
l'arithmétique du tour testable sans monter un créneau entier.

⚠️ **Le tour d'une qualification peut reculer.** Un archer qui commence en retard fait baisser le
minimum du plateau, donc le tour. Le calcul ci-dessous n'a **aucune mémoire** — il dit ce qui tourne
maintenant, et c'est `domain.arret_programme.phases_a_arreter` qui absorbe le recul (comparaison
`>` et non `!=`, correctif de 2ᵉ passe d'E05US033). Lisser ici pour « éviter le recul » ferait
mentir la lecture au moment précis où elle protège le pas de tir.

Domaine **pur** (règle 1).

[ADR-0082]: ../../docs/adr/0082-plusieurs-qualifications-dans-un-meme-deroule.md
[ADR-0090]: ../../docs/adr/0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md
[ADR-0091]: ../../docs/adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md
[ADR-0093]: ../../docs/adr/0093-une-qualification-se-decoupe-en-tours-egaux.md
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.bareme import BaremeQualification
from domain.contrat_phase import TypePhase
from domain.erreurs import DecoupageEnToursInvalide

__all__ = [
    "DecoupageEnTours",
    "verifier_decoupage",
    "verifier_decoupage_applicable",
    "volees_par_tour",
]


@dataclass(frozen=True)
class DecoupageEnTours:
    """Le réglage de découpage d'une qualification : **en combien de tours**, et rien d'autre.

    L'organisateur saisit un **nombre de tours**, pas une longueur : c'est l'arbitrage du cadrage
    du 20/08/2026. Le moteur en déduit la longueur (`volees_par_tour`) et **refuse** un nombre qui
    ne divise pas le barème — voir `verifier_decoupage`, qui est le pendant de
    `EtapeDeroule._verifier_rondes_appariables` : une propriété du **couple** (barème, découpage)
    ne peut pas se juger sur le réglage seul, puisqu'un format de bibliothèque s'écrit sans barème.

    Une seule classe pour un seul champ, comme `ConfigurationSuisse` et pour la même raison : le
    réglage se décide à la composition et ne dépend d'aucune donnée du jour J.
    """

    nb_tours: int = 1

    def __post_init__(self) -> None:
        if self.nb_tours < 1:
            raise DecoupageEnToursInvalide(
                f"Une qualification compte au moins un tour (reçu {self.nb_tours})."
            )


def volees_par_tour(bareme: BaremeQualification, decoupage: DecoupageEnTours | None) -> int:
    """Combien de volées dans un tour. Sans découpage, la phase **est** son tour."""
    if decoupage is None:
        return bareme.nb_volees
    return bareme.nb_volees // decoupage.nb_tours


def verifier_decoupage(
    bareme: BaremeQualification | None, decoupage: DecoupageEnTours | None
) -> None:
    """Le découpage tombe-t-il juste sur ce barème ? Lève `DecoupageEnToursInvalide` sinon.

    **Des tours égaux, ou pas de découpage.** 20 volées en 3 tours donnerait 7/7/6 : la pause ne
    tomberait pas au même endroit pour tout le monde, et « après le tour 2 » ne désignerait plus le
    même instant selon l'archer. On refuse à la composition plutôt que d'inventer un dernier tour
    court — et le refus est **réparable d'un geste** à l'atelier, là où le découvrir le jour J ne
    l'est pas.

    **Silencieux quand le barème manque** : une étape en cours de composition n'en a pas encore
    (le brouillon d'ADR-0063). C'est la doctrine déjà tenue par les vérifications voisines d'étape
    — « on ne refuse pas ce qu'on ne peut pas juger » —, et en inventer une seconde ferait diverger
    deux silences qui doivent être le même.
    """
    if decoupage is None or bareme is None:
        return
    if bareme.nb_volees % decoupage.nb_tours != 0:
        raise DecoupageEnToursInvalide(
            f"{bareme.nb_volees} volées ne se découpent pas en {decoupage.nb_tours} tours égaux. "
            "Choisissez un nombre de tours qui divise le nombre de volées."
        )


def verifier_decoupage_applicable(
    type_phase: TypePhase,
    bareme: BaremeQualification | None,
    decoupage: DecoupageEnTours | None,
) -> None:
    """Ce découpage a-t-il un sens sur **cette** phase ? — la garde des deux agrégats porteurs.

    Deux refus en un, et ils ne se recouvrent pas : un découpage sur un type qui n'est pas une
    qualification est un **réglage fantôme** (même garde que `poules`, `big_shoot_off` et `suisse`
    sur `Phase` — retyper une phase sans nettoyer son réglage laisse derrière une valeur que rien
    ne lit, donc invisible et fausse) ; un découpage qui ne divise pas le barème est un déroulé
    **inégal**, ce que `verifier_decoupage` refuse juste au-dessus.

    ⚠️ **Appelée par `EtapeDeroule` *et* par `Phase`, comme `verifier_coherence_etape`.** Les deux
    agrégats portent la même définition depuis ADR-0076 ; n'en garder qu'un laisserait l'autre
    porte ouverte, et c'est exactement le défaut qu'E05US033 a corrigé sur les arrêts (`PUT`
    répondant 200 puis chaque lecture tombant en 422).
    """
    if decoupage is not None and type_phase is not TypePhase.QUALIFICATION:
        raise DecoupageEnToursInvalide(
            f"Une phase de type « {type_phase.value} » n'est pas une qualification : elle n'a pas "
            "de découpage en tours à régler."
        )
    verifier_decoupage(bareme, decoupage)
