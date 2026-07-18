"""Génération des codes individuels de scoreur (E10US003).

Un code est distribué **sur papier** et **retapé** par le scoreur sur son téléphone : il doit être
court et sans ambiguïté de lecture. D'où un alphabet **sans caractères confondables** (`0`/`O`,
`1`/`I`) et en majuscules seules, tiré au sort cryptographiquement (`secrets`, jamais `random` — la
règle 11 « stdlib de préférence » et la robustesse d'un secret même modeste). L'unicité globale
n'est **pas** garantie ici : c'est `ServiceScoreurs` qui ré-essaie en cas de collision (pré-contrôle
`par_code`), le générateur ne fait que produire un candidat.
"""

from __future__ import annotations

import secrets

ALPHABET_CODE = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
"""32 symboles sans les confondables `I`, `O`, `0`, `1` — lisibles sur un papier de terrain."""

LONGUEUR_CODE = 6
"""6 caractères : ~10^9 combinaisons, de quoi rester unique pour 3-4 scoreurs, et court à taper."""


def generer_code_scoreur() -> str:
    """Renvoie un code candidat de `LONGUEUR_CODE` symboles tirés de `ALPHABET_CODE`."""
    return "".join(secrets.choice(ALPHABET_CODE) for _ in range(LONGUEUR_CODE))
