# ADR-0007 — Erreurs typées par couche

- **Statut** : Accepté
- **Date** : 2026-07-08
- **Décideurs** : Organisateur / Architecte

## Contexte et problème

Avec une architecture hexagonale (ADR-0003), une erreur peut naître dans le domaine (règle métier violée), l'application (cas d'usage impossible), l'infrastructure (panne DB/IO) ou l'API (entrée invalide). Traiter toutes les erreurs de façon uniforme brouille la cause, fait fuiter des détails techniques vers le client et complique le diagnostic en compétition.

## Options envisagées

- **Familles d'exceptions par couche**, mappées vers HTTP uniquement à la frontière API.
- Exceptions génériques partout : perte d'information sur l'origine, mapping HTTP dispersé.
- Codes d'erreur ad hoc au cas par cas : incohérent, non maintenable.

## Décision

Chaque couche définit sa **propre famille d'exceptions** ; le **mapping vers une réponse HTTP normalisée** se fait **uniquement dans l'adapter API**. Le domaine **ignore HTTP**.

| Couche | Famille | Exemple | → HTTP |
|---|---|---|---|
| Domaine | `DomainError` | `PlacementInvalide`, `PhaseMalAlimentee` | 422 (code métier) |
| Application | `ApplicationError` | `TournoiIntrouvable` | 404 / 409 |
| Infrastructure | `InfrastructureError` | échec DB / IO | 500 (message générique) |
| API | `ApiError` | validation d'entrée | 400 |

- **Format d'erreur uniforme côté client** : `{ code, message, details? }`.
- Les **messages internes ne fuient pas** : détail technique journalisé côté serveur, message générique renvoyé au client.
- Les erreurs **remontent typées** à travers les couches ; c'est l'API qui **traduit**.

## Conséquences

- **+** Cause d'erreur explicite ; diagnostic facilité (couplé aux logs structurés + AuditLog).
- **+** Mapping HTTP centralisé en un seul endroit (frontière API).
- **+** Le domaine ne connaît ni HTTP ni framework (cohérent avec ADR-0003).
- **−** Hiérarchie d'exceptions à définir et à maintenir par couche.
- **−** Discipline en revue : ne pas court-circuiter le mapping ni laisser fuiter une exception d'infrastructure brute.

## Liens
`guide-architecture.md` §6 ; ADR-0003.
