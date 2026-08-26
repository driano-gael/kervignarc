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

    Un départ est un **créneau du tournoi** (`tournoi_id`), pas une propriété d'un archer : le lien
    archer↔départ (inscription, portant `paye`) est E02US009, table distincte à venir.
    `tarif_centimes` est un **INTEGER**, pas un REAL : l'argent se compte en centimes entiers
    (ADR-0012) ; il est **NOT NULL** (un créneau a toujours un prix, `0` = gratuit). `horaire`
    est l'horaire du créneau `HH:MM` (E02US010), **NOT NULL** : un créneau a toujours une heure
    depuis E02US010 (le libellé libre facultatif d'E02US004 est abandonné).
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


class FormatTournoiORM(Base):
    """Table `format_tournoi` — persistance de l'agrégat `FormatTournoi` (E01US023, ADR-0060 §5).

    **Aucune FK vers `tournoi`**, et ce n'est pas un oubli : un format n'existe qu'en bibliothèque
    (patrimoine du club). Sa « copie » dans un tournoi n'est pas une ligne de cette table, ce sont
    les lignes de `phase` produites par son application. La table n'appartient donc **pas** à la
    descendance de `tournoi` — supprimer un tournoi ne doit pas toucher aux formats, et DETTE-001
    ne la concerne pas (même régime que `club`).

    La **séquence de modèles de phases** est stockée dans `config` (JSON,
    `{"etapes": [{"ordre", "type", "policies"?, "validation"?, "source"?, "effectif"?}, …]}`) —
    même procédé que `PhaseORM.config`, dont elle reprend la forme étape par étape pour que les
    deux se relisent avec les mêmes fonctions. Une table fille coûterait une jointure pour une
    donnée toujours lue en bloc et jamais requêtée.

    `nom` est `UNIQUE` : c'est ce qui rend la **promotion** idempotente — promouvoir deux fois sous
    le même nom met à jour le format au lieu de créer un homonyme que l'organisateur ne saurait pas
    distinguer dans sa liste.
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
    # (en FFTA tout licencié en a un — ADR-0014). L'anomalie est signalée à l'écran, pas comblée
    # par un club sentinelle. La suppression d'un club référencé est refusée côté service
    # (409, `ClubReference`).
    #
    # **Hors périmètre de DETTE-001**, à la différence des autres FK de ce fichier : elle pointe
    # vers `club`, qui n'est PAS dans la descendance de `tournoi`. Supprimer un tournoi (donc ses
    # archers) ne la viole jamais — c'est le sens inverse qu'elle contraint, et ce cas-là est
    # tranché (refus 409), comme l'est déjà `categorie.blason_id`.
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
    # DETTE-042 : le terme métier est « couloir de tir » (ADR-0073) ; renommer cette colonne
    # demande une migration, faite avec DETTE-010 (E01US019) pour n'en écrire qu'une.
    position: Mapped[str] = mapped_column(nullable=False)


class PlacementTableauORM(Base):
    """Table `placement_tableau` — pose matérialisée d'un duelliste, par phase (E03US009, ADR-0048).

    Le **plan de duels**, distinct du plan de cibles de qualification (`placement`, par départ) :
    scoppé par **phase** de tableau. Une ligne = un duelliste **posé** sur une case ;
    **clé primaire composite** `(phase_id, inscription_id)` — au plus une case par inscription **et
    par phase** (un archer a une pose en qualif *et* une pose en tableau, dans deux tables). Un
    inscrit **sans** ligne est en réserve — l'absence *est* l'information (comme ADR-0024).

    L'**appariement** (qui affronte qui) n'est **pas** persisté : il est recalculé du classement à
    chaque régénération (déterministe, ADR-0023/0048). Seule la **pose** l'est, pour l'ajustement au
    glisser-déposer. **`ON DELETE CASCADE`** (donnée dérivée, feuille — exception DETTE-001,
    ADR-0024) sur `phase_id` **et** `inscription_id` : la pose disparaît avec la phase ou
    l'inscription."""

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

    Troisième table de placement, et la seule dont l'unité posée ne soit pas un archer. C'est tout
    le sujet d'[ADR-0083] §3 : **le tireur au repos change à chaque tour**. Une poule de 5 tient sur
    4 couloirs — la méthode du cercle ne fait tirer que `effectif ÷ 2` rencontres par tour, donc un
    membre se repose, mais jamais le même ; une ronde de système suisse ré-apparie tout le plateau,
    donc aucun de ses tireurs n'a de couloir attitré non plus. Persister « archer → couloir », comme
    le fait `placement_tableau` (keyé `(phase_id, inscription_id)`), écrirait dans les deux cas une
    information **fausse**, pas seulement incomplète.

    ⚠️ **Elle s'appelait `placement_poule` jusqu'à E05US026** (migration 0046), et la colonne
    `poule_numero` s'appelle désormais `groupe_numero`. Le renommage a été demandé par le
    commanditaire le 16/08/2026 plutôt que de laisser un système suisse ranger ses blocs dans une
    table qui dit « poule » — une table qui ment sur ce qu'elle contient est un écart à la règle 3,
    et le prochain lecteur y perd plus que ce que la migration coûte. C'est l'arbitrage inverse de
    `DETTE-042` (`position` / « couloir »), et pour une raison assumée : là-bas le mot juste ne
    changeait **rien** au contenu, ici le nom désignait le mauvais **concept**.

    Une ligne = **un couloir** attribué à un groupe. `rang` porte sa position dans le bloc (1-based)
    pour que la plage se relise dans l'ordre de remplissage : un bloc peut déborder d'une cible sur
    la suivante, et « cible 3 couloir C » ne dit pas à lui seul s'il vient avant ou après « cible 4
    couloir A » sur des salles à capacité variable.

    ⚠️ **La clé primaire est le couloir** (`phase_id, cible_index, position`), pas le groupe. Elle
    porte donc l'invariant qui compte en salle — *un couloir, un occupant* —, que la base fait
    respecter au lieu de le confier au seul service. `UNIQUE(phase_id, groupe_numero, rang)` tient
    l'autre bout : un bloc ne saute ni ne répète de position, et l'index sert la lecture « les
    couloirs du groupe *n* », qui est la requête de tous les appelants.

    Les couloirs de chaque **rencontre**, tour par tour, ne sont pas ici : ils sont **dérivés** à la
    lecture, comme l'appariement d'un tableau (ADR-0023/0048). Persister le bloc et dériver le
    détail est ce qui permet à l'organisateur de déplacer un groupe entier sans réécrire un plan de
    rencontres qui, lui, dépend du tour affiché.

    **`ON DELETE CASCADE`** sur `phase_id` (donnée dérivée d'une phase, feuille — même exception
    DETTE-001 que `placement_tableau` et `duel`) : le plan disparaît avec la phase.

    [ADR-0083]: ../../../docs/adr/0083-le-contrat-de-phase-jouable.md
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
    """Table `phase` — persistance de l'agrégat `Phase` (introduction minimale, E01US009/ADR-0011).

    `type` et `statut` stockent la **valeur** de leurs énumérations (`TypePhase`, `StatutPhase`).
    Les **politiques** de la phase sont sérialisées dans `config` (JSON) : depuis E05US003/ADR-0046,
    le barème de qualification dans `config.policies.scoring` (nommé « cumul » + paramètres), le
    grain de validation restant à la racine dans `config.validation` (E01US015, `D-11`, ce n'est pas
    une politique de moteur) ; la traduction JSON ↔ agrégat est faite par le repository. C'est le
    `config` JSON qui permet d'ajouter une politique **sans migration de schéma** (ADR-0011) : une
    ligne écrite avant E01US015 n'a pas de clé `validation` et se relit avec le preset de son type,
    et la relecture reste tolérante à l'ancienne forme à plat de `scoring` (repli `_lire_scoring`,
    la migration `0028` réécrivant les lignes existantes). `ordre` et `statut` sont conformes au
    modèle de données mais non exploités avant le moteur (EPIC-05).

    ⚠️ **La phase pend au `depart`, plus au `tournoi`** (E01US025, ADR-0075, migration 0042) : le
    départ est la **portée sportive** — il rejoue le tournoi en entier, donc il porte sa séquence,
    ses classements et ses tableaux. `ordre` est contigu 1..N **par départ**. Le lien au tournoi
    reste atteignable par jointure `phase → depart → tournoi`, et c'est ce que font les lectures
    transverses (supervision, complétude, suppression en cascade).
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
    **avancement** (`PhaseORM`, qui n'a plus que `depart_id`, `ordre` et `statut`). Avant le
    07/08/2026, appliquer un format écrivait N copies complètes — une par créneau —, libres de
    diverger en silence.

    `type` stocke la valeur de `TypePhase`. Les **politiques** vivent dans `config` (JSON), forme
    `config.policies` d'ADR-0046 : c'est ce qui permet d'ajouter une politique **sans migration de
    schéma** (ADR-0011). La traduction JSON ↔ agrégat est faite par le repository, à l'identique de
    ce que faisait `PhaseORM` — le format de la `config` n'a pas changé, il a **changé de table**.
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
    """Table `franchissement_arret` — ce qu'un **arrêt programmé** a coupé (E05US033, [ADR-0091]).

    ⚠️ **Cette table ne porte pas les arrêts eux-mêmes**, et la séparation est le cœur de l'ADR. La
    *définition* d'un arrêt (« après le tour 3, portée départ ») vit dans `deroule_etape.config`, en
    JSON, donc **sans migration de schéma** (ADR-0046) : c'est du déroulé, défini une fois par
    tournoi et rejoué par chaque créneau (ADR-0076). Ici ne vit que l'**avancement** : cet arrêt-là
    a-t-il coupé, dans ce créneau-ci, et l'admin l'a-t-il relevé.

    C'est le **seul état persisté** du mécanisme — tout le reste de l'avancement étant recalculé à
    la lecture (ADR-0090 §5) — et il faut dire pourquoi celui-ci fait exception : la condition de
    déclenchement est **monotone**. Une fois le tour 2 achevé, « le tour 2 est achevé et un arrêt
    est posé après le tour 2 » reste vrai indéfiniment ; un déclencheur qui la relirait sans mémoire
    remettrait la phase en pause à chaque reprise, et l'organisateur perdrait la main
    définitivement.

    `phase_id` est la phase **déclenchante**, et `apres_tour` désigne l'arrêt dans la définition de
    son étape : le couple porte donc l'unicité. `phases_arretees` est un tableau JSON d'identifiants
    de phases — celles que cet arrêt a effectivement mises en pause, et donc celles que le geste de
    relance rendra. Les déduire à la reprise (« toutes les phases en pause du créneau ») relancerait
    aussi une phase suspendue à la main pour une autre raison.

    `tours_a_finir` est la photo, prise à l'armement d'un arrêt de portée **départ**, du tour que
    chaque autre phase avait en cours — c'est ce qui permet à chacune de *finir son tour* avant de
    s'arrêter (arbitrage du commanditaire, 18/08/2026).

    [ADR-0091]: ../../../docs/adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md
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
    """Table `arret_de_circonstance` — une pause décidée **le jour J** (E05US034, [ADR-0092]).

    ⚠️ **Troisième rangement du mécanisme, et la frontière est celle d'ADR-0076.** Un arrêt posé à
    l'atelier est de la *composition* : il vit dans `deroule_etape.config`, en JSON, et **tous les
    créneaux du tournoi le rejouent** (§4). Un arrêt posé pendant que la salle tire est de la
    *conduite* : il vit ici, il porte un `depart_id`, et **personne ne le rejoue** (§5). Les ranger
    ensemble ferait s'arrêter le créneau de l'après-midi pour une panne de chauffage du matin.

    ⚠️ **Une table plutôt qu'une colonne JSON sur `depart`**, contrairement au parti pris pour la
    définition. Deux raisons, et la seconde est la vraie : l'unicité `(depart_id, phase_id,
    apres_tour)` doit être tenue par le schéma — la pose est concurrente, ~30 tablettes valident
    pendant que l'organisateur clique — et un document JSON ne sait pas la tenir. Le volume est le
    même dans les deux cas (quelques lignes par créneau), donc ce n'est pas lui qui tranche.

    `portee` reprend `PorteeArret` : cette phase seule, ou tout ce qui tire dans le créneau.

    [ADR-0092]: ../../../docs/adr/0092-un-arret-pose-le-jour-j-appartient-au-creneau.md
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
    """Table `poste` — persistance de l'agrégat `Poste` (E04US001, ADR-0029 ; E07US004, ADR-0064).

    Credential d'un **lieu** d'un tournoi, plus le `code` imprimé sous le QR. `code` est `UNIQUE`
    **global** (pas par tournoi) : le rattachement se fait par le seul code, qui doit désigner un
    lieu sans ambiguïté d'un tournoi à l'autre. Le service stocke le code déjà canonique
    (`normaliser_code`).

    Deux natures depuis E07US004 (`type`) — **une seule table**, parce que le credential, le jeton,
    le heartbeat et la supervision sont rigoureusement les mêmes des deux côtés (le CA : *« c'est un
    poste, comme une tablette de cible — donc rien de neuf à inventer »*) :

    - `cible` : `cible_index` renseigné, `libelle` nul ;
    - `ecran` : `libelle` renseigné, `cible_index` nul.

    ⚠️ `cible_index` devient donc **nullable**, ce qui **affaiblit** `uq_poste_tournoi_cible` :
    SQLite considère chaque `NULL` comme distinct, donc plusieurs écrans coexistent sans heurter la
    contrainte — c'est exactement le CA (« plusieurs écrans possibles »). En contrepartie, la
    contrainte ne protège plus « une seule cible N par tournoi » que pour les lignes de type
    `cible`, ce qui est le seul cas où elle avait un sens. L'exclusivité `cible_index` ↔ `libelle`
    est portée par le domaine (`Poste.creer` / `creer_ecran`), pas par un `CHECK` : la base du
    projet n'en utilise nulle part, et un `CHECK` ajouté ici serait la seule règle métier vivant
    hors du domaine (règle 2).

    `deroule_json` porte la `SequenceVues` d'un écran, sérialisée comme `phase.sources_json`
    (migration 0036) : un tableau JSON `[{"vue": …, "cadence_s": …}]`. Nul pour une cible, et nul
    aussi pour un écran qui n'a rien réglé — il joue alors `SequenceVues.par_defaut()`, ce que le CA
    appelle le « déroulé par défaut ».
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

    __table_args__ = (UniqueConstraint("tournoi_id", "cible_index", name="uq_poste_tournoi_cible"),)


class SerieORM(Base):
    """Table `serie` — racine de persistance de l'agrégat `Serie` (saisie de qualif, E04US002).

    **Une série par `(phase, archer)`** (`UNIQUE(phase_id, archer_id)`, cf. port `SerieRepository`)
    :
    la grille de saisie d'un archer **dans une** phase de qualification — un déroulé peut en compter
    plusieurs (E05US025, ADR-0082). La série ne porte pas ses volées en
    colonne — elles vivent dans la table enfant `volee` (une ligne par volée), reliée par
    `serie_id`. Le **cumul** n'est pas stocké : il se recalcule des volées validées (`Serie.cumul`),
    seul l'état saisi est persisté.

    Deux FK **sans `ON DELETE`** = DETTE-001 : la série est de la donnée **saisie** (les scores),
    dans la descendance du tournoi via `archer` **et** `tournoi` — sa purge relève de la politique
    de suppression du tournoi, non tranchée. La cascade `archer` → `serie` est réalisée
    **applicativement** par `ArcherRepositorySQL.supprimer` (cascade maîtrisée, cf. `score`).
    """

    __tablename__ = "serie"
    # UNIQUE(phase_id, archer_id) : une feuille par archer **et par phase** (E05US025, ADR-0082).
    # Nommée comme dans la migration `0044` — présente ici, dans le `Base.metadata` cible de
    # l'autogénération, sinon un futur `--autogenerate` émettrait un `drop_constraint` fantôme et
    # retirerait le garde-fou.
    #
    # DETTE-046 **résorbée** ici. Le registre signalait une unicité au tournoi devenue fausse depuis
    # ADR-0075 — un archer inscrit sur deux créneaux n'avait qu'un seul emplacement pour ses
    # flèches,
    # la seconde série écrasant la première — et proposait `UNIQUE(depart_id, archer_id)`. La phase
    # **subsume** le départ (elle lui appartient), donc descendre la clé jusqu'à la phase règle le
    # cas de DETTE-046 *et* celui des qualifications multiples, avec **un** champ au lieu de deux
    # qui
    # diraient la même chose à deux mailles.
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

    Une ligne = une volée saisie : son `numero` (rang dans le barème), ses `valeurs` (les zones de
    score, stockées en **JSON** comme `BlasonORM.zones` — même procédé : petite liste toujours lue
    en bloc, jamais requêtée), et les marqueurs déclaratifs `saisie_par` / `validee_par`
    (`NULL` = non renseigné ; `validee_par` non `NULL` **est** le verrou, cf. `domain.serie.Volee`).

    `created_at` porte le **« quand »** de la saisie (ex-017, « volée 7 saisie par DURAND, 10h42 »):
    **métadonnée de persistance, hors du domaine `Volee`** (arbitrage de revue — réversible si un
    besoin domaine émergeait), comme l'`id`. Posé par le repository (port `Horloge`, UTC), et
    **préservé par numéro** à travers le purge + réinsertion : réécrire une série ne réinitialise
    pas le « quand » de ses volées déjà saisies. Le `server_default CURRENT_TIMESTAMP` n'est qu'un
    filet (SQLite exige un défaut pour un `NOT NULL` ajouté ; l'application le renseigne toujours) —
    relu, il redevient *aware* comme l'`horodatage` d'audit (SQLite stocke sans fuseau).

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
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class DuelORM(Base):
    """Table `duel` — le **tir** d'un match du tableau (saisie en duels, E04US013, ADR-0049).

    Une ligne = le résultat d'un match, keyé **`(phase_id, match_numero)`** (clé primaire composite,
    comme `placement_tableau`). On persiste le **tir** — `manches` (JSON, la liste des sets, deux
    volées de `ZoneScore` par manche), l'éventuel `barrage` (JSON, une flèche par camp + le gagnant
    désigné au plus près du centre), `validee_par` (le scoreur ; `NULL` = non validé) — **et
    l'identité des deux duellistes** (`haut_genre`/`haut_ref`, `bas_genre`/`bas_ref`). Elle
    n'est **pas** l'appariement *plan* (qui reste recalculé du classement, ADR-0048) : c'est le fait
    historique « **qui** a tiré ce résultat ». Elle **ancre** le tir contre une identité stable au
    lieu de la seule **position** `match_numero` : à la reconstruction, si les occupants recalculés
    du match divergent des duellistes enregistrés (le classement a changé après le tir), la
    divergence est **détectée** — jamais un score ré-attribué en silence à d'autres (ADR-0049
    §4). Le **barème** reste dérivé de l'arme (re-résolu à la lecture) : à participants identiques,
    même arme, même barème.

    **`ON DELETE CASCADE`** sur `phase_id` (donnée dérivée d'une phase, feuille — même exception que
    `placement_tableau`) : le tir disparaît avec la phase. Le `match_numero` n'est pas une FK (le
    tableau n'est pas persisté — il n'y a pas de table `match`) ; `*_ref` non plus (l'archer peut
    précéder ou non selon le genre, ADR-0028 — MVP : toujours un `archer_id`)."""

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


class ForfaitORM(Base):
    """Table `forfait` — persistance de l'agrégat `Forfait` (abandon / DSQ, E04US015, ADR-0050).

    Un forfait par **`(tournoi, archer, phase)`** (`UNIQUE`) : un archer ne se déclare qu'une fois
    forfait dans une phase donnée. `nature` stocke la **valeur** de l'énumération `NatureForfait`
    (`abandon` / `disqualification`) ; la traduction chaîne ↔ enum est faite par le repository,
    comme `action`/`ActionAuditee`. `declare_par` est le **nom** du déclarant (pas une FK) : la
    déclaration survit à la suppression du scoreur (E10US003), comme l'auteur d'audit. `motif` est
    **nullable** (facultatif). L'annulation (réversibilité, `D-15`) **supprime** la ligne — les
    flèches (`serie`/`volee`) ne sont jamais touchées.

    **`ON DELETE CASCADE`** sur `phase_id` (donnée dérivée d'une phase, feuille — même exception que
    `duel`/`placement_tableau`) : le forfait disparaît avec sa phase. Les FK `tournoi_id`/`archer`
    restent **sans `ON DELETE`** (DETTE-001, comme `serie`) : `tournoi_id` est stocké pour la
    lecture `par_tournoi` sans jointure. `archer_id` est purgé/réassigné par la **cascade
    applicative** de `ArcherRepositorySQL.supprimer`/`fusionner` — **exactement comme `serie`** (la
    FK est *enforced*, l'oublier bloque la suppression d'un archer forfaitaire ; revue adversariale
    E04US015). La purge liée au **tournoi** relève de la politique de suppression du tournoi, non
    tranchée.
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

    Née quand une **inscription payée disparaît** (départ supprimé, désinscription) : la ligne
    **survit** à cette disparition, elle en est la trace comptable. D'où l'absence de FK vers
    `inscription` ou `depart` — souvent détruits : on fige des **instantanés textuels**
    (`archer_prenom`, `archer_nom`, `creneau`) et le `montant_centimes` encaissé, comme
    `entree_audit`/`forfait` figent le **nom** de l'auteur plutôt qu'une FK (survie à la suppression
    du scoreur). Seul `tournoi_id` reste une FK — le registre appartient à son tournoi.

    `motif` et `statut` stockent la **valeur** des énumérations `MotifRemboursement` /
    `StatutRemboursement` (traduction chaîne ↔ enum côté repository, comme
    `action`/`ActionAuditee`).
    `cree_le` date l'ouverture ; `traite_le` est **nullable** (rempli au traitement
    remboursé/reporté).
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

    `portee` stocke la valeur de `PorteeBarrage` (qualification / poule / big_shoot_off). Les trois
    sont modélisées d'emblée bien qu'une seule soit câblée : le discriminant coûte une colonne
    aujourd'hui et une **migration de données** si on l'ajoutait plus tard (DETTE-028).

    `phase_id` et `reference` situent le barrage **dans** sa portée : la phase concernée, et le
    numéro de poule ou de manche pour les portées qui en ont une. Nuls en qualification, où le
    tournoi et le rang suffisent. `rang_dispute` est le rang partagé à éclater — **nul** pour un Big
    Shoot Off, dont l'égalité désigne un sortant plutôt qu'une place.

    `participants_json` fige la liste des tireurs (`[archer_id, …]`) à l'annonce. Même parti que
    `phase.sources_json` (migration 0036) et `poste.deroule_json` (0038) : du JSON dans une colonne
    texte pour une donnée toujours lue et écrite **en entier**, jamais ligne à ligne. Et surtout,
    elle est **figée** — la recalculer depuis le classement à chaque lecture ferait changer les
    tireurs sous les pieds du juge dès qu'une volée en retard est validée.

    ⚠️ **Le verdict n'est pas stocké**, il se recalcule depuis les tirs (`Barrage.resultat`). C'est
    ce qui rend une flèche mal saisie corrigeable : la corriger corrige le classement. Stocker
    l'ordre en plus des tirs créerait deux vérités, dont une périmée au premier correctif.
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

    Le grain est le **tir d'un participant à une manche**, ce qu'exige le CA (« persistance flèche
    par flèche ») et ce dont le moteur a besoin pour rejouer le verdict.

    ⚠️ **`score` nul signifie ABSENT, pas « pas encore saisi ».** C'est une issue réglementaire
    (B.6.5.2.4 : l'archer absent au barrage annoncé est déclaré perdant), et le domaine en avertit
    déjà (`TirBarrage`). Une saisie en attente n'a **pas de ligne** dans cette table — c'est ce qui
    distingue les deux, et confondre les deux ferait perdre quelqu'un qui n'a pas encore tiré.

    `distance_au_centre` est en **dixièmes de millimètre**, nulle quand la mesure n'a pas été faite.
    Une mesure absente n'est pas une distance nulle : le domaine refuse de départager dessus et fait
    retirer, ce qui est le cas le plus fréquent du jour J (le juge mesure la flèche litigieuse,
    rarement les deux).
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
    """Table `identite_tournoi` — l'identité visuelle d'un tournoi (E16US006, [ADR-0097]).

    **Une table à part, pas des colonnes sur `tournoi`.** Les deux logos sont des blobs ; posés sur
    `tournoi`, ils seraient traînés par chaque `SELECT` de la ligne — c'est-à-dire à l'ouverture de
    la liste des tournois, du tableau de bord et de toute lecture publique. Ici, la ligne d'identité
    n'est lue que par qui veut l'identité, et l'adapter sépare encore les **réglages** (quelques
    octets) des **octets d'un logo**, chacun sur sa requête.

    `tournoi_id` est **à la fois** clé primaire et clé étrangère : un tournoi a au plus une
    identité, et l'unicité est tenue par le schéma plutôt que par une garde applicative.

    Les accents sont **nullables** : `NULL` veut dire « rien n'a été choisi », et l'identité est
    alors héritée du club. Une ligne peut donc exister sans aucun accent — c'est le cas d'un
    tournoi dont on a seulement déposé le logo. Y semer un défaut le ferait passer pour *réglé*.
    Sinon, ils portent la forme normalisée `#rrggbb` (`domain.identite.Couleur.hex`) ; le type
    d'un logo stocke la **valeur** de `TypeLogo`, c'est-à-dire son type MIME. Un emplacement vide
    porte `NULL` **sur les deux colonnes** du couple — c'est l'adapter qui tient cet appariement,
    SQLite ne sachant pas exprimer « les deux ou aucune » sans `CHECK` (cf. commentaire du
    repository).
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
    # public. Elle sert aussi d'`ETag` sur la route qui sert les octets — un seul calcul, au dépôt.
    logo_evenement: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    logo_evenement_type: Mapped[str | None] = mapped_column(nullable=True)
    logo_evenement_empreinte: Mapped[str | None] = mapped_column(nullable=True)
    logo_club: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    logo_club_type: Mapped[str | None] = mapped_column(nullable=True)
    logo_club_empreinte: Mapped[str | None] = mapped_column(nullable=True)
