"""depart : horaire `HH:MM` obligatoire (NOT NULL) + reprise des libellés libres existants

Revision ID: 0032_depart_horaire_hhmm
Revises: 0031_forfait
Create Date: 2026-07-27

E02US010. L'horaire d'un départ était un **libellé libre facultatif** (E02US004) : `NULL` ou
n'importe quel texte (« 9h00 », « matin »). Il devient un **horaire du jour `HH:MM` obligatoire**
(validé au domaine). La colonne passe donc **NOT NULL**, ce qui impose de **reprendre** les valeurs
existantes non conformes — rien ne permet de deviner un `HH:MM` depuis « matin ».

**Reprise best-effort** : on convertit ce qui est convertible sans ambiguïté (`9h00`→`09:00`,
`9h`→`09:00`, `9:00`→`09:00`), et l'on retombe sur `00:00` (minuit — une valeur volontairement
implausible qui signale « à corriger ») pour le reste (`NULL`, « matin », vide). C'est une base
mono-club, locale et pas encore en production réelle : la reprise vise surtout les horaires de test
saisis à la démo (« 8h00 » → « 08:00 »), pas un patrimoine de données à préserver au caractère près.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0032_depart_horaire_hhmm"
down_revision: str | None = "0031_forfait"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_HHMM = re.compile(r"([01][0-9]|2[0-3]):[0-5][0-9]")
"""Le format canonique cible : `HH:MM` 24 h (identique à `domain.depart._FORMAT_HORAIRE`)."""

_HEURE_MINUTE = re.compile(r"(\d{1,2})\s*[h:]\s*(\d{2})")
"""Un libellé « 9h00 » / « 9:00 » / « 09h30 » : heure 1-2 chiffres, séparateur `h`/`:`, minutes."""

_HEURE_SEULE = re.compile(r"(\d{1,2})\s*h")
"""Un libellé « 9h » sans minutes → minute `00`."""


def _vers_hhmm(brut: str | None) -> str:
    """Convertit un horaire libre existant en `HH:MM` valide (best-effort ; défaut `00:00`)."""
    if brut is None:
        return "00:00"
    texte = brut.strip()
    if _HHMM.fullmatch(texte):
        return texte
    correspondance = _HEURE_MINUTE.fullmatch(texte)
    if correspondance is not None:
        heure, minute = int(correspondance.group(1)), int(correspondance.group(2))
        if 0 <= heure <= 23 and 0 <= minute <= 59:
            return f"{heure:02d}:{minute:02d}"
    correspondance = _HEURE_SEULE.fullmatch(texte)
    if correspondance is not None:
        heure = int(correspondance.group(1))
        if 0 <= heure <= 23:
            return f"{heure:02d}:00"
    return "00:00"


def upgrade() -> None:
    """Reprend les horaires existants en `HH:MM`, puis rend la colonne NOT NULL."""
    bind = op.get_bind()
    lignes = bind.execute(sa.text("SELECT id, horaire FROM depart")).fetchall()
    for ligne in lignes:
        converti = _vers_hhmm(ligne.horaire)
        if converti != ligne.horaire:
            bind.execute(
                sa.text("UPDATE depart SET horaire = :horaire WHERE id = :id"),
                {"horaire": converti, "id": ligne.id},
            )
    # SQLite ne sait pas passer une colonne NOT NULL en place : batch recrée la table (en
    # préservant `uq_depart_tournoi_numero` et la FK, reflétées automatiquement).
    with op.batch_alter_table("depart") as batch:
        batch.alter_column("horaire", existing_type=sa.String(), nullable=False)


def downgrade() -> None:
    """Redonne à `horaire` son caractère facultatif (les valeurs reprises restent en place)."""
    with op.batch_alter_table("depart") as batch:
        batch.alter_column("horaire", existing_type=sa.String(), nullable=True)
