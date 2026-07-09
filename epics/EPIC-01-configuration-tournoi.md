# EPIC-01 — Configuration du tournoi

- **ID** : EPIC-01
- **Statut** : À planifier
- **Priorité** : MVP
- **Dépend de** : EPIC-00
- **Réfs** : CDC fonctionnel M1 ; ADR-0006 (vocabulaire)

## Objectif / valeur
Permettre à l'organisateur de définir le contexte d'un tournoi : catégories, blasons, plan de salle et barèmes. C'est le socle de données que consomment le placement, la saisie et le moteur.

## Périmètre
### Inclus
- Création d'un tournoi (nom, date, lieu, type officiel/non officiel).
- **Catégories** avec pré-réglages FFTA salle modifiables ; association catégorie ↔ blason.
- **Blasons** : `taille` (fraction de place) + `capacité`.
- **Gabarits de salle** réutilisables (nb de cibles, capacité 1/2/4, positions A/B/C/D).
- **Presets de barèmes** modifiables par type de phase (qualif cumul, sets, finales, shoot-off, BSO).
- **Tarif par départ** (pour le suivi de paiement).

### Exclus
- L'application des barèmes (EPIC-04/05) ; l'algorithme de placement (EPIC-03).

## Capacités
- [ ] CRUD tournoi / catégories / blasons.
- [ ] Gestion des gabarits de salle (créer, réutiliser, ajuster).
- [ ] Bibliothèque de presets de barèmes.

## Incréments
- **MVP** : tournoi + catégories + blasons + un gabarit + barème de qualification simple + tarif.
- **MVP+1** : presets riches multi-phases, plusieurs gabarits, réglages officiels avancés.

## Critères d'acceptation (epic)
- Un tournoi entièrement configurable est prêt à recevoir des inscrits.
- Les blasons expriment bien une fraction de capacité cible.

## Questions ouvertes
- Liste exacte des catégories/blasons FFTA salle à pré-charger.
