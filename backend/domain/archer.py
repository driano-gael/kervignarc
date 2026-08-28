"""Agrégat **Archer** — la catégorie est obligatoire, le club ne l'est pas (ADR-0014).

⚠️ **`club_id is None` ne dit JAMAIS « cet archer n'a pas de club »** — en FFTA tout licencié en a
un. Il dit « on ne le sait pas **encore** » : une anomalie à résorber, pas un état légitime.
Inventer un club « Sans club » détruirait la nuance — deux archers partageraient le même `club_id`
et le placement les croirait du même club, une affirmation fausse là où `None` est honnête.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from domain.categorie import CategorieId
from domain.club import ClubId, cle_nom
from domain.erreurs import (
    CibleInvalide,
    HandicapInvalide,
    NomArcherInvalide,
    PrenomArcherInvalide,
)
from domain.tournoi import TournoiId

ArcherId = int
"""Identifiant technique d'un archer, attribué par la persistance."""

CleIdentite = tuple[str, str, ClubId | None]
"""Clé d'homonymie d'un archer — voir `cle_identite`."""

HANDICAP_MAXIMUM = 600
"""Borne haute d'un handicap (E05US015) : le score parfait d'une qualification FFTA
(20 volées de 3 flèches à 10).

Au-delà, le handicap ne corrige plus une différence de niveau — il **remplace** le tir."""


def cle_identite(nom: str, prenom: str, club_id: ClubId | None) -> CleIdentite:
    """Clé d'homonymie : deux archers de **même clé** sont vraisemblablement le même (E02US002).

    « Vraisemblablement » : un père et son fils partagent nom, prénom et club. La clé **signale**,
    elle ne refuse pas (`autoriser_homonyme`) — d'où l'absence de contrainte `UNIQUE` en base, qui
    rejetterait le fils. Replie casse et accents via `domain.club.cle_nom`, **réutilisé** plutôt
    que recopié. ⚠️ `club_id` entre **brut** : `None` = « club inconnu », jamais « aucun club »,
    donc un archer sans club n'est l'homonyme de personne (rapprochement = E02US005).
    """
    return (cle_nom(nom), cle_nom(prenom), club_id)


