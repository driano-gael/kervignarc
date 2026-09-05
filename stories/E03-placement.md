# E03 — Placement des archers & plan de cibles — User Stories

> EPIC : [EPIC-03](../epics/EPIC-03-placement.md) · Réfs : CDC fonctionnel M4, prototype `blason.py`/`player.py`.

> ⚠️ **Maille révisée le 17/07/2026** — regroupement des US au grain « capacité » (10 → 6). Les
> anciennes US découpées par étape technique (modéliser / placer / signaler / ajuster / générer le
> plan…) sont devenues des **critères d'acceptation** de l'US de capacité qui les porte. **Aucun
> comportement n'est perdu** (règle 9 — chaque ancien titre = une puce CA identifiée). Correspondance
> ancien → nouveau en fin de fichier. Aucune US de cet epic n'était livrée avant ce refactor : c'est
> un pur regroupement de backlog, sans impact sur du code existant.

---

### E03US001 — Placement automatique & plan de cibles ✅
*En tant qu'*administrateur, *je veux* que le système instancie les cibles/positions depuis le
gabarit, place automatiquement les archers en respectant capacité et fractions de blason, signale
les conflits qu'il ne peut résoudre, et produise le plan de cibles de la qualification, *afin de*
disposer d'un plan exploitable sans saisie manuelle.
- **CA — cibles/positions (ex-001)** : à partir du gabarit (E01US007), génération des `Cible`
  (index, capacité) et positions A/B/C/D.
