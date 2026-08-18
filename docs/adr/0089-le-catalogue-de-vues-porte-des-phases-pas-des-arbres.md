# ADR-0089 — Le catalogue de vues porte des **phases**, pas des arbres

- **Statut** : Accepté
- **Date** : 2026-08-18
- **Décideurs** : Organisateur / Architecte
- **Révise** : [ADR-0064](0064-ecran-de-salle-poste-type-et-pilotage-par-etat-lu.md) (l'écran de salle
  est un poste typé) — dont le catalogue `VueEcran` supposait, sans le dire, qu'une phase se dessine
  en arbre
- **S'appuie sur** : [ADR-0079](0079-un-seul-interrupteur-mes-archers-pour-tout-l-onglet-public.md)
  (un seul interrupteur « mes archers ») · [ADR-0083](0083-le-contrat-de-phase-jouable.md) (le
  contrat de phase jouable) · [ADR-0076](0076-un-deroule-defini-une-fois-un-avancement-par-depart.md)
  (un avancement par départ, qui donne son ordre au fil du déroulé)
- **Porté dans le code par** :
  `backend/domain/ecran.py` (`VueEcran.EN_COURS`) ·
  `backend/migrations/versions/0047_vue_en_cours.py` (le renommage de la valeur persistée) ·
  `backend/api/v1/big_shoot_off.py` (`EtatPubliqueReponse`, `TireurPubliqueReponse`,
  `ManchePubliqueReponse`, `FormatPubliqueReponse`, la route ouverte `GET /etat/` et la route
  scoreur `GET /saisie/`) ·
  `frontend/src/features/ecrans/api.ts` (`VueEcran`, `LIBELLE_VUE`, `TOUTES_LES_VUES` — le
  catalogue côté front, second exemplaire de celui du domaine) ·
  `frontend/src/features/en-cours/VueEnCours.tsx` (l'aiguilleur et son `switch` exhaustif) ·
  `frontend/src/features/en-cours/presentation.ts` (`phaseAAtterrir`) ·
  `frontend/src/features/poules/VuePoulesPublique.tsx` ·
  `frontend/src/features/suisse/VueSuissePublique.tsx` ·
  `frontend/src/features/big-shoot-off/VueBigShootOffPublique.tsx` ·
  `frontend/src/shared/duels/rencontre.ts` et
  `frontend/src/shared/duels/LigneRencontre.tsx` (la lecture publique commune) ·
  `frontend/src/features/tableaux/VueTableaux.tsx` (la prop `phaseId`, qui rend l'arbre pilotable
  de l'extérieur) ·
  `frontend/src/features/public/AccueilPublic.tsx` et
  `frontend/src/features/salle/EcranSalle.tsx` (les deux surfaces qui montent la vue)

## Contexte et problème

Trois formats sans arbre ont été livrés **jouables de bout en bout** en trois semaines : les poules
(`E05US023`), le Big Shoot Off (`E05US028`) et le système suisse (`E05US026` pour le moteur,
`E05US030` pour l'écran). Aucun des trois n'a jamais atteint l'**application publique** ni l'**écran
de salle**.

Le manque n'a pas été vu plus tôt parce qu'il ne ressemble pas à un manque. Chacune de ces US
livrait un écran de saisie et un écran d'organisation complets ; ce qui n'existait pas était la
surface *ouverte*, qui n'appartient à aucune des trois — elle appartient au **catalogue de vues**
posé par ADR-0064. Or ce catalogue portait une valeur nommée `TABLEAUX`, dont la docstring disait
« les **arbres de duels** du tournoi », et une vue front (`VueTableaux`) qui ne sait dessiner qu'un
arbre. Il n'y avait donc aucun endroit où poser une poule : le trou était dans la **forme** du
catalogue, pas dans les US qui n'y avaient rien mis.

La demande d'origine, formulée au cadrage d'`E05US030` le 16/08/2026, était « une vue publique du
système suisse ». L'instruire a montré que la livrer telle quelle aurait figé une **troisième**
variante locale — un onglet de plus, propre à un format —, et laissé le trou ouvert aux deux tiers.

Une question restait à trancher, et elle n'est pas cosmétique : **sous quel nom**. Trois candidats,
trois vérités différentes.

## Décision

### 1. La vue s'appelle **« En cours »** et montre la phase qui se joue, quel que soit son format

`VueEcran.TABLEAUX` devient `VueEcran.EN_COURS`, et l'onglet public « Tableaux » devient « En
cours ». La vue rend l'arbre de duels comme avant, et en plus la poule, la ronde de système suisse
et la manche de Big Shoot Off.

**Pourquoi pas garder « Tableaux ».** Le glossaire définit `Tableau` comme un « arbre de matchs à
élimination » : c'est le nom d'un **format**, pas d'un contenant. Le garder sur une vue qui rend
aussi une poule aurait fait dire au code et à la base quelque chose de faux — la règle 3 exige un
vocabulaire cohérent entre code, API, UI et doc, et c'est exactement le genre d'écart qui ne se
rattrape jamais parce qu'il ne casse rien.

**Pourquoi pas « Phases ».** C'était le mot **juste** du domaine, et il a été proposé — puis écarté
par le commanditaire le 18/08/2026, sur un argument de destinataire : la surface est publique, et un
spectateur ne manie pas ce vocabulaire. « En cours » ne nomme aucun format, dit ce que l'écran fait,
et restera vrai quand un dixième type de phase arrivera.

⚠️ **Le nom porte une inexactitude assumée** : avec l'historique (§3), l'onglet n'est plus
*strictement* « en cours ». Ce qui le rend honnête est l'**atterrissage** — la phase qui se joue est
celle qu'on voit en arrivant, remonter est un geste volontaire.

### 2. Le renommage passe par une **migration**, il ne se contente pas d'un libellé

La valeur `"tableaux"` est persistée dans `poste.deroule_json`. La migration `0047` la réécrit en
`"en_cours"`, et sait redescendre.

C'est l'arbitrage de la `0046` (`placement_poule` → `placement_par_bloc`, `E05US026`) appliqué au
même critère, et le rapprochement est le cœur de la décision : **ce n'est pas un synonyme mal choisi,
c'est le mauvais concept**. `position` pour « couloir de tir » (`DETTE-042`) désigne la bonne chose
sous un mot tiède, et l'arbitrage y fut inverse — ne pas migrer. Ici, un lecteur qui trouve
`"vue": "tableaux"` dans le déroulé d'un écran projetant des poules ne se demande pas si le mot est
le bon : il se demande **ce qui a bien pu écrire ça**.

⚠️ **Conséquence pour la lecture d'ADR-0064.** Son §1 se félicitait, à juste titre, que le catalogue
se soit élargi **trois fois sans une seule migration** — la preuve que persister la chaîne valait
mieux qu'un rang. La propriété reste vraie et n'est pas remise en cause : elle rend un **ajout**
gratuit. Elle ne dit rien d'un **renommage**, et la lire comme « le catalogue ne coûte jamais de
migration » serait un contresens. C'est la seule chose que cet ADR retire au précédent.

### 3. L'historique est une **navigation dans le déroulé du départ**, pas un journal

L'onglet atterrit sur la phase courante et laisse remonter aux précédentes. `phaseAAtterrir` prend
**la phase démarrée de rang le plus élevé**, sinon la première non terminée, sinon la dernière.

⚠️ **Les deux premières règles ne sont pas interchangeables, et la revue l'a démontré.** Une première
version se contentait de « la première non terminée », transposée de `VueTableaux`. La transposition
était fausse d'un cran : `VueTableaux` se cale sur `est_termine`, **calculé** à partir des duels,
tandis que `StatutPhase` est **déclaratif** — aucun service de tir ne le consulte pour accepter un
score, et rien n'oblige à clore la phase N avant de démarrer la N+1. Une qualification qu'on oublie
de passer à « Terminée » figeait donc l'onglet **et le projecteur** sur « il n'y a pas de rencontre à
suivre » pendant qu'on tirait les duels — sans recours, `interactif={false}` masquant le fil du
déroulé. C'est la première surface du produit **sans opérateur devant elle** dont le contenu dépend
d'une case à cocher.

À l'intérieur d'une phase, la profondeur d'historique est **dictée par la forme du format** et non
par un composant commun :

- une **poule** est un round-robin sur un plateau : tous ses tours tiennent à l'écran, on les affiche
  tous. Rien à bâtir ;
- un **Big Shoot Off** se lit en tableau (un tireur par ligne, une manche par colonne) : les manches
  jouées sont visibles d'emblée. Rien à bâtir non plus ;
- un **système suisse** ré-apparie tout le plateau à chaque ronde : les afficher toutes noierait la
  ronde en cours, la seule que la salle regarde. C'est le **seul** des trois à recevoir une
  navigation.

Inventer une navigation uniforme pour les trois aurait coûté trois fois plus et rendu deux écrans
moins lisibles.

### 4. Le **Big Shoot Off** reçoit la surface publique qui lui manquait

`GET /api/v1/big-shoot-off/etat/` devient **ouverte** et sert un DTO restreint neuf ; la lecture du
scoreur migre sur `/saisie/`. C'est le couple exact que `poules.py` et `suisse.py` portent déjà, et
l'asymétrie n'avait aucune raison d'être.

⚠️ **La justification de l'ancienne frontière était fausse, et c'est le point à retenir.** L'en-tête
du routeur affirmait que l'état devait rester scoreur parce qu'« il porte les scores manche par
manche, donc ce que le public n'a pas à voir **avant validation** ». Vérification faite :
`_scores_par_manche` ne rend que les manches **entièrement validées** et s'arrête à la première
incomplète. Le secret invoqué n'existait pas — la couche application le protégeait déjà, un cran
plus bas. Ce qui distingue réellement les deux formes est l'**adressage de saisie**
(`prochaine_volee`, `volees`), qui n'a de sens que devant un pavé. Une frontière **crue** tenue pour
une raison qui n'est pas la sienne est plus dangereuse qu'une frontière absente : personne ne la
vérifie.

Le DTO est **distinct**, jamais un `exclude` — troisième application de la règle que `poules.py`
puis `suisse.py` ont chacun dû apprendre en revue.

### 5. La rupture de contrat est assumée plutôt que contournée

`/etat/` change de forme au lieu qu'un `/public/` s'ajoute à côté. `/api/v1` n'a qu'**un seul
client**, livré dans le même bundle par le même serveur (mono-club, réseau local — règle 12) : il
n'existe aucun consommateur tiers à ménager, et laisser deux routes servir la même photo aurait figé
pour de bon l'asymétrie entre les trois formats.

## Conséquences

- **L'onglet public passe de six vues à six vues**, dont une change de nature : c'est le seul endroit
  où un spectateur suit une rencontre, quel que soit le format. Le trou des trois formats est comblé
  d'un coup plutôt qu'un tiers à la fois.
- **`VueTableaux` devient pilotable de l'extérieur** (prop `phaseId`) et éteint alors son sélecteur
  local. Deux barres de choix concurrentes sur le même écran donneraient deux vérités
  contradictoires — le défaut qu'`E16US004` avait déjà corrigé sur la bascule « mes archers » de
  cette même vue.
- **L'aiguillage est gardé par le compilateur** : le `switch` de `VueEnCours` se termine par une
  affectation à `never`, donc ajouter un type à `TypePhase` sans lui donner de branche **ne compile
  pas**. Une première rédaction doublait ce garde d'une table « types dessinés » dans
  `presentation.ts` : elle a été retirée, une table se désynchronisant en silence là où le `switch`
  est vérifié.
- **La colline reste non dessinée**, et l'écran le **dit** au lieu de rendre une page blanche. La
  branche disparaîtra avec `E05US027`.
- **`decrirePlaces` remonte dans `shared/salle/place.ts`**, auprès du type qu'elle manipule, et
  `features/suisse/presentation.ts` la ré-exporte. L'onglet en a besoin pour deux formats ; l'importer
  d'une feature depuis `shared/` aurait rouvert l'inversion que ce module documente comme la seule du
  front.
- **`VueTableaux` n'a pas été migrée sur `LigneRencontre`.** Son `LigneDuel` garde ses classes
  `tableaux__*` et sa feuille calibrée sur deux surfaces ; la refondre aurait mêlé un remaniement de
  l'existant à cette US sans bénéfice pour le CA. La duplication restante est **bornée à deux
  rendus** et nommée dans le code — pas une dette silencieuse, un point d'entrée.
- ⚠️ **La section « Porté dans le code par » est machine-lue, et sa forme compte autant que son
  contenu.** Le vérificateur d'atlas ne reconnaît un chemin qu'à sa racine (`backend/…`,
  `frontend/…`, `docs/…`) : une première rédaction en laissait cinq sans préfixe, qui étaient
  silencieusement jetés — donc **hors du seul contrôle qui vérifie les promesses** — pendant que
  leurs symboles retombaient sur les modules voisins, y produisant huit faux signaux. C'est le
  défaut d'ADR-0017 à l'envers : non pas un module vide nommé, mais de vrais modules placés hors de
  portée du vérificateur. Corollaire découvert dans le même geste : **on n'écrit pas de prose dans
  cette section** — le paragraphe qui expliquait ce piège y citait des racines de chemin, que le
  parseur a lues comme trois promesses de plus. D'où sa place ici.
- **Ce que cet ADR ne tranche pas** : `E05US032` (l'organisateur ouvre la ronde suivante) rouvrira la
  dérivation à la lecture du système suisse. Rien ici n'y touche — l'onglet lit l'état, il ne le fait
  pas avancer.

## Alternatives écartées

- **Un onglet public par format** (« Poules », « Suisse », « Big Shoot Off »). Additif et sans
  risque, mais le spectateur doit deviner lequel regarder, et trois onglets sur quatre sont vides à
  tout instant. C'est aussi ce qui aurait figé la troisième variante locale que le cadrage cherchait
  précisément à éviter.
- **Élargir « Tableaux » sans le renommer.** Aucune migration, mais la base et le code auraient dit
  « tableau » d'une poule. Écarté sur la règle 3 — cf. §2.
- **Nommer la vue « Phases ».** Exact au sens du domaine, cohérent avec l'écran d'organisation A07,
  et écarté sur le destinataire : la surface est publique.
- **Ajouter `/big-shoot-off/public/` à côté de `/etat/`.** Aucune rupture de contrat, mais deux
  routes pour la même photo et l'asymétrie entre les trois formats installée pour de bon.
- **Un composant d'historique commun aux trois formats.** Uniforme sur le papier, plus cher et moins
  lisible en salle : deux des trois formats n'en ont aucun besoin (§3).
