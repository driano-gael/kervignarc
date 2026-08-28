"""Patrimoine — une brique de bibliothèque se **copie** dans un tournoi, elle ne s'y référence pas.

⚠️ **Copier, parce qu'un tournoi archivé ne doit pas bouger** : si un tarif change en 2027, une
brique référencée réécrirait l'histoire du tournoi 2026 (arbitrage du 30/07/2026). Contrepartie
assumée — un brouillon ne bénéficie pas d'une correction faite ensuite. Une modification locale
déclarée **permanente** est promue dans la bibliothèque, sans toucher les tournois déjà assemblés.
"""

# ADR-0060, E01US023 — une brique se **copie** dans un tournoi ; `DETTE-023` trace ce qui restait
# à découpler quand l'atelier a cessé d'exiger un tournoi.

from __future__ import annotations

from enum import Enum


class OrigineBrique(str, Enum):
    """D'où vient une brique — ce qui distingue le **référentiel officiel** de la création du club.

    Le commanditaire veut une liste séparée officiel/utilisateur, et pouvoir, en modifiant un
    officiel, soit en faire une copie, soit l'intégrer au FFTA officiel. ⚠️ **Cette marque ne
    suffit pas à dire « conforme FFTA »** : elle dit d'où vient la brique, pas si elle a été
    modifiée depuis, ni contre quelle version du règlement. Tant que le référentiel versionné
    n'existe pas, `FFTA` signifie « issue du préchargement officiel », rien de plus.
    """

    FFTA = "ffta"
    UTILISATEUR = "utilisateur"
