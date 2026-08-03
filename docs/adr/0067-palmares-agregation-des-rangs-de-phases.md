# ADR-0067 — Le palmarès agrège les rangs des phases, et une 7ᵉ politique départage les ex æquo

- **Statut** : accepté
- **Date** : 03/08/2026
- **US** : E06US004 (podium des duels & agrégation des rangs)
- **Voisins** : [ADR-0004](0004-moteur-de-phases-politiques.md) (les six familles de politiques),
  [ADR-0065](0065-rang-acquis-lu-sur-la-plage-et-issue-repechee.md) (la fourchette acquise, *Règle
  R*), [ADR-0046](0046-config-policies-politiques-nommees-parametrees.md) (forme de
  `config.policies`), [ADR-0050](0050-forfait-abandon-et-disqualification.md) (abandon relégué, DSQ
  exclu), [ADR-0066](0066-seuil-de-barrage-porte-par-la-politique-tiebreak.md) (la couture
  « politique résolue par le registre » que celle-ci reprend)

## Contexte

Le projet savait dire **qui a le mieux tiré** (classement de qualification, E06US001) et **qui a
gagné un tableau** (`Tableau.podium()`, E05US005, visible dans le seul écran admin de saisie des
duels). Il ne savait pas dire **le classement final du tournoi** — celui qu'on affiche au mur à 17 h,
où le vainqueur du tableau est 1ᵉʳ même s'il était 6ᵉ le matin, et où l'archer non qualifié pour les
duels a tout de même un rang.

ADR-0065 avait laissé la question ouverte en toutes lettres : le routage rend une **fourchette**
(« 5ᵉ-8ᵉ ») pour un battu que rien n'a départagé, et s'interdit d'en choisir une valeur — « ce n'est
pas E06US004 ; elle reste due ».

Deux questions ont été posées au commanditaire au cadrage, et tranchées par lui :

1. **Comment départager deux archers sortis au même tour** — les quatre battus des quarts d'un
   tableau tronqué au podium ? Arbitrage : **politique injectable, défaut = rang de qualification**.
2. **Quel périmètre** ? Arbitrage : **moteur + API + vue publique + export PDF**.

## Décision

### 1. Le palmarès est une **fusion de blocs**, la phase la plus tardive l'emportant

Chaque archer est situé par la phase la plus **tardive** qui l'a classé (son `ordre` dans la
séquence), la qualification faisant bloc 0. Les blocs se rangent par ordre décroissant, et à
l'intérieur d'un bloc par position acquise croissante ; les rangs sont ensuite **renumérotés 1→N
sans trou**.

Deux conséquences qui ne sont pas des détails :

- **avoir disputé le tableau passe avant tout.** Le battu du 1ᵉʳ tour devance tout non-qualifié,
  quel qu'ait été le rang de qualification de l'un et de l'autre : il a franchi une porte que
  l'autre n'a pas franchie. C'est l'usage, et c'est ce que « fusionner » veut dire — sans quoi le
  palmarès ne serait qu'un classement de qualification décoré ;
- **la renumérotation est contiguë.** Un rang de qualification manquant (l'archer disqualifié en est
  **sorti**, ADR-0050) ne laisse pas de trou : le palmarès est *un* classement, pas la
  juxtaposition des numérotations de ses phases.

`domain/palmares.py` ne rejoue **aucun** tableau : il reçoit ce que chaque phase a décidé
(`ResultatPhase` : une position acquise par archer) et applique la règle. Reconstruire l'arbre est
le travail du service, lire une position acquise celui de `domain/tableau.py`. C'est ce qui rend la
règle de fusion testable sans monter un tournoi — et ce qui fera entrer les poules ou le système
suisse sans toucher au domaine : il ne connaît que des positions, pas des structures.

### 2. `aggregation` est une **septième famille de politiques**

ADR-0004 fermait le catalogue à six familles. E06US004 en ajoute une, `aggregation`, non par
symétrie mais parce qu'une **règle métier sans arbitre** est apparue : quatre archers sortent sur la
plage `[5..8]` et *aucun match ne les départagera jamais*. Deux réponses sont légitimes selon le
tournoi — c'est la définition d'une politique (règle 2) :

| Implémentation | Ce qu'elle décide |
|---|---|
| `AgregationParQualification` (**défaut**) | les range sur leur rang de qualification (usage World Archery) → 5, 6, 7, 8 |
| `AgregationExAequo` | assume l'*ex æquo* → « 5ᵉ-8ᵉ » pour les quatre |

⚠️ **À ne pas confondre avec `tiebreak`.** `tiebreak` départage sur un **score** (nombre de 10 puis
de 9, §8.1) des archers qui ont tiré la même chose ; `aggregation` intervient là où il n'y a **aucun
score commun à comparer** — deux archers de branches différentes n'ont pas tiré les mêmes flèches.
Les fusionner aurait obligé `Tiebreak` à accepter un `DecompteDepartage` vide, c'est-à-dire à mentir
sur ce qu'il compare.

La politique rend des **paquets ordonnés** plutôt qu'une liste plate : c'est ce qui permet à une
implémentation de dire « je n'ai pas su départager » sans inventer un ordre. `AgregationParQualification`
l'exerce d'ailleurs — deux archers *ex æquo en qualification* ressortent ex æquo, elle départage
*sur* la qualification, elle ne la contourne pas.

