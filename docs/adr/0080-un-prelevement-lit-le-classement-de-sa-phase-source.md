# ADR-0080 — Un prélèvement lit le classement de **sa** phase source

- **Statut** : Accepté
- **Date** : 2026-08-08
- **Décideurs** : Organisateur / Architecte
- **Portée** : E05US024 (le moteur peuple depuis n'importe quelle phase classante)
- **Complète** : [ADR-0068](0068-le-moteur-consomme-les-prelevements-declares.md) — qui a fait
  consommer les prélèvements visant la **qualification**, et laissé les autres au comportement
  d'avant. Cet ADR lève cette restriction et **retire** la justification qu'ADR-0068 en donnait.
- **Lie** : [ADR-0061](0061-routing-generique-et-placement-en-cascade.md) (les sources multiples,
  sans lesquelles rien de ceci n'était exprimable), [ADR-0065](0065-rang-acquis-lu-sur-la-plage-et-issue-repechee.md)
  (*Règle R* — les fourchettes de rangs qu'un tableau décerne),
  [ADR-0067](0067-palmares-agregation-des-rangs-de-phases.md) (la politique `aggregation`, ici
  réemployée telle quelle), [ADR-0075](0075-le-depart-est-la-portee-sportive.md) (tout se lit
  **dans un créneau**)
- **Source métier** : arbitrage du commanditaire du **08/08/2026**, au cadrage d'E16US002 — « *la
  création du déroulé doit permettre de composer les phases comme on en a envie, le club est libre
  de son format de tournoi* ».

## Contexte et problème

Le modèle de composition était **déjà générique** : une phase en tête de déroulé prend les inscrits,
toute phase en aval prend ce que ses `sources` déclarent, et rien dans ce mécanisme ne regarde le
*type* de la phase. L'organisateur pouvait donc composer « les rangs 1 à 8 de mes poules », l'écran
l'acceptait et le diagnostic le validait.

**Le moteur d'exécution, lui, ne lisait qu'un seul classement : celui de la qualification.**
`application/prelevement.py:preleves` recevait un `ordre_qualification` et ne retenait que les
sources le visant ; toutes les autres étaient **ignorées en silence**, la phase retombant sur *tous*
les archers en lice. Un tableau bien formé, plausible, et faux — que rien ne signalait avant la
salle. Le registre le disait sans détour (`DETTE-028`) : « une source dont la phase amont **n'est pas
la qualification** garde le comportement d'avant ».

Deux conséquences, dont la seconde n'est pas intuitive :

1. **Les formats en cascade étaient inaccessibles** — poules → tableau, tableau → consolante,
   qualification → qualification restreinte. Toute la richesse qu'ADR-0061 avait rendue *exprimable*
   restait *inexécutable*.
2. **L'unicité de la qualification était le pansement de ce raccourci.**
   `_anomalies_unicite_qualification` (E05US021) interdit plus d'une phase de qualification par
   séquence ; sa propre docstring la présente comme un invariant « **supposé partout et vérifié
   nulle part** », posé après que deux lecteurs de « **la** » qualification l'eurent résolue
   différemment. Ce n'est pas une règle du tir à l'arc : c'est une porte fermée pour que le raccourci
   ne se voie pas.

**Le motif de report d'ADR-0068 ne tenait plus.** Il invoquait un cycle : « lire le classement d'un
tableau amont demande la lecture d'E06US004 et créerait un cycle service → service ». Vérifié le
08/08/2026 — `palmares.py` importe bien `ServiceSaisieDuels`, donc l'inverse fermerait la boucle,
mais la lecture nécessaire (`tableau.positions_acquises()`) est produite par `ServiceSaisieDuels`
**lui-même**. Il n'y a donc pas de cycle de modules : il y a une **récursion** d'un service sur
lui-même. La note était exacte quand elle a été écrite (E06US004 n'était pas livrée) ; elle ne
l'était plus.

## Décision

**Chaque prélèvement est résolu dans le classement de la phase qu'il désigne.**

### 1. `preleves` reçoit un résolveur, pas un ordre privilégié

La signature passe de `preleves(phase, classement, ordre_qualification)` à
`preleves(phase, classement, resoudre_source)`, où `resoudre_source: Callable[[int], Classement |
None]`. Un **résolveur** et non une table pré-calculée : résoudre un tableau amont coûte une
reconstruction complète, on ne la paie donc que pour les ordres réellement déclarés en source.

`tranche` (ADR-0068 §5) suit la même règle, et pour la même raison : un décalage calculé sur une
autre base que celle qui a peuplé le tableau situerait ses positions dans le mauvais espace de rangs
— c'était `DETTE-034`.

### 2. Un tableau se lit comme un classement, et les *ex æquo* se ferment par `aggregation`

`domain/classement_de_tableau.py` (fonction **pure**) transforme un `Tableau` en `Classement` :
mêmes lignes d'archers, seul `rang_scratch` est réécrit sur ce que le tableau a décerné.

Un tableau ne rend pas que des rangs exacts : les quatre battus des quarts d'un tableau de 8 sortent
tous sur `[5..8]` (*Règle R*, ADR-0065). Fermer ces fourchettes est exactement ce que la politique
`aggregation` sait faire (ADR-0067) — c'est **elle** qu'on appelle. Écrire un départage local aurait
produit un ordre que le palmarès affiché au mur aurait contredit le même jour, sur le même écran.

⚠️ **`en_lice` n'entre pas dans l'ordre**, délibérément. Deux archers qui vont tirer la finale sont
`[1..2]` tous les deux ; les départager ici sur leur rang de qualification décernerait l'or **avant**
que la finale ne soit tirée — le défaut exact qu'ADR-0067 a corrigé. Ils reçoivent donc des rangs
consécutifs *provisoires*, et une phase aval qui prélève « les rangs 1 à 2 » les prend **tous les
deux**, ce qui est la bonne réponse : elle veut les deux finalistes.

### 3. La résolution est récursive, sur un graphe acyclique

`ServiceSaisieDuels._classement_de_l_ordre` rend, pour un ordre donné : le classement de tir s'il
s'agit d'une **qualification**, l'arbre reconstruit et relu s'il s'agit d'une **élimination
directe**, et **`None`** pour tout autre type — poules, suisse, colline et Big Shoot Off n'ont aucun
classement lisible tant qu'`E05US023` ne les rend pas jouables (`DETTE-028`). Rendre `None` fait
retomber la phase sur son comportement d'avant : le prélèvement reste **inerte**, jamais **faux**.

La terminaison ne repose pas sur un compteur mais sur un **invariant** : une source est toujours
**antérieure** (ADR-0045 §3, vérifié par `verifier_sequence`), donc l'ordre décroît strictement à
chaque descente. Une garde refuse néanmoins une chaîne qui boucle — inatteignable par la composition,
atteignable par une base incohérente (import, migration à la main). Un refus typé dit la cause ; un
`RecursionError` remonterait en 500 muet, un jour de compétition.

### 4. Le plancher d'inscrits remonte la chaîne

`effectif_minimum` (E05US021) traduisait un rang en nombre d'inscrits en ne reconnaissant que la
qualification. Il **remonte** désormais la chaîne des sources jusqu'à la phase alimentée par les
inscriptions : « les rangs 5 et suivants d'un tableau qui prend les rangs 17 à 32 de la
qualification » réclame **22** inscrits, pas 6. Le décalage se cumule.

Le plancher garde son oracle — *« viser exactement ce que le moteur lira »* — et c'est ce qui impose
`_TYPES_CLASSANTS_LUS`, **miroir explicite** de `_classement_de_l_ordre` : ce que le service résout,
on l'exige ; ce qu'il rend `None`, on ne l'exige pas. Les faire diverger rouvrirait le défaut
symétrique qu'E05US021 a corrigé — soit un plancher réclamé pour un prélèvement que rien n'honore
(**refus abusif** le jour J, le pire mode de défaillance), soit un plancher tu pour un prélèvement
que le moteur lira (le tournoi démarre puis casse en salle).

Nouveau cas, absent avant : une source dont la fenêtre est **bornée** plafonne ce que sa phase peut
classer. « Les rangs 33 et suivants d'un tableau qui prend les rangs 1 à 32 » est infaisable à 34
inscrits comme à 400 — c'est un **défaut de composition**, que le diagnostic signale, et non un
plancher. Le calcul rend alors « pas d'exigence » plutôt qu'un chiffre rassurant et faux.

### 5. Le plan de cibles emprunte la résolution, il ne la réimplémente pas

`ServicePlacementDuels` reçoit `ServiceSaisieDuels` en dépendance — **pas pour saisir**, uniquement
pour lui emprunter `resolveur_de_classement`. Reconstruire un tableau source est le métier de la
saisie, pas celui du plan.

C'est la raison d'être d'`application/prelevement.py`, et la leçon d'E05US020 : la règle y avait été
**recopiée** aux deux endroits avec un commentaire affirmant leur parité, et la recopie a lâché à la
première évolution — plan de 8 placements pour un tableau de 4, soit un archer posté sur une butte
sans duel et un autre en face du mauvais adversaire. Deux résolutions distinctes rouvriraient
exactement cela, un cran plus loin dans la chaîne.

Le sens de dépendance est sûr : `saisie_duels` ne connaît pas le placement, et `palmares` emprunte
déjà ce chemin. Corollaire au composition root : **la saisie se construit avant le plan**.

## Ce que cet ADR ne tranche pas

- **Plusieurs qualifications dans un déroulé** reste interdit (`_anomalies_unicite_qualification`).
  C'est le sujet d'**E05US025**, qui ne pouvait pas passer devant : sans la lecture générique livrée
  ici, une seconde qualification aurait reçu *tous* les inscrits. Ce qui reste à faire là-bas n'est
  pas le peuplement mais les **lecteurs** — `ServiceBaremeQualification` est bâti de bout en bout sur
  « **le** barème du tournoi », et les 12 appels de `portee.qualification_du_tournoi` sont à trier un
  par un.
- **`le_reste` et `par_issue_de_tour` restent inertes** (`DETTE-033`). Cet ADR élargit **quelle
  phase** on lit, pas **quelles natures** on sait résoudre. Leur donner un sens dans un service
  d'exécution serait décider une règle métier au mauvais endroit — l'erreur qu'ADR-0065 §3 a refusé
  de commettre.
- **Le coût d'exécution.** `DETTE-031` signale déjà que `reconstruire` rebâtit tout le classement du
  tournoi **une fois par phase à tableau**, sans cache ni plafond, sur deux routes publiques non
  authentifiées. La récursion **multiplie** ces reconstructions par la profondeur de la cascade. La
  résolution est mémoïsée **par appel** ; le cache transverse reste `DETTE-031`, non rouvert ici.
- **La capacité d'une phase à sources multiples** est mesurée sur la source la plus basse, pas sur
  leur somme — une sous-estimation, donc un plancher **tu** plutôt qu'un refus indu. Le sens sûr, à
  resserrer le jour où un déroulé réel en souffre.

## Conséquences

**Positives**

- **Le club est libre de son format**, au sens fort : ce que l'écran laisse composer, la salle le
  joue. La promesse d'E01US024 (« le tournoi se déroule comme le schéma que j'ai composé et validé »)
  cesse de s'arrêter à la première phase.
- **Un défaut silencieux devient impossible** : un prélèvement est désormais honoré ou inerte, jamais
  appliqué au mauvais classement. C'était la classe de bugs la plus coûteuse — plausible, non
  signalée, découverte le jour J.
- **Le plancher d'inscrits dit enfin la vérité sur les cascades**, là où il annonçait le minimum
  structurel (2) pour des déroulés qui en réclamaient vingt.

**Coûteuses / à surveiller**

- **Deux tests de caractérisation sont tombés**, et c'était le signal attendu — comme E05US020 avait
  fait tomber le sien. `test_une_source_qui_ne_vise_pas_la_qualification_est_ignoree` était faux
  **deux fois** : il figeait le repli silencieux, et son décor déclarait une source d'ordre 2 sur la
  phase d'ordre 2 — une phase se prélevant **elle-même**, que `verifier_sequence` n'aurait jamais
  laissé composer. Il passait donc pour la mauvaise raison. À retenir : *un test de caractérisation
  peut protéger un comportement que la composition ne peut même pas produire.*
- **`ServicePlacementDuels` dépend maintenant d'un service**, non plus seulement de ports. C'est un
  écart au patron dominant, assumé : l'alternative était de dupliquer la reconstruction d'arbre, ce
  que le module partagé existe précisément pour empêcher. À rouvrir si un troisième consommateur
  apparaît — le remède serait alors un port `ClassementDePhase` dans le domaine.
- **La récursion rend le coût de lecture non borné par la structure**, seulement par la profondeur du
  déroulé composé. Aucun format réel du club ne dépasse deux ou trois crans, mais rien ne l'impose.

## Porté dans le code par

- `backend/domain/classement_de_tableau.py` — `classement_de_tableau`, la lecture d'un tableau comme
  classement (fonction pure, `aggregation` injectée)
- `backend/application/prelevement.py` — `ResolveurClassement`, `preleves` et `tranche` : la règle
  **partagée** par les deux services de tableau
- `backend/application/saisie_duels.py` — `resolveur_de_classement` (exposé pour le plan de cibles)
  et `_classement_de_l_ordre` (les trois cas + la garde de boucle) ; `_decor` porte la chaîne en
  cours de descente
- `backend/application/placement_duels.py` — emprunte le résolveur de la saisie
- `backend/application/palmares.py` — `tranche` sur le même résolveur que l'ensemencement
- `backend/domain/deroule.py` — `_TYPES_CLASSANTS_LUS`, `_source_lisible` et `_inscrits_pour_classer`
  (le plancher qui remonte la chaîne, et le plafond des fenêtres bornées)
- `backend/bootstrap/composition.py` — la saisie construite **avant** le plan, aux deux points de
  câblage (application réelle et harnais de simulation)
- `backend/tests/test_prelevement_phase_source.py` (les CA de l'US),
  `backend/tests/test_domain_effectif_minimum.py` (la chaîne du plancher)
