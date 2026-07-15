"""Service applicatif Clubs — CRUD du référentiel des clubs (E02US001).

Orchestre le domaine derrière le port `ClubRepository`. Ne connaît ni HTTP, ni SQL, ni la file
d'écriture (sérialisation assurée en amont, côté API) ; il reste synchrone et pur
d'infrastructure.

Le référentiel est **global** (aucun tournoi en paramètre) : les clubs sont réutilisés d'une
compétition à l'autre.

**Unicité du nom.** Le domaine ne voit qu'un club à la fois, jamais la collection : c'est donc
ici qu'on refuse un doublon (`NomClubDejaPris`), avec une contrainte `UNIQUE` en base comme
garde-fou d'intégrité. Le contrôle « le nom est-il libre ? » puis l'insertion ne peuvent pas
s'entrelacer : toutes les écritures passent par la **file du writer unique** (ADR-0005), qui
les sérialise — le classique problème de concurrence entre la vérification et l'écriture ne se
pose donc pas ici.

La suppression d'un club **utilisé** (rattaché à des archers) sera refusée en **E02US002**, qui
introduit `archer.club_id` — donc l'usage à protéger, et le test qui l'exerce. Elle suivra le
patron de `ServiceBlasons.supprimer` / `BlasonReference` (E01US006). Écrire la règle ici
reviendrait à la vérifier contre le vide : aujourd'hui, rien ne peut référencer un club.
"""

from __future__ import annotations

from application.erreurs import ClubIntrouvable, NomClubDejaPris
from domain.club import Club, ClubId, cle_nom
from domain.ports import ClubRepository


class ServiceClubs:
    """Cas d'usage du référentiel des clubs : créer, lister, renommer, supprimer."""

    def __init__(self, clubs: ClubRepository) -> None:
        self._clubs = clubs

    def creer(self, nom: str) -> Club:
        """Ajoute un club au référentiel.

        Lève `NomClubInvalide` (domaine) si le nom est vide, `NomClubDejaPris` si un club porte
        déjà ce nom (à la casse près).
        """
        club = Club.creer(nom)
        self._exiger_nom_libre(club.nom)
        return self._clubs.ajouter(club)

    def lister(self) -> list[Club]:
        """Renvoie tout le référentiel, trié par nom (ordre d'affichage attendu à l'écran).

        Trie sur `cle_nom`, la clé qui sert aussi à refuser les homonymes : casse **et** accents
        repliés. Un tri sur le nom brut classerait par code point, donc « Élan » après « Zénith »
        — les clubs accentués s'entasseraient en fin de liste, dans l'écran même où l'utilisateur
        cherche le sien à l'œil.
        """
        return sorted(self._clubs.lister(), key=lambda club: cle_nom(club.nom))

    def modifier(self, club_id: ClubId, nom: str) -> Club:
        """Renomme un club.

        Lève `ClubIntrouvable` si l'identifiant est inconnu, `NomClubInvalide` (domaine) si le
        nom est vide, `NomClubDejaPris` si un **autre** club porte déjà ce nom.
        """
        club = self._club_existant(club_id)
        renomme = club.modifier(nom)
        self._exiger_nom_libre(renomme.nom, sauf=club_id)
        return self._clubs.enregistrer(renomme)

    def supprimer(self, club_id: ClubId) -> None:
        """Retire un club du référentiel. Lève `ClubIntrouvable` si l'identifiant est inconnu.

        Aucun club n'est « utilisé » tant qu'`archer.club_id` n'existe pas : le refus de
        suppression d'un club rattaché à des archers arrive en E02US002 (cf. docstring du
        module).
        """
        self._club_existant(club_id)
        self._clubs.supprimer(club_id)

    def _club_existant(self, club_id: ClubId) -> Club:
        club = self._clubs.par_id(club_id)
        if club is None:
            raise ClubIntrouvable(f"Aucun club d'identifiant {club_id}.")
        return club

    def _exiger_nom_libre(self, nom: str, sauf: ClubId | None = None) -> None:
        """Refuse un nom déjà porté par un autre club (`sauf` : le club en cours de renommage)."""
        homonyme = self._clubs.par_nom(nom)
        if homonyme is not None and homonyme.id != sauf:
            raise NomClubDejaPris(f"Un club nommé « {homonyme.nom} » existe déjà.")
