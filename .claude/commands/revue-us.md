---
description: Revue de code d'une US par des agents dédiés en parallèle, puis correction par l'agent auteur (déclenché au « lance la PR »)
argument-hint: "[ExxUSyyy optionnel — sinon déduit de la branche]"
allowed-tools: Bash(git status:*), Bash(git branch:*), Bash(git diff:*), Bash(git log:*), Bash(git fetch:*), Bash(git rev-parse:*), Bash(git merge-base:*), Bash(git add:*), Bash(git commit:*), Bash(git push:*), Bash(ruff:*), Bash(mypy:*), Bash(pytest:*), Bash(pip-audit:*), Bash(npm run:*), Bash(npm audit:*), Read, Grep, Glob, Edit, Write, Agent
---

# Revue d'US Kervignarc → correction → PR prête

Objectif : quand l'utilisateur dit « lance la PR », faire relire le travail de l'US par des
**agents de revue distincts** (quatre axes, en parallèle), puis laisser l'**agent auteur** (toi)
fusionner leurs rapports et intégrer les remarques avant de fournir la PR. L'utilisateur ouvre et
merge la PR lui-même. Cette procédure est fixée par [ADR-0013](../../docs/adr/0013-conduite-de-la-revue-d-us.md).

**Principe de coût** : ce qu'une machine prouve ne se relit pas à l'œil (porte mécanique, étape 0) ;
ce qui demande du jugement se relit en parallèle, à modèle fort, sans rien retirer de la grille
(étape 1) ; ce qui a déjà été relu et n'a pas bougé ne se relit pas deux fois (étape 3).

**Le contre-principe, qui prime** : une revue qui va vite et ne voit rien ne sert à rien. Un faux
négatif ici est invisible et durable — il tamponnera des US pendant des mois. Chaque fois que les
deux principes s'opposent, **c'est la détection qui gagne**.

US ciblée : `$ARGUMENTS` (si vide, la déduire de la branche courante `<type>/<ExxUSyyy>-<slug>`).

## Étape 0 — Cadrage (toi, l'agent auteur)

1. `git branch --show-current` — vérifier qu'on est sur une **branche d'US** (jamais `main`/`master`). Sinon, stop et prévenir.
2. `git fetch` puis déterminer la base : `git merge-base HEAD origin/main`.
3. Calculer le périmètre : `git diff --stat origin/main...HEAD` et la liste des fichiers modifiés. Ignorer les artefacts (`node_modules/`, `.venv/`, `dist/`, lockfiles générés sauf incohérence).
4. **Règle 12 — le format, ici ; le jugement, à un relecteur.** `git log --format='%h %s%n%b' origin/main..HEAD`. Tu vérifies toi-même le **factuel** : type/scope conventionnel, cohérence avec la branche, corps qui explique le quoi **et** le pourquoi, références présentes. Tu **ne juges pas** « décision structurante ⇒ ADR » : c'est la seule règle des seize dont l'objet est de rattraper ce que **tu** as escamoté, et te la confier la neutralise. Elle est à l'axe C2 (règle 12-ADR) ; passe-lui le log en périmètre. *(Preuve que ce n'est pas théorique : le commit `b47b25c` — refonte de cette procédure même — a été livré sans ADR, et c'est un relecteur tiers qui l'a rattrapé. ADR-0013 n'existerait pas autrement.)*
5. **Passer la porte mécanique AVANT de dépenser une passe de revue.** Selon les fichiers touchés — commandes **identiques à celles de `.github/workflows/ci.yml`**, qui est l'autorité bloquante (mêmes options : une commande approchante n'est pas la même mesure) :
   - backend : `ruff check .` · `ruff format --check .` · `mypy .` · `pytest` · `pip-audit -r requirements.txt --strict`
   - frontend : `npm ci` · `npm run lint` · `npm run format:check` · `npm run typecheck` · `npm run build` · `npm audit --audit-level=high`

   **Rouge ⇒ tu corriges d'abord, tu ne lances pas la revue** : un diff qui ne passe pas mypy fait relire du code condamné. La porte est un **sous-ensemble volontaire** de la CI : **une seule** étape est sciemment omise, le contrôle de synchro `requirements.txt`↔`pyproject.toml`. Toute **autre** divergence est un bug de cette procédure. La CI garde le dernier mot.
6. **Décider si la décharge s'applique** (voir ci-dessous) et noter le résultat : il est passé aux relecteurs.

### La décharge mécanique — et sa suspension

