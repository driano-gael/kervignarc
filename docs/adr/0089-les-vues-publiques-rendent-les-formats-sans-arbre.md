# ADR-0089 — Les vues publiques rendent les formats sans arbre

- **Statut** : accepté
- **Date** : 17/08/2026
- **US** : E05US031 — « Le public voit les formats sans arbre »
- **Révise** : [ADR-0064](0064-ecran-de-salle-poste-type-et-pilotage-par-etat-lu.md) (catalogue de vues de
  l'écran de salle)
- **Liés** : [ADR-0083](0083-le-contrat-de-phase-jouable.md) (contrat de phase jouable, décors),
  [ADR-0079](0079-un-seul-interrupteur-mes-archers-pour-tout-l-onglet-public.md) (interrupteur
  unique « mes archers »), [ADR-0075](0075-le-depart-est-la-portee-sportive.md) (le créneau est la
  portée), [ADR-0081](0081-une-phase-attend-que-sa-source-ait-departage-les-places-qu-elle-preleve.md)
  (phase en attente de sa source), [ADR-0076](0076-un-deroule-defini-une-fois-un-avancement-par-depart.md)
  (l'avancement est porté par le créneau)

## Contexte

Trois formats sans arbre sont jouables de bout en bout — les **poules** (`E05US023`), le **Big Shoot
Off** (`E05US028`) et le **système suisse** (`E05US026`/`E05US030`). Aucun des trois n'atteint
l'application publique ni l'écran de salle : l'onglet « Tableaux » est bâti sur
`GET /api/v1/tableaux/departs/{depart_id}`, qui ne rend qu'un **arbre de duels** (`TableauPublic` :
`duels`, `nb_tours`, `plage`, `podium`). Dès que le tournoi quitte l'élimination directe, le
spectateur n'a plus rien — y compris sur les archers qu'il a explicitement choisi de suivre.

Trois éléments de terrain cadrent la décision :

1. **Le manque est commun aux trois formats, pas propre au suisse.** La demande initiale du cadrage
   d'`E05US030` était « une vue publique du suisse » ; la livrer seule aurait figé une **troisième**
   variante locale au lieu de combler le trou. C'est le motif du découpage en `E05US031`.
2. **Les données publiques existent déjà pour deux formats sur trois.**
   `GET /poules/etat/{tournoi}/{phase}` et `GET /suisse/etat/{tournoi}/{phase}` sont **publiques et
   anonymes**, et portent déjà les rencontres rédigées, les couloirs et le classement. Le Big Shoot
   Off est le seul muet : son unique lecture (`/big-shoot-off/etat`) est derrière `exiger_scoreur`,
   et sa projection derrière `exiger_admin`.
3. **ADR-0064 pose une règle que cette US doit honorer** : *« on n'inscrit une vue qu'une fois son
   écran capable de l'afficher, sinon le réglage programme une page vide — et un écran de salle n'a
   personne devant lui pour comprendre ce qui manque »*.

Le périmètre a été **élargi au cadrage du 17/08/2026** par le commanditaire, au-delà du CA écrit :
l'historique des tours déjà joués, « mon chemin » pour un archer suivi, et la persistance du
classement d'une phase terminée. Ces trois ajouts sont reversés dans `stories/E05-moteur-phases.md`.

## Décision

### 1. Une **forme commune** « rencontres groupées + classement », pas une vue par type

Poules et système suisse partagent le décor `RONDES_APPARIEES` du contrat de phase (ADR-0083 §1), et
la même grammaire de lecture : *des rencontres appariées, groupées par tour ou par ronde, et un
classement qui dit où en est chacun*. Ils sont rendus par **un seul** composant, alimenté par un
**modèle neutre** (`shared/rencontres/`) auquel chaque format s'adapte.

Ce n'est pas une économie de lignes, c'est la seule forme qui tienne sur la durée : la **colline**
partage le même décor et arrive en `E05US027`. Écrire trois vues cousines aujourd'hui, c'est en
écrire une quatrième demain et garantir qu'elles divergeront sur la seule chose qui compte —
l'appariement affiché. C'est mot pour mot le raisonnement d'ADR-0064 §6 sur le schéma à braquets.

**Le Big Shoot Off garde sa vue propre, et ce n'est pas une exception de confort** : une manche y est
un **tir collectif sans adversaire** — pas de rencontre, pas d'appariement, pas de vainqueur de
rencontre. Le plier dans le modèle neutre demanderait d'y inventer des champs vides ; c'est
exactement ce qu'ADR-0064 §2 rejette (*« quand une valeur doit signifier deux choses selon le
contexte, elle finit par mentir dans l'un des deux »*).

⚠️ **La frontière est le décor, pas le nombre de formats.** Un format entre dans la forme commune
s'il apparie des rencontres ; sinon il a sa vue. Cette phrase est le critère à appliquer au format
suivant, et elle évite le débat « faut-il forcer ? » à chaque US de moteur.

### 2. Le modèle neutre est **du code testé**, pas du JSX

`shared/rencontres/modele.ts` porte les types (`BlocRencontres`, `RencontrePublique`,
`LigneClassement`) et les opérations pures — dont `cheminDe(archerId)`, qui extrait la trajectoire
d'un archer suivi. L'adaptation d'un DTO de format vers ce modèle vit **dans la feature du format**,
qui est propriétaire de son DTO ; le rendu vit dans `shared/`.

Ce partage n'est pas décoratif : il évite l'inversion `shared/ → features/`, la seule que le front
n'ait jamais tolérée (cf. l'en-tête de `shared/phases/catalogue.ts`, corrigé en revue pour cette
raison exacte). Et il applique l'enseignement le plus cher d'ADR-0064 §2 : *une garantie annoncée
dans un ADR n'existe que si un chemin de code la produit — et qu'un test l'exerce*. La logique de
« mon chemin » de l'arbre a dû être extraite du JSX après coup ; celle-ci naît dehors.

