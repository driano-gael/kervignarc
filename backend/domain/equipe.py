"""Agrégat **Equipe** — entité du tournoi, composée d'archers (E13US002, ADR-0028 point 2).

⚠️ **La composition est signalée, jamais bloquée** : une équipe se forme membre par membre et
traverse forcément des états non conformes. `ecarts_de_composition` les décrit ; le refus d'une
équipe non conforme appartient à son engagement dans une phase (E13US004).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import Enum

from domain.archer import ArcherId
from domain.categorie import SexeCategorie
from domain.erreurs import (
    ArcherDejaMembre,
    ArcherNonMembre,
    EffectifEquipeInvalide,
    NomEquipeInvalide,
)
from domain.tournoi import TournoiId

EquipeId = int
"""Identifiant technique d'une équipe, attribué par la persistance."""


class TypeEquipe(str, Enum):
    STANDARD = "standard"
    MIXTE = "mixte"


EFFECTIF_FFTA: dict[TypeEquipe, int] = {TypeEquipe.STANDARD: 3, TypeEquipe.MIXTE: 2}
"""Effectif par défaut d'un type d'équipe — référentiel FFTA §6.4 et §7."""


@dataclass(frozen=True)
class Equipe:
    """Une équipe d'un tournoi. `id` vaut `None` tant qu'elle n'est pas persistée.

    `membres` est ordonné par **ordre d'ajout** : c'est l'ordre dans lequel l'organisateur a
    composé l'équipe, celui qu'il retrouve à l'écran.
    """

    tournoi_id: TournoiId
    nom: str
    type: TypeEquipe
    effectif_attendu: int
    membres: tuple[ArcherId, ...] = ()
    id: EquipeId | None = None

    @staticmethod
    def creer(
        tournoi_id: TournoiId,
        nom: str,
        type: TypeEquipe,
        effectif_attendu: int | None = None,
    ) -> Equipe:
        """`effectif_attendu` absent : le défaut FFTA du type (`EFFECTIF_FFTA`)."""
        return Equipe(
            tournoi_id=tournoi_id,
            nom=_nom_valide(nom),
            type=type,
            effectif_attendu=_effectif_valide(type, effectif_attendu),
        )

    def modifier(self, nom: str, type: TypeEquipe, effectif_attendu: int | None = None) -> Equipe:
        """Mêmes règles que `creer` ; `id`, `tournoi_id` et `membres` sont préservés."""
        return replace(
            self,
            nom=_nom_valide(nom),
            type=type,
            effectif_attendu=_effectif_valide(type, effectif_attendu),
        )

    def ajouter_membre(self, archer_id: ArcherId) -> Equipe:
        if archer_id in self.membres:
            raise ArcherDejaMembre(f"L'archer {archer_id} figure déjà dans l'équipe {self.nom}.")
        return replace(self, membres=(*self.membres, archer_id))

    def retirer_membre(self, archer_id: ArcherId) -> Equipe:
        if archer_id not in self.membres:
            raise ArcherNonMembre(f"L'archer {archer_id} ne figure pas dans l'équipe {self.nom}.")
        return replace(self, membres=tuple(m for m in self.membres if m != archer_id))


class EcartComposition(str, Enum):
    """Ce qui rend une équipe non conforme — dans l'ordre où `ecarts_de_composition` les rend."""

    EFFECTIF_INSUFFISANT = "effectif_insuffisant"
    EFFECTIF_EXCEDENTAIRE = "effectif_excedentaire"
    ARMES_DIFFERENTES = "armes_differentes"
    ARME_NON_VERIFIABLE = "arme_non_verifiable"
    MIXITE_MANQUANTE = "mixite_manquante"
    SEXES_DIFFERENTS = "sexes_differents"
    SEXE_NON_VERIFIABLE = "sexe_non_verifiable"


@dataclass(frozen=True)
class ProfilMembre:
    """Ce que la composition lit d'un membre : arme et sexe **de sa catégorie** (CA 5).

    L'archer ne porte ni l'un ni l'autre (arbitrage du 01/10/2026) : c'est le service qui résout la
    catégorie de chaque membre et construit ce profil.
    """

    arme: str | None
    sexe: SexeCategorie | None


def ecarts_de_composition(
    equipe: Equipe, profils: Sequence[ProfilMembre]
) -> tuple[EcartComposition, ...]:
    """Les écarts de l'équipe à sa règle de composition ; `()` si elle est conforme.

    ⚠️ **On ne devine dans aucun sens** : une arme ou un sexe inconnu rend le critère « non
    vérifiable », sans effacer pour autant une différence **déjà établie** entre membres connus.
    """
    ecarts: list[EcartComposition] = []
    if len(profils) < equipe.effectif_attendu:
        ecarts.append(EcartComposition.EFFECTIF_INSUFFISANT)
    elif len(profils) > equipe.effectif_attendu:
        ecarts.append(EcartComposition.EFFECTIF_EXCEDENTAIRE)
    if not profils:
        return tuple(ecarts)
    ecarts.extend(_ecarts_d_arme(profils))
    ecarts.extend(_ecarts_de_sexe(equipe.type, profils))
    return tuple(ecarts)


def _ecarts_d_arme(profils: Sequence[ProfilMembre]) -> list[EcartComposition]:
    # L'arme est un texte libre de catégorie : on compare sa forme repliée, pas sa saisie.
    connues = {p.arme.strip().casefold() for p in profils if p.arme and p.arme.strip()}
    ecarts = []
    if len(connues) > 1:
        ecarts.append(EcartComposition.ARMES_DIFFERENTES)
    if any(not (p.arme and p.arme.strip()) for p in profils):
        ecarts.append(EcartComposition.ARME_NON_VERIFIABLE)
    return ecarts


def _ecarts_de_sexe(type: TypeEquipe, profils: Sequence[ProfilMembre]) -> list[EcartComposition]:
    # Une catégorie « mixte » ne dit pas le sexe de l'archer : il est inconnu, comme sans sexe.
    connus = {p.sexe for p in profils if p.sexe in (SexeCategorie.HOMME, SexeCategorie.FEMME)}
    inconnu = any(p.sexe not in (SexeCategorie.HOMME, SexeCategorie.FEMME) for p in profils)
    ecarts = []
    if type is TypeEquipe.MIXTE:
        if not inconnu and connus != {SexeCategorie.HOMME, SexeCategorie.FEMME}:
            ecarts.append(EcartComposition.MIXITE_MANQUANTE)
    elif len(connus) > 1:
        ecarts.append(EcartComposition.SEXES_DIFFERENTS)
    if inconnu:
        ecarts.append(EcartComposition.SEXE_NON_VERIFIABLE)
    return ecarts


def _nom_valide(nom: str) -> str:
    nom_normalise = nom.strip()
    if not nom_normalise:
        raise NomEquipeInvalide("Le nom d'une équipe ne peut pas être vide.")
    return nom_normalise


def _effectif_valide(type: TypeEquipe, effectif_attendu: int | None) -> int:
    effectif = EFFECTIF_FFTA[type] if effectif_attendu is None else effectif_attendu
    if effectif <= 0:
        raise EffectifEquipeInvalide(
            "L'effectif attendu d'une équipe doit être un entier strictement positif."
        )
    return effectif
