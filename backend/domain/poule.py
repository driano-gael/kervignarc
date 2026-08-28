"""Moteur de **poules** — la structure et le classement ; **personne n'y tire** (ADR-0062). Le tir
est un duel ordinaire ; « tout ou partie des autres archers » est un réglage, pas deux moteurs.
Arbitrages du 31/07/2026 (serpent, round-robin, barème 3/1/0) : `stories/E05`.

⚠️ **Aucun défaut n'est imposé au nombre de qualifiés** — il dépend de ce que la phase suivante
attend, pas du format de poule. C'est l'organisateur qui le saisit.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import Enum

from domain.erreurs import BarrageRequisAvantQualification, ConfigurationPouleInvalide
from domain.participant import Participant
from domain.politiques import DecompteDepartage, Tiebreak, TiebreakPoules


class ModeDeComposition(Enum):
    """Comment une phase de poules **répartit** son classement source en groupes (E05US029).

    Un **réglage**, pas un type de phase (règle 2) : les deux modes appellent le même moteur et ne
    diffèrent que sur *qui joue avec qui*. `SERPENT` (défaut) équilibre la force des groupes ;
    `PAR_NIVEAU` donne un groupe par tranche de rangs contiguë — le format club en cascade. ⚠️ Le
    mode décide aussi de la **lecture** du classement de phase : par niveau, lire « par rang de
    poule d'abord » annoncerait le vainqueur des 31ᵉ-36ᵉ 1ᵉʳ du tournoi. Indissociables.
    """

    SERPENT = "serpent"
    PAR_NIVEAU = "par_niveau"


@dataclass(frozen=True)
class BaremePoule:
    """Ce que rapporte une rencontre de poule — victoire, nul, défaite.

    Défaut **3 / 1 / 0**, arbitré le 31/07/2026 contre 2 / 1 / 0 : il **écarte davantage** un
    vainqueur d'un archer qui accumule les nuls. C'est un réglage, pas une règle. ⚠️ L'invariant
    `victoire >= nul >= defaite` n'est pas une coquetterie : un barème qui récompense la défaite
    produirait un classement parfaitement cohérent où perdre fait monter.
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

    `nb_qualifies` vaut `None` **délibérément** : le nombre de qualifiés est dicté par ce que la
    phase **suivante** attend, donc le déduire du format de poule serait deviner à la place de
    l'organisateur. `None` = « la poule classe, elle ne qualifie pas », la sélection se faisant par
    un prélèvement de la phase avale. `rencontres_par_archer` à `None` = round-robin complet.
    """

    nb_poules: int
    bareme: BaremePoule = field(default_factory=BaremePoule)
    nb_qualifies: int | None = None
    rencontres_par_archer: int | None = None
    mode: ModeDeComposition = ModeDeComposition.SERPENT
    """Comment répartir le classement source en groupes (E05US029) — serpent par défaut."""

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
        # ⚠️ **Ce n'est pas une duplication d'invariant, c'est l'invariant DE CET OBJET.**
        # `ConfigurationPoules` porte elle-même `nb_qualifies` **et** `mode` : un value object qui
        # refuse son propre état incohérent est à sa place, et c'est `nb_qualifies` d'ici que lit
        # `qualifies_de_poule`. Le réglage le redouble uniquement pour ajouter le **conseil de
        # remédiation** (« faites prélever des groupes entiers »), qui n'aurait aucun sens ici.
        if self.nb_qualifies is not None and self.mode is ModeDeComposition.PAR_NIVEAU:
            raise ConfigurationPouleInvalide(
                "Des poules de niveau ne désignent pas un nombre de qualifiés par poule : chaque "
                "groupe dispute sa propre tranche de rangs."
            )


@dataclass(frozen=True)
class ReglageDePoules:
    """Ce que l'organisateur **règle à l'atelier**, avant que l'effectif soit connu (E05US023).

    ⚠️ **À ne pas confondre avec `ConfigurationPoules`** : celui-ci porte une **taille visée**,
    connue dès la composition ; celle-là un **nombre de poules**, qui n'existe que le jour J.
    Stocker `nb_poules` figerait la répartition sur un effectif supposé — un tournoi réglé pour 32
    et joué à 30 monterait 8 poules dont deux à 3. `nb_qualifies` porte aussi le **régime d'ex
    æquo** : vide, la poule classe ; renseigné, elle qualifie.
    """

    taille_visee: int
    bareme: BaremePoule = field(default_factory=BaremePoule)
    nb_qualifies: int | None = None
    rencontres_par_archer: int | None = None
    departage_inter_poules: bool = False
    """Départager les archers d'un **même rang de poule** par leur décompte (§10.1, ADR-0083 §6).

    À l'intérieur d'un bloc de vainqueurs, les archers sont **ex æquo par défaut** : comparer des
    décomptes obtenus contre des adversaires différents n'a de valeur qu'au besoin. L'option est
    **auto-régulée par ADR-0081** — l'organisateur n'a à l'activer que quand une phase avale coupe
    un bloc et se voit refusée. ⚠️ Sans objet en mode `PAR_NIVEAU` (aucun bloc inter-poules) : le
    champ y est **ignoré** plutôt que refusé, pour ne pas opposer un 422 sur une case non touchée.
    """

    mode: ModeDeComposition = ModeDeComposition.SERPENT
    """Comment les groupes sont composés — serpent (défaut) ou par niveau (E05US029).

    Le défaut est le comportement de toujours : aucun tournoi déjà réglé ne change de composition
    du fait de cette US, et une configuration relue sans ce champ compose au serpent.
    """

    serpent_assume: bool = False
    """L'organisateur **assume** le serpent là où le niveau serait attendu (E05US029).

    Une phase de poules qui prélève dans des poules dispose déjà des niveaux : `domain/deroule.py`
    **refuse** de la composer au serpent, et cette case lève le refus — elle achète la trace que le
    choix a été posé, pas le droit de se tromper. ⚠️ Effacée à `False` sous `PAR_NIVEAU`,
    contrairement à `departage_inter_poules` seulement ignoré : une dérogation dormante
    **désarmerait un garde-fou** au retour au serpent.
    """

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
        # ⚠️ **« k qualifiés par poule » n'est pas exprimable en poules de niveau** (bloquant de
        # revue). Sous `SERPENT`, les `k` premiers de chaque groupe occupent les rangs `1..k*P` —
        # une fenêtre **contiguë** que la phase avale prélève par rangs. Sous `PAR_NIVEAU`, sur 4
        # groupes de 4 qualifiant 2, les qualifiés sont les rangs {1,2, 5,6, 9,10, 13,14} : un
        # **peigne** qu'aucun prélèvement par rangs ne désigne, et « rangs 1-8 » rendrait un autre
        # ensemble de même cardinal — plausible et faux. On refuse donc **le réglage** : une phase
        # de niveau qui doit resserrer se prélève par **groupes entiers**, déjà composable.
        if self.nb_qualifies is not None and self.mode is ModeDeComposition.PAR_NIVEAU:
            raise ConfigurationPouleInvalide(
                "Des poules de niveau ne désignent pas un nombre de qualifiés par poule : chaque "
                "groupe dispute sa propre tranche de rangs. Pour resserrer, faites prélever à la "
                "phase suivante des groupes entiers (« les rangs 1 à 18 »)."
            )
        # La dérogation est **normalisée**, pas refusée : la porter à `True` sous `PAR_NIVEAU` n'est
        # pas une faute de l'organisateur (il a pu cocher la case, puis changer de mode), mais la
        # laisser persister arme un levier que personne ne réassumera au retour au serpent.
        if self.serpent_assume and self.mode is not ModeDeComposition.SERPENT:
            object.__setattr__(self, "serpent_assume", False)

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
            mode=self.mode,
        )


def nb_poules_pour(effectif: int, taille_visee: int) -> int:
    """Combien de groupes former pour des poules « de `taille_visee` » (arbitrage du 09/08/2026).

    L'organisateur raisonne en **taille de poule** ; l'arrondi se fait **vers le bas** (30 archers
    en poules de 4 → 7 poules, remplies en cinq de 4 et deux de 5), l'invariant retenu étant
    *aucune poule ne compte moins que la taille demandée*. ⚠️ Sous le double de la taille visée il
    ne reste qu'**une** poule — 7 archers en poules de 4 donnent une poule de 7, que l'écran doit
    montrer avant validation.
    """

    # ⚠️ **Erreurs typées, pas des `ValueError` nus** (règle 5). Le second cas est **atteignable
    # depuis le client** : `ServicePoules._configuration` appelle `pour_effectif(len(participants))`
    # et une population vide est licite (phase composée avant les inscriptions). Un `ValueError`
    # n'étant ni `DomainError` ni `ApplicationError`, il sortait en **500**.
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

    ⚠️ **Arbitrage du 09/08/2026, et il n'est pas intuitif.** `rencontres_de_poule` apparie par la
    méthode du cercle, qui produit `effectif ÷ 2` rencontres par tour : une poule de 5 ne dispute
    que **deux** rencontres simultanées, soit quatre archers sur la ligne — elle tient sur une
    cible de 4 couloirs, comme une poule de 4. Réserver un couloir par membre ferait déborder toute
    poule impaire. Les membres **tournent** sur le bloc, d'où un plan qui place la poule.
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

    Le moteur ne rejoue pas le duel : `sets_*` départage (à égalité, un nul), `score_*` alimente la
    différence de score, `nb_dix_*` / `nb_neuf_*` les deux derniers critères §10.1. ⚠️ En **cumul**
    (arc à poulies), la saisie reporte le total dans `score_*` et laisse les sets à 0 : la
    rencontre devient un **nul** au sens des points de match. Le service qui assemble doit reporter
    la victoire dans `sets_*` (1-0) — le résultat ne sait pas qu'il est au cumul.
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
    """Répartit les participants **classés** en poules, selon le mode réglé (E05US023, E05US029).

    `participants` arrive **ordonné par rang**. `SERPENT` (défaut) équilibre la force des groupes,
    comme le seeding serpent équilibre un arbre — une distribution naïve mettrait tous les favoris
    ensemble. `PAR_NIVEAU` donne un groupe par tranche contiguë : exactement ce que le serpent
    existe pour éviter, et c'est voulu (la phase amont a déjà établi les niveaux). Les poules
    peuvent différer d'une unité quand l'effectif ne divise pas — chacune est classée séparément.
    """
    if configuration.nb_poules > len(participants):
        raise ConfigurationPouleInvalide(
            f"{configuration.nb_poules} poules pour {len(participants)} participants : "
            "une poule resterait vide."
        )
    groupes = (
        _tranches_de_niveau(participants, configuration.nb_poules)
        if configuration.mode is ModeDeComposition.PAR_NIVEAU
        else _serpent(participants, configuration.nb_poules)
    )
    return tuple(
        Poule(numero=numero + 1, membres=tuple(membres)) for numero, membres in enumerate(groupes)
    )


def _serpent(participants: Sequence[Participant], nb_poules: int) -> list[list[Participant]]:
    """La distribution en serpentin — inchangée depuis E05US015, extraite pour la bifurcation."""
    groupes: list[list[Participant]] = [[] for _ in range(nb_poules)]
    for index, participant in enumerate(participants):
        passage, position = divmod(index, nb_poules)
        # Un passage sur deux se fait à l'envers : c'est tout le serpent.
        numero = position if passage % 2 == 0 else nb_poules - 1 - position
        groupes[numero].append(participant)
    return groupes


def tailles_de_niveau(effectif: int, nb_poules: int) -> list[int]:
    """Les effectifs des tranches d'une composition **par niveau**, dans l'ordre (E05US029).

    **Domicile unique de la règle du gonflement** : les `surplus` **derniers** groupes prennent un
    membre de plus — le bas absorbe le reste. Publique et partagée, `domain/deroule.py` la consomme
    pour savoir quels rangs occupe un groupe : la recopier là-bas aurait été la duplication
    d'invariant que le registre proscrit, sur la propriété même qui définit le format.
    """
    base, surplus = divmod(effectif, nb_poules)
    return [base + (1 if numero >= nb_poules - surplus else 0) for numero in range(nb_poules)]


def _tranches_de_niveau(
    participants: Sequence[Participant], nb_poules: int
) -> list[list[Participant]]:
    """Un groupe par tranche de rangs **contiguë**, le surplus au **bas** (E05US029).

    Un groupe est un intervalle, jamais un peigne, et le surplus va aux **dernières** tranches pour
    que le haut du classement tire dans les conditions annoncées. ⚠️ `# DETTE-077` — `preleves`
    range par `(ordre_source, rang)` : une phase de niveau qui prélève dans **deux** phases
    parallèles compose des groupes reflétant l'ordre des sources, pas les niveaux. Ni refusé ni
    signalé.
    """
    tailles = tailles_de_niveau(len(participants), nb_poules)
    groupes: list[list[Participant]] = []
    debut = 0
    for taille in tailles:
        groupes.append(list(participants[debut : debut + taille]))
        debut += taille
    return groupes


def rencontres_de_poule(
    poule: Poule, configuration: ConfigurationPoules
) -> tuple[RencontrePoule, ...]:
    """Les rencontres d'une poule, par tours, selon la **méthode du cercle**.

    On fixe un membre et on fait tourner les autres ; à effectif **impair**, un membre se repose
    chaque tour. Le cercle dit **quand** se tirent les rencontres, et il est **déterministe**
    (règle 9). `rencontres_par_archer` le tronque à `k` tours ; à `k = n-1` on le déroule
    **entier**, sans quoi un seul membre disputerait `n-1` rencontres. ⚠️ Pour `k < n-1` à effectif
    impair, l'écart d'**une** rencontre subsiste : composer des poules paires, ou laisser complet.
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

    Le `tiebreak` est **injecté** (règle 2) ; à défaut `TiebreakPoules`. Deux membres que le
    comparateur ne sépare pas partagent le rang et sont marqués `ex_aequo` — le « barrage si
    nécessaire », que le moteur signale sans le décider. ⚠️ Les résultats d'une rencontre étrangère
    à la poule sont ignorés en silence ; en revanche un membre **sans aucune rencontre** figure
    bien au classement, à 0 partout — le faire disparaître serait pire.
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

    `()` si la configuration n'en déclare aucun (« la poule classe, elle ne qualifie pas »). ⚠️
    **Un ex æquo qui chevauche la barre est refusé**, pas arbitré : prendre « les deux premiers »
    quand les rangs 2 et 3 sont à égalité qualifierait sur l'ordre d'affichage, c'est-à-dire sur le
    rang de qualification d'origine, qui n'a plus cours en poule. Il faut faire tirer.
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
