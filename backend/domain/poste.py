"""Agrégat `Poste` — le credential d'une **cible** d'un tournoi (E04US001, ADR-0029).

Un `Poste` matérialise le couple `(tournoi_id, cible_index)` — la cible elle-même reste un value
object dérivé du `GabaritSalle`, sans identité propre — augmenté d'un **code** distribuable : le
code imprimé sous le QR (E09US008), retapé à la main en secours pour **rattacher** une tablette à sa
cible. C'est le **troisième mode d'identité** du projet (`D-13` : le *lieu*), après le scoreur (la
*personne*, ADR-0025) et l'admin (un *secret*).

Le `code` est **attribué par le service** (comme `Scoreur.code`, `Depart.numero`) : le domaine ne
voit qu'un poste à la fois, il ne peut garantir l'unicité — c'est une règle d'ensemble portée par
`ServicePostes` (génération avec ré-essai + `UNIQUE` en base). Le domaine ne fait que **normaliser**
le code et vérifier ses invariants. Agrégat **pur** (aucune dépendance framework, immuable).

`normaliser_code` est volontairement **dupliqué** de `domain.scoreur` (2ᵉ occurrence d'un « code de
terrain retapé ») : importer l'un dans l'autre couplerait deux agrégats distincts pour trois lignes.
On attend une **3ᵉ** preuve avant tout remède structurel (règle « dette »).
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.erreurs import CibleInvalide, CodePosteInvalide
from domain.tournoi import TournoiId

PosteId = int
"""Identifiant technique d'un poste, attribué par la persistance."""


def normaliser_code(code: str) -> str:
    """Forme canonique d'un code de cible : espaces de bord retirés, **majuscules**.

    Sert à **stocker** (le code généré est déjà canonique) **et** à **comparer** la saisie de
    rattachement : « ab12cd », « AB12CD » et «  AB12CD  » désignent le même poste. L'alphabet du
    code n'a ni accent ni casse accentuée, d'où une règle plus simple que `domain.club.cle_nom`
    (pas de `casefold`/NFKD).
    """
    return code.strip().upper()


@dataclass(frozen=True)
class Poste:
    """Le poste (credential) d'une cible. `id` vaut `None` tant qu'il n'est pas persisté.

    `code` est la forme **canonique** (cf. `normaliser_code`) du code imprimé sous le QR de la
    cible ; `cible_index` est le rang **1-based** de la cible dans le plan (`GabaritSalle.cibles`).
    """

    tournoi_id: TournoiId
    cible_index: int
    code: str
    id: PosteId | None = None

    @staticmethod
    def creer(tournoi_id: TournoiId, cible_index: int, code: str) -> Poste:
        """Crée un poste valide.

        `cible_index` doit être un entier **strictement positif** (`CibleInvalide`). Le `code` est
        normalisé (`normaliser_code`) et ne peut pas être vide (`CodePosteInvalide`) — il est
        **attribué par le service** (généré), jamais saisi ici.
        """
        return Poste(
            tournoi_id=tournoi_id,
            cible_index=_cible_valide(cible_index),
            code=_code_valide(code),
        )


def _cible_valide(cible_index: int) -> int:
    """Vérifie que l'index de cible est un entier strictement positif ; lève `CibleInvalide`."""
    if cible_index < 1:
        raise CibleInvalide(
            "Le numéro de cible d'un poste doit être un entier strictement positif."
        )
    return cible_index


def _code_valide(code: str) -> str:
    """Normalise le code ; lève `CodePosteInvalide` s'il est vide.

    Le code est **généré** (jamais saisi à la création) : cette garde protège l'invariant à la
    construction de l'agrégat, elle n'est pas un contrôle d'entrée utilisateur.
    """
    code_normalise = normaliser_code(code)
    if not code_normalise:
        raise CodePosteInvalide("Le code d'un poste ne peut pas être vide.")
    return code_normalise
