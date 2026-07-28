# ADR-0053 — Outillage de test de rendu front (Testing Library + jsdom)

- **Statut** : Accepté
- **Date** : 2026-07-28
- **Décideurs** : Développeur / Architecte (demande explicite, à la suite d'E14US002)
- **Portée** : outillage de test du front (`frontend/`) ; introduit dans E14US002
- **Complète** : E00US014 (premier runner de test front, Vitest) — cet ADR **étend** cette capacité
  du test de **logique pure** au test de **rendu** de composants
- **Lie** : [ADR-0009](0009-gouvernance-dependances.md) (gouvernance des dépendances — 4 libs dev
  ajoutées), règle 11 (parcimonie)

## Contexte et problème

Jusqu'ici le front ne se testait qu'en **logique pure** : Vitest (E00US014) exécute des fonctions et
des données (27 fichiers de tests), mais **aucun test de rendu** — monter un composant, simuler un
tap, vérifier ce qui s'affiche. La raison était l'**absence d'outillage** : Testing Library exige un
DOM en mémoire (`jsdom`), soit des dépendances supplémentaires, donc un **arbitrage** réservé à
l'utilisateur (règle 11). Plusieurs US front ont donc été livrées avec la note « front sans test de
rendu → vérifier à l'écran » (dont E14US002, dont le composant `AideEcran` est un pur comportement
d'affichage — bouton qui déploie/replie une aide).

À la revue d'E14US002, ce manque a été explicité ; l'utilisateur a **décidé d'outiller** le test de
rendu, sur cette US, pour qu'il serve aux US front suivantes. La décision est **structurante** (une
capacité de test nouvelle, une dépendance d'outillage, une configuration Vitest) → ADR (seuil bas du
projet : ADR-0008 couvre un choix de gestionnaire de paquets).

## Décision

**1. Adopter Testing Library + jsdom** comme socle de test de rendu, en **devDependencies** :

- `@testing-library/react` — monter/interroger un composant **par ce qu'un utilisateur perçoit**
  (rôle, texte accessibles), pas par ses détails d'implémentation ;
- `@testing-library/user-event` — simuler un **vrai geste** (séquence d'événements d'un tap/clic),
  fidèle à l'usage tactile visé ;
- `@testing-library/jest-dom` — matchers DOM lisibles (`toBeVisible`, `toHaveAttribute`…) **et** leur
  typage ;
- `jsdom` — le DOM en mémoire (« faux navigateur ») requis par le rendu.

Toutes **MIT**, `npm audit --audit-level=high` = 0 vulnérabilité. Standard de fait de l'écosystème
React (maintenu, largement adopté) — pas une lib « plaisir » : il n'existe pas d'équivalent « quelques
lignes maison » pour un DOM conforme. Documentées dans [`docs/dependances.md`](../dependances.md).

**2. Environnement `jsdom` global** (`vite.config.ts` › `test.environment`). Les 27 fichiers de tests
de **logique pure** préexistants y tournent **inchangés** (jsdom est un sur-ensemble de
l'environnement Node) : on évite ainsi les docblocks `// @vitest-environment` par fichier et un
fichier de setup au chargement conditionnel. Coût assumé : le démarrage de jsdom ralentit un peu la
suite (mono-club, suite courte — acceptable, règle 12).

**3. Un fichier de setup unique** (`src/test-setup.ts`, `test.setupFiles`) : étend `expect` avec les
matchers jest-dom et **nettoie le DOM après chaque test** (`cleanup()`) — sans quoi un composant
rendu fuiterait d'un test au suivant.

**4. Style aligné sur l'existant** : imports explicites `from 'vitest'` (pas de `globals: true`),
comme les 27 tests déjà en place. Fichiers de test `*.test.tsx` co-localisés avec le composant.

## Conséquences

- **Positif** : les US front à surface visible peuvent désormais **prouver** le comportement de leurs
  composants au lieu de reposer sur une vérification manuelle « à l'écran ». Premier cas :
  `AideEcran.test.tsx` (repli par défaut, déploiement/repli au tap, rien rendu sans texte). La note
  « vérifier à l'écran » reste utile pour l'**intégration visuelle** (mise en page, thème réel), mais
  n'est plus le **seul** filet pour le comportement.
- **Coût / limite** : +4 dépendances dev et +58 paquets transitifs (figés par `package-lock.json`) ;
  suite un peu plus lente (jsdom). Le test de rendu **ne remplace pas** l'œil humain sur le rendu
  réel (jsdom ne peint pas : pas de vraie mise en page ni de vrai tactile) — il couvre la **logique
  d'interaction**, pas l'ergonomie.
- **Rayon d'impact du jsdom global** (relevé en revue) : les 27 tests de logique pure s'exécutent
  désormais **dans jsdom** et non plus dans Node. Conséquence concrète : les stores Zustand `persist`
  y écrivent réellement dans un `localStorage` (inexistant sous Node), et `appliquerTheme` n'est plus
  court-circuité par sa garde SSR `typeof document`. Aucun test n'en change de **sens** (vérifié :
  aucun n'assertait sur l'absence de `window`/`localStorage`), mais pour fermer le **piège dormant**
  (une persistance qui fuirait d'un test au suivant), `src/test-setup.ts` **vide le `localStorage`
  après chaque test** — ce qui rétablit la sémantique d'isolation qu'offrait l'environnement Node.
- **Portée volontairement non rétroactive** : on n'ajoute pas de tests de rendu aux US déjà livrées
  (pas de rattrapage). L'outillage sert **à partir de maintenant** ; chaque US front jugera au cas par
  cas ce qui mérite un test de rendu (règle 12 — pas de test décoratif).
- **La règle 9 côté front s'en trouve renforcée** : un comportement de composant qui mappe un CA
  devient testable ; l'absence de test de rendu sur une US front à comportement non trivial pourra
  être remontée en revue (elle ne l'était pas tant que l'outillage manquait).
