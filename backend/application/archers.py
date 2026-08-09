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
    FusionArchersEngages,
    FusionImpossible,
    HomonymeArcher,
    SaisieHorsCible,
    TournoiIntrouvable,
)
from domain.archer import Archer, ArcherId, CleIdentite
from domain.categorie import CategorieId
from domain.club import ClubId, cle_nom
from domain.doublons import PaireDoublon, detecter_doublons
from domain.ports import (
    ArcherRepository,
    CategorieRepository,
    ClubRepository,
    InscriptionRepository,
    ScoreRepository,
    SerieRepository,
    TournoiRepository,
)
from domain.poste import Poste, TypePoste
from domain.score import Score
from domain.serie import Serie
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
        series: SerieRepository,
    ) -> None:
        self._tournois = tournois
        self._archers = archers
        self._scores = scores
        self._clubs = clubs
        self._categories = categories
        self._inscriptions = inscriptions
        # `_series` porte « l'archer a-t-il tiré ? » depuis E06US001 (DETTE-013 résorbée) : la
        # saisie réelle (E04US002) écrit des `Serie`/`Volee`, jamais `Score`. `_scores` ne sert
        # plus qu'au `saisir_score` du walking skeleton (endpoint sans appelant — DETTE-011).
        self._series = series

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

    def detecter_doublons(self, tournoi_id: TournoiId) -> list[PaireDoublon]:
        """Rapproche les paires d'inscrits vraisemblablement en double (E02US005).

        Lève `TournoiIntrouvable` si le tournoi n'existe pas — comme `lister`, un tournoi inconnu
        n'a pas « zéro doublon », il n'a pas d'inscrits du tout.

        Toute la logique de rapprochement vit dans le **domaine** (`domain.doublons`, pur et testé
        depuis le CA) : le service ne fait que fournir les inscrits du tournoi et propager le refus
        de tournoi inconnu. La détection est **sans état** — recalculée à chaque appel, aucune paire
        écartée n'est mémorisée (cf. story).
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        return detecter_doublons(self._archers.par_tournoi(tournoi_id))

    def fusionner(self, gagnant_id: ArcherId, perdant_id: ArcherId) -> Archer:
        """Fusionne un doublon : le **gagnant** absorbe les inscriptions et scores du **perdant**,
        qui disparaît (E02US005). Renvoie le gagnant.

        L'admin a **choisi** quelle fiche survit (le gagnant) ; la machine ne fusionne jamais
        d'office (le rapprochement est heuristique, ADR-0015). Le transfert lui-même — inscriptions,
        scores, série, en une transaction — est le contrat du port (`ArcherRepository.fusionner`),
        prouvé au niveau du repository ; ici on tient les **gardes** :

        - `ArcherIntrouvable` si l'une des fiches n'existe pas (contrôlé **avant** tout le reste) ;
        - `FusionImpossible` si c'est la **même** fiche (rien à fusionner) ou deux fiches de
          **tournois différents** (deux inscriptions distinctes, pas un doublon — l'homonymie
          se juge dans le tournoi, E02US002) ;
        - `FusionArchersEngages` si les **deux** fiches ont déjà une série de saisie : les fusionner
          mêlerait des volées (et violerait `UNIQUE(tournoi_id, archer_id)`). Le doublon se règle
          avant que le tournoi tire (arbitrage du 22/07/2026) ; si **une seule** a tiré, la fusion
          passe (série réassignée sans collision).

        Comme `ajouter`/`supprimer`, les lectures de garde **et** l'écriture tiennent dans la même
        commande soumise à la file du writer unique (règle 7) : aucune saisie concurrente ne peut se
        glisser entre le contrôle « les deux ont-ils tiré ? » et la fusion.
        """
        gagnant = self._archer_existant(gagnant_id)
        perdant = self._archer_existant(perdant_id)
        if gagnant_id == perdant_id:
            raise FusionImpossible("Une fiche ne peut pas être fusionnée avec elle-même.")
        if gagnant.tournoi_id != perdant.tournoi_id:
            raise FusionImpossible(
                "Ces deux archers appartiennent à des tournois différents : pas un doublon."
            )
        gagnant_a_tire = self._a_une_feuille(gagnant.tournoi_id, gagnant_id)
        perdant_a_tire = self._a_une_feuille(perdant.tournoi_id, perdant_id)
        if gagnant_a_tire and perdant_a_tire:
            raise FusionArchersEngages(
                f"« {gagnant.prenom} {gagnant.nom} » et « {perdant.prenom} {perdant.nom} » ont "
                "chacun une saisie enregistrée : les fusionner mêlerait leurs volées. Corrigez la "
                "saisie avant de fusionner (le doublon se règle avant que le tournoi tire)."
            )
        self._archers.fusionner(gagnant_id, perdant_id)
        return self._archer_existant(gagnant_id)

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

    def definir_handicap(
        self,
        archer_id: ArcherId,
        handicap_officiel: int | None = None,
        handicap_surcharge: int | None = None,
    ) -> Archer:
        """Fixe les deux handicaps d'un archer (E05US015) — **remplacement total** des deux valeurs.

        **Cas d'usage distinct de `modifier`, et volontairement pas un champ de plus dedans.**
        `modifier` corrige l'**état civil** d'un archer (nom, prénom, catégorie, club) : c'est une
        opération d'identité, gardée par deux confirmations d'homonymie et de catégorie. Un
        handicap n'a rien à y faire — il se règle souvent en série (import du club), parfois juste
        avant une phase, et le passer par `modifier` obligerait à renvoyer nom/prénom/catégorie à
        chaque ajustement, avec le risque d'écraser une correction faite entre-temps sur un autre
        poste. Un DTO par cas d'usage, c'est déjà le patron du projet (E02US001).

        `officiel` est la référence entretenue par le club ; `surcharge` la prime pour cette
        édition. Passer `None` aux deux **efface** les handicaps (retour au scratch) : comme pour
        `club_id` dans `modifier`, l'absence de valeur veut dire « remets à rien », jamais « n'y
        touche pas ». Lève `HandicapInvalide` (domaine) sur une valeur négative.
        """
        archer = self._archer_existant(archer_id)
        return self._archers.enregistrer(
            archer.avec_handicap(officiel=handicap_officiel, surcharge=handicap_surcharge)
        )

    def supprimer(self, archer_id: ArcherId, autoriser_suppression_engage: bool = False) -> None:
        """Désinscrit un archer (E02US003). Lève `ArcherIntrouvable` s'il n'existe pas.

        La suppression **efface aussi sa série de saisie (ses flèches), son placement et ses
        inscriptions sur départs** (E02US009) — c'est le contrat du port
        (cf. `ArcherRepository.supprimer`), pas un effet de bord.

        Lève `ArcherEngage` si l'archer est **placé** (il occupe une cible), **engagé** (il a déjà
        tiré — au moins une volée **validée**) ou **inscrit** sur au moins un départ, sauf
        `autoriser_suppression_engage=True` : un **signalement**, pas un refus
        (ADR-0016, sur le protocole d'ADR-0015). On ne fait pas disparaître en un clic un placement
        construit et des flèches saisies — mais l'admin, lui, peut savoir qu'il s'agit d'une erreur
        d'inscription.

        **Un abandon ne passe pas par ici** : c'est un forfait tracé (E04US015 / ADR-0050,
        ex-E12US004 — la même US couvre la qualification **et** les duels), qui préserve les
        flèches. Voir `ArcherEngage`.
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

    def saisir_score(
        self, archer_id: ArcherId, points: int, poste_autorise: Poste | None = None
    ) -> Score:
        """Enregistre une flèche d'un archer. Lève `ArcherIntrouvable` s'il n'existe pas.

        `poste_autorise` porte le **mode d'identité** de l'appelant (E10US007) :

        - `None` — la saisie vient de l'**admin** (E10US001), sans contrainte de cible ;
        - un `Poste` — la saisie vient d'un **poste de cible**, qui ne peut marquer que pour **sa**
          cible : `SaisieHorsCible` (→ 403) si l'archer visé n'est pas placé sur
          `(poste.tournoi_id, poste.cible_index)`.

        Le contrôle vit **ici**, dans la même opération que l'écriture (donc dans la même commande
        de la file du writer unique, règle 7) : lire la cible de l'archer puis écrire sans barrière
        entre les deux fermerait une fenêtre de course (l'archer replacé entre-temps). L'existence
        de l'archer se vérifie **avant** sa cible — un archer inconnu rend 404, pas 403.
        """
        archer = self._archer_existant(archer_id)
        if poste_autorise is not None:
            self._verifier_poste_sert_l_archer(poste_autorise, archer)
        return self._scores.ajouter(Score.creer(archer_id, points))

    @staticmethod
    def _verifier_poste_sert_l_archer(poste: Poste, archer: Archer) -> None:
        """Lève `SaisieHorsCible` si l'archer n'est pas sur la cible servie par le poste (E10US007).

        « SA cible » = même **tournoi** *et* même **index de cible**. Le tournoi compte : plusieurs
        tournois tournent en concurrence (intérieur + extérieur) et les numéros de cible se
        répètent, donc comparer le seul `cible_index` laisserait le poste d'un tournoi voisin saisir
        ici.

        ⚠️ **Les deux `None` sont refusés explicitement** (correctif de revue E07US004). La version
        d'origine s'en remettait à la comparaison : « un archer non placé n'est sur aucune cible,
        `None != cible_index` le refuse naturellement ». Ce raisonnement ne tenait que tant que
        `Poste.cible_index` était **garanti non nul** — E07US004 l'a rendu facultatif (écran de
        salle), et `None != None` vaut **faux** : la garde s'ouvrait pour un jeton d'écran face à
        n'importe quel archer non placé, c'est-à-dire tout l'effectif avant le placement. mypy n'a
        rien vu, parce que c'est une **comparaison** et non une affectation.

        Leçon générale, plus utile que le correctif : une garde qui repose sur « ces deux valeurs ne
        peuvent pas être nulles en même temps » est une garde qu'un changement **lointain** peut
        désarmer sans rien casser de visible. On énonce donc les conditions, on ne les déduit pas.
        """
        if (
            poste.type is not TypePoste.CIBLE
            or archer.tournoi_id != poste.tournoi_id
            or archer.cible is None
            or archer.cible != poste.cible_index
        ):
            raise SaisieHorsCible(
                "Ce poste ne peut saisir que pour les archers de sa propre cible."
            )

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
        suffit désormais, au même titre qu'une **volée validée** ou un placement. Le message
        **énumère ce qui sera détruit** plutôt que d'inviter à confirmer : c'est la seule chose qui
        distingue, à l'écran, une suppression légitime (erreur de saisie) d'un abandon mal
        enregistré — que le forfait (E04US015 / ADR-0050, ex-E12US004) doit servir en préservant
        les flèches. Un message qui dirait « confirmez pour supprimer » ferait de la destruction
        le chemin par défaut de l'archer.

        `archer_id` est passé par l'appelant, qui le tient déjà, plutôt que lu dans `archer.id` :
        cela évite un `assert` de narrowing — or un `assert` saute sous `python -O`, et celui-ci
        aurait laissé `par_archer(…, None)` ne trouver aucune série (`fleches = 0`), et un archer
        engagé se supprimer **sans aucun signalement**. Un garde-fou ne dépend pas de `-O`.
        """
        # « A tiré » dérive des **volées validées** (`Serie`, E04US002), pas de l'agrégat `Score`
        # que plus aucun flux n'alimente (DETTE-013 résorbée). Une volée saisie mais non validée
        # n'est qu'un état intermédiaire : elle ne rend pas l'archer engagé (arbitrage 20/07,
        # `stories/E02-inscriptions.md`).
        fleches = self._fleches_validees(archer.tournoi_id, archer_id)
        liste_inscriptions = self._inscriptions.par_archer(archer_id)
        inscriptions = len(liste_inscriptions)
        # DETTE-018 : la suppression d'archer purge ses inscriptions en cascade **sans ouvrir de
        # remboursement** (E08US005 ne couvre que la désinscription et la suppression de départ).
        # Faute de mieux pour ce chemin, on **alerte** l'admin des sommes à rembourser — la création
        # automatique du poste **n'est portée par aucune US à ce jour** : la référence est
        # [DETTE-018] au registre, qui décrit le remède — méthode
        # `supprimer_avec_remboursements` sur `ArcherRepository`, motif `ARCHER_SUPPRIME`, comme
        # le départ — et l'arbitrage du 29/07/2026 : différer plutôt qu'étendre la cascade
        # sensible de l'archer (ADR-0016). Ne pas chercher « l'US de suite » : elle n'a jamais
        # existé — le registre parle d'une « US de dette à créer ». On compte les payées sur `paye`
        # seul (sans relire les tarifs — pas de `depart_repository` ici) : un créneau gratuit marqué
        # payé est donc **sur-signalé**, tolérable pour un simple avertissement.
        payees = sum(1 for inscription in liste_inscriptions if inscription.paye)
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
            detail = f"{inscriptions} {accord}"
            if payees:
                detail += (
                    f" (dont {payees} payée{'s' if payees > 1 else ''} : "
                    "sommes à rembourser, E08US005)"
                )
            motifs.append(detail)
        if archer.cible is not None:
            motifs.append(f"un placement sur la cible {archer.cible}")
        raise ArcherEngage(
            f"« {archer.prenom} {archer.nom} » a {' et '.join(motifs)}. Le supprimer effacera ces "
            "données définitivement. S'il abandonne en cours d'épreuve, ne le supprimez pas : "
            "c'est un forfait, qui conserve ses résultats. Confirmez seulement s'il n'aurait "
            "jamais dû être inscrit."
        )

    def _feuilles(self, tournoi_id: TournoiId, archer_id: ArcherId) -> list[Serie]:
        """Les feuilles de cet archer dans ce tournoi — **toutes phases confondues**.

        ⚠️ **Correctif de revue E05US025.** Ces trois gardes (« a-t-il tiré ? ») appelaient
        `SerieRepository.par_archer(archer.tournoi_id, …)`, dont le premier paramètre est devenu un
        `phase_id` avec cette US. `TournoiId` et `PhaseId` sont deux alias de `int` (`DETTE-044`) :
        rien n'a échoué à la compilation, et les gardes ne trouvaient plus **aucune** série dès que
        les deux entiers cessaient de coïncider — un archer engagé se supprimait alors *sans le
        moindre signalement*, exactement le mode de panne contre lequel `_impact_suppression`
        s'était prémunie par ailleurs.

        La bonne maille est bien le **tournoi** et non la phase : la question posée est « cet archer
        a-t-il tiré **quelque part** ? », pas « dans laquelle ». `par_tournoi` la répond
        exactement, et mieux qu'avant l'US — un archer qui n'a tiré que dans la *basse* est
        désormais vu. L'avertissement du port (« jamais base de calcul d'un classement ») ne vise
        pas cet usage : on ne classe rien, on compte.
        """
        return [
            serie for serie in self._series.par_tournoi(tournoi_id) if serie.archer_id == archer_id
        ]

    def _a_une_feuille(self, tournoi_id: TournoiId, archer_id: ArcherId) -> bool:
        """L'archer a-t-il une feuille de marque ouverte dans ce tournoi (fût-elle vide) ?"""
        return bool(self._feuilles(tournoi_id, archer_id))

    def _fleches_validees(self, tournoi_id: TournoiId, archer_id: ArcherId) -> int:
        """Le nombre de flèches **validées** de cet archer, toutes qualifications du tournoi."""
        return sum(serie.nb_fleches_validees for serie in self._feuilles(tournoi_id, archer_id))

    def _signaler_changement_categorie(self, archer_id: ArcherId, edite: Archer) -> None:
        """Lève `ChangementCategorieArcherEngage` si l'archer a déjà tiré (E02US003).

        Appelé seulement quand la catégorie change réellement : c'est le déplacement des flèches
        déjà tirées d'un classement à l'autre qui se confirme, pas l'édition en elle-même.
        """
        # « A déjà tiré » = au moins une volée **validée** (`Serie`, E04US002 — plus l'agrégat
        # `Score`, DETTE-013 résorbée) : ce sont les flèches **qui comptent** qui basculeraient vers
        # un autre classement. Une volée saisie non validée n'est encore dans aucun classement, rien
        # ne bascule — elle ne déclenche pas ce signalement (arbitrage du 20/07/2026).
        if self._fleches_validees(edite.tournoi_id, archer_id) > 0:
            raise ChangementCategorieArcherEngage(
                f"« {edite.prenom} {edite.nom} » a déjà tiré dans sa catégorie actuelle. Changer "
                "de catégorie emporte ses flèches vers un autre classement ; confirmez s'il "
                "s'agit bien de corriger une catégorie mal saisie."
            )
