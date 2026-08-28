"""**Big Shoot Off** — type de phase à N participants, pas un barème de duel (ADR-0062).

Deux barrages : à la barre (toujours, §8.2, seuls les ex æquo de la frontière tirent) et entre
sortants (au choix — un barrage immobilise le pas de tir).

⚠️ **`eliminations` est ÉCRITE par l'organisateur, pas déduite** : rien n'impose qu'elle décroisse.
Jamais refusée, elle s'**écourte** — un format se réutilise sur des effectifs inconnus (règle 2).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from domain.erreurs import ConfigurationBigShootOffInvalide, ScoreDeMancheManquant
from domain.participant import Participant

_Cle = tuple[int, int]
"""La clé de comparaison d'un archer dans la manche courante : (score comparé, rang de départage).

Le second terme vaut 0 tant qu'aucun barrage n'a tranché, si bien qu'il est **neutre** dans le cas
courant. C'est lui qui permet à `_conclure` d'être rejouée à l'identique après un barrage : le
verdict n'écrase pas le score, il ne fait que départager ceux qui le partagent — un 21 ne peut donc
jamais passer sous un 18 parce qu'un barrage l'a désigné."""


@dataclass(frozen=True)
class ConfigurationBigShootOff:
    """Ce que l'organisateur règle — **une case par manche**, plus le format du tir.

    `eliminations` porte le nombre de sortants **de chaque manche**, sans valeur par défaut : une
    liste vide décrirait une phase sans élimination, donc un échauffement. « Pas encore réglé » se
    dit `Phase.big_shoot_off is None`. ⚠️ **Aucune validation ne dépend de l'effectif ici**, et
    c'est ce qui rend le format réutilisable — l'ajustement se fait à la lecture (`paliers_pour`)
    et au jeu, jamais par un refus.
    """

    eliminations: tuple[int, ...]
    volees: int = 1
    fleches_par_volee: int = 3
    cumul_des_manches: bool = False
    departage_les_sortants: bool = False
    """Faire tirer un barrage entre **éliminés** à égalité, pour leur donner des rangs distincts.

    Demandé par le commanditaire le 14/08/2026. Sans lui, deux sortants au même score **partagent**
    leur rang : leur égalité ne change rien à qui continue, elle ne décide que d'un numéro. Avec
    lui, le classement final est complet, au prix de barrages sans effet sur le cours du jeu."""

    def __post_init__(self) -> None:
        if self.volees < 1:
            raise ConfigurationBigShootOffInvalide(
                f"Une manche compte au moins une volée (reçu {self.volees})."
            )
        if self.fleches_par_volee < 1:
            raise ConfigurationBigShootOffInvalide(
                f"Une volée compte au moins une flèche (reçu {self.fleches_par_volee})."
            )
        if not self.eliminations:
            raise ConfigurationBigShootOffInvalide(
                "Un Big Shoot Off élimine à chaque manche : dites combien d'archers sortent au "
                "premier tour. Une phase qui n'élimine personne est un échauffement."
            )
        if any(quota < 1 for quota in self.eliminations):
            raise ConfigurationBigShootOffInvalide(
                "Une manche qui n'élimine personne se ferait tirer pour rien : retirez la case "
                f"plutôt que d'y mettre zéro (reçu {self.eliminations})."
            )

    @property
    def fleches_par_manche(self) -> int:
        """Combien de flèches chaque archer tire à chaque manche (V volées de F flèches)."""
        return self.volees * self.fleches_par_volee

    def paliers_pour(self, effectif: int) -> tuple[int, ...]:
        """Ce qu'il **reste** après chaque manche réellement jouable, sur cet effectif.

        La projection que l'atelier affiche sous la fiche de réglages — patron `RepartitionPoules`
        : « avec vos 12 inscrits : 12 → 8 → 6 → 5 ». L'organisateur voit que sa dernière case ne
        servira pas **avant** de composer. La liste s'arrête à la première manche qui viderait la
        lice : sortir 2 archers sur 2 ne laisserait personne.
        """
        paliers: list[int] = []
        restant = effectif
        for quota in self.eliminations:
            if restant - quota < 1:
                break
            restant -= quota
            paliers.append(restant)
        return tuple(paliers)

    def restants_pour(self, effectif: int) -> int:
        """Combien d'archers survivent — le **K dérivé**, qui n'est plus un paramètre."""
        paliers = self.paliers_pour(effectif)
        return paliers[-1] if paliers else effectif


@dataclass(frozen=True)
class EtatBigShootOff:
    """L'état d'un Big Shoot Off entre deux manches — **immuable**, comme tout agrégat du domaine.

    `en_lice` est ordonné et ne sert qu'à l'affichage ; `rangs` associe à chaque **éliminé** le rang
    qu'il emporte, trié par rang croissant. Un BSO terminé a `rangs` complet.
    """

    configuration: ConfigurationBigShootOff
    en_lice: tuple[Participant, ...]
    rangs: tuple[tuple[Participant, int], ...] = ()
    manche: int = 0
    cumuls: tuple[tuple[Participant, int], ...] = ()
    """Scores cumulés depuis le début — vides et inutilisés quand `cumul_des_manches` est faux."""

    barrage_en_cours: tuple[Participant, ...] = ()
    """Les ex æquo dont le barrage n'est pas encore tranché.

    ⚠️ **Porté par l'état, pas seulement par l'issue de la manche** — sans quoi la couture avec
    `domain/barrage.py` n'est pas praticable : `eliminer_apres_barrage` ne pourrait vérifier ni
    qu'une manche est réellement suspendue, ni que le verdict porte sur les bons archers. Un service
    pourrait alors éliminer n'importe qui, à n'importe quel moment, et lui décerner un rang."""

    places_au_barrage: int = 0
    """Combien des ex æquo ci-dessus sortent réellement.

    Distingue les **deux** barrages du format : à la barre, il est strictement inférieur au nombre
    d'ex æquo (trois archers à 22 pour une seule place) ; entre sortants, il leur est **égal** — ils
    sortent tous, le barrage ne fait qu'ordonner leurs rangs."""

    scores_suspendus: tuple[tuple[Participant, int], ...] = ()
    """Les scores comparés de la manche suspendue, mémorisés pour pouvoir la conclure.

    ⚠️ **C'est ce champ qui rend la reprise honnête.** Sans lui, `eliminer_apres_barrage` devrait
    deviner qui sortait *en plus* des ex æquo — or, dès qu'une manche élimine plusieurs archers, des
    sortants **certains** coexistent avec l'égalité de la barre. Les recalculer depuis les cumuls
    serait faux en mode remise à zéro, où le score de la manche n'est stocké nulle part ailleurs."""

    departages_acquis: tuple[tuple[Participant, int], ...] = ()
    """Les verdicts de barrage déjà rendus **dans la manche courante**, par archer.

    Une manche peut demander plusieurs barrages successifs (l'égalité à la barre, puis, si
    l'organisateur l'a réglé, celle des sortants). Chaque verdict s'ajoute ici et la conclusion est
    rejouée à l'identique : c'est ce qui évite d'écrire un chemin de reprise distinct par cas."""

    @property
    def quota_de_la_manche(self) -> int | None:
        """Combien d'archers la **prochaine** manche élimine, ou `None` si elle ne se joue pas.

        Deux raisons de ne pas se jouer, et elles disent la même chose : la liste de l'organisateur
        est épuisée, ou la manche viderait le pas de tir. Les réunir ici est ce qui permet à
        `est_termine` d'être une lecture et non une règle de plus.
        """
        eliminations = self.configuration.eliminations
        if self.manche >= len(eliminations):
            return None
        quota = eliminations[self.manche]
        return quota if len(self.en_lice) - quota >= 1 else None

    @property
    def est_termine(self) -> bool:
        """La phase s'arrête quand plus aucune manche n'est possible (arbitrage du 14/08/2026)."""
        return self.quota_de_la_manche is None

    def classement(self) -> tuple[tuple[Participant, int], ...]:
        """Le classement complet : les restants d'abord, puis les éliminés par rang croissant.

        Les **restants partagent le rang 1** : la règle ne prévoit rien pour les départager entre
        eux — c'est le principe même d'un « jusqu'aux derniers ». Leur imposer un ordre serait
        inventer un critère (le score de la dernière manche ?) que le commanditaire n'a pas donné.
        """
        tetes = tuple((participant, 1) for participant in self.en_lice)
        return tetes + self.rangs


