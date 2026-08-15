# ADR-0083 — Le contrat de phase jouable, et les poules pour le tailler

- **Statut** : Accepté
- **Date** : 2026-08-09, **amendé le 2026-08-14** (E05US028 — le contrat cède où le §2 l'annonçait :
  une capacité renommée, cf. § « Ce que le contrat a appris de sa **deuxième** mise à l'épreuve »)
- **Décideurs** : Organisateur / Architecte
- **Précise** : [ADR-0045](0045-sequence-de-phases-cycle-de-vie-typage-source.md) (typage ouvert des
  phases) · [ADR-0062](0062-catalogue-de-types-de-phase.md) (catalogue de types)
- **S'appuie sur** : [ADR-0046](0046-config-policies-politiques-nommees-parametrees.md)
  (le `config` JSON d'une étape) · [ADR-0024](0024-plan-de-cibles-materialise-ajustable.md) et
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

> ✅ **Le pari est tenu, et le contrat a cédé — d'un cran, à l'endroit prévu.** E05US028 (14/08/2026)
> n'a pas eu à redessiner les six questions : elle a renommé **une capacité**, dont le nom décrivait
> *comment* les types déjà écrits y répondaient au lieu de nommer la question. Détail au § « Ce que
> le contrat a appris de sa **deuxième** mise à l'épreuve ». Le choix de tailler sur les poules
> plutôt que sur le Big Shoot Off se confirme donc **a posteriori** : l'inverse aurait demandé de
> repasser sur du code livré, là où il n'a fallu qu'un `git mv` de vocabulaire.

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
  le `config` JSON de l'étape (ADR-0046) et le tir par `duel` : ni l'un ni l'autre ne touche au
  schéma. Le réglage vit **à la racine** du `config` — `config.policies` est le catalogue **fermé**
  des familles injectables, et un paramètre de phase n'en est pas une (arbitrage de revue, 10/08/2026).
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
> ci-dessus (exigence de `CLAUDE.md`, née du défaut d'ADR-0017). Elle a été **tenue au fil de la
> tranche** : ce qui suit décrit ce qui est **écrit et testé**, pas ce qui était prévu. La liste
> « Restent à écrire », qui vivait ici pendant la branche, a disparu au dernier commit — non pas
> effacée, mais **remplacée par les lignes qu'elle annonçait**, plus deux sections sur ce qui n'a
> volontairement pas été fait. C'est le régime que la règle de `CLAUDE.md` cherche : un ADR dont la
> section décrit un code vérifiable, jamais une intention.
>
> 🔄 **Re-vérifiée le 14/08/2026**, l'ADR étant rouvert par E05US028 (sa section *Décision* §2 a
> reçu le verdict du pari, et une capacité a été renommée).
>
> 🔄 **Re-vérifiée le 15/08/2026 à la revue d'E05US028, et c'est cette passe-là qui a corrigé le
> document.** La version du 14/08 affirmait, à trois endroits, que le service, le palmarès et le
> routage du Big Shoot Off « ne sont pas écrits » et que ses capacités restaient à `False` — vrai
> quand ces phrases ont été écrites, faux dans le commit qui les livrait, puisque le même diff les
> a écrits et a basculé les trois capacités à `True` (`domain/contrat_phase.py`). Le commit de
> rendu annonçait pourtant la section « re-vérifiée sur le code du jour » : elle ne l'avait pas
> été après coup.
>
> ⚠️ **C'est le défaut d'ADR-0017 à polarité inversée**, et il coûte autant. Ici l'ADR
> *sous-décrivait* le code au lieu de le sur-promettre — mais la prochaine US (E05US026, système
> suisse) l'aurait lu comme référence de contrat et y aurait trouvé écrit que le Big Shoot Off
> n'est ni classant ni routé. Un document périmé n'est pas *ambigu* : il s'écrit sans effort et il
> est faux, donc le garde-fou « CA ambigu » de la règle 9 ne se déclenche pas. La leçon est celle
> que `CLAUDE.md` énonce déjà et qu'il a fallu réapprendre : **écrire la section, c'est vérifier
> dans le code du jour** — et « re-vérifier » un ADR qu'on rouvre, c'est aussi relire ce qu'on y
> avait écrit la veille, pas seulement y ajouter des lignes.

| Module | Ce qu'il porte |
|---|---|
| `backend/domain/poule.py` · `ReglageDePoules` | §4 — la taille visée, sa conversion `pour_effectif`, et §5 les deux régimes (`produit_un_classement` / `produit_des_qualifies`) |
| `backend/domain/poule.py` · `nb_poules_pour` | §4 — l'arrondi vers le bas et l'invariant « aucune poule sous la taille demandée » |
| `backend/domain/poule.py` · `couloirs_occupes` | §3 — l'empreinte par le parallélisme, `2 × (effectif ÷ 2)` |
| `backend/domain/placement_poules.py` | §3 — le bloc contigu, le débordement, l'accolement de la poule suivante, le rapport de conflits |
| `backend/domain/phase.py` · `Phase.poules` | §4 — le réglage porté par l'agrégat, et l'invariant « pas de réglage de poules sur un autre type » (`ReglageDePoulesInvalide`) |
| `backend/domain/contrat_phase.py` | §1 — le **registre** : une ligne par type, sept capacités, et les dix tables dérivées (`TYPES_EN_TABLEAU`, `TYPES_DEROULES`, `TYPES_CLASSANTS_LUS`, `TYPES_EN_TABLEAU_JOUE`, `TYPES_JOUES`, `TYPES_SIGNALES_EN_ECART`, …) |
| `backend/domain/contrat_phase.py` · `deroule_par_un_service` · `TYPES_DEROULES` | §1 — la capacité **renommée le 14/08/2026** (ex-`monte_les_oppositions` / `TYPES_MONTES`) : elle nomme la *question*, plus la forme que prend la réponse. ⚠️ Vérifié sur le code du 15/08/2026 : la ligne `BIG_SHOOT_OFF` bascule ses trois capacités (`deroule_par_un_service`, `classement_lisible`, `route_l_archer`) à `True` **en fin de tranche E05US028**, une fois les modules ci-dessous écrits — la discipline d'E05US023 pour les poules, tenue à l'identique |
| `backend/domain/contrat_phase.py` · `route_tout_le_plateau` · `TYPES_ROUTES_IMPLICITEMENT` | §1 — 8ᵉ capacité, ajoutée à la **revue d'E05US028** sur un défaut constaté : `route_l_archer` disait « sait-on router cet archer ? » sans dire *combien d'archers* la phase concerne. Les deux questions se confondaient tant que seul un tableau routait ; le Big Shoot Off les sépare (8 finalistes sur 120), et sans la distinction il captait la résolution **implicite** du panneau — les non-finalistes lisaient « ne fait pas partie de ce Big Shoot Off » au lieu de leur rang final |
| `backend/domain/deroule.py` · `_TYPES_DEROULES` | §1 — seul consommateur de la table ; l'alias local devient homonyme, comme `_TYPES_CLASSANTS_LUS` juste à côté |
| `backend/domain/{phase,deroule_etape,format_tournoi}.py` · `big_shoot_off` · `backend/infrastructure/db/repositories/moteur.py` · `_lire_reglage_big_shoot_off` | §4 — le **précédent appliqué** : un réglage de format vit dans `config` à la racine, **sans migration**, exactement comme `config.poules`. Écrit le 14/08/2026 pour le Big Shoot Off |
| `backend/application/big_shoot_off.py` · `ServiceBigShootOff` | §1, §7 — le service qui rend le format jouable : projection, rejeu de la phase depuis les volées **validées**, saisie, validation par manche. ⚠️ **Le §7 s'applique à un second format** — là où une rencontre de poule réutilise `duel`, une manche de Big Shoot Off réutilise `serie`/`volee` (clé `(phase_id, archer_id)` depuis E05US025), **sans table ni migration** |
| `backend/application/big_shoot_off.py` · `LecteurEtatBigShootOff` · `backend/application/prelevement.py` · `LecteurClassementBigShootOff` | §1 — les deux ports étroits du format. Le second est un **jumeau volontairement dupliqué** de `LecteurClassementPoules` : 2ᵉ occurrence, pas 3ᵉ, donc le remède structurel attend E05US026 (règle « remède structurel » de `CLAUDE.md`) |
| `backend/application/saisie_duels.py` · `_classement_de_l_ordre` | §1 — 4ᵉ cas de résolution d'un ordre amont : un prélèvement visant un Big Shoot Off cesse d'être inerte |
| `backend/application/palmares.py` · `_resultat_big_shoot_off` | §1 — l'entrée au palmarès par un **`_resultat` propre au format**, pas par `TYPES_RECONSTRUCTIBLES` : ses rangs sont exacts sans arbre à rejouer. C'est la condition d'entrée que la section « ce que la tranche n'a pas fait » annonçait pour les poules |
| `backend/application/routage.py` · `_routage_big_shoot_off` · `ProchaineManche` · `IssueRoutage.PROCHAINE_MANCHE` | §1 (5ᵉ question) — le routage sait dire **quelle manche** vient et **combien sortent**. ⚠️ Pas **où** : `plan_de_cibles` reste `AUCUN` et le manque est nommé (`DETTE-059`), pas tu |
| `backend/api/v1/big_shoot_off.py` · `backend/api/v1/{phases,formats}.py` · `ReglageBigShootOffDTO` | §4 — le réglage traverse la frontière sur les **deux** mailles de composition (4ᵉ paire de jumeaux, `DETTE-054` élargie) |
| `frontend/src/shared/phases/{bigShootOff.ts,ReglageBigShootOff.tsx}` | §4 — la fiche **sans état** partagée par les deux écrans de composition, et la projection des paliers (miroir assumé de `paliers_pour`, 16 tests) |
| `frontend/src/features/big-shoot-off/SaisieBigShootOff.tsx` | §1 — la **ligne de tir**, et non le pavé de duel : `DecorDeSaisie.VOLEE_COLLECTIVE` n'a pas d'adversaire. ⚠️ Pas de file hors-ligne (`DETTE-060`) — elle transporte un acte de *duel* |
| `backend/tests/test_domain_big_shoot_off.py` | La règle élargie du 14/08/2026, écrite **depuis le CA avant l'implémentation** (règle 9) — c'est ce test qui a fait sortir la contradiction du CA |
| `backend/domain/deroule.py` · `backend/application/{palmares,simulation_format,saisie_duels,placement_duels,routage}.py` | §1 — les sites **dérivés** ; aucun ne réécrit son filtre |
| `frontend/src/shared/phases/catalogue.ts` · `TYPES_SIGNALES_EN_ECART` | §1 — le miroir client, écrit **en négatif** (un oubli y coûte un avertissement de trop, jamais un de moins) |
| `backend/infrastructure/db/repositories/moteur.py` · `_lire_reglage_poules` | §4 — `config.poules`, à la racine du `config` (ADR-0046), **sans migration** ; barème toujours écrit, relu de ce qui est écrit |
| `backend/infrastructure/db/models.py` · `PlacementPouleORM` + `migrations/versions/0045_placement_des_poules.py` | §3 — « poule → couloirs », clé primaire sur le **couloir** (un couloir, un occupant) |
| `backend/application/poules.py` · `ServicePoules` | §3, §5, §6 — composition le jour J, pose du plan, rencontres par tour, couloirs dérivés, classement, saisie d'une rencontre, et `classement_de_phase` (le port ci-dessous) |
| `backend/domain/classement_de_poules.py` | §6 — l'ordre « par rang de poule d'abord », les blocs **indécis** (ADR-0081), la liaison d'un ex æquo interne qui enjambe deux blocs, et le départage optionnel. ⚠️ **Descendu dans le domaine** alors que la liste de tranche — supprimée à la clôture — l'annonçait en `application/poules.py` : il croise des `RangPoule`, un `LigneClassement` et une politique `Tiebreak` — l'argument exact qui a placé son jumeau `classement_de_tableau` là |
| `backend/domain/poule.py` · `ReglageDePoules.departage_inter_poules` | §6 — le départage optionnel, persisté sous `config.poules.departage` (toujours sans migration) |
| `backend/application/prelevement.py` · `LecteurClassementPoules` | §6 — le **port étroit** qui casse le cycle `ServicePoules` ↔ `ServiceSaisieDuels`, et qui fait traverser le résolveur (donc le cache de reconstruction **et** la chaîne anti-boucle) |
| `backend/application/saisie_duels.py` · `brancher_poules` / `_classement_de_l_ordre` | §6 — le 3ᵉ cas de résolution d'un ordre amont : une phase de poules a désormais un classement lisible |
| `backend/domain/deroule.py` · `_anomalies_choc_de_poule` | §6 (exception mesurée) — l'avertissement d'atelier quand un tableau nourri par des poules peut réunir deux membres d'un même groupe au premier tour. Prédicat **exact**, confronté à l'appariement du serpent sur 9945 configurations : nombre de poules **impair** *et* paire fautive dans le prélèvement ; plus les trois cas où l'arithmétique ne s'applique pas (départage inter-poules, poules de tailles inégales, nombre de poules inconnu). ⚠️ L'oracle « effectif non puissance de 2 » qui figurait ici était **faux** — corrigé en revue le 10/08/2026 |
| `backend/api/v1/poules.py` | §3, §5, §7 — répartition, état, pose du plan (admin), et les trois écritures de tir du scoreur, qui renvoient **le même DTO de duel** que `saisie_duels` |
| `backend/api/v1/{phases,formats}.py` · `ReglagePoulesDTO` | §4 — le réglage traverse la frontière, sur les deux mailles de composition (jumeaux assumés, `DETTE-054`) |
| `backend/bootstrap/composition.py` | §1 — `ServicePoules` instancié, et le **branchement tardif** du port rendu visible au composition root (règle 8) |
| `frontend/src/shared/phases/{poules.ts,ReglagePoules.tsx}` | §4, §5, §6 — la fiche de réglages **sans état** partagée par les deux écrans de composition, et l'aperçu de répartition (miroir assumé du serpent du domaine) |
| `frontend/src/features/poules/SaisiePoules.tsx` | §3, §5, §7 — la **navigation** par poule et par tour, l'annonce du barrage requis, et le pavé de duel remonté tel quel (`DuelCharge`, famille `poule`) |
| `frontend/src/shared/stores/fileDuelsHorsLigneStore.ts` · `FamilleDuel` | §7 — un acte de rencontre de poule entre dans la **même** file hors-ligne et s'y rejoue (E04US009) |
| `backend/tests/test_domain_placement_poules.py` · `test_domain_reglage_poules.py` · `test_domain_classement_de_poules.py` | §3, §4, §5, §6 — écrits **depuis le CA** avant l'implémentation (règle 9) |
| `backend/tests/test_domain_contrat_phase.py` · `test_service_poules.py` · `test_placement_poule_repository.py` · `test_poules_api.py` | §1, §3, §5, §6 — dont le seul test qui éprouve le branchement tardif de bout en bout |

### Ce que la tranche n'a **pas** fait, et qui n'est pas un oubli

1. **`route_l_archer` reste `False`.** `application/routage.py` ne sait pas dire à un membre de
   poule où il tire ensuite. Ce n'est ni au CA ni à cette tranche ; la capacité attendra une US.
2. **Les poules n'entrent pas au palmarès** (`TYPES_RECONSTRUCTIBLES` est resté l'alias de
   `TYPES_EN_TABLEAU_JOUE`). L'y verser demanderait un `_resultat` propre au format, pas une entrée
   de plus dans une table.
3. **Le forfait en poule** n'est offert nulle part : l'écran de saisie masque le bouton hors
   tableau. Un abandon en poule n'est pas un *walkover* — la règle n'a pas été posée.
4. **`DETTE-028` rétrécit sans se refermer** : le suisse, la colline et le Big Shoot Off restent
   sans appelant, `ScoreAvecHandicap` et `RoutingRepechage` restent inertes. Le signal d'écart cesse
   de viser les poules **et continue de viser** les autres — dérivé du registre, donc il ne peut
   plus mentir type par type.

### Ce que le contrat a déjà appris de sa première mise à l'épreuve

Le contrat a tenu sur les poules, mais deux choses valent d'être notées avant `E05US028` :

- **`DecorDeSaisie` a suffi, `PlanDeCibles` aussi**, sans élargissement. Le décor
  `RENCONTRES_EN_GROUPES` n'a rien changé au *pavé* : c'est la navigation qu'il désigne, et c'est
  exactement ce que §7 prévoyait.
- **La 4ᵉ question s'est révélée être deux questions**, pas une. `produit_un_classement` et
  `classement_lisible` existaient déjà ; il a fallu leur adjoindre une **troisième** information que
  le contrat ne porte pas — *ce classement est-il départagé, et jusqu'où ?* Elle vit dans
  `ClassementSource.plages_indecises` (ADR-0081), donc hors du registre. Ce n'est pas un défaut du
  contrat : c'est une propriété de la **donnée**, pas du type. Mais un lecteur qui chercherait la
  réponse dans le registre ne l'y trouverait pas, et c'est le genre d'angle mort qui coûte cher.

### Ce que le contrat a appris de sa **deuxième** mise à l'épreuve (E05US028, 14/08/2026)

Le Big Shoot Off était l'épreuve annoncée au §2. Le contrat a tenu, **sauf sur un nom** — et c'est
la forme la plus intéressante d'échec, parce qu'elle ne se voit pas à la compilation.

**Le constat.** `monte_les_oppositions` valait `True` « quand un service de production monte
réellement les matchs/groupes de ce type ». Un Big Shoot Off n'a **ni matchs ni groupes** : il fait
tirer une volée collective, tout le monde sur la ligne. Une fois son service écrit, aucune des deux
valeurs n'était juste :

- `True` contredisait la **définition écrite** de la capacité — on aurait affirmé qu'un service
  monte des oppositions qui n'existent pas ;
- `False` faisait mentir tout ce qui en dérive : `TYPES_JOUES` aurait exclu le Big Shoot Off, donc
  l'atelier aurait continué de le signaler « composable mais pas jouable » (E01US024) sur un format
  désormais joué de bout en bout, et son prélèvement n'aurait pas relevé le plancher d'inscrits
  (E05US021).

**Ce que ça dit, et qui vaut au-delà du cas.** Quand aucune valeur d'un booléen n'est défendable,
ce n'est pas un cas particulier à traiter par une exception : c'est que le **nom** est plus étroit
que la question. La capacité a toujours répondu à « *un service de production exécute-t-il ce
type ?* » ; son nom, lui, décrivait la **forme** que prenait la réponse pour les deux seuls types
qui l'avaient à `True` au moment de l'écrire (élimination directe, poules — tous deux à
oppositions). Le premier format d'une autre forme l'a rendue inrépondable.

**Décision** — la capacité est renommée `deroule_par_un_service`, et sa table dérivée
`TYPES_MONTES` devient `TYPES_DEROULES`. Le verbe « dérouler » n'est pas neuf : c'est celui
qu'emploient déjà `domain/deroule.py`, `_TYPES_DEROULES` et le message d'atelier « le moteur ne sait
pas encore dérouler ce type ». Le renommage **retire** donc un vocabulaire concurrent au lieu d'en
ajouter un — `deroule._TYPES_DEROULES = TYPES_DEROULES` devient un alias local homonyme, comme
`_TYPES_CLASSANTS_LUS` juste à côté.

**Portée du changement** : quatre fichiers, aucun front (la capacité n'a pas de miroir client — seul
`TYPES_SIGNALES_EN_ECART` en a un, et il dérive, donc il suit sans être touché). Aucune migration :
c'est du vocabulaire de code, rien n'en est persisté.

**Ce qui n'a pas bougé, et qui était le vrai pari** : les **six questions**, `DecorDeSaisie`
(`VOLEE_COLLECTIVE` existait déjà), `PlanDeCibles`, et le grain — `FIN_DE_SERIE` était admis pour ce
type depuis E05US015. Le §2 pariait qu'un contrat taillé sur le format le plus riche accueillerait
le plus pauvre au prix d'un assouplissement ; le prix s'est révélé être **un mot**, pas une
structure. C'est la confirmation *a posteriori* du choix de tailler sur les poules : l'ordre inverse
aurait demandé de repasser sur du code déjà livré.

⚠️ **Ce paragraphe portait, jusqu'au 15/08/2026, l'affirmation inverse du code livré** : « au
14/08/2026, `classement_lisible` et `route_l_archer` du Big Shoot Off sont toujours à `False` : son
service, son entrée au palmarès et son routage ne sont pas écrits ». C'était exact à l'instant où
la phrase a été écrite, et faux dans le commit qui l'a livrée — E05US028 a écrit les trois et
basculé les trois capacités dans le même diff.

La discipline qu'il énonçait reste la bonne, et elle a été tenue : **on ne bascule une capacité
qu'une fois le code écrit**, jamais « puisque l'US est en cours » — c'est ce qui a évité de
reproduire `DETTE-028`. Ce qui a manqué, c'est la relecture de la phrase **en fin de tranche**, une
fois la bascule faite. Une note d'état datée survit mal à l'US qui la périme : celle-ci est
conservée comme trace de l'erreur plutôt que supprimée, puisqu'elle documente le mode de défaillance
que la section « Porté dans le code par » existe pour empêcher.

