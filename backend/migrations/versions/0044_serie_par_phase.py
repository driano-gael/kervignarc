"""la feuille de marque se rattache à sa phase, plus au tournoi — E05US025

Revision ID: 0044_serie_par_phase
Revises: 0043_deroule_defini_une_fois
Create Date: 2026-08-09

[ADR-0082] rend licite un déroulé portant **plusieurs qualifications** : 120 archers tirent 3x20,
puis la moitié haute et la moitié basse tirent chacune 3x15. Un archer y ouvre donc
**deux** feuilles de marque, et le CA exige qu'une flèche du second tour ne puisse pas atterrir
dans la première.

`SERIE` gagne `phase_id` (`NOT NULL`, `ON DELETE CASCADE`) et sa clé métier descend de
`UNIQUE(tournoi_id, archer_id)` à `UNIQUE(phase_id, archer_id)`.

**`tournoi_id` est conservé**, à rebours de la `0042` qui avait supprimé `phase.tournoi_id` en
remontant la portée. La situation n'est pas la même : là-bas deux portées **concurrentes** auraient
obligé chaque lecture à choisir laquelle honorer ; ici `tournoi_id` n'est plus une clé du tout,
juste le cadre que lisent les vues d'ensemble (`SerieRepository.par_tournoi`). Le déduire par
jointure `phase -> depart -> tournoi` à chaque lecture coûterait plus qu'il ne rapporte, et aucune
n'a de choix à faire : l'unicité, elle, n'existe plus qu'à la phase.

## Ce que cette migration résorbe au passage

**DETTE-046** — « un archer inscrit sur deux départs ne peut avoir qu'une série ». Le registre
proposait `UNIQUE(depart_id, archer_id)` + `Serie.depart_id`. La phase **subsume** le départ (elle
lui appartient depuis ADR-0075), donc descendre la clé jusqu'à la phase règle le cas de DETTE-046
*et* celui des qualifications multiples, avec **un** champ au lieu de deux qui diraient la même
chose à deux mailles. Les flèches du matin et de l'après-midi ont désormais chacune leur place.

## Reprise des données existantes — trois cas, tous traités explicitement

⚠️ **Le `type` d'une phase ne vit pas dans `phase`** : depuis la `0043` (ADR-0076), le déroulé se
définit une fois par tournoi dans `deroule_etape`, et `phase` ne garde que l'avancement d'un
créneau. La jointure passe donc par `phase -> depart -> deroule_etape` sur `(tournoi_id, ordre)`,
`ordre` étant la clé de rattachement voulue par ADR-0076 (et non un `etape_id`, qu'un
réordonnancement ferait diverger).

Avant cette migration, un tournoi n'a qu'**une** qualification par créneau (l'invariant d'unicité
d'E05US021, que l'US retire). La reprise consiste donc à retrouver *laquelle*, sans ambiguïté
possible sur le fond — seule la question « quel créneau ? » se pose.

1. **L'archer est inscrit à un créneau doté d'une qualification** : sa série s'y rattache. C'est le
   cas courant et il ne perd rien. Quand il est inscrit à **plusieurs** créneaux, on retient celui
   de **numéro le plus bas** — même convention que la `0042`. C'est précisément la situation que
   DETTE-046 décrivait comme cassée : ses flèches n'avaient qu'un emplacement, donc il n'existe de
   toute façon qu'une série à replacer, et la placer sur le premier créneau reproduit exactement ce
   que l'application affichait hier.

2. **Sinon**, repli sur la **première qualification du tournoi** (départ de numéro le plus bas).
   C'est mot pour mot ce que faisait `application/portee.py:qualification_du_tournoi`, que tous les
   lecteurs empruntaient : le comportement observable est donc **inchangé** pour ces lignes. Couvre
   la série d'un archer sans inscription (donnée déjà incohérente) et celle d'un archer dont le
   créneau n'a pas reçu de format.

3. **Résidu : aucune qualification dans tout le tournoi** — la série est supprimée, et le nombre
   supprimé est **journalisé** (niveau `WARNING`, avec le détail par tournoi).

   ⚠️ **C'est la seule perte de données de cette migration, et elle est délibérée** (arbitrage du
   commanditaire, 09/08/2026). L'état est atteignable : supprimer un créneau efface ses phases par
   cascade (`phase.depart_id`, `0042`) mais **pas** les séries, qui pendaient au tournoi. Ces lignes
   n'ont plus aucun rattachement sportif — ni barème pour les lire, ni classement où les ranger — et
   une colonne `NOT NULL` ne les tolère pas. La `0042` a posé le même précédent en supprimant les
   phases orphelines.

   Elles ne sont **pas** silencieuses : le compte part au log avant le `DELETE`, pour qu'une perte
   inattendue soit visible dans la sortie de migration plutôt que découverte en salle.

## Downgrade

Réversible **structurellement** : `phase_id` est retirée et l'unicité remonte au tournoi. Mais un
tournoi à plusieurs qualifications y perd tout : deux feuilles d'un même archer violeraient
`UNIQUE(tournoi_id, archer_id)`. Le downgrade **ne garde donc que la feuille de la qualification la
plus précoce** (`ordre` le plus bas), et journalise ce qu'il écarte — c'est le pendant du repli des
copies de créneau de la `0042`, et le même aveu : le modèle de destination n'a pas de place pour
cette donnée. Le downgrade existe pour dépanner un déploiement, pas pour revenir en arrière
durablement.

[ADR-0075]: ../../../docs/adr/0075-le-depart-est-la-portee-sportive.md
[ADR-0082]: ../../../docs/adr/0082-plusieurs-qualifications-dans-un-meme-deroule.md
"""

from __future__ import annotations

