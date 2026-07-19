# E04 — Saisie des scores en temps réel — User Stories

> EPIC : [EPIC-04](../epics/EPIC-04-saisie-scores.md) · Réfs : CDC fonctionnel M5, ADR-0005, **CDC UX §4 et §7.2**.

> ⚠️ **Maille révisée le 17/07/2026** — regroupement des US au grain « capacité » (÷3 : 18 → 6). Les
> anciennes US découpées par étape technique (saisir / valider / enregistrer / verrouiller / cumuler /
> diffuser / corriger…) sont devenues des **critères d'acceptation** de l'US de capacité qui les porte.
> **Aucun comportement n'est perdu** (règle 9 — chaque ancien titre = une puce CA identifiée). Les liens
> entrants ont été redirigés vers l'US survivante. Correspondance ancien → nouveau en fin de fichier.

> ⚠️ **Révisé le 14/07/2026** ([`cahier-des-charges-ux.md`](../cahier-des-charges-ux.md) §4, §7.2–7.3).
> **La tablette appartient à la cible, pas à la personne** : c'est un **poste fixe et ouvert** (`D-13`), et
> **ce n'est pas le scoreur qui saisit** — c'est un **marqueur** (un archer de la cible, désigné selon FFTA
> B.6.1.1) qui tape pour les 3–4 archers. Le scoreur, lui, est **itinérant** et **valide** (E10US003).
> **Deux postes distincts, pas un.** Le parc est **fourni par le club, navigateur seul, plancher tablette**
> (`D-05`, `D-02`) : **pas de mode kiosque**, donc la **fermeture accidentelle de l'onglet arrivera** — d'où
> E04US001.

---

### E04US001 — Rattacher une tablette à sa cible (QR + jeton de poste)
*En tant qu'*organisateur (au montage), *je veux* rattacher une tablette à une cible **en un scan**, *afin que* le poste sache qui il sert toute la journée — **et le retrouve tout seul après une coupure**.
- **CA** : **scan du QR de la cible** (E09US008) → le back émet un **jeton de poste** rangé dans le navigateur (`localStorage`) ; **code de secours saisi à la main** si le QR est abîmé ou l'appareil photo capricieux ; à **toute réouverture** (onglet fermé, navigateur planté, tablette redémarrée, veille de 3 h), le poste **retrouve sa cible sans rien demander à personne** ; le jeton est **lié au tournoi** et **révocable** → un **nouveau tournoi force le re-rattachement** ; le poste ne peut saisir que pour **sa** cible (E10US007) ; l'IP **n'est jamais l'identité** (diagnostic uniquement) ; **le jeton porte aussi les préférences du poste** — dont le **thème** choisi (`D-26`), qui **revient tout seul** à la réouverture.
- **Notes** : ~~« saisie d'un code de cible → session **scoreur** rattachée », v0.1~~ → **réécrite le 14/07/2026** (`D-06`, `D-07`). **Ni IP, ni empreinte** : les baux DHCP expirent (une tablette en veille perd sa cible) et une IP réattribuée ferait **partir les scores sur la mauvaise cible, silencieusement** — *un score faux et silencieux est pire qu'une erreur visible* ; l'empreinte ne distingue pas **30 tablettes identiques**. Réutilise le patron de `sessionAdminStore` (Zustand + `persist`, jeton `Bearer`, purge sur 401) → **`sessionPosteStore`** : ni concept nouveau, ni configuration réseau. **Piège traité par les CA** : *le jeton survit trop bien* — au tournoi suivant, la tablette de la cible 12 posée sur la cible 5 croirait toujours être la 12. **Le jeton porte les préférences, pas seulement le rattachement** (`D-26`, [CDC UX §4.5](../cahier-des-charges-ux.md)) : *dans un gymnase, la lumière varie d'une cible à l'autre* — la tablette sous la baie vitrée passe en thème clair, les 29 autres ne bougent pas. Sans ça, `D-05` (pas de kiosque, l'onglet se ferme) obligerait le bénévole à rebasculer son thème **à chaque réouverture**. **Arbitrage tranché le 18/07/2026 (multi-tournoi)** : « lié au tournoi » supporte **plusieurs tournois non terminés en même temps** (ex. intérieur + extérieur) — la révocation s'ancre sur le **statut** du tournoi (terminer un tournoi invalide ses jetons de poste ; régénérer les codes = E09US008), **jamais** sur un « tournoi courant » global. Le contrat d'identité du poste (code de cible généré/stocké, jeton opaque en mémoire, en-tête `X-Jeton-Poste`) est fixé par [ADR-0029](../docs/adr/0029-mode-d-identite-poste-de-cible-et-jeton-de-poste.md) — **3ᵉ mode de `D-13`, après le scoreur (ADR-0025)**. La garde s'appuie sur le `terminé` du cycle **actuel à 3 statuts** ; à réaligner quand E01US017 livrera les **7 statuts**.
- **Recette (ENF-7, 18/07/2026)** : une **seule tablette** disponible en test. Le jeton étant en `localStorage` **par origine**, un navigateur ne porte **qu'un** poste — exercer le multi-poste (plusieurs rattachements, diffusion, supervision E12US001) demande des **contextes séparés** (profils / navigation privée) ou le PC de dev comme postes additionnels ; la tablette valide le *device-specific* (tactile, QR, Wake Lock). Cf. [`guide-architecture.md`](../guide-architecture.md) §9.
- **Dépend de** : E03US001, E01US001 · **Jalon** : J1

