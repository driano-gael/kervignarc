"""Aiguillage par signature binaire — la source se reconnaît au contenu (arbitrage 1 d'E02US007)."""

from __future__ import annotations

from domain.erreurs import FichierInscritsIllisible
from domain.import_inscrits import FichierInscrits
from infrastructure.import_inscrits import ianseo, resultarc

_SIGNATURE_OLE2 = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_SIGNATURE_ZIP = b"PK\x03\x04"


class LecteurFichierInscritsAuto:
    def lire(self, contenu: bytes) -> FichierInscrits:
        if not contenu.strip():
            raise FichierInscritsIllisible("Le fichier déposé est vide.")
        if contenu.startswith(_SIGNATURE_OLE2):
            return resultarc.lire(contenu)
        if contenu.startswith(_SIGNATURE_ZIP):
            raise FichierInscritsIllisible(
                "Classeur .xlsx non reconnu : déposez l'export Ianseo (.csv) ou le classeur "
                "Résult'Arc (.xls)."
            )
        return ianseo.lire(contenu)
