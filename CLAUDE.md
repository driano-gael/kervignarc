# Kervignarc — instructions pour l'assistant

Gestion de tournoi de tir à l'arc en salle (18 m) : outil interne mono-club, déployé le jour J sur
réseau local **sans internet**. Backend FastAPI (serveur autoritaire) + SPA React servie par lui,
temps réel par WebSocket, ~30 tablettes BYOD.

> **Le [`guide-architecture.md`](guide-architecture.md) fait autorité** sur la structure et le style.
> Ce fichier n'est qu'un rappel opérationnel : en cas de divergence, le guide gagne, et toute
> exception à une règle passe par un ADR (`docs/adr/`).

## Communication avec l'utilisateur

Le projet est **en français** : code métier, documentation, commits, PR, et les échanges.

Ce projet est aussi un **apprentissage du développement assisté par IA** : la façon dont le travail
est expliqué compte autant que le code produit. En conséquence :

- **Sois explicatif.** Ne te contente pas de livrer le diff : dis ce que tu as fait, **pourquoi** tu
  l'as fait ainsi, et quelles alternatives tu as écartées. Une réponse qui laisse l'utilisateur
  incapable de refaire le raisonnement seul a raté sa cible.
- **Langage technique, niveau développeur junior.** Emploie les vrais termes (port, adapter,
  invariant, agrégat, injection de politique, migration) — ne les édulcore pas — mais **explique-les
  au passage** la première fois qu'ils apparaissent dans un contexte donné. Le but est que le
  vocabulaire soit acquis, pas contourné.
