---
description: Revue de code d'une US par des agents dédiés en parallèle, puis correction par l'agent auteur (déclenché au « lance la PR »)
argument-hint: "[ExxUSyyy optionnel — sinon déduit de la branche]"
allowed-tools: Bash(git status:*), Bash(git branch:*), Bash(git diff:*), Bash(git log:*), Bash(git fetch:*), Bash(git rev-parse:*), Bash(git merge-base:*), Bash(git add:*), Bash(git commit:*), Bash(git push:*), Read, Grep, Glob, Edit, Write, Agent
---

# Revue d'US Kervignarc → correction → PR prête

Objectif : quand l'utilisateur dit « lance la PR », faire relire le travail de l'US par des **agents
de revue distincts** (quatre axes, en parallèle), puis laisser l'**agent auteur** (toi) fusionner
leurs rapports et intégrer les remarques avant de fournir la PR. L'utilisateur ouvre et merge la PR
lui-même. Cette procédure est fixée par [ADR-0013](../../docs/adr/0013-conduite-de-la-revue-d-us.md).

**Principe de coût** : ce qu'une machine prouve ne se relit pas à l'œil (porte mécanique, étape 0) ;
ce qui demande du jugement se relit en parallèle, à modèle fort, sans rien retirer de la grille
(étape 1) ; ce qui a déjà été relu et n'a pas bougé ne se relit pas deux fois (étape 3).

**Le contre-principe, qui prime** : une revue qui va vite et ne voit rien ne sert à rien. Un faux
négatif ici est invisible et durable — il tamponnera des US pendant des mois. Chaque fois que les
deux principes s'opposent, **c'est la détection qui gagne**.

**Où vivent les grilles.** Chaque relecteur est un **agent versionné** de `.claude/agents/` —
`revue-axe-a`, `-b`, `-c1`, `-c2`, `-d` — qui porte sa grille, son modèle **épinglé** et ses outils
**restreints** (ni `Edit` ni `Write`). Cette commande ne redit pas les grilles : elle orchestre et
transmet le préambule commun. Une grille se modifie dans son fichier d'agent, une seule fois.

US ciblée : `$ARGUMENTS` (si vide, la déduire de la branche courante `<type>/<ExxUSyyy>-<slug>`).

## Étape 0 — Cadrage (toi, l'agent auteur)

