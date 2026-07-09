# E09 — Exports & documents — User Stories

> EPIC : [EPIC-09](../epics/EPIC-09-exports.md) · Réfs : CDC fonctionnel M9 (QT3 : lib PDF).

---

### E09US001 — Intégrer la bibliothèque PDF
*En tant que* développeur, *je veux* un socle de génération PDF, *afin de* produire tous les documents.
- **CA** : lib PDF choisie (WeasyPrint vs ReportLab — QT3) intégrée ; un document de test se génère ; fonctionne dans l'exécutable packagé.
- **Notes** : valider l'embarquement dans PyInstaller (risque R4).
- **Dépend de** : E00US012 · **Jalon** : J1

### E09US002 — Feuille de marque
*En tant qu'*organisateur, *je veux* imprimer les feuilles de marque, *afin de* la saisie/l'archivage papier.
- **CA** : feuille par cible/archer avec zones de scores ; conforme aux données.
- **Dépend de** : E09US001, E03US008 · **Jalon** : J1

### E09US003 — Liste de placement
*En tant qu'*organisateur, *je veux* imprimer le placement, *afin de* l'afficher à l'entrée.
- **CA** : liste archer → cible/position/départ ; triable par cible ou par nom.
- **Dépend de** : E09US001, E03US008 · **Jalon** : J1

### E09US004 — Liste club & paiement
*En tant qu'*organisateur, *je veux* la liste club/paiement, *afin de* gérer l'administratif.
- **CA** : par club/archer : nom/prénom, n° départ, nb départs, dû, payé/non ; totaux par club.
- **Dépend de** : E09US001, E08US003 · **Jalon** : J1

### E09US005 — Classement PDF par catégorie
*En tant qu'*organisateur, *je veux* exporter les classements par catégorie, *afin de* les diffuser/afficher.
- **CA** : PDF par catégorie (qualif et duels) ; en-tête tournoi ; imprimable.
- **Dépend de** : E09US001, E06US008 · **Jalon** : J3

### E09US006 — Classement intégral 1→N (PDF)
*En tant qu'*organisateur, *je veux* le classement complet en PDF, *afin de* publier le résultat final.
- **CA** : PDF listant les rangs 1→N ; cohérent avec E06US006.
- **Dépend de** : E09US001, E06US006 · **Jalon** : J3

### E09US007 — Déroulé horaire imprimable
*En tant qu'*organisateur, *je veux* imprimer le déroulé, *afin de* le communiquer.
- **CA** : PDF du déroulé (phases, tours, horaires) issu d'E03US010.
- **Dépend de** : E09US001, E03US010 · **Jalon** : J4
