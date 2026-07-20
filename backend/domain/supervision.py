"""Politique de supervision des postes (E12US001, ADR-0038) — pur, synchrone (règle 1).

L'**état** d'un poste (*en ligne* · *hors ligne* · *non rattaché*) est une **règle métier** dérivée
de sa présence, pas une lecture d'horloge : le « maintenant » et le seuil arrivent en paramètres,
le domaine ne lit jamais l'heure (port `Horloge`, côté service — règle 9, déterminisme). La
distinction porte le cœur du CA : séparer *une tablette morte* (hors ligne) de *des archers qui
tirent lentement* (en ligne, mais dont la **dernière saisie** est ancienne — activité calculée
ailleurs, hors de cette politique).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum


class EtatPoste(Enum):
    """État de présence d'un poste dans la console de supervision (ADR-0038)."""

    EN_LIGNE = "en_ligne"
    HORS_LIGNE = "hors_ligne"
    NON_RATTACHE = "non_rattache"


@dataclass(frozen=True)
class ActivitePoste:
    """Dernière présence signalée par un poste : **quand** (heartbeat) et depuis quelle **IP**.

    L'IP est un **indice de diagnostic** (retrouver physiquement une tablette), **jamais** une
    identité (`D-06`) : le poste s'identifie par son jeton, pas par son adresse. `None` si l'IP
    n'a pas pu être lue.
    """

    instant: datetime.datetime
    ip: str | None


def etat_poste(
    *,
    rattache: bool,
    secondes_depuis_heartbeat: float | None,
    seuil_hors_ligne_s: float,
) -> EtatPoste:
    """Dérive l'état d'un poste depuis sa présence (ADR-0038 §1).

    - **non rattaché** : aucune session ouverte (le code de cible est préparé, mais aucune tablette
      n'est dessus) — `rattache` faux ;
    - **hors ligne** : rattaché, mais dernier heartbeat **plus vieux que le seuil** — ou jamais vu
      (`secondes_depuis_heartbeat is None`) ;
    - **en ligne** : rattaché et vu il y a **≤ seuil** (borne **inclusive** côté en-ligne).

    `secondes_depuis_heartbeat` est un écart déjà calculé par le service (via le port `Horloge`) —
    d'où l'absence totale de `datetime` ici : la règle reste une pure comparaison de nombres.
    """
    if not rattache:
        return EtatPoste.NON_RATTACHE
    if secondes_depuis_heartbeat is None or secondes_depuis_heartbeat > seuil_hors_ligne_s:
        return EtatPoste.HORS_LIGNE
    return EtatPoste.EN_LIGNE
