# ADR-0079 — Un seul interrupteur « mes archers / tout » pour tout l'onglet public

- **Statut** : accepté
- **Date** : 08/08/2026
- **Contexte** : lot « retours du questionnaire de maquettes » (E16US004), questionnaires **P01**,
  **P02**, **P03**, **P05**
- **Remplace** : la lecture locale « Mon chemin / Tableau complet » de
  [E07US005](../../stories/E07-affichage-public.md). **Complète**
  [ADR-0039](0039-exposition-publique-du-deroule-scores-provisoires.md) (lecture publique anonyme du
  déroulé) et [ADR-0075](0075-le-depart-est-la-portee-sportive.md) (portée du départ).

## Contexte

Le socle « suivre plusieurs archers » existait depuis E07US006, mais **seule la carte de suivi s'en
servait**. Les cinq autres vues publiques — classement, affectations, tableaux, palmarès, plan de
cibles — ignoraient la liste des suivis, alors que quatre questionnaires demandaient de pouvoir les
lire centrées : *« il me faut les 2 »* (P03, sur le classement), *« une bascule pour suivre tous les
tableaux du tournoi ou uniquement centré sur les archers que l'on choisit de suivre »* (P05).

Une seule vue portait déjà une bascule de ce genre : `VueTableaux`, avec son sélecteur local
« Mon chemin / Tableau complet ». La question posée par E16US004 était donc : **généralise-t-on ce
sélecteur vue par vue, ou remonte-t-on le choix d'un cran ?**

## Décision

### 1. Un interrupteur unique, en tête de l'écran public

Le spectateur choisit **une fois** « je regarde mes archers » et ne le redit pas à chaque onglet.
L'alternative — un sélecteur par vue — est écartée : elle obligeait à répéter le même geste six
fois, et surtout elle rendait deux interrupteurs simultanément visibles sur l'écran « Tableaux »,
où le sélecteur local et l'interrupteur global auraient fini par se contredire.

**Conséquence assumée** : la combinaison « mon chemin sur les tableaux **et** classement complet »
n'est plus exprimable. C'est une perte réelle par rapport à E07US005, jugée acceptable — personne
ne l'avait demandée, et le coût du doublon contradictoire est certain quand celui de la perte est
hypothétique.

### 2. Le mode descend en prop ; il n'est **jamais** lu au store dans une vue partagée

`VueClassement`, `VueTableaux`, `VueAffectations` et `VuePalmares` servent **aussi** la coquille
admin et l'écran de salle. Une lecture directe du store public y ferait fuir le filtre sur des
surfaces qui n'en veulent pas — un classement d'organisation amputé, un écran projeté centré sur les
archers d'un spectateur au hasard. Le mode et la liste des suivis descendent donc de `AccueilPublic`
en **props explicites**, comme `filtrable` et `interactif` avant eux.

Corollaire : la règle vaut aussi pour la **liste** des suivis, pas seulement pour le mode. La revue
d'E16US004 a trouvé `VueTableaux` en exception — elle recevait `mode` en prop mais rebâtissait
`suivis` depuis le store —, ce qui rendait l'invariant invérifiable et abonnait l'écran de salle à
un store dont il n'a que faire.

### 3. Trois surfaces ne sont **jamais** centrées

- **Les podiums** (palmarès) : un podium amputé de ses médaillés ne répond plus à « qui a gagné »,
  la seule question que cet écran serve. Seul le classement final est centré.
- **Les barrages et le départage manuel** (classement) : surfaces d'**organisation**. Une liste
  amputée y ferait proposer un barrage entre deux archers sur trois.
- **Le pas de tir groupé par butte** (affectations) : la cible reste **entière, adversaire compris**.
  Sur un tableau de duels, le voisin de butte *est* l'adversaire ; le filtrer revient à cacher contre
  qui l'archer suivi tire. Même règle que `centrerCibles` pour le plan de cibles.

### 4. Le mode **retombe** sur « tout » quand aucun archer n'est suivi sur ce tournoi

La préférence est **globale** (une façon de lire), les suivis sont **par tournoi** (plusieurs
tournois `EN_COURS` en parallèle est une capacité voulue). Sans ce garde, ouvrir un second tournoi
viderait les cinq écrans publics d'un coup sans rien expliquer.

### 5. La préférence est **armée par défaut**

Le CA d'E07US005 promet que « la lecture *Mon chemin* est celle par défaut **dès qu'on suit
quelqu'un** », et `D-09` ouvre déjà l'onglet « Suivi » d'office pour la même raison : qui a désigné
ses archers a dit ce qu'il venait regarder. L'interrupteur unique ayant dissous les défauts **par
vue**, laisser la préférence à `false` aurait **révoqué ce CA en silence** — le défaut d'une US
livrée disparaissant comme effet de bord d'une autre.

