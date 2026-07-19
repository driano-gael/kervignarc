"""Modèles ORM SQLAlchemy — mapping des agrégats vers les tables (E00US009).

**Séparés du domaine** : le domaine ignore SQLAlchemy (ADR-0003). Un repository
(`repositories.py`) traduit dans les deux sens ORM ↔ agrégat de domaine. Ces classes
peuplent `Base.metadata`, cible des migrations Alembic.
"""

from __future__ import annotations

import datetime

from sqlalchemy import ForeignKey, UniqueConstraint
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


class DepartORM(Base):
    """Table `depart` — persistance de l'agrégat `Depart` (E02US004, ADR-0017).

    Un départ est un **créneau du tournoi** (`tournoi_id`), pas une propriété d'un archer : le lien
    archer↔départ (inscription, portant `paye`) est E02US009, table distincte à venir.
    `tarif_centimes` est un **INTEGER**, pas un REAL : l'argent se compte en centimes entiers
    (ADR-0012) ; il est **NOT NULL** (un créneau a toujours un prix, `0` = gratuit). `horaire`
    est un libellé de créneau facultatif.
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
    horaire: Mapped[str | None] = mapped_column(nullable=True)
    tarif_centimes: Mapped[int] = mapped_column(nullable=False)
    # Quota d'inscrits **facultatif** (E02US006) : NULL = créneau sans plafond. Le contrôle du
    # dépassement est applicatif (service), nulle contrainte SQL ne l'exprime (cf. `DepartComplet`).
    quota: Mapped[int | None] = mapped_column(nullable=True)


class ClubORM(Base):
    """Table `club` — persistance de l'agrégat `Club` (E02US001).

    **Aucune FK vers `tournoi`** : le référentiel est global et réutilisé d'une compétition à
    l'autre. La table n'appartient donc **pas** à la descendance de `tournoi` — supprimer un
    tournoi ne doit pas toucher aux clubs, et DETTE-001 ne la concerne pas.

    `nom` est `UNIQUE` : garde-fou d'intégrité, **exact** — il n'attrape que les homonymes au
    caractère près. Le refus fonctionnel du doublon (message et 409) est plus large et porté en
    amont par `ServiceClubs`, qui compare au sens de `domain.club.cle_nom` : espaces de bord,
    casse **et accents** repliés (« Élan de Fougères » ≡ « elan de fougeres »). Cet écart est
    assumé — SQL ne sait pas replier les accents sans colonne dénormalisée, et le writer unique
    (ADR-0005) garantit qu'aucune écriture ne contourne le service.
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
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — la politique de suppression d'un
    # tournoi non vide (cascade ou refus 409) n'est pas tranchée ; ne pas contourner ici.
    tournoi_id: Mapped[int] = mapped_column(ForeignKey("tournoi.id"), nullable=False)
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

    `taille` stocke la fraction de place occupée sur une cible (réel dans `]0, 1]`) et
    `capacite` le nombre d'archers admis (entier `>= 1`) ; la validation est portée par le
    domaine (`Blason.creer` / `Blason.modifier`).

    `zones` stocke les valeurs de score admises en **JSON** (`["10", "9", ..., "M"]`, même
    procédé que `GabaritSalleORM.config`) ; la traduction JSON ↔ tuple est faite par le
    repository. Une colonne dédiée par zone, ou une table fille, coûterait une jointure pour une
    donnée toujours lue en bloc et jamais requêtée.
    """

    __tablename__ = "blason"

    id: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — la politique de suppression d'un
    # tournoi non vide (cascade ou refus 409) n'est pas tranchée ; ne pas contourner ici.
    tournoi_id: Mapped[int] = mapped_column(ForeignKey("tournoi.id"), nullable=False)
    nom: Mapped[str] = mapped_column(nullable=False)
    taille: Mapped[float] = mapped_column(nullable=False)
    capacite: Mapped[int] = mapped_column(nullable=False)
    zones: Mapped[str] = mapped_column(nullable=False)


class GabaritSalleORM(Base):
    """Table `gabarit_salle` — persistance de l'agrégat `GabaritSalle` (E01US007, E01US008).

    Le plafond d'archers de chaque cible est stocké dans `config` (JSON, `{"capacites": [...]}`) ;
    `nb_cibles` est dénormalisé (= longueur de la liste) pour la lecture. La traduction JSON ↔
    agrégat est faite par le repository.

    `tournoi_id` distingue un **modèle** de bibliothèque (`NULL`, réutilisable) d'une **instance**
    appliquée à un tournoi (E01US008) : appliquer un modèle en crée une copie portant ce
    `tournoi_id`, ajustable sans altérer le modèle. Un tournoi porte au plus une instance.
    """

    __tablename__ = "gabarit_salle"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(nullable=False)
    nb_cibles: Mapped[int] = mapped_column(nullable=False)
    config: Mapped[str] = mapped_column(nullable=False)
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — l'instance appartient à la
    # descendance du tournoi, à traiter dans la même politique de suppression, non tranchée.
    tournoi_id: Mapped[int | None] = mapped_column(ForeignKey("tournoi.id"), nullable=True)


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
    # (en FFTA tout licencié en a un — ADR-0014). L'anomalie est signalée à l'écran, pas comblée
    # par un club sentinelle. La suppression d'un club référencé est refusée côté service
    # (409, `ClubReference`).
    #
    # **Hors périmètre de DETTE-001**, à la différence des autres FK de ce fichier : elle pointe
    # vers `club`, qui n'est PAS dans la descendance de `tournoi`. Supprimer un tournoi (donc ses
    # archers) ne la viole jamais — c'est le sens inverse qu'elle contraint, et ce cas-là est
    # tranché (refus 409), comme l'est déjà `categorie.blason_id`.
    club_id: Mapped[int | None] = mapped_column(ForeignKey("club.id"), nullable=True)


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

    Une ligne = un inscrit **posé** ; `inscription_id` en **clé primaire** (au plus une case par
    inscription). Un inscrit **sans** ligne est *en réserve* — l'absence de ligne *est*
    l'information, on ne persiste pas la réserve. `depart_id` est **dénormalisé** (dérivable de
    l'inscription) pour lire et réécrire le plan d'un départ sans jointure ; `position` porte la
    lettre A..D.

    **`ON DELETE CASCADE`**, à rebours de la convention DETTE-001 (« FK sans `ON DELETE`, purge
    applicative ») : `placement` est de la donnée **dérivée, reconstructible et feuille** (l'auto la
    régénère), pas de la donnée saisie remontant l'arbre du tournoi. Sa disparition suit
    automatiquement celle de l'inscription (désinscription, suppression d'archer/de départ) — cf.
    ADR-0024. Les FK sont **enforced** (`PRAGMA foreign_keys=ON`, `engine.py`).
    """

    __tablename__ = "placement"

    inscription_id: Mapped[int] = mapped_column(
        ForeignKey("inscription.id", ondelete="CASCADE"), primary_key=True
    )
    depart_id: Mapped[int] = mapped_column(
        ForeignKey("depart.id", ondelete="CASCADE"), nullable=False
    )
    cible_index: Mapped[int] = mapped_column(nullable=False)
    position: Mapped[str] = mapped_column(nullable=False)


