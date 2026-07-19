# E00 — Socle technique & walking skeleton — User Stories

> EPIC : [EPIC-00](../epics/EPIC-00-socle-technique.md) · Jalon J0 · Réfs : `guide-architecture.md`, ADR-0002/0003/0005.

---

### E00US001 — Initialiser le monorepo + gestionnaires
*En tant que* développeur, *je veux* un dépôt structuré `backend/` + `frontend/` avec l'outillage, *afin de* démarrer sur des bases saines.
- **CA** : `uv` gère l'environnement Python ; `pnpm`+`Vite` initialisent le front ; `README` de démarrage ; versions figées.
- **Notes** : arborescence conforme au `guide-architecture.md` §3.
- **Dépend de** : —

### E00US002 — Configurer la qualité
*En tant que* développeur, *je veux* lint/format/typage automatiques, *afin de* garantir la qualité dès le 1er commit.
- **CA** : ruff (lint+format) + mypy strict côté Python ; ESLint + Prettier + TS strict côté front ; hooks **pre-commit** actifs.
- **Notes** : configs partagées et versionnées.
- **Dépend de** : E00US001

### E00US003 — CI bloquante
*En tant que* équipe, *je veux* une CI qui bloque le merge si la qualité échoue, *afin de* protéger la branche principale.
- **CA** : pipeline exécutant lint + typage + tests ; merge impossible si rouge.
- **Notes** : rapide (< quelques min) pour ne pas freiner.
- **Dépend de** : E00US002

