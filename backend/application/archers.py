"""Service applicatif Archers (E00US011, E02US002, E02US003) — inscrire, éditer, placer, marquer.

Orchestre le domaine derrière les ports repository. Ne connaît ni HTTP, ni SQL, ni la file
d'écriture (sérialisation assurée en amont, côté API). Chaque cas d'usage vérifie l'existence
des ressources amont (tournoi, archer, club, catégorie) et fait remonter des erreurs typées.

**Deux registres de refus**, à ne pas confondre (E02US003). Les *signalements* — `HomonymeArcher`,
`ChangementCategorieArcherEngage` — constatent un fait dont la machine ne sait pas s'il est une
erreur ; ils portent un drapeau `autoriser_*` par lequel l'admin tranche (ADR-0015). Le *refus*
— `ArcherEngage` — est définitif : aucun drapeau ne le lève, il faut changer l'état du monde.
"""

from __future__ import annotations

from application.erreurs import (
    ArcherEngage,
    ArcherIntrouvable,
    CategorieHorsTournoi,
    ChangementCategorieArcherEngage,
    ClubIntrouvable,
    HomonymeArcher,
    TournoiIntrouvable,
)
from domain.archer import Archer, ArcherId, CleIdentite
from domain.categorie import CategorieId
from domain.club import ClubId, cle_nom
from domain.ports import (
    ArcherRepository,
    CategorieRepository,
    ClubRepository,
    ScoreRepository,
    TournoiRepository,
)
from domain.score import Score
from domain.tournoi import TournoiId


