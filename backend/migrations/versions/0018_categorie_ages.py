"""categorie : remplace `tranche_age` (scalaire) par `ages` (tableau JSON de tranches)

Revision ID: 0018_categorie_ages
Revises: 0017_inscription
Create Date: 2026-07-16

E01US013 (ADR-0019). Une catégorie couvre **une ou plusieurs** tranches d'âge : la colonne scalaire
`tranche_age` devient `ages`, un **tableau JSON** de codes de tranche (ex. `["U15","U18"]`). Le
scalaire rendait les regroupements de classement de l'arc nu indistinguables (« U18 » = U15+U18,
« Scratch » = U21..S3, `docs/referentiel-ffta.md` §3) — c'est le défaut que cette US corrige.

**Migration des données (pas seulement du schéma).** Contrairement aux revisions voisines (0016),
on ne peut pas se contenter de recréer une colonne vide : une reconstruction naïve `"U18"` →
`["U18"]` ré-introduirait le bug pour l'arc nu. On reconstruit donc `ages` depuis le couple
`(arme, tranche_age)` :

- `("Arc Nu", "U18")` → `["U15","U18"]` ; `tranche_age == "Scratch"` → `["U21","S1","S2","S3"]` ;
- une tranche des huit valeurs FFTA → `[tranche]` ;
- vide, ou texte libre non reconnu (ex. « senior » d'une catégorie créée à la main avant le
  vocabulaire fermé) → `[]` : la catégorie garde son libellé, perd la contrainte d'âge qui n'était
  déjà pas exploitable.

Le `downgrade` restaure `tranche_age` en **meilleur effort** (première tranche de `ages`, sinon
NULL) : le regroupement arc nu n'est pas restituable dans un scalaire — c'est précisément pourquoi
on l'abandonne.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_categorie_ages"
down_revision: str | None = "0017_inscription"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TRANCHES_VALIDES = frozenset({"U11", "U13", "U15", "U18", "U21", "S1", "S2", "S3"})

_categorie = sa.table(
    "categorie",
    sa.column("id", sa.Integer),
    sa.column("arme", sa.String),
    sa.column("tranche_age", sa.String),
    sa.column("ages", sa.String),
)


def _ages_json(arme: str | None, tranche: str | None) -> str:
    """Reconstruit le tableau JSON `ages` depuis l'ancien couple `(arme, tranche_age)`."""
    tranche = (tranche or "").strip()
    if not tranche:
        return "[]"
    if tranche == "Scratch":
        return json.dumps(["U21", "S1", "S2", "S3"])
    if tranche == "U18" and (arme or "").strip() == "Arc Nu":
        return json.dumps(["U15", "U18"])
    if tranche in _TRANCHES_VALIDES:
        return json.dumps([tranche])
    return "[]"


def upgrade() -> None:
    """Ajoute `ages`, reconstruit les valeurs, passe la colonne NOT NULL et retire `tranche_age`."""
    connexion = op.get_bind()
    op.add_column("categorie", sa.Column("ages", sa.String(), nullable=True))
    lignes = connexion.execute(
        sa.select(_categorie.c.id, _categorie.c.arme, _categorie.c.tranche_age)
    ).all()
    for identifiant, arme, tranche in lignes:
        connexion.execute(
            _categorie.update()
            .where(_categorie.c.id == identifiant)
            .values(ages=_ages_json(arme, tranche))
        )
    with op.batch_alter_table("categorie") as batch:
        batch.alter_column("ages", existing_type=sa.String(), nullable=False)
        batch.drop_column("tranche_age")


def downgrade() -> None:
    """Recrée `tranche_age` (meilleur effort : 1re tranche de `ages`) puis retire `ages`."""
    connexion = op.get_bind()
    op.add_column("categorie", sa.Column("tranche_age", sa.String(), nullable=True))
    lignes = connexion.execute(sa.select(_categorie.c.id, _categorie.c.ages)).all()
    for identifiant, ages_json in lignes:
        try:
            tranches = json.loads(ages_json)
        except (json.JSONDecodeError, TypeError):
            tranches = []
        premiere = tranches[0] if tranches else None
        connexion.execute(
            _categorie.update().where(_categorie.c.id == identifiant).values(tranche_age=premiere)
        )
    with op.batch_alter_table("categorie") as batch:
        batch.drop_column("ages")