@dataclass(frozen=True)
class IssueManche:
    """Ce qu'une manche produit : qui sort et à quel rang — ou l'égalité qui la suspend.

    `barrage_entre` n'est pas vide quand une égalité empêche de conclure : la manche **ne peut
    pas** se terminer, il faut faire tirer (§8.2), et l'état renvoyé est alors inchangé quant à la
    lice — on ne devine pas un sortant. `elimines` et `rangs_attribues` sont ordonnés du **plus
    faible au plus fort**, donc du rang le plus bas au plus haut.
    """

    etat: EtatBigShootOff
    elimines: tuple[Participant, ...] = ()
    rangs_attribues: tuple[tuple[Participant, int], ...] = ()
    barrage_entre: tuple[Participant, ...] = ()
    places_au_barrage: int = 0


def demarrer(
    participants: Sequence[Participant], configuration: ConfigurationBigShootOff
) -> EtatBigShootOff:
    """Ouvre un Big Shoot Off sur les `participants` reçus de la phase source.

    ⚠️ **Ne refuse plus rien** (élargissement du 14/08/2026). L'ancien contrôle `K >= N` n'a plus
    d'objet : K n'est plus un paramètre à confronter à l'effectif, il est ce que les éliminations
    laissent. Un effectif trop mince pour la première manche donne simplement un BSO immédiatement
    terminé, que l'atelier annonce par `paliers_pour` **avant** qu'on y arrive.
    """
    return EtatBigShootOff(
        configuration=configuration,
        en_lice=tuple(participants),
        cumuls=tuple((participant, 0) for participant in participants),
    )


