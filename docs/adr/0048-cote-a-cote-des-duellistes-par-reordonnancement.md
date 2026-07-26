# ADR-0048 — Duellistes côte à côte : ré-ordonnancement de l'entrée + signal dérivé, plan de duels matérialisé par phase

- **Statut** : Accepté
- **Date** : 2026-07-26
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E03-placement.md`](../../stories/E03-placement.md) (E03US009) ;
  [`docs/glossaire.md`](../glossaire.md) (`duelliste`, `côte à côte`, `plan de duels`)
- **Introduit par** : E03US009 (placer les duellistes d'un tableau côte à côte).
- **S'appuie sur** : [ADR-0023](0023-moteur-de-placement-glouton-deterministe.md) (glouton
  déterministe recalculable) · [ADR-0024](0024-plan-de-cibles-materialise-ajustable.md) (plan
  **matérialisé et ajustable**, raisons **dérivées à la lecture**) · [ADR-0047](0047-mixite-clubs-par-reordonnancement-et-signal-derive.md)
  (le patron jumeau : mixité par ré-ordonnancement + signal dérivé) · [ADR-0028](0028-participant-abstraction-du-competiteur.md)
  (le moteur de tableau oppose des `Participant`) · [ADR-0004](0004-politiques-de-tableau-injectables.md)
  /[ADR-0046](0046-config-policies-politiques-nommees-parametrees.md) (politiques de tableau
  injectables).

## Contexte et problème

Le CA d'E03US009 est mince — « lors d'une phase de tableau, les 2 duellistes sont placés **côte à
côte dans la mesure du possible** » — mais il repose sur deux briques qui, au moment de le prendre,
**ne se rejoignaient nulle part** :

- le **placement** (E03US001/004/006) est scoppé par **départ** (créneau de qualification), matérialisé
  dans la table `placement` (PK `inscription_id`) ; il n'a **aucune** notion de phase de tableau ;
- l'**arbre d'élimination** (E05US005) est un domaine **pur, en mémoire** : `Tableau`/`Match`/
  `Participant` (`domain/tableau.py`, `participant.py`) sans service, repository, API ni persistance.
  Aucun code ne construit un arbre à partir d'un classement réel — c'est E05US010, non livrée.

Trois questions structurantes, qu'aucun CA ne tranche :

1. **Où vivent les duels** au moment de placer, sachant que l'arbre n'est pas persisté ?
2. **Comment scoper un placement de phase de tableau**, la table `placement` étant déjà prise par la
   qualification (une pose par inscription par départ) ?
3. **Comment favoriser le côte à côte** dans le glouton mono-passe déterministe (ADR-0023) sans casser
   les contraintes de rang supérieur ni la non-régression d'E03US001–006 — et **où signaler** un duel
   qui n'a pas pu l'être ?

Le commanditaire a de plus tranché (26/07/2026) le **périmètre** : le placement des duels est
**ajustable au glisser-déposer** (comme la qualification, E03US004), donc **matérialisé** — et non une
simple vue recalculée en lecture seule.

## Décision

### 1. Le tableau est **recalculé** (déterministe), le **placement** est **matérialisé**

L'arbre (`construire_tableau`) est une **fonction pure reproductible** de `(participants ordonnés par
rang, seeding, byes)` : même régime qu'ADR-0023, **recalculable à la demande** depuis le classement
(`ServiceClassement`) dont il dérive. On ne persiste **pas** l'arbre : le figer exigerait une table de
matchs + la progression + le routing persistés — le cœur d'E05US010, hors périmètre. Ce qu'on
matérialise, comme la qualification (ADR-0024), c'est le **placement** (qui tire où), pour le rendre
**ajustable**. Séparation nette : l'**appariement** (qui affronte qui) est recalculé ; la **pose**
(sur quelle cible/position) est persistée et éditable.

**Portée du tableau, MVP (arbitrages reversés dans `stories/`)** :
- **Ensemencement scratch**, au `rang_scratch` du classement — c'est exactement ce que
  `construire_tableau` sait faire (il **ignore** les catégories, ADR-0028). Les tableaux **par
  catégorie** sont downstream (E05US010/E06US006) ; hors de cette tranche.
- **Tour 1 uniquement** : l'arbre ne connaît les occupants (`haut`/`bas`) **qu'au premier tour** ; les
  tours ≥ 2 restent `None` tant que les matchs amont ne sont pas joués (`domain/tableau.py`). Placer
  « les duellistes » n'a donc de sens déterministe qu'au **1er tour**.
- **Réutilise le gabarit de salle** du tournoi (`GabaritSalleRepository.par_tournoi`). Un agencement
  propre à la phase finale est une évolution ultérieure.

### 2. Le placement de duels est scoppé par **phase**, dans une **table dédiée** `placement_tableau`

Trois options pesées :
- **(a) discriminant phase/tour dans `placement`** ⇒ change la PK `inscription_id` en clé composite,
  touche tout le `PlacementRepository` et le `ON DELETE CASCADE` existants, régresse E03US001–006.
  **Rejeté** (invasif pour un besoin orthogonal).
- **(b) table dédiée `placement_tableau`**, keyée `(phase_id, inscription_id)`, colonnes
  `cible_index`, `position`. **Retenu** : isole le concern, laisse la qualification intacte, autorise
  l'ajustement (drag & drop) sans toucher l'invariant d'ADR-0024. Un inscrit **sans** ligne = réserve
  (l'absence *est* l'information, comme ADR-0024).
- **(c) recalculé non persisté** ⇒ écarté par le choix « ajustable » du commanditaire.

Le scope est la **phase** (une phase `ELIMINATION_DIRECTE`), pas le départ : une phase de tableau est
**tournoi-large**, pas un créneau. `ON DELETE CASCADE` sur `phase_id` **et** `inscription_id`.

### 3. Le pont `Participant → inscription` vit dans le **service**, sans nouveau port

La résolution `Participant → {archer|équipe}` est explicitement désignée par `domain/participant.py`
comme relevant d'une **couche haute** (jamais le moteur). Elle va donc dans le nouveau service
applicatif : en individuel, `Participant.ref_id` **est** l'`ArcherId` ; le service remonte
`archer → inscription` (via `InscriptionRepository`) et `archer → ArcherAPlacer` (**même** jointure
catégorie/blason que `ServicePlacement._archer_a_placer`). Un `Participant` de genre `EQUIPE` est
**hors périmètre** (pas d'entité `Equipe` avant E13US002) : le service l'**ignore proprement**, il ne
plante pas. **Aucun nouveau port** : ce ne sont que des compositions de repositories existants.

### 4. Côte à côte = **ré-ordonner l'entrée** + **signal dérivé** (jumeau d'ADR-0047)

- **« Voisin » = positions adjacentes de la *même* cible** : deux lettres consécutives (A-B, B-C, C-D ;
  A-C non). Physiquement côte à côte sur la même butte. On ne retient **pas** « cibles voisines » pour
  le MVP.
- **Mécanisme** : on **ne touche pas** le glouton (`_CibleEnCours.accueille`, ADR-0047 §1). On ajoute
  une stratégie d'ordre `_ordonner_pour_adjacence(archers, partenaire)` : tri de base
  `(hauteur, blason, archer_id)` (mêmes frontières de groupe qu'E03US001), puis, **dans** chaque
  groupe `(hauteur, blason)`, on émet les deux membres d'un duel **consécutivement**. Les deux
  duellistes partageant la catégorie → même blason/hauteur → même groupe : le clustering est naturel.
  Le glouton pose alors deux entrées consécutives sur deux positions consécutives. Une paire n'est
  **pas** côte à côte seulement quand la cible se remplit **entre** les deux (chevauchement de
  frontière) → **signalé**, jamais bloqué. Déterministe : paires clusterisées à la tête de `min`
  archer_id, singletons (byes, effectif impair) en place.
- **`placer` gagne un paramètre de stratégie** : `placer(cibles, archers, *, ordonner=…)`, défaut
  `_ordonner_pour_mixite` (qualification **byte-identique**, non-régression). Le placement de duels
  injecte `_ordonner_pour_adjacence`. Les mêmes trois propriétés d'ADR-0047 tiennent (groupe
  interchangeable pour les budgets → contraintes de rang supérieur intactes, aucune régression de
  décompte, déterminisme).
- **Signal dérivé, jamais persisté** : une **fonction pure** `duels_non_cote_a_cote(plan, paires)`
  liste les duels dont les deux membres ne sont **pas** sur la même cible à des positions adjacentes ;
  `cibles_avec_duel_separe(plan, paires)` en dérive les cibles concernées, rabattues en booléen
  `adjacence_non_garantie` par cible pour le **badge** (calqué sur `mixite_non_garantie`). Contrairement
  à la mixité, le signal **n'est pas** un champ de `CiblePlacee` (le glouton générique ne connaît pas
  les paires) : il se calcule en **post-passe** sur le plan + les paires, côté service, ce qui garde
  `placer` totalement générique et l'oracle 120 / E03US001–006 intacts.

### 5. Mixité (E03US006) ↔ côte à côte : deux stratégies d'ordre, jamais combinées

La mixité ré-ordonne l'entrée de la **qualification** (par départ) ; le côte à côte celle du **tableau**
(par phase). **Deux placements, deux scopes, deux appels distincts à `placer`** — aucune composition
sur le même appel, donc aucun conflit. La couture (paramètre `ordonner`) rend cela explicite. Si l'on
devait un jour les combiner sur une même cible de duels, la priorité serait **côte à côte > mixité**
(logistique du match avant équité), composables par granularité (paires clusterisées à l'intérieur,
clubs entrelacés à l'extérieur) ; hors périmètre ici.

### 6. Surface admin : écran d'ajustement du plan de duels, badge/bannière calqués sur la mixité

Un écran admin (drag & drop **HTML5 natif**, comme E03US004) affiche le plan de duels par cible +
un **badge ambre « duel non côte à côte »** par cible concernée + une **bannière** récapitulative.
Logique de présentation **pure** dans `presentation.ts`, jumelle de la mixité.

## Conséquences

- **+** Le glouton reste **inchangé et prouvablement non régressif** : le côte à côte vit dans un
  pré-tri isolé, pas dans les budgets.
- **+** Séparation propre : appariement **recalculé** (ADR-0023), pose **matérialisée** (ADR-0024). Un
  seul régime de persistance nouveau : la table `placement_tableau`, isolée de la qualification.
- **+** Le signal suit le régime **dérivé/non persisté** (ADR-0024/0047) : rien à migrer pour lui.
- **+** `Participant` reste **opaque** au moteur (ADR-0028) : la résolution vit dans le service, les
  équipes s'ignorent proprement en attendant E13US002.
- **−** Périmètre **volontairement étroit** (scratch, tour 1, gabarit du tournoi) : E03US009 tire à lui
  une part de l'infra d'E05US010 mais ne la couvre pas. Les tableaux par catégorie, les tours ≥ 2 et
  un agencement de finale dédié restent à faire — signalés, non masqués.
- **−** Côte à côte **best-effort par groupe de blason** (comme la mixité) : le glouton mono-passe peut
  séparer une paire qu'un réagencement global aurait rapprochée. Contrepartie assumée (ADR-0023) — le
  signal l'expose, l'admin ajuste au glisser-déposer.
- **−** Une **duplication structurelle** apparaît : `ServicePlacementDuels` recopie, scoppée par
  phase, non seulement la jointure `archer → ArcherAPlacer` mais **toute l'orchestration d'ajustement**
  de `ServicePlacement` (déplacer / échanger / valider / réserve / construire le plan). **2ᵉ
  occurrence** : on l'assume en l'état (règle 12) — scopes et tables distincts, un socle partagé
  coupleraient deux features ; l'extraction attendra la **3ᵉ** (seuil de remède structurel, règle 16),
  pour ne pas introduire un pattern prématuré. La duplication est **signalée, non masquée** (docstrings
  + ce point).
- **−** Le découpage « appariement **recalculé** / pose **persistée** » laisse des **poses orphelines** :
  une pose dont l'inscription n'est plus duelliste du 1er tour (le classement a changé entre deux
  régénérations). Choix (arbitrage de revue, reversé dans `stories/`) : **masquée en lecture** (le plan
  rendu l'écarte via `est_placable`), **purgée à la première écriture** (`_poses_a_jour` sur les chemins
  d'ajustement, qui tournent dans la file ; la régénération réécrit tout de toute façon). Sans ce
  traitement, la détection d'occupant d'un déplacement tombait sur une ligne fantôme → 500. Le plan de
  duels fait donc autorité **après régénération** ; entre-temps l'orpheline est inerte.
