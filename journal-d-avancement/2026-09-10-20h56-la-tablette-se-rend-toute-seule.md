# 10 septembre 2026, 20 h 56 — La tablette se rend toute seule

## Ce qui est nouveau

Quand une cible a fini de tirer, ou quand un duel vient d'être validé, la tablette bascule seule sur
l'écran **« Où tire-t-on ensuite ? »** : chaque archer y lit sa prochaine butte, ou sa place s'il est
sorti. C'était acquis depuis longtemps. Ce qui ne l'était pas, c'est la sortie de cet écran : il
fallait que **quelqu'un** appuie sur « Retour ».

Le jour J, personne n'appuie. L'archer lit sa destination et s'en va. La tablette reste sur l'écran
d'annonce, et le tireur suivant trouve une tablette qui ne sert à rien tant qu'un organisateur ne
passe pas.

Désormais **le panneau se referme tout seul au bout de trois minutes** et rend la tablette à la
saisie. Il prévient qu'il va le faire — une fine barre qui se remplit et la mention « Retour
automatique » —, sans afficher de compte à rebours chiffré : on annonce le départ de l'écran, on ne
demande à personne de surveiller une horloge.

## Ce que ça change

- **Plus de tablette orpheline.** Une butte qui a fini se remet d'aplomb seule, même si l'archer part
  sans rien toucher.
- **En duels aussi**, et c'est le cas le plus fréquent : après chaque duel validé, l'écran repart
  vers la liste des matchs sans geste du scoreur.
- **L'écran se rouvre.** En duels, un lien « Où tire-t-on ensuite ? » apparaît au-dessus de la liste
  et rouvre le panneau du dernier duel validé. La qualification l'avait déjà ; les duels non.

## Le point qui a demandé un arbitrage

Fallait-il **ne pas** refermer l'écran quand il annonce à quelqu'un qu'il est éliminé, pour lui
laisser le temps de lire sa place ?

La réponse est non, et le motif est concret : en élimination directe, il y a un battu à **chaque**
duel, à **tous** les tours. Une règle « on ne referme pas quand c'est fini » n'aurait donc **jamais**
refermé l'écran de duels — la fonctionnalité aurait été livrée sans effet, et rien ne l'aurait
signalé. Et au dernier tour d'un tournoi, toutes les lignes sont terminales : la salle entière serait
restée figée sur ses écrans d'annonce.

Trois minutes suffisent à lire « 3ᵉ du tableau », et le lien de réouverture est là pour le relire.

## Un cas que la revue a rattrapé : l'écriteau

Le même écran ne sert pas qu'à envoyer les gens quelque part. Quand l'organisateur **met une phase
en pause**, il affiche « Tir suspendu — restez à disposition ». Ce n'est pas une annonce qu'on lit et
qu'on emporte : c'est une **consigne**, qui doit rester tant que la pause dure.

Une pause tient quinze à vingt minutes. Le retour automatique l'aurait effacée au bout de trois.

Désormais l'application distingue les deux : une **annonce** se referme, un **écriteau** reste. Cela
vaut aussi pour « phase finale non configurée » et « tableau non constitué ».

## Ce qu'il faut savoir des trois minutes

Elles courent **aussi quand la tablette dort**. Si l'écran se met en veille et qu'on le réveille deux
minutes plus tard, le panneau peut avoir disparu. C'est un choix délibéré — un seul concept plutôt
que deux — et le lien « Où tire-t-on ensuite ? » permet de le rouvrir. À rouvrir comme sujet si un
tournoi réel montre que c'est gênant.

## Au passage : une place ne s'annonce que si elle est acquise

Vérification ajoutée sur un point qui était vrai mais que rien ne protégeait : **l'application
n'annonce jamais une place qu'aucun match n'a décernée**. Petite finale jouée mais finale pas encore
tirée, les deux finalistes ne portent aucun rang — pas même « 1ᵉ-2ᵉ ». Pour un archer sorti plus tôt,
l'écran dit ce qu'il sait : une fourchette (« 5ᵉ-8ᵉ du tableau ») ou son tour de sortie.

Une fiche de recette affirmait par ailleurs encore l'ancien comportement (« rang publié en fin de
phase » pour tout archer sorti avant les demies), remplacé depuis par la fourchette. Elle a été
reprise.

Recette détaillée : [`docs/fonctionnel/E16US018.md`](../docs/fonctionnel/E16US018.md).
