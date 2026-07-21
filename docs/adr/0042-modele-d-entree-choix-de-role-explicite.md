# ADR-0042 — Modèle d'entrée de l'appli : choix de rôle explicite au 1ᵉʳ lancement

- **Statut** : Accepté
- **Date** : 2026-07-21
- **US** : E00US017 — Écran d'accueil : choisir son appareil / rôle
- **Portée** : front (`frontend/src/app`, stores de session partagés) — aucun changement backend

## Contexte

Une **seule SPA** sert trois (désormais quatre) publics : la **tablette de cible** qui saisit, le
**téléphone public** qui consulte, le **scoreur itinérant** qui valide, l'**admin sur PC** qui
organise. Jusqu'ici l'aiguillage vers l'un de ces mondes était **implicite**, déduit d'un faisceau
d'indices dans `App.tsx` puis `CoquilleAdmin` :

- un **jeton de poste** (`sessionPosteStore.estPoste`, posé au rattachement ou à l'arrivée par le QR
  de la cible `?poste=<code>`) ouvrait l'écran de poste ;
- sinon la **coquille**, qui montrait l'**admin** si une session admin existait, la **consultation
  publique** sinon ;
- la consultation publique portait, enfouis, l'**entrée scoreur** (code) *et* le **login admin**
  (via `GestionTournois`), plus un lien de secours « cette tablette est un poste de cible ».

Les quatre portes existaient donc, mais **déduites d'un état de session**, pas **déclarées**. Au
lancement sur un PC neuf, l'app tombait sur la consultation publique — le mauvais écran pour
l'organisateur. Et un public (« je ne suis qu'un spectateur ») voyait malgré tout le login admin et
l'entrée scoreur : une **escalade** possible, contraire à `D-13` (le mode d'identité doit correspondre
à qui l'on est).

Le commanditaire (échange du 20/07/2026) veut **promouvoir ces portes en choix explicites** au
démarrage : plus lisible pour un bénévole qu'un rôle deviné.

## Décision

**Au 1ᵉʳ lancement, tant qu'aucun rôle n'est posé, l'app présente un écran de choix à quatre portes** —
**Tablette (cible)**, **Public (téléphone)**, **Scoreur**, **Admin (PC)** — et **mémorise** le choix
(`localStorage`, store `sessionRoleStore`). Aux ouvertures suivantes l'app va **droit** au rôle choisi,
**sans réafficher l'écran** : c'est le geste initial explicite, pas un menu récurrent (`D-09` — l'archer,
le plus nombreux, ne subit pas de friction à chaque ouverture).

### Le rôle effectif : une session en cours prime sur le choix

Le routage ne lit pas seulement le marqueur de choix : une **session déjà ouverte** l'emporte, pour
qu'une tablette rattachée ou un admin connecté ne **retombe jamais** sur l'écran de choix après un
simple rechargement (résilience jour J). L'ordre de résolution (fonction pure `resoudreRole`,
testée) :

1. **poste** — `estPoste` ou arrivée par `?poste=<code>` → **tablette** (verrou physique `D-13`,
   inconditionnel) ;
2. sinon le **marqueur de choix** s'il est posé → le rôle déclaré ;
3. sinon un **jeton admin** hérité → **admin** *(rétro-compat : une session d'avant cette US ne
   redemande pas le rôle)* ;
4. sinon un **jeton scoreur** hérité → **scoreur** *(idem)* ;
5. sinon **null** → l'écran de choix.

Les étapes 3–4 ne servent qu'à ne pas **rejouer** le choix pour une session préexistante ; en flux
normal, le marqueur (étape 2) est toujours posé au moment de choisir.

### Chaque porte mène où elle doit — pas d'escalade

- **Tablette** → **rattachement** (QR, ou URL + code + n° de cible, E04US001), puis reste un poste et
  **ne revoit jamais** l'écran de choix ni l'admin (`D-13` : qui tape sur la tablette d'une cible est
  légitime) ;
- **Public** → l'appli publique (classements, plans, suivi d'archers, E07US001/E07US006) **et rien
  d'autre** : l'entrée scoreur et le login admin en sont **retirés** — le public ne peut pas escalader
  (ni code scoreur, ni mot de passe admin) ;
- **Scoreur** → l'entrée par **code** (E10US003), itinérante, sans cible (`D-12`) ;
- **Admin** → le **login** (E10US002), puis la coquille d'administration (E00US015).

### Sortie de rôle : une échappatoire discrète, partout

Un choix mémorisé n'est pas une prison. Un contrôle discret **« Changer de rôle »** (en-tête) est
présent pour **Public / Scoreur / Admin** : il **réinitialise** le marqueur **et purge les sessions
locales** (poste, admin, scoreur) → retour à l'écran de choix. La **purge est nécessaire** : sans
elle, l'étape 3/4 de la résolution ré-inférerait aussitôt le rôle depuis le jeton résiduel et l'écran
de choix ne réapparaîtrait jamais. La **tablette** n'a **pas** ce contrôle d'en-tête (`D-13` : verrou
physique) — sa sortie reste le geste délibéré **« Détacher cette tablette »** déjà en place, auquel on
ajoute la réinitialisation du marqueur pour revenir au choix.

## Conséquences

- **Front seul.** Aucun schéma, aucune migration : on **réorganise l'aiguillage** et on **réemploie**
  les stores existants (`sessionPosteStore`, `sessionAdminStore`, `sessionScoreurStore`). Un nouveau
  store léger `sessionRoleStore` porte le seul marqueur de choix.
- **`CoquilleAdmin` recentrée.** Son repli « pas de session admin » n'est plus la consultation
  publique mais l'**écran de login** : elle n'est atteinte que par la porte Admin. La consultation
  publique devient une **destination à part entière** (porte Public), amincie de ses entrées scoreur /
  login / poste.
- **Tension assumée (`D-09` « GPS, pas tableau de résultats »).** Le CDC veut que l'archer tombe sur
  *sa journée*, pas sur un menu. Acceptable ici : l'écran n'apparaît qu'au **1ᵉʳ lancement** puis se
  souvient — la friction est **unique**, pas récurrente.
- **Purge locale, pas déconnexion serveur.** « Changer de rôle » efface les jetons **côté client** ;
  les sessions serveur correspondantes **expirent d'elles-mêmes** (comme au redémarrage serveur ou à
  la fin d'un tournoi, déjà gérés par les 401). Choix de simplicité cohérent avec le périmètre LAN
  mono-club (règle 12) ; une vraie déconnexion serveur pourra s'ajouter si le besoin apparaît.
- **Identité visuelle *par tournoi* hors périmètre.** L'écran de choix est **pré-tournoi** (aucun
  tournoi sélectionné, plusieurs peuvent coexister) : il porte un habillage **club/neutre** réutilisant
  les jetons de thème existants (clair/sombre système). L'**identité par tournoi** (logo, couleurs)
  reste à **E01US016**, qui en définira le modèle — la brancher ici aurait cassé la maille INVEST.
- **Pas de tests de rendu.** La logique risquée (la précédence de résolution) est isolée dans la
  fonction pure `resoudreRole`, **testée**. Le rendu des portes se vérifie **à l'écran** (les trois/
  quatre profils sur appareils isolés), comme noté au CA.
