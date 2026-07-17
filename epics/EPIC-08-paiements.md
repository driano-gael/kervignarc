# EPIC-08 — Suivi des paiements

- **ID** : EPIC-08
- **Statut** : À planifier
- **Priorité** : MVP
- **Dépend de** : EPIC-02
- **Réfs** : CDC fonctionnel M8

## Objectif / valeur
Suivre ce que chaque archer/club doit et a payé — sans transaction en ligne. Simplifie la gestion administrative de l'inscription.

## Périmètre
### Inclus
- **Montant dû** = **somme des tarifs** des départs auxquels l'archer est inscrit (les tarifs pouvant différer par créneau — [ADR-0017](../docs/adr/0017-le-depart-est-un-creneau-du-tournoi.md)).
- Statut **payé / non payé**.
- Vues consolidées **par archer** et **par club**.

### Exclus
- Paiement en ligne / transactions bancaires (hors périmètre produit).

## Capacités
- [ ] Calcul du montant dû.
- [ ] Suivi du statut de paiement.
- [ ] Vues archer / club.

## Incréments
- **MVP** : suivi complet (calcul + statut + vues).

## Critères d'acceptation (epic)
- Pour tout archer et tout club, le dû et le payé sont exacts et à jour.
- Alimente la liste club & paiement (EPIC-09).
