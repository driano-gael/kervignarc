# ADR-0083 — Le contrat de phase jouable, et les poules pour le tailler

- **Statut** : Accepté
- **Date** : 2026-08-09
- **Décideurs** : Organisateur / Architecte
- **Précise** : [ADR-0045](0045-sequence-de-phases-cycle-de-vie-typage-source.md) (typage ouvert des
  phases) · [ADR-0062](0062-catalogue-de-types-de-phase.md) (catalogue de types)
- **S'appuie sur** : [ADR-0046](0046-config-policies-politiques-nommees-parametrees.md)
  (`config.policies`) · [ADR-0024](0024-plan-de-cibles-materialise-ajustable.md) et
  [ADR-0048](0048-cote-a-cote-des-duellistes-par-reordonnancement.md) (plans de cibles matérialisés) · [ADR-0068](0068-le-moteur-consomme-les-prelevements-declares.md)
  (prélèvements consommés)
- **Résorbe** : [DETTE-028](../dette.md), **partiellement** — volet poules et barrage

## Contexte et problème

E05US015 ([ADR-0062](0062-catalogue-de-types-de-phase.md)) a livré six moteurs de domaine — poules,
système suisse, colline, Big Shoot Off, barrage, échauffement — chacun testé, aucun **appelé par la
production**. La lettre d'ADR-0045 §2 était tenue (« on n'offre pas en façade un type qu'aucun
moteur ne sait dérouler »), son intention pas du tout : l'organisateur peut composer une phase de
poules dont le réglage n'est exprimable nulle part et que rien ne déroulera. C'est `DETTE-028`.

Le commanditaire a demandé le 07/08/2026 que ces formats deviennent jouables « au plus tôt dans le
backlog », et « surtout » composables à l'atelier.

**Le vrai obstacle n'était pas l'absence de moteurs — ils existent — mais la façon dont le reste du
code décide qu'une phase est jouable.** Au 09/08/2026, **dix** endroits filtrent sur
`TypePhase.ELIMINATION_DIRECTE`, chacun répondant à une question légèrement différente :

| Site | Question posée |
|---|---|
| `domain/phase.py` · `TYPES_EN_TABLEAU` | « monte-t-elle un arbre de duels ? » (profondeur réglable) |
| `domain/deroule.py` · `_TYPES_DEROULES` | « le moteur va-t-il seulement monter cette phase ? » |
| `domain/deroule.py` · `_TYPES_CLASSANTS_LUS` | « sait-on lire ce qu'elle a classé ? » |
| `application/palmares.py` · `_TYPES_RECONSTRUCTIBLES` | « sait-on rejouer son arbre ? » |
| `application/simulation_format.py` · `_TYPES_DEROULABLES` | « faut-il avertir l'organisateur ? » |
| `application/saisie_duels.py` (×2) | « peut-on y saisir un tir ? » |
| `application/placement_duels.py` | « a-t-elle un plan de cibles ? » |
| `application/routage.py` | « sait-on dire où l'archer tire ensuite ? » |
| `application/tableaux_publics.py` | « le public la voit-il ? » |
| `frontend` · `TYPES_DEROULES` | idem, côté client |

Le code documente lui-même que ces tables « ne se recoupent que par coïncidence », et **deux
divergences réelles y sont déjà consignées** : `placement` figure dans `_TYPES_DEROULES` alors
qu'aucun service ne monte son tableau, et trois copies de `TYPES_EN_TABLEAU` avaient été
consolidées en deux, un commentaire affirmant l'unicité pendant qu'une troisième vivait ailleurs.

Ajouter les poules à dix tables indépendamment, puis le suisse, puis la colline, puis le Big Shoot
Off, garantissait la 3ᵉ, 4ᵉ et 5ᵉ divergence. **La 3ᵉ occurrence réelle est atteinte : le remède
structurel est justifié par le code d'aujourd'hui, pas par une évolution supposée.**

## Décision

### 1. Un **contrat de phase jouable**, résolu par type

Ce qu'une phase doit savoir répondre pour être jouable tient en six questions — celles que les dix
tables ci-dessus posaient chacune dans son coin :

1. **Qui entre dedans ?** — générique depuis [ADR-0068](0068-le-moteur-consomme-les-prelevements-declares.md)/E05US024, aucune reprise nécessaire.
2. **Qu'est-ce qu'on saisit ?** — le *décor* : un arbre de duels, des rencontres en groupes, une
   volée collective.
