---
description: Revue de code d'une US par des agents dédiés en parallèle, puis correction par l'agent auteur (déclenché au « lance la PR »)
argument-hint: "[ExxUSyyy optionnel — sinon déduit de la branche]"
allowed-tools: Bash(git status:*), Bash(git branch:*), Bash(git diff:*), Bash(git log:*), Bash(git fetch:*), Bash(git rev-parse:*), Bash(git merge-base:*), Bash(git add:*), Bash(git commit:*), Bash(git push:*), Bash(ruff:*), Bash(mypy:*), Bash(pytest:*), Bash(npm run:*), Bash(pre-commit:*), Read, Grep, Glob, Edit, Write, Agent
---

# Revue d'US Kervignarc → correction → PR prête

Objectif : quand l'utilisateur dit « lance la PR », faire relire le travail de l'US
par des **agents de revue distincts** (trois axes, en parallèle), puis laisser l'**agent
auteur** (toi) fusionner leurs rapports et intégrer les remarques avant de fournir la PR.
L'utilisateur ouvre et merge la PR lui-même.

**Principe de coût** : ce qu'une machine prouve ne se relit pas à l'œil (porte mécanique, étape 0) ;
ce qui demande du jugement se relit en parallèle, à modèle fort, sans rien retirer de la grille
(étape 1) ; ce qui a déjà été relu et n'a pas bougé ne se relit pas deux fois (étape 3).

US ciblée : `$ARGUMENTS` (si vide, la déduire de la branche courante `<type>/<ExxUSyyy>-<slug>`).

## Étape 0 — Cadrage (toi, l'agent auteur)

1. `git branch --show-current` — vérifier qu'on est sur une **branche d'US** (jamais `main`/`master`). Sinon, stop et prévenir.
2. `git fetch` puis déterminer la base : `git merge-base HEAD origin/main`.
3. Calculer le périmètre de la revue : `git diff --stat origin/main...HEAD` et la liste des fichiers modifiés. Ignorer les artefacts (`node_modules/`, `.venv/`, `dist/`, lockfiles générés sauf incohérence).
4. **Passer la porte mécanique AVANT de dépenser une passe de revue.** Selon les fichiers touchés : `ruff check .` + `mypy --strict --config-file=pyproject.toml .` + `pytest` (depuis `backend/`, venv activé) ; `npm run lint` + `npm run typecheck` (depuis `frontend/`). **Rouge ⇒ tu corriges d'abord, tu ne lances pas la revue** : un diff qui ne passe pas mypy fait relire du code condamné, et l'agent remonterait à l'œil ce que la machine dit en dix secondes.
5. Noter le **résultat de la porte** — il est passé aux relecteurs (voir « décharge mécanique » ci-dessous) et conditionne le périmètre de chaque axe.

## Étape 1 — Revue par des agents DÉDIÉS, en PARALLÈLE

Lance **trois sous-agents** (`Agent`, type `general-purpose`) **dans un seul message** — ils tournent
donc en même temps. Aucun ne modifie quoi que ce soit : chacun lit le diff et rend un rapport.

**Pourquoi trois et pas un.** Un relecteur unique déroule 16 règles en série : le temps mur est leur
somme, et son attention se dilue sur une consigne qui n'en finit pas. Trois relecteurs sur des axes
**disjoints** ramènent le temps mur à celui de l'axe le plus lent (C), à qualité **égale ou
meilleure** — mêmes règles, même diff intégral, chacun avec une consigne courte qu'il traite à fond.
Le découpage suit ce que chaque axe doit **lire** : A ne lit que le code, B lit le CA et les
manifestes, C lit le registre de dette et le glossaire. Aujourd'hui un seul agent charge tout ça dans
un seul contexte.

**Ce qui ne s'optimise pas** : les trois relecteurs gardent le **modèle fort** — c'est la barrière
qualité du projet (`CLAUDE.md` § Économie de contexte). On parallélise la revue, on ne la dégrade pas.
Le coût en tokens monte (~2×, chacun lit le diff) ; c'est le prix assumé du temps mur divisé par ~3.

