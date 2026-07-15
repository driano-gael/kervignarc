"""Agrégat `Archer` — participant d'un tournoi (E00US011, complété par E02US002).

Gabarit d'agrégat **pur** (aucune dépendance framework, immuable) : un archer appartient à un
tournoi, porte un `nom` et un `prenom`, tire dans une **catégorie** (obligatoire), peut être
rattaché à un **club** (facultatif — voir ci-dessous) et peut être **placé** sur une cible
(numéro de peloton). Le placement reste celui du walking skeleton (un simple numéro) ; les vraies
contraintes (capacité 1/2/4, ≥ 2 clubs/cible, blason = fraction de place) l'enrichiront en EPIC-03.

**Pourquoi la catégorie est obligatoire et pas le club** (ADR-0014). La catégorie se lit sur
l'archer présent (son âge, son arme) et commande tout le reste : sans elle, il n'est ni classable,
ni plaçable, ni facturable — c'est un état inexploitable, pas une donnée manquante. Le club, lui,
est une donnée **administrative externe** : le jour J, la licence est restée dans la voiture. En
FFTA tout licencié a pourtant un club, donc `club_id is None` ne dit **jamais** « cet archer n'a pas
de club » — il dit « on ne le sait pas **encore** ». C'est une anomalie à résorber, que l'écran des
archers signale et que E12US005 comptera ; ce n'est pas un état légitime, et surtout ce n'est pas un
club. Inventer un club « Sans club » pour combler le trou détruirait précisément cette nuance : deux
archers y seraient rattachés au **même** `club_id`, et le placement (E03US006, RG-3) les croirait du
même club — une affirmation fausse là où `None` dit honnêtement « inconnu ».

L'existence du club et de la catégorie référencés est vérifiée par le service applicatif : le
domaine ne lit pas la persistance (règle 1).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from domain.categorie import CategorieId
from domain.club import ClubId, cle_nom
from domain.erreurs import CibleInvalide, NomArcherInvalide, PrenomArcherInvalide
from domain.tournoi import TournoiId

ArcherId = int
"""Identifiant technique d'un archer, attribué par la persistance."""

CleIdentite = tuple[str, str, ClubId | None]
"""Clé d'homonymie d'un archer — voir `cle_identite`."""


def cle_identite(nom: str, prenom: str, club_id: ClubId | None) -> CleIdentite:
    """Clé d'homonymie : deux archers de **même clé** sont vraisemblablement le même (E02US002).

    « Vraisemblablement » et non « certainement » : deux archers **réels** peuvent partager cette
    clé — un père et son fils, mêmes nom, prénom et club, arrivent en compétition de club. La clé
    sert donc à **signaler** un doublon probable à la saisie, pas à le refuser ; c'est l'admin qui
    tranche (`ServiceArchers.ajouter(autoriser_homonyme=True)`). C'est aussi pourquoi aucune
    contrainte `UNIQUE` ne la double en base : elle rejetterait le fils.

    Replie la casse et les accents du nom et du prénom via `cle_nom` — « Lefèvre Rémi » saisi
    « LEFEVRE remi » sur une tablette est le doublon le plus probable, et c'est exactement le repli
    que le référentiel des clubs applique déjà (E02US001). On **réutilise** `domain.club.cle_nom`
    plutôt que de le recopier : deux règles de repli qui divergent, c'est un doublon accepté ici et
    refusé là. C'est son **1ᵉʳ usage hors du concept « club »** (le 3ᵉ en tout — cf. sa docstring) ;
    à un 2ᵉ hors club, l'extraire dans un module de texte se justifiera, en US dédiée.

    `club_id` entre dans la clé **brut** : deux homonymes de clubs différents sont deux archers
    distincts. Et comme `None` signifie « club inconnu » (jamais « aucun club »), un archer sans
    club n'est **pas** l'homonyme d'un archer rattaché : les rapprocher supposerait de savoir ce
    qu'on ignore justement. Ce rapprochement-là relève de E02US005 (détecter et fusionner).
    """
    return (cle_nom(nom), cle_nom(prenom), club_id)


@dataclass(frozen=True)
class Archer:
    """Un archer inscrit à un tournoi. `id` vaut `None` tant qu'il n'est pas persisté.

    `cible` vaut `None` tant que l'archer n'est pas placé (E00US011 : un simple numéro).
    `club_id` vaut `None` tant que son club n'est pas **connu** (cf. docstring du module).
    """

    nom: str
    prenom: str
    tournoi_id: TournoiId
    categorie_id: CategorieId
    cible: int | None = None
    club_id: ClubId | None = None
    id: ArcherId | None = None

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
