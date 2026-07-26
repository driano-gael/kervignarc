# 26/07/2026 — L'organisateur compose le format de son tournoi (les phases)

**US E05US001 — Séquence de phases.** Premier jalon des **duels** : jusqu'ici, un tournoi n'avait
qu'une étape, la qualification. L'organisateur peut désormais **enchaîner des phases** après elle et
décrire le déroulé de la compétition.

## Ce qui est nouveau

- **Un écran « Phases (format) »** (Admin → Préparation, juste après « Barème & validation »). On y
  **ajoute** les étapes qui suivent la qualification — pour l'instant **élimination directe** et
  **placement** —, on les **réordonne** (monter / descendre), on les **édite** ou on les **supprime**.

- **Chaque phase a un cycle de vie.** Une phase est *à venir*, puis *en cours*, peut être *mise en
  pause* (elle se fige, on la reprend plus tard) et enfin *terminée*. Un bouton par action, au bon
  moment : on ne peut pas démarrer deux fois ni terminer une phase pas encore lancée.

- **On dit d'où une phase tire ses participants.** Une phase peut être « alimentée » par une phase
  précédente : par exemple, l'élimination directe prend **les 16 premiers de la qualification**.
  L'application **vérifie que ça tient debout** : elle refuse une sélection vide, des rangs qui
  n'existent pas (prendre 40 archers d'une phase qui n'en classe que 32), ou un effectif qui ne
  correspond pas, avec un message clair.

## Pour qui, et ce que ça change

Pour l'**organisateur**. C'est la **première brique du moteur d'élimination** : on passe d'un tournoi
« une seule épreuve » à un tournoi dont on **compose le déroulé**. À ce stade, on **décrit** le
format (les phases, leur ordre, leur enchaînement) ; **faire jouer** les duels — tirer les tableaux,
faire avancer les vainqueurs — viendra dans les US suivantes. Le modèle de « qui vient d'où » est
volontairement **simple pour commencer** (une source par rangs) et s'enrichira quand on abordera le
placement intégral.
