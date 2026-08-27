"""Modèles ORM SQLAlchemy — mapping des agrégats vers les tables (E00US009).

**Séparés du domaine** : le domaine ignore SQLAlchemy (ADR-0003). Un repository
(`repositories.py`) traduit dans les deux sens ORM ↔ agrégat de domaine. Ces classes
peuplent `Base.metadata`, cible des migrations Alembic.
"""

from __future__ import annotations

import datetime

from sqlalchemy import ForeignKey, LargeBinary, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base


class TournoiORM(Base):
    """Table `tournoi` — persistance de l'agrégat `Tournoi`.

    `type_tournoi` et `statut` stockent la **valeur** de leurs énumérations respectives
    (`TypeTournoi`, `StatutTournoi`) ; la traduction chaîne ↔ enum est faite par le repository.

    Le **tarif** n'est plus ici : depuis ADR-0017 (E02US004) il vit sur chaque `Depart` (créneau).
    """

    __tablename__ = "tournoi"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(nullable=False)
    date: Mapped[datetime.date] = mapped_column(nullable=False)
    lieu: Mapped[str | None] = mapped_column(nullable=True)
    type_tournoi: Mapped[str] = mapped_column(nullable=False)
    statut: Mapped[str] = mapped_column(nullable=False)
    # E05US021 : minimum d'inscrits **exigé en plus** du plancher déduit des prélèvements (0040).
    # `NULL` = aucune exigence propre ; le plancher technique, lui, se recalcule des phases.
    effectif_minimum_exige: Mapped[int | None] = mapped_column(nullable=True)
    # E03US007 : cloisonnement des cibles (`aucun` / `categorie` / `blason` / `blason_et_categorie`,
    # 0041). NOT NULL avec défaut serveur `aucun` — un tournoi a **toujours** un réglage, et
    # « aucun » est une valeur, pas une absence : `NULL` aurait ouvert un cinquième état à traduire.
    cloisonnement: Mapped[str] = mapped_column(nullable=False, server_default="aucun")