import logging

import sqlalchemy as sa
from alembic import op

revision = "0044_serie_par_phase"
down_revision = "0043_deroule_defini_une_fois"
branch_labels = None
depends_on = None

_logger = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    """Ajoute `phase_id`, la renseigne pour chaque série, puis la rend obligatoire et unique."""
    # Colonne **d'abord nullable** : SQLite n'accepte pas d'ajouter une colonne `NOT NULL` sans
    # défaut à une table peuplée, et un défaut ici serait faux (aucune phase n'est « la » bonne).
    # On renseigne, puis on resserre par `batch_alter_table` — la recréation de table qu'impose
    # SQLite pour changer une contrainte.
    op.add_column("serie", sa.Column("phase_id", sa.Integer(), nullable=True))

    connexion = op.get_bind()

    # Cas 1 — la qualification du créneau où l'archer est inscrit (numéro de départ le plus bas).
    connexion.execute(
        sa.text(
            """
            UPDATE serie
               SET phase_id = (
                   SELECT p.id
                     FROM inscription i
                     JOIN depart d ON d.id = i.depart_id
                     JOIN phase p ON p.depart_id = d.id
                     JOIN deroule_etape e
                       ON e.tournoi_id = d.tournoi_id AND e.ordre = p.ordre
                    WHERE i.archer_id = serie.archer_id
                      AND d.tournoi_id = serie.tournoi_id
                      AND e.type = 'qualification'
                    ORDER BY d.numero, p.ordre
                    LIMIT 1
               )
             WHERE phase_id IS NULL
            """
        )
    )

    # Cas 2 — repli sur la première qualification du tournoi, quel que soit le créneau. C'est la
    # résolution qu'employait `qualification_du_tournoi` : ces lignes gardent donc exactement le
    # comportement qu'elles avaient hier.
    connexion.execute(
        sa.text(
            """
            UPDATE serie
               SET phase_id = (
                   SELECT p.id
                     FROM phase p
                     JOIN depart d ON d.id = p.depart_id
                     JOIN deroule_etape e
                       ON e.tournoi_id = d.tournoi_id AND e.ordre = p.ordre
                    WHERE d.tournoi_id = serie.tournoi_id
                      AND e.type = 'qualification'
                    ORDER BY d.numero, p.ordre
                    LIMIT 1
               )
             WHERE phase_id IS NULL
            """
        )
    )

    # Cas 3 — résidu : le tournoi n'a aucune qualification. Journalisé **avant** le DELETE, pour
    # qu'une perte inattendue se voie dans la sortie de migration.
    orphelines = connexion.execute(
        sa.text(
            """
            SELECT tournoi_id, COUNT(*) AS nb
              FROM serie
             WHERE phase_id IS NULL
             GROUP BY tournoi_id
             ORDER BY tournoi_id
            """
        )
    ).all()
    if orphelines:
        total = sum(ligne.nb for ligne in orphelines)
        detail = ", ".join(f"tournoi {ligne.tournoi_id} : {ligne.nb}" for ligne in orphelines)
        _logger.warning(
            "0044 — %s série(s) supprimée(s), sans aucune phase de qualification dans leur "
            "tournoi (%s). Leur créneau a probablement été supprimé : ces flèches n'avaient plus "
            "ni barème pour les lire ni classement où les ranger.",
            total,
            detail,
        )
        connexion.execute(sa.text("DELETE FROM serie WHERE phase_id IS NULL"))

    with op.batch_alter_table("serie", schema=None) as batch:
        batch.drop_constraint("uq_serie_tournoi_archer", type_="unique")
        batch.alter_column("phase_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            "fk_serie_phase", "phase", ["phase_id"], ["id"], ondelete="CASCADE"
        )
        batch.create_unique_constraint("uq_serie_phase_archer", ["phase_id", "archer_id"])


def downgrade() -> None:
    """Retire `phase_id` et remonte l'unicité au tournoi, en ne gardant qu'une feuille par
    archer."""
    connexion = op.get_bind()

    # Le modèle de destination n'a qu'un emplacement par (tournoi, archer) : on garde la feuille de
    # la qualification la plus **précoce** et l'on écarte les autres, faute de place. Journalisé,
    # parce que c'est une perte — le pendant exact du repli de créneau de la `0042`.
    surnumeraires = (
        connexion.execute(
            sa.text(
                """
            SELECT s.id
              FROM serie s
              JOIN phase p ON p.id = s.phase_id
             WHERE s.id <> (
                   SELECT s2.id
                     FROM serie s2
                     JOIN phase p2 ON p2.id = s2.phase_id
                    WHERE s2.tournoi_id = s.tournoi_id
                      AND s2.archer_id = s.archer_id
                    ORDER BY p2.ordre, s2.id
                    LIMIT 1
             )
            """
            )
        )
        .scalars()
        .all()
    )
    if surnumeraires:
        _logger.warning(
            "0044 (downgrade) — %s feuille(s) de marque écartée(s) : le modèle antérieur n'a "
            "qu'un emplacement par (tournoi, archer), seule la qualification la plus précoce est "
            "conservée.",
            len(surnumeraires),
        )
        connexion.execute(
            sa.text("DELETE FROM serie WHERE id IN :ids").bindparams(
                sa.bindparam("ids", value=tuple(surnumeraires), expanding=True)
            )
        )

    with op.batch_alter_table("serie", schema=None) as batch:
        batch.drop_constraint("uq_serie_phase_archer", type_="unique")
        batch.drop_constraint("fk_serie_phase", type_="foreignkey")
        batch.drop_column("phase_id")
        batch.create_unique_constraint("uq_serie_tournoi_archer", ["tournoi_id", "archer_id"])
