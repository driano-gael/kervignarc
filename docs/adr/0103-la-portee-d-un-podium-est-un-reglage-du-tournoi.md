# ADR-0103 — La portée d'un podium est un réglage du tournoi

- **Statut** : Accepté
- **Date** : 2026-08-31
- **US** : E16US014
- **Décideurs** : Organisateur / Architecte
- **S'appuie sur** :
  - [ADR-0067](0067-palmares-agregation-des-rangs-de-phases.md) — l'agrégation des rangs de phases.
    Cet ADR **révise sa Décision 5**, qui figeait le podium « par catégorie, rangs 1-4 »
  - [ADR-0070](0070-profondeur-de-classement-reglee-par-phase.md) — la profondeur de classement `top_n`,
    dont §2 explique pourquoi le mot « podium » avait été **écarté** d'un nom persisté
  - [ADR-0014](0014-club-inconnu-plutot-que-club-sentinelle.md) — « club inconnu » est une anomalie
    à signaler, pas un club de rattachement
  - [ADR-0071](0071-cloisonnement-categorie-blason-active-et-dur.md) — le précédent de forme : un
    réglage de tournoi persisté sur `tournoi`, avec son ADR

> ⚠️ **Cet ADR figure à la liste nominative d'[ADR-0075 § « Portée de la règle »](0075-le-depart-est-la-portee-sportive.md).**
> Il n'est pas d'outillage : il décide **ce que le moteur sportif publie comme résultat** — un
> troisième espace de rangs entre au domaine, et la notion de podium change de définition. Il porte
> donc sa section « Porté dans le code par », exigée de tout ADR neuf.

## Contexte

`Palmares.podium(categorie_id)` rendait les quatre premiers **d'une catégorie**, et rien d'autre :
la portée était une signature, la profondeur une constante de module (`PODIUM_JUSQU_AU = 4`).
[ADR-0067 § Décision 5](0067-palmares-agregation-des-rangs-de-phases.md) l'avait posé
délibérément — le paramètre `categorie_id` y est dit **obligatoire**, au motif qu'« une branche
scratch que seuls ses tests tenaient aurait dérivé en silence ».

Le questionnaire de maquettes (A16, 04/08/2026) demande l'inverse : *« podium configurable, tout
doit être possible »* — par catégorie, scratch, par club, par équipe. Un club récompense ce qu'il a
décidé de récompenser, et cela varie d'une édition à l'autre.

Le motif d'ADR-0067 n'a pas disparu pour autant : une branche par portée, c'est exactement le
scénario qu'il refusait. C'est cette tension que le présent ADR tranche.

## Décision

### 1. La portée est de la **configuration**, et elle se cumule

`ReglagePodiums` (`domain/podium.py`) porte un **ensemble** de `PorteePodium` — `SCRATCH`,
`CATEGORIE`, `CLUB` — et une profondeur. Un ensemble, pas un choix unique : le club qui remet des
médailles par catégorie **et** un trophée scratch ne doit pas changer de réglage entre deux remises
(arbitrage du commanditaire, 31/08/2026). L'ensemble **vide** est valide — un tournoi peut ne rien
récompenser.

C'est un réglage **du tournoi**, persisté sur `tournoi` (migration `0052`), au même titre que le
cloisonnement des cibles (ADR-0071) : deux tournois montés sur le même format ne remettent pas
forcément les mêmes médailles. Un format de tournoi est de la configuration, pas du code (règle 2).

### 2. Une seule branche, paramétrée — le motif d'ADR-0067 est honoré, pas contourné

`Palmares.podium(categorie_id)` **disparaît** au profit de `Palmares.podiums(reglage)`. Les trois
portées passent par **le même** `_bloc()`, qui applique les mêmes trois conditions (rang issu des
duels, plus en lice, rang exact) sur le rang de la portée. Il n'y a donc **pas** de « branche
scratch » : il y a un mécanisme et un paramètre.

C'est ce qui permet de réviser ADR-0067 §5 sans reproduire le défaut qu'il fermait. Garder l'ancienne
méthode à côté de la nouvelle aurait recréé deux chemins pouvant diverger ; les tests d'E06US004
conservent leurs valeurs attendues **au chiffre près** via une aide locale qui restitue l'ancienne
forme d'appel.

