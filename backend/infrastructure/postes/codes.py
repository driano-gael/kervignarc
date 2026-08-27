"""Génération des codes de cible (E04US001).

Un code se **retape** sous un QR abîmé : alphabet sans caractères confondables, en majuscules, tiré
par `secrets` (jamais `random`). L'unicité globale n'est pas garantie ici — `ServicePostes`
ré-essaie en cas de collision.

⚠️ Dupliqué **volontairement** de `infrastructure.scoreurs.codes` : 2ᵉ occurrence, on attend la 3ᵉ.
"""

from __future__ import annotations

import secrets

# DETTE-040 - 3e exemplaire depuis le front (shared/ui/codeTerrain.ts). Cf. registre.
ALPHABET_CODE = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
"""32 symboles sans les confondables `I`, `O`, `0`, `1` — lisibles sur un papier de terrain."""

LONGUEUR_CODE = 6
"""6 caractères : ~10^9 combinaisons, unique pour quelques dizaines de cibles, et court à taper."""


def generer_code_poste() -> str:
    """Renvoie un code candidat de `LONGUEUR_CODE` symboles tirés de `ALPHABET_CODE`."""
    return "".join(secrets.choice(ALPHABET_CODE) for _ in range(LONGUEUR_CODE))
