# EPIC-00 — Socle technique & walking skeleton

- **ID** : EPIC-00
- **Statut** : À planifier
- **Priorité** : MVP (prérequis)
- **Dépend de** : —
- **Réfs** : `guide-architecture.md`, `docs/adr/` (0002, 0003, 0005)

## Objectif / valeur
Mettre en place le socle et **livrer très tôt une tranche verticale bout-en-bout** qui traverse toutes les couches. Objectif : valider l'architecture hexagonale, la file d'écriture SQLite, le temps réel et le packaging **avant** d'investir dans la richesse fonctionnelle.

## Périmètre
### Inclus
- Monorepo `backend/` + `frontend/`, outillage **uv** + **pnpm/Vite**.
- Squelette hexagonal : `domain/` pur, `application/`, `infrastructure/`, `api/`, `bootstrap/` (composition root explicite).
- Persistance : SQLite (WAL) + **file d'écriture / writer unique**, repositories, migrations Alembic.
- API FastAPI + canal **WebSocket** ; shell React + React Query/Zustand.
- Qualité : mypy strict, ruff, TS strict, ESLint/Prettier, pre-commit, **CI bloquante**.
- **Tranche verticale démo** : créer un tournoi → ajouter 1 archer → le placer sur 1 cible → saisir 1 score → voir un classement se mettre à jour en live.
- Exécutable de dev lançable (base du packaging, cf. EPIC-11).

### Exclus
- Toute logique métier riche (déléguée aux EPICs suivants).

## Capacités
- [ ] Bootstrap du dépôt + outillage + CI.
- [ ] Squelette de couches + un port/adapter repository de bout en bout.
- [ ] File d'écriture opérationnelle + diffusion WebSocket post-commit.
- [ ] Tranche verticale démontrable.

## Critères d'acceptation (epic)
- La tranche verticale fonctionne bout-en-bout, temps réel inclus.
- CI verte (lint + typage strict + tests).
- Le `domain/` ne dépend d'aucun framework (vérifié).

## Risques
- Packaging (PyInstaller + front embarqué) : prototyper tôt (risque R4 du CDC technique).
- Pont async→sync + file d'écriture : valider le patron dès cette étape (ADR-0005).
