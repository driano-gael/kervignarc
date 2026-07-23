"""Détection de doublons d'archers (E02US005) — logique **pure** du domaine.

Deux fiches d'archer peuvent désigner **la même personne** saisie deux fois (l'erreur la plus
banale d'une table d'inscription) sans que les données le disent : il n'y a pas de numéro de
licence (repoussé à E02US007, ADR-0015), donc la détection est **heuristique**, jamais décidable.
On **rapproche** des paires vraisemblables et on les classe par certitude ; c'est l'admin qui
tranche et fusionne (`ServiceArchers.fusionner`) — la machine ne fusionne jamais d'office.

Deux niveaux (CA E02US005) :

- `PROBABLE` — mêmes nom et prénom (casse **et** accents repliés, `cle_nom`) **et** clubs
  compatibles : club identique, **ou** l'un des deux « club inconnu » (`club_id is None`). Ce
  dernier cas — le **pont** avec/sans club — est celui que la détection à l'inscription exclut
  délibérément (`domain.archer.cle_identite`, qui renvoie explicitement ici) : à l'inscription, on
  ne rapproche pas un archer sans club d'un archer rattaché, faute de savoir ; ici, l'admin le peut.
- `A_VERIFIER` — rapprochement **approximatif** : faute de frappe (distance d'édition faible),
  prénom **abrégé** (« J » / « Jean »), ou mêmes nom et prénom mais **clubs connus différents**.
  Signalé pour confirmation, pas tenu pour acquis — ces rapprochements produisent des faux positifs
  que l'admin écarte à l'œil (arbitrage du 22/07/2026 : le prix d'attraper plus de doublons réels).

Module **pur** (règle 1) : aucune dépendance framework, aucune lecture de persistance. La distance
d'édition est **maison** (`distance_edition`) — quelques lignes plutôt qu'une dépendance de
fuzzy-matching (règle 11).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from domain.archer import Archer
from domain.club import cle_nom

# Seuil de distance d'édition (nom + prénom repliés) en deçà duquel deux fiches sont « à vérifier ».
# 2 laisse passer une faute de frappe simple (une lettre fausse dans le nom **et** le prénom, ou
# deux dans l'un) sans rapprocher deux patronymes courts et distincts au-delà du raisonnable
# — la borne exacte est un arbitrage assumé (faux positifs admis, ils sont « à vérifier »).
_SEUIL_DISTANCE = 2


class NiveauDoublon(Enum):
    """Certitude d'un rapprochement (CA E02US005). L'ordre sert au tri : `PROBABLE` d'abord."""

    PROBABLE = "probable"
    A_VERIFIER = "a_verifier"


@dataclass(frozen=True)
class PaireDoublon:
    """Deux fiches rapprochées et le niveau de certitude du rapprochement.

    `a` et `b` sont ordonnés par identifiant croissant (`a.id < b.id`) : la paire est **non
    orientée** (le rapprochement ne désigne pas encore de gagnant/perdant — c'est la fusion qui le
    fera), et cet ordre la rend **déterministe** à l'affichage comme au test.
    """

    a: Archer
    b: Archer
    niveau: NiveauDoublon


def distance_edition(a: str, b: str) -> int:
    """Distance de Levenshtein entre deux chaînes (insertions/suppressions/substitutions).

    Implémentation **maison** à deux lignes de tableau (mémoire O(min-ish), en fait O(len(b))) :
    quelques centaines d'archers par tournoi, comparés deux à deux sur des noms courts — inutile
    d'ajouter une dépendance (règle 11). Sert au niveau « à vérifier » (faute de frappe).
    """
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    precedente = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        courante = [i]
        for j, cb in enumerate(b, start=1):
            cout = 0 if ca == cb else 1
            courante.append(min(courante[j - 1] + 1, precedente[j] + 1, precedente[j - 1] + cout))
        precedente = courante
    return precedente[-1]


