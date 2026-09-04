# ADR-0104 — Le classement des clubs se compte en médailles **inter-clubs**

- **Statut** : Accepté
- **Date** : 2026-09-04
- **US** : E16US017
- **Décideurs** : Organisateur / Architecte
- **S'appuie sur** :
  - [ADR-0103](0103-la-portee-d-un-podium-est-un-reglage-du-tournoi.md) — la portée d'un podium est
    un réglage du tournoi. Son **§8** annonce le présent ADR : « classer les **clubs entre eux** —
    par opposition aux archers d'un club entre eux — est un classement neuf et non un regroupement »
  - [ADR-0014](0014-club-inconnu-plutot-que-club-sentinelle.md) — « club inconnu » est une anomalie
    à signaler, pas un club de rattachement
  - [ADR-0065](0065-rang-acquis-lu-sur-la-plage-et-issue-repechee.md) — un *ex æquo* n'a pas de place de
    podium : personne ne saurait quelle médaille lui remettre

> ⚠️ **Cet ADR figure à la liste nominative d'[ADR-0075 § « Portée de la règle »](0075-le-depart-est-la-portee-sportive.md).**
> Il n'est pas d'outillage : il décide **ce que le moteur sportif publie comme résultat** — un
> classement neuf, qui n'existait pour aucune entité jusqu'ici. Il porte donc sa section « Porté
> dans le code par ».

## Contexte

Le produit sait classer des **archers** : au scratch, dans leur catégorie, et depuis ADR-0103 dans
leur club. Il ne sait pas classer les **clubs**. Or le questionnaire de maquettes (A16) demande un
trophée « du club le plus performant de la journée », et ce trophée se remet au même moment que les
médailles.

Trois barèmes ont été mis sur la table le 31/08/2026, au découpage d'`E16US014` :

1. **le décompte de médailles** — les clubs se comparent à l'or, puis à l'argent, puis au bronze ;
2. **la somme des scores de qualification** — écartée : elle **ignore les duels**, c'est-à-dire le
   tournoi lui-même. Un club dont personne ne passe un quart finirait devant un club champion ;
3. **un barème de points par rang** (5 pts au 1ᵉʳ, 3 au 2ᵉ…) — écarté : le barème devient lui-même
   une configuration à saisir, à défendre et à expliquer au pied du podium. C'est une US et un ADR
   à soi seul, pour un résultat que personne ne saurait vérifier de tête.

Le barème 1 a été retenu. ⚠️ **Il n'utilise que ce que le palmarès porte déjà** — les rangs décernés
— donc aucune donnée nouvelle ne remonte, et le résultat se recompte à la main au pied du podium.

Trois questions restaient ouvertes, aucune n'étant dans le questionnaire. Elles ont été tranchées le
04/09/2026 et forment le cœur du présent ADR.

## Décision

### 1. Le décompte se lit sur les **podiums décernés**, pas sur les rangs

`classer_clubs(palmares, reglage)` consomme les `BlocPodium` que `Palmares.podiums(reglage)` rend
déjà. C'est la traduction littérale du CA — « les médailles comptées sont celles que le tournoi
**décerne** » — et surtout la seule forme qui **interdit structurellement aux deux barèmes de
diverger** : il n'existe pas de seconde traversée des rangs qui pourrait un jour ne plus appliquer
les mêmes trois conditions que `_bloc` (rang issu des duels, plus en lice, rang exact).

Conséquence directe : le réglage des podiums **commande** le classement des clubs. Un tournoi qui ne
récompense que par catégorie classe ses clubs sur les médailles de catégorie, et un archer 3ᵉ scratch
mais 1ᵉʳ de sa catégorie rapporte un **or** à son club, pas un bronze.

### 2. La portée *club* est **exclue** du décompte

`PORTEES_INTER_CLUBS = {SCRATCH, CATEGORIE}`. La portée *club* d'ADR-0103 décerne un or **à
l'intérieur de chaque club** : la compter donnerait une médaille à **tous** les clubs, et jusqu'à
quatre à ceux qui ont assez d'archers pour remplir leur propre podium.

⚠️ **Le classement mesurerait alors l'effectif, pas la performance** — exactement ce que les Notes
d'`E16US017` excluaient en refusant un seuil d'effectif minimum (§7 ci-dessous). Une médaille gagnée
contre ses propres coéquipiers ne compare pas deux clubs.

