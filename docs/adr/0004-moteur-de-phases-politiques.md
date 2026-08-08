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

**Précisé par [ADR-0046](0046-config-policies-politiques-nommees-parametrees.md)** (E05US003) : la
forme concrète de la `config` — politiques sous `config.policies`, chacune `{"nom": …, …paramètres}`,
le grain de `validation` restant hors `policies` — et l'assemblage via un registre peuplé par la
composition root. C'est la résorption de DETTE-003.

## Porté dans le code par

> *Section ajoutée le 08/08/2026 (rétro-équipement des ADR structurants encore actifs). La règle
> « un ADR nomme les modules qui le portent » a été instituée le 06/08/2026 par
> [ADR-0075](0075-le-depart-est-la-portee-sportive.md) et n'avait pas été appliquée rétroactivement.
> Les modules ci-dessous ont été **vérifiés dans le code du jour**, pas déduits de l'ADR — nommer un
> module vide reproduirait exactement le défaut que la section existe pour empêcher.*

- `backend/domain/politiques.py` — **le cœur de cet ADR**. `FamillePolitique` énumère les familles ;
  chaque famille est un `Protocol` du domaine (`Routing`, `Scoring`, `Seeding`, `Byes`, `Tiebreak`,
  `Depth`, `Aggregation`) avec plusieurs implémentations pures. `PolitiquesPhase` est le jeu assemblé
  d'une phase, `RegistrePolitiques` la table `nom → implémentation`, et `assembler_politiques()` la
  fonction qui transforme une `config` en jeu de stratégies.
- `backend/domain/tableau.py` — le moteur qui **consomme** les politiques : il ne connaît aucun
  format, seulement des `Protocol`.
- `backend/domain/phase.py` — la phase porte le type (`TypePhase`) et la `config` où vivent les
  politiques ; `SourcePhase` porte le peuplement.
- `backend/bootstrap/composition.py` — le registre est **câblé à la main** (règle 8, pas de DI
  magique) : c'est le seul endroit où un nom de politique rencontre sa classe.

⚠️ **Deux écarts entre le texte de 2026-07-08 et le code d'aujourd'hui**, à connaître avant de citer
cet ADR :

1. La signature `route(perdant, tour, contexte)` du tableau ci-dessus a été **ressignée en
   `route(contexte)`** par [ADR-0061](0061-routing-generique-et-placement-en-cascade.md) — une
   méthode sans contexte complet ne pouvait rendre qu'une réponse constante, ce qui bloquait tout le
   moteur générique.
2. Le vocabulaire du tableau n'est pas celui du code : « Barème » se dit `scoring`, « Départage » se
   dit `tiebreak`, « Routage » se dit `routing`. Ce sont des **noms de famille**, pas une divergence
   de conception — mais un `grep "Barème"` ne trouve pas la politique.

Sept familles existent aujourd'hui, contre six au tableau : `aggregation` s'est ajoutée
([ADR-0067](0067-palmares-agregation-des-rangs-de-phases.md)).