1. **Noter l'heure** (`date`) — c'est la première des deux bornes de `durée porte`. Puis `git branch --show-current` : vérifier qu'on est sur une **branche d'US** (jamais `main`/`master`). Sinon, stop et prévenir.
2. `git fetch` puis déterminer la base : `git merge-base HEAD origin/main`.
3. Calculer le périmètre : `git diff --stat origin/main...HEAD` et la liste des fichiers modifiés. Ignorer les artefacts (`node_modules/`, `.venv/`, `dist/`, lockfiles générés sauf incohérence). **Repère de détection pour l'axe B (règle 9-doc)** : le diff touche-t-il `frontend/src/**` **sans** ajouter ni compléter un `docs/fonctionnel/<ExxUSyyy>.md` ? Si oui, c'est le signal d'une **fiche fonctionnelle manquante** — passe-le explicitement à l'axe B, qui tranchera (fiche due et absente = bloquant, ou US purement outillage front à justifier).
4. **Règle 12 — le format, ici ; le jugement, à un relecteur.** `git log --format='%h %s%n%b' origin/main..HEAD`. Tu vérifies toi-même le **factuel** : type/scope conventionnel, cohérence avec la branche, corps qui explique le quoi **et** le pourquoi, références présentes. Tu **ne juges pas** « décision structurante ⇒ ADR » : c'est la seule règle des seize dont l'objet est de rattraper ce que **tu** as escamoté, et te la confier la neutralise. Elle est à l'axe C2 ; passe-lui le log en périmètre. *(Preuve que ce n'est pas théorique : le commit `b47b25c` — refonte de cette procédure même — a été livré sans ADR, et c'est un relecteur tiers qui l'a rattrapé. ADR-0013 n'existerait pas autrement.)*
5. **Passer la porte mécanique AVANT de dépenser une passe de revue** — via l'agent **`porte-mecanique`**, à qui tu passes la liste des fichiers touchés. Il lit `.github/workflows/ci.yml`, exécute les étapes concernées, et te rend la liste verbatim des `run:` qu'il y a trouvés, un `EXIT` par commande, et les échecs non résumés. **La sortie volumineuse des tests reste dans son contexte, pas dans le tien.**

   ⚠️ **Ouvre `.github/workflows/ci.yml` et compare toi-même** — `grep -n 'run:' .github/workflows/ci.yml`, une dizaine de lignes — plutôt que de recouper le rapport de l'agent avec lui-même. Un exécutant qui omet une étape l'omet **aussi de sa transcription** : les deux colonnes concordent alors sans rien prouver, et c'est exactement l'auto-cohérence que `CLAUDE.md` § Cycle de branche décrit pour le hook de l'atlas (« il compare du périmé à du périmé »). Ce que l'agent apporte, c'est de lire `ci.yml` **au lieu** d'une liste recopiée ; ce que toi seul apportes, c'est un **second regard indépendant** — il coûte un `grep`. Si la section verbatim manque au rapport, ou si elle diverge de ce que tu lis, **le rapport est nul et non avenu**.

   Vérifie ensuite que les omissions sont bien les **deux** énumérées dans `porte-mecanique.md` — installation des dépendances Python, synchro `requirements.txt`↔`pyproject.toml` — et **rien d'autre** : `npm ci` en particulier doit avoir tourné. Toute autre divergence est un bug de cette procédure. *(Ce contrôle n'est pas décoratif : la liste que cette commande portait en dur avait divergé de `ci.yml` **deux fois** — `npm test` manquant depuis sa rédaction, découvert le 15/08/2026 sur E05US028, puis le job `atlas` jamais mentionné.)*

   **Rouge ou INCOMPLÈTE ⇒ tu corriges d'abord, tu ne lances pas la revue** : un diff qui ne passe pas mypy fait relire du code condamné, et une porte incomplète ne prouve rien. Seule interprétation qui t'appartient : `python -m atlas --verifier` rouge **peut** être le cas connu de régénération post-commit (`CLAUDE.md` § Cycle de branche) — auquel cas tu **régénères** (`cd backend && python -m atlas`), tu **commites** la carte et tu **redemandes la porte**. Un atlas rouge ne franchit jamais l'étape 0. La CI garde le dernier mot.
6. **Décider si la décharge s'applique** (voir ci-dessous). Si elle est suspendue, **note les fichiers qui la suspendent** : c'est cette liste, et pas le seul mot « SUSPENDUE », qui est passée à l'axe A.
7. **Noter l'heure une seconde fois** (la première est au point 1) : les deux bornes donnent `durée porte` dans [`docs/metriques-revue.md`](../../docs/metriques-revue.md).

### La décharge mécanique — et sa suspension

Ce que les outils **prouvent**, les relecteurs ne le relisent pas. Ce que la décharge couvre, **exactement** :

| Prouvé par | Ce qui est déchargé | Ce qui ne l'est PAS |
|---|---|---|
| `test_domain_isolation.py` (AST) | imports de `domain/` visant les **frameworks listés** dans `_FORBIDDEN_ROOTS` et les autres couches | tout import tiers **hors liste** ; le caractère **synchrone** du domaine (règle 1, axe A) |
| `mypy .` (strict) | `Any` implicite, annotations manquantes — **sauf `backend/migrations/`, exclu par `pyproject.toml`** | l'immutabilité (`frozen`), l'`Any` **explicite**, le `cast` qui masque un trou (règle 4, axe A) |
| `ruff` / `eslint` / `prettier` | lint, format, `no-explicit-any` côté TS (via `tseslint.configs.recommended`) | le `noqa` / `eslint-disable` qui **contourne** la règle au lieu de la satisfaire (→ dette, axe C2) |
| `pip-audit` / `npm audit` | **une seule chose** : l'absence de **vulnérabilité connue** — et côté npm, **au seuil `high` et au-dessus** seulement | **tout le reste de la règle 11-c** : la **licence** (permissive MIT/BSD/Apache/ISC ; copyleft à valider — `CLAUDE.md` règle 11, ADR-0009 §2), la **maintenance**, l'**adoption**, le **typosquatting** ; les vulns npm `moderate`/`low` ; la justification (11-b) et la documentation (11-d). Tout cela reste à l'axe B |
| `python -m atlas --verifier` | l'atlas généré est identique au dépôt | rien d'autre — l'atlas cartographie, il ne juge pas |

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
casse le garde-fou sans que la CI le voie), **`.claude/settings.json`** (une permission retirée
empêche une étape de tourner sans rien faire rougir), et **tout `.claude/agents/**` ou
`.claude/commands/revue-us.md`** — les grilles définissent ce que la revue **vérifie**, la commande
définit ce qui est **déchargé**, `porte-mecanique.md` définit ce qui est **exécuté** : les trois sont
la porte au même titre que `ci.yml`.