class PhaseORM(Base):
    """Table `phase` — persistance de l'agrégat `Phase` (introduction minimale, E01US009/ADR-0011).

    `type` et `statut` stockent la **valeur** de leurs énumérations (`TypePhase`, `StatutPhase`).
    Les **politiques** de la phase sont sérialisées dans `config` (JSON) : le barème de
    qualification dans `config.scoring` (E01US009) et le grain de validation dans
    `config.validation` (E01US015, `D-11`) ; la traduction JSON ↔ agrégat est faite par le
    repository. C'est le `config` JSON qui permet d'ajouter une politique **sans migration**
    (ADR-0011) : une ligne écrite avant E01US015 n'a pas de clé `validation`, et se relit avec le
    preset de son type. `ordre` et `statut` sont conformes au modèle de données mais non exploités
    avant le moteur (EPIC-05).
    """

    __tablename__ = "phase"

    id: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — enfant direct du tournoi, à traiter
    # dans la même politique de suppression, non tranchée ; ne pas contourner ici.
    tournoi_id: Mapped[int] = mapped_column(ForeignKey("tournoi.id"), nullable=False)
    ordre: Mapped[int] = mapped_column(nullable=False)
    type: Mapped[str] = mapped_column(nullable=False)
    config: Mapped[str] = mapped_column(nullable=False)
    statut: Mapped[str] = mapped_column(nullable=False)


class ScoreurORM(Base):
    """Table `scoreur` — persistance de l'agrégat `Scoreur` (E10US003).

    Scoreur **du tournoi** (`tournoi_id`), comme `depart` : défini à la configuration,
    redéfinissable à tout moment (`D-14`). `code` est le code individuel remis au scoreur, `UNIQUE`
    **global** (pas par tournoi) : le scoreur ouvre sa session par son seul code, qui doit donc
    désigner un scoreur sans ambiguïté d'un tournoi à l'autre. L'unicité `UNIQUE` est **exacte** ;
    contrairement au nom de club, aucun repli d'accents n'est nécessaire — le service stocke déjà le
    code sous forme canonique (`normaliser_code` : majuscules), et le code n'a pas d'accent.
    """

    __tablename__ = "scoreur"

    id: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — enfant direct du tournoi, à traiter
    # dans la même politique de suppression, non tranchée ; ne pas contourner ici.
    tournoi_id: Mapped[int] = mapped_column(ForeignKey("tournoi.id"), nullable=False)
    nom: Mapped[str] = mapped_column(nullable=False)
    code: Mapped[str] = mapped_column(nullable=False, unique=True)


