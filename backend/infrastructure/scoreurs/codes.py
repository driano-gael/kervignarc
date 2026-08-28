"""Génération des codes individuels de scoreur (E10US003).

Un code est distribué **sur papier** puis retapé : alphabet sans caractères confondables (`0`/`O`,
`1`/`I`), majuscules seules, tiré par `secrets` (jamais `random`). L'unicité globale n'est pas
garantie ici — `ServiceScoreurs` ré-essaie en cas de collision (pré-contrôle `par_code`).
"""

from __future__ import annotations

import secrets

# DETTE-040 - 3e exemplaire depuis le front (shared/ui/codeTerrain.ts). Cf. registre.
ALPHABET_CODE = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
"""32 symboles sans les confondables `I`, `O`, `0`, `1` — lisibles sur un papier de terrain."""

LONGUEUR_CODE = 6
"""6 caractères : ~10^9 combinaisons, de quoi rester unique pour 3-4 scoreurs, et court à taper."""


def generer_code_scoreur() -> str:
    """Renvoie un code candidat de `LONGUEUR_CODE` symboles tirés de `ALPHABET_CODE`."""
    return "".join(secrets.choice(ALPHABET_CODE) for _ in range(LONGUEUR_CODE))
