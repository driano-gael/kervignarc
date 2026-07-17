"""Agrégat `Blason` — une cible en carton d'un tournoi (E01US005 ; zones : E01US014).

Modélise l'**occupation d'une cible** : un blason porte un `nom`, une `taille` (fraction de
place occupée sur une cible, `0 < taille <= 1`) et une `capacite` (nombre d'archers admis,
`>= 1`). Agrégat de domaine **pur** (aucune dépendance framework, immuable), validé à la
création/édition. Les blasons appartiennent à un tournoi ; l'association d'une **catégorie** à
un blason par défaut viendra en E01US006. Reprend et formalise le prototype `Blason`.

Il porte aussi ses `zones` — les **valeurs de score admises** (E01US014) : un blason ne se
réduit pas à sa taille, un triple 40 n'a pas les zones 5 → 1 (référentiel §4.4). C'est cette
donnée qui permet au pavé de saisie (EPIC-04) de ne proposer que le tirable.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from enum import Enum

from domain.erreurs import (
    CapaciteBlasonInvalide,
    NomBlasonInvalide,
    TailleBlasonInvalide,
    ZonesBlasonInvalides,
)
from domain.tournoi import TournoiId

BlasonId = int
"""Identifiant technique d'un blason, attribué par la persistance."""


class ZoneScore(str, Enum):
    """Valeur de score admise sur un blason en salle (art. B.2.1.2).

    Vocabulaire **fermé** des onze valeurs marquables à 18 m (`docs/referentiel-ffta.md` §4.2) :
    cinq couleurs divisées en deux zones (10 → 1), plus `M` (manqué, hors blanc). Même patron que
    `TrancheAge` ([ADR-0019](../../docs/adr/0019-categorie-eligibilite-multi-tranches.md))
    et même régime : le DTO l'expose tel quel, une valeur hors vocabulaire est donc rejetée en
    **400** à la frontière, avant que le domaine ne la voie (règle 6).

    L'**ordre de déclaration** est l'ordre canonique, du centre vers l'extérieur :
    `ZONES_CANONIQUES` en dérive et les zones d'un blason y sont normalisées, l'ordre de saisie
    ne portant aucune information.

    La « mouche » (X) n'en fait **pas** partie : c'est le centre du 10 (§4.3 la donne comme un
    diamètre, pas comme une valeur), elle ne vaut pas un score distinct et aucun consommateur ne la
    demande à ce jour — le départage FFTA au nombre de X relèverait d'EPIC-06.
    """

    DIX = "10"
    NEUF = "9"
    HUIT = "8"
    SEPT = "7"
    SIX = "6"
    CINQ = "5"
    QUATRE = "4"
    TROIS = "3"
    DEUX = "2"
    UN = "1"
    MANQUE = "M"


ZONES_CANONIQUES: tuple[ZoneScore, ...] = tuple(ZoneScore)
"""Vocabulaire des zones, dans l'ordre canonique (centre → extérieur). Sert de clé de tri."""

ZONES_DEFAUT: tuple[ZoneScore, ...] = (
    ZoneScore.DIX,
    ZoneScore.NEUF,
    ZoneScore.HUIT,
    ZoneScore.SEPT,
    ZoneScore.SIX,
    ZoneScore.CINQ,
    ZoneScore.QUATRE,
    ZoneScore.TROIS,
    ZoneScore.DEUX,
    ZoneScore.UN,
    ZoneScore.MANQUE,
)
"""Zones par défaut : le jeu complet d'un **blason simple** (10 → 1 + M).

`taille` étant une *fraction de place* et non un diamètre, le domaine ne peut pas déduire s'il
s'agit d'un triple 40 : le défaut est donc le **sur-ensemble**, que l'administrateur restreint
explicitement pour un triple (arbitrage utilisateur du 17/07/2026 — cf. CA d'E01US014 et
[ADR-0020](../../docs/adr/0020-blason-zones-vocabulaire-ferme-et-defaut-sur-ensemble.md)).

Énuméré **en toutes lettres** plutôt qu'aliasé sur `ZONES_CANONIQUES` : les deux coïncident
aujourd'hui, mais ce sont deux concepts distincts (le *vocabulaire* et le *jeu par défaut*).
Ajouter une valeur au vocabulaire — X, si EPIC-06 le réclame — ne doit pas la faire entrer en
silence dans le défaut de tous les blasons, ni la désaligner du `_ZONES_DEFAUT` gelé de la
migration `0019`.
"""