@dataclass(frozen=True)
class Archer:
    """Un archer inscrit à un tournoi. `id` vaut `None` tant qu'il n'est pas persisté.

    `cible` vaut `None` tant que l'archer n'est pas placé ; `club_id` vaut `None` tant que son club
    n'est pas **connu** (cf. docstring du module). **Handicap (E05US015)** — deux valeurs, jamais
    une seule, demande explicite du commanditaire (31/07/2026) : un handicap officiel **et** une
    **surcharge** par archer. Voir `handicap`.
    """

    nom: str
    prenom: str
    tournoi_id: TournoiId
    categorie_id: CategorieId
    cible: int | None = None
    club_id: ClubId | None = None
    handicap_officiel: int | None = None
    """Le handicap **de référence**, entretenu par le club (saisi ou importé avec les archers).

    ⚠️ **Aucune table de handicap n'est codée dans le produit.** Le projet n'en possède aucune : la
    FFTA n'a pas de système officiel, et celui qui fait référence est anglo-saxon (Archery GB /
    World Archery). En reconstituer une produirait des classements **plausibles mais faux** — le
    pire des défauts, puisqu'il ne se voit pas. C'est donc le club qui répond de la valeur, ce qui
    est cohérent avec le point faible reconnu du format : « le calcul du handicap doit être fiable »
    (règle donnée par le commanditaire)."""

    handicap_surcharge: int | None = None
    """La valeur qui **prime** l'officiel pour cette édition — le second volet de la demande.

    Sert au cas réel : un archer dont le handicap officiel est manifestement périmé (reprise après
    une longue absence, progression rapide d'un jeune) sans qu'on veuille pour autant réécrire la
    référence du club. La surcharge est **locale au tournoi**, l'officiel voyage."""

    id: ArcherId | None = None

    def __post_init__(self) -> None:
        """Un handicap s'**ajoute** au score : il est positif ou nul, et **borné** par le haut.

        Une valeur négative retrancherait des points et passerait inaperçue au classement, où elle
        ressemblerait à une contre-performance. ⚠️ **La borne haute est la même règle métier, pas
        une précaution technique** : `HANDICAP_MAXIMUM` vaut le score parfait d'une qualification
        FFTA, au-delà duquel le handicap **remplace** le tir. Effet utile : une valeur aberrante
        est refusée en 422 au lieu de remonter en 500 depuis SQLite.
        """
        for valeur, nom in (
            (self.handicap_officiel, "officiel"),
            (self.handicap_surcharge, "de surcharge"),
        ):
            if valeur is None:
                continue
            if valeur < 0:
                raise HandicapInvalide(
                    f"Le handicap {nom} s'ajoute au score réalisé : il est positif ou nul "
                    f"(reçu {valeur})."
                )
            if valeur > HANDICAP_MAXIMUM:
                raise HandicapInvalide(
                    f"Le handicap {nom} ne peut pas dépasser {HANDICAP_MAXIMUM}, le score parfait "
                    f"d'une qualification : au-delà, il pèserait plus que le tir (reçu {valeur})."
                )

    @property
    def handicap(self) -> int:
        """Le handicap **effectif** : la surcharge si elle existe, sinon l'officiel, sinon 0.

        `0` est le neutre du format (`score + 0 == score`), donc un archer sans handicap connu
        concourt au scratch sans casser un classement au handicap. C'est plus sûr qu'un `None` que
        chaque appelant devrait penser à traiter — l'oubli produirait une exception le jour J, au
        pire moment.
        """
        if self.handicap_surcharge is not None:
            return self.handicap_surcharge
        return self.handicap_officiel if self.handicap_officiel is not None else 0

    def avec_handicap(self, officiel: int | None = None, surcharge: int | None = None) -> Archer:
        """Renvoie une copie aux handicaps mis à jour — **remplacement total** des deux valeurs.

        Comme `modifier` et pour la même raison : un défaut implicite confondrait « je retire la
        surcharge » et « je n'y touche pas », alors que retirer la surcharge (revenir à l'officiel)
        est précisément une action que l'organisateur demandera.
        """
        return replace(self, handicap_officiel=officiel, handicap_surcharge=surcharge)

    @staticmethod
    def creer(
        nom: str,
        prenom: str,
        tournoi_id: TournoiId,
        categorie_id: CategorieId,
        club_id: ClubId | None = None,
    ) -> Archer:
        """Crée un archer valide.

        Le nom et le prénom sont normalisés (espaces de bord retirés) et ne peuvent pas être vides ;
        lève `NomArcherInvalide` / `PrenomArcherInvalide` sinon. L'agrégat ne **vérifie pas**
        l'existence de la catégorie ni du club (règles inter-agrégats portées par le service).
        """
        return Archer(
            nom=_texte_obligatoire(nom, NomArcherInvalide, "Le nom de l'archer"),
            prenom=_texte_obligatoire(prenom, PrenomArcherInvalide, "Le prénom de l'archer"),
            tournoi_id=tournoi_id,
            categorie_id=categorie_id,
            club_id=club_id,
        )

    def modifier(
        self,
        nom: str,
        prenom: str,
        categorie_id: CategorieId,
        club_id: ClubId | None,
    ) -> Archer:
        """Renvoie une copie éditée (E02US003) ; mêmes contrôles de saisie que `creer`.

        **Remplacement total, pas mise à jour partielle** : les quatre champs éditables sont
        exigés, `club_id` compris et ⚠️ **sans valeur par défaut** — un défaut à `None` confondrait
        « je détache le club » et « je n'y touche pas », et c'est le premier qui est demandé
        (ADR-0014). `tournoi_id`, `cible` et `id` traversent la copie intacts : éditer ne déplace
        pas.
        """
        return replace(
            self,
            nom=_texte_obligatoire(nom, NomArcherInvalide, "Le nom de l'archer"),
            prenom=_texte_obligatoire(prenom, PrenomArcherInvalide, "Le prénom de l'archer"),
            categorie_id=categorie_id,
            club_id=club_id,
        )

    def placer(self, cible: int) -> Archer:
        """Renvoie une copie placée sur `cible` ; lève `CibleInvalide` si `cible < 1`."""
        if cible < 1:
            raise CibleInvalide("Le numéro de cible doit être un entier strictement positif.")
        return replace(self, cible=cible)

    def cle_identite(self) -> CleIdentite:
        """Clé d'homonymie de cet archer (voir la fonction `cle_identite`)."""
        return cle_identite(self.nom, self.prenom, self.club_id)


def _texte_obligatoire(
    valeur: str, erreur: type[NomArcherInvalide | PrenomArcherInvalide], sujet: str
) -> str:
    """Normalise un champ texte obligatoire ; lève l'erreur de domaine donnée s'il est vide."""
    valeur_normalisee = valeur.strip()
    if not valeur_normalisee:
        raise erreur(f"{sujet} ne peut pas être vide.")
    return valeur_normalisee