**Corollaire : sans portée inter-club, il n'y a pas de classement du tout**, et non un classement où
tout le monde est premier. Un tournoi réglé sur la seule portée *club* rend
`ClassementClubs(lignes=(), portees_comptees=())`.

### 3. L'état est **porté**, pas déduit d'une liste vide

`ClassementClubs.portees_comptees` nomme les portées qui alimentent le décompte ; vide, il dit
« aucune base de comparaison ». `provisoire` dit qu'un podium compté attend encore.

⚠️ **`portees_comptees` dérive du RÉGLAGE, jamais des blocs rendus.** Le dériver des blocs ferait
dire « sans base » à un tournoi qui n'a simplement encore décerné aucune médaille — un état faux qui
ne se corrigerait jamais à l'écran, puisque la cause affichée serait la mauvaise. Les deux vides
sont distincts et l'écran ne dit pas la même phrase : « les podiums réglés récompensent à
l'intérieur de chaque club » (réglage, ne bougera pas) contre « aucun club au classement »
(population).

⚠️ **Un troisième fait, ajouté en revue : `portees_reglees`.** `portees_comptees` vide **confond**
deux causes — « le tournoi ne récompense rien » (réglage vide, licite §1) et « il ne récompense qu'à
l'intérieur des clubs ». La première ne pose aucune question, la seconde en pose une à laquelle
l'écran doit répondre. La première rédaction les séparait **côté client**, en lisant `podiums` : la
**cinquième** inférence de ce type sur ce DTO, écrite quinze lignes sous l'avertissement de
`VuePalmares` qui recense les quatre précédentes, toutes fausses. Le fait est donc servi.

C'est la leçon des **trois passes de revue** qu'a coûtées ADR-0103 §6, où l'énoncé d'un bloc portait
chaque fois sur une autre population que son contenu.

### 3 bis. Un décompte de zéros n'est **pas** un classement

Tant qu'aucun club n'a de médaille, `classer_clubs` ne rend **aucune ligne**.

⚠️ **Ajouté en revue (axe C1), et c'est le défaut le plus visible qu'elle ait trouvé.** À décompte
égal le rang est partagé (décision 6) : un champ de zéros sortait donc tous les clubs **1ᵉʳˢ**.
C'est mot pour mot l'état que la décision 2 interdit — « pas un classement où tout le monde est
premier » — atteint par la porte du **décompte** au lieu de celle de la **portée**, et il dure
**toute la matinée** d'un tournoi, projeté au gymnase. Défaut de **conjonction** au sens propre :
le domaine, le front et le PDF étaient chacun verts, et le test de tri du domaine l'épinglait même
comme un comportement voulu (`"tous à zéro, tous 1ᵉʳˢ"`).