**Court-circuit de périmètre** : chaque axe reçoit la liste des fichiers modifiés. Si son périmètre
n'est pas touché (US front-only ⇒ axe A ; aucune dépendance ni test ⇒ pans de l'axe B), il répond
**RAS immédiatement, sans lire le diff**. Ne pas court-circuiter par supposition : en cas de doute
sur l'applicabilité d'une règle, **on l'applique**.

### Préambule commun aux trois agents

> « Tu es relecteur de code sur le projet **kervignarc** (gestion de tournoi tir à l'arc, archi hexagonale, backend FastAPI/SQLAlchemy sync + front React/TS). Relis UNIQUEMENT le diff `origin/main...HEAD` de la branche d'US courante (US : `<ExxUSyyy>`). **Ne modifie aucun fichier.** Tu couvres **uniquement l'axe ci-dessous** — les autres règles sont traitées par d'autres relecteurs en parallèle, ne les double pas.
>
> Rapport structuré : pour chaque remarque → `fichier:ligne`, sévérité (**bloquant** / **majeur** / **mineur** / **suggestion**), description, correctif proposé. Termine par une synthèse (nb par sévérité) et un verdict d'axe : *axe OK* / *corrections requises*. Sois concret et actionnable ; **pas de remarque décorative** — une remarque que l'auteur ne peut pas transformer en diff est du bruit.
>
> **Décharge mécanique — ne re-vérifie pas ce que la machine prouve, mais sache exactement ce qu'elle prouve.** Avant cette revue, la porte est passée au vert. Sont **prouvés**, ne les relis pas : les imports de frameworks/couches dans `domain/` (`test_domain_isolation.py`, AST, pre-commit + CI) ; l'absence d'`Any` implicite et la présence des annotations (`mypy --strict`, TS `strict`) ; le lint et le format (ruff/eslint/prettier).
>
> **Ce n'est pas la règle entière pour autant.** La décharge porte sur ce que l'outil vérifie, pas sur l'intitulé de la règle : le garde-fou d'imports est une *denylist* et ignore le caractère synchrone du domaine (règle 1, axe A) ; mypy ne dit rien de l'immutabilité (règle 4, axe A). Ces résidus restent à relire — ils sont écrits dans l'axe concerné.
>
> Un outil **contourné** (`# type: ignore`, `eslint-disable`, `noqa`, `skip`/`xfail`, assertion retirée, denylist non élargie) n'est jamais « vert » : signale-le comme **dette** (axe C).
>
> Fichiers modifiés par le diff : `<liste>`. Si ton axe n'a aucune surface dans ce diff, réponds *axe sans objet* sans lire le diff. En cas de doute sur l'applicabilité d'une règle, applique-la. »

### Axe A — Architecture & frontières (règles 1-8)

Périmètre : `backend/`. Lecture structurelle du code, verdicts nets.

> « 1. **Isolation du domaine — le résidu que l'AST ne prouve pas.** Le garde-fou est une **denylist d'imports** (`_FORBIDDEN_ROOTS`) : il attrape FastAPI/SQLAlchemy/Pydantic/… et les autres couches, rien d'autre. Restent à **ta** charge, et elles sont **bloquantes** : (a) un import tiers **absent de la liste** (`requests`, `pandas`, `redis`, n'importe quelle lib nouvelle) — le domaine n'admet que la stdlib et lui-même ; si le diff en introduit un, la denylist doit être élargie dans le même commit ; (b) le domaine doit rester **synchrone** — un `async def`, un `await`, un `asyncio` dans `domain/` passe le test sans broncher et viole la règle 1.
> 2. **Sens de dépendance** : dépendances pointent vers le domaine ; ports (interfaces) dans le domaine, adapters dans `infrastructure/`. Politiques du moteur = stratégies injectables.
> 3. **Vocabulaire** : métier en français FFTA (`Archer`, `Cible`, `Blason`, `Volee`, `Fleche`, `Duel`, `Depart`, `Categorie`, `Phase`), technique en anglais (`Repository`, `Adapter`, `Service`, `Router`, `Store`). Cohérence code/API/UI/doc.
> 4. **Typage strict — au-delà de mypy** : immutabilité privilégiée dans le domaine (dataclasses `frozen`), `Any` **explicite** ou `cast` qui masque un vrai trou de typage. Le reste est déchargé (cf. préambule).
> 5. **Erreurs typées par couche** : `DomainError`/`ApplicationError`/`InfrastructureError`/`ApiError`, mapping HTTP UNIQUEMENT à la frontière API. Réponse `{ code, message, details? }` ; pas de fuite de message interne au client.
> 6. **Frontière API** : DTO Pydantic distincts des entités domaine/ORM (aucune exposition directe). REST versionné `/api/v1/…`. `Depends` cantonnés à la couche API.
> 7. **SQLite single-writer** : écritures via la file (writer unique), lectures sync hors boucle event, WAL, transactions COURTES, pas de logique métier longue en transaction. Pas d'aiosqlite.
> 8. **Composition root** : câblage explicite dans `bootstrap/`/`main.py` (pas de DI magique) ; tout nouveau branchement y est reflété.
>
> **Sécurité** — traite-la ici, en priorité haute : secret ou identifiant en dur, écriture non protégée par `exiger_admin` alors que la règle des rôles l'exige, entrée client non validée qui atteint le domaine ou la base, fuite d'un message interne / d'une trace vers le client (règle 5), contrôle d'accès contourné par une route parallèle. Une écriture ouverte sans garde-fou = **bloquant**.
>
> Priorise les **bloquants** : violation de la règle de dépendance, fuite d'erreur interne, écriture SQLite hors file, écriture non protégée. »

