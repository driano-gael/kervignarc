# ADR-0055 — Session de simulation vivante, pilotée par pas, sur le substrat in-memory

- **Statut** : Accepté
- **Date** : 2026-07-28
- **Décideurs** : Organisateur / Architecte
- **Portée** : E15US003 (bot pilote automatique pausable + cockpit interactif multi-vues + canal de
  diffusion isolé)
- **Lie** : [ADR-0054](0054-execution-ephemere-du-moteur-sur-adapters-in-memory.md) (le **substrat**
  éphémère in-memory que cet ADR anime), [ADR-0005](0005-async-et-sqlite.md) / règle 7 (writer unique
  + diffusion post-commit — la contrainte que la session ne doit **pas** violer et le canal réel dont
  le **canal isolé** se démarque), [ADR-0049](0049-saisie-et-scoring-des-duels.md) (reconstruction du
  tableau au fil des duels validés — ce que le bot pilote), règle 9 (déterminisme — pas d'horloge ni
  d'aléa non maîtrisé)

## Contexte et problème

E15US002 (ADR-0054) a livré un **rejeu one-shot** : `ServiceSimulation.simuler(tournoi_id)` hydrate
un harnais in-memory, fait tourner le moteur et renvoie un `ResultatSimulation` figé. Il n'écrit rien
(un tournoi *avant démarrage* a des séries vides → classement à 0, tableaux non jouables) : c'est un
**substrat**, pas encore un déroulé.

E15US003 demande trois capacités qui, ensemble, transforment ce substrat en outil de démo/QA :

1. **Bot pilote automatique pausable** — un bot **génère des scores plausibles** et fait avancer le
   déroulé (qualif → duels → classement), **pausable** puis repris.
2. **Cockpit interactif** — une navbar bascule entre les vues **cible / archer / scoreur / public** ;
   **en pause**, l'humain peut **saisir à la place d'un rôle**, puis **rendre la main** au bot.
3. **Diffusion isolée** — l'état simulé est poussé au front sur un **canal séparé** du temps réel réel.

Trois tensions à trancher :

- **(a) Où vit l'état du déroulé ?** Le one-shot est sans état. Or « mettre en pause, saisir à la
  main, reprendre » suppose un déroulé **qui persiste entre deux requêtes HTTP** : un état mutable
  côté serveur. C'est une rupture avec le one-shot.
- **(b) Qui cadence le bot ?** Un « pilote automatique » évoque une boucle de fond qui avance seule.
  Mais une boucle serveur temporisée introduit une **horloge** et de la **concurrence** non
  déterministes — heurte la règle 9 (tests reproductibles) et complique la pause.
- **(c) Comment diffuser sans violer la règle 7 ?** La diffusion réelle est **exclusivement** couplée
  au listener post-commit de la `write_queue`. Une simulation ne soumet jamais à la file (ADR-0054
  §6) : réutiliser ce chemin est impossible **et** indésirable (il mêlerait simulé et réel).

## Décision

**1. Une `SessionSimulation` mutable, éphémère, en mémoire serveur — hors file d'écriture.** On
introduit un objet de **session** qui **détient** un `HarnaisSimulation` hydraté (le substrat
ADR-0054) plus l'état du pilote (en cours / en pause / terminé), l'étape courante (qualif / duels /
terminé), la graine et son générateur pseudo-aléatoire, et le niveau tiré de chaque archer. Un
**registre** en mémoire (`dict[SessionId, SessionSimulation]`, câblé à la composition root, règle 8)
garde les sessions vivantes. Rien n'atteint SQLite ni la `write_queue` : comme le substrat, la
non-persistance est **structurelle** (règle 7 intacte — aucune transaction longue, aucun writer
monopolisé). Une session est **jetable** : `arreter` la retire, le harnais et ses `dict` sont
collectés.

*Pourquoi un état serveur plutôt que « tout recalculer à chaque appel » ?* Parce que la reprise en
main **mute** le déroulé (une volée saisie à la main doit rester saisie au tour d'après) : sans état
conservé, il faudrait rejouer tout l'historique des saisies manuelles à chaque requête — c'est un
état, autant l'assumer. Le garde-fou de non-pollution ne repose pas sur l'absence d'état mais sur
l'**absence de chemin** vers la base (ADR-0054 §1).

**2. Le pilote est cadencé par des *pas* déclenchés depuis le front, pas par une boucle serveur.**
« Avancer » est une opération **synchrone et discrète** : `avancer(session, n)` fait progresser le
déroulé de `n` **unités** (voir point 3). Le « pilote automatique » est un **ticker côté front** qui
appelle `avancer` sur un intervalle ; **mettre en pause** = le front cesse d'appeler. Le serveur
reste **réactif et déterministe** : aucun thread de fond, aucune horloge, aucun aléa non maîtrisé
(règle 9) — un même `(graine, suite d'actions)` produit toujours le même déroulé, donc des **tests
reproductibles** depuis le CA. La vitesse de défilement est un pur **réglage d'UI**.

*Conséquence d'états.* Le pilote a trois états et des transitions gardées (409 si illégal, comme le
cycle de vie du tournoi, ADR-0026) :

| État | `avancer` (bot) | `saisir` (humain) | transitions |
|---|---|---|---|
| `en_cours` | autorisé | **refusé** (409) | → `en_pause` (mettre en pause) |
| `en_pause` | refusé (409) | **autorisé** | → `en_cours` (reprendre) |
| `termine` | refusé (409) | refusé (409) | terminal |

Le bot n'avance que quand il est aux commandes (`en_cours`) ; l'humain ne saisit que quand le bot est
suspendu (`en_pause`) — traduction directe du CA « en pause, l'humain peut saisir… puis rendre la
main ». `termine` est atteint quand il n'y a plus d'unité à jouer.

**3. Une *unité* de déroulé, commune au bot et à l'humain.** L'avancée se fait par unités atomiques,
identiques que ce soit le bot (`avancer`) ou l'humain (`saisir`) qui les joue — la **prochaine
unité** est un curseur unique, exposé au cockpit pour peupler le formulaire de reprise en main :

- **En qualification** — une unité = **la prochaine volée manquante** d'un archer, dans l'ordre
  *volée-major* (tout le monde tire la volée 1, puis la volée 2…), déterministe par tri des archers.
  Le bot en **génère les valeurs** (générateur plausible, point 4) ; l'humain les **fournit** (il
  joue la cible). La volée est posée **validée** (verrouillée) — le classement ne compte que le
  validé (`Serie.cumul`). La simulation **court-circuite délibérément** le workflow de validation par
  grain d'E04US002 (`ServiceSaisie` n'est d'ailleurs pas dans le harnais) : produire une donnée
  plausible n'est pas rejouer la cérémonie de saisie ; le déroulé, lui, est fidèle (mêmes agrégats,
  même classement).
