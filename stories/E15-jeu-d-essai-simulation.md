# EPIC-15 — Jeu d'essai & simulation — User Stories

> Issu des **retours de la démo au client final du 27/07/2026**. Un même outillage sert la **démo**
> (raconter le déroulé) et la **QA** (vérifier que tout s'enchaîne). Voir
> [`epics/EPIC-15`](../epics/EPIC-15-jeu-d-essai-simulation.md).
>
> **Contrainte centrale** (arbitrée avec l'organisateur) : la simulation est jouable sur **n'importe
> quel tournoi créé** (tout format) **sauf un tournoi démarré** (garde-fou), et **ne persiste rien** qui
> polluerait le réel — le déroulé joué par le bot est **éphémère**.
>
> ⚠️ **Stubs** : CA fin à préciser au cadrage ; E15US002 démarre par un **spike** (périmètre des ports).

### E15US001 — Jeu d'essai : générer des inscrits + scénarios rejouables
*En tant qu'*organisateur/testeur, *je veux* peupler un tournoi de test avec des inscrits réalistes et charger des scénarios prêts, *afin de* démontrer et tester l'appli sans saisir des données à la main.
- **Contexte** : retours de la démo du 27/07/2026 (« tester avec des données fake », « peupler N inscrits au hasard », « proposer des scénarios visibles sur le front »).
- **CA — générateur d'inscrits** : depuis un tournoi **créé exprès**, un bouton peuple **N archers aléatoires plausibles** (noms, clubs, catégories FFTA cohérentes) ; ce sont des **données réelles persistées** — c'est un tournoi de test qu'on assume comme tel.
- **CA — scénarios rejouables** : un **catalogue** de scénarios (petit tournoi, gros tournoi, multi-format) est **sélectionnable depuis le front** et instancie un tournoi + ses inscrits.
- **Notes** : écrit de la **donnée réelle** (via la file d'écriture) — **à distinguer** de la simulation éphémère (E15US002), qui ne persiste rien. Liste exacte des scénarios à **figer au cadrage**. Génération **déterministe** (graine explicite — pas d'aléa non maîtrisé, règle 9). US à **surface visible** → doc fonctionnelle + journal d'avancement.
- **Notes (arbitrages du cadrage, 28/07/2026)** :
  - **Catalogue figé à trois scénarios** (choix organisateur) : **petit** (16 archers, 1 départ, arc classique sénior — un tableau de duels jouable tout de suite), **gros** (120 archers, 3 départs, arc classique — charge du placement), **multi-format** (60 archers, 2 départs, les trois divisions — cohabitation des formats). Chaque scénario est **prêt à lancer** : il crée un tournoi brouillon complet (catégories FFTA pré-chargées + départs + archers **inscrits**), qui peut ensuite passer `prêt` (garde `TournoiSansDepart`, E02US010).
  - **Deux briques** : (1) un bouton « **peupler N archers** » sur le **tournoi courant** (N réglable, borné [1, 500]) ; (2) le **catalogue** qui crée son propre tournoi. Regroupées sur une **destination admin « Jeu d'essai »** dédiée (coquille, groupe Préparation).
  - **Graine** exposée en **champ optionnel** (défaut stable) — le même jeu se rejoue à l'identique (règle 9).
  - **Réutilisation des services** (pas de court-circuit du domaine) : `ServiceJeuEssai` compose `ServiceTournois`/`ServiceCategories`/`ServiceDeparts`/`ServiceArchers`/`ServiceInscriptions`/`ServiceClubs`. Tout tient dans **une** commande de file (patron `precharger_ffta`). **Pas d'ADR** : outillage réutilisant l'existant, sans nouveau pattern (règle 12) ; le déterminisme suit la convention règle 9 (générateur injecté). Textes d'écran = **1ᵉʳ jet** (aide contextuelle E14US002 mise à jour). Clubs générés = **référentiel global** enrichi (réutilise un club de même nom, ADR-0014).
  - **Garde-fou de statut sur « peupler »** (arbitrage tranché en revue, 28/07) : peupler écrit de la donnée réelle → **refusé sur un tournoi déjà démarré** (`en_cours`/`en_pause`/`terminé`/`archivé`) via `PeuplementTournoiDemarre` (409). Seuls `brouillon`/`prêt` sont peuplables — cohérent avec l'invariant d'EPIC-15 (« ne pollue jamais le réel ») et le garde-fou d'E15US002. L'**instanciation** d'un scénario n'est jamais bornée (elle crée un tournoi `brouillon` neuf).
- **Dépend de** : E02US002, E02US009 · **Jalon** : J3 · **Origine** : démo 27/07/2026

### E15US002 — Moteur de simulation éphémère + garde-fou (non-persistance)
*En tant que* système, *je veux* rejouer le moteur (qualif → duels → classement) d'un tournoi **non démarré** **sans rien persister**, *afin d'*alimenter la simulation de démo/QA sans polluer les données réelles.
- **Contexte** : retours de la démo du 27/07/2026. La simulation doit tourner sur **n'importe quel tournoi créé** (tout format), **sauf un tournoi démarré** (garde-fou), et **ne rien écrire** qui pollue le réel.
- **CA — exécution éphémère** : le moteur est rejoué sur un **jeu de repositories in-memory** (implémentant les ports `domain/ports.py`), **hydraté** depuis le tournoi choisi ; **aucune écriture** n'atteint SQLite ni la file d'écriture réelle.
- **CA — garde-fou** : lancer une simulation sur un tournoi **démarré** (`en_cours`/`en_pause` et au-delà) est **refusé** ; seuls les tournois **avant démarrage** (`brouillon`/`prêt`) sont simulables. *(Arbitrage tranché en cours d'US, 28/07 : un tournoi `terminé`/`archivé`/`annulé` **n'est pas** simulable — avant démarrage uniquement, cohérent avec l'invariant d'épic et `PeuplementTournoiDemarre` d'E15US001. Garde-fou `SimulationTournoiDemarre` → 409.)*
- **CA — non-pollution vérifiable** : après une simulation, la base du tournoi réel est **inchangée** (test d'invariant).
- **Notes** : **cœur technique** — **Option A** du plan (services applicatifs câblés sur des repos in-memory ; hors `write_queue`), **confirmée par le spike** (aucun service du moteur ne touche SQLite ni la file). **Spike en tête d'US** pour tracer les ports à couvrir (qualif → duels → classement : `ServiceClassement`, `ServicePlacementDuels`, `ServiceSaisieDuels`) + **no-op d'audit** (`enregistrer_avec_trace`/`declarer_avec_trace` ignorent la trace). **[ADR-0054](../docs/adr/0054-execution-ephemere-du-moteur-sur-adapters-in-memory.md) créé**. Tests domaine/service depuis les CA (règle 9) ; **oracle 120 reste vert** ; tests de conformité de port partagés (anti-dérive). **Sans surface visible directe** (couche moteur/infra).
  - **Arbitrages tranchés en cours d'US (28/07, doute technique → tranché, documenté, signalé après coup)** :
    - **Adapters in-memory en production** (`infrastructure/memory/`), **pas** de réutilisation des `Faux*Repository` des tests : le code de prod ne peut pas importer `tests/` (règle 1/2), et l'inverse (promotion des doublures) est un refactor transverse à traiter en US dédiée (règle 12). D'où l'**anti-dérive par tests de conformité de port partagés** (mêmes assertions SQL ↔ in-memory), pas par code partagé.
    - **`ServiceSimulation` (application) n'importe aucun adapter** : la composition root lui injecte une **usine de harnais** (règle 8) — aucune application n'importe `infrastructure/` dans le projet, on garde la convention. Le service **hydrate** par les ports (identifiants préservés) ; duels/plans/forfaits **non hydratés** (vides avant démarrage, garantis par le garde-fou).
    - **Pas d'API ni d'UI** dans cette US : les 3 CA se vérifient au niveau service. L'entrée (bot + cockpit + **canal de diffusion isolé**) est **E15US003** ; l'ADR pose le principe de non-diffusion (ne pas soumettre à la file suffit).
    - **Périmètre borné** (11 ports) : **pas de redécoupage** nécessaire.
- **Dépend de** : E05US003, E05US005, E06US001 · **Jalon** : J3 · **Origine** : démo 27/07/2026

### E15US003 — Bot pilote automatique pausable + cockpit interactif multi-vues
*En tant qu'*organisateur/testeur, *je veux* un bot qui fait avancer le tournoi simulé tout seul (que je peux mettre en pause) et un cockpit pour voir et piloter chaque rôle, *afin de* vérifier le déroulé et le démontrer.
- **Contexte** : retours de la démo du 27/07/2026 (« simuler le tour de chaque joueur », « simuler les tablettes cible/archer/scoreur/public », « un mode simulé avec une navbar pour switcher d'écran »).
- **CA — bot pausable** : un bot **génère des scores plausibles** et fait avancer la simulation (qualif → duels → classement) en **pilote automatique** ; il est **pausable** à tout moment, puis **reprend**.
- **CA — cockpit interactif** : une **navbar** bascule entre les vues **cible / archer / scoreur / public** de la simulation ; **en pause**, l'humain peut **saisir à la place d'un rôle** (comme un vrai appareil), puis **rendre la main** au bot.
- **CA — diffusion isolée** : l'état simulé est diffusé au front sur un **canal séparé** du flux temps réel réel (post-commit).
- **Notes** : couche **pilotage + UI** par-dessus E15US002. La génération de scores plausibles est une **stratégie injectable** (règle 1) — éventuel **ADR** « Politiques de génération de scores plausibles du bot ». Génération **déterministe** (graine). ⚠️ Front sans tests de rendu → vérifier **à l'écran**. US à **surface visible** → doc fonctionnelle + journal d'avancement.
- **Dépend de** : E15US002, E15US001 · **Jalon** : J3 · **Origine** : démo 27/07/2026
