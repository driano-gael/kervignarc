"""Rendu **tableur** (CSV) des documents exportables (E16US007, ADR-0101).

Pendant de `infrastructure/pdf/` : mêmes ports, mêmes contenus composés par les services, autre
format de sortie. ⚠️ Le paquet ne s'appelle pas `csv` **exprès** — il porterait le nom du module
stdlib que ses propres modules importent.
"""

from infrastructure.tableur.listes_impression import GenerateurListesImpressionCsv

__all__ = ["GenerateurListesImpressionCsv"]
