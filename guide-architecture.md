# Guide d'architecture & conventions de code — Kervignarc

| | |
|---|---|
| **Version** | 0.1 |
| **Date** | 08/07/2026 |
| **Statut** | Règles projet — à respecter par toute contribution |
| **Documents liés** | `cahier-des-charges-technique.md`, `moteur-placement-lucky-loser.md` |
| **Portée** | Structure du code et règles de développement, arbitrées en entretien d'architecture du 08/07/2026 |

> Ce guide fait autorité sur les questions de structure et de style. Les décisions structurantes sont journalisées en **ADR** (`docs/adr/`). Toute exception à une règle doit être justifiée par un ADR.

---

## 1. Principes directeurs

1. **Le domaine d'abord.** Le moteur métier (phases, politiques, placement) est le cœur de valeur et le point de risque n°1 : il est **isolé, pur et abondamment testé**.
2. **Le format n'est pas du code, c'est de la configuration.** Un format de tournoi = un assemblage de **politiques injectables** (cf. `moteur-placement-lucky-loser.md` §7).
3. **Exigence de qualité stricte** dès le départ (typage, lint, tests, CI bloquante).
4. **Simplicité assumée** hors du domaine : outil mono-club local, pas de sur-ingénierie côté infrastructure.

---

## 2. Architecture — hexagonale ciblée sur le domaine

### 2.1 Couches et règle de dépendance
```
        API (FastAPI, WebSocket)        ← adapters entrants
                  │
        Application (use cases)         ← orchestration
                  │
   ┌──────────────┴──────────────┐
   │        DOMAINE (pur)         │     ← aucune dépendance framework
   │  phases, politiques, règles  │
   └──────────────┬──────────────┘
                  │  (ports = interfaces)
        Infrastructure (SQLite, PDF…)   ← adapters sortants
```

- **Règle de dépendance (stricte)** : les dépendances pointent **vers le domaine**. Le `domain/` n'importe **jamais** FastAPI, SQLAlchemy, Pydantic, ni aucun module `api/`, `infrastructure/`, `application/`, `bootstrap/`.
  - **Vérifiée automatiquement** (E00US004) : un test d'architecture (`backend/tests/test_domain_isolation.py`, analyse AST) **échoue** si un module de `domain/` importe un framework ou une autre couche. Exécuté par pytest (CI) et par un hook pre-commit. Implémentation maison, sans dépendance dédiée (parcimonie, ADR-0009).
- Le domaine définit des **ports** (interfaces abstraites : `ArcherRepository`, `RankingStore`…) ; l'infrastructure fournit les **adapters**.
- Les **politiques** du moteur (`routing`, `scoring`, `seeding`, `byes`, `tiebreak`, `depth`) sont des interfaces du domaine, implémentées comme stratégies interchangeables.

### 2.2 Composition root explicite
- Le **câblage** des adapters et des politiques se fait **à la main** dans une factory / point d'entrée (`main.py` + un module `bootstrap/`), **sans conteneur DI magique**.
- Objectif : un graphe de dépendances **lisible et debuggable**. Ce qui est branché est visible en un seul endroit.
- Les dépendances des routes FastAPI (`Depends`) restent **cantonnées à la couche API** ; elles n'atteignent pas le domaine.

---

## 3. Structure du dépôt (monorepo) & outillage

```
kervignarc/
├── backend/
│   ├── domain/          # PUR : phases/, policies/, placement, ranking… (cf. CDC technique §4)
│   ├── application/     # use cases / services applicatifs
│   ├── infrastructure/  # adapters : db (SQLAlchemy sync + file d'écriture), pdf, import xls
│   ├── api/             # routers REST + WebSocket + mapping erreurs
│   ├── bootstrap/       # composition root (câblage explicite)
│   ├── tests/
│   └── main.py
├── frontend/            # React + TS (Vite), organisé par features
├── docs/
│   └── adr/             # Architecture Decision Records
├── pyproject.toml       # ruff + mypy + pytest — SOURCE DE VÉRITÉ des dépendances Python
├── requirements.txt     # export synchronisé (voir règle ci-dessous)
└── README.md
```