### 3. Le catalogue de vues **garde sa clé `tableaux`**, son libellé s'élargit

`VueEcran.TABLEAUX = "tableaux"` est une valeur **persistée** sur les postes-écrans (ADR-0064 §3 :
le déroulé de vues est un réglage de préparation, en base). La renommer imposerait une migration
pour changer un mot, et casserait tout déroulé déjà composé.

La clé reste donc `tableaux` ; c'est le **libellé affiché** qui devient « Rencontres », dans la
console de pilotage comme dans l'onglet public. La vue ne montre plus « les arbres » mais « la phase
qui se joue, quelle que soit sa forme ».

⚠️ **Conséquence assumée** : la clé technique et le libellé métier divergent. C'est un écart à la
règle 3 (cohérence code ↔ API ↔ UI ↔ doc), consenti ici parce que l'alternative — une migration de
données pour un renommage cosmétique — coûte plus cher que le désaccord. Inscrit au registre de
dette (**DETTE-070**) plutôt que tu : c'est le genre d'écart qui, non écrit, se redécouvre en
cherchant pourquoi un `grep tableaux` ne trouve rien.

**La règle d'ADR-0064 est honorée** : aucune vue n'est ajoutée au catalogue, on rend capable celle
qui existe. Le réglage ne peut donc programmer aucune page vide.

### 4. L'index des phases publiques est la **liste d'avancement du créneau**

La vue publique s'alimente à `GET /api/v1/departs/{depart_id}/phases` — déjà publique, déjà
ordonnée, déjà porteuse du `type` et du `statut` de chaque phase — et **non** à une extension de
`/tableaux/departs/{id}`.

