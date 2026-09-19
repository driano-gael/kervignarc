"""Service applicatif Archers (E00US011, E02US002, E02US003) — inscrire, éditer, placer, marquer.

⚠️ **Deux registres de refus, à ne pas confondre.** Les *signalements* (`HomonymeArcher`,
`ChangementCategorieArcherEngage`) portent un drapeau `autoriser_*` par lequel l'admin tranche
(ADR-0015) ; le refus `ArcherEngage`, lui, est **définitif** — aucun drapeau ne le lève.
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
    DepartRepository,
    Horloge,
    InscriptionRepository,
    ScoreRepository,
    SerieRepository,
    TournoiRepository,
)
from domain.poste import Poste, TypePoste
from domain.remboursement import MotifRemboursement, Remboursement
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
        departs: DepartRepository,
        horloge: Horloge,
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
        # E01US026 (résorbe DETTE-018) : ouvrir un remboursement demande le **tarif** du créneau
        # effacé et un **instant** de création — deux ports de plus, jamais un autre service
        # (règle 2). L'horloge est un port parce que lire l'heure est un effet de bord qui rendrait
        # le service non déterministe en test (règle 9).
        self._departs = departs
        self._horloge = horloge

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
        (`None` = club encore inconnu, ADR-0014) mais doit exister s'il est fourni. Lève
        `TournoiIntrouvable`, `CategorieHorsTournoi`, `ClubIntrouvable`, et `HomonymeArcher` si un
        archer de même identité est déjà inscrit — sauf `autoriser_homonyme=True`, par lequel
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

        Lève `TournoiIntrouvable` : un tournoi inconnu n'a pas « zéro inscrit ». Trie sur `cle_nom`
        (casse **et** accents repliés) — un tri sur le nom brut classe par code point, donc « Élan
        » après « Zola ». ⚠️ L'`id` départage en dernier ressort : deux homonymes **confirmés** ont
        la même clé, et sans ce 3ᵉ terme leur ordre serait celui d'un `SELECT` sans `ORDER BY`, que
        SQLite ne garantit pas — ils permuteraient d'un rafraîchissement à l'autre.
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        return sorted(
            self._archers.par_tournoi(tournoi_id),
            key=lambda archer: (cle_nom(archer.nom), cle_nom(archer.prenom), archer.id or 0),
        )

    def detecter_doublons(self, tournoi_id: TournoiId) -> list[PaireDoublon]:
        """Rapproche les paires d'inscrits vraisemblablement en double (E02US005).

        Toute la logique vit dans le **domaine** (`domain.doublons`, pur et testé depuis le CA) :
        le service fournit les inscrits et propage `TournoiIntrouvable`. La détection est **sans
        état** — recalculée à chaque appel, aucune paire écartée n'est mémorisée.
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        return detecter_doublons(self._archers.par_tournoi(tournoi_id))

    def fusionner(self, gagnant_id: ArcherId, perdant_id: ArcherId) -> Archer:
        """Fusionne un doublon : le **gagnant** absorbe la descendance du **perdant** (E02US005).

        L'admin **choisit** quelle fiche survit ; la machine ne fusionne jamais d'office
        (ADR-0015). Le transfert est le contrat du port ; ici on tient les **gardes** :
        `ArcherIntrouvable`, `FusionImpossible` (même fiche, ou deux tournois différents), et
        `FusionArchersEngages` si les **deux** ont une série — les fusionner mêlerait des volées et
        violerait l'unicité.
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

        Rejoue les contrôles de l'inscription : nom et prénom non vides, catégorie **du tournoi de
        l'archer**, club existant s'il est fourni. Deux signalements, chacun levé par son drapeau :
        `HomonymeArcher` si l'édition **fait entrer** l'archer dans l'identité d'un inscrit, et
        `ChangementCategorieArcherEngage` si la catégorie change alors qu'il a déjà tiré.
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

        **Cas d'usage distinct de `modifier`, et pas un champ de plus dedans** : `modifier` corrige
        l'**état civil**, gardé par deux confirmations. Un handicap se règle souvent en série, et
        le passer par `modifier` obligerait à renvoyer nom/prénom/catégorie à chaque ajustement —
        au risque d'écraser une correction faite entre-temps. Passer `None` aux deux **efface** les
        handicaps : l'absence de valeur veut dire « remets à rien », jamais « n'y touche pas ».
        """
        archer = self._archer_existant(archer_id)
        return self._archers.enregistrer(
            archer.avec_handicap(officiel=handicap_officiel, surcharge=handicap_surcharge)
        )

    def supprimer(self, archer_id: ArcherId, autoriser_suppression_engage: bool = False) -> None:
        """Désinscrit un archer (E02US003). Lève `ArcherIntrouvable` s'il n'existe pas.

        La suppression **efface aussi sa série de saisie, son placement et ses inscriptions**
        (E02US009) — c'est le contrat du port, pas un effet de bord. Lève `ArcherEngage` s'il est
        placé, a déjà tiré ou est inscrit, sauf `autoriser_suppression_engage=True` : un
        **signalement**, pas un refus (ADR-0016). ⚠️ **Un abandon ne passe pas par ici** : c'est un
        forfait tracé (ADR-0050), qui préserve les flèches.
        """
        archer = self._archer_existant(archer_id)
        # DETTE-007 : la confirmation est **aveugle**. Le compte de flèches annoncé par le
        # signalement n'est pas revérifié — entre le 409 et le rejeu, d'autres tablettes peuvent
        # avoir saisi, et l'on détruirait plus que le message n'a annoncé.
        if not autoriser_suppression_engage:
            self._signaler_engagement(archer, archer_id)
        remboursements = self._remboursements_des_payees(archer, archer_id)
        if remboursements:
            self._archers.supprimer_avec_remboursements(archer_id, remboursements)
        else:
            self._archers.supprimer(archer_id)

    def _remboursements_des_payees(
        self, archer: Archer, archer_id: ArcherId
    ) -> list[Remboursement]:
        """Un `Remboursement` par inscription **payée** sur un créneau **tarifé** (E01US026).

        Troisième et dernier chemin d'effacement d'une inscription payée (DETTE-018), après la
        désinscription et la suppression de départ. L'instantané (nom de l'archer, libellé du
        créneau) est figé **maintenant** : il doit survivre à ce qui disparaît. ⚠️ Un créneau
        **gratuit** marqué payé n'ouvre rien — `Remboursement.creer` refuse un montant nul, et un
        poste à 0 € ne demanderait rien à personne.
        """
        instant = self._horloge.maintenant()
        remboursements: list[Remboursement] = []
        for inscription in self._inscriptions.par_archer(archer_id):
            if not inscription.paye:
                continue
            depart = self._departs.par_id(inscription.depart_id)
            if depart is None or depart.tarif_centimes <= 0:
                continue
            remboursements.append(
                Remboursement.creer(
                    archer.tournoi_id,
                    archer_prenom=archer.prenom,
                    archer_nom=archer.nom,
                    creneau=f"Départ n°{depart.numero} — {depart.horaire}",
                    # DETTE-016 : le montant est le **tarif courant**, pas la somme réellement
                    # encaissée (le modèle ne stocke qu'un booléen `paye`) — faux si le tarif a été
                    # édité après le paiement. Même écart que sur les deux autres chemins.
                    montant_centimes=depart.tarif_centimes,
                    motif=MotifRemboursement.ARCHER_SUPPRIME,
                    cree_le=instant,
                )
            )
        return remboursements

    def placer(self, archer_id: ArcherId, cible: int) -> Archer:
        """Place un archer sur une cible. Lève `ArcherIntrouvable` s'il n'existe pas."""
        archer = self._archer_existant(archer_id)
        return self._archers.enregistrer(archer.placer(cible))

    def saisir_score(
        self, archer_id: ArcherId, points: int, poste_autorise: Poste | None = None
    ) -> Score:
        """Enregistre une flèche d'un archer. Lève `ArcherIntrouvable` s'il n'existe pas.

        `poste_autorise` porte le **mode d'identité** de l'appelant (E10US007) : `None` = admin
        sans contrainte de cible ; un `Poste` = saisie depuis un poste, qui ne peut marquer que
        pour **sa** cible (`SaisieHorsCible`, 403). Le contrôle vit **ici**, dans la même commande
        de la file que l'écriture (règle 7) : lire puis écrire sans barrière ouvrirait une course.
        """
        archer = self._archer_existant(archer_id)
        if poste_autorise is not None:
            self._verifier_poste_sert_l_archer(poste_autorise, archer)
        return self._scores.ajouter(Score.creer(archer_id, points))

    @staticmethod
    def _verifier_poste_sert_l_archer(poste: Poste, archer: Archer) -> None:
        """Lève `SaisieHorsCible` si l'archer n'est pas sur la cible du poste (E10US007).

        « SA cible » = même **tournoi** *et* même index : plusieurs tournois tournent en
        concurrence et les numéros se répètent. ⚠️ **Les deux `None` sont refusés explicitement** —
        s'en remettre à `None != cible_index` ne tenait que tant que `Poste.cible_index` était non
        nul, or E07US004 l'a rendu facultatif et `None != None` vaut **faux**. Une garde qui repose
        sur « ces deux valeurs ne peuvent pas être nulles ensemble » se désarme de loin.
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

        `sauf` : l'archer en cours d'édition, qui ne peut pas être son propre doublon. Balayage
        linéaire plutôt qu'un port de recherche dédié — quelques centaines d'archers par tournoi,
        sur une inscription : la simplicité prime hors du domaine (règle 12).
        """
        for inscrit in self._archers.par_tournoi(tournoi_id):
            if inscrit.id != sauf and inscrit.cle_identite() == cle:
                raise HomonymeArcher(
                    f"« {inscrit.prenom} {inscrit.nom} » est déjà inscrit à ce tournoi. "
                    "S'il s'agit d'un homonyme (un père et son fils, par exemple), confirmez "
                    "l'inscription ; sinon, il s'agit d'un doublon."
                )

    def _signaler_engagement(self, archer: Archer, archer_id: ArcherId) -> None:
        """Lève `ArcherEngage` si l'archer est placé, a déjà tiré **ou est inscrit** (E02US009).

        « Engagé » s'est élargi : une inscription sur au moins un départ suffit. Le message
        **énumère ce qui sera détruit** plutôt que d'inviter à confirmer — c'est ce qui distingue à
        l'écran une suppression légitime d'un abandon mal enregistré, que le forfait doit servir en
        préservant les flèches. `archer_id` est passé par l'appelant plutôt que lu dans `archer.id`
        pour éviter un `assert` de narrowing, qui saute sous `python -O`.
        """

        # « A tiré » dérive des **volées validées** (`Serie`), pas de l'agrégat `Score` que plus
        # aucun flux n'alimente (DETTE-013 résorbée). Une volée saisie non validée ne rend pas
        # l'archer engagé (arbitrage du 20/07/2026).
        fleches = self._fleches_validees(archer.tournoi_id, archer_id)
        liste_inscriptions = self._inscriptions.par_archer(archer_id)
        inscriptions = len(liste_inscriptions)
        # ⚠️ Le compte annoncé s'appuie sur `paye` **seul**, quand l'ouverture du remboursement
        # exige en plus un créneau tarifé (`_remboursements_des_payees`) : un créneau gratuit
        # marqué payé est donc **sur-signalé** ici et n'ouvre rien ensuite. Tolérable — le message
        # annonce plus que ce qui partira, jamais moins.
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
                    "un remboursement sera ouvert pour chacune)"
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

        ⚠️ Ces gardes appelaient `par_archer(archer.tournoi_id, …)`, dont le premier paramètre est
        devenu un `phase_id` (E05US025). `TournoiId` et `PhaseId` étant deux alias d'`int`
        (`DETTE-044`), rien n'a échoué à la compilation et les gardes ne trouvaient plus **aucune**
        série. La bonne maille est bien le **tournoi** : la question est « a-t-il tiré quelque part
        ? », pas « dans laquelle » — on ne classe rien, on compte.
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
        déjà tirées d'un classement à l'autre qui se confirme, pas l'édition elle-même.
        """

        # « A déjà tiré » = au moins une volée **validée** : ce sont les flèches **qui comptent**
        # qui basculeraient. Une volée non validée n'est dans aucun classement, rien ne bascule.
        if self._fleches_validees(edite.tournoi_id, archer_id) > 0:
            raise ChangementCategorieArcherEngage(
                f"« {edite.prenom} {edite.nom} » a déjà tiré dans sa catégorie actuelle. Changer "
                "de catégorie emporte ses flèches vers un autre classement ; confirmez s'il "
                "s'agit bien de corriger une catégorie mal saisie."
            )
