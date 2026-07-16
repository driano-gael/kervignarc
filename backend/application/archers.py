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
    InscriptionRepository,
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
        inscriptions: InscriptionRepository,
    ) -> None:
        self._tournois = tournois
        self._archers = archers
        self._scores = scores
        self._clubs = clubs
        self._categories = categories
        self._inscriptions = inscriptions

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

        L'`id` départage en dernier ressort. Deux homonymes **confirmés** (le père et le fils,
        que le projet soutient depuis E02US002) ont la même clé : sans ce 3ᵉ terme, leur ordre
        serait celui que rend `par_tournoi`, c'est-à-dire un `SELECT` sans `ORDER BY` — que SQLite
        ne garantit pas. Les deux lignes permuteraient d'un rafraîchissement à l'autre, sur l'écran
        même où on doit les distinguer à l'œil.
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        return sorted(
            self._archers.par_tournoi(tournoi_id),
            key=lambda archer: (cle_nom(archer.nom), cle_nom(archer.prenom), archer.id or 0),
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

    def supprimer(self, archer_id: ArcherId, autoriser_suppression_engage: bool = False) -> None:
        """Désinscrit un archer (E02US003). Lève `ArcherIntrouvable` s'il n'existe pas.

        La suppression **efface aussi ses scores, son placement et ses inscriptions sur départs**
        (E02US009) — c'est le contrat du port (cf. `ArcherRepository.supprimer`), pas un effet de
        bord.

        Lève `ArcherEngage` si l'archer est **placé** (il occupe une cible), **engagé** (il a déjà
        tiré) ou **inscrit** sur au moins un départ (E02US009), sauf
        `autoriser_suppression_engage=True` : un **signalement**, pas un refus
        (ADR-0016, sur le protocole d'ADR-0015). On ne fait pas disparaître en un clic un placement
        construit et des flèches saisies — mais l'admin, lui, peut savoir qu'il s'agit d'une erreur
        d'inscription.

        **Un abandon ne passe pas par ici** : c'est un forfait tracé (E04US015 en qualification,
        E12US004 en duels), qui préserve les flèches. Voir `ArcherEngage`.
        """
        archer = self._archer_existant(archer_id)
        # DETTE-007 : la confirmation est **aveugle**. Le compte de flèches annoncé par le
        # signalement n'est pas revérifié — entre le 409 et le rejeu, d'autres tablettes peuvent
        # avoir saisi, et l'on détruirait plus que le message n'a annoncé.
        if not autoriser_suppression_engage:
            self._signaler_engagement(archer, archer_id)
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

    def _signaler_engagement(self, archer: Archer, archer_id: ArcherId) -> None:
        """Lève `ArcherEngage` si l'archer est placé, a déjà tiré **ou est inscrit** (E02US003,
        E02US009).

        « Engagé » s'est élargi (glossaire, E02US009) : une inscription sur au moins un départ
        suffit désormais, au même titre qu'un score ou un placement. Le message **énumère ce qui
        sera détruit** plutôt que d'inviter à confirmer : c'est la seule chose qui distingue, à
        l'écran, une suppression légitime (erreur de saisie) d'un abandon mal enregistré — que le
        forfait (E04US015, E12US004) doit servir en préservant les flèches. Un message qui dirait
        « confirmez pour supprimer » ferait de la destruction le chemin par défaut de l'archer.

        `archer_id` est passé par l'appelant, qui le tient déjà, plutôt que lu dans `archer.id` :
        cela évite un `assert` de narrowing — or un `assert` saute sous `python -O`, et celui-ci
        aurait laissé `par_archer(None)` rendre `[]`, donc un archer engagé se supprimer **sans
        aucun signalement**. Un garde-fou de destruction ne dépend pas d'un drapeau d'interpréteur.
        """
        fleches = len(self._scores.par_archer(archer_id))
        inscriptions = len(self._inscriptions.par_archer(archer_id))
        if archer.cible is None and fleches == 0 and inscriptions == 0:
            return
        motifs = []
        if fleches:
            # Accord au singulier plutôt qu'un « flèche(s) » : ce message est lu par un bénévole
            # au moment où il s'apprête à détruire des données. Il doit se lire, pas se décoder.
            accord = "flèche déjà tirée" if fleches == 1 else "flèches déjà tirées"
            motifs.append(f"{fleches} {accord}")
        if inscriptions:
            accord = (
                "inscription sur un départ" if inscriptions == 1 else "inscriptions sur des départs"
            )
            motifs.append(f"{inscriptions} {accord}")
        if archer.cible is not None:
            motifs.append(f"un placement sur la cible {archer.cible}")
        raise ArcherEngage(
            f"« {archer.prenom} {archer.nom} » a {' et '.join(motifs)}. Le supprimer effacera ces "
            "données définitivement. S'il abandonne en cours d'épreuve, ne le supprimez pas : "
            "c'est un forfait, qui conserve ses résultats. Confirmez seulement s'il n'aurait "
            "jamais dû être inscrit."
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