La règle vit **au domaine**, pas dans les trois surfaces : c'est là que le rang naît. Les surfaces
disent « Aucun club n'a encore de médaille. » — une phrase vraie des **trois** causes possibles
(aucun club inscrit, rien d'encore décerné, médailles toutes revenues à des archers sans club), là
où « le classement démarrera aux finales » serait faux de la première.

### 4. Une médaille décernée deux fois compte deux fois

Un tournoi qui cumule *scratch* et *catégorie* remet **deux ors** au même archer. Son club en
encaisse deux (arbitrage du commanditaire, 04/09/2026).

Le décompte affiché **coïncide alors avec le nombre de médailles physiquement remises**, ce qui est
la propriété que l'on peut vérifier au pied du podium. L'alternative — dédoublonner par archer —
récompensait la profondeur d'effectif, mais faisait diverger le tableau du réel : deux médailles au
cou d'un archer, une seule au décompte de son club.

⚠️ **Effet assumé, énoncé avant l'arbitrage** : un club à un seul archer très fort double son score.

⚠️ **Et une limite trouvée en revue (axe D), qui borne la propriété ci-dessus.** Elle tombe quand le
tournoi n'a **qu'une seule catégorie** : le bloc *Toutes catégories* et l'unique bloc de catégorie
contiennent alors les **mêmes archers aux mêmes rangs**. Un seul jeu de médailles est remis, deux
sont comptés — le décompte ne coïncide plus avec le réel, ce qui était l'argument même de la
décision.

Elle est **documentée et non corrigée**, pour deux raisons. D'abord, dédoublonner casserait le cas
nominal, celui pour lequel l'arbitrage a été rendu : à plusieurs catégories, deux médailles sont
réellement remises. Ensuite, la duplication est **visible** — l'écran affiche deux blocs de podium
portant les mêmes noms, et l'organisateur qui règle deux portées sur une catégorie unique a demandé
cette redondance. La ligne « Compté sur : … » affichée sous le titre du classement (décision 8) la
rend lisible. Épinglée par `test_le_decompte_double_quand_le_tournoi_n_a_qu_une_categorie`, pour
qu'elle ne se redécouvre pas au pied du podium.

### 5. Trois métaux, et pas un de plus

La profondeur d'un podium va de 1 à 64 (ADR-0103 §4) et vaut **4 par défaut** : une 4ᵉ place est
donc le cas **nominal**, pas un cas limite. Elle ne rapporte rien. La compter aurait inventé un
quatrième métal que personne ne remet.

### 6. Les *ex æquo* partagent le rang ; le nom du club n'est **pas** un départage

Même décompte or/argent/bronze = même rang, avec sauts (1-2-2-4) — l'arithmétique du projet. Le
libellé du club n'entre dans la clé de tri que pour rendre l'**ordre d'affichage** déterministe
(règle 9 : deux lectures du même palmarès rendent la même liste). Il ne change aucun rang.

⚠️ Ceci ouvre un **5ᵉ site** de `DETTE-029` (« rang partagé à clé égale, avec sauts »), avec
`classement._ranger`, `poule`, `suisse` et `palmares._numeroter`. La ligne du registre a été
élargie plutôt qu'un contournement local inventé (§ Dette de `CLAUDE.md`). Le remède attendu —
`attribuer_rangs(ordonnes, meme_rang)` — accommode ce site sans modification : la clé est ici un
triplet de médailles au lieu d'un score, mais un prédicat d'égalité suffit.

### 7. Aucun effectif minimum, et un club bredouille est **classé**

Arbitrage du 31/08/2026 : un seuil masquerait des clubs en silence. Un club présent au tournoi
figure au classement, à zéro s'il le faut.

⚠️ **Limite assumée, énoncée avant l'arbitrage** : un club dont personne n'est monté sur un podium
est à égalité avec un club dont personne n'a rien gagné — le barème ne les sépare pas. C'est le prix
d'un décompte que tout le monde sait recompter.

Un archer **sans club** (ADR-0014) ne rapporte sa médaille à personne et **ne crée aucune ligne**
« sans club » : le club inconnu reste une anomalie à corriger aux inscriptions, pas une entité de
classement.

### 8. Le classement suit les quatre surfaces, et **dit sur quoi il repose**

Écran d'admin, appli publique, écran de salle et PDF — le trophée se remet en même temps que les
médailles, il se lit donc au même endroit. Le composant `VuePalmares` étant unique pour les trois
surfaces d'écran (prop `interactif`), cela coûte **un** bloc de JSX et **une** section de PDF.

Chaque surface affiche, sous le titre, la ligne **« Compté sur : Toutes catégories · Par
catégorie »**. ⚠️ Ajoutée en revue (axe D) : `portees_comptees` était servi et **jamais lu** — le
champ ne tenait pas la promesse de son propre commentaire. C'est pourtant l'information qui
désamorce la surprise de la décision 4 : « Or : 2 » pour un club d'un seul archer s'explique dès
qu'on lit sur quoi le décompte porte.

⚠️ **Trois vides, trois traitements**, et c'est ce que la surface peut commenter qui les sépare.
Réglage **vide** : rien ne s'affiche, il n'y a pas de question posée. **Aucune portée inter-club** :
le papier saute la section — une table vide imprimée se lirait « aucun club » sans que rien puisse
la commenter (parti de `_podiums`, ADR-0103 §6) — quand l'écran, lui, nomme la cause. **Aucun club
médaillé** : les deux le disent, le papier compris, car un tournoi dont personne n'a de club
rattaché doit produire ce signal.

## Conséquences

**Ce qui devient possible.** L'organisateur remet le trophée du club sans compter les médailles à la
main, et le décompte est celui qu'un délégué de club peut vérifier lui-même à partir des podiums
affichés — propriété que ni la somme des scores ni un barème de points n'auraient eue.

**Ce que cela coûte, et qui n'est pas gratuit.** La garde d'`E16US014` sur `_libelles_club` **tombe** :
le référentiel des clubs était lu **seulement** si la portée *club* était réglée, au motif explicite
que le cas courant « n'en fait rien ». Ce n'est plus vrai — le classement des clubs doit **nommer**
ses clubs dès qu'une portée inter-club est active, donc dès le réglage par défaut. La lecture est
désormais faite dès qu'**une** portée est réglée ; seul le tournoi qui ne récompense rien l'évite.
C'est un élargissement mesuré de `DETTE-031` (le palmarès est déjà reconstruit entièrement à chaque
lecture, sur une route publique) : un `SELECT` sur un référentiel de quelques dizaines de lignes
contre une reconstruction de tous les tableaux.

