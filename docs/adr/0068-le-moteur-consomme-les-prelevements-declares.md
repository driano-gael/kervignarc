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

⚠️ **L'effectif source compte les archers *classés*, pas les inscrits.** Un disqualifié n'a pas de
rang (ADR-0050) ; le compter étendrait « et suivants » jusqu'à un rang qui n'existe pas — la même
erreur que l'écrêtage d'ADR-0065 a corrigée sur les plages de tableau, au même endroit conceptuel.

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
- **`DETTE-028` rétrécit fortement** sans disparaître : la consommation des sources par rangs est
  faite, mais les réglages (`nb_poules`, `nb_manches`…) restent inexprimables en `config.policies`,
  `classement.py` ne passe toujours pas par la famille `scoring`, et `poule`/`suisse`/`colline`/
  `big_shoot_off` n'ont toujours aucun consommateur.