### 3. Le rang « dans son club » réutilise la renumérotation existante

`_numeroter(paquets, retenir=…)` sait déjà renuméroter un sous-ensemble depuis 1 — c'est ce qui
produit le rang de catégorie. Le rang de club est **le même appel** avec un autre filtre
(`_du_groupe`, généralisé depuis `_de_categorie`). Aucune arithmétique d'*ex æquo* n'est réécrite :
`DETTE-029` n'a pas gagné de 5ᵉ site.

Ce rang est calculé **inconditionnellement**, pas seulement quand la portée est active : le rendre
conditionnel aurait fait dépendre la **forme** de `LignePalmares` d'un réglage, donc obligé chaque
lecteur à savoir lequel était actif. Ce qui est conditionnel, c'est la **lecture du référentiel des
clubs** (`_libelles_club`), qui est la partie coûteuse.

### 4. La profondeur est une **colonne de tournoi**, et non la politique `depth`

Le projet possède déjà un mécanisme « jusqu'où on classe » : la politique injectable
`ProfondeurClassement` (ADR-0004, ADR-0046, ADR-0070), persistée dans `config.policies` **par
phase**. Elle n'est pas la bonne maille ici, et ce sont deux questions différentes :

- `depth` décide **jusqu'où le tableau départage**, c'est-à-dire combien de duels sont tirés ;
- `ReglagePodiums.profondeur` décide **combien de places le palmarès affiche**, une fois tout tiré.

Un podium traverse toutes les phases d'un tournoi ; le loger dans la config d'une phase aurait
demandé de choisir laquelle. ⚠️ **Conséquence à ne pas manquer** : ce réglage ne commande **pas** le
nombre de duels tirés. Avec la politique câblée par défaut (`AggregationParQualification`), les
rangs au-delà de la profondeur du tableau restent exacts — un podium à 8 places sur un tableau
`top_n(4)` rend bien 8 places, dont quatre marquées « (au classement) ». Le réglage n'est jamais
inerte, mais il ne fabrique pas de compétition.

### 5. « Podium » change de définition, et le mot « Scratch » n'est pas repris

Le glossaire définissait le **Podium** comme « la restriction aux rangs 1-4 décernés par un match
**d'une catégorie** ». Après cet ADR : *la restriction du palmarès aux N premiers rangs exacts issus
des duels, dans la ou les portées réglées sur le tournoi*. Le glossaire est réaligné dans le même
commit (règle 3 : cohérent code / API / UI / doc).

⚠️ **Le bloc sans regroupement se dit « Toutes catégories », jamais « Scratch ».** Le glossaire
réserve ce mot à un **libellé de catégorie** (regroupement de classement arc nu, U21+S1+S2+S3) : un
club qui nomme ainsi sa catégorie arc nu — le cas nominal FFTA — et coche les deux portées aurait
imprimé **deux blocs « Podium — Scratch »** sur la même page, contenus différents. Le **code** de la
portée reste `scratch` : il est cohérent avec `rang_scratch`, qui porte ce second sens partout dans
le moteur.

⚠️ **ADR-0070 §2 avait payé un renommage** (`podium` → `top_n`) pour éviter qu'un « podium jusqu'au
8ᵉ » devienne un nom persisté. Cet ADR crée précisément cela, et l'assume : le commanditaire a
demandé un podium configurable, et le mot « podium » est celui qu'il emploie. Le coût différé — un
renommage de colonne après la première base de production — est réel et nommé.

### 6. Un bloc vide est rendu par le domaine ; c'est le **document** qui le saute

`podiums()` rend un bloc même sans place décernée : à l'écran, un groupe qui disparaît se lit comme
un groupe sans archers alors qu'il est simplement en cours (parti `P-3`). Le PDF, lui, saute les
blocs vides — un tableau à en-tête seul n'a pas d'équivalent du message « podium en cours ».

⚠️ **L'écran doit distinguer « pas encore » de « jamais »** : avec la portée club, la plupart des
clubs n'ont personne au tableau (`DETTE-028`), et « les finales ne sont pas toutes tirées » y serait
faux deux fois. `BlocPodium.en_attente`, rempli **au domaine**, porte la nuance.

