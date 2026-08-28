"""Déduplication des écritures par identifiant de saisie — en mémoire, bornée, volatile (ADR-0036).
Un redémarrage oublie les identifiants, sans conséquence : la fenêtre de rejeu tient dans une
exécution (règle 12).

⚠️ **Consulté DANS la commande de la file** (règle 7) : c'est ce qui rend « déjà vu ? » et
l'écriture **atomiques**. Hors du writer, deux rejeux concurrents manqueraient tous deux le cache.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Callable
from typing import TypeVar, cast

_T = TypeVar("_T")

_BORNE_DEFAUT = 2048
"""Nombre maximal d'identifiants retenus (LRU) — garde-fou contre une croissance non bornée de la
mémoire. La borne **peut** être franchie sur une grosse journée (30 tablettes, qualif + duels),
mais **sans conséquence** : un identifiant encore susceptible d'être rejoué vient d'être utilisé,
il est donc **MRU** ; il faudrait 2048 écritures *plus récentes* pour l'évincer — soit des heures
après que le client a cessé de rejouer. L'éviction ne touche que des identifiants hors de toute
fenêtre de rejeu réaliste."""


class RegistreIdempotence:
    """Mémoire bornée des saisies déjà traitées, indexées par l'identifiant fourni par le client."""

    def __init__(self, borne: int = _BORNE_DEFAUT) -> None:
        self._resultats: OrderedDict[str, object] = OrderedDict()
        self._borne = borne
        self._verrou = threading.Lock()

    def executer(self, identifiant: str | None, commande: Callable[[], _T]) -> _T:
        """Exécute `commande` **une seule fois** par `identifiant` et renvoie son résultat.

        `identifiant` vide/`None` → aucune déduplication. Sinon, un premier passage exécute l'acte
        et **mémorise** son résultat ; tout rejeu renvoie ce résultat **sans ré-exécuter** — l'acte
        (volée écrite, trace d'audit) n'a lieu qu'une fois. ⚠️ La commande s'exécute **hors
        verrou**, ce qui est correct parce que ce registre n'est consulté que depuis le writer
        unique.
        """
        if not identifiant:
            return commande()
        with self._verrou:
            if identifiant in self._resultats:
                self._resultats.move_to_end(identifiant)
                # E04US002 : idempotence — rejeu dédoublonné, l'acte n'est pas rejoué.
                return cast(_T, self._resultats[identifiant])
        resultat = commande()
        with self._verrou:
            self._resultats[identifiant] = resultat
            self._resultats.move_to_end(identifiant)
            while len(self._resultats) > self._borne:
                self._resultats.popitem(last=False)  # éviction du plus ancien (LRU)
        return resultat