def jouer_manche(etat: EtatBigShootOff, scores: Mapping[Participant, int]) -> IssueManche:
    """Applique une manche : **les plus faibles sortent**, et prennent les derniers rangs.

    En mode cumul, le moteur additionne les manches précédentes avant de comparer ; en remise à
    zéro (le défaut), il compare la manche seule. Les rangs descendent depuis `len(en_lice)` — l'«
    ordre inverse de sortie » de l'arbitrage du 31/07, généralisé aux sorties multiples le 14/08.
    ⚠️ Un score **manquant** est refusé plutôt que traité comme un zéro : c'est une saisie
    incomplète, et l'éliminer sur une donnée absente est l'erreur qu'on ne voit qu'après coup.
    """
    if etat.est_termine:
        raise ConfigurationBigShootOffInvalide(
            "Ce Big Shoot Off est terminé : plus aucune manche ne peut se jouer sans vider le pas "
            "de tir."
        )
    if etat.barrage_en_cours:
        # ⚠️ **Le garde-fou de l'autre porte.** `eliminer_apres_barrage` vérifiait déjà qu'une
        # manche est suspendue ; `jouer_manche` ne vérifiait rien, donc on pouvait enjamber un
        # barrage en cours en rejouant une manche — le leader s'y faisait éliminer et l'égalité
        # était oubliée sans trace. Fermer une porte et laisser l'autre ouverte ne ferme rien.
        #
        # ⚠️ Cette note affirmait que les scores de la manche suspendue étaient « déjà repliés dans
        # `cumuls`, donc comptés deux fois ». C'est l'inverse : `_suspendre` ne replie rien, ils
        # étaient *perdus* — le diagnostic faux a directement produit un bug de plus.
        raise ConfigurationBigShootOffInvalide(
            "Un barrage est en attente entre "
            f"{len(etat.barrage_en_cours)} archers : il doit être tranché avant la manche suivante."
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
        cumuls[participant] = cumuls.get(participant, 0) + scores[participant]
        compares[participant] = (
            cumuls[participant] if etat.configuration.cumul_des_manches else scores[participant]
        )
    cumuls_tries = tuple((participant, cumuls[participant]) for participant in etat.en_lice)
    return _conclure(etat, compares, departages={}, cumuls=cumuls_tries)


def eliminer_apres_barrage(etat: EtatBigShootOff, ordre: Sequence[Participant]) -> IssueManche:
    """Conclut une manche que l'égalité avait suspendue, une fois le barrage tiré (§8.2).

    `ordre` range les ex æquo **du plus faible au plus fort** : le moteur du BSO ne rejoue pas le
    barrage, il en applique le verdict — ce qui permet au barrage d'être réutilisé tel quel par les
    poules et par un duel nul. ⚠️ **Le verdict départage, il ne réordonne pas** : il n'entre qu'en
    second terme, derrière le score de la manche. ⚠️ Deux vérifications, aucune superflue — la
    manche doit être **suspendue**, et le verdict porter **exactement** sur ses ex æquo.
    """
    if not etat.barrage_en_cours:
        raise ConfigurationBigShootOffInvalide(
            "Aucun barrage n'est en attente : ce Big Shoot Off n'a pas de manche suspendue."
        )
    if sorted(ordre, key=_identite) != sorted(etat.barrage_en_cours, key=_identite):
        raise ConfigurationBigShootOffInvalide(
            "Le verdict du barrage doit porter exactement sur les ex æquo qu'il départage : "
            f"{len(etat.barrage_en_cours)} archers attendus, {len(tuple(ordre))} reçus."
        )
    departages = dict(etat.departages_acquis)
    departages.update({participant: rang for rang, participant in enumerate(ordre)})
    return _conclure(
        etat,
        compares=dict(etat.scores_suspendus),
        departages=departages,
        cumuls=_cumuls_de_la_manche_suspendue(etat),
    )


def _cumuls_de_la_manche_suspendue(
    etat: EtatBigShootOff,
) -> tuple[tuple[Participant, int], ...]:
    """Les cumuls **manche comprise**, à replier au moment de conclure un barrage.

    ⚠️ **C'est ici que se jouait une inversion de vainqueur.** `_suspendre` ne replie délibérément
    pas les cumuls — ce qui permet de ressaisir une manche suspendue sans double comptage — mais
    `eliminer_apres_barrage` repassait ensuite ces cumuls *d'avant la manche*, si bien que le score
    tranché au barrage disparaissait du total. Le repli diffère selon le mode : en **cumul**
    `scores_suspendus` porte déjà le total ; en **remise à zéro** il ne porte que la manche.
    """
    suspendus = dict(etat.scores_suspendus)
    anciens = dict(etat.cumuls)
    if etat.configuration.cumul_des_manches:
        return tuple((participant, suspendus[participant]) for participant in etat.en_lice)
    return tuple(
        (participant, anciens.get(participant, 0) + suspendus[participant])
        for participant in etat.en_lice
    )


def _conclure(
    etat: EtatBigShootOff,
    compares: Mapping[Participant, int],
    departages: Mapping[Participant, int],
    cumuls: tuple[tuple[Participant, int], ...],
) -> IssueManche:
    """Le tronc commun : puis-je conclure cette manche, ou dois-je faire tirer ?

    Appelée à l'identique par `jouer_manche` et par `eliminer_apres_barrage` — c'est ce qui évite un
    chemin de reprise distinct par cas de figure, et ce qui garantit qu'un barrage ne change rien
    d'autre que ce qu'il a départagé.
    """
    quota = etat.quota_de_la_manche
    assert quota is not None, "Les appelants ont déjà refusé un Big Shoot Off terminé."
    cles = {
        participant: (compares[participant], departages.get(participant, 0))
        for participant in etat.en_lice
    }
    ordonnes = sorted(etat.en_lice, key=lambda participant: cles[participant])

    # 1. L'égalité **à la barre** : elle décide qui continue, donc elle se tire toujours.
    barre = cles[ordonnes[quota - 1]]
    certains = [participant for participant in etat.en_lice if cles[participant] < barre]
    a_la_barre = [participant for participant in etat.en_lice if cles[participant] == barre]
    places = quota - len(certains)
    if len(a_la_barre) > places:
        return _suspendre(etat, compares, departages, tuple(a_la_barre), places)

    sortants = ordonnes[:quota]
    # 2. L'égalité **entre sortants** : elle ne décide que d'un numéro de rang, donc elle ne se tire
    #    que si l'organisateur l'a réglé. On ne prend que le **premier** groupe encore à égalité ;
    #    s'il en reste un autre, la conclusion rejouée le trouvera au tour suivant.
    if etat.configuration.departage_les_sortants:
        for participant in sortants:
            groupe = [autre for autre in sortants if cles[autre] == cles[participant]]
            if len(groupe) > 1:
                return _suspendre(etat, compares, departages, tuple(groupe), len(groupe))

    return _eliminer(etat, sortants, cles, cumuls)


def _suspendre(
    etat: EtatBigShootOff,
    compares: Mapping[Participant, int],
    departages: Mapping[Participant, int],
    ex_aequo: tuple[Participant, ...],
    places: int,
) -> IssueManche:
    """Fige la manche en attendant un barrage — **rien ne bouge** dans la lice.

    `manche` n'avance pas : la manche est tirée, mais son issue reste suspendue tant que le barrage
    n'a pas parlé. La faire avancer ici ferait croire qu'un tour de plus a été tiré.

    Les cumuls ne sont **pas** repliés non plus. C'est ce qui permet à `jouer_manche` d'être rejouée
    sans double comptage si la manche suspendue devait être ressaisie.
    """
    return IssueManche(
        etat=EtatBigShootOff(
            configuration=etat.configuration,
            en_lice=etat.en_lice,
            rangs=etat.rangs,
            manche=etat.manche,
            cumuls=etat.cumuls,
            barrage_en_cours=ex_aequo,
            places_au_barrage=places,
            scores_suspendus=tuple(
                (participant, compares[participant]) for participant in etat.en_lice
            ),
            departages_acquis=tuple(departages.items()),
        ),
        barrage_entre=ex_aequo,
        places_au_barrage=places,
    )


def _eliminer(
    etat: EtatBigShootOff,
    sortants: Sequence[Participant],
    cles: Mapping[Participant, _Cle],
    cumuls: tuple[tuple[Participant, int], ...],
) -> IssueManche:
    """Retire les `sortants` de la lice et leur décerne les derniers rangs disponibles.

    Les rangs descendent depuis `len(en_lice)`. Deux sortants de clé **identique** partagent leur
    rang au sens usuel du classement sportif (« 1224 ») : chacun prend `1 + le nombre d'archers
    strictement meilleurs`, les rangs sautés restant vacants **après** le groupe — trace d'un
    départage qui n'a pas eu lieu. ⚠️ Le sens du partage a été arbitré le 15/08/2026 et reversé au
    référentiel §10.1 ; c'est la convention que `classement()` applique déjà aux rescapés.
    """
    depart = len(etat.en_lice)
    attribues: list[tuple[Participant, int]] = []
    for sortant in sortants:
        # Le rang du **dernier** membre du groupe d'ex æquo, pas du premier : `sortants` est trié du
        # plus faible au plus fort, donc le dernier ex æquo est celui qui a le moins d'archers
        # devant lui — c'est lui qui porte le rang « 1224 » que tout le groupe partage.
        dernier = max(
            autre_index
            for autre_index, autre in enumerate(sortants)
            if cles[autre] == cles[sortant]
        )
        attribues.append((sortant, depart - dernier))
    partants = set(sortants)
    en_lice = tuple(participant for participant in etat.en_lice if participant not in partants)
    suivant = EtatBigShootOff(
        configuration=etat.configuration,
        en_lice=en_lice,
        # `rangs` reste trié par rang croissant : les nouveaux sont inversés (le meilleur d'abord)
        # avant d'être empilés, sinon `classement()` rendrait une liste en dents de scie.
        rangs=(*reversed(attribues), *etat.rangs),
        manche=etat.manche + 1,
        cumuls=tuple((p, s) for p, s in cumuls if p in en_lice),
        # La manche est conclue : le barrage éventuel ne l'est plus « en cours », et les verdicts
        # rendus ne valent que pour elle.
        barrage_en_cours=(),
        places_au_barrage=0,
        scores_suspendus=(),
        departages_acquis=(),
    )
    return IssueManche(
        etat=suivant,
        elimines=tuple(sortants),
        rangs_attribues=tuple(attribues),
    )


def _identite(participant: Participant) -> tuple[str, int]:
    """Une clé de tri **totale** et stable pour comparer deux ensembles de participants.

    `Participant` n'est pas ordonnable (c'est un agrégat, pas un scalaire) : trier sur son genre et
    sa référence est ce qui permet de comparer « les ex æquo attendus » et « le verdict reçu » comme
    des ensembles, sans exiger d'eux le même ordre — c'est justement l'ordre qui est le verdict.
    """
    return (participant.genre.value, participant.ref_id)