*Arbitrage rendu par le commanditaire le 08/08/2026, en revue* : l'ouverture se fait **centrée**. Le
point 4 rend la valeur inoffensive quand il n'y a personne à centrer — « armée » ne veut jamais dire
« écran vide ».

### 6. Chaque vue nomme « aucun de vos archers ici » distinctement de son propre vide

Le cas est banal — un suivi engagé le matin quand on regarde le créneau de l'après-midi — et un
écran qui se vide sans rien dire se lit comme une panne. Chaque vue distingue donc les deux, et
**propose le retour à « Tout le tournoi »**. Symétriquement, un vide **réel** (aucun inscrit classé)
ne doit pas être imputé au filtre : le message ne nomme pas de cause unique quand plusieurs filtres
peuvent être en jeu (créneau, catégorie, interrupteur).

## Conséquences

**Positives.** La règle de centrage a un **domicile unique** (`shared/suivis/focus.ts`), testé en
logique pure : cinq vues qui auraient chacune écrit son filtre auraient dérivé. Le filtrage **ne
renumérote pas** — un 23ᵉ reste 23ᵉ —, comme le filtre par catégorie d'E06US001.

**Négatives, assumées.** (a) La combinaison par vue est perdue (§1). (b) Le prop-drilling du couple
`mode` / `suivis` traverse cinq signatures ; l'état illégal `mode="suivis"` avec `suivis=[]` reste
représentable, garanti seulement à la source. Une prop unique `centrerSur: number[] | null` le
rendrait inexprimable — **écarté pour l'instant** (règle 16 : aucune divergence constatée, aucun
bug ; à rouvrir au 6ᵉ écran, où la répétition ferait preuve). (c) Centré, le classement n'a plus de
tête figée : encadrer huit lignes dans une liste de trois n'encadre plus rien.

**Ce qu'il faut surveiller.** Le module vit dans `shared/` et non dans `features/public/`
précisément parce que des features servant l'admin et la salle en dépendent ; l'y ramener
réinstallerait au niveau du module le couplage que le §2 évite à l'exécution.

## Porté dans le code par

| Module | Ce qu'il applique |
|---|---|
| `frontend/src/shared/suivis/focus.ts` | §1 (domicile unique), §3 (`centrerCibles` garde la cible entière), §4 (`modeEffectif`), filtrage sans renumérotation |
| `frontend/src/shared/stores/sessionSuivisStore.ts` | §5 (`centrerSurSuivis` armé par défaut, persisté) |
| `frontend/src/features/public/AccueilPublic.tsx` | §1 (`BasculeAffichage`, masquée sur l'onglet « Suivi »), §2 (descente en props des cinq vues) |
| `frontend/src/features/palmares/VuePalmares.tsx` | §3 (podiums jamais centrés), §6 |
| `frontend/src/features/competition/VueClassement.tsx` | §3 (barrages/départage sur liste entière), §6 ; ex æquo calculés sur la liste **complète** |
| `frontend/src/features/routage/VueAffectations.tsx` | §3 (buttes entières, adversaire compris), §6 |
| `frontend/src/features/tableaux/VueTableaux.tsx` | §2 (`suivis` en prop, plus de lecture du store), §6 |
| `frontend/src/features/placement/PlanCiblesPublic.tsx` | §3, §6 |

**Tests qui le verrouillent** : `shared/suivis/focus.test.ts` (§1, §3, §4),
`shared/stores/sessionSuivisStore.test.ts` (§5 — `getInitialState`, le garde de dernier recours),
`features/public/AccueilPublic.test.tsx` (§1, §2, §5 de bout en bout),
`features/palmares/VuePalmares.test.tsx` (§3 podiums, §6),
`features/routage/presentation.test.ts` (§3 buttes entières, `posesParCible`),
`features/suivi/suivi.test.ts` (`departsDesArchersSuivis` — les créneaux de l'archer, pas ceux de la
salle), `features/tableaux/VueTableaux.test.tsx` (§2, §6),
`features/competition/TableClassement.test.tsx` (ex æquo calculés sur la liste complète **mais
annoncés seulement si une ligne visible les porte**).

⚠️ **Angle mort assumé** : `features/suivi/VueSuivi.tsx` n'a aucun test de **montage**, alors que
c'est le composant le plus modifié par E16US004 et l'onglet d'atterrissage. Sa logique extraite est
testée (`suivi.test.ts`, `tableaux/presentation.test.ts`), son rendu ne l'est pas — relevé en 2ᵉ
passe de revue, laissé en l'état plutôt que traité à la hâte en fin d'US.
