# EPIC-17 — Fidélité de l'application aux maquettes — User Stories

> Voir [`epics/EPIC-17`](../epics/EPIC-17-fidelite-aux-maquettes.md) et
> [ADR-0074](../docs/adr/0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md).
>
> **Ne pas confondre avec [`E16`](E16-retours-maquettes.md)** : E16 traite ce que le commanditaire
> reproche **aux maquettes** ; E17 amène **le produit** jusqu'à elles. Une US qui change ce que
> montre un écran est une E16 ; une US qui change **la ressemblance** entre l'écran et sa planche est
> une E17.
>
> **La source du CA tient en deux moitiés, et les confondre est le piège de cet épic.** La **forme**
> s'étalonne sur la planche et la charte mesurée : un écart se constate en superposant
> `maquettes/<code>-<slug>.html` et l'écran livré. Mais **quelle variante** de la planche fait foi se
> lit au **questionnaire** — par le libellé coché et le « pourquoi » écrit, **jamais par la lettre**
> ([ADR-0113](../docs/adr/0113-un-arbitrage-se-lit-par-l-intention-pas-par-la-lettre.md)).
>
> ⚠️ **Les questionnaires ont été remplis le 04/08 sur les vignettes, les planches redessinées le
> 05/08 en écrans pleins.** Les lettres n'ont pas suivi. **Vérifier la correspondance avant de
> mesurer un écart** — sur l'axe saisie, `S01` avait ses lettres **inversées**. Quand l'intention ne
> se traduit plus, il n'y a **pas d'étalon** : on ne résorbe pas le parti pris, on repose la question.
> *(Reversé ici en revue d'`E17US008` : ce préambule disait « la source du CA est la planche, **pas
> un questionnaire** » — l'inverse de l'arbitrage, et il gouverne les neuf US, dont `E17US009`.)*

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
> ⚠️ **Deux d'entre elles étaient bloquées sur un arbitrage du commanditaire** (`E17US005`, `E17US006`) :
> spécifiées, pas prenables avant la réponse. `E17US006` a été tranchée le 26/09/2026 (ADR-0114).

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
- **Contraintes valables quelle que soit l'option retenue** *(le CA complet s'écrit après l'arbitrage ; celles-ci, elles, tiennent dans les trois branches — ce ne sont pas des provisoires à ignorer)* :
  - l'application affiche la **même police** sur un poste **sans accès réseau et sans la police
    installée** — c'est le seul critère qui distingue vraiment les trois options ;
  - **aucun chargement depuis un domaine externe** : un `@import` vers un CDN est un échec silencieux
    en LAN, exactement le mode de panne que l'US vient fermer ;
  - la licence de tout actif embarqué est **versionnée à côté du fichier** et déclarée dans
    [`docs/dependances.md`](../docs/dependances.md) (règle 11).
- **Notes** : `DV-07` · **résorbe [DETTE-043](../docs/dette.md)** (la charte impose Inter, l'application ne l'embarque pas) · relève l'unique « non fait » assumé d'`E17US001`. **Piège** : vérifier le
  rendu **avec la police désinstallée du poste de dev**, sinon le test réussit toujours en local —
  c'est la même classe de piège que `crypto.randomUUID`, qui marche en `localhost` et casse en LAN.
- **Dépend de** : E17US001 · **Jalon** : J3

### E17US006 — Distinguer l'action destructrice de l'alerte
*En tant qu'*organisateur, *je veux* qu'une action **irréversible** se distingue d'une **alerte**, *afin de* ne pas confondre « ce poste est hors ligne » et « ce bouton supprime le tournoi ».

