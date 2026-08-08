# ADR-0068 — Le moteur consomme les prélèvements déclarés, et seulement ceux dont la règle est écrite

- **Statut** : accepté
- **Date** : 03/08/2026
- **US** : E05US020 (le moteur consomme les prélèvements déclarés)
- **Voisins** : [ADR-0061](0061-routing-generique-et-placement-en-cascade.md) (sources multiples et
  relatives), [ADR-0063](0063-brouillon-de-format-invariant-a-l-application.md) (la composition d'un
  déroulé et la mesure de l'écart), [ADR-0050](0050-forfait-abandon-et-disqualification.md) (abandon
  relégué, DSQ exclu), [ADR-0065](0065-rang-acquis-lu-sur-la-plage-et-issue-repechee.md) §3 (ne pas
  décider une règle métier dans un canal d'exécution)

## Contexte

E05US010 a livré les **prélèvements** (`Phase.sources`) : « les rangs 1 à 32 de la phase 1 », « les
rangs 33 et suivants ». E01US024 a livré leur **composition** — un écran, un schéma, un diagnostic.
Personne n'a livré leur **consommation** : `ServiceSaisieDuels._decor` ensemençait chaque tableau
avec *tous* les archers en lice, sans jamais lire ce que la phase déclarait.

L'organisateur composait donc « les rangs 1 à 32 », voyait un schéma vert, appliquait son format —
et le jour J le moteur montait un tableau de 120. E01US024 avait rendu l'écart **visible** (effectif
projeté vs constaté, alerte ambre) plutôt que de le laisser tacite, et posé un **test de
caractérisation** qui devait échouer le jour où le moteur honorerait les sources.

L'[audit de maintenabilité du 03/08/2026](../audit-maintenabilite.md) a désigné cette dette
(`DETTE-028`) comme la **seule dette ouverte fabriquant des défauts visibles par l'utilisateur** :
trois des cinq bloquants d'E06US004 en découlaient — palmarès plat toute la matinée, walkover de
forfait rouvrant le même défaut, podium par catégorie indécernable.

## Décision

### 1. Un prélèvement **par rangs** garde les archers dont le rang tombe dans son intervalle

`ServiceSaisieDuels._preleves` lit `phase.sources` et ne conserve que les lignes du classement dont
le `rang_scratch` appartient à l'un des intervalles déclarés. Les bornes viennent du **domaine**
(`SourcePhase.intervalle`), qui sait déjà résoudre une fin ouverte sur l'effectif réel : « les rangs
33 et suivants » vaut 88 archers à 120 classés et 50 à 82. **On consomme cette sémantique, on ne la
réécrit pas** — c'était tout l'objet de la remonter dans le domaine en E05US010.

Une phase **sans source** reste alimentée par les inscriptions : c'est la première de sa séquence
(la qualification), et c'est aussi le tableau tant que l'organisateur n'a rien déclaré. Le
comportement d'avant l'US est donc préservé là où il était correct.

L'effectif de la phase source compte les archers **classés** (un disqualifié n'a pas de rang,
ADR-0050). ⚠️ **Cette borne est aujourd'hui redondante**, et un premier jet de cet ADR en faisait à
tort un argument central : le rang d'une ligne classée ne dépasse jamais le nombre de lignes
classées, donc la borne haute d'une fin ouverte ne filtre rien. La revue adversariale l'a montré
mutation à l'appui — aucun test ne peut distinguer ce calcul de son absence. On garde l'appel parce
qu'il est sémantiquement juste, on retire l'argument plutôt que de l'illustrer par un test
décoratif.

### 2. Le rang prélevé est celui du **classement au moment de la lecture**

Un abandon est relégué en fin de classement et les suivants **remontent** (ADR-0050). « Les rangs 1
à 32 » prélève donc toujours 32 archers tant que 32 restent en lice : le 33ᵉ prend la place laissée.

Ce n'est **pas** un repêchage décidé par le moteur — c'est la conséquence du classement de
qualification, qui se recalcule à chaque lecture (ADR-0023). La propriété est heureuse : le
prélèvement se répare tout seul, sans qu'aucun écran n'ait à gérer « il manque un qualifié ».

