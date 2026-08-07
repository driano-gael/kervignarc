# 7 août 2026, 15 h 51 — Chaque départ rejoue le tournoi

Votre tournoi se joue en plusieurs **départs** : le créneau de 9 h, celui de 14 h. L'application le
savait pour les inscriptions, les quotas et le plan de cibles — mais **pas pour le tir**. Sur quatre
départs de cent archers, elle publiait **un** classement de quatre cents, où l'archer du matin se
retrouvait rangé contre celui du soir qu'il n'a jamais croisé.

Ce n'était pas un affichage discutable : c'était un résultat faux. Il l'était depuis treize mois. La
décision « un départ rejoue le tournoi » avait bien été prise en juillet 2025 — seule la logistique
l'avait appliquée, le moteur était resté en arrière, et rien ne permettait de s'en apercevoir.
**Désormais un tournoi de quatre créneaux produit quatre classements de cent.**

## Ce qui se prévoit, et ce qui se tire

En corrigeant cela, un second défaut est apparu : l'application recopiait le déroulé sur chaque
créneau. Régler le barème, c'était l'écrire quatre fois — et rien n'empêchait le départ 3 de
s'écarter des autres sans que personne ne le voie.

La séparation est maintenant nette, et elle se voit à l'écran :

- **ce qui se prévoit appartient au tournoi.** L'écran « Phases » compose la suite des phases **une
  seule fois**. Il n'y a plus de pastille d'état ni de bouton « Démarrer » : « démarrer la phase 2 »
  n'aurait plus de destinataire — la démarrer sur quel créneau ?
- **ce qui se tire appartient au créneau.** Un panneau « Piloter un créneau », sous le suivi du
  déroulé, fait vivre les phases départ par départ. **Le matin peut être en duels pendant que
  l'après-midi qualifie** — c'était impossible avant.

Le classement se lit lui aussi par créneau, avec un sélecteur. Sur l'**écran de salle**, pas de
sélecteur : il reste sans interaction, comme les autres vues projetées, et affiche le classement du
départ **qu'on est en train de tirer** — pas celui du matin resté affiché depuis six heures.

## Trois choses de plus, trouvées en relisant le travail

La relecture de cette correction en a trouvé trois autres, du même tonneau — des écrans restés au
tournoi là où la réalité est le créneau. Elles sont corrigées dans la même livraison.

**Le jour J, on était envoyé au mauvais tableau.** Les quatre chemins qui répondent à « où est-ce
que je tire ensuite ? » — la tablette, l'écran de salle, la table d'organisation, le panneau de
duels — visaient tous le premier tableau du **tournoi**. Les archers de l'après-midi étaient donc
renvoyés vers celui du matin, clos depuis des heures. C'est le défaut qui aurait coûté le plus cher
en salle, et il ne se voyait pas sur un tournoi à un seul créneau.

**Le suivi du déroulé se dessinait en double.** Sur deux créneaux, l'écran empilait le déroulé deux
fois, l'avancement du dernier écrasait celui des autres, et les tableaux étaient dimensionnés sur la
**somme** des inscrits : quatre créneaux de cent archers faisaient dessiner un tableau pour quatre
cents. Même chose pour l'onglet public « Tableaux », qui affichait les arbres de tous les créneaux
sans rien pour les distinguer.

**Le contrôle d'effectif comptait tout le monde ensemble.** Un tournoi de deux créneaux à 40 et 8
inscrits démarrait sans broncher, parce que 48 suffisaient au déroulé — puis échouait en salle,
l'après-midi. Le contrôle porte désormais sur le créneau **le moins garni**, et le refus le nomme :
« 8 archers inscrits **sur le départ 2** pour 34 requis ».

## Ce qu'il faut savoir

**Un tournoi à un seul départ — le cas courant — ne change pas.** Vous ne verrez de différence que
si vous en créez plusieurs.

**Une perte à signaler.** Si, sur une base existante, deux créneaux avaient reçu des réglages
différents pour le même rang de phase, seul celui du **premier départ** est conservé. C'est le sens
de la correction — ces écarts n'auraient jamais dû être possibles — mais c'est une perte réelle.

**Trois limites restent ouvertes**, toutes tracées au registre plutôt que corrigées à la hâte : le
**palmarès** ne voit encore que le premier créneau ; un archer inscrit sur **deux créneaux** ne peut
pas encore y tirer deux séries distinctes ; et il n'existe pas d'écran rassemblant les N classements
d'un tournoi.

Sur le palmarès, **vous avez tranché le 7 août** : ce sera **juxtaposé** — quatre départs, quatre
podiums, et aucun classement d'ensemble. La correction est planifiée, mais elle n'est pas dans cette
livraison : jusque-là, le palmarès d'un tournoi à plusieurs créneaux n'affiche que le premier.

**Deux défauts graves trouvés à la relecture finale.** Ils méritent d'être racontés, parce qu'ils
ont exactement la même forme que celui que cette livraison corrige — et qu'aucun des deux ne se
voyait sur un tournoi à un seul créneau.

- **Les écrans de duels s'adressaient au mauvais créneau.** Le plan de duels, la saisie des duels et
  « Feu vert » proposaient les phases du *tournoi* au lieu de celles du créneau. L'identifiant qu'ils
  envoyaient au serveur n'était même pas celui d'une phase, mais celui d'une ligne du déroulé —
  deux choses différentes, qui portent par hasard les mêmes numéros quand il n'y a qu'un créneau. Le
  scoreur de l'après-midi aurait écrasé les duels du matin, et « Feu vert » aurait lancé le tour du
  mauvais créneau sur toutes les tablettes, **sans le moindre message d'erreur**.
- **Le panneau des barrages faisait disparaître un bouton.** Il affichait les barrages de tous les
  créneaux. Un barrage encore ouvert le matin, au même rang qu'une égalité de l'après-midi — cas
  parfaitement ordinaire —, retirait le bouton « Faire tirer » de l'après-midi : plus aucun moyen de
  départager la dernière place qualificative.

Les deux sont corrigés, et chacun a désormais un test qui **échoue** si on remet l'erreur. Ce qui
manquait n'était pas l'attention : c'était un banc d'essai à **deux créneaux**. La quasi-totalité des
tests du projet tournaient sur un tournoi à un seul départ, où les deux façons de compter donnent le
même résultat. Un tel banc existe maintenant.

**À dire franchement sur la méthode** : cette correction est partie d'un constat de bug, pas d'une
fiche d'US. Elle a donc été spécifiée **après** avoir été écrite — l'inverse de la règle que le
projet se donne. Le raisonnement est consigné dans deux décisions d'architecture, mais les critères
d'acceptation décrivent ici ce qui a été livré ; ils valent comme garde-fou de non-régression, pas
comme preuve que le besoin a été bien compris. C'est à la recette de le confirmer.

Recette : [`docs/fonctionnel/E01US025.md`](../docs/fonctionnel/E01US025.md).