3. **Quand est-ce validé ?** — le grain, déjà porté par le catalogue (`_GRAINS_ADMIS`).
4. **Qui est classé, et dans quel ordre ?**
5. **Où l'archer tire-t-il ensuite ?**
6. **Combien de couloirs la phase occupe-t-elle, et comment ?**

Les tables existantes ne sont **pas supprimées** — leurs noms sont lus par une centaine de sites —
mais elles **dérivent** désormais d'une source unique par capacité. Ajouter un type se fait à un
seul endroit ; une table qui diverge devient impossible plutôt qu'improbable.

### 2. Les **poules** taillent le contrat, délibérément

Le contrat est dessiné en rendant **un** format réellement jouable, pas dans le vide. On a pris le
plus riche des quatre : les poules ont des groupes, des duels, un barème, une table de rangs, un
départage à cinq critères et un barrage.

Le Big Shoot Off aurait donné une tranche plus courte — mais il n'a **ni groupes ni duels**, et son
grain est `FIN_DE_SERIE` là où les trois autres sont `FIN_DE_DUEL`. Un contrat taillé dessus
n'aurait pas accueilli les poules, et il aurait fallu le refaire **en repassant sur du code déjà
livré**. On taille le gabarit sur le vêtement le plus large.

`E05US028` (Big Shoot Off) est donc l'US qui **éprouvera** ce contrat. S'il doit céder quelque part,
c'est là, et l'élargissement se documentera ici — c'est le signal utile que le contrat était trop
court, et il vaut d'être tracé plutôt que subi.

### 3. L'unité de placement d'une poule est **la poule**, pas l'archer

Une poule ne met pas tous ses membres sur la ligne : `rencontres_de_poule` apparie par la méthode du
cercle, qui produit `effectif ÷ 2` rencontres par tour — à effectif impair, un membre se repose.
**Une poule de 5 tient donc sur 4 couloirs**, comme une poule de 4. *(Point relevé par le
commanditaire le 09/08/2026 ; le premier cadrage réservait un couloir par membre et faisait déborder
toute poule impaire sans raison.)*

Mais **le membre au repos change à chaque tour** : aucun des cinq n'a de couloir attitré, ils
tournent sur le bloc. D'où :

- on persiste **« poule → plage de couloirs contigus »**, jamais « archer → couloir » — qui serait
  une information *fausse*, pas seulement incomplète ;
- les couloirs de chaque rencontre, tour par tour, sont **dérivés** à la lecture, comme
  l'appariement d'un tableau ([ADR-0023](0023-moteur-de-placement-glouton-deterministe.md)/[ADR-0048](0048-cote-a-cote-des-duellistes-par-reordonnancement.md)) ;
- une poule qui déborde d'une cible prend la suite sur la cible d'après, et **la poule suivante
  démarre au couloir libre juste après** — la salle se remplit en continu, sans trou (règle donnée
  par le commanditaire le 09/08/2026).

**Conséquence assumée** : `placement_tableau` (keyé `(phase_id, inscription_id)`) ne convient pas —
il porte un couloir *par archer*. Les poules demandent donc leur propre table et **une migration**,
là où le reste de l'US n'en demande aucune.

### 4. Le réglage porte la **taille visée**, la configuration porte le **nombre de poules**

Le déroulé se compose des semaines avant le tournoi, inscriptions ouvertes : **le nombre de poules
n'y est pas calculable**. L'organisateur règle donc « des poules de 4 » (`ReglageDePoules`), et la
conversion en nombre de groupes (`ConfigurationPoules`) se fait le jour J, sur l'effectif réel, en
**un seul endroit** (`ReglageDePoules.pour_effectif`).

L'arrondi est **vers le bas** sur le nombre de groupes, de sorte qu'aucune poule ne compte moins que
la taille demandée : 30 archers en poules de 4 donnent **7 poules — cinq de 4 et deux de 5**
(arbitrage du commanditaire du 09/08/2026, qui a écarté « 8 poules dont deux de 3 »). En
contrepartie, l'écran **montre** la répartition obtenue avant validation : c'est ce qui rend
lisible le cas extrême où l'effectif est inférieur au double de la taille (7 archers en poules de 4
→ une poule de 7).

