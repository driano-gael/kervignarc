# ADR-0044 — Sauvegarde/archive : lecture concurrente hors file d'écriture + première tâche périodique

- **Statut** : Accepté
- **Date** : 2026-07-26
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E11-exploitation.md`](../../stories/E11-exploitation.md) (E11US003 — CA
  « sauvegarde périodique » et « export/archive »).
- **Introduit par** : E11US003 (sauvegarde & archive).
- **Réfs** : [ADR-0005](0005-async-et-sqlite.md) (writer unique, file d'écriture,
  WAL), `CLAUDE.md` règle 7 (SQLite single-writer) et règle 12 (simplicité hors domaine).

## Contexte et problème

E11US003 introduit deux mécanismes que le projet n'avait jamais eus, et qui **touchent à une règle
non négociable** (règle 7) et à la **structure du cycle de vie** — d'où cet ADR, consultable hors du
contexte de l'US (une puce de `stories/` ne suffit pas à documenter l'interprétation d'une règle
non négociable ni un précédent d'architecture).

**1. Copier une base SQLite vive.** La règle 7 (ADR-0005) impose : *écritures via la file consommée
par le writer unique ; lectures synchrones hors boucle événementielle*. La sauvegarde périodique et
le snapshot d'archive doivent **copier la base pendant qu'elle est en service** (jusqu'à ~30 tablettes
écrivent). Une `shutil.copy` est fausse (elle ignore les pages encore dans le journal `-wal` et peut
être tronquée en pleine écriture). Comment copier sans casser l'invariant du writer unique ?

**2. Déclencher une sauvegarde toutes les N minutes.** C'est le **premier planificateur périodique**
du projet. `WriteQueue` tourne déjà dans le `lifespan`, mais c'est un worker événementiel
démarré/drainé, pas une tâche cadencée par le temps.

## Décision

**Une copie de base est une LECTURE ; elle ne passe donc pas par la file d'écriture.** On utilise
l'API de sauvegarde en ligne de SQLite (`sqlite3.Connection.backup()`), qui copie **page à page** au
niveau moteur, inclut l'état WAL, et **redémarre** proprement si la source change pendant la copie.
Conformément à la règle 7 (« lectures synchrones hors boucle »), cette opération :

- ouvre une **connexion `sqlite3` brute directe au fichier**, en parallèle du writer et **hors du
  moteur SQLAlchemy** (helper unique `infrastructure/db/snapshot.py`) ;
- s'exécute **hors boucle événementielle**, dans un `run_in_threadpool` (même patron que les
  endpoints PDF) ;
- pose un `PRAGMA busy_timeout` sur la connexion source pour patienter plutôt qu'échouer sur une
  contention rare (checkpoint), la cohérence WAL étant garantie par l'API de backup.

**La sauvegarde périodique est une tâche de fond du `lifespan`.** Une coroutine `while True: sleep ;
backup` est lancée par `asyncio.create_task` au démarrage et **annulée proprement** à l'arrêt
(`cancel()` + `await` sous `suppress(CancelledError)`). La première copie a lieu **après** un
intervalle (jamais au démarrage) — un test qui monte l'app n'en produit aucune. Best-effort : un
échec est journalisé, la boucle continue. Paramétrage par variables d'environnement
`KERVIGNARC_BACKUP_*` (intervalle, rétention, dossier), lues **une fois** à `create_app`.

**L'archive lit tout depuis un instantané unique.** `ConstructeurArchiveZip` prend **un** snapshot
cohérent, puis en dérive le fichier `.db`, les CSV et les comptes/version du manifeste — jamais de la
base vive à des instants différents. Les parties issues de la base décrivent ainsi le même état.

## Conséquences

- **Précédent (assumé)** : toute future opération de **maintenance en lecture** (restauration —
  E11US006, vérification d'intégrité) peut ouvrir une connexion `sqlite3` directe hors file, hors
  engine, à condition de rester une **lecture** et de tourner hors boucle. Une **écriture** de
  maintenance, elle, resterait soumise à la règle 7 (via la file).
- **Cadre du scheduler** : le `lifespan` accueille désormais des tâches périodiques. Rester parcimonieux
  (règle 12) — pas de framework d'ordonnancement ; une coroutine `sleep`/`cancel` suffit à l'échelle
  mono-club. La restauration/arrêt propre (E11US006) s'y branchera de même.
- **Config au démarrage** : changer un `KERVIGNARC_BACKUP_*` exige un **redémarrage** (lu une fois).
  Acceptable pour un déploiement jour J.
- **Limite** : l'atomicité vaut pour les parties **issues de la base** ; les PDF de l'archive,
  régénérés par le service en amont, reflètent leur propre instant de lecture — non figé avec le
  snapshot. Sans conséquence (archive de fin d'événement, base au calme).
