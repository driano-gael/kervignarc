# La salle peut s'arrêter — et repartir d'un bouton

**19 août 2026, 11 h 39** · `E05US033`

## Ce qui manquait

Une phase de tournoi en salle peut durer des heures. Jusqu'ici, elle enchaînait ses tours toute seule
jusqu'au bout : pour couper — le repas, une réorganisation de la salle, une annonce au micro —, il n'y
avait aucun geste prévu. L'organisateur pouvait interrompre le tournoi entier, ou rien.

## Ce que ça change

L'organisateur **prépare son planning de journée à l'atelier**, au moment où il compose son déroulé :
« pause après le tour 2, pause après le tour 5 », autant qu'il en veut, sur chaque phase. Chaque pause
porte une portée : *cette phase seule*, ou *tout le créneau*.

Le moment venu, la salle s'arrête **d'elle-même**. Les archers concernés lisent « en attente » sur leur
tablette au lieu de recevoir une cible. Un administrateur relance **d'un seul bouton** — qui rend d'un
coup toutes les phases qu'une même pause avait coupées, sans qu'il ait à les retrouver une par une.
Ensuite, tout repart en automatique jusqu'à la pause suivante.

Conséquence utile : piloter la salle tour par tour redevient possible sans mode spécial. Il suffit de
programmer une pause à chaque tour.

## Trois points à connaître

**Une pause de créneau ne coupe personne en plein tir.** Chaque phase finit d'abord le tour qu'elle a
en cours : la salle s'éteint en quelques minutes plutôt que d'un coup. Personne ne se retrouve l'arc
levé parce que la pause est tombée au mauvais moment.

**Corriger un score reste possible pendant la pause.** C'est justement le moment où l'on relit les
feuilles et où l'on découvre un 9 pris pour un 10. L'interdire aurait obligé à relancer toute la salle
pour rectifier une flèche, puis à l'arrêter de nouveau.

**Une phase sans pause programmée se comporte exactement comme avant.** Rien ne change pour un tournoi
qui n'en veut pas — c'est ce qui rend la nouveauté sans risque.

Au passage, une qualification peut être **découpée en tours** (« 20 volées en 2 tours de 10 »), ce qui
lui permet d'accueillir une pause en cours de route. Sans ce réglage, une qualification ne compte qu'un
seul tour et n'a nulle part où s'arrêter.

## Un défaut ancien trouvé au passage

Le bouton « mettre en pause » d'une phase existait depuis longtemps. **Il n'arrêtait rien du tout** :
les archers continuaient de tirer, les scoreurs de valider. La pause n'était qu'un mot affiché dans le
suivi.

Le dire est important parce que c'est ce qui a sauvé cette US : la fiche partait du postulat inverse
(« la pause gèle déjà la saisie, attention aux effets de bord »). Sans la vérification, on aurait livré
un planning de pauses qui n'arrête personne — une fonctionnalité entière fausse, et silencieusement.

C'est désormais réparé pour une phase. Le même bouton **au niveau du tournoi** reste, lui, décoratif :
c'est un autre geste, à une autre échelle, et il est inscrit au registre des points à traiter.

## Ce qui manque encore

Prévu **tout de suite après**, et à livrer avant de se servir des pauses un jour de compétition :

- ni le public ni l'écran de salle ne **disent** qu'il s'agit d'une pause — un spectateur pourrait la
  lire comme une panne ;
- rien ne rappelle à l'organisateur qu'une phase attend sa relance (« 2 phases attendent votre relance
  depuis 14 min ») ;
- il ne peut pas encore poser une pause **en cours de journée** (« bloquer dans 2 tours ») : tout se
  décide à l'atelier.

C'est `E05US034`. Sans elle, la capacité livrée aujourd'hui crée un mode de panne neuf : la salle
attend, personne ne sait pourquoi, et rien n'a l'air anormal.

## À prévoir plus tard

Le commanditaire a annoncé un besoin **futur** : un vrai **planning horaire de journée** (« pause repas
12 h – 13 h 30 »), où l'application calculerait elle-même quel tour tombe avant. Ce n'est pas le besoin
d'aujourd'hui, qui s'arrête à « après le tour n », et il n'a délibérément pas été anticipé dans le code
— seulement noté à l'endroit où l'on saura quoi rouvrir le jour où il arrivera.
