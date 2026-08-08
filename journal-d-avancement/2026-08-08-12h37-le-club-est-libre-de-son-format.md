# 8 août 2026, 12 h 37 — le club est enfin libre de son format

**US : E05US024** · [ADR-0080](../docs/adr/0080-un-prelevement-lit-le-classement-de-sa-phase-source.md)

## Ce qui ne marchait pas

En composant le déroulé d'un tournoi, l'organisateur peut écrire des choses comme « cette phase
prend **les huit premiers de mes poules** » ou « ce tableau de consolation prend **les rangs 33 et
suivants du tableau principal** ». L'écran l'acceptait sans broncher, et le diagnostic de déroulé
le déclarait valide.

Mais le moteur, lui, ne savait lire **qu'un seul classement** : celui de la qualification. Tout ce
qui pointait ailleurs était **ignoré en silence**, et la phase récupérait alors *tous* les archers
encore en lice. Résultat : un tableau qui a l'air normal, qui se monte sans erreur, et qui fait tirer
les mauvaises personnes. Le genre de défaut qui ne se découvre que le jour J, une fois les archers
devant les cibles.

## Ce qui change

Chaque prélèvement est désormais lu **dans la phase qu'il désigne**, quelle qu'elle soit — et sur
autant d'étages que le format en compte : une phase peut prendre dans un tableau, qui a lui-même
pris dans les poules, qui ont pris dans la qualification.

Deux conséquences concrètes :

- **Les formats en cascade fonctionnent réellement.** Poules → tableau, tableau → consolante,
  qualification → phase restreinte : ce que l'organisateur compose, la salle le joue.
- **L'avertissement « il vous faut au moins N inscrits » dit la vérité.** Il s'arrêtait à la première
  phase ; il remonte maintenant toute la chaîne. Un déroulé qui demande en réalité 22 inscrits
  l'annonce, au lieu de laisser croire que 2 suffisent — et un format impossible à jouer quel que
  soit le nombre d'archers n'est plus présenté comme un simple manque d'inscrits.

## Ce qui reste à faire

On ne peut **toujours pas** placer deux phases de qualification dans le même tournoi. C'est le sujet
de l'US suivante, et l'ordre n'est pas un choix de confort : sans la lecture livrée aujourd'hui, une
seconde qualification aurait reçu tous les inscrits au lieu de ceux que le format lui destine.

Les autres façons de prélever — « les perdants du tour 2 », « tout le reste » — restent sans effet,
comme avant : elles attendent que leur règle soit tranchée.

## À vérifier à la recette

Composer un déroulé en cascade (par exemple : qualification → tableau des rangs 1 à 16 → petit
tableau des rangs 1 à 4 de ce tableau), le faire jouer, et vérifier que **ce sont bien les vainqueurs
du tableau précédent** qui se retrouvent dans le suivant — et non les mieux classés de la
qualification.
