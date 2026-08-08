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

⚠️ **Et la clé `config.policies.aggregation` est explicitement refusée**
(`FAMILLES_HORS_CONFIG_PHASE`, correctif de revue — axe C2). `FamillePolitique` sert de **catalogue
fermé** des clés admises : ajouter la famille faisait, sans le vouloir, passer cette clé de
« refusée » à « acceptée, résolue, puis **silencieusement ignorée** ». C'est un cran pire que « pas
encore réglable » — c'est réglable *en apparence* et sans effet, donc un organisateur qui la
poserait croirait avoir changé la règle. Le premier jet de cet ADR se contredisait d'ailleurs à un
fichier d'écart : il refusait un champ sur `ResultatPhase` faute de consommateur… et en ajoutait un
sur `PolitiquesPhase`. Même parti que le grain de `validation`, qu'ADR-0046 garde déjà hors de
`policies` : une clé n'est acceptée que si quelqu'un la consomme.

**Une famille typée sur l'archer**, là où le moteur traite des `Participant` opaques (ADR-0028).
Délibéré : elle départage sur le **rang de qualification**, qui est une notion d'archer — une
équipe n'en a pas. Le service écarte donc les participants « équipe » avant de l'appeler.

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

⚠️ **Mais le drapeau seul ne suffisait pas**, et la revue l'a démontré (axe adversarial) : il
protégeait le *groupement*, pas la *numérotation*. Deux demi-finales ne se valident jamais au même
instant ; entre les deux, le vainqueur de la première est **seul** sur sa position `[1..2]`, et le
curseur lui donnait donc un rang **exact** — « 1ᵉʳ », médaille comprise. Deux corrections en
découlent :

- un paquet **encore en lice** rend sa **fourchette acquise**, pas celle du curseur : « 1ᵉʳ-2ᵉ »
  reste « 1ᵉʳ-2ᵉ ». C'est la seule façon de ne rien resserrer que le tir n'a pas resserré ;
- `LignePalmares.decerne` dit qu'un **match** a décidé le rang, et c'est **lui** que le podium
  regarde — pas `rang_min == rang_max`, qui n'est qu'une question d'affichage. Un rang de
  qualification est exact par construction ; un ex æquo tranché par la politique l'est aussi.

**Une phase qui n'a tranché aucun duel est écartée** (`ServicePalmares._resultat`). Le déroulé se
compose à l'avance (E01US024) : la phase de tableau existe **dès le matin**, `_decor` l'ensemence
avec tous les archers en lice (`DETTE-028`), et chacun n'a acquis que la plage de son premier match
— le tableau entier. Le palmarès affichait donc « 1ᵉʳ-120ᵉ » sur 120 lignes pendant toute la
qualification. Le critère retenu est **ce que le tableau a décidé**, et non `phase.statut` : passer
une phase à `en_cours` est une action manuelle, et faire dépendre un écran public de la discipline
de l'organisateur le laisserait muet tout l'après-midi s'il l'oublie. Le correctif symétrique
proposé en revue — écarter côté domaine toute position couvrant le tableau entier — a été
**écarté** : il casserait le milieu de tour, où six archers d'un tableau de 8 n'ont encore rien
acquis et tomberaient **derrière le battu** qu'ils n'ont pas rencontré.

### 4. `fourchette_de_rangs` **remonte** dans le domaine

E07US008 l'avait écrite dans `application/routage.py`, faute d'un second consommateur — et
`Tableau.classement()` portait un renvoi explicite « pour qu'E06US004 tombe dessus avant de la
réécrire ». C'est arrivé. La fonction vit désormais dans `domain/tableau.py`, d'où elle relit la
*Règle R* : deux services s'important une fonction privée l'un de l'autre auraient inversé le sens
des dépendances (règle 2) pour une règle métier de bout en bout.

### 5. Le podium ne montre **que** des rangs exacts

`Palmares.podium(categorie_id)` exige trois choses, et chacune ferme un trou trouvé en revue : le
rang est **décerné par un match** (§3), il est **exact** — on ne remet pas une médaille à quatre
archers 5ᵉ-8ᵉ — et il vaut **≤ 4**.

Sans la première, le podium se remplissait sur les seuls scores du matin : tout rang de
qualification étant exact par construction, l'écran public et le PDF décernaient « Or / Argent /
Bronze » **avant le moindre duel**. Trois axes l'ont relevé indépendamment, et aucun test existant
ne cassait en le corrigeant — le signe exact que le CA « rangs 1-4 issus de la finale/petite
finale » n'avait jamais été mis à l'épreuve.

⚠️ **La condition « décerné par un match » a été essayée, puis écartée par le commanditaire**
(03/08/2026). Elle amputait le livrable : le moteur ne monte qu'un **seul tableau scratch**
(`DETTE-028`), donc **quatre archers du tournoi entier** seulement obtiennent un rang décerné par
un match terminal. Toutes les autres catégories perdaient leur podium **tournoi terminé**, et le
PDF affiché au mur omettait leurs blocs. Le CA (« rangs 1-4 issus de la finale/petite finale »)
présuppose un tableau **par catégorie**, que le moteur ne réalise pas — c'est `DETTE-028` qui parle,
pas le palmarès.

La règle retenue est donc : **un rang de catégorie définitif suffit**, et `decerne` porte la
**provenance**, affichée à l'écran et sur le PDF (« Bronze · au classement »). La distinction
demandée entre *classement* et *podium* est préservée — elle se lit au lieu de faire disparaître
des médailles. Un tournoi sans aucun duel n'a toujours pas de podium : `origine` y vaut
`qualification` pour tout le monde.

**Le match pour la 3ᵉ place, lui, est déjà un paramètre du moteur** : la politique `depth`
(ADR-0004). `ProfondeurPodium(jusqu_au=4)` — le défaut câblé — dispute la petite finale ;
`jusqu_au=2` ne dispute que la finale. Deux tests l'épinglent. Ce qui manque n'est pas le
paramètre, c'est l'écran pour le régler par phase — même lacune que pour `aggregation`.

Un podium peut être **partiel** — rangs 3-4 publiés seuls, la petite finale se tirant couramment
avant la finale (le bronze avant l'or est l'usage en salle) — voire vide, et il le **dit** plutôt
que de laisser un blanc (`P-3`).

Le podium se lit **par catégorie**, et le paramètre est **obligatoire** : c'est là que se remettent
les médailles, la restriction du podium scratch serait vide pour toute catégorie n'ayant personne
dans les quatre premiers, et une branche scratch que seuls ses tests tenaient aurait dérivé en
silence (correctif de revue, axe C2).

### 6. `PALMARES` entre au catalogue des vues d'écran, sans migration

`VueEcran` persiste la **chaîne**, pas un rang (E07US004) : `AFFECTATIONS` l'avait vérifié en
E07US008, `PALMARES` est la deuxième à en profiter. C'est le motif littéral du CA de pilotage des
écrans (E07US004, ADR-0064) — « basculer sur le podium à 17 h et partir serrer des mains ».

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
- **Couplage assumé** : `ServicePalmares` appelle `ServiceSaisieDuels.reconstruire`, comme le
  routage (E04US018) et le pilotage (E12US002) — 3ᵉ occurrence d'un motif établi. Recoder la
  reconstruction par ports seuls la ferait **diverger** de l'écran de duels : le palmarès
  annoncerait un vainqueur que la saisie ne montre pas. On duplique une chaîne de ports, jamais une
  règle métier.
- **Coût** : un troisième consommateur de la reconstruction d'arbre non cachée sur route publique —
  `DETTE-031` élargie (poll de 30 s, plus long que les 20 s du routage, pour cette raison).