### 5. Deux régimes d'ex æquo, portés par un champ **déjà existant**

- La poule produit un **classement** (`nb_qualifies` non déclaré) : le classement *est* le livrable,
  donc **tout** ex æquo irréductible se départage au barrage.
- La poule produit des **qualifiés** (`nb_qualifies = k`) : seul le franchissement de la barre
  compte. Barrage **uniquement** si l'égalité tombe pile sur la barre ; deux archers à égalité aux
  rangs 3-4 d'une poule qui en qualifie 2 **restent à égalité**.

Ce n'est pas un réglage neuf : c'est la présence ou l'absence de `nb_qualifies`, seulement rendue
**explicite à l'écran** au lieu d'être déduite d'un champ laissé vide.

### 6. Le classement de phase est **« par rang de poule d'abord »**

*(Arbitrage du commanditaire du 09/08/2026, pris en cours de tranche.)* Les poules se jouent **en
parallèle** et donnent donc le même classement. Sur `P` poules, les rangs `1..P` sont les vainqueurs
de poule, `P+1..2P` les deuxièmes, et ainsi de suite — c'est ce qu'une phase avale lit quand elle
déclare « les rangs 1 à 8 ».

Trois conséquences, toutes voulues :

- **Le classement porte tout le monde**, pas seulement les qualifiés. C'est le *prélèvement* qui
  sélectionne, pas le classement qui tronque — ce qui rend une consolante « les rangs 9 à 16 »
  composable sans réglage neuf. Le dernier bloc peut être **incomplet** (30 archers en poules de 4 →
  7 poules, donc les rangs 29-30 ne portent que les 5ᵉˢ des deux poules de 5) ; les surnuméraires
  vont en dernier.
- **À l'intérieur d'un bloc, les archers sont ex æquo**, et un départage par décompte (§10.1) reste
  **optionnel**. Comparer des décomptes obtenus contre des adversaires différents n'a de valeur que
  si l'on en a besoin.
- **[ADR-0081] s'applique tel quel, et c'est ce qui rend l'option auto-régulée.** Une fenêtre qui
  *contient* un bloc est honorée (« les rangs 1 à 4 » sur 4 poules prend les quatre vainqueurs,
  ex æquo ou non) ; une fenêtre qui le *coupe* est refusée et annoncée (« les rangs 1 à 2 »), sauf
  départage activé. Le départage n'est donc nécessaire **que** quand la phase avale prélève à
  l'intérieur d'un bloc, et l'outil le dit au lieu de qualifier sur un ordre d'affichage.

⚠️ **Ce que cet ordre ne ferme pas** : sans départage, l'ordre interne d'un bloc pilote la **tête de
série** du tableau aval — le vainqueur de la poule 1 devient tête n°1 au seul motif que sa poule
porte le n°1. ADR-0081 ferme le cas des prélèvements *partiels* ; il subsiste pour un prélèvement qui
prend le bloc entier, où il est sans conséquence sur *qui* passe, mais pas sur *contre qui*.

**Aucune politique `seeding` neuve n'est requise** *(vérifié le 09/08/2026)* : le serpent sépare
naturellement les archers d'une même poule au premier tour — le 1ᵉʳ et le 2ᵉ d'une poule sont
distants de `P` rangs, et le serpent apparie des rangs de somme constante. Mesuré sans choc sur 4×2,
8×2, 4×4, 8×4, 16×2, 2×4 et 5×2. ⚠️ **Exception mesurée** : à effectif prélevé **non puissance de
2**, les byes décalent les paires et un choc redevient possible — 3 poules × 4 qualifiés produit
(rang 7, rang 10), tous deux de la poule 1. Signalé à l'atelier plutôt que corrigé : corriger
demanderait une politique de croisement, donc une règle métier que personne n'a demandée.

[ADR-0081]: 0081-une-phase-attend-que-sa-source-ait-departage-les-places-qu-elle-preleve.md

### 7. Le tir d'une rencontre réutilise la table `duel`

Une poule « n'invente pas une façon de tirer, seulement une façon d'apparier et de compter »
(`domain/poule.py`). Une rencontre est un **duel ordinaire** : le pavé de saisie d'E04US013, et la
table `duel` keyée `(phase_id, match_numero)`, sans table ni migration supplémentaires. La
numérotation des rencontres est **déterministe** (serpent + méthode du cercle), donc reconstructible
— même hypothèse que l'arbre d'un tableau, avec le même ancrage anti-ré-attribution par l'identité
des duellistes ([ADR-0049](0049-saisie-et-scoring-des-duels.md) §4).

