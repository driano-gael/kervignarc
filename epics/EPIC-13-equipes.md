# EPIC-13 — Épreuves par équipes

- **ID** : EPIC-13
- **Statut** : À planifier
- **Priorité** : MVP *(décision organisateur du 18/07/2026 — renverse le « hors périmètre » du cadrage du 14/07)*
- **Dépend de** : EPIC-02 (inscriptions), EPIC-05 (moteur / participant), EPIC-03 (placement), EPIC-04 (saisie), EPIC-06 (classement)
- **Réfs** : [ADR-0028](../docs/adr/0028-epreuves-par-equipes-participant.md) ; référentiel FFTA §6.3, §7 ; CDC technique §5 (`MATCH.participant`)

## Objectif / valeur
Permettre les **épreuves par équipes** (matchs à 3 archers, équipes mixtes H/F — FFTA §6.3/§7), en
**réalisant** l'abstraction *participant* que le cadrage avait laissée en porte ouverte (le moteur
oppose des participants, pas des archers). Un tournoi individuel devient le cas où chaque participant
**est** un archer.

## Périmètre
### Inclus
- **Abstraction participant** : `MATCH.participant_A/B` (archer **ou** équipe) dans le moteur (EPIC-05).
- **Composition des équipes** : entité `Equipe` du tournoi, membres, contrainte de composition (config, défaut FFTA).
- **Scoring d'équipe** : politique `scoring` (cumul, volées alternées §7), résolue par (phase, type de participant).
- **Placement, saisie, classement** apprenant à traiter un participant-équipe.

### Exclus
- Les formats non réglementés du catalogue E05 (poules, king of the hill…) — gate distinct (règle à fournir).
- Un classement fusionné individuel + équipes (si besoin réel : EPIC-06).

## Capacités
- [ ] Abstraction participant dans le moteur.
- [ ] CRUD des équipes + règle de composition.
- [ ] Politique de scoring d'équipe.
- [ ] Placement / saisie / classement par équipe.

## Critères d'acceptation (epic)
- Un duel individuel et un duel par équipes sont **deux assemblages du même moteur** (aucune branche `if équipe`).
- Le scoring d'équipe (cumul, volées alternées) reproduit un cas de référence FFTA §7 (oracle).

## Risques
- **Poser `Participant` trop tard** : si le moteur de duels (E05US005) se fige sur des archers avant l'abstraction, la précaution du cadrage est perdue → refonte. D'où **E13US001 en amont d'E05US005**.
