# ADR-0062 — Un type de phase se justifie par une structure, pas par un réglage

- **Statut** : Accepté
- **Date** : 2026-07-31
- **Décideurs** : Organisateur / Architecte
- **Portée** : E05US015 (catalogue de types de phase — échauffement, barrage, poules, Big Shoot Off,
  système suisse, colline, repêchage, handicap, finale spectacle)
- **Lie** : [ADR-0004](0004-moteur-de-phases-politiques.md) (les six familles de politiques, dont
  cet ADR peuple le catalogue), [ADR-0045](0045-sequence-de-phases-cycle-de-vie-typage-source.md)
  (§2 : « on n'offre pas en façade un type qu'aucun moteur ne sait dérouler » — la contrainte que
  cet ADR honore), [ADR-0046](0046-config-policies-politiques-nommees-parametrees.md) (la forme
  `{"nom": …, …params}`, ici exercée par la première politique **composite**),
  [ADR-0061](0061-routing-generique-et-placement-en-cascade.md) (le routing générique et les sources
  multiples, sans lesquels rien de ceci n'était exprimable)
- **Source métier** : règles fournies par le commanditaire le **31/07/2026** (poules, Big Shoot Off,
  échauffement, handicap, système suisse, King of the Hill, Ladder, finale spectacle), consignées au
  [référentiel §10.1](../referentiel-ffta.md) ; barrage au **règlement fédéral** (art. B.6.5.2,
  [référentiel §8.2](../referentiel-ffta.md)).

## Contexte et problème

L'application ne savait dérouler que trois types de phase : `qualification`, `elimination_directe`,
`placement`. Le cahier des charges en réclamait bien davantage (EF-3.1, EF-3.2), et la raison pour
laquelle ils n'étaient pas livrés n'était pas technique : **leur règle n'était écrite nulle part**.
La question Q9 — « qu'est-ce qu'un Big Shoot Off ? » — bloquait le projet depuis son origine.

Le cadrage du 31/07/2026 a levé ce blocage d'un coup : le commanditaire a fourni, verbatim, les
règles des poules, du Big Shoot Off, de l'échauffement, du handicap, du système suisse, du King of
the Hill, du Ladder et de la finale spectacle. Rien ne s'opposait plus à peupler le catalogue.

Restait la vraie question de conception, que la liste du cahier des charges masquait : **est-ce que
tout ce que cette liste énumère est un type de phase ?** Elle mélange en effet des choses de nature
très différente — un *format de tournoi* (poules), une *façon de compter les points* (handicap), une
*destination de perdant* (repêchage), une *mise en scène* (finale spectacle). Les traiter
uniformément comme des `TypePhase` aurait été le chemin le plus court, et le mauvais.

## Décision

### 1. Le critère : une structure propre, pas un réglage

**Un type de phase se justifie par une structure d'appariement et de progression qui lui est
propre.** Ce qui ne fait que régler une structure existante est une **politique** (ADR-0004) ou un
**paramètre**, jamais un type.

Appliqué à la liste, le critère la coupe en trois :

| Ce que le CDC énumère | Ce que c'est réellement | Où ça vit |
|---|---|---|
| échauffement, barrage, poules, Big Shoot Off, système suisse, colline | **types** — structure propre | `TypePhase` + un moteur de domaine |
| repêchage | **politique `routing`** — décide où va un perdant | `RoutingRepechage` |
| handicap | **politique `scoring`** — décide comment se calcule un score | `ScoreAvecHandicap` |
| finale spectacle, finale, tournoi des perdants, podium | **compositions** — assemblages de briques existantes | configuration seule |

Trois conséquences valent d'être nommées, parce qu'elles ne sont pas intuitives :

- Le **repêchage** ressemble à un type (le classeur du club a « un tableau de repêchage ») mais n'en
  est pas un : la phase qui accueille les repêchés est une élimination directe ordinaire, alimentée
  par un prélèvement `issue_de_tour/perdants` (ADR-0061). Ce que le repêchage ajoute vraiment, c'est
  **une décision sur le perdant en amont** — qu'il sorte du tableau sans y consommer de rang.
- Le **handicap** ne change ni l'arbre, ni le peuplement, ni le classement : uniquement l'arithmétique
  du score. Lui donner un type aurait dupliqué la qualification.
- Le **podium** n'est pas une phase du tout, c'est la **sortie** de la phase terminale. Aucun
  `TypePhase` ne s'appelle « podium », et c'est délibéré.

### 2. King of the Hill et Ladder sont **un seul** moteur

Les deux règles sont décrites séparément par le commanditaire et se ressemblent au point qu'il le
signale lui-même (« très proche du King of the Hill »). Leur différence tient en un nombre : la
**portée du défi** — un rang au-dessus, ou deux. C'est donc un paramètre (règle 2), et le type
s'appelle `colline`, pas `king_of_the_hill`.

**Deux arbitrages ont été nécessaires** pour qu'ils rentrent dans le modèle :

- **Version « journée », pas classement permanent.** Les règles décrivent un classement qui « évolue
  toute l'année » et des défis lancés au fil de l'eau. Une `Phase` kervignarc a des sources, un
  effectif, un début et une fin **dans un tournoi** : un ladder de saison ne s'y modélise pas. Le
  commanditaire a tranché pour la variante de journée (ordre initial = classement source, nombre de
  manches réglé à la composition, classement final = la colline). Le classement permanent de club
  reste un autre produit — c'est tracé, pas implémenté.
- **Mécanique « deux voisins s'affrontent »**, la seconde des deux que la règle du King of the Hill
  propose. Retenue parce qu'elle fait jouer tout le monde à chaque manche, là où « tous défient le
  King » n'occupe que deux archers.

⚠️ **Écart signalé, non arbitré seul** : l'exemple chiffré du Ladder ne concorde pas avec sa propre
règle (voir « Ce que cet ADR ne tranche pas »).

### 3. `Scoring` est ressignée pour recevoir un contexte

`Scoring.total(points_par_volee)` ne pouvait rendre qu'une fonction des seules volées. Un handicap
est une donnée **du tireur** : la méthode devient `total(points_par_volee, contexte)` avec un
`ContexteScore`, pendant du `ContexteRoutage` d'ADR-0061.

C'est exactement la rupture que `politiques.py` annonçait comme prévue et bon marché — et elle l'a
été : **aucun appelant de production** n'existait encore. Le sur-gel que DETTE-003 mettait en garde
d'éviter aurait consisté à figer dès E05US003 une signature spéculative « au cas où » ; on a préféré
livrer étroit et payer la rupture quand le besoin est arrivé. Le pari est tenu pour la seconde fois
(la première étant le `routing`, ADR-0061).

### 4. `DecompteDepartage` s'élargit par champs facultatifs

Le départage de poule compte **cinq** critères (points de match, différence de sets, différence de
score, 10, 9) là où la qualification en compte deux (§8.1). Le CA désignait cet élargissement comme
« la rupture de contrat la plus risquée de l'US », `TiebreakFftaDefaut` et `classement.py` en étant
consommateurs.

Elle se réduit à **trois champs à défaut `0`** : les constructions existantes restent valides, et
l'ordre des critères vit dans la **politique** (`TiebreakFftaDefaut` vs `TiebreakPoules`), pas dans
le décompte. Corollaire à connaître : un décompte de qualification comparé par `TiebreakPoules` a ses
trois premiers critères nuls, donc retombe sur §8.1 — dégradation silencieuse mais **juste**.

### 5. Le repêchage **décore** un routing, il ne le remplace pas

`RoutingRepechage(tours_repeches, sinon)` délègue à une autre politique tous les tours qu'il ne
repêche pas. Sans ce `sinon`, il aurait fallu choisir entre « repêcher » et « classer » — or le
format réel du club fait **les deux** dans le même tableau : le « Lucky-Looser » (gagnant de M427)
remonte disputer le titre, et tous les autres battus descendent se classer.

C'est la **première politique composite** du registre, donc la première dont la fabrique doit
résoudre un nom à son tour. Sa fabrique est **fermée sur le registre en construction** plutôt que
d'élargir la signature `Fabrique` de toutes les autres pour le besoin d'une seule.

### 6. Aucune table de handicap n'entre dans le produit

Le commanditaire souhaitait un handicap « officiel ». **Le projet n'en possède aucune table** : la
FFTA n'a pas de système de handicap officiel, et celui qui fait référence est anglo-saxon
(Archery GB / World Archery). En reconstituer une aurait produit des classements **plausibles mais
faux** — le pire des défauts, puisqu'il ne se voit pas.

Décision, prise avec le commanditaire : l'archer porte **deux valeurs** — un `handicap_officiel`
(entretenu par le club, saisi ou importé) et une `handicap_surcharge` qui le prime pour cette
édition. Le produit fournit le **mécanisme** ; le club répond de la **valeur**. C'est cohérent avec
le point faible que la règle reconnaît elle-même : « le calcul du handicap doit être fiable ».

## Conséquences

**Positives.**

- Le catalogue couvre la séquence d'exemple d'EF-3.1 de bout en bout — un test de recette le fige
  (`test_catalogue_types_de_phase.py`).
- Q9 est **fermée**. Elle bloquait le projet depuis l'origine.
- Le `barrage` est un **module unique servant trois usages** (phase autonome, égalité au plus faible
  d'un Big Shoot Off, ex æquo de poule). Les trois appellent `resoudre_barrage` et appliquent son
  verdict ; aucun ne le réimplémente.
- Les six moteurs sont **purs et déterministes** : aucun aléa, donc chaque phase est rejouable à
  l'identique après un incident le jour J (règle 9).

**Négatives, ou à surveiller.**

- **Le catalogue est large, et l'usage réel ne l'est pas.** Six types neufs, dont plusieurs que le
  club n'a peut-être jamais tirés. Un type non utilisé est du code non éprouvé : les moteurs sont
  couverts par leurs tests unitaires, pas par une journée réelle.
- **L'appariement du système suisse est glouton, pas optimal.** Il peut échouer à trouver un
  appariement sans ré-affrontement là où il en existait un. Il lève alors une erreur explicite plutôt
  que de rejouer une rencontre en silence. Un couplage de poids maximal (l'algorithme FIDE) est un
  algorithme de graphe entier pour un gain qui, à l'échelle d'un club, ne se verra pas.
- **Une troncature de round-robin à effectif impair ne donne pas le même nombre de rencontres à
  tout le monde** (écart d'une unité). Signalé dans le module plutôt que corrigé en douce : aucune
  correction n'est neutre.
- **Un tableau à repêchage dont la composition oublie la phase de repêchage perd ses battus en
  silence.** Le moteur ne peut pas le détecter — un tableau amputé de sa moitié basse est
  structurellement valide, et il ne sait pas ce que la séquence prévoit après lui. C'est au
  diagnostic de déroulé (E01US024) de l'attraper.
- **`TypePhase` est dupliquée côté front** (`features/phases` et `features/patrimoine`), donc deux
  occasions de diverger du backend. Assumé à deux occurrences ; à une troisième, l'extraire.

## Ce que cet ADR ne tranche pas

- **L'exemple chiffré du Ladder contredit sa règle.** Partant de `1 2 3 4 5 6 7 8`, « le n°6 défie le
  4 et gagne » donne `1 2 3 5 6 4 7 8` dans l'exemple fourni — soit le n°6 en **5ᵉ** position, alors
  que la règle (« le gagnant monte, le perdant descend ») mène à la 4ᵉ. **Le moteur applique la
  règle**, et un test fige cet arbitrage pour qu'un changement futur soit une décision et non un
  glissement. À confirmer à la recette.
- **Les défauts « faute de précision »** (composition serpent des poules, barème 3/1/0, remise à zéro
  entre manches de BSO, 5 rondes au suisse, appariement fort-contre-faible de la ronde 1, Buchholz)
  sont tous des **politiques ou des paramètres** : chacun se corrige par configuration, aucun ne
  touche un moteur. Ils sont à confirmer à l'usage.
- **Le classement permanent de club** (ladder de saison, King of the Hill à l'année) reste hors
  périmètre : ce n'est pas une phase de tournoi.
- **L'exécution** de ces phases dans un tournoi réel — peupler effectivement une phase depuis ses
  sources, enchaîner les manches, publier les classements — relève d'**E01US024** (composer,
  diagnostiquer et simuler un déroulé) et d'**E07US004** (voir le tournoi se dérouler). Cette US
  livre les moteurs et la surface de composition, pas le pilotage en temps réel.
