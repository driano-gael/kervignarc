# ADR-0012 — Compter l'argent en centimes entiers, jamais en flottants

- **Statut** : Accepté
- **Date** : 2026-07-15
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`modele-de-donnees.md`](../modele-de-donnees.md) (`TOURNOI.tarif_depart` était `REAL`)
- **Introduit par** : E01US010 (tarif par départ) ; **lie** EPIC-08 (paiements) et EPIC-09 (exports)

## Contexte et problème

E01US010 demande un **tarif par départ** paramétrable (EF-1.7). Ce tarif n'est pas une donnée
d'affichage : il **alimente des calculs et des sommes**, déjà spécifiés —

- **EF-8.1 / E08US001** : montant dû = tarif × nombre de départs ;
- **EF-2.3** : un archer peut avoir plusieurs départs ;
- **EF-9.6 / E08US004, E09US004** : listes **club & paiement** — donc des **totaux** sur ~120 archers.

Le [modèle de données](../modele-de-donnees.md) prévoyait `TOURNOI.tarif_depart REAL`, et
`DEPART.tarif` / `DEPART.montant_du` en `REAL` également.

**Le problème est arithmétique, pas stylistique.** Un flottant binaire (IEEE-754) ne représente pas
exactement la plupart des montants décimaux : `8,10 €` devient `8.0999999999999996…`. Une valeur
isolée s'affiche encore correctement (l'arrondi la rattrape), mais l'erreur **s'accumule à la
somme** — précisément l'opération que font EF-8.1 et EF-9.6. Une liste club affiche alors
`972.0000000000005 €`, ou pire, un total qui ne tombe pas juste à l'euro près. C'est un défaut
**silencieux** : rien ne le signale, et il ne se voit que sur le document remis au club.

Le moment de trancher était **maintenant** : avant qu'EPIC-08 consomme le champ, et avant qu'une
base réelle contienne des tarifs à convertir.

## Options

1. **`REAL`, conforme au modèle** — aucune divergence à justifier, code direct. Mais la dérive
   ci-dessus est structurelle, et migrer plus tard signifie convertir des données de production.
2. **`Decimal` (Python) sérialisé en `TEXT`** — exact, et lisible en base. Mais conversions
   partout, et **SQLite ne sait pas `SUM()` du TEXT** : les agrégats d'EPIC-08/09 devraient charger
   toutes les lignes en mémoire pour les additionner en Python.
3. **Centimes entiers (`INTEGER`)** — exact par construction, sommable en SQL, comparable,
   trivialement sérialisable en JSON. Coût : convertir à l'affichage, et discipliner le nommage.

## Décision

Retenir l'option 3. **Tout montant du projet est un entier de centimes**, et cette règle vaut pour
le domaine, la base, l'API et le front.

- **L'unité est dans le nom** : tout champ monétaire porte le suffixe **`_centimes`**
  (`tarif_depart_centimes`, `montant_du_centimes`…). C'est la défense la moins chère contre la
  confusion euros/centimes — la classe de bug que ce choix rouvrirait s'il restait implicite. Elle
  remplace un type dédié : l'invariant se réduit à `>= 0`, un value object serait de l'abstraction
  sans emploi (ADR-0003, parcimonie).
- **Les euros n'existent qu'à l'affichage.** L'API transporte des centimes ; la conversion vit dans
  **un seul** module côté client (aujourd'hui `frontend/src/features/competition/format.ts`).
- **La conversion passe par les chiffres du texte**, jamais par `parseFloat(x) * 100` — multiplier
  un flottant par 100 rouvre exactement le problème qu'on évite.
- **`NULL` reste distinct de `0`** là où l'absence a un sens : `NULL` = montant **non défini**,
  `0` = **gratuit**. C'était le cas de l'ancien `TOURNOI.tarif_depart_centimes` (E01US010) ; sur
  `DEPART.tarif_centimes` (E02US004) le tarif est en revanche **obligatoire**, l'état « non défini »
  n'existant plus pour un créneau — voir [ADR-0017](0017-le-depart-est-un-creneau-du-tournoi.md).
- **Portée** *(mise à jour par [ADR-0017](0017-le-depart-est-un-creneau-du-tournoi.md))* :
  `DEPART.tarif_centimes` (E02US004 — le tarif a **quitté** `TOURNOI`, où E01US010 l'avait d'abord
  posé) ; les montants dérivés par archer/club d'EPIC-08/09 (sommes des tarifs des départs) ; tout
  montant à venir.

## Conséquences

- **+** Les sommes d'EPIC-08/09 sont **exactes**, et se font **en SQL** (`SUM()` sur des entiers).
- **+** Aucune migration de données à prévoir quand EPIC-08 arrivera : la règle est posée **avant**
  le premier consommateur et avant toute donnée réelle.
- **+** Le suffixe `_centimes` rend l'unité vérifiable à la lecture, du schéma jusqu'au DTO.
- **−** Le modèle de données devait être **corrigé** (`REAL` → `INTEGER`), y compris sur `DEPART`,
  qui n'est pas encore implémenté : laisser deux conventions à trois écrans d'écart aurait rendu le
  document auto-contradictoire — le lecteur d'E02US004 n'aurait pas su laquelle fait foi (c'est le
  mécanisme décrit en [DETTE-003](../dette.md)).
- **−** Il faut convertir à chaque frontière d'affichage, et la saisie utilisateur (virgule, point,
  2 décimales) demande une validation dédiée. Ce module est **le** point sensible : sa
  non-régression n'est aujourd'hui couverte par aucun test — cf. [DETTE-005](../dette.md).
- **−** Un montant reste un `int` nu : rien n'empêche techniquement de passer des euros à une
  fonction qui attend des centimes. Le nommage l'empêche en pratique ; un type dédié serait le
  remède si le cas se présentait réellement.

## Liens

ADR-0003 (hexagonale, domaine pur) ; [`modele-de-donnees.md`](../modele-de-donnees.md) (`TOURNOI`,
`DEPART`) ; [`glossaire.md`](../glossaire.md) (*Centimes*, *Tarif d'un départ*) ;
[`dette.md`](../dette.md) DETTE-005 ; CDC fonctionnel EF-1.7, EF-2.3, EF-8.1, EF-9.6.
