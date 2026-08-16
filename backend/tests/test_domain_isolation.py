"""Garde-fou d'architecture (E00US004) — le domaine reste pur.

Règle de dépendance de l'architecture hexagonale (guide-architecture.md §2, ADR-0003) :
`domain/` ne doit importer **aucun framework** externe ni **aucune autre couche**
(`application`, `infrastructure`, `api`, `bootstrap`). Ce test **est** la règle, vérifiée
automatiquement (il échoue si la règle est violée) et fait donc échouer la CI le cas échéant.

Choix d'implémentation : analyse AST maison (stdlib), sans dépendance dédiée type
`import-linter` — par parcimonie (ADR-0009), le besoin étant couvert en quelques lignes.
"""

from __future__ import annotations

import ast
from pathlib import Path

# Ce fichier : backend/tests/test_domain_isolation.py → racine backend = parents[1].
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DOMAIN_DIR = _BACKEND_ROOT / "domain"

# Modules interdits d'import depuis le domaine : frameworks/infra technique + autres couches.
_FORBIDDEN_ROOTS: frozenset[str] = frozenset(
    {
        # Frameworks & infrastructure technique
        "fastapi",
        "starlette",
        "uvicorn",
        "pydantic",
        "sqlalchemy",
        "alembic",
        "httpx",
        # Autres couches (le domaine ne dépend d'aucune couche externe)
        "application",
        "infrastructure",
        "api",
        "bootstrap",
        # Paquets hors des cinq couches : outillage (`atlas` — ADR-0085 —, `release`), tests et
        # migrations. La denylist ne protège que ce qu'on a pensé à y écrire, et il en manquait
        # **quatre** : chacun était importable depuis `domain/` sans que le hook, la CI ni la revue
        # ne le voient. `release` en particulier — « outillage du binaire de release » — est la
        # catégorie exacte qui a justifié l'ajout d'`atlas`.
        # L'inversion en liste blanche (« le domaine n'importe que la stdlib et lui-même ») serait
        # le remède structurel ; elle relève d'un ADR, pas d'une ligne ajoutée en revue.
        "atlas",
        "release",
        "tests",
        "migrations",
    }
)


def test_les_paquets_hors_couches_sont_dans_la_denylist() -> None:
    """Ancre les quatre ajouts : sans eux, `domain/` pouvait les importer en silence."""
    assert _forbidden_imports("import atlas") == {"atlas"}
    assert _forbidden_imports("from release.chemins import x") == {"release"}


def _forbidden_imports(source: str) -> set[str]:
    """Renvoie les modules interdits importés dans `source` (vide si le domaine est pur)."""
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in _FORBIDDEN_ROOTS:
                    found.add(root)
        elif isinstance(node, ast.ImportFrom):
            if node.level >= 2:
                # Import relatif remontant au-dessus de domain/ → sort de la couche.
                found.add(f"import relatif (niveau {node.level})")
            elif node.module is not None:
                root = node.module.split(".", 1)[0]
                if root in _FORBIDDEN_ROOTS:
                    found.add(root)
    return found


def test_domain_layer_exists() -> None:
    """Les couches sont posées : la couche domaine existe (CA E00US004)."""
    assert _DOMAIN_DIR.is_dir(), "La couche domain/ doit exister."


def test_domain_stays_pure() -> None:
    """Aucun module de domain/ n'importe un framework ni une autre couche."""
    violations: dict[str, set[str]] = {}
    for path in sorted(_DOMAIN_DIR.rglob("*.py")):
        forbidden = _forbidden_imports(path.read_text(encoding="utf-8"))
        if forbidden:
            violations[path.relative_to(_BACKEND_ROOT).as_posix()] = forbidden
    detail = "; ".join(
        f"{file} → {', '.join(sorted(mods))}" for file, mods in sorted(violations.items())
    )
    assert not violations, f"Le domaine doit rester pur (ADR-0003). Imports interdits : {detail}"


def test_checker_detects_violations() -> None:
    """Le détecteur lui-même attrape bien les imports interdits (et laisse passer les licites)."""
    assert _forbidden_imports("import fastapi") == {"fastapi"}
    assert _forbidden_imports("from sqlalchemy.orm import Session") == {"sqlalchemy"}
    assert _forbidden_imports("from application.services import placer") == {"application"}
    assert _forbidden_imports("from ..infrastructure import db") == {"import relatif (niveau 2)"}
    # Imports licites : stdlib et modules internes au domaine.
    assert _forbidden_imports("import dataclasses\nfrom . import regles") == set()
