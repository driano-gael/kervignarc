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

from domain.erreurs import ConfigurationPouleInvalide
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
    des autres archers » de la règle, obtenu sans second algorithme.

    ⚠️ **À effectif impair, une troncature ne donne pas le même nombre de rencontres à tout le
    monde.** Un tour sur deux fait reposer quelqu'un ; sur `k` tours, les `k` archers qui se sont
    reposés ont disputé `k-1` rencontres et les autres `k`. L'écart est d'**une** rencontre au plus,
    mais il est réel et il fausse légèrement la comparaison des points de match. Deux façons
    honnêtes de l'éviter : composer des poules de taille **paire**, ou laisser le round-robin
    **complet** (où chacun rencontre tout le monde, quelle que soit la parité). On le signale ici
    plutôt que de le corriger en douce, parce qu'aucune correction n'est neutre — rallonger le
    cercle changerait le nombre de rencontres demandé.
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
    for resultat in resultats:
        if resultat.a not in membres or resultat.b not in membres:
            continue
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
        raise ConfigurationPouleInvalide(
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
        assert self._participant is not None and autre._participant is not None
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
