# 2 octobre 2026 — Le déroulé horaire de la journée

**US** : `E03US010` · **Jalon** : J4

## Ce qui change

Jusqu'ici, seule l'heure de chaque **départ** existait : rien ne disait à quelle heure commencerait
le tableau, ni la phase suivante.

Désormais, l'organisateur donne à chaque phase une **durée prévue** (« 2 h 30 pour la
qualification »), et l'application **calcule les heures** : sous la liste des phases, une grille
donne le début et la fin de chaque phase, **pour chaque départ**. Une phase commence quand celles
qui l'alimentent sont finies ; deux phases nourries par la même commencent ensemble.

Le **public** voit, dans l'onglet « En cours », l'heure de **début** prévue de chaque phase — pas
la fin, que le club juge trop imprévisible.

## Pour l'organisateur

- Une seule saisie vaut pour tous les départs : changer l'heure d'un départ décale toute sa grille.
- Aucune durée n'est proposée d'office. Une phase sans durée affiche « — », et celles qui en
  dépendent aussi : l'application ne devine jamais.
- Les pauses programmées se comptent dans la durée de leur phase.
- C'est un **prévisionnel** : l'application ne calcule ni avance ni retard pendant la journée.
- Un format enregistré emporte ses durées.

Scénario de vérification : [`docs/fonctionnel/E03US010.md`](../docs/fonctionnel/E03US010.md).
