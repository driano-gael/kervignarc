# E10 — Accès & rôles — User Stories

> EPIC : [EPIC-10](../epics/EPIC-10-acces-roles.md) · Réfs : CDC technique §9, ADR-0007, **CDC UX §5 (`D-13`)**.

> ⚠️ Maille révisée le 17/07/2026 — E10US001/002 (livrées) et E10US004 (caduque) inchangées ;
> E10US003 absorbe E10US008. Correspondance ancien → nouveau en fin de fichier.

> ⚠️ **Révisé le 14/07/2026** ([`cahier-des-charges-ux.md`](../cahier-des-charges-ux.md) §5, `D-13`). Le modèle
> à **quatre rôles** (public / archer / scoreur / admin) est remplacé par **trois modes d'identité**
> proportionnés au risque, dont **aucun n'est un compte utilisateur** — le jour J, personne n'a le temps
> d'en créer :
>
> | Qui | Identifié par | Peut | Ne peut pas |
> |---|---|---|---|
> | **Public** | rien | lire | tout le reste |
> | **Poste de cible** | **le lieu** (jeton de poste, **aucune auth**) | **saisir** pour sa cible | valider, configurer |
> | **Scoreur** | **la personne** (code individuel) | **valider** n'importe quelle cible | configurer |
> | **Admin** | **un secret** (login + mdp) | tout | — |
>
> **Il n'y a pas de rôle archer** : la tablette est fixée à la cible et **ouverte** — qui tape dessus est
> légitime par construction. **E10US003** et **E10US007** sont réécrites en conséquence ; **E10US004**
> devient caduque.

---

### E10US001 — Consultation publique ouverte
*En tant que* spectateur, *je veux* accéder aux résultats sans compte, *afin de* consulter librement.
- **CA** : toutes les **lectures** (`GET`) sont accessibles sur le LAN **sans authentification** ; **aucune écriture** n'est possible sans session valide (chaque endpoint d'écriture renvoie 401 sans jeton) ; l'UI n'expose aucune action d'écriture au public (formulaires de saisie masqués hors session). Garanti par test.
- **Notes** : ~~les **quatre rôles** sont cadrés (public = lecture ; **archer** = saisir ; **scoreur** = saisir + valider ; **admin** = configurer)~~ → **révisé le 14/07/2026 (`D-13`)** : **trois modes d'identité** (public = lecture ; **poste de cible** = saisir, identité par le **lieu**, sans auth ; **scoreur** = **valider**, identité par la **personne** ; admin = configurer). **Il n'y a pas de rôle archer.** Faute de ces modes encore implémentés, les écritures aujourd'hui ouvertes (inscription, placement, saisie de score de la tranche démo) restent **fermées en intérim derrière l'auth admin** ; leurs US (**E10US007** poste de cible, **E10US003** scoreur, EPIC-02 inscriptions) **élargiront** ensuite l'autorisation endpoint par endpoint (l'admin reste autorisé). Réutilise `exiger_admin` (E10US002).
- **Dépend de** : E00US009, E10US002 · **Jalon** : J1

### E10US002 — Accès administrateur protégé
*En tant qu'*organisateur, *je veux* un accès admin protégé par identifiant + mot de passe, *afin de* sécuriser la configuration.
- **CA** : au **1ᵉʳ accès admin** (aucun identifiant défini), l'app propose de **définir** le login + mot de passe ; ensuite, l'accès aux fonctions admin exige une **connexion** (login + mot de passe) ; une connexion réussie ouvre une session (jeton) jointe aux actions admin ; sans jeton valide, les actions admin sont refusées (401). Périmètre protégé de cette US : **création de tournoi** (config). La **lecture reste publique** (E10US001).
- **Notes** : auth = concern **technique** (application + infrastructure), pas d'entité domaine. Identifiants stockés dans un fichier **`.env` à la racine** (`KERVIGNARC_ADMIN_LOGIN` / `KERVIGNARC_ADMIN_PASSWORD`) — compromis de sécurité **assumé** (appli mono-club LAN) ; ce fichier est aussi la **porte de secours** en cas d'oubli (édition sur la machine serveur → redemandé au prochain accès). Comparaison en temps constant (`hmac.compare_digest`), jeton opaque (`secrets`), lecture/écriture `.env` en **stdlib** (aucune dépendance ajoutée, ADR-0009). Jeton **sans expiration** (l'expiration relève d'E10US003). `.env` **hors versionnage** (`.gitignore`).
- **Dépend de** : E00US009 · **Jalon** : J1

