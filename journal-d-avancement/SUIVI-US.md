# Suivi des US — état d'avancement

> **Ce fichier est le point de reprise.** Quand l'utilisateur dit « **reprend les US** », l'assistant
> lit ce tableau : il y trouve ce qui est **fait** (mergé sur `main`), et **la prochaine US** à
> prendre. La séquence de référence est celle de [`stories/README.md`](../stories/README.md) (jalons
> de valeur J0→J4). Le détail de chaque US est dans `stories/Exx-*.md`.
>
> **Règle de mise à jour** : une US passe à ✅ **dans son propre dernier commit, la revue
> (`/revue-us`) faite et poussée** — sans attendre la confirmation « c'est mergé ». C'est sûr parce
> que cette mise à jour **voyage avec le diff de l'US** : elle n'atteint `main` qu'**au merge de la
> PR**. Donc sur `main` ce tableau reste **toujours vrai** (le ✅ y apparaît pile au merge) ; sur la
> branche, il est optimiste d'un cran — c'est le livrable. Le même commit pointe la 🎯 suivante. En
> cas de doute au moment de reprendre, recouper avec `git log main --first-parent` / `git branch -r`.

**Dernière mise à jour : 28/07/2026** · **81 US livrées** · dernière : `E12US002` *(lancer un tour — feu vert + lancement, la bascule de tour du J2)*.

---

## 🎯 Prochaine US

