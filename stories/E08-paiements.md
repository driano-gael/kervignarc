# E08 — Suivi des paiements — User Stories

> EPIC : [EPIC-08](../epics/EPIC-08-paiements.md) · Réfs : CDC fonctionnel M8.

---

### E08US001 — Calculer le montant dû
*En tant qu'*administrateur, *je veux* le montant dû par archer, *afin de* facturer.
- **CA** : montant dû d'un archer = **somme des tarifs des départs** auxquels il est inscrit (E02US004 pose les tarifs des créneaux, E02US009 les inscriptions) ; recalculé si les inscriptions ou les tarifs changent. *(Révisé le 16/07/2026 — [ADR-0017](../docs/adr/0017-le-depart-est-un-creneau-du-tournoi.md) : les prix pouvant différer par créneau, c'est une **somme**, non plus `tarif × nb`.)*
- **Dépend de** : E02US004, E02US009 · **Jalon** : J1

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

### E08US005 — Rembourser une inscription payée annulée
*En tant qu'*administrateur, *je veux* tracer le remboursement d'une inscription **payée** qui disparaît (créneau supprimé ou archer désinscrit), *afin de* ne pas laisser une somme encaissée sans contrepartie.
- **CA** : quand une inscription **marquée payée** est effacée — suppression d'un départ à inscriptions confirmée (E02US009, [ADR-0018](../docs/adr/0018-supprimer-un-depart-a-inscriptions-confirmable.md)) ou désinscription — le montant encaissé devient un **remboursement à traiter** ; l'admin le marque **remboursé** (daté, tracé) ou **reporté** sur un autre créneau ; aucun encaissement en ligne (comme E08US002).
- **Notes** : **déportée d'E02US009** ([ADR-0018](../docs/adr/0018-supprimer-un-depart-a-inscriptions-confirmable.md)) : E02US009 ne fait que *décompter* les payées détruites dans le message de confirmation ; le remboursement est un **mouvement d'argent**, absent du modèle tant que `paye` reste un simple booléen. Cette US introduit la notion de transaction/remboursement (registre daté), pas E02US009. **Ouverte** : forme exacte du registre (avoir, report, remboursement effectif) à cadrer avec l'organisateur.
- **Dépend de** : E02US009, E08US002 · **Jalon** : J2