Ce que les outils **prouvent**, les relecteurs ne le relisent pas. Ce que la décharge couvre, **exactement** :

| Prouvé par | Ce qui est déchargé | Ce qui ne l'est PAS |
|---|---|---|
| `test_domain_isolation.py` (AST) | imports de `domain/` visant les **frameworks listés** dans `_FORBIDDEN_ROOTS` et les autres couches | tout import tiers **hors liste** ; le caractère **synchrone** du domaine (règle 1, axe A) |
| `mypy .` (strict) | `Any` implicite, annotations manquantes — **sauf `backend/migrations/`, exclu par `pyproject.toml`** | l'immutabilité (`frozen`), l'`Any` **explicite**, le `cast` qui masque un trou (règle 4, axe A) |
| `ruff` / `eslint` / `prettier` | lint, format, `no-explicit-any` côté TS (via `tseslint.configs.recommended`) | le `noqa` / `eslint-disable` qui **contourne** la règle au lieu de la satisfaire (→ dette, axe C2) |
| `pip-audit` / `npm audit` | **une seule chose** : l'absence de **vulnérabilité connue** — et côté npm, **au seuil `high` et au-dessus** seulement | **tout le reste de la règle 11-c** : la **licence** (permissive MIT/BSD/Apache/ISC ; copyleft à valider — `CLAUDE.md` règle 11, ADR-0009 §2), la **maintenance**, l'**adoption**, le **typosquatting** ; les vulns npm `moderate`/`low` ; la justification (11-b) et la documentation (11-d). Tout cela reste à l'axe B |

**Suspension — une porte verte ne prouve rien si le diff a déplacé la porte.** C'est un **principe,
pas une liste** : une liste oublie toujours un fichier, et c'est exactement comme ça que ce
garde-fou a été percé une première fois.

> **La décharge est suspendue dès que le diff touche un fichier qui définit ce que la porte exécute
> ou ce qu'elle vérifie.** Si tu te demandes si un fichier en fait partie, c'est qu'il en fait partie.

Non exhaustif, à titre d'illustration : `backend/pyproject.toml` (**toute** section d'outillage —
`[tool.mypy]`, `[tool.ruff*]`, `[tool.pytest.ini_options]` : un `addopts` qui ajoute `--ignore` tue
un garde-fou sans rien faire rougir), `frontend/package.json` (**bloc `scripts`** : il *est* la
définition de la porte front), `.pre-commit-config.yaml`, `.github/workflows/ci.yml`,
`frontend/eslint.config.js`, `frontend/tsconfig*.json`, `backend/tests/test_domain_isolation.py`,
`backend/tests/conftest.py` (cf. le commentaire de `.pre-commit-config.yaml` : un import ajouté là
casse le garde-fou sans que la CI le voie).

Suspension ⇒ signale-le aux agents, et l'axe A relit ces fichiers **ligne à ligne**. Tout
assouplissement (exclusion élargie, `disable_error_code`, `addopts` qui saute un test, script npm
neutralisé, ajout à `ignore`, étape CI retirée, hook supprimé, denylist non élargie) est
**bloquant** sauf justification explicite au corps du commit.

## Étape 1 — Revue par des agents DÉDIÉS, en PARALLÈLE

Lance **quatre sous-agents** (`Agent`, type `general-purpose`) — **cinq si le changement est
structurel** : le relecteur **adversarial** ci-dessous en est un à part entière, pas un bonus. Tous
**dans un seul message**, donc en même temps. Aucun ne modifie quoi que ce soit : chacun reçoit le
préambule commun et rend un rapport au même format, verdict compris.

**Pourquoi quatre et pas un.** Un relecteur unique déroule 16 règles en série : le temps mur est leur
somme, et son attention se dilue. Quatre relecteurs sur des axes disjoints ramènent le temps mur à
celui de l'axe le plus lent, à qualité égale ou meilleure — mêmes règles, chacun avec une consigne
courte qu'il traite à fond. C2 (dette/conception, jugement ouvert + registres) est le chemin
critique : c'est pour le raccourcir que la règle 13 en a été sortie vers C1.

**Ce qui ne s'optimise pas** : les relecteurs gardent le **modèle fort** — barrière qualité du projet
(`CLAUDE.md` § Économie de contexte). On parallélise la revue, on ne la dégrade pas.

