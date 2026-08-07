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

## Ce qu'il faut savoir

**Un tournoi à un seul départ — le cas courant — ne change pas.** Vous ne verrez de différence que
si vous en créez plusieurs.

**Une perte à signaler.** Si, sur une base existante, deux créneaux avaient reçu des réglages
différents pour le même rang de phase, seul celui du **premier départ** est conservé. C'est le sens
de la correction — ces écarts n'auraient jamais dû être possibles — mais c'est une perte réelle.

**Trois limites restent ouvertes**, toutes tracées au registre plutôt que corrigées à la hâte : le
**palmarès** ne voit encore que le premier créneau (et sa correction demande votre arbitrage : sur
quatre départs, additionne-t-on les podiums ou les juxtapose-t-on ?) ; un archer inscrit sur **deux
créneaux** ne peut pas encore y tirer deux séries distinctes ; et il n'existe pas d'écran rassemblant
les N classements d'un tournoi.

**À dire franchement sur la méthode** : cette correction est partie d'un constat de bug, pas d'une
fiche d'US. Elle a donc été spécifiée **après** avoir été écrite — l'inverse de la règle que le
projet se donne. Le raisonnement est consigné dans deux décisions d'architecture, mais les critères
d'acceptation décrivent ici ce qui a été livré ; ils valent comme garde-fou de non-régression, pas
comme preuve que le besoin a été bien compris. C'est à la recette de le confirmer.

Recette : [`docs/fonctionnel/E01US025.md`](../docs/fonctionnel/E01US025.md).
