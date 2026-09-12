# 12 septembre 2026 — Quand deux personnes saisissent la même volée, le rôle tranche

`E16US020` répond à une question que vous aviez posée au questionnaire sur les maquettes : *« deux
personnes modifient la même volée : qui doit trancher ? »*. Votre réponse était **la hiérarchie**.
Elle est maintenant dans le serveur.

## Ce qui change

Une volée **retient le rôle réel** de qui l'a écrite — pas le nom tapé dans « saisi par », qui est
une étiquette libre, mais la façon dont on s'est connecté : le QR d'une cible, le code d'un scoreur,
la session de l'organisateur. Une écriture venue d'un rang **moins élevé** que celui qui a déjà
saisi est **refusée**, avec une phrase qui dit pourquoi.

L'ordre est : **poste de cible → scoreur → organisateur**.

Avant, la dernière écriture gagnait toujours, en silence. Le cas visé est concret : vous corrigez
une volée, et la tablette de la cible — qui n'a pas vu votre correction — renvoie l'ancienne valeur
trente secondes plus tard.

## Trois choses à savoir, décidées avec vous

- **Entre deux tablettes, rien ne change.** Elles ont le même rang, donc la règle ne les départage
  pas : le dernier écrit gagne, comme avant. C'est **le cas le plus fréquent en salle**, et c'est le
  renoncement le plus coûteux de cette livraison. La solution qui l'aurait couvert — refuser *tout*
  second écrivain et lui montrer la saisie de l'autre — a été écartée, pas oubliée.
- **Le refus joue aussi vers le bas.** Si vous saisissez par erreur sur la cible 7, cette cible ne
  peut plus se corriger toute seule. Le recours : vous annulez la validation, ce qui **remet la
  préséance à zéro** et rend la volée à la tablette.
- **Cela ne concerne que la qualification.** Duels, poules, système suisse, colline et Big Shoot Off
  ne bougent pas.

## Ce qui n'est pas encore visible à l'écran

⚠️ **À dire franchement : vous ne verrez rien de tout cela en manipulant l'application aujourd'hui.**
Aucun écran d'administration ne saisit de volée de qualification — le seul écran qui écrit une volée
est la tablette, et deux tablettes sont à rang égal. Le refus ne peut donc se produire que par un
appel technique direct.

La règle est bien là, tenue par le serveur et vérifiée par des tests. L'écran de la tablette sait
déjà afficher le refus, en ambre, avec le recours. Il attend la surface qui le déclenchera. C'est
inscrit au registre (`DETTE-100`) plutôt que passé sous silence.

Le scénario de recette détaillé est dans [`docs/fonctionnel/E16US020.md`](../docs/fonctionnel/E16US020.md).
