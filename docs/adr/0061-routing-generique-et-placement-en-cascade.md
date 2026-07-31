# ADR-0061 — Le routing devient générique, et l'élimination directe n'est qu'un placement tronqué

- **Statut** : Accepté
- **Date** : 2026-07-31
- **Décideurs** : Organisateur / Architecte
- **Portée** : E05US010 (placement intégral 1→N, sources multiples, oracle 120)
- **Lie** : [ADR-0004](0004-moteur-de-phases-politiques.md) (les six familles de politiques, dont
  cet ADR honore la signature `route(perdant, tour, contexte)`),
  [ADR-0045](0045-sequence-de-phases-cycle-de-vie-typage-source.md) (la séquence de phases et son
  peuplement, ici élargi), [ADR-0049](0049-tableau-reconstruit-plutot-que-persiste.md) (le tableau
  est reconstruit — la raison pour laquelle le routage se décide à la construction),
  [ADR-0060](0060-briques-du-patrimoine-du-club-bibliotheque-copie-promotion.md) (la seconde table
  à migrer), [DETTE-015](../dette.md#dette-015--modèle-de-source-de-phase-minimal-et-provisoire)
  (résorbée)
- **Source métier** : [`moteur-placement-lucky-loser.md`](../../moteur-placement-lucky-loser.md)
  (Règles R et T, décisions Q1-Q6 du 08/07/2026)

## Contexte et problème

Le moteur livré par E05US005 sait dérouler un tableau à élimination directe et rendre un podium à
quatre places. Le format que le club tire réellement — celui du classeur `Tableaux.xlsx`, 120 archers
et 484 matchs — ne classe pas quatre archers mais **cent vingt** : personne n'y est éliminé, chaque
perdant descend dans un tableau de placement confiné aux rangs qu'il peut encore atteindre.

Le verrou n'était pas le catalogue de types de phase mais le **routing**. `DestinationPerdant`
n'avait qu'une valeur, `ELIMINE`, et `Routing.destination_du_perdant()` ne prenait **aucun
argument** : une méthode sans paramètres ne peut rendre qu'une réponse constante, donc ne peut pas
exprimer « la moitié basse de *ta* plage ». Tout ce qui n'est pas élimination sèche — placement,
repêchage, consolation, non-qualifiés de poule — en dépendait.

Deuxième problème, indépendant en apparence : une phase ne pouvait se peupler que d'**une** source,
« les rangs N→M d'une phase antérieure ». Le commanditaire a demandé deux choses le 31/07/2026 —
plusieurs sources de natures différentes (« les demi-finalistes du tableau principal, **et** le
gagnant du tableau secondaire ») et des prélèvements **relatifs** (« que le format s'ajuste si j'ai
prévu 120 archers et qu'il n'y en a que 82 »). Le classeur en donne d'ailleurs l'exemple : sa Grande
Finale est alimentée par les vainqueurs des quarts *et* par un « Lucky-Looser ».

## Décision

### 1. `Routing` dit *où*, `Depth` dit *jusqu'où*

`Routing.destination_du_perdant()` est ressignée en `route(contexte) -> Destination`, comme
ADR-0004 l'annonçait et comme `politiques.py` le prévoyait explicitement (« rupture bon marché, un
implémenteur, aucun consommateur »). Deux destinations : `HorsTableau` et `VersPlage(plage)` ; le
repêchage World Archery (E05US015) en ajoutera une troisième sans toucher aux deux premières.

La **profondeur** décide séparément jusqu'où descendre : un sous-tableau n'est engendré que si sa
plage contient encore un rang à classer. Cette séparation est ce qui rend le moteur générique — le
routing exprime la *mécanique* du format, la profondeur son *ambition*.

### 2. L'élimination directe livrée **est** un placement tronqué au rang 4

C'est la découverte de conception de cette US, et elle a changé la solution. Le tableau que le
produit livre depuis E05US005 a une **petite finale** : les perdants des demi-finales rejouent. Ils
ne sont donc pas éliminés — ce format n'est pas une élimination sèche, c'est un placement dont la
cascade s'arrête au rang 4.

Conséquence : la génération de l'arbre devient une **récursion sur les plages de rangs**, dont
l'élimination directe est le cas particulier.

```
engendrer(camps, plage, tour) :
    créer len(camps)/2 matchs
    si plage.largeur == 2 → matchs terminaux (Règle T), fin
    sinon :
        engendrer(vainqueurs, plage.moitié_haute)   si des rangs y restent à classer
        engendrer(perdants,  routing.route(…))      si des rangs y restent à classer
```

Avec `ProfondeurPodium(4)`, cette récursion produit **exactement** l'arbre d'avant l'US — mêmes
matchs, même numérotation, et la petite finale *est* le sous-groupe des perdants des demies. La
non-régression est donc structurelle et non plaquée : c'est le même algorithme qui rend les deux
formats. Avec `ProfondeurUnVersN`, elle produit le placement intégral 1→N.

La composition root injecte désormais `PlacementEnCascade` là où elle injectait `EliminationSeche`
— le vocabulaire se met en accord avec le comportement, l'arbre ne change pas. `EliminationSeche`
reste au catalogue pour le tableau **vraiment** sec, sans aucun match de classement (Q6).

### 3. Le routage se décide à la **construction**, pas à chaque match joué

