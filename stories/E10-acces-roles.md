# E10 — Accès & rôles — User Stories

> EPIC : [EPIC-10](../epics/EPIC-10-acces-roles.md) · Réfs : CDC technique §9, ADR-0007.

---

### E10US001 — Consultation publique ouverte
*En tant que* spectateur, *je veux* accéder aux résultats sans compte, *afin de* consulter librement.
- **CA** : accès en lecture seule sur le LAN sans authentification ; aucune action d'écriture possible.
- **Dépend de** : E00US009 · **Jalon** : J1

### E10US002 — Accès administrateur protégé
*En tant qu'*organisateur, *je veux* un accès admin protégé, *afin de* sécuriser la configuration.
- **CA** : authentification par mot de passe ; accès aux fonctions admin (config, moteur, exports, corrections).
- **Dépend de** : E00US009 · **Jalon** : J1

### E10US003 — Session scoreur par code de cible
*En tant que* scoreur, *je veux* ouvrir une session via un code de cible, *afin de* saisir sans compte nominatif.
- **CA** : saisie d'un code → session scoreur rattachée à la cible ; jeton simple ; expiration raisonnable.
- **Dépend de** : E03US001 · **Jalon** : J1

### E10US004 — Habiliter un scoreur sur plusieurs cibles
*En tant que* scoreur, *je veux* couvrir plusieurs cibles, *afin de* gérer un groupe.
- **CA** : une session peut être habilitée sur plusieurs cibles ; validation possible sur chacune ; pas sur les autres.
- **Dépend de** : E10US003 · **Jalon** : J1

### E10US005 — Journal d'audit métier
*En tant qu'*organisateur, *je veux* tracer les actions sensibles, *afin de* gérer les litiges.
- **CA** : `AuditLog` des corrections de score, validations, forfaits (qui/quand/avant-après) ; consultable par l'admin.
- **Dépend de** : E10US002 · **Jalon** : J1
