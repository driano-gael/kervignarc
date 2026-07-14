# EPICs — Kervignarc

Découpage en grandes fonctionnalités (EPICs), **par capacité produit**. Stratégie : **walking skeleton d'abord** (une tranche verticale bout-en-bout tôt), puis enrichissement par incréments de valeur. **Pas d'échéance ferme.**

## Convention
- Un fichier par EPIC : `EPIC-NN-slug.md`.
- Statuts : `À planifier` · `En cours` · `Livré`.
- Priorité indicative : **MVP** (séquence simple : qualif → élimination directe → podium), **MVP+1** (format riche : placement intégral 1→N, repêchage, écran projeté…), **Ultérieur**.

## Carte des EPICs

| ID | Titre | Priorité | Dépend de |
|---|---|---|---|
| [EPIC-00](EPIC-00-socle-technique.md) | Socle technique & walking skeleton | MVP | — |
| [EPIC-01](EPIC-01-configuration-tournoi.md) | Configuration du tournoi | MVP | 00 |
| [EPIC-02](EPIC-02-inscriptions.md) | Inscriptions & clubs | MVP | 00, 01 |
| [EPIC-03](EPIC-03-placement.md) | Placement des archers & plan de cibles | MVP | 01, 02 |
| [EPIC-04](EPIC-04-saisie-scores.md) | Saisie des scores en temps réel | MVP | 03, 10 |
| [EPIC-05](EPIC-05-moteur-phases.md) | Moteur de phases & tableaux | MVP → MVP+1 | 02, 04 |
| [EPIC-06](EPIC-06-classements.md) | Classements & résultats | MVP → MVP+1 | 04, 05 |
| [EPIC-07](EPIC-07-affichage-public.md) | Affichage public & écran projeté | MVP+1 | 04, 06 |
| [EPIC-08](EPIC-08-paiements.md) | Suivi des paiements | MVP | 02 |
| [EPIC-09](EPIC-09-exports.md) | Exports & documents | MVP → MVP+1 | 03, 06 |
| [EPIC-10](EPIC-10-acces-roles.md) | Accès & rôles | MVP | 00 |
| [EPIC-11](EPIC-11-exploitation.md) | Exploitation : sauvegarde, packaging, réseau | MVP | 00 |
| [EPIC-12](EPIC-12-pilotage-jour-j.md) | **Pilotage du jour J** — supervision, complétude, bascule de tour | MVP | 03, 04, 05 |

> 🎯 **EPIC-12 porte la valeur du produit** (créé le 14/07/2026). Les 12 EPICs ci-dessus couvraient tout le
> cycle — configuration, inscriptions, placement, saisie, moteur, classements, affichage, paiements, exports,
> rôles, exploitation — **sauf le moment où se joue la valeur** : faire partir le tour suivant **en 2 minutes
> au lieu de 20**, pendant que 150 archers attendent. Le trou a été révélé par l'entretien de conception du
> 14/07/2026 ([CDC UX §1](../cahier-des-charges-ux.md)).

## Ordre de construction conseillé
`EPIC-00` (skeleton) → tranche verticale minimale traversant `01 → 02 → 03 → 10 → 04 → 05(simple) → 06(simple) → 11(packaging)`, puis enrichissement : `05/06 (placement intégral)`, `07`, `09 (PDF)`, `02 (import XLS)`.

**`EPIC-12` se construit en deux temps**, adossés aux jalons : **J1** — supervision des postes, recherche
globale, complétude, règle d'alerte (dès qu'il y a des postes à superviser, donc avec `04`) ; **J2** — bascule
de tour (dès qu'il y a des duels à enchaîner, donc avec `05`).

## Références
`cahier-des-charges.md` (fonctionnel), `cahier-des-charges-technique.md`, **`cahier-des-charges-ux.md`** (architecture d'expérience, registre `D-nn`), **`cahier-des-charges-design.md`** (identité, registre `DV-nn`), `moteur-placement-lucky-loser.md`, `guide-architecture.md`, `docs/adr/`.
