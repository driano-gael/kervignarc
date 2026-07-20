# ADR-0032 — Navigation de l'appli admin par état local plutôt que react-router

- **Statut** : Accepté
- **Date** : 2026-07-19
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E00-socle.md`](../../stories/E00-socle.md) (E00US015 — Notes, arbitrage du
  18/07/2026 déjà consigné).
- **Introduit par** : E00US015 (ossature de navigation de l'appli admin — coquille).
- **Réfs** : [`cahier-des-charges-ux.md`](../../cahier-des-charges-ux.md) §7.1 (`D-19`, `D-20`) ;
  `CLAUDE.md` règle 11 (parcimonie des dépendances) ; [ADR-0009](0009-gouvernance-dependances.md)
  (gouvernance des dépendances).

## Contexte et problème

E00US015 remplace l'écran admin monolithique (`competition/TrancheVerticale.tsx`, ~14 sections
empilées) par une **coquille** : une sidebar groupée par temps du tournoi, une seule destination
affichée à la fois, un accueil contextualisé par le statut (CDC UX §7.1, `D-19`/`D-20`). Passer
d'un écran unique à **~16 destinations** pose la question du **mécanisme de navigation** : faut-il
introduire **`react-router`** (routes, URL par destination, historique navigateur) ou tenir la
navigation en **état local React** (`useState`) ?

`react-router` apporterait des URL adressables (deep-link, lien partageable, bouton Précédent,
état de navigation survivant au rechargement). Mais c'est une **dépendance runtime** de plus, et la
règle 11 impose la parcimonie (« en cas de doute, on n'ajoute pas ; stdlib ou quelques lignes maison
préférées »). Le contexte de déploiement pèse dans la balance : outil **interne mono-club**, sur
**réseau local sans internet**, sur des tablettes BYOD utilisées séance tenante. Personne ne
**partage** l'URL d'un écran d'administration ni ne **met en favori** la destination « Blasons » : la
valeur des URL adressables — réelle sur une appli web publique — est ici quasi nulle.

## Décision

**La navigation de la coquille admin se fait par état local `useState`, sans `react-router`.** La
destination active, le tournoi courant et le groupe déplié sont des `useState` dans le composant
`CoquilleAdmin` ; changer de destination met à jour cet état, la zone principale rend la feature
correspondante. Aucune dépendance de routage n'est ajoutée (le manifeste `package.json` est
**inchangé** par l'US).

Ce choix vaut pour l'**appli admin**. Il ne préjuge pas de l'app **poste de cible** (déjà pilotée
par le marqueur `?poste=<code>` en query-string, E04US001) ni d'une éventuelle **vitrine publique**,
qui répondent à d'autres besoins.

**Mise à jour E07US001 (2026-07-20).** La vitrine publique (vues classement + plan de cibles) a été
livrée et a **adopté le même mécanisme** — navigation par `useState` (choix du tournoi, onglets),
`package.json` toujours inchangé. Une nuance vaut d'être notée : côté **public**, l'URL adressable a
une valeur **réelle** que l'admin n'a pas — un spectateur voudrait partager « le classement du
tournoi X » ou « le plan du départ Y », et E07US006 (« ouvrir l'appli sur ma journée ») pourrait
réclamer un deep-link mémorisable. Le déclencheur de réouverture de cet ADR (« à rouvrir si un vrai
besoin d'URL apparaît », cf. Conséquences) est donc **plus susceptible de se produire sur la vitrine
publique que sur l'admin**. Les CA d'E07US001 (classements/plans/live) ne l'exigeant pas, le choix
sans routeur tient pour l'instant, zone publique comprise.

## Conséquences

- **+** Aucune dépendance ajoutée : la coquille tient en quelques `useState` et un tableau de
  destinations (règle 11, [ADR-0009](0009-gouvernance-dependances.md)). Moins de surface, moins de
  runtime à embarquer dans le futur binaire hors ligne.
- **+** Le modèle reste **simple et local** : la rigueur du projet va au moteur métier, pas à
  l'outillage front (règle 12).
- **−** **Pas d'URL adressable** : aucune destination n'a de deep-link ni de lien partageable, et le
  **rechargement (F5) perd l'état de navigation** — l'app repart sur l'accueil (`tournoi` /
  contextualisé). Acceptable pour un outil interne piloté en continu ; à **rouvrir si un vrai besoin
  d'URL apparaît** (ex. envoyer à un bénévole un lien direct vers un écran, ou survivre à un reload
  fréquent). Ce serait alors une nouvelle US + révision de cet ADR.
- **−** La navigation est un **précédent** pour toute destination future de l'admin (E00US016 et
  au-delà) : elles se branchent dans le même tableau `useState`, sans routeur. Introduire
  `react-router` plus tard resterait possible mais toucherait toutes les destinations d'un coup.
