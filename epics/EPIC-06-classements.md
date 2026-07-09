# EPIC-06 — Classements & résultats

- **ID** : EPIC-06
- **Statut** : À planifier
- **Priorité** : MVP (simple) → MVP+1 (intégral)
- **Dépend de** : EPIC-04, EPIC-05
- **Réfs** : CDC fonctionnel M7 ; `moteur-placement-lucky-loser.md` §3-4

## Objectif / valeur
Produire les classements (qualif, duels, final) consommés par l'affichage et les exports. Concrétise la valeur « résultat » du tournoi.

## Périmètre
### Inclus
- **Classement de qualification** (cumul) avec **départage** (presets FFTA : nb de 10 puis 9 ; barrage de tir).
- **Classements de duels** / par phase.
- **Profondeur configurable** : 1→N (placement intégral) ou top N + regroupement.
- **Classement final** agrégé par catégorie et global.

### Exclus
- Mise en page imprimable (EPIC-09) ; affichage live (EPIC-07).

## Capacités
- [ ] Classement qualif + départage.
- [ ] Agrégation des résultats de tableau en rangs.
- [ ] Politique de profondeur (1→N / top N).

## Incréments
- **MVP** : classement de qualification + podium simple.
- **MVP+1** : classement **intégral 1→N** issu du placement en cascade.

## Critères d'acceptation (epic)
- Les rangs produits correspondent à l'oracle 120 (cohérent avec EPIC-05).
- Le départage est appliqué de façon déterministe et traçable.

## Questions ouvertes
- Critères exacts de départage/barrage à figer (presets FFTA modifiables).
