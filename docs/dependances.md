# Registre des dépendances externes

> Registre **obligatoire** de toutes les librairies externes **directes** du projet (runtime et dev).
> Règle : toute dépendance ajoutée doit être **justifiée**, **sûre** et **inscrite ici** dans le même
> commit que son introduction. Voir [`../guide-architecture.md`](../guide-architecture.md) §3 et
> [ADR-0009](adr/0009-gouvernance-dependances.md).
>
> Seules les dépendances **directes** (choisies explicitement) sont listées ; les transitives sont
> figées par les lockfiles (`requirements.txt`, `package-lock.json`). Versions de référence :
> manifestes (`backend/pyproject.toml`, `frontend/package.json`). Licences **permissives**, à une
> exception documentée : **`zeroconf` est en LGPL-2.1** (copyleft faible). C'est **sans conséquence**
> ici — Kervignarc est un outil **interne mono-club, jamais distribué publiquement** ; la LGPL ne
> contraint qu'en cas de **distribution** d'un binaire liant la lib en refusant le re-link, ce qui
> n'arrive pas. Aucune modification de `zeroconf` n'est faite (simple import). À réévaluer **si** un
> jour le binaire était diffusé hors du club (E11US001, précédent tranché en
> [ADR-0043](adr/0043-acceptation-dependance-copyleft-lgpl.md)).
>
> **Audits de sécurité** (bloquants en CI, cf. `.github/workflows/ci.yml`, E00US003) — dernier contrôle
> 2026-07-28 (revalidé après l'ajout de l'outillage de test de rendu front — `@testing-library/*` +
> `jsdom`, E14US002) : `pip-audit` = **aucune vulnérabilité** ; `npm audit --audit-level=high`
> = **0 vulnérabilité** (`npm install` : *found 0 vulnerabilities*). Outils d'audit
> eux-mêmes : `pip-audit` est installé **ad hoc dans la CI** (non embarqué dans les manifestes
> applicatifs) ; `npm audit` est intégré à npm.

## Backend — runtime (`backend/pyproject.toml` › `dependencies`)

| Librairie | Version | Rôle | Justification | Licence |
|---|---|---|---|---|
| `fastapi` | 0.139.0 | Framework API (REST + WebSocket), validation Pydantic | Socle serveur acté ([ADR-0002](adr/0002-stack-et-topologie.md)) : async, WebSocket natif, typage, sert les statiques front | MIT |
| `uvicorn[standard]` | 0.51.0 | Serveur ASGI exécutant FastAPI | Serveur de référence pour FastAPI ; `[standard]` = websockets + boucle performante | BSD-3-Clause |
| `sqlalchemy` | 2.0.51 | ORM / Core SQL **synchrone** (accès SQLite, WAL) | Accès DB sync acté ([ADR-0005](adr/0005-async-et-sqlite.md)) ; Core+ORM typés, repositories derrière les ports (E00US006/009) | MIT |
| `alembic` | 1.18.5 | Migrations de schéma versionnées | Schéma versionné et testé (guide §7) ; standard de fait pour SQLAlchemy | MIT |
| `reportlab` | 5.0.0 | Génération PDF (documents imprimables) | Socle PDF acté ([ADR-0031](adr/0031-bibliotheque-pdf-reportlab.md)) : wheels autoportantes, **aucune bibliothèque native de niveau système à installer à part** (le code compilé de `pillow`/`reportlab` voyage dans les wheels), embarquable dans PyInstaller (R4) — retenu contre WeasyPrint sur ce seul critère (E09US001). Tire `pillow` et `charset-normalizer` (transitifs, figés par le lockfile) | BSD |
| `zeroconf` | 0.150.0 | Annonce mDNS `kervignarc.local` sur le réseau local | Mise en réseau du jour J (E11US001) : le binaire se publie lui-même, les tablettes accèdent au **nom** sans configurer le routeur. Alternative « quelques lignes maison » écartée (mDNS = multicast + encodage DNS non triviaux) ; wheels binaires cp313 embarquables PyInstaller ; expose `py.typed` (mypy strict). Publication **best-effort** — l'accès par IP reste le filet. Tire `ifaddr` (transitif) | LGPL-2.1 |

## Backend — développement (`backend/pyproject.toml` › `optional-dependencies.dev`)

