"""Patrimoine — une brique de bibliothèque se **copie** dans un tournoi, elle ne s'y référence pas.

⚠️ **Copier, parce qu'un tournoi archivé ne doit pas bouger** : si un tarif change en 2027, une
brique référencée réécrirait l'histoire du tournoi 2026 (arbitrage du 30/07/2026). Contrepartie
assumée — un brouillon ne bénéficie pas d'une correction faite ensuite. Une modification locale
déclarée **permanente** est promue dans la bibliothèque, sans toucher les tournois déjà assemblés.
"""

from __future__ import annotations

from enum import Enum


class OrigineBrique(str, Enum):
    """D'où vient une brique — ce qui distingue le **référentiel officiel** de la création du club.

    Le commanditaire veut « une liste séparée par officiel FFTA et création utilisateur », et
    pouvoir, en modifiant un officiel, soit « en faire une copie pour garder les deux modèles »,
    soit « l'intégrer au FFTA officiel (le règlement peut évoluer) ».

    ⚠️ **Cette marque ne suffit pas à dire « conforme FFTA ».** Elle dit d'où vient la brique, pas
    si elle a été modifiée depuis, ni contre **quelle version** du règlement elle a été établie. Le
    référentiel versionné et le contrôle de conformité relèvent du lot suivant ; tant qu'ils
    n'existent pas, `FFTA` signifie « issue du préchargement officiel », rien de plus.
    """

    FFTA = "ffta"
    UTILISATEUR = "utilisateur"
