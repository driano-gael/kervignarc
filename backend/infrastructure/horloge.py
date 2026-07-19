"""Adapter `HorlogeSysteme` — implémentation du port `domain.ports.Horloge` (E10US005).

Lit l'**horloge système** en **UTC** (`datetime` *aware*). C'est le seul point du code qui appelle
`datetime.now` : partout ailleurs (services, domaine), le temps arrive par le port `Horloge`, ce qui
rend les cas d'usage déterministes en test (règle 9). UTC — et non l'heure locale — parce qu'une
trace d'audit doit être comparable sans ambiguïté de fuseau ni saut d'heure d'été.
"""

from __future__ import annotations

import datetime


class HorlogeSysteme:
    """Horloge branchée sur l'horloge système, en UTC (adapter du port `Horloge`)."""

    def maintenant(self) -> datetime.datetime:
        """Renvoie l'instant courant en UTC (datetime *aware*)."""
        return datetime.datetime.now(datetime.UTC)
