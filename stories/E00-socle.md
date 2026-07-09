# E00 — Socle technique & walking skeleton — User Stories

> EPIC : [EPIC-00](../epics/EPIC-00-socle-technique.md) · Jalon J0 · Réfs : `guide-architecture.md`, ADR-0002/0003/0005.

---

### E00US001 — Initialiser le monorepo + gestionnaires
*En tant que* développeur, *je veux* un dépôt structuré `backend/` + `frontend/` avec l'outillage, *afin de* démarrer sur des bases saines.
- **CA** : `uv` gère l'environnement Python ; `pnpm`+`Vite` initialisent le front ; `README` de démarrage ; versions figées.
- **Notes** : arborescence conforme au `guide-architecture.md` §3.
- **Dépend de** : —

### E00US002 — Configurer la qualité
*En tant que* développeur, *je veux* lint/format/typage automatiques, *afin de* garantir la qualité dès le 1er commit.
- **CA** : ruff (lint+format) + mypy strict côté Python ; ESLint + Prettier + TS strict côté front ; hooks **pre-commit** actifs.
- **Notes** : configs partagées et versionnées.
- **Dépend de** : E00US001

### E00US003 — CI bloquante
*En tant que* équipe, *je veux* une CI qui bloque le merge si la qualité échoue, *afin de* protéger la branche principale.
- **CA** : pipeline exécutant lint + typage + tests ; merge impossible si rouge.
- **Notes** : rapide (< quelques min) pour ne pas freiner.
- **Dépend de** : E00US002

### E00US004 — Squelette de couches + garde-fou d'imports
*En tant que* développeur, *je veux* les couches `domain/application/infrastructure/api` posées, *afin de* respecter l'hexagonal.
- **CA** : les 4 couches existent ; une règle (lint d'imports) **échoue** si `domain/` importe un framework ou une couche externe.
- **Notes** : cf. ADR-0003 ; test automatisé de la règle de dépendance.
- **Dépend de** : E00US001

### E00US005 — Composition root minimale
*En tant que* développeur, *je veux* un point de câblage explicite, *afin de* voir toutes les dépendances en un endroit.
- **CA** : `bootstrap/` assemble adapters + services ; aucun conteneur DI ; `main.py` démarre via le bootstrap.
- **Dépend de** : E00US004

### E00US006 — Connexion SQLite (WAL) + migration initiale
*En tant que* développeur, *je veux* la base opérationnelle en WAL avec migrations, *afin de* persister les données.
- **CA** : base créée en mode **WAL** ; **Alembic** applique une migration initiale ; connexion via un adapter d'infrastructure.
- **Notes** : cf. ADR-0005.
- **Dépend de** : E00US005

### E00US007 — File d'écriture + writer unique
*En tant que* système, *je veux* sérialiser les écritures via une file, *afin d'*éviter les `database is locked`.
- **CA** : une commande d'écriture est mise en file et exécutée par **un seul worker** ; l'appelant obtient le résultat (future) ; les lectures restent concurrentes.
- **Notes** : point de passage unique pour audit + diffusion (ADR-0005).
- **Dépend de** : E00US006

### E00US008 — Canal WebSocket + diffusion post-commit
*En tant que* client, *je veux* recevoir les mises à jour en direct, *afin de* voir l'état sans rafraîchir.
- **CA** : un client peut s'abonner ; après commit d'une écriture, un événement est diffusé aux abonnés.
- **Notes** : diffusion déclenchée depuis le writer unique.
- **Dépend de** : E00US007

### E00US009 — Repository + endpoint de bout en bout
*En tant que* développeur, *je veux* un aller-retour complet API↔domaine↔DB, *afin de* valider le patron.
- **CA** : un agrégat trivial est créé via un endpoint (DTO Pydantic), persisté par un repository (port/adapter), relu ; erreurs typées mappées à la frontière.
- **Notes** : sert de gabarit pour les US métier ; cf. ADR-0007.
- **Dépend de** : E00US007

### E00US010 — Shell React
*En tant que* utilisateur, *je veux* une app front qui charge et se connecte, *afin d'*interagir.
- **CA** : shell React+TS ; **React Query** configuré (fetch/cache) ; **Zustand** pour l'état UI ; client **WebSocket** branché ; organisation par features.
- **Dépend de** : E00US009

### E00US011 — Tranche verticale démontrable
*En tant que* PO, *je veux* une démo bout-en-bout, *afin de* valider l'architecture tôt.
- **CA** : créer un tournoi → ajouter 1 archer → le placer sur 1 cible → saisir 1 score → **voir un classement se mettre à jour en live**.
- **Notes** : versions minimales, jetables/évolutives ; sert de fil rouge pour J1.
- **Dépend de** : E00US010

### E00US012 — Exécutable de dev
*En tant que* équipe, *je veux* lancer l'app en un binaire, *afin de* préparer le packaging.
- **CA** : FastAPI sert le **build front** en statique ; un exécutable de dev démarre le tout ; port fixe.
- **Notes** : base d'EPIC-11 (packaging complet PyInstaller).
- **Dépend de** : E00US011