- **Un seul dépôt** (back + front). Le build front est **embarqué** dans l'exécutable (servi en statique par FastAPI).
- **Outillage** : **`venv`/`pip`** (gestion Python & venv), **npm** + **Vite** (front). Versions Python/Node figées. *(Écart assumé au choix initial uv/pnpm — voir [ADR-0008](docs/adr/0008-outillage-npm-venv.md).)*
- **Build de release** : pipeline `build front → embarquer → PyInstaller` (exécutable double-clic).
- **Règle — dépendances externes tenues à jour** : tout **ajout (ou retrait) d'une librairie externe** doit mettre à jour le manifeste de dépendances **dans le même commit/branche que le code qui l'introduit**.
  - **Python** : la dépendance est déclarée dans `pyproject.toml` (source de vérité) **et** `requirements.txt` est régénéré pour rester synchronisé — `pip freeze > requirements.txt` (versions épinglées). `requirements.txt` n'est **jamais** édité à la main. La CI **échoue** si `requirements.txt` n'est pas à jour vis-à-vis de `pyproject.toml`.
  - **Frontend** : l'équivalent est `package.json` + lockfile `package-lock.json`, mis à jour par la commande d'ajout (`npm install`).
  - Aucune dépendance « fantôme » : une lib importée mais absente du manifeste est un échec de revue/CI.
