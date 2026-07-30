"""Arbre d'élimination directe (E05US005, ADR-0004) — le *tableau* qui orchestre les politiques.

E05US003 a livré les **stratégies pures** d'un format de tableau (`SeedingSerpent`,
`ByesAuxMieuxClasses`, `EliminationSeche`, …) ; cette US construit la **structure** qui les
assemble : dimensionner à la puissance de 2, ensemencer, attribuer les byes, générer les matchs
reliés à leurs sources, faire avancer le vainqueur et produire le podium (glossaire : `Tableau` =
« arbre de matchs à élimination »).

**Un format est de la configuration, pas du code** (règle 2). Le moteur ne connaît donc aucun format
en dur : il reçoit ses trois politiques injectées (`seeding` / `byes` / `routing`) et compose
l'arbre à partir d'elles. Changer de politique change le format sans toucher ce module.

**Le moteur oppose des `Participant`, pas des archers** (ADR-0028, E13US001). Un `Match` oppose des
`Participant` (archer **ou** équipe) : le moteur les traite de façon **opaque** — il les compare par
identité et les reporte dans l'arbre, sans jamais brancher sur leur genre (aucun `if équipe`). Le
**rang** de qualification ne sert qu'à l'**ensemencement** : `construire_tableau` reçoit les
participants **ordonnés par rang** (indice 0 = tête de série n°1), et le seeding organise les
**positions**. C'est la clé de structure (byes, appariements), distincte de l'occupant (le
participant). Le placement intégral d'E05US010 réutilisera ces mêmes briques.

**Périmètre E05US005 : élimination directe simple.** Le perdant est **éliminé** (routing sèche) ; le
podium se limite aux quatre premiers (finale → 1-2, petite finale → 3-4). La cascade de placement
(le perdant rejoue un sous-tableau) est E05US010 ; le **repêchage** WA est E05US016. Tous deux
**ressigneront** le routing d'ADR-0004 (`route(perdant, tour, contexte)`) — rupture assumée, un seul
implémenteur aujourd'hui. Domaine **pur** : aucun framework, aucune autre couche (règle 1).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from domain.erreurs import (
    EffectifTableauInvalide,
    FormatTableauIncoherent,
    MatchIntrouvable,
    MatchNonJouable,
    RoutingNonSupporte,
    VainqueurHorsMatch,
)
from domain.participant import Participant
from domain.politiques import Byes, DestinationPerdant, Routing, Seeding

# --- sources d'un camp de match ----------------------------------------------------------------
# La **source** d'un camp dit d'où vient son occupant ; elle est fixée à la construction (le câblage
# de l'arbre), tandis que l'occupant (`haut`/`bas` du `Match`) se remplit au fil de la progression.


@dataclass(frozen=True)
class TeteDeSerie:
    """Une **position** de tête de série (le rang `r`) entre dans ce camp au premier tour.

    C'est un rang d'ensemencement (clé de structure), pas un participant : l'occupant réel du camp
    est le participant placé à ce rang par `construire_tableau`.
    """

    rang: int


@dataclass(frozen=True)
class Exempt:
    """Place d'exempt (bye) : ce camp n'a **jamais** d'occupant (position au-delà de l'effectif, ou
    perdant d'un match gagné d'office). Le participant d'en face avance sans tirer."""


@dataclass(frozen=True)
class VainqueurDe:
    """Le camp reçoit le **vainqueur** du match `numero` (câblage des tours ≥ 2)."""

    numero: int


@dataclass(frozen=True)
class PerdantDe:
    """Le camp reçoit le **perdant** du match `numero` (câblage de la petite finale)."""

    numero: int


type Camp = TeteDeSerie | Exempt | VainqueurDe | PerdantDe


# --- match & tableau ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Match:
    """Un match du tableau : deux camps, un tour, un numéro, et l'issue quand elle est connue.

    `source_haut`/`source_bas` sont le **câblage** (immuable) ; `haut`/`bas` les **occupants** (des
    `Participant`) remplis par la progression (`None` = pas encore connu). `vainqueur` est `None`
    tant que le match n'est pas tranché. `place_en_jeu` distingue la finale `(1, 2)` et la petite
    finale `(3, 4)` — les seuls matchs dont l'issue fixe directement un rang de podium.
    """

    numero: int
    tour: int
    source_haut: Camp
    source_bas: Camp
    haut: Participant | None
    bas: Participant | None
    vainqueur: Participant | None = None
    place_en_jeu: tuple[int, int] | None = None

    @property
    def est_bye(self) -> bool:
        """Un camp est une place d'exempt : le match est gagné d'office (rien à disputer)."""
        return isinstance(self.source_haut, Exempt) or isinstance(self.source_bas, Exempt)

    @property
    def est_jouable(self) -> bool:
        """Les deux occupants sont connus, aucun exempt, pas encore de vainqueur : un vrai match."""
        return (
            self.haut is not None
            and self.bas is not None
            and self.vainqueur is None
            and not self.est_bye
        )

    @property
    def perdant(self) -> Participant | None:
        """Le perdant, une fois le vainqueur connu (`None` sinon, ou pour un bye sans face)."""
        if self.vainqueur is None or self.haut is None or self.bas is None:
            return None
        return self.bas if self.vainqueur == self.haut else self.haut