- **Contexte** : **trou de la charte**, relevé par `E17US001` puis reconfirmé par `E17US002`. `DV-03`
  **exclut le rouge** comme couleur d'alerte (il ne signale rien sur l'anthracite) et la charte
  mesurée ne prévoit **rien** pour le cas destructeur. Le produit utilise donc l'ambre par défaut —
  la **même teinte** que « poste hors ligne » et que l'avertissement. `E17US002` a atténué le
  symptôme (l'action destructrice ne prend plus l'aplat, la sécurité passe par le dialogue
  d'[ADR-0072](../docs/adr/0072-confirmation-destructrice-dialog-natif.md)) sans traiter la cause.
- **Arbitrage tranché le 26/09/2026 — option (c), aucune couleur propre** ([ADR-0114](../docs/adr/0114-l-action-destructrice-se-signale-par-la-forme-pas-par-la-couleur.md)).
  Trois options avaient été soumises : (a) une **troisième teinte** entrant à la charte ; (b) **deux
  niveaux d'ambre** (`--danger` avertit, `--danger-strong` escalade, déjà posé par `E17US002`) ;
  (c) **aucune couleur propre** — le destructeur se signale par la **forme** et le dialogue seuls.
  Le commanditaire a retenu (c) : l'ambre reste **réservé à l'alerte**. (b) a été écartée parce que
  deux ambres restent une même famille de teinte — l'irréversible et l'avertissement auraient
  continué de partager leur signal.
- **CA — l'action destructrice ne porte aucune couleur d'état** : le bouton destructeur
  (`.bouton--danger`), le dialogue de confirmation destructeur (`.dialogue--danger`) et le panneau
  d'impact d'une action massive (`.confirmation`, `ConfirmationChiffree`) ne référencent **aucun** jeton
  d'état (`--danger`, `--danger-strong`, `--success`, `--info`) ni la marque. ⚠️ Le panneau d'impact
  est rangé **côté destructeur**, pas côté alerte : il annonce le coût d'une action irréversible, il
  fait partie de sa confirmation au même titre que le dialogue.
- **CA — l'action destructrice se reconnaît à sa forme** : le bouton destructeur est le seul bouton à
  **contour épais** (2 px) **en encre neutre** (`--text`), sans aplat — distinct de l'action principale
  (aplat de marque) comme du bouton discret (contour fin `--border`, texte secondaire) ; le dialogue
  destructeur garde son **filet haut** (4 px), en encre neutre. La sécurité reste portée par le
  dialogue d'[ADR-0072](../docs/adr/0072-confirmation-destructrice-dialog-natif.md) (« Annuler » prend
  le focus) — inchangé.
- **CA — les jetons d'alerte portent leur ratio dans chaque déclinaison** : `--danger` et
  `--danger-strong` portent leur ratio de contraste mesuré en commentaire dans le thème sombre, le
  thème clair **et** la déclinaison claire de « Système » (`--danger-strong` clair n'en portait pas :
  6,78:1).
- **Contraintes de départ, tenues par (c)** : une action **irréversible** et un **avertissement** ne
  partagent pas leur signalement ; le signalement ne repose **jamais sur la couleur seule** (`DV-03`) ;
  aucun jeton n'est ajouté (donc aucun ratio neuf à mesurer).
- **Notes** : `DV-03` · [ADR-0074](../docs/adr/0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md)
  (amendé par ADR-0114). ⚠️ **Piège de nommage laissé en place — `DETTE-115`** : la classe
  s'appelle toujours `bouton--danger` (et la prop `ton="danger"`) alors qu'elle ne porte plus le jeton
  `--danger` ; le renommage attend qu'aucune branche en vol ne touche ses 22 fichiers. Le test de
  charte empêche d'y remettre l'ambre.
- **Dépend de** : E17US002 · **Jalon** : J3

### E17US007 — Résorber les écarts relevés sur les écrans d'administration
*En tant qu'*organisateur, *je veux* que les écrans d'administration ressemblent aux **variantes que j'ai retenues**, *afin de* ne pas travailler sur des partis pris que j'avais écartés.

- **Contexte** : le **relevé d'écarts des planches admin est fait** (06/08/2026, dans
  [`EPIC-17`](../epics/EPIC-17-fidelite-aux-maquettes.md)) ; `E17US003` et `E17US004` en ont traité
  trois écrans (A01, A02, A13). **Le reste du relevé n'a aucune US.** Un relevé sans US de résorption
  se périme sur place : les planches vieillissent pendant qu'on les relit (risque déjà réalisé sur A15).
- **CA** *(rétréci le 25/09/2026 sur arbitrage du commanditaire : les deux écrans 🔴 ici, les
  quatre 🟠 en [`E17US012`](#e17us012--les-écrans-dadministration-en-carte-tableau))* :
  - **A06 · référentiels** passe au **panneau latéral d'édition** (variante « **panneau latéral d'édition** » retenue) —
    aujourd'hui `Blasons.tsx` bascule **tout l'écran** en formulaire ;
  - **A09 · inscriptions** passe à **recherche d'abord, liste ensuite** (variante « **recherche d'abord, liste ensuite** » retenue), avec
    les compteurs d'entrée de la planche (inscrits, non placés, non réglés, doublons) ;
  - une colonne de planche qui **suppose une donnée que l'écran ne va pas chercher** est soit
    **alimentée**, soit **retirée de la planche** — jamais affichée vide. Le choix se fait par
    colonne et s'écrit.
- **Notes** : ⚠️ **Vérifier la correspondance questionnaire ↔ planche AVANT de mesurer** — les
  lettres `A**` sont aussi peu fiables que les `S**` (le redessin du 05/08 a porté sur les 36
  planches), et un CA est la **source d'un test** : dériver d'une lettre, c'est dériver de rien
  ([ADR-0113](../docs/adr/0113-un-arbitrage-se-lit-par-l-intention-pas-par-la-lettre.md)).
  ⚠️ **à redécouper si le relevé grossit** — six écrans dans une branche est le plafond.
  **Ne pas traiter** ce qui est marqué « recoupe `E16Uxxx` » dans le relevé (A15 → `E16US008`,
  A18 → `E16US007`, A11 → `E16US005`) : l'US E16 porte le besoin, E17 n'ajoute que l'exigence de
  ressemblance, et le faire deux fois produit deux variantes. **A05 · identité** est hors périmètre
  tant qu'`E01US016` est ⬜ — l'écran n'existe pas. **A07 · phases** est hors périmètre
  définitivement (« à refaire », aucune variante retenue) : c'est `E16US002`.