- **Règle — gouvernance des dépendances externes** (parcimonie, sécurité, documentation — cf. [ADR-0009](docs/adr/0009-gouvernance-dependances.md)) : une dépendance est un **coût et une surface de risque**, pas un réflexe.
  - **Parcimonie** — pas de librairie « plaisir » : on préfère la **bibliothèque standard** ou quelques lignes maison à une lib pour un besoin marginal. Chaque ajout doit répondre à un **besoin réel** (complexité, fiabilité ou temps qu'elle fait gagner), et son **poids/transitivité** est pris en compte. En cas de doute : **on n'ajoute pas**.
  - **Sécurité** — seules des librairies **sûres** sont autorisées : activement **maintenues**, largement adoptées, **sans vulnérabilité connue** (`pip-audit` / `npm audit` **verts** — bloquant en CI, cf. §3 outillage et EPIC-00), **licence compatible** (permissive : MIT/BSD/Apache/ISC ; copyleft à valider). Sources officielles (PyPI/npm) uniquement ; méfiance sur les paquets récents/peu téléchargés (typosquatting).
  - **Documentation** — **toute** librairie ajoutée est **documentée** dans le **registre des dépendances** ([`docs/dependances.md`](docs/dependances.md)) : *nom, version, couche/périmètre, rôle, justification (pourquoi elle plutôt que la stdlib/une alternative), licence*. Un ajout non documenté est un **échec de revue**.
  - **Revue** — l'ajout d'une dépendance est un **point d'attention explicite en revue de PR** (justification + sécurité + entrée de registre). Une dépendance structurante fait l'objet d'un **ADR**.

---

## 4. Langue & vocabulaire métier (ubiquitous language)

- **Termes métier en français** (issus de la FFTA) : `Archer`, `Cible`, `Blason`, `Volee`, `Fleche`, `Duel`, `Set`, `Barrage`, `Depart`, `Categorie`, `Placement`, `Tableau`, `Phase`.
- **Code technique / infrastructure en anglais** : `Repository`, `Adapter`, `Service`, `Router`, `Session`, `Store`, `Factory`, etc.
- **Cohérence obligatoire** entre le nom du concept dans le code, l'API, l'UI et la documentation.
- Un **glossaire** (`docs/glossaire.md`) fait référence ; le prototype hétérogène (`Player.lettre`, `idCible`) est **renommé** selon cette règle (`Archer`, `Cible.lettre` → `position`).

---

## 5. Conventions de code (qualité stricte, CI bloquante)

### Python
- **Typage** : annotations partout ; **mypy en mode strict** ; pas de `Any` implicite.
- **Lint & format** : **ruff** (lint + format), configuration partagée.
- **Style** : PEP 8, fonctions courtes, pas de logique métier hors du domaine.
- **Immutabilité** privilégiée dans le domaine (dataclasses `frozen`, valeurs plutôt qu'états mutables quand possible).

### TypeScript / React
- **`strict: true`** dans `tsconfig` ; pas de `any` non justifié.
- **ESLint + Prettier**, configuration partagée.
- Composants fonctionnels + hooks ; typage des props et des réponses API.

### Garde-fous
- **pre-commit** (ruff, mypy, eslint, prettier, tests rapides).
- **CI bloquante** : lint + typage + tests doivent passer avant tout merge.

---

## 6. Frontière API & taxonomie d'erreurs

### API
- **DTO Pydantic distincts** des objets du domaine (aucune exposition directe des entités domaine/ORM).
- **REST versionné** : `/api/v1/…`. Nommage des ressources en anglais technique, cohérent.
- **WebSocket** pour le temps réel (scores, tableaux, classements).

### Erreurs typées **par couche** (décision projet)
Chaque couche définit sa propre famille d'exceptions ; le mapping vers une réponse HTTP normalisée se fait **uniquement à la frontière API**.

| Couche | Exceptions | Exemple | Traitement |
|---|---|---|---|
| **Domaine** | `DomainError` (ex. `PlacementInvalide`, `PhaseMalAlimentee`) | règle métier violée | → HTTP 422, code métier explicite |
| **Application** | `ApplicationError` (ex. `TournoiIntrouvable`) | cas d'usage impossible | → HTTP 404/409 |
| **Infrastructure** | `InfrastructureError` (ex. échec DB/IO) | panne technique | → HTTP 500, message générique + log |
| **API** | `ApiError` (validation entrée) | requête invalide | → HTTP 400 |

- **Format de réponse d'erreur uniforme** : `{ code, message, details? }`. Les messages internes ne fuient pas vers le client (log côté serveur).
- Les erreurs **remontent typées** ; c'est l'adapter API qui **traduit** vers le format client — le domaine ignore HTTP.

---

## 7. Modèle d'exécution & accès aux données

- **FastAPI async** au niveau **I/O réseau / WebSocket / connexions**, mais **accès DB synchrones** (SQLAlchemy sync), encapsulés dans des **repositories** (ports côté domaine, implémentations côté infrastructure). Pas d'aiosqlite. Cf. [ADR-0005](docs/adr/0005-async-et-sqlite.md).
- ⚠️ **Règle SQLite (single-writer)** — SQLite n'accepte **qu'un seul écrivain** :
  - Base en **mode WAL** (lectures concurrentes non bloquées).
  - **Écritures via une file (queue) consommée par un writer unique** : sérialisation native, pas de `database is locked` sous 30 clients ; point de passage naturel pour l'audit métier et la diffusion WebSocket post-commit.
  - **Lectures** synchrones directes, exécutées **hors boucle événementielle** (threadpool/executor).
  - Transactions **courtes** ; pas de logique métier longue dans une transaction ouverte.
- Le domaine reste **synchrone et pur** ; file d'écriture et accès DB vivent dans les **adapters** (infrastructure).
- **Migrations** via Alembic ; schéma versionné et testé.

---

## 8. Front-end React

- **État serveur** : **React Query** (fetch, cache, invalidation, intégration temps réel via WebSocket).
- **État UI local** : **Zustand** (léger).
- **Organisation par features** (`features/placement`, `features/saisie`, `features/tableaux`, `features/classement`, `features/admin`…), pas par type technique.
- **Une feature = un écran autonome.** Chaque fonction vit dans son dossier (`features/<domaine>/` : composant + `api.ts` + `hooks.ts`) et se suffit à elle-même. Une fonction ne s'implémente **jamais** enfouie dans le fichier d'une autre ; pas de composant « fourre-tout » empilant plusieurs domaines. Le mauvais réflexe à proscrire : ajouter une section à un gros conteneur au lieu de créer une feature — c'est ainsi qu'un écran devient monolithique et cesse d'être évolutif.
- **Coquille de navigation.** L'assemblage des features passe par une **coquille** (ossature de navigation, [CDC UX §7.1](cahier-des-charges-ux.md)) qui affiche **une destination à la fois** ; brancher une nouvelle fonction = **une entrée** dans la coquille, pas une ligne de plus dans un écran empilé.
- **Ergonomie tactile** prioritaire sur l'écran de saisie ; indicateur d'état de connexion visible.

---

## 9. Stratégie de tests (pyramide complète)

- **Unitaires (priorité domaine)** : `pytest` sur phases, politiques, placement, départage, byes. Couverture élevée sur `domain/`.
- **Intégration** : repositories/adapters (DB réelle SQLite de test), endpoints API.
- **End-to-end** : quelques parcours front critiques (saisie → validation → classement live).
- **Oracle de non-régression** : **rejeu du tournoi 120 de `Tableaux.xlsx`** — l'arbre généré, le routage des perdants et le classement 1→120 doivent correspondre exactement au classeur.
- Tests **déterministes** (pas de dépendance à l'horloge/aléa non maîtrisé).
- **Recette de l'app poste avec une seule tablette (ENF-7).** Le rattachement de poste vit dans `localStorage` — **par origine, donc partagé entre onglets** : sur une tablette, **un navigateur = un seul poste**. Pour exercer le **multi-poste** avec peu de matériel : **contextes de navigation séparés** (profils / fenêtres privées), ou le **PC de dev** (chaque onglet y est un poste). La **tablette** valide le *device-specific* (tactile, scan QR, Screen Wake Lock, indicateur de connexion) ; la **logique multi-poste** (diffusion live, supervision, contention) se valide avec **N contextes navigateur**. Un **harnais de dev** injectant N jetons de poste est la voie la plus reproductible.

---

## 10. Observabilité

- **Logs structurés** (format machine, niveau configurable) dans les couches application/infrastructure ; le domaine ne journalise pas (il lève des erreurs typées).
- **Journal d'audit métier** (entité `AuditLog`) pour les actions sensibles : corrections de score, validations, forfaits — qui / quand / avant-après. Essentiel en cas de litige en compétition.
- Corrélation d'un incident : log technique + entrée d'audit métier.

---

## 11. Traçabilité des décisions & workflow

- **ADR** (`docs/adr/NNNN-titre.md`) : format court (contexte / décision / conséquences) pour toute décision structurante. Les arbitrages de ce guide y sont initialement consignés.
- **Commits conventionnels** : `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`…
- **Message de commit rédigé et fourni** : tout travail préparé s'accompagne d'un **message de commit prêt à l'emploi**. En développement **assisté**, l'assistant **prépare et propose systématiquement** ce message au moment de committer (l'utilisateur garde la main sur l'exécution de `git commit`/`push`).
  - **Format** : ligne de résumé conventionnelle `<type>(<scope>): <résumé>` (impératif, ≤ ~72 car., `scope` = ID d'US en minuscules quand pertinent) ; puis un **corps** expliquant le **quoi** et surtout le **pourquoi** (puces autorisées), et les références utiles (`US : ExxUSyyy`, `ADR-XXXX`, `Dépend de :`).
  - **Cohérence** : le `type` du commit = celui de la branche/US ; un commit ne mélange pas des périmètres sans raison (préférer des commits atomiques, sauf choix explicite de regroupement).
- **Une branche par user story** : tout développement d'une US se fait sur une **branche dédiée**, jamais directement sur la branche principale.
  - **Nommage** : `<type>/<ExxUSyyy>-<slug-court>` — tout en minuscules, `slug` en kebab-case.
    - Exemples : `feat/e04us003-saisie-fleches`, `fix/e05us012-routing-cascade`, `chore/e00us001-init-monorepo`, `docs/e00us004-garde-fou-imports`.
  - **`<type>`** reflète le **périmètre** de l'US (mêmes tags que les commits) :
    | Type | Quand |
    |---|---|
    | `feat` | nouvelle capacité / comportement métier |
    | `fix` | correction d'un défaut |
    | `refactor` | restructuration sans changement de comportement |
    | `test` | ajout/renforcement de tests seuls |
    | `docs` | documentation seule |
    | `chore` | outillage, config, build, CI |
  - **Cohérence branche ↔ commits ↔ US** : le `type` de la branche = celui des commits de l'US ; l'ID d'US apparaît dans la branche et est rappelé dans le titre de PR.
  - **Cycle de vie** : branche créée depuis la principale à jour → PR → **revue obligatoire** (≥ 1 relecteur) + **CI verte** → merge → **suppression de la branche**. Pas de merge direct sur la principale.
- Une US « trop grosse pour une branche » est le signe qu'elle doit être **redécoupée** (cf. maille INVEST du backlog).

---

## 12. Récapitulatif des règles (checklist de contribution)

- [ ] Le `domain/` n'importe aucun framework ni couche externe.
- [ ] Vocabulaire : métier en FR, technique en EN, cohérent partout.
- [ ] Typage strict (mypy strict / TS strict), lint & format passants.
- [ ] Erreurs typées par couche, mappées seulement à la frontière API.
- [ ] DTO Pydantic distincts des entités domaine.
- [ ] Écritures SQLite sérialisées (WAL), transactions courtes.
- [ ] Tests ajoutés/à jour ; l'oracle 120 reste vert.
- [ ] Câblage nouveau reflété dans la composition root.
- [ ] Toute nouvelle **librairie externe** est déclarée dans le manifeste (`pyproject.toml`→`requirements.txt` régénéré ; ou `package.json`) dans le même commit — pas de dépendance fantôme.
- [ ] Nouvelle dépendance : **justifiée** (parcimonie, pas de lib « plaisir »), **sûre** (`pip-audit`/`npm audit` verts, licence compatible) et **documentée** dans [`docs/dependances.md`](docs/dependances.md) — cf. §3 et ADR-0009.
- [ ] US développée sur sa **branche dédiée** `<type>/<ExxUSyyy>-<slug>` ; branche supprimée après merge.
- [ ] Décision structurante ⇒ ADR ; commit conventionnel ; revue avant merge.
- [ ] **Message de commit** conventionnel **rédigé et fourni** (résumé + corps quoi/pourquoi + réfs US/ADR) — proposé par l'assistant en développement assisté.

---

*Guide établi lors de l'entretien d'architecture du 08/07/2026. Évolue par ADR.*