## Conséquences

- **Un type de phase s'ajoute à un endroit**, non à dix. `E05US026` à `E05US028` en bénéficient
  directement ; c'est ce qui rend leur découpage tenable.
- **Une migration**, pour la seule table de placement des poules. Les réglages passent par
  `config.policies` (ADR-0046) et le tir par `duel` : ni l'un ni l'autre ne touche au schéma.
- **`DETTE-028` rétrécit sans se refermer.** Le suisse, la colline et le Big Shoot Off restent sans
  appelant, et `ScoreAvecHandicap` comme `RoutingRepechage` restent inertes. Le signal d'écart
  d'E01US024 doit donc cesser de viser les poules **et continuer de viser les trois autres** — sans
  quoi il mentirait pour ceux qui restent.
- **Le contrat sera éprouvé, pas figé.** Il est taillé sur un format ; les trois suivants diront
  s'il tient. Prétendre l'inverse serait exactement le défaut d'[ADR-0017](0017-le-depart-est-un-creneau-du-tournoi.md)
  — une intention présentée comme une décision.
- **Coût d'exécution** : la composition des poules relit le classement source, donc hérite de
  `DETTE-031` (reconstruction non mémoïsée). La mémoïsation *à l'intérieur d'un appel* suit le parti
  d'E05US024 ; le cache transverse n'est pas rouvert ici.

## Porté dans le code par

