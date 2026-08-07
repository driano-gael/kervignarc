"""le déroulé se définit une fois : `deroule_etape` naît, `phase` ne garde que l'avancement

Revision ID: 0043_deroule_defini_une_fois
Revises: 0042_portee_sportive_depart
Create Date: 2026-08-07

[ADR-0076] sépare la **définition** d'une étape (portée par le tournoi) de son **avancement**
(porté par chaque départ). La `0042` avait fait pendre `phase` au départ ; elle laissait chaque
créneau porter une **copie complète** de la définition — barème, grain, prélèvements, profondeur —
libres de diverger en silence.

Après cette migration :

- **`deroule_etape`** (neuve) porte `tournoi_id`, `ordre`, `type`, `config` : la définition, **une
  seule fois** par tournoi ;
- **`phase`** ne garde que `depart_id`, `ordre`, `statut` : où en est ce créneau de cette étape.

`phase.id` est **conservé** — c'est ce qui permet aux artefacts d'exécution (`forfait.phase_id`,
`placement_tableau.phase_id`, `duel.phase_id`, `barrage.phase_id`) de ne pas bouger d'une ligne.

## Reprise des données

La définition est reprise depuis les phases du **premier départ** de chaque tournoi (numéro le
plus bas, comme la `0042`). Les copies des autres créneaux sont **perdues si elles avaient
divergé** — c'est le sens même de la décision (elles n'auraient pas dû pouvoir diverger), mais
c'est une perte réelle, et il faut la dire plutôt que la laisser découvrir.

En pratique le risque est nul sur les bases existantes : la `0042` datant de la veille, aucune
divergence n'a eu le temps de naître.

⚠️ **Deux cas de bord traités explicitement** :

1. une phase dont le tournoi n'a **aucun** départ ne peut pas exister (la `0042` en aurait
   créé un) ;
2. une phase à la `config` illisible n'est **pas** silencieusement écartée : elle est reprise telle
   quelle dans `deroule_etape`, et c'est le repository qui la refusera en `InfrastructureError` à la
   relecture — même comportement qu'avant, au même endroit. Une migration n'est pas le lieu où l'on
   décide qu'une donnée est valide.

## Downgrade

La définition est **redistribuée** dans chaque phase de chaque créneau du tournoi. On retrouve donc
exactement l'état de la `0042` — N copies identiques. Les phases d'un départ dont le tournoi n'a
plus d'étape (cas impossible en pratique) sont supprimées faute de `config` à écrire, `phase.config`
étant `NOT NULL`.

⚠️ **« Réversible » tout court était faux**, et la revue l'a relevé : ce `downgrade`-ci fait bien
son travail, mais l'aller-retour complet `upgrade → downgrade → upgrade` **échouait** — la `0042`
rebranchait les N copies de créneau sur le tournoi, et l'`INSERT … SELECT` ci-dessous doublonnait
alors `(tournoi, ordre)`, laissant la base bloquée à mi-migration. Le correctif est dans la `0042`
(`_replier_les_copies_de_creneau`), qui ne remonte que les phases du premier créneau ;
l'aller-retour est désormais éprouvé par
`tests/test_migration_0042_0043_portee_et_deroule.py`. Une annonce de réversibilité que rien ne
teste est une **promesse**, pas une propriété.

[ADR-0076]: ../../../docs/adr/0076-un-deroule-defini-une-fois-un-avancement-par-depart.md
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0043_deroule_defini_une_fois"
down_revision = "0042_portee_sportive_depart"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connexion = op.get_bind()

    op.create_table(
        "deroule_etape",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tournoi_id", sa.Integer(), sa.ForeignKey("tournoi.id"), nullable=False),
        sa.Column("ordre", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("config", sa.String(), nullable=False),
        sa.UniqueConstraint("tournoi_id", "ordre", name="uq_deroule_tournoi_ordre"),
    )

    # La définition vient des phases du **premier créneau** de chaque tournoi. `MIN(depart.numero)`
    # choisit le même départ que la `0042`, pour que les deux migrations racontent la même histoire.
    connexion.execute(
        sa.text(
            "INSERT INTO deroule_etape (tournoi_id, ordre, type, config) "
            "SELECT d.tournoi_id, p.ordre, p.type, p.config "
            "FROM phase AS p "
            "JOIN depart AS d ON d.id = p.depart_id "
            "WHERE d.numero = ("
            "    SELECT MIN(d2.numero) FROM depart AS d2 WHERE d2.tournoi_id = d.tournoi_id"
            ")"
        )
    )

    with op.batch_alter_table("phase") as batch:
        batch.drop_column("type")
        batch.drop_column("config")
        batch.create_unique_constraint("uq_phase_depart_ordre", ["depart_id", "ordre"])


def downgrade() -> None:
    connexion = op.get_bind()

    with op.batch_alter_table("phase") as batch:
        batch.drop_constraint("uq_phase_depart_ordre", type_="unique")
        batch.add_column(sa.Column("type", sa.String(), nullable=True))
        batch.add_column(sa.Column("config", sa.String(), nullable=True))

    # Redistribution : chaque phase reprend la définition de l'étape de même rang, dans le tournoi
    # de son créneau. C'est l'inverse exact de la reprise ci-dessus.
    connexion.execute(
        sa.text(
            "UPDATE phase SET "
            "  type = (SELECT e.type FROM deroule_etape AS e "
            "          JOIN depart AS d ON d.id = phase.depart_id "
            "          WHERE e.tournoi_id = d.tournoi_id AND e.ordre = phase.ordre), "
            "  config = (SELECT e.config FROM deroule_etape AS e "
            "            JOIN depart AS d ON d.id = phase.depart_id "
            "            WHERE e.tournoi_id = d.tournoi_id AND e.ordre = phase.ordre)"
        )
    )
    connexion.execute(sa.text("DELETE FROM phase WHERE type IS NULL OR config IS NULL"))

    with op.batch_alter_table("phase") as batch:
        batch.alter_column("type", existing_type=sa.String(), nullable=False)
        batch.alter_column("config", existing_type=sa.String(), nullable=False)

    op.drop_table("deroule_etape")