⚠️ **Ne cite jamais un seul fichier de `.claude/` dans cette énumération sans ses frères.** Une liste
qui nomme `porte-mecanique.md` et tait `revue-axe-a.md` s'interprète *a contrario* : l'auteur d'un
futur diff qui affaiblirait une grille constatera que son fichier n'y figure pas. C'est le mode exact
par lequel ce garde-fou a été percé la première fois.

Suspension ⇒ **passe aux agents la liste des fichiers en cause**, pas seulement le mot « SUSPENDUE » :
l'axe A porte le principe, pas l'énumération, et il ne peut pas deviner lesquels relire. Il les relit
**ligne à ligne**. Tout
assouplissement (exclusion élargie, `disable_error_code`, `addopts` qui saute un test, script npm
neutralisé, ajout à `ignore`, étape CI retirée, hook supprimé, denylist non élargie) est
**bloquant** sauf justification explicite au corps du commit.

## Étape 1 — Revue par les agents dédiés, en PARALLÈLE

Lance **quatre sous-agents** — `revue-axe-a`, `revue-axe-b`, `revue-axe-c1`, `revue-axe-c2` —
**cinq** si le changement est structurel, en ajoutant `revue-axe-d` : le relecteur **adversarial** est
un axe à part entière, pas un bonus. **Requis** dès que le changement touche une procédure de revue,
un garde-fou, une configuration d'outillage, le moteur de placement, une politique injectable, une
frontière de couche ou un schéma de données. Facultatif ailleurs.

**Tous dans un seul message**, donc en même temps. Chacun reçoit le préambule commun ci-dessous et
rend un rapport au même format, verdict compris.

**Pourquoi quatre et pas un.** Un relecteur unique déroule 16 règles en série : le temps mur est leur
somme, et son attention se dilue. Quatre relecteurs sur des axes disjoints ramènent le temps mur à
celui de l'axe le plus lent, à qualité égale ou meilleure — mêmes règles, chacun avec une consigne
courte qu'il traite à fond.

**Ce qui ne s'optimise pas** : les relecteurs gardent le **modèle fort** — barrière qualité du projet
(`CLAUDE.md` § Économie de contexte). C'est désormais **épinglé** dans le frontmatter de chaque agent
(`model: opus`), donc insensible au modèle de la session : une US menée en Sonnet pour raison de coût
ne dégrade plus sa propre revue en silence. On parallélise la revue, on ne la dégrade pas.

**Gain attendu ~2×** sur le temps mur, pour un coût en tokens de ~2,5×. Honnêteté sur ce chiffre :
le chemin critique est `max(A, B, C1, C2, D)` et il **n'a jamais été mesuré** — c'est exactement ce
que [`metriques-revue.md`](../../docs/metriques-revue.md) sert à établir, passe après
passe.

### Concordance des numéros — à lire avant la grille

La grille reprend les **règles 1-11** de `CLAUDE.md` § Règles non négociables, **mêmes numéros**. Les
règles **12 à 16 sont propres à la revue** et ne correspondent PAS à la numérotation de `CLAUDE.md` :
en particulier, la règle **12 de `CLAUDE.md`** (« simplicité assumée hors domaine ») est couverte ici
par la règle **13**, et la règle **12 de la grille** (traçabilité) n'existe pas dans `CLAUDE.md`.
`9-doc` (fiche fonctionnelle) n'y existe pas non plus.

⚠️ Cette numérotation vit désormais **à la main dans sept fichiers** (cette commande + les cinq
grilles + `CLAUDE.md`) au lieu de deux. Quand l'une bouge, propager à toutes — c'est le coût de
maintenance qu'ADR-0013 assume, aggravé par la décision 8. `<!-- DETTE-068 -->`

### Périmètre : une aide à la LECTURE, jamais un déclencheur

Le périmètre d'un axe dit **par où commencer à lire**. Il ne dit **pas** quand se taire. Les règles
d'un axe s'appliquent **toujours**, que leur périmètre soit touché ou non.

