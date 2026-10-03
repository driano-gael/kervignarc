# 3 octobre 2026 — Le déroulé horaire s'imprime

**US** : `E09US007` · **Jalon** : J4

## Ce qui change

Depuis la veille, l'application calcule l'heure de chaque phase, départ par départ — mais on ne
pouvait que la lire à l'écran. L'écran **« Exports & impressions »** propose désormais le
**déroulé horaire en PDF** : un bloc par départ, une ligne par phase, avec ses heures de début et de
fin prévues et, quand c'est réglé, son nombre de tours (« 2 tours », « 5 rondes »).

## Pour l'organisateur

- Un seul document pour tout le tournoi, ou pour un seul départ au choix — à afficher dans la salle
  ou à envoyer aux clubs.
- Les heures sont celles de la grille de l'écran « Phases » : rien n'est recalculé. Une heure que
  l'application ne connaît pas s'imprime « à préciser », jamais devinée.
- Pas d'heure par tour : le document reste à la maille de la phase, comme la grille.
- PDF seul : un déroulé se lit, il ne se dépouille pas au tableur.

Scénario de vérification : [`docs/fonctionnel/E09US007.md`](../docs/fonctionnel/E09US007.md).