**Gain attendu ~2×** sur le temps mur, pour un coût en tokens de ~2,5×. Honnêteté sur ce chiffre :
le chemin critique est `max(A, B, C1, C2)` et il **n'a jamais été mesuré**. C2 en est le candidat
présumé (jugement ouvert + registres), mais B lit le plus large ensemble de fichiers et C1 mène la
chasse la plus ouverte sur le diff entier — ils sont des candidats au moins aussi sérieux. Le ~2×
est une **estimation à confirmer sur les trois prochaines US**, pas un acquis.

### Concordance des numéros — à lire avant la grille

La grille reprend les **règles 1-11** de `CLAUDE.md` § Règles non négociables, **mêmes numéros**. Les
règles **12 à 16 sont propres à la revue** et ne correspondent PAS à la numérotation de `CLAUDE.md` :
en particulier, la règle **12 de `CLAUDE.md`** (« simplicité assumée hors domaine ») est couverte ici
par la règle **13**, et la règle **12 de la grille** (traçabilité) n'existe pas dans `CLAUDE.md`.
Deux listes écrites à la main : quand l'une bouge, propager à l'autre — c'est le coût de maintenance
qu'ADR-0013 assume.

### Périmètre : une aide à la LECTURE, jamais un déclencheur

Le périmètre d'un axe dit **par où commencer à lire**. Il ne dit **pas** quand se taire. Les règles
d'un axe s'appliquent **toujours**, que leur périmètre soit touché ou non.

**Le seul discriminant est : AS-TU LU ?** Ce qui est interdit, c'est de **conclure sans avoir lu**.
Un axe qui a lu et ne trouve pas de surface pour ses règles rend un rapport légitime — à condition
de **dire ce qu'il a lu** : « lu les 4 fichiers du diff, tous Markdown, aucune surface pour les
règles 1-8 » est un rapport **valide et complet**. Ce n'est pas le décompte de remarques qui
distingue le bon axe du mauvais, c'est la **preuve de lecture**.

**Court-circuit sans lecture — réservé aux règles qui détectent une PRÉSENCE :**

- **Autorisé** : règle 10 (front) si aucun fichier `frontend/` ; règle 11 (dépendances) si aucun manifeste touché. Ces règles jugent quelque chose qui est là ; si ce n'est pas là, il n'y a rien à juger.
- **INTERDIT** : règle 9 (tests). Elle détecte une **absence**. Une US sans un seul test ne touche pas `backend/tests/` — et c'est précisément le défaut que la règle 9 existe pour trouver. Un axe B qui ne voit aucun test **lit le diff et justifie** que l'US n'en appelait pas ; il ne se tait jamais.

En cas de doute sur l'applicabilité d'une règle, **on l'applique**.

### Préambule commun à TOUS les agents — axe D compris

