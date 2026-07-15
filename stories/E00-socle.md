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
