# 8 août 2026, 12 h 37 — le club est enfin libre de son format

**US : E05US024** · [ADR-0080](../docs/adr/0080-un-prelevement-lit-le-classement-de-sa-phase-source.md)
· [ADR-0081](../docs/adr/0081-une-phase-attend-que-sa-source-ait-departage-les-places-qu-elle-preleve.md)

## Ce qui ne marchait pas

En composant le déroulé d'un tournoi, l'organisateur peut écrire des choses comme « cette phase
prend **les rangs 5 à 8 du tableau principal** » — autrement dit, les battus des quarts de finale.
L'écran l'acceptait sans broncher, et le diagnostic de déroulé le déclarait valide.

Mais le moteur, lui, ne savait lire **qu'un seul classement** : celui de la qualification. Tout ce
qui pointait ailleurs était **ignoré en silence**, et la phase récupérait alors *tous* les archers
encore en lice. Résultat : un tableau qui a l'air normal, qui se monte sans erreur, et qui fait tirer
les mauvaises personnes. Le genre de défaut qui ne se découvre que le jour J, une fois les archers
devant les cibles.

## Ce qui change

Chaque prélèvement est désormais lu **dans la phase qu'il désigne** — et sur autant d'étages que le
format en compte : une consolante peut prendre dans un tableau, qui a lui-même pris dans la
qualification.

Trois conséquences concrètes :

- **Les formats en cascade fonctionnent réellement.** Tableau → consolante, tableau → tableau : ce
  que l'organisateur compose, la salle le joue. Et le palmarès situe chacun à sa vraie place — le
  vainqueur d'une consolation qui dispute les places 33 et suivantes est annoncé 33ᵉ, pas 1ᵉʳ.
- **Ce qui n'est pas encore joué est annoncé comme tel.** Si la consolante est composée le matin,
  personne ne sait encore qui seront « les rangs 5 à 8 » : les quarts ne sont pas tirés. L'écran
  public l'écrit — « les places disputées ici ne sont pas encore connues » — au lieu d'inventer une
  liste d'archers plausible et fausse. C'est le défaut le plus dangereux qu'ait trouvé la relecture
  de cette US : le tableau affiché avait le bon nombre d'archers, avec des noms crédibles.
- **L'avertissement « il vous faut au moins N inscrits » dit la vérité.** Il s'arrêtait à la première
  phase ; il remonte maintenant toute la chaîne. Un déroulé qui demande en réalité 22 inscrits
  l'annonce, au lieu de laisser croire que 2 suffisent — et un format impossible à jouer quel que
  soit le nombre d'archers n'est plus présenté comme un simple manque d'inscrits.

## Ce qui reste à faire

Une phase qui prend ses archers dans des **poules**, un système suisse, une colline ou un Big Shoot
Off reste ignorée comme avant : ces formats n'ont pas encore de moteur, et c'est une tranche à part
(E05US023).

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