**Ce qui n'est pas fait, et qu'il faut savoir.** `DETTE-045` s'applique **aussi** à ce classement :
le palmarès est rendu « du tournoi » alors qu'il dérive du **premier créneau**. Un classement de
clubs est encore plus exposé que les podiums à cette imprécision, puisqu'il agrège — un club dont
les archers tirent sur un autre départ n'apporte rien. La ligne existante couvre déjà le cas
(elle nomme les portées *toutes catégories* et *club* comme revendiquant une portée que la donnée ne
couvre pas) ; elle n'a pas été élargie, elle s'applique telle quelle.

De même, l'écran projeté ne **pagine pas** le palmarès (ADR-0103 § Conséquences) : un classement de
clubs à trente lignes montrera le haut et rien d'autre au vidéoprojecteur.

**Ce qui reste à surveiller.** Le classement des clubs est recomposé à chaque lecture et recalcule
les podiums pour son propre compte (`classer_clubs` appelle `podiums()`). C'est **délibéré** — une
signature auto-suffisante rend impossible de lui passer des blocs calculés avec un autre réglage,
défaut que `_groupes` (ADR-0103) ne peut éviter que par convention. Le surcoût est une passe sans
E/S sur des lignes déjà en mémoire, négligeable devant `DETTE-031`. Si le palmarès gagne un jour un
cache, c'est là qu'il faudra le poser, pas ici.

## Porté dans le code par

- `backend/domain/classement_clubs.py` — **tout l'ADR**. `PORTEES_INTER_CLUBS` (décision 2) ;
  `classer_clubs` (décision 1 — la composition sur les blocs déjà décernés —, décision 3, qui
  dérive `portees_comptees` **et** `portees_reglees` du réglage, et **décision 3 bis** : la garde
  `aucune` qui refuse de ranger un champ de zéros) ; `ClassementClubs.portees_comptees`, `.portees_reglees` et
  `.provisoire` (décision 3) ; `_libelles` (décision 7, y compris l'exclusion des archers sans
  club) ; `_ranger` (décision 6, et le marqueur `DETTE-029` du 5ᵉ site).
  ⚠️ **`_decompter` porte à lui seul les décisions 4 et 5**, et c'est là que le mode de panne vit —
  relevé en revue (axe C2), la première rédaction l'omettait. La décision 4 (« deux fois compté »)
  n'est tenue par **aucune ligne** : elle l'est par l'**absence** de dédoublonnage par archer dans
  la double boucle `for bloc … for place`. Un mainteneur qui y ajouterait un `vu_par_archer`
  casserait l'ADR sans toucher un symbole nommé ailleurs. La décision 5, elle, est tenue par le
  **test** `place.rang <= _METAUX` : retirer la constante ne compilerait pas, relâcher la
  comparaison passerait.
- `backend/application/palmares.py` — `ServicePalmares._libelles_club` : la garde élargie du
  § Conséquences. C'est **le** symbole dont la modification casserait le nommage des clubs sans
  qu'aucun rang ne bouge.
- `backend/api/v1/palmares.py` — `ClassementClubsReponse`, `LigneClassementClubsReponse` et l'appel
  de `classer_clubs` dans `PalmaresReponse.de_rendu`, composé sur `rendu.complet` et non sur
  `rendu.affiche` (décision 8 + ADR-0103 §7).
- `backend/infrastructure/pdf/palmares.py` — `GenerateurPalmaresPdf._classement_clubs` : la section
  imprimée, et le saut du bloc sans base (décision 8).
- `frontend/src/features/palmares/VuePalmares.tsx` — le composant `ClassementClubs` (décision 8),
  qui rend les rangs du serveur **tels quels**, sauts d'*ex æquo* compris (décision 6).
- `frontend/src/features/palmares/presentation.ts` — `etatClassementClubs` : les trois vides
  distincts de la décision 3.
