"""Moteur de **poules** — groupes se rencontrant en round-robin (E05US015, [ADR-0062]).

Règle **fournie par le commanditaire le 31/07/2026** et reproduite au [référentiel §10.1] : elle
n'est écrite nulle part ailleurs (ni au règlement FFTA salle, ni dans aucun document du projet).

> **Principe** — les archers sont regroupés en poules et se rencontrent dans leur groupe.
> **Fonctionnement** — chaque archer rencontre tout ou partie des autres archers de sa poule ; un
> barème de points attribue les victoires, nuls et défaites ; le classement de poule détermine les
> qualifiés pour la phase suivante.
> **Départage** — points de match, différence de sets, différence de score, nombre de 10 / 9,
> barrage si nécessaire.

**Ce module ne fait tirer personne.** Il produit la **structure** (qui est dans quelle poule, qui
rencontre qui) et lit le **classement** à partir de résultats déjà tranchés. Le tir lui-même est un
duel ordinaire (`domain/duel.py`, pavé de saisie d'E04US013) : une poule n'invente pas une façon de
tirer, seulement une façon d'apparier et de compter.

**Ce qui est de la configuration, pas du code** (règle 2). « Tout ou partie des autres archers »
est un **réglage** (`rencontres_par_archer`), pas deux moteurs ; le barème de points, le nombre de
poules et le nombre de qualifiés en sont d'autres. Ce module ne connaît aucun format en dur.

**Arbitrages du 31/07/2026** (reversés dans `stories/E05-moteur-phases.md`, cf. règle 9) :
composition **serpent** depuis le classement source ; **round-robin complet** par défaut ; barème
**3 / 1 / 0** (victoire / nul / défaite) ; **aucun défaut** imposé au nombre de qualifiés — c'est
l'organisateur qui le saisit, parce qu'il dépend de ce que la phase suivante attend, pas du format
de poule.

Domaine **pur** : aucun framework, aucune autre couche (règle 1).

[référentiel §10.1]: ../../docs/referentiel-ffta.md
[ADR-0062]: ../../docs/adr/0062-catalogue-de-types-de-phase.md
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from domain.erreurs import BarrageRequisAvantQualification, ConfigurationPouleInvalide
from domain.participant import Participant
from domain.politiques import DecompteDepartage, Tiebreak, TiebreakPoules


@dataclass(frozen=True)
class BaremePoule:
    """Ce que rapporte une rencontre de poule — « un barème de points attribue les victoires, nuls
    et défaites » (règle du commanditaire).

    Défaut **3 / 1 / 0**, arbitré le 31/07/2026. La première proposition était 2 / 1 / 0 par
    cohérence avec les points de set FFTA (2 la manche gagnée, 1-1 l'égalité) ; le commanditaire a
    tranché pour 3 / 1 / 0, qui **écarte davantage** un vainqueur d'un archer qui accumule les nuls.
    C'est un réglage, pas une règle : il se change sans toucher au moteur.

    L'invariant `victoire >= nul >= defaite` n'est pas une coquetterie : un barème qui récompense
    la défaite produirait un classement où perdre fait monter, et le moteur n'a aucun moyen de s'en
    apercevoir plus tard — le classement resterait parfaitement cohérent, simplement absurde.
    """

    victoire: int = 3
    nul: int = 1
    defaite: int = 0

    def __post_init__(self) -> None:
        if self.defaite < 0:
            raise ConfigurationPouleInvalide(
                f"Une défaite ne retire pas de points (reçu {self.defaite})."
            )
        if not self.victoire >= self.nul >= self.defaite:
            raise ConfigurationPouleInvalide(
                f"Le barème doit récompenser au moins autant la victoire que le nul, et le nul que "
                f"la défaite (reçu {self.victoire} / {self.nul} / {self.defaite})."
            )

    def points(self, sets_pour: int, sets_contre: int) -> int:
        """Les points de match qu'une rencontre rapporte au camp qui a fait `sets_pour`."""
        if sets_pour > sets_contre:
            return self.victoire
        if sets_pour < sets_contre:
            return self.defaite
        return self.nul


@dataclass(frozen=True)
class ConfigurationPoules:
    """Le réglage d'une phase de poules — tout ce qui, du format, est de la configuration.

    `nb_qualifies` vaut `None` par défaut **délibérément** : le CA proposait 2 par poule, le
    commanditaire a demandé le 31/07/2026 qu'aucune valeur ne soit pré-remplie. C'est défendable
    au-delà de la préférence : le nombre de qualifiés est dicté par ce que la **phase suivante**
    attend (un tableau de 16 alimenté par 8 poules en prend 2, par 4 poules en prend 4), donc le
    déduire du format de poule serait deviner à la place de l'organisateur. `None` signifie « la
    poule classe, elle ne qualifie pas » — la sélection se fait alors par un prélèvement de la
    phase avale.

    `rencontres_par_archer` à `None` = **round-robin complet**, la lecture par défaut de « tout ou
    partie des autres archers ».
    """

    nb_poules: int
    bareme: BaremePoule = field(default_factory=BaremePoule)
    nb_qualifies: int | None = None
    rencontres_par_archer: int | None = None

    def __post_init__(self) -> None:
        if self.nb_poules < 1:
            raise ConfigurationPouleInvalide(
                f"Une phase de poules en compte au moins une (reçu {self.nb_poules})."
            )
        if self.nb_qualifies is not None and self.nb_qualifies < 1:
            raise ConfigurationPouleInvalide(
                f"Le nombre de qualifiés par poule est au moins 1, ou non déclaré "
                f"(reçu {self.nb_qualifies})."
            )
        if self.rencontres_par_archer is not None and self.rencontres_par_archer < 1:
            raise ConfigurationPouleInvalide(
                f"Un archer dispute au moins une rencontre, ou toutes si le nombre n'est pas "
                f"déclaré (reçu {self.rencontres_par_archer})."
            )


@dataclass(frozen=True)
class ReglageDePoules:
    """Ce que l'organisateur **règle à l'atelier**, avant que l'effectif soit connu (E05US023).

    **À ne pas confondre avec `ConfigurationPoules`**, et la distinction est tout le sujet :

    - `ReglageDePoules` porte une **taille visée** (« des poules de 4 »), connue dès la
      **composition** du déroulé, inscriptions encore ouvertes ;
    - `ConfigurationPoules` porte un **nombre de poules** (« 7 poules »), qui n'existe que le
      **jour J**, une fois l'effectif arrêté.

    Le déroulé se compose des semaines avant le tournoi : le nombre de poules n'y est **pas
    calculable**, il dépend du nombre d'inscrits. Stocker `nb_poules` dans la phase reviendrait à
    figer la répartition sur un effectif supposé — un tournoi réglé pour 32 et joué à 30 monterait
    8 poules dont deux à 3 archers, sans que rien ne le signale. C'est `pour_effectif` qui fait la
    conversion, au dernier moment et **en un seul endroit**.

    `nb_qualifies` porte aussi le **régime d'ex æquo** (arbitrage du 09/08/2026) : vide, la poule
    *classe* et tout ex æquo irréductible se départage ; renseigné, elle *qualifie* et seul un
    ex æquo tombant sur la barre justifie un barrage. Ce n'est pas un champ de plus — c'est la même
    information, seulement rendue explicite à l'écran plutôt que déduite d'un champ laissé vide.
    """

    taille_visee: int
    bareme: BaremePoule = field(default_factory=BaremePoule)
    nb_qualifies: int | None = None
    rencontres_par_archer: int | None = None
    departage_inter_poules: bool = False
    """Départager les archers d'un **même rang de poule** par leur décompte (§10.1, ADR-0083 §6).

    Le classement de phase range « par rang de poule d'abord » : sur `P` poules, les rangs `1..P`
    sont les vainqueurs. À l'intérieur de ce bloc, les archers sont **ex æquo par défaut** :
    comparer des décomptes obtenus contre des adversaires différents n'a de valeur qu'au besoin.

    L'option est **auto-régulée par ADR-0081** : sans elle, une phase avale qui prélève le bloc
    entier (« les rangs 1 à 4 » sur 4 poules) passe, et une qui le coupe (« les rangs 1 à 2 ») est
    refusée **et annoncée**. L'organisateur n'a donc à l'activer que quand l'outil le lui dit — au
    lieu de qualifier en silence sur un ordre d'affichage.

    ⚠️ Elle ne ferme **que** ce que le décompte sépare : deux décomptes identiques restent ex æquo,
    et un ex æquo *interne* à une poule reste irréductible quoi qu'on active
    (`domain/classement_de_poules.py`)."""

    def __post_init__(self) -> None:
        if self.taille_visee < 2:
            raise ConfigurationPouleInvalide(
                f"Une poule apparie au moins deux archers (taille visée reçue : "
                f"{self.taille_visee})."
            )
        if self.nb_qualifies is not None:
            if self.nb_qualifies < 1:
                raise ConfigurationPouleInvalide(
                    f"Le nombre de qualifiés par poule est au moins 1, ou non déclaré "
                    f"(reçu {self.nb_qualifies})."
                )
            # Contrôlé **ici** plutôt qu'au seul `qualifies_de_poule` : à l'atelier l'organisateur
            # corrige son réglage, en salle il serait bloqué devant une poule qu'on lui demande de
            # qualifier au-delà de son effectif. La borne est la taille **visée** — les poules
            # gonflées d'une unité en comptent une de plus, jamais une de moins.
            if self.nb_qualifies > self.taille_visee:
                raise ConfigurationPouleInvalide(
                    f"{self.nb_qualifies} qualifiés demandés dans des poules de "
                    f"{self.taille_visee}."
                )
        if self.rencontres_par_archer is not None and self.rencontres_par_archer < 1:
            raise ConfigurationPouleInvalide(
                f"Un archer dispute au moins une rencontre, ou toutes si le nombre n'est pas "
                f"déclaré (reçu {self.rencontres_par_archer})."
            )

    @property
    def produit_des_qualifies(self) -> bool:
        """La poule désigne un nombre de qualifiés pour la phase suivante."""
        return self.nb_qualifies is not None

    @property
    def produit_un_classement(self) -> bool:
        """La poule classe ses membres, et c'est son livrable — donc tout ex æquo se départage."""
        return self.nb_qualifies is None

    def pour_effectif(self, effectif: int) -> ConfigurationPoules:
        """La configuration que le moteur consomme, une fois l'effectif du jour connu."""
        return ConfigurationPoules(
            nb_poules=nb_poules_pour(effectif, self.taille_visee),
            bareme=self.bareme,
            nb_qualifies=self.nb_qualifies,
            rencontres_par_archer=self.rencontres_par_archer,
        )


def nb_poules_pour(effectif: int, taille_visee: int) -> int:
    """Combien de groupes former pour des poules « de `taille_visee` » (arbitrage du 09/08/2026).

    L'organisateur raisonne en **taille de poule**, pas en nombre de groupes : il demande « des
    poules de 4 », et c'est l'effectif du jour qui décide combien il y en aura. Cette fonction fait
    la conversion, et elle arrondit **vers le bas** :

    - 32 archers en poules de 4 → **8** poules de 4 ;
    - 30 archers en poules de 4 → **7** poules, que `composer_poules` remplira en cinq de 4 et deux
      de 5.

    **Pourquoi vers le bas.** Arrondir vers le haut donnerait 8 poules dont deux de 3 — le
    commanditaire l'a écarté explicitement : « il est possible pour répartir de faire quelques
    poules de 5 ». L'invariant retenu est donc *aucune poule ne compte moins que la taille
    demandée*, jamais l'inverse. C'est cohérent avec `composer_poules`, qui répartit au serpent et
    ne produit jamais plus d'une unité d'écart entre groupes.

    ⚠️ **Conséquence assumée** : sous le double de la taille visée, il ne reste qu'**une** poule —
    7 archers en poules de 4 donnent une poule de 7. Les deux invariants (« pas de poule sous la
    taille » et « pas plus d'une unité d'écart ») sont alors inconciliables, et on garde le premier.
    C'est pour ce cas que le CA exige que l'écran **montre** la répartition obtenue avant de la
    valider : l'organisateur voit la poule de 7 et corrige sa taille s'il n'en veut pas.
    """
    # ⚠️ **Erreurs typées, pas des `ValueError` nus** (règle 5, correctif de revue).
    #
    # Le second cas est **atteignable depuis le client** : `ServicePoules._configuration` appelle
    # `pour_effectif(len(participants))`, et une population vide est parfaitement licite — phase de
    # poules composée avant les inscriptions, ou source amont qui ne prélève encore rien. Un
    # `ValueError` n'étant ni `DomainError` ni `ApplicationError`, il tombait dans le filet
    # « erreur inattendue » de la frontière API et sortait en **500** — sur l'écran de réglage, sur
    # l'écran de saisie, et sur toute phase avale qui prélève dans des poules encore vides.
    if taille_visee < 2:
        raise ConfigurationPouleInvalide(
            f"Une poule apparie au moins deux archers (taille visée reçue : {taille_visee})."
        )
    if effectif < 1:
        raise ConfigurationPouleInvalide(
            f"Aucun archer à répartir en poules (effectif reçu : {effectif})."
        )
    return max(1, effectif // taille_visee)


def couloirs_occupes(effectif_de_poule: int) -> int:
    """Combien de **couloirs de tir** une poule occupe — son parallélisme, pas son effectif.

    **C'est l'arbitrage du 09/08/2026, et il n'est pas intuitif.** Une poule ne met pas tous ses
    membres sur la ligne en même temps : `rencontres_de_poule` apparie par la méthode du cercle,
    qui produit `effectif ÷ 2` rencontres par tour — à effectif **impair**, un membre se repose (le
    cercle tourne autour d'une place vide). Une poule de 5 ne dispute donc que **deux** rencontres
    simultanées, soit **quatre** archers sur la ligne : elle tient sur une seule cible de 4
    couloirs, exactement comme une poule de 4.

    Réserver un couloir par membre aurait fait déborder toute poule impaire sans raison, et décalé
    la salle entière d'un cran par poule. Les membres **tournent** sur le bloc : celui qui se repose
    change à chaque tour, ce qui est aussi la raison pour laquelle le plan place la **poule** et non
    l'archer (`domain/placement_par_bloc.py`, ADR-0083).

    Une poule de moins de deux membres n'apparie personne et n'occupe donc aucun couloir.
    """
    if effectif_de_poule < 2:
        return 0
    return 2 * (effectif_de_poule // 2)


@dataclass(frozen=True)
class Poule:
    """Un groupe et ses membres, dans l'ordre où la composition les y a placés."""

    numero: int
    membres: tuple[Participant, ...]


@dataclass(frozen=True)
class RencontrePoule:
    """Une rencontre à disputer : deux membres d'une même poule, à un tour donné.

    Le `tour` n'ordonne pas seulement l'affichage : il garantit qu'**aucun archer ne figure deux
    fois dans le même tour**, donc que les rencontres d'un tour peuvent se tirer *en parallèle* sur
    des cibles différentes. C'est ce qui rend une poule tenable en salle.
    """

    poule: int
    tour: int
    a: Participant
    b: Participant


@dataclass(frozen=True)
class ResultatRencontre:
    """L'issue **déjà tranchée** d'une rencontre, telle que le moteur la consomme.

    Le moteur de poule ne rejoue pas le duel : il reçoit ce que la saisie a produit. `sets_*`
    départage la rencontre (le vainqueur est celui qui a le plus de sets ; à égalité c'est un nul),
    `score_*` alimente la différence de score, `nb_dix_*` / `nb_neuf_*` les deux derniers critères
    du départage §10.1.

    ⚠️ En **cumul** (arc à poulies, qui ne joue pas en sets), la saisie reporte le total dans
    `score_*` et laisse les sets à 0 : la rencontre est alors un **nul** au sens des points de
    match. C'est une limite connue et **assumée ici** plutôt que devinée : décider qu'un duel au
    cumul vaut « victoire » demanderait de savoir que la phase se joue en cumul, information qui
    vit sur le barème de la phase (`BaremeDuel.mode`) et non sur le résultat. Le service qui
    assemble les résultats doit donc reporter la victoire dans `sets_*` (1-0) quand il travaille en
    cumul — c'est documenté dans `docs/fonctionnel/E05US015.md`.
    """

    a: Participant
    b: Participant
    sets_a: int
    sets_b: int
    score_a: int = 0
    score_b: int = 0
    nb_dix_a: int = 0
    nb_neuf_a: int = 0
    nb_dix_b: int = 0
    nb_neuf_b: int = 0


@dataclass(frozen=True)
class RangPoule:
    """Une ligne du classement de poule : son rang, le participant, et le décompte qui l'a placé.

    `ex_aequo` dit que ce rang est **partagé** — les cinq critères de §10.1 ont été épuisés sans
    départager. C'est là, et seulement là, qu'un barrage se justifie (« barrage si nécessaire ») :
    le moteur le **signale**, il ne le déclenche pas.
    """

    rang: int
    participant: Participant
    decompte: DecompteDepartage
    ex_aequo: bool = False


def composer_poules(
    participants: Sequence[Participant], configuration: ConfigurationPoules
) -> tuple[Poule, ...]:
    """Répartit les participants **classés** en poules, selon le **serpent** (arbitrage 31/07/2026).

    `participants` arrive **ordonné par rang** de la phase source (indice 0 = premier). Le serpent
    distribue 1→A, 2→B, 3→C, puis repart en sens inverse (4→C, 5→B, 6→A) : c'est ce qui équilibre
    la force des groupes, exactement comme le seeding serpent équilibre un arbre. Une distribution
    naïve (les 6 premiers dans la poule A) mettrait tous les favoris ensemble et en éliminerait la
    moitié au premier tour.

    Les poules peuvent être de **tailles inégales** d'une unité quand l'effectif ne divise pas —
    c'est inévitable et sans conséquence sur le classement, chaque poule étant classée séparément.
    """
    if configuration.nb_poules > len(participants):
        raise ConfigurationPouleInvalide(
            f"{configuration.nb_poules} poules pour {len(participants)} participants : "
            "une poule resterait vide."
        )
    groupes: list[list[Participant]] = [[] for _ in range(configuration.nb_poules)]
    for index, participant in enumerate(participants):
        passage, position = divmod(index, configuration.nb_poules)
        # Un passage sur deux se fait à l'envers : c'est tout le serpent.
        numero = position if passage % 2 == 0 else configuration.nb_poules - 1 - position
        groupes[numero].append(participant)
    return tuple(
        Poule(numero=numero + 1, membres=tuple(membres)) for numero, membres in enumerate(groupes)
    )


def rencontres_de_poule(
    poule: Poule, configuration: ConfigurationPoules
) -> tuple[RencontrePoule, ...]:
    """Les rencontres d'une poule, par tours, selon la **méthode du cercle**.

    On fixe un membre et on fait tourner les autres : à chaque tour, chacun rencontre un adversaire
    différent, et personne n'y figure deux fois. À effectif **impair**, un membre se repose à chaque
    tour (le cercle tourne autour d'une place vide) — sa rencontre n'est simplement pas produite.

    Pourquoi le cercle plutôt que « toutes les paires » : les paires seules ne disent pas **quand**
    se tirent les rencontres, or une poule de 6 tirée sur une cible doit s'organiser en 5 tours de 3
    matchs. Et surtout, le cercle est **déterministe** — ce que la règle 9 exige d'un moteur testé.

    `rencontres_par_archer` **tronque** le cercle à ses `k` premiers tours : c'est le « ou partie
    des autres archers » de la règle, obtenu sans second algorithme. Sauf pour `k = n-1`, qui est le
    round-robin complet exprimé en nombre : on y déroule le cercle **entier** (un tour de plus à
    effectif impair, celui du repos), sans quoi un seul membre disputerait ses `n-1` rencontres et
    tous les autres `n-2`.

    ⚠️ **Pour une troncature intermédiaire (`k < n-1`) à effectif impair, l'écart subsiste.** Un
    tour sur deux fait reposer quelqu'un ; sur `k` tours, les `k` archers qui se sont reposés ont
    disputé `k-1` rencontres et les autres `k`. L'écart est d'**une** rencontre, mais il fausse
    légèrement la comparaison des points de match. Deux façons honnêtes de l'éviter : composer des
    poules de taille **paire**, ou laisser le round-robin complet. On le signale plutôt que de le
    corriger en douce, parce qu'aucune correction n'est neutre — rallonger le cercle changerait le
    nombre de rencontres demandé.
    """
    membres = list(poule.membres)
    if len(membres) < 2:
        return ()
    # Place vide pour un effectif impair : le membre qui lui fait face se repose ce tour-là.
    roue: list[Participant | None] = list(membres)
    if len(roue) % 2 == 1:
        roue.append(None)
    nb_tours = len(roue) - 1
    if configuration.rencontres_par_archer is not None:
        # Le plafond est le nombre d'**adversaires** (`len(membres) - 1`), pas le nombre de tours du
        # cercle : à effectif impair le cercle compte un tour de plus que d'adversaires, et prendre
        # ce nombre-là ferait accepter une demande impossible à honorer.
        if configuration.rencontres_par_archer > len(membres) - 1:
            raise ConfigurationPouleInvalide(
                f"La poule {poule.numero} compte {len(membres)} membres : un archer n'y a que "
                f"{len(membres) - 1} adversaires possibles, pas "
                f"{configuration.rencontres_par_archer}."
            )
        nb_tours = configuration.rencontres_par_archer
        if configuration.rencontres_par_archer == len(membres) - 1:
            # Demander « autant de rencontres que d'adversaires », c'est demander le round-robin
            # complet : à effectif impair il faut alors le cercle **entier** (un tour de plus, celui
            # du repos), sinon quatre archers sur cinq en disputent une de moins que le cinquième.
            nb_tours = len(roue) - 1
    rencontres: list[RencontrePoule] = []
    for tour in range(nb_tours):
        # Rotation : le premier reste en place, les autres tournent d'un cran par tour.
        tete, *reste = roue
        tournes = [tete, *reste[-tour:], *reste[: len(reste) - tour]] if tour else list(roue)
        moitie = len(tournes) // 2
        for position in range(moitie):
            a = tournes[position]
            b = tournes[len(tournes) - 1 - position]
            if a is None or b is None:
                continue
            rencontres.append(RencontrePoule(poule=poule.numero, tour=tour + 1, a=a, b=b))
    return tuple(rencontres)


def classement_de_poule(
    poule: Poule,
    resultats: Iterable[ResultatRencontre],
    configuration: ConfigurationPoules,
    tiebreak: Tiebreak | None = None,
) -> tuple[RangPoule, ...]:
    """Classe les membres d'une poule à partir des rencontres tranchées (§10.1).

    Le `tiebreak` est **injecté** (règle 2) ; à défaut c'est `TiebreakPoules`, l'ordre à cinq
    critères de la règle. Deux membres que le comparateur ne sépare pas partagent le rang et sont
    marqués `ex_aequo` — c'est le moment du « barrage si nécessaire », que le moteur signale sans le
    décider (un comparateur pur ne fait pas tirer de flèches).

    ⚠️ Les résultats d'une rencontre **étrangère à la poule** sont ignorés en silence : le service
    passe volontiers l'ensemble des résultats de la phase, et filtrer ici évite de lui imposer un
    découpage préalable. En revanche, un membre **sans aucune rencontre** figure bien au classement
    (à 0 partout) : le faire disparaître serait pire — un archer présent doit apparaître.
    """
    comparateur: Tiebreak = tiebreak if tiebreak is not None else TiebreakPoules()
    membres = set(poule.membres)
    cumuls: dict[Participant, list[int]] = {
        membre: [0, 0, 0, 0, 0] for membre in poule.membres
    }  # points, diff sets, diff score, 10, 9
    vues: set[frozenset[Participant]] = set()
    for resultat in resultats:
        if resultat.a not in membres or resultat.b not in membres:
            continue
        if resultat.a == resultat.b:
            raise ConfigurationPouleInvalide(
                "Une rencontre de poule oppose deux membres distincts."
            )
        paire = frozenset((resultat.a, resultat.b))
        if paire in vues:
            # Sans ce contrôle, un double envoi du même résultat compterait les points deux fois et
            # le classement resterait parfaitement cohérent — simplement faux.
            raise ConfigurationPouleInvalide(
                f"La rencontre de la poule {poule.numero} entre ces deux membres est fournie deux "
                "fois : ses points seraient comptés en double."
            )
        vues.add(paire)
        # Une rencontre alimente les **deux** cumuls, symétriquement : on décrit le côté « A » puis
        # on relit le même tuple à l'envers, plutôt que d'écrire deux fois la même arithmétique.
        cotes = (
            (
                resultat.a,
                (resultat.sets_a, resultat.sets_b, resultat.score_a, resultat.score_b),
                (resultat.nb_dix_a, resultat.nb_neuf_a),
            ),
            (
                resultat.b,
                (resultat.sets_b, resultat.sets_a, resultat.score_b, resultat.score_a),
                (resultat.nb_dix_b, resultat.nb_neuf_b),
            ),
        )
        for participant, (sets_pour, sets_contre, score_pour, score_contre), (dix, neuf) in cotes:
            cumul = cumuls[participant]
            cumul[0] += configuration.bareme.points(sets_pour, sets_contre)
            cumul[1] += sets_pour - sets_contre
            cumul[2] += score_pour - score_contre
            cumul[3] += dix
            cumul[4] += neuf
    decomptes = {
        membre: DecompteDepartage(
            nb_dix=cumul[3],
            nb_neuf=cumul[4],
            points_match=cumul[0],
            diff_sets=cumul[1],
            diff_score=cumul[2],
        )
        for membre, cumul in cumuls.items()
    }
    # Tri stable : à décompte égal, l'ordre de composition (donc le rang source) départage
    # l'**affichage** sans créer de rangs distincts — même partage des rôles que `classement.py`.
    ordonnes = sorted(
        poule.membres,
        key=_ClefDeTri(decomptes, comparateur),
    )
    # DETTE-029 (docs/dette.md) : 3ᵉ écriture de « rang partagé à clé égale, avec sauts » dans le
    # domaine (`classement._ranger`, `poule.classement_de_poule`, `suisse.classement_suisse`), et
    # les trois divergent déjà. Remède proposé (fonction pure `attribuer_rangs`) en US dédiée.
    lignes: list[RangPoule] = []
    rang = 0
    precedent: Participant | None = None
    for index, membre in enumerate(ordonnes):
        partage = (
            precedent is not None
            and comparateur.departager(decomptes[precedent], decomptes[membre]) == 0
        )
        if not partage:
            rang = index + 1
        lignes.append(
            RangPoule(rang=rang, participant=membre, decompte=decomptes[membre], ex_aequo=partage)
        )
        precedent = membre
    return tuple(_marquer_ex_aequo(lignes))


def qualifies_de_poule(
    classement: Sequence[RangPoule], configuration: ConfigurationPoules
) -> tuple[Participant, ...]:
    """Les qualifiés d'une poule — les `nb_qualifies` premiers du classement.

    Renvoie `()` si la configuration n'en déclare aucun (« la poule classe, elle ne qualifie pas » :
    c'est alors la phase avale qui prélève ce qu'elle veut).

    ⚠️ **Un ex æquo qui chevauche la barre est refusé**, pas arbitré. Prendre « les deux premiers »
    quand les rangs 2 et 3 sont à égalité reviendrait à qualifier sur l'ordre d'affichage — c'est-à-
    dire sur le rang de qualification d'origine, qui n'a plus cours en poule. C'est précisément le
    « barrage si nécessaire » de la règle : il faut faire tirer, et le moteur le dit.
    """
    if configuration.nb_qualifies is None:
        return ()
    if configuration.nb_qualifies > len(classement):
        raise ConfigurationPouleInvalide(
            f"{configuration.nb_qualifies} qualifiés demandés dans une poule qui n'en classe que "
            f"{len(classement)}."
        )
    barre = configuration.nb_qualifies
    dernier_qualifie = classement[barre - 1]
    premier_elimine = classement[barre] if barre < len(classement) else None
    if premier_elimine is not None and premier_elimine.rang == dernier_qualifie.rang:
        raise BarrageRequisAvantQualification(
            f"Le rang {dernier_qualifie.rang} de la poule est partagé et tombe sur la barre de "
            "qualification : un barrage doit départager avant de qualifier."
        )
    return tuple(ligne.participant for ligne in classement[:barre])


class _ClefDeTri:
    """Clé de tri par comparateur injecté — `functools.cmp_to_key` écrit à la main.

    On n'importe pas `functools.cmp_to_key` pour deux lignes, mais surtout pour **typer** : sa
    version stdlib renvoie un `Any` que mypy strict refuserait de laisser passer sans `cast`
    (règle 4). Cette classe dit exactement ce qu'elle compare.
    """

    __slots__ = ("_comparateur", "_decomptes", "_participant")

    def __init__(
        self,
        decomptes: dict[Participant, DecompteDepartage],
        comparateur: Tiebreak,
        participant: Participant | None = None,
    ) -> None:
        self._decomptes = decomptes
        self._comparateur = comparateur
        self._participant = participant

    def __call__(self, participant: Participant) -> _ClefDeTri:
        return _ClefDeTri(self._decomptes, self._comparateur, participant)

    def __lt__(self, autre: _ClefDeTri) -> bool:
        # Pas d'`assert` : il disparaît sous `python -O`, et l'échec deviendrait alors un `KeyError`
        # opaque au milieu d'un `sorted`. Ici le message dit ce qui s'est passé.
        if self._participant is None or autre._participant is None:
            raise ConfigurationPouleInvalide(
                "Clé de tri incomplète : comparaison hors du contexte d'un classement de poule."
            )
        return (
            self._comparateur.departager(
                self._decomptes[self._participant], self._decomptes[autre._participant]
            )
            < 0
        )


def _marquer_ex_aequo(lignes: Sequence[RangPoule]) -> list[RangPoule]:
    """Propage `ex_aequo` au **premier** d'un groupe de rangs partagés.

    La boucle de classement ne marque que les suivants (elle compare chaque ligne à la précédente) ;
    or un ex æquo se lit sur **tout** le groupe, sans quoi l'affichage montrerait un rang 2 « seul »
    suivi d'un rang 2 « partagé ». Détail d'ergonomie, mais il fausserait la lecture du barrage.
    """
    marquees = list(lignes)
    for index, ligne in enumerate(marquees):
        if ligne.ex_aequo and index > 0 and not marquees[index - 1].ex_aequo:
            precedente = marquees[index - 1]
            marquees[index - 1] = RangPoule(
                rang=precedente.rang,
                participant=precedente.participant,
                decompte=precedente.decompte,
                ex_aequo=True,
            )
    return marquees
