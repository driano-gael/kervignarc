"""Agrégat `Poste` — le credential d'un **point de rattachement** d'un tournoi (E04US001, ADR-0029 ;
élargi aux écrans de salle par E07US004, ADR-0064).

Un `Poste` matérialise un lieu du gymnase augmenté d'un **code** distribuable : le code imprimé sous
le QR (E09US008), retapé à la main en secours pour **rattacher** un appareil à ce lieu. C'est le
**troisième mode d'identité** du projet (`D-13` : le *lieu*), après le scoreur (la *personne*,
ADR-0025) et l'admin (un *secret*).

Deux natures (`TypePoste`) :

- **cible** — le couple `(tournoi_id, cible_index)` d'origine ; la cible elle-même reste un value
  object dérivé du `GabaritSalle`, sans identité propre ;
- **écran** — un écran de salle, désigné par un **libellé** de place (« près du pas de tir »). Le
  CA d'E07US004 est explicite : *« l'écran est un poste de l'appli publique rattaché par jeton (même
  mécanisme que la tablette de cible) »*. Le typer ici plutôt que d'inventer un second agrégat fait
  hériter gratuitement le jeton, le heartbeat et la console de supervision — dont le CA a besoin
  (« un écran figé ne se plaint pas, seule la supervision le révèle »).

Le typage rend `cible_index` facultatif. Pour que cette facultativité ne se dilue pas en `None`
silencieux chez les appelants, l'invariant « seul un poste de cible a une cible » est **exigible au
point d'usage** : `Poste.cible()` lève plutôt que de rendre `None`.

Le `code` est **attribué par le service** (comme `Scoreur.code`, `Depart.numero`) : le domaine ne
voit qu'un poste à la fois, il ne peut garantir l'unicité — c'est une règle d'ensemble portée par
`ServicePostes` (génération avec ré-essai + `UNIQUE` en base). Le domaine ne fait que **normaliser**
le code et vérifier ses invariants. Agrégat **pur** (aucune dépendance framework, immuable).

`normaliser_code` est volontairement **dupliqué** de `domain.scoreur` (2ᵉ occurrence d'un « code de
terrain retapé ») : importer l'un dans l'autre couplerait deux agrégats distincts pour trois lignes.
On attend une **3ᵉ** preuve avant tout remède structurel (règle « dette »).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from domain.ecran import SequenceVues
from domain.erreurs import (
    CibleInvalide,
    CodePosteInvalide,
    LibelleEcranInvalide,
    PosteSansCible,
    PosteSansEcran,
)
from domain.tournoi import TournoiId

PosteId = int
"""Identifiant technique d'un poste, attribué par la persistance."""


