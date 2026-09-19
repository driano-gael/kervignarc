"""Porte mécanique locale : les vérifications de `ci.yml`, en deux étages (ADR-0110).

`--rapide` (~46 s) tient dans une boucle d'implémentation ; sans option, tout est joué.
Les trois groupes tournent en parallèle, comme les trois jobs GitHub.

    python porte.py --rapide
"""

from __future__ import annotations

import argparse
import dataclasses
import io
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SORTIES = RACINE / ".porte"


@dataclasses.dataclass(frozen=True)
class Verification:
    nom: str
    commande: tuple[str, ...]
    dossier: str
    ligne_ci: str
    rapide: bool = False
    essais: int = 1


# ⚠️ `ligne_ci` est la ligne `run:` correspondante de `.github/workflows/ci.yml`, à la lettre.
# `tests/test_porte_couvre_la_ci.py` compare les deux listes : une vérification ajoutée à la
# CI sans l'être ici fait rougir ce test. C'est ce qui tient les deux fichiers ensemble —
# sans lui, la porte locale passerait au vert sur un dépôt que la CI refuse (ADR-0110).
PY = (sys.executable,)

BACKEND: tuple[Verification, ...] = (
    Verification("ruff (lint)", (*PY, "-m", "ruff", "check", "."), "backend", "ruff check .", True),
    Verification(
        "ruff (format)",
        (*PY, "-m", "ruff", "format", "--check", "."),
        "backend",
        "ruff format --check .",
        True,
    ),
    Verification("mypy (strict)", (*PY, "-m", "mypy", "."), "backend", "mypy .", True),
    Verification("pytest", (*PY, "-m", "pytest"), "backend", "pytest"),
    Verification(
        "requirements sync",
        (*PY, "verifier_requirements.py"),
        "backend",
        "python verifier_requirements.py",
    ),
    Verification(
        "pip-audit",
        (*PY, "-m", "pip_audit", "-r", "requirements.txt", "--strict"),
        "backend",
        "pip-audit -r requirements.txt --strict",
    ),
)

ATLAS: tuple[Verification, ...] = (
    Verification(
        "atlas à jour",
        (*PY, "-m", "atlas", "--verifier"),
        "backend",
        "python -m atlas --verifier",
        True,
    ),
)

FRONTEND: tuple[Verification, ...] = (
    Verification("npm ci", ("npm", "ci"), "frontend", "npm ci"),
    Verification("eslint", ("npm", "run", "lint"), "frontend", "npm run lint"),
    Verification("prettier", ("npm", "run", "format:check"), "frontend", "npm run format:check"),
    Verification(
        "typecheck (tsc)", ("npm", "run", "typecheck"), "frontend", "npm run typecheck", True
    ),
    Verification("vitest", ("npm", "test"), "frontend", "npm test"),
    Verification("build", ("npm", "run", "build"), "frontend", "npm run build"),
    Verification(
        "npm audit",
        ("npm", "audit", "--audit-level=high", "--fetch-timeout=60000"),
        "frontend",
        "npm audit --audit-level=high --fetch-timeout=60000",
        essais=3,
    ),
)

GROUPES: dict[str, tuple[Verification, ...]] = {
    "backend": BACKEND,
    "atlas": ATLAS,
    "frontend": FRONTEND,
}

# L'étage rapide restreint pytest au domaine et au service : 2719 tests en ~19 s, contre
# ~445 s pour la suite. La sélection passe par un marqueur et jamais par une liste de
# chemins — 67 chemins en arguments coûtent 13,2 s de collecte là où le répertoire entier
# (249 fichiers) n'en coûte que 7,5 (mesuré le 19/09/2026 sur Windows). Ces 7,5 s restent
# payées ici, `-m` ne filtrant qu'après la collecte : DETTE-105.
PYTEST_RAPIDE = Verification(
    "pytest (domaine + service)",
    (*PY, "-m", "pytest", "-m", "domaine or service"),
    "backend",
    "",
    True,
)


@dataclasses.dataclass(frozen=True)
class Resultat:
    nom: str
    code: int
    duree: float
    journal: Path


def _resoudre(commande: tuple[str, ...]) -> tuple[str, ...]:
    # ⚠️ `npm` est un `.cmd` sous Windows : sans cette résolution, `subprocess` lève
    # `WinError 2` alors que la commande marche au terminal. `shutil.which` rend le chemin
    # complet et évite d'avoir à passer par `shell=True`, qui rouvrirait le quoting.
    chemin = shutil.which(commande[0])
    return (chemin or commande[0], *commande[1:])


