# Kervignarc

Solution logicielle de **gestion de tournoi de tir à l'arc en salle (18 m)** : configuration,
inscriptions, placement des cibles, saisie temps réel des scores (~30 tablettes BYOD), moteur de
phases configurable (qualification, duels, placement intégral 1→N) et classements en direct.

Outil **interne mono-club**, déployé le jour J sur un **réseau local sans internet** : un backend
FastAPI (serveur autoritaire) sert une SPA React et diffuse les mises à jour par WebSocket.

## Stack

- **Backend** : Python 3.13 · FastAPI · Uvicorn · SQLite/SQLAlchemy · Alembic *(ajoutés au fil des US)*.
- **Frontend** : React + TypeScript (Vite).
- **Outillage** : `venv`/`pip` (Python) · `npm` (front). *Voir [ADR-0008](docs/adr/0008-outillage-npm-venv.md) — écart assumé au choix initial uv/pnpm.*

## Prérequis

- **Python ≥ 3.13** et **Node ≥ 20** (testé avec Node 24).
- Git.

## Structure du dépôt

```
kervignarc/
├── backend/            # API FastAPI + domaine métier (architecture hexagonale)
│   ├── domain/         #   cœur métier PUR (aucune dépendance framework)
│   ├── application/    #   cas d'usage
│   ├── infrastructure/ #   adapters sortants (DB, PDF, import…)
│   ├── api/            #   routers REST /api/v1 + WebSocket
│   ├── bootstrap/      #   composition root (câblage explicite)
│   ├── tests/
│   ├── main.py         #   point d'entrée
│   ├── pyproject.toml  #   source de vérité des dépendances Python
│   └── requirements.txt#   gel des versions (généré, non édité à la main)
├── frontend/           # SPA React + TS (Vite)
├── docs/               # glossaire, modèle de données, référentiel FFTA, ADR (docs/adr/)
├── epics/  stories/    # backlog produit (EPICs et user stories)
├── prototype/          # prototype Python de déc. 2024 (référence, non exécuté)
└── *.md                # cahiers des charges + guide d'architecture
```

Détail des règles de contribution : [`guide-architecture.md`](guide-architecture.md).

## Démarrage — backend

```bash
cd backend
python -m venv .venv
# Windows (PowerShell) : .venv\Scripts\Activate.ps1
# Windows (Git Bash)   : source .venv/Scripts/activate
# macOS / Linux        : source .venv/bin/activate
pip install -e ".[dev]"       # installe FastAPI + outils de dev
uvicorn main:app --reload     # http://127.0.0.1:8000  (santé : /health)
pytest                        # exécute les tests
```

> **Dépendances** : `pyproject.toml` est la **source de vérité**. Après tout ajout/retrait de lib,
> régénérer le gel : `pip freeze --exclude-editable > requirements.txt` (ne jamais l'éditer à la main).

## Démarrage — frontend

```bash
cd frontend
npm install
npm run dev          # serveur de dev Vite (http://127.0.0.1:5173)
npm run build        # build de production (frontend/dist/)
npm run lint         # ESLint
npm run format       # Prettier (écriture) — format:check pour vérifier seulement
npm run typecheck    # TypeScript strict (tsc -b)
```

## Qualité & pre-commit

La qualité est **automatisée et bloquante** (cf. [`guide-architecture.md`](guide-architecture.md) §5) :

- **Backend** : `ruff` (lint + format) et `mypy --strict` — configurés dans `backend/pyproject.toml`.
- **Frontend** : `ESLint` (flat config) + `Prettier` + TypeScript `strict`.
- **Hooks pre-commit** : `.pre-commit-config.yaml` (racine) lance ruff, mypy, eslint, prettier avant
  chaque commit.

Activation (une fois, après avoir créé le venv backend et fait `npm install`) :

```bash
pip install -e "backend[dev]"     # fournit l'outil pre-commit
pre-commit install                # installe le hook git
pre-commit run --all-files        # (optionnel) vérifie tout le dépôt
```

## Développement

- **Une branche par user story** : `<type>/<ExxUSyyy>-<slug>` (ex. `feat/e04us003-saisie-fleches`).
  Voir le backlog [`stories/README.md`](stories/README.md) et le [`guide-architecture.md`](guide-architecture.md) §11.
- **Vocabulaire** : métier en français (FFTA), technique en anglais (voir [`docs/glossaire.md`](docs/glossaire.md)).
- **Décision structurante** ⇒ un ADR dans [`docs/adr/`](docs/adr/).

## Documentation

| Document | Contenu |
|---|---|
| [`cahier-des-charges.md`](cahier-des-charges.md) | Besoin fonctionnel |
| [`cahier-des-charges-technique.md`](cahier-des-charges-technique.md) | Architecture technique |
| [`cahier-des-charges-design.md`](cahier-des-charges-design.md) | Design & ergonomie |
| [`guide-architecture.md`](guide-architecture.md) | Conventions de code & workflow |
| [`moteur-placement-lucky-loser.md`](moteur-placement-lucky-loser.md) | Formalisation du moteur de placement |
| [`docs/dependances.md`](docs/dependances.md) | Registre des dépendances externes (obligatoire à l'ajout d'une lib) |
| [`docs/adr/`](docs/adr/) | Décisions d'architecture (ADR) |
| [`epics/`](epics/) · [`stories/`](stories/) | Backlog produit |