| Librairie | Version | Rôle | Justification | Licence |
|---|---|---|---|---|
| `ruff` | 0.8.6 | Lint **+** format Python | Un seul outil rapide remplace flake8+isort+black ; qualité bloquante (guide §5) | MIT |
| `mypy` | 1.14.1 | Typage statique strict | Exigence « mypy strict » (guide §5) ; fiabilité du domaine | MIT |
| `pytest` | 9.1.1 | Framework de tests | Standard de fait ; stratégie de tests (guide §9) | MIT |
| `httpx` | 0.28.1 | Client HTTP (tests) | Requis par `fastapi.testclient` pour tester l'API | BSD-3-Clause |
| `pre-commit` | 4.0.1 | Orchestration des hooks git | Rend la qualité bloquante avant commit (guide §5) | MIT |
| `pyinstaller` | 6.21.0 | Fabrique le binaire de release auto-contenu | Packaging du jour J (E11US001) : produit un exécutable unique embarquant front + migrations + PDF (`build_release.py`, `kervignarc.spec`). **Outil de build uniquement**, jamais importé au runtime. Standard de fait du packaging Python autonome | GPL-2.0-with-exception (l'exception autorise les binaires produits sous toute licence) |

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
| `@testing-library/react` | ^16.3 | Test de **rendu** de composants React (monter, interroger) | Outillage de test de rendu acté ([ADR-0053](adr/0053-outillage-test-de-rendu-front.md), E14US002) : vérifie qu'un composant s'affiche et réagit (ce que tsc/eslint ne prouvent pas). Standard de fait de l'écosystème React ; teste par le rôle/texte accessibles, pas par les détails d'implémentation | MIT |
| `@testing-library/user-event` | ^14.6 | Simulation d'interactions utilisateur (clic/tap, saisie) dans les tests | Compagnon de `@testing-library/react` : reproduit un vrai geste (séquence d'événements) plutôt qu'un `fireEvent` bas niveau — fidèle à l'usage tactile visé | MIT |
| `@testing-library/jest-dom` | ^7.0 | Matchers DOM lisibles pour `expect` (`toBeVisible`, `toHaveAttribute`…) | Assertions expressives sur le DOM rendu + leur typage `tsc` ; entrée `/vitest` intégrée à l'`expect` de Vitest (E14US002) | MIT |
| `jsdom` | ^29.1 | Implémentation du DOM en mémoire (« faux navigateur ») pour les tests | Environnement requis par Testing Library ([ADR-0053](adr/0053-outillage-test-de-rendu-front.md)) : exécute le rendu sans navigateur réel. `environment: 'jsdom'` global (les tests de logique pure préexistants y tournent inchangés) | MIT |
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

## Épingles de version transitives (`frontend/package.json` › `overrides`)

Cinq paquets **transitifs** (jamais importés par notre code) sont épinglés à une version précise.
Un `overrides` npm force la version d'une dépendance de dépendance ; c'est le seul levier quand le
problème vient d'un paquet qu'on ne déclare pas soi-même.

