# Jeu d'essai : remplir un tournoi sans tout saisir à la main

**28 juillet 2026, 13h36 — E15US001 (première brique d'EPIC-15 « jeu d'essai & simulation »)**

## Ce qui est nouveau

Un nouvel écran **« Jeu d'essai »** apparaît dans l'administration (groupe *Préparation*). Il répond à
un retour de la démo du 27/07 : *« pouvoir tester avec des données fake, peupler N inscrits au
hasard, proposer des scénarios prêts »*. Concrètement, deux gestes :

- **Peupler le tournoi courant** : on choisit un nombre (par exemple 30) et l'application ajoute d'un
  clic autant d'archers **factices mais crédibles** — noms et prénoms plausibles, clubs, catégories
  cohérentes. Si le tournoi n'avait pas encore de catégories, le jeu officiel FFTA est ajouté au
  passage.
- **Instancier un scénario** : un petit catalogue propose trois tournois prêts à l'emploi —
  **Petit** (16 archers, un créneau, pour tester vite un tableau de duels), **Gros** (120 archers,
  trois créneaux, pour éprouver le placement), **Multi-format** (60 archers mêlant arc classique,
  poulies et arc nu). Un clic crée un **nouveau tournoi complet** : catégories, créneaux et archers
  déjà **inscrits**, immédiatement **prêt à passer « prêt »** puis à lancer. L'écran bascule alors
  sur l'accueil de ce nouveau tournoi.

## Ce que ça change pour l'organisateur

Plus besoin de saisir des dizaines d'archers à la main pour **montrer** l'application ou **vérifier**
qu'un enchaînement fonctionne. On part d'un tournoi rempli en quelques secondes.

Un champ **« graine »** (un simple nombre) permet de **rejouer exactement le même jeu** : la même
graine produit les mêmes archers. Utile pour reproduire une situation ou comparer deux essais.

## À garder en tête

Ce sont de **vraies données**, enregistrées comme une saisie normale — c'est pourquoi l'outil est à
**réserver aux tournois de test**. La *simulation* qui **joue** un tournoi (scores automatiques) sans
rien enregistrer, elle, viendra dans les briques suivantes d'EPIC-15. Les textes des scénarios et de
l'aide sont un **premier jet**, à ajuster avec l'organisateur.
