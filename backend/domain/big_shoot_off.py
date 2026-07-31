"""Moteur du **Big Shoot Off** — finale à N archers en parallèle (E05US015, [ADR-0062]).

Règle **fournie par le commanditaire le 31/07/2026**, qui **ferme la question Q9** du cahier des
charges — bloquante depuis l'origine du projet. Reproduite au [référentiel §10.1] :

> Une phase finale qui reçoit x archers. Ils sont en parallèle, chacun tire x volées de x flèches,
> et le plus faible score est éliminé — jusqu'aux x derniers restants.

⚠️ **Ce n'est pas un barème de duel mais un type de phase à N participants.** Le « Big » désigne le
**nombre d'archers**, pas le nombre de flèches. Le cadrage a levé ainsi une tension du cahier des
charges, qui le rangeait tantôt en barème (EF-1.5, EF-5.2) tantôt en type de phase (EF-3.2) : c'est
bien un type, et c'est pourquoi il a son moteur plutôt qu'une ligne dans `BaremeDuel`.

Les quatre `x` de la règle sont **quatre paramètres distincts** que l'énoncé confond : N vient de la
source, V (volées par manche), F (flèches par volée) et K (derniers restants) se règlent à la
composition. Les lire comme un seul nombre donnerait « 5 archers tirent 5 volées de 5 flèches
jusqu'aux 5 derniers » — c'est-à-dire une phase qui ne se termine jamais.

**Arbitrages du 31/07/2026** (reversés dans `stories/E05-moteur-phases.md`) :
- **cumul ou remise à zéro entre manches** : c'est un **paramètre** (`cumul_des_manches`), à la
  demande du commanditaire. Défaut : **remise à zéro** — lecture littérale de « chacun tire … et le
  plus faible score est éliminé », et c'est ce qui fait le suspense d'une finale spectacle. Au
  cumul, un mauvais premier tour pèse jusqu'au bout et les dernières manches perdent leur enjeu.
- **égalité au plus faible** → **barrage** (§8.2, `domain/barrage.py`) ;
- les éliminés prennent les rangs dans l'**ordre inverse** de leur sortie, ce qui fait du BSO une
  phase qui **classe tout le monde**, cohérente avec le placement 1→N d'E05US010 ;
- **K = 1** par défaut ; si `K > 1`, les restants **partagent** le rang.

⚠️ **Ce module ne fait pas tirer.** Il reçoit les scores d'une manche et dit qui sort ; c'est une
mécanique d'élimination, pas une saisie. Domaine **pur** (règle 1).

[référentiel §10.1]: ../../docs/referentiel-ffta.md
[ADR-0062]: ../../docs/adr/0062-catalogue-de-types-de-phase.md
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from domain.erreurs import ConfigurationBigShootOffInvalide, ScoreDeMancheManquant
from domain.participant import Participant


@dataclass(frozen=True)
class ConfigurationBigShootOff:
    """Les quatre paramètres du format — les `x` que l'énoncé de la règle confond en un seul.

    `restants` est le K : le nombre d'archers encore en lice quand la phase s'arrête. Sa validation
    dépend de l'effectif réel, donc elle vit dans `demarrer` et non ici — une configuration de
    bibliothèque (`FormatTournoi`) est écrite avant de savoir combien d'archers arriveront.
    """

    volees: int = 1
    fleches_par_volee: int = 3
    restants: int = 1
    cumul_des_manches: bool = False

    def __post_init__(self) -> None:
        if self.volees < 1:
            raise ConfigurationBigShootOffInvalide(
                f"Une manche compte au moins une volée (reçu {self.volees})."
            )
        if self.fleches_par_volee < 1:
            raise ConfigurationBigShootOffInvalide(
                f"Une volée compte au moins une flèche (reçu {self.fleches_par_volee})."
            )
        if self.restants < 1:
            raise ConfigurationBigShootOffInvalide(
                f"Le Big Shoot Off laisse au moins un archer en lice (reçu {self.restants})."
            )

    @property
    def fleches_par_manche(self) -> int:
        """Combien de flèches chaque archer tire à chaque manche (V volées de F flèches)."""
        return self.volees * self.fleches_par_volee


@dataclass(frozen=True)
class EtatBigShootOff:
    """L'état d'un Big Shoot Off entre deux manches — **immuable**, comme tout agrégat du domaine.

    `en_lice` est ordonné et ne sert qu'à l'affichage ; `rangs` associe à chaque **éliminé** le rang
    qu'il emporte. Un BSO terminé a `en_lice` réduit à K et `rangs` complet.
    """

    configuration: ConfigurationBigShootOff
    en_lice: tuple[Participant, ...]
    rangs: tuple[tuple[Participant, int], ...] = ()
    manche: int = 0
    cumuls: tuple[tuple[Participant, int], ...] = ()
    """Scores cumulés depuis le début — vides et inutilisés quand `cumul_des_manches` est faux."""

    barrage_en_cours: tuple[Participant, ...] = ()
    """Les ex æquo au plus faible score dont le barrage n'est pas encore tranché.

    ⚠️ **Porté par l'état, pas seulement par l'issue de la manche** — sans quoi la couture avec
    `domain/barrage.py` n'est pas praticable : `eliminer_apres_barrage` ne pourrait vérifier ni
    qu'une manche est réellement suspendue, ni que le sortant faisait partie des ex æquo. Un service
    pourrait alors éliminer n'importe qui, à n'importe quel moment, et lui décerner un rang."""

    @property
    def est_termine(self) -> bool:
        """La phase s'arrête quand il ne reste que K archers (règle : « jusqu'aux x derniers »)."""
        return len(self.en_lice) <= self.configuration.restants

    def classement(self) -> tuple[tuple[Participant, int], ...]:
        """Le classement complet : les K restants d'abord, puis les éliminés dans l'ordre inverse.

        Les **restants partagent le rang 1** quand `K > 1` : la règle ne prévoit rien pour les
        départager entre eux — c'est le principe même d'un « jusqu'aux x derniers ». Leur imposer un
        ordre reviendrait à inventer un critère (le score de la dernière manche ?) que le
        commanditaire n'a pas donné.
        """
        tetes = tuple((participant, 1) for participant in self.en_lice)
        return tetes + self.rangs


@dataclass(frozen=True)
class IssueManche:
    """Ce qu'une manche produit : qui sort, et à quel rang — ou l'égalité qui bloque.

    `barrage_entre` n'est pas vide quand plusieurs archers partagent le score le plus faible : la
    manche **ne peut pas** se conclure, il faut faire tirer (§8.2). L'état renvoyé est alors
    inchangé — on ne devine pas un éliminé.
    """

    etat: EtatBigShootOff
    elimine: Participant | None = None
    rang_attribue: int | None = None
    barrage_entre: tuple[Participant, ...] = ()


def demarrer(
    participants: Sequence[Participant], configuration: ConfigurationBigShootOff
) -> EtatBigShootOff:
    """Ouvre un Big Shoot Off sur les `participants` reçus de la phase source.

    `restants` doit être **strictement inférieur** à l'effectif : à `K = N`, personne n'est jamais
    éliminé et la phase ne se termine pas. C'est le seul contrôle qui exige de connaître l'effectif,
    d'où sa place ici plutôt que sur la configuration.
    """
    if configuration.restants >= len(participants):
        raise ConfigurationBigShootOffInvalide(
            f"Un Big Shoot Off à {len(participants)} entrants ne peut pas en laisser "
            f"{configuration.restants} en lice : aucun archer ne serait jamais éliminé."
        )
    return EtatBigShootOff(
        configuration=configuration,
        en_lice=tuple(participants),
        cumuls=tuple((participant, 0) for participant in participants),
    )


def jouer_manche(etat: EtatBigShootOff, scores: Mapping[Participant, int]) -> IssueManche:
    """Applique une manche : le **plus faible score sort**, et prend le rang le plus bas restant.

    `scores` porte le score **de la manche** pour chaque archer encore en lice. En mode cumul, le
    moteur les additionne aux manches précédentes avant de comparer ; en mode remise à zéro (le
    défaut), il compare la manche seule.

    Le rang attribué à l'éliminé est `len(en_lice)` — le dernier rang encore disponible. C'est
    l'« ordre inverse de sortie » de l'arbitrage : le premier sorti d'un BSO à 5 prend le rang 5, et
    le vainqueur restera seul au rang 1.

    ⚠️ Un score **manquant** est refusé plutôt que traité comme un zéro. Un archer sans score dans
    la table n'est pas un archer à zéro : c'est une saisie incomplète, et le traiter comme le plus
    faible l'éliminerait sur une donnée absente — précisément l'erreur qu'on ne voit qu'après coup.
    """
    if etat.est_termine:
        raise ConfigurationBigShootOffInvalide(
            "Ce Big Shoot Off est terminé : il ne reste que les archers à conserver."
        )
    manquants = [participant for participant in etat.en_lice if participant not in scores]
    if manquants:
        raise ScoreDeMancheManquant(
            f"{len(manquants)} archer(s) encore en lice n'ont pas de score pour cette manche : "
            "un score absent n'est pas un score nul."
        )
    cumuls = dict(etat.cumuls)
    compares: dict[Participant, int] = {}
    for participant in etat.en_lice:
        de_la_manche = scores[participant]
        cumuls[participant] = cumuls.get(participant, 0) + de_la_manche
        compares[participant] = (
            cumuls[participant] if etat.configuration.cumul_des_manches else de_la_manche
        )
    plus_faible = min(compares.values())
    a_egalite = tuple(
        participant for participant in etat.en_lice if compares[participant] == plus_faible
    )
    manche = etat.manche + 1
    cumuls_tries = tuple((participant, cumuls[participant]) for participant in etat.en_lice)
    if len(a_egalite) > 1:
        # Égalité au plus faible → barrage (§8.2). L'état **n'avance pas** : la manche est jouée,
        # mais son issue reste suspendue tant que le barrage n'a pas désigné le sortant. Faire
        # avancer `manche` ici ferait croire qu'un tour de plus a été tiré.
        return IssueManche(
            etat=EtatBigShootOff(
                configuration=etat.configuration,
                en_lice=etat.en_lice,
                rangs=etat.rangs,
                manche=etat.manche,
                cumuls=cumuls_tries if etat.configuration.cumul_des_manches else etat.cumuls,
                barrage_en_cours=a_egalite,
            ),
            barrage_entre=a_egalite,
        )
    return _eliminer(etat, a_egalite[0], manche, cumuls_tries)


def eliminer_apres_barrage(etat: EtatBigShootOff, perdant_du_barrage: Participant) -> IssueManche:
    """Conclut une manche que l'égalité avait suspendue, une fois le barrage tiré (§8.2).

    Le `perdant_du_barrage` est celui que `resoudre_barrage` a désigné (`ResultatBarrage.perdant`
    du groupe correspondant) : le moteur du BSO ne rejoue pas le barrage, il en applique le verdict.
    Séparer les deux est ce qui permet au barrage d'être réutilisé tel quel par les poules et par un
    duel nul.

    ⚠️ **Deux vérifications, et aucune n'est superflue** : il faut qu'une manche soit réellement
    **suspendue** (sinon on éliminerait quelqu'un hors de toute manche, en lui décernant un rang),
    et que le sortant fasse partie des **ex æquo** de ce barrage (sinon le verdict d'un barrage
    servirait à éliminer un tiers). Sans elles, la couture BSO ↔ barrage laisse au service une
    liberté qu'aucune règle ne lui donne.
    """
    if not etat.barrage_en_cours:
        raise ConfigurationBigShootOffInvalide(
            "Aucun barrage n'est en attente : ce Big Shoot Off n'a pas de manche suspendue."
        )
    if perdant_du_barrage not in etat.barrage_en_cours:
        raise ConfigurationBigShootOffInvalide(
            "Le perdant désigné ne faisait pas partie des ex æquo de ce barrage."
        )
    return _eliminer(etat, perdant_du_barrage, etat.manche + 1, etat.cumuls)


def _eliminer(
    etat: EtatBigShootOff,
    sortant: Participant,
    manche: int,
    cumuls: tuple[tuple[Participant, int], ...],
) -> IssueManche:
    """Retire `sortant` de la lice et lui décerne le dernier rang encore disponible."""
    rang = len(etat.en_lice)
    en_lice = tuple(participant for participant in etat.en_lice if participant != sortant)
    suivant = EtatBigShootOff(
        configuration=etat.configuration,
        en_lice=en_lice,
        rangs=((sortant, rang), *etat.rangs),
        manche=manche,
        cumuls=tuple((p, s) for p, s in cumuls if p in en_lice),
        # La manche est conclue : le barrage éventuel ne l'est plus « en cours ».
        barrage_en_cours=(),
    )
    return IssueManche(etat=suivant, elimine=sortant, rang_attribue=rang)