### Axe B — CA, tests, dépendances & front (règles 9-12)

Périmètre : `backend/tests/`, `frontend/`, manifestes, `stories/`, `docs/fonctionnel/`.
C'est l'axe qui lit le **CA** — les autres n'ont pas à le charger.

> « 9. **Tests** : unitaires priorité domaine (couverture élevée), intégration adapters/endpoints, déterministes (pas d'horloge/aléa non maîtrisé). L'**oracle 120** doit rester vert. Le diff ajoute/maintient les tests attendus. **Audite les tests eux-mêmes, pas seulement le code qu'ils couvrent** — question à trancher explicitement dans ton rapport : *ces tests testent-ils le **CA** de l'US (`stories/Exx-*.md`, `docs/fonctionnel/<ExxUSyyy>.md`), ou le code **tel qu'il est écrit** ?* Un test qui ne fait que refléter l'implémentation (mêmes hypothèses, mêmes oublis, assertions recopiées du comportement observé) ne prouve rien : il passerait tout autant si le CA avait été mal compris. Un CA sans test correspondant, ou couvert par un test qui épouse le code au lieu du CA = **majeur**. Si tu doutes d'une règle métier, **propose 2-3 cas adverses** — ceux que l'auteur a probablement évités — rédigés en toutes lettres dans le rapport (tu ne modifies aucun fichier, c'est l'auteur qui les écrira) ; 2-3 cas ciblés, pas une suite entière. Rappel de la règle 9 de `CLAUDE.md` : domaine/service se testent **depuis le CA avant** d'implémenter ; pour la non-régression, l'oracle est le comportement actuel et l'auteur est légitime — n'y cherche pas d'indépendance. La suite est verte (porte mécanique) : ne la relance pas, juge ce qu'elle **prouve**.
> 10. **Front React** : état serveur via React Query, état UI local via Zustand, organisation par **features** (pas par type technique), ergonomie tactile + indicateur de connexion sur la saisie.
> 11. **Dépendances externes** : toute lib ajoutée est (a) déclarée dans le manifeste DANS le même commit (`pyproject.toml` **et** `requirements.txt` régénéré, jamais édité main ; ou `package.json` + `package-lock.json`), (b) **justifiée** (parcimonie, pas de lib « plaisir » — stdlib/qq lignes maison préférées), (c) **sûre** (audit vert, licence permissive), (d) **documentée** dans `docs/dependances.md`. Une dépendance fantôme ou non documentée = **bloquant**.
> 12. **Traçabilité** : commit conventionnel `<type>(<scope>): <résumé>` cohérent avec le type de branche/US ; décision structurante ⇒ ADR dans `docs/adr/`.
>
> Priorise les **bloquants** : dépendance fantôme, oracle cassé, CA non couvert. »

### Axe C — Qualité, dette & conception (règles 13-16)

Périmètre : diff intégral. C'est l'axe **le plus lent** (jugement ouvert) : il dimensionne le temps
mur, ne le charge pas de ce que A et B couvrent déjà.

> « 13. **Qualité générale** (hors règles 1-12, traitées par d'autres relecteurs) : bugs de correction, cas limites, lisibilité, duplication évitable, sur-ingénierie hors domaine (l'infra reste simple, mono-club local).
> 14. **Dette technique** — repère ce que le diff introduit ou aggrave comme raccourci assumé : `TODO`/`FIXME`/`type: ignore`/`eslint-disable` sans suivi, contournement temporaire, test désactivé ou affaibli (`skip`, `xfail`, assertion retirée), cas d'erreur non traité, migration Alembic manquante ou divergente du modèle, contrainte FK/index absents, config en dur qui devrait être paramétrée. Confronte le diff au registre [`docs/dette.md`](docs/dette.md) — **par sa table « Dette ouverte »** ; ne déplie une section « Détail » que pour une dette que le diff touche réellement (la table suffit à répondre « est-ce déjà tracé ? », le détail pèse 3× la table) : une dette assumée doit y être **inscrite dans le même commit** que son introduction (ligne au tableau + détail + marqueur `# DETTE-nnn` à l'endroit exact du raccourci) ; une US qui **aggrave** une dette déjà listée (ex. DETTE-001 : nouvelle table de la descendance de `tournoi` sans politique de suppression) doit élargir la ligne existante au lieu d'inventer un contournement local. Une dette **silencieuse** (absente du registre) introduite par le diff = **majeur** ; une dette qui casse un cas utilisateur réel dès maintenant n'est pas de la dette mais un **bloquant** à corriger avant merge.
> 15. **Dette de conception** — au-delà des règles 1-8, juge si la structure introduite tiendra : responsabilité placée dans la mauvaise couche (métier qui remonte dans le routeur ou descend dans l'adapter), abstraction prématurée ou au contraire absente là où un 3ᵉ appelant arrive, couplage entre features qui devraient s'ignorer, duplication structurelle (2ᵉ chemin qui refait ce qu'un service existant fait déjà — signale la route parallèle plutôt que l'élargissement), entité/modèle qui s'éloigne du `docs/glossaire.md` ou du `docs/modele-de-donnees.md`, invariant métier vérifié à plusieurs endroits au lieu du domaine. Dis explicitement ce que la conception actuelle rendra coûteux **plus tard** et le refactor minimal qui l'évite.
> 16. **Remède structurel — sur preuve, pas sur pronostic.** Quand tu remontes une dette de conception (règle 15), va jusqu'au remède et nomme-le, en t'appuyant sur le vocabulaire de patterns **déjà présent dans le projet** (ports/adapters, stratégie injectable pour les politiques du moteur, repository) plutôt que sur un catalogue importé. Conditions cumulatives : (a) la pression est **constatée dans le code d'aujourd'hui** — 3ᵉ occurrence réelle, invariant déjà dupliqué, port réclamé par la règle 2 — jamais une évolution supposée (2ᵉ club, mode extérieur, futur module) ; (b) tu chiffres le **coût du pattern** (indirection, fichiers, tests) face au coût de ne rien faire ; (c) tu proposes d'abord l'option **« rien »** si elle est défendable. « Pas de pattern : dupliquer une 2ᵉ fois et attendre le 3ᵉ cas » est une réponse **valide et attendue** — un pattern nommé sans les trois conditions est lui-même une remarque de **sur-ingénierie**, donc un défaut (cf. règle 13). Tu **proposes**, tu n'imposes pas : un remède structurel se traite en ADR + US dédiée, jamais en douce dans l'US courante.
>
> Pour 14 et 15 : ne remonte que la dette **imputable au diff** (introduite ou aggravée). Si tu croises de la dette préexistante hors périmètre, vérifie qu'elle figure dans [`docs/dette.md`](docs/dette.md) — si oui, ne la remonte pas (elle est déjà tracée) ; sinon, mentionne-la à part, en fin de rapport, en **suggestion** — sans la compter dans le verdict. »

## Étape 2 — Synthèse & correction par l'agent auteur (toi)

1. **Fusionne les trois rapports** en une seule liste, puis **présente-la** à l'utilisateur (synthèse
   par sévérité + liste). C'est ton travail, pas celui d'un 4ᵉ agent : tu as le contexte de l'US.
   - **Dédoublonne** : deux axes peuvent pointer la même ligne sous deux angles (A « métier dans le
     routeur », C « responsabilité dans la mauvaise couche »). Une seule remarque, la **sévérité la
     plus haute** des deux, les deux justifications.
   - **Arbitre les contradictions** plutôt que de les empiler : si A réclame une abstraction que C
     qualifie de sur-ingénierie, c'est la règle 16 qui tranche (preuve dans le code d'aujourd'hui,
     sinon « rien »). Dis explicitement laquelle tu retiens et pourquoi.
   - **Un axe muet n'est pas un axe vert** : « axe sans objet » veut dire *périmètre non touché*. Si
     un axe rend un rapport vide alors que son périmètre **est** dans le diff, c'est un raté de
     revue — relance ce seul axe, ne conclus pas *PR OK*.
   - Le **verdict global** est le plus sévère des trois : un bloquant sur un axe bloque la PR.
