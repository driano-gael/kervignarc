"""Arbre d'élimination directe (E05US005, ADR-0004) — le *tableau* qui orchestre les politiques.

E05US003 a livré les **stratégies pures** d'un format de tableau (`SeedingSerpent`,
`ByesAuxMieuxClasses`, `EliminationSeche`, …) ; cette US construit la **structure** qui les
assemble : dimensionner à la puissance de 2, ensemencer, attribuer les byes, générer les matchs
reliés à leurs sources, faire avancer le vainqueur et produire le podium (glossaire : `Tableau` =
« arbre de matchs à élimination »).

**Un format est de la configuration, pas du code** (règle 2). Le moteur ne connaît donc aucun format
en dur : il reçoit ses politiques injectées (`seeding` / `byes` / `routing` / `depth`) et compose
l'arbre à partir d'elles. Changer de politique change le format sans toucher ce module.

**Le moteur oppose des `Participant`, pas des archers** (ADR-0028, E13US001). Un `Match` oppose des
`Participant` (archer **ou** équipe) : le moteur les traite de façon **opaque** — il les compare par
identité et les reporte dans l'arbre, sans jamais brancher sur leur genre (aucun `if équipe`). Le
**rang** de qualification ne sert qu'à l'**ensemencement** : `construire_tableau` reçoit les
participants **ordonnés par rang** (indice 0 = tête de série n°1), et le seeding organise les
**positions**. C'est la clé de structure (byes, appariements), distincte de l'occupant (le
participant). Le placement intégral d'E05US010 réutilisera ces mêmes briques.

**E05US010 généralise la structure : le placement intégral, dont l'élimination directe est un cas.**
L'arbre n'est plus une suite de tours mais une **récursion sur les plages de rangs** — un groupe
disputant `[a..b]` engendre ses matchs, puis les vainqueurs sur `[a..mid]` et les perdants sur
`[mid+1..b]` là où le `routing` les envoie (*Règle R*), jusqu'à une plage de largeur 2 dont le match
**terminal** fixe deux rangs (*Règle T*). Avec une profondeur `podium`, cette même récursion rend
**exactement** l'arbre d'E05US005 — la petite finale *est* le sous-groupe des perdants des demies.
Le `routing` dit **où** descend un perdant, la `depth` **jusqu'où** l'on descend ; le repêchage WA
(E05US015) ajoutera une destination, pas un moteur. Cf. [ADR-0061].
Domaine **pur** : aucun framework, aucune autre couche (règle 1).

[ADR-0061]: ../../docs/adr/0061-routing-generique-et-placement-en-cascade.md
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from domain.erreurs import (
    EffectifTableauInvalide,
    FormatTableauIncoherent,
    MatchIntrouvable,
    MatchNonJouable,
    VainqueurHorsMatch,
)
from domain.participant import Participant
from domain.plage import Plage
from domain.politiques import (
    Byes,
    ContexteRoutage,
    Depth,
    ProfondeurPodium,
    Routing,
    Seeding,
    VersPlage,
)

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
    """Le camp reçoit le **perdant** du match `numero`.

    Câblait la seule petite finale avant E05US010 ; c'est désormais l'arête de toute la **cascade
    de placement** — un perdant descend d'un sous-tableau à l'autre par ce camp. La mécanique de
    propagation n'a pas eu à changer : `_propager` savait déjà reporter un perdant dans un camp
    arbitraire, seule la **génération** de l'arbre s'est étendue.
    """

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
    plage: Plage | None = None
    """La plage de rangs que ce match départage (E05US010) — `[1..8]` pour un quart d'un tableau de
    8, `[5..8]` pour le premier tour de son tableau de placement. `None` sur un tableau construit
    avant cette US (relecture d'un état persisté) : le champ est **facultatif** pour ne pas rompre
    les consommateurs existants, qui n'ont besoin que de `place_en_jeu`."""

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
    est consommé à la **construction** (il a câblé les arêtes de descente), pas à la progression :
    c'est ce qui rend l'arbre reconstructible à l'identique quel que soit l'ordre de saisie
    (ADR-0049, ADR-0061 §3). Il reste porté par l'agrégat pour que le tableau sache décrire son
    propre format.
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

        **Le routing n'est plus consulté ici** (E05US010) : il l'a été à la construction, quand
        l'arbre a été câblé. Le perdant suit donc simplement l'arête `PerdantDe` que la cascade lui
        a posée — vers son sous-tableau de placement s'il en existe un, nulle part sinon. C'est ce
        qui rend le tableau **reconstructible** depuis les seuls résultats (ADR-0049) :
        rejouer les mêmes matchs dans un autre ordre donne le même arbre.

        Les byes ainsi rendus décidables (un sous-tableau alimenté par un match gagné d'office) sont
        résolus dans la foulée.
        """
        m = self.match(numero)
        if not m.est_jouable:
            raise MatchNonJouable(
                f"Le match {numero} n'attend pas de vainqueur (bye, places incomplètes, déjà joué)."
            )
        if vainqueur not in (m.haut, m.bas):
            raise VainqueurHorsMatch(f"Ce participant ne dispute pas le match {numero}.")
        perdant = m.bas if vainqueur == m.haut else m.haut
        matchs = list(self.matchs)
        matchs[numero - 1] = replace(m, vainqueur=vainqueur)
        matchs = _propager(matchs, numero, gagnant=vainqueur, perdant=perdant)
        matchs = _resoudre_byes(matchs)
        return replace(self, matchs=tuple(matchs))

    def match_aval_du_perdant(self, numero: int) -> int | None:
        """Le match qui attend le **perdant** du match `numero`, s'il en existe un (E05US010).

        C'est la lecture du câblage de cascade : en placement intégral tout perdant d'un match non
        terminal en a un (« personne n'est éliminé ») ; en élimination sèche, aucun. Un match gagné
        d'office (bye) n'a **pas** de perdant, donc pas d'aval — son camp aval est resté `Exempt`.
        """
        for m in self.matchs:
            if m.source_haut == PerdantDe(numero) or m.source_bas == PerdantDe(numero):
                return m.numero
        return None

    def classement(self) -> tuple[Place, ...]:
        """Toutes les places **acquises**, du rang 1 au dernier décidé (CA « rangs terminaux »).

        Un rang est décidé par un **match terminal** : celui dont `place_en_jeu` porte la paire
        `(2k-1, 2k)`. *Règle T* - le gagnant prend le rang supérieur, le perdant le suivant. En
        placement intégral, tous les rangs 1→N y passent ; en profondeur `podium`, seuls les
        premiers. Les places sortent **triées par rang**, et le classement est **partiel** tant que
        des matchs terminaux restent à jouer : c'est la lecture « au fil de l'eau » dont vit
        l'écran de suivi.

        Un bye en match terminal (une plage dont un seul camp est occupé — effectif tronqué)
        attribue le rang supérieur à son unique occupant, sans attribuer le suivant : il n'y a
        personne à ce rang.
        """
        places: list[Place] = []
        for m in self.matchs:
            if m.place_en_jeu is None or m.vainqueur is None:
                continue
            rang_gagnant, rang_perdant = m.place_en_jeu
            places.append(Place(rang_gagnant, m.vainqueur))
            if m.perdant is not None:
                places.append(Place(rang_perdant, m.perdant))
        return tuple(sorted(places, key=lambda place: place.rang))

    def podium(self) -> tuple[Place, ...]:
        """Les quatre premières places : finale → rangs 1-2, petite finale → rangs 3-4 (CA podium).

        Vue **restreinte** du classement, conservée telle quelle pour ses consommateurs (E06US004,
        l'état de tableau d'E04US013). Elle reste vide tant que la finale n'est pas jouée — un
        podium est un tout —, là où `classement()` livre les rangs au fil de l'eau.
        """
        if self.finale.vainqueur is None:
            return ()
        return tuple(place for place in self.classement() if place.rang <= 4)


# --- construction ------------------------------------------------------------------------------


def construire_tableau(
    participants: Sequence[Participant],
    seeding: Seeding,
    byes: Byes,
    routing: Routing,
    depth: Depth | None = None,
) -> Tableau:
    """Assemble le tableau pour ces `participants` (CA E05US005, généralisé par E05US010).

    `participants` est **ordonné par rang** de qualification (indice 0 = tête n°1).

    **La structure est une récursion sur les plages de rangs**, et non plus une suite de tours. Un
    *groupe* de `2^j` camps disputant la plage `[a..b]` engendre `2^(j-1)` matchs ; puis, tant que
    la plage n'est pas terminale, il engendre **deux** sous-groupes : les vainqueurs sur la moitié
    haute, les perdants sur la moitié basse là où le `routing` les envoie (*Règle R*). Quand la
    plage atteint la largeur 2, le match est **terminal** : son issue fixe les deux rangs (*Règle
    T*), et la récursion s'arrête.

    L'élimination directe d'E05US005 **est un cas particulier** de cette récursion : avec une
    profondeur `podium` (rangs 1-4), le sous-groupe des perdants des quarts n'est pas engendré
    (aucun de ses rangs n'est à classer) tandis que celui des perdants des demies l'est — et ce
    sous-groupe *est* la petite finale. Même arbre, même numérotation qu'avant l'US.

    Consomme **quatre politiques** (ADR-0004) : `seeding` (l'ordre des positions), `byes` (autorité
    sur les dispensés — un garde-fou refuse une paire seeding/byes incohérente via
    `FormatTableauIncoherent`), `routing` (où descend un perdant) et `depth` (jusqu'où classer ;
    `ProfondeurPodium` par défaut, qui préserve le comportement historique des appelants qui ne la
    passent pas encore).

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
    a_classer = frozenset((depth or ProfondeurPodium()).rangs_a_classer(effectif))

    def occupant(position: int) -> Participant | None:
        """Le participant placé à cette `position` d'ensemencement, ou `None` si c'est un exempt."""
        return participants[position - 1] if position <= effectif else None

    matchs: list[Match] = []
    positions_dispensees: set[int] = set()

    # Premier tour : paires adjacentes de l'ordre serpent. Une position > effectif est une place
    # d'exempt (aucun participant à ce rang) ; grâce à l'arrondi à la puissance de 2 *supérieure*,
    # deux exempts ne tombent jamais dans la même paire — chaque match a donc un participant réel.
    camps_initiaux: list[tuple[Camp, Participant | None]] = []
    for position in ordre:
        if position <= effectif:
            camps_initiaux.append((TeteDeSerie(position), occupant(position)))
        else:
            camps_initiaux.append((Exempt(), None))
    for i in range(taille // 2):
        pos_haut, pos_bas = ordre[2 * i], ordre[2 * i + 1]
        if pos_bas > effectif:  # le camp haut est dispensé (adversaire exempt)
            positions_dispensees.add(pos_haut)
        elif pos_haut > effectif:  # le camp bas est dispensé
            positions_dispensees.add(pos_bas)

    # Cohérence seeding ↔ byes (règle 2) : les positions que la structure serpent laisse sans
    # adversaire doivent être exactement celles que `byes` désigne — sinon, la paire est refusée.
    # Contrôlé **avant** d'engendrer l'arbre : inutile de dérouler la cascade d'un format faux.
    if positions_dispensees != set(byes.porteurs_de_bye(effectif)):
        raise FormatTableauIncoherent(
            "Les politiques seeding et byes se contredisent sur les dispensés du premier tour."
        )

    def engendrer(
        camps: list[tuple[Camp, Participant | None]], plage: Plage, tour: int
    ) -> list[int]:
        """Engendre les matchs d'un groupe et, récursivement, ses sous-groupes. Rend leurs numéros.

        `camps` sont les entrants du groupe, déjà appariés deux à deux dans l'ordre reçu.
        """
        numeros: list[int] = []
        terminal = plage.est_terminale
        for k in range(len(camps) // 2):
            (src_haut, haut), (src_bas, bas) = camps[2 * k], camps[2 * k + 1]
            numero = len(matchs) + 1
            matchs.append(
                Match(
                    numero,
                    tour,
                    src_haut,
                    src_bas,
                    haut,
                    bas,
                    None,
                    plage.paire_terminale if terminal else None,
                    plage,
                )
            )
            numeros.append(numero)
        if terminal:
            return numeros  # *Règle T* : l'issue fixe les deux rangs, il n'y a plus rien à diviser

        # La moitié **haute** est structurelle (les vainqueurs y montent toujours) ; la basse,
        # elle, n'est pas calculée ici — c'est le `routing` qui dit où descend le perdant, et lui
        # seul. La déduire en double ferait de ce module un second lieu de décision.
        haute = plage.moitie_haute()
        if _a_classer(haute, a_classer):
            # Un match **vide** (deux camps exempts, cas d'un sous-tableau plus large que le nombre
            # de perdants réels) ne livrera jamais de vainqueur : son camp aval est un exempt, sinon
            # le tour suivant attendrait un occupant qui ne viendra pas — et le rang resterait
            # indécidé alors qu'il n'est disputé par personne.
            gagnants: list[tuple[Camp, Participant | None]] = [
                (Exempt() if _est_vide(matchs[n - 1]) else VainqueurDe(n), None) for n in numeros
            ]
            engendrer(gagnants, haute, tour + 1)
        destination = routing.route(ContexteRoutage(tour=tour, plage=plage))
        if isinstance(destination, VersPlage) and _a_classer(destination.plage, a_classer):
            # Le perdant d'un match gagné d'office (ou vide) n'existe pas : même raisonnement.
            entrants: list[tuple[Camp, Participant | None]] = [
                (Exempt() if matchs[n - 1].est_bye else PerdantDe(n), None) for n in numeros
            ]
            engendrer(entrants, destination.plage, tour + 1)
        return numeros

    engendrer(camps_initiaux, Plage(1, taille), 1)
    resolus = _resoudre_byes(matchs)
    return Tableau(effectif=effectif, taille=taille, matchs=tuple(resolus), routing=routing)


def _est_vide(match: Match) -> bool:
    """Ce match n'a **aucun** occupant possible : ses deux camps sont des places d'exempt.

    Se produit dans les sous-tableaux de placement quand l'effectif réel fournit moins de perdants
    que la plage n'a de places (5 archers dans un tableau de 8 : un seul match du premier tour est
    disputé, donc un seul perdant descend). À distinguer du **bye**, qui a un occupant et un
    vainqueur d'office ; un match vide n'a ni l'un ni l'autre.
    """
    return isinstance(match.source_haut, Exempt) and isinstance(match.source_bas, Exempt)


def _a_classer(plage: Plage, rangs: frozenset[int]) -> bool:
    """Ce sous-tableau a-t-il une raison d'exister ? — la profondeur décide (E05US010).

    Deux motifs d'élagage se rejoignent ici, et c'est voulu : la **profondeur** demandée (un top 4
    ne départage pas les rangs 5 et au-delà) et l'**effectif réel** (un tableau de 128 pour 120
    archers n'a personne à placer aux rangs 121-128). Dans les deux cas, la question est la même —
    « reste-t-il un rang à décider là-dedans ? » — donc une seule règle, pas deux garde-fous.
    """
    return any(rang in rangs for rang in range(plage.debut, plage.fin + 1))


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

    `# DETTE-020` — le front calcule **aussi** ce libellé (`features/saisie-duels/duel.ts`,
    E04US013), au pluriel et avec un suffixe sur la petite finale : deux domiciles pour une
    règle de vocabulaire, à unifier ici (ADR-0006).
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
