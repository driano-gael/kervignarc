"""Porte mécanique locale : les vérifications de `ci.yml`, en deux étages (ADR-0110).

`--rapide` (~50 s) tient dans une boucle d'implémentation et parallélise ses trois groupes ;
sans option, tout est joué, **en séquentiel** — le parallèle y est plus lent (ADR-0110 §3).

    python porte.py --rapide
"""

from __future__ import annotations

import argparse
import dataclasses
import io
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

# ⚠️ Un sous-dossier par processus : ce projet fait tourner des agents concurrents dans le même
# arbre de travail, et deux portes simultanées qui partagent un journal rendent un rapport
# « verbatim » qui ment. Le tableau final imprime le chemin, personne n'a donc à le deviner.
SORTIES = RACINE / ".porte" / str(os.getpid())

LIMITE_PAR_DEFAUT = 1800


@dataclasses.dataclass(frozen=True)
class Verification:
    nom: str
    commande: tuple[str, ...]
    dossier: str
    ligne_ci: str
    rapide: bool = False
    essais: int = 1
    environnement: tuple[tuple[str, str], ...] = ()
    limite: int = LIMITE_PAR_DEFAUT


# ⚠️ Le job `backend` de la CI **ne construit pas le front** : `npm run build` vit dans un autre
# job. En local `frontend/dist/` existe — cette porte le reconstruit elle-même — et fait monter la
# SPA à la racine, qui attrape des requêtes que le serveur nu laisserait tomber et **change des
# codes de réponse** (404 par repli SPA au lieu de 405). Sans cette variable, `pytest` serait vert
# ici et rouge en CI sans qu'une ligne de code ait bougé (constaté le 29/08/2026 sur E16US010).
SANS_BUILD_FRONT = (("KERVIGNARC_FRONTEND_DIST", str(RACINE / ".porte" / "dist-absent")),)


def _python_du_venv() -> str:
    # ⚠️ La porte se lance `python backend/porte.py` depuis la racine, et ce `python` est
    # souvent celui du **système** — qui n'a ni ruff, ni mypy, ni pytest : tout le groupe
    # backend sortirait rouge sur « No module named ruff ». On cherche donc le venv à côté de
    # ce fichier, plutôt que d'écrire un chemin de poste dans la commande prescrite.
    for relatif in ("Scripts/python.exe", "bin/python"):
        candidat = Path(__file__).resolve().parent / ".venv" / relatif
        if candidat.is_file():
            return str(candidat)
    return sys.executable


# ⚠️ `ligne_ci` cite la ligne `run:` correspondante de `ci.yml`, à la lettre.
# `tests/test_porte_couvre_la_ci.py` compare les deux listes **et** confronte `ligne_ci` à
# `commande` : une étiquette qui ne décrit plus ce qui est lancé fait rougir un test. Sans cette
# seconde confrontation, la citation serait déclarée au lieu d'être vérifiée (ADR-0110 §5).
PY = (_python_du_venv(),)

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
    Verification(
        "pytest", (*PY, "-m", "pytest"), "backend", "pytest", environnement=SANS_BUILD_FRONT
    ),
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
        limite=300,
    ),
)

GROUPES: dict[str, tuple[Verification, ...]] = {
    "backend": BACKEND,
    "atlas": ATLAS,
    "frontend": FRONTEND,
}

# L'étage rapide restreint pytest au domaine, au service et à l'oracle : 2738 tests en ~23 s,
# contre ~460 s pour la suite. La sélection passe par un marqueur et jamais par une liste de
# chemins — 67 chemins en arguments coûtent 13,2 s de collecte là où le répertoire entier en
# coûte 7,5 (mesuré le 19/09/2026 sur Windows). Ces 7,5 s restent payées ici : DETTE-105.
# ⚠️ La famille `atlas` en est **exclue** : 43,8 s mesurées, elle doublerait l'étage. Les
# cliquets documentaires de `test_atlas_corpus` ne sont donc pas joués par `--rapide`.
PYTEST_RAPIDE = Verification(
    "pytest (domaine + service + oracle)",
    (*PY, "-m", "pytest", "-m", "domaine or service or oracle"),
    "backend",
    "",
    True,
    environnement=SANS_BUILD_FRONT,
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
                timeout=verification.limite,
            )
        except (OSError, subprocess.TimeoutExpired) as erreur:
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


def _rendre_compte(resultats: list[Resultat], groupes: dict[str, tuple[Verification, ...]]) -> None:
    # ⚠️ Le dénominateur est le total de `GROUPES`, **jamais** celui de la sélection : compter
    # la sélection ferait afficher « 6/6 » à un étage rapide amputé de huit vérifications, ce
    # qui est exactement le faux vert que ce compte existe pour interdire.
    attendues = sum(len(v) for v in GROUPES.values())
    joues = {r.nom for r in resultats}
    absentes = [v.nom for groupe in groupes.values() for v in groupe if v.nom not in joues]
    non_selectionnees = [v.nom for groupe in GROUPES.values() for v in groupe if v.nom not in joues]
    print(f"\n  total — {len(resultats)}/{attendues} lancées — journaux : {SORTIES}")
    if absentes:
        print(f"  arrêtées par un rouge de leur groupe : {', '.join(absentes)}")
    restantes = [n for n in non_selectionnees if n not in absentes]
    if restantes:
        print(f"  hors de cet étage : {', '.join(restantes)}")


def main() -> int:
    # ⚠️ La console Windows est en cp1252 : un seul caractère hors de cette table dans un nom de
    # vérification faisait planter la porte **à l'affichage du tableau**, après que tout avait
    # tourné — et le plantage restait masqué tant qu'un groupe s'arrêtait plus tôt sur un rouge.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument(
        "--rapide", action="store_true", help="étage rapide (~50 s) — ne fonde aucun verdict de PR"
    )
    mode = analyseur.add_mutually_exclusive_group()
    mode.add_argument(
        "--sequentiel", action="store_true", help="forcer le séquentiel (mesure ADR-0110 §3)"
    )
    mode.add_argument(
        "--parallele",
        action="store_true",
        help="forcer le parallèle — plus LENT à l'étage complet (ADR-0110 §3), pas en routine",
    )
    options = analyseur.parse_args()

    manquants = [
        outil
        for outil in ("ruff", "mypy", "pytest")
        if subprocess.run((*PY, "-c", f"import {outil}"), capture_output=True).returncode != 0
    ]
    if manquants:
        print(f"{PY[0]} n'a pas {', '.join(manquants)} : venv incomplet, pas un diff cassé.")
        return 2

    try:
        SORTIES.mkdir(parents=True, exist_ok=True)
    except OSError as erreur:
        print(f"journaux impossibles à écrire dans {SORTIES} : {erreur}", file=sys.stderr)
        return 2

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

    largeur = max((len(r.nom) for r in resultats), default=0)
    print(f"\n{'PORTE RAPIDE' if options.rapide else 'PORTE COMPLÈTE'}\n")
    for resultat in sorted(resultats, key=lambda r: r.nom):
        etat = "OK  " if resultat.code == 0 else "ROUGE"
        print(f"  {etat}  {resultat.nom:<{largeur}}  {resultat.duree:6.1f} s")

    _rendre_compte(resultats, groupes)
    rouges = [r for r in resultats if r.code != 0]
    print(f"  durée {total:.1f} s — {len(rouges)} rouge(s)")
    for resultat in rouges:
        print(f"\n--- {resultat.nom} ---\n{resultat.journal}")
    return 1 if rouges else 0


if __name__ == "__main__":
    raise SystemExit(main())