**Le seul discriminant est : AS-TU LU ?** Ce qui est interdit, c'est de **conclure sans avoir lu**.
Un axe qui a lu et ne trouve pas de surface pour ses règles rend un rapport légitime — à condition
de **dire ce qu'il a lu** : « lu les 4 fichiers du diff, tous Markdown, aucune surface pour les
règles 1-8 » est un rapport **valide et complet**. Ce n'est pas le décompte de remarques qui
distingue le bon axe du mauvais, c'est la **preuve de lecture**.

**Court-circuit sans lecture — réservé aux règles qui détectent une PRÉSENCE :**

- **Autorisé** : règle 10 (front) si aucun fichier `frontend/` ; règle 11 (dépendances) si aucun manifeste touché.
- **INTERDIT** : règle 9 (tests) et règle 9-doc (fiche fonctionnelle). Elles détectent une **absence**. Une US sans un seul test ne touche pas `backend/tests/` — et c'est précisément le défaut que la règle 9 existe pour trouver.

En cas de doute sur l'applicabilité d'une règle, **on l'applique**.

### Préambule commun — à passer VERBATIM à TOUS les agents, axe D compris

⚠️ **Verbatim veut dire verbatim : ni résumé, ni reformulé, ni abrégé.** Tu le recopies à la main à
chaque lancement, et une consigne perdue à la transcription ne produit **aucun symptôme** — un axe
qui ne cherche pas une chose rend le même rapport qu'un axe qui ne la trouve pas. *(Ce n'est pas
théorique : à la toute première passe sous ce régime, l'auteur a transmis la règle de sécurité
réduite à son titre. C'est la raison pour laquelle elle vit maintenant dans les cinq grilles et non
ici.)*

> « Relis le diff `origin/main...HEAD` de la branche d'US courante (US : `<ExxUSyyy>`). Ta grille est
> dans ta propre définition d'agent ; ce qui suit la complète.
>
> **Ce que tu remontes (restriction dure)** : `<diff intégral | uniquement les fichiers : X, Y>`. Hors de là, ne remonte rien. Cette restriction **prime** sur le périmètre de lecture de ta définition ; elle ne lève pas l'interdiction de court-circuit des règles 9 et 9-doc **sur le périmètre donné**.
>
> Rapport structuré : pour chaque remarque → `fichier:ligne`, sévérité (**bloquant** / **majeur** / **mineur** / **suggestion**), description, correctif proposé. Termine par une synthèse (nb par sévérité), un verdict d'axe (*axe OK* / *corrections requises*) et une ligne `Durée : <hh:mm> → <hh:mm>`. Sois concret et actionnable ; **pas de remarque décorative** — une remarque que l'auteur ne peut pas transformer en diff est du bruit.
>
> **Décharge mécanique** : `<tableau de décharge, ou « SUSPENDUE — le diff touche : <liste des fichiers en cause> »>`. Ne re-vérifie pas ce qui y est marqué prouvé ; **tout le reste est à toi**, y compris les résidus explicités. Un outil **contourné** (`# type: ignore`, `eslint-disable`, `noqa`, `skip`/`xfail`, assertion retirée, denylist non élargie, config assouplie, permission retirée) n'est jamais « vert » : signale-le comme **dette** (axe C2).
>
> **Périmètre** : ta définition te dit par où commencer, pas quand te taire — tes règles s'appliquent même si ce périmètre n'est pas touché par le diff. **Tu ne conclus jamais sans avoir lu** ; si tu ne trouves pas de surface pour tes règles, dis **ce que tu as lu** et pourquoi il n'y a rien — c'est un rapport valide. En cas de doute, applique la règle. »

**La règle de sécurité n'est pas ici** : elle vit dans les **cinq** définitions d'agents, à
l'identique. C'est la seule règle que le projet double délibérément (ADR-0013, décision 4) ; la
charger avec la grille, plutôt que de la retranscrire, est ce qui l'empêche de se perdre.

## Étape 2 — Synthèse & correction par l'agent auteur (toi)