- **Notes (livraison, 25/09/2026)** — livrée dans la PR d'`E17US009`/`E17US011` (demande du
  commanditaire). Correspondance vérifiée d'abord (ADR-0113) : **les six écrans ont un étalon** —
  le libellé coché se retrouve dans une variante de la planche actuelle, aucune lettre n'a glissé.
  Arbitrages tranchés en cours d'US, reversés ici :
  - **A06** — la liste est un `<table>` groupé par **origine** (`<tbody>` + `th scope="rowgroup"`),
    « **Référentiel FFTA** » puis « **Créés par l'organisation** » : c'est la réserve du 04/08
    (« séparer les unités officielles FFTA de celles créées par l'admin »). ⚠️ Jamais
    « officiels » : l'origine dit la **provenance**, pas la conformité (ADR-0060 §4). La
    suppression passe **dans le panneau**, avec sa confirmation. Les colonnes **diamètre,
    distances, emploi** de la planche n'existent pas au modèle : **retirées de la planche**.
  - **A09** — sans recherche ni compteur choisi, **rien n'est listé** (sinon c'est la variante A,
    écartée). Les compteurs sont des **filtres** (bascule, `aria-pressed`) ; « **Non placés** » =
    sans cible — en **réserve** sur au moins un départ, **ou posé sur aucune cible d'aucun plan**,
    ce qui couvre l'archer inscrit au tournoi mais à **aucun départ** (celui qu'on a oublié) ; sans
    gabarit de salle, **tous** les inscrits. *(Corrigé en revue, axes B, C1, D : la 1ʳᵉ rédaction
    ne comptait que la réserve et affirmait à tort que « le plan persisté y range tout inscrit » —
    vrai des seuls inscrits à un départ.)* « Non réglés » = reste dû > 0. Une population illisible
    s'affiche « ? », **jamais 0** — les **doublons** compris. Le premier compteur garde le libellé
    de la planche, **accordé** : « Voir les N inscrits », « Voir l'inscrit » pour un seul. Une fiche
    ouverte par l'adresse (recherche transverse, E16US010) **reste listée** — sans quoi le
    résultat cliqué ne mènerait nulle part. La phrase « N rapprochements de fiches » est
    **remplacée** par le compteur « Doublons », qui la chiffre et filtre en plus.
  - ⚠️ **Les deux populations sont lues par un conteneur de l'admin (`InscriptionsAdmin`)**, pas
    par l'écran : les lire dans `archers` le faisait dépendre de `placement` et `paiements`, qui
    dépendent déjà de lui — l'atlas a mesuré le plus gros nœud d'enchevêtrement passant de **24 à
    29** features. Remis à 24 par ce détour.
  - **Non fait** : le bloc « Derniers gestes sur ce poste » de la planche B — absent du CA, il
    suppose un historique local qui n'existe pas. **Non vérifié au navigateur** : le navigateur
    piloté affichait une page d'erreur sur l'admin alors que le serveur répondait 200 — le contrôle
    visuel d'A06 et d'A09 reste à faire.
  - `DETTE-103` **aggravée** (4ᵉ copie du repli casse + accents). *(Ouverte d'abord sous un
    numéro neuf, `DETTE-114`, qui la doublait avec un constat faux — fusionnée en revue.)*
- **Dépend de** : E17US002 · **Jalon** : J3

### E17US012 — Les écrans d'administration en carte-tableau
*En tant qu'*organisateur, *je veux* que les listes de l'administration aient les colonnes nommées des planches, *afin de* lire tournois, scoreurs, postes et paiements comme je les ai validés.

- **Contexte** : fille d'`E17US007`, découpée le 25/09/2026 (arbitrage du commanditaire) — les
  quatre écarts 🟠 du relevé admin. Les étalons ont été **vérifiés** à ce moment (ADR-0113) :
  A04 « A — liste dense avec statut », A08 « A — liste simple avec état de connexion », A12
  « A — liste des postes avec dernier signe de vie », A17 « A — liste des dus » (✅).