ADR-0004 écrit `route(perdant, tour, contexte)`. Le contexte retenu (`ContexteRoutage`) porte le
tour et la plage, mais **pas le perdant** : au moment où l'arbre est câblé, aucun participant n'est
connu — `PerdantDe(m)` est une arête, pas une personne.

C'est un écart **assumé** à la lettre d'ADR-0004, et il découle d'ADR-0049 : le tableau est
*reconstruit* depuis les résultats, jamais persisté. Si le routage dépendait du perdant lui-même, la
structure de l'arbre dépendrait de l'ordre dans lequel les résultats sont tombés — deux
reconstructions du même tournoi pourraient différer. En décidant à la construction, la structure ne
dépend que des politiques ; les résultats ne font que la peupler. `jouer()` ne consulte donc plus le
routing du tout, et la mécanique de propagation existante (`_propager`) n'a pas eu à changer : elle
savait déjà reporter un perdant dans un camp arbitraire.

### 4. Un `SourcePhase` discriminé par `nature`, plutôt qu'une union de trois types

Une phase porte désormais `sources: tuple[SourcePhase, ...]`. Chaque prélèvement a une **nature** —
`rangs` (fin ouverte possible : « 33 et suivants »), `issue_de_tour` (gagnants/perdants du tour X),
`reste` (ce qu'aucune autre n'a pris).

L'alternative — une union `ParRangs | ParIssueDeTour | LeReste` — serait plus étanche : chaque
variante ne porterait que ses champs. Elle a été **écartée** parce que `SourcePhase(ordre_source=…,
rang_debut=…, rang_fin=…)` est construit dans une trentaine d'endroits et que le prélèvement par
rangs reste le cas courant : le discriminant garde ces constructions valides telles quelles. Le prix
est un value object plus large, payé par une validation stricte à la construction (un champ étranger
à la nature lève `SourceMalFormee` — jamais un champ ignoré en silence, qui serait un réglage que
l'organisateur croit avoir posé).

### 5. Le contrôle de somme cède devant les plages relatives

Le contrôle « la source prélève exactement l'effectif déclaré » ne s'applique plus que si **tous**
les prélèvements sont dénombrables au format. Dès qu'un seul est relatif (fin ouverte, « le reste »,
issue de tour), le compte ne se connaît qu'à l'exécution.

Ce n'est pas un relâchement : c'est la condition d'existence des plages relatives, et le CA le dit
pour l'autre bout du problème — un format devenu infaisable à effectif réduit (« les 32 premiers »
avec 20 inscrits) n'est **pas** une erreur de format à corriger, c'est une **anomalie à afficher**
(E01US024). L'invariant se déplace du format vers l'exécution parce que c'est là qu'il est
décidable.

## Conséquences

**Positives.** Le moteur sait produire un classement 1→N vérifié contre un tournoi réel. Le
repêchage (E05US015) devient une destination de plus, pas un moteur de plus. La profondeur est un
levier prêt : passer un tableau existant au placement intégral se fait en changeant une politique,
sans toucher au moteur — c'est ce qu'E01US024 exposera à l'organisateur, phase par phase.

**Coûts.** Une migration de données sur **deux** tables (`phase.config` et `format_tournoi.config`),
dont la seconde est facile à oublier. Le `downgrade` est **partiel et assumé** : une phase à
plusieurs sources n'a pas de représentation dans l'ancienne forme, la migration la laisse en l'état
plutôt que d'en perdre une moitié en silence. Un consommateur du domaine (`Phase.source` →
`Phase.sources`) a dû être repris partout, DTO et front compris.

**Limites connues, à ne pas confondre avec des oublis.**

- **L'oracle 120 ne couvre pas les rangs 1 à 4.** Le sommet du classeur n'est pas une élimination
  directe : la Grande Finale s'y tire en **Big Shoot Off** à dix archers, qui produit d'un coup les
  rangs 1 à 10. Le BSO est un type de phase d'E05US015 ; le classeur ne contient donc aucune finale
  d'élimination à comparer. L'oracle porte sur les rangs **5 à 120** (58 matchs terminaux) et le
  déclare.
- **L'écran « Phases » n'édite qu'un seul prélèvement**, « par rangs ». La composition riche est
  E01US024. Une phase hors de ce cas y est affichée en **lecture seule** : la soumettre avec le
  formulaire mono-source écraserait sa composition sans le dire.
- **Les natures `issue_de_tour` et `reste` sont modélisées, persistées et exposées, mais aucun
  moteur ne les consomme encore** — le peuplement effectif d'une phase par ses sources est le
  travail d'E01US024/E07US004. Elles sont livrées ici parce que le **modèle** est ce qui bloquait,
  et parce que les livrer plus tard aurait imposé une **seconde** migration double table.

## Alternatives écartées

- **Router à l'exécution** (`jouer` consulte le routing) : rompt la reconstructibilité (ADR-0049) et
  rend l'arbre dépendant de l'ordre de saisie. Écarté pour cette raison, pas par commodité.
- **Un moteur de placement distinct du moteur d'élimination** : deux algorithmes à tester, deux
  chemins à faire diverger, alors que le second est mathématiquement un cas du premier. La démarche
  inverse — chercher ce qui les unifie — a produit un moteur plus court que celui qu'il remplace.
- **Garder `podium()` comme seule sortie et lui ajouter des rangs** : `podium()` a une sémantique de
  tout-ou-rien (rien tant que la finale n'est pas jouée) que ses consommateurs utilisent. On a donc
  ajouté `classement()` (au fil de l'eau, 1→N) et laissé `podium()` en vue restreinte.