### E10US003 — Scoreurs du tournoi : définition & session
*En tant qu'*organisateur, *je veux* déclarer mes scoreurs et leur remettre un code, et *en tant que* scoreur, *je veux* ouvrir une session avec **mon** code, *afin de* **valider** les scores de n'importe quelle cible en laissant une trace nominative de qui a validé.
- **CA — session (ex-US003)** : saisie du code personnel → **session nominative** ; jeton persistant côté navigateur (survit à la fermeture de l'onglet) ; le scoreur **voit toutes les cibles du tournoi** et peut valider n'importe laquelle — **aucun rattachement, aucune prise en charge** (`D-12`) ; **chaque validation enregistre le nom du scoreur** (alimente E10US005) ; deux scoreurs peuvent ouvrir la même cible : le **live** la retire de la file dès qu'elle est validée (`D-12`) ; élargit l'autorisation des endpoints de **validation** au-delà de l'admin (E10US001).
- **CA — gestion des scoreurs (ex-US008)** : l'admin **crée/modifie/supprime** les scoreurs d'un tournoi (nom + **code court** généré) ; **redéfinissable à tout moment**, y compris tournoi **en cours** (`D-14`, `D-15`) — un scoreur qui ne vient pas, ça arrive ; les codes sont **imprimables** (un papier par scoreur, cf. EPIC-09) ; supprimer un scoreur **invalide sa session** mais **conserve la trace** de ses validations passées (E10US005).
- **Notes** : ~~« session par **code de cible** », v0.1~~ → **réécrite le 14/07/2026** ([CDC UX](../cahier-des-charges-ux.md) §5 et §7.3, `D-11`/`D-12`/`D-13`/`D-14`/`D-15`) : le scoreur est **itinérant**, il n'est pas rattaché à une cible — **le code de cible sert au *poste*** (E04US001), **pas à lui**. Il **valide** ; il ne saisit pas (la saisie est le geste du marqueur sur le poste de cible, E10US007). **Rend E10US004 caduque.** Même patron de jeton que `sessionAdminStore` (E10US002) → `sessionScoreurStore`. Cf. E04US002 (validation = scoreur seul) et le **grain de validation** = politique de phase (`config.validation`, `D-11`, ADR-0011). Côté définition des scoreurs : **3 à 4 scoreurs pour ~30 cibles** — **3 ou 4 codes à distribuer, pas 30** (le poste de cible, lui, est ouvert : E10US007). Module de **préparation** (« tout ce qui s'identifie se prépare à l'avance », CDC UX `P-6`), mais **accessible en permanence** (`P-3`).
- **Arbitrages tranchés le 18/07/2026** (reversés ici — règle 9 ; pour qu'E04US002/E10US005 n'en
  dérivent pas des tests faux), **formalisés dans
  [ADR-0025](../docs/adr/0025-mode-d-identite-scoreur-par-code-individuel.md)** :
  - **`Scoreur` = entité domaine** tournoi-scoped (donnée métier persistée, patron `Depart`) — pas un
    concern technique comme l'admin (un secret en `.env`). Table `scoreur`, migration `0023`.
  - **Code généré serveur, unique dans toute la base** (pas seulement par tournoi) : le login est
    `POST /api/v1/scoreurs/session {code}` **sans contexte tournoi**, le code doit donc désigner un
    scoreur sans ambiguïté. Alphabet **sans caractères confondables** (ni `I O 0 1`), 6 caractères,
    comparaison sur forme canonique (majuscules, `domain.scoreur.normaliser_code`). L'édition **fige**
    le code (comme `Depart.numero`).
  - **Session sans expiration** — le CA veut un jeton qui « survit à la fermeture de l'onglet » le
    temps d'une journée, et l'admin (plus puissant) n'expire pas ; la note d'E10US002 (« l'expiration
    relève d'E10US003 ») disait *où* on l'ajouterait, pas qu'on doit. Jeton **nominatif** en mémoire
    (jeton → scoreur), persisté `localStorage` côté navigateur.
  - **En-tête dédié `X-Jeton-Scoreur`**, orthogonal au `Authorization: Bearer` admin (deux modes
    d'identité indépendants). La dépendance `exiger_scoreur` est prête ; **E04US002** protégera les
    endpoints de **validation** en acceptant l'admin **ou** le scoreur (rien à élargir tant qu'ils
    n'existent pas — d'où le CA « session » qui, ici, n'a **pas** encore de surface de validation).
  - **Front, volet session : minimal** — login par code + confirmation nominative + déconnexion. La
    surface de **validation** (voir/valider les cibles, file triée par ancienneté) est **E04US002 /
    E12US001**, pas cette US. La **liste** des scoreurs (avec codes) est réservée à l'**admin**.
- **Absorbe** : ex-E10US003, E10US008. **Dépend de** : E10US002, E01US001 · **Jalon** : J1

### E10US004 — ~~Habiliter un scoreur sur plusieurs cibles~~ · **caduque**
> ⛔ **Caduque depuis le 14/07/2026** (`D-12`, CDC UX §7.3). **Ne pas réaliser.** L'US supposait un scoreur
> *habilité* sur un sous-ensemble de cibles. Or le scoreur est **itinérant par nature** : il voit **toutes**
> les cibles du tournoi et choisit celle qu'il valide (E10US003 réécrite). L'habilitation par cible n'a plus
> d'objet — et elle serait nuisible : si un scoreur prend du retard, les autres doivent pouvoir l'aider.
> *Conservée pour l'historique (l'ID n'est pas réattribué).*

### E10US005 — Journal d'audit métier
*En tant qu'*organisateur, *je veux* tracer les actions sensibles, *afin de* gérer les litiges.
- **CA** : `AuditLog` des corrections de score, validations, forfaits (qui/quand/avant-après) ; consultable par l'admin.
- **Dépend de** : E10US002 · **Jalon** : J1

### E10US006 — Modifier le mot de passe admin
*En tant qu'*organisateur connecté, *je veux* changer mon login/mot de passe depuis l'app, *afin de* faire tourner l'accès sans éditer le fichier à la main.
- **CA** : depuis une session admin valide, modifier le login et/ou le mot de passe en fournissant le **mot de passe actuel** ; en cas de succès, `.env` est réécrit et les sessions existantes restent valides (ou sont invalidées — au choix d'implémentation, documenté).
- **Notes** : réutilise le store d'identifiants `.env` d'E10US002 (écriture) ; édition directe de `.env` reste la porte de secours en cas d'oubli. Pas d'entité domaine.
- **Dépend de** : E10US002 · **Jalon** : J4 (confort/robustesse ; déplaçable en J1 si prioritaire)

### E10US007 — Poste de cible : saisir sans s'identifier
*En tant que* **marqueur** (un archer de la cible, désigné selon FFTA B.6.1.1), *je veux* saisir les scores **sans code ni compte**, *afin de* marquer immédiatement, sans rien avoir à apprendre ni à retenir.
- **CA** : les endpoints de **saisie** sont autorisés par le **jeton de poste** (E04US001) — **aucune authentification d'utilisateur** ; **le contrôle d'accès est physique** : la tablette est fixée à la cible, **qui tape dessus est légitime par construction** ; un poste ne peut saisir que pour **sa** cible (jeton) ; le poste **ne peut pas valider/verrouiller** une série (**scoreur seul**, E04US002 / E10US003) ni configurer ; élargit l'autorisation des endpoints de **saisie** au-delà de l'admin (E10US001).
- **Notes** : ~~« **rôle archer** : saisir ses scores », v0.1~~ → **réécrite le 14/07/2026** ([CDC UX](../cahier-des-charges-ux.md) §5, `D-13`). **Il n'y a pas de rôle archer** : il y a **un poste ouvert**. Le « mécanisme d'accès à préciser » de la v0.1 **est tranché : aucun**. Justification : aucun pouvoir n'est engagé (on saisit, **rien n'est définitif** tant que le scoreur n'a pas validé) — l'identité est donc **le lieu**, pas la personne. **30 postes ouverts plutôt que 30 codes à distribuer et à expliquer à des bénévoles.** Le **marqueur** est **déclaré et tracé à la volée** (E04US002) : *déclaratif ≠ authentifié*. Distinction clé inchangée : **saisie** (poste de cible) vs **validation** (scoreur seul).
- **Arbitrages tranchés le 18/07/2026** (reversés ici — règle 9 ; pour qu'E04US002 n'en dérive pas
  de tests faux), **formalisés dans
  [ADR-0030](../docs/adr/0030-saisie-autorisee-au-poste-de-cible-403-hors-cible.md)** :
  - **« SA cible » = même tournoi *et* même index de cible** — pas l'index seul. Plusieurs tournois
    tournent **en concurrence** (intérieur + extérieur, ADR-0029) et les numéros de cible **se
    répètent** : sans le contrôle du `tournoi_id`, le poste « cible 4 » d'un tournoi voisin saisirait
    pour la cible 4 de celui-ci. Un archer **non placé** n'est sur aucune cible → refusé au poste
    (seul l'admin saisit hors placement).
  - **Poste valide sur la mauvaise cible ⇒ 403, pas 401** : le jeton est établi (identité par le
    *lieu*) mais n'autorise que **sa** cible — « authentifié mais interdit ». C'est le **premier 403**
    du projet (erreur `SaisieHorsCible`). À distinguer du 401 (aucune session) et du 409 (conflit
    d'état). Côté front (E04US002), 401 = re-rattacher le poste ; 403 = ce n'est pas ta cible.
  - **Autorisation « admin OU poste » par une dépendance combinée `autoriser_saisie`**, qui **élargit**
    l'endpoint de saisie existant (l'admin reste autorisé, sans contrainte de cible) — pas de route
    parallèle (patron ADR-0025). L'invariant « SA cible » est vérifié **dans le service** (opération
    atomique de la write-queue, règle 7), non à l'API, pour fermer la fenêtre de course lecture→écriture.
  - **Périmètre : autorisation sans surface front.** La grille de saisie est E04US002 ; ici, un seul
    endpoint (`POST /archers/{id}/scores`, la démo E00US011) est élargi. Pas de `docs/fonctionnel/`
    livré (aucune UI à décrire). La garde « on ne saisit que sur un tournoi **en cours** » relève aussi
    d'E04US002 (`exiger_poste` refuse déjà un tournoi **terminé**, ADR-0029).
- **Dépend de** : E04US001, E10US001 · **Jalon** : J1

---

## Correspondance ancien → nouveau (maille révisée du 17/07/2026)

| Ancienne US | Titre d'origine | Devient |
|---|---|---|
| E10US001 | Consultation publique ouverte | **E10US001** (inchangée, livrée) |
| E10US002 | Accès administrateur protégé | **E10US002** (inchangée, livrée) |
| E10US003 | Session scoreur par code personnel | **E10US003** — CA « session » |
| E10US004 | Habiliter un scoreur sur plusieurs cibles | **E10US004** (inchangée, caduque) |
| E10US005 | Journal d'audit métier | **E10US005** (inchangée) |
| E10US006 | Modifier le mot de passe admin | **E10US006** (inchangée) |
| E10US007 | Poste de cible : saisir sans s'identifier | **E10US007** (inchangée) |
| E10US008 | Définir les scoreurs du tournoi | **E10US003** — CA « gestion des scoreurs » |
