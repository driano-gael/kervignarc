"""0047 — la vue d'écran `tableaux` devient `en_cours` (E05US031).

## Pourquoi renommer une valeur qui marche

`VueEcran.TABLEAUX` désignait « les arbres de duels du tournoi ». E05US031 élargit cette vue aux
**trois formats sans arbre** — poules, système suisse, Big Shoot Off — qui n'atteignaient
jusqu'ici ni l'appli publique ni l'écran de salle. La vue ne montre donc plus un tableau : elle
montre **ce qui se joue**, quel que soit le format.

Deux issues étaient possibles :

- **garder la chaîne `tableaux`** et n'en changer que le libellé à l'écran : aucune migration, mais
  un réglage persisté qui dit « tableaux » sur un écran projetant une poule ;
- **renommer** : une migration, et le nom redevient vrai. **C'est l'option retenue.**

⚠️ **C'est l'arbitrage de la `0046`, appliqué au même critère** (`placement_poule` →
`placement_par_bloc`, E05US026). Le glossaire définit `Tableau` comme un « arbre de matchs à
élimination » : c'est le nom d'un **format**, pas d'un contenant. Laisser `vue = "tableaux"` sur une
ronde de système suisse ne serait pas un synonyme mal choisi — comme `position` pour « couloir de
tir », arbitrage inverse de `DETTE-042` — mais le **mauvais concept**. Un lecteur qui trouve
`"tableaux"` dans le déroulé d'un écran affichant des poules ne se demande pas si le mot est le bon,
il se demande ce qui a bien pu écrire ça.

## Ce que la migration fait

Le déroulé d'un écran est **sérialisé en JSON** dans `poste.deroule_json`, sous la forme
`[{"vue": "…", "cadence_s": …}]` (cf. `_depuis_sequence_vues`). Il n'y a donc ni colonne ni
contrainte à reconstruire : une substitution **ciblée sur la paire clé/valeur** suffit.

⚠️ **Ciblée, et non un `replace` sur `"tableaux"` seul** : la chaîne pourrait apparaître ailleurs
dans le document si le format évoluait (un libellé, une vue future). On substitue
`"vue": "tableaux"` — la seule occurrence qui désigne la valeur d'enum — ce qui rend l'opération
sûre même si `deroule_json` s'enrichit.

La **prise de contrôle** (`vue_figee`) n'est pas concernée : elle vit en mémoire et non en base
(ADR-0064 §3). Un écran piloté à la main au moment de la montée de version retombe sur son déroulé,
ce qui est le comportement normal d'un redémarrage.

## Descente

`downgrade` refait la substitution inverse, sans perte : le renommage est **réversible**, comme
celui de la `0046`. Un écran réglé après la montée sur une vue `en_cours` redescend sur `tableaux`
et reste lisible par le bundle d'avant — il montrera l'arbre seul, ce qu'il savait faire.
"""

from __future__ import annotations

from alembic import op

revision = "0047_vue_en_cours"
down_revision = "0046_placement_par_bloc"
branch_labels = None
depends_on = None

_ANCIEN = '"vue": "tableaux"'
_NOUVEAU = '"vue": "en_cours"'


def _substituer(depuis: str, vers: str) -> None:
    """Remplace une paire clé/valeur dans les déroulés d'écran persistés."""
    op.execute(
        # Pas d'entrée utilisateur : les deux bornes sont des littéraux de ce module.
        f"UPDATE poste "
        f"SET deroule_json = replace(deroule_json, '{depuis}', '{vers}') "
        f"WHERE deroule_json IS NOT NULL"
    )


def upgrade() -> None:
    """`tableaux` devient `en_cours` dans le déroulé de chaque écran réglé."""
    _substituer(_ANCIEN, _NOUVEAU)


def downgrade() -> None:
    """Chemin inverse, sans perte."""
    _substituer(_NOUVEAU, _ANCIEN)
