# 2 août 2026, 16h13 — Départager au tir : le barrage des places décisives

**US livrée : E06US003.**

À score égal, le classement départage au nombre de 10, puis de 9. Quand cela ne suffit pas, deux
archers sont strictement à égalité, et jusqu'ici ils **partageaient** leur rang : deux 2ᵉ, puis un 4ᵉ.

C'est très bien au milieu du tableau. Ça ne va plus quand la place décide de quelque chose — la
dernière qualificative pour le tableau final, une marche du podium. Le règlement prévoit alors un
**tir de barrage** : une flèche chacun, le plus haut score gagne.

**Ce que l'organisateur peut faire maintenant.** Il déclare, sur la phase de qualification,
« je départage au tir jusqu'au rang N ». Le classement fait alors apparaître un encart qui **nomme
les places à trancher et les archers concernés**. Il fait tirer, saisit la flèche de chacun, et les
rangs deviennent consécutifs dans le tableau — sans décaler les archers suivants.

**Trois précautions valent d'être connues.**

- Si les deux flèches sont encore égales, on compare la distance au centre. Mais si le juge **ne
  l'a pas mesurée**, l'application **fait retirer** au lieu de trancher : une mesure absente est une
  inconnue, pas un centre parfait. C'est le cas le plus fréquent en salle — on mesure la flèche
  litigieuse, rarement les deux.
- Un archer **absent** au barrage annoncé est déclaré perdant, comme le veut le règlement. Cela se
  **coche** explicitement : un champ laissé vide veut dire « pas encore noté », jamais « absent ».
  L'application refuse d'ailleurs d'enregistrer une manche à moitié saisie.
- Une flèche mal notée se **corrige** : on ressaisit la manche, et le classement suit
  immédiatement. L'application ne mémorise pas « qui a gagné », elle le recalcule à partir des
  flèches.

**Rien ne change pour un tournoi qui ne demande rien.** Sans réglage, le classement se comporte
exactement comme avant : rangs partagés, aucun encart, aucun message. Le barrage est une **option**,
et c'est resté le point de vigilance principal de la livraison.

**Les poules et le Big Shoot Off aussi.** Un dépliant « Départager d'autres archers » permet de
conduire un barrage de poule ou de Big Shoot Off. Une différence à connaître : là, c'est
l'organisateur qui **désigne** les archers à départager, parce que l'application ne calcule pas
encore ces classements-là — et pour la même raison, le résultat s'affiche à l'écran mais ne remonte
dans aucun classement. On le reporte à la main, en attendant que ces formats soient déroulés par
l'application.

**Ce qui n'est pas couvert.** Le barrage à l'intérieur d'un duel (égalité de sets) est une autre
fonction, déjà livrée par ailleurs.

Deux garde-fous ajoutés après relecture, qui se voient à l'usage : un barrage ouvert par erreur
s'**annule**, et une flèche mal notée se **corrige** depuis l'écran. Par ailleurs, aucune égalité
n'est proposée tant qu'aucune flèche n'a été validée — sinon, au démarrage, tous les archers étant à
zéro, l'application aurait proposé de faire tirer le plateau entier.

Détail du parcours de vérification : [`docs/fonctionnel/E06US003.md`](../docs/fonctionnel/E06US003.md).