- **CA** *(repris d'`E17US007`, inchangés)* :
  - **A12 · postes**, **A08 · scoreurs** et **A04 · tournois** présentent leurs données en
    **carte-tableau à colonnes nommées**, celles de la planche, sans cesser d'être des `<table>`
    (CA d'`E17US002` : l'apparence, pas le balisage) ;
  - **A17 · paiements** gagne son **bandeau de totaux** (attendu / encaissé / restant dû / archers
    concernés) et l'**ancienneté** de la dette ; l'export trésorier **relève d'`E16US007`** ;
  - une colonne de planche qui **suppose une donnée que l'écran ne va pas chercher** (A04 :
    avancement, ce qui reste — **absents** de `TournoiReponse`) est soit **alimentée**, soit
    **retirée de la planche** — jamais affichée vide. Le choix se fait par colonne et s'écrit.
    **Tranché au cadrage du 26/09/2026** : A04 **avancement** et **ce qui reste** sont **retirés
    de la planche** — l'accueil d'un tournoi (A03, `FriseCycleDeVie`) situe déjà le tournoi dans
    son cycle, et les alimenter ferait calculer un avancement par tournoi pour une liste.
    **Règle retenue pour les autres colonnes** : alimentées si la donnée **existe en base et se lit
    simplement**, retirées si elles supposent un **concept neuf** ou une jointure fragile —
    - **A04** : **INSCRITS** (les **archers du tournoi**, inscrits à un créneau ou non — le même
      compte que « Voir les N inscrits » d'A09) et **CIBLES** alimentées ; liste classée **par
      statut, puis par date** ;
    - **A08** : **retirées de la planche** — **PÉRIMÈTRE** (un scoreur n'a aucun périmètre au
      modèle), **ÉTAT** (la session scoreur n'expire pas et n'émet aucun signe de vie : on sait
      qu'elle a été *ouverte*, jamais qu'elle est *en ligne* — l'afficher mentirait) et **DERNIÈRE
      VALIDATION** (le journal d'audit ne connaît le scoreur que par son **nom**, homonymes
      compris) ; chaque ligne ouvre son QR et son code ;
    - **A12** : le tableau est l'écran **Postes** (préparation des codes), une ligne par poste,
      QR à la ligne ; rattachement, appareil et signe de vie restent à la **supervision** (A13,
      tuiles retenues), qui porte déjà le bandeau par type d'écran. **Régénérer un jeton,
      Détacher, Réactiver** n'existent ni au front ni au serveur : capacités neuves, **hors
      fidélité**, portées au tracker comme besoin sans porteur ;
    - **A17** : **CLUB**, **CAT.** et **TARIF** alimentées ; l'**ancienneté** est alimentée par
      une **date d'inscription** neuve (migration) — la dette date de la **plus ancienne
      inscription non réglée** ; une inscription antérieure à la migration n'a **pas** de date et
      s'affiche « date inconnue », jamais une case vide.
- **Notes** : ⚠️ **A04, A08 et A17 ont bougé depuis le relevé du 06/08** (`E01US026`,
  `E16US015`) : **re-mesurer**, ne pas se fier au relevé. Les évolutions écrites au questionnaire
  font partie de la cible — A08 et A12 : « chaque ligne doit ouvrir le QR et le code de
  raccrochement » ; A04 : classer par statut puis date ; A12 : bandeau repliable par type d'écran.
- **Notes (livraison, 26/09/2026)** — re-mesuré avant de coder : A04 était une liste `<ul>`,
  A08 et A12 aussi, A17 avait déjà son `<table>` mais pas les colonnes de la planche. Deux des
  évolutions du questionnaire étaient **déjà livrées** : le tri « statut puis date » d'A04
  (`tournois/tri.ts`) et le bandeau repliable par type d'écran d'A12 (à la **supervision**). Tranché
  en cours d'US, en plus de l'arbitrage de cadrage ci-dessus :
  - **A12 · TYPE retiré** : l'écran Postes ne liste que les écrans de **cible** (`PosteAdmin` porte
    `cible_index`) — la colonne vaudrait toujours la même chose. Le **jeton** de la planche est le
    **code** imprimé sous le QR : l'en-tête garde le mot du produit, « Code ».
  - **A17 · TARIF / DÛ** : TARIF = ce que l'archer devait en tout (`du_centimes`), DÛ = ce qu'il doit
    encore, avec son statut. PAYÉ s'en déduit, la planche ne le montre pas. « Sans dette » s'écrit
    « — » dans DEPUIS ; un archer sans club, « sans club ».
  - **A17 · un montant nul n'est pas « Gratuit »** : `decrireTarif(0)` rendait « Gratuit » sur un
    reste réglé — y compris dans la vue par club, **avant** cette US. `decrireMontant` porte les
    montants, `decrireTarif` reste aux tarifs.
  - **A17 · « aucun créneau »** : un archer du tournoi inscrit à **aucun** créneau doit 0, comme
    un créneau gratuit — TARIF affiche « aucun créneau », pas « Gratuit » (`nb_inscriptions`).
    **« Encaissé »** = ce qui est payé sur les inscriptions **en cours** ; l'argent d'une inscription
    retirée vit dans l'onglet « Remboursements », hors du bandeau. *(Relevés en revue, axes B, C1,
    D.)*
  - **A04 · porte publique** : la même liste sert l'accueil public (`lectureSeule`). INSCRITS et
    CIBLES y sont **masquées** — colonnes d'administration ; le public garde État · Nom · Date.
  - **Fusion d'archers** : l'inscription qui reste sur un créneau commun garde la **plus
    ancienne** date, « inconnue » l'emportant (`date_fusionnee`) — sans quoi une fusion rajeunissait
    une dette. *(Relevé en revue, axe D.)*
  - Les **planches** A04, A08 et A12 sont corrigées (colonnes retirées, verdict « colonnes retirées
    par E17US012 ») ; A17 n'en perd aucune. Ses encarts « par moyen de paiement » ne sont pas au CA et
    ne sont **pas** faits — l'application ne connaît pas le moyen de paiement.