@dataclass(frozen=True)
class Place:
    """Une place de podium : le `rang` (1 = titre) attribué au `participant`."""

    rang: int
    participant: Participant


@dataclass(frozen=True)
class Tableau:
    """L'arbre d'élimination directe : sa taille (2^k), son effectif réel, ses matchs, son routing.

    Immuable comme tout agrégat de domaine : `jouer` renvoie un **nouveau** `Tableau`. Le `routing`
    injecté est consommé à chaque progression (le perdant part par élimination sèche).
    """

    effectif: int
    taille: int
    matchs: tuple[Match, ...]
    routing: Routing

    @property
    def nb_tours(self) -> int:
        """Le nombre de tours principaux, `log2(taille)` (8 places → 3 tours)."""
        return self.taille.bit_length() - 1

    def match(self, numero: int) -> Match:
        """Le match de ce numéro, ou `MatchIntrouvable`."""
        for m in self.matchs:
            if m.numero == numero:
                return m
        raise MatchIntrouvable(f"Aucun match numéro {numero} dans le tableau.")

    @property
    def finale(self) -> Match:
        """Le match aux rangs 1-2 (toujours présent : un tableau a une finale)."""
        return next(m for m in self.matchs if m.place_en_jeu == (1, 2))

    @property
    def petite_finale(self) -> Match | None:
        """Le match aux rangs 3-4, ou `None` pour un tableau de 2 (pas de demi-finales)."""
        return next((m for m in self.matchs if m.place_en_jeu == (3, 4)), None)

    @property
    def est_termine(self) -> bool:
        """La finale est jouée et la petite finale (si elle existe) l'est aussi."""
        petite = self.petite_finale
        return self.finale.vainqueur is not None and (
            petite is None or petite.vainqueur is not None
        )

    def jouer(self, numero: int, vainqueur: Participant) -> Tableau:
        """Enregistre le vainqueur du match `numero` et peuple le(s) match(s) aval — CA progression.

        Refuse un match introuvable (`MatchIntrouvable`), non jouable (`MatchNonJouable` : bye,
        places incomplètes, déjà joué) ou un vainqueur étranger au match (`VainqueurHorsMatch`).
        Le perdant est routé par la politique injectée : en élimination sèche il quitte le tournoi
        (aucune réinjection) ; une autre destination lève `RoutingNonSupporte` (E05US010/E05US016).
        Les byes ainsi rendus décidables (petite finale alimentée par une demi-finale) sont résolus.
        """
        m = self.match(numero)
        if not m.est_jouable:
            raise MatchNonJouable(
                f"Le match {numero} n'attend pas de vainqueur (bye, places incomplètes, déjà joué)."
            )
        if vainqueur not in (m.haut, m.bas):
            raise VainqueurHorsMatch(f"Ce participant ne dispute pas le match {numero}.")
        if self.routing.destination_du_perdant() is not DestinationPerdant.ELIMINE:
            raise RoutingNonSupporte(
                "Le moteur d'élimination directe ne route le perdant que par élimination sèche."
            )
        perdant = m.bas if vainqueur == m.haut else m.haut
        matchs = list(self.matchs)
        matchs[numero - 1] = replace(m, vainqueur=vainqueur)
        matchs = _propager(matchs, numero, gagnant=vainqueur, perdant=perdant)
        matchs = _resoudre_byes(matchs)
        return replace(self, matchs=tuple(matchs))

    def podium(self) -> tuple[Place, ...]:
        """Les places décidées : finale → rangs 1-2, petite finale → rangs 3-4 (CA podium).

        Renvoie les places au fur et à mesure qu'elles sont acquises (`()` tant que la finale n'est
        pas jouée). Un bye en petite finale (cas d'un effectif à demi-finale exemptée) attribue la
        3e place à son unique occupant, sans 4e place — alimente l'agrégation d'E06US004.
        """
        places: list[Place] = []
        finale = self.finale
        if finale.vainqueur is not None:
            places.append(Place(1, finale.vainqueur))
            if finale.perdant is not None:
                places.append(Place(2, finale.perdant))
        petite = self.petite_finale
        if petite is not None and petite.vainqueur is not None:
            places.append(Place(3, petite.vainqueur))
            if petite.perdant is not None:
                places.append(Place(4, petite.perdant))
        return tuple(places)


