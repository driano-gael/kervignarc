# E10 — Accès & rôles — User Stories

> EPIC : [EPIC-10](../epics/EPIC-10-acces-roles.md) · Réfs : CDC technique §9, ADR-0007.

---

### E10US001 — Consultation publique ouverte
*En tant que* spectateur, *je veux* accéder aux résultats sans compte, *afin de* consulter librement.
- **CA** : toutes les **lectures** (`GET`) sont accessibles sur le LAN **sans authentification** ; **aucune écriture** n'est possible sans session valide (chaque endpoint d'écriture renvoie 401 sans jeton) ; l'UI n'expose aucune action d'écriture au public (formulaires de saisie masqués hors session). Garanti par test.
- **Notes** : les **quatre rôles** sont cadrés (public = lecture ; **archer** = saisir ; **scoreur** = saisir + valider ; **admin** = configurer). Faute de rôles archer/scoreur encore implémentés, les écritures aujourd'hui ouvertes (inscription, placement, saisie de score de la tranche démo) sont **fermées en intérim derrière l'auth admin** ; leurs US de rôle (**E10US007** archer, **E10US003** scoreur, EPIC-02 inscriptions) **élargiront** ensuite l'autorisation endpoint par endpoint (l'admin reste autorisé). Réutilise `exiger_admin` (E10US002).
- **Dépend de** : E00US009, E10US002 · **Jalon** : J1

### E10US002 — Accès administrateur protégé
*En tant qu'*organisateur, *je veux* un accès admin protégé par identifiant + mot de passe, *afin de* sécuriser la configuration.
- **CA** : au **1ᵉʳ accès admin** (aucun identifiant défini), l'app propose de **définir** le login + mot de passe ; ensuite, l'accès aux fonctions admin exige une **connexion** (login + mot de passe) ; une connexion réussie ouvre une session (jeton) jointe aux actions admin ; sans jeton valide, les actions admin sont refusées (401). Périmètre protégé de cette US : **création de tournoi** (config). La **lecture reste publique** (E10US001).
- **Notes** : auth = concern **technique** (application + infrastructure), pas d'entité domaine. Identifiants stockés dans un fichier **`.env` à la racine** (`KERVIGNARC_ADMIN_LOGIN` / `KERVIGNARC_ADMIN_PASSWORD`) — compromis de sécurité **assumé** (appli mono-club LAN) ; ce fichier est aussi la **porte de secours** en cas d'oubli (édition sur la machine serveur → redemandé au prochain accès). Comparaison en temps constant (`hmac.compare_digest`), jeton opaque (`secrets`), lecture/écriture `.env` en **stdlib** (aucune dépendance ajoutée, ADR-0009). Jeton **sans expiration** (l'expiration relève d'E10US003). `.env` **hors versionnage** (`.gitignore`).
- **Dépend de** : E00US009 · **Jalon** : J1

### E10US003 — Session scoreur par code de cible
*En tant que* scoreur, *je veux* ouvrir une session via un code de cible, *afin de* **saisir et valider** les scores sans compte nominatif.
- **CA** : saisie d'un code → session scoreur rattachée à la cible ; jeton simple ; expiration raisonnable. Le scoreur peut **saisir ET valider** les scores de sa/ses cibles (la validation est réservée au scoreur, cf. E04US007) ; il élargit l'autorisation de ces endpoints au-delà de l'admin (E10US001).
- **Dépend de** : E03US001 · **Jalon** : J1

### E10US004 — Habiliter un scoreur sur plusieurs cibles
*En tant que* scoreur, *je veux* couvrir plusieurs cibles, *afin de* gérer un groupe.
- **CA** : une session peut être habilitée sur plusieurs cibles ; validation possible sur chacune ; pas sur les autres.
- **Dépend de** : E10US003 · **Jalon** : J1

### E10US005 — Journal d'audit métier
*En tant qu'*organisateur, *je veux* tracer les actions sensibles, *afin de* gérer les litiges.
- **CA** : `AuditLog` des corrections de score, validations, forfaits (qui/quand/avant-après) ; consultable par l'admin.
- **Dépend de** : E10US002 · **Jalon** : J1

### E10US006 — Modifier le mot de passe admin
*En tant qu'*organisateur connecté, *je veux* changer mon login/mot de passe depuis l'app, *afin de* faire tourner l'accès sans éditer le fichier à la main.
- **CA** : depuis une session admin valide, modifier le login et/ou le mot de passe en fournissant le **mot de passe actuel** ; en cas de succès, `.env` est réécrit et les sessions existantes restent valides (ou sont invalidées — au choix d'implémentation, documenté).
- **Notes** : réutilise le store d'identifiants `.env` d'E10US002 (écriture) ; édition directe de `.env` reste la porte de secours en cas d'oubli. Pas d'entité domaine.
- **Dépend de** : E10US002 · **Jalon** : J4 (confort/robustesse ; déplaçable en J1 si prioritaire)

### E10US007 — Rôle archer : saisir ses scores
*En tant qu'*archer, *je veux* saisir mes scores, *afin de* participer à la marque sans être admin ni scoreur.
- **CA** : un archer peut **saisir** des scores (endpoints de saisie autorisés à ce rôle, en plus de l'admin/scoreur) ; il **ne peut pas valider/verrouiller** une série (réservé au scoreur, E04US007) ni configurer. Mécanisme d'accès à préciser dans l'US (code, tablette partagée par cible, ou nominatif).
- **Notes** : élargit l'autorisation des endpoints de saisie ouverts en intérim par E10US001. Distinction clé : **saisie** (archer *ou* scoreur) vs **validation** (scoreur seul).
- **Dépend de** : E04US005, E10US001 · **Jalon** : J1