class ServiceArchers:
    """Cas d'usage des archers : inscrire, lister, éditer, supprimer, placer, marquer."""

    def __init__(
        self,
        tournois: TournoiRepository,
        archers: ArcherRepository,
        scores: ScoreRepository,
        clubs: ClubRepository,
        categories: CategorieRepository,
    ) -> None:
        self._tournois = tournois
        self._archers = archers
        self._scores = scores
        self._clubs = clubs
        self._categories = categories

    def ajouter(
        self,
        tournoi_id: TournoiId,
        nom: str,
        prenom: str,
        categorie_id: CategorieId,
        club_id: ClubId | None = None,
        autoriser_homonyme: bool = False,
    ) -> Archer:
        """Inscrit un archer à un tournoi (E02US002).

        La **catégorie est obligatoire** et doit appartenir au tournoi ; le **club est facultatif**
        (`None` = club encore inconnu, cf. `domain.archer` et ADR-0014) mais doit exister s'il est
        fourni.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas, `CategorieHorsTournoi` si la catégorie
        est inexistante ou étrangère au tournoi, `ClubIntrouvable` si un `club_id` est fourni sans
        correspondre à un club du référentiel, et `HomonymeArcher` si un archer de même identité
        (`domain.archer.cle_identite`) est déjà inscrit — sauf `autoriser_homonyme=True`, par lequel
        l'admin confirme qu'il s'agit bien de deux personnes distinctes.
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        self._verifier_categorie_du_tournoi(tournoi_id, categorie_id)
        if club_id is not None and self._clubs.par_id(club_id) is None:
            raise ClubIntrouvable(f"Aucun club d'identifiant {club_id}.")
        # L'agrégat est construit **avant** le contrôle d'homonymie : la clé dérive ainsi du nom
        # réellement stocké (normalisé par `Archer.creer`) et non de l'entrée brute. Sans cela, la
        # justesse reposerait sur une coïncidence entre deux normalisations indépendantes — celle
        # de `cle_nom` et celle de `_texte_obligatoire` — qu'une évolution de l'une romprait en
        # silence. Effet de bord voulu : une saisie invalide rend 422 avant 409, ce qui est l'ordre
        # juste (une entrée invalide n'est pas un conflit).
        archer = Archer.creer(nom, prenom, tournoi_id, categorie_id, club_id)
        if not autoriser_homonyme:
            self._signaler_homonyme(tournoi_id, archer.cle_identite())
        return self._archers.ajouter(archer)

    def lister(self, tournoi_id: TournoiId) -> list[Archer]:
        """Renvoie les inscrits d'un tournoi, triés par nom puis prénom (E02US003).

        Lève `TournoiIntrouvable` si le tournoi n'existe pas — un tournoi inconnu n'a pas « zéro
        inscrit », il n'a pas d'inscrits du tout, et l'écran doit dire lequel des deux.

        Trie sur `cle_nom` (casse **et** accents repliés) comme `ServiceClubs.lister`, et pour la
        même raison : un tri sur le nom brut classe par code point, donc « Élan » après « Zola » —
        les archers accentués s'entasseraient en fin de liste, dans l'écran même où le bénévole
        cherche un nom à l'œil. Le prénom départage les inscrits d'une même famille.
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        return sorted(
            self._archers.par_tournoi(tournoi_id),
            key=lambda archer: (cle_nom(archer.nom), cle_nom(archer.prenom)),
        )

    def modifier(
        self,
        archer_id: ArcherId,
        nom: str,
        prenom: str,
        categorie_id: CategorieId,
        club_id: ClubId | None = None,
        autoriser_homonyme: bool = False,
        autoriser_changement_categorie: bool = False,
    ) -> Archer:
        """Corrige un archer inscrit (E02US003) — **remplacement total** des champs éditables.

        Rejoue les contrôles de l'inscription : nom et prénom non vides (domaine), catégorie **du
        tournoi de l'archer** (`CategorieHorsTournoi`), club existant s'il est fourni
        (`ClubIntrouvable`). Lève `ArcherIntrouvable` si l'identifiant est inconnu.

        Deux signalements, chacun levé par son propre drapeau :

        - `HomonymeArcher` si l'édition **fait entrer** l'archer dans l'identité d'un inscrit ;
        - `ChangementCategorieArcherEngage` si la catégorie change alors que l'archer a déjà tiré.

        Le placement et le tournoi ne sont pas éditables (cf. `Archer.modifier`).
        """
        archer = self._archer_existant(archer_id)
        self._verifier_categorie_du_tournoi(archer.tournoi_id, categorie_id)
        if club_id is not None and self._clubs.par_id(club_id) is None:
            raise ClubIntrouvable(f"Aucun club d'identifiant {club_id}.")
        # Édité **avant** les deux contrôles de conflit, comme dans `ajouter` et pour les mêmes
        # raisons : la clé d'homonymie doit dériver du nom normalisé, et une saisie invalide doit
        # rendre 422 avant 409 (une entrée invalide n'est pas un conflit).
        edite = archer.modifier(nom, prenom, categorie_id, club_id)
        # Les deux signalements ne se déclenchent que sur un **changement** effectif. Rejouer
        # l'arbitrage à chaque édition, sur un homonyme déjà confirmé ou une catégorie qu'on ne
        # touche pas, apprendrait à l'admin à confirmer sans lire — c'est ainsi qu'un garde-fou
        # cesse d'en être un.
        if not autoriser_homonyme and edite.cle_identite() != archer.cle_identite():
            self._signaler_homonyme(archer.tournoi_id, edite.cle_identite(), sauf=archer_id)
        if not autoriser_changement_categorie and edite.categorie_id != archer.categorie_id:
            self._signaler_changement_categorie(archer_id, edite)
        return self._archers.enregistrer(edite)

    def supprimer(self, archer_id: ArcherId) -> None:
        """Désinscrit un archer (E02US003). Lève `ArcherIntrouvable` s'il n'existe pas.

        Lève `ArcherEngage` — **refus définitif** — si l'archer est placé (il occupe une cible)
        ou engagé (il a déjà tiré) : on ne fait pas disparaître en un clic un placement construit
        et des flèches saisies. Voir `ArcherEngage` pour l'arbitrage.
        """
        # DETTE-006 : les deux messages ci-dessous prescrivent un geste qui n'existe pas encore
        # (retirer un placement → E03 ; effacer un score → E04). Le refus est juste ; c'est sa
        # sortie qui manque. À reprendre avec ces US.
        archer = self._archer_existant(archer_id)
        if archer.cible is not None:
            raise ArcherEngage(
                f"« {archer.prenom} {archer.nom} » est placé sur la cible {archer.cible} ; "
                "retirez-le de son placement avant de le supprimer."
            )
        if self._scores.par_archer(archer_id):
            raise ArcherEngage(
                f"« {archer.prenom} {archer.nom} » a déjà tiré ; effacez ses scores avant de le "
                "supprimer."
            )
        self._archers.supprimer(archer_id)

    def placer(self, archer_id: ArcherId, cible: int) -> Archer:
        """Place un archer sur une cible. Lève `ArcherIntrouvable` s'il n'existe pas."""
        archer = self._archer_existant(archer_id)
        return self._archers.enregistrer(archer.placer(cible))

    def saisir_score(self, archer_id: ArcherId, points: int) -> Score:
        """Enregistre une flèche d'un archer. Lève `ArcherIntrouvable` s'il n'existe pas."""
        self._archer_existant(archer_id)
        return self._scores.ajouter(Score.creer(archer_id, points))

    def _archer_existant(self, archer_id: ArcherId) -> Archer:
        archer = self._archers.par_id(archer_id)
        if archer is None:
            raise ArcherIntrouvable(f"Aucun archer d'identifiant {archer_id}.")
        return archer

    def _verifier_categorie_du_tournoi(
        self, tournoi_id: TournoiId, categorie_id: CategorieId
    ) -> None:
        """Exige une catégorie **du tournoi** (patron `ServiceCategories._verifier_blason_...`)."""
        categorie = self._categories.par_id(categorie_id)
        if categorie is None or categorie.tournoi_id != tournoi_id:
            raise CategorieHorsTournoi(
                f"La catégorie {categorie_id} n'appartient pas au tournoi {tournoi_id}."
            )

    def _signaler_homonyme(
        self, tournoi_id: TournoiId, cle: CleIdentite, sauf: ArcherId | None = None
    ) -> None:
        """Lève `HomonymeArcher` si un archer de même identité est déjà inscrit au tournoi.

        `sauf` : l'archer en cours d'édition (E02US003), qui ne peut pas être son propre doublon —
        sans quoi toute édition serait impossible (patron `ServiceClubs._exiger_nom_libre`).

        Balayage linéaire des inscrits plutôt qu'un port de recherche dédié : quelques centaines
        d'archers par tournoi, sur une inscription — la simplicité prime hors du domaine (règle 12),
        et un index serait à maintenir cohérent avec `cle_identite` pour rien.
        """
        for inscrit in self._archers.par_tournoi(tournoi_id):
            if inscrit.id != sauf and inscrit.cle_identite() == cle:
                raise HomonymeArcher(
                    f"« {inscrit.prenom} {inscrit.nom} » est déjà inscrit à ce tournoi. "
                    "S'il s'agit d'un homonyme (un père et son fils, par exemple), confirmez "
                    "l'inscription ; sinon, il s'agit d'un doublon."
                )

    def _signaler_changement_categorie(self, archer_id: ArcherId, edite: Archer) -> None:
        """Lève `ChangementCategorieArcherEngage` si l'archer a déjà tiré (E02US003).

        Appelé seulement quand la catégorie change réellement : c'est le déplacement des flèches
        déjà tirées d'un classement à l'autre qui se confirme, pas l'édition en elle-même.
        """
        if self._scores.par_archer(archer_id):
            raise ChangementCategorieArcherEngage(
                f"« {edite.prenom} {edite.nom} » a déjà tiré dans sa catégorie actuelle. Changer "
                "de catégorie emporte ses flèches vers un autre classement ; confirmez s'il "
                "s'agit bien de corriger une catégorie mal saisie."
            )