@dataclass(frozen=True)
class Blason:
    """Un blason rattaché à un tournoi. `id` vaut `None` tant qu'il n'est pas persisté."""

    tournoi_id: TournoiId
    nom: str
    taille: float
    capacite: int
    # Sans valeur par défaut, délibérément : `zones` pilote le pavé de saisie (EPIC-04), et un
    # défaut sur le constructeur *brut* laisserait un futur chemin de réhydratation l'omettre en
    # silence — mypy et ruff resteraient verts, et le blason ressortirait « tout admis », soit le
    # bug même que cette US corrige. Le défaut vit sur `creer`, où il est un choix explicite.
    zones: tuple[ZoneScore, ...]
    id: BlasonId | None = None

    @staticmethod
    def creer(
        tournoi_id: TournoiId,
        nom: str,
        taille: float,
        capacite: int,
        zones: Iterable[ZoneScore | str] | None = None,
    ) -> Blason:
        """Crée un blason valide.

        Le `nom` est normalisé (espaces de bord retirés) et ne peut pas être vide ; la `taille`
        doit être dans `]0, 1]` (fraction de place) ; la `capacite` doit être un entier `>= 1` ;
        les `zones`, omises (**seul** sens de `None` ici), valent `ZONES_DEFAUT`.
        Lève l'erreur de domaine correspondante en cas de valeur invalide.
        """
        return Blason(
            tournoi_id=tournoi_id,
            nom=_nom_valide(nom),
            taille=_taille_valide(taille),
            capacite=_capacite_valide(capacite),
            zones=ZONES_DEFAUT if zones is None else valider_zones(zones),
        )

    def modifier(
        self,
        nom: str,
        taille: float,
        capacite: int,
        zones: Iterable[ZoneScore | str],
    ) -> Blason:
        """Renvoie une copie aux attributs mis à jour (mêmes règles que `creer`).

        L'`id` et le `tournoi_id` sont **préservés** (on ne déplace pas un blason d'un tournoi à
        l'autre). Les `zones` sont **obligatoires** : l'édition est un remplacement complet, comme
        pour le nom, la taille et la capacité — `None` n'y a donc pas un second sens (« inchangé »)
        qui aurait fait de ce champ le seul partiel d'un PUT par ailleurs total.
        Lève l'erreur de domaine correspondante en cas de valeur invalide.
        """
        return replace(
            self,
            nom=_nom_valide(nom),
            taille=_taille_valide(taille),
            capacite=_capacite_valide(capacite),
            zones=valider_zones(zones),
        )


def _nom_valide(nom: str) -> str:
    """Normalise le nom ; lève `NomBlasonInvalide` s'il est vide."""
    nom_normalise = nom.strip()
    if not nom_normalise:
        raise NomBlasonInvalide("Le nom d'un blason ne peut pas être vide.")
    return nom_normalise


def _taille_valide(taille: float) -> float:
    """Vérifie que la taille est une fraction de place dans `]0, 1]`."""
    if not 0 < taille <= 1:
        raise TailleBlasonInvalide(
            "La taille d'un blason doit être une fraction de place strictement positive "
            "et au plus égale à 1."
        )
    return taille


def _capacite_valide(capacite: int) -> int:
    """Vérifie que la capacité est un entier `>= 1`."""
    if capacite < 1:
        raise CapaciteBlasonInvalide("La capacité d'un blason doit être d'au moins 1.")
    return capacite


