# E13 — Épreuves par équipes — User Stories

> EPIC : [EPIC-13](../epics/EPIC-13-equipes.md) · Réfs : [ADR-0028](../docs/adr/0028-epreuves-par-equipes-participant.md), référentiel FFTA §6.3/§7, CDC technique §5.
> **Créé le 18/07/2026** — décision d'entrer les équipes dans le MVP (renverse le « hors périmètre » du cadrage du 14/07, ADR-0028).

---

### E13US001 — Abstraction participant (le match oppose des participants)
*En tant que* développeur, *je veux* que le moteur oppose des **participants** (archer **ou** équipe) et non des archers en dur, *afin d'*ajouter les équipes sans refondre le moteur de duels.
- **CA** : le modèle de duel porte `MATCH.participant_A/B` ; un `Participant` est **soit** un archer individuel **soit** une équipe ; un tournoi individuel est le cas où chaque participant **est** un archer (aucune complication du cas simple) ; peuplement et routage (E05) opèrent sur des participants.
- **Notes** : réalise la porte ouverte du cadrage (CDC §10). **Doit précéder E05US005** (l'arbre d'élimination) — sinon le moteur se fige sur des archers ([ADR-0028](../docs/adr/0028-epreuves-par-equipes-participant.md), risque). Tests domaine depuis ce CA (règle 9).
- **Dépend de** : E05US001 · **Jalon** : J2 *(avant E05US005)*

### E13US002 — Composer les équipes d'un tournoi
*En tant qu'*organisateur, *je veux* créer des équipes et y affecter des archers, *afin d'*inscrire des équipes à une épreuve.
- **CA** : entité `Equipe` du tournoi (nom, membres) ; CRUD ; un archer est affecté à une équipe **de son propre tournoi** ; la **contrainte de composition** (nombre d'archers, mixité) est **configurable**, défaut FFTA (§6.3/§7 : 3 archers ; mixte = 2 archers H/F) ; un archer engagé en équipe **élargit** la notion d'« engagé » (glossaire).
- **Notes** : entité enfant du tournoi (comme `Depart`, `Scoreur`) ; contrainte de composition = template modifiable (référentiel §10). Élargit [DETTE-001](../docs/dette.md) (FK `equipe.tournoi_id`, `membre_equipe.*` sans `ON DELETE`). Tests domaine (règle de composition) depuis ce CA.
- **Dépend de** : E13US001, E02US002 · **Jalon** : J2

### E13US003 — Scoring d'équipe (politique injectable)
*En tant que* scoreur, *je veux* saisir et cumuler le score d'une **équipe** (volées alternées, cumul des membres), *afin de* départager des équipes en duel.
- **CA** : le scoring d'équipe est une implémentation de la politique `scoring` ([ADR-0004](../docs/adr/0004-moteur-de-phases-politiques.md)) — **cumul** des membres, **volées alternées** (FFTA §7) ; résolu par le couple (phase, type de participant) ; **aucune branche `if équipe`** dans le moteur.
- **Notes** : reproduit un cas de référence FFTA §7 (oracle, règle 9). S'assemble comme les autres politiques (E05US003).
- **Dépend de** : E13US001, E05US003 · **Jalon** : J2

### E13US004 — Placement, saisie & classement par équipe
*En tant qu'*organisateur, *je veux* placer, saisir et classer des **équipes**, *afin de* dérouler une épreuve par équipes de bout en bout.
- **CA** : le placement pose une **équipe** (ses archers sur des cibles voisines) ; la saisie enregistre une **volée d'équipe** ; le classement produit des **rangs d'équipe** ; chaque brique traite un participant qui n'est pas un individu.
- **Notes** : les briques restent dans EPIC-03/04/06 ; EPIC-13 les **coordonne** pour le cas équipe. Découpage plus fin possible à la planification (par brique) si l'US est trop large pour une branche.
- **Dépend de** : E13US001, E13US002, E13US003 · **Jalon** : J2 → J3