⚠️ **Le créneau prime sur le groupe** (arbitrage du 01/09/2026) : `Palmares.duels_non_commences`
force `en_attente`. Sans lui, personne n'étant « en lice » tant qu'aucun résultat n'est lisible,
chaque bloc annonçait le **définitif** toute la matinée.

⚠️ **La règle exacte, parce qu'une approximation ici a déjà coûté une passe de revue** : le drapeau
est vrai tant qu'une phase à duels **encore ouverte** n'a rien livré — **les trois familles**
(tableau, poules/suisse/colline, Big Shoot Off), un créneau *qualification → poules* gardant sinon
le défaut intact. Il retombe au **premier résultat lisible**, pas à la fin du tournoi : l'attente se
lit ensuite archer par archer (`en_lice`), ce qui est juste pour un groupe jamais entré au tableau.
Et il exclut les phases **terminées** : un producteur rend `None` pour cinq raisons dont **une
seule** veut dire « ça va être tiré » — sans ce filtre, une consolante abandonnée laissait « Podium
en cours » **pour toujours**, et la branche du définitif devenait inatteignable.

⚠️ **Le serveur porte les faits, le client ne les déduit pas.** Même leçon que ci-dessus, un cran
plus haut : la vacuité du classement (`PalmaresReponse.classement_vide`) est **servie**, parce que
quatre gardes successives ont tenté de l'inférer de données filtrées ou commandées par le réglage,
et se sont trompées dans quatre coins différents.

⚠️ **Cet état est porté par le bloc, jamais recalculé par l'appelant** — c'est la leçon des trois
passes de revue qu'a coûtées cette décision : les blocs ont d'abord été composés sur un palmarès
filtré, puis leur effectif compté à l'écran sur les lignes affichées, puis la garde de vacuité lue
sur la vue. À chaque fois l'énoncé portait sur une autre population que le contenu. `effectif` et
`en_attente` vivent donc sur `BlocPodium`, remplis là où le groupe est déjà filtré : l'erreur cesse
d'être représentable. ⚠️ `effectif` compte les archers **récompensables** (rang issu des duels et
classé), pas tous ceux du groupe — les compter tous déclarait « podium partiel » à perpétuité.

### 7. Les podiums se composent sur le palmarès **complet**, jamais sur la vue filtrée

Le filtre par catégorie d'E06US001 restreint l'**affichage** du classement. Un podium, lui, est celui
du tournoi : il ne se rétrécit pas parce que l'organisateur a choisi de regarder une catégorie.
`ServicePalmares.rendu()` rend donc `complet` (les podiums), `affiche` (le classement) et le réglage,
en **une** lecture.

### 8. La portée *équipe* d'A16 est hors périmètre, et le restera jusqu'à EPIC-13

La classe `Equipe` n'existe pas ([ADR-0028](0028-epreuves-par-equipes-participant.md)). Un membre
d'énumération qui ne peut rien rendre est pire qu'un membre absent : il se règle, et il ne se voit
pas. Classer les **clubs entre eux** — par opposition aux archers d'un club entre eux — est un
classement neuf et non un regroupement : il part en `E16US017`, au décompte de médailles.

## Conséquences

**Ce qui devient possible.** Un club règle ce qu'il récompense sans toucher au code, et le réglage
vaut d'un coup pour les quatre surfaces du palmarès (écran d'admin, appli publique, écran de salle,
PDF). Ajouter une portée demain est un membre d'énumération plus une passe de renumérotation.

**Ce qui ne change pour personne.** Les défauts serveur de la migration `0052` (`["categorie"]`,
`4`) **sont** le comportement d'E06US004 : un tournoi déjà en base rend exactement le même palmarès.
La garantie vit dans la migration, pas dans le code, et `test_migration_0052_reglage_podiums.py`
l'épingle.

**Ce que cela coûte.** Un troisième couple de bornes sur chaque `LignePalmares` ; un
`ClubRepository` de plus au `ServicePalmares` (le PDF doit **nommer** les clubs et n'a pas d'écran
pour le faire à sa place) ; et deux réglages homonymes dans le vocabulaire du projet — la profondeur
de classement d'une phase et la profondeur d'un podium —, distingués au §4 et dans l'aide de l'écran.

