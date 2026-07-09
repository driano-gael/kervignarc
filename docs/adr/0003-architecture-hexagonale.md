# ADR-0003 — Architecture hexagonale ciblée + composition root explicite

- **Statut** : Accepté
- **Date** : 2026-07-08
- **Décideurs** : Organisateur / Architecte

## Contexte et problème

Le cœur de valeur et de risque du produit est le **moteur métier** (phases, placement, classement 1→N). Il est complexe, doit être testé exhaustivement (oracle du tournoi 120) et rester stable pendant que l'infrastructure (API, DB, PDF) évolue. Il faut éviter que la logique métier se retrouve diluée dans les routes FastAPI ou les modèles ORM.

## Options envisagées

- **Hexagonal ciblé** : domaine pur + ports/adapters, câblage par composition root explicite.
- Couches souples (pragmatique) : ORM/Pydantic autorisés dans le domaine — couplage plus fort, tests plus lourds.
- Monolithe sans couches : vélocité initiale, dette rapide sur un moteur subtil.
- Conteneur d'injection de dépendances (dependency-injector…) : outillé mais « magique », graphe de dépendances moins lisible.

## Décision

- **Architecture hexagonale ciblée sur le domaine** : `domain/` est **pur** (aucune dépendance à FastAPI, SQLAlchemy, Pydantic ni aux couches externes). Les dépendances pointent **vers le domaine**.
- Le domaine expose des **ports** (interfaces : repositories, stores) ; l'infrastructure fournit les **adapters**.
- **Composition root explicite** : le câblage des adapters et des politiques se fait **à la main** dans `bootstrap/` + `main.py`, **sans conteneur DI**.
- Les `Depends` FastAPI restent **cantonnés à la couche API**.
- Pragmatisme assumé **hors** du domaine (infrastructure simple, pas de sur-abstraction).

## Conséquences

- **+** Domaine testable en isolation, sans base ni serveur.
- **+** Graphe de dépendances lisible et debuggable (tout le câblage au même endroit).
- **+** Remplacement d'un adapter (ex. moteur PDF) sans toucher au domaine.
- **−** Mapping DTO ↔ domaine ↔ persistance à écrire (cérémonie).
- **−** Exige de la discipline : la règle « le domaine n'importe rien d'externe » doit être tenue en revue (lint d'imports possible).

## Liens
`guide-architecture.md` §2 ; `cahier-des-charges-technique.md` §4 ; ADR-0004, ADR-0007.
