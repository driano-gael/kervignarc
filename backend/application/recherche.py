"""Service de la **recherche transverse** — « chercher partout » (E16US010).

Assemble les trois référentiels cherchables (tournois, archers, clubs) en une forme de résultat
unique ; la règle de correspondance et le classement vivent au domaine (`domain.recherche`).
⚠️ **Le filtrage est en mémoire, délibérément** : le repli casse/accents n'est pas exprimable en
`LIKE` SQLite (« leveque » n'y trouve pas « Lévêque »). Tenable parce que mono-club et local
(règle 12) ; le coût et son seuil sont inscrits en `DETTE-092`.
"""

from __future__ import annotations

from domain.club import Club
from domain.ports import (
    ArcherRepository,
    CategorieRepository,
    ClubRepository,
    TournoiRepository,
)
from domain.recherche import (
    EntiteRecherchable,
    Recherche,
    ResultatRecherche,
    completer,
    correspond,
)
from domain.tournoi import Tournoi, TournoiId


class ServiceRecherche:
    """Cas d'usage : « trouve-moi cet item, et ouvre sa fiche »."""

    def __init__(
        self,
        tournoi_repository: TournoiRepository,
        archer_repository: ArcherRepository,
        club_repository: ClubRepository,
        categorie_repository: CategorieRepository,
    ) -> None:
        self._tournois = tournoi_repository
        self._archers = archer_repository
        self._clubs = club_repository
        self._categories = categorie_repository

    def chercher(
        self,
        entite: EntiteRecherchable,
        fragment: str,
        *,
        tournoi_id: TournoiId | None = None,
    ) -> Recherche:
        """Les propositions pour un fragment, dans une entité — bornées, total annoncé.

        `tournoi_id` réalise le second CA (« recherche d'archer **en pilotage**, scopée au
        tournoi ») : c'est le **même** chemin, restreint, et non une seconde recherche. ⚠️ Il n'a
        de sens que pour les archers — clubs et tournois sont des référentiels globaux, un scope
        les viderait sans rien dire.
        """
        if entite is EntiteRecherchable.ARCHER:
            return completer(self._archers_correspondants(fragment, tournoi_id), fragment)
        if entite is EntiteRecherchable.CLUB:
            return completer(self._clubs_correspondants(fragment), fragment)
        return completer(self._tournois_correspondants(fragment), fragment)

    def _tournois_correspondants(self, fragment: str) -> list[ResultatRecherche]:
        return [
            ResultatRecherche(
                entite=EntiteRecherchable.TOURNOI,
                id=tournoi.id,
                libelle=tournoi.nom,
                precision=_precision_tournoi(tournoi),
                tournoi_id=tournoi.id,
            )
            for tournoi in self._tournois.lister()
            if tournoi.id is not None and correspond(fragment, tournoi.nom, tournoi.lieu or "")
        ]

    def _clubs_correspondants(self, fragment: str) -> list[ResultatRecherche]:
        return [
            ResultatRecherche(entite=EntiteRecherchable.CLUB, id=club.id, libelle=club.nom)
            for club in self._clubs.lister()
            if club.id is not None and correspond(fragment, club.nom)
        ]

    def _archers_correspondants(
        self, fragment: str, tournoi_id: TournoiId | None
    ) -> list[ResultatRecherche]:
        """Les archers, décorés de leur club, de leur catégorie et de leur tournoi.

        ⚠️ **La catégorie n'est pas de l'ornement** : `domain.archer.cle_identite` dit qu'un père et
        son fils partagent nom, prénom **et** club — la détection de doublons de cette même US les
        rapproche pour cette raison. Sans elle, deux fiches du même tournoi rendaient deux lignes
        strictement identiques, et l'organisateur ouvrait celle du fils pour le père (relevé en
        3ᵉ passe par deux axes). Les classes d'âge les séparent par construction.
        """
        archers = (
            self._archers.par_tournoi(tournoi_id)
            if tournoi_id is not None
            else self._archers.tous()
        )
        clubs = {club.id: club for club in self._clubs.lister() if club.id is not None}
        tournois = {t.id: t for t in self._tournois.lister() if t.id is not None}
        retenus = [
            (archer, clubs.get(archer.club_id) if archer.club_id is not None else None)
            for archer in archers
            if archer.id is not None
        ]
        retenus = [
            (archer, club)
            for archer, club in retenus
            if correspond(fragment, f"{archer.nom} {archer.prenom}", club.nom if club else "")
        ]
        # Chargé **après** le filtrage, et seulement pour les tournois réellement représentés :
        # les catégories sont par tournoi, il n'existe pas de listing global (`DETTE-092`).
        categories = self._libelles_de_categorie({archer.tournoi_id for archer, _ in retenus})
        return [
            ResultatRecherche(
                entite=EntiteRecherchable.ARCHER,
                id=archer.id,
                libelle=f"{archer.nom} {archer.prenom}",
                # En pilotage on est déjà dans le tournoi : le rappeler à chaque ligne noie
                # les informations qui distinguent les fiches.
                precision=_precision_archer(
                    club,
                    categories.get(archer.categorie_id),
                    tournois.get(archer.tournoi_id) if tournoi_id is None else None,
                ),
                tournoi_id=archer.tournoi_id,
            )
            for archer, club in retenus
            if archer.id is not None
        ]

    def _libelles_de_categorie(self, tournois: set[TournoiId]) -> dict[int, str]:
        """Les libellés de catégorie des tournois donnés, indexés par identifiant."""
        libelles: dict[int, str] = {}
        for tournoi in tournois:
            for categorie in self._categories.par_tournoi(tournoi):
                if categorie.id is not None:
                    libelles[categorie.id] = categorie.libelle
        return libelles


def _precision_tournoi(tournoi: Tournoi) -> str:
    """La date situe deux éditions du même nom ; le lieu, deux tournois du même jour."""
    return f"{tournoi.date:%d/%m/%Y}" + (f" · {tournoi.lieu}" if tournoi.lieu else "")


def _precision_archer(
    club: Club | None, categorie: str | None, tournoi: Tournoi | None
) -> str | None:
    """« Club · Catégorie · Tournoi daté », sans les morceaux qu'on n'a pas.

    ⚠️ **Le tournoi se situe par la MÊME règle que `_precision_tournoi`** — date complète et lieu,
    pas seulement l'année : deux éditions d'une **même année civile** sont ordinaires (saison salle
    de novembre à mars), et la 1ʳᵉ correction n'avait repris que la moitié de la leçon.
    ⚠️ La **catégorie** sépare deux fiches d'un même tournoi et d'un même club — voir l'appelant.
    """
    morceaux = [
        club.nom if club else None,
        categorie,
        f"{tournoi.nom} — {_precision_tournoi(tournoi)}" if tournoi else None,
    ]
    presents = [morceau for morceau in morceaux if morceau]
    return " · ".join(presents) if presents else None
