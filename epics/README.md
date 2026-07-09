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

## Ordre de construction conseillé
`EPIC-00` (skeleton) → tranche verticale minimale traversant `01 → 02 → 03 → 10 → 04 → 05(simple) → 06(simple) → 11(packaging)`, puis enrichissement : `05/06 (placement intégral)`, `07`, `09 (PDF)`, `02 (import XLS)`.

## Références
`cahier-des-charges.md` (fonctionnel), `cahier-des-charges-technique.md`, `moteur-placement-lucky-loser.md`, `guide-architecture.md`, `docs/adr/`.
