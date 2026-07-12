# ADR-0010 — Unité de travail : la commande d'écriture est la frontière transactionnelle

- **Statut** : Accepté
- **Date** : 2026-07-12
- **Décideurs** : Organisateur / Architecte
- **Précise** : ADR-0005 (accès SQLite : lectures synchrones + file d'écriture single-writer)

## Contexte et problème

Aujourd'hui chaque méthode repository ouvre une **session courte** et fait son propre
`commit()` (ADR-0005, « une session par opération »). Pour les cas d'usage actuels, tous
**mono-écriture** (`creer` tournoi, `ajouter`/`placer` archer, `saisir_score`), c'est
correct : une méthode = une transaction = un `INSERT`/`UPDATE` atomique, avec rollback
implicite du `with … as session` en cas d'exception.

Deux garanties sont déjà acquises et doivent être **préservées** :

- **Sérialisation des écritures** : le router enveloppe *tout* le use case dans
  `write_queue.submit(...)`. Vérification (`par_id`) **et** écriture s'exécutent sur
  l'**unique thread writer** ; aucune écriture concurrente ne s'intercale (le
  *check-then-write* est sûr sans verrou applicatif).
- **Point de passage unique** post-commit : diffusion WebSocket (et, à venir, audit)
  branchés en un seul endroit via les listeners de la file.

Ce qui **manque** apparaîtra avec le MVP+1, dont plusieurs cas d'usage sont
**multi-écritures** et doivent réussir ou échouer **d'un bloc** :

- **placement** d'une série d'archers en une opération → N `UPDATE` ;
- **duels/matchs** : clore un match = MAJ statut **+** création du résultat ;
- **saisie d'une volée** (plusieurs flèches) validée d'un bloc → N `INSERT` scores.

Avec le modèle actuel, si une telle commande faisait `write1` (committé) puis `write2`
(échec), `write1` **resterait persisté** → état incohérent. La file **sérialise** les
écritures mais ne fournit **pas** d'atomicité *transverse* à plusieurs opérations repo :
chaque méthode commit la sienne.

## Options envisagées

- **Statu quo (une session + un commit par méthode repo)** : simple, mais rend
  l'atomicité multi-écritures **impossible** à composer — un échec en cours de use case
  laisse des écritures partielles committées.
- **Session optionnelle passée à chaque méthode** (`…, session=None`) : rétrocompatible,
  mais fait fuiter la notion de transaction dans **toutes** les signatures de ports et
  repose sur une discipline fragile (« ne pas oublier de committer côté appelant »).
- **Unité de travail dont la frontière est la commande d'écriture** *(retenue)* : le
  writer ouvre **une session par commande**, l'expose aux repos le temps de la commande,
  et **commit une seule fois** à la fin (rollback sur exception). La commande — déjà le
  point de sérialisation et de post-commit — devient aussi le point de **commit unique**.

## Décision

- **Une commande d'écriture = une session = une transaction = une diffusion post-commit.**
  Le writer (`WriteQueue`) ouvre la session au début de la commande, exécute le callable,
  puis **commit** ; toute exception provoque un **rollback** *complet* et se propage à la
  `Future` de l'appelant (aucune écriture partielle). Les listeners post-commit ne sont
  notifiés **qu'après** le commit réussi.
- **En écriture, les repositories utilisent la session fournie par l'unité de travail**
  (session ambiante de la commande) et **n'appellent plus `commit()` eux-mêmes**. Le
  commit est la responsabilité **exclusive** de la frontière (le writer).
- **Les lectures restent inchangées** : hors file, elles ouvrent leur **session courte**
  autonome (mode WAL, non bloquées par l'écriture en cours). Aucune régression sur l'axe
  lecture.
- **Le domaine et les use cases restent purs et synchrones.** L'unité de travail vit dans
  l'**infrastructure**, derrière les ports ; un use case multi-écriture enchaîne
  simplement ses appels repository — l'atomicité lui est fournie par la frontière, sans
  qu'il connaisse ni session ni transaction.
- **Portée** : cette révision **précise** l'ADR-0005 sur le seul point « une session par
  *opération* » → « une session par *commande* (une ou plusieurs opérations) ». Tout le
  reste de l'ADR-0005 (single-writer, queue, WAL, executor pour les lectures) demeure.
- **Mise en œuvre différée** : aucun code n'est modifié maintenant (les use cases actuels
  sont mono-écriture, donc déjà atomiques). La **première US multi-écriture** (placement
  en série, duel, ou volée) implémente l'unité de travail selon cet ADR et migre les repos
  vers la session fournie.

## Conséquences

- **+** Atomicité multi-écritures **par construction**, sans casser la sérialisation
  single-writer ni déplacer le point de post-commit/diffusion.
- **+** Use cases plus simples : ils composent des écritures sans se soucier du commit ;
  la transaction est un **détail d'infrastructure**.
- **+** Un seul endroit committe → un seul endroit à instrumenter (audit, broadcast),
  cohérent avec l'esprit « point de passage unique » de l'ADR-0005.
- **−** Les repositories doivent distinguer **contexte d'écriture** (session fournie, pas
  de commit) et **contexte de lecture** (session courte autonome) — un peu plus de
  mécanique dans les adapters (unité de travail injectée ou session ambiante par
  `contextvar`).
- **−** Discipline à tenir : **aucun `commit()` dans un repository** en contexte
  d'écriture ; le commit unique appartient à la frontière. À couvrir par un test
  d'atomicité (échec de la 2ᵉ écriture ⇒ rollback de la 1ʳᵉ).
- **⚠** Ne pas ré-ouvrir de session « courte » **à l'intérieur** d'une commande : une
  telle session committée échapperait au rollback de la frontière. En contexte d'écriture,
  tout passe par la session de l'unité de travail.

## Liens

ADR-0005 (file d'écriture single-writer, sessions courtes), ADR-0003 (hexagonale,
ports/adapters), ADR-0007 (erreurs par couche) ; `guide-architecture.md` §7.
