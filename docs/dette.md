# Registre de la dette

> Registre **obligatoire** de la dette **assumée** du projet : ce qu'on sait imparfait, qu'on a
> choisi de ne pas corriger tout de suite, et qu'on s'engage à résorber.
> Règle : une dette introduite ou aggravée par une US doit être **inscrite ici dans le même commit**
> que son introduction. Une dette non inscrite est une dette **silencieuse** — elle est remontée en
> **majeur** à la revue de PR (cf. [`../.claude/agents/revue-axe-c2.md`](../.claude/agents/revue-axe-c2.md), règles 14-15).
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
| [DETTE-075](#dette-075--une-pause-posée-le-jour-j-nest-relisible-nulle-part) | conception | mineur | `backend/domain/ports.py` (`ArretDeCirconstanceRepository`, marqueur `# DETTE-075`) ; `backend/api/v1/phases.py` (aucune route de lecture) ; `frontend/src/features/suivi-deroule/PilotageCreneau.tsx` (`PoserUnePause`, marqueur) | Un `ArretDeCirconstance` **posé** n'est exposé par aucune lecture : `GET …/arrets/en-attente` ne rend que des `FranchissementArret`, c'est-à-dire les arrêts qui ont **déjà coupé**. La seule confirmation est l'état transitoire `poser.isSuccess` de la mutation, perdu au changement d'onglet ou au rechargement | L'organisateur qui revient sur le pilotage ne peut plus savoir qu'une pause est armée, ni sur quel tour. S'il repose par précaution, il reçoit un 422 « deux arrêts sont posés après le même tour 4 » — message correct, mais qui devient la **seule** façon dont l'application lui dit qu'une pause existe. Asymétrie frappante : les arrêts **programmés**, eux, sont visibles à l'éditeur de déroulé. Classé mineur et non majeur parce qu'aucun cas n'est cassé — l'arrêt est bien posé et coupera — mais c'est un inconfort sur l'US dont le titre est « rendre la pause visible » | **E05US034** — relevé par quatre axes de revue (C2 en majeur, C1 et adversarial en mineur, A en suggestion), et **non mentionné** par ADR-0092, qui énumère pourtant soigneusement ce qui a été écarté (`retirer` sur le port, état `PROGRAMME`, champ JSON, durée serveur) : un lecteur de l'ADR en concluait l'inverse. La section *Ce qui a été écarté* de l'ADR a été complétée dans le même commit | Le port porte **déjà** `par_depart` : il n'y a ni pattern à introduire ni remède structurel. Deux voies. (a) **Ajouter les arrêts non franchis à une lecture existante** — `GET /departs/{id}/arrets/en-attente` ou le suivi du créneau — et les lister sous la ligne de phase (« Pause posée : après le tour 4 ») : ~40 lignes, pas de route neuve. (b) Les livrer avec l'**annulation**, qu'ADR-0092 renvoie déjà à une US si l'usage la réclame — auquel cas la lecture est de toute façon le préalable. ⚠️ **Ne pas réattribuer par pronostic** (cf. `DETTE-031`, `DETTE-074`) : aucune US du backlog ne rouvre ce chemin aujourd'hui, la ligne reste ouverte sans porteur |
| [DETTE-074](#dette-074--un-tableau-à-plusieurs-sources-nannonce-quun-tour-donc-aucune-pause-ny-tombe) | conception | **majeur** | `backend/domain/suivi_deroule.py` (`avancement_bloc`, repli `nb_tours = 1`, marqueur `# DETTE-074`) ; conséquence dans `backend/application/arrets_programmes.py` (`_avancement_connu`) | Une phase en **élimination directe** dont la tranche d'entrée est indéterminable — **plusieurs sources**, [ADR-0061](adr/0061-routing-generique-et-placement-en-cascade.md) — ne produit **aucun braquet** projeté, donc `avancement_bloc` retombe sur « **un** tour, aucun tour courant ». Or ce couple est exactement la signature de « je ne sais pas où en est cette phase », que `_avancement_connu` lit comme *ne pas couper*. Un arrêt programmé sur un tel tableau est donc **accepté à l'atelier et jamais déclenché** | C'est le mode de panne que l'US existe pour empêcher, atteint par une autre porte : l'organisateur programme sa pause repas, l'écran l'accepte, et le jour J la salle enchaîne. Aucun signal, ni à l'atelier ni en salle. Le repli lui-même est **sûr** (on ne coupe pas au mauvais moment, ce qui serait pire), mais il est **silencieux** — et c'est cela qui en fait un majeur plutôt qu'un mineur. Portée réelle : un déroulé où un tableau puise dans plusieurs phases amont, ce que le moteur autorise depuis E05US010 | **E05US032** a créé le repli et **nommé la limite en docstring**, en la déléguant nommément à E05US033 (« `E05US033` consommera ce champ : à reprendre là-bas, où le besoin le nommera »). E05US033 l'a bien consommé — et ne l'a **pas** reprise. Relevé par l'axe C2 de la revue de cette US, contre un état du registre qui n'en portait aucune trace : une dette déléguée d'une US à l'autre **en commentaire de code** n'est prise par personne, ce qui est précisément ce que le § *Dette* de `CLAUDE.md` interdit | Deux voies, à trancher sur preuve d'usage. (a) **Un lecteur d'avancement pour l'élimination directe** : `ServiceSaisieDuels` reconstruit déjà l'arbre et connaît `Tableau.nb_tours`, il suffirait de réaliser `LecteurAvancementDePhase` et de le brancher au composition root, comme les trois formats d'E05US032 — c'est le remède **borné et connu**, mais il paie une reconstruction de plus (`DETTE-031`). (b) **Refuser l'arrêt** sur un tableau à sources multiples, à l'atelier, comme on refuse déjà les types sans tour observable (ADR-0091 §8) : cohérent avec la doctrine « un refus explicite vaut mieux qu'un réglage inerte », mais le refus dépendrait du **nombre de sources**, donc d'un réglage voisin qu'on peut changer après coup — il faudrait revalider les arrêts à chaque édition des sources. ⚠️ Ne pas trancher par commodité : (a) rend la capacité complète, (b) la borne honnêtement. ~~À faire porter par `E05US034`, qui rouvre déjà le registre d'avancement pour la qualification~~ — ⚠️ **cette attribution est tombée à faux le 20/08/2026, et il faut dire pourquoi** : elle reposait entièrement sur la prémisse « `E05US034` rouvre le registre d'avancement », or le **cadrage a coupé le périmètre** de cette US et sorti le chantier moteur (qualification divisible en tours) vers `E05US035`. `E05US034` n'a donc branché **aucun** lecteur d'avancement, et n'était pas un point de passage. C'est **exactement** le défaut que `DETTE-031` porte déjà en toutes lettres — *« ne pas réattribuer par pronostic : c'est ce pronostic-là qui vient de tomber à faux »* — reproduit sur une autre ligne, cinq jours plus tard. Le remède reste entier. **Nouveau porteur naturel : `E05US035`**, qui rouvrira réellement le registre (un lecteur pour `QUALIFICATION`) et devra de toute façon rouvrir la table de refus par type. ⚠️ Mais l'inscrire ici ne suffit pas : c'est le **troisième** pronostic de porteur sur ce registre, et les deux précédents sont tombés. À traiter comme une indication, pas comme une affectation — la ligne reste ouverte tant que le code ne l'a pas fermée |
| [DETTE-073](#dette-073--la-pause-dun-tournoi-ne-gèle-toujours-rien) | conception | **majeur** | `backend/application/tournois.py` (`ServiceTournois.mettre_en_pause`, docstring et absence de garde), `backend/application/saisie.py` et `backend/application/saisie_duels.py` (aucune lecture de `StatutTournoi`), `backend/application/routage.py` | Mettre un **tournoi** en pause (`StatutTournoi.EN_PAUSE`, ADR-0026 §3) ne gèle **rien** : ni la saisie, ni la validation, ni le routage. Aucun de ces trois chemins ne lit le statut du tournoi. La docstring de `mettre_en_pause` **affirmait** « la saisie s'arrête jusqu'à `reprendre` » — promesse **retirée dans le commit de constat** (coût nul), mais la capacité reste absente et le **bouton de l'écran d'administration**, lui, continue de laisser croire le contraire | Un organisateur qui suspend son tournoi croit avoir arrêté la salle. Les archers continuent de tirer et les scoreurs de valider ; rien ne le signale, et le bouton a l'air d'avoir fonctionné (le statut change bien). C'est un **écart entre ce que l'application promet et ce qu'elle fait**, sur un geste d'exploitation du jour J | **Constatée au cadrage d'E05US033** (19/08/2026) en vérifiant le postulat inverse que la fiche de l'US portait. Le volet **phase** a été corrigé dans l'US ([ADR-0091](adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md) §6) parce qu'il en est le mécanisme même ; le volet **tournoi** est à une **autre maille** (ADR-0026 §3) et n'a ni sémantique « finir le tour en cours » ni geste de reprise partielle — l'arbitrage du commanditaire a explicitement borné l'US à la phase | Deux gestes, à trancher ensemble : (a) une garde `TournoiEnPause` sur les mêmes points d'écriture que `PhaseEnPause` — mais **coupant net**, y compris en plein tir, ce qui est la sémantique d'une suspension de compétition et non d'une pause de salle ; ~~(b) corriger la docstring et retirer la promesse~~ — **fait** dans le commit de constat, la docstring ne mentait plus au lecteur du code dès l'inscription de cette dette. Reste donc **(a) seul**. ⚠️ Ne pas laisser en l'état : l'**écran** continue de laisser croire à l'organisateur que sa salle est arrêtée, ce qui est le vrai coût. Marqueur `# DETTE-073` sur `ServiceTournois.mettre_en_pause` |
| [DETTE-072](#dette-072--la-ligne-dune-rencontre-a-deux-rendus) | conception | mineur | `frontend/src/shared/duels/LigneRencontre.tsx` (le point de vérité, poules + système suisse) et `frontend/src/features/tableaux/VueTableaux.tsx` (`LigneDuel`, les arbres de duels) | Une rencontre rédigée — deux noms, un score, l'état de validation — est rendue par **deux** composants, dans le **même onglet** public. Ils disent aujourd'hui la même chose ; rien ne les y oblige. Le premier écart visible sera un `LigneDuel` corrigé sans que `LigneRencontre` le soit, ou l'inverse — et le spectateur lira deux grammaires différentes en passant d'une poule à un arbre, dans la même vue | Nul à ce jour : les deux rendus sont alignés et la logique de lecture (`etatRencontre`, `scoreRencontre`, `gagnantAffiche`) est déjà **partagée** dans `shared/duels/rencontre.ts` — c'est la mise en forme et la feuille de style qui restent doubles. Devient réel dès qu'une US touche l'un des deux | **E05US031** ([ADR-0089](adr/0089-le-catalogue-de-vues-porte-des-phases-pas-des-arbres.md)) : l'US écrit `LigneRencontre` pour les trois formats sans arbre et **choisit de ne pas migrer** `LigneDuel` dessus. Dette **assumée et bornée à deux rendus**, inscrite dans le commit qui l'introduit | Migrer `LigneDuel` sur `LigneRencontre`, ce qui suppose de rallier les classes `tableaux__*` aux `encours__*` et de rejouer `tableaux.css` sur les deux surfaces (360 px et projection). Le geste est mécanique mais **hors périmètre d'une US de format** : il touche une vue livrée pour un gain nul sur le CA. Marqueurs `# DETTE-072` sur les deux composants |
| [DETTE-050](#dette-050--les-rendus-derreur-ad-hoc-ne-sont-pas-ralliés-à-texteerreur) | conception | mineur | `frontend/src/shared/ui/texteErreur.ts` (le point de vérité), et les **13 rendus non ralliés** — chacun porteur de son propre marqueur `DETTE-050` depuis le 08/08/2026 (13 marqueurs sur 8 fichiers) : `features/supervision/Supervision.tsx`, `features/competition/VueClassement.tsx`, `features/feu-vert/FeuVert.tsx`, `features/tournois/Tournois.tsx`, `features/placement/PlanCiblesPublic.tsx` (×2), `features/competition/PanneauBarrages.tsx` (×5), `features/phases/Phases.tsx`, `features/admin/ConnexionAdmin.tsx` — plus **deux copies verbatim** du narrowing dans `features/duels/Duels.tsx` et `features/placement/Placement.tsx` | Les rendus d'erreur **ad hoc contextuels** (« … injoignable — {message} ») affichent `erreur.message` **brut**. Seule une `ErreurApi` porte un message mappé à la frontière API (règle 5) ; toute autre erreur — au premier chef le `TypeError: Failed to fetch` d'une coupure réseau — s'affiche telle quelle. `texteErreur` existe depuis E16US003 et borne le cas, mais **n'a été appliqué qu'aux cinq rendus du périmètre de cette US** | **Réel mais bénin** : sur le LAN du jour J (pas d'internet, tablettes BYOD), une coupure fait lire à l'organisateur un message technique en anglais au lieu d'une phrase utile. Aucune donnée ne fuit — `Failed to fetch` ne dit rien du serveur —, c'est un défaut d'ergonomie sous panne, pas une fuite d'information sensible. *(Nuance ajoutée le 08/08/2026 : le chemin **succès** de `fetchJson` (`await reponse.json()` non gardé) peut aussi remonter un `SyntaxError` dont le message embarque, sur Chrome, un fragment du corps reçu — typiquement l'`index.html` servi par FastAPI. Le contenu reste celui de l'application, donc la sévérité ne bouge pas ; mais le raisonnement « aucune donnée ne fuit » ne portait que sur `Failed to fetch`.)* **Masqué en développement** : `localhost` ne coupe pas, donc le défaut ne se voit qu'en salle | **E00US013 / DETTE-004** avait explicitement **laissé** ces rendus hors du composant générique — le carve-out portait sur le **rendu**, pas sur le narrowing, et personne n'avait relevé que le second manquait aussi. Constatée et **partiellement résorbée** par E16US003 (5 rendus ralliés) ; le reste est inscrit ici plutôt que corrigé en douce dans une US front d'un autre sujet | US de dette dédiée — substitution **mécanique** (un import + un appel par site), plus le repli des **quatre** duplications du narrowing sur `texteErreur` — les deux helpers verbatim (`duels/Duels.tsx`, `placement/Placement.tsx`) **et** les deux encodages inline (`supervision/Supervision.tsx`, `supervision/PiloterEcrans.tsx`), que « les deux helpers dupliqués » laissait échapper. À faire d'un bloc : le faire au fil de l'eau reproduit exactement le piège d'E16US003 — un invariant appliqué à moitié est plus trompeur qu'un invariant absent, parce qu'il fait croire le chantier terminé |
| [DETTE-026](#dette-026--une-source-de-phase-est-ancrée-par-ordre-pas-par-identité) | conception | **majeur** | `backend/application/phases.py` (`_remapper`), `backend/application/bareme_qualification.py` (`_decaler_dun_cran`), `backend/domain/phase.py` (`SourcePhase.ordre_source`) | Une source désigne sa phase amont par son **rang dans la séquence** (`ordre_source`) et non par son identité. Toute opération qui renumérote la séquence — réordonnancement, suppression, insertion de la qualification en tête — doit donc **réécrire** les références de toutes les phases qui citaient la phase déplacée | **Nul aujourd'hui** : les quatre sites de remappage sont corrects et testés, et `PhaseSourceReferencee` interdit de supprimer une phase encore citée. Le coût est une **charge de vigilance** : chaque nouvel écrivain de la table `phase` doit penser à remapper, et un oubli fait pointer une source vers une phase arbitraire — silencieusement, puisque la séquence resterait valide. **Depuis ADR-0076, la conséquence est plus lourde** : le rang étant aussi la clé de jointure vers la définition, un rang mal remappé fait exécuter à un créneau le **barème d'une autre étape** | E05US001 (amorce du peuplement, ADR-0045 §3) ; **surface élargie par E05US010** — le remappage boucle désormais sur N sources au lieu d'une ; **aggravée par E01US025/ADR-0076** — le rang devient la **clé de jointure** définition ↔ avancement, et les écrivains passent de 2 à 4 | **[ADR-0078](adr/0078-la-sequence-s-ancre-sur-l-identite-de-l-etape.md) + E05US022** (décidés le 07/08/2026) — le seuil de la règle 16 est **atteint** (le registre s'était fixé rendez-vous au 3ᵉ écrivain ; il y en a 4, plus deux méthodes de port dont l'unique raison d'être est de contourner la contrainte). Remède **proposé** : FK `phase.etape_id → deroule_etape.id`, le rang restant sur la seule étape. Le contre-argument de `models.py` (« une FK dupliquerait l'information ») est sérieux et doit être écarté explicitement |
| [DETTE-001](#dette-001--suppression-de-tournoi-non-cascadée) | technique | majeur | `backend/infrastructure/db/models.py`, `backend/migrations/versions/` | Aucune FK de la descendance de `tournoi` n'a d'`ON DELETE CASCADE`, ni de suppression applicative équivalente : enfants directs `categorie`, `archer`, `blason`, `gabarit_salle`, **`deroule_etape`** (E01US025), `depart`, `scoreur`, `poste`, `entree_audit`, `remboursement` (→ `tournoi.id`) — **`phase` n'en est plus un** : elle pend au `depart` depuis ADR-0075, donc enfant **indirect**, à supprimer *avant* les départs — et **`franchissement_arret`** (E05US033) est un enfant indirect **de la phase**, donc à supprimer *avant* `phase`, elle-même avant `depart`, — et **`arret_de_circonstance`** (E05US034) porte **deux** FK sans `ON DELETE`, `depart_id` **et** `phase_id`, donc à supprimer *avant `phase` et avant `depart`*, enfants indirects `score` (→ `archer.id`, **sauf** par `ArcherRepositorySQL.supprimer` — voir Résorption), `inscription` (→ `archer.id` **et** `depart.id`, **sauf** par `ArcherRepositorySQL.supprimer` et `DepartRepositorySQL.supprimer` — E02US009) et `serie` (→ `tournoi.id` **et** `archer.id`, **sauf** par `ArcherRepositorySQL.supprimer` — E04US002 ; sa table enfant `volee` → `serie.id` est en **`ON DELETE CASCADE`**, **hors** dette comme `placement`) et `forfait` (enfant de `tournoi.id` **et** `archer.id`, **sauf** par `ArcherRepositorySQL.supprimer`/`fusionner` — E04US015 ; sa FK `phase_id` est en **`ON DELETE CASCADE`**, **hors** dette) et **`barrage`** (enfant direct de `tournoi.id`, plus un lien latéral `phase_id`) et **`barrage_tir`** (enfant de `barrage.id` **et** `archer.id`, **sauf** par `ArcherRepositorySQL.supprimer`/`fusionner` — E06US003) et liens latéraux `categorie.blason_id` (→ `blason.id`) et `archer.categorie_id` (→ `categorie.id`) | Supprimer un tournoi non vide lève une `IntegrityError` → **500** au lieu d'un 409 ou d'une cascade maîtrisée | E01US002 (cycle de vie du tournoi) ; aggravée à chaque nouvelle table/FK de la descendance (E01US004, E01US005, E01US006, E01US008, E01US009, E02US002, E02US004, E02US009, E10US003, E04US001, E10US005, E04US002, E04US015, **E08US005** — table `remboursement`, enfant direct de `tournoi.id` sans `ON DELETE`, comme `entree_audit` ; **E06US003** — deux tables de plus, `barrage` et `barrage_tir`, dont la seconde a **rejoué le piège de `forfait`** : FK *enforced* vers `archer.id` oubliée de la cascade applicative, donc archer indéracinable en 500 et fusion de doublons cassée, corrigé en revue) ; **E05US033** — table `franchissement_arret` de plus, enfant indirect **de la phase** (`ForeignKey("phase.id")` sans `ON DELETE`), donc un cran plus profond que tout ce que cette ligne énumérait : elle se supprime **avant** `phase`. ⚠️ L'US avait posé le marqueur et le mentionnait dans l'en-tête de sa migration, mais **n'avait pas élargi cette ligne** — deux gestes sur trois, alors que la section de détail écrit la procédure noir sur blanc. Relevé par l'axe C2 de la revue, et c'est exactement le manque qui ferait buter la résorption : qui écrira l'ordre de cascade le lira **ici**. ; **E05US034** — table `arret_de_circonstance` de plus, **double FK** `depart.id` + `phase.id` sans `ON DELETE` ; ⚠️ **le même manque reproduit** (marqueurs posés, ligne non élargie), relevé par l'axe C2 pour la deuxième US consécutive — le procédé, pas l'attention, est ce qui échoue ; **E01US025** — table `deroule_etape` de plus, enfant direct de `tournoi.id` sans `ON DELETE`, et `phase` **change de branche** (enfant du `depart`), ce qui déplace sa position dans l'ordre de cascade) ; **E02US010** n'ajoute ni table ni FK mais rend le 500 **systématique** pour tout tournoi non-brouillon (passer prêt exige désormais ≥ 1 départ, donc plus aucun tournoi `prêt`/`en_cours`/`terminé` n'est vide — cf. `test_supprimer_un_termine`, désormais en `xfail`) ; E02US003, E02US009, E04US002 puis E04US015 y ouvrent des **brèches partielles** (cascades applicatives `archer` → `score`, `archer`/`depart` → `inscription`, `archer` → `serie`, `archer` → `forfait`), qui ne valent que pour les chemins `ArcherRepositorySQL.supprimer` et `DepartRepositorySQL.supprimer` ; E02US005 (`ArcherRepositorySQL.fusionner`) **réassigne** cette même descendance (`archer` → `score`/`inscription`/`serie`/`forfait`, avec gestion de collision d'unicité) vers un autre archer — **3ᵉ chemin adapter conscient de la descendance d'`archer`**, à mettre à jour aussi si une table-enfant d'`archer` s'ajoute (n'aggrave pas la dette : n'ajoute ni table ni FK) | **[ADR-0077](adr/0077-supprimer-un-tournoi-signaler-puis-confirmer.md) + E01US026** (arbitré le 07/08/2026 : *« faire l'équivalent d'ADR-0016, faire confirmer »*) — on **signale** la descendance avec un décompte chiffré, l'admin **confirme**, puis on détruit en une transaction ; **aucun** `ON DELETE CASCADE` en base, la confirmation vivant dans le service. **⚠️ Deux pièges pour qui la résorbera.** (1) `archer` → `score` **n'est résolu que pour le chemin `ArcherRepositorySQL.supprimer`** (cascade applicative, E02US003) ; la branche **reste ouverte** pour toute suppression d'archer qui ne passe pas par cet adapter — dont la **cascade depuis `tournoi`**, précisément ce que cette dette vise. (2) **Ne pas poser `ON DELETE CASCADE` sur `score.archer_id`** : la confirmation vit **en amont**, dans `ServiceArchers.supprimer` (`ArcherEngage`), la purge dans l'adapter. Une cascade en base ne contourne pas la confirmation *sur ce chemin*, mais elle armerait une purge **silencieuse** sur **tout autre** chemin (cascade tournoi, import, script) — l'option écartée par [ADR-0016](adr/0016-supprimer-un-archer-engage-plutot-que-le-refuser.md) |
| [DETTE-006](#dette-006--cle_nom-nest-plus-chez-elle-dans-domainclubpy) | conception | mineur | `backend/domain/club.py` (`cle_nom`), `backend/domain/archer.py`, `backend/domain/doublons.py`, `backend/application/archers.py`, `backend/application/clubs.py` | `cle_nom` — le repli casse/accents des noms propres — vit dans `domain/club.py`, mais sert désormais **5** usages dont **3 hors du concept « club »** : `archer.cle_identite` (E02US002), le tri des archers (E02US003) et la détection de doublons `domain/doublons.py` (E02US005). Sa propre docstring avait posé le seuil : « si un 2ᵉ usage hors club apparaît, extraire dans un `domain/texte.py` en US dédiée » | La fonction est **juste** ; seul son domicile est faux. Un lecteur d'`archer.py` ou de `doublons.py` doit aller lire `club.py` pour comprendre comment se replient les noms d'archers, et le prochain usage hors club ira chercher la règle là où elle n'a plus de raison d'être | E02US002 (1ᵉʳ usage hors club) ; **seuil atteint** par E02US003 (2ᵉ) ; **3ᵉ usage hors club** par E02US005 (`domain/doublons.py`, détection de doublons) | US dédiée à créer (`refactor/…`) — déplacer dans `domain/texte.py`, 5 appelants, zéro changement de comportement |

| [DETTE-008](#dette-008--une-réponse-400-renvoie-lentrée-du-client-en-écho-non-borné) | technique | mineur | `backend/api/erreurs.py` (`_sur_erreur_validation`) | Une entrée rejetée par Pydantic revient **verbatim** au client : `details = jsonable_encoder(exc.errors())` embarque le champ `input` de chaque erreur, sans borne ni sur la taille d'une valeur, ni sur le nombre d'erreurs listées | **Amplification mesurée ×42,9** (50 Ko envoyés → 2,1 Mo reçus) sur un corps à 10 000 valeurs invalides. Le serveur travaille et répond ~43× le volume reçu, sur un réseau local le jour J où ~30 tablettes partagent la bande passante | E00US009 (patron de bout en bout, forme posée) ; **constatée** le 17/07/2026 à la revue d'E01US014 (axe adversarial), qui l'a mesurée sur `zones` (×42,9) **et** sur `ages` (×41,6) — le régime est **général à tous les DTO**, aucune US ne l'a introduit en propre | US dédiée (`fix/…`) — borner `input` dans `_sur_erreur_validation` (troncature de la valeur + plafond du nombre d'erreurs listées). ⚠️ **Ne pas retirer `details`** : le format `{code, message, details?}` est la règle 5, et [DETTE-007](#dette-007--la-confirmation-dune-suppression-darcher-est-aveugle) s'en sert (canal `details` désormais peuplé par E12US007, [ADR-0040](adr/0040-alerte-par-calcul-d-impact.md)) |
| [DETTE-007](#dette-007--la-confirmation-dune-suppression-darcher-est-aveugle) | conception | majeur | `backend/application/archers.py` (`ServiceArchers.supprimer`), `backend/application/departs.py` (`ServiceDeparts.supprimer`), `backend/api/v1/competition.py`, `backend/api/v1/departs.py`, `frontend/src/features/archers/api.ts`, `frontend/src/features/departs/api.ts` | La confirmation d'une suppression **destructrice-confirmable** ne **rappelle pas** au serveur le décompte que le signalement avait annoncé : `autoriser_suppression_engage=true` (archer engagé, `ArcherEngage`) **et** `autoriser_suppression_inscrits=true` (départ à inscriptions, `DepartAvecInscriptions`, E02US009) court-circuitent entièrement le constat, sans le revérifier | Entre le 409 et le rejeu, d'autres tablettes saisissent ou inscrivent (30 le jour J). Confirmer une suppression annoncée à « 1 flèche » (ou « 0 payée ») peut en détruire sept (ou effacer une inscription payée entre-temps) — **sans retour possible**. Or [ADR-0016](adr/0016-supprimer-un-archer-engage-plutot-que-le-refuser.md)/[ADR-0018](adr/0018-supprimer-un-depart-a-inscriptions-confirmable.md) font reposer la sûreté de ces cas sur ce message : « le message énumère ce qui sera détruit » plutôt que « confirmez pour supprimer ». Un message dont rien ne garantit la fraîcheur ne tient pas cette promesse | E02US003 (le chemin destructeur naît avec l'US ; la clause « le drapeau est cru sur parole » vient d'ADR-0015, raisonnée pour un protocole de **création** et reprise sans être rouverte pour une **destruction**) ; **aggravée par E02US009** (2ᵉ chemin destructeur-confirmable, `DepartAvecInscriptions`) | US dédiée — confirmation **contractuelle** : le client renvoie le décompte annoncé, le service re-signale s'il a changé. Exige de faire transiter le décompte par le champ `details` de la réponse d'erreur (`{code, message, details?}`, règle 5) — **plomberie désormais posée par E12US007** ([ADR-0040](adr/0040-alerte-par-calcul-d-impact.md)) : `ReplacementNonConfirme.details` peuple le canal et `_sur_erreur_application` le lit, le coût du correctif est donc réduit d'autant. Reste à faire : la confirmation **contractuelle** (renvoi du décompte annoncé + re-signalement) sur les chemins `archer`/`départ` |
| [DETTE-010](#dette-010--capacité-de-cible-plafonnée-à-4-en-dur) | technique | majeur | `backend/domain/gabarit_salle.py` (`CAPACITE_CIBLE_MAX`, `POSITIONS`) ; **côté front** : `frontend/src/features/placement/Placement.tsx` et `frontend/src/features/duels/Duels.tsx` (`POSITIONS = ['A','B','C','D']`), `frontend/src/features/gabarits/{Gabarits,PlanDeSalle}.tsx` (`PLAFONDS = [1,2,3,4]`) — *élargi par E16US001* | Le gabarit **borne la capacité d'une cible à [1,4]** (`CAPACITE_CIBLE_MAX = len(POSITIONS)`, `POSITIONS = ("A","B","C","D")` en dur) alors que le **modèle** (`modele-de-donnees.md`, `CIBLE.capacite`) **et** le **référentiel** (§5, EF-4.3) la veulent **non bornée** — la FFTA décrit une configuration à **3 triples verticaux** (> 4 postes) | Impossible de configurer une cible de plus de 4 postes ; **divergence code ↔ modèle ↔ référentiel** : la connaissance du projet dit « non borné », le code refuse | E01US007 (gabarit de salle) ; **constatée le 18/07/2026** (entretien de conception) | **E01US019** — délester le plafond, positions au-delà de `D` (`E`, `F`…), le placement (E03) suit |
| [DETTE-011](#dette-011--lagrégat-mono-flèche-sappelle-score-pas-fleche) | conception | mineur | `backend/domain/score.py` (`Score`, `ScoreId`), `backend/domain/ports.py` (`ScoreRepository`), `backend/domain/erreurs.py` (`ScoreInvalide`) | L'agrégat mono-flèche s'appelle `Score`, mais le [glossaire](glossaire.md) réserve `Fleche` au **tir unique** et `score` au **total** de points | Au vrai scoring (E04/E05 : volées, cumul), le nom `Score` sera pris par le **mauvais** concept → renommage subi ou ambiguïté durable dans le domaine et l'API | E00US011 (walking skeleton) ; **constatée le 18/07/2026** (audit de revue complète de `main`) | **Révisée 19/07/2026 (E04US002)** : le vrai scoring modélise la flèche comme **valeur** dans `Volee` (agrégats `Serie`/`Volee`), sans renommer `Score` — qui **survit** comme modèle de lecture du classement de démo. Le nom-clash est désamorcé (le total s'appelle `cumul`). **Révisée 20/07/2026 (E06US001, correctif DETTE-013)** : les gardes d'engagement sont repointées sur `Serie` — `Score` n'a désormais **plus aucun lecteur**, seul le `saisir_score` mort (`POST /scores`, sans appelant produit) l'écrit encore. Sa suppression (endpoint + agrégat + table `score`) redevient l'objet propre de cette dette, sans dépendance de lecture, dans une US `fix/`/`refactor/` dédiée ; voir détail |
| [DETTE-012](#dette-012--lurl-du-qr-de-cible-est-lorigine-de-la-requête-admin) | technique | mineur | `backend/application/documents_salle.py` (`_url_rattachement`) | L'URL encodée dans le QR de cible est **absolue**, bâtie sur l'**origine de la requête admin** (`request.base_url`, passée par l'API) : il n'existe pas de base URL publique configurée côté serveur. Générer les étiquettes depuis `localhost` (console du serveur) produit donc des QR pointant sur `http://localhost:8000/?poste=…`, inutilisables depuis une tablette | Un QR généré depuis `localhost` renvoie la tablette **sur elle-même** : le « filet » de re-rattachement (scanner le QR pour revenir sur sa cible) ne fonctionne pas. **Sans effet dans le flux nominal** : le jour J, l'admin atteint le serveur par son **IP réseau** (les 30 tablettes aussi), donc `base_url` = l'IP LAN et le QR est correct | E09US008 (impression des QR) ; **choix tranché en réalisation** (règle 11/12 : pas de config réseau introduite en douce ici) | **À replanifier** — E11US001 (livrée le 26/07/2026) apporte l'*enabler* (nom public stable `kervignarc.local` annoncé en mDNS) mais **ne câble pas** la base URL : `_url_rattachement` encode toujours `request.base_url`. Reste à faire dans une US dédiée (base URL publique configurable, source unique des liens absolus). **Design** : encoder `kervignarc.local` suppose le mDNS résolu côté tablette (best-effort) → l'IP LAN reste le défaut sûr |
| [DETTE-016](#dette-016--montant-remboursé--tarif-courant-pas-somme-encaissée) | conception | mineur | `backend/domain/remboursement.py`, `backend/application/inscriptions.py`, `backend/application/departs.py` | Le `montant_centimes` d'un remboursement fige le **tarif courant du départ au moment de l'effacement**, or le modèle ne stocke **jamais** la somme réellement versée (seul le booléen `paye` de l'inscription). Si le tarif d'un départ est **édité après** qu'une inscription y soit payée, le remboursement ouvert peut différer de l'encaissé | Sur un **mouvement d'argent**, un montant remboursé **faux** est possible — arguablement pire qu'absent. **Nul dans le flux nominal** (le tarif ne bouge pas après paiement) ; suppose une édition de tarif entre paiement et effacement | E08US005 ([ADR-0057](adr/0057-registre-de-remboursements.md), choix « tarif au moment de l'effacement ») ; **constaté en revue adversariale le 29/07/2026** | US dédiée — stocker `montant_paye_centimes` sur l'inscription à l'encaissement (ou **geler** le tarif d'un départ dès qu'une inscription y est payée). Marqueur `# DETTE-016` sur les deux sites de construction |
| [DETTE-017](#dette-017--auteur_admin-dupliqué-sur-3-sites) | conception | mineur | `backend/application/paiements.py`, `backend/application/placement.py`, `backend/application/remboursements.py` (`_AUTEUR_ADMIN`) | La constante `_AUTEUR_ADMIN = "Administrateur"` (auteur des entrées d'audit d'un acte admin) est **dupliquée** sur 3 sites : paiements (E08US002), régénération de plan (E12US007), remboursements (E08US005). Le seuil « factoriser au 3ᵉ cas » (CLAUDE.md § Dette) est **atteint** | Faible : littéral stable ; un 4ᵉ producteur admin re-dupliquera, et changer le libellé se fait en 3 endroits | E08US002/E12US007 (2 sites) ; **3ᵉ site E08US005**, proposé en résorption dans [ADR-0057](adr/0057-registre-de-remboursements.md) | US dédiée `refactor/` — extraire une constante partagée (`application/`), 3 appelants, zéro changement de comportement. Marqueur `# DETTE-017` sur les 3 sites |
| [DETTE-018](#dette-018--la-suppression-darcher-perd-les-remboursements) | conception | majeur | `backend/application/archers.py` (`_signaler_engagement`), `backend/infrastructure/db/repositories.py` (`ArcherRepositorySQL.supprimer`) | La suppression d'une **fiche archer** purge ses inscriptions en cascade **sans ouvrir de remboursement** — **3ᵉ chemin** d'effacement d'une inscription **payée**, hors des **deux** déclencheurs d'E08US005 (désinscription, suppression de départ). Le signalement `ArcherEngage` **alerte** (« dont P payée(s) : sommes à rembourser ») mais **aucune création automatique** de poste sur ce chemin | Une somme encaissée peut être effacée **sans poste au registre** (perte d'argent) — **atténué** par l'avertissement chiffré à la confirmation. Chemin **moins courant** que la désinscription (couverte). La **fusion** de doublons, elle, préserve `paye` (pas de perte) | E08US005 (périmètre borné aux 2 déclencheurs du CA) ; **arbitré avec le commanditaire le 29/07/2026** — différer plutôt qu'étendre la cascade **sensible** de l'archer (scores/séries/forfaits, ADR-0016) | **US de dette à créer** (aucune US ne la porte au 08/08/2026) — `ArcherRepository.supprimer_avec_remboursements` + motif `ARCHER_SUPPRIME`, comme le départ (`DepartRepository.supprimer_avec_remboursements`). Marqueur `# DETTE-018` sur `_signaler_engagement` |
| [DETTE-019](#dette-019--serviceroutage-jumeau-de-servicepilotagetour) | conception | mineur | `backend/application/routage.py`, `backend/application/pilotage_tour.py` | `ServiceRoutage` (E04US018) reprend de `ServicePilotageTour` (E12US002) trois éléments : `_sources_en_attente` (**corps identique**), la lecture « archer → pose du plan de duels » (`_poses_par_archer` / `_cibles_par_archer`, à la position près) et surtout la **garde tour-1** — « ne jamais annoncer la cible d'un match de tour ≥ 2, la pose persistée est celle du tour 1 » — écrite dans **deux formulations différentes** | Les deux premiers sont des dérivations sans enjeu. La **garde tour-1**, elle, est un invariant de sûreté physique : une cible périmée envoie un archer sur la mauvaise butte. Le jour où **E05US010** livrera le placement intégral 1→N, il faudra la lever **aux deux endroits** ; en rater une ne casse rien de visible côté serveur — ça affiche seulement une mauvaise cible. ⚠️ La parité s'arrête là : le routage porte **en plus** l'alerte « duel non côte à côte » (`duels_separes`) que le feu vert, lui, **ne porte pas** — cf. DETTE-021, qui est le vrai défaut | E04US018 (2ᵉ occurrence ; la 1ʳᵉ est E12US002) | ⚠️ **Les deux déclencheurs annoncés sont passés sans 3ᵉ site** (constat du 02/08/2026, remarque de revue) : `E07US004` et `E07US008` ont **réemployé** `ServiceRoutage` au lieu de recopier sa lecture — c'est le bon choix, et il vaut d'être acté plutôt que de laisser le registre prédire un passé révolu. Le déclencheur restant est **E05US010** (levée de la garde tour-1), pas un canal de routage. Extraction à la **3ᵉ occurrence** si elle survient. Remède pressenti : une lecture publique `ServicePlacementDuels.poses_par_archer` + un `cible_du_match(match, poses)` qui **porte** la garde tour-1, ~40 lignes déplacées, zéro changement de comportement. **Point d'entrée pour E05US010** : c'est là que la garde se lève. Marqueurs `# DETTE-019` sur les deux sites |
| [DETTE-020](#dette-020--le-libellé-de-tour-a-deux-domiciles) | conception | mineur | `backend/domain/tableau.py` (`libelle_tour`), `frontend/src/features/saisie-duels/duel.ts` (`libelleTour`) — **toujours deux sites** : E07US005 a failli en ouvrir un troisième et l'a refermé en servant le libellé du domaine au DTO (`api/v1/tableaux.py`, `features/tableaux/presentation.ts`) | Le nom d'un tour de tableau (« quart de finale », « petite finale ») est calculé **deux fois**, avec le même raisonnement (distance à la finale, `place_en_jeu` prioritaire) et des **sorties différentes** : le domaine rend le **singulier** (« Quart de finale », pour *un* archer), le front le **pluriel** (« Quarts de finale », pour un *titre de section ») et suffixe la petite finale (« Petite finale (3ᵉ place) ») | Les deux se lisent **sur le même écran, à un tap d'intervalle** (liste des duels puis panneau de routage). ⚠️ **Cette phrase était fausse, et E07US005 l'a prouvé le 04/08/2026** : jusque-là on lisait ici « aucun des deux libellés n'est faux dans son contexte ». Le domicile front (`saisie-duels/duel.ts`) ne connaît que `estPetiteFinale` : dès qu'une phase descend sous le podium (profondeur intégrale, E06US006), il nomme **« Finale »** le match de la 5ᵉ place, **« Demi-finales »** la branche 5-8, et `grouperParTour` **fusionne trois matchs sous un même titre** — sur l'écran du **scoreur**, celui qui donne le résultat. Le domaine a été corrigé (argument `plage`) ; ce domicile-là ne l'est pas. La duplication n'est donc plus stylistique, elle **produit un affichage faux** : la sévérité `mineur` de cette ligne est à rediscuter à la première US qui touche l'écran de saisie en duels, mais la **règle** est dupliquée : la prochaine évolution du vocabulaire (barrage, repêchage) devra se faire en deux endroits, dans deux langages. [ADR-0006](adr/0006-ubiquitous-language.md) veut un domicile unique pour le vocabulaire métier | E04US018 (2ᵉ occurrence ; la 1ʳᵉ est E04US013) | US `refactor/` — un seul domicile, le **domaine** : exposer `libelle` sur le DTO de duel comme sur celui de routage, retirer `libelleTour`/`estPetiteFinale` du front (`grouperParTour` groupe déjà par libellé, il consommerait celui du serveur). Le singulier/pluriel se règle alors par un paramètre du domaine, pas par une seconde implémentation. Marqueurs `# DETTE-020` / `// DETTE-020` sur les deux sites |
| [DETTE-021](#dette-021--le-feu-vert-lance-un-duel-dont-les-duellistes-sont-séparés) | conception | **majeur** | `backend/application/pilotage_tour.py` (`_duel_a_venir`, `_blocage`), `frontend/src/features/feu-vert/` | Le feu vert juge un duel « prêt à lancer » dès que **chacun** des deux occupants a *une* cible (`cible_haut is not None and cible_bas is not None`), sans jamais vérifier que c'est **la même** ni qu'ils sont **côte à côte**. Il affiche alors « prêt · cibles 4 et 7 » et **lance** le tour. Le panneau de routage (E04US018) porte, lui, l'alerte dérivée du domaine (`duels_separes`) | Le plan de duels est **persisté** mais l'appariement est **recalculé** à chaque lecture (ADR-0023) : une correction de score suffit à les désaccorder. Les deux écrans se **contredisent** alors — la tablette de l'archer avertit, l'écran de l'organisateur dit « prêt » et fait partir le tour, trace d'audit `LANCEMENT` à l'appui. C'est le canal qui donne l'**ordre**, donc celui où l'erreur coûte le plus | E12US002 (le défaut y est né) ; **constaté** le 30/07/2026 à la revue d'E04US018 (axe adversarial), qui a fermé le trou côté routage et rendu la divergence visible | US `fix/` dédiée — `DuelAVenir` porte le signal `duels_separes` (déjà calculé par `ServicePlacementDuels`, aucun calcul neuf), `_blocage` le nomme, l'écran Feu vert l'affiche en ambre. **Ne pas** en faire un `pret_a_lancer=False` : `P-3`, l'appli montre et n'empêche pas — et E03US009 **accepte** un duel séparé quand les cibles sont trop petites. Marqueur `# DETTE-021` posé |
| [DETTE-022](#dette-022--forfaits-de-la-phase-de-qualification-résolus-sur-4-sites) | conception | mineur | `backend/application/classements.py`, `backend/application/completude.py` (×2), `backend/application/saisie.py` | « Résoudre la phase de qualification puis lire ses forfaits » est écrit à **quatre** endroits, sous trois formes (`list[Forfait]`, `set`, `frozenset`). `completude.py` avait posé le rendez-vous dans son propre commentaire : « 2ᵉ occurrence, on extraira au **3ᵉ cas**, pas avant » | Faible : le motif est stable. Mais le seuil que le projet s'était lui-même fixé **dans le code** est franchi, et un 5ᵉ producteur re-dupliquera par mimétisme. Jumelle de DETTE-006 et DETTE-017 | E04US018 (4ᵉ site, `ServiceSaisie._forfaits_qualif`). ⚠️ **E05US035 : le 5ᵉ site lit les DEUX chemins, et la nuance compte pour la résorption.** `ServiceSaisie._volees_du_plus_lent` appelle `forfaits.par_phase(phase.id)` — le geste **juste**, celui vers lequel la résorption doit converger — **union** `_forfaits_qualif(tournoi_id)`, qui est le raccourci de cette dette. La seconde moitié n'est là que pour compenser `DETTE-047` (l'**écriture** range tous les forfaits de qualification sur la phase du premier créneau, donc `par_phase` seul en manquait la totalité ailleurs). ⚠️ **Une première rédaction de cette note, écrite dans le commit initial, affirmait « n'ajoute PAS de 5ᵉ site » : elle est devenue fausse au correctif de revue et a été reprise ici.** Ce qu'il faut retenir pour la résorption : la forme cible est **par phase**, mais elle n'est atteignable qu'une fois `DETTE-047` résorbée — les deux dettes doivent se traiter dans cet ordre | US `refactor/` — une lecture partagée `forfaits_qualif(tournoi_id) -> frozenset[ArcherId]`, 4 appelants, zéro changement de comportement. Marqueurs `# DETTE-022` sur les 4 sites |
| [DETTE-024](#dette-024--routeur-maison-plutôt-quune-bibliothèque) | conception | mineur | `frontend/src/shared/navigation/routeur.ts`, `frontend/src/shared/navigation/useChemin.ts` | Le routage par rôle (E14US003, [ADR-0059](adr/0059-routage-par-role-dans-l-url-routeur-maison.md)) est assuré par ~110 lignes maison au lieu d'une bibliothèque : `history.pushState` + `popstate` + `useSyncExternalStore`, plus deux fonctions pures d'analyse et de construction de chemins. Motif double : `react-router-dom` ≥ 7.12.0 tire un `react-router` dans la plage vulnérable de `GHSA-qwww-vcr4-c8h2` (mode RSC, inatteignable ici mais l'audit doit rester vert — règle 11), et l'installation de la version corrigée `react-router@8.3.0` est bloquée sur le poste | Faible aujourd'hui : le besoin est de cinq mondes et deux segments, sans route imbriquée ni garde déclarative, et les décisions d'aiguillage sont **pures et testées** (24 tests). Ce qui manquera si le produit grossit : routes imbriquées, chargement différé par route, gardes déclaratives, `<Link>` avec préchargement. Le coût se paiera au **premier** de ces besoins, pas avant | E14US003 (ADR-0059) | Remplacer par `react-router@8.3.0` quand l'installation est possible. Le remplacement est **borné par construction** : `routeur.ts` est pur et `useChemin.ts` ne fait que l'abonnement — seuls ces deux fichiers et trois appels à `naviguer` (`App`, `ChangerDeRole`, `EspacePoste`) sont concernés. Marqueur : en-tête de `routeur.ts` |
| [DETTE-025](#dette-025--appliquer-un-format-remplace-la-séquence-de-phases-sans-transaction) | technique | **majeur** | `backend/application/formats.py` (`ServiceFormats.appliquer`), `backend/application/phases.py` (`ServicePhases.reordonner`, `ServicePhases.supprimer`), `backend/application/departs.py` (`ServiceDeparts.creer`) | La suppression des phases existantes, la création de celles du format **et la recopie du minimum d'inscrits exigé sur le tournoi** (E05US021) passent par des **transactions séparées** (une session par appel de repository) : une panne entre elles laisse le tournoi sans phase, ou avec les phases du nouveau format et l'exigence de l'ancien | Faible sur les phases (quatre gardes les réduisent à une séquence `à venir` sans données attachées). **Plus seulement reconstituable depuis E05US021** : une exigence restée périmée est silencieuse, et peut aussi bien bloquer un démarrage légitime qu'en autoriser un que la règle du club interdisait. **Plus grave encore sur l'édition du déroulé** (E01US025) : le rang étant la clé de jointure, une phase non réalignée pointe l'étape voisine — le créneau exécute un **autre barème** sans qu'aucun écran ne le signale | E01US023 (relevé par la revue) ; **aggravée par E05US021** (3ᵉ écriture) ; **élargie par E01US025** à l'édition du déroulé (ADR-0076) puis, en 2ᵉ revue, à la **création d'un créneau** (`ServiceDeparts.creer` : `ajouter` le départ puis N `ajouter` de phase, N+1 transactions, un déroulé partiel qu'aucun geste ultérieur ne répare) — 3 sites de plus, et une conséquence **silencieuse** (mauvais barème exécuté) au lieu d'un « tournoi sans phase » visible, d'où le passage en **majeur** | Un `remplacer_sequence(tournoi_id, phases)` atomique sur l'adapter concret, patron `consigner_dans` ([ADR-0035](adr/0035-atomicite-acte-trace-session-partagee.md)). Marqueur `# DETTE-025` |
| [DETTE-028](#dette-028--le-catalogue-de-types-de-phase-est-livré-sans-consommateur) | conception | majeur | `backend/domain/big_shoot_off.py`, `barrage.py` (dont `ConfigurationBarrage`, qui décrit le format de saisie et n'a plus d'appelant depuis que `resoudre_barrage` ne fait que départager), `suisse.py`, `colline.py`, `politiques.py` (`ScoreAvecHandicap`, `RoutingRepechage`) — ⚠️ **`poule.py` et `TiebreakPoules` en sont sortis le 09/08/2026** (E05US023) ; **sites d'affichage de l'écart** (E01US024) : `application/simulation_format.py`, `api/v1/formats.py`, `frontend/src/features/deroule/` | Les six moteurs et les trois politiques d'E05US015 n'ont **aucun appelant de production** : aucun service ne les instancie, aucune `config.policies` ne sait porter `nb_poules` / `nb_manches` / `portee_de_defi` / `restants`, et `domain/classement.py` calcule toujours son cumul sans passer par la famille `scoring` — donc `ScoreAvecHandicap` reste inerte. L'écran « Phases » propose pourtant les six types à la composition | La lettre d'[ADR-0045](adr/0045-sequence-de-phases-cycle-de-vie-typage-source.md) §2 est tenue (un moteur existe pour chaque type offert), son **intention** ne l'est qu'à moitié : l'organisateur peut composer une phase de poules dont le réglage n'est exprimable nulle part et que rien ne déroulera. Et un moteur sans consommateur n'est éprouvé que par ses propres tests — écrits le même jour, par le même agent ⚠️ **Depuis E07US005, l'écart est aussi visible du public** : une phase de type `placement` que l'organisateur a le droit de composer est **omise sans mention** de l'onglet « Tableaux » et de la vue d'écran de salle — `ServiceSaisieDuels._decor` la refuse, le service public l'écarte. Les sites d'affichage de l'écart n'étaient jusque-là que des surfaces d'administration. | E05US015 ([ADR-0062](adr/0062-catalogue-de-types-de-phase.md)) — **périmètre assumé**, l'exécution relevant d'E01US024 ; relevé en revue comme devant être **tracé** et non seulement documenté à l'ADR. **Partiellement résorbée par E06US003** (02/08/2026, ADR-0066) : `barrage.py` a ses appelants, `config.policies.tiebreak` est le premier réglage réellement porté, et `classement.py` passe par `PolitiquesPhase.tiebreak` — les quatre autres moteurs restent sans consommateur | ⚠️ **E01US024 n'en avait résorbé que la moitié** (01/08/2026, [ADR-0063](adr/0063-brouillon-de-format-invariant-a-l-application.md)) : composition livrée, exécution non. ✅ **E05US020 a résorbé le peuplement** (03/08/2026, [ADR-0068](adr/0068-le-moteur-consomme-les-prelevements-declares.md)) : `ServiceSaisieDuels._preleves` honore les prélèvements **par rangs** sur la qualification — « les rangs 1 à 32 » monte un tableau de 32, « et suivants » se résout sur l'effectif réel. Le test de caractérisation d'E01US024 a échoué comme prévu et cédé la place à son pendant positif. ✅ **E05US024 a résorbé le peuplement en cascade** (08/08/2026, [ADR-0080](adr/0080-un-prelevement-lit-le-classement-de-sa-phase-source.md)) : un prélèvement est désormais lu dans le classement de **sa** phase source dès lors que le moteur sait la lire — tableau→consolante, tableau→tableau, et toute chaîne de phases **classantes lues** (`_TYPES_CLASSANTS_LUS` = qualification et élimination directe). Le « cycle » qu'E05US020 invoquait pour reporter ce cas **n'existait pas** : la lecture nécessaire (`tableau.positions_acquises`) est produite par `ServiceSaisieDuels` lui-même, donc c'est une **récursion** sur un graphe acyclique, pas un cycle de modules. La note était exacte à sa date (E06US004 n'était pas livrée), plus ensuite. Le plancher d'inscrits remonte la chaîne dans le même mouvement. **Ce qui reste** : une source visant une phase de type **poules / suisse / colline / Big Shoot Off** reste **ignorée en silence** — le moteur ne sait pas lire leur classement —, donc la phase aval y reçoit toujours *tous* les archers en lice ; `le_reste` et `par_issue_de_tour` demeurent **inertes** (résolus nulle part — `DETTE-033`), les réglages (`nb_poules`, `nb_manches`, `portee_de_defi`, `restants`) restent inexprimables en `config.policies`, et `classement.py` ne passe toujours pas par la famille `scoring`. Marqueur `# DETTE-028` : `politiques.py` (moteurs inertes). **Arbitrage du commanditaire (07/08/2026)** : ces formats sont **voulus jouables, « au plus tôt dans le backlog »** — et **surtout composables dans le déroulé à l'atelier**, avec leurs paramètres. Découpée le 09/08/2026 en quatre tranches (4 moteurs x 2 surfaces ne tient pas dans une branche). ✅ **E05US023 a résorbé le volet poules** (09/08/2026, [ADR-0083](adr/0083-le-contrat-de-phase-jouable.md)) : `ServicePoules` est instancié au composition root, `config.poules` porte le réglage (à la **racine** du `config` : `policies` est un catalogue fermé de familles injectables — correctif de revue du 10/08/2026), la phase se pose en salle, ses rencontres se saisissent avec le pavé de duel, son classement se lit (`domain/classement_de_poules.py`) et une phase avale y prélève. Le signal d'écart d'E01US024 ne vise plus les poules et **continue de viser** les quatre autres — c'est le registre de contrat (`domain/contrat_phase.py`) qui le dérive désormais. ⚠️ **Nuance ajoutée en revue le 10/08/2026** : cela ne vaut que pour le **bandeau d'atelier** (`TYPES_SIGNALES_EN_ECART`). Le **bot de simulation** ne joue toujours pas les poules — `fabriquer_harnais_simulation` ne construit aucun `ServicePoules` —, donc `application/simulation_format.py` retire `POULES` **à la main** de sa table, faute d'une capacité *simulable* au registre de contrat. Une table dérivée n'est sûre que si la capacité dérivée répond exactement à la même question ; ici elle n'y répondait pas. ✅ **E05US027 a résorbé le volet colline** (22/08/2026), 4ᵉ et dernière tranche : `ServiceColline` rejoue ses manches des duels validés, `domain/classement_de_colline.py` rend son classement de phase, le routage dit à un archer quel défi il tire, et les écrans (atelier, saisie, public) sont livrés dans la même branche. **Le volet « moteurs de formats sans appelant » est donc CLOS** — les quatre moteurs d'E05US015 qui décrivaient un format jouable ont tous leur consommateur de production, et `TYPES_SIGNALES_EN_ECART` ne vise plus que `placement` et `barrage`, dont le cas est d'une **autre nature** : le premier a un décor d'arbre sans service pour le monter (E06US006/ADR-0083), le second est un **départage**, pas un format qu'on déroule. Ni l'un ni l'autre n'attend d'US. ⚠️ **Mais la dette ne se referme pas pour autant**, et il faut le dire clairement plutôt que de la barrer : `ScoreAvecHandicap` et `RoutingRepechage` restent **inertes** (aucun `config.policies` ne les porte), `classement.py` ne passe toujours pas par la famille `scoring`, et `le_reste` / `par_issue_de_tour` demeurent résolus nulle part (`DETTE-033`). Ce qui subsiste est donc le volet **politiques**, pas le volet moteurs — et il n'a aucune US inscrite. Marqueur `# DETTE-028` : `politiques.py` |
| [DETTE-029](#dette-029--lattribution-des-rangs-ex-æquo-est-écrite-trois-fois) | conception | mineur | `backend/domain/classement.py` (`_ranger`), `backend/domain/poule.py` (`classement_de_poule`, `_marquer_ex_aequo`), `backend/domain/suisse.py` (`classement_suisse`, `_propager_ex_aequo`), **+ E06US004** : `backend/domain/palmares.py` (`_numeroter`) | La règle « rang partagé à clé égale, avec sauts (1-2-2-4) » est écrite **trois fois**, et la propagation du drapeau `ex_aequo` **deux fois** en copie quasi verbatim. Les trois sites **divergent déjà** : `classement._ranger` ne porte aucun drapeau `ex_aequo`, les deux nouveaux si. **E06US003 fait diverger un axe de plus** : `classement._ranger` range désormais par **comparateur injecté**, les deux autres par **clé** — le remède proposé (prédicat d'égalité en paramètre) accommode les deux formes | 3ᵉ occurrence réelle : le seuil que le § Dette de `CLAUDE.md` fixe pour proposer un remède structurel est franchi **sur preuve**, pas sur pronostic. Corriger la règle (ou la faire diverger davantage) demande trois modifications coordonnées, et un oubli produit un classement **cohérent et faux** | E05US015 — deux des trois sites sont introduits par cette US ; relevé en revue (axes C1 et C2) | **US `refactor/` dédiée + ADR** (règle 16 : jamais en douce dans l'US courante). Remède minimal : une fonction pure `attribuer_rangs(ordonnes, meme_rang)` du domaine (~15 lignes, aucune abstraction nouvelle — le comparateur `Tiebreak` injecté suffit), chaque appelant gardant son dataclass de sortie. Marqueur `# DETTE-029` aux trois sites |
| [DETTE-031](#dette-031--le-suivi-du-déroulé-se-recalcule-intégralement-à-chaque-lecture) | technique | mineur | `backend/application/suivi_deroule.py` (`ServiceSuiviDeroule.pour_tournoi`), `backend/api/v1/suivi_deroule.py`, `frontend/src/features/suivi-deroule/hooks.ts`, **+ E06US003** : `ServiceClassement._verdicts_qualif` (une requête `barrage` de plus **à chaque** lecture du classement, endpoint pollé toutes les 10 s par chaque écran), **+ E07US008** : `backend/application/routage.py` (`ServiceRoutage._grille`), `backend/api/v1/routage.py` (les **deux** routes), `frontend/src/features/routage/hooks.ts`, **+ E06US004** : `backend/application/palmares.py` (`ServicePalmares._resultat`, une reconstruction **par phase à tableau**), `backend/api/v1/palmares.py` (les **deux** routes, dont le PDF), `frontend/src/features/palmares/hooks.ts`, **+ E07US005** : `backend/application/tableaux_publics.py` (`ServiceTableauxPublics.pour_tournoi`, une reconstruction **par phase à tableau**), `backend/api/v1/tableaux.py`, `frontend/src/features/tableaux/hooks.ts`, **+ E16US004** : `frontend/src/features/suivi/VueSuivi.tsx` (le récapitulatif de journée monte `useTableauxDesDeparts` depuis l'onglet public « Suivi »), **+ E05US024** : `backend/application/saisie_duels.py` (`ServiceSaisieDuels.resolveur_de_classement` / `_classement_de_l_ordre` — résoudre un prélèvement reconstruit **toute la chaîne amont**), **+ E05US023** : `backend/application/poules.py` (`ServicePoules.etat` en lecture, et `_ecrire` qui la rappelle **à chaque manche, barrage et validation**), `backend/api/v1/poules.py` (les deux routes de lecture), `frontend/src/features/poules/hooks.ts`, `frontend/src/features/suisse/hooks.ts` *(E05US030 : deux lectures de plus — l'état de la phase côté scoreur et côté écran des phases ; **aucun `refetchInterval`**, donc l'aggravation est du même ordre que celle des poules)*, **+ E05US026** : `backend/application/suisse.py` (`ServiceSuisse.etat` et `_ecrire`, même régime), `backend/api/v1/suisse.py` (les deux routes de lecture), `backend/application/routage.py` (`_routage_par_rencontres`), `backend/application/poules.py` (`ServicePoules.rencontres_a_tirer`), `backend/application/palmares.py` (`_resultat_classant` et `_est_epuisee`), **+ E05US031** : `backend/application/big_shoot_off.py` (`ServiceBigShootOff.etat`, dont la route `/etat/` passe de **scoreur** à **ouverte**), `backend/api/v1/big_shoot_off.py`, `frontend/src/features/big-shoot-off/hooks.ts`, `frontend/src/features/en-cours/VueEnCours.tsx` (l'onglet public monte l'une des **trois** routes d'état selon le format de la phase affichée), **+ E05US033** : `backend/application/arrets_programmes.py` (`ServiceArretsProgrammes.evaluer`, marqueur `# DETTE-031`), **+ E05US034** : `backend/application/arrets_programmes.py` (une **5ᵉ lecture au chemin court** d'`evaluer`, et `poser_arret_relatif` qui appelle `avancement_par_phase` **sur le thread du writer unique**, marqueur `# DETTE-031` au point d'appel) et `backend/application/suivi_deroule.py` (`avancement_par_phase`), appelés **après chaque validation de score** par `ServiceSaisie.valider` et `ServiceSaisieDuels.valider`, **+ E05US035** : `backend/application/saisie.py` (`ServiceSaisie._volees_du_plus_lent`, marqueur `# DETTE-031`) — un **résolveur de classement neuf par phase**, plus `placements.par_depart` / `inscriptions.par_depart` / `forfaits.par_phase`, sur la phase la plus **peuplée** et la plus **longue** du créneau, **+ E05US027** : `backend/application/colline.py` (`ServiceColline.etat` et `_ecrire`, même régime que ses trois jumeaux), `backend/api/v1/colline.py` (les deux routes de lecture), `frontend/src/features/colline/hooks.ts`, plus `ServiceColline.rencontres_a_tirer` (routage) et `avancement_de_phase` (suivi) — **aucun `refetchInterval` armé**, donc l'aggravation est du même ordre que celle du suisse, **+ E05US032** : `backend/application/suivi_deroule.py` (`ServiceSuiviDeroule._avancement_lu` — une recomposition **par phase déroulée par un service** qui tourne, sur l'endpoint public déjà pollé), `backend/application/poules.py` / `suisse.py` / `big_shoot_off.py` (`avancement_de_phase`, qui passe par `etat()`) | `GET /api/v1/tournois/{id}/suivi-deroule` est **public, non authentifié, sans cache et sans plafond** : chaque appel compte les engagés (départs × inscriptions) puis, **par phase en tableau**, appelle `ServiceSaisieDuels.reconstruire` — qui recalcule tout le classement du tournoi, rebâtit l'arbre, rejoue les duels et applique les forfaits. Deux surfaces le pollent (écran de salle 10 s, pilotage 10 s) et n'importe qui sur le réseau local peut le poller aussi | Faible aujourd'hui : mono-club, quelques phases, un ou deux écrans, réseau local fermé — mesuré à ~34 ms pour le seul classement. Devient sensible avec beaucoup d'écrans, un déroulé à nombreuses phases, ou le jour où l'appli sortirait du LAN | E07US004 ([ADR-0064](adr/0064-ecran-de-salle-poste-type-et-pilotage-par-etat-lu.md)) — relevé en revue (axe adversarial) : la dette était **assumée en commentaire** de `hooks.ts` sans être tracée ici. **Élargie par E07US008** ([ADR-0065](adr/0065-rang-acquis-lu-sur-la-plage-et-issue-repechee.md)) : un **2ᵉ endpoint** au même régime (`/routage/{id}/affectations`) et **deux surfaces de polling** de plus (onglet public « Affectations », carte de suivi sur chaque téléphone) — relevé par trois axes de revue, qui ont aussi corrigé quatre textes citant `DETTE-008` à sa place. **Élargie de nouveau par E07US005** : un **3ᵉ** endpoint public (`/tableaux/{id}`), une reconstruction **par phase**, et deux surfaces de plus dont l'onglet public « Tableaux » — en autant d'exemplaires qu'il y a de spectateurs. **Élargie par E16US004** : une **3ᵉ surface** sur `/tableaux/{id}`, et surtout la **fin de la protection par montage conditionnel** — l'onglet « Suivi » qui la porte est l'onglet d'**atterrissage par défaut** dès qu'on suit un archer (D-09), donc le poll ne se paie plus à l'ouverture de « Tableaux » mais à l'ouverture de l'**appli**. Relevée par quatre axes de revue, contre un corps de commit qui l'affirmait « inchangée ». ⚠️ **Élargie par E05US026, et relevée en revue** : le code disait « la dette est élargie d'autant » sans que la ligne bouge — 3ᵉ récidive du même oubli sur cette dette. Le **routage** passe d'une reconstruction *par tableau* à une reconstruction *par phase à rencontres, chaîne amont comprise*, sur deux surfaces déjà pollées (onglet public « Affectations », carte de suivi sur chaque téléphone) ; le **palmarès** ajoute une résolution par phase classante **plus** un second rejeu complet de la chaîne amont (`_est_epuisee` passe par `etat()`, donc par un résolveur **neuf** : le facteur est ×2 sur ces phases, pas « une lecture » — précision apportée en revue), sur ses deux routes publiques dont le PDF. **Élargie par E05US024** ([ADR-0080](adr/0080-un-prelevement-lit-le-classement-de-sa-phase-source.md)) : résoudre le prélèvement d'une phase reconstruit **chaque phase de sa chaîne amont**, donc le coût d'une lecture n'est plus « une reconstruction par phase » mais « une reconstruction par phase **de la chaîne** ». Le cache est mémoïsé sur toute la descente (correctif de revue, axe C2 — créé par niveau, il rendait le coût exponentiel sur un déroulé en **diamant**), donc borné au nombre de phases distinctes **par appel**. ⚠️ **Mais la frontière est l'appel, pas la requête** : `pour_depart` et `pour_tournoi` bouclent sur les phases et appellent une fois **par phase**, si bien que le coût d'une requête est **quadratique** en longueur de chaîne — n(n+1)/2 reconstructions contre n avant l'US. Un premier énoncé de ce correctif disait « borné … mais ne franchit pas la requête », ce qui était encore faux **dans le sens rassurant** — relevé deux fois de suite par la revue, sur la même ligne. **Élargie par E05US031** ([ADR-0089](adr/0089-le-catalogue-de-vues-porte-des-phases-pas-des-arbres.md)) : l'onglet public « En cours » monte, selon le format, l'une des **trois** routes d'état de phase — dont `/big-shoot-off/etat/`, qui passe de scoreur à **ouverte** —, en autant d'exemplaires qu'il y a de spectateurs. La protection par **montage conditionnel** joue toujours ici (« En cours » n'est pas l'onglet d'atterrissage, contrairement au cas d'E16US004) et aucun `refetchInterval` n'est armé ; ce qui n'est pas borné est le pic de **validation de fin de tour**, où chaque spectateur paie une reconstruction. Inscrit **dans le commit de l'US**, les trois élargissements précédents ayant tous dû être repris en revue. ⚠️ **Élargie par E05US032** ([ADR-0090](adr/0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md)) — **et c'est la 4ᵉ fois que la revue doit le rattraper**, la ligne portant déjà la mention « 3ᵉ récidive ». Le suivi du déroulé ouvre un chemin **neuf** vers les trois `etat()` de format : jusque-là `_duels_tranches` sortait tôt sur les types hors tableau, donc `ServicePoules` / `ServiceSuisse` / `ServiceBigShootOff` n'étaient **jamais** atteints par cet endpoint. Cinq axes de revue l'ont relevé, dont l'axe A qui a noté que la méthode voisine portait un marqueur là où la neuve n'en avait pas. **Deux garde-fous posés en réponse** : le lecteur n'est interrogé que pour une phase **démarrée** (une ou deux par créneau, contre toutes — les phases `à venir` et `terminée` sont la majorité d'un déroulé en fin de journée), et le marqueur du service dit désormais « chaque phase en tableau **et chaque phase déroulée par un service de format** ». **Ce qui reste non fait, et qui est le vrai écart** : le port `LecteurAvancementDePhase` **n'a pas** le `resolveur` partagé de son jumeau `LecteurClassementDePhase` (ADR-0084), dont la docstring dit pourtant « en laisser le service de format fabriquer un neuf ferait payer deux fois un tableau amont partagé » — un déroulé qualif → poules → suisse refait donc une descente complète de la chaîne amont **par phase**. L'ADR-0090 revendiquait reprendre ce patron « à la lettre » : c'était inexact, et le texte a été corrigé. ⚠️ **Élargie par E05US033** ([ADR-0091](adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md)), et l'aggravation est d'une **autre nature que les précédentes** : celles-ci ajoutaient des *surfaces de lecture* (un écran de plus, un onglet de plus), toutes bornées par un poll de 10 s ou par un montage conditionnel. Ici c'est le **facteur d'appel** qui change : le déclencheur d'arrêt recompose le créneau **après chaque validation de score**, donc au rythme de la salle et non de l'affichage — des centaines de fois par jour, depuis ~30 tablettes. L'ordre de grandeur reste tenable (une ou deux phases actives par créneau, SQLite en local, aucune I/O réseau) et le marqueur est posé **au point d'appel**. ⚠️ **Élargie d'un cran par E05US034** ([ADR-0092](adr/0092-un-arret-pose-le-jour-j-appartient-au-creneau.md)) : le déclencheur lit désormais une **seconde source d'arrêts** (ceux posés le jour J), donc le *chemin court* — celui qui sort sans rien recomposer quand aucun arrêt n'existe — passe de **quatre** `SELECT` indexés à **cinq**. L'aggravation est petite et **non négociable** : sans cette lecture, la garde sortirait avant d'avoir vu l'arrêt, et toute pause posée en cours de journée serait **inerte** — la pose répond 200, l'écran l'affiche, et rien ne coupe. C'est le pire mode de panne du mécanisme, échangé contre un `SELECT`. Le chemin **long**, lui, ne bouge pas : les arrêts de circonstance sont lus **une** fois en tête d'`evaluer` et l'index par phase est ensuite dérivé sans relire (`_par_phase`, fonction pure) — la première rédaction relisait le dépôt dans le helper, soit deux `SELECT` identiques par validation, corrigé en revue. ⚠️ **Ce que cette ligne annonçait de trop peu, et qu'il faut dire** (relevé en revue, axes C2 et adversarial) : une ligne d'`arret_de_circonstance` n'est **jamais supprimée ni marquée consommée** (pas de `retirer`, pas de lien vers le franchissement produit). Dans un créneau **sans aucun arrêt programmé** — celui où le chemin court sortait systématiquement —, la première pause posée à 14 h **désarme la garde jusqu'au soir**, y compris après que la pause a coupé et été relevée. Le rapport « quatre `SELECT` indexés contre une recomposition complète » cesse alors de s'appliquer : on paie la recomposition après chaque validation. **L'option « rien » est retenue et elle est défendable** — l'ordre de grandeur reste tenable (une ou deux phases actives, SQLite local, règle 12) et c'est déjà le régime de tout créneau portant des arrêts programmés. Si une mesure le réclamait, le remède est d'un cran et non d'un pattern : filtrer la garde sur les arrêts **non encore traités**, l'information étant déjà lue au même endroit (`_traites_par_phase`). ⚠️ **Ce que cette US n'a pas fait non plus** : le `resolveur` partagé du port `LecteurAvancementDePhase`, remède borné hérité d'E05US032 et déjà non tenu par E05US033. E05US034 ne touche **aucun** des trois `avancement_de_phase` — elle lit le créneau par `ServiceSuiviDeroule`, comme sa tranche A. **Deuxième pronostic consécutif tombé à faux sur cette ligne** ; le remède reste sans porteur, et il faut cesser de lui en désigner un par déduction. ⚠️ **La promesse que cette ligne portait pour E05US033 n'a pas été tenue, et ce n'est pas un oubli** : elle annonçait que l'US « rouvrirait ces trois réalisations » et porterait donc le `resolveur` au port. Elle ne les a pas rouvertes — elle consomme `ServiceSuiviDeroule.pour_depart`, seul endroit sachant répondre pour **tous** les formats (l'élimination directe n'a aucun lecteur branché, cf. ADR-0091 §7), et n'a donc touché aucun des trois `avancement_de_phase`. Le remède reste entier et sans porteur désigné : ne pas le croire fait | Mémoïser la projection par `(tournoi_id, version)` — la reconstruction est **pure** à donnée constante, donc invalidable sur l'événement post-commit `donnees_modifiees` qui existe déjà. Aucun cache n'est justifié avant qu'une mesure le réclame. Marqueurs `# DETTE-031` sur `ServiceSuiviDeroule.pour_tournoi`, `ServiceRoutage._grille`, les deux routes de `api/v1/routage.py`, `features/routage/hooks.ts`, `ServicePalmares._resultat`, `api/v1/palmares.py`, `features/palmares/hooks.ts`, `ServiceTableauxPublics.pour_tournoi`, `api/v1/tableaux.py`, `features/tableaux/hooks.ts` et `ServiceSaisieDuels.resolveur_de_classement`, plus `ServicePoules.etat`, `ServicePoules._ecrire`, `ServicePoules.rencontres_a_tirer`, `ServiceSuisse.etat`, `ServiceSuisse._ecrire`, `ServiceRoutage._routage_par_rencontres`, `ServicePalmares._resultat_classant`, `ServicePalmares._est_epuisee` et, depuis **E05US031**, `ServiceBigShootOff.etat` plus `frontend/src/features/en-cours/VueEnCours.tsx`, et depuis **E05US032** `ServiceSuiviDeroule._avancement_lu`, et depuis **E05US033** `ServiceArretsProgrammes.evaluer`, et depuis **E05US034** `ServiceArretsProgrammes.poser_arret_relatif`, et depuis **E05US035** `ServiceSaisie._volees_du_plus_lent`. ⚠️ **Élargie par E05US035** ([ADR-0093](adr/0093-une-qualification-se-decoupe-en-tours-egaux.md)) : la **qualification** rejoint les types lus par le suivi, et c'est celle qui coûte le plus — la plus peuplée (tout le plateau, là où les autres formats n'ont que leurs qualifiés) et la plus longue (elle occupe la matinée entière). Le chemin est celui d'E05US033 : lu **après chaque validation de score**, donc sur le thread du writer unique, et par la route publique de suivi. ⚠️ **Un N+1 a été trouvé en revue et corrigé dans le commit** — une lecture de série **par archer** (~120 `SELECT` par volée validée) remplacée par `SerieRepository.par_phase`, que le port offrait déjà : quatre axes l'ont relevé, et le commentaire voisin mettait justement en garde contre ce geste pour le résolveur de classement (« correctif de 2ᵉ passe d'E05US025, à ne pas rejouer ici »). **Ce qui reste** est le résolveur fabriqué par phase — le régime de cette dette, pas un défaut neuf. **Remède borné, hérité d'E05US032 et toujours à faire** : porter le `resolveur` partagé au port `LecteurAvancementDePhase`, comme ADR-0084 le fait pour son jumeau — c'est la seule partie de cette dette qui ait un correctif *borné et connu*. ⚠️ Il était annoncé « se traite avec `E05US033`, qui rouvrira ces trois réalisations » : **E05US033 ne les a pas rouvertes** (elle passe par le suivi, pas par le port) et le remède n'a donc pas de porteur. Le rattacher à la prochaine US qui touche réellement `ServicePoules.avancement_de_phase`, `ServiceSuisse.avancement_de_phase` ou `ServiceBigShootOff.avancement_de_phase` — ou l'ouvrir en US `refactor/` dédiée, ce qui est plus honnête que de le remettre à une US qu'on n'a pas encore écrite. **Ne pas réattribuer par pronostic** : c'est ce pronostic-là qui vient de tomber à faux |
| [DETTE-032](#dette-032--la-prise-de-controle-se-mesure-sur-lheure-murale-pas-sur-une-horloge-monotone) | technique | mineur | `backend/application/ecrans.py` (`ServiceEcrans._ecoulees`), `backend/domain/ecran.py` (`Consigne.expiree`, `reste_secondes`) | L'échéance d'une prise de contrôle est calculée comme un écart entre deux lectures de l'**heure murale** (port `Horloge`). Une resynchronisation NTP en cours de journée qui **recule** l'horloge repousse d'autant l'expiration ; côté écran, le décompte local atteint zéro, le sondage suivant lui rend la durée pleine, et l'affichage **oscille** entre vue imposée et déroulé | Faible : suppose une remise à l'heure en pleine journée sur un serveur local sans internet. Le pire cas est cosmétique (un écran qui hésite quelques secondes), jamais une perte de donnée | E07US004 ([ADR-0064](adr/0064-ecran-de-salle-poste-type-et-pilotage-par-etat-lu.md)) — relevé en 3ᵉ passe de revue, après qu'un correctif eut **prétendu** le traiter sans le faire | Mesurer la durée sur une référence **monotone** (`time.monotonic`) plutôt que sur l'heure murale, en ajoutant un port dédié à côté d'`Horloge` — ce dernier reste juste pour *dater* (audit, présence), pas pour *chronométrer*. Marqueur `# DETTE-032` sur `ServiceEcrans._ecoulees` |
| [DETTE-033](#dette-033--un-battu-repris-par-la-séquence-nest-pas-annoncé) | conception | mineur | `backend/application/routage.py` (`ServiceRoutage._router`, branche `TERMINE`) | Le repêchage a **deux moitiés lues à deux sources indépendantes** : le `routing` (`_est_repeche`, décidé **match par match**) et les **sources de la séquence** (`_repechages`, indexées par **tour**). Seule la première est annoncée. Un battu que la phase avale prélève par `issue_de_tour/perdants` lit donc son rang **sans savoir qu'il rejoue** | Faible aujourd'hui : aucun moteur ne consomme les prélèvements (**DETTE-028**), donc composer un tel déroulé ne fait encore rien tirer à personne. Devient **réel** dès qu'E05US010+ exécutera le prélèvement — l'archer rentrerait chez lui entre deux phases | E07US008 ([ADR-0065](adr/0065-rang-acquis-lu-sur-la-plage-et-issue-repechee.md) §3) — un correctif de revue a tenté de la combler et a été **démoli de deux façons opposées** en 2ᵉ passe : `dernier` est le dernier match *joué* et non le match perdu (on rate le battu qui redescend en petite finale), et un **tour couvre plusieurs plages** (finale et petite finale sont toutes deux au tour 3, on décorerait le 4ᵉ du podium) | **Ne pas deviner** : les deux correctifs proposés étaient incompatibles, ce qui est le signal que la **sémantique de `SourcePhase.par_issue_de_tour` n'est pas tranchée**. Elle appartient à l'US qui implémentera le prélèvement, pas à un canal d'affichage. Figée par `test_le_battu_repris_par_la_sequence_n_est_pas_encore_annonce`, qui **échouera** le jour où la règle sera décidée. Marqueur `# DETTE-033` sur la branche `TERMINE` de `_router` |
| [DETTE-035](#dette-035--la-conséquence-dune-profondeur-de-classement-nest-pas-chiffrée-au-moment-du-choix) | conception | mineur | `backend/domain/deroule.py` (`_braquets`), `backend/application/simulation_format.py` (`PhaseSimulee.ecart`), `frontend/src/shared/phases/ChoixProfondeur.tsx` (`AIDE_PROFONDEUR`) | Le schéma à braquets compte les duels de l'**arbre** (`effectif - 1`) et **ignore ceux que la politique `depth` ajoute** : une petite finale au preset, toute la cascade de placement en 1→N. L'organisateur choisit donc « classement intégral » sans voir le nombre de duels qu'il vient d'engager, alors que la maquette A07 fait de ce chiffrage l'exigence `P-4` (« chiffrer la conséquence **au moment du choix**, pas la découvrir à 10 h ») | Modéré : c'est le réglage du déroulé qui pèse le plus lourd sur la journée — un tableau de 120 passe de **128 duels à 436** (mesuré en revue), près de quatre fois plus. Atténué de deux façons : l'écran **énonce** la conséquence en clair sous le choix, et la **simulation** (E15US002), qui joue réellement le format, en rend le compte exact | E06US006 ([ADR-0070](adr/0070-profondeur-de-classement-reglee-par-phase.md)) — assumée à l'écriture, pas découverte en revue | **Ne pas recopier la structure du tableau dans la projection.** Les deux voies faciles sont mauvaises : ensemencer un vrai `construire_tableau` dans `projeter` lui imposerait `seeding`/`byes` qu'une projection évite délibérément ; une formule fermée (`P/2 × log2(P)`) serait une **seconde source de vérité** sur l'arbre, à faire diverger au premier format. Piste : faire rendre à `Depth` le nombre de matchs de classement qu'elle implique pour un effectif — la politique sait déjà quels rangs elle produit. Marqueurs `# DETTE-035` sur `_braquets`, sur `PhaseSimulee.ecart` et sur `AIDE_PROFONDEUR` (le front est l'endroit exact du raccourci : c'est là que l'organisateur choisit sans voir le chiffre) |
| [DETTE-036](#dette-036--une-position-du-cloisonnement-na-pas-deffet-distinct) | conception | mineur | `backend/domain/cloisonnement.py` (`Cloisonnement.separe_blason`/`separe_categorie`), `frontend/src/features/placement/presentation.ts` (`LIBELLE_CLOISONNEMENT`) | Le réglage de cloisonnement offre **quatre** positions à l'organisateur, mais n'en produit que **trois** comportements : le blason d'un archer étant celui de sa catégorie (`Categorie.blason_id`), « un seul blason **et** une seule catégorie par cible » rend le même plan que « une seule catégorie par cible ». L'organisateur choisit une position plus stricte et obtient celle d'avant | Faible : aucun plan n'est faux, aucune règle n'est violée — le coût est un choix d'écran qui n'a pas l'effet qu'il annonce, sur la position la moins utilisée. Atténué par une mention explicite dans la fiche de recette, l'aide de l'écran et l'ADR | E03US007 ([ADR-0071](adr/0071-cloisonnement-categorie-blason-active-et-dur.md) §3) — **assumée au cadrage** (les quatre positions sont un choix du commanditaire, en connaissance de la redondance), **tracée** sur relevé de revue (axe C2) : le précédent DETTE-028 a établi qu'une capacité livrée sans effet se trace au registre et ne se contente pas d'un ADR | Se résorbe **d'elle-même** avec `EF-1.4` (une phase surcharge le blason : « toutes les finales sur triples ») — le couple (catégorie, blason) cesse alors d'être fonctionnel et les deux positions divergent, sans migration ni changement de contrat. **Ne rien faire d'ici là** : retirer la position coûterait une migration et un réapprentissage pour la remettre. Marqueurs `# DETTE-036` sur les deux prédicats de `Cloisonnement` et sur `LIBELLE_CLOISONNEMENT` |
| [DETTE-051](#dette-051--un-forfait-déclaré-en-tableau-reste-prélevable-en-aval) | conception | mineur | `backend/domain/classement_de_tableau.py` (`_situee`) | `_situee` remet le statut à `EN_LICE` pour **tout** participant du tableau, au motif que « le filtre des sortis a déjà eu lieu à l'ensemencement ». C'est vrai d'un forfait de **qualification**, pas d'un forfait déclaré **dans ce tableau-ci** : `_appliquer_forfaits` le traite en *walkover* (ADR-0050), l'archer **reste** dans l'arbre et conserve une position acquise. Il ressort donc `EN_LICE` dans le classement dérivé, et `preleves._en_lice` ne le filtre pas | Faible, mais **atteignable dès le premier format en cascade** — c'est-à-dire dès que cette US sert : un archer qui a abandonné en 1/8 peut être **ensemencé dans la consolante**, où il ne se présentera pas — un duel fantôme à gérer à la main le jour J. Aucune donnée n'est fausse, c'est une population trop large | E05US024 — relevé en revue (axe B), **non tranché** : « un abandon en tableau ferme-t-il l'accès aux phases aval ? » est une **règle métier**, pas un correctif de revue. La deviner reviendrait à décider une règle de compétition dans un service d'exécution, ce qu'ADR-0065 §3 a explicitement refusé de faire | Trancher avec le club, puis porter la décision dans `_situee` (propager `statut` plutôt que le forcer) **ou** dans `preleves`. Marqueur `# DETTE-051` sur `_situee` |
| [DETTE-052](#dette-052--la-saisie-admin-devine-le-créneau-de-larcher) | conception | mineur | `backend/application/saisie.py` (`_depart_de_saisie`), routes `POST /api/v1/tournois/{id}/archers/{id}/volees` et suivantes | En saisie **admin** (`contexte=None`), le service ne reçoit aucun créneau : il le **devine** en prenant le plus petit identifiant de créneau où l'archer est inscrit. La saisie par **poste** ne souffre pas du défaut — la tablette porte son `depart_id` | Un archer engagé matin **et** après-midi verra l'admin écrire dans son créneau du matin, donc dans la qualification du matin. Sans conséquence tant qu'un archer ne tire qu'un créneau, ce qui est le cas courant | Née de **E05US025** : la feuille pend désormais à une phase, donc il faut résoudre *laquelle* — la question ne se posait pas quand une série valait pour tout le tournoi. Le défaut est donc **révélé**, pas introduit : l'ancienne clé écrasait purement et simplement la seconde série (c'était DETTE-046) | Résorption : porter le `depart_id` sur les routes de saisie admin et le passer au service, comme le fait déjà le `ContexteSaisie` d'un poste. Marqueurs `# DETTE-052` sur `_depart_de_saisie` et `_phase_qualification` |
| [DETTE-053](#dette-053--bareme_du_tournoi-et-grain_du_tournoi-portent-un-nom-qui-ment) | conception | mineur | `backend/application/bareme_qualification.py` (`bareme_du_tournoi`), `backend/application/grain_validation.py` (`grain_du_tournoi`, `_qualification_ou_none`), routes `GET`/`PUT /api/v1/tournois/{id}/bareme-qualification` et `.../grain-validation` | Les deux lectures « du tournoi » rendent le réglage de la **première** qualification du déroulé. Le nom promet un réglage de tournoi ; le code rend celui d'une phase parmi N | Faible aujourd'hui — juste sur tout tournoi mono-qualification, c'est-à-dire la quasi-totalité. Sur un déroulé composé, un appelant qui s'y fierait annoncerait le barème du premier tour à des archers qui en tirent un autre. Les surfaces qui comptent sont déjà portées ailleurs (l'écran liste les qualifications, la feuille papier lit le créneau) | **E05US025**, avoué en *Conséquences* d'[ADR-0082](adr/0082-plusieurs-qualifications-dans-un-meme-deroule.md) mais **non tracé** — relevé en revue (axe C2), qui a rappelé le précédent DETTE-036/DETTE-037 : une capacité ou une limite avouée en ADR **se trace au registre**, l'aveu ne remplace pas la ligne | Résorption : faire passer les consommateurs restants par `qualifications` / une lecture par étape, puis retirer les deux méthodes et leurs routes historiques. Marqueurs `# DETTE-053` sur `bareme_du_tournoi` et `grain_du_tournoi` |
| [DETTE-054](#dette-054--huit-paires-de-dto-jumeaux-entre-les-deux-routeurs-de-composition) | conception | mineur | `backend/api/v1/phases.py` et `backend/api/v1/formats.py` — `SourceDTO`, `ProfondeurDTO`, `ReglagePoulesDTO` (+ `BaremePouleDTO`), **`ReglageBigShootOffDTO`** (E05US028, 4ᵉ paire) et **`ReglageSuisseDTO`** (E05US026, 5ᵉ paire) et **`ArretProgrammeDTO`** (E05US033, 6ᵉ paire) et **`DecoupageDTO`** (E05US035, 7ᵉ paire) et **`ReglageCollineDTO`** (E05US027, 8ᵉ paire, **deux** champs), chacun écrit **deux fois** | Les deux routeurs composent la **même** notion — une étape de déroulé — à deux mailles : la bibliothèque de formats et le déroulé d'un tournoi. Chaque champ de composition y est donc décliné en deux DTO strictement identiques (mêmes champs, mêmes `vers_agregat` / `de_agregat`), avec pour seule différence une docstring qui dit « jumeau assumé de l'autre » | Aucun effet à l'exécution. Le coût est un **oubli d'un côté** : E05US023 a dû ajouter le réglage de poules aux deux, et rien n'aurait rougi s'il n'avait été ajouté qu'à un — l'atelier de formats aurait perdu le réglage à la promotion, en silence. C'est le même angle mort que `ModelePhase.barrage_jusqu_au`, **effectivement** manqué jusqu'au 07/08/2026 (cf. ADR-0076) | **E05US023** (3ᵉ paire), **élargie par E05US028** (4ᵉ paire, `ReglageBigShootOffDTO`). Les deux premières datent d'E05US010 (`SourceDTO`) et d'E06US006 (`ProfondeurDTO`) : le seuil « 3ᵉ occurrence réelle » de `CLAUDE.md` est atteint depuis E05US023, donc le remède structurel est justifié par le code du jour — mais il se traite en US dédiée, pas en douce dans une US de moteur. ⚠️ **L'élargissement du 15/08/2026 est un relevé de revue** : le code portait bien « 4ᵉ paire, `DETTE-054` » et le corps de commit annonçait la dette « élargie », mais **le registre n'avait pas bougé** — qui l'aurait résorbée aurait extrait trois paires et laissé la quatrième. **Élargie de nouveau par E05US026** (5ᵉ paire, `ReglageSuisseDTO`) : la duplication croît d'une paire **par format rendu jouable**, ce qui est le signal que le remède ne doit plus attendre longtemps — la colline (`E05US027`) en fera une de plus. ⚠️ **Élargie d'une paire par E05US033** ([ADR-0091](adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md)) : `ArretProgrammeDTO`. Ce n'est pas une US de format, et le signal change donc de nature : la duplication ne croît plus seulement « par format rendu jouable » mais **par réglage d'étape**, quel qu'en soit le motif. *(Une seconde paire — `DecoupageDTO` — a existé pendant l'implémentation puis disparu avec le réglage de découpage, sorti du périmètre le 19/08/2026. Un état intermédiaire du registre l'annonçait : corrigé avant la PR.)* ⚠️ **Élargie de nouveau par E05US035** ([ADR-0093](adr/0093-une-qualification-se-decoupe-en-tours-egaux.md)) : `DecoupageDTO` revient, cette fois pour de bon — 7ᵉ paire. Le fait qu'elle soit apparue, disparue puis revenue en trois US **est** le signal : la duplication n'attend pas un nouveau format, elle suit chaque réglage d'étape, y compris ceux qu'une US ajoute puis retire. Inscrit dans le commit de l'US. ⚠️ **Élargie d'une 8ᵉ paire par E05US027** ([ADR-0083](adr/0083-le-contrat-de-phase-jouable.md)) : `ReglageCollineDTO`. La ligne annonçait depuis E05US026 que « la colline en fera une de plus » — c'est fait, et le pronostic était juste. ⚠️ **Cette paire-ci porte DEUX champs** (`nb_manches`, `portee_de_defi`) là où ses voisines n'en portent qu'un : le coût d'un oubli d'un côté est donc double, et c'est exactement le mode d'aggravation discret qu'E05US029 décrit ci-dessous. ⚠️ **Aggravée autrement par E05US029** ([ADR-0094](adr/0094-le-mode-de-composition-d-une-poule-commande-aussi-la-lecture-de-son-classement.md)) : **aucune paire neuve**, mais la paire `ReglagePoulesDTO` gagne **deux champs de plus** (`mode`, `serpent_assume`) des deux côtés. C'est le mode d'aggravation le plus discret — il n'ajoute pas de ligne au décompte et ne déclenche donc aucun signal — et c'est aussi le plus fréquent à venir : chaque réglage enrichi passera par là | US `refactor/` — un module de DTO de composition partagé (`api/v1/composition_dto.py` ou équivalent), importé par les deux routeurs. ⚠️ **Ne pas fusionner les deux `EtapeDTO`** : eux diffèrent réellement (le modèle n'a ni statut ni tournoi, ADR-0060 §5). Ce sont les **feuilles** qui sont identiques, pas les racines |
| [DETTE-037](#dette-037--lalerte-dimpact-ne-chiffre-pas-la-réserve-que-le-cloisonnement-va-créer) | conception | mineur | `backend/application/placement.py` (`ServicePlacement._impact`) | L'alerte qui protège une régénération tardive (E12US007) compte les archers **replacés** et les cibles **déjà scorées**, mais pas ceux qu'un cloisonnement plus strict va **exclure** : l'organisateur confirme, puis découvre la réserve. ADR-0071 invoque pourtant cette alerte comme la protection du réglage tournoi en cours | Faible à modéré : rien n'est perdu (la régénération est déterministe et réversible en desserrant le réglage), mais la décision est prise **sans** son chiffre — le défaut même que `P-4` et DETTE-035 nomment ailleurs | E03US007 ([ADR-0071](adr/0071-cloisonnement-categorie-blason-active-et-dur.md), Conséquences) — relevé en **2ᵉ passe** de revue par trois axes : le manque était **avoué dans l'ADR** et non tracé, alors que le même commit ouvrait DETTE-036 en invoquant « documenter ne suffit pas ». Deux poids, deux mesures dans un seul commit | Faire rendre à `_impact` un **compte de réserve projetée** : rejouer `placer` à blanc sur le gabarit et le réglage courants (lecture pure, aucun effet de bord — le moteur est déterministe et sans état) puis compter les conflits. Ne **pas** approcher le chiffre par une heuristique (« une cible par catégorie ») : il serait faux là où il compte, sur les gabarits justes. Marqueur `# DETTE-037` sur `ServicePlacement._impact` |
| [DETTE-038](#dette-038--un-libellé-de-match-énonce-des-rangs-relatifs-au-tableau) | conception | mineur | `backend/domain/tableau.py` (`libelle_tour`, les deux branches nommées par des rangs), `backend/application/routage.py` (2 appels), `backend/api/v1/tableaux.py` | `construire_tableau` engendre **toujours** depuis `Plage(1, taille)` : les rangs d'un match sont **relatifs au tableau**. Un tableau qui prélève « les rangs 33 et suivants » (composable **et exécutable** depuis E05US020) décide donc des rangs absolus 37-40 dans un match que l'application annonce « **Places 5 à 8** » — et « Match pour la 5ᵉ place » pour son terminal | Nul aujourd'hui sur le **premier** tableau d'un tournoi (le cas courant : il part du rang 1, relatif = absolu). Devient **faux devant le public** dès qu'un déroulé enchaîne un tableau secondaire — ce que le catalogue de types et les prélèvements par rangs rendent possible depuis E05US015/E05US020 | Défaut **préexistant** sur `place_en_jeu` (E05US010) ; **élargi** par E07US005, qui ajoute la famille « Places N à M » et la porte pour la **première fois sur une surface publique** (onglet « Tableaux », écran de salle, panneau de routage) | Le dépôt sait déjà faire : `domain.palmares` applique `decalage = rang_premier - 1` pour convertir relatif → absolu, et `domain/deroule.py` en avertit deux fois. Remède : passer ce décalage à `libelle_tour`, comme `_numeroter` le fait pour le palmarès — il se lit sur le prélèvement de la phase. **À traiter dans l'US qui livrera un déroulé à tableau secondaire**, pas avant : aujourd'hui aucun format livré n'en produit, et l'on chiffrerait un décalage toujours nul. Marqueur `# DETTE-038` sur les deux branches de `libelle_tour` |
| [DETTE-039](#dette-039--la-cadence-et-la-taille-dune-page-projetée-sont-en-dur) | technique | mineur | `frontend/src/features/routage/pagination.ts` (`NOMS_PAR_PAGE`, `SECONDES_PAR_PAGE`) | Le commanditaire demande « 20 s **(réglable)** » (questionnaire `p06`) ; la cadence et le nombre de noms par page sont deux constantes de module. `NOMS_PAR_PAGE = 40` n'a par ailleurs jamais été mesuré sur le vidéoprojecteur réel | Un club dont les noms sont longs, ou dont la salle est profonde, ne peut rien ajuster sans recompiler — sur la seule surface que personne ne peut manipuler pendant le tournoi | Lot « retours maquettes » du 05/08/2026 — assumé au commentaire ; **résorption : `E16US009`** |
| [DETTE-040](#dette-040--lalphabet-des-codes-de-terrain-existe-en-trois-exemplaires) | conception | mineur | `backend/infrastructure/postes/codes.py`, `backend/infrastructure/scoreurs/codes.py`, `frontend/src/shared/ui/codeTerrain.ts` | La chaîne `ABCDEFGHJKLMNPQRSTUVWXYZ23456789` et la longueur `6` sont écrites **trois fois**. Les deux fichiers Python annonçaient eux-mêmes attendre « une 3ᵉ preuve avant tout remède » : le front est cette troisième | Un alphabet modifié d'un côté et pas des deux autres produit des codes que le pavé refuse de composer, ou l'inverse. Le garde-fou réel reste que **le serveur tranche** — le front n'est qu'une aide à la frappe | Lot « retours maquettes » du 05/08/2026. **Aucun remède proposé** : réunir Python et TypeScript supposerait d'exposer l'alphabet par l'API, ce qui est une US à part entière et coûte plus que la duplication (règle 16 — « ne rien faire » est ici la bonne réponse) |
| [DETTE-041](#dette-041--le-front-approxime--a-tiré--par--total-non-nul-) | conception | mineur | `frontend/src/features/competition/departage.ts` (`totauxExAequo`), `frontend/src/features/competition/api.ts` (`LigneClassement`) | Le domaine **distingue** `a_tire` de `total > 0` — `backend/domain/classement.py` le documente : « un archer qui a validé une volée entièrement manquée a bien tiré, pour un total nul ». Le DTO n'expose pas ce booléen, donc le front l'approxime par `total !== 0` | Deux archers réellement à zéro ne sont pas signalés ex æquo. Cas de fin de journée, quasi théorique, sans conséquence autre que l'absence d'une phrase d'aide. **Non traité et plus gênant** : deux archers à des avancements différents (3 volées contre 6) au même total sont signalés ex æquo à tort — le DTO ne porte aucun avancement | Lot « retours maquettes » du 05/08/2026, relevé en 2ᵉ passe de revue. Résorption : exposer `a_tire` (et l'avancement) dans `LigneClassement`. ⚠️ **Le second volet est un arbitrage** : « ex æquo » vaut-il à l'issue de la qualification, ou à avancement égal ? À poser au commanditaire |
| [DETTE-042](#dette-042--le-métier-dit--couloir-de-tir--le-code-dit-position) | conception | majeur | `backend/domain/gabarit_salle.py` (`POSITIONS`), `backend/domain/placement.py` (`Placement.position`), les DTO de `backend/api/v1/{gabarits,placement,placement_duels,saisie,routage}.py`, leurs miroirs front, et les colonnes `placement.position` / `placement_duel.position` / **`placement_poule.position`** (E05US023) en base | **E16US001** ([ADR-0073](adr/0073-pas-de-tir-groupe-de-cibles-couloir-de-tir-place-d-archer.md)) a arbitré le terme métier : la place d'un archer devant sa cible est un **couloir de tir**, pas une « position ». Corrigé dans **l'application livrée** (écrans, aide contextuelle, messages d'API, les deux PDF, maquette A10 + planche wireframe, glossaire), **pas** dans les identifiants ni en base — écart à la **règle 3**, **amendant ADR-0006**, créé par cette US | Aucun effet à l'exécution : purement de lecture. Qui part du glossaire cherche `couloir` et ne trouve rien ; l'API expose un mot que l'UI contredit — soit les deux critères de « majeur » (invariant du projet + piège du prochain contributeur) | Non fait dans l'US : le renommage traverse domaine + ORM + **migration Alembic** + 5 modules d'API + front, ~20 fichiers mécaniques, dont le diff noierait celui du vocabulaire d'écran. Résorption **rattachée à `E01US019`** (voir DETTE-010) : même symbole, même colonne, **une seule migration** |
| [DETTE-055](#dette-055--un-barrage-de-poule-non-situé-est-accepté-et-ne-referme-rien) | conception | majeur | `backend/api/v1/barrages.py` (`AnnonceRequete._coherence_du_regime`, marqueur `# DETTE-055`), `backend/domain/barrage.py` (`BarrageDePlaces.verdict`), `backend/application/poules.py` (`_verdicts_de_barrage`) | En portée `poule`, `phase_id` et `rang` sont **facultatifs au contrat d'API**. C'était sans conséquence en E06US003 — aucun classement de poule n'existait où retourner un verdict. Depuis **E05US023**, le verdict **referme** le classement de la poule : `_verdicts_de_barrage` filtre sur l'égalité des phases (`None` n'égale aucune phase) et `verdict()` rend un ordre vide sans `rang_dispute`. Un `POST` direct sans ces deux champs ouvre donc un barrage qui se tire, se clôture, et **ne referme rien** — sans le moindre message | Le formulaire, lui, les exige depuis la revue d'E05US023 : le seul chemin utilisateur est sûr. Reste la voie API directe, et surtout le principe — le même fichier reproche cet écart au régime de qualification (« L'UI ne le permettait pas ; **l'API est le contrat** »). Second volet, non traité : le `rang` n'est **pas validé**, donc un rang qui ne correspond à aucun ex æquo de la phase produit un classement de poule renuméroté et débarrassé de ses `=`, silencieusement | Revue d'E05US023 (2ᵉ passe, axes A et adversarial). **Non corrigé dans l'US** : resserrer le régime invalide un comportement qu'`test_un_barrage_de_poule_se_declare_avec_ses_tireurs` documente comme voulu (`rang_dispute is None` y est asserté) — c'est un changement de contrat sur une US livrée, donc un **arbitrage du commanditaire**, pas de la plomberie | Exiger `phase_id` **et** `rang` en portée `poule` dans `_coherence_du_regime`, et refuser en service un `rang_dispute` qui n'est pas un rang partagé de la phase visée. Coût : les 13 annonces de poule de `test_barrages_api.py` à situer. À trancher avec le commanditaire |
| [DETTE-057](#dette-057--une-rencontre-de-poule-désynchronisée-na-aucune-sortie) | conception | majeur | `backend/application/poules.py` (`_rencontre_affichee`, `_duel_courant`), `frontend/src/features/poules/SaisiePoules.tsx`, **+ E05US029** : `backend/domain/poule.py` (`ReglageDePoules.mode`, marqueur `# DETTE-057`) | Quand la population d'une phase de poules change après des tirs, les rencontres déjà jouées portent des duellistes qui ne sont plus ceux que la composition désigne. Le tir est **masqué** (ADR-0049 §4) et l'écriture **refusée** (409) — les deux sont justes. Mais **aucun geste ne rétablit** la rencontre : il n'existe pas de purge des tirs orphelins d'une phase, **+ E05US027** : `backend/application/colline.py`, `frontend/src/features/colline/SaisieColline.tsx` | Le `match_numero` d'une poule est un **compteur** qui court sur toute la phase, pas une position d'arbre : un seul archer inscrit ou retiré peut désynchroniser **toutes** les rencontres tirées d'un coup. La seule sortie est de rétablir la population à l'identique. Atténué par la revue : l'écran **dit** l'état (« tir désynchronisé — à rétablir ») au lieu d'afficher « à tirer », et la file hors-ligne ne se fige plus — mais la donnée reste inatteignable ⚠️ **Élargie par E05US029** ([ADR-0094](adr/0094-le-mode-de-composition-d-une-poule-commande-aussi-la-lecture-de-son-classement.md)) : le déclencheur n'est plus seulement un changement de **population** mais aussi de **composition**. Basculer `ReglageDePoules.mode` sur une phase en cours recompose **tous** les groupes — `ServicePhases.modifier` n'ayant, comme le note `DETTE-062`, aucune garde de statut. **Le mode d'aggravation est le plus discret de la ligne** : à effectif divisible, serpent → par niveau conserve le **même nombre de groupes et les mêmes tailles**, donc l'aperçu de l'atelier est *identique avant et après* — là où un changement de population se voit. Deux atténuations réelles : le filet `DuelDesynchronise` joue à l'identique (rien n'est écrasé), et le geste est **réversible** — rebasculer le mode restaure exactement la composition, ce qui n'est pas vrai d'une population modifiée. *(Relevé par trois axes de revue.)* | Revue d'E05US023 (2ᵉ passe, axe adversarial). **Non corrigé dans l'US** : la seule résorption connue est un geste admin de **suppression de tirs**, donc une donnée de score effacée — cela ne se décide pas dans un correctif de revue ⚠️ **Élargie par E05US027 (relevé en 2ᵉ passe de revue)** : la colline est le 3ᵉ format concerné, et le **rayon** y est maximal — un inscrit de plus renumérote **toutes** les positions, donc désynchronise la phase **entière**, là où une poule ne perd que son groupe. La limite était décrite dans `docs/fonctionnel/E05US027.md` § « ce que cette US ne livre pas » et **pas ici** : une dette qui ne vit que dans une fiche de recette est introuvable au `grep`, donc silencieuse au sens du § Dette. | Deux pistes, à trancher : (a) un geste admin explicite « purger les rencontres orphelines de cette phase », confirmé et journalisé ; (b) rendre le `match_numero` **stable** sous recomposition en le dérivant de `(poule, tour, position)` plutôt que d'un compteur global — cela réduit le rayon d'explosion sans le supprimer, la composition changeant de toute façon les paires |
| [DETTE-060](#dette-060--lécran-de-big-shoot-off-nest-pas-branché-sur-la-file-hors-ligne) | conception | mineur | `frontend/src/features/big-shoot-off/SaisieBigShootOff.tsx` et `hooks.ts` (marqueurs `DETTE-060`) | Les deux mutations de cet écran (saisir une volée, valider une manche) partent **en direct**. Toutes les autres surfaces de saisie passent par la file hors-ligne d'E04US009, qui absorbe une coupure LAN et rejoue à la reconnexion | Une coupure pendant une finale fait **perdre la volée en cours**, que le scoreur retape. Borné : un Big Shoot Off dure quelques manches et se joue devant tout le monde, donc la perte est immédiatement visible et courte. Mais c'est un **écart au régime** des autres écrans, et le jour J se joue justement sur un LAN sans internet | **E05US028.** La file est bâtie sur la famille `DuelHorsLigne` : elle transporte un **acte de duel**, avec ses deux duellistes et son `match_numero`. Une volée collective n'en est pas un — l'y faire entrer demanderait d'élargir la file à un second type d'acte, donc de toucher le rejeu, la déduplication et le store, tous livrés et éprouvés | Élargir `fileDuelsHorsLigneStore` à un acte générique (`famille` existe déjà, c'est le discriminant naturel), ou lui adjoindre une file de volées. À faire dans une US front dédiée, avec ses tests de rejeu — pas en fin d'US de moteur |
| [DETTE-059](#dette-059--le-routage-dun-big-shoot-off-ne-donne-aucune-cible) | conception | mineur | `backend/application/routage.py` (`_routage_big_shoot_off`, `ProchaineManche`, marqueurs `# DETTE-059`), `backend/api/v1/routage.py` (`ProchaineMancheReponse`), `backend/domain/contrat_phase.py` (ligne `BIG_SHOOT_OFF`, `plan_de_cibles=AUCUN`) | Le routage sait dire à un finaliste **quelle manche** il tire et **combien sortent**, mais pas **où** : `cible` et `position` sont toujours `null`. Le service ne lit pas le plan de cibles du créneau, et le registre de contrat déclare honnêtement `plan_de_cibles=AUCUN` pour ce type | Borné, et **nommé** : `manque` dit en clair « votre cible n'est pas encore connue pour cette phase » (`P-3`), donc le panneau ne se prend pas pour une panne. Le jour J, le finaliste trouve sa butte par l'écran de salle ou par le juge, comme aujourd'hui — mais le panneau de routage, qui est *fait pour ça*, ne répond qu'à moitié | **E05US028.** Les finalistes sont des inscrits du créneau, donc leur couloir de qualification **existe** en base (`PlacementRepository.par_depart`) — le lire demanderait `PlacementRepository` **et** `InscriptionRepository` en dépendances de `ServiceRoutage`, plus la question métier « une finale spectacle se tire-t-elle sur les cibles de qualification ou sur des cibles dédiées ? », que le CA ne pose pas | Deux marches : (a) relire le plan du créneau et rendre le couloir de qualification, si le club confirme que la finale s'y tire ; (b) sinon, un plan de cibles propre au format (`PlanDeCibles.PAR_FINALISTE`) avec sa table, comme les poules en ont un. Trancher **avant** de coder : (a) est quelques lignes, (b) est une migration |
| [DETTE-061](#dette-061--une-flèche-validée-en-big-shoot-off-est-irrécupérable) | conception | **majeur** | `backend/application/big_shoot_off.py` (note de module et `saisir_volee`, marqueurs `# DETTE-061`), `backend/application/saisie.py` (`corriger_volee`, `_phase_qualification`) | Aucun chemin ne corrige une volée **validée** d'un Big Shoot Off. `saisir_volee` passe par `Serie.saisir_volee`, qui lève `VoleeVerrouillee` sur une volée verrouillée ; le seul appelant de `Serie.corriger_volee` résout sa feuille par `_phase_qualification`, donc jamais celle d'une finale | Une flèche mal saisie et validée en finale est **définitive**, et l'élimination qu'elle a produite avec elle. Le rejeu, lui, est correct : le jour où le geste existera, la correction remontera seule toute la chaîne — c'est le chemin d'entrée qui manque, pas le moteur. Cas rare mais public : la finale se joue devant tout le monde | Revue d'E05US028 (axe C1). ⚠️ **La note de module promettait l'inverse** — « ici la correction remonte d'elle-même toute la chaîne » —, et un scénario de la fiche de recette la décrivait : les deux ont été corrigés le 15/08/2026, la promesse ayant précédé la capacité. Arbitrage du commanditaire du 15/08/2026 : **dette assumée**, correction livrée dans une US dédiée plutôt qu'en élargissant celle-ci | Résorption : `ServiceBigShootOff.corriger_volee` + endpoint admin, avec trace `CORRECTION_SCORE` comme `application/saisie.py`. US front+back dédiée |
| [DETTE-076](#dette-076--le-miroir-front-de-la-répartition-en-poules-recopie-la-règle-du-domaine) | conception | mineur | `frontend/src/shared/phases/poules.ts` (`repartition`, marqueur `// DETTE-076`) ↔ `backend/domain/poule.py` (`nb_poules_pour`, `_serpent`, `_tranches_de_niveau`) | Le front **recopie** la règle de répartition du domaine — nombre de groupes, serpent, et depuis E05US029 le découpage par niveau — parce que l'atelier compose un **format de bibliothèque**, sans tournoi, donc sans lecture serveur possible (`GET /poules/repartition/…` exige un tournoi et une phase posée) | Aucun effet aujourd'hui : **zéro divergence** mesurée sur 6 600 comparaisons (2 modes × tailles 2→12 × effectifs 1→300, vérifié en revue). Le coût est qu'une dérive future produirait un **aperçu faux** — jamais un tournoi faux, le serveur composant seul le jour J. ⚠️ **L'enjeu de l'aperçu a changé avec E05US029** : au serpent, quel groupe gonfle est sans conséquence sportive ; par niveau, l'aperçu annonce des **rangs** (« rangs 1-6, 7-12 ») sur lesquels l'organisateur fonde son choix | E05US023 (miroir avoué en commentaire et en ADR, jamais inscrit), **aggravé et enfin tracé par E05US029**. Motif de l'inscription : « une limite avouée en ADR se trace au registre, l'aveu ne remplace pas la ligne » (`DETTE-053`), et « une dette qui ne vit qu'en commentaire n'est jamais prise » (`DETTE-064`) | Deux pistes : (a) une route d'aperçu **sans tournoi** que l'atelier appelle, (b) assumer le miroir avec un **test de contrat** comparant les deux implémentations sur une grille d'effectifs — la seconde est bien moins chère et suffit à empêcher la dérive |
| [DETTE-078](#dette-078--quatre-réglages-détape-sont-refusés-après-avoir-été-persistés) | conception | mineur | `backend/domain/deroule_etape.py` (`__post_init__`, marqueur `# DETTE-078`) ↔ `backend/domain/phase.py` (les gardes `Configuration*Invalide`) | Les réglages `poules`, `big_shoot_off`, `suisse` et `decoupage` ne sont refusés — quand ils sont posés sur un **type de phase qui ne les lira jamais** — que par `Phase.__post_init__`, c'est-à-dire à `instancier()`. Or l'étape rejoint le déroulé **avant** cette instanciation : une requête invalide laisse donc derrière elle une étape **orpheline**, sans instance de phase, occupant un `ordre` que l'ajout suivant ne réutilise pas | Le déroulé d'un tournoi se troue (rangs 1, 2, 4) **du fait d'une requête que le serveur a rejetée en 422**. L'organisateur voit un rang manquant sans avoir rien composé de tel, et n'a aucune piste : l'erreur qu'il a lue disait que rien n'avait été fait. Faible fréquence — il faut retyper une phase déjà réglée — mais l'effet est durable et silencieux | **E05US027**, relevée par l'axe adversarial de la revue et **reproduite par exécution** (`POST /tournois/1/phases` → 422, puis étape orpheline en base). Le défaut est **hérité** : il existe pour les quatre réglages depuis leurs US respectives. L'US du jour ne l'aggrave pas — elle ferme le cas **neuf** (`colline`, garde portée par `EtapeDeroule.__post_init__` et testée aux deux étages) et inscrit les quatre autres ici plutôt que de les corriger en douce | Hisser les quatre gardes restantes de `Phase` vers `EtapeDeroule.__post_init__`, sur le modèle de celle de `colline`, avec un test d'API « le refus ne persiste rien » par réglage. US `refactor/` dédiée : le geste est mécanique mais touche quatre invariants de composition et leurs tests, et il n'a rien à faire dans une US de format |
| [DETTE-079](#dette-079--le-panneau-de-saisie-dun-format-à-rencontres-est-écrit-trois-fois) | conception | majeur | `frontend/src/features/{poules/SaisiePoules,suisse/SaisieSuisse,colline/SaisieColline}.tsx` — marqueur `// DETTE-079` en tête des trois — **et** le trio `PlanDePoules`/`PlanDeSuisse`/`PlanDeColline` de `frontend/src/features/phases/Phases.tsx` (arbitrage distinct, cf. détail) | La **coquille** d'un panneau de saisie de format à rencontres est écrite trois fois, à l'identique sur ~120 lignes : `usePhases(departId)` → filtre par type → garde de `phaseRetenue` (mêmes trois lignes, même commentaire) → `<select>` de phase → `key={phaseRetenue}` → `isPending`/`isError` → `flatMap(...).find(...)` → garde `desynchronisee` → `<DuelCharge>` → bannière de conflits → mot de la fin → ce qui manque. Seuls diffèrent le vocabulaire (ronde/manche), le préfixe de position et le bloc « au repos » | **Constaté, pas pronostiqué** : `SaisieColline` porte **cinq** commentaires de la forme « correctif de revue d'E05US03x, repris ici d'emblée ». Chacun est un défaut trouvé sur une copie et **recopié à la main** dans la suivante. Le prochain correctif sur l'un des trois écrans devra être porté à trois endroits, et **rien ne rougira** s'il ne l'est qu'à deux — c'est déjà arrivé trois fois dans cette US, sur d'autres miroirs (`MOTEUR_SAIT_JOUER`, `_nb_tours_a_la_composition`, le montage du plan de cibles) | **E05US027** — la 3ᵉ copie est écrite par cette US, et le seuil « dupliquer une 2ᵉ fois et attendre le 3ᵉ cas » de `CLAUDE.md` § Dette est donc franchi **par ce diff**. Relevée par l'axe C2 | ⚠️ **Le remède recommandé est « rien », et c'est défendable** (règle 16, condition (c)) : la liste des formats à rencontres est **close** — `DETTE-066` le constate dans ce même registre, « il n'y a plus de format annoncé pour en faire un 5ᵉ ». La duplication est donc **stable en taille**, et un `<PanneauDeSaisieDeFormat>` paramétré coûterait plus d'indirection qu'il ne rapporte sur un ensemble figé. Ce qui manquait n'est pas le remède mais la **trace** : le signal à surveiller est « toute correction sur l'un des trois se porte sur les deux autres ». Si un 4ᵉ format à rencontres apparaissait, la ligne devient une US `refactor/` |
| [DETTE-080](#dette-080--la-plomberie-détat-des-deux-formulaires-de-composition-est-écrite-deux-fois) | conception | mineur | `frontend/src/features/phases/Phases.tsx` (`FormulairePhase`) ↔ `frontend/src/features/deroule/Deroule.tsx` (le formulaire d'étape) — marqueurs `// DETTE-080` sur les deux | Les deux écrans qui composent des phases — « Phases du tournoi » et « Composer un format » — déclarent **la même plomberie d'état** pour chaque réglage : un `useState` initialisé par un `depuis…()`, une garde de type au moment de construire la charge utile (`estPoules ? vers…() : null`), et une remise à zéro après ajout. Dix réglages y passent aujourd'hui (type, effectif, profondeur, poules, Big Shoot Off, suisse, colline, découpage, arrêts, **titre**). Les **contrôles** eux-mêmes ne sont pas dupliqués : `shared/phases/Reglage*.tsx` est partagé, et c'est la moitié du problème déjà résolue | Aucun effet à l'exécution : les deux copies sont correctes. Le coût est l'**oubli d'un côté**, et il est **déjà arrivé trois fois** — la remise à zéro de la profondeur n'avait été appliquée qu'à un des deux formulaires (relevé en 2ᵉ passe d'E06US006, commentaire encore en place dans `Phases.tsx`), la colline manquait à la liste de reset, et `Deroule.tsx` ne réinitialise toujours **aucun** champ à l'ajout (« l'asymétrie est constatée, pas voulue », dit le code). C'est le pendant **front** de `DETTE-054` : là-bas des DTO jumeaux, ici la plomberie qui les remplit | Antérieure à cette US (les deux formulaires divergent depuis E01US024), **inscrite** par `E16US002` qui y ajoute le 10ᵉ réglage. ⚠️ **Le seuil du remède structurel est franchi depuis longtemps** — dix occurrences, pas trois — mais il se traite en US dédiée, pas en douce dans une US d'IHM (`CLAUDE.md` § Dette). ⚠️ **Ce que cette US a fermé à la place, parce que la preuve y était** : `configInchangee` dans `Phases.tsx`, qui supprime la recopie manuelle de config des widgets à champ unique — trois occurrences réelles et **deux bugs déjà payés** (le barrage effaçait le découpage ; le couple découpage/arrêts partait en 422). Portée locale, une fonction, donc pas d'ADR | US `refactor/` — extraire un `shared/phases/useCompositionDEtape.ts` détenant l'état des dix réglages, leurs gardes de type et leur reset, consommé par les deux formulaires. ⚠️ **Ne pas fusionner les deux écrans** : ils diffèrent réellement de portée (l'un travaille sur un tournoi, l'autre sur une brique de bibliothèque hors tournoi — même distinction que `DETTE-054` fait entre feuilles et racines). C'est la **plomberie** qui est identique, pas les écrans |
| [DETTE-077](#dette-077--une-phase-de-niveau-à-sources-multiples-affirme-un-ordre-que-rien-ne-fonde) | conception | mineur | `backend/domain/poule.py` (`_tranches_de_niveau`, marqueur `# DETTE-077`) ↔ `backend/application/prelevement.py` (`preleves`) | `preleves` range son résultat par `(ordre_source, rang)`. Une phase composée **par niveau** qui prélève dans **deux** phases parallèles compose donc « tous ceux de la source A, puis tous ceux de la source B » : ses groupes reflètent l'**ordre des sources**, pas les niveaux | Le classement annonce le vainqueur de B derrière le dernier de A, au seul motif que B porte un ordre plus grand — bien formé, plausible et faux (la classe d'ADR-0081). ⚠️ **Le garde-fou du même lot y conduit** : le message de `SerpentApresDesPoules` recommande « choisissez par niveau », y compris quand plusieurs sources sont citées. Au serpent l'entrelacement était déjà arbitraire, mais la lecture par blocs n'**affirmait** aucun ordre de niveau ; `_par_groupe`, si | E05US029, relevée en 2ᵉ passe de revue (axes B et C2) : la limite était avouée en docstring et dans « ce que cet ADR ne décide pas », **pas** au registre — le même commit y inscrivait pourtant `DETTE-076` au motif que « l'aveu en ADR ne remplace pas la ligne ». Appliqué à une limite et pas à l'autre | Résorption : soit une anomalie d'avertissement « une phase composée par niveau ne devrait prélever qu'une source », soit savoir **fusionner** deux classements de phases parallèles — ce second point est une règle métier que personne n'a demandée, donc un arbitrage du commanditaire, pas un correctif |
| [DETTE-062](#dette-062--changer-le-format-du-tir-repartitionne-des-volées-déjà-validées) | conception | **majeur** | `backend/application/phases.py` (`ServicePhases.modifier`, marqueur `# DETTE-062`), `backend/application/big_shoot_off.py` (`_scores_par_manche`, `_scores_de_la_manche`, `_prochaine_volee`), **+ E05US035** : `backend/domain/deroule_etape.py` (`_nb_tours_a_la_composition`) **+ E05US027** : la même fonction en dérive désormais `colline.nb_manches` et `frontend/src/features/phases/Phases.tsx` (`ReglageDecoupageDePhase`), marqueurs `# DETTE-062` | Le découpage manche → volées est **dérivé du réglage à chaque lecture** (`(m-1)·V+1 … m·V`) et n'est stocké nulle part. `modifier` réécrit `volees` / `fleches_par_volee` sans aucune garde sur l'existence de séries | Passer `volees` de 1 à 2 **en cours de phase** re-partitionne des volées déjà validées dans d'autres manches : les scores de manche changent, les éliminations se rejouent autrement, **sans le moindre message**. Modifier `fleches_par_volee` compare des volées à 3 flèches avec des volées à 6. C'est une classe de risque **neuve** — la qualification n'a aucun regroupement dérivé ⚠️ **Élargie par E05US035**, et l'élargissement corrige une phrase de cette ligne même : elle affirmait « c'est une classe de risque neuve — **la qualification n'a aucun regroupement dérivé** ». Elle en a un depuis le découpage en tours. Changer `nb_tours` sur une phase **en cours** déplace les frontières de tour : passer de 2 à 4 tours à la 6ᵉ volée rend une pause « après le tour 1 » **immédiatement due**, donc coupe la salle sur la volée en cours ; un écart plus grand fait consommer plusieurs pauses en « manquées » sans qu'aucune n'ait coupé. `ServicePhases.modifier` n'a **aucune garde de statut**, et le contrôle front est rendu quel que soit le statut de la phase. **Deux différences avec le cas Big Shoot Off la rendent moins grave** : aucun **score** n'est re-partitionné (le découpage ne touche que l'avancement — c'est le bénéfice de l'avoir tenu hors du barème, ADR-0093 §1), et un franchissement déjà écrit ne se rejoue pas. Mitigé par la recette, qui dit de régler le découpage **avant** de démarrer la phase — une consigne, pas un garde-fou. *(Relevé par l'axe adversarial en 2ᵉ passe de revue, qui a noté que la fiche fonctionnelle **recommandait activement** le geste.)* | Revue d'E05US028 (axe C2). Non corrigé dans l'US : la garde propre demande de lire les séries de la phase depuis `ServicePhases`, donc une dépendance neuve au `SerieRepository` dans le service de composition — à peser plutôt qu'à câbler en fin d'US | Résorption : refuser la modification de `volees` / `fleches_par_volee` d'un Big Shoot Off dès qu'une `Serie` existe sur une de ses phases ; les autres champs (`eliminations`, options) restent libres, ils ne déplacent aucune borne. Pendant de DETTE-057 côté **format du tir** au lieu de **population** |
| [DETTE-064](#dette-064--létape-de-déroulé-se-recopie-champ-par-champ-dans-les-décors-de-test) | technique | majeur | `backend/tests/conftest.py` — `poser_phase_sql` **et** `poser_phase_factice`, marqueurs `# DETTE-064` | Les deux helpers construisent une `EtapeDeroule` en **recopiant les champs de la `Phase` un à un**. Rien ne rougit quand on en oublie un : le décor pose alors une phase **non réglée** là où le test croit avoir posé une phase réglée | Aucun effet en production — c'est du décor de test. Le coût est un **faux négatif coûteux** : le test échoue en `phase_pas_reglee` sur une phase parfaitement réglée, et l'on cherche le défaut dans le service. ⚠️ **Le piège s'est déclenché trois fois de suite**, à chaque réglage neuf | **E05US023** (poules, 1ʳᵉ), **E05US028** (Big Shoot Off, 2ᵉ), **E05US026** (système suisse, 3ᵉ), **E05US027** (colline, 4ᵉ). ⚠️ **La 4ᵉ confirme la prédiction sans exception** : le réglage de la colline a été oublié dans les **deux** helpers, et **onze** tests d'API ont échoué en `phase_pas_reglee` sur une phase parfaitement réglée — c'est en cherchant la cause qu'on est retombé sur le commentaire qui l'annonçait. Quatre réglages neufs, quatre oublis, et à chaque fois c'est un test d'**API** qui a rattrapé, jamais une relecture. Le piège ne se déclenche donc pas « parfois » : il se déclenche **toujours**. ⚠️ **E05US033 n'en ajoute aucune**, et c'est un effet de son périmètre final : les arrêts ne se recopient pas sur `Phase` (ADR-0091 §2, cycle d'import), donc les helpers n'ont aucun champ de plus à recopier — un décor d'arrêts écrit l'étape lui-même. Un état intermédiaire de l'US annonçait une 4ᵉ occurrence (le réglage de découpage) ; il est sorti du périmètre le 19/08/2026 et le registre est revenu à trois. Le commentaire du helper avait **prédit** la 3ᵉ mot pour mot (« il le sera à chaque réglage neuf ») sans qu'elle soit tracée ici : une dette qui ne vit qu'en commentaire n'est jamais prise. Le seuil « 3ᵉ occurrence réelle » de `CLAUDE.md` est atteint **sur preuve** | Résorption : une fabrique unique **du domaine** — `EtapeDeroule.de_phase(phase)` — que les deux helpers appellent, et qui vit à côté d'`EtapeDeroule.instancier` (son inverse). La colline (`E05US027`) en a fait une 4ᵉ. ⚠️ **Et le remède ne couvrira pas tout** : `EtapeDeroule.de_phase(phase)` ne peut pas recopier un champ que `Phase` ne porte **pas**, ce qui est le cas des `arrets` par conception (ADR-0091 §2, cycle d'import). La fabrique règle la classe de défaut « champ oublié », pas la classe « champ absent du miroir » — à savoir avant de la croire complète. US `refactor/` dédiée |
| [DETTE-065](#dette-065--le-garde-dautorisation-des-routeurs-décriture-est-recopié-sept-fois) | conception | **majeur** | `backend/api/v1/{saisie,saisie_duels,forfaits,poules,big_shoot_off,suisse,colline}.py` — `_exiger_meme_tournoi` (marqueur `# DETTE-065`) et `_cle_idempotence` | Les deux fonctions sont écrites **à l'identique** dans sept routeurs d'écriture. `_exiger_meme_tournoi` **est** le contrôle qui empêche un scoreur d'écrire hors de son tournoi (403 `scoreur_hors_tournoi`) | Aucun effet aujourd'hui : les sept copies sont correctes. Le coût est qu'un **8ᵉ routeur d'écriture qui l'oublierait ne ferait rougir personne** — même angle mort que `DETTE-054` pour les DTO jumeaux, mais appliqué à une **autorisation** et non à un champ de composition. C'est ce qui le rend majeur et non mineur | Les cinq premières copies datent d'E04US002 → E05US028 ; la **6ᵉ** est ajoutée par **E05US026** et relevée en revue ; la **7ᵉ** par **E05US027**. ⚠️ **Et cette 7ᵉ est précisément celle que la ligne annonçait** — « un 7ᵉ routeur d'écriture qui l'oublierait ne ferait rougir personne ». Elle n'a pas été oubliée, mais rien n'y a veillé : c'est le commentaire du routeur voisin qui l'a rappelée à l'auteur, pas un garde-fou. Le contraste relevé **à E05US026** y est net : cette branche-là consacrait un ADR entier à un remède structurel sur sa 3ᵉ occurrence pendant qu'elle ajoute la 6ᵉ d'un autre, en silence | Résorption : `exiger_meme_tournoi` rejoint `api/dependances.py`, où vit déjà `exiger_scoreur` ; la fabrique de clé d'idempotence rejoint un `api/v1/_idempotence.py`. US `refactor/` dédiée — **pas** dans une US de moteur |
| [DETTE-066](#dette-066--le-bot-de-simulation-se-retire-des-formats-à-la-main) | conception | mineur | `backend/application/simulation_format.py` (`_TYPES_DEROULABLES`, marqueur `# DETTE-066`), `backend/bootstrap/composition.py` (`fabriquer_harnais_simulation`) | `_TYPES_DEROULABLES` part de la table **dérivée** `TYPES_JOUES` et lui **retranche à la main** les formats que le bot ne sait pas jouer. Les deux tables répondent à des questions différentes — « un service de production déroule-t-il ce type ? » contre « le **bot** sait-il le jouer ? » — et rien ne le garantit | Un format rendu jouable sans être retiré de cette liste fait annoncer `joue=True, 0 tour, 0 duel` à l'atelier : des zéros lus comme un **constat**, et le bandeau « le moteur ne sait pas encore dérouler ce type » disparaît. C'est arrivé | **4ᵉ occurrence** : poules (E05US023), Big Shoot Off (E05US028), système suisse (**E05US026**, oubli relevé en revue), colline (**E05US027**). ✅ **La 4ᵉ n'a pas été un oubli, et c'est la nouveauté** : le garde-fou posé en E05US035 (`test_le_bot_de_simulation_ne_pretend_pas_jouer_ce_qu_il_ne_sait_pas`) est **tombé dès la bascule du registre de contrat**, avant qu'une seule ligne de `simulation_format.py` soit touchée. Le retrait a donc été posé en connaissance de cause au lieu d'être découvert en salle. La dette s'élargit d'un terme mais **cesse de s'aggraver en risque** : ce qui manquait n'était pas le remède, c'était la détection. Le seuil du remède structurel de `CLAUDE.md` est atteint **sur preuve** | Résorption : une capacité `simulable_par_le_bot` au registre de contrat (`domain/contrat_phase.py`), dont `_TYPES_DEROULABLES` dérive — ou, si le bot doit vraiment apprendre les formats, une US qui construit les services manquants dans le harnais. À trancher en US dédiée. ⚠️ **Le pronostic « la colline en fera un 4ᵉ retrait sinon » s'est vérifié** — elle l'a fait. Il n'y a plus de format annoncé pour en faire un 5ᵉ : les quatre types à rencontres y sont tous. La dette est donc **stable en taille** désormais, ce qui retire l'argument d'urgence sans retirer le défaut |
| [DETTE-058](#dette-058--le-big-shoot-off-ignore-le-grain-de-validation-réglé-sur-sa-phase) | conception | mineur | `backend/application/big_shoot_off.py` (note de module et `valider_manche`, marqueurs `# DETTE-058`), `backend/domain/phase.py` (`_GRAINS_ADMIS`) | `_GRAINS_ADMIS` autorise `FIN_DE_SERIE` **et** `TOUTES_LES_N_VOLEES` sur un Big Shoot Off, donc l'organisateur peut régler l'un ou l'autre à l'atelier. Le service, lui, **impose** `toutes_les_n_volees(V)` — le seul grain qui permette de valider manche par manche — et ne lit jamais `phase.validation` | Aucun effet visible : le grain imposé est le seul jouable. Un Big Shoot Off réglé « en fin de série » serait **injouable** — on ne saurait qui est éliminé qu'après la dernière manche, c'est-à-dire jamais, la dernière manche dépendant des précédentes. Le défaut est donc un **réglage qui ment** : l'atelier offre un choix sans effet, et l'organisateur qui le pose croit avoir changé quelque chose | **E05US028.** Honorer le réglage aurait bloqué la salle ; le refuser à l'atelier demande de retirer `FIN_DE_SERIE` de `_GRAINS_ADMIS` pour ce type, or ce dictionnaire est un invariant de `domain/phase.py` partagé avec la qualification et vérifié par `test_domain_phase` — un changement de contrat sur une US livrée, pas un cavalier dans une US de moteur | Résorption : restreindre `_GRAINS_ADMIS[BIG_SHOOT_OFF]` à `TOUTES_LES_N_VOLEES`, **ou** faire du grain une lecture dérivée du réglage pour ce type (la cadence *est* `volees`, il n'y a rien à choisir). La seconde piste est la plus honnête : elle supprime le réglage au lieu de le contraindre |
| [DETTE-044](#dette-044--tournoiid-et-departid-sont-le-même-type-pour-mypy) | conception | majeur | `backend/domain/tournoi.py` (`TournoiId`), `backend/domain/depart.py` (`DepartId`), et tous les alias d'identifiant du projet (`ArcherId`, `PhaseId`, `CategorieId`…) | Les identifiants sont des **alias** (`TournoiId = int`), pas des types distincts. Passer un identifiant de tournoi là où on attend un départ **typecheck parfaitement** | Démontré à l'échelle pendant E01US025 : la bascule de portée n'a produit que **10 erreurs mypy** ; renommer les méthodes de port (`par_tournoi` → `par_depart`) en a révélé **157 de plus** — toutes des appels compilables et faux. Sans ce renommage, le refactor aurait été « vert » et cassé | Résorption : `NewType("DepartId", int)` sur les identifiants. Invasif (tout le dépôt), mais **mécanique** et guidé par mypy. À faire en US dédiée. Le garde-fou `tests/test_portee_sportive.py` couvre le cas du départ ; il ne couvre pas les autres paires. **Élargie par E05US025** (relevé de revue) : la bascule de `SerieRepository.par_archer` de `tournoi_id` à `phase_id` reposait explicitement sur « un appelant resté à la maille tournoi doit cesser de compiler » — pari **faux**, 9 sites manqués en silence, dont la lecture de la grille de saisie et les trois gardes « cet archer a-t-il tiré ? ». Mesure d'atténuation prise en attendant le `NewType` : les décors de tests ne font plus coïncider `tournoi_id` et `phase_id` (séquence de `FauxPhaseRepository` décalée à 100, `_PHASE_TEST` distinct, décors SQL à deux créneaux), pour qu'une confusion **échoue** au lieu de passer |
| [DETTE-045](#dette-045--le-palmarès-et-la-simulation-ne-voient-que-le-premier-départ) | conception | majeur | `backend/application/palmares.py` (`_premier_depart`), `backend/application/simulation.py`, `backend/application/simulation_format.py` | Le classement vit **par départ** ([ADR-0075](adr/0075-le-depart-est-la-portee-sportive.md)), mais le palmarès et le rejeu de simulation sont restés à la maille tournoi : ils prennent le **premier créneau** et ignorent les autres | Sur un tournoi multi-créneaux, le palmarès n'affiche que le podium du matin ; les autres départs n'ont **aucun** palmarès. Silencieux — rien à l'écran ne dit que la vue est partielle | **Arbitrage rendu le 07/08/2026** : *« juxtaposé — 4 départs = 4 podiums »*. Il n'y a donc **aucune** agrégation inter-départs à écrire, et la résorption n'est plus bloquée. Planifiée en **E06US009** |
| [DETTE-047](#dette-047--les-forfaits-de-qualification-pendent-tous-à-la-phase-du-premier-créneau) | conception | majeur | `backend/application/forfaits.py` (`_phase_qualification`), `backend/application/classements.py` (`_forfaits_qualif`), `backend/application/portee.py` (`qualification_du_tournoi`), **+ E05US035** : `backend/application/saisie.py` (`_volees_du_plus_lent`, marqueur `# DETTE-047`) | Déclarer un forfait de qualification l'attache à la phase rendue par `qualification_du_tournoi`, c'est-à-dire à celle du **premier** créneau, quel que soit le créneau où l'archer tire. La lecture emprunte le même raccourci : l'affichage est donc **cohérent par accident**, pas juste ⚠️ **E05US035 en hérite un TROISIÈME effet, et il va dans la direction dangereuse** (relevé en 2ᵉ passe de revue) : `ServiceSaisie._volees_du_plus_lent` doit lire les forfaits par les deux chemins pour ne pas geler une phase (cf. `DETTE-022`), donc il importe l'effet n° 2 — un archer engagé sur **deux** créneaux et déclaré forfait sur l'un est retiré du plateau de **l'autre**, où il tire réellement. Le plus lent devient alors quelqu'un d'autre et la phase avance **trop tôt** : la pause peut tomber pendant qu'il tire, exactement ce que toute E05US035 est construite pour éviter. Le premier jet du lecteur avait le défaut **opposé** (phase gelée par un forfait invisible) ; l'union échange l'un contre l'autre, et c'est le moins mauvais des deux — un archer double-engagé est rare, un forfait ne l'est pas — mais cela **cesse d'être un inconfort de classement** pour devenir un risque d'exploitation. | Deux effets réels. (1) `forfait.phase_id` est en `ON DELETE CASCADE` et `PRAGMA foreign_keys` est actif : **supprimer le créneau du matin efface les forfaits de tous les autres créneaux**, silencieusement. (2) Un archer engagé sur deux créneaux (cas soutenu, cf. DETTE-046) déclaré forfait l'après-midi est **relégué aussi le matin** — le filtre par archer ne discrimine pas le départ | **Découvert à la 2ᵉ revue d'E01US025** (axes C1 et adversarial), sur le module que l'US crée justement pour **concentrer** la portée tournoi résiduelle. Non traité dans l'US : la résorption change la signature des deux gestes de forfait **et** la route `/api/v1/forfaits`, donc le front — un périmètre d'US à part entière | Résorption : `declarer_en_qualification` / `annuler_en_qualification` prennent un `depart_id` et résolvent par `par_depart_et_type(depart_id, QUALIFICATION)` ; route portée au créneau. **Même famille que DETTE-045 et DETTE-046** — une portée restée au tournoi alors que la réalité est le créneau ; à traiter dans le même lot. Marqueurs `# DETTE-047` sur les deux résolutions |
| [DETTE-048](#dette-048--le-module-qui-concentre-la-portée-tournoi-nest-ni-testé-ni-surveillé) | technique | majeur | `backend/application/portee.py` (module entier), `backend/tests/test_portee_sportive.py` (balayage AST) | `portee.py` est le **seul** endroit où la portée tournoi survit délibérément, et il alimente neuf services. Il n'est importé par aucun test. Il échappe de surcroît au garde-fou de portée : le balayage AST reconnaît des **noms de variables** (`phase`, `barrage`, `qualification`) et ne voit pas un `tournoi_id` passé en **paramètre** | Le point de concentration du raccourci est le seul à n'être ni testé ni surveillé — et c'est de lui que sont sortis les deux défauts de portée trouvés en 2ᵉ revue (DETTE-047, et les verdicts de barrage corrigés dans l'US). Rien n'empêche le dixième appelant de refaire la même erreur de maille | Relevé à la 2ᵉ revue d'E01US025 (axe adversarial). Non traité : l'US corrigeait les appelants fautifs, pas l'outillage du garde-fou | Résorption : un `tests/test_portee.py` sur les trois fonctions, **décor à deux créneaux** (seul décor capable de voir la maille — cf. `tests/test_portee_deux_creneaux.py`, livré par cette US), plus l'extension du balayage AST aux **noms de paramètres**. Marqueur `# DETTE-048` en tête de `portee.py` |
| [DETTE-049](#dette-049--les-doublures-de-phase-ont-un--mode-indulgent--qui-nassemble-pas) | technique | mineur | `backend/infrastructure/memory/repositories.py` (`InMemoryPhaseRepository._assemble`), `backend/tests/conftest.py` (`FauxPhaseRepository`) | Sans magasin de départs **et** de déroulés, les deux doublures rendent les phases **telles que posées** au lieu d'assembler leur définition depuis le déroulé. Le câblage réel (`bootstrap/composition.py`) passe toujours les deux ; la majorité des décors de test n'en passe qu'un | Une doublure qui répond autrement que la production peut **consacrer** un bug au lieu de l'attraper — précisément le mode de panne que l'US a rencontré deux fois. Aggravant : la concession vit dans un module de **production**, pas seulement dans `conftest` | Introduite par E01US025 (séparation déroulé / avancement, [ADR-0076](adr/0076-un-deroule-defini-une-fois-un-avancement-par-depart.md)), tracée sur relevé de revue (axe C2 en **majeur**, axe adversarial en **suggestion** — arbitré **mineur** : la branche est morte au câblage réel, et le contrat est vérifié par `test_conformite_ports_memoire` sur la variante câblée) | Résorption : rendre `departs`/`deroules` **obligatoires** dans les deux classes et corriger les décors (~20 lignes mécaniques), ou les fabriquer en interne par défaut. À faire dans l'US qui touchera ces décors, pas en propre. Marqueur `# DETTE-049` sur `_assemble` |
| [DETTE-043](#dette-043--la-charte-impose-inter-lapplication-ne-lembarque-pas) | conception | mineur | `frontend/src/index.css` (`--sans`) | `DV-07` impose **Inter**. La pile de polices la déclare en tête, mais **aucun fichier de police n'est livré** : sur un poste qui ne l'a pas installée, le navigateur retombe silencieusement sur `Segoe UI` ou la police système | Le jour J tourne **sans internet** : aucune tablette ne pourra la télécharger. Le rendu réel sera donc, en pratique, celui de la police système sur la quasi-totalité du parc — proportions justes, dessin des lettres faux. Aucun effet fonctionnel, mais la charte est **déclarée satisfaite alors qu'elle ne l'est pas** | **E17US001** (05/08/2026, [ADR-0074](adr/0074-les-maquettes-font-foi-et-la-charte-mesuree-est-la-source-des-jetons.md)) : la charte a été posée sans embarquer la police | **E17US005** (spécifiée le 08/08/2026, 🔒 bloquée sur arbitrage) — embarquer les `.woff2` d'Inter dans `frontend/public/` avec un `@font-face` local. **Bloqué sur arbitrage** : c'est un ajout d'actif au dépôt (règle 11) — ~100 à 300 Ko, licence OFL —, donc une décision du commanditaire, pas de l'implémenteur |
| [DETTE-067](#dette-067--le-javascript-de-latlas-nest-ni-typé-ni-linté) | technique | mineur | `atlas/statique/` — **1 837 lignes de JS** (`pages.js` 1 656, `coquille.js` 181) plus 530 de CSS, soit **2 367 lignes** — élargie par E00US019 (+ 420 lignes : vue d'avancement, graphe des epics, fiche d'US) puis par E00US020 (+ 353 lignes de JS, + 371 avec le CSS : carte du code, schéma des couches, matrice, ports) ; marqueurs `DETTE-067` en tête des trois fichiers | Le JavaScript du site de l'atlas n'est ni typé, ni linté, ni formaté automatiquement. `eslint` et `prettier` sont cadrés sur `^frontend/` (hooks pre-commit) et `working-directory: frontend` (CI) : `atlas/`, à la racine, leur est invisible | **Borné.** Le site ne touche aucune donnée du tournoi — il lit du généré et affiche du texte : une régression y dégrade la lecture d'une documentation, jamais un score. Les trois fautes invisibles en développement (`fetch()` ou module ES, mortels en `file://` ; ressource externe, alors que le jour J est hors ligne ; `viewport` manquant) sont couvertes par `backend/tests/test_atlas_site.py`. Ce qui reste à découvert est le **rendu** : rien ne garantit qu'une page est lisible à 360 px | E00US018 ([ADR-0086](adr/0086-un-atlas-genere-le-depot-cartographie-sans-dependance.md)) — assumé au titre de la règle 12 : rallier ces 700 lignes demanderait soit d'étendre l'outillage du front à un dossier qui n'en est pas, soit une seconde chaîne Node sans build | **Déclencheur franchi le 16/08/2026 par E00US020** (2 367 lignes pour un seuil de 2 000) : la résorption est **ouverte** — `E00US026`, comme le prévoyait la clause « la prochaine US qui touche `atlas/statique/` ouvre la résorption, elle ne relève pas le seuil ». Déclencheurs d'origine : `atlas/statique/` dépasse **2 000 lignes**, **ou** un défaut de rendu échappe deux fois. ⚠️ Le seuil initialement inscrit (« ~1 000 lignes ») était **déjà franchi le jour de l'inscription** — le volume avait été estimé à ~700 lignes pour 1 550 réelles. Un déclencheur atteint à la rédaction n'en est pas un : il ne se déclenchera jamais *plus tard*, et il neutralise l'entrée. Relevé en revue, corrigé ici. Sortie la moins coûteuse : élargir les patrons existants (`^(frontend|atlas)/`), pas introduire un build |
| [DETTE-068](#dette-068--la-grille-de-revue-et-son-orchestration-vivent-dans-sept-fichiers-sans-garde-fou-de-cohérence) | conception | mineur | `.claude/commands/revue-us.md` et `.claude/agents/revue-axe-{a,b,c1,c2,d}.md` + `porte-mecanique.md` — marqueur `DETTE-068` dans la commande, § « Concordance des numéros » | ADR-0013 décision 8 sort les grilles de la commande vers sept fichiers versionnés. La commande garde l'orchestration, le préambule et la table de décharge ; chaque agent porte sa grille. **Rien ne vérifie mécaniquement que les deux restent d'accord** — la numérotation des règles, la liste de suspension, les renvois croisés sont tenus à la main | **Réel, et déjà constaté trois fois au commit d'introduction** : `docs/adr/0075:220` et `docs/dette.md:7` pointaient encore vers l'ancien emplacement de `12-ADR` et des règles 14-15 ; et `revue-axe-a.md` omettait `porte-mecanique.md` de sa liste de suspension — le fichier même qui suspendait la décharge sur ce lot. Un renvoi mort se lit comme une preuve : c'est le défaut « ADR creux » que la revue existe pour trouver, appliqué à sa propre procédure | `chore/agents-dedies-revue` (16/08/2026), ADR-0013 décision 8 — assumé au titre de la règle 12 : un test qui compare deux textes en prose coûterait plus que le mal, puisque chaque agent reformule légitimement | **La prochaine divergence constatée ouvre la résorption** — pas « la troisième » : le compte de trois est atteint à la rédaction, et un déclencheur déjà franchi ne se déclenche jamais *plus tard* (leçon de DETTE-067, corrigée ici à l'inscription). Piste la moins chère, sur preuve du code d'aujourd'hui : élargir `_RACINES_DE_CODE` de `backend/atlas/sources/adr.py` à `.claude/` — le contrôle `portage-inexistant` vérifierait alors l'**existence** des fichiers nommés par les tables « Porté dans le code par », ce qu'il ne fait pas aujourd'hui (4 des 7 lignes d'ADR-0013 lui sont invisibles). Ne couvre pas le contenu |
| [DETTE-069](#dette-069--un-sous-agent-peut-écrire-dans-larbre-et-pousser) | technique | **majeur** | `.claude/settings.json` (`deny`), `.claude/agents/*.md` (champ `tools`) — marqueur `DETTE-069` dans `revue-us.md` § « Où vivent les grilles » et dans `porte-mecanique.md` | Les six agents du dispositif de revue n'ont ni `Edit` ni `Write`, mais gardent **`Bash` non scopé**. Le `deny` versionné ne refuse ni `git commit`, ni `git push`, ni `sed -i`, ni une redirection. « Tu ne modifies aucun fichier » est donc une **consigne de prompt**, pas une contrainte. **Élargie le 17/08/2026** : `.claude/settings.local.json`, non versionné donc jamais relu en revue, ouvre son `allow` sur **`Bash(*)`** et `PowerShell(*)` — les 28 entrées restreintes de `settings.json` sont **court-circuitées**, seul le `deny` versionné survit (il l'emporte sur l'`allow`) | **Constaté, pas théorique.** Le 17/08/2026, l'agent `porte-mecanique` (un `haiku`), appelé pour exécuter la porte, a corrigé un ADR, régénéré l'atlas, lancé `ruff format`, puis `git add` / `commit` / `push` — **22 fichiers**, dont l'intégralité des correctifs de revue en cours, sous un message qui n'en décrivait que deux et dont le justificatif était inventé (`e8d3258`). Ses corrections étaient justes ; le geste ne l'était pas. Le dommage principal n'est pas le fichier touché mais la **traçabilité détruite** : `git add -A` ramasse le travail d'autrui, et le message devient faux sans que personne n'ait menti | [ADR-0013](adr/0013-conduite-de-la-revue-d-us.md) décision 8 (16/08/2026) — l'axe adversarial de sa propre revue avait décrit le scénario mot pour mot quelques heures avant qu'il ne se produise | **Essai joué et conclu le 17/08/2026 : la piste du `Bash` scopé est morte.** Un agent déclaré `tools: Read, Bash(git log:*)` a exécuté `git status` (hors scope mais dans l'`allow` — seul le frontmatter aurait pu la refuser), `git count-objects` (hors `allow` et hors `deny`), et surtout un `touch` en **écriture**, fichier vérifié sur le disque. Le spécificateur est accepté sans erreur et **ignoré en silence**, en lecture comme en écriture. Scoper les six agents ne donnerait qu'un garde-fou de **façade** — pire que rien, puisqu'on cesserait de surveiller ce qui ne l'est pas. Il ne reste que le pansement (`git status` après chaque sous-agent dans `/revue-us`) : **la dette reste ouverte, sans piste de durcissement mécanique**. Deux passes, dont une non concluante, et l'enseignement de méthode qui en sort (sonder le geste que le garde-fou est censé empêcher ; énumérer *toutes* les couches qui peuvent dire oui) sont en section. Agent d'essai supprimé. Arbitrage laissé ouvert, **par poste donc hors dépôt** : remettre ou non `Bash(*)` dans `settings.local.json` |
| [DETTE-071](#dette-071--lavancement-dun-créneau-sert-les-réglages-complets-à-un-anonyme) | conception | mineur | `backend/api/v1/phases.py` (`lister_avancement`, `PhaseReponse` **et**, depuis E05US035, `lister_phases`, `EtapeReponse`), consommée par `frontend/src/features/en-cours/VueEnCours.tsx` — appli publique **et** écran de salle, via `frontend/src/features/phases/hooks.ts` (`useAvancementPhases`), qui rend le type `Phase` **entier** — et par l'écran de pilotage | `GET /api/v1/departs/{depart_id}/phases` est une **lecture ouverte** (E10US001) qui rend `PhaseReponse` **entière** : `sources`, `effectif`, `profondeur`, `poules`, `suisse`, `big_shoot_off`, `barrage_jusqu_au`, et depuis **E05US035** `decoupage`. Un anonyme sur le réseau lit donc les **réglages d'atelier** d'un créneau — la liste de sortants d'un Big Shoot Off, le nombre de rondes d'un suisse, la taille visée des poules — là où l'écran public n'a besoin que de `id`, `ordre`, `type`, `statut` | **Faible, et ce n'est pas un secret** : ces réglages sont annoncés en salle et lisibles sur le papier du greffe ; rien ici n'est une donnée personnelle ni un jeton. Le coût est celui d'une **surface d'API plus large que son usage** : chaque champ ajouté à `PhaseReponse` part au public sans décision, et c'est le mécanisme qui a produit trois défauts déjà corrigés ailleurs dans ce registre. À surveiller le jour où une phase portera un réglage qu'on ne veut pas annoncer. ⚠️ **E05US035 y ajoute `decoupage` sur les DEUX routes ouvertes** — `PhaseReponse` (avancement d'un créneau) et `EtapeReponse` (déroulé d'un tournoi, `GET /tournois/{id}/phases`, sans garde admin), cette dernière recevant aussi **`nb_volees`** (le nombre de volées du barème). Exposition **assumée et décidée** pour les trois champs — le nombre de tours d'une qualification est déjà annoncé publiquement par l'avancement (« tour 1 sur 2 »), donc le champ ne révèle rien de neuf. C'est la **décision** qui manquait, et que le marqueur réclame. ⚠️ **E05US027 y ajoute `colline`** (`nb_manches`, `portee_de_defi`) sur les **deux** mêmes routes ouvertes. Exposition **assumée** : `GET /api/v1/colline/etat/` est déjà une route ouverte par décision de cette US et sert ces deux champs, et `VueCollinePublique` annonce le nom du format au public — le champ ne révèle donc rien de neuf. La ligne est élargie plutôt que le champ fermé, mais elle est élargie **explicitement**, ce qui est le geste que cette dette réclame : le manquer, c'est reprendre le mécanisme même qu'elle décrit (« chaque champ ajouté part au public **sans décision** ») | **Préexistant** — la route est publique depuis sa création (E01US025, ADR-0075). Inscrit ici le 18/08/2026 à la demande de l'utilisateur, après que la revue d'**E05US031** l'a relevé deux fois (axes C2 et adversarial) : l'US en fait un consommateur **public** de plus, donc un motif de moins pour le laisser en l'état. L'écart était honnêtement signalé en [ADR-0089 § Conséquences] et dans l'en-tête de `phases-publiques/api.ts`, mais **absent du registre** — donc introuvable par `grep` à qui cherche la dette, ce que le § Dette de `CLAUDE.md` compte comme dette silencieuse | Dériver un **DTO public étroit** (`PhaseAvancementReponse` : `id`, `ordre`, `type`, `statut`) servi par cette route, et réserver `PhaseReponse` aux lectures admin — le patron est déjà celui d'`EtatPubliqueReponse` (E05US031, ADR-0089 §5). **US de résorption : `E10US009`.** Ne pas simplement ajouter une garde admin : l'appli publique et l'écran de salle en dépendent, les fermer casserait un usage réel |

## Dette résorbée

| ID | Nature | Portée | Soldée par |
|---|---|---|---|
| DETTE-056 | conception | `frontend/src/features/scoreur-session/EspaceScoreur.tsx`, `frontend/src/features/saisie-duels/SaisieDuels.tsx`, `frontend/src/features/poules/SaisiePoules.tsx`, `frontend/src/features/big-shoot-off/SaisieBigShootOff.tsx`, `frontend/src/features/departs/hooks.ts` (`useCreneauDesDuels`) | **E05US030** (16/08/2026) — le choix de créneau est **remonté dans `EspaceScoreur`**, qui le rend une fois et le passe en prop aux **quatre** panneaux ; les trois marqueurs `# DETTE-056` sont retirés. Résorbée **dans** l'US qui l'aurait aggravée : le système suisse portait le compte à quatre sélecteurs, donc à six couples désaccordables, et c'était la **4ᵉ** occurrence — bien au-delà du seuil « attendre le 3ᵉ cas ». ⚠️ **Pas dans `useSessionScoreurStore`**, l'autre voie que la ligne proposait : ce store est persisté au `localStorage`, donc le créneau aurait survécu à la fermeture de l'onglet et rouvert la journée du lendemain sur le départ de la veille. Le gel voulu dure une session d'écran, pas une nuit. ⚠️ **Résorbée pour les panneaux de SAISIE**, et le panneau « Forfaits — qualification » garde le sien : il est volontairement indépendant (un abandon se prononce parfois sur un archer d'un autre créneau) et son défaut n'est même pas le même. La revue a relevé que trois artefacts affirmaient « un seul sélecteur » alors que l'écran en montre deux dès le premier rendu ; le correctif a été de **nommer** le second (« Départ des forfaits ») plutôt que de supprimer une capacité voulue. L'invariant est **tenu par un test** (`EspaceScoreur.test.tsx` : un seul sélecteur « Départ », et les quatre panneaux de saisie reçoivent la même valeur) — ⚠️ **et ce test a lui-même dû être corrigé** : une première version doublait le panneau des forfaits à `null`, si bien que l'assertion passait *parce que le seul contre-exemple avait été retiré du DOM* — les cas correspondants ont été **déplacés** depuis `SaisieDuels.test.tsx`, où ils ne pouvaient plus rien voir. ⚠️ Défaut constaté au passage, sans rapport avec la résorption : cette entrée n'a **jamais eu de section de détail**, son ancre était morte depuis sa création |
| [DETTE-046](#dette-046--un-archer-inscrit-sur-deux-départs-ne-peut-avoir-quune-série) | conception | table `serie`, `backend/domain/serie.py`, `backend/infrastructure/db/repositories/tir.py` | **E05US025** (09/08/2026, [ADR-0082](adr/0082-plusieurs-qualifications-dans-un-meme-deroule.md)) — **sans US dédiée**. La feuille de marque devait pendre à sa **phase** pour qu'un archer engagé dans deux qualifications y tienne deux feuilles ; or la phase **subsume** le départ (elle lui appartient depuis ADR-0075). La clé `UNIQUE(phase_id, archer_id)` règle donc le cas de cette dette *et* celui des qualifications multiples, avec **un** champ au lieu des deux que la résorption proposée (`Serie.depart_id`) aurait ajoutés à deux mailles. Migration `0044`, avec reprise des données. Marqueurs retirés de `models.py` |
| [DETTE-063](#-dette-063--le-système-suisse-noccupe-aucun-couloir-résorbée-le-16082026) | conception | `backend/domain/contrat_phase.py`, `backend/application/suisse.py`, `backend/domain/placement_par_bloc.py` | **E05US026** (16/08/2026) — **ouverte et refermée dans la même US**, en deux temps : le commanditaire a tranché le renommage du placement par bloc (migration `0046`), ce qui a libéré le chemin, puis `ServiceSuisse.regenerer_plan` a posé le bloc unique et `plan_de_cibles` est passé à `PAR_BLOC_DE_COULOIRS`. La section de détail est **conservée** : le raisonnement « pourquoi un seul bloc » se reposera à la colline (`E05US027`) |
| [DETTE-034](#dette-034--une-phase-de-consolation-serait-mal-classée-au-palmarès) | conception | `backend/domain/palmares.py` (`calculer_palmares`, `ResultatPhase.rang_premier`), `backend/application/prelevement.py` (`tranche`) | **E05US020** (03/08/2026, [ADR-0068](adr/0068-le-moteur-consomme-les-prelevements-declares.md) §5). La dette était assumée « impact nul, aucun moteur ne consomme les prélèvements » — **l'US qui la résorbe est celle qui invalidait cette prémisse**, et la revue adversariale l'a mesuré : le vainqueur d'une consolante passait 1ᵉʳ du palmarès, sur un déroulé que `verifier_sequence` accepte. `ResultatPhase` porte désormais le **premier rang du tournoi** que sa phase dispute, et l'ordre se lit sur le rang **absolu** au lieu de l'`ordre` de phase. Le test de caractérisation `test_la_phase_la_plus_tardive_l_emporte` a échoué comme prévu et ne garde que ce qui était vrai — la règle par archer |
| [DETTE-030](#dette-030--lunion-typephase-est-dupliquée-côté-front) | technique | `frontend/src/features/phases/api.ts`, `frontend/src/features/patrimoine/api.ts`, `features/phases/Phases.tsx`, `features/patrimoine/format.ts` | **E01US024** (01/08/2026) — l'écran « Composer un déroulé » est la **3ᵉ** feature portant l'union, exactement le déclencheur que la dette s'était fixé. Extraction dans `frontend/src/shared/phases/catalogue.ts` (`TypePhase`, `NatureSource`, `IssueTour`, `LIBELLE_TYPE`, `AIDE_TYPE`, `TYPES_SANS_CLASSEMENT`) ; les deux `api.ts` **ré-exportent** d'ici, aucun import existant ne casse. Deux domiciles au lieu de trois ; l'exigence d'exhaustivité des `Record` est **conservée** — elle protège l'autre moitié du risque (l'oubli d'un type à l'usage, que l'extraction ne voit pas). Marqueurs `# DETTE-030` retirés |
| [DETTE-015](#dette-015--modèle-de-source-de-phase-minimal-et-provisoire) | conception | `backend/domain/phase.py` (`SourcePhase`, `SequencePhases`), `domain/format_tournoi.py` (`ModelePhase.sources`), les `config` JSON de **`phase` et `format_tournoi`**, `api/v1/phases.py`, `api/v1/formats.py`, `features/phases/`, `features/patrimoine/` | **E05US010** (31/07/2026, [ADR-0061](adr/0061-routing-generique-et-placement-en-cascade.md)) : une phase porte `sources: tuple[SourcePhase, ...]` — **plusieurs** prélèvements, de natures `rangs` / `issue_de_tour` / `reste`, avec **plages relatives** (fin ouverte, « le reste ») pour qu'un format composé pour 120 archers tienne à 82. Le routing devient générique (`route(contexte)` → `HorsTableau` / `VersPlage`), la cascade de placement classe 1→N. Migration **0036 sur les deux tables** (l'ancienne forme `config.source` reste relisable) ; marqueurs `# DETTE-015` retirés des deux sites. ⚠️ Reste hors périmètre, **par décision d'US et non par oubli** : l'écran « Phases » n'édite qu'un prélèvement « par rangs » (les autres y sont en lecture seule) et aucun moteur ne **consomme** encore `issue_de_tour` / `reste` — c'est E01US024. ⚠️ Une facette de DETTE-015 **n'est pas** couverte par cette résorption et a été **re-déclarée** en [DETTE-026](#dette-026--une-source-de-phase-est-ancrée-par-ordre-pas-par-identité) : l'**ancrage par `ordre`** (et non par identité), que l'US a généralisé à N sources sans le changer |
| [DETTE-023](#dette-023--latelier-affiche-des-briques-encore-scopées-par-tournoi) | conception | `frontend/src/features/admin/CoquilleAdmin.tsx` (axe `atelier`) | **E01US023** (31/07/2026, [ADR-0060](adr/0060-briques-du-patrimoine-du-club-bibliotheque-copie-promotion.md)) : catégories et blasons sont devenus des **modèles de bibliothèque** (`tournoi_id` nullable, migration `0034`), et le déroulé une brique neuve — `FormatTournoi` (migration `0035`). `bareme` et `phases`, qui règlent **une** édition, sont parties au **pilotage** — même partage que `plan` (la copie) face à `gabarits` (le modèle). Les **six** destinations de l'atelier s'ouvrent désormais sans tournoi — `bareme`, `phases` et `simulation` ayant rejoint le **pilotage**, car elles règlent (ou rejouent) **une** édition (ADR-0060 §6) ; le message « Choisissez un tournoi ci-dessus » et son repli « cette brique dépend encore d'un tournoi » ont disparu. Le pré-chargement FFTA — le symptôme de fond, qui recréait les quatre blasons canoniques à chaque tournoi — alimente la bibliothèque **une fois pour toutes**, et son bouton par tournoi a été **retiré de l'écran** (l'endpoint subsiste pour le jeu d'essai E15US001, qui peuple un tournoi sans passer par l'atelier). L'invariant « aucune destination de l'atelier n'exige un tournoi » est **vérifié par un test** (`axes.test.ts` sur la table `BESOIN_TOURNOI`, sortie du composant pour être lisible). Marqueur `# DETTE-023` retiré. ⚠️ **Résorbée autrement que prévu** sur un point : la ligne annonçait de sortir *les quatre briques* du périmètre d'un tournoi ; pour les phases, c'était impossible sans désarmer l'invariant `SequencePhases` (ordres contigus 1..N) — cf. ADR-0060 §5. |
| [DETTE-014](#dette-014--la-complétude-ignore-le-forfait) | conception | `backend/application/completude.py` | **E04US015** (27/07/2026, [ADR-0050](adr/0050-forfait-abandon-et-disqualification.md)) : le forfait est livré (abandon/DSQ, agrégat `Forfait`). `_serie_complete` → `_serie_close(serie, nb_volees, est_forfait)` : un archer **forfait en qualification** a sa série **close par forfait** (le forfait *termine* sa participation malgré ses volées partielles préservées). La complétude lit les forfaits de la phase de qualif ; une cible portant un forfaitaire n'est plus « à finir » à jamais. Marqueur `# DETTE-014` retiré du code (remplacé par une note « résorbée »). |
| [DETTE-005](#dette-005--conversion-euroscentimes-sans-aucun-test) | technique | `frontend/src/features/competition/format.ts` | **E00US014** : runner `vitest` installé + script `npm test`, câblé à la CI bloquante (E00US003) ; `format.test.ts` couvre la conversion euros↔centimes (aller-retour, sens de complétion `padEnd`/`padStart`, rejets). Marqueur `# DETTE-005` retiré du code. |
| [DETTE-002](#dette-002--hauteur-de-blason-non-modélisée) | conception | `backend/domain/categorie.py`, `docs/modele-de-donnees.md` | **E03US001** ([ADR-0022](adr/0022-hauteur-de-centre-sur-la-categorie.md)) : la hauteur du centre de l'or vit sur `Categorie` (`hauteur_cm`, 130 par défaut, 110 pour les U11) ; le placement en fait une **contrainte de 1er rang** — une butte, une seule hauteur (test « U11 + adultes → séparés »). Migration `0020` (backfill 110 si `ages` contient U11). |
| DETTE-009 | conception | `backend/api/v1/categories.py` (`ModifierCategorieRequete`) | **E03US004** : le formulaire catégorie porte la hauteur du centre (UI de placement), donc `hauteur_cm` est rendue **obligatoire** au PUT (DTO + `ServiceCategories.modifier` en keyword-only) ; le PUT redevient **intégralement total** ([ADR-0020](adr/0020-blason-zones-vocabulaire-ferme-et-defaut-sur-ensemble.md)), l'entorse « champ partiel » disparaît. Test de non-régression HTTP **inversé** (omission → 400). |
| [DETTE-013](#dette-013--les-gardes-dengagement-lisent-un-score-que-plus-rien-nécrit) | conception | `backend/application/archers.py` (`_signaler_engagement`, `_signaler_changement_categorie`) | **E06US001** (même branche, 20/07/2026) : les deux gardes lisent désormais `SerieRepository.par_archer` — « a tiré » = **au moins une volée validée** (`Serie.nb_fleches_validees`), plus l'agrégat `Score` mort. Arbitrage « volée *validée* (pas toute volée saisie) » reversé dans `stories/E02-inscriptions.md` (règle 9). Tests dérivés du CA E02US003/E02US009 (service **et** API). Marqueur retiré. Reste ouvert sur son objet propre : la **suppression** de `Score`, désormais sans lecteur (DETTE-011). |
| [DETTE-003](#dette-003--config-de-phase-à-plat-au-lieu-de-configpolicies) | conception | `backend/infrastructure/db/repositories.py`, `backend/migrations/versions/0028_phase_config_policies.py`, `docs/modele-de-donnees.md`, `docs/adr/0004-*`/`0011-*` | **E05US003** ([ADR-0046](adr/0046-config-policies-politiques-nommees-parametrees.md)) : les politiques vivent sous `config.policies`, chacune `{"nom": …, …params}` (nom + paramètres) ; le grain de `validation` reste **hors** `policies` (ce n'est pas une politique de moteur). Migration de données `0028` (racine → `policies`, `mode` → `nom`) + relecture tolérante (`_lire_scoring`, filet pour sauvegarde antérieure). `modele-de-donnees.md` et ADR-0004 réconciliés. Tests : bascule d'écriture, relecture ancienne forme, migration. |
| [DETTE-004](#dette-004--messageerreur-dupliqué-dans-chaque-feature-front) | conception | `frontend/src/features/*/`, `frontend/src/shared/ui/MessageErreur.tsx` | **E00US013** (21/07/2026) : `MessageErreur` extrait dans `shared/ui/`, **19 copies retirées** (18 définitions `function MessageErreur` + le rendu inline verbatim de `postes/Postes.tsx`) — recompte terrain du grep, la baseline « 16/18 » sous-numérotait. Rendu **inchangé** (mêmes classes, même `role="alert"`). Les autres `role="alert"` du front ont été **examinés et laissés** à dessein : blocs de **confirmation** à action (archers ×2 édition, NouvelArcher inscription — ton neutre, pas `--erreur`), rendu **ambre** ad hoc du refus 409 de placement (`placement__alerte`, helper `messageErreur` conservé), et rendus **ad hoc contextuels** (« … injoignable — {message} ») hors périmètre du composant générique dupliqué. Marqueurs `DETTE-004` retirés du code. ⚠️ **Angle mort de ce carve-out, relevé le 07/08/2026 (E16US003)** : il portait sur le **rendu**, mais emportait au passage le **narrowing** — ces rendus interpolaient donc `erreur.message` brut, et affichaient un `TypeError: Failed to fetch` sur coupure LAN. Suivi désormais en [DETTE-050](#dette-050--les-rendus-derreur-ad-hoc-ne-sont-pas-ralliés-à-texteerreur). |

## Détail

### DETTE-078 — quatre réglages d'étape sont refusés **après** avoir été persistés

**Où** : `backend/domain/deroule_etape.py` (`__post_init__`, marqueur `# DETTE-078`) ↔
`backend/domain/phase.py` (les gardes `ConfigurationPoulesInvalide`,
`ConfigurationBigShootOffInvalide`, `ConfigurationSuisseInvalide`, `DecoupageInvalide`).

**Le mécanisme.** Poser un réglage sur un type qui ne le lira jamais est refusé — c'est le cas du
**retypage** : on compose une phase en suisse, on la repasse en élimination directe, et le nombre de
rondes reste accroché. Mais le refus vit sur `Phase`, donc à `instancier()`, tandis que
`ServicePhases.ajouter` fait rejoindre l'étape au déroulé **avant** d'instancier. L'ordre des deux
gestes est le défaut : la validation arrive après l'écriture.

**Ce que ça produit, vérifié par exécution.** `POST /api/v1/tournois/1/phases` avec un réglage
incohérent rend bien `422`, et laisse en base une étape sans instance de phase, à l'`ordre` 3.
L'ajout suivant prend l'`ordre` 4. Le déroulé affiche 1, 2, 4 — **troué par une requête refusée**. Le
pire n'est pas le trou, c'est que l'organisateur a lu un message disant que rien n'avait été fait.

**Pourquoi seule la colline est fermée.** Le champ neuf (`colline`) n'a aucune raison de naître avec
ce défaut : sa garde est portée par `EtapeDeroule.__post_init__`, donc antérieure à toute écriture,
et testée aux deux étages (`test_domain_reglage_colline.py`, `test_colline_api.py`). Les quatre
autres sont **hérités** — les corriger toucherait quatre invariants de composition et leurs tests
dans une US de format, ce que le § Dette de `CLAUDE.md` proscrit. Ils sont donc inscrits, pas
corrigés.

**Résorption** : hisser les quatre gardes vers `EtapeDeroule.__post_init__` sur le modèle de
`colline`, avec un test d'API « le refus ne persiste rien » par réglage. US `refactor/` dédiée.

### DETTE-080 — la plomberie d'état des **deux** formulaires de composition est écrite deux fois

**Où** : `frontend/src/features/phases/Phases.tsx` (`FormulairePhase`) ↔
`frontend/src/features/deroule/Deroule.tsx` (le formulaire d'étape) — marqueurs `// DETTE-080`.

**Ce qui est dupliqué, et ce qui ne l'est pas.** Les **contrôles** de réglage sont partagés : les six
`shared/phases/Reglage*.tsx` et `ChoixProfondeur.tsx` sont montés par les deux écrans, et leurs
en-têtes le disent (« partagée par les **deux** écrans qui composent des phases »). Ce qui reste
écrit deux fois est la **plomberie** autour d'eux, pour chacun des dix réglages :

1. l'état local et son adaptateur d'entrée — `useState(depuisReglageColline(etape?.colline ?? null))` ;
2. la **garde de type** au moment de construire la charge utile — `estColline ? versReglageColline(colline) : null`,
   dont le motif (« un réglage porté par un autre type serait refusé en 422 ») est recopié en commentaire des deux côtés ;
3. la **remise à zéro** après ajout, pour que le réglage d'une phase ne se reporte pas en silence sur la suivante.

**Pourquoi ce n'est pas `DETTE-054`.** Celle-ci décrit des DTO jumeaux **côté serveur**, et son remède
est un module de DTO partagé. Ici le duplicata est côté client et porte sur du **cycle de vie de
composant**, pas sur une forme de donnée. Les deux se ressemblent parce qu'ils ont la même cause —
deux mailles pour une même notion, le déroulé d'un tournoi et la brique de bibliothèque — mais ils
ne se résorbent pas au même endroit.

**Ce que l'oubli coûte, et il a déjà coûté trois fois.**

- La **remise à zéro de la profondeur** n'a d'abord été posée que sur un des deux formulaires
  (2ᵉ passe de revue d'E06US006). Le commentaire qui le raconte est toujours dans `Deroule.tsx` :
  « *relevé en 2ᵉ passe : le correctif n'avait été appliqué qu'à un des deux formulaires jumeaux* ».
- La **colline** manquait à cette même liste de reset (2ᵉ passe d'E05US027) : un Ladder portée 4 sur
  8 manches se serait reporté en silence sur la phase suivante.
- `Deroule.tsx` **ne réinitialise toujours aucun champ** à l'ajout — type et effectif compris. Le
  code le dit en toutes lettres : « *l'asymétrie est constatée, pas voulue* ». C'est donc une
  divergence **ouverte**, pas seulement un risque.

**Ce qu'E16US002 y ajoute** : le `titre`, 10ᵉ réglage, avec ses trois éléments de plomberie des deux
côtés. Le câbler à l'atelier n'était pas facultatif — le serveur porte `EtapeDTO.titre`, et un front
qui l'ignorerait enverrait `titre: null` à chaque enregistrement, donc **effacerait les titres d'un
format promu depuis un tournoi titré**. C'est exactement le mode de panne que la ligne `suisse` de
`features/patrimoine/api.ts` documente pour E05US026.

**Ce que cette US a fermé à la place.** La preuve était ailleurs, et elle était plus mûre :
`configInchangee` (`Phases.tsx`) remplace la recopie **manuelle** de la config complète que faisaient
les widgets n'éditant qu'un champ. Trois occurrences réelles, et surtout **deux bugs déjà payés** que
le fichier raconte — `ReglageBarrage` effaçait le `decoupage` (rendant inertes les pauses posées
dessus), et le couple découpage/arrêts partait en 422. Le `titre` en aurait été le troisième :
sans cette fonction, régler un barrage renommait la phase en silence. Portée locale — une fonction,
un fichier —, donc pas d'ADR.

**Résorption** : US `refactor/` dédiée. Un `shared/phases/useCompositionDEtape.ts` détenant les dix
états, leurs gardes de type et leur reset, consommé par les deux formulaires ; les écrans ne gardent
que ce qui les distingue vraiment (l'un a un tournoi et des sources éditables restreintes, l'autre
un brouillon de format sans tournoi). ⚠️ **Ne pas fusionner les deux écrans** : leur portée diffère
réellement, exactement comme `DETTE-054` distingue ses feuilles de ses racines.

### DETTE-079 — le panneau de saisie d'un format à rencontres est écrit **trois fois**

**Où** : `frontend/src/features/poules/SaisiePoules.tsx`,
`frontend/src/features/suisse/SaisieSuisse.tsx`, `frontend/src/features/colline/SaisieColline.tsx`
— marqueur `// DETTE-079` en tête des trois.

**Le mécanisme.** Les trois composants partagent une **coquille** identique sur ~120 lignes :
sélection de la phase à scorer dans le créneau, garde de `phaseRetenue` (mêmes trois lignes et même
commentaire), remontée du duel ouvert, garde `desynchronisee`, pavé `DuelCharge`, bannière de
conflits, mot de la fin, liste de ce qui manque. Ce qui varie tient en trois points : le vocabulaire
(ronde / manche), le préfixe de position propre à la colline, et le bloc « au repos ».

**Ce que ça coûte, et la preuve est dans l'US qui l'inscrit.** `SaisieColline` porte **cinq**
commentaires « correctif de revue d'E05US03x, repris ici d'emblée » — cinq défauts trouvés sur une
copie et **recopiés à la main** dans la suivante. La discipline a tenu cinq fois ; elle a échoué
trois fois dans la même US sur des miroirs voisins (`MOTEUR_SAIT_JOUER`,
`_nb_tours_a_la_composition`, le montage de `PlanDeColline`), tous relevés en revue. Un garde-fou qui
repose sur la mémoire de l'auteur n'est pas un garde-fou.

⚠️ **Le remède recommandé est « rien », et il est argumenté.** La règle 16 exige d'écarter l'option
« rien » **à raison** : ici elle tient, parce que la liste des formats à rencontres est **close**.
`DETTE-066` l'écrit dans ce registre — « il n'y a plus de format annoncé pour en faire un 5ᵉ : les
quatre types à rencontres y sont tous ». Une duplication **stable en taille** ne justifie pas une
indirection : un `<PanneauDeSaisieDeFormat>` paramétré ferait payer un niveau d'abstraction à trois
écrans figés, pour un gain nul sur le CA.

**Ce qui manquait n'est donc pas le remède, c'est la trace** — au même titre que `DETTE-066`,
inscrite elle aussi sans intention de résorption. Le signal à surveiller : *toute correction sur l'un
des trois écrans se porte sur les deux autres*. Si un 4ᵉ format à rencontres apparaissait, cette
ligne devient une US `refactor/` — et la fermeture de la liste, l'hypothèse à réexaminer en premier.

### Deux précisions ajoutées en 2ᵉ passe de revue

**Pourquoi `SaisieBigShootOff.tsx` n'est PAS de la fratrie, alors que `DETTE-066` compte quatre
formats à rencontres.** L'écart est réel et l'omission méritait d'être justifiée plutôt que tue : ce
panneau partage bien le haut de la coquille (`usePhases`, la garde de `phaseRetenue`, le `<select>`
de phase, les états `isPending`/`isError`) mais **pas le bas** — il ne monte aucun `DuelCharge`,
parce qu'une manche de Big Shoot Off n'oppose personne : tous les finalistes tirent en parallèle. Sa
moitié basse n'a donc aucun jumeau à faire diverger, et c'est cette moitié-là qui porte les cinq
correctifs de revue recopiés à la main. Trois écrans, pas quatre — le décompte est exact, et il ne
contredit pas `DETTE-066`.

**Le trio `PlanDePoules` / `PlanDeSuisse` / `PlanDeColline` est dans la même ligne, avec un
arbitrage DIFFÉRENT.** Ces trois-là (`frontend/src/features/phases/Phases.tsx`) sont eux aussi une
3ᵉ copie, ~40 lignes chacune : bouton `Générer`/`Régénérer` au libellé conditionnel, `planVide` par
`flatMap(...).every(couloirs === null)`, bloc `conflits` avec `decrireConflits(..., 'Bloc')`,
`MessageErreur`, classement en pied. La cicatrice est déjà visible — le correctif `'Bloc'` de la
revue d'E05US030 a été **recopié à la main** dans `PlanDeColline`.

⚠️ **Ici, l'option « rien » est nettement plus faible que pour les panneaux de saisie**, et il faut
le dire plutôt que de traiter deux duplications jumelles différemment dans un même registre : les
trois copies vivent **dans le même fichier**, donc l'extraction d'un composant local paramétré
(`{ etat, regenerer, rencontres, classement }`) ne coûte ni module, ni import, ni fichier de test —
`PlansDeCibles.test.tsx` existe déjà. C'est un candidat sérieux pour une US `refactor/`, pas un
« on duplique et on attend ».

Ce qui a été fait dans l'US, en revanche, c'est de **retirer au montage sa capacité à récidiver** :
`TYPES_A_PLAN_PAR_BLOCS` (`shared/phases/catalogue.ts`) porte la liste, `LignePhase` en dérive le
montage, et `PlansDeCibles.test.tsx` itère dessus — un type ajouté à la table sans panneau fait
rougir. La duplication subsiste ; le **défaut qu'elle causait** (un format injouable faute
d'appelant, trois fois de suite) ne peut plus se produire en silence.

### DETTE-077 — une phase de niveau à sources multiples affirme un ordre que rien ne fonde

**Où** : `backend/domain/poule.py` (`_tranches_de_niveau`, marqueur `# DETTE-077`) ↔
`backend/application/prelevement.py` (`preleves`).

**Le mécanisme.** `preleves` concatène les populations de chaque source dans l'ordre
`(ordre_source, rang)`. Sous `SERPENT`, cet entrelacement est arbitraire mais **inoffensif** : la
lecture par blocs de rang ne prétend rien sur l'ordre d'entrée. Sous `PAR_NIVEAU`, la composition
découpe cette liste en **tranches contiguës** et la lecture les rend **groupe par groupe** : l'ordre
d'entrée devient une **affirmation** de niveau. Une phase prélevant « les rangs 1-4 de la phase 2 »
et « les rangs 1-4 de la phase 3 » compose donc le groupe A avec les quatre de la phase 2 et le
groupe B avec les quatre de la phase 3, puis annonce le vainqueur de la phase 3 **5ᵉ** — au seul
motif que la phase 3 porte un ordre plus grand.

⚠️ **Le garde-fou du même lot y conduit.** `SerpentApresDesPoules` accorde son message au pluriel
(« prélève dans **les phases** 2, 3 (poules) ») et recommande « choisissez « par niveau » » —
c'est-à-dire, dans cette configuration précise, l'option dont la justesse n'est pas tenue.

**Pourquoi ce n'est pas corrigé ici.** Fusionner deux classements de phases **parallèles** demande
de savoir les comparer — deux poules jouées séparément ne produisent pas des rangs commensurables.
C'est une règle métier qu'aucun CA ne demande, donc un arbitrage du commanditaire ; l'inventer dans
un correctif de revue serait exactement ce que la règle 16 proscrit.

**Résorption — la piste courte d'abord.** Une anomalie d'**avertissement** « une phase composée par
niveau ne devrait prélever qu'une source » coûte quelques lignes dans `domain/deroule.py`, ne
tranche rien, et suffit à ce que l'organisateur ne tombe pas dedans par le message du garde-fou.
La fusion réelle, si elle est un jour demandée, est une US à part entière.

### DETTE-076 — le miroir front de la répartition en poules recopie la règle du domaine

**Où** : `frontend/src/shared/phases/poules.ts` (`repartition`, marqueur `// DETTE-076`) ↔
`backend/domain/poule.py` (`nb_poules_pour`, `_serpent`, `_tranches_de_niveau`).

**Pourquoi le miroir existe.** L'aperçu « à N archers, voici vos groupes » se rend dans l'atelier de
**formats**, qui compose une brique de bibliothèque : il n'y a ni tournoi ni phase posée, donc la
route serveur qui fait autorité (`GET /api/v1/poules/repartition/{tournoi}/{phase}`) n'est pas
appelable. Un aller-retour par frappe serait de toute façon le mauvais outil pour une aide à la
saisie. Le miroir a des précédents assumés (`EFFECTIF_MAX`, `RANGS_DU_PODIUM`).

**Ce que ça coûte.** Rien aujourd'hui : la revue d'E05US029 a comparé les deux implémentations sur
**6 600 configurations** (2 modes × tailles 2→12 × effectifs 1→300) — **zéro divergence**, y compris
sur les cas limites (une seule poule sous le double de la taille visée, gonflement par le bas). Le
coût est une **dérive future** : une règle de répartition modifiée d'un seul côté produirait un
aperçu faux. Jamais un tournoi faux — c'est le serveur qui compose le jour J, et c'est ce qui
maintient cette dette en *mineur*.

⚠️ **E05US029 change l'enjeu sans changer la nature.** Au serpent, l'aperçu annonce des **tailles**,
et quel groupe gonfle est « sans conséquence sportive ». Par niveau, il annonce des **rangs**
(« rangs 1-6, 7-12, … ») sur lesquels l'organisateur fonde son choix de format : une dérive lui
montrerait des tranches qui ne seront pas celles jouées. La règle recopiée passe par ailleurs de
deux à **trois** (nombre de groupes, serpent, tranches de niveau).

**Pourquoi elle est inscrite maintenant et pas en E05US023.** Le miroir était avoué en commentaire
d'en-tête et, depuis ADR-0094, dans les *Conséquences* de l'ADR — mais **aucune ligne de registre**.
C'est le motif que le registre s'est déjà appliqué deux fois : « une limite avouée en ADR se trace
au registre, l'aveu ne remplace pas la ligne » (`DETTE-053`) et « une dette qui ne vit qu'en
commentaire n'est jamais prise » (`DETTE-064`). Relevée par l'axe C2 de la revue d'E05US029.

**Résorption — deux pistes, la seconde est la bonne affaire.** (a) Une route d'aperçu **sans
tournoi** que l'atelier appellerait : supprime le miroir, mais ajoute un endpoint et un aller-retour
réseau à une aide à la saisie. (b) **Assumer** le miroir et le verrouiller par un **test de
contrat** : un fichier de vecteurs (mode, taille, effectif → tailles attendues) généré depuis le
domaine et rejoué par vitest. Quelques dizaines de lignes, et la dérive devient impossible sans
faire rougir la CI.

### DETTE-075 — une pause posée le jour J n'est relisible nulle part

**Ce qui manque.** `ArretDeCirconstanceRepository` expose `par_depart` et `ajouter` ; seul le
**service** appelle `par_depart`, pour évaluer. Aucune route ne rend les arrêts posés, et l'écran ne
les affiche donc jamais. `GET /departs/{id}/arrets/en-attente` ne sert que des `FranchissementArret`
— la trace d'un arrêt qui a **déjà** coupé, pas d'un arrêt **armé**.

**Ce que ça coûte aujourd'hui.** L'organisateur pose « bloquer dans 2 tours », change d'écran,
revient : plus rien à l'écran ne dit qu'une pause est armée, ni sur quel tour elle tombera. La seule
manière d'apprendre son existence est de reposer la même et de lire le refus. Rien n'est cassé — la
pause coupera — mais l'US s'appelle « rendre la pause visible », et c'est la seule surface du
mécanisme qui reste muette.

**Pourquoi ce n'est pas un remède structurel.** Le port a déjà la méthode, l'adapter a déjà le
`where`, la clé de cache existe. C'est une tranche d'IHM, pas un pattern : le § *Dette* de
`CLAUDE.md` demande une preuve dans le code du jour avant d'introduire une abstraction, et il n'y en
a aucune ici — il n'y a même pas de duplication.

**Effet de bord à connaître pour qui la résorbera.** `usePoserArretRelatif` n'invalide **aucune**
requête aujourd'hui, et c'est délibéré (poser un arrêt ne change aucune lecture existante). Le jour
où la lecture existe, c'est **elle** qu'il faudra invalider — et elle seule. Le hook porte la note.

Marqueurs `# DETTE-075` sur `ArretDeCirconstanceRepository` (le port, là où la lecture manque) et
sur `PoserUnePause` (l'écran qui devrait l'afficher).

### DETTE-074 — un tableau à plusieurs sources n'annonce qu'un tour, donc aucune pause n'y tombe

**Le raccourci.** `domain/suivi_deroule.avancement_bloc` compose l'avancement d'une phase à partir de
ses **braquets projetés**. Une phase en élimination directe dont la tranche d'entrée est
indéterminable — parce qu'elle puise dans **plusieurs** phases amont
([ADR-0061](adr/0061-routing-generique-et-placement-en-cascade.md)) — n'en produit aucun, et le bloc
retombe alors sur `nb_tours = 1, tour_courant = None`.

**Pourquoi c'est un problème d'E05US033 et pas d'E05US032.** Ce couple est la signature exacte de
« avancement inconnu » pour `ServiceArretsProgrammes._avancement_connu`, qui refuse alors de couper.
Le repli est donc **sûr** — on ne met jamais une salle en pause au mauvais moment, ce qui serait le
pire des deux — mais il rend l'arrêt **définitivement inerte** sur cette phase, sans le dire à
personne :

- à l'atelier, l'écran offre le réglage : `elimination_directe` est un type arrêtable, le nombre de
  sources n'entre pas dans le refus ;
- en salle, rien ne distingue « pause pas encore atteinte » de « pause qui ne viendra jamais ».

L'organisateur découvrirait donc le jour J que sa pause repas n'a pas eu lieu — mot pour mot le mode
de panne qu'[ADR-0091](adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md) §8 refuse
ailleurs, atteint ici par une autre porte.

**Ce que l'histoire de cette dette apprend.** E05US032 a créé le repli, a vu la limite, l'a écrite en
docstring — et l'a **déléguée nommément à E05US033** : « *`E05US033` consommera ce champ : à reprendre
là-bas, où le besoin le nommera.* » E05US033 a bien consommé le champ ; elle n'a pas repris la limite,
et n'aurait rien vu si l'axe C2 ne l'avait pas relevé. Une dette déléguée d'une US à la suivante **en
commentaire de code** n'a aucun porteur : elle n'apparaît dans aucune revue, aucun tracker, aucune
table. C'est exactement ce que le § *Dette* de `CLAUDE.md` interdit, et le fait que la docstring d'origine
fût honnête et précise n'y change rien — ce n'est pas la qualité du commentaire qui manquait, c'est le
**lieu**.

**Résorption — deux voies, à trancher sur preuve d'usage.**

1. **Un lecteur d'avancement pour l'élimination directe.** `ServiceSaisieDuels` reconstruit déjà
   l'arbre et connaît `Tableau.nb_tours` : réaliser `LecteurAvancementDePhase` et le brancher au
   composition root suffirait, sur le patron exact des trois formats d'E05US032
   ([ADR-0090](adr/0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md) §5). C'est le
   remède **borné et connu**. Coût : une reconstruction de plus par lecture, donc `DETTE-031` élargie.
2. **Refuser l'arrêt** à l'atelier sur un tableau à sources multiples, comme on refuse déjà les types
   sans tour observable. Cohérent avec « un refus explicite vaut mieux qu'un réglage inerte », mais le
   refus dépendrait alors du **nombre de sources** — un réglage voisin, modifiable après coup : il
   faudrait revalider les arrêts à chaque édition des sources d'une phase, ce qui est un mécanisme neuf.

⚠️ **Ne pas trancher par commodité.** (1) rend la capacité complète, (2) la borne honnêtement ; les
deux sont défendables, et c'est un arbitrage à porter au commanditaire.

⚠️ **Le porteur désigné est tombé à faux — 20/08/2026.** Cette section disait « à rattacher à
`E05US034`, qui rouvre déjà le registre d'avancement pour la qualification, donc qui paiera le patron
une fois pour deux formats ». Le raisonnement était juste **et la prémisse a disparu** : le cadrage
d'E05US034 a coupé le périmètre et sorti le chantier moteur vers `E05US035`. E05US034 n'a branché
aucun lecteur d'avancement, et n'était donc pas le point de passage annoncé.

**Ce que cette dette apprend maintenant, et qui est un cran au-dessus de sa leçon d'origine.** Elle
était née d'une délégation *en commentaire de code*, sans porteur ; on l'a corrigée en l'inscrivant
ici — le bon geste. Mais l'inscription a **reconduit le même mécanisme sous une autre forme** : au
lieu de nommer une US qui n'existait qu'en commentaire, elle a nommé une US du tracker **en pariant
sur son périmètre**. Un périmètre d'US n'est fixé qu'à son cadrage, c'est-à-dire *après* que la
dette a été écrite. `DETTE-031` porte déjà ce constat en toutes lettres — *« ne pas réattribuer par
pronostic : c'est ce pronostic-là qui vient de tomber à faux »* — et c'est la **deuxième** ligne du
registre à le vérifier en cinq jours.

**Nouveau porteur naturel : `E05US035`**, qui rouvrira réellement le registre d'avancement (un
lecteur pour `QUALIFICATION`) et devra de toute façon rouvrir la table de refus par type. ⚠️ À lire
comme une **indication**, pas comme une affectation : c'est le troisième pronostic sur cette ligne,
et les deux précédents sont tombés. La ligne reste ouverte tant que le code ne l'a pas fermée.

Marqueur `# DETTE-074` sur le repli de `avancement_bloc` et sur `_avancement_connu`, qui est l'endroit
où la conséquence se produit.

### DETTE-073 — la pause d'un **tournoi** ne gèle toujours rien

**Ce que fait le code.** `ServiceTournois.mettre_en_pause` fait passer un tournoi `en_cours` à
`en_pause` (`StatutTournoi.EN_PAUSE`, ADR-0026 §3) et s'arrête là. Aucun chemin d'écriture ne lit ce
statut : ni `ServiceSaisie.saisir_volee` / `.valider`, ni `ServiceSaisieDuels.saisir_manche` /
`.saisir_barrage` / `.valider`, ni `ServiceRoutage`, qui sélectionne ses phases sur
`statut is not TERMINEE` — le statut de la **phase**, et jamais celui du tournoi.

**Et la docstring dit le contraire** : « Gèle un tournoi `en_cours` en `en_pause` (la saisie s'arrête
jusqu'à `reprendre`) ». C'est ce qui rend cette dette **majeure** plutôt que mineure : ce n'est pas
une capacité manquante, c'est une capacité **annoncée** et absente. Un lecteur du code la croit
tenue ; un organisateur croit avoir arrêté sa salle.

**Comment on l'a trouvée.** Par accident, et l'accident est instructif. La fiche d'`E05US033` listait
« `EN_PAUSE` gèle la validation » parmi ses *pièges à vérifier* — c'est-à-dire comme un acquis dont il
fallait mesurer les effets de bord. La vérification a rendu l'inverse du postulat : rien n'était gelé,
**ni au niveau phase, ni au niveau tournoi**. Sans elle, l'US aurait livré un arrêt programmé qui
n'arrête personne.

**Pourquoi le volet tournoi n'est pas corrigé dans l'US.** Trois raisons, dans cet ordre :

1. **ce n'est pas la même maille.** ADR-0026 §3 fait de la pause de tournoi une suspension de
   *compétition*, quand `E05US033` livre une pause de *salle*. Les confondre mélangerait « on
   s'arrête dix minutes » et « la compétition est suspendue » ;
2. **la sémantique diffère, et pas à la marge.** Le CA de l'US impose qu'un arrêt de créneau laisse
   **chaque phase finir son tour en cours** ([ADR-0091](adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md) §4).
   Une suspension de compétition, elle, coupe net — y compris en plein tir. Ce n'est pas un
   paramètre du même mécanisme : c'est un autre geste ;
3. **le périmètre a été arbitré par le commanditaire** le 19/08/2026, sur les trois options posées
   (phase seule / phase et tournoi / rien geler). Il a choisi la phase seule.

**Ce qui rendrait la résorption sûre.** Deux gestes, à trancher ensemble parce que le second est le
repli du premier :

- **(a)** une garde `TournoiEnPause` (409) sur les mêmes points d'écriture que `PhaseEnPause`, en
  coupant net. ⚠️ Décider alors du sort de la **correction** : la garde de phase la laisse passer (CA
  du 19/08/2026, « la pause est le moment où l'on découvre les erreurs »), et il n'est pas évident
  qu'une compétition suspendue doive suivre la même règle — c'est un arbitrage à demander, pas à
  déduire ;
- ~~**(b)** corriger la docstring et retirer la promesse~~ — **fait dès le commit de constat**
  (E05US033), parce que le coût était nul et qu'une docstring fausse trompe le prochain lecteur du
  code avant tout organisateur. La dette est donc déjà passée de « l'application mente au
  développeur » à « la capacité n'existe pas », et il ne reste que **(a)**.

⚠️ **Ne pas laisser en l'état pour autant.** Le **bouton de l'écran d'administration** continue, lui,
de laisser croire à l'organisateur que sa salle est arrêtée — et c'est là qu'est le vrai coût, pas
dans la docstring. Des deux volets constatés le 19/08/2026, c'est le seul qui subsiste.

### DETTE-065 — le garde d'autorisation des routeurs d'écriture est recopié sept fois

**Ce que fait le code.** `_exiger_meme_tournoi(scoreur, tournoi_id)` et `_cle_idempotence(...)` sont
écrits **à l'identique** dans sept routeurs : `saisie.py`, `saisie_duels.py`, `forfaits.py`,
`poules.py`, `big_shoot_off.py` et `suisse.py`.

**Pourquoi c'est majeur alors que les sept copies sont justes.** Parce que la fonction dupliquée
**est** le contrôle d'accès : elle refuse (403 `scoreur_hors_tournoi`) un scoreur qui écrirait hors
de son tournoi. Rien — ni mypy, ni ruff, ni un test générique — ne rougit si un **8ᵉ** routeur
d'écriture l'oublie. C'est le même angle mort que `DETTE-054` décrit pour les DTO jumeaux, mais
appliqué à une **autorisation** au lieu d'un champ de composition : là-bas l'oubli fait perdre un
réglage, ici il ouvre une écriture.

**Comment elle a été trouvée.** Relevée en revue d'E05US026, sur le contraste : la même branche
consacre un ADR entier ([ADR-0084](adr/0084-un-seul-port-de-lecture-de-classement-resolu-par-type.md))
à justifier un remède structurel sur sa **3ᵉ** occurrence, pendant qu'elle ajoute la **6ᵉ**
occurrence de celle-ci sans une ligne au registre.

**Résorption.** `exiger_meme_tournoi` rejoint `api/dependances.py`, où vit déjà `exiger_scoreur` —
son domicile naturel, et il devient alors une dépendance FastAPI comme les autres. La fabrique de
clé d'idempotence rejoint un module `api/v1/_idempotence.py`. **US `refactor/` dédiée** : le geste
touche sept routeurs d'écriture et leurs tests, il n'a rien à faire dans une US de moteur.

### DETTE-066 — le bot de simulation se retire des formats à la main

**Ce que fait le code.** `application/simulation_format.py` calcule
`_TYPES_DEROULABLES = TYPES_JOUES - {POULES, BIG_SHOOT_OFF, SUISSE}` : il part d'une table
**dérivée** du registre de contrat et lui **retranche à la main** les formats que le harnais de
simulation ne sait pas jouer (`fabriquer_harnais_simulation` ne construit aucun de ces services).

**Pourquoi le retrait manuel est fragile.** Les deux tables répondent à des questions différentes :
`TYPES_JOUES` dit « **un service de production** déroule-t-il ce type ? », ce site demande « le
**bot** sait-il le jouer ? ». Le module le documente lui-même — « remplacer une table écrite à la
main par une table dérivée n'est sûr que si la capacité dérivée répond exactement à la même
question ». Rien ne relie les deux, donc rien ne signale l'oubli.

**Ce que l'oubli coûte, et il a été constaté.** Un format qui devient jouable sans être retiré ici
tombe dans la branche « pas d'état » et sort `joue=True, tours=0, duels=0` : l'atelier affiche des
zéros **comme un constat**, et le bandeau « le moteur ne sait pas encore dérouler ce type »
disparaît. L'organisateur compose alors un déroulé que rien ne simulera, en croyant l'avoir vérifié.

**3ᵉ occurrence, donc remède justifié sur preuve** : poules (E05US023), Big Shoot Off (E05US028),
système suisse (E05US026 — oubli réel, relevé en revue par deux axes indépendants).

**Résorption.** Une capacité `simulable_par_le_bot` au registre de contrat, dont
`_TYPES_DEROULABLES` dérive : la question devient explicite, et un format neuf doit y répondre.
L'alternative — apprendre au harnais à construire les services manquants — est plus ambitieuse et
se décide séparément. À trancher en **US dédiée** ; sans quoi la colline (`E05US027`) en fera un 4ᵉ
retrait à la main.

### ✅ DETTE-063 — le système suisse n'occupe aucun couloir *(résorbée le 16/08/2026)*

**Résorbée dans l'US qui l'a ouverte**, en deux temps le même jour : le commanditaire a tranché
le renommage (`placement_par_bloc`, migration 0046), ce qui a libéré le chemin, puis
`ServiceSuisse.regenerer_plan` a posé le bloc. Conservée ici parce que le raisonnement qui suit
explique **pourquoi un seul bloc** — la question se reposera à la colline (`E05US027`).

**Ce que fait le code.** `domain/contrat_phase.py` déclare `plan_de_cibles=AUCUN` pour `SUISSE`, et
c'est **exact** : `application/suisse.py` rejoue les rondes, expose les rencontres et rend le
classement, mais aucun service ne pose de couloirs pour cette phase.

**Pourquoi l'écart existe.** Le CA d'E05US026 demandait « le plan de cibles suit — mêmes règles
d'empreinte et de contiguïté qu'en poules », et le mécanisme existe déjà
(`domain/placement_par_bloc.py` : un groupe occupe un **bloc de couloirs contigus**, les couloirs de
chaque rencontre étant dérivés à la lecture). Deux choses manquaient, et la seconde était un
arbitrage, pas du code :

1. le **service** qui pose ce bloc pour une phase de suisse — **c'est ce qui reste** ;
2. ✅ une décision de **vocabulaire**, rendue le 16/08/2026. Le port et la table s'appelaient
   `placement_poule`, avec une colonne `poule_numero` — or une ronde de suisse n'est pas une poule.
   Le commanditaire a tranché pour le **renommage** (`placement_par_bloc`, `groupe_numero`,
   migration 0046) plutôt que pour la tolérance du mensonge : le nom désignait le mauvais
   **concept**, pas seulement un synonyme imparfait comme dans `DETTE-042`.

⚠️ **L'unité placée est le bloc, jamais l'archer**, et c'est la même raison qu'en poules : une ronde
**ré-apparie tout le plateau**, donc personne n'a de couloir attitré. Persister « archer → couloir »
écrirait une information *fausse*, pas seulement incomplète.

**Ce que ça coûte aujourd'hui.** L'organisateur ne peut pas préparer la salle pour cette phase, là où
il le peut pour une qualification, un tableau ou des poules. Le jour J, les tireurs d'une ronde
trouvent leur butte par l'écran de salle ou par le juge — même situation que `DETTE-059` pour le Big
Shoot Off, et même caractère borné.

**Résorption.** Un bloc **unique** couvrant `2 × (effectif ÷ 2)` couloirs, la n-ième rencontre d'une
ronde prenant les couloirs `2n` et `2n+1` du bloc — exactement `_couloirs_de_la_rencontre` des
poules. Trancher le point 2 **avant** de coder : c'est lui qui décide s'il y a migration.

### DETTE-064 — l'étape de déroulé se recopie champ par champ dans les décors de test

**Ce que fait le code.** `poser_phase_sql` et `poser_phase_factice` (`backend/tests/conftest.py`)
construisent une `EtapeDeroule` à partir d'une `Phase` en **recopiant ses champs un à un**. Il n'y a
aucun mécanisme qui rende un oubli visible : le décor pose alors une phase **non réglée** là où le
test croit avoir posé une phase réglée.

**Pourquoi c'est majeur alors que c'est du test.** Parce que le défaut se présente **à l'envers de
ce qu'il est**. Le test échoue en `phase_pas_reglee` sur une phase parfaitement réglée, et l'on
cherche le défaut dans le service, dans le repository, dans la sérialisation du `config` — partout
sauf dans le décor. C'est du temps perdu à chaque fois, et il n'y a aucun signal qui oriente.

**Le piège s'est déclenché trois fois de suite, une par réglage neuf.**

| US | Réglage oublié | Symptôme |
|---|---|---|
| E05US023 | `poules` | phase de poules non réglée dans le décor |
| E05US028 | `big_shoot_off` | idem, tests d'API en `phase_pas_reglee` |
| E05US026 | `suisse` | idem, **quatre** tests d'API |

⚠️ **La 3ᵉ occurrence avait été prédite mot pour mot** — le commentaire du helper écrivait, dès
E05US028 : « *ce recopiage champ par champ est structurellement fragile (rien ne rougit quand on en
oublie un), et il le sera à chaque réglage neuf* ». Elle n'était pas **tracée ici**, et c'est
précisément ce qui manquait pour qu'elle soit prise : une dette qui ne vit qu'en commentaire n'entre
dans aucune file de travail. C'est le cas d'école du § Dette de `CLAUDE.md` — « une dette silencieuse
est remontée en majeur à la revue ».

**Résorption.** Une fabrique **du domaine**, `EtapeDeroule.de_phase(phase)`, appelée par les deux
helpers. Sa place naturelle est à côté d'`EtapeDeroule.instancier`, dont elle est l'inverse : le
domaine sait déjà descendre d'une étape vers une phase, il lui manque le chemin retour. Le seuil
« 3ᵉ occurrence réelle » de `CLAUDE.md` étant atteint sur preuve, le remède se justifie — mais en
**US dédiée**, pas en douce. La colline (`E05US027`) en a fait une 4ᵉ occurrence.

### DETTE-060 — l'écran de Big Shoot Off n'est pas branché sur la file hors-ligne

**Ce que fait le code.** `useSaisirVolee` et `useValiderManche` appellent l'API directement. Les
autres surfaces de saisie — qualification, duels, poules — passent par la file d'E04US009, qui
encaisse une coupure LAN, garde l'acte et le rejoue à la reconnexion.

**Pourquoi l'écart existe.** La file est bâtie sur `DuelHorsLigne` : elle transporte un **acte de
duel**, avec ses deux duellistes et son `match_numero`. C'est ce qui a permis aux poules de l'obtenir
gratuitement (une rencontre de poule *est* un duel, ADR-0083 §7). Une **volée collective** n'en est
pas un : il n'y a ni adversaire ni numéro de match. L'y faire entrer demande d'élargir la file à un
second type d'acte, donc de toucher le rejeu, la déduplication et le store — trois modules livrés et
éprouvés, sur une US qui portait déjà un changement de règle métier.

**Ce qui borne le risque.** Un Big Shoot Off est une **finale** : quelques manches, un effectif
réduit, devant tout le monde. Une volée perdue se voit sur-le-champ et se retape. Ce n'est pas
comparable à une qualification de 120 archers sur trois heures, où la file protège un volume qu'on
ne peut pas reconstituer de mémoire.

**Résorption.** `famille` existe déjà dans le store comme discriminant : c'est le point d'accroche
naturel pour un acte générique. US front dédiée, avec ses tests de rejeu.

### DETTE-059 — le routage d'un Big Shoot Off ne donne aucune cible

**Ce que fait le code.** `ServiceRoutage._routage_big_shoot_off` rend une issue
`PROCHAINE_MANCHE` portant le numéro de la manche et le nombre de sortants, mais `cible` et
`position` valent toujours `None`. Le champ `manque` le dit en clair.

**Pourquoi ce n'est pas un bug.** Le registre de contrat déclare `plan_de_cibles=AUCUN` pour ce
type, ce qui est **exact** : aucun service n'attribue de couloir à un finaliste. La capacité
`route_l_archer` répond « le routage sait dire ce qui vient », pas « il sait dire où ». Le taire
aurait été le défaut ; le nommer est la règle `P-3` (« ce qui n'est pas connu est nommé »).

**Pourquoi ce n'est pas résorbé dans E05US028.** Deux obstacles, dont un métier :

1. **technique** — les finalistes sont des inscrits du créneau, donc leur couloir de qualification
   existe déjà (`PlacementRepository.par_depart`, keyé par inscription). Le lire demande deux
   dépendances neuves à `ServiceRoutage` (`PlacementRepository`, `InscriptionRepository`) ;
2. **métier, et c'est le vrai blocage** — une finale spectacle se tire-t-elle sur les cibles de
   qualification, ou sur des cibles dédiées devant le public ? Le CA ne le dit pas, et le référentiel
   §10.1 non plus. Répondre (a) sans le demander figerait une règle de compétition dans un service
   de lecture, ce qu'ADR-0065 §3 a explicitement refusé de faire.

**Résorption.** Trancher la question métier d'abord. Si la finale se tire sur les cibles de
qualification, (a) est quelques lignes. Sinon il faut un plan propre au format
(`PlanDeCibles.PAR_FINALISTE`) avec sa table et sa migration, comme les poules en ont un
(ADR-0083 §3). Marqueurs `# DETTE-059`.

### DETTE-058 — le Big Shoot Off ignore le grain de validation réglé sur sa phase

**Ce que fait le code.** `ServiceBigShootOff.valider_manche` construit son grain à la volée,
`GrainValidation.toutes_les_n_volees(configuration.volees)`, et n'ouvre jamais `phase.validation`.
C'est le seul grain qui verrouille **une manche** — `Serie.valider` y validant « le prochain lot de
N volées non validées », ce qui est exactement le bloc de volées de la manche courante.

**Pourquoi c'est un écart et pas un choix.** `domain/phase.py` admet deux grains pour ce type :

```python
TypePhase.BIG_SHOOT_OFF: frozenset({TypeGrain.FIN_DE_SERIE, TypeGrain.TOUTES_LES_N_VOLEES}),
```

L'atelier propose donc un réglage que le service n'honore pas. Ce n'est pas un bug de comportement
— le grain imposé est le **seul jouable** — mais un réglage qui ment : « fin de série » sur un Big
Shoot Off signifierait attendre la fin des manches pour savoir qui est éliminé, alors que chaque
manche détermine les participants de la suivante. La phase ne démarrerait jamais.

**Pourquoi ne pas l'avoir corrigé dans E05US028.** Les deux remèdes touchent un contrat livré :

- retirer `FIN_DE_SERIE` de `_GRAINS_ADMIS` invalide un couple type/grain que `test_domain_phase`
  documente comme admis depuis E05US015, et `_GRAINS_ADMIS` est partagé avec la qualification ;
- déduire le grain du réglage pour ce type introduit une exception dans un dictionnaire dont toute
  la valeur est d'être une table uniforme.

Aucun des deux n'est de la plomberie, et l'US portait déjà un changement de **règle métier** (les
éliminations par paliers, référentiel §10.1 amendé). Empiler un second changement de contrat dans la
même branche aurait mélangé deux sujets.

**Résorption.** La seconde piste est la plus honnête : pour un Big Shoot Off, la cadence de
validation **est** `configuration.volees` — il n'y a rien à choisir, donc rien à régler. Supprimer
le réglage vaut mieux que le contraindre. Marqueurs `# DETTE-058` en note de module et sur
`valider_manche`.

### DETTE-054 — huit paires de DTO jumeaux entre les deux routeurs de composition

**Où** : `backend/api/v1/phases.py` et `backend/api/v1/formats.py`. Trois paires strictement
identiques — `SourceDTO` (E05US010), `ProfondeurDTO` (E06US006), `ReglagePoulesDTO` +
`BaremePouleDTO` (E05US023) — plus les blocs `model_config = ConfigDict(extra="forbid")` et leur
docstring, eux aussi recopiés.

⚠️ **Le décompte en « paires » sous-estime la dette, et E05US029 le montre.** Cette US n'ajoute
aucune paire : elle ajoute **deux champs** (`mode`, `serpent_assume`) à la paire `ReglagePoulesDTO`,
donc quatre déclarations pour deux notions. Le titre de cette dette continuera d'annoncer « sept
paires » pendant que la surface dupliquée croît — ce qui est précisément le genre de mesure qui
rassure à tort. La bonne unité serait le **champ** dupliqué, pas la classe.

**Pourquoi les jumeaux existent.** Les deux routeurs servent la **même** notion à deux mailles : la
bibliothèque de formats (`ModelePhase`, sans tournoi ni statut — ADR-0060 §5) et le déroulé d'un
tournoi (`EtapeDeroule`). Les **racines** diffèrent donc réellement ; ce sont les **feuilles** qui
sont identiques, et c'est là que la duplication est gratuite.

**Ce que ça coûte.** Rien à l'exécution : le risque est un ajout fait d'un seul côté. Il n'est pas
théorique — `ModelePhase.barrage_jusqu_au` a **effectivement** manqué jusqu'au 07/08/2026, si bien
que promouvoir un tournoi en format **perdait son seuil de barrage**, en silence (ADR-0076).
E05US023 a dû poser `poules` aux deux endroits, et rien n'aurait rougi s'il n'y en avait eu qu'un.

**Pourquoi assumée maintenant.** La règle « remède structurel » de `CLAUDE.md` demande une **3ᵉ
occurrence réelle** avant d'introduire un pattern : elle est atteinte ici, pas avant. Mais elle
demande aussi que le remède se traite **en US dédiée**, jamais en douce dans l'US courante — et
E05US023 est déjà une tranche large, dont le diff noierait un déplacement de DTO.

**Résorption attendue.** US `refactor/` — extraire les feuilles partagées dans un module de DTO de
composition, importé par les deux routeurs. Ne **pas** fusionner les deux `EtapeDTO`/`PhaseReponse`,
qui portent des champs différents pour de bonnes raisons. Marqueurs `DETTE-054` dans les docstrings
de `ReglagePoulesDTO`, `ReglageBigShootOffDTO`, `ReglageSuisseDTO` et `ArretProgrammeDTO`
des deux fichiers — **six** paires, pas cinq. ⚠️ **Ce paragraphe a été faux trois fois de suite, et c'est l'information la plus utile qu'il porte.** La consigne disait d'abord « trois paires » en ne nommant que `ReglagePoulesDTO` (relevé en revue d'E05US026), puis « cinq » alors qu'E05US033 en ajoutait (relevé en revue d'E05US033), puis « sept » alors que le périmètre final de cette même US n'en ajoutait qu'**une** — le réglage de découpage, donc `DecoupageDTO`, est sorti le 19/08/2026. Chaque fois, qui aurait résorbé en lisant ce détail aurait laissé les dernières derrière lui — exactement le défaut que la ligne du tableau reproche à E05US028. Le titre lui-même portait un compte périmé. **Corollaire pour la prochaine US qui ajoute un réglage d'étape** : le compte est à trois endroits (titre, ligne de tableau, ce paragraphe), et les trois doivent bouger ensemble.

### DETTE-053 — `bareme_du_tournoi` et `grain_du_tournoi` portent un nom qui ment

**Où** : `backend/application/bareme_qualification.py` (`bareme_du_tournoi`),
`backend/application/grain_validation.py` (`grain_du_tournoi`, `_qualification_ou_none`), et les
deux routes historiques `/api/v1/tournois/{id}/bareme-qualification` et `.../grain-validation`.

**Le raccourci.** Depuis [ADR-0082](adr/0082-plusieurs-qualifications-dans-un-meme-deroule.md), un
déroulé peut porter plusieurs qualifications : « le barème **du tournoi** » n'existe plus en
général. Les deux méthodes rendent celui de la **première** — un `next(...)` sur les étapes de type
`qualification`. Le nom continue d'annoncer un réglage de tournoi.

**Ce que ça coûte.** Rien sur un tournoi mono-qualification, c'est-à-dire la quasi-totalité. Sur le
déroulé de référence (3×20, puis *haute* et *basse* à 3×15), tout appelant qui s'y fierait
annoncerait 20 volées à des archers qui en tirent 15. Les deux surfaces où cela se voyait ont été
portées ailleurs dans la même US : l'écran « Barème & validation » liste les qualifications, et la
feuille de marque papier lit désormais le barème **du créneau** (`_bareme_du_creneau`).

**Pourquoi conservé.** Les routes historiques les servent, et elles restent le **seul chemin qui
crée** la qualification d'un tournoi neuf, dont le déroulé est vide. Les retirer maintenant
demanderait de déplacer ce geste de création, ce qui n'est pas le sujet de cette US.

**Résorption.** Faire passer les consommateurs restants par `qualifications` (liste) ou par une
lecture par étape, puis retirer les deux méthodes et leurs routes. Marqueurs `# DETTE-053` aux deux
endroits.

### DETTE-052 — la saisie admin devine le créneau de l'archer

**Où** : `backend/application/saisie.py` (`_depart_de_saisie`, `_phase_qualification`), et les
routes de saisie admin, qui ne portent pas de `depart_id`.

**Le raccourci.** Depuis [ADR-0082](adr/0082-plusieurs-qualifications-dans-un-meme-deroule.md), une
feuille de marque pend à sa **phase** : écrire une volée suppose donc de savoir *dans quelle
qualification*, donc *dans quel créneau*. La saisie par **poste** le sait — la tablette porte son
`ContexteSaisie(cible, départ)`. La saisie **admin**, elle, n'a rien : le service retient le plus
petit identifiant de créneau où l'archer est inscrit.

**Ce que ça coûte.** Un archer engagé sur deux créneaux, dont l'organisateur corrige une volée
depuis l'écran d'administration, se voit écrire dans le créneau du **matin** quoi qu'il arrive.
C'est peu : le cas « un archer sur deux créneaux » est soutenu par le modèle mais rare, et le
chemin normal de saisie (le poste) est juste.

**Pourquoi ce n'est pas une régression.** Avant E05US025, ce même archer n'avait **qu'une seule
feuille** pour tout le tournoi : sa seconde série écrasait la première (c'était DETTE-046, résorbée
par la même US). Le raccourci actuel est donc strictement meilleur que l'état antérieur — il choisit
mal une feuille parmi deux, là où il n'y en avait qu'une, fausse.

**Ce qui a été écarté.** Trier sur le **numéro** de créneau plutôt que sur l'identifiant aurait
demandé d'injecter un `DepartRepository` entier dans `ServiceSaisie` pour un départage sans enjeu —
les deux ordres ne diffèrent que si les créneaux ont été renumérotés après coup. Ce qui compte ici
est d'être **déterministe** : deux saisies successives du même archer doivent atterrir dans la même
feuille. Le vrai remède n'est pas un meilleur tri, c'est que la route porte le créneau.

**Résorption.** Porter le `depart_id` sur les routes de saisie admin et le passer au service, à
l'image du `ContexteSaisie` d'un poste. Emporte le front (l'écran d'administration doit choisir le
créneau quand l'archer en a plusieurs). Marqueurs `# DETTE-052` dans `saisie.py`.

### DETTE-051 — un forfait déclaré **en tableau** reste prélevable en aval

**Le raccourci.** `domain/classement_de_tableau.py:_situee` réécrit le statut de chaque ligne à
`StatutClassement.EN_LICE`, avec ce motif : « un archer présent dans le tableau y a sa place, quel
que soit ce que la qualification disait de lui. Le filtre des sortis a déjà eu lieu — à
l'ensemencement de ce tableau-ci —, et le rejouer ici retirerait deux fois le même archer. »

Le raisonnement est juste **pour un forfait de qualification** : celui-là n'est jamais entré dans
l'arbre, et le classement du tableau ne le contient pas. Il ne l'est pas pour un forfait déclaré
**dans la phase de tableau** : `ServiceSaisieDuels._appliquer_forfaits` le traite en **walkover**
(E04US015 / [ADR-0050](adr/0050-forfait-abandon-et-disqualification.md)) — son adversaire passe, mais
lui **reste** dans l'arbre et garde une position acquise. Il ressort donc `EN_LICE` du classement
dérivé, et `preleves._en_lice` ne le filtre pas.

**Ce que ça coûte.** Un archer qui a abandonné en 1/8 peut être ensemencé dans la consolante. Il ne
s'y présentera pas : l'organisateur découvre un duel sans duelliste et le règle à la main. Aucune
donnée n'est fausse et aucun classement n'est faussé — la population est simplement trop large.

**Pourquoi ce n'est pas corrigé ici.** La question sous-jacente — *un abandon en tableau ferme-t-il
l'accès aux phases aval, ou seulement au reste de ce tableau ?* — est une **règle de compétition**,
pas un détail d'implémentation. Les deux réponses se défendent (un archer blessé ne repart pas ;
un archer qui déclare forfait sur un duel pour raison d'horaire peut vouloir la consolante), et le
règlement FFTA ne la tranche pas à notre maille. La deviner dans un service d'exécution est
exactement ce qu'[ADR-0065](adr/0065-rang-acquis-lu-sur-la-plage-et-issue-repechee.md) §3 a refusé
de faire pour `par_issue_de_tour` — et `DETTE-033` en est la trace.

**Remède.** Trancher avec le club, puis porter la décision **à un seul endroit** : soit `_situee`
propage le `statut` d'origine au lieu de le forcer, soit `preleves` filtre sur les forfaits de la
phase source. Le premier est plus juste (le classement dit la vérité) mais demande que
`classement_de_tableau` connaisse les forfaits de la phase, qu'il ne reçoit pas aujourd'hui.

Marqueur `# DETTE-051` sur `_situee`.

### DETTE-072 — la ligne d'une rencontre a **deux rendus**

`E05US031` fait rendre au **même onglet public** quatre formats : l'arbre de duels (par `VueTableaux`,
livrée en `E07US005`) et les trois formats sans arbre (par les vues neuves des features `poules`,
`suisse` et `big-shoot-off`). Les uns et les autres affichent la même chose au niveau de la ligne —
deux noms, un score au milieu, le gagnant en gras une fois scellé, « en attente de validation » entre
la fin du tir et le sceau.

Cette ligne existe en deux exemplaires :

- `shared/duels/LigneRencontre.tsx`, écrit par cette US et partagé par les trois formats sans arbre ;
- `LigneDuel`, interne à `features/tableaux/VueTableaux.tsx`, inchangé.

**Ce qui n'est *pas* dupliqué, et c'est ce qui borne la dette** : la logique de lecture est déjà
partagée dans `shared/duels/rencontre.ts` — `etatRencontre`, `scoreRencontre`, `gagnantAffiche`,
`participants` —, et elle est **testée** (`shared/duels/rencontre.test.ts`). Ce qui reste double est
le **JSX** et la **feuille de style**. Une divergence de règle est donc improbable ; une divergence
d'apparence ne l'est pas.

**Pourquoi ne pas l'avoir fait tout de suite.** Migrer `LigneDuel` suppose de rallier les classes
`tableaux__*` aux `encours__*` et de rejouer `tableaux.css` sur ses **deux** surfaces calibrées
(360 px tenu à la main, projection lue à cinq mètres). C'est un remaniement d'une vue livrée, sans
bénéfice pour le CA de l'US, et le mêler à une US de format aurait fait porter à celle-ci un risque
de régression visuelle sur l'écran de salle qu'elle n'a aucune raison de prendre.

⚠️ **Ce n'est pas un « remède structurel » différé au sens du `CLAUDE.md`.** Ce dernier vise
l'introduction d'un **pattern** sur preuve de 3ᵉ occurrence déjà écrite ; ici le partage a bien eu
lieu (`LigneRencontre` sert **trois** formats d'un coup), et ce qui reste est un unique appelant
historique non rallié. La dette est donc « une migration à finir », pas « une abstraction à
inventer ».

**Le déclencheur** : la première US qui touche l'un des deux rendus. À ce moment-là, rallier coûte
moins cher que de modifier deux fois.

### DETTE-050 — les rendus d'erreur ad hoc ne sont pas ralliés à `texteErreur`

**Constat.** Le front a deux façons d'afficher une erreur. Le composant partagé
`shared/ui/MessageErreur` réduit toute erreur **non-`ErreurApi`** à « Une erreur est survenue. » — un
imprévu technique n'a pas à s'afficher à l'utilisateur (règle 5 : le mapping se fait à la frontière
API, aucun message interne ne fuit). À côté, une quinzaine de **rendus ad hoc contextuels** gardent
leur propre phrase (« Complétude injoignable — … », « Actions injoignables — … ») et interpolent
`erreur.message` **sans ce filtre**.

`DETTE-004` (E00US013) avait examiné ces rendus et les avait **laissés** hors du composant générique.
La décision était bonne sur son objet — ils ont une phrase contextuelle utile, les fondre dans
`MessageErreur` l'aurait perdue — mais elle n'a pas vu que le carve-out portait sur le **rendu** et
emportait au passage le **narrowing**, qui, lui, n'a rien de contextuel.

**Pourquoi c'est visible en salle et pas ici.** `fetchJson` ne lève une `ErreurApi` que sur réponse
HTTP non-ok. Une coupure réseau ne produit pas de réponse : `fetch` rejette un `TypeError:
Failed to fetch` (`NetworkError when attempting to fetch resource` sous Firefox). En développement,
le front parle à `localhost` — qui ne coupe jamais. Le jour J, ~30 tablettes BYOD sur un LAN sans
internet : c'est le mode de panne **le plus probable** de l'application.

**Ce qu'E16US003 a fait, et pourquoi elle s'est arrêtée là.** L'US a extrait `texteErreur` et rallié
les **cinq** rendus de son périmètre (`Completude` ×2 — lecture *et* mutation —,
`CompletudeAdministrative`, `Accueil`, `FriseCycleDeVie`). Elle n'a pas converti le reste du dépôt :
ce sont des écrans qu'elle ne touchait pas, sur des sujets sans rapport avec la complétude, et une
US ne réécrit pas quinze fichiers hors de son objet.

⚠️ **Le piège que cette ligne existe pour éviter.** La première rédaction de `texteErreur.ts`
affirmait « trois sites partagent cette forme » — c'était faux (il y en avait cinq dans le périmètre,
une quinzaine dans le dépôt), et deux fuites subsistaient **dans les fichiers que le correctif venait
d'éditer**, dont l'une dix lignes sous celle qu'il corrigeait, sur l'action irréversible du produit.
La revue l'a mesuré en exécutant le cas. Leçon à retenir pour la résorption : **un invariant extrait
et appliqué à moitié est plus trompeur qu'un invariant absent**, parce que l'existence du module fait
croire le chantier terminé. Donc : d'un bloc, avec un décompte terrain (`grep -rn "error.message"`),
pas au fil de l'eau.

**Marqueurs posés le 08/08/2026** (mise en conformité du backlog). La dette était **ouverte sans
aucun marqueur `# DETTE-050` dans le code** — donc invisible depuis les fichiers qu'elle concerne,
c'est-à-dire exactement le mode d'oubli qu'elle dénonce elle-même. **Chaque rendu porte désormais
son propre marqueur** — 13 marqueurs sur 8 fichiers.

> *Rectifié en revue le 08/08/2026.* Le premier jet ne posait qu'**un** marqueur par fichier, celui
> qui annonce le compte. C'était insuffisant et pour la raison même que cette fiche dénonce :
> `CLAUDE.md` § Dette exige le marqueur « à l'**endroit exact** du raccourci » ; qui édite le 4ᵉ
> rendu de `PanneauBarrages.tsx` ne voyait rien, et supprimer le bloc annoté aurait emporté le
> marquage des quatre autres. Les marqueurs des sites secondaires sont volontairement **nus**
> (`// DETTE-050`) : le commentaire explicatif reste au premier de chaque fichier.

Le décompte terrain a **corrigé la liste de cette fiche** sur trois points — à lire avant de
résorber, sans quoi la première heure se passe à chercher des fichiers qui n'existent pas :

| Écrit ici | Réel |
|---|---|
| `features/barrages/PanneauBarrages.tsx` | **`features/competition/PanneauBarrages.tsx`** — il n'y a pas de feature `barrages` |
| `features/competition/Tournois.tsx` | **`features/tournois/Tournois.tsx`** |
| `features/duels/SaisieDuels.tsx` | **faux positif, à retirer du périmètre.** Le fichier est `features/saisie-duels/SaisieDuels.tsx`, et surtout il **ne fuit pas** : `MessageErreurDuel` n'interpole le message brut que dans une branche gardée par `erreur instanceof ErreurApi && erreur.code === 'duel_desynchronise'`, et retombe sur `MessageErreur` pour tout le reste. C'est le **contre-exemple** de la dette, pas un cas d'elle. |

Total réel : **13 rendus dans 8 fichiers**, plus les 2 copies du narrowing — et non 12 sites comme
annoncé. ⚠️ **Restent hors périmètre, délibérément** : les blocs `mutation.error?.message` d'
`Archers.tsx`, `NouvelArcher.tsx` et `Departs.tsx`. Ils interpolent aussi un message brut, mais ne
sont montés que sur un **409 métier** (`ArcherEngage`, confirmations), donc l'erreur y est une
`ErreurApi` par construction. Les rallier ne changerait rien à l'affichage ; les compter gonflerait
le chantier d'un tiers pour rien. *(Distinction à refaire au moment de résorber : c'est le seul
critère qui sépare un rendu à corriger d'un rendu déjà sûr.)*

---

### DETTE-001 — suppression de tournoi non cascadée

**Constat.** Aucune FK de la descendance de `tournoi` ne porte de politique de suppression, ni côté
modèle (`ForeignKey(...)` sans `ondelete`) ni côté migrations
(`sa.ForeignKeyConstraint([...], [...])`), et le service de suppression ne purge pas les enfants.
La descendance compte trois natures de liens :

- **enfants directs** de `tournoi` — `categorie`, `archer`, `blason` (FK → `tournoi.id`),
  `gabarit_salle` pour son **instance** appliquée à un tournoi (E01US008 ; les modèles de
  bibliothèque, `tournoi_id NULL`, ne sont pas concernés), **`deroule_etape`** (E01US025, la
  *définition* du déroulé — [ADR-0076](adr/0076-un-deroule-defini-une-fois-un-avancement-par-depart.md)),
  `depart` (E02US004, créneau du tournoi — [ADR-0017](adr/0017-le-depart-est-un-creneau-du-tournoi.md)),
  `scoreur` (E10US003, personne habilitée à valider — [ADR-0025](adr/0025-mode-d-identite-scoreur-par-code-individuel.md))
  et `poste` (E04US001, credential d'une cible — [ADR-0029](adr/0029-mode-d-identite-poste-de-cible-et-jeton-de-poste.md)) ;

  ⚠️ **`phase` a quitté cette liste** (E01US025, [ADR-0075](adr/0075-le-depart-est-la-portee-sportive.md),
  migration `0042`) : elle pend au **départ**, elle est donc un enfant *indirect* — et l'ordre de
  cascade s'en trouve changé, les phases devant partir **avant** les départs. Y voir encore un
  enfant direct ferait écrire un `DELETE FROM phase WHERE tournoi_id = ?` sur une colonne qui
  n'existe plus. La `deroule_etape` qui la remplace au premier rang, elle, n'a **aucune**
  descendance : elle se supprime sans ordre particulier ;
- **enfants indirects** — `score` (FK → `archer.id`), donc bloquant pour la suppression d'un `archer`,
  elle-même requise par toute cascade partant du tournoi ; et `inscription` (E02US009), qui porte
  **deux** FK de la descendance — `archer.id` **et** `depart.id` — et bloque donc la suppression de
  **l'un ou l'autre** de ses parents : dans une cascade partant du tournoi, les inscriptions doivent
  partir **avant** les archers et avant les départs ;

  ⚠️ **`franchissement_arret` est le point le plus profond de l'arbre** (E05US033,
  [ADR-0091](adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md) §3) : `FK → phase.id`
  sans `ON DELETE`, donc un cran **sous** `phase`, elle-même sous `depart`. L'ordre de cascade compte
  désormais **trois** niveaux sur cette branche : `franchissement_arret` → `phase` → `depart`. Une
  résorption qui reprendrait l'ancienne énumération (« phases avant départs ») buterait en
  `IntegrityError` sur la première phase ayant connu une pause. ⚠️ **L'US avait posé le marqueur et le
  mentionnait dans l'en-tête de sa migration, mais n'avait pas élargi cette section** — deux gestes
  sur trois, alors que la procédure ci-dessus les énumère noir sur blanc. Relevé par l'axe C2 de la
  revue, corrigé avant la PR : qui écrira l'ordre de cascade le lira **ici**, pas dans une migration ;

  ⚠️ **`arret_de_circonstance` porte DEUX FK de la descendance** (E05US034,
  [ADR-0092](adr/0092-un-arret-pose-le-jour-j-appartient-au-creneau.md)) : `depart_id` **et**
  `phase_id`, aucune avec `ON DELETE`. Elle doit donc partir **avant `phase` et avant `depart`** —
  c'est la première table de l'arbre à bloquer *deux* parents de branches différentes, comme
  `inscription` le fait pour `archer`/`depart`. ⚠️ **Le manque s'est reproduit à l'identique, deux US
  de suite** : les marqueurs étaient posés (`models.py`, migration `0049`) mais cette section n'avait
  pas été élargie — les mêmes deux gestes sur trois que ceux racontés juste au-dessus, alors que le
  paragraphe qui les raconte était sous les yeux. Relevé par l'axe C2, corrigé avant la PR. Ce qui
  échoue ici n'est pas l'attention mais le **procédé** : rien dans le dépôt ne réclame l'inscription,
  aucune porte ne rougit, et la seule chose qui la déclenche est de relire cette section. La rendre
  vérifiable (un contrôle qui compare les FK sans `ON DELETE` du modèle à l'énumération de cette
  ligne) est une **US**, pas une note ;
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
> (elle efface ses résultats), et un archer qui **abandonne** relève du forfait ([E04US015](../stories/E04-saisie-scores.md), qui a absorbé ex-E12US004),
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

**Élargissement au front (E16US001, 05/08/2026).** Le plafond de 4 n'est pas qu'une constante du
domaine : le front en porte **trois copies** — `POSITIONS = ['A','B','C','D']` dans `Placement.tsx`
et dans `Duels.tsx`, et `PLAFONDS = [1,2,3,4]` dans les deux écrans de gabarit. E16US001, qui a
ajouté un aperçu des couloirs sur le plan de salle, **aurait ajouté une quatrième copie** ; elle
dérive à la place la lettre de son rang (`String.fromCharCode(65 + rang)`) et itère sur `PLAFONDS`,
de sorte que cet écran-là suivra automatiquement. Les trois autres sites, eux, restent à balayer :
le jour où E01US019 relève le plafond, un sélecteur proposera « jusqu'à 6 couloirs » pendant que les
grilles de placement et de duels continueront de n'afficher que `A`→`D`, **silencieusement**.

**Résorption attendue.** **E01US019** : capacité non bornée, positions au-delà de `D` (`E`, `F`…),
placement adapté, **et les trois sites front ci-dessus**. Marqueur `DETTE-010` à poser sur
`gabarit_salle.py` à cette occasion.

⚠️ **À faire dans le même chantier que [DETTE-042](#dette-042--le-métier-dit--couloir-de-tir--le-code-dit-position)**
(renommage `position` → `couloir`) : les deux dettes portent sur le **même symbole** et la **même
colonne**. Les séparer coûterait deux migrations Alembic sur la même colonne.

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
**physique**. Le plan de duels ne pose que le 1ᵉʳ tour ([ADR-0048](adr/0048-cote-a-cote-des-duellistes-par-reordonnancement.md)) ;
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
[ADR-0006](adr/0006-ubiquitous-language.md) exige un domicile unique pour le vocabulaire
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

**Ce que la 3ᵉ occurrence a appris — E07US005 (04/08/2026).** L'US a d'abord écrit un **troisième**
domicile (`features/tableaux/presentation.ts`, `libelleTour` + `libelleEnjeu`), et la revue l'a
relevé sur **trois axes**. Deux enseignements, qui valent plus que le compte :

1. **Le coût de la duplication n'est pas théorique, il s'est matérialisé le jour même.** Le
   troisième domicile produisait « Places 5-6 » là où le domaine dit « Match pour la 5ᵉ place »,
   sur **deux onglets voisins de la même appli publique** (« Affectations » sert le libellé du
   domaine, « Tableaux » servait le sien) — exactement le préjudice que la colonne « Impact »
   décrit, passé de deux à trois écrans.
2. **Et surtout : la copie était fausse.** Elle nommait un match par sa distance à la finale sans
   voir que `place_en_jeu` n'existe que sur les matchs **terminaux** — donc elle appelait
   « Demi-finale » un match des places 5-8. Le domaine ne savait pas mieux faire à ce moment-là :
   le correctif a **enrichi `libelle_tour` d'un argument `plage`**, ce qui a corrigé du même coup
   le **panneau de routage** (E07US008), qui portait silencieusement le même défaut. C'est
   l'argument le plus net en faveur de la résorption : un domicile unique, corrigé une fois,
   corrige toutes les surfaces.

**La dette reste donc à deux domiciles** (le troisième a été refermé avant merge), mais son enjeu a
**changé de nature** : ce n'est plus une divergence de style, c'est un **affichage faux** sur l'écran
du scoreur dès qu'une phase descend sous le podium (« Finale » sur le match de la 5ᵉ place,
« Demi-finales » sur la branche 5-8, trois matchs fusionnés sous un même titre par `grouperParTour`).
Le remède est inchangé — `features/saisie-duels/duel.ts` doit à son tour consommer le libellé servi. E07US005
montre que ce chemin fonctionne : le DTO public porte désormais `libelle`, il n'y a plus qu'à faire
pareil sur le DTO de duel du scoreur.

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
la séquence invalide les références et oblige à les réécrire. **Quatre** sites le font aujourd'hui, tous
corrects et couverts par des tests :

- `ServicePhases._remapper` — réordonnancement et suppression (avec recompactage) ;
- `ServiceBaremeQualification._decaler_dun_cran` — insertion de la qualification en tête ;
- `DerouleRepository.reordonner` et `PhaseRepository.reordonner` (E01US025) — l'écriture d'ensemble
  qui gare les rangs hors de portée avant de les reposer. Ces deux méthodes de port **n'existent que
  pour cela** : c'est la contrepartie d'une unicité `(tournoi, ordre)` / `(départ, ordre)` qu'on
  garde **parce qu'**elle dit vrai.

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

**⚠️ Aggravée par E01US025 / [ADR-0076](adr/0076-un-deroule-defini-une-fois-un-avancement-par-depart.md)
— et la clause « 2 sites, on ne pose pas de pattern » est **périmée**.** Trois choses ont changé le
même jour :

1. **le rang n'est plus seulement la clé de la séquence, il est aussi la clé de jointure**
   définition ↔ avancement. `phase` ne porte plus sa définition : elle la reçoit de l'étape de
   **même `ordre`**. Un rang mal remappé ne fait donc plus seulement pointer une *source* vers la
   mauvaise phase — il fait exécuter à un créneau le **barème, le grain et les prélèvements d'une
   autre étape** ;
2. **les écrivains passent de 2 à 4** : `ServicePhases._remapper` et
   `ServiceBaremeQualification._decaler_dun_cran` sont rejoints par `DerouleRepository.reordonner`
   et `PhaseRepository.reordonner`, deux méthodes de port **dont l'unique raison d'être** est de
   contourner l'unicité `(tournoi, ordre)` / `(départ, ordre)` en garant les rangs hors de portée
   avant de les reposer ;
3. le seuil de la **règle 16 est donc atteint et dépassé** — le registre s'était explicitement fixé
   rendez-vous « au jour où un 3ᵉ écrivain apparaît ».

**Le remède structurel est PROPOSÉ, pas fait ici** (règle : ADR + US dédiée, jamais en douce dans
l'US courante). Sa forme : une FK `phase.etape_id → deroule_etape.id`, le rang restant porté par la
**seule** étape. Le contre-argument est sérieux et doit être **écarté explicitement**, pas ignoré —
`infrastructure/db/models.py` le formule ainsi : « une FK dupliquerait l'information tout en pouvant
en diverger ». Il reste par ailleurs vrai que `FormatTournoi` ne peut pas s'ancrer autrement que par
l'ordre, ses `ModelePhase` n'ayant **pas** d'identité (ADR-0060 §5) : la résorption sera donc
**asymétrique** — identité côté édition concrète, ordre côté bibliothèque —, ce qui est précisément
ce que l'ADR devra trancher.

**Résorption attendue — décidée le 07/08/2026.** [ADR-0078](adr/0078-la-sequence-s-ancre-sur-l-identite-de-l-etape.md)
tranche : la séquence s'ancre sur l'**identité** de l'étape (`phase.etape_id`, `etape_source_id`),
le rang ne décrivant plus que l'ordre d'affichage ; `FormatTournoi` **garde** l'ancrage par ordre,
ses `ModelePhase` n'ayant pas d'identité (asymétrie assumée, la conversion se faisant à
`appliquer`). Le contre-argument de `models.py` — « une FK dupliquerait l'information » — y est
écarté explicitement : le remède ne duplique pas, il **sépare** les deux rôles que le rang cumulait
depuis ADR-0076. Planifiée en **E05US022**. Ce n'est plus « attendre un déclencheur » : le
déclencheur a eu lieu.


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

**⚠️ Élargie par E05US021 — et la justification ci-dessus ne suffit plus seule.** `appliquer` écrit
désormais une **troisième** fois, après la pose des phases : la recopie de `effectif_minimum_exige`
sur le tournoi ([ADR-0069](adr/0069-effectif-minimum-deduit-et-exige.md) §4). Une panne entre les
deux laisse un tournoi dont les **phases** viennent du nouveau format et dont l'**exigence** est
encore celle du précédent. Cet état-là n'est pas « reconstituable en réappliquant un format » au
sens où on l'entendait : il est **silencieux** — rien à l'écran ne le signale — et il se manifeste
soit en bloquant un démarrage légitime (exigence trop haute conservée), soit en en autorisant un que
la règle du club interdisait (exigence perdue). Il reste sans perte de données de tir, mais la
cotation « faible » tient maintenant à la seule improbabilité de la panne, plus à l'innocuité de son
résultat. C'est un **argument de plus** pour le remède ci-dessous, pas un changement de gravité.

**Pourquoi elle est prise.** Le remède est une opération atomique **sur l'adapter concret** — un
`remplacer_sequence(tournoi_id, phases)` en une seule session, sur le patron `consigner_dans`
d'[ADR-0035](adr/0035-atomicite-acte-trace-session-partagee.md). C'est un ajout au **port** et à son
adapter, donc une modification qui dépasse le périmètre de cette US, pour un cas dont la fenêtre est
de quelques millisecondes et la perte reconstituable.

**⚠️ Élargie par E01US025 à `ServicePhases.reordonner` et `ServicePhases.supprimer` — et la
conséquence y est plus grave que partout ailleurs.** Depuis [ADR-0076](adr/0076-un-deroule-defini-une-fois-un-avancement-par-depart.md),
éditer le déroulé écrit **des deux côtés** de la couture définition ↔ avancement, en transactions
séparées : `reordonner` fait `DerouleRepository.reordonner` puis `_realigner_avancements` (deux
écritures) ; `supprimer` en fait **trois** — retrait des avancements du rang, retrait de l'étape,
puis réalignement et recompactage.

Ce qu'une panne entre deux de ces écritures laisse n'est **pas** un « tournoi sans phase », visible
et reconstituable. Le rang **est** la clé de jointure vers la définition : une phase restée sur son
ancien ordre pointe **l'étape voisine**. Le créneau exécute alors un **autre barème, un autre grain,
d'autres prélèvements** — sans la moindre erreur, sans rien à l'écran, et l'organisateur n'a aucune
raison de rouvrir l'atelier. C'est le seul état de cette dette qui puisse **fausser des résultats**
plutôt que d'interrompre une configuration.

L'improbabilité est la même qu'ailleurs (quelques millisecondes) et les gardes en amont sont
inchangées ; c'est la **conséquence** qui change de nature, et c'est ce qui doit peser au moment de
choisir quand résorber.

**Résorption attendue.** À la première US qui touche `PhaseRepository` ou `DerouleRepository` — ou au
premier incident. Le remède est le même pour les trois sites : une écriture atomique **sur l'adapter
concret**, patron `consigner_dans`. Marqueurs `# DETTE-025` posés sur la boucle de suppression **et**
sur la recopie de l'exigence dans `ServiceFormats.appliquer`, et sur les **deux couples d'écritures**
de `ServicePhases.reordonner` / `.supprimer` — les cinq écritures que le remède devra réunir par
paires.


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

> ✅ **Rétrécie le 09/08/2026 par E05US023 — volet poules refermé** ([ADR-0083](adr/0083-le-contrat-de-phase-jouable.md)).
> Le format le plus riche des quatre est désormais jouable de bout en bout : réglé à l'atelier
> (`config.poules`, à la racine du `config`, sans migration), posé en salle (`placement_poule`, migration 0045),
> tiré avec le pavé de duel d'E04US013, classé (§10.1) et **lu** par une phase avale
> (`domain/classement_de_poules.py` + port `LecteurClassementPoules`). Le barrage de portée `poule`
> referme le classement, ce qui ferme la boucle que cette dette laissait ouverte depuis E05US015.
>
> ⚠️ **Ce que la tranche n'a pas fermé, et qu'il ne faut pas croire fermé** : le routage ne sait
> toujours pas dire à un membre de poule où il tire ensuite (`route_l_archer=False`), les poules
> n'entrent pas au palmarès, et le forfait en poule n'est offert nulle part. Ces trois-là sont
> **hors du périmètre d'E05US023**, pas des oublis — et aucun n'est visible depuis cette ligne, qui
> ne parle que d'« appelant de production ». Le registre de contrat, lui, les dit capacité par
> capacité.
>
> **Le signal d'écart ne se tient plus à la main.** `contrat_phase.TYPES_SIGNALES_EN_ECART` le
> dérive du registre : un type devient jouable, il sort du signal, à un seul endroit. C'est ce qui
> garantit que les trois tranches suivantes ne pourront pas le laisser mentir.


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
- **Exécution — ⚠️ RÉSORBÉE POUR LES RANGS le 03/08/2026 (E05US020, [ADR-0068](adr/0068-le-moteur-consomme-les-prelevements-declares.md)).**
  `ServiceSaisieDuels._preleves` lit désormais `Phase.sources` : une phase qui déclare « les rangs 1
  à 32 » monte un tableau de 32, et « les rangs 33 et suivants » se résout sur l'effectif réel. Le
  test de caractérisation posé ci-dessous **a échoué comme prévu** et a été remplacé par son pendant
  positif. **Ce qui reste** : `le_reste` et `par_issue_de_tour` demeurent **inertes** — vérifié dans
  le code, aucune des deux n'est résolue nulle part (`effectif_selectionne`, `resoudre`, `intervalle`
  rendent `None`) ; leur donner un sens dans un service d'exécution serait décider une règle métier
  au mauvais endroit (`DETTE-033`). Et une source dont la phase amont n'est **pas** la qualification
  garde le comportement d'avant.
- **Exécution en cascade — ✅ RÉSORBÉE le 08/08/2026 (E05US024, [ADR-0080](adr/0080-un-prelevement-lit-le-classement-de-sa-phase-source.md)).**
  La restriction ci-dessus est levée : `preleves` reçoit un **résolveur** de classement et lit chaque
  source dans la phase qu'elle désigne. `domain/classement_de_tableau.py` lit un tableau comme un
  classement (fourchettes *ex æquo* fermées par la politique `aggregation`, ADR-0067, plutôt que par
  un départage local qui aurait contredit le palmarès du même jour). `effectif_minimum` remonte la
  chaîne des sources, et refuse de chiffrer un plancher que la fenêtre amont plafonne.
  ⚠️ **Le motif de report d'E05US020 était périmé, pas faux** : il invoquait un cycle service →
  service, or `tableau.positions_acquises` est produit par `ServiceSaisieDuels` lui-même — une
  **récursion**, sur un graphe rendu acyclique par l'antériorité des sources (ADR-0045 §3). Leçon à
  garder : *une justification de report se re-vérifie à la reprise, elle ne se recopie pas.*
  ⚠️ **Ce que cela coûte** : la récursion multiplie les reconstructions de `DETTE-031` par le
  **nombre de phases de la chaîne** amont. Un premier jet annonçait « par la profondeur de la
  cascade » et mémoïsait **par niveau** : sur un déroulé en **diamant** (une super-finale nourrie
  par le principal *et* la consolante, tous deux nés du même tableau), la phase commune était
  reconstruite une fois par chemin — un coût **exponentiel** en profondeur, et une inexactitude qui
  allait dans le sens rassurant. Le cache est désormais créé au sommet et **descendu** dans toute la
  récursion (correctif de revue, axe C2) ; le cache **transverse aux requêtes** reste `DETTE-031`,
  non rouvert. Les réglages
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

**⚠️ E06US003 en a résorbé une part (02/08/2026, [ADR-0066](adr/0066-seuil-de-barrage-porte-par-la-politique-tiebreak.md)).**
Deux des trois griefs tombent pour le seul `barrage.py` : il a désormais des **appelants de
production** (service, API, écran) et le **premier réglage réellement porté par `config.policies`**
(`tiebreak.jusqu_au`, lu et écrit par le repository de phase, résolu par le registre) ; et
`classement.py` **passe enfin par `PolitiquesPhase.tiebreak`** au lieu de réimplémenter §8.1 à la
main — la couture réclamée ci-dessus existe, même si `scoring` ne l'emprunte pas encore, donc
`ScoreAvecHandicap` reste inerte.

**Ce que cela ne résorbe pas, et il faut le dire net** : `poule.py`, `big_shoot_off.py`, `suisse.py`,
`colline.py` n'ont **toujours aucun consommateur** (vérifié dans le code : aucun import hors domaine
et tests). Le barrage sait *techniquement* servir un classement de poule ou une manche de Big Shoot
Off — `PorteeBarrage` porte les trois valeurs et la table les accepte, précisément pour éviter une
migration de données plus tard —, mais il n'existe **aucun classement de poule calculé quelque part**
où le brancher. Câbler ces deux portées aurait produit une surface pour une phase que l'application
ne sait pas dérouler, c'est-à-dire aggraver cette dette en ayant l'air de la traiter.

**Résorption attendue.** **US dédiée du chantier moteur**, à cadrer : faire consommer `Phase.sources`
par le peuplement des phases (le point dur — il touche `ServiceSaisieDuels._decor`, donc le déroulé
réel du jour J), porter les réglages **restants** dans `config.policies` (`nb_poules`, `nb_manches`,
`portee_de_defi`, `restants`), et rebrancher `classement.py` sur la famille **`scoring`** pour que le
handicap s'applique — la couture `tiebreak` montrant désormais comment s'y prendre.
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

**Élargissement du 04/08/2026 — E07US005.** Un **troisième** endpoint au même régime :
`GET /api/v1/tableaux/{id}` (`ServiceTableauxPublics.pour_tournoi`), public, non authentifié, sans
cache ni plafond. Deux nuances propres à celui-ci :

- il appelle `ServiceSaisieDuels.etat_tableau` **une fois par phase en tableau**, comme le palmarès
  (E06US004) — donc le coût croît avec le déroulé, pas seulement avec le nombre de lecteurs ;
- il ajoute **deux** surfaces de polling, dont une du type le plus coûteux : l'onglet public
  « Tableaux » sur le **téléphone de chaque spectateur** (comme la carte de suivi d'E07US008), et la
  vue `en_cours` de l'**écran de salle** (`tableaux` jusqu'à E05US031, migration `0047`).

La garde `actif` du hook limite la casse (la requête n'est montée que par le composant réellement
affiché — le correctif qu'`EcranSalle` avait dû appliquer à `useSuiviDeroule`), mais elle ne change
pas le régime : le cache React Query est **par navigateur**, rien ne se mutualise entre appareils.

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

Marqueur `# DETTE-031` posé sur `ServiceSuiviDeroule.pour_tournoi`, sur `ServiceRoutage._grille`
(`backend/application/routage.py`) et, depuis E07US005, sur `ServiceTableauxPublics.pour_tournoi`,
la route `GET /api/v1/tableaux/{id}` et `frontend/src/features/tableaux/hooks.ts`. Depuis
**E16US004**, également sur `frontend/src/features/suivi/VueSuivi.tsx`.

#### Élargissement du 08/08/2026 — E16US004 : la protection par montage conditionnel ne borne plus

Le récapitulatif de journée de l'onglet public **« Suivi »** lit désormais les arbres de duels
(`useTableauxDesDeparts`). C'est une **troisième surface de polling** de `GET /api/v1/tableaux/{id}`,
et c'est la plus exposée des trois — pour une raison qui n'a rien à voir avec le volume :

**ce qui bornait cet endpoint jusqu'ici n'existe plus.** Le commentaire de `features/tableaux/hooks.ts`
l'énonçait noir sur blanc : *« ce qui limite la casse est le montage conditionnel du composant »* —
on ne payait la reconstruction que si l'on **ouvrait** l'onglet « Tableaux ». Or « Suivi » est
l'onglet d'**atterrissage par défaut** de tout spectateur qui suit un archer (D-09) : la lecture la
plus chère du serveur part maintenant **dès l'ouverture de l'appli**, sur chaque téléphone de la
salle, sans que personne ait rien demandé. Le garde-fou n'a pas été affaibli par distraction : il a
été **contourné par la navigation**, ce qu'aucune porte mécanique ne peut voir.

Deux bornes subsistent, et elles sont volontaires :
- **aucun poll sans suivi** — la requête n'est montée que si l'on suit au moins un archer ;
- **seuls les départs concernés** sont interrogés, dérivés des plans déjà chargés, et non tous ceux
  du tournoi. Corriger le bug d'origine (le récapitulatif ne lisait que le créneau de la *salle*,
  amputant l'archer du matin dès l'après-midi) imposait d'élargir la lecture ; la borner aux départs
  où les archers suivis tirent est ce qui empêche ce correctif de multiplier la dette par le nombre
  de créneaux. En pratique : un départ, deux si l'on suit des archers de deux créneaux.

*Relevé par **quatre axes** de revue. Aggravant : le corps de commit affirmait l'inverse — « `# DETTE-031`
inchangée, ni élargie ni réduite — la requête existait déjà sur cet écran ». C'était faux : ce qui
existait déjà sur `VueSuivi`, c'était `useAffectations`, un **autre** endpoint. Une affirmation
rassurante et fausse dans un corps de commit coûte plus cher qu'un oubli : elle décourage la
vérification suivante. Le commentaire de `hooks.ts` qui attribuait la protection au montage a été
corrigé dans le même geste, sans quoi il aurait menti au prochain mainteneur.*

*Relevée en revue (axe adversarial) : la dette était **assumée en commentaire** dans
`frontend/src/features/suivi-deroule/hooks.ts` — donc réelle et connue — mais **pas tracée ici**,
ce que le § Dette de `CLAUDE.md` compte comme dette silencieuse. **E07US008 a rejoué le même geste
et s'est fait reprendre de la même façon** : la charge était assumée en commentaire à quatre
endroits (docstring de la route, `hooks.ts`, `VueSuivi.tsx`, ADR-0065), sous le mauvais numéro de
dette, et le registre n'était pas touché. Trois axes de revue l'ont relevé — le fait que le même
défaut se reproduise sur l'US suivante est en soi le meilleur argument pour la porte de revue.*

#### Élargissement du 18/08/2026 — E05US031 : trois reconstructions de plus, sur un onglet public

L'onglet public « Tableaux » devient **« En cours »** et rend la phase qui se joue quel qu'en soit le
format. Il monte donc, selon le format du moment, `GET /poules/etat/…`, `GET /suisse/etat/…` ou
`GET /big-shoot-off/etat/…` — **trois routes déjà au régime de cette dette** (`ServicePoules.etat` et
`ServiceSuisse.etat` y sont nommés depuis `E05US023` et `E05US026`), auxquelles s'ajoute
`ServiceBigShootOff.etat`, qui rejoue la phase entière à chaque lecture (`_rejouer`) et n'était
jusqu'ici lu que par des scoreurs authentifiés.

**Ce que cette US change tient en deux points, et le second est le seul qui compte :**

1. `GET /big-shoot-off/etat/` passe de **scoreur** à **ouverte**. Le nombre de lecteurs potentiels
   passe de « les bénévoles de la ligne » à « tout le monde dans la salle » ;
2. surtout, **la surface qui monte ces lectures est l'onglet public**, en autant d'exemplaires qu'il
   y a de spectateurs, le cache React Query étant par navigateur. C'est exactement l'aggravation
   qu'`E07US005` avait apportée sur `/tableaux/{id}` — sauf qu'ici elle porte sur **trois** routes de
   plus, et sur celles qui rejouent une phase de duels tir par tir.

**Ce qui borne encore, et il faut être précis sur ce qui ne borne pas :**

- **le montage conditionnel joue** — une seule des trois routes est montée à la fois, celle du format
  de la phase affichée, et rien n'est monté tant que l'onglet n'est pas ouvert. Contrairement à
  `E16US004`, « En cours » n'est **pas** l'onglet d'atterrissage (c'est « Suivi », ou « Classement »
  à défaut) : la protection que cet élargissement-là avait perdue tient toujours ici ;
- **aucun `refetchInterval`** sur `useEtatPoules`, `useEtatSuisse` ni `useEtatBigShootOff` : le
  rafraîchissement passe par l'invalidation globale de `useRealtime`, donc par les **écritures
  réelles** et non par une horloge. Un onglet ouvert sur une salle au repos ne coûte rien ;
- **la remontée d'historique ne coûte rien de plus** : changer de ronde ne relance aucune requête (la
  photo porte toutes les rondes), et une phase déjà consultée est en cache.

⚠️ **Ce qui n'est pas borné** : chaque **validation de rencontre** invalide globalement, donc chaque
spectateur ayant l'onglet ouvert paie une reconstruction de la phase en cours. Sur une phase de
poules à 36 archers en fin de tour, c'est le pic de charge de la journée — et il arrive mécaniquement
au moment où le plus de monde regarde.

*Élargissement **relevé et inscrit dans le commit de l'US**, sans attendre la revue : c'est la 4ᵉ fois
que cette dette s'élargit, et les trois précédentes ont toutes dû être reprises en revue parce que le
code l'assumait en commentaire sans que la ligne bouge.*

#### Élargissement E05US032 — le suivi atteint enfin les services de format, et le paie

Jusqu'ici, `ServiceSuiviDeroule` **n'atteignait jamais** `ServicePoules`, `ServiceSuisse` ni
`ServiceBigShootOff` : son unique lecture coûteuse, `_duels_tranches`, sort tôt sur `phase.type not
in TYPES_EN_TABLEAU`. En branchant le port `LecteurAvancementDePhase` ([ADR-0090](adr/0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md) §5),
`_avancement_lu` ouvre un chemin **neuf** depuis cet endpoint public vers les trois `etat()`, qui
recomposent intégralement leur phase, **chaîne de sources amont comprise**.

Deux garde-fous posés en réponse à la revue :

- **le lecteur n'est interrogé que pour une phase démarrée** (`STATUTS_DEMARRES`). Sans cette garde,
  chaque poll recomposait aussi les phases `à venir` et `terminée` — la majorité d'un déroulé en fin
  de journée — pour un résultat dont `avancement_bloc` jette le `tour_courant` de toute façon ;
- le marqueur du service, qui disait « la reconstruction de chaque phase **en tableau** », devenait
  faux dans le commit qui le laissait en place : il nomme désormais les deux chemins.

⚠️ **Ce qui reste, et c'est l'écart réel** : le port n'a **pas** le paramètre `resolveur` de son
jumeau `LecteurClassementDePhase` (`application/prelevement.py`), dont la docstring dit pourtant
« en laisser le service de format fabriquer un neuf ferait payer deux fois un tableau amont partagé
(`DETTE-031`) ». Un déroulé qualif → poules → suisse refait donc une descente complète de la chaîne
amont **par phase**, là où le jumeau la partage. ADR-0090 revendiquait reprendre ce patron « à la
lettre » — c'était inexact, l'ADR a été corrigé, et le remède est **borné et connu** : porter le
résolveur au port. Il se traite avec `E05US033`, qui rouvrira ces trois réalisations de toute façon.

*Relevé par **cinq** axes de revue, ce qui est le score le plus élevé du registre sur cette ligne —
et le signal que le réflexe « une US qui touche au suivi élargit DETTE-031 » n'est toujours pas
acquis à l'écriture.*

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

### DETTE-033 — un battu repris par la **séquence** n'est pas annoncé

`ServiceRoutage` sait dire « repêché » à un archer que le **routing** fait ressortir du tableau
(`VersRepechage` → issue `REPECHE`, [ADR-0065](adr/0065-rang-acquis-lu-sur-la-plage-et-issue-repechee.md) §2).
Il ne sait **pas** le dire à celui qu'une **phase avale prélève** par
`SourcePhase.par_issue_de_tour(ordre, tour, PERDANTS)` : celui-là est classé dans ce tableau, lit sa
fourchette de rangs, et rien ne lui apprend qu'il rejoue.

Les deux moitiés ne se lisent pas au même endroit, et c'est la racine :

| Moitié | Source | Grain |
|---|---|---|
| routing | `tableau.routing.route(contexte)` | le **match** |
| séquence | `phase.sources` des phases postérieures | le **tour** |

**Pourquoi c'est assumé et non corrigé dans l'US.** Un correctif de revue a posé la `destination`
sur les lignes `TERMINE`. La 2ᵉ passe l'a démoli **de deux façons opposées**, chacune preuve
d'exécution à l'appui :

- `dernier` est le **dernier match joué**, pas le match perdu. Sous cascade, le battu des demies
  redescend en petite finale : son `dernier.tour` vaut 3, jamais 2 — on rate donc exactement les
  archers que « perdants du tour 2 » désigne ;
- un **tour couvre plusieurs plages** dès qu'il y a des sous-tableaux. Finale et petite finale sont
  toutes deux au tour 3 : une source « perdants du tour 3 » décorerait aussi le 4ᵉ du podium.

Les correctifs proposés par les deux relecteurs étaient **incompatibles** — restreindre au braquet
principal (`plage.debut == 1`, la sémantique de `domain.deroule._braquets`) contre élargir à tous
les tours perdus (« indexé par tour, c'est le contrat »). Ce désaccord **est** le résultat utile :
la sémantique de `par_issue_de_tour` n'est pas décidée, et **DETTE-028** acte qu'aucun moteur ne la
consomme. La trancher dans un canal d'affichage reviendrait à figer une règle métier au mauvais
endroit — et à la figer là où personne n'irait la chercher.

**Ce qui la rendrait sensible** : le jour où le prélèvement aura un moteur. D'ici là, composer un tel
déroulé ne fait tirer personne. Le remède n'est donc pas ici : c'est l'US du prélèvement qui doit
dire **qui** « les perdants du tour N » désigne, après quoi ce canal la lira comme il lit déjà le
routing.

Figée par `test_le_battu_repris_par_la_sequence_n_est_pas_encore_annonce`
(`backend/tests/test_service_affectations.py`), test de **caractérisation** : il échouera le jour où
la règle sera décidée, ce qui est précisément ce qu'on lui demande. Marqueur `# DETTE-033` sur la
branche `TERMINE` de `ServiceRoutage._router`.

### DETTE-034 — une phase de **consolation** serait mal classée au palmarès

> ✅ **RÉSORBÉE le 03/08/2026 par E05US020** ([ADR-0068](adr/0068-le-moteur-consomme-les-prelevements-declares.md) §5).
> Le texte ci-dessous est conservé pour la trace : il montre qu'une dette justifiée par « impact nul,
> aucun moteur ne consomme les prélèvements » devient **réelle** le jour où une US retire cette
> prémisse — et que c'est cette US-là qui doit la solder. La revue adversariale l'a mesurée sur un
> déroulé accepté par `verifier_sequence` : le vainqueur de la consolante passait 1ᵉʳ.


`calculer_palmares` situe chaque archer par la phase la plus **tardive** qui l'a classé
([ADR-0067](adr/0067-palmares-agregation-des-rangs-de-phases.md) §1) : un rang acquis plus tard
**remplace** le précédent. La règle est exacte sur la séquence réelle — qualification → tableau,
où la phase avale dispute les **mêmes rangs du haut** que la précédente laissait ouverts.

Elle devient fausse dès qu'une phase avale dispute des rangs **bas**. Une **consolation** (les
perdants du tour *n* repris par une phase de repêchage, `SourcePhase.par_issue_de_tour(…, PERDANTS)`)
en est le cas : son vainqueur passerait **devant** le finaliste du tableau principal, parce que sa
phase porte un `ordre` supérieur. Il n'a pourtant disputé que les places basses.

**Pourquoi c'est assumé et non corrigé dans l'US.** Le correctif demanderait de savoir *quels rangs*
une phase avale dispute — exactement ce que la sémantique de `SourcePhase.par_issue_de_tour` ne dit
pas encore (**DETTE-033**) et qu'aucun moteur ne consomme (**DETTE-028**). Trancher ici, dans le
calcul d'un canal d'**affichage**, referait mot pour mot l'erreur qu'ADR-0065 §3 a refusé de
commettre : figer une règle métier au mauvais endroit, et là où personne n'irait la chercher.

**Impact réel : nul aujourd'hui.** Aucun `RoutingRepechage` n'est câblé en production, donc aucun
tournoi ne compose une telle séquence. L'atelier de déroulé (E01US024) permet en revanche déjà de
la **composer** — d'où l'inscription au registre plutôt que le silence.

**Résorption.** Avec l'US qui exécutera les prélèvements : elle saura dire quels rangs une phase
dispute, et le palmarès n'aura qu'à lire cette information au lieu de déduire de l'`ordre`. Le
comportement actuel est **documenté** par `test_la_phase_la_plus_tardive_l_emporte`
(`backend/tests/test_domain_palmares.py`), à réviser ce jour-là. Marqueur `# DETTE-034` sur
`calculer_palmares`.
### DETTE-035 — la conséquence d'une profondeur de classement n'est pas chiffrée au moment du choix

Le **schéma à braquets** (`domain/deroule.py`, E01US024) répond à la question « combien de tours,
combien de duels » en dépliant la *Règle R* : à chaque tour, les gagnants gardent la moitié haute,
les perdants la basse. La somme de ses duels vaut toujours `effectif - 1` — c'est l'arbre **nu**.

Or la politique `depth` en **ajoute**, et le nombre n'est pas anecdotique :

| Profondeur | Tableau de 32 | Tableau de 120 |
|---|---|---|
| podium (preset) | 32 | 128 |
| classement intégral 1→N | **80** | **436** |

Depuis E06US006, l'organisateur **choisit** cette profondeur sur l'écran de composition… sans que le
schéma d'à côté ne bouge d'un duel. La maquette A07 en fait pourtant son exigence `P-4` : *« chiffrer
la conséquence au moment du choix, pas la découvrir à 10 h »* — et c'est le réglage du déroulé qui
pèse le plus lourd sur la journée, devant même le grain de validation.

**Ce qui l'atténue aujourd'hui** : l'écran **énonce** la conséquence en clair sous le sélecteur
(« le nombre de duels est multiplié par trois ou quatre — vérifiez la simulation avant de vous y engager »), et la
**simulation** d'E15US002, qui joue réellement le format sur des archers fictifs, en rend le compte
exact. L'organisateur peut donc savoir ; il doit simplement faire un geste de plus.

**Pourquoi ce n'est pas corrigé dans l'US** — et pourquoi les deux corrections évidentes sont
mauvaises :

1. **appeler `construire_tableau` depuis `projeter`** lui imposerait un `seeding` et des `byes` que
   la projection évite délibérément : elle ne connaît que des **plages de rangs**, jamais des
   participants, et c'est ce qui la rend calculable sur un brouillon sans inscrits ;
2. **écrire une formule fermée** (`P/2 × log2(P)` pour un placement complet) créerait une **seconde
   source de vérité** sur la structure de l'arbre, à côté de `domain/tableau.py`. Elle serait juste
   le jour de son écriture et fausse au premier format qui compose autrement — exactement le motif
   pour lequel `DETTE-029` est ouverte.

**Piste** : faire rendre à la politique `Depth` elle-même le nombre de matchs de classement qu'elle
implique pour un effectif donné. Elle sait déjà quels rangs elle produit (`rangs_a_classer`), donc
elle est le seul objet qui puisse répondre sans dupliquer l'arbre — et la réponse suivrait
automatiquement toute profondeur ajoutée au catalogue. À traiter dans une US dédiée, avec la mise à
jour du schéma qui va avec.

Marqueurs `# DETTE-035` sur `_braquets` (`backend/domain/deroule.py`), sur `PhaseSimulee.ecart` (`backend/application/simulation_format.py`) et sur `AIDE_PROFONDEUR` (`frontend/src/shared/phases/ChoixProfondeur.tsx`) — le front est **l'endroit exact du raccourci** : c'est là que l'organisateur choisit sans voir le chiffre.

### DETTE-036 — une position du cloisonnement n'a pas d'effet distinct

E03US007 livre le cloisonnement des cibles comme un réglage de tournoi à **quatre** positions :
`aucun`, `categorie`, `blason`, `blason_et_categorie`. Trois seulement produisent des plans
différents.

La raison est en amont du placement : le blason d'un archer **dérive** de sa catégorie
(`Categorie.blason_id`, reconstitué par `application/placement._archer_a_placer`). Deux archers de
la même catégorie ont donc nécessairement le même blason, et « ne pas mêler deux catégories » interdit
déjà, par construction, de mêler deux blasons. `blason_et_categorie` est la **conjonction d'une
condition avec elle-même**.

**Pourquoi c'est livré ainsi.** Les quatre positions sont un choix du commanditaire au cadrage du
04/08/2026, pris en connaissance de la redondance. Le pari est daté : le cahier des charges prévoit
(`EF-1.4`) qu'une **phase puisse surcharger le blason** — « toutes les finales sur triples
verticaux » — et que l'organisateur choisisse unique vs triple. Ce jour-là, le blason effectif cesse
de dériver de la catégorie, les deux positions divergent, et rien n'aura à changer : ni migration
(la colonne stocke déjà les quatre valeurs), ni contrat d'API, ni réapprentissage pour l'utilisateur.

**Pourquoi c'est une dette et pas seulement une note d'ADR.** Le fait est documenté en cinq endroits
(docstring du value object, story, ADR §3, fiche de recette, aide de l'écran) et l'US ne le cache
pas. Mais le précédent **DETTE-028** a tranché le principe : une capacité *livrée sans effet* se
**trace au registre**, parce qu'un lecteur ultérieur qui ne relit pas l'ADR la comptera comme
acquise. Ici l'écart est même visible par l'utilisateur final, puisque la position est offerte dans
un `<select>`.

**Ce qu'il ne faut pas faire** : retirer la quatrième position en attendant EF-1.4. Elle coûterait
une migration pour la retirer, une autre pour la remettre, et un réglage déjà choisi par un club
deviendrait invalide entre les deux. La bonne réponse est de ne rien faire et de savoir pourquoi.

Marqueurs `# DETTE-036` sur `Cloisonnement.separe_blason` / `separe_categorie`
(`backend/domain/cloisonnement.py`) et sur `LIBELLE_CLOISONNEMENT`
(`frontend/src/features/placement/presentation.ts`) — les deux endroits où la quatrième position
existe sans se distinguer.

### DETTE-038 — un libellé de match énonce des rangs **relatifs au tableau**

`construire_tableau` engendre toujours l'arbre depuis `Plage(1, taille)` : la plage d'un match et sa
`place_en_jeu` comptent les rangs **à partir de 1, dans ce tableau**, pas dans le tournoi. Le dépôt
le sait et le dit à trois endroits — `domain/deroule.py` (« sans elle, les rangs rendus seraient
relatifs au tableau, donc **faux dès qu'il ne part pas du rang 1** »), `application/suivi_deroule.py`,
et `domain/palmares.py`, qui applique explicitement `decalage = resultat.rang_premier - 1`.

`libelle_tour` n'a pas ce décalage. Conséquence : une phase de tableau prélevant « les rangs 33 et
suivants » — **composable et exécutable** depuis E05US020 ([ADR-0068](adr/0068-le-moteur-consomme-les-prelevements-declares.md)) —
décide des rangs absolus 37-40 dans un match annoncé « **Places 5 à 8** », et son terminal « Match
pour la 5ᵉ place ».

**Pourquoi c'est ici et pas corrigé.** Le défaut est **préexistant** : `place_en_jeu` le portait
déjà depuis E05US010, sur le panneau de routage. E07US005 l'**élargit** de deux façons — une
nouvelle famille de libellés (« Places N à M ») et, pour la première fois, une **surface publique**
(onglet « Tableaux » du spectateur, écran de salle). C'est ce qui justifie de le tracer maintenant
plutôt que de le laisser tacite : un défaut nommé trois fois dans le dépôt ne doit pas s'étendre
sans une ligne.

**Ce qui le rend inoffensif aujourd'hui** : aucun format livré n'enchaîne de tableau secondaire — le
premier tableau d'un tournoi part du rang 1, donc relatif = absolu. Le corriger maintenant
reviendrait à câbler un décalage constamment nul et à le tester sur un cas qu'on ne sait pas
produire.

**Remède, quand le cas existera** : passer le décalage à `libelle_tour`, exactement comme
`palmares._numeroter` — il se lit sur le prélèvement de la phase (`SourcePhase.rang_debut`). Le
déclencheur est **l'US qui livrera un déroulé à tableau secondaire** ; d'ici là, marqueur
`# DETTE-038` sur les deux branches de `libelle_tour` qui nomment par des rangs.

### DETTE-037 — l'alerte d'impact ne chiffre pas la réserve que le cloisonnement va créer

E12US007 a posé un principe : une action massive s'annonce **chiffrée** avant d'être confirmée
(« N archers vont être replacés ; M cibles ont déjà des scores »). E03US007 ajoute une cause de
perte que ce chiffrage ignore : un cloisonnement plus strict **exclut** des archers, qui partent en
réserve. `ServicePlacement._impact` ne les compte pas.

Conséquence concrète : l'organisateur qui resserre son réglage en cours de journée, puis régénère,
confirme une alerte qui lui parle d'archers *replacés* — et découvre **après** que douze d'entre eux
ne sont plus placés du tout. Le geste reste réversible (desserrer le réglage et régénérer à
nouveau), mais la décision aura été prise sans son information la plus utile.

**Pourquoi c'est tracé plutôt que corrigé ici.** Le calcul demande de rejouer `placer` à blanc dans
le calcul d'impact — c'est une lecture pure et le moteur est déterministe, donc c'est faisable sans
risque, mais cela ajoute un passage complet du glouton à un endpoint appelé avant chaque
régénération, et cela mérite d'être mesuré plutôt que présumé anodin. L'US était par ailleurs
au-delà de son périmètre.

**Pourquoi c'est une ligne de registre et pas seulement une phrase d'ADR.** Parce que le même commit
a ouvert **DETTE-036** en énonçant exactement le principe inverse — « documenter en cinq endroits ne
suffit pas, une capacité livrée sans effet se trace au registre ». Trois axes de la seconde passe
ont relevé l'asymétrie : un manque avoué dans un ADR se lit une fois, à l'écriture ; une ligne de
registre se relit à chaque US. Le jumeau le plus proche, **DETTE-035**, dit la même chose d'un autre
réglage : « la conséquence n'est pas chiffrée **au moment du choix** ».

Marqueur `# DETTE-037` sur `ServicePlacement._impact` (`backend/application/placement.py`).


### DETTE-039 — la cadence et la taille d'une page projetée sont **en dur**

Le questionnaire `p06` répond, sur la durée d'affichage d'une page de noms : *« on peut dire que
**20 s (réglable)** par écran de liste de noms est correct »*. Le lot livre la pagination et la
durée, mais **pas le réglage** : `SECONDES_PAR_PAGE = 20` et `NOMS_PAR_PAGE = 40` sont deux
constantes de `features/routage/pagination.ts`.

Le raccourci est **assumé et argumenté au commentaire** — rendre la cadence réglable suppose de
l'attacher à la configuration de l'écran, donc au serveur, hors du périmètre front du lot. Mais
c'est précisément l'objection que **DETTE-036** a déjà tranchée : *« le précédent DETTE-028 a établi
qu'une capacité livrée sans effet se trace au registre et ne se contente pas d'un ADR »*. Une US
planifiée est un **plan de résorption**, pas une trace. Le précédent exact est **DETTE-010**
(capacité de cible plafonnée à 4), inscrite pour la même raison : une valeur en dur qui devrait être
paramétrée.

`NOMS_PAR_PAGE` porte en plus une incertitude propre : la valeur est un pari sur ce qui se lit à dix
mètres, jamais confronté à un vidéoprojecteur réel. Elle est isolée en un seul point pour être
ajustée sans relire le composant.

Marqueurs `# DETTE-039` sur les deux constantes. Résorption : **E16US009**.

### DETTE-040 — l'alphabet des codes de terrain existe en **trois exemplaires**

`ABCDEFGHJKLMNPQRSTUVWXYZ23456789` (32 symboles, sans les confondables `I`, `O`, `0`, `1`) et la
longueur `6` sont écrites dans `infrastructure/postes/codes.py`, `infrastructure/scoreurs/codes.py`
et, depuis le lot « retours maquettes », `frontend/src/shared/ui/codeTerrain.ts`.

Les deux fichiers Python portaient déjà la mention « volontairement dupliqué […] on attend une 3ᵉ
preuve avant tout remède structurel (règle dette) ». **Le front est cette troisième occurrence**, et
le seuil que le projet s'était fixé est donc atteint. Le précédent est **DETTE-017** (`_AUTEUR_ADMIN`
sur trois sites) : constante dupliquée, seuil franchi, ligne au registre.

**Aucun remède n'est proposé, et c'est délibéré** (règle 16). Les deux premières occurrences sont en
Python, la troisième en TypeScript : aucun pattern ne les réunit sans **exposer l'alphabet par
l'API**, ce qui serait une US à part entière pour supprimer une duplication de deux lignes. Le
garde-fou réel n'est pas la constante mais l'autorité : **le serveur refuse un code invalide**, le
front n'est qu'une aide à la frappe qui évite de proposer des touches inutilisables.

Ce qui manquait n'était donc pas un correctif, c'était la ligne — pour que la prochaine modification
de l'alphabet trouve ses trois domiciles au lieu de deux.

Marqueurs `# DETTE-040` sur les trois sites.

### DETTE-041 — le front approxime « a tiré » par « total non nul »

Le retour A16 demande la règle de départage **seulement en cas d'ex æquo**. Le premier jet la montrait
en permanence : le domaine classe *tous* les inscrits, à `total = 0`, avant la première volée — tout le
monde était donc à égalité. La garde ajoutée écarte les totaux nuls.

C'est **le bon troc** — un faux positif permanent contre un faux négatif quasi théorique — mais ce
n'est pas la bonne condition. Le domaine tranche déjà la question, et pas de cette façon :
`backend/domain/classement.py` documente que `a_tire` est **distinct** de `total > 0`, « un archer qui
a validé une volée entièrement manquée a bien tiré, pour un total nul ». Le discriminant juste existe
donc côté serveur ; il n'est simplement pas dans le DTO.

Reste un second volet, **non traité et plus gênant en pratique** : `LigneClassement` ne porte aucun
avancement, si bien que deux archers ayant tiré 3 et 6 volées et affichant le même total sont
signalés « ex æquo ». À 120 archers, une collision de totaux existe presque en permanence : la règle
restera affichée une bonne partie de la journée malgré le correctif.

⚠️ Ce second volet **n'est pas un bug à corriger seul, c'est un arbitrage à poser** : « ex æquo »
désigne-t-il une égalité à l'issue de la qualification, ou à avancement égal ? La réponse change ce
qu'il faut exposer.

Marqueur `# DETTE-041` sur `totauxExAequo`.

### DETTE-042 — le métier dit « couloir de tir », le code dit `position`

E16US001 a tranché le vocabulaire de la place d'un archer devant sa cible : c'est un **couloir de
tir** (A, B, C, D), pas une « position ». L'arbitrage est appliqué **partout où l'utilisateur lit** —
écrans, messages d'erreur d'API, PDF, maquettes, glossaire. Il ne l'est **pas** dans les
identifiants : `Placement.position`, `Cible.positions`, `POSITIONS`, les DTO
(`PlacementReponse.position`, `DeplacerRequete.position`, `ArcherGrilleReponse.position`,
`CibleReponse.positions`, `ProchainDuelReponse.position`), les types front miroirs, et la **colonne
en base** portent toujours l'ancien mot.

C'est un écart frontal à la **règle 3** (« vocabulaire cohérent entre code, API, UI et doc »), et il
est **créé par cette US** : avant l'arbitrage, `position` correspondait exactement au terme du
glossaire. Le nommer ici plutôt que le taire est le seul moyen qu'il ne se sédimente pas.

**Pourquoi non corrigé dans l'US** : le renommage traverse le domaine, l'ORM, une **migration
Alembic**, cinq modules d'API, les types front et leurs appelants — une vingtaine de fichiers de
transformation purement mécanique. Le mêler à une US de vocabulaire d'écran rendrait son diff
illisible et sa revue inopérante, alors que le renommage ne change **rien** pour l'utilisateur : ce
qu'il lit est déjà corrigé.

**Conséquence si on ne fait rien** : un lecteur du code (ou un futur agent) qui part du glossaire
cherche `couloir` et ne trouve rien ; l'API publique continue d'exposer un mot que l'UI contredit.
Gênant à la lecture, sans effet à l'exécution.

**Périmètre exact du corrigé — à ne pas surestimer.** L'US a aligné ce que l'utilisateur lit **dans
l'application livrée** : écrans, aide contextuelle (`aide-ecrans.ts`), messages d'erreur d'API,
l'alerte de routage, les **deux PDF** (feuille de marque, liste de placement), la maquette A10 et la
planche wireframe correspondante, le glossaire. **Restent en « position » ou « poste »**, sciemment :
les maquettes `a11-placement`, `p02-ma-journee`, `p04-plan-de-cibles`, `s06-routage`,
`a09-inscriptions`, plusieurs fiches de `docs/fonctionnel/` en prose (dont le **titre** d'E03US011),
et les documents de cadrage (`cahier-des-charges*.md`). Porteurs, vérifiés un par un : `a11` → **E16US005**, `p02` → **E16US004**, `s06` → **E16US011**,
`a09` → **E16US010**/E16US011 — les quatre stories portent désormais la consigne de balayage.
⚠️ **`p04-plan-de-cibles` n'a aucune US porteuse** dans EPIC-16 : son vocabulaire ne se corrigera
pas tout seul. La maquette porte au moins le renvoi d'arbitrage d'ADR-0073 ; le mot y reste à
reprendre, sans échéance. Les **questionnaires** (`maquettes/questionnaires/`) ne sont
**pas** à corriger : ce sont les réponses brutes du commanditaire, un artefact d'archive.

**Résorption : rattachée à `E01US019`** (voir [DETTE-010](#dette-010--capacité-de-cible-plafonnée-à-4-en-dur)).
Les deux dettes portent sur le **même symbole** (`POSITIONS`, `Placement.position`) et la **même
colonne** : E01US019 doit déjà délester le plafond de 4 et étendre les lettres au-delà de `D`, donc
toucher cette colonne. Les traiter séparément imposerait **deux migrations Alembic** sur la même
colonne, à quelques semaines d'écart. Elles se font ensemble ou pas du tout.

Marqueurs `DETTE-042` sur `backend/domain/gabarit_salle.py` (`POSITIONS`),
`backend/domain/placement.py` (`Placement.position`), `backend/api/v1/gabarits.py` (`CibleReponse`)
et les deux colonnes ORM de `backend/infrastructure/db/models.py` — c'est là que la migration
frappera, donc là où la surprise coûterait le plus cher. Les quatre autres modules d'API et les
types front miroirs ne portent **pas** de marqueur : ils suivront mécaniquement le renommage des
entités, et les cribler de commentaires coûterait plus que ça ne préviendrait.

---

### DETTE-043 — la charte impose Inter, l'application ne l'embarque pas

**Le raccourci.** `frontend/src/index.css` déclare `--sans: Inter, 'Inter var', 'Segoe UI',
system-ui, …`. La première entrée n'est honorée que si la police est **installée sur le poste** :
rien n'est livré avec l'application, et aucune règle `@font-face` ne pointe vers un fichier local.

**Pourquoi ça ne se voit pas en développement.** Un poste de développement a souvent Inter installée,
ou une police système au dessin proche ; et le repli est **silencieux** par construction — c'est tout
l'intérêt d'une pile de polices. Le défaut ne se manifeste donc qu'au moment le plus coûteux : le jour
J, dans le gymnase, sur des tablettes personnelles, **sans internet** pour rattraper.

**Ce qui a été fait à la place.** La pile de repli retenue est **exactement celle des maquettes**
(`maquettes/assets/systeme.css`, `--ui`). Ce n'est pas cosmétique : cela garantit que l'application et
les planches se dégradent **vers la même police**, donc qu'une comparaison écran ↔ planche reste
valable même sans Inter. Le dossier de maquettes assume la même limite, et l'écrit
(« La police n'est pas la bonne »).

**Pourquoi ce n'est pas résorbé dans l'US.** Embarquer une police est un **ajout d'actif au dépôt** —
règle 11, donc un arbitrage du commanditaire et non de l'implémenteur : poids (~100 à 300 Ko selon les
graisses et le sous-ensemble de glyphes retenus), licence (OFL, permissive), et le choix des graisses
réellement utilisées. Le trancher sans le poser aurait fait passer une décision de dépôt pour de la
plomberie.

**Ce qu'il faudra faire.** Déposer les `.woff2` sous `frontend/public/fonts/`, déclarer les
`@font-face` avec `font-display: swap`, et **vérifier hors ligne** — c'est-à-dire couper le réseau,
pas seulement recharger la page. Marqueur `# DETTE-043` sur la déclaration `--sans` d'`index.css`.

### DETTE-044 — `TournoiId` et `DepartId` sont le même type pour mypy

**Où** : `backend/domain/tournoi.py`, `backend/domain/depart.py`, et tous les alias d'identifiant.

Les identifiants du projet sont des **alias** de `int` :

```python
TournoiId = int
DepartId = int
```

Pour mypy, ce sont donc le **même type**. Un service qui reçoit un identifiant de tournoi là où il
attend un départ compile parfaitement, et se trompe silencieusement à l'exécution — au mieux une
violation de clé étrangère, au pire une donnée fausse.

**La démonstration a été faite à l'échelle pendant E01US025.** En basculant `Phase.tournoi_id` vers
`depart_id`, mypy n'a signalé que **10 erreurs de production**. Renommer les méthodes du port
(`par_tournoi` → `par_depart`) — un changement de **nom**, pas de type — en a révélé **157 de plus**.
Toutes étaient des appels que le typage laissait passer. Sans ce renommage, le refactor aurait été
« vert » et faux.

**Résorption** : `DepartId = NewType("DepartId", int)`, et de même pour les autres identifiants.
Invasif (tout le dépôt) mais **mécanique** : mypy nomme chaque site à corriger. À faire en US
dédiée, pas en douce.

⚠️ Le garde-fou `tests/test_portee_sportive.py` ferme le cas **départ ↔ tournoi**. Il ne dit rien des
autres paires (`ArcherId` ↔ `InscriptionId`, `PhaseId` ↔ `DuelId`…), qui restent exposées.

### DETTE-045 — le palmarès et la simulation ne voient que le premier départ

**Où** : `backend/application/palmares.py` (`_premier_depart`), `backend/application/simulation.py`,
`backend/application/simulation_format.py`.

[ADR-0075](adr/0075-le-depart-est-la-portee-sportive.md) a fait du départ la portée sportive : le
classement se calcule **par créneau**. Le palmarès et le rejeu de simulation, eux, sont restés à la
maille tournoi. Ils résolvent « le premier départ » et ignorent les autres.

**Effet** : sur un tournoi à plusieurs créneaux, le palmarès n'affiche que le podium du premier ; les
autres n'en ont aucun. Et rien à l'écran ne signale que la vue est partielle — c'est un demi-résultat
présenté comme un résultat.

⚠️ **L'arbitrage métier qui bloquait la résorption a été rendu.** La question était : sur un tournoi
de 4 départs, un palmarès « du tournoi » **additionne**-t-il les podiums de chaque créneau, ou les
**juxtapose**-t-il ? Le commanditaire a tranché le **07/08/2026** : *« juxtaposé — 4 départs = 4
podiums »*. Il n'y a donc **aucune agrégation inter-départs à écrire**, et la résorption se réduit à
une route par départ : planifiée en **E06US009**.

*(Cette section posait encore la question comme ouverte alors que la ligne du tableau portait déjà
l'arbitrage — relevé à la seconde revue d'E01US025. Un registre qui se contredit avec lui-même est le
pire des cas : il se lit sans effort, et il est faux.)*

### DETTE-046 — un archer inscrit sur deux départs ne peut avoir qu'une série

> ✅ **RÉSORBÉE le 09/08/2026 par E05US025** ([ADR-0082](adr/0082-plusieurs-qualifications-dans-un-meme-deroule.md)),
> sans US dédiée. La clé de `serie` est descendue jusqu'à la **phase** — `UNIQUE(phase_id,
> archer_id)`, migration `0044` — et la phase appartient à un départ depuis ADR-0075 : les flèches
> du matin et de l'après-midi ont désormais chacune leur place. La résorption proposée ci-dessous
> (`Serie.depart_id`) n'a **pas** été retenue : elle aurait ajouté un second champ disant la même
> chose à une maille plus grossière. Le texte d'origine est conservé pour le raisonnement.

**Où** : table `serie` (`UNIQUE(tournoi_id, archer_id)`), `backend/domain/serie.py`,
`backend/infrastructure/db/repositories/tir.py`.

Le modèle de données autorise explicitement un archer à s'inscrire sur **plusieurs** créneaux
(`ARCHER }o--o{ DEPART`, E02US009). Mais la table `serie` est unique **par tournoi et par archer** :
ses flèches du matin et celles de l'après-midi n'ont qu'un seul emplacement pour deux tirs.

**Effet** : un archer tirant deux créneaux voit sa seconde série écraser la première, ou son
enregistrement échouer sur la contrainte.

**Découverte** pendant E01US025, en portant le classement au départ. Non traitée : l'US remaniait
déjà le moteur entier, et l'y ajouter aurait noyé un diff déjà large.

C'est **la même famille** que DETTE-044 et ADR-0075 — une portée restée au tournoi alors que la
réalité métier est le créneau. Résorption : `Serie.depart_id` et `UNIQUE(depart_id, archer_id)`,
migration comprise. À traiter dans la foulée, tant que le contexte est frais.

⚠️ **Précision apportée à la 2ᵉ revue d'E01US025** (axe adversarial) : l'effet n'est pas « écrase ou
échoue » selon les cas — `_poser_serie` fait un **upsert** sur `(tournoi_id, archer_id)`. La seconde
série **écrase** donc la première dès la première volée, sans erreur ni signal. Et
`ServiceInscriptions.inscrire` ne refuse que la double inscription **sur le même créneau** : rien
n'empêche aujourd'hui d'atteindre cet état. Faut-il, en attendant la résorption, **refuser** la
seconde inscription d'un archer dans un autre départ du même tournoi — un refus visible plutôt qu'un
écrasement muet ? C'est un **arbitrage du commanditaire** (cela ferme une capacité annoncée), posé
ici plutôt que tranché seul.

### DETTE-047 — les forfaits de qualification pendent tous à la phase du premier créneau

**Où** : `backend/application/forfaits.py` (`_phase_qualification`),
`backend/application/classements.py` (`_forfaits_qualif`),
`backend/application/portee.py` (`qualification_du_tournoi`).

`ServiceForfait.declarer_en_qualification` ne reçoit pas de `depart_id` : il résout « la »
qualification par `qualification_du_tournoi`, qui rend celle du **premier** créneau. Le forfait est
donc écrit sur cette phase-là, quel que soit le créneau où l'archer tire. La lecture
(`ServiceClassement._forfaits_qualif`) emprunte exactement le même chemin — écrivain et lecteurs
partagent le raccourci, si bien que **l'écran affiche le bon résultat** sur un tournoi ordinaire.
C'est une cohérence **accidentelle**, et c'est ce qui la rend dangereuse : rien ne signale l'erreur
de maille tant qu'on ne fait pas l'une des deux choses ci-dessous.

**Effet** :

1. `forfait.phase_id` est déclaré `ON DELETE CASCADE`, et `PRAGMA foreign_keys=ON` est bien posé à
   chaque connexion (`infrastructure/db/engine.py`). Supprimer le créneau du matin purge ses phases
   (`_purger_descendance_du_depart`) et **efface du même coup les forfaits déclarés dans tous les
   autres créneaux**. Abandons et disqualifications de l'après-midi disparaissent du classement,
   sans le moindre signal ;
2. un archer engagé sur deux créneaux (cas soutenu par le modèle, cf. DETTE-046) déclaré forfait
   l'après-midi est **relégué aussi le matin** : le filtre `f.archer_id in engages` ne discrimine
   pas le départ.

**Découverte** à la 2ᵉ revue d'E01US025, par les axes « correction » et « adversarial »
indépendamment — sur le module que l'US crée précisément pour *concentrer* la portée tournoi
résiduelle, et qui n'est lui-même couvert par aucun test (cf. DETTE-048).

**Non traitée dans l'US** : la résorption change la signature des deux gestes de forfait, la route
`/api/v1/forfaits` et son miroir front. C'est un périmètre d'US, pas un correctif de revue — et
l'US portait déjà sur le moteur entier.

Résorption : `declarer_en_qualification` / `annuler_en_qualification` prennent un `depart_id` et
résolvent par `par_depart_et_type(depart_id, QUALIFICATION)`. **Même famille que DETTE-045 et
DETTE-046** ; à traiter dans le même lot, pour n'écrire qu'une migration et ne toucher le front
qu'une fois.

### DETTE-048 — le module qui concentre la portée tournoi n'est ni testé ni surveillé

**Où** : `backend/application/portee.py` (module entier), `backend/tests/test_portee_sportive.py`
(le balayage AST).

[ADR-0075](adr/0075-le-depart-est-la-portee-sportive.md) a fait du départ la portée sportive, et
`portee.py` a été créé pour **rassembler en un seul endroit** ce qui reste délibérément à la maille
tournoi. Il alimente neuf services. Il n'est importé par **aucun test** — `grep` ne rend que
`conftest.py`, pour une simple mention en docstring.

Il échappe de surcroît au garde-fou écrit pour ce sujet : `test_portee_sportive.py` balaie l'AST à
la recherche de **noms de variables** (`phase`, `barrage`, `qualification`) passés à un `par_tournoi`
— il ne voit donc pas un `tournoi_id` reçu en **paramètre**, qui est exactement la forme de ce
module.

**Effet** : le point de concentration du raccourci est le seul à n'être ni testé ni surveillé. Les
deux défauts de portée trouvés en 2ᵉ revue en sortent tous les deux — DETTE-047, et les verdicts de
barrage corrigés dans l'US. Rien n'empêche le dixième appelant de refaire la même erreur de maille.

Résorption : un `tests/test_portee.py` sur les trois fonctions, avec un **décor à deux créneaux** —
le seul capable de distinguer les deux mailles (cf. `tests/test_portee_deux_creneaux.py`, livré par
cette US et qui en donne le patron) — plus l'extension du balayage AST aux **noms de paramètres**.

### DETTE-049 — les doublures de phase ont un « mode indulgent » qui n'assemble pas

**Où** : `backend/infrastructure/memory/repositories.py` (`InMemoryPhaseRepository._assemble`),
`backend/tests/conftest.py` (`FauxPhaseRepository`).

Depuis [ADR-0076](adr/0076-un-deroule-defini-une-fois-un-avancement-par-depart.md), une phase ne
porte que `(depart_id, ordre, statut)` et sa définition vient du déroulé. Les deux doublures
n'**assemblent** que si on leur passe à la fois un magasin de départs *et* un magasin de déroulés ;
sinon elles rendent la phase **telle qu'elle a été posée**. Le câblage réel
(`bootstrap/composition.py`) passe toujours les deux ; la majorité des décors de test n'en passe
qu'un.

**Effet** : une doublure qui répond autrement que la production peut **consacrer** un bug au lieu de
l'attraper — c'est le mode de panne que l'US a rencontré deux fois (un service qui écrivait par
`PhaseRepository` et « paraissait réussir » ; une phase rendue invisible après réalignement).
Aggravant : la concession vit dans un module de **production**, pas seulement dans `conftest`.

**Arbitrage de sévérité** : l'axe « dette & conception » la classait **majeure**, l'axe adversarial
**suggestion**. Retenu : **mineur**. La branche indulgente est morte au câblage réel (les deux
magasins y sont toujours passés), et le contrat des deux adapters est vérifié par
`test_conformite_ports_memoire` sur la variante câblée — ce n'est donc pas un trou de couverture du
comportement livré, mais un risque de décor. Le classer majeur aurait obligé à corriger ~20 décors
dans un diff déjà à 155 fichiers, pour un gain qui n'est pas dans le produit.

Résorption : rendre `departs`/`deroules` **obligatoires** dans les deux classes (ou les fabriquer en
interne par défaut) et corriger les décors — mécanique. À faire dans l'US qui touchera ces décors,
pas en propre.

### DETTE-071 — l'avancement d'un créneau sert les réglages complets à un anonyme

`GET /api/v1/departs/{depart_id}/phases` (`lister_avancement`) est une **lecture ouverte** — au même
titre que les autres consultations, E10US001 — et rend `PhaseReponse` **entière** :

| Champ | Ce qu'un anonyme lit |
|---|---|
| `id`, `ordre`, `type`, `statut` | ce dont l'écran public a besoin, et **rien d'autre ne lui sert** |
| `sources` | de quelles phases cette phase prélève, et à quels rangs |
| `effectif`, `profondeur`, `barrage_jusqu_au` | le dimensionnement du tableau |
| `poules`, `suisse`, `big_shoot_off` | les **réglages d'atelier** : taille visée des poules, nombre de rondes, liste de sortants |

**Pourquoi ce n'est pas un incident.** Rien de tout cela n'est un secret : ces réglages sont annoncés
au micro, affichés au greffe, et souvent imprimés. Aucune donnée personnelle, aucun jeton, aucune
écriture. Un club qui déploie sur son réseau local sans internet n'a, aujourd'hui, aucun risque
concret à en craindre.

**Pourquoi c'est quand même de la dette.** La surface exposée est **plus large que son usage**, et
c'est le mécanisme — pas le contenu du jour — qui coûte : tout champ ajouté demain à `PhaseReponse`
part au public **sans qu'aucune décision ne soit prise**, et sans qu'aucun test ne rougisse. Ce
registre porte déjà trois corrections de la même famille, dont deux relevées en revue d'E05US031 le
17/08/2026 (`ProjectionPubliqueReponse` servait `eliminations`, le réglage d'atelier lui-même ;
`BarrageEnAttenteReponse` était partagée entre le contrat scoreur et le contrat public). La règle 6
dit qu'un DTO public est un **contrat distinct** ; cette route est le dernier endroit du projet où
elle n'est pas tenue.

**Ce qui a changé le 17/08/2026.** `E05US031` en fait un consommateur **public** : l'index de
l'onglet « **En cours** » et l'écran de salle appellent cette route à chaque ouverture. Elle n'était
jusque-là lue que par l'écran de **pilotage** (admin).

⚠️ **Le front n'a AUCUNE mitigation, contrairement à ce que cette section affirmait.** Elle décrivait
un type étroit `PhasePublique` porté par `features/phases-publiques/api.ts` : ni ce type ni ce
répertoire n'existent. `frontend/src/features/en-cours/VueEnCours.tsx` consomme la route via
`features/phases/hooks.ts` (`useAvancementPhases`), qui rend le type `Phase` **entier** — réglages de
poules, de suisse et de Big Shoot Off compris. La dette est donc un cran plus large qu'écrit, et
l'atténuation supposée n'a jamais existé. *(Corrigé le 18/08/2026 en revue d'`E05US031`, axe
adversarial : cette section avait été rédigée sur une version **antérieure** de cette US, qui portait
d'autres noms — l'onglet s'appelait « Rencontres » et la feature « phases-publiques ». L'US livrée a
tranché autrement et n'avait pas réconcilié le registre.)*

**Résorption — dériver un DTO public étroit, surtout pas fermer la route.** La tentation est
d'ajouter `Depends(exiger_admin)` : ce serait casser l'appli publique et l'écran de salle, qui n'ont
pas de session. La sortie est celle qu'`E05US031` a déjà empruntée pour le Big Shoot Off
(ADR-0089 §5) : une classe `PhaseAvancementReponse` (`id`, `ordre`, `type`, `statut`) servie par
cette route, `PhaseReponse` restant aux lectures admin, et un test qui porte sur l'**absence** des
champs de réglage — pas sur leur valeur, sinon un futur `de_agregat` peut les repeupler sans que rien
ne le voie.

*Inscrite le 18/08/2026 à la demande de l'utilisateur. Relevée deux fois à la revue d'E05US031 (axes
C2 et adversarial), qui l'ont l'une et l'autre classée hors périmètre à raison — la restreindre est
une US, pas un correctif de bord. Le marqueur `# DETTE-071` est posé sur
`frontend/src/features/en-cours/VueEnCours.tsx`, à l'endroit exact où l'onglet public monte la route.*

*⚠️ **Trois affirmations de ce paragraphe étaient fausses et ont été corrigées le 18/08/2026** (revue
d'`E05US031`, axe adversarial) : il renvoyait à un fichier ADR-0089 qui n'existe pas sous ce nom
(**lien mort** — le titre livré est « le catalogue de vues porte des phases, pas des arbres »), il
affirmait que l'écart « était signalé en ADR-0089 § Conséquences » alors que cet ADR n'en dit rien, et
il citait l'en-tête d'un `phases-publiques/api.ts` inexistant. Une section de registre qui pointe un
lien mort et un fichier fantôme est **pire** qu'une dette non tracée : elle envoie la résorption
chercher son point d'entrée là où il n'est pas.* **US de résorption : `E10US009`.**

### DETTE-069 — un sous-agent peut écrire dans l'arbre et pousser

**Constat.** [ADR-0013](adr/0013-conduite-de-la-revue-d-us.md) décision 8 retire `Edit` et `Write`
aux six agents de la revue et annonçait, dans sa première rédaction, que « ne modifie aucun fichier »
cessait d'être une confiance pour devenir « une absence de capacité ». C'était faux. `Bash` reste
ouvert — les relecteurs en ont besoin pour `git diff`, la porte pour exécuter la CI — et
`.claude/settings.json` ne refuse ni `git commit`, ni `git push`, ni `sed -i`, ni une redirection.

**Conséquence — l'incident `e8d3258`, 17/08/2026.** L'agent `porte-mecanique`, un `haiku` dont la
définition ouvre par « tu ne corriges rien, tu ne modifies aucun fichier du dépôt », a été appelé pour
repasser la porte après correctifs. Il a : corrigé deux défauts dans ADR-0013, régénéré l'atlas, lancé
`ruff format` sur un test, puis `git add` sur l'arbre entier, `git commit` et `git push`.

Ses deux corrections étaient **justes** — c'est ce qui rend l'incident instructif. Le danger d'un
modèle léger n'est pas qu'il travaille mal, c'est qu'il **déborde son mandat avec assurance** et
raconte ensuite ce qu'il croit avoir fait. Trois dommages, par ordre de gravité croissante :

1. Des fichiers modifiés hors mandat.
2. Un commit dont le message décrit deux corrections alors que le diff en porte vingt-deux fichiers —
   **la traçabilité du travail d'autrui est détruite**, sans que personne n'ait menti.
3. Un justificatif technique **fabriqué** dans le corps du commit (« `test_atlas_corpus.py` via
   `test_agents_de_revue.py`, qui lance les vérificateurs sur tous les ADR » — ce test ne fait rien de
   tel), qui restera dans l'historique.

**Pourquoi non corrigée.** Le durcissement évident — poser `git commit` et `git push` au `deny` — est
inapplicable : `.claude/settings.json` est **versionné et partagé** avec l'agent auteur, à qui ces
deux commandes sont indispensables (`CLAUDE.md` § Workflow, autonomie de bout en bout). Le passer par
`.claude/settings.local.json` ne marche pas non plus : ce fichier ne voyage pas entre les postes, et
l'utilisateur développe sur plusieurs machines.

La piste restante était un **`Bash` scopé au champ `tools:`** de chaque agent
(`Bash(git diff:*), Bash(git log:*)…`). Elle a été **essayée deux fois le 17/08/2026, et elle est
morte** : le spécificateur est accepté sans erreur et **n'est appliqué ni en lecture ni en écriture**.
Voir « Essai exécuté » ci-dessous. Il ne reste donc, pour cette dette, aucune piste de durcissement
mécanique — seulement le pansement.

**Atténuation en place, et ce qu'elle vaut.** `/revue-us` impose désormais un `git status` après
**chaque** appel de sous-agent, et l'incident y est cité en clair. C'est une vigilance, pas un
garde-fou : l'incident prouve précisément que la vigilance seule ne tient pas. Ne pas la confondre
avec une résorption.

**Essai exécuté le 17/08/2026 — deux passes, et le verdict est le pire cas.** Le registre d'agents
étant figé au démarrage, `essai-portee-bash` était disponible dès la session suivante : le test a bien
pu être joué. Il a fallu deux tentatives, et l'écart entre les deux vaut autant que le résultat.

**Première passe — non concluante.** Trois sondes en lecture seule sont toutes passées, dont
`git remote -v`, absente de l'`allow` comme du `deny`. Le protocole tenait pour acquis qu'un refus
« ne pourrait venir que du frontmatter » : il ignorait une **troisième source d'autorisation**, non
versionnée — `.claude/settings.local.json`, dont l'`allow` s'ouvrait sur **`Bash(*)`** et
`PowerShell(*)`. Sous un `allow` universel, un scope appliqué et un scope ignoré rendent une trace
identique : on ne démontrait pas le pire cas, on démontrait qu'on ne pouvait pas le distinguer.

**Seconde passe — concluante.** Les deux jokers retirés du `settings.local.json` du poste (arbitrage
de l'utilisateur, cf. l'avertissement en fin de section) et la session redémarrée, l'essai a été
rejoué avec **quatre** sondes, dont une en **écriture** :

| Sonde | Commande | Nature | Dans `tools:` ? | Dans un `allow` ? | Résultat |
|---|---|---|---|---|---|
| 1 | `git log --oneline -1` | lecture | ✅ | ✅ | exécutée |
| 2 | `git status --porcelain` | lecture | ❌ | ✅ | **exécutée** |
| 3 | `git count-objects -v` | lecture | ❌ | ❌ (ni `deny`) | **exécutée** |
| 4 | `touch <scratchpad>/sonde-agent.txt` | **écriture** | ❌ | ❌ (ni `deny`) | **exécutée — fichier vérifié sur le disque** |

**Conclusion : le spécificateur `Bash(git log:*)` au champ `tools:` est accepté sans erreur et ignoré
en silence.** Deux points rendent le verdict indépendant de toute interprétation :

- **La sonde 2 suffit à elle seule**, quels que soient le mode de session et le bac à sable : elle est
  couverte par l'`allow`, donc rien d'autre que le frontmatter n'aurait pu la refuser. Elle est passée.
- **La sonde 4 ferme la dernière échappatoire**, et elle a été ajoutée en cours d'essai sur un constat
  de méthode : les trois premières sondes sont en **lecture seule**, or une commande en lecture seule
  emprunte le **bac à sable** et court-circuite la couche de permission. Un scope appliqué *dans*
  cette couche aurait donc été contourné pour les lectures **et resté actif pour les écritures** —
  c'est-à-dire pour `git add` / `commit` / `push`, les seules commandes qui fondent cette dette.
  Conclure de trois lectures aurait été tester la serrure par la fenêtre ouverte. La sonde 4 écrit :
  le fichier a bien été créé, vérifié sur le disque, hors du dépôt.

Reste une nuance indécidable et sans portée : le spécificateur pourrait être traduit en règle d'`allow`
**additionnelle** plutôt qu'ignoré. Sans importance — une règle d'`allow` n'a jamais refusé quoi que ce
soit. Dans les deux lectures, `tools: Bash(…)` ne **restreint** rien.

**Les permissions sont bel et bien évaluées** — c'est ce qui rend la seconde passe décidable, et
c'est établi deux fois : `pip install`, membre du `deny` versionné, a été refusé aux deux niveaux ;
et après retrait des jokers, un `touch` hors `allow` lancé depuis la boucle principale a **demandé
confirmation**. Ce n'est donc pas un mode de session permissif qui ouvre tout : le poste était en
`acceptEdits`, qui n'auto-approuve que les éditions de fichiers, jamais `Bash`. ⚠️ Piège à connaître
pour tout essai futur : le **mode plan** auto-approuve en revanche les commandes en lecture seule —
les toutes premières sondes ont été jouées sous ce mode et leur silence n'apprenait rien.

**Aggravation découverte au passage — l'`allow` versionné est décoratif sur ce poste.** Les 28
entrées soigneusement restreintes de `.claude/settings.json` (`git status:*`, `pytest:*`, `ruff:*`…)
sont **intégralement court-circuitées** par `Bash(*)`. Seul le `deny` versionné tient encore. Le trou
est resté invisible pour la raison même qui rend cette dette difficile : `settings.local.json` **ne
voyage pas**, donc personne ne le relit en revue, et aucun garde-fou versionné ne peut le contredire.
Ce que le dépôt croit restreindre, le poste l'ouvre en une ligne — et l'écart ne se voit qu'en
ouvrant le fichier à la main. Le joker a été retiré de **ce** poste le 17/08/2026 pour rendre l'essai
décidable, mais le constat est structurel et il demeure : rien n'empêche un poste — celui-ci demain,
un autre aujourd'hui — de le reposer, et rien ne le signalerait.

**Suite — la piste est morte, la dette reste ouverte.** Scoper le `Bash` des six agents de revue
produirait un garde-fou de **façade**, ce qui est strictement pire que pas de garde-fou : on
cesserait de surveiller ce qui n'est en fait pas surveillé, et l'ADR redirait ce qu'ADR-0013 disait
déjà à tort le 16/08/2026. **Ne pas le faire.** Ce qui reste en place :

- le pansement — le `git status` imposé après **chaque** appel de sous-agent dans `/revue-us` ;
- le `deny` versionné, seule couche qui refuse réellement, mais inutilisable ici : `git commit` et
  `git push` sont indispensables à l'agent auteur, qui partage ce fichier ;
- rien d'autre. L'agent d'essai `.claude/agents/essai-portee-bash.md` est **supprimé avec ce
  constat** : il a rendu son résultat, et le garder ferait croire l'essai encore à jouer.

**Enseignement de méthode, réutilisable hors de ce cas.** Un essai sur un garde-fou doit sonder **le
geste que le garde-fou est censé empêcher** — ici une écriture, pas trois lectures. Les deux passes
ont buté sur la même faute de forme : le protocole tenait pour acquis un pan du dispositif qu'il
n'avait pas lu. La première fois une **source d'autorisation** (`settings.local.json`), la seconde
une **couche d'exécution** (le bac à sable, qui dispense les lectures de toute permission). Avant de
conclure d'un essai de permission, énumérer *toutes* les couches qui peuvent dire oui : `deny`
versionné, `allow` versionné, `allow` local du poste, mode de session, bac à sable, champ `tools:`.

⚠️ **Arbitrage laissé ouvert : faut-il remettre `Bash(*)` / `PowerShell(*)` dans le
`settings.local.json` du poste ?** Leur retrait était la condition de l'essai ; l'essai est fini. Les
laisser dehors rétablit une demande de confirmation à chaque commande hors de l'`allow` versionné —
ce qui heurte la préférence « zéro interruption » du poste, mais redonne du sens aux 28 entrées
restreintes de `settings.json`. C'est une décision de l'utilisateur, pas de l'implémenteur, et elle
est **par poste** : elle ne s'inscrit pas dans le dépôt.

⚠️ **Cette dette est classée majeure et non mineure** parce qu'elle porte sur un dispositif dont la
raison d'être est d'être un garde-fou. Un relecteur qui peut modifier ce qu'il relit n'est pas un
relecteur dégradé : c'est un relecteur dont on ne peut plus rien conclure.

### DETTE-068 — la grille de revue et son orchestration vivent dans sept fichiers, sans garde-fou de cohérence

**Constat.** Avant le 16/08/2026, `/revue-us` était un fichier : les cinq grilles, le préambule, la
table de décharge et l'orchestration y cohabitaient. ADR-0013 décision 8 les sépare — la commande
orchestre, sept agents versionnés portent les grilles, leur modèle et leurs outils. Le gain est réel
(modèle épinglé, `Edit`/`Write` retirés, sortie des tests hors contexte) et il est documenté.

Le prix l'est aussi : **six surfaces de plus où la même chose peut être dite deux fois, et diverger.**

**Conséquence.** Trois divergences existaient déjà dans le commit qui introduit la séparation, toutes
relevées en revue et corrigées avant merge :

1. `docs/adr/0075:220` renvoyait à `.claude/commands/revue-us.md` pour la règle `12-ADR` — déménagée
   dans `revue-axe-c2.md`. Or ADR-0075 désigne ce renvoi comme **la contrepartie** d'une règle qui
   borne la détection : un pointeur mort y annule la garantie.
2. `docs/dette.md:7` (l'en-tête de ce fichier) renvoyait au même endroit pour les règles 14-15.
3. `revue-axe-a.md` recopiait la liste des fichiers qui suspendent la décharge **sans**
   `porte-mecanique.md` — c'est-à-dire sans le fichier qui suspendait la décharge sur ce lot précis.

Le mode de défaillance est celui d'un renvoi qui **se lit comme une preuve** : personne ne vérifie un
lien qui a l'air juste.

**Pourquoi non corrigée.** Il n'y a pas de correctif mécanique proportionné. Un test qui comparerait
la commande et les grilles devrait comparer deux textes en prose qui divergent **légitimement** —
chaque agent reformule sa consigne pour son propre usage. Le coût dépasserait le mal (règle 12 :
la rigueur va au moteur métier, pas à l'outillage ; règle 16 : pas de remède structurel sans preuve
et sans chiffrage).

Trois atténuations sont en place, et elles sont ce qui maintient la sévérité à *mineur* :

- la liste de suspension n'existe plus qu'en **un** exemplaire (le principe est chez l'agent, la
  liste illustrative dans la commande) ;
- la règle de **sécurité** est délibérément dupliquée à l'identique dans les cinq grilles, parce
  qu'elle se charge avec la grille au lieu d'être retranscrite à la main ;
- la section « Concordance des numéros » est rétablie dans la commande, avec l'avertissement que la
  numérotation vit désormais dans sept fichiers.

**Résorption.** La **prochaine** divergence constatée l'ouvre. Formulation choisie à dessein : le
seuil « au troisième cas » qu'ADR-0013 proposait initialement était **déjà franchi à la rédaction**,
et DETTE-067 a montré ce que produit un déclencheur atteint le jour de son inscription — il ne se
déclenche jamais *plus tard*, et il neutralise l'entrée.

La piste la moins chère est identifiée, sur preuve du code d'aujourd'hui : `_RACINES_DE_CODE` de
`backend/atlas/sources/adr.py` ne contient ni `.claude/` ni `journal-d-avancement/`, si bien que **4
des 7 lignes** de la table « Porté dans le code par » d'ADR-0013 sont invisibles au contrôle
`portage-inexistant` — pourtant bloquant en CI. Deux éléments de tuple suffiraient à vérifier
l'**existence** des fichiers nommés (pas leur contenu). C'est une modification du générateur d'atlas,
donc de la configuration d'outillage : elle relève d'une US `chore/` dédiée, jamais du lot courant.

### DETTE-067 — le JavaScript de l'atlas n'est ni typé ni linté

**Ce que fait le code.** `atlas/statique/` porte 1 837 lignes de JavaScript navigateur (coquille,
rendu des pages, schémas SVG) écrites sans TypeScript, sans build, et **sans passer sous aucun
linter**. *(Élargie le 16/08/2026 par `E00US019` : + 420 lignes — la vue d'avancement, le graphe
des epics et la fiche d'US ; puis le même jour par `E00US020` : **+ 353 lignes de JS** (+ 371 en
comptant le CSS) — la carte du code, le schéma du sens des dépendances, la matrice et l'inventaire
des ports. Le delta annoncé au premier jet, « + 387 », mélangeait le JS, le CSS **et** la page
HTML, qui n'entre pas dans le périmètre de cette dette.)*

**Pourquoi l'écart existe.** `eslint` et `prettier` s'exécutent depuis `frontend/` : leurs hooks
pre-commit sont cadrés `files: ^frontend/` et leurs étapes de CI ont `working-directory: frontend`.
`atlas/` vit à la racine et leur est donc invisible. Les rallier demanderait soit d'élargir le
périmètre de l'outillage du front à un dossier qui n'en fait pas partie, soit d'installer une
seconde chaîne Node pour ~1 470 lignes sans build — les deux contredisent la règle 12 (« la rigueur
va au moteur métier, pas à l'outillage ») pour un site de documentation.

**Ce qui borne le risque.** Le site ne touche **aucune donnée du tournoi** : il lit des fichiers
générés et affiche du texte. Une régression y dégrade la lecture d'une documentation, jamais un
score ni un placement. Et les trois fautes qui ne se voient pas en développement sont, elles,
couvertes mécaniquement par `backend/tests/test_atlas_site.py` : un `fetch()` ou un module ES
(parfait en `localhost`, mort en `file://`), une ressource externe (le jour J est hors ligne), un
`viewport` manquant. Ce qui reste non couvert est le **rendu** : rien ne dit qu'une page est
lisible à 360 px — d'où la checklist manuelle dans `atlas/README.md`.

**Résorption — ouverte, le déclencheur est franchi.** Deux déclencheurs avaient été écrits pour ne
pas être négociés au cas par cas : si `atlas/statique/` dépasse **2 000 lignes**, ou si un défaut de
rendu échappe **deux fois**. Le premier était **à 20 lignes** au 16/08/2026 (1 980), avec cette
clause : « la prochaine US qui touche `atlas/statique/` ouvre la résorption, elle ne relève pas le
seuil ». `E00US020` l'a franchi le jour même (**2 367 lignes**) en ajoutant la carte du code. La
clause s'applique **telle qu'écrite** : la résorption est planifiée en `E00US026`, et le seuil n'est
pas relevé. C'était tout l'intérêt de l'écrire à l'avance — le seuil précédent avait, lui, été
franchi le jour de sa rédaction, ce qui l'avait rendu inopérant.

⚠️ *Le seuil a été corrigé en revue.* Il disait « ~1 000 lignes » pour un volume estimé à
~700 — la mesure donne **1 550** (dont 1 050 de JS). Le déclencheur était donc franchi le
jour même où il était écrit, ce qui le rendait inopérant : un seuil déjà atteint ne se
déclenche jamais *plus tard*. Le nouveau est devant nous, avec ~30 % de marge. La sortie
la moins coûteuse serait alors d'étendre les patrons existants (`files: ^(frontend|atlas)/` côté
prettier, une seconde cible eslint) plutôt que d'introduire un build.
