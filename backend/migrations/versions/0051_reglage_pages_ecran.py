"""0051 — le réglage des pages projetées d'un écran de salle (E16US009).

## Deux colonnes plutôt qu'un troisième JSON

`poste.deroule_json` sérialise une **liste ordonnée de longueur libre** — c'est ce qui justifiait le
JSON (migration 0038, comme `phase.sources_json` en 0036). Le réglage de pages, lui, est un couple
de deux entiers scalaires dont le nombre ne bougera pas : deux colonnes se lisent, s'indexent et se
contraignent, là où un JSON n'apporterait que la souplesse dont on n'a pas besoin. Le registre de
dette porte déjà le prix de cette souplesse ailleurs (`DETTE-039` sur le front, `DETTE-023` sur le
JSON d'étape) ; on ne l'ajoute pas ici.

## Aucune donnée écrite, et c'est ce qui rend la migration sûre

Les deux colonnes sont **nulles** pour tout écran existant. Nul signifie « rien réglé », et un écran
qui n'a rien réglé joue `ReglagePages.par_defaut()` — dont les valeurs (40 noms, 20 s) sont
**exactement** celles que le front tenait en dur avant cette US (`DETTE-039` :
`NOMS_PAR_PAGE = 40`, `SECONDES_PAR_PAGE = 20`). Aucun écran déjà installé ne change donc de
comportement au déploiement, et la migration n'a rien à peupler. Semer les valeurs par défaut aurait
au contraire rendu indiscernable « l'organisateur a mesuré et choisi 40 » de « il n'a rien choisi »
— même parti qu'en 0050 pour les accents hérités.

Nulles pour une **cible**, aussi : une tablette ne projette rien. L'exclusivité est portée par le
domaine (`Poste.avec_pages`, `pages_effectives`), pas par un `CHECK` — comme l'exclusivité
`cible_index` ↔ `libelle` de 0038, et pour la même raison (la base du projet n'utilise aucun
`CHECK`, et une règle métier ne vit pas hors du domaine, règle 1).

## Les deux colonnes vont par paire

Elles sont écrites ensemble (`ReglagePages` est un value object indivisible) et le repository
**refuse** une paire incomplète plutôt que de compléter en silence avec la moitié du défaut. Le
schéma ne l'impose pas ; le lecteur, si — un écran qui projetterait 40 noms toutes les 5 s sans que
personne ne l'ait demandé serait indétectable depuis la salle.

## Descente

`downgrade` supprime les deux colonnes, donc les réglages posés. La perte est **totale sur cette
donnée et sans recours**, mais elle est purement ergonomique : les écrans redescendus reprennent les
40 noms / 20 s d'avant l'US, c'est-à-dire le comportement que le dépôt a eu pendant tout le reste de
son histoire. Aucune règle sportive, aucun classement, aucune garde de cycle de vie n'en dépend.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0051_reglage_pages_ecran"
down_revision = "0050_identite_visuelle_tournoi"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Ajoute les deux colonnes, nulles partout (cf. en-tête : aucune donnée à reprendre)."""
    with op.batch_alter_table("poste") as batch:
        batch.add_column(sa.Column("noms_par_page", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("cadence_page_s", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("poste") as batch:
        batch.drop_column("cadence_page_s")
        batch.drop_column("noms_par_page")
