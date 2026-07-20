# ADR-0038 — Présence des postes par heartbeat (état en ligne / hors ligne)

- **Statut** : Accepté
- **Date** : 2026-07-20
- **Décideurs** : Organisateur / Architecte
- **Introduit par** : E12US001 (superviser les postes de saisie).
- **Amende** : [`stories/E12-pilotage-jour-j.md`](../../stories/E12-pilotage-jour-j.md) (E12US001, CA
  et Notes). N'amende pas la dette : la volatilité de la présence est un **choix** cohérent avec le
  modèle de session, pas un raccourci assumé.
- **S'appuie sur** : [ADR-0029](0029-mode-d-identite-poste-de-cible-et-jeton-de-poste.md) (jeton de
  poste en mémoire) et [ADR-0034](0034-poste-selectionne-son-depart-courant.md) (départ courant en
  mémoire) — la présence prolonge le **même parti** : état de session volatil, en mémoire.

## Contexte et problème

E12US001 veut une console de supervision qui distingue **« ils tirent lentement »** de **« leur
tablette est morte »**. Or **rien** côté serveur ne suit l'état de connexion d'un poste : le
`Broadcaster` WebSocket (E00US008) est un ensemble de files **anonymes** — aucune identité, aucun
horodatage. Savoir qu'un poste est **en ligne** ou **hors ligne** est donc à créer.

Deux besoins distincts se cachent derrière « superviser un poste », et les confondre casse le CA :

1. **Liveness** — la tablette est-elle *joignable* ? C'est ce qui sépare *morte* de *vivante*.
2. **Activité de travail** — quand a-t-on *saisi* pour la dernière fois sur cette cible ? C'est ce
   qui sépare *lente* (vivante mais qui n'avance pas) de *rapide*.

## Décision

### 1. Liveness par **heartbeat**, pas par la connexion WebSocket

Le poste envoie périodiquement (**~10 s**) un `POST /api/v1/postes/session/heartbeat`
authentifié par son jeton (`X-Jeton-Poste`). Le serveur mémorise, par `poste_id`, l'**instant** de
la dernière réception et l'**IP** vue. Un `RegistrePresence` (port du domaine, adapter en mémoire)
porte cet état.

**Règle d'état** (fonction **pure** du domaine, `domain/supervision.py`) : à partir de
`(rattaché ?, secondes depuis le dernier heartbeat, seuil)` →

- **non rattaché** : aucune session ouverte pour ce poste (code préparé mais aucune tablette
  dessus) ;
- **hors ligne** : rattaché mais dernier heartbeat **plus vieux que le seuil** (**30 s** = 3 pings
  manqués) — ou jamais vu ;
- **en ligne** : rattaché et vu il y a **≤ seuil**.

Le « maintenant » vient du port `Horloge` (jamais lu dans le domaine — règle 9, déterminisme) ; le
seuil est **injecté** (défaut 30 s), pas codé en dur dans le domaine. La borne est **inclusive**
côté « en ligne » (`secondes ≤ seuil`).

**Pourquoi le heartbeat plutôt que la présence WebSocket ?** Lier chaque connexion WS à un
`poste_id` obligerait à **introduire l'identité dans le `Broadcaster`**, aujourd'hui volontairement
anonyme (walking skeleton, un seul canal). C'est une mutation d'infra plus lourde, et surtout
**moins testable** : la présence WS se prouve en simulant des sockets, là où le heartbeat se prouve
en injectant une **horloge figée** et un registre. Le heartbeat **découple** la supervision du
transport temps réel — le `Broadcaster` reste ce qu'il est.

### 2. « Dernière activité » = dernière **saisie**, pas dernier heartbeat

La colonne *dernière activité* (« il y a 14 mn ») affiche l'horodatage de la **dernière volée
saisie** sur la cible (max des `created_at` des volées de ses archers), **pas** le dernier
heartbeat. Raison décisive : un poste en ligne pingue toutes les 10 s ; si *dernière activité*
suivait le heartbeat, elle afficherait **toujours** « il y a quelques secondes » et la **lenteur
deviendrait invisible** — exactement ce que le CA veut voir. Le heartbeat sert la **liveness** (la
pastille en ligne/hors ligne), la saisie sert l'**activité** (depuis combien de temps ça n'a pas
avancé). Ce sont deux horloges pour deux questions.

