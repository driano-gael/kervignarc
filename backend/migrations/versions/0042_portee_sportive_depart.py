"""le départ devient la portée sportive : phase et barrage changent de parent — E01US025

Revision ID: 0042_portee_sportive_depart
Revises: 0041_cloisonnement_cible
Create Date: 2026-08-06

[ADR-0075] rétablit ce qu'[ADR-0017] avait décidé treize mois plus tôt sans que le moteur le porte :
un départ **rejoue le tournoi en entier**, donc il a sa séquence de phases, ses classements et ses
tableaux. `PHASE.tournoi_id` devient `PHASE.depart_id`, et `BARRAGE.tournoi_id` devient
`BARRAGE.depart_id` (un barrage départage une place *dans un classement*, donc dans un créneau).

**Aucune colonne `tournoi_id` n'est conservée à côté.** Deux portées coexistantes obligeraient
chaque lecture à choisir laquelle honorer, et la première qui se tromperait rétablirait le bug en
silence (ADR-0075, « ce qui a été écarté »). Le tournoi reste atteignable par
`phase → depart → tournoi`.

## Reprise des données existantes — trois cas, tous traités explicitement

1. **Tournoi mono-départ** (le cas courant) : son unique créneau reçoit la séquence. Aucune perte,
   aucun changement de comportement — c'est le cas où les deux portées se confondaient, et c'est
   d'ailleurs pourquoi le défaut est passé inaperçu (l'oracle 120 est mono-départ).
2. **Tournoi multi-départs** : les phases sont rattachées au **premier créneau** (numéro le plus
   bas). Les autres départs se retrouvent **sans déroulé** et devront se voir appliquer un format.
   C'est une conséquence assumée, et le seul choix qui préserve l'intégrité : recopier la séquence
   dans chaque créneau créerait des phases neuves auxquelles **rien** ne pendrait, tandis que les
   forfaits et les plans de duels (`forfait.phase_id`, `placement_tableau.phase_id`) resteraient
   accrochés au seul exemplaire d'origine. On aurait échangé une donnée fausse contre une donnée
   incohérente. Mieux vaut un départ vide, visible à l'écran, qu'un déroulé fantôme.
3. **Tournoi avec des phases mais aucun départ** : un créneau de reprise est **créé**
   (numéro 1, horaire ``09:00``, tarif ``0``) et reçoit la séquence. Fabriquer une donnée en
   migration n'est pas anodin, mais les deux alternatives sont pires : supprimer les phases est
   destructeur, et échouer bloquerait l'ouverture de la base. Sous le nouveau modèle, cet état est
   de toute façon invalide — la migration doit produire un schéma cohérent, pas le constater.
   Le créneau est reconnaissable (tarif nul, horaire par défaut) et l'organisateur l'ajuste.

Les phases **orphelines** (dont le tournoi n'existe plus — DETTE-001, FK sans `ON DELETE`) sont
supprimées : elles ne peuvent être rattachées à aucun créneau, et une FK `NOT NULL` ne les
tolérerait pas. Idem pour les barrages.

## Downgrade

Réversible **structurellement**, pas fonctionnellement : le retour à `tournoi_id` se fait par
jointure `depart → tournoi` et redonne un schéma valide. Mais les tournois multi-départs
retrouveront un déroulé **fusionné** — c'est-à-dire le bug qu'ADR-0075 corrige. Le downgrade existe
pour dépanner un déploiement, pas pour revenir en arrière durablement.

⚠️ **Il ne garde que les phases du premier créneau** (`_replier_les_copies_de_creneau`, correctif de
revue). Le modèle de destination ne connaît qu'une séquence 1..N par tournoi : y rebrancher les N
copies par créneau produisait des rangs en doublon, invisibles ici — aucune contrainte ne les
interdit avant la `0042` — mais fatals au `upgrade` suivant, où la `0043` doublonnait
`(tournoi, ordre)` dans `deroule_etape` et laissait la base **bloquée à mi-migration**. L'avancement
des autres créneaux est donc **perdu** : c'est le prix d'un modèle qui n'a pas de place pour lui.
L'aller-retour `upgrade → downgrade → upgrade` est éprouvé par
`tests/test_migration_0042_0043_portee_et_deroule.py`.

[ADR-0017]: ../../../docs/adr/0017-le-depart-est-un-creneau-du-tournoi.md
[ADR-0075]: ../../../docs/adr/0075-le-depart-est-la-portee-sportive.md
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0042_portee_sportive_depart"
down_revision = "0041_cloisonnement_cible"
branch_labels = None
depends_on = None


# Le créneau de reprise du cas 3 : reconnaissable, et volontairement gratuit — un tarif inventé
# fausserait la facturation, un tarif nul se voit et s'ajuste.
_HORAIRE_REPRISE = "09:00"


def _depart_cible_par_tournoi(connexion: sa.Connection) -> dict[int, int]:
    """`{tournoi_id: depart_id}` — le créneau qui recevra les phases de chaque tournoi.

    Le **premier** départ au sens du numéro (celui que l'écran affiche en tête), pas au sens de
    l'identifiant technique : deux créneaux créés dans le désordre puis renumérotés donneraient
    des rattachements différents selon le critère, et le numéro est celui que l'organisateur voit.
    """
    lignes = connexion.execute(
        sa.text("SELECT tournoi_id, id FROM depart ORDER BY tournoi_id, numero, id")
    ).fetchall()
    cibles: dict[int, int] = {}
    for tournoi_id, depart_id in lignes:
        cibles.setdefault(tournoi_id, depart_id)
    return cibles


def _creer_departs_de_reprise(connexion: sa.Connection, table: str, cibles: dict[int, int]) -> None:
    """Crée un créneau de reprise pour les tournois qui portent des `table` mais aucun départ."""
    manquants = connexion.execute(
        sa.text(
            f"SELECT DISTINCT t.tournoi_id FROM {table} AS t "
            "JOIN tournoi ON tournoi.id = t.tournoi_id "
            "WHERE t.tournoi_id NOT IN (SELECT tournoi_id FROM depart)"
        )
    ).scalars()
    for tournoi_id in manquants:
        if tournoi_id in cibles:
            continue
        connexion.execute(
            sa.text(
                "INSERT INTO depart (tournoi_id, numero, horaire, tarif_centimes, quota) "
                "VALUES (:tournoi_id, 1, :horaire, 0, NULL)"
            ),
            {"tournoi_id": tournoi_id, "horaire": _HORAIRE_REPRISE},
        )
        cibles[tournoi_id] = int(
            connexion.execute(
                sa.text("SELECT id FROM depart WHERE tournoi_id = :t ORDER BY id DESC LIMIT 1"),
                {"t": tournoi_id},
            ).scalar_one()
        )


def _basculer(connexion: sa.Connection, table: str) -> None:
    """Fait passer `table` de `tournoi_id` à `depart_id`, données reprises.

    La colonne est ajoutée **nullable**, remplie, purgée de ses orphelins, puis rendue `NOT NULL`
    au moment de retirer l'ancienne : sous SQLite on ne peut pas ajouter une colonne `NOT NULL`
    sans défaut à une table peuplée.
    """
    cibles = _depart_cible_par_tournoi(connexion)
    _creer_departs_de_reprise(connexion, table, cibles)

    with op.batch_alter_table(table) as batch:
        batch.add_column(sa.Column("depart_id", sa.Integer(), nullable=True))

    for tournoi_id, depart_id in cibles.items():
        connexion.execute(
            sa.text(f"UPDATE {table} SET depart_id = :depart WHERE tournoi_id = :tournoi"),
            {"depart": depart_id, "tournoi": tournoi_id},
        )

    # Orphelines : tournoi disparu (DETTE-001 — FK sans `ON DELETE`). Aucun créneau ne peut les
    # accueillir, et la contrainte `NOT NULL` qui suit les refuserait. Leur descendance
    # (`forfait`, `placement_tableau`) part avec elles par `ON DELETE CASCADE`.
    connexion.execute(sa.text(f"DELETE FROM {table} WHERE depart_id IS NULL"))

    with op.batch_alter_table(table) as batch:
        batch.alter_column("depart_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(f"fk_{table}_depart", "depart", ["depart_id"], ["id"])
        batch.drop_column("tournoi_id")


def upgrade() -> None:
    connexion = op.get_bind()
    _basculer(connexion, "phase")
    _basculer(connexion, "barrage")


def _replier_les_copies_de_creneau(connexion: sa.Connection) -> None:
    """Ne garde que les phases du **premier créneau** de chaque tournoi (downgrade).

    ⚠️ **C'est ce qui rend l'aller-retour possible**, et c'est un correctif de revue. L'`upgrade`
    ci-dessus part d'un modèle où un tournoi a **une** séquence 1..N et la rattache à un créneau ;
    depuis, chaque créneau porte la sienne. Rebrancher naïvement *toutes* les phases sur le tournoi
    lui en donnait donc N par rang — un état que le modèle d'avant la `0042` n'a jamais connu et
    dont aucune contrainte ne le protège. Le `upgrade` suivant les rattachait toutes au même
    créneau, et la `0043` butait sur son propre `INSERT … SELECT` : `(tournoi, ordre)` en doublon
    dans `deroule_etape`, base **bloquée à mi-migration**.

    La perte est réelle et assumée — l'avancement des autres créneaux n'a pas de place où aller
    dans le modèle de destination —, du même ordre que celle qu'annonce déjà la `0043` sur les
    définitions divergentes. On la **dit** plutôt que de la laisser découvrir.

    Les artefacts d'exécution des phases supprimées partent explicitement : leurs FK déclarent bien
    `ON DELETE CASCADE`, mais SQLite ne l'applique que si `PRAGMA foreign_keys` est actif — ce
    qu'Alembic ne fait pas. Compter dessus laisserait des `duel` orphelins pointant un `phase_id`
    disparu.
    """
    cibles = _depart_cible_par_tournoi(connexion)
    if not cibles:
        return
    gardes = ",".join(str(depart_id) for depart_id in cibles.values())
    condamnees = f"SELECT id FROM phase WHERE depart_id NOT IN ({gardes})"
    for enfant in ("duel", "placement_tableau", "forfait"):
        connexion.execute(sa.text(f"DELETE FROM {enfant} WHERE phase_id IN ({condamnees})"))
    # `barrage.phase_id` est **nullable** et sans cascade : on délie plutôt que de supprimer — un
    # barrage annoncé reste une trace de ce qui s'est passé, il n'est pas dérivé de la phase.
    connexion.execute(
        sa.text(f"UPDATE barrage SET phase_id = NULL WHERE phase_id IN ({condamnees})")
    )
    connexion.execute(sa.text(f"DELETE FROM phase WHERE depart_id NOT IN ({gardes})"))


def _rebasculer(connexion: sa.Connection, table: str) -> None:
    """Retour à `tournoi_id` par la jointure `depart → tournoi` (downgrade)."""
    with op.batch_alter_table(table) as batch:
        batch.add_column(sa.Column("tournoi_id", sa.Integer(), nullable=True))
    connexion.execute(
        sa.text(
            f"UPDATE {table} SET tournoi_id = "
            f"(SELECT depart.tournoi_id FROM depart WHERE depart.id = {table}.depart_id)"
        )
    )
    connexion.execute(sa.text(f"DELETE FROM {table} WHERE tournoi_id IS NULL"))
    with op.batch_alter_table(table) as batch:
        batch.alter_column("tournoi_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(f"fk_{table}_tournoi", "tournoi", ["tournoi_id"], ["id"])
        batch.drop_column("depart_id")


def downgrade() -> None:
    connexion = op.get_bind()
    _rebasculer(connexion, "barrage")
    # Le repli **précède** la rebascule : une fois `tournoi_id` rétabli, on ne saurait plus quelles
    # phases venaient de quel créneau.
    _replier_les_copies_de_creneau(connexion)
    _rebasculer(connexion, "phase")