*(Un premier jet du CA supposait l'inverse — que le prélèvement laisserait un trou, et qu'il faudrait
arbitrer la promotion du suivant. Vérifié au cadrage : l'arbitrage n'existe pas.)*

### 3. `le_reste` et `par_issue_de_tour` restent **inertes**, et c'est délibéré

Vérifié au cadrage, dans le code : **ni l'une ni l'autre de ces natures n'est résolue nulle part**.
`effectif_selectionne`, `resoudre` et `intervalle` rendent `None` pour les deux, et aucun module ne
les interprète. Elles se **construisent** et se **valident** ; elles ne se **calculent** pas.

Leur donner un sens **ici**, dans un service d'exécution, serait décider une règle métier au mauvais
endroit — exactement ce qu'ADR-0065 §3 a refusé de faire pour le repêchage, et ce que `DETTE-033`
acte. Une phase qui ne déclare que des sources de ces natures retombe donc sur « tous les archers en
lice », comme avant l'US, et un test l'**épingle** : il tombera le jour où l'US du prélèvement
tranchera leur sémantique.

C'est la même discipline que le reste du chantier moteur : **on n'exécute que ce dont la règle est
écrite**.

### 4. Ce que cette US ne fait **pas** : les tableaux par catégorie

`SourcePhase` sélectionne par **rangs**. `Phase` ne porte **aucune** catégorie. Consommer les
prélèvements donne donc « les rangs 1 à 32 du classement scratch », **jamais** « les Seniors
Hommes ».

Le podium par catégorie décerné par des matchs (le 3ᵉ bloquant d'E06US004) demande donc un concept
qui n'existe pas encore — une phase scopée à une catégorie, ou un prélèvement filtré par catégorie.
C'est une **décision de modélisation**, qui mérite son propre cadrage et son propre ADR : US dédiée.

⚠️ **L'audit du 03/08/2026 laissait croire l'inverse** (« rend possible le vrai podium par
catégorie »). C'était faux, et la vérification a été faite avant d'écrire une ligne de cette US.
L'audit est corrigé dans le même commit.

### 5. Une phase dispute une **tranche** de rangs — et le palmarès le sait (résorbe `DETTE-034`)

Correctif de revue adversariale. Consommer les prélèvements a **rendu atteignable** un défaut que
`DETTE-034` décrivait en le jugeant sans impact — au motif, précisément, qu'« aucun moteur ne
consomme les prélèvements ». C'est cette US qui retire la prémisse : c'est donc à elle de solder la
dette.

Le scénario, mesuré sur un déroulé que `verifier_sequence` **accepte** : phase 2 « les rangs 1 à 4 »
(tableau principal), phase 3 « les rangs 5 et suivants » (consolante). La règle du palmarès — « la
phase la plus tardive l'emporte » — couronnait le vainqueur de la **consolante** en tête, et
reléguait le finaliste du principal. Schéma vert, aucune anomalie, aucun bandeau : le PDF projeté en
salle donnait l'or au 5ᵉ de qualification.

**Décision** : `ResultatPhase` porte le **premier rang du tournoi** que sa phase dispute
(`rang_premier`, calculé par `application.prelevement.tranche` depuis les sources), et le palmarès
ordonne sur le rang **absolu** au lieu de l'`ordre` de phase. Une consolante prélevant les rangs 5+
voit son vainqueur classé 5ᵉ — ce qu'il est.

`ordre` ne sert plus que de **départage** à rang égal (une position jouée précède un rang de
qualification). Les tranches d'un déroulé valide ne se recoupant pas, les rangs absolus suffisent à
ordonner.

⚠️ **Ce qu'il faut retenir de méthode** : une dette justifiée par « impact nul parce que X n'existe
pas » doit être **relue par l'US qui livre X**. Ici, `DETTE-034` avait été écrite la veille par
l'auteur même de l'US qui allait l'activer, et la connexion n'a été faite ni au cadrage ni à
l'implémentation — c'est la revue adversariale qui l'a mesurée.

### 6. Un prélèvement que l'effectif ne peut pas honorer : refus, et contrôle **en amont**

Un déroulé composé pour 120 archers, appliqué à une édition qui en réunit 40 : « les rangs 33 et
suivants » ne prélève personne. Le moteur **refuse** de monter un tableau (`EffectifTableauInvalide`)
plutôt que d'inventer une population — retomber sur « tous les archers en lice » ressusciterait
exactement le défaut que cette US corrige.

Mais le refus arrive **trop tard** : sur la tablette, en pleine compétition. Arbitrage du
commanditaire (03/08/2026) : *« les inscrits sont connus au lancement, donc on ne peut pas lancer un
tournoi qui n'a pas assez d'inscrits pour son format ; le logiciel doit connaître la fourchette basse
et avertir l'admin avant de lancer. On bascule sur un autre format. »*

Le refus du moteur reste donc comme **dernier garde-fou** — un tournoi dans cet état ne devrait plus
pouvoir être lancé — et le contrôle qui l'empêchera d'arriver fait l'objet d'une **US dédiée** :
un format connaît son effectif minimum, et le lancement le vérifie contre les inscrits réels.

## Conséquences

- **Ce qui devient vrai** : le tournoi se déroule comme le schéma composé. Un format déclarant « les
  rangs 1 à 32 » monte un tableau de 32, quel que soit le nombre d'inscrits.
- **Le test de caractérisation d'E01US024 a échoué**, comme il avait été écrit pour le faire, et il
  est remplacé par son pendant positif (`test_la_simulation_ne_signale_plus_d_ecart_sur_un_prelevement_par_rangs`).
  C'est la meilleure preuve qu'un test de caractérisation vaut la peine d'être écrit : il a survécu
  deux US et signalé lui-même le moment de sa retraite.
- **La réserve permanente de l'écran de composition** (« le moteur ne lit pas encore les
  prélèvements ») n'est plus vraie **pour les rangs** ; elle reste vraie pour `le_reste` et les
  issues de tour. Elle est reformulée, pas supprimée.
