# Registre de la dette

> Registre **obligatoire** de la dette **assumée** du projet : ce qu'on sait imparfait, qu'on a
> choisi de ne pas corriger tout de suite, et qu'on s'engage à résorber.
> Règle : une dette introduite ou aggravée par une US doit être **inscrite ici dans le même commit**
> que son introduction. Une dette non inscrite est une dette **silencieuse** — elle est remontée en
> **majeur** à la revue de PR (cf. [`../.claude/commands/revue-us.md`](../.claude/commands/revue-us.md), règles 14-15).
>
> Ce registre n'est **pas** une liste de tâches : il n'accueille que la dette **acceptée en connaissance
> de cause**. Un bug qu'on peut corriger dans l'US se corrige dans l'US ; il n'atterrit pas ici.

## Deux natures de dette

- **Dette technique** — un raccourci d'implémentation assumé : `TODO`/`FIXME`, `type: ignore`,
  `eslint-disable`, test désactivé ou affaibli, cas d'erreur non traité, contrainte/index absents,
  migration divergente du modèle, valeur en dur qui devrait être paramétrée.
  Le code marche (ou échoue de façon connue), mais l'implémentation est en deçà des règles du projet.
- **Dette de conception** — une structure qui tiendra mal : responsabilité placée dans la mauvaise
  couche, abstraction prématurée ou manquante, couplage entre features, duplication structurelle,
  modèle qui s'éloigne du [glossaire](glossaire.md) ou du [modèle de données](modele-de-donnees.md),
  invariant métier vérifié hors du domaine.
  Le code marche aujourd'hui ; c'est le **changement suivant** qui coûtera cher.

## Sévérités

| Sévérité | Sens | Conséquence |
|---|---|---|
| **bloquant** | casse un cas utilisateur réel **dès maintenant** | n'entre pas ici : se corrige avant merge |
| **majeur** | dégrade un invariant du projet ou piège le prochain contributeur | US de résorption **planifiée** |
| **mineur** | inconfort local, contournable | résorbée à l'occasion d'une US qui touche la zone |

## Dette ouverte

