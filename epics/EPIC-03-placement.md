# EPIC-03 — Placement des archers & plan de cibles

- **ID** : EPIC-03
- **Statut** : À planifier
- **Priorité** : MVP
- **Dépend de** : EPIC-01, EPIC-02
- **Réfs** : CDC fonctionnel M4 ; prototype `blason.py`/`player.py`

## Objectif / valeur
Répartir automatiquement les archers sur les cibles en respectant les contraintes, avec ajustement manuel — remplace une tâche manuelle chronophage et sujette aux erreurs.

## Périmètre
### Inclus
- **Placement automatique** sur la base du gabarit de salle (EPIC-01).
- **Contraintes** : capacité (**libre ≥ 1**), somme des fractions de blasons ≤ capacité, **hauteur de blason compatible** sur une même butte (un U11 tire à 110 cm, les autres à 130 cm — cf. [DETTE-002](../docs/dette.md), à résorber ici), ≥ 2 clubs par cible, séparation catégorie/blason (contrainte activable, pas liée au type de tournoi).
- **Ajustement manuel** par glisser-déposer.
- Attribution **cible + position (A/B/C/D) + départ**.
- Génération du **plan de cibles** (qui tire où) et du **déroulé horaire**.
- Placement des **duellistes côte à côte** (phases de tableau) — *incrément, lié EPIC-05*.

### Exclus
- Génération des tableaux/matchs (EPIC-05) ; exports imprimables (EPIC-09).

## Capacités
- [ ] Moteur de placement sous contraintes + rapport de faisabilité.
- [ ] Éditeur drag & drop.
- [ ] Plan de cibles par phase/tour.
- [ ] Déroulé horaire.

## Incréments
- **MVP** : placement auto (contraintes de base) + ajustement manuel + plan de cibles qualif.
- **MVP+1** : contraintes avancées, placement des duellistes, déroulé horaire enrichi.

## Critères d'acceptation (epic)
- Un placement valide (contraintes respectées ou conflits signalés) est produit et ajustable.

## Questions ouvertes
- **Priorité des contraintes** en cas de conflit (hypothèse : capacité > catégorie > mixité club).
- **Déroulé horaire** : calculé (durées × tours) ou saisi manuellement ?
