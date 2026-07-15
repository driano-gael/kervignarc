---
description: Revue de code d'une US par un agent dédié, puis correction par l'agent auteur (déclenché au « lance la PR »)
argument-hint: "[ExxUSyyy optionnel — sinon déduit de la branche]"
allowed-tools: Bash(git status:*), Bash(git branch:*), Bash(git diff:*), Bash(git log:*), Bash(git fetch:*), Bash(git rev-parse:*), Bash(git merge-base:*), Read, Grep, Glob, Edit, Write, Agent
---

# Revue d'US Kervignarc → correction → PR prête

Objectif : quand l'utilisateur dit « lance la PR », faire relire le travail de l'US
par un **agent de revue distinct**, puis laisser l'**agent auteur** (toi) intégrer
les remarques avant de fournir la PR. L'utilisateur ouvre et merge la PR lui-même.

US ciblée : `$ARGUMENTS` (si vide, la déduire de la branche courante `<type>/<ExxUSyyy>-<slug>`).

## Étape 0 — Cadrage (toi, l'agent auteur)

1. `git branch --show-current` — vérifier qu'on est sur une **branche d'US** (jamais `main`/`master`). Sinon, stop et prévenir.
2. `git fetch` puis déterminer la base : `git merge-base HEAD origin/main`.
3. Calculer le périmètre de la revue : `git diff --stat origin/main...HEAD` et la liste des fichiers modifiés. Ignorer les artefacts (`node_modules/`, `.venv/`, `dist/`, lockfiles générés sauf incohérence).

## Étape 1 — Revue par un agent DÉDIÉ (différent de l'auteur)

Lance **un sous-agent** (`Agent`, type `general-purpose`) avec la consigne ci-dessous.
Cet agent ne modifie RIEN : il lit le diff et remonte des remarques structurées.

