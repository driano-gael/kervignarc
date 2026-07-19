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
la grille en erreur) : la vérité serveur revient au rejeu.

**4. Rejouer à la reconnexion, le zéro-doublon délégué au serveur.** Un hook monté sur l'écran de
saisie déclenche le rejeu quand le **lien WebSocket revient** (`connecte`) : sur un LAN, la
restauration du réseau coïncide avec la réouverture du WebSocket (reconnexion auto ~1 s), signal plus
fiable que `navigator.onLine`. On renvoie la file **dans l'ordre**, une par une. Le **zéro-doublon
n'est pas géré côté front** : il est **serveur** (registre d'idempotence par `identifiant_saisie`,
ADR-0036). D'où la règle d'implémentation : **l'identifiant est figé à la mise en file, jamais
régénéré au rejeu** — rejouer une saisie déjà passée juste avant la coupure renvoie le même résultat,
sans deuxième volée.

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
- **Limite assumée — refus serveur au rejeu.** Une saisie mise en file n'a **jamais** été validée par
  le serveur (on ne l'enfile que sur panne réseau, avant toute réponse). Si, au rejeu, le serveur la
  **refuse** définitivement (`ErreurApi` : configuration changée, archer retiré de la cible…), on la
  **retire** de la file (sinon elle bloquerait le rejeu indéfiniment) et on la **journalise**
  (`console.error`). La perte est **visible** : la relecture de série qui suit retire la volée
  optimiste de la grille. Cas rare, non traité par un flux de reprise dédié — à rouvrir si le terrain
  le fait apparaître, pas avant (pas de spéculation).
- **Limite — déclencheur du rejeu = reconnexion WebSocket.** Une saisie qui échouerait alors que le
  WebSocket **reste** ouvert (panne HTTP sans coupure du lien) attend la prochaine transition de lien
  pour être rejouée. Sur un LAN — un seul lien physique — les deux tombent ensemble ; le cas est
  négligeable. On évite ainsi une boucle de rejeu chaude sur un serveur qui répondrait mal.
- **Neutre** : le champ `en_attente` de `Volee` est **purement local** (le serveur ne l'émet jamais).
