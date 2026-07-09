# E08 — Suivi des paiements — User Stories

> EPIC : [EPIC-08](../epics/EPIC-08-paiements.md) · Réfs : CDC fonctionnel M8.

---

### E08US001 — Calculer le montant dû
*En tant qu'*administrateur, *je veux* le montant dû par archer, *afin de* facturer.
- **CA** : montant = tarif (E01US010) × nombre de départs (E02US004) ; recalculé si les départs changent.
- **Dépend de** : E01US010, E02US004 · **Jalon** : J1

### E08US002 — Marquer payé / non payé
*En tant qu'*administrateur, *je veux* suivre le statut de paiement, *afin de* savoir qui a réglé.
- **CA** : statut payé/non payé par archer (ou par départ) ; modifiable ; pas de transaction en ligne.
- **Dépend de** : E08US001 · **Jalon** : J1

### E08US003 — Vue paiement par archer
*En tant qu'*administrateur, *je veux* une vue par archer, *afin de* contrôler individuellement.
- **CA** : liste des archers avec dû / payé / reste ; filtrable.
- **Dépend de** : E08US002 · **Jalon** : J1

### E08US004 — Vue paiement par club
*En tant qu'*administrateur, *je veux* une vue consolidée par club, *afin de* gérer les règlements groupés.
- **CA** : totaux par club (dû, payé, reste) ; détail des archers du club.
- **Dépend de** : E08US002 · **Jalon** : J1
