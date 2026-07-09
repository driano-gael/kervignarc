# ADR-0004 — Moteur de phases à politiques injectables

- **Statut** : Accepté
- **Date** : 2026-07-08
- **Décideurs** : Organisateur / Architecte

## Contexte et problème

Le besoin ne se limite pas à un format de tournoi figé. L'analyse du classeur réel (`Tableaux.xlsx`, tournoi 120) révèle un **placement intégral en cascade** (personne n'est éliminé, la plage de rangs se divise par deux, matchs terminaux fixant chaque rang 1→N). Par ailleurs le client veut pouvoir composer **librement** des séquences de phases (qualif, barrage, principal, repêchage, placement, finale, Big Shoot Off) et couvrir aussi des **formats simples** (élimination directe, top N). Coder chaque format en dur mènerait à une explosion combinatoire de code.

Décisions de cadrage associées (formalisation §7) : Lucky Loser **configurable** (classement en cascade *ou* repêchage réintégrant le principal), profondeur de classement **configurable** (1→N ou top N), départage **presets FFTA modifiables**, byes **aux mieux classés**, règle /2 **universelle**.

## Options envisagées

- **Moteur générique + politiques injectables** : un format = un assemblage de stratégies.
- Un module par format (placement intégral, élimination simple…) : duplication, divergence, maintenance coûteuse.
- Moteur monolithique paramétré par de gros `if/else` : illisible, non testable unitairement.

## Décision

Le moteur manipule une **séquence de phases**. Chaque phase de tableau reçoit un jeu de **politiques injectables**, interfaces du domaine avec plusieurs implémentations :

| Politique | Rôle | Variantes |
|---|---|---|
| **Routage** `route(perdant, tour, contexte)` | destination du perdant | cascade de placement · repêchage-réintégration · élimination sèche |
| **Barème** | calcul/victoire | cumul · sets 4 pts · finales 6 pts · shoot-off · Big Shoot Off |
| **Seeding** | composition de l'arbre | serpent, arrondi 2^k |
| **Byes** | exempts si effectif ≠ 2^k | aux mieux classés (défaut) |
| **Départage** | égalités | nb de 10/9 · shoot-off plus près du centre |
| **Profondeur** | jusqu'où classer | 1→N (défaut) · top N + regroupement |

Un **format** est donc un assemblage : ex. « placement intégral 120 » = `routing=cascade, depth=1→N, byes=mieux classés, seeding=serpent`. Les politiques sont stockées dans la **config JSON de la phase** et réutilisables entre tournois (modèles de séquence).

## Conséquences

- **+** Nouveaux formats sans nouveau code moteur (assemblage + config).
- **+** Chaque politique est unitairement testable ; le repêchage WA devient `routing=repêchage`.
- **+** Répond directement au « constructeur de tableau libre » du CDC fonctionnel.
- **−** Abstraction exigeante à concevoir : le **routage** est le point le plus délicat (risque R1).
- **−** Nécessite un **oracle** fort : rejeu du tournoi 120 pour valider l'assemblage par défaut.

## Liens
`moteur-placement-lucky-loser.md` (règles + décisions §7) ; `cahier-des-charges-technique.md` §4.2 ; ADR-0003.