2. Traite chaque remarque :
   - **bloquant / majeur** → corrige dans le code.
   - **mineur / suggestion** → corrige si rapide et sûr ; sinon justifie brièvement de ne pas le faire.
   - **remède structurel proposé (règle 16)** → ne l'implémente **pas** dans l'US courante, même si la remarque est majeure. Vérifie les trois conditions (preuve dans le code, coût chiffré, option « rien » écartée à raison) ; si elles tiennent, inscris la dette au registre et propose l'ADR + l'US dédiée à l'utilisateur. Si elles ne tiennent pas, écarte la remarque en le justifiant — c'est de la sur-ingénierie.
   - **dette (technique ou de conception)** → soit tu la résorbes dans l'US, soit tu l'**assumes explicitement** en suivant la procédure de [`docs/dette.md`](docs/dette.md) : ligne au registre + détail, marqueur `# DETTE-nnn` à l'endroit du raccourci, mention dans le corps de la PR, et proposition d'une US de résorption à l'utilisateur. Jamais laissée silencieuse.
3. Après corrections, relance localement ce qui est pertinent (ruff/mypy/pytest côté back, eslint/typecheck côté front) selon les fichiers touchés.
4. Prépare le **message de commit** conventionnel des correctifs (`<type>(<scope>): …` + corps quoi/pourquoi + `US: ExxUSyyy`).
5. **Committe et pousse** les correctifs sans demander l'aval — c'est le workflow autonome (`CLAUDE.md` § Workflow) : tu ne rends pas la main pour ça. Seuls `git merge`, `git rebase` et l'ajout de dépendance (règle 11) restent soumis à arbitrage.

## Étape 3 — Boucle & sortie

- S'il restait des **bloquants** non résolus, relance une passe **doublement cadrée** : sur les
  **fichiers touchés par les correctifs**, et sur les **seuls axes concernés** par ces fichiers (un
  correctif de test ne réveille pas l'axe A). Grille complète de l'axe rejoué, sur ce seul périmètre.
  Le reste du diff a déjà été relu et n'a pas bougé — le refaire relire coûte une passe entière (diff
  intégral + registre de dette) pour un résultat connu. Les trois axes ne se rejouent intégralement
  que si les correctifs ont **débordé** des fichiers déjà relus.
- Sinon, fournis la **PR prête** : lien `pull/new/<branche>`, **titre** (`<type>(<ExxUSyyy>): <résumé>`, rappel de l'ID d'US) et **corps** (contexte, ce qui a été fait, remarques de revue traitées, `US: ExxUSyyy`, ADR éventuels). Rappelle que c'est l'utilisateur qui ouvre et merge, puis dit « c'est mergé ».
