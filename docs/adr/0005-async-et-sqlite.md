# ADR-0005 — Accès SQLite : lectures synchrones + file d'écriture (single-writer)

- **Statut** : Accepté
- **Date** : 2026-07-08
- **Décideurs** : Organisateur / Architecte

## Contexte et problème

Le serveur (FastAPI) sert ~30 clients simultanés en LAN : **surtout des lectures** (consultation, écran projeté, live) et des **écritures ponctuelles** à la validation des scores, diffusées en temps réel par WebSocket. La base est **SQLite** (fichier local, cf. ADR-0002). SQLite n'accepte **qu'un seul écrivain** à la fois : mal maîtrisé, cela provoque des erreurs `database is locked` en pleine compétition.

## Options envisagées

- **Async de bout en bout** (aiosqlite) + verrou applicatif sur les écritures : homogène avec FastAPI, mais SQLite ne tire aucun gain de parallélisme d'écriture de l'async, et le verrou applicatif reste à gérer à la main.
- **Accès DB synchrones + file d'écriture (queue) consommée par un writer unique** : sérialise les écritures par construction, découple l'écriture de la requête.
- Passer à PostgreSQL : lèverait la contrainte single-writer mais contredit ADR-0002 (simplicité, sauvegarde = copie de fichier) sans justification à ce volume.

## Décision

- **Pas d'accès DB asynchrone.** FastAPI reste async au niveau **I/O réseau / WebSocket / connexions**, mais la couche de persistance est **synchrone** (SQLAlchemy sync).
- **Écritures via une file (queue) consommée par un unique writer** :
  - les handlers **publient une commande d'écriture** dans la file et attendent son résultat (future) ;
  - un **seul worker** exécute les écritures **séquentiellement** → sérialisation native, pas de contention, pas de `database is locked` ;
  - le point d'écriture unique est l'endroit naturel pour **journaliser l'audit** et **déclencher la diffusion WebSocket** après commit.
- **Lectures** : directes/synchrones, exécutées **hors de la boucle événementielle** (threadpool/executor) pour ne pas la bloquer ; **mode WAL** activé (lectures concurrentes non bloquées par l'écriture en cours).
- **Transactions courtes** ; aucune logique métier longue dans une transaction ouverte.
- Le **domaine reste pur et synchrone** ; la file et les accès DB vivent dans les **adapters** (infrastructure), derrière les ports repository.

## Conséquences

- **+** Sérialisation des écritures **explicite et simple à raisonner** (une file, un writer) — élimine les locks.
- **+** Point de passage unique idéal pour audit métier et diffusion temps réel post-commit.
- **+** Découple la latence d'écriture de la requête ; permet éventuellement de **batcher**.
- **−** Débit d'écriture **sériel** (borné) — acceptable car les écritures sont ponctuelles (validation de volée/match), pas massives.
- **−** Complexité à outiller : gestion des futures/erreurs de la file, backpressure, **arrêt propre** (drain de la file à la fermeture).
- **−** Le pont async→sync (executor) doit être maîtrisé pour ne pas bloquer la boucle.
- **⚠** À valider par un **test de charge** (30 clients) ; si le débit d'écriture sériel devenait insuffisant, réévaluer PostgreSQL (nouvel ADR).

## Liens
`guide-architecture.md` §7 ; `cahier-des-charges-technique.md` §11 ; ADR-0002, ADR-0003.