> **⚡ Priorité immédiate — retours de la démo du 27/07/2026.** Avant de reprendre la séquence J2,
> traiter le **lot démo** (bugs & petits ajouts), puis les épics **EPIC-14** (accueil admin) et
> **EPIC-15** (jeu d'essai & simulation) — détail en section « Ajouts de la démo du 27/07/2026 » plus
> bas. Ordre des bugs : ~~E02US010~~ ✅ (horaire `HH:MM`), ~~E01US017~~ ✅ (7 statuts),
> ~~E11US008~~ ✅ (LAN + QR), ~~E03US011~~ ✅ (placement), ~~E01US022~~ ✅ (blason FFTA).
> **Les bugs du lot démo sont clos**, **EPIC-14 est livrée** (accueil-tableau de bord + aide
> contextuelle) et **EPIC-15 est close** (`E15US001` jeu d'essai + `E15US002` moteur de simulation
> éphémère + `E15US003` cockpit de simulation livrés). **`E12US002` est livrée** (feu vert + lancement) ;
> la séquence J2 reprend maintenant à `E08US005`.
>
> **`E08US005` — rembourser une inscription payée annulée** : la **prochaine à prendre**. *Ensuite* :
> `E04US018` (afficher la prochaine cible après validation — le **premier écran récepteur** du signal
> de lancement émis par `E12US002`), puis `E07US008` / `E07US004` (les autres canaux).
> *Note : le **fil équipes** est **débloqué** — `E13US002` (composer les équipes) peut être pris à tout
> moment maintenant qu'`E13US001` a posé l'abstraction `Participant`.*
> *`E12US004` (tracer un forfait) est **absorbée** par `E04US015` — voir ci-dessous.*
> *J1 est **terminé** (46/46) ; le confort « ma journée » et les classements imprimables restent hors
> décompte du jalon.*
>
> *Fait juste avant :*
> - `E12US002` **lancer un tour — feu vert + lancement** — US à **surface visible**, la **bascule de
>   tour** du J2 (là où le produit gagne sa valeur). Un écran admin **« Feu vert »** (« Jour J »)
>   montre **en continu**, duel par duel à venir, les trois questions du CA — *participants connus ?*,
>   *cible attribuée ?*, *source amont validée ?* — et **nomme** le blocage (« en attente du duel n°3 »,
>   « cible non attribuée »), jamais un simple drapeau (`P-3`). Un **bouton chiffre** ce qu'il déclenche
>   (« 2 duels · cibles 1 · 4 archers prévenus ») et fait **partir** les duels **prêts** (jouables **et**
>   placés), l'unité lançable étant le **duel** (`D-23`) ; le geste est **recalculé dans la file**, jamais
>   cru sur parole (précédent E12US007), rien de prêt ⇒ 409 `aucun_duel_a_lancer`. **Décision d'archi
>   tranchée** ([ADR-0056](../docs/adr/0056-lancement-d-un-tour-acte-audite-et-diffuse.md)) : le lancement
>   est un **acte audité** (`ActionAuditee.LANCEMENT`) qui **déclenche la diffusion** d'un `LiveEvent`
>   typé post-commit (règle 7) — **aucun statut posé** sur le tableau (reconstruit, ADR-0049). **Périmètre
>   séquencé** (règle 9) : les 3 canaux récepteurs (tablette E04US018, public E07US008, salle E07US004)
>   n'existent pas — le signal **part** mais n'est écouté de façon ciblée par personne ; la cible des
>   tours ≥ 2 attend le placement 1→N (E05US010). `Q-UX6` **partiellement tranchée** (socle du CA livré ;
>   métriques d'exploitation en plus restent à arrêter devant l'écran). Nouveau `ServicePilotageTour`
>   (compose saisie + placement de duels + audit, service→service). Tests **service depuis le CA** (feu
>   vert, chiffrage, filtrage des non-prêts, trace) ; API **après** (câblage, diffusion typée). Oracle 120
>   vert. Front : écran + poll live, logique de présentation pure testée. Story alignée (Notes). Recette :
>   [`docs/fonctionnel/E12US002.md`](../docs/fonctionnel/E12US002.md).
> - `E15US003` **bot pilote automatique pausable + cockpit interactif multi-vues + canal isolé** — US à
>   **surface visible**, **3ᵉ et dernière d'EPIC-15** (close). Un écran admin **« Simulation »** rejoue
>   le tournoi courant **sans rien persister** : un **bot** génère des scores plausibles (déterministes
>   par graine, règle 9) et fait avancer qualif → duels → classement par **pas discrets pilotés côté
>   front** (ADR-0055 §2 : *ticker*, pas de boucle serveur → déterministe et testable). **Session
>   vivante** en mémoire (`ServicePilotageSimulation` + `SessionSimulation` + registre), **hors file
>   d'écriture** — règle 7 intacte, non-pollution **structurelle** (ADR-0054 réutilisé). Trois états
>   gardés `en_cours ⇄ en_pause → terminée` (409 hors état) ; **reprise en main** en pause : l'humain
>   joue la **même unité** que le bot (saisir une volée / désigner un vainqueur). **Générateur de
>   scores** = stratégie **injectable** (règle 1/2), application. **Canal WS isolé** `/ws/simulation`
>   (broadcaster dédié — l'isolement est **structurel**, deux hubs). Refactor : `charger_tournoi_simulable`
>   + `hydrater_harnais` extraits en **source unique** partagée avec le rejeu one-shot (E15US002
>   inchangé). Tests **service depuis le CA** (bot, pause/reprise, reprise en main qualif & duels,
>   déterminisme, non-pollution, garde-fous) ; API/WS **après** (câblage, canal isolé). Oracle 120 vert.
>   **Arbitrage tranché au cadrage** : périmètre **« tout d'un coup »** (bot + cockpit + reprise en main
>   + canal isolé), la reprise en main imposant la session vivante serveur. Story alignée (Notes).
>   Décisions : [ADR-0055](../docs/adr/0055-session-de-simulation-vivante-pilotee-par-pas.md). Recette :
>   [`docs/fonctionnel/E15US003.md`](../docs/fonctionnel/E15US003.md).
> - `E15US002` **moteur de simulation éphémère + garde-fou (non-persistance)** — US **sans surface
>   visible directe** (couche moteur/infra), **2ᵉ d'EPIC-15**, **cœur technique**. Rejoue le moteur
>   (qualif → duels → classement) d'un tournoi **avant démarrage** sur un jeu d'**adapters in-memory**
>   (`infrastructure/memory/`) câblant les **mêmes** services (`ServiceClassement`,
>   `ServicePlacementDuels`, `ServiceSaisieDuels`) et politiques que la production : « ne rien
>   persister » est **structurel** (aucun chemin de ces adapters vers SQLite ni la file d'écriture —
>   règle 7). **Option A** confirmée par le spike (aucun service moteur ne touche la base/la file).
>   **`ServiceSimulation`** (application) ne connaît **aucun** adapter : la composition root lui injecte
>   une **usine de harnais** (règle 8) ; il **hydrate** les repos in-memory par les ports (identifiants
>   préservés) puis fait tourner ses services. **Garde-fou** `SimulationTournoiDemarre` (409) —
>   simulable `brouillon`/`prêt` seulement (arbitrage « terminé/archivé ? » tranché **non**, cohérent
>   avec `PeuplementTournoiDemarre` d'E15US001). **Non-pollution vérifiée** sur **vraie base** (compteurs
>   de lignes inchangés). **Anti-dérive** par **tests de conformité de port** (mêmes assertions
>   SQL ↔ in-memory). **Pas d'API ni d'UI** (substrat pour le cockpit E15US003). Tests service **depuis
>   le CA** ; oracle 120 vert. Décisions : [ADR-0054](../docs/adr/0054-execution-ephemere-du-moteur-sur-adapters-in-memory.md).
> - `E15US001` **jeu d'essai : générer des inscrits + scénarios rejouables** — US à **surface visible**,
>   **1ʳᵉ d'EPIC-15**. Un écran admin **« Jeu d'essai »** (groupe Préparation) : bouton **« peupler N
>   archers »** sur le tournoi courant (données réalistes, N borné [1, 500]) **et** un **catalogue de
>   scénarios** (`petit` 16 · `gros` 120 · `multi-format` 60) qui **instancie un tournoi complet prêt à
>   lancer** (catégories FFTA + départs + archers inscrits → passe `prêt`). **Donnée réelle persistée**,
>   **à distinguer** de la simulation éphémère (E15US002). **Arbitrages tranchés au cadrage** : trio de
>   scénarios figé + destination dédiée + graine optionnelle. **Déterminisme** (règle 9) par
>   `random.Random(graine)` injectée. **Réutilise les services existants** (`ServiceJeuEssai` compose
>   Tournois/Catégories/Départs/Archers/Inscriptions/Clubs — pas de court-circuit du domaine), tout dans
>   **une** commande de file (patron `precharger_ffta`). **Pas d'ADR** (outillage sans nouveau pattern,
>   règle 12). Tests service **depuis le CA** ; API testée après. Story alignée (Notes). Recette :
>   [`docs/fonctionnel/E15US001.md`](../docs/fonctionnel/E15US001.md).
> - `E14US002` **aide contextuelle « ce qui est saisissable et pourquoi »** — US à **surface visible**,
>   **2ᵉ et dernière d'EPIC-14** (close). Sur **chaque** écran d'administration, un bouton **« ⓘ Aide »**
>   replié par défaut se **déplie au tap** pour expliquer, en langage organisateur, ce qui s'y saisit et
>   à quoi ça sert en aval. **Présentation pure** — **aucun** changement domaine/API (note story
>   respectée). **Arbitrages tranchés au cadrage** (CA stub → maquette) : **(1)** couvrir **toutes les
>   ~22 destinations** (pas seulement les écrans de saisie), texte **centralisé** ; **(2)** forme **bouton
>   « ⓘ » déployé au tap**, masqué par défaut — dicté par la contrainte **tactile** (les `title=` au
>   survol ne s'affichent pas au doigt). D'où : un composant unique `AideEcran` (`shared/ui/`, patron
>   comme `MessageErreur`), un dictionnaire `id → texte` (`features/admin/aide-ecrans.ts`, **1 point de
>   vérité**), rendu **une seule fois** en tête de `.coquille__contenu` (la coquille connaît la
>   destination active → zéro édition des 22 features). Textes = **1ᵉʳ jet à relire** avec l'organisateur
>   (signalé dans le fichier). Story alignée (Notes). **Extension à la demande utilisateur** : l'US
>   **outille le test de rendu front** (Testing Library + jsdom, devDependencies MIT, `npm audit` vert),
>   env `jsdom` global + `src/test-setup.ts`, et **1er test de rendu** `AideEcran.test.tsx` — décision
>   structurante, [ADR-0053](../docs/adr/0053-outillage-test-de-rendu-front.md), libs dans
>   [`docs/dependances.md`](../docs/dependances.md) ; sert désormais aux US front suivantes. Recette :
>   [`docs/fonctionnel/E14US002.md`](../docs/fonctionnel/E14US002.md).
> - `E14US001` **accueil-tableau de bord contextualisé par tournoi (`D-20`)** — US à **surface
>   visible**, **première d'EPIC-14** (lisibilité admin). Choisir un tournoi ouvre son **Accueil** :
>   (1) **frise des 7 statuts** (ADR-0026), courant surligné, avec les **boutons d'action** offerts
>   par le statut ; (2) **checklist « à faire »** (réutilise la complétude E12US005) ; (3)
>   **chiffres-clés** — inscrits & réglés (paiements E08US002), postes en ligne (supervision E12US001)
>   — et **alertes** dérivées. **Aucune règle métier nouvelle** (agrège, ne recalcule pas — cadrage).
>   **Arbitrages tranchés au cadrage** (CA stub) : *les 3 briques d'un coup* + *frise à boutons
>   d'action* → d'où l'exposition en **lecture** de la topologie (`transitions_possibles` domaine +
>   `GET …/transitions`, source unique + test de cohérence topologie↔gardes, règle 1). **Bug corrigé
>   au passage** : le front ne gérait que **3 statuts** et se **bloquait** dès `prêt`/`en_pause` (badge
>   muet, aucun bouton) → aligné sur les 7 ; la frise **remplace** l'ancien `CycleDeVie`. Story alignée
>   (Notes). Décisions : [ADR-0052](../docs/adr/0052-accueil-admin-contextualise-par-statut.md).
>   Recette : [`docs/fonctionnel/E14US001.md`](../docs/fonctionnel/E14US001.md).
> - `E01US022` **blason FFTA par défaut par catégorie + affichage hérité** — US à **surface visible**
>   (dernier bug du lot démo). Le pré-chargement FFTA (`precharger_ffta`) crée désormais aussi les
>   **quatre blasons** canoniques du §3 — « Blason 80 cm » / « 60 cm » / « 40 cm » / « Triple 40 cm »
>   — et **relie chaque catégorie au sien** (Classique U11 → 80, U13/U15 → 60, adultes → 40 ;
>   Poulies → triple 40 ; Arc Nu « U18 » → 60, « Scratch » → 40). **Arbitrage de périmètre tranché**
>   (option « preset blasons + défauts + affichage ») : `blason_id` étant une FK vers un blason
>   **existant du tournoi** et E01US005 n'ayant livré **aucun jeu** de blasons, l'US **absorbe** leur
>   pré-chargement (idempotent par nom, réutilise un blason personnalisé de même nom). `taille` =
>   fraction de place (canoniques du placement : 80 → `1.0`, 60 → `0.5`, 40/triple → `0.25`) ; le
>   triple 40 se distingue par ses **zones** (10 → 6 + M, pas de 5 → 1, §4.4). Blasons/liens
>   **modifiables** (template, RG-8). Affichage **lecture** sur `Archers.tsx` (liste) et
>   `NouvelArcher.tsx` (indice sous la catégorie) — **pas** de blason par archer (hors périmètre).
>   Story alignée (Notes). Recette : [`docs/fonctionnel/E01US022.md`](../docs/fonctionnel/E01US022.md).
> - `E03US011` **placement : retour visuel de génération + position A..D côté admin** — US à
>   **surface visible**, correctif **front** (présentation, domaine inchangé). Le bouton
>   **« Générer le plan »** affiche « Génération… » pendant l'appel puis **confirme le résultat**
>   (« Plan prêt » si tous placés ; « Plan généré : N placés, M en réserve » sinon ; « aucun archer à
>   placer » si le départ est vide) — l'échec silencieux diagnostiqué était **muet-mais-ok** (le POST
>   `/regenerer` réussit, seul le retour manquait). Et chaque archer posé affiche sa **position**
>   (lettre A..D, badge accent) sur sa cible **côté admin**, comme côté public — la lettre
>   n'apparaissait que sur les cases **libres**. Recette : [`docs/fonctionnel/E03US011.md`](../docs/fonctionnel/E03US011.md).
> - `E11US008` **accès réseau LAN + QR de rattachement à l'écran** — US à **surface visible**. Le
>   lancement de dev (`run_dev.py`) écoute désormais sur **`0.0.0.0`** comme la release (`--host` pour
>   restreindre), et **affiche l'IP LAN** joignable par les tablettes (réutilise `release.reseau.adresse_lan`).
>   L'écran **Postes de cible** affiche, par cible, son **QR de rattachement** en **image SVG**
>   (vectorielle, agrandissable pour le scan) via un endpoint `GET …/postes/{cible_index}/qr` — rendu
>   `renderSVG` **pur Python**, aucune dépendance ajoutée (PNG/`renderPM` écarté : `rlPyCairo` absent).
>   Endpoint **admin** (le QR encode le code) ; le front le charge en **blob authentifié** (le Bearer
>   admin est en JS, un `<img src>` direct n'emporterait pas le jeton). **DETTE-012** gagne un **2ᵉ
>   consommateur** (même marqueur) et reste **ouverte** ; sa parade — ouvrir l'admin par l'IP LAN —
>   est désormais **atteignable en dev** et **documentée** (`docs/deploiement.md` §6). Recette :
>   [`docs/fonctionnel/E11US008.md`](../docs/fonctionnel/E11US008.md).
> - `E02US010` **horaire de départ `HH:MM` obligatoire & ≥ 1 départ** — US à **surface visible**.
>   L'horaire d'un créneau devient une **vraie donnée temporelle `HH:MM`** (24 h), **obligatoire**,
>   validée **au domaine** (422 ; 400 si le champ manque à la frontière) — le libellé libre
>   d'E02US004 est abandonné ; le front pose un **masque de saisie**. Deux gardes de cohérence :
>   passer un tournoi **`prêt`** exige **≥ 1 départ** (`TournoiSansDepart`, première brique de la
>   complétude de préparation, [ADR-0026] §2), et supprimer le **dernier** départ d'un tournoi
>   **non-brouillon** est **refusé** (`DernierDepartNonSupprimable`). Migration 0032 : reprise
>   best-effort des horaires libres existants → `HH:MM` + colonne NOT NULL. La suppression d'un
>   tournoi non vide reste bloquée par **DETTE-001** (500), rendue systématique par cette US (notée).
>   Recette : [`docs/fonctionnel/E02US010.md`](../docs/fonctionnel/E02US010.md).
> - `E12US008` **cycle de vie d'un départ** — US à **surface visible**. Un créneau porte un **état
>   dérivé** (jamais saisi) : **ouvert** (aucun score) → **lancé** (au moins une flèche validée) →
>   **clos** (toutes les séries closes, barème validé ou forfait). Modifier/supprimer un créneau
>   **lancé/clos** est **signalé et confirmable** (alerte chiffrée, même famille qu'E12US007) ; un
>   créneau **ouvert** reste librement éditable (E02US009 inchangé). État **non stocké** : calculé en
>   réutilisant `ServiceCompletude` via un **port étroit** (comme `LecteurPaiements`). À la
>   suppression, la confirmation de cycle **subsume** celle des inscriptions. Badge d'état + confirmation
>   côté front. Décisions : [ADR-0051](../docs/adr/0051-cycle-de-vie-d-un-depart.md). Recette :
>   [`docs/fonctionnel/E12US008.md`](../docs/fonctionnel/E12US008.md).
> - `E04US015` **gérer abandon / disqualification** — US à **surface visible**. Un acte **scoreur**
>   « déclarer abandon / DSQ », **en qualification comme en duels** ([ADR-0050](../docs/adr/0050-forfait-abandon-et-disqualification.md),
>   qui **fusionne E04US015 + E12US004**). Concept unique `Forfait` **scopé à la phase** : en qualif
>   un **abandon** est relégué en fin de classement (rangé, score affiché), une **DSQ** en est sortie
>   (rang vide, score conservé) ; en duels le forfaitaire **cède** son match (l'adversaire passe). Les
>   **flèches sont préservées** (≠ suppression, ADR-0016) ; l'acte est **daté, attribué, motivé,
>   réversible** (`D-15`) et **audité** (`FORFAIT`). **DETTE-014 résorbée** (la complétude compte un
>   forfaitaire comme « série close »). `Q-UX5` fermée sur le **scoreur**. Recette :
>   [`docs/fonctionnel/E04US015.md`](../docs/fonctionnel/E04US015.md).
> - `E04US013` **écran scoreur (tranche front)** — US à **surface visible**, sous la **même US** que le
>   backend (le compte d'US ne bouge pas). Le scoreur choisit une **phase de tableau**, voit la **liste
>   des duels par tour**, ouvre un duel et le score : **grille de manches** (sets ou cumul selon `mode`,
>   résolu par arme côté serveur — le front n'en décide pas), **barrage** conditionnel (§8.2, désignation
>   manuelle du plus près du centre), **validation** qui verrouille et fait avancer le tableau jusqu'au
>   **podium**. **File hors-ligne + rejeu** dédiée aux actes de duel (2ᵉ occurrence du motif de
>   résilience, **dupliquée** — pas extraite, règle 12). Le **contrat de lecture** des duels a été
>   **enrichi** (pavé exposé dès la lecture : zones du blason, nb de manches/flèches, seuil), analogue à
>   la grille de qualif. Écran monté dans l'**Espace scoreur**. Recette :
>   [`docs/fonctionnel/E04US013.md`](../docs/fonctionnel/E04US013.md).
> - `E04US013` **backend** (saisie en duels) — **sans surface visible** (domaine → moteur → politiques →
>   persistance → service → **API scoreur**). Un **duel** se score au **système de sets** (points de set
>   2/1-1/0, premier à 6 — FFTA ; club 4) ou **au cumul** en arc à poulies (A.7.5.2) ; à égalité, un
>   **barrage** (1 flèche, puis désignation du plus près du centre — l'appli ne mesure pas la distance).
>   Le **vainqueur validé** est transmis au moteur `Tableau.jouer` : le tableau, **non persisté**, est
>   **reconstruit** du classement et **rejoué** des duels validés (seul le **tir** est persisté, table
>   `duel`, migration 0030). Le barème est **résolu par arme** via un **résolveur injecté à défaut FFTA**
>   (E01US011 le configurera — **dépendance sur-affirmée retirée**). Décisions :
>   [ADR-0049](../docs/adr/0049-saisie-et-scoring-des-duels.md).
> - `E03US009` (placer les duellistes côte à côte) — US à **surface visible**. Le placement d'une phase
>   de tableau met les **deux adversaires d'un duel** du 1er tour **côte à côte** « dans la mesure du
>   possible », par ré-ordonnancement de l'entrée du glouton (moteur inchangé, ADR-0048) ; les duels non
>   rapprochés sont **signalés**. Plan **matérialisé par phase** (table `placement_tableau`, migration
>   0029), ajustable au glisser-déposer. Recette : [`docs/fonctionnel/E03US009.md`](../docs/fonctionnel/E03US009.md).

---

## J0 — Walking skeleton — ✅ **terminé (12/12)**

| US | Titre | État |
|---|---|---|
| E00US001 | Initialiser le monorepo | ✅ |
| E00US002 | Configurer la qualité (ruff, mypy, ESLint…) | ✅ |
| E00US003 | CI bloquante | ✅ |
| E00US004 | Squelette de couches + garde-fou d'imports | ✅ |
| E00US005 | Composition root minimale | ✅ |
| E00US006 | SQLite (WAL) + migration initiale | ✅ |
| E00US007 | File d'écriture + writer unique | ✅ |
| E00US008 | WebSocket + diffusion post-commit | ✅ |
| E00US009 | Repository + endpoint bout-en-bout | ✅ |
| E00US010 | Shell React | ✅ |
| E00US011 | Tranche verticale démontrable | ✅ |
| E00US012 | Exécutable de dev (FastAPI sert le front) | ✅ |

## J1 — Tournoi de qualification de bout en bout — ✅ **terminé (46/46)**

| Seq | US | Titre | État |
|---|---|---|---|
| 13 | E01US001 | Créer un tournoi | ✅ |
| 14 | E10US002 | Accès administrateur protégé | ✅ |
| 15 | E10US001 | Consultation publique ouverte | ✅ |
| 16 | E01US002 | Éditer / lister les tournois | ✅ |
| 17 | E01US003 | Gérer les catégories (CRUD) | ✅ |
| 18 | E01US004 | Pré-charger les catégories FFTA salle | ✅ |
| 19 | E01US013 | Catégorie : éligibilité multi-âges | ✅ |
| 20 | E01US005 | Gérer les blasons | ✅ |
| 21 | E01US014 | Blason : valeurs de score admises | ✅ |
| 22 | E01US006 | Associer catégorie ↔ blason | ✅ |
| 23 | E01US007 | Définir un gabarit de salle | ✅ |
| 24 | E01US008 | Réutiliser / ajuster un gabarit | ✅ |
| 25 | E01US009 | Définir un barème de qualification | ✅ |
| 26 | E01US015 | Grain de validation d'une phase | ✅ |
| 27 | E01US010 | Définir le tarif par départ | ✅ |
| 28 | E02US001 | Gérer le référentiel clubs | ✅ |
| 29 | E02US002 | Créer un archer | ✅ |
| 30 | E02US003 | Éditer / supprimer un archer | ✅ |
| 31 | E02US004 | Configurer les départs (créneaux) | ✅ |
| 32 | E02US009 | Inscrire un archer sur des départs | ✅ |
| 33 | E00US014 | Outiller les tests du front | ✅ |
| 34 | E08US001 | Calculer le montant dû | ✅ |
| 35 | E03US001 | Placement automatique & plan de cibles | ✅ |
| 36 | E03US004 | Ajuster le placement (glisser-déposer) | ✅ |
| 37 | E10US003 | Scoreurs : définition & session | ✅ |
| 38 | E09US008 | Imprimer QR de cible & codes scoreurs | ✅ |
| 39 | E04US001 | Rattacher une tablette à sa cible (QR) | ✅ |
| 40 | E10US007 | Poste de cible : saisir sans s'identifier | ✅ |
| 41 | E04US002 | Saisie de qualification en temps réel | ✅ |
| 42 | E04US009 | Diffusion live & résilience réseau | ✅ |
| 43 | E12US001 | Superviser les postes de saisie | ✅ |
| 44 | E06US001 | Classement de qualification | ✅ |
| 45 | E07US001 | Vues publiques : classements, plans, live | ✅ |
| 46 | E07US006 | Suivre des archers : ma journée *(tranche 1, front)* | ✅ |
| **46b** | **E07US009** | **Suivre le déroulé du tour en direct** *(tranche 2, backend + ADR)* | ✅ |
| 47 | E10US005 | Journal d'audit métier | ✅ *(fait en avance)* |
| 48 | E12US007 | Alerter par calcul d'impact | ✅ |
| 49 | E08US002 | Suivi des paiements | ✅ |
| 50 | E12US005 | Afficher la complétude du tournoi | ✅ |
| 51 | E12US006 | Rechercher un archer depuis n'importe où | ✅ |
| 52 | E02US005 | Détecter et fusionner les doublons | ✅ |
| 53 | E02US006 | Contrôler les quotas | ✅ *(fait en avance)* |
| 54 | E09US001 | Socle PDF & feuille de marque | ✅ *(fait en avance)* |
| 55 | E09US003 | Listes imprimables (placement, club, paiement) | ✅ |
| 56 | E11US001 | Release, base et mise en réseau | ✅ |
| 57 | E11US003 | Sauvegarde & archive | ✅ |

## J2 — Duels simples + bascule de tour — 🔶 **en cours (9/14)**

| Seq | US | Titre | État |
|---|---|---|---|
| 58 | E05US001 | Séquence de phases | ✅ |
| 59 | E05US003 | Politiques injectables & assemblage | ✅ |
| 60 | E05US005 | Arbre d'élimination directe *(moteur sur `Participant`)* | ✅ |
| 61 | E03US006 | Contrainte ≥ 2 clubs par cible | ✅ |
| 62 | E03US009 | Placer les duellistes côte à côte | ✅ |
| 63 | E04US013 | Saisie en duels | ✅ *(backend + API + écran scoreur)* |
| 64 | E04US015 | Gérer abandon / disqualification | ✅ *(qualif + duels, ADR-0050)* |
| 65 | E12US004 | ~~Tracer un forfait~~ | ⛔ *(absorbée par E04US015)* |
| 66 | E12US008 | Cycle de vie d'un départ | ✅ *(état dérivé + garde-fou confirmable, ADR-0051)* |
| 67 | E08US005 | Rembourser une inscription payée annulée | 🎯 *(prochaine — J2 reprend ici)* |
| 68 | E12US002 | Lancer un tour (feu vert + lancement) | ✅ *(feu vert + lancement-événement, ADR-0056)* |
| 69 | E04US018 | Afficher la prochaine cible après validation | ⬜ |
| 70 | E07US008 | Vue publique des affectations du prochain tour | ⬜ |
| 71 | E06US003 | Barrage de tir pour places décisives | ⬜ |
| 72 | E06US004 | Podium des duels & agrégation des rangs | ⬜ |

## J3 — Placement intégral 1→N + écran de salle — 🔶 **en cours (2/11)**

| Seq | US | Titre | État |
|---|---|---|---|
| 73 | E05US010 | Placement intégral 1→N | ⬜ |
| 74 | E05US015 | Big Shoot Off | ⬜ |
| 75 | E05US018 | Oracle 120 (rejeu + comparaison) | ⬜ |
| 76 | E06US006 | Classement intégral 1→N & profondeur | ⬜ |
| 77 | E03US007 | Contrainte séparation catégorie/blason | ⬜ |
| 78 | E09US005 | Classements PDF | ⬜ |
| 79 | E00US013 | Factoriser les briques d'UI partagées | ✅ *(remontée de J3, DETTE-004 résorbée)* |
| 80 | E01US016 | Définir l'identité visuelle du tournoi | ⬜ |
| 81 | E07US004 | Écran de salle : déroulé auto & pilotage | ⬜ |
| 82 | E07US005 | Vue tableaux/arbres live | ⬜ |
| 83 | E05US019 | Enregistrer une séquence comme modèle | ⬜ |
| — | E00US015 | Ossature de navigation admin (coquille) | ✅ *(fait en avance — ajout 18/07)* |

## J4 — Confort, richesse & robustesse — ⬜ **non commencé (0/8)**

| Seq | US | Titre | État |
|---|---|---|---|
| 84 | E02US007 | Importer un fichier inscript'arc | ⬜ |
| 85 | E01US011 | Presets de barèmes multi-phases | ⬜ |
| 86 | E01US012 | Gérer plusieurs gabarits | ⬜ |
| 87 | E03US010 | Générer / éditer le déroulé horaire | ⬜ |
| 88 | E09US007 | Déroulé horaire imprimable | ⬜ |
| 89 | E05US016 | Routing repêchage-réintégration (WA) | ⬜ |
| 90 | E11US006 | Restauration & arrêt propre | ⬜ |
| 91 | E10US006 | Modifier le mot de passe admin | ⬜ |

## Ajouts de l'entretien du 18/07/2026 — 🔶 **en cours (4/10)**

> Non renumérotés dans les jalons ci-dessus (séquence indicative, à insérer au bon rang). Cf.
> [`stories/README.md`](../stories/README.md) § « Ajouts » et ADR-0026/0027/0028.

| US | Titre | Jalon | État |
|---|---|---|---|
| E00US015 | Coquille de navigation admin | J3 | ✅ |
| E00US016 | Écrans admin : liste/fiche & référentiels | J3 | ⬜ *(définie en `stories/`, non implémentée)* |
| E01US017 | Cycle de vie enrichi (7 statuts) | J1 | ✅ |
| E01US018 | Vocabulaire de score configurable | J1 | ⬜ *(idem)* |
| E01US019 | Capacité de cible non bornée | J1→J3 | ⬜ *(idem)* |
| E02US010 | Horaire de départ HH:MM obligatoire | J1 | ✅ |
| E13US001 | Abstraction participant | J2 | ✅ *(livrée avant E05US005, ADR-0028)* |
| E13US002 | Composer les équipes d'un tournoi | J2 | ⬜ |
| E13US003 | Scoring d'équipe (politique injectable) | J2 | ⬜ |
| E13US004 | Placement, saisie & classement par équipe | J2→J3 | ⬜ |

## Ajout du 20/07/2026 — ✅ **livrée (1/1)**

> Issu de l'échange sur le modèle d'entrée de l'appli (une seule SPA, désormais **quatre** expériences).
> Cf. [`stories/E00-socle.md`](../stories/E00-socle.md) § E00US017 et [ADR-0042](../docs/adr/0042-modele-d-entree-choix-de-role-explicite.md).
> Livrée le 21/07 : écran de choix 4 portes (Tablette / Public / Scoreur / Admin), choix persistant,
> le public ne peut pas escalader, échappatoire « Changer de rôle » ; front seul.

| US | Titre | Jalon | État |
|---|---|---|---|
| E00US017 | Écran d'accueil : choisir son appareil / rôle | J3 | ✅ |

## Ajout du 21/07/2026 — ⬜ **à planifier (0/2)**

> Issus du cadrage d'E08US002 : la tarification devient une **configuration du tournoi**
> ([ADR-0041](../docs/adr/0041-tarification-configuration-du-tournoi.md)). Ouverture **décidée**, pas
> codée — seule « somme des tarifs de l'archer » est implémentée. Cf. [`stories/E01-configuration.md`](../stories/E01-configuration.md).

| US | Titre | Jalon | État |
|---|---|---|---|
| E01US020 | Modèle de tarification injectable & sujet de facturation (archer/club) | à planifier | ⬜ *(définie en `stories/`, non implémentée ; sujet `club` sur `club_id`/ADR-0014, **pas** via E13)* |
| E01US021 | Tarification dégressive (option config, %/montant) | à planifier | ⬜ *(définie en `stories/`, non implémentée ; dépend d'E01US020)* |

## Ajouts de la démo du 27/07/2026 — ✅ **traités (10/10)**

> Retours de la présentation au client final **et** du développeur (27/07/2026). Cadrage par le
> dialogue (esprit agile). Deux US **déjà spécifiées** remontent en priorité (♻️, pas de doublon) ;
> les autres sont **neuves** (🆕). **Bugs d'abord**, puis EPIC-14 (accueil admin) et EPIC-15 (jeu
> d'essai & simulation). Détail des US : `stories/Exx-*.md`. Épics :
> [`EPIC-14`](../epics/EPIC-14-lisibilite-admin.md), [`EPIC-15`](../epics/EPIC-15-jeu-d-essai-simulation.md).

| US | Titre | Épic | État |
|---|---|---|---|
| E02US010 | Horaire de départ `HH:MM` (corrige « 8h00 → 18h00 » : n° collé à l'horaire) | E02 ♻️ | ✅ |
| E01US017 | Cycle de vie enrichi (7 statuts) — **prérequis** du dashboard | E01 ♻️ | ✅ |
| E11US008 | Accès LAN (poste organisateur) + QR de rattachement à l'écran | E11 🆕 | ✅ |
| E03US011 | Placement : retour visuel de génération + position A..D côté admin | E03 🆕 | ✅ |
| E01US022 | Blason FFTA par défaut par catégorie + affichage hérité | E01 🆕 | ✅ |
| E14US001 | Accueil-tableau de bord contextualisé (`D-20`) | E14 🆕 | ✅ |
| E14US002 | Aide contextuelle « ce qui est saisissable & pourquoi » | E14 🆕 | ✅ |
| E15US001 | Jeu d'essai : générer des inscrits + scénarios rejouables | E15 🆕 | ✅ |
| E15US002 | Moteur de simulation éphémère + garde-fou (non-persistance) | E15 🆕 | ✅ *(rejeu in-memory, ADR-0054)* |
| E15US003 | Bot pilote auto pausable + cockpit interactif multi-vues | E15 🆕 | ✅ *(session vivante + canal isolé, ADR-0055)* |

## US caduque

| US | Titre | Motif |
|---|---|---|
| E10US004 | ~~Habiliter un scoreur sur plusieurs cibles~~ | Sans objet depuis `D-12`/`D-13` (scoreur itinérant). Conservée comme trace. |

---

## Légende

- ✅ mergé sur `main` · 🎯 prochaine US à prendre · 🔶 jalon en cours · ⬜ à faire
- *« fait en avance »* : US traitée avant son rang de séquence (dépendance ou opportunité).
- *« définie en `stories/`, non implémentée »* : le fichier de spec existe (créé à l'entretien du
  18/07) mais aucun code n'est livré — ne pas confondre présence en `stories/` et US faite.
