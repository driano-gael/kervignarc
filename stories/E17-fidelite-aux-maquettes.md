# EPIC-17 — Fidélité de l'application aux maquettes — User Stories

> Voir [`epics/EPIC-17`](../epics/EPIC-17-fidelite-aux-maquettes.md) et
> [ADR-0074](../docs/adr/0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md).
>
> **Ne pas confondre avec [`E16`](E16-retours-maquettes.md)** : E16 traite ce que le commanditaire
> reproche **aux maquettes** ; E17 amène **le produit** jusqu'à elles. Une US qui change ce que
> montre un écran est une E16 ; une US qui change **la ressemblance** entre l'écran et sa planche est
> une E17.
>
> **La source du CA est ici la planche et la charte mesurée**, pas un questionnaire : les écarts se
> constatent en superposant `maquettes/<code>-<slug>.html` et l'écran livré.

---

### E17US001 — Poser la charte du club dans l'application
*En tant qu'*organisateur, *je veux* que l'application porte **les couleurs et la typographie de mon club**, *afin de* montrer au bureau l'outil qui a été validé sur les maquettes, et non une maquette technique grise et violette.

- **Contexte** : `frontend/src/index.css` portait encore, en toutes lettres, le socle du walking
  skeleton — *« le design sur-mesure sera posé par les US design »*. Ces US n'existaient pas. Les 98
  US livrées ont donc toutes hérité d'un accent violet `#aa3bff`, d'un fond blanc et de `system-ui`.