- **Rattache les décisions aux règles.** Quand un choix découle d'une règle du projet ou d'un ADR,
  nomme-la explicitement (« le domaine ne peut pas importer SQLAlchemy — règle 1, d'où le port ») :
  c'est ce lien qui fait comprendre l'architecture plutôt que de la subir.
- **Signale les pièges et les raisons de se méfier.** Cas limites, effets de bord, ce qui cassera
  plus tard — y compris quand l'utilisateur ne l'a pas demandé.
- **Reste honnête sur l'incertitude.** Si une approche est un pari ou si tu n'as pas vérifié quelque
  chose, dis-le franchement plutôt que d'affirmer. Un doute exprimé s'apprend ; une erreur assurée
  s'imite.
- **Ne cède pas sur le fond pour être pédagogique** : explication ≠ approximation, et détail ≠
  délayage. On explique le raisonnement, pas la syntaxe Python.

### Apprendre à piloter l'assistant

L'utilisateur veut aussi **apprendre à mieux se servir de l'assistant**. L'outil fait donc partie du
sujet, pas seulement le code :

- **Rends ton propre fonctionnement visible.** Quand une demande te fait choisir une stratégie
  (déléguer à un sous-agent, lancer `/revue-us`, explorer avant d'éditer, passer par un plan), dis
  **pourquoi** ce chemin plutôt qu'un autre. C'est ce qui rend le pilotage reproductible.
- **Signale ce qui aurait mieux marché.** Si une demande était ambiguë, sous-spécifiée, ou t'a fait
  partir sur une fausse piste, dis-le **après coup**, avec la formulation qui t'aurait mis sur les
  rails du premier coup. Ne fais pas semblant que tout était clair.
- **Expose les leviers au moment utile** — commande, skill, mode plan, fichier de contexte, découpage
  de la demande. Au moment où ils servent, pas en catalogue théorique.
- **Dis ce que tu ne peux pas faire**, ou ce que tu fais mal : contexte que tu n'as pas, vérification
  que tu n'as pas pu mener, endroit où une relecture humaine reste indispensable. Connaître les
  limites de l'outil fait partie de savoir l'utiliser.
- **Corrige les usages contre-productifs.** Si une habitude de prompt dégrade le résultat (demande
  trop large, plusieurs sujets mêlés, contrainte implicite jamais énoncée), signale-le franchement au
  lieu de faire de ton mieux en silence.

## Commandes

```bash
# Backend (depuis backend/, venv activé)
pip install -e ".[dev]"
uvicorn main:app --reload     # http://127.0.0.1:8000  (santé : /health)
pytest
mypy --strict --config-file=pyproject.toml .
ruff check . && ruff format .

# Frontend (depuis frontend/)
npm run dev / build / lint / format / typecheck

# Application complète (proche production, port fixe)
cd backend && python run_dev.py        # --no-build réutilise frontend/dist/
```

`pre-commit` (racine) lance ruff, mypy strict, le garde-fou d'isolation du domaine, eslint et
prettier avant chaque commit. La CI GitHub Actions est **bloquante** sur PR et sur `main`.

## Règles non négociables

1. **Isolation du domaine.** `backend/domain/` n'importe **aucun** framework (FastAPI, SQLAlchemy,
   Pydantic) ni aucune autre couche (`api/`, `application/`, `infrastructure/`, `bootstrap/`). Pur et
   synchrone. Vérifié par `backend/tests/test_domain_isolation.py` (AST) en pre-commit et en CI.
2. **Sens des dépendances.** Tout pointe vers le domaine. Les ports (interfaces) vivent dans le
   domaine, les adapters dans `infrastructure/`. Les politiques du moteur (`routing`, `scoring`,
   `seeding`, `byes`, `tiebreak`, `depth`) sont des stratégies injectables — un format de tournoi est
   de la **configuration**, pas du code.
3. **Vocabulaire.** Métier en **français FFTA** (`Archer`, `Cible`, `Blason`, `Volee`, `Fleche`,
   `Duel`, `Depart`, `Categorie`, `Phase`), technique en **anglais** (`Repository`, `Adapter`,
   `Service`, `Router`, `Store`). Cohérent entre code, API, UI et doc — voir
   [`docs/glossaire.md`](docs/glossaire.md).
4. **Typage strict.** mypy strict côté Python (pas d'`Any` implicite), TS `strict` (pas d'`any` non
   justifié). Immutabilité privilégiée dans le domaine (dataclasses `frozen`).
5. **Erreurs typées par couche.** `DomainError` / `ApplicationError` / `InfrastructureError` /
   `ApiError`. Le mapping HTTP se fait **uniquement à la frontière API**, réponse
   `{ code, message, details? }`. Aucun message interne ne fuit vers le client (log serveur).
6. **Frontière API.** DTO Pydantic **distincts** des entités domaine/ORM (jamais d'exposition
   directe). REST versionné `/api/v1/…`. Les `Depends` restent cantonnés à la couche API.
7. **SQLite single-writer.** WAL ; écritures **via la file consommée par le writer unique** ;
   lectures synchrones hors boucle événementielle ; transactions **courtes**, pas de logique métier
   longue dans une transaction ouverte. Pas d'aiosqlite. Migrations Alembic.
8. **Composition root explicite.** Câblage à la main dans `bootstrap/` / `main.py`, sans DI magique.
   Tout nouveau branchement y est reflété.
9. **Tests.** Unitaires en priorité sur le domaine (couverture élevée), intégration sur les adapters
   et endpoints, déterministes (pas d'horloge ni d'aléa non maîtrisé). **L'oracle 120** (rejeu du
   tournoi de `Tableaux.xlsx`) doit rester vert.
10. **Front React.** État serveur via React Query, état UI local via Zustand, organisation **par
    features** (pas par type technique). Ergonomie tactile prioritaire sur l'écran de saisie +
    indicateur de connexion visible.
11. **Dépendances externes.** Parcimonie — pas de lib « plaisir » : stdlib ou quelques lignes maison
    préférées ; en cas de doute, on n'ajoute pas. Toute lib ajoutée est, **dans le même commit**,
    (a) déclarée au manifeste (`pyproject.toml` source de vérité **+** `requirements.txt` régénéré
    par `pip freeze --exclude-editable`, **jamais** édité à la main ; ou `package.json` +
    `package-lock.json`), (b) justifiée, (c) sûre (`pip-audit`/`npm audit` verts, licence
    permissive), (d) documentée dans [`docs/dependances.md`](docs/dependances.md). Une dépendance
    fantôme ou non documentée est bloquante.
12. **Simplicité assumée hors domaine.** L'infra reste simple : mono-club, local. La rigueur va au
    moteur métier, pas à l'outillage.

