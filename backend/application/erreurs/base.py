"""La racine des erreurs applicatives — dont **toutes** les autres héritent.

Isolée dans son propre module pour que le barillet (`__init__.py`) ne soit **que** des
imports : une classe définie avant eux les repousse après le premier code exécutable (E402) et
force les modules de thème à importer le paquet qui les importe. Idem `domain/erreurs/base.py`."""

from __future__ import annotations


class ApplicationError(Exception):
    """Racine des erreurs de cas d'usage. Chaque sous-classe porte un `code` stable."""

    code = "erreur_application"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