class PosteORM(Base):
    """Table `poste` — persistance de l'agrégat `Poste` (E04US001, ADR-0029).

    Credential d'une **cible** d'un tournoi : le couple `(tournoi_id, cible_index)` — `UNIQUE`, une
    seule cible N par tournoi — plus le `code` imprimé sous le QR. `code` est `UNIQUE` **global**
    (pas par tournoi) : le rattachement se fait par le seul code, qui doit désigner une cible sans
    ambiguïté d'un tournoi à l'autre. Le service stocke le code déjà canonique (`normaliser_code`).
    """

    __tablename__ = "poste"

    id: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — enfant direct du tournoi, à traiter
    # dans la même politique de suppression, non tranchée ; ne pas contourner ici.
    tournoi_id: Mapped[int] = mapped_column(ForeignKey("tournoi.id"), nullable=False)
    cible_index: Mapped[int] = mapped_column(nullable=False)
    code: Mapped[str] = mapped_column(nullable=False, unique=True)

    __table_args__ = (UniqueConstraint("tournoi_id", "cible_index", name="uq_poste_tournoi_cible"),)


class SerieORM(Base):
    """Table `serie` — racine de persistance de l'agrégat `Serie` (saisie de qualif, E04US002).

    **Une série par archer** (`UNIQUE(tournoi_id, archer_id)`, cf. port `SerieRepository`) : la
    grille de saisie d'un archer sur la phase de qualification. La série ne porte pas ses volées en
    colonne — elles vivent dans la table enfant `volee` (une ligne par volée), reliée par
    `serie_id`. Le **cumul** n'est pas stocké : il se recalcule des volées validées (`Serie.cumul`),
    seul l'état saisi est persisté.

    Deux FK **sans `ON DELETE`** = DETTE-001 : la série est de la donnée **saisie** (les scores),
    dans la descendance du tournoi via `archer` **et** `tournoi` — sa purge relève de la politique
    de suppression du tournoi, non tranchée. La cascade `archer` → `serie` est réalisée
    **applicativement** par `ArcherRepositorySQL.supprimer` (cascade maîtrisée, cf. `score`).
    """

    __tablename__ = "serie"
    # UNIQUE(tournoi_id, archer_id) : une seule série de qualification par archer. Nommée comme dans
    # la migration `0026` — présente ici, dans le `Base.metadata` cible de l'autogénération, sinon
    # un futur `--autogenerate` émettrait un `drop_constraint` fantôme et retirerait le garde-fou.
    __table_args__ = (UniqueConstraint("tournoi_id", "archer_id", name="uq_serie_tournoi_archer"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — enfant direct du tournoi, à traiter
    # dans la même politique de suppression, non tranchée ; ne pas contourner ici.
    tournoi_id: Mapped[int] = mapped_column(ForeignKey("tournoi.id"), nullable=False)
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — enfant indirect du tournoi via
    # `archer`. La cascade est **applicative et maîtrisée** (`ArcherRepositorySQL.supprimer`), à
    # l'image de `score.archer_id`/`inscription.archer_id` ; ne pas contourner ici.
    archer_id: Mapped[int] = mapped_column(ForeignKey("archer.id"), nullable=False)


class VoleeORM(Base):
    """Table `volee` — une volée d'une série (E04US002), table **enfant** de `serie`.

    Une ligne = une volée saisie : son `numero` (rang dans le barème), ses `valeurs` (les zones de
    score, stockées en **JSON** comme `BlasonORM.zones` — même procédé : petite liste toujours lue
    en bloc, jamais requêtée), et les marqueurs déclaratifs `saisie_par` / `validee_par`
    (`NULL` = non renseigné ; `validee_par` non `NULL` **est** le verrou, cf. `domain.serie.Volee`).

    **`ON DELETE CASCADE`** sur `serie_id`, à rebours de la convention DETTE-001 : une volée est un
    **composant strict** de l'agrégat `Serie` (value object interne), son cycle de vie est
    entièrement lié à sa série — pas de la donnée qui remonte l'arbre du tournoi de façon autonome.
    Sa disparition suit celle de la série (cf. `PlacementORM`, même exception assumée) ; les FK sont
    **enforced** (`PRAGMA foreign_keys=ON`, `engine.py`). En fonctionnement normal, le repository
    réécrit les volées d'une série par purge + réinsertion (patron `PlacementRepositorySQL`).
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


class EntreeAuditORM(Base):
    """Table `entree_audit` — persistance de l'agrégat `EntreeAudit` (journal d'audit, E10US005).

    Journal **du tournoi** (`tournoi_id`), en **ajout seul** : ni `enregistrer` ni `supprimer` côté
    repository (une trace ne se retouche pas). `action` stocke la **valeur** de l'énumération
    `ActionAuditee` (`validation` / `correction_score` / `forfait`) ; la traduction chaîne ↔ enum
    est faite par le repository, comme `statut`/`StatutTournoi`.

    `auteur` est le **nom** de qui a agi (pas une FK vers `scoreur`) : la trace survit à la
    suppression du scoreur (E10US003). `horodatage` porte le « quand » ; `avant`/`apres` sont
    **nullables** (une validation n'a pas d'état antérieur, une correction si).
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
