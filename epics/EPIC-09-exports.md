# EPIC-09 — Exports & documents

- **ID** : EPIC-09
- **Statut** : À planifier
- **Priorité** : MVP (documents de base) → MVP+1 (PDF complets)
- **Dépend de** : EPIC-03, EPIC-06
- **Réfs** : CDC fonctionnel M9 ; CDC technique (QT3 lib PDF)

## Objectif / valeur
Produire les documents papier/PDF nécessaires à l'organisation et à la communication des résultats, sans ressaisie.

## Périmètre
### Inclus
- **Feuilles de marque** (par cible/archer).
- **Listes de placement** (archer → cible / position / départ).
- **Listes club & paiement** (nom/prénom, n° départ, nb départs, dû, payé/non).
- **Classements PDF** (par catégorie ; classement intégral 1→N).
- **Déroulé horaire** de la journée.

### Exclus
- Production des données elles-mêmes (EPICs amont).

## Capacités
- [ ] Génération PDF (choix lib : WeasyPrint vs ReportLab — QT3).
- [ ] Modèles de documents.

## Incréments
- **MVP** : feuilles de marque + listes de placement + listes club/paiement (formats simples).
- **MVP+1** : classements PDF complets + déroulé horaire.

## Critères d'acceptation (epic)
- Les documents sont imprimables et fidèles aux données en base.

## Questions ouvertes
- Bibliothèque PDF à retenir (rendu attendu).