| Paquet | Version | Pourquoi |
|---|---|---|
| `@emnapi/core` | `1.11.1` | `npm ci` échouait en CI sur « Missing @emnapi/core/runtime » — un lockfile valide pour `npm install` peut ne pas l'être pour `npm ci`, qui est plus strict. Dépendance optionnelle de binaires par plateforme (rollup/oxide). |
| `@emnapi/runtime` | `1.11.1` | idem. |
| `brace-expansion` | `5.0.9` | Advisory **GHSA-rgw5-rvv9-x895** (DoS, sévérité **high**) couvrant `4.0.0 – 5.0.8`. Tiré par `eslint` → `minimatch`. **Dev only** : rien n'en part dans le bundle du jour J. |
| `nanoid` | `^3.3.17` | Advisory **GHSA-2v37-7h3g-55p8** (boucle infinie si `size` vaut zéro, sévérité **high**) couvrant `< 3.3.17`. Tiré par `vite` → `postcss`. **Dev only** : `postcss` ne tourne qu'au *build*, rien n'en part dans le bundle du jour J — et le défaut suppose un générateur personnalisé, que nous n'écrivons pas. Épinglé quand même : `npm audit --audit-level=high` est **bloquant en CI**, il ne distingue pas dev et prod. |
| `postcss` | `^8.5.23` | Advisory **GHSA-fxqj-rqcc-2cmp** (lecture de `.map` arbitraires via `sourceMappingURL` quand `from` n'est pas défini, sévérité *moderate*) couvrant `<= 8.5.22`. Tiré par `vite`. **Dev only**, même raisonnement. Sévérité sous le seuil de la CI, montée **au passage** de `nanoid` : les deux advisories visent la même chaîne, les traiter séparément aurait fait deux allers-retours. |

### ⚠️ Une épingle doit être **relue** à chaque advisory

`brace-expansion` était déjà épinglé — à `5.0.8`, précisément la borne haute de l'advisory publiée
le 03/08/2026. **L'épingle d'hier est devenue le problème d'aujourd'hui** : figer une version protège
d'une régression, mais empêche aussi de recevoir un correctif de sécurité. La CI a échoué sur des PR
qui ne touchaient aucun fichier front.

Le réflexe, quand `npm audit` casse une PR sans rapport : **regarder si le paquet fautif est dans
`overrides`** avant de chercher ailleurs. Et à chaque montée d'épingle, revalider par un **`npm ci`**
— pas un `npm install` : c'est `npm ci` que la CI exécute, et c'est lui qui avait piégé le projet la
première fois.

### ⚠️ Ne **jamais** régénérer ce lockfile depuis un poste Windows

`npm install --package-lock-only` **élague** du lockfile les paquets optionnels propres à une autre
plateforme. Sous Windows, les deux entrées `@emnapi` disparaissent — elles ne servent qu'aux binaires
Linux. Le lockfile obtenu est parfaitement valide **sur le poste qui l'a produit**, et fait échouer
`npm ci` en CI :

```
npm error `npm ci` can only install packages when your package.json and package-lock.json are in sync
npm error Missing: @emnapi/core@1.11.1 from lock file
npm error Missing: @emnapi/runtime@1.11.1 from lock file
```

**Un `npm ci` local ne peut pas l'attraper** : il valide sur la plateforme qui vient d'élaguer. C'est
ce qui rend le piège coûteux — la boucle de retour passe obligatoirement par la CI.

**Le remède** : partir du lockfile **existant** et n'y modifier que l'entrée visée — trois champs,
`version`, `resolved` et `integrity` (relevés par `npm view <paquet>@<version> dist.integrity`).
Puis vérifier que chaque clé d'`overrides` a son entrée à la bonne version dans `packages` : c'est
exactement la condition que `npm ci` contrôle.

*(Constaté le 04/08/2026. C'est la **deuxième fois** que ce lockfile piège le projet, et la première
où la cause profonde est nommée : ce n'est pas `@emnapi` qui est capricieux, c'est **régénérer un
lockfile multiplateforme depuis une seule plateforme**.)*

#### Le piège s'est représenté le 07/08/2026 — et la consigne ci-dessus a tenu

Deux advisories (`nanoid` **high**, `postcss` *moderate*) ont été publiées **pendant** la revue
d'E16US003 : `npm audit` était vert au début de la session, rouge à la fin, **lockfile inchangé**. La
CI a donc cassé sur une PR qui ne touchait aucune dépendance.

Ce qui a été fait, dans l'ordre, et vaut d'être reproduit :

1. `npm audit fix` a été lancé **pour observer**, pas pour livrer : il a élagué les deux entrées
   `@emnapi` (11 → 6 mentions), exactement comme en 2026-08-04. **Le piège est donc reproductible et
   n'a rien d'accidentel** — il se déclenchera à chaque fois.
2. `npm install --package-lock-only` élague **tout autant** : ce n'est pas `audit fix` le fautif,
   c'est bien *régénérer depuis une seule plateforme*. Utile à savoir, la note de 2026-08-04 ne visait
   que `--package-lock-only` et on pouvait croire l'autre commande sûre.
3. Remède appliqué : lockfile d'origine + **édition chirurgicale** des deux entrées visées
   (`version`, `resolved`, `integrity` relevés par `npm view`), plus l'ajout des deux clés à
   `overrides` — l'épingle **déclare l'intention** et survivra à une régénération future.
4. Vérifications : `@emnapi` toujours à 11 mentions, 272 paquets (inchangé), JSON valide, **les cinq
   clés d'`overrides` ont leur entrée à la bonne version**, puis `npm ci` + `npm audit` + la porte
   complète.

⚠️ **Ce que la vérification locale ne prouve toujours pas.** Un `npm ci` vert sous Windows ne dit rien
de la CI Linux — c'est écrit plus haut et ça reste vrai. Ici le risque est **faible** parce que le
lockfile d'origine (multiplateforme) a été conservé et que seuls six champs ont bougé ; mais la preuve
reste la CI.

*(Troisième fois que ce lockfile coûte un aller-retour. La **cause** est nommée depuis le 04/08 ; ce
qui manquait était de savoir que `npm audit fix` tombe dans le même trou que `--package-lock-only`.)*