### E04US002 — Saisie de qualification en temps réel
*En tant que* **marqueur**, *je veux* saisir, valider, cumuler et corriger les flèches de qualification sur ma cible, *afin de* produire le score en temps réel — sans rien perdre ni laisser d'incorrigible.
- **CA — grille (ex-002)** : archers/positions de la cible **déduits du poste et de son départ courant** (le poste choisit son départ — [ADR-0034](../docs/adr/0034-poste-selectionne-son-depart-courant.md) — puis les archers viennent des affectations `(cible, départ)` — [ADR-0033](../docs/adr/0033-source-de-saisie-affectations-cible-depart.md), *pas* de `Archer.cible`) ; volée courante mise en évidence ; **grain de validation actif indiqué** (« validation à la fin de la série », `D-11`, E01US015) ; adapté au tactile — **cibles ≥ 48 px**, plancher **768 px** (`D-02`).
- **CA — marqueur (ex-017)** : au début du départ, **désignation du ou des marqueurs** parmi les archers de la cible (**plusieurs possibles**) ; **marqueur actif affiché discrètement et changé en un geste** (pas de sélecteur permanent qui vole l'espace du pavé) ; **chaque volée enregistre qui l'a saisie**, consultable (« volée 7 saisie par DURAND, 10h42 ») ; **déclaratif, pas authentifié** (E10US007 : le poste reste ouvert) ; alimente **E10US005** (`D-04`).
- **CA — pavé (ex-003)** : pavé de valeurs **déduit du blason tiré** (`Blason.zones`, E01US014) et **non** du barème de la phase — sur un triple 40 les touches 5→1 n'existent pas (FFTA §4.4) ; gros boutons ; correction possible avant validation.
- **CA — valeurs légales (ex-004)** : refus d'une valeur hors barème ; nombre de flèches par volée conforme au barème (E01US009).
- **CA — enregistrement (ex-005)** : volée persistée par la **file d'écriture** (writer unique) ; accusé de réception au client ; **idempotence par identifiant de saisie** (mécanisme **introduit ici** — cf. « Arbitrages » ; ⚠️ la mention initiale « ADR-0005 » était fausse : ADR-0005 ne couvre que la **sérialisation** single-writer, pas l'idempotence de la saisie).
- **CA — édition avant validation (ex-006)** : volée modifiable tant que la série n'est pas validée ; historique non requis à ce stade.
- **CA — validation & verrou (ex-007)** : après validation, la série est **verrouillée** (non éditable hors correction habilitée, cf. CA suivant) ; **la validation porte le nom du scoreur** (E10US003, alimente E10US005) ; **grain de validation lu dans la phase** (`config.validation`, E01US015 : fin de série / fin de duel / toutes les N volées).
- **CA — cumul (ex-008)** : total mis à jour à chaque validation, conforme au barème.
- **CA — correction tracée (ex-012)** : un score **verrouillé** n'est corrigeable que par un **rôle habilité** ; toute correction écrit une entrée d'**AuditLog** (qui / quand / avant-après, E10US005) et **recalcule le cumul**.
- **Notes** : **la validation est un acte *de fin*** — FFTA : les feuilles de marque sont signées « à la fin de la distance, de la compétition **ou du duel** ». L'art. B.6.1.2 (« établissement des scores toutes les 2 volées ») porte sur le **cumul** (calculé par l'appli), **pas** sur la validation par un tiers : valider toutes les 2 volées ferait **~180 passages par départ** (intenable à 3 scoreurs). La validation du scoreur **tient lieu de seconde marque** (`D-03`, FFTA B.6.1.1) — **`Q-UX3` : à confirmer par un arbitre du club**. Le **marqueur** (`D-04`) : *il change rarement, donc l'interface ne s'organise pas autour de ce changement* (**pas de sélecteur permanent** au-dessus de la grille) ; la trace est l'**équivalent numérique de la signature** de la feuille de marque (FFTA B.6.1.1), seul argument sérieux face à un arbitre contestant la dématérialisation. La **correction tracée** (ex-012) est le seul chemin d'écriture sur une série verrouillée.
- **Arbitrages tranchés le 19/07/2026** (reversés ici — règle 9 ; pour que l'implémentation d'E04US002
  n'en dérive pas des tests faux) :
  - **Redécoupage : backend d'abord (en trois tranches), front en dernier.** L'US absorbe 9 ex-US et
    traverse toutes les couches : trop grosse pour une branche revue en une passe (ADR-0021). Le
    backend est livré en **trois PR** de maille « capacité », dans cet ordre :
    - **PR1 « moteur métier »** (`feat/e04us002-saisie-backend`, **mergée**) : **domaine** `Serie`/
      `Volee` (saisie, validation par grain, verrou, cumul, correction tracée) + **service**
      `ServiceSaisie` (résolution config, pilotage, entrées d'audit) + les **ports** (`SerieRepository`,
      `AuditRepository`). **Aucune persistance** : le moteur n'écrit encore rien.
    - **PR2a « persistance & atomicité »** (`feat/e04us002-saisie-persistance`, **cette branche**) :
      ORM `SerieORM`/`VoleeORM` + **migration** `0026` (DETTE-001), adapter `SerieRepositorySQL`
      réalisant l'**atomicité acte↔trace** (session partagée, ADR-0035 ; `consigner_dans` sur
      l'adapter audit **concret** — cf. rectification règle 1 ci-dessous), **câblage** de
      `ServiceSaisie`. Le moteur PR1 **persiste** désormais ; aucun endpoint (le service reste
      appelable en interne, testé sur vraie base).
    - **PR2b « exposition & contexte poste »** (`feat/e04us002-saisie-exposition`, **livrée**) :
      **départ courant du poste** (extension E04US001, [ADR-0034](../docs/adr/0034-poste-selectionne-son-depart-courant.md)),
      **source des archers** = affectations `(cible, départ)` ([ADR-0033](../docs/adr/0033-source-de-saisie-affectations-cible-depart.md)),
      **garde « SA cible / SON départ » au service**, **idempotence par identifiant de saisie**
      ([ADR-0036](../docs/adr/0036-idempotence-de-la-saisie-par-identifiant-en-memoire.md)),
      **`created_at` de volée** (le « quand », préservé par numéro), **endpoints API** + DTOs :
      côté **poste** (fixer départ, grille, saisir volée, relire série) et côté **scoreur** (valider,
      corriger). **Le retrait de la démo `saisir_score` est différé** — cf. arbitrage ci-dessous.

    La **grille tactile** part en **dernière tranche** front (`feat/e04us002-saisie-grille`,
    **livrée** 2026-07-19) : cibles ≥ 48 px, pavé déduit du blason, sélecteur de départ courant,
    marqueur discret, navigateur de volées, grain affiché. Le **panneau de routage** post-validation
    n'y est **pas** — c'est E04US018 (bloquée, dépend d'E03US009) ; la surface **scoreur**
    (validation/correction, §7.3) et la **file hors-ligne / diffusion live** (E04US009) non plus. La
    doc `docs/fonctionnel/E04US002.md` accompagne cette tranche (première UI à décrire).
  - **Rectification règle 1 sur la couture d'audit (PR2a).** ADR-0035 §1 posait que « le port
    `AuditRepository` gagne `consigner_dans(session, …)` ». Impossible : le port vit dans le domaine,
    un paramètre `Session` (SQLAlchemy) y violerait la règle 1 (garde-fou AST). `consigner_dans` est
    donc sur l'**adapter concret** `AuditRepositorySQL` (infra→infra) ; le port domaine reste
    `consigner`/`par_tournoi`. ADR-0035 §1 amendé au même commit. Correction de **forme**, pas de fond.
  - **Le `created_at` d'une volée (le « quand », ex-017) reste PR2b.** PR2a persiste l'état **saisi**
    de l'agrégat (numéro, valeurs, marqueurs, verrou) ; l'horodatage de ligne — métadonnée du chemin
    de **lecture/consultation** (« volée 7 saisie par DURAND, 10h42 ») — arrive avec la surface qui le
    montre. Le persister à vide en PR2a serait spéculatif (et l'upsert par purge+réinsertion en
    réinitialiserait la valeur à chaque sauvegarde : la question d'identité des volées se traite en PR2b).
  - **Le poste sélectionne son départ courant — [ADR-0034](../docs/adr/0034-poste-selectionne-son-depart-courant.md).**
    Le CA « archers déduits du jeton de poste » était **insatisfiable en l'état** : le `Poste` ne
    connaît que `(tournoi_id, cible_index)`, mais les `Affectation` sont **par départ** et une cible
    sert plusieurs départs. Résolution (arbitrée avec l'utilisateur) : le poste, une fois rattaché à
    sa cible, se met « en mode départ X » (**geste manuel**, état de session) ; les archers A–D
    viennent alors des affectations `(cible, départ)`. Le cas courant est **mono-départ** (présélection
    côté front), mais le modèle **supporte N départs** (chevauchement). **L'automatisation** (« lancer
    un tour » bascule tous les postes d'un coup) est **différée à E12US002** : même geste, orchestré —
    hors périmètre ici, acté pour que ce soit un **choix**, pas un oubli.
  - **Source des archers = affectations `(cible, départ)`, pas `Archer.cible` — [ADR-0033](../docs/adr/0033-source-de-saisie-affectations-cible-depart.md).**
    Le champ walking-skeleton `Archer.cible` n'est plus source de saisie ; on reconstitue via
    `PlacementRepository.par_depart` filtré sur `cible_index` → position A–D. Le contrôle « SA cible »
    (ADR-0030) s'étend au **triplet** `(tournoi, cible, départ)`. La démo `saisir_score` (mono-point,
    sur `Archer.cible`) est **retirée** au profit de la nouvelle surface volée-par-volée.
  - **Atomicité acte↔trace : couture de session partagée — [ADR-0035](../docs/adr/0035-atomicite-acte-trace-session-partagee.md).**
    Décision (arbitrée avec l'utilisateur) parmi les trois options remontées par la revue
    adversariale d'E10US005 : **co-localiser** l'écriture du score et la consignation d'audit dans
    **une seule session, un seul commit** (tout ou rien), sur le patron `ArcherRepositorySQL.supprimer`.
    `AuditRepository.consigner` gagne un mode « session fournie » (`consigner_dans(session, entree)`,
    sans commit) ; le chemin autonome d'E10US005 est préservé. Fini la fenêtre « validation non tracée /
    trace fantôme ».
  - **Idempotence par identifiant de saisie : mécanisme introduit ici** (⚠️ la mention « ADR-0005 »
    du CA était **fausse** — ADR-0005 ne traite que la sérialisation single-writer). Le client fournit
    un **identifiant de saisie** ; la commande de la file **dédoublonne** (un rejeu réseau ne crée pas
    une volée en double). Marqueur `# E04US002 : idempotence` à l'endroit de la déduplication.
  - **DETTE-011 (`Score`→`Fleche`) n'est PAS résorbée ici.** Le vrai scoring modélise la flèche comme
    **valeur** (`ZoneScore`) dans une `Volee`, pas comme entité : `Serie`/`Volee` **remplaceront**
    `Score` pour la **saisie** — dès la **plomberie PR2** (la PR1 « moteur métier » n'écrit encore
    rien) —, mais l'agrégat `Score` **survit** comme modèle de lecture du **classement de démo**
    (`calculer_classement`) jusqu'à son rebasage sur les volées en **E06US001**. Le nom-clash que
    DETTE-011 redoutait est **évité** (le total s'appelle `cumul`, pas `Score`) ; le renommage reste un
    nettoyage à part, à l'ère E06. Le classement de démo deviendra un **stub sans données** une fois
    la plomberie PR2 livrée (la démo `saisir_score` retirée, plus aucun `Score` écrit) — régression
    d'un démonstrateur, pas d'un cas utilisateur réel ; E06US001 le corrige.
  - **Dépendance E10US005 satisfaite en amont** : elle était insatisfiable (l'US 005, seq 47, vient
    *après* cette US, seq 41, et n'existait pas). Son **socle** (agrégat `EntreeAudit`, port
    `AuditRepository`, `ServiceAudit.consigner`, port `Horloge`) a été **livré d'abord**. La validation
    consigne `action=VALIDATION` (auteur = **nom du scoreur** — `exiger_scoreur` devra **résoudre le
    `Scoreur`**, aujourd'hui il ne fait que valider) ; la correction tracée consigne
    `action=CORRECTION_SCORE, avant, apres, auteur=nom du rôle habilité`.
  - **`avant`/`apres` : passer `None`, jamais `""`** — le socle les conserve **verbatim** (pas de
    normalisation) : `""` est distinct de `NULL` en base et à la relecture. Une `CORRECTION_SCORE`
    **porte** avant/après ; une validation les laisse à `None` (un `""` afficherait un « avant » vide).
  - **Le « quand » d'une saisie (ex-017, « …10h42 »)** est porté par le **`created_at` de la ligne
    volée** en PR2 (métadonnée de persistance, comme l'`id`), *pas* un champ du domaine — consultable
    via le chemin de lecture PR2. *(Arbitrage de revue du 19/07 : réversible/additif si un besoin
    domaine émergeait.)*
  - **Garde « SA cible / SON départ » au service, pas à l'API (ADR-0033 §3, remontée de la revue
    adversariale).** En PR2, la signature de `ServiceSaisie` recevra le **contexte poste**
    `(cible_index, depart_id)` et vérifiera l'appartenance de l'archer avant d'écrire — pas dans un
    `Depends` d'API, qu'un appelant hors HTTP (writer WS E04US009, orchestrateur E12US002)
    contournerait. Marqueur `# E04US002 (PR2)` posé dans `ServiceSaisie._charger_archer`.
  - **Durcissements du serveur autoritaire (revue du 19/07).** Le domaine borne le **rang de volée**
    par le barème (`1 <= numero <= nb_volees`), symétrique de la garde flèches (ex-004) : sans quoi
    une volée hors barème gonflerait le cumul (ex-008). La complétude d'une série est jugée sur
    l'**ensemble** exact `{1..N}`, pas un décompte. Une volée verrouillée **nomme** son validateur :
    un nom vide est refusé au domaine (`NomIntervenantInvalide`), sans l'emprunter à la couche audit.
  - **Arbitrages de la tranche exposition (PR2b, 2026-07-19) :**
    - **Le « rôle habilité » à corriger (ex-012) est le scoreur.** Le CA ne le nommait pas ; lu
      comme le **scoreur**, cohérent avec « validation = scoreur seul » (le correcteur d'un score
      verrouillé est la même autorité de marque que le validateur). L'admin, lui, peut tout
      (E10US001). Réversible si un rôle distinct (« arbitre ») émergeait — c'est un guard d'endpoint.
    - **Le scoreur est itinérant *dans son tournoi*.** `ScoreurHorsTournoi` (403) refuse un scoreur
      qui validerait/corrigerait dans un tournoi voisin — la faille se rouvrirait en concurrence de
      tournois. Même famille que `SaisieHorsCible`. Garde à l'endpoint (il tient le `Scoreur` résolu ;
      `exiger_scoreur` **résout désormais le scoreur**, non plus un simple booléen).
    - **Sans départ courant, le poste ne saisit pas** (`DepartCourantNonDefini`, 409) — refus
      explicite d'ADR-0034 §1, distinct du 403 « hors cible » (le départ *est* fixé mais l'archer
      n'y est pas).
    - **Idempotence : registre en mémoire, borné, volatil ([ADR-0036](../docs/adr/0036-idempotence-de-la-saisie-par-identifiant-en-memoire.md)).**
      Consulté **dans** la commande de la file (writer unique) ; aligné sur le modèle de session
      (jeton de poste ADR-0029, départ courant ADR-0034, eux aussi volatils). Corrige la mention
      « ADR-0005 » du CA, qui était fausse.
    - **`created_at` de volée hors du domaine `Volee`** (métadonnée de persistance, comme l'`id`) :
      posé par le repository via `Horloge`, **préservé par numéro** au travers du purge + réinsertion,
      exposé par un port `SerieRepository.horodatages` que le service joint à la série (`etat_serie`).
    - **Retrait de la démo `saisir_score` différé en US de nettoyage dédiée.** ADR-0033 le prévoyait
      « dans cette US » ; mais `/scores` (walking skeleton E00US011) est le **véhicule de test** du
      fil rouge — l'E2E `test_tranche_verticale`, les tests « archer engagé » (catégorie/suppression),
      la diffusion temps réel **sèment tous via `/scores`**. Son retrait casse/réécrit ~10 tests : un
      chantier à isoler, pas à bâcler dans la PR d'exposition. La démo **coexiste** sans conflit avec
      la nouvelle surface (tables `score` vs `serie`/`volee` distinctes) — pas de régression ;
      le classement de démo reste alimenté jusqu'au nettoyage, puis stub jusqu'à E06US001.
  - **Arbitrages de la tranche grille (front, 2026-07-19) :**
    - **Le pavé est exposé *dans la grille*, par archer — pas re-dérivé côté front.** Le CA « pavé »
      veut les touches illégales **absentes** (triple 40 → pas de 5→1). La grille exposée en PR2b
      (`ArcherGrilleReponse`) ne portait que `{position, archer_id, nom, prénom}` — ni `zones`, ni
      même `categorie_id`. Reconstituer `archer → catégorie → blason → zones` côté front, c'était 2–3
      appels fragiles **et** re-dériver une règle de scoring dont **le serveur est l'autorité**. Choix
      (additif, pas de migration) : `ArcherGrilleReponse` gagne `zones: list[str]` (le service dérive
      déjà, `_zones_du_blason`), dans l'ordre canonique. La grille est **tolérante** (`[]` si le
      blason est indéterminable, robustesse jour J) ; le chemin d'**écriture** reste strict
      (`BlasonIntrouvable`, 404 — erreur **visible**, pas de score faux silencieux).
    - **La « volée courante » avance dès qu'une volée est *saisie*, pas *validée*.** Piège corrigé en
      cours d'implémentation : la validation (le verrou) est l'acte du **scoreur**, plus tard — rien
      ne se verrouille pendant la saisie. Une « prochaine à saisir = plus petite non verrouillée »
      aurait **bloqué le marqueur sur la volée 1**. Retenu : prochaine = plus petite **non saisie** ;
      l'édition d'une volée déjà saisie (tant que non validée — CA « édition avant validation ») passe
      par un **navigateur de volées** explicite.
    - **Périmètre de la tranche : poste de cible (marqueur) seul.** Exclus, chacun sa surface/US : la
      **validation & correction** (scoreur, §7.3), le **panneau de routage** (E04US018, bloquée), la
      **file hors-ligne + diffusion live** (E04US009). Conséquence assumée : sans surface scoreur, le
      **cumul officiel reste à 0** (il ne compte que le validé) — la saisie se teste de bout en bout
      via l'API scoreur (livrée en PR2b), l'UI scoreur viendra ensuite.
- **Absorbe** : ex-E04US002 à 008, E04US012, E04US017. **Dépend de** : E04US001, E01US009, E01US014, E01US015, E00US007, E10US003, E10US005, E10US007 · **Jalon** : J1

### E04US009 — Diffusion live & résilience réseau
*En tant que* public/organisateur (le live) et scoreur (les coupures), *je veux* que les scores validés se diffusent en direct et survivent à une coupure brève, *afin de* suivre l'épreuve et de **ne rien perdre**.
- **CA — diffusion live (ex-009)** : après validation (E04US002), **diffusion WebSocket** ; les abonnés (écran de salle, mobile) se mettent à jour en **< 1–2 s**.
- **CA — file hors-ligne (ex-010)** : hors-ligne, les saisies sont **mises en file côté front** et **rejouées à la reconnexion** ; **pas de doublon** (idempotence, ADR-0005).
- **CA — indicateur (ex-011)** : **état de connexion visible** en permanence — connecté / hors-ligne / synchronisation en cours.
- **Absorbe** : ex-E04US009 à 011. **Dépend de** : E00US008, E04US002 · **Jalon** : J1

### E04US013 — Saisie en duels
*En tant que* scoreur, *je veux* saisir un duel au système de sets, en désigner le vainqueur et résoudre les égalités, *afin de* faire progresser le tableau.
- **CA — sets (ex-013)** : points de set attribués selon le barème (FFTA : premier à **6 pts** sur 5 sets ; format club : 4 pts) ; cumul des points de set du match ; **les arcs à poulies ne tirent pas en sets** mais au cumul (FFTA A.7.5.2) — le barème se résout par (phase, arme), cf. EF-3.4.
- **CA — vainqueur (ex-014)** : vainqueur calculé selon le barème de sets ; transmis au moteur (E05US005).
- **CA — barrage/shoot-off (ex-016)** : à égalité, saisie d'un **shoot-off** (1 flèche) ; plus près du centre départage ; vainqueur enregistré — politique `tiebreak` (ADR-0004), presets FFTA.
- **Notes** : **incohérence corrigée le 17/07/2026** — l'ex-`E04US016` déclarait « Dépend de E06US003 » alors que `E06US003` (barrage de places au classement) dépend elle-même de l'ex-`E04US016` : cycle. La saisie du shoot-off est le **mécanisme**, le classement de barrage en est un **consommateur** ; la dépendance ne va que dans un sens (`E06US003` → cette US). La dépendance inverse est retirée.
- **Absorbe** : ex-E04US013, E04US014, E04US016. **Dépend de** : E01US011, E05US005 · **Jalon** : J2

### E04US015 — Gérer abandon / disqualification
*En tant que* scoreur, *je veux* enregistrer un abandon/DSQ, *afin de* refléter la réalité.
- **CA** : statut spécial sur un archer/match ; impact correct sur la progression et le classement ; **les flèches déjà tirées sont préservées** — un archer qui abandonne reste dans les résultats avec son statut, il n'en disparaît pas.
- **Notes** : c'est l'**alternative désignée à la suppression d'archer** (E02US003) pour l'abandon en **qualification** — le seul cas exerçable avant les duels ([ADR-0016](../docs/adr/0016-supprimer-un-archer-engage-plutot-que-le-refuser.md), arbitrage métier du 16/07/2026). La préservation des flèches n'est pas un détail d'implémentation : c'est **ce qui distingue** l'abandon de la suppression, laquelle les détruit. Un abandon qui effacerait les résultats rendrait ADR-0016 faux. **E12US004 élargit** cette US aux duels (forfait daté, attribué, réversible, audité). Tant que cette US n'est pas livrée, un archer qui abandonne n'a **aucun** moyen propre d'être enregistré, et la suppression est à portée de clic pour faire exactement la mauvaise chose — d'où sa priorité.
  > **Restée séparée au regroupement ÷3 du 17/07/2026** (elle n'a pas rejoint « Saisie en duels ») : elle est **ancrée par [ADR-0016]** (qui lui fait porter l'abandon en qualification *et*, via E12US004, aux duels) — un ancrage ADR ne se fond pas dans une US de capacité. *Incohérence latente à signaler, non tranchée ici : le jalon (J2) et la dépendance (duels) contredisent le « abandon en qualification » de la note ; à arbitrer hors refactor de maille.*
- **Dépend de** : E04US013 · **Jalon** : J2

### E04US018 — Afficher la prochaine cible après validation
*En tant qu'*archer, *je veux* voir **où je tire ensuite** dès que le scoreur a validé, *afin de* ne pas avoir à chercher ni à demander.
- **CA** : dès la validation (E04US002), la tablette **bascule en panneau de routage** : pour **chaque** archer de la cible, sa **prochaine affectation** (cible, position, heure, tour), son **repêchage**, ou son **rang final** s'il est éliminé ; l'affichage est **instantané** — rien n'est calculé à cet instant (`D-08`) ; retour à la grille pour la suite.
- **Notes** : `D-09` — **canal n°1 des 4 canaux de routage**, et **besoin absent des 117 US d'origine**. Ne couvre **que celui qui est encore là** : l'archer valide, range ses flèches et part — **l'info doit le suivre** sur son téléphone (**E07US008**). Fonctionne parce que **les cibles sont attribuées aux *matchs*** (positions de tableau), pas aux archers : « le match n°3 des 1/8ᵉ se tire sur la cible 4, quel que soit son vainqueur » → l'info existe **avant même le duel** (E03US009).
- **Dépend de** : E04US002, E03US009 · **Jalon** : J2

---

## Correspondance ancien → nouveau (maille ÷3 du 17/07/2026)

| Ancienne US | Titre d'origine | Devient |
|---|---|---|
| E04US001 | Rattacher une tablette à sa cible | **E04US001** (inchangée) |
| E04US002 | Afficher la grille de saisie | **E04US002** — CA « grille » |
| E04US003 | Saisir les flèches (pavé) | **E04US002** — CA « pavé » |
| E04US004 | Valider les valeurs autorisées | **E04US002** — CA « valeurs légales » |
| E04US005 | Enregistrer une volée via la file | **E04US002** — CA « enregistrement » |
| E04US006 | Éditer une volée non validée | **E04US002** — CA « édition avant validation » |
| E04US007 | Verrouiller une série validée | **E04US002** — CA « validation & verrou » |
| E04US008 | Cumuler le score sur les volées | **E04US002** — CA « cumul » |
| E04US009 | Diffuser la mise à jour en live | **E04US009** — CA « diffusion live » |
| E04US010 | Mettre en file hors-ligne + rejouer | **E04US009** — CA « file hors-ligne » |
| E04US011 | Indicateur d'état de connexion | **E04US009** — CA « indicateur » |
| E04US012 | Corriger une volée validée (tracé) | **E04US002** — CA « correction tracée » |
| E04US013 | Saisie en sets (duels) | **E04US013** — CA « sets » |
| E04US014 | Désigner le vainqueur d'un match | **E04US013** — CA « vainqueur » |
| E04US015 | Gérer abandon / disqualification | **E04US015** (inchangée) |
| E04US016 | Déclencher un barrage/shoot-off | **E04US013** — CA « barrage/shoot-off » |
| E04US017 | Désigner et tracer le marqueur | **E04US002** — CA « marqueur » |
| E04US018 | Afficher la prochaine cible après validation | **E04US018** (inchangée) |
