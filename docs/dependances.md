# Registre des dépendances externes

> Registre **obligatoire** de toutes les librairies externes **directes** du projet (runtime et dev).
> Règle : toute dépendance ajoutée doit être **justifiée**, **sûre** et **inscrite ici** dans le même
> commit que son introduction. Voir [`../guide-architecture.md`](../guide-architecture.md) §3 et
> [ADR-0009](adr/0009-gouvernance-dependances.md).
>
> Seules les dépendances **directes** (choisies explicitement) sont listées ; les transitives sont
> figées par les lockfiles (`requirements.txt`, `package-lock.json`). Versions de référence :
> manifestes (`backend/pyproject.toml`, `frontend/package.json`). Licences toutes **permissives**.
>
> **Audits de sécurité** (bloquants en CI, cf. `.github/workflows/ci.yml`, E00US003) — dernier contrôle
> 2026-07-10 : `pip-audit -r requirements.txt --strict` = **aucune vulnérabilité** ; `npm audit
> --audit-level=high` = **0 vulnérabilité**. Outils d'audit eux-mêmes : `pip-audit` est installé
> **ad hoc dans la CI** (non embarqué dans les manifestes applicatifs) ; `npm audit` est intégré à npm.

## Backend — runtime (`backend/pyproject.toml` › `dependencies`)

| Librairie | Version | Rôle | Justification | Licence |
|---|---|---|---|---|
| `fastapi` | 0.139.0 | Framework API (REST + WebSocket), validation Pydantic | Socle serveur acté ([ADR-0002](adr/0002-stack-et-topologie.md)) : async, WebSocket natif, typage, sert les statiques front | MIT |
| `uvicorn[standard]` | 0.51.0 | Serveur ASGI exécutant FastAPI | Serveur de référence pour FastAPI ; `[standard]` = websockets + boucle performante | BSD-3-Clause |
| `sqlalchemy` | 2.0.51 | ORM / Core SQL **synchrone** (accès SQLite, WAL) | Accès DB sync acté ([ADR-0005](adr/0005-async-et-sqlite.md)) ; Core+ORM typés, repositories derrière les ports (E00US006/009) | MIT |
| `alembic` | 1.18.5 | Migrations de schéma versionnées | Schéma versionné et testé (guide §7) ; standard de fait pour SQLAlchemy | MIT |

## Backend — développement (`backend/pyproject.toml` › `optional-dependencies.dev`)

| Librairie | Version | Rôle | Justification | Licence |
|---|---|---|---|---|
| `ruff` | 0.8.6 | Lint **+** format Python | Un seul outil rapide remplace flake8+isort+black ; qualité bloquante (guide §5) | MIT |
| `mypy` | 1.14.1 | Typage statique strict | Exigence « mypy strict » (guide §5) ; fiabilité du domaine | MIT |
| `pytest` | 9.1.1 | Framework de tests | Standard de fait ; stratégie de tests (guide §9) | MIT |
| `httpx` | 0.28.1 | Client HTTP (tests) | Requis par `fastapi.testclient` pour tester l'API | BSD-3-Clause |
| `pre-commit` | 4.0.1 | Orchestration des hooks git | Rend la qualité bloquante avant commit (guide §5) | MIT |

## Frontend — runtime (`frontend/package.json` › `dependencies`)

| Librairie | Version | Rôle | Justification | Licence |
|---|---|---|---|---|
| `react` | ^19.2 | Bibliothèque UI | SPA riche (temps réel, glisser-déposer) actée ([ADR-0002](adr/0002-stack-et-topologie.md)) | MIT |
| `react-dom` | ^19.2 | Rendu DOM de React | Indispensable à React côté navigateur | MIT |
| `@tanstack/react-query` | ^5.101 | État **serveur** : fetch, cache, invalidation, intégration temps réel | Patron état-serveur acté (guide §8) ; invalidation pilotée par le WebSocket (E00US010) | MIT |
| `zustand` | ^5.0 | État **UI** local léger | État UI acté (guide §8) ; ex. statut de connexion (E00US010), sans boilerplate Redux | MIT |

## Frontend — développement (`frontend/package.json` › `devDependencies`)

| Librairie | Version | Rôle | Justification | Licence |
|---|---|---|---|---|
| `vite` | ^8.1 | Build & serveur de dev | Outil de build acté ([ADR-0002](adr/0002-stack-et-topologie.md)) ; HMR rapide | MIT |
| `@vitejs/plugin-react` | ^6.0 | Support React (Fast Refresh) pour Vite | Officiel Vite/React | MIT |
| `vitest` | ^4.1 | Runner de tests unitaires (front) | Premier runner de test du front (E00US014) ; runner natif de Vite (réutilise `vite.config.ts`, zéro config) ; résorbe [DETTE-005](dette.md) en couvrant `format.ts` (conversion euros↔centimes, [ADR-0012](adr/0012-argent-en-centimes-entiers.md)) | MIT |
| `typescript` | ~6.0 | Compilateur TypeScript (typage strict) | Exigence TS strict (guide §5) | Apache-2.0 |
| `eslint` | ^10.6 | Linter JS/TS | Exigence ESLint (guide §5) | MIT |
| `@eslint/js` | ^10.0 | Règles de base ESLint (flat config) | Recommandations officielles ESLint | MIT |
| `typescript-eslint` | ^8.63 | Parser + règles ESLint pour TypeScript | Lint type-aware du TS | MIT |
| `eslint-plugin-react-hooks` | ^7.1 | Règles des Hooks React | Évite les bugs classiques de Hooks | MIT |
| `eslint-plugin-react-refresh` | ^0.5 | Compat Fast Refresh (Vite) | Garde-fou HMR en dev | MIT |
| `eslint-config-prettier` | ^10.1 | Désactive les règles ESLint en conflit avec Prettier | Sépare lint (ESLint) et format (Prettier) | MIT |
| `prettier` | ^3.9 | Formateur de code | Exigence Prettier (guide §5) | MIT |
| `globals` | ^17.7 | Déclarations de variables globales (env navigateur) | Requis par la flat config ESLint | MIT |
| `@types/react` | ^19.2 | Types TypeScript de React | Typage strict des composants | MIT |
| `@types/react-dom` | ^19.2 | Types TypeScript de react-dom | Typage strict du rendu | MIT |
| `@types/node` | ^24.13 | Types Node (config Vite) | Typage de `vite.config.ts` / outillage | MIT |

## Procédure d'ajout d'une dépendance

1. **Vérifier le besoin** (parcimonie) : la stdlib ou quelques lignes maison suffisent-elles ?
2. **Vérifier la sûreté** : maintenue, adoptée, licence permissive, source officielle, audit vert.
3. **Déclarer** dans le manifeste (`pyproject.toml` puis `pip freeze --exclude-editable > requirements.txt`,
   ou `npm install`) — **même commit**.
4. **Documenter** ici (ligne du tableau adéquat) — **même commit**.
5. **Signaler en revue de PR** ; si structurante → **ADR** dédié.
