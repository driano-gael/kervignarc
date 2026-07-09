# EPIC-04 — Saisie des scores en temps réel

- **ID** : EPIC-04
- **Statut** : À planifier
- **Priorité** : MVP
- **Dépend de** : EPIC-03, EPIC-10
- **Réfs** : CDC fonctionnel M5 ; ADR-0002, ADR-0005

## Objectif / valeur
Permettre la saisie des scores sur ~30 tablettes (BYOD) en temps réel, avec validation par le scoreur et diffusion live — c'est le cœur opérationnel du jour J.

## Périmètre
### Inclus
- Saisie sur navigateur, appareil **rattaché à une cible**, volée par volée.
- Barème adapté à la **phase en cours** (cumul en qualif ; sets/duels dépend EPIC-05).
- **Validation** par le scoreur (peut couvrir **plusieurs cibles**), verrouillage après validation.
- **Cumul / calcul automatique**.
- **Temps réel** via WebSocket ; **tolérance aux coupures brèves** (file d'attente côté front + reconnexion, idempotence).
- **Correction** d'un score validé par rôle habilité, **tracée** (AuditLog).
- Ergonomie **tactile** (gros boutons, pavé de points).

### Exclus
- Construction des tableaux (EPIC-05) ; classements agrégés (EPIC-06).

## Capacités
- [ ] Écran de saisie tactile + validation.
- [ ] Cumul automatique + verrouillage.
- [ ] Live WebSocket + file de tolérance coupures.
- [ ] Correction tracée.

## Incréments
- **MVP** : saisie qualif (cumul) + validation + live + tolérance coupures.
- **MVP+1** : saisie en sets/duels, cas particuliers (abandon, disqualification → barrage).

## Critères d'acceptation (epic)
- Aucun score validé n'est perdu, même après une coupure wifi brève.
- La mise à jour live est visible en < 1–2 s.

## Questions ouvertes
- Mode de saisie par défaut (scoreur unique vs archer, H1).
- Règles de départage/barrage à appliquer (presets FFTA, cf. EPIC-06).
