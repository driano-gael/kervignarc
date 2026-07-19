"""Test de l'adapter `HorlogeSysteme` (E10US005) — le port `Horloge` en production.

Le contrat du port est « l'instant courant, en **UTC** (datetime *aware*) ». On vérifie ce contrat,
pas la valeur (impossible à figer : c'est justement ce que le port permet d'injecter en test). Deux
appels successifs ne reculent pas — garde-fou minimal contre une inversion de sens.
"""

from __future__ import annotations

import datetime

from infrastructure.horloge import HorlogeSysteme


def test_maintenant_est_aware_utc() -> None:
    instant = HorlogeSysteme().maintenant()

    assert instant.tzinfo is not None
    assert instant.utcoffset() == datetime.timedelta(0)


def test_maintenant_ne_recule_pas() -> None:
    horloge = HorlogeSysteme()

    premier = horloge.maintenant()
    second = horloge.maintenant()

    assert second >= premier
