"""Modèles ORM SQLAlchemy — mapping des agrégats vers les tables (E00US009).

**Séparés du domaine** : le domaine ignore SQLAlchemy (ADR-0003). Un repository
(`repositories.py`) traduit dans les deux sens ORM ↔ agrégat de domaine. Ces classes
peuplent `Base.metadata`, cible des migrations Alembic.
"""

from __future__ import annotations

import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base


class TournoiORM(Base):
    """Table `tournoi` — persistance de l'agrégat `Tournoi`.

    `type_tournoi` et `statut` stockent la **valeur** de leurs énumérations respectives
    (`TypeTournoi`, `StatutTournoi`) ; la traduction chaîne ↔ enum est faite par le repository.

    `tarif_depart_centimes` est un **INTEGER**, pas un REAL : l'argent se compte en centimes
    entiers (E01US010). `NULL` signifie « tarif non défini », distinct de `0` (gratuit).
    """

    __tablename__ = "tournoi"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(nullable=False)
    date: Mapped[datetime.date] = mapped_column(nullable=False)
    lieu: Mapped[str | None] = mapped_column(nullable=True)
    type_tournoi: Mapped[str] = mapped_column(nullable=False)
    statut: Mapped[str] = mapped_column(nullable=False)
    tarif_depart_centimes: Mapped[int | None] = mapped_column(nullable=True)


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
    tranche_age: Mapped[str | None] = mapped_column(nullable=True)
    sexe: Mapped[str | None] = mapped_column(nullable=True)
    # Blason par défaut, facultatif (E01US006). La suppression d'un blason référencé est refusée
    # côté service (409, `BlasonReference`).
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — lien latéral au sein de la
    # descendance du tournoi, à traiter dans la même politique de suppression, non tranchée.
    blason_id: Mapped[int | None] = mapped_column(ForeignKey("blason.id"), nullable=True)


class BlasonORM(Base):
    """Table `blason` — persistance de l'agrégat `Blason` (E01US005).

    `taille` stocke la fraction de place occupée sur une cible (réel dans `]0, 1]`) et
    `capacite` le nombre d'archers admis (entier `>= 1`) ; la validation est portée par le
    domaine (`Blason.creer` / `Blason.modifier`).
    """

    __tablename__ = "blason"

    id: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — la politique de suppression d'un
    # tournoi non vide (cascade ou refus 409) n'est pas tranchée ; ne pas contourner ici.
    tournoi_id: Mapped[int] = mapped_column(ForeignKey("tournoi.id"), nullable=False)
    nom: Mapped[str] = mapped_column(nullable=False)
    taille: Mapped[float] = mapped_column(nullable=False)
    capacite: Mapped[int] = mapped_column(nullable=False)


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
    """Table `archer` — persistance de l'agrégat `Archer` (E00US011, club en E02US001)."""

    __tablename__ = "archer"

    id: Mapped[int] = mapped_column(primary_key=True)
    # DETTE-001 (docs/dette.md) : FK sans ON DELETE CASCADE — la politique de suppression d'un
    # tournoi non vide (cascade ou refus 409) n'est pas tranchée ; ne pas contourner ici.
    tournoi_id: Mapped[int] = mapped_column(ForeignKey("tournoi.id"), nullable=False)
    nom: Mapped[str] = mapped_column(nullable=False)
    cible: Mapped[int | None] = mapped_column(nullable=True)
    # Club de rattachement, facultatif (E02US001) ; E02US002 le rendra obligatoire. La suppression
    # d'un club référencé est refusée côté service (409, `ClubReference`).
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