- **CA — capacité & fraction (ex-002)** : chaque archer reçoit cible + position + départ, sous
  **trois budgets par cible** — la formule « somme des fractions ≤ capacité » recouvrait en fait
  **deux** grandeurs distinctes (clarifié le 17/07/2026 depuis le prototype `cible.py`, réf. de
  l'epic) :
  - **espace** : la somme des `taille` (fractions) des cartons posés sur une cible ≤ **1,0** (une
    cible = une face physique unitaire) ;
  - **positions** : le nombre d'archers sur une cible ≤ `Cible.capacite` (les lettres A/B/C/D) ;
  - **partage de carton** : le nombre d'archers sur un même blason ≤ `Blason.capacite`.
- **CA — hauteur (ex-DETTE-002)** : tous les archers d'une cible tirent à la **même hauteur de
  centre** (`Categorie.hauteur_cm` : 110 cm pour les U11, 130 sinon) — une butte n'a qu'une hauteur.
  Contrainte de 1er rang, au même rang que capacité/espace ([ADR-0022](../docs/adr/0022-hauteur-de-centre-sur-la-categorie.md)).
- **CA — conflits (ex-003)** : si une contrainte ne peut être satisfaite (plus de cible, hauteur
  incompatible, catégorie sans blason par défaut…), un rapport liste les archers non placés (pas
  d'échec silencieux).
- **CA — plan de cibles (ex-008)** : vue par cible listant archers + positions + départ ; source
  des exports (E09US003).
- **Notes** : entité `Cible` ; `position` (ex-`lettre` du prototype) — ex-001. Algo de placement
  dans `domain/placement`, pur et testable — ex-002 ; glouton déterministe, contraintes câblées,
  recalcul à la demande ([ADR-0023](../docs/adr/0023-moteur-de-placement-glouton-deterministe.md)). Le **plan de cibles** (ex-008) est la vue par
  cible produite par le placement — source des exports (E09US003) et de la vue publique (E07US001).
  **L'ex-E03US008 est absorbée ici** ; ses liens entrants (E04US001, E07, E09, E12) ont été
  **redirigés vers E03US001** dans la passe globale du 17/07/2026. La **mixité ≥ 2 clubs** (RG-3) et
  la **séparation catégorie/blason** restent hors de cette US (E03US006 / E03US007 — **livrées** les
  26/07 et 04/08/2026). Périmètre
  technique tranché le 17/07/2026 : **domaine + service + endpoint de lecture** (recalcul à la
  demande) ; la **persistance** du plan et l'**ajustement** manuel sont E03US004 — d'où la hauteur
  laissée **facultative** au PUT catégorie ([DETTE-009](../docs/dette.md), le front est hors
  périmètre). *(DETTE-009 **résorbée** par E03US004 : la hauteur est désormais **obligatoire** au PUT
  — ne pas dériver de cette phrase un CA périmé.)*
- **Absorbe** : ex-E03US001 à 003, E03US008. **Dépend de** : E01US007, E02US004 · **Jalon** : J1

### E03US004 — Ajuster le placement (glisser-déposer) ✅
*En tant qu'*administrateur, *je veux* déplacer un archer à la main et être empêché par l'UI si le
déplacement viole les règles, *afin d'*affiner le placement auto sans le casser.
- **CA — glisser-déposer (ex-004)** : drag & drop d'un archer d'une position à une autre ;
  persistance via la file ; mise à jour live.
- **CA — déplacement invalide (ex-005)** : un déplacement violant capacité/fraction est refusé
  avec message ; état inchangé.
- **CA — réserve** : une zone **réserve** (banc, sans capacité) reçoit les archers non posés. Le
  placement auto y range ceux qu'il **ne peut pas** placer, avec une **raison explicite** (pas de
  blason, plus de cible compatible) — jamais d'archer perdu en silence. L'admin peut y mettre un
  archer de côté et l'en reposer sur une case libre. **Plan final = réserve vide** + contraintes
  respectées.
- **CA — échange atomique** : déposer un archer sur une case **occupée** permute les deux ; la
  permutation est validée **en bloc** (chacun doit tenir dans la cible de l'autre) et refusée
  entièrement sinon (état inchangé). Déposer depuis la réserve sur une case occupée est refusé
  (rien à permuter en retour).
- **CA — placer les restants** : un bouton complète la réserve **automatiquement** dans les trous
  du plan **sans déplacer** les archers déjà posés ; ce qu'aucune cible ne prend reste en réserve.
- **CA — annuler** : un bouton « annuler les modifications » **régénère** le placement auto
  (déterministe) et écrase les ajustements manuels (avec confirmation). C'est la même opération que
  « générer le plan » — cf. [ADR-0024](../docs/adr/0024-plan-de-cibles-materialise-ajustable.md).
- **Notes** : front feature `placement`, **écran dédié admin sur PC** (drag **HTML5 natif**, sans
  dépendance — la règle 10 « tactile prioritaire » vise les tablettes de saisie, pas cet écran).
  Persistance **matérialisée** (table `placement`, une affectation par inscription ; sans ligne =
  réserve) et modèle **live / serveur autoritaire** : chaque geste écrit via la file et diffuse — 
  [ADR-0024](../docs/adr/0024-plan-de-cibles-materialise-ajustable.md). Résorbe **DETTE-009** :
  porte la hauteur de centre au formulaire catégorie et rend `hauteur_cm` obligatoire au PUT.
  *(Arbitrages tranchés le 18/07/2026, reversés ici — règle 9.)*
- ⚠️ **Renvoi — `E16US005` redemande cette réserve sous le nom de « puits de réserve ».** Le
  questionnaire A11 du 04/08/2026 dit *« je ne vois pas de puits de réserve pour déplacer des archers
  sans les positionner »*, et la story pose en question ouverte « en réserve se représente-t-il côté
  serveur ? ». **La réponse est ici** : oui, et depuis E03US004 — le modèle de persistance d'
  [ADR-0024](../docs/adr/0024-plan-de-cibles-materialise-ajustable.md) est *une affectation par
  inscription, **sans ligne = réserve*** ; le placement auto y range déjà les non-plaçables **avec
  leur raison**. `E16US005` est donc, sur ce point, un **défaut d'écran** (la zone n'est pas rendue),
  pas une capacité serveur à écrire. *(Renvoi posé le 08/08/2026 : c'est le seul des cinq doublons
  fonctionnels du backlog que le projet n'avait pas détecté au cadrage — les quatre autres l'ont
  tous été. Un doublon non signalé se paie deux fois : une US refait ce qu'une autre a livré, ou
  bien y renonce en croyant le sujet couvert.)*
- **Absorbe** : ex-E03US004, E03US005. **Dépend de** : E03US001 · **Jalon** : J1

### E03US006 — Contrainte ≥ 2 clubs par cible ✅
*En tant qu'*administrateur, *je veux* au moins 2 clubs par cible quand c'est possible, *afin d'*
assurer la mixité.
- **CA** : le placement auto favorise ≥ 2 clubs/cible ; signalé si impossible.
- **Notes (livré, 26/07/2026 — [ADR-0047](../docs/adr/0047-mixite-clubs-par-reordonnancement-et-signal-derive.md))** :
  contrainte **molle**, **priorité la plus basse** (EPIC-03 : `capacité > catégorie/hauteur > mixité
  club`) — jamais bloquante, jamais au détriment d'une contrainte de rang supérieur. La mixité est
  obtenue en **ré-ordonnant l'entrée** du glouton (round-robin des clubs par groupe hauteur/blason),
  le moteur restant inchangé. « Signalé si impossible » = propriété **dérivée** `mixite_non_garantie`
  au niveau **cible** (≥ 2 archers, < 2 clubs **connus** distincts), recalculée à la lecture (jamais
  persistée, comme la raison de réserve d'ADR-0024). `club_id NULL` = **indécidable** (ADR-0014) :
  deux inconnus ne sont **pas** réputés du même club → signalé. **Surface livrée** : moteur + service
  + API, **et** un **badge ambre** par cible + une **bannière** récapitulative sur l'écran de placement
  admin (arbitrage de périmètre tranché au cadrage). Une cible à 0/1 archer est **sans objet** (pas de
  signal). Recette : [`docs/fonctionnel/E03US006.md`](../docs/fonctionnel/E03US006.md).
- **Dépend de** : E03US001 · **Jalon** : J2

### E03US007 — Contrainte séparation catégorie/blason ✅
*En tant qu'*administrateur (officiel), *je veux* cloisonner par catégorie/blason, *afin de*
respecter les règles officielles.
- **CA — réglage activable à quatre positions** *(élargi au cadrage du 04/08/2026, reversé ici)* :
  le cloisonnement est un **réglage du tournoi** (RG-4, activable, indépendant du type de tournoi) à
  quatre positions — `aucun` (**défaut**, comportement d'E03US001), `categorie` (une seule catégorie
  par cible), `blason` (un seul blason par cible), `blason_et_categorie`.
- **CA — contrainte dure** : quand le réglage est actif, le placement automatique **ne mêle jamais**
  ce qu'il sépare, et le **déplacement manuel** violant la règle est refusé (409, état inchangé).
- **CA — conflits signalés** : ce que le cloisonnement empêche de poser part en **réserve** avec une
  raison **propre** (`cloisonnement`), distincte de « aucune cible possible » (salle saturée) — le
  geste correctif n'est pas le même. Jamais d'échec silencieux.
- **CA — priorité des contraintes** *(question ouverte d'EPIC-03, tranchée)* :
  `capacité / espace / hauteur` > **cloisonnement** > `mixité de club` > `adjacence des duellistes`.
  Le cloisonnement ne peut que **retirer** des cohabitations, jamais en autoriser une.
- **CA — changer le réglage ne déplace personne** : le plan est matérialisé (ADR-0024) ; une cible
  déjà posée qui viole le réglage nouvellement activé est **signalée** (badge + bannière disant de
  régénérer), jamais réarrangée d'office. Sur une telle cible, **toute** pose est refusée — même
  celle d'un archer de la catégorie déjà présente : le refus dit « cette cible ne respecte déjà pas
  le cloisonnement », il n'accuse pas le candidat. *(Arbitrage tranché en cours d'US : une règle
  « ne pas aggraver » dépendrait de l'ordre des gestes, donc serait imprévisible pour l'admin.)*
- **Notes (livré, 04/08/2026 — [ADR-0071](../docs/adr/0071-cloisonnement-categorie-blason-active-et-dur.md))** :
  - **Surface livrée** : moteur + service + API (`GET`/`PUT /api/v1/tournois/{id}/cloisonnement`)
    **et** le sélecteur sur l'écran de placement admin, le badge ambre par cible, la bannière
    récapitulative et la raison de réserve. Le réglage vaut aussi pour le **plan de duels**
    (E03US009) : même salle, même règle.
  - ⚠️ **`blason_et_categorie` est aujourd'hui équivalent à `categorie`** : le blason dérive de la
    catégorie (`Categorie.blason_id`), donc deux archers de même catégorie ont le même blason. Les
    deux positions divergeront quand une **phase pourra surcharger le blason** (EF-1.4). Livré à
    quatre positions en connaissance de cette redondance (ADR-0071 §3) — ne pas la lire comme un
    gain actuel.
  - **Catégorie inconnue = refus**, jamais « même catégorie » : l'indécidable d'ADR-0014 transposé à
    une contrainte dure.
  - **Coût assumé** : un cloisonnement strict consomme des cibles (chaque catégorie entame sa butte)
    et peut produire de la réserve sur un gabarit juste — visible dans les conflits, réversible d'un
    réglage.
  - Recette : [`docs/fonctionnel/E03US007.md`](../docs/fonctionnel/E03US007.md).
- **Dépend de** : E03US001, E01US006 · **Jalon** : J3

### E03US009 — Placer les duellistes côte à côte ✅
*En tant qu'*administrateur, *je veux* que les adversaires d'un duel soient sur des positions
voisines, *afin de* faciliter les matchs.
- **CA** : lors d'une phase de tableau, les 2 duellistes sont placés côte à côte dans la mesure du
  possible ; signalé si impossible.
- **Notes (arbitrages tranchés le 26/07/2026 — [ADR-0048](../docs/adr/0048-cote-a-cote-des-duellistes-par-reordonnancement.md))** :
  - **« Côte à côte » = positions adjacentes de la *même* cible** (lettres consécutives A-B, B-C, C-D ;
    A-C non). Contrainte **molle, priorité la plus basse**, jamais bloquante — jumeau exact de la mixité
    (E03US006/ADR-0047) : obtenue en **ré-ordonnant l'entrée** du glouton (les deux duellistes émis
    consécutivement dans leur groupe `hauteur/blason`), le moteur restant inchangé.
  - **« Signalé si impossible »** = propriété **dérivée** (jamais persistée) : un duel dont les deux
    membres ne sont pas sur la même cible à des positions adjacentes est listé (`duels_non_cote_a_cote`),
    et les cibles concernées portent un **badge ambre** `adjacence_non_garantie` + une **bannière**
    récapitulative sur l'écran d'ajustement.
  - **Périmètre matérialisé & ajustable** (choix commanditaire) : le plan de duels est **matérialisé**
    (table `placement_tableau`, scoppée par **phase**) et **ajustable au glisser-déposer**, calqué sur
    la qualification (E03US004/ADR-0024). L'**appariement** (qui affronte qui) est **recalculé** depuis
    le classement (déterministe, ADR-0023) ; seule la **pose** est persistée.
  - **MVP volontairement étroit** : **ensemencement scratch** (au `rang_scratch`, ce que
    `construire_tableau` sait déjà faire — il ignore les catégories, ADR-0028) ; **tour 1 uniquement**
    (seuls duels aux adversaires connus à la construction) ; **réutilise le gabarit** du tournoi. Les
    tableaux **par catégorie**, les **tours ≥ 2** et un agencement de finale dédié sont downstream
    (E05US010/E06US006) — hors de cette tranche. Les `Participant` de genre **équipe** sont ignorés
    proprement (pas d'entité `Equipe` avant E13US002).
  - **Pose orpheline** (arbitrage tranché à la revue, 26/07) : l'appariement étant **recalculé** mais
    la pose **persistée**, une pose dont l'inscription n'est **plus** duelliste du 1er tour (le
    classement a changé — un archer classé plus tard décale l'arbre, l'ancien duelliste passe en bye)
    est **orpheline**. Choix retenu : elle est **masquée en lecture** et **purgée à la première
    écriture** (ajustement ou régénération) ; le plan de duels fait autorité **après régénération**.
    C'est ce qui évite un 500 quand l'admin déplace un jeton sur une case « visiblement vide » portant
    encore une pose orpheline.
- **Dépend de** : E03US001, E05US005 · **Jalon** : J2

### E03US010 — Générer / éditer le déroulé horaire
*En tant qu'*administrateur, *je veux* un déroulé horaire de la journée, *afin de* cadencer
l'événement.
- **CA** : grille horaire par phase/tour ; éditable manuellement (génération auto en option —
  question ouverte).
- **Dépend de** : E05US001 · **Jalon** : J4

### E03US011 — Placement : retour visuel de génération + position (A..D) visible
*En tant qu'*administrateur, *je veux* voir que « Générer le plan » travaille et aboutit, et voir la **position** (A, B, C, D…) de chaque archer sur sa cible après placement, *afin de* comprendre ce qui se passe et vérifier le placement.
- **Contexte** : retours de la démo du 27/07/2026. (1) Le bouton « Générer le plan » (`Placement.tsx`) déclenche un PUT `/plan-de-cibles` **sans aucun retour visuel** (ni chargement, ni succès, ni erreur) → il **paraît muet** ; à trancher : muet-mais-ok ou muet-en-échec. (2) La position (lettre `A..D`) n'est **pas** affichée sur l'écran admin de placement, alors qu'elle l'est côté public (`PlanCiblesPublic.tsx`).
- **CA — retour de génération** : cliquer « Générer le plan » montre un état **en cours** (bouton occupé), puis un **succès** (le plan mis à jour s'affiche) ou une **erreur lisible** en cas d'échec ; l'échec silencieux éventuel est diagnostiqué et corrigé.
- **CA — position visible** : chaque archer placé affiche sa **position** (A, B, C, D…, cf. E01US019 au-delà de D) sur sa cible **côté admin**, comme côté public.
- **Notes** : correctifs **front** (présentation) ; pas de changement de domaine attendu. ⚠️ Front sans tests de rendu → vérifier **à l'écran**. US à **surface visible** → doc fonctionnelle + journal d'avancement.
- **Dépend de** : E03US001, E03US004 · **Jalon** : J1 · **Origine** : démo 27/07/2026


### E03US012 — Poser les cibles des tours suivants

*En tant qu'*administrateur, *je veux* que les duellistes d'un tour ≥ 2 reçoivent une cible dès que
leur tour est déterminé, *afin de* savoir où envoyer chaque archer au lieu de lire
« cible non attribuée » sur tout le tableau passé le premier tour.

- **Contexte** : `E03US009` a livré le plan de duels **tour 1 uniquement** et renvoyait les tours
  ≥ 2 « downstream (E05US010/E06US006) ». Ce renvoi est **faux** : ces deux US désignent la
  **profondeur de classement** (classer du rang 1 au rang N), pas la pose de cibles, et elles sont
  livrées depuis le 31/07/2026 sans que la garde bouge. `DETTE-019` l'avait constaté (« le registre
  attendait une US déjà passée ») ; **aucune US n'a jamais porté ce sujet**. Cadrée le 05/09/2026 en
  amont d'`E16US013`, dont elle conditionne la valeur : sans pose au-delà du tour 1, aucun duel n'est
  jamais « prêt à lancer » après le tour 1, donc il n'y a rien à lancer automatiquement.
- **CA — une pose appartient à un tour** : un archer occupe une cible **par tour**, pas une par
  phase. Les poses existantes deviennent celles du **tour 1**, sans changement d'affichage pour un
  tournoi déjà en base.
- **CA — le tour suivant se pose seul, dès qu'il est déterminé** : quand **tous** les duels d'un tour
  sont tranchés, les duellistes du tour suivant reçoivent leur pose **sans geste de l'organisateur**,
  puis restent ajustables au glisser-déposer comme le tour 1. ⚠️ **La maille est le tour entier, pas
  le duel** (tranché au cadrage du 05/09/2026) : regrouper les archers demande de connaître
  l'ensemble à placer, et poser duel par duel au fil des validations éparpillerait le tour sur le pas
  de tir dans l'ordre d'arrivée des résultats.
- **CA — un tour avancé se regroupe sur les premières cibles** (arbitrage du commanditaire,
  05/09/2026) : moins d'archers restant à chaque tour, le tour se tasse sur les cibles de **plus
  petit numéro** et libère les cibles hautes. La contrainte « côte à côte » d'`E03US009`
  ([ADR-0048](../docs/adr/0048-cote-a-cote-des-duellistes-par-reordonnancement.md)) reste **molle** et
  s'applique à l'identique.
- **CA — rien ne se pose pour un tour indéterminé** : un duel dont les sources ne sont pas tranchées
  n'a **aucune** pose, et le feu vert garde son blocage nommé (« en attente du duel n°X »). L'absence
  de pose n'est jamais une pose vide.
- **CA — la garde « tour 1 » tombe** aux **quatre** sites que `DETTE-019` énumère (feu vert,
  routage, et leurs deux jumeaux **front**) : le feu vert cesse d'annoncer « cible non attribuée »
  sur un tour ≥ 2 posé, et le panneau de routage annonce la vraie cible. ⚠️ Lever la garde côté
  serveur **sans** toucher les deux fichiers front laisserait l'écran annoncer une limite disparue,
  **sans qu'aucun test rougisse** — c'est nommément le piège décrit au registre.
- **CA — une pose périmée ne survit pas à la correction qui l'a périmée** : corriger un résultat d'un
  tour antérieur change les vainqueurs, donc les occupants des tours suivants. Les poses des tours
  devenus faux suivent la règle déjà posée par `E03US009` pour les **poses orphelines** — masquées en
  lecture, purgées à la première écriture — et le tour se repose quand il redevient déterminé.
- **Notes** :
  - ⚠️ **Le moteur n'est pas en cause** : `domain.placement.placer` est un glouton **générique, sans
    notion de tour**. La limite vient de son appelant (`ServicePlacementDuels._charger`, qui ne lui
    passe que `paires_du_premier_tour`). Il n'y a **aucun moteur à écrire**.
  - ⚠️ **Le vrai blocage est la clé de la table** : `placement_tableau` a pour clé primaire
    `(phase_id, inscription_id)`. Elle ne **peut pas** représenter deux poses du même archer. La clé
    gagne le tour — changement de clé primaire + reprise des lignes en tour 1, donc migration `0053`
    et [ADR-0106](../docs/adr/0106-la-pose-d-une-cible-appartient-a-un-tour.md).
  - ⚠️ **Cette US aggrave `DETTE-021`** (le feu vert dit « prêt » sans vérifier que les deux
    duellistes sont sur la **même** cible) : le défaut n'existait qu'au tour 1, il vaudra désormais à
    **tous** les tours. La ligne du registre est **élargie**, pas contournée.
  - ⚠️ **Pas de sélecteur de tour** à l'écran du plan de duels dans cette tranche : il rend le plan
    du **tour en cours**, qu'il **nomme**. Consulter un tour passé ou à venir est un confort écarté du
    périmètre, faute de besoin énoncé.
  - US à **surface visible** → doc fonctionnelle + journal d'avancement.
- **Dépend de** : E03US009, E05US005, E12US002 · **Jalon** : J2 · **Origine** : cadrage d'`E16US013`,
  05/09/2026 — résorption de `DETTE-019`

---

## Correspondance ancien → nouveau (maille du 17/07/2026)

| Ancienne US | Titre d'origine | Devient |
|---|---|---|
| E03US001 | Modéliser cibles/positions depuis le gabarit | **E03US001** — CA « cibles/positions » |
| E03US002 | Placement auto : capacité + fraction de blason | **E03US001** — CA « capacité & fraction » |
| E03US003 | Placement auto : signaler les conflits | **E03US001** — CA « conflits » |
| E03US004 | Ajuster le placement en glisser-déposer | **E03US004** — CA « glisser-déposer » |
| E03US005 | Empêcher un déplacement invalide | **E03US004** — CA « déplacement invalide » |
| E03US006 | Contrainte ≥ 2 clubs par cible | **E03US006** (inchangée) |
| E03US007 | Contrainte séparation catégorie/blason | **E03US007** (inchangée) |
| E03US008 | Générer le plan de cibles (qualif) | **E03US001** — CA « plan de cibles » |
| E03US009 | Placer les duellistes côte à côte | **E03US009** (inchangée) |
| E03US010 | Générer / éditer le déroulé horaire | **E03US010** (inchangée) |
