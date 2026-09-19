"""Vérifie que `requirements.txt` épingle bien toutes les dépendances de `pyproject.toml`.

Appelé par `ci.yml` et par `porte.py`. Extrait de `ci.yml` en E00US031, où il vivait en
`shell: python` inline : les deux portes en auraient gardé chacune une copie (ADR-0110).
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path


def normaliser(nom: str) -> str:
    return re.sub(r"[-_.]+", "-", nom).lower()


def _dependances_declarees() -> list[str]:
    donnees = tomllib.loads(Path("pyproject.toml").read_text("utf-8"))
    projet = donnees["project"]
    directes: list[str] = list(projet.get("dependencies", []))
    for extra in projet.get("optional-dependencies", {}).values():
        directes += extra
    return directes


def _epinglages_figes() -> set[str]:
    figes: set[str] = set()
    for ligne in Path("requirements.txt").read_text("utf-8").splitlines():
        trouve = re.match(r"^([A-Za-z0-9._-]+)==([^\s;]+)", ligne.strip())
        if trouve:
            figes.add(f"{normaliser(trouve.group(1))}=={trouve.group(2).lower()}")
    return figes


def manquantes() -> list[str]:
    figes = _epinglages_figes()
    absentes: list[str] = []
    for specification in _dependances_declarees():
        trouve = re.match(r"^([A-Za-z0-9._-]+)(?:\[[^\]]*\])?==([^\s;]+)", specification)
        if not trouve:
            absentes.append(f"{specification} (doit être épinglé avec ==)")
        elif f"{normaliser(trouve.group(1))}=={trouve.group(2).lower()}" not in figes:
            absentes.append(f"{trouve.group(1)}=={trouve.group(2)}")
    return absentes


def main() -> int:
    absentes = manquantes()
    if absentes:
        print("requirements.txt désynchronisé de pyproject.toml. Manquant/incohérent :")
        for item in absentes:
            print(f"  - {item}")
        print(
            'Régénère : pip install -e ".[dev]" && '
            "pip freeze --exclude-editable > requirements.txt"
        )
        return 1
    print("requirements.txt est synchronisé avec pyproject.toml.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
