"""Service des **équipes** d'un tournoi (E13US002) — règles d'ensemble que l'agrégat ne voit pas.

⚠️ La composition est **signalée, jamais bloquée** (CA 4) : aucune écriture n'est refusée pour un
écart de composition ; seuls l'unicité du nom, l'appartenance au tournoi et « une équipe par type »
(CA 3) le sont.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from application.erreurs import (
    ArcherDejaEnEquipe,
    ArcherHorsTournoi,
    EquipeIntrouvable,
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


class ServiceEquipes:
    def __init__(
        self,
        equipes: EquipeRepository,
        tournois: TournoiRepository,
        archers: ArcherRepository,
        categories: CategorieRepository,
    ) -> None:
        self._equipes = equipes
        self._tournois = tournois
        self._archers = archers
        self._categories = categories

    def lister(self, tournoi_id: TournoiId) -> list[EquipeVue]:
        """Triées par nom au sens de `cle_nom` — DETTE-006, comme les scoreurs et les clubs."""
        self._verifier_tournoi(tournoi_id)
        equipes = sorted(self._equipes.par_tournoi(tournoi_id), key=lambda e: cle_nom(e.nom))
        return self._vues(tournoi_id, equipes)

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
        modifiee = self._equipe_du_tournoi(tournoi_id, equipe_id).modifier(
            nom, type, effectif_attendu
        )
        self._refuser_nom_pris(modifiee)
        for archer_id in modifiee.membres:
            self._refuser_autre_equipe_du_type(modifiee, archer_id)
        return self._vue(self._equipes.enregistrer(modifiee))

    def supprimer(self, tournoi_id: TournoiId, equipe_id: EquipeId) -> None:
        self._equipe_du_tournoi(tournoi_id, equipe_id)
        self._equipes.supprimer(equipe_id)

    def ajouter_membre(
        self, tournoi_id: TournoiId, equipe_id: EquipeId, archer_id: ArcherId
    ) -> EquipeVue:
        equipe = self._equipe_du_tournoi(tournoi_id, equipe_id)
        archer = self._archers.par_id(archer_id)
        if archer is None or archer.tournoi_id != tournoi_id:
            raise ArcherHorsTournoi(f"Aucun archer d'identifiant {archer_id} dans ce tournoi.")
        complete = equipe.ajouter_membre(archer_id)
        self._refuser_autre_equipe_du_type(complete, archer_id)
        return self._vue(self._equipes.enregistrer(complete))

    def retirer_membre(
        self, tournoi_id: TournoiId, equipe_id: EquipeId, archer_id: ArcherId
    ) -> EquipeVue:
        equipe = self._equipe_du_tournoi(tournoi_id, equipe_id)
        return self._vue(self._equipes.enregistrer(equipe.retirer_membre(archer_id)))

    # --- Gardes ---

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
        for autre in self._equipes.par_archer(archer_id):
            if autre.id != equipe.id and autre.type is equipe.type:
                archer = self._archers.par_id(archer_id)
                nom = f"« {archer.prenom} {archer.nom} »" if archer else f"L'archer {archer_id}"
                raise ArcherDejaEnEquipe(
                    f"{nom} est déjà membre de l'équipe {equipe.type.value} « {autre.nom} » : "
                    "un archer appartient à une seule équipe de chaque type."
                )

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
    membres = [(archer_id, archers[archer_id]) for archer_id in equipe.membres]
    profils = [_profil(categories.get(a.categorie_id)) for _, a in membres]
    return EquipeVue(
        equipe=equipe,
        membres=tuple(
            _membre_vu(archer_id, a, categories.get(a.categorie_id)) for archer_id, a in membres
        ),
        ecarts=ecarts_de_composition(equipe, profils),
    )


def _profil(categorie: Categorie | None) -> ProfilMembre:
    if categorie is None:
        return ProfilMembre(arme=None, sexe=None)
    return ProfilMembre(arme=categorie.arme, sexe=categorie.sexe)


def _membre_vu(archer_id: ArcherId, archer: Archer, categorie: Categorie | None) -> MembreVu:
    return MembreVu(
        archer_id=archer_id,
        nom=archer.nom,
        prenom=archer.prenom,
        categorie=categorie.libelle if categorie else "",
    )