| ID | Nature | Sévérité | Portée | Description | Impact | Introduite par | Résorption |
|---|---|---|---|---|---|---|---|
| [DETTE-001](#dette-001--suppression-de-tournoi-non-cascadée) | technique | majeur | `backend/infrastructure/db/models.py`, `backend/migrations/versions/` | Aucune FK de la descendance de `tournoi` n'a d'`ON DELETE CASCADE`, ni de suppression applicative équivalente : enfants directs `categorie`, `archer`, `blason`, `gabarit_salle`, `phase` (→ `tournoi.id`), enfant indirect `score` (→ `archer.id`) et liens latéraux `categorie.blason_id` (→ `blason.id`) et `archer.categorie_id` (→ `categorie.id`) | Supprimer un tournoi non vide lève une `IntegrityError` → **500** au lieu d'un 409 ou d'une cascade maîtrisée | E01US002 (cycle de vie du tournoi) ; aggravée à chaque nouvelle table/FK de la descendance (E01US004, E01US005, E01US006, E01US008, E01US009, E02US002) | US dédiée — non planifiée |
| [DETTE-002](#dette-002--hauteur-de-blason-non-modélisée) | conception | majeur | `backend/domain/blason.py`, `docs/modele-de-donnees.md` | `Blason` modélise l'occupation d'une cible par une `taille` (fraction) + `capacite`, mais **pas la hauteur du centre** — 110 cm pour le blason 80 cm des U11 contre 130 cm pour tous les autres (FFTA B.2.2.1.1, C.3.1.1) | Le placement automatique (EPIC-03) pourra composer une butte physiquement intirable : un U11 et des adultes sur la même cible passent le contrôle « somme des fractions ≤ capacité » alors que leurs blasons ne peuvent pas coexister | E01US005 (blasons) ; constatée au cadrage FFTA du 14/07/2026 | E03US001 (placement automatique) — **avant** d'écrire l'algorithme |
| [DETTE-003](#dette-003--config-de-phase-à-plat-au-lieu-de-configpolicies) | conception | majeur | `backend/infrastructure/db/repositories.py` (`_config_phase`, `_vers_phase`), `docs/modele-de-donnees.md` | La `config` d'une phase écrit ses politiques **à plat à la racine** (`config.scoring`, `config.validation`) alors que le modèle cible (ADR-0004) les range sous `config.policies` ; et `scoring` y est un **objet paramétré** au lieu d'un **nom de preset** | Deux conventions coexistent pour le même champ. Le moteur (EPIC-05) devra soit adopter la forme à plat — et renoncer au modèle cible — soit migrer les `config` déjà écrites : c'est une décision reportée, pas évitée | E01US009 (forme posée) ; suivie par E01US015 (`config.validation`), qui s'y aligne plutôt que d'introduire une 2ᵉ convention | E05US004 (assembler les politiques) — **avant** d'écrire le moteur |
| [DETTE-005](#dette-005--conversion-euroscentimes-sans-aucun-test) | technique | majeur | `frontend/src/features/competition/format.ts` | La conversion **euros ↔ centimes** — seul convertisseur d'argent de l'application ([ADR-0012](adr/0012-argent-en-centimes-entiers.md)) — n'a **aucun test** : le front n'a pas de runner (`package.json` : ni `vitest`, ni script `test`) | Une régression silencieuse fausse **le montant dû** (EF-8.1) : inverser `padEnd`/`padStart` transforme 8,10 € en 8,01 € sans que rien ne bronche. Le code est juste aujourd'hui ; c'est sa **non-régression** qui n'est protégée par rien | E01US010 (1ʳᵉ logique pure du front) ; absence de runner préexistante (E00US002 n'outille que lint/format) | E00US014 (runner de test front) — **avant** E08US001, qui consommera le tarif |
| [DETTE-004](#dette-004--messageerreur-dupliqué-dans-chaque-feature-front) | conception | mineur | `frontend/src/features/*/` (9 occurrences) | Le composant `MessageErreur` est copié **à l'identique** dans chaque feature — même signature, même corps, mêmes classes — au lieu de vivre dans `shared/` | Tout changement du rendu d'erreur (ex. le token d'alerte **ambre** du CDC design, `DV-03`) se fait en 9 endroits, avec le risque d'en oublier un : les erreurs sont précisément ce que l'utilisateur voit quand ça va mal | E00US011 puis chaque feature (`admin`, `bareme`, `blasons`, `categories`, `competition`, `gabarits` ×2) ; **aggravée** par E01US015 (8ᵉ copie) puis E02US001 (9ᵉ copie) | E00US013 (factoriser les briques d'UI partagées) |

## Dette résorbée

_(aucune à ce jour)_

## Détail

### DETTE-001 — suppression de tournoi non cascadée

**Constat.** Aucune FK de la descendance de `tournoi` ne porte de politique de suppression, ni côté
modèle (`ForeignKey(...)` sans `ondelete`) ni côté migrations
(`sa.ForeignKeyConstraint([...], [...])`), et le service de suppression ne purge pas les enfants.
La descendance compte trois natures de liens :

- **enfants directs** de `tournoi` — `categorie`, `archer`, `blason` (FK → `tournoi.id`),
  `gabarit_salle` pour son **instance** appliquée à un tournoi (E01US008 ; les modèles de
  bibliothèque, `tournoi_id NULL`, ne sont pas concernés) et `phase` (E01US009) ;
- **enfant indirect** — `score` (FK → `archer.id`), donc bloquant pour la suppression d'un `archer`,
  elle-même requise par toute cascade partant du tournoi ;
- **liens latéraux** entre deux enfants du tournoi — `categorie.blason_id` (FK → `blason.id`,
  E01US006) et `archer.categorie_id` (FK → `categorie.id`, E02US002) : dans une cascade, ils
  imposent un **ordre** — dénouer/supprimer la `categorie` avant son `blason`, et l'`archer` avant
  sa `categorie`.

Une résorption qui ne traiterait que les FK vers `tournoi.id` laisserait `score` **et** les liens
latéraux bloquer la cascade.

> **E02US002 élargit cette ligne plutôt que de contourner localement.** `archer.categorie_id` est
> `NOT NULL` : contrairement à `categorie.blason_id` (nullable, qu'on peut dénouer), une cascade ne
> pourra pas le mettre à `NULL` — elle devra supprimer l'archer, donc ses `score` d'abord. La chaîne
> à respecter est désormais `score → archer → categorie → blason`. À noter : `archer.club_id`
> **n'entre pas** dans cette dette (il pointe vers `club`, hors descendance du tournoi — cf.
> [ADR-0014](adr/0014-club-inconnu-plutot-que-club-sentinelle.md)).

**Conséquence.** La suppression d'un tournoi ne réussit que s'il est vide. Dès qu'une catégorie, un
archer, un score ou un blason y est rattaché, la contrainte FK échoue et l'erreur remonte non
traitée jusqu'à la frontière API — donc un **500**, alors que la règle 5 impose une erreur typée et
un code métier explicite.

**Pourquoi c'est en dette et pas corrigé.** Le choix entre les deux comportements est **fonctionnel**,
pas technique, et n'est pas tranché :
- **cascade** — supprimer le tournoi supprime tout son contenu (simple, mais destructeur et irréversible) ;
- **refus** — 409 tant que le tournoi n'est pas vide (sûr, mais impose une purge manuelle).

Trancher demande une décision produit ; la trancher au fil d'une US de catégorie ou de blason
reviendrait à la trancher par accident.

**Aggravation.** Chaque US qui ajoute une table **ou une FK** à la descendance de `tournoi` élargit
la dette sans la créer. Une telle US doit :
1. ajouter sa ligne au périmètre de DETTE-001 (colonne « Introduite par ») ;
2. poser le marqueur `# DETTE-001` sur la FK concernée ;
3. ne pas inventer de contournement local (pas de purge ad hoc dans un service).

E01US006 ajoute la FK latérale `categorie.blason_id`. À noter : la suppression d'un **blason isolé**
encore référencé par une catégorie **n'est pas** de la dette — elle est **tranchée** et traitée par
le service (`BlasonReference` → 409). Seule reste ouverte la suppression du **tournoi** englobant,
qui relève de cette même politique non arbitrée.

**Résorption attendue.** Une US dédiée qui (a) tranche le comportement, (b) l'applique de façon
homogène à **toute la descendance** — `score` et le lien `categorie → blason` compris — via une
migration, (c) mappe l'erreur en `DomainError` → 409 si le refus est retenu, (d) couvre les deux
cas (tournoi vide / non vide) en test d'intégration. Décision structurante ⇒ **ADR**.

### DETTE-002 — hauteur de blason non modélisée

**Constat.** `Blason` décrit l'occupation d'une cible par deux grandeurs — `taille` (fraction de
place, `]0,1]`) et `capacite` (`≥ 1`) — et le placement en dérivera la règle « somme des fractions
d'une cible ≤ capacité ». Le [référentiel FFTA](referentiel-ffta.md) §5 ajoute une grandeur
absente du modèle : la **hauteur du centre de l'or**, mesurée du sol. Elle vaut **130 cm** pour un
blason unique ou un triple vertical (art. B.2.2.1.1), **100 à 162 cm** pour une butte à 4 blasons
(B.2.2.1.2) — et surtout **110 cm** pour le blason 80 cm des U11 (art. C.3.1.1).

**Conséquence.** Deux blasons ne peuvent pas cohabiter sur une même butte si leurs hauteurs de
centre diffèrent : le carton n'a qu'une position. Un **U11** (centre à 110 cm) ne peut donc pas
partager une cible avec des archers tirant à 130 cm, **quelle que soit la place restante**. La
règle « somme des fractions ≤ capacité » laisse pourtant passer cette combinaison : la hauteur
n'est pas réductible à une fraction, et aucune donnée du modèle ne permet de la déduire. Le
placement automatique (EPIC-03) produira donc des plans de cibles **physiquement intirables**, sans
que rien ne le signale.

**Pourquoi c'est en dette et pas corrigé.** Ajouter un champ `hauteur` au blason est trivial ; le
concevoir correctement ne l'est pas. La hauteur n'est pas une propriété isolée : elle appelle une
règle de **compatibilité entre blasons d'une même butte**, dont la forme (valeur unique ? plage
haute/basse pour les buttes à 4 blasons ? contrainte dérivée de la catégorie plutôt que du blason ?)
relève de la conception du **moteur de placement**, pas du CRUD de blasons. Trancher maintenant, au
fil d'une US de configuration, reviendrait à figer l'abstraction du placement avant de l'avoir
écrite — le reproche exact que l'on fait déjà au modèle actuel.

**Résorption attendue.** L'US de placement automatique (E03US001) doit, **avant** d'écrire
l'algorithme : (a) choisir où vit la hauteur (blason ? catégorie ? les deux ?), (b) l'ajouter au
modèle et à la migration, (c) exprimer la compatibilité comme une **contrainte de placement à part
entière**, au même rang que la capacité et la mixité club, (d) couvrir en test le cas « U11 +
adultes sur une même butte → refusé ». Documenté au CDC fonctionnel en **EF-4.4b**.

### DETTE-003 — config de phase à plat au lieu de `config.policies`

**Constat.** Le [modèle de données](modele-de-donnees.md) décrit la `config` cible d'une phase
(ADR-0004) comme un objet où **toute politique vit sous `policies`**, désignée par un **nom de
preset** :

```json
{ "policies": { "routing": "cascade", "scoring": "sets_4pts", "validation": { "grain": "fin_de_duel" } } }
```

L'implémentation écrit autre chose — les politiques **à la racine**, et `scoring` en **objet
paramétré** :

```json
{ "scoring": { "volees": 20, "fleches": 3, "mode": "cumul" }, "validation": { "grain": "fin_de_serie" } }
```

Les deux écarts ont chacun leur raison. La **racine** : E01US009 n'avait qu'une politique à loger,
et l'ADR-0011 borne son périmètre à « une phase `qualification`, `config.scoring` » — introduire le
niveau `policies` pour une clé unique aurait été une abstraction sans emploi. L'**objet** plutôt que
le nom de preset : un barème de qualification se **paramètre** (nb de volées × nb de flèches, CA
d'E01US009 : « valeurs modifiables »), il ne se choisit pas dans un catalogue fermé — le nom de
preset suppose des barèmes de duel énumérables (`sets_4pts`), ce que la qualification n'est pas.

**Conséquence.** Deux conventions coexistent pour le même champ, et rien dans le code ne dit
laquelle fait foi. Le moteur (EPIC-05) devra trancher : adopter la forme à plat — et corriger le
modèle cible, donc l'ADR-0004 — ou rétablir `policies` et **migrer** les `config` déjà écrites par
E01US009/E01US015. Plus des tournois réels porteront une `config`, plus le second chemin coûtera.
Le risque immédiat est faible (un seul type de phase, deux clés), mais l'ambiguïté est réelle :
E01US011 (presets multi-phases) et E01US015 se sont déjà posé la question.

**Pourquoi c'est en dette et pas corrigé.** La trancher demande de savoir **ce que le moteur
attend** : `policies` n'a de sens que face à plusieurs politiques hétérogènes et à leur résolution
par le couple (phase, arme) — EF-3.4, `scoring_par_arme` — qui n'est pas écrite. Choisir maintenant,
au fil d'une US de configuration, figerait la forme de `config` **avant** d'avoir le seul code qui
la consomme. C'est le reproche exact que l'on ferait à l'inverse. E01US015 s'aligne donc sur la
forme effective plutôt que d'ajouter une 2ᵉ convention dans la même `config` — un troisième état
serait pire que les deux actuels.

**Résorption attendue.** E05US004 (assembler les politiques d'une phase) doit, **avant** d'écrire le
moteur : (a) trancher racine vs `policies`, et preset nommé vs objet paramétré — les deux questions
sont liées mais distinctes ; (b) mettre `docs/modele-de-donnees.md` et l'ADR-0004 en accord avec la
décision (l'un des deux a tort, il faut dire lequel) ; (c) si `policies` est retenu, fournir la
migration des `config` existantes et couvrir en test la relecture d'une `config` de l'ancienne
forme — le même patron que le « zéro migration » d'E01US015 (`_vers_phase`) ; (d) décision
structurante ⇒ **ADR** (qui amendera ou remplacera l'ADR-0011).

### DETTE-004 — `MessageErreur` dupliqué dans chaque feature front

**Constat.** Neuf features déclarent chacune leur `MessageErreur`, copie conforme :

```tsx
function MessageErreur({ erreur }: { erreur: Error | null }) {
  if (erreur === null) return null
  const message = erreur instanceof ErreurApi ? erreur.message : 'Une erreur est survenue.'
  return <p className="carte__etat carte__etat--erreur" role="alert">{message}</p>
}
```

Occurrences : `admin/ConnexionAdmin.tsx`, `bareme/BaremeQualification.tsx`, `blasons/Blasons.tsx`,
`categories/Categories.tsx`, `clubs/Clubs.tsx`, `competition/TrancheVerticale.tsx`,
`gabarits/Gabarits.tsx`, `gabarits/PlanDeSalle.tsx`, `grain-validation/GrainValidation.tsx`. Même
signature, même corps, mêmes classes CSS, même `role="alert"`.

**Conséquence.** Le rendu des erreurs n'a pas de point unique. Le CDC design impose que l'**alerte
soit ambre** et que les couleurs sémantiques appartiennent au produit (`DV-03`) : appliquer ce token
demandera neuf modifications identiques, et il suffit d'en manquer une pour qu'un écran mente sur la
gravité de ce qu'il affiche. Or l'erreur est exactement ce que l'utilisateur regarde quand la
journée déraille.

> **E02US002 n'ajoute pas de 10ᵉ copie, mais ouvre un rendu d'erreur *hors* `MessageErreur`** :
> le bloc de confirmation d'homonyme de `competition/TrancheVerticale.tsx` (`role="alert"`, avec un
> bouton « Inscrire quand même ») est **actionnable** et volontairement **neutre** — un doublon
> probable n'est pas une erreur, l'inscription reste possible —, d'où l'absence du modificateur
> `--erreur`. **E00US013 ne le trouvera pas** en cherchant `MessageErreur` : il n'est pas une copie.
> À traiter avec la même résorption (soit un `MessageErreur` acceptant des enfants, soit un
> composant frère assumé), sans quoi le token ambre s'appliquera à neuf endroits sur dix.

**Rythme d'aggravation.** Une copie par feature créée : c'est mécanique, et E02US001 le confirme
(9ᵉ). Chaque US de configuration qui ouvre un écran en ajoutera une tant qu'E00US013 n'est pas
faite — E02US002 (archers) est la suivante sur la trajectoire. Le coût de la résorption croît donc
à chaque US, pendant que celui de la copie reste nul sur le moment : c'est exactement le profil
d'une dette qu'on ne « trouve » jamais le temps de rembourser.

**Pourquoi c'est en dette et pas corrigé.** La duplication est **préexistante** : E01US015 en hérite
et en ajoute la 8ᵉ copie, mais ne la crée pas. La résorber ici toucherait sept features étrangères à
l'US — dont la saisie et la connexion admin — sans test front pour rattraper une régression (le
projet n'en a aucun). Le périmètre d'une US de configuration n'est pas le bon véhicule ; le faire
« au passage » diluerait la revue de l'US dans un refactor transverse.

**Résorption attendue.** E00US013 : extraire `MessageErreur` dans `frontend/src/shared/ui/`, le
faire consommer par les 9 features, et supprimer les copies. Cheap et mécanique (~10 lignes ajoutées
contre 8 suppressions), mais à faire **d'un bloc** pour que la revue porte sur l'équivalence du
rendu. À enchaîner de préférence **avant** E01US016 (identité visuelle) et le thème sombre, qui
consommeront les tokens de couleur.

### DETTE-005 — conversion euros/centimes sans aucun test

**Constat.** [ADR-0012](adr/0012-argent-en-centimes-entiers.md) pose que l'argent se compte en
**centimes entiers** et que les euros n'existent qu'à l'affichage. La conversion vit donc en **un
seul** endroit, `frontend/src/features/competition/format.ts` — et cet endroit n'a **aucun test**.
Le front n'a pas de runner du tout : `frontend/package.json` ne déclare ni `vitest`, ni
`testing-library`, ni script `test` ; les scripts s'arrêtent à `dev`, `build`, `typecheck`, `lint`,
`format`.

**Conséquence.** Jusqu'ici, l'absence de tests front était sans grande portée : le front n'hébergeait
que du rendu, et `tsc` + ESLint suffisaient à en attraper l'essentiel. E01US010 y met pour la
première fois de la **logique pure et arithmétique**, à cas limites non évidents :

- `saisieEurosVersCentimes("8,1")` doit rendre **810**, pas 801 (`padEnd`, pas `padStart`) ;
- `centimesVersSaisieEuros(5)` doit rendre **« 0,05 »**, pas « 0,5 » (`padStart` ici, l'inverse) ;
- l'aller-retour doit être stable sur `0`, sinon éditer un tournoi gratuit l'efface.

Ces trois lignes décident de **ce que paiera un archer** (EF-8.1). Une « simplification » d'un
`padEnd` en `padStart` passerait `tsc`, ESLint et la revue, et transformerait 8,10 € en 8,01 € sur
toutes les listes de club — sans qu'aucun signal ne se déclenche.

**Pourquoi c'est en dette et pas corrigé.** Le correctif n'est pas « écrire un test » : c'est
**outiller le front pour qu'il puisse en avoir un** — devDependency, script, câblage CI. Trois
raisons de ne pas le faire au fil d'E01US010 : (1) la règle 11 du projet (ADR-0009) impose de
déclarer, justifier et documenter toute dépendance ajoutée — un travail qui mérite sa revue propre,
pas un passager clandestin dans une US de configuration ; (2) toucher `package-lock.json` a déjà
cassé la CI front une fois (résolution `@emnapi`), et ce risque doit être isolé dans une US où il
est **le** sujet ; (3) le premier runner de test du front est une décision d'outillage, du même
rang qu'E00US002 (ruff, mypy, ESLint, Prettier) — elle appartient à EPIC-00.

**Résorption attendue.** **E00US014** : installer un runner (vitest, déjà transitif via Vite),
l'ajouter à la CI bloquante (E00US003) et à [`dependances.md`](dependances.md), puis couvrir
`format.ts` — `0`, `« 8 »`, `« 8,1 »`, `« 8,10 »`, `« 0,05 »`, point vs virgule, rejets (`8,105`,
`-8`, `huit`, `8,`), et **stabilité de l'aller-retour**. À faire **avant E08US001**, qui consommera
le tarif pour calculer les montants dus. Marqueur `DETTE-005` posé en tête de `format.ts`.

## Procédure — inscrire une dette

1. **Vérifier qu'elle est assumée** : si elle se corrige dans l'US sans déborder du périmètre, la corriger.
2. **Ajouter la ligne** au tableau « Dette ouverte » (ID `DETTE-nnn` incrémental) — **même commit** que l'introduction.
3. **Rédiger le détail** : constat, conséquence, pourquoi non corrigée, résorption attendue.
4. **Marquer le code** : commentaire à l'endroit exact du raccourci, renvoyant à l'ID (`# DETTE-001 : …`).
5. **Mentionner dans le corps de la PR**, et proposer l'US de résorption à l'utilisateur.
6. À la résorption : déplacer la ligne vers « Dette résorbée » avec l'US qui l'a soldée, et retirer les marqueurs du code.