1. **Fusionne les rapports** en une seule liste, puis **présente-la** à l'utilisateur. C'est ton
   travail, pas celui d'un agent de plus : tu as le contexte de l'US.
   - **Reprends d'abord verbatim le verdict et le décompte par sévérité de chaque axe**, tels que
     rendus (une ligne par axe), avant la liste fusionnée. Puis joins les **rapports bruts en
     annexe, non édités**. Tu es la partie relue et tu détiens l'unique copie des revues : sans
     cette trace, chaque remarque que tu écartes disparaît sans laisser de preuve.
   - **Dédoublonne** : deux axes peuvent pointer la même ligne sous deux angles (A « métier dans le
     routeur », C2 « responsabilité dans la mauvaise couche »). Une seule remarque, la **sévérité la
     plus haute** des deux, les deux justifications.
   - **Arbitre les contradictions** plutôt que de les empiler, et **vérifie par toi-même** : deux
     axes peuvent affirmer le contraire sur un fait vérifiable (« TS `strict` interdit l'`any`
     explicite » vs « non, c'est eslint qui le fait »). Va lire la config, tranche sur preuve, dis
     laquelle tu retiens et pourquoi. Si l'opposition est un jugement (A réclame une abstraction que
     C2 juge sur-ingénierie), c'est la **règle 16** qui tranche.
   - **Un axe muet n'est pas un axe vert — mais un axe qui a lu et n'a rien trouvé l'est.** Un axe
     qui rend *axe OK* doit dire **ce qu'il a lu**. « Sans objet » **sans cette phrase** est un raté
     de revue — relance-le. Recevable sans lecture uniquement pour les pans à court-circuit autorisé
     (règles 10 et 11). Un axe B silencieux sur les tests est toujours un raté.
   - Le **verdict global** est le plus sévère de **tous les rapports rendus, relecteur adversarial
     compris** : un bloquant, d'où qu'il vienne, bloque la PR.
2. Traite chaque remarque :
   - **bloquant / majeur** → corrige dans le code.
   - **mineur / suggestion** → corrige si rapide et sûr ; sinon justifie brièvement de ne pas le faire.
   - **remède structurel proposé (règle 16)** → ne l'implémente **pas** dans l'US courante, même si la remarque est majeure. Vérifie les trois conditions (preuve dans le code, coût chiffré, option « rien » écartée à raison) ; si elles tiennent, inscris la dette au registre et propose l'ADR + l'US dédiée à l'utilisateur. Si elles ne tiennent pas, écarte la remarque en le justifiant — c'est de la sur-ingénierie.
   - **dette (technique ou de conception)** → soit tu la résorbes dans l'US, soit tu l'**assumes explicitement** en suivant la procédure de [`docs/dette.md`](../../docs/dette.md) : ligne au registre + détail, marqueur `# DETTE-nnn` à l'endroit du raccourci, mention dans le corps de la PR, et proposition d'une US de résorption à l'utilisateur. Jamais laissée silencieuse.
3. Après corrections, **repasse la porte complète** via l'agent `porte-mecanique`, sur les jobs concernés par les fichiers touchés. **Pas de porte partielle, pas de `pytest` restreint à un chemin** : la décision 1 d'ADR-0013 dit qu'« une commande approchante n'est pas la même mesure », et un correctif écrit sous pression est exactement la population où la suite complète sert. Les ~3 min se dépensent en tâche de fond, une fois par passe.
4. **Renseigne une ligne** dans [`docs/metriques-revue.md`](../../docs/metriques-revue.md) : les deux bornes de l'étape 0 donnent `durée porte`, les lignes `Durée :` des rapports donnent `axe le + lent`, et la colonne décisive est **quel axe a trouvé les bloquants**. C'est la seule mesure dont ADR-0013 admet manquer.
5. Prépare le **message de commit** conventionnel des correctifs (`<type>(<scope>): …` + corps quoi/pourquoi + `US: ExxUSyyy`).
6. **Committe et pousse** les correctifs sans demander l'aval — c'est le workflow autonome (`CLAUDE.md` § Workflow) : tu ne rends pas la main pour ça. Seuls `git merge`, `git rebase` et l'ajout de dépendance (règle 11) restent soumis à arbitrage.

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
  - **Si les correctifs touchent la config des outils** — au sens du principe ci-dessus, donc
    `.claude/settings.json`, `.claude/agents/**` et cette commande compris — la décharge devient
    suspendue et l'axe A est rejoué.
  - Si les correctifs ont **débordé** des fichiers déjà relus, tous les axes se rejouent.
- Sinon, fournis la **PR prête** : lien `pull/new/<branche>`, **titre** (`<type>(<ExxUSyyy>): <résumé>`, rappel de l'ID d'US) et **corps** (contexte, ce qui a été fait, remarques de revue traitées, `US: ExxUSyyy`, ADR éventuels). Rappelle que c'est l'utilisateur qui ouvre et merge, puis dit « c'est mergé ».
