# 23 août 2026, 10h57 — l'application dit ce qui manque **avant** qu'on clique

**Un nouvel écran répond à la question qu'on se pose le matin du tournoi :** *puis-je lancer, et
sinon qu'est-ce qui me manque ?* Il s'appelle « **Prêt à démarrer ?** » et il vit dans le Pilotage,
juste au-dessus de son grand frère « Prêt à terminer ? ».

## Le problème qu'il corrige

L'application savait déjà refuser un démarrage — un tournoi sans créneau, un tournoi qui n'a pas
assez d'inscrits pour le programme composé. Ce qu'elle ne savait pas faire, c'est le dire **à
l'avance**, ni le dire **en entier** :

1. vous cliquez « Marquer prêt » → *refus : ce tournoi n'a aucun départ* ;
2. vous ajoutez un créneau, vous recliquez → *refus : 28 inscrits pour 34 requis*.

Deux allers-retours, alors que l'application connaissait les deux manques dès le départ. Elle ne
répondait qu'à la première objection venue.

Le nouvel écran les affiche **toutes ensemble**, avant le moindre clic, et met en tête la réponse en
une phrase : « **Oui — rien ne s'y oppose** » ou « **Pas encore — ce qui manque ci-dessous sera
refusé au démarrage** ». La liste dit ensuite pourquoi.

Et quand il manque des inscrits, l'écran ne se contente pas du chiffre : il reprend **la phrase
exacte** que vous liriez en cas de refus — quel créneau est concerné, et quelle partie du programme
réclame ces archers. Un tournoi de 48 archers répartis en deux créneaux de 40 et 8 affiche « 8 sur
34 » : sans préciser qu'il s'agit du deuxième créneau, le chiffre paraîtrait faux. C'est le créneau
le moins rempli qui commande, puisque le programme se rejoue entièrement dans chacun.

## Ce qui manque n'est pas toujours ce qui bloque

C'est la distinction que l'écran tient, et elle n'est pas cosmétique. Certains manques **empêchent**
vraiment de lancer (pas de créneau, pas assez d'inscrits) ; d'autres méritent d'être signalés sans
rien interdire — un programme non composé, par exemple : l'application accepte de lancer un tournoi
sans lui, et l'écran ne doit pas prétendre le contraire.

Un écran plus sévère que l'application ferait renoncer un organisateur qui avait le droit de
continuer. C'est pourquoi **aucun bouton n'est jamais grisé** : l'écran vous prévient, il ne vous
verrouille pas. S'il y a un vrai refus, il arrive au clic, comme avant.

Enfin, **un tournoi déjà lancé — ou annulé — n'affiche plus rien à préparer.** L'écran le dit en une
phrase, adaptée au cas : « déjà lancé » pour un tournoi parti, « annulé » pour un tournoi abandonné
avant même d'avoir commencé. Il cesse aussi d'interroger le serveur, ce qui évite d'occuper le réseau
pour une question qui ne se pose plus.

## Une famille, pas un écran de plus

Vous aviez demandé, en relisant les maquettes, quatre écrans de cette sorte : *prêt à démarrer*,
*prêt à terminer*, *prêt à archiver*, *prêt à exporter*. La question restée ouverte était : quatre
écrans distincts, ou une seule forme déclinée ?

**Une seule forme déclinée** — c'est ce qui a été retenu. Concrètement : les quatre écrans partagent
le même squelette, la même façon de poser la question et la même façon de lister ce qui manque. Les
deux membres livrés aujourd'hui (démarrer, terminer) le prouvent déjà : « Prêt à terminer ? » a été
rebâti sur ce squelette commun sans que rien ne change à l'écran.

L'intérêt est de calendrier autant que de cohérence : deux mises à jour à venir — les exports et le
feu vert — s'apprêtaient à inventer chacune sa propre version de « puis-je passer à la suite ». Elles
n'ont plus à le faire.

## Ce que cette mise à jour ne fait pas

**« Prêt à archiver » et « prêt à exporter » ne sont pas livrés.** Leur place est réservée, leur
forme est posée, mais ils n'ont ni rubrique ni contenu. Ils viendront avec leurs propres mises à
jour.

**Il y a toujours deux endroits pour démarrer un tournoi.** La frise du cycle de vie, sur l'accueil
de l'administration, garde ses boutons « Démarrer » et « Terminer ». Les deux fonctionnent et disent
la même chose ; l'un donne le bouton seul, l'autre le bouton expliqué. Les réunir suppose de
retoucher la navigation d'ensemble — ce sera à trancher quand « archiver » rejoindra la famille,
puisque la frise porte aussi ce bouton-là.

**Une question vous reviendra.** Faut-il autoriser le lancement d'un tournoi dont le programme n'a
pas été composé ? Aujourd'hui c'est permis, et l'écran se contente de le signaler. Le changer est une
décision d'organisation, pas un détail technique : elle n'a pas été prise en douce à l'occasion de
cette mise à jour.
