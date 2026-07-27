# EPIC-15 — Jeu d'essai & simulation

- **ID** : EPIC-15
- **Statut** : À planifier
- **Priorité** : MVP+1 *(retours de la démo au client final, 27/07/2026 — outil de démo & de QA)*
- **Dépend de** : EPIC-02 (inscriptions), EPIC-05 (moteur de phases), EPIC-06 (classements)
- **Réfs** : **ADR à créer** « Exécution éphémère du moteur sur adaptateurs in-memory des ports » ; règles **1** (domaine pur, politiques injectables) & **7** (single-writer) du projet

## Objectif / valeur
Pouvoir **démontrer et tester** l'appli sans saisie manuelle : peupler des inscrits, charger des
scénarios, et **rejouer un tournoi entier** (qualif → duels → classement) avec un bot, en observant
chaque rôle (cible, archer, scoreur, public). Un même outillage sert la **démo** (raconter le déroulé au
client) et la **QA** (vérifier que tout s'enchaîne). Retours de la démo du 27/07/2026 : « tester avec des
données fake », « peupler N inscrits au hasard », « proposer des scénarios visibles sur le front »,
« depuis l'admin, vérifier la création et le déroulé — arbre + phases, simuler le tour de chaque joueur,
simuler les tablettes cible/archer/scoreur/public ».

## Périmètre
### Inclus
- **Jeu d'essai persistant** : génération d'inscrits réalistes + scénarios rejouables (E15US001).
- **Simulation éphémère** : rejouer le moteur **sans rien persister**, sur tout tournoi **non démarré** (E15US002).
- **Bot pausable + cockpit interactif** multi-vues avec reprise en main (E15US003).

### Exclus
- Toute **persistance** du déroulé simulé — contrainte forte : la simulation ne pollue **jamais** le réel.
- Simuler un tournoi **déjà démarré** (garde-fou).

## Capacités
- [ ] Générateur d'inscrits + scénarios (E15US001).
- [ ] Moteur de simulation éphémère + garde-fou (E15US002).
- [ ] Bot pilote auto pausable + cockpit interactif (E15US003).

## Critères d'acceptation (epic)
- Une simulation lancée sur un tournoi brouillon peuplé se déroule jusqu'au classement, se met en
  **pause**, accepte une **saisie manuelle**, reprend — et **ne laisse aucune trace** dans les données réelles.
- Lancer une simulation sur un tournoi **démarré** est **refusé**.

## Risques
- **Périmètre des ports in-memory** inconnu tant que le **spike** (E15US002) n'a pas tracé
  qualif → duels → classement → risque de sous-estimation ; d'où le spike en tête d'US.
- **Dérive** entre repos in-memory et repos SQL → tests de conformité de port partagés (anti-dérive).
- **Option « transaction rollback » écartée** : violerait la règle 7 (transaction longue monopolise le
  writer unique). Retenue : services applicatifs câblés sur des **repos in-memory** hors file d'écriture.
