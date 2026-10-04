"""Service des **équipes** d'un tournoi (E13US002) — règles d'ensemble que l'agrégat ne voit pas.

⚠️ La composition est **signalée, jamais bloquée** (CA 4) : aucune écriture n'est refusée pour un
écart de composition ; seuls l'unicité du nom, l'appartenance au tournoi et « une équipe par type »
(CA 3) le sont.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol

from application.erreurs import (
    ArcherDejaEnEquipe,
    ArcherHorsTournoi,
    CompositionEquipeVerrouillee,
    EquipeIntrouvable,
    MembreIntrouvable,
    NomEquipeDejaPris,
    TournoiIntrouvable,
)
from domain.archer import Archer, ArcherId
from domain.categorie import Categorie, CategorieId
from domain.club import cle_nom
from domain.equipe import (
    EcartComposition,
    Equipe,
    EquipeId,
    ProfilMembre,
    TypeEquipe,
    conflit_de_type,
    ecarts_de_composition,
)
from domain.ports import ArcherRepository, CategorieRepository, EquipeRepository, TournoiRepository
from domain.tournoi import TournoiId


@dataclass(frozen=True)
class MembreVu:
    archer_id: ArcherId
    nom: str
    prenom: str
    categorie: str


@dataclass(frozen=True)
class EquipeVue:
    """Une équipe telle que l'écran la montre : ses membres résolus et ses écarts (CA 4, CA 8)."""

    equipe: Equipe
    membres: tuple[MembreVu, ...]
    ecarts: tuple[EcartComposition, ...]

    @property
    def conforme(self) -> bool:
        return not self.ecarts


@dataclass(frozen=True)
class EquipeJouee:
    """Ce qu'un duel lit d'une équipe engagée (E13US004) : ses membres, et la catégorie commune.

    `categorie` est celle du **premier** membre : une équipe engagée est conforme, donc ses membres
    partagent l'arme ; c'est elle qui résout le barème et le blason du duel (ADR-0120 §5).
    """

    equipe: Equipe
    membres: tuple[MembreVu, ...]
    categorie: Categorie | None


class VerrouDeComposition(Protocol):
    """Ces archers tirent-ils un départ où un tableau d'équipes de ce type a un tir (E13US004) ?"""

    def en_jeu(
        self, tournoi_id: TournoiId, type: TypeEquipe, archers: Iterable[ArcherId]
    ) -> bool: ...