> « Tu es relecteur de code sur le projet **kervignarc** (gestion de tournoi tir à l'arc, archi hexagonale, backend FastAPI/SQLAlchemy sync + front React/TS). Relis le diff `origin/main...HEAD` de la branche d'US courante (US : `<ExxUSyyy>`). **Ne modifie aucun fichier.** Tu couvres **uniquement l'axe ci-dessous** — les autres règles sont traitées par d'autres relecteurs en parallèle, ne les double pas, **à l'exception de la sécurité (ci-dessous), où le doublon est voulu**.
>
> **Ce que tu remontes (restriction dure)** : `<diff intégral | uniquement les fichiers : X, Y>`. Hors de là, ne remonte rien. Cette restriction **prime** sur le périmètre de lecture ci-dessous ; elle ne lève pas l'interdiction de court-circuit de la règle 9 **sur le périmètre donné**.
>
> Rapport structuré : pour chaque remarque → `fichier:ligne`, sévérité (**bloquant** / **majeur** / **mineur** / **suggestion**), description, correctif proposé. Termine par une synthèse (nb par sévérité) et un verdict d'axe : *axe OK* / *corrections requises*. Sois concret et actionnable ; **pas de remarque décorative** — une remarque que l'auteur ne peut pas transformer en diff est du bruit.
>
> **SÉCURITÉ — la seule règle partagée par tous les axes. Traite-la sur ton périmètre, en priorité haute**, même si tu penses qu'un autre la verra : secret ou identifiant en dur ; écriture non protégée par `exiger_admin` alors que la règle des rôles l'exige ; entrée client non validée atteignant le domaine ou la base ; fuite d'un message interne ou d'une trace vers le client ; contrôle d'accès contourné par une route parallèle ; **côté front** : jeton ou secret persisté en clair (`localStorage`), secret embarqué dans le bundle (`import.meta.env`), `dangerouslySetInnerHTML`, log d'un jeton. Une écriture ouverte sans garde-fou = **bloquant**.
>
> **Décharge mécanique** : `<tableau de décharge, ou « SUSPENDUE — le diff touche la configuration des outils »>`. Ne re-vérifie pas ce qui y est marqué prouvé ; **tout le reste est à toi**, y compris les résidus explicités. Un outil **contourné** (`# type: ignore`, `eslint-disable`, `noqa`, `skip`/`xfail`, assertion retirée, denylist non élargie, config assouplie) n'est jamais « vert » : signale-le comme **dette** (axe C2).
>
> **Par où commencer à lire (indicatif, ne restreint RIEN)** : `<périmètre de l'axe>`. Il te dit par où commencer, pas quand te taire : tes règles s'appliquent même si ce périmètre n'est pas touché par le diff. **Tu ne conclus jamais sans avoir lu** ; si tu ne trouves pas de surface pour tes règles, dis **ce que tu as lu** et pourquoi il n'y a rien — c'est un rapport valide. En cas de doute, applique la règle. »

### Axe A — Architecture, frontières & config d'outillage (règles 1-8)

Lecture : `backend/` d'abord. Verdicts structurels, nets.

> « 1. **Isolation du domaine — le résidu que l'AST ne prouve pas.** Le garde-fou est une **denylist d'imports** (`_FORBIDDEN_ROOTS`) : il attrape FastAPI/SQLAlchemy/Pydantic/… et les autres couches, rien d'autre. Restent à **ta** charge, **bloquantes** : (a) un import tiers **absent de la liste** (`requests`, `pandas`, `redis`, toute lib nouvelle) — le domaine n'admet que la stdlib et lui-même ; si le diff en introduit un, la denylist doit être élargie dans le même commit ; (b) le domaine doit rester **synchrone** — un `async def`, un `await`, un `asyncio` dans `domain/` passe le test sans broncher et viole la règle 1.
> 2. **Sens de dépendance** : dépendances pointent vers le domaine ; ports (interfaces) dans le domaine, adapters dans `infrastructure/`. Politiques du moteur = stratégies injectables.
> 3. **Vocabulaire (côté Python)** : métier en français FFTA (`Archer`, `Cible`, `Blason`, `Volee`, `Fleche`, `Duel`, `Depart`, `Categorie`, `Phase`), technique en anglais (`Repository`, `Adapter`, `Service`, `Router`, `Store`). Cohérence code ↔ API ↔ `docs/glossaire.md`. *(Le volet front est à l'axe B, qui lit `frontend/`.)*
> 4. **Typage strict (côté Python) — au-delà de mypy** : immutabilité dans le domaine (dataclasses `frozen`), `Any` **explicite** ou `cast` masquant un vrai trou. Attention : **`backend/migrations/` est exclu de mypy** (`pyproject.toml`) — si le diff y touche, le typage n'y est prouvé par rien.
> 5. **Erreurs typées par couche** : `DomainError`/`ApplicationError`/`InfrastructureError`/`ApiError`, mapping HTTP UNIQUEMENT à la frontière API. Réponse `{ code, message, details? }` ; pas de fuite de message interne au client.
> 6. **Frontière API** : DTO Pydantic distincts des entités domaine/ORM. REST versionné `/api/v1/…`. `Depends` cantonnés à la couche API.
> 7. **SQLite single-writer** : écritures via la file (writer unique), lectures sync hors boucle event, WAL, transactions COURTES. Pas d'aiosqlite.
> 8. **Composition root** : câblage explicite dans `bootstrap/`/`main.py` ; tout nouveau branchement y est reflété.
>
> **Si la décharge est SUSPENDUE** (le diff touche la config des outils), c'est **ta** charge prioritaire : relis `pyproject.toml` (`[tool.mypy]`/`[tool.ruff]`), `.pre-commit-config.yaml`, `ci.yml`, `eslint.config.js`, `tsconfig*.json`, `test_domain_isolation.py` **ligne à ligne**. Tout assouplissement non justifié au corps du commit = **bloquant**. Une porte verte ne prouve rien si le diff a déplacé la porte.
>
> Priorise les **bloquants** : violation de la règle de dépendance, fuite d'erreur interne, écriture SQLite hors file, écriture non protégée, garde-fou affaibli. »

### Axe B — CA, tests, dépendances & front (règles 9-11, + volet front de 3 et 4)

Lecture : `stories/`, `docs/fonctionnel/`, `backend/tests/`, `frontend/`, manifestes — **et
`backend/domain/` + `backend/application/`** : on ne juge pas un test sans voir ce qu'il teste.

> « 9. **Tests — ne court-circuite JAMAIS.** Unitaires priorité domaine, intégration adapters/endpoints, déterministes (pas d'horloge/aléa non maîtrisé). L'**oracle 120** doit rester vert. **Audite les tests eux-mêmes, pas seulement le code qu'ils couvrent** — question à trancher explicitement : *ces tests testent-ils le **CA** de l'US (`stories/Exx-*.md`, puce « CA »), ou le code **tel qu'il est écrit** ?* Un test qui ne fait que refléter l'implémentation (mêmes hypothèses, mêmes oublis, assertions recopiées du comportement observé) ne prouve rien : il passerait tout autant si le CA avait été mal compris. Un CA sans test correspondant, ou couvert par un test qui épouse le code au lieu du CA = **majeur**. **Si le diff n'ajoute aucun test, tu lis le diff et tu justifies** que l'US n'en appelait pas — l'absence de test est ce que cette règle existe pour détecter, elle ne te dispense pas, elle te convoque. **Lis l'implémentation** (`domain/`, `application/`) pour vérifier que le test exerce bien les bornes qu'il prétend couvrir : un test vert sur une fixture à 2 archers ne dit rien d'un service qui teste `> 1` au lieu de `> 0`. Si tu doutes d'une règle métier, **propose 2-3 cas adverses** rédigés en toutes lettres (l'auteur les écrira) ; 2-3 cas ciblés, pas une suite entière. Rappel (`CLAUDE.md` règle 9) : domaine/service se testent **depuis le CA avant** d'implémenter ; pour la non-régression, l'oracle est le comportement actuel et l'auteur est légitime — n'y cherche pas d'indépendance. La suite est verte (porte mécanique) : ne la relance pas, juge ce qu'elle **prouve**.
> 10. **Front React** *(court-circuit autorisé si aucun fichier `frontend/`)* : état serveur via React Query, état UI local via Zustand, organisation par **features** (pas par type technique), ergonomie tactile + indicateur de connexion sur la saisie.
> 11. **Dépendances externes** *(court-circuit autorisé si aucun manifeste touché)* : toute lib ajoutée est (a) déclarée au manifeste DANS le même commit (`pyproject.toml` **et** `requirements.txt` régénéré, jamais édité à la main ; ou `package.json` + `package-lock.json`), (b) **justifiée** (parcimonie, pas de lib « plaisir » — stdlib/qq lignes maison préférées), (c) **sûre**, (d) **documentée** dans `docs/dependances.md`. Dépendance fantôme ou non documentée = **bloquant**. **Sur le (c), l'audit ne te décharge que d'une chose : l'absence de CVE connue.** Restent à toi, et ADR-0009 §2 les exige : **licence compatible** (permissive MIT/BSD/Apache/ISC ; **copyleft à valider explicitement** — une GPL sans CVE passe la porte au vert), lib **activement maintenue**, **largement adoptée**, source officielle, **vigilance typosquatting** (paquet récent ou peu téléchargé au nom voisin d'un connu). Côté npm, une vulnérabilité `moderate`/`low` passe aussi la porte (`--audit-level=high`).
> **3-front. Vocabulaire** : métier en français FFTA, technique en anglais, cohérent avec le backend, l'API et `docs/glossaire.md`.
> **4-front. Typage** : `as` / double cast `as unknown as X` non justifié. *(L'`any` explicite est déchargé : `no-explicit-any` est en erreur via `tseslint.configs.recommended`, et `npm run lint` est dans la porte.)*
>
> Priorise les **bloquants** : dépendance fantôme, oracle cassé, CA non couvert, test absent non justifié. »

### Axe C1 — Correction & cas limites (règle 13)

Lecture : **le diff intégral**, plus la `stories/Exx-*.md` de l'US (puce « CA ») — c'est le second
terme de la moitié de tes conjonctions, tu ne peux pas le chercher sans l'avoir. **Pas de registre
de dette, pas de glossaire, pas de modèle de données** : c'est ce qui te rend rapide. Tu es le
**seul à voir le diff entier** : c'est ta valeur propre.

> « 13. **Qualité générale** (hors règles 1-12 **prises isolément**, traitées par d'autres relecteurs) : bugs de correction, cas limites, lisibilité, duplication évitable, sur-ingénierie hors domaine (l'infra reste simple, mono-club local).
>
> **Les défauts de CONJONCTION sont à toi, et à toi seul.** Les autres axes sont cloisonnés : l'axe B juge un test contre le CA, l'axe A juge une structure. Un défaut qui naît de la **rencontre** de deux axes n'appartient à aucun des deux — il est à toi, parce que tu vois tout. Exemple réel du projet : un service qui teste `if compter_archers(club_id) > 1` (au lieu de `> 0`) **et** un test dont la fixture crée 2 archers → vert des deux côtés, et un club à 1 archer se supprime en silence en laissant un archer orphelin. Ni A (structure saine) ni B (test conforme à un vrai CA) ne peuvent l'attraper. Cherche activement ces paires : une validation faible **et** le test qui l'évite ; un cas d'erreur non traité **et** le CA qui ne le mentionne pas.
>
> Priorise les **bloquants** : ce qui casse un cas utilisateur réel dès maintenant. »

### Axe C2 — Dette, conception & ADR (règles 14-16 + 12-ADR)

Lecture : le diff, la table « Dette ouverte » de `docs/dette.md`, `docs/glossaire.md`,
`docs/modele-de-donnees.md`, plus `git log --format='%h %s%n%b' origin/main..HEAD` (la branche n'est
pas un fichier — c'est un périmètre, pas une exception).

> « **12-ADR.** Lis le log de branche. Le diff contient-il une **décision structurante** (nouveau pattern, politique injectable, frontière, garde-fou, procédure, choix d'outillage) **non couverte** par un ADR de `docs/adr/` ? Le seuil du projet est **bas** : ADR-0008 couvre un choix de gestionnaire de paquets. ADR manquant = **majeur**. C'est à toi et pas à l'auteur : c'est son propre travail que cette question juge, et il est mal placé pour trancher qu'il n'avait pas à écrire d'ADR.
> 14. **Dette technique** — repère ce que le diff introduit ou aggrave comme raccourci assumé : `TODO`/`FIXME`/`type: ignore`/`eslint-disable` sans suivi, contournement temporaire, test désactivé ou affaibli (`skip`, `xfail`, assertion retirée), cas d'erreur non traité, migration Alembic manquante ou divergente du modèle, contrainte FK/index absents, config en dur qui devrait être paramétrée, **configuration d'outil assouplie**. Confronte le diff au registre [`docs/dette.md`](../../docs/dette.md) — **par sa table « Dette ouverte »** ; ne déplie une section « Détail » que pour une dette que le diff touche réellement (la table suffit à répondre « est-ce déjà tracé ? », le détail pèse 3× la table) : une dette assumée doit y être **inscrite dans le même commit** que son introduction (ligne au tableau + détail + marqueur `# DETTE-nnn` à l'endroit exact du raccourci) ; une US qui **aggrave** une dette déjà listée (ex. DETTE-001 : nouvelle table de la descendance de `tournoi` sans politique de suppression) doit élargir la ligne existante au lieu d'inventer un contournement local. Une dette **silencieuse** (absente du registre) introduite par le diff = **majeur** ; une dette qui casse un cas utilisateur réel dès maintenant n'est pas de la dette mais un **bloquant** à corriger avant merge.
> 15. **Dette de conception** — au-delà des règles 1-8, juge si la structure introduite tiendra : responsabilité placée dans la mauvaise couche (métier qui remonte dans le routeur ou descend dans l'adapter), abstraction prématurée ou au contraire absente là où un 3ᵉ appelant arrive, couplage entre features qui devraient s'ignorer, duplication structurelle (2ᵉ chemin qui refait ce qu'un service existant fait déjà — signale la route parallèle plutôt que l'élargissement), entité/modèle qui s'éloigne du `docs/glossaire.md` ou du `docs/modele-de-donnees.md`, invariant métier vérifié à plusieurs endroits au lieu du domaine. Dis explicitement ce que la conception actuelle rendra coûteux **plus tard** et le refactor minimal qui l'évite.
> 16. **Remède structurel — sur preuve, pas sur pronostic.** Quand tu remontes une dette de conception (règle 15), va jusqu'au remède et nomme-le, en t'appuyant sur le vocabulaire de patterns **déjà présent dans le projet** (ports/adapters, stratégie injectable pour les politiques du moteur, repository) plutôt que sur un catalogue importé. Conditions cumulatives : (a) la pression est **constatée dans le code d'aujourd'hui** — 3ᵉ occurrence réelle, invariant déjà dupliqué, port réclamé par la règle 2 — jamais une évolution supposée (2ᵉ club, mode extérieur, futur module) ; (b) tu chiffres le **coût du pattern** (indirection, fichiers, tests) face au coût de ne rien faire ; (c) tu proposes d'abord l'option **« rien »** si elle est défendable. « Pas de pattern : dupliquer une 2ᵉ fois et attendre le 3ᵉ cas » est une réponse **valide et attendue** — un pattern nommé sans les trois conditions est lui-même une remarque de **sur-ingénierie**, donc un défaut (cf. règle 13). Tu **proposes**, tu n'imposes pas : un remède structurel se traite en ADR + US dédiée, jamais en douce dans l'US courante.
>
> Pour 14 et 15 : ne remonte que la dette **imputable au diff** (introduite ou aggravée). Si tu croises de la dette préexistante hors périmètre, vérifie qu'elle figure dans [`docs/dette.md`](../../docs/dette.md) — si oui, ne la remonte pas (elle est déjà tracée) ; sinon, mentionne-la à part, en fin de rapport, en **suggestion** — sans la compter dans le verdict. »

### Axe D — Relecteur adversarial (requis sur changement structurel)

Lecture : le diff, la version d'avant, et **tout ce qu'il juge nécessaire de vérifier lui-même**.
Il est le seul à qui l'on ne donne pas de grille : une grille dirait quoi chercher, or son travail
est de trouver ce que personne n'a pensé à mettre dans une grille.

**Requis** dès que le changement est structurel : procédure de revue, garde-fou, configuration
d'outillage, moteur de placement, politique injectable, frontière de couche, schéma de données.
Facultatif ailleurs.

> « Ta mission n'est **pas** d'appliquer la grille du projet : c'est de **démolir** ce changement. Cherche ce qu'il fait **perdre** — un faux négatif ici est invisible et durable, il tamponnera des US pendant des mois. **Vérifie tout par toi-même** : si le diff prétend qu'un outil prouve quelque chose, va lire la config de l'outil ; ne crois aucun texte sur parole, surtout pas un commentaire rassurant. Cherche les trous **déplacés plutôt que fermés** : quand un correctif ferme le cas signalé, demande-toi **où ailleurs le même raisonnement s'applique** — c'est là que le bug a survécu. Attention particulière à une correction faite **sous pression** : l'auteur vient d'être repris, il a réécrit vite, et il est motivé à croire que c'est réglé.
>
> Pour chaque attaque qui **aboutit** : `fichier:ligne`, sévérité, la faille, un **scénario concret** (quel diff futur passerait à travers), le correctif minimal. Ne remonte que ce que tu peux **étayer** ; si une piste ne mène à rien, dis-le (« piste vérifiée, RAS, parce que… ») — c'est une information utile. **Ne fabrique pas de findings pour paraître utile** : si le changement est bon, le dire franchement est un résultat de première valeur. »

**Ce n'est pas décoratif.** Sur les deux seuls échantillons dont ce projet dispose — les deux tours
de refonte de cette procédure — les axes de conformité ont rendu *axe OK* ou des mineurs, et
**l'agent adversarial a trouvé la totalité des bloquants, les deux fois**. C'est, à ce jour, le seul
dispositif qui ait jamais rien trouvé ici. À défendre la prochaine fois qu'on cherchera à raccourcir
la revue.

## Étape 2 — Synthèse & correction par l'agent auteur (toi)

1. **Fusionne les rapports** en une seule liste, puis **présente-la** à l'utilisateur. C'est ton
   travail, pas celui d'un agent de plus : tu as le contexte de l'US.
   - **Reprends d'abord verbatim le verdict et le décompte par sévérité de chaque axe**, tels que
     rendus (une ligne par axe), avant la liste fusionnée. Puis joins les **rapports bruts en
     annexe, non édités**. Tu es la partie relue et tu détiens l'unique copie des revues : sans
     cette trace, chaque remarque que tu écartes disparaît sans laisser de preuve. Coût quasi nul,
     ils sont déjà en contexte.
   - **Dédoublonne** : deux axes peuvent pointer la même ligne sous deux angles (A « métier dans le
     routeur », C2 « responsabilité dans la mauvaise couche »). Une seule remarque, la **sévérité la
     plus haute** des deux, les deux justifications.
   - **Arbitre les contradictions** plutôt que de les empiler, et **vérifie par toi-même** : deux
     axes peuvent affirmer le contraire sur un fait vérifiable (« TS `strict` interdit l'`any`
     explicite » vs « non, c'est eslint qui le fait »). Va lire la config, tranche sur preuve, dis
     laquelle tu retiens et pourquoi. Si l'opposition est un jugement (A réclame une abstraction que
     C2 juge sur-ingénierie), c'est la **règle 16** qui tranche.
   - **Un axe muet n'est pas un axe vert — mais un axe qui a lu et n'a rien trouvé l'est.** Ce qui
     est irrecevable, c'est de **conclure sans avoir lu** : un axe qui rend *axe OK* doit dire **ce
     qu'il a lu**. « Lu les 4 fichiers du diff, tous Markdown, aucune surface pour les règles 1-8 »
     est un rapport valide et complet ; « sans objet » **sans cette phrase** est un raté de revue —
     relance-le. « Sans objet » sans lecture n'est recevable que pour les pans à court-circuit
     autorisé (règles 10 et 11). Un axe B silencieux sur les tests est toujours un raté.
   - Le **verdict global** est le plus sévère de **tous les rapports rendus, relecteur adversarial
     compris** : un bloquant, d'où qu'il vienne, bloque la PR.
2. Traite chaque remarque :
   - **bloquant / majeur** → corrige dans le code.
   - **mineur / suggestion** → corrige si rapide et sûr ; sinon justifie brièvement de ne pas le faire.
   - **remède structurel proposé (règle 16)** → ne l'implémente **pas** dans l'US courante, même si la remarque est majeure. Vérifie les trois conditions (preuve dans le code, coût chiffré, option « rien » écartée à raison) ; si elles tiennent, inscris la dette au registre et propose l'ADR + l'US dédiée à l'utilisateur. Si elles ne tiennent pas, écarte la remarque en le justifiant — c'est de la sur-ingénierie.
   - **dette (technique ou de conception)** → soit tu la résorbes dans l'US, soit tu l'**assumes explicitement** en suivant la procédure de [`docs/dette.md`](../../docs/dette.md) : ligne au registre + détail, marqueur `# DETTE-nnn` à l'endroit du raccourci, mention dans le corps de la PR, et proposition d'une US de résorption à l'utilisateur. Jamais laissée silencieuse.
3. Après corrections, **repasse la porte** (étape 0.5) sur les fichiers touchés.
4. Prépare le **message de commit** conventionnel des correctifs (`<type>(<scope>): …` + corps quoi/pourquoi + `US: ExxUSyyy`).
5. **Committe et pousse** les correctifs sans demander l'aval — c'est le workflow autonome (`CLAUDE.md` § Workflow) : tu ne rends pas la main pour ça. Seuls `git merge`, `git rebase` et l'ajout de dépendance (règle 11) restent soumis à arbitrage.

## Étape 3 — Boucle & sortie

- S'il restait des **bloquants** non résolus, relance une passe **doublement cadrée** : sur les
  **fichiers touchés par les correctifs** (renseigne le slot « Ce que tu remontes » du préambule), et
  sur les **seuls axes concernés** par ces fichiers. Grille complète de l'axe rejoué, sur ce seul
  périmètre. Le reste du diff a déjà été relu et n'a pas bougé — le refaire relire coûte une passe
  entière pour un résultat connu.

  C'est la **seule exception** à « le périmètre n'est jamais un déclencheur », et elle n'est
  recevable que parce que le diff a **déjà été relu intégralement et n'a pas bougé**. Elle ne rouvre
  pas le trou qu'elle a l'air de rouvrir, à trois conditions **impératives** :
  - **Si les correctifs touchent du code de production** (`domain/`, `application/`, `api/`,
    `infrastructure/`, `frontend/src/`), **l'axe B est rejoué quoi qu'il arrive.** La règle 9 détecte
    une absence : un correctif non testé ne touche aucun fichier de test et n'éveillerait donc jamais
    son propre relecteur — et un correctif écrit sous pression sur le domaine est précisément la
    population où les tests sautent.
  - **Si les correctifs touchent la config des outils**, la décharge devient suspendue et l'axe A est
    rejoué.
  - Si les correctifs ont **débordé** des fichiers déjà relus, tous les axes se rejouent.
- Sinon, fournis la **PR prête** : lien `pull/new/<branche>`, **titre** (`<type>(<ExxUSyyy>): <résumé>`, rappel de l'ID d'US) et **corps** (contexte, ce qui a été fait, remarques de revue traitées, `US: ExxUSyyy`, ADR éventuels). Rappelle que c'est l'utilisateur qui ouvre et merge, puis dit « c'est mergé ».