- **CA** :
  - **aucune couleur n'est écrite dans le front hors d'`index.css`** — les features ne connaissent
    que des jetons **sémantiques** (le nom dit l'usage, jamais la teinte) ; les seules exceptions
    admises sont celles qui ont une raison **physique** et commentée (le QR reste sur fond blanc pour
    rester scannable, quel que soit le thème) ;
  - les jetons portent **les valeurs de la charte mesurée** ([CDC design §3.3](../cahier-des-charges-design.md)),
    telles que transcrites par [`maquettes/assets/systeme.css`](../maquettes/assets/systeme.css) —
    anthracite `#1D1D1B`, rouge club `#B71918`, alerte ambre `#FFB000` ;
  - **le rouge du club n'est jamais une couleur de texte ni de contour en thème sombre** (`DV-04`,
    2,55:1) : trois jetons distincts selon l'usage — aplat, contour, texte ;
  - **l'alerte est ambre, jamais rouge** (`DV-03`) ; le rouge sur l'anthracite ne signale rien ;
  - **chaque déclinaison de thème redéfinit l'ensemble des jetons** : un jeton oublié dans un thème
    est une faute de contraste silencieuse (l'ambre `#FFB000` tombe à 1,83:1 sur blanc) ;
  - **le thème sombre est le défaut**, sans suivre le système (`DV-02`) ; le choix explicite d'un
    poste le surcharge, et l'option « Système » de `D-26` **reste disponible et fonctionnelle** ;
  - un **contour d'élément actionnable** (champ, bouton, touche) est distinct d'un **séparateur
    décoratif** : 4,04:1 contre 1,55:1 (WCAG 1.4.11) ;
  - la **police est celle des maquettes**, à pile de repli identique, pour que l'écran et la planche
    se dégradent de la même façon quand Inter est absente du poste.
- **Notes** : `DV-02`, `DV-03`, `DV-04`, `DV-07`, `D-26` · [ADR-0074](../docs/adr/0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md).
  **Un seul arbitrage discutable** : l'ancien `--text` du produit (corps) devient
  `--text-secondary` et non `--text`, pour **conserver la hiérarchie à deux niveaux** que
  `--text`/`--text-h` portaient. Reprendre `--text` partout aurait mis tout le corps de texte à
  16,88:1 et aplati la hiérarchie sur la seule graisse. **Réversible en une ligne** si le rendu
  paraît trop sourd. **Non fait, à arbitrer** : embarquer Inter (ajout d'actif, règle 11 — sans
  fichier local, aucune tablette ne la chargera le jour J, qui tourne sans internet) ; et la
  **couleur d'une action destructrice**, que la charte ne définit pas — elle est ambre par défaut,
  ce qui lui fait partager sa teinte avec « poste hors ligne ».
- **Dépend de** : — · **Jalon** : J1 *(transverse : conditionne toute confrontation d'écran)*

### E17US002 — Le catalogue de composants adopte les formes des planches
*En tant qu'*organisateur, *je veux* que les boutons, cartes, champs, onglets et pastilles de l'application aient **la forme de ceux des maquettes**, *afin de* reconnaître l'outil validé sur toutes les pages à la fois, et pas seulement à ses couleurs.

- **Contexte** : la charte (E17US001) a donné à l'application les bonnes **couleurs** ; il lui restait
  la mauvaise **silhouette**. Le front arrondissait tout entre 8 et 12 px là où les planches
  distinguent deux familles — l'ossature à 8-10 px, le contenu à 4-6 px —, et son bouton d'action
  était en graisse 500 contre 800.
- **CA** :
  - les composants partagés reprennent les **valeurs des planches** : rayons, tailles, graisses,
    interlettrages — bouton d'action, bouton discret, champ, carte, pastille d'état, onglets, titre
    d'application, en-tête de table ;
  - **la densité n'est pas reprise** : le commanditaire a demandé l'inverse en A02 (« je mettrai plus
    d'espace, plus aéré […] et cela pour tous les écrans »). Un arbitrage explicite l'emporte sur la
    planche (ADR-0074) ;
  - **la structure sémantique n'est pas sacrifiée à l'allure** : une liste tabulaire reste un
    `<table>` et prend l'**apparence** de la carte-tableau des planches, sans devenir une pile de
    `<div>` — un lecteur d'écran doit continuer d'annoncer l'en-tête de colonne ;
  - un `<button>` **composite** (une porte de l'accueil : icône + titre + phrase) n'hérite pas de la
    typographie du bouton d'action ;
  - une action **destructrice** est trouvable sans être dominante : elle ne prend pas l'aplat.
- **Notes** : vérifiée **au navigateur**, écran par écran — c'est ce qui a fait apparaître deux
  défauts qu'aucun test ne pouvait voir : les portes de l'accueil rendues en graisse 800, et
  « Annuler le tournoi » en aplat ambre **écrasant** « Marquer prêt ». La couleur d'une action
  destructrice reste **un trou de la charte** : le choix retenu (ambre en texte et contour, la
  sécurité étant portée par le dialogue d'ADR-0072) est **soumis au commanditaire**.
  **Arbitrage reversé à la revue** : la fusion de `--warn` dans `--danger` avait rendu **identiques**
  cinq paires d'états que le produit distinguait. La charte porte **deux** niveaux d'ambre —
  `--danger` avertit, `--danger-strong` escalade — et c'est cette paire qui rétablit la distinction,
  sans réintroduire de rouge. Quatre boutons **composites** (bandeau repliable, ligne de duel, volée,
  navigateur de volées) avaient aussi hérité de la typographie du bouton d'action : ils déclarent
  désormais `font: inherit`, comme `.coquille__lien` et `.onglet`.
- **Dépend de** : E17US001 · **Jalon** : J1

### E17US003 — Les deux premiers écrans de l'admin se conforment à leur planche
*En tant qu'*organisateur, *je veux* que l'écran de connexion et l'accueil de l'administration ressemblent aux planches validées, *afin de* ne pas ouvrir l'outil sur un formulaire perdu dans un coin d'écran.

- **Contexte** : `A01` retient la variante **A — « formulaire sobre plein cadre »**, `A02` la variante
  **A — « accueil à trois portes »**. Les deux sont 🟡, donc leurs réserves font partie de la cible.
- **CA** :
  - la connexion est une **colonne centrée** (≈ 420 px), pas une carte dans l'angle haut-gauche ;
  - la carte porte un **bandeau de titre** disant ce qu'on y fait, et les champs ont un **libellé
    visible au-dessus** — un `placeholder` disparaît à la première frappe et n'est pas un libellé ;
  - le bouton d'envoi est **pleine largeur** (`.bouton principal` des planches, pas la variante en
    ligne) ;
  - l'échappatoire « Choisir un autre appareil » est **sous** la carte et centrée ;
  - l'accueil des axes s'ouvre sur la **question** de la planche, et l'axe Pilotage dit **sur quoi il
    travaille** quand un tournoi est en cours.
- **Notes** : réserve A01 « sépare le nom de l'appli et l'état serveur dans un header séparé » : **déjà
  satisfaite** avant cette US. Question A01 « le lien de secours est-il utile ? » — réponse « je ne sais
  pas s'il est utile » : **pas une consigne de suppression**, et la planche le conserve ; il reste
  (`ADR-0042` impose une échappatoire). **Non fait** : la pastille d'alerte de complétude sur la liste
  (c'est `E16US010`) et la ligne « 28/30 postes en ligne » de la planche, qui demanderait un agrégat
  que le serveur n'expose pas — on n'affiche que ce que l'écran sait déjà.
- **Dépend de** : E17US002 · **Jalon** : J1

### E17US004 — La supervision passe en grille de tuiles
*En tant qu'*organisateur, *je veux* voir mes trente postes **d'un seul coup d'œil**, *afin de* repérer celui qui s'est tu sans lire trente lignes.

- **Contexte** : `A13` retient la variante **B — « grille de tuiles (30 d'un œil) »** et le verdict est
  **✅ validé tel quel**. Le produit livrait la variante **A**, le tableau — c'est-à-dire le parti pris
  écarté. C'est l'écran du jour J.
- **CA** :
  - les cibles se lisent en **grille de tuiles**, une tuile par cible, sans défilement de tableau ;
  - une tuile porte le **numéro de cible**, la **volée en cours** en forme courte, le **dernier signe
    de vie** et une **jauge d'avancement** ;
  - un poste **muet** se distingue **au cadre**, pas seulement à sa pastille ; son état est écrit
    **en toutes lettres** (`DV-03` : jamais la couleur seule) **et sa tuile conserve le temps écoulé
    depuis le dernier signe de vie** — c'est lui qui distingue « le wifi a sauté » de « la tablette
    est morte », donc lui qui décide du geste. *(Arbitrage reversé à la revue : la première version
    remplaçait le temps par l'état, sur une lecture inexacte de la planche — sa tuile hors ligne
    porte bien les deux.)* ;
  - **rien n'est perdu** de ce que le tableau portait : l'IP de diagnostic (`D-06`) et la révocation
    restent atteignables depuis la tuile ;
  - la jauge a un **équivalent textuel** — sans lui, un lecteur d'écran ne lit qu'une boîte vide.
- **Notes** : `voleeCourte` et `fractionAvancement` sont **pures et testées avant le rendu**, comme le
  reste d'`etat.ts` ; un test vérifie qu'elles ne peuvent pas diverger d'`avancementLibelle` — sinon
  une tuile afficherait une jauge là où le tableau affiche « — », sur le même poste au même instant.
  La fraction est **bornée à 1** : le serveur peut annoncer une volée au-delà de la grille (reprise,
  grille raccourcie), et la jauge déborderait de sa piste. **Vérifié au navigateur** avec 30 postes
  réels, non rattachés ; l'état **rattaché** (jauge + IP + révocation) n'a pas pu être vu faute
  d'appareil connecté — il est couvert par les tests unitaires et la relecture.
- **Dépend de** : E17US002 · **Jalon** : J2 *(écran du jour J)*

---

> **Les six US ci-dessous ont été créées le 08/08/2026**, à la mise en conformité du backlog.
> Elles ne sont pas neuves : ce sont les **capacités que l'épic annonçait déjà** sans qu'aucune US ne
> les porte. Un épic qui promet six capacités et n'en référence aucune se lit comme **terminé** dès
> que ses US cochées le sont — c'est ce qu'`EPIC-14` faisait au même moment.
> ⚠️ **Deux d'entre elles sont bloquées sur un arbitrage du commanditaire** (`E17US005`, `E17US006`) :
> elles sont **spécifiées, pas prenables**. Ne pas les commencer avant la réponse.

### E17US005 — Embarquer la police du club pour le jour J
*En tant qu'*organisateur, *je veux* que les tablettes affichent **la police des maquettes** sans réseau, *afin de* ne pas découvrir le jour J un outil qui ne ressemble plus à celui qui a été validé.

- **Contexte** : `E17US001` a posé la **pile** de polices à l'identique des planches (Inter en tête,
  repli commun), mais **pas le fichier**. Le jour J tourne **sans internet** (contrainte du projet) et
  les tablettes sont **BYOD** : aucune ne chargera Inter depuis un CDN, et rien ne garantit qu'elle
  soit installée. L'application se dégrade donc silencieusement vers `system-ui` — un repli différent
  sur chaque tablette, et différent de la planche.
- ⛔ **Bloquée sur un arbitrage — ajout d'actif, règle 11.** Embarquer une police, c'est ajouter un
  **actif versionné** au dépôt (licence, poids, provenance, mise à jour). C'est un arbitrage de
  l'utilisateur, pas une décision technique : la règle 11 le range avec les ajouts de dépendance.
  **Trois options à lui soumettre**, dans l'ordre de préférence de l'assistant :
  1. **Embarquer Inter en local** (SIL Open Font License 1.1, permissive) — sous-ensemble latin,
     2 graisses (400/800, les seules utilisées par la charte), format `woff2`, `font-display: swap`.
     Coût : ~2 fichiers, quelques dizaines de Ko. Fidélité maximale.
  2. **Assumer le repli système** et **corriger les planches** pour qu'elles utilisent la même pile —
     coût zéro côté produit, mais la charte perd sa typographie et `DV-07` devient sans objet.
  3. **Choisir une police déjà présente** sur les appareils cibles — suppose de connaître le parc,
     ce qui n'est pas le cas en BYOD.
- **CA** *(à écrire une fois l'option retenue — l'énoncer maintenant préjugerait de l'arbitrage)* :
  - l'application affiche la **même police** sur un poste **sans accès réseau et sans la police
    installée** — c'est le seul critère qui distingue vraiment les trois options ;
  - **aucun chargement depuis un domaine externe** : un `@import` vers un CDN est un échec silencieux
    en LAN, exactement le mode de panne que l'US vient fermer ;
  - la licence de tout actif embarqué est **versionnée à côté du fichier** et déclarée dans
    [`docs/dependances.md`](../docs/dependances.md) (règle 11).
- **Notes** : `DV-07` · relève l'unique « non fait » assumé d'`E17US001`. **Piège** : vérifier le
  rendu **avec la police désinstallée du poste de dev**, sinon le test réussit toujours en local —
  c'est la même classe de piège que `crypto.randomUUID`, qui marche en `localhost` et casse en LAN.
- **Dépend de** : E17US001 · **Jalon** : J3

### E17US006 — Donner une couleur à l'action destructrice
*En tant qu'*organisateur, *je veux* qu'une action **irréversible** se distingue d'une **alerte**, *afin de* ne pas confondre « ce poste est hors ligne » et « ce bouton supprime le tournoi ».

- **Contexte** : **trou de la charte**, relevé par `E17US001` puis reconfirmé par `E17US002`. `DV-03`
  **exclut le rouge** comme couleur d'alerte (il ne signale rien sur l'anthracite) et la charte
  mesurée ne prévoit **rien** pour le cas destructeur. Le produit utilise donc l'ambre par défaut —
  la **même teinte** que « poste hors ligne » et que l'avertissement. `E17US002` a atténué le
  symptôme (l'action destructrice ne prend plus l'aplat, la sécurité passe par le dialogue
  d'[ADR-0072](../docs/adr/0072-confirmation-des-actions-irreversibles.md)) sans traiter la cause.
- ⛔ **Bloquée sur un arbitrage — trou de charte.** Ce n'est **pas** une US d'écran : la palette ne se
  discute pas en US (`EPIC-17` § Exclus), elle se décide **en ADR** contre la charte mesurée, avec les
  ratios de contraste. Options à soumettre : (a) une **troisième teinte** entrant à la charte, avec
  son ratio mesuré en thème clair **et** sombre ; (b) **deux niveaux d'ambre** — c'est ce que
  `E17US002` a déjà posé (`--danger` avertit, `--danger-strong` escalade) : l'acter suffirait, et
  l'US se réduirait à documenter ; (c) **aucune couleur propre** — le destructeur se signale par la
  **forme** et le dialogue seuls, la couleur n'y jouant aucun rôle.
- **CA** *(à écrire après l'arbitrage)* :
  - une action **irréversible** et un **avertissement** ne partagent pas leur signalement ;
  - le signalement ne repose **jamais sur la couleur seule** (`DV-03`) ;
  - tout jeton ajouté porte son **ratio de contraste mesuré** en commentaire, dans **les deux
    thèmes** — un jeton défini dans un seul thème est une faute de contraste silencieuse (CA
    d'`E17US001`).
- **Notes** : `DV-03` · [ADR-0074](../docs/adr/0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md) ·
  ADR attendu. **Ne pas la traiter en passant** dans une US d'écran : c'est ainsi que le trou s'est
  creusé (deux US l'ont signalé sans pouvoir le fermer).
- **Dépend de** : E17US002 · **Jalon** : J3

### E17US007 — Résorber les écarts relevés sur les écrans d'administration
*En tant qu'*organisateur, *je veux* que les écrans d'administration ressemblent aux **variantes que j'ai retenues**, *afin de* ne pas travailler sur des partis pris que j'avais écartés.

- **Contexte** : le **relevé d'écarts des planches admin est fait** (06/08/2026, dans
  [`EPIC-17`](../epics/EPIC-17-fidelite-aux-maquettes.md)) ; `E17US003` et `E17US004` en ont traité
  trois écrans (A01, A02, A13). **Le reste du relevé n'a aucune US.** Un relevé sans US de résorption
  se périme sur place : les planches vieillissent pendant qu'on les relit (risque déjà réalisé sur A15).
- **CA** :
  - **A06 · référentiels** passe au **panneau latéral d'édition** (variante **B** retenue) —
    aujourd'hui `Blasons.tsx` bascule **tout l'écran** en formulaire ;
  - **A09 · inscriptions** passe à **recherche d'abord, liste ensuite** (variante **B** retenue), avec
    les compteurs d'entrée de la planche (inscrits, non placés, non réglés, doublons) ;
  - **A12 · postes**, **A08 · scoreurs** et **A04 · tournois** présentent leurs données en
    **carte-tableau à colonnes nommées**, celles de la planche, sans cesser d'être des `<table>`
    (CA d'`E17US002` : l'apparence, pas le balisage) ;
  - **A17 · paiements** gagne son **bandeau de totaux** (attendu / encaissé / restant dû / archers
    concernés) et l'**ancienneté** de la dette ; l'export trésorier **relève d'`E16US007`** et n'est
    pas traité ici ;
  - une colonne de planche qui **suppose une donnée que l'écran ne va pas chercher** (A04 :
    avancement, ce qui reste) est soit **alimentée**, soit **retirée de la planche** — jamais affichée
    vide. Le choix se fait par colonne et s'écrit.
- **Notes** : ⚠️ **à redécouper si le relevé grossit** — six écrans dans une branche est le plafond.
  **Ne pas traiter** ce qui est marqué « recoupe `E16Uxxx` » dans le relevé (A15 → `E16US008`,
  A18 → `E16US007`, A11 → `E16US005`) : l'US E16 porte le besoin, E17 n'ajoute que l'exigence de
  ressemblance, et le faire deux fois produit deux variantes. **A05 · identité** est hors périmètre
  tant qu'`E01US016` est ⬜ — l'écran n'existe pas. **A07 · phases** est hors périmètre
  définitivement (« à refaire », aucune variante retenue) : c'est `E16US002`.
- **Dépend de** : E17US002 · **Jalon** : J3

### E17US008 — Confronter les écrans de saisie à leurs planches
*En tant que* scoreur, *je veux* que le pavé de saisie et l'écran de duel ressemblent à ce qui a été validé, *afin de* retrouver à 3 m d'une cible les repères vus sur la maquette.

- **Contexte** : les **9 planches `S**`** (rattachement, poste de cible, pavé de saisie, marqueur,
  saisie de duel, routage, file scoreur, validation de cible, états système) **n'ont jamais été
  confrontées** aux écrans livrés. Seul l'axe admin l'a été.
- **CA** :
  - un **relevé d'écarts** est produit pour les 9 planches, selon la méthode de l'épic —
    **questionnaire → variante retenue → écran livré**, jamais la première variante venue (le piège
    documenté sur A00, où s'aligner sur la planche aurait défait un écran validé) ;
  - les écarts de **structure** (zones, hiérarchie, formes) sont résorbés ; les écarts de **densité**
    ne le sont pas — le produit est volontairement plus aéré, c'est la planche qui est en retard (CA
    d'épic) ;
  - ⚠️ **là où fidélité et usage s'opposent, l'usage gagne et la planche est corrigée.** C'est l'axe
    où ce risque est réel : une planche se juge à l'arrêt, un pavé de saisie se juge **une flèche à la
    main**. Tout arbitrage de ce type est **écrit** dans la planche, pas seulement appliqué.
- **Notes** : `S09 · états système` est la planche à lire en premier — elle fixe le vocabulaire
  visuel des états que les huit autres réemploient. **Recoupe `E16US011`**, dont l'une des deux
  contradictions à arbitrer porte sur `S08` (validation de cible) **contre un endpoint vivant** :
  l'attendre plutôt que de trancher ici.
- **Dépend de** : E17US002 · **Jalon** : J3

### E17US009 — Confronter les écrans publics et l'écran de salle à leurs planches
*En tant que* spectateur, *je veux* que les écrans publics ressemblent à ce qui a été montré au club, *afin de* retrouver l'information là où on me l'a annoncée.

- **Contexte** : les **7 planches `P**`** (« c'est moi », ma journée, classements, plan de cibles,
  tableau de duels, salle-affectations, salle-classement/podium) n'ont pas été confrontées. Deux
  d'entre elles ont bougé récemment côté produit — `P03` par `E16US004` (interrupteur unique
  « mes archers / tout ») et les vues de salle par `E07US004`/`E07US005`.
- **CA** :
  - un **relevé d'écarts** est produit pour les 7 planches, même méthode ;
  - les écarts de structure sont résorbés, **sauf** là où un arbitrage du commanditaire postérieur à
    la planche l'emporte (**réserve 2 d'ADR-0074**) — précédent posé deux fois : A14 par `E16US003`,
    P03 par `E16US004`. Ces deux-là sont donc **hors périmètre de résorption** : la planche y est en
    retard sur la décision, et c'est **la planche** qui est corrigée ;
  - l'**écran de salle** (`P06`, `P07`) se juge à sa **distance d'usage** — vidéoprojecteur 1920 × 1080
    lu à plusieurs mètres —, pas au navigateur du poste de dev.
- **Notes** : ⚠️ **`P03` a été redessinée le 05/08 et n'a pas été validée** (pas de tour 2) ; elle est
  écartée pour la même raison qu'A14. Ne pas rouvrir l'arbitrage d'`E16US004`.
- **Dépend de** : E17US002 · **Jalon** : J3

### E17US010 — Empêcher le dossier de maquettes de dériver du produit
*En tant que* développeur, *je veux* que la navigation des planches suive **automatiquement** celle du produit, *afin de* ne pas relire des maquettes qui décrivent une application qui n'existe plus.

- **Contexte** : [`maquettes/assets/appareils.js`](../maquettes/assets/appareils.js) **transcrit**
  l'ossature des trois axes depuis `axes.ts` (30 destinations) — c'était déjà un progrès sur la
  recopie à la main. Mais la transcription est **manuelle** : chaque US qui renomme ou déplace une
  destination la désynchronise, en silence. L'épic inscrit la resynchronisation à son périmètre sans
  qu'aucune US ne la porte, donc elle ne se fait qu'à la faveur d'un autre travail.
- **CA** :
  - `appareils.js` est **resynchronisé** sur `axes.ts` — écart nul au moment de la livraison ;
  - la dérive est **détectable mécaniquement** : un contrôle rend rouge un dossier de maquettes qui
    décrit une destination absente d'`axes.ts`, ou qui en oublie une. Sans ce contrôle, l'US ne fait
    que remettre le compteur à zéro et le problème revient à l'US suivante ;
  - le contrôle **n'ajoute pas de dépendance** (règle 11) et **ne bloque pas** sur une divergence
    volontaire : une planche peut légitimement décrire une destination **à venir**, à condition de le
    déclarer.
- **Notes** : ⚠️ **arbitrage technique laissé à l'implémenteur** — contrôle en pre-commit, en CI, ou
  test front. Préférence de l'assistant : **test front** (`maquettes/` n'est pas du code de
  production, et la CI front tourne déjà), mais c'est à trancher devant le code. **Précédent utile** :
  `test_domain_isolation.py` et `test_portee_sportive.py` sont les deux garde-fous mécaniques
  existants du projet — s'en inspirer plutôt qu'inventer une forme neuve.
  Ce n'est **pas** une US de fidélité visuelle : elle protège l'**outil** de relecture, sans quoi
  toutes les autres E17 se font sur une base fausse. À prendre **avant** `E17US008` et `E17US009`,
  qui vont relire 16 planches.
- **Dépend de** : — · **Jalon** : J3
