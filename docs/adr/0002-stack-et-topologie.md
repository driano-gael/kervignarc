# ADR-0002 — Stack technique & topologie de déploiement

- **Statut** : Accepté
- **Date** : 2026-07-08
- **Décideurs** : Organisateur / Architecte

## Contexte et problème

Application de gestion de tournoi de tir à l'arc en salle, utilisée **le jour J dans un gymnase sans internet**, avec ~30 tablettes de saisie (BYOD, via navigateur), un écran projeté et le public. Un prototype Python de domaine existe déjà (`blason.py`, `player.py`). Le livrable vise **un seul club** (pas de multi-tenant). L'organisateur n'est pas nécessairement technicien.

## Options envisagées

- **Backend Python (FastAPI) + front React (SPA), SQLite, serveur local sur portable, exécutable double-clic.**
- Stack JS full-stack (Node) : abandonnerait le prototype de domaine Python déjà écrit.
- Application offline-first (chaque tablette autonome + synchronisation) : robuste sans wifi mais complexité de résolution de conflits injustifiée pour un LAN maîtrisé.
- SaaS cloud : incompatible avec la contrainte « sans internet ».

## Décision

- **Backend** : Python **FastAPI**, réutilisant/étendant le domaine existant.
- **Frontend** : **React + TypeScript** (SPA, Vite), servi en statique par le backend.
- **Base** : **SQLite** (fichier local).
- **Topologie** : **serveur-autoritaire sur LAN** ; le serveur tourne sur le **PC portable** de l'organisateur, connecté à un **routeur wifi dédié** ; les clients sont en **navigateur (BYOD)**.
- **Temps réel** : **WebSocket**.
- **Livraison** : **exécutable auto-contenu** (PyInstaller), lancement double-clic ; **outil mono-club**.
- **Tolérance réseau** : coupures **brèves** seulement (file d'attente côté front + reconnexion), pas d'offline-first.

## Conséquences

- **+** Réutilise l'acquis Python ; un seul processus à déployer ; sauvegarde = copie de fichier.
- **+** BYOD via navigateur = aucun logiciel à installer sur les tablettes.
- **−** SQLite impose une discipline d'écriture (voir [ADR-0005](0005-async-et-sqlite.md)).
- **−** Le hotspot doit être un **routeur dédié** (pas le partage du portable) pour tenir 30 clients.
- **−** Packaging (PyInstaller + front embarqué + dépendances PDF) à valider tôt (risque R4 du CDC technique).

## Liens
`cahier-des-charges-technique.md` §1, §3, §8 ; ADR-0005.
