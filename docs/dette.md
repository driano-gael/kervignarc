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
| [DETTE-001](#dette-001--suppression-de-tournoi-non-cascadée) | technique | majeur | `backend/infrastructure/db/models.py`, `backend/migrations/versions/` | Aucune FK de la descendance de `tournoi` n'a d'`ON DELETE CASCADE`, ni de suppression applicative équivalente : enfants directs `categorie`, `archer`, `blason`, `gabarit_salle`, `phase`, `depart`, `scoreur`, `poste`, `entree_audit` (→ `tournoi.id`), enfants indirects `score` (→ `archer.id`, **sauf** par `ArcherRepositorySQL.supprimer` — voir Résorption), `inscription` (→ `archer.id` **et** `depart.id`, **sauf** par `ArcherRepositorySQL.supprimer` et `DepartRepositorySQL.supprimer` — E02US009) et `serie` (→ `tournoi.id` **et** `archer.id`, **sauf** par `ArcherRepositorySQL.supprimer` — E04US002 ; sa table enfant `volee` → `serie.id` est en **`ON DELETE CASCADE`**, **hors** dette comme `placement`) et liens latéraux `categorie.blason_id` (→ `blason.id`) et `archer.categorie_id` (→ `categorie.id`) | Supprimer un tournoi non vide lève une `IntegrityError` → **500** au lieu d'un 409 ou d'une cascade maîtrisée | E01US002 (cycle de vie du tournoi) ; aggravée à chaque nouvelle table/FK de la descendance (E01US004, E01US005, E01US006, E01US008, E01US009, E02US002, E02US004, E02US009, E10US003, E04US001, E10US005, E04US002) ; E02US003, E02US009 puis E04US002 y ouvrent des **brèches partielles** (cascades applicatives `archer` → `score`, `archer`/`depart` → `inscription`, `archer` → `serie`), qui ne valent que pour les chemins `ArcherRepositorySQL.supprimer` et `DepartRepositorySQL.supprimer` ; E02US005 (`ArcherRepositorySQL.fusionner`) **réassigne** cette même descendance (`archer` → `score`/`inscription`/`serie`) vers un autre archer — **3ᵉ chemin adapter conscient de la descendance d'`archer`**, à mettre à jour aussi si une table-enfant d'`archer` s'ajoute (n'aggrave pas la dette : n'ajoute ni table ni FK) | US dédiée — non planifiée. **⚠️ Deux pièges pour qui la résorbera.** (1) `archer` → `score` **n'est résolu que pour le chemin `ArcherRepositorySQL.supprimer`** (cascade applicative, E02US003) ; la branche **reste ouverte** pour toute suppression d'archer qui ne passe pas par cet adapter — dont la **cascade depuis `tournoi`**, précisément ce que cette dette vise. (2) **Ne pas poser `ON DELETE CASCADE` sur `score.archer_id`** : la confirmation vit **en amont**, dans `ServiceArchers.supprimer` (`ArcherEngage`), la purge dans l'adapter. Une cascade en base ne contourne pas la confirmation *sur ce chemin*, mais elle armerait une purge **silencieuse** sur **tout autre** chemin (cascade tournoi, import, script) — l'option écartée par [ADR-0016](adr/0016-supprimer-un-archer-engage-plutot-que-le-refuser.md) |
| [DETTE-003](#dette-003--config-de-phase-à-plat-au-lieu-de-configpolicies) | conception | majeur | `backend/infrastructure/db/repositories.py` (`_config_phase`, `_vers_phase`), `docs/modele-de-donnees.md` | La `config` d'une phase écrit ses politiques **à plat à la racine** (`config.scoring`, `config.validation`) alors que le modèle cible (ADR-0004) les range sous `config.policies` ; et `scoring` y est un **objet paramétré** au lieu d'un **nom de preset** | Deux conventions coexistent pour le même champ. Le moteur (EPIC-05) devra soit adopter la forme à plat — et renoncer au modèle cible — soit migrer les `config` déjà écrites : c'est une décision reportée, pas évitée | E01US009 (forme posée) ; suivie par E01US015 (`config.validation`), qui s'y aligne plutôt que d'introduire une 2ᵉ convention | E05US003 (assembler les politiques) — **avant** d'écrire le moteur |
| [DETTE-006](#dette-006--cle_nom-nest-plus-chez-elle-dans-domainclubpy) | conception | mineur | `backend/domain/club.py` (`cle_nom`), `backend/domain/archer.py`, `backend/domain/doublons.py`, `backend/application/archers.py`, `backend/application/clubs.py` | `cle_nom` — le repli casse/accents des noms propres — vit dans `domain/club.py`, mais sert désormais **5** usages dont **3 hors du concept « club »** : `archer.cle_identite` (E02US002), le tri des archers (E02US003) et la détection de doublons `domain/doublons.py` (E02US005). Sa propre docstring avait posé le seuil : « si un 2ᵉ usage hors club apparaît, extraire dans un `domain/texte.py` en US dédiée » | La fonction est **juste** ; seul son domicile est faux. Un lecteur d'`archer.py` ou de `doublons.py` doit aller lire `club.py` pour comprendre comment se replient les noms d'archers, et le prochain usage hors club ira chercher la règle là où elle n'a plus de raison d'être | E02US002 (1ᵉʳ usage hors club) ; **seuil atteint** par E02US003 (2ᵉ) ; **3ᵉ usage hors club** par E02US005 (`domain/doublons.py`, détection de doublons) | US dédiée à créer (`refactor/…`) — déplacer dans `domain/texte.py`, 5 appelants, zéro changement de comportement |

| [DETTE-008](#dette-008--une-réponse-400-renvoie-lentrée-du-client-en-écho-non-borné) | technique | mineur | `backend/api/erreurs.py` (`_sur_erreur_validation`) | Une entrée rejetée par Pydantic revient **verbatim** au client : `details = jsonable_encoder(exc.errors())` embarque le champ `input` de chaque erreur, sans borne ni sur la taille d'une valeur, ni sur le nombre d'erreurs listées | **Amplification mesurée ×42,9** (50 Ko envoyés → 2,1 Mo reçus) sur un corps à 10 000 valeurs invalides. Le serveur travaille et répond ~43× le volume reçu, sur un réseau local le jour J où ~30 tablettes partagent la bande passante | E00US009 (patron de bout en bout, forme posée) ; **constatée** le 17/07/2026 à la revue d'E01US014 (axe adversarial), qui l'a mesurée sur `zones` (×42,9) **et** sur `ages` (×41,6) — le régime est **général à tous les DTO**, aucune US ne l'a introduit en propre | US dédiée (`fix/…`) — borner `input` dans `_sur_erreur_validation` (troncature de la valeur + plafond du nombre d'erreurs listées). ⚠️ **Ne pas retirer `details`** : le format `{code, message, details?}` est la règle 5, et [DETTE-007](#dette-007--la-confirmation-dune-suppression-darcher-est-aveugle) s'en sert (canal `details` désormais peuplé par E12US007, [ADR-0040](adr/0040-alerte-par-calcul-d-impact.md)) |
| [DETTE-007](#dette-007--la-confirmation-dune-suppression-darcher-est-aveugle) | conception | majeur | `backend/application/archers.py` (`ServiceArchers.supprimer`), `backend/application/departs.py` (`ServiceDeparts.supprimer`), `backend/api/v1/competition.py`, `backend/api/v1/departs.py`, `frontend/src/features/archers/api.ts`, `frontend/src/features/departs/api.ts` | La confirmation d'une suppression **destructrice-confirmable** ne **rappelle pas** au serveur le décompte que le signalement avait annoncé : `autoriser_suppression_engage=true` (archer engagé, `ArcherEngage`) **et** `autoriser_suppression_inscrits=true` (départ à inscriptions, `DepartAvecInscriptions`, E02US009) court-circuitent entièrement le constat, sans le revérifier | Entre le 409 et le rejeu, d'autres tablettes saisissent ou inscrivent (30 le jour J). Confirmer une suppression annoncée à « 1 flèche » (ou « 0 payée ») peut en détruire sept (ou effacer une inscription payée entre-temps) — **sans retour possible**. Or [ADR-0016](adr/0016-supprimer-un-archer-engage-plutot-que-le-refuser.md)/[ADR-0018](adr/0018-supprimer-un-depart-a-inscriptions-confirmable.md) font reposer la sûreté de ces cas sur ce message : « le message énumère ce qui sera détruit » plutôt que « confirmez pour supprimer ». Un message dont rien ne garantit la fraîcheur ne tient pas cette promesse | E02US003 (le chemin destructeur naît avec l'US ; la clause « le drapeau est cru sur parole » vient d'ADR-0015, raisonnée pour un protocole de **création** et reprise sans être rouverte pour une **destruction**) ; **aggravée par E02US009** (2ᵉ chemin destructeur-confirmable, `DepartAvecInscriptions`) | US dédiée — confirmation **contractuelle** : le client renvoie le décompte annoncé, le service re-signale s'il a changé. Exige de faire transiter le décompte par le champ `details` de la réponse d'erreur (`{code, message, details?}`, règle 5) — **plomberie désormais posée par E12US007** ([ADR-0040](adr/0040-alerte-par-calcul-d-impact.md)) : `ReplacementNonConfirme.details` peuple le canal et `_sur_erreur_application` le lit, le coût du correctif est donc réduit d'autant. Reste à faire : la confirmation **contractuelle** (renvoi du décompte annoncé + re-signalement) sur les chemins `archer`/`départ` |
| [DETTE-010](#dette-010--capacité-de-cible-plafonnée-à-4-en-dur) | technique | majeur | `backend/domain/gabarit_salle.py` (`CAPACITE_CIBLE_MAX`, `POSITIONS`) | Le gabarit **borne la capacité d'une cible à [1,4]** (`CAPACITE_CIBLE_MAX = len(POSITIONS)`, `POSITIONS = ("A","B","C","D")` en dur) alors que le **modèle** (`modele-de-donnees.md`, `CIBLE.capacite`) **et** le **référentiel** (§5, EF-4.3) la veulent **non bornée** — la FFTA décrit une configuration à **3 triples verticaux** (> 4 postes) | Impossible de configurer une cible de plus de 4 postes ; **divergence code ↔ modèle ↔ référentiel** : la connaissance du projet dit « non borné », le code refuse | E01US007 (gabarit de salle) ; **constatée le 18/07/2026** (entretien de conception) | **E01US019** — délester le plafond, positions au-delà de `D` (`E`, `F`…), le placement (E03) suit |
| [DETTE-011](#dette-011--lagrégat-mono-flèche-sappelle-score-pas-fleche) | conception | mineur | `backend/domain/score.py` (`Score`, `ScoreId`), `backend/domain/ports.py` (`ScoreRepository`), `backend/domain/erreurs.py` (`ScoreInvalide`) | L'agrégat mono-flèche s'appelle `Score`, mais le [glossaire](glossaire.md) réserve `Fleche` au **tir unique** et `score` au **total** de points | Au vrai scoring (E04/E05 : volées, cumul), le nom `Score` sera pris par le **mauvais** concept → renommage subi ou ambiguïté durable dans le domaine et l'API | E00US011 (walking skeleton) ; **constatée le 18/07/2026** (audit de revue complète de `main`) | **Révisée 19/07/2026 (E04US002)** : le vrai scoring modélise la flèche comme **valeur** dans `Volee` (agrégats `Serie`/`Volee`), sans renommer `Score` — qui **survit** comme modèle de lecture du classement de démo. Le nom-clash est désamorcé (le total s'appelle `cumul`). **Révisée 20/07/2026 (E06US001, correctif DETTE-013)** : les gardes d'engagement sont repointées sur `Serie` — `Score` n'a désormais **plus aucun lecteur**, seul le `saisir_score` mort (`POST /scores`, sans appelant produit) l'écrit encore. Sa suppression (endpoint + agrégat + table `score`) redevient l'objet propre de cette dette, sans dépendance de lecture, dans une US `fix/`/`refactor/` dédiée ; voir détail |
| [DETTE-012](#dette-012--lurl-du-qr-de-cible-est-lorigine-de-la-requête-admin) | technique | mineur | `backend/application/documents_salle.py` (`_url_rattachement`) | L'URL encodée dans le QR de cible est **absolue**, bâtie sur l'**origine de la requête admin** (`request.base_url`, passée par l'API) : il n'existe pas de base URL publique configurée côté serveur. Générer les étiquettes depuis `localhost` (console du serveur) produit donc des QR pointant sur `http://localhost:8000/?poste=…`, inutilisables depuis une tablette | Un QR généré depuis `localhost` renvoie la tablette **sur elle-même** : le « filet » de re-rattachement (scanner le QR pour revenir sur sa cible) ne fonctionne pas. **Sans effet dans le flux nominal** : le jour J, l'admin atteint le serveur par son **IP réseau** (les 30 tablettes aussi), donc `base_url` = l'IP LAN et le QR est correct | E09US008 (impression des QR) ; **choix tranché en réalisation** (règle 11/12 : pas de config réseau introduite en douce ici) | E11US001 (release & mise en réseau) — **base URL publique configurable**, source unique pour tous les liens absolus (QR, éventuels partages) |
| [DETTE-014](#dette-014--la-complétude-ignore-le-forfait) | conception | majeur | `backend/application/completude.py` (`_serie_complete`) | La complétude (E12US005) définit une cible *terminée* comme « **toutes les séries validées** » (`Serie.est_complete`), **sans notion de forfait**. Or E12US004 (« tracer un forfait », ⬜ non livrée) impose de **préserver les flèches déjà tirées** : un archer forfait garde sa série partielle, jamais les N volées verrouillées | **Nul aujourd'hui** (aucun forfait n'existe encore). **Dès qu'E12US004 est livrée** : une cible portant un archer forfait ne sera **jamais** « terminée » → qualification bloquée en `ALERTE`, `sportif_complet` **faux à jamais**, l'avertissement de clôture « X cibles ne sont pas terminées » se déclenche alors que le tournoi est sportivement fini — la complétude **ment** | E12US005 (la complétude naît sans notion de forfait, E12US004 n'étant pas encore livrée) | **E12US004** — y traiter un archer forfait comme **« série close par forfait »** dans `_serie_complete` (le forfait *termine* la participation de l'archer). Marqueur `# DETTE-014` posé sur `_serie_complete` |

## Dette résorbée

| ID | Nature | Portée | Soldée par |
|---|---|---|---|
| [DETTE-005](#dette-005--conversion-euroscentimes-sans-aucun-test) | technique | `frontend/src/features/competition/format.ts` | **E00US014** : runner `vitest` installé + script `npm test`, câblé à la CI bloquante (E00US003) ; `format.test.ts` couvre la conversion euros↔centimes (aller-retour, sens de complétion `padEnd`/`padStart`, rejets). Marqueur `# DETTE-005` retiré du code. |
| [DETTE-002](#dette-002--hauteur-de-blason-non-modélisée) | conception | `backend/domain/categorie.py`, `docs/modele-de-donnees.md` | **E03US001** ([ADR-0022](adr/0022-hauteur-de-centre-sur-la-categorie.md)) : la hauteur du centre de l'or vit sur `Categorie` (`hauteur_cm`, 130 par défaut, 110 pour les U11) ; le placement en fait une **contrainte de 1er rang** — une butte, une seule hauteur (test « U11 + adultes → séparés »). Migration `0020` (backfill 110 si `ages` contient U11). |
| DETTE-009 | conception | `backend/api/v1/categories.py` (`ModifierCategorieRequete`) | **E03US004** : le formulaire catégorie porte la hauteur du centre (UI de placement), donc `hauteur_cm` est rendue **obligatoire** au PUT (DTO + `ServiceCategories.modifier` en keyword-only) ; le PUT redevient **intégralement total** ([ADR-0020](adr/0020-blason-zones-vocabulaire-ferme-et-defaut-sur-ensemble.md)), l'entorse « champ partiel » disparaît. Test de non-régression HTTP **inversé** (omission → 400). |
| [DETTE-013](#dette-013--les-gardes-dengagement-lisent-un-score-que-plus-rien-nécrit) | conception | `backend/application/archers.py` (`_signaler_engagement`, `_signaler_changement_categorie`) | **E06US001** (même branche, 20/07/2026) : les deux gardes lisent désormais `SerieRepository.par_archer` — « a tiré » = **au moins une volée validée** (`Serie.nb_fleches_validees`), plus l'agrégat `Score` mort. Arbitrage « volée *validée* (pas toute volée saisie) » reversé dans `stories/E02-inscriptions.md` (règle 9). Tests dérivés du CA E02US003/E02US009 (service **et** API). Marqueur retiré. Reste ouvert sur son objet propre : la **suppression** de `Score`, désormais sans lecteur (DETTE-011). |
| [DETTE-004](#dette-004--messageerreur-dupliqué-dans-chaque-feature-front) | conception | `frontend/src/features/*/`, `frontend/src/shared/ui/MessageErreur.tsx` | **E00US013** (21/07/2026) : `MessageErreur` extrait dans `shared/ui/`, **19 copies retirées** (18 définitions `function MessageErreur` + le rendu inline verbatim de `postes/Postes.tsx`) — recompte terrain du grep, la baseline « 16/18 » sous-numérotait. Rendu **inchangé** (mêmes classes, même `role="alert"`). Les autres `role="alert"` du front ont été **examinés et laissés** à dessein : blocs de **confirmation** à action (archers ×2 édition, NouvelArcher inscription — ton neutre, pas `--erreur`), rendu **ambre** ad hoc du refus 409 de placement (`placement__alerte`, helper `messageErreur` conservé), et rendus **ad hoc contextuels** (« … injoignable — {message} ») hors périmètre du composant générique dupliqué. Marqueurs `DETTE-004` retirés du code. |

## Détail

### DETTE-001 — suppression de tournoi non cascadée

**Constat.** Aucune FK de la descendance de `tournoi` ne porte de politique de suppression, ni côté
modèle (`ForeignKey(...)` sans `ondelete`) ni côté migrations
(`sa.ForeignKeyConstraint([...], [...])`), et le service de suppression ne purge pas les enfants.
La descendance compte trois natures de liens :

- **enfants directs** de `tournoi` — `categorie`, `archer`, `blason` (FK → `tournoi.id`),
  `gabarit_salle` pour son **instance** appliquée à un tournoi (E01US008 ; les modèles de
  bibliothèque, `tournoi_id NULL`, ne sont pas concernés), `phase` (E01US009), `depart` (E02US004,
  créneau du tournoi — [ADR-0017](adr/0017-le-depart-est-un-creneau-du-tournoi.md)), `scoreur`
  (E10US003, personne habilitée à valider — [ADR-0025](adr/0025-mode-d-identite-scoreur-par-code-individuel.md))
  et `poste` (E04US001, credential d'une cible — [ADR-0029](adr/0029-mode-d-identite-poste-de-cible-et-jeton-de-poste.md)) ;
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

E03US004 ajoute la table `placement` avec **deux FK en `ON DELETE CASCADE`** (`inscription_id`,
`depart_id`) : **hors** de cette dette. C'est de la donnée **dérivée, reconstructible et feuille**, et
sa disparition en cascade est **assumée et argumentée**
([ADR-0024](adr/0024-plan-de-cibles-materialise-ajustable.md)), pas un raccourci non tranché — le
futur résolveur de DETTE-001 n'a **rien à faire** sur `placement`, elle s'auto-cascade déjà.

E10US003 ajoute `scoreur` (FK → `tournoi.id`, sans `ON DELETE`), enfant direct **feuille** : aucun
enfant à purger avant lui, aucun lien latéral. Comme `depart`, une cascade partant du tournoi devra
simplement le supprimer avant le tournoi — rien de plus. Les **sessions** de scoreur ne sont pas en
base (mémoire, `ScoreurSessionStore`), donc rien à cascader de ce côté.

E04US001 ajoute `poste` (FK → `tournoi.id`, sans `ON DELETE`), même profil que `scoreur` : enfant
direct **feuille**, à supprimer avant le tournoi. Ses **sessions** sont en mémoire
(`PosteSessionStore`), rien à cascader ; la contrainte `UNIQUE(tournoi_id, cible_index)` disparaît
avec la ligne, sans effet sur la cascade.

E10US005 ajoute `entree_audit` (FK → `tournoi.id`, sans `ON DELETE`), même profil que
`scoreur`/`poste` : enfant direct **feuille**, à supprimer avant le tournoi. Journal **en ajout
seul**, aucun enfant en aval, rien à cascader ; l'`auteur` y est un **nom** (pas une FK vers
`scoreur`), donc supprimer un scoreur ne touche pas ses traces — et la cascade du tournoi n'a que la
ligne `entree_audit` elle-même à retirer.

E04US002 (tranche persistance PR2a) ajoute `serie` (racine de saisie de qualification) avec **deux
FK sans `ON DELETE`** — `tournoi_id` (enfant direct) **et** `archer_id` (enfant indirect via
`archer`). Dans une cascade partant du tournoi, la série doit partir **avant** l'archer, comme
`score` ; E04US002 résout cette branche par **cascade applicative**
(`ArcherRepositorySQL.supprimer` efface la série de l'archer dans sa transaction), brèche qui ne
vaut — comme `score`/`inscription` — **que** pour ce chemin d'adapter : la cascade depuis le tournoi
reste ouverte. Sa table enfant `volee` (`serie_id`) porte, elle, **`ON DELETE CASCADE`** : **hors**
de cette dette, à l'image de `placement` — composant strict de l'agrégat `Serie`, sa disparition
suit celle de la série (le futur résolveur de DETTE-001 n'a **rien à faire** sur `volee`). L'agrégat
`Score` du walking skeleton subsiste par ailleurs (classement de démo, DETTE-011) : `serie` **ne le
remplace pas encore** côté base, les deux enfants d'`archer` coexistent.

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

**Résorption (E03US001, 17/07/2026 — [ADR-0022](adr/0022-hauteur-de-centre-sur-la-categorie.md)).**
La hauteur vit sur **`Categorie`** (`hauteur_cm`, entier `> 0`, défaut 130), et non sur le blason
(option (a) tranchée par arbitrage : la hauteur suit la catégorie d'âge de l'archer, pas le carton).
Ajoutée au modèle et à la **migration `0020`** (backfill 110 pour les catégories dont les `ages`
contiennent U11, 130 sinon) — point (b). Le moteur de placement en fait une **contrainte de 1er
rang** : tous les archers d'une cible partagent la même hauteur, un archer d'une autre hauteur
bascule sur une cible neuve, faute de quoi il ressort en **conflit** — point (c). Test « U11 (110) +
adultes (130) → séparés / conflit » couvert dans `test_domain_placement.py` — point (d). **Hors
résorption** : la **plage** de hauteur des buttes à 4 blasons (100–162 cm) reste hors modèle (le
mono-club place au centre 130/110), à traiter en contrainte avancée si un cas réel l'exige.

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

> **✅ Résorbée par E00US013 (21/07/2026).** `MessageErreur` vit dans
> `frontend/src/shared/ui/MessageErreur.tsx` ; les **18 copies locales** (recompte terrain du grep)
> le consomment, plus le rendu inline verbatim de `postes/Postes.tsx` — soit **19 rendus** ralliés à
> un point unique, à **rendu strictement inchangé**. Les autres `role="alert"` ont été examinés et
> **laissés** : les blocs de confirmation à action (archers, NouvelArcher — ton neutre, pas
> `--erreur`) et le refus 409 ambre de placement (`placement__alerte`) ne sont **pas** des affichages
> d'erreur et n'ont pas leur place dans `MessageErreur` ; les rendus **ad hoc contextuels**
> (« … injoignable — {message} ») gardent leur message propre et restent hors périmètre du composant
> générique dupliqué. Le narratif ci-dessous est conservé comme
> trace ; il sous-numérotait (« 16/18 ») — le compte livré est **19 rendus**.

**Constat.** Quinze features déclarent chacune leur `MessageErreur`, copie conforme :

```tsx
function MessageErreur({ erreur }: { erreur: Error | null }) {
  if (erreur === null) return null
  const message = erreur instanceof ErreurApi ? erreur.message : 'Une erreur est survenue.'
  return <p className="carte__etat carte__etat--erreur" role="alert">{message}</p>
}
```

Occurrences (grep exhaustif `function MessageErreur`, 21/07/2026) : `admin/ConnexionAdmin.tsx`,
`archers/Archers.tsx`, `bareme/BaremeQualification.tsx`, `blasons/Blasons.tsx`,
`categories/Categories.tsx`, `clubs/Clubs.tsx`, `departs/Departs.tsx`, `tournois/Tournois.tsx`,
`gabarits/Gabarits.tsx`, `gabarits/PlanDeSalle.tsx`, `grain-validation/GrainValidation.tsx`,
`inscriptions/InscriptionsArcher.tsx`, `placement/Placement.tsx`, `scoreurs/Scoreurs.tsx`,
`scoreur-session/EspaceScoreur.tsx`, `poste/EspacePoste.tsx`, `saisie/Saisie.tsx`,
`paiements/Paiements.tsx`. Même signature, même corps, mêmes classes CSS, même `role="alert"`. Soit
**18 copies dans 17 features** (`gabarits` en a deux). *(La liste ci-dessus avait perdu
`saisie/Saisie.tsx` — E04US002 — jusqu'au grep du 21/07/2026 ; E08US002 ajoute `paiements`.)*

> **Rectification de décompte (revue d'E00US015, 19/07/2026).** Le registre reconduisait « 14 copies
> dans 13 features » ; le grep exhaustif des définitions en trouve **16** — `departs/Departs.tsx`
> (E02US004) et `inscriptions/InscriptionsArcher.tsx` (E02US009) n'avaient jamais été ajoutés à la
> liste lors de leur création. Erreur **préexistante**, corrigée ici au passage puisque cette US
> touche la ligne.

> **E00US015 (coquille admin) a *relocalisé*, pas aggravé.** L'écran monolithique
> `competition/TrancheVerticale.tsx` a disparu ; sa copie vit désormais dans la feature `tournois`
> (gestion des tournois extraite). Le formulaire de création d'archer qu'il enfouissait rejoint la
> feature `archers` (`archers/NouvelArcher.tsx`), qui **réutilise** la copie exportée d'`Archers.tsx`
> plutôt que d'en créer une 15ᵉ — réutilisation **intra-feature** (la feature `archers` garde **une**
> copie), pas une extraction vers `shared/` : ce serait « 13 copies + 1 brique partagée », deux
> conventions au lieu d'une, précisément ce qu'E00US013 doit pouvoir remplacer d'un bloc homogène. Le
> décompte est donc **inchangé par cette US** (une copie retirée, une ajoutée), à **16 copies dans
> 15 features** une fois la baseline rectifiée ci-dessus.

**Conséquence.** Le rendu des erreurs n'a pas de point unique. Le CDC design impose que l'**alerte
soit ambre** et que les couleurs sémantiques appartiennent au produit (`DV-03`) : appliquer ce token
demandera seize modifications identiques, et il suffit d'en manquer une pour qu'un écran mente sur la
gravité de ce qu'il affiche. Or l'erreur est exactement ce que l'utilisateur regarde quand la
journée déraille.

> **Les blocs de confirmation *hors* `MessageErreur` sont le vrai piège de cette dette.** E02US002 en
> a ouvert un : le bloc d'homonyme (`role="alert"` + bouton « Inscrire quand même »), déplacé par
> E00US015 dans `archers/NouvelArcher.tsx` avec le formulaire de création d'archer qu'il accompagne,
> **actionnable** et volontairement **neutre** — un doublon probable n'est
> pas une erreur —, d'où l'absence du modificateur `--erreur`. E02US003 en ajoute **trois** dans
> `archers/Archers.tsx` (« Enregistrer quand même », « Changer quand même de catégorie »,
> « Supprimer définitivement, avec ses résultats »), de la même famille — le dernier en `--danger`,
> parce que sa confirmation **détruit** ([ADR-0016](adr/0016-supprimer-un-archer-engage-plutot-que-le-refuser.md)).
> E03US004 en ajoute un **cinquième** : l'alerte de refus de déplacement `placement__alerte`
> (`placement/Placement.tsx`, `role="alert"` en `var(--warn)`, refus `409` non bloquant).
> **E00US013 ne les trouvera pas** en cherchant `MessageErreur` : ce ne sont pas des copies. Ils sont
> désormais **cinq**, dans trois features, et se ressemblent assez pour mériter le même traitement
> que les copies (soit un `MessageErreur` acceptant des enfants, soit un composant frère assumé) —
> sans quoi le token ambre s'appliquera à onze endroits sur seize.

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
(`ServiceClubs.lister`). Elle en a désormais **trois autres, hors du concept « club »** :

- `domain.archer.cle_identite` (E02US002) — replier **nom et prénom d'archer** ;
- `ServiceArchers.lister` (E02US003) — **classer les archers** d'un tournoi ;
- `domain.doublons._rapprocher` (E02US005) — replier **nom et prénom** pour rapprocher les
  **doublons** d'archers (détection heuristique).

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
`club.py`, et `archer.py` (comme `doublons.py`) importe `cle_nom` depuis un module dont le nom dit
le contraire de ce qu'il fait. Le 3ᵉ usage hors club **est arrivé** (E02US005, `domain/doublons.py`,
détection de doublons — que ce constat avait nommé comme candidat naturel) : il va bien chercher la
règle là où elle n'a plus de raison d'être. Sévérité **mineure** : inconfort local, aucun invariant
en danger.

**Pourquoi non corrigée dans l'US.** [`CLAUDE.md`](../CLAUDE.md) § Dette : un remède structurel se
propose **sur preuve dans le code d'aujourd'hui** — c'est le cas ici, le 2ᵉ usage existe — et « se
traite en ADR + US dédiée, **jamais en douce dans l'US courante** ». Le déplacement touche
`club.py`, `archer.py`,
`ServiceClubs` et `ServiceArchers` — il n'a rien à faire dans une US qui parle d'éditer un archer,
où il noierait le diff métier sous un refactor. E02US003 s'est donc contentée d'**ajouter l'usage
et de constater le déclenchement**.

**Résorption.** US dédiée à créer (`refactor/…`) : déplacer `cle_nom` dans un `domain/texte.py`, y
rapatrier la docstring qui explique le repli (NFKD → retrait des combinantes → `casefold`), mettre
à jour les **5** appelants (dont `domain/doublons.py`, E02US005). **Zéro changement de comportement**
— les tests existants sont l'oracle, et c'est ce qui rend l'US sûre et courte. Marqueur `# DETTE-006`
en tête de `cle_nom`.

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

**Résorption.** US dédiée, à créer. **Mise à jour — la plomberie du canal `details` est désormais
posée** par E12US007 ([ADR-0040](adr/0040-alerte-par-calcul-d-impact.md)) : `ReplacementNonConfirme`
porte un `details` chiffré et `_sur_erreur_application` le transmet (`getattr(exc, "details", None)`).
Le contrat d'erreur n'est donc **plus** à ouvrir — il reste à faire porter `details` à `ArcherEngage`
(`{fleches, cible}`) et `DepartAvecInscriptions` (`{inscriptions, payees}`), puis à réaliser la
confirmation **contractuelle** : le front lit `erreur.details` (le `ErreurApi` du client l'expose
déjà) et **renvoie** le décompte, que le service **re-signale** s'il a changé au rejeu. Marqueurs
`DETTE-007` posés sur `ServiceArchers.supprimer`, `ServiceDeparts.supprimer`,
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

### DETTE-010 — capacité de cible plafonnée à 4 en dur

**Constat.** `backend/domain/gabarit_salle.py` fixe `POSITIONS = ("A", "B", "C", "D")` et
`CAPACITE_CIBLE_MAX = len(POSITIONS)` (= 4) ; `_capacite_valide` refuse toute capacité hors `[1, 4]`.
Or le **modèle de données** (`modele-de-donnees.md`, `CIBLE.capacite` : « ≥ 1, non borné ») et le
**référentiel** (§5, §10 ; CDC `EF-4.3`) posent une capacité **non bornée** — la FFTA décrit une
configuration à **3 triples verticaux**, soit une butte de plus de 4 postes.

**Conséquence.** Un admin ne peut pas déclarer une cible à plus de 4 postes via le gabarit : la
configuration à 3 triples verticaux, pourtant documentée, est **irréalisable**. Divergence entre trois
sources qui devraient s'accorder (code, modèle, référentiel), la connaissance faisant foi (« non
borné ») et le code étant en retard.

**Pourquoi tracée ici et non corrigée dans l'entretien.** L'entretien de conception ne touche pas au
code (docs uniquement) ; délester le plafond impacte les **positions** (lettres au-delà de `D`) et le
**moteur de placement** (E03), qui suppose 4 positions — c'est une US, pas une retouche.

**Résorption attendue.** **E01US019** : capacité non bornée, positions au-delà de `D` (`E`, `F`…),
placement adapté. Marqueur `DETTE-010` à poser sur `gabarit_salle.py` à cette occasion.

### DETTE-011 — l'agrégat mono-flèche s'appelle `Score`, pas `Fleche`

**Constat.** L'agrégat qui modélise **une flèche marquée** (`backend/domain/score.py`) porte le nom
`Score`, de même que ses satellites `ScoreId`, `ScoreRepository` (port) et `ScoreInvalide` (erreur).
Or le [glossaire](glossaire.md) distingue deux concepts : **`Fleche`** = « un tir unique » et
**`score`** = « total de points ». Le nom `Score` désigne donc, dans le code, le concept que le
glossaire nomme `Fleche` — et laisse le mot juste (`score` = total) sans porteur.

**Conséquence.** Tant que le walking skeleton ne persiste qu'un point par flèche, l'ambiguïté est
sans effet fonctionnel. Elle se paiera à l'arrivée du **vrai scoring** (E04/E05 : `Volee`, `Serie`,
cumul, sets de duel), quand le concept « total » aura besoin du nom `Score` : soit on renomme
l'agrégat flèche à ce moment-là (renommage **subi**, en pleine US de moteur), soit on garde deux
sens du mot `Score` dans le même code (ambiguïté **durable**, code↔glossaire divergents — règle 3).

**Pourquoi non corrigée maintenant.** Le renommage traverse le domaine (`score.py`, `ports.py`,
`erreurs.py`), l'application, l'infrastructure (repository + modèle ORM + migration de la table
`score`), l'API et les tests : c'est un `refactor/…` à part entière, hors du périmètre d'un audit.
Le faire « en douce » ici mêlerait un renommage transverse à des correctifs sans rapport.

**Résorption attendue.** US dédiée `refactor/…` **avant E04** : renommer `Score`→`Fleche`,
`ScoreId`→`FlecheId`, `ScoreRepository`→`FlecheRepository`, `ScoreInvalide`→`FlecheInvalide`
(la table `score` peut suivre ou rester, à trancher dans l'US) — **zéro changement de comportement**,
la valeur reste la même, seul le vocabulaire s'aligne sur le glossaire. Marqueur `DETTE-011` posé
sur la classe `Score`.

**Mise à jour 19/07/2026 (E04US002) — non résorbée, et le sera autrement que prévu.** E04US002 (vrai
scoring) modélise la flèche comme **valeur** (`ZoneScore`) *dans* une `Volee`, pas comme entité :
`Serie`/`Volee` **remplaceront** `Score` pour la **saisie** — dès que la **plomberie PR2** les
persistera ; la PR1 « moteur métier » (domaine + service) n'écrit encore rien. Contre l'attente « renommer `Score`→`Fleche`
avant E04 », l'agrégat `Score` n'est **pas** renommé mais **conservé** comme modèle de lecture du
**classement de démo** (`calculer_classement`), jusqu'à son rebasage sur les volées en **E06US001** —
le renommer maintenant démolirait ce classement (périmètre E06). Le nom-clash redouté est **désamorcé
autrement** : le total du scoring s'appelle `cumul`, jamais `Score`. La dette **reste ouverte** (le nom
`Score` désigne toujours une flèche), mais son échéance de résorption glisse à **l'ère E06** (rebasage
du classement), où `Score` perdra son dernier usage et pourra être supprimé plutôt que renommé.

**Mise à jour 20/07/2026 (E06US001) — la prémisse « dernier usage » était fausse.** E06US001 a bien
rebasé le **classement** sur `Serie`/`Volee` : `Score` n'est plus lu par `calculer_classement`. Mais
il n'a **pas** perdu son dernier usage — les **gardes d'engagement** de `ServiceArchers`
(`_signaler_engagement`, `_signaler_changement_categorie`) décident « l'archer a-t-il déjà tiré ? » en
lisant encore `Score` (`ScoreRepository.par_archer`). `Score` **survit donc** comme substrat de ces
gardes, et sa suppression ne peut pas avoir lieu tant qu'elles ne sont pas repointées sur `Serie`. Ce
repointage (et le fait que les gardes lisent désormais un `Score` que **plus aucun flux produit
n'écrit**) est une dette à part entière, inscrite en **[DETTE-013](#dette-013--les-gardes-dengagement-lisent-un-score-que-plus-rien-nécrit)** : c'est **elle** qui porte
désormais l'échéance de suppression de `Score`, dans une US `fix/` dédiée. DETTE-011 reste ouverte sur
son objet propre (le **nom** `Score` désigne une flèche), découplé de cette suppression.

**Mise à jour 20/07/2026 (correctif DETTE-013, même branche E06US001).** Les gardes d'engagement ont
été repointées sur `Serie` (DETTE-013 **résorbée**) : `Score` n'a plus **aucun lecteur**. Ne subsiste
que son **écrivain mort** — `ServiceArchers.saisir_score` derrière `POST /archers/{id}/scores`, sans
appelant produit depuis le retrait du bouton « Marquer ». L'échéance que DETTE-013 portait revient donc
à DETTE-011, mais **allégée** : plus de repointage préalable à faire, il ne reste qu'à **supprimer** le
mort (agrégat `Score`/`ScoreId`/`ScoreRepository`/`ScoreInvalide`, l'endpoint et son DTO, l'adapter +
l'ORM + la table `score` via migration) — un `refactor/`/`fix/` mécanique, sans changement de
comportement observable.

### DETTE-012 — l'URL du QR de cible est l'origine de la requête admin

**Constat.** Le QR de rattachement d'une cible (E09US008) encode une URL **absolue**
`{origine}/?poste=<code>`, où `origine` est l'**origine de la requête admin** qui génère le PDF
(`request.base_url`, passée au service `ServiceDocumentsSalle.etiquettes_cibles`). Le backend ne
connaît **aucune base URL publique** configurée (seules variables d'env : `KERVIGNARC_DATABASE_URL`,
`KERVIGNARC_ENV_FILE`, `KERVIGNARC_FRONTEND_DIST`). L'origine du QR est donc, mécaniquement, l'adresse
par laquelle l'admin a ouvert l'appli au moment d'imprimer.

**Conséquence.** Le QR n'est scannable **utilement** que si cette origine est joignable depuis les
tablettes. Dans le flux nominal, elle l'est : le jour J, l'admin — comme les ~30 tablettes — atteint
le serveur par son **IP réseau local**, donc `base_url` vaut cette IP et le QR est correct. Le piège
est l'admin qui imprime **depuis la console du serveur** via `http://localhost:8000` : les QR
pointent alors sur `localhost`, et une tablette qui les scanne revient **sur elle-même** — le
« filet » de re-rattachement (`D-07`, le cœur de l'US) tombe. C'est une **limite de déploiement**,
pas un bug du flux nominal ; d'où la sévérité mineure.

**Pourquoi non corrigée maintenant.** La corriger proprement, c'est introduire une **base URL
publique configurable** (variable d'env ou réglage) — une décision de **mise en réseau** qui
appartient à E11US001 (« Release, base et mise en réseau »), pas à une US d'export. L'amorcer ici
(un demi-réglage que E11US001 réécrirait) serait le contournement local que la règle de dette
proscrit. `request.base_url` est le meilleur défaut **sans config**, et il est correct dans le flux
réel.

**Résorption attendue.** E11US001 : exposer une base URL publique configurée une fois (l'IP/port du
serveur sur le réseau du gymnase), et la faire consommer par le service à la place de
`request.base_url` — source unique pour tous les liens absolus. Marqueur `DETTE-012` posé sur
`_url_rattachement` dans `application/documents_salle.py`.

### DETTE-013 — les gardes d'engagement lisent un `Score` que plus rien n'écrit

**Constat.** Les deux gardes de sûreté de `ServiceArchers` — `_signaler_engagement` (suppression
d'archer) et `_signaler_changement_categorie` (édition) — décident « l'archer a-t-il déjà tiré ? » en
comptant `ScoreRepository.par_archer(...)`, c.-à-d. l'agrégat **`Score`** du walking skeleton. Or
E06US001 retire le bouton « Marquer », **dernier écrivain de `Score`** : plus aucun flux produit ne
l'alimente (l'endpoint `POST /scores` survit mais n'a plus d'appelant). La **vraie** saisie (E04US002)
écrit des `Serie`/`Volee`, jamais `Score`. En production, `fleches` vaut donc **toujours 0**.

**Conséquence.** Le motif « flèches déjà tirées » de ces gardes est mort :
- suppression : un archer aux volées validées mais **ni placé ni inscrit** (chemin de saisie **admin**,
  `contexte=None`) passe les trois motifs à zéro → il est supprimé **sans aucun avertissement**, et sa
  feuille de marque part en **cascade** (`ArcherRepositorySQL.supprimer` fait un `DELETE` sur `serie`,
  puis `volee` en `ON DELETE CASCADE`). Même quand l'archer est inscrit sur un départ, le message
  **sous-estime** ce qui est détruit (« inscription sur un départ » au lieu d'une série complète) ;
- changement de catégorie : `_signaler_changement_categorie` ne lit **que** `Score` → il ne se
  déclenche jamais pour un archer aux volées réelles, dont les flèches basculent silencieusement vers
  un autre classement.

**Nature / imputation.** La **racine préexiste à E04US002** (les gardes ont toujours lu `Score`
pendant que la saisie réelle écrivait `Serie`). E06US001 ne modifie pas leur code, mais (a) supprime
le dernier écrivain de `Score`, figeant le motif « flèches » à zéro pour **tous** les archers, et (b)
l'a **rejustifié à tort** dans son corps de commit (« l'endpoint `/scores` reste — contrôle « archer
engagé » »). C'est ce qui la rend imputable ici. Classée **majeur** (perte de données possible), pas
bloquant : le comportement de **production** n'est pas régressé par cette US (le motif était déjà mort
depuis E04US002), et le chemin nominal de suppression reste couvert par « placé »/« inscrit ».

**Résorbée par E06US001 (20/07/2026), dans la branche même.** Sur décision de ne pas merger le défaut,
les deux gardes ont été repointées sur `SerieRepository.par_archer(tournoi_id, archer_id)` : « a
tiré » = **au moins une volée validée** (`Serie.nb_fleches_validees`, qui compte les flèches des seules
volées verrouillées — le manqué `M` compris). Le message d'engagement énumère désormais le **vrai**
décompte de flèches. Tests **dérivés du CA** E02US003/E02US009 (règle 9) : au niveau **service**
(`test_service_archers`, via une volée validée montée par `Montage.faire_tirer`) **et** **API**
(`test_competition_api`, via `_semer_serie`), plus un test **domaine** de `nb_fleches_validees`.

**Arbitrage tranché le 20/07/2026 (reversé dans `stories/E02-inscriptions.md`).** « A tiré » retient
la **volée validée**, pas *toute* volée saisie : une volée saisie mais non validée n'est qu'un état
intermédiaire (cohérent avec `cumul`/classement, qui ne comptent que le validé) — elle ne rend l'archer
ni engagé (suppression) ni bloqué (changement de catégorie). Deux tests figent cette limite (archer à
volée non validée → aucun signalement). *Idée connexe **hors périmètre**, laissée à une US à écrire (avec
son CA) : une **alerte douce** distincte — « une saisie est en cours, attends-tu la validation ? » —
au moment de supprimer/forfaiter ; ce n'est pas la garde « archer engagé », c'est un autre signalement.*

**Reste ouvert.** La **suppression** de `Score` (agrégat + endpoint mort `POST /scores` + table)
revient à **DETTE-011**, désormais **sans dépendance de lecture** (plus aucune garde ne lit `Score`).
La confirmation aveugle de suppression reste **DETTE-007**. Marqueur `DETTE-013` retiré des deux gardes.

### DETTE-014 — la complétude ignore le forfait

**Constat.** La complétude du tournoi (E12US005) décide qu'une cible `(départ, cible)` est *terminée*
quand **tous** ses archers placés ont une série **complète** — au sens de `Serie.est_complete` :
toutes les volées du barème **validées**. Cette définition n'a **aucune notion de forfait**. Or
E12US004 (« Tracer un forfait », ⬜ non livrée) pose que l'archer absent **n'est pas un trou** mais une
**donnée**, et que **les flèches déjà tirées sont préservées** : un forfait garde donc sa série
partielle (k volées sur N), jamais les N volées verrouillées.

**Conséquence.** Tant qu'E12US004 n'existe pas, l'impact est **nul** (aucun forfait ne peut être
tracé). Mais **dès sa livraison**, un archer qui abandonne après quelques volées maintient sa cible en
état incomplet : `_serie_complete` renvoie `False` pour lui à jamais → la cible n'est **jamais**
comptée terminée → la qualification reste `ALERTE`, `sportif_complet` est **faux à jamais**, et
l'avertissement de clôture « X cibles ne sont pas terminées » se déclenche à chaque tentative de
terminer alors que le tournoi est **sportivement fini**. La complétude **ment** : elle compte comme
« reste à tirer » ce qu'une décision d'arbitrage a clos. Le garde-fou du CA d'E12US004 (« l'adversaire
passe, le tableau reste cohérent ») n'a aucun écho côté complétude.

**Pourquoi non corrigée maintenant.** Le modèle de forfait n'existe pas encore (`Serie`/`Volee` n'ont
pas de statut d'abandon, E12US004 non livrée) : il n'y a **rien à interroger**. Poser aujourd'hui une
branche « ou forfait » serait du code mort branché sur une donnée absente. La dette est donc **inscrite
et marquée** (`# DETTE-014` sur `_serie_complete`) plutôt que résorbée, pour que l'US qui livrera le
forfait ne l'oublie pas — c'est un **angle mort silencieux** (rien à l'écran ne signale qu'un forfait
figerait la cible), au contraire du séquencement des phases éliminatoires, lui **visible** (« à venir »).

**Résorption attendue.** **E12US004** : à la livraison du forfait, traiter un archer forfait comme
**« série close par forfait »** dans `_serie_complete` (le forfait *termine* la participation de
l'archer au sens de la complétude, même série partielle). Retirer alors le marqueur `# DETTE-014`.

## Procédure — inscrire une dette

1. **Vérifier qu'elle est assumée** : si elle se corrige dans l'US sans déborder du périmètre, la corriger.
2. **Ajouter la ligne** au tableau « Dette ouverte » (ID `DETTE-nnn` incrémental) — **même commit** que l'introduction.
3. **Rédiger le détail** : constat, conséquence, pourquoi non corrigée, résorption attendue.
4. **Marquer le code** : commentaire à l'endroit exact du raccourci, renvoyant à l'ID (`# DETTE-001 : …`).
5. **Mentionner dans le corps de la PR**, et proposer l'US de résorption à l'utilisateur.
6. À la résorption : déplacer la ligne vers « Dette résorbée » avec l'US qui l'a soldée, et retirer les marqueurs du code.
