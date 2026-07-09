# E07 — Affichage public & écran projeté — User Stories

> EPIC : [EPIC-07](../epics/EPIC-07-affichage-public.md) · Réfs : CDC fonctionnel M6.

---

### E07US001 — Vue publique des classements
*En tant que* spectateur, *je veux* consulter les classements en lecture seule, *afin de* suivre le tournoi.
- **CA** : accès sans authentification ; lecture seule ; par catégorie ; responsive mobile.
- **Dépend de** : E06US001, E10US001 · **Jalon** : J1

### E07US002 — Live des vues publiques
*En tant que* spectateur, *je veux* que les classements se mettent à jour seuls, *afin de* ne pas rafraîchir.
- **CA** : abonnement WebSocket ; mise à jour automatique après chaque validation.
- **Dépend de** : E07US001, E04US009 · **Jalon** : J1

### E07US003 — Vue publique des plans de cibles
*En tant que* archer/spectateur, *je veux* voir qui tire où, *afin de* m'orienter dans la salle.
- **CA** : plan de cibles consultable (cible/position/départ) ; responsive.
- **Dépend de** : E03US008 · **Jalon** : J1

### E07US004 — Écran projeté plein écran
*En tant qu'*organisateur, *je veux* un affichage projeté, *afin de* informer la salle.
- **CA** : mode plein écran lisible à distance ; rotation automatique de vues (classement, tableaux).
- **Dépend de** : E07US002 · **Jalon** : J3

### E07US005 — Vue tableaux/arbres live
*En tant que* spectateur, *je veux* voir les arbres de duels en direct, *afin de* suivre la progression.
- **CA** : rendu de l'arbre (principal + placement) mis à jour en live.
- **Dépend de** : E05US007, E07US002 · **Jalon** : J3