# --- construction ------------------------------------------------------------------------------


def construire_tableau(
    participants: Sequence[Participant], seeding: Seeding, byes: Byes, routing: Routing
) -> Tableau:
    """Assemble le tableau d'élimination directe pour ces `participants` (CA E05US005).

    `participants` est **ordonné par rang** de qualification (indice 0 = tête n°1). Étapes :
    arrondi à la puissance de 2 (via la longueur de l'ordre serpent) ; premier tour par paires de
    l'ordre serpent, une position au-delà de l'effectif devenant un `Exempt` ; tours suivants câblés
    `VainqueurDe` deux à deux ; petite finale câblée `PerdantDe` des deux demi-finales. Les byes du
    premier tour sont ensuite résolus (le participant exempté gagne d'office et avance).

    Consomme les **trois politiques** injectées : `seeding` (l'ordre des positions), `byes`
    (autorité sur les dispensés — un garde-fou refuse une paire seeding/byes incohérente via
    `FormatTableauIncoherent`) et `routing` (porté par le `Tableau`, consommé à la progression).

    **Préconditions à la charge de l'appelant** (non défendues ici : le moteur ne lit aucune
    identité, il ne peut donc pas les vérifier) : `participants` est **trié par rang** de
    qualification et **sans doublon**. Un ordre faux produirait un ensemencement silencieusement
    erroné ; un même participant présent deux fois briserait l'appariement. Le premier consommateur
    (le classement source, via E04US013 / E05US010) garantit ces invariants.
    """
    effectif = len(participants)
    if effectif < 2:
        raise EffectifTableauInvalide(
            f"Un tableau d'élimination directe demande au moins 2 participants (reçu {effectif})."
        )
    ordre = seeding.ordre_des_tetes(effectif)
    taille = len(ordre)
    nb_tours = taille.bit_length() - 1

    def occupant(position: int) -> Participant | None:
        """Le participant placé à cette `position` d'ensemencement, ou `None` si c'est un exempt."""
        return participants[position - 1] if position <= effectif else None

    matchs: list[Match] = []
    numero = 0
    positions_dispensees: set[int] = set()

    # Premier tour : paires adjacentes de l'ordre serpent. Une position > effectif est une place
    # d'exempt (aucun participant à ce rang) ; grâce à l'arrondi à la puissance de 2 *supérieure*,
    # deux exempts ne tombent jamais dans la même paire — chaque match a donc un participant réel.
    tours: list[list[int]] = []
    tour1: list[int] = []
    for i in range(taille // 2):
        numero += 1
        pos_haut, pos_bas = ordre[2 * i], ordre[2 * i + 1]
        source_haut: Camp = TeteDeSerie(pos_haut) if pos_haut <= effectif else Exempt()
        source_bas: Camp = TeteDeSerie(pos_bas) if pos_bas <= effectif else Exempt()
        haut, bas = occupant(pos_haut), occupant(pos_bas)
        if pos_bas > effectif:  # le camp haut est dispensé (adversaire exempt)
            positions_dispensees.add(pos_haut)
        elif pos_haut > effectif:  # le camp bas est dispensé
            positions_dispensees.add(pos_bas)
        place = (1, 2) if taille == 2 else None  # tableau de 2 : ce match unique est la finale
        matchs.append(Match(numero, 1, source_haut, source_bas, haut, bas, None, place))
        tour1.append(numero)
    tours.append(tour1)

    # Cohérence seeding ↔ byes (règle 2) : les positions que la structure serpent laisse sans
    # adversaire doivent être exactement celles que `byes` désigne — sinon, la paire est refusée.
    if positions_dispensees != set(byes.porteurs_de_bye(effectif)):
        raise FormatTableauIncoherent(
            "Les politiques seeding et byes se contredisent sur les dispensés du premier tour."
        )

    # Tours suivants : chaque match reçoit les vainqueurs de deux matchs consécutifs du tour amont.
    for tour in range(2, nb_tours + 1):
        precedent = tours[-1]
        courant: list[int] = []
        for j in range(len(precedent) // 2):
            numero += 1
            place = (1, 2) if tour == nb_tours else None
            matchs.append(
                Match(
                    numero,
                    tour,
                    VainqueurDe(precedent[2 * j]),
                    VainqueurDe(precedent[2 * j + 1]),
                    None,
                    None,
                    None,
                    place,
                )
            )
            courant.append(numero)
        tours.append(courant)

    # Petite finale (dès qu'il y a des demi-finales, taille ≥ 4) : les perdants des deux demies
    # jouent les rangs 3-4. Le perdant d'un bye n'existe pas — la place reste alors un Exempt.
    if taille >= 4:
        demi = tours[-2]
        numero += 1
        src_haut: Camp = Exempt() if matchs[demi[0] - 1].est_bye else PerdantDe(demi[0])
        src_bas: Camp = Exempt() if matchs[demi[1] - 1].est_bye else PerdantDe(demi[1])
        matchs.append(Match(numero, nb_tours, src_haut, src_bas, None, None, None, (3, 4)))

    resolus = _resoudre_byes(matchs)
    return Tableau(effectif=effectif, taille=taille, matchs=tuple(resolus), routing=routing)


def paires_du_premier_tour(tableau: Tableau) -> tuple[tuple[Participant, Participant], ...]:
    """Les duels **effectivement disputés** au premier tour : (haut, bas) de chaque match jouable.

    Sert le placement des duellistes côte à côte (E03US009) : seuls les matchs du **tour 1** ont
    leurs deux occupants connus dès la construction (les tours ≥ 2 restent `None` jusqu'à la
    progression). On exclut les **byes** (un seul occupant, `est_jouable` faux) : un exempté n'a pas
    d'adversaire à placer à côté de lui. Fonction **pure**, ordre = celui des matchs (donc de
    l'ensemencement)."""
    return tuple(
        (m.haut, m.bas)
        for m in tableau.matchs
        if m.tour == 1 and m.est_jouable and m.haut is not None and m.bas is not None
    )


def libelle_tour(tour: int, nb_tours: int, place_en_jeu: tuple[int, int] | None = None) -> str:
    """Le nom que la salle donne à ce tour — « Quart de finale », « 1/8 de finale », « Finale ».

    Vocabulaire métier (règle 3), donc domaine : un archer ne se repère pas au **rang** du tour dans
    l'arbre (« tour 2 »), il se repère à sa **distance au titre**. Ce libellé se compte donc **à
    rebours** de la finale — le tour 1 est un quart sur un tableau de 8, une demie sur un tableau de
    4. Au-delà du quart, la FFTA nomme les tours par leur fraction (1/8, 1/16, …).

    `place_en_jeu` **prime** sur le compte : la petite finale se dispute au **même tour** que la
    finale, et sans ce discriminant les deux matchs porteraient le même nom (E04US018 — le panneau
    de routage enverrait les demi-finalistes battus au mauvais rendez-vous).

    Fonction **pure** : aucune lecture, aucun état. `nb_tours` vient de `Tableau.nb_tours`.
    """
    if place_en_jeu == (3, 4):
        return "Petite finale"
    restants = nb_tours - tour
    if restants <= 0:
        return "Finale"
    if restants == 1:
        return "Demi-finale"
    if restants == 2:
        return "Quart de finale"
    return f"1/{2**restants} de finale"


# --- rouages internes de progression -----------------------------------------------------------


def _propager(
    matchs: list[Match], numero: int, gagnant: Participant, perdant: Participant | None
) -> list[Match]:
    """Reporte gagnant (et perdant s'il existe) du match `numero` dans les camps qui l'attendent."""
    resultat: list[Match] = []
    for m in matchs:
        haut, bas = m.haut, m.bas
        if m.source_haut == VainqueurDe(numero):
            haut = gagnant
        elif perdant is not None and m.source_haut == PerdantDe(numero):
            haut = perdant
        if m.source_bas == VainqueurDe(numero):
            bas = gagnant
        elif perdant is not None and m.source_bas == PerdantDe(numero):
            bas = perdant
        resultat.append(m if (haut, bas) == (m.haut, m.bas) else replace(m, haut=haut, bas=bas))
    return resultat


def _resoudre_byes(matchs: list[Match]) -> list[Match]:
    """Résout tout bye décidable (son unique occupant est connu) et propage le vainqueur, en boucle.

    Un bye n'a pas d'adversaire : dès que son seul occupant est connu il l'emporte. Résoudre en
    boucle couvre la cascade — un bye de premier tour peuple un tour suivant ; une petite finale
    alimentée par une demi-finale exemptée ne devient décidable qu'une fois l'autre demie jouée.
    """
    courant = list(matchs)
    change = True
    while change:
        change = False
        for i, m in enumerate(courant):
            if m.est_bye and m.vainqueur is None:
                occupant = m.haut if m.haut is not None else m.bas
                if occupant is not None:
                    courant[i] = replace(m, vainqueur=occupant)
                    courant = _propager(courant, m.numero, gagnant=occupant, perdant=None)
                    change = True
                    break
    return courant
