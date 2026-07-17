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
| [DETTE-001](#dette-001--suppression-de-tournoi-non-cascadée) | technique | majeur | `backend/infrastructure/db/models.py`, `backend/migrations/versions/` | Aucune FK de la descendance de `tournoi` n'a d'`ON DELETE CASCADE`, ni de suppression applicative équivalente : enfants directs `categorie`, `archer`, `blason`, `gabarit_salle`, `phase`, `depart` (→ `tournoi.id`), enfants indirects `score` (→ `archer.id`, **sauf** par `ArcherRepositorySQL.supprimer` — voir Résorption) et `inscription` (→ `archer.id` **et** `depart.id`, **sauf** par `ArcherRepositorySQL.supprimer` et `DepartRepositorySQL.supprimer` — E02US009) et liens latéraux `categorie.blason_id` (→ `blason.id`) et `archer.categorie_id` (→ `categorie.id`) | Supprimer un tournoi non vide lève une `IntegrityError` → **500** au lieu d'un 409 ou d'une cascade maîtrisée | E01US002 (cycle de vie du tournoi) ; aggravée à chaque nouvelle table/FK de la descendance (E01US004, E01US005, E01US006, E01US008, E01US009, E02US002, E02US004, E02US009) ; E02US003 puis E02US009 y ouvrent des **brèches partielles** (cascades applicatives `archer` → `score`, `archer`/`depart` → `inscription`), qui ne valent que pour les chemins `ArcherRepositorySQL.supprimer` et `DepartRepositorySQL.supprimer` | US dédiée — non planifiée. **⚠️ Deux pièges pour qui la résorbera.** (1) `archer` → `score` **n'est résolu que pour le chemin `ArcherRepositorySQL.supprimer`** (cascade applicative, E02US003) ; la branche **reste ouverte** pour toute suppression d'archer qui ne passe pas par cet adapter — dont la **cascade depuis `tournoi`**, précisément ce que cette dette vise. (2) **Ne pas poser `ON DELETE CASCADE` sur `score.archer_id`** : la confirmation vit **en amont**, dans `ServiceArchers.supprimer` (`ArcherEngage`), la purge dans l'adapter. Une cascade en base ne contourne pas la confirmation *sur ce chemin*, mais elle armerait une purge **silencieuse** sur **tout autre** chemin (cascade tournoi, import, script) — l'option écartée par [ADR-0016](adr/0016-supprimer-un-archer-engage-plutot-que-le-refuser.md) |
| [DETTE-002](#dette-002--hauteur-de-blason-non-modélisée) | conception | majeur | `backend/domain/blason.py`, `docs/modele-de-donnees.md` | `Blason` modélise l'occupation d'une cible par une `taille` (fraction) + `capacite`, mais **pas la hauteur du centre** — 110 cm pour le blason 80 cm des U11 contre 130 cm pour tous les autres (FFTA B.2.2.1.1, C.3.1.1) | Le placement automatique (EPIC-03) pourra composer une butte physiquement intirable : un U11 et des adultes sur la même cible passent le contrôle « somme des fractions ≤ capacité » alors que leurs blasons ne peuvent pas coexister | E01US005 (blasons) ; constatée au cadrage FFTA du 14/07/2026 | E03US001 (placement automatique) — **avant** d'écrire l'algorithme |
| [DETTE-003](#dette-003--config-de-phase-à-plat-au-lieu-de-configpolicies) | conception | majeur | `backend/infrastructure/db/repositories.py` (`_config_phase`, `_vers_phase`), `docs/modele-de-donnees.md` | La `config` d'une phase écrit ses politiques **à plat à la racine** (`config.scoring`, `config.validation`) alors que le modèle cible (ADR-0004) les range sous `config.policies` ; et `scoring` y est un **objet paramétré** au lieu d'un **nom de preset** | Deux conventions coexistent pour le même champ. Le moteur (EPIC-05) devra soit adopter la forme à plat — et renoncer au modèle cible — soit migrer les `config` déjà écrites : c'est une décision reportée, pas évitée | E01US009 (forme posée) ; suivie par E01US015 (`config.validation`), qui s'y aligne plutôt que d'introduire une 2ᵉ convention | E05US003 (assembler les politiques) — **avant** d'écrire le moteur |
| [DETTE-004](#dette-004--messageerreur-dupliqué-dans-chaque-feature-front) | conception | mineur | `frontend/src/features/*/` (10 occurrences) | Le composant `MessageErreur` est copié **à l'identique** dans chaque feature — même signature, même corps, mêmes classes — au lieu de vivre dans `shared/` | Tout changement du rendu d'erreur (ex. le token d'alerte **ambre** du CDC design, `DV-03`) se fait en 10 endroits, avec le risque d'en oublier un : les erreurs sont précisément ce que l'utilisateur voit quand ça va mal | E00US011 puis chaque feature (`admin`, `bareme`, `blasons`, `categories`, `competition`, `gabarits` ×2) ; **aggravée** par E01US015 (8ᵉ copie), E02US001 (9ᵉ copie) puis E02US003 (10ᵉ copie, feature `archers`) | E00US013 (factoriser les briques d'UI partagées) |
| [DETTE-006](#dette-006--cle_nom-nest-plus-chez-elle-dans-domainclubpy) | conception | mineur | `backend/domain/club.py` (`cle_nom`), `backend/domain/archer.py`, `backend/application/archers.py`, `backend/application/clubs.py` | `cle_nom` — le repli casse/accents des noms propres — vit dans `domain/club.py`, mais sert désormais **4** usages dont **2 hors du concept « club »** : `archer.cle_identite` (E02US002) et le tri des archers (E02US003). Sa propre docstring avait posé le seuil : « si un 2ᵉ usage hors club apparaît, extraire dans un `domain/texte.py` en US dédiée » | La fonction est **juste** ; seul son domicile est faux. Un lecteur d'`archer.py` doit aller lire `club.py` pour comprendre comment se replient les noms d'archers, et le prochain usage hors club ira chercher la règle là où elle n'a plus de raison d'être | E02US002 (1ᵉʳ usage hors club) ; **seuil atteint** par E02US003 (2ᵉ) | US dédiée à créer (`refactor/…`) — déplacer dans `domain/texte.py`, 4 appelants, zéro changement de comportement |

| [DETTE-008](#dette-008--une-réponse-400-renvoie-lentrée-du-client-en-écho-non-borné) | technique | mineur | `backend/api/erreurs.py` (`_sur_erreur_validation`) | Une entrée rejetée par Pydantic revient **verbatim** au client : `details = jsonable_encoder(exc.errors())` embarque le champ `input` de chaque erreur, sans borne ni sur la taille d'une valeur, ni sur le nombre d'erreurs listées | **Amplification mesurée ×42,9** (50 Ko envoyés → 2,1 Mo reçus) sur un corps à 10 000 valeurs invalides. Le serveur travaille et répond ~43× le volume reçu, sur un réseau local le jour J où ~30 tablettes partagent la bande passante | E00US009 (patron de bout en bout, forme posée) ; **constatée** le 17/07/2026 à la revue d'E01US014 (axe adversarial), qui l'a mesurée sur `zones` (×42,9) **et** sur `ages` (×41,6) — le régime est **général à tous les DTO**, aucune US ne l'a introduit en propre | US dédiée (`fix/…`) — borner `input` dans `_sur_erreur_validation` (troncature de la valeur + plafond du nombre d'erreurs listées). ⚠️ **Ne pas retirer `details`** : le format `{code, message, details?}` est la règle 5, et [DETTE-007](#dette-007--la-confirmation-dune-suppression-darcher-est-aveugle) prévoit précisément de s'en servir |
| [DETTE-007](#dette-007--la-confirmation-dune-suppression-darcher-est-aveugle) | conception | majeur | `backend/application/archers.py` (`ServiceArchers.supprimer`), `backend/application/departs.py` (`ServiceDeparts.supprimer`), `backend/api/v1/competition.py`, `backend/api/v1/departs.py`, `frontend/src/features/archers/api.ts`, `frontend/src/features/departs/api.ts` | La confirmation d'une suppression **destructrice-confirmable** ne **rappelle pas** au serveur le décompte que le signalement avait annoncé : `autoriser_suppression_engage=true` (archer engagé, `ArcherEngage`) **et** `autoriser_suppression_inscrits=true` (départ à inscriptions, `DepartAvecInscriptions`, E02US009) court-circuitent entièrement le constat, sans le revérifier | Entre le 409 et le rejeu, d'autres tablettes saisissent ou inscrivent (30 le jour J). Confirmer une suppression annoncée à « 1 flèche » (ou « 0 payée ») peut en détruire sept (ou effacer une inscription payée entre-temps) — **sans retour possible**. Or [ADR-0016](adr/0016-supprimer-un-archer-engage-plutot-que-le-refuser.md)/[ADR-0018](adr/0018-supprimer-un-depart-a-inscriptions-confirmable.md) font reposer la sûreté de ces cas sur ce message : « le message énumère ce qui sera détruit » plutôt que « confirmez pour supprimer ». Un message dont rien ne garantit la fraîcheur ne tient pas cette promesse | E02US003 (le chemin destructeur naît avec l'US ; la clause « le drapeau est cru sur parole » vient d'ADR-0015, raisonnée pour un protocole de **création** et reprise sans être rouverte pour une **destruction**) ; **aggravée par E02US009** (2ᵉ chemin destructeur-confirmable, `DepartAvecInscriptions`) | US dédiée — confirmation **contractuelle** : le client renvoie le décompte annoncé, le service re-signale s'il a changé. Exige de faire transiter le décompte par le champ `details` de la réponse d'erreur (`{code, message, details?}`, règle 5) — **jamais peuplé à ce jour** : c'est cette plomberie, sur `ApplicationError`, qui fait le coût |

## Dette résorbée

| ID | Nature | Portée | Soldée par |
|---|---|---|---|
| [DETTE-005](#dette-005--conversion-euroscentimes-sans-aucun-test) | technique | `frontend/src/features/competition/format.ts` | **E00US014** : runner `vitest` installé + script `npm test`, câblé à la CI bloquante (E00US003) ; `format.test.ts` couvre la conversion euros↔centimes (aller-retour, sens de complétion `padEnd`/`padStart`, rejets). Marqueur `# DETTE-005` retiré du code. |

## Détail

### DETTE-001 — suppression de tournoi non cascadée

**Constat.** Aucune FK de la descendance de `tournoi` ne porte de politique de suppression, ni côté
modèle (`ForeignKey(...)` sans `ondelete`) ni côté migrations
(`sa.ForeignKeyConstraint([...], [...])`), et le service de suppression ne purge pas les enfants.
La descendance compte trois natures de liens :

- **enfants directs** de `tournoi` — `categorie`, `archer`, `blason` (FK → `tournoi.id`),
  `gabarit_salle` pour son **instance** appliquée à un tournoi (E01US008 ; les modèles de
  bibliothèque, `tournoi_id NULL`, ne sont pas concernés), `phase` (E01US009) et `depart` (E02US004,
  créneau du tournoi — [ADR-0017](adr/0017-le-depart-est-un-creneau-du-tournoi.md)) ;
- **enfants indirects** — `score` (FK → `archer.id`), donc bloquant pour la suppression d'un `archer`,
  elle-même requise par toute cascade partant du tournoi ; et `inscription` (E02US009), qui porte
  **deux** FK de la descendance — `archer.id` **et** `depart.id` — et bloque donc la suppression de
  **l'un ou l'autre** de ses parents : dans une cascade partant du tournoi, les inscriptions doivent
  partir **avant** les archers et avant les départs ;
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

> **E02US009 ajoute `inscription`, qui a deux parents dans la descendance.** La chaîne devient
> `score → archer`, `inscription → {archer, depart}`, puis `archer → categorie → blason` et
> `depart → tournoi`. Concrètement, une cascade depuis le tournoi doit purger les `inscription`
> **avant** de toucher aux `archer` **ou** aux `depart`. E02US009 en résout deux branches par cascade
> applicative (`ArcherRepositorySQL.supprimer` et `DepartRepositorySQL.supprimer` effacent les
> inscriptions liées dans leur transaction) ; comme pour `score`, ces brèches ne valent **que** pour
> ces deux chemins d'adapter — la cascade depuis le tournoi reste ouverte.

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

**Résorption attendue.** E05US003 (assembler les politiques d'une phase) doit, **avant** d'écrire le
moteur : (a) trancher racine vs `policies`, et preset nommé vs objet paramétré — les deux questions
sont liées mais distinctes ; (b) mettre `docs/modele-de-donnees.md` et l'ADR-0004 en accord avec la
décision (l'un des deux a tort, il faut dire lequel) ; (c) si `policies` est retenu, fournir la
migration des `config` existantes et couvrir en test la relecture d'une `config` de l'ancienne
forme — le même patron que le « zéro migration » d'E01US015 (`_vers_phase`) ; (d) décision
structurante ⇒ **ADR** (qui amendera ou remplacera l'ADR-0011).

### DETTE-004 — `MessageErreur` dupliqué dans chaque feature front

**Constat.** Dix features déclarent chacune leur `MessageErreur`, copie conforme :

```tsx
function MessageErreur({ erreur }: { erreur: Error | null }) {
  if (erreur === null) return null
  const message = erreur instanceof ErreurApi ? erreur.message : 'Une erreur est survenue.'
  return <p className="carte__etat carte__etat--erreur" role="alert">{message}</p>
}
```

Occurrences : `admin/ConnexionAdmin.tsx`, `archers/Archers.tsx`, `bareme/BaremeQualification.tsx`,
`blasons/Blasons.tsx`, `categories/Categories.tsx`, `clubs/Clubs.tsx`,
`competition/TrancheVerticale.tsx`, `gabarits/Gabarits.tsx`, `gabarits/PlanDeSalle.tsx`,
`grain-validation/GrainValidation.tsx`. Même signature, même corps, mêmes classes CSS, même
`role="alert"`.

**Conséquence.** Le rendu des erreurs n'a pas de point unique. Le CDC design impose que l'**alerte
soit ambre** et que les couleurs sémantiques appartiennent au produit (`DV-03`) : appliquer ce token
demandera dix modifications identiques, et il suffit d'en manquer une pour qu'un écran mente sur la
gravité de ce qu'il affiche. Or l'erreur est exactement ce que l'utilisateur regarde quand la
journée déraille.

> **Les blocs de confirmation *hors* `MessageErreur` sont le vrai piège de cette dette.** E02US002 en
> a ouvert un : le bloc d'homonyme de `competition/TrancheVerticale.tsx` (`role="alert"` + bouton
> « Inscrire quand même »), **actionnable** et volontairement **neutre** — un doublon probable n'est
> pas une erreur —, d'où l'absence du modificateur `--erreur`. E02US003 en ajoute **trois** dans
> `archers/Archers.tsx` (« Enregistrer quand même », « Changer quand même de catégorie »,
> « Supprimer définitivement, avec ses résultats »), de la même famille — le dernier en `--danger`,
> parce que sa confirmation **détruit** ([ADR-0016](adr/0016-supprimer-un-archer-engage-plutot-que-le-refuser.md)).
> **E00US013 ne les trouvera pas** en cherchant `MessageErreur` : ce ne sont pas des copies. Ils sont
> désormais **quatre**, dans deux features, et se ressemblent assez pour mériter le même traitement
> que les copies (soit un `MessageErreur` acceptant des enfants, soit un composant frère assumé) —
> sans quoi le token ambre s'appliquera à dix endroits sur quatorze.

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

> **Résorbée par E00US014** (16/07/2026) : runner `vitest` + `format.test.ts` + étape CI bloquante ;
> marqueur retiré de `format.ts`. Le constat ci-dessous est conservé comme trace.

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

### DETTE-006 — `cle_nom` n'est plus chez elle dans `domain/club.py`

**Constat.** `domain.club.cle_nom` replie les espaces de bord, la **casse** et les **accents** d'un
nom. Elle est née pour le référentiel des clubs (E02US001) et y a deux usages légitimes : refuser
un homonyme de club (`ClubRepository.par_nom`) et classer le référentiel à l'écran
(`ServiceClubs.lister`). Elle en a désormais **deux autres, hors du concept « club »** :

- `domain.archer.cle_identite` (E02US002) — replier **nom et prénom d'archer** ;
- `ServiceArchers.lister` (E02US003) — **classer les archers** d'un tournoi.

La réutilisation est le bon geste, et il est délibéré : deux règles de repli qui divergeraient
accepteraient un doublon ici et le refuseraient là. Ce n'est pas elle qui est en cause — c'est le
**domicile**. `cle_nom` n'est plus « une notion métier du référentiel des clubs » : c'est la règle
de repli des noms propres du projet.

Le seuil n'est pas inventé ici : la docstring de `cle_nom` l'avait **posé elle-même** en E02US002,
en acceptant le 1ᵉʳ usage hors club — « *Si un 2ᵉ usage hors club apparaît, extraire dans un
`domain/texte.py` en US dédiée.* » E02US003 est ce 2ᵉ usage. Le déclencheur est donc une **preuve
dans le code d'aujourd'hui** (règle 16), pas un pronostic.

**Conséquence.** La fonction est juste : rien ne casse, aujourd'hui ni demain. Ce qui coûte, c'est
la **lecture** — qui veut comprendre comment se replient les noms d'archers doit aller lire
`club.py`, et `archer.py` importe `cle_nom` depuis un module dont le nom dit le contraire de ce
qu'il fait. Le prochain usage hors club (E02US005, détection de doublons, est un candidat naturel)
ira chercher la règle là où elle n'a plus de raison d'être. Sévérité **mineure** : inconfort local,
aucun invariant en danger.

**Pourquoi non corrigée dans l'US.** [`CLAUDE.md`](../CLAUDE.md) § Dette : un remède structurel se
propose **sur preuve dans le code d'aujourd'hui** — c'est le cas ici, le 2ᵉ usage existe — et « se
traite en ADR + US dédiée, **jamais en douce dans l'US courante** ». Le déplacement touche
`club.py`, `archer.py`,
`ServiceClubs` et `ServiceArchers` — il n'a rien à faire dans une US qui parle d'éditer un archer,
où il noierait le diff métier sous un refactor. E02US003 s'est donc contentée d'**ajouter l'usage
et de constater le déclenchement**.

**Résorption.** US dédiée à créer (`refactor/…`) : déplacer `cle_nom` dans un `domain/texte.py`, y
rapatrier la docstring qui explique le repli (NFKD → retrait des combinantes → `casefold`), mettre
à jour les 4 appelants. **Zéro changement de comportement** — les tests existants sont l'oracle, et
c'est ce qui rend l'US sûre et courte. Marqueur `# DETTE-006` en tête de `cle_nom`.

> **Pourquoi ce numéro a servi deux fois sur la branche `feat/e02us003-…`.** Le commit `621c9e1`
> ouvrait un DETTE-006 « un archer placé ou engagé est définitivement non supprimable ». L'arbitrage
> métier du 16/07/2026 l'a **dissous** : la suppression d'un archer engagé est devenue confirmable
> (elle efface ses résultats), et un archer qui **abandonne** relève du forfait ([E12US004](../stories/E12-pilotage-jour-j.md)),
> qui les conserve. Il n'y avait donc plus de dette — le refus sans issue qui la créait n'existe
> plus. Le numéro, jamais parvenu à `main`, a été réattribué plutôt que laissé en trou.

### DETTE-007 — la confirmation d'une suppression d'archer est aveugle

**Constat.** [ADR-0016](adr/0016-supprimer-un-archer-engage-plutot-que-le-refuser.md) fait reposer la
sûreté de la suppression d'un archer engagé sur **un message** : le 409 énumère ce qui sera détruit
(« a 2 flèches déjà tirées et un placement sur la cible 3 »), plutôt que d'inviter à confirmer. C'est
un choix explicite — « un message qui dirait *confirmez pour supprimer* ferait de la destruction le
chemin par défaut de l'archer qui s'en va ».

Or le rejeu **ne revérifie rien** :

```python
archer = self._archer_existant(archer_id)
if not autoriser_suppression_engage:      # ← le drapeau court-circuite tout le constat
    self._signaler_engagement(archer, archer_id)
self._archers.supprimer(archer_id)
```

Entre le 409 et le clic de confirmation, les **30 tablettes** du jour J saisissent. Confirmer une
suppression annoncée à « 1 flèche » peut en détruire sept — sans retour, et sans journal
(l'audit est E10US005).

**Ce que la sérialisation ne couvre pas.** ADR-0015 §*Pourquoi le contrôle applicatif suffit ici*
démontre qu'il n'y a pas de fenêtre **à l'intérieur** d'une commande soumise à la file. Vrai, et sans
objet : la fenêtre est **entre deux requêtes HTTP**. Le writer unique ne l'a jamais fermée et n'a
jamais prétendu le faire.

**D'où vient le raccourci.** D'ADR-0015 : « *Le drapeau est cru sur parole. Un client peut poser
`autoriser_homonyme: true` dès le premier appel […] C'est la forme normale d'un flux de confirmation
[…] le garde-fou protège d'une **erreur**, pas d'une **volonté**.* » Raisonnement juste — pour un
protocole de **création**, où poser le drapeau à l'aveugle ajoute une ligne. E02US003 l'a repris tel
quel pour un protocole de **destruction**, sans le rouvrir. C'est là que la clause cesse d'être
anodine.

**Pourquoi non corrigée dans l'US.** Le remède propre est une **confirmation contractuelle** : le
client renvoie le compte que le signalement lui a montré, le service re-signale s'il a changé — et le
compte qui bouge est justement le signal que la prémisse de l'admin est fausse (un archer qui tire
pendant qu'on le supprime *participe*, il n'est pas une erreur de saisie). Le service et la route
prennent ce paramètre en ~10 lignes. **Le coût est ailleurs** : le front n'a **pas** le compte —
le classement expose un *total de points*, pas un nombre de flèches. Le lui donner suppose de peupler
le champ `details` de la réponse d'erreur (`{code, message, details?}`, règle 5) — **jamais utilisé
depuis la création du projet** : `ApplicationError` ne le porte pas, `api/erreurs.py` ne le
transmet pas. C'est une modification du **contrat d'erreur de toutes les couches**, pour une seule
erreur. Elle mérite sa propre US et sa propre revue, pas un ajout tardif en fin de correctif de revue.

**Sévérité : majeur, pas bloquant.** La fenêtre est de quelques secondes, ouverte par l'admin
lui-même, et le geste demandé — détruire cet archer — reste celui qu'il obtient. Ce qui est faux,
c'est le **compte annoncé**, pas la nature de l'acte. Rien ne casse un cas utilisateur réel
aujourd'hui ; ce qui se perd, c'est l'exactitude d'un consentement éclairé.

**E02US009 ajoute un 2ᵉ chemin de la même forme.** Supprimer un départ à inscriptions
([ADR-0018](adr/0018-supprimer-un-depart-a-inscriptions-confirmable.md)) suit exactement le patron :
le 409 `depart_avec_inscriptions` énumère « N inscriptions dont P déjà payées », et
`autoriser_suppression_inscrits=true` **court-circuite le décompte au rejeu**. La même fenêtre
inter-requêtes s'ouvre — une inscription payée entre le 409 et la confirmation sera effacée sans que
le décompte l'ait vue. La dette est **une** (la confirmation aveugle des suppressions destructrices),
mais elle a désormais **deux points d'application** ; la résorption contractuelle ci-dessous les traite
ensemble.

**Résorption.** US dédiée, à créer. Portée : `details` sur `ApplicationError` + `api/erreurs.py`
(qui sait déjà le rendre — `_reponse(..., details)` existe et n'est jamais appelé avec) ; `ArcherEngage`
porte `{fleches, cible}`, `DepartAvecInscriptions` porte `{inscriptions, payees}` ; le front lit
`erreur.details` (le `ErreurApi` du client l'expose déjà) et le renvoie. **Elle bénéficierait à tout
le projet** : le format `{code, message, details?}` est une règle non négociable dont la moitié n'a
jamais servi. Marqueurs `DETTE-007` posés sur `ServiceArchers.supprimer`, `ServiceDeparts.supprimer`,
`frontend/src/features/archers/api.ts` et `frontend/src/features/departs/api.ts`.

### DETTE-008 — une réponse 400 renvoie l'entrée du client en écho non borné

**Constat.** `_sur_erreur_validation` (`backend/api/erreurs.py`) traduit un rejet Pydantic en
`400 {code, message, details}`, où `details = jsonable_encoder(exc.errors())`. Chaque entrée de
`exc.errors()` porte un champ **`input`** : la valeur fautive, **telle que le client l'a envoyée**.
Rien ne borne ni la taille d'une valeur, ni le nombre d'erreurs listées.

**Mesuré** le 17/07/2026 (exécution sur `TestClient`, app câblée sur base migrée) :

| Requête | Envoyé | Reçu | Amplification |
|---|---|---|---|
| `POST /blasons` — `zones: ["a"] × 10 000` | 50 053 o | 2 148 960 o | **×42,9** |
| `POST /categories` — `ages: ["a"] × 10 000` | 50 026 o | 2 078 960 o | **×41,6** |
| idem, **sans authentification** | — | **79 o** | — (401, aucun écho) |

**Conséquence.** Le serveur sérialise et renvoie ~43× le volume qu'il reçoit. Le jour J, ~30
tablettes partagent un réseau local sans internet : un corps malformé de quelques dizaines de Ko
suffit à produire plusieurs Mo de réponse, sur le processus qui porte aussi la file d'écriture.
C'est un coût de robustesse, pas un vecteur d'attaque.

**Pourquoi ce n'est pas un point de sécurité.** Le vecteur anonyme n'existe pas : `exiger_admin`
s'exécute **avant** la validation de corps — vérifié, une requête non authentifiée reçoit **401 en
79 octets, sans écho**. Il faut donc déjà être administrateur pour déclencher l'amplification, et un
administrateur dispose de moyens plus directs. Aucune donnée interne ne fuit non plus : `input` est
ce que l'appelant a lui-même envoyé.

**Pourquoi non corrigée dans l'US où elle a été constatée.** E01US014 (blason : valeurs de score
admises) l'a fait apparaître en fermant le vocabulaire des `zones` au DTO — mais elle ne l'a pas
**introduite** : la mesure sur `ages` (×41,6), posé par [ADR-0019](adr/0019-categorie-eligibilite-multi-tranches.md)
et hors de son périmètre, établit que le régime vaut pour **tous les DTO** du projet depuis le
patron d'E00US009. La corriger reviendrait à changer le contrat d'erreur de **toute** la frontière
API depuis une US de configuration de blason : c'est le débordement de périmètre que le § Dette
proscrit. Le registre est ici à sa place — la dette est réelle, tracée, et n'appartient à personne.

**Résorption attendue.** US dédiée (`fix/…`) sur `_sur_erreur_validation` seul : tronquer `input`
(la **valeur**, pas son `repr` — cf. `domain.blason._extrait`, qui traite le même problème côté
domaine) et plafonner le nombre d'erreurs listées, avec un test qui borne la réponse. Le travail
est **local à un gestionnaire**, sans migration ni changement de code métier.

⚠️ **Piège pour qui la résorbera** : **ne pas supprimer `details`**. Le format
`{code, message, details?}` est la **règle 5**, et [DETTE-007](#dette-007--la-confirmation-dune-suppression-darcher-est-aveugle)
prévoit explicitement de s'en servir pour faire transiter le décompte d'une confirmation
destructrice — un champ jamais peuplé à ce jour. Il faut **borner** `details`, pas le retirer.

Marqueur `DETTE-008` posé sur `_sur_erreur_validation` (`backend/api/erreurs.py`).

## Procédure — inscrire une dette

1. **Vérifier qu'elle est assumée** : si elle se corrige dans l'US sans déborder du périmètre, la corriger.
2. **Ajouter la ligne** au tableau « Dette ouverte » (ID `DETTE-nnn` incrémental) — **même commit** que l'introduction.
3. **Rédiger le détail** : constat, conséquence, pourquoi non corrigée, résorption attendue.
4. **Marquer le code** : commentaire à l'endroit exact du raccourci, renvoyant à l'ID (`# DETTE-001 : …`).
5. **Mentionner dans le corps de la PR**, et proposer l'US de résorption à l'utilisateur.
6. À la résorption : déplacer la ligne vers « Dette résorbée » avec l'US qui l'a soldée, et retirer les marqueurs du code.