def detecter_doublons(archers: list[Archer]) -> list[PaireDoublon]:
    """Rapproche les paires d'archers vraisemblablement en double, classées par certitude.

    Balayage **quadratique** de toutes les paires (n²/2) : à l'échelle d'un tournoi de club
    (quelques centaines d'inscrits), c'est immédiat et sans état — l'écran recalcule à l'ouverture
    (on ne persiste pas les paires écartées, cf. story). Le tri final — `PROBABLE` d'abord, puis
    par identifiants — rend la liste **déterministe**.
    """
    paires: list[PaireDoublon] = []
    for i, a in enumerate(archers):
        for b in archers[i + 1 :]:
            niveau = _rapprocher(a, b)
            if niveau is not None:
                paires.append(_paire_ordonnee(a, b, niveau))
    return sorted(
        paires,
        key=lambda p: (0 if p.niveau is NiveauDoublon.PROBABLE else 1, p.a.id or 0, p.b.id or 0),
    )


def _rapprocher(a: Archer, b: Archer) -> NiveauDoublon | None:
    """Niveau de rapprochement de deux fiches, ou `None` si elles ne se ressemblent pas."""
    nom_a, prenom_a = cle_nom(a.nom), cle_nom(a.prenom)
    nom_b, prenom_b = cle_nom(b.nom), cle_nom(b.prenom)
    meme_identite = nom_a == nom_b and prenom_a == prenom_b

    if meme_identite and _clubs_compatibles(a, b):
        return NiveauDoublon.PROBABLE

    # Mêmes nom et prénom mais clubs **connus et différents** : ni un doublon probable (les clubs
    # départagent, comme à l'inscription — `cle_identite` porte le club brut), ni rien (l'identité
    # est trop proche pour l'ignorer). C'est exactement « à vérifier ».
    if meme_identite:
        return NiveauDoublon.A_VERIFIER

    # Prénom abrégé (« J » / « Jean ») sur un même nom : la distance d'édition seule le raterait
    # (« j » vs « jean-baptiste » est loin), l'abréviation le rattrape.
    if nom_a == nom_b and _est_abreviation(prenom_a, prenom_b):
        return NiveauDoublon.A_VERIFIER

    # Faute de frappe : une petite distance d'édition cumulée sur le nom **et** le prénom.
    distance = distance_edition(nom_a, nom_b) + distance_edition(prenom_a, prenom_b)
    if 1 <= distance <= _SEUIL_DISTANCE:
        return NiveauDoublon.A_VERIFIER

    return None


def _clubs_compatibles(a: Archer, b: Archer) -> bool:
    """Deux clubs sont compatibles s'ils sont **égaux** ou si **l'un est inconnu** (`None`).

    `None` = « club pas encore su » (ADR-0014), jamais « aucun club » : un archer sans club **peut**
    être le même qu'un archer rattaché — c'est précisément le pont que l'inscription n'ose pas
    franchir et que la fusion permet.
    """
    return a.club_id == b.club_id or a.club_id is None or b.club_id is None


def _est_abreviation(x: str, y: str) -> bool:
    """Vrai si une chaîne est un **préfixe strict** non vide de l'autre (« J » ⊂ « Jean »).

    Strict (`len(court) < len(long)`) : deux chaînes égales ne sont pas une abréviation l'une de
    l'autre (ce cas relève de l'identité, traité en amont), et le préfixe doit compter au moins une
    lettre — une initiale vide ne rapproche rien.
    """
    court, long = (x, y) if len(x) <= len(y) else (y, x)
    return 1 <= len(court) < len(long) and long.startswith(court)


def _paire_ordonnee(a: Archer, b: Archer, niveau: NiveauDoublon) -> PaireDoublon:
    """Range la paire par identifiant croissant (déterminisme d'affichage et de test)."""
    if (a.id or 0) <= (b.id or 0):
        return PaireDoublon(a, b, niveau)
    return PaireDoublon(b, a, niveau)