## Dette

Une dette **assumée** (technique ou de conception) s'inscrit au registre
[`docs/dette.md`](docs/dette.md) **dans le commit qui l'introduit** : ligne au tableau + section de
détail + marqueur `# DETTE-nnn` à l'endroit exact du raccourci. Une US qui **aggrave** une dette déjà
listée élargit la ligne existante au lieu d'inventer un contournement local. Une dette silencieuse
est remontée en **majeur** à la revue ; ce qui casse un cas utilisateur réel dès maintenant n'est pas
de la dette mais un **bloquant** à corriger avant merge. Le registre n'est pas une liste de tâches :
un bug corrigeable dans l'US se corrige dans l'US.

Un **remède structurel** (introduire un pattern) se propose sur **preuve dans le code d'aujourd'hui**
— 3ᵉ occurrence réelle, invariant déjà dupliqué — jamais sur une évolution supposée, et se traite en
ADR + US dédiée, jamais en douce dans l'US courante. « Dupliquer une 2ᵉ fois et attendre le 3ᵉ cas »
est une réponse valide.

## Workflow

- **Une branche par US**, jamais de travail direct sur `main`. Nommage
  `<type>/<ExxUSyyy>-<slug-court>` en minuscules kebab-case (ex. `feat/e04us003-saisie-fleches`).
  `<type>` ∈ `feat` | `fix` | `refactor` | `test` | `docs` | `chore`, cohérent branche ↔ commits ↔ US.
- **Commits conventionnels** : `<type>(<scope>): <résumé>` (impératif, ≤ ~72 car., `scope` = ID d'US
  en minuscules) + corps expliquant le **quoi** et surtout le **pourquoi**, avec les références
  (`US: ExxUSyyy`, `ADR-XXXX`). Commits atomiques.
- **Le message de commit est toujours rédigé et proposé** par l'assistant — mais **l'utilisateur
  garde la main** sur l'exécution de `git commit` / `git push` : ne pas les lancer sans son aval.
- Quand l'utilisateur dit **« lance la PR »**, exécuter [`/revue-us`](.claude/commands/revue-us.md) :
  revue du diff par un agent dédié selon la grille projet, puis correction par l'agent auteur.
  **C'est l'utilisateur qui ouvre et merge la PR**, puis dit « c'est mergé ».
- Cycle : branche depuis `main` à jour → PR → revue + CI verte → merge → suppression de la branche.
- **Décision structurante ⇒ ADR** dans `docs/adr/` (contexte / décision / conséquences).
- Une US trop grosse pour une branche doit être **redécoupée** (maille INVEST).

## Documents de référence

| Document | Contenu |
|---|---|
| [`guide-architecture.md`](guide-architecture.md) | **Conventions de code & workflow — fait autorité** |
| [`cahier-des-charges.md`](cahier-des-charges.md) | Besoin fonctionnel |
| [`cahier-des-charges-technique.md`](cahier-des-charges-technique.md) | Architecture technique |
| [`cahier-des-charges-ux.md`](cahier-des-charges-ux.md) · [`-design.md`](cahier-des-charges-design.md) | Parcours & registres `D-nn` / `DV-nn` |
| [`moteur-placement-lucky-loser.md`](moteur-placement-lucky-loser.md) | Formalisation du moteur de placement |
| [`docs/glossaire.md`](docs/glossaire.md) · [`docs/modele-de-donnees.md`](docs/modele-de-donnees.md) · [`docs/referentiel-ffta.md`](docs/referentiel-ffta.md) | Vocabulaire, modèle, règles FFTA |
| [`docs/dette.md`](docs/dette.md) · [`docs/dependances.md`](docs/dependances.md) · [`docs/adr/`](docs/adr/) | Registres et décisions |
| [`epics/`](epics/) · [`stories/`](stories/) | Backlog produit (jalons J0→J4) |

`prototype/` est un prototype Python de déc. 2024 : **référence de lecture uniquement**, non exécuté,
au vocabulaire hétérogène (`Player.lettre`, `idCible`) — ne pas s'en inspirer pour le nommage.
