# E03 — Placement des archers & plan de cibles — User Stories

> EPIC : [EPIC-03](../epics/EPIC-03-placement.md) · Réfs : CDC fonctionnel M4, prototype `blason.py`/`player.py`.

> ⚠️ **Maille révisée le 17/07/2026** — regroupement des US au grain « capacité » (10 → 6). Les
> anciennes US découpées par étape technique (modéliser / placer / signaler / ajuster / générer le
> plan…) sont devenues des **critères d'acceptation** de l'US de capacité qui les porte. **Aucun
> comportement n'est perdu** (règle 9 — chaque ancien titre = une puce CA identifiée). Correspondance
> ancien → nouveau en fin de fichier. Aucune US de cet epic n'était livrée avant ce refactor : c'est
> un pur regroupement de backlog, sans impact sur du code existant.

---

### E03US001 — Placement automatique & plan de cibles
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
  la **séparation catégorie/blason** restent hors de cette US (E03US006 / E03US007). Périmètre
  technique tranché le 17/07/2026 : **domaine + service + endpoint de lecture** (recalcul à la
  demande) ; la **persistance** du plan et l'**ajustement** manuel sont E03US004 — d'où la hauteur
  laissée **facultative** au PUT catégorie ([DETTE-009](../docs/dette.md), le front est hors
  périmètre).
- **Absorbe** : ex-E03US001 à 003, E03US008. **Dépend de** : E01US007, E02US004 · **Jalon** : J1

### E03US004 — Ajuster le placement (glisser-déposer)
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
- **Absorbe** : ex-E03US004, E03US005. **Dépend de** : E03US001 · **Jalon** : J1

### E03US006 — Contrainte ≥ 2 clubs par cible
*En tant qu'*administrateur, *je veux* au moins 2 clubs par cible quand c'est possible, *afin d'*
assurer la mixité.
- **CA** : le placement auto favorise ≥ 2 clubs/cible ; signalé si impossible.
- **Dépend de** : E03US001 · **Jalon** : J2

### E03US007 — Contrainte séparation catégorie/blason
*En tant qu'*administrateur (officiel), *je veux* cloisonner par catégorie/blason, *afin de*
respecter les règles officielles.
- **CA** : sur une cible, respect du blason associé à la catégorie ; conflits signalés.
- **Notes** : ordre de priorité des contraintes à confirmer (question ouverte EPIC-03).
- **Dépend de** : E03US001, E01US006 · **Jalon** : J3

### E03US009 — Placer les duellistes côte à côte
*En tant qu'*administrateur, *je veux* que les adversaires d'un duel soient sur des positions
voisines, *afin de* faciliter les matchs.
- **CA** : lors d'une phase de tableau, les 2 duellistes sont placés côte à côte dans la mesure du
  possible.
- **Dépend de** : E03US001, E05US005 · **Jalon** : J2

### E03US010 — Générer / éditer le déroulé horaire
*En tant qu'*administrateur, *je veux* un déroulé horaire de la journée, *afin de* cadencer
l'événement.
- **CA** : grille horaire par phase/tour ; éditable manuellement (génération auto en option —
  question ouverte).
- **Dépend de** : E05US001 · **Jalon** : J4

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