**Ce qui n'est pas fait, et qu'il faut savoir.** L'écran projeté ne **pagine pas** le palmarès :
E16US009 a donné une pagination au classement et aux affectations, jamais à cette vue. Tenable à
huit blocs de quatre places, la portée *club* peut en produire des dizaines — le vidéoprojecteur
montrera le haut et rien d'autre. Le déclencheur est un choix explicite de l'organisateur (le défaut
reste catégorie / 4 places) ; la limite est inscrite au registre de dette plutôt que corrigée ici.

**Ce qui reste à surveiller.** `DETTE-045` : le palmarès est rendu « du tournoi » alors qu'il dérive
du **premier créneau**. Les portées *toutes catégories* et *club* revendiquent explicitement une
portée que la donnée ne couvre pas — la ligne est élargie en conséquence.

## Porté dans le code par

- `backend/domain/podium.py` — `PorteePodium`, `ReglagePodiums`, `PROFONDEUR_PODIUM_PAR_DEFAUT`,
  `PROFONDEUR_PODIUM_MAX` : la décision 1 et la borne du §4. Module à part pour la même raison que
  `domain/cloisonnement.py` (éviter un cycle avec `domain/palmares`).
- `backend/domain/palmares.py` — `Palmares.podiums`, `_bloc`, `_cle_de`, `_groupes`, `_rang_exact`
  (décisions 2 et 6), `BlocPodium.effectif` / `BlocPodium.en_attente`, qui portent l'état du bloc
  au lieu de le laisser recalculer par ses lecteurs, et `Palmares.duels_non_commences`, qui fait primer
  le créneau sur le groupe (décision 6) ; `_du_groupe` et la passe `rangs_club` de `calculer_palmares` (décision 3) ;
  `LIBELLE_SCRATCH` (décision 5) ; `LignePalmares.rang_club_min` / `rang_club_max` / `club_libelle`.
- `backend/domain/tournoi.py` — `Tournoi.reglage_podiums` et `definir_reglage_podiums` : le réglage
  vit sur l'agrégat tournoi (décision 1).
- `backend/application/palmares.py` — `RenduPalmares` et `ServicePalmares.rendu` (décision 7), et
  `_duels_non_commences` et son appel dans `_calculer` — le service est le seul à voir les phases
  du créneau et leur statut (décision 6) ;
  `_libelles_club` (lecture conditionnelle, décision 3) ; `reglage_podiums` /
  `definir_reglage_podiums`.
- `backend/api/v1/palmares.py` — `PalmaresReponse.classement_vide`, qui **porte** le fait « ce
  tournoi est-il classé ? » que quatre gardes successives avaient tenté d'inférer ; `PodiumReponse`
  (dont `effectif` et `en_attente`, recopiés du bloc), `PlacePodiumReponse`, `ReglagePodiumsReponse`, `ReglerPodiumsRequete`,
  `PalmaresReponse.de_rendu`, et les fonctions de route `reglage_podiums` (lecture ouverte) et
  `regler_podiums` (derrière `exiger_admin`).
- `backend/infrastructure/db/models.py` (`TournoiORM.podium_portees`, `podium_profondeur`),
  `backend/migrations/versions/0052_reglage_podiums.py` (les défauts serveur qui portent la
  non-régression) et `backend/infrastructure/db/repositories/referentiel.py`
  (`_vers_reglage_podiums`, `_portees_en_json`).
- `backend/infrastructure/pdf/palmares.py` — `_podiums` saute les blocs vides (décision 6) et
  compose sur `complet` (décision 7).
- `frontend/src/features/palmares/ReglagePodiums.tsx` — l'écran de réglage, monté par
  `features/admin/CoquilleAdmin.tsx` et **jamais** par `VuePalmares.tsx`, qui sert aussi le public.
- `frontend/src/features/palmares/presentation.ts` — `etatPodium` : la **mise en mots** de la
  nuance « pas encore » / « plus jamais » (décision 6). Le front ne calcule plus rien : il lit
  `podium.effectif` et `podium.en_attente`.
