"""Service de la **recherche transverse** — « chercher partout » (E16US010).

Assemble les trois référentiels cherchables (tournois, archers, clubs) en une forme de résultat
unique ; la règle de correspondance et le classement vivent au domaine (`domain.recherche`).
⚠️ **Le filtrage est en mémoire, délibérément** : le repli casse/accents n'est pas exprimable en
`LIKE` SQLite (« leveque » n'y trouve pas « Lévêque »). Tenable parce que mono-club et local
(règle 12) — voir la docstring d'`ArcherRepository.tous`.
"""

from __future__ import annotations

from domain.club import Club
from domain.ports import ArcherRepository, ClubRepository, TournoiRepository
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
    ) -> None:
        self._tournois = tournoi_repository
        self._archers = archer_repository
        self._clubs = club_repository

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
        """Les archers, décorés de leur club et de leur tournoi.

        Sans cette décoration, deux fiches homonymes de deux éditions différentes rendraient deux
        lignes identiques : l'organisateur ne pourrait pas choisir laquelle ouvrir.
        """
        archers = (
            self._archers.par_tournoi(tournoi_id)
            if tournoi_id is not None
            else self._archers.tous()
        )
        clubs = {club.id: club for club in self._clubs.lister() if club.id is not None}
        tournois = {t.id: t for t in self._tournois.lister() if t.id is not None}
        resultats = []
        for archer in archers:
            club = clubs.get(archer.club_id) if archer.club_id is not None else None
            libelle = f"{archer.nom} {archer.prenom}"
            if archer.id is None or not correspond(fragment, libelle, club.nom if club else ""):
                continue
            resultats.append(
                ResultatRecherche(
                    entite=EntiteRecherchable.ARCHER,
                    id=archer.id,
                    libelle=libelle,
                    # En pilotage on est déjà dans le tournoi : le rappeler à chaque ligne noie
                    # la seule information qui distingue les fiches, le club.
                    precision=_precision_archer(
                        club, tournois.get(archer.tournoi_id) if tournoi_id is None else None
                    ),
                    tournoi_id=archer.tournoi_id,
                )
            )
        return resultats


def _precision_tournoi(tournoi: Tournoi) -> str:
    """La date situe deux éditions du même nom ; le lieu, deux tournois du même jour."""
    return f"{tournoi.date:%d/%m/%Y}" + (f" · {tournoi.lieu}" if tournoi.lieu else "")


def _precision_archer(club: Club | None, tournoi: Tournoi | None) -> str | None:
    """« Club · Tournoi », sans les morceaux qu'on n'a pas — « club inconnu » est un cas réel."""
    morceaux = [club.nom if club else None, tournoi.nom if tournoi else None]
    presents = [morceau for morceau in morceaux if morceau]
    return " · ".join(presents) if presents else None