- **`DETTE-034` est soldée** (§5) — par l'US même qui l'avait rendue atteignable.
- **`E05US021` est ouverte** (§6) : un format connaît son effectif minimum, et le lancement le
  vérifie contre les inscrits réels.
- **`DETTE-028` rétrécit fortement** sans disparaître : la consommation des sources par rangs est
  faite, mais les réglages (`nb_poules`, `nb_manches`…) restent inexprimables en `config.policies`,
  `classement.py` ne passe toujours pas par la famille `scoring`, et `poule`/`suisse`/`colline`/
  `big_shoot_off` n'ont toujours aucun consommateur.

## Porté dans le code par

> *Section ajoutée le 08/08/2026 (rétro-équipement des ADR structurants encore actifs). La règle
> « un ADR nomme les modules qui le portent » a été instituée le 06/08/2026 par
> [ADR-0075](0075-le-depart-est-la-portee-sportive.md) et n'avait pas été appliquée rétroactivement.
> Les modules ci-dessous ont été **vérifiés dans le code du jour**, pas déduits de l'ADR — nommer un
> module vide reproduirait exactement le défaut que la section existe pour empêcher.*

- `backend/application/prelevement.py` — `preleves()` filtre le classement de la source sur les
  intervalles déclarés ; `tranche()` calcule l'effectif prélevé ; `profondeur_de()` résout la
  profondeur. C'est le module central de cet ADR.
- `backend/domain/phase.py` — `SourcePhase.intervalle(effectif_source)`, qui **résout la fin
  ouverte** sur l'effectif réel (« les rangs 33 et suivants » vaut 88 à 120 classés, 50 à 82). La
  sémantique est dans le **domaine** : le service la consomme, il ne la réécrit pas.
- `backend/application/saisie_duels.py` — le décor de phase, qui applique le prélèvement au
  peuplement effectif.

Le cas « une phase **sans** source reste alimentée par les inscriptions » est porté par le même
chemin : c'est l'absence de `phase.sources` qui le déclenche, pas un drapeau. ⚠️ La portée de cet
ADR a été **élargie deux fois depuis** — par [ADR-0080](0080-un-prelevement-lit-le-classement-de-sa-phase-source.md)
(la source n'est plus forcément la qualification) et [ADR-0081](0081-une-phase-attend-que-sa-source-ait-departage-les-places-qu-elle-preleve.md)
(une fenêtre coupant un bloc indécis est **refusée**). Le lire seul donnerait une image de 2026-08-01.