> ⚠️ Section vérifiée **sur le code du jour**, module par module, et non déduite de la décision
> ci-dessus (exigence de `CLAUDE.md`, née du défaut d'ADR-0017). Elle est **mise à jour au fil de la
> tranche** : ce qui suit décrit ce qui est **écrit et testé**, pas ce qui est prévu.

| Module | Ce qu'il porte |
|---|---|
| `backend/domain/poule.py` · `ReglageDePoules` | §4 — la taille visée, sa conversion `pour_effectif`, et §5 les deux régimes (`produit_un_classement` / `produit_des_qualifies`) |
| `backend/domain/poule.py` · `nb_poules_pour` | §4 — l'arrondi vers le bas et l'invariant « aucune poule sous la taille demandée » |
| `backend/domain/poule.py` · `couloirs_occupes` | §3 — l'empreinte par le parallélisme, `2 × (effectif ÷ 2)` |
| `backend/domain/placement_poules.py` | §3 — le bloc contigu, le débordement, l'accolement de la poule suivante, le rapport de conflits |
| `backend/domain/phase.py` · `Phase.poules` | §4 — le réglage porté par l'agrégat, et l'invariant « pas de réglage de poules sur un autre type » (`ReglageDePoulesInvalide`) |
| `backend/domain/contrat_phase.py` | §1 — le **registre** : une ligne par type, sept capacités, et les dix tables dérivées (`TYPES_EN_TABLEAU`, `TYPES_MONTES`, `TYPES_CLASSANTS_LUS`, `TYPES_EN_TABLEAU_JOUE`, `TYPES_JOUES`, `TYPES_SIGNALES_EN_ECART`, …) |
| `backend/domain/deroule.py` · `backend/application/{palmares,simulation_format,saisie_duels,placement_duels,routage}.py` | §1 — les sites **dérivés** ; aucun ne réécrit son filtre |
| `frontend/src/shared/phases/catalogue.ts` · `TYPES_SIGNALES_EN_ECART` | §1 — le miroir client, écrit **en négatif** (un oubli y coûte un avertissement de trop, jamais un de moins) |
| `backend/infrastructure/db/repositories/moteur.py` · `_lire_reglage_poules` | §4 — `config.policies.poules` (ADR-0046), **sans migration** ; barème toujours écrit, relu de ce qui est écrit |
| `backend/infrastructure/db/models.py` · `PlacementPouleORM` + `migrations/versions/0045_placement_des_poules.py` | §3 — « poule → couloirs », clé primaire sur le **couloir** (un couloir, un occupant) |
| `backend/application/poules.py` · `ServicePoules` | §3, §5, §6 — composition le jour J, pose du plan, rencontres par tour, couloirs dérivés, classement, saisie d'une rencontre |
| `backend/tests/test_domain_placement_poules.py` · `test_domain_reglage_poules.py` | §3, §4, §5 — écrits **depuis le CA** avant l'implémentation (règle 9) |
| `backend/tests/test_domain_contrat_phase.py` · `test_service_poules.py` · `test_placement_poule_repository.py` | §1, §3, §5, §6 |

### Restent à écrire dans cette tranche *(état au 09/08/2026, après six commits)*

**Volontairement absents du tableau ci-dessus** : nommer un module vide est précisément le défaut
qu'ADR-0017 a coûté treize mois.

1. **§4 — le classement d'une phase de poules n'est pas encore *lisible*.** `ServicePoules` produit
   le classement de chaque groupe, mais `ServiceSaisieDuels._classement_de_l_ordre` rend toujours
   `None` sur ce type, si bien que le CA « la phase avale consomme les qualifiés » **n'est pas
   livré**. `contrat_phase.py` porte donc `classement_lisible=False` pour les poules, et un test le
   verrouille — l'avoir mis à `True` par anticipation réclamait 34 inscrits pour un prélèvement que
   rien n'honore, soit le « refus abusif le jour J » d'E05US021. *(Défaut introduit puis refermé le
   09/08/2026 ; cf. le commit `fix(e05us023): le registre cesse d'annoncer…`.)*

   ✅ **L'arbitrage qui bloquait ce point est tranché** (09/08/2026, §6 ci-dessus) : « par rang de
   poule d'abord », tout le monde au classement, surnuméraires en dernier, départage interne
   optionnel. Il ne reste donc que du code, décrit ci-dessous.

   **Ce qu'il reste à écrire, dans l'ordre** :

   a. `application/poules.py` — une fonction rendant le `ClassementSource` de la phase depuis les
      `PouleAffichee` : concaténation par rang de poule, `plages_indecises` posées sur **chaque bloc
      non départagé** (c'est ce qui arme ADR-0081 et rend l'option auto-régulée), `rang_premier` lu
      par `tranche` comme pour un tableau.
   b. Un **port étroit** `LecteurClassementPoules` (patron de `LecteurPopulationPhase`, cf.
      `application/prelevement.py`) pour casser le cycle `ServicePoules` → `ServiceSaisieDuels`,
      **câblé à la main en `bootstrap/`** (règle 8) — l'un des deux services doit recevoir l'autre
      après construction, et c'est le genre de branchement qui doit se voir au composition root.
   c. La bascule `classement_lisible=True` dans `domain/contrat_phase.py`, et le retournement de
      `test_le_classement_dune_poule_nest_pas_encore_lisible_par_une_phase_avale`.
   d. Le **signalement** du choc de poule à l'atelier quand l'effectif prélevé n'est pas une
      puissance de 2 (§6, exception mesurée) — un avertissement, pas un refus.

2. **§5 — l'exposition du barrage de poule.** Le moteur est complet depuis E05US015, la portée
   `POULE` est câblée depuis E06US003, et `ServicePoules._verdicts_de_barrage` **relit déjà** les
   verdicts pour refermer le classement. Manque l'**annonce** depuis l'écran quand
   `PouleAffichee.barrage_requis` est vrai.

3. **L'exposition à l'atelier et en salle** : DTO Pydantic, endpoints `/api/v1`, fiche de réglages
   avec la répartition en direct (`ServicePoules.repartition` la rend déjà, sans exiger de salle ni
   de plan), écran de saisie des rencontres, et le **câblage en composition root** — `ServicePoules`
   n'est instancié nulle part aujourd'hui.

4. **`route_l_archer` reste `False`, et c'est hors périmètre** — à ne pas confondre avec le point 1.
   `application/routage.py` ne sait pas dire à un membre de poule où il tire ensuite ; ce n'est ni au
   CA ni à cette liste. Cette capacité-là attendra une US, quand les trois ci-dessus doivent être
   closes avant que la branche parte en revue.

5. **Les documents de fin d'US** : `docs/fonctionnel/E05US023.md`, `docs/dette.md` (DETTE-028
   rétrécie au périmètre poules, pas refermée), le journal d'avancement (résumé + fichier daté) et
   `SUIVI-US.md`.
