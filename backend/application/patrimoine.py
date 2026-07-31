"""Service applicatif Patrimoine — la bibliothèque de briques du club (E01US023, ADR-0060).

Orchestre le domaine derrière les ports repository. Ne connaît ni HTTP, ni SQL, ni la file
d'écriture (sérialisation assurée en amont, côté API) ; il reste synchrone et pur d'infrastructure.

Trois facettes, qui sont les trois temps de la vie d'une brique :

- **bibliothèque** — CRUD des modèles (`tournoi_id is None`), plus le pré-chargement du référentiel
  FFTA **une fois pour toutes** (et non à chaque tournoi, ce qui était le symptôme de fond de
  DETTE-023) ;
- **assemblage** — copier des modèles dans un tournoi. La copie, pas la référence : si un barème
  change en 2027, le tournoi 2026 archivé ne doit pas bouger (ADR-0060 §2) ;
- **promotion** — faire remonter la copie modifiée d'un tournoi dans la bibliothèque, sans
  rétroagir sur les éditions déjà assemblées (ADR-0060 §3).

**Pourquoi un service à part** plutôt que d'étoffer `ServiceCategories` et `ServiceBlasons` : la
copie d'une catégorie doit **réattacher son `blason_id`** à la copie du blason du même tournoi.
C'est une règle **inter-agrégats et inter-collections** — aucun des deux services existants ne voit
les deux côtés, et les faire se connaître aurait couplé deux CRUD indépendants. Ici,
`ServiceCategories` et `ServiceBlasons` restent inchangés dans leur périmètre « un tournoi ».

Les formats de tournoi, eux, vivent dans `application/formats.py` : leur copie n'est pas une brique
rattachée mais les **phases** du tournoi (ADR-0060 §5).
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable
from dataclasses import dataclass

from application.erreurs import (
    BlasonIntrouvable,
    BriqueDejaEnBibliotheque,
    BriqueHorsBibliotheque,
    CategorieIntrouvable,
    NomBriqueDejaPris,
    TournoiIntrouvable,
)
from application.referentiel_ffta import blasons_salle_18m, categories_salle_18m
from domain.blason import Blason, BlasonId, ZoneScore
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


@dataclass(frozen=True)
class RapportAssemblage:
    """Ce qu'a produit un assemblage — **copié** d'un côté, **ignoré** de l'autre.

    Les « ignorés » ne sont pas une anomalie : l'assemblage est **rejouable** (dédup par nom, même
    régime que `precharger_ffta`), et c'est justement ce compte qui permet à l'écran de dire « rien
    de neuf » plutôt que de laisser croire à un échec.
    """

    blasons_copies: int
    blasons_ignores: int
    categories_copiees: int
    categories_ignorees: int


def _cle(libelle: str) -> str:
    """Clé de déduplication d'une brique : nom replié sur la casse et les espaces de bord.

    Volontairement **la même** que celle de `precharger_ffta` (E01US004/E01US022), pas celle de
    `domain.club.cle_nom` : les accents ne sont **pas** repliés ici. Deux briques du référentiel
    FFTA ne diffèrent jamais par un accent, et replier plus large ferait fusionner deux catégories
    que l'organisateur a délibérément distinguées.
    """
    return libelle.strip().casefold()


class ServicePatrimoine:
    """Cas d'usage du patrimoine : bibliothèque, assemblage d'un tournoi, promotion."""

    def __init__(
        self,
        tournois: TournoiRepository,
        categories: CategorieRepository,
        blasons: BlasonRepository,
    ) -> None:
        self._tournois = tournois
        self._categories = categories
        self._blasons = blasons

    # --- Bibliothèque ---------------------------------------------------------------------

    def lister_categories(self) -> list[Categorie]:
        """Renvoie les catégories **modèles** de la bibliothèque (liste éventuellement vide)."""
        return self._categories.par_bibliotheque()

    def lister_blasons(self) -> list[Blason]:
        """Renvoie les blasons **modèles** de la bibliothèque (liste éventuellement vide)."""
        return self._blasons.par_bibliotheque()

    def creer_categorie(
        self,
        libelle: str,
        arme: str | None = None,
        ages: Iterable[TrancheAge] = (),
        sexe: SexeCategorie | None = None,
        blason_id: BlasonId | None = None,
        hauteur_cm: int = HAUTEUR_CENTRE_DEFAUT,
    ) -> Categorie:
        """Crée une catégorie **de bibliothèque** (sans tournoi).

        `blason_id`, s'il est fourni, doit désigner un blason **de la bibliothèque** : un modèle qui
        pointerait vers le blason d'un tournoi serait recopié tel quel à chaque assemblage et
        traînerait une FK vers une autre édition. Lève `BriqueHorsBibliotheque` sinon.
        """
        self._verifier_blason_de_bibliotheque(blason_id)
        categorie = Categorie.creer(None, libelle, arme, ages, sexe, blason_id, hauteur_cm)
        self._exiger_libelle_categorie_libre(categorie.libelle)
        return self._categories.ajouter(categorie)

    def creer_blason(
        self,
        nom: str,
        taille: float,
        capacite: int,
        zones: Iterable[ZoneScore] | None = None,
    ) -> Blason:
        """Crée un blason **de bibliothèque** (sans tournoi) ; `zones` omises → défaut domaine.

        Lève `NomBriqueDejaPris` si un modèle porte déjà ce nom : l'assemblage et la promotion
        dédoublonnent par le nom, deux homonymes les rendraient non déterministes.
        """
        blason = Blason.creer(None, nom, taille, capacite, zones)
        self._exiger_nom_blason_libre(blason.nom)
        return self._blasons.ajouter(blason)

    def dupliquer_categorie(self, categorie_id: CategorieId, libelle: str) -> Categorie:
        """Détache une **copie** d'un modèle sous un nouveau libellé (CA « modifier un officiel »).

        L'issue « en faire une copie pour garder les deux modèles » : l'original reste intact, et la
        copie passe en **création utilisateur** — elle n'est plus le référentiel fédéral, même si
        elle en descend. Pendant exact de `ServiceFormats.dupliquer`, face à l'édition sur place
        (`PUT /categories/{id}`) qui, elle, laisse un officiel officiel (ADR-0060 §4).
        """
        modele = self._modele_categorie(categorie_id)
        # Par la **fabrique**, pas par `replace` : elle seule normalise et refuse un libellé vide
        # (`LibelleCategorieInvalide`). `replace` sur une dataclass sans `__post_init__` laisserait
        # passer « » et fabriquerait une brique invalide en base. `origine` retombe sur son défaut,
        # `utilisateur` — c'est le sens même de la duplication.
        copie = Categorie.creer(
            None,
            libelle,
            modele.arme,
            modele.ages,
            modele.sexe,
            modele.blason_id,
            modele.hauteur_cm,
        )
        self._exiger_libelle_categorie_libre(copie.libelle)
        return self._categories.ajouter(copie)

    def dupliquer_blason(self, blason_id: BlasonId, nom: str) -> Blason:
        """Détache une **copie** d'un modèle de blason sous un nouveau nom (même règle)."""
        modele = self._modele_blason(blason_id)
        copie = Blason.creer(None, nom, modele.taille, modele.capacite, modele.zones)
        self._exiger_nom_blason_libre(copie.nom)
        return self._blasons.ajouter(copie)

    def precharger_ffta(self) -> RapportAssemblage:
        """Pré-charge le référentiel FFTA 18 m **dans la bibliothèque** (E01US023).

        C'est la correction de fond de DETTE-023 : `ServiceCategories.precharger_ffta` recréait les
        quatre blasons canoniques **à chaque tournoi**, faute d'un endroit où les ranger. Ici, le
        référentiel entre au patrimoine une fois, et les tournois en reçoivent des copies.

        Blasons **d'abord** — l'ordre n'est pas cosmétique : `blason_id` est une FK vers un blason
        existant, une catégorie ne peut pas être reliée à un blason qui n'existe pas encore.

        Rejouable sans doublonner (dédup par nom/libellé). Une brique déjà présente est **laissée
        telle quelle** : on ne réaffecte pas rétroactivement un blason à une catégorie que l'admin
        a pu personnaliser. Les briques créées sont marquées `origine = ffta` — ce qui dit d'où
        elles viennent, **pas** qu'elles sont conformes (ADR-0060 §4).
        """
        blasons_par_nom = {_cle(b.nom): b for b in self._blasons.par_bibliotheque()}
        blasons_copies = 0
        for modele in blasons_salle_18m():
            if _cle(modele.nom) in blasons_par_nom:
                continue
            blasons_par_nom[_cle(modele.nom)] = self._blasons.ajouter(
                Blason.creer(
                    None,
                    modele.nom,
                    modele.taille,
                    modele.capacite,
                    modele.zones,
                    origine=OrigineBrique.FFTA,
                )
            )
            blasons_copies += 1

        libelles = {_cle(c.libelle) for c in self._categories.par_bibliotheque()}
        categories_copiees = 0
        for modele_categorie in categories_salle_18m():
            if _cle(modele_categorie.libelle) in libelles:
                continue
            blason = blasons_par_nom[_cle(modele_categorie.blason_nom)]
            self._categories.ajouter(
                Categorie.creer(
                    None,
                    modele_categorie.libelle,
                    modele_categorie.arme,
                    modele_categorie.ages,
                    modele_categorie.sexe,
                    blason.id,
                    modele_categorie.hauteur_cm,
                    origine=OrigineBrique.FFTA,
                )
            )
            libelles.add(_cle(modele_categorie.libelle))
            categories_copiees += 1

        return RapportAssemblage(
            blasons_copies=blasons_copies,
            blasons_ignores=len(blasons_salle_18m()) - blasons_copies,
            categories_copiees=categories_copiees,
            categories_ignorees=len(categories_salle_18m()) - categories_copiees,
        )

    # --- Assemblage d'un tournoi ----------------------------------------------------------

    def assembler(self, tournoi_id: TournoiId) -> RapportAssemblage:
        """Copie **toute la bibliothèque** dans un tournoi (blasons puis catégories).

        Rejouable : une brique dont le nom est déjà pris dans le tournoi est ignorée, jamais
        écrasée — l'organisateur a pu ajuster sa copie, et l'assemblage ne doit pas défaire son
        travail. Les liens `catégorie → blason` sont **réattachés** aux copies du tournoi.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas.
        """
        self._tournoi_existant(tournoi_id)
        blasons_du_tournoi, blasons_copies = self._copier_blasons(tournoi_id)
        categories_copiees, categories_ignorees = self._copier_categories(
            tournoi_id, blasons_du_tournoi
        )
        modeles_blasons = self._blasons.par_bibliotheque()
        return RapportAssemblage(
            blasons_copies=blasons_copies,
            blasons_ignores=len(modeles_blasons) - blasons_copies,
            categories_copiees=categories_copiees,
            categories_ignorees=categories_ignorees,
        )

    def appliquer_blason(self, tournoi_id: TournoiId, blason_id: BlasonId) -> Blason:
        """Copie **un** blason de bibliothèque dans un tournoi et renvoie la copie.

        Idempotent par nom : si le tournoi porte déjà un blason de ce nom, celui-ci est renvoyé
        **tel quel** plutôt que dupliqué — un homonyme de blason dans un même tournoi serait
        indiscernable à l'écran de saisie.

        Lève `TournoiIntrouvable`, `BlasonIntrouvable`, ou `BriqueHorsBibliotheque` si l'identifiant
        vise la copie d'un tournoi et non un modèle.
        """
        self._tournoi_existant(tournoi_id)
        modele = self._modele_blason(blason_id)
        return self._copier_blason(tournoi_id, modele)

    def appliquer_categorie(self, tournoi_id: TournoiId, categorie_id: CategorieId) -> Categorie:
        """Copie **une** catégorie de bibliothèque dans un tournoi et renvoie la copie.

        **Entraîne son blason** : `blason_id` vise un blason du tournoi (règle inter-agrégats
        E01US006), donc le blason par défaut du modèle est copié d'abord s'il manque. Sans cette
        cascade, la copie sortirait soit sans blason, soit avec une FK vers la bibliothèque.

        Idempotent par libellé, comme `appliquer_blason`.
        """
        self._tournoi_existant(tournoi_id)
        modele = self._modele_categorie(categorie_id)
        blason_du_tournoi: BlasonId | None = None
        if modele.blason_id is not None:
            modele_blason = self._blasons.par_id(modele.blason_id)
            if modele_blason is not None:
                blason_du_tournoi = self._copier_blason(tournoi_id, modele_blason).id
        existantes = {_cle(c.libelle): c for c in self._categories.par_tournoi(tournoi_id)}
        deja = existantes.get(_cle(modele.libelle))
        if deja is not None:
            return deja
        return self._categories.ajouter(modele.pour_tournoi(tournoi_id, blason_du_tournoi))

    # --- Promotion ------------------------------------------------------------------------

    def promouvoir_blason(self, blason_id: BlasonId) -> Blason:
        """Fait remonter la copie d'un tournoi dans la bibliothèque (« c'est permanent »).

        Si un modèle porte déjà ce nom, il est **mis à jour** (son identifiant et son origine sont
        conservés — modifier un officiel sur place le laisse officiel, ADR-0060 §4) ; sinon un
        modèle est créé. Les tournois **déjà assemblés gardent leur copie** : rien ici ne les
        touche, et c'est exactement la garantie que la copie achète.

        Lève `BlasonIntrouvable`, ou `BriqueDejaEnBibliotheque` si la brique visée est déjà un
        modèle (geste sans objet).
        """
        copie = self._copie_blason(blason_id)
        existant = self._modele_homonyme_blason(copie.nom)
        if existant is None:
            # Modèle **neuf** : il n'a aucun ancêtre au référentiel fédéral, donc rien ne lui donne
            # sa provenance. Le laisser hériter du `ffta` de la copie ferait entrer une brique
            # renommée localement dans la liste « officiel » de l'atelier — précisément la liste que
            # le commanditaire veut séparée. Mettre à jour un homonyme, en revanche, conserve son
            # origine (« modifier un officiel le laisse officiel », ADR-0060 §4).
            return self._blasons.ajouter(
                dataclasses.replace(copie.en_bibliotheque(), origine=OrigineBrique.UTILISATEUR)
            )
        return self._blasons.enregistrer(
            existant.modifier(copie.nom, copie.taille, copie.capacite, copie.zones)
        )

    def promouvoir_categorie(self, categorie_id: CategorieId) -> Categorie:
        """Fait remonter la copie d'un tournoi dans la bibliothèque (« c'est permanent »).

        Le `blason_id` est **retraduit** vers le blason de bibliothèque de même nom — miroir exact
        du réattachement fait à l'assemblage. S'il n'en existe aucun, le modèle promu part sans
        blason par défaut plutôt qu'avec une FK vers un tournoi : mieux vaut un défaut absent qu'un
        lien qui traverse les éditions.

        Lève `CategorieIntrouvable`, ou `BriqueDejaEnBibliotheque` si la brique est déjà un modèle.
        """
        copie = self._copie_categorie(categorie_id)
        blason_bibliotheque = self._blason_bibliotheque_homonyme(copie.blason_id)
        existante = self._modele_homonyme_categorie(copie.libelle)
        if existante is None:
            # Cf. `promouvoir_blason` : un modèle neuf ne s'auto-proclame pas officiel.
            return self._categories.ajouter(
                dataclasses.replace(
                    copie.en_bibliotheque(blason_bibliotheque),
                    origine=OrigineBrique.UTILISATEUR,
                )
            )
        return self._categories.enregistrer(
            existante.modifier(
                copie.libelle,
                copie.arme,
                copie.ages,
                copie.sexe,
                blason_bibliotheque,
                copie.hauteur_cm,
            )
        )

    # --- Rouages internes -----------------------------------------------------------------

    def _copier_blasons(self, tournoi_id: TournoiId) -> tuple[dict[str, Blason], int]:
        """Copie les blasons de bibliothèque absents du tournoi ; renvoie la table nom → copie."""
        du_tournoi = {_cle(b.nom): b for b in self._blasons.par_tournoi(tournoi_id)}
        copies = 0
        for modele in self._blasons.par_bibliotheque():
            if _cle(modele.nom) in du_tournoi:
                continue
            du_tournoi[_cle(modele.nom)] = self._blasons.ajouter(modele.pour_tournoi(tournoi_id))
            copies += 1
        return du_tournoi, copies

    def _copier_categories(
        self, tournoi_id: TournoiId, blasons_du_tournoi: dict[str, Blason]
    ) -> tuple[int, int]:
        """Copie les catégories absentes du tournoi, liens `blason_id` réattachés à ses copies."""
        modeles_blasons = {b.id: b for b in self._blasons.par_bibliotheque()}
        libelles = {_cle(c.libelle) for c in self._categories.par_tournoi(tournoi_id)}
        copiees = 0
        ignorees = 0
        for modele in self._categories.par_bibliotheque():
            if _cle(modele.libelle) in libelles:
                ignorees += 1
                continue
            blason_du_tournoi: BlasonId | None = None
            modele_blason = modeles_blasons.get(modele.blason_id)
            if modele_blason is not None:
                copie_blason = blasons_du_tournoi.get(_cle(modele_blason.nom))
                blason_du_tournoi = None if copie_blason is None else copie_blason.id
            self._categories.ajouter(modele.pour_tournoi(tournoi_id, blason_du_tournoi))
            libelles.add(_cle(modele.libelle))
            copiees += 1
        return copiees, ignorees

    def _copier_blason(self, tournoi_id: TournoiId, modele: Blason) -> Blason:
        """Copie un blason dans un tournoi, ou renvoie l'homonyme déjà présent (idempotence)."""
        for existant in self._blasons.par_tournoi(tournoi_id):
            if _cle(existant.nom) == _cle(modele.nom):
                return existant
        return self._blasons.ajouter(modele.pour_tournoi(tournoi_id))

    def _blason_bibliotheque_homonyme(self, blason_id: BlasonId | None) -> BlasonId | None:
        """Traduit le blason d'un tournoi en son homonyme de bibliothèque, ou `None`."""
        if blason_id is None:
            return None
        blason = self._blasons.par_id(blason_id)
        if blason is None:
            return None
        modele = self._modele_homonyme_blason(blason.nom)
        return None if modele is None else modele.id

    def _exiger_libelle_categorie_libre(self, libelle: str) -> None:
        if self._modele_homonyme_categorie(libelle) is not None:
            raise NomBriqueDejaPris(f"Une catégorie du club porte déjà le libellé « {libelle} ».")

    def _exiger_nom_blason_libre(self, nom: str) -> None:
        if self._modele_homonyme_blason(nom) is not None:
            raise NomBriqueDejaPris(f"Un blason du club porte déjà le nom « {nom} ».")

    def _modele_homonyme_blason(self, nom: str) -> Blason | None:
        for modele in self._blasons.par_bibliotheque():
            if _cle(modele.nom) == _cle(nom):
                return modele
        return None

    def _modele_homonyme_categorie(self, libelle: str) -> Categorie | None:
        for modele in self._categories.par_bibliotheque():
            if _cle(modele.libelle) == _cle(libelle):
                return modele
        return None

    def _modele_blason(self, blason_id: BlasonId) -> Blason:
        blason = self._blasons.par_id(blason_id)
        if blason is None:
            raise BlasonIntrouvable(f"Aucun blason d'identifiant {blason_id}.")
        if blason.tournoi_id is not None:
            raise BriqueHorsBibliotheque(
                f"Le blason {blason_id} appartient au tournoi {blason.tournoi_id} : seul un "
                "modèle de la bibliothèque est applicable."
            )
        return blason

    def _modele_categorie(self, categorie_id: CategorieId) -> Categorie:
        categorie = self._categories.par_id(categorie_id)
        if categorie is None:
            raise CategorieIntrouvable(f"Aucune catégorie d'identifiant {categorie_id}.")
        if categorie.tournoi_id is not None:
            raise BriqueHorsBibliotheque(
                f"La catégorie {categorie_id} appartient au tournoi {categorie.tournoi_id} : "
                "seul un modèle de la bibliothèque est applicable."
            )
        return categorie

    def _copie_blason(self, blason_id: BlasonId) -> Blason:
        blason = self._blasons.par_id(blason_id)
        if blason is None:
            raise BlasonIntrouvable(f"Aucun blason d'identifiant {blason_id}.")
        if blason.tournoi_id is None:
            raise BriqueDejaEnBibliotheque(
                f"Le blason {blason_id} est déjà un modèle de la bibliothèque : il n'y a rien à "
                "promouvoir."
            )
        return blason

    def _copie_categorie(self, categorie_id: CategorieId) -> Categorie:
        categorie = self._categories.par_id(categorie_id)
        if categorie is None:
            raise CategorieIntrouvable(f"Aucune catégorie d'identifiant {categorie_id}.")
        if categorie.tournoi_id is None:
            raise BriqueDejaEnBibliotheque(
                f"La catégorie {categorie_id} est déjà un modèle de la bibliothèque : il n'y a "
                "rien à promouvoir."
            )
        return categorie

    def _verifier_blason_de_bibliotheque(self, blason_id: BlasonId | None) -> None:
        if blason_id is None:
            return
        blason = self._blasons.par_id(blason_id)
        if blason is None:
            raise BlasonIntrouvable(f"Aucun blason d'identifiant {blason_id}.")
        if blason.tournoi_id is not None:
            raise BriqueHorsBibliotheque(
                f"Le blason {blason_id} appartient à un tournoi : une catégorie de bibliothèque "
                "ne peut hériter que d'un blason de bibliothèque."
            )

    def _tournoi_existant(self, tournoi_id: TournoiId) -> None:
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
