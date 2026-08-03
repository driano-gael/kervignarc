"""La racine des erreurs du domaine — dont **toutes** les autres héritent.

Isolée dans son propre module pour que le barillet (`__init__.py`) ne soit **que** des imports :
une classe définie avant eux les repoussait après le premier code exécutable, et forçait les
modules de thème à importer le paquet qui les importe. La circularité ne tenait que par l'ordre
des lignes."""

from __future__ import annotations


class DomainError(Exception):
    """Racine des erreurs métier. Chaque sous-classe porte un `code` stable."""

    code = "erreur_domaine"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
