"""Déduplication des écritures de saisie par **identifiant de saisie** (E04US002, ADR-0036).

Le client fournit, à chaque écriture de volée, un identifiant opaque ; la commande de la file
**dédoublonne** dessus : un rejeu réseau (ACK perdu, reconnexion, file hors-ligne E04US009) ne
rejoue pas l'acte, il renvoie le résultat déjà calculé. Sans quoi une validation rejouée écrirait
une **seconde entrée d'audit**, et une correction rejouée réappliquerait le geste.

Mécanisme **en mémoire, borné (LRU), volatil** — cohérent avec le modèle de session du projet (le
jeton de poste ADR-0029 et le départ courant ADR-0034 sont eux aussi en mémoire) : un redémarrage
serveur oublie les identifiants, ce qui est sans conséquence (la fenêtre de rejeu tient dans une
exécution). Simplicité assumée hors domaine (règle 12) : mono-club, local, pas de table de
déduplication ni de persistance — voir ADR-0036 pour les alternatives écartées.

⚠️ **Consulté DANS la commande de la file** (writer unique, règle 7) : c'est ce qui rend le
contrôle « déjà vu ? » et l'écriture **atomiques**. Consulté hors du writer, deux rejeux concurrents
pourraient tous deux manquer le cache et s'exécuter — la sérialisation par le writer l'empêche.
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

        `identifiant` vide/`None` → aucune déduplication (exécution simple) : un client qui n'en
        fournit pas accepte le comportement par défaut. Sinon, un premier passage exécute l'acte et
        **mémorise** son résultat ; tout rejeu du même identifiant renvoie ce résultat **sans
        ré-exécuter** — l'acte (volée écrite, trace d'audit) n'a lieu qu'une fois.

        La commande s'exécute **hors verrou** (une écriture peut être lente) : correct car ce
        registre n'est consulté que depuis le writer unique, qui sérialise déjà les commandes.
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