### 3. Registre de présence **en mémoire, volatil, sans persistance**

Un dictionnaire `poste_id → (instant, ip)` sous verrou (accès depuis les threads du threadpool),
**effacé au redémarrage** serveur — comme le jeton (ADR-0029) et le départ courant (ADR-0034). Au
redémarrage, session et présence disparaissent ensemble : les postes repassent *non rattachés* puis
se re-signalent au premier heartbeat. Aucune table, aucune migration (règle 12, simplicité hors
domaine ; mono-club, réseau local).

### 4. La console est **lue à la demande** (poll court), pas poussée par le heartbeat

Le passage **hors ligne** ne naît d'**aucun événement** : il naît du **temps qui passe** sans
heartbeat. Aucune diffusion WebSocket ne peut donc le signaler. La console rafraîchit par un
**poll court** (React Query `refetchInterval` ~5 s), qui capte à la fois les retours en ligne, les
passages hors ligne (par expiration du seuil) et l'avancement. Les heartbeats ne passent **pas** par
la file d'écriture (`WriteQueue`) : ce sont des lectures/écritures mémoire, sans transaction ni
diffusion — un ping toutes les 10 s × 30 postes ne doit rien coûter en base. La diffusion WebSocket
globale existante (`donnees_modifiees`) continue de rafraîchir la console sur les **saisies**, en
complément du poll.

### 5. Révoquer / réinitialiser un poste = fermer sa session + oublier sa présence

L'admin peut **révoquer** un poste (`D-07`) : on invalide **toutes** ses sessions
(`invalider_poste(poste_id)`, sur le modèle de `invalider_scoreur`) et on **oublie** sa présence. Le
poste repasse *non rattaché* ; sa tablette, à la prochaine résolution de session, retombe sur
l'écran de rattachement.

## Alternatives écartées

- **Présence via la connexion WebSocket** (identité injectée dans le `Broadcaster`). Réutilise le
  socket déjà ouvert (zéro trafic en plus) mais alourdit une infra volontairement anonyme et se
  teste mal (simulation de sockets vs horloge figée). Écartée pour E12US001 ; réévaluable si le
  trafic heartbeat devenait un problème (il ne le sera pas à 30 postes).
- **Dériver l'état des seules écritures** (« vu » = dernière saisie). Zéro infra, mais un poste
  **connecté qui tire lentement écrit rarement** → paraîtrait *mort*. Casse le but même de l'US.
  C'est précisément pourquoi liveness (heartbeat) et activité (saisie) sont **séparées** (§1–2).
- **Registre de présence persisté en base.** Survivrait au redémarrage, mais ajoute une écriture par
  ping (à rebours de la brièveté des transactions, règle 7) pour un gain nul : la présence se
  reconstitue en une fenêtre de heartbeat. Sur-ingénierie hors domaine.

## Conséquences

- **+** L'admin voit enfin la différence entre *lent* et *mort*, sans que la supervision touche à
  l'infra temps réel : le `Broadcaster` reste anonyme, le heartbeat est un chemin à part.
- **+** Entièrement déterministe en test (horloge injectée + registre en mémoire) — aucune horloge
  murale dans les assertions.
- **−** L'état de présence ne survit pas à un redémarrage serveur (fenêtre de re-signalement d'un
  heartbeat). Accepté et **signalé**, cohérent avec les sessions volatiles existantes.
- **−** Un poll court (~5 s) sur la console maintient un léger trafic tant que l'écran est ouvert.
  Négligeable (une lecture mémoire, un écran admin à la fois), et c'est le **seul** moyen de rendre
  le passage hors ligne — un non-événement — visible sans action de l'admin.
- **⚠ Piège à surveiller** : le seuil (30 s) doit rester **strictement supérieur** à l'intervalle de
  heartbeat (10 s), avec une marge pour absorber un ping manqué. Un seuil trop proche de
  l'intervalle ferait **clignoter** les postes (faux hors-ligne à chaque ping en retard). Les deux
  valeurs sont liées : les changer, c'est les changer **ensemble** (heartbeat front + seuil serveur).