class ServiceEquipes:
    def __init__(
        self,
        equipes: EquipeRepository,
        tournois: TournoiRepository,
        archers: ArcherRepository,
        categories: CategorieRepository,
        *,
        verrou: VerrouDeComposition,
    ) -> None:
        self._equipes = equipes
        self._verrou = verrou
        self._tournois = tournois
        self._archers = archers
        self._categories = categories

    def lister(self, tournoi_id: TournoiId) -> list[EquipeVue]:
        """Triées par nom au sens de `cle_nom` — DETTE-006, comme les scoreurs et les clubs."""
        self._verifier_tournoi(tournoi_id)
        equipes = sorted(self._equipes.par_tournoi(tournoi_id), key=lambda e: cle_nom(e.nom))
        return self._vues(tournoi_id, equipes)

    def a_engager(
        self, tournoi_id: TournoiId, type: TypeEquipe
    ) -> tuple[list[Equipe], dict[ArcherId, ProfilMembre]]:
        """Les équipes de `type` et le profil de chaque archer du tournoi, lus une fois."""
        categories = {c.id: c for c in self._categories.par_tournoi(tournoi_id)}
        profils = {
            archer.id: ProfilMembre.de_categorie(categories.get(archer.categorie_id))
            for archer in self._archers.par_tournoi(tournoi_id)
            if archer.id is not None
        }
        equipes = [e for e in self._equipes.par_tournoi(tournoi_id) if e.type is type]
        return equipes, profils

    # DETTE-031 — relue par camp et par match, sans mémoïsation d'une reconstruction à l'autre.
    def jouee(self, equipe_id: EquipeId) -> EquipeJouee | None:
        equipe = self._equipes.par_id(equipe_id)
        if equipe is None:
            return None
        membres = [
            (archer_id, archer)
            for archer_id in equipe.membres
            if (archer := self._archers.par_id(archer_id)) is not None
        ]
        categories = {a.categorie_id: self._categories.par_id(a.categorie_id) for _, a in membres}
        return EquipeJouee(
            equipe=equipe,
            membres=tuple(
                _membre_vu(archer_id, a, categories[a.categorie_id]) for archer_id, a in membres
            ),
            categorie=categories[membres[0][1].categorie_id] if membres else None,
        )

    def creer(
        self, tournoi_id: TournoiId, nom: str, type: TypeEquipe, effectif_attendu: int | None
    ) -> EquipeVue:
        self._verifier_tournoi(tournoi_id)
        equipe = Equipe.creer(tournoi_id, nom, type, effectif_attendu)
        self._refuser_nom_pris(equipe)
        return self._vue(self._equipes.enregistrer(equipe))

    def modifier(
        self,
        tournoi_id: TournoiId,
        equipe_id: EquipeId,
        nom: str,
        type: TypeEquipe,
        effectif_attendu: int | None,
    ) -> EquipeVue:
        """⚠️ Changer le type re-vérifie « une équipe par type » pour **chaque** membre (CA 3)."""
        equipe = self._equipe_du_tournoi(tournoi_id, equipe_id)
        modifiee = equipe.modifier(nom, type, effectif_attendu)
        if (modifiee.type, modifiee.effectif_attendu) != (equipe.type, equipe.effectif_attendu):
            self._refuser_si_en_jeu(tournoi_id, equipe.type, equipe.membres)
            self._refuser_si_en_jeu(tournoi_id, modifiee.type, equipe.membres)
        self._refuser_nom_pris(modifiee)
        for archer_id in modifiee.membres:
            self._refuser_autre_equipe_du_type(modifiee, archer_id)
        return self._vue(self._equipes.enregistrer(modifiee))

    def supprimer(self, tournoi_id: TournoiId, equipe_id: EquipeId) -> None:
        equipe = self._equipe_du_tournoi(tournoi_id, equipe_id)
        self._refuser_si_en_jeu(tournoi_id, equipe.type, equipe.membres)
        self._equipes.supprimer(equipe_id)

    def ajouter_membre(
        self, tournoi_id: TournoiId, equipe_id: EquipeId, archer_id: ArcherId
    ) -> EquipeVue:
        equipe = self._equipe_du_tournoi(tournoi_id, equipe_id)
        self._refuser_si_en_jeu(tournoi_id, equipe.type, (*equipe.membres, archer_id))
        archer = self._archers.par_id(archer_id)
        if archer is None or archer.tournoi_id != tournoi_id:
            raise ArcherHorsTournoi(f"Aucun archer d'identifiant {archer_id} dans ce tournoi.")
        if archer_id in equipe.membres:
            raise ArcherDejaEnEquipe(
                f"« {archer.prenom} {archer.nom} » figure déjà dans l'équipe « {equipe.nom} »."
            )
        complete = equipe.ajouter_membre(archer_id)
        self._refuser_autre_equipe_du_type(complete, archer_id)
        return self._vue(self._equipes.enregistrer(complete))

    def retirer_membre(
        self, tournoi_id: TournoiId, equipe_id: EquipeId, archer_id: ArcherId
    ) -> EquipeVue:
        equipe = self._equipe_du_tournoi(tournoi_id, equipe_id)
        self._refuser_si_en_jeu(tournoi_id, equipe.type, equipe.membres)
        if archer_id not in equipe.membres:
            raise MembreIntrouvable(
                f"{self._nom_archer(archer_id)} ne figure pas dans l'équipe « {equipe.nom} »."
            )
        return self._vue(self._equipes.enregistrer(equipe.retirer_membre(archer_id)))

    # --- Gardes ---

    def _refuser_si_en_jeu(
        self, tournoi_id: TournoiId, type: TypeEquipe, archers: Iterable[ArcherId]
    ) -> None:
        if self._verrou.en_jeu(tournoi_id, type, archers):
            raise CompositionEquipeVerrouillee(
                "Le tableau d'équipes de ce départ a déjà été tiré : ses équipes ne se suppriment "
                "et ne se recomposent plus, sans quoi les résultats seraient relus pour d'autres "
                "équipes."
            )

    def _verifier_tournoi(self, tournoi_id: TournoiId) -> None:
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")

    def _equipe_du_tournoi(self, tournoi_id: TournoiId, equipe_id: EquipeId) -> Equipe:
        self._verifier_tournoi(tournoi_id)
        equipe = self._equipes.par_id(equipe_id)
        if equipe is None or equipe.tournoi_id != tournoi_id:
            raise EquipeIntrouvable(
                f"Aucune équipe d'identifiant {equipe_id} dans le tournoi {tournoi_id}."
            )
        return equipe

    def _refuser_nom_pris(self, equipe: Equipe) -> None:
        cle = cle_nom(equipe.nom)
        for autre in self._equipes.par_tournoi(equipe.tournoi_id):
            if autre.id != equipe.id and cle_nom(autre.nom) == cle:
                raise NomEquipeDejaPris(f"Une équipe s'appelle déjà « {autre.nom} ».")

    def _refuser_autre_equipe_du_type(self, equipe: Equipe, archer_id: ArcherId) -> None:
        conflit = conflit_de_type([equipe], self._equipes.par_archer(archer_id))
        if conflit is not None:
            _, autre = conflit
            raise ArcherDejaEnEquipe(
                f"{self._nom_archer(archer_id)} est déjà membre de l'équipe {equipe.type.value} "
                f"« {autre.nom} » : un archer appartient à une seule équipe de chaque type."
            )

    def _nom_archer(self, archer_id: ArcherId) -> str:
        archer = self._archers.par_id(archer_id)
        return f"« {archer.prenom} {archer.nom} »" if archer else f"L'archer {archer_id}"

    # --- Lecture ---

    def _vue(self, equipe: Equipe) -> EquipeVue:
        return self._vues(equipe.tournoi_id, [equipe])[0]

    def _vues(self, tournoi_id: TournoiId, equipes: Sequence[Equipe]) -> list[EquipeVue]:
        """Archers et catégories du tournoi lus **une fois**, quel que soit le nombre d'équipes."""
        archers = {a.id: a for a in self._archers.par_tournoi(tournoi_id)}
        categories = {c.id: c for c in self._categories.par_tournoi(tournoi_id)}
        return [_vue_de(equipe, archers, categories) for equipe in equipes]


def _vue_de(
    equipe: Equipe,
    archers: dict[ArcherId | None, Archer],
    categories: dict[CategorieId | None, Categorie],
) -> EquipeVue:
    # Un archer supprimé entre les deux lectures de `lister` (hors writer) est ignoré, pas un 500.
    membres = [
        (archer_id, archers[archer_id]) for archer_id in equipe.membres if archer_id in archers
    ]
    profils = [ProfilMembre.de_categorie(categories.get(a.categorie_id)) for _, a in membres]
    return EquipeVue(
        equipe=equipe,
        membres=tuple(
            _membre_vu(archer_id, a, categories.get(a.categorie_id)) for archer_id, a in membres
        ),
        ecarts=ecarts_de_composition(equipe, profils),
    )


def _membre_vu(archer_id: ArcherId, archer: Archer, categorie: Categorie | None) -> MembreVu:
    return MembreVu(
        archer_id=archer_id,
        nom=archer.nom,
        prenom=archer.prenom,
        categorie=categorie.libelle if categorie else "",
    )