Le motif est structurel : un arbre est un **cas particulier** de phase, pas le sommaire du créneau.
Faire du routeur des tableaux l'index de tous les formats l'aurait obligé à connaître poules, suisse
et Big Shoot Off — une frontière API qui grossit à chaque format livré, alors que la liste des
phases est déjà l'endroit dont c'est le métier (ADR-0076 : l'avancement est porté par le créneau).

Le sélecteur liste donc **toutes** les phases du créneau, terminées comprises — c'est ce qui rend le
classement d'une poule close consultable après le démarrage de la phase suivante, sans une ligne de
backend.

### 5. Le Big Shoot Off gagne sa lecture publique, et ses routes s'alignent sur ses jumeaux

Poules et suisse exposent chacun deux surfaces nommées de la même façon : `/etat` **publique et
restreinte**, `/saisie` **scoreur et complète**. Le Big Shoot Off, livré avant que ce partage ne soit
un motif, appelle `/etat` sa lecture **scoreur**.

Les deux routes sont donc alignées : `/big-shoot-off/etat/{tournoi}/{phase}` devient **publique**, et
la lecture du scoreur passe à `/big-shoot-off/saisie/{tournoi}/{phase}`. Le front et le serveur sont
livrés ensemble (SPA servie par le backend), il n'y a pas de client tiers à ménager.

**Ce que le DTO public retire** (règle 6 — le DTO public n'est pas l'objet interne appauvri par
politesse, c'est un contrat distinct) : `prochaine_volee`, qui est une **affordance de saisie** et
n'a aucun sens pour un lecteur ; le détail de numérotation des volées d'une manche ; et les champs
d'atelier de la projection (`volees`, `fleches_par_volee`, `manches_ignorees`), qui sont du réglage.

Il **conserve** les scores par manche : ils ne portent que les manches **entièrement validées**
(invariant déjà tenu par `TireurAffiche.scores`), donc rien qui ne soit acquis. C'est le pendant
exact des points d'un duel sur la route publique des tableaux.

### 6. L'interrupteur « mes archers » vaut ici **sans exception**

ADR-0079 pose un interrupteur unique en tête de l'onglet public, jamais un par vue. Les vues de
format le reçoivent en prop, comme les cinq autres — elles ne lisent jamais le store, parce
qu'elles servent aussi l'écran de salle, où il n'y a personne à suivre (correctif de revue
d'E16US004, à ne pas refaire).

Chaque vue **nomme son propre vide** distinctement : « aucun de vos archers ici » n'est pas « rien à
afficher ». Un spectateur qui suit des archers d'une catégorie en regardant la poule d'une autre est
le cas banal, pas le cas limite.

## Conséquences

**Positives**

- Les trois formats atteignent l'application publique et l'écran de salle **d'un seul geste**, et la
  colline (`E05US027`) héritera de la forme commune sans écrire de vue.
- Le classement d'une phase terminée reste consultable, sans backend : c'est une conséquence du §4.
- L'alignement des routes du Big Shoot Off retire un piège réel — trois formats jumeaux, deux
  conventions de nommage, dont une qui plaçait une lecture scoreur derrière le nom de la lecture
  publique.

**Négatives / à surveiller**

- **La clé `tableaux` ne dit plus ce que la vue montre** (§3, `DETTE-070`).
- **Le modèle neutre est un pari sur la forme**, pas sur les données : si un format à venir apparie
  des rencontres *et* porte une structure que le modèle ignore (un enchaînement de groupes, par
  exemple), il faudra l'élargir plutôt que le contourner par une vue de plus. Le critère du §1 est là
  pour rendre ce choix explicite.
- **`GET /departs/{id}/phases` expose les réglages complets** (`sources`, `poules`, `suisse`,
  `big_shoot_off`) sur une route anonyme. Ce n'est **pas** introduit ici — la route est publique
  depuis sa création — mais cette US en fait un consommateur de plus, donc un motif de moins pour la
  restreindre un jour. Signalé sans être corrigé : la restreindre casserait les écrans qui en
  dépendent déjà, ce qui est une US, pas un correctif de bord.
- L'onglet public passe de six à six vues (aucune n'est ajoutée), mais son sélecteur de phase liste
  désormais **toutes** les phases du créneau, échauffement compris. Les types sans vue détaillée
  affichent une ligne honnête plutôt qu'un écran vide.

## Alternatives écartées

- **Une vue par type de phase** (trois composants indépendants). Plus direct à écrire, mais trois
  variantes à maintenir et une quatrième à écrire pour la colline — et la certitude qu'elles
  divergeront sur l'appariement affiché. Écartée par le commanditaire au cadrage du 17/08/2026.
- **Étendre `TableauPublic` à un « tableau » générique.** Aurait demandé de faire entrer une poule
  dans une structure d'arbre (`nb_tours`, `plage`, `podium`), donc d'y laisser des champs vides
  porteurs de sens implicite — le défaut nommé au §1.
- **Une nouvelle vue au catalogue de l'écran de salle** (`poules`, `suisse`, `big_shoot_off`).
  Aurait multiplié les entrées d'un réglage que l'organisateur compose à la main, et exigé de lui
  qu'il sache **à l'avance** quels formats son tournoi jouera pour programmer son écran. La vue
  « Rencontres » suit le créneau toute seule.
- **Une route publique unique « état de phase, tous formats ».** Séduisante, mais elle aurait fait
  d'un routeur le point de passage de tous les moteurs — l'inverse du sens des dépendances (règle 2),
  et un fichier qui grossit à chaque format.

## Porté dans le code par

| Décision | Module chargé de l'appliquer |
|---|---|
| §1 — forme commune, critère du décor | `frontend/src/shared/rencontres/modele.ts` (les types neutres, `TourVue`) · `frontend/src/shared/rencontres/VueRencontres.tsx` (le rendu unique) |
| §1 — adaptation par format | `frontend/src/features/poules/publique.ts` (`formatPublicDesPoules`) · `frontend/src/features/suisse/publique.ts` (`formatPublicDuSuisse`, `enDemiPoints`) |
| §1 — vue propre au Big Shoot Off | `frontend/src/features/big-shoot-off/VueBigShootOffPublique.tsx` · `frontend/src/features/big-shoot-off/publique.ts` (`lignesTireurs`) |
| §2 — « mon chemin » testé hors JSX | `frontend/src/shared/rencontres/modele.ts` (`cheminDe`, `rangDe`, `engagesParmi`), couvert par `frontend/src/shared/rencontres/modele.test.ts` |
| §3 — clé conservée, libellé élargi | `frontend/src/features/ecrans/api.ts` (`LIBELLE_VUE`) · `backend/domain/ecran.py` (`VueEcran`, **inchangé — c'est la décision**) |
| §4 — index par la liste d'avancement | `frontend/src/features/phases-publiques/api.ts` (`PhasePublique`, `getPhasesPubliques`) · `frontend/src/features/phases-publiques/presentation.ts` (`renduDe`, `phaseAMontrer`) · `backend/api/v1/phases.py` (`lister_avancement`, la route consommée) |
| §5 — deux surfaces, deux droits | `backend/api/v1/big_shoot_off.py` (`lire_etat` public / `lire_pour_saisie` scoreur, `EtatPubliqueReponse`) |
| §6 — interrupteur en prop, vide nommé | `frontend/src/features/phases-publiques/VuePhases.tsx` (props `mode`/`suivis`, jamais le store) · `frontend/src/shared/rencontres/VueRencontres.tsx` (`MesArchers`) |
