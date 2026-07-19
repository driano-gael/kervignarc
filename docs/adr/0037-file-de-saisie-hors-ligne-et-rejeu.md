# ADR-0037 — File de saisie hors-ligne côté front : mise en file sur panne, rejeu à la reconnexion

- **Statut** : Accepté
- **Date** : 2026-07-20
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E04-saisie-scores.md`](../../stories/E04-saisie-scores.md) (E04US009, CA
  « file hors-ligne » ex-010 et « indicateur » ex-011). Corrige au passage la référence « ADR-0005 »
  du CA (l'idempotence relève d'[ADR-0036](0036-idempotence-de-la-saisie-par-identifiant-en-memoire.md),
  pas d'ADR-0005). N'amende pas la dette : la file est une **capacité**, pas un raccourci assumé.
- **Introduit par** : E04US009 (diffusion live & résilience réseau).
- **S'appuie sur** : [ADR-0036](0036-idempotence-de-la-saisie-par-identifiant-en-memoire.md)
  (le **zéro-doublon** au rejeu est garanti serveur, par l'identifiant de saisie),
  [ADR-0029](0029-mode-d-identite-poste-de-cible-et-jeton-de-poste.md) (le poste survit à la
  fermeture de l'onglet — même exigence de persistance `localStorage`).

## Contexte et problème

Le jour J, ~30 tablettes BYOD saisissent sur un LAN de gymnase **sans internet**. Le réseau local
peut hoqueter (borne wifi saturée, tablette qui s'éloigne). Le CA E04US009 « file hors-ligne » exige
que, **hors-ligne, les saisies soient mises en file côté front et rejouées à la reconnexion, sans
doublon** — *« ne rien perdre »* est l'invariant, et un score perdu silencieusement est pire qu'une
erreur visible.

Avant cette US, une saisie de volée était un `POST` direct : en cas de panne réseau, la mutation
tombait en **erreur** et le marqueur restait **bloqué** sur un écran d'erreur, la volée perdue s'il
ne recommençait pas. Trois questions à trancher : (1) comment **détecter** le hors-ligne ? (2) où
**ranger** les saisies en attente ? (3) comment **rejouer** sans créer de doublon ?

## Décision

**1. Détecter le hors-ligne par la nature de l'échec, pas par `navigator.onLine`.** Le client HTTP
(`fetchJson`) **rejette** avec une `TypeError` quand le `fetch` échoue au niveau réseau (serveur
injoignable), et lève une **`ErreurApi`** quand le serveur a **répondu** un refus (403 hors-cible,
404 blason introuvable…). On met en file **seulement** le premier cas ; une `ErreurApi` est une vraie
erreur, propagée à l'UI. `navigator.onLine` est écarté : sur un LAN sans internet il vaut souvent
`true` alors que le serveur est injoignable — il mentirait.

**2. Ranger la file dans un store Zustand persisté (`localStorage`).** Nouveau
`shared/stores/fileHorsLigneStore` (à côté de `sessionPosteStore`, même patron `persist`) : une liste
FIFO de corps de saisie. La persistance vaut jusqu'au bout — la file **survit à la fermeture de
l'onglet** (D-05 : pas de kiosque, l'onglet se ferme), comme le rattachement du poste. Une
ré-édition hors-ligne de la **même** volée remplace l'attente précédente (pas deux corps pour un
même emplacement). L'état vit dans `shared/` pour que l'indicateur (shared) **et** la feature saisie
en dépendent, jamais l'inverse.

**3. Faire avancer le marqueur par une série optimiste.** Quand une saisie part en file, la mutation
ne tombe pas en erreur : elle renvoie une **série optimiste** (la volée injectée localement, marquée
`en_attente`) qui rafraîchit le cache. Le marqueur **continue** (la grille avance), au lieu de rester
coincé — condition pour que la file soit utilisable, pas seulement un tampon invisible. Le **cumul
officiel ne bouge pas** : il ne compte que les volées **validées** par le scoreur, jamais une volée
en attente. Hors-ligne, on **n'invalide pas** la série (une relecture échouerait et ferait retomber
la grille en erreur) : la vérité serveur revient au rejeu. Une saisie **en ligne** réussie pour une
volée **supersède** une éventuelle attente hors-ligne du même emplacement (elle la retire de la file) ;
un rejeu déjà **en vol** — qui tient un instantané de la file — relit l'appartenance **vivante** avant
chaque envoi et **saute** ce qui a été retiré, pour qu'un vieux corps ne réécrase pas la valeur neuve.

**4. Rejouer à la reconnexion, le zéro-doublon délégué au serveur.** On renvoie la file **dans
l'ordre**, une par une. Le **zéro-doublon n'est pas géré côté front** : il est **serveur** (registre
d'idempotence par `identifiant_saisie`, ADR-0036 ; et pour une saisie de volée, l'écriture est de
toute façon un **upsert par `(série, numéro)`** — rejouer les mêmes valeurs est idempotent *de fait*,
même si le serveur a redémarré et vidé son registre). D'où la règle d'implémentation : **l'identifiant
est figé à la mise en file, jamais régénéré au rejeu**.

**Le rejeu se déclenche par transition, sur trois signaux** (jamais par la longueur de file, qui
rouvrirait une boucle chaude sur un serveur qui répond mal) : (a) le **lien WebSocket revient**
(`connecte`) — sur un LAN, la restauration du réseau coïncide avec la réouverture du WebSocket
(reconnexion auto ~1 s), signal plus fiable que `navigator.onLine` ; (b) le **jeton de poste revient**
(re-rattachement) — nécessaire parce qu'un rejeu peut buter sur un 401 (serveur redémarré → session de
poste volatile perdue, ADR-0029) *sans* que le WebSocket ne tombe : c'est alors le re-rattachement, pas
une transition de lien, qui relance ; (c) un **succès de saisie en ligne** — filet pour une saisie
enfilée sur un hoquet HTTP bref qui n'a pas fait tomber le WebSocket.

**Un refus au rejeu n'est pas l'autre — sinon on perd des scores en silence.** `fetchJson` lève une
`ErreurApi` pour **tout** statut non-2xx. Les confondre ferait retirer de la file (donc perdre) une
saisie sur une panne **transitoire**. On discrimine par le statut : seul un **refus définitif** (4xx
**métier** non rejouable — 400, 403 hors-cible, 404 blason introuvable, 422) est retiré ; un
**transitoire** — **401** (serveur redémarré / jeton perdu), 408, **409** (départ courant perdu au
redémarrage), 429, et **tout 5xx** (serveur saturé par la reconnexion de masse des ~30 tablettes) — est
**gardé en file** et rejoué plus tard, exactement comme une panne réseau. « Ne rien perdre » prime sur
« ne pas boucler ».

**5. Trois états d'indicateur.** L'indicateur (déjà permanent, E00US010) gagne l'état
**« synchronisation en cours »** pendant le rejeu, et affiche le **nombre de saisies en attente**.
La logique d'affichage est une fonction pure (`etatIndicateur`), testée.

**6. La diffusion live (CA ex-009) ne demande aucun code neuf.** Une validation de série passe par la
file d'écriture ; le listener post-commit (E00US008) publie déjà un `LiveEvent` diffusé à tous les
abonnés `/ws`, qui déclenche l'invalidation React Query côté abonnés (classement, série). Le CA
« après validation → diffusion < 1–2 s » est donc satisfait par l'infrastructure existante ; on s'y
appuie plutôt que d'ajouter un événement typé spéculatif (l'affinage par sujet/tournoi reste ouvert).

## Conséquences

- **Positif** : une coupure brève ne perd plus de saisie ni ne bloque le marqueur ; la file survit à
  la réouverture de l'onglet ; le dédoublonnage réutilise le mécanisme serveur (ADR-0036) sans
  logique fragile côté client ; toute la logique (file, rejeu, indicateur, série optimiste) est en
  **modules purs / stores** testés en node, sans dépendance de test nouvelle (pas de jsdom).
- **Limite assumée — refus définitif au rejeu.** Une saisie mise en file n'a **jamais** été validée
  par le serveur (on ne l'enfile que sur panne réseau, avant toute réponse). Si, au rejeu, le serveur
  la refuse **définitivement** (4xx métier : archer retiré de la cible, blason introuvable…), on la
  **retire** de la file et on la **journalise** (`console.error`). La perte est **visible** (la
  relecture de série retire la volée optimiste de la grille). Cas rare, non traité par un flux de
  reprise dédié — à rouvrir si le terrain le fait apparaître. *(Les refus **transitoires** — 401, 409,
  5xx… — ne passent pas par là : ils sont gardés en file, cf. Décision 4.)* Réserve honnête : sur une
  tablette BYOD, un `console.error` n'est vu de personne ; la seule visibilité réelle est la
  disparition de la volée à la relecture. Suffisant pour un cas aussi rare, à revoir si fréquent.
- **Limite — un item enfilé sans transition de lien ni saisie en ligne suivante attend.** Le cas
  résiduel après les trois déclencheurs (Décision 4) : une saisie enfilée sur un hoquet HTTP alors que
  le WebSocket **reste** ouvert, si aucune saisie en ligne ne suit et que le lien ne retombe jamais.
  Sur un LAN — un seul lien physique — un vrai défaut réseau fait tomber le WebSocket ; le cas est
  résiduel. Il reste **visible** (l'indicateur affiche « Hors ligne · N en attente » en permanence),
  jamais une perte. On préfère ça à une boucle de rejeu chaude déclenchée par la longueur de file.
- **Neutre — non couvert par test : le câblage React.** La logique *décidable* est extraite en
  modules purs testés (`rejouer`, `serieOptimiste`, `etatIndicateur`, les classificateurs d'erreur
  `horsLigne.ts`, le store) ; l'**orchestration** des hooks (déclenchement du rejeu, invalidation
  conditionnelle) reste non exercée — tester un `useEffect`/`useMutation` exigerait jsdom +
  testing-library, dépendances de dev absentes du projet (aucun test de composant nulle part). Choix
  cohérent avec l'existant ; à revoir si ces hooks s'étoffent.
- **Neutre** : le champ `en_attente` de `Volee` est **purement local** (le serveur ne l'émet jamais).
