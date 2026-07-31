"""Service applicatif Catégories — CRUD des catégories d'un tournoi (E01US003).

Orchestre le domaine derrière les ports repository. Ne connaît ni HTTP, ni SQL, ni la file
d'écriture (sérialisation assurée en amont, côté API) ; il reste synchrone et pur
d'infrastructure. Il vérifie l'existence des ressources amont (tournoi, catégorie) et la
cohérence du **blason par défaut** (règle inter-agrégats : même tournoi), et fait remonter des
erreurs typées (`TournoiIntrouvable`, `CategorieIntrouvable`, `BlasonHorsTournoi`).
"""

from __future__ import annotations

from collections.abc import Iterable

from application.erreurs import (
    BlasonHorsTournoi,
    BlasonIntrouvable,
    BriqueHorsBibliotheque,
    CategorieIntrouvable,
    NomBriqueDejaPris,
    TournoiIntrouvable,
)
from application.referentiel_ffta import blasons_salle_18m, categories_salle_18m
from domain.blason import Blason, BlasonId
from domain.categorie import (
    HAUTEUR_CENTRE_DEFAUT,
    Categorie,
    CategorieId,
    SexeCategorie,
    TrancheAge,
)
from domain.patrimoine import OrigineBrique
from domain.ports import BlasonRepository, CategorieRepository, TournoiRepository
from domain.tournoi import TournoiId