- **En duels** — une unité = **le prochain duel jouable non tranché** (phases d'élimination directe
  dans l'ordre, puis tours, puis n° de match). La jouer, c'est **désigner un vainqueur** et produire
  les tirs correspondants via `ServiceSaisieDuels` (`saisir_manche` × N, puis `valider`), après quoi
  le tableau **avance de lui-même** à la reconstruction suivante (ADR-0049). Le bot choisit le
  vainqueur **plausiblement** (biais au niveau/à l'ensemencement) ; l'humain le **désigne** (il joue
  le scoreur). Les scores sont fabriqués pour être **décisifs** (le gagnant tire au maximum, le
  perdant une volée strictement inférieure) : pas de barrage à gérer, déroulé toujours tranché.

**4. La génération de scores est une stratégie injectable (règle 1/2), déterministe par graine.** Un
`GenerateurScores` (port applicatif) transforme *(zones du blason, nombre de flèches, niveau de
l'archer, générateur pseudo-aléatoire)* en une volée plausible ; l'implémentation par défaut
(`GenerateurScoresPlausibles`) tire chaque flèche parmi les **zones légales du blason** avec un poids
croissant vers le centre, modulé par le **niveau** de l'archer (tiré une fois par la graine) pour que
les totaux **s'étalent** et que le classement ait du sens. Elle vit au **niveau applicatif** (comme
`ServiceJeuEssai` d'E15US001) : « un score plausible » est de l'**outillage de démo**, pas une règle
FFTA — ce n'est pas une des six politiques du moteur (routing/scoring/seeding/byes/tiebreak/depth),
mais une stratégie **injectée à la composition root**, donc substituable sans toucher au domaine. Le
déterminisme (règle 9) vient d'un `random.Random(graine)` **injecté**, jamais du module `random`
global.

**5. Un canal de diffusion isolé : un `Broadcaster` dédié et un endpoint WebSocket séparé.** La
simulation pousse son état sur `/ws/simulation`, servi par un **second** `Broadcaster`
(`broadcaster_simulation`), **distinct** de celui du temps réel réel. Aucune écriture simulée ne
transite par la `write_queue`, donc le canal réel reste muet (ADR-0054 §6) ; réciproquement, le canal
simulé ne porte **que** des `LiveEvent` de simulation. L'isolement est **structurel** (deux hubs
séparés), pas un filtrage sur un canal partagé — le réel et le simulé ne peuvent pas fuir l'un vers
l'autre. Le service de pilotage **publie** sur ce canal après chaque mutation (avancer / saisir /
pause / reprendre) ; il reçoit le hub par un **port étroit** (`DiffusionSimulation`) pour rester sans
infrastructure (règle 8) et testable sans WebSocket.

## Conséquences

**Positives.**

- La reprise en main est un cas **naturel** : bot et humain jouent la **même** unité via le **même**
  curseur ; « saisir à la place d'un rôle » n'est pas un chemin parallèle, juste l'autre acteur.
- **Déterminisme** total (règle 9) : pas de boucle de fond, pas d'horloge — le CA se teste depuis un
  service synchrone, sans WebSocket ni timing. L'oracle 120 reste l'oracle (même moteur, ADR-0054).
- Règle 7 **intacte** : la session vit hors de la file ; aucune transaction longue.
- Isolation de diffusion **par construction** (deux hubs), pas une discipline à tenir.

**Négatives / limites.**

- **Fuite mémoire potentielle** : une session non arrêtée reste en mémoire. Acceptable pour un outil
  **mono-club, local, admin** (règle 12) : peu de sessions, courtes, un redémarrage les efface. Pas
  d'expiration automatique livrée (over-engineering pour la cible) — inscrit comme **limite connue**,
  pas comme dette (rien n'est cassé pour un utilisateur réel).
- **Le curseur « volée-major » est un choix d'ergonomie**, pas une règle FFTA : il rend le déroulé
  **lisible** (tout le monde progresse ensemble) mais n'est qu'une des mises en ordre possibles.
- **La reprise en main est au grain de l'unité** (une volée, un vainqueur de duel), pas une
  ré-écriture libre de l'état : suffisant pour « démontrer qu'on peut prendre le relais », sans
  rouvrir la complexité d'un éditeur d'état complet.

**Écartées.**

- **Boucle serveur temporisée** (le bot avance seul en tâche de fond) : introduit horloge + threads
  non déterministes (heurte la règle 9), complique la pause (annuler une tâche) et le test. Le ticker
  front donne le **même** effet visuel sans rien de cela.
- **Recalcul intégral à chaque requête** (rejouer tout l'historique de saisies) : possible tant que
  le bot est seul, impraticable dès que l'humain injecte des unités — l'état conservé est plus simple
  *et* plus rapide.
- **Filtrer un canal WebSocket unique par sujet** (réel + simulé sur `/ws`) : moins isolant qu'un hub
  séparé (un bug de filtre ferait fuiter le simulé dans le réel), et le socle mono-canal n'a pas
  encore de sujets. Deux hubs sont plus simples et plus sûrs (règle 12).
