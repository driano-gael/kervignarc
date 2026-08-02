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
| [DETTE-026](#dette-026--une-source-de-phase-est-ancrée-par-ordre-pas-par-identité) | conception | mineur | `backend/application/phases.py` (`_remapper`), `backend/application/bareme_qualification.py` (`_decaler_dun_cran`), `backend/domain/phase.py` (`SourcePhase.ordre_source`) | Une source désigne sa phase amont par son **rang dans la séquence** (`ordre_source`) et non par son identité. Toute opération qui renumérote la séquence — réordonnancement, suppression, insertion de la qualification en tête — doit donc **réécrire** les références de toutes les phases qui citaient la phase déplacée | **Nul aujourd'hui** : les deux sites de remappage sont corrects et testés, et `PhaseSourceReferencee` interdit de supprimer une phase encore citée. Le coût est une **charge de vigilance** : chaque nouvel écrivain de la table `phase` doit penser à remapper, et un oubli fait pointer une source vers une phase arbitraire — silencieusement, puisque la séquence resterait valide | E05US001 (amorce du peuplement, ADR-0045 §3) ; **surface élargie par E05US010** — le remappage boucle désormais sur N sources au lieu d'une | **Non planifiée.** Facette de DETTE-015 **non** couverte par sa résorption (E05US010) : le modèle de source a été refondu, son **ancrage** ne l'a pas été. À traiter le jour où un 3ᵉ écrivain de la séquence apparaît (règle 16 : 2 sites aujourd'hui, on ne pose pas de pattern) — l'ancrage par `PhaseId` supprimerait tout remappage, au prix d'une migration des `config` |
| [DETTE-001](#dette-001--suppression-de-tournoi-non-cascadée) | technique | majeur | `backend/infrastructure/db/models.py`, `backend/migrations/versions/` | Aucune FK de la descendance de `tournoi` n'a d'`ON DELETE CASCADE`, ni de suppression applicative équivalente : enfants directs `categorie`, `archer`, `blason`, `gabarit_salle`, `phase`, `depart`, `scoreur`, `poste`, `entree_audit`, `remboursement` (→ `tournoi.id`), enfants indirects `score` (→ `archer.id`, **sauf** par `ArcherRepositorySQL.supprimer` — voir Résorption), `inscription` (→ `archer.id` **et** `depart.id`, **sauf** par `ArcherRepositorySQL.supprimer` et `DepartRepositorySQL.supprimer` — E02US009) et `serie` (→ `tournoi.id` **et** `archer.id`, **sauf** par `ArcherRepositorySQL.supprimer` — E04US002 ; sa table enfant `volee` → `serie.id` est en **`ON DELETE CASCADE`**, **hors** dette comme `placement`) et `forfait` (enfant de `tournoi.id` **et** `archer.id`, **sauf** par `ArcherRepositorySQL.supprimer`/`fusionner` — E04US015 ; sa FK `phase_id` est en **`ON DELETE CASCADE`**, **hors** dette) et liens latéraux `categorie.blason_id` (→ `blason.id`) et `archer.categorie_id` (→ `categorie.id`) | Supprimer un tournoi non vide lève une `IntegrityError` → **500** au lieu d'un 409 ou d'une cascade maîtrisée | E01US002 (cycle de vie du tournoi) ; aggravée à chaque nouvelle table/FK de la descendance (E01US004, E01US005, E01US006, E01US008, E01US009, E02US002, E02US004, E02US009, E10US003, E04US001, E10US005, E04US002, E04US015, **E08US005** — table `remboursement`, enfant direct de `tournoi.id` sans `ON DELETE`, comme `entree_audit`) ; **E02US010** n'ajoute ni table ni FK mais rend le 500 **systématique** pour tout tournoi non-brouillon (passer prêt exige désormais ≥ 1 départ, donc plus aucun tournoi `prêt`/`en_cours`/`terminé` n'est vide — cf. `test_supprimer_un_termine`, désormais en `xfail`) ; E02US003, E02US009, E04US002 puis E04US015 y ouvrent des **brèches partielles** (cascades applicatives `archer` → `score`, `archer`/`depart` → `inscription`, `archer` → `serie`, `archer` → `forfait`), qui ne valent que pour les chemins `ArcherRepositorySQL.supprimer` et `DepartRepositorySQL.supprimer` ; E02US005 (`ArcherRepositorySQL.fusionner`) **réassigne** cette même descendance (`archer` → `score`/`inscription`/`serie`/`forfait`, avec gestion de collision d'unicité) vers un autre archer — **3ᵉ chemin adapter conscient de la descendance d'`archer`**, à mettre à jour aussi si une table-enfant d'`archer` s'ajoute (n'aggrave pas la dette : n'ajoute ni table ni FK) | US dédiée — non planifiée. **⚠️ Deux pièges pour qui la résorbera.** (1) `archer` → `score` **n'est résolu que pour le chemin `ArcherRepositorySQL.supprimer`** (cascade applicative, E02US003) ; la branche **reste ouverte** pour toute suppression d'archer qui ne passe pas par cet adapter — dont la **cascade depuis `tournoi`**, précisément ce que cette dette vise. (2) **Ne pas poser `ON DELETE CASCADE` sur `score.archer_id`** : la confirmation vit **en amont**, dans `ServiceArchers.supprimer` (`ArcherEngage`), la purge dans l'adapter. Une cascade en base ne contourne pas la confirmation *sur ce chemin*, mais elle armerait une purge **silencieuse** sur **tout autre** chemin (cascade tournoi, import, script) — l'option écartée par [ADR-0016](adr/0016-supprimer-un-archer-engage-plutot-que-le-refuser.md) |
| [DETTE-006](#dette-006--cle_nom-nest-plus-chez-elle-dans-domainclubpy) | conception | mineur | `backend/domain/club.py` (`cle_nom`), `backend/domain/archer.py`, `backend/domain/doublons.py`, `backend/application/archers.py`, `backend/application/clubs.py` | `cle_nom` — le repli casse/accents des noms propres — vit dans `domain/club.py`, mais sert désormais **5** usages dont **3 hors du concept « club »** : `archer.cle_identite` (E02US002), le tri des archers (E02US003) et la détection de doublons `domain/doublons.py` (E02US005). Sa propre docstring avait posé le seuil : « si un 2ᵉ usage hors club apparaît, extraire dans un `domain/texte.py` en US dédiée » | La fonction est **juste** ; seul son domicile est faux. Un lecteur d'`archer.py` ou de `doublons.py` doit aller lire `club.py` pour comprendre comment se replient les noms d'archers, et le prochain usage hors club ira chercher la règle là où elle n'a plus de raison d'être | E02US002 (1ᵉʳ usage hors club) ; **seuil atteint** par E02US003 (2ᵉ) ; **3ᵉ usage hors club** par E02US005 (`domain/doublons.py`, détection de doublons) | US dédiée à créer (`refactor/…`) — déplacer dans `domain/texte.py`, 5 appelants, zéro changement de comportement |

| [DETTE-008](#dette-008--une-réponse-400-renvoie-lentrée-du-client-en-écho-non-borné) | technique | mineur | `backend/api/erreurs.py` (`_sur_erreur_validation`) | Une entrée rejetée par Pydantic revient **verbatim** au client : `details = jsonable_encoder(exc.errors())` embarque le champ `input` de chaque erreur, sans borne ni sur la taille d'une valeur, ni sur le nombre d'erreurs listées | **Amplification mesurée ×42,9** (50 Ko envoyés → 2,1 Mo reçus) sur un corps à 10 000 valeurs invalides. Le serveur travaille et répond ~43× le volume reçu, sur un réseau local le jour J où ~30 tablettes partagent la bande passante | E00US009 (patron de bout en bout, forme posée) ; **constatée** le 17/07/2026 à la revue d'E01US014 (axe adversarial), qui l'a mesurée sur `zones` (×42,9) **et** sur `ages` (×41,6) — le régime est **général à tous les DTO**, aucune US ne l'a introduit en propre | US dédiée (`fix/…`) — borner `input` dans `_sur_erreur_validation` (troncature de la valeur + plafond du nombre d'erreurs listées). ⚠️ **Ne pas retirer `details`** : le format `{code, message, details?}` est la règle 5, et [DETTE-007](#dette-007--la-confirmation-dune-suppression-darcher-est-aveugle) s'en sert (canal `details` désormais peuplé par E12US007, [ADR-0040](adr/0040-alerte-par-calcul-d-impact.md)) |
| [DETTE-007](#dette-007--la-confirmation-dune-suppression-darcher-est-aveugle) | conception | majeur | `backend/application/archers.py` (`ServiceArchers.supprimer`), `backend/application/departs.py` (`ServiceDeparts.supprimer`), `backend/api/v1/competition.py`, `backend/api/v1/departs.py`, `frontend/src/features/archers/api.ts`, `frontend/src/features/departs/api.ts` | La confirmation d'une suppression **destructrice-confirmable** ne **rappelle pas** au serveur le décompte que le signalement avait annoncé : `autoriser_suppression_engage=true` (archer engagé, `ArcherEngage`) **et** `autoriser_suppression_inscrits=true` (départ à inscriptions, `DepartAvecInscriptions`, E02US009) court-circuitent entièrement le constat, sans le revérifier | Entre le 409 et le rejeu, d'autres tablettes saisissent ou inscrivent (30 le jour J). Confirmer une suppression annoncée à « 1 flèche » (ou « 0 payée ») peut en détruire sept (ou effacer une inscription payée entre-temps) — **sans retour possible**. Or [ADR-0016](adr/0016-supprimer-un-archer-engage-plutot-que-le-refuser.md)/[ADR-0018](adr/0018-supprimer-un-depart-a-inscriptions-confirmable.md) font reposer la sûreté de ces cas sur ce message : « le message énumère ce qui sera détruit » plutôt que « confirmez pour supprimer ». Un message dont rien ne garantit la fraîcheur ne tient pas cette promesse | E02US003 (le chemin destructeur naît avec l'US ; la clause « le drapeau est cru sur parole » vient d'ADR-0015, raisonnée pour un protocole de **création** et reprise sans être rouverte pour une **destruction**) ; **aggravée par E02US009** (2ᵉ chemin destructeur-confirmable, `DepartAvecInscriptions`) | US dédiée — confirmation **contractuelle** : le client renvoie le décompte annoncé, le service re-signale s'il a changé. Exige de faire transiter le décompte par le champ `details` de la réponse d'erreur (`{code, message, details?}`, règle 5) — **plomberie désormais posée par E12US007** ([ADR-0040](adr/0040-alerte-par-calcul-d-impact.md)) : `ReplacementNonConfirme.details` peuple le canal et `_sur_erreur_application` le lit, le coût du correctif est donc réduit d'autant. Reste à faire : la confirmation **contractuelle** (renvoi du décompte annoncé + re-signalement) sur les chemins `archer`/`départ` |
| [DETTE-010](#dette-010--capacité-de-cible-plafonnée-à-4-en-dur) | technique | majeur | `backend/domain/gabarit_salle.py` (`CAPACITE_CIBLE_MAX`, `POSITIONS`) | Le gabarit **borne la capacité d'une cible à [1,4]** (`CAPACITE_CIBLE_MAX = len(POSITIONS)`, `POSITIONS = ("A","B","C","D")` en dur) alors que le **modèle** (`modele-de-donnees.md`, `CIBLE.capacite`) **et** le **référentiel** (§5, EF-4.3) la veulent **non bornée** — la FFTA décrit une configuration à **3 triples verticaux** (> 4 postes) | Impossible de configurer une cible de plus de 4 postes ; **divergence code ↔ modèle ↔ référentiel** : la connaissance du projet dit « non borné », le code refuse | E01US007 (gabarit de salle) ; **constatée le 18/07/2026** (entretien de conception) | **E01US019** — délester le plafond, positions au-delà de `D` (`E`, `F`…), le placement (E03) suit |
| [DETTE-011](#dette-011--lagrégat-mono-flèche-sappelle-score-pas-fleche) | conception | mineur | `backend/domain/score.py` (`Score`, `ScoreId`), `backend/domain/ports.py` (`ScoreRepository`), `backend/domain/erreurs.py` (`ScoreInvalide`) | L'agrégat mono-flèche s'appelle `Score`, mais le [glossaire](glossaire.md) réserve `Fleche` au **tir unique** et `score` au **total** de points | Au vrai scoring (E04/E05 : volées, cumul), le nom `Score` sera pris par le **mauvais** concept → renommage subi ou ambiguïté durable dans le domaine et l'API | E00US011 (walking skeleton) ; **constatée le 18/07/2026** (audit de revue complète de `main`) | **Révisée 19/07/2026 (E04US002)** : le vrai scoring modélise la flèche comme **valeur** dans `Volee` (agrégats `Serie`/`Volee`), sans renommer `Score` — qui **survit** comme modèle de lecture du classement de démo. Le nom-clash est désamorcé (le total s'appelle `cumul`). **Révisée 20/07/2026 (E06US001, correctif DETTE-013)** : les gardes d'engagement sont repointées sur `Serie` — `Score` n'a désormais **plus aucun lecteur**, seul le `saisir_score` mort (`POST /scores`, sans appelant produit) l'écrit encore. Sa suppression (endpoint + agrégat + table `score`) redevient l'objet propre de cette dette, sans dépendance de lecture, dans une US `fix/`/`refactor/` dédiée ; voir détail |
| [DETTE-012](#dette-012--lurl-du-qr-de-cible-est-lorigine-de-la-requête-admin) | technique | mineur | `backend/application/documents_salle.py` (`_url_rattachement`) | L'URL encodée dans le QR de cible est **absolue**, bâtie sur l'**origine de la requête admin** (`request.base_url`, passée par l'API) : il n'existe pas de base URL publique configurée côté serveur. Générer les étiquettes depuis `localhost` (console du serveur) produit donc des QR pointant sur `http://localhost:8000/?poste=…`, inutilisables depuis une tablette | Un QR généré depuis `localhost` renvoie la tablette **sur elle-même** : le « filet » de re-rattachement (scanner le QR pour revenir sur sa cible) ne fonctionne pas. **Sans effet dans le flux nominal** : le jour J, l'admin atteint le serveur par son **IP réseau** (les 30 tablettes aussi), donc `base_url` = l'IP LAN et le QR est correct | E09US008 (impression des QR) ; **choix tranché en réalisation** (règle 11/12 : pas de config réseau introduite en douce ici) | **À replanifier** — E11US001 (livrée le 26/07/2026) apporte l'*enabler* (nom public stable `kervignarc.local` annoncé en mDNS) mais **ne câble pas** la base URL : `_url_rattachement` encode toujours `request.base_url`. Reste à faire dans une US dédiée (base URL publique configurable, source unique des liens absolus). **Design** : encoder `kervignarc.local` suppose le mDNS résolu côté tablette (best-effort) → l'IP LAN reste le défaut sûr |
| [DETTE-016](#dette-016--montant-remboursé--tarif-courant-pas-somme-encaissée) | conception | mineur | `backend/domain/remboursement.py`, `backend/application/inscriptions.py`, `backend/application/departs.py` | Le `montant_centimes` d'un remboursement fige le **tarif courant du départ au moment de l'effacement**, or le modèle ne stocke **jamais** la somme réellement versée (seul le booléen `paye` de l'inscription). Si le tarif d'un départ est **édité après** qu'une inscription y soit payée, le remboursement ouvert peut différer de l'encaissé | Sur un **mouvement d'argent**, un montant remboursé **faux** est possible — arguablement pire qu'absent. **Nul dans le flux nominal** (le tarif ne bouge pas après paiement) ; suppose une édition de tarif entre paiement et effacement | E08US005 ([ADR-0057](adr/0057-registre-de-remboursements.md), choix « tarif au moment de l'effacement ») ; **constaté en revue adversariale le 29/07/2026** | US dédiée — stocker `montant_paye_centimes` sur l'inscription à l'encaissement (ou **geler** le tarif d'un départ dès qu'une inscription y est payée). Marqueur `# DETTE-016` sur les deux sites de construction |
| [DETTE-017](#dette-017--auteur_admin-dupliqué-sur-3-sites) | conception | mineur | `backend/application/paiements.py`, `backend/application/placement.py`, `backend/application/remboursements.py` (`_AUTEUR_ADMIN`) | La constante `_AUTEUR_ADMIN = "Administrateur"` (auteur des entrées d'audit d'un acte admin) est **dupliquée** sur 3 sites : paiements (E08US002), régénération de plan (E12US007), remboursements (E08US005). Le seuil « factoriser au 3ᵉ cas » (CLAUDE.md § Dette) est **atteint** | Faible : littéral stable ; un 4ᵉ producteur admin re-dupliquera, et changer le libellé se fait en 3 endroits | E08US002/E12US007 (2 sites) ; **3ᵉ site E08US005**, proposé en résorption dans [ADR-0057](adr/0057-registre-de-remboursements.md) | US dédiée `refactor/` — extraire une constante partagée (`application/`), 3 appelants, zéro changement de comportement. Marqueur `# DETTE-017` sur les 3 sites |
| [DETTE-018](#dette-018--la-suppression-darcher-perd-les-remboursements) | conception | majeur | `backend/application/archers.py` (`_signaler_engagement`), `backend/infrastructure/db/repositories.py` (`ArcherRepositorySQL.supprimer`) | La suppression d'une **fiche archer** purge ses inscriptions en cascade **sans ouvrir de remboursement** — **3ᵉ chemin** d'effacement d'une inscription **payée**, hors des **deux** déclencheurs d'E08US005 (désinscription, suppression de départ). Le signalement `ArcherEngage` **alerte** (« dont P payée(s) : sommes à rembourser ») mais **aucune création automatique** de poste sur ce chemin | Une somme encaissée peut être effacée **sans poste au registre** (perte d'argent) — **atténué** par l'avertissement chiffré à la confirmation. Chemin **moins courant** que la désinscription (couverte). La **fusion** de doublons, elle, préserve `paye` (pas de perte) | E08US005 (périmètre borné aux 2 déclencheurs du CA) ; **arbitré avec le commanditaire le 29/07/2026** — différer plutôt qu'étendre la cascade **sensible** de l'archer (scores/séries/forfaits, ADR-0016) | US de suite — `ArcherRepository.supprimer_avec_remboursements` + motif `ARCHER_SUPPRIME`, comme le départ (`DepartRepository.supprimer_avec_remboursements`). Marqueur `# DETTE-018` sur `_signaler_engagement` |
| [DETTE-019](#dette-019--serviceroutage-jumeau-de-servicepilotagetour) | conception | mineur | `backend/application/routage.py`, `backend/application/pilotage_tour.py` | `ServiceRoutage` (E04US018) reprend de `ServicePilotageTour` (E12US002) trois éléments : `_sources_en_attente` (**corps identique**), la lecture « archer → pose du plan de duels » (`_poses_par_archer` / `_cibles_par_archer`, à la position près) et surtout la **garde tour-1** — « ne jamais annoncer la cible d'un match de tour ≥ 2, la pose persistée est celle du tour 1 » — écrite dans **deux formulations différentes** | Les deux premiers sont des dérivations sans enjeu. La **garde tour-1**, elle, est un invariant de sûreté physique : une cible périmée envoie un archer sur la mauvaise butte. Le jour où **E05US010** livrera le placement intégral 1→N, il faudra la lever **aux deux endroits** ; en rater une ne casse rien de visible côté serveur — ça affiche seulement une mauvaise cible. ⚠️ La parité s'arrête là : le routage porte **en plus** l'alerte « duel non côte à côte » (`duels_separes`) que le feu vert, lui, **ne porte pas** — cf. DETTE-021, qui est le vrai défaut | E04US018 (2ᵉ occurrence ; la 1ʳᵉ est E12US002) | ⚠️ **Les deux déclencheurs annoncés sont passés sans 3ᵉ site** (constat du 02/08/2026, remarque de revue) : `E07US004` et `E07US008` ont **réemployé** `ServiceRoutage` au lieu de recopier sa lecture — c'est le bon choix, et il vaut d'être acté plutôt que de laisser le registre prédire un passé révolu. Le déclencheur restant est **E05US010** (levée de la garde tour-1), pas un canal de routage. Extraction à la **3ᵉ occurrence** si elle survient. Remède pressenti : une lecture publique `ServicePlacementDuels.poses_par_archer` + un `cible_du_match(match, poses)` qui **porte** la garde tour-1, ~40 lignes déplacées, zéro changement de comportement. **Point d'entrée pour E05US010** : c'est là que la garde se lève. Marqueurs `# DETTE-019` sur les deux sites |
| [DETTE-020](#dette-020--le-libellé-de-tour-a-deux-domiciles) | conception | mineur | `backend/domain/tableau.py` (`libelle_tour`), `frontend/src/features/saisie-duels/duel.ts` (`libelleTour`) | Le nom d'un tour de tableau (« quart de finale », « petite finale ») est calculé **deux fois**, avec le même raisonnement (distance à la finale, `place_en_jeu` prioritaire) et des **sorties différentes** : le domaine rend le **singulier** (« Quart de finale », pour *un* archer), le front le **pluriel** (« Quarts de finale », pour un *titre de section ») et suffixe la petite finale (« Petite finale (3ᵉ place) ») | Les deux se lisent **sur le même écran, à un tap d'intervalle** (liste des duels puis panneau de routage). Aucun des deux libellés n'est faux dans son contexte, mais la **règle** est dupliquée : la prochaine évolution du vocabulaire (barrage, repêchage) devra se faire en deux endroits, dans deux langages. [ADR-0006](adr/0006-vocabulaire-metier-francais.md) veut un domicile unique pour le vocabulaire métier | E04US018 (2ᵉ occurrence ; la 1ʳᵉ est E04US013) | US `refactor/` — un seul domicile, le **domaine** : exposer `libelle` sur le DTO de duel comme sur celui de routage, retirer `libelleTour`/`estPetiteFinale` du front (`grouperParTour` groupe déjà par libellé, il consommerait celui du serveur). Le singulier/pluriel se règle alors par un paramètre du domaine, pas par une seconde implémentation. Marqueurs `# DETTE-020` / `// DETTE-020` sur les deux sites |
| [DETTE-021](#dette-021--le-feu-vert-lance-un-duel-dont-les-duellistes-sont-séparés) | conception | **majeur** | `backend/application/pilotage_tour.py` (`_duel_a_venir`, `_blocage`), `frontend/src/features/feu-vert/` | Le feu vert juge un duel « prêt à lancer » dès que **chacun** des deux occupants a *une* cible (`cible_haut is not None and cible_bas is not None`), sans jamais vérifier que c'est **la même** ni qu'ils sont **côte à côte**. Il affiche alors « prêt · cibles 4 et 7 » et **lance** le tour. Le panneau de routage (E04US018) porte, lui, l'alerte dérivée du domaine (`duels_separes`) | Le plan de duels est **persisté** mais l'appariement est **recalculé** à chaque lecture (ADR-0023) : une correction de score suffit à les désaccorder. Les deux écrans se **contredisent** alors — la tablette de l'archer avertit, l'écran de l'organisateur dit « prêt » et fait partir le tour, trace d'audit `LANCEMENT` à l'appui. C'est le canal qui donne l'**ordre**, donc celui où l'erreur coûte le plus | E12US002 (le défaut y est né) ; **constaté** le 30/07/2026 à la revue d'E04US018 (axe adversarial), qui a fermé le trou côté routage et rendu la divergence visible | US `fix/` dédiée — `DuelAVenir` porte le signal `duels_separes` (déjà calculé par `ServicePlacementDuels`, aucun calcul neuf), `_blocage` le nomme, l'écran Feu vert l'affiche en ambre. **Ne pas** en faire un `pret_a_lancer=False` : `P-3`, l'appli montre et n'empêche pas — et E03US009 **accepte** un duel séparé quand les cibles sont trop petites. Marqueur `# DETTE-021` posé |
| [DETTE-022](#dette-022--forfaits-de-la-phase-de-qualification-résolus-sur-4-sites) | conception | mineur | `backend/application/classements.py`, `backend/application/completude.py` (×2), `backend/application/saisie.py` | « Résoudre la phase de qualification puis lire ses forfaits » est écrit à **quatre** endroits, sous trois formes (`list[Forfait]`, `set`, `frozenset`). `completude.py` avait posé le rendez-vous dans son propre commentaire : « 2ᵉ occurrence, on extraira au **3ᵉ cas**, pas avant » | Faible : le motif est stable. Mais le seuil que le projet s'était lui-même fixé **dans le code** est franchi, et un 5ᵉ producteur re-dupliquera par mimétisme. Jumelle de DETTE-006 et DETTE-017 | E04US018 (4ᵉ site, `ServiceSaisie._forfaits_qualif`) | US `refactor/` — une lecture partagée `forfaits_qualif(tournoi_id) -> frozenset[ArcherId]`, 4 appelants, zéro changement de comportement. Marqueurs `# DETTE-022` sur les 4 sites |
| [DETTE-024](#dette-024--routeur-maison-plutôt-quune-bibliothèque) | conception | mineur | `frontend/src/shared/navigation/routeur.ts`, `frontend/src/shared/navigation/useChemin.ts` | Le routage par rôle (E14US003, [ADR-0059](adr/0059-routage-par-role-dans-l-url-routeur-maison.md)) est assuré par ~110 lignes maison au lieu d'une bibliothèque : `history.pushState` + `popstate` + `useSyncExternalStore`, plus deux fonctions pures d'analyse et de construction de chemins. Motif double : `react-router-dom` ≥ 7.12.0 tire un `react-router` dans la plage vulnérable de `GHSA-qwww-vcr4-c8h2` (mode RSC, inatteignable ici mais l'audit doit rester vert — règle 11), et l'installation de la version corrigée `react-router@8.3.0` est bloquée sur le poste | Faible aujourd'hui : le besoin est de cinq mondes et deux segments, sans route imbriquée ni garde déclarative, et les décisions d'aiguillage sont **pures et testées** (24 tests). Ce qui manquera si le produit grossit : routes imbriquées, chargement différé par route, gardes déclaratives, `<Link>` avec préchargement. Le coût se paiera au **premier** de ces besoins, pas avant | E14US003 (ADR-0059) | Remplacer par `react-router@8.3.0` quand l'installation est possible. Le remplacement est **borné par construction** : `routeur.ts` est pur et `useChemin.ts` ne fait que l'abonnement — seuls ces deux fichiers et trois appels à `naviguer` (`App`, `ChangerDeRole`, `EspacePoste`) sont concernés. Marqueur : en-tête de `routeur.ts` |
| [DETTE-025](#dette-025--appliquer-un-format-remplace-la-séquence-de-phases-sans-transaction) | technique | mineur | `backend/application/formats.py` (`ServiceFormats.appliquer`) | La suppression des phases existantes et la création de celles du format passent par des **transactions séparées** (une session par appel de repository) : une panne entre les deux laisse le tournoi sans phase, et une lecture concurrente peut voir une séquence partielle | Faible : **quatre** gardes (phase engagée, forfait pendant, **duelliste posé**, retrait de la qualification) réduisent le cas à une séquence `à venir` **sans données attachées**, que l'organisateur reconstitue en réappliquant un format | E01US023 (relevé par la revue ; remède hors périmètre — il touche le **port** `PhaseRepository`) | Un `remplacer_sequence(tournoi_id, phases)` atomique sur l'adapter concret, patron `consigner_dans` ([ADR-0035](adr/0035-atomicite-acte-trace-session-partagee.md)). Marqueur `# DETTE-025` |
| [DETTE-028](#dette-028--le-catalogue-de-types-de-phase-est-livré-sans-consommateur) | conception | majeur | **`backend/application/saisie_duels.py` (`_decor` — le cœur du raccourci)**, `backend/domain/poule.py`, `big_shoot_off.py`, `barrage.py` (dont `ConfigurationBarrage`, qui décrit le format de saisie et n'a plus d'appelant depuis que `resoudre_barrage` ne fait que départager), `suisse.py`, `colline.py`, `politiques.py` (`ScoreAvecHandicap`, `TiebreakPoules`, `RoutingRepechage`) ; **sites d'affichage de l'écart** (E01US024) : `application/simulation_format.py`, `api/v1/formats.py`, `frontend/src/features/deroule/` | Les six moteurs et les trois politiques d'E05US015 n'ont **aucun appelant de production** : aucun service ne les instancie, aucune `config.policies` ne sait porter `nb_poules` / `nb_manches` / `portee_de_defi` / `restants`, et `domain/classement.py` calcule toujours son cumul sans passer par la famille `scoring` — donc `ScoreAvecHandicap` reste inerte. L'écran « Phases » propose pourtant les six types à la composition | La lettre d'[ADR-0045](adr/0045-sequence-de-phases-cycle-de-vie-typage-source.md) §2 est tenue (un moteur existe pour chaque type offert), son **intention** ne l'est qu'à moitié : l'organisateur peut composer une phase de poules dont le réglage n'est exprimable nulle part et que rien ne déroulera. Et un moteur sans consommateur n'est éprouvé que par ses propres tests — écrits le même jour, par le même agent | E05US015 ([ADR-0062](adr/0062-catalogue-de-types-de-phase.md)) — **périmètre assumé**, l'exécution relevant d'E01US024 ; relevé en revue comme devant être **tracé** et non seulement documenté à l'ADR | ⚠️ **E01US024 n'en a résorbé que la moitié** (01/08/2026, [ADR-0063](adr/0063-brouillon-de-format-invariant-a-l-application.md)) : la **composition** est livrée (les 9 types se composent, avec effectif et prélèvements), l'**exécution** non — aucun service ne lit encore `Phase.sources` pour peupler une phase, `ServiceSaisieDuels._decor` ensemençant chaque tableau avec *tous* les archers en lice. L'US **aggrave** donc le coût (on peut désormais composer un déroulé que le moteur ignorera) et le compense en **affichant l'écart** projeté/constaté, fixé par un test de non-régression. Reste : **US dédiée** du chantier moteur — faire consommer les sources au peuplement, porter les réglages en `config.policies`, rebrancher `classement.py` sur `PolitiquesPhase`. Marqueurs `# DETTE-028` : `politiques.py` (moteurs inertes) **et** `ServiceSaisieDuels._decor` (le peuplement qui ignore les sources) |
| [DETTE-029](#dette-029--lattribution-des-rangs-ex-æquo-est-écrite-trois-fois) | conception | mineur | `backend/domain/classement.py` (`_ranger`), `backend/domain/poule.py` (`classement_de_poule`, `_marquer_ex_aequo`), `backend/domain/suisse.py` (`classement_suisse`, `_propager_ex_aequo`) | La règle « rang partagé à clé égale, avec sauts (1-2-2-4) » est écrite **trois fois**, et la propagation du drapeau `ex_aequo` **deux fois** en copie quasi verbatim. Les trois sites **divergent déjà** : `classement._ranger` ne porte aucun drapeau `ex_aequo`, les deux nouveaux si | 3ᵉ occurrence réelle : le seuil que le § Dette de `CLAUDE.md` fixe pour proposer un remède structurel est franchi **sur preuve**, pas sur pronostic. Corriger la règle (ou la faire diverger davantage) demande trois modifications coordonnées, et un oubli produit un classement **cohérent et faux** | E05US015 — deux des trois sites sont introduits par cette US ; relevé en revue (axes C1 et C2) | **US `refactor/` dédiée + ADR** (règle 16 : jamais en douce dans l'US courante). Remède minimal : une fonction pure `attribuer_rangs(ordonnes, meme_rang)` du domaine (~15 lignes, aucune abstraction nouvelle — le comparateur `Tiebreak` injecté suffit), chaque appelant gardant son dataclass de sortie. Marqueur `# DETTE-029` aux trois sites |
| [DETTE-031](#dette-031--le-suivi-du-déroulé-se-recalcule-intégralement-à-chaque-lecture) | technique | mineur | `backend/application/suivi_deroule.py` (`ServiceSuiviDeroule.pour_tournoi`), `backend/api/v1/suivi_deroule.py`, `frontend/src/features/suivi-deroule/hooks.ts`, **+ E07US008** : `backend/application/routage.py` (`ServiceRoutage._grille`), `backend/api/v1/routage.py` (les **deux** routes), `frontend/src/features/routage/hooks.ts` | `GET /api/v1/tournois/{id}/suivi-deroule` est **public, non authentifié, sans cache et sans plafond** : chaque appel compte les engagés (départs × inscriptions) puis, **par phase en tableau**, appelle `ServiceSaisieDuels.reconstruire` — qui recalcule tout le classement du tournoi, rebâtit l'arbre, rejoue les duels et applique les forfaits. Deux surfaces le pollent (écran de salle 10 s, pilotage 10 s) et n'importe qui sur le réseau local peut le poller aussi | Faible aujourd'hui : mono-club, quelques phases, un ou deux écrans, réseau local fermé — mesuré à ~34 ms pour le seul classement. Devient sensible avec beaucoup d'écrans, un déroulé à nombreuses phases, ou le jour où l'appli sortirait du LAN | E07US004 ([ADR-0064](adr/0064-ecran-de-salle-poste-type-et-pilotage-par-etat-lu.md)) — relevé en revue (axe adversarial) : la dette était **assumée en commentaire** de `hooks.ts` sans être tracée ici. **Élargie par E07US008** ([ADR-0065](adr/0065-rang-acquis-lu-sur-la-plage-et-issue-repechee.md)) : un **2ᵉ endpoint** au même régime (`/routage/{id}/affectations`) et **deux surfaces de polling** de plus (onglet public « Affectations », carte de suivi sur chaque téléphone) — relevé par trois axes de revue, qui ont aussi corrigé quatre textes citant `DETTE-008` à sa place | Mémoïser la projection par `(tournoi_id, version)` — la reconstruction est **pure** à donnée constante, donc invalidable sur l'événement post-commit `donnees_modifiees` qui existe déjà. Aucun cache n'est justifié avant qu'une mesure le réclame. Marqueur `# DETTE-031` sur `ServiceSuiviDeroule.pour_tournoi` |
| [DETTE-032](#dette-032--la-prise-de-controle-se-mesure-sur-lheure-murale-pas-sur-une-horloge-monotone) | technique | mineur | `backend/application/ecrans.py` (`ServiceEcrans._ecoulees`), `backend/domain/ecran.py` (`Consigne.expiree`, `reste_secondes`) | L'échéance d'une prise de contrôle est calculée comme un écart entre deux lectures de l'**heure murale** (port `Horloge`). Une resynchronisation NTP en cours de journée qui **recule** l'horloge repousse d'autant l'expiration ; côté écran, le décompte local atteint zéro, le sondage suivant lui rend la durée pleine, et l'affichage **oscille** entre vue imposée et déroulé | Faible : suppose une remise à l'heure en pleine journée sur un serveur local sans internet. Le pire cas est cosmétique (un écran qui hésite quelques secondes), jamais une perte de donnée | E07US004 ([ADR-0064](adr/0064-ecran-de-salle-poste-type-et-pilotage-par-etat-lu.md)) — relevé en 3ᵉ passe de revue, après qu'un correctif eut **prétendu** le traiter sans le faire | Mesurer la durée sur une référence **monotone** (`time.monotonic`) plutôt que sur l'heure murale, en ajoutant un port dédié à côté d'`Horloge` — ce dernier reste juste pour *dater* (audit, présence), pas pour *chronométrer*. Marqueur `# DETTE-032` sur `ServiceEcrans._ecoulees` |

## Dette résorbée

| ID | Nature | Portée | Soldée par |
|---|---|---|---|
| [DETTE-030](#dette-030--lunion-typephase-est-dupliquée-côté-front) | technique | `frontend/src/features/phases/api.ts`, `frontend/src/features/patrimoine/api.ts`, `features/phases/Phases.tsx`, `features/patrimoine/format.ts` | **E01US024** (01/08/2026) — l'écran « Composer un déroulé » est la **3ᵉ** feature portant l'union, exactement le déclencheur que la dette s'était fixé. Extraction dans `frontend/src/shared/phases/catalogue.ts` (`TypePhase`, `NatureSource`, `IssueTour`, `LIBELLE_TYPE`, `AIDE_TYPE`, `TYPES_SANS_CLASSEMENT`) ; les deux `api.ts` **ré-exportent** d'ici, aucun import existant ne casse. Deux domiciles au lieu de trois ; l'exigence d'exhaustivité des `Record` est **conservée** — elle protège l'autre moitié du risque (l'oubli d'un type à l'usage, que l'extraction ne voit pas). Marqueurs `# DETTE-030` retirés |
| [DETTE-015](#dette-015--modèle-de-source-de-phase-minimal-et-provisoire) | conception | `backend/domain/phase.py` (`SourcePhase`, `SequencePhases`), `domain/format_tournoi.py` (`ModelePhase.sources`), les `config` JSON de **`phase` et `format_tournoi`**, `api/v1/phases.py`, `api/v1/formats.py`, `features/phases/`, `features/patrimoine/` | **E05US010** (31/07/2026, [ADR-0061](adr/0061-routing-generique-et-placement-en-cascade.md)) : une phase porte `sources: tuple[SourcePhase, ...]` — **plusieurs** prélèvements, de natures `rangs` / `issue_de_tour` / `reste`, avec **plages relatives** (fin ouverte, « le reste ») pour qu'un format composé pour 120 archers tienne à 82. Le routing devient générique (`route(contexte)` → `HorsTableau` / `VersPlage`), la cascade de placement classe 1→N. Migration **0036 sur les deux tables** (l'ancienne forme `config.source` reste relisable) ; marqueurs `# DETTE-015` retirés des deux sites. ⚠️ Reste hors périmètre, **par décision d'US et non par oubli** : l'écran « Phases » n'édite qu'un prélèvement « par rangs » (les autres y sont en lecture seule) et aucun moteur ne **consomme** encore `issue_de_tour` / `reste` — c'est E01US024. ⚠️ Une facette de DETTE-015 **n'est pas** couverte par cette résorption et a été **re-déclarée** en [DETTE-026](#dette-026--une-source-de-phase-est-ancrée-par-ordre-pas-par-identité) : l'**ancrage par `ordre`** (et non par identité), que l'US a généralisé à N sources sans le changer |
| [DETTE-023](#dette-023--latelier-affiche-des-briques-encore-scopées-par-tournoi) | conception | `frontend/src/features/admin/CoquilleAdmin.tsx` (axe `atelier`) | **E01US023** (31/07/2026, [ADR-0060](adr/0060-briques-du-patrimoine-du-club-bibliotheque-copie-promotion.md)) : catégories et blasons sont devenus des **modèles de bibliothèque** (`tournoi_id` nullable, migration `0034`), et le déroulé une brique neuve — `FormatTournoi` (migration `0035`). `bareme` et `phases`, qui règlent **une** édition, sont parties au **pilotage** — même partage que `plan` (la copie) face à `gabarits` (le modèle). Les **six** destinations de l'atelier s'ouvrent désormais sans tournoi — `bareme`, `phases` et `simulation` ayant rejoint le **pilotage**, car elles règlent (ou rejouent) **une** édition (ADR-0060 §6) ; le message « Choisissez un tournoi ci-dessus » et son repli « cette brique dépend encore d'un tournoi » ont disparu. Le pré-chargement FFTA — le symptôme de fond, qui recréait les quatre blasons canoniques à chaque tournoi — alimente la bibliothèque **une fois pour toutes**, et son bouton par tournoi a été **retiré de l'écran** (l'endpoint subsiste pour le jeu d'essai E15US001, qui peuple un tournoi sans passer par l'atelier). L'invariant « aucune destination de l'atelier n'exige un tournoi » est **vérifié par un test** (`axes.test.ts` sur la table `BESOIN_TOURNOI`, sortie du composant pour être lisible). Marqueur `# DETTE-023` retiré. ⚠️ **Résorbée autrement que prévu** sur un point : la ligne annonçait de sortir *les quatre briques* du périmètre d'un tournoi ; pour les phases, c'était impossible sans désarmer l'invariant `SequencePhases` (ordres contigus 1..N) — cf. ADR-0060 §5. |
| [DETTE-014](#dette-014--la-complétude-ignore-le-forfait) | conception | `backend/application/completude.py` | **E04US015** (27/07/2026, [ADR-0050](adr/0050-forfait-abandon-et-disqualification.md)) : le forfait est livré (abandon/DSQ, agrégat `Forfait`). `_serie_complete` → `_serie_close(serie, nb_volees, est_forfait)` : un archer **forfait en qualification** a sa série **close par forfait** (le forfait *termine* sa participation malgré ses volées partielles préservées). La complétude lit les forfaits de la phase de qualif ; une cible portant un forfaitaire n'est plus « à finir » à jamais. Marqueur `# DETTE-014` retiré du code (remplacé par une note « résorbée »). |
| [DETTE-005](#dette-005--conversion-euroscentimes-sans-aucun-test) | technique | `frontend/src/features/competition/format.ts` | **E00US014** : runner `vitest` installé + script `npm test`, câblé à la CI bloquante (E00US003) ; `format.test.ts` couvre la conversion euros↔centimes (aller-retour, sens de complétion `padEnd`/`padStart`, rejets). Marqueur `# DETTE-005` retiré du code. |
| [DETTE-002](#dette-002--hauteur-de-blason-non-modélisée) | conception | `backend/domain/categorie.py`, `docs/modele-de-donnees.md` | **E03US001** ([ADR-0022](adr/0022-hauteur-de-centre-sur-la-categorie.md)) : la hauteur du centre de l'or vit sur `Categorie` (`hauteur_cm`, 130 par défaut, 110 pour les U11) ; le placement en fait une **contrainte de 1er rang** — une butte, une seule hauteur (test « U11 + adultes → séparés »). Migration `0020` (backfill 110 si `ages` contient U11). |
| DETTE-009 | conception | `backend/api/v1/categories.py` (`ModifierCategorieRequete`) | **E03US004** : le formulaire catégorie porte la hauteur du centre (UI de placement), donc `hauteur_cm` est rendue **obligatoire** au PUT (DTO + `ServiceCategories.modifier` en keyword-only) ; le PUT redevient **intégralement total** ([ADR-0020](adr/0020-blason-zones-vocabulaire-ferme-et-defaut-sur-ensemble.md)), l'entorse « champ partiel » disparaît. Test de non-régression HTTP **inversé** (omission → 400). |
| [DETTE-013](#dette-013--les-gardes-dengagement-lisent-un-score-que-plus-rien-nécrit) | conception | `backend/application/archers.py` (`_signaler_engagement`, `_signaler_changement_categorie`) | **E06US001** (même branche, 20/07/2026) : les deux gardes lisent désormais `SerieRepository.par_archer` — « a tiré » = **au moins une volée validée** (`Serie.nb_fleches_validees`), plus l'agrégat `Score` mort. Arbitrage « volée *validée* (pas toute volée saisie) » reversé dans `stories/E02-inscriptions.md` (règle 9). Tests dérivés du CA E02US003/E02US009 (service **et** API). Marqueur retiré. Reste ouvert sur son objet propre : la **suppression** de `Score`, désormais sans lecteur (DETTE-011). |
| [DETTE-003](#dette-003--config-de-phase-à-plat-au-lieu-de-configpolicies) | conception | `backend/infrastructure/db/repositories.py`, `backend/migrations/versions/0028_phase_config_policies.py`, `docs/modele-de-donnees.md`, `docs/adr/0004-*`/`0011-*` | **E05US003** ([ADR-0046](adr/0046-config-policies-politiques-nommees-parametrees.md)) : les politiques vivent sous `config.policies`, chacune `{"nom": …, …params}` (nom + paramètres) ; le grain de `validation` reste **hors** `policies` (ce n'est pas une politique de moteur). Migration de données `0028` (racine → `policies`, `mode` → `nom`) + relecture tolérante (`_lire_scoring`, filet pour sauvegarde antérieure). `modele-de-donnees.md` et ADR-0004 réconciliés. Tests : bascule d'écriture, relecture ancienne forme, migration. |
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

> **Note ajoutée par E01US023.** `categorie.tournoi_id` et `blason.tournoi_id` sont désormais
> **nullables** : `NULL` désigne un **modèle de bibliothèque**, qui n'appartient à aucun tournoi. La
> politique de suppression qui sera tranchée ici ne doit donc **jamais** emporter ces lignes — ni par
> un `ON DELETE CASCADE`, ni par un `DELETE … WHERE tournoi_id = ?` (qui, lui, les ignore par
> construction). Détruire le patrimoine du club en supprimant un tournoi serait le pire effet de bord
> imaginable de cette dette. La table `format_tournoi`, elle, n'a aucune FK vers `tournoi` et reste
> hors sujet (même régime que `club`).

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

> **✅ Résorbée par E05US003 (26/07/2026), [ADR-0046](adr/0046-config-policies-politiques-nommees-parametrees.md).**
> Les deux questions liées mais distinctes sont tranchées : (1) les politiques du moteur vivent sous
> **`config.policies`** (aligné sur le modèle cible ADR-0004, qui « gagne sa place » dès que six
> familles y logent) ; (2) une politique se désigne par **nom + paramètres** (`{"nom": "cumul",
> "volees": 20, "fleches": 3}`) — ni objet anonyme, ni preset fermé. Le grain de `validation`
> **n'est pas** une politique de moteur : il reste **hors** `policies` (ce qui tranche au passage une
> incohérence de `modele-de-donnees.md`). Migration de données `0028` (racine → `policies`,
> `mode` → `nom`) **et** relecture tolérante de l'ancienne forme (`repositories._lire_scoring`, filet
> pour une base restaurée d'une sauvegarde antérieure). `modele-de-donnees.md` et ADR-0004 réconciliés
> avec le code. Le narratif ci-dessous est conservé comme trace.

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
publique configurable** (variable d'env ou réglage) et la faire consommer par le service à la place
de `request.base_url`. L'amorcer en douce (un demi-réglage) serait le contournement local que la
règle de dette proscrit. `request.base_url` est le meilleur défaut **sans config**, et il est correct
dans le flux réel.

**Résorption — re-ciblée le 26/07/2026 (E11US001).** La colonne *Résorption* visait E11US001, sur
l'idée que « mise en réseau » y introduirait la base URL publique. **E11US001 est livrée sans le
faire** : elle apporte l'*enabler* — un **nom public stable `kervignarc.local`** annoncé en mDNS et
le binding `0.0.0.0` — mais ne touche pas `_url_rattachement`, qui encode toujours `request.base_url`.
La dette reste donc **ouverte**, à traiter dans une **US dédiée** (`fix`/`refactor`) : exposer une
base URL publique configurable (défaut sûr = l'**IP LAN**, pas `kervignarc.local` qui suppose le mDNS
résolu côté tablette — best-effort) et la faire consommer par le service. Marqueur `DETTE-012` posé
sur `_url_rattachement` dans `application/documents_salle.py`.

**E11US008 (27/07/2026) — parade rendue opérationnelle, dette toujours ouverte.** Cette US (1) fait
écouter le **lancement de dev** (`run_dev.py`) sur `0.0.0.0` comme la release, et (2) expose le QR
**à l'écran** (Admin → Postes de cible) en plus du PDF. Elle **n'introduit pas** la base URL
configurable : le nouvel endpoint `GET …/postes/{cible_index}/qr` réutilise `_url_rattachement`, donc
encode lui aussi `request.base_url` — c'est un **2ᵉ consommateur** de la dette (même marqueur
`DETTE-012`). La dette reste **ouverte** ; ce que change E11US008, c'est que la parade — « ouvrir
l'admin par l'IP LAN pour que le QR soit scannable » — est désormais **atteignable en dev** et
**documentée** (`docs/deploiement.md` §6). La résorption réelle (base URL publique configurable)
bénéficierait alors aux **deux** consommateurs d'un coup.

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

> **✅ Résorbée par E04US015 (27/07/2026), [ADR-0050](adr/0050-forfait-abandon-et-disqualification.md).**
> Le forfait est livré (agrégat `Forfait`, abandon/DSQ). `_serie_complete` est devenue
> `_serie_close(serie, nb_volees, est_forfait)` : un archer **forfait en qualification** est compté
> **clos** (sa participation est *terminée* par le forfait, malgré ses volées partielles préservées).
> `ServiceCompletude` lit les forfaits de la phase de qualif — une cible portant un forfaitaire n'est
> plus « à finir » à jamais. Marqueur `# DETTE-014` retiré ; une note « résorbée » le remplace dans
> `completude.py`. La résorption arrive **avec l'US du forfait elle-même**, comme prévu ci-dessous —
> sauf qu'E12US004 a été **absorbée** par E04US015 (ADR-0050), qui livre les deux contextes.

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

### DETTE-015 — modèle de source de phase minimal et provisoire

**Constat.** E05US001 rend la **séquence de phases** active et introduit, avec elle, le **peuplement
d'une phase par une autre** (« la phase d'élimination prend les 16 premiers de la qualification »).
Le modèle cible (ADR-0004, formalisé dans `moteur-placement-lucky-loser.md`) est riche : une phase
peut être alimentée par **plusieurs** sources (les **gagnants** *et* les **perdants** d'un tour), le
perdant d'un match est **routé en cascade** vers un sous-tableau de placement, et les plages de rangs
se **divisent récursivement** jusqu'au rang terminal. Tout cela est le cœur d'**E05US010** (jalon J3).

E05US001 n'en livre qu'une **amorce délibérément minimale** : **une seule** source par phase, de la
forme « rangs `[rang_debut..rang_fin]` de la phase d'ordre `ordre_source` » (`SourcePhase`), plus un
`effectif` facultatif par phase. Ce sous-ensemble suffit à (a) composer les séquences proches
(qualif → élimination directe / placement) et (b) rendre **décidables** les trois contrôles de
cohérence exigés par le CA — *source vide*, *rangs inexistants*, *effectif incompatible* — portés par
l'agrégat pur `SequencePhases`.

**Conséquence.** **Nulle tant qu'E05US010 n'est pas prise.** La source unique « par rangs » est un
**sous-cas valide** du modèle complet : une phase saisie aujourd'hui avec une source restera lisible.
Mais E05US010 devra **élargir** le modèle (sources multiples gagnants/perdants, routing, division
récursive), ce qui touchera `SourcePhase`/`SequencePhases`, le DTO/API de peuplement et l'écran
d'édition. C'est une dette de **conception assumée**, pas un bug : rien ne casse, un modèle
provisoire attend son remplaçant.

**Pourquoi assumée maintenant.** Deux options se présentaient à E05US001 : (1) ne poser **aucun**
contrôle de source et reporter les trois contrôles du CA à E05US010, ou (2) amorcer un modèle minimal
pour honorer le CA dès maintenant. L'**arbitrage du commanditaire (26/07/2026)** a retenu (2) — le CA
d'E05US001 promet ces contrôles, les livrer vides aurait été un CA périmé. Le modèle est **borné**
(une source, un intervalle de rangs, **pas** de routing ni de gagnants/perdants) précisément pour que
son retravail par E05US010 reste **peu coûteux**. Voir [ADR-0045](adr/0045-sequence-de-phases-cycle-de-vie-typage-source.md) §3.

> **Élargie par E01US023.** `SourcePhase` est désormais **sérialisée dans une seconde table** :
> `ModelePhase.source` (`domain/format_tournoi.py`) est écrite dans `format_tournoi.config` par
> `_config_format` et relue par `_vers_modele_phase`. Le type du domaine est **réutilisé**, pas
> dupliqué — mais la surface de remédiation grandit : E05US010 devra migrer **aussi** les `config`
> des formats déjà enregistrés, pas seulement celles des phases. Marqueur `# DETTE-015` posé sur
> les **deux** sites (`SourcePhase` et `ModelePhase.source`).

**Résorbée par E05US010** (31/07/2026, [ADR-0061](adr/0061-routing-generique-et-placement-en-cascade.md)).
`SourcePhase` porte une `nature` (`rangs` / `issue_de_tour` / `reste`), un `rang_fin` **facultatif**
(« et suivants ») et vit en **liste** sur `Phase.sources` comme sur `ModelePhase.sources`. Les
contrôles de séquence se sont élargis en conséquence : recoupement entre sources d'une même phase, et
somme des prélèvements **seulement quand ils sont tous dénombrables** — dès qu'un prélèvement est
relatif, le compte ne se ferme qu'à l'exécution (c'est la condition d'existence des plages relatives,
cf. ADR-0061 §5). La migration **0036** réécrit `config.source` → `config.sources` dans **`phase` et
`format_tournoi`** — la seconde table étant l'élargissement signalé ci-dessus, celle qu'il aurait été
facile d'oublier. Les deux marqueurs `# DETTE-015` sont retirés.

> **Ce qui reste ouvert n'est pas de la dette mais du périmètre déclaré** (ADR-0061, § Limites) :
> l'écran « Phases » n'édite qu'un prélèvement « par rangs » — une phase à composition avancée y est
> affichée **en lecture seule**, précisément pour qu'un formulaire mono-source ne l'écrase pas — et
> aucun moteur ne **consomme** encore les natures `issue_de_tour` / `reste`. Le modèle est livré ici
> parce que c'est lui qui bloquait, et parce que le livrer plus tard aurait imposé une **seconde**
> migration double table. La composition et le diagnostic sont E01US024.
>
> **Point levé le 01/08/2026 (E01US024, [ADR-0063](adr/0063-brouillon-de-format-invariant-a-l-application.md)).**
> La moitié « édition » de cette réserve est close : l'écran « Composer un déroulé » édite les
> **trois** natures et **plusieurs** prélèvements par phase — c'est exactement l'écran que le renvoi
> « éditable depuis l'écran de composition du déroulé » de `Phases.tsx` désignait. La moitié
> « consommation » reste ouverte et relève de [DETTE-028](#dette-028--le-catalogue-de-types-de-phase-est-livré-sans-consommateur) :
> aucun moteur ne lit encore `issue_de_tour` / `reste` pour peupler une phase.

### DETTE-016 — montant remboursé = tarif courant, pas somme encaissée

**Constat.** E08US005 fige, à l'ouverture d'un remboursement, `montant_centimes = depart.tarif_centimes`
— le **tarif du départ au moment de l'effacement** de l'inscription payée. Or le modèle de paiement
(E08US002) ne stocke **jamais la somme réellement versée** : le fait de paiement est un **simple
booléen** `paye` sur l'inscription (pas de montant, pas de date, pas de transaction). Il est donc
**structurellement impossible** de retrouver ce qui a été encaissé après coup.

**Conséquence.** Si le **tarif d'un départ est édité** (`ServiceDeparts.modifier`, sans garde vis-à-vis
des inscriptions déjà payées) **entre** le paiement et l'effacement, le remboursement ouvert porte le
**nouveau** tarif, pas la somme versée. Sur un mouvement d'argent, rendre un montant faux est
arguablement pire que ne rien tracer. **Nul dans le flux nominal** (un tarif n'est en général pas
retouché après que des archers ont payé) ; le risque suppose cette édition tardive.

**Pourquoi assumée maintenant.** Corriger à la racine suppose de **modéliser l'encaissement** — stocker
`montant_paye_centimes` sur l'inscription au marquage payé (E08US002), ou **geler** le tarif d'un départ
dès la première inscription payée. Les deux touchent le modèle de paiement et débordent le CA
d'E08US005 (qui ne fait qu'introduire le registre). ADR-0057 documente le mécanisme « tarif au moment
de l'effacement » ; cette dette en trace la **limite**.

**Résorption attendue.** US dédiée (modèle de paiement) : figer la somme encaissée. Marqueur
`# DETTE-016` posé sur les deux sites de construction (`ServiceInscriptions.desinscrire`,
`ServiceDeparts._remboursements_des_payees`).

### DETTE-017 — `_AUTEUR_ADMIN` dupliqué sur 3 sites

**Constat.** L'auteur des entrées d'audit d'un acte **administrateur** est la constante locale
`_AUTEUR_ADMIN = "Administrateur"`, désormais **dupliquée** sur **trois** sites applicatifs :
`application/paiements.py` (marquage de paiement, E08US002), `application/placement.py` (régénération
massive du plan, E12US007) et `application/remboursements.py` (traitement d'un remboursement,
E08US005). La règle du projet (« dupliquer une 2ᵉ fois et attendre le 3ᵉ cas ») place le **seuil de
factorisation au 3ᵉ cas** — atteint ici.

**Conséquence.** Faible : le littéral est stable et trivial. Mais un **4ᵉ** producteur d'audit admin
re-dupliquera par mimétisme, et un éventuel changement de libellé devra se faire en trois endroits
cohérents. C'est une dette de **conception** (un invariant — « l'identité de l'admin dans l'audit » —
qui n'a pas de domicile unique), jumelle de DETTE-006.

**Pourquoi assumée maintenant.** L'extraction d'une constante partagée est un **remède structurel** :
CLAUDE.md § Dette veut qu'il se traite en **US dédiée**, jamais en douce dans l'US courante. E08US005
franchit le seuil mais ne doit pas porter le refactor ; il le **signale** (ADR-0057 § Conséquences) et
le trace ici.

**Résorption attendue.** US `refactor/` — extraire `AUTEUR_ADMIN` dans un module partagé
(`application/`), 3 appelants, zéro changement de comportement. Marqueur `# DETTE-017` sur les 3 sites.

### DETTE-018 — la suppression d'archer perd les remboursements

**Constat.** E08US005 ouvre un remboursement quand une inscription **payée** disparaît par ses **deux**
déclencheurs de CA : désinscription (`ServiceInscriptions.desinscrire`) et suppression de départ
(`ServiceDeparts`). Mais une inscription payée peut aussi disparaître par un **troisième** chemin — la
suppression d'une **fiche archer** (`ArcherRepositorySQL.supprimer` purge les inscriptions en cascade,
DETTE-001) — qui, lui, **n'ouvre aucun remboursement**. Une somme encaissée peut donc être effacée sans
contrepartie, exactement ce que l'*afin-de* du CA vise à empêcher. *(La **fusion** de doublons,
E02US005, préserve `paye` : pas de perte.)*

**Conséquence.** Perte d'argent possible sur ce chemin, **atténuée** — le signalement `ArcherEngage`
(`_signaler_engagement`) **alerte** désormais l'admin (« … dont P payée(s) : sommes à rembourser,
E08US005 ») au moment de la confirmation, mais **aucun poste n'est créé** automatiquement. Le chemin est
**moins courant** que la désinscription (le geste usuel), qui est couverte.

**Pourquoi assumée maintenant.** Étendre le mécanisme au 3ᵉ chemin ajoute un déclencheur **hors du CA
écrit** d'E08US005 **et** modifie la cascade de suppression d'archer — un chemin **sensible**
(scores/séries/forfaits/placements, [ADR-0016](adr/0016-supprimer-un-archer-engage-plutot-que-le-refuser.md)).
**Arbitrage du commanditaire (29/07/2026)** : **différer** dans une US de suite plutôt que grossir
E08US005 et toucher cette cascade — en fermant le **silence** dès maintenant (avertissement + cette
dette). Constaté en **revue adversariale**.

**Résorption attendue.** US de suite — doter `ArcherRepository` d'un `supprimer_avec_remboursements` et
ajouter un motif `MotifRemboursement.ARCHER_SUPPRIME`, sur le patron exact du départ
(`DepartRepository.supprimer_avec_remboursements`). Marqueur `# DETTE-018` posé sur `_signaler_engagement`.

### DETTE-019 — `ServiceRoutage` jumeau de `ServicePilotageTour`

**Constat.** `ServiceRoutage` (E04US018) et `ServicePilotageTour` (E12US002) posent la même question
sous deux angles — le pilotage demande « ce duel est-il prêt ? », le routage « où va cet archer ? » —
et partagent donc trois éléments, dupliqués :

1. `_sources_en_attente(match)` — **corps rigoureusement identique** ;
2. la lecture « archer → pose du plan de duels » (`_poses_par_archer` / `_cibles_par_archer`) — le
   routage garde en plus la **position** (A..D), le pilotage ne compte que des cibles ;
3. la **garde tour-1** : « ne jamais annoncer la cible d'un match de tour ≥ 2 ». Écrite dans deux
   formulations différentes (`place = match.tour == 1` puis un ternaire, d'un côté ; un
   `if match.tour != 1: return None, CIBLE_A_VENIR` de l'autre).

**Conséquence.** Les deux premiers points sont des dérivations sans enjeu — les dupliquer une 2ᵉ fois
est la réponse que le projet prescrit. Le **troisième** est différent : c'est un invariant de sûreté
**physique**. Le plan de duels ne pose que le 1ᵉʳ tour ([ADR-0048](adr/0048-plan-de-duels.md)) ;
réutiliser cette pose au tour suivant enverrait un finaliste sur son ancienne butte. Le jour où
**E05US010** livrera le placement intégral 1→N, la garde devra être levée **aux deux endroits**, sous
deux formes : en rater une ne fait rien échouer, ça affiche seulement une mauvaise cible — et c'est le
canal de routage, celui qui parle à l'archer, qui la rendrait comme un ordre.

**Pourquoi assumée maintenant.** C'est la **2ᵉ** occurrence, et le projet place le seuil de
factorisation au 3ᵉ cas (« dupliquer une 2ᵉ fois et attendre le 3ᵉ » est une réponse valide) ; un
remède structurel se traite en US dédiée, jamais en douce dans l'US courante. Ce qui manquait — et que
cette ligne apporte — c'est la **traçabilité** : un commentaire de code n'est pas retrouvable depuis
l'autre bout, et rien ne reliait E05US010 à la garde qu'elle devra lever.

**Résorption attendue.** À la **3ᵉ** occurrence, attendue avec `E07US008` (appli publique) et
`E07US004` (écran de salle) — les canaux 3 et 4 du routage (`D-09`), qui liront la même projection.
Remède pressenti, sans pattern neuf : une lecture publique `ServicePlacementDuels.poses_par_archer`
et un `cible_du_match(match, poses)` qui **porte** la garde tour-1, ~40 lignes déplacées, deux
appelants, zéro changement de comportement. Marqueurs `# DETTE-019` sur les deux sites.

### DETTE-020 — le libellé de tour a deux domiciles

**Constat.** Le nom d'un tour de tableau est calculé **deux fois** : `libelle_tour` dans
`backend/domain/tableau.py` (E04US018) et `libelleTour` dans
`frontend/src/features/saisie-duels/duel.ts` (E04US013). Même raisonnement — on compte à rebours de la
finale, `place_en_jeu` prime — mais des **sorties différentes** :

| | domaine | front |
|---|---|---|
| 3ᵉ place | `Petite finale` | `Petite finale (3ᵉ place)` |
| avant-dernier tour | `Demi-finale` | `Demi-finales` |
| −2 | `Quart de finale` | `Quarts de finale` |

**Conséquence.** Les deux se lisent **sur le même écran, à un tap d'intervalle** : le scoreur voit la
liste des duels titrée « Quarts de finale », ouvre un duel, le valide, et le panneau de routage lui
répond « Quart de finale ». Aucun des deux n'est faux dans son contexte — l'un titre un groupe, l'autre
adresse un archer — mais la **règle** est dupliquée, et
[ADR-0006](adr/0006-vocabulaire-metier-francais.md) exige un domicile unique pour le vocabulaire
métier. La prochaine évolution (barrage E06US003, repêchage E05US016) devra se faire en deux endroits,
dans deux langages, sans que rien ne le signale.

**Pourquoi assumée maintenant.** Unifier suppose de faire porter le libellé par le DTO de duel et de
retirer `libelleTour` du front, ce qui touche `grouperParTour` et ses tests — un refactor qui déborde
d'E04US018 et relève d'une US dédiée. Aligner les chaînes « à la main » dans ce commit aurait rendu
l'incohérence **invisible** sans supprimer la duplication : pire, puisque plus rien ne la signalerait.

**Résorption attendue.** US `refactor/` — exposer `libelle` sur le DTO de duel comme sur celui de
routage, retirer `libelleTour`/`estPetiteFinale` du front (`grouperParTour` groupe déjà **par
libellé** : il consommerait simplement celui du serveur). Le singulier/pluriel devient alors un
paramètre du domaine, pas une seconde implémentation. Marqueurs `# DETTE-020` / `// DETTE-020` sur les
deux sites.

### DETTE-021 — le feu vert lance un duel dont les duellistes sont séparés

**Constat.** `ServicePilotageTour._duel_a_venir` calcule
`cible_attribuee = cible_haut is not None and cible_bas is not None`. Deux cibles **différentes**
satisfont cette condition : le duel ressort `pret_a_lancer`, `_blocage` rend `None`, et l'écran
affiche « prêt · cibles 4 et 7 » (`frontend/src/features/feu-vert/etat.ts` sait même mettre les deux
au pluriel). Le bouton part alors, avec sa trace d'audit `LANCEMENT` et son `LiveEvent`.

**Conséquence.** Le plan de duels est **persisté** ; l'appariement, lui, est **recalculé à chaque
lecture** (ADR-0023, ADR-0048 : « l'appariement n'est jamais persisté »). Une correction de score en
qualification (E04US013) suffit donc à désaccorder les deux. Depuis E04US018, la tablette de l'archer
**avertit** (« placement à revoir »), tandis que l'écran de l'organisateur dit « prêt » et **lance**.
Deux écrans qui se contredisent, et c'est le second qui donne l'ordre : les deux duellistes partent
sur deux buttes et se cherchent. Avant E04US018 les deux canaux étaient également muets — le défaut
existait, il ne se voyait pas.

**Pourquoi assumée maintenant.** Le défaut est **antérieur** à E04US018 et vit dans l'écran d'une
autre US (E12US002). Le corriger en douce dans l'US courante reviendrait à étendre son périmètre à la
surface d'une autre — ce que le projet interdit pour les remèdes structurels, et ce qu'on ne veut pas
faire à la sauvette sur le geste le plus engageant du jour J. E04US018 **ferme le trou sur son propre
canal** et inscrit celui-ci.

**Résorption attendue.** US `fix/` dédiée : `DuelAVenir` porte le signal `duels_separes` — **déjà
calculé** par `ServicePlacementDuels.plan_de_duels`, aucun calcul neuf —, `_blocage` le nomme, et
l'écran Feu vert l'affiche en **ambre** (DV-03). ⚠️ **Ne pas** en faire un `pret_a_lancer = False` :
`P-3` veut que l'appli montre sans empêcher, et E03US009 **accepte** délibérément un duel séparé
quand les cibles sont trop petites — bloquer le lancement transformerait un avertissement légitime en
impasse. Marqueur `# DETTE-021` posé sur `_duel_a_venir`.

### DETTE-022 — forfaits de la phase de qualification résolus sur 4 sites

**Constat.** « Résoudre la phase de qualification, puis lire ses forfaits » est écrit à **quatre**
endroits : `application/classements.py` (`_forfaits_qualif`, → `list[Forfait]`),
`application/completude.py` deux fois (`avancement_depart` et `_compter_cibles`, → `set[ArcherId]`),
et désormais `application/saisie.py` (`_forfaits_qualif`, → `frozenset[ArcherId]`, E04US018).

`completude.py` avait posé le rendez-vous **dans son propre commentaire** : « La résolution barème +
forfaits est **dupliquée** de `_compter_cibles` (2ᵉ occurrence, règle 12 : on extraira au **3ᵉ cas**,
pas avant). » Ce site est celui qui franchit le seuil.

**Conséquence.** Faible en soi — le motif est stable et les trois formes de retour sont anodines.
Mais le seuil que le projet s'est fixé est franchi, et un 5ᵉ producteur re-dupliquera par mimétisme.
Jumelle de DETTE-006 (`cle_nom`) et DETTE-017 (`_AUTEUR_ADMIN`), toutes deux inscrites au même titre.

**Pourquoi assumée maintenant.** L'extraction est un **remède structurel** : CLAUDE.md § Dette veut
qu'il se traite en US dédiée, jamais en douce dans l'US courante. E04US018 franchit le seuil, le
signale et le trace ici.

**Résorption attendue.** US `refactor/` — une lecture partagée
`forfaits_qualif(tournoi_id) -> frozenset[ArcherId]` dans `application/`, 4 appelants, zéro
changement de comportement. Retirer au passage la phrase « on extraira au 3ᵉ cas » de
`completude.py`, devenue fausse. Marqueurs `# DETTE-022` sur les 4 sites.

### DETTE-023 — l'atelier affiche des briques encore scopées par tournoi

**Constat.** E14US003 remplace le découpage temporel de l'appli admin (Préparation / Jour J) par
trois **axes d'activité** : atelier, pilotage, gestion. L'atelier annonce « fabriquer, **hors
tournoi** » — c'est le patrimoine du club, il vit d'année en année. Huit destinations y sont rangées,
mais **quatre ne tiennent pas la promesse** :

| Destination | Endpoint | Tient la promesse ? |
|---|---|---|
| Clubs | `/clubs` | ✅ réellement global |
| Gabarits (salles types) | `/gabarits` + `/tournois/{id}/gabarit` | ✅ patron modèle → instance (E01US007) |
| Catégories | `/tournois/{id}/categories` | ❌ scopé tournoi |
| Blasons | `/tournois/{id}/blasons` | ❌ scopé tournoi |
| Barème & validation | `/tournois/{id}/bareme-qualification` | ❌ scopé tournoi |
| Phases (format) | `/tournois/{id}/phases` | ❌ scopé tournoi |
| Jeu d'essai · Simulation | outils | ✅ (le jeu d'essai gère l'absence de tournoi) |

**Conséquence.** L'axe atelier affiche « Choisissez un tournoi ci-dessus » sur la moitié de ses
destinations — sans proposer de sélecteur, puisque par construction il n'en a pas. Le contournement
du jour consiste à entrer par le pilotage pour fixer le tournoi courant, puis à revenir dans
l'atelier : soit **exactement le mélange que le découpage supprime**. C'est une incohérence visible
par l'utilisateur, d'où la sévérité **majeur** — mais elle ne casse aucun cas d'usage existant : les
quatre écrans fonctionnent comme avant, seule leur place a changé.

**Pourquoi non corrigée dans cette US.** Libérer les briques est un changement de **modèle de
données** (bibliothèque globale + copie à l'assemblage, migrations Alembic, ADR sur la portée des
briques) qui pèse plus que le découpage lui-même. Le commanditaire a demandé de voir la structure
**vite** ; la livrer avant le modèle est un choix assumé, pas un oubli. Le préchargement FFTA
(`precharger_ffta`, E01US022) est d'ailleurs le symptôme de fond : il **recrée** les quatre blasons
canoniques à chaque tournoi, faute de patrimoine où les ranger.

**✅ Résorbée le 31/07/2026 par E01US023** ([ADR-0060](adr/0060-briques-du-patrimoine-du-club-bibliotheque-copie-promotion.md)).
La correction a suivi le plan ci-dessous pour les **catégories** et les **blasons** — bibliothèque
globale, copie à l'assemblage, promotion remontante, sur le patron de `gabarits`. Pour les **phases**
et le **barème**, non : le barème n'est pas une entité (il vit dans la `config` de la phase de
qualification) et l'invariant d'une phase est **collectif** (`SequencePhases` exige des ordres
contigus 1..N) — des phases de bibliothèque auraient exigé de **désarmer** ce garde-fou. La brique
réutilisable est donc le **format** (`FormatTournoi`, une séquence de modèles de phases), et les deux
écrans qui règlent une édition sont partis au pilotage. Le texte d'origine est conservé ci-dessous.

**Résorption attendue (texte d'origine).** Lot « atelier » (déjà cadré) : sortir catégories, blasons, barèmes et phases
du périmètre d'un tournoi, sur le patron **déjà éprouvé** de `gabarits`. Décidé avec le commanditaire
le 30/07/2026 : la brique est **copiée** à l'assemblage (le tournoi porte son propre matériau, donc
l'archive reste vraie), la modification est **locale** au tournoi, et une modification déclarée
**permanente remonte** dans la brique de l'atelier. Marqueur `# DETTE-023` en tête de
`CoquilleAdmin.tsx`.

### DETTE-026 — une source de phase est ancrée par `ordre`, pas par identité

**Nature** : conception · **Sévérité** : mineur · **Introduite par** : E05US001, **surface élargie
par E05US010**

`SourcePhase.ordre_source` désigne la phase amont par son **rang dans la séquence**. Comme les
ordres forment la suite contiguë 1..N (invariant `SequencePhases`), toute opération qui renumérote
la séquence invalide les références et oblige à les réécrire. Deux sites le font aujourd'hui, tous
deux corrects et couverts par des tests :

- `ServicePhases._remapper` — réordonnancement et suppression (avec recompactage) ;
- `ServiceBaremeQualification._decaler_dun_cran` — insertion de la qualification en tête.

**Pourquoi ce n'est pas un bug.** `PhaseSourceReferencee` (409) interdit de supprimer une phase
qu'une autre cite, et les deux remappages couvrent l'intégralité des sources d'une phase depuis
E05US010. Le `KeyError` théorique sur `ancien_vers_nouveau[…]` n'est pas atteignable : la table est
construite sur toutes les phases restantes, et le garde refuse en amont toute source orpheline.

**Ce que ça coûte.** Une charge de **vigilance permanente** : tout futur écrivain de la table `phase`
devra penser au remappage, et l'oublier ne casserait rien de visible — la séquence resterait
structurellement valide, avec des sources pointant la mauvaise phase. C'est le mode d'échec le plus
coûteux à diagnostiquer : silencieux et différé.

> **Facette de DETTE-015 non résorbée.** E05US010 a refondu le **modèle** de source (natures, plages
> relatives, liste) et soldé DETTE-015 à ce titre ; elle n'a **pas** touché à l'**ancrage**, qui
> faisait pourtant partie du raccourci d'origine (l'ancien `_remapper` portait le renvoi
> « les ancres de source sont des `ordre`, non des id — DETTE-015 »). Plutôt que de laisser cette
> facette disparaître avec la ligne soldée, elle est **re-déclarée ici** — c'est la règle du projet :
> une dette ne sort du registre que résorbée, jamais par effet de bord d'une renumérotation.

**Résorption attendue.** Non planifiée, et **c'est un choix** (règle 16) : la pression est de **2**
occurrences, pas 3. Le remède le jour venu — ancrer par `PhaseId` plutôt que par `ordre` — supprime
les deux remappages mais impose une migration des `config` JSON des **deux** tables (`phase` et
`format_tournoi`), et pose un problème neuf pour `FormatTournoi`, dont les `ModelePhase` n'ont
précisément **pas** d'identité (ADR-0060 §5) : un format de bibliothèque ne peut s'ancrer que sur
l'ordre. C'est cette asymétrie, plus que le coût, qui justifie d'attendre un vrai déclencheur.


### DETTE-024 — routeur maison plutôt qu'une bibliothèque

**Constat.** E14US003 donne une adresse à chaque monde (`/public`, `/scoreur`, `/cible`,
`/admin/<axe>/<destination>`). Le routage est écrit à la main, en ~110 lignes réparties sur deux
fichiers : `shared/navigation/routeur.ts` (**pur** — analyse et construction de chemins,
correspondance monde ↔ rôle) et `shared/navigation/useChemin.ts` (l'abonnement à `history`, via
`useSyncExternalStore`).

**Pourquoi pas une bibliothèque.** Le commanditaire avait tranché pour `react-router-dom`. Deux faits
ont refermé l'arbitrage le jour même :

1. **sécurité** — toutes les versions `≥ 7.12.0` dépendent d'un `react-router` dans la plage vulnérable
   de l'avis `GHSA-qwww-vcr4-c8h2` (contournement CSRF en mode RSC). Le trou n'est **pas atteignable**
   dans une SPA purement cliente servie en statique, mais la **règle 11** exige un `npm audit` vert ;
2. **la version corrigée n'a pas pu être installée** — `react-router@8.3.0` existe et convient
   (peer deps React ≥ 19.2.7, exactement ce que le projet a), mais `npm install` est bloqué par une
   règle de permission du poste. Déclarer la dépendance sans l'installer produirait une **dépendance
   fantôme**, que la règle 11 qualifie de bloquante.

**Conséquence.** Ce qui manque, et qui manquera au premier besoin réel : routes **imbriquées**,
**chargement différé** par route, **gardes déclaratives**, `<Link>` avec préchargement. Aucun de ces
besoins n'existe aujourd'hui — cinq mondes, deux segments d'admin, et des gardes déjà écrites en
fonctions pures testées (`mondeAServir`, `peutChangerDeRole`, `resoudreRole`).

**Pourquoi la sévérité est *mineure*.** Le code n'est ni faux ni fragile : les décisions sont pures et
couvertes par 24 tests, le comportement critique du jour J (conservation de `?poste=<code>` pour les
QR déjà imprimés) est prouvé par un test dédié. C'est une dette de **conception assumée**, pas un
raccourci d'implémentation.

**Résorption attendue.** Remplacer par `react-router@8.3.0` quand l'installation redevient possible.
Le remplacement est **borné par construction** : `routeur.ts` est pur et `useChemin.ts` ne fait que
l'abonnement — seuls ces deux fichiers et les appels à `naviguer` (`App`, `ChangerDeRole`,
`EspacePoste`, `CoquilleAdmin`) sont concernés. Ils vivent sous `shared/navigation/` et non sous
`app/` : une **feature ne doit pas importer le shell** (inversion relevée en revue). Le marqueur vit en tête de `routeur.ts`, avec l'historique complet de
l'arbitrage.

### DETTE-025 — appliquer un format remplace la séquence de phases **sans transaction**

**Constat.** `ServiceFormats.appliquer` (E01US023) supprime les phases du tournoi puis crée celles du
format. Chaque appel de `PhaseRepositorySQL` ouvre **sa propre session et son propre commit** : la
suppression et la recréation ne forment donc pas une unité de travail. Une panne entre les deux
boucles (disque plein, base verrouillée) laisse le tournoi **sans aucune phase**, sans rollback ; et
comme les lectures sont synchrones hors file (règle 7), un poste qui lit pendant l'opération peut
observer une séquence partielle, dont les ordres ne forment pas 1..N.

**Pourquoi c'est de la dette et pas un bloquant.** **Quatre** gardes rendent le cas très improbable
et sans perte irréparable : le remplacement est **refusé** dès qu'une phase est engagée, dès qu'un
forfait pend sur l'une d'elles, dès qu'un duelliste y est posé, et dès qu'il retirerait la
qualification.

*(La première rédaction n'en comptait que trois et justifiait la cotation « faible » par une prémisse
alors **fausse** — la garde ne couvrait pas les poses du plan de duels, qu'elle nommait pourtant. La
revue l'a démontré à l'exécution ; la quatrième garde a été ajoutée, et la cotation redevient vraie.)* Ce qui peut être perdu est donc une
séquence de phases `à venir` **sans données attachées**, que l'organisateur reconstitue en
réappliquant un format. Aucun score, aucun duel, aucun forfait n'est en jeu.

**Pourquoi elle est prise.** Le remède est une opération atomique **sur l'adapter concret** — un
`remplacer_sequence(tournoi_id, phases)` en une seule session, sur le patron `consigner_dans`
d'[ADR-0035](adr/0035-atomicite-acte-trace-session-partagee.md). C'est un ajout au **port** et à son
adapter, donc une modification qui dépasse le périmètre de cette US, pour un cas dont la fenêtre est
de quelques millisecondes et la perte reconstituable.

**Résorption attendue.** À la première US qui touche `PhaseRepository` — ou au premier incident.
Marqueur `# DETTE-025` posé sur la boucle de suppression de `ServiceFormats.appliquer`.


### ~~DETTE-027~~ — appariement suisse glouton — **résorbée le 01/08/2026, dans l'US qui l'avait inscrite**

*Inscrite puis résorbée le même jour : elle n'a jamais atteint `main`. On la conserve ici parce que
son histoire vaut plus que son existence.*

`suisse._apparier` composait une ronde en glouton : pour chaque participant, le premier adversaire
non déjà rencontré, sans jamais revenir sur ses pas. La dette assumait cet écart en estimant son
impact **faible** — « le cas suppose un effectif restreint et beaucoup de rondes ».

**Cette estimation était fausse, et la revue l'a mesurée.** Sur 500 tournois simulés par
configuration, déroulés ronde après ronde :

| effectif | rondes | tournois bloqués (glouton) |
|---|---|---|
| **16** | **5** *(le défaut `ConfigurationSuisse.nb_rondes`)* | **265/500 — 53 %** |
| 12 | 5 | 340/500 — 68 % |
| 8 | 4 | 241/500 — 48 % |
| 6 | 3 | 150/500 — 30 % |
| 24 | 5 | 140/500 — 28 % |

Le blocage tombait le plus souvent à la **dernière** ronde, quand chacun avait déjà tiré quatre fois.
Seize archers en cinq rondes, c'est le réglage **par défaut** sur un effectif de club ordinaire :
pas « un cas défavorable », le cas **nominal**. Le format était inutilisable.

**Ce qu'on en retient.** Une dette dont l'impact est estimé « à vue » est plus dangereuse qu'une
dette non écrite : elle **rassure**. L'US suivante (E01US024) aurait branché le moteur en lisant
« impact faible ». Une ligne d'impact qui n'a pas été mesurée devrait le dire.

**Résorption.** `_apparier_en_reculant` : essais successifs **avec retour arrière**, qui n'échoue
que si aucun appariement sans ré-affrontement n'existe réellement. Remesuré sur le même protocole,
les sept configurations ci-dessus **plus** les effectifs impairs (7, 9) : **0 blocage sur 500**
partout. Le coût est une recherche en profondeur sur quelques dizaines de sommets, calculée une fois
par ronde entre deux volées. Le remède « algorithme de graphe entier » que la dette jugeait
disproportionné tenait en vingt lignes.

### DETTE-028 — le catalogue de types de phase est livré **sans consommateur**

E05US015 livre six moteurs de domaine (`poule`, `big_shoot_off`, `barrage`, `suisse`, `colline`,
plus l'échauffement qui n'en a pas) et trois politiques (`RoutingRepechage`, `ScoreAvecHandicap`,
`TiebreakPoules`). **Aucun n'a d'appelant de production** : aucun service ne les instancie, aucune
`config.policies` ne sait porter leurs réglages (`nb_poules`, `nb_manches`, `portee_de_defi`,
`restants`, barème de poule), et `domain/classement.py` calcule son cumul sans passer par la famille
`scoring` — donc le handicap, bien que stocké, exposé et affiché, ne s'applique à aucun classement.

**Ce que cela coûte.** L'écran « Phases » propose les six types à la composition : la **lettre**
d'ADR-0045 §2 est tenue (« on n'offre pas un type qu'aucun moteur ne sait dérouler »), son
**intention** ne l'est qu'à moitié. Un organisateur peut composer une phase de poules que rien ne
déroulera, et dont le réglage n'est exprimable nulle part. Corollaire moins visible : un moteur sans
consommateur n'est éprouvé que par ses propres tests — écrits le même jour, par le même agent, ce que
la revue de cette US a précisément sanctionné (trois défauts de comportement, chacun protégé par une
fixture qui l'évitait).

**Pourquoi c'est assumé.** Le découpage du chantier moteur le prévoit : E05US010 livre le placement,
E05US015 le catalogue, **E01US024** la composition et l'exécution, E07US004 le suivi en direct.
Livrer les moteurs sans leur pilotage est le prix de ce découpage, pas un oubli — ADR-0062 le dit
dans sa section « Ce que cet ADR ne tranche pas ».

**Ce qu'E01US024 a fait — et pas fait (01/08/2026, [ADR-0063](adr/0063-brouillon-de-format-invariant-a-l-application.md)).**
L'US devait la résorber ; elle n'en a résorbé **que la moitié**, et a rendu l'autre **visible** au
lieu de la laisser tacite. La distinction vaut d'être posée, parce que c'est elle qui dit ce qui
reste :

- **Composition — fait.** Les neuf types sont désormais composables depuis un écran (« Composer un
  déroulé »), avec effectif et prélèvements des trois natures. La projection de déroulé
  (`domain/deroule.py`) calcule ce que chaque phase accueille et ce qu'elle produit.
- **Exécution — non fait, et c'est le cœur de la dette.** Aucun service ne lit encore
  `Phase.sources` pour peupler une phase : `ServiceSaisieDuels._decor` ensemence **chaque** tableau
  avec *tous* les archers en lice, quel que soit le prélèvement déclaré. Les réglages
  (`nb_poules`, `nb_manches`, `portee_de_defi`, `restants`) restent inexprimables en
  `config.policies`, et `classement.py` ne passe toujours pas par la famille `scoring`.

**Aggravation constatée, et son antidote.** L'US **augmente** le coût de cette dette : jusqu'ici
personne ne pouvait composer un déroulé que le moteur ignorerait ; désormais si, et l'organisateur
peut donc se fier à un schéma que l'exécution ne tiendra pas. Plutôt qu'un contournement local,
l'écart est **mesuré et affiché** : `ToursPhase` porte l'effectif **projeté** à côté de l'effectif
**constaté** (`ecart`), l'API l'expose et l'écran de simulation le signale en ambre. Un test de
non-régression **fixe** cet écart (`test_la_simulation_signale_l_ecart_quand_le_moteur_ignore_le_prelevement`)
: le jour où le moteur honorera les sources, il échouera — c'est le signal attendu pour le retirer.

**Où la compensation s'arrête — dit explicitement, parce que la revue a montré qu'elle promettait
plus qu'elle ne tient.** L'alerte se déclenche sur l'**effectif** et le **nombre de tours**, plus un
signal `joue` qui dit quand le moteur n'a **rien** joué du tout — le cas des six types d'E05US015,
qui n'ont aucun moteur d'exécution et affichaient sinon « — tours, — duels » comme des faits. Les
**duels** sont affichés (projetés et constatés) mais **hors du prédicat d'alerte** : le schéma
compte l'arbre, le moteur y ajoute la petite finale de `ProfondeurPodium`, si bien qu'un écart d'une
unité existe sur *toute* phase de tableau. L'y inclure — ce que faisait un premier jet — allumait
l'avertissement sur 100 % des simulations et noyait le signal dans son propre bruit. Mais tout cela vit **derrière le bouton « Simuler »** : l'écran de
composition porte donc, en permanence, une réserve dès qu'un bloc prélève (« le moteur ne lit pas
encore les prélèvements »). Sans elle, l'organisateur qui compose, voit le verdict vert et applique
— sans jamais simuler — repartait avec un tournoi qui ne se déroulerait pas comme dessiné.

**Résorption attendue.** **US dédiée du chantier moteur**, à cadrer : faire consommer `Phase.sources`
par le peuplement des phases (le point dur — il touche `ServiceSaisieDuels._decor`, donc le déroulé
réel du jour J), porter les réglages dans `config.policies`, et rebrancher `classement.py` sur
`PolitiquesPhase` pour que le handicap s'applique.
Marqueurs `# DETTE-028` : `politiques.py` (moteurs inertes) et `ServiceSaisieDuels._decor` (le
peuplement qui ignore les sources).

### DETTE-029 — l'attribution des rangs ex æquo est écrite **trois fois**

La règle « deux entrées de même clé partagent le rang, on repart à `index + 1` dès que la clé change »
(sauts 1-2-2-4) existe désormais en trois exemplaires : `classement._ranger` (E01US012),
`poule.classement_de_poule` et `suisse.classement_suisse` (E05US015). La propagation du drapeau
`ex_aequo` au **premier** d'un groupe existe, elle, en deux copies quasi verbatim
(`poule._marquer_ex_aequo`, `suisse._propager_ex_aequo` — dont la docstring renvoie explicitement à
sa jumelle).

**Ce que cela coûte.** Les trois sites **divergent déjà** : `classement._ranger` ne porte aucun
drapeau `ex_aequo`, les deux nouveaux si. Corriger la règle demande trois modifications coordonnées,
et un oubli produit un classement **cohérent et faux** — le défaut qui ne se voit pas.

**Pourquoi ce n'est pas corrigé ici.** Le § Dette de `CLAUDE.md` et la règle 16 de la revue sont
formels : un remède structurel se traite en **ADR + US dédiée**, jamais en douce dans l'US courante.
La 3ᵉ occurrence est le seuil qui autorise à le **proposer**, pas à le faire.

**Remède proposé.** Une fonction pure du domaine, sans abstraction nouvelle :

```python
def attribuer_rangs[T](ordonnes: Sequence[T], meme_rang: Callable[[T, T], bool]) -> tuple[tuple[int, bool], ...]
```

Chaque appelant fournit son prédicat d'égalité (le comparateur `Tiebreak` injecté suffit) et garde
son propre dataclass de sortie. ~15 lignes, trois appels réécrits, tests existants inchangés.

**Résorption attendue.** US `refactor/` dédiée. Marqueur `# DETTE-029` aux trois sites.

### DETTE-030 — l'union `TypePhase` est **dupliquée** côté front

`TypePhase` (9 valeurs depuis E05US015) est déclarée dans `features/phases/api.ts` **et** dans
`features/patrimoine/api.ts` — les formats de bibliothèque composent les mêmes types que les phases
d'un tournoi. Avec l'enum backend, cela fait **trois** domiciles pour une seule vérité.

**Ce que cela coûte, mesuré.** Le coût s'est manifesté dans l'US même qui assume la duplication :
`patrimoine/format.ts` décrivait une étape par un ternaire à repli (`… : 'Placement'`), donc les six
types ajoutés s'affichaient tous « Placement » dans les écrans Formats et Assemblage — et
`npm run typecheck` restait vert, un ternaire n'ayant pas à être exhaustif. Corrigé en
`Record<TypePhase, string>`, qui rend l'oubli d'un type **non compilable**.

**Pourquoi c'est assumé.** Deux occurrences ne justifient pas d'introduire un module partagé :
« dupliquer une 2ᵉ fois et attendre le 3ᵉ cas » est une réponse explicitement valide du § Dette.

**Résorbée le 01/08/2026 par E01US024**, exactement au déclencheur annoncé. L'écran « Composer un
déroulé » est la **3ᵉ** feature portant l'union — et la 3ᵉ à nommer les types. L'extraction a donc
eu lieu, sur preuve dans le code du jour et non sur une évolution supposée :
`frontend/src/shared/phases/catalogue.ts` porte désormais `TypePhase`, `NatureSource`, `IssueTour`,
`LIBELLE_TYPE`, `AIDE_TYPE` et `TYPES_SANS_CLASSEMENT`. Les deux `api.ts` **ré-exportent** d'ici
(aucun import existant ne casse), `Phases.tsx` et `patrimoine/format.ts` consomment les tables
partagées. Il reste **deux** domiciles pour la vérité — l'enum backend et ce module — au lieu de
trois, et les marqueurs `# DETTE-030` sont retirés.

La contrainte d'exhaustivité qui rendait la duplication tenable **est conservée** et n'est pas
devenue superflue : elle protège contre l'autre moitié du risque, l'oubli d'un type **à l'usage**
(un `Record` incomplet ne compile pas), là où l'extraction ne protège que contre la divergence des
**déclarations**.


## Procédure — inscrire une dette

1. **Vérifier qu'elle est assumée** : si elle se corrige dans l'US sans déborder du périmètre, la corriger.
2. **Ajouter la ligne** au tableau « Dette ouverte » (ID `DETTE-nnn` incrémental) — **même commit** que l'introduction.
3. **Rédiger le détail** : constat, conséquence, pourquoi non corrigée, résorption attendue.
4. **Marquer le code** : commentaire à l'endroit exact du raccourci, renvoyant à l'ID (`# DETTE-001 : …`).
5. **Mentionner dans le corps de la PR**, et proposer l'US de résorption à l'utilisateur.
6. À la résorption : déplacer la ligne vers « Dette résorbée » avec l'US qui l'a soldée, et retirer les marqueurs du code.

### DETTE-031 — le suivi du déroulé se recalcule **intégralement à chaque lecture**

`GET /api/v1/tournois/{id}/suivi-deroule` (E07US004) est une **lecture publique, non authentifiée,
sans cache et sans plafond**. Chaque appel :

1. compte les engagés — un parcours de tous les départs × toutes leurs inscriptions ;
2. projette le format (`domain.deroule.projeter`, pur et bon marché) ;
3. puis, **par phase en tableau**, appelle `ServiceSaisieDuels.reconstruire`, qui recalcule *tout*
   le classement du tournoi (tous les archers, toutes les séries), rebâtit l'arbre, rejoue les duels
   persistés et applique les forfaits.

Deux surfaces le pollent en continu — l'écran de salle et le suivi au pilotage, toutes deux à 10 s —
et, l'endpoint étant public par nécessité (un écran de salle n'a pas de session admin), n'importe
quel appareil du réseau local peut le poller aussi.

**Élargissement du 02/08/2026 — E07US008.** Le même régime vaut désormais pour un **second**
endpoint : `GET /api/v1/routage/{id}/affectations` appelle le **même** `ServiceSaisieDuels.
reconstruire` via `ServiceRoutage._grille`, public et non authentifié lui aussi, et **sans plafond**
(contrairement à `GET /routage/{id}`, borné à 64 identifiants — ce plafond-là bornait
l'amplification requête→réponse, régime de [DETTE-008](#dette-008--une-réponse-400-renvoie-lentrée-du-client-en-écho-non-borné), pas le coût de lecture ;
c'est cette confusion que la revue d'E07US008 a corrigée dans quatre textes).

Deux **surfaces de polling** s'ajoutent, dont une qui change la nature du risque : l'onglet public
« Affectations », et surtout la **carte de suivi sur le téléphone de chaque spectateur** — là où les
consommateurs précédents étaient en un ou deux exemplaires (des écrans d'organisation), celui-ci est
en autant d'exemplaires qu'il y a de gens dans la salle. Une garde `enabled` limite la casse (la
requête n'est montée que si l'on suit au moins un archer), mais elle ne change pas le régime.

⚠️ **Le filet de 20 s n'est pas le régime dominant** : `useRealtime` invalide **sans clé**
(`queryClient.invalidateQueries()`), donc **chaque écriture serveur** provoque un refetch sur
**chaque client monté**. En pointe de saisie, la fréquence réelle suit le rythme des validations,
pas l'intervalle de poll. Et le cache React Query étant **par navigateur**, aucune mutualisation
n'existe entre appareils : le coût serveur est d'une reconstruction **par appareil et par
invalidation**.

**Pourquoi c'est assumé et non corrigé dans l'US.** Le contexte est mono-club, local, quelques
phases, un ou deux écrans, réseau fermé ; la mesure disponible (~34 ms pour le seul classement)
ne justifie pas un cache. Ajouter une mémoïsation sans mesure serait de la sur-ingénierie — et un
cache est précisément le genre de mécanisme qui coûte cher en justesse (invalidation) pour un gain
non constaté.

**Ce qui la rendrait sensible** : beaucoup d'écrans, un déroulé à nombreuses phases en tableau, ou
une sortie du LAN. Le remède est **borné par construction** : la projection est **pure à donnée
constante**, donc mémoïsable par `(tournoi_id, version)` et invalidable sur l'événement post-commit
`donnees_modifiees` qui existe déjà (`bootstrap.composition._diffuser_apres_ecriture`). Aucun
nouveau pattern, aucune abstraction : un dictionnaire et un compteur de version.

Marqueur `# DETTE-031` posé sur `ServiceSuiviDeroule.pour_tournoi` et sur `ServiceRoutage._grille`
(`backend/application/routage.py`).

*Relevée en revue (axe adversarial) : la dette était **assumée en commentaire** dans
`frontend/src/features/suivi-deroule/hooks.ts` — donc réelle et connue — mais **pas tracée ici**,
ce que le § Dette de `CLAUDE.md` compte comme dette silencieuse. **E07US008 a rejoué le même geste
et s'est fait reprendre de la même façon** : la charge était assumée en commentaire à quatre
endroits (docstring de la route, `hooks.ts`, `VueSuivi.tsx`, ADR-0065), sous le mauvais numéro de
dette, et le registre n'était pas touché. Trois axes de revue l'ont relevé — le fait que le même
défaut se reproduise sur l'US suivante est en soi le meilleur argument pour la porte de revue.*

### DETTE-032 — la prise de contrôle se mesure sur l'heure murale, pas sur une horloge monotone

`ServiceEcrans._ecoulees` calcule la durée écoulée d'une prise de contrôle comme un écart entre deux
lectures du port `Horloge`, c'est-à-dire de l'**heure murale**. `Consigne.expiree` et
`reste_secondes` en dépendent.

Si l'horloge **recule** — une resynchronisation NTP en cours de journée — l'expiration est repoussée
d'autant. Côté écran, le décompte **local** atteint zéro et la vue imposée est abandonnée ; le
sondage suivant rend une durée pleine et l'écran se refige. L'affichage **oscille** jusqu'à ce que
l'heure rattrape son retard.

**Pourquoi ce n'est pas corrigé dans l'US.** Le cas suppose une remise à l'heure en pleine
compétition, sur un serveur local sans internet (le déploiement du jour J est hors ligne, ADR-0044).
Le pire effet est cosmétique : un écran qui hésite quelques secondes sur ce qu'il montre. Aucune
donnée n'est en jeu.

**Le remède, quand il se justifiera** : chronométrer sur `time.monotonic` via un port dédié, à côté
d'`Horloge`. La distinction est propre et vaut d'être nommée — **`Horloge` sert à *dater*** (une
trace d'audit, un heartbeat, tout ce qui doit rester lisible et comparable après coup) ; **une
référence monotone sert à *chronométrer*** (une durée, un délai). Les confondre est exactement ce
qui produit ce défaut, et le projet a d'autres endroits où la même distinction s'appliquerait
(présence, idempotence) — d'où une US dédiée plutôt qu'un correctif local.

*Relevée en 3ᵉ passe de revue, après qu'un correctif de 2ᵉ passe eut **prétendu** la traiter : un
plancher à zéro sur l'écart, dont la mesure a montré qu'il ne changeait strictement rien (le
plafond de `reste_secondes` normalisait déjà la sortie). Le plancher est conservé — il évite qu'un
appelant reçoive un temps négatif — mais sa docstring dit désormais ce qu'il fait, et pas ce qu'on
aurait voulu qu'il fasse.*