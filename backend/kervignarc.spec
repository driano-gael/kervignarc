# -*- mode: python ; coding: utf-8 -*-
"""Spec PyInstaller du binaire de release Kervignarc (E11US001).

Produit un exécutable **onefile** auto-contenu (`dist/kervignarc[.exe]`) embarquant :
le front React déjà buildé, les migrations Alembic, les ressources ReportLab (PDF) et la
pile mDNS zeroconf. Point d'entrée : `run.py`.

Build : `python build_release.py` (enchaîne `npm run build` puis PyInstaller). Ne pas
lancer PyInstaller à la main sans avoir un `frontend/dist/` à jour — cf. docs/deploiement.md.

Deux catégories de contenu qu'une simple analyse d'imports **ne verrait pas** :
- des **données** chargées dynamiquement (migrations `env.py`/`versions`, front statique,
  polices ReportLab) → `datas` ;
- des **modules importés par nom** à l'exécution (boucles/protocoles uvicorn, scripts de
  migration référencés par chemin, nos adapters câblés dans la composition root) →
  `hiddenimports` + `collect_submodules`.
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = []
binaries = []
hiddenimports = []

# --- Données embarquées (lecture seule, dépaquetées sous _MEIPASS au lancement) ----------
# Migrations Alembic : env.py + versions/*.py, chargés par chemin → invisibles à l'analyse.
datas += [("migrations", "migrations"), ("alembic.ini", ".")]
# Front React déjà buildé : servi en statique par FastAPI (KERVIGNARC_FRONTEND_DIST).
datas += [("../frontend/dist", "frontend/dist")]

# --- Modules chargés dynamiquement -------------------------------------------------------
# Nos packages : adapters/services câblés à la main dans la composition root, scripts de
# migration important `infrastructure.db.*`, point d'entrée release.
for paquet in ("domain", "application", "infrastructure", "api", "bootstrap", "release"):
    hiddenimports += collect_submodules(paquet)

# Dépendances à **collecte totale** (données + sous-modules importés par nom + extensions).
# `reportlab` en fait partie : son module code-barres importe `...barcode.code128` etc. par
# `eval` — invisible à l'analyse statique, d'où un `collect_submodules`, pas juste les données.
for paquet in ("uvicorn", "alembic", "zeroconf", "reportlab"):
    d, b, h = collect_all(paquet)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ["run.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

# Onefile : un unique exécutable, pratique à déployer (« double-clic »). La base SQLite est
# écrite **à côté** de l'exe (release/chemins.py), pas dans le dossier temporaire volatile.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="kervignarc",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
