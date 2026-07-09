# E04 — Saisie des scores en temps réel — User Stories

> EPIC : [EPIC-04](../epics/EPIC-04-saisie-scores.md) · Réfs : CDC fonctionnel M5, ADR-0005.

---

### E04US001 — Rattacher un appareil à une cible
*En tant que* scoreur, *je veux* associer ma tablette à une cible, *afin de* saisir les bons archers.
- **CA** : saisie d'un code de cible → session rattachée ; un scoreur peut couvrir plusieurs cibles (E10US004).
- **Dépend de** : E10US003, E03US008 · **Jalon** : J1

### E04US002 — Afficher la grille de saisie (4 archers)
*En tant que* scoreur, *je veux* voir les archers de ma cible, *afin de* saisir leurs scores.
- **CA** : liste des archers/positions de la cible ; volée courante mise en évidence ; adapté au tactile.
- **Dépend de** : E04US001 · **Jalon** : J1

### E04US003 — Saisir les flèches d'une volée (pavé tactile)
*En tant que* scoreur, *je veux* saisir chaque flèche via un pavé, *afin de* renseigner rapidement.
- **CA** : pavé de valeurs (0-10, M, X) ; gros boutons ; correction avant validation.
- **Dépend de** : E04US002 · **Jalon** : J1

### E04US004 — Valider les valeurs autorisées
*En tant que* système, *je veux* n'accepter que des valeurs légales, *afin d'*éviter les erreurs.
- **CA** : refus d'une valeur hors barème ; nb de flèches par volée conforme au barème (E01US009).
- **Dépend de** : E04US003 · **Jalon** : J1

### E04US005 — Enregistrer une volée via la file d'écriture
*En tant que* scoreur, *je veux* que ma volée soit enregistrée, *afin de* ne pas la perdre.
- **CA** : volée persistée par la **file d'écriture** (writer unique) ; accusé de réception au client.
- **Notes** : idempotence par identifiant de saisie (ADR-0005).
- **Dépend de** : E00US007, E04US004 · **Jalon** : J1

### E04US006 — Éditer une volée non validée
*En tant que* scoreur, *je veux* corriger une volée pas encore validée, *afin de* rectifier une saisie.
- **CA** : modification possible tant que la série n'est pas validée ; historique non requis à ce stade.
- **Dépend de** : E04US005 · **Jalon** : J1

### E04US007 — Verrouiller une série validée
*En tant que* scoreur, *je veux* valider une série, *afin de* la figer.
- **CA** : après validation, la série est **verrouillée** (non éditable sans correction habilitée) ; diffusée.
- **Dépend de** : E04US005 · **Jalon** : J1

### E04US008 — Cumuler le score sur les volées
*En tant que* système, *je veux* cumuler les volées, *afin de* produire le score de qualif.
- **CA** : total mis à jour à chaque validation ; conforme au barème.
- **Dépend de** : E04US007 · **Jalon** : J1

### E04US009 — Diffuser la mise à jour en live
*En tant que* public/organisateur, *je veux* voir les scores en direct, *afin de* suivre l'épreuve.
- **CA** : après validation, diffusion WebSocket ; les abonnés (écran, mobile) se mettent à jour < 1-2 s.
- **Dépend de** : E00US008, E04US007 · **Jalon** : J1

### E04US010 — Mettre en file hors-ligne + rejouer
*En tant que* scoreur, *je veux* continuer à saisir malgré une coupure brève, *afin de* ne rien perdre.
- **CA** : saisies mises en file côté front hors-ligne ; rejeu à la reconnexion ; pas de doublon (idempotence).
- **Dépend de** : E04US005 · **Jalon** : J1

### E04US011 — Indicateur d'état de connexion
*En tant que* scoreur, *je veux* voir si je suis connecté, *afin de* savoir si mes saisies partent.
- **CA** : indicateur visible (connecté / hors-ligne / synchronisation en cours).
- **Dépend de** : E04US010 · **Jalon** : J1

### E04US012 — Corriger une volée validée (tracé)
*En tant qu'*administrateur/scoreur habilité, *je veux* corriger un score verrouillé, *afin de* réparer une erreur.
- **CA** : correction réservée aux rôles habilités ; entrée d'**AuditLog** (qui/quand/avant-après) ; recalcul du cumul.
- **Dépend de** : E04US007, E10US005 · **Jalon** : J1

### E04US013 — Saisie en sets (duels)
*En tant que* scoreur, *je veux* saisir un match au système de sets, *afin de* gérer les duels.
- **CA** : points de set attribués selon le barème (ex. 4 pts gagnant) ; cumul des points de set du match.
- **Dépend de** : E01US011, E05US007 · **Jalon** : J2

### E04US014 — Désigner le vainqueur d'un match
*En tant que* système, *je veux* déterminer le vainqueur, *afin de* faire progresser le tableau.
- **CA** : vainqueur calculé selon le barème de sets ; transmis au moteur (E05US008).
- **Dépend de** : E04US013 · **Jalon** : J2

### E04US015 — Gérer abandon / disqualification
*En tant que* scoreur, *je veux* enregistrer un abandon/DSQ, *afin de* refléter la réalité.
- **CA** : statut spécial sur un archer/match ; impact correct sur la progression et le classement.
- **Dépend de** : E04US014 · **Jalon** : J2

### E04US016 — Déclencher un barrage/shoot-off (égalité)
*En tant que* scoreur, *je veux* résoudre une égalité par barrage, *afin de* départager.
- **CA** : à égalité, saisie d'un shoot-off (1 flèche) ; plus près du centre départage ; vainqueur enregistré.
- **Notes** : politique `tiebreak` (ADR-0004) ; presets FFTA.
- **Dépend de** : E04US014, E06US003 · **Jalon** : J2