class TypePoste(str, Enum):
    """Ce à quoi un poste est rattaché — la cible d'un tireur, ou un écran de salle (E07US004).

    `str, Enum` comme `TypePhase` : la valeur est aussi bien la forme persistée que la forme
    exposée, sans table de correspondance à tenir à jour de part et d'autre.
    """

    CIBLE = "cible"
    ECRAN = "ecran"


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
    """Le poste (credential) d'une cible ou d'un écran. `id` vaut `None` tant qu'il n'est pas
    persisté.

    `code` est la forme **canonique** (cf. `normaliser_code`) du code imprimé sous le QR ;
    `cible_index` est le rang **1-based** de la cible dans le plan (`GabaritSalle.cibles`), présent
    pour les seuls postes de type `CIBLE` ; `libelle` désigne la place d'un écran dans le gymnase,
    présent pour les seuls postes de type `ECRAN`.

    Les deux champs sont facultatifs **au type de données** et exclusifs **à l'invariant** : les
    constructeurs nommés sont la seule voie normale de création, et `cible()` refuse le mésusage.

    `deroule` est le réglage propre d'un écran (« **chacun son déroulé** », CA) — donc bien un état
    de *cet* agrégat, et non une table satellite : l'écran **est** le poste. `None` signifie « rien
    n'a été réglé » et se lit par `deroule_effectif`, qui rend le déroulé par défaut du CA.
    """

    tournoi_id: TournoiId
    cible_index: int | None
    code: str
    type: TypePoste = TypePoste.CIBLE
    libelle: str | None = None
    deroule: SequenceVues | None = None
    id: PosteId | None = None

    @staticmethod
    def creer(tournoi_id: TournoiId, cible_index: int, code: str) -> Poste:
        """Crée le poste d'une **cible**.

        `cible_index` doit être un entier **strictement positif** (`CibleInvalide`). Le `code` est
        normalisé (`normaliser_code`) et ne peut pas être vide (`CodePosteInvalide`) — il est
        **attribué par le service** (généré), jamais saisi ici.

        Le nom reste `creer` (et non `creer_cible`) : c'est le cas d'origine, appelé partout, et le
        renommer aurait produit un diff de churn sans rien apprendre au lecteur.
        """
        return Poste(
            tournoi_id=tournoi_id,
            cible_index=_cible_valide(cible_index),
            code=_code_valide(code),
            type=TypePoste.CIBLE,
            libelle=None,
        )

    @staticmethod
    def creer_ecran(
        tournoi_id: TournoiId,
        libelle: str,
        code: str,
        deroule: SequenceVues | None = None,
    ) -> Poste:
        """Crée le poste d'un **écran de salle** (E07US004).

        Pas de cible : un écran informe, il ne collecte pas. Le `libelle` est nettoyé de ses espaces
        de bord et ne peut pas être vide (`LibelleEcranInvalide`) — c'est lui qui désigne l'écran
        dans la console au moment de le piloter. Il n'est **pas unique** : deux écrans « entrée » ne
        sont pas une incohérence, seulement une désignation paresseuse.
        """
        return Poste(
            tournoi_id=tournoi_id,
            cible_index=None,
            code=_code_valide(code),
            type=TypePoste.ECRAN,
            libelle=_libelle_valide(libelle),
            deroule=deroule,
        )

    def avec_deroule(self, deroule: SequenceVues) -> Poste:
        """Rend une copie de cet écran avec un autre déroulé (agrégat immuable, règle 4)."""
        if self.type is not TypePoste.ECRAN:
            raise PosteSansEcran("Seul un écran de salle porte un déroulé de vues.")
        return replace(self, deroule=deroule)

    def avec_libelle(self, libelle: str) -> Poste:
        """Rend une copie de cet écran renommé (l'écran déménage dans le gymnase)."""
        if self.type is not TypePoste.ECRAN:
            raise PosteSansEcran("Seul un écran de salle porte un libellé.")
        return replace(self, libelle=_libelle_valide(libelle))

    @property
    def deroule_effectif(self) -> SequenceVues:
        """Le déroulé que cet écran joue réellement — le sien, ou celui **par défaut** du CA.

        Résoudre le défaut **ici** plutôt que chez chaque appelant garantit qu'un écran fraîchement
        créé informe sans configuration, et qu'aucune surface ne peut afficher « aucune vue ».
        """
        if self.type is not TypePoste.ECRAN:
            raise PosteSansEcran("Seul un écran de salle joue un déroulé de vues.")
        return self.deroule if self.deroule is not None else SequenceVues.par_defaut()

    def cible(self) -> int:
        """L'index de cible de ce poste ; lève `PosteSansCible` si ce n'en est pas un.

        Point d'exigence de l'invariant : saisir un score, fixer un départ courant ou figurer dans
        l'avancement d'une cible n'a de sens que pour un poste de type `CIBLE`. Lever plutôt que
        rendre `None` évite qu'un appelant oublie le cas et affiche « cible None ».
        """
        if self.type is not TypePoste.CIBLE or self.cible_index is None:
            raise PosteSansCible("Ce poste n'est pas rattaché à une cible.")
        return self.cible_index


LIBELLE_ECRAN_MAX = 60
"""Longueur maximale du libellé d'un écran.

Borne **haute** ajoutée en revue : `code` et `cible_index` étaient bornés, pas le libellé. Une
chaîne de dix mille caractères traversait jusqu'à la console de supervision **et** au bandeau plein
écran d'un vidéoprojecteur. 60 caractères tiennent largement « Près du pas de tir, côté buvette » et
restent lisibles de loin — c'est un repère de place dans un gymnase, pas une phrase.
"""


def _libelle_valide(libelle: str) -> str:
    """Nettoie le libellé d'un écran ; lève `LibelleEcranInvalide` s'il est vide ou trop long."""
    nettoye = libelle.strip()
    if not nettoye:
        raise LibelleEcranInvalide("Le libellé d'un écran de salle ne peut pas être vide.")
    if len(nettoye) > LIBELLE_ECRAN_MAX:
        raise LibelleEcranInvalide(
            f"Le libellé d'un écran de salle ne peut pas dépasser {LIBELLE_ECRAN_MAX} caractères."
        )
    return nettoye


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