**Injectable, pas encore réglable.** La politique est injectée par la composition root et résolue
**par le registre** (`registre.resoudre(AGGREGATION, "par_qualification", {})`) — la contourner en
instanciant la stratégie à la main ferait de la politique une décoration (même parti qu'ADR-0066).
Mais `Phase` ne persiste aucune `config.policies` générique : seul `barrage_jusqu_au` l'est. Il
n'existe donc **aucun champ** où écrire le choix de l'organisateur. C'est un manque de **surface**,
pas de conception ; il se comblera avec l'US qui donnera aux phases leur config. En attendant,
`ResultatPhase` **ne porte pas** de politique par phase : un champ que rien ne peut renseigner
serait de la généralité spéculative.

### 3. Une fourchette « encore en lice » n'est **pas** un ex æquo — et les confondre décerne l'or avant la finale

`Tableau.positions_acquises()` rend, par participant, une `PositionAcquise(rang_min, rang_max,
en_lice)`. Le drapeau `en_lice` n'est pas décoratif : `[1..2]` porté par deux finalistes et `[5..8]`
porté par quatre battus ont la **même forme** et des sens opposés.

- `en_lice=False` — plus aucun match ne les départagera : la politique `aggregation` tranche ;
- `en_lice=True` — ils vont **tirer** : aucune politique n'a le droit de décider à leur place.

Sans ce drapeau, le palmarès départageait les deux finalistes sur leur rang de qualification et
**décernait l'or avant que la finale ne soit tirée**. Le défaut a été trouvé par un test de service
écrit depuis le CA avant l'implémentation (règle 9) — l'ordre d'écriture a payé exactement ce qu'il
promet.

Corollaire heureux : un archer encore en lice reçoit la plage de son match en cours (un
demi-finaliste est `[1..4]`). Le palmarès se consulte **pendant** le tournoi ; sans cela, un
demi-finaliste tomberait derrière les archers qu'il vient de battre.

### 4. `fourchette_de_rangs` **remonte** dans le domaine

E07US008 l'avait écrite dans `application/routage.py`, faute d'un second consommateur — et
`Tableau.classement()` portait un renvoi explicite « pour qu'E06US004 tombe dessus avant de la
réécrire ». C'est arrivé. La fonction vit désormais dans `domain/tableau.py`, d'où elle relit la
*Règle R* : deux services s'important une fonction privée l'un de l'autre auraient inversé le sens
des dépendances (règle 2) pour une règle métier de bout en bout.

### 5. Le podium ne montre **que** des rangs exacts

`Palmares.podium()` écarte les fourchettes : on ne remet pas une médaille à quatre archers 5ᵉ-8ᵉ, et
afficher une fourchette sur un podium ferait chercher longtemps qui monte sur la boîte. Un podium
peut donc être **partiel** — rangs 3-4 publiés seuls, la petite finale se tirant couramment avant la
finale (le bronze avant l'or est l'usage en salle) — voire vide, et il le **dit** plutôt que de
laisser un blanc (`P-3`).

Le podium se lit **par catégorie**, sur le rang de catégorie : c'est là que se remettent les
médailles, et la restriction du podium scratch serait vide pour toute catégorie n'ayant personne
dans les quatre premiers.

### 6. `PALMARES` entre au catalogue des vues d'écran, sans migration

`VueEcran` persiste la **chaîne**, pas un rang (E07US004) : `AFFECTATIONS` l'avait vérifié en
E07US008, `PALMARES` est la deuxième à en profiter. C'est le motif littéral du CA de pilotage des
écrans (E12US003) — « basculer sur le podium à 17 h et partir serrer des mains ».

## Conséquences

- **Ce qui devient possible** : un classement final consultable par le public, projetable en salle
  et imprimable (PDF), qui se resserre au fil des duels ; et une règle de départage qui se change
  sans toucher au code.
- **Portée réelle** : qualification + phases à **tableau**. Les moteurs `poule`, `big_shoot_off`,
  `suisse`, `colline` existent (E05US015) mais **aucun service ne les déroule** (`DETTE-028`) : il
  n'y a littéralement rien à lire. Ils entreront sans toucher au domaine.
- **Limite assumée, `DETTE-034`** : une phase de **consolation** (les perdants du tour *n* repris
  par une phase avale) serait mal classée — la règle « la phase la plus tardive l'emporte » ferait
  passer le vainqueur d'un repêchage devant le finaliste du tableau principal. Aucun `RoutingRepechage`
  n'est câblé en production (`DETTE-028`) et la sémantique de `SourcePhase.par_issue_de_tour` n'est
  toujours pas tranchée (`DETTE-033`) : trancher **ici**, dans un canal d'affichage, referait
  exactement l'erreur qu'ADR-0065 §3 a refusé de commettre. La lacune est inscrite au registre.
- **Coût** : un troisième consommateur de la reconstruction d'arbre non cachée sur route publique —
  `DETTE-031` élargie (poll de 30 s, plus long que les 20 s du routage, pour cette raison).