def valider_zones(zones: Iterable[ZoneScore | str]) -> tuple[ZoneScore, ...]:
    """Valide et normalise les valeurs de score admises ; lève `ZonesBlasonInvalides`.

    **Publique** à dessein : le repository la rejoue à la **relecture**, pour qu'une colonne
    corrompue remonte en `InfrastructureError` plutôt qu'en agrégat silencieusement invalide
    (même geste que `_vers_phase`, qui repasse par `BaremeQualification.creer` — ADR-0007).

    Trois règles seulement, et **aucune n'est un contrôle de conformité FFTA** : `M` est toujours
    admis (un manqué est physiquement possible sur tout blason, le scoreur doit pouvoir le saisir),
    au moins une zone marquante (sans quoi le blason n'existe pas), pas de doublon.

    La **contiguïté** n'est délibérément pas exigée. Le motif est qu'elle ne sert **aucun
    consommateur** : le pavé de saisie affiche ce qu'on lui donne, et EPIC-04 somme des valeurs
    indépendantes — un jeu troué n'existe sur aucun carton réel, mais l'interdire n'apporterait
    rien qu'une norme. RG-8 (« l'application n'impose ni ne vérifie la conformité au règlement »)
    **confirme** ce choix, il ne le dicte pas : sous sa lecture littérale, les trois règles
    ci-dessus seraient elles aussi de la conformité. Ce qui les distingue est l'**intégrité aval**,
    pas le règlement.

    Le vocabulaire, lui, est fermé par `ZoneScore` — normalement à la frontière (400, règle 6) ;
    la garde ici couvre les appelants internes (import, script), pour qui le domaine reste
    l'autorité.
    """
    # `str` est lui-même un `Iterable[str]` : sans cette garde, `zones="1M"` passerait en
    # `('1', 'M')` au lieu d'échouer. Inatteignable via l'API (Pydantic refuse), mais un futur
    # import CSV ou script appellerait le domaine directement.
    if isinstance(zones, str):
        raise ZonesBlasonInvalides(
            "Les zones d'un blason sont une liste de valeurs, pas une chaîne de caractères."
        )

    # Un non-itérable (`None`, `42`) lèverait un `TypeError` **nu** : cette fonction est publique
    # et promet une erreur de domaine typée (règle 5) — ses appelants internes ne doivent pas
    # avoir à connaître ses entrailles pour la rattraper.
    try:
        brutes = list(zones)
    except TypeError as exc:
        raise ZonesBlasonInvalides(
            f"Les zones d'un blason doivent être une liste de valeurs "
            f"(reçu : {type(zones).__name__})."
        ) from exc

    saisies: list[ZoneScore] = []
    for zone in brutes:
        try:
            # `ZoneScore` hérite de `str`, donc ses propres membres passent aussi par `strip()` —
            # c'est sans effet (la valeur est déjà nette) et ça évite une branche morte.
            saisies.append(ZoneScore(zone.strip() if isinstance(zone, str) else zone))
        except ValueError as exc:
            # Le **type** est dans le message, sinon `zones=[10, "M"]` (entiers JSON d'un script)
            # donnerait « 10 est inconnue, valeurs admises : 10, 9… » — vrai mais illisible.
            raise ZonesBlasonInvalides(
                f"Zone de score inconnue : {_extrait(zone)} (type {type(zone).__name__}). "
                f"Valeurs admises : {', '.join(z.value for z in ZONES_CANONIQUES)}."
            ) from exc

    if len(set(saisies)) != len(saisies):
        raise ZonesBlasonInvalides("Une même zone de score ne peut pas être admise deux fois.")
    # Avant le contrôle de `M` : sinon `zones=[]` sortirait « M ne peut pas être retirée », un
    # message vrai mais trompeur pour un admin qui n'a rien retiré du tout.
    if not any(zone is not ZoneScore.MANQUE for zone in saisies):
        raise ZonesBlasonInvalides("Un blason doit admettre au moins une zone marquante.")
    if ZoneScore.MANQUE not in saisies:
        raise ZonesBlasonInvalides(
            f"La zone « {ZoneScore.MANQUE.value} » (manqué) est toujours admise et ne peut pas "
            "être retirée."
        )

    retenues = set(saisies)
    return tuple(zone for zone in ZONES_CANONIQUES if zone in retenues)


def _extrait(valeur: object, taille_max: int = 20) -> str:
    """Rend `valeur` lisible dans un message d'erreur, **bornée** et proprement tronquée.

    **L'appelant visé n'est pas le client HTTP** : depuis que le DTO porte `list[ZoneScore]`,
    Pydantic rejette une zone hors vocabulaire en 400 et cette fonction n'est jamais atteinte par
    une requête. Elle sert les appelants **internes** que `valider_zones` est publique pour servir
    — import, script, réhydratation d'une colonne corrompue — dont la sortie va au **log serveur**.
    Un jeu de 10 Mo n'y a pas plus sa place que dans une réponse.
    *(L'amplification de l'écho dans une **réponse 400** est un autre sujet : elle vient de
    `jsonable_encoder(exc.errors())` à la frontière, vaut pour tous les DTO du projet — `ages`
    compris — et ne se traite pas ici.)*

    Ne lève **jamais** : elle construit un message d'erreur, échouer ici masquerait l'erreur
    d'origine. `repr()` d'un entier gigantesque lève `ValueError` (limite de conversion), et un
    `__repr__` maison peut lever n'importe quoi — d'où le filet large.
    """
    if isinstance(valeur, str):
        return f"{valeur[:taille_max]!r}…" if len(valeur) > taille_max else repr(valeur)
    try:
        brut = repr(valeur)
    # Filet volontairement large : cf. docstring, un formateur de message ne lève pas.
    except Exception:
        return f"<{type(valeur).__name__} irreprésentable>"
    return f"{brut[:taille_max]}…" if len(brut) > taille_max else brut