- **Dépend de** : E17US007 · **Jalon** : J3

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
- **Notes** : ⚠️ **US à deux temps — à redécouper dès que le relevé est produit.** Le second temps
  (« les écarts sont résorbés ») n'a **pas de périmètre borné** tant que le relevé n'existe pas : on
  ne peut donc pas en dériver de test au moment de brancher. Même plafond qu'`E17US007` — **six
  écrans dans une branche**, et ici il y en a neuf : le redécoupage est la règle, pas l'exception.
  `S09 · états système` est la planche à lire en premier — elle fixe le vocabulaire
  visuel des états que les huit autres réemploient.
- **Notes (livraison, 24/09/2026)** — le relevé des 9 planches est dans
  [`EPIC-17`](../epics/EPIC-17-fidelite-aux-maquettes.md) ; **cinq écrans résorbés** (`S01`, `S02`,
  `S03`, `S04`, `S09`), sous le plafond. Quatre arbitrages tranchés en cours d'US, reversés ici :
  - ✅ ~~**Recoupe `E16US011`** … l'attendre plutôt que de trancher ici~~ — **note périmée, levée.**
    `E16US011` a été **close par découpage** le 10/09/2026 : `S08` est parti en `E16US019` (✅
    11/09) et `S09` en `E16US020` (✅ 12/09, [ADR-0107](../docs/adr/0107-une-ecriture-concurrente-est-arbitree-par-le-role-de-qui-ecrit.md)).
    Il n'y avait donc plus rien à attendre, et la contradiction annoncée « contre un endpoint
    vivant » avait elle-même été **requalifiée** (elle était à moitié fausse). ⚠️ Une note de
    blocage qui survit à la levée de son blocage coûte une US : celle-ci a failli reporter l'axe.
  - ⚠️ **Le CA « questionnaire → variante retenue » n'est pas applicable tel quel sur cet axe** — tranché en [ADR-0113](../docs/adr/0113-un-arbitrage-se-lit-par-l-intention-pas-par-la-lettre.md). Les
    questionnaires ont été remplis le 04/08 sur les **vignettes**, les planches redessinées le 05/08
    en écrans pleins : **4 planches sur 9** ne proposent plus la variante qui a été retenue (`S01`, `S04`, `S06`, `S08` ; `S05` n'en avait aucune), et
    sur `S01` les lettres sont **inversées**. La variante retenue se lit donc **par l'intention**,
    jamais par la lettre — tableau de correspondance dans le relevé. **Ne pas citer une lettre de
    questionnaire dans le code** : `EspacePoste.tsx` en portait une (« variante B »), corrigée.
  - **`S04`, `S05` et `S08` n'ont plus d'étalon** et sont **exclues de toute résorption de
    fidélité** — s'y aligner serait deviner. Le geste qui referme cela est **du temps du
    commanditaire** : remplir le tour 2 des questionnaires `S**` sur les écrans pleins. Porté au
    tracker, pas ici.
  - **Le bandeau hors-ligne de `S09` n'est monté que sur la tablette de cible.** La promesse « la
    saisie continue » n'est vraie que là où une file absorbe l'écriture : sur le PC d'organisation
    et le public, une écriture pendant la coupure **échoue**. Le **scoreur** est exclu pour une
    autre raison — sa file existe, mais `etatIndicateur` ne la compte pas (`DETTE-112`), et son
    écran de duels porte déjà son propre indicateur d'attente. ⚠️ **Ne pas le relever comme écart de
    fidélité en `E17US009`** : c'est un arbitrage, pas un oubli.
  - **`S07 · file scoreur` n'a aucun écran ni endpoint.** Ce n'est pas un écart de fidélité mais une
    **US non livrée** (comme A05 sur l'axe admin). ⚠️ Le tri d'`E16US011` le rangeait parmi les
    « validés, rien à faire » : son verdict « ✅ validé tel quel — **on peut coder ça** » est un feu
    vert, pas un constat de livraison. **Reste sans destinataire**, comme la critique de `S05`.
- **Dépend de** : E17US002 · **Jalon** : J3

### E17US011 — La ligne d'archer porte la volée en cours
*En tant que* marqueur, *je veux* saisir en touchant la flèche que je remplis, *afin de* ne pas chercher où taper entre deux volées.

- **Contexte** : sorti du relevé de l'axe saisie (`E17US008`, 24/09/2026), **seul écart 🔴 laissé
  ouvert**. La planche `S02` fait de la ligne d'archer la **zone de saisie** — `pos | nom | fl fl fl
  | somme`, la case en cours marquée. Le produit en fait un **bouton d'ouverture** : la ligne ne
  porte qu'avancement, cumul et relecture des volées closes.
- **CA** :
  - la ligne d'archer affiche les **trois flèches de la volée en cours**, dont celle en train d'être
    saisie, et la **somme** de cette volée — la structure de la planche ;
  - **toucher une case de flèche** ouvre le pavé sur cette flèche : c'est la réserve écrite deux
    fois au questionnaire `S02` (*« l'appel du pavé doit se faire à la sélection de la zone de
    saisie »*), dont `E17US008` n'a tenu que la moitié (le pavé est appelé, mais par l'archer) ;
  - le pavé, n'ayant plus à porter seul la volée, **rend sa colonne** : la grille reprend la largeur
    de la tablette (S02 : « les lignes d'archer font toute la largeur ») et les touches peuvent
    atteindre les **90 px** de S03. Les deux écarts 🟠 laissés par `E17US008` se ferment ici.
- **CA — `DETTE-111` est résorbée pour la conversion « zone → points »** *(arbitrage du commanditaire, 24/09/2026)* : la
  conversion « zone de blason → points » est écrite **deux fois**, en Python (`_points_zone`, privé)
  et en TypeScript (`pointsZone`). Le barème gagne un **`points_par_zone`** ; `_points_zone` devient
  public et domicile unique ; `pointsZone` devient une **lecture de table**. ⚠️ **Ne pas appliquer le
  remède de `DETTE-020`** (servir la valeur par le DTO et retirer le calcul du front) : le poste doit
  valoriser des volées **hors ligne** que le serveur n'a jamais reçues — `serieOptimiste` conserve le
  `cumul` serveur, qui les ignore. On sert la **règle**, pas le **résultat**. Cette US est le bon
  porteur parce qu'elle rouvre déjà `volees.ts`, la ligne d'archer et le pavé, avec leurs tests.
  ⚠️ **La seconde moitié de `DETTE-111` reste ouverte** : « quelles volées comptent dans un total »
  est posé unilatéralement côté front et n'a **aucun domicile au domaine**. `points_par_zone` ne
  transporte que la valeur d'une zone. Ne pas cocher la dette comme résorbée.
- **Notes** : ⚠️ **Ce qu'il faut tenir, c'est l'archer actif — pas un tampon de frappe.** La bande de
  relecture est **hors** du bouton de ligne parce que la toucher **changerait d'archer** : le
  `onClick` de la ligne est `setArcherChoisi`. Des cases de flèche tapables doivent donc **arrêter la
  propagation**, sous peine de faire basculer l'archer à chaque saisie.
  ⚠️ **Ne pas reprendre le motif historique** : « cela démontait `PaveArcher` avec son tampon de
  frappe » a été vrai jusqu'au jour où les brouillons ont été **remontés dans `Saisie`** — ce qui,
  dit le commentaire de `Saisie.tsx`, « supprime la classe entière de défauts ». `E17US008` avait
  différé cette US **au nom de cet invariant mort** ; l'axe adversarial l'a relevé. Le test ne se
  dérive **pas** de là : il se dérive de la planche `S02` (la ligne est `pos | nom | fl fl fl |
  somme`) et de la réserve écrite deux fois au questionnaire.
- **Notes (livraison, 25/09/2026)** — livrée dans la même PR qu'`E17US009` (demande du
  commanditaire). Arbitrages tranchés en cours d'US, reversés ici :
  - **La ligne montre la volée « prochaine à saisir »**, brouillon compris — la même que le pavé
    ouvrirait. Toucher une case **désigne l'archer et vise la flèche** : une case remplie est
    **remplacée** à la frappe suivante (c'est ce qui rend une volée pleine corrigeable avant
    envoi) ; une case vide ne crée pas de trou, la frappe reprend à la suite (`frapper`,
    `flecheVisee`). Les cases sont des boutons **voisins** du bouton de ligne, pas imbriqués : la
    propagation ne peut pas atteindre `setArcherChoisi` par construction.
  - ⚠️ **« Le pavé rend sa colonne » réintroduisait le défaut qu'`E17US008` avait corrigé** :
    empilé, ses touches tombaient à **826 px sur une fenêtre de 641** (mesuré). Le pavé est donc
    **ancré en bas de l'écran** (`position: sticky`), comme un clavier : pleine largeur **et**
    toujours visible. Pour ne pas masquer la grille, il a été compacté (420 → **253 px**) :
    navigation des volées sur un rang défilant, volée tapée et actions sur un rang, les onze
    touches sur un seul. ⚠️ **Dès 45 rem, et borné à la fenêtre** : ancrage et compactage
    partagent ce seuil, qui inclut la **tablette en portrait** (768 px), l'appareil visé. Sur un
    **téléphone**, non compacté, un pavé collé plus haut que l'écran aurait son haut
    inatteignable : il reste empilé sous la grille. *(1ᵉʳ correctif de revue à 60 rem : il avait
    rouvert la tablette en portrait pour régler le téléphone — relevé en 2ᵉ passe, axe D.)*
  - ⚠️ **La ligne et le pavé lisent la même volée ouverte** (`voleeOuverte`, état `ouverture`
    unique dans `Saisie`). La 1ʳᵉ version recalculait dans la ligne : la ligne montrait une autre
    volée que le pavé dès qu'on naviguait ou qu'une volée rendue était ressaisie (revue, axes B,
    C1, D). Toucher le **nom** d'un autre archer remet l'ouverture à zéro ; les cases restent
    inactives tant que la série n'est pas lue ; sans barème lisible, cumul et totaux affichent
    « ? ».
  - ⚠️ **« 90 px par touche » n'est tenu qu'à partir d'une carte d'environ 1 100 px** : sur la
    carte de 1 061 px du poste de mesure, les onze touches font **87 × 64 px**. Les tenir à 90 px
    imposerait un second rang, donc de repousser la grille.
  - **Le domicile unique** est `domain/blason.points_zone` (à côté de `ZoneScore`), et non
    `serie.py` : **cinq** sites portaient la règle, pas deux — `serie.py`, `duel.py`,
    `application/generateur_scores.py` (`valeur_zone`, dupliquée « délibérément » parce que le
    symbole était privé), `saisie/volees.ts`, `saisie-duels/duel.ts`. Les quatre premiers sont
    résorbés ; **`duel.ts` reste** (le DTO des duels ne sert pas de table) — inscrit à `DETTE-111`,
    qui reste ouverte aussi pour sa moitié « agrégation ».
  - Le cumul de série de la ligne est libellé **« cumul »** : sans le mot, `0 [ ][ ][ ] 0` ne disait
    pas lequel des deux nombres était la somme de la volée.
- **Dépend de** : E17US008 · **Jalon** : J3

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
- **Notes** : ⚠️ **US à deux temps — à redécouper dès que le relevé est produit**, pour la même
  raison qu'`E17US008` : le « résorber » n'est pas borné avant que le « relever » ait rendu.
  ⚠️ **`P03` a été redessinée le 05/08 et n'a pas été validée** (pas de tour 2) ; elle est
  écartée pour la même raison qu'A14. Ne pas rouvrir l'arbitrage d'`E16US004`.
- **Notes (livraison, 25/09/2026)** — le relevé des 7 planches est dans
  [`EPIC-17`](../epics/EPIC-17-fidelite-aux-maquettes.md). **Pas de redécoupage** : le relevé a
  rendu un « résorber » **borné et petit**, l'axe public ayant été rapproché d'avance par `E16US004`
  et `E16US009`. Arbitrages tranchés en cours d'US, reversés ici :
  - **Périmètre retenu au cadrage** (commanditaire, 25/09) : relevé **et** résorption dans la même
    branche, les réserves 🟡 du tour 1 comptant dans la cible.
  - **Correspondance par l'intention** (ADR-0113) : **P05** a ses lettres glissées (le retenu
    « “mon chemin” en liste » est la planche **B**) ; **P06** dessinait l'ancienne variante
    **écartée** (tri par cible) ; **P04** avait **inversé** l'ordre retenu (« ma cible d'abord »).
  - **P04 · « ma cible d'abord »** : la carte des places suivies précède la grille **quel que soit
    l'affichage** (« tout » ou « mes archers ») — elle est lue sur le plan complet. Ordre de la
    **salle** (cible, puis couloir), pas l'ordre d'ajout des suivis. Sans archer suivi posé sur le
    départ affiché, **pas de carte** : le plan reste seul.
  - **P04 · pas de regroupement par pas de tir** : le gabarit est une liste de cibles (ADR-0073),
    l'écran ne peut pas le dire — **la planche est corrigée**, pas le produit.
  - **P01/P02 · identité secondaire** : « club · catégorie » sous le nom, dans la recherche **et**
    sur la carte suivie. Une partie inconnue est **tue**, jamais remplacée par un identifiant ni par
    un club inventé (ADR-0014).
  - **Planches corrigées** là où elles étaient en retard sur un arbitrage (réserve 2 d'ADR-0074) :
    P04, P05 (horaires par tour — réponse du 04/08 : « seulement pour les départs des différentes
    phases »), P06, P07.
  - **P02 · rang provisoire et « volée 8 sur 12 »** : **non faits**, proposition du redessin du 05/08
    jamais validée — **à reposer au tour 2**, comme `S04`.
  - ⚠️ **Le CA « l'écran de salle se juge à sa distance d'usage » n'est pas tenu** par le relevé :
    Chrome reste à 1366 px sur le poste. P06/P07 sont confrontés au code et au CSS ; le contrôle en
    salle (1920 × 1080, à plusieurs mètres) **reste à faire par le commanditaire**.
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
- **Arbitrages rendus** *(livrée le 23/09/2026 — reversés ici dans le commit de l'US, règle 9)* :
  - **Forme du contrôle : test front**, comme le pressentaient les Notes — mais la raison n'était pas
    « la CI front tourne déjà ». C'est que le test **importe** `AXE_PAR_DESTINATION` : la source
    produit est lue par `tsc`, jamais regexée, donc **un seul des deux côtés peut mentir sur sa
    forme**. Un garde-fou Python (comme `test_domain_isolation.py`) aurait dû parser les *deux*
    fichiers — deux parseurs fragiles au lieu d'un.
  - **Déclaration d'une divergence volontaire** : `// PLANCHE-A-VENIR: <id> — <pourquoi>` dans
    `appareils.js`, **nominative, justifiée, locale et périssable** (les quatre bornes sont dans
    [ADR-0112](../docs/adr/0112-une-transcription-documentaire-se-tient-sous-garde-mecanique.md) §4,
    chacune fermant un contournement **mesuré en revue**). ⚠️ **Voie préférée** : ne pas inscrire
    du tout l'écran non livré dans la table — `navigationAdmin` le rend déjà « non livrée » en
    pointillés, mécanisme antérieur à l'US que l'échappatoire contredisait. ⚠️ **Asymétrie voulue** : une maquette *en avance* sur le produit se déclare et
    passe ; une destination *livrée* qu'aucune maquette ne montre reste rouge **sans échappatoire**
    — c'est ce sens de dérive, et lui seul, qui fait relire des planches périmées.
  - **Le contrôle porte aussi l'axe** : une destination rangée sous « pilotage » d'un côté et
    « atelier » de l'autre rougit. Gratuit — les deux structures portent déjà cette donnée.
  - **Périmètre : les identifiants de destination seulement** — ce qui reste hors garde est
    énuméré par `DETTE-110`, seul endroit qui le fasse. **Ce résidu — libellés et ordre —** vit
    dans un tableau local à `CoquilleAdmin`, hors de portée d'un import ; les remonter serait la
    **4ᵉ** `Record` exhaustif d'`axes.ts` (`AXE_PAR_DESTINATION`, `BESOIN_TOURNOI`,
    `OUVRE_UN_ELEMENT`) : le pattern est **déjà établi**, donc la règle 16 l'autorise — elle
    n'interdit que d'en **introduire** un sur pari. Le motif du report est le **coût** : 33
    entrées à déplacer dans un composant de 759 lignes, au milieu d'une US d'outillage.
    ⚠️ *(La 1ʳᵉ rédaction disait « 3ᵉ occurrence, donc remède structurel » : faux deux fois,
    relevé en revue — `OUVRE_UN_ELEMENT` existe, et la règle 16 ne dit pas cela.)*
- **Écart réel mesuré à la livraison** *(le garde-fou a été vu rouge avant d'être vu vert)* : **4
  destinations livrées absentes** des maquettes — `identite` (E16US006), `archer` (E16US010),
  `pret-demarrer` (E16US012), `audit` (E16US016) — et **1 fantôme**, `doublons`, retirée du produit
  par `E16US010`. Soit **cinq US** de dérive accumulée, plus **quatre libellés** périmés dont deux
  renommés par `E16US002` *précisément parce qu'ils portaient chacun le nom de l'autre*.
  ⚠️ **« Aucun ADR » était une erreur, corrigée en revue** : les deux garde-fous invoqués comme
  patron sont chacun adossés à une décision écrite (règle 1 de `CLAUDE.md`, ADR-0075), et la
  décision prise ici — *une copie documentaire inévitable est admise à condition d'être tenue
  sous garde* — est une **exception bornée à ADR-0102 §1**, généralisable (un 2ᵉ candidat existe :
  `maquettes/assets/systeme.css`). D'où [ADR-0112](../docs/adr/0112-une-transcription-documentaire-se-tient-sous-garde-mecanique.md).
- **Dépend de** : — · **Jalon** : J3