class ServiceCategories:
    """Cas d'usage des catégories : créer, lister, éditer, supprimer."""

    def __init__(
        self,
        tournois: TournoiRepository,
        categories: CategorieRepository,
        blasons: BlasonRepository,
    ) -> None:
        self._tournois = tournois
        self._categories = categories
        self._blasons = blasons

    def creer(
        self,
        tournoi_id: TournoiId,
        libelle: str,
        arme: str | None = None,
        ages: Iterable[TrancheAge] = (),
        sexe: SexeCategorie | None = None,
        blason_id: BlasonId | None = None,
        hauteur_cm: int = HAUTEUR_CENTRE_DEFAUT,
    ) -> Categorie:
        """Crée une catégorie rattachée à un tournoi.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas, `BlasonHorsTournoi` si le blason par
        défaut n'appartient pas à ce tournoi, `DomainError` si le libellé est vide ou la hauteur du
        centre n'est pas un entier strictement positif.
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        self._verifier_blason_du_tournoi(tournoi_id, blason_id)
        categorie = Categorie.creer(tournoi_id, libelle, arme, ages, sexe, blason_id, hauteur_cm)
        return self._categories.ajouter(categorie)

    def lister(self, tournoi_id: TournoiId) -> list[Categorie]:
        """Renvoie les catégories d'un tournoi. Lève `TournoiIntrouvable` s'il n'existe pas."""
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        return self._categories.par_tournoi(tournoi_id)

    def precharger_ffta(self, tournoi_id: TournoiId) -> list[Categorie]:
        """Pré-charge le jeu FFTA salle (18 m) dans un tournoi : blasons puis catégories (E01US004).

        Crée d'abord les **blasons FFTA** du §3 absents du tournoi (E01US022), puis les catégories
        du référentiel officiel (`application.referentiel_ffta`) absentes du tournoi, **rattachées
        à leur blason par défaut** du §3. Blasons et catégories sont dédupliqués par nom/libellé
        (comparaison insensible à la casse et aux espaces de bord) : l'action reste **rejouable
        sans doublonner**. Le tout est ordinaire : **modifiable et supprimable** via le CRUD.

        Le rattachement d'un `blason_id` de catégorie n'étant possible que vers un blason
        **existant du tournoi**, l'ordre (blasons d'abord) n'est pas cosmétique. Une catégorie déjà
        présente est ignorée telle quelle — on ne lui **réaffecte pas** rétroactivement un blason
        (respect de l'idempotence : on ne touche pas à l'existant).

        Renvoie les catégories effectivement **créées**, dans l'ordre du référentiel (liste vide
        si tout était déjà présent). Lève `TournoiIntrouvable` si le tournoi n'existe pas.
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        blasons_par_nom = self._precharger_blasons_ffta(tournoi_id)
        libelles_existants = {
            categorie.libelle.strip().casefold()
            for categorie in self._categories.par_tournoi(tournoi_id)
        }
        creees: list[Categorie] = []
        for modele in categories_salle_18m():
            cle = modele.libelle.strip().casefold()
            if cle in libelles_existants:
                continue
            blason = blasons_par_nom[modele.blason_nom.strip().casefold()]
            categorie = Categorie.creer(
                tournoi_id,
                modele.libelle,
                modele.arme,
                modele.ages,
                modele.sexe,
                blason.id,
                hauteur_cm=modele.hauteur_cm,
                origine=OrigineBrique.FFTA,
            )
            creees.append(self._categories.ajouter(categorie))
            libelles_existants.add(cle)
        return creees

    def _precharger_blasons_ffta(self, tournoi_id: TournoiId) -> dict[str, Blason]:
        """Crée (idempotemment) les blasons FFTA du §3 dans le tournoi (E01US022).

        Renvoie une table `nom casefold → blason` de **tous** les blasons FFTA du tournoi (créés à
        l'appel ou déjà présents d'un pré-chargement antérieur), pour que `precharger_ffta` résolve
        le blason par défaut de chaque catégorie. Ne recrée pas un blason dont le nom est déjà pris
        (l'admin a pu le personnaliser — on ne l'écrase pas).
        """
        par_nom = {
            blason.nom.strip().casefold(): blason
            for blason in self._blasons.par_tournoi(tournoi_id)
        }
        for modele in blasons_salle_18m():
            cle = modele.nom.strip().casefold()
            if cle in par_nom:
                continue
            blason = Blason.creer(
                tournoi_id,
                modele.nom,
                modele.taille,
                modele.capacite,
                modele.zones,
                # Provenance **exacte** de la donnée : ces blasons viennent du référentiel
                # fédéral, ils sont marqués comme tels. Ce n'est **pas** ce qui protège la liste
                # séparée de l'atelier — c'est la promotion qui s'en charge, en forçant
                # `utilisateur` pour un modèle neuf (`ServicePatrimoine.promouvoir_*`). Sans effet
                # d'écran aujourd'hui, donc : une brique de tournoi n'affiche pas son origine.
                origine=OrigineBrique.FFTA,
            )
            par_nom[cle] = self._blasons.ajouter(blason)
        return par_nom

    def modifier(
        self,
        categorie_id: CategorieId,
        libelle: str,
        arme: str | None = None,
        ages: Iterable[TrancheAge] = (),
        sexe: SexeCategorie | None = None,
        blason_id: BlasonId | None = None,
        *,
        hauteur_cm: int,
    ) -> Categorie:
        """Édite une catégorie (libellé, arme, tranches d'âge, sexe, blason par défaut, hauteur).

        Le PUT catégorie est **total** (ADR-0020) : `hauteur_cm` est **obligatoire** — le formulaire
        catégorie le porte depuis E03US004, ce qui résorbe DETTE-009. Paramètre **keyword-only**
        pour rester requis derrière les champs facultatifs.

        Lève `CategorieIntrouvable` si l'identifiant est inconnu, `DomainError` si le libellé est
        vide ou la hauteur du centre fournie n'est pas un entier strictement positif. Pour le blason
        par défaut : `BlasonHorsTournoi` si la catégorie appartient à un tournoi et que le blason
        n'en fait pas partie ; `BriqueHorsBibliotheque` si c'est un **modèle** et que le blason
        appartient à un tournoi ; `BlasonIntrouvable` dans les deux cas si le blason n'existe pas.
        """
        categorie = self._categorie_existante(categorie_id)
        # Un modèle de bibliothèque n'a pas de tournoi : la garde « le blason appartient bien à ce
        # tournoi » ne s'y applique pas — mais elle est **remplacée**, jamais levée (E01US023).
        # Sans le `else`, cette route héritée était le seul chemin par lequel un modèle pouvait
        # acquérir une FK vers l'édition d'un autre tournoi, que `ServicePatrimoine.creer_categorie`
        # refuse à la création : l'invariant aurait tenu à la création et cédé à l'édition.
        if categorie.tournoi_id is None:
            self._verifier_blason_de_bibliotheque(blason_id)
        else:
            self._verifier_blason_du_tournoi(categorie.tournoi_id, blason_id)
        modifiee = categorie.modifier(libelle, arme, ages, sexe, blason_id, hauteur_cm)
        if categorie.tournoi_id is None:
            # **Deuxième fois** que cette route héritée laisse passer ce que les routes neuves
            # refusent. L'unicité posée à la création (`NomBriqueDejaPris`) était contournable par
            # le bouton « Renommer » de l'atelier — qui appelle précisément ce PUT. Deux modèles
            # homonymes rendent l'assemblage et la promotion non déterministes : un seul est copié,
            # l'autre est compté « déjà présent » et n'atteint jamais aucun tournoi.
            self._exiger_libelle_de_bibliotheque_libre(modifiee.libelle, sauf=categorie_id)
        return self._categories.enregistrer(modifiee)

    def supprimer(self, categorie_id: CategorieId) -> None:
        """Supprime une catégorie. Lève `CategorieIntrouvable` si l'identifiant est inconnu."""
        self._categorie_existante(categorie_id)
        self._categories.supprimer(categorie_id)

    def _categorie_existante(self, categorie_id: CategorieId) -> Categorie:
        categorie = self._categories.par_id(categorie_id)
        if categorie is None:
            raise CategorieIntrouvable(f"Aucune catégorie d'identifiant {categorie_id}.")
        return categorie

    def _exiger_libelle_de_bibliotheque_libre(self, libelle: str, sauf: CategorieId) -> None:
        """Refuse un libellé déjà porté par un **autre** modèle de bibliothèque.

        `sauf` exclut la catégorie en cours d'édition, sans quoi renommer une catégorie en
        elle-même échouerait — patron `ServiceFormats._verifier_nom_libre`, qui fait déjà ce
        contrôle à l'édition d'un format. Même clé de comparaison que la déduplication de
        l'assemblage (`ServicePatrimoine._cle` : casse et espaces de bord repliés), sans quoi la
        garde et la déduplication ne parleraient pas de la même chose.
        """
        cle = libelle.strip().casefold()
        for modele in self._categories.par_bibliotheque():
            if modele.id != sauf and modele.libelle.strip().casefold() == cle:
                raise NomBriqueDejaPris(
                    f"Une catégorie du club porte déjà le libellé « {modele.libelle} »."
                )

    def _verifier_blason_de_bibliotheque(self, blason_id: BlasonId | None) -> None:
        """Vérifie qu'un blason par défaut (facultatif) est bien un **modèle de bibliothèque**.

        Pendant de `_verifier_blason_du_tournoi` pour une catégorie sans tournoi (E01US023). Un
        modèle qui pointerait vers le blason d'un tournoi serait recopié tel quel à **chaque**
        assemblage et traînerait une FK vers une autre édition — et à la copie, le service ne
        retrouvant pas ce blason en bibliothèque, la catégorie atterrirait **sans blason**, en
        silence. Même règle que `ServicePatrimoine.creer_categorie` ; elle est ici parce que
        l'édition passe par ce service, la création par l'autre.
        """
        if blason_id is None:
            return
        blason = self._blasons.par_id(blason_id)
        if blason is None:
            raise BlasonIntrouvable(f"Aucun blason d'identifiant {blason_id}.")
        if blason.tournoi_id is not None:
            raise BriqueHorsBibliotheque(
                f"Le blason {blason_id} appartient au tournoi {blason.tournoi_id} : une catégorie "
                "de bibliothèque ne peut hériter que d'un blason de bibliothèque."
            )

    def _verifier_blason_du_tournoi(
        self, tournoi_id: TournoiId, blason_id: BlasonId | None
    ) -> None:
        """Vérifie qu'un blason par défaut (facultatif) appartient bien au tournoi.

        Sans blason (`None`), rien à vérifier. Sinon, le blason doit exister **et** être rattaché
        au même tournoi, sans quoi le lien serait incohérent → `BlasonHorsTournoi`.
        """
        if blason_id is None:
            return
        blason = self._blasons.par_id(blason_id)
        if blason is None or blason.tournoi_id != tournoi_id:
            raise BlasonHorsTournoi(
                f"Le blason {blason_id} n'appartient pas au tournoi {tournoi_id}."
            )