class DepartORM(Base):
    """Table `depart` — persistance de l'agrégat `Depart` (E02US004, ADR-0017).

    Un départ est un **créneau du tournoi**, pas une propriété d'un archer : le lien archer↔départ
    est `inscription` (E02US009). `tarif_centimes` est un **INTEGER** — l'argent se compte en
    centimes entiers (ADR-0012) — et **NOT NULL** (`0` = gratuit). `horaire` (`HH:MM`) est
    **NOT NULL** depuis E02US010, qui a abandonné le libellé libre facultatif d'E02US004.
    """

    __tablename__ = "depart"
    # Numéro **unique par tournoi** (le service attribue max+1). Déclaré ici, dans le
    # `Base.metadata` cible de l'autogénération Alembic, et **nommé** comme dans la migration
    # `0016` : sans cette ligne, un futur `alembic revision --autogenerate` émettrait un
    # `drop_constraint` fantôme et retirerait le garde-fou en silence. Même convention que
    # `ClubORM.nom` (`unique=True`).
    __table_args__ = (UniqueConstraint("tournoi_id", "numero", name="uq_depart_tournoi_numero"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — enfant direct du tournoi, à traiter
    # dans la même politique de suppression, non tranchée ; ne pas contourner ici.
    tournoi_id: Mapped[int] = mapped_column(ForeignKey("tournoi.id"), nullable=False)
    numero: Mapped[int] = mapped_column(nullable=False)
    horaire: Mapped[str] = mapped_column(nullable=False)
    tarif_centimes: Mapped[int] = mapped_column(nullable=False)
    # Quota d'inscrits **facultatif** (E02US006) : NULL = créneau sans plafond. Le contrôle du
    # dépassement est applicatif (service), nulle contrainte SQL ne l'exprime (cf. `DepartComplet`).
    quota: Mapped[int | None] = mapped_column(nullable=True)


class ClubORM(Base):
    """Table `club` — persistance de l'agrégat `Club` (E02US001).

    **Aucune FK vers `tournoi`** : le référentiel est global, la table n'est pas dans la descendance
    de `tournoi` (DETTE-001 ne la concerne pas). ⚠️ `nom` est `UNIQUE` **exact** — il n'attrape que
    les homonymes au caractère près ; le refus fonctionnel, plus large, vit dans `ServiceClubs`
    (`cle_nom` replie espaces, casse et accents). Écart assumé : le writer unique garantit qu'aucune
    écriture ne le contourne.
    """

    __tablename__ = "club"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(nullable=False, unique=True)


class CategorieORM(Base):
    """Table `categorie` — persistance de l'agrégat `Categorie` (E01US003).

    `sexe` stocke la **valeur** de l'énumération `SexeCategorie` (`H` / `F` / `mixte`) ou `NULL` ;
    la traduction chaîne ↔ enum est faite par le repository.
    """

    __tablename__ = "categorie"

    id: Mapped[int] = mapped_column(primary_key=True)
    # `tournoi_id` distingue un **modèle** de bibliothèque (`NULL`, patrimoine du club, réutilisable
    # d'une année sur l'autre) d'une **copie** appartenant à un tournoi (E01US023, ADR-0060) — même
    # patron que `gabarit_salle` depuis E01US008. Avant E01US023 la colonne était obligatoire : d'où
    # un atelier qui promettait « hors tournoi » sans pouvoir le tenir (DETTE-023, résorbée).
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — la politique de suppression d'un
    # tournoi non vide (cascade ou refus 409) n'est pas tranchée ; ne pas contourner ici.
    tournoi_id: Mapped[int | None] = mapped_column(ForeignKey("tournoi.id"), nullable=True)
    # `ffta` (issue du préchargement officiel) ou `utilisateur` — ce qui permet les deux listes
    # séparées que le commanditaire demande, et la copie plutôt que l'écrasement d'un officiel.
    origine: Mapped[str] = mapped_column(nullable=False, server_default="utilisateur")
    libelle: Mapped[str] = mapped_column(nullable=False)
    arme: Mapped[str | None] = mapped_column(nullable=True)
    # Tranches d'âge éligibles, stockées en **tableau JSON** de codes (ex. `["U15","U18"]`,
    # E01US013) : une catégorie couvre une ou plusieurs tranches, `"[]"` = aucune contrainte. La
    # (dé)sérialisation est faite par le repository (patron de la `config` des gabarits/phases).
    ages: Mapped[str] = mapped_column(nullable=False)
    sexe: Mapped[str | None] = mapped_column(nullable=True)
    # Blason par défaut, facultatif (E01US006). La suppression d'un blason référencé est refusée
    # côté service (409, `BlasonReference`).
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — lien latéral au sein de la
    # descendance du tournoi, à traiter dans la même politique de suppression, non tranchée.
    blason_id: Mapped[int | None] = mapped_column(ForeignKey("blason.id"), nullable=True)
    # Hauteur du centre de l'or (sol → centre), en cm (E03US001, ADR-0022) : 130 par défaut, 110
    # pour les U11. Pilote la contrainte de placement « une butte, une hauteur ». Renseignée pour
    # les lignes antérieures par la migration `0020` (backfill 130, 110 si `ages` contient U11).
    hauteur_cm: Mapped[int] = mapped_column(nullable=False)


class BlasonORM(Base):
    """Table `blason` — persistance de l'agrégat `Blason` (E01US005 ; `zones` : E01US014).

    `taille` est la fraction de place occupée (`]0, 1]`), `capacite` le nombre d'archers admis ; la
    validation est portée par le domaine.

    `zones` stocke les valeurs de score en **JSON** (même procédé que `GabaritSalleORM.config`) :
    une table fille coûterait une jointure pour une donnée toujours lue en bloc, jamais requêtée.
    """

    __tablename__ = "blason"

    id: Mapped[int] = mapped_column(primary_key=True)
    # `tournoi_id` distingue un **modèle** de bibliothèque (`NULL`, patrimoine du club, réutilisable
    # d'une année sur l'autre) d'une **copie** appartenant à un tournoi (E01US023, ADR-0060) — même
    # patron que `gabarit_salle` depuis E01US008. Avant E01US023 la colonne était obligatoire : d'où
    # un atelier qui promettait « hors tournoi » sans pouvoir le tenir (DETTE-023, résorbée).
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — la politique de suppression d'un
    # tournoi non vide (cascade ou refus 409) n'est pas tranchée ; ne pas contourner ici.
    tournoi_id: Mapped[int | None] = mapped_column(ForeignKey("tournoi.id"), nullable=True)
    origine: Mapped[str] = mapped_column(nullable=False, server_default="utilisateur")
    nom: Mapped[str] = mapped_column(nullable=False)
    taille: Mapped[float] = mapped_column(nullable=False)
    capacite: Mapped[int] = mapped_column(nullable=False)
    zones: Mapped[str] = mapped_column(nullable=False)


class GabaritSalleORM(Base):
    """Table `gabarit_salle` — persistance de l'agrégat `GabaritSalle` (E01US007, E01US008).

    Le plafond de chaque cible est dans `config` (JSON) ; `nb_cibles` est dénormalisé pour la
    lecture. ⚠️ `tournoi_id` distingue un **modèle** de bibliothèque (`NULL`, réutilisable) d'une
    **instance** appliquée à un tournoi : appliquer un modèle en crée une copie ajustable sans
    altérer le modèle. Un tournoi porte au plus une instance.
    """

    __tablename__ = "gabarit_salle"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(nullable=False)
    nb_cibles: Mapped[int] = mapped_column(nullable=False)
    config: Mapped[str] = mapped_column(nullable=False)
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — l'instance appartient à la
    # descendance du tournoi, à traiter dans la même politique de suppression, non tranchée.
    tournoi_id: Mapped[int | None] = mapped_column(ForeignKey("tournoi.id"), nullable=True)


class FormatTournoiORM(Base):
    """Table `format_tournoi` — persistance de l'agrégat `FormatTournoi` (E01US023, ADR-0060 §5).

    **Aucune FK vers `tournoi`** : un format n'existe qu'en bibliothèque (patrimoine du club), sa
    « copie » dans un tournoi étant les lignes de `phase` produites par son application. Hors
    descendance de `tournoi`, donc hors DETTE-001 — même régime que `club`. La **séquence de
    modèles de phases** est dans `config` (JSON), même forme que `PhaseORM.config` pour que les deux
    se relisent avec les mêmes fonctions. `nom` est `UNIQUE` : la promotion est ainsi idempotente.
    """

    __tablename__ = "format_tournoi"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(nullable=False, unique=True)
    # `ffta` (préchargé officiel) ou `utilisateur` — les deux listes séparées de l'atelier.
    origine: Mapped[str] = mapped_column(nullable=False, server_default="utilisateur")
    config: Mapped[str] = mapped_column(nullable=False)


class ArcherORM(Base):
    """Table `archer` — persistance de l'agrégat `Archer` (E00US011, inscription en E02US002)."""

    __tablename__ = "archer"

    id: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — la politique de suppression d'un
    # tournoi non vide (cascade ou refus 409) n'est pas tranchée ; ne pas contourner ici.
    tournoi_id: Mapped[int] = mapped_column(ForeignKey("tournoi.id"), nullable=False)
    nom: Mapped[str] = mapped_column(nullable=False)
    prenom: Mapped[str] = mapped_column(nullable=False)
    cible: Mapped[int | None] = mapped_column(nullable=True)
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — `categorie` appartient, elle, à la
    # descendance du tournoi (contrairement à `club` ci-dessous), donc cette FK relève bien de la
    # politique de suppression non tranchée. E02US002 élargit la ligne existante du registre.
    categorie_id: Mapped[int] = mapped_column(ForeignKey("categorie.id"), nullable=False)
    # Club de rattachement, **facultatif** : `NULL` = club encore *inconnu*, jamais « aucun club »
    # (ADR-0014). L'anomalie est signalée à l'écran, pas comblée par un club sentinelle ; la
    # suppression d'un club référencé est refusée côté service (409, `ClubReference`).
    #
    # **Hors périmètre de DETTE-001** : elle pointe vers `club`, qui n'est PAS dans la descendance
    # de `tournoi` — c'est le sens inverse qu'elle contraint, et ce cas-là est tranché.
    club_id: Mapped[int | None] = mapped_column(ForeignKey("club.id"), nullable=True)
    # Handicap (E05US015) : deux colonnes, jamais une seule — le handicap **officiel** entretenu par
    # le club, et la **surcharge** qui le prime pour cette édition (demande du commanditaire,
    # 31/07/2026). `NULL` = non renseigné, distinct d'un handicap **nul** : un archer sans handicap
    # connu et un archer à handicap 0 concourent pareil au scratch, mais seul le second a été
    # évalué. La nuance ne change rien au calcul et tout à ce que l'écran doit afficher.
    handicap_officiel: Mapped[int | None] = mapped_column(nullable=True)
    handicap_surcharge: Mapped[int | None] = mapped_column(nullable=True)


class ScoreORM(Base):
    """Table `score` — persistance de l'agrégat `Score` (E00US011)."""

    __tablename__ = "score"

    id: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — enfant indirect de `tournoi` via
    # `archer`, donc concerné par la même politique de suppression, non tranchée ; ne pas
    # contourner ici.
    archer_id: Mapped[int] = mapped_column(ForeignKey("archer.id"), nullable=False)
    points: Mapped[int] = mapped_column(nullable=False)


class InscriptionORM(Base):
    """Table `inscription` — lien archer↔départ, portant `paye` (E02US009, ADR-0017).

    Table de **liaison** : un archer s'inscrit sur un ou plusieurs départs (créneaux) de son
    tournoi. `paye` est le **seul fait propre** à l'inscription (booléen, `0`/`1` en SQLite) ; le
    montant dû n'est **pas** stocké — il se dérive du `tarif_centimes` du départ à la lecture
    (ADR-0017). C'est là que reviennent les colonnes `paye`/`montant_du` que le modèle v0.3 posait à
    tort sur `depart` (elles étaient par-archer).
    """

    __tablename__ = "inscription"
    # UNIQUE(archer_id, depart_id) : un archer ne s'inscrit qu'une fois sur un même créneau. Nommée
    # comme dans la migration `0017` — sans cette ligne dans `Base.metadata`, un futur
    # `--autogenerate` émettrait un `drop_constraint` fantôme et retirerait le garde-fou en silence.
    # Le refus fonctionnel (`DejaInscrit`, 409) est porté en amont par `ServiceInscriptions`.
    __table_args__ = (
        UniqueConstraint("archer_id", "depart_id", name="uq_inscription_archer_depart"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-001 (docs/dette.md) : **deux** FK sans ON DELETE CASCADE — enfant indirect du tournoi
    # via `archer` **et** via `depart`. La purge en cascade est applicative et maîtrisée
    # (`ArcherRepositorySQL.supprimer` et `DepartRepositorySQL.supprimer`) ; ne pas contourner ici.
    archer_id: Mapped[int] = mapped_column(ForeignKey("archer.id"), nullable=False)
    depart_id: Mapped[int] = mapped_column(ForeignKey("depart.id"), nullable=False)
    paye: Mapped[bool] = mapped_column(nullable=False, default=False)


class PlacementORM(Base):
    """Table `placement` — affectation matérialisée d'un inscrit sur une case (E03US004, ADR-0024).

    Une ligne = un inscrit **posé** ; `inscription_id` en clé primaire. Un inscrit **sans** ligne
    est *en réserve* — l'absence de ligne *est* l'information. `depart_id` est dénormalisé pour lire
    le plan d'un départ sans jointure. ⚠️ **`ON DELETE CASCADE`**, à rebours de DETTE-001 :
    `placement` est de la donnée **dérivée, reconstructible et feuille**, pas de la donnée saisie
    qui remonte l'arbre du tournoi. Les FK sont *enforced* (`engine.py`).
    """

    __tablename__ = "placement"

    inscription_id: Mapped[int] = mapped_column(
        ForeignKey("inscription.id", ondelete="CASCADE"), primary_key=True
    )
    depart_id: Mapped[int] = mapped_column(
        ForeignKey("depart.id", ondelete="CASCADE"), nullable=False
    )
    cible_index: Mapped[int] = mapped_column(nullable=False)
    # DETTE-042 : le terme métier est « couloir de tir » (ADR-0073) ; renommer cette colonne
    # demande une migration, faite avec DETTE-010 (E01US019) pour n'en écrire qu'une.
    position: Mapped[str] = mapped_column(nullable=False)


class PlacementTableauORM(Base):
    """Table `placement_tableau` — pose matérialisée d'un duelliste, par phase (E03US009, ADR-0048).

    Le **plan de duels**, distinct du plan de cibles (`placement`, par départ) : scopé par la
    **phase**, clé primaire `(phase_id, inscription_id)`. ⚠️ L'**appariement** n'est **pas**
    persisté — il se recalcule du classement (ADR-0023/0048) ; seule la **pose** l'est, pour
    l'ajustement au glisser-déposer. `ON DELETE CASCADE` sur les deux FK (donnée dérivée, feuille).
    """

    __tablename__ = "placement_tableau"

    phase_id: Mapped[int] = mapped_column(
        ForeignKey("phase.id", ondelete="CASCADE"), primary_key=True
    )
    inscription_id: Mapped[int] = mapped_column(
        ForeignKey("inscription.id", ondelete="CASCADE"), primary_key=True
    )
    cible_index: Mapped[int] = mapped_column(nullable=False)
    # DETTE-042 : le terme métier est « couloir de tir » (ADR-0073) ; renommer cette colonne
    # demande une migration, faite avec DETTE-010 (E01US019) pour n'en écrire qu'une.
    position: Mapped[str] = mapped_column(nullable=False)


class PlacementParBlocORM(Base):
    """Table `placement_par_bloc` — les couloirs qu'un **groupe** occupe, par phase (E05US023).

    ⚠️ Seule table de placement dont l'unité posée ne soit pas un archer (ADR-0083 §3) : **le tireur
    au repos change à chaque tour**, donc persister « archer → couloir » écrirait une information
    **fausse**. Une ligne = un couloir, `rang` portant sa position dans le bloc. ⚠️ La clé primaire
    est le **couloir** — la base fait respecter *un couloir, un occupant*, et
    `UNIQUE(phase_id, groupe_numero, rang)` tient l'autre bout. `ON DELETE CASCADE` sur `phase_id`.
    """

    __tablename__ = "placement_par_bloc"
    __table_args__ = (
        UniqueConstraint("phase_id", "groupe_numero", "rang", name="uq_placement_par_bloc"),
    )

    phase_id: Mapped[int] = mapped_column(
        ForeignKey("phase.id", ondelete="CASCADE"), primary_key=True
    )
    cible_index: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-042 : le terme métier est « couloir de tir » (ADR-0073) ; la colonne garde le nom
    # `position` de ses deux aînées — **délibérément**, plutôt que d'introduire ici le bon nom et
    # de laisser trois tables de placement en nommer deux à l'ancienne et une à la neuve. Le
    # renommage se fera d'un bloc avec DETTE-010, pour n'écrire qu'une migration.
    position: Mapped[str] = mapped_column(primary_key=True)
    groupe_numero: Mapped[int] = mapped_column(nullable=False)
    rang: Mapped[int] = mapped_column(nullable=False)


class PhaseORM(Base):
    """Table `phase` — persistance de l'agrégat `Phase` (E01US009/ADR-0011).

    `type` et `statut` stockent la **valeur** de leurs énumérations ; les politiques sont dans
    `config` (JSON, forme `config.policies` d'ADR-0046), ce qui permet d'en ajouter **sans migration
    de schéma**. ⚠️ **La phase pend au `depart`, plus au `tournoi`** (E01US025, ADR-0075, migration
    0042) : le départ est la **portée sportive**, `ordre` est contigu 1..N **par départ**, et le
    tournoi reste atteignable par jointure `phase → depart → tournoi`.
    """

    __tablename__ = "phase"
    # Une seule instance par (créneau, rang) : deux avancements du même rang dans le même départ
    # n'auraient aucun sens, et le service s'appuie sur cette unicité pour synchroniser.
    __table_args__ = (UniqueConstraint("depart_id", "ordre", name="uq_phase_depart_ordre"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — enfant du départ depuis ADR-0075, donc
    # petit-enfant du tournoi ; même politique de suppression non tranchée, ne pas contourner ici.
    depart_id: Mapped[int] = mapped_column(ForeignKey("depart.id"), nullable=False)
    # `ordre` est la **clé de jointure** vers la définition (`deroule_etape` du tournoi de ce
    # départ) : c'est lui, et non un `etape_id`, parce que le déroulé s'édite par rang — un
    # réordonnancement remappe déjà les ordres partout (DETTE-026), et une FK dupliquerait
    # l'information tout en pouvant en diverger.
    ordre: Mapped[int] = mapped_column(nullable=False)
    statut: Mapped[str] = mapped_column(nullable=False)


class DerouleEtapeORM(Base):
    """Table `deroule_etape` — la **définition** d'une étape du déroulé d'un tournoi (ADR-0076).

    Le déroulé se définit **une fois** par tournoi ; chaque départ le rejoue en portant un simple
    **avancement** (`PhaseORM`). Avant le 07/08/2026, appliquer un format écrivait N copies
    complètes, libres de diverger en silence. Les politiques vivent dans `config` (JSON, forme
    d'ADR-0046) : le format n'a pas changé, il a **changé de table**.
    """

    __tablename__ = "deroule_etape"
    # Un seul réglage par rang dans un tournoi : c'est la définition même d'une séquence 1..N.
    __table_args__ = (UniqueConstraint("tournoi_id", "ordre", name="uq_deroule_tournoi_ordre"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-001 : FK sans ON DELETE CASCADE — enfant direct du tournoi, même politique de
    # suppression non tranchée que le reste de sa descendance.
    tournoi_id: Mapped[int] = mapped_column(ForeignKey("tournoi.id"), nullable=False)
    ordre: Mapped[int] = mapped_column(nullable=False)
    type: Mapped[str] = mapped_column(nullable=False)
    config: Mapped[str] = mapped_column(nullable=False)


class FranchissementArretORM(Base):
    """Table `franchissement_arret` — ce qu'un **arrêt programmé** a coupé (E05US033, ADR-0091).

    ⚠️ **Cette table ne porte pas les arrêts eux-mêmes** : leur *définition* vit dans
    `deroule_etape.config` (JSON, sans migration), rejouée par chaque créneau (ADR-0076). Seul état
    **persisté** du mécanisme, la condition de déclenchement étant **monotone** — sans mémoire, la
    phase repasserait en pause à chaque reprise. `phases_arretees` liste celles que cet arrêt a
    mises en pause ; les déduire à la reprise relancerait une phase suspendue pour autre chose.
    """

    __tablename__ = "franchissement_arret"
    # Un arrêt ne se franchit qu'une fois par créneau : c'est l'idempotence du déclencheur, tenue
    # par le schéma et pas seulement par le service. Deux tablettes qui valident dans la même
    # seconde ne peuvent donc pas produire deux franchissements du même arrêt.
    __table_args__ = (
        UniqueConstraint("phase_id", "apres_tour", name="uq_franchissement_phase_tour"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-001 : FK sans ON DELETE CASCADE — descendant du départ par la phase, même politique de
    # suppression non tranchée que le reste de la descendance du tournoi ; ne pas contourner ici.
    phase_id: Mapped[int] = mapped_column(ForeignKey("phase.id"), nullable=False)
    apres_tour: Mapped[int] = mapped_column(nullable=False)
    etat: Mapped[str] = mapped_column(nullable=False)
    # Deux documents JSON plutôt que deux tables d'association : les volumes sont de l'ordre de
    # quelques lignes par créneau, rien ne les interroge autrement que « pour cet arrêt », et la
    # règle 12 (« l'infra reste simple : mono-club, local ») dit où mettre la rigueur.
    # `server_default` et non `default` : c'est la convention du fichier partout où la migration en
    # pose un, et l'écart faisait diverger le schéma des métadonnées de celui que produit Alembic
    # (`0048` déclare bien `server_default`). Relevé en revue (axe A).
    tours_a_finir: Mapped[str] = mapped_column(nullable=False, server_default="{}")
    phases_arretees: Mapped[str] = mapped_column(nullable=False, server_default="[]")
    # `arrete_depuis` — quand cet arrêt a éteint sa **première** phase (E05US034). Nullable, et le
    # `NULL` a un sens : cet arrêt n'a encore rien éteint (arrêt de créneau armé, ou pause manquée).
    # C'est ce que la pastille du tableau de bord décompte ; aucune règle du mécanisme n'en dépend,
    # ce qui est la raison pour laquelle un `NULL` y est inoffensif.
    arrete_depuis: Mapped[datetime.datetime | None] = mapped_column(nullable=True)


class ArretDeCirconstanceORM(Base):
    """Table `arret_de_circonstance` — une pause décidée **le jour J** (E05US034, ADR-0092).

    ⚠️ Un arrêt posé à l'atelier est de la *composition* : il vit dans `deroule_etape.config` et
    **tous les créneaux le rejouent** (ADR-0076 §4). Un arrêt posé pendant que la salle tire est de
    la *conduite* : il vit ici, porte un `depart_id`, et **personne ne le rejoue** (§5).
    ⚠️ Une table plutôt qu'un JSON sur `depart` : l'unicité `(depart_id, phase_id, apres_tour)` doit
    être tenue par le **schéma**, la pose étant concurrente. Le volume, lui, ne tranche pas.
    """

    __tablename__ = "arret_de_circonstance"
    # Deux fois le même arrêt sur la même phase ne coupe qu'une fois : le dire au schéma, et pas
    # seulement au service, ferme le double-clic de deux tablettes d'admin dans la même seconde.
    __table_args__ = (
        UniqueConstraint(
            "depart_id", "phase_id", "apres_tour", name="uq_arret_circonstance_phase_tour"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-001 : FK sans ON DELETE CASCADE — descendance du tournoi, même politique de suppression
    # non tranchée que le reste ; ne pas contourner ici.
    depart_id: Mapped[int] = mapped_column(ForeignKey("depart.id"), nullable=False)
    phase_id: Mapped[int] = mapped_column(ForeignKey("phase.id"), nullable=False)
    apres_tour: Mapped[int] = mapped_column(nullable=False)
    portee: Mapped[str] = mapped_column(nullable=False)


class ScoreurORM(Base):
    """Table `scoreur` — persistance de l'agrégat `Scoreur` (E10US003).

    Scoreur **du tournoi**, comme `depart`, redéfinissable à tout moment (`D-14`). `code` est
    `UNIQUE` **global** : le scoreur ouvre sa session par son seul code, qui doit le désigner sans
    ambiguïté d'un tournoi à l'autre. L'unicité est **exacte** et suffit — le service stocke déjà le
    code canonique (`normaliser_code`), et un code n'a pas d'accent.
    """

    __tablename__ = "scoreur"

    id: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — enfant direct du tournoi, à traiter
    # dans la même politique de suppression, non tranchée ; ne pas contourner ici.
    tournoi_id: Mapped[int] = mapped_column(ForeignKey("tournoi.id"), nullable=False)
    nom: Mapped[str] = mapped_column(nullable=False)
    code: Mapped[str] = mapped_column(nullable=False, unique=True)


class PosteORM(Base):
    """Table `poste` — persistance de l'agrégat `Poste` (E04US001, ADR-0029 ; E07US004, ADR-0064).

    Credential d'un **lieu**, plus le `code` imprimé sous le QR — `UNIQUE` **global**. Deux natures
    (`type`) dans **une seule table** : une `cible` porte `cible_index`, un `ecran` porte `libelle`,
    `deroule_json` et son réglage de pages. ⚠️ `cible_index` est donc **nullable**, ce qui affaiblit
    `uq_poste_tournoi_cible` (SQLite tient chaque `NULL` pour distinct) — c'est le CA « plusieurs
    écrans ». L'exclusivité `cible_index` ↔ `libelle` est portée par le domaine (règle 2).
    """

    __tablename__ = "poste"

    id: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — enfant direct du tournoi, à traiter
    # dans la même politique de suppression, non tranchée ; ne pas contourner ici.
    tournoi_id: Mapped[int] = mapped_column(ForeignKey("tournoi.id"), nullable=False)
    cible_index: Mapped[int | None] = mapped_column(nullable=True)
    code: Mapped[str] = mapped_column(nullable=False, unique=True)
    type: Mapped[str] = mapped_column(nullable=False, server_default="cible")
    libelle: Mapped[str | None] = mapped_column(nullable=True)
    deroule_json: Mapped[str | None] = mapped_column(nullable=True)
    noms_par_page: Mapped[int | None] = mapped_column(nullable=True)
    cadence_page_s: Mapped[int | None] = mapped_column(nullable=True)

    __table_args__ = (UniqueConstraint("tournoi_id", "cible_index", name="uq_poste_tournoi_cible"),)


class SerieORM(Base):
    """Table `serie` — racine de persistance de l'agrégat `Serie` (saisie de qualif, E04US002).

    **Une série par `(phase, archer)`** (E05US025, ADR-0082) : un déroulé peut compter plusieurs
    qualifications. Les volées vivent dans `volee` ; le **cumul** n'est pas stocké, il se recalcule.
    Deux FK **sans `ON DELETE`** (DETTE-001) — c'est de la donnée **saisie** —, la cascade
    `archer` → `serie` étant réalisée **applicativement** par `ArcherRepositorySQL.supprimer`.
    """

    __tablename__ = "serie"
    # UNIQUE(phase_id, archer_id) : une feuille par archer **et par phase** (E05US025, ADR-0082).
    # Nommée comme dans la migration `0044` — présente ici, dans le `Base.metadata` cible de
    # l'autogénération, sinon un futur `--autogenerate` émettrait un `drop_constraint` fantôme.
    #
    # DETTE-046 **résorbée** ici : l'unicité au tournoi était fausse depuis ADR-0075 (un archer sur
    # deux créneaux n'avait qu'un emplacement). La phase **subsume** le départ, donc descendre la
    # clé jusqu'à elle règle ce cas *et* celui des qualifications multiples, avec un seul champ.
    __table_args__ = (UniqueConstraint("phase_id", "archer_id", name="uq_serie_phase_archer"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — enfant direct du tournoi, à traiter
    # dans la même politique de suppression, non tranchée ; ne pas contourner ici.
    #
    # ⚠️ **Conservé bien que dérivable** (phase -> depart -> tournoi) : c'est la portée que lisent
    # les vues d'ensemble, et la jointure à chaque lecture coûterait plus qu'elle ne rapporte. Ce
    # n'est plus une clé, seulement un cadre — l'unicité est descendue à la phase.
    tournoi_id: Mapped[int] = mapped_column(ForeignKey("tournoi.id"), nullable=False)
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — enfant indirect du tournoi via
    # `archer`. La cascade est **applicative et maîtrisée** (`ArcherRepositorySQL.supprimer`), à
    # l'image de `score.archer_id`/`inscription.archer_id` ; ne pas contourner ici.
    archer_id: Mapped[int] = mapped_column(ForeignKey("archer.id"), nullable=False)
    # `ON DELETE CASCADE`, à l'image de `duel.phase_id` : les flèches d'une phase supprimée n'ont
    # plus d'existence sportive. C'est le même parti que le tableau de duels, dont la suppression
    # emporte les rencontres — et non celui de DETTE-001, qui concerne la descendance du *tournoi*,
    # dont la politique de purge n'est pas tranchée.
    phase_id: Mapped[int] = mapped_column(
        ForeignKey("phase.id", ondelete="CASCADE"), nullable=False
    )


class VoleeORM(Base):
    """Table `volee` — une volée d'une série (E04US002), table **enfant** de `serie`.

    Une ligne = une volée saisie : `numero`, `valeurs` (JSON, comme `BlasonORM.zones`), et les
    marqueurs `saisie_par` / `validee_par` — ce dernier non `NULL` **est** le verrou. `created_at`
    est une **métadonnée de persistance**, hors du domaine (arbitrage de revue), **préservée par
    numéro** à travers le purge + réinsertion. ⚠️ `ON DELETE CASCADE` sur `serie_id`, à rebours de
    DETTE-001 : une volée est un **composant strict** de son agrégat.
    """

    __tablename__ = "volee"
    # UNIQUE(serie_id, numero) : un seul rang N par série. Le domaine borne déjà `1..N` (barème) ;
    # cette contrainte est le garde-fou d'intégrité côté base. Nommée comme dans la migration 0026.
    __table_args__ = (UniqueConstraint("serie_id", "numero", name="uq_volee_serie_numero"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    serie_id: Mapped[int] = mapped_column(
        ForeignKey("serie.id", ondelete="CASCADE"), nullable=False
    )
    numero: Mapped[int] = mapped_column(nullable=False)
    valeurs: Mapped[str] = mapped_column(nullable=False)
    saisie_par: Mapped[str | None] = mapped_column(nullable=True)
    validee_par: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class DuelORM(Base):
    """Table `duel` — le **tir** d'un match du tableau (saisie en duels, E04US013, ADR-0049).

    Une ligne = le résultat d'un match, keyé `(phase_id, match_numero)` : le tir (`manches`,
    `barrage`, `validee_par`) **et l'identité des deux duellistes**. ⚠️ Cette identité n'est **pas**
    l'appariement *plan* (recalculé du classement, ADR-0048) : elle **ancre** le tir, si bien qu'une
    divergence est **détectée** au lieu d'un score ré-attribué en silence (ADR-0049 §4).
    """

    __tablename__ = "duel"

    phase_id: Mapped[int] = mapped_column(
        ForeignKey("phase.id", ondelete="CASCADE"), primary_key=True
    )
    match_numero: Mapped[int] = mapped_column(primary_key=True)
    haut_genre: Mapped[str] = mapped_column(nullable=False)
    haut_ref: Mapped[int] = mapped_column(nullable=False)
    bas_genre: Mapped[str] = mapped_column(nullable=False)
    bas_ref: Mapped[int] = mapped_column(nullable=False)
    manches: Mapped[str] = mapped_column(nullable=False)
    barrage: Mapped[str | None] = mapped_column(nullable=True)
    validee_par: Mapped[str | None] = mapped_column(nullable=True)


class EntreeAuditORM(Base):
    """Table `entree_audit` — persistance de l'agrégat `EntreeAudit` (journal d'audit, E10US005).

    Journal **du tournoi**, en **ajout seul** : ni `enregistrer` ni `supprimer` côté repository —
    une trace ne se retouche pas. `action` stocke la **valeur** de `ActionAuditee`.

    `auteur` est le **nom** de qui a agi (pas une FK) : la trace survit à la suppression du scoreur.
    `avant`/`apres` sont nullables — une validation n'a pas d'état antérieur, une correction si.
    """

    __tablename__ = "entree_audit"

    id: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — enfant direct du tournoi, à traiter
    # dans la même politique de suppression, non tranchée ; ne pas contourner ici.
    tournoi_id: Mapped[int] = mapped_column(ForeignKey("tournoi.id"), nullable=False)
    action: Mapped[str] = mapped_column(nullable=False)
    auteur: Mapped[str] = mapped_column(nullable=False)
    horodatage: Mapped[datetime.datetime] = mapped_column(nullable=False)
    objet: Mapped[str] = mapped_column(nullable=False)
    avant: Mapped[str | None] = mapped_column(nullable=True)
    apres: Mapped[str | None] = mapped_column(nullable=True)


class ForfaitORM(Base):
    """Table `forfait` — persistance de l'agrégat `Forfait` (abandon / DSQ, E04US015, ADR-0050).

    Un forfait par `(tournoi, archer, phase)`. `declare_par` est le **nom** du déclarant (pas une
    FK) : la déclaration survit à la suppression du scoreur. L'annulation (`D-15`) **supprime** la
    ligne — les flèches ne sont jamais touchées. `ON DELETE CASCADE` sur `phase_id`, les autres FK
    restant sans `ON DELETE` (DETTE-001). ⚠️ `archer_id` est purgé par la **cascade applicative** de
    `ArcherRepositorySQL` — l'oublier bloque la suppression d'un archer forfaitaire.
    """

    __tablename__ = "forfait"
    __table_args__ = (
        UniqueConstraint(
            "tournoi_id", "archer_id", "phase_id", name="uq_forfait_tournoi_archer_phase"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — enfant direct du tournoi (dénormalisé
    # pour `par_tournoi`), à traiter à la suppression du tournoi ; ne pas contourner.
    tournoi_id: Mapped[int] = mapped_column(ForeignKey("tournoi.id"), nullable=False)
    # DETTE-001 : FK sans ON DELETE CASCADE — enfant indirect via `archer` (cf. `serie.archer_id`).
    archer_id: Mapped[int] = mapped_column(ForeignKey("archer.id"), nullable=False)
    phase_id: Mapped[int] = mapped_column(
        ForeignKey("phase.id", ondelete="CASCADE"), nullable=False
    )
    nature: Mapped[str] = mapped_column(nullable=False)
    declare_par: Mapped[str] = mapped_column(nullable=False)
    declare_le: Mapped[datetime.datetime] = mapped_column(nullable=False)
    motif: Mapped[str | None] = mapped_column(nullable=True)


class RemboursementORM(Base):
    """Table `remboursement` — registre des sommes encaissées à rendre (E08US005, ADR-0057).

    Née quand une **inscription payée disparaît**, la ligne **survit** à cette disparition : elle en
    est la trace comptable. D'où l'absence de FK vers `inscription` ou `depart` — on fige des
    **instantanés textuels** et le montant, comme `entree_audit`/`forfait` figent le nom de
    l'auteur. Seul `tournoi_id` reste une FK ; `traite_le` est nullable (rempli au traitement).
    """

    __tablename__ = "remboursement"

    id: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — enfant direct du tournoi, à traiter
    # dans la politique de suppression du tournoi (non tranchée) ; ne pas contourner ici.
    tournoi_id: Mapped[int] = mapped_column(ForeignKey("tournoi.id"), nullable=False)
    archer_prenom: Mapped[str] = mapped_column(nullable=False)
    archer_nom: Mapped[str] = mapped_column(nullable=False)
    creneau: Mapped[str] = mapped_column(nullable=False)
    montant_centimes: Mapped[int] = mapped_column(nullable=False)
    motif: Mapped[str] = mapped_column(nullable=False)
    statut: Mapped[str] = mapped_column(nullable=False)
    cree_le: Mapped[datetime.datetime] = mapped_column(nullable=False)
    traite_le: Mapped[datetime.datetime | None] = mapped_column(nullable=True)


class BarrageORM(Base):
    """Table `barrage` — un tir de barrage **annoncé** (E06US003, ADR-0066).

    `portee` stocke la valeur de `PorteeBarrage` ; les trois sont modélisées d'emblée bien qu'une
    seule soit câblée — le discriminant coûte une colonne aujourd'hui, une migration plus tard
    (DETTE-028). ⚠️ `participants_json` est **figé** à l'annonce : recalculer depuis le classement
    ferait changer les tireurs sous les pieds du juge. ⚠️ Le **verdict n'est pas stocké**, il se
    recalcule des tirs — c'est ce qui rend une flèche mal saisie corrigeable.
    """

    __tablename__ = "barrage"

    id: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — enfant direct du tournoi, à traiter
    # dans la politique de suppression du tournoi (non tranchée) ; ne pas contourner ici.
    # Portée sportive : le barrage départage une place dans le classement **d'un départ**
    # (E01US025, ADR-0075, migration 0042) — c'était `tournoi_id`.
    depart_id: Mapped[int] = mapped_column(ForeignKey("depart.id"), nullable=False)
    # DETTE-001 : FK sans ON DELETE CASCADE — lien latéral dans la descendance du tournoi.
    phase_id: Mapped[int | None] = mapped_column(ForeignKey("phase.id"), nullable=True)
    portee: Mapped[str] = mapped_column(nullable=False)
    reference: Mapped[str | None] = mapped_column(nullable=True)
    rang_dispute: Mapped[int | None] = mapped_column(nullable=True)
    participants_json: Mapped[str] = mapped_column(nullable=False)
    clos: Mapped[bool] = mapped_column(nullable=False, server_default=text("0"))
    cree_le: Mapped[datetime.datetime] = mapped_column(nullable=False)


class BarrageTirORM(Base):
    """Table `barrage_tir` — une flèche de barrage, manche par manche (E06US003).

    ⚠️ **`score` nul signifie ABSENT, pas « pas encore saisi »** — issue réglementaire (B.6.5.2.4).
    Une saisie en attente n'a **pas de ligne** ici, et confondre les deux ferait perdre quelqu'un
    qui n'a pas tiré. `distance_au_centre` est en **dixièmes de millimètre**, nulle quand la mesure
    n'a pas été faite : le domaine refuse alors de départager dessus et fait retirer.
    """

    __tablename__ = "barrage_tir"

    id: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-001 : FK sans ON DELETE CASCADE — enfant du barrage, purgé avec lui par le repository.
    barrage_id: Mapped[int] = mapped_column(ForeignKey("barrage.id"), nullable=False)
    manche: Mapped[int] = mapped_column(nullable=False)
    # DETTE-001 : enfant **indirect** via `archer`, comme `forfait.archer_id`. FK *enforced* : la
    # cascade applicative de `ArcherRepositorySQL.supprimer`/`fusionner` la traite explicitement,
    # sans quoi l'archer devient indéracinable (500).
    archer_id: Mapped[int] = mapped_column(ForeignKey("archer.id"), nullable=False)
    score: Mapped[int | None] = mapped_column(nullable=True)
    distance_au_centre: Mapped[int | None] = mapped_column(nullable=True)

    __table_args__ = (UniqueConstraint("barrage_id", "manche", "archer_id", name="uq_barrage_tir"),)


class IdentiteVisuelleORM(Base):
    """Table `identite_tournoi` — l'identité visuelle d'un tournoi (E16US006, ADR-0097).

    **Une table à part, pas des colonnes sur `tournoi`** : les logos sont des blobs, que chaque
    `SELECT` de la ligne traînerait. `tournoi_id` est à la fois clé primaire et clé étrangère.
    ⚠️ Les accents sont **nullables** : `NULL` = « rien n'a été choisi », l'identité étant héritée
    du club — y semer un défaut ferait passer le tournoi pour *réglé*. Un emplacement de logo vide
    porte `NULL` **sur les deux colonnes**, appariement tenu par l'adapter.
    """

    __tablename__ = "identite_tournoi"

    # `ON DELETE CASCADE` : composant **strict** de l'agrégat tournoi (une ligne, sans descendance,
    # cosmétique), au même titre que `volee.serie_id` — et non la descendance non tranchée de
    # DETTE-001. Sans cela, la ligne d'identité — qui naît au premier réglage et n'est jamais
    # retirée — rendait le tournoi définitivement indéracinable (`PRAGMA foreign_keys=ON`).
    # Clé primaire **et** étrangère : au plus une identité par tournoi, tenu par le schéma.
    tournoi_id: Mapped[int] = mapped_column(
        ForeignKey("tournoi.id", ondelete="CASCADE"), primary_key=True
    )
    accent_primaire: Mapped[str | None] = mapped_column(nullable=True)
    accent_secondaire: Mapped[str | None] = mapped_column(nullable=True)
    # Chaque logo est un **triplet** (octets, type MIME, empreinte du contenu), écrit d'un seul
    # geste par l'adapter. L'empreinte est stockée et non recalculée : la projection des réglages
    # est faite colonne par colonne **sans charger un octet** (c'est la raison d'être de cette
    # table), et hacher pour connaître un numéro de version aurait annulé ce gain à chaque affichage
    # public. La route qui sert les octets la lit **seule** pour répondre 304 (`empreinte_du_logo`),
    # de sorte que la version servie et la version persistée sont la même valeur — un seul calcul,
    # au dépôt.
    logo_evenement: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    logo_evenement_type: Mapped[str | None] = mapped_column(nullable=True)
    logo_evenement_empreinte: Mapped[str | None] = mapped_column(nullable=True)
    logo_club: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    logo_club_type: Mapped[str | None] = mapped_column(nullable=True)
    logo_club_empreinte: Mapped[str | None] = mapped_column(nullable=True)
