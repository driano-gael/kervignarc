"""Agrégat `Scoreur` — une personne habilitée à **valider** les scores d'un tournoi (E10US003).

Un **scoreur** est un bénévole **itinérant** (CDC UX §7.3, `D-12`) : rattaché à **aucune cible**, il
choisit celle dont il valide les scores. 3 à 4 scoreurs par tournoi (~30 cibles). Il est identifié
par **la personne** — un `code` court, individuel, distribué sur papier (`D-13`) —, à la différence
du poste de cible (identité = le **lieu**, sans code, E10US007) et de l'admin (identité = **un
secret**, E10US002). Il n'y a **pas de rôle archer** : la tablette de saisie est ouverte ; le
scoreur, lui, **valide** et doit donc être tracé.

Entité **du tournoi** (`tournoi_id`), comme `Depart` : les scoreurs se définissent à la
configuration du tournoi et sont **redéfinissables à tout moment** (`D-14`). Agrégat **pur** (aucune
dépendance framework, immuable) : `creer` / `modifier` valident et renvoient une copie.

Le `code` est **attribué par le service** (comme `Depart.numero`) : le domaine ne voit qu'un scoreur
à la fois, il ne peut donc pas garantir l'unicité — c'est une règle d'ensemble portée par
`ServiceScoreurs` (génération avec ré-essai + `UNIQUE` en base). Le domaine ne fait que
**normaliser** le code (`normaliser_code`) et vérifier qu'il n'est pas vide.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from domain.erreurs import CodeScoreurInvalide, NomScoreurInvalide
from domain.tournoi import TournoiId

ScoreurId = int
"""Identifiant technique d'un scoreur, attribué par la persistance."""


def normaliser_code(code: str) -> str:
    """Forme canonique d'un code de scoreur : espaces de bord retirés, **majuscules**.

    Deux codes de même forme normalisée désignent le même code. Sert à **stocker** (le code généré
    est déjà canonique) **et** à **comparer** la saisie du scoreur à la connexion : « ab12cd »,
    « AB12CD » et «  AB12CD  » ouvrent la même session. Le pendant, pour les noms de clubs et
    d'archers, est `domain.club.cle_nom` — mais un code tiré d'un alphabet restreint n'a ni casse
    accentuée ni accent à replier : d'où une règle distincte, plus simple (pas de `casefold`/NFKD).
    """
    return code.strip().upper()


@dataclass(frozen=True)
class Scoreur:
    """Un scoreur d'un tournoi. `id` vaut `None` tant qu'il n'est pas persisté.

    `code` est la forme **canonique** (cf. `normaliser_code`) du code individuel remis au scoreur ;
    `nom` est le nom sous lequel ses validations seront tracées (E10US005).
    """

    tournoi_id: TournoiId
    nom: str
    code: str
    id: ScoreurId | None = None

    @staticmethod
    def creer(tournoi_id: TournoiId, nom: str, code: str) -> Scoreur:
        """Crée un scoreur valide.

        Le `nom` est normalisé (espaces de bord retirés) et ne peut pas être vide
        (`NomScoreurInvalide`). Le `code` est normalisé (`normaliser_code`) et ne peut pas être vide
        (`CodeScoreurInvalide`) — il est **attribué par le service** (généré), jamais saisi ici.
        """
        return Scoreur(
            tournoi_id=tournoi_id,
            nom=_nom_valide(nom),
            code=_code_valide(code),
        )

    def modifier(self, nom: str) -> Scoreur:
        """Renvoie une copie au nom mis à jour (mêmes règles que `creer`).

        L'`id`, le `tournoi_id` et surtout le `code` sont **préservés** : le code a été imprimé et
        remis au scoreur, le régénérer à chaque édition invaliderait le papier distribué. Seul le
        nom se corrige (faute de frappe) — même parti que `Depart.modifier`, qui fige le `numero`
        attribué par le système.
        """
        return replace(self, nom=_nom_valide(nom))


def _nom_valide(nom: str) -> str:
    """Normalise le nom ; lève `NomScoreurInvalide` s'il est vide."""
    nom_normalise = nom.strip()
    if not nom_normalise:
        raise NomScoreurInvalide("Le nom d'un scoreur ne peut pas être vide.")
    return nom_normalise


def _code_valide(code: str) -> str:
    """Normalise le code ; lève `CodeScoreurInvalide` s'il est vide.

    Le code est **généré** (jamais saisi à la création) : cette garde protège l'invariant à la
    construction de l'agrégat, elle n'est pas un contrôle d'entrée utilisateur.
    """
    code_normalise = normaliser_code(code)
    if not code_normalise:
        raise CodeScoreurInvalide("Le code d'un scoreur ne peut pas être vide.")
    return code_normalise
