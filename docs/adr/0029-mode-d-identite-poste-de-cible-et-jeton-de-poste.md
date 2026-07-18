# ADR-0029 — Mode d'identité « poste de cible » : code de cible régénérable, jeton de poste lié au tournoi

- **Statut** : Accepté
- **Date** : 2026-07-18
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E04-saisie-scores.md`](../../stories/E04-saisie-scores.md) (E04US001) ;
  [`docs/glossaire.md`](../glossaire.md) (`Poste`) ; [`docs/modele-de-donnees.md`](../modele-de-donnees.md)
  (table `POSTE`) ; [`docs/dette.md`](../dette.md) (DETTE-001, FK `poste.tournoi_id`).
- **Introduit par** : E04US001 (rattacher une tablette à sa cible).
- **S'appuie sur** : [ADR-0025](0025-mode-d-identite-scoreur-par-code-individuel.md) (dont il est le
  **troisième et dernier maillon** du modèle d'identité `D-13`), [ADR-0007](0007-erreurs-par-couche.md)
  (erreurs typées, mapping à la frontière), [ADR-0009](0009-gouvernance-dependances.md) (stdlib d'abord :
  aucune lib QR ni JWT ici).

## Contexte et problème

`D-13` (CDC UX §5) définit **trois modes d'identité proportionnés au risque** : l'**admin** (un
*secret*, ADR-0009), le **scoreur** (une *personne*, ADR-0025), et le **poste de cible** (un *lieu*).
Ce dernier est le mode le plus **ouvert** : le poste ne s'authentifie pas comme une personne — c'est
un **marqueur** (un archer de la cible, `D-04`) qui saisit sans se connecter (E10US007). Mais le poste
doit tout de même **savoir quelle cible il sert**, et le **retrouver seul après une coupure** : le parc
est fourni par le club, navigateur seul, **sans mode kiosque** (`D-05`) — la fermeture accidentelle de
l'onglet sur 30 postes × 8 h **arrivera**.

Le danger nommé par le CA : *un score parti **silencieusement** sur la mauvaise cible est pire qu'une
erreur visible*. D'où le rejet de l'IP et de l'empreinte comme identité (baux DHCP qui expirent,
30 tablettes identiques) au profit d'un **rattachement explicite**. Reste le piège « le jeton survit
trop bien » : au tournoi suivant, la tablette de la cible 12 posée sur la cible 5 se croirait encore 12.

Plusieurs choix que le CA ne tranche pas seul (arbitrés le 18/07/2026), dont l'ancrage de la
**révocation** — sans notion de « tournoi courant » côté serveur, et **avec** l'exigence nouvelle de
supporter **plusieurs tournois `EN_COURS` en même temps** (intérieur + extérieur, arbitrage du
18/07). D'où cet ADR.

## Décision

**1. Le poste de cible est une donnée métier persistée — le code de cible naît ici.** Table `poste`
(`tournoi_id`, `cible_index`, `code`), agrégat `domain.poste.Poste`, port `PosteRepository`, adapter
SQL — sur le patron `Scoreur` (ADR-0025), avec la même **asymétrie assumée avec l'admin**. Un `Poste`
matérialise le **credential d'une cible** `(tournoi_id, cible_index)` : la `Cible` elle-même reste un
value object dérivé du `GabaritSalle` (elle n'a pas d'identité propre) ; le `Poste` lui ajoute un
**code** distribuable. E09US008 (imprimer les QR) ne fera qu'**imprimer** ces codes — le **contrat**
(forme du code, URL de rattachement) est fixé **ici**, puisque E04US001 précède E09US008 malgré la
dépendance inverse de la séquence (défaut de backlog signalé, `stories/` corrigé).

**2. Code de cible généré par le serveur, unique dans toute la base, et RÉGÉNÉRABLE.** Comme le code
scoreur : alphabet **sans caractères confondables**, tiré par `secrets`, forme **canonique**
(`normaliser_code`), unicité **globale** (`UNIQUE(code)`) — le code seul désigne un poste sans
contexte tournoi, comme la connexion scoreur. Deux différences avec le scoreur :
- **`UNIQUE(tournoi_id, cible_index)`** en plus : un seul code vivant par cible d'un tournoi.
- Le code est **mutable** (`Poste.regenerer(nouveau_code)`), là où le code scoreur est figé. C'est ce
  qui rend le credential **révocable** : régénérer change le code imprimé → les anciens QR/jetons
  deviennent caducs. Un code déterministe (« T3-C12 ») ne serait **pas** révocable — d'où le stockage
  d'un code aléatoire. (2ᵉ occurrence d'un « générateur de code » : dupliqué sans factoriser, on
  attend une 3ᵉ preuve avant tout remède structurel — règle « dette ».)

**3. Session de poste : jeton opaque en mémoire, sans expiration, MAIS valide seulement tant que son
tournoi n'est PAS `TERMINE`.** Un jeton (`secrets.token_urlsafe`) lie `jeton → poste`
(`PosteSessionStore`), persisté en `localStorage` côté client (survit onglet fermé / redémarrage
tablette / veille), en mémoire côté serveur (invalidé au redémarrage serveur, cohérent ADR-0025). La
**nouveauté** face au scoreur : à **chaque résolution** de session, on vérifie que le tournoi du poste
n'est pas `TERMINE`. C'est l'ancrage de la révocation, compatible multi-tournois :
- **Plusieurs tournois non terminés coexistent** → l'intérieur et l'extérieur ont chacun leurs postes
  valides, simultanément. Aucun « tournoi courant » global (qui interdirait ce cas).
- **Terminer** un tournoi (`StatutTournoi.TERMINE`) invalide d'un coup **tous ses postes** → geste de
  fin normal qui force le re-rattachement au tournoi suivant.
- **Régénérer** le code d'un poste (nouveau code + purge de session) est une révocation ciblée sans
  terminer le tournoi : c'est le CA « régénérable » de **E09US008**, qui livrera la méthode domaine, la
  purge du store et l'endpoint. E04US001 s'en tient à la révocation par **terminer**.
- **Seuil « pas `TERMINE` » plutôt que « `EN_COURS` »** : l'acteur est l'organisateur **au montage**,
  qui rattache souvent **avant** de démarrer le tournoi (`D-07`, « tout se prépare à l'avance ») ; un
  `brouillon` doit donc pouvoir être rattaché. Seul le `terminé` ferme la porte (piège « le jeton
  survit trop bien »). La garde « on ne **saisit** que sur un tournoi en cours » relève de E04US002,
  pas du rattachement.

**4. En-tête dédié `X-Jeton-Poste`, portée `'poste'` orthogonale.** Le jeton de poste voyage dans un
en-tête distinct du Bearer admin et du `X-Jeton-Scoreur` (dépendance `exiger_poste`, symétrique). Les
trois modes sont **indépendants** : sur une même tablette un 401 de poste ne purge que la session
poste. La portée front devient `'admin' | 'scoreur' | 'poste' | 'aucune'`.

**5. Le jeton porte les préférences du poste (thème `D-26`) — côté client.** Le thème choisi
(sombre/clair, `D-26` : la lumière varie d'une cible à l'autre dans un gymnase) est rangé dans le
`sessionPosteStore` (persisté `localStorage`) **à côté** du jeton, et **revient tout seul** à la
réouverture. Le serveur n'a **pas** besoin de connaître le thème : c'est une préférence locale du
poste, pas une donnée métier. Le thème est **construit ici** (aucun mécanisme de bascule n'existait —
le front était `prefers-color-scheme` pur) : attribut `data-theme` sur `<html>` + bloc CSS miroir du
`@media (prefers-color-scheme: dark)` existant.

**6. L'IP n'est jamais l'identité.** Elle peut servir au **diagnostic** (superviser les postes,
E12US001) mais ne détermine **jamais** à quelle cible un score est rattaché — seul le jeton le fait.

## Conséquences

- **+** Support natif de **plusieurs tournois simultanés** (intérieur + extérieur) : rien n'est global,
  tout est scopé `tournoi_id`.
- **+** Révocation **explicite et par tournoi** (terminer / régénérer), le cœur de l'arbitrage : robuste
  sans inventer de « tournoi actif » global.
- **+** Le contrat d'identité du poste est **ici**, pas éparpillé : E09US008 (impression),
  E04US002 (saisie) et E10US007 (saisir sans s'identifier) s'appuieront sur `exiger_poste` **prêt**.
- **+** Aucune dépendance nouvelle : pas de lib QR (le QR n'encode qu'une **URL** ouverte par la caméra
  native — E09US008 génère l'image ; ici on lit juste un code dans l'URL, avec saisie manuelle en
  secours), pas de JWT (jeton opaque + store, comme ADR-0025).
- **−** **Limite inhérente, non corrigeable ici** : déplacer physiquement une tablette d'un tournoi vif
  à un autre **sans re-scanner** ne peut pas être rattrapé côté serveur (l'IP n'est pas l'identité, par
  conception `D-13`). Seul le rituel de re-scan (qui **écrase** le jeton local) couvre ce cas. C'est une
  propriété du modèle « le lieu », pas un défaut.
- **−** Sessions **en mémoire** : un redémarrage serveur force le re-rattachement (re-scan). Volontaire,
  cohérent ADR-0025, pas une perte de données (le code imprimé reste valide, on rescanne).
- **−** **Poste orphelin si le plan de salle rétrécit** : `assurer_codes` ne crée que les codes
  manquants (idempotent) mais ne **supprime pas** le poste d'une cible retirée du gabarit après
  préparation — son code reste listé et rattachable. Sans conséquence tant que la **saisie** n'existe
  pas (E04US002) ; la réconciliation poste ↔ plan (suppression/régénération) relève de **E09US008**
  (« régénérable »), qui possède déjà la gestion des codes. Édge connu, non silencieux.
- **−** FK `poste.tournoi_id` **sans `ON DELETE`** (DETTE-001, purge non tranchée) : élargit la dette
  existante d'une table, sans contournement local.
- **⚠ Dépendance en avant — cycle de vie à 7 statuts** : la garde de révocation s'appuie sur le seul
  `StatutTournoi.TERMINE` du cycle **actuel à 3 statuts** (brouillon/en_cours/terminé). L'entretien de
  conception du 18/07/2026 acte un **cycle à 7 statuts** (ADR « cycle-de-vie-du-tournoi-sept-statuts »,
  livré par **E01US017**), pas encore implémenté au moment d'E04US001. Quand il atterrira, **revisiter
  le seuil** : quels statuts (au-delà de « terminé » : « clos », « archivé », « annulé »… selon E01US017)
  rendent un jeton de poste caduc, et lesquels autorisent encore le rattachement. Le point d'accroche
  est unique (`ServicePostes._refuser_si_termine` + le contrôle de `resoudre_session`) — l'alignement
  sera local.
- **Périmètre** : E04US001 livre le **rattachement** (code de cible + jeton + reconnexion) et le
  **thème** par poste. La **saisie** proprement dite (grille, pavé, validation) est E04US002 ;
  l'**impression** des QR/codes est E09US008 ; la garde « le poste ne saisit que pour SA cible » sera
  posée par E10US007 sur `exiger_poste`.
