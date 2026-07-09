# EPIC-10 — Accès & rôles

- **ID** : EPIC-10
- **Statut** : À planifier
- **Priorité** : MVP
- **Dépend de** : EPIC-00
- **Réfs** : CDC technique §9 ; ADR-0007

## Objectif / valeur
Donner à chaque intervenant le bon niveau d'accès, en restant simple et adapté à un réseau local fermé. Prérequis de la saisie (EPIC-04).

## Périmètre
### Inclus
- **Public** : consultation en lecture seule, sans authentification.
- **Scoreur** : accès par **code de cible**, habilitable sur **plusieurs cibles** ; jeton de session simple.
- **Administrateur** : accès protégé par mot de passe (configuration, moteur, exports, corrections).
- **Journal d'audit** des actions sensibles (corrections, validations, forfaits).

### Exclus
- Comptes nominatifs individuels (non retenus) ; SSO / annuaire.

## Capacités
- [ ] Accès public ouvert en lecture.
- [ ] Session scoreur par code de cible (multi-cibles).
- [ ] Accès admin protégé.
- [ ] AuditLog métier.

## Incréments
- **MVP** : les trois niveaux d'accès + AuditLog.

## Critères d'acceptation (epic)
- Un scoreur ne peut valider que sur ses cibles autorisées.
- Les actions sensibles sont tracées (qui / quand / avant-après).
