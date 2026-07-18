"""Génération des codes de cible (E04US001).

Un code est imprimé **sous le QR** de la cible et **retapé** en secours (QR abîmé, appareil photo
capricieux) : il doit être court et sans ambiguïté de lecture. D'où un alphabet **sans caractères
confondables** et en majuscules, tiré cryptographiquement (`secrets`, jamais `random`). L'unicité
globale n'est **pas** garantie ici : `ServicePostes` ré-essaie en cas de collision.

Volontairement **dupliqué** de `infrastructure.scoreurs.codes` (2ᵉ « code de terrain retapé ») : on
attend une 3ᵉ preuve avant tout remède structurel (règle « dette »).
"""

from __future__ import annotations

import secrets

ALPHABET_CODE = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
"""32 symboles sans les confondables `I`, `O`, `0`, `1` — lisibles sur un papier de terrain."""

LONGUEUR_CODE = 6
"""6 caractères : ~10^9 combinaisons, unique pour quelques dizaines de cibles, et court à taper."""


def generer_code_poste() -> str:
    """Renvoie un code candidat de `LONGUEUR_CODE` symboles tirés de `ALPHABET_CODE`."""
    return "".join(secrets.choice(ALPHABET_CODE) for _ in range(LONGUEUR_CODE))