def _executer(verification: Verification) -> Resultat:
    SORTIES.mkdir(exist_ok=True)
    journal = SORTIES / f"{verification.nom.replace(' ', '_').replace('/', '-')}.txt"
    debut = time.monotonic()
    code = 1
    for essai in range(verification.essais):
        try:
            issue = subprocess.run(
                _resoudre(verification.commande),
                cwd=RACINE / verification.dossier,
                capture_output=True,
                shell=False,
            )
        except OSError as erreur:
            # Une porte qui plante est plus dangereuse qu'une porte rouge : l'échec d'une
            # vérification ne doit jamais emporter les autres groupes.
            journal.write_text(f"{verification.commande[0]} : {erreur}\n", encoding="utf-8")
            return Resultat(verification.nom, 1, time.monotonic() - debut, journal)
        code = issue.returncode
        journal.write_bytes(issue.stdout + issue.stderr)
        if code == 0:
            break
        if essai + 1 < verification.essais:
            time.sleep(15)
    return Resultat(verification.nom, code, time.monotonic() - debut, journal)


def _derouler(verifications: tuple[Verification, ...]) -> list[Resultat]:
    resultats: list[Resultat] = []
    for verification in verifications:
        resultat = _executer(verification)
        resultats.append(resultat)
        if resultat.code != 0:
            break
    return resultats


def _selection(rapide: bool) -> dict[str, tuple[Verification, ...]]:
    if not rapide:
        return GROUPES
    retenues: dict[str, tuple[Verification, ...]] = {}
    for groupe, verifications in GROUPES.items():
        gardees = tuple(v for v in verifications if v.rapide)
        if groupe == "backend":
            gardees = (*gardees, PYTEST_RAPIDE)
        if gardees:
            retenues[groupe] = gardees
    return retenues


def main() -> int:
    # ⚠️ La console Windows est en cp1252 : un seul caractère hors de cette table dans un nom de
    # vérification faisait planter la porte **à l'affichage du tableau**, après que tout avait
    # tourné — et le plantage restait masqué tant qu'un groupe s'arrêtait plus tôt sur un rouge.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--rapide", action="store_true", help="étage rapide")
    analyseur.add_argument("--sequentiel", action="store_true", help="forcer le séquentiel")
    analyseur.add_argument("--parallele", action="store_true", help="forcer le parallèle")
    options = analyseur.parse_args()

    # ⚠️ Le parallélisme n'est bénéfique **qu'à l'étage rapide** (46 s contre 68 s mesurés le
    # 19/09/2026). À l'étage complet il est contre-productif : `pytest` y domine et **double**
    # sous contention (479 s → 900 s) sur les 4 cœurs de la machine, si bien que le total monte
    # à 905 s contre 845 s en séquentiel. Ne pas « uniformiser » les deux étages (ADR-0110).
    en_parallele = options.parallele or (options.rapide and not options.sequentiel)

    groupes = _selection(options.rapide)
    debut = time.monotonic()
    if en_parallele:
        with ThreadPoolExecutor(max_workers=len(groupes)) as executeur:
            resultats = [r for lot in executeur.map(_derouler, groupes.values()) for r in lot]
    else:
        resultats = [r for lot in groupes.values() for r in _derouler(lot)]
    total = time.monotonic() - debut

    largeur = max(len(r.nom) for r in resultats)
    print(f"\n{'PORTE RAPIDE' if options.rapide else 'PORTE COMPLÈTE'}\n")
    for resultat in sorted(resultats, key=lambda r: r.nom):
        etat = "OK  " if resultat.code == 0 else "ROUGE"
        print(f"  {etat}  {resultat.nom:<{largeur}}  {resultat.duree:6.1f} s")

    rouges = [r for r in resultats if r.code != 0]
    attendues = sum(len(v) for v in groupes.values())
    print(f"\n  total {total:.1f} s — {len(resultats)}/{attendues} lancées, {len(rouges)} rouge(s)")
    for resultat in rouges:
        print(f"\n--- {resultat.nom} ---\n{resultat.journal}")
    return 1 if rouges else 0


if __name__ == "__main__":
    raise SystemExit(main())