> Consigne à passer à l'agent de revue (adapter l'ID d'US et la base) :
>
> « Tu es relecteur de code sur le projet **kervignarc** (gestion de tournoi tir à l'arc, archi hexagonale, backend FastAPI/SQLAlchemy sync + front React/TS). Relis UNIQUEMENT le diff `origin/main...HEAD` de la branche d'US courante. Ne modifie aucun fichier. Rends un rapport structuré : pour chaque remarque → `fichier:ligne`, sévérité (**bloquant** / **majeur** / **mineur** / **suggestion**), description, correctif proposé. Termine par une synthèse (nb par sévérité) et un verdict : *PR OK* / *corrections requises*.
>
> Grille de revue — conventions projet (`guide-architecture.md`) :
> 1. **Isolation du domaine** : `domain/` n'importe AUCUN framework (FastAPI, SQLAlchemy, Pydantic) ni autre couche (`api/`, `application/`, `infrastructure/`, `bootstrap/`). Domaine pur & synchrone.
> 2. **Sens de dépendance** : dépendances pointent vers le domaine ; ports (interfaces) dans le domaine, adapters dans `infrastructure/`. Politiques du moteur = stratégies injectables.
> 3. **Vocabulaire** : métier en français FFTA (`Archer`, `Cible`, `Blason`, `Volee`, `Fleche`, `Duel`, `Depart`, `Categorie`, `Phase`), technique en anglais (`Repository`, `Adapter`, `Service`, `Router`, `Store`). Cohérence code/API/UI/doc.
> 4. **Typage strict** : mypy strict côté Python (pas de `Any` implicite), TS `strict` (pas de `any` non justifié). Annotations partout. Immutabilité privilégiée dans le domaine (dataclasses `frozen`).
> 5. **Erreurs typées par couche** : `DomainError`/`ApplicationError`/`InfrastructureError`/`ApiError`, mapping HTTP UNIQUEMENT à la frontière API. Réponse `{ code, message, details? }` ; pas de fuite de message interne au client.
> 6. **Frontière API** : DTO Pydantic distincts des entités domaine/ORM (aucune exposition directe). REST versionné `/api/v1/…`. `Depends` cantonnés à la couche API.
> 7. **SQLite single-writer** : écritures via la file (writer unique), lectures sync hors boucle event, WAL, transactions COURTES, pas de logique métier longue en transaction. Pas d'aiosqlite.
> 8. **Composition root** : câblage explicite dans `bootstrap/`/`main.py` (pas de DI magique) ; tout nouveau branchement y est reflété.
> 9. **Tests** : unitaires priorité domaine (couverture élevée), intégration adapters/endpoints, déterministes (pas d'horloge/aléa non maîtrisé). L'**oracle 120** doit rester vert. Le diff ajoute/maintient les tests attendus. **Audite les tests eux-mêmes, pas seulement le code qu'ils couvrent** — question à trancher explicitement dans ton rapport : *ces tests testent-ils le **CA** de l'US (`stories/Exx-*.md`, `docs/fonctionnel/<ExxUSyyy>.md`), ou le code **tel qu'il est écrit** ?* Un test qui ne fait que refléter l'implémentation (mêmes hypothèses, mêmes oublis, assertions recopiées du comportement observé) ne prouve rien : il passerait tout autant si le CA avait été mal compris. Un CA sans test correspondant, ou couvert par un test qui épouse le code au lieu du CA = **majeur**. Si tu doutes d'une règle métier, **propose 2-3 cas adverses** — ceux que l'auteur a probablement évités — rédigés en toutes lettres dans le rapport (tu ne modifies aucun fichier, c'est l'auteur qui les écrira) ; 2-3 cas ciblés, pas une suite entière. Rappel de la règle 9 de `CLAUDE.md` : domaine/service se testent **depuis le CA avant** d'implémenter ; pour la non-régression, l'oracle est le comportement actuel et l'auteur est légitime — n'y cherche pas d'indépendance.
> 10. **Front React** : état serveur via React Query, état UI local via Zustand, organisation par **features** (pas par type technique), ergonomie tactile + indicateur de connexion sur la saisie.
> 11. **Dépendances externes** : toute lib ajoutée est (a) déclarée dans le manifeste DANS le même commit (`pyproject.toml` **et** `requirements.txt` régénéré, jamais édité main ; ou `package.json` + `package-lock.json`), (b) **justifiée** (parcimonie, pas de lib « plaisir » — stdlib/qq lignes maison préférées), (c) **sûre** (audit vert, licence permissive), (d) **documentée** dans `docs/dependances.md`. Une dépendance fantôme ou non documentée = **bloquant**.
> 12. **Traçabilité** : commit conventionnel `<type>(<scope>): <résumé>` cohérent avec le type de branche/US ; décision structurante ⇒ ADR dans `docs/adr/`.
> 13. **Qualité générale** (hors conventions ci-dessus) : bugs de correction, cas limites, lisibilité, duplication évitable, sur-ingénierie hors domaine (l'infra reste simple, mono-club local).
> 14. **Dette technique** — repère ce que le diff introduit ou aggrave comme raccourci assumé : `TODO`/`FIXME`/`type: ignore`/`eslint-disable` sans suivi, contournement temporaire, test désactivé ou affaibli (`skip`, `xfail`, assertion retirée), cas d'erreur non traité, migration Alembic manquante ou divergente du modèle, contrainte FK/index absents, config en dur qui devrait être paramétrée. Confronte le diff au registre [`docs/dette.md`](docs/dette.md) : une dette assumée doit y être **inscrite dans le même commit** que son introduction (ligne au tableau + détail + marqueur `# DETTE-nnn` à l'endroit exact du raccourci) ; une US qui **aggrave** une dette déjà listée (ex. DETTE-001 : nouvelle table de la descendance de `tournoi` sans politique de suppression) doit élargir la ligne existante au lieu d'inventer un contournement local. Une dette **silencieuse** (absente du registre) introduite par le diff = **majeur** ; une dette qui casse un cas utilisateur réel dès maintenant n'est pas de la dette mais un **bloquant** à corriger avant merge.
> 15. **Dette de conception** — au-delà des règles 1-8, juge si la structure introduite tiendra : responsabilité placée dans la mauvaise couche (métier qui remonte dans le routeur ou descend dans l'adapter), abstraction prématurée ou au contraire absente là où un 3ᵉ appelant arrive, couplage entre features qui devraient s'ignorer, duplication structurelle (2ᵉ chemin qui refait ce qu'un service existant fait déjà — signale la route parallèle plutôt que l'élargissement), entité/modèle qui s'éloigne du `docs/glossaire.md` ou du `docs/modele-de-donnees.md`, invariant métier vérifié à plusieurs endroits au lieu du domaine. Dis explicitement ce que la conception actuelle rendra coûteux **plus tard** et le refactor minimal qui l'évite.
> 16. **Remède structurel — sur preuve, pas sur pronostic.** Quand tu remontes une dette de conception (règle 15), va jusqu'au remède et nomme-le, en t'appuyant sur le vocabulaire de patterns **déjà présent dans le projet** (ports/adapters, stratégie injectable pour les politiques du moteur, repository) plutôt que sur un catalogue importé. Conditions cumulatives : (a) la pression est **constatée dans le code d'aujourd'hui** — 3ᵉ occurrence réelle, invariant déjà dupliqué, port réclamé par la règle 2 — jamais une évolution supposée (2ᵉ club, mode extérieur, futur module) ; (b) tu chiffres le **coût du pattern** (indirection, fichiers, tests) face au coût de ne rien faire ; (c) tu proposes d'abord l'option **« rien »** si elle est défendable. « Pas de pattern : dupliquer une 2ᵉ fois et attendre le 3ᵉ cas » est une réponse **valide et attendue** — un pattern nommé sans les trois conditions est lui-même une remarque de **sur-ingénierie**, donc un défaut (cf. règle 13). Tu **proposes**, tu n'imposes pas : un remède structurel se traite en ADR + US dédiée, jamais en douce dans l'US courante.
>
> Pour 14 et 15 : ne remonte que la dette **imputable au diff** (introduite ou aggravée). Si tu croises de la dette préexistante hors périmètre, vérifie qu'elle figure dans [`docs/dette.md`](docs/dette.md) — si oui, ne la remonte pas (elle est déjà tracée) ; sinon, mentionne-la à part, en fin de rapport, en **suggestion** — sans la compter dans le verdict.
>
> Priorise les **bloquants** (violations de la règle de dépendance, dépendance fantôme, fuite d'erreur interne, oracle cassé, écriture SQLite hors file) puis le reste. Sois concret et actionnable ; pas de remarque décorative. »

## Étape 2 — Correction par l'agent auteur (toi)

1. Récupère le rapport de l'agent de revue et **présente-le** à l'utilisateur (synthèse + liste).
2. Traite chaque remarque :
   - **bloquant / majeur** → corrige dans le code.
   - **mineur / suggestion** → corrige si rapide et sûr ; sinon justifie brièvement de ne pas le faire.
   - **remède structurel proposé (règle 16)** → ne l'implémente **pas** dans l'US courante, même si la remarque est majeure. Vérifie les trois conditions (preuve dans le code, coût chiffré, option « rien » écartée à raison) ; si elles tiennent, inscris la dette au registre et propose l'ADR + l'US dédiée à l'utilisateur. Si elles ne tiennent pas, écarte la remarque en le justifiant — c'est de la sur-ingénierie.
   - **dette (technique ou de conception)** → soit tu la résorbes dans l'US, soit tu l'**assumes explicitement** en suivant la procédure de [`docs/dette.md`](docs/dette.md) : ligne au registre + détail, marqueur `# DETTE-nnn` à l'endroit du raccourci, mention dans le corps de la PR, et proposition d'une US de résorption à l'utilisateur. Jamais laissée silencieuse.
3. Après corrections, relance localement ce qui est pertinent (ruff/mypy/pytest côté back, eslint/typecheck côté front) selon les fichiers touchés.
4. Prépare le **message de commit** conventionnel des correctifs (`<type>(<scope>): …` + corps quoi/pourquoi + `US: ExxUSyyy`).
5. **Committe et pousse** les correctifs sans demander l'aval — c'est le workflow autonome (`CLAUDE.md` § Workflow) : tu ne rends pas la main pour ça. Seuls `git merge`, `git rebase` et l'ajout de dépendance (règle 11) restent soumis à arbitrage.

## Étape 3 — Boucle & sortie

- S'il restait des **bloquants** non résolus, relance une passe de revue (retour Étape 1) sur le nouveau diff.
- Sinon, fournis la **PR prête** : lien `pull/new/<branche>`, **titre** (`<type>(<ExxUSyyy>): <résumé>`, rappel de l'ID d'US) et **corps** (contexte, ce qui a été fait, remarques de revue traitées, `US: ExxUSyyy`, ADR éventuels). Rappelle que c'est l'utilisateur qui ouvre et merge, puis dit « c'est mergé ».