### E00US004 — Squelette de couches + garde-fou d'imports
*En tant que* développeur, *je veux* les couches `domain/application/infrastructure/api` posées, *afin de* respecter l'hexagonal.
- **CA** : les 4 couches existent ; une règle (lint d'imports) **échoue** si `domain/` importe un framework ou une couche externe.
- **Notes** : cf. ADR-0003 ; test automatisé de la règle de dépendance.
- **Dépend de** : E00US001

### E00US005 — Composition root minimale
*En tant que* développeur, *je veux* un point de câblage explicite, *afin de* voir toutes les dépendances en un endroit.
- **CA** : `bootstrap/` assemble adapters + services ; aucun conteneur DI ; `main.py` démarre via le bootstrap.
- **Dépend de** : E00US004

### E00US006 — Connexion SQLite (WAL) + migration initiale
*En tant que* développeur, *je veux* la base opérationnelle en WAL avec migrations, *afin de* persister les données.
- **CA** : base créée en mode **WAL** ; **Alembic** applique une migration initiale ; connexion via un adapter d'infrastructure.
- **Notes** : cf. ADR-0005.
- **Dépend de** : E00US005

### E00US007 — File d'écriture + writer unique
*En tant que* système, *je veux* sérialiser les écritures via une file, *afin d'*éviter les `database is locked`.
- **CA** : une commande d'écriture est mise en file et exécutée par **un seul worker** ; l'appelant obtient le résultat (future) ; les lectures restent concurrentes.
- **Notes** : point de passage unique pour audit + diffusion (ADR-0005).
- **Dépend de** : E00US006

### E00US008 — Canal WebSocket + diffusion post-commit
*En tant que* client, *je veux* recevoir les mises à jour en direct, *afin de* voir l'état sans rafraîchir.
- **CA** : un client peut s'abonner ; après commit d'une écriture, un événement est diffusé aux abonnés.
- **Notes** : diffusion déclenchée depuis le writer unique.
- **Dépend de** : E00US007

### E00US009 — Repository + endpoint de bout en bout
*En tant que* développeur, *je veux* un aller-retour complet API↔domaine↔DB, *afin de* valider le patron.
- **CA** : un agrégat trivial est créé via un endpoint (DTO Pydantic), persisté par un repository (port/adapter), relu ; erreurs typées mappées à la frontière.
- **Notes** : sert de gabarit pour les US métier ; cf. ADR-0007.
- **Dépend de** : E00US007

### E00US010 — Shell React
*En tant que* utilisateur, *je veux* une app front qui charge et se connecte, *afin d'*interagir.
- **CA** : shell React+TS ; **React Query** configuré (fetch/cache) ; **Zustand** pour l'état UI ; client **WebSocket** branché ; organisation par features.
- **Dépend de** : E00US009

### E00US011 — Tranche verticale démontrable
*En tant que* PO, *je veux* une démo bout-en-bout, *afin de* valider l'architecture tôt.
- **CA** : créer un tournoi → ajouter 1 archer → le placer sur 1 cible → saisir 1 score → **voir un classement se mettre à jour en live**.
- **Notes** : versions minimales, jetables/évolutives ; sert de fil rouge pour J1.
- **Dépend de** : E00US010

### E00US012 — Exécutable de dev
*En tant que* équipe, *je veux* lancer l'app en un binaire, *afin de* préparer le packaging.
- **CA** : FastAPI sert le **build front** en statique ; un exécutable de dev démarre le tout ; port fixe.
- **Notes** : base d'EPIC-11 (packaging complet PyInstaller).
- **Dépend de** : E00US011

### E00US014 — Outiller les tests du front
*En tant que* développeur, *je veux* pouvoir **tester la logique du front**, *afin qu'*une régression sur un calcul d'argent ne parte pas en production sans un signal.
- **Contexte** : **[DETTE-005](../docs/dette.md)** — le front n'a **aucun runner** (`package.json` : ni `vitest`, ni script `test`) ; E00US002 n'a outillé que lint/format/types. Tant que le front ne faisait que du rendu, `tsc` + ESLint suffisaient. E01US010 y a introduit la **conversion euros ↔ centimes** ([ADR-0012](../docs/adr/0012-argent-en-centimes-entiers.md)), seule logique arithmétique du front — et elle décide de ce que paiera un archer (EF-8.1).
- **CA** : un runner installé (**vitest**, déjà transitif via Vite) + script `npm test` ; **branché sur la CI bloquante** (E00US003) au même titre que lint/types ; dépendance déclarée dans `package.json` **et** documentée dans [`dependances.md`](../docs/dependances.md) (ADR-0009) ; `format.ts` couvert — `0`, `« 8 »`, `« 8,1 »` → 810, `« 0,05 »` → 5, point vs virgule, rejets (`8,105`, `-8`, `huit`, `8,`), **stabilité de l'aller-retour** ; marqueur `DETTE-005` retiré et ligne déplacée en « Dette résorbée ».
- **Notes** : ⚠️ **à faire avant E08US001**, qui consommera le tarif pour calculer les montants dus. Le vrai risque de l'US est le **lockfile** : `npm ci` a déjà cassé la CI front sur une résolution `@emnapi` — revalider `npm ci` **localement** après l'ajout, et figer par `overrides` si besoin. Ne pas viser une couverture du rendu (pas de testing-library dans cette US) : le besoin prouvé est la **logique pure**.
- **Dépend de** : E00US002, E00US003 · **Jalon** : J1 *(dette — avant E08US001)*

### E00US013 — Factoriser les briques d'UI partagées du front
*En tant que* développeur, *je veux* que l'affichage d'une erreur ait **un seul point de vérité**, *afin qu'*un changement de rendu (couleur, ton, accessibilité) se fasse une fois et non dix.
- **Contexte** : **[DETTE-004](../docs/dette.md)** — `MessageErreur` est copié **à l'identique** dans 10 features (`admin`, `archers`, `bareme`, `blasons`, `categories`, `clubs`, `competition`, `gabarits` ×2, `grain-validation`) : même signature, même corps, mêmes classes, même `role="alert"`. **Tenir le compte à jour ici** : la liste est le CA, et une liste périmée fait cocher « zéro copie restante » à qui en laisse deux.
- **CA** : `MessageErreur` vit dans `frontend/src/shared/ui/` ; **les 10 copies locales** le consomment, **zéro restante** ; le rendu est **inchangé** à l'écran (mêmes classes, même `role="alert"`) ; marqueurs `DETTE-004` retirés et ligne déplacée en « Dette résorbée ». **Les 8 autres `role="alert"` du front sont examinés et tranchés explicitement** (repris ou laissés, mais pas oubliés) :
  - **4 blocs de confirmation** — ton **neutre**, pas de `--erreur`, une action : `competition/TrancheVerticale.tsx` (« Inscrire quand même ») et `archers/Archers.tsx` ×3 (« Enregistrer quand même », « Changer quand même de catégorie », « Supprimer définitivement, avec ses résultats » — ce dernier en `--danger`, sa confirmation détruit, [ADR-0016](../docs/adr/0016-supprimer-un-archer-engage-plutot-que-le-refuser.md)). **Ce sont eux le vrai enjeu** : n'ayant pas `--erreur`, un token posé sur cette classe ne les atteint pas, et un `grep MessageErreur` ne les trouve pas ;
  - **4 rendus d'erreur ad hoc** portant déjà `carte__etat--erreur` : `admin/ConnexionAdmin.tsx` ×2 (« Accès admin injoignable », « Les deux mots de passe ne correspondent pas »), `competition/TrancheVerticale.tsx` ×2 (« Montant en euros attendu », « Classement injoignable »). Un token CSS les atteint ; une refonte du **balisage** non.
  > **Compte de référence, à recompter plutôt qu'à croire** : `grep -rcn 'role="alert"' frontend/src --include=*.tsx` → **18** = 10 copies + 8 ci-dessus. Ce décompte a déjà été faux **deux fois** (à 9→10 features, puis à 3→4 blocs) : recompter avant de cocher, ne pas recopier ce nombre.
- **Notes** : refactor **mécanique et d'un bloc**, pour que la revue porte sur l'équivalence du rendu. Placée **juste avant E01US016** (identité visuelle) et le thème sombre, qui consommeront les tokens de couleur — l'alerte doit être **ambre** (`DV-03`), et ce token ne doit s'appliquer qu'à **un** endroit. ⚠️ Le front n'a **aucun test** : vérifier à l'écran (au moins la connexion admin et une erreur de saisie).
- **Dépend de** : E00US011 · **Jalon** : J3 *(dette — résorbée là où elle commence à coûter)*

### E00US015 — Ossature de navigation de l'appli admin (coquille)
*En tant qu'* organisateur, *je veux* naviguer entre les fonctions d'administration par une **barre de navigation latérale** qui n'affiche qu'un écran à la fois, *afin de* ne plus subir une page unique où toutes les fonctions sont empilées en colonne.
- **Contexte** : le front admin est aujourd'hui **monolithique** — `frontend/src/features/competition/TrancheVerticale.tsx` empile ~14 sections dans une seule carte, gardées par `estAdmin`, **sans aucune navigation** (pas de routeur, pas de menu, tout se voit en scrollant). Deux fonctions sont même **enfouies** dans ce fichier au lieu d'être des features : l'**inscription d'un archer** (`InscriptionArcher`) et la **gestion des tournois** (`GestionTournois`, formulaires de création/édition, `CycleDeVie`). Le découpage **logique** par features existe déjà (un dossier par domaine sous `features/`) ; ce qui manque, c'est la **coquille** qui les répartit sur des écrans distincts.
- **CA — navigation** : une **sidebar** liste les destinations d'administration **groupées par temps du tournoi** (Préparation / Jour J / Après — [CDC UX §7.1](../cahier-des-charges-ux.md), `D-19`) ; un clic affiche **une seule destination** dans la zone principale ; **toutes** les destinations restent accessibles en permanence (`P-3`, replié ≠ interdit) ; le **sélecteur de tournoi** coiffe la navigation — tout ce qui est en dessous lui appartient.
- **CA — accueil contextualisé** (`D-20`) : l'écran affiché **par défaut** dépend du **statut** du tournoi (brouillon → préparation ; en cours → supervision ; terminé → résultats). C'est une **priorité d'affichage, pas une restriction** — les autres destinations restent à un clic.
- **CA — découpage propre** : chaque fonction d'administration est une **feature autonome** (`features/<domaine>/` : composant + `api.ts` + `hooks.ts`), branchée dans la coquille par **une seule entrée** ; **aucune** fonction n'est enfouie dans le fichier d'une autre (règle [`guide-architecture.md`](../guide-architecture.md) §8). Les deux fonctions embarquées dans `TrancheVerticale.tsx` — **inscription archer** et **gestion tournois** — sont **extraites** en features dédiées.
- **CA — l'état backend n'est pas un écran** : l'écran de diagnostic redondant (`features/systeme/EtatBackend.tsx`) est **retiré** ; l'état de connexion reste porté par la **pastille** de l'en-tête (`IndicateurConnexion`) — un voyant permanent, pas une destination.
- **CA — non-régression** : toutes les fonctions admin livrées (cycle de vie, départs, catégories, blasons, gabarits, clubs, barème, grain de validation, scoreurs, inscription, archers, placement, classement) restent **accessibles et fonctionnelles** ; aucune perte de comportement.
- **Notes** : réalise l'ossature admin du [CDC UX §7.1](../cahier-des-charges-ux.md) (`D-19`, `D-20`) et **solde le front monolithique**. **Navigation par état local `useState`** (pas de `react-router`) — arbitrage du 18/07/2026, acté en [ADR-0032](../docs/adr/0032-navigation-admin-par-etat-local.md) : le périmètre (≈ 16 destinations, réseau local, pas de deep-link ni d'URL partagée) ne justifie pas la dépendance (règle 11) ; à réévaluer si un vrai besoin d'URL apparaît (conséquence actée : l'état de navigation est perdu au rechargement). Le **repli en icônes** (56 px, `D-19`) réservé au plan de salle et à l'arbre de duels est **hors** de cette US. **Pattern liste/fiche** et **listes déroulantes / multisélection** des référentiels = évolution UX **séparée** (US dédiée, après la coquille), pour ne pas gonfler celle-ci. ⚠️ Le front n'a **pas de tests de rendu** : vérifier **à l'écran** que chaque destination s'ouvre et que les deux features extraites fonctionnent.
- **Arbitrages de périmètre tranchés à l'implémentation (19/07/2026), reversés ici (règle 9)** : la coquille ne matérialise **que les destinations livrées** — seuls les temps **Préparation** et **Jour J** portent des entrées ; **Après** (Podiums, Paiements, Exports, Archive, Audit) et les destinations §7.1 non encore construites (Identité, Supervision, Complétude, Validation, recherche) **n'apparaissent pas** — elles viendront avec leur US, pas en entrées vides. L'accueil contextualisé s'appuie sur les **3 statuts actuels** (les 7 d'ADR-0026 sont E01US017, non livrés) : `brouillon → « Tournoi »` ; `en_cours`/`termine → « Classement en direct »` — seul écran de suivi livré, **stand-in** de « Supervision » et « Résultats » tant que ces écrans n'existent pas. Le saut à l'accueil contextualisé se fait **au changement de tournoi**, pas à chaque changement de statut (démarrer un tournoi n'arrache pas l'admin de son écran — `P-3`). Les entrées de **rôle** (scoreur, lien poste) restent sur l'**accueil public** (hors coquille admin) : elles s'adressent à d'autres tablettes, pas au poste de l'organisateur.
- **Dépend de** : E00US011 · **Jalon** : J3 *(structure front — tirée en priorité « US suivante » à la demande de l'organisateur, 18/07/2026)*

### E00US016 — Écrans d'administration : liste → fiche & référentiels en déroulante
*En tant qu'*organisateur, *je veux* gérer chaque entité par un **tableau (liste) → fiche d'édition** et choisir les valeurs de référence dans des **listes déroulantes**, *afin de* saisir vite et sans erreur, sur des écrans propres.
- **Contexte** : après la coquille (E00US015), les écrans d'administration passent du **formulaire empilé** à un pattern **liste/fiche** homogène. Remontées du 18/07/2026. Évolution **UX transverse**, séparée de la coquille pour ne pas la gonfler.
- **CA — liste/fiche** : chaque entité du tournoi (tournois, catégories, blasons, gabarits, clubs, départs, scoreurs, archers) se gère par un **tableau** — colonnes utiles, dont l'**état** quand il existe (ex. statut du tournoi) — et une **fiche** d'édition ; on entre en édition **depuis une ligne**.
- **CA — référentiels en déroulante** : les valeurs de référence (catégories FFTA, tranches d'âge, blasons, clubs…) sont proposées en **liste déroulante** ; les champs **multivalués** (ex. catégorie ↔ **plusieurs** tranches d'âge, E01US013) se saisissent par **cases à cocher** (multisélection), jamais en texte libre.
- **CA — fractions de blason en déroulante** (remontée B3) : la **taille** d'un blason se choisit dans une déroulante **{cible entière (1), demi (½), tiers (⅓), quart (¼)}**, avec une option « Autre… » **repliée** pour un réel libre ; le back **garde le modèle fraction** (aucun changement de domaine).
- **Notes** : présentation uniquement — **aucun changement de domaine/API** attendu (au plus un confort de tri). ⚠️ Front sans tests de rendu : vérifier **à l'écran**. Découpage plus fin possible **par entité** à la planification si l'US est trop large pour une branche.
- **Dépend de** : E00US015 · **Jalon** : J3
